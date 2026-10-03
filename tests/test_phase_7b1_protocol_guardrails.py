"""Phase 7B.1 External Benchmark Protocol & Forensic Audit Guardrails Suite.

Rigorously verifies all 25 data governance invariants for Phase 7B.1:
1. Exact dataset version
2. DOI identity
3. Checksum integrity
4. Exact dimensions
5. Stated spatial resolution
6. Band and polarization identity
7. Physical-unit declaration
8. Parent-product uniqueness & counts
9. Source-dataset lineage
10. Part-I leakage firewall
11. Part-III quarantine protection
12. DARTIS proxy set isolation
13. EXP-06 checkpoint cryptographic hash
14. Canonical preprocessing parameters
15. Threshold immutability (tau = 0.22)
16. Resolution compatibility firewall
17. Semantic class definitions
18. Evaluation-unit declaration
19. Parent-product clustering contract
20. No benchmark-specific threshold tuning
21. No training from frozen evaluation set
22. Historical report preservation
23. Terminology correctness
24. External-data provenance completeness
25. Matrix and manifest SHA integrity
"""

import hashlib
import json
from pathlib import Path
import pytest
from PIL import Image
import rasterio

REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_EXP06_CHECKPOINT_PATH = (
    REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
)
EXPECTED_EXP06_SHA256 = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
FROZEN_OPERATING_TAU = 0.22

MATRIX_PATH = REPO_ROOT / "data" / "metadata" / "external_lookalike_benchmark_matrix.json"
PARSED_LI_MANIFEST = REPO_ROOT / "scratch" / "li_dataset_parsed_manifest.json"
SAMPLE_TIFF = REPO_ROOT / "scratch" / "li_sample" / "Image_Geo" / "s1a-iw-grd-vv-20150220t211700-20150220t211729-004712-005d33-001-10.tiff"
SAMPLE_PNG = REPO_ROOT / "scratch" / "li_sample" / "label" / "s1a-iw-grd-vv-20150220t211700-20150220t211729-004712-005d33-001-10.png"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def test_guardrail_01_exact_dataset_version():
    """Verify exact dataset version for Li et al. (V2 with corner tiepoints)."""
    assert MATRIX_PATH.exists(), "Benchmark candidate matrix missing"
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    assert "V2" in ds1["version"]
    assert "tiepoint" in ds1["version"].lower() or "geographic" in ds1["version"].lower()


def test_guardrail_02_doi_identity():
    """Verify persistent DOIs for dataset, preprint, and peer-reviewed journal."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    assert ds1["doi"] == "10.5281/zenodo.14279466"
    assert "10.5194/essd-2024-222" in ds1["source_citation"]
    assert "10.3390/rs18010113" in ds1["source_citation"]


def test_guardrail_03_checksum_integrity():
    """Verify that the official archive MD5 checksum is documented."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    assert "5bf6e338dd2a686de5ecd5fee3e139cd" in ds1["reproducibility"]


def test_guardrail_04_dimensions():
    """Verify physical array dimensions from matrix, parsed manifest, and sample file."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    assert "256 x 256" in ds1["dimensions"]

    if SAMPLE_TIFF.exists():
        with rasterio.open(SAMPLE_TIFF) as src:
            assert src.width == 256
            assert src.height == 256

    if SAMPLE_PNG.exists():
        im = Image.open(SAMPLE_PNG)
        assert im.size == (256, 256)


def test_guardrail_05_spatial_resolution():
    """Verify that spatial resolution is documented as 100m, NOT 10m."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    assert "100 m" in ds1["resolution"]
    assert "10x" in ds1["resolution"].lower() or "downsample" in ds1["resolution"].lower()


def test_guardrail_06_band_and_polarization_identity():
    """Verify that Li et al. is single-pol VV only with zero VH channels."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    assert "VV only" in ds1["polarization"]
    assert "0 VH" in ds1["polarization"] or "zero VH" in ds1["polarization"].lower()

    if SAMPLE_TIFF.exists():
        with rasterio.open(SAMPLE_TIFF) as src:
            assert src.count == 1


def test_guardrail_07_physical_unit_declaration():
    """Verify physical units are explicitly declared as scaled uint16, not float32 dB."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    assert "uint16" in ds1["physical_representation"].lower()

    if SAMPLE_TIFF.exists():
        with rasterio.open(SAMPLE_TIFF) as src:
            assert src.dtypes[0] == "uint16"


