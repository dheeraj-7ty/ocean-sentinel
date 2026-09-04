"""Sentinel Hub Process API integration for AOI-specific imagery.

Process API endpoint: https://sh.dataspace.copernicus.eu/api/v1/process

Requests processed Sentinel-1 GRD rasters for a specific AOI and time range.
The Process API uses evalscripts (JavaScript) to define the output bands and
processing pipeline.

This module provides:

1. ``ProcessRequestBuilder`` — converts an ``ImageryRequest`` into a fully-
   validated Sentinel Hub Process API JSON payload.  It performs NO network
   I/O; authentication is the responsibility of the HTTP transport layer.

2. ``SentinelImageryService`` — performs authenticated HTTP requests against
   the Sentinel Hub Process API and validates/parses the returned GeoTIFF data.

Canonical output: GeoTIFF / FLOAT32

Architecture::

    ImageryRequest
          ↓
    ProcessRequestBuilder.build()
          ↓
    dict  (deterministic Process API payload, no credentials)
          ↓
    SentinelImageryService.request_imagery()
          ↓
    ImageryResult (validated GeoTIFF metadata + raster stats + raw bytes)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import numpy as np
from rasterio.io import MemoryFile

from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.errors import (
    AuthenticationError,
    AuthorizationError,
    InvalidRequestError,
    ProviderInvalidResponseError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RasterValidationError,
)
from ocean_sentinel.models import (
    BandStatistics,
    ImageryRequest,
    ImageryResult,
    Polarization,
)
from ocean_sentinel.satellite.auth import TokenManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Sentinel Hub data collection type for Sentinel-1 GRD
SH_DATA_TYPE_S1_GRD = "sentinel-1-grd"

# Sentinel Hub processes Sentinel-1 GRD values as linear intensity (σ0).
# Orthorectification corrects for terrain-induced geometric distortions and
# is required for reliable geolocation.  SIGMA0_ELLIPSOID is the default
# radiometric calibration for GRD data from the Process API.
SH_S1_DEFAULT_PROCESSING = {
    "orthorectify": "true",
    "backCoeff": "SIGMA0_ELLIPSOID",
}

# ---------------------------------------------------------------------------
# Evalscript templates
# ---------------------------------------------------------------------------

# Evalscripts are parameterised at build time based on the requested bands.
# They must be V3 (//VERSION=3).

_EVALSCRIPT_TEMPLATE = """\
//VERSION=3
function setup() {{
    return {{
        input: [{input_bands}],
        output: {{
            id: "default",
            bands: {num_bands},
            sampleType: "FLOAT32"
        }}
    }};
}}

function evaluatePixel(samples) {{
    return [{sample_values}];
}}
"""

# Keep the dual-band default for direct use / backward compatibility
DEFAULT_EVALSCRIPT_VV_VH = """\
//VERSION=3
function setup() {
    return {
        input: ["VV", "VH"],
        output: {
            id: "default",
            bands: 2,
            sampleType: "FLOAT32"
        }
    };
}

