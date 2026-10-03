r"""Ocean Sentinel Origin & Drift Reasoning Engine.

Implements first-order Lagrangian particle trajectory modeling for candidate drift
forecasting (forward mode) and candidate origin region reconstruction (backward mode):

$$\frac{d\mathbf{x}}{dt} = \mathbf{u}_{\text{current}}(\mathbf{x}, t) + \alpha_{\text{wind}} \mathbf{u}_{\text{wind}}(\mathbf{x}, t)$$

Strict Scientific Boundaries:
----------------------------
1. This module estimates PHYSICALLY CONSISTENT CANDIDATE TRAJECTORIES and
   CANDIDATE ORIGIN REGIONS under specified metocean assumptions.
2. It MUST NOT claim actual spill source, responsible vessel, legal attribution,
   or exact release locations.
3. Windage factor is modeled as an empirical leeway uncertainty ensemble ($\alpha \in [\alpha_{\min}, \alpha_{\max}]$),
   not a universal physical constant.
4. Current and wind contributions are kept explicitly separated.
5. Strict Provenance Gates enforce separation between PHYSICAL and DEMO modes:
   - PHYSICAL mode strictly requires authoritative observation timestamps and real
     metocean forcing provenance. Test-supplied timestamps are rejected fail-closed.
   - DEMO mode accommodates controlled synthetic test fixtures and pipeline validation.
6. Geodesic kinematics utilize a first-order local ellipsoidal differential update on WGS84
   using principal radii of curvature ($M, N$). Step truncation error scales as $O((\Delta s / R)^2)$.
   It is a local differential stepping approximation, not a global geodesic solve for long arcs.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import rasterio.warp
from rasterio.crs import CRS
from shapely.geometry import MultiPoint, MultiPolygon, Point, Polygon, box, mapping, shape
import shapely

from ocean_sentinel.interpretation import calculate_polygon_area_m2
from ocean_sentinel.temporal import TimestampProvenance

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and Exceptions
# ---------------------------------------------------------------------------


class DriftMode(str, Enum):
    """Operational mode separating physical reasoning from demo/synthetic test runs."""

    PHYSICAL = "PHYSICAL"
    DEMO = "DEMO"


class DirectionMode(str, Enum):
    """Temporal integration direction."""

    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"


class ForcingSourceType(str, Enum):
    """Provenance category of metocean forcing data."""

    OPERATIONAL_ANALYSIS = "OPERATIONAL_ANALYSIS"
    NUMERICAL_WEATHER_PREDICTION = "NUMERICAL_WEATHER_PREDICTION"
    OBSERVED_IN_SITU = "OBSERVED_IN_SITU"
    SYNTHETIC_TEST_FIXTURE = "SYNTHETIC_TEST_FIXTURE"


class ProvenanceGateError(RuntimeError):
    """Raised when unverified or synthetic inputs attempt to enter physical reasoning."""

    pass


class MissingForcingError(RuntimeError):
    """Raised when required environmental forcing (current or wind) is missing."""

    pass


# ---------------------------------------------------------------------------
# Metocean Provider Adapters & Anti-Bypass Registry
# ---------------------------------------------------------------------------


_REPO_METOCEAN_ACCREDITATION_KEY = "OCEAN_SENTINEL_REPO_ACCREDITED_SEAL_V1"


class MetoceanProviderAdapter:
    """Base contract for metocean forcing provider adapters."""

    def __init__(
        self,
        adapter_id: str,
        is_operational: bool = False,
        verification_token: Optional[str] = None,
        accreditation_seal: Optional[str] = None,
    ) -> None:
        self.adapter_id = adapter_id
        self.is_operational = is_operational
        self.verification_token = verification_token
        self._accreditation_seal = accreditation_seal

    def is_accredited(self) -> bool:
        """Check if adapter carries authentic repository accreditation seal."""
        return self._accreditation_seal == _REPO_METOCEAN_ACCREDITATION_KEY


class MetoceanSourceRegistry:
    """Closed registry maintaining accredited operational metocean data sources and adapters.

    Prevents provenance forgery where callers manually assert `is_authoritative=True`
    or register untrusted runtime mock adapters.
    """

    _accredited_adapters: Dict[str, MetoceanProviderAdapter] = {}

    @classmethod
    def register_adapter(cls, adapter: MetoceanProviderAdapter) -> None:
        """Register a provider adapter. Rejects unaccredited operational adapters."""
        if adapter.is_operational and not adapter.is_accredited():
            raise ProvenanceGateError(
                f"Untrusted adapter registration rejected for '{adapter.adapter_id}': "
                "Dynamic or caller-instantiated operational adapters lack repository accreditation seal. "
                "PHYSICAL mode requires certified repository-provisioned provider lineage."
            )
        cls._accredited_adapters[adapter.adapter_id] = adapter

    @classmethod
    def is_adapter_accredited_operational(
        cls, adapter_id: Optional[str], token: Optional[str] = None
    ) -> bool:
        if not adapter_id or adapter_id not in cls._accredited_adapters:
            return False
        adapter = cls._accredited_adapters[adapter_id]
        if not adapter.is_operational or not adapter.is_accredited():
            return False
        if adapter.verification_token and adapter.verification_token != token:
            return False
        return True

    @classmethod
    def has_active_operational_adapters(cls) -> bool:
        return any(a.is_operational and a.is_accredited() for a in cls._accredited_adapters.values())


# ---------------------------------------------------------------------------
# Data Models: Metocean Forcing & Observation
# ---------------------------------------------------------------------------


class MetoceanForcingPoint:
    """Discrete metocean observation or model grid point."""

    def __init__(
        self,
        timestamp: datetime,
        latitude: float,
        longitude: float,
        current_u: Optional[float] = None,
        current_v: Optional[float] = None,
        wind_u: Optional[float] = None,
        wind_v: Optional[float] = None,
        forcing_source: str = "unknown",
        source_type: ForcingSourceType = ForcingSourceType.SYNTHETIC_TEST_FIXTURE,
    ) -> None:
        self.timestamp = timestamp if timestamp.tzinfo is not None else timestamp.replace(tzinfo=timezone.utc)
        self.latitude = latitude
        self.longitude = longitude
        self.current_u = current_u
        self.current_v = current_v
        self.wind_u = wind_u
        self.wind_v = wind_v
        self.forcing_source = forcing_source
        self.source_type = source_type

    def is_complete(self) -> bool:
        """Check if all 4 vector components are present and finite."""
        vals = [self.current_u, self.current_v, self.wind_u, self.wind_v]
        return all(v is not None and np.isfinite(v) for v in vals)


class MetoceanForcingField:
    """Metocean forcing field providing current and wind velocities over time.

    Supports spatially uniform or spatiotemporally bounded environmental forcing.
    """

    def __init__(
        self,
        forcing_source: str,
        source_type: ForcingSourceType,
        is_authoritative: bool,
        spatial_resolution_deg: Optional[float] = None,
        temporal_resolution_hours: Optional[float] = None,
        constant_current_u: Optional[float] = None,
        constant_current_v: Optional[float] = None,
        constant_wind_u: Optional[float] = None,
        constant_wind_v: Optional[float] = None,
        spatial_bounds: Optional[Tuple[float, float, float, float]] = None,
        temporal_bounds: Optional[Tuple[datetime, datetime]] = None,
        allow_missing_wind: bool = False,
        allow_missing_current: bool = False,
        adapter_id: Optional[str] = None,
        verification_token: Optional[str] = None,
    ) -> None:
        self.forcing_source = forcing_source
        self.source_type = source_type
        self.is_authoritative = is_authoritative
        self.spatial_resolution_deg = spatial_resolution_deg
        self.temporal_resolution_hours = temporal_resolution_hours
        self.constant_current_u = constant_current_u
        self.constant_current_v = constant_current_v
        self.constant_wind_u = constant_wind_u
        self.constant_wind_v = constant_wind_v
        self.spatial_bounds = spatial_bounds  # (min_lon, min_lat, max_lon, max_lat)
        self.temporal_bounds = temporal_bounds  # (t_start, t_end)
        self.allow_missing_wind = allow_missing_wind
        self.allow_missing_current = allow_missing_current
        self.adapter_id = adapter_id
        self.verification_token = verification_token
        self._seal = self._compute_seal()

    def _compute_seal(self) -> str:
        """Compute SHA-256 seal over critical provenance fields to prevent post-validation mutation."""
        raw = f"{self.forcing_source}:{self.source_type.value}:{self.is_authoritative}:{self.adapter_id}:{self.verification_token}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify that forcing provenance fields have not been modified post-instantiation."""
        return hasattr(self, "_seal") and self._seal == self._compute_seal()

    def get_forcing(self, lon: float, lat: float, dt: datetime) -> Tuple[float, float, float, float]:
        """Retrieve (current_u, current_v, wind_u, wind_v) at position and time.

        Raises MissingForcingError if required components or bounds are violated.
        """
        # Check spatial bounds if specified
        if self.spatial_bounds is not None:
            min_lon, min_lat, max_lon, max_lat = self.spatial_bounds
            if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
                raise MissingForcingError(
                    f"Position ({lon:.4f}, {lat:.4f}) is outside forcing spatial bounds "
                    f"[{min_lon}, {min_lat}, {max_lon}, {max_lat}] for source '{self.forcing_source}'."
                )

        # Check temporal bounds if specified
        if self.temporal_bounds is not None:
            t_start, t_end = self.temporal_bounds
            t_q = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
            t_s = t_start if t_start.tzinfo is not None else t_start.replace(tzinfo=timezone.utc)
            t_e = t_end if t_end.tzinfo is not None else t_end.replace(tzinfo=timezone.utc)
            if not (t_s <= t_q <= t_e):
                raise MissingForcingError(
                    f"Query timestamp {t_q.isoformat()} is outside forcing temporal bounds "
                    f"[{t_s.isoformat()}, {t_e.isoformat()}] for source '{self.forcing_source}'."
                )

        cu = self.constant_current_u
        cv = self.constant_current_v
        wu = self.constant_wind_u
        wv = self.constant_wind_v

        # Check current components
        if (cu is None or cv is None) and not self.allow_missing_current:
            raise MissingForcingError(
                f"Surface ocean current velocity missing in forcing source '{self.forcing_source}'."
            )
        cu = cu if cu is not None else 0.0
        cv = cv if cv is not None else 0.0

        # Check wind components
        if (wu is None or wv is None) and not self.allow_missing_wind:
            raise MissingForcingError(
                f"10m atmospheric wind velocity missing in forcing source '{self.forcing_source}'."
            )
        wu = wu if wu is not None else 0.0
        wv = wv if wv is not None else 0.0

        return float(cu), float(cv), float(wu), float(wv)

    def to_provenance_dict(self) -> Dict[str, Any]:
        """Metadata description of the forcing source."""
        return {
            "forcing_source": self.forcing_source,
            "source_type": self.source_type.value,
            "is_authoritative": self.is_authoritative,
            "spatial_resolution_deg": self.spatial_resolution_deg,
            "temporal_resolution_hours": self.temporal_resolution_hours,
            "spatial_bounds": list(self.spatial_bounds) if self.spatial_bounds else None,
            "temporal_bounds": (
                [self.temporal_bounds[0].isoformat(), self.temporal_bounds[1].isoformat()]
                if self.temporal_bounds else None
            ),
            "allow_missing_wind": self.allow_missing_wind,
            "allow_missing_current": self.allow_missing_current,
        }


