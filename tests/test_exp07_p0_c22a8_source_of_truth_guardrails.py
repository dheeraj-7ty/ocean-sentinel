"""Test suite for EXP-07-P0-C22-A.8: Final Source-of-Truth Independence Contract Audit
and Pre-Training Authorization Gate.

Validates that:
1. Authoritative independence unit is PARENT_ACQUISITION_CLUSTER (cluster_id) under GOV-RULE-077.
2. cluster_id <-> mission_data_take_id is strictly bijective (functions and inverses) across OPS-02.
3. TRAIN independent parent cluster count derived from manifests strictly equals 40.
4. DEV independent parent cluster count derived from manifests strictly equals 12.
5. HOLDOUT metadata cluster count derived from manifests strictly equals 12 (metadata only).
6. Total independent parent clusters across OPS-02 strictly equals 64 (40 + 12 + 12 = 64).
7. Physical sample counts strictly equal 132 TRAIN, 40 DEV, 40 HOLDOUT (212 total).
8. Zero cross-partition independence leakage across all fields.
9. Executable C21 protocol contains zero stale '23' independence figures.
10. Actual C22-B execution scripts contain zero stale '23' parameters.
11. Tile count (132 TRAIN) is not treated as replication count (40).
12. Canonical dataset manifest hash remains bitwise unchanged.
13. Canonical initial model state hash remains bitwise unchanged.
14. Preserved historical random initial state hash remains bitwise unchanged.
15. Source-of-truth audit artifact declares READY_FOR_USER_AUTHORIZATION.
"""

import hashlib
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PHYSICAL_MANIFEST = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"
CLUSTER_MANIFEST = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_parent_cluster_manifest_v1.json"
PARTITION_MANIFEST = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_partition_manifest_v1.json"
FREEZE_SPEC = REPO_ROOT / "data" / "ops02" / "OPS02_DATASET_FREEZE_SPEC_v1.0.1.json"
C21_PROTOCOL = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c21_single_variable_diagnostic_protocol_v1.json"
C21_HYPOTHESIS = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c21_hypothesis_information_value_v1.json"
AUDIT_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a8_final_independence_source_of_truth_v1.json"
INCIDENT_PATH = REPO_ROOT / "data" / "metadata" / "exp07_p0_c22a8_incident_register_v1.json"
CANONICAL_MODEL = REPO_ROOT / "data" / "ops02" / "initial_model_state_canonical.pt"
HISTORICAL_RANDOM = REPO_ROOT / "data" / "ops02" / "initial_model_state.pt"


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(65536):
            h.update(b)
    return h.hexdigest().upper()


def test_01_authoritative_independence_unit_contract():
    """Verify authoritative unit is PARENT_ACQUISITION_CLUSTER under GOV-RULE-077."""
    assert CLUSTER_MANIFEST.exists()
    c_man = load_json(CLUSTER_MANIFEST)
    assert "GOV-RULE-077" in c_man["clustering_invariant"]
    for c in c_man["clusters"]:
        assert c["independence_classification"] == "INDEPENDENT_PARENT_CLUSTER"
        assert c["cluster_id"].startswith("ops02_cluster_")


def test_02_cluster_datatake_bijection_proof():
    """Mathematically prove cluster_id <-> mission_data_take_id is bijective."""
    p_man = load_json(PHYSICAL_MANIFEST)
    c_man = load_json(CLUSTER_MANIFEST)

    dtk_to_cid = {}
    cid_to_dtk = {}
    for s in p_man["samples"]:
        dtk = s["mission_data_take_id"]
        cid = s["cluster_id"]
        if dtk in dtk_to_cid:
            assert dtk_to_cid[dtk] == cid
        else:
            dtk_to_cid[dtk] = cid
        if cid in cid_to_dtk:
            assert cid_to_dtk[cid] == dtk
        else:
            cid_to_dtk[cid] = dtk

    assert len(dtk_to_cid) == len(cid_to_dtk) == 64
    for c in c_man["clusters"]:
        assert dtk_to_cid[c["mission_data_take_id"]] == c["cluster_id"]
        assert cid_to_dtk[c["cluster_id"]] == c["mission_data_take_id"]


def test_03_partition_independence_counts_derived():
    """Derive partition independence counts from manifests: 40 TRAIN, 12 DEV, 12 HOLDOUT."""
    p_man = load_json(PHYSICAL_MANIFEST)
    train_cids = set(s["cluster_id"] for s in p_man["samples"] if s["partition"] == "TRAIN")
    dev_cids = set(s["cluster_id"] for s in p_man["samples"] if s["partition"] == "DEV")
    holdout_cids = set(s["cluster_id"] for s in p_man["samples"] if s["partition"] == "HOLDOUT")

    assert len(train_cids) == 40
    assert len(dev_cids) == 12
    assert len(holdout_cids) == 12
    assert len(train_cids) + len(dev_cids) + len(holdout_cids) == 64


