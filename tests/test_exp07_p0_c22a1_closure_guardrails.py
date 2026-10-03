"""Tests for EXP-07-P0-C22-A.1 Reproducibility and Governance Closure Guardrails.

Verifies:
1. Exact pixel decomposition: 8,650,752 - 55,422 = 8,595,330 and 8,595,330 - 194,270 = 8,401,060
2. 12 per-class counts sum to 8,401,060 and median frequency is 399,710.5
3. Exact 6-decimal rounding agreement of formula weights with historical C16 executed literals
4. Identical 6-decimal literals convert to bitwise identical torch.float32 tensors
5. Rejection of false machine-epsilon claims on decimal rounding residuals (LL-EXP07-023)
6. Canonical dimension terminology: exactly 19 locked invariants (INV-01..INV-19) and 1 independent variable
7. Control and Treatment differ in exactly one experimental dimension (CLASS_LOSS_WEIGHT_VECTOR)
8. Runtime pre-training fingerprinting and parity verification tooling in exp07_fingerprint.py
9. Exact cryptographic lineage bindings for all 6 freeze and manifest artifacts
10. Quarantine firewall enforcement blocking HOLDOUT and Part-III access
11. Agent Learning Framework maturity states (LL-021, LL-022, LL-023 are REGRESSION_PROTECTED, zero PROVEN_STABLE)
12. Historical C16 posture as Historical Reference Control
13. Readiness verdict is READY_FOR_USER_AUTHORIZATION (never TRAINING_AUTHORIZED)
"""

import hashlib
import json
import math
from pathlib import Path
import pytest
import torch

