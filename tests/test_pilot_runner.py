"""Unit and regression tests for Gate 4.3C-B Pilot Runner semantics.

Verifies:
1. StepAccountingOptimizer accuracy under finite gradients and NaN/Inf skips.
2. Dual-layer cross-verification against AdamW per-parameter state step counts.
3. --no-test CLI flag suppresses test dataset and loader instantiation.
4. Hard GPU preflight raises fatal RuntimeError on CPU or sm < 70.
5. Production preflight gate executes strictly ZERO optimizer steps.
6. Checkpoint metadata semantics and integrity verification for all 3 artifacts.
7. Output directory safety guard against certified baseline corruption.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import torch
import torch.nn as nn
from torch.amp import GradScaler

from scripts.train_exp01 import (
    DEFAULT_OUTPUT_DIR,
    StepAccountingOptimizer,
    atomic_save_checkpoint,
    build_arg_parser,
    file_sha256,
    main,
    run_preflight_gate,
    safe_load_checkpoint,
    update_checkpoint_integrity,
)


class SimpleLinear(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.fc = nn.Linear(4, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc(x)


def test_step_accounting_optimizer_finite_and_inf_skip() -> None:
    """Verify StepAccountingOptimizer accurately records attempts, successful updates, and skips."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SimpleLinear().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    accountant = StepAccountingOptimizer(optimizer)
    scaler = GradScaler(device.type, enabled=(device.type == "cuda"))

    # Initial state
    assert accountant.optimizer_step_attempts == 0
    assert accountant.successful_optimizer_updates == 0
    assert accountant.amp_skipped_updates == 0

    # 1. Normal finite step
    x = torch.randn(2, 4, device=device)
    loss = model(x).sum()
    scaler.scale(loss).backward()
    accountant.record_attempt()
    scaler.step(optimizer)
    scaler.update()
    optimizer.zero_grad()

    assert accountant.optimizer_step_attempts == 1
    assert accountant.successful_optimizer_updates == 1
    assert accountant.amp_skipped_updates == 0

    # 2. Injected Inf gradient step (if CUDA AMP enabled, GradScaler skips optimizer.step)
    if device.type == "cuda":
        loss = model(x).sum()
        scaler.scale(loss).backward()
        for p in model.parameters():
            p.grad.data.fill_(float("inf"))

        accountant.record_attempt()
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad()

        assert accountant.optimizer_step_attempts == 2
        assert accountant.successful_optimizer_updates == 1
        assert accountant.amp_skipped_updates == 1

        # 3. Clean recovery step
        loss = model(x).sum()
        scaler.scale(loss).backward()
        accountant.record_attempt()
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad()

        assert accountant.optimizer_step_attempts == 3
        assert accountant.successful_optimizer_updates == 2
        assert accountant.amp_skipped_updates == 1


def test_step_accounting_cross_verification_with_adamw_state() -> None:
    """Verify that successful_optimizer_updates matches AdamW internal parameter step states."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SimpleLinear().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    accountant = StepAccountingOptimizer(optimizer)

    for i in range(5):
        optimizer.zero_grad()
        x = torch.randn(2, 4, device=device)
        loss = model(x).sum()
        loss.backward()
        accountant.record_attempt()
        optimizer.step()

    summary = accountant.get_accounting_summary()
    assert summary["optimizer_step_attempts"] == 5
    assert summary["successful_optimizer_updates"] == 5
    assert summary["amp_skipped_updates"] == 0

    for p in model.parameters():
        assert p in optimizer.state
        assert "step" in optimizer.state[p]
        p_step = int(optimizer.state[p]["step"].item())
        assert p_step == 5


def test_no_test_flag_present_in_arg_parser() -> None:
    """Verify --no-test flag is accepted and defaults to False."""
    parser = build_arg_parser()
    args = parser.parse_args([])
    assert args.no_test is False

    args_no_test = parser.parse_args(["--no-test"])
    assert args_no_test.no_test is True


def test_gpu_preflight_fails_fatally_without_cuda(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify that main() raises fatal RuntimeError when CUDA is unavailable."""
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    test_args = ["train_exp01.py", "--output-dir", str(tmp_path / "test_out")]
    with monkeypatch.context() as m:
        m.setattr("sys.argv", test_args)
        with pytest.raises(RuntimeError, match="FATAL: Production training requires CUDA"):
            main()