def test_04_physical_sample_counts_derived():
    """Derive physical sample counts from manifests: 132 TRAIN, 40 DEV, 40 HOLDOUT (212 total)."""
    p_man = load_json(PHYSICAL_MANIFEST)
    samples = p_man["samples"]
    assert len(samples) == 212

    train_s = [s for s in samples if s["partition"] == "TRAIN"]
    dev_s = [s for s in samples if s["partition"] == "DEV"]
    holdout_s = [s for s in samples if s["partition"] == "HOLDOUT"]

    assert len(train_s) == 132
    assert len(dev_s) == 40
    assert len(holdout_s) == 40


def test_05_zero_cross_partition_leakage():
    """Verify zero cross-partition leakage across cluster_id and mission_data_take_id."""
    p_man = load_json(PHYSICAL_MANIFEST)
    train_cids = set(s["cluster_id"] for s in p_man["samples"] if s["partition"] == "TRAIN")
    dev_cids = set(s["cluster_id"] for s in p_man["samples"] if s["partition"] == "DEV")
    holdout_cids = set(s["cluster_id"] for s in p_man["samples"] if s["partition"] == "HOLDOUT")

    assert len(train_cids & dev_cids) == 0
    assert len(train_cids & holdout_cids) == 0
    assert len(dev_cids & holdout_cids) == 0


def test_06_c21_protocol_absence_of_stale_23():
    """Verify executable C21 protocol contains zero stale '23' independence count."""
    assert C21_PROTOCOL.exists()
    content = C21_PROTOCOL.read_text(encoding="utf-8")
    assert "23 datatakes" not in content
    assert "23 clusters" not in content
    assert "23 independent" not in content

    # Check C21 hypothesis audit statement
    assert C21_HYPOTHESIS.exists()
    hyp = load_json(C21_HYPOTHESIS)
    h1 = next(h for h in hyp["hypothesis_evaluation_matrix"] if h["hypothesis_id"] == "H1")
    assert "40 TRAIN datatakes" in h1["statement"]
    assert "23 datatakes across 212" not in h1["statement"]


def test_07_c22b_execution_scripts_absence_of_stale_23():
    """Verify C22-B execution scripts do not parameterize or reference stale 23."""
    rehearse_path = REPO_ROOT / "scripts" / "rehearse_exp07_diag01_canonical_zero_step.py"
    assert rehearse_path.exists()
    lines = rehearse_path.read_text(encoding="utf-8").splitlines()
    for lno, line in enumerate(lines, 1):
        if "23" in line:
            # Must not be a parameter or count
            assert "datatake" not in line.lower()
            assert "cluster" not in line.lower()


def test_08_tile_count_vs_replication_count_distinction():
    """Verify tile count (132) is mathematically distinguished from cluster count (40)."""
    p_man = load_json(PHYSICAL_MANIFEST)
    train_samples = [s for s in p_man["samples"] if s["partition"] == "TRAIN"]
    assert len(train_samples) == 132
    clusters = set(s["cluster_id"] for s in train_samples)
    assert len(clusters) == 40
    assert len(train_samples) != len(clusters)


def test_09_canonical_dataset_manifest_hash_integrity():
    """Verify physical dataset manifest SHA-256 hash remains 100% bitwise identical."""
    expected_hash = "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"
    actual_hash = sha256_file(PHYSICAL_MANIFEST)
    assert actual_hash == expected_hash


def test_10_canonical_model_state_hashes_integrity():
    """Verify canonical model state and historical random state remain bitwise identical."""
    assert CANONICAL_MODEL.exists()
    assert HISTORICAL_RANDOM.exists()

    expected_canonical_sha256 = "67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D"
    expected_random_sha256 = "4BB233DB629E44DE12E41F11809024B7A5BDA4DBCFB19D13752295973117E45C"

    assert sha256_file(CANONICAL_MODEL) == expected_canonical_sha256
    assert sha256_file(HISTORICAL_RANDOM) == expected_random_sha256


def test_11_audit_artifact_completeness_and_verdict():
    """Verify C22-A.8 audit artifact is complete and verdict is READY_FOR_USER_AUTHORIZATION."""
    assert AUDIT_PATH.exists()
    audit = load_json(AUDIT_PATH)
    assert audit["audit_metadata"]["audit_id"] == "OPS02_C22A8_FINAL_INDEPENDENCE_SOURCE_OF_TRUTH_v1"
    assert audit["readiness_decision"]["verdict"] == "READY_FOR_USER_AUTHORIZATION"
    assert audit["bijection_mathematical_proof"]["are_exact_inverses"] is True
    assert audit["c22b_computational_dependency_audit"]["c22b_readiness"] == "100% VERIFIED_FOR_FUTURE_EXECUTION"


def test_12_governance_safety_boundaries():
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
