"""Unit and Integration Tests for Ocean Sentinel Lesson Architecture v2."""

import json
from pathlib import Path
import pytest

from ocean_sentinel.governance.applicability import ApplicabilityEngine
from ocean_sentinel.governance.interface import evaluate_task_preflight
from ocean_sentinel.governance.lifecycle import LifecycleManager
from ocean_sentinel.governance.models import (
    ActionType,
    AssumptionState,
    EvidenceStrength,
    LearningState,
    Lesson,
    NoveltyFlag,
    Rule,
    RuleChangeClass,
    ScopeLevel,
    SeverityLevel,
    TaskContext,
    ValidationRecord,
)
from ocean_sentinel.governance.novelty import NoveltyDetector
from ocean_sentinel.governance.precedence import PrecedenceEngine
from ocean_sentinel.governance.retrieval import HybridRetrievalEngine
from ocean_sentinel.governance.store import GovernanceStore

REPO_ROOT = Path(__file__).resolve().parent.parent
V2_DIR = REPO_ROOT / "data" / "metadata" / "governance_v2"


@pytest.fixture(scope="module")
def store():
    return GovernanceStore.get_instance(force_reload=True)


# ==============================================================================
# 1. Schema & Entity Reference Integrity
# ==============================================================================
def test_v2_schema_and_entity_integrity(store):
    """Asserts that all normalized v2 entities exist, have non-empty required fields, and valid references."""
    assert len(store.principles) >= 12, "Principles missing"
    assert len(store.failure_classes) >= 27, "Failure classes incomplete"
    assert len(store.rules) >= 120, "Rules catalog incomplete"
    assert len(store.lessons) == 104, "Lesson count mismatch (expected 104 lessons from v1)"
    assert len(store.assumptions) >= 12, "Assumptions registry incomplete"
    assert len(store.incidents) >= 37, "Incidents registry incomplete"

    # Check rule references
    for rid, rule in store.rules.items():
        assert rule.principle_id in store.principles, f"Rule {rid} references unknown principle {rule.principle_id}"
        assert rule.failure_class in store.failure_classes, f"Rule {rid} references unknown failure class {rule.failure_class}"
        assert rule.statement, f"Rule {rid} has empty statement"

    # Check lesson references
    for lid, lesson in store.lessons.items():
        assert lesson.title, f"Lesson {lid} has empty title"
        assert lesson.principle_id in store.principles, f"Lesson {lid} references unknown principle {lesson.principle_id}"
        assert lesson.failure_class in store.failure_classes, f"Lesson {lid} references unknown failure class {lesson.failure_class}"


# ==============================================================================
# 2. Applicability Engine Logic
# ==============================================================================
def test_applicability_engine_filtering(store):
    """Asserts that structured condition evaluation correctly selects relevant rules and rejects irrelevant ones."""
    engine = ApplicabilityEngine()

    rule_census = store.get_rule("GOV-RULE-129")
    assert rule_census is not None

    # Context with matching operation
    matching_ctx = TaskContext(
        task_id="T1",
        operation=["sample_eligibility_census"],
        diagnostic="DIAG-05"
    )
    is_app, reasons = engine.evaluate_rule(rule_census, matching_ctx)
    assert is_app, "Rule 129 should apply to sample_eligibility_census operation"
    assert any("operation" in r.lower() for r in reasons)

    # Context without matching operation
    non_matching_ctx = TaskContext(
        task_id="T2",
        operation=["report_generation"],
        diagnostic="DIAG-01"
    )
    is_app_2, _ = engine.evaluate_rule(rule_census, non_matching_ctx)
    assert not is_app_2, "Rule 129 should not apply to report_generation on DIAG-01"


# ==============================================================================
# 3. Precedence & Conflict Resolution
# ==============================================================================
def test_precedence_severity_over_specificity(store):
    """Asserts that a critical global rule cannot be overridden by a lower-severity task rule."""
    engine = PrecedenceEngine()

    global_critical = Rule(
        rule_id="RULE-GLOBAL-CRITICAL",
        principle_id="PRIN-007",
        failure_class="DATA-INTEGRITY",
        title="Global Critical Prohibition",
        statement="Prohibit holdout access globally.",
        scope=ScopeLevel.GLOBAL,
        severity=SeverityLevel.CRITICAL,
        action=ActionType.BLOCK,
        non_overridable=True
    )
    task_low = Rule(
        rule_id="RULE-TASK-LOW",
        principle_id="PRIN-007",
        failure_class="DATA-INTEGRITY",
        title="Task Specific Allowance",
        statement="Allow holdout scan.",
        scope=ScopeLevel.TASK,
        severity=SeverityLevel.LOW,
        action=ActionType.WARN,
        prohibited_actions=["holdout"]
    )

    p_crit = engine.calculate_effective_priority(global_critical)
    p_low = engine.calculate_effective_priority(task_low)
    assert p_crit > p_low, "Global critical non-overridable rule must have higher priority than task rule"


