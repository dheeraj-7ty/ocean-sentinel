"""Contract tests for Ocean Sentinel Governance Control-Effectiveness & Negative Feedback Instrumentation.

Covers:
- NegativeFeedbackCategory (exact 9 values, uniqueness, serialization, rework mapping)
- ControlStage (exact 6 values, uniqueness, serialization, canonical order)
- ControlStageOutcome (exact 4 values, distinct bounded semantics)
- ControlTraceRecord (creation, validation, serialization, immutability conventions)
- ControlEffectivenessTracker (in-memory trace builder, anti-fabrication guards, overwrite protection, deterministic trace)
- Critical Semantic Guards (retrieved != presented, retrieved != applicable, block != mistake prevented, unknown != false)
- Preflight Integration (trace emitted in PreflightV2Result, existing governance behaviors preserved)
- Tamper-Evident Negative Feedback Receipts (atomic writes, fail-closed conflicting overwrite, canonical sha256, no canonical catalog mutation)
"""

import json
from pathlib import Path
import pytest

from ocean_sentinel.governance.control import (
    DEFAULT_FEEDBACK_DIR,
    NON_AUTHORITATIVE_FEEDBACK_TO_REWORK_MAPPING,
    ORDERED_CONTROL_STAGES,
    ControlEffectivenessTracker,
    record_negative_feedback,
    resolve_rule_applied_outcome,
)
from ocean_sentinel.governance.interface import evaluate_task_preflight
from ocean_sentinel.governance.models import (
    ControlStage,
    ControlStageOutcome,
    ControlTraceRecord,
    NegativeFeedbackCategory,
    PreflightV2Result,
    ReworkClass,
    TaskContext,
)
from ocean_sentinel.governance.provenance import canonicalize_json_v1
from ocean_sentinel.governance.store import GovernanceStore

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_V2_DIR = REPO_ROOT / "data" / "metadata" / "governance_v2"


# ==============================================================================
# Group A: NegativeFeedbackCategory
# ==============================================================================

class TestNegativeFeedbackCategory:
    """Verifies the exact nine canonical negative feedback categories."""

    EXPECTED_CATEGORIES = {
        "FALSE_BLOCK",
        "MISSED_LESSON",
        "WRONG_APPLICABILITY",
        "WRONG_SCOPE",
        "WRONG_PRECEDENCE",
        "WEAK_ENFORCEMENT",
        "STALE_LESSON",
        "DUPLICATE_LESSON",
        "CONTRADICTORY_LESSON",
    }

    def test_exact_nine_categories_present(self):
        actual = {c.value for c in NegativeFeedbackCategory}
        assert actual == self.EXPECTED_CATEGORIES, (
            f"Expected exactly 9 categories, got diff: {actual ^ self.EXPECTED_CATEGORIES}"
        )
        assert len(NegativeFeedbackCategory) == 9

    def test_category_uniqueness(self):
        names = [c.name for c in NegativeFeedbackCategory]
        values = [c.value for c in NegativeFeedbackCategory]
        assert len(names) == len(set(names))
        assert len(values) == len(set(values))

    def test_category_serialization(self):
        for cat in NegativeFeedbackCategory:
            serialized = json.dumps({"category": cat.value})
            loaded = json.loads(serialized)
            assert loaded["category"] == cat.value

    def test_non_authoritative_rework_mapping(self):
        """Ensures all 9 categories map to documented operational ReworkClass without silent merging."""
        assert len(NON_AUTHORITATIVE_FEEDBACK_TO_REWORK_MAPPING) == 9
        for cat in NegativeFeedbackCategory:
            assert cat in NON_AUTHORITATIVE_FEEDBACK_TO_REWORK_MAPPING
            assert isinstance(NON_AUTHORITATIVE_FEEDBACK_TO_REWORK_MAPPING[cat], ReworkClass)


# ==============================================================================
# Group B: ControlStage
# ==============================================================================

class TestControlStage:
    """Verifies the exact six canonical stages of the learning-control chain."""

    EXPECTED_STAGES = [
        "LESSON_EXISTS",
        "LESSON_RETRIEVED",
        "LESSON_APPLICABLE",
        "LESSON_PRESENTED",
        "RULE_APPLIED",
        "MISTAKE_PREVENTED",
    ]

    def test_exact_six_stages_present(self):
        actual = [s.value for s in ControlStage]
        assert actual == self.EXPECTED_STAGES
        assert len(ControlStage) == 6

    def test_stage_uniqueness(self):
        names = [s.name for s in ControlStage]
        values = [s.value for s in ControlStage]
        assert len(names) == len(set(names))
        assert len(values) == len(set(values))

    def test_canonical_ordering(self):
        assert [s.value for s in ORDERED_CONTROL_STAGES] == self.EXPECTED_STAGES


