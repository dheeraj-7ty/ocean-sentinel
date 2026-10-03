"""Core data models for Ocean Sentinel Governance & Institutional Learning Architecture v2."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union


class ScopeLevel(str, Enum):
    """Scope hierarchy for governance rules and lessons."""
    GLOBAL = "GLOBAL"
    DOMAIN = "DOMAIN"
    PROJECT = "PROJECT"
    EXPERIMENT = "EXPERIMENT"
    DIAGNOSTIC = "DIAGNOSTIC"
    TASK = "TASK"

    @property
    def rank(self) -> int:
        """Higher integer = broader scope."""
        ranks = {
            ScopeLevel.GLOBAL: 60,
            ScopeLevel.DOMAIN: 50,
            ScopeLevel.PROJECT: 40,
            ScopeLevel.EXPERIMENT: 30,
            ScopeLevel.DIAGNOSTIC: 20,
            ScopeLevel.TASK: 10,
        }
        return ranks.get(self, 0)


class SeverityLevel(str, Enum):
    """Severity classification for governance violations."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"

    @property
    def rank(self) -> int:
        """Higher integer = higher severity."""
        ranks = {
            SeverityLevel.CRITICAL: 100,
            SeverityLevel.HIGH: 75,
            SeverityLevel.MEDIUM: 50,
            SeverityLevel.LOW: 25,
            SeverityLevel.INFORMATIONAL: 10,
        }
        return ranks.get(self, 0)


class ActionType(str, Enum):
    """Enforcement action emitted by governance rules."""
    BLOCK = "BLOCK"
    WARN = "WARN"
    RECOMMEND = "RECOMMEND"
    INFORM = "INFORM"


class LearningState(str, Enum):
    """Lifecycle stages for institutional lessons and rules."""
    PROPOSED = "PROPOSED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    RECORDED = "RECORDED"
    REGRESSION_PROTECTED = "REGRESSION_PROTECTED"
    PROVEN_STABLE = "PROVEN_STABLE"
    DEPRECATED = "DEPRECATED"
    SUPERSEDED = "SUPERSEDED"


class EvidenceStrength(str, Enum):
    """Trust hierarchy for evidence supporting lessons and rules."""
    DIRECT_MEASUREMENT = "DIRECT_MEASUREMENT"
    REPRODUCED_ANALYSIS = "REPRODUCED_ANALYSIS"
    INDEPENDENT_VALIDATION = "INDEPENDENT_VALIDATION"
    DOCUMENTED_IMPLEMENTATION_FACT = "DOCUMENTED_IMPLEMENTATION_FACT"
    AGENT_INTERPRETATION = "AGENT_INTERPRETATION"
    HYPOTHESIS = "HYPOTHESIS"
    UNVERIFIED_ASSERTION = "UNVERIFIED_ASSERTION"

    @property
    def allows_hard_block(self) -> bool:
        """Determines whether evidence strength is sufficient to justify a hard BLOCK action."""
        return self in (
            EvidenceStrength.DIRECT_MEASUREMENT,
            EvidenceStrength.REPRODUCED_ANALYSIS,
            EvidenceStrength.INDEPENDENT_VALIDATION,
            EvidenceStrength.DOCUMENTED_IMPLEMENTATION_FACT,
        )


class RuleChangeClass(str, Enum):
    """Classification of modifications to governance rules for monotonic safety."""
    STRENGTHENING = "STRENGTHENING"
    NARROWING = "NARROWING"
    BROADENING = "BROADENING"
    WEAKENING = "WEAKENING"
    SEMANTIC_CHANGE = "SEMANTIC_CHANGE"


class AssumptionState(str, Enum):
    """Epistemic states for operational and scientific assumptions."""
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    DEPRECATED = "DEPRECATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class NoveltyFlag(str, Enum):
    """Classification of novel risk or operational surfaces."""
    NOVEL = "NOVEL"
    POTENTIALLY_NOVEL = "POTENTIALLY_NOVEL"
    KNOWN_BUT_UNPROTECTED = "KNOWN_BUT_UNPROTECTED"
    KNOWN = "KNOWN"


class ReworkClass(str, Enum):
    """Taxonomy of rework and incident root causes."""
    NEW_FAILURE = "NEW_FAILURE"
    KNOWN_FAILURE_MISSED = "KNOWN_FAILURE_MISSED"
    KNOWN_FAILURE_TEST_FAILED = "KNOWN_FAILURE_TEST_FAILED"
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
    RULE_APPLICATION_FAILURE = "RULE_APPLICATION_FAILURE"
    CONFLICTING_RULE = "CONFLICTING_RULE"
    MISSING_IMPLEMENTATION_CHECK = "MISSING_IMPLEMENTATION_CHECK"
    DOCUMENTATION_ONLY = "DOCUMENTATION_ONLY"


