"""Real Copernicus Sentinel-1 imagery retrieval verification.

This script executes an end-to-end verification against the live
Copernicus Data Space Ecosystem (CDSE) APIs:
1. Discovers a real Sentinel-1 GRD observation via STAC
2. Compiles a Process API request for a sub-AOI
3. Acquires an OAuth Bearer token via TokenManager
4. Retrieves processed GeoTIFF SAR raster data via Sentinel Hub Process API
5. Parses and validates the raster with rasterio
6. Reports safe verification metadata

SECURITY:
- Never prints client secret or access token
- Never logs Authorization headers
- Only reports safe metadata (dimensions, CRS, statistics)

Usage:
    python scripts/verify_imagery.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

# Add src to path for editable install compatibility
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


async def verify_real_imagery_retrieval() -> None:
    """Execute end-to-end imagery retrieval against real Copernicus APIs."""
    print("=" * 70)
    print("Ocean Sentinel -- Real Copernicus Sentinel-1 Imagery Verification")
    print("=" * 70)
    print()

    # Verify credentials presence without printing them
    client_id = os.environ.get("COPERNICUS_CLIENT_ID", "")
    client_secret = os.environ.get("COPERNICUS_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            client_id = os.environ.get("COPERNICUS_CLIENT_ID", "")
            client_secret = os.environ.get("COPERNICUS_CLIENT_SECRET", "")
        except ImportError:
            pass

    if not client_id or not client_secret:
        print("STATUS: NOT VERIFIED")
        print(
            "REASON: credentials unavailable "
            "(COPERNICUS_CLIENT_ID or COPERNICUS_CLIENT_SECRET missing)"
        )
        return

    print("Credentials found: YES")
    print()

    try:
        from ocean_sentinel.config import CopernicusSettings
        from ocean_sentinel.models import (
            BoundingBox,
            ImageryRequest,
            OutputConfig,
            OutputFormat,
            Polarization,
            SearchRequest,
            TimeRange,
        )
        from ocean_sentinel.satellite.auth import TokenManager
        from ocean_sentinel.satellite.discovery import SentinelDiscoveryService
        from ocean_sentinel.satellite.imagery import SentinelImageryService

        settings = CopernicusSettings()
        token_manager = TokenManager(settings)
        discovery_service = SentinelDiscoveryService(settings, max_pages=2)
        imagery_service = SentinelImageryService(settings, token_manager)

        # 1. Discover a real Sentinel-1 observation
        # Test AOI: Mediterranean Sea / Southern Italy (frequent overpasses)
        search_bbox = BoundingBox(west=15.5, south=39.5, east=16.5, north=40.5)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=21)
        time_range = TimeRange(start=start_time, end=end_time)

        print("Step 1: Discovering real Sentinel-1 observation via STAC...")
        search_req = SearchRequest(
            bbox=search_bbox,
            time_range=time_range,
            max_results=3,
        )

        stac_result = await discovery_service.search(search_req)
        if not stac_result.observations:
            print("STATUS: NOT VERIFIED")
            print("REASON: No Sentinel-1 observations found in test AOI within the last 21 days")
            return

        obs = stac_result.observations[0]
        print(f"Discovered observation: {obs.id}")
        print(f"Acquisition time: {obs.acquisition_time.isoformat()}")
        available_pols = obs.polarizations or [Polarization.VV, Polarization.VH]
        print(f"Available polarizations: {[p.value for p in available_pols]}")
        print()

        # 2. Select target bands (subset of available)
        requested_bands = [p for p in [Polarization.VV, Polarization.VH] if p in available_pols]
        if not requested_bands:
            requested_bands = [available_pols[0]]

        # 3. Create a focused sub-AOI request (256x256 to be lightweight)
        # Bounding box within the Mediterranean search area
        sub_bbox = BoundingBox(west=15.6, south=39.6, east=16.0, north=40.0)
        # Narrow temporal window around the acquisition time
        obs_time = obs.acquisition_time
        obs_start = obs_time - timedelta(hours=1)
        obs_end = obs_time + timedelta(hours=1)
        obs_time_range = TimeRange(start=obs_start, end=obs_end)

        imagery_req = ImageryRequest(
            observation=obs,
            bbox=sub_bbox,
            time_range=obs_time_range,
            requested_bands=requested_bands,
            output=OutputConfig(width=256, height=256, format=OutputFormat.TIFF),
        )

        print("Step 2: Requesting processed SAR imagery via Sentinel Hub Process API...")
        print(f"Process API endpoint: {settings.copernicus_process_api_url}")
        print("Requested dimensions: 256x256")
        print(f"Requested bands: {[p.value for p in requested_bands]}")
        print("Executing authenticated Process API retrieval...")
        print()

        result = await imagery_service.request_imagery(imagery_req)

        # 4. Print safe verification results
        total_finite = sum(stat.finite_pixel_count for stat in result.band_statistics)

        print("=" * 70)
        print("REAL COPERNICUS SENTINEL-1 IMAGERY VERIFICATION")
        print("=" * 70)
        print("Status: PASS")
        print(f"Observation: {result.observation_id}")
        print("Raster received: YES")
        print("Format: GeoTIFF")
        print(f"Width: {result.width}")
        print(f"Height: {result.height}")
        print(f"Bands: {result.band_count}")
        print(f"Polarizations: {[p.value for p in result.bands]}")
        print(f"Dtype: {result.dtype}")
        print(f"CRS: {result.crs}")
        print(f"Bounds: {[round(b, 4) for b in result.bounds]}")
        print(f"Raw GeoTIFF size: {len(result.raw_bytes):,} bytes")
        total_px = result.width * result.height * result.band_count
        print(f"Valid finite pixels: {total_finite:,} / {total_px:,}")
        for stat in result.band_statistics:
            print(
                f"  Band {stat.polarization.value}: "
                f"min={stat.min_value:.6f}, "
                f"max={stat.max_value:.6f}, "
                f"mean={stat.mean_value:.6f}, "
                f"finite={stat.finite_pixel_count:,}"
            )
        print("Processing API: PASS")
        print("=" * 70)

    except Exception as e:
        print("=" * 70)
        print("REAL COPERNICUS SENTINEL-1 IMAGERY VERIFICATION")
        print("=" * 70)
        print("Status: FAIL")
        print(f"Error category: {type(e).__name__}")
        print(f"Error detail: {str(e)[:200]}")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(verify_real_imagery_retrieval())
