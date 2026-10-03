"""Test suite for EXP-07-P0-C22-A.2: Zero-Step Preflight Rehearsal and Final Authorization Gate.

Validates the end-to-end rehearsal audit, initial model state, first-batch parity,
forward pass boundary, loss contract, quarantine firewall, and governance readiness verdict.
"""

import hashlib
import json
from pathlib import Path
import pytest
import torch
import torch.nn as nn

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a2_zero_step_preflight_v1.json"
INCIDENT_PATH = REPO_ROOT / "data" / "metadata" / "exp07_p0_c22a2_incident_register_v1.json"
INITIAL_MODEL_PATH = REPO_ROOT / "data" / "ops02" / "initial_model_state.pt"
LESSONS_PATH = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"

from ocean_sentinel.ml.exp07_reference import ResNet18UNet
from ocean_sentinel.ml.exp07_fingerprint import (
    CANONICAL_HISTORICAL_C16_LITERALS,
    UNIFORM_TREATMENT_LITERALS,
    assert_dataset_lineage_hashes,
    assert_loss_weight_vector_contract,
    assert_quarantine_firewall,
)


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_rehearsal_audit_existence_and_status():
    """Verify that the zero-step preflight audit exists and confirms passed status."""
    assert AUDIT_PATH.exists(), f"Rehearsal audit missing at {AUDIT_PATH}"
    audit = load_json(AUDIT_PATH)

    assert audit["audit_metadata"]["audit_id"] == "OPS02_C22A2_ZERO_STEP_PREFLIGHT_v1"
    assert audit["audit_metadata"]["task_id"] == "EXP-07-P0-C22-A.2"
    assert audit["audit_metadata"]["status"] == "PREFLIGHT_PASSED_ZERO_STEP_VERIFIED"
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

    # Check INV-03 is explicitly classified under governance
    assert any("INV-03" in inv for inv in governance_invariants)
    assert not any("INV-03" in inv for inv in scientific_invariants)


def test_canonical_weight_vector_hashes():
    """Verify canonical compact and formatted JSON hashes for control and treatment weight vectors."""
    audit = load_json(AUDIT_PATH)
    iv = audit["authoritative_experiment_structure"]["independent_variable"]

    ctrl_compact = json.dumps(CANONICAL_HISTORICAL_C16_LITERALS, separators=(',', ':')).encode('utf-8')
    treat_compact = json.dumps(UNIFORM_TREATMENT_LITERALS, separators=(',', ':')).encode('utf-8')
    ctrl_formatted = json.dumps(CANONICAL_HISTORICAL_C16_LITERALS).encode('utf-8')
    treat_formatted = json.dumps(UNIFORM_TREATMENT_LITERALS).encode('utf-8')

    expected_ctrl_compact = hashlib.sha256(ctrl_compact).hexdigest().upper()
    expected_treat_compact = hashlib.sha256(treat_compact).hexdigest().upper()
    expected_ctrl_formatted = hashlib.sha256(ctrl_formatted).hexdigest().upper()
    expected_treat_formatted = hashlib.sha256(treat_formatted).hexdigest().upper()

    assert iv["control_vector_compact_json_sha256"] == expected_ctrl_compact
    assert iv["treatment_vector_compact_json_sha256"] == expected_treat_compact
    assert iv["control_vector_formatted_json_sha256"] == expected_ctrl_formatted
    assert iv["treatment_vector_formatted_json_sha256"] == expected_treat_formatted

    # Verify tensor conversion equality
    t_ctrl = torch.tensor(CANONICAL_HISTORICAL_C16_LITERALS, dtype=torch.float32)
    t_treat = torch.tensor(UNIFORM_TREATMENT_LITERALS, dtype=torch.float32)
    assert_loss_weight_vector_contract(t_ctrl, t_treat)


