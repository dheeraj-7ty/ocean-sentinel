"""Investigation Execution Engine (Phase 7A).

Coordinates deterministic, graph-driven execution of investigation runs
across scientific DAG stages with:
- Config & protocol fingerprinting for stage-level idempotency
- Duplicate artifact creation prevention
- Granular stage attempt audit tracking
- Strict fail-closed scientific execution firewall
- Controlled pause and interruption recovery hooks
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import secrets
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ocean_sentinel.orchestration.dag import (
    DAGValidationError,
    ScientificDAG,
    create_canonical_scientific_dag,
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
    ) -> None:
        self.store = store or InvestigationRunStore(repo_root=repo_root)
        self.dag = dag or create_canonical_scientific_dag()
        self.repo_root = self.store.repo_root

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

        # Deterministic JSON representation of input hashes
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
        # 1. Determine completed stages
        completed_stages = {
            k for k, v in run.stages.items() if v.status == StageExecutionStatus.COMPLETED.value
        }

        # 2. Check execution eligibility against DAG
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
                raise ScientificGateViolationError(reason)
            else:
                run.set_stage_status(
                    stage_id,
                    StageExecutionStatus.FAILED,
                    message=f"Cannot execute stage '{stage_id}': {reason}",
                )
                raise InvestigationEngineError(f"Cannot execute stage '{stage_id}': {reason}")

        # 3. Gather input hashes from dependent stages
        node = self.dag.nodes[stage_id]
        input_hashes: Dict[str, str] = {}
        input_refs: List[str] = []
        for dep in node.dependencies:
            for art in run.artifacts:
                if art.producer_stage == dep:
                    input_hashes[art.artifact_id] = art.sha256
                    input_refs.append(art.artifact_id)

        # 4. Compute config & protocol fingerprint
        fingerprint = self.compute_stage_fingerprint(
            stage_id=stage_id,
            context=context,
            input_hashes=input_hashes,
            stage_config=stage_config,
        )

        # 5. Idempotency Check: if stage already completed with matching fingerprint and valid outputs
        st = run.stages.get(stage_id)
        if st and st.status == StageExecutionStatus.COMPLETED.value and st.latest_fingerprint == fingerprint:
            # Verify outputs physically on disk
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
                # Reuse latest attempt or create a skipped attempt record
                existing_attempt = next(
                    (a for a in reversed(st.attempts) if a.status == StageExecutionStatus.COMPLETED.value),
                    None,
                )
                if existing_attempt:
                    return existing_attempt
                run_attempt = next(
                    (
                        a
                        for a in reversed(run.attempts)
                        if a.stage_id == stage_id and a.status == StageExecutionStatus.COMPLETED.value
                    ),
                    None,
                )
                if run_attempt:
                    return run_attempt

        # 6. Initialize new execution attempt
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

        # 7. Execute stage handler
        try:
            output_artifacts = handler(context, run)
            output_hashes: Dict[str, str] = {}
            output_refs: List[str] = []

            for art in output_artifacts:
                # Enforce SHA-256 calculation / verification
                art.producer_stage = stage_id
                art.verify_integrity(self.repo_root)
                run.add_artifact(art)
                context.register_artifact(art)
                output_hashes[art.artifact_id] = art.sha256
                output_refs.append(art.artifact_id)

            attempt.mark_completed(output_hashes)
            run.set_stage_status(stage_id, StageExecutionStatus.COMPLETED)
            st = run.stages[stage_id]
            st.output_refs = output_refs
            st.latest_fingerprint = fingerprint

            self.store.save_run(run)
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

        for stage_id in topo_order:
            node = self.dag.nodes[stage_id]

            # 1. Check for simulated/test interruption
            if interrupt_before_stage and stage_id == interrupt_before_stage:
                logger.info("Simulating interruption before stage '%s'", stage_id)
                run.set_stage_status(stage_id, StageExecutionStatus.RUNNING)
                # Create an in-flight attempt record
                attempt_id = f"att_{stage_id}_{int(time.time())}_{secrets.token_hex(3)}"
                attempt = StageAttempt(
                    attempt_id=attempt_id,
                    stage_id=stage_id,
                    status=StageExecutionStatus.RUNNING.value,
                )
                run.record_attempt(attempt)
                run.overall_status = InvestigationRunStatus.SUSPENDED.value
                self.store.save_run(run)
                return run

            # 2. Check if stage is already completed (e.g. during resume)
            st = run.stages.get(stage_id)
            if st and st.status == StageExecutionStatus.COMPLETED.value:
                logger.debug("Stage '%s' already completed; skipping to next.", stage_id)
                continue

            # 3. Check if handler is registered
            if stage_id not in handlers:
                # If stage is scientific-gated, halt fail-closed
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
                    return run
                else:
                    logger.warning("No handler registered for un-gated stage '%s'; marking SKIPPED.", stage_id)
                    run.set_stage_status(
                        stage_id,
                        StageExecutionStatus.SKIPPED,
                        message=f"No handler registered for un-gated stage '{stage_id}'.",
                    )
                    continue

            # 4. Execute stage handler
            handler = handlers[stage_id]
            try:
                self.execute_stage(run, context, stage_id, handler)
            except ScientificGateViolationError:
                # Scientific gate reached
                run.overall_status = InvestigationRunStatus.READY_FOR_DETECTION.value
                run.finished_at = datetime.now(timezone.utc).isoformat()
                self.store.save_run(run)
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
                raise

        # All eligible stages finished
        has_failed_or_skipped = any(
            st.status in [StageExecutionStatus.FAILED.value, StageExecutionStatus.SKIPPED.value]
            for st in run.stages.values()
        )
        if has_failed_or_skipped:
            run.overall_status = InvestigationRunStatus.FAILED.value
        else:
            run.overall_status = InvestigationRunStatus.SUCCEEDED.value
        run.finished_at = datetime.now(timezone.utc).isoformat()
        self.store.save_run(run)
        return run
