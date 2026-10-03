"""Regression guardrails for EXP-07-P0-C22-F: C22-E Analytical Correction & Diagnostic-Roadmap Validation.

Asserts:
1. Rejection of invalid "mathematically capping" claims.
2. Rejection of uncalibrated "Stable Strength" class labeling.
3. Calibrated root-cause and representation language.
4. Input discriminability framed as testable hypothesis (no assumed bottleneck).
5. Immutable primary metric contract (dev_mIoU_phenomena over classes 1..11).
6. Registration of durable lessons LL-C22F-001 through LL-C22F-004.
7. Valid Level 5 machine-readable audit JSON schema and invariants.
8. Prioritized diagnostic roadmap consistency and zero-compute adherence.
9. Verified class support counts and zero-training/zero-GPU invariants.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = REPO_ROOT / "data" / "ops02" / "audits"
METADATA_DIR = REPO_ROOT / "data" / "metadata"
EXP07_DIR = REPO_ROOT / "experiments" / "EXP-07"


def test_01_no_mathematical_cap_claims_in_c22e_priorities_json():
    """Verify that the invalid 'mathematically capping' claim has been removed from C22-E priorities."""
    priorities_path = AUDIT_DIR / "ops02_c22e_next_diagnostic_priorities_v1.json"
    assert priorities_path.exists(), "C22-E priorities JSON must exist"
    content = priorities_path.read_text(encoding="utf-8")
    assert "mathematically capping" not in content.lower()
    assert "mathematically cap" not in content.lower()
    assert "capping aggregate miou" not in content.lower()


def test_02_no_mathematical_cap_claims_in_c22e_markdown_report():
    """Verify that the invalid 'mathematically capping' claim has been removed from C22-E markdown."""
    report_path = EXP07_DIR / "EXP07_P0_C22E_LOSS_WEIGHT_HYPOTHESIS_CLOSURE_20260914.md"
    assert report_path.exists(), "C22-E report must exist"
    content = report_path.read_text(encoding="utf-8")
    assert "mathematically capping" not in content.lower()
    assert "artificially capping score at ~0.05" not in content.lower()
    assert "cap macro miou at ~0.05" not in content.lower()


def test_03_stable_strength_terminology_eliminated():
    """Verify that 'Stable Strength' is not used as an uncalibrated performance label."""
    report_path = EXP07_DIR / "EXP07_P0_C22E_LOSS_WEIGHT_HYPOTHESIS_CLOSURE_20260914.md"
    content = report_path.read_text(encoding="utf-8")
    assert "stable strengths" not in content.lower()
    assert "stable strength" not in content.lower()


def test_04_no_unmeasured_representation_claims():
    """Verify that unmeasured representation learning claims are replaced with task performance claims."""
    report_path = EXP07_DIR / "EXP07_P0_C22E_LOSS_WEIGHT_HYPOTHESIS_CLOSURE_20260914.md"
    content = report_path.read_text(encoding="utf-8")
    assert "did not improve representation learning" not in content.lower()
    assert "did not improve model capacity or feature learning" not in content.lower()


def test_05_no_assumed_information_bottleneck_in_rank_3():
    """Verify that Rank 3 is framed as backscatter distribution overlap, not an assumed information bottleneck."""
    priorities_path = AUDIT_DIR / "ops02_c22e_next_diagnostic_priorities_v1.json"
    content = priorities_path.read_text(encoding="utf-8")
    data = json.loads(content)
    rank_3 = next(p for p in data["prioritized_investigations"] if p["rank"] == 3)
    assert "bottleneck" not in rank_3["title"].lower()
    assert "bottleneck" not in rank_3["investigation_id"].lower()


def test_06_durable_learning_lessons_registered():
    """Verify that LL-C22F-001 through LL-C22F-004 are registered in lessons learned."""
    lessons_path = METADATA_DIR / "ocean_sentinel_lessons_learned_v1.json"
    assert lessons_path.exists()
    lessons_data = json.loads(lessons_path.read_text(encoding="utf-8"))
    lesson_ids = {l["lesson_id"] for l in lessons_data["lessons"]}

    for expected_id in ["LL-C22F-001", "LL-C22F-002", "LL-C22F-003", "LL-C22F-004"]:
        assert expected_id in lesson_ids, f"Lesson {expected_id} must be registered"
        lesson = next(l for l in lessons_data["lessons"] if l["lesson_id"] == expected_id)
        assert lesson["status"] == "REGRESSION_PROTECTED"
        assert lesson["category"] == "SCIENTIFIC_VALIDITY"


def test_07_c22f_audit_json_schema_and_invariants():
    """Verify C22-F Level 5 machine-readable audit JSON schema and compliance."""
    c22f_audit_path = AUDIT_DIR / "ops02_c22f_diagnostic_roadmap_validation_v1.json"
    assert c22f_audit_path.exists(), "C22-F audit JSON must exist"
    audit = json.loads(c22f_audit_path.read_text(encoding="utf-8"))

    assert audit["task_id"] == "EXP-07-P0-C22-F"
    assert audit["status"] == "COMPLETED_VALID"
    assert audit["terminal_status"] == "C22E_ANALYTICAL_CORRECTION = COMPLETED_VALID"
    assert "EXECUTE ONLY THE HIGHEST-RANKED ZERO-COMPUTE DIAGNOSTIC" in audit["next_authorized_stage"]

    compliance = audit["execution_constraints_compliance"]
    assert compliance["training_step_count"] == 0
    assert compliance["gpu_seconds"] == 0.0
    assert compliance["holdout_access_count"] == 0
    assert compliance["part_iii_access_count"] == 0
    assert compliance["primary_metric_altered"] is False


def test_08_diagnostic_roadmap_order_and_zero_compute():
    """Verify that Rank 1 is metric sensitivity, Rank 2 is sampler, Rank 3 is radiometric, all zero-GPU."""
    c22f_audit_path = AUDIT_DIR / "ops02_c22f_diagnostic_roadmap_validation_v1.json"
    audit = json.loads(c22f_audit_path.read_text(encoding="utf-8"))
    roadmap = audit["validated_prioritized_diagnostic_roadmap"]

    assert len(roadmap) == 3
    assert roadmap[0]["rank"] == 1
    assert roadmap[0]["investigation_id"] == "DIAG-01-CLASS-SUPPORT-METRIC-SENSITIVITY"
    assert roadmap[0]["done_without_training"] is True
    assert roadmap[0]["compute_cost"] == "ZERO_GPU_COMPUTE"

    assert roadmap[1]["rank"] == 2
    assert roadmap[1]["investigation_id"] == "DIAG-02-SAMPLER-EXPOSURE-SCHEDULE-AUDIT"
    assert roadmap[1]["done_without_training"] is True
    assert roadmap[1]["compute_cost"] == "ZERO_GPU_COMPUTE"

    assert roadmap[2]["rank"] == 3
    assert roadmap[2]["investigation_id"] == "DIAG-03-RADIOMETRIC-INPUT-DISCRIMINABILITY"
    assert roadmap[2]["done_without_training"] is True


def test_09_primary_metric_contract_frozen():
    """Verify that the primary metric contract dev_mIoU_phenomena (classes 1..11) is confirmed frozen."""
    c22f_audit_path = AUDIT_DIR / "ops02_c22f_diagnostic_roadmap_validation_v1.json"
    audit = json.loads(c22f_audit_path.read_text(encoding="utf-8"))
    contract = audit["primary_metric_contract_confirmation"]

    assert contract["metric_name"] == "dev_mIoU_phenomena"
    assert contract["classes_evaluated"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    assert contract["background_class_0_excluded"] is True
    assert "FROZEN" in contract["status"]


def test_10_dev_class_support_counts_exact():
    """Verify the exact DEV class presence counts (MCC=17, IWs=31, RF=2, HM=3, OF=1, all others 0)."""
    c22f_audit_path = AUDIT_DIR / "ops02_c22f_diagnostic_roadmap_validation_v1.json"
    audit = json.loads(c22f_audit_path.read_text(encoding="utf-8"))
    evidence = {item["class_name"]: item["dev_sample_count"] for item in audit["verified_five_seed_class_support_evidence"]}

    assert evidence["MCC"] == 17
    assert evidence["IWs"] == 31
    assert evidence["RF"] == 2
    assert evidence["HM"] == 3
    assert evidence["OF"] == 1
    assert evidence["AF"] == 0
    assert evidence["BS"] == 0
    assert evidence["LWA"] == 0
    assert evidence["POW"] == 0
    assert evidence["WS"] == 0
    assert evidence["Eddy"] == 0


def test_lesson_c22f_001_no_mathematical_cap_claims():
    """Alias for LL-C22F-001 regression test."""
    test_01_no_mathematical_cap_claims_in_c22e_priorities_json()
    test_02_no_mathematical_cap_claims_in_c22e_markdown_report()


def test_lesson_c22f_002_separate_performance_and_stability():
    """Alias for LL-C22F-002 regression test."""
    test_03_stable_strength_terminology_eliminated()


def test_lesson_c22f_003_no_unmeasured_representation_claims():
    """Alias for LL-C22F-003 regression test."""
    test_04_no_unmeasured_representation_claims()


def test_lesson_c22f_004_input_limitation_measured_not_assumed():
    """Alias for LL-C22F-004 regression test."""
    test_05_no_assumed_information_bottleneck_in_rank_3()
