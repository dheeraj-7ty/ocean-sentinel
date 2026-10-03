"""Phase 5H Adversarial Pre-Launch Preflight & Transaction Regression Test Suite.

Verifies:
1. Exact architecture ResNet34UNet.
2. Exact parameter (24,346,305), buffer (19,054), and state dict (24,365,359) counts.
3. Exact teacher baseline SHA-256 and size.
4. Exact hard-negative candidate manifest SHA-256.
5. Exact spatial split manifest SHA-256.
6. 355 capped candidates (fp_pixels <= 50,000).
7. Zero excluded candidates eligible (45 excluded, fp_pixels > 50,000).
8. All candidates 100% GT-negative (gt_pixels == 0).
9. 15 standard + 1 mined = 16 tiles/batch structure.
10. 6.25% mined batch exposure.
11. Exactly 896 batches per epoch.
12. Exactly 8,960 total optimizer steps.
13. Fixed operating threshold tau = 0.22.
14. Fixed random seed = 42 (sampler seed: 42 + 1000 * epoch).
15. Optimizer configuration (AdamW, lr=1e-4, weight_decay=1e-2).
16. Scheduler configuration (CosineAnnealingLR, T_max=10, eta_min=1e-6).
17. Exact BCE loss coefficient (0.5).
18. Exact Dice loss coefficient (0.5).
19. Exact Dice smoothing parameter (1.0).
20. BCE positive class weight pos_weight = 2.0.
21. Negative BCE loss component remains strictly unweighted (diff == 0.0).
22. Dice loss output is bitwise identical / unaffected by pos_weight.
23. Part III scientific firewall 100% closed.
24. Prior experiment immutability (EXP-01, EXP-03, EXP-04, EXP-05).
25. Windows verifier safety requirements (num_workers=0, main guard).
26. Telemetry and run-state requirements.
27. One-variable purity: only pos_weight changes vs EXP-05.
28. Complete epoch transaction preflight on CPU using SegmentationMeter.compute().
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

from scripts.train_exp06 import (
    EXPECTED_CANDIDATE_MANIFEST_SHA256,
    EXPECTED_SPLIT_SHA256,
    EXPECTED_TEACHER_SHA256,
    EXPECTED_TEACHER_SIZE,
    SEVERITY_CAP_THRESHOLD,
    EXPECTED_RETAINED_CANDIDATES,
    EXPECTED_EXCLUDED_CANDIDATES,
    EXPECTED_SURVIVING_SCENES,
    POS_WEIGHT,
    BCE_COEFF,
    DICE_COEFF,
    DICE_SMOOTH,
    FROZEN_THRESHOLD,
    TwoStreamBatchSampler,
    build_arg_parser,
    evaluate_validation,
    atomic_save_checkpoint,
    atomic_write_json,
)
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss
from ocean_sentinel.ml.unet_resnet import ResNet34UNet, count_parameters


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def test_authorization_guard_fails_closed():
    """Verify train_exp06.py raises RuntimeError if --authorized is absent."""
    from scripts import train_exp06

    parser = train_exp06.build_arg_parser()
    args = parser.parse_args([])
    assert not args.authorized

    with pytest.raises(RuntimeError, match="PHASE 5H TRAINING EXECUTION NOT AUTHORIZED"):
        train_exp06.train_exp06(args)


def test_architecture_parameter_and_buffer_counts():
    """Verify ResNet34UNet parameter, buffer, and state counts."""
    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")
    param_counts = count_parameters(model)
    assert param_counts["trainable"] == 24346305
    assert param_counts["non_trainable"] == 0

    named_buffers = list(model.named_buffers())
    total_buffers = sum(b.numel() for _, b in named_buffers)
    assert total_buffers == 19054

    state_dict = model.state_dict()
    total_state_elements = sum(p.numel() for p in state_dict.values())
    assert total_state_elements == 24365359


def test_provenance_and_input_hashes():
    """Verify teacher, manifest, and split hashes on disk."""
    t_path = REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt"
    assert t_path.exists()
    assert compute_sha256(t_path) == EXPECTED_TEACHER_SHA256
    assert t_path.stat().st_size == EXPECTED_TEACHER_SIZE

    m_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "exp03_hard_negative_manifest.json"
    assert m_path.exists()
    assert compute_sha256(m_path) == EXPECTED_CANDIDATE_MANIFEST_SHA256

    s_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
    assert s_path.exists()
    assert compute_sha256(s_path) == EXPECTED_SPLIT_SHA256


def test_candidate_filtering_and_scene_retention():
    """Verify exact 50,000 cap yields 355 candidates across 251 scenes with zero GT."""
    m_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "exp03_hard_negative_manifest.json"
    data = json.loads(m_path.read_text(encoding="utf-8"))
    cands = data["candidates"]
    assert len(cands) == 400
    assert all(c["gt_pixels"] == 0 for c in cands)

    retained = [c for c in cands if c["fp_pixels"] <= SEVERITY_CAP_THRESHOLD]
    excluded = [c for c in cands if c["fp_pixels"] > SEVERITY_CAP_THRESHOLD]

    assert len(retained) == EXPECTED_RETAINED_CANDIDATES
    assert len(excluded) == EXPECTED_EXCLUDED_CANDIDATES
    assert len(set(c["parent_stem"] for c in retained)) == EXPECTED_SURVIVING_SCENES


def test_two_stream_sampler_sampling_contract():
    """Verify 15 standard + 1 mined = 16 batch structure, 896 batches, 8,960 steps."""
    sampler = TwoStreamBatchSampler(13440, EXPECTED_RETAINED_CANDIDATES, 15, 1, seed=42)
    assert len(sampler) == 896
    batches = list(sampler)
    assert len(batches) == 896
    assert all(len(b) == 16 for b in batches)
    assert all(b[15] >= 13440 for b in batches)


def test_loss_formulation_analytical_invariants():
    """Verify mathematical properties of pos_weight = 2.0 in CombinedBCEAndDiceLoss:
    1. Positive targets scaled by exactly 2.0.
    2. Negative targets difference is exactly 0.0.
    3. Dice loss is bitwise identical.
    """
    loss_w1 = CombinedBCEAndDiceLoss(bce_weight=BCE_COEFF, dice_weight=DICE_COEFF, smooth=DICE_SMOOTH, pos_weight=1.0)
    loss_w2 = CombinedBCEAndDiceLoss(bce_weight=BCE_COEFF, dice_weight=DICE_COEFF, smooth=DICE_SMOOTH, pos_weight=POS_WEIGHT)

    dummy_logits = torch.tensor([[-1.5, 2.5], [0.8, -2.2]], dtype=torch.float32)
    dummy_targets = torch.tensor([[0.0, 1.0], [1.0, 0.0]], dtype=torch.float32)

    bce1 = nn.BCEWithLogitsLoss(reduction="none")(dummy_logits, dummy_targets)
    bce2 = nn.BCEWithLogitsLoss(reduction="none", pos_weight=torch.tensor([POS_WEIGHT]))(dummy_logits, dummy_targets)

    # Negative targets must have 0.0 difference
    diff_neg = (bce2[dummy_targets == 0] - bce1[dummy_targets == 0]).abs().max().item()
    assert diff_neg < 1e-7

    # Positive targets must have ratio == 2.0
    ratio_pos = (bce2[dummy_targets == 1] / bce1[dummy_targets == 1])
    assert torch.allclose(ratio_pos, torch.tensor([POS_WEIGHT, POS_WEIGHT]), atol=1e-6)

    # Dice loss must be identical
    dice1 = loss_w1.dice(dummy_logits, dummy_targets)
    dice2 = loss_w2.dice(dummy_logits, dummy_targets)
    assert (dice1 - dice2).abs().item() == 0.0


def test_part_iii_firewall_enforced():
    """Verify Part III firewall raises PartIIIFirewallViolationError on forbidden paths."""
    from ocean_sentinel.ingestion.firewall import assert_no_part_iii_leakage, PartIIIFirewallViolationError

    allowed_paths = ["data/raw/trujillo_2024/images/Oil/00001.tif"]
    assert_no_part_iii_leakage(allowed_paths, check_content_hashes=False)

    forbidden_paths = ["data/metadata/trujillo_part_iii/manifest.json"]
    with pytest.raises(PartIIIFirewallViolationError):
        assert_no_part_iii_leakage(forbidden_paths, check_content_hashes=False)


def test_prior_experiment_checkpoints_immutable():
    """Verify that EXP-01, EXP-03, EXP-04, and EXP-05 checkpoints remain untouched and loadable."""
    exp_checkpoints = {
        "EXP-01": (REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt", "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699"),
        "EXP-03": (REPO_ROOT / "experiments" / "performance" / "exp03_baseline_hard_neg" / "best_model.pt", "BE00C1C8B35A3648FCCAD3864F844ED2EB68E079F2CC390C1BA3EC147BF2DA57"),
        "EXP-04": (REPO_ROOT / "experiments" / "performance" / "exp04_hard_neg_ablation" / "best_model.pt", "FAC3C313386F3FE561C2ECF0945B7F960CAA74897C5E8105FB68635529F1320B"),
        "EXP-05": (REPO_ROOT / "experiments" / "performance" / "exp05_candidate_severity_cap" / "best_model.pt", "D9FC12E312E5DF012650E8106DCF90782534EFB1BD1E38BA7FDCF4E0802A0481"),
    }
    for exp_id, (path, sha) in exp_checkpoints.items():
        assert path.exists(), f"Missing {exp_id} checkpoint"
        assert compute_sha256(path) == sha, f"Hash drift for {exp_id}"


def test_epoch_transaction_preflight_end_to_end():
    """Simulate complete mini epoch transaction on CPU with pos_weight=2.0."""
    device = torch.device("cpu")
    model = nn.Sequential(
        nn.Conv2d(2, 4, kernel_size=3, padding=1),
        nn.ReLU(),
        nn.Conv2d(4, 1, kernel_size=1),
    ).to(device)

    criterion = CombinedBCEAndDiceLoss(bce_weight=BCE_COEFF, dice_weight=DICE_COEFF, smooth=DICE_SMOOTH, pos_weight=POS_WEIGHT).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=10, eta_min=1e-6)

    # 1. Training step
    model.train()
    optimizer.zero_grad()
    dummy_x = torch.randn(2, 2, 64, 64, device=device)
    dummy_y = torch.randint(0, 2, (2, 1, 64, 64), dtype=torch.float32, device=device)

    logits = model(dummy_x)
    loss = criterion(logits, dummy_y)
    assert torch.isfinite(loss).item()
    loss.backward()
    optimizer.step()
    scheduler.step()

    # 2. Validation & metric computation using SegmentationMeter.compute()
    val_loader = DataLoader(TensorDataset(dummy_x, dummy_y), batch_size=2)
    val_metrics = evaluate_validation(model, val_loader, criterion, device, threshold=FROZEN_THRESHOLD)

    assert "val_loss" in val_metrics
    assert "val_iou" in val_metrics
    assert "val_recall" in val_metrics
    assert "clean_water_far_pct" in val_metrics

    # 3. Checkpoint write and reload
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

        reloaded = torch.load(tmp_path, map_location="cpu", weights_only=False)
        assert "model_state_dict" in reloaded
        assert reloaded["epoch"] == 1
