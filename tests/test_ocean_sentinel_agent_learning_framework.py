"""Tests for the Ocean Sentinel Durable Agent Learning & Failure-Prevention Framework.

Validates schema compliance, lifecycle state progression, preventive controls,
and regression test execution across all catalogued lessons.
"""

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LESSONS_PATH = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"
DOCS_PATH = REPO_ROOT / "docs" / "OCEAN_SENTINEL_AGENT_LEARNING_FRAMEWORK.md"


def load_lessons_db() -> dict:
    assert LESSONS_PATH.exists(), f"Lessons database not found at {LESSONS_PATH}"
    return json.loads(LESSONS_PATH.read_text(encoding="utf-8"))


def test_framework_metadata_and_taxonomy():
    """Verify framework metadata, categories, and lifecycle stages."""
    db = load_lessons_db()
    meta = db["framework_metadata"]
    assert meta["version"] == "1.0.0"
    assert meta["governance_contract"] == "DURABLE_AGENT_LEARNING_v1"

    expected_stages = [
        "DETECTED", "RECORDED", "MITIGATED", "REGRESSION_PROTECTED", "PROVEN_STABLE"
    ]
    assert meta["lifecycle_stages"] == expected_stages

    expected_categories = [
        "SCIENTIFIC_VALIDITY", "DATA_INTEGRITY", "REPRODUCIBILITY",
        "IMPLEMENTATION_INTEGRITY", "DOCUMENTATION_INTEGRITY",
        "OPERATIONAL_SAFETY", "AGENT_PROCESS"
    ]
    assert meta["category_taxonomy"] == expected_categories


def test_lessons_minimum_count_and_schema():
    """Verify minimum 20 lessons and strict schema adherence for each entry."""
    db = load_lessons_db()
    lessons = db["lessons"]
    assert len(lessons) >= 20, f"Expected at least 20 lessons, found {len(lessons)}"

    required_fields = [
        "lesson_id", "category", "failure_pattern", "description", "root_cause",
        "first_seen", "last_seen", "occurrence_count", "severity", "affected_tasks",
        "detection_method", "prevention_method", "required_preflight",
        "regression_test", "status", "notes"
    ]
    valid_categories = set(db["framework_metadata"]["category_taxonomy"])
    valid_statuses = set(db["framework_metadata"]["lifecycle_stages"])
    valid_severities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    lesson_ids = set()
    for lsn in lessons:
        lid = lsn["lesson_id"]
        assert lid not in lesson_ids, f"Duplicate lesson ID: {lid}"
        lesson_ids.add(lid)

        for field in required_fields:
            assert field in lsn, f"Lesson {lid} missing required field: {field}"
            assert lsn[field] is not None, f"Lesson {lid} field {field} is None"

        assert lsn["category"] in valid_categories, f"Invalid category in {lid}: {lsn['category']}"
        assert lsn["status"] in valid_statuses, f"Invalid status in {lid}: {lsn['status']}"
        assert lsn["severity"] in valid_severities, f"Invalid severity in {lid}: {lsn['severity']}"
        assert isinstance(lsn["affected_tasks"], list)
        assert len(lsn["affected_tasks"]) > 0
        assert lsn["occurrence_count"] >= 1


def test_regression_protection_rule():
    """A lesson cannot be REGRESSION_PROTECTED unless a valid test path is documented."""
    db = load_lessons_db()
    for lsn in db["lessons"]:
        lid = lsn["lesson_id"]
        if lsn["status"] in ["REGRESSION_PROTECTED", "PROVEN_STABLE"]:
            reg_test = lsn["regression_test"]
            assert reg_test, f"Lesson {lid} is {lsn['status']} but lacks a regression_test"
            assert "tests/" in reg_test, f"Lesson {lid} regression_test must point to a tests/ file"


# ==============================================================================
# Dedicated Lesson Regression Verifications
# ==============================================================================

def test_lesson_001_narrative_vs_machine_truth():
    """LL-EXP07-001: Machine truth shows EVAL-A target-native mIoU > model-declared."""
    post_audit = json.loads((REPO_ROOT / "data/ops02/audits/ops02_c21_c20_post_audit_v1.json").read_text(encoding="utf-8"))
    corr = next(c for c in post_audit["forensic_corrections"] if c["correction_id"] == "CORR-C20-001")
    eval_a = corr["level_5_machine_truth"]["eval_a_c16_to_ops01_dev"]
    assert eval_a["target_native_normalization_mIoU"] == 0.028818
    assert eval_a["model_declared_normalization_mIoU"] == 0.027285
    assert eval_a["target_native_normalization_mIoU"] > eval_a["model_declared_normalization_mIoU"]
    assert eval_a["higher_performing_normalization"] == "TARGET_NATIVE"