def test_precedence_conflict_detection():
    """Asserts that identical-priority opposing directives emit an explicit blocking conflict."""
    engine = PrecedenceEngine()

    rule_a = Rule(
        rule_id="RULE-A",
        principle_id="PRIN-001",
        failure_class="DATA-INTEGRITY",
        title="Directive A",
        statement="Block resource X.",
        scope=ScopeLevel.PROJECT,
        severity=SeverityLevel.HIGH,
        action=ActionType.BLOCK,
        prohibited_actions=["resource_x"]
    )
    rule_b = Rule(
        rule_id="RULE-B",
        principle_id="PRIN-001",
        failure_class="DATA-INTEGRITY",
        title="Directive B",
        statement="Warn resource X.",
        scope=ScopeLevel.PROJECT,
        severity=SeverityLevel.HIGH,
        action=ActionType.WARN,
        prohibited_actions=["resource_x"]
    )

    active, conflicts, blockers = engine.resolve_rules([rule_a, rule_b])
    assert len(conflicts) > 0, "Conflict should be detected between opposing directives"
    assert any(c.resolution_status == "UNRESOLVED_CONFLICT" for c in conflicts)
    assert len(blockers) > 0, "Unresolved conflict must emit a critical preflight blocker"


def test_precedence_explicit_supersession():
    """Asserts that explicit supersession declaration retires the older rule."""
    engine = PrecedenceEngine()

    rule_old = Rule(
        rule_id="RULE-OLD",
        principle_id="PRIN-001",
        failure_class="DATA-INTEGRITY",
        title="Old Rule",
        statement="Old guideline.",
        scope=ScopeLevel.PROJECT,
        severity=SeverityLevel.HIGH,
        action=ActionType.BLOCK,
        status=LearningState.SUPERSEDED
    )
    rule_new = Rule(
        rule_id="RULE-NEW",
        principle_id="PRIN-001",
        failure_class="DATA-INTEGRITY",
        title="New Rule",
        statement="New guideline.",
        scope=ScopeLevel.PROJECT,
        severity=SeverityLevel.HIGH,
        action=ActionType.BLOCK,
        supersedes=["RULE-OLD"]
    )

    active, conflicts, blockers = engine.resolve_rules([rule_old, rule_new])
    active_ids = [r.rule_id for r in active]
    assert "RULE-NEW" in active_ids
    assert "RULE-OLD" not in active_ids, "RULE-OLD should be retired by explicit supersession"
    assert any(c.resolution_status == "RESOLVED_BY_SUPERSESSION" for c in conflicts)


# ==============================================================================
# 4. Lifecycle & Evidence-Based Promotion
# ==============================================================================
def test_lifecycle_transitions():
    """Asserts valid and invalid state transitions."""
    # 1. RECORDED -> PROVEN_STABLE directly is illegal
    ok, msg = LifecycleManager.can_transition(LearningState.RECORDED, LearningState.PROVEN_STABLE)
    assert not ok
    assert "strictly prohibited" in msg

    # 2. RECORDED -> REGRESSION_PROTECTED requires automated test
    ok, _ = LifecycleManager.can_transition(LearningState.RECORDED, LearningState.REGRESSION_PROTECTED, has_automated_test=False)
    assert not ok
    ok, _ = LifecycleManager.can_transition(LearningState.RECORDED, LearningState.REGRESSION_PROTECTED, has_automated_test=True)
    assert ok

    # 3. REGRESSION_PROTECTED -> PROVEN_STABLE requires >= 2 independent task validation records
    records_1 = [ValidationRecord(task="TASK-1", timestamp="2026-09-15", test="t1", result="PASSED")]
    ok, msg = LifecycleManager.can_transition(
        LearningState.REGRESSION_PROTECTED, LearningState.PROVEN_STABLE, has_automated_test=True, validation_records=records_1
    )
    assert not ok
    assert "at least 2 independent tasks" in msg

    records_2 = [
        ValidationRecord(task="TASK-1", timestamp="2026-09-15", test="t1", result="PASSED"),
        ValidationRecord(task="TASK-2", timestamp="2026-09-16", test="t1", result="PASSED")
    ]
    ok, msg = LifecycleManager.can_transition(
        LearningState.REGRESSION_PROTECTED, LearningState.PROVEN_STABLE, has_automated_test=True, validation_records=records_2
    )
    assert ok


# ==============================================================================
# 5. Hybrid Retrieval & Explainability
# ==============================================================================
def test_hybrid_retrieval_explainability(store):
    """Asserts that hybrid retrieval returns exact matches, keyword matches, and human-readable reasons."""
    retriever = HybridRetrievalEngine(store.list_lessons(), store.list_rules())

    # Exact ID retrieval
    results = retriever.retrieve_by_query("GOV-RULE-129")
    assert len(results) > 0
    assert results[0].item_id == "GOV-RULE-129"
    assert "Exact Rule ID match" in results[0].relevance_reason

    # Lexical keyword retrieval
    res_kw = retriever.retrieve_by_query("radiometric overlap")
    assert len(res_kw) > 0
    assert any("Lexical match" in r.relevance_reason for r in res_kw)

    # Context retrieval
    ctx = TaskContext(
        diagnostic="DIAG-05",
        operation=["sample_eligibility_census"],
        risk_class=["POPULATION-CONSTRUCTION"]
    )
    res_ctx = retriever.retrieve_for_context(ctx)
    assert len(res_ctx) > 0
    assert res_ctx[0].relevance_reason != ""