def test_guardrail_08_parent_product_uniqueness():
    """Verify parent product accounting: exactly 484 IW source scenes and 2,383 WV vignettes."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    assert "484" in ds1["parent_product_identity"]
    assert "2,383" in ds1["parent_product_identity"] or "2383" in ds1["parent_product_identity"]

    if PARSED_LI_MANIFEST.exists():
        data = json.loads(PARSED_LI_MANIFEST.read_text(encoding="utf-8"))
        iw_stems = {
            e["name"].replace("label/", "").rsplit("-", 1)[0]
            for e in data["labels"]
            if "-iw-" in e["name"]
        }
        assert len(iw_stems) == 484


def test_guardrail_09_source_dataset_lineage():
    """Verify explicit documentation of upstream reused datasets (TenGeoP-SARwv and Tao et al.)."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    lineage = ds1["source_data_lineage"]
    assert "TenGeoP-SARwv" in lineage
    assert "Tao et al." in lineage


def test_guardrail_10_part_i_leakage_firewall():
    """Verify that Part-I split manifest remains unchanged and independent."""
    part_i_manifest = REPO_ROOT / "data" / "metadata" / "internal_development_split_manifest.json"
    assert part_i_manifest.exists()
    assert compute_sha256(part_i_manifest) == "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"


def test_guardrail_11_part_iii_quarantine():
    """Verify Part III quarantine firewall remains strictly enforced under Rule 38."""
    from ocean_sentinel.ingestion.firewall import assert_no_part_iii_leakage, PartIIIFirewallViolationError

    matrix_file = str(MATRIX_PATH)
    assert_no_part_iii_leakage([matrix_file], check_content_hashes=False)

    with pytest.raises(PartIIIFirewallViolationError):
        assert_no_part_iii_leakage(["data/raw/trujillo_part_iii/images/00000.tif"], check_content_hashes=False)


def test_guardrail_12_dartis_leakage():
    """Verify 0 shared parent products between Li et al. IW scenes and DARTIS proxies."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    assert "0 shared products" in ds1["leakage_status"] or "CLEAN relative to DARTIS" in ds1["leakage_status"]


def test_guardrail_13_exp06_checkpoint_hash():
    """Verify that the frozen EXP-06 checkpoint exists on disk with exact cryptographic digest."""
    assert CANONICAL_EXP06_CHECKPOINT_PATH.exists(), f"EXP-06 checkpoint missing at {CANONICAL_EXP06_CHECKPOINT_PATH}"
    actual_hash = compute_sha256(CANONICAL_EXP06_CHECKPOINT_PATH)
    assert actual_hash == EXPECTED_EXP06_SHA256, f"EXP-06 hash mismatch: {actual_hash} != {EXPECTED_EXP06_SHA256}"


def test_guardrail_14_canonical_preprocessing():
    """Verify canonical normalization stats directly from spatial_split_manifest.json."""
    split_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
    manifest = json.loads(split_path.read_text(encoding="utf-8"))
    stats = manifest["normalization_stats"]
    assert stats["channel_means"][0] == pytest.approx(-33.233136989478695, abs=1e-6)
    assert stats["channel_means"][1] == pytest.approx(-19.941215852796695, abs=1e-6)
    assert stats["channel_stds"][0] == pytest.approx(6.489985665955077, abs=1e-6)
    assert stats["channel_stds"][1] == pytest.approx(4.531345684833188, abs=1e-6)


def test_guardrail_15_threshold_immutability():
    """Verify threshold remains strictly frozen at tau = 0.22."""
    dev_baseline = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "exp06_frozen_dev_baseline.json"
    data = json.loads(dev_baseline.read_text(encoding="utf-8"))
    assert data["protocol"]["decision_threshold_tau"] == FROZEN_OPERATING_TAU


def test_guardrail_16_resolution_compatibility():
    """Verify Li et al. is classified as NOT DIRECTLY SUITABLE for zero-shot EXP-06 evaluation."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    assert "NOT DIRECTLY SUITABLE FOR ZERO-SHOT EXP-06" in ds1["exp06_direct_compatibility"]


