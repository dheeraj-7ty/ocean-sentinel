"""Test suite for EXP-07-P0-C22-A.5: Canonical-State Zero-Step Preflight Rehearsal and Pre-Training Gate.

Validates the canonical zero-step preflight rehearsal audit, canonical initial state,
pretrained backbone cryptographic identity, first-batch parity, first-forward logits equality,
loss boundary, BatchNorm safety, quarantine firewall, and pre-training readiness verdict.
"""

import hashlib
import json
import os
from pathlib import Path
import pytest
import torch
import torch.nn as nn

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a5_canonical_zero_step_preflight_v1.json"
INCIDENT_PATH = REPO_ROOT / "data" / "metadata" / "exp07_p0_c22a5_incident_register_v1.json"
CANONICAL_MODEL_PATH = REPO_ROOT / "data" / "ops02" / "initial_model_state_canonical.pt"
RANDOM_MODEL_PATH = REPO_ROOT / "data" / "ops02" / "initial_model_state.pt"
PRETRAINED_PATH = Path(os.path.expanduser("~/.cache/torch/hub/checkpoints/resnet18-f37072fd.pth"))
TELEMETRY_PATH = REPO_ROOT / "scratch" / "exp07_p0_c22a5_run_state.json"
LESSONS_PATH = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"

from ocean_sentinel.ml.exp07_reference import ResNet18UNet
from ocean_sentinel.ml.exp07_fingerprint import (
    CANONICAL_HISTORICAL_C16_LITERALS,
    UNIFORM_TREATMENT_LITERALS,
    assert_dataset_lineage_hashes,
    assert_loss_weight_vector_contract,
    assert_quarantine_firewall,
    fingerprint_model_state_dict,
)


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_canonical_rehearsal_audit_existence_and_status():
    """Verify that the C22-A.5 canonical zero-step preflight audit exists and confirms passed status."""
    assert AUDIT_PATH.exists(), f"Rehearsal audit missing at {AUDIT_PATH}"
    audit = load_json(AUDIT_PATH)

    assert audit["audit_metadata"]["audit_id"] == "OPS02_C22A5_CANONICAL_ZERO_STEP_PREFLIGHT_v1"
    assert audit["audit_metadata"]["task_id"] == "EXP-07-P0-C22-A.5"
    assert audit["audit_metadata"]["status"] == "PREFLIGHT_PASSED_CANONICAL_ZERO_STEP_VERIFIED"
    assert audit["readiness_verdict"] == "READY_FOR_USER_AUTHORIZATION"


def test_twenty_controlled_dimensions_taxonomy():
    """Verify the 20 controlled dimensions: 1 independent variable, 18 scientific invariants, 1 governance invariant."""
    audit = load_json(AUDIT_PATH)
    dim_spec = audit["authoritative_experiment_structure"]

    assert dim_spec["total_controlled_dimensions"] == 20
    assert dim_spec["independent_variable"]["name"] == "CLASS_LOSS_WEIGHT_VECTOR"
    assert dim_spec["independent_variable"]["vector_length"] == 12

    scientific_invariants = dim_spec["scientific_experimental_invariants"]
    governance_invariants = dim_spec["execution_governance_invariants"]

    assert len(scientific_invariants) == 18
    assert len(governance_invariants) == 1
    assert any("INV-03" in inv for inv in governance_invariants)
    assert not any("INV-03" in inv for inv in scientific_invariants)


def test_canonical_pretrained_backbone_dependency_and_sha256():
    """Verify local cache contains official resnet18-f37072fd.pth with complete SHA256."""
    assert PRETRAINED_PATH.exists(), f"Pretrained weights missing at {PRETRAINED_PATH}"
    file_bytes = PRETRAINED_PATH.read_bytes()
    assert len(file_bytes) == 46830571
    computed_sha256 = hashlib.sha256(file_bytes).hexdigest().upper()
    assert computed_sha256 == "F37072FD47E89C5E827621C5BAFFA7500819F7896BBACEC160B1A16C560E07EC"