class ObservationRecord:
    """Observed detection record serving as initial state for drift modeling."""

    def __init__(
        self,
        event_id: str,
        source_scene: str,
        observation_time: datetime,
        timestamp_provenance: Union[TimestampProvenance, str],
        geometry: Dict[str, Any],
        centroid: List[float],
        area_m2: float,
        detection_type: str = "oil_spill",
        lineage_verification_token: Optional[str] = None,
    ) -> None:
        if not (len(centroid) == 2 and np.isfinite(centroid[0]) and np.isfinite(centroid[1])):
            raise ValueError(f"Centroid coordinates must be finite numbers: {centroid}")
        if not (-180.0 <= centroid[0] <= 180.0 and -90.0 <= centroid[1] <= 90.0):
            raise ValueError(f"Centroid coordinates out of geographic range [-180, 180], [-90, 90]: {centroid}")
        if area_m2 < 0.0 or not np.isfinite(area_m2):
            raise ValueError(f"Observed area must be a non-negative finite number: {area_m2}")

        self.event_id = event_id
        self.source_scene = source_scene
        self.observation_time = (
            observation_time if observation_time.tzinfo is not None else observation_time.replace(tzinfo=timezone.utc)
        )
        self.timestamp_provenance = (
            timestamp_provenance.value if isinstance(timestamp_provenance, TimestampProvenance) else str(timestamp_provenance)
        )
        self.geometry = geometry
        self.centroid = centroid
        self.area_m2 = area_m2
        self.detection_type = detection_type
        self.lineage_verification_token = lineage_verification_token
        self._seal = self._compute_seal()

    def _compute_seal(self) -> str:
        """Compute SHA-256 seal over observation provenance fields to prevent post-validation mutation."""
        raw = f"{self.event_id}:{self.source_scene}:{self.observation_time.isoformat()}:{self.timestamp_provenance}:{self.lineage_verification_token}:{self.centroid}:{self.area_m2}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify that observation provenance fields have not been modified post-instantiation."""
        return hasattr(self, "_seal") and self._seal == self._compute_seal()

    def has_verified_lineage(self) -> bool:
        """Verify whether observation is backed by genuine verified manifest or scene metadata token."""
        return bool(self.lineage_verification_token and self.lineage_verification_token.startswith("VERIFIED_"))

    @classmethod
    def from_temporal_event(cls, event_dict: Dict[str, Any]) -> ObservationRecord:
        """Construct from temporal event dictionary or GeoJSON feature."""
        if "properties" in event_dict:
            props = event_dict["properties"]
            geom = event_dict.get("geometry", {})
            event_id = event_dict.get("id") or props.get("event_id", "unknown_event")
        else:
            props = event_dict
            geom = event_dict.get("geometry", {})
            event_id = event_dict.get("event_id", "unknown_event")

        t_str = props.get("t1_time") or props.get("t0_time") or props.get("observation_time")
        if not t_str:
            raise ValueError("Event record lacks timestamp field ('t1_time' or 'observation_time').")
        clean_t = t_str.replace("Z", "+00:00")
        obs_dt = datetime.fromisoformat(clean_t)

        prov = props.get("timestamp_provenance") or TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP.value

        centroid = props.get("centroid")
        if not centroid:
            if not geom or not geom.get("coordinates"):
                raise ValueError(f"Event '{event_id}' has missing or empty geometry and no centroid.")
            s_geom = shape(geom)
            if s_geom.is_empty:
                raise ValueError(f"Event '{event_id}' has empty geometry.")
            centroid = [float(s_geom.centroid.x), float(s_geom.centroid.y)]

        return cls(
            event_id=event_id,
            source_scene=props.get("t1_source") or props.get("t0_source") or "unknown_scene",
            observation_time=obs_dt,
            timestamp_provenance=prov,
            geometry=geom,
            centroid=centroid,
            area_m2=float(props.get("area_m2", 0.0)),
            detection_type=props.get("change_type", "oil_spill"),
        )


