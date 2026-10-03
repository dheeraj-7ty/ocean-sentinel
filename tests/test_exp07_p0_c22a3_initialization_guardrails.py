"""Test suite for EXP-07-P0-C22-A.3: Canonical Initialization Lineage Forensic Gate.

Validates the initialization lineage audit, confirms current initial_model_state.pt is
non-canonical (random-initialized), enforces offline governance, and verifies that the
final readiness verdict is strictly BLOCKED.
"""

import hashlib
import json
import os
from pathlib import Path
import pytest
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c21_single_variable_diagnostic_protocol_v1.json"
INITIAL_MODEL_PATH = REPO_ROOT / "data" / "ops02" / "initial_model_state.pt"
GATE_AUDIT_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a3_initialization_lineage_gate_v1.json"
INCIDENT_PATH = REPO_ROOT / "data" / "metadata" / "exp07_p0_c22a3_incident_register_v1.json"
LESSONS_PATH = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"
TELEMETRY_PATH = REPO_ROOT / "scratch" / "exp07_p0_c22a3_run_state.json"

from ocean_sentinel.ml.exp07_reference import ResNet18UNet


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_authoritative_protocol_requires_imagenet_pretrained_backbone():
    """Verify that INV-10 in the canonical protocol explicitly requires ImageNet-pretrained weights."""
    assert PROTOCOL_PATH.exists()
    proto = load_json(PROTOCOL_PATH)
    invariants = {inv["id"]: inv for inv in proto["locked_experimental_dimensions"]["invariants"]}

    assert "INV-10" in invariants
    inv_10 = invariants["INV-10"]
    assert "ResNet18_Weights.IMAGENET1K_V1" in inv_10["value"]
    assert "resnet18-f37072fd.pth" in inv_10["value"]

    # Verify model initialization contract explicitly specifies conv1 adaptation and seed 42
    contract = proto["reproducibility_and_parity_contracts"]["model_initialization_contract"]
    assert contract["pretrained_backbone_identity"] == "torchvision.models.ResNet18_Weights.IMAGENET1K_V1"
    assert "Mean of 3 RGB pretrained channels" in contract["conv1_adaptation"]
    assert "42" in contract["decoder_head_initialization"]


def test_current_initial_model_state_is_random_and_non_canonical():
    """Verify that data/ops02/initial_model_state.pt bitwise matches random initialization with seed 42."""
    assert INITIAL_MODEL_PATH.exists()
    loaded_sd = torch.load(INITIAL_MODEL_PATH, map_location="cpu")

    # Instantiate un-pretrained model with seed 42
    torch.manual_seed(42)
    model_rand = ResNet18UNet(in_channels=1, num_classes=12, pretrained=False, bn_momentum=0.05)
    rand_sd = model_rand.state_dict()

    assert len(loaded_sd) == len(rand_sd) == 192
    for key in loaded_sd.keys():
        assert torch.equal(loaded_sd[key], rand_sd[key]), f"Discrepancy in tensor {key}"

    # Verify gate audit marks it NON_CANONICAL_INITIALIZATION_ARTIFACT
    audit = load_json(GATE_AUDIT_PATH)
    curr_audit = audit["forensic_audit_current_initial_model_state"]
    assert curr_audit["contains_imagenet_pretrained_weights"] is False
    assert curr_audit["classification"] == "NON_CANONICAL_INITIALIZATION_ARTIFACT"


def test_pretrained_file_not_locally_available_and_no_downloads():
    """Verify local cache lacked resnet18-f37072fd.pth in C22-A.3, or if provisioned in C22-A.4, it is authorized."""
    cache_dir = Path(os.path.expanduser("~/.cache/torch/hub/checkpoints"))
    target_file = cache_dir / "resnet18-f37072fd.pth"
    c22a4_manifest = REPO_ROOT / "data" / "ops02" / "manifests" / "exp07_diag01_initialization_lineage_v1.json"
    if not c22a4_manifest.exists():
        assert not target_file.exists(), "Pretrained weights unexpectedly exist in cache without authorization"
    else:
        assert target_file.exists(), "Authorized pretrained weights should exist once C22-A.4 is provisioned"

    audit = load_json(GATE_AUDIT_PATH)
    rec = audit["pretrained_file_availability_and_recovery"]
    assert rec["torch_hub_cache_result"] == "resnet18-f37072fd.pth NOT FOUND (only resnet34-b627a593.pth exists)"
    assert rec["recovery_outcome"] == "CANONICAL_INIT_STATE_NOT_RECOVERABLE"


