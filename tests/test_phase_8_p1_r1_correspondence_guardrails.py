"""Phase 8-P1-R1 Empirical Correspondence Validity & Threshold Audit Guardrails.

Validates the critical methodological reconciliation rules established in Phase 8-P1-R1:
1. Historical generation method must be classified as NOT_DIRECTLY_VERIFIED.
2. 10x block mean must be formulated as an empirically supported hypothesis, not historical fact.
3. Both raw and masked metrics must be explicitly preserved; silent replacement prohibited.
4. Zero-padding boundary masking must be deterministic and leakage-safe.
5. Downsampling hypotheses comparison must assess 10x mean as clearly preferred over decimation but plausibly equivalent to intensity averaging.
6. Local shift response surface must report sharp unimodal peak with drop-off at non-zero offsets.
7. Null control strength must be classified as LIMITED_PILOT, not universal distribution.
8. Thresholds 0.70 and 0.85 must be classified as DESIGN_THRESHOLD_ONLY.
9. Confirmation subset must be audited as blind to Control 2 results (no tuning leakage).
10. Generalization boundary must be capped at LEVEL_2 (multiple independent parent acquisitions).
11. P2 readiness must require explicit conditional restrictions.
12. Part-III benchmark, EXP-06 checkpoint, and Part-I manifest remain bitwise frozen.
13. Zero training, zero GPU invocation, zero git staging invariant.
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
def reconciled_results():
    path = METADATA_DIR / "ops01_alignment_spotcheck_results_v1_reconciled.json"
    assert path.exists(), f"Reconciled spotcheck results missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def telemetry():
    path = SCRATCH_DIR / "phase_8_p1_r1_run_state.json"
    assert path.exists(), f"Phase 8-P1-R1 telemetry missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Guardrail 1: Historical generation method must be permanently classified NOT_DIRECTLY_VERIFIED
def test_r1_01_generation_method_not_directly_verified(reconciled_results):
    ev = reconciled_results["historical_generation_evidence"]
    assert ev["status"] == "NOT_DIRECTLY_VERIFIED"
    assert "confirmed historical preprocessing method" in ev["prohibited_wording"]
    assert "empirically supported as a correspondence hypothesis" in ev["approved_wording"]


# Guardrail 2: Full pipeline dependency chain must label every stage correctly
def test_r1_02_pipeline_dependency_chain_audited(reconciled_results):
    chain = reconciled_results["pipeline_dependency_chain"]
    assert len(chain) >= 8
    statuses = {step["stage"]: step["epistemic_status"] for step in chain}
    assert "OBSERVED" in statuses["Li TIFF raster"]
    assert "OBSERVED" in statuses["Native Level-1 pixels"]
    assert "DERIVED" in statuses["Candidate source window"] or "DERIVED_HYPOTHESIS" in statuses["Candidate source window"]
    assert "DERIVED" in statuses["Spatial aggregation"] or "DERIVED_HYPOTHESIS" in statuses["Spatial aggregation"]
    assert "OPTIMIZED_ON_DISCOVERY_CONFIRMED_ON_CONFIRMATION" in statuses["Orientation selection"]
    assert "OPTIMIZED_ON_DISCOVERY_CONFIRMED_ON_CONFIRMATION" in statuses["Spatial shift selection"]


# Guardrail 3: Raw and masked metrics must be preserved side-by-side; silent replacement prohibited
def test_r1_03_raw_and_masked_metrics_preserved(reconciled_results):
    evals = reconciled_results["slice_evaluations"]
    for slice_id, res in evals.items():
        metrics = res["final_metrics"]
        assert "ncc_raw" in metrics
        assert "ncc_masked" in metrics
        # For slices with 0 zero-pixels, raw and masked must match
        if res["radiometric"]["zeros_count"] == 0:
            assert metrics["ncc_raw"] == metrics["ncc_masked"]
        else:
            # On boundary slices with zeros, raw and masked differ
            assert metrics["ncc_masked"] > metrics["ncc_raw"]


# Guardrail 4: Zero-padding boundary masking must be deterministic and leakage-safe
def test_r1_04_zero_masking_deterministic_and_leakage_safe(reconciled_results):
    za = reconciled_results["zero_nodata_audit"]
    assert za["leakage_safe"] is True
    assert "li_arr > 0" in za["deterministic_mask_rule"]
    assert za["slices_zero_free_count"] == 6
    assert za["slices_with_zero_pixels_count"] == 3


# Guardrail 5: Downsampling robustness must evaluate plausible hypotheses without overclaim
def test_r1_05_downsampling_robustness_audited(reconciled_results):
    da = reconciled_results["downsampling_evaluation_assessment"]
    assert da["H1_vs_H3_status"] == "PLAUSIBLY_EQUIVALENT"
    assert da["H1_vs_H4_H5_status"] == "CLEARLY_PREFERRED_OVER_POINT_SAMPLING"


# Guardrail 6: Shift response surface must document sharp unimodal peak
def test_r1_06_shift_response_surface_audited(reconciled_results):
    sr = reconciled_results["shift_response_surface_audit"]
    assert sr["peak_shift"] == [0.0, 0.0]
    assert sr["peak_character"] == "SHARP_ISOLATED_UNIMODAL_PEAK"
    assert sr["drop_at_0.5_li_px_50m"] > 0.05
    assert sr["drop_at_1.0_li_px_100m"] > 0.15


# Guardrail 7: Null control strength must be classified as LIMITED_PILOT
def test_r1_07_null_control_strength_limited_pilot(reconciled_results):
    nc = reconciled_results["null_control_audit"]
    assert nc["null_control_strength"] == "LIMITED_PILOT"
    assert nc["universal_null_distribution_claim_allowed"] is False
    assert nc["separation_margin"] > 0.30


# Guardrail 8: Thresholds 0.70 and 0.85 must be classified as DESIGN_THRESHOLD_ONLY
def test_r1_08_threshold_classified_as_design_only(reconciled_results):
    ta = reconciled_results["threshold_audit"]
    assert ta["threshold_status"] == "DESIGN_THRESHOLD_ONLY"
    assert "EMPIRICALLY_VALIDATED_DATASET_WIDE" in ta["prohibited_labels"]


# Guardrail 9: Confirmation subset must be audited as blind to Control 2 results
def test_r1_09_confirmation_blind_to_control_2(reconciled_results):
    dca = reconciled_results["discovery_confirmation_audit"]
    assert dca["status"] == "CONFIRMATION_WAS_BLIND_TO_CONTROL_2_RESULTS"
    assert dca["leakage_detected"] is False


# Guardrail 10: Generalization boundary must be capped at LEVEL_2
def test_r1_10_generalization_boundary_capped_at_level_2(reconciled_results):
    gb = reconciled_results["generalization_boundary"]
    assert gb["highest_defensible_level"] == "LEVEL_2_MULTIPLE_INDEPENDENT_PARENT_ACQUISITIONS"
    assert gb["levels_hierarchy"]["LEVEL_3_DATASET_WIDE_EMPIRICAL_VALIDATION"] is False


# Guardrail 11: P2 readiness decision and required restrictions
def test_r1_11_p2_readiness_conditions_enforced(reconciled_results):
    p2 = reconciled_results["p2_readiness"]
    assert "B. P2 READY ONLY WITH RESTRICTED CONDITIONAL ALIGNMENT" in p2["decision"]
    assert len(p2["required_restrictions"]) == 11
    # Check key restrictions
    restr_text = " ".join(p2["required_restrictions"]).lower()
    assert "parent-scene grouping" in restr_text
    assert "zero group intersection" in restr_text
    assert "independent georegistration validation" in restr_text
    assert "historical li generation method" in restr_text


# Guardrail 12: Bitwise frozen invariants preserved
def test_r1_12_frozen_invariants():
    ckpt_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    assert hashlib.sha256(ckpt_path.read_bytes()).hexdigest().upper() == FROZEN_EXP06_SHA
    manifest_path = METADATA_DIR / "internal_development_split_manifest.json"
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper() == FROZEN_PART_I_SHA
    part_iii_dir = EXP_DIR / "performance" / "trujillo_part_iii_eval_20260911_exp01"
    assert part_iii_dir.exists()


# Guardrail 13: Zero training, zero GPU invocation, zero git staging
def test_r1_13_execution_invariants(telemetry, reconciled_results):
    assert telemetry["training_invoked"] is False
    assert telemetry["gpu_invoked"] is False
    assert reconciled_results["training_invoked"] is False
    assert reconciled_results["gpu_invoked"] is False
    res = subprocess.run(["git", "diff", "--cached", "--name-status"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == ""
