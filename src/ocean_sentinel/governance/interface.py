"""Future Agent Task Interface for Lesson Architecture v2.

Provides a single, structured, reusable preflight evaluation API answering:
- What happened before that is relevant to this task?
- What rules apply?
- Why do they apply?
- What must I check before acting?
- What prevents me from repeating the failure?
"""

import time
from typing import Any, Dict, List, Optional
from ocean_sentinel.governance.applicability import ApplicabilityEngine
from ocean_sentinel.governance.enforcement import EnforcementEngine
from ocean_sentinel.governance.models import (
    PreflightIssueV2,
    PreflightV2Result,
    Rule,
    SeverityLevel,
    TaskContext,
)
from ocean_sentinel.governance.control import (
    ControlEffectivenessTracker,
    ControlStage,
    ControlStageOutcome,
)
from ocean_sentinel.governance.novelty import NoveltyDetector
from ocean_sentinel.governance.precedence import PrecedenceEngine
from ocean_sentinel.governance.retrieval import HybridRetrievalEngine
from ocean_sentinel.governance.store import GovernanceStore


def evaluate_task_preflight(
    context: TaskContext,
    tracker: Optional[ControlEffectivenessTracker] = None,
) -> PreflightV2Result:
    """Evaluates a proposed task context against the complete Lesson Architecture v2."""
    start_time = time.perf_counter()
    store = GovernanceStore.get_instance()
    active_tracker = tracker or ControlEffectivenessTracker(task_id=context.task_id)

    # 1. Applicability Engine: filter candidate rules
    app_engine = ApplicabilityEngine()
    applicable_candidates: List[Rule] = []
    for r in store.list_rules():
        is_app, _ = app_engine.evaluate_rule(r, context)
        if is_app:
            applicable_candidates.append(r)

    # 2. Precedence and Conflict Resolution
    prec_engine = PrecedenceEngine()
    active_rules, conflicts, conflict_blockers = prec_engine.resolve_rules(applicable_candidates)

    # 3. Enforcement Engine: detect blockers, warnings, and recommendations
    enf_engine = EnforcementEngine()
    blockers, warnings, recommendations = enf_engine.evaluate_task(context, active_rules)
    blockers.extend(conflict_blockers)

    # 4. Hybrid Retrieval Engine: find relevant lessons and rules with match reasons
    retrieval_engine = HybridRetrievalEngine(store.list_lessons(), store.list_rules())
    relevant_items = retrieval_engine.retrieve_for_context(context, max_results=8)

    # Instrument Control Stage 2 (LESSON_RETRIEVED) based on actual hybrid retrieval execution
    retrieved_lessons = [item for item in relevant_items if getattr(item, "item_type", "") == "lesson"]
    if len(retrieved_lessons) > 0:
        lesson_ids = [l.item_id for l in retrieved_lessons]
        active_tracker.record_stage(
            ControlStage.LESSON_RETRIEVED,
            ControlStageOutcome.TRUE,
            reason=f"Hybrid retrieval returned {len(retrieved_lessons)} lesson(s) for task context.",
            entity_refs=lesson_ids,
            source="governance_preflight_retrieval",
        )
    else:
        active_tracker.record_stage(
            ControlStage.LESSON_RETRIEVED,
            ControlStageOutcome.FALSE,
            reason="Hybrid retrieval executed and returned zero lessons matching task context.",
            source="governance_preflight_retrieval",
        )

    # Instrument Control Stage 1 (LESSON_EXISTS) - unobserved independently from retrieval
    # Preflight does not possess an independent authoritative oracle for lesson existence.
    if active_tracker.get_stage_record(ControlStage.LESSON_EXISTS) is None:
        active_tracker.record_stage(
            ControlStage.LESSON_EXISTS,
            ControlStageOutcome.UNKNOWN,
            reason=(
                "The current system has a retrieval operation but does not have an independent observation "
                "proving that a relevant lesson exists separately from whether retrieval returned it."
            ),
            source="governance_preflight_store",
        )

    # Instrument Control Stage 3 (LESSON_APPLICABLE) - unobserved in current rule-only applicability engine
    if active_tracker.get_stage_record(ControlStage.LESSON_APPLICABLE) is None:
        active_tracker.record_stage(
            ControlStage.LESSON_APPLICABLE,
            ControlStageOutcome.UNKNOWN,
            reason="Current applicability engine evaluates rules; lesson-specific applicability evaluator is not present in architecture.",
            source="governance_preflight_applicability",
        )

    # Instrument Control Stage 4 (LESSON_PRESENTED) - unobserved in backend preflight
    if active_tracker.get_stage_record(ControlStage.LESSON_PRESENTED) is None:
        active_tracker.record_stage(
            ControlStage.LESSON_PRESENTED,
            ControlStageOutcome.UNKNOWN,
            reason="Preflight evaluation occurs inside backend pipeline; UI presentation event not observed.",
            source="governance_preflight_presentation",
        )

    # 5. Assumption Registry: surface relevant assumptions
    required_assumptions = []
    for asmp in store.list_assumptions():
        # Match assumptions associated with applicable rules or context scope
        if any(rid in asmp.associated_rules for rid in [r.rule_id for r in active_rules]):
            required_assumptions.append(asmp)
        elif asmp.assumption_id in context.active_assumptions:
            required_assumptions.append(asmp)

    # 6. Novelty Detection
    nov_detector = NoveltyDetector(store.failure_classes, store.rules, store.assumptions)
    novelty_flags = nov_detector.evaluate_task_novelty(context, active_rules)
    for n_flag in novelty_flags:
        if n_flag.get("flag") == "BLOCK_CONTRADICTED_ASSUMPTION":
            blockers.append(PreflightIssueV2(
                severity=SeverityLevel.CRITICAL,
                code="BLOCK-ASM-CONTRADICTED",
                rule_id="GOV-RULE-100",
                message=n_flag["description"],
                remediation=n_flag["guideline"],
            ))
        elif "assumption" in n_flag.get("target", ""):
            warnings.append(PreflightIssueV2(
                severity=SeverityLevel.HIGH,
                code="WARN-ASM-UNVERIFIED",
                rule_id="GOV-RULE-100",
                message=n_flag["description"],
                remediation=n_flag["guideline"],
            ))

    # Instrument Control Stage 5 (RULE_APPLIED)
    # Strictly distinguishes:
    #   Case 1/2: zero applicable rules => NOT_APPLICABLE (even if active catalog rules > 0)
    #   Case 3: applicable rules > 0, applied = 0 => FALSE
    #   Case 4: applicable rules > 0, applied > 0 => TRUE
    all_issues = blockers + warnings + recommendations
    applied_rule_ids = sorted(list(set(issue.rule_id for issue in all_issues if issue.rule_id)))
    active_tracker.record_rule_applied(
        applicable_rules_count=len(active_rules),
        applied_rule_ids=applied_rule_ids,
        active_rules_count=len(store.list_rules()),
        source="governance_preflight_enforcement",
    )

    # Instrument Control Stage 6 (MISTAKE_PREVENTED) - unobserved prior to post-action outcome evidence
    if active_tracker.get_stage_record(ControlStage.MISTAKE_PREVENTED) is None:
        active_tracker.record_stage(
            ControlStage.MISTAKE_PREVENTED,
            ControlStageOutcome.UNKNOWN,
            reason="Preflight evaluation precedes task execution; post-action outcome evidence is not yet observable.",
            source="governance_preflight_outcome",
        )

    # 7. Aggregate required checks and tests
    required_checks = set()
    relevant_tests = set()
    for r in active_rules:
        for chk in r.required_checks:
            required_checks.add(chk)
        for t in r.regression_test_ids:
            relevant_tests.add(t)

    elapsed = time.perf_counter() - start_time
    has_blockers = len(blockers) > 0
    passed = not has_blockers

    # Finalize deterministic control trace
    control_trace = active_tracker.finalize_trace()

    return PreflightV2Result(
        passed=passed,
        task_id=context.task_id or "TASK-CURRENT",
        task_type=context.task_type,
        elapsed_seconds=elapsed,
        relevant_lessons=relevant_items,
        applicable_rules=active_rules,
        required_assumptions=required_assumptions,
        required_checks=sorted(list(required_checks)),
        blockers=blockers,
        warnings=warnings,
        recommendations=recommendations,
        relevant_tests=sorted(list(relevant_tests)),
        conflicts=[c.__dict__ for c in conflicts],
        novelty_flags=novelty_flags,
        control_trace=control_trace,
    )



