r"""Ocean Sentinel AIS Spatio-Temporal Correlation Engine V1.

Correlates time-indexed candidate drift trajectories and candidate origin hypotheses
against historical/operational vessel Automatic Identification System (AIS) tracks.

Scientific & Legal Boundaries:
------------------------------
1. This module evaluates SPATIO-TEMPORAL EVIDENCE COMPATIBILITY between vessel tracks
   and candidate origin hypotheses.
2. It MUST NOT claim proven spill source, responsible vessel, legal culpability,
   or causality.
3. The composite metric is named `evidence_compatibility_score`. It is an uncalibrated
   heuristic ranking metric, NOT a calibrated attribution probability.
4. AIS absence MUST NOT be interpreted as vessel absence (accounting for receiver gaps,
   satellite revisit limits, and transponder-off periods).
5. Vessel course (COG) is NOT required to match oil drift direction, as vessel navigation
   and environmental surface transport represent distinct physical quantities.
6. Provenance Gates:
   - PHYSICAL mode requires verified operational/archive AIS feeds with complete
     provenance and quality certification. Synthetic fixtures are rejected fail-closed.
   - DEMO mode accommodates controlled synthetic fixtures for verification.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from shapely.geometry import LineString, MultiPoint, MultiPolygon, Point, Polygon, box, mapping, shape
from shapely.strtree import STRtree
import shapely

from ocean_sentinel.drift import (
    DirectionMode,
    DriftMode,
    ParticleTrajectory,
    ProvenanceGateError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums, Weights & Exceptions
# ---------------------------------------------------------------------------


class AISProvenance(str, Enum):
    """Provenance category of AIS vessel tracking data."""

    VERIFIED_OPERATIONAL_FEED = "VERIFIED_OPERATIONAL_FEED"
    HISTORICAL_ARCHIVE = "HISTORICAL_ARCHIVE"
    SYNTHETIC_DEMO_FEED = "SYNTHETIC_DEMO_FEED"


class AISCorrelationMode(str, Enum):
    """Operational mode separating physical inference from demo/synthetic test runs."""

    PHYSICAL = "PHYSICAL"
    DEMO = "DEMO"


class NavigationStatus(str, Enum):
    """Standard maritime AIS navigation status categories."""

    UNDERWAY_USING_ENGINE = "UNDERWAY_USING_ENGINE"
    AT_ANCHOR = "AT_ANCHOR"
    NOT_UNDER_COMMAND = "NOT_UNDER_COMMAND"
    RESTRICTED_MANOEUVRABILITY = "RESTRICTED_MANOEUVRABILITY"
    CONSTRAINED_BY_DRAUGHT = "CONSTRAINED_BY_DRAUGHT"
    MOORED = "MOORED"
    AGROUND = "AGROUND"
    ENGAGED_IN_FISHING = "ENGAGED_IN_FISHING"
    UNDERWAY_SAILING = "UNDERWAY_SAILING"
    UNKNOWN = "UNKNOWN"


class TrackQualityClass(str, Enum):
    """Quality classification of a vessel track after cleaning and validation."""

    EXCELLENT = "EXCELLENT"      # 0 rejected records, no speed jumps, max gap <= tau_max
    DEGRADED = "DEGRADED"        # isolated outliers or gaps, but retains >= 2 valid points and >= 50% data
    UNUSABLE = "UNUSABLE"        # < 2 valid points retained, or < 50% data retained, or non-monotonic


class VesselCoverageStatus(str, Enum):
    """Vessel observational coverage status relative to candidate origin / drift window."""

    OBSERVED_IN_WINDOW = "OBSERVED_IN_WINDOW"                     # Observed during active drift window
    TELEMETRY_GAP_ACROSS_WINDOW = "TELEMETRY_GAP_ACROSS_WINDOW"   # Tracking gap > tau_max spans event window
    OUTSIDE_WINDOW = "OUTSIDE_WINDOW"                             # Track exists strictly before or after window
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"                       # Track unusable due to low point count


@dataclass(frozen=True)
class CompatibilityScoreWeights:
    """Configurable weights for the uncalibrated evidence compatibility ranking score.

    Notice: These weights define an operational engineering heuristic, NOT a scientifically
    calibrated attribution probability. Versioned for auditability.
    """

    weight_trajectory_spatial: float = 0.40
    weight_temporal_proximity: float = 0.30
    weight_origin_endpoint: float = 0.15
    weight_origin_polygon: float = 0.15
    quality_floor: float = 0.80
    quality_scale: float = 0.20
    version: str = "1.1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "weight_trajectory_spatial": self.weight_trajectory_spatial,
            "weight_temporal_proximity": self.weight_temporal_proximity,
            "weight_origin_endpoint": self.weight_origin_endpoint,
            "weight_origin_polygon": self.weight_origin_polygon,
            "quality_floor": self.quality_floor,
            "quality_scale": self.quality_scale,
            "version": self.version,
        }


class AISError(Exception):
    """Base exception for AIS correlation errors."""
    pass


class AISQualityError(AISError):
    """Raised when AIS track quality falls below operational thresholds."""
    pass


# ---------------------------------------------------------------------------
# AIS Provider Adapter Contract & Anti-Bypass Registry
# ---------------------------------------------------------------------------


_REPO_AIS_ACCREDITATION_KEY = "OCEAN_SENTINEL_REPO_ACCREDITED_AIS_SEAL_V1"


class AISProviderAdapter:
    """Base contract for AIS feed ingestion adapters."""

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
        return self._accreditation_seal == _REPO_AIS_ACCREDITATION_KEY


class AISSourceRegistry:
    """Closed registry maintaining accredited operational AIS data providers and adapters.

    Prevents provenance forgery where callers manually assert `provenance=VERIFIED_OPERATIONAL_FEED`
    or register untrusted runtime mock adapters.
    """

    _accredited_adapters: Dict[str, AISProviderAdapter] = {}

    @classmethod
    def register_adapter(cls, adapter: AISProviderAdapter) -> None:
        """Register an AIS provider adapter. Rejects unaccredited operational adapters."""
        if adapter.is_operational and not adapter.is_accredited():
            raise ProvenanceGateError(
                f"Untrusted AIS adapter registration rejected for '{adapter.adapter_id}': "
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
# Geodesic & Spatial Helper Functions
# ---------------------------------------------------------------------------


def haversine_distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate spherical great-circle distance between two coordinates in meters.

    Numerical Method:
    -----------------
    Uses the classical spherical Haversine formula on a mean spherical Earth of radius
    R = 6,371,008.8 m (IUGG recommended mean Earth radius).

    Scientific Boundary & Accuracy Notice:
    --------------------------------------
    This is a SPHERICAL great-circle distance, NOT an ellipsoidal WGS84 geodesic.
    While highly efficient and accurate to within ~0.3% - 0.5% globally (sufficient
    for spatio-temporal correlation and spatial filtering), it does not account for
    ellipsoidal flattening. Documented honestly as spherical Haversine distance.
    """
    R = 6371008.8  # Earth mean radius in meters
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)

    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(max(0.0, 1.0 - a)))
    return float(R * c)


