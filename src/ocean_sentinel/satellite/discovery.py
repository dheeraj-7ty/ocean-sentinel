"""Sentinel-1 product discovery via CDSE STAC API.

STAC endpoint: https://stac.dataspace.copernicus.eu/v1
Collection: sentinel-1-grd (for Sentinel-1 GRD products)

This module provides the boundary between the STAC API and
the internal acquisition metadata representation.

Architecture:
    SearchRequest → STAC POST body → HTTP request → STAC FeatureCollection
    → parse/validate → list[AcquisitionMetadata]

Authentication:
    The CDSE STAC search endpoint is publicly accessible and does NOT require
    OAuth2 authentication. The TokenManager is accepted optionally for future
    use but is not used for STAC search in this phase.

Pagination:
    The Copernicus STAC API returns a ``rel=next`` link (POST-based) when more
    results are available. This module follows ``next`` links up to a
    configurable maximum page count to prevent unbounded retrieval.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.errors import (
    AuthenticationError,
    InvalidAOIError,
    InvalidTimeRangeError,
    ProviderInvalidResponseError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SatelliteError,
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

logger = logging.getLogger(__name__)

# STAC collection identifier for Sentinel-1 GRD
STAC_COLLECTION_S1_GRD = "sentinel-1-grd"

# Safety limits
DEFAULT_MAX_PAGES = 10
DEFAULT_PAGE_LIMIT = 50
ABSOLUTE_MAX_RESULTS = 500


class STACSearchResult:
    """Result container for a STAC search operation.

    Attributes:
        observations: Parsed observation metadata objects.
        total_returned: Number of observations returned across all pages.
        pages_fetched: Number of STAC pages retrieved.
        has_more: Whether more results exist beyond what was fetched.
    """

    def __init__(
        self,
        observations: list[AcquisitionMetadata],
        pages_fetched: int = 1,
        has_more: bool = False,
    ) -> None:
        self.observations = observations
        self.total_returned = len(observations)
        self.pages_fetched = pages_fetched
        self.has_more = has_more

    def __repr__(self) -> str:
        return (
            f"STACSearchResult(total_returned={self.total_returned}, "
            f"pages_fetched={self.pages_fetched}, "
            f"has_more={self.has_more})"
        )


class SentinelDiscoveryService:
    """Searches the CDSE STAC catalog for Sentinel-1 acquisitions.

    Converts raw STAC items into normalized AcquisitionMetadata objects.

    Usage::

        settings = CopernicusSettings()
        discovery = SentinelDiscoveryService(settings)

        result = await discovery.search(SearchRequest(
            bbox=BoundingBox(west=15.0, south=39.5, east=16.0, north=40.5),
            time_range=TimeRange(
                start=datetime(2026, 8, 1, tzinfo=timezone.utc),
                end=datetime(2026, 9, 1, tzinfo=timezone.utc),
            ),
            max_results=10,
        ))

        for obs in result.observations:
            print(obs.id, obs.acquisition_time)
    """

    def __init__(
        self,
        settings: CopernicusSettings,
        *,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> None:
        self._settings = settings
        self._stac_url = settings.copernicus_stac_url
        self._max_pages = max_pages

    @property
    def search_endpoint(self) -> str:
        """STAC search endpoint URL."""
        return f"{self._stac_url}/search"

    @property
    def collection_endpoint(self) -> str:
        """STAC collection endpoint for S1 GRD."""
        return f"{self._stac_url}/collections/{STAC_COLLECTION_S1_GRD}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(self, request: SearchRequest) -> STACSearchResult:
        """Search for Sentinel-1 GRD observations matching the request.

        Args:
            request: Validated search parameters (AOI, time range, limits).

        Returns:
            STACSearchResult containing parsed observations.

        Raises:
            InvalidAOIError: If the AOI is invalid.
            InvalidTimeRangeError: If the time range is invalid.
            AuthenticationError: If the STAC API rejects credentials.
            ProviderUnavailableError: On HTTP 5xx or connection failure.
            ProviderTimeoutError: On request timeout.
            ProviderRateLimitedError: On HTTP 429.
            ProviderInvalidResponseError: On malformed STAC response.
        """
        self._validate_request(request)

        body = self._build_search_body(request)

        all_observations: list[AcquisitionMetadata] = []
        pages_fetched = 0
        has_more = False
        max_results = min(request.max_results, ABSOLUTE_MAX_RESULTS)

        # First page
        url = self.search_endpoint
        current_body: dict[str, Any] | None = body

        while pages_fetched < self._max_pages:
            pages_fetched += 1

            if current_body is not None:
                data = await self._execute_stac_request(url, body=current_body)
            else:
                # Follow next-link (which may use a different URL + body)
                data = await self._execute_stac_request(url, body=body)

            features = self._extract_features(data)

            for feature in features:
                if len(all_observations) >= max_results:
                    has_more = True
                    break
                try:
                    obs = self._stac_item_to_acquisition(feature)
                    all_observations.append(obs)
                except Exception as e:
                    logger.warning(
                        "Skipping malformed STAC item %s: %s",
                        feature.get("id", "<unknown>"),
                        e,
                    )

            if len(all_observations) >= max_results:
                has_more = True
                break

            # Check for next page
            next_link = self._find_next_link(data)
            if next_link is None:
                break

            url = next_link.get("href", self.search_endpoint)
            # The CDSE next link uses POST with a body in the link
            next_body = next_link.get("body")
            if next_body and isinstance(next_body, dict):
                current_body = next_body
            else:
                # Fallback — use the original body (shouldn't normally happen)
                current_body = body

            has_more = True  # There was a next link

        # If we stopped due to max_pages but there was a next link
        if pages_fetched >= self._max_pages and self._find_next_link(data) is not None:
            has_more = True

        logger.info(
            "STAC search returned %d observations across %d page(s), has_more=%s",
            len(all_observations),
            pages_fetched,
            has_more,
        )

        return STACSearchResult(
            observations=all_observations,
            pages_fetched=pages_fetched,
            has_more=has_more and len(all_observations) >= max_results,
        )

    # ------------------------------------------------------------------
    # Request construction
    # ------------------------------------------------------------------

    def _validate_request(self, request: SearchRequest) -> None:
        """Additional runtime validation beyond Pydantic."""
        bbox = request.bbox
        if bbox.area_degrees_squared < 1e-6:
            raise InvalidAOIError(
                "AOI is too small (near-zero area)",
                details={"area_deg2": bbox.area_degrees_squared},
            )
        if bbox.area_degrees_squared > 400:
            raise InvalidAOIError(
                "AOI is unreasonably large (> 400 square degrees)",
                details={"area_deg2": bbox.area_degrees_squared},
            )

    def _build_search_body(self, request: SearchRequest) -> dict[str, Any]:
        """Construct the STAC POST search body."""
        body: dict[str, Any] = {
            "collections": [STAC_COLLECTION_S1_GRD],
            "bbox": request.bbox.to_list(),
            "datetime": request.time_range.to_stac_datetime(),
            "limit": min(request.max_results, DEFAULT_PAGE_LIMIT),
        }

        # Optional: add sortby for deterministic ordering
        body["sortby"] = [{"field": "datetime", "direction": "desc"}]

        return body

    # ------------------------------------------------------------------
    # HTTP execution
    # ------------------------------------------------------------------

    async def _execute_stac_request(
        self,
        url: str,
        *,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a POST request to the STAC search endpoint.

        Returns the parsed JSON response body.

        Raises appropriate SatelliteError subclasses on failure.
        """
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.http_timeout_seconds,
            ) as client:
                response = await client.post(
                    url,
                    json=body,
                    headers={"Accept": "application/geo+json"},
                )

        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(
                "STAC search request timed out",
                details={"timeout_seconds": self._settings.http_timeout_seconds},
                cause=e,
            ) from e
        except httpx.HTTPError as e:
            raise ProviderUnavailableError(
                "STAC search failed due to network error",
                cause=e,
            ) from e

        # Handle HTTP status errors
        self._handle_http_status(response)

        # Parse JSON
        try:
            data = response.json()
        except Exception as e:
            raise ProviderInvalidResponseError(
                "STAC endpoint returned invalid JSON",
                details={"status_code": response.status_code},
                cause=e,
            ) from e

        if not isinstance(data, dict):
            raise ProviderInvalidResponseError(
                "STAC endpoint returned unexpected response format",
                details={"type": type(data).__name__},
            )

        return data

    def _handle_http_status(self, response: httpx.Response) -> None:
        """Raise appropriate errors for non-2xx HTTP status codes."""
        status = response.status_code

        if 200 <= status < 300:
            return

        if status in (401, 403):
            raise AuthenticationError(
                f"STAC API authentication/authorization failed (HTTP {status})",
                details={"status_code": status},
            )
        if status == 429:
            raise ProviderRateLimitedError(
                "STAC API rate limit exceeded (HTTP 429)",
                details={"status_code": status},
            )
        if status == 400:
            # Try to extract error detail without exposing secrets
            try:
                err_body = response.json()
                detail = err_body.get("description", err_body.get("detail", ""))
            except Exception:
                detail = ""
            raise ProviderInvalidResponseError(
                f"STAC API rejected the request (HTTP 400)",
                details={"status_code": status, "detail": str(detail)[:200]},
            )
        if status == 404:
            raise ProviderInvalidResponseError(
                "STAC API resource not found (HTTP 404)",
                details={"status_code": status},
            )
        if status >= 500:
            raise ProviderUnavailableError(
                f"STAC API server error (HTTP {status})",
                details={"status_code": status},
            )
        # Other 4xx
        raise ProviderInvalidResponseError(
            f"STAC API returned unexpected status (HTTP {status})",
            details={"status_code": status},
        )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _extract_features(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract and validate the features array from a STAC response."""
        resp_type = data.get("type")
        if resp_type != "FeatureCollection":
            raise ProviderInvalidResponseError(
                f"Expected STAC FeatureCollection, got type={resp_type!r}",
                details={"type": resp_type},
            )

        features = data.get("features")
        if features is None:
            raise ProviderInvalidResponseError(
                "STAC response missing 'features' array",
            )
        if not isinstance(features, list):
            raise ProviderInvalidResponseError(
                "STAC response 'features' is not an array",
                details={"type": type(features).__name__},
            )

        return features

    def _find_next_link(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Find the 'next' pagination link in the STAC response."""
        links = data.get("links", [])
        if not isinstance(links, list):
            return None

        for link in links:
            if isinstance(link, dict) and link.get("rel") == "next":
                href = link.get("href")
                if href and isinstance(href, str):
                    return link

        return None

    def _stac_item_to_acquisition(
        self, item: dict[str, Any]
    ) -> AcquisitionMetadata:
        """Convert a raw STAC item dict into an AcquisitionMetadata object.

        Raises ValueError if the item is missing required fields.
        """
        # --- Required fields ---
        item_id = item.get("id")
        if not item_id or not isinstance(item_id, str):
            raise ValueError("STAC item missing 'id'")

        geometry = item.get("geometry")
        if not geometry or not isinstance(geometry, dict):
            raise ValueError(f"STAC item {item_id} missing 'geometry'")

        properties = item.get("properties")
        if not isinstance(properties, dict):
            raise ValueError(f"STAC item {item_id} missing 'properties'")

        # Acquisition datetime
        dt_str = properties.get("datetime")
        if not dt_str:
            raise ValueError(f"STAC item {item_id} missing 'datetime' property")

        try:
            acquisition_time = datetime.fromisoformat(
                dt_str.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"STAC item {item_id} has invalid datetime: {dt_str}"
            ) from e

        # --- Optional fields ---
        bbox = item.get("bbox")
        if bbox is not None and not isinstance(bbox, list):
            bbox = None

        collection = item.get("collection", STAC_COLLECTION_S1_GRD)

        # Polarizations
        raw_pols = properties.get("sar:polarizations")
        polarizations = None
        if isinstance(raw_pols, list):
            polarizations = []
            for p in raw_pols:
                try:
                    polarizations.append(Polarization(p))
                except ValueError:
                    logger.debug("Unknown polarization %s in item %s", p, item_id)

        # Orbit direction
        orbit_direction = None
        raw_orbit = properties.get("sat:orbit_state")
        if raw_orbit:
            orbit_map = {"ascending": OrbitDirection.ASCENDING, "descending": OrbitDirection.DESCENDING}
            orbit_direction = orbit_map.get(str(raw_orbit).lower())

        # Product type
        raw_product_type = properties.get("product:type", "")
        product_type = ProductType.GRD  # All items in sentinel-1-grd are GRD

        # Instrument mode
        acquisition_mode = properties.get("sar:instrument_mode")

        # Relative orbit
        relative_orbit = properties.get("sat:relative_orbit")
        if relative_orbit is not None:
            try:
                relative_orbit = int(relative_orbit)
            except (ValueError, TypeError):
                relative_orbit = None

        # Platform
        platform = properties.get("platform")

        # Self link
        self_link = None
        item_links = item.get("links", [])
        if isinstance(item_links, list):
            for link in item_links:
                if isinstance(link, dict) and link.get("rel") == "self":
                    self_link = link.get("href")
                    break

        # Assets
        stac_assets = item.get("assets")
        if stac_assets is not None and not isinstance(stac_assets, dict):
            stac_assets = None

        # Build a small set of interesting provider properties
        provider_props = {}
        for key in (
            "product:type",
            "processing:level",
            "processing:version",
            "sar:frequency_band",
            "sar:center_frequency",
            "sar:observation_direction",
            "constellation",
            "start_datetime",
            "end_datetime",
        ):
            val = properties.get(key)
            if val is not None:
                provider_props[key] = val

        return AcquisitionMetadata(
            id=item_id,
            mission="sentinel-1",
            product_type=product_type,
            acquisition_time=acquisition_time,
            geometry=geometry,
            bbox=bbox,
            polarizations=polarizations,
            orbit_direction=orbit_direction,
            acquisition_mode=acquisition_mode,
            relative_orbit=relative_orbit,
            platform=platform,
            source_collection=collection,
            source_reference=item_id,
            self_link=self_link,
            stac_assets=stac_assets,
            provider_properties=provider_props if provider_props else None,
        )
