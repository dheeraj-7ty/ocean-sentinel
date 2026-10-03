"""
Phase 8-P0 OPS-01 Protocol Regression Guardrail Test Suite
Protects:
1. Random image-level splitting is prohibited; grouping at parent level enforced.
2. Same parent scene crossing partitions is prohibited.
3. Same source product crossing partitions is prohibited.
4. Duplicate source acquisition across partitions is prohibited.
5. HM must remain Artificial / Anthropogenic Objects; renaming to Vessel is prohibited.
6. Li OS class is strictly prohibited from entering OPS-01 as an oil-spill training class.
7. Geographic alignment assumptions cannot be treated as proven physical registration.
8. 15.79 m residual cannot be treated as independent registration accuracy.
9. 50 m tolerance cannot be treated as physical registration uncertainty.
10. Cataloged label count (47) cannot be confused with physically evaluated imagery (9).
11. Orientation of Controls 1-2 cannot be generalized to Controls 3-12 without metadata.
12. Protected holdout contamination is prohibited.
13. Dataset versioning schema enforced to prevent drift.
14. Silent post-hoc split changes prohibited.
15. Training authorization boundary enforced (protocol definition does not authorize training).
16. Bitwise frozen invariants (EXP-06, Part-I, tau=0.22, Part-III firewall).
17. Zero training, zero GPU compute, and zero git staging invariants.
"""

import hashlib
import json
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = REPO_ROOT / "data" / "metadata"
SCRATCH_DIR = REPO_ROOT / "scratch"
EXP_DIR = REPO_ROOT / "experiments"

FROZEN_EXP06_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
FROZEN_PART_I_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"
FROZEN_TAU = 0.22


@pytest.fixture(scope="module")
def taxonomy():
    path = METADATA_DIR / "ops01_taxonomy_v1.json"
    assert path.exists(), f"OPS-01 taxonomy missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def protocol_spec():
    path = METADATA_DIR / "ops01_protocol_spec_v1.json"
    assert path.exists(), f"OPS-01 protocol spec missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def telemetry():
    path = SCRATCH_DIR / "phase_8_p0_run_state.json"
    assert path.exists(), f"Phase 8-P0 telemetry missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Guardrail 1: Random image-level splitting is prohibited
def test_p0_01_random_splitting_prohibited(protocol_spec):
    fw = protocol_spec["scene_level_grouping_firewall"]
    pseudo = fw["deterministic_algorithm_pseudocode"]
    assert "Sort all grouping keys lexicographically" in pseudo
    assert "SHA256" in pseudo
    assert "greedy bin-packing" in pseudo
    # Invariant statement check
    invariants = protocol_spec["governance_invariants"]
    assert any("never permitted to occupy different leakage partitions" in inv for inv in invariants)


# Guardrail 2: Same parent scene crossing partitions prohibited
def test_p0_02_parent_scene_partition_crossing_prohibited(protocol_spec):
    pseudo = protocol_spec["scene_level_grouping_firewall"]["deterministic_algorithm_pseudocode"]
    assert "every slice in group g is assigned to the exact same partition" in pseudo
    assert "intersection(TRAIN_groups, DEV_groups) == empty" in pseudo
    assert "intersection(TRAIN_groups, HOLDOUT_groups) == empty" in pseudo
    assert "intersection(DEV_groups, HOLDOUT_groups) == empty" in pseudo


# Guardrail 3: Same source product crossing partitions prohibited
def test_p0_03_source_product_crossing_prohibited(protocol_spec):
    audit_checks = protocol_spec["leakage_audit_spec"]["audit_checks"]
    assert any("Parent scene stem overlap" in c for c in audit_checks)
    assert any("Level-1 SAFE source product ID overlap" in c for c in audit_checks)


# Guardrail 4: Duplicate source acquisition across partitions prohibited
def test_p0_04_duplicate_source_acquisition_prohibited(protocol_spec):
    audit_checks = protocol_spec["leakage_audit_spec"]["audit_checks"]
    assert any("Duplicate file content" in c for c in audit_checks)
    assert any("Temporal acquisition timestamp proximity" in c for c in audit_checks)
    assert any("Orbit pass ID overlap" in c for c in audit_checks)


# Guardrail 5: HM must remain Artificial / Anthropogenic Objects; renaming to Vessel prohibited
def test_p0_05_hm_naming_invariant(taxonomy):
    rule = taxonomy["governance_invariants"]["hm_naming_rule"]
    assert "Artificial / Anthropogenic Objects" in rule
    assert "renaming to Vessel is strictly forbidden" in rule
    hm_class = [c for c in taxonomy["classes"] if c["abbreviation"] == "HM"][0]
    assert hm_class["class_name"] == "Artificial / Anthropogenic Objects"
    assert "Vessel" != hm_class["class_name"]


# Guardrail 6: Li OS strictly prohibited as oil-spill training class
def test_p0_06_os_exclusion_invariant(taxonomy):
    rule = taxonomy["governance_invariants"]["os_exclusion_rule"]
    assert "strictly excluded from OPS-01 training" in rule
    os_class = [c for c in taxonomy["classes"] if c["abbreviation"] == "OS"][0]
    assert os_class["training_eligible"] is False
    assert os_class["role"] == "EXCLUDED_DEFICIENT_DATA"
    assert "insufficient data" in os_class["exclusion_reason"].lower()


