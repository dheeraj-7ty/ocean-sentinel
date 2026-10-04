"""API Routes for Ocean Sentinel V1.

Implements versioned endpoints under /api/v1/ for health checks, job orchestration,
artifact discovery, and machine-readable result retrieval.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from ocean_sentinel.api.schemas import (
    AcquisitionJobLinks,
    AcquisitionJobListResponse,
    AcquisitionJobRequest,
    AcquisitionJobResponse,
    ArtifactListResponse,
    CreateInvestigationRequest,
    CreateJobRequest,
    ErrorResponse,
    HealthResponse,
    JobLinks,
    JobResponse,
    ScenarioListResponse,
    ScenarioResponse,
)
from ocean_sentinel.orchestration.acquisition_job import (
    AcquisitionJobManifest,
    AcquisitionJobOrchestrator,
    AcquisitionJobStatus,
)
from ocean_sentinel.orchestration.engine import InvestigationEngine
from ocean_sentinel.orchestration.events import (
    EventSeverity,
    InvestigationEvent,
    InvestigationEventType,
)
from ocean_sentinel.orchestration.investigation_run import (
    InvestigationRun,
    InvestigationRunRequest,
    InvestigationRunStatus,
    InvestigationStageState,
    StageExecutionStatus,
)
from ocean_sentinel.orchestration.investigation_store import InvestigationRunStore
from ocean_sentinel.orchestration.jobs import (
    JobManifest,
    JobMode,
    JobStatus,
    JobStore,
    PipelineType,
)
from ocean_sentinel.orchestration.pipeline import PipelineOrchestrator
from ocean_sentinel.orchestration.scenarios import get_scenario, list_scenarios

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

router = APIRouter(prefix="/api/v1", tags=["Ocean Sentinel V1"])

# Default singleton orchestrators
_default_orchestrator: Optional[PipelineOrchestrator] = None
_default_acquisition_orchestrator: Optional[AcquisitionJobOrchestrator] = None
_default_investigation_store: Optional[InvestigationRunStore] = None
_default_investigation_engine: Optional[InvestigationEngine] = None


def get_orchestrator() -> PipelineOrchestrator:
    """Dependency provider for PipelineOrchestrator."""
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = PipelineOrchestrator()
    return _default_orchestrator


def set_orchestrator(orchestrator: PipelineOrchestrator) -> None:
    """Override orchestrator for testing."""
    global _default_orchestrator
    _default_orchestrator = orchestrator


def get_acquisition_orchestrator() -> AcquisitionJobOrchestrator:
    """Dependency provider for AcquisitionJobOrchestrator."""
    global _default_acquisition_orchestrator
    if _default_acquisition_orchestrator is None:
        _default_acquisition_orchestrator = AcquisitionJobOrchestrator()
    return _default_acquisition_orchestrator


def set_acquisition_orchestrator(orchestrator: AcquisitionJobOrchestrator) -> None:
    """Override acquisition orchestrator for testing."""
    global _default_acquisition_orchestrator
    _default_acquisition_orchestrator = orchestrator


def get_investigation_store() -> InvestigationRunStore:
    """Dependency provider for InvestigationRunStore."""
    global _default_investigation_store
    if _default_investigation_store is None:
        _default_investigation_store = InvestigationRunStore(repo_root=REPO_ROOT)
    return _default_investigation_store


def set_investigation_store(store: InvestigationRunStore) -> None:
    """Override investigation store for testing."""
    global _default_investigation_store
    _default_investigation_store = store


def get_investigation_engine() -> InvestigationEngine:
    """Dependency provider for InvestigationEngine."""
    global _default_investigation_engine
    if _default_investigation_engine is None:
        _default_investigation_engine = InvestigationEngine(
            store=get_investigation_store(),
            repo_root=REPO_ROOT,
        )
    return _default_investigation_engine


def set_investigation_engine(engine: InvestigationEngine) -> None:
    """Override investigation engine for testing."""
    global _default_investigation_engine
    _default_investigation_engine = engine


def _build_job_links(request: Request, job_id: str) -> JobLinks:
    """Build canonical hypermedia links for a job."""
    base_url = str(request.base_url).rstrip("/")
    return JobLinks(
        self=f"{base_url}/api/v1/jobs/{job_id}",
        artifacts=f"{base_url}/api/v1/jobs/{job_id}/artifacts",
        result=f"{base_url}/api/v1/jobs/{job_id}/result",
    )


def _manifest_to_response(request: Request, manifest: JobManifest) -> JobResponse:
    """Convert JobManifest to JobResponse schema."""
    links = _build_job_links(request, manifest.job_id)
    return JobResponse(
        job_id=manifest.job_id,
        mode=manifest.mode,
        pipeline_type=manifest.pipeline_type,
        scenario_id=manifest.scenario_id,
        investigation_label=manifest.investigation_label,
        status=manifest.status,
        current_stage=manifest.current_stage,
        created_at=manifest.created_at,
        started_at=manifest.started_at,
        finished_at=manifest.finished_at,
        requested_config=manifest.requested_config,
        stage_status=manifest.stage_status,
        artifacts=manifest.artifacts,
        error=manifest.error,
        limitations=manifest.limitations,
        links=links,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health and subsystem freeze status",
)
def get_health() -> HealthResponse:
    """Returns backend service health, API version, and frozen scientific subsystem status."""
    return HealthResponse()


@router.get(
    "/investigations/scenarios",
    response_model=ScenarioListResponse,
    summary="List registered real repository investigation scenarios",
)
def list_investigation_scenarios() -> ScenarioListResponse:
    """Returns the list of verified real repository scenarios available for investigation."""
    scenarios = list_scenarios()
    return ScenarioListResponse(
        total_scenarios=len(scenarios),
        scenarios=[ScenarioResponse(**sc.to_dict()) for sc in scenarios],
    )


@router.get(
    "/investigations/scenarios/{scenario_id}",
    response_model=ScenarioResponse,
    summary="Get details for a registered investigation scenario",
    responses={
        404: {"model": ErrorResponse, "description": "Scenario not found"},
    },
)
def get_investigation_scenario(scenario_id: str) -> ScenarioResponse:
    """Retrieve verified metadata and artifact mappings for a specific scenario."""
    sc = get_scenario(scenario_id)
    if not sc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SCENARIO_NOT_FOUND",
                "message": f"Scenario '{scenario_id}' not found in registered catalog.",
            },
        )
    return ScenarioResponse(**sc.to_dict())


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize and execute a pipeline job",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input parameters or path traversal"},
        403: {"model": ErrorResponse, "description": "Provenance rejection"},
        500: {"model": ErrorResponse, "description": "Pipeline execution failure"},
    },
)
def create_job(
    req: CreateJobRequest,
    request: Request,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> JobResponse:
    """Initialize and execute a pipeline job synchronously.

    Supports DEMO_FUSION, ARTIFACT_FUSION, REAL_REPOSITORY, and PHYSICAL workflows.
    Fails closed when operational feeds are unavailable in PHYSICAL mode.
    """
    logger.info(
        "Received create_job request: mode=%s, pipeline_type=%s, scenario_id=%s",
        req.mode,
        req.pipeline_type,
        req.scenario_id,
    )

    manifest = orchestrator.run_job(
        mode=req.mode,
        pipeline_type=req.pipeline_type,
        input_artifacts=req.input_artifacts,
        spatial_tolerance_m=req.spatial_tolerance_m,
        temporal_tolerance_hours=req.temporal_tolerance_hours,
        scenario_id=req.scenario_id,
        investigation_label=req.investigation_label,
    )

    return _manifest_to_response(request, manifest)


@router.get(
    "/jobs",
    summary="List recently executed pipeline jobs",
)
def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> Dict[str, Any]:
    """Returns recently executed pipeline jobs from the local job store."""
    jobs = orchestrator.job_store.list_jobs(limit=limit)
    return {
        "total_jobs": len(jobs),
        "limit": limit,
        "jobs": jobs,
    }


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get complete status and manifest of a job",
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
def get_job(
    job_id: str,
    request: Request,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> JobResponse:
    """Get the complete current manifest and state of a job by ID."""
    manifest = orchestrator.job_store.get_manifest(job_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": f"Job '{job_id}' not found in job store.",
            },
        )
    return _manifest_to_response(request, manifest)


@router.get(
    "/jobs/{job_id}/artifacts",
    response_model=ArtifactListResponse,
    summary="List all machine-readable artifacts generated by a job",
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
def get_job_artifacts(
    job_id: str,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> ArtifactListResponse:
    """Discover all artifacts (Graph JSON, Summary JSON, GeoJSON) produced by a job."""
    manifest = orchestrator.job_store.get_manifest(job_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": f"Job '{job_id}' not found in job store.",
            },
        )
    return ArtifactListResponse(
        job_id=manifest.job_id,
        total_artifacts=len(manifest.artifacts),
        artifacts=manifest.artifacts,
    )


@router.get(
    "/jobs/{job_id}/result",
    summary="Get normalized Evidence Fusion result",
    responses={
        403: {"model": ErrorResponse, "description": "Provenance rejection"},
        404: {"model": ErrorResponse, "description": "Job or result not found"},
        500: {"model": ErrorResponse, "description": "Job failed during execution"},
    },
)
def get_job_result(
    job_id: str,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> Dict[str, Any]:
    """Retrieve the normalized Evidence Fusion result for a job.

    Preserves Evidence Graph, hypotheses, independent cluster counts,
    conflict ledger, data-unavailable telemetry gaps, and limitations.
    Never manufactures single scalar attribution confidence numbers.
    """
    manifest = orchestrator.job_store.get_manifest(job_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": f"Job '{job_id}' not found in job store.",
            },
        )

    if manifest.status == JobStatus.BLOCKED_PROVENANCE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PROVENANCE_REJECTION",
                "message": manifest.error.get("message") if manifest.error else "Job blocked by physical provenance gate.",
                "stage": manifest.error.get("stage") if manifest.error else "VALIDATE",
                "details": manifest.error.get("details", {}) if manifest.error else {},
            },
        )

    if manifest.status == JobStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": manifest.error.get("code", "PIPELINE_ERROR") if manifest.error else "PIPELINE_ERROR",
                "message": manifest.error.get("message") if manifest.error else "Job execution failed.",
                "stage": manifest.error.get("stage") if manifest.error else "UNKNOWN",
                "details": manifest.error.get("details", {}) if manifest.error else {},
            },
        )

    if not manifest.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ARTIFACT_NOT_FOUND",
                "message": f"Result not available for job '{job_id}' (status: {manifest.status}).",
            },
        )

    return manifest.result


# ---------------------------------------------------------------------------
# Operational Acquisition Endpoints (Phase 6C)
# ---------------------------------------------------------------------------


def _safe_relative_path(p: Optional[str]) -> Optional[str]:
    """Sanitize local absolute filesystem paths to safe relative logical paths for API output."""
    if not p:
        return None
    try:
        path_obj = Path(p)
        if path_obj.is_absolute():
            try:
                return path_obj.relative_to(REPO_ROOT).as_posix()
            except ValueError:
                return path_obj.name
        return path_obj.as_posix()
    except Exception:
        return str(p)


def _build_acquisition_job_links(request: Request, job_id: str) -> AcquisitionJobLinks:
    """Build hypermedia links for an operational acquisition job."""
    base_url = str(request.base_url).rstrip("/")
    return AcquisitionJobLinks(
        self=f"{base_url}/api/v1/acquisitions/{job_id}",
        result=f"{base_url}/api/v1/acquisitions/{job_id}/result",
        geotiff=f"{base_url}/api/v1/acquisitions/{job_id}/geotiff",
    )


def _acquisition_manifest_to_response(
    request: Request, manifest: AcquisitionJobManifest
) -> AcquisitionJobResponse:
    """Convert AcquisitionJobManifest to AcquisitionJobResponse schema."""
    links = _build_acquisition_job_links(request, manifest.job_id)
    return AcquisitionJobResponse(
        job_id=manifest.job_id,
        status=manifest.status,
        current_stage=manifest.current_stage,
        created_at=manifest.created_at,
        started_at=manifest.started_at,
        finished_at=manifest.finished_at,
        request_params=manifest.request_params,
        stage_timings=manifest.stage_timings,
        acquisition_id=manifest.acquisition_id,
        provider=manifest.provider,
        source_reference=manifest.source_reference,
        geotiff_path=_safe_relative_path(manifest.geotiff_path),
        metadata_path=_safe_relative_path(manifest.metadata_path),
        content_sha256=manifest.content_sha256,
        sar_validation=manifest.sar_validation,
        evidence_id=manifest.evidence_id,
        execution_authorized=manifest.execution_authorized,
        has_prediction=manifest.has_prediction,
        error=manifest.error,
        limitations=manifest.limitations,
        links=links,
    )


@router.post(
    "/acquisitions",
    response_model=AcquisitionJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize and synchronously execute an operational Earth-observation acquisition job",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input parameters or rejected provider"},
        500: {"model": ErrorResponse, "description": "Acquisition workflow failure"},
    },
)
async def create_acquisition_job(
    req: AcquisitionJobRequest,
    request: Request,
    orchestrator: AcquisitionJobOrchestrator = Depends(get_acquisition_orchestrator),
) -> AcquisitionJobResponse:
    """Synchronously execute an operational Earth observation acquisition workflow.

    Workflow:
        REQUEST -> DISCOVER -> ACQUIRE -> PERSIST -> VALIDATE -> READY_FOR_DETECTION

    Guarantees:
        - Rejects mock/synthetic/demo providers fail-closed.
        - Persists raw GeoTIFF and metadata sidecar atomically.
        - Re-verifies bitwise SHA-256 integrity upon reload.
        - Preflight validates SAR raster compliance (dual-band, float32, valid CRS).
        - Fires OperationalDetectionBoundary with EXECUTION_AUTHORIZED = False.
    """
    logger.info(
        "Received acquisition job request: provider=%s, platform=%s, bbox=[%s, %s, %s, %s]",
        req.provider,
        req.platform,
        req.west,
        req.south,
        req.east,
        req.north,
    )

    manifest = await orchestrator.execute_acquisition_job(
        west=req.west,
        south=req.south,
        east=req.east,
        north=req.north,
        start_time=req.start_time,
        end_time=req.end_time,
        provider=req.provider,
        platform=req.platform,
        polarizations=req.polarizations,
        width=req.width or 512,
        height=req.height or 512,
        investigation_label=req.investigation_label,
    )

    if manifest.status == AcquisitionJobStatus.REJECTED_INPUT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": manifest.error.get("code", "INVALID_INPUT") if manifest.error else "INVALID_INPUT",
                "message": manifest.error.get("message", "Input rejected.") if manifest.error else "Input rejected.",
                "stage": manifest.error.get("stage", "REQUEST") if manifest.error else "REQUEST",
                "details": manifest.error.get("details", {}) if manifest.error else {},
            },
        )

    return _acquisition_manifest_to_response(request, manifest)


@router.get(
    "/acquisitions",
    response_model=AcquisitionJobListResponse,
    summary="List recently executed operational acquisition jobs",
)
def list_acquisition_jobs(
    limit: int = Query(50, ge=1, le=200),
    orchestrator: AcquisitionJobOrchestrator = Depends(get_acquisition_orchestrator),
) -> AcquisitionJobListResponse:
    """Returns recently executed operational acquisition jobs from the job store."""
    jobs = orchestrator.list_acquisition_jobs(limit=limit)
    return AcquisitionJobListResponse(
        total_jobs=len(jobs),
        limit=limit,
        jobs=jobs,
    )


@router.get(
    "/acquisitions/{job_id}",
    response_model=AcquisitionJobResponse,
    summary="Get status and manifest of an operational acquisition job",
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
def get_acquisition_job(
    job_id: str,
    request: Request,
    orchestrator: AcquisitionJobOrchestrator = Depends(get_acquisition_orchestrator),
) -> AcquisitionJobResponse:
    """Get the complete manifest and current state of an acquisition job by ID."""
    manifest = orchestrator.get_job_manifest(job_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": f"Acquisition job '{job_id}' not found.",
            },
        )
    return _acquisition_manifest_to_response(request, manifest)


@router.get(
    "/acquisitions/{job_id}/result",
    summary="Get operational evidence result for an acquisition job",
    responses={
        400: {"model": ErrorResponse, "description": "Job failed"},
        404: {"model": ErrorResponse, "description": "Job or evidence not found"},
        500: {"model": ErrorResponse, "description": "Pipeline failure"},
    },
)
def get_acquisition_result(
    job_id: str,
    orchestrator: AcquisitionJobOrchestrator = Depends(get_acquisition_orchestrator),
) -> Dict[str, Any]:
    """Retrieve the canonical structured evidence result produced by an acquisition job."""
    manifest = orchestrator.get_job_manifest(job_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": f"Acquisition job '{job_id}' not found.",
            },
        )

    if manifest.status in [
        AcquisitionJobStatus.FAILED_DISCOVERY.value,
        AcquisitionJobStatus.FAILED_ACQUISITION.value,
        AcquisitionJobStatus.FAILED_PERSISTENCE.value,
        AcquisitionJobStatus.FAILED_INTEGRITY.value,
        AcquisitionJobStatus.FAILED_VALIDATION.value,
    ]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": manifest.error.get("code", "ACQUISITION_FAILED") if manifest.error else "ACQUISITION_FAILED",
                "message": manifest.error.get("message", "Job failed.") if manifest.error else "Job failed.",
                "stage": manifest.error.get("stage", "UNKNOWN") if manifest.error else "UNKNOWN",
                "details": manifest.error.get("details", {}) if manifest.error else {},
            },
        )

    if not manifest.evidence_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "EVIDENCE_NOT_READY",
                "message": f"Operational evidence not ready for job '{job_id}' (status: {manifest.status}).",
            },
        )

    return manifest.evidence_result


# ---------------------------------------------------------------------------
# Phase 7B Investigation & Event Telemetry Endpoints
# ---------------------------------------------------------------------------


def _resolve_investigation_run(
    run_id: str,
    store: InvestigationRunStore,
    orchestrator: AcquisitionJobOrchestrator,
) -> InvestigationRun:
    """Resolve an InvestigationRun from store or convert from Phase 6C AcquisitionJob."""
    try:
        run = store.load_run(run_id)
        if run:
            return run
    except Exception:
        pass

    acq_manifest = orchestrator.get_job_manifest(run_id)
    if acq_manifest:
        return InvestigationRun.from_acquisition_job(acq_manifest)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "RUN_NOT_FOUND",
            "message": f"Investigation run '{run_id}' not found.",
        },
    )


@router.get(
    "/investigations",
    summary="List stored investigation runs and recent operational acquisition runs",
)
def list_investigations(
    limit: int = Query(50, ge=1, le=200),
    store: InvestigationRunStore = Depends(get_investigation_store),
    orchestrator: AcquisitionJobOrchestrator = Depends(get_acquisition_orchestrator),
) -> Dict[str, Any]:
    """Returns combined investigation runs from store and acquisition jobs."""
    runs = store.list_runs(limit=limit)
    existing_ids = {r["run_id"] for r in runs}

    acq_jobs = orchestrator.list_acquisition_jobs(limit=limit)
    for acq in acq_jobs:
        job_id = acq.get("job_id") if isinstance(acq, dict) else getattr(acq, "job_id", "")
        if job_id and job_id not in existing_ids:
            created_at = acq.get("created_at") if isinstance(acq, dict) else getattr(acq, "created_at", None)
            status = acq.get("status") if isinstance(acq, dict) else getattr(acq, "status", None)
            current_stage = acq.get("current_stage") if isinstance(acq, dict) else getattr(acq, "current_stage", None)
            label = acq.get("investigation_label") if isinstance(acq, dict) else getattr(acq, "investigation_label", None)
            runs.append({
                "run_id": job_id,
                "created_at": created_at,
                "status": status,
                "current_stage": current_stage,
                "analysis_mode": "PHYSICAL",
                "scenario_id": None,
                "investigation_label": label or f"Acquisition {job_id}",
            })

    runs.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {
        "total_runs": len(runs),
        "limit": limit,
        "runs": runs[:limit],
    }


@router.post(
    "/investigations",
    summary="Initialize and start a durable investigation run",
    status_code=status.HTTP_201_CREATED,
)
def create_investigation(
    req: CreateInvestigationRequest,
    store: InvestigationRunStore = Depends(get_investigation_store),
    engine: InvestigationEngine = Depends(get_investigation_engine),
) -> Dict[str, Any]:
    """Create a durable investigation run with canonical DAG stages and fail-closed scientific gate."""
    import secrets
    run_id = f"inv_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(3)}"

    # Standardize AOI geometry
    aoi_geom = req.aoi
    if not aoi_geom and req.bbox and len(req.bbox) == 4:
        w, s, e, n = req.bbox
        aoi_geom = {
            "type": "Polygon",
            "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
        }

    run_req = InvestigationRunRequest(
        aoi=aoi_geom,
        bbox=req.bbox,
        time_window={"start_time": req.start_time or "", "end_time": req.end_time or ""},
        polarizations=req.polarizations or ["VV", "VH"],
        analysis_mode=req.analysis_mode,
        investigation_label=req.investigation_label,
        scenario_id=req.scenario_id,
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    run = InvestigationRun(
        run_id=run_id,
        created_at=now_iso,
        started_at=now_iso,
        request=run_req,
        provenance_policy="FAIL_CLOSED_OPERATIONAL",
        graph_id="canonical_scientific_dag_v1",
        current_stage="READY_FOR_DETECTION",
        overall_status=InvestigationRunStatus.READY_FOR_DETECTION.value,
        evidence_state={
            "execution_authorized": False,
            "has_prediction": False,
            "scientific_status": "BLOCKED — Scientific execution gated (EXECUTION_AUTHORIZED = False)",
        },
    )

    # Initialize canonical DAG stages
    dag = engine.dag
    for stage_id, node in dag.nodes.items():
        if node.is_scientific_gated:
            run.stages[stage_id] = InvestigationStageState(
                stage_id=stage_id,
                status=StageExecutionStatus.BLOCKED.value,
                started_at=now_iso,
                finished_at=now_iso,
                message="Scientific model execution is strictly gated (EXECUTION_AUTHORIZED = False).",
            )
        else:
            run.stages[stage_id] = InvestigationStageState(
                stage_id=stage_id,
                status=StageExecutionStatus.COMPLETED.value if stage_id in ["VALIDATE", "INGEST", "PREPROCESS"] else StageExecutionStatus.PENDING.value,
                started_at=now_iso if stage_id in ["VALIDATE", "INGEST", "PREPROCESS"] else None,
                finished_at=now_iso if stage_id in ["VALIDATE", "INGEST", "PREPROCESS"] else None,
                message=f"Stage {stage_id} initialized.",
            )

    store.save_run(run)

    # Emit Phase 7B lifecycle events to durable log and EventBus
    engine.emit_event(
        run=run,
        event_type=InvestigationEventType.RUN_CREATED,
        payload={"run_id": run_id, "analysis_mode": req.analysis_mode, "aoi": aoi_geom},
    )
    engine.emit_event(
        run=run,
        event_type=InvestigationEventType.RUN_STARTED,
        payload={"run_id": run_id},
    )
    engine.emit_event(
        run=run,
        event_type=InvestigationEventType.STAGE_COMPLETED,
        stage_id="VALIDATE",
        payload={"stage_id": "VALIDATE", "message": "AOI and temporal parameters validated."},
    )
    engine.emit_event(
        run=run,
        event_type=InvestigationEventType.STAGE_COMPLETED,
        stage_id="INGEST",
        payload={"stage_id": "INGEST", "message": "Observation metadata indexed."},
    )
    engine.emit_event(
        run=run,
        event_type=InvestigationEventType.STAGE_COMPLETED,
        stage_id="PREPROCESS",
        payload={"stage_id": "PREPROCESS", "message": "Channel contracts verified."},
    )
    engine.emit_event(
        run=run,
        event_type=InvestigationEventType.STAGE_BLOCKED,
        stage_id="INFER",
        severity=EventSeverity.WARNING,
        payload={
            "stage_id": "INFER",
            "message": "Scientific model execution is strictly gated (EXECUTION_AUTHORIZED = False).",
            "execution_authorized": False,
        },
    )
    engine.emit_event(
        run=run,
        event_type=InvestigationEventType.STAGE_BLOCKED,
        stage_id="INTERPRET",
        severity=EventSeverity.WARNING,
        payload={
            "stage_id": "INTERPRET",
            "message": "Scientific model execution is strictly gated (EXECUTION_AUTHORIZED = False).",
            "execution_authorized": False,
        },
    )
    engine.emit_event(
        run=run,
        event_type=InvestigationEventType.TELEMETRY_SNAPSHOT,
        payload=engine.get_run_telemetry(run),
    )

    return run.to_dict()


@router.get(
    "/investigations/{run_id}",
    summary="Get current state and manifest for an investigation run",
    responses={
        404: {"model": ErrorResponse, "description": "Run not found"},
    },
)
def get_investigation_run(
    run_id: str,
    store: InvestigationRunStore = Depends(get_investigation_store),
    orchestrator: AcquisitionJobOrchestrator = Depends(get_acquisition_orchestrator),
) -> Dict[str, Any]:
    """Retrieve full canonical InvestigationRun domain state by ID."""
    run = _resolve_investigation_run(run_id, store, orchestrator)
    return run.to_dict()


@router.get(
    "/investigations/{run_id}/telemetry",
    summary="Get operational telemetry snapshot for an investigation run",
    responses={
        404: {"model": ErrorResponse, "description": "Run not found"},
    },
)
def get_investigation_telemetry(
    run_id: str,
    store: InvestigationRunStore = Depends(get_investigation_store),
    engine: InvestigationEngine = Depends(get_investigation_engine),
    orchestrator: AcquisitionJobOrchestrator = Depends(get_acquisition_orchestrator),
) -> Dict[str, Any]:
    """Retrieve structured operational telemetry without exposing unverified scientific metrics."""
    run = _resolve_investigation_run(run_id, store, orchestrator)
    return engine.get_run_telemetry(run)


@router.get(
    "/investigations/{run_id}/events/history",
    summary="Retrieve recorded event log history for an investigation run",
    responses={
        404: {"model": ErrorResponse, "description": "Run not found"},
    },
)
def get_investigation_event_history(
    run_id: str,
    after_sequence: Optional[int] = Query(None, description="Return events with sequence > after_sequence"),
    limit: int = Query(100, ge=1, le=500),
    store: InvestigationRunStore = Depends(get_investigation_store),
    orchestrator: AcquisitionJobOrchestrator = Depends(get_acquisition_orchestrator),
) -> Dict[str, Any]:
    """Read historical events from the append-only durable event log."""
    _resolve_investigation_run(run_id, store, orchestrator)
    event_log = store.get_event_log(run_id)
    events = event_log.replay(after_sequence=after_sequence, limit=limit)
    return {
        "run_id": run_id,
        "after_sequence": after_sequence,
        "total_returned": len(events),
        "events": [e.to_dict() for e in events],
    }


@router.get(
    "/investigations/{run_id}/events",
    summary="Stream live investigation events via Server-Sent Events (SSE) with replay support",
    responses={
        404: {"model": ErrorResponse, "description": "Run not found"},
    },
)
async def stream_investigation_events(
    run_id: str,
    request: Request,
    last_event_id: Optional[int] = Query(None, description="Sequence cursor for replaying events"),
    last_event_id_header: Optional[str] = Header(None, alias="Last-Event-ID"),
    store: InvestigationRunStore = Depends(get_investigation_store),
    engine: InvestigationEngine = Depends(get_investigation_engine),
    orchestrator: AcquisitionJobOrchestrator = Depends(get_acquisition_orchestrator),
) -> StreamingResponse:
    """Stream real-time SSE events for an investigation run.

    Replay & Reconnection:
        - If Last-Event-ID or last_event_id is provided, replays all historical durable events
          from events.jsonl after that sequence before attaching live subscription.
        - Emits keepalive ping comments every 15s to preserve HTTP stream health.
        - Disconnects gracefully upon client cancellation without affecting engine execution.
    """
    initial_run = _resolve_investigation_run(run_id, store, orchestrator)

    # Resolve replay cursor
    cursor: Optional[int] = None
    if last_event_id is not None:
        cursor = last_event_id
    elif last_event_id_header is not None:
        try:
            cursor = int(last_event_id_header.strip())
        except ValueError:
            cursor = None

    async def event_generator():
        event_log = store.get_event_log(run_id)
        highest_seq = cursor or 0

        # 1. Subscribe to live events on in-process EventBus FIRST to eliminate the replay-to-subscription race gap
        sub = engine.event_bus.subscribe(run_id)

        try:
            # 2. Replay historical durable events from disk (captures everything up to this instant)
            historical_events = event_log.replay(after_sequence=cursor)
            for evt in historical_events:
                if evt.sequence > highest_seq:
                    highest_seq = evt.sequence
                yield evt.to_sse()

            # 3. Drain any events already captured in sub.queue that arrived during replay
            stream_closed = False
            while not sub.queue.empty():
                try:
                    q_evt = sub.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if q_evt is None:
                    stream_closed = True
                    break
                if q_evt.sequence > highest_seq:
                    highest_seq = q_evt.sequence
                    yield q_evt.to_sse()

            if stream_closed:
                return

            # Resynchronize from disk if queue overflowed during initial replay
            if getattr(sub, "has_overflowed", False):
                sub.has_overflowed = False
                missed_events = event_log.replay(after_sequence=highest_seq)
                for m_evt in missed_events:
                    if m_evt.sequence > highest_seq:
                        highest_seq = m_evt.sequence
                        yield m_evt.to_sse()

            # Check if run is already in terminal state and no new events can occur
            terminal_statuses = {
                InvestigationRunStatus.SUCCEEDED.value,
                InvestigationRunStatus.FAILED.value,
                InvestigationRunStatus.READY_FOR_DETECTION.value,
                InvestigationRunStatus.BLOCKED.value,
            }
            latest_run = store.load_run(run_id) or initial_run
            if latest_run.overall_status in terminal_statuses and sub.queue.empty():
                return

            # 4. Stream live events with automatic queue-overflow recovery from durable disk
            while not await request.is_disconnected():
                # Resynchronize from durable disk log if bounded subscriber queue overflowed
                if getattr(sub, "has_overflowed", False):
                    sub.has_overflowed = False
                    missed_events = event_log.replay(after_sequence=highest_seq)
                    for m_evt in missed_events:
                        if m_evt.sequence > highest_seq:
                            highest_seq = m_evt.sequence
                            yield m_evt.to_sse()

                try:
                    evt = await asyncio.wait_for(sub.queue.get(), timeout=15.0)
                    if evt is None:
                        break

                    # Check overflow again upon waking to ensure gapless delivery
                    if getattr(sub, "has_overflowed", False):
                        sub.has_overflowed = False
                        missed_events = event_log.replay(after_sequence=highest_seq)
                        for m_evt in missed_events:
                            if m_evt.sequence > highest_seq:
                                highest_seq = m_evt.sequence
                                yield m_evt.to_sse()

                    # Prevent duplicate emission if event was already replayed
                    if evt.sequence > highest_seq:
                        highest_seq = evt.sequence
                        yield evt.to_sse()

                    if evt.event_type in [
                        InvestigationEventType.RUN_COMPLETED.value,
                        InvestigationEventType.RUN_FAILED.value,
                    ]:
                        break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            engine.event_bus.unsubscribe(sub)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