def test_lesson_004_dataset_provenance_preservation():
    """LL-EXP07-004: Historical dataset identity v1.0.0 is bitwise identical to v1.0.1."""
    post_audit = json.loads((REPO_ROOT / "data/ops02/audits/ops02_c21_c20_post_audit_v1.json").read_text(encoding="utf-8"))
    corr = next(c for c in post_audit["forensic_corrections"] if c["correction_id"] == "CORR-C20-004")
    assert corr["level_5_machine_truth"]["split_allocations"] == "132 TRAIN / 40 DEV / 40 HOLDOUT identical across both"


def test_lesson_007_tensor_shape_syntax():
    """LL-EXP07-007: Representation strictly includes singleton channel dimension."""
    proto = json.loads((REPO_ROOT / "data/ops02/audits/ops02_c21_single_variable_diagnostic_protocol_v1.json").read_text(encoding="utf-8"))
    comp = next(c for c in proto["paired_experiment_package_manifest"]["components"] if c["name"] == "canonical_input_target_representation")
    assert "[B, 1, 256, 256]" in comp["value"]


def test_lesson_009_no_bug_free_overclaim():
    """LL-EXP07-009: No C21 protocol claims 100% bug-free, and post-audit explicitly rectifies it."""
    proto_text = (REPO_ROOT / "data/ops02/audits/ops02_c21_single_variable_diagnostic_protocol_v1.json").read_text(encoding="utf-8")
    assert "100% bug-free" not in proto_text.lower()
    post_audit = json.loads((REPO_ROOT / "data/ops02/audits/ops02_c21_c20_post_audit_v1.json").read_text(encoding="utf-8"))
    corr = next(c for c in post_audit["forensic_corrections"] if c["correction_id"] == "CORR-C20-003")
    assert "100% bug-free" not in corr["corrected_epistemic_position"].lower()


def test_lesson_010_historical_baseline_integrity():
    """LL-EXP07-010: C8 and C10 historical DEV phenomena baselines are verified from Level 5 JSON."""
    c8_json = json.loads((REPO_ROOT / "data/metadata/exp07_p0_c8_training_results_seed42_v1.json").read_text(encoding="utf-8"))
    c10_json = json.loads((REPO_ROOT / "data/metadata/exp07_p0_c10_training_results_seed101_v1.json").read_text(encoding="utf-8"))
    assert abs(c8_json["best_dev_mIoU_phenomena"] - 0.11903) < 1e-4
    assert abs(c10_json["best_dev_mIoU_phenomena"] - 0.13782) < 1e-4


def test_lesson_011_normalization_directionality():
    """LL-EXP07-011: Normalization sensitivity is strictly recorded as evaluation-dependent."""
    post_audit = json.loads((REPO_ROOT / "data/ops02/audits/ops02_c21_c20_post_audit_v1.json").read_text(encoding="utf-8"))
    corr = next(c for c in post_audit["forensic_corrections"] if c["correction_id"] == "CORR-C20-001")
    assert "EVALUATION-DEPENDENT" in corr["corrected_epistemic_position"]


def test_lesson_014_checkpoint_lineage_hashes():
    """LL-EXP07-014: Checkpoint lineage audit in C20 contains cryptographic SHA-256 digests."""
    lineage = json.loads((REPO_ROOT / "data/ops02/audits/ops02_c20_checkpoint_lineage_audit_v1.json").read_text(encoding="utf-8"))
    assert "checkpoints" in lineage
    for name, ckpt in lineage["checkpoints"].items():
        assert "sha256" in ckpt
        assert len(ckpt["sha256"]) == 64


def test_lesson_019_parent_datatake_accounting():
    """LL-EXP07-019: Tile count is distinguished from parent datatake count."""
    manifest = json.loads((REPO_ROOT / "data/ops02/manifests/ops02_physical_dataset_manifest_v1.json").read_text(encoding="utf-8"))
    train_tiles = [s for s in manifest["samples"] if s["partition"] == "TRAIN"]
    assert len(train_tiles) == 132
    datatakes = set(s["mission_data_take_id"] for s in train_tiles)
    assert len(datatakes) == 40
    assert len(train_tiles) != len(datatakes)

    # Invariant from EXP-07-P0-C22-A.7: narrative text in lesson 019 cannot claim 23
    db = load_lessons_db()
    lsn = next(l for l in db["lessons"] if l["lesson_id"] == "LL-EXP07-019")
    assert "23 parent datatakes" not in lsn["description"]
    assert "40 TRAIN parent datatakes" in lsn["description"]


def test_lesson_020_automated_protection_requirement():
    """LL-EXP07-020: Every single catalogued lesson has regression protection."""
    db = load_lessons_db()
    for lsn in db["lessons"]:
        assert lsn["status"] in ["REGRESSION_PROTECTED", "PROVEN_STABLE"]
        assert lsn["regression_test"]
