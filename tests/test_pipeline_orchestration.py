"""Comprehensive Test Suite for Pipeline Orchestration V1.

Tests JobManifest, JobStore, PipelineOrchestrator, stage lifecycles,
artifact registration, error recording, and PHYSICAL mode fail-closed behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import pytest

from ocean_sentinel.orchestration.jobs import (
    ArtifactRecord,
    JobErrorRecord,
    JobManifest,
    JobMode,
    JobStatus,
    JobStore,
    PipelineStage,
    PipelineType,
    StageExecutionStatus,
    StageRecord,
)
from ocean_sentinel.orchestration.pipeline import PipelineOrchestrator


@pytest.fixture
def temp_job_store(tmp_path: Path) -> JobStore:
    """Provide an isolated temporary JobStore."""
    return JobStore(base_dir=tmp_path / "jobs")


@pytest.fixture
def temp_orchestrator(temp_job_store: JobStore) -> PipelineOrchestrator:
    """Provide a PipelineOrchestrator using the isolated JobStore."""
    return PipelineOrchestrator(job_store=temp_job_store)


# ---------------------------------------------------------------------------
# JobStore & Manifest Tests
# ---------------------------------------------------------------------------


def test_job_store_lifecycle(temp_job_store: JobStore):
    """Verify job manifest creation, serialization, atomic persistence, and retrieval."""
    manifest = temp_job_store.create_job(
        mode=JobMode.DEMO,
        pipeline_type=PipelineType.DEMO_FUSION,
        requested_config={"test_key": "test_val"},
    )
    assert manifest.job_id.startswith("job_")
    assert manifest.status == JobStatus.CREATED.value
    assert manifest.mode == JobMode.DEMO.value
    assert manifest.pipeline_type == PipelineType.DEMO_FUSION.value

    # Manifest file exists on disk
    manifest_path = temp_job_store.get_manifest_path(manifest.job_id)
    assert manifest_path.is_file()

    # Retrieve manifest from disk
    loaded = temp_job_store.get_manifest(manifest.job_id)
    assert loaded is not None
    assert loaded.job_id == manifest.job_id
    assert loaded.requested_config["test_key"] == "test_val"

    # Mutate and save
    loaded.set_stage_status(PipelineStage.VALIDATE, StageExecutionStatus.COMPLETED, message="OK")
    temp_job_store.save_manifest(loaded)

    reloaded = temp_job_store.get_manifest(manifest.job_id)
    assert reloaded is not None
    assert PipelineStage.VALIDATE.value in reloaded.stage_status
    assert reloaded.stage_status[PipelineStage.VALIDATE.value]["status"] == StageExecutionStatus.COMPLETED.value


def test_job_store_list_jobs(temp_job_store: JobStore):
    """Verify list_jobs returns sorted manifests with limit."""
    j1 = temp_job_store.create_job(JobMode.DEMO, PipelineType.DEMO_FUSION)
    j2 = temp_job_store.create_job(JobMode.DEMO, PipelineType.ARTIFACT_FUSION)

    jobs = temp_job_store.list_jobs(limit=10)
    assert len(jobs) == 2
    ids = [j["job_id"] for j in jobs]
    assert j1.job_id in ids
    assert j2.job_id in ids


def test_job_store_nonexistent_manifest(temp_job_store: JobStore):
    """Verify get_manifest returns None for nonexistent jobs."""
    assert temp_job_store.get_manifest("job_does_not_exist") is None


# ---------------------------------------------------------------------------
# Orchestrator Workflow Tests
# ---------------------------------------------------------------------------


def test_orchestrator_demo_fusion_success(temp_orchestrator: PipelineOrchestrator):
    """Verify complete end-to-end DEMO_FUSION execution."""
    manifest = temp_orchestrator.run_job(
        mode=JobMode.DEMO,
        pipeline_type=PipelineType.DEMO_FUSION,
        spatial_tolerance_m=5000.0,
        temporal_tolerance_hours=2.0,
    )

    assert manifest.status == JobStatus.SUCCEEDED.value
    assert manifest.started_at is not None
    assert manifest.finished_at is not None

    # Stages executed
    assert manifest.stage_status[PipelineStage.VALIDATE.value]["status"] == StageExecutionStatus.COMPLETED.value
    assert manifest.stage_status[PipelineStage.INGEST.value]["status"] == StageExecutionStatus.COMPLETED.value
    assert manifest.stage_status[PipelineStage.FUSION.value]["status"] == StageExecutionStatus.COMPLETED.value
    assert manifest.stage_status[PipelineStage.EXPORT.value]["status"] == StageExecutionStatus.COMPLETED.value

    # Artifacts registered and present on disk
    assert len(manifest.artifacts) == 3
    for art in manifest.artifacts:
        p = Path(art["file_path"])
        assert p.is_file()
        assert p.stat().st_size > 0

    # Result structure verified
    assert manifest.result is not None
    assert manifest.result["multiple_plausible_candidates"] is True
    assert manifest.result["plausible_candidate_count"] >= 2
    assert manifest.result["negative_proof_guard"] == "AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE"


def test_orchestrator_artifact_fusion_success(temp_orchestrator: PipelineOrchestrator):
    """Verify ARTIFACT_FUSION execution with repository artifacts."""
    manifest = temp_orchestrator.run_job(
        mode=JobMode.DEMO,
        pipeline_type=PipelineType.ARTIFACT_FUSION,
        input_artifacts={
            "temporal_geojson": "outputs/temporal/00007_to_01339_temporal_events.geojson",
            "drift_geojson": "outputs/origin_drift/trujillo_00007_01339.geojson",
            "ais_summary": "outputs/ais/trujillo_00007_01339_summary.json",
        },
    )

    assert manifest.status == JobStatus.SUCCEEDED.value
    assert manifest.result is not None
    assert manifest.result["total_evidence_items"] == 33
    assert manifest.result["multiple_plausible_candidates"] is True
    assert len(manifest.artifacts) == 3


def test_orchestrator_physical_mode_fails_closed(temp_orchestrator: PipelineOrchestrator):
    """Verify PHYSICAL mode strictly fails closed with PROVENANCE_REJECTION."""
    manifest = temp_orchestrator.run_job(
        mode=JobMode.PHYSICAL,
        pipeline_type=PipelineType.PHYSICAL,
    )

    assert manifest.status == JobStatus.BLOCKED_PROVENANCE.value
    assert manifest.error is not None
    assert manifest.error["code"] == "PROVENANCE_REJECTION"
    assert "BLOCKED — AWAITING_OPERATIONAL_SOURCE" in manifest.error["message"]
    # Stage VALIDATE should be BLOCKED
    assert manifest.stage_status[PipelineStage.VALIDATE.value]["status"] == StageExecutionStatus.BLOCKED.value
    # No result produced
    assert manifest.result is None


def test_orchestrator_invalid_spatial_tolerance(temp_orchestrator: PipelineOrchestrator):
    """Verify non-positive spatial tolerance fails with INVALID_INPUT."""
    manifest = temp_orchestrator.run_job(
        mode=JobMode.DEMO,
        pipeline_type=PipelineType.DEMO_FUSION,
        spatial_tolerance_m=-50.0,
    )

    assert manifest.status == JobStatus.FAILED.value
    assert manifest.error is not None
    assert manifest.error["code"] == "INVALID_INPUT"
    assert "spatial_tolerance_m" in manifest.error["message"]


def test_orchestrator_invalid_temporal_tolerance(temp_orchestrator: PipelineOrchestrator):
    """Verify non-positive temporal tolerance fails with INVALID_INPUT."""
    manifest = temp_orchestrator.run_job(
        mode=JobMode.DEMO,
        pipeline_type=PipelineType.DEMO_FUSION,
        temporal_tolerance_hours=0.0,
    )

    assert manifest.status == JobStatus.FAILED.value
    assert manifest.error is not None
    assert manifest.error["code"] == "INVALID_INPUT"
    assert "temporal_tolerance_hours" in manifest.error["message"]


def test_orchestrator_path_traversal_rejection(temp_orchestrator: PipelineOrchestrator):
    """Verify path traversal references are rejected."""
    manifest = temp_orchestrator.run_job(
        mode=JobMode.DEMO,
        pipeline_type=PipelineType.ARTIFACT_FUSION,
        input_artifacts={"drift_geojson": "../../etc/shadow"},
    )

    assert manifest.status == JobStatus.FAILED.value
    assert manifest.error is not None
    assert manifest.error["code"] == "INVALID_INPUT"
    assert "Path traversal rejected" in manifest.error["message"]


def test_orchestrator_missing_artifacts_in_artifact_fusion(temp_orchestrator: PipelineOrchestrator):
    """Verify missing required artifact files fail cleanly with ARTIFACT_NOT_FOUND."""
    manifest = temp_orchestrator.run_job(
        mode=JobMode.DEMO,
        pipeline_type=PipelineType.ARTIFACT_FUSION,
        input_artifacts={
            "detection_geojson": "nonexistent/path/det.geojson",
            "temporal_geojson": "nonexistent/path/temp.geojson",
            "drift_geojson": "nonexistent/path/drift.geojson",
            "ais_summary": "nonexistent/path/ais.json",
        },
    )

    assert manifest.status == JobStatus.FAILED.value
    assert manifest.error is not None
    assert manifest.error["code"] == "ARTIFACT_NOT_FOUND"


def test_orchestrator_stage_duration_tracking(temp_orchestrator: PipelineOrchestrator):
    """Verify duration_seconds is computed for completed stages."""
    manifest = temp_orchestrator.run_job(
        mode=JobMode.DEMO,
        pipeline_type=PipelineType.DEMO_FUSION,
    )
    for st_name in [PipelineStage.VALIDATE.value, PipelineStage.INGEST.value, PipelineStage.FUSION.value, PipelineStage.EXPORT.value]:
        rec = manifest.stage_status.get(st_name)
        assert rec is not None
        assert rec["duration_seconds"] is not None
        assert rec["duration_seconds"] >= 0.0


def test_repeated_demo_determinism(temp_orchestrator: PipelineOrchestrator):
    """Verify running DEMO_FUSION twice produces identical scientific results."""
    m1 = temp_orchestrator.run_job(JobMode.DEMO, PipelineType.DEMO_FUSION)
    m2 = temp_orchestrator.run_job(JobMode.DEMO, PipelineType.DEMO_FUSION)

    r1 = m1.result
    r2 = m2.result
    assert r1 is not None and r2 is not None
    assert r1["total_evidence_items"] == r2["total_evidence_items"]
    assert r1["total_candidate_hypotheses"] == r2["total_candidate_hypotheses"]
    assert r1["plausible_candidate_count"] == r2["plausible_candidate_count"]
