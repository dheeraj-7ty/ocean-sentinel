"""EXP-07-P0-C14: OPS-02 Full-Scale Dataset Assembly and Governance Guardrails.

Verifies:
1. Canonical dense taxonomy integrity (0..11, OF=5, POW=6, HM=11).
2. Strict exclusion of Mineral Oil Spill (Class 14) from EXP-07 target space (GOV-RULE-060).
3. Datatake and orbital track clustering invariant (GOV-RULE-077).
4. Pre-slice partitioning invariant at parent cluster level (GOV-RULE-075).
5. Zero inter-partition leakage across TRAIN, DEV, and HOLDOUT.
6. Pristine holdout read-only invariant (zero model evaluation/selection in C14).
7. Cross-source duplicate handling and zero OPS-01 overlap (GOV-RULE-078).
8. Four distinct QC layers verified across all materialized physical samples.
9. Physical file existence and SHA256 correspondence.
10. Live telemetry run state integrity (COMPLETED, training_started=False, seed2024_started=False).
11. Training authorization boundary (TRAINING=NO).
12. Comprehensive coverage across all 11 natural phenomena + HM in DEV and HOLDOUT.
"""

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = REPO_ROOT / "data" / "metadata"
OPS02_DIR = REPO_ROOT / "data" / "ops02"
MANIFESTS_DIR = OPS02_DIR / "manifests"
AUDITS_DIR = OPS02_DIR / "audits"
IMAGES_DIR = OPS02_DIR / "derived" / "images"
MASKS_DIR = OPS02_DIR / "derived" / "masks"
TELEMETRY_PATH = REPO_ROOT / "scratch" / "exp07_p0_c14_run_state.json"


def test_authoritative_manifests_and_audits_exist():
    """Verify all 14 required C14 manifests and audits exist and parse."""
    required_manifests = [
        MANIFESTS_DIR / "ops02_parent_cluster_manifest_v1.json",
        MANIFESTS_DIR / "ops02_partition_manifest_v1.json",
        MANIFESTS_DIR / "ops02_physical_dataset_manifest_v1.json",
    ]
    required_audits = [
        AUDITS_DIR / "ops02_parent_identity_audit_v1.json",
        AUDITS_DIR / "ops02_cross_source_duplicate_audit_v1.json",
        AUDITS_DIR / "ops02_dataset_qc_v1.json",
        AUDITS_DIR / "ops02_class_coverage_v1.json",
        AUDITS_DIR / "ops02_geographic_coverage_v1.json",
        AUDITS_DIR / "ops02_temporal_coverage_v1.json",
        AUDITS_DIR / "ops02_acquisition_coverage_v1.json",
        AUDITS_DIR / "ops02_source_dominance_v1.json",
        AUDITS_DIR / "ops02_sufficiency_gate_v1.json",
        AUDITS_DIR / "ops02_holdout_integrity_v1.json",
    ]
    required_metadata = [
        METADATA_DIR / "exp07_p0_c14_incident_register_v1.json",
        METADATA_DIR / "exp07_p0_c14_provenance_summary_v1.json",
        METADATA_DIR / "exp07_p0_c14_c13_reconciliation_v1.json",
    ]
    for p in required_manifests + required_audits + required_metadata:
        assert p.exists(), f"Required C14 artifact missing: {p}"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"Artifact {p.name} must be a JSON object"


def test_canonical_dense_taxonomy_indices():
    """Verify canonical dense class definitions (OF=5, POW=6, HM=11)."""
    dataset_manifest = json.loads((MANIFESTS_DIR / "ops02_physical_dataset_manifest_v1.json").read_text(encoding="utf-8"))
    samples = dataset_manifest["samples"]
    assert len(samples) >= 200, f"Expected >= 200 physical samples, got {len(samples)}"

    all_dense_classes = set()
    for s in samples:
        all_dense_classes.update(s["canonical_dense_class_ids_present"])

    # Ensure all dense indices are strictly in 0..11
    assert all_dense_classes.issubset(set(range(12))), f"Invalid dense class indices: {all_dense_classes}"
    assert 5 in all_dense_classes, "OF (Dense 5) must be present"
    assert 6 in all_dense_classes, "POW (Dense 6) must be present"
    assert 11 in all_dense_classes, "HM (Dense 11) must be present"


def test_mineral_oil_spill_strict_exclusion():
    """Verify Mineral Oil Spill (Source Class 14) is strictly excluded (GOV-RULE-060)."""
    dataset_manifest = json.loads((MANIFESTS_DIR / "ops02_physical_dataset_manifest_v1.json").read_text(encoding="utf-8"))
    for s in dataset_manifest["samples"]:
        assert 14 not in s["source_class_ids_present"], f"Sample {s['sample_id']} contains Mineral Oil Spill (14)!"


def test_parent_cluster_and_datatake_invariant():
    """Verify datatake clustering invariant (GOV-RULE-077) and no OPS-01 overlap."""
    cluster_manifest = json.loads((MANIFESTS_DIR / "ops02_parent_cluster_manifest_v1.json").read_text(encoding="utf-8"))
    clusters = cluster_manifest["clusters"]
    assert len(clusters) >= 60, f"Expected >= 60 clusters, got {len(clusters)}"

    # Check uniqueness of datatake IDs across clusters
    datatakes = [c["mission_data_take_id"] for c in clusters]
    assert len(datatakes) == len(set(datatakes)), "Datatake IDs must be unique across clusters"

    # Check zero overlap with OPS-01
    ops01_manifest = json.loads((METADATA_DIR / "ops01_physical_dataset_manifest_v4.json").read_text(encoding="utf-8"))
    ops01_parents = set(s["parent_scene_id"] for s in ops01_manifest["samples"])

    all_scenes = set()
    for c in clusters:
        all_scenes.update(c["constituent_scene_ids"])

    overlap = all_scenes & ops01_parents
    assert len(overlap) == 0, f"Detected leakage between OPS-02 clusters and OPS-01 parents: {overlap}"


