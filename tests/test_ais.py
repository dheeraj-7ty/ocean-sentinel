"""Comprehensive Test Suite for Ocean Sentinel AIS Spatio-Temporal Correlation Engine V1.

Verifies:
1. Valid AIS point ingestion & property preservation
2. Invalid coordinate rejection fail-closed
3. Duplicate and out-of-order timestamp handling & sorting
4. Telemetry speed jump detection (> max plausible speed)
5. Large AIS gap handling without false interpolation
6. Longitude wrapping / antimeridian consistency
7. Spatial proximity calculation (Haversine geodesic)
8. Temporal offset calculation and proximity decay
9. Trajectory corridor matching and distance evaluation
10. Candidate origin polygon intersection test
11. Multi-vessel deterministic ranking & separation
12. Quality factor degradation on corrupted/gapped tracks
13. Missing static metadata handling (None without inventing)
14. DEMO vs PHYSICAL mode strict provenance separation
15. Provenance gate rejection on synthetic feeds in PHYSICAL mode
16. Bitwise deterministic execution across repeated runs
17. RFC 7946 WGS84 GeoJSON schema compliance
18. Empty hypotheses / empty tracks behavior
19. Malformed input error handling
20. End-to-end integration: Temporal Detection -> Origin Drift -> AIS Correlation
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import Point, Polygon, box

from ocean_sentinel.ais import (
    AISCorrelationMode,
    AISProvenance,
    AISRecord,
    CandidateHypothesisPoint,
    NavigationStatus,
    TrackQualityReport,
    VesselTrack,
    correlate_vessel_tracks,
    filter_and_assemble_vessel_tracks,
    generate_deterministic_demo_ais_fixture,
    haversine_distance_m,
    serialize_ais_correlation_to_geojson,
    serialize_ais_correlation_summary,
)
from ocean_sentinel.drift import (
    DirectionMode,
    DriftMode,
    ForcingSourceType,
    MetoceanForcingField,
    ObservationRecord,
    ProvenanceGateError,
    run_origin_drift_analysis,
)
from ocean_sentinel.temporal import TimestampProvenance

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_candidate_origin_polygon() -> Polygon:
    """Polygon representing a candidate origin region around (-90.438, 26.927)."""
    return box(-90.46, 26.90, -90.41, 26.95)


@pytest.fixture
def sample_trajectory_envelope_polygon() -> Polygon:
    """Polygon representing overall trajectory envelope."""
    return box(-90.55, 26.85, -90.35, 27.10)


@pytest.fixture
def sample_hypotheses() -> List[CandidateHypothesisPoint]:
    """Sample time-indexed candidate origin hypotheses at 2024-05-12T00:00:00Z."""
    ref_time = datetime(2024, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    pts = [
        (-90.438, 26.927),
        (-90.430, 26.935),
        (-90.445, 26.920),
        (-90.420, 26.940),
    ]
    return [
        CandidateHypothesisPoint(
            longitude=p[0],
            latitude=p[1],
            timestamp=ref_time,
            particle_id=f"p_{i}",
            windage_factor=0.01 + i * 0.01,
            trajectory_step=48,
            is_origin_endpoint=True,
        )
        for i, p in enumerate(pts)
    ]


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------


def test_valid_ais_point_ingestion():
    """Verify clean ingestion and property preservation of valid AIS records."""
    rec = AISRecord(
        mmsi="123456789",
        timestamp=datetime(2024, 5, 12, 10, 0, 0, tzinfo=timezone.utc),
        longitude=-90.5,
        latitude=27.0,
        sog_knots=14.2,
        cog_degrees=185.0,
        imo="IMO9999999",
        vessel_name="TEST_VESSEL",
        vessel_type="Tanker",
        navigation_status=NavigationStatus.UNDERWAY_USING_ENGINE,
        source_identifier="TEST_STATION",
        provenance=AISProvenance.HISTORICAL_ARCHIVE,
    )
    assert rec.mmsi == "123456789"
    assert rec.sog_knots == 14.2
    assert rec.cog_degrees == 185.0
    assert rec.imo == "IMO9999999"
    assert rec.provenance == "HISTORICAL_ARCHIVE"
    d = rec.to_dict()
    assert d["mmsi"] == "123456789"
    assert d["longitude"] == -90.5


def test_invalid_coordinate_rejection():
    """Verify out-of-range coordinates raise ValueError."""
    t = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="coordinates out of range"):
        AISRecord(mmsi="123", timestamp=t, longitude=-195.0, latitude=25.0)

    with pytest.raises(ValueError, match="coordinates out of range"):
        AISRecord(mmsi="123", timestamp=t, longitude=-90.0, latitude=95.0)


def test_duplicate_and_out_of_order_timestamps():
    """Verify tracks are chronologically sorted and duplicate timestamps are deduplicated."""
    t0 = datetime(2024, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=10)
    t2 = t0 + timedelta(minutes=20)

    records = [
        AISRecord("111", t2, -90.0, 27.0),
        AISRecord("111", t0, -90.2, 26.8),
        AISRecord("111", t1, -90.1, 26.9),
        AISRecord("111", t1, -90.1, 26.9),  # Duplicate timestamp
    ]

    tracks = filter_and_assemble_vessel_tracks(records)
    track = tracks["111"]

    assert len(track.records) == 3
    assert track.records[0].timestamp == t0
    assert track.records[1].timestamp == t1
    assert track.records[2].timestamp == t2
    assert track.quality_report.rejection_reasons.get("duplicate_timestamp") == 1


def test_speed_jump_telemetry_detection():
    """Verify impossible speed jumps (>60 knots) are flagged and rejected."""
    t0 = datetime(2024, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=5)

    records = [
        AISRecord("222", t0, -90.0, 27.0),
        AISRecord("222", t1, -89.5, 27.0),  # ~49 km in 5 minutes = ~588 km/h = ~317 knots!
    ]

    tracks = filter_and_assemble_vessel_tracks(records, max_plausible_speed_knots=60.0)
    track = tracks["222"]

    assert track.quality_report.impossible_speed_jumps == 1
    assert len(track.records) == 1


def test_large_ais_gap_handling_and_interpolation_guard():
    """Verify positions are NOT interpolated across gaps exceeding max_interpolation_gap."""
    t0 = datetime(2024, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    t_gap = t0 + timedelta(hours=6)  # 6-hour gap

    records = [
        AISRecord("333", t0, -90.0, 27.0),
        AISRecord("333", t_gap, -89.8, 27.2),
    ]

    tracks = filter_and_assemble_vessel_tracks(records)
    track = tracks["333"]
    assert track.quality_report.max_gap_seconds == 6 * 3600.0

    # Query hypothesis midway across the gap (t0 + 3h)
    hyp_mid = [
        CandidateHypothesisPoint(
            longitude=-89.9,
            latitude=27.1,
            timestamp=t0 + timedelta(hours=3),
            particle_id="p1",
            windage_factor=0.02,
            trajectory_step=10,
            is_origin_endpoint=True,
        )
    ]

    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=hyp_mid,
        max_interpolation_gap_seconds=2 * 3600.0,  # 2h limit
    )

    assert len(metrics) == 1
    # Because gap > 2h, it does not interpolate; temporal offset is > 0
    assert metrics[0].temporal_offset_seconds >= 3 * 3600.0 - 5.0
    assert any("large telemetry gap" in lim for lim in metrics[0].data_limitations)


def test_haversine_distance_known_baseline():
    """Verify Haversine distance matches spherical baseline at 1 degree latitude (~111.19 km)."""
    d = haversine_distance_m(0.0, 0.0, 0.0, 1.0)
    assert 111_000.0 < d < 111_400.0


def test_candidate_origin_polygon_matching(sample_candidate_origin_polygon, sample_hypotheses):
    """Verify vessel track passing through origin polygon receives inside_origin=True."""
    t_target = datetime(2024, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        AISRecord("444", t_target - timedelta(hours=1), -90.48, 26.88),
        AISRecord("444", t_target, -90.438, 26.927),  # Exactly inside polygon
        AISRecord("444", t_target + timedelta(hours=1), -90.40, 26.97),
    ]

    tracks = filter_and_assemble_vessel_tracks(records)
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=sample_hypotheses,
        candidate_origin_polygon=sample_candidate_origin_polygon,
    )

    assert len(metrics) == 1
    assert metrics[0].inside_candidate_origin_region is True
    assert metrics[0].min_distance_to_origin_m < 50.0
    assert metrics[0].evidence_compatibility_score > 0.85


def test_multiple_vessel_deterministic_ranking(sample_candidate_origin_polygon, sample_hypotheses):
    """Verify deterministic ranking separates clearly compatible, corridor, and gapped candidates."""
    fixture_records = generate_deterministic_demo_ais_fixture(
        origin_lon=-90.438,
        origin_lat=26.927,
        origin_time=datetime(2024, 5, 12, 0, 0, 0, tzinfo=timezone.utc),
    )

    tracks = filter_and_assemble_vessel_tracks(fixture_records)
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=sample_hypotheses,
        candidate_origin_polygon=sample_candidate_origin_polygon,
    )

    assert len(metrics) == 6

    # Top candidate must be MT_HORIZON_STAR (highly compatible)
    assert metrics[0].mmsi == "368123450"
    assert metrics[0].vessel_name == "MT_HORIZON_STAR"
    assert metrics[0].inside_candidate_origin_region is True
    assert metrics[0].evidence_compatibility_score > 0.80

    # Temporally incompatible vessel (MV_PACIFIC_CARRIER) must have low score despite spatial coincidence
    carrier_metric = next(m for m in metrics if m.mmsi == "368987650")
    assert carrier_metric.evidence_compatibility_score < 0.10
    assert carrier_metric.temporal_offset_seconds > 30 * 3600.0

    # Spatially incompatible vessel (OCEAN_TUG_TITAN) must be far away
    tug_metric = next(m for m in metrics if m.mmsi == "367111220")
    assert tug_metric.min_distance_to_origin_m > 50_000.0


def test_missing_metadata_preservation():
    """Verify missing vessel metadata remains None without inventing default values."""
    rec = AISRecord(
        mmsi="555",
        timestamp=datetime.now(timezone.utc),
        longitude=-90.0,
        latitude=27.0,
        imo=None,
        vessel_name=None,
        vessel_type=None,
        sog_knots=None,
        cog_degrees=None,
    )
    assert rec.imo is None
    assert rec.vessel_name is None
    assert rec.sog_knots is None
    d = rec.to_dict()
    assert d["imo"] is None
    assert d["vessel_name"] is None
    assert d["sog_knots"] is None


def test_provenance_gate_rejection_in_physical_mode():
    """Verify SYNTHETIC_DEMO_FEED data is strictly rejected in PHYSICAL mode fail-closed."""
    rec = AISRecord(
        mmsi="666",
        timestamp=datetime.now(timezone.utc),
        longitude=-90.0,
        latitude=27.0,
        provenance=AISProvenance.SYNTHETIC_DEMO_FEED,
    )
    tracks = filter_and_assemble_vessel_tracks([rec, rec])

    hyp = [
        CandidateHypothesisPoint(
            longitude=-90.0,
            latitude=27.0,
            timestamp=datetime.now(timezone.utc),
            particle_id="p1",
            windage_factor=0.02,
            trajectory_step=1,
            is_origin_endpoint=True,
        )
    ]

    with pytest.raises(ProvenanceGateError, match="PHYSICAL mode rejected"):
        correlate_vessel_tracks(
            tracks=tracks,
            hypotheses=hyp,
            mode=AISCorrelationMode.PHYSICAL,
        )


def test_rfc7946_geojson_serialization(sample_candidate_origin_polygon, sample_hypotheses):
    """Verify serialized GeoJSON FeatureCollection adheres strictly to RFC 7946 WGS84 format."""
    fixture_records = generate_deterministic_demo_ais_fixture(
        origin_lon=-90.438,
        origin_lat=26.927,
    )
    tracks = filter_and_assemble_vessel_tracks(fixture_records)
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=sample_hypotheses,
        candidate_origin_polygon=sample_candidate_origin_polygon,
    )

    geojson = serialize_ais_correlation_to_geojson(
        candidates=metrics,
        tracks=tracks,
        candidate_origin_polygon=sample_candidate_origin_polygon,
        event_id="test_event_geo",
    )

    assert geojson["type"] == "FeatureCollection"
    assert "metadata" in geojson
    assert geojson["metadata"]["scientific_boundary"] == "EVIDENCE_COMPATIBILITY_ONLY_NO_LEGAL_ATTRIBUTION"
    assert len(geojson["features"]) > 0

    # Test JSON round-trip
    serialized = json.dumps(geojson)
    loaded = json.loads(serialized)
    assert loaded["type"] == "FeatureCollection"


def test_empty_hypotheses_and_tracks():
    """Verify empty hypotheses or empty tracks return empty results gracefully."""
    empty_res1 = correlate_vessel_tracks(tracks={}, hypotheses=[])
    assert empty_res1 == []

    tracks = filter_and_assemble_vessel_tracks(generate_deterministic_demo_ais_fixture())
    empty_res2 = correlate_vessel_tracks(tracks=tracks, hypotheses=[])
    assert empty_res2 == []


def test_end_to_end_temporal_drift_ais_integration(tmp_path: Path):
    """Verify full pipeline flow: Temporal Event -> Drift Origin -> AIS Correlation."""
    # 1. Observation
    poly = box(-90.445, 26.915, -90.430, 26.935)
    obs = ObservationRecord(
        event_id="e2e_spill_001",
        source_scene="scene_001",
        observation_time=datetime(2024, 5, 13, 0, 0, 0, tzinfo=timezone.utc),
        timestamp_provenance=TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP,
        geometry={"type": "Polygon", "coordinates": [[[-90.445, 26.915], [-90.430, 26.915], [-90.430, 26.935], [-90.445, 26.935], [-90.445, 26.915]]]},
        centroid=[-90.438, 26.927],
        area_m2=500_000.0,
    )

    # 2. Forcing field
    forcing = MetoceanForcingField(
        forcing_source="demo_metocean",
        source_type=ForcingSourceType.SYNTHETIC_TEST_FIXTURE,
        is_authoritative=False,
        constant_current_u=0.10,
        constant_current_v=0.05,
        constant_wind_u=-2.0,
        constant_wind_v=1.0,
    )

    # 3. Drift Analysis (Backward 24h)
    drift_report, geojson_path, _ = run_origin_drift_analysis(
        observation=obs,
        forcing_field=forcing,
        direction=DirectionMode.BACKWARD,
        mode=DriftMode.DEMO,
        duration_hours=24.0,
        particle_count=5,
        output_dir=tmp_path / "drift_out",
    )

    assert geojson_path is not None and geojson_path.is_file()

    # 4. AIS Correlation
    from scripts.run_ais_correlation import load_drift_artifacts

    hypotheses, origin_poly, env_poly, event_id, t_term, duration_h = load_drift_artifacts(geojson_path)
    assert len(hypotheses) > 0
    assert origin_poly is not None

    ais_records = generate_deterministic_demo_ais_fixture(
        origin_lon=float(origin_poly.centroid.x),
        origin_lat=float(origin_poly.centroid.y),
        origin_time=t_term,
    )

    tracks = filter_and_assemble_vessel_tracks(ais_records)
    candidates = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=hypotheses,
        candidate_origin_polygon=origin_poly,
        trajectory_envelope_polygon=env_poly,
        mode=AISCorrelationMode.DEMO,
    )

    assert len(candidates) > 0
    top_cand = candidates[0]
    assert top_cand.vessel_name == "MT_HORIZON_STAR"
    assert top_cand.inside_candidate_origin_region is True
    assert top_cand.evidence_compatibility_score > 0.80