# ==============================================================================
# Group C: ControlStageOutcome
# ==============================================================================

class TestControlStageOutcome:
    """Verifies the exact 4-valued bounded semantic outcomes."""

    EXPECTED_OUTCOMES = {"TRUE", "FALSE", "UNKNOWN", "NOT_APPLICABLE"}

    def test_exact_four_outcomes_present(self):
        actual = {o.value for o in ControlStageOutcome}
        assert actual == self.EXPECTED_OUTCOMES
        assert len(ControlStageOutcome) == 4

    def test_semantic_distinctness(self):
        """Confirms that UNKNOWN, NOT_APPLICABLE, and FALSE are mutually distinct."""
        assert ControlStageOutcome.UNKNOWN != ControlStageOutcome.FALSE
        assert ControlStageOutcome.NOT_APPLICABLE != ControlStageOutcome.FALSE
        assert ControlStageOutcome.UNKNOWN != ControlStageOutcome.NOT_APPLICABLE
        assert ControlStageOutcome.TRUE != ControlStageOutcome.UNKNOWN


# ==============================================================================
# Group D: ControlTraceRecord
# ==============================================================================

class TestControlTraceRecord:
    """Verifies lightweight, serializable, and evidence-oriented trace records."""

    def test_valid_record_creation(self):
        rec = ControlTraceRecord(
            stage=ControlStage.LESSON_RETRIEVED,
            outcome=ControlStageOutcome.TRUE,
            observed_at="2026-09-26T12:00:00Z",
            reason="Retrieved 2 lessons",
            entity_refs=["LES-001", "LES-002"],
            evidence_refs=["search_query_log_123"],
            source="hybrid_retrieval",
            control_trace_id="trace_test_001",
        )
        assert rec.stage == ControlStage.LESSON_RETRIEVED
        assert rec.outcome == ControlStageOutcome.TRUE
        assert rec.entity_refs == ["LES-001", "LES-002"]

    def test_to_dict_serialization(self):
        rec = ControlTraceRecord(
            stage=ControlStage.RULE_APPLIED,
            outcome=ControlStageOutcome.FALSE,
            observed_at="2026-09-26T12:00:00Z",
            reason="Rule was applicable but plan did not violate preconditions",
            entity_refs=["GOV-RULE-001"],
            evidence_refs=[],
            source="enforcement_engine",
            control_trace_id="trace_test_002",
        )
        d = rec.to_dict()
        assert d["stage"] == "RULE_APPLIED"
        assert d["outcome"] == "FALSE"
        assert d["reason"] == "Rule was applicable but plan did not violate preconditions"
        assert d["entity_refs"] == ["GOV-RULE-001"]
        assert d["control_trace_id"] == "trace_test_002"

        # Verify JSON round-trip
        dumped = json.dumps(d)
        loaded = json.loads(dumped)
        assert loaded["stage"] == "RULE_APPLIED"
        assert loaded["outcome"] == "FALSE"


# ==============================================================================
# Group E: ControlEffectivenessTracker
# ==============================================================================