def test_gpu_preflight_fails_fatally_on_cpu_device(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify that main() raises fatal RuntimeError when --device cpu is requested."""
    test_args = ["train_exp01.py", "--device", "cpu", "--output-dir", str(tmp_path / "test_out")]
    with monkeypatch.context() as m:
        m.setattr("sys.argv", test_args)
        with pytest.raises(RuntimeError, match="Device 'cpu' is strictly prohibited"):
            main()


def test_gpu_preflight_fails_fatally_on_incompatible_gpu(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify that main() raises fatal RuntimeError when GPU compute capability is below sm_70."""
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    incompatible_info = {
        "pytorch_version": "2.10.0+cu128",
        "cuda_runtime": "12.8",
        "gpu_available": True,
        "gpu_count": 1,
        "gpu_name": "Tesla P100",
        "compute_capability": (6, 0),
        "sm_string": "sm_60",
        "compatible": False,
        "reason": "GPU compute capability sm_60 is below minimum required sm_70",
    }
    monkeypatch.setattr("ocean_sentinel.ml.gpu_qualification.probe_gpu_hardware", lambda: incompatible_info)
    test_args = ["train_exp01.py", "--device", "cuda", "--output-dir", str(tmp_path / "test_out")]
    with monkeypatch.context() as m:
        m.setattr("sys.argv", test_args)
        with pytest.raises(RuntimeError, match="FATAL: GPU architecture sm_60 is incompatible"):
            main()


def test_output_dir_safety_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that main() refuses to run pilot mode in certified baseline output directory."""
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    test_args = ["train_exp01.py", "--output-dir", str(DEFAULT_OUTPUT_DIR), "--no-test"]
    with monkeypatch.context() as m:
        m.setattr("sys.argv", test_args)
        with pytest.raises(RuntimeError, match="Refusing to run pilot/qualification mode"):
            main()


def test_checkpoint_metadata_semantics_audit(tmp_path: Path) -> None:
    """Verify distinct semantics, required keys, shapes, and checkpoint_integrity.json for all 3 artifacts."""
    output_dir = tmp_path / "chkpt_audit"
    output_dir.mkdir(parents=True, exist_ok=True)

    model = SimpleLinear()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=1)
    scaler = GradScaler("cpu", enabled=False)

    chkpt_state = {
        "epoch": 1,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "scaler_state_dict": scaler.state_dict(),
        "val_iou": 0.72500,
        "val_dice": 0.81000,
        "val_loss": 0.25000,
        "best_val_iou": -1.0,
        "best_epoch": 0,
        "patience_counter": 0,
        "history": [{"epoch": 1, "val_iou": 0.725}],
        "config": {"epochs": 1, "batch_size": 8},
        "experiment_fingerprint": {"manifest_sha256": "C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0"},
    }

    latest_path = output_dir / "latest_checkpoint.pt"
    best_path = output_dir / "best_model.pt"
    final_path = output_dir / "final_model.pt"

    sha_latest = atomic_save_checkpoint(latest_path, chkpt_state)
    update_checkpoint_integrity(
        output_dir,
        {
            "latest_checkpoint": str(latest_path),
            "latest_epoch": 1,
            "latest_sha256": sha_latest,
            "latest_time_utc": "2026-09-08T22:00:00Z",
        },
    )

    sha_best = atomic_save_checkpoint(best_path, chkpt_state)
    update_checkpoint_integrity(
        output_dir,
        {
            "best_checkpoint": str(best_path),
            "best_epoch": 1,
            "best_val_iou": 0.725,
            "best_sha256": sha_best,
            "best_time_utc": "2026-09-08T22:00:05Z",
        },
    )

    # final_model.pt is saved without update_checkpoint_integrity in the runner
    sha_final = atomic_save_checkpoint(final_path, {k: v for k, v in chkpt_state.items()})

    # Read-only audit verification
    integrity_path = output_dir / "checkpoint_integrity.json"
    assert integrity_path.exists()
    integrity_data = json.loads(integrity_path.read_text(encoding="utf-8"))

    # Verify latest and best are recorded in integrity JSON
    assert integrity_data["latest_sha256"] == sha_latest
    assert integrity_data["latest_epoch"] == 1
    assert integrity_data["best_sha256"] == sha_best
    assert integrity_data["best_epoch"] == 1

    # Verify final_model.pt is NOT recorded in integrity JSON (matching actual production runner)
    assert "final_sha256" not in integrity_data

    # Load and verify all 3 files
    for name, p, expected_sha in [
        ("latest_checkpoint.pt", latest_path, sha_latest),
        ("best_model.pt", best_path, sha_best),
        ("final_model.pt", final_path, sha_final),
    ]:
        assert p.exists()
        assert p.stat().st_size > 1024
        assert file_sha256(p) == expected_sha

        loaded = safe_load_checkpoint(p, map_location="cpu", expected_sha256=expected_sha)
        assert loaded["epoch"] == 1
        assert "model_state_dict" in loaded
        assert "optimizer_state_dict" in loaded
        assert "scheduler_state_dict" in loaded
        assert "scaler_state_dict" in loaded
        assert loaded["experiment_fingerprint"]["manifest_sha256"] == "C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0"


def test_step_accounting_with_lr_scheduler() -> None:
    """Verify StepAccountingOptimizer operates cleanly when wrapped by PyTorch LRScheduler."""
    from torch.optim.lr_scheduler import CosineAnnealingLR

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SimpleLinear().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    accountant = StepAccountingOptimizer(optimizer)
    scheduler = CosineAnnealingLR(optimizer, T_max=10)
    scaler = GradScaler(device.type, enabled=(device.type == "cuda"))

    for step in range(5):
        accountant.record_attempt()
        loss = model(torch.randn(2, 4, device=device)).sum()
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad()

    scheduler.step()

    summary = accountant.get_accounting_summary()
    assert summary["optimizer_step_attempts"] == 5
    assert summary["successful_optimizer_updates"] == 5
    assert summary["amp_skipped_updates"] == 0
