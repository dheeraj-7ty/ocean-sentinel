"""Ocean Sentinel Temporal Change Reasoning Pipeline.

Quantifies, tracks, and extracts spatial and temporal changes between sequential
satellite observations (T0 and T1):
1. Strict temporal ordering validation (T0 < T1).
2. Spatial grid compatibility and explicit nearest-neighbor mask reprojection.
3. 4-way discrete mask differencing:
   - PERSISTENT: Detected at both T0 and T1 (T0=1, T1=1)
   - NEW: Detected at T1 but not T0 (T0=0, T1=1)
   - DISAPPEARED: Detected at T0 but not T1 (T0=1, T1=0)
   - UNCHANGED_BACKGROUND: Neither T0 nor T1 (T0=0, T1=0)
4. Continuous score delta analysis (T1_prob - T0_prob) over valid overlapping pixels.
5. Spatial object matching between T0 and T1 candidate detection polygons (IoU-based).
6. Metric area and relative change quantification (with safe zero handling).
7. Geospatial temporal event serialization into RFC 7946 compliant WGS84 GeoJSON.

Scientific Boundary Reminder:
This module measures OBSERVED CHANGE. It does NOT infer causality, drift, origin,
or vessel attribution.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import rasterio
import rasterio.features
import rasterio.warp
from rasterio.crs import CRS
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds, transform as window_transform
from shapely.geometry import MultiPolygon, Polygon, box, mapping, shape
import shapely

from pydantic import BaseModel, Field

from ocean_sentinel.interpretation import (
    calculate_polygon_area_m2,
    validate_prediction_mask,
    validate_probability_raster,
)

logger = logging.getLogger(__name__)


class TemporalError(Exception):
    """Base exception for temporal change analysis errors."""
    pass


class TemporalValidationError(TemporalError):
    """Raised when temporal ordering or timestamp metadata is invalid."""
    pass


class SpatialAlignmentError(TemporalError):
    """Raised when spatial grids or footprints fail alignment validation."""
    pass


class ChangeCategory(str, Enum):
    """Discrete category of observed change between T0 and T1."""
    PERSISTENT = "persistent"
    NEW = "new"
    DISAPPEARED = "disappeared"
    UNCHANGED_BACKGROUND = "unchanged_background"


class TimestampProvenance(str, Enum):
    """Provenance category for an observation acquisition timestamp."""
    VERIFIED_FROM_SOURCE_METADATA = "VERIFIED_FROM_SOURCE_METADATA"
    VERIFIED_FROM_AUTHORITATIVE_MANIFEST = "VERIFIED_FROM_AUTHORITATIVE_MANIFEST"
    EXTERNALLY_SUPPLIED_TEST_TIMESTAMP = "EXTERNALLY_SUPPLIED_TEST_TIMESTAMP"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class MatchedObjectPair(BaseModel):
    """Correlation between a T0 detection polygon and a T1 detection polygon."""
    t0_polygon_id: str = Field(..., description="Identifier of polygon at T0")
    t1_polygon_id: str = Field(..., description="Identifier of polygon at T1")
    area_t0_m2: float = Field(..., ge=0.0, description="Area of T0 polygon in m^2")
    area_t1_m2: float = Field(..., ge=0.0, description="Area of T1 polygon in m^2")
    area_change_m2: float = Field(..., description="Change in area (A_t1 - A_t0) in m^2")
    relative_area_change: Optional[float] = Field(
        default=None,
        description="Relative fractional change ((A_t1 - A_t0) / A_t0). None if A_t0 == 0.",
    )
    overlap_iou: float = Field(..., ge=0.0, le=1.0, description="Spatial Intersection over Union")
    overlap_area_m2: float = Field(..., ge=0.0, description="Intersection area in m^2")
    centroid_displacement_m: float = Field(..., ge=0.0, description="Centroid shift distance in meters")


class TemporalEvent(BaseModel):
    """Geospatially extracted temporal change object (New, Persistent, Disappeared)."""
    event_id: str = Field(..., description="Unique temporal event identifier")
    t0_source: str = Field(..., description="T0 source image/mask identifier")
    t1_source: str = Field(..., description="T1 source image/mask identifier")
    t0_time: str = Field(..., description="T0 acquisition time (ISO UTC)")
    t1_time: str = Field(..., description="T1 acquisition time (ISO UTC)")
    change_type: ChangeCategory = Field(..., description="Category: new, persistent, disappeared")
    geometry: Dict[str, Any] = Field(..., description="WGS84 GeoJSON geometry mapping")
    geometry_crs: str = Field(default="EPSG:4326", description="Declared GeoJSON CRS (RFC 7946 WGS84)")
    pixel_count: int = Field(..., ge=1, description="Count of constituent change pixels")
    area_m2: float = Field(..., ge=0.0, description="Real-world area in m^2")
    area_km2: float = Field(..., ge=0.0, description="Real-world area in km^2")
    area_crs: str = Field(..., description="CRS used for metric area computation")
    area_method: str = Field(..., description="Method used for metric area computation")
    mean_probability_t0: Optional[float] = Field(default=None, description="Mean model score at T0")
    mean_probability_t1: Optional[float] = Field(default=None, description="Mean model score at T1")
    mean_probability_delta: Optional[float] = Field(
        default=None, description="Mean score change (T1_prob - T0_prob)"
    )
    centroid: List[float] = Field(..., description="Centroid [lon, lat]")
    bbox: List[float] = Field(..., description="Bounding box [minx, miny, maxx, maxy]")

    def to_geojson_feature(self) -> Dict[str, Any]:
        """Format event as RFC 7946 compliant GeoJSON Feature."""
        props = {
            "event_id": self.event_id,
            "t0_source": self.t0_source,
            "t1_source": self.t1_source,
            "t0_time": self.t0_time,
            "t1_time": self.t1_time,
            "change_type": self.change_type.value,
            "pixel_count": self.pixel_count,
            "area_m2": round(self.area_m2, 2),
            "area_km2": round(self.area_km2, 6),
            "area_crs": self.area_crs,
            "area_method": self.area_method,
            "mean_probability_t0": (
                round(self.mean_probability_t0, 4) if self.mean_probability_t0 is not None else None
            ),
            "mean_probability_t1": (
                round(self.mean_probability_t1, 4) if self.mean_probability_t1 is not None else None
            ),
            "mean_probability_delta": (
                round(self.mean_probability_delta, 4) if self.mean_probability_delta is not None else None
            ),
            "centroid": [round(c, 6) for c in self.centroid],
            "bbox": [round(b, 6) for b in self.bbox],
        }
        return {
            "type": "Feature",
            "id": self.event_id,
            "geometry": self.geometry,
            "properties": props,
        }


class TemporalReport(BaseModel):
    """Complete summary of temporal change analysis between two observations."""
    t0_source: str
    t1_source: str
    t0_time: str
    t1_time: str
    time_interval_hours: float
    timestamp_provenance: Optional[Dict[str, Any]] = None
    spatial_alignment: Dict[str, Any]
    counts: Dict[str, Any]
    areas_m2: Dict[str, float]
    areas_km2: Dict[str, float]
    pixel_counts: Dict[str, int]
    probability_change_summary: Optional[Dict[str, Any]] = None
    filter_criteria: Dict[str, Any]
    matched_objects: List[MatchedObjectPair]
    events: List[TemporalEvent]
    execution_time_seconds: float

    def to_geojson_feature_collection(self) -> Dict[str, Any]:
        """Format report into GeoJSON FeatureCollection."""
        return {
            "type": "FeatureCollection",
            "name": "ocean_sentinel_temporal_change",
            "metadata": {
                "t0_source": self.t0_source,
                "t1_source": self.t1_source,
                "t0_time": self.t0_time,
                "t1_time": self.t1_time,
                "time_interval_hours": round(self.time_interval_hours, 2),
                "timestamp_provenance": self.timestamp_provenance,
                "spatial_alignment": self.spatial_alignment,
                "counts": self.counts,
                "areas_m2": {k: round(v, 2) for k, v in self.areas_m2.items()},
                "areas_km2": {k: round(v, 6) for k, v in self.areas_km2.items()},
                "pixel_counts": self.pixel_counts,
                "probability_change_summary": self.probability_change_summary,
                "filter_criteria": self.filter_criteria,
                "matched_objects_count": len(self.matched_objects),
                "execution_time_seconds": round(self.execution_time_seconds, 4),
                "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            },
            "features": [e.to_geojson_feature() for e in self.events],
        }


# ---------------------------------------------------------------------------
# Validation & Alignment Functions
# ---------------------------------------------------------------------------


def resolve_temporal_timestamp(
    raster_path: Union[str, Path],
    explicit_time: Optional[Union[str, datetime]] = None,
) -> Tuple[datetime, TimestampProvenance]:
    """Resolve acquisition timestamp and determine its provenance.

    Order of precedence:
    1. Metadata tags embedded in the raster file -> VERIFIED_FROM_SOURCE_METADATA.
    2. Explicit timestamp argument if provided -> EXTERNALLY_SUPPLIED_TEST_TIMESTAMP.
    3. Fails if timestamp cannot be determined.

    Returns (datetime in UTC, TimestampProvenance).
    """
    path = Path(raster_path)
    tag_time_str = None

    if path.is_file():
        try:
            with rasterio.open(path) as src:
                tags = src.tags()
                # Check common satellite timestamp tags
                for key in ("acquisition_time", "datetime", "TIFFTAG_DATETIME", "start_time"):
                    if key in tags and tags[key]:
                        tag_time_str = tags[key]
                        break
        except Exception:
            pass

    if tag_time_str is not None:
        try:
            # Handle ISO format or standard TIFF format "YYYY:MM:DD HH:MM:SS"
            clean_str = tag_time_str.replace("Z", "+00:00")
            if ":" in clean_str[:10]:  # TIFF format
                dt = datetime.strptime(clean_str, "%Y:%m:%d %H:%M:%S")
                tag_dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = datetime.fromisoformat(clean_str)
                tag_dt = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

            if explicit_time is not None:
                exp_dt = (
                    explicit_time if isinstance(explicit_time, datetime)
                    else datetime.fromisoformat(str(explicit_time).replace("Z", "+00:00"))
                )
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                if tag_dt != exp_dt:
                    logger.warning(
                        f"Explicit timestamp '{explicit_time}' conflicts with raster metadata tag '{tag_time_str}'. "
                        f"Enforcing raster metadata '{tag_time_str}' over user input."
                    )
            return tag_dt, TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA
        except Exception:
            logger.warning(f"Could not parse timestamp from TIFF tag: {tag_time_str}")

    if explicit_time is not None:
        if isinstance(explicit_time, datetime):
            dt = explicit_time if explicit_time.tzinfo is not None else explicit_time.replace(tzinfo=timezone.utc)
            return dt, TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP
        try:
            clean_str = explicit_time.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt, TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP
        except Exception as e:
            raise TemporalValidationError(f"Invalid explicit timestamp format '{explicit_time}': {e}") from e

    raise TemporalValidationError(
        f"Missing acquisition timestamp for {path.name}. "
        "Raster tags lack timestamp and no explicit timestamp was provided."
    )


def parse_temporal_timestamp(
    raster_path: Union[str, Path],
    explicit_time: Optional[Union[str, datetime]] = None,
) -> datetime:
    """Resolve and parse the acquisition timestamp for a raster.

    Maintains backwards compatibility by returning datetime in UTC.
    """
    dt, _ = resolve_temporal_timestamp(raster_path, explicit_time)
    return dt


def validate_temporal_ordering(
    t0_time: datetime,
    t1_time: datetime,
) -> float:
    """Ensure strict temporal ordering: t0_time < t1_time.

    Returns time interval in hours.
    """
    if t0_time >= t1_time:
        raise TemporalValidationError(
            f"Temporal ordering violation: T0 acquisition ({t0_time.isoformat()}) "
            f"must be strictly before T1 acquisition ({t1_time.isoformat()})."
        )

    delta_seconds = (t1_time - t0_time).total_seconds()
    return delta_seconds / 3600.0


def check_spatial_overlap(
    t0_bounds: Tuple[float, float, float, float],
    t0_crs: CRS,
    t1_bounds: Tuple[float, float, float, float],
    t1_crs: CRS,
) -> Tuple[bool, float]:
    """Verify that T0 and T1 footprints intersect in WGS84 coordinates.

    Returns (intersects: bool, overlap_fraction: float).
    """
    box0 = box(*t0_bounds)
    box1 = box(*t1_bounds)

    # Reproject to WGS84 for intersection check if necessary
    crs_wgs84 = CRS.from_epsg(4326)
    if t0_crs != crs_wgs84:
        box0 = shape(rasterio.warp.transform_geom(t0_crs, crs_wgs84, mapping(box0)))
    if t1_crs != crs_wgs84:
        box1 = shape(rasterio.warp.transform_geom(t1_crs, crs_wgs84, mapping(box1)))

    if not box0.intersects(box1):
        return False, 0.0

    inter = box0.intersection(box1)
    if inter.is_empty or inter.area <= 0:
        return False, 0.0

    overlap_fraction = inter.area / min(box0.area, box1.area)
    return True, overlap_fraction


def align_temporal_grids(
    t0_mask: np.ndarray,
    t0_transform: Affine,
    t0_crs: CRS,
    t1_mask: np.ndarray,
    t1_transform: Affine,
    t1_crs: CRS,
    t0_prob: Optional[np.ndarray] = None,
    t1_prob: Optional[np.ndarray] = None,
    allow_reprojection: bool = True,
) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray], Optional[np.ndarray], Dict[str, Any]]:
    """Align T1 raster data into the T0 spatial grid.

    If grids match exactly, returns inputs directly.
    If grids differ:
      - Uses Resampling.nearest for the binary mask (guarantees {0, 1}).
      - Uses Resampling.bilinear for continuous probabilities.

    Raises SpatialAlignmentError if footprints do not overlap or reprojection is disallowed.
    """
    grid_identical = (
        (t0_mask.shape == t1_mask.shape)
        and (t0_transform == t1_transform)
        and (t0_crs == t1_crs)
    )

    if grid_identical:
        alignment_meta = {
            "strategy": "exact_grid_match",
            "resampling_mask": "none",
            "resampling_probability": "none",
            "source_crs": t0_crs.to_string(),
            "target_grid_shape": list(t0_mask.shape),
        }
        return t0_mask, t1_mask, t0_prob, t1_prob, alignment_meta

    if not allow_reprojection:
        raise SpatialAlignmentError(
            "Spatial grids differ (shape, transform, or CRS) and allow_reprojection=False."
        )

    # Check that footprints intersect
    t0_h, t0_w = t0_mask.shape
    t1_h, t1_w = t1_mask.shape
    t0_bounds = (
        t0_transform.c,
        t0_transform.f + t0_transform.e * t0_h,
        t0_transform.c + t0_transform.a * t0_w,
        t0_transform.f,
    )
    t1_bounds = (
        t1_transform.c,
        t1_transform.f + t1_transform.e * t1_h,
        t1_transform.c + t1_transform.a * t1_w,
        t1_transform.f,
    )

    overlaps, frac = check_spatial_overlap(t0_bounds, t0_crs, t1_bounds, t1_crs)
    if not overlaps:
        raise SpatialAlignmentError("T0 and T1 rasters have zero spatial overlap.")

    logger.info(
        f"Reprojecting T1 onto T0 spatial grid ({t0_h}x{t0_w}, {t0_crs}). "
        f"Estimated footprint overlap: {frac * 100:.1f}%"
    )

    # 1. Reproject binary mask using NEAREST NEIGHBOR
    t1_aligned_mask = np.zeros_like(t0_mask, dtype=np.uint8)
    reproject(
        source=t1_mask,
        destination=t1_aligned_mask,
        src_transform=t1_transform,
        src_crs=t1_crs,
        dst_transform=t0_transform,
        dst_crs=t0_crs,
        resampling=Resampling.nearest,
    )

    # 2. Reproject probability map using BILINEAR (if present)
    t1_aligned_prob = None
    if t1_prob is not None:
        t1_aligned_prob = np.full(t0_mask.shape, np.nan, dtype=np.float32)
        reproject(
            source=t1_prob,
            destination=t1_aligned_prob,
            src_transform=t1_transform,
            src_crs=t1_crs,
            dst_transform=t0_transform,
            dst_crs=t0_crs,
            resampling=Resampling.bilinear,
        )

    alignment_meta = {
        "strategy": "reprojected_t1_to_t0_grid",
        "resampling_mask": "nearest_neighbor",
        "resampling_probability": "bilinear" if t1_prob is not None else "none",
        "target_crs": t0_crs.to_string(),
        "footprint_overlap_fraction": round(frac, 4),
        "target_grid_shape": list(t0_mask.shape),
    }

    return t0_mask, t1_aligned_mask, t0_prob, t1_aligned_prob, alignment_meta


# ---------------------------------------------------------------------------
# Object Matching Engine
# ---------------------------------------------------------------------------


def extract_candidate_polygons_from_mask(
    mask: np.ndarray,
    transform: Affine,
    crs: CRS,
    prefix: str,
    min_pixels: int = 0,
    min_area_m2: float = 0.0,
) -> List[Tuple[str, Polygon, float]]:
    """Extract individual connected component polygons, IDs, and areas from a mask.

    Applies optional min_pixels and min_area_m2 filtering to maintain consistency
    with detection event extraction.
    """
    shapes_gen = rasterio.features.shapes(
        mask.astype(np.int16),
        mask=(mask == 1),
        transform=transform,
        connectivity=8,
    )

    polys: List[Tuple[str, Polygon, float]] = []
    idx = 1
    for geom_dict, val in shapes_gen:
        if val != 1:
            continue
        geom = shape(geom_dict)
        if not geom.is_valid:
            geom = shapely.make_valid(geom)
        if geom.is_empty:
            continue

        cands = []
        if isinstance(geom, Polygon):
            cands.append(geom)
        elif isinstance(geom, MultiPolygon):
            cands.extend(list(geom.geoms))
        elif hasattr(geom, "geoms"):
            for g in geom.geoms:
                if isinstance(g, Polygon) and not g.is_empty:
                    cands.append(g)

        for p in cands:
            if p.is_empty:
                continue

            area_m2, _, _ = calculate_polygon_area_m2(p, crs)
            if min_area_m2 > 0.0 and area_m2 < min_area_m2:
                continue

            if min_pixels > 0:
                bounds = p.bounds
                win = from_bounds(*bounds, transform=transform).round_offsets().round_lengths()
                w_trans = window_transform(win, transform)
                h_win, w_win = int(win.height), int(win.width)
                if h_win <= 0 or w_win <= 0:
                    continue
                geom_mask = rasterio.features.geometry_mask(
                    [p], out_shape=(h_win, w_win), transform=w_trans, invert=True
                )
                px_count = int(np.sum(geom_mask))
                if px_count < min_pixels:
                    continue

            poly_id = f"{prefix}_obj_{idx:04d}"
            polys.append((poly_id, p, area_m2))
            idx += 1

    return polys


def match_t0_t1_objects(
    t0_polys: List[Tuple[str, Polygon, float]],
    t1_polys: List[Tuple[str, Polygon, float]],
    crs: CRS,
    iou_threshold: float = 0.10,
    one_to_one: bool = False,
) -> List[MatchedObjectPair]:
    """Correlate candidate T0 and T1 objects via spatial Intersection over Union (IoU).

    Matching Semantics:
    -------------------
    - Candidate Overlap Graph (default: one_to_one=False):
      Returns all candidate association edges between T0 and T1 objects where
      spatial IoU >= iou_threshold. In scenes with splits/merges, a single T0 object
      may correlate with multiple T1 objects and vice-versa.
    - Deterministic Greedy Assignment (one_to_one=True):
      Resolves bipartite candidate edges into a 1-to-1 assignment. Candidates are sorted
      descending by IoU, breaking ties deterministically by larger intersection area,
      then lexicographical polygon IDs. Each T0 object is matched to at most one T1 object.
      LIMITATION: This is an objective greedy spatial overlap heuristic for linear tracking,
      not a global combinatorial solver or drift-trajectory physical model.

    Parameters
    ----------
    t0_polys : list[tuple[str, Polygon, float]]
        (id, polygon, area_m2) for T0.
    t1_polys : list[tuple[str, Polygon, float]]
        (id, polygon, area_m2) for T1.
    crs : CRS
        Coordinate reference system.
    iou_threshold : float
        Minimum IoU to consider objects spatially correlated.
    one_to_one : bool
        If True, enforces deterministic 1-to-1 matching. If False, returns all candidate edges.

    Returns
    -------
    matched_pairs : list[MatchedObjectPair]
        Matched object pairs with measured area changes and centroid displacement.
    """
    candidate_matches: List[MatchedObjectPair] = []

    for id0, p0, a0 in t0_polys:
        b0 = p0.bounds
        for id1, p1, a1 in t1_polys:
            b1 = p1.bounds
            # Quick bounding box disjoint check
            if b0[0] > b1[2] or b0[2] < b1[0] or b0[1] > b1[3] or b0[3] < b1[1]:
                continue

            inter = p0.intersection(p1)
            if inter.is_empty or inter.area <= 0:
                continue

            union = p0.union(p1)
            iou = inter.area / union.area if union.area > 0 else 0.0

            if iou >= iou_threshold:
                inter_m2, _, _ = calculate_polygon_area_m2(inter, crs)
                area_change = a1 - a0

                # Safe relative change calculation
                rel_change = (area_change / a0) if a0 > 0.0 else None

                # Centroid shift
                c0 = p0.centroid
                c1 = p1.centroid
                shift_dist_m = 0.0
                if crs.is_projected:
                    shift_dist_m = float(np.hypot(c1.x - c0.x, c1.y - c0.y))
                else:
                    # Metric distance on WGS84 (approximate Euclidean on degree projection)
                    m_per_deg_lat = 111132.954
                    m_per_deg_lon = 111412.84 * np.cos(np.radians(0.5 * (c0.y + c1.y)))
                    dy_m = (c1.y - c0.y) * m_per_deg_lat
                    dx_m = (c1.x - c0.x) * m_per_deg_lon
                    shift_dist_m = float(np.hypot(dx_m, dy_m))

                candidate_matches.append(
                    MatchedObjectPair(
                        t0_polygon_id=id0,
                        t1_polygon_id=id1,
                        area_t0_m2=round(a0, 2),
                        area_t1_m2=round(a1, 2),
                        area_change_m2=round(area_change, 2),
                        relative_area_change=round(rel_change, 4) if rel_change is not None else None,
                        overlap_iou=round(iou, 4),
                        overlap_area_m2=round(inter_m2, 2),
                        centroid_displacement_m=round(shift_dist_m, 2),
                    )
                )

    if not one_to_one:
        return candidate_matches

    # Deterministic greedy 1-to-1 assignment
    # Sort descending by: IoU, intersection area; ascending by: t0_id, t1_id
    candidate_matches.sort(
        key=lambda m: (-m.overlap_iou, -m.overlap_area_m2, m.t0_polygon_id, m.t1_polygon_id)
    )

    assigned_t0: set[str] = set()
    assigned_t1: set[str] = set()
    one_to_one_matches: List[MatchedObjectPair] = []

    for m in candidate_matches:
        if m.t0_polygon_id not in assigned_t0 and m.t1_polygon_id not in assigned_t1:
            one_to_one_matches.append(m)
            assigned_t0.add(m.t0_polygon_id)
            assigned_t1.add(m.t1_polygon_id)

    return one_to_one_matches


# ---------------------------------------------------------------------------
# Core Temporal Change Analysis Engine
# ---------------------------------------------------------------------------


def extract_change_events_from_mask(
    change_mask: np.ndarray,
    change_type: ChangeCategory,
    transform: Affine,
    crs: CRS,
    t0_id: str,
    t1_id: str,
    t0_time_iso: str,
    t1_time_iso: str,
    t0_prob: Optional[np.ndarray] = None,
    t1_prob: Optional[np.ndarray] = None,
    min_pixels: int = 0,
    min_area_m2: float = 0.0,
) -> Tuple[List[TemporalEvent], int, float]:
    """Polygonize a discrete change mask (e.g. NEW or PERSISTENT) into temporal events."""
    shapes_gen = rasterio.features.shapes(
        change_mask.astype(np.int16),
        mask=(change_mask == 1),
        transform=transform,
        connectivity=8,
    )

    h, w = change_mask.shape
    crs_wgs84 = CRS.from_epsg(4326)
    needs_wgs84_reproj = (crs != crs_wgs84)

    events: List[TemporalEvent] = []
    total_area_m2 = 0.0
    idx = 1

    for geom_dict, val in shapes_gen:
        if val != 1:
            continue
        raw_geom = shape(geom_dict)
        clean_geom = shapely.make_valid(raw_geom) if not raw_geom.is_valid else raw_geom

        if clean_geom.is_empty:
            continue

        polys: List[Polygon] = []
        if isinstance(clean_geom, Polygon):
            polys.append(clean_geom)
        elif isinstance(clean_geom, MultiPolygon):
            polys.extend(list(clean_geom.geoms))
        elif hasattr(clean_geom, "geoms"):
            for g in clean_geom.geoms:
                if isinstance(g, Polygon) and not g.is_empty:
                    polys.append(g)

        for poly in polys:
            if poly.is_empty:
                continue

            bounds = poly.bounds
            win = from_bounds(*bounds, transform=transform).round_offsets().round_lengths()
            w_trans = window_transform(win, transform)
            h_win, w_win = int(win.height), int(win.width)
            if h_win <= 0 or w_win <= 0:
                continue

            geom_mask = rasterio.features.geometry_mask(
                [poly], out_shape=(h_win, w_win), transform=w_trans, invert=True
            )
            pixel_count = int(np.sum(geom_mask))
            if pixel_count == 0:
                continue

            area_m2, area_crs, area_method = calculate_polygon_area_m2(poly, crs)
            area_km2 = area_m2 / 1_000_000.0

            # Filter checks
            if min_pixels > 0 and pixel_count < min_pixels:
                continue
            if min_area_m2 > 0.0 and area_m2 < min_area_m2:
                continue

            # Probability score statistics over enclosed pixels
            p0_mean = None
            p1_mean = None
            delta_mean = None

            if t0_prob is not None or t1_prob is not None:
                r0, r1 = int(win.row_off), int(win.row_off + h_win)
                c0, c1 = int(win.col_off), int(win.col_off + w_win)
                r0_c = max(0, min(h, r0))
                r1_c = max(0, min(h, r1))
                c0_c = max(0, min(w, c0))
                c1_c = max(0, min(w, c1))

                mask_slice = geom_mask[: (r1_c - r0_c), : (c1_c - c0_c)]

                if t0_prob is not None:
                    p0_slice = t0_prob[r0_c:r1_c, c0_c:c1_c][mask_slice]
                    p0_fin = p0_slice[np.isfinite(p0_slice)]
                    if len(p0_fin) > 0:
                        p0_mean = float(np.mean(p0_fin))

                if t1_prob is not None:
                    p1_slice = t1_prob[r0_c:r1_c, c0_c:c1_c][mask_slice]
                    p1_fin = p1_slice[np.isfinite(p1_slice)]
                    if len(p1_fin) > 0:
                        p1_mean = float(np.mean(p1_fin))

                if p0_mean is not None and p1_mean is not None:
                    delta_mean = p1_mean - p0_mean

            # Reproject geometry to WGS84 for GeoJSON RFC 7946 compliance if needed
            if needs_wgs84_reproj:
                wgs84_dict = rasterio.warp.transform_geom(crs, crs_wgs84, mapping(poly))
                wgs84_geom = shape(wgs84_dict)
            else:
                wgs84_geom = poly
                wgs84_dict = mapping(poly)

            event_id = f"{t0_id}_{t1_id}_{change_type.value}_{idx:04d}"
            centroid = [float(wgs84_geom.centroid.x), float(wgs84_geom.centroid.y)]
            event_bbox = [float(b) for b in wgs84_geom.bounds]

            event = TemporalEvent(
                event_id=event_id,
                t0_source=t0_id,
                t1_source=t1_id,
                t0_time=t0_time_iso,
                t1_time=t1_time_iso,
                change_type=change_type,
                geometry=wgs84_dict,
                geometry_crs="EPSG:4326",
                pixel_count=pixel_count,
                area_m2=round(area_m2, 2),
                area_km2=round(area_km2, 6),
                area_crs=area_crs,
                area_method=area_method,
                mean_probability_t0=round(p0_mean, 4) if p0_mean is not None else None,
                mean_probability_t1=round(p1_mean, 4) if p1_mean is not None else None,
                mean_probability_delta=round(delta_mean, 4) if delta_mean is not None else None,
                centroid=centroid,
                bbox=event_bbox,
            )

            events.append(event)
            total_area_m2 += area_m2
            idx += 1

    return events, len(events), total_area_m2


def analyze_temporal_change(
    t0_mask_path: Union[str, Path],
    t1_mask_path: Union[str, Path],
    t0_prob_path: Optional[Union[str, Path]] = None,
    t1_prob_path: Optional[Union[str, Path]] = None,
    t0_time: Optional[Union[str, datetime]] = None,
    t1_time: Optional[Union[str, datetime]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    output_prefix: Optional[str] = None,
    min_pixels: int = 0,
    min_area_m2: float = 0.0,
    match_iou_threshold: float = 0.10,
    one_to_one: bool = False,
    allow_reprojection: bool = True,
) -> Tuple[TemporalReport, Optional[Path], Optional[Path]]:
    """Execute end-to-end temporal change reasoning on two sequential observations.

    Parameters
    ----------
    t0_mask_path : str | Path
        Path to T0 binary prediction mask GeoTIFF.
    t1_mask_path : str | Path
        Path to T1 binary prediction mask GeoTIFF.
    t0_prob_path : str | Path | None
        Optional companion probability map for T0.
    t1_prob_path : str | Path | None
        Optional companion probability map for T1.
    t0_time : str | datetime | None
        Acquisition time for T0 (parsed from tags if None).
    t1_time : str | datetime | None
        Acquisition time for T1 (parsed from tags if None).
    output_dir : str | Path | None
        Directory to save output GeoJSON and JSON reports.
    output_prefix : str | None
        Filename prefix for outputs.
    min_pixels : int
        Filter small change regions under this pixel count.
    min_area_m2 : float
        Filter small change regions under this area.
    match_iou_threshold : float
        IoU threshold for matching candidate T0 and T1 objects.
    one_to_one : bool
        If True, enforces deterministic greedy 1-to-1 matching. If False, returns all candidate edges.
    allow_reprojection : bool
        Whether to automatically reproject T1 onto T0 grid if mismatched.

    Returns
    -------
    report : TemporalReport
        Complete temporal analysis report.
    geojson_path : Path | None
        Path to exported GeoJSON FeatureCollection.
    json_path : Path | None
        Path to exported JSON summary report.
    """
    start_time = time.time()

    # 1. Temporal Timestamp Resolution & Validation
    t0_dt, t0_prov = resolve_temporal_timestamp(t0_mask_path, t0_time)
    t1_dt, t1_prov = resolve_temporal_timestamp(t1_mask_path, t1_time)
    interval_hours = validate_temporal_ordering(t0_dt, t1_dt)
    t0_iso = t0_dt.isoformat()
    t1_iso = t1_dt.isoformat()

    timestamp_provenance = {
        "t0_source": Path(t0_mask_path).stem.replace("_mask", ""),
        "t0_provenance": t0_prov.value,
        "t1_source": Path(t1_mask_path).stem.replace("_mask", ""),
        "t1_provenance": t1_prov.value,
        "is_authoritative": (
            t0_prov in (TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA, TimestampProvenance.VERIFIED_FROM_AUTHORITATIVE_MANIFEST)
            and t1_prov in (TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA, TimestampProvenance.VERIFIED_FROM_AUTHORITATIVE_MANIFEST)
        ),
        "rationale": (
            "Authoritative acquisition timestamps verified from source metadata."
            if (t0_prov != TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP and t1_prov != TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP)
            else "Timestamps were supplied externally via CLI/test parameter. Source raster metadata lacks embedded acquisition timestamps."
        ),
    }

    # 2. Ingest and Validate Mask Rasters
    m0_data, m0_trans, m0_crs, m0_dims = validate_prediction_mask(t0_mask_path)
    m1_data, m1_trans, m1_crs, m1_dims = validate_prediction_mask(t1_mask_path)

    # 3. Ingest Companion Probabilities (if present)
    p0_data = None
    if t0_prob_path is not None:
        p0_data = validate_probability_raster(
            t0_prob_path, expected_dims=m0_dims, expected_crs=m0_crs, expected_transform=m0_trans
        )

    p1_data = None
    if t1_prob_path is not None:
        p1_data = validate_probability_raster(
            t1_prob_path, expected_dims=m1_dims, expected_crs=m1_crs, expected_transform=m1_trans
        )

    # 4. Spatial Grid Alignment & Reprojection
    m0_aligned, m1_aligned, p0_aligned, p1_aligned, align_meta = align_temporal_grids(
        t0_mask=m0_data,
        t0_transform=m0_trans,
        t0_crs=m0_crs,
        t1_mask=m1_data,
        t1_transform=m1_trans,
        t1_crs=m1_crs,
        t0_prob=p0_data,
        t1_prob=p1_data,
        allow_reprojection=allow_reprojection,
    )

    # 5. Discrete 4-Way Mask Differencing
    t0_bin = (m0_aligned == 1)
    t1_bin = (m1_aligned == 1)

    persistent_mask = (t0_bin & t1_bin).astype(np.uint8)
    new_mask = ((~t0_bin) & t1_bin).astype(np.uint8)
    disappeared_mask = (t0_bin & (~t1_bin)).astype(np.uint8)
    unchanged_bg_mask = ((~t0_bin) & (~t1_bin)).astype(np.uint8)

    px_persistent = int(np.sum(persistent_mask))
    px_new = int(np.sum(new_mask))
    px_disappeared = int(np.sum(disappeared_mask))
    px_unchanged_bg = int(np.sum(unchanged_bg_mask))

    # 6. Continuous Score Delta Analysis (if both probabilities exist)
    prob_change_summary = None
    if p0_aligned is not None and p1_aligned is not None:
        valid_both = np.isfinite(p0_aligned) & np.isfinite(p1_aligned)
        if np.sum(valid_both) > 0:
            delta_arr = p1_aligned[valid_both] - p0_aligned[valid_both]
            prob_change_summary = {
                "mean_delta": round(float(np.mean(delta_arr)), 5),
                "max_delta": round(float(np.max(delta_arr)), 5),
                "min_delta": round(float(np.min(delta_arr)), 5),
                "std_delta": round(float(np.std(delta_arr)), 5),
                "valid_pixel_count": int(np.sum(valid_both)),
            }

    # 7. Extract Geospatial Change Objects
    t0_stem = Path(t0_mask_path).stem.replace("_mask", "")
    t1_stem = Path(t1_mask_path).stem.replace("_mask", "")

    new_events, n_new, area_new_m2 = extract_change_events_from_mask(
        new_mask, ChangeCategory.NEW, m0_trans, m0_crs, t0_stem, t1_stem, t0_iso, t1_iso,
        p0_aligned, p1_aligned, min_pixels=min_pixels, min_area_m2=min_area_m2
    )
    persistent_events, n_pers, area_pers_m2 = extract_change_events_from_mask(
        persistent_mask, ChangeCategory.PERSISTENT, m0_trans, m0_crs, t0_stem, t1_stem, t0_iso, t1_iso,
        p0_aligned, p1_aligned, min_pixels=min_pixels, min_area_m2=min_area_m2
    )
    disappeared_events, n_disapp, area_disapp_m2 = extract_change_events_from_mask(
        disappeared_mask, ChangeCategory.DISAPPEARED, m0_trans, m0_crs, t0_stem, t1_stem, t0_iso, t1_iso,
        p0_aligned, p1_aligned, min_pixels=min_pixels, min_area_m2=min_area_m2
    )

    all_events = new_events + persistent_events + disappeared_events
    total_changed_area_m2 = area_new_m2 + area_pers_m2 + area_disapp_m2

    # 8. Object Matching (Correlating T0 and T1 candidate polygons)
    t0_polys = extract_candidate_polygons_from_mask(
        m0_aligned, m0_trans, m0_crs, t0_stem, min_pixels=min_pixels, min_area_m2=min_area_m2
    )
    t1_polys = extract_candidate_polygons_from_mask(
        m1_aligned, m0_trans, m0_crs, t1_stem, min_pixels=min_pixels, min_area_m2=min_area_m2
    )
    matched_pairs = match_t0_t1_objects(
        t0_polys, t1_polys, m0_crs, iou_threshold=match_iou_threshold, one_to_one=one_to_one
    )

    elapsed = time.time() - start_time

    # Construct Report
    report = TemporalReport(
        t0_source=t0_stem,
        t1_source=t1_stem,
        t0_time=t0_iso,
        t1_time=t1_iso,
        time_interval_hours=interval_hours,
        timestamp_provenance=timestamp_provenance,
        spatial_alignment=align_meta,
        counts={
            "new_regions": n_new,
            "persistent_regions": n_pers,
            "disappeared_regions": n_disapp,
            "total_change_regions": len(all_events),
            "matched_object_pairs": len(matched_pairs),
            "matching_mode": "one_to_one" if one_to_one else "candidate_associations",
        },
        areas_m2={
            "new_area_m2": round(area_new_m2, 2),
            "persistent_area_m2": round(area_pers_m2, 2),
            "disappeared_area_m2": round(area_disapp_m2, 2),
            "total_changed_area_m2": round(total_changed_area_m2, 2),
        },
        areas_km2={
            "new_area_km2": round(area_new_m2 / 1e6, 6),
            "persistent_area_km2": round(area_pers_m2 / 1e6, 6),
            "disappeared_area_km2": round(area_disapp_m2 / 1e6, 6),
            "total_changed_area_km2": round(total_changed_area_m2 / 1e6, 6),
        },
        pixel_counts={
            "persistent_pixels": px_persistent,
            "new_pixels": px_new,
            "disappeared_pixels": px_disappeared,
            "unchanged_background_pixels": px_unchanged_bg,
        },
        probability_change_summary=prob_change_summary,
        filter_criteria={
            "min_pixels": min_pixels,
            "min_area_m2": min_area_m2,
            "match_iou_threshold": match_iou_threshold,
            "one_to_one": one_to_one,
        },
        matched_objects=matched_pairs,
        events=all_events,
        execution_time_seconds=round(elapsed, 4),
    )

    geojson_path = None
    json_path = None

    if output_dir is not None:
        out_d = Path(output_dir)
        out_d.mkdir(parents=True, exist_ok=True)
        prefix = output_prefix or f"{t0_stem}_to_{t1_stem}"

        geojson_path = out_d / f"{prefix}_temporal_events.geojson"
        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(report.to_geojson_feature_collection(), f, indent=2)

        json_path = out_d / f"{prefix}_temporal_summary.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)

        logger.info(f"Saved temporal GeoJSON to: {geojson_path}")
        logger.info(f"Saved temporal summary JSON to: {json_path}")

    return report, geojson_path, json_path