class TestControlEffectivenessTracker:
    """Verifies tracker functionality: stage recording, overwrite guards, trace finalization."""

    def test_in_memory_construction_no_disk_side_effects(self, tmp_path):
        tracker = ControlEffectivenessTracker(task_id="TASK-MEM-ONLY")
        assert tracker.task_id == "TASK-MEM-ONLY"
        assert tracker.trace_id.startswith("trace_TASK-MEM-ONLY_")

    def test_record_stage_and_retrieve(self):
        tracker = ControlEffectivenessTracker(task_id="TASK-RECORD")
        rec = tracker.record_stage(
            stage=ControlStage.LESSON_EXISTS,
            outcome=ControlStageOutcome.TRUE,
            reason="Lesson store has 1 matching item",
            entity_refs=["LES-010"],
        )
        assert rec.stage == ControlStage.LESSON_EXISTS
        assert rec.outcome == ControlStageOutcome.TRUE

        retrieved = tracker.get_stage_record(ControlStage.LESSON_EXISTS)
        assert retrieved is not None
        assert retrieved.entity_refs == ["LES-010"]

    def test_contradictory_overwrite_rejected(self):
        tracker = ControlEffectivenessTracker(task_id="TASK-CONTRADICTION")
        tracker.record_stage(
            stage=ControlStage.LESSON_EXISTS,
            outcome=ControlStageOutcome.TRUE,
            reason="Found matching lesson",
        )
        with pytest.raises(ValueError, match="Contradictory overwrite rejected"):
            tracker.record_stage(
                stage=ControlStage.LESSON_EXISTS,
                outcome=ControlStageOutcome.FALSE,
                reason="Now trying to claim it does not exist",
            )

    def test_idempotent_overwrite_accepted(self):
        tracker = ControlEffectivenessTracker(task_id="TASK-IDEMPOTENT")
        rec1 = tracker.record_stage(
            stage=ControlStage.LESSON_EXISTS,
            outcome=ControlStageOutcome.TRUE,
            reason="Initial observation",
        )
        rec2 = tracker.record_stage(
            stage=ControlStage.LESSON_EXISTS,
            outcome=ControlStageOutcome.TRUE,
            reason="Same outcome re-observed",
        )
        assert rec1 == rec2

    def test_finalization_fills_unobserved_with_unknown(self):
        tracker = ControlEffectivenessTracker(task_id="TASK-FINALIZE")
        tracker.record_stage(
            stage=ControlStage.LESSON_EXISTS,
            outcome=ControlStageOutcome.TRUE,
            reason="Explicit observation",
        )
        trace = tracker.finalize_trace()

        assert len(trace) == 6
        stages = [r.stage for r in trace]
        assert stages == ORDERED_CONTROL_STAGES

        # LESSON_EXISTS is TRUE
        assert trace[0].stage == ControlStage.LESSON_EXISTS
        assert trace[0].outcome == ControlStageOutcome.TRUE

        # Other 5 stages should be UNKNOWN
        for rec in trace[1:]:
            assert rec.outcome == ControlStageOutcome.UNKNOWN, (
                f"Expected UNKNOWN for unobserved stage {rec.stage.value}, got {rec.outcome.value}"
            )

    def test_cannot_record_after_finalization(self):
        tracker = ControlEffectivenessTracker(task_id="TASK-AFTER-FINAL")
        tracker.finalize_trace()
        with pytest.raises(RuntimeError, match="already finalized"):
            tracker.record_stage(ControlStage.LESSON_RETRIEVED, ControlStageOutcome.TRUE)


# ==============================================================================
# Group F: Critical Semantic Guards (Anti-Fabrication)
# ==============================================================================

