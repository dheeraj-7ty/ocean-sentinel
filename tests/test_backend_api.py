"""Comprehensive Test Suite for Ocean Sentinel Backend API V1.

Tests FastAPI endpoints under /api/v1/:
- Health endpoint & subsystem status
- Job creation (DEMO_FUSION, ARTIFACT_FUSION, PHYSICAL)
- Input validation & path traversal security hardening
- Error semantics & status codes (400, 403, 404, 422, 500)
- Artifact discovery
- Result retrieval & evidence graph exposure
- Terminology guard & non-attribution boundary
- Job persistence across restart simulation
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from ocean_sentinel.api.app import create_app
from ocean_sentinel.api.routes import set_orchestrator
from ocean_sentinel.orchestration.jobs import (
    JobMode,
    JobStatus,
    JobStore,
    PipelineType,
)
from ocean_sentinel.orchestration.pipeline import PipelineOrchestrator


@pytest.fixture
def test_client(tmp_path: Path) -> TestClient:
    """Provide a TestClient connected to an isolated temporary JobStore."""
    store = JobStore(base_dir=tmp_path / "api_jobs")
    orch = PipelineOrchestrator(job_store=store)
    set_orchestrator(orch)

    app = create_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health & Status
# ---------------------------------------------------------------------------


def test_health_endpoint(test_client: TestClient):
    """1. Health endpoint returns service status, version, and frozen subsystem states."""
    resp = test_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["service"] == "ocean-sentinel-backend"
    assert data["status"] == "healthy"
    assert data["api_version"] == "1.0.0"
    assert data["app_version"] == "0.1.0"

    subsystems = data["frozen_subsystems"]
    assert subsystems["sar_inference"] == "FROZEN"
    assert subsystems["interpretation"] == "FROZEN"
    assert subsystems["temporal_change"] == "FROZEN"
    assert subsystems["drift_origin"] == "FROZEN"
    assert subsystems["ais_correlation"] == "FROZEN"
    assert subsystems["evidence_fusion"] == "FROZEN"

    assert data["mode_info"]["physical_operational_status"] == "BLOCKED — AWAITING_OPERATIONAL_SOURCE"


# ---------------------------------------------------------------------------
# Job Creation & Workflows
# ---------------------------------------------------------------------------


def test_create_demo_job_success(test_client: TestClient):
    """2. Valid DEMO_FUSION job creation returns 201, SUCCEEDED status, and hypermedia links."""
    payload = {
        "mode": "DEMO",
        "pipeline_type": "DEMO_FUSION",
        "spatial_tolerance_m": 5000.0,
        "temporal_tolerance_hours": 2.0,
    }
    resp = test_client.post("/api/v1/jobs", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["job_id"].startswith("job_")
    assert data["status"] == "SUCCEEDED"
    assert data["mode"] == "DEMO"
    assert data["pipeline_type"] == "DEMO_FUSION"

    links = data["links"]
    assert f"/api/v1/jobs/{data['job_id']}" in links["self"]
    assert f"/api/v1/jobs/{data['job_id']}/artifacts" in links["artifacts"]
    assert f"/api/v1/jobs/{data['job_id']}/result" in links["result"]


def test_create_artifact_fusion_job_success(test_client: TestClient):
    """3. Valid ARTIFACT_FUSION job creation consumes repository outputs and returns 201."""
    payload = {
        "mode": "DEMO",
        "pipeline_type": "ARTIFACT_FUSION",
        "input_artifacts": {
            "temporal_geojson": "outputs/temporal/00007_to_01339_temporal_events.geojson",
            "drift_geojson": "outputs/origin_drift/trujillo_00007_01339.geojson",
            "ais_summary": "outputs/ais/trujillo_00007_01339_summary.json",
        },
    }
    resp = test_client.post("/api/v1/jobs", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "SUCCEEDED"
    assert len(data["artifacts"]) == 3


# ---------------------------------------------------------------------------
# State, Artifacts & Result Retrieval
# ---------------------------------------------------------------------------


def test_get_job_state(test_client: TestClient):
    """4. Querying job state returns full manifest."""
    create_resp = test_client.post("/api/v1/jobs", json={"mode": "DEMO", "pipeline_type": "DEMO_FUSION"})
    job_id = create_resp.json()["job_id"]

    resp = test_client.get(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["job_id"] == job_id
    assert data["status"] == "SUCCEEDED"
    assert "VALIDATE" in data["stage_status"]
    assert "FUSION" in data["stage_status"]
    assert "EXPORT" in data["stage_status"]


def test_get_job_artifacts(test_client: TestClient):
    """5. Querying job artifacts returns machine-readable artifact metadata."""
    create_resp = test_client.post("/api/v1/jobs", json={"mode": "DEMO", "pipeline_type": "DEMO_FUSION"})
    job_id = create_resp.json()["job_id"]

    resp = test_client.get(f"/api/v1/jobs/{job_id}/artifacts")
    assert resp.status_code == 200
    data = resp.json()

    assert data["job_id"] == job_id
    assert data["total_artifacts"] == 3
    types = [a["artifact_type"] for a in data["artifacts"]]
    assert "EVIDENCE_GRAPH_JSON" in types
    assert "EVIDENCE_SUMMARY_JSON" in types
    assert "EVIDENCE_GEOJSON" in types


def test_get_job_result_success(test_client: TestClient):
    """6. Result endpoint returns full normalized Evidence Fusion results."""
    create_resp = test_client.post("/api/v1/jobs", json={"mode": "DEMO", "pipeline_type": "DEMO_FUSION"})
    job_id = create_resp.json()["job_id"]

    resp = test_client.get(f"/api/v1/jobs/{job_id}/result")
    assert resp.status_code == 200
    result = resp.json()

    assert result["job_id"] == job_id
    assert result["total_evidence_items"] >= 6
    assert result["multiple_plausible_candidates"] is True
    assert result["negative_proof_guard"] == "AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE"

    # Evidence graph is exposed
    assert "evidence_graph" in result
    assert "nodes" in result["evidence_graph"]
    assert "edges" in result["evidence_graph"]


# ---------------------------------------------------------------------------
# 404 Not Found Checks
# ---------------------------------------------------------------------------


def test_get_unknown_job_404(test_client: TestClient):
    """7. Unknown job returns 404 with structured JOB_NOT_FOUND code."""
    resp = test_client.get("/api/v1/jobs/job_unknown_12345")
    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] == "JOB_NOT_FOUND"


def test_get_unknown_job_artifacts_404(test_client: TestClient):
    """8. Artifacts endpoint for unknown job returns 404."""
    resp = test_client.get("/api/v1/jobs/job_unknown_12345/artifacts")
    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] == "JOB_NOT_FOUND"


def test_get_unknown_job_result_404(test_client: TestClient):
    """9. Result endpoint for unknown job returns 404."""
    resp = test_client.get("/api/v1/jobs/job_unknown_12345/result")
    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] == "JOB_NOT_FOUND"


# ---------------------------------------------------------------------------
# Input Validation & Security Hardening
# ---------------------------------------------------------------------------


def test_create_job_invalid_mode(test_client: TestClient):
    """10. Invalid mode parameter returns 422 with INVALID_INPUT."""
    resp = test_client.post("/api/v1/jobs", json={"mode": "INVALID_MODE"})
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == "INVALID_INPUT"


def test_create_job_invalid_pipeline_type(test_client: TestClient):
    """11. Invalid pipeline_type returns 422 with INVALID_INPUT."""
    resp = test_client.post("/api/v1/jobs", json={"pipeline_type": "UNSUPPORTED_TYPE"})
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == "INVALID_INPUT"


def test_create_job_negative_spatial_tolerance(test_client: TestClient):
    """12. Negative spatial_tolerance_m returns 422 with INVALID_INPUT."""
    resp = test_client.post("/api/v1/jobs", json={"spatial_tolerance_m": -50.0})
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == "INVALID_INPUT"


def test_create_job_negative_temporal_tolerance(test_client: TestClient):
    """13. Negative temporal_tolerance_hours returns 422 with INVALID_INPUT."""
    resp = test_client.post("/api/v1/jobs", json={"temporal_tolerance_hours": -2.0})
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == "INVALID_INPUT"


def test_create_job_path_traversal_rejection(test_client: TestClient):
    """14. Path traversal attempt in input_artifacts returns 422 with INVALID_INPUT."""
    payload = {
        "mode": "DEMO",
        "pipeline_type": "ARTIFACT_FUSION",
        "input_artifacts": {
            "drift_geojson": "../../etc/passwd",
        },
    }
    resp = test_client.post("/api/v1/jobs", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == "INVALID_INPUT"


# ---------------------------------------------------------------------------
# Provenance & Physical Mode Fail-Closed Gate
# ---------------------------------------------------------------------------


def test_create_job_physical_mode_fail_closed(test_client: TestClient):
    """15. PHYSICAL mode execution without operational feeds produces BLOCKED_PROVENANCE."""
    resp = test_client.post(
        "/api/v1/jobs",
        json={"mode": "PHYSICAL", "pipeline_type": "PHYSICAL"},
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "BLOCKED_PROVENANCE"
    assert data["error"]["code"] == "PROVENANCE_REJECTION"
    assert "BLOCKED — AWAITING_OPERATIONAL_SOURCE" in data["error"]["message"]


def test_get_job_result_blocked_provenance_403(test_client: TestClient):
    """16. Requesting result of a BLOCKED_PROVENANCE job returns 403 Forbidden."""
    create_resp = test_client.post(
        "/api/v1/jobs",
        json={"mode": "PHYSICAL", "pipeline_type": "PHYSICAL"},
    )
    job_id = create_resp.json()["job_id"]

    resp = test_client.get(f"/api/v1/jobs/{job_id}/result")
    assert resp.status_code == 403
    data = resp.json()
    assert data["code"] == "PROVENANCE_REJECTION"


# ---------------------------------------------------------------------------
# Job Listing & Restart Persistence
# ---------------------------------------------------------------------------


def test_list_jobs_endpoint(test_client: TestClient):
    """17. Listing jobs returns recent job summaries."""
    test_client.post("/api/v1/jobs", json={"mode": "DEMO", "pipeline_type": "DEMO_FUSION"})
    test_client.post("/api/v1/jobs", json={"mode": "DEMO", "pipeline_type": "DEMO_FUSION"})

    resp = test_client.get("/api/v1/jobs?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_jobs"] >= 2
    assert len(data["jobs"]) >= 2


def test_manifest_survives_restart(tmp_path: Path):
    """18. Manifest is readable independently of the process (simulating server restart)."""
    jobs_dir = tmp_path / "restart_jobs"
    store1 = JobStore(base_dir=jobs_dir)
    orch1 = PipelineOrchestrator(job_store=store1)
    set_orchestrator(orch1)

    app1 = create_app()
    client1 = TestClient(app1)
    create_resp = client1.post("/api/v1/jobs", json={"mode": "DEMO", "pipeline_type": "DEMO_FUSION"})
    job_id = create_resp.json()["job_id"]

    # Simulate server restart by creating completely new store, orchestrator, and client
    store2 = JobStore(base_dir=jobs_dir)
    orch2 = PipelineOrchestrator(job_store=store2)
    set_orchestrator(orch2)

    app2 = create_app()
    client2 = TestClient(app2)

    resp = client2.get(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["status"] == "SUCCEEDED"

    res_resp = client2.get(f"/api/v1/jobs/{job_id}/result")
    assert res_resp.status_code == 200
    assert res_resp.json()["multiple_plausible_candidates"] is True


# ---------------------------------------------------------------------------
# Scientific Terminology & Multi-Candidate Preservations
# ---------------------------------------------------------------------------


def test_terminology_guard_in_api_response(test_client: TestClient):
    """19. Response bodies do NOT contain illegal attribution or culpability claims."""
    create_resp = test_client.post("/api/v1/jobs", json={"mode": "DEMO", "pipeline_type": "DEMO_FUSION"})
    job_id = create_resp.json()["job_id"]

    result_resp = test_client.get(f"/api/v1/jobs/{job_id}/result")
    content_str = result_resp.text.lower()

    forbidden_terms = [
        "probability_of_guilt",
        "responsible_vessel",
        "guilty",
        "convicted",
        "proven_source",
        "culpable",
    ]
    for term in forbidden_terms:
        assert term not in content_str, f"Illegal attribution term '{term}' found in API result response!"


def test_multiple_candidates_preserved_in_api(test_client: TestClient):
    """20. Multiple candidate vessels remain preserved simultaneously without forced winner."""
    create_resp = test_client.post("/api/v1/jobs", json={"mode": "DEMO", "pipeline_type": "DEMO_FUSION"})
    job_id = create_resp.json()["job_id"]

    result_resp = test_client.get(f"/api/v1/jobs/{job_id}/result")
    result = result_resp.json()

    assert result["multiple_plausible_candidates"] is True
    assert result["plausible_candidate_count"] >= 2
    candidates = result["candidate_vessel_hypotheses"]
    supported_vessels = [
        c["vessel_name"]
        for c in candidates
        if c["overall_status"] in ["SUPPORTED_BY_AVAILABLE_EVIDENCE", "CONSISTENT_WITH_AVAILABLE_EVIDENCE"]
    ]
    assert "MT_HORIZON_STAR" in supported_vessels
    assert "GULF_SUPPLIER_VII" in supported_vessels