# ==============================================================================
# 6. Novelty Detection
# ==============================================================================
def test_novelty_detection(store):
    """Asserts that novel operations or unverified assumptions are accurately flagged."""
    detector = NoveltyDetector(store.failure_classes, store.rules, store.assumptions)

    ctx_novel = TaskContext(
        operation=["unregistered_quantum_annealing_pass"],
        active_assumptions=["UNREGISTERED-ASSUMPTION-999"]
    )
    flags = detector.evaluate_task_novelty(ctx_novel, applicable_rules=[])
    flag_types = [f["flag"] for f in flags]
    assert NoveltyFlag.NOVEL.value in flag_types


# ==============================================================================
# 7. Performance Invariant (< 5.0 seconds, target < 0.05s)
# ==============================================================================
def test_preflight_performance_invariant():
    """Asserts that preflight completes in well under 5 seconds."""
    ctx = TaskContext(
        task_id="PERF-TEST",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["sample_eligibility_census", "paired_inference"],
        proposed_plan="Valid execution plan under registered design."
    )
    res = evaluate_task_preflight(ctx)
    assert res.elapsed_seconds < 5.0, f"Preflight exceeded 5s target: {res.elapsed_seconds:.4f}s"
    assert res.elapsed_seconds < 0.20, f"Preflight took longer than expected: {res.elapsed_seconds:.4f}s"


# ==============================================================================
# 8. Migration Completeness & Zero Lesson Loss
# ==============================================================================
def test_migration_zero_loss(store):
    """Asserts that all 104 historical lessons and validation records are preserved."""
    legacy_p = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"
    legacy_data = json.loads(legacy_p.read_text(encoding="utf-8"))
    legacy_lessons = legacy_data.get("lessons", [])

    assert len(legacy_lessons) == 104
    assert len(store.lessons) == 104

    for leg in legacy_lessons:
        lid = leg["lesson_id"]
        assert lid in store.lessons, f"Legacy lesson {lid} lost in v2 migration!"
        v2_lsn = store.lessons[lid]
        assert v2_lsn.status.value == leg["status"]
        assert len(v2_lsn.validation_history) == len(leg.get("validation_history", []))


# ==============================================================================
# 9. Monotonic Safety Enforcement
# ==============================================================================
def test_monotonic_safety_critical_weakening_fails_closed():
    """Asserts that modifying or proposing a rule that weakens a critical invariant fails closed."""
    old_rule = Rule(
        rule_id="BLOCK-001-HOLDOUT",
        principle_id="PRIN-007",
        failure_class="DATA-INTEGRITY",
        title="HOLDOUT partition access is strictly forbidden",
        statement="HOLDOUT partition access is strictly forbidden.",
        scope=ScopeLevel.GLOBAL,
        severity=SeverityLevel.CRITICAL,
        action=ActionType.BLOCK,
        non_overridable=True,
        prohibited_actions=["holdout", "holdout evaluation"]
    )

    # 1. Attempt to downgrade severity
    weakened_severity = Rule(
        rule_id="BLOCK-001-HOLDOUT",
        principle_id="PRIN-007",
        failure_class="DATA-INTEGRITY",
        title="HOLDOUT partition access is strictly forbidden",
        statement="HOLDOUT partition access is strictly forbidden.",
        scope=ScopeLevel.GLOBAL,
        severity=SeverityLevel.LOW,
        action=ActionType.BLOCK,
        non_overridable=True,
        prohibited_actions=["holdout", "holdout evaluation"]
    )
    change_class, reason = LifecycleManager.classify_rule_change(old_rule, weakened_severity)
    assert change_class == RuleChangeClass.WEAKENING
    ok, msg = LifecycleManager.validate_monotonic_safety(old_rule, weakened_severity)
    assert not ok, "Critical rule weakening must fail closed"
    assert "CRITICAL_SAFETY_WEAKENING_PROHIBITED" in msg

    # 2. Attempt to downgrade action from BLOCK to WARN
    weakened_action = Rule(
        rule_id="BLOCK-001-HOLDOUT",
        principle_id="PRIN-007",
        failure_class="DATA-INTEGRITY",
        title="HOLDOUT partition access is strictly forbidden",
        statement="HOLDOUT partition access is strictly forbidden.",
        scope=ScopeLevel.GLOBAL,
        severity=SeverityLevel.CRITICAL,
        action=ActionType.WARN,
        non_overridable=True,
        prohibited_actions=["holdout", "holdout evaluation"]
    )
    ok_act, msg_act = LifecycleManager.validate_monotonic_safety(old_rule, weakened_action)
    assert not ok_act
    assert "CRITICAL_SAFETY_WEAKENING_PROHIBITED" in msg_act

    # 3. Attempt to remove prohibited action
    weakened_prohibition = Rule(
        rule_id="BLOCK-001-HOLDOUT",
        principle_id="PRIN-007",
        failure_class="DATA-INTEGRITY",
        title="HOLDOUT partition access is strictly forbidden",
        statement="HOLDOUT partition access is strictly forbidden.",
        scope=ScopeLevel.GLOBAL,
        severity=SeverityLevel.CRITICAL,
        action=ActionType.BLOCK,
        non_overridable=True,
        prohibited_actions=["holdout"]  # removed 'holdout evaluation'
    )
    ok_proh, msg_proh = LifecycleManager.validate_monotonic_safety(old_rule, weakened_prohibition)
    assert not ok_proh
    assert "CRITICAL_SAFETY_WEAKENING_PROHIBITED" in msg_proh


