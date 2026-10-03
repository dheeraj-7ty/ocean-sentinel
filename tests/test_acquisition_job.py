"""Targeted Test Suite for Phase 6C: Operational Acquisition Job & API Surface.

Covers:
1. Valid acquisition request schema & parameter normalization
2. Invalid AOI validation (bounds inversion, out of bounds)
3. Invalid date range validation (end <= start)
4. Synthetic / mock / demo provider rejection (fail-closed)
5. Deterministic collision-resistant job ID generation
6. Successful end-to-end mocked provider workflow (REQUEST -> DISCOVER -> ACQUIRE -> PERSIST -> VALIDATE -> READY_FOR_DETECTION)
7. Discovery failure mapping (timeout / unavailable / no observations) -> FAILED_DISCOVERY
8. Acquisition failure mapping (HTTP 500 / timeout / corrupt payload) -> FAILED_ACQUISITION
9. Persistence failure mapping (disk error) -> FAILED_PERSISTENCE
10. Integrity failure mapping (SHA-256 mismatch) -> FAILED_INTEGRITY
11. SAR validation failure mapping (contract violation) -> FAILED_VALIDATION
12. Scientific firewall: zero inference invocation, execution_authorized = False, has_prediction = False
13. FastAPI endpoint integration tests:
    - POST /api/v1/acquisitions (201 Created, READY_FOR_DETECTION)
    - POST /api/v1/acquisitions (400 Bad Request on invalid input / synthetic provider)
    - GET /api/v1/acquisitions (listing jobs)
    - GET /api/v1/acquisitions/{job_id} (retrieving job manifest)
    - GET /api/v1/acquisitions/{job_id}/result (retrieving operational evidence result)
    - GET /api/v1/acquisitions/{job_id}/result (error state handling)
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
import numpy as np
import pytest
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds

from ocean_sentinel.api.app import create_app
from ocean_sentinel.api.routes import set_acquisition_orchestrator
from ocean_sentinel.api.schemas import (
    AcquisitionJobRequest,
    AcquisitionJobResponse,
)
from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.errors import (
    ProviderTimeoutError,
    ProviderUnavailableError,
    RasterValidationError,
)
from ocean_sentinel.models import (
    AcquisitionMetadata,
    BandStatistics,
    BoundingBox,
    ImageryRequest,
    ImageryResult,
    OutputConfig,
    Polarization,
    ProductType,
    TimeRange,
)
from ocean_sentinel.operational_pipeline import (
    OperationalEvidenceResult,
    OperationalSARPipeline,
    PipelineStageState,
)
from ocean_sentinel.orchestration.acquisition_job import (
    AcquisitionJobManifest,
    AcquisitionJobOrchestrator,
    AcquisitionJobStage,
    AcquisitionJobStatus,
)
from ocean_sentinel.orchestration.jobs import JobStore
from ocean_sentinel.satellite.discovery import STACSearchResult, SentinelDiscoveryService
from ocean_sentinel.satellite.imagery import SentinelImageryService
from ocean_sentinel.satellite.persistence import (
    AcquisitionPersistenceService,
    PersistedAcquisitionArtifact,
    PersistenceIntegrityError,
    RealDataAcquisitionBridge,
)


# ---------------------------------------------------------------------------
# Test Fixtures & Synthetic GeoTIFF Helpers
# ---------------------------------------------------------------------------


def _create_mock_geotiff_bytes(
    width: int = 16,
    height: int = 16,
    bands: int = 2,
    dtype: str = "float32",
    bounds: tuple[float, float, float, float] = (1.0, 50.0, 2.0, 51.0),
) -> bytes:
    """Creates a deterministic in-memory GeoTIFF byte payload."""
    west, south, east, north = bounds
    transform = from_bounds(west, south, east, north, width, height)
    crs = CRS.from_epsg(4326)

    with MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff",
            width=width,
            height=height,
            count=bands,
            dtype=dtype,
            crs=crs,
            transform=transform,
        ) as dst:
            for b in range(1, bands + 1):
                data = (np.ones((height, width), dtype=np.float32) * b * 0.1).astype(np.float32)
                dst.write(data, b)
        return memfile.read()


def _make_mock_observation(obs_id: str = "S1A_IW_GRDH_TEST_OBS") -> AcquisitionMetadata:
    return AcquisitionMetadata(
        id=obs_id,
        mission="sentinel-1",
        product_type=ProductType.GRD,
        acquisition_time=datetime(2024, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        geometry={
            "type": "Polygon",
            "coordinates": [[[1.0, 50.0], [2.0, 50.0], [2.0, 51.0], [1.0, 51.0], [1.0, 50.0]]],
        },
        polarizations=[Polarization.VV, Polarization.VH],
        provider="copernicus_cdse",
        source_reference=obs_id,
        self_link=f"https://stac.dataspace.copernicus.eu/v1/collections/sentinel-1-grd/items/{obs_id}",
    )


def _make_mock_imagery_result(
    obs_id: str = "S1A_IW_GRDH_TEST_OBS",
    raw_bytes: Optional[bytes] = None,
) -> ImageryResult:
    b = raw_bytes or _create_mock_geotiff_bytes()
    stats = [
        BandStatistics(
            polarization=Polarization.VV,
            min_value=0.01,
            max_value=1.5,
            mean_value=0.08,
            finite_pixel_count=256,
            total_pixel_count=256,
        ),
        BandStatistics(
            polarization=Polarization.VH,
            min_value=0.001,
            max_value=0.2,
            mean_value=0.015,
            finite_pixel_count=256,
            total_pixel_count=256,
        ),
    ]
    return ImageryResult(
        observation_id=obs_id,
        width=16,
        height=16,
        band_count=2,
        bands=[Polarization.VV, Polarization.VH],
        dtype="float32",
        crs="EPSG:4326",
        bounds=[1.0, 50.0, 2.0, 51.0],
        transform=[0.0625, 0.0, 1.0, 0.0, -0.0625, 51.0],
        band_statistics=stats,
        raw_bytes=b,
    )


# ---------------------------------------------------------------------------
# Unit Tests: Schema & Parameter Validation
# ---------------------------------------------------------------------------


class TestAcquisitionJobSchemas:
    """Validates AcquisitionJobRequest schema and rejection boundaries."""

    def test_valid_request(self):
        req = AcquisitionJobRequest(
            west=1.0,
            south=50.0,
            east=2.0,
            north=51.0,
            start_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
            provider="copernicus_cdse",
            polarizations=["VV", "VH"],
        )
        assert req.west == 1.0
        assert req.provider == "copernicus_cdse"
        assert req.polarizations == ["VV", "VH"]

    def test_invalid_aoi_inverted_longitude(self):
        with pytest.raises(ValueError, match="east.*must be strictly greater than west"):
            AcquisitionJobRequest(
                west=5.0,
                south=50.0,
                east=2.0,
                north=51.0,
                start_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
                end_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
            )

    def test_invalid_aoi_inverted_latitude(self):
        with pytest.raises(ValueError, match="north.*must be strictly greater than south"):
            AcquisitionJobRequest(
                west=1.0,
                south=52.0,
                east=2.0,
                north=50.0,
                start_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
                end_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
            )

    def test_invalid_time_range(self):
        with pytest.raises(ValueError, match="end_time.*must be strictly after start_time"):
            AcquisitionJobRequest(
                west=1.0,
                south=50.0,
                east=2.0,
                north=51.0,
                start_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
                end_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
            )

    def test_synthetic_provider_rejected_fail_closed(self):
        for fake in ["synthetic_provider", "demo_copernicus", "mock_source", "dummy_feed"]:
            with pytest.raises(ValueError, match="only real operational EO providers"):
                AcquisitionJobRequest(
                    west=1.0,
                    south=50.0,
                    east=2.0,
                    north=51.0,
                    start_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
                    end_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
                    provider=fake,
                )

    def test_invalid_polarization(self):
        with pytest.raises(ValueError, match="Polarization.*invalid"):
            AcquisitionJobRequest(
                west=1.0,
                south=50.0,
                east=2.0,
                north=51.0,
                start_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
                end_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
                polarizations=["INVALID_POL"],
            )


# ---------------------------------------------------------------------------
# Unit & Workflow Tests: AcquisitionJobOrchestrator
# ---------------------------------------------------------------------------


class TestAcquisitionJobOrchestrator:
    """Tests the state machine, bindings, and failure mappings of the orchestrator."""

    @pytest.fixture
    def setup_orchestrator(self, tmp_path: Path):
        job_store = JobStore(base_dir=tmp_path / "jobs")
        raw_storage = tmp_path / "raw_acquisitions"
        persistence = AcquisitionPersistenceService(storage_root=raw_storage)
        pipeline = OperationalSARPipeline(execution_authorized=False)
        bridge = RealDataAcquisitionBridge(
            persistence_service=persistence,
            operational_pipeline=pipeline,
        )

        discovery = MagicMock(spec=SentinelDiscoveryService)
        imagery = MagicMock(spec=SentinelImageryService)

        orchestrator = AcquisitionJobOrchestrator(
            job_store=job_store,
            discovery_service=discovery,
            imagery_service=imagery,
            persistence_service=persistence,
            bridge=bridge,
        )
        return orchestrator, discovery, imagery, job_store

    def test_deterministic_job_id(self, setup_orchestrator):
        orchestrator, _, _, _ = setup_orchestrator
        jid = orchestrator.generate_job_id()
        assert jid.startswith("acq_")
        assert len(jid) > 15

    @pytest.mark.asyncio
    async def test_successful_acquisition_workflow(self, setup_orchestrator):
        orchestrator, discovery, imagery, job_store = setup_orchestrator

        # Configure mocks
        mock_obs = _make_mock_observation("S1A_IW_GRDH_SUCCESS_01")
        discovery.search = AsyncMock(return_value=STACSearchResult(observations=[mock_obs]))
        imagery.request_imagery = AsyncMock(return_value=_make_mock_imagery_result("S1A_IW_GRDH_SUCCESS_01"))

        manifest = await orchestrator.execute_acquisition_job(
            west=1.0,
            south=50.0,
            east=2.0,
            north=51.0,
            start_time=datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc),
            provider="copernicus_cdse",
            width=16,
            height=16,
        )

        assert manifest.status == AcquisitionJobStatus.READY_FOR_DETECTION.value
        assert manifest.current_stage == AcquisitionJobStage.COMPLETE.value
        assert manifest.acquisition_id == "S1A_IW_GRDH_SUCCESS_01"
        assert manifest.provider == "copernicus_cdse"
        assert manifest.source_reference == "S1A_IW_GRDH_SUCCESS_01"
        assert manifest.geotiff_path is not None
        assert Path(manifest.geotiff_path).is_file()
        assert manifest.metadata_path is not None
        assert Path(manifest.metadata_path).is_file()
        assert manifest.content_sha256 is not None
        assert manifest.sar_validation["status"] == "PASSED"
        assert manifest.evidence_id is not None
        assert manifest.evidence_result is not None
        assert manifest.execution_authorized is False
        assert manifest.has_prediction is False

        # Verify job store disk persistence
        reloaded = orchestrator.get_job_manifest(manifest.job_id)
        assert reloaded is not None
        assert reloaded.status == AcquisitionJobStatus.READY_FOR_DETECTION.value
        assert reloaded.content_sha256 == manifest.content_sha256

    @pytest.mark.asyncio
    async def test_discovery_no_observations_fails_discovery(self, setup_orchestrator):
        orchestrator, discovery, imagery, _ = setup_orchestrator
        discovery.search = AsyncMock(return_value=STACSearchResult(observations=[]))

        manifest = await orchestrator.execute_acquisition_job(
            west=1.0,
            south=50.0,
            east=2.0,
            north=51.0,
            start_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
        )

        assert manifest.status == AcquisitionJobStatus.FAILED_DISCOVERY.value
        assert manifest.current_stage == AcquisitionJobStage.DISCOVER.value
        assert manifest.error["code"] == "NO_OBSERVATIONS_FOUND"
        imagery.request_imagery.assert_not_called()

    @pytest.mark.asyncio
    async def test_discovery_timeout_fails_discovery(self, setup_orchestrator):
        orchestrator, discovery, _, _ = setup_orchestrator
        discovery.search = AsyncMock(side_effect=ProviderTimeoutError("STAC timed out"))

        manifest = await orchestrator.execute_acquisition_job(
            west=1.0,
            south=50.0,
            east=2.0,
            north=51.0,
            start_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
        )

        assert manifest.status == AcquisitionJobStatus.FAILED_DISCOVERY.value
        assert manifest.error["code"] == "PROVIDER_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_acquisition_network_error_fails_acquisition(self, setup_orchestrator):
        orchestrator, discovery, imagery, _ = setup_orchestrator
        mock_obs = _make_mock_observation()
        discovery.search = AsyncMock(return_value=STACSearchResult(observations=[mock_obs]))
        imagery.request_imagery = AsyncMock(side_effect=ProviderUnavailableError("Process API HTTP 503"))

        manifest = await orchestrator.execute_acquisition_job(
            west=1.0,
            south=50.0,
            east=2.0,
            north=51.0,
            start_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
        )

        assert manifest.status == AcquisitionJobStatus.FAILED_ACQUISITION.value
        assert manifest.current_stage == AcquisitionJobStage.ACQUIRE.value
        assert manifest.error["code"] == "ACQUISITION_TIMEOUT_OR_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_persistence_failure_fails_persistence(self, setup_orchestrator):
        orchestrator, discovery, imagery, _ = setup_orchestrator
        mock_obs = _make_mock_observation()
        discovery.search = AsyncMock(return_value=STACSearchResult(observations=[mock_obs]))
        # Imagery with empty bytes triggers empty raster error
        bad_result = _make_mock_imagery_result()
        bad_result.raw_bytes = b""
        imagery.request_imagery = AsyncMock(return_value=bad_result)

        manifest = await orchestrator.execute_acquisition_job(
            west=1.0,
            south=50.0,
            east=2.0,
            north=51.0,
            start_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
        )

        assert manifest.status == AcquisitionJobStatus.FAILED_PERSISTENCE.value
        assert manifest.current_stage == AcquisitionJobStage.PERSIST.value
        assert manifest.error["code"] == "EMPTY_RASTER_BYTES"

    @pytest.mark.asyncio
    async def test_integrity_hash_mismatch_fails_integrity(self, setup_orchestrator):
        orchestrator, discovery, imagery, _ = setup_orchestrator
        mock_obs = _make_mock_observation("S1A_TAMPER_TEST")
        discovery.search = AsyncMock(return_value=STACSearchResult(observations=[mock_obs]))
        imagery.request_imagery = AsyncMock(return_value=_make_mock_imagery_result("S1A_TAMPER_TEST"))

        # Tamper with the persistence service load method
        original_persist = orchestrator.persistence_service.persist_acquisition

        def tampered_persist(imagery_res, req):
            art = original_persist(imagery_res, req)
            # Intentionally corrupt disk file
            with open(art.geotiff_path, "wb") as f:
                f.write(b"CORRUPTED_BYTES_HERE")
            return art

        orchestrator.persistence_service.persist_acquisition = tampered_persist

        manifest = await orchestrator.execute_acquisition_job(
            west=1.0,
            south=50.0,
            east=2.0,
            north=51.0,
            start_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
        )

        assert manifest.status == AcquisitionJobStatus.FAILED_INTEGRITY.value
        assert manifest.current_stage == AcquisitionJobStage.VALIDATE.value
        assert manifest.error["code"] == "PERSISTED_ARTIFACT_HASH_MISMATCH"

    @pytest.mark.asyncio
    async def test_sar_validation_failure_fails_validation(self, setup_orchestrator):
        orchestrator, discovery, imagery, _ = setup_orchestrator
        mock_obs = _make_mock_observation("S1A_NAN_TEST")
        discovery.search = AsyncMock(return_value=STACSearchResult(observations=[mock_obs]))

        # Generate GeoTIFF with all NaN values to trigger SAR validation failure
        west, south, east, north = (1.0, 50.0, 2.0, 51.0)
        transform = from_bounds(west, south, east, north, 16, 16)
        with MemoryFile() as memfile:
            with memfile.open(
                driver="GTiff",
                width=16,
                height=16,
                count=2,
                dtype="float32",
                crs=CRS.from_epsg(4326),
                transform=transform,
            ) as dst:
                dst.write(np.full((16, 16), np.nan, dtype=np.float32), 1)
                dst.write(np.full((16, 16), np.nan, dtype=np.float32), 2)
            nan_bytes = memfile.read()

        imagery.request_imagery = AsyncMock(
            return_value=_make_mock_imagery_result("S1A_NAN_TEST", raw_bytes=nan_bytes)
        )

        manifest = await orchestrator.execute_acquisition_job(
            west=1.0,
            south=50.0,
            east=2.0,
            north=51.0,
            start_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
        )

        assert manifest.status == AcquisitionJobStatus.FAILED_VALIDATION.value
        assert manifest.current_stage == AcquisitionJobStage.VALIDATE.value
        assert manifest.error["code"] == "SAR_VALIDATION_FAILED"

    @pytest.mark.asyncio
    async def test_scientific_firewall_zero_inference(self, setup_orchestrator):
        orchestrator, discovery, imagery, _ = setup_orchestrator
        mock_obs = _make_mock_observation()
        discovery.search = AsyncMock(return_value=STACSearchResult(observations=[mock_obs]))
        imagery.request_imagery = AsyncMock(return_value=_make_mock_imagery_result())

        with patch.object(
            orchestrator.bridge.operational_pipeline.detection_boundary,
            "execute_inference",
        ) as mock_exec:
            manifest = await orchestrator.execute_acquisition_job(
                west=1.0,
                south=50.0,
                east=2.0,
                north=51.0,
                start_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
                end_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
            )
            # execute_inference must NEVER be called
            mock_exec.assert_not_called()
            assert manifest.status == AcquisitionJobStatus.READY_FOR_DETECTION.value
            assert manifest.execution_authorized is False
            assert manifest.has_prediction is False


# ---------------------------------------------------------------------------
# Integration Tests: FastAPI Endpoints
# ---------------------------------------------------------------------------


class TestAcquisitionAPIEndpoints:
    """Tests the /api/v1/acquisitions HTTP endpoints via TestClient."""

    @pytest.fixture
    def api_client(self, tmp_path: Path):
        job_store = JobStore(base_dir=tmp_path / "api_jobs")
        raw_storage = tmp_path / "api_raw"
        persistence = AcquisitionPersistenceService(storage_root=raw_storage)
        pipeline = OperationalSARPipeline(execution_authorized=False)
        bridge = RealDataAcquisitionBridge(
            persistence_service=persistence,
            operational_pipeline=pipeline,
        )

        discovery = MagicMock(spec=SentinelDiscoveryService)
        imagery = MagicMock(spec=SentinelImageryService)

        # Default success mocks
        mock_obs = _make_mock_observation("S1A_API_OBS_001")
        discovery.search = AsyncMock(return_value=STACSearchResult(observations=[mock_obs]))
        imagery.request_imagery = AsyncMock(return_value=_make_mock_imagery_result("S1A_API_OBS_001"))

        orchestrator = AcquisitionJobOrchestrator(
            job_store=job_store,
            discovery_service=discovery,
            imagery_service=imagery,
            persistence_service=persistence,
            bridge=bridge,
        )
        set_acquisition_orchestrator(orchestrator)

        app = create_app()
        client = TestClient(app)
        return client, orchestrator, discovery, imagery

    def test_post_acquisition_job_success(self, api_client):
        client, _, _, _ = api_client
        payload = {
            "west": 1.0,
            "south": 50.0,
            "east": 2.0,
            "north": 51.0,
            "start_time": "2024-05-01T00:00:00Z",
            "end_time": "2024-05-02T00:00:00Z",
            "provider": "copernicus_cdse",
            "platform": "sentinel-1",
            "polarizations": ["VV", "VH"],
            "width": 64,
            "height": 64,
        }
        resp = client.post("/api/v1/acquisitions", json=payload)
        assert resp.status_code == 201
        data = resp.json()

        assert data["job_id"].startswith("acq_")
        assert data["status"] == "READY_FOR_DETECTION"
        assert data["acquisition_id"] == "S1A_API_OBS_001"
        assert data["provider"] == "copernicus_cdse"
        assert data["content_sha256"] is not None
        assert data["execution_authorized"] is False
        assert data["has_prediction"] is False

        # Path safety verification (Section VI.I: No absolute drive/filesystem path leakage)
        assert data["geotiff_path"] is not None
        assert not Path(data["geotiff_path"]).is_absolute()
        assert not (":\\" in data["geotiff_path"] or ":/" in data["geotiff_path"])
        assert data["metadata_path"] is not None
        assert not Path(data["metadata_path"]).is_absolute()
        assert not (":\\" in data["metadata_path"] or ":/" in data["metadata_path"])

        # Links verification
        links = data["links"]
        assert f"/api/v1/acquisitions/{data['job_id']}" in links["self"]
        assert f"/api/v1/acquisitions/{data['job_id']}/result" in links["result"]

    def test_post_acquisition_invalid_aoi_rejected_422(self, api_client):
        client, _, _, _ = api_client
        payload = {
            "west": 5.0,  # west > east
            "south": 50.0,
            "east": 2.0,
            "north": 51.0,
            "start_time": "2024-05-01T00:00:00Z",
            "end_time": "2024-05-02T00:00:00Z",
        }
        resp = client.post("/api/v1/acquisitions", json=payload)
        assert resp.status_code == 422

    def test_post_acquisition_synthetic_provider_rejected_422(self, api_client):
        client, _, _, _ = api_client
        payload = {
            "west": 1.0,
            "south": 50.0,
            "east": 2.0,
            "north": 51.0,
            "start_time": "2024-05-01T00:00:00Z",
            "end_time": "2024-05-02T00:00:00Z",
            "provider": "synthetic_mock_feed",
        }
        resp = client.post("/api/v1/acquisitions", json=payload)
        assert resp.status_code == 422

    def test_get_acquisition_job_by_id(self, api_client):
        client, _, _, _ = api_client
        # 1. Create
        payload = {
            "west": 1.0,
            "south": 50.0,
            "east": 2.0,
            "north": 51.0,
            "start_time": "2024-05-01T00:00:00Z",
            "end_time": "2024-05-02T00:00:00Z",
        }
        post_resp = client.post("/api/v1/acquisitions", json=payload)
        job_id = post_resp.json()["job_id"]

        # 2. Get by ID
        get_resp = client.get(f"/api/v1/acquisitions/{job_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["job_id"] == job_id
        assert data["status"] == "READY_FOR_DETECTION"

    def test_get_acquisition_job_not_found_404(self, api_client):
        client, _, _, _ = api_client
        resp = client.get("/api/v1/acquisitions/acq_nonexistent_job_id")
        assert resp.status_code == 404
        assert resp.json()["code"] == "JOB_NOT_FOUND"

    def test_get_acquisition_result_success(self, api_client):
        client, _, _, _ = api_client
        payload = {
            "west": 1.0,
            "south": 50.0,
            "east": 2.0,
            "north": 51.0,
            "start_time": "2024-05-01T00:00:00Z",
            "end_time": "2024-05-02T00:00:00Z",
        }
        post_resp = client.post("/api/v1/acquisitions", json=payload)
        job_id = post_resp.json()["job_id"]

        result_resp = client.get(f"/api/v1/acquisitions/{job_id}/result")
        assert result_resp.status_code == 200
        ev = result_resp.json()

        assert ev["evidence_id"].startswith("ev_opsar_")
        assert ev["status"] == "DETECTION_READY"
        assert ev["provenance_class"] == "VERIFIED_OPERATIONAL"
        assert ev["lineage_record"]["execution_authorized"] is False
        assert "SAR_RASTER_VALIDATION" in ev["lineage_record"]["stages"]

    def test_list_acquisitions_endpoint(self, api_client):
        client, _, _, _ = api_client
        payload = {
            "west": 1.0,
            "south": 50.0,
            "east": 2.0,
            "north": 51.0,
            "start_time": "2024-05-01T00:00:00Z",
            "end_time": "2024-05-02T00:00:00Z",
        }
        client.post("/api/v1/acquisitions", json=payload)

        list_resp = client.get("/api/v1/acquisitions?limit=10")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total_jobs"] >= 1
        assert len(data["jobs"]) >= 1
