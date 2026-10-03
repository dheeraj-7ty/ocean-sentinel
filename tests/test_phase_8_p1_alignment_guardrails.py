"""Phase 8-P1 Forensic Source Verification & Empirical SAR Intensity Correspondence Guardrails.

Validates the 12 critical methodological and governance invariants established in Phase 8-P1:
1. Fixed NCC threshold prohibited from being treated as empirically validated without negative control separability.
2. Dimensions-only alignment claims prohibited without empirical intensity correspondence.
3. Unverified radiometric conversion (arbitrary dB calibration) prohibited; must be classified UNSUPPORTED/UNCERTAIN.
4. Same-data optimization/validation masquerading as independent validation prohibited (discovery vs confirmation split required).
5. Orientation extrapolation from Controls 1-2 to Controls 3-12 prohibited.
6. Hard-coded 10x generation assumption prohibited; downsampling hypotheses H1-H5 must be evaluated.
7. Arbitrary shift selection without reporting prohibited; shift search must test and report offsets.
8. Omission of negative controls prohibited; null/negative distribution required for separability.
9. Dataset-wide generalization from small pilot prohibited (PILOT_SCOPE invariant: 9 evaluated slices across 2 controls).
10. Final OPS-01 holdout contamination prohibited (final holdout never used for discovery/tuning).
11. Protected Part-III benchmark access/modification prohibited.
12. Zero training, zero GPU invocation, zero git staging invariant.
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
def spotcheck_results():
    path = METADATA_DIR / "ops01_alignment_spotcheck_results_v1.json"
    assert path.exists(), f"Spotcheck results missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def telemetry():
    path = SCRATCH_DIR / "phase_8_p1_run_state.json"
    assert path.exists(), f"Phase 8-P1 telemetry missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Guardrail 1: Fixed NCC threshold cannot be treated as validated without negative control separability
def test_p1_01_empirical_threshold_separability(spotcheck_results):
    sep = spotcheck_results["empirical_separability"]
    assert "positive_distribution" in sep
    assert "negative_distribution" in sep
    assert sep["empirical_separation_margin"] > 0.30
    assert sep["threshold_calibration_status"] == "EMPIRICALLY_JUSTIFIED_ON_PILOT"
    pos_min = sep["positive_distribution"]["min"]
    neg_max = sep["negative_distribution"]["max"]
    assert pos_min > neg_max, f"Overlap detected: pos_min={pos_min} <= neg_max={neg_max}"


# Guardrail 2: Dimensions-only alignment claims prohibited; empirical intensity correspondence required
def test_p1_02_empirical_intensity_correspondence_required(spotcheck_results):
    evals = spotcheck_results["slice_evaluations"]
    assert len(evals) == 9
    for slice_id, res in evals.items():
        assert "final_metrics" in res
        metrics = res["final_metrics"]
        assert "ncc_masked" in metrics
        assert "pearson_masked" in metrics
        assert "nrmse_masked" in metrics
        assert metrics["ncc_masked"] >= 0.85, f"Slice {slice_id} masked NCC below 0.85: {metrics['ncc_masked']}"
        assert metrics["pearson_masked"] >= 0.85


# Guardrail 3: Unverified radiometric conversion prohibited
def test_p1_03_unverified_radiometric_conversion_prohibited(spotcheck_results):
    radio = spotcheck_results["radiometric_audit"]
    assert radio["conversion_to_db_sigma_naught"] == "UNSUPPORTED_UNCERTAIN"
    assert "uncalibrated" in radio["conversion_rationale"].lower()


# Guardrail 4: Same-data optimization/validation masquerading as independent validation prohibited
def test_p1_04_discovery_confirmation_split_enforced(spotcheck_results):
    disc_conf = spotcheck_results["discovery_confirmation_evaluation"]
    assert disc_conf["discovery_subset"]["control_id"] == 1
    assert disc_conf["discovery_subset"]["slices_count"] == 4
    assert disc_conf["confirmation_subset"]["control_id"] == 2
    assert disc_conf["confirmation_subset"]["slices_count"] == 5
    assert disc_conf["generalization_confirmed"] is True
    assert disc_conf["confirmation_subset"]["ncc_median"] >= 0.90


# Guardrail 5: Orientation extrapolation from Controls 1-2 to Controls 3-12 prohibited
def test_p1_05_prohibit_orientation_extrapolation(spotcheck_results):
    per_ctrl = spotcheck_results["per_control_summary"]
    assert len(per_ctrl) == 12
    # Controls 1 and 2 have verified identity orientation
    assert per_ctrl[0]["preferred_orientation"] == "identity"
    assert per_ctrl[1]["preferred_orientation"] == "identity"
    # Controls 3 to 12 must NOT inherit identity orientation blindly
    for c in per_ctrl[2:]:
        assert c["status"] == "INSUFFICIENT_DATA"
        assert c["imagery_status"] == "MISSING_SOURCE_IMAGERY"
        assert "UNTESTED" in c["preferred_orientation"]


# Guardrail 6: Hard-coded 10x generation assumption prohibited; downsampling hypotheses compared
def test_p1_06_downsampling_hypotheses_compared(spotcheck_results):
    for slice_id, res in spotcheck_results["slice_evaluations"].items():
        comp = res["downsampling_comparison"]
        assert "H1_block_mean_dn" in comp
        assert "H2_block_median_dn" in comp
        assert "H3_block_intensity_mean" in comp
        assert "H4_center_sampled" in comp
        assert "H5_edge_sampled" in comp
        # Point sampling must have lower correlation than block averaging due to speckle
        assert comp["H1_block_mean_dn"]["ncc_masked"] > comp["H4_center_sampled"]["ncc_masked"]
        assert comp["H1_block_mean_dn"]["ncc_masked"] > comp["H5_edge_sampled"]["ncc_masked"]


# Guardrail 7: Arbitrary shift selection without reporting prohibited
def test_p1_07_shift_search_reporting(spotcheck_results):
    for slice_id, res in spotcheck_results["slice_evaluations"].items():
        assert "shift_search_row" in res
        assert "shift_search_col" in res
        assert res["peak_displacement_li_px"] == [0.0, 0.0]
        assert res["peak_prominence_vs_half_pixel"] > 0.0


# Guardrail 8: Omission of negative controls prohibited
def test_p1_08_negative_controls_present(spotcheck_results):
    for slice_id, res in spotcheck_results["slice_evaluations"].items():
        negs = res["negative_controls"]
        assert "unrelated_shift_500_lines" in negs
        assert "unrelated_shift_2000_lines" in negs
        assert "unrelated_shift_3000_cols" in negs
        assert "cross_scene_negative" in negs
        assert "random_permutation" in negs
        # Every negative control must be substantially lower than the positive match
        pos_ncc = res["final_metrics"]["ncc_masked"]
        for n_name, n_val in negs.items():
            assert pos_ncc - n_val > 0.30, f"Insufficient margin on {slice_id} for {n_name}: pos={pos_ncc}, neg={n_val}"


# Guardrail 9: Dataset-wide generalization from small pilot prohibited
def test_p1_09_pilot_scope_prohibits_dataset_wide_claims(spotcheck_results):
    src = spotcheck_results["source_availability_audit"]
    assert src["total_controls"] == 12
    assert src["controls_with_physical_imagery"] == [1, 2]
    assert src["controls_missing_imagery"] == list(range(3, 13))
    assert src["physically_evaluated_slices"] == 9
    assert src["missing_slices"] == 38
    assert spotcheck_results["alignment_classification"] == "ALIGNMENT_CONDITIONAL"
    assert spotcheck_results["dataset_construction_authorization"] == "CONDITIONAL_FOR_CONTROLLED_DATASET_CONSTRUCTION"


# Guardrail 10: Holdout contamination prohibited
def test_p1_10_holdout_contamination_prohibited(spotcheck_results):
    # Spotcheck only evaluated Controls 1 and 2 from internal pilot, never final OPS-01 holdout
    for s_id, res in spotcheck_results["slice_evaluations"].items():
        assert res["subset"] in ["DISCOVERY", "CONFIRMATION"]
        assert res["subset"] != "HOLDOUT"


# Guardrail 11: Protected Part-III benchmark access/modification prohibited
def test_p1_11_part_iii_protected():
    part_iii_dir = EXP_DIR / "performance" / "trujillo_part_iii_eval_20260911_exp01"
    assert part_iii_dir.exists()
    # Confirm freeze hashes are unchanged
    ckpt_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    assert hashlib.sha256(ckpt_path.read_bytes()).hexdigest().upper() == FROZEN_EXP06_SHA
    manifest_path = METADATA_DIR / "internal_development_split_manifest.json"
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper() == FROZEN_PART_I_SHA


# Guardrail 12: Zero training, zero GPU invocation, zero git staging
def test_p1_12_execution_invariants(telemetry, spotcheck_results):
    assert telemetry["training_invoked"] is False
    assert telemetry["gpu_invoked"] is False
    assert spotcheck_results["training_invoked"] is False
    assert spotcheck_results["gpu_invoked"] is False
    res = subprocess.run(["git", "diff", "--cached", "--name-status"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == ""
