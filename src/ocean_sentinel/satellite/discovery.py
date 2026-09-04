"""Sentinel-1 product discovery via CDSE STAC API.

STAC endpoint: https://stac.dataspace.copernicus.eu/v1
Collection: sentinel-1-grd (for Sentinel-1 GRD products)

This module provides the boundary between the STAC API and
the internal acquisition metadata representation.
"""

from __future__ import annotations

import logging
from typing import Optional

from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.errors import SatelliteErrorCode
from ocean_sentinel.models import (
    AcquisitionMetadata,
    BoundingBox,
    SearchRequest,
    TimeRange,
)

logger = logging.getLogger(__name__)

# STAC collection identifier for Sentinel-1 GRD
STAC_COLLECTION_S1_GRD = "sentinel-1-grd"


class SentinelDiscoveryService:
    """Searches the CDSE STAC catalog for Sentinel-1 acquisitions.

    Converts raw STAC items into normalized AcquisitionMetadata objects.

    Implementation will be completed in Phase 1B.
    """

    def __init__(self, settings: CopernicusSettings) -> None:
        self._settings = settings
        self._stac_url = settings.copernicus_stac_url

    @property
    def search_endpoint(self) -> str:
        """STAC search endpoint URL."""
        return f"{self._stac_url}/search"

    @property
    def collection_endpoint(self) -> str:
        """STAC collection endpoint for S1 GRD."""
        return f"{self._stac_url}/collections/{STAC_COLLECTION_S1_GRD}"

    # Phase 1B: async def search(self, request: SearchRequest) -> list[AcquisitionMetadata]
    # Phase 1B: def _stac_item_to_acquisition(self, item: dict) -> AcquisitionMetadata
