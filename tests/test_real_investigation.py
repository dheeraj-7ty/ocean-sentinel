"""Focused Verification Suite for Real Repository Investigation Workflow V1.

Tests all 17 verification requirements mandated by Section 16 of the task specification:
1. DEMO remains clearly DEMO.
2. REAL_REPOSITORY mode is accepted.
3. PHYSICAL remains fail-closed.
4. REAL_REPOSITORY does not silently fall back to DEMO.
5. Invalid artifact references are rejected.
6. Traversal is rejected.
7. Job stage states are faithfully surfaced.
8. Real repository result appears via API.
9. Provenance state is displayed correctly.
10. Metadata unavailable is handled explicitly.
11. Actual artifact geometry is rendered.
12. Evidence Fusion result semantics remain unchanged.
13. Multiple candidates remain visible.
14. Conflicts remain visible.
15. DATA_UNAVAILABLE remains visible.
16. No prohibited attribution wording is introduced.
17. Repeated execution of the same repository scenario is deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Generator
import pytest
from fastapi.testclient import TestClient

from ocean_sentinel.api.app import create_app
from ocean_sentinel.api.routes import set_orchestrator
from ocean_sentinel.orchestration.jobs import (
    JobMode,
    JobStatus,
    JobStore,
    PipelineStage,
    PipelineType,
    StageExecutionStatus,
)
from ocean_sentinel.orchestration.pipeline import PipelineOrchestrator
from ocean_sentinel.orchestration.scenarios import (
    get_scenario,
    list_scenarios,
)
from ocean_sentinel.fusion import (
    EvidenceFusionEngine,
    EvidenceItem,
    EvidenceType,
    IndependenceEngine,
    IndependenceRelation,
    ProvenanceClass,
    SourceType,
    load_evidence_from_drift_geojson,
    load_evidence_from_temporal_geojson,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client_with_isolated_store(tmp_path: Path) -> Generator[TestClient, None, None]:
    """TestClient with an isolated temporary JobStore."""
    store = JobStore(tmp_path / "test_jobs")
    orchestrator = PipelineOrchestrator(job_store=store)
    set_orchestrator(orchestrator)
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestRealInvestigationWorkflow:
    """Automated verification suite for Real Repository Investigation Workflow V1."""

    # 1. DEMO remains clearly DEMO
    def test_01_demo_remains_clearly_demo(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post("/api/v1/jobs", json={"mode": "DEMO", "pipeline_type": "DEMO_FUSION"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["mode"] == "DEMO"
        assert data["pipeline_type"] == "DEMO_FUSION"
        assert data["status"] == "SUCCEEDED"

        # Check result
        res_resp = client.get(f"/api/v1/jobs/{data['job_id']}/result")
        assert res_resp.status_code == 200
        res = res_resp.json()
        assert res["mode"] == "DEMO"
        assert res["provenance_class"] == "SYNTHETIC_DEMO"

    # 2. REAL_REPOSITORY mode is accepted
    def test_02_real_repository_mode_accepted(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["mode"] == "REAL_REPOSITORY"
        assert data["pipeline_type"] == "REAL_REPOSITORY"
        assert data["scenario_id"] == "TRUJILLO_00260_00608"
        assert data["status"] == "SUCCEEDED"

    # 3. PHYSICAL remains fail-closed
    def test_03_physical_remains_fail_closed(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post("/api/v1/jobs", json={"mode": "PHYSICAL", "pipeline_type": "PHYSICAL"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "BLOCKED_PROVENANCE"
        assert "AWAITING_OPERATIONAL_SOURCE" in data["error"]["message"]

        # 403 on result retrieval
        res_resp = client.get(f"/api/v1/jobs/{data['job_id']}/result")
        assert res_resp.status_code == 403
        assert res_resp.json()["code"] == "PROVENANCE_REJECTION"

    # 4. REAL_REPOSITORY does not silently fall back to DEMO
    def test_04_real_repository_no_silent_fallback_to_demo(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        # Invalid scenario must fail with INVALID_INPUT, never fall back to DEMO
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "NON_EXISTENT_SCENARIO_ID",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "FAILED"
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "NON_EXISTENT_SCENARIO_ID" in data["error"]["message"]
        # Result endpoint returns 500/failed
        res_resp = client.get(f"/api/v1/jobs/{data['job_id']}/result")
        assert res_resp.status_code == 500

    # 5. Invalid artifact references are rejected
    def test_05_invalid_artifact_references_rejected(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "DEMO",
                "pipeline_type": "ARTIFACT_FUSION",
                "input_artifacts": {
                    "temporal_geojson": "outputs/temporal/does_not_exist_9999.geojson",
                },
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "FAILED"
        assert data["error"]["code"] == "ARTIFACT_NOT_FOUND"

    # 6. Traversal is rejected
    def test_06_traversal_is_rejected(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        # Path traversal in scenario_id
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "../../../etc/passwd",
            },
        )
        assert resp.status_code in [400, 422]
        data = resp.json()
        assert "traversal" in str(data).lower() or data.get("code") == "INVALID_INPUT"

        # Path traversal in input_artifacts
        resp2 = client.post(
            "/api/v1/jobs",
            json={
                "mode": "DEMO",
                "pipeline_type": "ARTIFACT_FUSION",
                "input_artifacts": {
                    "temporal_geojson": "../secret.json",
                },
            },
        )
        assert resp2.status_code in [400, 422]
        data2 = resp2.json()
        assert "traversal" in str(data2).lower() or data2.get("code") == "INVALID_INPUT"

    # 7. Job stage states are faithfully surfaced
    def test_07_job_stage_states_faithfully_surfaced(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        data = resp.json()
        stages = data["stage_status"]

        # Exact faithfulness per Section 10
        assert stages["VALIDATE"]["status"] == "COMPLETED"
        assert stages["INGEST"]["status"] == "COMPLETED"
        assert stages["INFER"]["status"] == "SKIPPED"
        assert "exp06" in stages["INFER"]["details"]["reason"]
        assert stages["INTERPRET"]["status"] == "SKIPPED"
        assert stages["TEMPORAL"]["status"] == "COMPLETED"
        assert stages["DRIFT"]["status"] == "COMPLETED"
        assert stages["AIS"]["status"] == "COMPLETED"
        assert stages["FUSION"]["status"] == "COMPLETED"
        assert stages["EXPORT"]["status"] == "COMPLETED"

    # 8. Real repository result appears in frontend / API
    def test_08_real_repository_result_appears(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        jid = resp.json()["job_id"]
        res_resp = client.get(f"/api/v1/jobs/{jid}/result")
        assert res_resp.status_code == 200
        res = res_resp.json()
        assert res["job_id"] == jid
        assert res["mode"] == "REAL_REPOSITORY"
        assert res["scenario_id"] == "TRUJILLO_00260_00608"
        assert "Trujillo" in res["investigation_label"]

    # 9. Provenance state is displayed correctly
    def test_09_provenance_state_correct(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        jid = resp.json()["job_id"]
        res_resp = client.get(f"/api/v1/jobs/{jid}/result")
        res = res_resp.json()
        assert res["provenance_class"] == "REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY"
        assert res["provenance_status"] == "PROVENANCE_LIMITED"
        assert res["has_synthetic_dependencies"] is True
        assert res["stage_provenance"]["satellite"] == "HISTORICAL_ARCHIVE"
        assert res["stage_provenance"]["temporal"] == "HISTORICAL_ARCHIVE"
        assert res["stage_provenance"]["drift"] == "SYNTHETIC_DEMO"
        assert res["stage_provenance"]["ais"] == "SYNTHETIC_DEMO"

        # Check exported artifacts provenance
        art_resp = client.get(f"/api/v1/jobs/{jid}/artifacts")
        arts = art_resp.json()["artifacts"]
        for art in arts:
            assert art["provenance_class"] == "REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY"

    # 10. Metadata unavailable is handled explicitly
    def test_10_metadata_unavailable_handled_explicitly(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        # Check scenario endpoint
        sc_resp = client.get("/api/v1/investigations/scenarios/TRUJILLO_00007_01339")
        assert sc_resp.status_code == 200
        sc = sc_resp.json()
        assert sc["satellite_product_id"] == "METADATA UNAVAILABLE"
        assert sc["vessel_truth"] == "METADATA UNAVAILABLE"
        assert sc["physical_incident_label"] == "METADATA UNAVAILABLE"
        assert sc["unverified_source_metadata"] == "METADATA UNAVAILABLE"

    # 11. Actual artifact geometry is rendered
    def test_11_actual_artifact_geometry_rendered(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        jid = resp.json()["job_id"]
        res = client.get(f"/api/v1/jobs/{jid}/result").json()
        spills = res["candidate_spill_hypotheses"]
        assert len(spills) > 0
        origin_geom = spills[0]["spatial_geometry"]
        assert origin_geom is not None
        assert origin_geom["type"] in ["Polygon", "MultiPolygon", "Point"]
        coords = origin_geom["coordinates"]
        assert len(coords) > 0

    # 12. Evidence Fusion result semantics remain unchanged
    def test_12_evidence_fusion_semantics_preserved(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        res = client.get(f"/api/v1/jobs/{resp.json()['job_id']}/result").json()
        assert "engine" in res
        assert "evidence_graph" in res
        assert "nodes" in res["evidence_graph"]
        assert "edges" in res["evidence_graph"]
        assert any("compatibility" in b.lower() for b in res["scientific_boundaries"])
        assert res["negative_proof_guard"] == "AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE"

    # 13. Multiple candidates remain visible
    def test_13_multiple_candidates_visible(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        res = client.get(f"/api/v1/jobs/{resp.json()['job_id']}/result").json()
        assert res["multiple_plausible_candidates"] is True
        vessels = res["candidate_vessel_hypotheses"]
        assert len(vessels) >= 2
        names = [v["vessel_name"] for v in vessels]
        assert "MT_HORIZON_STAR" in names
        assert "GULF_SUPPLIER_VII" in names

    # 14. Conflicts remain visible
    def test_14_conflicts_remain_visible(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        res = client.get(f"/api/v1/jobs/{resp.json()['job_id']}/result").json()
        edges = res["evidence_graph"]["edges"]
        edge_types = [e["relation_type"] for e in edges]
        assert len(edge_types) > 0

    # 15. DATA_UNAVAILABLE remains visible
    def test_15_data_unavailable_remains_visible(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        res = client.get(f"/api/v1/jobs/{resp.json()['job_id']}/result").json()
        vessels = res["candidate_vessel_hypotheses"]
        sea_prowler = next(v for v in vessels if v["vessel_name"] == "SEA_PROWLER")
        assert "TELEMETRY_GAP" in sea_prowler["coverage_status"]

    # 16. No prohibited attribution wording is introduced
    def test_16_no_prohibited_attribution_wording(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        raw_text = json.dumps(resp.json()).lower()
        res_raw = json.dumps(client.get(f"/api/v1/jobs/{resp.json()['job_id']}/result").json()).lower()
        combined = raw_text + " " + res_raw

        prohibited = [
            "guilty",
            "confirmed responsible vessel",
            "proven causal attribution",
            "perpetrator",
            "culprit",
        ]
        for word in prohibited:
            assert word not in combined, f"Prohibited word '{word}' found in response"

    # 17. Deterministic repeated execution
    def test_17_deterministic_repeated_execution(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        r1 = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        ).json()
        r2 = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        ).json()

        res1 = client.get(f"/api/v1/jobs/{r1['job_id']}/result").json()
        res2 = client.get(f"/api/v1/jobs/{r2['job_id']}/result").json()

        assert res1["total_evidence_items"] == res2["total_evidence_items"]
        assert res1["total_candidate_hypotheses"] == res2["total_candidate_hypotheses"]
        assert res1["plausible_candidate_count"] == res2["plausible_candidate_count"]
        # Vessel names and scores are identical
        v1 = [(v["vessel_name"], v["evidence_compatibility_score"]) for v in res1["candidate_vessel_hypotheses"]]
        v2 = [(v["vessel_name"], v["evidence_compatibility_score"]) for v in res2["candidate_vessel_hypotheses"]]
        assert v1 == v2


class TestRealInvestigationProvenanceCorrection:
    """Dedicated provenance verification suite per Section 9 & 14."""

    # 1. Historical Sentinel-1 artifact remains HISTORICAL_ARCHIVE
    def test_01_historical_sentinel1_artifact_remains_historical_archive(self) -> None:
        temporal_path = REPO_ROOT / "outputs/temporal/00007_to_01339_temporal_events.geojson"
        evidence_items = load_evidence_from_temporal_geojson(temporal_path)
        assert len(evidence_items) > 0
        for item in evidence_items:
            assert item.provenance_class == ProvenanceClass.HISTORICAL_ARCHIVE.value
            assert item.derivation_type == "DERIVED_ANALYSIS"
            assert "scene_00007" in item.root_source_ids
            assert "scene_01339" in item.root_source_ids

    # 2. DEMO-generated AIS artifact remains SYNTHETIC_DEMO
    def test_02_demo_generated_ais_artifact_remains_synthetic_demo(self) -> None:
        ais_path = REPO_ROOT / "outputs/ais/trujillo_00007_01339_summary.json"
        with open(ais_path, "r", encoding="utf-8") as f:
            ais_data = json.load(f)
        assert ais_data.get("mode") == "DEMO"
        candidates = ais_data.get("candidate_vessels", [])
        assert len(candidates) > 0
        for cand in candidates:
            assert cand.get("provenance") == "SYNTHETIC_DEMO_FEED"

        engine = EvidenceFusionEngine()
        engine.synthesize_candidate_vessel_hypotheses(ais_data, "drift_hypo_01")
        ais_items = [
            it for it in engine.evidence_store.values()
            if "ais" in it.source_id.lower() or "vessel" in it.source_id.lower() or "candidate" in it.evidence_id.lower()
        ]
        assert len(ais_items) > 0
        for it in ais_items:
            assert it.provenance_class == ProvenanceClass.SYNTHETIC_DEMO.value

    # 3. DEMO-generated drift artifact remains SYNTHETIC_DEMO
    def test_03_demo_generated_drift_artifact_remains_synthetic_demo(self) -> None:
        drift_path = REPO_ROOT / "outputs/origin_drift/trujillo_00007_01339.geojson"
        with open(drift_path, "r", encoding="utf-8") as f:
            drift_data = json.load(f)
        assert drift_data.get("metadata", {}).get("mode") == "DEMO"
        assert "synthetic" in drift_data.get("metadata", {}).get("forcing_source", "").lower()

        drift_items = load_evidence_from_drift_geojson(drift_path)
        assert len(drift_items) > 0
        for item in drift_items:
            assert item.provenance_class == ProvenanceClass.SYNTHETIC_DEMO.value

    # 4. A scenario cannot promote synthetic child evidence to HISTORICAL_ARCHIVE
    def test_04_cannot_promote_synthetic_child_evidence_to_historical_archive(
        self, client_with_isolated_store: TestClient
    ) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        jid = resp.json()["job_id"]
        res = client.get(f"/api/v1/jobs/{jid}/result").json()
        ledger = res["evidence_ledger"]

        # Synthetic drift items must remain SYNTHETIC_DEMO
        drift_items = [
            it for it in ledger
            if it.get("evidence_type") in ["DRIFT_TRAJECTORY", "DRIFT_ORIGIN_HYPOTHESIS"]
        ]
        assert len(drift_items) > 0
        for it in drift_items:
            assert it["provenance_class"] == "SYNTHETIC_DEMO"

        # Synthetic AIS candidate vessel items must remain SYNTHETIC_DEMO
        vessel_items = [
            it for it in ledger
            if it.get("evidence_type") in ["AIS_OBSERVATION", "AIS_TRACK", "AIS_CORRELATION"]
        ]
        assert len(vessel_items) > 0
        for it in vessel_items:
            assert it["provenance_class"] == "SYNTHETIC_DEMO"

    # 5. Real repository investigation detects synthetic dependencies
    def test_05_real_repository_investigation_detects_synthetic_dependencies(
        self, client_with_isolated_store: TestClient
    ) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        jid = resp.json()["job_id"]
        res = client.get(f"/api/v1/jobs/{jid}/result").json()
        assert res["has_synthetic_dependencies"] is True
        assert res["provenance_status"] == "PROVENANCE_LIMITED"
        assert res["stage_provenance"]["drift"] == "SYNTHETIC_DEMO"
        assert res["stage_provenance"]["ais"] == "SYNTHETIC_DEMO"
        assert res["stage_provenance"]["satellite"] == "HISTORICAL_ARCHIVE"

    # 6. REAL_REPOSITORY does not silently re-label synthetic evidence
    def test_06_real_repository_does_not_silently_relabel_synthetic_evidence(
        self, client_with_isolated_store: TestClient
    ) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        jid = resp.json()["job_id"]
        manifest = client.get(f"/api/v1/jobs/{jid}").json()
        # AIS and DRIFT stages must record SYNTHETIC_DEMO provenance
        assert manifest["stage_status"]["DRIFT"]["details"]["provenance_class"] == "SYNTHETIC_DEMO"
        assert manifest["stage_status"]["AIS"]["details"]["provenance_class"] == "SYNTHETIC_DEMO"

    # 7. Final result exposes provenance limitation correctly
    def test_07_final_result_exposes_provenance_limitation_correctly(
        self, client_with_isolated_store: TestClient
    ) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        jid = resp.json()["job_id"]
        res = client.get(f"/api/v1/jobs/{jid}/result").json()
        assert res["provenance_class"] == "REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY"
        assert res["provenance_status"] == "PROVENANCE_LIMITED"
        assert res.get("provenance_limitation") is not None
        assert "synthetic" in res["provenance_limitation"].lower()
        assert any("compatibility" in b.lower() for b in res["scientific_boundaries"])

    # 8. Lineage: historical SAR -> temporal derivative must NOT become independent
    def test_08_lineage_historical_sar_to_temporal_not_independent(self) -> None:
        temporal_path = REPO_ROOT / "outputs/temporal/00007_to_01339_temporal_events.geojson"
        temp_items = load_evidence_from_temporal_geojson(temporal_path)
        assert len(temp_items) > 0
        temp_item = temp_items[0]
        assert temp_item.derivation_type == "DERIVED_ANALYSIS"
        assert "scene_00007" in temp_item.root_source_ids
        assert "scene_01339" in temp_item.root_source_ids

        # Root SAR observation item
        sar_item = EvidenceItem(
            evidence_id="sar_root_00007",
            evidence_type=EvidenceType.SAR_DETECTION,
            source_type=SourceType.SENTINEL_1_SAR,
            source_id="scene_00007",
            observation_time=temp_item.observation_time,
            provenance_class=ProvenanceClass.HISTORICAL_ARCHIVE,
            provenance_source="SENTINEL_1_ARCHIVE",
            root_source_ids=["scene_00007"],
        )
        engine = EvidenceFusionEngine()
        engine.ingest_evidence_item(sar_item)
        engine.ingest_evidence_item(temp_item)

        indep = IndependenceEngine(engine.evidence_store)
        rel = indep.classify_relationship("sar_root_00007", temp_item.evidence_id)
        # Must NOT be INDEPENDENT_SOURCE; temporal change derives from / shares root with SAR
        assert rel in [IndependenceRelation.SHARED_SOURCE, IndependenceRelation.DERIVED_FROM]

        # Independent clustering must group them into a single cluster to prevent double counting
        clusters = indep.group_into_independent_clusters(["sar_root_00007", temp_item.evidence_id])
        assert len(clusters) == 1
        assert "sar_root_00007" in clusters[0]
        assert temp_item.evidence_id in clusters[0]

    # 9. Lineage: historical SAR -> synthetic drift -> synthetic AIS retains synthetic provenance
    def test_09_lineage_downstream_branch_retains_synthetic_provenance(
        self, client_with_isolated_store: TestClient
    ) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        jid = resp.json()["job_id"]
        res = client.get(f"/api/v1/jobs/{jid}/result").json()
        # Satellite stage remains historical
        assert res["stage_provenance"]["satellite"] == "HISTORICAL_ARCHIVE"
        # Downstream branch drift is synthetic
        assert res["stage_provenance"]["drift"] == "SYNTHETIC_DEMO"
        # Downstream branch AIS is synthetic
        assert res["stage_provenance"]["ais"] == "SYNTHETIC_DEMO"
        # Overall result is NOT HISTORICAL_ARCHIVE
        assert res["provenance_class"] != "HISTORICAL_ARCHIVE"
        assert res["provenance_class"] == "REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY"

    # 10. PHYSICAL still fails closed
    def test_10_physical_still_fails_closed(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post("/api/v1/jobs", json={"mode": "PHYSICAL", "pipeline_type": "PHYSICAL"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "BLOCKED_PROVENANCE"
        res_resp = client.get(f"/api/v1/jobs/{data['job_id']}/result")
        assert res_resp.status_code == 403

    # 11. DEMO still works
    def test_11_demo_still_works(self, client_with_isolated_store: TestClient) -> None:
        client = client_with_isolated_store
        resp = client.post("/api/v1/jobs", json={"mode": "DEMO", "pipeline_type": "DEMO_FUSION"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "SUCCEEDED"
        res = client.get(f"/api/v1/jobs/{data['job_id']}/result").json()
        assert res["mode"] == "DEMO"
        assert res["provenance_class"] == "SYNTHETIC_DEMO"
        assert res["has_synthetic_dependencies"] is False

    # 12. Existing Evidence Fusion semantics remain unchanged
    def test_12_existing_evidence_fusion_semantics_remain_unchanged(
        self, client_with_isolated_store: TestClient
    ) -> None:
        client = client_with_isolated_store
        resp = client.post(
            "/api/v1/jobs",
            json={
                "mode": "REAL_REPOSITORY",
                "pipeline_type": "REAL_REPOSITORY",
                "scenario_id": "TRUJILLO_00260_00608",
            },
        )
        jid = resp.json()["job_id"]
        res = client.get(f"/api/v1/jobs/{jid}/result").json()
        assert res["multiple_plausible_candidates"] is True
        assert res["negative_proof_guard"] == "AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE"
        assert len(res["candidate_vessel_hypotheses"]) == 6
        assert res["plausible_candidate_count"] >= 2
        # MT_HORIZON_STAR top score matches expected range ~0.86 - 0.92
        mt_star = next(v for v in res["candidate_vessel_hypotheses"] if v["vessel_name"] == "MT_HORIZON_STAR")
        assert 0.85 <= mt_star["evidence_compatibility_score"] <= 0.95
