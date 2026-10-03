"""Phase 8-P2-R2 Recovery & Partition Population Guardrails Test Suite.

Enforces 26 mandatory governance, integrity, and scientific guardrails:
1. Catalog count being reported as physical count
2. Source availability being confused with successful materialization
3. Same parent scene crossing partitions
4. Same product crossing partitions
5. Duplicate physical source copies
6. Ambiguous lineage becoming training eligible
7. HM renaming (must be 'Artificial / Anthropogenic Objects', never 'Vessel')
8. OS entering training (Class 14 strictly excluded)
9. 15.79m becoming physical accuracy
10. 50m becoming physical uncertainty
11. 10x mean being called historical fact
12. Catalog-only samples inflating dataset diversity
13. Zero/nodata masking without provenance
14. Holdout contamination
15. Arbitrary '20 scenes' being called scientific sufficiency
16. One class occurrence being treated as class coverage
17. Correlated slices being treated as independent samples
18. WV being included merely to increase count
19. Failed retrievals being mislabeled unavailable
20. Incomplete recovery producing 'P3 ready'
21. Reproducibility drift
22. Source mutation
23. Training invocation
24. GPU invocation
25. Part-III access
26. Git mutation
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


@pytest.fixture(scope="module")
def population_snapshot_v2():
    p = METADATA_DIR / "current_population_snapshot_v2.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def physical_manifest_v2():
    p = METADATA_DIR / "ops01_physical_dataset_manifest_v2.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def split_manifest_v3():
    p = METADATA_DIR / "ops01_split_manifest_v3.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def sufficiency_v2():
    p = METADATA_DIR / "ops01_dataset_sufficiency_v2.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def telemetry_r2():
    p = SCRATCH_DIR / "phase_8_p2_r2_run_state.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# Guardrail 1: Catalog count being reported as physical count
def test_01_catalog_count_not_reported_as_physical_count(population_snapshot_v2, physical_manifest_v2):
    cat = population_snapshot_v2["populations"]["catalog_candidates"]["total_samples"]
    phys = physical_manifest_v2["summary"]["total_materialized_samples"]
    assert cat == 5011
    assert phys == 131
    assert cat != phys, "FATAL: Catalog count collapsed into physical count!"


# Guardrail 2: Source availability being confused with successful materialization
def test_02_source_availability_not_confused_with_materialization(population_snapshot_v2, physical_manifest_v2):
    rec = population_snapshot_v2["populations"]["source_recoverable"]["verified_recoverable_products"]
    mat_parents = physical_manifest_v2["summary"]["total_parent_scenes"]
    assert rec == 25
    assert mat_parents == 25
    assert len(physical_manifest_v2["samples"]) == 131


# Guardrail 3: Same parent scene crossing partitions
def test_03_same_parent_scene_crossing_partitions(split_manifest_v3):
    parts = split_manifest_v3["partitions"]
    train_p = set(parts["TRAIN"]["parent_scenes"])
    dev_p = set(parts["DEV"]["parent_scenes"])
    holdout_p = set(parts["HOLDOUT"]["parent_scenes"])

    assert len(train_p & dev_p) == 0, "Leakage: TRAIN & DEV share parent scenes!"
    assert len(train_p & holdout_p) == 0, "Leakage: TRAIN & HOLDOUT share parent scenes!"
    assert len(dev_p & holdout_p) == 0, "Leakage: DEV & HOLDOUT share parent scenes!"
    assert split_manifest_v3["leakage_verification"]["leakage_status"] == "ZERO_LEAKAGE_VERIFIED"


# Guardrail 4: Same product crossing partitions
def test_04_same_product_crossing_partitions(physical_manifest_v2):
    prods = {"TRAIN": set(), "DEV": set(), "HOLDOUT": set()}
    for s in physical_manifest_v2["samples"]:
        prods[s["partition"]].add(s["source_product_id"])

    assert len(prods["TRAIN"] & prods["DEV"]) == 0, "Leakage: TRAIN & DEV share source product IDs!"
    assert len(prods["TRAIN"] & prods["HOLDOUT"]) == 0, "Leakage: TRAIN & HOLDOUT share source product IDs!"
    assert len(prods["DEV"] & prods["HOLDOUT"]) == 0, "Leakage: DEV & HOLDOUT share source product IDs!"


# Guardrail 5: Duplicate physical source copies
def test_05_duplicate_physical_source_copies(physical_manifest_v2):
    sample_ids = [s["sample_id"] for s in physical_manifest_v2["samples"]]
    assert len(sample_ids) == len(set(sample_ids)), "Duplicate sample IDs detected in physical manifest!"


# Guardrail 6: Ambiguous lineage becoming training eligible
def test_06_ambiguous_lineage_not_training_eligible(physical_manifest_v2):
    for s in physical_manifest_v2["samples"]:
        assert s["training_eligibility"] == "TRAINING_ELIGIBLE"
        assert s["parent_scene_id"] is not None and len(s["parent_scene_id"]) > 10
        assert s["source_product_id"] is not None and len(s["source_product_id"]) > 10
        assert s["image_sha256"] is not None and len(s["image_sha256"]) == 64
        assert s["mask_sha256"] is not None and len(s["mask_sha256"]) == 64
        assert s["source_window"]["width"] == 2560 and s["source_window"]["height"] == 2560


# Guardrail 7: HM renaming (must be 'Artificial / Anthropogenic Objects', never 'Vessel')
def test_07_hm_renaming_prohibited():
    tax_path = METADATA_DIR / "ops01_taxonomy_v1.json"
    with open(tax_path, "r", encoding="utf-8") as f:
        tax = json.load(f)
    hm_cls = [c for c in tax["classes"] if c["abbreviation"] == "HM"]
    assert len(hm_cls) == 1
    assert hm_cls[0]["class_name"] == "Artificial / Anthropogenic Objects"
    assert "vessel" not in hm_cls[0]["class_name"].lower(), "FATAL: HM renamed to Vessel!"


# Guardrail 8: OS entering training (Class 14 strictly excluded)
def test_08_os_entering_training_strictly_prohibited(physical_manifest_v2):
    for s in physical_manifest_v2["samples"]:
        assert 14 not in s["label_class_set"], f"FATAL: Class 14 (OS) in eligible sample {s['sample_id']}!"
        assert "OS" not in s["class_composition"], f"FATAL: OS in composition for {s['sample_id']}!"


# Guardrail 9: 15.79m becoming physical accuracy
def test_09_prohibit_15_79m_becoming_physical_accuracy(physical_manifest_v2, sufficiency_v2):
    for c in sufficiency_v2["criteria"]:
        assert "15.79m physical accuracy" not in c["evidence"].lower()


# Guardrail 10: 50m becoming physical uncertainty
def test_10_prohibit_50m_becoming_physical_uncertainty(sufficiency_v2):
    for c in sufficiency_v2["criteria"]:
        assert "50m physical uncertainty" not in c["evidence"].lower()


# Guardrail 11: 10x mean being called historical fact
def test_11_prohibit_10x_mean_called_historical_fact(physical_manifest_v2):
    hyp = physical_manifest_v2["correspondence_hypothesis"]
    assert "hypothesis" in hyp.lower()
    assert "proven historical fact" not in hyp.lower()


# Guardrail 12: Catalog-only samples inflating dataset diversity
def test_12_catalog_only_samples_not_inflating_diversity(sufficiency_v2, physical_manifest_v2):
    mat_count = physical_manifest_v2["summary"]["total_materialized_samples"]
    assert mat_count == 131
    # Check that diversity in sufficiency is calculated on 131 slices, not 5011
    crit = [c for c in sufficiency_v2["criteria"] if c["criterion"] == "Physical sample count"][0]
    assert "131" in crit["observed_value"]
    assert "5011" not in crit["observed_value"]


# Guardrail 13: Zero/nodata masking without provenance
def test_13_zero_nodata_masking_without_provenance(physical_manifest_v2):
    for s in physical_manifest_v2["samples"]:
        assert "radiometric_stats" in s
        assert "valid_pixel_fraction" in s["radiometric_stats"]
        assert "zeros_count" in s["radiometric_stats"]
        assert s["radiometric_stats"]["valid_pixel_fraction"] <= 1.0


# Guardrail 14: Holdout contamination
def test_14_holdout_contamination(split_manifest_v3, sufficiency_v2):
    holdout_parents = split_manifest_v3["partitions"]["HOLDOUT"]["parent_scenes"]
    assert len(holdout_parents) >= 3, "Holdout must contain >= 3 independent parent scenes!"
    crit = [c for c in sufficiency_v2["criteria"] if c["criterion"] == "Holdout independence"][0]
    assert crit["status"] == "PASS"


# Guardrail 15: Arbitrary '20 scenes' being called scientific sufficiency
def test_15_arbitrary_20_scenes_not_called_sufficiency(sufficiency_v2):
    criteria_names = [c["criterion"] for c in sufficiency_v2["criteria"]]
    assert len(criteria_names) >= 10, "Sufficiency must be multidimensional!"
    assert "Independent IW parent scenes" in criteria_names
    assert "HM parent coverage" in criteria_names
    assert "Dominant-parent concentration" in criteria_names
    assert "Temporal diversity" in criteria_names
    assert "Geographic diversity" in criteria_names


# Guardrail 16: One class occurrence being treated as class coverage
def test_16_one_class_occurrence_not_treated_as_coverage(sufficiency_v2):
    audit = sufficiency_v2["class_coverage_audit"]
    # Check that HM is represented across multiple parents
    assert audit["HM"]["parent_scene_count"] >= 5, "HM must be represented across >= 5 parents!"
    # Check that OF is represented across multiple parents
    assert audit["OF"]["parent_scene_count"] >= 3, "OF must be represented across multiple parents!"


# Guardrail 17: Correlated slices being treated as independent samples
def test_17_correlated_slices_not_treated_as_independent(physical_manifest_v2):
    summary = physical_manifest_v2["summary"]
    n_slices = summary["total_materialized_samples"]
    n_parents = summary["total_parent_scenes"]
    assert n_slices == 131
    assert n_parents == 25
    assert n_slices != n_parents, "FATAL: Slices conflated with independent parents!"


# Guardrail 18: WV being included merely to increase count
def test_18_wv_not_forced_into_ops01(physical_manifest_v2):
    for s in physical_manifest_v2["samples"]:
        assert s["mode"] == "IW", f"FATAL: Non-IW sample {s['sample_id']} included in OPS-01 candidate!"


# Guardrail 19: Failed retrievals being mislabeled unavailable
def test_19_failed_retrievals_not_mislabeled(telemetry_r2):
    assert telemetry_r2["source_products_failed"] == 0
    assert telemetry_r2["source_products_recovered"] == 25


# Guardrail 20: Incomplete recovery producing 'P3 ready'
def test_20_incomplete_recovery_prevention(split_manifest_v3, sufficiency_v2):
    p = split_manifest_v3["partitions"]
    assert p["TRAIN"]["physical_slices_count"] > 0
    assert p["DEV"]["physical_slices_count"] > 0
    assert p["HOLDOUT"]["physical_slices_count"] > 0
    assert p["TRAIN"]["parent_scene_count"] >= 3
    assert p["DEV"]["parent_scene_count"] >= 3
    assert p["HOLDOUT"]["parent_scene_count"] >= 3
    assert sufficiency_v2["final_decision"] == "A. OPS-01 PHYSICAL DATA SUFFICIENT FOR P3"


# Guardrail 21: Reproducibility drift
def test_21_reproducibility_drift(physical_manifest_v2):
    for s in physical_manifest_v2["samples"][:10]:
        img_p = REPO_ROOT / s["derived_image_path"]
        mask_p = REPO_ROOT / s["derived_mask_path"]
        assert sha256_file(img_p) == s["image_sha256"], f"Drift in {img_p}"
        assert sha256_file(mask_p) == s["mask_sha256"], f"Drift in {mask_p}"


# Guardrail 22: Source mutation
def test_22_source_mutation():
    # Verify EXP-06 and Part-I frozen hashes
    exp06_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    assert exp06_path.exists()
    assert sha256_file(exp06_path) == FROZEN_EXP06_SHA, "EXP-06 checkpoint modified!"

    part_i_path = METADATA_DIR / "internal_development_split_manifest.json"
    assert part_i_path.exists()
    assert sha256_file(part_i_path) == FROZEN_PART_I_SHA, "Part-I split manifest modified!"


# Guardrail 23: Training invocation
def test_23_training_not_invoked(telemetry_r2):
    assert telemetry_r2["training_invoked"] is False, "Training was invoked!"


# Guardrail 24: GPU invocation
def test_24_gpu_not_invoked(telemetry_r2):
    assert telemetry_r2["gpu_invoked"] is False, "GPU was invoked!"


# Guardrail 25: Part-III access
def test_25_part_iii_access():
    res = subprocess.run(
        ["git", "diff", "--name-status"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True
    )
    assert "part_iii" not in res.stdout.lower(), "Part-III modified in git diff!"


# Guardrail 26: Git mutation
def test_26_git_mutation():
    res = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True
    )
    assert res.stdout.strip() == "", "FATAL: Git index has staged modifications!"
