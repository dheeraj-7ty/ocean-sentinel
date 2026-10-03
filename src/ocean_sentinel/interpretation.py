"""Ocean Sentinel Geospatial Prediction Interpretation Pipeline.

Converts raw pixel-level segmentation prediction masks and probability maps
into structured, georeferenced maritime detection events:
1. Binary prediction mask validation (CRS, affine transform, band count, binary values).
2. Connected component extraction into vector geometries via rasterio.features.shapes.
3. Topological hole preservation and geometry validity enforcement (via shapely).
4. Real-world metric area calculation in square meters (using local UTM / equal-area projection).
5. Aggregation of continuous probability statistics (mean, max, min, std) per polygon.
6. Explicit, configurable small-object noise filtering (min_pixels, min_area_m2).
7. Structured detection event serialization into RFC 7946 compliant GeoJSON.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import rasterio
import rasterio.features
import rasterio.warp
from rasterio.crs import CRS
from rasterio.transform import Affine
from rasterio.windows import from_bounds, transform as window_transform
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
import shapely

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class InterpretationError(Exception):
    """Base exception for geospatial interpretation errors."""
    pass


class MaskValidationError(InterpretationError):
    """Raised when a prediction mask violates the input contract."""
    pass


# ---------------------------------------------------------------------------
# Structured Event Models
# ---------------------------------------------------------------------------


class ProbabilityStatistics(BaseModel):
    """Continuous model prediction score statistics over polygon pixels.

    Note: These are raw sigmoid model scores, NOT calibrated probabilistic confidence.
    """
    mean_probability: float = Field(..., description="Mean model score over enclosed pixels")
    max_probability: float = Field(..., description="Maximum model score over enclosed pixels")
    min_probability: float = Field(..., description="Minimum model score over enclosed pixels")
    std_probability: float = Field(..., description="Standard deviation of model score")


class DetectionEvent(BaseModel):
    """Individual connected maritime detection object (e.g. oil slick)."""
    event_id: str = Field(..., description="Unique event identifier")
    source_image: str = Field(..., description="Identifier or filename of source image")
    detection_class: str = Field(..., description="Classification category (e.g. 'oil_spill')")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry mapping in source CRS")
    geometry_crs: str = Field(..., description="Declared CRS of the geometry coordinates")
    pixel_count: int = Field(..., ge=1, description="Number of constituent raster pixels")
    area_m2: float = Field(..., ge=0.0, description="Real-world geodesic/projected area in square meters")
    area_km2: float = Field(..., ge=0.0, description="Real-world area in square kilometers")
    area_crs: str = Field(..., description="CRS used for metric area computation")
    area_method: str = Field(..., description="Projection or calculation method used for area")
    centroid: List[float] = Field(..., description="[longitude, latitude] or [x, y] of centroid")
    bbox: List[float] = Field(..., description="Bounding box [minx, miny, maxx, maxy]")
    probability_statistics: Optional[ProbabilityStatistics] = Field(
        default=None,
        description="Score statistics (if probability raster was provided)",
    )
    threshold: Optional[float] = Field(
        default=None,
        description="Decision threshold used to generate the source mask",
    )

    def to_geojson_feature(self) -> Dict[str, Any]:
        """Format detection event as a standard GeoJSON Feature dictionary."""
        props = {
            "event_id": self.event_id,
            "source_image": self.source_image,
            "detection_class": self.detection_class,
            "pixel_count": self.pixel_count,
            "area_m2": round(self.area_m2, 2),
            "area_km2": round(self.area_km2, 6),
            "geometry_crs": self.geometry_crs,
            "area_crs": self.area_crs,
            "area_method": self.area_method,
            "centroid": [round(c, 6) for c in self.centroid],
            "bbox": [round(b, 6) for b in self.bbox],
            "threshold": self.threshold,
        }
        if self.probability_statistics is not None:
            props["probability_statistics"] = {
                "mean_probability": round(self.probability_statistics.mean_probability, 5),
                "max_probability": round(self.probability_statistics.max_probability, 5),
                "min_probability": round(self.probability_statistics.min_probability, 5),
                "std_probability": round(self.probability_statistics.std_probability, 5),
            }

        return {
            "type": "Feature",
            "id": self.event_id,
            "geometry": self.geometry,
            "properties": props,
        }


class DetectionReport(BaseModel):
    """Collection of detected events and associated geospatial interpretation metadata."""
    source_image: str
    source_crs: str
    detection_class: str
    threshold: Optional[float] = None
    total_detected_regions: int
    filtered_regions: int
    retained_regions: int
    total_area_m2: float
    total_area_km2: float
    filter_criteria: Dict[str, Any]
    execution_time_seconds: float
    events: List[DetectionEvent]

    def to_geojson_feature_collection(self) -> Dict[str, Any]:
        """Serialize full report into an RFC 7946 compliant GeoJSON FeatureCollection."""
        return {
            "type": "FeatureCollection",
            "name": "ocean_sentinel_detections",
            "crs": {
                "type": "name",
                "properties": {
                    "name": self.source_crs,
                },
            },
            "metadata": {
                "source_image": self.source_image,
                "source_crs": self.source_crs,
                "detection_class": self.detection_class,
                "threshold": self.threshold,
                "total_detected_regions": self.total_detected_regions,
                "filtered_regions": self.filtered_regions,
                "retained_regions": self.retained_regions,
                "total_area_m2": round(self.total_area_m2, 2),
                "total_area_km2": round(self.total_area_km2, 6),
                "filter_criteria": self.filter_criteria,
                "execution_time_seconds": round(self.execution_time_seconds, 4),
                "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            },
            "features": [e.to_geojson_feature() for e in self.events],
        }


# ---------------------------------------------------------------------------
# Validation Functions
# ---------------------------------------------------------------------------


def validate_prediction_mask(
    mask_path: Union[str, Path],
) -> Tuple[np.ndarray, Affine, CRS, Tuple[int, int]]:
    """Inspect and validate a prediction mask GeoTIFF.

    Parameters
    ----------
    mask_path : str | Path
        Path to the binary mask GeoTIFF.

    Returns
    -------
    mask_data : np.ndarray
        2D uint8 array (H, W).
    transform : Affine
        Affine geotransform matrix.
    crs : CRS
        Coordinate reference system.
    dimensions : tuple[int, int]
        (height, width).

    Raises
    ------
    MaskValidationError
        If file violates band count, CRS, transform, or dimension requirements.
    """
    p = Path(mask_path)
    if not p.is_file():
        raise MaskValidationError(f"Prediction mask file not found: {p}")

    try:
        with rasterio.open(p) as src:
            if src.count != 1:
                raise MaskValidationError(
                    f"Expected single-band prediction mask, got {src.count} bands in {p.name}"
                )
            if src.crs is None:
                raise MaskValidationError(
                    f"Prediction mask is missing coordinate reference system (CRS): {p.name}"
                )
            if src.transform is None or src.transform.is_identity:
                raise MaskValidationError(
                    f"Prediction mask lacks a non-trivial affine geotransform: {p.name}"
                )
            if src.height <= 0 or src.width <= 0:
                raise MaskValidationError(
                    f"Invalid raster dimensions ({src.height}, {src.width}) in {p.name}"
                )

            data = src.read(1)
            transform = src.transform
            crs = src.crs
            dims = (src.height, src.width)
    except MaskValidationError:
        raise
    except Exception as e:
        raise MaskValidationError(f"Failed to read mask GeoTIFF {p}: {e}") from e

    # Ensure binary values: only 0, 1 (or 255 for nodata)
    unique_vals = set(np.unique(data))
    allowed_vals = {0, 1, 255}
    if not unique_vals.issubset(allowed_vals):
        raise MaskValidationError(
            f"Prediction mask contains non-binary values {unique_vals - allowed_vals} in {p.name}. "
            f"Expected only 0 (background), 1 (oil), and optional 255 (nodata)."
        )

    # Normalize to strictly uint8 {0, 1}
    binary_mask = (data == 1).astype(np.uint8)

    return binary_mask, transform, crs, dims


def validate_probability_raster(
    prob_path: Union[str, Path],
    expected_dims: Tuple[int, int],
    expected_crs: CRS,
    expected_transform: Affine,
) -> np.ndarray:
    """Inspect and validate an optional companion probability GeoTIFF.

    Parameters
    ----------
    prob_path : str | Path
        Path to probability GeoTIFF.
    expected_dims : tuple[int, int]
        (height, width) expected from mask.
    expected_crs : CRS
        CRS expected from mask.
    expected_transform : Affine
        Affine transform expected from mask.

    Returns
    -------
    prob_data : np.ndarray
        2D float32 array (H, W).

    Raises
    ------
    MaskValidationError
        If dimensions, CRS, or transform do not match the mask.
    """
    p = Path(prob_path)
    if not p.is_file():
        raise MaskValidationError(f"Probability raster file not found: {p}")

    try:
        with rasterio.open(p) as src:
            if src.count != 1:
                raise MaskValidationError(
                    f"Expected 1-band probability raster, got {src.count} in {p.name}"
                )
            if (src.height, src.width) != expected_dims:
                raise MaskValidationError(
                    f"Probability dimensions ({src.height}, {src.width}) mismatch "
                    f"mask dimensions {expected_dims} in {p.name}"
                )
            if src.crs != expected_crs:
                raise MaskValidationError(
                    f"Probability CRS ({src.crs}) does not match mask CRS ({expected_crs}) in {p.name}"
                )
            if src.transform != expected_transform:
                raise MaskValidationError(
                    f"Probability affine transform does not match mask transform in {p.name}"
                )

            prob_data = src.read(1).astype(np.float32)
    except MaskValidationError:
        raise
    except Exception as e:
        raise MaskValidationError(f"Failed to read probability GeoTIFF {p}: {e}") from e

    return prob_data


# ---------------------------------------------------------------------------
# Real-World Metric Area Calculation
# ---------------------------------------------------------------------------


def calculate_polygon_area_m2(
    geom: Union[Polygon, MultiPolygon],
    crs: CRS,
) -> Tuple[float, str, str]:
    """Calculate the real-world surface area in square meters.

    Does NOT use naive `geom.area` on geographic coordinates (EPSG:4326),
    which yields square degrees.

    Strategy:
    1. If the CRS is already a projected metric coordinate system (e.g. UTM),
       uses the projected Cartesian area directly.
    2. If the CRS is geographic (e.g. EPSG:4326 WGS84), projects the geometry
       into the appropriate local Universal Transverse Mercator (UTM) zone
       derived from the geometry centroid coordinates.

    Parameters
    ----------
    geom : Polygon | MultiPolygon
        Shapely geometry in the source CRS.
    crs : CRS
        Coordinate reference system of the geometry.

    Returns
    -------
    area_m2 : float
        Surface area in square meters.
    area_crs : str
        CRS code used for metric calculation.
    area_method : str
        Description of projection technique.
    """
    if geom.is_empty:
        return 0.0, crs.to_string(), "empty_geometry"

    # Case 1: Already projected with metric units
    if crs.is_projected:
        units = getattr(crs, "linear_units", "").lower()
        if units in ("metre", "meter", "m"):
            return float(geom.area), crs.to_string(), "projected_source_crs"

    # Case 2: Geographic coordinates (e.g. EPSG:4326)
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y

    # Determine local UTM zone
    zone = int(np.floor((lon + 180.0) / 6.0)) + 1
    zone = max(1, min(60, zone))
    hemisphere = "N" if lat >= 0 else "S"
    utm_epsg = (32600 if lat >= 0 else 32700) + zone
    utm_crs = CRS.from_epsg(utm_epsg)

    try:
        geom_dict = mapping(geom)
        reprojected_dict = rasterio.warp.transform_geom(crs, utm_crs, geom_dict)
        reprojected_shape = shape(reprojected_dict)
        area_m2 = float(reprojected_shape.area)
        return area_m2, f"EPSG:{utm_epsg}", f"utm_projection_zone_{zone}{hemisphere}"
    except Exception as e:
        logger.warning(
            f"UTM reprojection failed for centroid ({lon}, {lat}): {e}. "
            "Falling back to authalic cosine approximation."
        )
        # Cosine-corrected authalic fallback: 1 deg lat ~ 111,132.9m
        m_per_deg_lat = 111132.954
        m_per_deg_lon = 111412.84 * np.cos(np.radians(lat))
        approx_area_m2 = float(geom.area * m_per_deg_lat * m_per_deg_lon)
        return approx_area_m2, "EPSG:4326", "authalic_cosine_approximation"


# ---------------------------------------------------------------------------
# Core Polygonization and Interpretation Engine
# ---------------------------------------------------------------------------


def polygonize_prediction_mask(
    mask: np.ndarray,
    transform: Affine,
    crs: CRS,
    source_image_id: str,
    probability_data: Optional[np.ndarray] = None,
    connectivity: int = 8,
    min_pixels: int = 0,
    min_area_m2: float = 0.0,
    detection_class: str = "oil_spill",
    threshold: Optional[float] = None,
) -> DetectionReport:
    """Transform binary raster mask into structured geospatial detection events.

    Parameters
    ----------
    mask : np.ndarray
        2D binary array (H, W), values {0, 1}.
    transform : Affine
        Affine geotransform.
    crs : CRS
        Coordinate reference system.
    source_image_id : str
        Identifier or filename of source image.
    probability_data : np.ndarray | None
        Optional companion probability map (H, W).
    connectivity : int
        Pixel connectivity: 4 or 8 (default 8).
    min_pixels : int
        Minimum pixel count threshold for noise rejection (default 0).
    min_area_m2 : float
        Minimum area in m^2 for noise rejection (default 0.0).
    detection_class : str
        Classification label (default 'oil_spill').
    threshold : float | None
        Operating decision threshold.

    Returns
    -------
    report : DetectionReport
        Comprehensive detection report containing all retained events and metadata.
    """
    start_time = time.time()
    h, w = mask.shape

    if connectivity not in (4, 8):
        raise ValueError(f"Connectivity must be 4 or 8, got {connectivity}")

    # 1. Raster-to-Vector extraction via rasterio.features.shapes
    shapes_generator = rasterio.features.shapes(
        mask.astype(np.int16),
        mask=(mask == 1),
        transform=transform,
        connectivity=connectivity,
    )

    events: List[DetectionEvent] = []
    total_detected = 0
    filtered_count = 0
    total_area_m2 = 0.0

    raw_shapes_count = 0
    for geom_dict, val in shapes_generator:
        if val != 1:
            continue

        raw_shapes_count += 1
        raw_geom = shape(geom_dict)

        # Topological repair if necessary
        if not raw_geom.is_valid:
            clean_geom = shapely.make_valid(raw_geom)
        else:
            clean_geom = raw_geom

        if clean_geom.is_empty:
            continue

        # Extract constituent polygons if make_valid produced a collection
        poly_candidates: List[Polygon] = []
        if isinstance(clean_geom, Polygon):
            poly_candidates.append(clean_geom)
        elif isinstance(clean_geom, MultiPolygon):
            poly_candidates.extend(list(clean_geom.geoms))
        elif hasattr(clean_geom, "geoms"):
            for g in clean_geom.geoms:
                if isinstance(g, Polygon) and not g.is_empty:
                    poly_candidates.append(g)

        for poly in poly_candidates:
            if poly.is_empty:
                continue

            total_detected += 1

            # Bounding window calculation
            bounds = poly.bounds
            win = from_bounds(*bounds, transform=transform).round_offsets().round_lengths()
            w_trans = window_transform(win, transform)
            h_win, w_win = int(win.height), int(win.width)

            if h_win <= 0 or w_win <= 0:
                filtered_count += 1
                continue

            # Rasterize polygon in window to get exact constituent pixels
            geom_mask = rasterio.features.geometry_mask(
                [poly], out_shape=(h_win, w_win), transform=w_trans, invert=True
            )
            pixel_count = int(np.sum(geom_mask))

            if pixel_count == 0:
                filtered_count += 1
                continue

            # Area calculation in square meters
            area_m2, area_crs, area_method = calculate_polygon_area_m2(poly, crs)
            area_km2 = area_m2 / 1_000_000.0

            # Filter checks
            if min_pixels > 0 and pixel_count < min_pixels:
                filtered_count += 1
                continue
            if min_area_m2 > 0.0 and area_m2 < min_area_m2:
                filtered_count += 1
                continue

            # Probability score statistics (if companion raster provided)
            prob_stats: Optional[ProbabilityStatistics] = None
            if probability_data is not None:
                r0, r1 = int(win.row_off), int(win.row_off + h_win)
                c0, c1 = int(win.col_off), int(win.col_off + w_win)
                # Clamp to raster boundaries safely
                r0_c = max(0, min(h, r0))
                r1_c = max(0, min(h, r1))
                c0_c = max(0, min(w, c0))
                c1_c = max(0, min(w, c1))

                sub_prob = probability_data[r0_c:r1_c, c0_c:c1_c]
                # Slice mask to clamped shape if window overflowed
                mask_slice = geom_mask[: (r1_c - r0_c), : (c1_c - c0_c)]
                pixel_probs = sub_prob[mask_slice]
                finite_probs = pixel_probs[np.isfinite(pixel_probs)]

                if len(finite_probs) > 0:
                    prob_stats = ProbabilityStatistics(
                        mean_probability=float(np.mean(finite_probs)),
                        max_probability=float(np.max(finite_probs)),
                        min_probability=float(np.min(finite_probs)),
                        std_probability=float(np.std(finite_probs)),
                    )

            event_idx = len(events) + 1
            event_id = f"{source_image_id}_det_{event_idx:04d}"

            event = DetectionEvent(
                event_id=event_id,
                source_image=source_image_id,
                detection_class=detection_class,
                geometry=mapping(poly),
                geometry_crs=crs.to_string(),
                pixel_count=pixel_count,
                area_m2=round(area_m2, 2),
                area_km2=round(area_km2, 6),
                area_crs=area_crs,
                area_method=area_method,
                centroid=[float(poly.centroid.x), float(poly.centroid.y)],
                bbox=[float(b) for b in bounds],
                probability_statistics=prob_stats,
                threshold=threshold,
            )

            events.append(event)
            total_area_m2 += area_m2

    elapsed = time.time() - start_time

    return DetectionReport(
        source_image=source_image_id,
        source_crs=crs.to_string(),
        detection_class=detection_class,
        threshold=threshold,
        total_detected_regions=total_detected,
        filtered_regions=filtered_count,
        retained_regions=len(events),
        total_area_m2=round(total_area_m2, 2),
        total_area_km2=round(total_area_m2 / 1_000_000.0, 6),
        filter_criteria={
            "min_pixels": min_pixels,
            "min_area_m2": min_area_m2,
            "connectivity": connectivity,
        },
        execution_time_seconds=round(elapsed, 4),
        events=events,
    )


def export_detections_geojson(
    report: DetectionReport,
    output_path: Union[str, Path],
) -> Path:
    """Save detection report as an RFC 7946 compliant GeoJSON file.

    Parameters
    ----------
    report : DetectionReport
        Computed detection report.
    output_path : str | Path
        Destination `.geojson` file path.

    Returns
    -------
    saved_path : Path
        Absolute path to the saved file.
    """
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    fc = report.to_geojson_feature_collection()
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=2)

    logger.info(f"Saved detection GeoJSON to: {out_p}")
    return out_p


def interpret_prediction(
    mask_path: Union[str, Path],
    probability_path: Optional[Union[str, Path]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    output_prefix: Optional[str] = None,
    min_pixels: int = 0,
    min_area_m2: float = 0.0,
    connectivity: int = 8,
    detection_class: str = "oil_spill",
    threshold: Optional[float] = 0.22,
) -> Tuple[DetectionReport, Optional[Path]]:
    """End-to-end interpretation of an inference prediction.

    Parameters
    ----------
    mask_path : str | Path
        Path to prediction mask GeoTIFF.
    probability_path : str | Path | None
        Optional companion probability GeoTIFF.
    output_dir : str | Path | None
        Directory to save output GeoJSON. If None, does not write to disk.
    output_prefix : str | None
        Prefix for output file. Defaults to mask stem.
    min_pixels : int
        Minimum pixel count threshold for noise filtering.
    min_area_m2 : float
        Minimum area in m^2 for noise filtering.
    connectivity : int
        Pixel connectivity (4 or 8, default 8).
    detection_class : str
        Category label (default 'oil_spill').
    threshold : float | None
        Operating threshold.

    Returns
    -------
    report : DetectionReport
        Structured detection report.
    geojson_path : Path | None
        Path to written GeoJSON file, or None if output_dir was None.
    """
    m_path = Path(mask_path)
    binary_mask, transform, crs, dims = validate_prediction_mask(m_path)

    prob_data = None
    if probability_path is not None:
        p_path = Path(probability_path)
        if p_path.is_file():
            prob_data = validate_probability_raster(
                p_path, expected_dims=dims, expected_crs=crs, expected_transform=transform
            )

    source_stem = m_path.stem
    if source_stem.endswith("_mask"):
        source_id = source_stem[:-5]
    else:
        source_id = source_stem

    report = polygonize_prediction_mask(
        mask=binary_mask,
        transform=transform,
        crs=crs,
        source_image_id=source_id,
        probability_data=prob_data,
        connectivity=connectivity,
        min_pixels=min_pixels,
        min_area_m2=min_area_m2,
        detection_class=detection_class,
        threshold=threshold,
    )

    geojson_path = None
    if output_dir is not None:
        out_d = Path(output_dir)
        prefix = output_prefix or source_id
        geojson_path = out_d / f"{prefix}_detections.geojson"
        export_detections_geojson(report, geojson_path)

    return report, geojson_path
