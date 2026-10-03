"""Unit and integration tests for Real-Data Acquisition & Persistence Boundary (Phase 6B).

Verifies:
- Valid real-provider acquisition metadata persistence
- Rejection of missing acquisition identity
- Rejection of synthetic/mock/demo providers (fail-closed)
- Rejection of missing source references
- Atomic disk persistence of GeoTIFF and metadata sidecar
- SHA-256 cryptographic binding and detection of tampered disk files
- Seamless handoff into Phase 6 OperationalSARPipeline without bypassing contracts
- Explicit fail-closed mapping on external provider network/timeout failures
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from typing import Any, Dict

import httpx
import numpy as np
import pytest
import respx
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds

from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.errors import (
    ProviderTimeoutError,
    ProviderUnavailableError,
    RasterValidationError,
)
from ocean_sentinel.models import (
    AcquisitionMetadata,
    BoundingBox,
    ImageryRequest,
    ImageryResult,
    OutputConfig,
    Polarization,
    ProductType,
    TimeRange,
)
from ocean_sentinel.operational_pipeline import (
    DEFAULT_CHECKPOINT_PATH,
    OperationalEvidenceResult,
    OperationalSARPipeline,
)
from ocean_sentinel.satellite.auth import TokenManager
from ocean_sentinel.satellite.imagery import SentinelImageryService
from ocean_sentinel.satellite.persistence import (
    AcquisitionPersistenceService,
    MissingAcquisitionIdentityError,
    MissingSourceReferenceError,
    PersistedAcquisitionArtifact,
    PersistenceError,
    PersistenceIntegrityError,
    RasterMaterializationError,
    RealDataAcquisitionBridge,
    UnauthorizedProviderError,
)


def _create_sample_geotiff_bytes(
    width: int = 64,
    height: int = 64,
    bands: int = 2,
    crs_epsg: int = 4326,
    bounds: tuple[float, float, float, float] = (-79.5, -8.5, -78.5, -7.5),
) -> bytes:
    """Generate in-memory valid GeoTIFF bytes for unit testing."""
    west, south, east, north = bounds
    transform = from_bounds(west, south, east, north, width, height)
    crs = CRS.from_epsg(crs_epsg)

    with MemoryFile() as memfile:
        kwargs: dict[str, Any] = {
            "driver": "GTiff",
            "width": width,
            "height": height,
            "count": bands,
            "dtype": "float32",
            "crs": crs,
            "transform": transform,
        }
        with memfile.open(**kwargs) as dst:
            np.random.seed(123)
            for b in range(1, bands + 1):
                # Exponential positive backscatter (typical SAR linear intensity)
                arr = np.random.exponential(scale=0.01 * b, size=(height, width)).astype(np.float32) + 1e-4
                dst.write(arr, b)
        return memfile.read()


@pytest.fixture
def sample_geotiff_bytes() -> bytes:
    return _create_sample_geotiff_bytes()


@pytest.fixture
def sample_imagery_request() -> ImageryRequest:
    obs = AcquisitionMetadata(
        id="S1A_IW_GRDH_1SDV_20220115T221530_20220115T221555_041464_04EE34_12AB",
        mission="sentinel-1",
        product_type=ProductType.GRD,
        acquisition_time=datetime(2022, 1, 15, 22, 15, 30, tzinfo=timezone.utc),
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [-79.5, -8.5],
                [-78.5, -8.5],
                [-78.5, -7.5],
                [-79.5, -7.5],
                [-79.5, -8.5],
            ]],
        },
        bbox=[-79.5, -8.5, -78.5, -7.5],
        polarizations=[Polarization.VH, Polarization.VV],
        provider="copernicus_cdse",
        source_reference="https://browser.dataspace.copernicus.eu/items/S1A_IW_GRDH_12AB",
    )
    return ImageryRequest(
        observation=obs,
        bbox=BoundingBox(west=-79.5, south=-8.5, east=-78.5, north=-7.5),
        time_range=TimeRange(
            start=datetime(2022, 1, 15, 22, 0, 0, tzinfo=timezone.utc),
            end=datetime(2022, 1, 15, 23, 0, 0, tzinfo=timezone.utc),
        ),
        requested_bands=[Polarization.VH, Polarization.VV],
        output=OutputConfig(width=64, height=64, crs_epsg=4326),
    )


@pytest.fixture
def sample_imagery_result(sample_geotiff_bytes, sample_imagery_request) -> ImageryResult:
    return ImageryResult(
        observation_id=sample_imagery_request.observation.id,
        width=64,
        height=64,
        band_count=2,
        bands=[Polarization.VH, Polarization.VV],
        dtype="float32",
        crs="EPSG:4326",
        bounds=[-79.5, -8.5, -78.5, -7.5],
        transform=[0.015625, 0.0, -79.5, 0.0, -0.015625, -7.5],
        raw_bytes=sample_geotiff_bytes,
    )


# ---------------------------------------------------------------------------
# Test Persistence Service Contracts
# ---------------------------------------------------------------------------


class TestAcquisitionPersistenceService:
    """Tests atomic disk persistence and cryptographic binding."""

    def test_persist_and_load_success(self, sample_imagery_result, sample_imagery_request):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AcquisitionPersistenceService(storage_root=tmpdir)
            artifact = service.persist_acquisition(sample_imagery_result, sample_imagery_request)

            assert isinstance(artifact, PersistedAcquisitionArtifact)
            assert artifact.acquisition_id == sample_imagery_request.observation.id
            assert artifact.provider == "copernicus_cdse"
            assert artifact.source_reference == sample_imagery_request.observation.source_reference
            assert Path(artifact.geotiff_path).is_file()
            assert Path(artifact.metadata_path).is_file()
            assert len(artifact.content_sha256) == 64

            # Load and verify
            loaded_art, channel_arrays = service.load_persisted_acquisition(artifact.acquisition_id)
            assert loaded_art.content_sha256 == artifact.content_sha256
            assert Polarization.VH in channel_arrays
            assert Polarization.VV in channel_arrays
            assert channel_arrays[Polarization.VH].shape == (64, 64)
            assert channel_arrays[Polarization.VV].shape == (64, 64)

    def test_missing_acquisition_id_fails_closed(self, sample_imagery_result, sample_imagery_request):
        sample_imagery_result.observation_id = ""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AcquisitionPersistenceService(storage_root=tmpdir)
            with pytest.raises(MissingAcquisitionIdentityError) as exc_info:
                service.persist_acquisition(sample_imagery_result, sample_imagery_request)
            assert exc_info.value.code == "MISSING_ACQUISITION_ID"

    def test_synthetic_provider_rejected_fail_closed(self, sample_imagery_result, sample_imagery_request):
        sample_imagery_request.observation.provider = "synthetic_fixture_generator"
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AcquisitionPersistenceService(storage_root=tmpdir)
            with pytest.raises(UnauthorizedProviderError) as exc_info:
                service.persist_acquisition(sample_imagery_result, sample_imagery_request)
            assert exc_info.value.code == "UNAUTHORIZED_PROVIDER"

    def test_missing_source_reference_fails_closed(self, sample_imagery_result, sample_imagery_request):
        sample_imagery_request.observation.source_reference = None
        sample_imagery_request.observation.self_link = None
        sample_imagery_request.observation.source_collection = None
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AcquisitionPersistenceService(storage_root=tmpdir)
            with pytest.raises(MissingSourceReferenceError) as exc_info:
                service.persist_acquisition(sample_imagery_result, sample_imagery_request)
            assert exc_info.value.code == "MISSING_SOURCE_REFERENCE"

    def test_empty_raster_bytes_fails_closed(self, sample_imagery_result, sample_imagery_request):
        sample_imagery_result.raw_bytes = b""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AcquisitionPersistenceService(storage_root=tmpdir)
            with pytest.raises(RasterMaterializationError) as exc_info:
                service.persist_acquisition(sample_imagery_result, sample_imagery_request)
            assert exc_info.value.code == "EMPTY_RASTER_BYTES"

    def test_tampered_disk_file_detected_fail_closed(self, sample_imagery_result, sample_imagery_request):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AcquisitionPersistenceService(storage_root=tmpdir)
            artifact = service.persist_acquisition(sample_imagery_result, sample_imagery_request)

            # Corrupt the GeoTIFF on disk
            with open(artifact.geotiff_path, "wb") as f:
                f.write(b"corrupted_tampered_payload_12345")

            # Loading must fail closed on SHA256 mismatch
            with pytest.raises(PersistenceIntegrityError) as exc_info:
                service.load_persisted_acquisition(artifact.acquisition_id)
            assert exc_info.value.code == "PERSISTED_ARTIFACT_HASH_MISMATCH"

    def test_missing_metadata_sidecar_fails_closed(self, sample_imagery_result, sample_imagery_request):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AcquisitionPersistenceService(storage_root=tmpdir)
            artifact = service.persist_acquisition(sample_imagery_result, sample_imagery_request)

            # Remove metadata file
            Path(artifact.metadata_path).unlink()

            with pytest.raises(PersistenceIntegrityError) as exc_info:
                service.load_persisted_acquisition(artifact.acquisition_id)
            assert exc_info.value.code == "PERSISTED_METADATA_NOT_FOUND"


# ---------------------------------------------------------------------------
# Test Bridge & Handoff to Phase 6 Pipeline
# ---------------------------------------------------------------------------


class TestRealDataAcquisitionBridge:
    """Tests the bridge connecting persisted real EO rasters to the firewalled Phase 6 pipeline."""

    def test_persist_and_handoff_reaches_detection_ready(
        self,
        sample_imagery_result,
        sample_imagery_request,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = AcquisitionPersistenceService(storage_root=tmpdir)
            pipeline = OperationalSARPipeline(
                execution_authorized=False,
                checkpoint_path=DEFAULT_CHECKPOINT_PATH,
            )
            bridge = RealDataAcquisitionBridge(
                persistence_service=persistence,
                operational_pipeline=pipeline,
            )

            artifact, evidence = bridge.persist_and_handoff(
                sample_imagery_result, sample_imagery_request
            )

            assert isinstance(artifact, PersistedAcquisitionArtifact)
            assert isinstance(evidence, OperationalEvidenceResult)

            # Verify Pipeline status
            assert evidence.status == "DETECTION_READY"
            assert evidence.provenance_class == "VERIFIED_OPERATIONAL"
            assert evidence.acquisition_id == sample_imagery_request.observation.id

            # Verify Lineage Hierarchy: Observation → Acquisition → Raster → Preprocessing → Detection
            stages = evidence.lineage_record["stages"]
            assert stages == [
                "OBSERVATION_INGESTION",
                "SAR_RASTER_VALIDATION",
                "SAR_PREPROCESSING_MAPPING_A",
                "DETECTION_BOUNDARY_PREFLIGHT",
            ]

            # Verify Preprocessing metadata
            assert evidence.preprocessing_summary["channel_order"] == ["VH", "VV"]
            assert evidence.preprocessing_summary["normalization_contract"] == "mapping_a_zscore"

            # Verify Detection firewall
            assert evidence.detection_summary["execution_authorized"] is False
            assert evidence.detection_summary["has_prediction"] is False


# ---------------------------------------------------------------------------
# Test External Provider Fail-Closed Mapping
# ---------------------------------------------------------------------------


class TestExternalProviderFailClosed:
    """Tests that remote network/HTTP failures result in explicit failure, never fake success."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_process_api_network_failure_fails_closed(self, sample_imagery_request):
        settings = CopernicusSettings(
            copernicus_client_id="test-client-id",
            copernicus_client_secret="test-client-secret",
        )
        token_manager = TokenManager(settings)

        # Mock token endpoint
        respx.post(settings.copernicus_token_url).respond(
            200,
            json={"access_token": "valid-token", "token_type": "Bearer", "expires_in": 3600},
        )
        # Mock process API to simulate network connection drop
        respx.post(settings.copernicus_process_api_url).mock(
            side_effect=httpx.ConnectError("Connection refused by provider")
        )

        service = SentinelImageryService(settings, token_manager)

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await service.request_imagery(sample_imagery_request)

        assert "network error" in exc_info.value.message.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_process_api_timeout_fails_closed(self, sample_imagery_request):
        settings = CopernicusSettings(
            copernicus_client_id="test-client-id",
            copernicus_client_secret="test-client-secret",
        )
        token_manager = TokenManager(settings)

        respx.post(settings.copernicus_token_url).respond(
            200,
            json={"access_token": "valid-token", "token_type": "Bearer", "expires_in": 3600},
        )
        respx.post(settings.copernicus_process_api_url).mock(
            side_effect=httpx.TimeoutException("Provider request timed out after 30s")
        )

        service = SentinelImageryService(settings, token_manager)

        with pytest.raises(ProviderTimeoutError) as exc_info:
            await service.request_imagery(sample_imagery_request)

        assert "timed out" in exc_info.value.message.lower()
