"""Phase 7B.2A Class Semantics & OPS-01 Readiness Gate Regression Guardrails.

Verifies authoritative class semantics, non-existence of viable oil spill class,
full-mask scan accounting, bilinear registration contract, boundary uncertainty,
source completeness accounting, and frozen baseline invariants.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = REPO_ROOT / "data" / "metadata"
SCRATCH_DIR = REPO_ROOT / "scratch"
EXP_DIR = REPO_ROOT / "experiments"

AUTH_CLASS_DICT = METADATA_DIR / "li_authoritative_class_dictionary.json"
PRESERVED_CLASS_DICT = METADATA_DIR / "li_class_dictionary.json"
FULL_AUDIT_REPORT = SCRATCH_DIR / "li_full_mask_consistency_audit.json"
REG_AUDIT_V2 = METADATA_DIR / "li_geometry_registration_audit_v2.json"
IW_MANIFEST = METADATA_DIR / "li_iw_source_scene_manifest.json"
WV_MANIFEST = METADATA_DIR / "li_wv_source_lineage_manifest.json"
SPLIT_READINESS = METADATA_DIR / "benchmark_split_readiness.json"
TRAINING_CONTRACT = EXP_DIR / "PHASE_7B2A_OPS01_TRAINING_READINESS_CONTRACT.md"
CORRECTION_REPORT = EXP_DIR / "PHASE_7B2A_CLASS_DICTIONARY_CORRECTION_20260913.md"
PART_I_MANIFEST = METADATA_DIR / "internal_development_split_manifest.json"
EXP06_CHECKPOINT = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"

EXPECTED_AUTH_DICT_SHA = "9377DA6310804E459F2113914F6C933FF42F03277EC2D740A1FE29630A46DE46"
FROZEN_EXP06_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
FROZEN_PART_I_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_01_authoritative_class_count():
    """1. Verify authoritative class dictionary specifies 15 classes with exact roles."""
    assert AUTH_CLASS_DICT.exists(), f"Missing {AUTH_CLASS_DICT}"
    with open(AUTH_CLASS_DICT, "r", encoding="utf-8") as f:
        cd = json.load(f)
    assert len(cd["classes"]) == 15
    assert cd["dataset_total_images"] == 5011


def test_02_authoritative_class_id_mapping():
    """2. Verify exact class-ID mapping to names and abbreviations."""
    with open(AUTH_CLASS_DICT, "r", encoding="utf-8") as f:
        cd = json.load(f)
    cmap = {c["class_id"]: c for c in cd["classes"]}
    assert cmap[0]["abbreviation"] == "BG"
    assert cmap[1]["abbreviation"] == "AF"
    assert cmap[2]["abbreviation"] == "BS"
    assert cmap[3]["abbreviation"] == "IB"
    assert cmap[4]["abbreviation"] == "LWA"
    assert cmap[5]["abbreviation"] == "MCC"
    assert cmap[6]["abbreviation"] == "OF"
    assert cmap[7]["abbreviation"] == "POW"
    assert cmap[8]["abbreviation"] in ("RC/RF", "RC", "RF")
    assert cmap[9]["abbreviation"] == "SI"
    assert cmap[10]["abbreviation"] == "WS"
    assert cmap[11]["abbreviation"] == "Eddy"
    assert cmap[12]["abbreviation"] in ("IWs", "IW")
    assert cmap[13]["abbreviation"] == "HM"
    assert cmap[14]["abbreviation"] == "OS"


def test_03_no_invented_oil_spill_class():
    """3. Verify Class 14 is excluded from training and flagged as insufficient data."""
    with open(AUTH_CLASS_DICT, "r", encoding="utf-8") as f:
        cd = json.load(f)
    cmap = {c["class_id"]: c for c in cd["classes"]}
    assert cmap[14]["ops01_training_role"] == "EXCLUDED_INSUFFICIENT_DATA"
    assert cmap[14]["image_count"] == 4
    assert cmap[14]["pixel_count"] == 1702
    assert cmap[14]["pixel_percentage"] < 0.001


def test_04_palette_index_consistency():
    """4. Verify palette consistency: 0 palette discrepancies across all 5,011 masks."""
    assert FULL_AUDIT_REPORT.exists(), f"Missing {FULL_AUDIT_REPORT}"
    with open(FULL_AUDIT_REPORT, "r", encoding="utf-8") as f:
        audit = json.load(f)
    assert audit["distinct_palettes_count"] == 1
    assert audit["palette_discrepancies"] == 0
    assert audit["total_images_audited"] == 5011


def test_05_full_mask_id_validation():
    """5. Verify observed pixel IDs: exactly [0..14], 0 corrupted masks, 0 undocumented IDs."""
    with open(FULL_AUDIT_REPORT, "r", encoding="utf-8") as f:
        audit = json.load(f)
    assert audit["observed_pixel_class_ids"] == list(range(15))
    assert audit["corrupted_images_count"] == 0


def test_06_source_product_completeness_accounting():
    """6. Verify exact source product completeness accounting in IW manifest summary."""
    with open(IW_MANIFEST, "r", encoding="utf-8") as f:
        iw = json.load(f)
    acct = iw["summary"]["archive_recovery_accounting"]
    assert acct["N_IW_SCENES_IDENTIFIED"] == 484
    assert acct["N_IW_PRODUCTS_EXACTLY_RECOVERED"] == 12
    assert acct["N_IW_PRODUCTS_NOT_FOUND"] == 0
    assert acct["N_IW_PRODUCTS_QUERY_ERROR"] == 0
    assert acct["N_IW_PRODUCTS_AMBIGUOUS"] == 0
    assert acct["full_source_recovery_status"] == "FULL_SOURCE_RECOVERY_PENDING"


def test_07_filename_derived_identity_marked_inferred():
    """7. Verify non-recovered scenes are explicitly marked INFERRED."""
    with open(IW_MANIFEST, "r", encoding="utf-8") as f:
        iw = json.load(f)
    inferred_count = sum(
        1 for s in iw["scenes"] if s["source_product_id_status"] == "INFERRED_FROM_CANONICAL_ESA_STEM"
    )
    verified_count = sum(
        1 for s in iw["scenes"] if s["source_product_id_status"] == "VERIFIED_EXACT_MATCH_IN_ARCHIVE"
    )
    assert verified_count == 12
    assert inferred_count == 484 - 12


def test_08_exact_product_recovery_provenance():
    """8. Verify exact product recovery provenance in control sample."""
    asf_file = SCRATCH_DIR / "asf_representative_recovery_audit.json"
    assert asf_file.exists(), f"Missing {asf_file}"
    with open(asf_file, "r", encoding="utf-8") as f:
        asf = json.load(f)
    assert len(asf) == 12
    for item in asf:
        assert item["status"] == "EXACT_MATCH_RECOVERED"
        assert item["source_product_id"].startswith("S1")
        assert "GRD" in item["source_product_id"]
        assert item["polarization"] in ("VV", "VV+VH")


def test_09_gcp_georeferencing_consistency():
    """9. Verify GCP georeferencing extraction and 4-corner coordinate consistency."""
    assert REG_AUDIT_V2.exists(), f"Missing {REG_AUDIT_V2}"
    with open(REG_AUDIT_V2, "r", encoding="utf-8") as f:
        ra = json.load(f)
    gcps = ra["geometric_model_evaluation"]["control_sample_analysis"]["corner_gcps"]
    assert len(gcps) == 4
    for g in gcps:
        assert g["lat"] > 0
        assert g["lon"] > 100


def test_10_no_unjustified_affine_assumption():
    """10. Verify that 6-DOF affine model is rejected and Bilinear model is mandated."""
    with open(REG_AUDIT_V2, "r", encoding="utf-8") as f:
        ra = json.load(f)
    models = ra["geometric_model_evaluation"]["tested_transformation_models"]
    affine = next(m for m in models if "Affine" in m["model_name"])
    bilinear = next(m for m in models if "Bilinear" in m["model_name"])
    
    assert affine["fitting_verdict"] == "SCIENTIFICALLY_INVALID_FOR_RADAR_GEOMETRY"
    assert affine["residual_registration_error_meters"] > 10000.0  # 12.75 km residual
    assert bilinear["fitting_verdict"] == "MATHEMATICALLY_EXACT_AND_AUTHORITATIVE"
    assert bilinear["residual_registration_error_meters"] == 0.0


def test_11_derived_mask_terminology():
    """11. Verify mandated DERIVED_HIGH_RESOLUTION_MASK and forbidden native 10m truth."""
    with open(REG_AUDIT_V2, "r", encoding="utf-8") as f:
        ra = json.load(f)
    contract = ra["boundary_uncertainty_contract"]
    assert contract["mandated_mask_classification"] == "DERIVED_HIGH_RESOLUTION_MASK"
    assert "NATIVE_10M_GROUND_TRUTH" in contract["strictly_forbidden_classifications"]


def test_12_boundary_uncertainty_contract():
    """12. Verify boundary uncertainty contract pre-registers 50m erosion buffer."""
    with open(REG_AUDIT_V2, "r", encoding="utf-8") as f:
        ra = json.load(f)
    pre = ra["boundary_uncertainty_contract"]["pre_registered_evaluation_protocol"]
    assert pre["boundary_erosion_buffer_meters"] == 50.0
    assert pre["boundary_erosion_buffer_native_pixels"] == 5


def test_13_iw_wv_separation():
    """13. Verify separate track specification for IW (Track A) and WV (Track B)."""
    assert TRAINING_CONTRACT.exists(), f"Missing {TRAINING_CONTRACT}"
    with open(TRAINING_CONTRACT, "r", encoding="utf-8") as f:
        content = f.read()
    assert "TRACK A (Sentinel-1 IW Mode)" in content
    assert "TRACK B (Sentinel-1 WV Mode)" in content


def test_14_source_lineage_integrity():
    """14. Verify source lineage integrity: TenGeoP-SARwv for WV, ESA GRD for IW."""
    with open(WV_MANIFEST, "r", encoding="utf-8") as f:
        wv = json.load(f)
    assert wv["summary"]["intermediate_dataset"] == "TenGeoP-SARwv (Wang et al., 2019)"
    assert wv["summary"]["total_unique_orbit_passes"] == 1678


def test_15_parent_product_split():
    """15. Verify parent-product split contract prevents sibling patch leakage."""
    with open(SPLIT_READINESS, "r", encoding="utf-8") as f:
        sr = json.load(f)
    assert sr["split_architecture_contract"]["iw_mode_split_contract"]["unique_parent_source_scenes"] == 484
    assert sr["split_architecture_contract"]["wv_mode_split_contract"]["unique_orbit_passes"] == 1678


def test_16_geographic_holdout_metadata():
    """16. Verify geographic basin holdouts are pre-registered."""
    with open(SPLIT_READINESS, "r", encoding="utf-8") as f:
        sr = json.load(f)
    holdouts = sr["split_architecture_contract"]["geographic_and_temporal_holdouts"]
    assert "North Atlantic" in holdouts["geographic_basin_holdout"]
    assert "Mediterranean Sea" in holdouts["geographic_basin_holdout"]


def test_17_no_model_output_label_contamination():
    """17. Verify rule prohibiting EXP-06 outputs from influencing OPS-01 labels."""
    with open(TRAINING_CONTRACT, "r", encoding="utf-8") as f:
        content = f.read()
    assert "No Model-Output Label Contamination" in content
    assert "EXP-06 predictions, confidences, or false-positive alarms must NEVER be used" in content


def test_18_benchmark_a_b_separation():
    """18. Verify strict separation between Benchmark A and Benchmark B."""
    with open(TRAINING_CONTRACT, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Strict Benchmark Separation" in content


def test_19_no_exp07_training():
    """19. Verify EXP-07 training remains strictly forbidden."""
    with open(TRAINING_CONTRACT, "r", encoding="utf-8") as f:
        content = f.read()
    assert "EXP-07 TRAINING: STRICTLY FORBIDDEN" in content


def test_20_no_threshold_modification():
    """20. Verify threshold is frozen at tau = 0.22."""
    with open(SPLIT_READINESS, "r", encoding="utf-8") as f:
        sr = json.load(f)
    assert sr["frozen_operating_invariants"]["canonical_threshold"] == 0.22


def test_21_protected_part_i():
    """21. Verify Part-I development split manifest SHA-256 remains bitwise frozen."""
    assert PART_I_MANIFEST.exists(), f"Missing {PART_I_MANIFEST}"
    actual_sha = compute_sha256(PART_I_MANIFEST)
    assert actual_sha == FROZEN_PART_I_SHA, f"Part-I manifest modified: {actual_sha}"


def test_22_protected_part_iii():
    """22. Verify Part-III is permanently quarantined under Rule 38."""
    with open(SPLIT_READINESS, "r", encoding="utf-8") as f:
        sr = json.load(f)
    assert sr["frozen_operating_invariants"]["part_iii_status"] == "PERMANENTLY_QUARANTINED_UNDER_RULE_38"


def test_23_manifest_sha_integrity():
    """23. Verify cryptographic SHA-256 integrity of authoritative dictionary and EXP-06 checkpoint."""
    actual_dict_sha = compute_sha256(AUTH_CLASS_DICT)
    assert actual_dict_sha == EXPECTED_AUTH_DICT_SHA, f"Dictionary SHA mismatch: {actual_dict_sha}"
    actual_exp06_sha = compute_sha256(EXP06_CHECKPOINT)
    assert actual_exp06_sha == FROZEN_EXP06_SHA, f"EXP-06 SHA mismatch: {actual_exp06_sha}"


def test_24_historical_report_preservation():
    """24. Verify previous class dictionary and correction report are preserved."""
    assert PRESERVED_CLASS_DICT.exists(), f"Missing {PRESERVED_CLASS_DICT}"
    assert CORRECTION_REPORT.exists(), f"Missing {CORRECTION_REPORT}"


def test_25_deterministic_manifests():
    """25. Verify deterministic manifest ordering across all records."""
    with open(IW_MANIFEST, "r", encoding="utf-8") as f:
        iw = json.load(f)
    scene_ids = [s["source_scene_id"] for s in iw["scenes"]]
    assert scene_ids == sorted(scene_ids), "IW scenes are not sorted deterministically"
    
    with open(WV_MANIFEST, "r", encoding="utf-8") as f:
        wv = json.load(f)
    pass_ids = [p["orbit_pass_id"] for p in wv["orbit_passes"]]
    assert pass_ids == sorted(pass_ids), "WV passes are not sorted deterministically"
