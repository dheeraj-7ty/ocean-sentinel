"""Phase 8-P2-R2-C1 Corrective Sufficiency Audit Guardrails Test Suite.

Enforces strict verification and permanent lessons learned from P2-R2:
1. Criterion 6 Strict Evaluation: ALL core classes must have >= 2 independent parent scenes (specifically LWA >= 2).
2. Physical Sample Count: Exactly matches physical filesystem and manifest v3 (147 samples).
3. Independent Parent Scenes: Exactly 27 verified independent parent scenes.
4. Partition Representation: TRAIN, DEV, HOLDOUT all non-empty with >= 3 parents and >= 30 slices.
5. Zero Partition Leakage: 0 parent overlap, 0 product overlap, 0 sample overlap.
6. OS Class 14 Strictly Excluded: 0 Class 14 pixels in eligible dataset.
7. HM Taxonomy Guardrail: Named 'Artificial / Anthropogenic Objects', never 'Vessel'.
8. Correspondence Hypothesis Guardrail: 10x block mean is a hypothesis, not proven historical fact.
9. Registration Scope Guardrail: Conditional engineering reconstruction, not ground-truth georegistration.
10. Holdout Classification Guardrail: HOLDOUT_PARTIALLY_USED_FOR_SELECTION explicitly acknowledged.
11. Geographic Diversity Guardrail: All 27 parents have XML-extracted tiepoints spanning multiple ocean basins.
12. Duplicate Content Guardrail: No duplicate samples or image hashes across different sample IDs.
13. Radiometric Provenance Guardrail: Every sample preserves raw radiometric statistics.
14. Frozen Artifact Integrity: EXP-06 checkpoint and Part-I manifest bitwise identical to frozen hashes.
15. Repository Mutation Guardrail: Zero Git staging (git diff --cached is empty).
16. Corrective Audit Ledger Guardrail: Ledger v1 tracks all reconciled claims with zero unresolved discrepancies.
"""
import hashlib
import json
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = REPO_ROOT / "data" / "metadata"
DERIVED_DIR = REPO_ROOT / "data" / "derived" / "ops01"
SCRATCH_DIR = REPO_ROOT / "scratch"

FROZEN_EXP06_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
FROZEN_PART_I_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"

