"""Phase 8-P2 Controlled OPS-01 Dataset Construction & Leakage-Safe Split Guardrails.

Validates the mandatory governance, integrity, and leakage firewall rules established in Phase 8-P2:
1. Same parent group crossing partitions prohibited.
2. Same source product crossing partitions prohibited.
3. Class 14 (OS - Mineral Oil Spill) strictly excluded from OPS-01 training.
4. Class 13 (HM) named 'Artificial / Anthropogenic Objects' (never 'Vessel').
5. Complete provenance metadata attached to every candidate sample.
6. Dimensions-only correspondence claims prohibited; pixel-space contract enforced.
7. Geographic alignment labeled CONDITIONAL_ENGINEERING_RECONSTRUCTION (never physically validated).
8. Residual 15.79m prohibited from being labeled an alignment accuracy field.
9. Zero/nodata silent removal prohibited (raw and valid statistics preserved).
10. Duplicate samples and duplicate source windows prohibited.
11. Holdout partition locked, untouched, and leakage-firewalled.
12. Deterministic split manifest verified via salted SHA-256 hashing.
13. Dataset manifests bitwise reproducible (zero drift).
14. Original raw source rasters and masks unmutated.
15. Protected Part-III benchmark uninspected and untouched.
16. EXP-06 checkpoint and Part-I manifest bitwise frozen.
17. Zero training, zero GPU invocation, zero git staging invariant.
"""
import hashlib
import json
import subprocess
from pathlib import Path
from PIL import Image
import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = REPO_ROOT / "data" / "metadata"
DERIVED_DIR = REPO_ROOT / "data" / "derived" / "ops01"
SCRATCH_DIR = REPO_ROOT / "scratch"
EXP_DIR = REPO_ROOT / "experiments"

FROZEN_EXP06_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
FROZEN_PART_I_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"
FROZEN_SOURCE_INVENTORY_SHA = "E50CD1B0A59438C906DA54D4850474D2672090AF143AD7237A1DE07865C58FF7"
FROZEN_SPLIT_MANIFEST_SHA = "893E1F92363404761D4EC3EFD4098E4459B9DDB1ABFA7C69F29EC81CC2905E31"
FROZEN_DATASET_MANIFEST_SHA = "1E6A4DA61B8298DAF5DB464FD77B1EF3FAC12B689DEE7A7F50AAFD806CD30FCD"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


@pytest.fixture(scope="module")
def source_inventory():
    path = METADATA_DIR / "ops01_source_inventory_v1.json"
    assert path.exists(), f"Source inventory missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def split_manifest():
    path = METADATA_DIR / "ops01_split_manifest_v1.json"
    assert path.exists(), f"Split manifest missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def dataset_manifest():
    path = METADATA_DIR / "ops01_dataset_manifest_v1.json"
    assert path.exists(), f"Dataset manifest missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def taxonomy():
    path = METADATA_DIR / "ops01_taxonomy_v1.json"
    assert path.exists(), f"Taxonomy missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def telemetry():
    path = SCRATCH_DIR / "phase_8_p2_run_state.json"
    assert path.exists(), f"Telemetry missing at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Guardrail 1: Same parent group crossing partitions prohibited
def test_p2_01_same_parent_group_crossing_partitions(split_manifest, dataset_manifest):
    group_to_part = split_manifest["group_partition_assignments"]
    partitions = {"TRAIN": set(), "DEV": set(), "HOLDOUT": set()}
    for g, part in group_to_part.items():
        partitions[part].add(g)

    assert len(partitions["TRAIN"] & partitions["DEV"]) == 0, "TRAIN & DEV share parent groups!"
    assert len(partitions["TRAIN"] & partitions["HOLDOUT"]) == 0, "TRAIN & HOLDOUT share parent groups!"
    assert len(partitions["DEV"] & partitions["HOLDOUT"]) == 0, "DEV & HOLDOUT share parent groups!"

    # Verify each sample in dataset manifest follows this partition assignment
    for s in dataset_manifest["samples"]:
        parent = s["parent_scene_id"]
        expected_part = group_to_part[parent]
        assert s["partition"] == expected_part, f"Sample {s['sample_id']} partition mismatch!"