def interpolate_geodesic_position(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
    fraction: float,
) -> Tuple[float, float]:
    """Spherical great-circle SLERP interpolation between two geographic coordinates.

    Numerical Method:
    -----------------
    Uses 3D unit-vector Spherical Linear Interpolation (SLERP) on a unit sphere
    to trace the spherical great-circle orthodrome between (lon1, lat1) and (lon2, lat2).

    Scientific Boundary & Accuracy Notice:
    --------------------------------------
    This calculation is a SPHERICAL great-circle SLERP interpolation, NOT an ellipsoidal
    WGS84 geodesic calculation (e.g. Vincenty or Karney geodesic interpolation).
    It operates on a unit sphere and maps back to geographic coordinates.
    Correctly handles antimeridian (180/-180) crossings and polar convergence.
    Safely handles coincident endpoints and near-antipodal boundary conditions.

    Parameters
    ----------
    lon1, lat1 : float
        Starting coordinates in degrees.
    lon2, lat2 : float
        Ending coordinates in degrees.
    fraction : float
        Normalized time fraction in [0.0, 1.0].

    Returns
    -------
    lon, lat : tuple[float, float]
        Interpolated coordinates in degrees [-180, 180], [-90, 90].
    """
    if fraction <= 0.0:
        return float(lon1), float(lat1)
    if fraction >= 1.0:
        return float(lon2), float(lat2)

    # Convert coordinates to radians
    lam1, phi1 = np.radians(lon1), np.radians(lat1)
    lam2, phi2 = np.radians(lon2), np.radians(lat2)

    # Convert to 3D Cartesian unit vectors
    v1 = np.array([np.cos(phi1) * np.cos(lam1), np.cos(phi1) * np.sin(lam1), np.sin(phi1)])
    v2 = np.array([np.cos(phi2) * np.cos(lam2), np.cos(phi2) * np.sin(lam2), np.sin(phi2)])

    # Angle between vectors
    dot = float(np.clip(np.dot(v1, v2), -1.0, 1.0))
    theta = np.arccos(dot)

    if theta < 1e-9:
        # Coincident endpoints
        return float(lon1), float(lat1)

    sin_theta = np.sin(theta)
    if sin_theta < 1e-9:
        # Near-antipodal or collinear condition
        return float(lon1), float(lat1)

    # SLERP weighting
    w1 = np.sin((1.0 - fraction) * theta) / sin_theta
    w2 = np.sin(fraction * theta) / sin_theta

    v_interp = w1 * v1 + w2 * v2
    v_norm = np.linalg.norm(v_interp)
    if v_norm == 0.0:
        return float(lon1), float(lat1)
    v_interp /= v_norm

    interp_lat = float(np.degrees(np.arcsin(np.clip(v_interp[2], -1.0, 1.0))))
    interp_lon = float(np.degrees(np.arctan2(v_interp[1], v_interp[0])))

    # Wrap longitude to [-180, 180]
    interp_lon = (interp_lon + 180.0) % 360.0 - 180.0
    interp_lat = max(-90.0, min(90.0, interp_lat))

    return interp_lon, interp_lat


# ---------------------------------------------------------------------------
# Data Models: AIS Record & Vessel Track
# ---------------------------------------------------------------------------