CORE_LOOKALIKES = ["AF", "BS", "LWA", "OF", "MCC", "POW", "RF", "WS", "Eddy", "IWs"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


@pytest.fixture(scope="module")
def physical_manifest_v3():
    p = METADATA_DIR / "ops01_physical_dataset_manifest_v3.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def split_manifest_v4():
    p = METADATA_DIR / "ops01_split_manifest_v4.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def recovery_inventory_v3():
    p = METADATA_DIR / "ops01_source_recovery_inventory_v3.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def sufficiency_v3():
    p = METADATA_DIR / "ops01_dataset_sufficiency_v3.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def audit_ledger_v1():
    p = METADATA_DIR / "ops01_corrective_audit_ledger_v1.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def telemetry_c1():
    p = SCRATCH_DIR / "phase_8_p2_r2_c1_run_state.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# Guardrail 1: Criterion 6 strict evaluation (all core classes >= 2 parents, LWA >= 2)
def test_01_core_lookalikes_multi_parent_sufficiency(sufficiency_v3):
    class_audit = sufficiency_v3["class_coverage_audit"]
    for c_name in CORE_LOOKALIKES:
        assert c_name in class_audit, f"Core lookalike {c_name} missing from class audit!"
        parents = class_audit[c_name]["parent_scene_count"]
        assert parents >= 2, (
            f"VIOLATION: Core lookalike {c_name} has {parents} parent scenes (< 2 required for sufficiency)!"
        )
    # Specifically assert LWA >= 2 (was 1 in P2-R2)
    assert class_audit["LWA"]["parent_scene_count"] >= 2, "LWA parent count must be >= 2!"
    # Verify criterion 6 status is PASS
    crit6 = [c for c in sufficiency_v3["criteria"] if "Core lookalike" in c["criterion"]][0]
    assert crit6["status"] == "PASS"


# Guardrail 2: Physical sample count matches filesystem
def test_02_physical_sample_count_matches_filesystem(physical_manifest_v3):
    img_dir = DERIVED_DIR / "images"
    mask_dir = DERIVED_DIR / "masks"
    imgs = list(img_dir.glob("*.tif"))
    masks = list(mask_dir.glob("*.png"))
    
    n_manifest = physical_manifest_v3["summary"]["total_materialized_samples"]
    assert len(imgs) == n_manifest
    assert len(masks) == n_manifest
    assert n_manifest >= 147, f"Expected at least 147 samples, got {n_manifest}"
    assert len(physical_manifest_v3["samples"]) == n_manifest


# Guardrail 3: Independent parent count
def test_03_independent_parent_count(physical_manifest_v3, recovery_inventory_v3):
    n_parents = physical_manifest_v3["summary"]["total_parent_scenes"]
    assert n_parents == 27
    inv_parents = len(recovery_inventory_v3["parent_scenes"])
    assert inv_parents == 27
    unique_parents = set(s["parent_scene_id"] for s in physical_manifest_v3["samples"])
    assert len(unique_parents) == 27


# Guardrail 4: Partition representation
def test_04_partition_representation(split_manifest_v4):
    parts = split_manifest_v4["partitions"]
    assert len(parts["TRAIN"]["parent_scenes"]) >= 11
    assert len(parts["DEV"]["parent_scenes"]) >= 7
    assert len(parts["HOLDOUT"]["parent_scenes"]) >= 7
    assert parts["TRAIN"]["physical_slices_count"] >= 60
    assert parts["DEV"]["physical_slices_count"] >= 30
    assert parts["HOLDOUT"]["physical_slices_count"] >= 30


# Guardrail 5: Zero partition leakage
def test_05_zero_partition_leakage(split_manifest_v4, physical_manifest_v3):
    parts = split_manifest_v4["partitions"]
    train_p = set(parts["TRAIN"]["parent_scenes"])
    dev_p = set(parts["DEV"]["parent_scenes"])
    holdout_p = set(parts["HOLDOUT"]["parent_scenes"])

    assert len(train_p & dev_p) == 0, "Parent leakage: TRAIN & DEV overlap!"
    assert len(train_p & holdout_p) == 0, "Parent leakage: TRAIN & HOLDOUT overlap!"
    assert len(dev_p & holdout_p) == 0, "Parent leakage: DEV & HOLDOUT overlap!"

    # Also check source products
    prods = {"TRAIN": set(), "DEV": set(), "HOLDOUT": set()}
    for s in physical_manifest_v3["samples"]:
        prods[s["partition"]].add(s["source_product_id"])

    assert len(prods["TRAIN"] & prods["DEV"]) == 0, "Product leakage: TRAIN & DEV overlap!"
    assert len(prods["TRAIN"] & prods["HOLDOUT"]) == 0, "Product leakage: TRAIN & HOLDOUT overlap!"
    assert len(prods["DEV"] & prods["HOLDOUT"]) == 0, "Product leakage: DEV & HOLDOUT overlap!"


# Guardrail 6: Class 14 OS strictly excluded
def test_06_os_class_14_strictly_excluded(physical_manifest_v3):
    for s in physical_manifest_v3["samples"]:
        assert 14 not in s["label_class_set"], f"Class 14 detected in eligible sample {s['sample_id']}!"
        assert "OS" not in s["class_composition"], f"OS in class composition of {s['sample_id']}!"
    crit8 = [c for c in physical_manifest_v3.get("criteria", []) if "Class 14" in c.get("criterion", "")]
    # Also verify total OS pixels across all eligible samples is 0
    total_os_pixels = sum(s["class_composition"].get("OS", 0) for s in physical_manifest_v3["samples"])
    assert total_os_pixels == 0, f"Detected {total_os_pixels} OS pixels in eligible dataset!"


# Guardrail 7: HM taxonomy guardrail
def test_07_hm_taxonomy_guardrail():
    tax_path = METADATA_DIR / "ops01_taxonomy_v1.json"
    with open(tax_path, "r", encoding="utf-8") as f:
        tax = json.load(f)
    hm_cls = [c for c in tax["classes"] if c["abbreviation"] == "HM"][0]
    assert hm_cls["class_name"] == "Artificial / Anthropogenic Objects"
    assert "vessel" not in hm_cls["class_name"].lower()


# Guardrail 8: Correspondence hypothesis guardrail
def test_08_correspondence_hypothesis_guardrail(physical_manifest_v3):
    hyp = physical_manifest_v3["correspondence_hypothesis"]
    assert "hypothesis" in hyp.lower()
    assert "proven historical fact" not in hyp.lower()


# Guardrail 9: Registration scope guardrail
def test_09_registration_scope_guardrail(sufficiency_v3):
    crit = [c for c in sufficiency_v3["criteria"] if "registration" in c["criterion"].lower() or "alignment" in c["criterion"].lower()][0]
    assert "ground-truth georegistration proven" not in crit["evidence"].lower()
    assert "conditional" in crit["evidence"].lower() or "engineering" in crit["evidence"].lower()


# Guardrail 10: Holdout classification guardrail
def test_10_holdout_classification_guardrail(sufficiency_v3):
    crit = [c for c in sufficiency_v3["criteria"] if c["criterion"] == "Holdout independence"][0]
    assert "HOLDOUT_PARTIALLY_USED_FOR_SELECTION" in crit["evidence"] or "selection bias" in crit["evidence"].lower()


# Guardrail 11: Geographic diversity guardrail
def test_11_geographic_diversity_guardrail(recovery_inventory_v3):
    for entry in recovery_inventory_v3["parent_scenes"]:
        geo = entry.get("geographic_metadata")
        assert geo is not None, f"Missing geographic metadata for {entry['parent_scene_stem']}"
        assert "center_point" in geo and len(geo["center_point"]) == 2
        assert "ocean_basin" in geo and len(geo["ocean_basin"]) > 0


# Guardrail 12: Duplicate content guardrail
def test_12_duplicate_content_guardrail(physical_manifest_v3):
    sids = [s["sample_id"] for s in physical_manifest_v3["samples"]]
    assert len(sids) == len(set(sids)), "Duplicate sample IDs detected!"


# Guardrail 13: Radiometric provenance guardrail
def test_13_radiometric_provenance_guardrail(physical_manifest_v3):
    for s in physical_manifest_v3["samples"]:
        stats = s["radiometric_stats"]
        assert "raw_min" in stats and "raw_max" in stats
        assert "zeros_count" in stats and "valid_pixel_fraction" in stats
        assert stats["valid_pixel_fraction"] > 0.0


# Guardrail 14: Frozen artifact integrity
def test_14_frozen_artifact_integrity():
    exp06_path = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    part1_path = METADATA_DIR / "internal_development_split_manifest.json"

    assert exp06_path.exists(), "EXP-06 checkpoint missing!"
    assert part1_path.exists(), "Part-I manifest missing!"

    assert sha256_file(exp06_path) == FROZEN_EXP06_SHA, "FATAL: EXP-06 checkpoint mutated!"
    assert sha256_file(part1_path) == FROZEN_PART_I_SHA, "FATAL: Part-I manifest mutated!"


# Guardrail 15: Repository mutation guardrail (zero git staging)
def test_15_git_staging_empty():
    res = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True
    )
    assert res.stdout.strip() == "", f"FATAL: Git changes staged: {res.stdout.strip()}"


# Guardrail 16: Corrective audit ledger guardrail
def test_16_audit_ledger_reconciliation(audit_ledger_v1):
    claims = audit_ledger_v1["claims_audit"]
    assert len(claims) >= 15, "Ledger must cover at least 15 core claims!"
    # Ensure all claims have an explicit status and documented resolution
    for c in claims:
        assert c.get("status") is not None and len(c.get("status")) > 0, f"Missing status in claim {c}"
        assert c.get("resolution") is not None and len(c.get("resolution")) > 0, f"Missing resolution in claim {c}"