class NegativeFeedbackCategory(str, Enum):
    """Canonical taxonomy of failures in the learning and governance control mechanism.
    
    Distinguishes failure of the learning system itself from operational rework classes.
    """
    FALSE_BLOCK = "FALSE_BLOCK"
    MISSED_LESSON = "MISSED_LESSON"
    WRONG_APPLICABILITY = "WRONG_APPLICABILITY"
    WRONG_SCOPE = "WRONG_SCOPE"
    WRONG_PRECEDENCE = "WRONG_PRECEDENCE"
    WEAK_ENFORCEMENT = "WEAK_ENFORCEMENT"
    STALE_LESSON = "STALE_LESSON"
    DUPLICATE_LESSON = "DUPLICATE_LESSON"
    CONTRADICTORY_LESSON = "CONTRADICTORY_LESSON"


class ControlStage(str, Enum):
    """Stages of the learning-to-prevention control chain."""
    LESSON_EXISTS = "LESSON_EXISTS"
    LESSON_RETRIEVED = "LESSON_RETRIEVED"
    LESSON_APPLICABLE = "LESSON_APPLICABLE"
    LESSON_PRESENTED = "LESSON_PRESENTED"
    RULE_APPLIED = "RULE_APPLIED"
    MISTAKE_PREVENTED = "MISTAKE_PREVENTED"


class ControlStageOutcome(str, Enum):
    """Bounded observation semantics for a control stage.
    
    Distinguishes verified presence, verified absence, unobserved/uninstrumented,
    and not applicable states.
    """
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class ControlTraceRecord:
    """Observation of a single control stage in the learning-to-prevention pipeline."""
    stage: ControlStage
    outcome: ControlStageOutcome
    observed_at: str = ""
    reason: str = ""
    entity_refs: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    source: str = "governance_preflight"
    control_trace_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value if isinstance(self.stage, ControlStage) else str(self.stage),
            "outcome": self.outcome.value if isinstance(self.outcome, ControlStageOutcome) else str(self.outcome),
            "observed_at": self.observed_at,
            "reason": self.reason,
            "entity_refs": list(self.entity_refs),
            "evidence_refs": list(self.evidence_refs),
            "source": self.source,
            "control_trace_id": self.control_trace_id,
        }


@dataclass
class Principle:
    """A durable statement of scientific or engineering truth."""
    principle_id: str
    title: str
    statement: str
    rationale: str
    scope: ScopeLevel = ScopeLevel.GLOBAL
    domain: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["scope"] = self.scope.value
        return d


@dataclass
class FailureClass:
    """A reusable category of engineering or scientific failure."""
    class_id: str
    name: str
    description: str
    parent_class: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    typical_severity: SeverityLevel = SeverityLevel.HIGH
    prevention_guideline: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["typical_severity"] = self.typical_severity.value
        return d


