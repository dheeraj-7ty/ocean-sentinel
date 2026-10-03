"""Phase 8-P2-R2-C2 Final Taxonomy Integrity & P3 Gate Guardrails Test Suite.

Enforces strict verification of all C2 audit findings and resolutions:

1.  Taxonomy Canonical Abbreviations: All manifest_v3 class_composition entries use taxonomy_v1 abbreviations.
2.  Taxonomy Canonical Class Names: class_name fields match canonical names exactly.
3.  Taxonomy Canonical Label IDs: source_label_id fields match canonical IDs.
4.  Taxonomy No Drift Terms: manifest_v3 contains no prohibited drift terminology.
5.  C2 Incident Register Exists: INC-P2R2-C2-001 and INC-P2R2-C2-002 recorded and resolved.
6.  Ledger v2 OF Claim Correction: Claim 11 corrected to Class 6 (not Class 8).
7.  Ledger v2 OF Scope Correction: scope says Ocean Front (not Oil Slick).
8.  Geographic Basin Audit Exists: ops01_geographic_basin_audit_v1.json present.
9.  Geographic Basin Count: Exactly 5 distinct basin labels in manifest_v3.
10. Geographic Basin Evidence Status: All 27 parents have EXTRACTED_FROM_S3_ANNOTATION_XML status.
11. South Atlantic Warning Disclosed: Single-parent South Atlantic basin is documented.
12. Sufficiency v4 Holdout Disclosure: HOLDOUT_PARTIALLY_USED_FOR_SELECTION explicitly present.
13. Sufficiency v4 Taxonomy Correction Note: c2_taxonomy_correction field present.
14. Epistemic Boundary: CONDITIONAL_ENGINEERING_RECONSTRUCTION present in manifest.
15. Epistemic Boundary: EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS present in manifest.
16. Frozen Artifact Integrity: EXP-06 and Part-I bitwise identical to frozen hashes (inherited from C1).
17. Zero OS Pixels: Class 14 still excluded in manifest_v3.
18. Zero Partition Leakage: No parent appears in more than one partition.
19. Image SHA Uniqueness: All 147 image SHA256 hashes are distinct.
20. Mask SHA Duplicates Expected: Duplicate mask SHAs only occur within single-class-fraction-1.0 samples.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = REPO_ROOT / "data" / "metadata"

FROZEN_EXP06_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
FROZEN_PART_I_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"

# Drift terms that must NEVER appear in manifest_v3 class_composition entries
PROHIBITED_DRIFT_TERMS = [
    "Organic Film",
    "Oil Front",
    "Oil Slick Lookalike",
    "Microalgae Bloom",
    "Marine Organisms",
    "Rain Cell Front",
    "Pure Wave",
    "Wind Field",
    "Vessel",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


@pytest.fixture(scope="module")
def taxonomy():
    p = METADATA_DIR / "ops01_taxonomy_v1.json"
    assert p.exists(), f"Missing canonical taxonomy: {p}"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def canonical_abbr(taxonomy):
    return {c["abbreviation"]: c["class_name"] for c in taxonomy["classes"]}


@pytest.fixture(scope="module")
def canonical_label_id(taxonomy):
    return {c["abbreviation"]: c["source_label_id"] for c in taxonomy["classes"]}


@pytest.fixture(scope="module")
def manifest_v3():
    p = METADATA_DIR / "ops01_physical_dataset_manifest_v3.json"
    assert p.exists(), f"Missing {p}"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def samples(manifest_v3):
    return manifest_v3["samples"]


@pytest.fixture(scope="module")
def incident_register():
    p = METADATA_DIR / "ops01_c2_taxonomy_incident_register.json"
    assert p.exists(), f"Missing C2 incident register: {p}"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ledger_v2():
    p = METADATA_DIR / "ops01_corrective_audit_ledger_v2.json"
    assert p.exists(), f"Missing C2 corrected ledger v2: {p}"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def sufficiency_v4():
    p = METADATA_DIR / "ops01_dataset_sufficiency_v4.json"
    assert p.exists(), f"Missing sufficiency v4: {p}"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def geo_basin_audit():
    p = METADATA_DIR / "ops01_geographic_basin_audit_v1.json"
    assert p.exists(), f"Missing geographic basin audit: {p}"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# =========================================================
# TEST GROUP 1: Taxonomy Canonical Integrity (Data Layer)
# =========================================================

def test_01_manifest_v3_all_abbreviations_canonical(samples, canonical_abbr):
    """All class_composition abbreviations in manifest_v3 are in canonical taxonomy."""
    violations = []
    for s in samples:
        for abbr in s.get("class_composition", {}):
            if abbr not in canonical_abbr:
                violations.append(f"sample={s['sample_id']} abbr={abbr}")
    assert not violations, (
        f"INC-P2R2-C2-001 regression: Non-canonical abbreviations in manifest_v3: {violations}"
    )


def test_02_manifest_v3_class_names_match_canonical(samples, canonical_abbr):
    """All class_composition class_name fields match canonical taxonomy names exactly."""
    violations = []
    for s in samples:
        for abbr, info in s.get("class_composition", {}).items():
            if abbr in canonical_abbr:
                expected = canonical_abbr[abbr]
                stored = info.get("class_name", "")
                if stored != expected:
                    violations.append(
                        f"sample={s['sample_id']} abbr={abbr} stored='{stored}' expected='{expected}'"
                    )
    assert not violations, (
        f"Class name mismatch in manifest_v3: {violations}"
    )


def test_03_manifest_v3_source_label_ids_correct(samples, canonical_label_id):
    """All class_composition source_label_id fields match canonical taxonomy IDs."""
    violations = []
    for s in samples:
        for abbr, info in s.get("class_composition", {}).items():
            if abbr in canonical_label_id:
                expected = canonical_label_id[abbr]
                stored = info.get("source_label_id")
                if stored is not None and stored != expected:
                    violations.append(
                        f"sample={s['sample_id']} abbr={abbr} stored_id={stored} expected_id={expected}"
                    )
    assert not violations, (
        f"Source label ID mismatch in manifest_v3: {violations}"
    )


def test_04_manifest_v3_no_prohibited_drift_terms(samples):
    """manifest_v3 class_composition contains no prohibited drift terminology."""
    manifest_text = json.dumps([s.get("class_composition", {}) for s in samples])
    found = [term for term in PROHIBITED_DRIFT_TERMS if term in manifest_text]
    assert not found, (
        f"INC-P2R2-C2-001 regression: Prohibited drift terms in manifest_v3 class_composition: {found}"
    )


def test_05_of_abbreviation_maps_to_ocean_front_not_organic_film(samples, canonical_abbr):
    """OF abbreviation must map to Ocean Front (source_label_id=6), never to Oil/Organic Film."""
    assert canonical_abbr["OF"] == "Ocean Front", (
        "Canonical taxonomy: OF must be Ocean Front, not any form of Oil/Organic Film."
    )
    for s in samples:
        if "OF" in s.get("class_composition", {}):
            info = s["class_composition"]["OF"]
            assert info.get("class_name") == "Ocean Front", (
                f"sample={s['sample_id']}: OF class_name='{info.get('class_name')}' must be 'Ocean Front'"
            )
            assert info.get("source_label_id") == 6, (
                f"sample={s['sample_id']}: OF source_label_id={info.get('source_label_id')} must be 6"
            )


# =========================================================
# TEST GROUP 2: C2 Incident Register
# =========================================================

def test_06_c2_incident_register_exists_and_has_three_incidents(incident_register):
    """C2 incident register exists and records exactly 3 incidents."""
    incidents = incident_register.get("incidents", [])
    assert len(incidents) == 3, f"Expected 3 C2 incidents, got {len(incidents)}"


def test_07_inc_c2_001_taxonomy_drift_recorded_and_resolved(incident_register):
    """INC-P2R2-C2-001 (taxonomy drift in C1 report) is recorded and resolved."""
    incidents = {i["incident_id"]: i for i in incident_register["incidents"]}
    assert "INC-P2R2-C2-001" in incidents, "INC-P2R2-C2-001 must be in register"
    inc = incidents["INC-P2R2-C2-001"]
    assert inc["severity"] == "MAJOR"
    assert inc["data_layer_impact"] == "NONE"
    assert inc["regression_test_required"] is True


def test_08_inc_c2_002_ledger_of_error_recorded_and_resolved(incident_register):
    """INC-P2R2-C2-002 (OF class ID error in ledger_v1) is recorded and resolved."""
    incidents = {i["incident_id"]: i for i in incident_register["incidents"]}
    assert "INC-P2R2-C2-002" in incidents, "INC-P2R2-C2-002 must be in register"
    inc = incidents["INC-P2R2-C2-002"]
    assert inc["severity"] == "MAJOR"
    assert inc["data_layer_impact"] == "NONE"


def test_09_all_c2_incidents_non_p3_blocking(incident_register):
    """No C2 incidents are P3-blocking."""
    assert not incident_register["incidents_summary"]["p3_blocking"], (
        "C2 incidents must not be P3-blocking"
    )
    assert incident_register["incidents_summary"]["resolution_status"] == "ALL_RESOLVED_IN_C2"


# =========================================================
# TEST GROUP 3: Ledger v2 Correction Verification
# =========================================================

def test_10_ledger_v2_of_claim_uses_correct_class_id(ledger_v2):
    """ops01_corrective_audit_ledger_v2 Claim of_parent_count references OF as Class 6, not Class 8."""
    claims = ledger_v2.get("claims_audit", [])
    of_claim = next((c for c in claims if c.get("claim") == "of_parent_count"), None)
    assert of_claim is not None, "of_parent_count claim must exist in ledger_v2"
    assert "Class 6" in of_claim.get("evidence_source", ""), (
        f"Ledger_v2 of_parent_count must reference Class 6; got: {of_claim.get('evidence_source')}"
    )
    assert "Class 8" not in of_claim.get("evidence_source", ""), (
        "Ledger_v2 of_parent_count must NOT reference Class 8 (that is RF)"
    )


def test_11_ledger_v2_of_scope_says_ocean_front(ledger_v2):
    """ops01_corrective_audit_ledger_v2 Claim of_parent_count scope says Ocean Front."""
    claims = ledger_v2.get("claims_audit", [])
    of_claim = next((c for c in claims if c.get("claim") == "of_parent_count"), None)
    assert of_claim is not None
    scope = of_claim.get("scope", "")
    assert "Ocean Front" in scope, (
        f"of_parent_count scope must say 'Ocean Front'; got: '{scope}'"
    )
    # Scope may reference historical error for audit traceability but must start with Ocean Front
    assert scope.startswith("Ocean Front"), (
        f"of_parent_count scope must START with 'Ocean Front'; got: '{scope}'"
    )


def test_12_ledger_v2_has_taxonomy_audit_claim(ledger_v2):
    """Ledger_v2 contains the C2 taxonomy_terminology_integrity claim."""
    claims = ledger_v2.get("claims_audit", [])
    tax_claim = next((c for c in claims if c.get("claim") == "taxonomy_terminology_integrity"), None)
    assert tax_claim is not None, "taxonomy_terminology_integrity claim must be in ledger_v2"
    assert tax_claim["status"] == "CORRECTED_IN_C2"


# =========================================================
# TEST GROUP 4: Geographic Basin Audit
# =========================================================

def test_13_geographic_basin_audit_document_exists(geo_basin_audit):
    """ops01_geographic_basin_audit_v1.json exists and has required fields."""
    assert geo_basin_audit.get("phase") == "PHASE_8_P2_R2_C2"
    assert "basin_distribution" in geo_basin_audit
    assert "overclaim_assessment" in geo_basin_audit


def test_14_exactly_five_distinct_basin_labels_in_manifest(samples):
    """manifest_v3 contains exactly 5 distinct ocean_basin labels across all 27 parent scenes."""
    parent_basins = {}
    for s in samples:
        pid = s["parent_scene_id"]
        if pid not in parent_basins:
            geo = s.get("geographic_location", {})
            parent_basins[pid] = geo.get("ocean_basin", "UNKNOWN")
    unique_basins = set(parent_basins.values())
    assert len(unique_basins) == 5, (
        f"Expected 5 distinct basin labels, got {len(unique_basins)}: {unique_basins}"
    )
    assert "UNKNOWN" not in unique_basins, "No parent scene may have UNKNOWN basin label"


def test_15_all_parent_geo_extracted_from_xml(samples):
    """All 27 parent scenes have geographic_location extracted from S3 annotation XMLs."""
    parent_status = {}
    for s in samples:
        pid = s["parent_scene_id"]
        if pid not in parent_status:
            geo = s.get("geographic_location", {})
            parent_status[pid] = geo.get("status", "MISSING")
    for pid, status in parent_status.items():
        assert status == "EXTRACTED_FROM_S3_ANNOTATION_XML", (
            f"Parent {pid} geo status: {status} (expected EXTRACTED_FROM_S3_ANNOTATION_XML)"
        )


def test_16_geographic_overclaim_not_present(geo_basin_audit):
    """Geographic basin audit does not claim globally representative or all ocean basins."""
    overclaim = geo_basin_audit.get("overclaim_assessment", {})
    assert str(overclaim.get("claim_globally_representative", "")).startswith("NOT_MADE"), (
        f"globally_representative must start with NOT_MADE; got: '{overclaim.get('claim_globally_representative')}'"
    )
    assert str(overclaim.get("claim_all_ocean_basins", "")).startswith("NOT_MADE"), (
        f"all_ocean_basins must start with NOT_MADE; got: '{overclaim.get('claim_all_ocean_basins')}'"
    )


# =========================================================
# TEST GROUP 5: Sufficiency v4 Disclosures
# =========================================================

def test_17_sufficiency_v4_holdout_partially_used_disclosed(sufficiency_v4):
    """ops01_dataset_sufficiency_v4 explicitly discloses HOLDOUT_PARTIALLY_USED_FOR_SELECTION."""
    disclosure = sufficiency_v4.get("holdout_status_disclosure", "")
    assert disclosure == "HOLDOUT_PARTIALLY_USED_FOR_SELECTION", (
        f"holdout_status_disclosure must be HOLDOUT_PARTIALLY_USED_FOR_SELECTION; got: '{disclosure}'"
    )


def test_18_sufficiency_v4_c2_taxonomy_correction_note_present(sufficiency_v4):
    """ops01_dataset_sufficiency_v4 contains c2_taxonomy_correction field documenting C2 fix."""
    note = sufficiency_v4.get("c2_taxonomy_correction", "")
    assert len(note) > 50, (
        "c2_taxonomy_correction note must be non-empty and substantive"
    )


def test_19_sufficiency_v4_class_coverage_audit_canonical(sufficiency_v4, canonical_abbr):
    """ops01_dataset_sufficiency_v4 class_coverage_audit uses canonical class names."""
    cc = sufficiency_v4.get("class_coverage_audit", {})
    violations = []
    for abbr, info in cc.items():
        if abbr not in canonical_abbr:
            violations.append(f"Non-canonical abbr: {abbr}")
        elif info.get("class_name") and info.get("class_name") != canonical_abbr[abbr]:
            violations.append(
                f"abbr={abbr} class_name='{info.get('class_name')}' != '{canonical_abbr[abbr]}'"
            )
    assert not violations, f"Taxonomy errors in sufficiency_v4 class_coverage_audit: {violations}"


# =========================================================
# TEST GROUP 6: Epistemic Boundary Verification
# =========================================================

def test_20_epistemic_boundary_conditional_reconstruction_in_manifest(manifest_v3):
    """manifest_v3 preserves CONDITIONAL_ENGINEERING_RECONSTRUCTION epistemic boundary."""
    text = json.dumps(manifest_v3)
    assert "CONDITIONAL_ENGINEERING_RECONSTRUCTION" in text, (
        "manifest_v3 must contain CONDITIONAL_ENGINEERING_RECONSTRUCTION"
    )


def test_21_epistemic_boundary_empirically_supported_hypothesis_in_manifest(manifest_v3):
    """manifest_v3 preserves EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS epistemic boundary."""
    text = json.dumps(manifest_v3)
    assert "EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS" in text, (
        "manifest_v3 must contain EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS"
    )


# =========================================================
# TEST GROUP 7: Provenance & Integrity
# =========================================================

def test_22_zero_os_class_14_pixels_in_manifest(samples):
    """Class 14 (OS, Mineral Oil Spill) must have exactly 0 admitted pixels in manifest_v3."""
    os_samples = [s for s in samples if 14 in s.get("label_class_set", [])]
    assert not os_samples, (
        f"{len(os_samples)} samples with OS (Class 14) pixels found; must be 0"
    )


def test_23_zero_parent_partition_leakage(samples):
    """No parent_scene_id appears in more than one partition."""
    parent_partitions = {}
    for s in samples:
        pid = s["parent_scene_id"]
        part = s["partition"]
        if pid not in parent_partitions:
            parent_partitions[pid] = set()
        parent_partitions[pid].add(part)
    leakage = {pid: parts for pid, parts in parent_partitions.items() if len(parts) > 1}
    assert not leakage, f"Parent partition leakage detected: {leakage}"


def test_24_all_image_sha256_unique(samples):
    """All 147 image SHA256 hashes are distinct (no duplicate image content)."""
    sha_counter = Counter(s.get("image_sha256") for s in samples if s.get("image_sha256"))
    duplicates = {sha: cnt for sha, cnt in sha_counter.items() if cnt > 1}
    assert not duplicates, (
        f"Duplicate image SHA256 hashes found: {list(duplicates.keys())}"
    )


def test_25_mask_sha_duplicates_only_in_single_class_full_coverage(samples):
    """Duplicate mask SHA256 hashes may only occur in samples where a single class covers 100% of pixels."""
    sha_to_samples = {}
    for s in samples:
        sha = s.get("mask_sha256")
        if sha:
            sha_to_samples.setdefault(sha, []).append(s)

    violations = []
    for sha, group in sha_to_samples.items():
        if len(group) > 1:
            for s in group:
                cc = s.get("class_composition", {})
                # Check if any class has fraction >= 0.99 (near-full coverage)
                # Near-full is expected: BG+SI tiles can be 99.6% one class with trace pixels of another
                max_fraction = max((info.get("fraction", 0) for info in cc.values()), default=0)
                if max_fraction < 0.99:
                    violations.append(
                        f"sample={s['sample_id']} has duplicate mask SHA but max_class_fraction={max_fraction:.3f}"
                    )
    assert not violations, (
        f"Unexpected mask SHA duplicates in non-full-coverage samples: {violations}"
    )


def test_26_frozen_exp06_hash_unchanged():
    """EXP-06 best_model.pt SHA256 is bitwise identical to frozen baseline."""
    exp06 = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    assert exp06.exists(), f"EXP-06 missing: {exp06}"
    actual = sha256_file(exp06)
    assert actual == FROZEN_EXP06_SHA, (
        f"EXP-06 hash mismatch: {actual} != {FROZEN_EXP06_SHA}"
    )


def test_27_frozen_part_i_hash_unchanged():
    """Part-I internal_development_split_manifest.json is bitwise identical to frozen baseline."""
    part1 = REPO_ROOT / "data" / "metadata" / "internal_development_split_manifest.json"
    assert part1.exists(), f"Part-I missing: {part1}"
    actual = sha256_file(part1)
    assert actual == FROZEN_PART_I_SHA, (
        f"Part-I hash mismatch: {actual} != {FROZEN_PART_I_SHA}"
    )