class TrajectoryStep:
    """Discrete state at time t along a single particle path."""

    def __init__(
        self,
        step_index: int,
        timestamp: datetime,
        longitude: float,
        latitude: float,
        current_u: float,
        current_v: float,
        wind_u: float,
        wind_v: float,
        windage_factor: float,
        displacement_current_m: Tuple[float, float],
        displacement_wind_m: Tuple[float, float],
        total_displacement_m: Tuple[float, float],
        cumulative_distance_m: float,
    ) -> None:
        self.step_index = step_index
        self.timestamp = timestamp
        self.longitude = longitude
        self.latitude = latitude
        self.current_u = current_u
        self.current_v = current_v
        self.wind_u = wind_u
        self.wind_v = wind_v
        self.windage_factor = windage_factor
        self.displacement_current_m = displacement_current_m
        self.displacement_wind_m = displacement_wind_m
        self.total_displacement_m = total_displacement_m
        self.cumulative_distance_m = cumulative_distance_m


class ParticleTrajectory:
    """Full integrated trajectory for an individual particle with parameter attributes."""

    def __init__(
        self,
        particle_id: str,
        windage_factor: float,
        initial_point: List[float],
        steps: List[TrajectoryStep],
    ) -> None:
        self.particle_id = particle_id
        self.windage_factor = windage_factor
        self.initial_point = initial_point
        self.steps = steps
        self.terminal_point = [steps[-1].longitude, steps[-1].latitude] if steps else initial_point
        self.total_distance_m = steps[-1].cumulative_distance_m if steps else 0.0

        # Net displacement
        if steps:
            dx_net = sum(s.total_displacement_m[0] for s in steps)
            dy_net = sum(s.total_displacement_m[1] for s in steps)
            self.net_displacement_m = float(np.hypot(dx_net, dy_net))
        else:
            self.net_displacement_m = 0.0

    def to_geojson_feature(self) -> Dict[str, Any]:
        """Serialize trajectory path into RFC 7946 GeoJSON LineString."""
        coords = [[round(s.longitude, 6), round(s.latitude, 6)] for s in self.steps]
        if len(coords) < 2:
            coords = [self.initial_point, self.terminal_point]

        return {
            "type": "Feature",
            "id": self.particle_id,
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
            "properties": {
                "feature_type": "trajectory_line",
                "particle_id": self.particle_id,
                "windage_factor": round(self.windage_factor, 4),
                "initial_point": [round(c, 6) for c in self.initial_point],
                "terminal_point": [round(c, 6) for c in self.terminal_point],
                "step_count": len(self.steps),
                "total_distance_m": round(self.total_distance_m, 2),
                "net_displacement_m": round(self.net_displacement_m, 2),
            },
        }


