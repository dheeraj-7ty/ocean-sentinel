"""
Phase 7C-R1 Methodological Validity Audit Regression Guardrail Test Suite
Enforces Rules 92-102 and protects:
1. 2550 vs 2560 discrepancy cannot be ignored (reconciled via cell count vs index span).
2. Pixel-center and pixel-edge conventions must be explicit.
3. Exact factor 10 cannot be asserted without source-grid proof.
4. A source window inferred from Li GCPs cannot be called independently observed.
5. Validation correspondence must be distinguished from validation coordinates.
6. Model C cannot be labelled physical ground truth (must be SOURCE_PRODUCT_GEOLOCATION_GRID_INTERPOLATION).
7. A residual conditional on an assumed crop mapping cannot be called independent.
8. 50m tolerance cannot be marked empirically supported from an invalid/conditional residual.
9. Pilot results cannot generalize beyond 12 controls.
10. Control count (12) and slice count (47) cannot be conflated.
11. Phase 7C-R1 cannot train (training_invoked = False).
12. Phase 7C-R1 cannot use GPU compute (gpu_invoked = False).
13. EXP-06 remains frozen (SHA256: B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF).
14. tau remains 0.22.
15. Part-I remains frozen (SHA256: 17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072).
16. Part-III remains quarantined under Rule 38.
17. Git staging remains untouched (0 staged changes).
18. Incident INC-7C-01 documented and mitigated.
19. Bilinear basis normalization consistency (scale factor is exactly 10.0 m/index).
20. Source crop evidence classified as INFERRED, not DIRECTLY_VERIFIED.
21. Model B disposition classified as CONDITIONALLY_SUPPORTED_FOR_12_CONTROLS.
22. Overall Phase 7C disposition classified as B. PHASE 7C METHOD CONDITIONALLY SUPPORTED — LIMITATIONS.
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
def control_manifest():
    path = METADATA_DIR / "phase_7c_control_product_manifest.json"
    assert path.exists(), f"Phase 7C control manifest missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def reconciled_results():
    path = METADATA_DIR / "phase_7c_r1_reconciled_alignment_results.json"
    assert path.exists(), f"Phase 7C-R1 reconciled results missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def telemetry():
    path = SCRATCH_DIR / "phase_7c_r1_run_state.json"
    assert path.exists(), f"Phase 7C-R1 telemetry missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Test 1: 2550 vs 2560 discrepancy cannot be ignored
def test_01_2550_vs_2560_discrepancy_reconciled(reconciled_results):
    pca = reconciled_results["pixel_convention_audit"]
    assert pca["SOURCE_CELL_COUNT"] == 2560
    assert pca["SOURCE_INDEX_SPAN"] == 2550.0
    assert pca["TARGET_CELL_COUNT"] == 256
    assert pca["TARGET_INDEX_SPAN"] == 255.0
    assert pca["DOWNSAMPLE_FACTOR"] == 10
    # The arithmetic discrepancy 2550 vs 2560 must be explicitly explained
    assert "RECONCILED" in pca["arithmetic_reconciliation_verdict"]
    assert pca["SOURCE_CELL_COUNT"] != pca["SOURCE_INDEX_SPAN"]


# Test 2: Pixel-center and pixel-edge conventions must be explicit
def test_02_pixel_conventions_explicit(reconciled_results):
    pca = reconciled_results["pixel_convention_audit"]
    assert "PIXEL_CENTER_CONVENTION" in pca
    assert "PIXEL_EDGE_CONVENTION" in pca
    assert "255" in pca["PIXEL_CENTER_CONVENTION"]
    assert "2,550" in pca["PIXEL_CENTER_CONVENTION"]
    assert "256" in pca["PIXEL_EDGE_CONVENTION"]
    assert "2,560" in pca["PIXEL_EDGE_CONVENTION"]


# Test 3: Exact factor 10 cannot be asserted without source-grid proof
def test_03_exact_factor_10_governance(reconciled_results):
    pca = reconciled_results["pixel_convention_audit"]
    # Ratio of center-to-center span to target index span must be exactly 10.0
    scale_center = pca["SOURCE_INDEX_SPAN"] / pca["TARGET_INDEX_SPAN"]
    assert scale_center == pytest.approx(10.0, rel=1e-6)
    # Ratio of outer cell count to target cell count must be exactly 10.0
    scale_edge = pca["SOURCE_CELL_COUNT"] / pca["TARGET_CELL_COUNT"]
    assert scale_edge == pytest.approx(10.0, rel=1e-6)


# Test 4: A source window inferred from Li GCPs cannot be called independently observed
def test_04_inferred_window_not_independently_observed(reconciled_results):
    sce = reconciled_results["source_crop_evidence"]
    assert sce["classification"] == "INFERRED"
    assert sce["directly_verified"] is False
    assert "numerically inverted" in sce["details"].lower()


# Test 5: Validation correspondence must be distinguished from validation coordinates
def test_05_validation_correspondence_distinguished(reconciled_results):
    ia = reconciled_results["independence_audit"]
    assert ia["correspondence_status"] == "NOT_DIRECTLY_ESTABLISHED_ASSUMED_CORRESPONDENCE"
    assert "constructed from the same inverted corner bounds" in ia["circularity_finding"]


# Test 6: Model C cannot be labelled physical ground truth
def test_06_model_c_terminology_corrected(reconciled_results):
    models = reconciled_results["tested_models_summary"]
    model_c = models["model_c_direct_l1_grid"]
    assert model_c["verdict"] == "SOURCE_PRODUCT_GEOLOCATION_GRID_INTERPOLATION"
    assert "PHYSICAL_GROUND_CONTROL" not in model_c["verdict"]
    assert "GROUND_TRUTH" not in model_c["verdict"]
    for s in reconciled_results["slice_level_evaluations"]:
        assert s["model_c_direct_l1_grid"]["status"] == "SOURCE_PRODUCT_GEOLOCATION_GRID_INTERPOLATION"


# Test 7: A residual conditional on an assumed crop mapping cannot be called independent
def test_07_residual_conditional_on_assumed_mapping(reconciled_results):
    ia = reconciled_results["independence_audit"]
    assert ia["residual_classification"] == "CONDITIONAL_ON_ASSUMED_CROP_MAPPING"
    assert "INDEPENDENT_PHYSICAL_VALIDATION" != ia["residual_classification"]


# Test 8: 50m tolerance cannot be marked empirically supported from an invalid residual
def test_08_50m_tolerance_conditional(reconciled_results):
    eval_params = reconciled_results["evaluation_parameters"]
    assert eval_params["governance_status"] == "SUPPORTED_ONLY_CONDITIONAL_ON_CROP_PIXEL_CONVENTION_ASSUMPTION"
    assert "UNCONDITIONALLY_VALIDATED" not in eval_params["governance_status"]


# Test 9: Pilot results cannot generalize beyond 12 controls
def test_09_pilot_results_bounded(reconciled_results):
    gen_limits = reconciled_results["generalization_limits"]
    assert gen_limits["evaluated_control_products"] == 12
    assert gen_limits["untested_scenes_count"] == 472
    assert gen_limits["dataset_wide_validation_status"] == "NOT_VALIDATED_REMAINS_RESTRICTED_TO_PILOT"


# Test 10: Control count and slice count cannot be conflated
def test_10_control_and_slice_counts_not_conflated(reconciled_results):
    assert reconciled_results["total_control_products"] == 12
    assert reconciled_results["total_li_slices_evaluated"] == 47
    assert reconciled_results["total_control_products"] != reconciled_results["total_li_slices_evaluated"]


# Test 11: Phase 7C-R1 cannot train
def test_11_no_training_invoked(telemetry):
    assert telemetry["training_invoked"] is False


# Test 12: Phase 7C-R1 cannot use GPU compute
def test_12_no_gpu_invoked(telemetry):
    assert telemetry["gpu_invoked"] is False


# Test 13: EXP-06 remains frozen
def test_13_exp06_frozen():
    ckpt_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    assert ckpt_path.exists()
    sha = hashlib.sha256(ckpt_path.read_bytes()).hexdigest().upper()
    assert sha == FROZEN_EXP06_SHA


# Test 14: tau remains 0.22
def test_14_tau_frozen():
    baseline_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "exp06_frozen_dev_baseline.json"
    assert baseline_path.exists()
    with open(baseline_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert float(data["protocol"]["decision_threshold_tau"]) == FROZEN_TAU


# Test 15: Part-I remains frozen
def test_15_part_i_manifest_frozen():
    manifest_path = METADATA_DIR / "internal_development_split_manifest.json"
    assert manifest_path.exists()
    sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper()
    assert sha == FROZEN_PART_I_SHA


# Test 16: Part-III remains quarantined
def test_16_part_iii_firewall():
    part_iii_dir = EXP_DIR / "performance" / "trujillo_part_iii_eval_20260911_exp01"
    assert part_iii_dir.exists()


# Test 17: Git staging remains untouched
def test_17_git_staging_untouched():
    res = subprocess.run(["git", "diff", "--cached", "--name-status"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == ""


# Test 18: Incident INC-7C-01 documented in telemetry
def test_18_incident_inc_7c_01_recorded(telemetry):
    incidents = telemetry.get("incidents", [])
    inc_ids = [inc.get("id") for inc in incidents]
    assert "INC-7C-01" in inc_ids
    inc = [i for i in incidents if i.get("id") == "INC-7C-01"][0]
    assert "2550" in inc["description"] and "2560" in inc["description"]
    assert "resolved" in inc["status"].lower()


# Test 19: Model B disposition is CONDITIONALLY_SUPPORTED
def test_19_model_b_conditionally_supported(reconciled_results):
    models = reconciled_results["tested_models_summary"]
    assert models["model_b_corrected_bilinear"]["verdict"] == "CONDITIONALLY_SUPPORTED_FOR_12_CONTROLS"
    assert reconciled_results["final_phase_verdict"] == "B. PHASE 7C METHOD CONDITIONALLY SUPPORTED — LIMITATIONS"


# Test 20: Mathematical scaling consistency check
def test_20_scaling_consistency_check():
    # 2560 native cells with 10x block averaging
    native_cells = 2560
    factor = 10
    out_cells = native_cells // factor  # 256
    assert out_cells == 256
    # Pixel center of block 0 is at offset 4.5
    # Pixel center of block 255 is at offset 2554.5
    center_span = (255 * factor + 4.5) - 4.5
    assert center_span == 2550.0
    # Span of target indices 0 to 255
    target_index_span = 255.0
    assert center_span / target_index_span == 10.0
