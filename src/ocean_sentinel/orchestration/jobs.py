"""Canonical Job and Manifest Data Models for Pipeline Orchestration V1.

Provides filesystem-backed, deterministic job management for Ocean Sentinel.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from pathlib import Path
import secrets
import tempfile
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class JobMode(str, Enum):
    """Execution mode of the pipeline job."""

    DEMO = "DEMO"
    REAL_REPOSITORY = "REAL_REPOSITORY"
    PHYSICAL = "PHYSICAL"


class PipelineType(str, Enum):
    """Pipeline workflow type."""

    DEMO_FUSION = "DEMO_FUSION"
    ARTIFACT_FUSION = "ARTIFACT_FUSION"
    REAL_REPOSITORY = "REAL_REPOSITORY"
    PHYSICAL = "PHYSICAL"


class JobStatus(str, Enum):
    """Lifecycle status of a pipeline job."""

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED_PROVENANCE = "BLOCKED_PROVENANCE"
    INVALID_INPUT = "INVALID_INPUT"


class PipelineStage(str, Enum):
    """Canonical stages of pipeline execution."""

    VALIDATE = "VALIDATE"
    INGEST = "INGEST"
    PREPROCESS = "PREPROCESS"
    INFER = "INFER"
    INTERPRET = "INTERPRET"
    TEMPORAL = "TEMPORAL"
    DRIFT = "DRIFT"
    AIS = "AIS"
    FUSION = "FUSION"
    EXPORT = "EXPORT"


class StageExecutionStatus(str, Enum):
    """Status of an individual stage execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class StageRecord:
    """Record of execution for a single pipeline stage."""

    stage: str
    status: str = StageExecutionStatus.PENDING.value
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ArtifactRecord:
    """Machine-readable metadata for an artifact generated or consumed by a job."""

    artifact_id: str
    artifact_type: str
    file_path: str
    format: str
    generated_by_stage: str
    relative_path: Optional[str] = None
    size_bytes: Optional[int] = None
    provenance_class: str = "SYNTHETIC_DEMO"
    availability: str = "AVAILABLE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JobErrorRecord:
    """Structured error descriptor."""

    code: str
    message: str
    stage: Optional[str] = None
    retryable: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class JobManifest:
    """Canonical filesystem-backed pipeline job manifest."""

    def __init__(
        self,
        job_id: str,
        mode: Union[JobMode, str] = JobMode.DEMO,
        pipeline_type: Union[PipelineType, str] = PipelineType.DEMO_FUSION,
        created_at: Optional[str] = None,
        started_at: Optional[str] = None,
        finished_at: Optional[str] = None,
        status: Union[JobStatus, str] = JobStatus.CREATED,
        current_stage: Optional[Union[PipelineStage, str]] = None,
        requested_config: Optional[Dict[str, Any]] = None,
        stage_status: Optional[Dict[str, Union[StageRecord, Dict[str, Any]]]] = None,
        artifacts: Optional[List[Union[ArtifactRecord, Dict[str, Any]]]] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[Union[JobErrorRecord, Dict[str, Any]]] = None,
        limitations: Optional[List[str]] = None,
        scenario_id: Optional[str] = None,
        investigation_label: Optional[str] = None,
    ) -> None:
        self.job_id = str(job_id)
        self.mode = mode.value if isinstance(mode, JobMode) else str(mode).upper()
        self.pipeline_type = (
            pipeline_type.value if isinstance(pipeline_type, PipelineType) else str(pipeline_type).upper()
        )
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.started_at = started_at
        self.finished_at = finished_at
        self.status = status.value if isinstance(status, JobStatus) else str(status).upper()
        self.current_stage = (
            current_stage.value
            if isinstance(current_stage, PipelineStage)
            else (str(current_stage).upper() if current_stage else None)
        )
        self.requested_config = dict(requested_config or {})
        self.scenario_id = scenario_id
        self.investigation_label = investigation_label

        # Parse stages
        self.stage_status: Dict[str, Dict[str, Any]] = {}
        if stage_status:
            for k, v in stage_status.items():
                if isinstance(v, StageRecord):
                    self.stage_status[k] = v.to_dict()
                elif isinstance(v, dict):
                    self.stage_status[k] = v

        # Parse artifacts
        self.artifacts: List[Dict[str, Any]] = []
        if artifacts:
            for art in artifacts:
                if isinstance(art, ArtifactRecord):
                    self.artifacts.append(art.to_dict())
                elif isinstance(art, dict):
                    self.artifacts.append(art)

        self.result = dict(result) if result is not None else None

        # Parse error
        if isinstance(error, JobErrorRecord):
            self.error = error.to_dict()
        elif isinstance(error, dict):
            self.error = error
        else:
            self.error = None

        self.limitations = list(limitations or [
            "Local filesystem-backed orchestration MVP for development and evaluation.",
            "Attribution assessments establish evidence compatibility only; NO legal responsibility is assigned.",
            "Absence of AIS records does NOT prove vessel absence.",
        ])

    def set_stage_status(
        self,
        stage: Union[PipelineStage, str],
        status: Union[StageExecutionStatus, str],
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update or create the execution record for a stage."""
        st_name = stage.value if isinstance(stage, PipelineStage) else str(stage).upper()
        st_val = status.value if isinstance(status, StageExecutionStatus) else str(status).upper()

        now_str = datetime.now(timezone.utc).isoformat()
        rec = self.stage_status.get(st_name, {})
        started_at = rec.get("started_at")
        finished_at = rec.get("finished_at")
        duration = rec.get("duration_seconds")

        if st_val == StageExecutionStatus.RUNNING.value:
            started_at = now_str
            self.current_stage = st_name
        elif st_val in [
            StageExecutionStatus.COMPLETED.value,
            StageExecutionStatus.FAILED.value,
            StageExecutionStatus.SKIPPED.value,
            StageExecutionStatus.BLOCKED.value,
        ]:
            finished_at = now_str
            if started_at:
                try:
                    t_start = datetime.fromisoformat(started_at)
                    t_finish = datetime.fromisoformat(finished_at)
                    duration = round((t_finish - t_start).total_seconds(), 4)
                except Exception:
                    duration = None

        merged_details = dict(rec.get("details", {}))
        if details:
            merged_details.update(details)

        self.stage_status[st_name] = {
            "stage": st_name,
            "status": st_val,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": duration,
            "message": message or rec.get("message"),
            "details": merged_details,
        }

    def add_artifact(self, artifact: Union[ArtifactRecord, Dict[str, Any]]) -> None:
        """Register an output artifact."""
        d = artifact.to_dict() if isinstance(artifact, ArtifactRecord) else dict(artifact)
        self.artifacts.append(d)

    def set_failed(
        self,
        code: str,
        message: str,
        stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
    ) -> None:
        """Mark job as failed with structured error descriptor."""
        self.status = JobStatus.FAILED.value
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.error = {
            "code": code,
            "message": message,
            "stage": stage or self.current_stage,
            "retryable": retryable,
            "details": details or {},
        }
        if stage:
            self.set_stage_status(stage, StageExecutionStatus.FAILED, message=message, details=details)

    def set_blocked_provenance(
        self,
        message: str,
        stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark job as blocked due to strict physical provenance rejection."""
        self.status = JobStatus.BLOCKED_PROVENANCE.value
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.error = {
            "code": "PROVENANCE_REJECTION",
            "message": message,
            "stage": stage or self.current_stage,
            "retryable": False,
            "details": details or {},
        }
        if stage:
            self.set_stage_status(stage, StageExecutionStatus.BLOCKED, message=message, details=details)

    def set_succeeded(self, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark job as successfully finished."""
        self.status = JobStatus.SUCCEEDED.value
        self.finished_at = datetime.now(timezone.utc).isoformat()
        if result is not None:
            self.result = result

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete manifest to machine-readable dictionary."""
        return {
            "job_id": self.job_id,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "mode": self.mode,
            "pipeline_type": self.pipeline_type,
            "scenario_id": self.scenario_id,
            "investigation_label": self.investigation_label,
            "status": self.status,
            "current_stage": self.current_stage,
            "requested_config": self.requested_config,
            "stage_status": self.stage_status,
            "artifacts": self.artifacts,
            "result": self.result,
            "error": self.error,
            "limitations": self.limitations,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> JobManifest:
        """Reconstruct a JobManifest from a dictionary."""
        return cls(
            job_id=data["job_id"],
            mode=data.get("mode", JobMode.DEMO.value),
            pipeline_type=data.get("pipeline_type", PipelineType.DEMO_FUSION.value),
            created_at=data.get("created_at"),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            status=data.get("status", JobStatus.CREATED.value),
            current_stage=data.get("current_stage"),
            requested_config=data.get("requested_config"),
            stage_status=data.get("stage_status"),
            artifacts=data.get("artifacts"),
            result=data.get("result"),
            error=data.get("error"),
            limitations=data.get("limitations"),
            scenario_id=data.get("scenario_id"),
            investigation_label=data.get("investigation_label"),
        )


# ---------------------------------------------------------------------------
# Filesystem Job Store
# ---------------------------------------------------------------------------


class JobStore:
    """Filesystem-backed job store managing job workspaces and manifests."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def generate_job_id(self, prefix: str = "job") -> str:
        """Generate a collision-resistant, deterministic timestamped job ID."""
        now_utc = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        rand_token = secrets.token_hex(4)
        return f"{prefix}_{now_utc}_{rand_token}"

    def get_job_dir(self, job_id: str) -> Path:
        """Get the isolated directory path for a job."""
        clean_id = Path(job_id).name
        return self.base_dir / clean_id

    def get_manifest_path(self, job_id: str) -> Path:
        """Get the manifest.json path for a job."""
        return self.get_job_dir(job_id) / "manifest.json"

    def get_artifacts_dir(self, job_id: str) -> Path:
        """Get the directory where job artifacts are saved."""
        d = self.get_job_dir(job_id) / "artifacts"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def create_job(
        self,
        mode: Union[JobMode, str],
        pipeline_type: Union[PipelineType, str],
        requested_config: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
        investigation_label: Optional[str] = None,
    ) -> JobManifest:
        """Create and initialize a new job workspace and initial manifest."""
        jid = job_id or self.generate_job_id()
        job_dir = self.get_job_dir(jid)
        job_dir.mkdir(parents=True, exist_ok=True)

        manifest = JobManifest(
            job_id=jid,
            mode=mode,
            pipeline_type=pipeline_type,
            requested_config=requested_config,
            status=JobStatus.CREATED,
            scenario_id=scenario_id,
            investigation_label=investigation_label,
        )
        self.save_manifest(manifest)
        return manifest

    def save_manifest(self, manifest: JobManifest) -> Path:
        """Atomically persist manifest to disk."""
        target_path = self.get_manifest_path(manifest.job_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        data = manifest.to_dict()
        tmp_file = target_path.with_suffix(".tmp")

        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=False)

        # Atomic replace
        tmp_file.replace(target_path)
        return target_path

    def get_manifest(self, job_id: str) -> Optional[JobManifest]:
        """Read job manifest from disk."""
        path = self.get_manifest_path(job_id)
        if not path.is_file():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return JobManifest.from_dict(data)
        except Exception as e:
            logger.error("Failed to read job manifest '%s': %s", path, e)
            return None

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recently created jobs sorted by creation time descending."""
        jobs: List[Dict[str, Any]] = []
        if not self.base_dir.is_dir():
            return jobs

        for entry in self.base_dir.iterdir():
            if entry.is_dir():
                mf = entry / "manifest.json"
                if mf.is_file():
                    try:
                        with open(mf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        jobs.append({
                            "job_id": data.get("job_id", entry.name),
                            "mode": data.get("mode"),
                            "pipeline_type": data.get("pipeline_type"),
                            "status": data.get("status"),
                            "created_at": data.get("created_at"),
                            "started_at": data.get("started_at"),
                            "finished_at": data.get("finished_at"),
                        })
                    except Exception:
                        pass

        # Sort descending by created_at
        jobs.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return jobs[:limit]