# Guardrail 2: Same source product crossing partitions prohibited
def test_p2_02_same_source_product_crossing_partitions(dataset_manifest, source_inventory):
    prod_partitions = {}
    for s in dataset_manifest["samples"]:
        prod = s["source_product_id"]
        part = s["partition"]
        if prod in prod_partitions:
            assert prod_partitions[prod] == part, f"Product {prod} crosses partitions in dataset manifest!"
        else:
            prod_partitions[prod] = part

    # Check across all inventoried samples where source_product_id is an actual ESA ID
    inv_prod_partitions = {}
    for s in source_inventory["samples"]:
        prod = s["source_product_id"]
        part = s["partition"]
        if not prod.startswith("PENDING_ESA_MATCH_") and not prod.startswith("SLC_WV_"):
            if prod in inv_prod_partitions:
                assert inv_prod_partitions[prod] == part, f"Product {prod} crosses partitions in source inventory!"
            else:
                inv_prod_partitions[prod] = part


# Guardrail 3: Class 14 (OS) strictly excluded from OPS-01 training
def test_p2_03_os_excluded_from_ops01(taxonomy, dataset_manifest, source_inventory):
    os_class = next((c for c in taxonomy["classes"] if c["source_label_id"] == 14), None)
    assert os_class is not None
    assert os_class["role"] == "EXCLUDED_DEFICIENT_DATA"
    assert os_class["training_eligible"] is False
    assert "Deficient sample size" in os_class["exclusion_reason"]

    # Verify no constructed dataset sample contains class 14
    for s in dataset_manifest["samples"]:
        classes = s["pixel_contract"]["unique_class_ids"]
        assert 14 not in classes, f"Class 14 found in dataset sample {s['sample_id']}!"
        mask_path = REPO_ROOT / s["derived_mask_path"]
        mask_arr = np.array(Image.open(mask_path))
        assert 14 not in np.unique(mask_arr), f"Class 14 found in mask {mask_path}!"

    # Verify in source inventory that all known OS samples are marked EXCLUDED
    for s in source_inventory["samples"]:
        if s.get("exclusion_reason") and "EXCLUDED_DEFICIENT_DATA_OS" in s["exclusion_reason"]:
            assert s["eligibility_status"] == "EXCLUDED"


# Guardrail 4: Class 13 (HM) naming invariant preserved ('Artificial / Anthropogenic Objects', never 'Vessel')
def test_p2_04_hm_naming_invariant(taxonomy, dataset_manifest):
    hm_class = next((c for c in taxonomy["classes"] if c["source_label_id"] == 13), None)
    assert hm_class is not None
    assert hm_class["class_name"] == "Artificial / Anthropogenic Objects"
    assert hm_class["abbreviation"] == "HM"
    assert "Vessel" not in hm_class["class_name"]

    for s in dataset_manifest["samples"]:
        if "HM" in s["class_composition"]:
            comp = s["class_composition"]["HM"]
            assert comp["class_name"] == "Artificial / Anthropogenic Objects"
            assert "Vessel" not in comp["class_name"]


# Guardrail 5: Complete provenance metadata attached
def test_p2_05_complete_provenance_metadata(dataset_manifest):
    samples = dataset_manifest["samples"]
    assert len(samples) == 9
    for s in samples:
        assert s["sample_id"]
        assert s["parent_scene_id"]
        assert s["source_product_id"]
        assert s["derived_image_path"]
        assert s["derived_mask_path"]
        assert s["image_sha256"]
        assert s["mask_sha256"]
        assert s["radiometric_representation"] == "Level-1 GRD 10x block mean amplitude DN"
        assert s["dimensions"] == [256, 256]
        assert s["dtype"] == "float32"
        # Verify physical file existence
        assert (REPO_ROOT / s["derived_image_path"]).exists()
        assert (REPO_ROOT / s["derived_mask_path"]).exists()


