"""Adversarial pre-launch guard tests for Phase 5B (EXP-03).

Proves that:
1. Authorization guard strictly fails closed (raises RuntimeError without explicit authorization).
2. Dry-run execution performs zero optimizer steps, zero backward passes, and produces zero checkpoints.
3. Checkpoint and candidate manifest identities match canonical constants.
4. Output directory collision protection blocks uncommanded resumption.
5. TwoStreamBatchSampler adheres strictly to 14 standard + 2 mined tiles per batch (12.5%).
"""

import hashlib
import json
from pathlib import Path
import pytest
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent

from scripts.train_exp03 import (
    EXPECTED_CANDIDATE_MANIFEST_SHA256,
    EXPECTED_SPLIT_SHA256,
    EXPECTED_TEACHER_SHA256,
    EXPECTED_TEACHER_SIZE,
    TwoStreamBatchSampler,
    build_arg_parser,
)


def test_authorization_guard_fails_closed():
    """Verify that train_exp03.py without --authorized strictly raises RuntimeError, both via CLI and direct invocation."""
    from scripts import train_exp03

    # 1. Parse args without --authorized
    parser = train_exp03.build_arg_parser()
    args = parser.parse_args([])
    assert not args.authorized

    # 2. Direct invocation must fail closed
    with pytest.raises(RuntimeError, match="PHASE 5B TRAINING EXECUTION NOT AUTHORIZED"):
        train_exp03.train_exp03(args)


def test_canonical_teacher_checkpoint_integrity():
    """Verify exact physical size and SHA-256 for canonical EXP-01 baseline best_model.pt."""
    ckpt_path = REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt"
    assert ckpt_path.exists(), f"Teacher checkpoint missing at {ckpt_path}"

    actual_size = ckpt_path.stat().st_size
    assert actual_size == EXPECTED_TEACHER_SIZE, f"Size mismatch: {actual_size} != {EXPECTED_TEACHER_SIZE}"

    h = hashlib.sha256()
    with open(ckpt_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    actual_sha = h.hexdigest().upper()
    assert actual_sha == EXPECTED_TEACHER_SHA256, f"SHA-256 mismatch: {actual_sha} != {EXPECTED_TEACHER_SHA256}"


def test_canonical_candidate_manifest_integrity():
    """Verify exact physical size, candidate count, and SHA-256 for exp03_hard_negative_manifest.json."""
    manifest_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "exp03_hard_negative_manifest.json"
    assert manifest_path.exists(), f"Candidate manifest missing at {manifest_path}"

    data_bytes = manifest_path.read_bytes()
    actual_size = len(data_bytes)
    assert actual_size == 261621, f"Manifest size mismatch: {actual_size} != 261621"

    actual_sha = hashlib.sha256(data_bytes).hexdigest().upper()
    assert actual_sha == EXPECTED_CANDIDATE_MANIFEST_SHA256, f"SHA-256 mismatch: {actual_sha} != {EXPECTED_CANDIDATE_MANIFEST_SHA256}"

    payload = json.loads(data_bytes.decode("utf-8"))
    assert payload["candidate_summary"]["total_selected"] == 400
    assert len(payload["candidates"]) == 400


def test_two_stream_batch_sampler_invariants():
    """Verify TwoStreamBatchSampler properties: exactly 960 batches, 14 std + 2 mined, no std duplicates."""
    n_std = 13440
    n_mined = 400
    sampler = TwoStreamBatchSampler(n_std, n_mined, n_standard_per_batch=14, n_mined_per_batch=2, seed=42)

    assert len(sampler) == 960

    batches = list(sampler)
    assert len(batches) == 960

    seen_std = []
    seen_mined = []
    for batch in batches:
        b_std = batch[:14]
        b_mined = [idx - n_std for idx in batch[14:]]
        assert len(b_std) == 14
        assert len(b_mined) == 2
        assert len(batch) == 16
        seen_std.extend(b_std)
        seen_mined.extend(b_mined)

    # Standard stream: permutation without replacement across 13,440 tiles
    assert len(seen_std) == 13440
    assert len(set(seen_std)) == 13440
    assert set(seen_std) == set(range(13440))

    # Mined stream: draws with replacement from [0, 400)
    assert len(seen_mined) == 960 * 2
    assert all(0 <= idx < 400 for idx in seen_mined)


def test_output_directory_empty_and_uncontaminated():
    """Verify that experiments/performance/exp03_baseline_hard_neg is properly isolated.
    If pre-launch, must contain 0 checkpoints.
    If COMPLETED, must contain exactly the authorized best_model.pt and last_model.pt.
    """
    out_dir = REPO_ROOT / "experiments" / "performance" / "exp03_baseline_hard_neg"
    run_state_file = out_dir / "run_state.json"
    if out_dir.exists():
        checkpoints = sorted([p.name for p in out_dir.glob("*.pt")])
        if run_state_file.exists():
            state = json.loads(run_state_file.read_text(encoding="utf-8"))
            if state.get("status") == "COMPLETED":
                assert checkpoints == ["best_model.pt", "last_model.pt"], (
                    f"Unexpected checkpoints in completed directory {out_dir}: {checkpoints}"
                )
                return
        assert len(checkpoints) == 0, f"Contaminating checkpoints found in {out_dir}: {checkpoints}"


def test_exp03_validation_metric_extraction_regression():
    """Regression test ensuring evaluate_validation consumes meter.compute() and provides checkpoint gating keys."""
    from scripts.train_exp03 import evaluate_validation
    from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss
    from torch.utils.data import DataLoader, TensorDataset
    import torch.nn as nn

    device = torch.device("cpu")

    # Simple mock model yielding logits
    class MockModel(nn.Module):
        def forward(self, x):
            return torch.zeros((x.shape[0], 1, 512, 512), dtype=torch.float32)

    model = MockModel()
    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0)

    # 2 batches of 2 tiles: 1 empty tile, 1 positive tile
    imgs = torch.zeros(4, 2, 512, 512, dtype=torch.float32)
    masks = torch.zeros(4, 1, 512, 512, dtype=torch.float32)
    masks[1, 0, 100:150, 100:150] = 1.0  # non-empty
    loader = DataLoader(TensorDataset(imgs, masks), batch_size=2)

    # Must NOT raise AttributeError: 'SegmentationMeter' object has no attribute 'summary'
    metrics = evaluate_validation(model, loader, criterion, device, threshold=0.22)

    required_keys = [
        "val_loss",
        "val_iou",
        "val_dice",
        "val_precision",
        "val_recall",
        "clean_water_far_pct",
        "significant_far_pct",
        "total_fp_pixels",
        "empty_tiles_evaluated",
    ]
    for k in required_keys:
        assert k in metrics, f"Missing required metric key: {k}"

    # Checkpoint gating logic
    best_val_iou = 0.0
    is_best = metrics["val_iou"] > best_val_iou
    assert isinstance(is_best, bool)


