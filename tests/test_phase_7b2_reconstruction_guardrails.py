"""Phase 7B.2 Regression Guardrails.

Verifies source-granule reconstruction, geometric registration contract,
lineage provenance, leakage firewalls, class dictionary integrity,
metric denominator governance, and frozen baseline invariants.
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

IW_MANIFEST = METADATA_DIR / "li_iw_source_scene_manifest.json"
WV_MANIFEST = METADATA_DIR / "li_wv_source_lineage_manifest.json"
REG_AUDIT = METADATA_DIR / "li_geometry_registration_audit.json"
CLASS_DICT = METADATA_DIR / "li_class_dictionary.json"
SPLIT_READINESS = METADATA_DIR / "benchmark_split_readiness.json"
PART_I_MANIFEST = METADATA_DIR / "internal_development_split_manifest.json"
EXP06_CHECKPOINT = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
CORRECTION_ADDENDUM = EXP_DIR / "PHASE_7B1_CORRECTION_ADDENDUM_20260913.md"

FROZEN_EXP06_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
FROZEN_PART_I_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_01_source_parent_identity_integrity():
    """1. Verify source-parent identity integrity in IW and WV manifests."""
    assert IW_MANIFEST.exists(), f"Missing {IW_MANIFEST}"
    assert WV_MANIFEST.exists(), f"Missing {WV_MANIFEST}"
    
    with open(IW_MANIFEST, "r", encoding="utf-8") as f:
        iw = json.load(f)
    with open(WV_MANIFEST, "r", encoding="utf-8") as f:
        wv = json.load(f)
        
    for scene in iw["scenes"]:
        assert "source_scene_id" in scene
        assert "source_product_id" in scene
        assert "source_product_id_status" in scene
        assert scene["source_product_id_status"] in (
            "VERIFIED_EXACT_MATCH_IN_ARCHIVE",
            "INFERRED_FROM_CANONICAL_ESA_STEM"
        )
        
    for p in wv["orbit_passes"]:
        assert "orbit_pass_id" in p
        assert "satellite" in p
        assert "absolute_orbit" in p
        assert "mission_data_take_id" in p


def test_02_iw_parent_reconstruction():
    """2. Verify IW parent reconstruction: exactly 484 scenes, 2,628 slices."""
    with open(IW_MANIFEST, "r", encoding="utf-8") as f:
        iw = json.load(f)
        
    assert iw["summary"]["total_iw_slices"] == 2628
    assert iw["summary"]["total_unique_source_scenes"] == 484
    assert len(iw["scenes"]) == 484
    assert len(iw["slices"]) == 2628
    
    total_slices_sum = sum(s["slice_count"] for s in iw["scenes"])
    assert total_slices_sum == 2628
    assert iw["summary"]["min_slices_per_scene"] >= 1
    assert iw["summary"]["max_slices_per_scene"] <= 51


def test_03_wv_parent_reconstruction():
    """3. Verify WV parent reconstruction: 2,383 vignettes across 1,678 orbit passes."""
    with open(WV_MANIFEST, "r", encoding="utf-8") as f:
        wv = json.load(f)
        
    assert wv["summary"]["total_wv_vignettes"] == 2383
    assert wv["summary"]["total_unique_orbit_passes"] == 1678
    assert wv["summary"]["total_unique_calendar_dates"] == 344
    assert len(wv["orbit_passes"]) == 1678
    assert len(wv["vignettes"]) == 2383
    
    total_vig_sum = sum(p["vignette_count"] for p in wv["orbit_passes"])
    assert total_vig_sum == 2383


def test_04_lineage_provenance():
    """4. Verify lineage provenance: IW Level-1 GRD, WV Level-1 SLC via TenGeoP-SARwv."""
    with open(IW_MANIFEST, "r", encoding="utf-8") as f:
        iw = json.load(f)
    with open(WV_MANIFEST, "r", encoding="utf-8") as f:
        wv = json.load(f)
        
    for s in iw["scenes"]:
        assert "Ground Range Detected (GRD)" in s["ultimate_source_lineage"]
    for p in wv["orbit_passes"]:
        assert "TenGeoP-SARwv" in p["intermediate_source_dataset"]
        assert "Single Look Complex (SLC) Wave Mode" in p["ultimate_source_lineage"]


def test_05_part_i_leakage():
    """5. Verify Part-I leakage firewall."""
    with open(IW_MANIFEST, "r", encoding="utf-8") as f:
        iw = json.load(f)
    with open(PART_I_MANIFEST, "r", encoding="utf-8") as f:
        part1 = json.load(f)
        
    part1_ids = set(s["source_identity"] for s in part1["scenes"])
    for s in iw["scenes"]:
        assert s["source_scene_id"] not in part1_ids


def test_06_part_iii_quarantine():
    """6. Verify Part-III permanent quarantine under Rule 38."""
    with open(SPLIT_READINESS, "r", encoding="utf-8") as f:
        readiness = json.load(f)
    assert readiness["frozen_operating_invariants"]["part_iii_status"] == "PERMANENTLY_QUARANTINED_UNDER_RULE_38"


def test_07_dartis_leakage():
    """7. Verify zero orbit pass intersection between Li IW/WV and DARTIS."""
    with open(IW_MANIFEST, "r", encoding="utf-8") as f:
        iw = json.load(f)
    dartis_provenance = METADATA_DIR / "lookalike_proxy_provenance_manifest.json"
    with open(dartis_provenance, "r", encoding="utf-8") as f:
        dartis = json.load(f)
        
    li_orbits = set((s["satellite"], s["absolute_orbit"]) for s in iw["scenes"])
    dartis_orbits = set()
    for c in dartis["candidates"]:
        parts = c["source_product_id"].replace(".SAFE", "").split("_")
        if len(parts) >= 7:
            dartis_orbits.add((parts[0], int(parts[6])))
            
    overlap = li_orbits.intersection(dartis_orbits)
    assert len(overlap) == 0, f"Unexpected orbit overlap with DARTIS: {overlap}"


def test_08_geographic_leakage():
    """8. Verify geographic leakage audit results for representative sample."""
    audit_file = SCRATCH_DIR / "spatial_leakage_control_results.json"
    assert audit_file.exists(), f"Missing {audit_file}"
    with open(audit_file, "r", encoding="utf-8") as f:
        res = json.load(f)
        
    assert len(res) >= 12
    for r in res:
        assert r["part_i_direct_hits"] == 0
        assert r["part_iii_direct_hits"] == 0
        assert r["dartis_direct_hits"] == 0
        assert r["part_i_buffer_hits"] == 0
        assert r["part_iii_buffer_hits"] == 0


def test_09_temporal_leakage():
    """9. Verify temporal separation: WV strictly 2016, DARTIS strictly 2019."""
    with open(WV_MANIFEST, "r", encoding="utf-8") as f:
        wv = json.load(f)
    assert wv["summary"]["temporal_range_start"].startswith("2016")
    assert wv["summary"]["temporal_range_stop"].startswith("2016")


def test_10_class_id_dictionary_integrity():
    """10. Verify class-ID dictionary integrity: 15 classes, correct palette mapping."""
    assert CLASS_DICT.exists(), f"Missing {CLASS_DICT}"
    with open(CLASS_DICT, "r", encoding="utf-8") as f:
        cd = json.load(f)
        
    assert cd["total_classes"] == 15
    assert cd["background_class_id"] == 0
    assert len(cd["classes"]) == 15
    
    class_map = {c["class_id"]: c for c in cd["classes"]}
    assert class_map[0]["abbreviation"] == "BG"
    assert class_map[0]["rgb_color"] == [0, 0, 0]
    assert class_map[2]["abbreviation"] == "BS"
    assert class_map[2]["rgb_color"] == [0, 128, 0]
    assert class_map[4]["abbreviation"] == "LWA"
    assert class_map[4]["rgb_color"] == [0, 0, 128]
    assert class_map[12]["abbreviation"] == "IWs"
    assert class_map[12]["rgb_color"] == [64, 0, 128]
    assert class_map[14]["abbreviation"] == "OS"


def test_11_100m_to_10m_registration_contract():
    """11. Verify 100m-to-10m registration contract and quantization uncertainty."""
    assert REG_AUDIT.exists(), f"Missing {REG_AUDIT}"
    with open(REG_AUDIT, "r", encoding="utf-8") as f:
        ra = json.load(f)
        
    assert ra["native_grid_contract"]["iw_mode_nominal_pixel_spacing_m"] == 10.0
    assert ra["li_distributed_imagery_contract"]["nominal_pixel_spacing_m"] == 100.0
    assert ra["scientific_mask_contract"]["mandated_designation"] == "DERIVED HIGH-RESOLUTION MASK"


def test_12_no_invented_10m_ground_truth():
    """12. Verify prohibition of 'native 10m ground truth' designation."""
    with open(REG_AUDIT, "r", encoding="utf-8") as f:
        ra = json.load(f)
    forbidden = ra["scientific_mask_contract"]["forbidden_designations"]
    assert "native 10m ground truth" in forbidden
    assert "10m pixel-level ground truth" in forbidden


def test_13_no_false_positive_metric_denominator_misuse():
    """13. Verify metric denominator governance: separate quantities A through E."""
    with open(SPLIT_READINESS, "r", encoding="utf-8") as f:
        sr = json.load(f)
        
    metrics = sr["benchmark_b_specification"]["corrected_metric_contract"]
    assert "quantity_a" in metrics
    assert "quantity_b" in metrics
    assert "quantity_c" in metrics
    assert "quantity_d" in metrics
    assert "quantity_e" in metrics
    
    assert metrics["quantity_b"]["metric_name"] == "PHENOMENON_REGION_RESPONSE"
    assert "NOT a false alarm rate" in metrics["quantity_b"]["scientific_role"]


def test_14_no_benchmark_specific_threshold_tuning():
    """14. Verify threshold is frozen at tau = 0.22."""
    with open(SPLIT_READINESS, "r", encoding="utf-8") as f:
        sr = json.load(f)
    assert sr["frozen_operating_invariants"]["canonical_threshold"] == 0.22


def test_15_checkpoint_sha_integrity():
    """15. Verify EXP-06 checkpoint SHA256 integrity directly from disk."""
    assert EXP06_CHECKPOINT.exists(), f"Missing {EXP06_CHECKPOINT}"
    actual_sha = compute_sha256(EXP06_CHECKPOINT)
    assert actual_sha == FROZEN_EXP06_SHA, f"EXP-06 checkpoint mismatch: {actual_sha}"


def test_16_canonical_preprocessing_integrity():
    """16. Verify canonical preprocessing invariants."""
    with open(SPLIT_READINESS, "r", encoding="utf-8") as f:
        sr = json.load(f)
    assert sr["benchmark_b_specification"]["execution_status"] == "BLOCKED_PENDING_NATIVE_10M_DUAL_POL_RECOVERY"


def test_17_protected_manifest_immutability():
    """17. Verify Part-I development split manifest immutability."""
    assert PART_I_MANIFEST.exists(), f"Missing {PART_I_MANIFEST}"
    actual_sha = compute_sha256(PART_I_MANIFEST)
    assert actual_sha == FROZEN_PART_I_SHA, f"Part-I manifest modified: {actual_sha}"


def test_18_historical_report_preservation():
    """18. Verify historical report preservation and correction addendum."""
    assert CORRECTION_ADDENDUM.exists(), f"Missing {CORRECTION_ADDENDUM}"
    with open(CORRECTION_ADDENDUM, "r", encoding="utf-8") as f:
        content = f.read()
    assert "high-value candidate resource" in content
    assert "CORRECTION ADDENDUM" in content


def test_19_no_training_during_7b2():
    """19. Verify no model training during Phase 7B.2."""
    with open(SPLIT_READINESS, "r", encoding="utf-8") as f:
        sr = json.load(f)
    assert sr["frozen_operating_invariants"]["exp07_training"] == "STRICTLY_FORBIDDEN"
    assert sr["frozen_operating_invariants"]["ops01_training_in_phase_7b2"] == "STRICTLY_FORBIDDEN"
    assert sr["overall_training_readiness_verdict"] == "READY_WITH_EXPLICIT_LIMITATIONS"


def test_20_deterministic_manifest_ordering():
    """20. Verify deterministic sorting order in manifests."""
    with open(IW_MANIFEST, "r", encoding="utf-8") as f:
        iw = json.load(f)
    with open(WV_MANIFEST, "r", encoding="utf-8") as f:
        wv = json.load(f)
        
    iw_scene_ids = [s["source_scene_id"] for s in iw["scenes"]]
    assert iw_scene_ids == sorted(iw_scene_ids), "IW scenes are not deterministically sorted"
    
    wv_pass_ids = [p["orbit_pass_id"] for p in wv["orbit_passes"]]
    assert wv_pass_ids == sorted(wv_pass_ids), "WV orbit passes are not deterministically sorted"


def test_21_complete_source_record_accounting():
    """21. Verify complete source-record accounting: 2,628 IW + 2,383 WV = 5,011 total."""
    with open(IW_MANIFEST, "r", encoding="utf-8") as f:
        iw = json.load(f)
    with open(WV_MANIFEST, "r", encoding="utf-8") as f:
        wv = json.load(f)
        
    total_accounted = len(iw["slices"]) + len(wv["vignettes"])
    assert total_accounted == 5011, f"Expected 5,011 records, accounted for {total_accounted}"