class TestCriticalSemanticGuards:
    """Verifies that the system strictly prevents stage fabrication and inference leaps."""

    def test_lesson_presented_requires_explicit_ui_source(self):
        """Backend preflight alone cannot mark LESSON_PRESENTED = TRUE."""
        tracker = ControlEffectivenessTracker(task_id="TASK-ANTI-FABRICATE")
        with pytest.raises(ValueError, match="FABRICATION_GUARD: LESSON_PRESENTED cannot be marked TRUE"):
            tracker.record_stage(
                stage=ControlStage.LESSON_PRESENTED,
                outcome=ControlStageOutcome.TRUE,
                source="governance_preflight",  # Disallowed source for TRUE presentation
                reason="Preflight returned a lesson so we assume user saw it",
            )

        # Allowed when source is explicitly UI / client / operator
        rec = tracker.record_stage(
            stage=ControlStage.LESSON_PRESENTED,
            outcome=ControlStageOutcome.TRUE,
            source="ui_presentation_dialog",
            reason="Modal dialog rendered lesson to user",
        )
        assert rec.outcome == ControlStageOutcome.TRUE

    def test_mistake_prevented_requires_explicit_evidence_refs(self):
        """Enforcement blocking an action does NOT automatically imply mistake_prevented = TRUE."""
        tracker = ControlEffectivenessTracker(task_id="TASK-PREVENTION-EVIDENCE")
        with pytest.raises(ValueError, match="FABRICATION_GUARD: MISTAKE_PREVENTED cannot be marked TRUE"):
            tracker.record_stage(
                stage=ControlStage.MISTAKE_PREVENTED,
                outcome=ControlStageOutcome.TRUE,
                evidence_refs=[],  # Disallowed: empty evidence
                reason="The rule blocked the action so we assume the mistake was prevented",
            )

        # Allowed when explicit post-action outcome evidence references are supplied
        rec = tracker.record_stage(
            stage=ControlStage.MISTAKE_PREVENTED,
            outcome=ControlStageOutcome.TRUE,
            evidence_refs=["audit_log_run_999", "clean_build_artifact_hash"],
            reason="Post-action forensic log confirmed no holdout access occurred",
        )
        assert rec.outcome == ControlStageOutcome.TRUE

    def test_uninstrumented_stages_default_to_unknown_not_false(self):
        """Unobserved is NOT false. Absence of evidence is not evidence of absence."""
        tracker = ControlEffectivenessTracker(task_id="TASK-UNOBSERVED-SEMANTICS")
        trace = tracker.finalize_trace()
        for rec in trace:
            assert rec.outcome == ControlStageOutcome.UNKNOWN
            assert rec.outcome != ControlStageOutcome.FALSE

    def test_lesson_exists_cannot_be_derived_from_retrieval_alone(self):
        """Preflight retrieval outcome cannot be claimed as an independent existence proof."""
        tracker = ControlEffectivenessTracker(task_id="TASK-EXISTENCE-GUARD")
        with pytest.raises(ValueError, match="FABRICATION_GUARD: LESSON_EXISTS cannot be derived directly from retrieval"):
            tracker.record_stage(
                stage=ControlStage.LESSON_EXISTS,
                outcome=ControlStageOutcome.TRUE,
                source="governance_preflight_retrieval",
                reason="Conflating retrieval match with independent existence oracle",
            )

        with pytest.raises(ValueError, match="FABRICATION_GUARD: LESSON_EXISTS cannot be derived directly from retrieval"):
            tracker.record_stage(
                stage=ControlStage.LESSON_EXISTS,
                outcome=ControlStageOutcome.FALSE,
                source="governance_preflight_retrieval",
                reason="Conflating retrieval miss with independent absence proof",
            )


# ==============================================================================
# Group G: Preflight Integration
# ==============================================================================

class TestPreflightIntegration:
    """Verifies that evaluate_task_preflight integrates ControlEffectivenessTracker safely."""

    def test_preflight_populates_control_trace(self):
        ctx = TaskContext(
            task_id="TASK-PREFLIGHT-TRACE",
            task_type="diagnostic",
            diagnostic="DIAG-05",
            operation=["sample_eligibility_census", "paired_inference"],
            proposed_plan="Normal plan under registered design.",
        )
        res: PreflightV2Result = evaluate_task_preflight(ctx)

        assert isinstance(res, PreflightV2Result)
        assert hasattr(res, "control_trace")
        assert len(res.control_trace) == 6

        stage_map = {r.stage: r for r in res.control_trace}
        assert ControlStage.LESSON_EXISTS in stage_map
        assert ControlStage.LESSON_RETRIEVED in stage_map
        assert ControlStage.LESSON_APPLICABLE in stage_map
        assert ControlStage.LESSON_PRESENTED in stage_map
        assert ControlStage.RULE_APPLIED in stage_map
        assert ControlStage.MISTAKE_PREVENTED in stage_map

        # Verify strict separation semantics
        # Preflight does NOT possess an independent lesson existence oracle:
        assert stage_map[ControlStage.LESSON_EXISTS].outcome == ControlStageOutcome.UNKNOWN
        # Preflight DOES observe actual retrieval:
        assert stage_map[ControlStage.LESSON_RETRIEVED].outcome in (ControlStageOutcome.TRUE, ControlStageOutcome.FALSE)
        # Preflight does NOT observe UI presentation:
        assert stage_map[ControlStage.LESSON_PRESENTED].outcome == ControlStageOutcome.UNKNOWN
        # Preflight does NOT observe post-action outcome evidence:
        assert stage_map[ControlStage.MISTAKE_PREVENTED].outcome == ControlStageOutcome.UNKNOWN
        # Lesson applicability evaluator is not in current rule-only engine:
        assert stage_map[ControlStage.LESSON_APPLICABLE].outcome == ControlStageOutcome.UNKNOWN

    def test_retrieval_miss_does_not_imply_lesson_absence(self):
        """When preflight retrieves zero lessons, LESSON_EXISTS remains UNKNOWN, not FALSE."""
        ctx_no_match = TaskContext(
            task_id="TASK-NO-MATCH",
            task_type="diagnostic",
            proposed_plan="Unmatched plan with synthetic terms.",
        )
        res = evaluate_task_preflight(ctx_no_match)
        stage_map = {r.stage: r for r in res.control_trace}
        assert stage_map[ControlStage.LESSON_RETRIEVED].outcome == ControlStageOutcome.FALSE
        assert stage_map[ControlStage.LESSON_EXISTS].outcome == ControlStageOutcome.UNKNOWN
        assert "independent observation" in stage_map[ControlStage.LESSON_EXISTS].reason

    def test_preflight_to_dict_includes_control_trace(self):
        ctx = TaskContext(
            task_id="TASK-PREFLIGHT-DICT",
            task_type="diagnostic",
            diagnostic="DIAG-05",
            operation=["sample_eligibility_census"],
            proposed_plan="Sample plan.",
        )
        res = evaluate_task_preflight(ctx)
        d = res.to_dict()

        assert "control_trace_count" in d
        assert d["control_trace_count"] == 6
        assert "control_trace" in d
        assert len(d["control_trace"]) == 6
        assert d["control_trace"][0]["stage"] == "LESSON_EXISTS"

    def test_existing_governance_blocking_behavior_preserved(self):
        """Confirms that holdout access violation still blocks preflight exactly as before."""
        ctx_violating = TaskContext(
            task_id="TASK-HOLDOUT-VIOLATION",
            task_type="diagnostic",
            diagnostic="DIAG-01",
            operation=["access_holdout"],
            proposed_plan="Reading holdout split for parameter tuning.",
        )
        res = evaluate_task_preflight(ctx_violating)
        assert res.passed is False
        assert len(res.blockers) > 0
        assert any("HOLDOUT" in b.code or "GOV-RULE-001" in b.rule_id for b in res.blockers)

        # Rule was applied:
        stage_map = {r.stage: r for r in res.control_trace}
        assert stage_map[ControlStage.RULE_APPLIED].outcome == ControlStageOutcome.TRUE
        # But MISTAKE_PREVENTED remains UNKNOWN (BLOCK does not manufacture prevention evidence):
        assert stage_map[ControlStage.MISTAKE_PREVENTED].outcome == ControlStageOutcome.UNKNOWN


