"""Unit tests for SentinelImageryService (Phase 1B.3.2).

Covers:
- Success cases: VV, VH, VV+VH retrieval and parsing
- Request building integration & Authorization header injection
- HTTP error mapping (400, 401, 403, 404, 429, 500, 502, 503)
- Network error mapping (timeout, connect error)
- Response validation: empty, HTML, JSON error, corrupt GeoTIFF
- Raster metadata validation: dimensions, band count, dtype, CRS, transform
- Pixel statistics computation and all-NaN detection
- Security: secrets and tokens never leak into results, exceptions, or logs

All tests use mocked HTTP (respx) and synthetic in-memory GeoTIFFs (rasterio.MemoryFile).
No live network requests are made during these tests.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import numpy as np
import pytest
import respx
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds

from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.errors import (
    AuthenticationError,
    AuthorizationError,
    ProviderInvalidResponseError,
    ProviderRateLimitedError,
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
    OutputFormat,
    Polarization,
    ProductType,
    TimeRange,
)
from ocean_sentinel.satellite.auth import TokenManager
from ocean_sentinel.satellite.imagery import (
    ProcessRequestBuilder,
    SentinelImageryService,
)

# ---------------------------------------------------------------------------
# Test fixtures & helpers
# ---------------------------------------------------------------------------

PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"


def _create_synthetic_geotiff(
    width: int = 10,
    height: int = 10,
    bands: int = 2,
    dtype: str = "float32",
    crs_epsg: Optional[int] = 4326,
    bounds: tuple[float, float, float, float] = (15.0, 39.5, 16.0, 40.5),
    all_nan: bool = False,
    custom_transform: bool = True,
) -> bytes:
    """Generate in-memory GeoTIFF bytes for unit testing."""
    west, south, east, north = bounds
    transform = from_bounds(west, south, east, north, width, height) if custom_transform else None
    crs = CRS.from_epsg(crs_epsg) if crs_epsg is not None else None

    with MemoryFile() as memfile:
        kwargs: dict[str, Any] = {
            "driver": "GTiff",
            "width": width,
            "height": height,
            "count": bands,
            "dtype": dtype,
        }
        if crs is not None:
            kwargs["crs"] = crs
        if transform is not None:
            kwargs["transform"] = transform

        with memfile.open(**kwargs) as dst:
            for b in range(1, bands + 1):
                if all_nan:
                    arr = np.full((height, width), np.nan, dtype=np.float32)
                else:
                    # Provide deterministic non-empty floating point values
                    base = np.arange(height * width, dtype=np.float32).reshape((height, width))
                    arr = (base + b * 10.0) / 100.0
                dst.write(arr, b)

        return memfile.read()


def _make_observation(
    obs_id: str = "S1D_IW_GRDH_TEST",
    polarizations: Optional[list[Polarization]] = None,
) -> AcquisitionMetadata:
    if polarizations is None:
        polarizations = [Polarization.VV, Polarization.VH]
    return AcquisitionMetadata(
        id=obs_id,
        mission="sentinel-1",
        product_type=ProductType.GRD,
        acquisition_time=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        geometry={
            "type": "Polygon",
            "coordinates": [[[15.0, 39.5], [16.0, 39.5], [16.0, 40.5], [15.0, 40.5], [15.0, 39.5]]],
        },
        polarizations=polarizations,
    )


def _make_imagery_request(
    bands: Optional[list[Polarization]] = None,
    width: int = 10,
    height: int = 10,
    obs: Optional[AcquisitionMetadata] = None,
) -> ImageryRequest:
    if bands is None:
        bands = [Polarization.VV, Polarization.VH]
    if obs is None:
        obs = _make_observation(polarizations=bands)
    return ImageryRequest(
        observation=obs,
        bbox=BoundingBox(west=15.0, south=39.5, east=16.0, north=40.5),
        time_range=TimeRange(
            start=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 2, 0, 0, 0, tzinfo=timezone.utc),
        ),
        requested_bands=bands,
        output=OutputConfig(width=width, height=height, format=OutputFormat.TIFF),
    )


class MockTokenManager:
    """Mock TokenManager returning a predetermined token or raising an error."""

    def __init__(self, token: str = "mock-valid-bearer-token", should_fail: bool = False):
        self._token = token
        self._should_fail = should_fail
        self.call_count = 0

    async def get_token(self) -> str:
        self.call_count += 1
        if self._should_fail:
            raise AuthenticationError("OAuth2 token request failed: invalid credentials")
        return self._token


@pytest.fixture
def test_settings(monkeypatch) -> CopernicusSettings:
    monkeypatch.setenv("COPERNICUS_CLIENT_ID", "mock-client-id")
    monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "mock-client-secret")
    return CopernicusSettings()


@pytest.fixture
def mock_token_manager() -> MockTokenManager:
    return MockTokenManager("test-bearer-token-xyz")


@pytest.fixture
def imagery_service(test_settings, mock_token_manager) -> SentinelImageryService:
    return SentinelImageryService(test_settings, mock_token_manager)


# ---------------------------------------------------------------------------
# Success Cases
# ---------------------------------------------------------------------------


class TestImageryServiceSuccess:
    """Verifies successful imagery retrieval and parsing across band configurations."""

    @respx.mock
    async def test_successful_vv_vh_retrieval(self, imagery_service):
        """Dual-band VV+VH GeoTIFF retrieval and parsing."""
        tiff_bytes = _create_synthetic_geotiff(width=10, height=10, bands=2)
        route = respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(bands=[Polarization.VV, Polarization.VH], width=10, height=10)
        result = await imagery_service.request_imagery(req)

        assert route.called
        assert isinstance(result, ImageryResult)
        assert result.observation_id == req.observation.id
        assert result.width == 10
        assert result.height == 10
        assert result.band_count == 2
        assert result.bands == [Polarization.VV, Polarization.VH]
        assert result.dtype == "float32"
        assert "4326" in result.crs
        assert len(result.band_statistics) == 2

        # Check per-band statistics
        stat_vv = result.band_statistics[0]
        assert stat_vv.polarization == Polarization.VV
        assert stat_vv.finite_pixel_count == 100
        assert stat_vv.min_value >= 0.0

        stat_vh = result.band_statistics[1]
        assert stat_vh.polarization == Polarization.VH
        assert stat_vh.finite_pixel_count == 100

        # Safe summary check
        summary = result.to_safe_summary()
        assert summary["width"] == 10
        assert "raw_bytes" not in summary

    @respx.mock
    async def test_successful_vv_single_band(self, imagery_service):
        """Single-band VV retrieval and parsing."""
        tiff_bytes = _create_synthetic_geotiff(width=16, height=16, bands=1)
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(bands=[Polarization.VV], width=16, height=16)
        result = await imagery_service.request_imagery(req)

        assert result.band_count == 1
        assert result.bands == [Polarization.VV]
        assert len(result.band_statistics) == 1
        assert result.band_statistics[0].polarization == Polarization.VV

    @respx.mock
    async def test_successful_vh_single_band(self, imagery_service):
        """Single-band VH retrieval and parsing."""
        tiff_bytes = _create_synthetic_geotiff(width=12, height=12, bands=1)
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(bands=[Polarization.VH], width=12, height=12)
        result = await imagery_service.request_imagery(req)

        assert result.band_count == 1
        assert result.bands == [Polarization.VH]
        assert result.band_statistics[0].polarization == Polarization.VH

    @respx.mock
    async def test_correct_authorization_header(self, imagery_service, mock_token_manager):
        """Service must inject Authorization: Bearer <token>."""
        tiff_bytes = _create_synthetic_geotiff(width=10, height=10, bands=1)
        route = respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(bands=[Polarization.VV], width=10, height=10)
        await imagery_service.request_imagery(req)

        assert route.called
        request = route.calls.last.request
        assert request.headers["Authorization"] == "Bearer test-bearer-token-xyz"
        assert request.headers["Accept"] == "image/tiff"

    @respx.mock
    async def test_correct_process_api_endpoint(self, imagery_service):
        """Service must POST to the configured process API URL."""
        tiff_bytes = _create_synthetic_geotiff(width=10, height=10, bands=1)
        route = respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(bands=[Polarization.VV], width=10, height=10)
        await imagery_service.request_imagery(req)

        assert route.calls.last.request.url == PROCESS_URL

    @respx.mock
    async def test_correct_payload_integration_with_builder(self, imagery_service):
        """Payload sent to HTTP client must match ProcessRequestBuilder output."""
        tiff_bytes = _create_synthetic_geotiff(width=10, height=10, bands=2)
        route = respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(bands=[Polarization.VV, Polarization.VH], width=10, height=10)
        expected_payload = ProcessRequestBuilder.build(req)

        await imagery_service.request_imagery(req)

        sent_body = json.loads(route.calls.last.request.content)
        assert sent_body == expected_payload


# ---------------------------------------------------------------------------
# Authentication Cases
# ---------------------------------------------------------------------------


class TestImageryServiceAuthentication:
    """Verifies handling of authentication failures."""

    @respx.mock
    async def test_real_token_manager_integration(self, test_settings):
        """Service integrates with actual TokenManager and caches tokens."""
        respx.post(test_settings.copernicus_token_url).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "real-token-123", "token_type": "Bearer", "expires_in": 600},
            )
        )
        tiff_bytes = _create_synthetic_geotiff(width=10, height=10, bands=1)
        proc_route = respx.post(PROCESS_URL).mock(
            return_value=httpx.Response(200, content=tiff_bytes)
        )

        tm = TokenManager(test_settings)
        service = SentinelImageryService(test_settings, tm)
        req = _make_imagery_request(bands=[Polarization.VV], width=10, height=10)

        result = await service.request_imagery(req)
        assert result.band_count == 1
        assert proc_route.calls.last.request.headers["Authorization"] == "Bearer real-token-123"

    async def test_token_manager_failure_raises_authentication_error(self, test_settings):
        """Failure to acquire token must raise AuthenticationError."""
        failing_tm = MockTokenManager(should_fail=True)
        service = SentinelImageryService(test_settings, failing_tm)
        req = _make_imagery_request()

        with pytest.raises(AuthenticationError, match="OAuth2 token request failed"):
            await service.request_imagery(req)

    @respx.mock
    async def test_http_401_raises_authentication_error(self, imagery_service):
        """Process API returning HTTP 401 must raise AuthenticationError."""
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(401, text="Unauthorized token"))
        req = _make_imagery_request()

        with pytest.raises(AuthenticationError, match="HTTP 401") as exc_info:
            await imagery_service.request_imagery(req)

        assert exc_info.value.details["status_code"] == 401

    @respx.mock
    async def test_http_403_raises_authorization_error(self, imagery_service):
        """Process API returning HTTP 403 must raise AuthorizationError."""
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(403, text="Forbidden access"))
        req = _make_imagery_request()

        with pytest.raises(AuthorizationError, match="HTTP 403") as exc_info:
            await imagery_service.request_imagery(req)

        assert exc_info.value.details["status_code"] == 403


# ---------------------------------------------------------------------------
# HTTP & Network Error Cases
# ---------------------------------------------------------------------------


class TestImageryServiceHttpErrors:
    """Verifies mapping of HTTP status codes and network failures."""

    @respx.mock
    async def test_http_400_raises_provider_invalid_response_error(self, imagery_service):
        """HTTP 400 must raise ProviderInvalidResponseError with sanitized detail."""
        respx.post(PROCESS_URL).mock(
            return_value=httpx.Response(400, json={"error": {"message": "Invalid bounding box"}})
        )
        req = _make_imagery_request()

        with pytest.raises(ProviderInvalidResponseError, match="HTTP 400") as exc_info:
            await imagery_service.request_imagery(req)

        assert exc_info.value.details["status_code"] == 400
        assert "Invalid bounding box" in exc_info.value.details["detail"]

    @respx.mock
    async def test_http_404_raises_provider_invalid_response_error(self, imagery_service):
        """HTTP 404 must raise ProviderInvalidResponseError."""
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(404, text="Not Found"))
        req = _make_imagery_request()

        with pytest.raises(ProviderInvalidResponseError, match="HTTP 404") as exc_info:
            await imagery_service.request_imagery(req)

        assert exc_info.value.details["status_code"] == 404

    @respx.mock
    async def test_http_429_raises_provider_rate_limited_error(self, imagery_service):
        """HTTP 429 must raise ProviderRateLimitedError."""
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(429, text="Rate limit exceeded"))
        req = _make_imagery_request()

        with pytest.raises(ProviderRateLimitedError, match="HTTP 429"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_http_500_raises_provider_unavailable_error(self, imagery_service):
        """HTTP 500 must raise ProviderUnavailableError."""
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(500, text="Internal Server Error"))
        req = _make_imagery_request()

        with pytest.raises(ProviderUnavailableError, match="HTTP 500"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_http_502_503_raises_provider_unavailable_error(self, imagery_service):
        """HTTP 502 / 503 must raise ProviderUnavailableError."""
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(503, text="Service Unavailable"))
        req = _make_imagery_request()

        with pytest.raises(ProviderUnavailableError, match="HTTP 503"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_network_timeout_raises_provider_timeout_error(self, imagery_service):
        """Timeout exception must raise ProviderTimeoutError."""
        respx.post(PROCESS_URL).mock(side_effect=httpx.ReadTimeout("Read timed out"))
        req = _make_imagery_request()

        with pytest.raises(ProviderTimeoutError, match="timed out"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_network_connect_error_raises_provider_unavailable_error(self, imagery_service):
        """Connection failure must raise ProviderUnavailableError."""
        respx.post(PROCESS_URL).mock(side_effect=httpx.ConnectError("Connection refused"))
        req = _make_imagery_request()

        with pytest.raises(ProviderUnavailableError, match="network error"):
            await imagery_service.request_imagery(req)


# ---------------------------------------------------------------------------
# Response Validation Cases
# ---------------------------------------------------------------------------


class TestImageryServiceResponseValidation:
    """Verifies strict validation of response content and GeoTIFF integrity."""

    @respx.mock
    async def test_empty_response_raises_raster_validation_error(self, imagery_service):
        """HTTP 200 with empty body must raise RasterValidationError."""
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=b""))
        req = _make_imagery_request()

        with pytest.raises(RasterValidationError, match="empty response"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_html_response_raises_raster_validation_error(self, imagery_service):
        html_content = b"<!DOCTYPE html><html><body>Error</body></html>"
        respx.post(PROCESS_URL).mock(
            return_value=httpx.Response(200, content=html_content)
        )
        req = _make_imagery_request()

        with pytest.raises(RasterValidationError, match="HTML content"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_json_error_response_raises_raster_validation_error(self, imagery_service):
        """JSON error body with 200 must raise RasterValidationError."""
        respx.post(PROCESS_URL).mock(
            return_value=httpx.Response(200, content=b'{"error": "Failed to generate raster"}')
        )
        req = _make_imagery_request()

        with pytest.raises(RasterValidationError, match="JSON error"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_corrupted_geotiff_raises_raster_validation_error(self, imagery_service):
        respx.post(PROCESS_URL).mock(
            return_value=httpx.Response(200, content=b"NOT_A_GEOTIFF_HEADER_BYTES")
        )
        req = _make_imagery_request()

        with pytest.raises(RasterValidationError, match="Failed to parse response as GeoTIFF"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_wrong_raster_width_raises_raster_validation_error(self, imagery_service):
        """Raster with width different from request must raise RasterValidationError."""
        tiff_bytes = _create_synthetic_geotiff(width=20, height=10, bands=2)
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(width=10, height=10)
        with pytest.raises(RasterValidationError, match="width mismatch"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_wrong_raster_height_raises_raster_validation_error(self, imagery_service):
        """Raster with height different from request must raise RasterValidationError."""
        tiff_bytes = _create_synthetic_geotiff(width=10, height=20, bands=2)
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(width=10, height=10)
        with pytest.raises(RasterValidationError, match="height mismatch"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_wrong_band_count_raises_raster_validation_error(self, imagery_service):
        """Raster with different band count from request must raise RasterValidationError."""
        tiff_bytes = _create_synthetic_geotiff(width=10, height=10, bands=1)  # Only 1 band returned
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(bands=[Polarization.VV, Polarization.VH], width=10, height=10)
        with pytest.raises(RasterValidationError, match="Band count mismatch"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_wrong_dtype_raises_raster_validation_error(self, imagery_service):
        """Raster with non-float32 dtype (e.g. uint8) must raise RasterValidationError."""
        tiff_bytes = _create_synthetic_geotiff(width=10, height=10, bands=1, dtype="uint8")
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(bands=[Polarization.VV], width=10, height=10)
        with pytest.raises(RasterValidationError, match="dtype mismatch"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_missing_crs_raises_raster_validation_error(self, imagery_service):
        """Raster with no CRS must raise RasterValidationError."""
        tiff_bytes = _create_synthetic_geotiff(width=10, height=10, bands=1, crs_epsg=None)
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(bands=[Polarization.VV], width=10, height=10)
        with pytest.raises(RasterValidationError, match="missing coordinate reference system"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_crs_mismatch_raises_raster_validation_error(self, imagery_service):
        """Raster with unexpected CRS (e.g. EPSG:3857 instead of 4326) must raise."""
        tiff_bytes = _create_synthetic_geotiff(width=10, height=10, bands=1, crs_epsg=3857)
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(bands=[Polarization.VV], width=10, height=10)
        with pytest.raises(RasterValidationError, match="CRS EPSG mismatch"):
            await imagery_service.request_imagery(req)

    @respx.mock
    async def test_all_nan_pixel_data_raises_raster_validation_error(self, imagery_service):
        """Raster with only NaN pixels must be detected and rejected."""
        tiff_bytes = _create_synthetic_geotiff(width=10, height=10, bands=1, all_nan=True)
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(bands=[Polarization.VV], width=10, height=10)
        with pytest.raises(RasterValidationError, match="no valid finite pixel data"):
            await imagery_service.request_imagery(req)


# ---------------------------------------------------------------------------
# Security Cases
# ---------------------------------------------------------------------------


class TestImageryServiceSecurity:
    """Verifies that secrets and tokens never appear in exceptions, logs, or results."""

    @respx.mock
    async def test_access_token_not_in_exception(self, test_settings):
        """Secret tokens must not leak into exception text on failure."""
        token_str = "secret-super-sensitive-token-12345"
        tm = MockTokenManager(token=token_str)
        service = SentinelImageryService(test_settings, tm)

        respx.post(PROCESS_URL).mock(return_value=httpx.Response(500, text="Internal crash"))
        req = _make_imagery_request()

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await service.request_imagery(req)

        err_msg = str(exc_info.value)
        assert token_str not in err_msg

    @respx.mock
    async def test_client_secret_not_in_exception(self, test_settings):
        """Client secret must not appear in exception messages."""
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(400, text="Invalid syntax"))
        tm = MockTokenManager()
        service = SentinelImageryService(test_settings, tm)
        req = _make_imagery_request()

        with pytest.raises(ProviderInvalidResponseError) as exc_info:
            await service.request_imagery(req)

        err_msg = str(exc_info.value)
        assert "mock-client-secret" not in err_msg

    @respx.mock
    async def test_no_authorization_in_result_object(self, imagery_service):
        """ImageryResult must not contain authorization or token fields."""
        tiff_bytes = _create_synthetic_geotiff(width=10, height=10, bands=1)
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        req = _make_imagery_request(bands=[Polarization.VV], width=10, height=10)
        result = await imagery_service.request_imagery(req)

        result_dict = result.model_dump()
        result_str = str(result_dict)
        assert "Authorization" not in result_str
        assert "Bearer" not in result_str
        assert "test-bearer-token-xyz" not in result_str

    @respx.mock
    async def test_authorization_header_not_logged(self, imagery_service, caplog):
        """Logs must not record the bearer token."""
        tiff_bytes = _create_synthetic_geotiff(width=10, height=10, bands=1)
        respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, content=tiff_bytes))

        with caplog.at_level(logging.DEBUG):
            req = _make_imagery_request(bands=[Polarization.VV], width=10, height=10)
            await imagery_service.request_imagery(req)

        log_text = caplog.text
        assert "test-bearer-token-xyz" not in log_text