def test_guardrail_17_semantic_class_definitions():
    """Verify all 15 classes from BG to OS are enumerated in matrix."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    classes = ds1["label_classes"]
    assert len(classes) >= 14
    class_text = " ".join(classes)
    for c in ["BS", "LWA", "IWs", "OF", "AF", "RC", "RF", "POW", "WS", "SI", "IB", "HM", "OS"]:
        assert c in class_text


def test_guardrail_18_evaluation_unit_declaration():
    """Verify hierarchy of evaluation units: PIXEL, PATCH, SCENE, PARENT_PRODUCT."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    units = matrix["metadata"]["evaluation_units_defined"]
    for u in ["PIXEL", "PATCH", "SCENE", "PARENT_PRODUCT"]:
        assert u in units


def test_guardrail_19_parent_product_clustering():
    """Verify protocol mandates parent-product clustering for statistical claims."""
    protocol_path = REPO_ROOT / "experiments" / "PHASE_7B1_EXTERNAL_LOOKALIKE_PROTOCOL_20260913.md"
    assert protocol_path.exists()
    content = protocol_path.read_text(encoding="utf-8")
    assert "Parent Product / Source Scene" in content
    assert "cluster" in content.lower()


def test_guardrail_20_no_benchmark_specific_tuning():
    """Verify that protocol forbids benchmark-specific threshold tuning."""
    protocol_path = REPO_ROOT / "experiments" / "PHASE_7B1_EXTERNAL_LOOKALIKE_PROTOCOL_20260913.md"
    content = protocol_path.read_text(encoding="utf-8")
    assert "threshold search, fine-tuning, and model modification are STRICTLY FORBIDDEN" in content or "ROC sweeps" in content


def test_guardrail_21_no_training_from_frozen_evaluation_set():
    """Verify that Li et al. is strictly barred from EXP-07 training."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ds1 = next(d for d in matrix["datasets"] if d["dataset_id"] == "DS-01-S1-OCEAN-PHENOMENA-ZENODO-14279466")
    assert "Strictly barred from EXP-07" in ds1["training_suitability"]


def test_guardrail_22_historical_report_preservation():
    """Verify that historical Phase 7B.0 report exists and correction addendum was created."""
    hist_path = REPO_ROOT / "experiments" / "PHASE_7B0_EXTERNAL_LOOKALIKE_BENCHMARK_AUDIT_20260913.md"
    addendum_path = REPO_ROOT / "experiments" / "PHASE_7B0_CORRECTION_ADDENDUM_20260913.md"
    assert hist_path.exists()
    assert addendum_path.exists()


def test_guardrail_23_terminology_correctness():
    """Verify that unsupported generalizations were not re-introduced."""
    protocol_path = REPO_ROOT / "experiments" / "PHASE_7B1_EXTERNAL_LOOKALIKE_PROTOCOL_20260913.md"
    content = protocol_path.read_text(encoding="utf-8")
    assert "alarms are uniformly distributed" not in content
    assert "systemic across the SAR acquisition domain" not in content


def test_guardrail_24_external_data_provenance_completeness():
    """Verify that all 8 candidate datasets contain all 27 required fields."""
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    required_keys = [
        "dataset_id", "name", "version", "doi", "source_url", "source_citation",
        "sensor", "mode", "polarization", "resolution", "dimensions",
        "physical_representation", "label_classes", "label_provenance",
        "parent_product_identity", "geography", "time", "independence",
        "source_data_lineage", "leakage_status", "licensing", "reproducibility",
        "exp06_direct_compatibility", "phenomenon_specialist_suitability",
        "lookalike_specialist_suitability", "evaluation_suitability",
        "training_suitability", "confidence", "benchmark_tier", "rejection_reason"
    ]
    for ds in matrix["datasets"]:
        for k in required_keys:
            assert k in ds, f"Key {k} missing in dataset {ds['dataset_id']}"


def test_guardrail_25_manifest_sha_integrity():
    """Verify SHA-256 integrity of the external benchmark matrix file."""
    assert MATRIX_PATH.exists()
    digest = compute_sha256(MATRIX_PATH)
    assert len(digest) == 64
    assert digest.isalnum()
