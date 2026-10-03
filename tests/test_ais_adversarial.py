"""Adversarial and Edge-Case Test Suite for Ocean Sentinel AIS Correlation & Drift V1.

Mandatory Adversarial Tests (Release Gate Requirements):
1. Synthetic AIS marked authoritative manually (Anti-Bypass Protection)
2. Synthetic metocean marked authoritative manually (Anti-Bypass Protection)
3. Corrupt AIS record (coordinate validation / NaN / inf rejection)
4. One bad speed segment (degraded track retention without total vessel discarding)
5. Large AIS gap (flagged without false interpolation across gap)
6. Wrong timestamp (temporal offset decay & gating)
7. Future AIS timestamp (handled safely)
8. Out-of-window vessel (VesselCoverageStatus.OUTSIDE_WINDOW)
9. Trajectory-envelope-only intersection (does not falsely inflate particle score)
10. Candidate-origin-only intersection at wrong time (temporally gated)
11. Valid trajectory intersection at intermediate time (e.g. 6h back)
12. Multiple equally plausible candidates (deterministic ranking & separation)
13. No candidates (empty track collection handled safely)
14. Missing vessel metadata (None preserved without fabrication)
15. Antimeridian coordinates (wrapping handled deterministically)
16. High-latitude geometry (polar guard & numerical stability)
17. Empty drift hypothesis set (fails safely returning empty list)
18. Invalid GeoJSON (handled safely with clear error)
19. DEMO data passed to PHYSICAL mode (fails closed)
20. PHYSICAL mode with missing provenance (fails closed)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import numpy as np
import pytest
from shapely.geometry import Point, Polygon, box

from ocean_sentinel.ais import (
    AISCorrelationMode,
    AISProvenance,
    AISProviderAdapter,
    AISRecord,
    AISSourceRegistry,
    CandidateHypothesisPoint,
    CompatibilityScoreWeights,
    NavigationStatus,
    TrackQualityClass,
    VesselCoverageStatus,
    correlate_vessel_tracks,
    filter_and_assemble_vessel_tracks,
    generate_deterministic_demo_ais_fixture,
    haversine_distance_m,
    interpolate_geodesic_position,
    serialize_ais_correlation_to_geojson,
    serialize_ais_correlation_summary,
)
from ocean_sentinel.drift import (
    DirectionMode,
    DriftMode,
    ForcingSourceType,
    MetoceanForcingField,
    MetoceanProviderAdapter,
    MetoceanSourceRegistry,
    ObservationRecord,
    ProvenanceGateError,
    run_origin_drift_analysis,
)
from ocean_sentinel.temporal import TimestampProvenance

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def base_time() -> datetime:
    return datetime(2024, 5, 12, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_hypotheses_trajectory(base_time: datetime) -> List[CandidateHypothesisPoint]:
    """Create a backtracked trajectory over 12 hours from (lon=-90.0, lat=27.0)."""
    hyps: List[CandidateHypothesisPoint] = []
    # Slick at T_obs (t=0) is at (-90.0, 27.0)
    # Backtracked to (-90.6, 26.4) over 12 hours (12 steps of 1h)
    for step in range(13):
        t = base_time - timedelta(hours=step)
        lon = -90.0 - step * 0.05
        lat = 27.0 - step * 0.05
        hyps.append(
            CandidateHypothesisPoint(
                longitude=lon,
                latitude=lat,
                timestamp=t,
                particle_id="particle_main",
                windage_factor=0.03,
                trajectory_step=step,
                is_origin_endpoint=(step == 12),
            )
        )
    return hyps


# ---------------------------------------------------------------------------
# 1. Synthetic AIS marked authoritative manually (Anti-Bypass Protection)
# ---------------------------------------------------------------------------

def test_adv_01_synthetic_ais_marked_authoritative_manually(base_time: datetime):
    """Caller setting is_authoritative=True or operational provenance without accredited adapter must fail closed."""
    rec = AISRecord(
        mmsi="111222333",
        timestamp=base_time,
        longitude=-90.3,
        latitude=26.7,
        provenance=AISProvenance.VERIFIED_OPERATIONAL_FEED.value,
        adapter_id="unauthorized_spoofed_adapter",
        verification_token="fake_token",
    )
    tracks = filter_and_assemble_vessel_tracks([rec, rec])
    hyp = [
        CandidateHypothesisPoint(
            longitude=-90.3, latitude=26.7, timestamp=base_time,
            particle_id="p0", windage_factor=0.03, trajectory_step=0, is_origin_endpoint=True
        )
    ]

    with pytest.raises(ProvenanceGateError, match="PHYSICAL mode rejected"):
        correlate_vessel_tracks(tracks=tracks, hypotheses=hyp, mode=AISCorrelationMode.PHYSICAL)


# ---------------------------------------------------------------------------
# 2. Synthetic metocean marked authoritative manually (Anti-Bypass Protection)
# ---------------------------------------------------------------------------

def test_adv_02_synthetic_metocean_marked_authoritative_manually(base_time: datetime):
    """Caller setting is_authoritative=True on forcing without accredited registry adapter must fail closed."""
    forcing = MetoceanForcingField(
        forcing_source="HYCOM_OPERATIONAL_CLAIMED",
        source_type=ForcingSourceType.OPERATIONAL_ANALYSIS,
        is_authoritative=True,
        adapter_id="unregistered_provider",
        verification_token="bogus_token",
        constant_current_u=0.2,
        constant_current_v=0.1,
    )
    obs = ObservationRecord(
        event_id="test_event_02",
        observation_time=base_time,
        source_scene="S1A_TEST",
        timestamp_provenance=TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA,
        geometry={"type": "Point", "coordinates": [-90.0, 27.0]},
        centroid=[-90.0, 27.0],
        area_m2=50000.0,
    )
    with pytest.raises(ProvenanceGateError, match="PHYSICAL mode rejected"):
        run_origin_drift_analysis(
            observation=obs,
            forcing_field=forcing,
            direction=DirectionMode.BACKWARD,
            mode=DriftMode.PHYSICAL,
            duration_hours=6.0,
        )


# ---------------------------------------------------------------------------
# 3. Corrupt AIS record (NaN/inf and boundary rejection)
# ---------------------------------------------------------------------------

def test_adv_03_corrupt_ais_record(base_time: datetime):
    """NaN, infinite, or out-of-bounds coordinates must fail immediately upon instantiation."""
    with pytest.raises(ValueError, match="finite numbers"):
        AISRecord(mmsi="100", timestamp=base_time, longitude=float("nan"), latitude=27.0)

    with pytest.raises(ValueError, match="finite numbers"):
        AISRecord(mmsi="100", timestamp=base_time, longitude=-90.0, latitude=float("inf"))

    with pytest.raises(ValueError, match="coordinates out of range"):
        AISRecord(mmsi="100", timestamp=base_time, longitude=-185.0, latitude=27.0)

    with pytest.raises(ValueError, match="coordinates out of range"):
        AISRecord(mmsi="100", timestamp=base_time, longitude=-90.0, latitude=95.0)


# ---------------------------------------------------------------------------
# 4. One bad speed segment (Degraded track kept, not completely discarded)
# ---------------------------------------------------------------------------

def test_adv_04_one_bad_speed_segment(base_time: datetime):
    """A single 120-knot jump must be flagged and rejected without discarding valid track segments."""
    records = []
    # 5 valid points (12 knots ~ 0.2 nmi per min)
    for i in range(5):
        t = base_time + timedelta(minutes=i * 10)
        records.append(
            AISRecord(
                mmsi="444001",
                timestamp=t,
                longitude=-90.0 + i * 0.02,
                latitude=27.0 + i * 0.02,
                sog_knots=12.0,
            )
        )
    # 1 anomalous point 2 degrees away 1 minute later (> 600 knots)
    records.append(
        AISRecord(
            mmsi="444001",
            timestamp=base_time + timedelta(minutes=41),
            longitude=-88.0,
            latitude=29.0,
            sog_knots=12.0,
        )
    )
    # 3 more valid points continuing from the initial route
    for i in range(5, 8):
        t = base_time + timedelta(minutes=i * 10)
        records.append(
            AISRecord(
                mmsi="444001",
                timestamp=t,
                longitude=-90.0 + i * 0.02,
                latitude=27.0 + i * 0.02,
                sog_knots=12.0,
            )
        )

    tracks = filter_and_assemble_vessel_tracks(records, max_plausible_speed_knots=60.0)
    assert "444001" in tracks
    track = tracks["444001"]

    # Verify track quality assessment
    report = track.quality_report
    assert report.records_received == 9
    assert report.records_rejected == 1
    assert report.records_retained == 8
    assert report.quality_class == TrackQualityClass.DEGRADED
    assert report.is_usable is True
    assert len(report.speed_anomalies) == 1
    assert report.speed_anomalies[0]["apparent_speed_knots"] > 60.0


# ---------------------------------------------------------------------------
# 5. Large AIS gap (Flagged without false interpolation across gap)
# ---------------------------------------------------------------------------

def test_adv_05_large_ais_gap(base_time: datetime, sample_hypotheses_trajectory):
    """Vessel with an 8-hour gap must not interpolate across the gap."""
    # Vessel has observation at base_time - 10h and base_time - 2h (8 hour gap)
    t1 = base_time - timedelta(hours=10)
    t2 = base_time - timedelta(hours=2)
    r1 = AISRecord(mmsi="555001", timestamp=t1, longitude=-90.5, latitude=26.5)
    r2 = AISRecord(mmsi="555001", timestamp=t2, longitude=-90.1, latitude=26.9)

    tracks = filter_and_assemble_vessel_tracks([r1, r2], max_interpolation_gap_seconds=7200.0)
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=sample_hypotheses_trajectory,
        max_interpolation_gap_seconds=7200.0,
        mode=AISCorrelationMode.DEMO,
    )
    assert len(metrics) == 1
    m = metrics[0]
    # The gap is 8h (28800s) which exceeds 2h (7200s)
    # The hypothesis at 6h back cannot be interpolated between r1 and r2
    assert m.is_position_inferred is False
    assert m.coverage_status == VesselCoverageStatus.TELEMETRY_GAP_ACROSS_WINDOW.value
    assert any("large telemetry gap" in lim for lim in m.data_limitations)


# ---------------------------------------------------------------------------
# 6. Wrong timestamp (Temporal offset decay & gating)
# ---------------------------------------------------------------------------

def test_adv_06_wrong_timestamp(base_time: datetime, sample_hypotheses_trajectory):
    """Vessel precisely at the origin coordinates but 48 hours early receives low score."""
    t_wrong = base_time - timedelta(hours=48)
    r1 = AISRecord(mmsi="666001", timestamp=t_wrong, longitude=-90.6, latitude=26.4)
    r2 = AISRecord(mmsi="666001", timestamp=t_wrong + timedelta(minutes=10), longitude=-90.6, latitude=26.4)

    tracks = filter_and_assemble_vessel_tracks([r1, r2])
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=sample_hypotheses_trajectory,
        mode=AISCorrelationMode.DEMO,
    )
    assert len(metrics) == 1
    m = metrics[0]
    # Temporal offset is ~36 hours (relative to 12h backtrack origin)
    assert m.temporal_offset_seconds >= 35 * 3600
    assert m.score_breakdown["temporal_proximity_component"] < 1e-6
    assert m.evidence_compatibility_score < 0.10


# ---------------------------------------------------------------------------
# 7. Future AIS timestamp (Handled safely)
# ---------------------------------------------------------------------------

def test_adv_07_future_ais_timestamp(base_time: datetime, sample_hypotheses_trajectory):
    """Vessel observation timestamp far in the future must be handled cleanly."""
    t_future = base_time + timedelta(days=5)
    r1 = AISRecord(mmsi="777001", timestamp=t_future, longitude=-90.0, latitude=27.0)
    r2 = AISRecord(mmsi="777001", timestamp=t_future + timedelta(minutes=15), longitude=-90.0, latitude=27.0)

    tracks = filter_and_assemble_vessel_tracks([r1, r2])
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=sample_hypotheses_trajectory,
        mode=AISCorrelationMode.DEMO,
    )
    assert len(metrics) == 1
    assert metrics[0].coverage_status == VesselCoverageStatus.OUTSIDE_WINDOW.value


# ---------------------------------------------------------------------------
# 8. Out-of-window vessel (VesselCoverageStatus.OUTSIDE_WINDOW)
# ---------------------------------------------------------------------------

def test_adv_08_out_of_window_vessel(base_time: datetime, sample_hypotheses_trajectory):
    """Vessel with track completely outside modeled drift window."""
    t_past = base_time - timedelta(days=2)
    r1 = AISRecord(mmsi="888001", timestamp=t_past, longitude=-90.0, latitude=27.0)
    r2 = AISRecord(mmsi="888001", timestamp=t_past + timedelta(minutes=30), longitude=-90.0, latitude=27.0)

    tracks = filter_and_assemble_vessel_tracks([r1, r2])
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=sample_hypotheses_trajectory,
        mode=AISCorrelationMode.DEMO,
    )
    assert len(metrics) == 1
    assert metrics[0].coverage_status == VesselCoverageStatus.OUTSIDE_WINDOW.value


# ---------------------------------------------------------------------------
# 9. Trajectory-envelope-only intersection (Does not inflate particle score)
# ---------------------------------------------------------------------------

def test_adv_09_trajectory_envelope_only_intersection(base_time: datetime, sample_hypotheses_trajectory):
    """Vessel intersects the broad envelope polygon but is 20km away from any particle trajectory."""
    # Envelope covers a broad box
    env_poly = box(-91.0, 26.0, -89.5, 27.5)

    # Vessel point is at (-89.6, 26.1), inside envelope box, but far from trajectory
    t_sample = base_time - timedelta(hours=6)
    r1 = AISRecord(mmsi="999001", timestamp=t_sample, longitude=-89.6, latitude=26.1)
    r2 = AISRecord(mmsi="999001", timestamp=t_sample + timedelta(minutes=10), longitude=-89.6, latitude=26.1)

    tracks = filter_and_assemble_vessel_tracks([r1, r2])
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=sample_hypotheses_trajectory,
        trajectory_envelope_polygon=env_poly,
        mode=AISCorrelationMode.DEMO,
    )
    assert len(metrics) == 1
    m = metrics[0]
    assert m.inside_trajectory_envelope is True
    assert m.min_distance_to_trajectory_m > 40000.0  # > 40 km away from particles
    assert m.score_breakdown["spatial_trajectory_proximity_component"] < 1e-3
    assert m.evidence_compatibility_score <= 0.301


# ---------------------------------------------------------------------------
# 10. Candidate-origin-only intersection at wrong time (Temporally gated)
# ---------------------------------------------------------------------------

def test_adv_10_candidate_origin_only_intersection_at_wrong_time(base_time: datetime, sample_hypotheses_trajectory):
    """Vessel inside candidate origin polygon, but 14 hours after the origin endpoint time."""
    origin_poly = box(-90.65, 26.35, -90.55, 26.45)
    # Origin endpoint hypothesis is at base_time - 12h
    # Vessel is at origin coordinates at base_time + 2h (14 hours difference)
    t_vessel = base_time + timedelta(hours=2)
    r1 = AISRecord(mmsi="101001", timestamp=t_vessel, longitude=-90.6, latitude=26.4)
    r2 = AISRecord(mmsi="101001", timestamp=t_vessel + timedelta(minutes=15), longitude=-90.6, latitude=26.4)

    tracks = filter_and_assemble_vessel_tracks([r1, r2])
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=sample_hypotheses_trajectory,
        candidate_origin_polygon=origin_poly,
        origin_coarse_time_window_seconds=10800.0,  # 3 hour coarse window
        mode=AISCorrelationMode.DEMO,
    )
    assert len(metrics) == 1
    m = metrics[0]
    # Gated out because 14h > 3h coarse window
    assert m.inside_candidate_origin_region is False
    assert m.score_breakdown["origin_polygon_coincidence"] < 1e-5


# ---------------------------------------------------------------------------
# 11. Valid trajectory intersection at intermediate time (e.g. 6h back)
# ---------------------------------------------------------------------------

def test_adv_11_valid_trajectory_intersection_at_intermediate_time(base_time: datetime, sample_hypotheses_trajectory):
    """Vessel matches an intermediate trajectory hypothesis (6h back) within 150m, though 45km from terminal origin."""
    t_6h = base_time - timedelta(hours=6)
    # Hypothesis at 6h back: lon = -90.0 - 6*0.05 = -90.3, lat = 27.0 - 6*0.05 = 26.7
    r1 = AISRecord(mmsi="111001", timestamp=t_6h, longitude=-90.301, latitude=26.701)
    r2 = AISRecord(mmsi="111001", timestamp=t_6h + timedelta(minutes=20), longitude=-90.290, latitude=26.710)

    origin_poly = box(-90.65, 26.35, -90.55, 26.45)  # 12h terminal origin

    tracks = filter_and_assemble_vessel_tracks([r1, r2])
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=sample_hypotheses_trajectory,
        candidate_origin_polygon=origin_poly,
        mode=AISCorrelationMode.DEMO,
    )
    assert len(metrics) == 1
    m = metrics[0]
    assert m.min_distance_to_trajectory_m < 200.0  # Close to 6h particle
    assert m.closest_hypothesis_step == 6
    assert m.temporal_offset_seconds == 0.0
    assert m.inside_candidate_origin_region is False  # Never entered terminal polygon
    # But receives high compatibility score because trajectory particle matching is PRIMARY!
    assert m.evidence_compatibility_score > 0.65


# ---------------------------------------------------------------------------
# 12. Multiple equally plausible candidates (Deterministic ranking & separation)
# ---------------------------------------------------------------------------

def test_adv_12_multiple_equally_plausible_candidates(base_time: datetime, sample_hypotheses_trajectory):
    """Two distinct vessels with identical kinematics and proximity must both be ranked deterministically."""
    t_6h = base_time - timedelta(hours=6)
    v1_recs = [
        AISRecord(mmsi="121001", timestamp=t_6h, longitude=-90.301, latitude=26.701, vessel_name="VESSEL_A"),
        AISRecord(mmsi="121001", timestamp=t_6h + timedelta(minutes=15), longitude=-90.29, latitude=26.71, vessel_name="VESSEL_A"),
    ]
    v2_recs = [
        AISRecord(mmsi="121002", timestamp=t_6h, longitude=-90.301, latitude=26.701, vessel_name="VESSEL_B"),
        AISRecord(mmsi="121002", timestamp=t_6h + timedelta(minutes=15), longitude=-90.29, latitude=26.71, vessel_name="VESSEL_B"),
    ]
    tracks = filter_and_assemble_vessel_tracks(v1_recs + v2_recs)
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=sample_hypotheses_trajectory,
        mode=AISCorrelationMode.DEMO,
    )
    assert len(metrics) == 2
    assert abs(metrics[0].evidence_compatibility_score - metrics[1].evidence_compatibility_score) < 1e-5
    mmsis = {m.mmsi for m in metrics}
    assert mmsis == {"121001", "121002"}


# ---------------------------------------------------------------------------
# 13. No candidates (Empty track collection handled safely)
# ---------------------------------------------------------------------------

def test_adv_13_no_candidates(sample_hypotheses_trajectory):
    """Empty tracks dictionary must safely produce empty candidates list."""
    metrics = correlate_vessel_tracks(
        tracks={},
        hypotheses=sample_hypotheses_trajectory,
        mode=AISCorrelationMode.DEMO,
    )
    assert metrics == []
    summary = serialize_ais_correlation_summary(metrics, tracks={})
    assert summary["total_vessels_evaluated"] == 0
    assert summary["candidate_vessels"] == []


# ---------------------------------------------------------------------------
# 14. Missing vessel metadata (None preserved without fabrication)
# ---------------------------------------------------------------------------

def test_adv_14_missing_vessel_metadata(base_time: datetime, sample_hypotheses_trajectory):
    """Missing vessel names, IMO, and types must remain None without fabricating values."""
    rec = AISRecord(
        mmsi="141001",
        timestamp=base_time,
        longitude=-90.0,
        latitude=27.0,
        vessel_name=None,
        imo=None,
        vessel_type=None,
        navigation_status=None,
    )
    tracks = filter_and_assemble_vessel_tracks([rec, rec])
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=sample_hypotheses_trajectory,
        mode=AISCorrelationMode.DEMO,
    )
    assert len(metrics) == 1
    m = metrics[0]
    assert m.vessel_name is None
    assert m.imo is None
    assert m.vessel_type is None
    d = m.to_dict()
    assert d["vessel_name"] is None
    assert d["imo"] is None
    assert d["vessel_type"] is None


# ---------------------------------------------------------------------------
# 15. Antimeridian coordinates (Wrapping handled deterministically)
# ---------------------------------------------------------------------------

def test_adv_15_antimeridian_coordinates():
    """Distance calculations across the antimeridian (180 / -180) must be accurate and bounded."""
    # Two points across antimeridian: 179.9° and -179.9° at equator
    # Longitudinal distance is 0.2 degrees ~ 22.2 km
    d = haversine_distance_m(179.9, 0.0, -179.9, 0.0)
    assert 22000.0 < d < 22500.0

    # Test coordinate wrapping
    rec = AISRecord(
        mmsi="151001",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        longitude=180.0,
        latitude=0.0,
    )
    assert rec.longitude == 180.0


# ---------------------------------------------------------------------------
# 16. High-latitude geometry (Polar guard & numerical stability)
# ---------------------------------------------------------------------------

def test_adv_16_high_latitude_geometry():
    """High-latitude calculations (e.g. 75°N and 85°N) must not overflow or divide by zero."""
    d = haversine_distance_m(0.0, 85.0, 10.0, 85.0)
    assert np.isfinite(d)
    assert d > 0.0

    # Verify polar guard in drift trajectory integration
    forcing = MetoceanForcingField(
        forcing_source="TEST_POLAR",
        source_type=ForcingSourceType.SYNTHETIC_TEST_FIXTURE,
        is_authoritative=False,
        constant_current_u=0.5,
        constant_current_v=0.0,
        constant_wind_u=2.0,
        constant_wind_v=1.0,
    )
    obs = ObservationRecord(
        event_id="polar_event",
        observation_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        source_scene="S1_POLAR",
        timestamp_provenance=TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA,
        geometry={"type": "Point", "coordinates": [0.0, 85.0]},
        centroid=[0.0, 85.0],
        area_m2=10000.0,
    )
    report, _, _ = run_origin_drift_analysis(
        observation=obs,
        forcing_field=forcing,
        direction=DirectionMode.FORWARD,
        mode=DriftMode.DEMO,
        duration_hours=2.0,
        timestep_seconds=1800.0,
    )
    assert report["summary_statistics"]["trajectory_count"] > 0


# ---------------------------------------------------------------------------
# 17. Empty drift hypothesis set (Handled safely)
# ---------------------------------------------------------------------------

def test_adv_17_empty_drift_hypothesis_set(base_time: datetime):
    """Empty candidate hypotheses list must safely return empty list."""
    rec = AISRecord(mmsi="171001", timestamp=base_time, longitude=-90.0, latitude=27.0)
    tracks = filter_and_assemble_vessel_tracks([rec, rec])
    metrics = correlate_vessel_tracks(
        tracks=tracks,
        hypotheses=[],
        mode=AISCorrelationMode.DEMO,
    )
    assert metrics == []


# ---------------------------------------------------------------------------
# 18. Invalid GeoJSON (Handled safely with clear error)
# ---------------------------------------------------------------------------

def test_adv_18_invalid_geojson(tmp_path: Path):
    """Corrupted GeoJSON file must be rejected cleanly by load_drift_artifacts."""
    from scripts.run_ais_correlation import load_drift_artifacts

    bad_json = tmp_path / "corrupted_drift.geojson"
    bad_json.write_text("{\"type\": \"NotAFeatureCollection\"}", encoding="utf-8")

    with pytest.raises(ValueError, match="Expected GeoJSON FeatureCollection"):
        load_drift_artifacts(bad_json)


# ---------------------------------------------------------------------------
# 19. DEMO data passed to PHYSICAL mode (Fails closed)
# ---------------------------------------------------------------------------

def test_adv_19_demo_data_passed_to_physical_mode(sample_hypotheses_trajectory):
    """Synthetic demo fixture passed to PHYSICAL mode must be strictly rejected."""
    demo_records = generate_deterministic_demo_ais_fixture()
    tracks = filter_and_assemble_vessel_tracks(demo_records)

    with pytest.raises(ProvenanceGateError, match="PHYSICAL mode rejected"):
        correlate_vessel_tracks(
            tracks=tracks,
            hypotheses=sample_hypotheses_trajectory,
            mode=AISCorrelationMode.PHYSICAL,
        )


# ---------------------------------------------------------------------------
# 20. PHYSICAL mode with missing provenance (Fails closed)
# ---------------------------------------------------------------------------

def test_adv_20_physical_mode_with_missing_provenance(base_time: datetime, sample_hypotheses_trajectory):
    """Record with unverified/missing provenance in PHYSICAL mode must be strictly rejected."""
    rec = AISRecord(
        mmsi="202001",
        timestamp=base_time,
        longitude=-90.0,
        latitude=27.0,
        provenance="",
        adapter_id=None,
    )
    tracks = filter_and_assemble_vessel_tracks([rec, rec])

    with pytest.raises(ProvenanceGateError, match="PHYSICAL mode rejected"):
        correlate_vessel_tracks(
            tracks=tracks,
            hypotheses=sample_hypotheses_trajectory,
            mode=AISCorrelationMode.PHYSICAL,
        )


# ---------------------------------------------------------------------------
# CLI Standardized Exit Code Contract Tests
# ---------------------------------------------------------------------------

def test_cli_exit_code_contract():
    """Verify CLI exit codes adhere to: 0=SUCCESS, 1=ERROR, 2=PROVENANCE_REJECTION, 3=INVALID_INPUT."""
    import subprocess
    import sys

    py_exe = sys.executable
    script_drift = str(REPO_ROOT / "scripts" / "run_origin_drift.py")
    script_ais = str(REPO_ROOT / "scripts" / "run_ais_correlation.py")

    # 1. Invalid input: missing file -> returncode 3
    res = subprocess.run([py_exe, script_drift, "--event", "nonexistent_event_file.json"], capture_output=True)
    assert res.returncode == 3

    # 2. Invalid input: missing drift geojson -> returncode 3
    res = subprocess.run([py_exe, script_ais, "--drift-geojson", "nonexistent_drift.geojson"], capture_output=True)
    assert res.returncode == 3

    # 3. Provenance rejection: drift in PHYSICAL mode without accredited forcing -> returncode 2
    sample_geojson = REPO_ROOT / "outputs" / "origin_drift" / "trujillo_part1_origin_drift.geojson"
    if sample_geojson.is_file():
        res = subprocess.run(
            [py_exe, script_ais, "--drift-geojson", str(sample_geojson), "--mode", "physical"],
            capture_output=True,
        )
        assert res.returncode == 2


# ---------------------------------------------------------------------------
# 21. Distance Calculation Matrix (Spherical Haversine)
# ---------------------------------------------------------------------------

def test_adv_21_distance_calculation_matrix():
    """Verify spherical Haversine distance across diverse planetary geometries."""
    # 1. Equator: 1 degree along Equator (111.195 km)
    d_eq = haversine_distance_m(0.0, 0.0, 1.0, 0.0)
    assert 111_000.0 < d_eq < 111_400.0

    # 2. Meridional distance: 1 degree along meridian (111.195 km)
    d_mer = haversine_distance_m(0.0, 0.0, 0.0, 1.0)
    assert 111_000.0 < d_mer < 111_400.0

    # 3. East/West at 60 deg N: 1 degree along parallel (111.195 * cos(60) = 55.597 km)
    d_60n = haversine_distance_m(0.0, 60.0, 1.0, 60.0)
    assert 55_400.0 < d_60n < 55_800.0

    # 4. Antimeridian crossing: 179.99 to -179.99 (0.02 deg apart = ~2.22 km)
    d_anti = haversine_distance_m(179.99, 0.0, -179.99, 0.0)
    assert 2_200.0 < d_anti < 2_250.0

    # 5. High latitude: 85 deg N (111.195 * cos(85) = ~9.69 km)
    d_85n = haversine_distance_m(0.0, 85.0, 1.0, 85.0)
    assert 9_600.0 < d_85n < 9_800.0

    # 6. Short distance: ~11 meters
    d_short = haversine_distance_m(0.0, 0.0, 0.0001, 0.0)
    assert 10.0 < d_short < 12.0

    # 7. Long intercontinental distance: London to New York (~5,570 km)
    d_long = haversine_distance_m(0.0, 51.5, -74.0, 40.7)
    assert 5_500_000.0 < d_long < 5_650_000.0


# ---------------------------------------------------------------------------
# 22. SLERP Geodesic Interpolation & Dateline Crossing
# ---------------------------------------------------------------------------

def test_adv_22_slerp_geodesic_interpolation_and_dateline_crossing():
    """Verify great-circle SLERP interpolation across antimeridian and high latitudes."""
    # 1. Dateline crossing: 179.9 to -179.9 at Equator
    # Midpoint must be at 180.0 (or -180.0), NOT at 0.0 (Greenwich)
    lon_mid, lat_mid = interpolate_geodesic_position(179.9, 0.0, -179.9, 0.0, fraction=0.5)
    assert abs(abs(lon_mid) - 180.0) < 1e-4
    assert abs(lat_mid - 0.0) < 1e-4

    # 2. Polar crossing: 0 deg E, 85 deg N to 180 deg E, 85 deg N
    # Great circle arc passes directly over the North Pole (90 deg N)
    lon_pole, lat_pole = interpolate_geodesic_position(0.0, 85.0, 180.0, 85.0, fraction=0.5)
    assert abs(lat_pole - 90.0) < 1e-4

    # 3. Boundary conditions: fraction 0.0 and 1.0
    lon_0, lat_0 = interpolate_geodesic_position(10.0, 20.0, 30.0, 40.0, fraction=0.0)
    assert lon_0 == 10.0 and lat_0 == 20.0

    lon_1, lat_1 = interpolate_geodesic_position(10.0, 20.0, 30.0, 40.0, fraction=1.0)
    assert lon_1 == 30.0 and lat_1 == 40.0

    # 4. Ordinary midpoint along equator
    lon_ord, lat_ord = interpolate_geodesic_position(0.0, 0.0, 10.0, 0.0, fraction=0.5)
    assert abs(lon_ord - 5.0) < 1e-4
    assert abs(lat_ord - 0.0) < 1e-4

    # 5. Coincident endpoints: fraction 0.5 must return the exact point without division by zero
    lon_coin, lat_coin = interpolate_geodesic_position(12.34, 56.78, 12.34, 56.78, fraction=0.5)
    assert abs(lon_coin - 12.34) < 1e-4
    assert abs(lat_coin - 56.78) < 1e-4

    # 6. Near-antipodal stability: points separated by nearly 180 degrees must not divide by zero
    lon_anti, lat_anti = interpolate_geodesic_position(0.0, 0.0, 179.9999, 0.0, fraction=0.5)
    assert np.isfinite(lon_anti) and np.isfinite(lat_anti)


# ---------------------------------------------------------------------------
# 23. Interpolation Bracket and Inference Flag Correctness
# ---------------------------------------------------------------------------

def test_adv_23_interpolation_bracket_and_inference_flag(base_time: datetime):
    """Verify observed vs inferred position classification across various time brackets."""
    # 1. Exact sample match: hypothesis time exactly matches AIS observation
    r1 = AISRecord(mmsi="23001", timestamp=base_time, longitude=-90.0, latitude=27.0)
    r2 = AISRecord(mmsi="23001", timestamp=base_time + timedelta(minutes=30), longitude=-90.1, latitude=27.1)
    tracks = filter_and_assemble_vessel_tracks([r1, r2])

    hyp_exact = [
        CandidateHypothesisPoint(
            longitude=-90.0, latitude=27.0, timestamp=base_time,
            particle_id="p0", windage_factor=0.03, trajectory_step=0, is_origin_endpoint=True
        )
    ]
    res_exact = correlate_vessel_tracks(tracks=tracks, hypotheses=hyp_exact, mode=AISCorrelationMode.DEMO)
    assert res_exact[0].is_position_inferred is False  # Directly observed at base_time

    # 2. Intermediate inferred match (15 minutes in a 30-minute bracket)
    hyp_mid = [
        CandidateHypothesisPoint(
            longitude=-90.05, latitude=27.05, timestamp=base_time + timedelta(minutes=15),
            particle_id="p0", windage_factor=0.03, trajectory_step=1, is_origin_endpoint=False
        )
    ]
    res_mid = correlate_vessel_tracks(tracks=tracks, hypotheses=hyp_mid, mode=AISCorrelationMode.DEMO)
    assert res_mid[0].is_position_inferred is True  # Interpolated between r1 and r2
    assert res_mid[0].interpolation_gap_seconds == 1800.0

    # 3. Bracket over tau_max (7300s > 7200s): must NOT interpolate across excessive gap
    r_gap1 = AISRecord(mmsi="23002", timestamp=base_time, longitude=-90.0, latitude=27.0)
    r_gap2 = AISRecord(mmsi="23002", timestamp=base_time + timedelta(seconds=7300), longitude=-90.5, latitude=27.5)
    tracks_gap = filter_and_assemble_vessel_tracks([r_gap1, r_gap2])

    hyp_in_gap = [
        CandidateHypothesisPoint(
            longitude=-90.25, latitude=27.25, timestamp=base_time + timedelta(seconds=3600),
            particle_id="p0", windage_factor=0.03, trajectory_step=1, is_origin_endpoint=False
        )
    ]
    res_gap = correlate_vessel_tracks(
        tracks=tracks_gap, hypotheses=hyp_in_gap, max_interpolation_gap_seconds=7200.0, mode=AISCorrelationMode.DEMO
    )
    assert res_gap[0].is_position_inferred is False  # Refused interpolation across gap > tau_max


# ---------------------------------------------------------------------------
# 24. Closed Registry Unaccredited Adapter Rejection
# ---------------------------------------------------------------------------

def test_adv_24_closed_registry_unaccredited_adapter_rejection():
    """Unaccredited dynamic adapter registration attempts must be rejected fail-closed."""
    # 1. AIS unaccredited operational adapter
    fake_ais = AISProviderAdapter(adapter_id="dynamic_fake_ais", is_operational=True)
    with pytest.raises(ProvenanceGateError, match="Untrusted AIS adapter registration rejected"):
        AISSourceRegistry.register_adapter(fake_ais)

    # 2. Metocean unaccredited operational adapter
    fake_met = MetoceanProviderAdapter(adapter_id="dynamic_fake_met", is_operational=True)
    with pytest.raises(ProvenanceGateError, match="Untrusted adapter registration rejected"):
        MetoceanSourceRegistry.register_adapter(fake_met)


# ---------------------------------------------------------------------------
# 25. Post-Validation Metadata Tampering Detection
# ---------------------------------------------------------------------------

def test_adv_25_post_validation_metadata_tampering_detection(base_time: datetime):
    """Modifying metadata attributes post-instantiation must be detected and rejected."""
    # 1. AIS Record tampering
    rec = AISRecord(
        mmsi="25001",
        timestamp=base_time,
        longitude=-90.0,
        latitude=27.0,
        provenance=AISProvenance.SYNTHETIC_DEMO_FEED,
    )
    assert rec.verify_integrity() is True

    # Mutate provenance after instantiation
    rec.provenance = AISProvenance.VERIFIED_OPERATIONAL_FEED.value
    assert rec.verify_integrity() is False

    tracks = filter_and_assemble_vessel_tracks([rec, rec])
    hyp = [
        CandidateHypothesisPoint(
            longitude=-90.0, latitude=27.0, timestamp=base_time,
            particle_id="p0", windage_factor=0.03, trajectory_step=0, is_origin_endpoint=True
        )
    ]
    with pytest.raises(ProvenanceGateError, match="Tamper detection rejected for vessel"):
        correlate_vessel_tracks(tracks=tracks, hypotheses=hyp, mode=AISCorrelationMode.DEMO)

    # 2. Forcing field tampering
    forcing = MetoceanForcingField(
        forcing_source="gulf_forcing",
        source_type=ForcingSourceType.SYNTHETIC_TEST_FIXTURE,
        is_authoritative=False,
    )
    assert forcing.verify_integrity() is True
    forcing.is_authoritative = True  # Tampering
    assert forcing.verify_integrity() is False

    obs = ObservationRecord(
        event_id="test_tamper_obs",
        source_scene="scene_1",
        observation_time=base_time,
        timestamp_provenance=TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP,
        geometry={"type": "Point", "coordinates": [-90.0, 27.0]},
        centroid=[-90.0, 27.0],
        area_m2=1000.0,
    )
    with pytest.raises(ProvenanceGateError, match="Tamper detection rejected for forcing field"):
        run_origin_drift_analysis(observation=obs, forcing_field=forcing, mode=DriftMode.DEMO)


# ---------------------------------------------------------------------------
# 26. First-Point Outlier Anomaly Rejection
# ---------------------------------------------------------------------------

def test_adv_26_first_point_outlier_rejection(base_time: datetime):
    """First-point GPS jump must be rejected while preserving the remaining legitimate track."""
    # Point 0 is at (0, 0) - teleportation spike (>2000 km away)
    p0 = AISRecord(mmsi="26001", timestamp=base_time, longitude=0.0, latitude=0.0)
    # Points 1, 2, 3 are legitimate track in Gulf of Mexico (10-minute intervals, 12 knots)
    p1 = AISRecord(mmsi="26001", timestamp=base_time + timedelta(minutes=10), longitude=-90.0, latitude=27.0)
    p2 = AISRecord(mmsi="26001", timestamp=base_time + timedelta(minutes=20), longitude=-90.03, latitude=27.03)
    p3 = AISRecord(mmsi="26001", timestamp=base_time + timedelta(minutes=30), longitude=-90.06, latitude=27.06)

    tracks = filter_and_assemble_vessel_tracks([p0, p1, p2, p3], max_plausible_speed_knots=60.0)
    assert "26001" in tracks
    track = tracks["26001"]

    # Point 0 rejected, Points 1, 2, 3 retained
    assert track.quality_report.records_received == 4
    assert track.quality_report.records_rejected == 1
    assert track.quality_report.records_retained == 3
    assert track.records[0].longitude == -90.0
    assert track.quality_report.quality_class == TrackQualityClass.DEGRADED
    assert track.quality_report.is_usable is True


# ---------------------------------------------------------------------------
# 27. Last-Point Outlier Anomaly Rejection
# ---------------------------------------------------------------------------

def test_adv_27_last_point_outlier_rejection(base_time: datetime):
    """Last-point GPS jump must be rejected while preserving preceding valid track."""
    p0 = AISRecord(mmsi="27001", timestamp=base_time, longitude=-90.0, latitude=27.0)
    p1 = AISRecord(mmsi="27001", timestamp=base_time + timedelta(minutes=10), longitude=-90.03, latitude=27.03)
    p2 = AISRecord(mmsi="27001", timestamp=base_time + timedelta(minutes=20), longitude=-90.06, latitude=27.06)
    # Point 3 jumps to (0, 0)
    p3 = AISRecord(mmsi="27001", timestamp=base_time + timedelta(minutes=30), longitude=0.0, latitude=0.0)

    tracks = filter_and_assemble_vessel_tracks([p0, p1, p2, p3], max_plausible_speed_knots=60.0)
    track = tracks["27001"]
    assert track.quality_report.records_retained == 3
    assert track.records[-1].longitude == -90.06
    assert track.quality_report.records_rejected == 1


# ---------------------------------------------------------------------------
# 28. Two Consecutive Outliers Rejection
# ---------------------------------------------------------------------------

def test_adv_28_consecutive_outliers_rejection(base_time: datetime):
    """Consecutive telemetry outliers in track must be isolated without breaking the track."""
    p0 = AISRecord(mmsi="28001", timestamp=base_time, longitude=-90.0, latitude=27.0)
    p1 = AISRecord(mmsi="28001", timestamp=base_time + timedelta(minutes=10), longitude=-90.03, latitude=27.03)
    # Consecutive bad points
    b1 = AISRecord(mmsi="28001", timestamp=base_time + timedelta(minutes=15), longitude=-80.0, latitude=20.0)
    b2 = AISRecord(mmsi="28001", timestamp=base_time + timedelta(minutes=18), longitude=-70.0, latitude=15.0)
    # Valid continuation
    p2 = AISRecord(mmsi="28001", timestamp=base_time + timedelta(minutes=20), longitude=-90.06, latitude=27.06)
    p3 = AISRecord(mmsi="28001", timestamp=base_time + timedelta(minutes=30), longitude=-90.09, latitude=27.09)

    tracks = filter_and_assemble_vessel_tracks([p0, p1, b1, b2, p2, p3], max_plausible_speed_knots=60.0)
    track = tracks["28001"]
    assert track.quality_report.records_retained == 4
    assert track.quality_report.records_rejected == 2
    assert track.quality_report.is_usable is True


# ---------------------------------------------------------------------------
# 29. Alternating Outliers Rejection
# ---------------------------------------------------------------------------

def test_adv_29_alternating_outliers_rejection(base_time: datetime):
    """Alternating good/bad records must isolate all bad records."""
    records = [
        AISRecord(mmsi="29001", timestamp=base_time, longitude=-90.0, latitude=27.0),
        AISRecord(mmsi="29001", timestamp=base_time + timedelta(minutes=5), longitude=0.0, latitude=0.0),
        AISRecord(mmsi="29001", timestamp=base_time + timedelta(minutes=10), longitude=-90.03, latitude=27.03),
        AISRecord(mmsi="29001", timestamp=base_time + timedelta(minutes=15), longitude=0.0, latitude=0.0),
        AISRecord(mmsi="29001", timestamp=base_time + timedelta(minutes=20), longitude=-90.06, latitude=27.06),
    ]
    tracks = filter_and_assemble_vessel_tracks(records, max_plausible_speed_knots=60.0)
    track = tracks["29001"]
    assert track.quality_report.records_retained == 3
    assert track.quality_report.records_rejected == 2
    assert track.quality_report.is_usable is True


# ---------------------------------------------------------------------------
# 30. Excessive Outliers Mark Track Unusable
# ---------------------------------------------------------------------------

def test_adv_30_excessive_outliers_unusable_track(base_time: datetime):
    """Track with >50% anomalous points must be classified as UNUSABLE."""
    records = [
        AISRecord(mmsi="30001", timestamp=base_time, longitude=-90.0, latitude=27.0),
        AISRecord(mmsi="30001", timestamp=base_time + timedelta(minutes=2), longitude=10.0, latitude=10.0),
        AISRecord(mmsi="30001", timestamp=base_time + timedelta(minutes=4), longitude=20.0, latitude=20.0),
        AISRecord(mmsi="30001", timestamp=base_time + timedelta(minutes=6), longitude=30.0, latitude=30.0),
        AISRecord(mmsi="30001", timestamp=base_time + timedelta(minutes=8), longitude=-90.02, latitude=27.02),
    ]
    tracks = filter_and_assemble_vessel_tracks(records, max_plausible_speed_knots=60.0)
    track = tracks["30001"]
    assert track.quality_report.records_retained == 2
    assert track.quality_report.records_rejected == 3  # 3/5 = 60% rejected > 50%
    assert track.quality_report.quality_class == TrackQualityClass.UNUSABLE
    assert track.quality_report.is_usable is False


# ---------------------------------------------------------------------------
# 31. Score Sensitivity to Configured Weights
# ---------------------------------------------------------------------------

def test_adv_31_score_sensitivity_to_weights(base_time: datetime, sample_hypotheses_trajectory):
    """Verify evidence compatibility score changes deterministically when weights are reconfigured."""
    # Vessel passing moderately close to trajectory
    records = [
        AISRecord(mmsi="31001", timestamp=base_time - timedelta(hours=6), longitude=-90.35, latitude=26.75),
        AISRecord(mmsi="31001", timestamp=base_time - timedelta(hours=5), longitude=-90.30, latitude=26.80),
    ]
    tracks = filter_and_assemble_vessel_tracks(records)

    # Weight set 1: heavy trajectory weight (0.70)
    weights_traj = CompatibilityScoreWeights(
        weight_trajectory_spatial=0.70, weight_temporal_proximity=0.10, version="test_v1"
    )
    res1 = correlate_vessel_tracks(
        tracks=tracks, hypotheses=sample_hypotheses_trajectory, weights=weights_traj, mode=AISCorrelationMode.DEMO
    )

    # Weight set 2: heavy origin endpoint weight (0.70)
    weights_orig = CompatibilityScoreWeights(
        weight_origin_endpoint=0.70, weight_trajectory_spatial=0.10, version="test_v2"
    )
    res2 = correlate_vessel_tracks(
        tracks=tracks, hypotheses=sample_hypotheses_trajectory, weights=weights_orig, mode=AISCorrelationMode.DEMO
    )

    assert res1[0].evidence_compatibility_score != res2[0].evidence_compatibility_score
    assert res1[0].score_breakdown["score_weights_version"] == "test_v1"
    assert res2[0].score_breakdown["score_weights_version"] == "test_v2"


# ---------------------------------------------------------------------------
# 32. Negative-Proof Guard and Coverage Status Taxonomy
# ---------------------------------------------------------------------------

def test_adv_32_negative_proof_guard_and_coverage_status_taxonomy(base_time: datetime, sample_hypotheses_trajectory):
    """Verify AIS absence never implies vessel absence, and coverage statuses are properly categorized."""
    # Vessel 1: Observed inside window
    r_obs = [
        AISRecord(mmsi="32001", timestamp=base_time - timedelta(hours=6), longitude=-90.3, latitude=26.7),
        AISRecord(mmsi="32001", timestamp=base_time - timedelta(hours=5), longitude=-90.25, latitude=26.75),
    ]
    # Vessel 2: Outside window (2 days early)
    r_out = [
        AISRecord(mmsi="32002", timestamp=base_time - timedelta(days=2), longitude=-90.3, latitude=26.7),
        AISRecord(mmsi="32002", timestamp=base_time - timedelta(days=2) + timedelta(hours=1), longitude=-90.25, latitude=26.75),
    ]
    # Vessel 3: Telemetry gap across window (gap > 2 hours)
    r_gap = [
        AISRecord(mmsi="32003", timestamp=base_time - timedelta(hours=12), longitude=-90.3, latitude=26.7),
        AISRecord(mmsi="32003", timestamp=base_time, longitude=-90.25, latitude=26.75),
    ]

    all_records = r_obs + r_out + r_gap
    tracks = filter_and_assemble_vessel_tracks(all_records)
    results = correlate_vessel_tracks(tracks=tracks, hypotheses=sample_hypotheses_trajectory, mode=AISCorrelationMode.DEMO)

    status_map = {res.mmsi: res.coverage_status for res in results}
    assert status_map["32001"] == VesselCoverageStatus.OBSERVED_IN_WINDOW
    assert status_map["32002"] == VesselCoverageStatus.OUTSIDE_WINDOW
    assert status_map["32003"] == VesselCoverageStatus.TELEMETRY_GAP_ACROSS_WINDOW

    # Verify GeoJSON and Summary guardrails
    geojson = serialize_ais_correlation_to_geojson(results, tracks, mode=AISCorrelationMode.DEMO)
    assert geojson["metadata"]["negative_proof_guard"] == "AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE"

    summary = serialize_ais_correlation_summary(results, tracks, mode=AISCorrelationMode.DEMO)
    assert any("Absence of an AIS track" in lim for lim in summary["scientific_limitations"])

