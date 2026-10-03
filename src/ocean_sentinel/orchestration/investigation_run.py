"""Investigation Run Domain Model & Durable Execution Types (Phase 7A).

Provides the core domain primitives for durable, recoverable investigation runs:
- InvestigationRun: Durable run-level domain object
- InvestigationRunRequest: Standardized request parameters
- ArtifactRef: First-class integrity-bound artifact reference
- StageAttempt: Executable stage execution attempt record with fingerprints
- StageRetryPolicy: Granular stage-specific retry semantics
- InvestigationStageState: Stage lifecycle and execution tracking
- InvestigationRunRecoveryState: Durable recovery metadata

Governance & Provenance Guarantees:
-----------------------------------
1. SHA-256 digests provide cryptographic integrity binding and provenance
   lineage only; they do not imply non-repudiation, digital signatures,
   or legal authenticity.
2. Scientific execution remains strictly fail-closed: model inference,
   training, holdout evaluation, and Trujillo Part III access are disabled
   by default unless explicitly authorized.
3. Terminology matches canonical implementation truth: initial job lifecycle
   state is REQUESTED (not SUBMITTED).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
from pathlib import Path
import secrets
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InvestigationRunStatus(str, Enum):
    """Lifecycle status of a durable investigation run."""

    REQUESTED = "REQUESTED"
    DISCOVERING = "DISCOVERING"
    ACQUIRING = "ACQUIRING"
    PERSISTING = "PERSISTING"
    VALIDATING = "VALIDATING"
    RUNNING = "RUNNING"
    SUSPENDED = "SUSPENDED"
    READY_FOR_DETECTION = "READY_FOR_DETECTION"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class StageExecutionStatus(str, Enum):
    """Status of an individual stage execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    INTERRUPTED = "INTERRUPTED"


class ArtifactType(str, Enum):
    """Classification of investigation artifacts."""

    GEOTIFF = "GEOTIFF"
    JSON_METADATA = "JSON_METADATA"
    GEOJSON = "GEOJSON"
    MASK = "MASK"
    CSV = "CSV"
    REPORT = "REPORT"
    EVIDENCE_OBJECT = "EVIDENCE_OBJECT"
    CONFIG = "CONFIG"
    UNKNOWN = "UNKNOWN"


class ProvenanceClass(str, Enum):
    """Data provenance origin class."""

    REAL_OBSERVATION = "REAL_OBSERVATION"
    DERIVED_ANALYTICAL = "DERIVED_ANALYTICAL"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    GOVERNED_BASELINE = "GOVERNED_BASELINE"


class ContentStatus(str, Enum):
    """Integrity status of referenced artifact content."""

    INTEGRITY_VERIFIED = "INTEGRITY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    MISSING = "MISSING"
    CORRUPTED = "CORRUPTED"


# ---------------------------------------------------------------------------
# Core Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class InvestigationRunRequest:
    """Standardized request envelope for an investigation run."""

    location: Optional[Dict[str, Any]] = None
    aoi: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None
    time_window: Optional[Dict[str, str]] = None
    analysis_mode: str = "DEMO"
    requested_outputs: List[str] = field(default_factory=list)
    provider: str = "copernicus_cdse"
    platform: str = "sentinel-1"
    polarizations: List[str] = field(default_factory=lambda: ["VV", "VH"])
    investigation_label: Optional[str] = None
    scenario_id: Optional[str] = None
    spatial_tolerance_m: float = 5000.0
    temporal_tolerance_hours: float = 2.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InvestigationRunRequest:
        return cls(
            location=data.get("location"),
            aoi=data.get("aoi"),
            bbox=data.get("bbox"),
            time_window=data.get("time_window"),
            analysis_mode=data.get("analysis_mode", "DEMO"),
            requested_outputs=list(data.get("requested_outputs", [])),
            provider=data.get("provider", "copernicus_cdse"),
            platform=data.get("platform", "sentinel-1"),
            polarizations=list(data.get("polarizations", ["VV", "VH"])),
            investigation_label=data.get("investigation_label"),
            scenario_id=data.get("scenario_id"),
            spatial_tolerance_m=float(data.get("spatial_tolerance_m", 5000.0)),
            temporal_tolerance_hours=float(data.get("temporal_tolerance_hours", 2.0)),
        )