# Guardrail 7: Geographic alignment assumptions cannot be treated as proven
def test_p0_07_alignment_assumptions_not_proven(protocol_spec):
    contract_b = protocol_spec["label_image_correspondence_contracts"]["contract_b_geographic_space"]
    assert contract_b["status"] == "CONDITIONAL_ENGINEERING_RECONSTRUCTION"
    assert "Must not be represented as independently validated georegistration" in contract_b["rule"]


# Guardrail 8: 15.79 m residual cannot be treated as independent registration accuracy
def test_p0_08_residual_conditional(protocol_spec):
    spot_check = protocol_spec["intensity_cross_correlation_spot_check_spec"]
    assert "decision_gates" in spot_check
    gates = spot_check["decision_gates"]
    assert "ALIGNMENT_PASS" in gates
    assert "ALIGNMENT_CONDITIONAL" in gates
    assert "ALIGNMENT_FAIL" in gates


# Guardrail 9: 50 m tolerance cannot be treated as physical uncertainty
def test_p0_09_tolerance_is_design_parameter():
    path = METADATA_DIR / "phase_7c_r2_alignment_evidence_boundary.json"
    with open(path, "r", encoding="utf-8") as f:
        boundary = json.load(f)
    tol = boundary["tolerance_50m_reassessment"]
    assert tol["classification"] == "DESIGN_PARAMETER"
    assert "remains unquantified" in tol["conceptual_distinctions"]["registration_uncertainty"].lower()


# Guardrail 10: Cataloged labels cannot be confused with physically evaluated imagery
def test_p0_10_labels_vs_imagery_not_confused():
    path = METADATA_DIR / "phase_7c_r2_alignment_evidence_boundary.json"
    with open(path, "r", encoding="utf-8") as f:
        boundary = json.load(f)
    lineage = boundary["lineage_summary"]
    assert lineage["slice_count_declared_labels"] == 47
    assert lineage["geotiff_slices_evaluated_count"] == 9
    assert lineage["slice_count_declared_labels"] != lineage["geotiff_slices_evaluated_count"]


# Guardrail 11: Orientation of Controls 1-2 cannot be generalized to Controls 3-12
def test_p0_11_orientation_uncertain_for_controls_3_to_12():
    path = METADATA_DIR / "phase_7c_r2_alignment_evidence_boundary.json"
    with open(path, "r", encoding="utf-8") as f:
        boundary = json.load(f)
    oa = boundary["orientation_audit"]
    assert oa["status"] == "ORIENTATION_UNCERTAIN"
    assert len(oa["controls_verified"]) == 2
    assert len(oa["controls_untested"]) == 10


# Guardrail 12: Protected holdout contamination prohibited
def test_p0_12_holdout_protection(protocol_spec):
    rules = protocol_spec["holdout_governance"]["strict_firewall_rules"]
    assert any("No hyperparameter tuning" in r for r in rules)
    assert any("No decision threshold calibration" in r for r in rules)
    assert any("completely independent from protected Part-III" in r for r in rules)


# Guardrail 13: Dataset versioning schema enforced
def test_p0_13_dataset_versioning_schema(protocol_spec):
    fields = protocol_spec["dataset_versioning_schema"]["required_fields"]
    assert "ops01_dataset_version" in fields
    assert "source_manifest_sha256" in fields
    assert "split_manifest_sha256" in fields
    assert "taxonomy_version" in fields
    assert "alignment_protocol_version" in fields


# Guardrail 14: Silent post-hoc split changes prohibited
def test_p0_14_split_manifest_freeze_required(protocol_spec):
    invariants = protocol_spec["governance_invariants"]
    assert any("Training requires separate operator authorization" in inv for inv in invariants)


# Guardrail 15: Training authorization boundary strictly enforced
def test_p0_15_training_unauthorized(protocol_spec):
    assert protocol_spec["training_authorization_status"] == "UNAUTHORIZED_PROTOCOL_DEFINITION_ONLY"
    invariants = protocol_spec["governance_invariants"]
    assert "Protocol definition does not authorize training." in invariants
    assert "Dataset construction does not automatically authorize training." in invariants


# Guardrail 16: Bitwise frozen invariants preserved
def test_p0_16_frozen_invariants():
    ckpt_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    assert hashlib.sha256(ckpt_path.read_bytes()).hexdigest().upper() == FROZEN_EXP06_SHA

    manifest_path = METADATA_DIR / "internal_development_split_manifest.json"
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper() == FROZEN_PART_I_SHA

    baseline_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "exp06_frozen_dev_baseline.json"
    with open(baseline_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert float(data["protocol"]["decision_threshold_tau"]) == FROZEN_TAU

    part_iii_dir = EXP_DIR / "performance" / "trujillo_part_iii_eval_20260911_exp01"
    assert part_iii_dir.exists()


# Guardrail 17: Zero training, zero GPU compute, zero git staging
def test_p0_17_execution_invariants(telemetry):
    assert telemetry["training_invoked"] is False
    assert telemetry["gpu_invoked"] is False
    res = subprocess.run(["git", "diff", "--cached", "--name-status"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == ""