def format_preflight_v2_report(res: PreflightV2Result) -> str:
    """Formats a human- and agent-readable Markdown report from a PreflightV2Result."""
    lines = []
    lines.append("=" * 72)
    lines.append(f"OCEAN SENTINEL AGENT GOVERNANCE PREFLIGHT v2 — [{res.task_type.upper()}]")
    lines.append("=" * 72)
    status_str = "PASSED (EXECUTION AUTHORIZED WITHIN ENVELOPE)" if res.passed else "FAILED (EXECUTION BLOCKED)"
    lines.append(f"Status:             {status_str}")
    lines.append(f"Task ID:            {res.task_id}")
    lines.append(f"Elapsed Runtime:    {res.elapsed_seconds:.4f}s (< 5.0s target)")
    lines.append(f"Applicable Rules:   {len(res.applicable_rules)} active rules")
    lines.append(f"Relevant Lessons:   {len(res.relevant_lessons)} institutional lessons retrieved")
    lines.append(f"Active Assumptions: {len(res.required_assumptions)} surfaced")
    lines.append("-" * 72)

    if res.blockers:
        lines.append("\n[CRITICAL GOVERNANCE BLOCKERS] — MUST RESOLVE BEFORE PROCEEDING:")
        for b in res.blockers:
            lines.append(f"  * [{b.code}] (Rule {b.rule_id}): {b.message}")
            lines.append(f"    REMEDY: {b.remediation}")
            if b.test_ids:
                lines.append(f"    TEST:   {b.test_ids}")

    if res.warnings:
        lines.append("\n[ADVISORY WARNINGS]:")
        for w in res.warnings:
            lines.append(f"  * [{w.code}] (Rule {w.rule_id}): {w.message}")
            lines.append(f"    REMEDY: {w.remediation}")

    if res.novelty_flags:
        lines.append("\n[NOVELTY & RISK DETECTION]:")
        for nov in res.novelty_flags[:5]:
            lines.append(f"  * [{nov['flag']}] {nov['target']}: {nov['description']}")
            lines.append(f"    GUIDANCE: {nov['guideline']}")
        if len(res.novelty_flags) > 5:
            lines.append(f"  ... and {len(res.novelty_flags) - 5} additional flagged rules in RECORDED state.")

    if res.required_assumptions:
        lines.append("\n[KEY OPERATIONAL ASSUMPTIONS SURFACED]:")
        for a in res.required_assumptions[:5]:
            lines.append(f"  - [{a.status.value}] {a.assumption_id}: {a.statement}")
            lines.append(f"    Verification: {a.verification_method}")

    if res.relevant_lessons:
        lines.append("\n[TOP RELEVANT INSTITUTIONAL LESSONS RETRIEVED]:")
        for item in res.relevant_lessons[:5]:
            lines.append(f"  - {item.item_id} [{item.severity.value} | {item.status.value}]: {item.item.get('title')}")
            lines.append(f"    Why Retrieved: {item.relevance_reason}")

    if res.relevant_tests:
        lines.append("\n[ASSOCIATED REGRESSION GUARDRAILS]:")
        for t in res.relevant_tests[:6]:
            lines.append(f"  * {t}")

    lines.append("=" * 72)
    return "\n".join(lines)