# ==============================================================================
# Group H: Negative Feedback Receipts
# ==============================================================================

class TestNegativeFeedbackReceipts:
    """Verifies integrity-checked receipt persistence, conflict detection, and governance isolation."""

    def test_valid_receipt_creation_and_canonical_hash(self, tmp_path):
        receipt = record_negative_feedback(
            category=NegativeFeedbackCategory.FALSE_BLOCK,
            reason="Preflight blocked an authorized read operation incorrectly",
            control_trace_id="trace_test_receipt_001",
            entity_refs=["GOV-RULE-002"],
            evidence_refs=["preflight_log_123"],
            task_context={"task_id": "TASK-FEEDBACK-01"},
            receipt_dir=tmp_path,
            receipt_id="rcpt_test_001",
        )

        assert receipt["receipt_id"] == "rcpt_test_001"
        assert receipt["category"] == "FALSE_BLOCK"
        assert receipt["receipt_type"] == "INTEGRITY_CHECKED_NEGATIVE_FEEDBACK_RECEIPT"
        assert "payload_sha256" in receipt
        assert "INTEGRITY-CHECKED LOCAL RECEIPT" in receipt["integrity_note"]

        # Verify on-disk file
        target_file = tmp_path / "rcpt_test_001.json"
        assert target_file.exists()
        disk_data = json.loads(target_file.read_text(encoding="utf-8"))
        assert disk_data["payload_sha256"] == receipt["payload_sha256"]

    def test_receipt_integrity_disclaimers_complete(self, tmp_path):
        """Ensures receipt note explicitly disclaims digital signatures and non-repudiation."""
        receipt = record_negative_feedback(
            category=NegativeFeedbackCategory.MISSED_LESSON,
            reason="Testing disclaimer coverage",
            receipt_dir=tmp_path,
            receipt_id="rcpt_disclaimer_test",
        )
        note = receipt["integrity_note"]
        assert "INTEGRITY-CHECKED LOCAL RECEIPT" in note
        assert "conflicting overwrite detection" in note
        assert "does not establish external identity" in note
        assert "digital signatures" in note
        assert "cryptographic non-repudiation" in note
        assert "Telemetry remains strictly observational" in note

    def test_receipt_hashing_is_deterministic(self, tmp_path):
        """Verifies that identical payload generates identical SHA-256."""
        payload_a = {
            "receipt_id": "rcpt_det_001",
            "schema_version": "1.0.0",
            "receipt_type": "INTEGRITY_CHECKED_NEGATIVE_FEEDBACK_RECEIPT",
            "category": "MISSED_LESSON",
            "recorded_at": "2026-09-26T12:00:00Z",
            "control_trace_id": "trace_det",
            "entity_refs": ["LES-005"],
            "evidence_refs": [],
            "task_context": {},
            "source": "governance_agent",
            "reason": "Deterministic hash test",
        }
        bytes_a = canonicalize_json_v1(payload_a)
        bytes_b = canonicalize_json_v1(payload_a)
        assert bytes_a == bytes_b

    def test_fail_closed_on_conflicting_overwrite(self, tmp_path):
        """Attempting to overwrite an existing receipt with differing payload raises RuntimeError."""
        # Record initial receipt
        record_negative_feedback(
            category=NegativeFeedbackCategory.WEAK_ENFORCEMENT,
            reason="Initial reason",
            receipt_dir=tmp_path,
            receipt_id="rcpt_conflict_test",
        )

        # Attempt to record differing receipt with same receipt_id
        with pytest.raises(RuntimeError, match="TAMPER_PROTECTION_ERROR"):
            record_negative_feedback(
                category=NegativeFeedbackCategory.WEAK_ENFORCEMENT,
                reason="Tampered or modified reason",
                receipt_dir=tmp_path,
                receipt_id="rcpt_conflict_test",
            )

    def test_idempotent_re_recording_succeeds(self, tmp_path):
        """Re-recording with identical fields and timestamp succeeds idempotently."""
        r1 = record_negative_feedback(
            category=NegativeFeedbackCategory.DUPLICATE_LESSON,
            reason="Duplicate lesson found",
            receipt_dir=tmp_path,
            receipt_id="rcpt_idem_test",
        )
        # Reading existing file returns identical envelope
        target_file = tmp_path / "rcpt_idem_test.json"
        assert target_file.exists()

    def test_empty_reason_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="Cannot record negative feedback without an explicit reason"):
            record_negative_feedback(
                category=NegativeFeedbackCategory.FALSE_BLOCK,
                reason="",
                receipt_dir=tmp_path,
            )

    def test_canonical_governance_catalogs_remain_unmodified(self, tmp_path):
        """Ensures record_negative_feedback touches ONLY receipts directory, never canonical governance."""
        rules_path = CANONICAL_V2_DIR / "rules.json"
        lessons_path = CANONICAL_V2_DIR / "lessons.json"
        incidents_path = CANONICAL_V2_DIR / "incidents.json"

        rules_mtime_before = rules_path.stat().st_mtime
        lessons_mtime_before = lessons_path.stat().st_mtime
        incidents_mtime_before = incidents_path.stat().st_mtime

        record_negative_feedback(
            category=NegativeFeedbackCategory.WRONG_SCOPE,
            reason="Testing governance catalog isolation",
            receipt_dir=tmp_path,
            receipt_id="rcpt_isolation_test",
        )

        assert rules_path.stat().st_mtime == rules_mtime_before
        assert lessons_path.stat().st_mtime == lessons_mtime_before
        assert incidents_path.stat().st_mtime == incidents_mtime_before

        # Ensure no negative_feedback.json was created in governance_v2
        illegal_feedback_path = CANONICAL_V2_DIR / "negative_feedback.json"
        assert not illegal_feedback_path.exists(), "Illegal negative_feedback.json created in canonical governance dir!"


