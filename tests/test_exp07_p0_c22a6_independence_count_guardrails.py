"""Test suite for EXP-07-P0-C22-A.6: OPS-02 Independence-Count Reconciliation and Authorization Gate.

Validates that:
1. Manifest sample counts are exact: 132 TRAIN, 40 DEV, 40 HOLDOUT (212 total).
2. Manifest parent cluster counts are exact: 40 TRAIN, 12 DEV, 12 HOLDOUT (64 total).
3. Manifest-derived TRAIN independence count evaluates to 40 across mission_data_take_id,
   cluster_id, and parent_scene_id, and does NOT equal 23.
4. The audit strictly enforces Part B & Part M governance: since manifest-derived count != 23,
   the readiness decision is strictly BLOCKED.
5. Zero training updates, zero backward passes, zero HOLDOUT access occurred.
"""

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PHYSICAL_MANIFEST = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"
CLUSTER_MANIFEST = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_parent_cluster_manifest_v1.json"
FREEZE_SPEC = REPO_ROOT / "data" / "ops02" / "OPS02_DATASET_FREEZE_SPEC_v1.0.1.json"
AUDIT_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a6_independence_count_reconciliation_v1.json"
INCIDENT_PATH = REPO_ROOT / "data" / "metadata" / "exp07_p0_c22a6_incident_register_v1.json"
TELEMETRY_PATH = REPO_ROOT / "scratch" / "exp07_p0_c22a6_run_state.json"


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_manifest_sample_counts_and_partition_breakdown():
    """Verify physical sample counts: 132 TRAIN, 40 DEV, 40 HOLDOUT, 212 total."""
    assert PHYSICAL_MANIFEST.exists()
    p_man = load_json(PHYSICAL_MANIFEST)
    samples = p_man["samples"]

    assert len(samples) == 212
    train_s = [s for s in samples if s["partition"] == "TRAIN"]
    dev_s = [s for s in samples if s["partition"] == "DEV"]
    holdout_s = [s for s in samples if s["partition"] == "HOLDOUT"]

    assert len(train_s) == 132
    assert len(dev_s) == 40
    assert len(holdout_s) == 40


def test_manifest_parent_cluster_counts():
    """Verify parent cluster counts in ops02_parent_cluster_manifest_v1.json: 64 total (40 TRAIN, 12 DEV, 12 HOLDOUT)."""
    assert CLUSTER_MANIFEST.exists()
    c_man = load_json(CLUSTER_MANIFEST)
    clusters = c_man["clusters"]

    assert len(clusters) == 64
    assert sum(1 for c in clusters if c["partition"] == "TRAIN") == 40
    assert sum(1 for c in clusters if c["partition"] == "DEV") == 12
    assert sum(1 for c in clusters if c["partition"] == "HOLDOUT") == 12


def test_manifest_derived_train_independence_count_is_40_not_23():
    """Derive TRAIN independence count from manifest fields and verify it equals 40, NOT 23."""
    p_man = load_json(PHYSICAL_MANIFEST)
    train_samples = [s for s in p_man["samples"] if s["partition"] == "TRAIN"]

    datatakes = set(s["mission_data_take_id"] for s in train_samples)
    clusters = set(s["cluster_id"] for s in train_samples)
    parent_scenes = set(s["parent_scene_id"] for s in train_samples)

    # All three candidate fields derive 40
    assert len(datatakes) == 40
    assert len(clusters) == 40
    assert len(parent_scenes) == 40

    # Machine truth is 40, which disproves the claimed 23
    assert len(datatakes) != 23
    assert len(clusters) != 23


def test_freeze_spec_mathematical_consistency():
    """Verify OPS02_DATASET_FREEZE_SPEC_v1.0.1.json partition breakdown math (40 + 12 + 12 = 64)."""
    assert FREEZE_SPEC.exists()
    spec = load_json(FREEZE_SPEC)
    breakdown = spec["summary"]["partition_breakdown"]

    tr_c = breakdown["TRAIN"]["parent_clusters"]
    dev_c = breakdown["DEV"]["parent_clusters"]
    ho_c = breakdown["HOLDOUT"]["parent_clusters"]

    assert tr_c == 40
    assert dev_c == 12
    assert ho_c == 12
    assert tr_c + dev_c + ho_c == 64

    # If TRAIN were 23, total clusters would be 47, violating the frozen 64-cluster specification
    assert 23 + dev_c + ho_c != 64


def test_reconciliation_audit_verdict_is_blocked():
    """Verify that audit strictly adheres to Part B and Part M rules and outputs BLOCKED."""
    assert AUDIT_PATH.exists()
    audit = load_json(AUDIT_PATH)

    assert audit["audit_metadata"]["audit_id"] == "OPS02_C22A6_INDEPENDENCE_COUNT_RECONCILIATION_v1"
    assert audit["readiness_decision"]["verdict"] == "BLOCKED"
    assert "40" in audit["readiness_decision"]["justification"]
    assert "23" in audit["readiness_decision"]["justification"]


def test_incident_register_records_critical_blocker():
    """Verify incident register catalogs INC-C22A6-001 with CRITICAL severity and BLOCKED status."""
    assert INCIDENT_PATH.exists()
    inc_data = load_json(INCIDENT_PATH)

    incidents = {inc["incident_id"]: inc for inc in inc_data["incidents_catalogued"]}
    assert "INC-C22A6-001" in incidents
    inc = incidents["INC-C22A6-001"]
    assert inc["severity"] == "CRITICAL"
    assert inc["whether_current_evaluation_was_blocked"] is True


def test_zero_training_and_firewall_compliance():
    """Verify zero training occurred, zero backward passes, and zero holdout access."""
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