@dataclass
class Incident:
    """A concrete historical occurrence where a failure or anomaly manifested."""
    incident_id: str
    task_id: str
    title: str
    failure_class: str
    description: str
    root_cause: str
    impact: str
    detection: str
    correction: str
    prevention: str
    evidence: str = ""
    lessons_created: List[str] = field(default_factory=list)
    rules_created: List[str] = field(default_factory=list)
    tests_created: List[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Rule:
    """An actionable, enforceable prevention requirement."""
    rule_id: str
    principle_id: str
    failure_class: str
    title: str
    statement: str
    scope: ScopeLevel = ScopeLevel.GLOBAL
    severity: SeverityLevel = SeverityLevel.HIGH
    action: ActionType = ActionType.BLOCK
    applies_to: Dict[str, Any] = field(default_factory=dict)
    prohibited_actions: List[str] = field(default_factory=list)
    required_checks: List[str] = field(default_factory=list)
    regression_test_ids: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    incident_refs: List[str] = field(default_factory=list)
    supersedes: List[str] = field(default_factory=list)
    superseded_by: Optional[str] = None
    status: LearningState = LearningState.REGRESSION_PROTECTED
    non_overridable: bool = False
    precedence_weight: int = 0
    evidence_lineage: Dict[str, Any] = field(default_factory=dict)
    evidence_strength: EvidenceStrength = EvidenceStrength.DIRECT_MEASUREMENT

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["scope"] = self.scope.value
        d["severity"] = self.severity.value
        d["action"] = self.action.value
        d["status"] = self.status.value
        d["evidence_strength"] = self.evidence_strength.value if hasattr(self.evidence_strength, "value") else str(self.evidence_strength)
        return d


@dataclass
class ValidationRecord:
    """A single verifiable historical validation event."""
    task: str
    timestamp: str
    test: str
    result: str
    environment: str = "python-3.10"
    scope: str = "regression"
    evidence: str = ""
    fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Lesson:
    """Durable knowledge extracted from historical experience."""
    lesson_id: str
    title: str
    principle_id: str
    failure_class: str
    severity: SeverityLevel
    scope: ScopeLevel
    description: str
    root_cause: str
    incorrect_behavior: str
    correct_rule: str
    prevention_method: str
    rules: List[str] = field(default_factory=list)
    incidents: List[str] = field(default_factory=list)
    required_checks: List[str] = field(default_factory=list)
    regression_test_ids: List[str] = field(default_factory=list)
    status: LearningState = LearningState.REGRESSION_PROTECTED
    validation_history: List[ValidationRecord] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    category: str = "SCIENTIFIC_VALIDITY"
    first_seen: str = ""
    last_seen: str = ""
    occurrence_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["scope"] = self.scope.value
        d["status"] = self.status.value
        d["validation_history"] = [v.to_dict() if isinstance(v, ValidationRecord) else v for v in self.validation_history]
        return d


@dataclass
class Assumption:
    """An explicit scientific, operational, or data assumption."""
    assumption_id: str
    statement: str
    status: AssumptionState = AssumptionState.UNVERIFIED
    scope: ScopeLevel = ScopeLevel.PROJECT
    verification_method: str = ""
    associated_rules: List[str] = field(default_factory=list)
    verified_in_task: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["scope"] = self.scope.value
        return d


@dataclass
class TaskContext:
    """Normalized representation of a task or proposed execution step."""
    task_id: str = ""
    project: str = "Ocean Sentinel"
    task_type: str = "diagnostic"
    experiment: Optional[str] = None
    diagnostic: Optional[str] = None
    domain: List[str] = field(default_factory=list)
    operation: List[str] = field(default_factory=list)
    model: Optional[str] = None
    dataset: Optional[str] = None
    partition: Optional[str] = None
    observation_unit: Optional[str] = None
    inference_unit: Optional[str] = None
    statistical_test: Optional[str] = None
    artifact_type: Optional[str] = None
    risk_class: List[str] = field(default_factory=list)
    proposed_plan: Optional[str] = None
    proposed_command: Optional[str] = None
    active_assumptions: List[str] = field(default_factory=list)
    telemetry_state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PreflightIssueV2:
    """A concrete finding emitted by the governance evaluation engine."""
    severity: SeverityLevel
    code: str
    rule_id: str
    message: str
    remediation: str
    test_ids: List[str] = field(default_factory=list)
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class RetrievalResult:
    """An item returned by the hybrid retrieval engine with explicit match reason."""
    item_id: str
    item_type: str  # "rule", "lesson", "principle", "incident", "assumption"
    score: float
    relevance_reason: str
    scope_match: bool
    failure_class_match: bool
    severity: SeverityLevel
    status: LearningState
    item: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["status"] = self.status.value
        return d


@dataclass
class PreflightV2Result:
    """Complete, human-auditable preflight response for future agents."""
    passed: bool
    task_id: str
    task_type: str
    elapsed_seconds: float
    relevant_lessons: List[RetrievalResult] = field(default_factory=list)
    applicable_rules: List[Rule] = field(default_factory=list)
    required_assumptions: List[Assumption] = field(default_factory=list)
    required_checks: List[str] = field(default_factory=list)
    blockers: List[PreflightIssueV2] = field(default_factory=list)
    warnings: List[PreflightIssueV2] = field(default_factory=list)
    recommendations: List[PreflightIssueV2] = field(default_factory=list)
    relevant_tests: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    novelty_flags: List[Dict[str, Any]] = field(default_factory=list)
    receipt_written: bool = False
    receipt_path: Optional[str] = None
    control_trace: List[ControlTraceRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "elapsed_seconds": round(self.elapsed_seconds, 4),
            "relevant_lessons_count": len(self.relevant_lessons),
            "relevant_lessons": [r.to_dict() for r in self.relevant_lessons],
            "applicable_rules_count": len(self.applicable_rules),
            "applicable_rules": [r.to_dict() for r in self.applicable_rules],
            "required_assumptions_count": len(self.required_assumptions),
            "required_assumptions": [a.to_dict() for a in self.required_assumptions],
            "required_checks": self.required_checks,
            "blockers_count": len(self.blockers),
            "blockers": [b.to_dict() for b in self.blockers],
            "warnings_count": len(self.warnings),
            "warnings": [w.to_dict() for w in self.warnings],
            "recommendations": [rc.to_dict() for rc in self.recommendations],
            "relevant_tests": self.relevant_tests,
            "conflicts": self.conflicts,
            "novelty_flags": self.novelty_flags,
            "receipt_written": self.receipt_written,
            "receipt_path": self.receipt_path,
            "control_trace_count": len(self.control_trace),
            "control_trace": [t.to_dict() if hasattr(t, "to_dict") else t for t in self.control_trace],
        }


# ==============================================================================
# Phase 10 Quantitative Effectiveness Metrics & Trace Analytics Models
# ==============================================================================

class MetricStatus(str, Enum):
    """Four-valued bounded metric status enforcing zero-fabrication guarantees.
    
    Invariants:
    - MEASURED: A valid metric result computed from sufficient, valid evidence
      appropriate to that specific metric, with all required preconditions satisfied
      and a valid non-zero denominator where the metric requires one. Ground truth
      is required only for metrics that genuinely require an independent/adjudicated
      ground truth source.
    - UNKNOWN: Target state is unobservable, uninstrumented, or indeterminate.
    - INSUFFICIENT_DATA: Metric is applicable, but required evidence is incomplete or inadequate.
    - NOT_APPLICABLE: There is genuinely no eligible population / mathematical domain.
    """
    MEASURED = "MEASURED"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"



@dataclass
class MetricResult:
    """Compact, evidence-oriented metric result structure."""
    metric_id: str
    metric_version: str = "1.0.0"
    status: MetricStatus = MetricStatus.UNKNOWN
    value: Optional[float] = None
    numerator: Optional[Union[int, float]] = None
    denominator: Optional[Union[int, float]] = None
    population_definition: str = ""
    eligibility_definition: str = ""
    evaluation_set_id: Optional[str] = None
    source_trace_ids: List[str] = field(default_factory=list)
    source_receipt_ids: List[str] = field(default_factory=list)
    computed_at: str = ""
    warnings: List[str] = field(default_factory=list)
    schema_version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "metric_version": self.metric_version,
            "status": self.status.value if isinstance(self.status, MetricStatus) else str(self.status),
            "value": round(self.value, 4) if self.value is not None else None,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "population_definition": self.population_definition,
            "eligibility_definition": self.eligibility_definition,
            "evaluation_set_id": self.evaluation_set_id,
            "source_trace_ids": list(self.source_trace_ids),
            "source_receipt_ids": list(self.source_receipt_ids),
            "computed_at": self.computed_at,
            "warnings": list(self.warnings),
            "schema_version": self.schema_version,
            "metadata": dict(self.metadata),
        }


