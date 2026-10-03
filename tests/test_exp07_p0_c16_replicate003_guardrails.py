"""Unit tests and guardrails for EXP-07-P0-C16: Kaggle GPU Qualification,

OPS02_v1.0.0_FROZEN Training Ingestion, and Authorized Replicate 003 (Seed 42).
"""

import json
import hashlib
from pathlib import Path
import pytest
import torch
import torch.nn as nn

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_kaggle_gpu_qualification():
    """Verify training occurred strictly on remote Kaggle GPU and not on local machine."""
    env_file = REPO_ROOT / "data/metadata/exp07_p0_c16_training_environment_v1.json"
    assert env_file.exists(), f"Missing {env_file}"

    with open(env_file, "r", encoding="utf-8") as f:
        env_data = json.load(f)

    assert env_data["execution_platform"] == "KAGGLE_GPU"
    assert env_data["hardware"]["local_laptop_training"] is False
    assert "Tesla T4" in env_data["hardware"]["gpu_model"]
    assert env_data["hardware"]["gpu_count"] >= 1
    assert env_data["hardware"]["cuda_compute_capability"] == [7, 5]


def test_holdout_firewall_untouched():
    """Verify HOLDOUT was strictly quarantined (0 loads, 0 inference, 0 forward passes)."""
    metrics_file = REPO_ROOT / "experiments/EXP-07/runs/EXP07_RUN003_SEED42/metrics.json"
    assert metrics_file.exists(), f"Missing {metrics_file}"

    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert metrics["holdout_access_count"] == 0, "HOLDOUT quarantine was breached!"

    telemetry_file = REPO_ROOT / "scratch/exp07_p0_c16_run_state.json"
    with open(telemetry_file, "r", encoding="utf-8") as f:
        telemetry = json.load(f)
    assert telemetry["holdout_access_count"] == 0


def test_single_replicate_seed42():
    """Verify exactly one replicate (Replicate 003, Seed 42) was executed and Seed 2024 was barred."""
    metrics_file = REPO_ROOT / "experiments/EXP-07/runs/EXP07_RUN003_SEED42/metrics.json"
    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert metrics["replicate_id"] == "REPLICATE_003"
    assert metrics["seed"] == 42
    assert metrics["seed2024_started"] is False


def test_checkpoint_validity_and_architecture():
    """Verify best checkpoint exists, matches SHA-256, loads cleanly, and matches exact architecture."""
    from ocean_sentinel.ml.exp07_reference import ResNet18UNet

    ckpt_path = REPO_ROOT / "experiments/EXP-07/runs/EXP07_RUN003_SEED42/best_model.pt"
    assert ckpt_path.exists(), f"Missing {ckpt_path}"

    # Verify SHA-256
    with open(ckpt_path, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest().upper()

    expected_sha256 = "936EF935F8049FA15FBC735F8073D08F074796ACC20BE0A2885DD35C7CB09D67"
    assert h == expected_sha256, f"Checksum mismatch: {h} vs {expected_sha256}"

    # Verify state dict loading and exact parameters
    state_dict = torch.load(ckpt_path, map_location="cpu")
    model = ResNet18UNet(in_channels=1, num_classes=12, pretrained=False)
    model.load_state_dict(state_dict)

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    bn_layers = sum(1 for m in model.modules() if isinstance(m, nn.BatchNorm2d))

    assert trainable_params == 14310860, f"Expected 14,310,860 parameters, got {trainable_params}"
    assert bn_layers == 30, f"Expected 30 BatchNorm2d layers, got {bn_layers}"


def test_training_metrics_and_early_stopping():
    """Verify metrics consistency, best epoch selection, and early stopping."""
    metrics_file = REPO_ROOT / "experiments/EXP-07/runs/EXP07_RUN003_SEED42/metrics.json"
    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert metrics["status"] == "COMPLETED"
    assert metrics["best_epoch"] == 17
    assert abs(metrics["best_dev_mIoU_phenomena"] - 0.049399) < 1e-4
    assert metrics["total_epochs_trained"] == 27  # Early stopping triggered at 27 (17 + 10 patience)


def test_metadata_artifacts_exist():
    """Verify all canonical C16 metadata artifacts exist."""
    required = [
        "scratch/exp07_p0_c16_run_state.json",
        "data/metadata/exp07_p0_c16_training_environment_v1.json",
        "data/metadata/exp07_p0_c16_incident_register_v1.json",
        "data/metadata/exp07_p0_c16_reproducibility_v1.json",
        "experiments/EXP-07/runs/EXP07_RUN003_SEED42/metrics.json",
        "experiments/EXP-07/runs/EXP07_RUN003_SEED42/epoch_history.json",
        "experiments/EXP-07/runs/EXP07_RUN003_SEED42/training_environment.json",
        "experiments/EXP-07/runs/EXP07_RUN003_SEED42/best_model.pt",
        "experiments/EXP-07/runs/EXP07_RUN003_SEED42/last_model.pt",
    ]
    for r in required:
        assert (REPO_ROOT / r).exists(), f"Required artifact {r} does not exist!"