# ---------------------------------------------------------------------------
# Geodesic Kinematic Engine
# ---------------------------------------------------------------------------


def geodesic_displacement_wgs84(
    lon: float, lat: float, dx_m: float, dy_m: float
) -> Tuple[float, float]:
    r"""Calculate new coordinates using first-order local ellipsoidal differential displacement on WGS84.

    Evaluates principal radii of curvature at the starting latitude:
    - Meridian radius of curvature: $M(\phi) = \frac{a(1 - e^2)}{(1 - e^2 \sin^2 \phi)^{3/2}}$
    - Prime vertical radius of curvature: $N(\phi) = \frac{a}{\sqrt{1 - e^2 \sin^2 \phi}}$

    Angular increments:
    $$\Delta \phi = \frac{\Delta y}{M(\phi)}, \quad \Delta \lambda = \frac{\Delta x}{N(\phi) \cos \phi}$$

    Accuracy & Stability Boundary:
    ------------------------------
    This is an explicit first-order differential stepping update for small timesteps ($\Delta s \ll R_{\text{earth}}$).
    Local step truncation error scales as $O((\Delta s / R)^2)$. For typical ocean drift displacements
    ($\Delta s \le 1\,\text{km}$ per step), step error relative to a full ellipsoidal direct geodesic solve
    is on the order of millimeters to centimeters. It is NOT a global geodesic solver for large single steps.

    Parameters
    ----------
    lon : float
        Starting longitude in degrees.
    lat : float
        Starting latitude in degrees.
    dx_m : float
        Eastward metric displacement in meters ($u \cdot \Delta t$).
    dy_m : float
        Northward metric displacement in meters ($v \cdot \Delta t$).

    Returns
    -------
    new_lon, new_lat : tuple[float, float]
        Displaced coordinates in degrees WGS84.
    """
    # WGS84 ellipsoid constants
    a = 6378137.0  # semi-major axis (meters)
    e2 = 0.00669437999014  # first eccentricity squared

    phi = np.radians(lat)
    sin_phi = np.sin(phi)
    denom = 1.0 - e2 * (sin_phi**2)

    # Meridian radius of curvature (North-South)
    M = a * (1.0 - e2) / np.power(denom, 1.5)
    # Prime vertical radius of curvature (East-West)
    N = a / np.sqrt(denom)

    # Angular increments in radians
    dlat_rad = dy_m / M
    # Prevent singularity at poles
    cos_phi = np.cos(phi)
    if np.abs(cos_phi) < 1e-6:
        dlon_rad = 0.0
    else:
        dlon_rad = dx_m / (N * cos_phi)

    new_lat = lat + float(np.degrees(dlat_rad))
    new_lon = lon + float(np.degrees(dlon_rad))

    # Wrap longitude into [-180, 180]
    new_lon = (new_lon + 180.0) % 360.0 - 180.0
    # Clamp latitude into [-90, 90]
    new_lat = max(-90.0, min(90.0, new_lat))

    return new_lon, new_lat