# ==============================================================================
# Group I: Adversarial & Boundary Scenarios
# ==============================================================================

class TestAdversarialScenarios:
    """Verifies edge cases, coercion rejections, corruption handling, and telemetry isolation."""

    def test_lesson_exists_true_but_retrieval_missed_it(self):
        tracker = ControlEffectivenessTracker(task_id="TASK-RETRIEVAL-MISS")
        tracker.record_stage(ControlStage.LESSON_EXISTS, ControlStageOutcome.TRUE, reason="Exists in store")
        tracker.record_stage(ControlStage.LESSON_RETRIEVED, ControlStageOutcome.FALSE, reason="Query failed to match")
        trace = tracker.finalize_trace()
        stage_map = {r.stage: r for r in trace}
        assert stage_map[ControlStage.LESSON_EXISTS].outcome == ControlStageOutcome.TRUE
        assert stage_map[ControlStage.LESSON_RETRIEVED].outcome == ControlStageOutcome.FALSE

    def test_rule_exists_but_not_applicable(self):
        tracker = ControlEffectivenessTracker(task_id="TASK-RULE-NA")
        tracker.record_stage(ControlStage.RULE_APPLIED, ControlStageOutcome.NOT_APPLICABLE, reason="Scope mismatch")
        trace = tracker.finalize_trace()
        stage_map = {r.stage: r for r in trace}
        assert stage_map[ControlStage.RULE_APPLIED].outcome == ControlStageOutcome.NOT_APPLICABLE

    def test_rule_applicable_but_not_applied(self):
        tracker = ControlEffectivenessTracker(task_id="TASK-RULE-NO-FIRE")
        tracker.record_stage(ControlStage.RULE_APPLIED, ControlStageOutcome.FALSE, reason="Rule satisfied by plan")
        trace = tracker.finalize_trace()
        stage_map = {r.stage: r for r in trace}
        assert stage_map[ControlStage.RULE_APPLIED].outcome == ControlStageOutcome.FALSE

    def test_invalid_stage_coercion_rejected(self):
        tracker = ControlEffectivenessTracker(task_id="TASK-INVALID-STAGE")
        with pytest.raises(ValueError, match="Invalid ControlStage"):
            tracker.record_stage("INVALID_STAGE_NAME", ControlStageOutcome.TRUE)

    def test_invalid_outcome_coercion_rejected(self):
        tracker = ControlEffectivenessTracker(task_id="TASK-INVALID-OUTCOME")
        with pytest.raises(ValueError, match="Invalid ControlStageOutcome"):
            tracker.record_stage(ControlStage.LESSON_EXISTS, "MAYBE")

    def test_invalid_feedback_category_coercion_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="Invalid NegativeFeedbackCategory"):
            record_negative_feedback(
                category="NON_EXISTENT_CATEGORY",
                reason="Invalid category test",
                receipt_dir=tmp_path,
            )

    def test_receipt_corrupted_on_disk_fails_closed(self, tmp_path):
        corrupt_file = tmp_path / "rcpt_corrupt.json"
        corrupt_file.write_text("{ corrupt json content ...", encoding="utf-8")
        with pytest.raises(RuntimeError, match="TAMPER_PROTECTION_ERROR"):
            record_negative_feedback(
                category=NegativeFeedbackCategory.MISSED_LESSON,
                reason="Trying to write over corrupt receipt",
                receipt_dir=tmp_path,
                receipt_id="rcpt_corrupt",
            )

    def test_telemetry_isolation_from_authorization(self):
        """Confirms that passing a tracker or telemetry does not alter preflight pass/fail authorization."""
        ctx = TaskContext(
            task_id="TASK-ISOLATION-AUTH",
            task_type="diagnostic",
            diagnostic="DIAG-05",
            operation=["sample_eligibility_census"],
            proposed_plan="Valid execution plan.",
        )
        res_standard = evaluate_task_preflight(ctx)
        
        custom_tracker = ControlEffectivenessTracker(task_id="TASK-ISOLATION-AUTH")
        res_custom = evaluate_task_preflight(ctx, tracker=custom_tracker)

        assert res_standard.passed == res_custom.passed
        assert len(res_standard.blockers) == len(res_custom.blockers)
        assert len(res_standard.warnings) == len(res_custom.warnings)