def test_canonical_initial_state_artifact_and_strict_loading():
    """Verify data/ops02/initial_model_state_canonical.pt exists, matches SHA256, and loads strictly."""
    assert CANONICAL_MODEL_PATH.exists()
    file_bytes = CANONICAL_MODEL_PATH.read_bytes()
    assert len(file_bytes) == 57356426
    computed_sha256 = hashlib.sha256(file_bytes).hexdigest().upper()
    assert computed_sha256 == "67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D"

    loaded_sd = torch.load(CANONICAL_MODEL_PATH, map_location="cpu")
    assert len(loaded_sd) == 192

    model = ResNet18UNet(in_channels=1, num_classes=12, pretrained=False, bn_momentum=0.05)
    load_res = model.load_state_dict(loaded_sd, strict=True)
    assert len(load_res.missing_keys) == 0
    assert len(load_res.unexpected_keys) == 0

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    buffers = list(model.named_buffers())
    float_buf = sum(b.numel() for _, b in buffers if b.dtype in (torch.float32, torch.float64))
    int_buf = sum(b.numel() for _, b in buffers if b.dtype in (torch.int64, torch.int32, torch.int16, torch.int8, torch.uint8))
    total_elements = sum(v.numel() for v in loaded_sd.values())
    bn_count = sum(1 for m in model.modules() if isinstance(m, nn.BatchNorm2d))

    assert trainable_params == 14310860
    assert float_buf + int_buf == 11806
    assert total_elements == 14322666
    assert bn_count == 30


def test_historical_random_artifact_remains_preserved_and_classified():
    """Verify data/ops02/initial_model_state.pt remains intact with its historical random hash."""
    assert RANDOM_MODEL_PATH.exists()
    file_bytes = RANDOM_MODEL_PATH.read_bytes()
    assert len(file_bytes) == 57354338
    computed_sha256 = hashlib.sha256(file_bytes).hexdigest().upper()
    assert computed_sha256 == "4BB233DB629E44DE12E41F11809024B7A5BDA4DBCFB19D13752295973117E45C"


def test_first_batch_parity_and_logits_bitwise_equality():
    """Verify that Control and Treatment arms produce identical first-batch logits and checksums."""
    audit = load_json(AUDIT_PATH)
    fps = audit["parity_fingerprints"]

    assert fps["control_model_state_fingerprint"] == fps["treatment_model_state_fingerprint"]
    assert fps["batchnorm_pre_forward_equality"] is True
    assert fps["batchnorm_post_forward_equality"] is True
    assert fps["logits_bitwise_equality"] is True
    assert len(fps["first_batch_sample_ids"]) == 8
    assert len(fps["first_batch_input_tensor_checksum"]) == 64
    assert len(fps["first_batch_logits_checksum"]) == 64


def test_loss_boundary_and_single_variable_difference():
    """Verify that finite losses are computed and differ solely due to the loss weight vector."""
    audit = load_json(AUDIT_PATH)
    res = audit["first_forward_loss_results"]

    assert res["finite_loss_verified"] is True
    assert res["control_loss_batch_0"] > 0
    assert res["treatment_loss_batch_0"] > 0
    assert res["delta_loss_batch_0"] > 0
    assert res["backward_executed"] is False
    assert res["optimizer_step_executed"] is False
    assert res["scheduler_step_executed"] is False


def test_firewall_zero_holdout_and_zero_part_iii():
    """Verify strict quarantine firewall compliance: zero HOLDOUT access and zero Part-III access."""
    audit = load_json(AUDIT_PATH)
    fw = audit["firewall_compliance"]

    assert fw["holdout_access_count"] == 0
    assert fw["part_iii_access_count"] == 0
    assert fw["quarantine_firewall_verified"] is True


def test_incident_register_and_governance_boundaries():
    """Verify incident register catalogs zero-step canonical rehearsal with zero violations."""
    assert INCIDENT_PATH.exists()
    inc = load_json(INCIDENT_PATH)

    gov = inc["governance_compliance"]
    assert gov["zero_training_verified"] is True
    assert gov["zero_backward_verified"] is True
    assert gov["zero_optimizer_step_verified"] is True
    assert gov["zero_scheduler_step_verified"] is True
    assert gov["zero_kaggle_verified"] is True
    assert gov["holdout_access_count"] == 0
    assert gov["part_iii_access_count"] == 0


def test_learning_framework_lesson_024_status():
    """Verify LL-EXP07-024 remains REGRESSION_PROTECTED."""
    assert LESSONS_PATH.exists()
    lessons_data = load_json(LESSONS_PATH)
    lessons = {l["lesson_id"]: l for l in lessons_data.get("lessons", [])}

    assert "LL-EXP07-024" in lessons
    lsn = lessons["LL-EXP07-024"]
    assert lsn["status"] == "REGRESSION_PROTECTED"
    assert lsn["status"] != "PROVEN_STABLE"


def test_readiness_decision_is_ready_for_user_authorization():
    """Verify final readiness verdict is strictly READY_FOR_USER_AUTHORIZATION."""
    audit = load_json(AUDIT_PATH)
    assert audit["readiness_verdict"] == "READY_FOR_USER_AUTHORIZATION"
