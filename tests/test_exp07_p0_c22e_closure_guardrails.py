"""EXP-07-P0-C22-E: Loss-Weight Hypothesis Closure & Failure Diagnosis Guardrails.

Verifies:
1. Formal closure of loss-weight intervention as 'not supported as a robust replacement'.
2. Canonical C16 sqrt-median class weighting policy retained without modification.
3. Accurate boundary delineation (questions answered vs questions not answered).
4. Absence of unmeasured mechanistic speculation in repaired C22-D report.
5. Prioritization of failure diagnosis before any new ML intervention.
6. Maximum 3 candidate investigations, all adhering to zero-compute / diagnostic criteria.
7. Strict zero HOLDOUT and Part III payload access.
8. Durable lessons LL-C22E-001 through LL-C22E-005 registered and REGRESSION_PROTECTED.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def closure_audit() -> dict:
    p = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22e_loss_weight_hypothesis_closure_v1.json"
    assert p.exists(), f"Closure audit missing: {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def diagnostic_priorities() -> dict:
    p = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22e_next_diagnostic_priorities_v1.json"
    assert p.exists(), f"Diagnostic priorities missing: {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def lessons_learned() -> dict:
    p = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"
    assert p.exists(), f"Lessons learned missing: {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def test_lesson_c22e_001_replication_validity(closure_audit: dict):
    """LL-C22E-001: Assert that Case B replication outcome is classified as COMPLETED_VALID."""
    assert closure_audit["status"] == "COMPLETED_VALID"
    assert "NOT_SUPPORTED_AS_A_ROBUST_ADVANTAGE" in closure_audit["tested_hypothesis"]["status"]
    assert closure_audit["scientific_status"] == "LOSS_WEIGHT_INTERVENTION = CLOSED_NOT_SUPPORTED_FOR_CANONICAL_REPLACEMENT"


def test_lesson_c22e_002_robustness_not_forced_significance(closure_audit: dict):
    """LL-C22E-002: Assert small-sample robustness framing without mathematical overclaiming."""
    qual = closure_audit["canonical_policy_verdict"]["scientific_qualification"]
    assert "null is not mathematically proven" in qual
    assert "equivalence is not claimed" in qual
    assert "not claimed to be harmful in general" in qual
    assert "fails to demonstrate a robust development advantage" in qual


def test_lesson_c22e_003_boundary_delineation(closure_audit: dict):
    """LL-C22E-003: Assert exact delineation of answered vs unanswered questions."""
    hyp = closure_audit["tested_hypothesis"]
    assert hyp["question_answered"] == "Does uniform weighting demonstrate a stable DEV advantage over the canonical weighting policy under this frozen OPS-02 setup?"
    assert hyp["answer"] == "NO"

    unanswered = hyp["questions_not_answered"]
    assert len(unanswered) >= 7
    assert any("architecture" in q for q in unanswered)
    assert any("representation" in q for q in unanswered)
    assert any("dataset size" in q or "diversity" in q for q in unanswered)
    assert any("HOLDOUT" in q for q in unanswered)


def test_lesson_c22e_004_no_mechanistic_speculation():
    """LL-C22E-004: Assert absence of unmeasured mechanistic speculation in C22-D report."""
    report_path = REPO_ROOT / "experiments" / "EXP-07" / "EXP07_P0_C22D_MULTISEED_REPLICATION_20260914.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")

    forbidden_phrases = [
        "Treatment rapidly fits dominant features early",
        "plateau/overfitting",
        "regularized by the class-weight vector",
        "sustained exploration",
        "Early Convergence & Overfitting",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in content, f"Forbidden speculative phrase found in C22-D report: '{phrase}'"

    # Confirm required evidence-calibrated wording is present
    required_calibrated_wording = "Across the replicated runs, the unweighted treatment often reached its best DEV checkpoint earlier, but this observation alone does not establish a mechanism of faster convergence, overfitting, or feature dominance."
    assert required_calibrated_wording in content, "Missing required evidence-calibrated wording in C22-D report."


def test_lesson_c22e_005_diagnose_before_intervene(diagnostic_priorities: dict):
    """LL-C22E-005: Assert that next investigations are ranked failure diagnoses requiring zero GPU training."""
    assert diagnostic_priorities["selection_criterion"] == "MAXIMUM_INFORMATION_GAIN_PER_UNIT_OF_COMPUTE"
    investigations = diagnostic_priorities["prioritized_investigations"]
    assert len(investigations) <= 3
    assert len(investigations) >= 1

    for inv in investigations:
        assert inv["holdout_necessary"] is False
        assert "ZERO GPU compute" in inv["compute_cost"] or "Negligible CPU" in inv["compute_cost"]
        assert len(inv["target_failure"]) > 10
        assert len(inv["existing_evidence"]) >= 1

    prohibited = diagnostic_priorities["prohibited_actions"]
    assert any("Do NOT launch new GPU training" in p for p in prohibited)
    assert any("Do NOT access HOLDOUT" in p for p in prohibited)


def test_canonical_policy_retention(closure_audit: dict):
    """Assert canonical C16 sqrt-median-frequency weighting policy is retained and uniform weighting rejected."""
    verdict = closure_audit["canonical_policy_verdict"]
    assert verdict["action"] == "RETAIN_CANONICAL_POLICY"
    assert verdict["uniform_weighting_action"] == "DO_NOT_ADOPT"
    assert verdict["further_loss_weight_replications_recommended"] is False

    from ocean_sentinel.ml.exp07_fingerprint import CANONICAL_HISTORICAL_C16_LITERALS
    assert verdict["canonical_weighting_vector"] == CANONICAL_HISTORICAL_C16_LITERALS


def test_firewall_zero_access(closure_audit: dict):
    """Assert strict zero HOLDOUT and Part III payload access throughout C22-E."""
    fw = closure_audit["firewall_compliance"]
    assert fw["holdout_access_count"] == 0
    assert fw["holdout_status"] == "QUARANTINED_ZERO_ACCESS"
    assert fw["part_iii_access_count"] == 0
    assert fw["part_iii_status"] == "FIREWALLED_ZERO_ACCESS"


def test_lessons_learned_registration(lessons_learned: dict):
    """Assert that LL-C22E-001 through LL-C22E-005 are registered and REGRESSION_PROTECTED."""
    lessons_by_id = {l["lesson_id"]: l for l in lessons_learned["lessons"]}
    for lid in ["LL-C22E-001", "LL-C22E-002", "LL-C22E-003", "LL-C22E-004", "LL-C22E-005"]:
        assert lid in lessons_by_id, f"Missing lesson {lid}"
        assert lessons_by_id[lid]["status"] == "REGRESSION_PROTECTED"