# ==============================================================================
# 10. Rule Quarantine and Evidence Strength
# ==============================================================================
def test_rule_quarantine_prevents_unauthorized_blocking():
    """Asserts that quarantined rules (PROPOSED/REVIEW_REQUIRED) cannot emit hard blockers."""
    from ocean_sentinel.governance.enforcement import EnforcementEngine

    quarantined_rule = Rule(
        rule_id="RULE-NEW-PROPOSAL",
        principle_id="PRIN-001",
        failure_class="DATA-INTEGRITY",
        title="New proposal",
        statement="Block XYZ.",
        scope=ScopeLevel.PROJECT,
        severity=SeverityLevel.CRITICAL,
        action=ActionType.BLOCK,
        status=LearningState.PROPOSED,
        prohibited_actions=["xyz_action"]
    )

    engine = EnforcementEngine()
    ctx = TaskContext(
        task_id="T-QUARANTINE",
        task_type="diagnostic",
        proposed_plan="Execute xyz_action in diagnostic."
    )
    blockers, warnings, _ = engine.evaluate_task(ctx, [quarantined_rule])
    assert len(blockers) == 0, "Quarantined rule must not emit hard BLOCK"
    assert len(warnings) > 0, "Quarantined rule must be demoted to WARN"
    assert any("quarantined" in w.message.lower() for w in warnings)


def test_weak_evidence_cannot_emit_hard_block():
    """Asserts that rules backed only by hypotheses or unverified assertions cannot emit hard blockers."""
    from ocean_sentinel.governance.enforcement import EnforcementEngine

    weak_rule = Rule(
        rule_id="RULE-HYPOTHETICAL",
        principle_id="PRIN-001",
        failure_class="DATA-INTEGRITY",
        title="Hypothetical restriction",
        statement="Block ABC based on hypothesis.",
        scope=ScopeLevel.PROJECT,
        severity=SeverityLevel.CRITICAL,
        action=ActionType.BLOCK,
        status=LearningState.REGRESSION_PROTECTED,
        evidence_strength=EvidenceStrength.HYPOTHESIS,
        prohibited_actions=["abc_action"]
    )

    engine = EnforcementEngine()
    ctx = TaskContext(
        task_id="T-WEAK-EVIDENCE",
        task_type="diagnostic",
        proposed_plan="Execute abc_action in diagnostic."
    )
    blockers, warnings, _ = engine.evaluate_task(ctx, [weak_rule])
    assert len(blockers) == 0, "Weak evidence rule must not emit hard BLOCK"
    assert len(warnings) > 0, "Weak evidence rule must be demoted to WARN"
    assert any("weak evidence" in w.message.lower() for w in warnings)


# ==============================================================================
# 11. Validation Independence and Fingerprint Collisions
# ==============================================================================
def test_validation_independence_anti_duplication():
    """Asserts that duplicate validation fingerprints and self-validations are rejected."""
    # 1. Self-validation by origin task is rejected
    origin_record = ValidationRecord(
        task="TASK-ORIGIN",
        timestamp="2026-09-10T12:00:00Z",
        test="test_x",
        result="PASSED",
        fingerprint=LifecycleManager.compute_validation_fingerprint("TASK-ORIGIN", "test_x", "", "2026-09-10T12:00:00Z")
    )
    ok, msg = LifecycleManager.can_transition(
        LearningState.REGRESSION_PROTECTED,
        LearningState.PROVEN_STABLE,
        has_automated_test=True,
        validation_records=[origin_record],
        origin_task="TASK-ORIGIN"
    )
    assert not ok
    assert "BLOCK-010-SELF_VALIDATION_PROHIBITED" in msg

    # 2. Duplicate fingerprint collision is rejected
    subsequent_1 = ValidationRecord(
        task="TASK-SUB-1",
        timestamp="2026-09-12T12:00:00Z",
        test="test_x",
        result="PASSED",
        fingerprint="identical_fingerprint_hash"
    )
    subsequent_2 = ValidationRecord(
        task="TASK-SUB-2",
        timestamp="2026-09-14T12:00:00Z",
        test="test_x",
        result="PASSED",
        fingerprint="identical_fingerprint_hash"
    )
    ok_dup, msg_dup = LifecycleManager.can_transition(
        LearningState.REGRESSION_PROTECTED,
        LearningState.PROVEN_STABLE,
        has_automated_test=True,
        validation_records=[subsequent_1, subsequent_2]
    )
    assert not ok_dup
    assert "BLOCK-010-DUPLICATE_VALIDATION" in msg_dup


# ==============================================================================
# 12. Rule Change Impact Calculation
# ==============================================================================
def test_rule_impact_calculation(store):
    """Asserts that calculate_rule_impact correctly traces affected lessons, incidents, and tests."""
    impact = LifecycleManager.calculate_rule_impact("GOV-RULE-100", store)
    assert "error" not in impact
    assert impact["rule_id"] == "GOV-RULE-100"
    assert impact["principle_id"] == "PRIN-001"
    assert impact["failure_class"] == "ARTIFACT-REPORT-MISMATCH"
    assert isinstance(impact["impacted_lessons"], list)


