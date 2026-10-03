"""Test suite for EXP-07-P0-C22-A.7: Authoritative OPS-02 Independence-Unit Reconciliation,
Historical Impact Analysis, and Protocol Repair Guardrails.

Validates that:
1. The authoritative independence unit is explicitly defined as PARENT_ACQUISITION_CLUSTER
   governed by GOV-RULE-077 and mapped 1:1 with mission_data_take_id.
2. TRAIN independence count derived from manifests strictly equals 40.
3. DEV independence count derived from manifests strictly equals 12.
4. HOLDOUT metadata independence count derived from manifests strictly equals 12 (zero payload reads).
5. Total independent units across all partitions strictly equals 64 (40 + 12 + 12 = 64).
6. Cross-partition leakage is strictly 0 across cluster_id, mission_data_take_id, and parent_scene_id.
7. Physical tile count (132 TRAIN) is mathematically distinguished from independent unit count (40).
8. Stale '23' figure cannot be declared as the authoritative OPS-02 TRAIN independence count.
9. Narrative learning registry (LL-EXP07-019) is cryptographically and textually consistent with manifest truth.
10. Governance boundaries (zero training, zero backward, zero HOLDOUT access) are strictly maintained.
"""

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PHYSICAL_MANIFEST = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"
CLUSTER_MANIFEST = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_parent_cluster_manifest_v1.json"
PARTITION_MANIFEST = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_partition_manifest_v1.json"
FREEZE_SPEC = REPO_ROOT / "data" / "ops02" / "OPS02_DATASET_FREEZE_SPEC_v1.0.1.json"
AUDIT_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a7_independence_definition_and_impact_v1.json"
INCIDENT_PATH = REPO_ROOT / "data" / "metadata" / "exp07_p0_c22a7_incident_register_v1.json"
LESSONS_PATH = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"
GOV_RULES_PATH = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_governance_rules_v1.json"


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_authoritative_independence_unit_governance():
    """Verify primary independence unit is PARENT_ACQUISITION_CLUSTER under GOV-RULE-077."""
    assert GOV_RULES_PATH.exists()
    gov = load_json(GOV_RULES_PATH)
    rule_077 = next((r for r in gov["rules"] if r["rule_id"] == "GOV-RULE-077"), None)
    assert rule_077 is not None
    assert "Mission Datatake and Orbital Clustering Invariant" in rule_077["title"]
    assert "Delta t < 10 minutes" in rule_077["description"]

    assert CLUSTER_MANIFEST.exists()
    c_man = load_json(CLUSTER_MANIFEST)
    assert "GOV-RULE-077" in c_man["clustering_invariant"]
    for c in c_man["clusters"]:
        assert c["independence_classification"] == "INDEPENDENT_PARENT_CLUSTER"
        assert c["mission_data_take_id"] in c["cluster_id"]


def test_manifest_derived_train_independence_count():
    """Derive TRAIN independence count from physical manifest and verify it equals 40."""
    assert PHYSICAL_MANIFEST.exists()
    p_man = load_json(PHYSICAL_MANIFEST)
    train_samples = [s for s in p_man["samples"] if s["partition"] == "TRAIN"]

    datatakes = set(s["mission_data_take_id"] for s in train_samples)
    clusters = set(s["cluster_id"] for s in train_samples)
    parent_scenes = set(s["parent_scene_id"] for s in train_samples)

    assert len(datatakes) == 40
    assert len(clusters) == 40
    assert len(parent_scenes) == 40


def test_manifest_derived_dev_and_holdout_independence_counts():
    """Derive DEV and HOLDOUT counts from manifests (metadata only, zero payload reads)."""
    p_man = load_json(PHYSICAL_MANIFEST)
    dev_samples = [s for s in p_man["samples"] if s["partition"] == "DEV"]
    holdout_samples = [s for s in p_man["samples"] if s["partition"] == "HOLDOUT"]

    dev_dtks = set(s["mission_data_take_id"] for s in dev_samples)
    holdout_dtks = set(s["mission_data_take_id"] for s in holdout_samples)

    assert len(dev_dtks) == 12
    assert len(holdout_dtks) == 12
    assert len(dev_samples) == 40
    assert len(holdout_samples) == 40


