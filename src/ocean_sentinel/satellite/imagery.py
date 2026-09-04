"""Sentinel Hub Process API integration for AOI-specific imagery.

Process API endpoint: https://sh.dataspace.copernicus.eu/api/v1/process

Requests processed Sentinel-1 GRD rasters for a specific AOI and time range.
The Process API uses evalscripts (JavaScript) to define the output.

This module provides the boundary between Sentinel Hub and the
internal raster processing pipeline.

Canonical output: GeoTIFF / FLOAT32
"""

from __future__ import annotations

import logging

from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.satellite.auth import TokenManager

logger = logging.getLogger(__name__)

# Sentinel Hub data collection type for Sentinel-1 GRD
SH_DATA_TYPE_S1_GRD = "sentinel-1-grd"

# Default evalscript for VV + VH as FLOAT32
DEFAULT_EVALSCRIPT_VV_VH = """
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


class SentinelImageryService:
    """Requests processed Sentinel-1 imagery via Sentinel Hub Process API.

    Implementation will be completed in Phase 1B.
    """

    def __init__(self, settings: CopernicusSettings, token_manager: TokenManager) -> None:
        self._settings = settings
        self._token_manager = token_manager
        self._process_url = settings.copernicus_process_api_url

    # Phase 1B: async def request_imagery(self, ...) -> bytes
    # Phase 1B: def _build_process_request(self, ...) -> dict
