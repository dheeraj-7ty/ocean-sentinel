"""Tests for Sentinel-1 STAC discovery.

Covers:
- Successful search with multiple observations
- Empty result handling
- Search input validation (AOI, datetime)
- STAC response parsing and field extraction
- Malformed STAC responses (missing fields, bad JSON, non-dict)
- HTTP error handling (400, 401, 403, 404, 429, 500, 503)
- Network failures (connection, timeout)
- Pagination (multi-page, next-link, max-page protection)
- Security: no credential/token leakage in errors

All tests use mocked HTTP — no real Copernicus contact.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
import respx

from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.errors import (
    AuthenticationError,
    InvalidAOIError,
    InvalidTimeRangeError,
    ProviderInvalidResponseError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SatelliteErrorCode,
)
from ocean_sentinel.models import (
    AcquisitionMetadata,
    BoundingBox,
    OrbitDirection,
    Polarization,
    ProductType,
    SearchRequest,
    TimeRange,
)
from ocean_sentinel.satellite.discovery import (
    STAC_COLLECTION_S1_GRD,
    STACSearchResult,
    SentinelDiscoveryService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

STAC_SEARCH_URL = "https://stac.dataspace.copernicus.eu/v1/search"


def _make_stac_item(
    item_id: str = "S1D_IW_GRDH_1SDV_20260901T164823_test",
    dt: str = "2026-09-01T16:48:23.677768Z",
    *,
    platform: str = "sentinel-1d",
    polarizations: list[str] | None = None,
    orbit_state: str = "ascending",
    relative_orbit: int = 146,
    instrument_mode: str = "IW",
    product_type: str = "IW_GRDH_1S",
    collection: str = "sentinel-1-grd",
    bbox: list[float] | None = None,
    geometry: dict | None = None,
    assets: dict | None = None,
) -> dict[str, Any]:
    """Create a realistic mock STAC item based on actual CDSE response structure."""
    if polarizations is None:
        polarizations = ["VV", "VH"]
    if bbox is None:
        bbox = [15.112, 39.815, 18.560, 41.725]
    if geometry is None:
        geometry = {
            "type": "Polygon",
            "coordinates": [[
                [15.112, 39.815],
                [18.560, 39.815],
                [18.560, 41.725],
                [15.112, 41.725],
                [15.112, 39.815],
            ]],
        }
    if assets is None:
        assets = {
            "vh": {
                "href": "s3://eodata/Sentinel-1/vh.tif",
                "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                "roles": ["data"],
            },
            "vv": {
                "href": "s3://eodata/Sentinel-1/vv.tif",
                "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                "roles": ["data"],
            },
            "thumbnail": {
                "href": "https://example.com/thumb.jpg",
                "type": "image/jpeg",
                "roles": ["thumbnail"],
            },
        }

    return {
        "type": "Feature",
        "stac_version": "1.1.0",
        "id": item_id,
        "collection": collection,
        "geometry": geometry,
        "bbox": bbox,
        "properties": {
            "datetime": dt,
            "platform": platform,
            "instruments": ["sar"],
            "constellation": "sentinel-1",
            "product:type": product_type,
            "sar:instrument_mode": instrument_mode,
            "sar:polarizations": polarizations,
            "sat:orbit_state": orbit_state,
            "sat:relative_orbit": relative_orbit,
            "processing:level": "L1",
            "sar:frequency_band": "C",
            "sar:center_frequency": 5.405,
        },
        "links": [
            {
                "rel": "self",
                "href": f"https://stac.dataspace.copernicus.eu/v1/collections/sentinel-1-grd/items/{item_id}",
            },
            {
                "rel": "collection",
                "href": "https://stac.dataspace.copernicus.eu/v1/collections/sentinel-1-grd",
            },
        ],
        "assets": assets,
    }


def _make_feature_collection(
    features: list[dict[str, Any]],
    *,
    has_next: bool = False,
    next_body: dict | None = None,
) -> dict[str, Any]:
    """Create a mock STAC FeatureCollection response."""
    links = [
        {"rel": "root", "href": "https://stac.dataspace.copernicus.eu/v1/"},
        {"rel": "self", "href": STAC_SEARCH_URL},
    ]
    if has_next:
        next_link: dict[str, Any] = {
            "rel": "next",
            "href": STAC_SEARCH_URL,
            "method": "POST",
            "type": "application/geo+json",
        }
        if next_body:
            next_link["body"] = next_body
        links.append(next_link)

    return {
        "type": "FeatureCollection",
        "numberReturned": len(features),
        "features": features,
        "links": links,
    }


@pytest.fixture
def settings(monkeypatch) -> CopernicusSettings:
    """Provide test settings with fake credentials."""
    monkeypatch.setenv("COPERNICUS_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "test-client-secret")
    return CopernicusSettings()


@pytest.fixture
def discovery(settings) -> SentinelDiscoveryService:
    """Provide a SentinelDiscoveryService with test settings."""
    return SentinelDiscoveryService(settings, max_pages=5)


@pytest.fixture
def search_request() -> SearchRequest:
    """Provide a valid search request for testing."""
    return SearchRequest(
        bbox=BoundingBox(west=15.0, south=39.5, east=16.0, north=40.5),
        time_range=TimeRange(
            start=datetime(2026, 8, 1, tzinfo=timezone.utc),
            end=datetime(2026, 9, 1, tzinfo=timezone.utc),
        ),
        max_results=10,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestDiscoverySuccess:
    """Tests for successful STAC search."""

    @respx.mock
    async def test_successful_search_multiple_observations(
        self, discovery, search_request
    ):
        """Should return parsed observations from a valid STAC response."""
        features = [
            _make_stac_item("S1D_ITEM_001", "2026-09-01T10:00:00Z"),
            _make_stac_item("S1D_ITEM_002", "2026-08-30T10:00:00Z"),
            _make_stac_item("S1D_ITEM_003", "2026-08-28T10:00:00Z"),
        ]
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection(features)
            )
        )

        result = await discovery.search(search_request)

        assert isinstance(result, STACSearchResult)
        assert result.total_returned == 3
        assert result.pages_fetched == 1
        assert not result.has_more

        obs = result.observations
        assert len(obs) == 3
        assert all(isinstance(o, AcquisitionMetadata) for o in obs)

    @respx.mock
    async def test_observation_fields_parsed(self, discovery, search_request):
        """Should correctly parse all fields from a STAC item."""
        features = [_make_stac_item()]
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection(features)
            )
        )

        result = await discovery.search(search_request)
        obs = result.observations[0]

        assert obs.id == "S1D_IW_GRDH_1SDV_20260901T164823_test"
        assert obs.mission == "sentinel-1"
        assert obs.product_type == ProductType.GRD
        assert obs.acquisition_time.year == 2026
        assert obs.acquisition_time.month == 9
        assert obs.geometry["type"] == "Polygon"
        assert obs.bbox == [15.112, 39.815, 18.560, 41.725]
        assert obs.polarizations == [Polarization.VV, Polarization.VH]
        assert obs.orbit_direction == OrbitDirection.ASCENDING
        assert obs.acquisition_mode == "IW"
        assert obs.relative_orbit == 146
        assert obs.platform == "sentinel-1d"
        assert obs.source_collection == "sentinel-1-grd"
        assert obs.self_link is not None
        assert "stac.dataspace.copernicus.eu" in obs.self_link
        assert obs.stac_assets is not None
        assert "vv" in obs.stac_assets
        assert "vh" in obs.stac_assets

    @respx.mock
    async def test_provider_properties_preserved(self, discovery, search_request):
        """Should preserve useful provider-specific properties."""
        features = [_make_stac_item()]
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection(features)
            )
        )

        result = await discovery.search(search_request)
        obs = result.observations[0]

        assert obs.provider_properties is not None
        assert obs.provider_properties["product:type"] == "IW_GRDH_1S"
        assert obs.provider_properties["processing:level"] == "L1"

    @respx.mock
    async def test_descending_orbit_parsed(self, discovery, search_request):
        """Should parse descending orbit direction."""
        features = [_make_stac_item(orbit_state="descending")]
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection(features)
            )
        )

        result = await discovery.search(search_request)
        assert result.observations[0].orbit_direction == OrbitDirection.DESCENDING

    @respx.mock
    async def test_correct_stac_request_construction(self, discovery, search_request):
        """Should construct a valid STAC POST body."""
        route = respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection([])
            )
        )

        await discovery.search(search_request)

        assert route.called
        request = route.calls.last.request
        body = json.loads(request.content)
        assert body["collections"] == ["sentinel-1-grd"]
        assert body["bbox"] == [15.0, 39.5, 16.0, 40.5]
        assert "datetime" in body
        assert "2026" in body["datetime"]
        assert body["limit"] <= 50


# ---------------------------------------------------------------------------
# Empty results
# ---------------------------------------------------------------------------


class TestDiscoveryEmptyResults:
    """Tests for searches returning zero observations."""

    @respx.mock
    async def test_empty_result(self, discovery, search_request):
        """Valid search returning zero features should not raise."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection([])
            )
        )

        result = await discovery.search(search_request)

        assert result.total_returned == 0
        assert result.observations == []
        assert result.pages_fetched == 1
        assert not result.has_more


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestDiscoveryInputValidation:
    """Tests for search request validation."""

    @respx.mock
    async def test_tiny_aoi_rejected(self, discovery):
        """Near-zero area AOI should be rejected."""
        request = SearchRequest(
            bbox=BoundingBox(west=15.0, south=40.0, east=15.0001, north=40.0001),
            time_range=TimeRange(
                start=datetime(2026, 8, 1, tzinfo=timezone.utc),
                end=datetime(2026, 9, 1, tzinfo=timezone.utc),
            ),
        )

        with pytest.raises(InvalidAOIError, match="too small"):
            await discovery.search(request)

    @respx.mock
    async def test_huge_aoi_rejected(self, discovery):
        """Unreasonably large AOI should be rejected."""
        request = SearchRequest(
            bbox=BoundingBox(west=-170.0, south=-80.0, east=170.0, north=80.0),
            time_range=TimeRange(
                start=datetime(2026, 8, 1, tzinfo=timezone.utc),
                end=datetime(2026, 9, 1, tzinfo=timezone.utc),
            ),
        )

        with pytest.raises(InvalidAOIError, match="unreasonably large"):
            await discovery.search(request)


