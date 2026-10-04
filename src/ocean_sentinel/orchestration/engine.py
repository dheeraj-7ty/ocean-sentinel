"""Investigation Execution Engine (Phase 7A/7B).

Coordinates deterministic, graph-driven execution of investigation runs
across scientific DAG stages with:
- Config & protocol fingerprinting for stage-level idempotency
- Duplicate artifact creation prevention
- Granular stage attempt audit tracking
- Strict fail-closed scientific execution firewall
- Controlled pause and interruption recovery hooks
- Phase 7B durable event emission, replay, and in-process event streaming
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import secrets
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from ocean_sentinel.orchestration.dag import (
    DAGValidationError,
    ScientificDAG,
    create_canonical_scientific_dag,
)
from ocean_sentinel.orchestration.event_bus import EventBus, get_global_event_bus
from ocean_sentinel.orchestration.events import (
    EventSeverity,
    InvestigationEvent,
    InvestigationEventType,
)
from ocean_sentinel.orchestration.investigation_context import InvestigationContext
from ocean_sentinel.orchestration.investigation_run import (
    ArtifactRef,
    ContentStatus,
    InvestigationRun,
    InvestigationRunStatus,
    InvestigationStageState,
    StageAttempt,
    StageExecutionStatus,
)
from ocean_sentinel.orchestration.investigation_store import InvestigationRunStore

logger = logging.getLogger(__name__)


class InvestigationEngineError(Exception):
    """Base error raised during investigation execution."""


class ScientificGateViolationError(InvestigationEngineError):
    """Raised when scientific stage execution is attempted without authorization."""


class InvestigationEngine:
    """Deterministic orchestrator executing investigation runs against a ScientificDAG."""

    def __init__(
        self,
        store: Optional[InvestigationRunStore] = None,
        dag: Optional[ScientificDAG] = None,
        repo_root: Optional[Path] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.store = store or InvestigationRunStore(repo_root=repo_root)
        self.dag = dag or create_canonical_scientific_dag()
        self.repo_root = self.store.repo_root
        self.event_bus = event_bus or get_global_event_bus()

    def emit_event(
        self,
        run: InvestigationRun,
        event_type: Union[InvestigationEventType, str],
        payload: Optional[Dict[str, Any]] = None,
        stage_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
        severity: Union[EventSeverity, str] = EventSeverity.INFO,
        correlation_id: Optional[str] = None,
    ) -> InvestigationEvent:
        """Record event to append-only durable log, then broadcast to subscribers.

        Write order:
        1. Canonical run state is persisted prior to calling this method.
        2. Event is durably appended to local events.jsonl.
        3. Subscribers on the in-process EventBus are notified.
        """
        event_log = self.store.get_event_log(run.run_id)
        clean_payload = payload or {}
        try:
            evt = event_log.emit(
                event_type=event_type,
                payload=clean_payload,
                stage_id=stage_id,
                attempt_id=attempt_id,
                producer="InvestigationEngine",
                severity=severity,
                correlation_id=correlation_id,
            )
        except Exception as err:
            logger.critical(
                "EventLog append failed for run '%s' (event %s): %s. Suppressing broadcast to prevent phantom events.",
                run.run_id,
                event_type,
                err,
            )
            raise InvestigationEngineError(
                f"Durable event persistence failed for run '{run.run_id}': {err}"
            ) from err

        self.event_bus.publish(evt)
        return evt

    def get_run_telemetry(self, run: InvestigationRun) -> Dict[str, Any]:
        """Generate structured operational telemetry for an investigation run."""
        event_log = self.store.get_event_log(run.run_id)
        current_stage = run.current_stage
        if not current_stage:
            for st_id, st in run.stages.items():
                if st.status == StageExecutionStatus.RUNNING.value:
                    current_stage = st_id
                    break

        start_dt = None
        finish_dt = None
        if run.started_at:
            try:
                start_dt = datetime.fromisoformat(run.started_at)
            except Exception:
                pass
        if run.finished_at:
            try:
                finish_dt = datetime.fromisoformat(run.finished_at)
            except Exception:
                pass

        elapsed_sec = None
        if start_dt:
            end_time = finish_dt or datetime.now(timezone.utc)
            elapsed_sec = max(0.0, round((end_time - start_dt).total_seconds(), 3))

        return {
            "run_id": run.run_id,
            "overall_status": run.overall_status,
            "current_stage": current_stage,
            "total_stages": len(self.dag.nodes),
            "completed_stages": sum(
                1 for st in run.stages.values() if st.status == StageExecutionStatus.COMPLETED.value
            ),
            "blocked_stages": sum(
                1 for st in run.stages.values() if st.status == StageExecutionStatus.BLOCKED.value
            ),
            "failed_stages": sum(
                1 for st in run.stages.values() if st.status == StageExecutionStatus.FAILED.value
            ),
            "total_attempts": len(run.attempts),
            "artifacts_count": len(run.artifacts),
            "event_count": event_log.current_sequence,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "elapsed_seconds": elapsed_sec,
            "scientific_execution_authorized": False,
        }

    def emit_telemetry_snapshot(self, run: InvestigationRun) -> InvestigationEvent:
        """Capture and emit an operational telemetry event."""
        telemetry = self.get_run_telemetry(run)
        return self.emit_event(
            run=run,
            event_type=InvestigationEventType.TELEMETRY_SNAPSHOT,
            payload=telemetry,
        )

    def compute_stage_fingerprint(
        self,
        stage_id: str,
        context: InvestigationContext,
        input_hashes: Dict[str, str],
        stage_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Calculate a deterministic SHA-256 fingerprint for stage inputs & protocol."""
        h = hashlib.sha256()
        h.update(stage_id.encode("utf-8"))
        h.update(str(context.protocol_sha256 or "").encode("utf-8"))
        h.update(str(context.model_sha256 or "").encode("utf-8"))

        norm_inputs = json.dumps(input_hashes, sort_keys=True)
        h.update(norm_inputs.encode("utf-8"))

        if stage_config:
            norm_config = json.dumps(stage_config, sort_keys=True)
            h.update(norm_config.encode("utf-8"))

        return h.hexdigest()

    def execute_stage(
        self,
        run: InvestigationRun,
        context: InvestigationContext,
        stage_id: str,
        handler: Callable[[InvestigationContext, InvestigationRun], List[ArtifactRef]],
        stage_config: Optional[Dict[str, Any]] = None,
    ) -> StageAttempt:
        """Execute an individual DAG stage with idempotency check and attempt tracking."""
        completed_stages = {
            k for k, v in run.stages.items() if v.status == StageExecutionStatus.COMPLETED.value
        }

        # 1. Check execution eligibility against DAG
        can_run, reason = self.dag.can_execute_stage(
            stage_id, completed_stages, context.authorization_state
        )
        if not can_run:
            node = self.dag.nodes.get(stage_id)
            if node and node.is_scientific_gated:
                logger.info(
                    "Scientific stage '%s' halted fail-closed by policy: %s", stage_id, reason
                )
                run.set_stage_status(
                    stage_id,
                    StageExecutionStatus.BLOCKED,
                    message="Scientific execution is gated by repository policy.",
                    details={"gate_reason": reason},
                )
                attempt_id = f"att_{stage_id}_{int(time.time())}_{secrets.token_hex(3)}"
                attempt = StageAttempt(
                    attempt_id=attempt_id,
                    stage_id=stage_id,
                    status=StageExecutionStatus.BLOCKED.value,
                    error={"code": "SCIENTIFIC_EXECUTION_GATED", "message": reason},
                )
                run.record_attempt(attempt)
                self.store.save_run(run)

                # Emit STAGE_BLOCKED event (never STAGE_STARTED)
                self.emit_event(
                    run=run,
                    event_type=InvestigationEventType.STAGE_BLOCKED,
                    payload={"stage_id": stage_id, "gate_reason": reason},
                    stage_id=stage_id,
                    attempt_id=attempt_id,
                    severity=EventSeverity.WARNING,
                )
                raise ScientificGateViolationError(reason)
            else:
                run.set_stage_status(
                    stage_id,
                    StageExecutionStatus.FAILED,
                    message=f"Cannot execute stage '{stage_id}': {reason}",
                )
                self.store.save_run(run)
                self.emit_event(
                    run=run,
                    event_type=InvestigationEventType.STAGE_FAILED,
                    payload={"stage_id": stage_id, "reason": reason},
                    stage_id=stage_id,
                    severity=EventSeverity.ERROR,
                )
                raise InvestigationEngineError(f"Cannot execute stage '{stage_id}': {reason}")

        # 2. Gather input hashes from dependent stages
        node = self.dag.nodes[stage_id]
        input_hashes: Dict[str, str] = {}
        input_refs: List[str] = []
        for dep in node.dependencies:
            for art in run.artifacts:
                if art.producer_stage == dep:
                    input_hashes[art.artifact_id] = art.sha256
                    input_refs.append(art.artifact_id)

        # 3. Compute config & protocol fingerprint
        fingerprint = self.compute_stage_fingerprint(
            stage_id=stage_id,
            context=context,
            input_hashes=input_hashes,
            stage_config=stage_config,
        )

        # 4. Idempotency Check: if stage already completed with matching fingerprint and valid outputs
        st = run.stages.get(stage_id)
        if st and st.status == StageExecutionStatus.COMPLETED.value and st.latest_fingerprint == fingerprint:
            stage_artifacts = [a for a in run.artifacts if a.producer_stage == stage_id]
            all_valid = len(stage_artifacts) > 0 and all(
                a.verify_integrity(self.repo_root) for a in stage_artifacts
            )
            if all_valid:
                logger.info(
                    "Stage '%s' already completed with identical fingerprint '%s'; reusing verified artifacts.",
                    stage_id,
                    fingerprint[:8],
                )
                existing_attempt = next(
                    (a for a in reversed(st.attempts) if a.status == StageExecutionStatus.COMPLETED.value),
                    None,
                )
                if not existing_attempt:
                    existing_attempt = next(
                        (
                            a
                            for a in reversed(run.attempts)
                            if a.stage_id == stage_id and a.status == StageExecutionStatus.COMPLETED.value
                        ),
                        None,
                    )
                self.emit_event(
                    run=run,
                    event_type=InvestigationEventType.STAGE_SKIPPED,
                    payload={"stage_id": stage_id, "reason": "idempotent_reuse", "fingerprint": fingerprint[:8]},
                    stage_id=stage_id,
                    attempt_id=existing_attempt.attempt_id if existing_attempt else None,
                )
                if existing_attempt:
                    return existing_attempt

        # 5. Initialize new execution attempt
        run.set_stage_status(stage_id, StageExecutionStatus.RUNNING)
        st = run.stages[stage_id]
        attempt_num = len(st.attempts) + 1
        attempt_id = f"att_{stage_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(3)}"
        attempt = StageAttempt(
            attempt_id=attempt_id,
            stage_id=stage_id,
            attempt_number=attempt_num,
            started_at=datetime.now(timezone.utc).isoformat(),
            status=StageExecutionStatus.RUNNING.value,
            input_hashes=input_hashes,
            config_fingerprint=fingerprint,
        )
        run.record_attempt(attempt)
        st.input_refs = input_refs
        st.latest_fingerprint = fingerprint
        self.store.save_run(run)

        # Emit STAGE_STARTED event
        self.emit_event(
            run=run,
            event_type=InvestigationEventType.STAGE_STARTED,
            payload={"stage_id": stage_id, "attempt_number": attempt_num, "fingerprint": fingerprint[:8]},
            stage_id=stage_id,
            attempt_id=attempt_id,
        )

        # 6. Execute stage handler
        try:
            output_artifacts = handler(context, run)
            output_hashes: Dict[str, str] = {}
            output_refs: List[str] = []

            for art in output_artifacts:
                art.producer_stage = stage_id
                art.verify_integrity(self.repo_root)
                run.add_artifact(art)
                context.register_artifact(art)
                output_hashes[art.artifact_id] = art.sha256
                output_refs.append(art.artifact_id)

                # Emit ARTIFACT_REGISTERED event
                self.emit_event(
                    run=run,
                    event_type=InvestigationEventType.ARTIFACT_REGISTERED,
                    payload={
                        "artifact_id": art.artifact_id,
                        "artifact_type": getattr(art, "type", "UNKNOWN"),
                        "sha256": art.sha256,
                        "path": getattr(art, "path", ""),
                    },
                    stage_id=stage_id,
                    attempt_id=attempt_id,
                )

            attempt.mark_completed(output_hashes)
            run.set_stage_status(stage_id, StageExecutionStatus.COMPLETED)
            st = run.stages[stage_id]
            st.output_refs = output_refs
            st.latest_fingerprint = fingerprint

            self.store.save_run(run)

            # Emit STAGE_COMPLETED event
            self.emit_event(
                run=run,
                event_type=InvestigationEventType.STAGE_COMPLETED,
                payload={"stage_id": stage_id, "attempt_id": attempt_id, "output_count": len(output_artifacts)},
                stage_id=stage_id,
                attempt_id=attempt_id,
            )
            return attempt

        except Exception as e:
            logger.error("Stage '%s' execution failed: %s", stage_id, e)
            attempt.mark_failed({"error_class": e.__class__.__name__, "message": str(e)})
            run.set_stage_status(
                stage_id,
                StageExecutionStatus.FAILED,
                message=str(e),
                details={"error_class": e.__class__.__name__},
            )
            run.error = {"stage": stage_id, "message": str(e)}
            run.overall_status = InvestigationRunStatus.FAILED.value
            self.store.save_run(run)

            # Emit STAGE_FAILED event
            self.emit_event(
                run=run,
                event_type=InvestigationEventType.STAGE_FAILED,
                payload={"stage_id": stage_id, "attempt_id": attempt_id, "error": str(e)},
                stage_id=stage_id,
                attempt_id=attempt_id,
                severity=EventSeverity.ERROR,
            )
            raise

    def run_pipeline(
        self,
        run: InvestigationRun,
        context: InvestigationContext,
        handlers: Dict[str, Callable[[InvestigationContext, InvestigationRun], List[ArtifactRef]]],
        interrupt_before_stage: Optional[str] = None,
    ) -> InvestigationRun:
        """Execute registered stages according to DAG topological order.

        Stops gracefully when scientific execution gate is reached, transitioning
        the run to terminal state READY_FOR_DETECTION without scientific evaluation.
        """
        topo_order = self.dag.get_topological_order()

        # Emit RUN_STARTED event
        self.emit_event(
            run=run,
            event_type=InvestigationEventType.RUN_STARTED,
            payload={"run_id": run.run_id, "topological_order": topo_order},
        )

        for stage_id in topo_order:
            node = self.dag.nodes[stage_id]

            # 1. Check for simulated/test interruption
            if interrupt_before_stage and stage_id == interrupt_before_stage:
                logger.info("Simulating interruption before stage '%s'", stage_id)
                run.set_stage_status(stage_id, StageExecutionStatus.RUNNING)
                attempt_id = f"att_{stage_id}_{int(time.time())}_{secrets.token_hex(3)}"
                attempt = StageAttempt(
                    attempt_id=attempt_id,
                    stage_id=stage_id,
                    status=StageExecutionStatus.RUNNING.value,
                )
                run.record_attempt(attempt)
                run.overall_status = InvestigationRunStatus.SUSPENDED.value
                self.store.save_run(run)

                self.emit_event(
                    run=run,
                    event_type=InvestigationEventType.STAGE_INTERRUPTED,
                    payload={"stage_id": stage_id, "attempt_id": attempt_id},
                    stage_id=stage_id,
                    attempt_id=attempt_id,
                    severity=EventSeverity.WARNING,
                )
                self.emit_event(
                    run=run,
                    event_type=InvestigationEventType.RUN_SUSPENDED,
                    payload={"interrupted_before": stage_id},
                )
                return run

            # 2. Check if stage is already completed (e.g. during resume)
            st = run.stages.get(stage_id)
            if st and st.status == StageExecutionStatus.COMPLETED.value:
                logger.debug("Stage '%s' already completed; skipping to next.", stage_id)
                continue

            # 3. Check if handler is registered
            if stage_id not in handlers:
                if node.is_scientific_gated:
                    logger.info("Reached scientific boundary at '%s'; halting at READY_FOR_DETECTION.", stage_id)
                    run.set_stage_status(
                        stage_id,
                        StageExecutionStatus.BLOCKED,
                        message="Scientific model inference is gated (EXECUTION_AUTHORIZED = False).",
                    )
                    run.overall_status = InvestigationRunStatus.READY_FOR_DETECTION.value
                    run.finished_at = datetime.now(timezone.utc).isoformat()
                    self.store.save_run(run)

                    self.emit_event(
                        run=run,
                        event_type=InvestigationEventType.STAGE_BLOCKED,
                        payload={"stage_id": stage_id, "gate_reason": "Scientific execution gated (EXECUTION_AUTHORIZED = False)"},
                        stage_id=stage_id,
                        severity=EventSeverity.WARNING,
                    )
                    self.emit_event(
                        run=run,
                        event_type=InvestigationEventType.RUN_COMPLETED,
                        payload={"terminal_status": "READY_FOR_DETECTION", "scientific_execution_authorized": False},
                    )
                    return run
                else:
                    logger.warning("No handler registered for un-gated stage '%s'; marking SKIPPED.", stage_id)
                    run.set_stage_status(
                        stage_id,
                        StageExecutionStatus.SKIPPED,
                        message=f"No handler registered for un-gated stage '{stage_id}'.",
                    )
                    self.emit_event(
                        run=run,
                        event_type=InvestigationEventType.STAGE_SKIPPED,
                        payload={"stage_id": stage_id, "reason": "no_handler_registered"},
                        stage_id=stage_id,
                    )
                    continue

            # 4. Execute stage handler
            handler = handlers[stage_id]
            try:
                self.execute_stage(run, context, stage_id, handler)
            except ScientificGateViolationError:
                run.overall_status = InvestigationRunStatus.READY_FOR_DETECTION.value
                run.finished_at = datetime.now(timezone.utc).isoformat()
                self.store.save_run(run)
                self.emit_event(
                    run=run,
                    event_type=InvestigationEventType.RUN_COMPLETED,
                    payload={"terminal_status": "READY_FOR_DETECTION", "scientific_execution_authorized": False},
                )
                return run
            except Exception as err:
                run.overall_status = InvestigationRunStatus.FAILED.value
                run.error = {
                    "code": "STAGE_EXECUTION_FAILED",
                    "stage": stage_id,
                    "message": str(err),
                }
                run.finished_at = datetime.now(timezone.utc).isoformat()
                self.store.save_run(run)
                self.emit_event(
                    run=run,
                    event_type=InvestigationEventType.RUN_FAILED,
                    payload={"stage_id": stage_id, "error": str(err)},
                    severity=EventSeverity.ERROR,
                )
                raise

        # All eligible stages finished
        has_failed_or_skipped = any(
            st.status in [StageExecutionStatus.FAILED.value, StageExecutionStatus.SKIPPED.value]
            for st in run.stages.values()
        )
        if has_failed_or_skipped:
            run.overall_status = InvestigationRunStatus.FAILED.value
            self.emit_event(
                run=run,
                event_type=InvestigationEventType.RUN_FAILED,
                payload={"error": "Pipeline completed with failed or skipped stages"},
                severity=EventSeverity.ERROR,
            )
        else:
            run.overall_status = InvestigationRunStatus.SUCCEEDED.value
            self.emit_event(
                run=run,
                event_type=InvestigationEventType.RUN_COMPLETED,
                payload={"terminal_status": "SUCCEEDED"},
            )

        run.finished_at = datetime.now(timezone.utc).isoformat()
        self.store.save_run(run)
        return run

    def resume_pipeline(
        self,
        run: InvestigationRun,
        context: InvestigationContext,
        handlers: Dict[str, Callable[[InvestigationContext, InvestigationRun], List[ArtifactRef]]],
    ) -> InvestigationRun:
        """Resume an interrupted investigation run from its earliest safely resumable stage."""
        self.emit_event(
            run=run,
            event_type=InvestigationEventType.RECOVERY_STARTED,
            payload={"run_id": run.run_id},
        )
        run, next_resumable = self.store.prepare_resume(run, dag=self.dag)
        if not run.recovery_state.can_resume:
            self.emit_event(
                run=run,
                event_type=InvestigationEventType.RECOVERY_BLOCKED,
                payload={"corrupted_artifacts": run.recovery_state.corrupted_artifacts},
                severity=EventSeverity.ERROR,
            )
            return run

        self.emit_event(
            run=run,
            event_type=InvestigationEventType.RECOVERY_COMPLETED,
            payload={
                "next_resumable_stage": next_resumable,
                "completed_stages": run.recovery_state.completed_stages,
            },
        )
        self.emit_event(
            run=run,
            event_type=InvestigationEventType.RUN_RESUMED,
            payload={"next_resumable_stage": next_resumable},
        )
        return self.run_pipeline(run, context, handlers)