@dataclass
class ClientPresentationEvent:
    """Client/operator presentation event recording UI display of governance entities."""
    event_id: str
    lesson_id: str
    client_id: str
    rendered_at: str
    session_id: str = ""
    interaction_type: str = "RENDERED"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AdjudicatedTaskRecord:
    """Task record with ground-truth relevance or correctness annotations for evaluation."""
    task_id: str
    task_type: str = ""
    task_context: Dict[str, Any] = field(default_factory=dict)
    ground_truth_relevant_lesson_ids: Optional[List[str]] = None
    preflight_passed: Optional[bool] = None
    is_block_accurate: Optional[bool] = None  # True if block was legitimate/correct, False if false block, None if unadjudicated
    adjudicated_by: str = ""
    adjudication_timestamp: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MetricEvaluationBatch:
    """Deterministic offline batch representation for trace and receipt evaluation.

    Hash Layer Contract (CONTRACT B: Semantic Input Dataset Identity):
    - dataset_hash: Deterministic canonicalized semantic input identity.
      Binds canonical semantic task context, ground-truth annotations, preflight adjudication,
      and stable receipt payloads, strictly excluding volatile write timestamps and run metadata.
    - evaluation_manifest_hash / batch_result_hash: Batch evaluation result identity.
      Binds dataset_hash, run metadata (batch_id), metric keys, and computed metric results.
    """
    batch_id: str
    dataset_hash: str
    source_manifest: Dict[str, Any] = field(default_factory=dict)
    validated_records: List[Dict[str, Any]] = field(default_factory=list)
    quarantined_records: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, MetricResult] = field(default_factory=dict)
    computed_at: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    is_synthetic_fixture: bool = False
    synthetic_fixture_label: str = ""
    evaluation_manifest_hash: str = ""
    batch_result_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "dataset_hash": self.dataset_hash,
            "evaluation_manifest_hash": self.evaluation_manifest_hash,
            "batch_result_hash": self.batch_result_hash,
            "source_manifest": self.source_manifest,
            "validated_records_count": len(self.validated_records),
            "quarantined_records_count": len(self.quarantined_records),
            "quarantined_records": self.quarantined_records,
            "metrics": {k: m.to_dict() for k, m in self.metrics.items()},
            "computed_at": self.computed_at,
            "provenance": self.provenance,
            "is_synthetic_fixture": self.is_synthetic_fixture,
            "synthetic_fixture_label": self.synthetic_fixture_label,
        }
