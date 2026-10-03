"""Guardrail and regression test suite for Ocean Sentinel Phase 7B.0.

Validates external lookalike benchmark discovery, provenance audit, and evaluation-protocol design:
1. Acquisition rejection vs semantic rejection separation.
2. Unsupported 'uniform distribution' and 'SAR domain' wording eliminated.
3. External benchmark independence requirements codified.
4. Dataset label-type distinction enforced.
5. Annotation vs ground truth distinction documented.
6. Parent-product clustering metadata declared.
7. No external dataset enters training in Phase 7B.0 (EXP-07 blocked).
8. No threshold optimization (tau=0.22 frozen).
9. Part-I immutability preserved.
10. Part-III quarantine preserved.
11. Benchmark manifest integrity and deterministic ordering.
12. Provenance completeness across all audited candidate datasets.
13. Durable telemetry finalized.
"""

import hashlib
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = REPO_ROOT / "data" / "metadata"
EXPERIMENTS_DIR = REPO_ROOT / "experiments"

INTERNAL_MANIFEST = METADATA_DIR / "internal_development_split_manifest.json"
PART_III_AUDIT = METADATA_DIR / "part_iii_exclusion_audit.json"
PROXY_SEMANTIC_MANIFEST = METADATA_DIR / "proxy_semantic_dataset_manifest.json"
PROXY_SEMANTIC_MATRIX = METADATA_DIR / "proxy_semantic_evidence_matrix.json"
BENCHMARK_MATRIX_PATH = METADATA_DIR / "external_lookalike_benchmark_matrix.json"
PHASE_7A3_CORRECTED_REPORT = EXPERIMENTS_DIR / "PHASE_7A3_SEMANTIC_ADJUDICATION_REPORT_20260913_CORRECTED.md"
PHASE_7A3_ADDENDUM = EXPERIMENTS_DIR / "PHASE_7A3_CORRECTION_ADDENDUM_20260913.md"
PHASE_7B0_REPORT = EXPERIMENTS_DIR / "PHASE_7B0_EXTERNAL_LOOKALIKE_BENCHMARK_AUDIT_20260913.md"
TELEMETRY_7B0 = REPO_ROOT / "scratch" / "phase_7b0_benchmark_audit_run_state.json"
EXP06_CKPT = EXPERIMENTS_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_acquisition_vs_semantic_rejection_separation():
    """1. Acquisition rejection must remain REJECTED_ACQUISITION and not REJECTED_SEMANTIC."""
    assert PROXY_SEMANTIC_MANIFEST.is_file()
    with open(PROXY_SEMANTIC_MANIFEST, "r", encoding="utf-8") as f:
        man = json.load(f)

    assert man["summary"]["rejected_acquisition"] == 30
    assert "rejected_semantic" not in man["status_breakdown"]
    assert man["status_breakdown"]["REJECTED_ACQUISITION"] == 30

    with open(PROXY_SEMANTIC_MATRIX, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    rej_candidates = [c for c in matrix["candidates"] if c["physical_validation_status"] == "REJECTED_ACQUISITION"]
    assert len(rej_candidates) == 30
    for c in rej_candidates:
        assert c["semantic_status"] == "REJECTED_ACQUISITION"
        assert c["physical_raster_path"] is None


def test_unsupported_uniform_distribution_wording_eliminated():
    """2. Verify that corrected reports do NOT claim 'uniformly distributed' alarms."""
    assert PHASE_7A3_CORRECTED_REPORT.is_file()
    text = PHASE_7A3_CORRECTED_REPORT.read_text(encoding="utf-8")
    assert "uniformly distributed" not in text.lower()
    assert "alarm-producing patches occur across a large majority of parent products" in text.lower()


def test_unsupported_sar_domain_generalization_eliminated():
    """3. Verify that corrected reports do NOT claim 'systemic across the SAR acquisition domain'."""
    assert PHASE_7A3_CORRECTED_REPORT.is_file()
    text = PHASE_7A3_CORRECTED_REPORT.read_text(encoding="utf-8")
    assert "systemic across the sar acquisition domain" not in text.lower()
    assert "observed across a large majority of parent products in this evaluated proxy population" in text.lower()


def test_external_benchmark_independence_requirement():
    """4. External benchmark matrix must record independence from Part-I, Part-III, and DARTIS."""
    assert BENCHMARK_MATRIX_PATH.is_file()
    with open(BENCHMARK_MATRIX_PATH, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    datasets = matrix["datasets"]
    assert len(datasets) >= 5
    for d in datasets:
        assert "independence_from_part_i" in d
        assert "independence_from_part_iii" in d
        assert "independence_from_dartis" in d


def test_dataset_label_type_distinction():
    """5. Dataset matrix must explicitly distinguish label types (pixel mask vs scene categorical)."""
    with open(BENCHMARK_MATRIX_PATH, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    for d in matrix["datasets"]:
        assert "label_type" in d
        assert len(d["label_type"]) > 0


def test_annotation_vs_ground_truth_distinction():
    """6. Dataset matrix must distinguish annotation method from ground truth provenance."""
    with open(BENCHMARK_MATRIX_PATH, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    for d in matrix["datasets"]:
        assert "annotation_method" in d
        assert "annotation_vs_ground_truth" in d


def test_parent_product_clustering_metadata():
    """7. Evaluation units in benchmark matrix must account for parent product clustering."""
    with open(BENCHMARK_MATRIX_PATH, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    units = matrix["metadata"]["evaluation_units_defined"]
    assert "PARENT_PRODUCT" in units
    assert "PATCH" in units
    assert "PIXEL" in units


def test_no_external_dataset_enters_training_in_phase_7b0():
    """8. No external dataset may enter training, fine-tuning, or candidate pools in Phase 7B.0."""
    exp07_dirs = list((EXPERIMENTS_DIR / "performance").glob("exp07*"))
    assert len(exp07_dirs) == 0, f"Found unauthorized EXP-07 directory: {exp07_dirs}"

    # Verify no bulk benchmark downloads exist in raw data
    raw_dir = REPO_ROOT / "data" / "raw"
    external_downloads = list(raw_dir.glob("external_benchmarks*"))
    assert len(external_downloads) == 0, f"Unauthorized external benchmark download found: {external_downloads}"


def test_no_threshold_optimization_phase_7b0():
    """9. Canonical threshold tau=0.22 remains frozen."""
    dev_baseline_file = EXPERIMENTS_DIR / "performance" / "exp06_positive_bce_weight" / "exp06_frozen_dev_baseline.json"
    assert dev_baseline_file.is_file()
    with open(dev_baseline_file, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    assert baseline["protocol"]["decision_threshold_tau"] == 0.22


def test_part_i_immutability_phase_7b0():
    """10. Part-I development manifest remains strictly bitwise unchanged."""
    assert INTERNAL_MANIFEST.is_file()
    computed_sha = compute_sha256(INTERNAL_MANIFEST)
    assert computed_sha == "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"


def test_part_iii_quarantine_phase_7b0():
    """11. Part-III benchmark remains strictly quarantined under Rule 38."""
    assert PART_III_AUDIT.is_file()
    with open(PART_III_AUDIT, "r", encoding="utf-8") as f:
        p3 = json.load(f)
    assert p3["scene_level_excluded_regions_count"] == 680


def test_benchmark_matrix_integrity_and_determinism():
    """12. Benchmark candidate matrix must be deterministically sorted and contain all 8 datasets."""
    with open(BENCHMARK_MATRIX_PATH, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    datasets = matrix["datasets"]
    assert len(datasets) == 8
    dataset_ids = [d["dataset_id"] for d in datasets]
    assert dataset_ids == sorted(dataset_ids)


def test_provenance_completeness():
    """13. All 8 datasets must have complete provenance metadata."""
    with open(BENCHMARK_MATRIX_PATH, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    for d in matrix["datasets"]:
        assert d["name"]
        assert d["sensor"]
        assert d["polarization"]
        assert d["resolution"]
        assert d["geography"]
        assert d["time_period"]
        assert d["benchmark_tier"] in ("TIER 1", "TIER 2", "TIER 3", "TIER 4", "TIER 5")
        assert d["recommendation"]


def test_durable_telemetry_phase_7b0():
    """14. Phase 7B.0 telemetry must exist and record completed state."""
    assert TELEMETRY_7B0.is_file()
    with open(TELEMETRY_7B0, "r", encoding="utf-8") as f:
        telem = json.load(f)
    assert telem["status"] == "COMPLETED"
    assert telem["candidate_datasets_found"] == 8
    assert len(telem["final_ranking"]) == 8
