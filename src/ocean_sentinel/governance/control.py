"""Control-Effectiveness Tracking and Negative Feedback Instrumentation Layer.

Enforces strict separation of the six-stage learning-to-prevention control chain:
  lesson_exists != lesson_retrieved != lesson_applicable != lesson_presented != rule_applied != mistake_prevented

And provides tamper-evident negative feedback receipt persistence without modifying
canonical Governance V2 catalogs or enabling autonomous learning/promotion.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import uuid

from ocean_sentinel.governance.models import (
    ControlStage,
    ControlStageOutcome,
    ControlTraceRecord,
    NegativeFeedbackCategory,
    ReworkClass,
)
from ocean_sentinel.governance.provenance import canonicalize_json_v1

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_FEEDBACK_DIR = REPO_ROOT / "outputs" / "receipts" / "learning_feedback"

# Canonical ordering of control stages for deterministic trace emission
ORDERED_CONTROL_STAGES: List[ControlStage] = [
    ControlStage.LESSON_EXISTS,
    ControlStage.LESSON_RETRIEVED,
    ControlStage.LESSON_APPLICABLE,
    ControlStage.LESSON_PRESENTED,
    ControlStage.RULE_APPLIED,
    ControlStage.MISTAKE_PREVENTED,
]

# Non-authoritative mapping from NegativeFeedbackCategory to operational ReworkClass
NON_AUTHORITATIVE_FEEDBACK_TO_REWORK_MAPPING: Dict[NegativeFeedbackCategory, ReworkClass] = {
    NegativeFeedbackCategory.FALSE_BLOCK: ReworkClass.RULE_APPLICATION_FAILURE,
    NegativeFeedbackCategory.MISSED_LESSON: ReworkClass.KNOWN_FAILURE_MISSED,
    NegativeFeedbackCategory.WRONG_APPLICABILITY: ReworkClass.RULE_APPLICATION_FAILURE,
    NegativeFeedbackCategory.WRONG_SCOPE: ReworkClass.RULE_APPLICATION_FAILURE,
    NegativeFeedbackCategory.WRONG_PRECEDENCE: ReworkClass.CONFLICTING_RULE,
    NegativeFeedbackCategory.WEAK_ENFORCEMENT: ReworkClass.MISSING_IMPLEMENTATION_CHECK,
    NegativeFeedbackCategory.STALE_LESSON: ReworkClass.DOCUMENTATION_ONLY,
    NegativeFeedbackCategory.DUPLICATE_LESSON: ReworkClass.DOCUMENTATION_ONLY,
    NegativeFeedbackCategory.CONTRADICTORY_LESSON: ReworkClass.CONFLICTING_RULE,
}


def _coerce_stage(stage: Union[ControlStage, str]) -> ControlStage:
    """Safely converts string or enum to ControlStage, rejecting invalid inputs."""
    if isinstance(stage, ControlStage):
        return stage
    try:
        return ControlStage[str(stage).strip().upper()]
    except (KeyError, ValueError):
        raise ValueError(f"Invalid ControlStage: '{stage}'. Must be one of {[s.value for s in ControlStage]}")


def _coerce_outcome(outcome: Union[ControlStageOutcome, str]) -> ControlStageOutcome:
    """Safely converts string or enum to ControlStageOutcome, rejecting invalid inputs."""
    if isinstance(outcome, ControlStageOutcome):
        return outcome
    try:
        return ControlStageOutcome[str(outcome).strip().upper()]
    except (KeyError, ValueError):
        raise ValueError(f"Invalid ControlStageOutcome: '{outcome}'. Must be one of {[o.value for o in ControlStageOutcome]}")


def _coerce_feedback_category(category: Union[NegativeFeedbackCategory, str]) -> NegativeFeedbackCategory:
    """Safely converts string or enum to NegativeFeedbackCategory, rejecting invalid inputs."""
    if isinstance(category, NegativeFeedbackCategory):
        return category
    try:
        return NegativeFeedbackCategory[str(category).strip().upper()]
    except (KeyError, ValueError):
        raise ValueError(f"Invalid NegativeFeedbackCategory: '{category}'. Must be one of {[c.value for c in NegativeFeedbackCategory]}")


def resolve_rule_applied_outcome(
    applicable_rules_count: Optional[int],
    applied_rules_count: int,
    active_rules_count: Optional[int] = None,
) -> Tuple[ControlStageOutcome, str]:
    """Determines the exact bounded ControlStageOutcome for RULE_APPLIED.
    
    Enforces the semantic matrix:
    - Case 1: active=0, applicable=0, applied=0 => NOT_APPLICABLE
    - Case 2: active>0, applicable=0, applied=0 => NOT_APPLICABLE
    - Case 3: active>=0, applicable>0, applied=0 => FALSE
    - Case 4: applicable>0, applied>0 => TRUE
    - Case 5: indeterminate applicability/enforcement => UNKNOWN
    
    Strict Invariants:
    - Active rules count is NOT an applicability proxy.
    - Zero applied rules does NOT imply NOT_APPLICABLE if applicable rules > 0.
    """
    if applicable_rules_count is None:
        return (
            ControlStageOutcome.UNKNOWN,
            "Applicability evaluation was indeterminate or unobserved; cannot determine RULE_APPLIED."
        )

    if applied_rules_count > 0:
        return (
            ControlStageOutcome.TRUE,
            f"Enforcement engine applied {applied_rules_count} rule(s) contributing to preflight decision."
        )

    if applicable_rules_count == 0:
        active_ctx = f" (across {active_rules_count} active catalog rule(s))" if active_rules_count is not None else ""
        return (
            ControlStageOutcome.NOT_APPLICABLE,
            f"Zero rules applicable to current task context{active_ctx}; no rule application evaluated."
        )

    # applicable_rules_count > 0 and applied_rules_count == 0
    return (
        ControlStageOutcome.FALSE,
        f"{applicable_rules_count} rule(s) were applicable but none triggered violations against proposed context."
    )


class ControlEffectivenessTracker:
    """In-memory trace builder for recording learning-to-prevention control stage observations.
    
    Adheres strictly to the Anti-Fabrication Principles:
    - Does NOT infer presentation from retrieval.
    - Does NOT infer mistake prevention from enforcement blocking.
    - Does NOT fabricate FALSE when a stage is merely unobserved/uninstrumented.
    - Does NOT equate active rules with applicable rules or applicable rules with applied rules.
    - Prevents contradictory overwrites of the same stage within a trace.
    - Pure in-memory construction; emits no unauthorized state mutations.
    """

    def __init__(self, trace_id: Optional[str] = None, task_id: str = ""):
        self.task_id = task_id or "TASK-UNSPECIFIED"
        self.trace_id = trace_id or f"trace_{self.task_id}_{uuid.uuid4().hex[:12]}"
        self._records: Dict[ControlStage, ControlTraceRecord] = {}
        self._finalized: bool = False

    def record_rule_applied(
        self,
        applicable_rules_count: Optional[int],
        applied_rule_ids: Optional[Sequence[str]] = None,
        active_rules_count: Optional[int] = None,
        source: str = "governance_preflight_enforcement",
        timestamp: Optional[str] = None,
    ) -> ControlTraceRecord:
        """Records the RULE_APPLIED control stage enforcing the active vs applicable vs applied matrix."""
        applied_ids = list(applied_rule_ids or [])
        outcome, reason = resolve_rule_applied_outcome(
            applicable_rules_count=applicable_rules_count,
            applied_rules_count=len(applied_ids),
            active_rules_count=active_rules_count,
        )
        entity_refs = applied_ids if outcome == ControlStageOutcome.TRUE else []
        return self.record_stage(
            stage=ControlStage.RULE_APPLIED,
            outcome=outcome,
            reason=reason,
            entity_refs=entity_refs,
            source=source,
            timestamp=timestamp,
        )

    def record_stage(
        self,
        stage: Union[ControlStage, str],
        outcome: Union[ControlStageOutcome, str],
        reason: str = "",
        entity_refs: Optional[Sequence[str]] = None,
        evidence_refs: Optional[Sequence[str]] = None,
        source: str = "governance_preflight",
        timestamp: Optional[str] = None,
    ) -> ControlTraceRecord:
        """Records an observed control stage outcome.
        
        Raises ValueError if an attempt is made to overwrite an already recorded stage
        with a contradictory outcome.
        """
        if self._finalized:
            raise RuntimeError("Cannot record stage: ControlEffectivenessTracker is already finalized.")

        c_stage = _coerce_stage(stage)
        c_outcome = _coerce_outcome(outcome)

        # Anti-fabrication check: preflight cannot mark LESSON_EXISTS as TRUE/FALSE based on retrieval alone
        if c_stage == ControlStage.LESSON_EXISTS and c_outcome in (ControlStageOutcome.TRUE, ControlStageOutcome.FALSE):
            if source and "retrieval" in source.lower():
                raise ValueError(
                    "FABRICATION_GUARD: LESSON_EXISTS cannot be derived directly from retrieval observation alone. "
                    "Retrieval outcome (LESSON_RETRIEVED) does not constitute independent lesson existence proof."
                )

        # Anti-fabrication check: preflight cannot mark LESSON_PRESENTED as TRUE without explicit UI evidence
        if c_stage == ControlStage.LESSON_PRESENTED and c_outcome == ControlStageOutcome.TRUE:
            if not source or "ui" not in source.lower() and "operator" not in source.lower() and "client" not in source.lower():
                raise ValueError(
                    "FABRICATION_GUARD: LESSON_PRESENTED cannot be marked TRUE by preflight alone. "
                    "Explicit UI, client, or operator presentation evidence is required."
                )

        # Anti-fabrication check: preflight cannot mark MISTAKE_PREVENTED as TRUE without explicit outcome evidence
        if c_stage == ControlStage.MISTAKE_PREVENTED and c_outcome == ControlStageOutcome.TRUE:
            if not evidence_refs or len(evidence_refs) == 0:
                raise ValueError(
                    "FABRICATION_GUARD: MISTAKE_PREVENTED cannot be marked TRUE without explicit "
                    "post-action outcome evidence references."
                )

        # Overwrite protection: prevent contradictory overwrites
        if c_stage in self._records:
            existing = self._records[c_stage]
            if existing.outcome != c_outcome:
                raise ValueError(
                    f"Contradictory overwrite rejected for {c_stage.value}: "
                    f"existing outcome is '{existing.outcome.value}', cannot overwrite with '{c_outcome.value}'."
                )
            # Idempotent overwrite with same outcome: keep existing or update metadata
            return existing

        ts = timestamp or datetime.now(timezone.utc).isoformat()
        record = ControlTraceRecord(
            stage=c_stage,
            outcome=c_outcome,
            observed_at=ts,
            reason=reason,
            entity_refs=list(entity_refs or []),
            evidence_refs=list(evidence_refs or []),
            source=source,
            control_trace_id=self.trace_id,
        )
        self._records[c_stage] = record
        return record

    def get_stage_record(self, stage: Union[ControlStage, str]) -> Optional[ControlTraceRecord]:
        """Returns the recorded observation for a stage, or None if not yet observed."""
        c_stage = _coerce_stage(stage)
        return self._records.get(c_stage)

    def finalize_trace(self) -> List[ControlTraceRecord]:
        """Finalizes and returns the complete, deterministic 6-stage control trace.
        
        Any stage that was not explicitly observed defaults to ControlStageOutcome.UNKNOWN,
        distinguishing absence of observation from confirmed absence (FALSE).
        """
        now_ts = datetime.now(timezone.utc).isoformat()

        # Fill unobserved stages with bounded UNKNOWN semantics
        for stage in ORDERED_CONTROL_STAGES:
            if stage not in self._records:
                reason = f"Stage {stage.value} was not observed or not instrumented in current pipeline."
                if stage == ControlStage.LESSON_EXISTS:
                    reason = (
                        "The current system has a retrieval operation but does not have an independent observation "
                        "proving that a relevant lesson exists separately from whether retrieval returned it."
                    )
                elif stage == ControlStage.LESSON_APPLICABLE:
                    reason = "Current applicability engine evaluates rules; lesson applicability is not evaluated."
                elif stage == ControlStage.LESSON_PRESENTED:
                    reason = "Preflight evaluation does not observe UI or downstream agent presentation."
                elif stage == ControlStage.MISTAKE_PREVENTED:
                    reason = "Preflight evaluation occurs before execution; outcome evidence not yet observable."

                self._records[stage] = ControlTraceRecord(
                    stage=stage,
                    outcome=ControlStageOutcome.UNKNOWN,
                    observed_at=now_ts,
                    reason=reason,
                    entity_refs=[],
                    evidence_refs=[],
                    source="governance_preflight_default",
                    control_trace_id=self.trace_id,
                )

        self._finalized = True
        return [self._records[s] for s in ORDERED_CONTROL_STAGES]


def record_negative_feedback(
    category: Union[NegativeFeedbackCategory, str],
    reason: str,
    control_trace_id: Optional[str] = None,
    entity_refs: Optional[Sequence[str]] = None,
    evidence_refs: Optional[Sequence[str]] = None,
    task_context: Optional[Dict[str, Any]] = None,
    source: str = "governance_agent",
    receipt_dir: Optional[Path] = None,
    receipt_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Records an integrity-checked, conflict-detecting negative feedback receipt to disk.
    
    Persistence Boundary:
    - Stores receipts in outputs/receipts/learning_feedback/
    - Does NOT modify canonical Governance V2 catalogs (rules.json, lessons.json, incidents.json)
    - Does NOT modify data/metadata/governance_v2/
    
    Integrity and Conflict Detection:
    - Fails closed if receipt already exists with a differing SHA-256 payload.
    - Uses atomic crash-safe local write (.tmp + os.replace).
    - Labels output accurately as INTEGRITY-CHECKED LOCAL RECEIPT (no digital signature,
      no non-repudiation, and cannot prevent detection if an attacker maliciously rewrites
      both the payload and digest simultaneously). Telemetry remains strictly observational.
    """
    cat = _coerce_feedback_category(category)
    if not reason or not reason.strip():
        raise ValueError("Cannot record negative feedback without an explicit reason.")

    ts = datetime.now(timezone.utc).isoformat()
    r_id = receipt_id or f"rcpt_fb_{cat.value.lower()}_{uuid.uuid4().hex[:12]}"
    target_dir = receipt_dir or DEFAULT_FEEDBACK_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    receipt_payload: Dict[str, Any] = {
        "receipt_id": r_id,
        "schema_version": "1.0.0",
        "receipt_type": "INTEGRITY_CHECKED_NEGATIVE_FEEDBACK_RECEIPT",
        "category": cat.value,
        "recorded_at": ts,
        "control_trace_id": control_trace_id or "",
        "entity_refs": list(entity_refs or []),
        "evidence_refs": list(evidence_refs or []),
        "task_context": dict(task_context or {}),
        "source": source,
        "reason": reason.strip(),
    }

    # Deterministic canonical serialization & SHA-256 computation
    canonical_bytes = canonicalize_json_v1(receipt_payload)
    payload_sha256 = hashlib.sha256(canonical_bytes).hexdigest()

    final_envelope: Dict[str, Any] = {
        **receipt_payload,
        "payload_sha256": payload_sha256,
        "integrity_note": (
            "INTEGRITY-CHECKED LOCAL RECEIPT: SHA-256 payload digests provide local payload-integrity checks "
            "and conflicting overwrite detection when the recorded digest remains trustworthy. "
            "This receipt does not establish external identity, digital signatures, or cryptographic non-repudiation, "
            "and cannot prevent detection if an attacker with local filesystem access maliciously rewrites "
            "both the payload and digest simultaneously. Telemetry remains strictly observational."
        ),
    }

    receipt_file = target_dir / f"{r_id}.json"

    # Fail-closed protection against conflicting receipt mutation
    if receipt_file.exists():
        try:
            existing_data = json.loads(receipt_file.read_text(encoding="utf-8"))
            if existing_data.get("payload_sha256") != payload_sha256:
                raise RuntimeError(
                    f"TAMPER_PROTECTION_ERROR: Receipt '{r_id}' already exists on disk with differing payload SHA-256 "
                    f"({existing_data.get('payload_sha256')} vs {payload_sha256}). Conflicting overwrite strictly refused."
                )
            # Idempotent return of existing verified receipt
            return existing_data
        except (json.JSONDecodeError, OSError) as e:
            raise RuntimeError(
                f"TAMPER_PROTECTION_ERROR: Existing receipt '{r_id}' is corrupt or unreadable: {e}. Overwrite refused."
            )

    # Atomic write pattern: write to tmp file then atomic replace
    tmp_file = target_dir / f"{r_id}.json.tmp_{uuid.uuid4().hex[:8]}"
    try:
        tmp_file.write_bytes(json.dumps(final_envelope, indent=2, sort_keys=True).encode("utf-8"))
        os.replace(tmp_file, receipt_file)
    except Exception as e:
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass
        raise RuntimeError(f"Failed to persist feedback receipt '{r_id}': {e}")

    return final_envelope
