"""Quantitative Effectiveness Metrics & Trace Analytics Engine for Ocean Sentinel.

Implements Phase 10:
- Bounded 4-valued metric evaluation (MEASURED, UNKNOWN, INSUFFICIENT_DATA, NOT_APPLICABLE)
- Zero-fabrication guarantee: missing oracles, denominators, labels, or causal evidence
  strictly yield UNKNOWN or INSUFFICIENT_DATA, never fabricated 0.0.
- Offline negative-feedback receipt ingestion with JSON schema validation,
  SHA-256 payload digest verification, conflict detection on duplicate IDs, and quarantine.
- Deterministic offline evaluation batch generation with explicit synthetic fixture isolation.
- Purely observational analytics: cannot mutate authorization decisions, cannot promote
  rules or lessons, and never modifies canonical Governance V2 catalogs.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from ocean_sentinel.governance.models import (
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
    PreflightV2Result,
    Rule,
)
from ocean_sentinel.governance.provenance import canonicalize_json_v1

# Schema versions
METRIC_SCHEMA_VERSION: str = "1.0.0"
BATCH_SCHEMA_VERSION: str = "1.0.0"

# Canonical receipt fields hashed by record_negative_feedback
CANONICAL_RECEIPT_HASH_FIELDS = (
    "receipt_id",
    "schema_version",
    "receipt_type",
    "category",
    "recorded_at",
    "control_trace_id",
    "entity_refs",
    "evidence_refs",
    "task_context",
    "source",
    "reason",
)


class ConflictingReceiptError(RuntimeError):
    """Raised when two receipts share the same receipt_id but possess conflicting content."""
    pass


# ==============================================================================
# 1. Receipt Ingestion & Quarantine Pipeline
# ==============================================================================

def validate_and_extract_receipt_payload(raw_data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Validates raw receipt dictionary structure against required schema fields.
    
    Returns:
        (is_valid, error_reason, canonical_payload_dict)
    """
    if not isinstance(raw_data, dict):
        return False, "INVALID_ROOT_TYPE: Expected JSON object", None

    required_fields = ["receipt_id", "schema_version", "category", "reason", "recorded_at"]
    missing = [f for f in required_fields if f not in raw_data or raw_data[f] is None]
    if missing:
        return False, f"MISSING_SCHEMA_FIELDS: {', '.join(missing)}", None

    # Validate category coercion
    raw_cat = raw_data.get("category")
    try:
        if isinstance(raw_cat, NegativeFeedbackCategory):
            cat_enum = raw_cat
        else:
            cat_enum = NegativeFeedbackCategory[str(raw_cat).strip().upper()]
    except (KeyError, AttributeError):
        return False, f"UNKNOWN_CATEGORY: '{raw_cat}' is not a valid NegativeFeedbackCategory", None

    # Construct the canonical payload dictionary for digest verification
    canonical_payload = {
        "receipt_id": str(raw_data["receipt_id"]),
        "schema_version": str(raw_data["schema_version"]),
        "receipt_type": str(raw_data.get("receipt_type", "INTEGRITY_CHECKED_NEGATIVE_FEEDBACK_RECEIPT")),
        "category": cat_enum.value,
        "recorded_at": str(raw_data["recorded_at"]),
        "control_trace_id": str(raw_data.get("control_trace_id", "")),
        "entity_refs": list(raw_data.get("entity_refs") or []),
        "evidence_refs": list(raw_data.get("evidence_refs") or []),
        "task_context": dict(raw_data.get("task_context") or {}),
        "source": str(raw_data.get("source", "governance_agent")),
        "reason": str(raw_data["reason"]).strip(),
    }
    return True, None, canonical_payload


