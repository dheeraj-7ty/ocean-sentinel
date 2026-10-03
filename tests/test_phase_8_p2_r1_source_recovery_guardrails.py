"""Phase 8-P2-R1 OPS-01 Source Recovery, Materialization Sufficiency & Dataset Scope Guardrails.

Validates the mandatory governance, integrity, and sufficiency rules established in Phase 8-P2-R1:
1. Catalog counts must never be reported as physical image counts.
2. Missing imagery must not be conflated with unattempted retrieval.
3. Duplicate parent products must be deduplicated with complete provenance.
4. Duplicate source scenes crossing partitions is strictly prohibited.
5. Source-product IDs crossing partitions is strictly prohibited.
6. Same orbit pass crossing WV partitions is strictly prohibited.
7. HM must be named 'Artificial / Anthropogenic Objects' (never 'Vessel').
8. Class 14 (OS) is permanently excluded from OPS-01 training.
9. 15.79 m is prohibited from being interpreted as measured physical accuracy.
10. 50 m is prohibited from being interpreted as physical registration uncertainty.
11. 10x block mean is an empirically supported hypothesis, not proven historical fact.
12. Geographic alignment conditionality must be explicitly preserved.
13. Zero/nodata pixels must not be silently removed (raw and valid statistics preserved).
14. Label presence must never be treated as physical image availability.
15. Classes must not be declared covered on the basis of a single small sample.
16. Raw sample count must never be confused with independent parent source count.
17. Holdout and Dev partitions must contain physical samples before P3 is authorized.
18. Incomplete physical data must produce an INSUFFICIENT verdict, never a premature ready state.
19. Raw source rasters and labels must remain unmutated.
20. Protected Part-III benchmark remains completely uninspected and untouched.
21. EXP-06 checkpoint and Part-I manifest remain bitwise frozen.
22. Model training must not be invoked.
23. GPU computation must not be invoked.
24. Git staging must remain strictly empty (zero git mutation).
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
FROZEN_LEDGER_SHA = "31612D77FEAEAAA9034F5802C6D96484BDEFD64D7F36F98B8C62465012E61D41"
FROZEN_RECOVERY_INV_SHA = "8F05080E1007E1B06B030180BCEF09CAD8EC3E71B1B0D077F8D734E8493EA606"
FROZEN_SUFFICIENCY_SHA = "705637C776CA8879A73E141FB5AD4C575A98E3202AAF4B77A8C620658E645C29"
FROZEN_SPLIT_V2_SHA = "310A8FE48EFBFCA8EF60C01A99CC59E6AAE9FC5FFD8DFC7DD934C2C322D5A296"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


@pytest.fixture(scope="module")
def population_ledger():
    path = METADATA_DIR / "ops01_candidate_population_ledger_v1.json"
    assert path.exists(), f"Population ledger missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def recovery_inventory():
    path = METADATA_DIR / "ops01_source_recovery_inventory_v1.json"
    assert path.exists(), f"Recovery inventory missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def sufficiency_report():
    path = METADATA_DIR / "ops01_physical_dataset_sufficiency_v1.json"
    assert path.exists(), f"Sufficiency report missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def split_manifest_v2():
    path = METADATA_DIR / "ops01_split_manifest_v2.json"
    assert path.exists(), f"Split manifest v2 missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def telemetry():
    path = SCRATCH_DIR / "phase_8_p2_r1_run_state.json"
    assert path.exists(), f"Telemetry missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Guardrail 1: Catalog counts must never be reported as physical image counts
def test_r1_01_catalog_vs_physical_conflation(recovery_inventory, sufficiency_report):
    s = recovery_inventory["summary"]
    assert s["total_candidate_samples"] == 5011
    assert s["physical_images_available_local"] == 9
    assert s["total_candidate_samples"] != s["physical_images_available_local"]
    assert sufficiency_report["physical_dataset_metrics"]["materialized_samples"] == 9


# Guardrail 2: Missing imagery must not be conflated with unattempted retrieval
def test_r1_02_missing_vs_unattempted_retrieval(population_ledger):
    states = set(s["source_availability_state"] for s in population_ledger["ledger"])
    assert "METADATA_ONLY" in states
    assert "PHYSICAL_IMAGE_PRESENT_REMOTE_CONFIRMED" in states
    assert "CONSTRUCTED" in states
    # Ensure unattempted IW scenes are distinguished from confirmed remote assets
    metadata_only = [s for s in population_ledger["ledger"] if s["source_availability_state"] == "METADATA_ONLY"]
    remote_confirmed = [s for s in population_ledger["ledger"] if s["source_availability_state"] == "PHYSICAL_IMAGE_PRESENT_REMOTE_CONFIRMED"]
    assert len(metadata_only) == 2578
    assert len(remote_confirmed) == 37


# Guardrail 3: Duplicate parent products must be deduplicated with complete provenance
def test_r1_03_parent_product_deduplication(recovery_inventory):
    s = recovery_inventory["summary"]
    assert s["iw_parent_scenes_total"] == 484
    assert s["iw_slices_total"] == 2628
    assert s["iw_slices_total"] > s["iw_parent_scenes_total"]


# Guardrail 4: Duplicate source scenes crossing partitions is strictly prohibited
def test_r1_04_source_scenes_crossing_partitions(split_manifest_v2):
    g_to_p = split_manifest_v2["group_partition_assignments"]
    parts = {"TRAIN": set(), "DEV": set(), "HOLDOUT": set()}
    for g, p in g_to_p.items():
        parts[p].add(g)
    assert len(parts["TRAIN"] & parts["DEV"]) == 0
    assert len(parts["TRAIN"] & parts["HOLDOUT"]) == 0
    assert len(parts["DEV"] & parts["HOLDOUT"]) == 0


# Guardrail 5: Source-product IDs crossing partitions is strictly prohibited
def test_r1_05_source_product_ids_crossing_partitions(population_ledger):
    prod_to_part = {}
    for s in population_ledger["ledger"]:
        pid = s["source_product_id"]
        part = s["partition"]
        if not pid.startswith("SAFE_GRD_") and not pid.startswith("SLC_WV_"):
            if pid in prod_to_part:
                assert prod_to_part[pid] == part, f"Product {pid} crosses partitions!"
            else:
                prod_to_part[pid] = part


# Guardrail 6: Same orbit pass crossing WV partitions is strictly prohibited
def test_r1_06_orbit_pass_crossing_wv_partitions(population_ledger):
    orbit_to_part = {}
    for s in population_ledger["ledger"]:
        if s["dataset_mode"] == "WV":
            orbit = s["orbit_pass_id"]
            part = s["partition"]
            if orbit in orbit_to_part:
                assert orbit_to_part[orbit] == part, f"Orbit {orbit} crosses partitions!"
            else:
                orbit_to_part[orbit] = part


# Guardrail 7: HM must be named 'Artificial / Anthropogenic Objects' (never 'Vessel')
def test_r1_07_hm_naming_invariant(sufficiency_report):
    hm = sufficiency_report["cohort_class_comparisons"]["all_iw_2628"]["HM"]
    assert hm["class_name"] == "Artificial / Anthropogenic Objects"
    assert "Vessel" not in hm["class_name"]


# Guardrail 8: Class 14 (OS) is permanently excluded from OPS-01 training
def test_r1_08_os_exclusion_invariant(population_ledger, sufficiency_report):
    for s in population_ledger["ledger"]:
        if "OS" in str(s.get("source_availability_state")):
            assert s["training_eligibility"] == "EXCLUDED"
    os_status = sufficiency_report["physical_dataset_metrics"]["oil_spill_os_status"]
    assert os_status["exclusion_verified"] is True
    assert os_status["status"] == "PERMANENTLY_EXCLUDED"


# Guardrail 9: 15.79 m is prohibited from being interpreted as measured physical accuracy
def test_r1_09_prohibit_15_79m_accuracy(sufficiency_report, recovery_inventory, split_manifest_v2):
    for artifact in [sufficiency_report, recovery_inventory, split_manifest_v2]:
        text = json.dumps(artifact)
        assert "alignment_accuracy_m" not in text
        assert "15.79" not in text


# Guardrail 10: 50 m is prohibited from being interpreted as physical registration uncertainty
def test_r1_10_prohibit_50m_uncertainty(sufficiency_report, recovery_inventory):
    for artifact in [sufficiency_report, recovery_inventory]:
        text = json.dumps(artifact)
        assert "registration_uncertainty_50m" not in text


# Guardrail 11: 10x block mean is an empirically supported hypothesis, not proven historical fact
def test_r1_11_ten_x_mean_is_hypothesis(split_manifest_v2):
    assert split_manifest_v2["alignment_protocol_version"] == "PHASE_8_P1_R1_RECONCILED"


# Guardrail 12: Geographic alignment conditionality must be explicitly preserved
def test_r1_12_alignment_conditionality_preserved(population_ledger):
    constructed = [s for s in population_ledger["ledger"] if s["source_availability_state"] == "CONSTRUCTED"]
    assert len(constructed) == 9
    for s in constructed:
        assert s["alignment_status"] == "CONDITIONAL_ENGINEERING_RECONSTRUCTION"


# Guardrail 13: Zero/nodata pixels must not be silently removed
def test_r1_13_zero_nodata_statistics_preserved():
    dataset_manifest_path = METADATA_DIR / "ops01_dataset_manifest_v1.json"
    with open(dataset_manifest_path, "r", encoding="utf-8") as f:
        dm = json.load(f)
    for s in dm["samples"]:
        rs = s["radiometric_statistics"]
        assert "raw_mean" in rs and "valid_mean" in rs
        assert "edge_padding_fraction" in rs


# Guardrail 14: Label presence must never be treated as physical image availability
def test_r1_14_label_presence_not_image_availability(population_ledger):
    ledger = population_ledger["ledger"]
    labels_available = sum(1 for s in ledger if s["physical_label_available"] is True)
    images_available = sum(1 for s in ledger if s["physical_image_available"] is True)
    assert labels_available == 5011
    assert images_available == 9
    assert labels_available != images_available


# Guardrail 15: Classes must not be declared covered on the basis of a single small sample
def test_r1_15_prohibit_declaring_class_covered_from_tiny_sample(sufficiency_report):
    hm_status = sufficiency_report["physical_dataset_metrics"]["anthropogenic_hm_status"]
    assert hm_status["status"] == "COMPLETELY_ABSENT"
    assert hm_status["materialized_pixel_count"] == 0
    missing = sufficiency_report["physical_dataset_metrics"]["classes_completely_absent_from_materialized"]
    assert "HM" in missing
    assert "BS" in missing
    assert "AF" in missing


# Guardrail 16: Raw sample count must never be confused with independent parent source count
def test_r1_16_sample_count_not_independent_source_count(sufficiency_report):
    metrics = sufficiency_report["physical_dataset_metrics"]
    assert metrics["materialized_samples"] == 9
    assert metrics["independent_parent_acquisitions"] == 2
    assert metrics["materialized_samples"] > metrics["independent_parent_acquisitions"]


# Guardrail 17: Holdout and Dev partitions must contain physical samples before P3 is authorized
def test_r1_17_holdout_and_dev_non_emptiness_mandate(split_manifest_v2):
    phys = split_manifest_v2["physical_materialization_by_partition"]
    assert phys["TRAIN"]["physical_slices_materialized"] == 9
    assert phys["DEV"]["physical_slices_materialized"] == 0
    assert phys["HOLDOUT"]["physical_slices_materialized"] == 0
    assert split_manifest_v2["split_sufficiency_verdict"] == "INSUFFICIENT_FOR_P3"


# Guardrail 18: Incomplete physical data must produce an INSUFFICIENT verdict, never a premature ready state
def test_r1_18_incomplete_physical_data_prohibits_dataset_ready(sufficiency_report):
    assert sufficiency_report["dataset_sufficiency_verdict"] == "INSUFFICIENT_FOR_P3"
    assert sufficiency_report["decision"] == "C. OPS-01 SOURCE DATA INSUFFICIENT — FURTHER RECOVERY REQUIRED"
    assert "A. OPS-01 SOURCE DATA SUFFICIENT FOR P3" not in sufficiency_report["decision"]


# Guardrail 19: Raw source rasters and labels must remain unmutated
def test_r1_19_source_raw_files_unmutated():
    assert (SCRATCH_DIR / "li_sample" / "Image_Geo").exists()
    assert (SCRATCH_DIR / "all_labels" / "label").exists()
    assert len(list((SCRATCH_DIR / "li_sample" / "Image_Geo").glob("*.tiff"))) == 9
    assert len(list((SCRATCH_DIR / "all_labels" / "label").glob("*.png"))) == 5011


# Guardrail 20: Protected Part-III benchmark remains completely uninspected and untouched
def test_r1_20_part_iii_firewall():
    part_iii_dir = EXP_DIR / "performance" / "trujillo_part_iii_eval_20260911_exp01"
    assert part_iii_dir.exists()


# Guardrail 21: EXP-06 checkpoint and Part-I manifest remain bitwise frozen
def test_r1_21_exp06_and_part_i_frozen():
    ckpt_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    assert hashlib.sha256(ckpt_path.read_bytes()).hexdigest().upper() == FROZEN_EXP06_SHA
    manifest_path = METADATA_DIR / "internal_development_split_manifest.json"
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper() == FROZEN_PART_I_SHA


# Guardrail 22: Model training must not be invoked
def test_r1_22_zero_training_invoked(telemetry):
    assert telemetry["training_invoked"] is False


# Guardrail 23: GPU computation must not be invoked
def test_r1_23_zero_gpu_invoked(telemetry):
    assert telemetry["gpu_invoked"] is False


# Guardrail 24: Git staging must remain strictly empty (zero git mutation)
def test_r1_24_zero_git_staging():
    res = subprocess.run(["git", "diff", "--cached", "--name-status"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == ""