class AISRecord:
    """Individual timestamped AIS position report."""

    def __init__(
        self,
        mmsi: str,
        timestamp: datetime,
        longitude: float,
        latitude: float,
        sog_knots: Optional[float] = None,
        cog_degrees: Optional[float] = None,
        imo: Optional[str] = None,
        vessel_name: Optional[str] = None,
        vessel_type: Optional[str] = None,
        navigation_status: Optional[Union[NavigationStatus, str]] = None,
        source_identifier: str = "unknown_source",
        provenance: AISProvenance = AISProvenance.SYNTHETIC_DEMO_FEED,
        adapter_id: str = "DEMO_SYNTHETIC_FIXTURE_ADAPTER",
        verification_token: Optional[str] = None,
        raw_properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not (np.isfinite(longitude) and np.isfinite(latitude)):
            raise ValueError(f"AIS coordinates must be finite numbers: ({longitude}, {latitude})")
        if not (-180.0 <= longitude <= 180.0 and -90.0 <= latitude <= 90.0):
            raise ValueError(f"AIS coordinates out of range [-180, 180], [-90, 90]: ({longitude}, {latitude})")

        self.mmsi = str(mmsi).strip()
        self.timestamp = timestamp if timestamp.tzinfo is not None else timestamp.replace(tzinfo=timezone.utc)
        self.longitude = float(longitude)
        self.latitude = float(latitude)
        self.sog_knots = float(sog_knots) if (sog_knots is not None and np.isfinite(sog_knots)) else None
        self.cog_degrees = float(cog_degrees) if (cog_degrees is not None and np.isfinite(cog_degrees)) else None
        self.imo = str(imo).strip() if imo else None
        self.vessel_name = str(vessel_name).strip() if vessel_name else None
        self.vessel_type = str(vessel_type).strip() if vessel_type else None
        self.navigation_status = (
            navigation_status.value if isinstance(navigation_status, NavigationStatus)
            else (str(navigation_status) if navigation_status else NavigationStatus.UNKNOWN.value)
        )
        self.source_identifier = source_identifier
        self.provenance = (
            provenance.value if isinstance(provenance, AISProvenance) else str(provenance)
        )
        self.adapter_id = adapter_id
        self.verification_token = verification_token
        self.raw_properties = raw_properties or {}
        self._seal = self._compute_seal()

    def _compute_seal(self) -> str:
        """Compute SHA-256 seal over AIS record provenance fields to prevent post-validation mutation."""
        prov_val = self.provenance.value if isinstance(self.provenance, AISProvenance) else str(self.provenance)
        raw = f"{self.mmsi}:{self.timestamp.isoformat()}:{self.longitude}:{self.latitude}:{prov_val}:{self.adapter_id}:{self.verification_token}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify that record provenance fields have not been modified post-instantiation."""
        return hasattr(self, "_seal") and self._seal == self._compute_seal()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize record into dictionary."""
        return {
            "mmsi": self.mmsi,
            "timestamp": self.timestamp.isoformat(),
            "longitude": round(self.longitude, 6),
            "latitude": round(self.latitude, 6),
            "sog_knots": round(self.sog_knots, 2) if self.sog_knots is not None else None,
            "cog_degrees": round(self.cog_degrees, 1) if self.cog_degrees is not None else None,
            "imo": self.imo,
            "vessel_name": self.vessel_name,
            "vessel_type": self.vessel_type,
            "navigation_status": self.navigation_status,
            "source_identifier": self.source_identifier,
            "provenance": self.provenance,
            "adapter_id": self.adapter_id,
        }


class TrackQualityReport:
    """Quality control audit report for a vessel's AIS trajectory."""

    def __init__(
        self,
        records_received: int,
        records_rejected: int,
        records_retained: int,
        rejection_reasons: Dict[str, int],
        max_gap_seconds: float,
        time_span_seconds: float,
        impossible_speed_jumps: int,
        is_usable: bool,
        speed_anomalies: Optional[List[Dict[str, Any]]] = None,
        quality_class: TrackQualityClass = TrackQualityClass.EXCELLENT,
    ) -> None:
        self.records_received = records_received
        self.records_rejected = records_rejected
        self.records_retained = records_retained
        self.rejection_reasons = rejection_reasons
        self.max_gap_seconds = max_gap_seconds
        self.time_span_seconds = time_span_seconds
        self.impossible_speed_jumps = impossible_speed_jumps
        self.is_usable = is_usable
        self.speed_anomalies = speed_anomalies or []
        self.quality_class = quality_class

    def to_dict(self) -> Dict[str, Any]:
        return {
            "records_received": self.records_received,
            "records_rejected": self.records_rejected,
            "records_retained": self.records_retained,
            "rejection_reasons": self.rejection_reasons,
            "max_gap_seconds": round(self.max_gap_seconds, 1),
            "max_gap_hours": round(self.max_gap_seconds / 3600.0, 2),
            "time_span_hours": round(self.time_span_seconds / 3600.0, 2),
            "impossible_speed_jumps": self.impossible_speed_jumps,
            "speed_anomalies_count": len(self.speed_anomalies),
            "quality_class": self.quality_class.value,
            "is_usable": self.is_usable,
        }


class VesselTrack:
    """Chronologically sorted, quality-filtered trajectory of a specific vessel."""

    def __init__(
        self,
        mmsi: str,
        records: List[AISRecord],
        quality_report: TrackQualityReport,
        imo: Optional[str] = None,
        vessel_name: Optional[str] = None,
        vessel_type: Optional[str] = None,
    ) -> None:
        self.mmsi = mmsi
        self.records = records
        self.quality_report = quality_report
        self.imo = imo
        self.vessel_name = vessel_name
        self.vessel_type = vessel_type

    @property
    def start_time(self) -> Optional[datetime]:
        return self.records[0].timestamp if self.records else None

    @property
    def end_time(self) -> Optional[datetime]:
        return self.records[-1].timestamp if self.records else None

    def to_linestring(self) -> Optional[LineString]:
        """Convert retained records into a Shapely LineString geometry."""
        if len(self.records) < 2:
            return None
        coords = [(r.longitude, r.latitude) for r in self.records]
        return LineString(coords)


# ---------------------------------------------------------------------------
# Track Quality Filtering & Ingestion
# ---------------------------------------------------------------------------


def filter_and_assemble_vessel_tracks(
    records: List[AISRecord],
    max_plausible_speed_knots: float = 60.0,
    max_interpolation_gap_seconds: float = 7200.0,  # 2 hours
) -> Dict[str, VesselTrack]:
    """Group, filter, and validate raw AIS records into clean vessel tracks.

    Quality Controls Enforced:
    --------------------------
    - Discards invalid / out-of-range coordinates.
    - Resolves duplicate timestamps deterministically.
    - Detects impossible kinematic speed jumps (> max_plausible_speed_knots).
    - Measures tracking gaps without fabricating interpolation across large dropouts.
    """
    grouped: Dict[str, List[AISRecord]] = {}
    for r in records:
        grouped.setdefault(r.mmsi, []).append(r)

    tracks: Dict[str, VesselTrack] = {}

    for mmsi, mmsi_records in grouped.items():
        received_count = len(mmsi_records)
        rejection_reasons: Dict[str, int] = {}

        # 1. Coordinate range filter
        valid_coords: List[AISRecord] = []
        for rec in mmsi_records:
            if -180.0 <= rec.longitude <= 180.0 and -90.0 <= rec.latitude <= 90.0:
                valid_coords.append(rec)
            else:
                rejection_reasons["invalid_coordinates"] = rejection_reasons.get("invalid_coordinates", 0) + 1

        # 2. Chronological sorting
        valid_coords.sort(key=lambda x: x.timestamp)

        # 3. Deduplication of identical timestamps
        deduped: List[AISRecord] = []
        seen_times = set()
        for rec in valid_coords:
            t_iso = rec.timestamp.isoformat()
            if t_iso in seen_times:
                rejection_reasons["duplicate_timestamp"] = rejection_reasons.get("duplicate_timestamp", 0) + 1
                continue
            seen_times.add(t_iso)
            deduped.append(rec)

        # 4. Kinematic feasibility & speed jump check
        retained: List[AISRecord] = []
        speed_anomalies: List[Dict[str, Any]] = []
        speed_jumps = 0
        max_gap = 0.0

        # Detect if first point is an isolated outlier against points 1 and 2
        start_idx = 0
        if len(deduped) >= 3:
            p0 = deduped[0]
            p1 = deduped[1]
            p2 = deduped[2]
            dt_01 = (p1.timestamp - p0.timestamp).total_seconds()
            dt_12 = (p2.timestamp - p1.timestamp).total_seconds()
            if dt_01 > 0 and dt_12 > 0:
                s_01 = (haversine_distance_m(p0.longitude, p0.latitude, p1.longitude, p1.latitude) / dt_01) * 1.94384
                s_12 = (haversine_distance_m(p1.longitude, p1.latitude, p2.longitude, p2.latitude) / dt_12) * 1.94384
                if s_01 > max_plausible_speed_knots and s_12 <= max_plausible_speed_knots:
                    # p0 is an isolated first-point anomaly; discard it so subsequent valid track is preserved
                    speed_jumps += 1
                    rejection_reasons["impossible_speed_jump"] = rejection_reasons.get("impossible_speed_jump", 0) + 1
                    speed_anomalies.append({
                        "prev_timestamp": p0.timestamp.isoformat(),
                        "curr_timestamp": p1.timestamp.isoformat(),
                        "dt_seconds": round(dt_01, 1),
                        "distance_m": round(haversine_distance_m(p0.longitude, p0.latitude, p1.longitude, p1.latitude), 1),
                        "apparent_speed_knots": round(s_01, 2),
                        "threshold_knots": max_plausible_speed_knots,
                        "action": "FIRST_POINT_OUTLIER_REJECTED",
                    })
                    start_idx = 1

        for i, rec in enumerate(deduped[start_idx:]):
            if i == 0:
                retained.append(rec)
                continue

            prev = retained[-1]
            dt_s = (rec.timestamp - prev.timestamp).total_seconds()
            if dt_s <= 0:
                rejection_reasons["non_monotonic_timestamp"] = rejection_reasons.get("non_monotonic_timestamp", 0) + 1
                continue

            if dt_s > max_gap:
                max_gap = dt_s

            # Distance in meters
            dist_m = haversine_distance_m(prev.longitude, prev.latitude, rec.longitude, rec.latitude)
            speed_ms = dist_m / dt_s
            speed_knots = speed_ms * 1.94384

            if speed_knots > max_plausible_speed_knots:
                speed_jumps += 1
                rejection_reasons["impossible_speed_jump"] = rejection_reasons.get("impossible_speed_jump", 0) + 1
                speed_anomalies.append({
                    "prev_timestamp": prev.timestamp.isoformat(),
                    "curr_timestamp": rec.timestamp.isoformat(),
                    "dt_seconds": round(dt_s, 1),
                    "distance_m": round(dist_m, 1),
                    "apparent_speed_knots": round(speed_knots, 2),
                    "threshold_knots": max_plausible_speed_knots,
                    "action": "OUTLIER_POINT_REJECTED",
                })
                # Reject anomalous outlier point but keep track alive for subsequent valid observations
                continue

            retained.append(rec)

        rejected_count = received_count - len(retained)
        time_span = (
            (retained[-1].timestamp - retained[0].timestamp).total_seconds()
            if len(retained) >= 2 else 0.0
        )

        if len(retained) < 2 or (received_count > 0 and (len(retained) / received_count < 0.5)):
            quality_class = TrackQualityClass.UNUSABLE
            is_usable = False
        elif rejected_count > 0 or max_gap > max_interpolation_gap_seconds or speed_jumps > 0:
            quality_class = TrackQualityClass.DEGRADED
            is_usable = True
        else:
            quality_class = TrackQualityClass.EXCELLENT
            is_usable = True

        # Extract vessel metadata if available in records
        v_name = next((r.vessel_name for r in retained if r.vessel_name), None)
        v_imo = next((r.imo for r in retained if r.imo), None)
        v_type = next((r.vessel_type for r in retained if r.vessel_type), None)

        quality = TrackQualityReport(
            records_received=received_count,
            records_rejected=rejected_count,
            records_retained=len(retained),
            rejection_reasons=rejection_reasons,
            max_gap_seconds=max_gap,
            time_span_seconds=time_span,
            impossible_speed_jumps=speed_jumps,
            is_usable=is_usable,
            speed_anomalies=speed_anomalies,
            quality_class=quality_class,
        )

        tracks[mmsi] = VesselTrack(
            mmsi=mmsi,
            records=retained,
            quality_report=quality,
            imo=v_imo,
            vessel_name=v_name,
            vessel_type=v_type,
        )

    return tracks


# ---------------------------------------------------------------------------
# Candidate Hypotheses Extraction from Drift Model
# ---------------------------------------------------------------------------


class CandidateHypothesisPoint:
    """A discrete time-indexed position hypothesis derived from backtracked drift modeling."""

    def __init__(
        self,
        longitude: float,
        latitude: float,
        timestamp: datetime,
        particle_id: str,
        windage_factor: float,
        trajectory_step: int,
        is_origin_endpoint: bool = False,
    ) -> None:
        self.longitude = longitude
        self.latitude = latitude
        self.timestamp = timestamp if timestamp.tzinfo is not None else timestamp.replace(tzinfo=timezone.utc)
        self.particle_id = particle_id
        self.windage_factor = windage_factor
        self.trajectory_step = trajectory_step
        self.is_origin_endpoint = is_origin_endpoint


def extract_candidate_hypotheses_from_trajectories(
    trajectories: List[ParticleTrajectory],
) -> List[CandidateHypothesisPoint]:
    """Extract all time-indexed state hypotheses from backtracked Lagrangian particles."""
    hypotheses: List[CandidateHypothesisPoint] = []
    for traj in trajectories:
        n_steps = len(traj.steps)
        for s in traj.steps:
            is_term = (s.step_index == n_steps)
            hypotheses.append(
                CandidateHypothesisPoint(
                    longitude=s.longitude,
                    latitude=s.latitude,
                    timestamp=s.timestamp,
                    particle_id=traj.particle_id,
                    windage_factor=traj.windage_factor,
                    trajectory_step=s.step_index,
                    is_origin_endpoint=is_term,
                )
            )
    return hypotheses


# ---------------------------------------------------------------------------
# Spatio-Temporal Correlation Engine
# ---------------------------------------------------------------------------


class VesselCompatibilityMetric:
    """Detailed spatio-temporal compatibility assessment for a single candidate vessel."""

    def __init__(
        self,
        mmsi: str,
        vessel_name: Optional[str],
        imo: Optional[str],
        vessel_type: Optional[str],
        min_distance_to_origin_m: float,
        min_distance_to_trajectory_m: float,
        closest_approach_time_utc: datetime,
        closest_hypothesis_time_utc: datetime,
        temporal_offset_seconds: float,
        closest_hypothesis_particle_id: str,
        closest_hypothesis_step: int,
        closest_hypothesis_windage: float,
        is_position_inferred: bool,
        interpolation_gap_seconds: float,
        inside_candidate_origin_region: bool,
        inside_trajectory_envelope: bool,
        coverage_status: VesselCoverageStatus,
        track_continuity_ratio: float,
        evidence_compatibility_score: float,
        score_breakdown: Dict[str, Any],
        identity_provenance: Dict[str, Any],
        provenance: str,
        data_limitations: List[str],
    ) -> None:
        self.mmsi = mmsi
        self.vessel_name = vessel_name
        self.imo = imo
        self.vessel_type = vessel_type
        self.min_distance_to_origin_m = min_distance_to_origin_m
        self.min_distance_to_trajectory_m = min_distance_to_trajectory_m
        self.closest_approach_time_utc = closest_approach_time_utc
        self.closest_hypothesis_time_utc = closest_hypothesis_time_utc
        self.temporal_offset_seconds = temporal_offset_seconds
        self.closest_hypothesis_particle_id = closest_hypothesis_particle_id
        self.closest_hypothesis_step = closest_hypothesis_step
        self.closest_hypothesis_windage = closest_hypothesis_windage
        self.is_position_inferred = is_position_inferred
        self.interpolation_gap_seconds = interpolation_gap_seconds
        self.inside_candidate_origin_region = inside_candidate_origin_region
        self.inside_trajectory_envelope = inside_trajectory_envelope
        self.coverage_status = coverage_status
        self.track_continuity_ratio = track_continuity_ratio
        self.evidence_compatibility_score = evidence_compatibility_score
        self.score_breakdown = score_breakdown
        self.identity_provenance = identity_provenance
        self.provenance = provenance
        self.data_limitations = data_limitations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mmsi": self.mmsi,
            "vessel_name": self.vessel_name,
            "imo": self.imo,
            "vessel_type": self.vessel_type,
            "min_distance_to_origin_m": round(self.min_distance_to_origin_m, 1),
            "min_distance_to_trajectory_m": round(self.min_distance_to_trajectory_m, 1),
            "closest_approach_time_utc": self.closest_approach_time_utc.isoformat(),
            "closest_hypothesis_time_utc": self.closest_hypothesis_time_utc.isoformat(),
            "temporal_offset_seconds": round(self.temporal_offset_seconds, 1),
            "temporal_offset_hours": round(self.temporal_offset_seconds / 3600.0, 2),
            "closest_hypothesis_particle_id": self.closest_hypothesis_particle_id,
            "closest_hypothesis_step": self.closest_hypothesis_step,
            "closest_hypothesis_windage": round(self.closest_hypothesis_windage, 4),
            "is_position_inferred": self.is_position_inferred,
            "interpolation_gap_seconds": round(self.interpolation_gap_seconds, 1),
            "inside_candidate_origin_region": self.inside_candidate_origin_region,
            "inside_trajectory_envelope": self.inside_trajectory_envelope,
            "coverage_status": self.coverage_status.value,
            "track_continuity_ratio": round(self.track_continuity_ratio, 3),
            "evidence_compatibility_score": round(self.evidence_compatibility_score, 4),
            "score_breakdown": {
                k: (round(v, 4) if isinstance(v, (int, float)) else v)
                for k, v in self.score_breakdown.items()
            },
            "identity_provenance": self.identity_provenance,
            "provenance": self.provenance,
            "data_limitations": self.data_limitations,
        }


