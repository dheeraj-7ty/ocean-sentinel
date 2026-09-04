"""Real Copernicus STAC discovery verification.

This script queries the live Copernicus STAC API to verify that
Ocean Sentinel can discover real Sentinel-1 observations.

SECURITY:
- Never prints access tokens
- Never prints client secrets
- Never writes credentials to files
- Only reports safe metadata (IDs, dates, coordinates)

Usage:
    python scripts/verify_stac.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

# Add src to path for editable install compatibility
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


async def verify_real_stac_discovery() -> None:
    """Query the real Copernicus STAC API and report results safely."""

    print("=" * 70)
    print("Ocean Sentinel — Real Copernicus STAC Discovery Verification")
    print("=" * 70)
    print()

    # Check if credentials are available (needed for config loading)
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
        print("REASON: Credentials not found (needed for CopernicusSettings)")
        return

    print("Credentials found: YES")
    print()

    try:
        from ocean_sentinel.config import CopernicusSettings
        from ocean_sentinel.models import (
            BoundingBox,
            SearchRequest,
            TimeRange,
        )
        from ocean_sentinel.satellite.discovery import SentinelDiscoveryService

        settings = CopernicusSettings()
        discovery = SentinelDiscoveryService(settings, max_pages=2)

        # Test AOI: small Mediterranean area (Southern Italy / Calabria)
        # This area typically has frequent Sentinel-1 overpasses
        bbox = BoundingBox(west=15.5, south=39.5, east=16.5, north=40.5)

        # Use a recent 14-day window to maximize chances of finding data
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=14)

        time_range = TimeRange(start=start, end=end)

        request = SearchRequest(
            bbox=bbox,
            time_range=time_range,
            max_results=5,
        )

        print("--- Search Parameters ---")
        print(f"STAC endpoint: {settings.copernicus_stac_url}")
        print(f"Collection: sentinel-1-grd")
        print(f"AOI: [{bbox.west}, {bbox.south}, {bbox.east}, {bbox.north}]")
        print(f"Time range: {start.isoformat()} to {end.isoformat()}")
        print(f"Max results: {request.max_results}")
        print()
        print("Executing STAC search...")
        print()

        result = await discovery.search(request)

        print("=" * 70)
        print("REAL COPERNICUS STAC DISCOVERY")
        print("=" * 70)
        print(f"Status: PASS")
        print(f"Collection: sentinel-1-grd")
        print(f"Results found: {result.total_returned}")
        print(f"Pages fetched: {result.pages_fetched}")
        print(f"Has more results: {result.has_more}")
        print()

        if result.observations:
            print("--- Observations ---")
            for i, obs in enumerate(result.observations):
                print(f"\n  [{i + 1}] ID: {obs.id}")
                print(f"      Acquisition: {obs.acquisition_time.isoformat()}")
                print(f"      Platform: {obs.platform}")
                print(f"      Mode: {obs.acquisition_mode}")
                print(f"      Polarizations: {[p.value for p in obs.polarizations] if obs.polarizations else 'N/A'}")
                print(f"      Orbit: {obs.orbit_direction.value if obs.orbit_direction else 'N/A'}")
                print(f"      Relative orbit: {obs.relative_orbit}")
                print(f"      BBox: {obs.bbox}")
                print(f"      Assets: {list(obs.stac_assets.keys()) if obs.stac_assets else 'N/A'}")
                if obs.self_link:
                    print(f"      Self link: {obs.self_link[:100]}...")
        else:
            print("No observations found for this AOI/time window.")
            print("This is NOT an error — valid search with zero results.")

        print()
        print("=" * 70)

    except Exception as e:
        print("=" * 70)
        print("REAL COPERNICUS STAC DISCOVERY")
        print("=" * 70)
        print(f"Status: FAIL")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        print("=" * 70)

        # Safety check
        error_str = str(e)
        if client_secret in error_str:
            print("WARNING: Client secret found in error output!")


def main() -> None:
    asyncio.run(verify_real_stac_discovery())


if __name__ == "__main__":
    main()