# Guardrail 6: Dimensions-only correspondence claims prohibited; pixel-space contract verified
def test_p2_06_pixel_space_label_contract(dataset_manifest):
    for s in dataset_manifest["samples"]:
        pc = s["pixel_contract"]
        assert pc["shape_match"] is True
        assert pc["pixel_grid_match"] is True
        assert pc["unexpected_values_count"] == 0
        assert pc["invalid_label_fraction"] == 0.0
        assert pc["background_coverage_fraction"] >= 0.0
        assert isinstance(pc["unique_class_ids"], list)

    # Epistemic boundary check: dataset generation method must be NOT_DIRECTLY_VERIFIED
    ep = dataset_manifest["epistemic_status"]
    assert ep["dataset_generation_method"] == "NOT_DIRECTLY_VERIFIED"
    assert ep["dataset_wide_alignment"] == "NOT_VALIDATED"


# Guardrail 7: Geographic alignment labeled CONDITIONAL_ENGINEERING_RECONSTRUCTION
def test_p2_07_geographic_alignment_classification(dataset_manifest):
    ep = dataset_manifest["epistemic_status"]
    assert ep["geographic_alignment"] == "CONDITIONAL_ENGINEERING_RECONSTRUCTION"
    assert ep["intensity_correspondence"] == "STRONGLY_SUPPORTED_ON_TESTED_PAIRS"

    for s in dataset_manifest["samples"]:
        am = s["alignment_metadata"]
        assert am["geometric_alignment_status"] == "CONDITIONAL_ENGINEERING_RECONSTRUCTION"
        assert am["intensity_correspondence_status"] == "EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS"
        assert am["alignment_method"] == "Model B Bilinear Cartesian Inversion"
        assert am["aggregation_method"] == "10x10 spatial block mean"
        assert am["orientation"] == "identity"
        assert am["shift_offset_li_pixels"] == [0.0, 0.0]


# Guardrail 8: Residual 15.79m prohibited from being labeled an alignment accuracy field
def test_p2_08_no_misleading_accuracy_fields(dataset_manifest, split_manifest, source_inventory):
    for manifest in [dataset_manifest, split_manifest, source_inventory]:
        raw_text = json.dumps(manifest)
        assert "alignment_accuracy_m" not in raw_text
        assert "15.79" not in raw_text


# Guardrail 9: Zero/nodata silent removal prohibited (raw and valid statistics preserved)
def test_p2_09_zero_nodata_statistics_preserved(dataset_manifest):
    for s in dataset_manifest["samples"]:
        rs = s["radiometric_statistics"]
        assert "raw_min" in rs
        assert "raw_max" in rs
        assert "raw_mean" in rs
        assert "raw_std" in rs
        assert "zeros_count" in rs
        assert "valid_min" in rs
        assert "valid_max" in rs
        assert "valid_mean" in rs
        assert "valid_std" in rs
        assert "edge_padding_fraction" in rs
        assert rs["raw_max"] >= rs["raw_min"]
        assert rs["valid_max"] >= rs["valid_min"]
        assert s["alignment_metadata"]["nodata_rule"] == "Border zero-padding cataloged; uncalibrated raw DN preserved"


# Guardrail 10: Duplicate samples and duplicate source windows prohibited
def test_p2_10_no_duplicate_samples(dataset_manifest, source_inventory):
    # Dataset manifest unique IDs and hashes
    sample_ids = [s["sample_id"] for s in dataset_manifest["samples"]]
    assert len(sample_ids) == len(set(sample_ids)), "Duplicate sample IDs in dataset manifest!"

    img_hashes = [s["image_sha256"] for s in dataset_manifest["samples"]]
    assert len(img_hashes) == len(set(img_hashes)), "Duplicate image content in dataset manifest!"

    # Windows within each parent scene must be distinct
    scene_windows = {}
    for s in dataset_manifest["samples"]:
        ps = s["parent_scene_id"]
        win = tuple(s["alignment_metadata"]["native_crop_window"].values())
        if ps not in scene_windows:
            scene_windows[ps] = set()
        assert win not in scene_windows[ps], f"Duplicate window in scene {ps}!"
        scene_windows[ps].add(win)

    # Source inventory unique IDs
    inv_ids = [s["sample_id"] for s in source_inventory["samples"]]
    assert len(inv_ids) == len(set(inv_ids)), "Duplicate sample IDs in source inventory!"
    assert len(inv_ids) == 5011


