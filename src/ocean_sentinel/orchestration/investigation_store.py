"""Durable Investigation Run Filesystem Store (Phase 7A).

Manages run workspaces, atomic persistence of manifests, stage states,
attempts, and artifact references. Provides durable crash recovery and
safe resume position determination.

Storage Layout:
---------------
outputs/
  investigations/
    <run_id>/
      manifest.json    # Authoritative InvestigationRun domain root
      stages.json      # Granular stage execution states
      attempts.json    # Historical execution attempt audit log
      artifacts.json   # First-class registered artifact references
      events.jsonl     # Append-only durable event log (Phase 7B)
      artifacts/       # Directory for run-materialized files
      evidence/        # Operational evidence objects & payloads
      logs/            # Optional task-local execution logs
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import secrets
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from ocean_sentinel.orchestration.event_log import DurableEventLog

from ocean_sentinel.orchestration.dag import ScientificDAG, create_canonical_scientific_dag
from ocean_sentinel.orchestration.investigation_run import (
    ArtifactRef,
    ContentStatus,
    InvestigationRun,
    InvestigationRunRecoveryState,
    InvestigationRunStatus,
    InvestigationStageState,
    StageAttempt,
    StageExecutionStatus,
)

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class InvestigationRunStore:
    """Filesystem-backed manager for durable investigation runs."""

    def __init__(self, base_dir: Optional[Path] = None, repo_root: Optional[Path] = None) -> None:
        self.repo_root = Path(repo_root or REPO_ROOT).resolve()
        self.base_dir = Path(base_dir or (self.repo_root / "outputs" / "investigations")).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def generate_run_id(self, prefix: str = "inv") -> str:
        """Generate a collision-resistant, deterministic timestamped run ID."""
        now_utc = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        rand_token = secrets.token_hex(4)
        return f"{prefix}_{now_utc}_{rand_token}"

    def get_run_dir(self, run_id: str) -> Path:
        """Get the isolated directory path for an investigation run."""
        clean_id = Path(run_id).name
        return self.base_dir / clean_id

    def get_manifest_path(self, run_id: str) -> Path:
        return self.get_run_dir(run_id) / "manifest.json"

    def get_stages_path(self, run_id: str) -> Path:
        return self.get_run_dir(run_id) / "stages.json"

    def get_attempts_path(self, run_id: str) -> Path:
        return self.get_run_dir(run_id) / "attempts.json"

    def get_artifacts_path(self, run_id: str) -> Path:
        return self.get_run_dir(run_id) / "artifacts.json"

    def get_events_path(self, run_id: str) -> Path:
        return self.get_run_dir(run_id) / "events.jsonl"

    def get_event_log(self, run_id: str) -> DurableEventLog:
        """Retrieve the durable event log for this run."""
        from ocean_sentinel.orchestration.event_log import DurableEventLog

        if not hasattr(self, "_event_logs"):
            self._event_logs = {}
        if run_id not in self._event_logs:
            self._event_logs[run_id] = DurableEventLog(self.get_events_path(run_id))
        return self._event_logs[run_id]

    def get_artifacts_dir(self, run_id: str) -> Path:
        d = self.get_run_dir(run_id) / "artifacts"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_evidence_dir(self, run_id: str) -> Path:
        d = self.get_run_dir(run_id) / "evidence"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_logs_dir(self, run_id: str) -> Path:
        d = self.get_run_dir(run_id) / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _atomic_write_json(self, target_path: Path, data: Any) -> None:
        """Persist JSON data using atomic write-and-replace."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = target_path.with_suffix(f".tmp_{secrets.token_hex(3)}")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=False)
        tmp_file.replace(target_path)

    def save_run(self, run: InvestigationRun) -> Path:
        """Atomically persist complete investigation run to disk."""
        run_dir = self.get_run_dir(run.run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        self.get_artifacts_dir(run.run_id)
        self.get_evidence_dir(run.run_id)
        self.get_logs_dir(run.run_id)

        # 1. Authoritative manifest.json
        manifest_path = self.get_manifest_path(run.run_id)
        self._atomic_write_json(manifest_path, run.to_dict())

        # 2. Granular sidecars for efficient query / inspection
        self._atomic_write_json(
            self.get_stages_path(run.run_id),
            {k: (v.to_dict() if hasattr(v, "to_dict") else v) for k, v in run.stages.items()},
        )
        self._atomic_write_json(
            self.get_attempts_path(run.run_id),
            [(a.to_dict() if hasattr(a, "to_dict") else a) for a in run.attempts],
        )
        self._atomic_write_json(
            self.get_artifacts_path(run.run_id),
            [(a.to_dict() if hasattr(a, "to_dict") else a) for a in run.artifacts],
        )

        return manifest_path

    def load_run(self, run_id: str) -> Optional[InvestigationRun]:
        """Read and reconstruct an InvestigationRun from durable disk storage."""
        manifest_path = self.get_manifest_path(run_id)
        if not manifest_path.is_file():
            return None

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return InvestigationRun.from_dict(data)
        except Exception as e:
            logger.error("Failed to load run '%s' from '%s': %s", run_id, manifest_path, e)
            return None

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List stored investigation runs sorted by creation time descending."""
        runs: List[Dict[str, Any]] = []
        if not self.base_dir.is_dir():
            return runs

        for entry in self.base_dir.iterdir():
            if entry.is_dir():
                mf = entry / "manifest.json"
                if mf.is_file():
                    try:
                        with open(mf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        runs.append({
                            "run_id": data.get("run_id", entry.name),
                            "created_at": data.get("created_at"),
                            "status": data.get("overall_status"),
                            "current_stage": data.get("current_stage"),
                            "analysis_mode": data.get("request", {}).get("analysis_mode"),
                            "scenario_id": data.get("request", {}).get("scenario_id"),
                            "investigation_label": data.get("request", {}).get("investigation_label"),
                        })
                    except Exception as e:
                        logger.warning("Failed parsing manifest '%s': %s", mf, e)

        runs.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return runs[:limit]

    def determine_recovery_state(
        self,
        run: InvestigationRun,
        dag: Optional[ScientificDAG] = None,
    ) -> InvestigationRunRecoveryState:
        """Inspect durable disk state and determine the safe restart/resume position."""
        active_dag = dag or create_canonical_scientific_dag(run.graph_id)
        topo_order = active_dag.get_topological_order()

        completed_stages: List[str] = []
        corrupted_artifacts: List[str] = []
        interrupted_stage: Optional[str] = None

        # 1. Audit all registered artifacts for integrity
        for art in run.artifacts:
            if not art.verify_integrity(self.repo_root):
                if art.artifact_id not in corrupted_artifacts:
                    corrupted_artifacts.append(art.artifact_id)

        # 2. Verify artifact integrity for completed stages
        for stage_id in topo_order:
            st = run.stages.get(stage_id)
            if st is None:
                continue

            if st.status == StageExecutionStatus.RUNNING.value:
                interrupted_stage = stage_id
            elif st.status == StageExecutionStatus.COMPLETED.value:
                stage_artifacts = [a for a in run.artifacts if a.producer_stage == stage_id]
                has_corrupted = any(a.artifact_id in corrupted_artifacts for a in stage_artifacts)
                if not has_corrupted:
                    completed_stages.append(stage_id)
                else:
                    st.status = StageExecutionStatus.FAILED.value
                    st.message = f"Output artifact verification failed: {[a.artifact_id for a in stage_artifacts if a.artifact_id in corrupted_artifacts]}"

        # 3. Determine earliest safely resumable stage
        completed_set = set(completed_stages)
        ready_stages = active_dag.get_ready_stages(completed_set)
        if interrupted_stage and interrupted_stage in ready_stages:
            next_resumable = interrupted_stage
        else:
            next_resumable = ready_stages[0] if ready_stages else None

        can_resume = len(corrupted_artifacts) == 0 and (
            next_resumable is not None or len(completed_stages) == len(topo_order)
        )

        if not can_resume and len(corrupted_artifacts) > 0:
            next_resumable = None

        # 4. Pending stages
        pending_stages = [
            s for s in topo_order if s not in completed_set and s != next_resumable
        ]

        recovery = InvestigationRunRecoveryState(
            can_resume=can_resume,
            next_resumable_stage=next_resumable,
            interrupted_stage=interrupted_stage,
            completed_stages=completed_stages,
            pending_stages=pending_stages,
            corrupted_artifacts=corrupted_artifacts,
            last_checkpoint_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        run.recovery_state = recovery
        return recovery

    def prepare_resume(
        self,
        run: InvestigationRun,
        dag: Optional[ScientificDAG] = None,
    ) -> Tuple[InvestigationRun, Optional[str]]:
        """Prepare an interrupted or suspended run for resumption.

        Resets interrupted attempts, purges incomplete artifacts from the interrupted stage,
        and transitions the run to RUNNING ready for the next resumable stage.
        """
        recovery = self.determine_recovery_state(run, dag=dag)

        if not recovery.can_resume:
            logger.error("Run '%s' cannot be resumed: %s", run.run_id, recovery.corrupted_artifacts)
            run.overall_status = InvestigationRunStatus.FAILED.value
            run.error = {
                "code": "CANNOT_RESUME",
                "message": f"Artifact integrity checks failed: {recovery.corrupted_artifacts}",
            }
            self.save_run(run)
            return run, None

        # Handle interrupted stage if one exists
        if recovery.interrupted_stage:
            int_id = recovery.interrupted_stage
            st = run.stages.get(int_id)
            if st is not None:
                # Mark latest attempt as INTERRUPTED
                if st.attempts and st.attempts[-1].status == StageExecutionStatus.RUNNING.value:
                    st.attempts[-1].mark_interrupted("Recovered after ungraceful process termination")
                st.status = StageExecutionStatus.PENDING.value
                st.started_at = None
                st.finished_at = None
                st.duration_seconds = None

        run.overall_status = InvestigationRunStatus.RUNNING.value
        run.current_stage = recovery.next_resumable_stage
        self.save_run(run)
        return run, recovery.next_resumable_stage
