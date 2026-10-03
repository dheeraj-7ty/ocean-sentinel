"""EXP-07-P0-C22-D: Multi-Seed Replication Guardrails and Invariant Verification.

Verifies:
1. Small-sample statistical framing (no forced p < 0.05 gate, explicit small-n limitations).
2. Evidence calibration: Case B classification (seed-sensitive effect, no canonical policy change).
3. Clear separation of historical discovery (Seed 42) and prospective replications (Seeds 101, 202, 303, 404).
4. Machine truth exactness for all paired deltas and aggregate metrics.
5. Bitwise artifact integrity across all 37 replication files against manifest.
6. Canonical status quo preservation (C16 loss weights remain locked as canonical).
7. Strict zero HOLDOUT and Part III payload access firewall.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def replication_audit() -> dict:
    audit_path = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22d_multiseed_replication_v1.json"
    assert audit_path.exists(), f"Audit file not found: {audit_path}"
    with open(audit_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def replication_aggregate() -> dict:
    agg_path = REPO_ROOT / "experiments" / "EXP-07" / "runs" / "EXP07_DIAG01_REPLICATION" / "exp07_diag01_replication_aggregate.json"
    assert agg_path.exists(), f"Aggregate file not found: {agg_path}"
    with open(agg_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def lessons_learned() -> dict:
    ll_path = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"
    assert ll_path.exists(), f"Lessons learned not found: {ll_path}"
    with open(ll_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_lesson_c22d_001_small_sample_protocol(replication_audit: dict):
    """LL-C22D-001: Assert small-sample robustness framing without mandatory p < 0.05 gate."""
    protocol = replication_audit["predeclared_protocol"]
    assert protocol["confirmatory_hypothesis_testing"] is False
    assert protocol["p_value_threshold_mandatory"] is False
    assert protocol["study_type"] == "Small-sample robustness and effect-consistency study"

    summary = replication_audit["results"]["all_five_pairs_summary"]
    limitation = summary["statistical_limitation_statement"]
    assert "small (n=5)" in limitation
    assert "No confirmatory hypothesis claim" in limitation


def test_lesson_c22d_002_single_seed_insufficient(replication_audit: dict, replication_aggregate: dict):
    """LL-C22D-002: Assert Case B classification due to mixed multi-seed outcomes."""
    assert replication_audit["scientific_classification"] == "CASE_B_SEED_SENSITIVE_UNJUSTIFIED_FOR_CANONICAL_ADOPTION"
    assert replication_audit["scientific_interpretation"]["case"] == "CASE_B"

    # Prospective replications were evenly split: 2 wins, 2 losses
    prospective = replication_audit["results"]["prospective_replications_summary"]
    assert prospective["n_prospective_seeds"] == 4
    assert prospective["treatment_wins"] == 2
    assert prospective["control_wins"] == 2
    assert prospective["ties"] == 0
    assert prospective["delta_mean"] < 0.0  # Actually slightly favors control (-0.00288)


def test_lesson_c22d_003_prospective_distinction(replication_audit: dict):
    """LL-C22D-003: Assert historical discovery seed 42 is kept distinct from prospective replications."""
    results = replication_audit["results"]
    assert "seed_42_historical_discovery" in results
    assert "prospective_replications" in results

    seed_42 = results["seed_42_historical_discovery"]
    assert seed_42["seed"] == 42
    assert seed_42["seed_type"] == "HISTORICAL_DISCOVERY_OBSERVATION"

    prospective_seeds = [s["seed"] for s in results["prospective_replications"]]
    assert prospective_seeds == [101, 202, 303, 404]
    for p in results["prospective_replications"]:
        assert p["seed_type"] == "PROSPECTIVE_REPLICATION"
        assert p["initial_state_bitwise_equal"] is True


def test_lesson_c22d_004_predeclared_criteria(replication_audit: dict, replication_aggregate: dict):
    """LL-C22D-004: Assert all metrics match predeclared criteria and exact machine values."""
    agg = replication_aggregate["aggregate_statistics"]
    assert agg["n_pairs"] == 5
    assert agg["treatment_wins"] == 3
    assert agg["control_wins"] == 2
    assert agg["ties"] == 0
    assert agg["proportion_treatment_superior"] == 0.6

    # Verify exact numerical reconciliation
    assert agg["control_mean_dev_mIoU"] == 0.04904
    assert agg["control_std_dev_mIoU"] == 0.00693
    assert agg["treatment_mean_dev_mIoU"] == 0.04909
    assert agg["treatment_std_dev_mIoU"] == 0.00421
    assert agg["delta_mean"] == 0.00004
    assert agg["delta_std"] == 0.01006
    assert agg["delta_median"] == 0.00383
    assert agg["delta_min"] == -0.01405
    assert agg["delta_max"] == 0.01171


def test_lesson_c22d_005_policy_preservation():
    """LL-C22D-005: Assert canonical training policy remains locked to C16 sqrt-median weights."""
    from ocean_sentinel.ml.exp07_fingerprint import CANONICAL_HISTORICAL_C16_LITERALS

    expected_canonical = [
        0.403935, 2.450546, 0.876692, 0.945945,
        0.648189, 4.211476, 0.719641, 2.956203,
        1.064525, 1.882870, 0.387652, 18.243211
    ]
    assert CANONICAL_HISTORICAL_C16_LITERALS == expected_canonical


def test_replication_manifest_integrity():
    """Assert all 37 downloaded replication artifacts match their SHA-256 hashes in the manifest."""
    base_dir = REPO_ROOT / "experiments" / "EXP-07" / "runs" / "EXP07_DIAG01_REPLICATION"
    manifest_path = base_dir / "exp07_diag01_replication_manifest.json"
    assert manifest_path.exists(), f"Manifest missing: {manifest_path}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert len(manifest) == 37
    for rel_path, expected_hash in manifest.items():
        file_path = base_dir / rel_path
        assert file_path.exists(), f"Missing replication artifact: {rel_path}"

        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        actual_hash = h.hexdigest().upper()
        assert actual_hash == expected_hash.upper(), f"Hash mismatch for {rel_path}: {actual_hash} != {expected_hash}"


def test_firewall_zero_access(replication_audit: dict):
    """Assert zero HOLDOUT and Part III payload access count throughout replication."""
    firewall = replication_audit["firewall_verification"]
    assert firewall["holdout_access_count"] == 0
    assert firewall["holdout_status"] == "QUARANTINED_ZERO_ACCESS"
    assert firewall["part_iii_access_count"] == 0
    assert firewall["part_iii_status"] == "FIREWALLED_ZERO_ACCESS"


def test_lessons_learned_registration(lessons_learned: dict):
    """Assert that LL-C22D-001 through LL-C22D-005 are registered and REGRESSION_PROTECTED."""
    lessons_by_id = {l["lesson_id"]: l for l in lessons_learned["lessons"]}
    for lid in ["LL-C22D-001", "LL-C22D-002", "LL-C22D-003", "LL-C22D-004", "LL-C22D-005"]:
        assert lid in lessons_by_id, f"Missing lesson {lid}"
        assert lessons_by_id[lid]["status"] == "REGRESSION_PROTECTED"