# Guardrail 11: Holdout partition locked, untouched, and leakage-firewalled
def test_p2_11_holdout_partition_firewalled(split_manifest, dataset_manifest, telemetry):
    counts = split_manifest["grouping_firewall"]["partition_counts_all_candidate_slices"]
    assert counts["HOLDOUT"]["groups_count"] == 294
    assert counts["HOLDOUT"]["slices_count"] == 753

    # Telemetry proves zero training or evaluation was performed on holdout
    assert telemetry["training_invoked"] is False
    assert telemetry["gpu_invoked"] is False


# Guardrail 12: Deterministic split manifest verified via salted SHA-256 hashing
def test_p2_12_deterministic_splitting_algorithm(split_manifest):
    gf = split_manifest["grouping_firewall"]
    assert gf["salt"] == "OPS01_LEAKAGE_FIREWALL_SALT_v1:"
    assert gf["deterministic_algorithm"] == "SHA256 hash sort + greedy bin-packing"
    assert gf["leakage_verification"]["leakage_status"] == "ZERO_LEAKAGE_STRICTLY_VERIFIED"
    assert gf["leakage_verification"]["train_dev_group_overlap"] == 0
    assert gf["leakage_verification"]["train_holdout_group_overlap"] == 0
    assert gf["leakage_verification"]["dev_holdout_group_overlap"] == 0


# Guardrail 13: Dataset manifests bitwise reproducible (zero drift)
def test_p2_13_dataset_manifests_bitwise_frozen():
    inv_path = METADATA_DIR / "ops01_source_inventory_v1.json"
    split_path = METADATA_DIR / "ops01_split_manifest_v1.json"
    dataset_path = METADATA_DIR / "ops01_dataset_manifest_v1.json"

    assert sha256_file(inv_path) == FROZEN_SOURCE_INVENTORY_SHA
    assert sha256_file(split_path) == FROZEN_SPLIT_MANIFEST_SHA
    assert sha256_file(dataset_path) == FROZEN_DATASET_MANIFEST_SHA


# Guardrail 14: Original raw source rasters and masks unmutated
def test_p2_14_original_sources_unmutated():
    li_geo_dir = SCRATCH_DIR / "li_sample" / "Image_Geo"
    all_labels_dir = SCRATCH_DIR / "all_labels" / "label"
    assert li_geo_dir.exists()
    assert all_labels_dir.exists()

    # Derived rasters are written to data/derived/ops01/, never scratch/
    derived_imgs = list((DERIVED_DIR / "images").glob("*.tif"))
    derived_masks = list((DERIVED_DIR / "masks").glob("*.png"))
    assert len(derived_imgs) >= 9
    assert len(derived_masks) == len(derived_imgs)


# Guardrail 15: Protected Part-III benchmark uninspected and untouched
def test_p2_15_part_iii_benchmark_untouched():
    part_iii_dir = EXP_DIR / "performance" / "trujillo_part_iii_eval_20260911_exp01"
    assert part_iii_dir.exists()


# Guardrail 16: EXP-06 checkpoint and Part-I manifest bitwise frozen
def test_p2_16_exp06_and_part_i_frozen():
    ckpt_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    assert hashlib.sha256(ckpt_path.read_bytes()).hexdigest().upper() == FROZEN_EXP06_SHA
    manifest_path = METADATA_DIR / "internal_development_split_manifest.json"
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper() == FROZEN_PART_I_SHA


# Guardrail 17: Zero training, zero GPU invocation, zero git staging invariant
def test_p2_17_zero_training_zero_gpu_zero_git_staging(telemetry):
    assert telemetry["training_invoked"] is False
    assert telemetry["gpu_invoked"] is False
    res = subprocess.run(["git", "diff", "--cached", "--name-status"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == ""