# ==============================================================================
# 13. Statistical Provenance Suite (SciPy 1.15.3 Wilcoxon Semantics)
# ==============================================================================
def test_statistical_provenance_scipy_wilcoxon_semantics():
    """Asserts that MethodProvenanceValidator accurately validates exact vs ties/zeros,
    PermutationMethod, and asymptotic modes under SciPy 1.15.3 invariants.
    """
    from ocean_sentinel.governance.provenance import MethodProvenanceValidator

    # Case A: Distinct, nonzero differences (exact discrete signed-rank valid)
    payload_a = {
        "test_name": "scipy.stats.wilcoxon",
        "method": "exact",
        "has_ties": False,
        "has_zeros": False,
        "zero_method": "wilcox",
        "library": "scipy",
        "version": "1.15.3",
        "executed_algorithm": "exact discrete signed-rank distribution",
        "p_value": 0.03125,
        "n_paired": 6,
        "exact_p_value_semantics": "exact discrete signed-rank method under stated assumptions",
    }
    issues_a = MethodProvenanceValidator.validate_statistical_payload(payload_a)
    assert len([i for i in issues_a if i.code in ("PROV-001-UNBOUND_METHOD", "PROV-007-STATISTICAL_CONFLATION", "PROV-010-EXACT_ASSUMPTION_VIOLATION")]) == 0

    # Case B: Tied differences without caveat (exact assumption violated)
    payload_b = {
        "test_name": "scipy.stats.wilcoxon",
        "method": "exact",
        "has_ties": True,
        "has_zeros": False,
        "zero_method": "wilcox",
        "library": "scipy",
        "version": "1.15.3",
        "executed_algorithm": "exact discrete signed-rank distribution",
        "p_value": 0.04,
        "n_paired": 10,
        "exact_p_value_semantics": "exact p-value",
    }
    issues_b = MethodProvenanceValidator.validate_statistical_payload(payload_b)
    b_codes = [i.code for i in issues_b]
    assert "PROV-010-EXACT_ASSUMPTION_VIOLATION" in b_codes

    # Case B2: Tied differences with proper caveat -> passes
    payload_b2 = dict(payload_b, exact_p_value_semantics="NOT_EXACT_UNDER_DOCUMENTED_ASSUMPTIONS")
    issues_b2 = MethodProvenanceValidator.validate_statistical_payload(payload_b2)
    assert "PROV-010-EXACT_ASSUMPTION_VIOLATION" not in [i.code for i in issues_b2]

    # Case C: Zero differences without caveat
    payload_c = {
        "test_name": "scipy.stats.wilcoxon",
        "method": "exact",
        "has_ties": False,
        "has_zeros": True,
        "zero_method": "wilcox",
        "library": "scipy",
        "version": "1.15.3",
        "executed_algorithm": "exact discrete signed-rank distribution",
        "p_value": 0.05,
        "n_paired": 12,
        "exact_p_value_semantics": "exact p-value",
    }
    issues_c = MethodProvenanceValidator.validate_statistical_payload(payload_c)
    assert "PROV-010-EXACT_ASSUMPTION_VIOLATION" in [i.code for i in issues_c]

    # Case D: Explicit PermutationMethod (verified executed algorithm)
    payload_d = {
        "test_name": "scipy.stats.wilcoxon",
        "method": "PermutationMethod",
        "n_resamples": 9999,
        "zero_method": "wilcox",
        "library": "scipy",
        "version": "1.15.3",
        "executed_algorithm": "permutation_test",
        "p_value": 0.012,
        "n_paired": 10,
    }
    issues_d = MethodProvenanceValidator.validate_statistical_payload(payload_d)
    assert "PROV-011-UNVERIFIED_PERMUTATION_CONFIGURATION" not in [i.code for i in issues_d]
    assert "PROV-007-STATISTICAL_CONFLATION" not in [i.code for i in issues_d]

    # Case D2: PermutationMethod requested but executed_algorithm missing/unverified
    payload_d2 = {
        "test_name": "scipy.stats.wilcoxon",
        "method": "PermutationMethod",
        "zero_method": "wilcox",
        "library": "scipy",
        "version": "1.15.3",
        "executed_algorithm": "exact discrete signed-rank distribution",
        "p_value": 0.012,
        "n_paired": 10,
    }
    issues_d2 = MethodProvenanceValidator.validate_statistical_payload(payload_d2)
    assert "PROV-011-UNVERIFIED_PERMUTATION_CONFIGURATION" in [i.code for i in issues_d2]

    # Case E: Asymptotic mode
    payload_e = {
        "test_name": "scipy.stats.wilcoxon",
        "method": "asymptotic",
        "zero_method": "wilcox",
        "library": "scipy",
        "version": "1.15.3",
        "executed_algorithm": "asymptotic normal approximation",
        "p_value": 0.021,
        "n_paired": 100,
    }
    issues_e = MethodProvenanceValidator.validate_statistical_payload(payload_e)
    assert "PROV-001-UNBOUND_METHOD" not in [i.code for i in issues_e]
    # Report consistency: report claims exact while artifact used asymptotic
    rep_issues = MethodProvenanceValidator.audit_report_consistency(payload_e, "Our test showed exact significance with p = 0.0210.")
    assert any(i.code == "PROV-009-METHOD_MISMATCH" for i in rep_issues)

    # Case F: Mismatched method semantics (wilcoxon method='exact' claiming permutation)
    payload_f = {
        "test_name": "scipy.stats.wilcoxon",
        "method": "exact",
        "zero_method": "wilcox",
        "library": "scipy",
        "version": "1.15.3",
        "executed_algorithm": "exact permutation test",
        "p_value": 0.03,
        "n_paired": 10,
    }
    issues_f = MethodProvenanceValidator.validate_statistical_payload(payload_f)
    assert any(i.code == "PROV-007-STATISTICAL_CONFLATION" for i in issues_f)

    # Case G: SciPy version mismatch
    payload_g = {
        "test_name": "scipy.stats.wilcoxon",
        "method": "exact",
        "zero_method": "wilcox",
        "library": "scipy",
        "version": "1.14.0",
        "executed_algorithm": "exact discrete signed-rank distribution",
        "p_value": 0.03,
        "n_paired": 10,
    }
    issues_g = MethodProvenanceValidator.validate_statistical_payload(payload_g)
    assert any(i.code == "METHOD_SEMANTICS_REVIEW_REQUIRED" for i in issues_g)


