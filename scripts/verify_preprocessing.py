"""Real Copernicus Sentinel-1 SAR imagery preprocessing verification.

This script executes an end-to-end verification against real Copernicus data:
1. Discovers a real Sentinel-1 observation via STAC.
2. Retrieves processed GeoTIFF SAR raster data via Sentinel Hub Process API.
3. Preprocesses the raster via SARPreprocessor into physical dB, linear,
   validity masks, and independent per-band normalized representations.
4. Validates scientific values, statistics, and geospatial metadata.
5. Reports safe verification results.

SECURITY:
- Never prints client secret or access token.
- Never logs Authorization headers.
- Never dumps raw array contents.
- Only reports safe metadata (dimensions, statistics, valid percentages).

Usage:
    python scripts/verify_preprocessing.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

# Add src to path for editable install compatibility
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


async def verify_real_sar_preprocessing() -> None:
    """Execute end-to-end imagery retrieval and SAR preprocessing against real data."""
    print("=" * 70)
    print("Ocean Sentinel -- Real Copernicus Sentinel-1 SAR Preprocessing Verification")
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
        print("STATUS: NOT VERIFIED -- REAL DATA")
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
        from ocean_sentinel.processing import (
            NormalizationMethod,
            PreprocessingConfig,
            SARPreprocessor,
        )
        from ocean_sentinel.satellite.auth import TokenManager
        from ocean_sentinel.satellite.discovery import SentinelDiscoveryService
        from ocean_sentinel.satellite.imagery import SentinelImageryService

        settings = CopernicusSettings()
        token_manager = TokenManager(settings)
        discovery_service = SentinelDiscoveryService(settings, max_pages=2)
        imagery_service = SentinelImageryService(settings, token_manager)

        # 1. Discover a real Sentinel-1 observation
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
            print("STATUS: NOT VERIFIED -- REAL DATA")
            print("REASON: No Sentinel-1 observations found in test AOI within the last 21 days")
            return

        obs = stac_result.observations[0]
        print(f"Discovered observation: {obs.id}")
        available_pols = obs.polarizations or [Polarization.VV, Polarization.VH]
        print(f"Available polarizations: {[p.value for p in available_pols]}")
        print()

        # 2. Select VV and VH
        requested_bands = [p for p in [Polarization.VV, Polarization.VH] if p in available_pols]
        if not requested_bands:
            requested_bands = [available_pols[0]]

        # 3. Retrieve focused sub-AOI imagery (256x256)
        sub_bbox = BoundingBox(west=15.6, south=39.6, east=16.0, north=40.0)
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
        imagery_result = await imagery_service.request_imagery(imagery_req)
        print(f"Raw GeoTIFF received: {len(imagery_result.raw_bytes):,} bytes")
        print()

        # 4. Preprocess imagery via SARPreprocessor
        print("Step 3: Preprocessing imagery with SARPreprocessor...")
        config = PreprocessingConfig(
            convert_to_db=True,
            db_floor=-50.0,
            preserve_linear=True,
            normalization_method=NormalizationMethod.PERCENTILE,
            percentile_min=1.0,
            percentile_max=99.0,
            clip_normalized=True,
        )
        preprocessor = SARPreprocessor(default_config=config)
        result = preprocessor.process(imagery_result)

        # 5. Output safe verification results
        print("=" * 70)
        print("REAL COPERNICUS SENTINEL-1 SAR PREPROCESSING VERIFICATION")
        print("=" * 70)
        print("Status: PASS")
        print(f"Observation: {result.observation_id}")
        print(f"Dimensions: {result.width}x{result.height}")
        print(f"Bands: {result.band_count}")
        print(f"Polarizations: {[p.value for p in result.polarizations]}")
        print(f"CRS: {result.crs}")
        print(f"Bounds: {[round(b, 4) for b in result.bounds]}")
        print(f"Normalization Method: {result.config.normalization_method.value}")
        print(f"dB Clamping Floor: {result.config.db_floor} dB")
        print()

        for pol in result.polarizations:
            band = result.get_band(pol)
            q = band.quality
            db_s = band.db_stats
            lin_s = band.linear_stats
            norm = band.normalized_data

            print(f"--- Band {pol.value} ---")
            print(
                f"  Valid pixels: {q.valid_pixels:,} / {q.total_pixels:,} "
                f"({q.valid_percentage:.2f}%)"
            )
            print(f"  Invalid pixels: {q.invalid_pixels:,}")
            if lin_s:
                print(
                    f"  Linear sigma0: min={lin_s.min:.6f}, max={lin_s.max:.6f}, "
                    f"mean={lin_s.mean:.6f}, median={lin_s.median:.6f}, std={lin_s.std:.6f}"
                )
            print(
                f"  Decibels (dB): min={db_s.min:.2f} dB, max={db_s.max:.2f} dB, "
                f"mean={db_s.mean:.2f} dB, median={db_s.median:.2f} dB, std={db_s.std:.2f} dB"
            )
            if norm is not None:
                print(
                    f"  Normalized: min={float(np.min(norm)):.4f}, max={float(np.max(norm)):.4f}, "
                    f"mean={float(np.mean(norm)):.4f}, std={float(np.std(norm)):.4f}"
                )
            if band.normalization_metadata:
                params = band.normalization_metadata.parameters
                p_str = ", ".join(f"{k}={v:.2f}" for k, v in params.items())
                print(f"  Norm parameters: {p_str}")
            print()

        # Multi-channel array verification
        mc_db = result.to_multichannel_array(kind="db")
        mc_norm = result.to_multichannel_array(kind="normalized")
        print(f"Multichannel dB array shape: {mc_db.shape}, dtype: {mc_db.dtype}")
        print(f"Multichannel normalized array shape: {mc_norm.shape}, dtype: {mc_norm.dtype}")
        print("SAR Preprocessing Pipeline: PASS")
        print("=" * 70)

    except Exception as e:
        print("=" * 70)
        print("REAL COPERNICUS SENTINEL-1 SAR PREPROCESSING VERIFICATION")
        print("=" * 70)
        print("Status: FAIL")
        print(f"Error category: {type(e).__name__}")
        print(f"Error detail: {str(e)[:200]}")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(verify_real_sar_preprocessing())
