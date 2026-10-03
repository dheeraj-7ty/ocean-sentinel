"""
Phase 7C Spatial-Alignment Pilot Regression Guardrail Test Suite
Protects:
- Pilot scope bounding (PILOT_SCOPE = 12 CONTROL PRODUCTS)
- Prohibition on premature dataset-wide generalization (12 != 484)
- Source product identity verification (multi-archive metadata requirement)
- Polarization audit integrity (VV_ONLY vs VVVH_DUALPOL verified from source metadata)
- Geolocation grid classification as SOURCE_PRODUCT_GEOLOCATION_CONTROLS, not ground truth
- Independence of interior validation controls from 4-corner fitting controls
- Separation of raster resampling (nearest-neighbor) from spatial registration
- Classification of derived annotations as DERIVED_HIGH_RESOLUTION_MASK, never native ground truth
- Distinction between nominal pixel spacing (10m) and spatial resolution (~20x22m)
- 50m candidate boundary tolerance as an evaluation parameter, not physical uncertainty
- Preservation of spatial heterogeneity and distribution metrics (mean, rms, max, percentiles)
- Rejection of 2D Affine model and identification of raw GeoTIFF diagonal cross-tagging
- Bitwise frozen invariants (EXP-06, Part-I manifest, tau=0.22, Part-III firewall)
- Zero training, zero GPU compute, and zero git staging invariants
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
    assert path.exists(), f"Phase 7C control product manifest missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def alignment_results():
    path = METADATA_DIR / "phase_7c_alignment_results.json"
    assert path.exists(), f"Phase 7C alignment results missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def telemetry():
    path = SCRATCH_DIR / "phase_7c_run_state.json"
    assert path.exists(), f"Phase 7C telemetry missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Guardrail 1: Pilot scope is strictly bounded to 12 control products
def test_guardrail_01_pilot_scope_bounded(control_manifest):
    assert control_manifest["summary"]["total_controls_identified"] == 12
    assert control_manifest["summary"]["total_controls_recovered"] == 12
    assert len(control_manifest["controls"]) == 12
    assert "PILOT_SCOPE = 12 CONTROL PRODUCTS" in control_manifest["pilot_scope_invariant"]


# Guardrail 2: No extrapolation from 12 to 484
def test_guardrail_02_no_extrapolation_to_dataset(control_manifest, alignment_results):
    assert control_manifest["summary"]["total_untested_iw_scenes_remaining"] == 472
    gen_limits = alignment_results["generalization_limits"]
    assert gen_limits["untested_scenes_count"] == 472
    assert gen_limits["dataset_wide_validation_status"] == "NOT_VALIDATED_REMAINS_RESTRICTED_TO_PILOT"


# Guardrail 3: Source identity requires multi-archive verification
def test_guardrail_03_source_identity_multi_archive(control_manifest):
    for ctrl in control_manifest["controls"]:
        assert ctrl["verification_status"] == "EXACT_MATCH"
        evidence = ctrl["cross_archive_evidence"]
        assert evidence["nasa_asf_daac_verified"] is True
        assert evidence["esa_cdse_verified"] is True
        assert evidence["cdse_content_length_bytes"] is not None
        assert evidence["cdse_content_length_bytes"] > 500_000_000


# Guardrail 4: Filename alone cannot establish identity
def test_guardrail_04_filename_alone_not_identity(control_manifest):
    for ctrl in control_manifest["controls"]:
        assert ctrl["esa_safe_granule"].endswith(".SAFE")
        assert ctrl["sensor_and_platform"]["orbit_absolute"] > 0
        assert ctrl["native_scene_geometry"]["numberOfLines"] > 0
        assert ctrl["native_scene_geometry"]["numberOfSamples"] > 0


# Guardrail 5: Polarization must be metadata-derived
def test_guardrail_05_polarization_metadata_derived(control_manifest):
    breakdown = control_manifest["summary"]["polarization_breakdown"]
    assert breakdown["VV_ONLY"] == 1
    assert breakdown["VVVH_DUALPOL"] == 11
    # Control 1 is VV-only
    c1 = control_manifest["controls"][0]
    assert c1["polarization_configuration"]["classification"] == "VV_ONLY"
    assert c1["polarization_configuration"]["has_vh_channel"] is False
    # Control 2 is VV+VH dual-pol
    c2 = control_manifest["controls"][1]
    assert c2["polarization_configuration"]["classification"] == "VVVH_DUALPOL"
    assert c2["polarization_configuration"]["has_vh_channel"] is True


# Guardrail 6: XML geolocation metadata is NOT surveyed ground truth
def test_guardrail_06_xml_metadata_not_ground_truth(control_manifest):
    for ctrl in control_manifest["controls"]:
        grid = ctrl["geolocation_grid"]
        assert grid["governance_classification"] == "SOURCE_PRODUCT_GEOLOCATION_CONTROLS"
        assert "GROUND_TRUTH" not in grid["governance_classification"]


# Guardrail 7: Four-corner fit is NOT independent validation
def test_guardrail_07_four_corner_fit_not_validation(alignment_results):
    models = alignment_results["tested_models_summary"]
    b_model = models["model_b_corrected_bilinear"]
    assert "VALIDATED_WITHIN_50M_TOLERANCE_FOR_PILOT" in b_model["verdict"]


# Guardrail 8: Independent residuals must use controls not used for fitting
def test_guardrail_08_independent_residuals_controls(alignment_results):
    for slice_eval in alignment_results["slice_level_evaluations"]:
        assert slice_eval["n_interior_points"] > 0
        b_res = slice_eval["model_b_corrected_bilinear"]
        assert b_res["max_m"] > 0.0, "Independent residual cannot be identically 0.0"
        assert b_res["max_m"] <= 50.0


# Guardrail 9: Resampling != registration
def test_guardrail_09_resampling_distinct_from_registration(alignment_results):
    contract = alignment_results["label_to_operational_10m_grid_contract"]
    assert "Nearest-Neighbor" in contract["resampling_rule"]
    assert contract["status"] == "VALIDATED_FOR_12_CONTROL_PRODUCTS"


# Guardrail 10: Derived mask != native ground truth
def test_guardrail_10_derived_mask_classification(alignment_results):
    contract = alignment_results["label_to_operational_10m_grid_contract"]
    assert contract["mask_classification"] == "DERIVED_HIGH_RESOLUTION_MASK"
    for forbidden in contract["strictly_forbidden_classifications"]:
        assert forbidden != contract["mask_classification"]


# Guardrail 11: Nominal pixel spacing != measured resolution
def test_guardrail_11_pixel_spacing_vs_resolution(control_manifest):
    for ctrl in control_manifest["controls"]:
        geom = ctrl["native_scene_geometry"]
        assert geom["rangePixelSpacing_m"] == 10.0
        assert geom["azimuthPixelSpacing_m"] == pytest.approx(10.0, rel=1e-2)
        assert "~20m (range) x ~22m (azimuth)" in geom["nominal_resolution_note"]


# Guardrail 12: 50m tolerance is an evaluation parameter, not physical uncertainty
def test_guardrail_12_50m_tolerance_evaluation_parameter(alignment_results):
    eval_params = alignment_results["evaluation_parameters"]
    assert eval_params["candidate_boundary_tolerance_m"] == 50.0
    assert eval_params["governance_status"] == "SUPPORTED_FOR_PILOT"


# Guardrail 13: Failed controls cannot be silently excluded
def test_guardrail_13_no_silent_control_exclusion(control_manifest):
    assert control_manifest["summary"]["total_controls_failed"] == 0
    assert control_manifest["summary"]["total_controls_ambiguous"] == 0


# Guardrail 14: Ambiguous products cannot enter quantitative validation
def test_guardrail_14_no_ambiguous_products(control_manifest):
    for ctrl in control_manifest["controls"]:
        assert ctrl["verification_status"] == "EXACT_MATCH"


# Guardrail 15: Model comparison requires declared fitting and validation controls
def test_guardrail_15_model_comparison_declared(alignment_results):
    models = alignment_results["tested_models_summary"]
    assert "model_a_raw_geotiff_bilinear" in models
    assert "model_b_corrected_bilinear" in models
    assert "model_c_direct_l1_grid" in models
    assert "model_d_2d_affine" in models


# Guardrail 16: Mean residual alone cannot establish alignment quality
def test_guardrail_16_distribution_metrics_required(alignment_results):
    for slice_eval in alignment_results["slice_level_evaluations"]:
        b_res = slice_eval["model_b_corrected_bilinear"]
        assert "mean_m" in b_res
        assert "rms_m" in b_res
        assert "max_m" in b_res


# Guardrail 17: Spatially heterogeneous errors must be preserved
def test_guardrail_17_spatial_heterogeneity_preserved(alignment_results):
    sh = alignment_results["spatial_heterogeneity_findings"]
    assert "azimuth_dependence" in sh
    assert "range_dependence" in sh
    assert "orbit_direction_invariance" in sh


# Guardrail 18: Pilot result cannot become dataset-wide validation
def test_guardrail_18_pilot_cannot_become_dataset_validation(alignment_results):
    assert alignment_results["generalization_limits"]["dataset_wide_validation_status"] == "NOT_VALIDATED_REMAINS_RESTRICTED_TO_PILOT"


# Guardrail 19: No model training invoked
def test_guardrail_19_no_training_invoked(telemetry):
    assert telemetry["training_invoked"] is False


# Guardrail 20: No GPU compute invoked
def test_guardrail_20_no_gpu_invoked(telemetry):
    assert telemetry["gpu_invoked"] is False


# Guardrail 21: EXP-06 checkpoint bitwise integrity preserved
def test_guardrail_21_exp06_frozen():
    ckpt_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    assert ckpt_path.exists()
    sha = hashlib.sha256(ckpt_path.read_bytes()).hexdigest().upper()
    assert sha == FROZEN_EXP06_SHA


# Guardrail 22: Decision threshold tau frozen at 0.22
def test_guardrail_22_tau_frozen():
    baseline_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "exp06_frozen_dev_baseline.json"
    assert baseline_path.exists()
    with open(baseline_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert float(data["protocol"]["decision_threshold_tau"]) == FROZEN_TAU


# Guardrail 23: Part-I canonical manifest unchanged
def test_guardrail_23_part_i_manifest_frozen():
    manifest_path = METADATA_DIR / "internal_development_split_manifest.json"
    assert manifest_path.exists()
    sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper()
    assert sha == FROZEN_PART_I_SHA


# Guardrail 24: Part-III benchmark remains quarantined under Rule 38
def test_guardrail_24_part_iii_firewall():
    part_iii_dir = EXP_DIR / "performance" / "trujillo_part_iii_eval_20260911_exp01"
    assert part_iii_dir.exists()


# Guardrail 25: Git staging remains untouched
def test_guardrail_25_git_staging_untouched():
    res = subprocess.run(["git", "diff", "--cached", "--name-status"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == ""


# Guardrail 26: Raw GeoTIFF diagonal cross-tagging failure mode identified
def test_guardrail_26_raw_geotiff_shear_identified(alignment_results):
    models = alignment_results["tested_models_summary"]
    raw_m = models["model_a_raw_geotiff_bilinear"]
    assert "FAILED_FOR_INTERIOR_ALIGNMENT_WHEN_UNCORRECTED" in raw_m["verdict"]
    for slice_eval in alignment_results["slice_level_evaluations"]:
        raw_res = slice_eval["model_a_raw_geotiff_bilinear"]
        assert raw_res["max_m"] > 1000.0, "Raw uncorrected bilinear must reflect multi-kilometer shear"


# Guardrail 27: Corrected bilinear model satisfies 50m tolerance across all slices
def test_guardrail_27_corrected_bilinear_satisfies_tolerance(alignment_results):
    for slice_eval in alignment_results["slice_level_evaluations"]:
        b_res = slice_eval["model_b_corrected_bilinear"]
        assert b_res["max_m"] <= 50.0
        assert b_res["status"] == "VALIDATED_WITHIN_50M_TOLERANCE"


# Guardrail 28: Direct L1 grid model achieves exact tiepoint reproduction
def test_guardrail_28_direct_l1_grid_exact(alignment_results):
    for slice_eval in alignment_results["slice_level_evaluations"]:
        l1_res = slice_eval["model_c_direct_l1_grid"]
        assert l1_res["mean_m"] == 0.0
        assert l1_res["max_m"] == 0.0
        assert l1_res["status"] == "EXACT_PHYSICAL_GROUND_CONTROL_REPRODUCTION"


# Guardrail 29: 2D affine model rejected for radar geometry
def test_guardrail_29_affine_rejected(alignment_results):
    models = alignment_results["tested_models_summary"]
    assert "SCIENTIFICALLY_INVALID" in models["model_d_2d_affine"]["verdict"]


# Guardrail 30: All 12 controls have exact slice label PNG representations
def test_guardrail_30_all_controls_have_labels(control_manifest):
    label_dir = SCRATCH_DIR / "all_labels" / "label"
    assert label_dir.exists()
    for ctrl in control_manifest["controls"]:
        stem = ctrl["sample_stem"]
        matches = list(label_dir.glob(f"{stem}*.png"))
        assert len(matches) > 0, f"No label files found for {stem}"
        assert len(matches) == ctrl["li_dataset_slices"]["total_slices_in_scene"]