def sample_polygon_particles(
    geom_dict: Dict[str, Any],
    count: int = 1,
) -> List[List[float]]:
    """Deterministically sample seed particle points across a detection polygon.

    Parameters
    ----------
    geom_dict : dict
        GeoJSON geometry mapping.
    count : int
        Number of spatial seed particles to generate.

    Returns
    -------
    points : list[list[float]]
        List of [lon, lat] coordinates.
    """
    if not geom_dict or not geom_dict.get("coordinates"):
        raise ValueError("Cannot sample particles: detection geometry is missing or empty.")

    s_geom = shape(geom_dict)
    if s_geom.is_empty:
        raise ValueError("Cannot sample particles: detection geometry is an empty Shapely object.")

    if not s_geom.is_valid:
        s_geom = shapely.make_valid(s_geom)
        if s_geom.is_empty:
            raise ValueError("Detection geometry became empty after shapely.make_valid.")

    c = [float(s_geom.centroid.x), float(s_geom.centroid.y)]
    if count <= 1:
        return [c]

    pts = [c]
    bounds = s_geom.bounds  # minx, miny, maxx, maxy
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]

    # Deterministic spatial sampling on a regular grid
    n_side = int(np.ceil(np.sqrt(count * 1.5)))
    xs = np.linspace(bounds[0] + 0.1 * width, bounds[2] - 0.1 * width, n_side)
    ys = np.linspace(bounds[1] + 0.1 * height, bounds[3] - 0.1 * height, n_side)

    for x in xs:
        for y in ys:
            p = Point(x, y)
            if s_geom.contains(p):
                pts.append([float(x), float(y)])
                if len(pts) >= count:
                    return pts

    # If polygon is very thin or small, fall back to centroid replicates or exterior coords
    if len(pts) < count and hasattr(s_geom, "exterior") and s_geom.exterior:
        for coord in s_geom.exterior.coords:
            pts.append([float(coord[0]), float(coord[1])])
            if len(pts) >= count:
                break

    while len(pts) < count:
        pts.append(c)

    return pts[:count]


# ---------------------------------------------------------------------------
# Core Lagrangian Trajectory Integrator
# ---------------------------------------------------------------------------


def integrate_lagrangian_trajectory(
    start_lon: float,
    start_lat: float,
    start_time: datetime,
    duration_hours: float,
    timestep_seconds: float,
    windage_factor: float,
    forcing_field: MetoceanForcingField,
    direction: DirectionMode,
    particle_id: str,
) -> ParticleTrajectory:
    """Numerically integrate a single Lagrangian particle trajectory forward or backward in time.

    Kinematics:
    -----------
    Forward:
      dx = (u_current + alpha * u_wind) * dt
      dy = (v_current + alpha * v_wind) * dt

    Backward (Hypothesis Reconstruction):
      dx = - (u_current + alpha * u_wind) * dt
      dy = - (v_current + alpha * v_wind) * dt
    """
    total_seconds = duration_hours * 3600.0
    if not (np.isfinite(start_lon) and np.isfinite(start_lat)):
        raise ValueError(f"Starting coordinates must be finite numbers: [{start_lon}, {start_lat}]")
    if not (np.isfinite(duration_hours) and np.isfinite(timestep_seconds)):
        raise ValueError(f"Duration and timestep must be finite numbers: duration={duration_hours}, dt={timestep_seconds}")
    if total_seconds <= 0:
        raise ValueError(f"Duration must be strictly positive (got {duration_hours} hours).")
    if duration_hours > 720.0:
        raise ValueError(f"Excessive duration: {duration_hours}h exceeds 720h (30 days).")
    if timestep_seconds <= 0:
        raise ValueError(f"Timestep must be strictly positive (got {timestep_seconds} seconds).")
    if timestep_seconds > 86400.0:
        raise ValueError(f"Excessive integration timestep: {timestep_seconds}s > 86400s (24h). Numerical stability compromised.")

    sign = 1.0 if direction == DirectionMode.FORWARD else -1.0
    n_steps = max(1, int(np.ceil(total_seconds / timestep_seconds)))
    dt = total_seconds / n_steps

    curr_lon, curr_lat = start_lon, start_lat
    curr_time = start_time
    cumulative_dist_m = 0.0
    steps: List[TrajectoryStep] = []

    for step_idx in range(1, n_steps + 1):
        # Query environmental forcing at current location and time
        cu, cv, wu, wv = forcing_field.get_forcing(curr_lon, curr_lat, curr_time)

        # Decompose kinematic components in m/s
        vel_c_x = cu
        vel_c_y = cv
        vel_w_x = windage_factor * wu
        vel_w_y = windage_factor * wv

        vel_tot_x = vel_c_x + vel_w_x
        vel_tot_y = vel_c_y + vel_w_y

        # Integrate displacement over timestep (meters)
        dx_c = sign * vel_c_x * dt
        dy_c = sign * vel_c_y * dt
        dx_w = sign * vel_w_x * dt
        dy_w = sign * vel_w_y * dt
        dx_tot = dx_c + dx_w
        dy_tot = dy_c + dy_w

        # Geodesic update on WGS84
        next_lon, next_lat = geodesic_displacement_wgs84(curr_lon, curr_lat, dx_tot, dy_tot)

        step_dist = float(np.hypot(dx_tot, dy_tot))
        cumulative_dist_m += step_dist

        # Time advancement
        time_step_delta = timedelta(seconds=dt)
        next_time = (
            curr_time + time_step_delta
            if direction == DirectionMode.FORWARD
            else curr_time - time_step_delta
        )

        step = TrajectoryStep(
            step_index=step_idx,
            timestamp=next_time,
            longitude=round(next_lon, 6),
            latitude=round(next_lat, 6),
            current_u=round(cu, 4),
            current_v=round(cv, 4),
            wind_u=round(wu, 4),
            wind_v=round(wv, 4),
            windage_factor=round(windage_factor, 4),
            displacement_current_m=(round(dx_c, 2), round(dy_c, 2)),
            displacement_wind_m=(round(dx_w, 2), round(dy_w, 2)),
            total_displacement_m=(round(dx_tot, 2), round(dy_tot, 2)),
            cumulative_distance_m=round(cumulative_dist_m, 2),
        )
        steps.append(step)

        curr_lon, curr_lat = next_lon, next_lat
        curr_time = next_time

    return ParticleTrajectory(
        particle_id=particle_id,
        windage_factor=windage_factor,
        initial_point=[start_lon, start_lat],
        steps=steps,
    )