# ---------------------------------------------------------------------------
# HTTP failures
# ---------------------------------------------------------------------------


class TestDiscoveryHTTPFailures:
    """Tests for HTTP error handling."""

    @respx.mock
    async def test_http_400(self, discovery, search_request):
        """HTTP 400 should raise ProviderInvalidResponseError."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                400, json={"description": "Invalid bbox"}
            )
        )

        with pytest.raises(ProviderInvalidResponseError, match="rejected") as exc_info:
            await discovery.search(search_request)

        assert exc_info.value.details["status_code"] == 400

    @respx.mock
    async def test_http_401(self, discovery, search_request):
        """HTTP 401 should raise AuthenticationError."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )

        with pytest.raises(AuthenticationError) as exc_info:
            await discovery.search(search_request)

        assert exc_info.value.details["status_code"] == 401

    @respx.mock
    async def test_http_403(self, discovery, search_request):
        """HTTP 403 should raise AuthenticationError."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(403, text="Forbidden")
        )

        with pytest.raises(AuthenticationError):
            await discovery.search(search_request)

    @respx.mock
    async def test_http_404(self, discovery, search_request):
        """HTTP 404 should raise ProviderInvalidResponseError."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(404, text="Not Found")
        )

        with pytest.raises(ProviderInvalidResponseError, match="not found"):
            await discovery.search(search_request)

    @respx.mock
    async def test_http_429_rate_limited(self, discovery, search_request):
        """HTTP 429 should raise ProviderRateLimitedError."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(429, text="Too Many Requests")
        )

        with pytest.raises(ProviderRateLimitedError, match="rate limit"):
            await discovery.search(search_request)

    @respx.mock
    async def test_http_500(self, discovery, search_request):
        """HTTP 500 should raise ProviderUnavailableError."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with pytest.raises(ProviderUnavailableError, match="server error") as exc_info:
            await discovery.search(search_request)

        assert exc_info.value.details["status_code"] == 500

    @respx.mock
    async def test_http_503(self, discovery, search_request):
        """HTTP 503 should raise ProviderUnavailableError."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(503, text="Service Unavailable")
        )

        with pytest.raises(ProviderUnavailableError, match="server error"):
            await discovery.search(search_request)


# ---------------------------------------------------------------------------
# Network failures
# ---------------------------------------------------------------------------


class TestDiscoveryNetworkFailures:
    """Tests for network-level failures."""

    @respx.mock
    async def test_connection_error(self, discovery, search_request):
        """Connection failure should raise ProviderUnavailableError."""
        respx.post(STAC_SEARCH_URL).mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(ProviderUnavailableError, match="network error"):
            await discovery.search(search_request)

    @respx.mock
    async def test_timeout(self, discovery, search_request):
        """Timeout should raise ProviderTimeoutError."""
        respx.post(STAC_SEARCH_URL).mock(
            side_effect=httpx.ReadTimeout("Read timed out")
        )

        with pytest.raises(ProviderTimeoutError, match="timed out"):
            await discovery.search(search_request)


# ---------------------------------------------------------------------------
# Malformed STAC responses
# ---------------------------------------------------------------------------


class TestDiscoveryMalformedResponses:
    """Tests for malformed or unexpected STAC responses."""

    @respx.mock
    async def test_invalid_json(self, discovery, search_request):
        """Non-JSON response should raise ProviderInvalidResponseError."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200,
                content=b"<html>Not JSON</html>",
                headers={"Content-Type": "text/html"},
            )
        )

        with pytest.raises(ProviderInvalidResponseError, match="invalid JSON"):
            await discovery.search(search_request)

    @respx.mock
    async def test_json_array_response(self, discovery, search_request):
        """JSON array instead of object should raise."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(200, json=["unexpected"])
        )

        with pytest.raises(ProviderInvalidResponseError, match="unexpected response"):
            await discovery.search(search_request)

    @respx.mock
    async def test_wrong_type_field(self, discovery, search_request):
        """Response with wrong 'type' field should raise."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"type": "Feature", "features": []},
            )
        )

        with pytest.raises(ProviderInvalidResponseError, match="FeatureCollection"):
            await discovery.search(search_request)

    @respx.mock
    async def test_missing_features_array(self, discovery, search_request):
        """Response missing 'features' should raise."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"type": "FeatureCollection"},
            )
        )

        with pytest.raises(ProviderInvalidResponseError, match="features"):
            await discovery.search(search_request)

    @respx.mock
    async def test_features_not_array(self, discovery, search_request):
        """Response where 'features' is not an array should raise."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"type": "FeatureCollection", "features": "not-array"},
            )
        )

        with pytest.raises(ProviderInvalidResponseError, match="not an array"):
            await discovery.search(search_request)

    @respx.mock
    async def test_item_missing_id(self, discovery, search_request):
        """Item without 'id' should be skipped (logged warning)."""
        bad_item = _make_stac_item()
        del bad_item["id"]
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection([bad_item])
            )
        )

        result = await discovery.search(search_request)
        assert result.total_returned == 0  # Skipped

    @respx.mock
    async def test_item_missing_datetime(self, discovery, search_request):
        """Item without datetime should be skipped."""
        bad_item = _make_stac_item()
        del bad_item["properties"]["datetime"]
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection([bad_item])
            )
        )

        result = await discovery.search(search_request)
        assert result.total_returned == 0  # Skipped

    @respx.mock
    async def test_item_missing_geometry(self, discovery, search_request):
        """Item without geometry should be skipped."""
        bad_item = _make_stac_item()
        del bad_item["geometry"]
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection([bad_item])
            )
        )

        result = await discovery.search(search_request)
        assert result.total_returned == 0  # Skipped

    @respx.mock
    async def test_good_items_survive_alongside_bad(self, discovery, search_request):
        """Good items should still be returned even if some items are malformed."""
        good_item = _make_stac_item("GOOD_ITEM")
        bad_item = _make_stac_item("BAD_ITEM")
        del bad_item["properties"]["datetime"]

        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection([good_item, bad_item])
            )
        )

        result = await discovery.search(search_request)
        assert result.total_returned == 1
        assert result.observations[0].id == "GOOD_ITEM"

    @respx.mock
    async def test_missing_optional_fields_handled(self, discovery, search_request):
        """Items with missing optional fields should parse with None values."""
        item = _make_stac_item()
        # Remove optional properties
        del item["properties"]["sar:polarizations"]
        del item["properties"]["sat:orbit_state"]
        del item["properties"]["sat:relative_orbit"]
        del item["properties"]["platform"]
        del item["assets"]
        del item["bbox"]

        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection([item])
            )
        )

        result = await discovery.search(search_request)
        obs = result.observations[0]

        assert obs.polarizations is None or obs.polarizations == []
        assert obs.orbit_direction is None
        assert obs.relative_orbit is None
        assert obs.platform is None
        assert obs.stac_assets is None
        assert obs.bbox is None


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class TestDiscoveryPagination:
    """Tests for pagination handling."""

    @respx.mock
    async def test_two_page_pagination(self, discovery):
        """Should follow next link to get more results."""
        request = SearchRequest(
            bbox=BoundingBox(west=15.0, south=39.5, east=16.0, north=40.5),
            time_range=TimeRange(
                start=datetime(2026, 8, 1, tzinfo=timezone.utc),
                end=datetime(2026, 9, 1, tzinfo=timezone.utc),
            ),
            max_results=20,
        )

        page1_features = [_make_stac_item(f"ITEM_P1_{i}") for i in range(3)]
        page2_features = [_make_stac_item(f"ITEM_P2_{i}") for i in range(2)]

        page1_body = {
            "collections": ["sentinel-1-grd"],
            "bbox": [15.0, 39.5, 16.0, 40.5],
            "token": "page2token",
        }

        call_count = 0

        def side_effect(request, route):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(
                    200,
                    json=_make_feature_collection(
                        page1_features, has_next=True, next_body=page1_body
                    ),
                )
            else:
                return httpx.Response(
                    200, json=_make_feature_collection(page2_features)
                )

        respx.post(STAC_SEARCH_URL).mock(side_effect=side_effect)

        result = await discovery.search(request)

        assert result.total_returned == 5
        assert result.pages_fetched == 2
        assert not result.has_more

    @respx.mock
    async def test_max_results_stops_pagination(self, discovery):
        """Should stop fetching when max_results is reached."""
        request = SearchRequest(
            bbox=BoundingBox(west=15.0, south=39.5, east=16.0, north=40.5),
            time_range=TimeRange(
                start=datetime(2026, 8, 1, tzinfo=timezone.utc),
                end=datetime(2026, 9, 1, tzinfo=timezone.utc),
            ),
            max_results=3,
        )

        page1_features = [_make_stac_item(f"ITEM_{i}") for i in range(5)]
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200,
                json=_make_feature_collection(page1_features, has_next=True),
            )
        )

        result = await discovery.search(request)

        assert result.total_returned == 3
        assert result.has_more  # There are more available
        assert result.pages_fetched == 1  # Didn't need page 2

    @respx.mock
    async def test_max_pages_protection(self, settings):
        """Should not fetch more than max_pages even if next links exist."""
        discovery = SentinelDiscoveryService(settings, max_pages=2)
        request = SearchRequest(
            bbox=BoundingBox(west=15.0, south=39.5, east=16.0, north=40.5),
            time_range=TimeRange(
                start=datetime(2026, 8, 1, tzinfo=timezone.utc),
                end=datetime(2026, 9, 1, tzinfo=timezone.utc),
            ),
            max_results=100,
        )

        # Always return results with a next link
        def side_effect(request, route):
            features = [_make_stac_item(f"ITEM_{route.call_count}")]
            return httpx.Response(
                200,
                json=_make_feature_collection(features, has_next=True),
            )

        respx.post(STAC_SEARCH_URL).mock(side_effect=side_effect)

        result = await discovery.search(request)

        assert result.pages_fetched == 2  # Capped at max_pages

    @respx.mock
    async def test_no_next_link_stops_pagination(self, discovery, search_request):
        """Should stop when there is no next link."""
        features = [_make_stac_item()]
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection(features)
            )
        )

        result = await discovery.search(search_request)

        assert result.pages_fetched == 1
        assert not result.has_more


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class TestDiscoverySecurity:
    """Verify that secrets are never exposed in STAC errors."""

    @respx.mock
    async def test_credentials_not_in_provider_error(self, discovery, search_request):
        """Credential values must not appear in STAC error messages."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(500, text="Server Error")
        )

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await discovery.search(search_request)

        error_str = str(exc_info.value)
        assert "test-client-id" not in error_str
        assert "test-client-secret" not in error_str

    @respx.mock
    async def test_token_not_in_network_error(self, discovery, search_request):
        """Token values must not appear in network error messages."""
        respx.post(STAC_SEARCH_URL).mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await discovery.search(search_request)

        error_str = str(exc_info.value)
        assert "test-client-id" not in error_str
        assert "test-client-secret" not in error_str

    @respx.mock
    async def test_credentials_not_in_error_dict(self, discovery, search_request):
        """Credential values must not appear in to_dict() output."""
        respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(500, text="Server Error")
        )

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await discovery.search(search_request)

        dict_str = json.dumps(exc_info.value.to_dict())
        assert "test-client-id" not in dict_str
        assert "test-client-secret" not in dict_str

    @respx.mock
    async def test_no_auth_header_in_stac_request(self, discovery, search_request):
        """STAC search should not send Authorization header (public endpoint)."""
        route = respx.post(STAC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200, json=_make_feature_collection([])
            )
        )

        await discovery.search(search_request)

        request = route.calls.last.request
        assert "authorization" not in {k.lower() for k in request.headers.keys()}


# ---------------------------------------------------------------------------
# STACSearchResult
# ---------------------------------------------------------------------------


class TestSTACSearchResult:
    """Tests for the result container."""

    def test_repr(self):
        result = STACSearchResult([], pages_fetched=1, has_more=False)
        r = repr(result)
        assert "total_returned=0" in r
        assert "pages_fetched=1" in r

    def test_total_returned_matches_observations(self):
        obs = [
            AcquisitionMetadata(
                id="test",
                mission="sentinel-1",
                product_type=ProductType.GRD,
                acquisition_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                geometry={
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 0], [1, 0], [1, 1], [0, 1], [0, 0]
                    ]],
                },
            )
        ]
        result = STACSearchResult(obs, pages_fetched=1, has_more=False)
        assert result.total_returned == 1
        assert len(result.observations) == 1
