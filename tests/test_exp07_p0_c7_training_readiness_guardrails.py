import hashlib
import json
from pathlib import Path
import pytest
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent

EXP06_BEST_MODEL_PATH = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
EXP06_EXPECTED_SHA256 = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"

PART1_MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "internal_development_split_manifest.json"
PART1_EXPECTED_SHA256 = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"

OPS01_MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "ops01_physical_dataset_manifest_v4.json"
OPS01_EXPECTED_SHA256 = "FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_frozen_hashes_preflight():
    """Verify EXP-06, Part-I, and OPS-01 v4 manifests match frozen SHA-256 hashes."""
    assert EXP06_BEST_MODEL_PATH.exists(), f"Missing EXP-06 model at {EXP06_BEST_MODEL_PATH}"
    assert sha256_file(EXP06_BEST_MODEL_PATH) == EXP06_EXPECTED_SHA256

    assert PART1_MANIFEST_PATH.exists(), f"Missing Part-I manifest at {PART1_MANIFEST_PATH}"
    assert sha256_file(PART1_MANIFEST_PATH) == PART1_EXPECTED_SHA256

    assert OPS01_MANIFEST_PATH.exists(), f"Missing OPS-01 v4 manifest at {OPS01_MANIFEST_PATH}"
    assert sha256_file(OPS01_MANIFEST_PATH) == OPS01_EXPECTED_SHA256