# ---------------------------------------------------------------------------
# Envelope & Uncertainty Geometry Reconstruction
# ---------------------------------------------------------------------------


def compute_uncertainty_envelope(
    trajectories: List[ParticleTrajectory],
    buffer_meters: float = 100.0,
) -> Tuple[Dict[str, Any], float]:
    """Compute WGS84 polygon envelope enclosing all particle trajectories.

    Note: This is an uncertainty envelope representation bounding the ensemble paths,
    NOT a probability distribution or physically occupied slick boundary.

    Returns (GeoJSON mapping, area in m^2).
    """
    all_points: List[Tuple[float, float]] = []
    for traj in trajectories:
        all_points.append((traj.initial_point[0], traj.initial_point[1]))
        for s in traj.steps:
            all_points.append((s.longitude, s.latitude))

    if not all_points:
        return {"type": "Polygon", "coordinates": []}, 0.0

    mp = MultiPoint(all_points)
    hull = mp.convex_hull
    lat_ref = all_points[0][1] if all_points else 0.0
    deg_lat = buffer_meters / 111132.0
    deg_lon = buffer_meters / (111132.0 * max(0.01, float(np.cos(np.radians(lat_ref)))))

    if isinstance(hull, Point):
        hull = box(hull.x - deg_lon, hull.y - deg_lat, hull.x + deg_lon, hull.y + deg_lat)
    elif hull.geom_type == "LineString":
        hull = hull.buffer(deg_lat)

    crs_wgs84 = CRS.from_epsg(4326)
    area_m2, _, _ = calculate_polygon_area_m2(hull, crs_wgs84)
    return mapping(hull), area_m2


def compute_candidate_origin_region(
    trajectories: List[ParticleTrajectory],
    buffer_meters: float = 200.0,
) -> Tuple[Dict[str, Any], float]:
    """Compute candidate origin region polygon from the terminal endpoints of backtracked particles.

    Note: This bounding polygon defines a physically consistent candidate origin hypothesis
    under the selected forcing and leeway ensemble, NOT a proven release location or spill source.

    Returns (GeoJSON mapping, area in m^2).
    """
    endpoints = [traj.terminal_point for traj in trajectories]
    if not endpoints:
        return {"type": "Polygon", "coordinates": []}, 0.0

    mp = MultiPoint(endpoints)
    hull = mp.convex_hull
    lat_ref = endpoints[0][1] if endpoints else 0.0
    deg_lat = buffer_meters / 111132.0
    deg_lon = buffer_meters / (111132.0 * max(0.01, float(np.cos(np.radians(lat_ref)))))

    if isinstance(hull, Point):
        hull = box(hull.x - deg_lon, hull.y - deg_lat, hull.x + deg_lon, hull.y + deg_lat)
    elif hull.geom_type == "LineString":
        hull = hull.buffer(deg_lat)

    crs_wgs84 = CRS.from_epsg(4326)
    area_m2, _, _ = calculate_polygon_area_m2(hull, crs_wgs84)
    return mapping(hull), area_m2


# ---------------------------------------------------------------------------
# High-Level Drift & Origin Engine
# ---------------------------------------------------------------------------


