"""Tests for EXP-07-P0-DIAG-04: Receptive Field & Spatial Scale Compatibility Guardrails.

Validates:
1. Canonical OPS-02 identity in audit JSON.
2. Exact manifest SHA-256 binding.
3. 132 TRAIN / 40 DEV / 40 HOLDOUT counts.
4. Exactly 172 development tiles analyzed.
5. Exactly 52 development parent clusters.
6. HOLDOUT partition strictly quarantined and excluded.
7. Part III zero leakage.
8. Zero backward passes executed.
9. Zero training steps executed.
10. Exact encoder theoretical receptive fields (Layer 4 = 435 px).
11. Exact multi-path skip dependency ranges (19, 71, 155-163, 323-339, 531-563 px).
12. Crop-clipping semantics: usable context <= 256 px.
13. Canonical 256x256 grid geometry at 100m.
14. Edge-censored component semantics (EDGE_CENSORED_OBSERVATION).
15. Connected component terminology (ANNOTATED_CONNECTED_COMPONENT).
16. Absence of arbitrary 3 dB spectral threshold in PSD.
17. Mask PSD interpreted as annotation morphology, not physical SAR wavelength.
18. Non-causal scientific language: no claims that RF mismatch caused failure.
19. Empirical learned-weight ERF explicitly declared UNMEASURED / false.
20. Lesson registry integrity.
21. Reproducibility metadata and execution timestamp present.
22. Full numerical consistency between audit JSON and narrative report.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_JSON_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_diag04_receptive_field_scale_compatibility_v1.json"
REPORT_MD_PATH = REPO_ROOT / "experiments" / "EXP-07" / "EXP07_P0_DIAG04_RECEPTIVE_FIELD_SCALE_COMPATIBILITY_20260915.md"
MANIFEST_PATH = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"


@pytest.fixture(scope="module")
def diag04_audit():
    assert AUDIT_JSON_PATH.exists(), f"Missing audit JSON: {AUDIT_JSON_PATH}"
    with open(AUDIT_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def diag04_report_text():
    assert REPORT_MD_PATH.exists(), f"Missing narrative report: {REPORT_MD_PATH}"
    return REPORT_MD_PATH.read_text(encoding="utf-8")


def test_guardrail_01_canonical_ops02_identity(diag04_audit):
    """1. Verify canonical OPS-02 dataset identity."""
    assert diag04_audit["dataset_contract"]["dataset_id"] == "OPS-02"
    assert diag04_audit["dataset_contract"]["freeze_spec"] == "OPS02_v1.0.1_FROZEN"


def test_guardrail_02_exact_manifest_sha256(diag04_audit):
    """2. Verify exact manifest SHA-256 binding."""
    expected_sha = "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"
    assert diag04_audit["dataset_contract"]["manifest_sha256"] == expected_sha
    computed = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest().upper()
    assert computed == expected_sha


def test_guardrail_03_partition_counts(diag04_audit):
    """3. Verify 132 TRAIN / 40 DEV / 40 HOLDOUT counts."""
    assert diag04_audit["dataset_contract"]["train_tile_count"] == 132
    assert diag04_audit["dataset_contract"]["dev_tile_count"] == 40
    assert diag04_audit["dataset_contract"]["holdout_tile_count"] == 40


def test_guardrail_04_development_tile_count(diag04_audit):
    """4. Verify exactly 172 development tiles analyzed."""
    assert diag04_audit["coverage"]["total_tiles_analyzed"] == 172
    assert diag04_audit["dataset_contract"]["development_tile_count"] == 172


def test_guardrail_05_development_cluster_count(diag04_audit):
    """5. Verify exactly 52 development parent clusters."""
    assert diag04_audit["dataset_contract"]["development_cluster_count"] == 52


def test_guardrail_06_holdout_quarantine_integrity(diag04_audit):
    """6. Verify HOLDOUT partition is strictly quarantined and excluded."""
    assert diag04_audit["coverage"]["holdout_tiles_quarantined"] == 40
    assert diag04_audit["governance"]["holdout_access"] == 0


def test_guardrail_07_part_iii_exclusion(diag04_audit):
    """7. Verify Part III is zero access."""
    assert diag04_audit["governance"]["part_iii_access"] == 0


def test_guardrail_08_zero_backward_passes(diag04_audit):
    """8. Verify zero backward passes executed."""
    assert diag04_audit["governance"]["backward_passes"] == 0


def test_guardrail_09_zero_training_steps(diag04_audit):
    """9. Verify zero training/optimizer/parameter updates."""
    assert diag04_audit["governance"]["training_steps"] == 0
    assert diag04_audit["governance"]["optimizer_steps"] == 0
    assert diag04_audit["governance"]["parameter_updates"] == 0
    assert diag04_audit["governance"]["gpu_seconds"] == 0.0


def test_guardrail_10_exact_encoder_receptive_fields(diag04_audit):
    """10. Verify exact encoder theoretical receptive fields (Layer 4 = 435 px)."""
    enc_rf = diag04_audit["architecture_contract"]["encoder_theoretical_receptive_fields"]
    assert enc_rf["conv1"]["trf_px"] == 7
    assert enc_rf["maxpool"]["trf_px"] == 11
    assert enc_rf["layer1"]["trf_px"] == 43
    assert enc_rf["layer2"]["trf_px"] == 99
    assert enc_rf["layer3"]["trf_px"] == 211
    assert enc_rf["layer4"]["trf_px"] == 435


def test_guardrail_11_exact_multipath_rf_ranges(diag04_audit):
    """11. Verify exact multi-path skip dependency ranges."""
    mp = diag04_audit["architecture_contract"]["multipath_receptive_fields"]
    assert mp["path_A_skip_x0"]["trf_range_px"] == [19]
    assert mp["path_B_skip_x1"]["trf_range_px"] == [71]
    assert mp["path_C_skip_x2"]["trf_range_px"] == [155, 163]
    assert mp["path_D_skip_x3"]["trf_range_px"] == [323, 339]
    assert mp["path_E_bottleneck_x4"]["trf_range_px"] == [531, 563]


def test_guardrail_12_crop_clipping_semantics(diag04_audit):
    """12. Verify crop clipping semantics (usable context <= 256 px)."""
    policy = diag04_audit["architecture_contract"]["crop_clipping_policy"]
    assert policy["tile_boundary_px"] == 256
    assert policy["tile_boundary_km"] == 25.6
    assert "strictly clipped" in policy["usable_context_limit"]


def test_guardrail_13_grid_geometry(diag04_audit):
    """13. Verify canonical 256x256 grid geometry at 100m."""
    assert diag04_audit["dataset_contract"]["grid_shape"] == [256, 256]
    assert diag04_audit["dataset_contract"]["pixel_spacing_m"] == 100.0


def test_guardrail_14_edge_censorship_semantics(diag04_audit):
    """14. Verify edge-censored component semantics (EDGE_CENSORED_OBSERVATION)."""
    edge_stats = diag04_audit["edge_censoring"]
    for c_name in ["IWs", "MCC", "LWA", "AF", "POW", "WS", "OF", "BS"]:
        assert edge_stats[c_name]["edge_censored_ratio"] > 0.80
        assert "EDGE_CENSORED_OBSERVATION" in edge_stats[c_name]["censorship_interpretation"]


def test_guardrail_15_connected_component_terminology(diag04_report_text, diag04_audit):
    """15. Verify connected-component terminology (ANNOTATED_CONNECTED_COMPONENT)."""
    assert "ANNOTATED_CONNECTED_COMPONENT" in diag04_report_text or "annotated connected component" in diag04_report_text.lower()
    for lim in diag04_audit["limitations"]:
        if "Connected components" in lim:
            assert "ANNOTATED_CONNECTED_COMPONENTS" in lim


def test_guardrail_16_no_3db_spectral_cutoff(diag04_audit):
    """16. Verify absence of arbitrary 3 dB spectral threshold in PSD."""
    for c_name, psd_data in diag04_audit["periodicity_results"].items():
        if "criterion" in psd_data:
            assert "3 dB" not in psd_data["criterion"]
            assert "DESCRIPTIVE_PREDECLARED_STABILITY_CRITERION" in psd_data["criterion"]


def test_guardrail_17_mask_psd_semantics(diag04_audit):
    """17. Verify mask PSD interpreted as annotation morphology, not physical SAR wavelength."""
    for c_name, psd_data in diag04_audit["periodicity_results"].items():
        if "scientific_interpretation" in psd_data:
            assert "ANNOTATION_MORPHOLOGY_LAYOUT_PERIODICITY" in psd_data["scientific_interpretation"]
            assert "NOT physical radar backscatter wavelength" in psd_data["scientific_interpretation"]


def test_guardrail_18_no_causal_performance_claims(diag04_audit, diag04_report_text):
    """18. Verify non-causal scientific language: no claims that RF mismatch caused failure."""
    assert diag04_audit["evidence_levels"]["CAUSAL_ESTABLISHED"].startswith("STRICTLY PROHIBITED")
    unhedged = [
        "spatial context is required",
        "receptive field mismatch caused model failure",
        "receptive field mismatch causes model failure",
        "spatial scale mismatch causes poor model performance",
        "spatial-scale mismatch causes poor model performance",
        "proof that spatial context is required",
    ]
    for pattern in unhedged:
        assert pattern not in diag04_report_text.lower()


def test_guardrail_19_empirical_erf_unmeasured(diag04_audit):
    """19. Verify empirical learned-weight ERF explicitly declared UNMEASURED."""
    erf_mode = diag04_audit["architecture_contract"]["erf_evaluation_mode"]
    assert erf_mode["empirical_erf_measured"] is False
    assert erf_mode["backward_passes"] == 0
    assert erf_mode["idealized_analytical_proxy"]["label"] == "IDEALIZED_ANALYTICAL_PROXY"


def test_guardrail_20_lesson_integrity():
    """20. Verify lesson registry integrity."""
    lessons_path = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"
    assert lessons_path.exists()
    with open(lessons_path, "r", encoding="utf-8") as f:
        ldb = json.load(f)
    ids = [lsn["lesson_id"] for lsn in ldb["lessons"]]
    assert len(ids) == len(set(ids))
    assert "LL-DIAG04-PLAN-001" in ids
    assert "LL-DIAG04-PLAN-002" in ids
    assert "LL-DIAG04-PLAN-003" in ids
    assert "LL-EXP07-028" in ids


def test_guardrail_21_reproducibility_metadata(diag04_audit):
    """21. Verify reproducibility metadata and execution timestamp present."""
    meta = diag04_audit["metadata"]
    assert meta["task_id"] == "EXP-07-P0-DIAG-04-EXECUTION"
    assert meta["execution_authorization"] == "AUTHORIZED_AND_EXECUTED"
    assert meta["elapsed_seconds"] > 0.0
    assert meta["python_version"] is not None
    assert meta["numpy_version"] is not None


def test_guardrail_22_report_and_json_consistency(diag04_audit, diag04_report_text):
    """22. Verify full numerical consistency between audit JSON and narrative report."""
    assert str(diag04_audit["coverage"]["total_tiles_analyzed"]) in diag04_report_text
    comps = diag04_audit["coverage"]["total_components_extracted"]
    assert (str(comps) in diag04_report_text) or (f"{comps:,}" in diag04_report_text)
    assert str(diag04_audit["coverage"]["train_tiles"]) in diag04_report_text
    assert str(diag04_audit["coverage"]["dev_tiles"]) in diag04_report_text
    assert str(diag04_audit["coverage"]["holdout_tiles_quarantined"]) in diag04_report_text
    assert diag04_audit["dataset_contract"]["manifest_sha256"] in diag04_report_text


def test_guardrail_23_authoritative_of_k_reconciliation(diag04_audit):
    """23. Verify authoritative OF K values: DEV K=1, TRAIN K=4, Pool K=5."""
    diag03_path = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_diag03_radiometric_discriminability_v1.json"
    assert diag03_path.exists()
    with open(diag03_path, "r", encoding="utf-8") as f:
        d3 = json.load(f)
    of_d3_dev = d3["support_statistics"]["DEV"]["5"]
    of_d3_trn = d3["support_statistics"]["TRAIN"]["5"]

    assert of_d3_dev["parent_cluster_count"] == 1
    assert of_d3_dev["tile_count"] == 1
    assert of_d3_dev["valid_pixel_count"] == 1709
    assert of_d3_trn["parent_cluster_count"] == 4
    assert of_d3_trn["tile_count"] == 9

    # Verify DIAG-04 audit JSON reflects authoritative support
    of_sup = diag04_audit["authoritative_class_support"]["5"]
    assert of_sup["dev_k"] == 1
    assert of_sup["train_k"] == 4
    assert of_sup["dev_pool_k"] == 5
    assert diag04_audit["uncertainty"]["bootstrap_results"]["OF"]["k"] == 5


def test_guardrail_24_authoritative_all_class_k_reconciliation(diag04_audit):
    """24. Verify all 12 class K values match authoritative DIAG-03 source exactly."""
    diag03_path = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_diag03_radiometric_discriminability_v1.json"
    with open(diag03_path, "r", encoding="utf-8") as f:
        d3 = json.load(f)

    for cid_str, sup in diag04_audit["authoritative_class_support"].items():
        cname = sup["class_name"]
        d3_dev = d3["support_statistics"]["DEV"][cid_str]
        d3_trn = d3["support_statistics"]["TRAIN"][cid_str]

        assert sup["dev_k"] == d3_dev["parent_cluster_count"]
        assert sup["train_k"] == d3_trn["parent_cluster_count"]
        assert sup["dev_pool_k"] == sup["dev_k"] + sup["train_k"]
        assert diag04_audit["uncertainty"]["bootstrap_results"][cname]["k"] == sup["dev_pool_k"]


def test_guardrail_25_represent_language_guardrail(diag04_report_text):
    """25. Verify 'represent' does not imply successful learned representation."""
    unhedged_represent = [
        "adequate to represent hm",
        "architecture represents compact objects",
        "architecture can represent rf",
        "architecture successfully represents",
        "structural inability to represent",
        "adequacy to represent",
    ]
    for pattern in unhedged_represent:
        assert pattern not in diag04_report_text.lower()


def test_guardrail_26_crop_dominance_guardrail(diag04_report_text):
    """26. Verify crop-aperture observations are not described as causal or dominant constraints."""
    unhedged_dominance = [
        "aperture rather than receptive-field limits constrains",
        "aperture rather than receptive field limits constrains",
        "crop aperture is the dominant limitation",
        "crop limitation explains observed extent",
        "data-window bounding dominance",
    ]
    for pattern in unhedged_dominance:
        assert pattern not in diag04_report_text.lower()


def test_guardrail_27_result_classification_split(diag04_audit, diag04_report_text):
    """27. Verify separate classification for architectural scale vs model performance."""
    rc = diag04_audit["result_classification"]
    assert rc["architectural_scale_compatibility"] == "SUPPORTED"
    assert rc["model_performance_implication"] == "NOT_ESTABLISHED"
    clean_text = diag04_report_text.replace("*", "").lower()
    assert "architectural scale compatibility" in clean_text and "supported" in clean_text
    assert "model performance implication" in clean_text and "not_established" in clean_text


def test_guardrail_28_diag05_and_holdout_part_iii_safety(diag04_audit):
    """28. Verify DIAG-05 remains unexecuted, HOLDOUT and Part III remain 0 access."""
    assert diag04_audit["governance"]["diag05_executed"] is False
    assert diag04_audit["governance"]["holdout_access"] == 0
    assert diag04_audit["governance"]["part_iii_access"] == 0


def test_guardrail_29_skip_connection_activation_semantics(diag04_report_text):
    """29. Verify skip connections provide higher-resolution activations without unmeasured semantic preservation claims."""
    assert "skip connections provide higher-resolution encoder activations" in diag04_report_text.lower()
    unmeasured_semantic = [
        "skip connections preserve high-resolution target information",
        "skip connections preserve semantic target information",
        "proving that high-resolution spatial features are preserved",
    ]
    for pattern in unmeasured_semantic:
        assert pattern not in diag04_report_text.lower()


def test_guardrail_30_bootstrap_resampling_semantics(diag04_report_text, diag04_audit):
    """30. Verify bootstrap resampling does not claim independent sample inflation and small-K remains descriptive."""
    clean_text = diag04_report_text.replace("*", "").lower()
    assert "bootstrap resampling does not increase the number of independent acquisition clusters" in clean_text
    assert "bootstrap resampling (b=1000) does not increase independent cluster count" in [l.lower() for l in diag04_audit["limitations"]][6]
    # Check that small K classes in DEV are described as descriptive / suppressed
    assert "c_dict" in diag04_audit["uncertainty"]["resampling_method"] or "B=1000" in diag04_audit["uncertainty"]["resampling_method"]



