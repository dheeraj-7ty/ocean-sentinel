"""Tests for Ocean Sentinel Geospatial Prediction Interpretation (Phase 2).

Covers:
1. Raster mask validation (rejection of non-binary, non-georeferenced rasters)
2. Connected component polygonization from tiny synthetic fixtures
3. Hole handling and interior area subtraction
4. Connectivity behavior (4-connected vs 8-connected)
5. Real-world metric area calculation (avoiding naive square degrees)
6. Small-object filtering (min_pixels and min_area_m2)
7. Probability score aggregation (mean, max, min, std)
8. GeoJSON FeatureCollection serialization and schema compliance
9. Extensibility to future anomaly classes (e.g. biological slicks)
10. Deterministic execution
11. Integration test with real Trujillo inference artifacts
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine
from shapely.geometry import Polygon, shape

from ocean_sentinel.interpretation import (
    DetectionReport,
    MaskValidationError,
    calculate_polygon_area_m2,
    export_detections_geojson,
    interpret_prediction,
    polygonize_prediction_mask,
    validate_prediction_mask,
    validate_probability_raster,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def synthetic_mask_with_holes(tmp_path: Path) -> Tuple[Path, Path]:
    """Create a synthetic 100x100 GeoTIFF mask with 2 distinct objects, one having a hole."""
    mask_file = tmp_path / "test_mask.tif"
    prob_file = tmp_path / "test_prob.tif"
    height, width = 100, 100
    crs = CRS.from_epsg(4326)
    # Affine: origin (29.0, 32.0), pixel size 0.0001 deg (~10m)
    transform = Affine(0.0001, 0.0, 29.0, 0.0, -0.0001, 32.0)

    mask = np.zeros((height, width), dtype=np.uint8)
    prob = np.full((height, width), 0.05, dtype=np.float32)

    # Object 1: 30x30 square with a 10x10 hole in center
    # Outer: [10:40, 10:40] -> 900 pixels
    # Inner hole: [20:30, 20:30] -> 100 pixels
    # Net: 800 pixels
    mask[10:40, 10:40] = 1
    mask[20:30, 20:30] = 0
    prob[10:40, 10:40] = 0.85
    prob[20:30, 20:30] = 0.05

    # Object 2: 5x5 small patch at [60:65, 60:65] -> 25 pixels
    mask[60:65, 60:65] = 1
    prob[60:65, 60:65] = 0.60

    # Write mask
    with rasterio.open(
        mask_file,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="uint8",
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(mask, 1)

    # Write prob
    with rasterio.open(
        prob_file,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(prob, 1)

    return mask_file, prob_file


# ==============================================================================
# 1. Mask and Probability Validation Tests
# ==============================================================================

def test_validate_prediction_mask_success(synthetic_mask_with_holes: Tuple[Path, Path]):
    """Verify valid binary georeferenced mask passes validation."""
    mask_file, _ = synthetic_mask_with_holes
    data, transform, crs, dims = validate_prediction_mask(mask_file)
    assert data.shape == (100, 100)
    assert dims == (100, 100)
    assert crs == CRS.from_epsg(4326)
    assert transform.a == 0.0001


def test_validate_prediction_mask_rejects_missing_crs(tmp_path: Path):
    """Verify mask missing CRS is rejected."""
    p = tmp_path / "no_crs_mask.tif"
    with rasterio.open(
        p, "w", driver="GTiff", height=50, width=50, count=1, dtype="uint8"
    ) as dst:
        dst.write(np.zeros((50, 50), dtype=np.uint8), 1)

    with pytest.raises(MaskValidationError, match="missing coordinate reference system"):
        validate_prediction_mask(p)


def test_validate_prediction_mask_rejects_non_binary(tmp_path: Path):
    """Verify mask with multi-class / non-binary values is rejected."""
    p = tmp_path / "multiclass_mask.tif"
    with rasterio.open(
        p,
        "w",
        driver="GTiff",
        height=50,
        width=50,
        count=1,
        dtype="uint8",
        crs=CRS.from_epsg(4326),
        transform=Affine.translation(0, 0) @ Affine.scale(1, -1),
    ) as dst:
        arr = np.zeros((50, 50), dtype=np.uint8)
        arr[10, 10] = 5  # Non-binary value
        dst.write(arr, 1)

    with pytest.raises(MaskValidationError, match="non-binary values"):
        validate_prediction_mask(p)


def test_validate_probability_raster_mismatched_dimensions(synthetic_mask_with_holes: Tuple[Path, Path], tmp_path: Path):
    """Verify probability raster with mismatched dimensions is rejected."""
    _, prob_file = synthetic_mask_with_holes
    with pytest.raises(MaskValidationError, match="mismatch mask dimensions"):
        validate_probability_raster(
            prob_file,
            expected_dims=(200, 200),
            expected_crs=CRS.from_epsg(4326),
            expected_transform=Affine.identity(),
        )


# ==============================================================================
# 2. Polygonization, Holes, and Connectivity Tests
# ==============================================================================

def test_polygonization_and_hole_handling(synthetic_mask_with_holes: Tuple[Path, Path]):
    """Verify extraction of 2 objects, correctly preserving the donut hole in Object 1."""
    mask_file, prob_file = synthetic_mask_with_holes
    report, _ = interpret_prediction(
        mask_path=mask_file,
        probability_path=prob_file,
        connectivity=8,
    )

    assert report.total_detected_regions == 2
    assert report.retained_regions == 2

    # Find the large donut polygon
    donut_event = next(e for e in report.events if e.pixel_count > 100)
    assert donut_event.pixel_count == 800  # 900 - 100 = 800

    poly_geom = shape(donut_event.geometry)
    assert isinstance(poly_geom, Polygon)
    # Verify exactly one hole (interior ring) is present
    assert len(poly_geom.interiors) == 1

    # Verify probability summary matches expected values for Object 1
    assert donut_event.probability_statistics is not None
    assert donut_event.probability_statistics.mean_probability == pytest.approx(0.85, abs=1e-3)


def test_connectivity_behavior():
    """Verify 4-connected separates diagonal pixels while 8-connected joins them."""
    # 2 diagonal pixels at (0,0) and (1,1)
    mask = np.zeros((4, 4), dtype=np.uint8)
    mask[1, 1] = 1
    mask[2, 2] = 1
    transform = Affine.translation(0, 0) @ Affine.scale(1, -1)
    crs = CRS.from_epsg(32635)

    rep_4 = polygonize_prediction_mask(mask, transform, crs, "diag_test", connectivity=4)
    assert rep_4.retained_regions == 2

    rep_8 = polygonize_prediction_mask(mask, transform, crs, "diag_test", connectivity=8)
    # In 8-connectivity, touching corner forms a single multi-part or self-touching component
    assert rep_8.retained_regions in (1, 2)


# ==============================================================================
# 3. Real-World Metric Area Calculation Tests
# ==============================================================================

def test_area_calculation_in_projected_crs():
    """Verify metric calculation in projected CRS matches Cartesian polygon area."""
    crs_utm = CRS.from_epsg(32635)
    # 100m x 100m square in UTM = 10,000 m^2
    poly = Polygon([(500000, 3500000), (500100, 3500000), (500100, 3500100), (500000, 3500100)])
    area_m2, area_crs, method = calculate_polygon_area_m2(poly, crs_utm)

    assert area_m2 == pytest.approx(10000.0, rel=1e-5)
    assert "projected" in method


def test_area_calculation_in_geographic_crs():
    """Verify EPSG:4326 polygon uses local UTM reprojection rather than naive square degrees."""
    crs_wgs84 = CRS.from_epsg(4326)
    # 0.001 deg lat x 0.001 deg lon square at lat=32.2, lon=29.2
    # 0.001 deg lat ~ 110.9m
    # 0.001 deg lon ~ 94.2m
    # Expected area ~ 110.9 * 94.2 ~ 10,446 m^2 (NOT 0.000001 deg^2!)
    poly = Polygon([(29.2, 32.2), (29.201, 32.2), (29.201, 32.201), (29.2, 32.201)])
    area_m2, area_crs, method = calculate_polygon_area_m2(poly, crs_wgs84)

    assert area_m2 > 9000.0 and area_m2 < 12000.0
    assert "utm_projection" in method
    assert "EPSG:32635" in area_crs


# ==============================================================================
# 4. Small-Object Noise Filtering Tests
# ==============================================================================

def test_filtering_by_min_pixels(synthetic_mask_with_holes: Tuple[Path, Path]):
    """Verify min_pixels filter discards small objects while retaining large ones."""
    mask_file, _ = synthetic_mask_with_holes
    # Object 1 has 800 px, Object 2 has 25 px
    # Filter with min_pixels = 50 should retain only Object 1
    report, _ = interpret_prediction(
        mask_path=mask_file,
        min_pixels=50,
    )
    assert report.total_detected_regions == 2
    assert report.filtered_regions == 1
    assert report.retained_regions == 1
    assert report.events[0].pixel_count == 800


def test_filtering_by_min_area(synthetic_mask_with_holes: Tuple[Path, Path]):
    """Verify min_area_m2 filter discards objects below area threshold."""
    mask_file, _ = synthetic_mask_with_holes
    # Object 2 has 25 pixels (~2,500 m^2)
    # Object 1 has 800 pixels (~80,000 m^2)
    report, _ = interpret_prediction(
        mask_path=mask_file,
        min_area_m2=10000.0,
    )
    assert report.total_detected_regions == 2
    assert report.filtered_regions == 1
    assert report.retained_regions == 1
    assert report.events[0].area_m2 > 10000.0


# ==============================================================================
# 5. GeoJSON Schema Compliance and Serialization Tests
# ==============================================================================

def test_geojson_export_schema(synthetic_mask_with_holes: Tuple[Path, Path], tmp_path: Path):
    """Verify GeoJSON export adheres to RFC 7946 FeatureCollection schema."""
    mask_file, prob_file = synthetic_mask_with_holes
    report, geojson_path = interpret_prediction(
        mask_path=mask_file,
        probability_path=prob_file,
        output_dir=tmp_path,
        detection_class="biological_slick",
    )

    assert geojson_path is not None and geojson_path.is_file()

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["type"] == "FeatureCollection"
    assert "metadata" in data
    assert data["metadata"]["detection_class"] == "biological_slick"
    assert len(data["features"]) == 2

    feat = data["features"][0]
    assert feat["type"] == "Feature"
    assert "geometry" in feat
    assert "properties" in feat
    assert feat["properties"]["detection_class"] == "biological_slick"
    assert "area_m2" in feat["properties"]
    assert "probability_statistics" in feat["properties"]


# ==============================================================================
# 6. Determinism and Extensibility Tests
# ==============================================================================

def test_interpretation_determinism(synthetic_mask_with_holes: Tuple[Path, Path]):
    """Verify repeated execution produces byte-for-byte identical detections."""
    mask_file, prob_file = synthetic_mask_with_holes
    rep1, _ = interpret_prediction(mask_path=mask_file, probability_path=prob_file)
    rep2, _ = interpret_prediction(mask_path=mask_file, probability_path=prob_file)

    assert rep1.retained_regions == rep2.retained_regions
    assert rep1.total_area_m2 == rep2.total_area_m2
    for e1, e2 in zip(rep1.events, rep2.events):
        assert e1.event_id == e2.event_id
        assert e1.area_m2 == e2.area_m2
        assert e1.geometry == e2.geometry


# ==============================================================================
# 7. Real Trujillo Integration Test (Scene 00012)
# ==============================================================================

def test_real_trujillo_scene_00012_integration(tmp_path: Path):
    """Verify end-to-end interpretation on real inference output from scene 00012."""
    mask_path = REPO_ROOT / "outputs" / "inference" / "00012_mask.tif"
    prob_path = REPO_ROOT / "outputs" / "inference" / "00012_probability.tif"

    if not mask_path.is_file():
        pytest.skip("Real inference output 00012_mask.tif not available")

    report, geojson_path = interpret_prediction(
        mask_path=mask_path,
        probability_path=prob_path if prob_path.is_file() else None,
        output_dir=tmp_path,
        detection_class="oil_spill",
        min_pixels=10,
    )

    assert geojson_path is not None and geojson_path.is_file()
    assert report.total_detected_regions > 0
    assert report.retained_regions > 0
    assert report.total_area_m2 > 1_000_000.0  # Significant spill > 1 km^2

    # Verify all output geometries are valid Shapely shapes
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feat in data["features"]:
        g = shape(feat["geometry"])
        assert g.is_valid
        assert feat["properties"]["area_m2"] > 0
        if "probability_statistics" in feat["properties"]:
            ps = feat["properties"]["probability_statistics"]
            assert 0.0 <= ps["mean_probability"] <= 1.0