# ==============================================================================
# 14. Lifecycle Anti-Gaming Suite (Tasks A through F)
# ==============================================================================
def test_lifecycle_anti_gaming_suite():
    """Asserts that LifecycleManager rejects realistic gaming attempts to manufacture PROVEN_STABLE status."""
    base_evidence = "Verified passing metric mIoU=0.842 on test_c21_guardrail."

    # Task A: Same evidence, same fixture, different task ID -> rejected
    rec_1 = ValidationRecord(task="TASK-RUN-01", timestamp="2026-09-12T10:00:00Z", test="test_c21", result="PASSED", evidence=base_evidence)
    rec_2 = ValidationRecord(task="TASK-RUN-02", timestamp="2026-09-12T11:00:00Z", test="test_c21", result="PASSED", evidence=base_evidence)
    ok_a, msg_a = LifecycleManager.can_transition(LearningState.REGRESSION_PROTECTED, LearningState.PROVEN_STABLE, has_automated_test=True, validation_records=[rec_1, rec_2], origin_task="TASK-ORIGIN")
    assert not ok_a
    assert "BLOCK-010-DUPLICATE_EVIDENCE" in msg_a

    # Task B: Same evidence, changed timestamp -> rejected
    rec_3 = ValidationRecord(task="TASK-RUN-03", timestamp="2026-09-15T12:00:00Z", test="test_c21", result="PASSED", evidence=base_evidence)
    ok_b, msg_b = LifecycleManager.can_transition(LearningState.REGRESSION_PROTECTED, LearningState.PROVEN_STABLE, has_automated_test=True, validation_records=[rec_1, rec_3], origin_task="TASK-ORIGIN")
    assert not ok_b
    assert "BLOCK-010-DUPLICATE_EVIDENCE" in msg_b

    # Task C: Same test, different wrapper but identical evidence -> rejected
    rec_4 = ValidationRecord(task="TASK-RUN-04", timestamp="2026-09-16T12:00:00Z", test="wrapper_for_test_c21", result="PASSED", evidence=base_evidence)
    ok_c, msg_c = LifecycleManager.can_transition(LearningState.REGRESSION_PROTECTED, LearningState.PROVEN_STABLE, has_automated_test=True, validation_records=[rec_1, rec_4], origin_task="TASK-ORIGIN")
    assert not ok_c
    assert "BLOCK-010-DUPLICATE_EVIDENCE" in msg_c

    # Task D: Cosmetic whitespace modification of identical substantive payload -> rejected
    cosmetic_evidence = "   Verified  passing metric   mIoU=0.842  on test_c21_guardrail.   "
    rec_5 = ValidationRecord(task="TASK-RUN-05", timestamp="2026-09-16T14:00:00Z", test="test_c21", result="PASSED", evidence=cosmetic_evidence)
    ok_d, msg_d = LifecycleManager.can_transition(LearningState.REGRESSION_PROTECTED, LearningState.PROVEN_STABLE, has_automated_test=True, validation_records=[rec_1, rec_5], origin_task="TASK-ORIGIN")
    assert not ok_d
    assert "BLOCK-010-DUPLICATE_EVIDENCE" in msg_d

    # Task E: Replay task ID -> rejected
    distinct_ev = "Distinct evidence from independent dataset census."
    rec_replay = ValidationRecord(task="REPLAY-RUN-01", timestamp="2026-09-16T15:00:00Z", test="test_replay", result="PASSED", evidence=distinct_ev)
    ok_e, msg_e = LifecycleManager.can_transition(LearningState.REGRESSION_PROTECTED, LearningState.PROVEN_STABLE, has_automated_test=True, validation_records=[rec_1, rec_replay], origin_task="TASK-ORIGIN")
    assert not ok_e
    assert "BLOCK-010-SYNTHETIC_VALIDATION_PROHIBITED" in msg_e

    # Task F: Same automation chain batch -> rejected
    rec_chain = ValidationRecord(task="AUTO-CHAIN-BATCH-02", timestamp="2026-09-16T16:00:00Z", test="test_chain", result="PASSED", evidence=distinct_ev)
    ok_f, msg_f = LifecycleManager.can_transition(LearningState.REGRESSION_PROTECTED, LearningState.PROVEN_STABLE, has_automated_test=True, validation_records=[rec_1, rec_chain], origin_task="TASK-ORIGIN")
    assert not ok_f
    assert "BLOCK-010-SYNTHETIC_VALIDATION_PROHIBITED" in msg_f