def verify_receipt_sha256(raw_data: Dict[str, Any], canonical_payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Verifies that the recorded payload_sha256 matches canonicalize_json_v1 digest."""
    recorded_sha = raw_data.get("payload_sha256")
    if not recorded_sha:
        return False, "MISSING_PAYLOAD_SHA256: Receipt lacks payload digest"

    canonical_bytes = canonicalize_json_v1(canonical_payload)
    computed_sha = hashlib.sha256(canonical_bytes).hexdigest()

    if recorded_sha != computed_sha:
        return False, f"CORRUPTED_DIGEST_MISMATCH: Recorded {recorded_sha} != Computed {computed_sha}"

    return True, None


def ingest_negative_feedback_receipts(
    receipt_sources: Union[Path, str, Sequence[Union[Path, str, Dict[str, Any]]]],
    fail_closed_on_conflict: bool = True,
) -> Dict[str, Any]:
    """Ingests negative feedback receipts from paths or dictionaries.
    
    Guarantees:
    - Rejects malformed JSON syntax.
    - Validates schema and category.
    - Verifies canonical SHA-256 payload digest.
    - Quarantines invalid or corrupt records.
    - Deterministically deduplicates identical records (same ID, same digest).
    - Fails closed on conflicting records (same ID, differing content/digest).
    - Never mutates canonical governance catalogs.
    
    Returns:
        Dict with keys:
            - validated_records: List[Dict[str, Any]]
            - quarantined_records: List[Dict[str, Any]]
            - duplicate_count: int
            - conflict_count: int
            - total_examined: int
    """
    items_to_process: List[Tuple[str, Union[str, Dict[str, Any]]]] = []
    read_quarantined: List[Dict[str, Any]] = []

    # Collect inputs
    if isinstance(receipt_sources, (str, Path)):
        p = Path(receipt_sources)
        if p.is_dir():
            for f in sorted(p.glob("*.json")):
                try:
                    items_to_process.append((f.name, f.read_text(encoding="utf-8")))
                except (OSError, UnicodeDecodeError) as e:
                    read_quarantined.append({
                        "source": f.name,
                        "quarantine_reason": f"READ_ERROR: {e}",
                        "raw_content": "",
                    })
        elif p.is_file():
            try:
                items_to_process.append((p.name, p.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError) as e:
                read_quarantined.append({
                    "source": p.name,
                    "quarantine_reason": f"READ_ERROR: {e}",
                    "raw_content": "",
                })
        else:
            items_to_process.append((str(receipt_sources), str(receipt_sources)))
    elif isinstance(receipt_sources, Sequence):
        for idx, src in enumerate(receipt_sources):
            if isinstance(src, (str, Path)):
                p = Path(src)
                if p.is_file():
                    try:
                        items_to_process.append((p.name, p.read_text(encoding="utf-8")))
                    except (OSError, UnicodeDecodeError) as e:
                        read_quarantined.append({
                            "source": p.name,
                            "quarantine_reason": f"READ_ERROR: {e}",
                            "raw_content": "",
                        })
                else:
                    items_to_process.append((f"item_{idx}.json", str(src)))
            elif isinstance(src, dict):
                items_to_process.append((f"dict_{idx}_{src.get('receipt_id', 'unknown')}", src))

    validated_by_id: Dict[str, Dict[str, Any]] = {}
    quarantined: List[Dict[str, Any]] = list(read_quarantined)
    duplicate_count: int = 0
    conflict_count: int = 0

    for source_name, raw_content in items_to_process:
        # Step A: Parse JSON
        if isinstance(raw_content, dict):
            parsed = raw_content
        else:
            try:
                parsed = json.loads(raw_content)
            except (json.JSONDecodeError, TypeError) as e:
                quarantined.append({
                    "source": source_name,
                    "quarantine_reason": f"MALFORMED_JSON: {e}",
                    "raw_content": str(raw_content)[:500],
                })
                continue

        # Step B: Validate schema & category
        is_valid, schema_err, canonical_payload = validate_and_extract_receipt_payload(parsed)
        if not is_valid or canonical_payload is None:
            quarantined.append({
                "source": source_name,
                "receipt_id": parsed.get("receipt_id") if isinstance(parsed, dict) else None,
                "quarantine_reason": schema_err or "INVALID_SCHEMA",
                "raw_content": parsed,
            })
            continue

        # Step C: Verify digest
        is_digest_valid, digest_err = verify_receipt_sha256(parsed, canonical_payload)
        if not is_digest_valid:
            quarantined.append({
                "source": source_name,
                "receipt_id": canonical_payload["receipt_id"],
                "quarantine_reason": digest_err or "DIGEST_FAILURE",
                "raw_content": parsed,
            })
            continue

        # Step D: Duplicate and Conflict Handling
        r_id = canonical_payload["receipt_id"]
        current_digest = parsed.get("payload_sha256")

        if r_id in validated_by_id:
            existing = validated_by_id[r_id]
            existing_digest = existing.get("payload_sha256")
            if existing_digest == current_digest:
                # Idempotent identical duplicate
                duplicate_count += 1
                continue
            else:
                # Conflicting duplicate! Same ID with differing content/digest
                conflict_count += 1
                conflict_msg = (
                    f"RECEIPT_INTEGRITY_CONFLICT_ERROR: Conflicting receipt detected for ID '{r_id}'. "
                    f"Existing SHA-256 ({existing_digest}) differs from incoming ({current_digest}). Overwrite refused."
                )
                if fail_closed_on_conflict:
                    raise ConflictingReceiptError(conflict_msg)
                else:
                    quarantined.append({
                        "source": source_name,
                        "receipt_id": r_id,
                        "quarantine_reason": f"CONFLICTING_DUPLICATE: {conflict_msg}",
                        "raw_content": parsed,
                    })
                    continue

        # Validated record accepted
        validated_by_id[r_id] = parsed

    # Return sorted deterministic list of validated records
    sorted_validated = sorted(validated_by_id.values(), key=lambda r: str(r.get("receipt_id", "")))
    total_candidates = len(items_to_process) + len(read_quarantined)
    return {
        "validated_records": sorted_validated,
        "quarantined_records": quarantined,
        "duplicate_count": duplicate_count,
        "conflict_count": conflict_count,
        "read_error_count": len(read_quarantined),
        "total_candidates_encountered": total_candidates,
        "total_examined": total_candidates,  # Preserved compatibility alias
    }


# ==============================================================================
# 2. Metric 1: Retrieval Recall
# ==============================================================================

def compute_retrieval_recall(
    eval_tasks: Sequence[Union[AdjudicatedTaskRecord, Dict[str, Any]]],
    evaluation_set_id: Optional[str] = None,
    source_trace_ids: Optional[Sequence[str]] = None,
) -> MetricResult:
    """Computes retrieval recall over an adjudicated evaluation set with ground truth.
    
    Formula:
        Recall = Total relevant retrieved lessons / Total relevant lessons in evaluation set
        
    Anti-fabrication invariants:
    - If evaluation tasks are missing or lack ground truth labels -> INSUFFICIENT_DATA.
    - If total relevant lessons across the evaluation set is 0 -> NOT_APPLICABLE (value=None).
    - Missing ground truth is NEVER silently treated as 0.0.
    """
    ts = datetime.now(timezone.utc).isoformat()
    metric_id = "METRIC-RETRIEVAL-RECALL"
    pop_def = "Adjudicated task evaluation set with explicit ground-truth relevant lesson IDs"
    elig_def = "Tasks possessing non-empty ground_truth_relevant_lesson_ids in evaluation set"

    if not eval_tasks:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.INSUFFICIENT_DATA,
            value=None,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["Evaluation tasks sequence is empty; recall cannot be computed."],
        )

    total_relevant_lessons = 0
    relevant_retrieved_lessons = 0
    has_any_ground_truth = False

    for item in eval_tasks:
        if isinstance(item, AdjudicatedTaskRecord):
            raw_gt = item.ground_truth_relevant_lesson_ids
            gt_ids = set(raw_gt) if raw_gt is not None else None
            raw_ret = (item.task_context or {}).get("retrieved_lesson_ids")
            retrieved_ids = set(raw_ret or [])
        elif isinstance(item, dict):
            raw_gt = item.get("ground_truth_relevant_lesson_ids")
            gt_ids = set(raw_gt) if raw_gt is not None else None
            raw_ret = item.get("retrieved_lesson_ids")
            retrieved_ids = set(raw_ret or [])
        else:
            continue

        if gt_ids is not None:
            has_any_ground_truth = True
            total_relevant_lessons += len(gt_ids)
            relevant_retrieved_lessons += len(gt_ids.intersection(retrieved_ids))

    if not has_any_ground_truth:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.INSUFFICIENT_DATA,
            value=None,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["Evaluation tasks lack ground-truth relevance labels; recall requires an authoritative oracle."],
        )

    if total_relevant_lessons == 0:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            numerator=0,
            denominator=0,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["Zero relevant lessons in ground-truth evaluation set; recall denominator is zero."],
        )

    recall_val = round(relevant_retrieved_lessons / total_relevant_lessons, 4)
    return MetricResult(
        metric_id=metric_id,
        status=MetricStatus.MEASURED,
        value=recall_val,
        numerator=relevant_retrieved_lessons,
        denominator=total_relevant_lessons,
        population_definition=pop_def,
        eligibility_definition=elig_def,
        evaluation_set_id=evaluation_set_id,
        source_trace_ids=list(source_trace_ids or []),
        computed_at=ts,
    )


# ==============================================================================
# 3. Metric 2: Retrieval Precision
# ==============================================================================

def compute_retrieval_precision(
    eval_tasks: Sequence[Union[AdjudicatedTaskRecord, Dict[str, Any]]],
    evaluation_set_id: Optional[str] = None,
    source_trace_ids: Optional[Sequence[str]] = None,
) -> MetricResult:
    """Computes retrieval precision over an adjudicated evaluation set with ground truth.
    
    Formula:
        Precision = Total relevant retrieved lessons / Total retrieved lessons
        
    Anti-fabrication invariants:
    - If evaluation tasks lack ground truth labels -> INSUFFICIENT_DATA.
    - If total retrieved lessons across evaluation tasks is 0 -> NOT_APPLICABLE (value=None).
    """
    ts = datetime.now(timezone.utc).isoformat()
    metric_id = "METRIC-RETRIEVAL-PRECISION"
    pop_def = "Retrieved lesson instances across evaluated task cohort"
    elig_def = "Tasks with retrieved lessons evaluated against ground-truth relevance labels"

    if not eval_tasks:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.INSUFFICIENT_DATA,
            value=None,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["Evaluation tasks sequence is empty; precision cannot be computed."],
        )

    total_retrieved = 0
    relevant_retrieved = 0
    has_any_ground_truth = False

    for item in eval_tasks:
        if isinstance(item, AdjudicatedTaskRecord):
            raw_gt = item.ground_truth_relevant_lesson_ids
            gt_ids = set(raw_gt) if raw_gt is not None else None
            raw_ret = (item.task_context or {}).get("retrieved_lesson_ids")
            retrieved_ids = set(raw_ret or [])
        elif isinstance(item, dict):
            raw_gt = item.get("ground_truth_relevant_lesson_ids")
            gt_ids = set(raw_gt) if raw_gt is not None else None
            raw_ret = item.get("retrieved_lesson_ids")
            retrieved_ids = set(raw_ret or [])
        else:
            continue

        if gt_ids is not None:
            has_any_ground_truth = True
            total_retrieved += len(retrieved_ids)
            relevant_retrieved += len(gt_ids.intersection(retrieved_ids))

    if not has_any_ground_truth:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.INSUFFICIENT_DATA,
            value=None,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["Evaluation tasks lack ground-truth relevance labels; precision requires an authoritative oracle."],
        )

    if total_retrieved == 0:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            numerator=0,
            denominator=0,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["Zero lessons were retrieved across the evaluation cohort; precision denominator is zero."],
        )

    prec_val = round(relevant_retrieved / total_retrieved, 4)
    return MetricResult(
        metric_id=metric_id,
        status=MetricStatus.MEASURED,
        value=prec_val,
        numerator=relevant_retrieved,
        denominator=total_retrieved,
        population_definition=pop_def,
        eligibility_definition=elig_def,
        evaluation_set_id=evaluation_set_id,
        source_trace_ids=list(source_trace_ids or []),
        computed_at=ts,
    )


# ==============================================================================
# 4. Metric 3: False-Block Rate
# ==============================================================================

def compute_false_block_rate(
    eval_tasks: Sequence[Union[AdjudicatedTaskRecord, Dict[str, Any]]],
    denominator_basis: str = "adjudicated_blocks",
    evaluation_set_id: Optional[str] = None,
    source_trace_ids: Optional[Sequence[str]] = None,
) -> MetricResult:
    """Computes false-block rate from an explicitly adjudicated population.
    
    Formula:
        If denominator_basis == "adjudicated_blocks" (default):
            False-Block Rate = Verified false blocks / Total adjudicated blocks
        If denominator_basis == "all_adjudicated_tasks":
            False-Block Rate = Verified false blocks / Total adjudicated tasks
            
    Anti-fabrication invariants:
    - BLOCK status alone, user dissatisfaction, or negative feedback receipts alone
      NEVER prove a false block.
    - If tasks lack ground truth block correctness adjudication -> INSUFFICIENT_DATA.
    - If adjudicated denominator is zero -> NOT_APPLICABLE.
    """
    ts = datetime.now(timezone.utc).isoformat()
    metric_id = "METRIC-FALSE-BLOCK-RATE"
    pop_def = f"Adjudicated tasks evaluated for block correctness (basis: {denominator_basis})"
    elig_def = "Tasks possessing explicit is_block_accurate adjudication (True=correct, False=false-block)"

    if not eval_tasks:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.INSUFFICIENT_DATA,
            value=None,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["Evaluation tasks sequence is empty; false-block rate cannot be computed."],
        )

    adjudicated_blocks = 0
    verified_false_blocks = 0
    adjudicated_tasks = 0

    for item in eval_tasks:
        if isinstance(item, AdjudicatedTaskRecord):
            is_accurate = item.is_block_accurate
            passed = item.preflight_passed
        elif isinstance(item, dict):
            is_accurate = item.get("is_block_accurate")
            passed = item.get("preflight_passed")
        else:
            continue

        if is_accurate is not None:
            adjudicated_tasks += 1
            # If the task was blocked (passed is False, or passed is None with block accuracy recorded)
            if passed is False or (passed is None and is_accurate in (True, False)):
                adjudicated_blocks += 1
                if is_accurate is False:
                    verified_false_blocks += 1

    if adjudicated_tasks == 0:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.INSUFFICIENT_DATA,
            value=None,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=[
                "Missing ground-truth block correctness adjudication (is_block_accurate). "
                "BLOCK status and observational feedback alone do not constitute proof of false block."
            ],
        )

    denominator = adjudicated_blocks if denominator_basis == "adjudicated_blocks" else adjudicated_tasks

    if denominator == 0:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            numerator=0,
            denominator=0,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=[f"Zero items in denominator basis '{denominator_basis}'; false-block rate is not applicable."],
        )

    rate_val = round(verified_false_blocks / denominator, 4)
    return MetricResult(
        metric_id=metric_id,
        status=MetricStatus.MEASURED,
        value=rate_val,
        numerator=verified_false_blocks,
        denominator=denominator,
        population_definition=pop_def,
        eligibility_definition=elig_def,
        evaluation_set_id=evaluation_set_id,
        source_trace_ids=list(source_trace_ids or []),
        computed_at=ts,
        metadata={"denominator_basis": denominator_basis, "adjudicated_tasks": adjudicated_tasks},
    )


# ==============================================================================
# 5. Metric 4: Recurring Failure-Class Prevalence
# ==============================================================================

def compute_recurring_failure_class_prevalence(
    incident_or_event_records: Sequence[Dict[str, Any]],
    evaluation_set_id: Optional[str] = None,
    allow_prefiltered_classified_only: bool = False,
) -> MetricResult:

    """Computes recurring failure-class prevalence over an observed event cohort.
    
    Formula:
        Prevalence = Count of distinct failure classes with >= 2 observed occurrences
                     / Total distinct observed failure classes
                     
    Anti-fabrication & Completeness invariants:
    - This is a structural prevalence metric measuring repeat occurrences across an evaluation cohort.
      It is NOT a temporal recurrence rate over time.
    - Timestamps are NOT mandatory for prevalence; if timestamps are absent, prevalence can still be evaluated
      over the cohort. When timestamps are present, they are preserved as optional provenance.
    - Completeness Guard: Does not silently discard unclassified records. If the evaluated cohort contains
      ANY record missing required failure-class identity, returns INSUFFICIENT_DATA, unless the caller
      explicitly declares the supplied cohort as a pre-filtered CLASSIFIED_ONLY population
      (via allow_prefiltered_classified_only=True).
    - If event list is empty -> NOT_APPLICABLE.
    """
    ts = datetime.now(timezone.utc).isoformat()
    metric_id = "METRIC-RECURRING-FAILURE-CLASS-PREVALENCE"
    pop_def = "Observed incident/event cohort evaluated for recurring failure-class prevalence"
    elig_def = "Records possessing non-empty, normalized failure_class"

    if not incident_or_event_records:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            numerator=0,
            denominator=0,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["Event sequence is empty; recurring failure-class prevalence is not applicable."],
        )

    # Tally events by failure class and track unclassified records
    events_by_fc: Dict[str, int] = {}
    missing_fc_count = 0

    for idx, rec in enumerate(incident_or_event_records):
        fc = rec.get("failure_class")
        if not fc or not str(fc).strip():
            missing_fc_count += 1
            continue
        clean_fc = str(fc).strip().upper()
        events_by_fc[clean_fc] = events_by_fc.get(clean_fc, 0) + 1

    total_records = len(incident_or_event_records)

    # Completeness check: unclassified records must not be silently discarded
    if missing_fc_count > 0 and not allow_prefiltered_classified_only:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.INSUFFICIENT_DATA,
            value=None,
            numerator=None,
            denominator=None,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=[
                f"Evaluated cohort contains {missing_fc_count} of {total_records} records missing required failure-class identity. "
                "Recurring failure-class prevalence cannot be accurately derived without complete classification, "
                "unless caller explicitly declares cohort as pre-filtered classified-only."
            ],
            metadata={
                "total_records": total_records,
                "missing_fc_count": missing_fc_count,
                "classified_records_count": total_records - missing_fc_count,
                "cohort_scope": "INCOMPLETE_CLASSIFICATION",
                "metric_type": "STRUCTURAL_PREVALENCE",
            },
        )

    if not events_by_fc:
        # All records lacked failure class or empty
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.INSUFFICIENT_DATA if missing_fc_count > 0 else MetricStatus.NOT_APPLICABLE,
            value=None,
            numerator=0 if missing_fc_count == 0 else None,
            denominator=0 if missing_fc_count == 0 else None,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["Zero failure classes found in evaluation cohort."],
            metadata={
                "total_records": total_records,
                "missing_fc_count": missing_fc_count,
            },
        )

    distinct_classes = len(events_by_fc)
    recurrent_classes = sum(1 for fc, count in events_by_fc.items() if count >= 2)
    prevalence_val = round(recurrent_classes / distinct_classes, 4)

    has_timestamps = any(bool(rec.get("timestamp")) for rec in incident_or_event_records)
    scope_label = "PREFILTERED_CLASSIFIED_ONLY" if allow_prefiltered_classified_only and missing_fc_count > 0 else "FULL_COHORT_CLASSIFIED"

    return MetricResult(
        metric_id=metric_id,
        status=MetricStatus.MEASURED,
        value=prevalence_val,
        numerator=recurrent_classes,
        denominator=distinct_classes,
        population_definition=pop_def,
        eligibility_definition=elig_def,
        evaluation_set_id=evaluation_set_id,
        computed_at=ts,
        metadata={
            "distinct_failure_classes": distinct_classes,
            "recurrent_classes_count": recurrent_classes,
            "missing_fc_count": missing_fc_count,
            "metric_type": "STRUCTURAL_PREVALENCE",
            "cohort_scope": scope_label,
            "temporal_provenance": "TIMESTAMPS_PRESENT" if has_timestamps else "TIMESTAMPS_ABSENT",
            "temporal_scope": "COHORT_OBSERVATION_NON_TEMPORAL",
        },
    )


def compute_recurrence_rate(
    incident_or_event_records: Sequence[Dict[str, Any]],
    evaluation_set_id: Optional[str] = None,
    allow_prefiltered_classified_only: bool = False,
) -> MetricResult:
    """DEPRECATED COMPATIBILITY ALIAS — returns structural recurring failure-class prevalence; not a temporal recurrence rate.
    
    Routes directly to canonical compute_recurring_failure_class_prevalence().
    """
    return compute_recurring_failure_class_prevalence(
        incident_or_event_records=incident_or_event_records,
        evaluation_set_id=evaluation_set_id,
        allow_prefiltered_classified_only=allow_prefiltered_classified_only,
    )



# ==============================================================================
# 6. Metric 5: Lesson Staleness & Objective Age
# ==============================================================================

def compute_lesson_staleness(
    lessons: Sequence[Union[Lesson, Dict[str, Any]]],
    reference_time: Optional[datetime] = None,
    stale_threshold_days: Optional[float] = None,
    evaluation_set_id: Optional[str] = None,
) -> MetricResult:
    """Computes objective validation age and conditional staleness classification.
    
    Semantics & Invariants:
    - What "stale" means: A lesson whose most recent validation timestamp is older than
      stale_threshold_days relative to reference_time (or has no validation history when
      an operational staleness threshold is enforced).
    - What data is required: Lesson.validation_history entries with valid timestamps +
      an authoritative operational staleness threshold policy (stale_threshold_days).
    - What happens when threshold is absent: Objective validation ages (mean, median, min,
      max days, and unvalidated count) are calculated and reported in metadata, but binary
      stale/not-stale classification is NOT fabricated; status strictly returns INSUFFICIENT_DATA.
    - If lesson population is empty: returns NOT_APPLICABLE.
    - Age nature: Elapsed calendar time (fractional days) between the lesson's most recent
      validation event timestamp (UTC) and reference_time (UTC).
    """
    ts = datetime.now(timezone.utc).isoformat()
    ref_dt = reference_time or datetime.now(timezone.utc)
    metric_id = "METRIC-LESSON-STALENESS"
    pop_def = "Active governance lessons evaluated for chronological age and validation recency"
    elig_def = "Lessons with validation history entries vs. operational staleness threshold"

    if not lessons:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            numerator=0,
            denominator=0,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["Lesson sequence is empty; staleness evaluation is not applicable."],
        )

    ages_days: List[float] = []
    unvalidated_count = 0
    stale_count = 0
    future_timestamps_count = 0

    for l in lessons:
        v_hist = l.validation_history if isinstance(l, Lesson) else l.get("validation_history", [])
        if not v_hist:
            unvalidated_count += 1
            if stale_threshold_days is not None:
                stale_count += 1
            continue

        # Extract timestamps
        dts = []
        for v in v_hist:
            raw_v_ts = v.timestamp if hasattr(v, "timestamp") else v.get("timestamp")
            if raw_v_ts:
                try:
                    clean = str(raw_v_ts).replace("Z", "+00:00")
                    dts.append(datetime.fromisoformat(clean))
                except (ValueError, TypeError):
                    pass

        if not dts:
            unvalidated_count += 1
            if stale_threshold_days is not None:
                stale_count += 1
            continue

        most_recent = max(dts)
        # Ensure UTC timezone comparability
        if most_recent.tzinfo is None:
            most_recent = most_recent.replace(tzinfo=timezone.utc)
        if ref_dt.tzinfo is None:
            ref_dt = ref_dt.replace(tzinfo=timezone.utc)

        delta_sec = (ref_dt - most_recent).total_seconds()
        if delta_sec < 0:
            future_timestamps_count += 1
            # Temporally invalid observation! Do NOT clamp to 0.0 or add to ages_days
            continue

        age_days = delta_sec / 86400.0
        ages_days.append(age_days)

        if stale_threshold_days is not None and age_days > stale_threshold_days:
            stale_count += 1

    total_lessons = len(lessons)
    age_stats: Dict[str, Any] = {
        "total_lessons": total_lessons,
        "lessons_with_validation_count": len(ages_days) + future_timestamps_count,
        "valid_validation_count": len(ages_days),
        "unvalidated_lessons_count": unvalidated_count,
        "future_validation_timestamps_count": future_timestamps_count,
        "temporal_evidence_status": "TEMPORALLY_INVALID" if future_timestamps_count > 0 else "VALID",
        "mean_days_since_validation": round(statistics.mean(ages_days), 2) if ages_days else None,
        "median_days_since_validation": round(statistics.median(ages_days), 2) if ages_days else None,
        "min_days_since_validation": round(min(ages_days), 2) if ages_days else None,
        "max_days_since_validation": round(max(ages_days), 2) if ages_days else None,
        "stale_threshold_days_applied": stale_threshold_days,
        "age_metric_type": "CALENDAR_DAYS_SINCE_LAST_VALIDATION",
    }

    if future_timestamps_count > 0:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.INSUFFICIENT_DATA,
            value=None,
            numerator=None,
            denominator=total_lessons,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=[
                f"Cohort contains {future_timestamps_count} lesson(s) with validation timestamp(s) in the future relative to reference_time. "
                "Due to temporally invalid evidence, staleness classification cannot be reliably derived and returns INSUFFICIENT_DATA."
            ],
            metadata=age_stats,
        )

    if stale_threshold_days is None:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.INSUFFICIENT_DATA,
            value=None,
            numerator=None,
            denominator=total_lessons,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=[
                "No authoritative staleness threshold policy provided in governance. "
                "Objective validation ages reported in metadata without fabricating a binary classification; "
                "staleness classification remains INSUFFICIENT_DATA."
            ],
            metadata=age_stats,
        )

    staleness_rate = round(stale_count / total_lessons, 4)
    return MetricResult(
        metric_id=metric_id,
        status=MetricStatus.MEASURED,
        value=staleness_rate,
        numerator=stale_count,
        denominator=total_lessons,
        population_definition=pop_def,
        eligibility_definition=elig_def,
        evaluation_set_id=evaluation_set_id,
        computed_at=ts,
        metadata=age_stats,
    )


# ==============================================================================
# 7. Metric 6: Citation Frequency & Coverage
# ==============================================================================

def compute_catalog_rule_citation_frequency(
    target_entity_id: str,
    rules_catalog: Sequence[Union[Rule, Dict[str, Any]]],
    evaluation_set_id: Optional[str] = None,
) -> MetricResult:
    """Computes citation frequency of a target entity across the active governance rules catalog.
    
    Population:
        All active Rule records within data/metadata/governance_v2/rules.json (or passed catalog).
    Numerator:
        Count of active rules whose principle_id or evidence_refs cite target_entity_id.
    Denominator:
        Total count of active rules in the evaluated catalog.
    Evaluation Scope:
        Catalog-level structural citation coverage.
    """
    ts = datetime.now(timezone.utc).isoformat()
    metric_id = "METRIC-CATALOG-RULE-CITATION-FREQUENCY"
    pop_def = f"Catalog of active governance rules evaluated for citations of '{target_entity_id}'"
    elig_def = "Active rules in governance catalog"

    if not rules_catalog:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            numerator=0,
            denominator=0,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["Rules catalog is empty; catalog rule citation frequency is not applicable."],
        )

    citation_count = 0
    total_rules = len(rules_catalog)

    for item in rules_catalog:
        if isinstance(item, Rule):
            if item.principle_id == target_entity_id or target_entity_id in item.evidence_refs:
                citation_count += 1
        elif isinstance(item, dict):
            if item.get("principle_id") == target_entity_id or target_entity_id in item.get("evidence_refs", []):
                citation_count += 1

    freq_val = round(citation_count / total_rules, 4)
    return MetricResult(
        metric_id=metric_id,
        status=MetricStatus.MEASURED,
        value=freq_val,
        numerator=citation_count,
        denominator=total_rules,
        population_definition=pop_def,
        eligibility_definition=elig_def,
        evaluation_set_id=evaluation_set_id,
        computed_at=ts,
        metadata={
            "target_entity_id": target_entity_id,
            "population_type": "active_rules",
            "evaluation_scope": "CATALOG_RULES",
            "total_rules": total_rules,
            "citing_rules_count": citation_count,
        },
    )


def compute_trace_citation_frequency(
    target_entity_id: str,
    traces: Sequence[Union[PreflightV2Result, Dict[str, Any]]],
    evaluation_set_id: Optional[str] = None,
) -> MetricResult:
    """Computes citation/reference frequency of a target entity across execution traces.
    
    Population:
        All execution trace / PreflightV2Result records within the evaluated batch.
    Numerator:
        Count of traces that reference target_entity_id in relevant_lessons or control_trace.entity_refs.
    Denominator:
        Total count of execution traces in the evaluated cohort.
    Evaluation Scope:
        Execution trace cohort reference coverage.
    """
    ts = datetime.now(timezone.utc).isoformat()
    metric_id = "METRIC-TRACE-CITATION-FREQUENCY"
    pop_def = f"Execution traces evaluated for citations/references to '{target_entity_id}'"
    elig_def = "PreflightV2Result or execution trace records in evaluation batch"

    if not traces:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            numerator=0,
            denominator=0,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["Trace sequence is empty; trace citation frequency is not applicable."],
        )

    citation_count = 0
    total_traces = len(traces)

    for item in traces:
        if isinstance(item, PreflightV2Result):
            matched = any(
                r.item_id == target_entity_id for r in item.relevant_lessons
            ) or any(
                rec.entity_refs and target_entity_id in rec.entity_refs for rec in item.control_trace
            )
            if matched:
                citation_count += 1
        elif isinstance(item, dict):
            rel_lessons = [r.get("item_id") for r in item.get("relevant_lessons", [])]
            trace_refs = [
                ref for t in item.get("control_trace", []) for ref in t.get("entity_refs", [])
            ]
            if target_entity_id in rel_lessons or target_entity_id in trace_refs:
                citation_count += 1

    freq_val = round(citation_count / total_traces, 4)
    return MetricResult(
        metric_id=metric_id,
        status=MetricStatus.MEASURED,
        value=freq_val,
        numerator=citation_count,
        denominator=total_traces,
        population_definition=pop_def,
        eligibility_definition=elig_def,
        evaluation_set_id=evaluation_set_id,
        computed_at=ts,
        metadata={
            "target_entity_id": target_entity_id,
            "population_type": "control_traces",
            "evaluation_scope": "EXECUTION_TRACES",
            "total_traces": total_traces,
            "citing_traces_count": citation_count,
        },
    )


def compute_citation_frequency(
    target_entity_id: str,
    citing_population: Sequence[Union[Rule, PreflightV2Result, Dict[str, Any]]],
    population_type: str = "active_rules",
    evaluation_set_id: Optional[str] = None,
) -> MetricResult:
    """Dispatches citation frequency evaluation to specific, unambiguous population implementations.
    
    Supported population_type:
    - "active_rules" / "catalog_rules": Dispatches to compute_catalog_rule_citation_frequency
    - "control_traces" / "execution_traces": Dispatches to compute_trace_citation_frequency
    """
    if population_type in ("active_rules", "catalog_rules"):
        return compute_catalog_rule_citation_frequency(
            target_entity_id=target_entity_id,
            rules_catalog=citing_population,  # type: ignore
            evaluation_set_id=evaluation_set_id,
        )
    elif population_type in ("control_traces", "execution_traces"):
        return compute_trace_citation_frequency(
            target_entity_id=target_entity_id,
            traces=citing_population,  # type: ignore
            evaluation_set_id=evaluation_set_id,
        )
    else:
        ts = datetime.now(timezone.utc).isoformat()
        return MetricResult(
            metric_id="METRIC-CITATION-FREQUENCY",
            status=MetricStatus.INSUFFICIENT_DATA,
            value=None,
            population_definition=f"Unrecognized population '{population_type}'",
            eligibility_definition="Undefined",
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=[f"Unknown population_type '{population_type}'. Must be 'active_rules' or 'control_traces'."],
        )


# ==============================================================================
# 8. Metric 7: UI Presentation Telemetry Rate
# ==============================================================================

def compute_ui_presentation_rate(
    recommended_lesson_ids: Sequence[str],
    client_events: Optional[Sequence[Union[ClientPresentationEvent, Dict[str, Any]]]] = None,
    evaluation_set_id: Optional[str] = None,
) -> MetricResult:
    """Computes presentation telemetry rate over explicitly recorded client presentation events.
    
    Anti-fabrication invariant:
    - Backend retrieval != UI presentation.
    - If no client presentation event stream exists, returns status=UNKNOWN (value=None).
      UI events are NEVER simulated from backend retrieval.
    """
    ts = datetime.now(timezone.utc).isoformat()
    metric_id = "METRIC-UI-PRESENTATION-RATE"
    pop_def = "Recommended retrieved lessons evaluated against client UI presentation events"
    elig_def = "Retrieved lessons recommended for operator presentation"

    if client_events is None or len(client_events) == 0:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.UNKNOWN,
            value=None,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=[
                "No client-side UI presentation events recorded. Headless backend execution "
                "cannot observe UI presentation; presentation rate remains strictly UNKNOWN."
            ],
        )

    if not recommended_lesson_ids:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            numerator=0,
            denominator=0,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["No lessons were recommended for presentation; denominator is zero."],
        )

    # Extract presented lesson IDs from client event stream
    presented_ids: Set[str] = set()
    for ev in client_events:
        l_id = ev.lesson_id if isinstance(ev, ClientPresentationEvent) else ev.get("lesson_id")
        if l_id:
            presented_ids.add(str(l_id))

    recommended_set = set(recommended_lesson_ids)
    presented_count = len(recommended_set.intersection(presented_ids))
    total_recommended = len(recommended_set)

    pres_val = presented_count / total_recommended
    return MetricResult(
        metric_id=metric_id,
        status=MetricStatus.MEASURED,
        value=pres_val,
        numerator=presented_count,
        denominator=total_recommended,
        population_definition=pop_def,
        eligibility_definition=elig_def,
        evaluation_set_id=evaluation_set_id,
        computed_at=ts,
        metadata={"presented_lesson_ids": sorted(presented_ids)},
    )


# ==============================================================================
# 9. Metric 8: Negative Feedback Receipt Validation Pass Rate
# ==============================================================================

def compute_receipt_validation_pass_rate(
    ingestion_result: Dict[str, Any],
    evaluation_set_id: Optional[str] = None,
) -> MetricResult:
    """Computes the validation pass rate for ingested negative-feedback receipts.
    
    Formula:
        Pass Rate = N(valid receipts) / N(total receipts examined)
        
    Scope:
        Receipt validation batch or directory.
        
    Anti-overclaiming invariants:
    - Measures the structural acceptance rate (syntax, schema, category,
      digest match, and uncorrupted persistence) across examined receipts.
    - Does NOT imply that the numeric ratio itself measures cryptographic integrity.
    """
    ts = datetime.now(timezone.utc).isoformat()
    metric_id = "METRIC-RECEIPT-VALIDATION-PASS-RATE"
    pop_def = "All negative-feedback receipt candidates encountered and subjected to validation/ingestion handling"
    elig_def = "Receipt candidates with valid JSON syntax, canonical schema, valid category, and verified SHA-256 digest"

    total = ingestion_result.get("total_candidates_encountered", ingestion_result.get("total_examined", 0))
    valid_count = len(ingestion_result.get("validated_records", []))
    quarantined_records = ingestion_result.get("quarantined_records", [])
    quarantine_count = len(quarantined_records)
    duplicate_count = ingestion_result.get("duplicate_count", 0)
    conflict_count = ingestion_result.get("conflict_count", 0)

    # Granular validation failure breakdown
    read_error_count = sum(1 for q in quarantined_records if "READ_ERROR" in str(q.get("quarantine_reason", "")))
    schema_invalid_count = sum(1 for q in quarantined_records if "INVALID_SCHEMA" in str(q.get("quarantine_reason", "")))
    category_invalid_count = sum(1 for q in quarantined_records if "UNKNOWN_CATEGORY" in str(q.get("quarantine_reason", "")))
    digest_mismatch_count = sum(1 for q in quarantined_records if "CORRUPTED_DIGEST_MISMATCH" in str(q.get("quarantine_reason", "")))
    malformed_json_count = sum(1 for q in quarantined_records if "MALFORMED_JSON" in str(q.get("quarantine_reason", "")))

    if total == 0:
        return MetricResult(
            metric_id=metric_id,
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            numerator=0,
            denominator=0,
            population_definition=pop_def,
            eligibility_definition=elig_def,
            evaluation_set_id=evaluation_set_id,
            computed_at=ts,
            warnings=["No receipt candidate records encountered; receipt validation pass rate not applicable."],
            metadata={
                "metric_type": "VALIDATION_ACCEPTANCE_RATE",
                "total_candidates_encountered": 0,
                "total_examined": 0,
                "valid_count": 0,
            },
        )

    pass_rate = round(valid_count / total, 4)
    return MetricResult(
        metric_id=metric_id,
        status=MetricStatus.MEASURED,
        value=pass_rate,
        numerator=valid_count,
        denominator=total,
        population_definition=pop_def,
        eligibility_definition=elig_def,
        evaluation_set_id=evaluation_set_id,
        computed_at=ts,
        metadata={
            "metric_type": "VALIDATION_ACCEPTANCE_RATE",
            "total_candidates_encountered": total,
            "total_examined": total,
            "valid_count": valid_count,
            "quarantined_count": quarantine_count,
            "duplicate_count": duplicate_count,
            "conflict_count": conflict_count,
            "read_error_count": read_error_count,
            "schema_invalid_count": schema_invalid_count,
            "category_invalid_count": category_invalid_count,
            "digest_mismatch_count": digest_mismatch_count,
            "malformed_json_count": malformed_json_count,
        },
    )


def compute_receipt_ingestion_summary(
    ingestion_result: Dict[str, Any],
    evaluation_set_id: Optional[str] = None,
) -> MetricResult:
    """DEPRECATED COMPATIBILITY ALIAS — returns receipt validation pass rate; not a cryptographic integrity metric.
    
    Routes to canonical compute_receipt_validation_pass_rate().
    """
    canonical_res = compute_receipt_validation_pass_rate(
        ingestion_result=ingestion_result,
        evaluation_set_id=evaluation_set_id,
    )
    # Retain deprecated metric_id for backwards compatibility
    canonical_res.metric_id = "METRIC-RECEIPT-INGESTION-INTEGRITY"
    canonical_res.metadata["deprecated_alias"] = "compute_receipt_ingestion_summary"
    canonical_res.metadata["canonical_metric_id"] = "METRIC-RECEIPT-VALIDATION-PASS-RATE"
    return canonical_res



# ==============================================================================
# 10. Offline Evaluation Batch Engine
# ==============================================================================

def evaluate_offline_batch(
    batch_id: str,
    eval_tasks: Sequence[Union[AdjudicatedTaskRecord, Dict[str, Any]]],
    receipt_sources: Optional[Union[Path, str, Sequence[Union[Path, str, Dict[str, Any]]]]] = None,
    client_events: Optional[Sequence[Union[ClientPresentationEvent, Dict[str, Any]]]] = None,
    lessons_catalog: Optional[Sequence[Union[Lesson, Dict[str, Any]]]] = None,
    rules_catalog: Optional[Sequence[Union[Rule, Dict[str, Any]]]] = None,
    is_synthetic_fixture: bool = False,
    stale_threshold_days: Optional[float] = None,
) -> MetricEvaluationBatch:
    """Executes a deterministic offline evaluation batch across traces, receipts, and catalogs.
    
    Guarantees:
    - Purely observational: cannot modify canonical governance catalogs.
    - Zero fabrication: missing oracles strictly produce UNKNOWN or INSUFFICIENT_DATA.
    - Synthetic fixtures are explicitly labeled: 'SYNTHETIC_TEST_FIXTURE_ONLY'.
    - Produces deterministic dataset_hash adhering strictly to CONTRACT B:
      'dataset_hash is a deterministic canonicalized semantic input identity.'
      It binds canonical semantic task contexts, ground-truth annotations, preflight status,
      and stable receipt payloads, while strictly excluding volatile write timestamps (recorded_at)
      and execution run metadata (batch_id, computed_at, temporary directories).
    """
    ts = datetime.now(timezone.utc).isoformat()
    synth_label = "SYNTHETIC_TEST_FIXTURE_ONLY" if is_synthetic_fixture else ""

    # Ingest receipts
    ingestion_res = {"validated_records": [], "quarantined_records": [], "total_examined": 0}
    if receipt_sources is not None:
        ingestion_res = ingest_negative_feedback_receipts(receipt_sources, fail_closed_on_conflict=True)

    validated_receipts = ingestion_res.get("validated_records", [])
    quarantined = ingestion_res.get("quarantined_records", [])

    # Compute metrics
    metrics: Dict[str, MetricResult] = {}

    # Metric 1: Recall
    metrics["retrieval_recall"] = compute_retrieval_recall(eval_tasks, evaluation_set_id=batch_id)

    # Metric 2: Precision
    metrics["retrieval_precision"] = compute_retrieval_precision(eval_tasks, evaluation_set_id=batch_id)

    # Metric 3: False-Block Rate
    metrics["false_block_rate"] = compute_false_block_rate(eval_tasks, evaluation_set_id=batch_id)

    # Metric 4: Recurring Failure-Class Prevalence (and backward-compatible recurrence_rate)
    # Build incident events from tasks and receipts
    event_records: List[Dict[str, Any]] = []
    for t in eval_tasks:
        if isinstance(t, dict) and t.get("failure_class"):
            event_records.append(t)
    for r in validated_receipts:
        cat = r.get("category", "")
        # Observational feedback mapped to rework class
        event_records.append({
            "failure_class": f"FEEDBACK_{cat}",
            "timestamp": r.get("recorded_at"),
            "incident_id": r.get("receipt_id"),
        })
    prevalence_res = compute_recurring_failure_class_prevalence(event_records, evaluation_set_id=batch_id)
    metrics["recurring_failure_class_prevalence"] = prevalence_res
    metrics["recurrence_rate"] = prevalence_res

    # Metric 5: Lesson Staleness
    if lessons_catalog:
        metrics["lesson_staleness"] = compute_lesson_staleness(
            lessons_catalog,
            stale_threshold_days=stale_threshold_days,
            evaluation_set_id=batch_id,
        )

    # Metric 6: Citation Frequency (Rule Catalog)
    if rules_catalog:
        metrics["citation_frequency_rules"] = compute_catalog_rule_citation_frequency(
            target_entity_id="PRIN-001",
            rules_catalog=rules_catalog,
            evaluation_set_id=batch_id,
        )

    # Metric 7: UI Presentation Telemetry
    recommended_ids = []
    for t in eval_tasks:
        if isinstance(t, AdjudicatedTaskRecord):
            raw_ret = (t.task_context or {}).get("retrieved_lesson_ids")
            recommended_ids.extend(raw_ret or [])
        elif isinstance(t, dict):
            raw_ret = t.get("retrieved_lesson_ids")
            recommended_ids.extend(raw_ret or [])
    metrics["ui_presentation_rate"] = compute_ui_presentation_rate(
        recommended_ids,
        client_events=client_events,
        evaluation_set_id=batch_id,
    )

    # Metric 8: Receipt Validation Pass Rate (with backward-compatible alias key)
    if receipt_sources is not None:
        metrics["receipt_validation_pass_rate"] = compute_receipt_validation_pass_rate(
            ingestion_res,
            evaluation_set_id=batch_id,
        )
        metrics["receipt_ingestion_summary"] = compute_receipt_ingestion_summary(
            ingestion_res,
            evaluation_set_id=batch_id,
        )


    # Manifest for deterministic hashing adhering to CONTRACT B (Semantic Input Dataset Identity)
    task_keys: List[str] = []
    semantic_tasks: List[Dict[str, Any]] = []
    for idx, t in enumerate(eval_tasks):
        if isinstance(t, AdjudicatedTaskRecord):
            tid = str(t.task_id or f"task_{idx}")
            ttype = str(t.task_type or "")
            tctx = dict(t.task_context or {})
            gt = list(t.ground_truth_relevant_lesson_ids) if t.ground_truth_relevant_lesson_ids is not None else None
            if gt is not None:
                gt = sorted([str(x) for x in gt])
            passed = t.preflight_passed
            accurate = t.is_block_accurate
            fc = getattr(t, "failure_class", None) or tctx.get("failure_class")
        elif isinstance(t, dict):
            tid = str(t.get("task_id", f"task_{idx}"))
            ttype = str(t.get("task_type", ""))
            tctx = dict(t.get("task_context") or {})
            raw_gt = t.get("ground_truth_relevant_lesson_ids")
            gt = sorted([str(x) for x in raw_gt]) if raw_gt is not None else None
            passed = t.get("preflight_passed")
            accurate = t.get("is_block_accurate")
            fc = t.get("failure_class") or tctx.get("failure_class")
        else:
            tid = f"task_{idx}"
            ttype = ""
            tctx = {}
            gt = None
            passed = None
            accurate = None
            fc = None

        task_keys.append(tid)
        task_rec: Dict[str, Any] = {
            "task_id": tid,
            "task_type": ttype,
            "task_context": tctx,
            "ground_truth_relevant_lesson_ids": gt,
            "preflight_passed": passed,
            "is_block_accurate": accurate,
        }
        if fc is not None:
            task_rec["failure_class"] = str(fc)
        semantic_tasks.append(task_rec)

    # Sort deterministically
    semantic_tasks.sort(key=lambda x: (x["task_id"], canonicalize_json_v1(x).decode("utf-8")))

    receipt_keys: List[str] = []
    semantic_receipts: List[Dict[str, Any]] = []
    for idx, r in enumerate(validated_receipts):
        rid = str(r.get("receipt_id", f"rcpt_{idx}"))
        cat = str(r.get("category", ""))
        reason = str(r.get("reason", "")).strip()
        ent = sorted([str(e) for e in (r.get("entity_refs") or [])])
        evid = sorted([str(e) for e in (r.get("evidence_refs") or [])])
        tctx = dict(r.get("task_context") or {})
        control_trace_id = str(r.get("control_trace_id", ""))
        source = str(r.get("source", ""))
        receipt_keys.append(rid)
        semantic_receipts.append({
            "receipt_id": rid,
            "category": cat,
            "reason": reason,
            "entity_refs": ent,
            "evidence_refs": evid,
            "task_context": tctx,
            "control_trace_id": control_trace_id,
            "source": source,
        })

    receipt_keys.sort()
    semantic_receipts.sort(key=lambda x: (x["receipt_id"], canonicalize_json_v1(x).decode("utf-8")))

    metric_summaries = []
    for k in sorted(metrics.keys()):
        m = metrics[k]
        metric_summaries.append({
            "key": k,
            "metric_id": m.metric_id,
            "status": m.status.value if hasattr(m.status, "value") else str(m.status),
            "value": m.value,
            "numerator": m.numerator,
            "denominator": m.denominator,
        })

    # Manifest for deterministic input dataset hashing (CONTRACT B: canonical semantic input dataset identity)
    input_dataset_manifest = {
        "is_synthetic_fixture": is_synthetic_fixture,
        "eval_tasks_count": len(eval_tasks),
        "task_keys": sorted(task_keys),
        "semantic_tasks": semantic_tasks,
        "validated_receipts_count": len(validated_receipts),
        "quarantined_receipts_count": len(quarantined),
        "receipt_keys": receipt_keys,
        "semantic_receipts": semantic_receipts,
    }
    dataset_manifest_bytes = canonicalize_json_v1(input_dataset_manifest)
    dataset_hash = hashlib.sha256(dataset_manifest_bytes).hexdigest()

    # Manifest for complete batch evaluation result identity
    evaluation_manifest = {
        "dataset_hash": dataset_hash,
        "batch_id": batch_id,
        "is_synthetic_fixture": is_synthetic_fixture,
        "eval_tasks_count": len(eval_tasks),
        "validated_receipts_count": len(validated_receipts),
        "quarantined_receipts_count": len(quarantined),
        "metrics_keys": sorted(metrics.keys()),
        "task_keys": sorted(task_keys),
        "receipt_keys": receipt_keys,
        "metric_summaries": metric_summaries,
    }
    evaluation_manifest_bytes = canonicalize_json_v1(evaluation_manifest)
    evaluation_manifest_hash = hashlib.sha256(evaluation_manifest_bytes).hexdigest()
    batch_result_hash = evaluation_manifest_hash

    return MetricEvaluationBatch(
        batch_id=batch_id,
        dataset_hash=dataset_hash,
        evaluation_manifest_hash=evaluation_manifest_hash,
        batch_result_hash=batch_result_hash,
        source_manifest=input_dataset_manifest,
        validated_records=validated_receipts,
        quarantined_records=quarantined,
        metrics=metrics,
        computed_at=ts,
        provenance={
            "engine": "ocean_sentinel.governance.metrics",
            "version": METRIC_SCHEMA_VERSION,
            "architecture_authority": "ChatGPT_CAO",
            "approval_authority": "Human",
            "evaluation_manifest_hash": evaluation_manifest_hash,
        },
        is_synthetic_fixture=is_synthetic_fixture,
        synthetic_fixture_label=synth_label,
    )