function evaluatePixel(samples) {
    return [samples.VV, samples.VH];
}
"""


# ---------------------------------------------------------------------------
# ProcessRequestBuilder
# ---------------------------------------------------------------------------


class ProcessRequestBuilder:
    """Translates a domain-level ``ImageryRequest`` into a Sentinel Hub
    Process API payload.

    This class performs **no** network I/O.  It only builds and validates the
    JSON structure.  Authentication credentials are **never** included in the
    returned payload; they must be attached by the HTTP transport layer.

    The build is deterministic: identical inputs always produce identical
    outputs, enabling reliable test assertions.

    Usage::

        request = ImageryRequest(
            observation=obs,
            bbox=BoundingBox(west=15.0, south=39.5, east=16.0, north=40.5),
            time_range=TimeRange(start=..., end=...),
            requested_bands=[Polarization.VV, Polarization.VH],
            output=OutputConfig(width=512, height=512),
        )

        payload = ProcessRequestBuilder.build(request)
        # payload is a plain dict, ready to be JSON-serialised and POSTed
    """

    @staticmethod
    def build(request: ImageryRequest) -> dict[str, Any]:
        """Build and return a Sentinel Hub Process API payload.

        Args:
            request: Validated domain imagery request.

        Returns:
            A plain ``dict`` representing the Process API JSON body.
            The dict contains no authentication credentials.

        Raises:
            InvalidRequestError: If any derived parameter is invalid (e.g.
                the band list is empty after deduplication).
        """
        bands = ProcessRequestBuilder._resolve_bands(request)
        evalscript = ProcessRequestBuilder._build_evalscript(bands)
        bounds_section = ProcessRequestBuilder._build_bounds(request)
        data_section = ProcessRequestBuilder._build_data(request)
        output_section = request.output.to_sh_output()

        return {
            "input": {
                "bounds": bounds_section,
                "data": data_section,
            },
            "output": output_section,
            "evalscript": evalscript,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_bands(request: ImageryRequest) -> list[Polarization]:
        """Return deduplicated, order-preserved list of requested bands.

        Raises:
            InvalidRequestError: If the deduplicated list is empty.
        """
        seen: set[Polarization] = set()
        bands: list[Polarization] = []
        for p in request.requested_bands:
            if p not in seen:
                seen.add(p)
                bands.append(p)

        if not bands:
            raise InvalidRequestError(
                "No valid bands remain after deduplication",
                details={"requested_bands": [p.value for p in request.requested_bands]},
            )
        return bands

    @staticmethod
    def _build_evalscript(bands: list[Polarization]) -> str:
        """Generate a V3 evalscript for the given polarization bands."""
        input_bands = ", ".join(f'"{p.value}"' for p in bands)
        sample_values = ", ".join(f"samples.{p.value}" for p in bands)
        return _EVALSCRIPT_TEMPLATE.format(
            input_bands=input_bands,
            num_bands=len(bands),
            sample_values=sample_values,
        )

    @staticmethod
    def _build_bounds(request: ImageryRequest) -> dict[str, Any]:
        """Build the Process API ``input.bounds`` section."""
        return {
            "bbox": request.bbox.to_list(),
            "properties": {
                "crs": request.output.to_crs_url(),
            },
        }

    @staticmethod
    def _build_data(request: ImageryRequest) -> list[dict[str, Any]]:
        """Build the Process API ``input.data`` section."""
        return [
            {
                "type": SH_DATA_TYPE_S1_GRD,
                "dataFilter": {
                    "timeRange": {
                        "from": _fmt_sh_datetime(request.time_range.start),
                        "to": _fmt_sh_datetime(request.time_range.end),
                    },
                },
                "processing": dict(SH_S1_DEFAULT_PROCESSING),
            }
        ]


# ---------------------------------------------------------------------------
# SentinelImageryService (HTTP transport & GeoTIFF validation)
# ---------------------------------------------------------------------------


class SentinelImageryService:
    """Requests processed Sentinel-1 imagery via Copernicus Sentinel Hub Process API.

    Orchestrates:
    1. Payload compilation via ``ProcessRequestBuilder``
    2. Bearer token retrieval via ``TokenManager``
    3. Authenticated POST to Sentinel Hub Process API
    4. Safe error mapping and HTTP status handling
    5. In-memory GeoTIFF validation and parsing via ``rasterio.MemoryFile``
    6. Extraction of raster metadata, bounds, CRS, transform, and band statistics

    Usage::

        settings = CopernicusSettings()
        tm = TokenManager(settings)
        service = SentinelImageryService(settings, tm)

        result = await service.request_imagery(imagery_request)
        print(result.width, result.height, result.bands)
    """

    def __init__(
        self,
        settings: CopernicusSettings,
        token_manager: TokenManager,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._settings = settings
        self._token_manager = token_manager
        self._process_url = settings.copernicus_process_api_url
        self._client = client

    async def request_imagery(self, request: ImageryRequest) -> ImageryResult:
        """Retrieve and validate Sentinel-1 SAR imagery for the given request.

        Args:
            request: Validated domain imagery request.

        Returns:
            Validated ``ImageryResult`` containing raster metadata, band
            statistics, and raw GeoTIFF bytes.

        Raises:
            AuthenticationError: On OAuth or 401 token authentication failure.
            AuthorizationError: On 403 access denial.
            ProviderRateLimitedError: On HTTP 429 rate limit exceeded.
            ProviderTimeoutError: On request timeout.
            ProviderUnavailableError: On 5xx server error or network failure.
            ProviderInvalidResponseError: On 400 bad request or unexpected format.
            RasterValidationError: If response is empty, not a GeoTIFF, or has
                incompatible dimensions, bands, dtype, CRS, or no finite data.
        """
        payload = ProcessRequestBuilder.build(request)
        token = await self._token_manager.get_token()
        raw_bytes = await self._execute_process_request(payload, token)
        return self._validate_and_parse_raster(raw_bytes, request)

    async def _execute_process_request(
        self, payload: dict[str, Any], token: str
    ) -> bytes:
        """Send authenticated POST to Process API and return raw response bytes."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "image/tiff",
            "Content-Type": "application/json",
        }

        try:
            if self._client is not None:
                response = await self._client.post(
                    self._process_url,
                    json=payload,
                    headers=headers,
                )
            else:
                async with httpx.AsyncClient(
                    timeout=self._settings.http_timeout_seconds,
                ) as client:
                    response = await client.post(
                        self._process_url,
                        json=payload,
                        headers=headers,
                    )
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(
                "Process API request timed out",
                details={"timeout_seconds": self._settings.http_timeout_seconds},
                cause=e,
            ) from e
        except httpx.HTTPError as e:
            raise ProviderUnavailableError(
                "Process API request failed due to network error",
                cause=e,
            ) from e

        self._handle_http_status(response)
        return response.content

    def _handle_http_status(self, response: httpx.Response) -> None:
        """Map non-2xx HTTP status codes to appropriate domain errors."""
        status = response.status_code
        if 200 <= status < 300:
            return

        if status == 401:
            raise AuthenticationError(
                f"Process API authentication failed (HTTP {status})",
                details={"status_code": status},
            )
        if status == 403:
            raise AuthorizationError(
                f"Process API authorization denied (HTTP {status})",
                details={"status_code": status},
            )
        if status == 429:
            raise ProviderRateLimitedError(
                "Process API rate limit exceeded (HTTP 429)",
                details={"status_code": status},
            )
        if status == 400:
            detail = self._extract_error_detail(response)
            if detail:
                msg = f"Process API rejected the request (HTTP 400): {detail}"
            else:
                msg = "Process API rejected the request (HTTP 400)"
            raise ProviderInvalidResponseError(
                msg,
                details={"status_code": status, "detail": detail},
            )
        if status == 404:
            raise ProviderInvalidResponseError(
                "Process API resource not found (HTTP 404)",
                details={"status_code": status},
            )
        if status >= 500:
            raise ProviderUnavailableError(
                f"Process API server error (HTTP {status})",
                details={"status_code": status},
            )
        raise ProviderInvalidResponseError(
            f"Process API returned unexpected status (HTTP {status})",
            details={"status_code": status},
        )

    def _extract_error_detail(self, response: httpx.Response) -> str:
        """Extract sanitized error detail from response body without leaking secrets."""
        try:
            body = response.json()
            if isinstance(body, dict):
                err = body.get("error", {})
                if isinstance(err, dict):
                    msg = err.get("message", "")
                else:
                    msg = str(err)
                if not msg:
                    msg = body.get("detail", body.get("description", ""))
                return str(msg)[:200]
        except Exception:
            pass
        return ""

    def _validate_and_parse_raster(
        self, raw_bytes: bytes, request: ImageryRequest
    ) -> ImageryResult:
        """Validate that raw bytes constitute a valid GeoTIFF conforming to request."""
        if not raw_bytes:
            raise RasterValidationError("Process API returned empty response body")

        # Preliminary payload checks for HTML or JSON error responses returned with 200
        stripped = raw_bytes[:256].strip()
        if (
            stripped.startswith(b"<!DOCTYPE")
            or stripped.startswith(b"<html")
            or b"<head>" in stripped
        ):
            raise RasterValidationError(
                "Process API returned HTML content instead of GeoTIFF",
                details={"byte_length": len(raw_bytes)},
            )
        if stripped.startswith(b"{") and b'"error"' in stripped:
            raise RasterValidationError(
                "Process API returned JSON error instead of GeoTIFF",
                details={"byte_length": len(raw_bytes)},
            )

        try:
            with MemoryFile(raw_bytes) as memfile:
                with memfile.open() as dataset:
                    # 1. Driver check
                    if dataset.driver != "GTiff":
                        raise RasterValidationError(
                            f"Expected GTiff driver, got: {dataset.driver}",
                            details={"driver": dataset.driver},
                        )

                    # 2. Dimensions check
                    if request.output.width is not None and dataset.width != request.output.width:
                        raise RasterValidationError(
                            f"Raster width mismatch: expected {request.output.width}, "
                            f"got {dataset.width}",
                            details={
                                "expected_width": request.output.width,
                                "actual_width": dataset.width,
                            },
                        )
                    if (
                        request.output.height is not None
                        and dataset.height != request.output.height
                    ):
                        raise RasterValidationError(
                            f"Raster height mismatch: expected {request.output.height}, "
                            f"got {dataset.height}",
                            details={
                                "expected_height": request.output.height,
                                "actual_height": dataset.height,
                            },
                        )

                    # 3. Band count check
                    expected_band_count = len(request.requested_bands)
                    if dataset.count != expected_band_count:
                        raise RasterValidationError(
                            f"Band count mismatch: expected {expected_band_count}, "
                            f"got {dataset.count}",
                            details={
                                "expected_bands": expected_band_count,
                                "actual_bands": dataset.count,
                            },
                        )

                    # 4. Data type check
                    for b_idx in range(1, dataset.count + 1):
                        b_dtype = dataset.dtypes[b_idx - 1]
                        if b_dtype != "float32":
                            raise RasterValidationError(
                                f"Band {b_idx} dtype mismatch: expected float32, got {b_dtype}",
                                details={
                                    "band": b_idx,
                                    "expected_dtype": "float32",
                                    "actual_dtype": b_dtype,
                                },
                            )

                    # 5. CRS check
                    if dataset.crs is None:
                        raise RasterValidationError(
                            "Raster is missing coordinate reference system (CRS)",
                        )
                    epsg = dataset.crs.to_epsg()
                    if epsg is not None and epsg != request.output.crs_epsg:
                        raise RasterValidationError(
                            f"CRS EPSG mismatch: expected {request.output.crs_epsg}, got {epsg}",
                            details={"expected_epsg": request.output.crs_epsg, "actual_epsg": epsg},
                        )

                    # 6. Geotransform / bounds check
                    if dataset.transform is None:
                        raise RasterValidationError("Raster is missing affine geotransform")

                    # 7. Pixel values and finite data validation
                    band_stats: list[BandStatistics] = []
                    all_bands_empty = True

                    for idx, pol in enumerate(request.requested_bands):
                        band_arr = dataset.read(idx + 1)
                        total_pixels = int(band_arr.size)
                        finite_mask = np.isfinite(band_arr)
                        finite_count = int(np.sum(finite_mask))

                        if finite_count > 0:
                            all_bands_empty = False
                            finite_vals = band_arr[finite_mask]
                            min_val = float(np.min(finite_vals))
                            max_val = float(np.max(finite_vals))
                            mean_val = float(np.mean(finite_vals))
                        else:
                            min_val = 0.0
                            max_val = 0.0
                            mean_val = 0.0

                        band_stats.append(
                            BandStatistics(
                                polarization=pol,
                                min_value=min_val,
                                max_value=max_val,
                                mean_value=mean_val,
                                finite_pixel_count=finite_count,
                                total_pixel_count=total_pixels,
                            )
                        )

                    if all_bands_empty and dataset.width * dataset.height > 0:
                        raise RasterValidationError(
                            "Raster contains no valid finite pixel data "
                            "(all pixels are NaN or infinite)",
                            details={"total_pixels": dataset.width * dataset.height},
                        )

                    bounds = [
                        float(dataset.bounds.left),
                        float(dataset.bounds.bottom),
                        float(dataset.bounds.right),
                        float(dataset.bounds.top),
                    ]
                    transform = [float(x) for x in dataset.transform[:6]]
                    crs_str = dataset.crs.to_string()

                    return ImageryResult(
                        observation_id=request.observation.id,
                        width=dataset.width,
                        height=dataset.height,
                        band_count=dataset.count,
                        bands=list(request.requested_bands),
                        dtype="float32",
                        crs=crs_str,
                        bounds=bounds,
                        transform=transform,
                        band_statistics=band_stats,
                        raw_bytes=raw_bytes,
                    )

        except RasterValidationError:
            raise
        except Exception as e:
            raise RasterValidationError(
                f"Failed to parse response as GeoTIFF: {e}",
                cause=e,
            ) from e


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _fmt_sh_datetime(dt: datetime) -> str:
    """Format a datetime as a Sentinel Hub Process API datetime string.

    Normalises to UTC and formats as ``YYYY-MM-DDTHH:MM:SSZ``.
    Microseconds are intentionally dropped — the Process API ignores them.
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