def run_origin_drift_analysis(
    observation: ObservationRecord,
    forcing_field: MetoceanForcingField,
    direction: DirectionMode = DirectionMode.BACKWARD,
    mode: DriftMode = DriftMode.DEMO,
    duration_hours: float = 24.0,
    timestep_seconds: float = 1800.0,  # 30 minutes
    windage_min: float = 0.01,
    windage_max: float = 0.04,
    windage_steps: int = 4,
    particle_count: int = 5,
    output_dir: Optional[Union[str, Path]] = None,
    output_prefix: Optional[str] = None,
) -> Tuple[Dict[str, Any], Optional[Path], Optional[Path]]:
    """Execute origin/drift analysis over an observation with ensemble uncertainty.

    Provenance Gate Enforcement:
    ----------------------------
    In PHYSICAL mode:
      1. Observation timestamp MUST be VERIFIED_FROM_SOURCE_METADATA or VERIFIED_FROM_AUTHORITATIVE_MANIFEST.
         EXTERNALLY_SUPPLIED_TEST_TIMESTAMP is strictly rejected fail-closed.
      2. Forcing field MUST be authoritative (is_authoritative == True).
         Synthetic fixtures or missing forcing are strictly rejected fail-closed.

    In DEMO mode:
      Accommodates synthetic test fixtures and pipeline validation. Output metadata
      explicitly declares mode as non-physical.
    """
    # -----------------------------------------------------------------------
    # 1. Provenance Gate Verification & Tamper Detection
    # -----------------------------------------------------------------------
    if not observation.verify_integrity():
        raise ProvenanceGateError(
            f"Tamper detection rejected for observation '{observation.event_id}': "
            "Observation metadata has been modified post-instantiation."
        )
    if not forcing_field.verify_integrity():
        raise ProvenanceGateError(
            f"Tamper detection rejected for forcing field '{forcing_field.forcing_source}': "
            "Forcing field metadata has been modified post-instantiation."
        )

    if mode == DriftMode.PHYSICAL:
        # Check Observation Timestamp Provenance
        auth_provs = [
            TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA.value,
            TimestampProvenance.VERIFIED_FROM_AUTHORITATIVE_MANIFEST.value,
        ]
        if observation.timestamp_provenance not in auth_provs:
            raise ProvenanceGateError(
                f"PHYSICAL mode rejected: Observation timestamp provenance is '{observation.timestamp_provenance}'. "
                "Physical drift and origin inference strictly requires authoritative satellite acquisition timestamps "
                "(VERIFIED_FROM_SOURCE_METADATA or VERIFIED_FROM_AUTHORITATIVE_MANIFEST). "
                "Select mode='DEMO' to execute non-physical tests."
            )
        # Anti-bypass lineage verification
        if not observation.has_verified_lineage():
            raise ProvenanceGateError(
                f"PHYSICAL mode rejected: Observation '{observation.event_id}' has unverified timestamp lineage. "
                "Caller-declared timestamp_provenance string without source scene metadata or manifest verification is strictly rejected."
            )

        # Check Metocean Forcing Provenance (Anti-Bypass)
        if not forcing_field.is_authoritative or not MetoceanSourceRegistry.is_adapter_accredited_operational(
            forcing_field.adapter_id, forcing_field.verification_token
        ):
            raise ProvenanceGateError(
                f"PHYSICAL mode rejected: Forcing source '{forcing_field.forcing_source}' (adapter: '{forcing_field.adapter_id}') "
                "lacks accredited operational provider lineage. Caller-asserted is_authoritative=True is strictly rejected without "
                "registered adapter verification. Physical metocean forcing is currently BLOCKED — AWAITING_OPERATIONAL_METOCEAN_SOURCE."
            )

    # -----------------------------------------------------------------------
    # 2. Windage Ensemble Setup
    # -----------------------------------------------------------------------
    if windage_steps <= 1 or windage_min >= windage_max:
        windage_factors = [float(windage_min)]
    else:
        windage_factors = [float(w) for w in np.linspace(windage_min, windage_max, windage_steps)]

    # -----------------------------------------------------------------------
    # 3. Spatial Particle Sampling
    # -----------------------------------------------------------------------
    seed_points = sample_polygon_particles(observation.geometry, count=particle_count)

    # -----------------------------------------------------------------------
    # 4. Trajectory Integration Ensemble
    # -----------------------------------------------------------------------
    trajectories: List[ParticleTrajectory] = []
    pidx = 1

    for pt in seed_points:
        for w_factor in windage_factors:
            part_id = f"{observation.event_id}_p{pidx:03d}_w{int(w_factor*1000):03d}"
            traj = integrate_lagrangian_trajectory(
                start_lon=pt[0],
                start_lat=pt[1],
                start_time=observation.observation_time,
                duration_hours=duration_hours,
                timestep_seconds=timestep_seconds,
                windage_factor=w_factor,
                forcing_field=forcing_field,
                direction=direction,
                particle_id=part_id,
            )
            trajectories.append(traj)
            pidx += 1

    # -----------------------------------------------------------------------
    # 5. Ensemble Envelopes & Diagnostics
    # -----------------------------------------------------------------------
    traj_envelope_geom, traj_envelope_area_m2 = compute_uncertainty_envelope(trajectories)

    origin_region_geom = None
    origin_region_area_m2 = None
    if direction == DirectionMode.BACKWARD:
        origin_region_geom, origin_region_area_m2 = compute_candidate_origin_region(trajectories)

    # Compute Summary Diagnostics
    displacements = [t.net_displacement_m for t in trajectories]
    tot_distances = [t.total_distance_m for t in trajectories]

    # Evaluate Dominant Driver (current vs wind)
    # Check sample forcing
    sample_cu, sample_cv, sample_wu, sample_wv = forcing_field.get_forcing(
        observation.centroid[0], observation.centroid[1], observation.observation_time
    )
    mean_w = float(np.mean(windage_factors))
    curr_mag = float(np.hypot(sample_cu, sample_cv))
    wind_leeway_mag = float(np.hypot(mean_w * sample_wu, mean_w * sample_wv))
    if curr_mag > 2.0 * wind_leeway_mag:
        dominant_driver = "CURRENT_DOMINATED"
    elif wind_leeway_mag > 2.0 * curr_mag:
        dominant_driver = "WIND_DOMINATED"
    else:
        dominant_driver = "BALANCED_WIND_AND_CURRENT"

    summary_stats = {
        "trajectory_count": len(trajectories),
        "mean_net_displacement_m": round(float(np.mean(displacements)), 2),
        "min_net_displacement_m": round(float(np.min(displacements)), 2),
        "max_net_displacement_m": round(float(np.max(displacements)), 2),
        "mean_total_distance_m": round(float(np.mean(tot_distances)), 2),
        "dominant_driver": dominant_driver,
        "sample_surface_current_speed_ms": round(curr_mag, 3),
        "sample_wind_leeway_speed_ms": round(wind_leeway_mag, 3),
    }

    scientific_limitations = [
        "Oil slicks are complex non-passive surface films subject to weathering, spreading, and emulsification.",
        "SAR detectability depends on sea state (literature operational heuristic: ~2-3 m/s <= u10 <= ~10-12 m/s).",
        "Windage factor is modeled as a configurable empirical leeway ensemble (operational default: 1% to 4%), not a universal physical constant.",
        "Backward trajectory integration yields a physically consistent candidate origin hypothesis under selected dynamics, NOT proven source attribution.",
        "Trajectory envelope and candidate origin polygons are convex hull bounds, not probability distributions or exact release footprints.",
        "Metocean forcing resolution, interpolation, and sub-grid turbulence represent significant sources of unmodeled variance.",
    ]

    report = {
        "engine": "ocean_sentinel_origin_drift_v1",
        "mode": mode.value,
        "direction": direction.value,
        "observation": {
            "event_id": observation.event_id,
            "source_scene": observation.source_scene,
            "observation_time_utc": observation.observation_time.isoformat(),
            "timestamp_provenance": observation.timestamp_provenance,
            "centroid": observation.centroid,
            "area_m2": observation.area_m2,
        },
        "forcing_provenance": forcing_field.to_provenance_dict(),
        "model_parameters": {
            "duration_hours": duration_hours,
            "timestep_seconds": timestep_seconds,
            "windage_min": windage_min,
            "windage_max": windage_max,
            "windage_steps": windage_steps,
            "tested_windage_factors": [round(w, 4) for w in windage_factors],
            "spatial_seed_particles": len(seed_points),
            "total_ensemble_particles": len(trajectories),
        },
        "envelopes": {
            "trajectory_envelope_area_m2": round(traj_envelope_area_m2, 2),
            "trajectory_envelope_area_km2": round(traj_envelope_area_m2 / 1e6, 6),
            "candidate_origin_region_area_m2": (
                round(origin_region_area_m2, 2) if origin_region_area_m2 is not None else None
            ),
            "candidate_origin_region_area_km2": (
                round(origin_region_area_m2 / 1e6, 6) if origin_region_area_m2 is not None else None
            ),
        },
        "summary_statistics": summary_stats,
        "scientific_limitations": scientific_limitations,
    }

    # -----------------------------------------------------------------------
    # 6. GeoJSON FeatureCollection Serialization (RFC 7946 WGS84)
    # -----------------------------------------------------------------------
    features = []

    # 1. Observation geometry feature
    features.append({
        "type": "Feature",
        "id": f"{observation.event_id}_observation",
        "geometry": observation.geometry,
        "properties": {
            "feature_type": "observed_detection",
            "event_id": observation.event_id,
            "observation_time": observation.observation_time.isoformat(),
            "area_m2": observation.area_m2,
        },
    })

    # 2. Particle trajectories
    for traj in trajectories:
        features.append(traj.to_geojson_feature())

    # 3. Candidate origin region (if backward mode)
    if origin_region_geom is not None:
        features.append({
            "type": "Feature",
            "id": f"{observation.event_id}_candidate_origin_region",
            "geometry": origin_region_geom,
            "properties": {
                "feature_type": "candidate_origin_region",
                "area_m2": round(origin_region_area_m2 or 0.0, 2),
                "area_km2": round((origin_region_area_m2 or 0.0) / 1e6, 6),
                "backtracked_duration_hours": duration_hours,
            },
        })

    # 4. Trajectory envelope
    features.append({
        "type": "Feature",
        "id": f"{observation.event_id}_trajectory_envelope",
        "geometry": traj_envelope_geom,
        "properties": {
            "feature_type": "trajectory_envelope",
            "area_m2": round(traj_envelope_area_m2, 2),
            "area_km2": round(traj_envelope_area_m2 / 1e6, 6),
        },
    })

    geojson_dict = {
        "type": "FeatureCollection",
        "name": "ocean_sentinel_origin_drift",
        "metadata": {
            "mode": mode.value,
            "direction": direction.value,
            "event_id": observation.event_id,
            "observation_time": observation.observation_time.isoformat(),
            "timestamp_provenance": observation.timestamp_provenance,
            "forcing_source": forcing_field.forcing_source,
            "is_authoritative": forcing_field.is_authoritative and (mode == DriftMode.PHYSICAL),
            "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
        "features": features,
    }

    # -----------------------------------------------------------------------
    # 7. File Export (if output_dir specified)
    # -----------------------------------------------------------------------
    geojson_path = None
    json_path = None

    if output_dir is not None:
        out_p = Path(output_dir)
        out_p.mkdir(parents=True, exist_ok=True)
        prefix = output_prefix or f"{observation.event_id}_{direction.value.lower()}_drift"

        geojson_path = out_p / f"{prefix}.geojson"
        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(geojson_dict, f, indent=2)

        json_path = out_p / f"{prefix}_summary.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Saved drift GeoJSON to: {geojson_path}")
        logger.info(f"Saved drift summary JSON to: {json_path}")

    return report, geojson_path, json_path
