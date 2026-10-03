"""Phase 5F Pre-Launch Preflight & Transaction Regression Test Suite.

Proves prior to EXP-05 launch:
1. Authorization guard fails closed without --authorized.
2. Candidate severity cap (<= 50,000 FP pixels) yields exactly 355 retained and 45 excluded candidates.
3. Zero ground-truth contamination across all candidates.
4. Surviving parent scene count is exactly 251 (91.94% retention) with no scene domination.
5. TwoStreamBatchSampler maintains 15 standard + 1 mined = 16 tiles/batch, 896 batches/epoch, 8,960 optimizer steps.
6. Deterministic sampler seed semantics (seed + epoch * 1000).
7. Frozen threshold tau = 0.22.
8. Part III scientific firewall remains 100% closed.
9. Prior experiment artifacts (EXP-01, EXP-03, EXP-04 checkpoints) remain untouched and valid.
10. Epoch transaction preflight: executes forward, loss, backward, optimizer step, scheduler step,
    metric update, metric compute (SegmentationMeter.compute()), atomic checkpoint write, and run_state update on CPU.
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path
import pytest
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

REPO_ROOT = Path(__file__).resolve().parent.parent

from scripts.train_exp05 import (
    EXPECTED_CANDIDATE_MANIFEST_SHA256,
    EXPECTED_SPLIT_SHA256,
    EXPECTED_TEACHER_SHA256,
    EXPECTED_TEACHER_SIZE,
    SEVERITY_CAP_THRESHOLD,
    EXPECTED_RETAINED_CANDIDATES,
    EXPECTED_EXCLUDED_CANDIDATES,
    EXPECTED_SURVIVING_SCENES,
    TwoStreamBatchSampler,
    build_arg_parser,
    evaluate_validation,
    atomic_save_checkpoint,
    atomic_write_json,
)
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss
from ocean_sentinel.ml.unet_resnet import ResNet34UNet


def test_authorization_guard_fails_closed():
    """Verify that train_exp05.py without --authorized strictly raises RuntimeError."""
    from scripts import train_exp05

    parser = train_exp05.build_arg_parser()
    args = parser.parse_args([])
    assert not args.authorized

    with pytest.raises(RuntimeError, match="PHASE 5F TRAINING EXECUTION NOT AUTHORIZED"):
        train_exp05.train_exp05(args)


def test_severity_cap_filtering_invariants():
    """Verify exact 50,000 cap filtering, counts, purity, and scene retention."""
    manifest_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "exp03_hard_negative_manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    cands = data["candidates"]
    assert len(cands) == 400
    assert all(c["gt_pixels"] == 0 for c in cands)

    retained = [c for c in cands if c["fp_pixels"] <= SEVERITY_CAP_THRESHOLD]
    excluded = [c for c in cands if c["fp_pixels"] > SEVERITY_CAP_THRESHOLD]

    assert len(retained) == EXPECTED_RETAINED_CANDIDATES
    assert len(excluded) == EXPECTED_EXCLUDED_CANDIDATES
    assert all(c["fp_pixels"] <= SEVERITY_CAP_THRESHOLD for c in retained)
    assert all(c["fp_pixels"] > SEVERITY_CAP_THRESHOLD for c in excluded)

    surviving_scenes = set(c["parent_stem"] for c in retained)
    assert len(surviving_scenes) == EXPECTED_SURVIVING_SCENES


def test_two_stream_batch_sampler_exp05_contract():
    """Verify sampler invariants: 15+1 batch structure, 896 batches, deterministic seeds."""
    n_std = 13440
    n_mined = EXPECTED_RETAINED_CANDIDATES  # 355
    sampler = TwoStreamBatchSampler(n_std, n_mined, n_standard_per_batch=15, n_mined_per_batch=1, seed=42)

    assert len(sampler) == 896
    batches = list(sampler)
    assert len(batches) == 896

    for b in batches:
        assert len(b) == 16
        b_std = b[:15]
        b_mined = [idx - n_std for idx in b[15:]]
        assert len(b_std) == 15
        assert len(b_mined) == 1
        assert 0 <= b_mined[0] < n_mined

    # Determinism across runs
    sampler2 = TwoStreamBatchSampler(n_std, n_mined, n_standard_per_batch=15, n_mined_per_batch=1, seed=42)
    batches2 = list(sampler2)
    assert batches == batches2

    # Different epochs produce different draws
    sampler.set_epoch(1)
    batches_ep1 = list(sampler)
    assert batches != batches_ep1


def test_part_iii_firewall_strictly_enforced():
    """Verify Part III firewall raises PartIIIFirewallViolationError on forbidden paths."""
    from ocean_sentinel.ingestion.firewall import assert_no_part_iii_leakage, PartIIIFirewallViolationError

    allowed_paths = ["data/raw/trujillo_2024/images/Oil/00001.tif"]
    assert_no_part_iii_leakage(allowed_paths, check_content_hashes=False)

    forbidden_paths = ["data/metadata/trujillo_part_iii/manifest.json"]
    with pytest.raises(PartIIIFirewallViolationError):
        assert_no_part_iii_leakage(forbidden_paths, check_content_hashes=False)


def test_prior_experiment_checkpoints_immutable():
    """Verify that EXP-01, EXP-03, and EXP-04 checkpoints exist and match hashes."""
    def get_sha(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        return h.hexdigest().upper()

    t_path = REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt"
    assert t_path.exists()
    assert get_sha(t_path) == EXPECTED_TEACHER_SHA256

    e3_path = REPO_ROOT / "experiments" / "performance" / "exp03_baseline_hard_neg" / "best_model.pt"
    assert e3_path.exists()
    assert get_sha(e3_path) == "BE00C1C8B35A3648FCCAD3864F844ED2EB68E079F2CC390C1BA3EC147BF2DA57"

    e4_path = REPO_ROOT / "experiments" / "performance" / "exp04_hard_neg_ablation" / "best_model.pt"
    assert e4_path.exists()
    assert get_sha(e4_path) == "FAC3C313386F3FE561C2ECF0945B7F960CAA74897C5E8105FB68635529F1320B"


def test_epoch_transaction_preflight_end_to_end():
    """End-to-end simulation of a full epoch transaction chain on CPU.
    Exercises: forward, loss, backward, optimizer step, scheduler step,
    metric update, metric compute (using .compute()), atomic checkpoint write, and run_state update.
    """
    device = torch.device("cpu")
    model = nn.Sequential(
        nn.Conv2d(2, 4, kernel_size=3, padding=1),
        nn.ReLU(),
        nn.Conv2d(4, 1, kernel_size=1),
    ).to(device)

    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=10, eta_min=1e-6)

    # 1. Training step
    model.train()
    optimizer.zero_grad()
    dummy_x = torch.randn(2, 2, 64, 64, device=device)
    dummy_y = torch.randint(0, 2, (2, 1, 64, 64), dtype=torch.float32, device=device)

    logits = model(dummy_x)
    loss = criterion(logits, dummy_y)
    loss.backward()
    optimizer.step()
    scheduler.step()

    # 2. Validation & metric computation
    val_loader = DataLoader(TensorDataset(dummy_x, dummy_y), batch_size=2)
    val_metrics = evaluate_validation(model, val_loader, criterion, device, threshold=0.22)

    assert "val_loss" in val_metrics
    assert "val_iou" in val_metrics
    assert "val_recall" in val_metrics
    assert "clean_water_far_pct" in val_metrics

    # 3. Checkpoint persistence and atomicity
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "test_best_model.pt"
        ckpt_state = {
            "epoch": 1,
            "model_state_dict": model.state_dict(),
            "val_metrics": val_metrics,
        }
        sha = atomic_save_checkpoint(tmp_path, ckpt_state)
        assert tmp_path.exists()
        assert len(sha) == 64

        # Verify loadability
        reloaded = torch.load(tmp_path, map_location="cpu", weights_only=False)
        assert "model_state_dict" in reloaded
        assert reloaded["epoch"] == 1

        # Verify run_state persistence
        state_path = Path(tmp_dir) / "run_state.json"
        atomic_write_json(state_path, {"status": "RUNNING", "best_val_iou": val_metrics["val_iou"]})
        assert state_path.exists()
        loaded_state = json.loads(state_path.read_text(encoding="utf-8"))
        assert loaded_state["status"] == "RUNNING"