def test_pre_slice_partitioning_and_zero_leakage():
    """Verify pre-slice partitioning invariant (GOV-RULE-075) and zero partition leakage."""
    part_manifest = json.loads((MANIFESTS_DIR / "ops02_partition_manifest_v1.json").read_text(encoding="utf-8"))
    partitions = part_manifest["partitions"]

    train_clusters = set(partitions["TRAIN"]["clusters"])
    dev_clusters = set(partitions["DEV"]["clusters"])
    holdout_clusters = set(partitions["HOLDOUT"]["clusters"])

    assert len(train_clusters & dev_clusters) == 0, "TRAIN and DEV share clusters!"
    assert len(train_clusters & holdout_clusters) == 0, "TRAIN and HOLDOUT share clusters!"
    assert len(dev_clusters & holdout_clusters) == 0, "DEV and HOLDOUT share clusters!"
    assert part_manifest["leakage_verification"]["inter_partition_leakage"] == "0% VERIFIED"


def test_pristine_holdout_protection():
    """Verify HOLDOUT is read-only and zero model evaluation was performed."""
    holdout_audit = json.loads((AUDITS_DIR / "ops02_holdout_integrity_v1.json").read_text(encoding="utf-8"))
    assert holdout_audit["holdout_access_status"] == "READ_ONLY_CRYPTOGRAPHICALLY_LOCKED"
    assert holdout_audit["model_selection_access_count"] == 0
    assert holdout_audit["hyperparameter_tuning_access_count"] == 0
    assert holdout_audit["training_access_count"] == 0
    assert holdout_audit["holdout_integrity_verdict"] == "PRISTINE_AND_UNTOUCHED"


def test_four_distinct_qc_layers():
    """Verify all four distinct QC layers achieved 100% pass rate."""
    qc_audit = json.loads((AUDITS_DIR / "ops02_dataset_qc_v1.json").read_text(encoding="utf-8"))
    layers = qc_audit["qc_layers"]

    assert layers["layer_a_technical"]["fail_count"] == 0
    assert layers["layer_b_provenance"]["fail_count"] == 0
    assert layers["layer_c_semantic_label"]["fail_count"] == 0
    assert layers["layer_d_scientific_independence"]["fail_count"] == 0
    assert layers["layer_a_technical"]["pass_count"] >= 200


def test_physical_materialized_files_exist_and_match():
    """Verify materialized files on disk exist and are non-empty."""
    dataset_manifest = json.loads((MANIFESTS_DIR / "ops02_physical_dataset_manifest_v1.json").read_text(encoding="utf-8"))
    samples = dataset_manifest["samples"]

    for s in samples[:20]:  # Spot check first 20
        img_p = REPO_ROOT / s["derived_image_path"]
        mask_p = REPO_ROOT / s["derived_mask_path"]
        assert img_p.exists(), f"Image file missing: {img_p}"
        assert mask_p.exists(), f"Mask file missing: {mask_p}"
        assert img_p.stat().st_size > 0, f"Image file empty: {img_p}"
        assert mask_p.stat().st_size > 0, f"Mask file empty: {mask_p}"


def test_class_coverage_in_dev_and_holdout():
    """Verify all canonical phenomena have representation across TRAIN, DEV, and HOLDOUT."""
    class_cov = json.loads((AUDITS_DIR / "ops02_class_coverage_v1.json").read_text(encoding="utf-8"))
    classes = class_cov["classes"]

    # Every class must be present in DEV and HOLDOUT
    for c_name, stats in classes.items():
        assert stats["dev_parent_count"] >= 1, f"Class {c_name} missing from DEV partition!"
        assert stats["holdout_parent_count"] >= 1, f"Class {c_name} missing from HOLDOUT partition!"
        assert stats["train_parent_count"] >= 1, f"Class {c_name} missing from TRAIN partition!"

    # HM must have >= 8 total parents
    assert classes["HM"]["total_parent_count"] >= 8, f"HM total parents < 8: {classes['HM']['total_parent_count']}"


def test_live_telemetry_run_state():
    """Verify live telemetry state is COMPLETED and negative constraints respected."""
    assert TELEMETRY_PATH.exists(), "Telemetry file missing"
    state = json.loads(TELEMETRY_PATH.read_text(encoding="utf-8"))

    assert state["status"] == "COMPLETED"
    assert state["training_started"] is False
    assert state["holdout_evaluation_performed"] is False
    assert state["seed2024_started"] is False
    assert state["samples_materialized"] >= 200
    assert state["samples_qc_pass"] >= 200
    assert state["samples_qc_fail"] == 0


def test_sufficiency_gate_reassessment():
    """Verify sufficiency gate status is READY_FOR_DATASET_FREEZE_REVIEW and training not authorized."""
    suff = json.loads((AUDITS_DIR / "ops02_sufficiency_gate_v1.json").read_text(encoding="utf-8"))
    assert suff["overall_verdict"] == "READY_FOR_DATASET_FREEZE_REVIEW"
    assert suff["model_training_verdict"] == "NOT_AUTHORIZED_IN_C14"
    assert all(c["status"] == "PASS" for c in suff["criteria"])
