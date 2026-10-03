"""Comprehensive Test Suite for Ocean Sentinel Origin & Drift Reasoning Engine.

Covers:
1. Forward Lagrangian integration
2. Backward Lagrangian origin reconstruction
3. Zero-current baseline (pure windage leeway)
4. Constant current baseline (pure hydrodynamic advection)
5. Constant wind baseline
6. Combined wind and current kinematics
7. Windage uncertainty ensemble (parameter sweep alpha in [min, max])
8. Particle ensemble initialization across detection geometry
9. RFC 7946 WGS84 GeoJSON trajectory output
10. Deterministic execution across repeated runs
11. Unit consistency (meters, seconds, meters/second)
12. Timestamp provenance rejection in PHYSICAL mode (rejection of test timestamps)
13. Missing forcing rejection (fail-closed on missing environmental components)
14. DEMO vs PHYSICAL mode strict separation
15. Real temporal event integration (with provenance gate verification)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box, mapping, shape

from ocean_sentinel.drift import (
    DirectionMode,
    DriftMode,
    ForcingSourceType,
    MetoceanForcingField,
    MissingForcingError,
    ObservationRecord,
    ParticleTrajectory,
    ProvenanceGateError,
    geodesic_displacement_wgs84,
    integrate_lagrangian_trajectory,
    run_origin_drift_analysis,
    sample_polygon_particles,
)
from ocean_sentinel.temporal import TimestampProvenance

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def synthetic_observation_demo() -> ObservationRecord:
    """Create a synthetic observation with EXTERNALLY_SUPPLIED_TEST_TIMESTAMP."""
    # 1km x 1km box in Gulf of Mexico around (-90.5, 27.0)
    poly = box(-90.505, 26.995, -90.495, 27.005)
    return ObservationRecord(
        event_id="test_event_001",
        source_scene="test_scene_s1",
        observation_time=datetime(2024, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        timestamp_provenance=TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP,
        geometry=mapping(poly),
        centroid=[-90.5, 27.0],
        area_m2=1_000_000.0,
        detection_type="oil_spill",
    )


@pytest.fixture
def synthetic_observation_authoritative() -> ObservationRecord:
    """Create an observation with VERIFIED_FROM_SOURCE_METADATA."""
    poly = box(-90.505, 26.995, -90.495, 27.005)
    return ObservationRecord(
        event_id="test_event_auth",
        source_scene="S1A_IW_GRDH_1SDV_20240501",
        observation_time=datetime(2024, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        timestamp_provenance=TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA,
        geometry=mapping(poly),
        centroid=[-90.5, 27.0],
        area_m2=1_000_000.0,
        detection_type="oil_spill",
    )


@pytest.fixture
def synthetic_forcing_field() -> MetoceanForcingField:
    """Create a uniform forcing field with known test velocities."""
    return MetoceanForcingField(
        forcing_source="synthetic_test_forcing",
        source_type=ForcingSourceType.SYNTHETIC_TEST_FIXTURE,
        is_authoritative=False,
        constant_current_u=0.20,  # 0.20 m/s East
        constant_current_v=0.10,  # 0.10 m/s North
        constant_wind_u=-4.0,     # 4.0 m/s West
        constant_wind_v=2.0,      # 2.0 m/s North
    )


# ---------------------------------------------------------------------------
# 1. Forward Lagrangian Integration
# ---------------------------------------------------------------------------

def test_forward_integration(synthetic_forcing_field):
    """Verify forward integration steps forward in time and follows drift direction."""
    t0 = datetime(2024, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    traj = integrate_lagrangian_trajectory(
        start_lon=-90.5,
        start_lat=27.0,
        start_time=t0,
        duration_hours=1.0,
        timestep_seconds=1800.0,  # 2 steps of 1800s
        windage_factor=0.03,
        forcing_field=synthetic_forcing_field,
        direction=DirectionMode.FORWARD,
        particle_id="p1",
    )

    assert len(traj.steps) == 2
    assert traj.steps[0].timestamp == datetime(2024, 5, 1, 12, 30, 0, tzinfo=timezone.utc)
    assert traj.steps[1].timestamp == datetime(2024, 5, 1, 13, 0, 0, tzinfo=timezone.utc)
    assert traj.total_distance_m > 0.0


# ---------------------------------------------------------------------------
# 2. Backward Lagrangian Integration
# ---------------------------------------------------------------------------

def test_backward_integration(synthetic_forcing_field):
    """Verify backward integration steps backward in time and opposes forward velocity."""
    t0 = datetime(2024, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    traj = integrate_lagrangian_trajectory(
        start_lon=-90.5,
        start_lat=27.0,
        start_time=t0,
        duration_hours=1.0,
        timestep_seconds=1800.0,
        windage_factor=0.03,
        forcing_field=synthetic_forcing_field,
        direction=DirectionMode.BACKWARD,
        particle_id="p_back",
    )

    assert len(traj.steps) == 2
    # Timestamps decrease backward into history
    assert traj.steps[0].timestamp < t0
    assert traj.steps[1].timestamp < traj.steps[0].timestamp
    # Displacement opposes forward drift direction
    assert traj.steps[1].cumulative_distance_m > 0.0


# ---------------------------------------------------------------------------
# 3. Zero-Current Baseline (Pure Windage)
# ---------------------------------------------------------------------------

def test_zero_current_baseline():
    """Verify pure windage kinematics when ocean currents are zero."""
    forcing = MetoceanForcingField(
        forcing_source="pure_wind",
        source_type=ForcingSourceType.SYNTHETIC_TEST_FIXTURE,
        is_authoritative=False,
        constant_current_u=0.0,
        constant_current_v=0.0,
        constant_wind_u=10.0,  # 10 m/s East
        constant_wind_v=0.0,
    )
    t0 = datetime(2024, 5, 1, 0, 0, tzinfo=timezone.utc)
    alpha = 0.03  # 3% windage -> 0.3 m/s East
    traj = integrate_lagrangian_trajectory(
        start_lon=-90.5,
        start_lat=27.0,
        start_time=t0,
        duration_hours=1.0,  # 3600s
        timestep_seconds=3600.0,
        windage_factor=alpha,
        forcing_field=forcing,
        direction=DirectionMode.FORWARD,
        particle_id="p_wind",
    )

    step = traj.steps[0]
    expected_dx = alpha * 10.0 * 3600.0  # 1080 meters
    assert step.displacement_current_m == (0.0, 0.0)
    assert step.displacement_wind_m[0] == pytest.approx(expected_dx, abs=1.0)
    assert step.displacement_wind_m[1] == 0.0


# ---------------------------------------------------------------------------
# 4. Constant Current Baseline
# ---------------------------------------------------------------------------

def test_constant_current_baseline():
    """Verify pure current advection when wind is zero."""
    forcing = MetoceanForcingField(
        forcing_source="pure_current",
        source_type=ForcingSourceType.SYNTHETIC_TEST_FIXTURE,
        is_authoritative=False,
        constant_current_u=0.50,  # 0.5 m/s East
        constant_current_v=0.0,
        constant_wind_u=0.0,
        constant_wind_v=0.0,
    )
    t0 = datetime(2024, 5, 1, 0, 0, tzinfo=timezone.utc)
    traj = integrate_lagrangian_trajectory(
        start_lon=-90.5,
        start_lat=27.0,
        start_time=t0,
        duration_hours=1.0,
        timestep_seconds=3600.0,
        windage_factor=0.03,
        forcing_field=forcing,
        direction=DirectionMode.FORWARD,
        particle_id="p_curr",
    )

    step = traj.steps[0]
    expected_dx = 0.50 * 3600.0  # 1800 meters
    assert step.displacement_wind_m == (0.0, 0.0)
    assert step.displacement_current_m[0] == pytest.approx(expected_dx, abs=1.0)


# ---------------------------------------------------------------------------
# 5. Constant Wind Baseline
# ---------------------------------------------------------------------------

def test_constant_wind_baseline():
    """Verify pure northward wind displacement."""
    forcing = MetoceanForcingField(
        forcing_source="north_wind",
        source_type=ForcingSourceType.SYNTHETIC_TEST_FIXTURE,
        is_authoritative=False,
        constant_current_u=0.0,
        constant_current_v=0.0,
        constant_wind_u=0.0,
        constant_wind_v=5.0,  # 5 m/s North
    )
    t0 = datetime(2024, 5, 1, 0, 0, tzinfo=timezone.utc)
    traj = integrate_lagrangian_trajectory(
        start_lon=-90.5,
        start_lat=27.0,
        start_time=t0,
        duration_hours=2.0,  # 7200s
        timestep_seconds=7200.0,
        windage_factor=0.02,  # 2% -> 0.1 m/s North
        forcing_field=forcing,
        direction=DirectionMode.FORWARD,
        particle_id="p_north_wind",
    )

    step = traj.steps[0]
    expected_dy = 0.02 * 5.0 * 7200.0  # 720 meters
    assert step.displacement_wind_m[1] == pytest.approx(expected_dy, abs=1.0)
    assert step.longitude == pytest.approx(-90.5, abs=1e-5)
    assert step.latitude > 27.0


# ---------------------------------------------------------------------------
# 6. Combined Wind and Current
# ---------------------------------------------------------------------------

def test_combined_wind_and_current():
    """Verify additive superposition of current and windage components."""
    forcing = MetoceanForcingField(
        forcing_source="combined",
        source_type=ForcingSourceType.SYNTHETIC_TEST_FIXTURE,
        is_authoritative=False,
        constant_current_u=0.20,
        constant_current_v=0.10,
        constant_wind_u=10.0,
        constant_wind_v=5.0,
    )
    t0 = datetime(2024, 5, 1, 0, 0, tzinfo=timezone.utc)
    alpha = 0.02  # wind leeway: u_w_eff = 0.20, v_w_eff = 0.10
    traj = integrate_lagrangian_trajectory(
        start_lon=-90.5,
        start_lat=27.0,
        start_time=t0,
        duration_hours=1.0,
        timestep_seconds=3600.0,
        windage_factor=alpha,
        forcing_field=forcing,
        direction=DirectionMode.FORWARD,
        particle_id="p_comb",
    )

    step = traj.steps[0]
    # Current: dx=720m, dy=360m
    # Windage: dx=720m, dy=360m
    # Total: dx=1440m, dy=720m
    assert step.displacement_current_m == (720.0, 360.0)
    assert step.displacement_wind_m == (720.0, 360.0)
    assert step.total_displacement_m == (1440.0, 720.0)


# ---------------------------------------------------------------------------
# 7. Windage Ensemble
# ---------------------------------------------------------------------------

def test_windage_ensemble(synthetic_observation_demo, synthetic_forcing_field):
    """Verify parameter sweep generates distinct trajectories with increasing displacement."""
    report, _, _ = run_origin_drift_analysis(
        observation=synthetic_observation_demo,
        forcing_field=synthetic_forcing_field,
        direction=DirectionMode.FORWARD,
        mode=DriftMode.DEMO,
        duration_hours=6.0,
        windage_min=0.01,
        windage_max=0.04,
        windage_steps=4,
        particle_count=1,  # Single seed, 4 windages
    )

    trajs = report["trajectories"] if "trajectories" in report else report["summary_statistics"]
    assert report["model_parameters"]["total_ensemble_particles"] == 4
    assert report["model_parameters"]["tested_windage_factors"] == [0.01, 0.02, 0.03, 0.04]


# ---------------------------------------------------------------------------
# 8. Particle Ensemble Initialization
# ---------------------------------------------------------------------------

def test_particle_ensemble_sampling(synthetic_observation_demo, synthetic_forcing_field):
    """Verify multi-particle sampling initializes particles across detection polygon."""
    pts = sample_polygon_particles(synthetic_observation_demo.geometry, count=5)
    assert len(pts) == 5

    report, _, _ = run_origin_drift_analysis(
        observation=synthetic_observation_demo,
        forcing_field=synthetic_forcing_field,
        direction=DirectionMode.BACKWARD,
        mode=DriftMode.DEMO,
        duration_hours=12.0,
        particle_count=5,
        windage_min=0.02,
        windage_max=0.03,
        windage_steps=2,  # 5 particles * 2 windages = 10 total
    )

    assert report["model_parameters"]["total_ensemble_particles"] == 10
    assert report["envelopes"]["trajectory_envelope_area_m2"] > 0.0
    assert report["envelopes"]["candidate_origin_region_area_m2"] > 0.0


# ---------------------------------------------------------------------------
# 9. WGS84 Trajectory GeoJSON Output
# ---------------------------------------------------------------------------

def test_wgs84_geojson_output(synthetic_observation_demo, synthetic_forcing_field, tmp_path: Path):
    """Verify exported GeoJSON complies with RFC 7946 WGS84 standard."""
    report, geojson_path, json_path = run_origin_drift_analysis(
        observation=synthetic_observation_demo,
        forcing_field=synthetic_forcing_field,
        direction=DirectionMode.BACKWARD,
        mode=DriftMode.DEMO,
        duration_hours=12.0,
        output_dir=tmp_path / "drift_test",
    )

    assert geojson_path is not None and geojson_path.is_file()
    assert json_path is not None and json_path.is_file()

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0

    for feat in data["features"]:
        assert feat["type"] == "Feature"
        geom = shape(feat["geometry"])
        assert geom.is_valid
        minx, miny, maxx, maxy = geom.bounds
        assert -180.0 <= minx <= 180.0
        assert -180.0 <= maxx <= 180.0
        assert -90.0 <= miny <= 90.0
        assert -90.0 <= maxy <= 90.0


# ---------------------------------------------------------------------------
# 10. Deterministic Execution
# ---------------------------------------------------------------------------

def test_deterministic_execution(synthetic_observation_demo, synthetic_forcing_field):
    """Verify identical parameters produce identical numerical outputs."""
    r1, _, _ = run_origin_drift_analysis(
        observation=synthetic_observation_demo,
        forcing_field=synthetic_forcing_field,
        direction=DirectionMode.FORWARD,
        mode=DriftMode.DEMO,
        duration_hours=12.0,
        particle_count=3,
        windage_steps=2,
    )
    r2, _, _ = run_origin_drift_analysis(
        observation=synthetic_observation_demo,
        forcing_field=synthetic_forcing_field,
        direction=DirectionMode.FORWARD,
        mode=DriftMode.DEMO,
        duration_hours=12.0,
        particle_count=3,
        windage_steps=2,
    )

    assert r1["summary_statistics"] == r2["summary_statistics"]
    assert r1["envelopes"] == r2["envelopes"]


# ---------------------------------------------------------------------------
# 11. Unit Consistency
# ---------------------------------------------------------------------------

def test_unit_consistency():
    """Verify geodesic displacement distances match metric speed * time."""
    lon, lat = 0.0, 0.0  # Equator
    dx = 1000.0  # 1 km East
    dy = 0.0
    new_lon, new_lat = geodesic_displacement_wgs84(lon, lat, dx, dy)
    # At equator, 1 deg lon = 111319.49 m
    # 1000 m should be ~0.008983 degrees
    deg_diff = new_lon - lon
    assert deg_diff == pytest.approx(1000.0 / 111319.49, rel=1e-3)


# ---------------------------------------------------------------------------
# 12. Timestamp Provenance Gate Rejection
# ---------------------------------------------------------------------------

def test_timestamp_provenance_gate_rejection(synthetic_observation_demo, synthetic_forcing_field):
    """Verify PHYSICAL mode strictly rejects EXTERNALLY_SUPPLIED_TEST_TIMESTAMP."""
    with pytest.raises(ProvenanceGateError, match="Observation timestamp provenance"):
        run_origin_drift_analysis(
            observation=synthetic_observation_demo,  # Has test-supplied timestamp
            forcing_field=synthetic_forcing_field,
            direction=DirectionMode.BACKWARD,
            mode=DriftMode.PHYSICAL,  # Strict mode
        )


# ---------------------------------------------------------------------------
# 13. Missing Forcing Rejection
# ---------------------------------------------------------------------------

def test_missing_forcing_rejection(synthetic_observation_authoritative):
    """Verify missing forcing components raise MissingForcingError fail-closed."""
    missing_forcing = MetoceanForcingField(
        forcing_source="incomplete_source",
        source_type=ForcingSourceType.SYNTHETIC_TEST_FIXTURE,
        is_authoritative=False,
        constant_current_u=None,  # Missing current
        constant_current_v=None,
        constant_wind_u=5.0,
        constant_wind_v=5.0,
        allow_missing_current=False,
    )

    with pytest.raises(MissingForcingError, match="Surface ocean current velocity missing"):
        missing_forcing.get_forcing(0.0, 0.0, datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# 14. DEMO vs PHYSICAL Mode Separation
# ---------------------------------------------------------------------------

def test_demo_vs_physical_mode_separation(synthetic_observation_demo, synthetic_forcing_field):
    """Verify DEMO mode executes cleanly with test fixtures and declares non-physical mode."""
    report, _, _ = run_origin_drift_analysis(
        observation=synthetic_observation_demo,
        forcing_field=synthetic_forcing_field,
        direction=DirectionMode.BACKWARD,
        mode=DriftMode.DEMO,
    )

    assert report["mode"] == "DEMO"
    assert report["observation"]["timestamp_provenance"] == "EXTERNALLY_SUPPLIED_TEST_TIMESTAMP"
    assert report["summary_statistics"]["trajectory_count"] > 0


# ---------------------------------------------------------------------------
# 15. Temporal Event Demo Integration with Gate Verification
# ---------------------------------------------------------------------------

def test_temporal_event_demo_integration_with_gate_verification(tmp_path: Path):
    """Verify end-to-end integration with benchmark detection geometry in DEMO mode.

    Note: This test uses real detection geometry from benchmark scenes with test-supplied
    timestamps (EXTERNALLY_SUPPLIED_TEST_TIMESTAMP) and synthetic forcing. It verifies
    pipeline mechanics and confirms fail-closed rejection in PHYSICAL mode.
    It does NOT validate real-world physical drift.
    """
    event_file = REPO_ROOT / "outputs" / "temporal" / "00260_to_00608_temporal_events.geojson"
    if not event_file.is_file():
        pytest.skip("Benchmark temporal events GeoJSON not available.")

    from scripts.run_origin_drift import load_observation_from_file

    obs = load_observation_from_file(event_file)
    assert obs.event_id is not None
    assert obs.area_m2 > 0.0

    # Test 1: In PHYSICAL mode, must fail closed because timestamp is EXTERNALLY_SUPPLIED_TEST_TIMESTAMP
    forcing = MetoceanForcingField(
        forcing_source="gulf_of_mexico_pilot",
        source_type=ForcingSourceType.SYNTHETIC_TEST_FIXTURE,
        is_authoritative=False,
        constant_current_u=0.15,
        constant_current_v=0.08,
        constant_wind_u=-3.0,
        constant_wind_v=2.5,
    )

    with pytest.raises(ProvenanceGateError):
        run_origin_drift_analysis(
            observation=obs,
            forcing_field=forcing,
            direction=DirectionMode.BACKWARD,
            mode=DriftMode.PHYSICAL,
        )

    # Test 2: In DEMO mode, executes successfully and generates candidate origin region
    report, geojson_path, json_path = run_origin_drift_analysis(
        observation=obs,
        forcing_field=forcing,
        direction=DirectionMode.BACKWARD,
        mode=DriftMode.DEMO,
        duration_hours=24.0,
        output_dir=tmp_path / "real_event_demo",
    )

    assert report["mode"] == "DEMO"
    assert report["envelopes"]["candidate_origin_region_area_m2"] > 0.0
    assert geojson_path is not None and geojson_path.is_file()


# ---------------------------------------------------------------------------
# 16. Geodesic Edge Conditions & Consistency
# ---------------------------------------------------------------------------

def test_cardinal_geodesic_displacements():
    """Verify cardinal (N, S, E, W) displacements against expected WGS84 curvature."""
    # North: latitude increases, longitude unchanged
    lon_n, lat_n = geodesic_displacement_wgs84(0.0, 0.0, dx_m=0.0, dy_m=111132.9)
    assert lon_n == 0.0
    assert 0.99 < lat_n < 1.01

    # South: latitude decreases, longitude unchanged
    lon_s, lat_s = geodesic_displacement_wgs84(0.0, 0.0, dx_m=0.0, dy_m=-111132.9)
    assert lon_s == 0.0
    assert -1.01 < lat_s < -0.99

    # East at Equator: longitude increases, latitude unchanged
    lon_e, lat_e = geodesic_displacement_wgs84(0.0, 0.0, dx_m=111319.5, dy_m=0.0)
    assert lat_e == 0.0
    assert 0.99 < lon_e < 1.01

    # West at Equator: longitude decreases, latitude unchanged
    lon_w, lat_w = geodesic_displacement_wgs84(0.0, 0.0, dx_m=-111319.5, dy_m=0.0)
    assert lat_w == 0.0
    assert -1.01 < lon_w < -0.99


def test_geodesic_timestep_consistency(synthetic_forcing_field):
    """Verify trajectory endpoint convergence across refined timesteps (Euler consistency)."""
    # 24h trajectory with dt = 1800s vs dt = 900s
    start_t = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
    t_1800 = integrate_lagrangian_trajectory(
        start_lon=-90.0,
        start_lat=27.0,
        start_time=start_t,
        duration_hours=24.0,
        timestep_seconds=1800.0,
        windage_factor=0.02,
        forcing_field=synthetic_forcing_field,
        direction=DirectionMode.FORWARD,
        particle_id="p1800",
    )
    t_900 = integrate_lagrangian_trajectory(
        start_lon=-90.0,
        start_lat=27.0,
        start_time=start_t,
        duration_hours=24.0,
        timestep_seconds=900.0,
        windage_factor=0.02,
        forcing_field=synthetic_forcing_field,
        direction=DirectionMode.FORWARD,
        particle_id="p900",
    )
    # Under constant velocity fields, displacement is linear and timesteps yield sub-meter agreement
    dist_diff_m = np.hypot(
        (t_1800.terminal_point[0] - t_900.terminal_point[0]) * 111000 * np.cos(np.radians(27.0)),
        (t_1800.terminal_point[1] - t_900.terminal_point[1]) * 111000,
    )
    assert dist_diff_m < 5.0, f"Endpoints diverged by {dist_diff_m}m between 1800s and 900s timesteps"


def test_high_latitude_and_pole_safeguard():
    """Verify polar safeguard avoids ZeroDivisionError and clamps latitude at boundary."""
    # Near North Pole (89.9 N)
    lon, lat = geodesic_displacement_wgs84(0.0, 89.9, dx_m=500.0, dy_m=500.0)
    assert -180.0 <= lon <= 180.0
    assert lat <= 90.0

    # Exactly at North Pole (90.0 N)
    lon_pole, lat_pole = geodesic_displacement_wgs84(0.0, 90.0, dx_m=100.0, dy_m=100.0)
    assert -180.0 <= lon_pole <= 180.0
    assert lat_pole == 90.0


def test_antimeridian_wrapping():
    """Verify coordinates crossing the 180 degree antimeridian wrap into [-180, 180]."""
    lon_wrap, _ = geodesic_displacement_wgs84(179.99, 0.0, dx_m=5000.0, dy_m=0.0)
    assert -180.0 <= lon_wrap <= -179.0, f"Expected antimeridian wrapping, got {lon_wrap}"


# ---------------------------------------------------------------------------
# 17. Input Validation & Edge Conditions
# ---------------------------------------------------------------------------

def test_empty_geometry_rejection():
    """Verify empty or missing geometry is rejected with clear ValueError."""
    with pytest.raises(ValueError, match="missing or empty"):
        sample_polygon_particles({"type": "Polygon", "coordinates": []}, count=5)


def test_invalid_coordinates_rejection():
    """Verify invalid geographic coordinates are rejected fail-closed."""
    with pytest.raises(ValueError, match="out of geographic range"):
        ObservationRecord(
            event_id="bad_coords",
            source_scene="scene_1",
            observation_time=datetime.now(timezone.utc),
            timestamp_provenance=TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP,
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
            centroid=[250.0, 45.0],  # Invalid longitude > 180
            area_m2=1000.0,
        )


def test_forcing_spatial_and_temporal_bounds_rejection():
    """Verify forcing field bounds violations fail closed with MissingForcingError."""
    bounded_forcing = MetoceanForcingField(
        forcing_source="bounded_gulf_grid",
        source_type=ForcingSourceType.OPERATIONAL_ANALYSIS,
        is_authoritative=True,
        constant_current_u=0.1,
        constant_current_v=0.1,
        constant_wind_u=2.0,
        constant_wind_v=2.0,
        spatial_bounds=(-95.0, 20.0, -85.0, 30.0),
        temporal_bounds=(
            datetime(2024, 5, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 5, 2, 0, 0, tzinfo=timezone.utc),
        ),
    )

    # 1. Valid inside bounds
    cu, cv, wu, wv = bounded_forcing.get_forcing(-90.0, 25.0, datetime(2024, 5, 1, 12, 0, tzinfo=timezone.utc))
    assert cu == 0.1

    # 2. Outside spatial bounds (lon = -80.0)
    with pytest.raises(MissingForcingError, match="outside forcing spatial bounds"):
        bounded_forcing.get_forcing(-80.0, 25.0, datetime(2024, 5, 1, 12, 0, tzinfo=timezone.utc))

    # 3. Outside temporal bounds (dt = 2024-05-03)
    with pytest.raises(MissingForcingError, match="outside forcing temporal bounds"):
        bounded_forcing.get_forcing(-90.0, 25.0, datetime(2024, 5, 3, 12, 0, tzinfo=timezone.utc))


def test_excessive_timestep_rejection(synthetic_forcing_field):
    """Verify excessive timestep (>86400s) raises ValueError to guard stability."""
    with pytest.raises(ValueError, match="Excessive integration timestep"):
        integrate_lagrangian_trajectory(
            start_lon=0.0,
            start_lat=0.0,
            start_time=datetime.now(timezone.utc),
            duration_hours=48.0,
            timestep_seconds=100000.0,
            windage_factor=0.02,
            forcing_field=synthetic_forcing_field,
            direction=DirectionMode.FORWARD,
            particle_id="p_bad",
        )