# ==============================================================================
# 15. Safety Channel Decoupling from Ranked Retrieval
# ==============================================================================
def test_safety_channel_strictly_enforces_when_retrieval_misses():
    """Asserts that critical safety enforcement strictly executes even when
    ranked retrieval returns zero safety-rule matches (due to zero lexical overlap).
    """
    # Context with zero lexical overlap to HOLDOUT or git rules
    ctx_holdout = TaskContext(
        task_id="SAFE-CHAN-01",
        task_type="diagnostic",
        proposed_plan="Compute calibrated Doppler centroid frequency f_dc and azimuthal bandwidth B_az for Sentinel-1 TOPS mode.",
        operation=["access_holdout"]
    )
    res_holdout = evaluate_task_preflight(ctx_holdout)
    assert not res_holdout.passed
    assert any(b.code == "BLOCK-001-HOLDOUT" for b in res_holdout.blockers)

    ctx_git = TaskContext(
        task_id="SAFE-CHAN-02",
        task_type="documentation",
        proposed_plan="Updating mathematical appendix for radar backscatter sigma_0 equations.",
        proposed_command="git reset --hard HEAD~1"
    )
    res_git = evaluate_task_preflight(ctx_git)
    assert not res_git.passed
    assert any(b.code == "BLOCK-007-DESTRUCTIVE_GIT" for b in res_git.blockers)


# ==============================================================================
# 16. Precedence Invariant: Identical Priority Opposing Actions
# ==============================================================================
def test_precedence_opposing_actions_unresolved_conflict():
    """Asserts that opposing substantive actions with identical priority trigger
    UNRESOLVED_CONFLICT and BLOCK-CONFLICT-001. Rule ID determines display order only.
    """
    r1 = Rule(
        rule_id="RULE-OPP-BLOCK-01",
        principle_id="PRIN-001",
        failure_class="GENERAL",
        title="Prohibit Action X",
        statement="Block action X",
        scope=ScopeLevel.PROJECT,
        severity=SeverityLevel.HIGH,
        action=ActionType.BLOCK,
        prohibited_actions=["action_x"]
    )
    r2 = Rule(
        rule_id="RULE-OPP-WARN-02",
        principle_id="PRIN-001",
        failure_class="GENERAL",
        title="Warn Action X",
        statement="Warn action X",
        scope=ScopeLevel.PROJECT,
        severity=SeverityLevel.HIGH,
        action=ActionType.WARN,
        prohibited_actions=["action_x"]
    )
    prec_eng = PrecedenceEngine()
    active_rules, conflicts, block_issues = prec_eng.resolve_rules([r1, r2])
    
    unresolved = [c for c in conflicts if c.resolution_status == "UNRESOLVED_CONFLICT"]
    assert len(unresolved) == 1
    assert unresolved[0].winning_rule_id is None
    assert any(b.code == "BLOCK-CONFLICT-001" for b in block_issues)


# ==============================================================================
# 17. Telemetry vs Execution Authorization Gate
# ==============================================================================
def test_telemetry_authorization_fail_closed_gate(tmp_path):
    """Asserts that telemetry cannot grant execution authority and that inconsistent
    authorization flags fail closed."""
    from scripts.agent_governance_preflight import verify_telemetry_run_state

    # 1. COMPLETE with execution_authorized=True -> fails closed
    p1 = tmp_path / "tel_bad_exec.json"
    p1.write_text(json.dumps({
        "final_completion_state": "COMPLETE",
        "phase": "COMPLETE",
        "analysis_authorized": True,
        "execution_authorized": True,
        "scientific_execution": False,
        "forbidden_scientific_or_data_operations": False,
        "governance": {"zero_destructive_git": True}
    }), encoding="utf-8")
    valid_1, errs_1 = verify_telemetry_run_state(p1)
    assert not valid_1
    assert any("BLOCK-012-TELEMETRY_AUTHORIZATION_AMBIGUITY" in e for e in errs_1)

    # 2. COMPLETE with scientific_execution=True -> fails closed
    p2 = tmp_path / "tel_bad_sci.json"
    p2.write_text(json.dumps({
        "final_completion_state": "COMPLETE",
        "phase": "COMPLETE",
        "analysis_authorized": True,
        "execution_authorized": False,
        "scientific_execution": True,
        "forbidden_scientific_or_data_operations": False,
        "governance": {"zero_destructive_git": True}
    }), encoding="utf-8")
    valid_2, errs_2 = verify_telemetry_run_state(p2)
    assert not valid_2
    assert any("BLOCK-012-TELEMETRY_AUTHORIZATION_AMBIGUITY" in e for e in errs_2)