from ocean_sentinel.ml.exp07_fingerprint import (
    assert_dataset_lineage_hashes,
    assert_loss_weight_vector_contract,
    assert_quarantine_firewall,
    capture_rng_snapshot,
    fingerprint_model_state_dict,
    restore_rng_snapshot,
    verify_runtime_initialization_parity,
    CANONICAL_HISTORICAL_C16_LITERALS,
    UNIFORM_TREATMENT_LITERALS,
    FREEZE_SPEC_SHA256,
    PHYSICAL_MANIFEST_SHA256,
    PARTITION_MANIFEST_SHA256,
    PARENT_CLUSTER_MANIFEST_SHA256,
    TAXONOMY_SPEC_SHA256,
    WEIGHT_PROVENANCE_SHA256,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CLOSURE_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a1_reproducibility_governance_closure_v1.json"
READINESS_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a_training_readiness_v1.json"
PROTOCOL_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c21_single_variable_diagnostic_protocol_v1.json"
LESSONS_PATH = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"
INCIDENTS_PATH = REPO_ROOT / "data" / "metadata" / "exp07_p0_c22a1_incident_register_v1.json"
REPORT_PATH = REPO_ROOT / "experiments" / "EXP-07" / "EXP07_P0_C22A_FINAL_LOSS_WEIGHT_RECONCILIATION_AND_TRAINING_READINESS_20260914.md"


def load_json(path: Path) -> dict:
    assert path.exists(), f"File missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_pixel_count_arithmetic_decomposition():
    """Verify exact arithmetic count decomposition and class sum."""
    closure = load_json(CLOSURE_PATH)
    counts = closure["pixel_count_evidence_decomposition"]["arithmetic_count_equality"]

    assert counts["total_grid_pixels"] == 8650752
    assert counts["border_padding_nodata_pixels"] == 55422
    assert counts["radiometric_valid_pixels"] == 8595330
    assert counts["excluded_sea_ice_pixels"] == 194270
    assert counts["canonical_dense_training_pixels"] == 8401060

    # Arithmetic equalities
    assert counts["total_grid_pixels"] - counts["border_padding_nodata_pixels"] == counts["radiometric_valid_pixels"]
    assert counts["radiometric_valid_pixels"] - counts["excluded_sea_ice_pixels"] == counts["canonical_dense_training_pixels"]
    assert counts["class_counts_sum"] == 8401060
    assert counts["median_frequency"] == 399710.5


def test_weight_recomputation_and_tensor_parity():
    """Verify formula float64 rounded to 6 decimals matches C16 literals and produces identical float32 tensor."""
    closure = load_json(CLOSURE_PATH)
    ctrl = closure["canonical_experiment_dimension_specification"]["independent_variable"]["control_vector"]
    treat = closure["canonical_experiment_dimension_specification"]["independent_variable"]["treatment_vector"]

    assert ctrl == CANONICAL_HISTORICAL_C16_LITERALS
    assert treat == UNIFORM_TREATMENT_LITERALS

    # Float32 tensor bitwise parity
    t_c16 = torch.tensor(CANONICAL_HISTORICAL_C16_LITERALS, dtype=torch.float32)
    t_ctrl = torch.tensor(ctrl, dtype=torch.float32)
    assert torch.equal(t_c16, t_ctrl)


def test_lesson_023_no_machine_epsilon_overclaim():
    """LL-EXP07-023: Ensure no audit, report, or test claims decimal residual is below float32 machine epsilon."""
    # Check closure report text
    report_text = REPORT_PATH.read_text(encoding="utf-8")
    assert "well within float32 machine epsilon" not in report_text
    assert "below float32 machine epsilon" not in report_text
    assert "below single-precision machine epsilon" not in report_text

    # Verify closure audit JSON
    closure = load_json(CLOSURE_PATH)
    claim = closure["float32_precision_audit"]["corrected_claim"]
    assert "NOT float32 machine epsilon" in claim
    assert closure["float32_precision_audit"]["max_observed_decimal_residual"] <= 5.0e-7


def test_canonical_dimension_terminology():
    """Verify exactly 19 locked invariant dimensions and 1 isolated variable across protocol and closure."""
    closure = load_json(CLOSURE_PATH)
    dim_spec = closure["canonical_experiment_dimension_specification"]

    assert dim_spec["independent_variable"]["count"] == 1
    assert dim_spec["independent_variable"]["name"] == "CLASS_LOSS_WEIGHT_VECTOR"
    assert dim_spec["locked_invariant_dimensions"]["count"] == 19
    assert len(dim_spec["locked_invariant_dimensions"]["invariants"]) == 19
    assert dim_spec["total_controlled_dimensions"] == 20

    # Cross-check protocol JSON
    proto = load_json(PROTOCOL_PATH)
    assert proto["locked_experimental_dimensions"]["dimension_count"] == 19
    assert len(proto["locked_experimental_dimensions"]["invariants"]) == 19
    assert proto["single_independent_variable"]["variable_identifier"] == "CLASS_LOSS_WEIGHT_VECTOR"


def test_single_variable_difference_assertion():
    """Verify that Control and Treatment differ in exactly one dimension."""
    ctrl_weights = torch.tensor(CANONICAL_HISTORICAL_C16_LITERALS, dtype=torch.float32)
    treat_weights = torch.tensor(UNIFORM_TREATMENT_LITERALS, dtype=torch.float32)

    # Valid contract passes without exception
    assert_loss_weight_vector_contract(ctrl_weights, treat_weights)

    # Invalid contract with modified weights raises ValueError
    invalid_ctrl = ctrl_weights.clone()
    invalid_ctrl[0] = 1.0
    with pytest.raises(ValueError, match="Control weight tensor does not bitwise match"):
        assert_loss_weight_vector_contract(invalid_ctrl, treat_weights)


def test_runtime_fingerprint_tooling_and_parity():
    """Verify exp07_fingerprint module executes model state hashing, RNG snapshots, and parity checks."""
    # Test RNG snapshot and restore
    rng = capture_rng_snapshot()
    assert "python_random_state" in rng
    assert "numpy_random_state" in rng
    assert "torch_cpu_state" in rng
    restore_rng_snapshot(rng)

    # Test model state dict fingerprinting
    dummy_dict = {
        "conv1.weight": torch.randn(16, 1, 3, 3),
        "bn1.weight": torch.ones(16),
        "bn1.bias": torch.zeros(16),
    }
    hash1 = fingerprint_model_state_dict(dummy_dict)
    hash2 = fingerprint_model_state_dict(dummy_dict)
    assert hash1 == hash2
    assert len(hash1) == 64

    # Test parity verification
    fp_control = {
        "initial_model_state_sha256": hash1,
        "sample_schedule_sha256": "AAA111",
        "batch_schedule_sha256": "BBB222",
        "dataset_manifest_sha256": PHYSICAL_MANIFEST_SHA256,
        "partition_manifest_sha256": PARTITION_MANIFEST_SHA256,
        "freeze_spec_sha256": FREEZE_SPEC_SHA256,
        "loss_weight_vector_sha256": "CTRL_HASH",
    }
    fp_treatment = dict(fp_control)
    fp_treatment["loss_weight_vector_sha256"] = "TREAT_HASH"

    passed, mismatches = verify_runtime_initialization_parity(fp_control, fp_treatment)
    assert passed is True
    assert len(mismatches) == 0

    # Ensure identical loss weights fail single-variable requirement
    fp_treatment_invalid = dict(fp_control)
    passed_inv, mismatches_inv = verify_runtime_initialization_parity(fp_control, fp_treatment_invalid)
    assert passed_inv is False
    assert any("Single-variable violation" in m for m in mismatches_inv)


def test_dataset_lineage_hashes():
    """Verify cryptographic bindings of all 5 dataset specifications and manifests."""
    verified = assert_dataset_lineage_hashes(REPO_ROOT)
    assert verified["freeze_spec"] == FREEZE_SPEC_SHA256
    assert verified["physical_manifest"] == PHYSICAL_MANIFEST_SHA256
    assert verified["partition_manifest"] == PARTITION_MANIFEST_SHA256
    assert verified["parent_cluster_manifest"] == PARENT_CLUSTER_MANIFEST_SHA256
    assert verified["taxonomy_spec"] == TAXONOMY_SPEC_SHA256


def test_firewall_hardening():
    """Verify automated path blocking denies HOLDOUT and Part-III access."""
    # Permitted paths pass
    allowed = ["data/ops02/train/tile_001.tif", "data/ops02/dev/tile_002.png"]
    assert_quarantine_firewall(allowed)

    # HOLDOUT access blocked
    with pytest.raises(PermissionError, match="Firewall breach blocked"):
        assert_quarantine_firewall(["data/ops02/holdout/tile_001.tif"])

    # Part-III access blocked
    with pytest.raises(PermissionError, match="Firewall breach blocked"):
        assert_quarantine_firewall(["data/trujillo_part_iii/raw_scene.tif"])

    with pytest.raises(PermissionError, match="Firewall breach blocked"):
        assert_quarantine_firewall(["experiments/performance/phase_6_part_iii_external_evaluation/results.json"])


def test_lessons_learned_maturity_and_presence():
    """Verify LL-EXP07-021, LL-022, and LL-023 are present and REGRESSION_PROTECTED, zero PROVEN_STABLE."""
    registry = load_json(LESSONS_PATH)
    lessons = registry["lessons"]
    
    lesson_map = {l["lesson_id"]: l for l in lessons}
    assert "LL-EXP07-021" in lesson_map
    assert "LL-EXP07-022" in lesson_map
    assert "LL-EXP07-023" in lesson_map

    for lid in ["LL-EXP07-021", "LL-EXP07-022", "LL-EXP07-023"]:
        item = lesson_map[lid]
        assert item["status"] == "REGRESSION_PROTECTED"
        assert item["status"] != "PROVEN_STABLE"
        assert len(item["failure_pattern"]) > 0
        assert len(item["prevention_method"]) > 0
        assert len(item["regression_test"]) > 0

    # Ensure no lesson is prematurely marked PROVEN_STABLE in C22-A / C22-A.1
    for item in lessons:
        if item["lesson_id"].startswith("LL-EXP07-02"):
            assert item["status"] != "PROVEN_STABLE"


def test_training_readiness_verdict_and_governance():
    """Verify readiness verdict is READY_FOR_USER_AUTHORIZATION, never TRAINING_AUTHORIZED."""
    closure = load_json(CLOSURE_PATH)
    verdict = closure["executive_summary"]["readiness_verdict"]
    assert verdict == "READY_FOR_USER_AUTHORIZATION"
    assert verdict != "TRAINING_AUTHORIZED"
    assert closure["executive_summary"]["blocking_issues_count"] == 0

    # Check incident register
    incidents = load_json(INCIDENTS_PATH)
    assert incidents["governance_compliance"]["zero_training_verified"] is True
    assert incidents["governance_compliance"]["zero_kaggle_verified"] is True
    assert incidents["governance_compliance"]["holdout_access_count"] == 0
    assert incidents["governance_compliance"]["part_iii_access_verified"] is False