@dataclass
class ArtifactRef:
    """First-class reference to an investigation artifact.

    Provides cryptographic SHA-256 integrity binding and provenance lineage.
    Note: SHA-256 hashing verifies content integrity; it does not provide
    digital signatures, non-repudiation, or legal authenticity.
    """

    artifact_id: str
    type: str
    format: str
    path: str
    size_bytes: int
    sha256: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    producer_stage: str = "UNKNOWN"
    input_artifacts: List[str] = field(default_factory=list)
    dataset_identity: Optional[str] = None
    model_identity: Optional[str] = None
    protocol_identity: Optional[str] = None
    spatial_metadata: Optional[Dict[str, Any]] = None
    temporal_metadata: Optional[Dict[str, Any]] = None
    provenance_class: str = ProvenanceClass.DERIVED_ANALYTICAL.value
    content_status: str = ContentStatus.UNVERIFIED.value

    def verify_integrity(self, repo_root: Optional[Path] = None) -> bool:
        """Verify that the physical file exists and matches its SHA-256 digest."""
        base = Path(repo_root) if repo_root else Path.cwd()
        target = (base / self.path) if not Path(self.path).is_absolute() else Path(self.path)

        if not target.is_file():
            self.content_status = ContentStatus.MISSING.value
            return False

        try:
            h = hashlib.sha256()
            with open(target, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            actual_digest = h.hexdigest().lower()
            if actual_digest == self.sha256.lower():
                self.content_status = ContentStatus.INTEGRITY_VERIFIED.value
                self.size_bytes = target.stat().st_size
                return True
            else:
                self.content_status = ContentStatus.CORRUPTED.value
                logger.warning(
                    "Artifact '%s' SHA-256 mismatch: recorded=%s actual=%s",
                    self.artifact_id,
                    self.sha256,
                    actual_digest,
                )
                return False
        except Exception as e:
            self.content_status = ContentStatus.CORRUPTED.value
            logger.error("Failed to read artifact '%s': %s", target, e)
            return False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ArtifactRef:
        return cls(
            artifact_id=data["artifact_id"],
            type=data["type"],
            format=data["format"],
            path=data["path"],
            size_bytes=int(data.get("size_bytes", 0)),
            sha256=data["sha256"],
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            producer_stage=data.get("producer_stage", "UNKNOWN"),
            input_artifacts=list(data.get("input_artifacts", [])),
            dataset_identity=data.get("dataset_identity"),
            model_identity=data.get("model_identity"),
            protocol_identity=data.get("protocol_identity"),
            spatial_metadata=data.get("spatial_metadata"),
            temporal_metadata=data.get("temporal_metadata"),
            provenance_class=data.get("provenance_class", ProvenanceClass.DERIVED_ANALYTICAL.value),
            content_status=data.get("content_status", ContentStatus.UNVERIFIED.value),
        )


@dataclass
class StageAttempt:
    """Execution attempt record for an individual stage."""

    attempt_id: str
    stage_id: str
    attempt_number: int = 1
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: Optional[str] = None
    status: str = StageExecutionStatus.RUNNING.value
    input_hashes: Dict[str, str] = field(default_factory=dict)
    output_hashes: Dict[str, str] = field(default_factory=dict)
    config_fingerprint: str = ""
    error: Optional[Dict[str, Any]] = None

    def mark_completed(self, output_hashes: Dict[str, str]) -> None:
        self.ended_at = datetime.now(timezone.utc).isoformat()
        self.status = StageExecutionStatus.COMPLETED.value
        self.output_hashes = dict(output_hashes)

    def mark_failed(self, error: Dict[str, Any]) -> None:
        self.ended_at = datetime.now(timezone.utc).isoformat()
        self.status = StageExecutionStatus.FAILED.value
        self.error = dict(error)

    def mark_interrupted(self, message: str = "Process interrupted before completion") -> None:
        self.ended_at = datetime.now(timezone.utc).isoformat()
        self.status = StageExecutionStatus.INTERRUPTED.value
        self.error = {"code": "PROCESS_INTERRUPTED", "message": message}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StageAttempt:
        return cls(
            attempt_id=data["attempt_id"],
            stage_id=data["stage_id"],
            attempt_number=int(data.get("attempt_number", 1)),
            started_at=data.get("started_at", datetime.now(timezone.utc).isoformat()),
            ended_at=data.get("ended_at"),
            status=data.get("status", StageExecutionStatus.RUNNING.value),
            input_hashes=dict(data.get("input_hashes", {})),
            output_hashes=dict(data.get("output_hashes", {})),
            config_fingerprint=data.get("config_fingerprint", ""),
            error=data.get("error"),
        )


@dataclass
class StageRetryPolicy:
    """Stage-specific retry semantics."""

    max_retries: int = 0
    retryable_errors: List[str] = field(default_factory=list)
    backoff_seconds: float = 1.0
    is_safe_retry: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StageRetryPolicy:
        return cls(
            max_retries=int(data.get("max_retries", 0)),
            retryable_errors=list(data.get("retryable_errors", [])),
            backoff_seconds=float(data.get("backoff_seconds", 1.0)),
            is_safe_retry=bool(data.get("is_safe_retry", False)),
        )


@dataclass
class InvestigationStageState:
    """Execution state and history for an individual stage."""

    stage_id: str
    version: str = "1.0.0"
    status: str = StageExecutionStatus.PENDING.value
    dependencies: List[str] = field(default_factory=list)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    input_refs: List[str] = field(default_factory=list)
    output_refs: List[str] = field(default_factory=list)
    attempts: List[StageAttempt] = field(default_factory=list)
    latest_fingerprint: Optional[str] = None
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "version": self.version,
            "status": self.status,
            "dependencies": self.dependencies,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "input_refs": self.input_refs,
            "output_refs": self.output_refs,
            "attempts": [a.to_dict() for a in self.attempts],
            "latest_fingerprint": self.latest_fingerprint,
            "message": self.message,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InvestigationStageState:
        attempts = [StageAttempt.from_dict(a) for a in data.get("attempts", [])]
        return cls(
            stage_id=data["stage_id"],
            version=data.get("version", "1.0.0"),
            status=data.get("status", StageExecutionStatus.PENDING.value),
            dependencies=list(data.get("dependencies", [])),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            duration_seconds=data.get("duration_seconds"),
            input_refs=list(data.get("input_refs", [])),
            output_refs=list(data.get("output_refs", [])),
            attempts=attempts,
            latest_fingerprint=data.get("latest_fingerprint"),
            message=data.get("message"),
            details=dict(data.get("details", {})),
        )


@dataclass
class InvestigationRunRecoveryState:
    """State metadata evaluating run recoverability and resume position."""

    can_resume: bool = True
    next_resumable_stage: Optional[str] = None
    interrupted_stage: Optional[str] = None
    completed_stages: List[str] = field(default_factory=list)
    pending_stages: List[str] = field(default_factory=list)
    corrupted_artifacts: List[str] = field(default_factory=list)
    last_checkpoint_timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InvestigationRunRecoveryState:
        return cls(
            can_resume=bool(data.get("can_resume", True)),
            next_resumable_stage=data.get("next_resumable_stage"),
            interrupted_stage=data.get("interrupted_stage"),
            completed_stages=list(data.get("completed_stages", [])),
            pending_stages=list(data.get("pending_stages", [])),
            corrupted_artifacts=list(data.get("corrupted_artifacts", [])),
            last_checkpoint_timestamp=data.get("last_checkpoint_timestamp"),
        )


# ---------------------------------------------------------------------------
# InvestigationRun Domain Root
# ---------------------------------------------------------------------------


@dataclass
class InvestigationRun:
    """Durable, recoverable domain root for an investigation execution.

    Maintains run lifecycle, explicit stage states, attempts, registered
    artifact references, and recovery parameters across process boundaries.
    """

    run_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    request: InvestigationRunRequest = field(default_factory=InvestigationRunRequest)
    provenance_policy: str = "FAIL_CLOSED_OPERATIONAL"
    graph_id: str = "canonical_scientific_dag_v1"
    current_stage: Optional[str] = None
    overall_status: str = InvestigationRunStatus.REQUESTED.value
    stages: Dict[str, InvestigationStageState] = field(default_factory=dict)
    artifacts: List[ArtifactRef] = field(default_factory=list)
    attempts: List[StageAttempt] = field(default_factory=list)
    evidence_state: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(
        default_factory=lambda: [
            "Local filesystem-backed investigation run kernel (Phase 7A).",
            "Attribution assessments establish evidence compatibility only; NO legal responsibility assigned.",
            "Absence of AIS records does NOT prove vessel absence.",
            "Scientific model execution is strictly gated (EXECUTION_AUTHORIZED = False).",
        ]
    )
    error: Optional[Dict[str, Any]] = None
    recovery_state: InvestigationRunRecoveryState = field(default_factory=InvestigationRunRecoveryState)

    def add_artifact(self, artifact: ArtifactRef) -> None:
        """Register or update an artifact reference."""
        for idx, existing in enumerate(self.artifacts):
            if existing.artifact_id == artifact.artifact_id:
                self.artifacts[idx] = artifact
                return
        self.artifacts.append(artifact)

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactRef]:
        for a in self.artifacts:
            if a.artifact_id == artifact_id:
                return a
        return None

    def record_attempt(self, attempt: StageAttempt) -> None:
        """Record a stage attempt globally and within stage state."""
        self.attempts.append(attempt)
        if attempt.stage_id not in self.stages:
            self.stages[attempt.stage_id] = InvestigationStageState(stage_id=attempt.stage_id)
        self.stages[attempt.stage_id].attempts.append(attempt)

    def set_stage_status(
        self,
        stage_id: str,
        status: Union[StageExecutionStatus, str],
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update lifecycle status of an individual stage."""
        val = status.value if isinstance(status, StageExecutionStatus) else str(status).upper()
        now_str = datetime.now(timezone.utc).isoformat()

        if stage_id not in self.stages:
            self.stages[stage_id] = InvestigationStageState(stage_id=stage_id)

        st = self.stages[stage_id]
        st.status = val
        if message:
            st.message = message
        if details:
            st.details.update(details)

        if val == StageExecutionStatus.RUNNING.value:
            st.started_at = now_str
            self.current_stage = stage_id
            if self.overall_status == InvestigationRunStatus.REQUESTED.value:
                self.overall_status = InvestigationRunStatus.RUNNING.value
                self.started_at = now_str
        elif val in [
            StageExecutionStatus.COMPLETED.value,
            StageExecutionStatus.FAILED.value,
            StageExecutionStatus.SKIPPED.value,
            StageExecutionStatus.BLOCKED.value,
            StageExecutionStatus.INTERRUPTED.value,
        ]:
            st.finished_at = now_str
            if st.started_at:
                try:
                    t0 = datetime.fromisoformat(st.started_at)
                    t1 = datetime.fromisoformat(now_str)
                    st.duration_seconds = round((t1 - t0).total_seconds(), 4)
                except Exception:
                    st.duration_seconds = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete run to machine-readable dictionary."""
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "request": self.request.to_dict(),
            "provenance_policy": self.provenance_policy,
            "graph_id": self.graph_id,
            "current_stage": self.current_stage,
            "overall_status": self.overall_status,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "artifacts": [a.to_dict() for a in self.artifacts],
            "attempts": [a.to_dict() for a in self.attempts],
            "evidence_state": self.evidence_state,
            "limitations": self.limitations,
            "error": self.error,
            "recovery_state": self.recovery_state.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InvestigationRun:
        """Reconstruct an InvestigationRun from a serialized dictionary."""
        stages = {k: InvestigationStageState.from_dict(v) for k, v in data.get("stages", {}).items()}
        artifacts = [ArtifactRef.from_dict(a) for a in data.get("artifacts", [])]
        attempts = [StageAttempt.from_dict(a) for a in data.get("attempts", [])]
        req = InvestigationRunRequest.from_dict(data.get("request", {}))
        rec = InvestigationRunRecoveryState.from_dict(data.get("recovery_state", {}))

        return cls(
            run_id=data["run_id"],
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            request=req,
            provenance_policy=data.get("provenance_policy", "FAIL_CLOSED_OPERATIONAL"),
            graph_id=data.get("graph_id", "canonical_scientific_dag_v1"),
            current_stage=data.get("current_stage"),
            overall_status=data.get("overall_status", InvestigationRunStatus.REQUESTED.value),
            stages=stages,
            artifacts=artifacts,
            attempts=attempts,
            evidence_state=dict(data.get("evidence_state", {})),
            limitations=list(data.get("limitations", [])),
            error=data.get("error"),
            recovery_state=rec,
        )

    @classmethod
    def from_acquisition_manifest(cls, manifest: Any) -> InvestigationRun:
        """Convert a Phase 6C AcquisitionJobManifest into a durable InvestigationRun."""
        params = getattr(manifest, "request_params", {}) or {}
        req = InvestigationRunRequest(
            bbox=params.get("bbox"),
            time_window={"start_time": str(params.get("start_time", "")), "end_time": str(params.get("end_time", ""))},
            provider=getattr(manifest, "provider", "copernicus_cdse") or "copernicus_cdse",
            platform=params.get("platform", "sentinel-1"),
            polarizations=list(params.get("polarizations", ["VV", "VH"])),
            investigation_label=params.get("investigation_label"),
            analysis_mode="PHYSICAL",
        )

        run = cls(
            run_id=manifest.job_id,
            created_at=manifest.created_at,
            started_at=manifest.started_at,
            finished_at=manifest.finished_at,
            request=req,
            provenance_policy="FAIL_CLOSED_OPERATIONAL",
            graph_id="canonical_scientific_dag_v1",
            current_stage=getattr(manifest, "current_stage", None),
            overall_status=manifest.status,
            evidence_state={
                "evidence_id": getattr(manifest, "evidence_id", None),
                "execution_authorized": getattr(manifest, "execution_authorized", False),
                "has_prediction": getattr(manifest, "has_prediction", False),
            },
            limitations=list(getattr(manifest, "limitations", [])),
            error=getattr(manifest, "error", None),
        )

        # Register GeoTIFF artifact if present
        if getattr(manifest, "geotiff_path", None) and getattr(manifest, "content_sha256", None):
            run.add_artifact(
                ArtifactRef(
                    artifact_id=f"art_geotiff_{manifest.job_id}",
                    type=ArtifactType.GEOTIFF.value,
                    format="raster/geotiff",
                    path=manifest.geotiff_path,
                    size_bytes=0,
                    sha256=manifest.content_sha256,
                    created_at=manifest.finished_at or manifest.created_at,
                    producer_stage="ACQUIRE",
                    provenance_class=ProvenanceClass.REAL_OBSERVATION.value,
                    content_status=ContentStatus.UNVERIFIED.value,
                )
            )

        # Register metadata sidecar artifact if present
        if getattr(manifest, "metadata_path", None):
            run.add_artifact(
                ArtifactRef(
                    artifact_id=f"art_metadata_{manifest.job_id}",
                    type=ArtifactType.JSON_METADATA.value,
                    format="application/json",
                    path=manifest.metadata_path,
                    size_bytes=0,
                    sha256="",
                    created_at=manifest.finished_at or manifest.created_at,
                    producer_stage="PERSIST",
                    provenance_class=ProvenanceClass.REAL_OBSERVATION.value,
                    content_status=ContentStatus.UNVERIFIED.value,
                )
            )

        return run

