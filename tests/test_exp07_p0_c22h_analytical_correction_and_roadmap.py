"""Regression and guardrail tests for EXP-07-P0-C22-H.

Ensures:
1. LL-C22H-001, LL-C22H-002, LL-C22H-003 lessons registered and valid.
2. C22G audit JSON has verdict CASE_B_SUPPORT_SENSITIVE_BUT_VALID_FROZEN_METRIC and classification CASE B.
3. C22G report markdown framing is calibrated to CASE B with erratum/reclassification section.
4. C22H audit JSON exists with zero training/GPU/holdout access and restored DIAG-02 sampler audit identity.
5. Authoritative diagnostic roadmap preserves DIAG-02 as sampler audit and distinguishes receptive field as DIAG-04.
"""

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_lessons_learned_c22h_registered():
    """Verify lessons LL-C22H-001, LL-C22H-002, LL-C22H-003 exist and are well-formed."""
    lessons_path = REPO_ROOT / "data/metadata/ocean_sentinel_lessons_learned_v1.json"
    assert lessons_path.exists(), f"Lessons file missing: {lessons_path}"

    with open(lessons_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lessons = {l["lesson_id"]: l for l in data["lessons"]}
    required_ids = ["LL-C22H-001", "LL-C22H-002", "LL-C22H-003"]

    for lid in required_ids:
        assert lid in lessons, f"Lesson {lid} not found in lessons learned repository"
        l = lessons[lid]
        assert l["status"] in ["active", "REGRESSION_PROTECTED"]
        assert len(l["failure_pattern"]) > 10
        assert len(l["description"]) > 15
        assert len(l["root_cause"]) > 15
        assert len(l["prevention_method"]) > 15
        assert len(l["regression_test"]) > 5
        assert "EXP-07-P0-C22-H" in l["affected_tasks"]


def test_c22g_audit_verdict_reclassified_to_case_b():
    """Verify C22G audit JSON is reclassified to CASE B with calibrated framing."""
    audit_path = REPO_ROOT / "data/ops02/audits/ops02_c22g_class_support_metric_sensitivity_v1.json"
    assert audit_path.exists(), f"Audit file missing: {audit_path}"

    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    findings = audit["core_scientific_findings"]
    assert findings["verdict"] == "CASE_B_SUPPORT_SENSITIVE_BUT_VALID_FROZEN_METRIC"
    assert "support sensitivity" in findings["summary"].lower()

    decision = audit["decision_logic"]
    assert decision["classification"] == "CASE B"
    assert "DIAG-02-SAMPLER-EXPOSURE-SCHEDULE-AUDIT" in decision["recommended_next_step"]
    assert "reclassification_history" in decision
    assert decision["reclassification_history"]["original_classification"] == "CASE C"


def test_c22g_report_framing_and_reclassification_section():
    """Verify C22G report markdown has calibrated CASE B framing and Section 14 erratum."""
    report_path = REPO_ROOT / "experiments/EXP-07/EXP07_P0_C22G_CLASS_SUPPORT_METRIC_SENSITIVITY_20260914.md"
    assert report_path.exists(), f"Report file missing: {report_path}"

    content = report_path.read_text(encoding="utf-8")

    # CASE B verdict must be present
    assert "CASE B — SUPPORT-SENSITIVE BUT VALID FROZEN METRIC" in content
    # Section 14 Erratum must exist
    assert "## 14. Erratum & Reclassification History (C22-H Corrective Review)" in content
    # Section 12 must recommend DIAG-02-SAMPLER-EXPOSURE-SCHEDULE-AUDIT
    assert "DIAG-02-SAMPLER-EXPOSURE-SCHEDULE-AUDIT" in content
    # Pejorative/distorted framing must be removed from verdict
    assert "egregious distortion of reality" not in content


def test_c22h_audit_artifact_governance_and_roadmap():
    """Verify C22H Level 5 audit artifact adheres to governance and restores roadmap."""
    audit_path = REPO_ROOT / "data/ops02/audits/ops02_c22h_analytical_correction_and_roadmap_alignment_v1.json"
    assert audit_path.exists(), f"Audit file missing: {audit_path}"

    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    assert audit["task_id"] == "EXP-07-P0-C22-H"
    assert audit["status"] == "COMPLETED_VALID"

    # Governance checks: zero compute/training/holdout
    gov = audit["governance_guarantees"]
    assert gov["training_steps"] == 0
    assert gov["backward_passes"] == 0
    assert gov["optimizer_steps"] == 0
    assert gov["scheduler_steps"] == 0
    assert gov["gpu_training_compute_seconds"] == 0.0
    assert gov["holdout_payload_access_count"] == 0
    assert gov["part_iii_benchmark_access_count"] == 0
    assert gov["analytical_compute_mode"] == "CPU_ONLY"

    # Roadmap integrity
    roadmap = {item["rank"]: item for item in audit["authoritative_diagnostic_roadmap"]}
    assert roadmap[1]["investigation_id"] == "DIAG-01-CLASS-SUPPORT-METRIC-SENSITIVITY"
    assert roadmap[1]["classification"] == "CASE B"
    assert roadmap[2]["investigation_id"] == "DIAG-02-SAMPLER-EXPOSURE-SCHEDULE-AUDIT"
    assert roadmap[2]["status"] == "NEXT_PENDING_USER_AUTHORIZATION"
    assert roadmap[3]["investigation_id"] == "DIAG-03-RADIOMETRIC-FEATURE-DISCRIMINABILITY"
    assert roadmap[4]["investigation_id"] == "DIAG-04-RECEPTIVE-FIELD-SCALE-COMPATIBILITY"
