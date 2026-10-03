"""Adversarial pre-launch guard tests for Phase 5D (EXP-04).

Proves that:
1. Authorization guard strictly fails closed (raises RuntimeError without explicit --authorized).
2. TwoStreamBatchSampler adheres strictly to 15 standard + 1 mined tiles per batch (6.25% mined exposure, 896 batches).
3. Checkpoint, candidate manifest, and spatial split identities match canonical constants.
4. Output directory isolation protects against uncommanded checkpoint collision.
5. evaluate_validation consumes meter.compute() and provides checkpoint gating keys.
6. Epoch transaction preflight executes cleanly end-to-end on CPU.
7. ResNet34UNet architecture maintains exact parameter (24,346,305) and buffer (19,054) counts.
"""

import hashlib
import json
from pathlib import Path
import pytest
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

REPO_ROOT = Path(__file__).resolve().parent.parent

from scripts.train_exp04 import (
    EXPECTED_CANDIDATE_MANIFEST_SHA256,
    EXPECTED_SPLIT_SHA256,
    EXPECTED_TEACHER_SHA256,
    EXPECTED_TEACHER_SIZE,
    TwoStreamBatchSampler,
    build_arg_parser,
    evaluate_validation,
    atomic_save_checkpoint,
    atomic_write_json,
)
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss
from ocean_sentinel.ml.unet_resnet import ResNet34UNet


def test_authorization_guard_fails_closed():
    """Verify that train_exp04.py without --authorized strictly raises RuntimeError."""
    from scripts import train_exp04

    parser = train_exp04.build_arg_parser()
    args = parser.parse_args([])
    assert not args.authorized

    with pytest.raises(RuntimeError, match="PHASE 5D TRAINING EXECUTION NOT AUTHORIZED"):
        train_exp04.train_exp04(args)


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
    assert all(c["gt_pixels"] == 0 for c in payload["candidates"])


def test_exp04_two_stream_batch_sampler_invariants():
    """Verify EXP-04 TwoStreamBatchSampler properties:
    - exactly 896 batches per epoch (13,440 // 15 = 896)
    - 15 standard + 1 mined = 16 tiles per batch
    - standard stream has 13,440 unique indices (zero duplicates)
    - mined stream draws from [0, 400)
    """
    n_std = 13440
    n_mined = 400
    sampler = TwoStreamBatchSampler(n_std, n_mined, n_standard_per_batch=15, n_mined_per_batch=1, seed=42)

    assert len(sampler) == 896

    batches = list(sampler)
    assert len(batches) == 896

    seen_std = []
    seen_mined = []
    for batch in batches:
        assert len(batch) == 16
        b_std = batch[:15]
        b_mined = [idx - n_std for idx in batch[15:]]
        assert len(b_std) == 15
        assert len(b_mined) == 1
        seen_std.extend(b_std)
        seen_mined.extend(b_mined)

    # Standard stream: complete permutation without replacement across 13,440 tiles
    assert len(seen_std) == 13440
    assert len(set(seen_std)) == 13440
    assert set(seen_std) == set(range(13440))

    # Mined stream: draws with replacement from [0, 400)
    assert len(seen_mined) == 896
    assert all(0 <= idx < 400 for idx in seen_mined)


def test_exp04_output_directory_isolation():
    """Verify that experiments/performance/exp04_hard_neg_ablation contains zero checkpoints prior to training."""
    out_dir = REPO_ROOT / "experiments" / "performance" / "exp04_hard_neg_ablation"
    run_state_file = out_dir / "run_state.json"
    if out_dir.exists():
        checkpoints = sorted([p.name for p in out_dir.glob("*.pt")])
        if run_state_file.exists():
            state = json.loads(run_state_file.read_text(encoding="utf-8"))
            if state.get("status") == "COMPLETED":
                assert checkpoints == ["best_model.pt", "last_model.pt"]
                return
        assert len(checkpoints) == 0, f"Contaminating checkpoints found in {out_dir}: {checkpoints}"


def test_exp04_validation_metric_extraction_regression():
    """Regression test ensuring evaluate_validation consumes meter.compute() and provides checkpoint gating keys."""
    device = torch.device("cpu")

    class MockModel(nn.Module):
        def forward(self, x):
            return torch.zeros((x.shape[0], 1, 512, 512), dtype=torch.float32)

    model = MockModel()
    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0)

    imgs = torch.zeros(4, 2, 512, 512, dtype=torch.float32)
    masks = torch.zeros(4, 1, 512, 512, dtype=torch.float32)
    masks[1, 0, 100:150, 100:150] = 1.0
    loader = DataLoader(TensorDataset(imgs, masks), batch_size=2)

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


def test_exp04_epoch_transaction_preflight(tmp_path):
    """Mandatory preflight proving the full epoch transaction succeeds without error.
    Covers:
    train representation -> validation -> meter compute -> metric persistence ->
    atomic checkpoint serialization -> independent load verification.
    """
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

    # 5. Checkpoint serialization & 6. Reload verification
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

    loaded = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    assert loaded["epoch"] == 1
    assert "model_state_dict" in loaded


def test_model_architecture_parameter_and_buffer_counts():
    """Verify ResNet34UNet parameter and buffer counts:
    - Trainable parameters: 24,346,305
    - Buffers: 19,054
    - Total state dict elements: 24,365,359
    """
    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    buffers = sum(b.numel() for b in model.buffers())
    total_elements = sum(t.numel() for t in model.state_dict().values())

    assert trainable == 24346305, f"Trainable params mismatch: {trainable} != 24,346,305"
    assert buffers == 19054, f"Buffers mismatch: {buffers} != 19,054"
    assert total_elements == 24365359, f"Total state dict elements mismatch: {total_elements} != 24,365,359"