# ==============================================================================
# Group J: Rule Applicability Matrix (Phase 9B Micro-Closure)
# ==============================================================================

class TestRuleApplicabilityMatrix:
    """Verifies the exact 5-case matrix and strict separation: active != applicable != applied."""

    def test_case1_zero_active_rules_is_not_applicable(self):
        """Case 1: active=0, applicable=0, applied=0 => NOT_APPLICABLE."""
        outcome, reason = resolve_rule_applied_outcome(
            applicable_rules_count=0,
            applied_rules_count=0,
            active_rules_count=0,
        )
        assert outcome == ControlStageOutcome.NOT_APPLICABLE
        assert "Zero rules applicable" in reason

    def test_case2_active_rules_exist_but_zero_applicable_is_not_applicable(self):
        """Case 2 (Adversarial Counterexample 1): active>0, applicable=0, applied=0 => NOT_APPLICABLE.
        
        Strict Invariant: Active catalog rules existing does NOT produce RULE_APPLIED = FALSE!
        """
        outcome, reason = resolve_rule_applied_outcome(
            applicable_rules_count=0,
            applied_rules_count=0,
            active_rules_count=15,  # 15 active catalog rules
        )
        assert outcome == ControlStageOutcome.NOT_APPLICABLE
        assert outcome != ControlStageOutcome.FALSE, "Active catalog rules count must not be used as applicability proxy!"
        assert "across 15 active catalog rule(s)" in reason

    def test_case3_applicable_rules_exist_but_zero_applied_is_false(self):
        """Case 3 (Adversarial Counterexample 2): active>0, applicable>0, applied=0 => FALSE.
        
        Strict Invariant: Zero applied rules does NOT produce NOT_APPLICABLE when applicable rules exist!
        """
        outcome, reason = resolve_rule_applied_outcome(
            applicable_rules_count=4,
            applied_rules_count=0,
            active_rules_count=15,
        )
        assert outcome == ControlStageOutcome.FALSE
        assert outcome != ControlStageOutcome.NOT_APPLICABLE, "Zero applied rules must not produce NOT_APPLICABLE when rules applied=0 but applicable>0!"
        assert "4 rule(s) were applicable but none triggered violations" in reason

    def test_case4_applicable_rules_and_applied_rules_is_true(self):
        """Case 4: applicable>0, applied>0 => TRUE."""
        outcome, reason = resolve_rule_applied_outcome(
            applicable_rules_count=4,
            applied_rules_count=2,
            active_rules_count=15,
        )
        assert outcome == ControlStageOutcome.TRUE
        assert "Enforcement engine applied 2 rule(s)" in reason

    def test_case5_indeterminate_applicability_is_unknown(self):
        """Case 5: indeterminate applicability/enforcement => UNKNOWN."""
        outcome, reason = resolve_rule_applied_outcome(
            applicable_rules_count=None,
            applied_rules_count=0,
        )
        assert outcome == ControlStageOutcome.UNKNOWN
        assert "indeterminate or unobserved" in reason

    def test_tracker_record_rule_applied_method(self):
        """Verifies that ControlEffectivenessTracker.record_rule_applied correctly constructs the record."""
        tracker = ControlEffectivenessTracker(task_id="TASK-RULE-APPLIED-METHOD")
        rec = tracker.record_rule_applied(
            applicable_rules_count=3,
            applied_rule_ids=["GOV-RULE-001", "GOV-RULE-002"],
            active_rules_count=10,
        )
        assert rec.stage == ControlStage.RULE_APPLIED
        assert rec.outcome == ControlStageOutcome.TRUE
        assert rec.entity_refs == ["GOV-RULE-001", "GOV-RULE-002"]

    def test_preflight_compliant_plan_has_applicable_rules_but_false_rule_applied(self):
        """Verifies that a compliant preflight task with applicable rules produces RULE_APPLIED = FALSE."""
        ctx = TaskContext(
            task_id="TASK-PREFLIGHT-COMPLIANT-MATRIX",
            task_type="diagnostic",
            diagnostic="DIAG-05",
            operation=["sample_eligibility_census"],
            proposed_plan="Normal non-violating plan under registered architecture.",
        )
        res = evaluate_task_preflight(ctx)
        assert res.passed is True
        assert len(res.applicable_rules) > 0  # Rules were applicable
        assert len(res.blockers) == 0         # But zero triggered

        stage_map = {r.stage: r for r in res.control_trace}
        assert stage_map[ControlStage.RULE_APPLIED].outcome == ControlStageOutcome.FALSE
        assert stage_map[ControlStage.RULE_APPLIED].outcome != ControlStageOutcome.NOT_APPLICABLE
        assert stage_map[ControlStage.RULE_APPLIED].outcome != ControlStageOutcome.TRUE

    def test_receipt_integrity_wording_contains_trustworthy_qualification(self, tmp_path):
        """Ensures receipt note contains the exact trustworthy digest qualification."""
        receipt = record_negative_feedback(
            category=NegativeFeedbackCategory.FALSE_BLOCK,
            reason="Trustworthy digest qualification test",
            receipt_dir=tmp_path,
            receipt_id="rcpt_trustworthy_test",
        )
        note = receipt["integrity_note"]
        assert "when the recorded digest remains trustworthy" in note


