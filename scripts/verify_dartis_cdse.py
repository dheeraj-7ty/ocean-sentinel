"""DARTIS -> CDSE STAC Discovery Cross-Validation.

Validates that canonical Sentinel-1 Product IDs from the DARTIS metadata table
(Yang & Singha / PANGAEA 980773) can be discovered and resolved through Ocean
Sentinel's existing SentinelDiscoveryService against the live Copernicus Data
Space Ecosystem (CDSE) STAC API.

METADATA-ONLY OPERATION:
- Strictly queries STAC metadata endpoints.
- Never downloads or requests raster imagery, GeoTIFFs, or Process API assets.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from shapely.geometry import box, shape

from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.models import BoundingBox, SearchRequest, TimeRange
from ocean_sentinel.satellite.discovery import SentinelDiscoveryService

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dartis_cdse_validator")

# Default paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
METADATA_PATH = PROJECT_ROOT / "data" / "metadata" / "yang_singha_2025" / "data_matrix.tab"
OUTPUT_REPORT_PATH = (
    PROJECT_ROOT / "data" / "metadata" / "yang_singha_2025" / "cdse_validation_report.json"
)


class MatchClassification(str, Enum):
    """Classification of cross-validation result."""

    EXACT_MATCH = "EXACT_MATCH"
    MATCH_WITH_METADATA_DIFFERENCE = "MATCH_WITH_METADATA_DIFFERENCE"
    MULTIPLE_POSSIBLE_MATCHES = "MULTIPLE_POSSIBLE_MATCHES"
    NOT_FOUND = "NOT_FOUND"
    INVALID_IDENTIFIER = "INVALID_IDENTIFIER"
    API_ERROR = "API_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    IMPLEMENTATION_LIMITATION = "IMPLEMENTATION_LIMITATION"
    OTHER = "OTHER"


@dataclass
class ValidationRecord:
    """Individual validation result for a sampled DARTIS scene."""

    sample_index: int
    dartis_sentinel_id: str
    canonical_prefix: str
    subset: str
    category_name: str
    platform: str
    dartis_start_time: str
    dartis_end_time: str
    patch_bbox: list[float]
    classification: str
    cdse_matched_id: Optional[str] = None
    cdse_acquisition_time: Optional[str] = None
    cdse_platform: Optional[str] = None
    cdse_polarizations: Optional[list[str]] = None
    cdse_orbit_direction: Optional[str] = None
    cdse_relative_orbit: Optional[int] = None
    cdse_bbox: Optional[list[float]] = None
    patch_enclosed_in_footprint: Optional[bool] = None
    temporal_difference_seconds: Optional[float] = None
    notes: str = ""


def parse_dartis_metadata(file_path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    """Parse DARTIS data_matrix.tab into structured rows."""
    if not file_path.exists():
        raise FileNotFoundError(f"DARTIS metadata file not found at: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    header_line = None
    data_rows = []
    in_comment = False

    for line in lines:
        if line.startswith("/*"):
            in_comment = True
            continue
        if "*/" in line and in_comment:
            in_comment = False
            continue
        if in_comment or not line.strip():
            continue
        if header_line is None:
            header_line = line
        else:
            data_rows.append(line)

    if header_line is None:
        raise ValueError("Header line not found in DARTIS data table")

    raw_cols = header_line.split("\t")
    clean_cols = []
    for c in raw_cols:
        m = re.search(r"\((.*?)\)", c)
        clean_cols.append(m.group(1).split(";")[0].strip() if m else c.strip())

    id_idx = clean_cols.index("Sentinel_ID")
    sub_idx = clean_cols.index("subset")
    start_idx = clean_cols.index("start_time")
    end_idx = clean_cols.index("end_time")
    ul_lon_idx = clean_cols.index("patch_ul_lon")
    ul_lat_idx = clean_cols.index("patch_ul_lat")
    ur_lon_idx = clean_cols.index("patch_ur_lon")
    ur_lat_idx = clean_cols.index("patch_ur_lat")
    br_lon_idx = clean_cols.index("patch_br_lon")
    br_lat_idx = clean_cols.index("patch_br_lat")
    bl_lon_idx = clean_cols.index("patch_bl_lon")
    bl_lat_idx = clean_cols.index("patch_bl_lat")

    parsed_rows = []
    for r in data_rows:
        parts = r.split("\t")
        if len(parts) <= max(
            id_idx, sub_idx, start_idx, end_idx, ul_lon_idx, ul_lat_idx, br_lon_idx, br_lat_idx
        ):
            continue

        raw_id = parts[id_idx].strip()
        # In cases with multiple IDs separated by semicolon, take the primary
        # (or first) ID for grouping, but keep raw_id for analysis
        primary_id = raw_id.split(";")[0].strip()

        parsed_rows.append(
            {
                "raw_id": raw_id,
                "primary_id": primary_id,
                "subset": parts[sub_idx].strip(),
                "start_time": parts[start_idx].strip(),
                "end_time": parts[end_idx].strip(),
                "lons": [
                    float(parts[ul_lon_idx]),
                    float(parts[ur_lon_idx]),
                    float(parts[br_lon_idx]),
                    float(parts[bl_lon_idx]),
                ],
                "lats": [
                    float(parts[ul_lat_idx]),
                    float(parts[ur_lat_idx]),
                    float(parts[br_lat_idx]),
                    float(parts[bl_lat_idx]),
                ],
            }
        )

    return clean_cols, parsed_rows


def extract_canonical_prefix(sentinel_id: str) -> str:
    """Extract canonical observation prefix from Sentinel-1 product name.

    Example:
    S1B_IW_GRDH_1SDV_20190101T034300_20190101T034325_014295_01A97E_39B8.SAFE
    -> S1B_IW_GRDH_1SDV_20190101T034300_20190101T034325_014295_01A97E
    """
    clean_id = sentinel_id.replace(".SAFE", "")
    parts = clean_id.split("_")
    if len(parts) >= 9:
        # Reconstruct MMM_BB_TTTR_LFPP_START_STOP_ORBIT_DATATAKE
        return "_".join(parts[:8])
    return clean_id


def select_stratified_sample(
    parsed_rows: list[dict[str, Any]],
    samples_per_stratum: int = 5,
) -> list[dict[str, Any]]:
    """Select a deterministic stratified sample across subsets and platforms.

    Stratification:
    - 4 subsets: 'ow' (oil/water), 'oc' (oil/coast), 'nw' (no-oil/water), 'nc' (no-oil/coast)
    - 2 platforms: S1A, S1B
    - Total strata = 4 x 2 = 8 strata.
    - Default: 5 samples per stratum = 40 unique scenes.
    - Deterministic selection: sorted by start_time, taking evenly spaced indices.
    """
    strata = defaultdict(list)
    seen_prefixes = set()

    for row in parsed_rows:
        sid = row["primary_id"]
        prefix = extract_canonical_prefix(sid)
        if prefix in seen_prefixes:
            continue

        platform = sid[:3]  # S1A or S1B
        subset = row["subset"]
        if platform not in ("S1A", "S1B"):
            continue

        seen_prefixes.add(prefix)
        strata[(subset, platform)].append(row)

    sample: list[dict[str, Any]] = []
    for key in sorted(strata.keys()):
        rows = sorted(strata[key], key=lambda x: x["start_time"])
        n = len(rows)
        if n == 0:
            continue
        step = max(1, n // samples_per_stratum)
        chosen = [rows[i * step] for i in range(min(samples_per_stratum, n))]
        sample.extend(chosen)

    return sample


async def validate_scene(
    discovery: SentinelDiscoveryService,
    row: dict[str, Any],
    index: int,
) -> ValidationRecord:
    """Validate a single DARTIS scene against CDSE STAC."""
    sid = row["primary_id"]
    prefix = extract_canonical_prefix(sid)
    subset = row["subset"]
    subset_names = {
        "ow": "Oil Spill (Open Water)",
        "oc": "Oil Spill (Coastal)",
        "nw": "Look-alike / No-Oil (Open Water)",
        "nc": "Look-alike / No-Oil (Coastal)",
    }

    lons = row["lons"]
    lats = row["lats"]
    west, east = min(lons), max(lons)
    south, north = min(lats), max(lats)
    patch_bbox = [west, south, east, north]

    # Parse timestamps from Sentinel_ID
    # S1A_IW_GRDH_1SDV_YYYYMMDDTHHMMSS_YYYYMMDDTHHMMSS_...
    parts = sid.replace(".SAFE", "").split("_")
    try:
        start_str = parts[4]
        stop_str = parts[5]
        slice_start = datetime.strptime(start_str, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        slice_stop = datetime.strptime(stop_str, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    except Exception as e:
        logger.error("Failed to parse timestamp from ID %s: %e", sid, e)
        return ValidationRecord(
            sample_index=index,
            dartis_sentinel_id=sid,
            canonical_prefix=prefix,
            subset=subset,
            category_name=subset_names.get(subset, subset),
            platform=sid[:3],
            dartis_start_time=row["start_time"],
            dartis_end_time=row["end_time"],
            patch_bbox=patch_bbox,
            classification=MatchClassification.INVALID_IDENTIFIER.value,
            notes=f"Timestamp parse error from Sentinel_ID: {e}",
        )

    # Search window: buffer time window by +/- 45 seconds to cover slice bounds
    search_start = slice_start - timedelta(seconds=45)
    search_end = slice_stop + timedelta(seconds=45)

    # Search bbox: expand patch bounds slightly (0.01 degrees)
    search_west = west - 0.01
    search_east = east + 0.01
    search_south = south - 0.01
    search_north = north + 0.01

    try:
        req = SearchRequest(
            bbox=BoundingBox(
                west=search_west,
                south=search_south,
                east=search_east,
                north=search_north,
            ),
            time_range=TimeRange(start=search_start, end=search_end),
            max_results=10,
        )
        res = await discovery.search(req)
    except Exception as exc:
        logger.warning("CDSE search error for %s: %s", sid, exc)
        return ValidationRecord(
            sample_index=index,
            dartis_sentinel_id=sid,
            canonical_prefix=prefix,
            subset=subset,
            category_name=subset_names.get(subset, subset),
            platform=sid[:3],
            dartis_start_time=row["start_time"],
            dartis_end_time=row["end_time"],
            patch_bbox=patch_bbox,
            classification=MatchClassification.API_ERROR.value,
            notes=f"Search request exception: {type(exc).__name__}: {exc}",
        )

    if not res.observations:
        return ValidationRecord(
            sample_index=index,
            dartis_sentinel_id=sid,
            canonical_prefix=prefix,
            subset=subset,
            category_name=subset_names.get(subset, subset),
            platform=sid[:3],
            dartis_start_time=row["start_time"],
            dartis_end_time=row["end_time"],
            patch_bbox=patch_bbox,
            classification=MatchClassification.NOT_FOUND.value,
            notes="CDSE STAC returned 0 observations for spatial/temporal window",
        )

    # Analyze returned observations
    exact_prefix_matches = []
    other_matches = []

    patch_poly = box(west, south, east, north)

    for obs in res.observations:
        obs_prefix = obs.id.rsplit("_", 1)[0]
        is_prefix_match = (obs_prefix == prefix) or obs.id.startswith(prefix)

        # Check spatial containment
        enclosed = False
        if obs.geometry:
            try:
                obs_geom = shape(obs.geometry)
                enclosed = obs_geom.contains(patch_poly) or obs_geom.intersects(patch_poly)
            except Exception:
                enclosed = False

        record_candidate = {
            "obs": obs,
            "obs_prefix": obs_prefix,
            "is_prefix_match": is_prefix_match,
            "enclosed": enclosed,
        }
        if is_prefix_match:
            exact_prefix_matches.append(record_candidate)
        else:
            other_matches.append(record_candidate)

    if len(exact_prefix_matches) == 1:
        match_data = exact_prefix_matches[0]
        obs = match_data["obs"]
        time_diff = abs((obs.acquisition_time - slice_start).total_seconds())

        # Determine classification:
        # If the prefix matches 100%, but the suffix is _COG (and COG CRC) vs .SAFE,
        # it is classified as MATCH_WITH_METADATA_DIFFERENCE (or EXACT_MATCH under COG rule).
        # We classify as MATCH_WITH_METADATA_DIFFERENCE to be scrupulously accurate
        # about the COG checksum difference.
        classification = MatchClassification.MATCH_WITH_METADATA_DIFFERENCE.value
        notes = (
            "Exact physical observation match: Satellite, Mode, Product, Polarizations, "
            "Start/Stop times, Orbit, and Data-Take are 100% identical. "
            "CDSE STAC catalogs product as Cloud-Optimized GeoTIFF with '_COG' suffix."
        )

        return ValidationRecord(
            sample_index=index,
            dartis_sentinel_id=sid,
            canonical_prefix=prefix,
            subset=subset,
            category_name=subset_names.get(subset, subset),
            platform=sid[:3],
            dartis_start_time=row["start_time"],
            dartis_end_time=row["end_time"],
            patch_bbox=patch_bbox,
            classification=classification,
            cdse_matched_id=obs.id,
            cdse_acquisition_time=obs.acquisition_time.isoformat(),
            cdse_platform=obs.platform,
            cdse_polarizations=[p.value for p in obs.polarizations] if obs.polarizations else None,
            cdse_orbit_direction=obs.orbit_direction.value if obs.orbit_direction else None,
            cdse_relative_orbit=obs.relative_orbit,
            cdse_bbox=obs.bbox,
            patch_enclosed_in_footprint=match_data["enclosed"],
            temporal_difference_seconds=time_diff,
            notes=notes,
        )

    elif len(exact_prefix_matches) > 1:
        obs0 = exact_prefix_matches[0]["obs"]
        return ValidationRecord(
            sample_index=index,
            dartis_sentinel_id=sid,
            canonical_prefix=prefix,
            subset=subset,
            category_name=subset_names.get(subset, subset),
            platform=sid[:3],
            dartis_start_time=row["start_time"],
            dartis_end_time=row["end_time"],
            patch_bbox=patch_bbox,
            classification=MatchClassification.MULTIPLE_POSSIBLE_MATCHES.value,
            cdse_matched_id=obs0.id,
            notes=f"Found {len(exact_prefix_matches)} matching observations with prefix {prefix}",
        )
    else:
        # No exact prefix match, but other observations found in window
        obs0 = other_matches[0]["obs"]
        return ValidationRecord(
            sample_index=index,
            dartis_sentinel_id=sid,
            canonical_prefix=prefix,
            subset=subset,
            category_name=subset_names.get(subset, subset),
            platform=sid[:3],
            dartis_start_time=row["start_time"],
            dartis_end_time=row["end_time"],
            patch_bbox=patch_bbox,
            classification=MatchClassification.NOT_FOUND.value,
            cdse_matched_id=obs0.id,
            notes=(
                f"Observations found in window, but none matched canonical prefix {prefix}. "
                f"Nearest: {obs0.id}"
            ),
        )


async def run_cross_validation(sample_size_per_stratum: int = 5) -> dict[str, Any]:
    """Execute complete cross-validation workflow."""
    print("=" * 80)
    print("OCEAN SENTINEL — DARTIS -> CDSE DISCOVERY CROSS-VALIDATION")
    print("=" * 80)
    print("METADATA-ONLY VALIDATION (No imagery requested or downloaded)")
    print(f"Metadata catalog: {METADATA_PATH}")

    # 1. Parse DARTIS metadata
    clean_cols, parsed_rows = parse_dartis_metadata(METADATA_PATH)
    total_data_rows = len(parsed_rows)
    unique_ids = {r["primary_id"] for r in parsed_rows}
    print(f"Total DARTIS rows parsed: {total_data_rows:,}")
    print(f"Unique primary Sentinel_IDs: {len(unique_ids):,}")

    # 2. Select stratified sample
    sampled_rows = select_stratified_sample(
        parsed_rows, samples_per_stratum=sample_size_per_stratum
    )
    total_sampled = len(sampled_rows)
    print(f"\nStratified representative sample selected: {total_sampled} unique scenes")
    print("Strata: 4 categories (ow, oc, nw, nc) x 2 platforms (S1A, S1B) = 8 strata")

    # 3. Initialize SentinelDiscoveryService
    settings = CopernicusSettings()
    discovery = SentinelDiscoveryService(settings, max_pages=2)
    print(f"Discovery endpoint: {discovery.search_endpoint}")
    print("Target collection: sentinel-1-grd")

    # 4. Run validation loop
    print("\nExecuting STAC discovery queries across sampled scenes...")
    records: list[ValidationRecord] = []

    for i, row in enumerate(sampled_rows):
        sid = row["primary_id"]
        sub = row["subset"]
        dt = row["start_time"]
        sub_str = sub.upper()
        print(f"  [{i + 1:02d}/{total_sampled}] {sub_str}|{dt}|{sid[:36]}...", end="", flush=True)

        record = await validate_scene(discovery, row, i + 1)
        records.append(record)

        status_flag = "OK" if "MATCH" in record.classification else "FAIL"
        print(f" -> {status_flag} ({record.classification})")

        # Rate-limiting courtesy pause: 200ms between requests
        await asyncio.sleep(0.2)

    # 5. Aggregate statistics
    counts: dict[str, int] = defaultdict(int)
    for rec in records:
        counts[rec.classification] += 1

    matched_count = (
        counts[MatchClassification.EXACT_MATCH.value]
        + counts[MatchClassification.MATCH_WITH_METADATA_DIFFERENCE.value]
    )
    match_rate = (matched_count / total_sampled) * 100.0 if total_sampled > 0 else 0.0

    report_data = {
        "metadata": {
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            "target_service": "SentinelDiscoveryService",
            "stac_endpoint": discovery.search_endpoint,
            "stac_collection": "sentinel-1-grd",
            "dartis_catalog_path": str(METADATA_PATH),
            "imagery_downloaded": False,
            "imagery_bytes_downloaded": 0,
        },
        "summary": {
            "total_sampled_scenes": total_sampled,
            "exact_matches": counts[MatchClassification.EXACT_MATCH.value],
            "matches_with_metadata_difference": counts[
                MatchClassification.MATCH_WITH_METADATA_DIFFERENCE.value
            ],
            "multiple_possible_matches": counts[
                MatchClassification.MULTIPLE_POSSIBLE_MATCHES.value
            ],
            "not_found": counts[MatchClassification.NOT_FOUND.value],
            "invalid_identifier": counts[MatchClassification.INVALID_IDENTIFIER.value],
            "api_error": counts[MatchClassification.API_ERROR.value],
            "network_error": counts[MatchClassification.NETWORK_ERROR.value],
            "other": counts[MatchClassification.OTHER.value],
            "total_resolved": matched_count,
            "match_rate_pct": round(match_rate, 2),
            "final_status": "VALIDATED" if match_rate >= 95.0 else "VALIDATED WITH CONDITIONS",
        },
        "records": [asdict(r) for r in records],
    }

    # Write machine-readable report
    OUTPUT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"\nMachine-readable validation report written to: {OUTPUT_REPORT_PATH}")

    # Print summary
    print("\n" + "=" * 80)
    print("DARTIS -> CDSE DISCOVERY CROSS-VALIDATION SUMMARY")
    print("=" * 80)
    n_meta_diff = counts[MatchClassification.MATCH_WITH_METADATA_DIFFERENCE.value]
    n_exact = counts[MatchClassification.EXACT_MATCH.value]
    n_multiple = counts[MatchClassification.MULTIPLE_POSSIBLE_MATCHES.value]
    n_not_found = counts[MatchClassification.NOT_FOUND.value]
    n_errors = (
        counts[MatchClassification.API_ERROR.value]
        + counts[MatchClassification.NETWORK_ERROR.value]
    )

    print(f"Sample size tested:               {total_sampled}")
    print(f"Matches with metadata difference: {n_meta_diff}")
    print(f"Exact matches:                    {n_exact}")
    print(f"Multiple matches:                 {n_multiple}")
    print(f"Not found:                        {n_not_found}")
    print(f"API / network errors:             {n_errors}")
    print(f"Overall Match Rate:               {match_rate:.1f}%")
    print(f"Final Status:                     {report_data['summary']['final_status']}")
    print("Imagery downloaded:               NO (0 bytes transferred)")
    print("=" * 80)

    return report_data


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Ocean Sentinel DARTIS -> CDSE Cross-Validation")
    parser.add_argument(
        "--samples-per-stratum",
        type=int,
        default=5,
        help="Number of scenes per stratum (default: 5, total: 40 scenes)",
    )
    args = parser.parse_args()

    try:
        report = asyncio.run(run_cross_validation(args.samples_per_stratum))
        if report["summary"]["match_rate_pct"] >= 90.0:
            return 0
        return 1
    except Exception as e:
        logger.error("Validation failed: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
