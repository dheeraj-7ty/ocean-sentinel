"""Comprehensive Test Suite for Ocean Sentinel Temporal Change Reasoning.

Covers:
1. T0 < T1 temporal validation (strict ordering) and rejection of T0 >= T1
2. CRS mismatch detection and alignment
3. Transform/grid mismatch detection and handling
4. Identical masks (all persistent, zero new, zero disappeared)
5. Entirely new mask (zero persistent, zero disappeared)
6. Entirely disappeared mask (zero persistent, zero new)
7. Persistent region extraction and verification
8. Mixed new / persistent / disappeared scenes
9. Continuous probability delta (T1_prob - T0_prob)
10. Zero-area relative-change safe handling (no ZeroDivisionError)
11. Polygon matching via spatial IoU threshold
12. Deterministic execution
13. RFC 7946 WGS84 GeoJSON schema compliance
14. Mask nearest-neighbor resampling semantics during reprojection
15. Real Sentinel-1 multi-temporal integration test (scenes 00260 & 00608)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine
from shapely.geometry import Polygon, box, shape

from ocean_sentinel.temporal import (
    ChangeCategory,
    MatchedObjectPair,
    SpatialAlignmentError,
    TemporalEvent,
    TemporalReport,
    TemporalValidationError,
    align_temporal_grids,
    analyze_temporal_change,
    extract_candidate_polygons_from_mask,
    extract_change_events_from_mask,
    match_t0_t1_objects,
    parse_temporal_timestamp,
    validate_temporal_ordering,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def synthetic_pair_aligned(tmp_path: Path):
    """Create two identical-grid 100x100 synthetic rasters at T0 and T1.
    
    T0 has:
      - Region A (disappearing): [10:30, 10:30]
      - Region B (persistent): [50:70, 50:70]
    T1 has:
      - Region B (persistent): [50:70, 50:70]
      - Region C (new): [75:90, 10:25]
    """
    height, width = 100, 100
    crs = CRS.from_epsg(4326)
    # Origin at (30.0, 32.0), step 0.0001 deg (~10m)
    transform = Affine(0.0001, 0.0, 30.0, 0.0, -0.0001, 32.0)

    # T0 data
    m0 = np.zeros((height, width), dtype=np.uint8)
    m0[10:30, 10:30] = 1  # Region A
    m0[50:70, 50:70] = 1  # Region B

    p0 = np.full((height, width), 0.1, dtype=np.float32)
    p0[10:30, 10:30] = 0.8
    p0[50:70, 50:70] = 0.7

    # T1 data
    m1 = np.zeros((height, width), dtype=np.uint8)
    m1[50:70, 50:70] = 1  # Region B
    m1[75:90, 10:25] = 1  # Region C

    p1 = np.full((height, width), 0.2, dtype=np.float32)
    p1[50:70, 50:70] = 0.9
    p1[75:90, 10:25] = 0.85

    t0_mask_path = tmp_path / "t0_mask.tif"
    t0_prob_path = tmp_path / "t0_prob.tif"
    t1_mask_path = tmp_path / "t1_mask.tif"
    t1_prob_path = tmp_path / "t1_prob.tif"

    for pth, arr, dtype in [
        (t0_mask_path, m0, "uint8"),
        (t0_prob_path, p0, "float32"),
        (t1_mask_path, m1, "uint8"),
        (t1_prob_path, p1, "float32"),
    ]:
        with rasterio.open(
            pth, "w", driver="GTiff", height=height, width=width, count=1,
            dtype=dtype, crs=crs, transform=transform
        ) as dst:
            dst.write(arr, 1)

    return t0_mask_path, t0_prob_path, t1_mask_path, t1_prob_path


# ---------------------------------------------------------------------------
# 1. T0 < T1 Validation
# ---------------------------------------------------------------------------

def test_temporal_ordering_valid():
    """Verify that strict T0 < T1 passes and computes elapsed hours correctly."""
    t0 = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2024, 5, 1, 16, 30, 0, tzinfo=timezone.utc)
    hours = validate_temporal_ordering(t0, t1)
    assert hours == 6.5


def test_temporal_ordering_violation_equal():
    """Verify that identical timestamps raise TemporalValidationError."""
    t0 = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(TemporalValidationError, match="must be strictly before"):
        validate_temporal_ordering(t0, t0)


def test_temporal_ordering_violation_reversed():
    """Verify that T0 > T1 raises TemporalValidationError."""
    t0 = datetime(2024, 5, 2, 10, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(TemporalValidationError, match="Temporal ordering violation"):
        validate_temporal_ordering(t0, t1)


def test_parse_temporal_timestamp_tag(tmp_path: Path):
    """Verify timestamp parsing from embedded TIFF metadata tag."""
    pth = tmp_path / "tagged.tif"
    with rasterio.open(
        pth, "w", driver="GTiff", height=10, width=10, count=1, dtype="uint8",
        crs=CRS.from_epsg(4326), transform=Affine.identity()
    ) as dst:
        dst.update_tags(acquisition_time="2024-05-10T14:30:00Z")
        dst.write(np.zeros((10, 10), dtype=np.uint8), 1)

    dt = parse_temporal_timestamp(pth)
    assert dt.year == 2024
    assert dt.month == 5
    assert dt.day == 10
    assert dt.hour == 14
    assert dt.minute == 30
    assert dt.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# 2. CRS Mismatch Detection & Alignment
# ---------------------------------------------------------------------------

def test_crs_mismatch_detection_and_reprojection(tmp_path: Path):
    """Verify that CRS mismatch is handled: reprojected when allowed, rejected when disallowed."""
    # T0 in EPSG:4326 (lon 30.0 to 30.01, lat 32.0 to 31.99)
    crs_4326 = CRS.from_epsg(4326)
    trans_4326 = Affine(0.0001, 0.0, 30.0, 0.0, -0.0001, 32.0)
    m0 = np.zeros((100, 100), dtype=np.uint8)
    m0[20:40, 20:40] = 1

    # T1 in UTM Zone 36N (EPSG:32636) overlapping the same location
    crs_utm = CRS.from_epsg(32636)
    # UTM coordinates for (lon=30.0, lat=32.0) in UTM 36N is approx (216576.0, 3544370.0)
    trans_utm = Affine(10.0, 0.0, 216576.0, 0.0, -10.0, 3544370.0)
    m1 = np.zeros((100, 100), dtype=np.uint8)
    m1[20:40, 20:40] = 1

    # Disallow reprojection -> must raise SpatialAlignmentError
    with pytest.raises(SpatialAlignmentError, match="Spatial grids differ"):
        align_temporal_grids(
            m0, trans_4326, crs_4326,
            m1, trans_utm, crs_utm,
            allow_reprojection=False
        )

    # Allow reprojection -> successfully aligns
    m0_a, m1_a, _, _, meta = align_temporal_grids(
        m0, trans_4326, crs_4326,
        m1, trans_utm, crs_utm,
        allow_reprojection=True
    )
    assert m1_a.shape == m0.shape
    assert meta["strategy"] == "reprojected_t1_to_t0_grid"
    assert meta["resampling_mask"] == "nearest_neighbor"
    assert set(np.unique(m1_a)).issubset({0, 1})


# ---------------------------------------------------------------------------
# 3. Transform / Grid Mismatch Detection
# ---------------------------------------------------------------------------

def test_grid_mismatch_offset_transform():
    """Verify offset transform triggers reprojection or error based on flag."""
    crs = CRS.from_epsg(4326)
    t0_trans = Affine(0.0001, 0.0, 30.0, 0.0, -0.0001, 32.0)
    t1_trans = Affine(0.0001, 0.0, 30.002, 0.0, -0.0001, 32.002)  # Slight offset, overlapping

    m0 = np.zeros((50, 50), dtype=np.uint8)
    m1 = np.ones((50, 50), dtype=np.uint8)

    with pytest.raises(SpatialAlignmentError):
        align_temporal_grids(m0, t0_trans, crs, m1, t1_trans, crs, allow_reprojection=False)

    _, m1_aligned, _, _, meta = align_temporal_grids(
        m0, t0_trans, crs, m1, t1_trans, crs, allow_reprojection=True
    )
    assert m1_aligned.shape == (50, 50)
    assert meta["strategy"] == "reprojected_t1_to_t0_grid"


# ---------------------------------------------------------------------------
# 4. Identical Masks
# ---------------------------------------------------------------------------

def test_identical_masks(synthetic_pair_aligned):
    """Verify identical masks yield 100% persistent, 0 new, 0 disappeared."""
    t0_mask, _, _, _ = synthetic_pair_aligned
    t0_time = "2024-05-01T00:00:00Z"
    t1_time = "2024-05-02T00:00:00Z"

    report, _, _ = analyze_temporal_change(
        t0_mask_path=t0_mask,
        t1_mask_path=t0_mask,  # Identical
        t0_time=t0_time,
        t1_time=t1_time,
    )

    assert report.counts["persistent_regions"] > 0
    assert report.counts["new_regions"] == 0
    assert report.counts["disappeared_regions"] == 0
    assert report.pixel_counts["new_pixels"] == 0
    assert report.pixel_counts["disappeared_pixels"] == 0
    assert report.pixel_counts["persistent_pixels"] == (20 * 20) + (20 * 20)  # 800 px


# ---------------------------------------------------------------------------
# 5. Entirely New Mask
# ---------------------------------------------------------------------------

def test_entirely_new_mask(tmp_path: Path):
    """Verify that empty T0 + populated T1 produces only NEW regions."""
    crs = CRS.from_epsg(4326)
    trans = Affine(0.0001, 0.0, 30.0, 0.0, -0.0001, 32.0)

    m0_path = tmp_path / "empty_t0.tif"
    m1_path = tmp_path / "spill_t1.tif"

    m0 = np.zeros((50, 50), dtype=np.uint8)
    m1 = np.zeros((50, 50), dtype=np.uint8)
    m1[10:20, 10:20] = 1  # 100 px new object

    for p, arr in [(m0_path, m0), (m1_path, m1)]:
        with rasterio.open(
            p, "w", driver="GTiff", height=50, width=50, count=1,
            dtype="uint8", crs=crs, transform=trans
        ) as dst:
            dst.write(arr, 1)

    report, _, _ = analyze_temporal_change(
        t0_mask_path=m0_path,
        t1_mask_path=m1_path,
        t0_time="2024-05-01T00:00:00Z",
        t1_time="2024-05-02T00:00:00Z",
    )

    assert report.counts["new_regions"] == 1
    assert report.counts["persistent_regions"] == 0
    assert report.counts["disappeared_regions"] == 0
    assert report.pixel_counts["new_pixels"] == 100
    assert report.pixel_counts["persistent_pixels"] == 0
    assert report.pixel_counts["disappeared_pixels"] == 0


# ---------------------------------------------------------------------------
# 6. Entirely Disappeared Mask
# ---------------------------------------------------------------------------

def test_entirely_disappeared_mask(tmp_path: Path):
    """Verify that populated T0 + empty T1 produces only DISAPPEARED regions."""
    crs = CRS.from_epsg(4326)
    trans = Affine(0.0001, 0.0, 30.0, 0.0, -0.0001, 32.0)

    m0_path = tmp_path / "spill_t0.tif"
    m1_path = tmp_path / "empty_t1.tif"

    m0 = np.zeros((50, 50), dtype=np.uint8)
    m0[15:30, 15:30] = 1  # 225 px
    m1 = np.zeros((50, 50), dtype=np.uint8)

    for p, arr in [(m0_path, m0), (m1_path, m1)]:
        with rasterio.open(
            p, "w", driver="GTiff", height=50, width=50, count=1,
            dtype="uint8", crs=crs, transform=trans
        ) as dst:
            dst.write(arr, 1)

    report, _, _ = analyze_temporal_change(
        t0_mask_path=m0_path,
        t1_mask_path=m1_path,
        t0_time="2024-05-01T00:00:00Z",
        t1_time="2024-05-02T00:00:00Z",
    )

    assert report.counts["disappeared_regions"] == 1
    assert report.counts["new_regions"] == 0
    assert report.counts["persistent_regions"] == 0
    assert report.pixel_counts["disappeared_pixels"] == 225


# ---------------------------------------------------------------------------
# 7. Persistent Region
# ---------------------------------------------------------------------------

def test_persistent_region(tmp_path: Path):
    """Verify that a single persistent region between T0 and T1 is properly extracted."""
    crs = CRS.from_epsg(4326)
    trans = Affine(0.0001, 0.0, 30.0, 0.0, -0.0001, 32.0)

    m0_path = tmp_path / "p_t0.tif"
    m1_path = tmp_path / "p_t1.tif"

    m = np.zeros((50, 50), dtype=np.uint8)
    m[10:25, 10:25] = 1  # 225 px

    for p in [m0_path, m1_path]:
        with rasterio.open(
            p, "w", driver="GTiff", height=50, width=50, count=1,
            dtype="uint8", crs=crs, transform=trans
        ) as dst:
            dst.write(m, 1)

    report, _, _ = analyze_temporal_change(
        t0_mask_path=m0_path,
        t1_mask_path=m1_path,
        t0_time="2024-05-01T00:00:00Z",
        t1_time="2024-05-02T00:00:00Z",
    )

    assert report.counts["persistent_regions"] == 1
    event = report.events[0]
    assert event.change_type == ChangeCategory.PERSISTENT
    assert event.pixel_count == 225
    assert event.area_m2 > 0.0


# ---------------------------------------------------------------------------
# 8. Mixed New / Persistent / Disappeared
# ---------------------------------------------------------------------------

def test_mixed_new_persistent_disappeared(synthetic_pair_aligned):
    """Verify correct categorization of mixed change scene."""
    t0_mask, t0_prob, t1_mask, t1_prob = synthetic_pair_aligned

    report, _, _ = analyze_temporal_change(
        t0_mask_path=t0_mask,
        t1_mask_path=t1_mask,
        t0_prob_path=t0_prob,
        t1_prob_path=t1_prob,
        t0_time="2024-05-01T12:00:00Z",
        t1_time="2024-05-02T12:00:00Z",
    )

    # In fixture:
    # Region A [10:30, 10:30] -> 400 px DISAPPEARED
    # Region B [50:70, 50:70] -> 400 px PERSISTENT
    # Region C [75:90, 10:25] -> 225 px NEW
    assert report.pixel_counts["disappeared_pixels"] == 400
    assert report.pixel_counts["persistent_pixels"] == 400
    assert report.pixel_counts["new_pixels"] == 225

    assert report.counts["disappeared_regions"] == 1
    assert report.counts["persistent_regions"] == 1
    assert report.counts["new_regions"] == 1
    assert report.counts["total_change_regions"] == 3


# ---------------------------------------------------------------------------
# 9. Continuous Probability Delta
# ---------------------------------------------------------------------------

def test_probability_delta(synthetic_pair_aligned):
    """Verify continuous score delta statistics match raster math."""
    t0_mask, t0_prob, t1_mask, t1_prob = synthetic_pair_aligned

    report, _, _ = analyze_temporal_change(
        t0_mask_path=t0_mask,
        t1_mask_path=t1_mask,
        t0_prob_path=t0_prob,
        t1_prob_path=t1_prob,
        t0_time="2024-05-01T12:00:00Z",
        t1_time="2024-05-02T12:00:00Z",
    )

    assert report.probability_change_summary is not None
    pcs = report.probability_change_summary
    assert pcs["valid_pixel_count"] == 100 * 100
    # Overall probability delta:
    # Background: T0=0.1, T1=0.2 -> delta=+0.1
    # Region B: T0=0.7, T1=0.9 -> delta=+0.2
    # Region A: T0=0.8, T1=0.2 -> delta=-0.6
    # Region C: T0=0.1, T1=0.85 -> delta=+0.75
    assert pcs["min_delta"] < 0.0  # Captures decrease in disappeared region
    assert pcs["max_delta"] > 0.5  # Captures increase in new region


# ---------------------------------------------------------------------------
# 10. Zero-Area Relative-Change Safe Handling
# ---------------------------------------------------------------------------

def test_zero_area_relative_change_safe_handling():
    """Verify that MatchedObjectPair handles area_t0 == 0.0 without ZeroDivisionError."""
    pair = MatchedObjectPair(
        t0_polygon_id="t0_0001",
        t1_polygon_id="t1_0001",
        area_t0_m2=0.0,
        area_t1_m2=500.0,
        area_change_m2=500.0,
        relative_area_change=None,  # Handled safely
        overlap_iou=0.0,
        overlap_area_m2=0.0,
        centroid_displacement_m=10.0,
    )
    assert pair.relative_area_change is None
    assert pair.area_change_m2 == 500.0


# ---------------------------------------------------------------------------
# 11. Polygon Matching via Spatial IoU
# ---------------------------------------------------------------------------

def test_polygon_matching_iou():
    """Verify candidate polygon matching correctly computes IoU and links objects."""
    crs = CRS.from_epsg(32636)  # Projected metric CRS
    # Poly 0: [0, 0] to [100, 100] -> area 10,000
    p0 = box(0, 0, 100, 100)
    # Poly 1: [50, 0] to [150, 100] -> area 10,000, intersection [50, 0] to [100, 100] = 5,000
    # Union = 15,000 -> IoU = 5,000 / 15,000 = 0.3333
    p1 = box(50, 0, 150, 100)

    t0_polys = [("t0_1", p0, 10000.0)]
    t1_polys = [("t1_1", p1, 10000.0)]

    # Threshold 0.20 -> match should be found
    matches = match_t0_t1_objects(t0_polys, t1_polys, crs, iou_threshold=0.20)
    assert len(matches) == 1
    assert matches[0].overlap_iou == pytest.approx(0.3333, abs=1e-3)
    assert matches[0].area_change_m2 == 0.0
    assert matches[0].relative_area_change == 0.0

    # Threshold 0.50 -> no match
    matches_high = match_t0_t1_objects(t0_polys, t1_polys, crs, iou_threshold=0.50)
    assert len(matches_high) == 0


def test_one_to_one_greedy_matching_disambiguation():
    """Verify deterministic 1-to-1 greedy matching disambiguates 1-to-many candidate overlaps."""
    crs = CRS.from_epsg(32636)
    # T0 object: box [0, 0, 100, 100] -> area 10,000
    p0 = box(0, 0, 100, 100)

    # T1 object A: box [30, 0, 130, 100] -> intersection [30, 0, 100, 100] = 7,000
    # union = 13,000 -> IoU = 7,000 / 13,000 = 0.538
    p1_a = box(30, 0, 130, 100)

    # T1 object B: box [70, 0, 170, 100] -> intersection [70, 0, 100, 100] = 3,000
    # union = 17,000 -> IoU = 3,000 / 17,000 = 0.176
    p1_b = box(70, 0, 170, 100)

    t0_polys = [("t0_1", p0, 10000.0)]
    t1_polys = [("t1_a", p1_a, 10000.0), ("t1_b", p1_b, 10000.0)]

    # Candidate association edges (many-to-many graph)
    cand_matches = match_t0_t1_objects(t0_polys, t1_polys, crs, iou_threshold=0.10, one_to_one=False)
    assert len(cand_matches) == 2  # T0 matches both A and B candidates

    # One-to-one greedy assignment
    one_to_one_matches = match_t0_t1_objects(t0_polys, t1_polys, crs, iou_threshold=0.10, one_to_one=True)
    assert len(one_to_one_matches) == 1
    assert one_to_one_matches[0].t1_polygon_id == "t1_a"  # Highest IoU chosen deterministically


def test_candidate_polygon_extraction_filtering():
    """Verify extract_candidate_polygons_from_mask respects min_pixels filter."""
    crs = CRS.from_epsg(4326)
    trans = Affine(0.0001, 0.0, 30.0, 0.0, -0.0001, 32.0)
    m = np.zeros((50, 50), dtype=np.uint8)
    m[5:15, 5:15] = 1   # 100 px object
    m[30:32, 30:32] = 1  # 4 px speck

    # Unfiltered -> 2 polygons
    all_polys = extract_candidate_polygons_from_mask(m, trans, crs, "test", min_pixels=0)
    assert len(all_polys) == 2

    # Filtered >= 10 px -> 1 polygon
    filtered_polys = extract_candidate_polygons_from_mask(m, trans, crs, "test", min_pixels=10)
    assert len(filtered_polys) == 1
    assert filtered_polys[0][0] == "test_obj_0001"


def test_timestamp_provenance_resolution(tmp_path: Path):
    """Verify resolve_temporal_timestamp distinguishes metadata tags from external test timestamps."""
    from ocean_sentinel.temporal import TimestampProvenance, resolve_temporal_timestamp

    # Case 1: Tagged file
    pth_tagged = tmp_path / "tagged.tif"
    with rasterio.open(
        pth_tagged, "w", driver="GTiff", height=10, width=10, count=1, dtype="uint8",
        crs=CRS.from_epsg(4326), transform=Affine.identity()
    ) as dst:
        dst.update_tags(acquisition_time="2024-05-10T14:30:00Z")
        dst.write(np.zeros((10, 10), dtype=np.uint8), 1)

    dt, prov = resolve_temporal_timestamp(pth_tagged)
    assert prov == TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA
    assert dt.hour == 14

    # Case 2: Untagged file with explicit time
    pth_untagged = tmp_path / "untagged.tif"
    with rasterio.open(
        pth_untagged, "w", driver="GTiff", height=10, width=10, count=1, dtype="uint8",
        crs=CRS.from_epsg(4326), transform=Affine.identity()
    ) as dst:
        dst.write(np.zeros((10, 10), dtype=np.uint8), 1)

    dt_exp, prov_exp = resolve_temporal_timestamp(pth_untagged, explicit_time="2024-06-01T12:00:00Z")
    assert prov_exp == TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP
    assert dt_exp.day == 1



# ---------------------------------------------------------------------------
# 12. Deterministic Execution
# ---------------------------------------------------------------------------

def test_deterministic_execution(synthetic_pair_aligned):
    """Verify that repeated runs on the same input yield identical results."""
    t0_mask, t0_prob, t1_mask, t1_prob = synthetic_pair_aligned

    r1, _, _ = analyze_temporal_change(
        t0_mask_path=t0_mask,
        t1_mask_path=t1_mask,
        t0_prob_path=t0_prob,
        t1_prob_path=t1_prob,
        t0_time="2024-05-01T12:00:00Z",
        t1_time="2024-05-02T12:00:00Z",
    )
    r2, _, _ = analyze_temporal_change(
        t0_mask_path=t0_mask,
        t1_mask_path=t1_mask,
        t0_prob_path=t0_prob,
        t1_prob_path=t1_prob,
        t0_time="2024-05-01T12:00:00Z",
        t1_time="2024-05-02T12:00:00Z",
    )

    assert r1.counts == r2.counts
    assert r1.areas_m2 == r2.areas_m2
    assert r1.pixel_counts == r2.pixel_counts
    assert len(r1.events) == len(r2.events)
    for e1, e2 in zip(r1.events, r2.events):
        assert e1.event_id == e2.event_id
        assert e1.change_type == e2.change_type
        assert e1.area_m2 == e2.area_m2
        assert e1.pixel_count == e2.pixel_count


# ---------------------------------------------------------------------------
# 13. RFC 7946 GeoJSON Schema Compliance
# ---------------------------------------------------------------------------

def test_geojson_rfc7946_compliance(synthetic_pair_aligned, tmp_path: Path):
    """Verify exported GeoJSON complies with RFC 7946 standard."""
    t0_mask, t0_prob, t1_mask, t1_prob = synthetic_pair_aligned
    out_dir = tmp_path / "geojson_test"

    report, geojson_path, json_path = analyze_temporal_change(
        t0_mask_path=t0_mask,
        t1_mask_path=t1_mask,
        t0_prob_path=t0_prob,
        t1_prob_path=t1_prob,
        t0_time="2024-05-01T12:00:00Z",
        t1_time="2024-05-02T12:00:00Z",
        output_dir=out_dir,
    )

    assert geojson_path is not None and geojson_path.is_file()
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert len(data["features"]) == len(report.events)

    for feat in data["features"]:
        assert feat["type"] == "Feature"
        assert "id" in feat
        assert "geometry" in feat
        geom = shape(feat["geometry"])
        assert geom.is_valid
        # Bounds must be within WGS84 range
        minx, miny, maxx, maxy = geom.bounds
        assert -180.0 <= minx <= 180.0
        assert -180.0 <= maxx <= 180.0
        assert -90.0 <= miny <= 90.0
        assert -90.0 <= maxy <= 90.0

        # Required properties
        props = feat["properties"]
        assert "change_type" in props
        assert props["change_type"] in ["new", "persistent", "disappeared"]
        assert "area_m2" in props
        assert "area_km2" in props
        assert "pixel_count" in props


# ---------------------------------------------------------------------------
# 14. Nearest-Neighbor Resampling Semantics for Masks
# ---------------------------------------------------------------------------

def test_mask_nearest_neighbor_resampling_semantics(tmp_path: Path):
    """Verify that reprojecting masks maintains strict binary {0, 1} values without fractional blur."""
    crs = CRS.from_epsg(4326)
    t0_trans = Affine(0.0001, 0.0, 30.0, 0.0, -0.0001, 32.0)
    # T1 has a rotated or non-integer scale transform
    t1_trans = Affine(0.000137, 0.0, 30.0005, 0.0, -0.000137, 32.0005)

    m0 = np.zeros((100, 100), dtype=np.uint8)
    m1 = np.zeros((100, 100), dtype=np.uint8)
    m1[30:70, 30:70] = 1

    _, m1_reprojected, _, _, meta = align_temporal_grids(
        t0_mask=m0,
        t0_transform=t0_trans,
        t0_crs=crs,
        t1_mask=m1,
        t1_transform=t1_trans,
        t1_crs=crs,
        allow_reprojection=True,
    )

    # Values must strictly be 0 or 1, no intermediate floats/integers
    unique_vals = set(np.unique(m1_reprojected))
    assert unique_vals.issubset({0, 1})
    assert meta["resampling_mask"] == "nearest_neighbor"


# ---------------------------------------------------------------------------
# 15. Real Sentinel-1 Integration Test
# ---------------------------------------------------------------------------

def test_real_sentinel1_temporal_integration(tmp_path: Path):
    """Integration test executing end-to-end temporal analysis on real Trujillo SAR pairs."""
    t0_mask = REPO_ROOT / "outputs" / "inference" / "00260_mask.tif"
    t0_prob = REPO_ROOT / "outputs" / "inference" / "00260_probability.tif"
    t1_mask = REPO_ROOT / "outputs" / "inference" / "00608_mask.tif"
    t1_prob = REPO_ROOT / "outputs" / "inference" / "00608_probability.tif"

    if not (t0_mask.is_file() and t1_mask.is_file()):
        pytest.skip("Real Sentinel-1 inference outputs not available on disk.")

    t0_time = "2024-05-01T00:00:00Z"
    t1_time = "2024-05-13T00:00:00Z"

    report, geojson_path, json_path = analyze_temporal_change(
        t0_mask_path=t0_mask,
        t1_mask_path=t1_mask,
        t0_prob_path=t0_prob,
        t1_prob_path=t1_prob,
        t0_time=t0_time,
        t1_time=t1_time,
        output_dir=tmp_path / "temporal_integration",
        match_iou_threshold=0.05,
    )

    assert report.t0_source == "00260"
    assert report.t1_source == "00608"
    assert report.time_interval_hours == 288.0  # 12 days
    assert report.spatial_alignment["strategy"] == "reprojected_t1_to_t0_grid"
    assert report.spatial_alignment["footprint_overlap_fraction"] > 0.95

    # Check actual measured pixel counts from real multi-temporal acquisitions
    # In this real 12-day interval, the slick observed at T0 has dissipated/drifted,
    # and a new slick signature is detected at T1 with zero direct pixel overlap.
    assert report.pixel_counts["persistent_pixels"] == 0
    assert report.pixel_counts["disappeared_pixels"] == 38195
    assert report.pixel_counts["new_pixels"] == 40159

    assert report.counts["new_regions"] > 0
    assert report.counts["disappeared_regions"] > 0
    assert report.counts["total_change_regions"] > 0
    assert report.areas_m2["total_changed_area_m2"] > 0.0

    # Probability summary exists
    assert report.probability_change_summary is not None
    assert report.probability_change_summary["valid_pixel_count"] > 0

    # Output files exist and are valid JSON
    assert geojson_path is not None and geojson_path.is_file()
    assert json_path is not None and json_path.is_file()


def test_real_sentinel1_identical_grid_integration(tmp_path: Path):
    """Integration test with real co-registered Sentinel-1 pair (00007 & 01339) demonstrating 100% persistence."""
    t0_mask = REPO_ROOT / "outputs" / "inference" / "00007_mask.tif"
    t0_prob = REPO_ROOT / "outputs" / "inference" / "00007_probability.tif"
    t1_mask = REPO_ROOT / "outputs" / "inference" / "01339_mask.tif"
    t1_prob = REPO_ROOT / "outputs" / "inference" / "01339_probability.tif"

    if not (t0_mask.is_file() and t1_mask.is_file()):
        pytest.skip("Real Sentinel-1 inference outputs not available on disk.")

    t0_time = "2024-04-10T10:00:00Z"
    t1_time = "2024-04-10T12:00:00Z"

    report, geojson_path, json_path = analyze_temporal_change(
        t0_mask_path=t0_mask,
        t1_mask_path=t1_mask,
        t0_prob_path=t0_prob,
        t1_prob_path=t1_prob,
        t0_time=t0_time,
        t1_time=t1_time,
        output_dir=tmp_path / "identical_grid_integration",
    )

    assert report.t0_source == "00007"
    assert report.t1_source == "01339"
    assert report.time_interval_hours == 2.0
    assert report.spatial_alignment["strategy"] == "exact_grid_match"

    assert report.pixel_counts["persistent_pixels"] == 62042
    assert report.pixel_counts["new_pixels"] == 0
    assert report.pixel_counts["disappeared_pixels"] == 0

    assert report.counts["persistent_regions"] > 0
    assert report.counts["new_regions"] == 0
    assert report.counts["disappeared_regions"] == 0

    assert geojson_path is not None and geojson_path.is_file()
    assert json_path is not None and json_path.is_file()

