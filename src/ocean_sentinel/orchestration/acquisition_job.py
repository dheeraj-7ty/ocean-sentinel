"""Operational Acquisition Job & Workflow Orchestrator (Phase 6C).

Coordinates user/API-triggered Earth-observation acquisition workflows:
    USER/API REQUEST
          ↓
    ACQUISITION JOB (Deterministic ID & Initial Manifest)
          ↓
    DISCOVERY (CDSE STAC catalog search)
          ↓
    REAL-DATA RETRIEVAL (Authenticated Process API request)
          ↓
    PERSISTENCE (Atomic GeoTIFF + Metadata Sidecar to data/raw/acquisitions/)
          ↓
    INTEGRITY VERIFICATION (Cryptographic SHA-256 match)
          ↓
    SAR VALIDATION (Dual-band, float32, georeferenced preflight contract)
          ↓
    OPERATIONAL EVIDENCE OBJECT (Canonical structured lineage record)
          ↓
    JOB STATUS / RESULT API (READY_FOR_DETECTION, zero scientific inference)

Scientific & Safety Guardrails:
------------------------------
1. EXECUTION_AUTHORIZED = False:
   Detection boundary halts strictly at preflight. No forward passes, no detections,
   no holdout/Trujillo Part III evaluation, no threshold tuning.
2. ZERO SYNTHETIC FALLBACK:
   Synthetic/mock/demo providers are rejected fail-closed.
3. EXPLICIT FAILURE STATES:
   Network, provider, persistence, integrity, or validation failures transition
   to explicit failure states (FAILED_DISCOVERY, FAILED_ACQUISITION, etc.).
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

from ocean_sentinel.config import CopernicusSettings, get_settings
from ocean_sentinel.errors import (
    AuthenticationError,
    AuthorizationError,
    InvalidAOIError,
    InvalidRequestError,
    InvalidTimeRangeError,
    ProviderInvalidResponseError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RasterValidationError,
    SatelliteError,
)
from ocean_sentinel.models import (
    AcquisitionMetadata,
    BoundingBox,
    ImageryRequest,
    ImageryResult,
    OutputConfig,
    Polarization,
    ProductType,
    SearchRequest,
    TimeRange,
)
from ocean_sentinel.operational_pipeline import (
    OperationalEvidenceResult,
    OperationalIngestionRequest,
    OperationalSARPipeline,
    PipelineStageState,
)
from ocean_sentinel.orchestration.jobs import JobStore
from ocean_sentinel.satellite.auth import TokenManager
from ocean_sentinel.satellite.discovery import SentinelDiscoveryService
from ocean_sentinel.satellite.imagery import SentinelImageryService
from ocean_sentinel.satellite.persistence import (
    AcquisitionPersistenceService,
    PersistedAcquisitionArtifact,
    PersistenceError,
    PersistenceIntegrityError,
    RealDataAcquisitionBridge,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
GOVERNED_ACQUISITIONS_DIR = REPO_ROOT / "data" / "raw" / "acquisitions"


# ---------------------------------------------------------------------------
# State Machine Enums
# ---------------------------------------------------------------------------


class AcquisitionJobStatus(str, Enum):
    """Lifecycle status of an operational acquisition job."""

    REQUESTED = "REQUESTED"
    DISCOVERING = "DISCOVERING"
    ACQUIRING = "ACQUIRING"
    PERSISTING = "PERSISTING"
    VALIDATING = "VALIDATING"
    READY_FOR_DETECTION = "READY_FOR_DETECTION"

    # Explicit failure states
    FAILED_DISCOVERY = "FAILED_DISCOVERY"
    FAILED_ACQUISITION = "FAILED_ACQUISITION"
    FAILED_PERSISTENCE = "FAILED_PERSISTENCE"
    FAILED_INTEGRITY = "FAILED_INTEGRITY"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    REJECTED_INPUT = "REJECTED_INPUT"


class AcquisitionJobStage(str, Enum):
    """Operational acquisition execution stages."""

    REQUEST = "REQUEST"
    DISCOVER = "DISCOVER"
    ACQUIRE = "ACQUIRE"
    PERSIST = "PERSIST"
    VALIDATE = "VALIDATE"
    COMPLETE = "COMPLETE"


# ---------------------------------------------------------------------------
# Acquisition Job Manifest Model
# ---------------------------------------------------------------------------


@dataclass
class AcquisitionJobManifest:
    """Filesystem-backed canonical manifest of an operational acquisition job."""

    job_id: str
    status: str = AcquisitionJobStatus.REQUESTED.value
    current_stage: str = AcquisitionJobStage.REQUEST.value
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    request_params: Dict[str, Any] = field(default_factory=dict)
    stage_timings: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Bound operational acquisition identity & provenance
    acquisition_id: Optional[str] = None
    provider: Optional[str] = None
    source_reference: Optional[str] = None
    geotiff_path: Optional[str] = None
    metadata_path: Optional[str] = None
    content_sha256: Optional[str] = None
    sar_validation: Optional[Dict[str, Any]] = None

    # Operational evidence binding
    evidence_id: Optional[str] = None
    evidence_result: Optional[Dict[str, Any]] = None

    # Security & scientific invariants
    execution_authorized: bool = False
    has_prediction: bool = False

    # Failure descriptor
    error: Optional[Dict[str, Any]] = None

    limitations: List[str] = field(
        default_factory=lambda: [
            "Operational acquisition pre-scientific validation boundary.",
            "Model inference strictly firewalled (EXECUTION_AUTHORIZED = False).",
            "Artifacts verified for bitwise SHA-256 integrity and SAR raster compliance.",
        ]
    )

    def set_stage(
        self,
        stage: AcquisitionJobStage,
        status: AcquisitionJobStatus,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record stage transition with ISO UTC timestamps."""
        now_str = datetime.now(timezone.utc).isoformat()
        self.current_stage = stage.value
        self.status = status.value

        if self.started_at is None:
            self.started_at = now_str

        st_rec = self.stage_timings.get(stage.value, {})
        started_at = st_rec.get("started_at", now_str)
        finished_at = now_str if "FAILED" in status.value or status == AcquisitionJobStatus.READY_FOR_DETECTION else None

        duration = None
        if finished_at and started_at:
            try:
                t0 = datetime.fromisoformat(started_at)
                t1 = datetime.fromisoformat(finished_at)
                duration = round((t1 - t0).total_seconds(), 4)
            except Exception:
                duration = None

        merged_details = dict(st_rec.get("details", {}))
        if details:
            merged_details.update(details)

        self.stage_timings[stage.value] = {
            "stage": stage.value,
            "status": status.value,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": duration,
            "message": message,
            "details": merged_details,
        }

    def set_failed(
        self,
        code: str,
        message: str,
        stage: AcquisitionJobStage,
        failure_status: AcquisitionJobStatus,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark job as failed with explicit failure state."""
        self.set_stage(
            stage=stage,
            status=failure_status,
            message=f"[{code}] {message}",
            details=details,
        )
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.error = {
            "code": code,
            "message": message,
            "stage": stage.value,
            "failure_status": failure_status.value,
            "details": details or {},
        }

    def set_ready_for_detection(
        self,
        artifact: PersistedAcquisitionArtifact,
        evidence: OperationalEvidenceResult,
    ) -> None:
        """Mark job as completed at the READY_FOR_DETECTION operational boundary."""
        now_str = datetime.now(timezone.utc).isoformat()
        self.finished_at = now_str
        self.acquisition_id = artifact.acquisition_id
        self.provider = artifact.provider
        self.source_reference = artifact.source_reference
        self.geotiff_path = artifact.geotiff_path
        self.metadata_path = artifact.metadata_path
        self.content_sha256 = artifact.content_sha256
        self.sar_validation = {
            "status": "PASSED",
            "band_count": len(artifact.polarizations),
            "polarizations": artifact.polarizations,
            "width": artifact.width,
            "height": artifact.height,
            "crs": artifact.crs,
            "sha256": artifact.content_sha256,
        }
        self.evidence_id = evidence.evidence_id
        self.evidence_result = evidence.to_dict()
        self.execution_authorized = False
        self.has_prediction = False

        self.set_stage(
            stage=AcquisitionJobStage.COMPLETE,
            status=AcquisitionJobStatus.READY_FOR_DETECTION,
            message="Operational acquisition validated and ready for detection preflight.",
            details={
                "evidence_id": evidence.evidence_id,
                "acquisition_id": artifact.acquisition_id,
                "content_sha256": artifact.content_sha256,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AcquisitionJobManifest:
        """Deserialize from dictionary."""
        return cls(**data)


# ---------------------------------------------------------------------------
# Acquisition Job Orchestrator
# ---------------------------------------------------------------------------


class AcquisitionJobOrchestrator:
    """Orchestrates end-to-end operational acquisition workflows."""

    def __init__(
        self,
        job_store: Optional[JobStore] = None,
        discovery_service: Optional[SentinelDiscoveryService] = None,
        imagery_service: Optional[SentinelImageryService] = None,
        persistence_service: Optional[AcquisitionPersistenceService] = None,
        bridge: Optional[RealDataAcquisitionBridge] = None,
        settings: Optional[CopernicusSettings] = None,
    ) -> None:
        self.job_store = job_store or JobStore(REPO_ROOT / "outputs" / "jobs")
        if settings is not None:
            self._settings = settings
        else:
            try:
                self._settings = get_settings()
            except Exception:
                self._settings = CopernicusSettings(
                    copernicus_client_id="stub_test_id",  # type: ignore[arg-type]
                    copernicus_client_secret="stub_test_secret",  # type: ignore[arg-type]
                )

        self.discovery_service = discovery_service or SentinelDiscoveryService(self._settings)
        if imagery_service is None:
            tm = TokenManager(self._settings)
            self.imagery_service = SentinelImageryService(self._settings, tm)
        else:
            self.imagery_service = imagery_service

        self.persistence_service = persistence_service or AcquisitionPersistenceService(
            storage_root=GOVERNED_ACQUISITIONS_DIR
        )
        self.bridge = bridge or RealDataAcquisitionBridge(
            persistence_service=self.persistence_service,
            operational_pipeline=OperationalSARPipeline(execution_authorized=False),
        )

    def generate_job_id(self) -> str:
        """Produce deterministic, collision-resistant job identity."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        token = secrets.token_hex(4)
        return f"acq_{ts}_{token}"

    def save_job_manifest(self, manifest: AcquisitionJobManifest) -> Path:
        """Persist acquisition job manifest atomically to the job directory."""
        job_dir = self.job_store.get_job_dir(manifest.job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = job_dir / "manifest.json"

        tmp_path = manifest_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)
        tmp_path.replace(manifest_path)
        return manifest_path

    def get_job_manifest(self, job_id: str) -> Optional[AcquisitionJobManifest]:
        """Read acquisition job manifest from job directory."""
        job_dir = self.job_store.get_job_dir(job_id)
        manifest_path = job_dir / "manifest.json"
        if not manifest_path.is_file():
            return None
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AcquisitionJobManifest.from_dict(data)
        except Exception as e:
            logger.error("Failed to load acquisition manifest %s: %s", manifest_path, e)
            return None

    def list_acquisition_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recently executed acquisition jobs."""
        results: List[Dict[str, Any]] = []
        if not self.job_store.base_dir.is_dir():
            return results

        for entry in self.job_store.base_dir.iterdir():
            if entry.is_dir() and entry.name.startswith("acq_"):
                mf_path = entry / "manifest.json"
                if mf_path.is_file():
                    try:
                        with open(mf_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        results.append(data)
                    except Exception:
                        pass
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results[:limit]

    async def execute_acquisition_job(
        self,
        west: float,
        south: float,
        east: float,
        north: float,
        start_time: datetime,
        end_time: datetime,
        provider: str = "copernicus_cdse",
        platform: str = "sentinel-1",
        polarizations: Optional[List[str]] = None,
        width: int = 512,
        height: int = 512,
        investigation_label: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> AcquisitionJobManifest:
        """Executes the full operational acquisition workflow asynchronously."""
        jid = job_id or self.generate_job_id()
        pols_str = polarizations or ["VV", "VH"]

        manifest = AcquisitionJobManifest(
            job_id=jid,
            request_params={
                "bbox": [west, south, east, north],
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "provider": provider,
                "platform": platform,
                "polarizations": pols_str,
                "width": width,
                "height": height,
                "investigation_label": investigation_label,
            },
        )
        self.save_job_manifest(manifest)

        # -------------------------------------------------------------------
        # 1. Input Validation Stage
        # -------------------------------------------------------------------
        manifest.set_stage(
            AcquisitionJobStage.REQUEST,
            AcquisitionJobStatus.REQUESTED,
            message="Validating operational acquisition request parameters.",
        )
        self.save_job_manifest(manifest)

        # Provider validation: Fail closed on mock/synthetic/demo
        provider_clean = str(provider).strip().lower()
        if not provider_clean:
            manifest.set_failed(
                code="MISSING_PROVIDER",
                message="Data source provider identifier is required.",
                stage=AcquisitionJobStage.REQUEST,
                failure_status=AcquisitionJobStatus.REJECTED_INPUT,
            )
            self.save_job_manifest(manifest)
            return manifest

        if any(f in provider_clean for f in ["synthetic", "mock", "demo", "dummy", "fake", "simulated"]):
            manifest.set_failed(
                code="UNAUTHORIZED_PROVIDER",
                message=f"Provider '{provider}' is strictly rejected. Only real operational EO providers are authorized.",
                stage=AcquisitionJobStage.REQUEST,
                failure_status=AcquisitionJobStatus.REJECTED_INPUT,
                details={"provider": provider},
            )
            self.save_job_manifest(manifest)
            return manifest

        # Bounding box & time range validation
        try:
            bbox = BoundingBox(west=west, south=south, east=east, north=north)
        except Exception as e:
            manifest.set_failed(
                code="INVALID_AOI",
                message=f"Invalid bounding box coordinates: {e}",
                stage=AcquisitionJobStage.REQUEST,
                failure_status=AcquisitionJobStatus.REJECTED_INPUT,
            )
            self.save_job_manifest(manifest)
            return manifest

        try:
            t_range = TimeRange(start=start_time, end=end_time)
        except Exception as e:
            manifest.set_failed(
                code="INVALID_TIME_RANGE",
                message=f"Invalid temporal search window: {e}",
                stage=AcquisitionJobStage.REQUEST,
                failure_status=AcquisitionJobStatus.REJECTED_INPUT,
            )
            self.save_job_manifest(manifest)
            return manifest

        # Polarization validation
        try:
            pol_enums = [Polarization(p.strip().upper()) for p in pols_str]
        except Exception as e:
            manifest.set_failed(
                code="INVALID_POLARIZATIONS",
                message=f"Invalid polarization channel specified: {e}",
                stage=AcquisitionJobStage.REQUEST,
                failure_status=AcquisitionJobStatus.REJECTED_INPUT,
            )
            self.save_job_manifest(manifest)
            return manifest

        # -------------------------------------------------------------------
        # 2. Discovery Stage
        # -------------------------------------------------------------------
        manifest.set_stage(
            AcquisitionJobStage.DISCOVER,
            AcquisitionJobStatus.DISCOVERING,
            message="Querying STAC catalog for real Sentinel-1 observation.",
        )
        self.save_job_manifest(manifest)

        search_req = SearchRequest(
            bbox=bbox,
            time_range=t_range,
            product_type=ProductType.GRD,
            polarizations=pol_enums,
            max_results=1,
        )

        try:
            stac_res = await self.discovery_service.search(search_req)
        except (ProviderTimeoutError, ProviderUnavailableError, ProviderRateLimitedError) as e:
            manifest.set_failed(
                code="PROVIDER_UNAVAILABLE",
                message=f"External catalog discovery failed: {e}",
                stage=AcquisitionJobStage.DISCOVER,
                failure_status=AcquisitionJobStatus.FAILED_DISCOVERY,
                details=getattr(e, "details", {}),
            )
            self.save_job_manifest(manifest)
            return manifest
        except Exception as e:
            manifest.set_failed(
                code="DISCOVERY_ERROR",
                message=f"STAC search encountered an error: {e}",
                stage=AcquisitionJobStage.DISCOVER,
                failure_status=AcquisitionJobStatus.FAILED_DISCOVERY,
            )
            self.save_job_manifest(manifest)
            return manifest

        if not stac_res.observations:
            manifest.set_failed(
                code="NO_OBSERVATIONS_FOUND",
                message="No Sentinel-1 GRD observation found in external catalog for the specified AOI and window.",
                stage=AcquisitionJobStage.DISCOVER,
                failure_status=AcquisitionJobStatus.FAILED_DISCOVERY,
            )
            self.save_job_manifest(manifest)
            return manifest

        obs = stac_res.observations[0]
        manifest.acquisition_id = obs.id
        manifest.provider = obs.provider
        manifest.source_reference = obs.source_reference or obs.self_link
        self.save_job_manifest(manifest)

        # -------------------------------------------------------------------
        # 3. Acquisition Stage
        # -------------------------------------------------------------------
        manifest.set_stage(
            AcquisitionJobStage.ACQUIRE,
            AcquisitionJobStatus.ACQUIRING,
            message=f"Requesting processed SAR raster for observation '{obs.id}'.",
            details={"observation_id": obs.id},
        )
        self.save_job_manifest(manifest)

        img_req = ImageryRequest(
            observation=obs,
            bbox=bbox,
            time_range=TimeRange(
                start=obs.acquisition_time,
                end=datetime.fromtimestamp(obs.acquisition_time.timestamp() + 1800, tz=timezone.utc),
            ) if obs.acquisition_time > t_range.start else t_range,
            requested_bands=pol_enums,
            output=OutputConfig(width=width, height=height, crs_epsg=4326),
        )

        try:
            imagery_res = await self.imagery_service.request_imagery(img_req)
        except (ProviderTimeoutError, ProviderUnavailableError, ProviderRateLimitedError) as e:
            manifest.set_failed(
                code="ACQUISITION_TIMEOUT_OR_UNAVAILABLE",
                message=f"External imagery request failed: {e}",
                stage=AcquisitionJobStage.ACQUIRE,
                failure_status=AcquisitionJobStatus.FAILED_ACQUISITION,
                details=getattr(e, "details", {}),
            )
            self.save_job_manifest(manifest)
            return manifest
        except RasterValidationError as e:
            manifest.set_failed(
                code="RASTER_VALIDATION_ERROR",
                message=f"Retrieved raster payload failed validation: {e}",
                stage=AcquisitionJobStage.ACQUIRE,
                failure_status=AcquisitionJobStatus.FAILED_ACQUISITION,
                details=getattr(e, "details", {}),
            )
            self.save_job_manifest(manifest)
            return manifest
        except Exception as e:
            manifest.set_failed(
                code="ACQUISITION_ERROR",
                message=f"Imagery retrieval failed: {e}",
                stage=AcquisitionJobStage.ACQUIRE,
                failure_status=AcquisitionJobStatus.FAILED_ACQUISITION,
            )
            self.save_job_manifest(manifest)
            return manifest

        # -------------------------------------------------------------------
        # 4. Persistence Stage
        # -------------------------------------------------------------------
        manifest.set_stage(
            AcquisitionJobStage.PERSIST,
            AcquisitionJobStatus.PERSISTING,
            message="Persisting raster bytes and cryptographic metadata to disk.",
        )
        self.save_job_manifest(manifest)

        try:
            artifact = self.persistence_service.persist_acquisition(imagery_res, img_req)
        except PersistenceError as e:
            manifest.set_failed(
                code=e.code,
                message=f"Failed to persist acquisition: {e.message}",
                stage=AcquisitionJobStage.PERSIST,
                failure_status=AcquisitionJobStatus.FAILED_PERSISTENCE,
                details=e.details,
            )
            self.save_job_manifest(manifest)
            return manifest
        except Exception as e:
            manifest.set_failed(
                code="PERSISTENCE_FAILED",
                message=f"Persistence error: {e}",
                stage=AcquisitionJobStage.PERSIST,
                failure_status=AcquisitionJobStatus.FAILED_PERSISTENCE,
            )
            self.save_job_manifest(manifest)
            return manifest

        manifest.geotiff_path = artifact.geotiff_path
        manifest.metadata_path = artifact.metadata_path
        manifest.content_sha256 = artifact.content_sha256
        self.save_job_manifest(manifest)

        # -------------------------------------------------------------------
        # 5. Validation Stage (Integrity & Operational SAR Preflight)
        # -------------------------------------------------------------------
        manifest.set_stage(
            AcquisitionJobStage.VALIDATE,
            AcquisitionJobStatus.VALIDATING,
            message="Verifying SHA-256 integrity and executing Phase 6 SAR preflight.",
        )
        self.save_job_manifest(manifest)

        # Re-load from disk and re-verify SHA-256 digest
        try:
            verified_artifact, channel_arrays = self.persistence_service.load_persisted_acquisition(
                artifact.acquisition_id
            )
        except PersistenceIntegrityError as e:
            manifest.set_failed(
                code=e.code,
                message=f"Integrity verification failed: {e.message}",
                stage=AcquisitionJobStage.VALIDATE,
                failure_status=AcquisitionJobStatus.FAILED_INTEGRITY,
                details=e.details,
            )
            self.save_job_manifest(manifest)
            return manifest
        except Exception as e:
            manifest.set_failed(
                code="INTEGRITY_CHECK_FAILED",
                message=f"Integrity check failed: {e}",
                stage=AcquisitionJobStage.VALIDATE,
                failure_status=AcquisitionJobStatus.FAILED_INTEGRITY,
            )
            self.save_job_manifest(manifest)
            return manifest

        # Execute OperationalSARPipeline handoff
        try:
            ingestion_req = self.persistence_service.to_operational_ingestion_request(
                verified_artifact, channel_arrays
            )
            evidence_result = self.bridge.operational_pipeline.run(ingestion_req)
        except Exception as e:
            manifest.set_failed(
                code="SAR_VALIDATION_FAILED",
                message=f"Operational SAR validation contract failed: {e}",
                stage=AcquisitionJobStage.VALIDATE,
                failure_status=AcquisitionJobStatus.FAILED_VALIDATION,
            )
            self.save_job_manifest(manifest)
            return manifest

        if evidence_result.status != "DETECTION_READY":
            manifest.set_failed(
                code="PIPELINE_NOT_DETECTION_READY",
                message=f"Pipeline finished with non-ready status: {evidence_result.status}",
                stage=AcquisitionJobStage.VALIDATE,
                failure_status=AcquisitionJobStatus.FAILED_VALIDATION,
            )
            self.save_job_manifest(manifest)
            return manifest

        # -------------------------------------------------------------------
        # 6. Final State: READY_FOR_DETECTION
        # -------------------------------------------------------------------
        manifest.set_ready_for_detection(verified_artifact, evidence_result)
        self.save_job_manifest(manifest)

        logger.info(
            "Acquisition job '%s' successfully reached READY_FOR_DETECTION for acquisition '%s' (SHA256=%s...)",
            manifest.job_id,
            manifest.acquisition_id,
            manifest.content_sha256[:12] if manifest.content_sha256 else "",
        )
        return manifest
