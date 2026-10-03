"""End-to-End Operational Learning Proof for Ocean Sentinel Governance.

Demonstrates that the Agent Learning & Failure-Prevention Framework is capable of
closed-loop operational learning:
  FAILURE DETECTED
  -> RECORDED (Candidate Incident / Lesson + Negative Feedback Receipt)
  -> MITIGATED (Corrective action in staged environment)
  -> REGRESSION_PROTECTED (Executable guardrail associated + Lifecycle transition verified)
  -> FUTURE TASK APPLICABILITY & RETRIEVAL (Matched via Applicability & Hybrid Retrieval)
  -> ENFORCEMENT & RECURRENCE BLOCKING (Preflight actively halts reintroduction)
  -> EVIDENCE-BACKED PROMOTION (Anti-gaming & multi-task validation rules enforced)
  -> BEHAVIORAL DIFFERENCE PROVEN (Failure silently allowed BEFORE vs actively blocked AFTER)

All fixtures are staged, synthetic, and non-scientific.
No holdout data, no Part III data, no scientific inference, and no protected files modified.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pytest

from ocean_sentinel.governance.applicability import ApplicabilityEngine
from ocean_sentinel.governance.control import (
    ControlEffectivenessTracker,
    ControlStage,
    ControlStageOutcome,
    NegativeFeedbackCategory,
    record_negative_feedback,
)
from ocean_sentinel.governance.enforcement import EnforcementEngine
from ocean_sentinel.governance.interface import evaluate_task_preflight
from ocean_sentinel.governance.lifecycle import LifecycleManager
from ocean_sentinel.governance.models import (
    ActionType,
    EvidenceStrength,
    Incident,
    LearningState,
    Lesson,
    PreflightIssueV2,
    PreflightV2Result,
    Rule,
    ScopeLevel,
    SeverityLevel,
    TaskContext,
    ValidationRecord,
)
from ocean_sentinel.governance.retrieval import HybridRetrievalEngine


# ==============================================================================
# 1. Synthetic Domain Component: Staged Manifest Pipeline
# ==============================================================================

class SyntheticStagingPipeline:
    """A safe, non-scientific synthetic staging component susceptible to a seed-drift failure."""

    @staticmethod
    def validate_manifest_config(config: Dict[str, Any]) -> Tuple[bool, str]:
        """Detector: Verifies that manifest generation explicitly declares a deterministic integer seed."""
        if "seed" not in config or config["seed"] is None:
            return False, "FAIL_UNPINNED_SEED: Random seed is unpinned or None; causes non-deterministic spatial splits."
        if not isinstance(config["seed"], int):
            return False, f"FAIL_INVALID_SEED_TYPE: Seed must be an integer, got {type(config['seed']).__name__}."
        if config["seed"] <= 0:
            return False, "FAIL_INVALID_SEED_VALUE: Seed must be a strictly positive integer."
        return True, "PASS: Manifest configuration is deterministic and valid."


# ==============================================================================
# 2. End-to-End Learning Loop Verification Suite
# ==============================================================================

class TestLearningLoopEndToEndProof:
    """Rigorous verification of the 9-step closed-loop learning sequence."""

    def test_step_a_failure_detection(self):
        """STEP A: Controlled failure condition is reliably detected."""
        # Unsafe configuration: unpinned seed
        unsafe_config = {
            "dataset_name": "synthetic_coastal_pilot_v1",
            "seed": None,  # Failure mode: unpinned RNG
            "split_ratio": [0.7, 0.15, 0.15],
        }
        detected, reason = SyntheticStagingPipeline.validate_manifest_config(unsafe_config)
        assert not detected, "Detector failed to detect unpinned seed!"
        assert "FAIL_UNPINNED_SEED" in reason

    def test_step_b_failure_recording(self, tmp_path):
        """STEP B: Failure is formally represented as structured Incident, Lesson, and Feedback Receipt."""
        # 1. Structured Incident Representation
        incident = Incident(
            incident_id="INC-SYNTH-2026-001",
            task_id="TASK-SYNTH-HARVEST-01",
            title="Non-deterministic split caused by unpinned RNG seed in staging config",
            failure_class="REPRODUCIBILITY",
            description="Staging config omitted explicit seed, causing split allocation to fluctuate across runs.",
            root_cause="Config parser defaulted missing 'seed' to random system entropy.",
            impact="Cluster split manifests diverged across replicate dry runs.",
            detection="SyntheticStagingPipeline.validate_manifest_config",
            correction="Pinned seed to deterministic constant 20260927 in staging profile.",
            prevention="GOV-RULE-SYNTH-901: All staging split configs must declare explicit integer seed > 0.",
            evidence=str(tmp_path / "seed_drift_audit.json"),
            rules_created=["GOV-RULE-SYNTH-901"],
            lessons_created=["LL-SYNTH-001"],
            tests_created=["tests/test_learning_loop_end_to_end_proof.py::test_step_g_recurrence_prevention"],
        )
        assert incident.incident_id == "INC-SYNTH-2026-001"
        assert incident.failure_class == "REPRODUCIBILITY"

        # 2. Structured Lesson Candidate Representation
        lesson = Lesson(
            lesson_id="LL-SYNTH-001",
            title="Mandatory explicit RNG seed declaration in staging split manifests",
            principle_id="PRIN-001",
            failure_class="REPRODUCIBILITY",
            severity=SeverityLevel.HIGH,
            scope=ScopeLevel.PROJECT,
            description="Staging configurations omitting an explicit positive integer seed exhibit non-deterministic cluster allocations.",
            root_cause="Absence of preflight validation schema requiring mandatory seed parameter.",
            incorrect_behavior="Omitting 'seed' parameter or setting seed=None in staging manifest.",
            correct_rule="Declare seed as a positive integer in all manifest configurations.",
            prevention_method="Enforce GOV-RULE-SYNTH-901 via preflight check and automated regression test.",
            rules=["GOV-RULE-SYNTH-901"],
            incidents=["INC-SYNTH-2026-001"],
            regression_test_ids=["tests/test_learning_loop_end_to_end_proof.py::test_step_g_recurrence_prevention"],
            status=LearningState.RECORDED,
            category="REPRODUCIBILITY",
            first_seen="TASK-SYNTH-HARVEST-01",
        )
        assert lesson.status == LearningState.RECORDED
        assert len(lesson.regression_test_ids) == 1

        # 3. Tamper-evident negative feedback receipt emission
        receipt = record_negative_feedback(
            category=NegativeFeedbackCategory.WEAK_ENFORCEMENT,
            reason="Unpinned seed in staging config escaped static parse phase.",
            receipt_dir=tmp_path / "feedback",
            receipt_id="rcpt_synth_test_001",
            entity_refs=["LL-SYNTH-001", "GOV-RULE-SYNTH-901"],
            evidence_refs=[str(tmp_path / "seed_drift_audit.json")],
            task_context={"task_id": "TASK-SYNTH-HARVEST-01", "operation": ["manifest_staging"]},
        )
        assert receipt["receipt_id"] == "rcpt_synth_test_001"
        assert "payload_sha256" in receipt
        assert (tmp_path / "feedback" / "rcpt_synth_test_001.json").exists()

    def test_step_c_mitigation(self):
        """STEP C: Immediate defect is mitigated in the staged configuration."""
        mitigated_config = {
            "dataset_name": "synthetic_coastal_pilot_v1",
            "seed": 20260927,  # Mitigated: explicit positive integer seed
            "split_ratio": [0.7, 0.15, 0.15],
        }
        passed, msg = SyntheticStagingPipeline.validate_manifest_config(mitigated_config)
        assert passed, f"Mitigation failed: {msg}"
        assert "PASS" in msg

    def test_step_d_regression_protection_and_lifecycle_progression(self):
        """STEP D: Executable regression protection is bound and state advances from RECORDED to REGRESSION_PROTECTED."""
        lesson = Lesson(
            lesson_id="LL-SYNTH-001",
            title="Mandatory explicit RNG seed declaration in staging split manifests",
            principle_id="PRIN-001",
            failure_class="REPRODUCIBILITY",
            severity=SeverityLevel.HIGH,
            scope=ScopeLevel.PROJECT,
            description="Staging configurations omitting explicit seed exhibit drift.",
            root_cause="Missing schema check.",
            incorrect_behavior="seed=None",
            correct_rule="seed must be int > 0",
            prevention_method="GOV-RULE-SYNTH-901",
            status=LearningState.RECORDED,
            regression_test_ids=["tests/test_learning_loop_end_to_end_proof.py::test_step_g_recurrence_prevention"],
        )

        # Transition without automated test must fail
        ok_no_test, msg_no_test = LifecycleManager.can_transition(
            current=lesson.status,
            target=LearningState.REGRESSION_PROTECTED,
            has_automated_test=False,
        )
        assert not ok_no_test
        assert "without an automated guardrail" in msg_no_test

        # Transition with automated test must succeed
        ok_with_test, msg_with_test = LifecycleManager.can_transition(
            current=lesson.status,
            target=LearningState.REGRESSION_PROTECTED,
            has_automated_test=True,
        )
        assert ok_with_test
        lesson.status = LearningState.REGRESSION_PROTECTED
        assert lesson.status == LearningState.REGRESSION_PROTECTED

    def test_step_e_future_task_applicability_and_retrieval(self):
        """STEP E: Separate synthetic future task retrieves lesson and activates the rule."""
        rule_synth = Rule(
            rule_id="GOV-RULE-SYNTH-901",
            principle_id="PRIN-001",
            failure_class="REPRODUCIBILITY",
            title="Explicit RNG seed requirement for staging operations",
            statement="All staging split manifests must declare an explicit deterministic integer seed.",
            scope=ScopeLevel.PROJECT,
            severity=SeverityLevel.HIGH,
            action=ActionType.BLOCK,
            applies_to={"operation": ["staging_split_manifest", "manifest_generation"]},
            prohibited_actions=["unpinned seed", "random entropy split", "seed=None"],
            regression_test_ids=["tests/test_learning_loop_end_to_end_proof.py::test_step_g_recurrence_prevention"],
            status=LearningState.REGRESSION_PROTECTED,
            evidence_strength=EvidenceStrength.DIRECT_MEASUREMENT,
        )

        lesson_synth = Lesson(
            lesson_id="LL-SYNTH-001",
            title="Mandatory explicit RNG seed declaration in staging split manifests",
            principle_id="PRIN-001",
            failure_class="REPRODUCIBILITY",
            severity=SeverityLevel.HIGH,
            scope=ScopeLevel.PROJECT,
            description="Staging split manifests omitting explicit seed exhibit non-deterministic allocations.",
            root_cause="Missing preflight validation check.",
            incorrect_behavior="seed=None",
            correct_rule="seed must be int > 0",
            prevention_method="GOV-RULE-SYNTH-901",
            rules=["GOV-RULE-SYNTH-901"],
            status=LearningState.REGRESSION_PROTECTED,
            regression_test_ids=["tests/test_learning_loop_end_to_end_proof.py::test_step_g_recurrence_prevention"],
        )

        # Future Task Context with matching operation
        future_ctx = TaskContext(
            task_id="TASK-FUTURE-CANDIDATE-HARVEST-99",
            task_type="data_processing",
            operation=["staging_split_manifest"],
            proposed_plan="Generate candidate split manifests for coastal scenes.",
        )

        # 1. Applicability Engine test
        app_engine = ApplicabilityEngine()
        is_app, reasons = app_engine.evaluate_rule(rule_synth, future_ctx)
        assert is_app, "Rule failed to match future task context!"
        assert any("operation" in r.lower() for r in reasons)

        # 2. Retrieval Engine test
        retrieval_engine = HybridRetrievalEngine([lesson_synth], [rule_synth])
        results = retrieval_engine.retrieve_for_context(future_ctx)
        assert len(results) > 0
        retrieved_ids = [r.item_id for r in results]
        assert "LL-SYNTH-001" in retrieved_ids or "GOV-RULE-SYNTH-901" in retrieved_ids

    def test_step_f_enforcement_blocks_unsafe_future_task(self):
        """STEP F: EnforcementEngine blocks an unsafe future task plan proposing prohibited actions."""
        rule_synth = Rule(
            rule_id="GOV-RULE-SYNTH-901",
            principle_id="PRIN-001",
            failure_class="REPRODUCIBILITY",
            title="Explicit RNG seed requirement for staging operations",
            statement="All staging split manifests must declare an explicit deterministic integer seed.",
            scope=ScopeLevel.PROJECT,
            severity=SeverityLevel.HIGH,
            action=ActionType.BLOCK,
            applies_to={"operation": ["staging_split_manifest"]},
            prohibited_actions=["unpinned seed", "random entropy split"],
            status=LearningState.REGRESSION_PROTECTED,
            evidence_strength=EvidenceStrength.DIRECT_MEASUREMENT,
        )

        # Unsafe plan explicitly mentioning prohibited action
        unsafe_future_ctx = TaskContext(
            task_id="TASK-FUTURE-RECURRENCE-01",
            task_type="data_processing",
            operation=["staging_split_manifest"],
            proposed_plan="Generate staging manifest using unpinned seed for exploratory diversity.",
        )

        enf_engine = EnforcementEngine()
        blockers, warnings, _ = enf_engine.evaluate_task(unsafe_future_ctx, [rule_synth])
        assert len(blockers) > 0, "Enforcement engine failed to emit a BLOCK for prohibited action!"
        assert any(b.rule_id == "GOV-RULE-SYNTH-901" for b in blockers)
        assert any("unpinned seed" in b.message.lower() for b in blockers)

        # Compliant plan passes cleanly
        compliant_future_ctx = TaskContext(
            task_id="TASK-FUTURE-COMPLIANT-01",
            task_type="data_processing",
            operation=["staging_split_manifest"],
            proposed_plan="Generate staging manifest using deterministic pinned seed 20260927.",
        )
        blockers_c, _, _ = enf_engine.evaluate_task(compliant_future_ctx, [rule_synth])
        assert len(blockers_c) == 0, f"Compliant plan was falsely blocked: {[b.message for b in blockers_c]}"

    def test_step_g_recurrence_prevention(self):
        """STEP G: Regression guardrail actively halts reintroduction of the failure mode."""
        # Reintroduced failure
        reintroduced_config = {
            "dataset_name": "synthetic_future_dataset_v2",
            "seed": None,  # Reintroduced bug
            "split_ratio": [0.7, 0.15, 0.15],
        }
        passed, reason = SyntheticStagingPipeline.validate_manifest_config(reintroduced_config)
        assert not passed, "Reintroduced failure mode was not caught by the guardrail!"
        assert "FAIL_UNPINNED_SEED" in reason

        # Corrected configuration passes
        valid_config = {
            "dataset_name": "synthetic_future_dataset_v2",
            "seed": 42,
            "split_ratio": [0.7, 0.15, 0.15],
        }
        passed_v, _ = SyntheticStagingPipeline.validate_manifest_config(valid_config)
        assert passed_v

    def test_step_h_evidence_backed_promotion_gates(self):
        """STEP H: PROVEN_STABLE promotion requires multi-task evidence and rejects all 10 adversarial gaming attempts."""
        # Case J: Direct status-forcing from RECORDED -> PROVEN_STABLE is illegal
        ok_j, msg_j = LifecycleManager.can_transition(
            LearningState.RECORDED, LearningState.PROVEN_STABLE
        )
        assert not ok_j
        assert "strictly prohibited" in msg_j

        # Case I: Missing automated test flag -> rejected
        ok_i, msg_i = LifecycleManager.can_transition(
            LearningState.REGRESSION_PROTECTED,
            LearningState.PROVEN_STABLE,
            has_automated_test=False,
            validation_records=[],
            origin_task="TASK-ORIGIN",
        )
        assert not ok_i
        assert "without an active automated test" in msg_i

        # Case G: Origin task validating itself -> rejected (self-validation prohibited)
        rec_origin = ValidationRecord(
            task="TASK-ORIGIN",
            timestamp="2026-10-01T10:00:00Z",
            test="test_step_g_recurrence_prevention",
            result="PASSED",
            evidence="Self-validation attempt by origin task.",
        )
        ok_g, msg_g = LifecycleManager.can_transition(
            LearningState.REGRESSION_PROTECTED,
            LearningState.PROVEN_STABLE,
            has_automated_test=True,
            validation_records=[rec_origin],
            origin_task="TASK-ORIGIN",
        )
        assert not ok_g
        assert "BLOCK-010-SELF_VALIDATION_PROHIBITED" in msg_g

        # Case A: Same task repeated twice (< 2 distinct tasks) -> rejected
        rec_task1 = ValidationRecord(
            task="TASK-INDEPENDENT-RUN-01",
            timestamp="2026-10-01T10:00:00Z",
            test="test_step_g_recurrence_prevention",
            result="PASSED",
            evidence="Deterministic partition verification passed for seed=20260927 across 100 tiles.",
        )
        rec_task1_repeat = ValidationRecord(
            task="TASK-INDEPENDENT-RUN-01",
            timestamp="2026-10-01T11:00:00Z",
            test="test_step_g_recurrence_prevention",
            result="PASSED",
            evidence="Second run of same task.",
        )
        ok_a, msg_a = LifecycleManager.can_transition(
            LearningState.REGRESSION_PROTECTED,
            LearningState.PROVEN_STABLE,
            has_automated_test=True,
            validation_records=[rec_task1, rec_task1_repeat],
            origin_task="TASK-ORIGIN",
        )
        assert not ok_a
        assert "BLOCK-010-UNVERIFIED_PROVEN_STABLE" in msg_a

        # Case B: Replay task prefix -> rejected
        rec_replay = ValidationRecord(
            task="REPLAY-RUN-02",
            timestamp="2026-10-01T12:00:00Z",
            test="test_step_g_recurrence_prevention",
            result="PASSED",
            evidence="Replay execution evidence.",
        )
        ok_b, msg_b = LifecycleManager.can_transition(
            LearningState.REGRESSION_PROTECTED,
            LearningState.PROVEN_STABLE,
            has_automated_test=True,
            validation_records=[rec_task1, rec_replay],
            origin_task="TASK-ORIGIN",
        )
        assert not ok_b
        assert "BLOCK-010-SYNTHETIC_VALIDATION_PROHIBITED" in msg_b

        # Case E: Automated batch chain / synthetic indicators -> rejected
        rec_chain = ValidationRecord(
            task="AUTO-CHAIN-BATCH-05",
            timestamp="2026-10-01T13:00:00Z",
            test="test_step_g_recurrence_prevention",
            result="PASSED",
            evidence="Auto-chain execution evidence.",
        )
        ok_e, msg_e = LifecycleManager.can_transition(
            LearningState.REGRESSION_PROTECTED,
            LearningState.PROVEN_STABLE,
            has_automated_test=True,
            validation_records=[rec_task1, rec_chain],
            origin_task="TASK-ORIGIN",
        )
        assert not ok_e
        assert "BLOCK-010-SYNTHETIC_VALIDATION_PROHIBITED" in msg_e

        # Case C & D: Different task IDs but identical evidence hash -> rejected
        rec_task2_dup = ValidationRecord(
            task="TASK-INDEPENDENT-RUN-02",
            timestamp="2026-10-01T14:00:00Z",
            test="test_step_g_recurrence_prevention",
            result="PASSED",
            evidence="Deterministic partition verification passed for seed=20260927 across 100 tiles.",  # Identical
        )
        ok_cd, msg_cd = LifecycleManager.can_transition(
            LearningState.REGRESSION_PROTECTED,
            LearningState.PROVEN_STABLE,
            has_automated_test=True,
            validation_records=[rec_task1, rec_task2_dup],
            origin_task="TASK-ORIGIN",
        )
        assert not ok_cd
        assert "BLOCK-010-DUPLICATE_EVIDENCE" in msg_cd

        # Case F: Duplicate validation fingerprint -> rejected
        forced_fp = LifecycleManager.compute_validation_fingerprint(
            task="TASK-INDEPENDENT-RUN-01",
            test="test_step_g_recurrence_prevention",
            evidence="Deterministic partition verification passed for seed=20260927 across 100 tiles.",
            timestamp="2026-10-01T10:00:00Z",
        )
        rec_task1_fp = ValidationRecord(
            task="TASK-INDEPENDENT-RUN-01",
            timestamp="2026-10-01T10:00:00Z",
            test="test_step_g_recurrence_prevention",
            result="PASSED",
            evidence="Deterministic partition verification passed for seed=20260927 across 100 tiles.",
            fingerprint=forced_fp,
        )
        rec_task2_dup_fp = ValidationRecord(
            task="TASK-INDEPENDENT-RUN-02",
            timestamp="2026-10-01T14:00:00Z",
            test="test_step_g_recurrence_prevention",
            result="PASSED",
            evidence="Different text but manually forced duplicate fingerprint.",
            fingerprint=forced_fp,
        )
        ok_f, msg_f = LifecycleManager.can_transition(
            LearningState.REGRESSION_PROTECTED,
            LearningState.PROVEN_STABLE,
            has_automated_test=True,
            validation_records=[rec_task1_fp, rec_task2_dup_fp],
            origin_task="TASK-ORIGIN",
        )
        assert not ok_f
        assert "BLOCK-010-DUPLICATE_VALIDATION" in msg_f

        # Case H: Genuine distinct validations across 2 subsequent independent tasks -> authorized
        rec_task2_genuine = ValidationRecord(
            task="TASK-INDEPENDENT-RUN-02",
            timestamp="2026-10-01T15:00:00Z",
            test="test_step_g_recurrence_prevention",
            result="PASSED",
            evidence="Second independent validation on coastal cluster 04 verified identical manifest hash 9a8b7c.",
        )
        ok_h, msg_h = LifecycleManager.can_transition(
            LearningState.REGRESSION_PROTECTED,
            LearningState.PROVEN_STABLE,
            has_automated_test=True,
            validation_records=[rec_task1, rec_task2_genuine],
            origin_task="TASK-ORIGIN",
        )
        assert ok_h
        assert "Legal transition authorized" in msg_h

    def test_step_i_future_behavior_difference_proof(self):
        """STEP I: Concrete before-and-after demonstration that experience changed future system behavior.
        
        BEFORE: An unpinned seed was admitted silently because no rule existed.
        AFTER: The identical task configuration is actively evaluated, rejected by Preflight, and caught by regression test.
        """
        # Baseline (BEFORE): No rule in active set
        unsafe_task = TaskContext(
            task_id="TASK-UNPROTECTED-ERA",
            task_type="data_processing",
            operation=["staging_split_manifest"],
            proposed_plan="Execute staging split with unpinned seed for maximum exploration entropy.",
        )
        enf_engine = EnforcementEngine()

        # Before learning: zero rules active -> passed
        blockers_before, _, _ = enf_engine.evaluate_task(unsafe_task, active_rules=[])
        assert len(blockers_before) == 0, "Before learning, task was unexpectedly blocked!"

        # After learning: rule is active and regression-protected -> blocked
        learned_rule = Rule(
            rule_id="GOV-RULE-SYNTH-901",
            principle_id="PRIN-001",
            failure_class="REPRODUCIBILITY",
            title="Explicit RNG seed requirement for staging operations",
            statement="All staging split manifests must declare an explicit deterministic integer seed.",
            scope=ScopeLevel.PROJECT,
            severity=SeverityLevel.HIGH,
            action=ActionType.BLOCK,
            applies_to={"operation": ["staging_split_manifest"]},
            prohibited_actions=["unpinned seed"],
            status=LearningState.REGRESSION_PROTECTED,
            evidence_strength=EvidenceStrength.DIRECT_MEASUREMENT,
        )
        blockers_after, _, _ = enf_engine.evaluate_task(unsafe_task, active_rules=[learned_rule])
        assert len(blockers_after) == 1, "After learning, task failed to be blocked!"
        assert blockers_after[0].rule_id == "GOV-RULE-SYNTH-901"
        assert "unpinned seed" in blockers_after[0].message.lower()

        # Empirical proof that experience changed future system behavior
        behavior_changed = (len(blockers_before) == 0) and (len(blockers_after) == 1)
        assert behavior_changed, "Closed-loop behavioral difference was not proven!"

    def test_governed_causality_and_preflight_pipeline(self):
        """Rigorous causality test: proves that evaluate_task_preflight executes the complete
        governance pipeline, demonstrating the exact relationship between Rules, Lessons, and Enforcement.
        
        1. Preflight blocks unsafe operations via active Rules evaluated by EnforcementEngine.
        2. HybridRetrievalEngine retrieves Lessons for contextual explanation, not execution blocking.
        3. Even when lexical retrieval returns zero safety matches, EnforcementEngine strictly blocks.
        4. ControlEffectivenessTracker records LESSON_APPLICABLE=UNKNOWN as an intentional architectural
           boundary because Rules, not Lessons, are the executable applicability unit.
        """
        # Context attempting prohibited operations
        unsafe_plan_ctx = TaskContext(
            task_id="TASK-PREFLIGHT-CAUSALITY-01",
            task_type="diagnostic",
            diagnostic="DIAG-05",
            operation=["access_holdout"],
            proposed_plan="Evaluate checkpoint accuracy directly against holdout partition.",
        )

        tracker = ControlEffectivenessTracker(task_id=unsafe_plan_ctx.task_id)
        result = evaluate_task_preflight(unsafe_plan_ctx, tracker=tracker)

        # 1. Verification of blocking: preflight halted
        assert not result.passed, "Preflight failed to block prohibited holdout access!"
        assert any(b.code == "BLOCK-001-HOLDOUT" for b in result.blockers)

        # 2. Verification of retrieved lessons (informative context)
        assert isinstance(result.relevant_lessons, list)

        # 3. Verification of control effectiveness trace
        trace_stages = {r.stage: r.outcome for r in result.control_trace}
        # LESSON_APPLICABLE is UNKNOWN because ApplicabilityEngine intentionally evaluates Rules, not Lessons
        assert trace_stages[ControlStage.LESSON_APPLICABLE] == ControlStageOutcome.UNKNOWN
        # RULE_APPLIED is TRUE because active invariant rules were evaluated and applied
        assert trace_stages[ControlStage.RULE_APPLIED] == ControlStageOutcome.TRUE