def correlate_vessel_tracks(
    tracks: Dict[str, VesselTrack],
    hypotheses: List[CandidateHypothesisPoint],
    candidate_origin_polygon: Optional[Polygon] = None,
    trajectory_envelope_polygon: Optional[Polygon] = None,
    max_interpolation_gap_seconds: float = 7200.0,  # 2 hours
    distance_scale_m: float = 5000.0,               # 5 km
    time_scale_seconds: float = 3600.0,              # 1 hour
    origin_coarse_time_window_seconds: float = 10800.0,  # 3 hours coarse window
    weights: CompatibilityScoreWeights = CompatibilityScoreWeights(),
    mode: AISCorrelationMode = AISCorrelationMode.DEMO,
) -> List[VesselCompatibilityMetric]:
    """Correlate vessel tracks against time-indexed candidate origin hypotheses.

    Hierarchy of Evaluation:
    ------------------------
    1. PRIMARY: Exact time-synchronized geodesic distance to discrete backtracked particle hypotheses.
    2. SECONDARY: Spatial proximity to terminal origin endpoints and temporally-gated origin polygon coincidence.
    3. TERTIARY: Spatial intersection with overall trajectory uncertainty envelope.
    """
    # 0. Integrity verification on all input vessel records (Tamper Detection)
    for mmsi, track in tracks.items():
        for rec in track.records:
            if not rec.verify_integrity():
                raise ProvenanceGateError(
                    f"Tamper detection rejected for vessel '{mmsi}' record at {rec.timestamp.isoformat()}: "
                    "Record metadata has been modified post-instantiation."
                )

    # Provenance gate check for PHYSICAL mode (Anti-Bypass Protection)
    if mode == AISCorrelationMode.PHYSICAL:
        if not AISSourceRegistry.has_active_operational_adapters():
            raise ProvenanceGateError(
                "PHYSICAL mode rejected: No accredited operational AIS provider adapter is active in the repository. "
                "Physical correlation is BLOCKED — AWAITING_OPERATIONAL_AIS_SOURCE. "
                "Callers cannot declare authority merely by setting record provenance flags."
            )
        for mmsi, track in tracks.items():
            for rec in track.records:
                prov_val = rec.provenance.value if isinstance(rec.provenance, AISProvenance) else str(rec.provenance)
                if (
                    prov_val != AISProvenance.VERIFIED_OPERATIONAL_FEED.value
                    or not AISSourceRegistry.is_adapter_accredited_operational(rec.adapter_id, rec.verification_token)
                ):
                    raise ProvenanceGateError(
                        f"PHYSICAL mode rejected: Vessel {mmsi} record at {rec.timestamp.isoformat()} "
                        f"lacks accredited operational provider lineage (adapter: '{rec.adapter_id}'). "
                        "Caller-declared provenance flags without accredited adapter lineage are strictly rejected."
                    )

    if not hypotheses:
        return []

    # Separate origin endpoints (T1 - tau) from intermediate path hypotheses
    origin_hypotheses = [h for h in hypotheses if h.is_origin_endpoint]
    if not origin_hypotheses:
        origin_hypotheses = hypotheses

    t_hyp_min = min(h.timestamp for h in hypotheses)
    t_hyp_max = max(h.timestamp for h in hypotheses)

    results: List[VesselCompatibilityMetric] = []

    for mmsi, track in tracks.items():
        if not track.records:
            continue

        limitations: List[str] = []
        if track.quality_report.max_gap_seconds > max_interpolation_gap_seconds:
            limitations.append(
                f"Track has large telemetry gap ({track.quality_report.max_gap_seconds / 3600.0:.1f}h); "
                "positions were not interpolated across gap."
            )
        if track.quality_report.records_rejected > 0:
            limitations.append(f"{track.quality_report.records_rejected} anomalous/duplicate reports were rejected.")

        t_start = track.records[0].timestamp
        t_end = track.records[-1].timestamp

        # 1. Primary: Time-synchronized evaluation across ALL trajectory hypotheses
        best_traj_dist = float("inf")
        best_traj_vessel_time = track.records[0].timestamp
        best_traj_hypo_time = hypotheses[0].timestamp
        best_traj_dt_s = float("inf")
        best_traj_inferred = False
        best_traj_gap_s = 0.0
        best_particle_id = hypotheses[0].particle_id
        best_step_idx = hypotheses[0].trajectory_step
        best_windage = hypotheses[0].windage_factor

        for hyp in hypotheses:
            ht = hyp.timestamp
            if t_start <= ht <= t_end:
                idx = 0
                while idx < len(track.records) - 1 and track.records[idx + 1].timestamp < ht:
                    idx += 1
                r1 = track.records[idx]
                r2 = track.records[min(idx + 1, len(track.records) - 1)]
                gap_s = (r2.timestamp - r1.timestamp).total_seconds()

                if gap_s <= max_interpolation_gap_seconds and gap_s > 0:
                    frac = (ht - r1.timestamp).total_seconds() / gap_s
                    interp_lon, interp_lat = interpolate_geodesic_position(
                        r1.longitude, r1.latitude, r2.longitude, r2.latitude, frac
                    )
                    d = haversine_distance_m(interp_lon, interp_lat, hyp.longitude, hyp.latitude)
                    if d < best_traj_dist:
                        best_traj_dist = d
                        best_traj_vessel_time = ht
                        best_traj_hypo_time = ht
                        best_traj_dt_s = 0.0
                        is_exact_match = (
                            abs((ht - r1.timestamp).total_seconds()) < 1e-3
                            or abs((r2.timestamp - ht).total_seconds()) < 1e-3
                        )
                        best_traj_inferred = not is_exact_match
                        best_traj_gap_s = gap_s
                        best_particle_id = hyp.particle_id
                        best_step_idx = hyp.trajectory_step
                        best_windage = hyp.windage_factor
                else:
                    # Gap is > max_interpolation_gap_seconds: do NOT interpolate across wide gap!
                    # Only consider bracket boundary if within max_interpolation_gap_seconds
                    dt1 = abs((r1.timestamp - ht).total_seconds())
                    dt2 = abs((r2.timestamp - ht).total_seconds())
                    if min(dt1, dt2) <= max_interpolation_gap_seconds:
                        r_close = r1 if dt1 <= dt2 else r2
                        dt = min(dt1, dt2)
                        d = haversine_distance_m(r_close.longitude, r_close.latitude, hyp.longitude, hyp.latitude)
                        if d < best_traj_dist:
                            best_traj_dist = d
                            best_traj_vessel_time = r_close.timestamp
                            best_traj_hypo_time = ht
                            best_traj_dt_s = dt
                            best_traj_inferred = False
                            best_traj_gap_s = gap_s
                            best_particle_id = hyp.particle_id
                            best_step_idx = hyp.trajectory_step
                            best_windage = hyp.windage_factor
            else:
                closest_rec = track.records[0] if ht < t_start else track.records[-1]
                dt = abs((closest_rec.timestamp - ht).total_seconds())
                # Only compare against boundary observation if within max_interpolation_gap_seconds
                if dt <= max_interpolation_gap_seconds:
                    d = haversine_distance_m(closest_rec.longitude, closest_rec.latitude, hyp.longitude, hyp.latitude)
                    if d < best_traj_dist:
                        best_traj_dist = d
                        best_traj_vessel_time = closest_rec.timestamp
                        best_traj_hypo_time = ht
                        best_traj_dt_s = dt
                        best_traj_inferred = False
                        best_traj_gap_s = 0.0
                        best_particle_id = hyp.particle_id
                        best_step_idx = hyp.trajectory_step
                        best_windage = hyp.windage_factor

        # 2. Secondary: Time-synchronized distance to terminal origin endpoints
        min_origin_endpoint_dist = float("inf")
        for hyp in origin_hypotheses:
            ht = hyp.timestamp
            if t_start <= ht <= t_end:
                idx = 0
                while idx < len(track.records) - 1 and track.records[idx + 1].timestamp < ht:
                    idx += 1
                r1 = track.records[idx]
                r2 = track.records[min(idx + 1, len(track.records) - 1)]
                gap_s = (r2.timestamp - r1.timestamp).total_seconds()
                if gap_s <= max_interpolation_gap_seconds and gap_s > 0:
                    frac = (ht - r1.timestamp).total_seconds() / gap_s
                    interp_lon, interp_lat = interpolate_geodesic_position(
                        r1.longitude, r1.latitude, r2.longitude, r2.latitude, frac
                    )
                    d = haversine_distance_m(interp_lon, interp_lat, hyp.longitude, hyp.latitude)
                    if d < min_origin_endpoint_dist:
                        min_origin_endpoint_dist = d
                else:
                    dt1 = abs((r1.timestamp - ht).total_seconds())
                    dt2 = abs((r2.timestamp - ht).total_seconds())
                    if min(dt1, dt2) <= max_interpolation_gap_seconds:
                        r_close = r1 if dt1 <= dt2 else r2
                        d = haversine_distance_m(r_close.longitude, r_close.latitude, hyp.longitude, hyp.latitude)
                        if d < min_origin_endpoint_dist:
                            min_origin_endpoint_dist = d
            else:
                closest_rec = track.records[0] if ht < t_start else track.records[-1]
                dt = abs((closest_rec.timestamp - ht).total_seconds())
                if dt <= max_interpolation_gap_seconds:
                    d = haversine_distance_m(closest_rec.longitude, closest_rec.latitude, hyp.longitude, hyp.latitude)
                    if d < min_origin_endpoint_dist:
                        min_origin_endpoint_dist = d

        # 3. Secondary: Inside candidate origin region polygon at a plausible time?
        inside_origin_at_plausible_time = False
        best_origin_coincidence = 0.0
        if candidate_origin_polygon is not None and not candidate_origin_polygon.is_empty:
            for rec in track.records:
                p = Point(rec.longitude, rec.latitude)
                if candidate_origin_polygon.contains(p):
                    dt_origin = min(abs((rec.timestamp - h.timestamp).total_seconds()) for h in origin_hypotheses)
                    if dt_origin <= origin_coarse_time_window_seconds:
                        inside_origin_at_plausible_time = True
                    coincidence_factor = float(np.exp(-dt_origin / time_scale_seconds))
                    if coincidence_factor > best_origin_coincidence:
                        best_origin_coincidence = coincidence_factor

        # 4. Tertiary: Inside trajectory envelope during modeled drift window?
        inside_envelope = False
        if trajectory_envelope_polygon is not None and not trajectory_envelope_polygon.is_empty:
            t_env_min = t_hyp_min - timedelta(seconds=time_scale_seconds)
            t_env_max = t_hyp_max + timedelta(seconds=time_scale_seconds)
            for rec in track.records:
                if t_env_min <= rec.timestamp <= t_env_max:
                    p = Point(rec.longitude, rec.latitude)
                    if trajectory_envelope_polygon.contains(p):
                        inside_envelope = True
                        break

        # 5. Coverage Status Classification
        if t_end < t_hyp_min or t_start > t_hyp_max:
            cov_status = VesselCoverageStatus.OUTSIDE_WINDOW
        elif track.quality_report.max_gap_seconds > max_interpolation_gap_seconds:
            cov_status = VesselCoverageStatus.TELEMETRY_GAP_ACROSS_WINDOW
        elif not track.quality_report.is_usable:
            cov_status = VesselCoverageStatus.INSUFFICIENT_DATA
        else:
            cov_status = VesselCoverageStatus.OBSERVED_IN_WINDOW

        # 6. Compute Transparent Evidence Compatibility Score
        # Component A & B: Spatial and Temporal Proximity to Trajectory Ensemble (0 to 1)
        if not np.isfinite(best_traj_dist):
            closest_rec = track.records[0] if t_end < t_hyp_min else track.records[-1]
            best_traj_dist = min(
                haversine_distance_m(closest_rec.longitude, closest_rec.latitude, h.longitude, h.latitude)
                for h in hypotheses
            )
            best_traj_dt_s = min(
                abs((r.timestamp - h.timestamp).total_seconds())
                for r in track.records
                for h in hypotheses
            )
            best_traj_vessel_time = closest_rec.timestamp
            s_spatial = 0.0
            s_temporal = 0.0
        else:
            s_spatial = float(np.exp(-best_traj_dist / distance_scale_m))
            s_temporal = float(np.exp(-best_traj_dt_s / time_scale_seconds))

        # Component C: Terminal Origin Endpoint Proximity (0 to 1)
        if not np.isfinite(min_origin_endpoint_dist):
            min_origin_endpoint_dist = min(
                haversine_distance_m(track.records[-1].longitude, track.records[-1].latitude, h.longitude, h.latitude)
                for h in origin_hypotheses
            )
            s_endpoint = 0.0
        else:
            s_endpoint = float(np.exp(-min_origin_endpoint_dist / distance_scale_m))

        # Component D: Origin Polygon Coincidence (0 to 1, temporally gated)
        s_origin_poly = best_origin_coincidence

        # Component E: Track Continuity Ratio
        q_ratio = (
            float(track.quality_report.records_retained / track.quality_report.records_received)
            if track.quality_report.records_received > 0 else 0.0
        )

        base_score = (
            weights.weight_trajectory_spatial * s_spatial
            + weights.weight_temporal_proximity * s_temporal
            + weights.weight_origin_endpoint * s_endpoint
            + weights.weight_origin_polygon * s_origin_poly
        )
        composite_score = float(
            np.clip(base_score * (weights.quality_floor + weights.quality_scale * q_ratio), 0.0, 1.0)
        )

        score_breakdown = {
            "primary_spatial_trajectory_component": s_spatial,
            "primary_temporal_proximity_component": s_temporal,
            "secondary_origin_endpoint_component": s_endpoint,
            "secondary_origin_polygon_component": s_origin_poly,
            "tertiary_envelope_containment": inside_envelope,
            "spatial_trajectory_proximity_component": s_spatial,
            "temporal_proximity_component": s_temporal,
            "origin_endpoint_proximity_component": s_endpoint,
            "origin_polygon_coincidence": s_origin_poly,
            "track_quality_factor": q_ratio,
            "score_weights_version": weights.version,
        }

        # Identity Provenance
        sources = list({r.source_identifier for r in track.records if r.source_identifier})
        identity_prov = {
            "mmsi": mmsi,
            "imo": track.imo,
            "vessel_name": track.vessel_name,
            "vessel_type": track.vessel_type,
            "source_identifiers": sources,
            "identity_resolution_status": "SINGLE_MMSI_UNRESOLVED_TEMPORAL_IDENTITY",
        }

        provenance_str = track.records[0].provenance if track.records else AISProvenance.SYNTHETIC_DEMO_FEED.value

        metric = VesselCompatibilityMetric(
            mmsi=mmsi,
            vessel_name=track.vessel_name,
            imo=track.imo,
            vessel_type=track.vessel_type,
            min_distance_to_origin_m=min_origin_endpoint_dist,
            min_distance_to_trajectory_m=best_traj_dist,
            closest_approach_time_utc=best_traj_vessel_time,
            closest_hypothesis_time_utc=best_traj_hypo_time,
            temporal_offset_seconds=best_traj_dt_s,
            closest_hypothesis_particle_id=best_particle_id,
            closest_hypothesis_step=best_step_idx,
            closest_hypothesis_windage=best_windage,
            is_position_inferred=best_traj_inferred,
            interpolation_gap_seconds=best_traj_gap_s,
            inside_candidate_origin_region=inside_origin_at_plausible_time,
            inside_trajectory_envelope=inside_envelope,
            coverage_status=cov_status,
            track_continuity_ratio=q_ratio,
            evidence_compatibility_score=composite_score,
            score_breakdown=score_breakdown,
            identity_provenance=identity_prov,
            provenance=provenance_str,
            data_limitations=limitations,
        )
        results.append(metric)

    # Sort descending by evidence compatibility score
    results.sort(key=lambda x: x.evidence_compatibility_score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# RFC 7946 GeoJSON & Machine-Readable Output Serialization
# ---------------------------------------------------------------------------


def serialize_ais_correlation_to_geojson(
    candidates: List[VesselCompatibilityMetric],
    tracks: Dict[str, VesselTrack],
    candidate_origin_polygon: Optional[Polygon] = None,
    trajectory_envelope_polygon: Optional[Polygon] = None,
    mode: AISCorrelationMode = AISCorrelationMode.DEMO,
    event_id: str = "unknown_event",
) -> Dict[str, Any]:
    """Serialize correlation results into an RFC 7946 WGS84 GeoJSON FeatureCollection."""
    features: List[Dict[str, Any]] = []

    # 1. Candidate Origin Region Polygon (Reference)
    if candidate_origin_polygon is not None and not candidate_origin_polygon.is_empty:
        features.append({
            "type": "Feature",
            "id": f"{event_id}_candidate_origin_region",
            "geometry": mapping(candidate_origin_polygon),
            "properties": {
                "feature_type": "candidate_origin_region_reference",
                "event_id": event_id,
            },
        })

    # 2. Trajectory Envelope Polygon (Reference)
    if trajectory_envelope_polygon is not None and not trajectory_envelope_polygon.is_empty:
        features.append({
            "type": "Feature",
            "id": f"{event_id}_trajectory_envelope",
            "geometry": mapping(trajectory_envelope_polygon),
            "properties": {
                "feature_type": "trajectory_envelope_reference",
                "event_id": event_id,
            },
        })

    # 3. Vessel Tracks & Candidate Markers
    for cand in candidates:
        track = tracks.get(cand.mmsi)
        if not track or not track.records:
            continue

        # Vessel Path LineString
        line_geom = track.to_linestring()
        if line_geom:
            features.append({
                "type": "Feature",
                "id": f"vessel_{cand.mmsi}_track",
                "geometry": mapping(line_geom),
                "properties": {
                    "feature_type": "vessel_track_linestring",
                    "mmsi": cand.mmsi,
                    "vessel_name": cand.vessel_name,
                    "imo": cand.imo,
                    "vessel_type": cand.vessel_type,
                    "evidence_compatibility_score": round(cand.evidence_compatibility_score, 4),
                    "score_breakdown": cand.score_breakdown,
                    "score_version": cand.score_breakdown.get("score_weights_version", "v1.1.0"),
                    "min_distance_to_trajectory_m": round(cand.min_distance_to_trajectory_m, 1),
                    "min_distance_to_origin_m": round(cand.min_distance_to_origin_m, 1),
                    "closest_approach_time_utc": cand.closest_approach_time_utc.isoformat(),
                    "closest_hypothesis_time_utc": cand.closest_hypothesis_time_utc.isoformat(),
                    "temporal_offset_seconds": round(cand.temporal_offset_seconds, 1),
                    "closest_hypothesis_particle_id": cand.closest_hypothesis_particle_id,
                    "closest_hypothesis_step": cand.closest_hypothesis_step,
                    "closest_hypothesis_windage": round(cand.closest_hypothesis_windage, 4),
                    "is_position_inferred": cand.is_position_inferred,
                    "interpolation_gap_seconds": round(cand.interpolation_gap_seconds, 1),
                    "inside_candidate_origin": cand.inside_candidate_origin_region,
                    "inside_trajectory_envelope": cand.inside_trajectory_envelope,
                    "coverage_status": cand.coverage_status.value,
                    "track_continuity_ratio": round(cand.track_continuity_ratio, 3),
                    "identity_provenance": cand.identity_provenance,
                    "provenance": cand.provenance,
                    "data_limitations": cand.data_limitations,
                },
            })

        # Closest Approach Point Marker
        rec_closest = min(
            track.records,
            key=lambda r: abs((r.timestamp - cand.closest_approach_time_utc).total_seconds()),
        )
        features.append({
            "type": "Feature",
            "id": f"vessel_{cand.mmsi}_closest_approach",
            "geometry": {
                "type": "Point",
                "coordinates": [round(rec_closest.longitude, 6), round(rec_closest.latitude, 6)],
            },
            "properties": {
                "feature_type": "vessel_closest_approach_point",
                "mmsi": cand.mmsi,
                "vessel_name": cand.vessel_name,
                "imo": cand.imo,
                "vessel_type": cand.vessel_type,
                "timestamp_utc": rec_closest.timestamp.isoformat(),
                "closest_hypothesis_time_utc": cand.closest_hypothesis_time_utc.isoformat(),
                "min_distance_to_trajectory_m": round(cand.min_distance_to_trajectory_m, 1),
                "min_distance_to_origin_m": round(cand.min_distance_to_origin_m, 1),
                "evidence_compatibility_score": round(cand.evidence_compatibility_score, 4),
                "is_position_inferred": cand.is_position_inferred,
                "coverage_status": cand.coverage_status.value,
                "provenance": cand.provenance,
            },
        })

    return {
        "type": "FeatureCollection",
        "name": "ocean_sentinel_ais_correlation",
        "metadata": {
            "mode": mode.value,
            "event_id": event_id,
            "candidate_count": len(candidates),
            "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "scientific_boundary": "EVIDENCE_COMPATIBILITY_ONLY_NO_LEGAL_ATTRIBUTION",
            "negative_proof_guard": "AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE",
        },
        "features": features,
    }


def serialize_ais_correlation_summary(
    candidates: List[VesselCompatibilityMetric],
    tracks: Dict[str, VesselTrack],
    mode: AISCorrelationMode = AISCorrelationMode.DEMO,
    event_id: str = "unknown_event",
    weights: Optional[CompatibilityScoreWeights] = None,
) -> Dict[str, Any]:
    """Produce machine-readable summary JSON of the AIS correlation results."""
    used_weights = weights or CompatibilityScoreWeights()
    return {
        "engine": "ocean_sentinel_ais_correlation_v1",
        "mode": mode.value,
        "event_id": event_id,
        "score_version": used_weights.version,
        "score_weights": used_weights.to_dict(),
        "total_vessels_evaluated": len(tracks),
        "candidate_vessels": [c.to_dict() for c in candidates],
        "scientific_limitations": [
            "AIS correlation establishes spatio-temporal compatibility with candidate origin hypotheses, NOT legal attribution.",
            "Absence of an AIS track in the candidate region does NOT prove no vessel was present (transponder blackouts, coverage gaps, unequipped vessels).",
            "Vessel Course Over Ground (COG) is not required to match slick drift direction.",
            "The evidence compatibility score is an uncalibrated ranking metric, not an attribution probability or likelihood of culpability.",
            "Candidate origin regions and backtracked trajectory envelopes represent physical hypotheses, not confirmed historical release coordinates.",
        ],
    }


# ---------------------------------------------------------------------------
# Deterministic DEMO Fixture Generator
# ---------------------------------------------------------------------------


def generate_deterministic_demo_ais_fixture(
    origin_lon: float = -90.438,
    origin_lat: float = 26.927,
    origin_time: Optional[datetime] = None,
) -> List[AISRecord]:
    """Generate a deterministic suite of synthetic vessel tracks for DEMO testing.

    Coordinates and timing are anchored relative to (origin_lon, origin_lat) and origin_time.

    Covers:
    1. Clearly compatible vessel (Tanker MT_HORIZON_STAR): crosses origin within 300m and 15m.
    2. Temporally incompatible vessel (Container MV_PACIFIC_CARRIER): same route 36h earlier.
    3. Spatially incompatible vessel (Tug OCEAN_TUG_TITAN): active at release time, but 65km away.
    4. Vessel with large AIS gap (Fishing SEA_PROWLER): 8-hour blackout across origin window.
    5. Noisy telemetry glitch vessel (GLITCH_RUNNER): contains impossible 95-knot speed jumps.
    6. Trajectory corridor candidate (Supply GULF_SUPPLIER_VII): passes ~4.2km off path.
    """
    ref_time = origin_time or datetime(2024, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    records: List[AISRecord] = []

    # 1. MT_HORIZON_STAR (MMSI 368123450) — Highly Compatible
    # Traverses from (origin_lon - 0.12, origin_lat - 0.12) to (origin_lon + 0.12, origin_lat + 0.12)
    # Reaching origin_lon, origin_lat at ref_time + 15 min (step 6)
    t0 = ref_time - timedelta(hours=2)
    for step in range(13):  # every 20 minutes for 4 hours
        t = t0 + timedelta(minutes=step * 20)
        frac = step / 12.0
        lon = (origin_lon - 0.12) + frac * 0.24
        lat = (origin_lat - 0.12) + frac * 0.24
        records.append(
            AISRecord(
                mmsi="368123450",
                timestamp=t,
                longitude=lon,
                latitude=lat,
                sog_knots=12.5,
                cog_degrees=45.0,
                imo="IMO9123456",
                vessel_name="MT_HORIZON_STAR",
                vessel_type="Crude Oil Tanker",
                navigation_status=NavigationStatus.UNDERWAY_USING_ENGINE,
                source_identifier="DEMO_STATION_GULF",
                provenance=AISProvenance.SYNTHETIC_DEMO_FEED,
            )
        )

    # 2. MV_PACIFIC_CARRIER (MMSI 368987650) — Temporally Incompatible (36 hours early)
    t_early = ref_time - timedelta(hours=36)
    for step in range(10):
        t = t_early + timedelta(minutes=step * 20)
        frac = step / 9.0
        lon = (origin_lon - 0.12) + frac * 0.24
        lat = (origin_lat - 0.12) + frac * 0.24
        records.append(
            AISRecord(
                mmsi="368987650",
                timestamp=t,
                longitude=lon,
                latitude=lat,
                sog_knots=18.0,
                cog_degrees=45.0,
                imo="IMO9876543",
                vessel_name="MV_PACIFIC_CARRIER",
                vessel_type="Container Ship",
                navigation_status=NavigationStatus.UNDERWAY_USING_ENGINE,
                source_identifier="DEMO_STATION_GULF",
                provenance=AISProvenance.SYNTHETIC_DEMO_FEED,
            )
        )

    # 3. OCEAN_TUG_TITAN (MMSI 367111220) — Spatially Incompatible (~65km West)
    for step in range(10):
        t = ref_time - timedelta(hours=2) + timedelta(minutes=step * 20)
        records.append(
            AISRecord(
                mmsi="367111220",
                timestamp=t,
                longitude=(origin_lon - 0.65) + step * 0.005,
                latitude=origin_lat + step * 0.005,
                sog_knots=8.0,
                cog_degrees=45.0,
                imo="IMO9333444",
                vessel_name="OCEAN_TUG_TITAN",
                vessel_type="Tug / Supply",
                navigation_status=NavigationStatus.UNDERWAY_USING_ENGINE,
                source_identifier="DEMO_STATION_GULF",
                provenance=AISProvenance.SYNTHETIC_DEMO_FEED,
            )
        )

    # 4. SEA_PROWLER (MMSI 366333440) — Large 8-hour AIS Transmission Blackout
    # Report before blackout
    records.append(
        AISRecord(
            mmsi="366333440",
            timestamp=ref_time - timedelta(hours=5),
            longitude=origin_lon - 0.08,
            latitude=origin_lat - 0.08,
            sog_knots=7.0,
            cog_degrees=45.0,
            vessel_name="SEA_PROWLER",
            vessel_type="Fishing Vessel",
            provenance=AISProvenance.SYNTHETIC_DEMO_FEED,
        )
    )
    # Report after blackout (8 hours later)
    records.append(
        AISRecord(
            mmsi="366333440",
            timestamp=ref_time + timedelta(hours=3),
            longitude=origin_lon + 0.08,
            latitude=origin_lat + 0.08,
            sog_knots=6.5,
            cog_degrees=45.0,
            vessel_name="SEA_PROWLER",
            vessel_type="Fishing Vessel",
            provenance=AISProvenance.SYNTHETIC_DEMO_FEED,
        )
    )

    # 5. GLITCH_RUNNER (MMSI 369555660) — Impossible 95-knot Speed Jump
    records.append(
        AISRecord(
            mmsi="369555660",
            timestamp=ref_time - timedelta(hours=1),
            longitude=origin_lon - 0.05,
            latitude=origin_lat,
            sog_knots=12.0,
            cog_degrees=90.0,
            vessel_name="GLITCH_RUNNER",
            provenance=AISProvenance.SYNTHETIC_DEMO_FEED,
        )
    )
    # 5 minutes later, jumped 20 km away (speed ~ 130 knots!)
    records.append(
        AISRecord(
            mmsi="369555660",
            timestamp=ref_time - timedelta(minutes=55),
            longitude=origin_lon + 0.15,
            latitude=origin_lat,
            sog_knots=12.0,
            cog_degrees=90.0,
            vessel_name="GLITCH_RUNNER",
            provenance=AISProvenance.SYNTHETIC_DEMO_FEED,
        )
    )

    # 6. GULF_SUPPLIER_VII (MMSI 368777880) — Corridor Candidate (~4.2km away)
    for step in range(8):
        t = ref_time - timedelta(hours=1) + timedelta(minutes=step * 25)
        # Shifted by 0.038 deg North (~4.2 km)
        records.append(
            AISRecord(
                mmsi="368777880",
                timestamp=t,
                longitude=(origin_lon - 0.05) + step * 0.015,
                latitude=(origin_lat + 0.038) + step * 0.015,
                sog_knots=11.0,
                cog_degrees=45.0,
                vessel_name="GULF_SUPPLIER_VII",
                vessel_type="Offshore Supply",
                provenance=AISProvenance.SYNTHETIC_DEMO_FEED,
            )
        )

    return records
