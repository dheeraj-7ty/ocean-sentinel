"""Phase 7A.2 Pre-Acquisition Data Governance Reconciliation.

Reconstructs exact candidate sets (SET A through SET G), distinguishes region-level
from parent-scene level counts, updates semantic classifications to
PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY, and generates reconciled audit artifacts.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import rasterio
from shapely.geometry import box, Polygon

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = REPO_ROOT / "data" / "metadata"
YANG_DIR = METADATA_DIR / "yang_singha_2025"
TRUJILLO_DIR = METADATA_DIR / "trujillo_2024"
PART_III_INV = REPO_ROOT / "scratch" / "trujillo_part_iii_image_inventory.json"
PART_I_MANIFEST = TRUJILLO_DIR / "spatial_split_manifest.json"
DARTIS_TAB = YANG_DIR / "data_matrix.tab"


def reconcile_candidates():
    print("=" * 70)
    print("PHASE 7A.2 CANDIDATE SET RECONCILIATION & GOVERNANCE AUDIT")
    print("=" * 70)

    # 1. Load Part III Inventory
    print("[1/5] Loading Trujillo Part III benchmark inventory...")
    with open(PART_III_INV, "r", encoding="utf-8") as f:
        part_iii_raw = json.load(f)

    part_iii_geoms = []
    for item in part_iii_raw:
        b = item["bounds"]
        part_iii_geoms.append({
            "relative_path": item["relative_path"],
            "polygon": box(b[0], b[1], b[2], b[3]),
        })
    print(f"  Part III benchmark scenes: {len(part_iii_geoms)}")

    # 2. Load Part I Manifest
    print("[2/5] Loading Trujillo Part I development dataset...")
    with open(PART_I_MANIFEST, "r", encoding="utf-8") as f:
        part_i_raw = json.load(f)

    part_i_patches = []
    for p in part_i_raw["patches"]:
        with rasterio.open(p["image_path"]) as src:
            b = src.bounds
            part_i_patches.append({
                "patch_stem": p["patch_stem"],
                "split": p["split"],
                "polygon": box(b.left, b.bottom, b.right, b.top),
            })
    print(f"  Part I parent scenes: {len(part_i_patches)}")

    # 3. Parse DARTIS data_matrix.tab
    print("[3/5] Parsing DARTIS catalog...")
    cols = [
        "subset", "jpg_file", "xml_file", "tag", "patch_name", "start_time", "end_time", "Sentinel_ID",
        "patch_width", "patch_height", "patch_ul_lon", "patch_ul_lat", "patch_ur_lon", "patch_ur_lat",
        "patch_br_lon", "patch_br_lat", "patch_bl_lon", "patch_bl_lat", "obj_ul_lon", "obj_ul_lat",
        "obj_ur_lon", "obj_ur_lat", "obj_br_lon", "obj_br_lat", "obj_bl_lon", "obj_bl_lat",
        "obj_patchloc_xmin", "obj_patchloc_ymin", "obj_patchloc_xmax", "obj_patchloc_ymax", "label_size"
    ]

    all_rows = []
    with open(DARTIS_TAB, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip() == "*/":
                break
        next(f)  # header
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= len(cols):
                all_rows.append(dict(zip(cols, parts[:len(cols)])))
            else:
                all_rows.append(dict(zip(cols, parts)))

    # SET A: All raw candidate regions (no-oil subsets: nw, nc)
    set_a = [r for r in all_rows if r.get("subset") in ("nw", "nc")]
    products_a = set(r["Sentinel_ID"] for r in set_a)
    print(f"  SET A (All raw candidates): {len(set_a)} regions across {len(products_a)} parent products")

    # Build polygons
    for r in set_a:
        ul = (float(r["patch_ul_lon"]), float(r["patch_ul_lat"]))
        ur = (float(r["patch_ur_lon"]), float(r["patch_ur_lat"]))
        br = (float(r["patch_br_lon"]), float(r["patch_br_lat"]))
        bl = (float(r["patch_bl_lon"]), float(r["patch_bl_lat"]))
        r["poly"] = Polygon([ul, ur, br, bl])

    # SET B: Part-III directly overlapping regions
    print("[4/5] Auditing Part III & Part I intersections...")
    set_b = []
    set_b_products = set()
    for r in set_a:
        if any(r["poly"].intersects(p3["polygon"]) for p3 in part_iii_geoms):
            set_b.append(r)
            set_b_products.add(r["Sentinel_ID"])

    # SET C: All regions from contaminated Part-III parent products
    set_c = [r for r in set_a if r["Sentinel_ID"] in set_b_products]
    set_c_products = set(r["Sentinel_ID"] for r in set_c)

    # SET D: Part-III cleared candidate regions
    set_d = [r for r in set_a if r["Sentinel_ID"] not in set_b_products]
    set_d_products = set(r["Sentinel_ID"] for r in set_d)

    # Part I direct overlaps on SET D
    part_i_direct_regions = []
    part_i_overlapping_products_in_d = set()
    for r in set_d:
        if any(r["poly"].intersects(p1["polygon"]) for p1 in part_i_patches):
            part_i_direct_regions.append(r)
            part_i_overlapping_products_in_d.add(r["Sentinel_ID"])

    # SET E: Part-I overlapping candidate regions in SET D (parent-scene expanded)
    set_e = [r for r in set_d if r["Sentinel_ID"] in part_i_overlapping_products_in_d]
    set_e_products = set(r["Sentinel_ID"] for r in set_e)

    # SET F: Part-I disjoint candidate regions in SET D (parent-scene level)
    set_f = [r for r in set_d if r["Sentinel_ID"] not in part_i_overlapping_products_in_d]
    set_f_products = set(r["Sentinel_ID"] for r in set_f)

    # SET G: Final accepted/provisional proxy candidates (equivalent to SET F before physical validation)
    set_g = set_f
    set_g_products = set_f_products

    # Mathematical assertions
    assert len(set_a) == 2290
    assert len(products_a) == 869
    assert len(set_b) == 355
    assert len(set_b_products) == 195
    assert len(set_c) == 680
    assert len(set_c_products) == 195
    assert len(set_d) == 1610
    assert len(set_d_products) == 674
    assert len(part_i_direct_regions) == 543
    assert len(part_i_overlapping_products_in_d) == 331
    assert len(set_e) == 1063
    assert len(set_e_products) == 331
    assert len(set_f) == 547
    assert len(set_f_products) == 343
    assert len(set_g) == 547
    assert len(set_g_products) == 343

    # Partition checks
    assert len(set_c) + len(set_d) == len(set_a)
    assert len(set_c_products) + len(set_d_products) == len(products_a)
    assert len(set_e) + len(set_f) == len(set_d)
    assert len(set_e_products) + len(set_f_products) == len(set_d_products)
    assert len(part_i_direct_regions) + 520 == len(set_e)  # 543 direct + 520 co-scene indirect

    print("\n--- EXACT SET RECONCILIATION ---")
    print(f"SET A (All raw candidates):            {len(set_a):>5} regions | {len(products_a):>4} parent products")
    print(f"SET B (Part III direct overlap):       {len(set_b):>5} regions | {len(set_b_products):>4} parent products")
    print(f"SET C (Part III scene-contaminated):   {len(set_c):>5} regions | {len(set_c_products):>4} parent products")
    print(f"SET D (Part III cleared):              {len(set_d):>5} regions | {len(set_d_products):>4} parent products")
    print(f"SET E_direct (Part I direct overlap):  {len(part_i_direct_regions):>5} regions | {len(part_i_overlapping_products_in_d):>4} parent products")
    print(f"SET E_scene (Part I scene-expanded):   {len(set_e):>5} regions | {len(set_e_products):>4} parent products")
    print(f"SET F (Part I & III fully disjoint):   {len(set_f):>5} regions | {len(set_f_products):>4} parent products")
    print(f"SET G (Provisional proxy candidates):  {len(set_g):>5} regions | {len(set_g_products):>4} parent products")

    print("\n--- ARITHMETIC RECONCILIATION SUMMARY ---")
    print("1. Part III Partition: 2,290 = 680 (SET C) + 1,610 (SET D)")
    print("2. Parent Product Partition: 869 = 195 (SET C) + 674 (SET D)")
    print("3. Part I Scene-Level Partition: 1,610 = 1,063 (SET E) + 547 (SET F)")
    print("4. Part I Parent Product Partition: 674 = 331 (SET E) + 343 (SET F)")
    print("5. Part I Region Decomposition: 1,063 = 543 (direct) + 520 (co-scene indirect)")
    print("6. Apparent Discrepancy Resolution:")
    print("   1,610 - 543 = 1,067 reflects direct region subtraction.")
    print("   1,610 - 1,063 = 547 reflects mandatory scene-level parent product subtraction.")
    print("   Therefore, 547 is the exact count of candidates from fully disjoint parent products.")

    # 4. Generate Reconciled Metadata Artifacts
    print("\n[5/5] Generating reconciled durable metadata artifacts...")
    ts_now = datetime.now(timezone.utc).isoformat()

    # (A) Candidate Set Reconciliation Record
    reconciliation_record = {
        "document_id": "PHASE_7A.2_PRE_ACQUISITION_DATA_GOVERNANCE_CORRECTION_20260912",
        "timestamp_utc": ts_now,
        "sets": {
            "SET_A_raw_candidates": {"regions": len(set_a), "parent_products": len(products_a), "relation": "All DARTIS nw and nc records"},
            "SET_B_part_iii_direct_overlap": {"regions": len(set_b), "parent_products": len(set_b_products), "relation": "Regions directly intersecting Part III bounding boxes"},
            "SET_C_part_iii_scene_contaminated": {"regions": len(set_c), "parent_products": len(set_c_products), "relation": "All regions belonging to parent products in SET B"},
            "SET_D_part_iii_cleared": {"regions": len(set_d), "parent_products": len(set_d_products), "relation": "SET_A \\ SET_C (100% free of Part III parent scenes)"},
            "SET_E_part_i_direct_overlap": {"regions": len(part_i_direct_regions), "parent_products": len(part_i_overlapping_products_in_d), "relation": "Regions in SET D directly intersecting Part I footprints"},
            "SET_E_part_i_scene_expanded": {"regions": len(set_e), "parent_products": len(set_e_products), "relation": "All regions in SET D belonging to parent products with direct Part I overlap"},
            "SET_F_fully_disjoint": {"regions": len(set_f), "parent_products": len(set_f_products), "relation": "SET_D \\ SET_E_scene (100% disjoint from Part III and Part I at scene level)"},
            "SET_G_provisional_proxies": {"regions": len(set_g), "parent_products": len(set_g_products), "relation": "Identical to SET_F; provisionally eligible pending physical acquisition"}
        },
        "exact_arithmetic_formulas": {
            "part_iii_region_partition": "2290 == 680 + 1610",
            "part_iii_product_partition": "869 == 195 + 674",
            "part_i_region_partition": "1610 == 1063 + 547",
            "part_i_product_partition": "674 == 331 + 343",
            "part_i_overlapping_region_decomposition": "1063 == 543 (direct) + 520 (co-scene indirect)",
            "arithmetic_inconsistency_resolution": "The apparent conflict (1610 - 543 = 1067 vs 547 + 1063 = 1610) is resolved by recognizing that 543 is the direct region overlap count whereas 1063 is the scene-level expanded overlap count (543 direct + 520 co-scene). Since data governance requires scene-level exclusion, all 1063 regions are assigned DEVELOPMENT_ONLY, leaving exactly 547 regions from 343 parent products fully disjoint."
        }
    }
    with open(METADATA_DIR / "candidate_set_reconciliation.json", "w", encoding="utf-8") as f:
        json.dump(reconciliation_record, f, indent=2)
    print("  Saved candidate_set_reconciliation.json")

    # (B) Update Part III Exclusion Audit
    part_iii_audit = {
        "audit_version": "1.1.0",
        "timestamp_utc": ts_now,
        "firewall_rule": "Rule 38 / Section 4: Part III Exclusion Firewall",
        "benchmark_scenes_evaluated": 450,
        "candidate_regions_evaluated": 2290,
        "unique_parent_products_evaluated": 869,
        "direct_overlapping_regions_count": 355,
        "contaminated_parent_products_count": 195,
        "scene_level_excluded_regions_count": 680,
        "indirect_scene_level_excluded_regions_count": 325,
        "cleared_candidate_regions_count": 1610,
        "cleared_parent_products_count": 674,
        "decision": "EXCLUDE_ALL_SCENE_LEVEL_CONTAMINATED_PRODUCTS",
        "reconciliation_math": {
            "regions_partition": "2290 = 680 (scene-level rejected) + 1610 (cleared)",
            "rejected_decomposition": "680 = 355 (direct overlap) + 325 (co-scene indirect overlap)",
            "parent_products_partition": "869 = 195 (contaminated) + 674 (cleared)"
        }
    }
    with open(METADATA_DIR / "part_iii_exclusion_audit.json", "w", encoding="utf-8") as f:
        json.dump(part_iii_audit, f, indent=2)
    print("  Updated part_iii_exclusion_audit.json")

    # (C) Update Part I Leakage Audit
    part_i_audit = {
        "audit_version": "1.1.0",
        "timestamp_utc": ts_now,
        "firewall_rule": "Section 5: Part I Leakage Firewall",
        "part_i_scenes_evaluated": 1200,
        "candidates_cleared_of_part_iii_regions": 1610,
        "candidates_cleared_of_part_iii_parent_products": 674,
        "direct_part_i_overlapping_regions": 543,
        "direct_part_i_overlapping_parent_products": 331,
        "scene_level_expanded_part_i_overlapping_regions": 1063,
        "indirect_co_scene_part_i_overlapping_regions": 520,
        "disjoint_candidate_regions_count": 547,
        "disjoint_parent_products_count": 343,
        "reconciliation_math": {
            "cleared_regions_partition": "1610 = 1063 (parent-scene overlapping) + 547 (parent-scene disjoint)",
            "overlapping_regions_decomposition": "1063 = 543 (direct footprint overlap) + 520 (co-scene indirect overlap)",
            "parent_products_partition": "674 = 331 (parent-scene overlapping) + 343 (parent-scene disjoint)",
            "resolution_of_apparent_discrepancy": "Subtracting direct regions (1610 - 543 = 1067) neglects 520 co-scene regions sharing parent products with direct overlaps. Scene-level exclusion groups all 1063 regions into DEVELOPMENT_ONLY, yielding exactly 547 candidate regions across 343 parent products with zero Part I footprint overlap."
        }
    }
    with open(METADATA_DIR / "part_i_leakage_audit.json", "w", encoding="utf-8") as f:
        json.dump(part_i_audit, f, indent=2)
    print("  Updated part_i_leakage_audit.json")

    # (D) Update Lookalike Proxy Provenance Manifest
    provenance_candidates = []
    for r in set_a:
        sid = r["Sentinel_ID"]
        tag = r["tag"]
        source_label = r["subset"]
        
        if source_label == "nw":
            src_desc = "DARTIS catalog subset 'nw': No-oil open-water dark feature candidate"
            our_interp = "Candidate non-slick ocean feature (e.g. biogenic surfactant, low-wind surface, internal wave, or clean water); requires physical imagery validation"
        elif source_label == "nc":
            src_desc = "DARTIS catalog subset 'nc': No-oil coastal-water dark feature candidate"
            our_interp = "Candidate coastal dark feature (e.g. coastal shadow, shallow bathymetry, terrestrial runoff, or coastal surfactant); requires physical imagery validation"
        else:
            src_desc = f"Unknown subset '{source_label}'"
            our_interp = "Uncharacterized"

        if sid in set_b_products:
            training_role = "REJECTED"
            proxy_confidence = "NONE"
            exclusion_reason = "Part III Contamination Firewall (scene-level intersection with external test benchmark)"
            physical_status = "REJECTED_UNACQUIRED"
        elif sid in part_i_overlapping_products_in_d:
            training_role = "DEVELOPMENT_ONLY"
            proxy_confidence = "PROBABLE"
            exclusion_reason = "Part I Spatial Overlap (quarantined from holdout; restricted to development co-clustering)"
            physical_status = "RESERVED_UNACQUIRED"
        else:
            # Fully disjoint - PROVISIONALLY ELIGIBLE
            training_role = "PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY"
            proxy_confidence = "PROVISIONAL_PENDING_PHYSICAL_VALIDATION"
            exclusion_reason = "NONE (Clean non-Part-III, non-Part-I proxy candidate; metadata/provenance tests pass)"
            physical_status = "PENDING_ACQUISITION"

        provenance_candidates.append({
            "candidate_tag": tag,
            "source_product_id": sid,
            "source_label": source_label,
            "source_description": src_desc,
            "source_confidence": "HIGH_CATALOG_METADATA",
            "our_interpretation": our_interp,
            "training_role": training_role,
            "proxy_confidence": proxy_confidence,
            "physical_validation_status": physical_status,
            "exclusion_reason": exclusion_reason,
            "acquisition_start_utc": r.get("start_time"),
            "patch_dimensions_pixels": [int(r.get("patch_width", 640)), int(r.get("patch_height", 640))],
            "geographic_corners_wgs84": {
                "upper_left": [float(r["patch_ul_lon"]), float(r["patch_ul_lat"])],
                "upper_right": [float(r["patch_ur_lon"]), float(r["patch_ur_lat"])],
                "bottom_right": [float(r["patch_br_lon"]), float(r["patch_br_lat"])],
                "bottom_left": [float(r["patch_bl_lon"]), float(r["patch_bl_lat"])],
            }
        })

    role_counts = Counter(c["training_role"] for c in provenance_candidates)
    provenance_manifest = {
        "manifest_version": "2.0.0",
        "generated_timestamp_utc": ts_now,
        "data_governance_status": "PRE_ACQUISITION_RECONCILED",
        "physical_imagery_status": "PENDING_ACQUISITION",
        "total_candidate_regions": len(provenance_candidates),
        "unique_parent_products": len(products_a),
        "training_role_summary": dict(role_counts),
        "semantic_firewall_definitions": {
            "PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY": "Metadata/provenance/geospatial tests indicate eligibility for subsequent physical proxy validation; semantic suitability as a negative training example has not yet been confirmed.",
            "DEVELOPMENT_ONLY": "Candidate region overlaps Part-I development corpus footprints; quarantined from holdout and restricted to internal exploratory co-clustering.",
            "REJECTED": "Candidate region originates from a parent product contaminated by Trujillo Part III external benchmark scenes; permanently excluded under Rule 38."
        },
        "candidates": provenance_candidates
    }
    with open(METADATA_DIR / "lookalike_proxy_provenance_manifest.json", "w", encoding="utf-8") as f:
        json.dump(provenance_manifest, f, indent=2)
    print("  Updated lookalike_proxy_provenance_manifest.json (v2.0.0)")

    print("\n" + "=" * 70)
    print("PHASE 7A.2 RECONCILIATION COMPLETE — 100% INVARIANTS PASS")
    print("=" * 70)


if __name__ == "__main__":
    reconcile_candidates()