def test_training_protocol_frozen_contract():
    """Verify training protocol metadata contains exact frozen hyperparameters and C6 loss weights."""
    protocol_path = REPO_ROOT / "data" / "metadata" / "exp07_p0_c7_training_protocol_v1.json"
    assert protocol_path.exists()
    with open(protocol_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Optimizer
    opt = data["optimizer_specification"]
    assert opt["optimizer_name"] == "AdamW"
    assert opt["base_learning_rate"] == 0.0005
    assert opt["weight_decay"] == 0.01
    assert opt["betas"] == [0.9, 0.999]
    assert opt["gradient_clipping"]["max_norm"] == 1.0

    # Scheduler
    sched = data["learning_rate_schedule"]
    assert sched["schedule_type"] == "LinearWarmupCosineAnnealingLR"
    assert sched["warmup_epochs"] == 3
    assert sched["max_epochs"] == 30
    assert sched["min_lr"] == 1.0e-6

    # Batch dynamics & architecture
    batch = data["batch_and_optimization_dynamics"]
    assert batch["physical_minibatch_size"] == 8
    assert batch["gradient_accumulation_steps"] == 2
    assert batch["effective_optimization_batch_size"] == 16
    assert batch["batchnorm_statistical_batch_size"] == 8
    assert data["model_architecture"]["batchnorm_momentum"] == 0.05

    # Loss weights matching exact C6 values
    loss = data["loss_specification"]
    c6_weights = loss["class_weights"]
    assert pytest.approx(c6_weights["0"], abs=1e-5) == 0.273233
    assert pytest.approx(c6_weights["11"], abs=1e-5) == 12.159536
    assert pytest.approx(loss["max_min_ratio"], abs=1e-3) == 44.5024

    # Early stopping and epoch budget
    epochs = data["epoch_and_stopping_budget"]
    assert epochs["max_epochs"] == 30
    assert epochs["min_epochs"] == 15
    assert epochs["early_stopping_patience"] == 10
    assert epochs["early_stopping_min_delta"] == 0.005
    assert epochs["monitored_metric"] == "dev_mIoU_phenomena"


def test_experiment_matrix_contract():
    """Verify experiment matrix defines baseline run-001 and 2 replicates, prohibiting sweeps."""
    matrix_path = REPO_ROOT / "data" / "metadata" / "exp07_p0_c7_experiment_matrix_v1.json"
    assert matrix_path.exists()
    with open(matrix_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["runs"][0]["run_id"] == "EXP07_RUN001_SEED42"
    runs = data["runs"]
    assert len(runs) == 3
    run_ids = [r["run_id"] for r in runs]
    assert run_ids == ["EXP07_RUN001_SEED42", "EXP07_RUN002_SEED101", "EXP07_RUN003_SEED2024"]

    # All runs must have identical hyperparameters
    for r in runs:
        assert "AdamW" in r["optimizer"]
        assert "5e-4" in r["optimizer"]
        assert "1e-2" in r["optimizer"]

    assert data["sweeps_authorized"] is False
    assert data["hyperparameter_search_authorized"] is False


def test_failure_policy_contract():
    """Verify failure policy metadata specifies 7-step lifecycle and critical failure modes."""
    policy_path = REPO_ROOT / "data" / "metadata" / "exp07_p0_c7_failure_policy_v1.json"
    assert policy_path.exists()
    with open(policy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data["failure_lifecycle"]) == 7

    failure_modes = data["failure_modes"]
    mode_names = [m["name"] for m in failure_modes]
    assert "NaN or Inf Loss" in mode_names
    assert "Exploding Gradient Norm" in mode_names
    assert "Trivial All-Background Collapse" in mode_names
    assert "Out of Memory (OOM)" in mode_names
    assert "Corrupted Target Label" in mode_names
    assert "BatchNorm Statistics Instability" in mode_names


def test_resource_estimate_epistemic_integrity():
    """Verify resource estimates maintain strict epistemic classification and stay within limits."""
    res_path = REPO_ROOT / "data" / "metadata" / "exp07_p0_c7_resource_estimate_v1.json"
    assert res_path.exists()
    with open(res_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mem = data["memory_budget"]
    assert mem["peak_gpu_vram_mb"] < 3000.0  # Peak VRAM must be well below 3GB
    assert "ESTIMATED" in mem["status_peak_gpu_vram"]

    assert mem["status_model_parameters"] == "MEASURED"
    assert mem["model_parameters_bytes"] == 57290664

    storage = data["disk_storage_budget"]
    assert storage["status_storage"] == "CALCULATED"
    assert storage["total_storage_three_runs_mb"] < 2000.0  # Storage must be well below 2GB


def test_governance_rules_v1_integrity():
    """Verify GOV-RULE-062, 063, 064 are active and total rules count is 64."""
    gov_json_path = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_governance_rules_v1.json"
    assert gov_json_path.exists()
    with open(gov_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_rules"] >= 64
    rule_ids = {r["rule_id"]: r for r in data["rules"]}
    assert "GOV-RULE-062" in rule_ids
    assert "GOV-RULE-063" in rule_ids
    assert "GOV-RULE-064" in rule_ids

    assert rule_ids["GOV-RULE-062"]["status"] == "ACTIVE"
    assert rule_ids["GOV-RULE-063"]["status"] == "ACTIVE"
    assert rule_ids["GOV-RULE-064"]["status"] == "ACTIVE"

    # Verify markdown file also contains the rules
    gov_md_path = REPO_ROOT / "experiments" / "PROJECT_GOVERNANCE" / "ocean_sentinel_governance_rules_v1.md"
    assert gov_md_path.exists()
    with open(gov_md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    assert "GOV-RULE-062" in md_text
    assert "GOV-RULE-063" in md_text
    assert "GOV-RULE-064" in md_text


def test_holdout_firewall_quarantine():
    """Verify HOLDOUT cannot be accessed as a training partition in protocol."""
    protocol_path = REPO_ROOT / "data" / "metadata" / "exp07_p0_c7_training_protocol_v1.json"
    with open(protocol_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    firewall = data["holdout_firewall"]
    assert firewall["training_access"] == "BLOCKED"
    assert firewall["stopping_access"] == "BLOCKED"
    assert firewall["selection_access"] == "BLOCKED"
    assert "HOLDOUT_PARTIALLY_USED_FOR_SELECTION" in data["permanent_epistemic_disclosures"]["holdout_disclosure"]


def test_model_architecture_shape_and_parameter_invariants():
    """Verify ResNet18-UNet model has exactly 14,310,860 parameters and 30 BatchNorm layers."""
    from ocean_sentinel.ml.exp07_reference import ResNet18UNet

    model = ResNet18UNet(num_classes=12)
    param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    assert param_count == 14310860

    bn_count = sum(1 for m in model.modules() if isinstance(m, torch.nn.BatchNorm2d))
    assert bn_count == 30

    # Verification of forward pass tensor shapes (CPU-only)
    dummy_input = torch.zeros((2, 1, 256, 256), dtype=torch.float32)
    model.eval()
    with torch.no_grad():
        out = model(dummy_input)
    assert out.shape == (2, 12, 256, 256)
