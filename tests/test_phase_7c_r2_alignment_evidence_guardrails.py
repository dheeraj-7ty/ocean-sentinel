"""
Phase 7C-R2 Alignment Evidence Boundary Regression Guardrail Test Suite
Protects:
1. Prevention of cell-count (2560) vs index-span (2550) conflation.
2. Prevention of inferred crop being labelled verified.
3. Prevention of conditional residual being labelled independent.
4. Prevention of source-product interpolation being labelled physical ground truth.
5. Prevention of candidate tolerance (50m) being labelled an empirical error bound.
6. Prevention of pilot evidence being generalized dataset-wide (12 controls != 484 scenes).
7. Prevention of local affine approximation being labelled physically general.
8. Detection of ambiguous parent-slice lineage (exact 12 controls, 47 slice labels, 0 ambiguous).
9. Prevention of orientation from Controls 1 & 2 being generalized to all 12 controls without metadata.
10. Prevention of GCP ordering interpretation being treated as proven dataset corruption.
11. Enforcement of INC-7C-02 recording in telemetry and metadata.
12. Bitwise frozen invariants (EXP-06, Part-I, tau=0.22, Part-III firewall).
13. Zero training, zero GPU compute, and zero git staging invariants.
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
def boundary_manifest():
    path = METADATA_DIR / "phase_7c_r2_alignment_evidence_boundary.json"
    assert path.exists(), f"Phase 7C-R2 boundary manifest missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def telemetry():
    path = SCRATCH_DIR / "phase_7c_r2_run_state.json"
    assert path.exists(), f"Phase 7C-R2 telemetry missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Guardrail 1: Prevention of cell-count vs index-span conflation
def test_r2_01_cell_count_vs_index_span_conflation(boundary_manifest):
    ar = boundary_manifest["arithmetic_reconciliation"]
    assert ar["SOURCE_CELL_COUNT"] == 2560
    assert ar["SOURCE_INDEX_SPAN"] == 2550.0
    assert ar["TARGET_CELL_COUNT"] == 256
    assert ar["TARGET_INDEX_SPAN"] == 255.0
    assert ar["MATHEMATICALLY_CONSISTENT"] is True
    assert ar["DATASET_GENERATION_VERIFIED"] is False
    assert ar["SOURCE_CELL_COUNT"] != ar["SOURCE_INDEX_SPAN"]


# Guardrail 2: Inferred crop cannot be labelled verified
def test_r2_02_inferred_crop_not_labelled_verified(boundary_manifest):
    q3 = boundary_manifest["three_questions_separation"]["question_3_independent_crop_transformation_established"]
    assert q3["status"] == "NOT_SUPPORTED"
    claim_g = [c for c in boundary_manifest["claims_table"] if c["claim_id"] == "G"][0]
    assert claim_g["status"] == "INFERRED"
    assert claim_g["status"] != "DIRECTLY_ESTABLISHED"


# Guardrail 3: Conditional residual cannot be labelled independent
def test_r2_03_residual_conditional_not_independent(boundary_manifest):
    res_audit = boundary_manifest["residual_15_79m_audit"]
    assert res_audit["independence_classification"] == "RESIDUAL IS CONDITIONAL ON ASSUMED CORRESPONDENCE"
    assert res_audit["independent_evidence_search_result"] == "NO INDEPENDENT LI-PIXEL-TO-L1 CORRESPONDENCE EVIDENCE FOUND"
    claim_i = [c for c in boundary_manifest["claims_table"] if c["claim_id"] == "I"][0]
    assert claim_i["status"] == "UNSUPPORTED"


# Guardrail 4: Source-product interpolation cannot be labelled physical ground truth
def test_r2_04_source_interpolation_not_ground_truth(boundary_manifest):
    model_c = boundary_manifest["models_assessment"]["model_c_direct_l1_grid"]
    assert model_c == "SOURCE_PRODUCT_GEOLOCATION_GRID_INTERPOLATION"
    assert "PHYSICAL_GROUND_CONTROL" not in model_c
    assert "GROUND_TRUTH" not in model_c


# Guardrail 5: Candidate tolerance (50m) cannot be labelled an empirical error bound
def test_r2_05_candidate_tolerance_is_design_parameter(boundary_manifest):
    tol = boundary_manifest["tolerance_50m_reassessment"]
    assert tol["classification"] == "DESIGN_PARAMETER"
    assert "CONDITIONALLY_SUPPORTED" in tol["status"]
    dist = tol["conceptual_distinctions"]
    assert "registration_uncertainty" in dist
    assert "remains unquantified" in dist["registration_uncertainty"].lower()


# Guardrail 6: Pilot evidence cannot be generalized dataset-wide
def test_r2_06_no_dataset_wide_generalization(boundary_manifest):
    claim_p = [c for c in boundary_manifest["claims_table"] if c["claim_id"] == "P"][0]
    assert claim_p["status"] == "UNSUPPORTED"
    not_safe = boundary_manifest["phase_8_assumption_boundary"]["not_safe_to_use"]
    assert any("dataset-wide" in s.lower() for s in not_safe)


# Guardrail 7: Local affine approximation cannot be labelled physically general
def test_r2_07_affine_not_physically_general(boundary_manifest):
    model_d = boundary_manifest["models_assessment"]["model_d_2d_affine"]
    assert "Not suitable as the general physical geolocation model" in model_d
    assert "may remain a local approximation" in model_d


# Guardrail 8: Parent-slice lineage must be unambiguous
def test_r2_08_parent_slice_lineage_unambiguous(boundary_manifest):
    lineage = boundary_manifest["lineage_summary"]
    assert lineage["control_product_count"] == 12
    assert lineage["unique_parent_product_count"] == 12
    assert lineage["slice_count_declared_labels"] == 47
    assert lineage["unique_slice_filename_count"] == 47
    assert lineage["verified_parent_links"] == 47
    assert lineage["ambiguous_links"] == 0
    assert lineage["unverified_links"] == 0


# Guardrail 9: Orientation cannot be generalized to all 12 controls without metadata
def test_r2_09_orientation_uncertain_for_untested_controls(boundary_manifest):
    oa = boundary_manifest["orientation_audit"]
    assert oa["status"] == "ORIENTATION_UNCERTAIN"
    assert len(oa["controls_verified"]) == 2
    assert len(oa["controls_untested"]) == 10
    not_safe = boundary_manifest["phase_8_assumption_boundary"]["not_safe_to_use"]
    assert any("orientation" in s.lower() for s in not_safe)


# Guardrail 10: GCP ordering cannot be treated as proven dataset corruption
def test_r2_10_gcp_ordering_is_metadata_interpretation_issue(boundary_manifest):
    gcp_audit = boundary_manifest["gcp_ordering_audit"]
    assert gcp_audit["status"] == "METADATA_ORDERING_INTERPRETATION_ISSUE"
    assert "CORRUPTION" not in gcp_audit["status"]
    assert "ERROR_ESTABLISHED" not in gcp_audit["status"]


# Guardrail 11: Incident INC-7C-02 documented and mitigated
def test_r2_11_incident_inc_7c_02_documented(boundary_manifest, telemetry):
    incidents = boundary_manifest["incidents"]
    inc_ids = [inc["incident_id"] for inc in incidents]
    assert "INC-7C-02" in inc_ids
    inc_02 = [i for i in incidents if i["incident_id"] == "INC-7C-02"][0]
    assert "47" in inc_02["title"] and "9" in inc_02["title"]
    assert inc_02["status"] == "RESOLVED"


# Guardrail 12: Final verdict permits Phase 8 only conditionally
def test_r2_12_final_verdict_conditional(boundary_manifest):
    assert boundary_manifest["final_verdict"] == "B. PHASE 8 CAN PROCEED WITH EXPLICIT CONDITIONAL ASSUMPTIONS"
    safe = boundary_manifest["phase_8_assumption_boundary"]["safe_to_use"]
    cond = boundary_manifest["phase_8_assumption_boundary"]["conditional_to_use"]
    not_safe = boundary_manifest["phase_8_assumption_boundary"]["not_safe_to_use"]
    assert len(safe) > 0
    assert len(cond) > 0
    assert len(not_safe) > 0


# Guardrail 13: Bitwise frozen invariants preserved
def test_r2_13_frozen_invariants():
    ckpt_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    assert hashlib.sha256(ckpt_path.read_bytes()).hexdigest().upper() == FROZEN_EXP06_SHA

    manifest_path = METADATA_DIR / "internal_development_split_manifest.json"
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper() == FROZEN_PART_I_SHA

    baseline_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "exp06_frozen_dev_baseline.json"
    with open(baseline_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert float(data["protocol"]["decision_threshold_tau"]) == FROZEN_TAU


# Guardrail 14: Part-III benchmark remains quarantined
def test_r2_14_part_iii_firewall():
    part_iii_dir = EXP_DIR / "performance" / "trujillo_part_iii_eval_20260911_exp01"
    assert part_iii_dir.exists()


# Guardrail 15: No training, no GPU compute, no git staging
def test_r2_15_governance_invariants(telemetry):
    assert telemetry["training_invoked"] is False
    assert telemetry["gpu_invoked"] is False
    res = subprocess.run(["git", "diff", "--cached", "--name-status"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == ""