def test_initial_model_state_strict_identity():
    """Verify initial model state artifact hash, strict loading, parameter counts, and BN layer counts."""
    audit = load_json(AUDIT_PATH)
    model_audit = audit["initial_model_identity"]

    assert INITIAL_MODEL_PATH.exists()
    model_bytes = INITIAL_MODEL_PATH.read_bytes()
    expected_sha256 = hashlib.sha256(model_bytes).hexdigest().upper()

    assert model_audit["initial_model_state_sha256"] == expected_sha256
    assert model_audit["initial_model_state_sha256"] == "4BB233DB629E44DE12E41F11809024B7A5BDA4DBCFB19D13752295973117E45C"
    assert model_audit["pretrained_backbone_file_hash"] == "NOT_LOCALLY_VERIFIED"

    # Instantiate model and load state_dict strictly
    loaded_sd = torch.load(INITIAL_MODEL_PATH, map_location="cpu")
    model = ResNet18UNet(in_channels=1, num_classes=12, pretrained=False, bn_momentum=0.05)
    model.load_state_dict(loaded_sd, strict=True)

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    buffers = list(model.named_buffers())
    total_buffers = sum(b.numel() for _, b in buffers)
    total_elements = sum(v.numel() for v in loaded_sd.values())
    bn_count = sum(1 for m in model.modules() if isinstance(m, nn.BatchNorm2d))

    assert trainable_params == 14310860
    assert total_buffers == 11806
    assert total_elements == 14322666
    assert bn_count == 30
    assert model_audit["strict_load_verified"] is True


def test_first_batch_and_sampler_parity():
    """Verify first batch parity fingerprints in the rehearsal audit."""
    audit = load_json(AUDIT_PATH)
    fp = audit["parity_fingerprints"]

    assert fp["control_model_state_sha256"] == fp["treatment_model_state_sha256"]
    assert fp["batchnorm_pre_forward_equality"] is True
    assert fp["logits_bitwise_equality"] is True
    assert len(fp["first_batch_sample_ids"]) == 8
    assert len(fp["sampler_schedule_72_draws_sha256"]) == 64


def test_forward_loss_boundary_and_zero_training():
    """Verify loss was computed for batch 0 and zero training/backward/step occurred."""
    audit = load_json(AUDIT_PATH)
    loss_res = audit["first_forward_loss_results"]

    assert loss_res["finite_loss_verified"] is True
    assert 2.5 < loss_res["control_loss_batch_0"] < 2.7
    assert 2.5 < loss_res["treatment_loss_batch_0"] < 2.7
    assert abs(loss_res["delta_loss_batch_0"] - (loss_res["treatment_loss_batch_0"] - loss_res["control_loss_batch_0"])) < 1e-6

    # Absolute governance verification
    assert loss_res["backward_executed"] is False
    assert loss_res["optimizer_step_executed"] is False
    assert loss_res["scheduler_step_executed"] is False


def test_firewall_rehearsal_compliance():
    """Verify zero HOLDOUT and zero Part III access occurred during the preflight."""
    audit = load_json(AUDIT_PATH)
    fw = audit["firewall_compliance"]

    assert fw["holdout_access_count"] == 0
    assert fw["part_iii_access_count"] == 0
    assert fw["quarantine_firewall_verified"] is True

    # Safe synthetic denial check
    assert_quarantine_firewall(["data/ops02/train/sample_001.tif"])
    with pytest.raises(PermissionError, match="Firewall breach blocked"):
        assert_quarantine_firewall(["data/ops02/holdout/tile_999.tif"])


def test_incident_register_integrity():
    """Verify C22-A.2 incident register records zero blocking issues."""
    assert INCIDENT_PATH.exists()
    inc_data = load_json(INCIDENT_PATH)

    assert inc_data["governance_compliance"]["zero_training_verified"] is True
    assert inc_data["governance_compliance"]["zero_backward_verified"] is True
    assert inc_data["governance_compliance"]["zero_optimizer_step_verified"] is True
    assert inc_data["governance_compliance"]["zero_scheduler_step_verified"] is True
    assert inc_data["governance_compliance"]["zero_kaggle_verified"] is True
    assert inc_data["governance_compliance"]["holdout_access_count"] == 0
    assert inc_data["governance_compliance"]["part_iii_access_count"] == 0


def test_learning_framework_lessons_status():
    """Verify LL-EXP07-021, LL-EXP07-022, LL-EXP07-023 are REGRESSION_PROTECTED and none PROVEN_STABLE."""
    assert LESSONS_PATH.exists()
    lessons_data = load_json(LESSONS_PATH)
    lessons = {l["lesson_id"]: l for l in lessons_data.get("lessons", [])}

    for lid in ["LL-EXP07-021", "LL-EXP07-022", "LL-EXP07-023"]:
        assert lid in lessons, f"Lesson {lid} missing from registry"
        assert lessons[lid]["status"] == "REGRESSION_PROTECTED", f"Lesson {lid} not REGRESSION_PROTECTED"
        assert lessons[lid]["status"] != "PROVEN_STABLE", f"Lesson {lid} must not be marked PROVEN_STABLE"