def test_pairwise_parity_does_not_equal_canonical_provenance():
    """Verify that pairwise parity holds between two random models, but neither is canonical."""
    torch.manual_seed(42)
    m_control = ResNet18UNet(in_channels=1, num_classes=12, pretrained=False, bn_momentum=0.05)
    torch.manual_seed(42)
    m_treatment = ResNet18UNet(in_channels=1, num_classes=12, pretrained=False, bn_momentum=0.05)

    # Pairwise parity holds
    for k in m_control.state_dict().keys():
        assert torch.equal(m_control.state_dict()[k], m_treatment.state_dict()[k])

    # But canonical provenance is false (conv1 does not contain ImageNet weights)
    audit = load_json(GATE_AUDIT_PATH)
    analysis = audit["pairwise_vs_canonical_parity_analysis"]
    assert analysis["pairwise_parity_status"] == "VERIFIED_IN_C22A2"
    assert analysis["canonical_parity_status"] == "CONTRADICTED"


def test_c22a3_incident_register_records_critical_blocker():
    """Verify incident register catalogs INC-C22A3-001 with CRITICAL severity and BLOCKED status."""
    assert INCIDENT_PATH.exists()
    inc_data = load_json(INCIDENT_PATH)

    incidents = {inc["incident_id"]: inc for inc in inc_data["incidents_catalogued"]}
    assert "INC-C22A3-001" in incidents
    inc = incidents["INC-C22A3-001"]
    assert inc["severity"] == "CRITICAL"
    assert inc["status"] == "BLOCKED"
    assert inc["whether_current_evaluation_was_blocked"] is True


def test_lesson_024_pairwise_parity_does_not_prove_canonical_provenance():
    """Verify LL-EXP07-024 is registered in lessons learned as REGRESSION_PROTECTED."""
    assert LESSONS_PATH.exists()
    lessons_data = load_json(LESSONS_PATH)
    lessons = {l["lesson_id"]: l for l in lessons_data.get("lessons", [])}

    assert "LL-EXP07-024" in lessons
    lsn = lessons["LL-EXP07-024"]
    assert lsn["status"] == "REGRESSION_PROTECTED"
    assert lsn["status"] != "PROVEN_STABLE"
    assert "Pairwise parity is insufficient" in lsn["failure_pattern"] or "Conflating pairwise condition parity" in lsn["failure_pattern"]


def test_final_readiness_decision_is_blocked():
    """Verify the final readiness decision in C22-A.3 is strictly BLOCKED."""
    assert GATE_AUDIT_PATH.exists()
    audit = load_json(GATE_AUDIT_PATH)

    assert audit["readiness_decision"]["verdict"] == "BLOCKED"
    assert "BLOCKED supersedes READY_FOR_USER_AUTHORIZATION" in audit["readiness_decision"]["supersedes_c22a2_verdict"]


def test_governance_and_zero_training_compliance():
    """Verify zero training occurred, zero backward passes, and zero holdout access."""
    assert TELEMETRY_PATH.exists()
    telemetry = load_json(TELEMETRY_PATH)

    assert telemetry["training_started"] is False
    assert telemetry["backward_executed"] is False
    assert telemetry["optimizer_step_executed"] is False
    assert telemetry["scheduler_step_executed"] is False
    assert telemetry["kaggle_started"] is False
    assert telemetry["holdout_access"] is False
    assert telemetry["part_iii_access"] is False