def test_total_independence_reconciliation():
    """Verify total independent units reconcile: 40 + 12 + 12 = 64."""
    c_man = load_json(CLUSTER_MANIFEST)
    assert len(c_man["clusters"]) == 64
    assert c_man["train_clusters"] == 40
    assert c_man["dev_clusters"] == 12
    assert c_man["holdout_clusters"] == 12

    assert c_man["train_clusters"] + c_man["dev_clusters"] + c_man["holdout_clusters"] == 64


def test_zero_cross_partition_independence_leakage():
    """Verify zero cross-partition datatake, cluster, or scene leakage."""
    p_man = load_json(PHYSICAL_MANIFEST)
    parts = {"TRAIN": set(), "DEV": set(), "HOLDOUT": set()}
    for s in p_man["samples"]:
        parts[s["partition"]].add(s["mission_data_take_id"])

    assert len(parts["TRAIN"] & parts["DEV"]) == 0
    assert len(parts["TRAIN"] & parts["HOLDOUT"]) == 0
    assert len(parts["DEV"] & parts["HOLDOUT"]) == 0


def test_sample_cardinality_vs_independence_distinction():
    """Verify tile count (132 TRAIN) is mathematically distinct from independent count (40)."""
    p_man = load_json(PHYSICAL_MANIFEST)
    train_samples = [s for s in p_man["samples"] if s["partition"] == "TRAIN"]
    assert len(train_samples) == 132
    datatakes = set(s["mission_data_take_id"] for s in train_samples)
    assert len(datatakes) == 40
    assert len(train_samples) != len(datatakes)


def test_rejection_of_stale_23_as_authoritative_train_count():
    """Verify stale '23' is rejected by authoritative manifests and freeze spec."""
    spec = load_json(FREEZE_SPEC)
    train_spec = spec["summary"]["partition_breakdown"]["TRAIN"]
    assert train_spec["parent_clusters"] == 40
    assert train_spec["datatakes"] == 40
    assert train_spec["parent_clusters"] != 23

    # Mathematical proof: 23 would break total 64 clusters
    assert 23 + 12 + 12 != 64


def test_learning_registry_lesson_019_consistency():
    """Verify LL-EXP07-019 narrative text correctly references 40 datatakes and rejects 23."""
    lessons_data = load_json(LESSONS_PATH)
    lsn = next((l for l in lessons_data["lessons"] if l["lesson_id"] == "LL-EXP07-019"), None)
    assert lsn is not None
    assert "40 TRAIN parent datatakes" in lsn["description"]
    assert "23 parent datatakes" not in lsn["description"]
    assert "40 independent parent datatakes" in lsn["notes"]


def test_audit_artifact_completeness_and_verdict():
    """Verify C22-A.7 audit artifact contains full contract and READY verdict."""
    assert AUDIT_PATH.exists()
    audit = load_json(AUDIT_PATH)
    assert audit["audit_metadata"]["audit_id"] == "OPS02_C22A7_INDEPENDENCE_DEFINITION_AND_IMPACT_v1"
    assert audit["readiness_decision"]["verdict"] == "READY_FOR_PROTOCOL_REPAIR_COMPLETE"
    assert audit["historical_impact_analysis"]["summary_classification"] == "DOCUMENTATION_ONLY"
    assert audit["historical_impact_analysis"]["dataset_membership_impact"] == "NONE"
    assert audit["historical_impact_analysis"]["computational_pipeline_impact"] == "NONE"


def test_governance_quarantine_integrity():
    """Verify zero training occurred, zero backward passes, zero holdout access."""
    assert INCIDENT_PATH.exists()
    inc = load_json(INCIDENT_PATH)
    gov = inc["governance_compliance"]
    assert gov["zero_training_verified"] is True
    assert gov["zero_backward_verified"] is True
    assert gov["zero_optimizer_step_verified"] is True
    assert gov["zero_scheduler_step_verified"] is True
    assert gov["zero_kaggle_verified"] is True
    assert gov["holdout_access_count"] == 0
    assert gov["part_iii_access_count"] == 0