# ==============================================================================
# 18. End-to-End Future-Agent Contexts Matrix (ACTUAL == EXPECTED)
# ==============================================================================
def test_end_to_end_future_agent_contexts_matrix():
    """Asserts that the 6 future-agent contexts and negative controls produce
    exact expected governance behavior (ACTUAL == EXPECTED across 8 dimensions).
    """
    matrix = [
        {
            "id": "A_diag",
            "context": TaskContext(
                task_id="A_diag",
                task_type="diagnostic",
                diagnostic="DIAG-05",
                operation=["sample_eligibility_census", "paired_inference"],
                proposed_plan="Conduct census after validity masking."
            ),
            "expected_action": "PASS",
            "expected_blockers": [],
            "expected_warnings": [],
            "expected_applicable_rules_count": 122,
            "expected_novelty_flag": "KNOWN_BUT_UNPROTECTED",
        },
        {
            "id": "B_doc",
            "context": TaskContext(
                task_id="B_doc",
                task_type="documentation",
                proposed_plan="Refactor docstrings in ocean_sentinel.utils."
            ),
            "expected_action": "PASS",
            "expected_blockers": [],
            "expected_warnings": [],
            "expected_applicable_rules_count": 13,
            "expected_novelty_flag": "KNOWN",
        },
        {
            "id": "C_stat",
            "context": TaskContext(
                task_id="C_stat",
                task_type="evaluation",
                operation=["bootstrap_confidence_intervals"],
                statistical_test={"library": "scipy", "function": "scipy.stats.bootstrap", "method": "BCa"}
            ),
            "expected_action": "PASS",
            "expected_blockers": [],
            "expected_warnings": [],
            "expected_applicable_rules_count": 118,
            "expected_novelty_flag": "NOVEL",
        },
        {
            "id": "D_sci",
            "context": TaskContext(
                task_id="D_sci",
                task_type="diagnostic",
                operation=["synthetic_aperture_tomography"],
                proposed_plan="3D volumetric scattering inversion."
            ),
            "expected_action": "PASS",
            "expected_blockers": [],
            "expected_warnings": [],
            "expected_applicable_rules_count": 118,
            "expected_novelty_flag": "NOVEL",
        },
        {
            "id": "E_gov",
            "context": TaskContext(
                task_id="E_gov",
                task_type="repository_governance",
                proposed_plan="Reviewing rule quarantine states for promotion."
            ),
            "expected_action": "PASS",
            "expected_blockers": [],
            "expected_warnings": [],
            "expected_applicable_rules_count": 13,
            "expected_novelty_flag": "KNOWN",
        },
        {
            "id": "F_insp",
            "context": TaskContext(
                task_id="F_insp",
                task_type="diagnostic",
                proposed_plan="Forensic read-only inspection of ops02 audit logs without model execution."
            ),
            "expected_action": "PASS",
            "expected_blockers": [],
            "expected_warnings": [],
            "expected_applicable_rules_count": 118,
            "expected_novelty_flag": "KNOWN_BUT_UNPROTECTED",
        },
        {
            "id": "G_holdout_ctrl",
            "context": TaskContext(
                task_id="G_holdout_ctrl",
                task_type="diagnostic",
                proposed_plan="Evaluating holdout data split."
            ),
            "expected_action": "BLOCK",
            "expected_blockers": ["BLOCK-001-HOLDOUT"],
            "expected_warnings": [],
            "expected_applicable_rules_count": 118,
            "expected_novelty_flag": None,
        },
        {
            "id": "H_contra_asmp_ctrl",
            "context": TaskContext(
                task_id="H_contra_asmp_ctrl",
                task_type="diagnostic",
                active_assumptions=["ASSUMP-006"]
            ),
            "expected_action": "BLOCK",
            "expected_blockers": ["BLOCK-ASM-CONTRADICTED"],
            "expected_warnings": [],
            "expected_applicable_rules_count": 118,
            "expected_novelty_flag": "BLOCK_CONTRADICTED_ASSUMPTION",
        },
        {
            "id": "I_unver_asmp_ctrl",
            "context": TaskContext(
                task_id="I_unver_asmp_ctrl",
                task_type="diagnostic",
                active_assumptions=["UNREGISTERED-ASMP-999"]
            ),
            "expected_action": "WARN",
            "expected_blockers": [],
            "expected_warnings": ["WARN-ASM-UNVERIFIED"],
            "expected_applicable_rules_count": 118,
            "expected_novelty_flag": "NOVEL",
        },
    ]

    for item in matrix:
        cid = item["id"]
        ctx = item["context"]
        res = evaluate_task_preflight(ctx)
        actual_action = "BLOCK" if res.blockers else ("WARN" if res.warnings else "PASS")
        assert actual_action == item["expected_action"], f"Context {cid} action mismatch: expected {item['expected_action']}, got {actual_action}"

        actual_blocker_codes = [b.code for b in res.blockers]
        for exp_b in item["expected_blockers"]:
            assert exp_b in actual_blocker_codes, f"Context {cid} missing expected blocker {exp_b} in {actual_blocker_codes}"

        actual_warning_codes = [w.code for w in res.warnings]
        for exp_w in item["expected_warnings"]:
            assert exp_w in actual_warning_codes, f"Context {cid} missing expected warning {exp_w} in {actual_warning_codes}"

        assert len(res.applicable_rules) == item["expected_applicable_rules_count"], (
            f"Context {cid} rule count mismatch: expected {item['expected_applicable_rules_count']}, got {len(res.applicable_rules)}"
        )

        if item["expected_novelty_flag"]:
            nov_flags = [f["flag"] for f in res.novelty_flags]
            assert item["expected_novelty_flag"] in nov_flags, (
                f"Context {cid} missing expected novelty flag {item['expected_novelty_flag']} in {nov_flags}"
            )

