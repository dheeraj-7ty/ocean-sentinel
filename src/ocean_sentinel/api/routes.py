"""API Routes for Ocean Sentinel V1.

Implements versioned endpoints under /api/v1/ for health checks, job orchestration,
artifact discovery, and machine-readable result retrieval.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from ocean_sentinel.api.schemas import (
    ArtifactListResponse,
    CreateJobRequest,
    ErrorResponse,
    HealthResponse,
    JobLinks,
    JobResponse,
    ScenarioListResponse,
    ScenarioResponse,
)
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

# Default singleton orchestrator
_default_orchestrator: Optional[PipelineOrchestrator] = None


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
