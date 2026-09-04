"""Sentinel Hub Process API integration for AOI-specific imagery.

Process API endpoint: https://sh.dataspace.copernicus.eu/api/v1/process

Requests processed Sentinel-1 GRD rasters for a specific AOI and time range.
The Process API uses evalscripts (JavaScript) to define the output bands and
processing pipeline.

This module provides:

1. ``ProcessRequestBuilder`` — converts an ``ImageryRequest`` into a fully-
   validated Sentinel Hub Process API JSON payload.  It performs NO network
   I/O; authentication is the responsibility of the HTTP transport layer.

2. ``SentinelImageryService`` — will perform the actual HTTP request in a
   future phase (Phase 1B.3.2).  The request-construction layer defined here
   is ready to be consumed by that service.

Canonical output: GeoTIFF / FLOAT32

Architecture::

    ImageryRequest
          ↓
    ProcessRequestBuilder.build()
          ↓
    dict  (deterministic Process API payload, no credentials)
          ↓
    [Phase 1B.3.2] SentinelImageryService.request_imagery()
          ↓
    bytes (raw GeoTIFF response)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.errors import InvalidRequestError
from ocean_sentinel.models import ImageryRequest, Polarization
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
# SentinelImageryService (HTTP transport — Phase 1B.3.2)
# ---------------------------------------------------------------------------


class SentinelImageryService:
    """Requests processed Sentinel-1 imagery via Sentinel Hub Process API.

    Phase 1B.3.1 provides the request-construction layer via
    ``ProcessRequestBuilder``.  The actual HTTP download is implemented in
    Phase 1B.3.2.
    """

    def __init__(self, settings: CopernicusSettings, token_manager: TokenManager) -> None:
        self._settings = settings
        self._token_manager = token_manager
        self._process_url = settings.copernicus_process_api_url

    # Phase 1B.3.2: async def request_imagery(self, request: ImageryRequest) -> bytes
    # Phase 1B.3.2: async def _execute_process_request(self, payload: dict, token: str) -> bytes


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
