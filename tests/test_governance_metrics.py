"""Adversarial and Contract Tests for Governance Metrics & Trace Analytics (Phase 10).

Covers all 28 mandatory adversarial semantic boundaries:
1. missing oracle -> UNKNOWN / INSUFFICIENT_DATA
2. zero denominator -> never division-by-zero or fabricated zero
3. empty retrieved set with known zero relevant population -> mathematically valid result
4. retrieval miss != lesson absence
5. block != prevention
6. block != false-block
7. active rules != applicable rules
8. applicable rules != applied rules
9. repeated receipt ID with identical content -> deterministic/idempotent handling
10. repeated receipt ID with conflicting content -> fail closed
11. corrupted digest -> reject/quarantine
12. malformed receipt schema -> reject/quarantine
13. unknown feedback category -> reject
14. duplicate event records -> deterministic deduplication
15. missing timestamps -> no fabricated recurrence ordering
16. missing failure-class identity -> recurrence remains INSUFFICIENT_DATA (completeness guard)
17. missing staleness threshold -> report age but do not fabricate stale/not-stale classification
18. backend retrieval -> presentation remains UNKNOWN without explicit client event
19. synthetic fixtures remain visibly isolated from real measurements
20. metric output is deterministic across repeated runs
21. canonical governance catalogs remain untouched
22. telemetry remains observational
23. metric engine cannot mutate authorization decisions
24. metric engine cannot promote lessons/rules
25. report numbers reconcile exactly with raw counts
26. citation frequency distinguishes rule catalog population from trace batch population
27. status taxonomy bounds and zero-fabrication guarantees (MEASURED does not universally require oracle)
28. integrity detection precision wording, fail-closed conflicting overwrite, and anti-overclaiming guards.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pytest
from typing import Any, Dict, List

from ocean_sentinel.governance.control import (
    ControlEffectivenessTracker,
    ORDERED_CONTROL_STAGES,
    record_negative_feedback,
)
from ocean_sentinel.governance.interface import evaluate_task_preflight
from ocean_sentinel.governance.metrics import (
    ConflictingReceiptError,
    compute_catalog_rule_citation_frequency,
    compute_citation_frequency,
    compute_false_block_rate,
    compute_lesson_staleness,
    compute_receipt_ingestion_summary,
    compute_receipt_validation_pass_rate,
    compute_recurrence_rate,
    compute_recurring_failure_class_prevalence,
    compute_retrieval_precision,
    compute_retrieval_recall,
    compute_trace_citation_frequency,

    compute_ui_presentation_rate,
    evaluate_offline_batch,
    ingest_negative_feedback_receipts,
)
from ocean_sentinel.governance.models import (
    ActionType,
    AdjudicatedTaskRecord,
    ClientPresentationEvent,
    ControlStage,
    ControlStageOutcome,
    ControlTraceRecord,
    Lesson,
    MetricEvaluationBatch,
    MetricResult,
    MetricStatus,
    NegativeFeedbackCategory,
    PreflightIssueV2,
    PreflightV2Result,
    Rule,
    ScopeLevel,
    SeverityLevel,
    TaskContext,
    ValidationRecord,
)
from ocean_sentinel.governance.provenance import canonicalize_json_v1
from ocean_sentinel.governance.store import GovernanceStore

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_V2_DIR = REPO_ROOT / "data" / "metadata" / "governance_v2"
SYNTHETIC_MARKER = "SYNTHETIC_TEST_FIXTURE_ONLY"


# ==============================================================================
# Group A: Retrieval Recall & Precision Boundary Tests (Items 1, 2, 3, 4)
# ==============================================================================

class TestRetrievalMetricsBoundaries:
    """Verifies retrieval recall and precision boundaries against zero fabrication."""

    def test_01_missing_oracle_yields_insufficient_data(self):
        """1. missing oracle -> UNKNOWN / INSUFFICIENT_DATA (never 0.0)."""
        # Tasks with retrieved lessons but NO ground truth relevance annotations
        synthetic_tasks = [
            AdjudicatedTaskRecord(
                task_id="SYNTH-TASK-001",
                task_context={"retrieved_lesson_ids": ["LL-001", "LL-002"]},
                ground_truth_relevant_lesson_ids=None,  # Missing oracle/labels
                notes=SYNTHETIC_MARKER,
            )
        ]
        recall = compute_retrieval_recall(synthetic_tasks)
        assert recall.status == MetricStatus.INSUFFICIENT_DATA
        assert recall.value is None, "Missing oracle must yield value=None, not 0.0"

        precision = compute_retrieval_precision(synthetic_tasks)
        assert precision.status == MetricStatus.INSUFFICIENT_DATA
        assert precision.value is None, "Missing oracle must yield value=None, not 0.0"

        # Explicit None retrieved_lesson_ids safely handled without TypeError
        task_with_none_ret = AdjudicatedTaskRecord(
            task_id="SYNTH-TASK-NONE-RET",
            task_context={"retrieved_lesson_ids": None},
            ground_truth_relevant_lesson_ids=["LL-001"],
            notes=SYNTHETIC_MARKER,
        )
        rec_none = compute_retrieval_recall([task_with_none_ret])
        assert rec_none.status == MetricStatus.MEASURED
        assert rec_none.value == 0.0

    def test_02_zero_denominator_never_divides_by_zero_or_fabricates_zero(self):
        """2. zero denominator -> never division-by-zero or fabricated zero."""
        empty_tasks: List[AdjudicatedTaskRecord] = []
        recall = compute_retrieval_recall(empty_tasks)
        assert recall.status == MetricStatus.INSUFFICIENT_DATA
        assert recall.value is None

        precision = compute_retrieval_precision(empty_tasks)
        assert precision.status == MetricStatus.INSUFFICIENT_DATA
        assert precision.value is None

    def test_03_empty_retrieved_set_with_zero_relevant_population_yields_not_applicable(self):
        """3. empty retrieved set with known zero relevant population -> mathematically valid result."""
        # Ground truth explicitly asserts 0 relevant lessons exist
        synthetic_tasks = [
            {
                "task_id": "SYNTH-TASK-002",
                "ground_truth_relevant_lesson_ids": [],
                "retrieved_lesson_ids": [],
                "notes": SYNTHETIC_MARKER,
            }
        ]
        # Recall when total relevant is zero
        recall = compute_retrieval_recall(synthetic_tasks)
        assert recall.status == MetricStatus.NOT_APPLICABLE
        assert recall.value is None
        assert recall.numerator == 0
        assert recall.denominator == 0

        # Precision when total retrieved is zero
        precision = compute_retrieval_precision(synthetic_tasks)
        assert precision.status == MetricStatus.NOT_APPLICABLE
        assert precision.value is None

    def test_04_retrieval_miss_does_not_imply_lesson_absence(self):
        """4. retrieval miss != lesson absence.
        
        A lesson may exist in the catalog even if the retrieval engine missed it.
        """
        catalog_lessons = [
            Lesson(
                lesson_id="LL-EXP07-001",
                title="Synthetic catalog lesson",
                principle_id="PRIN-001",
                failure_class="DATA-INTEGRITY",
                severity=SeverityLevel.HIGH,
                scope=ScopeLevel.GLOBAL,
                description=SYNTHETIC_MARKER,
                root_cause="test",
                incorrect_behavior="test",
                correct_rule="test",
                prevention_method="test",
            )
        ]
        # Task context that retrieves nothing
        task_record = AdjudicatedTaskRecord(
            task_id="SYNTH-TASK-003",
            task_context={"retrieved_lesson_ids": []},
            ground_truth_relevant_lesson_ids=["LL-EXP07-001"],  # Lesson exists and was relevant!
            notes=SYNTHETIC_MARKER,
        )
        recall = compute_retrieval_recall([task_record])
        assert recall.status == MetricStatus.MEASURED
        assert recall.value == 0.0
        assert recall.numerator == 0
        assert recall.denominator == 1
        # Proves lesson existed in ground truth despite zero retrieval
        assert len(catalog_lessons) == 1
        assert catalog_lessons[0].lesson_id in task_record.ground_truth_relevant_lesson_ids


# ==============================================================================
# Group B: False-Block & Control Semantics (Items 5, 6, 7, 8)
# ==============================================================================

class TestControlSemanticsAndFalseBlock:
    """Verifies critical distinctions: block != prevention, block != false-block, active != applicable != applied."""

    def test_05_block_does_not_equal_mistake_prevented(self):
        """5. block != prevention.
        
        A preflight block is a control enforcement action, not empirical proof that a mistake was averted.
        """
        tracker = ControlEffectivenessTracker(task_id="test_05")
        tracker.record_stage(
            stage=ControlStage.RULE_APPLIED,
            outcome=ControlStageOutcome.TRUE,
            reason="Violation detected; action BLOCK emitted",
            entity_refs=["GOV-RULE-001"],
            source="test_05",
        )
        trace = tracker.finalize_trace()
        rule_applied_rec = next(r for r in trace if r.stage == ControlStage.RULE_APPLIED)
        prevented_rec = next(r for r in trace if r.stage == ControlStage.MISTAKE_PREVENTED)

        assert rule_applied_rec.outcome == ControlStageOutcome.TRUE
        # Mistake prevented remains UNKNOWN without post-execution causal evidence
        assert prevented_rec.outcome == ControlStageOutcome.UNKNOWN
        assert rule_applied_rec.outcome != prevented_rec.outcome

    def test_06_block_does_not_equal_false_block_without_adjudication(self):
        """6. block != false-block.
        
        BLOCK status or user complaint alone cannot be treated as a false block without verified adjudication.
        """
        unadjudicated_task = AdjudicatedTaskRecord(
            task_id="SYNTH-TASK-004",
            preflight_passed=False,  # Blocked!
            is_block_accurate=None,  # No correctness adjudication
            notes=SYNTHETIC_MARKER,
        )
        fb_rate = compute_false_block_rate([unadjudicated_task])
        assert fb_rate.status == MetricStatus.INSUFFICIENT_DATA
        assert fb_rate.value is None, "Unadjudicated block must not be inferred as false block"

        # Adjudicated legitimate block
        legit_block = AdjudicatedTaskRecord(
            task_id="SYNTH-TASK-005",
            preflight_passed=False,
            is_block_accurate=True,  # Block was correct!
            notes=SYNTHETIC_MARKER,
        )
        fb_legit = compute_false_block_rate([legit_block])
        assert fb_legit.status == MetricStatus.MEASURED
        assert fb_legit.value == 0.0, "Legitimate block has false-block rate of 0.0"

        # Adjudicated false block
        false_block = AdjudicatedTaskRecord(
            task_id="SYNTH-TASK-006",
            preflight_passed=False,
            is_block_accurate=False,  # Verified incorrect block!
            notes=SYNTHETIC_MARKER,
        )
        fb_false = compute_false_block_rate([false_block])
        assert fb_false.status == MetricStatus.MEASURED
        assert fb_false.value == 1.0, "Verified false block has rate of 1.0"

    def test_07_active_rules_differ_from_applicable_rules(self):
        """7. active rules != applicable rules.
        
        Active rules in catalog do not automatically apply to an arbitrary task context.
        """
        store = GovernanceStore.get_instance()
        active_rules = store.list_rules()
        assert len(active_rules) > 10, "Store must contain active rules"

        # Task context with narrow scope
        narrow_context = TaskContext(
            task_id="SYNTH-TASK-007",
            domain=["irrelevant_domain"],
            operation=["benign_read_only_action"],
            risk_class=["minimal"],
        )
        preflight_res = evaluate_task_preflight(narrow_context)
        # Applicable rules is a strict subset of active rules
        assert len(preflight_res.applicable_rules) < len(active_rules)

    def test_08_applicable_rules_differ_from_applied_rules(self):
        """8. applicable rules != applied rules.
        
        A rule may be applicable to a context, but if no violation is triggered, RULE_APPLIED is FALSE.
        """
        store = GovernanceStore.get_instance()
        # Find a rule with non-empty required_checks or prohibited_actions
        rule = next(r for r in store.list_rules() if r.prohibited_actions)
        
        # Construct benign context matching rule applicability but NOT violating prohibited action
        benign_context = TaskContext(
            task_id="SYNTH-TASK-008",
            domain=["scientific"],
            operation=["benign_valid_operation"],
            risk_class=["low"],
            proposed_plan="Valid clean operation following standard procedure",
        )
        preflight_res = evaluate_task_preflight(benign_context)
        trace = preflight_res.control_trace
        rule_applied_trace = next(r for r in trace if r.stage == ControlStage.RULE_APPLIED)
        
        # When applicable rules exist but none violated, RULE_APPLIED is FALSE (or NOT_APPLICABLE if none applicable)
        assert rule_applied_trace.outcome in (ControlStageOutcome.FALSE, ControlStageOutcome.NOT_APPLICABLE)


# ==============================================================================
# Group C: Receipt Ingestion, Integrity & Conflict Handling (Items 9, 10, 11, 12, 13, 14)
# ==============================================================================

class TestReceiptIngestionAndIntegrity:
    """Verifies receipt schema, SHA-256 verification, fail-closed conflicts, and deduplication."""

    def test_09_repeated_receipt_id_with_identical_content_is_idempotent(self, tmp_path):
        """9. repeated receipt ID with identical content -> deterministic/idempotent handling."""
        receipt = record_negative_feedback(
            category=NegativeFeedbackCategory.FALSE_BLOCK,
            reason="Synthetic test reason",
            receipt_dir=tmp_path,
            receipt_id="rcpt_ident_001",
            source=SYNTHETIC_MARKER,
        )
        # Ingest directory containing receipt, plus identical in-memory copy
        result = ingest_negative_feedback_receipts([tmp_path / "rcpt_ident_001.json", receipt])
        assert len(result["validated_records"]) == 1
        assert result["duplicate_count"] == 1
        assert result["conflict_count"] == 0

    def test_10_repeated_receipt_id_with_conflicting_content_fails_closed(self, tmp_path):
        """10. repeated receipt ID with conflicting content -> fail closed."""
        receipt_1 = record_negative_feedback(
            category=NegativeFeedbackCategory.FALSE_BLOCK,
            reason="First content version",
            receipt_dir=tmp_path,
            receipt_id="rcpt_conflict_001",
            source=SYNTHETIC_MARKER,
        )
        # Construct conflicting receipt with same ID but different payload
        conflicting_payload = dict(receipt_1)
        conflicting_payload["reason"] = "Mutated conflicting reason"
        # Recompute differing SHA
        raw_core = {k: v for k, v in conflicting_payload.items() if k not in ("payload_sha256", "integrity_note")}
        conflicting_payload["payload_sha256"] = hashlib.sha256(canonicalize_json_v1(raw_core)).hexdigest()

        # Ingestion must fail closed by raising ConflictingReceiptError
        with pytest.raises(ConflictingReceiptError):
            ingest_negative_feedback_receipts([receipt_1, conflicting_payload], fail_closed_on_conflict=True)

        # In non-fatal quarantine mode, both or conflicting record must be quarantined
        res = ingest_negative_feedback_receipts([receipt_1, conflicting_payload], fail_closed_on_conflict=False)
        assert res["conflict_count"] == 1
        assert any("CONFLICTING_DUPLICATE" in q["quarantine_reason"] for q in res["quarantined_records"])

    def test_11_corrupted_digest_is_quarantined(self):
        """11. corrupted digest -> reject/quarantine."""
        corrupted_receipt = {
            "receipt_id": "rcpt_corrupted_001",
            "schema_version": "1.0.0",
            "category": "FALSE_BLOCK",
            "recorded_at": "2026-09-26T12:00:00Z",
            "reason": "Legitimate reason",
            "payload_sha256": "0000000000000000000000000000000000000000000000000000000000000000",  # Fake digest!
            "source": SYNTHETIC_MARKER,
        }
        res = ingest_negative_feedback_receipts([corrupted_receipt])
        assert len(res["validated_records"]) == 0
        assert len(res["quarantined_records"]) == 1
        assert "CORRUPTED_DIGEST_MISMATCH" in res["quarantined_records"][0]["quarantine_reason"]

    def test_12_malformed_receipt_schema_is_quarantined(self, tmp_path):
        """12. malformed receipt schema and unreadable candidate files are quarantined with denominator preserved."""
        malformed_records = [
            "{ bad json string ",
            {"missing_category": True, "reason": "No id"},
            {"receipt_id": "rcpt_no_reason", "schema_version": "1.0.0", "category": "FALSE_BLOCK", "recorded_at": "2026-09-26T12:00:00Z"},
        ]
        res = ingest_negative_feedback_receipts(malformed_records)
        assert len(res["validated_records"]) == 0
        assert len(res["quarantined_records"]) == 3
        assert res["total_candidates_encountered"] == 3
        pass_rate = compute_receipt_validation_pass_rate(res)
        assert pass_rate.denominator == 3
        assert pass_rate.numerator == 0
        assert pass_rate.value == 0.0
        assert "all negative-feedback receipt candidates encountered" in pass_rate.population_definition.lower()

        # Test unreadable candidate file in a receipt directory:
        rcpt_dir = tmp_path / "receipts_unreadable"
        rcpt_dir.mkdir()
        record_negative_feedback(
            category=NegativeFeedbackCategory.FALSE_BLOCK,
            reason="Legitimate feedback",
            receipt_dir=rcpt_dir,
            receipt_id="rcpt_valid_candidate_001",
            source=SYNTHETIC_MARKER,
        )
        # Write an unreadable binary corrupted candidate file
        corrupt_file = rcpt_dir / "corrupt_candidate.json"
        corrupt_file.write_bytes(b"\x80\xff\xfe\xfd\xaa\xbb")

        dir_res = ingest_negative_feedback_receipts(rcpt_dir)
        assert dir_res["total_candidates_encountered"] == 2
        assert dir_res["read_error_count"] == 1
        assert len(dir_res["validated_records"]) == 1
        assert any("READ_ERROR" in str(q.get("quarantine_reason", "")) for q in dir_res["quarantined_records"])

        dir_pass = compute_receipt_validation_pass_rate(dir_res)
        assert dir_pass.denominator == 2, "Unreadable candidate must remain in denominator"
        assert dir_pass.numerator == 1
        assert dir_pass.value == 0.5
        assert dir_pass.metadata["read_error_count"] == 1
        assert dir_pass.metadata["total_candidates_encountered"] == 2

    def test_13_unknown_feedback_category_is_rejected(self):
        """13. unknown feedback category -> reject."""
        invalid_cat_receipt = {
            "receipt_id": "rcpt_bad_cat_001",
            "schema_version": "1.0.0",
            "category": "INVALID_FABRICATED_CATEGORY",
            "recorded_at": "2026-09-26T12:00:00Z",
            "reason": "Test unknown category",
            "source": SYNTHETIC_MARKER,
        }
        res = ingest_negative_feedback_receipts([invalid_cat_receipt])
        assert len(res["validated_records"]) == 0
        assert len(res["quarantined_records"]) == 1
        assert "UNKNOWN_CATEGORY" in res["quarantined_records"][0]["quarantine_reason"]

        # Validate canonical receipt validation pass rate metric
        pass_res = compute_receipt_validation_pass_rate(res)
        assert pass_res.metric_id == "METRIC-RECEIPT-VALIDATION-PASS-RATE"
        assert pass_res.status == MetricStatus.MEASURED
        assert pass_res.value == 0.0
        assert pass_res.numerator == 0
        assert pass_res.denominator == 1
        assert pass_res.metadata["category_invalid_count"] == 1
        assert pass_res.metadata["metric_type"] == "VALIDATION_ACCEPTANCE_RATE"

        # Deprecated compatibility alias returns identical values with alias metadata
        alias_res = compute_receipt_ingestion_summary(res)
        assert alias_res.metric_id == "METRIC-RECEIPT-INGESTION-INTEGRITY"
        assert alias_res.value == 0.0
        assert alias_res.metadata["canonical_metric_id"] == "METRIC-RECEIPT-VALIDATION-PASS-RATE"

    def test_14_duplicate_event_records_deterministic_deduplication(self, tmp_path):
        """14. duplicate event records -> deterministic deduplication."""
        rcpt = record_negative_feedback(
            category=NegativeFeedbackCategory.MISSED_LESSON,
            reason="Deduplication test",
            receipt_dir=tmp_path,
            receipt_id="rcpt_dedup_001",
            source=SYNTHETIC_MARKER,
        )
        res = ingest_negative_feedback_receipts([rcpt, rcpt, rcpt])
        assert len(res["validated_records"]) == 1
        assert res["duplicate_count"] == 2

        # Validate pass rate computation on deduplicated set (1 unique admitted / 3 examined)
        pass_res = compute_receipt_validation_pass_rate(res)
        assert pass_res.metric_id == "METRIC-RECEIPT-VALIDATION-PASS-RATE"
        assert pass_res.status == MetricStatus.MEASURED
        assert pass_res.value == round(1 / 3, 4)
        assert pass_res.numerator == 1
        assert pass_res.denominator == 3
        assert pass_res.metadata["duplicate_count"] == 2



# ==============================================================================
# Group D: Recurrence, Staleness & Telemetry (Items 15, 16, 17, 18)
# ==============================================================================

class TestRecurrenceStalenessAndTelemetry:
    """Verifies recurrence temporal ordering, staleness threshold discipline, and UI telemetry bounds."""

    def test_15_missing_timestamps_precludes_fabricated_recurrence_ordering(self):
        """15. prevalence is computable over cohort without fabricating temporal ordering when timestamps are absent."""
        events_without_timestamps = [
            {"incident_id": "INC-001", "failure_class": "DATA-INTEGRITY", "timestamp": ""},
            {"incident_id": "INC-002", "failure_class": "DATA-INTEGRITY", "timestamp": None},
        ]
        rec_res = compute_recurring_failure_class_prevalence(events_without_timestamps)
        assert rec_res.status == MetricStatus.MEASURED
        assert rec_res.value == 1.0  # 1 recurrent failure class / 1 distinct failure class
        assert rec_res.numerator == 1
        assert rec_res.denominator == 1
        assert rec_res.metadata["metric_type"] == "STRUCTURAL_PREVALENCE"
        assert rec_res.metadata["temporal_provenance"] == "TIMESTAMPS_ABSENT"
        assert rec_res.metadata["temporal_scope"] == "COHORT_OBSERVATION_NON_TEMPORAL"

        # Also test backward-compatible alias and verify it is not treated as a temporal rate
        alias_res = compute_recurrence_rate(events_without_timestamps)
        assert alias_res.status == MetricStatus.MEASURED
        assert alias_res.value == 1.0
        assert alias_res.metric_id == "METRIC-RECURRING-FAILURE-CLASS-PREVALENCE"
        assert alias_res.metadata["metric_type"] == "STRUCTURAL_PREVALENCE"
        assert "DEPRECATED COMPATIBILITY ALIAS" in (compute_recurrence_rate.__doc__ or "")
        assert "not a temporal recurrence rate" in (compute_recurrence_rate.__doc__ or "")

    def test_16_missing_failure_class_identity_keeps_recurrence_unknown(self):
        """16. missing failure-class identity -> recurrence prevalence remains INSUFFICIENT_DATA."""
        events_without_fc = [
            {"incident_id": "INC-003", "failure_class": "", "timestamp": "2026-09-26T10:00:00Z"},
            {"incident_id": "INC-004", "failure_class": None, "timestamp": "2026-09-26T11:00:00Z"},
        ]
        rec_res = compute_recurring_failure_class_prevalence(events_without_fc)
        assert rec_res.status == MetricStatus.INSUFFICIENT_DATA
        assert rec_res.value is None
        assert rec_res.metadata["missing_fc_count"] == 2

        # Completeness Guard: Mixed classified + unclassified cohort must NOT silently discard unclassified
        mixed_events = [
            {"incident_id": "INC-005", "failure_class": "DATA-INTEGRITY"},
            {"incident_id": "INC-006", "failure_class": "DATA-INTEGRITY"},
            {"incident_id": "INC-007", "failure_class": None},  # unclassified
        ]
        mixed_res = compute_recurring_failure_class_prevalence(mixed_events)
        assert mixed_res.status == MetricStatus.INSUFFICIENT_DATA
        assert mixed_res.value is None
        assert mixed_res.metadata["missing_fc_count"] == 1
        assert mixed_res.metadata["cohort_scope"] == "INCOMPLETE_CLASSIFICATION"

        # Explicit prefiltered classified-only mode permitted when explicitly requested
        prefiltered_res = compute_recurring_failure_class_prevalence(
            mixed_events, allow_prefiltered_classified_only=True
        )
        assert prefiltered_res.status == MetricStatus.MEASURED
        assert prefiltered_res.value == 1.0
        assert prefiltered_res.metadata["cohort_scope"] == "PREFILTERED_CLASSIFIED_ONLY"


    def test_17_missing_staleness_threshold_reports_age_without_fabricating_classification(self):
        """17. missing staleness threshold -> report age but do not fabricate stale classification (INSUFFICIENT_DATA)."""
        lessons = [
            Lesson(
                lesson_id="LL-SYNTH-01",
                title="Lesson with validation history",
                principle_id="PRIN-001",
                failure_class="DATA-INTEGRITY",
                severity=SeverityLevel.MEDIUM,
                scope=ScopeLevel.PROJECT,
                description=SYNTHETIC_MARKER,
                root_cause="test",
                incorrect_behavior="test",
                correct_rule="test",
                prevention_method="test",
                validation_history=[
                    ValidationRecord(
                        task="SYNTH-TASK",
                        timestamp="2026-09-10T00:00:00Z",
                        test="test_x",
                        result="PASSED",
                    )
                ],
            )
        ]
        # Without threshold: status must be INSUFFICIENT_DATA, value=None, but age statistics reported
        stale_res = compute_lesson_staleness(lessons, stale_threshold_days=None)
        assert stale_res.status == MetricStatus.INSUFFICIENT_DATA
        assert stale_res.value is None
        assert "mean_days_since_validation" in stale_res.metadata
        assert stale_res.metadata["mean_days_since_validation"] is not None

        # When lesson cohort is empty: status must be NOT_APPLICABLE
        empty_res = compute_lesson_staleness([], stale_threshold_days=5.0)
        assert empty_res.status == MetricStatus.NOT_APPLICABLE
        assert empty_res.value is None

        # A. Normal historical timestamp:
        stale_res_with_policy = compute_lesson_staleness(
            lessons,
            reference_time=datetime(2026, 9, 26, 0, 0, 0, tzinfo=timezone.utc),
            stale_threshold_days=5.0,
        )
        assert stale_res_with_policy.status == MetricStatus.MEASURED
        assert stale_res_with_policy.value == 1.0  # 16 days > 5 days -> stale
        assert stale_res_with_policy.metadata["temporal_evidence_status"] == "VALID"

        # B. Exact reference timestamp:
        lesson_exact = Lesson(
            lesson_id="LL-SYNTH-EXACT",
            title="Exact reference validation lesson",
            principle_id="PRIN-001",
            failure_class="DATA-INTEGRITY",
            severity=SeverityLevel.LOW,
            scope=ScopeLevel.PROJECT,
            description=SYNTHETIC_MARKER,
            root_cause="test",
            incorrect_behavior="test",
            correct_rule="test",
            prevention_method="test",
            validation_history=[
                ValidationRecord(
                    task="SYNTH-TASK",
                    timestamp="2026-09-26T00:00:00Z",
                    test="test_exact",
                    result="PASSED",
                )
            ],
        )
        stale_exact = compute_lesson_staleness(
            [lesson_exact],
            reference_time=datetime(2026, 9, 26, 0, 0, 0, tzinfo=timezone.utc),
            stale_threshold_days=5.0,
        )
        assert stale_exact.status == MetricStatus.MEASURED
        assert stale_exact.value == 0.0  # 0.0 <= 5.0 -> not stale
        assert stale_exact.numerator == 0
        assert stale_exact.denominator == 1
        assert stale_exact.metadata["mean_days_since_validation"] == 0.0
        assert stale_exact.metadata["future_validation_timestamps_count"] == 0
        assert stale_exact.metadata["temporal_evidence_status"] == "VALID"

        # C. Future validation timestamp:
        # Future relative to reference_time must NOT be clamped to 0.0 or treated as valid 0-day observation;
        # It must be marked temporally invalid, tracked in metadata, and return INSUFFICIENT_DATA.
        lesson_future = Lesson(
            lesson_id="LL-SYNTH-FUTURE",
            title="Future validation lesson",
            principle_id="PRIN-001",
            failure_class="DATA-INTEGRITY",
            severity=SeverityLevel.LOW,
            scope=ScopeLevel.PROJECT,
            description=SYNTHETIC_MARKER,
            root_cause="test",
            incorrect_behavior="test",
            correct_rule="test",
            prevention_method="test",
            validation_history=[
                ValidationRecord(
                    task="SYNTH-TASK",
                    timestamp="2026-10-01T00:00:00Z",
                    test="test_future",
                    result="PASSED",
                )
            ],
        )
        stale_future = compute_lesson_staleness(
            [lesson_future],
            reference_time=datetime(2026, 9, 26, 0, 0, 0, tzinfo=timezone.utc),
            stale_threshold_days=5.0,
        )
        assert stale_future.status == MetricStatus.INSUFFICIENT_DATA
        assert stale_future.value is None, "Future validation timestamp must not yield a valid or zero-age measurement"
        assert stale_future.numerator is None
        assert stale_future.denominator == 1
        assert stale_future.metadata["future_validation_timestamps_count"] == 1
        assert stale_future.metadata["temporal_evidence_status"] == "TEMPORALLY_INVALID"
        assert any("future relative to reference_time" in w for w in stale_future.warnings)

    def test_18_backend_retrieval_leaves_presentation_unknown_without_client_event(self):
        """18. backend retrieval -> presentation remains UNKNOWN without explicit client event."""
        recommended_lessons = ["LL-001", "LL-002"]
        # In absence of client presentation event callback
        pres_res = compute_ui_presentation_rate(recommended_lessons, client_events=None)
        assert pres_res.status == MetricStatus.UNKNOWN
        assert pres_res.value is None
        assert "Headless backend execution cannot observe UI presentation" in pres_res.warnings[0]

        # With explicit client presentation event stream
        client_events = [
            ClientPresentationEvent(
                event_id="EVT-001",
                lesson_id="LL-001",
                client_id="OPERATOR_CONSOLE_1",
                rendered_at="2026-09-26T12:00:00Z",
                metadata={"synthetic": SYNTHETIC_MARKER},
            )
        ]
        pres_measured = compute_ui_presentation_rate(recommended_lessons, client_events=client_events)
        assert pres_measured.status == MetricStatus.MEASURED
        assert pres_measured.value == 0.5  # 1 out of 2 presented


# ==============================================================================
# Group E: Synthetic Isolation, Determinism & Governance Invariants (Items 19-28)
# ==============================================================================

class TestSyntheticIsolationAndGovernanceInvariants:
    """Verifies synthetic labeling, determinism, catalog immutability, and zero-fabrication guarantees."""

    def test_19_synthetic_fixtures_remain_visibly_isolated(self):
        """19. synthetic fixtures remain visibly isolated from real measurements."""
        batch = evaluate_offline_batch(
            batch_id="SYNTH-BATCH-001",
            eval_tasks=[],
            is_synthetic_fixture=True,
        )
        assert batch.is_synthetic_fixture is True
        assert batch.synthetic_fixture_label == SYNTHETIC_MARKER
        b_dict = batch.to_dict()
        assert b_dict["synthetic_fixture_label"] == SYNTHETIC_MARKER

    def test_20_metric_output_is_deterministic_across_repeated_runs(self, tmp_path):
        """20. metric output is deterministic across repeated runs and independent of wall-clock or paths."""
        tasks = [
            AdjudicatedTaskRecord(
                task_id="SYNTH-TASK-DET-1",
                task_context={"retrieved_lesson_ids": ["LL-01", "LL-02"]},
                ground_truth_relevant_lesson_ids=["LL-01"],
                preflight_passed=False,
                is_block_accurate=True,
                notes=SYNTHETIC_MARKER,
            )
        ]
        # Create receipts in two completely different directory paths
        dir1 = tmp_path / "run1"
        dir2 = tmp_path / "run2"
        dir1.mkdir()
        dir2.mkdir()
        record_negative_feedback(
            category=NegativeFeedbackCategory.FALSE_BLOCK,
            reason="Deterministic test",
            receipt_dir=dir1,
            receipt_id="rcpt_det_001",
            source=SYNTHETIC_MARKER,
        )
        record_negative_feedback(
            category=NegativeFeedbackCategory.FALSE_BLOCK,
            reason="Deterministic test",
            receipt_dir=dir2,
            receipt_id="rcpt_det_001",
            source=SYNTHETIC_MARKER,
        )

        batch1 = evaluate_offline_batch("BATCH-DET", tasks, receipt_sources=dir1, is_synthetic_fixture=True)
        batch2 = evaluate_offline_batch("BATCH-DET", tasks, receipt_sources=dir2, is_synthetic_fixture=True)

        # 1. PROPERTY A (STABILITY): Same semantic inputs across different temporary directory paths
        # -> identical dataset_hash and evaluation_manifest_hash
        assert batch1.dataset_hash == batch2.dataset_hash
        assert batch1.evaluation_manifest_hash == batch2.evaluation_manifest_hash
        assert batch1.batch_result_hash == batch1.evaluation_manifest_hash

        assert batch1.metrics["retrieval_recall"].value == batch2.metrics["retrieval_recall"].value
        assert batch1.metrics["retrieval_precision"].value == batch2.metrics["retrieval_precision"].value
        assert batch1.metrics["false_block_rate"].value == batch2.metrics["false_block_rate"].value
        assert batch1.metrics["receipt_ingestion_summary"].value == batch2.metrics["receipt_ingestion_summary"].value

        # 1b. STABILITY under Run Metadata Change: differing batch_id -> same dataset_hash, distinct evaluation_manifest_hash
        batch_other_meta = evaluate_offline_batch("BATCH-DET-RUN-2", tasks, receipt_sources=dir1, is_synthetic_fixture=True)
        assert batch_other_meta.dataset_hash == batch1.dataset_hash, "Run metadata change must not change input dataset_hash"
        assert batch_other_meta.evaluation_manifest_hash != batch1.evaluation_manifest_hash, "Run metadata change must update evaluation_manifest_hash"

        # 2. PROPERTY B (SENSITIVITY): Semantic input changes must alter dataset_hash
        # 2a. Different task identifier
        different_tasks = [
            AdjudicatedTaskRecord(
                task_id="SYNTH-TASK-DET-DIFFERENT",
                task_context={"retrieved_lesson_ids": ["LL-03"]},
                ground_truth_relevant_lesson_ids=["LL-03"],
                notes=SYNTHETIC_MARKER,
            )
        ]
        batch_diff = evaluate_offline_batch("BATCH-DET-DIFF", different_tasks, receipt_sources=dir1, is_synthetic_fixture=True)
        assert batch_diff.dataset_hash != batch1.dataset_hash, "Different task identifier must produce different dataset_hash"

        # 2b. Added/removed task population count
        batch_extra_task = evaluate_offline_batch("BATCH-DET-EXTRA", tasks + different_tasks, receipt_sources=dir1, is_synthetic_fixture=True)
        assert batch_extra_task.dataset_hash != batch1.dataset_hash, "Altering task population count must produce different dataset_hash"

        # 2c. Altering receipt population
        batch_no_receipts = evaluate_offline_batch("BATCH-DET-NO-RCPT", tasks, receipt_sources=None, is_synthetic_fixture=True)
        assert batch_no_receipts.dataset_hash != batch1.dataset_hash, "Altering receipt population must produce different dataset_hash"

        # 2d. Altering synthetic fixture categorical status
        batch_real_flag = evaluate_offline_batch("BATCH-DET-REAL", tasks, receipt_sources=dir1, is_synthetic_fixture=False)
        assert batch_real_flag.dataset_hash != batch1.dataset_hash, "Altering synthetic fixture status must produce different dataset_hash"

        # 2e. CRITICAL SAME-ID / DIFFERENT-CONTENT TESTS (CONTRACT B: SEMANTIC INPUT DATASET IDENTITY)
        # Case A: Same task_id, different retrieved_lesson_ids in task_context
        tasks_case_a = [
            AdjudicatedTaskRecord(
                task_id="SYNTH-TASK-DET-1",
                task_context={"retrieved_lesson_ids": ["LL-01", "LL-99"]},  # altered retrieval context
                ground_truth_relevant_lesson_ids=["LL-01"],
                preflight_passed=False,
                is_block_accurate=True,
                notes=SYNTHETIC_MARKER,
            )
        ]
        batch_case_a = evaluate_offline_batch("BATCH-DET", tasks_case_a, receipt_sources=dir1, is_synthetic_fixture=True)
        assert batch_case_a.dataset_hash != batch1.dataset_hash, (
            "Contract B violation: Altering task_context['retrieved_lesson_ids'] with identical task_id must alter dataset_hash"
        )

        # Case B: Same task_id, different ground_truth_relevant_lesson_ids
        tasks_case_b = [
            AdjudicatedTaskRecord(
                task_id="SYNTH-TASK-DET-1",
                task_context={"retrieved_lesson_ids": ["LL-01", "LL-02"]},
                ground_truth_relevant_lesson_ids=["LL-99"],  # altered ground truth
                preflight_passed=False,
                is_block_accurate=True,
                notes=SYNTHETIC_MARKER,
            )
        ]
        batch_case_b = evaluate_offline_batch("BATCH-DET", tasks_case_b, receipt_sources=dir1, is_synthetic_fixture=True)
        assert batch_case_b.dataset_hash != batch1.dataset_hash, (
            "Contract B violation: Altering ground_truth_relevant_lesson_ids with identical task_id must alter dataset_hash"
        )

        # Case C: Same task_id, different adjudication fields (is_block_accurate)
        tasks_case_c = [
            AdjudicatedTaskRecord(
                task_id="SYNTH-TASK-DET-1",
                task_context={"retrieved_lesson_ids": ["LL-01", "LL-02"]},
                ground_truth_relevant_lesson_ids=["LL-01"],
                preflight_passed=False,
                is_block_accurate=False,  # altered block accuracy (false block)
                notes=SYNTHETIC_MARKER,
            )
        ]
        batch_case_c = evaluate_offline_batch("BATCH-DET", tasks_case_c, receipt_sources=dir1, is_synthetic_fixture=True)
        assert batch_case_c.dataset_hash != batch1.dataset_hash, (
            "Contract B violation: Altering is_block_accurate with identical task_id must alter dataset_hash"
        )

        # Case D: Same receipt_id, different canonical receipt payload (category)
        dir3 = tmp_path / "run3"
        dir3.mkdir()
        record_negative_feedback(
            category=NegativeFeedbackCategory.MISSED_LESSON,  # altered category
            reason="Deterministic test",
            receipt_dir=dir3,
            receipt_id="rcpt_det_001",  # identical receipt_id
            source=SYNTHETIC_MARKER,
        )
        batch_case_d = evaluate_offline_batch("BATCH-DET", tasks, receipt_sources=dir3, is_synthetic_fixture=True)
        assert batch_case_d.dataset_hash != batch1.dataset_hash, (
            "Contract B violation: Altering receipt category with identical receipt_id must alter dataset_hash"
        )

        # 2f. PROPERTY E (IRRELEVANT-METADATA INVARIANCE): Changing excluded administrative metadata
        # Changing task 'notes' (pure administrative metadata) leaves dataset_hash strictly identical
        tasks_admin_meta = [
            AdjudicatedTaskRecord(
                task_id="SYNTH-TASK-DET-1",
                task_context={"retrieved_lesson_ids": ["LL-01", "LL-02"]},
                ground_truth_relevant_lesson_ids=["LL-01"],
                preflight_passed=False,
                is_block_accurate=True,
                notes="COMPLETELY_DIFFERENT_ADMIN_NOTES",  # excluded administrative metadata
            )
        ]
        batch_admin_meta = evaluate_offline_batch("BATCH-DET", tasks_admin_meta, receipt_sources=dir1, is_synthetic_fixture=True)
        assert batch_admin_meta.dataset_hash == batch1.dataset_hash, (
            "Property E violation: Changing excluded administrative notes must not alter dataset_hash"
        )

        # 3. RESULT-ONLY INVARIANCE: Changing computed metric output must not alter input dataset_hash
        lesson_for_eval = Lesson(
            lesson_id="LL-DET-EVAL-01",
            title="Deterministic eval lesson",
            principle_id="PRIN-001",
            failure_class="DATA-INTEGRITY",
            severity=SeverityLevel.LOW,
            scope=ScopeLevel.PROJECT,
            description=SYNTHETIC_MARKER,
            root_cause="test",
            incorrect_behavior="test",
            correct_rule="test",
            prevention_method="test",
            validation_history=[
                ValidationRecord(
                    task="SYNTH-TASK",
                    timestamp="2026-09-10T00:00:00Z",
                    test="test_x",
                    result="PASSED",
                )
            ],
        )
        batch_thresh_stale = evaluate_offline_batch(
            "BATCH-THRESH-1", tasks, receipt_sources=dir1,
            lessons_catalog=[lesson_for_eval],
            stale_threshold_days=5.0,  # 16 days elapsed > 5 days -> stale (value: 1.0)
            is_synthetic_fixture=True,
        )
        batch_thresh_fresh = evaluate_offline_batch(
            "BATCH-THRESH-1", tasks, receipt_sources=dir1,
            lessons_catalog=[lesson_for_eval],
            stale_threshold_days=100.0,  # 16 days elapsed < 100 days -> not stale (value: 0.0)
            is_synthetic_fixture=True,
        )
        # Verify metric calculation output actually changed
        assert batch_thresh_stale.metrics["lesson_staleness"].value == 1.0
        assert batch_thresh_fresh.metrics["lesson_staleness"].value == 0.0
        assert batch_thresh_stale.metrics["lesson_staleness"].value != batch_thresh_fresh.metrics["lesson_staleness"].value

        # Input dataset_hash MUST remain strictly identical despite differing metric output
        assert batch_thresh_stale.dataset_hash == batch_thresh_fresh.dataset_hash, "Metric output change must not alter input dataset_hash"
        # While evaluation_manifest_hash MUST change to reflect differing results
        assert batch_thresh_stale.evaluation_manifest_hash != batch_thresh_fresh.evaluation_manifest_hash, "Metric output change must alter evaluation_manifest_hash"

        # 4. Enveloping & Decoupling check
        assert batch1.evaluation_manifest_hash != batch1.dataset_hash
        b_dict = batch1.to_dict()
        assert "dataset_hash" in b_dict
        assert "evaluation_manifest_hash" in b_dict
        assert "batch_result_hash" in b_dict

    def test_21_canonical_governance_catalogs_remain_untouched(self):
        """21. canonical governance catalogs remain untouched."""
        rules_path = CANONICAL_V2_DIR / "rules.json"
        lessons_path = CANONICAL_V2_DIR / "lessons.json"
        incidents_path = CANONICAL_V2_DIR / "incidents.json"

        # Record hashes before
        h_rules_before = hashlib.sha256(rules_path.read_bytes()).hexdigest()
        h_lessons_before = hashlib.sha256(lessons_path.read_bytes()).hexdigest()
        h_incidents_before = hashlib.sha256(incidents_path.read_bytes()).hexdigest()

        # Run offline batch evaluation
        tasks = [
            AdjudicatedTaskRecord(
                task_id="SYNTH-TASK-CAT-1",
                task_context={"retrieved_lesson_ids": ["LL-01"]},
                ground_truth_relevant_lesson_ids=["LL-01"],
                notes=SYNTHETIC_MARKER,
            )
        ]
        evaluate_offline_batch("BATCH-CAT-CHECK", tasks, is_synthetic_fixture=True)

        # Hashes after must be bit-identical
        assert hashlib.sha256(rules_path.read_bytes()).hexdigest() == h_rules_before
        assert hashlib.sha256(lessons_path.read_bytes()).hexdigest() == h_lessons_before
        assert hashlib.sha256(incidents_path.read_bytes()).hexdigest() == h_incidents_before

    def test_22_telemetry_remains_observational_only(self):
        """22. telemetry remains observational; it is never an authorization gate."""
        tracker = ControlEffectivenessTracker(task_id="test_22")
        trace = tracker.finalize_trace()
        # Ensure tracker has no method to alter preflight pass/block
        assert not hasattr(tracker, "authorize")
        assert not hasattr(tracker, "override_decision")
        assert len(trace) == len(ORDERED_CONTROL_STAGES)

    def test_23_metric_engine_cannot_mutate_authorization_decisions(self):
        """23. metric engine cannot mutate authorization decisions."""
        task_context = TaskContext(
            task_id="SYNTH-AUTH-TEST",
            domain=["imagery"],
            operation=["illegal_direct_mutation"],
            proposed_command="rm -rf /",
        )
        preflight_res = evaluate_task_preflight(task_context)
        initial_passed = preflight_res.passed

        # Passing preflight_res to offline evaluation batch
        evaluate_offline_batch(
            batch_id="BATCH-AUTH-TEST",
            eval_tasks=[preflight_res.to_dict()],
            is_synthetic_fixture=True,
        )

        # Authorization verdict cannot be flipped or mutated
        assert preflight_res.passed == initial_passed

    def test_24_metric_engine_cannot_promote_lessons_or_rules(self):
        """24. metric engine cannot promote lessons/rules."""
        store = GovernanceStore.get_instance()
        lesson_count_before = len(store.list_lessons())
        rule_count_before = len(store.list_rules())

        # Execute metric evaluations
        tasks = [
            AdjudicatedTaskRecord(
                task_id="SYNTH-PROMOTE-TEST",
                task_context={"retrieved_lesson_ids": ["LL-01"]},
                ground_truth_relevant_lesson_ids=["LL-01"],
                notes=SYNTHETIC_MARKER,
            )
        ]
        evaluate_offline_batch("BATCH-PROMOTE-TEST", tasks, is_synthetic_fixture=True)

        assert len(store.list_lessons()) == lesson_count_before
        assert len(store.list_rules()) == rule_count_before

    def test_25_report_numbers_reconcile_exactly_with_raw_counts(self):
        """25. report numbers reconcile exactly with raw counts."""
        tasks = [
            AdjudicatedTaskRecord(
                task_id="T1",
                task_context={"retrieved_lesson_ids": ["L1", "L2"]},
                ground_truth_relevant_lesson_ids=["L1", "L3"],  # 2 GT, 1 matched
                preflight_passed=False,
                is_block_accurate=False,  # 1 false block
                notes=SYNTHETIC_MARKER,
            ),
            AdjudicatedTaskRecord(
                task_id="T2",
                task_context={"retrieved_lesson_ids": ["L3"]},
                ground_truth_relevant_lesson_ids=["L3"],  # 1 GT, 1 matched
                preflight_passed=False,
                is_block_accurate=True,  # 1 accurate block
                notes=SYNTHETIC_MARKER,
            ),
        ]
        batch = evaluate_offline_batch("BATCH-RECON", tasks, is_synthetic_fixture=True)

        recall = batch.metrics["retrieval_recall"]
        assert recall.status == MetricStatus.MEASURED
        assert recall.numerator == 2
        assert recall.denominator == 3
        assert recall.value == round(2 / 3, 4)

        precision = batch.metrics["retrieval_precision"]
        assert precision.status == MetricStatus.MEASURED
        assert precision.numerator == 2
        assert precision.denominator == 3
        assert precision.value == round(2 / 3, 4)

        false_block = batch.metrics["false_block_rate"]
        assert false_block.status == MetricStatus.MEASURED
        assert false_block.numerator == 1
        assert false_block.denominator == 2
        assert false_block.value == 0.5

    def test_26_citation_frequency_population_disambiguation(self):
        """26. citation frequency distinguishes rule catalog population from trace batch population."""
        # 1. Catalog Rule population test
        rule1 = Rule(
            rule_id="RULE-CITE-01",
            principle_id="PRIN-001",
            failure_class="DATA_GOVERNANCE",
            title="Cite Prin 1",
            statement="test",
            action=ActionType.BLOCK,
            evidence_refs=["LL-001"],
        )
        rule2 = Rule(
            rule_id="RULE-CITE-02",
            principle_id="PRIN-002",
            failure_class="DATA_GOVERNANCE",
            title="Cite Prin 2",
            statement="test",
            action=ActionType.BLOCK,
            evidence_refs=[],
        )
        cat_res = compute_catalog_rule_citation_frequency("PRIN-001", [rule1, rule2])
        assert cat_res.metric_id == "METRIC-CATALOG-RULE-CITATION-FREQUENCY"
        assert cat_res.status == MetricStatus.MEASURED
        assert cat_res.numerator == 1
        assert cat_res.denominator == 2
        assert cat_res.value == 0.5
        assert cat_res.metadata["evaluation_scope"] == "CATALOG_RULES"

        # 2. Execution Trace population test
        trace_record = ControlTraceRecord(
            stage=ControlStage.RULE_APPLIED,
            outcome=ControlStageOutcome.TRUE,
            entity_refs=["RULE-CITE-01", "PRIN-001"],
            reason="Blocked by rule",
        )
        p_res = PreflightV2Result(
            passed=False,
            task_id="TASK-CITE-01",
            task_type="synthetic_test",
            elapsed_seconds=0.01,
            relevant_lessons=[],
            control_trace=[trace_record],
        )
        trace_res = compute_trace_citation_frequency("PRIN-001", [p_res])
        assert trace_res.metric_id == "METRIC-TRACE-CITATION-FREQUENCY"
        assert trace_res.status == MetricStatus.MEASURED
        assert trace_res.numerator == 1
        assert trace_res.denominator == 1
        assert trace_res.value == 1.0
        assert trace_res.metadata["evaluation_scope"] == "EXECUTION_TRACES"

        # 3. Dispatch via compute_citation_frequency
        disp_cat = compute_citation_frequency("PRIN-001", [rule1, rule2], population_type="catalog_rules")
        assert disp_cat.metric_id == "METRIC-CATALOG-RULE-CITATION-FREQUENCY"
        assert disp_cat.value == 0.5

        disp_trace = compute_citation_frequency("PRIN-001", [p_res], population_type="execution_traces")
        assert disp_trace.metric_id == "METRIC-TRACE-CITATION-FREQUENCY"
        assert disp_trace.value == 1.0

        # 4. Unknown population returns INSUFFICIENT_DATA
        disp_unknown = compute_citation_frequency("PRIN-001", [rule1], population_type="undefined_pop")
        assert disp_unknown.status == MetricStatus.INSUFFICIENT_DATA
        assert disp_unknown.value is None

    def test_27_status_taxonomy_bounds_and_zero_fabrication(self):
        """27. verifies the 4-valued bounded status taxonomy (MEASURED, UNKNOWN, INSUFFICIENT_DATA, NOT_APPLICABLE).
        
        Confirms that MEASURED is metric-specific and does NOT universally require a ground-truth oracle:
        - metrics requiring ground truth (e.g. false block rate, recall) require adjudication.
        - metrics evaluated over structural catalog/trace/validation evidence (e.g. citation frequency,
          receipt validation pass rate, objective lesson age) achieve MEASURED without ground-truth oracles.
        """
        # MEASURED (Case A: Ground-truth required): Evaluated over verified block accuracy
        res_measured_gt = compute_false_block_rate([
            AdjudicatedTaskRecord(task_id="T1", is_block_accurate=True, preflight_passed=False)
        ])
        assert res_measured_gt.status == MetricStatus.MEASURED
        assert res_measured_gt.value == 0.0  # 0 false blocks out of 1 block

        # MEASURED (Case B: No ground-truth oracle required): Evaluated over catalog rule evidence
        rule_synth = Rule(
            rule_id="RULE-MEASURED-01",
            principle_id="PRIN-001",
            failure_class="DATA_GOVERNANCE",
            title="Cite Prin 1",
            statement="test",
            action=ActionType.BLOCK,
            evidence_refs=["LL-001"],
        )
        res_measured_catalog = compute_catalog_rule_citation_frequency("PRIN-001", [rule_synth])
        assert res_measured_catalog.status == MetricStatus.MEASURED
        assert res_measured_catalog.value == 1.0
        # Proves MEASURED does not universally require an external ground-truth oracle

        # MEASURED (Case C: No ground-truth oracle required): Evaluated over receipt structural validation evidence
        res_measured_receipt = compute_receipt_validation_pass_rate({
            "total_examined": 1,
            "validated_records": [{"receipt_id": "r1"}],
        })
        assert res_measured_receipt.status == MetricStatus.MEASURED
        assert res_measured_receipt.value == 1.0

        # UNKNOWN: Fundamentally unobserved event stream
        res_unknown = compute_ui_presentation_rate(["LL-01"], client_events=None)
        assert res_unknown.status == MetricStatus.UNKNOWN
        assert res_unknown.value is None

        # INSUFFICIENT_DATA: Evaluation attempted but mandatory oracle/threshold missing
        res_insufficient = compute_retrieval_recall([
            AdjudicatedTaskRecord(task_id="T2", ground_truth_relevant_lesson_ids=None)
        ])
        assert res_insufficient.status == MetricStatus.INSUFFICIENT_DATA
        assert res_insufficient.value is None

        # NOT_APPLICABLE: Cohort has tasks, but zero were blocked (denominator is zero)
        res_na = compute_false_block_rate([
            AdjudicatedTaskRecord(task_id="T3", is_block_accurate=True, preflight_passed=True)
        ])
        assert res_na.status == MetricStatus.NOT_APPLICABLE
        assert res_na.value is None
        assert res_na.numerator == 0
        assert res_na.denominator == 0


    def test_28_integrity_detection_precision_wording(self, tmp_path):
        """28. verifies integrity detection terminology and fail-closed conflicting overwrite."""
        r1 = record_negative_feedback(
            category=NegativeFeedbackCategory.FALSE_BLOCK,
            reason="Original audit payload",
            receipt_dir=tmp_path,
            receipt_id="rcpt_integrity_01",
            source=SYNTHETIC_MARKER,
        )
        r_mutated = dict(r1)
        r_mutated["reason"] = "Direct file overwrite on disk"
        raw_core = {k: v for k, v in r_mutated.items() if k not in ("payload_sha256", "integrity_note")}
        r_mutated["payload_sha256"] = hashlib.sha256(canonicalize_json_v1(raw_core)).hexdigest()

        # Ingestion verifies integrity detection
        with pytest.raises(ConflictingReceiptError) as exc_info:
            ingest_negative_feedback_receipts([r1, r_mutated], fail_closed_on_conflict=True)
        assert "RECEIPT_INTEGRITY_CONFLICT_ERROR" in str(exc_info.value)
        # Note: Detection != Physical prevention; system proves post-hoc integrity detection when digest differs.

        # Regression prevention: ensure metric docstrings never overclaim tamper guarantees
        import ocean_sentinel.governance.metrics as m_mod
        for attr_name in dir(m_mod):
            attr = getattr(m_mod, attr_name)
            if callable(attr) and hasattr(attr, "__doc__") and attr.__doc__:
                doc_lower = attr.__doc__.lower()
                assert "tamper-proof" not in doc_lower, f"Overclaimed tamper-proof in {attr_name}"
                assert "tamper-evident" not in doc_lower, f"Overclaimed tamper-evident in {attr_name}"
                assert "tamper prevention" not in doc_lower, f"Overclaimed tamper prevention in {attr_name}"