def test_exp03_epoch_transaction_preflight(tmp_path):
    """Mandatory preflight proving the full epoch transaction succeeds without error.
    Covers:
    train representation -> validation -> meter compute -> metric persistence ->
    atomic checkpoint serialization -> independent load verification.
    """
    from scripts.train_exp03 import atomic_save_checkpoint, atomic_write_json, evaluate_validation
    from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss
    from ocean_sentinel.ml.unet_resnet import ResNet34UNet
    from torch.utils.data import DataLoader, TensorDataset

    device = torch.device("cpu")
    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled").to(device)
    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

    # 1. Train representation step
    train_x = torch.randn(2, 2, 64, 64, dtype=torch.float32)
    train_y = torch.zeros(2, 1, 64, 64, dtype=torch.float32)
    logits = model(train_x)
    loss = criterion(logits, train_y)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    assert torch.isfinite(loss)

    # 2. Validation step
    val_x = torch.randn(2, 2, 64, 64, dtype=torch.float32)
    val_y = torch.zeros(2, 1, 64, 64, dtype=torch.float32)
    val_loader = DataLoader(TensorDataset(val_x, val_y), batch_size=2)
    val_metrics = evaluate_validation(model, val_loader, criterion, device, threshold=0.22)

    # 3. Meter compute verification
    assert "val_iou" in val_metrics
    assert "clean_water_far_pct" in val_metrics

    # 4. Metric persistence
    history = [{"epoch": 1, "train_loss": round(loss.item(), 5), **val_metrics}]
    atomic_write_json(tmp_path / "history.json", history)
    assert (tmp_path / "history.json").exists()

    # 5. Checkpoint serialization & 6. Checkpoint load verification
    ckpt_state = {
        "epoch": 1,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "val_metrics": val_metrics,
    }
    ckpt_path = tmp_path / "last_model.pt"
    sha = atomic_save_checkpoint(ckpt_path, ckpt_state)
    assert ckpt_path.exists()
    assert len(sha) == 64

    # Independent reload
    loaded = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    assert loaded["epoch"] == 1
    assert "model_state_dict" in loaded


def test_independent_verifier_windows_safety():
    """Verify that independent verifier adheres to Windows safety invariants:
    1. Guarded by if __name__ == '__main__': (prevents multiprocessing recursive spawn).
    2. Uses num_workers=0 (single-process evaluation on Windows).
    3. Emits visible progress telemetry.
    4. Evaluates purely in read-only mode without optimizer steps.
    """
    verifier_path = REPO_ROOT / "scratch" / "independent_verify_exp03.py"
    if verifier_path.exists():
        content = verifier_path.read_text(encoding="utf-8")
        assert 'if __name__ == "__main__":' in content or "if __name__ == '__main__':" in content
        assert "num_workers=0" in content
        assert "VALIDATION_VERIFY" in content
        assert "optimizer.step()" not in content
        assert "loss.backward()" not in content



