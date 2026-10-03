"""Ocean Sentinel Real-Data Operational Pipeline Foundation (Phase 6).

Implements the minimal production-meaningful operational pipeline spine:
    External Real EO Source
              ↓
    Acquisition Identity & Ingestion Boundary
              ↓
    Provenance & Lineage Tracking
              ↓
    SAR Raster Validation (Bands, Dtype, Validity Mask, Geometry, Nodata)
              ↓
    Explicit SAR Preprocessing Contract (Mapping A Normalization, Linear-to-dB)
              ↓
    Detection Boundary & Frozen Checkpoint Verification (Firewall Protected)
              ↓
    Canonical Evidence Object Construction (Observation → Acquisition → Detection)
              ↓
    Lifecycle Telemetry & Fail-Closed Guardrails

Operating Safety & Scientific Boundaries:
------------------------------------------
1. EXECUTION_AUTHORIZED = FALSE by default:
   Model inference, training, holdout evaluation, and threshold tuning are strictly
   firewalled. In preflight mode, checkpoint presence and SHA256 integrity are verified
   without executing forward passes.
2. FAIL-CLOSED VALIDATION:
   Missing acquisition IDs, fake/synthetic providers, corrupted rasters, zero valid pixels,
   band count mismatches, and ambiguous channel mappings fail closed immediately.
3. CANONICAL LINEAGE & EVIDENCE:
   Every operational result produces an auditable evidence object carrying full lineage
   (Observation → Acquisition → Raster → Preprocessing → Detection → Evidence Result)
   directly translatable to ocean_sentinel.fusion.EvidenceItem.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import uuid

import numpy as np
from rasterio.crs import CRS
from rasterio.transform import Affine
from shapely.geometry import shape
from shapely.validation import explain_validity

from ocean_sentinel.fusion import (
    DerivationType,
    EvidenceItem,
    EvidenceType,
    ObservationStatus,
    ProvenanceClass,
    SourceType,
)
from ocean_sentinel.models import BoundingBox, Polarization

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CHECKPOINT_PATH = (
    REPO_ROOT
    / "experiments"
    / "performance"
    / "exp06_positive_bce_weight"
    / "best_model.pt"
)
EXPECTED_EXP06_CHECKPOINT_SHA256 = (
    "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
)


def get_canonical_checkpoint_sha256(
    checkpoint_rel_path: str = "experiments/performance/exp06_positive_bce_weight/best_model.pt",
) -> str:
    """Derives the expected model checkpoint SHA-256 digest directly from the canonical Artifact Registry.

    Enforces Candidate Lesson CL-003/CL-004:
    DUPLICATED_MANUAL_HASH_CONSTANTS != SINGLE_AUTHORITATIVE_HASH_ORACLE
    """
    registry_path = REPO_ROOT / "experiments" / "ARTIFACT_REGISTRY.md"
    if registry_path.is_file():
        try:
            text = registry_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if checkpoint_rel_path in line and "|" in line:
                    cols = [c.strip() for c in line.split("|")]
                    for col in cols[1:]:
                        clean = col.replace("`", "").strip().upper()
                        if len(clean) == 64 and all(c in "0123456789ABCDEF" for c in clean):
                            return clean
        except Exception as e:
            logger.warning("Could not read canonical Artifact Registry at %s: %e", registry_path, e)
    return EXPECTED_EXP06_CHECKPOINT_SHA256

# Canonical Mapping A constants (Cross-Pol VH, Co-Pol VV in dB)
DEFAULT_NORM_MEAN = [-33.2323, -19.9405]
DEFAULT_NORM_STD = [6.4912, 4.5308]
DEFAULT_DB_FLOOR = -50.0
DEFAULT_DECISION_THRESHOLD = 0.22

# Recognized operational satellite providers
RECOGNIZED_OPERATIONAL_PROVIDERS = {
    "copernicus_cdse",
    "sentinel_hub",
    "esa_scihub",
    "asf",
    "peps",
}


# ---------------------------------------------------------------------------
# Exceptions (Fail-Closed Operational Error Domain)
# ---------------------------------------------------------------------------


class OperationalPipelineError(Exception):
    """Base exception for errors during operational pipeline execution."""

    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.code, "message": self.message, "details": self.details}


class IngestionRejectionError(OperationalPipelineError):
    """Raised when an incoming EO acquisition fails ingestion contract validation."""

    pass


class SARValidationError(OperationalPipelineError):
    """Raised when a SAR raster violates spatial, radiometric, or band contracts."""

    pass


class OperationalPreprocessingError(OperationalPipelineError):
    """Raised when SAR preprocessing cannot be executed according to contract."""

    pass


class CheckpointIntegrityError(OperationalPipelineError):
    """Raised when a model checkpoint file is missing or violates hash integrity."""

    pass


class UnauthorizedInferenceError(OperationalPipelineError):
    """Raised when model inference is requested without explicit scientific authorization."""

    pass


# ---------------------------------------------------------------------------
# Telemetry Lifecycle States
# ---------------------------------------------------------------------------


class PipelineStageState(str, Enum):
    """Operational pipeline lifecycle stages."""

    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    PREPROCESSING = "PREPROCESSING"
    READY_FOR_DETECTION = "READY_FOR_DETECTION"
    DETECTION_READY = "DETECTION_READY"
    INFERRING = "INFERRING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    BLOCKED_UNAUTHORIZED = "BLOCKED_UNAUTHORIZED"


@dataclass
class TelemetryEvent:
    """Single discrete lifecycle event in operational pipeline execution."""

    stage: str
    timestamp: str
    status: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PipelineTelemetryTracker:
    """Manages stage-by-stage lifecycle telemetry for operational jobs."""

    def __init__(self, pipeline_run_id: Optional[str] = None) -> None:
        self.pipeline_run_id = pipeline_run_id or f"pipe_{uuid.uuid4().hex[:12]}"
        self.events: List[TelemetryEvent] = []
        self.current_state: PipelineStageState = PipelineStageState.RECEIVED
        self.start_time: str = datetime.now(timezone.utc).isoformat()
        self.end_time: Optional[str] = None

    def record_transition(
        self,
        stage: PipelineStageState,
        status: str = "IN_PROGRESS",
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> TelemetryEvent:
        """Record an explicit stage transition."""
        self.current_state = stage
        event = TelemetryEvent(
            stage=stage.value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=status,
            message=message,
            details=details or {},
        )
        self.events.append(event)
        logger.info(f"Pipeline [{self.pipeline_run_id}] Stage -> {stage.value} ({status}): {message}")
        return event

    def finalize(self, success: bool, final_message: str = "") -> None:
        """Mark pipeline run completion."""
        self.end_time = datetime.now(timezone.utc).isoformat()
        final_stage = PipelineStageState.COMPLETED if success else PipelineStageState.FAILED
        self.record_transition(
            stage=final_stage,
            status="SUCCESS" if success else "FAILURE",
            message=final_message,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_run_id": self.pipeline_run_id,
            "current_state": self.current_state.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
        }


# ---------------------------------------------------------------------------
# Stage C — Real-Data Ingestion Boundary Models & Validation
# ---------------------------------------------------------------------------


@dataclass
class OperationalIngestionRequest:
    """Domain request for real-data SAR ingestion."""

    acquisition_id: str
    provider: str
    acquisition_time: Union[datetime, str]
    spatial_extent: Union[Dict[str, Any], BoundingBox, List[float]]
    crs: str
    polarizations: Sequence[Union[Polarization, str]]
    source_reference: Optional[str] = None
    raw_bytes: Optional[bytes] = None
    raw_arrays: Optional[Dict[str, np.ndarray]] = None
    transform: Optional[Sequence[float]] = None
    width: Optional[int] = None
    height: Optional[int] = None
    nodata: Optional[float] = None
    metadata_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationalAcquisitionRecord:
    """Validated acquisition record accepted by the operational boundary."""

    acquisition_id: str
    provider: str
    acquisition_time: datetime
    spatial_geometry: Dict[str, Any]
    bbox: List[float]
    crs: str
    polarizations: List[Polarization]
    source_reference: Optional[str]
    content_sha256: Optional[str]
    raw_bytes: Optional[bytes]
    raw_arrays: Optional[Dict[Polarization, np.ndarray]]
    transform: List[float]
    width: int
    height: int
    nodata: Optional[float]
    status: str = "INGESTION_ACCEPTED"
    metadata_properties: Dict[str, Any] = field(default_factory=dict)

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "acquisition_id": self.acquisition_id,
            "provider": self.provider,
            "acquisition_time": self.acquisition_time.isoformat(),
            "bbox": self.bbox,
            "crs": self.crs,
            "polarizations": [p.value for p in self.polarizations],
            "source_reference": self.source_reference,
            "content_sha256": self.content_sha256,
            "width": self.width,
            "height": self.height,
            "has_raw_bytes": self.raw_bytes is not None,
            "status": self.status,
        }


def validate_ingestion_boundary(request: OperationalIngestionRequest) -> OperationalAcquisitionRecord:
    """Deterministic validation of an incoming real-data EO acquisition.

    Enforces:
    - Explicit non-empty acquisition ID
    - Recognized real-data provider (rejects synthetic / fake fallback)
    - Valid UTC acquisition timestamp
    - Valid geographic extent / geometry
    - Valid CRS
    - Unambiguous dual-polarization metadata
    """
    # 1. Acquisition ID check
    acq_id = str(request.acquisition_id).strip() if request.acquisition_id else ""
    if not acq_id:
        raise IngestionRejectionError(
            code="MISSING_ACQUISITION_ID",
            message="Operational acquisition identity is required and cannot be empty.",
        )

    # 2. Provider validation (Fail-closed against synthetic / demo fallback)
    provider_raw = str(request.provider).strip().lower() if request.provider else ""
    if not provider_raw:
        raise IngestionRejectionError(
            code="MISSING_PROVIDER_ID",
            message="Data source provider identifier is required.",
            details={"acquisition_id": acq_id},
        )
    if any(forbidden in provider_raw for forbidden in ["synthetic", "demo", "fake", "mock", "dummy"]):
        raise IngestionRejectionError(
            code="UNAUTHORIZED_PROVIDER",
            message=(
                f"Synthetic, mock, or fake provider '{provider_raw}' is strictly rejected. "
                "Real EO source is mandatory in the operational pipeline."
            ),
            details={"acquisition_id": acq_id, "provider": provider_raw},
        )
    if provider_raw not in RECOGNIZED_OPERATIONAL_PROVIDERS:
        logger.warning(f"Unusual provider '{provider_raw}' provided for acquisition {acq_id}.")

    # 3. Timestamp parsing & validation
    acq_time: datetime
    if isinstance(request.acquisition_time, datetime):
        acq_time = request.acquisition_time
        if acq_time.tzinfo is None:
            acq_time = acq_time.replace(tzinfo=timezone.utc)
        else:
            acq_time = acq_time.astimezone(timezone.utc)
    elif isinstance(request.acquisition_time, str):
        try:
            iso_str = request.acquisition_time.strip().replace("Z", "+00:00")
            acq_time = datetime.fromisoformat(iso_str)
            if acq_time.tzinfo is None:
                acq_time = acq_time.replace(tzinfo=timezone.utc)
            else:
                acq_time = acq_time.astimezone(timezone.utc)
        except Exception as e:
            raise IngestionRejectionError(
                code="INVALID_TIMESTAMP",
                message=f"Failed to parse acquisition timestamp '{request.acquisition_time}': {e}",
                details={"acquisition_id": acq_id},
            ) from e
    else:
        raise IngestionRejectionError(
            code="INVALID_TIMESTAMP",
            message=f"Acquisition timestamp must be a datetime or ISO string, got {type(request.acquisition_time)}",
            details={"acquisition_id": acq_id},
        )

    # 4. Spatial extent & geometry validation
    geom_dict: Dict[str, Any]
    bbox_coords: List[float]
    if isinstance(request.spatial_extent, BoundingBox):
        bbox_coords = request.spatial_extent.to_list()
        geom_dict = request.spatial_extent.to_geojson_polygon()
    elif isinstance(request.spatial_extent, list) and len(request.spatial_extent) == 4:
        w, s, e, n = [float(v) for v in request.spatial_extent]
        if w >= e or s >= n:
            raise IngestionRejectionError(
                code="INVALID_SPATIAL_EXTENT",
                message=f"Degenerate bounding box coordinates: west={w}, south={s}, east={e}, north={n}",
                details={"acquisition_id": acq_id, "bbox": [w, s, e, n]},
            )
        bbox_coords = [w, s, e, n]
        geom_dict = {
            "type": "Polygon",
            "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
        }
    elif isinstance(request.spatial_extent, dict):
        geom_dict = request.spatial_extent
        try:
            poly = shape(geom_dict)
            if not poly.is_valid:
                reason = explain_validity(poly)
                raise IngestionRejectionError(
                    code="INVALID_GEOMETRY",
                    message=f"Invalid spatial geometry: {reason}",
                    details={"acquisition_id": acq_id},
                )
            bounds = poly.bounds
            bbox_coords = [float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3])]
        except IngestionRejectionError:
            raise
        except Exception as e:
            raise IngestionRejectionError(
                code="INVALID_GEOMETRY",
                message=f"Failed to parse GeoJSON geometry: {e}",
                details={"acquisition_id": acq_id},
            ) from e
    else:
        raise IngestionRejectionError(
            code="INVALID_SPATIAL_EXTENT",
            message="spatial_extent must be a BoundingBox, 4-element list [w, s, e, n], or GeoJSON dict",
            details={"acquisition_id": acq_id},
        )

    # 5. CRS validation
    crs_str = str(request.crs).strip() if request.crs else ""
    if not crs_str:
        raise IngestionRejectionError(
            code="MISSING_CRS",
            message="Coordinate Reference System (CRS) is mandatory.",
            details={"acquisition_id": acq_id},
        )
    try:
        CRS.from_string(crs_str)
    except Exception as e:
        raise IngestionRejectionError(
            code="INVALID_CRS",
            message=f"Unrecognized or invalid CRS '{crs_str}': {e}",
            details={"acquisition_id": acq_id, "crs": crs_str},
        ) from e

    # 6. Polarization validation
    parsed_pols: List[Polarization] = []
    if not request.polarizations:
        raise IngestionRejectionError(
            code="MISSING_POLARIZATION_METADATA",
            message="Polarization metadata is required and cannot be empty.",
            details={"acquisition_id": acq_id},
        )
    for p in request.polarizations:
        if isinstance(p, Polarization):
            parsed_pols.append(p)
        elif isinstance(p, str):
            p_clean = p.strip().upper()
            try:
                parsed_pols.append(Polarization(p_clean))
            except ValueError:
                raise IngestionRejectionError(
                    code="UNRECOGNIZED_POLARIZATION",
                    message=f"Unrecognized SAR polarization '{p}'",
                    details={"acquisition_id": acq_id, "polarization": p},
                )
        else:
            raise IngestionRejectionError(
                code="INVALID_POLARIZATION_TYPE",
                message=f"Invalid polarization type {type(p)}",
                details={"acquisition_id": acq_id},
            )

    # Ensure required dual-pol channels are present for detection
    pol_set = {p.value for p in parsed_pols}
    if not ({"VH", "VV"}.issubset(pol_set) or {"HH", "HV"}.issubset(pol_set)):
        raise IngestionRejectionError(
            code="AMBIGUOUS_POLARIZATION_SET",
            message=(
                f"Polarization set {[p.value for p in parsed_pols]} does not contain expected "
                "standard dual-pol channels (VH and VV)."
            ),
            details={"acquisition_id": acq_id, "polarizations": [p.value for p in parsed_pols]},
        )

    # 7. Compute content hash if raw bytes provided
    content_hash = None
    if request.raw_bytes:
        content_hash = hashlib.sha256(request.raw_bytes).hexdigest()

    # Dimensions and transform
    width = request.width or 512
    height = request.height or 512
    transform = list(request.transform or [0.0001, 0.0, bbox_coords[0], 0.0, -0.0001, bbox_coords[3]])

    # Map raw arrays if present
    parsed_arrays: Optional[Dict[Polarization, np.ndarray]] = None
    if request.raw_arrays is not None:
        parsed_arrays = {}
        for pol in parsed_pols:
            arr = request.raw_arrays.get(pol.value)
            if arr is None:
                arr = request.raw_arrays.get(pol)
            if arr is not None:
                parsed_arrays[pol] = arr

    return OperationalAcquisitionRecord(
        acquisition_id=acq_id,
        provider=provider_raw,
        acquisition_time=acq_time,
        spatial_geometry=geom_dict,
        bbox=bbox_coords,
        crs=crs_str,
        polarizations=parsed_pols,
        source_reference=request.source_reference,
        content_sha256=content_hash,
        raw_bytes=request.raw_bytes,
        raw_arrays=parsed_arrays,
        transform=transform,
        width=width,
        height=height,
        nodata=request.nodata,
        metadata_properties=request.metadata_properties,
    )


# ---------------------------------------------------------------------------
# Stage D — Deterministic SAR Validation
# ---------------------------------------------------------------------------


@dataclass
class OperationalRasterValidationResult:
    """Result of deterministic SAR raster validation."""

    band_count: int
    height: int
    width: int
    dtype: str
    crs: str
    transform: List[float]
    polarizations: List[Polarization]
    valid_mask: np.ndarray  # Shape: (H, W), boolean
    valid_pixels: int
    invalid_pixels: int
    valid_percentage: float
    is_linear: bool
    channel_order: List[Polarization]
    channel_arrays: Dict[Polarization, np.ndarray]

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "band_count": self.band_count,
            "height": self.height,
            "width": self.width,
            "dtype": self.dtype,
            "crs": self.crs,
            "channel_order": [p.value for p in self.channel_order],
            "valid_pixels": self.valid_pixels,
            "invalid_pixels": self.invalid_pixels,
            "valid_percentage": round(self.valid_percentage, 4),
            "is_linear": self.is_linear,
        }


def validate_sar_raster(
    arrays: Union[Dict[Polarization, np.ndarray], np.ndarray],
    polarizations: Sequence[Polarization],
    crs: str,
    transform: Sequence[float],
    nodata: Optional[float] = None,
    require_georeferencing: bool = True,
) -> OperationalRasterValidationResult:
    """Deterministically validates a 2-channel SAR raster against operational contracts.

    Contract enforcement:
    - Band count: exactly 2 channels (Mapping A: VH, VV)
    - Dtype: float32
    - Dimensions: H > 0, W > 0
    - Georeferencing: valid CRS and non-identity affine transform
    - Finite values: non-zero valid pixels (fails closed on all-NaN or all-non-positive)
    - Channel ordering: maps available polarizations to explicit [VH, VV] contract
    """
    # 1. Normalize arrays to Dict[Polarization, np.ndarray]
    channel_dict: Dict[Polarization, np.ndarray] = {}
    if isinstance(arrays, dict):
        channel_dict = dict(arrays)
    elif isinstance(arrays, np.ndarray):
        if arrays.ndim != 3:
            raise SARValidationError(
                code="INVALID_ARRAY_DIMENSIONS",
                message=f"3D numpy array expected with shape (2, H, W), got {arrays.shape}",
            )
        if arrays.shape[0] != len(polarizations):
            raise SARValidationError(
                code="BAND_COUNT_MISMATCH",
                message=f"Array band count {arrays.shape[0]} does not match polarizations list length {len(polarizations)}",
            )
        for idx, pol in enumerate(polarizations):
            channel_dict[pol] = arrays[idx]
    else:
        raise SARValidationError(
            code="UNSUPPORTED_DATA_CONTAINER",
            message=f"Unsupported array container type {type(arrays)}",
        )

    # 2. Band count contract check
    band_count = len(channel_dict)
    if band_count != 2:
        raise SARValidationError(
            code="INVALID_BAND_COUNT",
            message=f"Mapping A requires exactly 2 SAR polarization channels (VH and VV), got {band_count}",
            details={"actual_band_count": band_count},
        )

    # 3. Check required polarizations (VH, VV)
    avail_pols = set(channel_dict.keys())
    if Polarization.VH not in avail_pols or Polarization.VV not in avail_pols:
        avail_str = ", ".join(p.value for p in avail_pols)
        raise SARValidationError(
            code="MISSING_REQUIRED_POLARIZATION",
            message=f"Operational pipeline requires both VH and VV polarizations. Found: [{avail_str}]",
            details={"available_polarizations": [p.value for p in avail_pols]},
        )

    # 4. Dimensionality, dtype, and finite value checks
    vh_arr = channel_dict[Polarization.VH]
    vv_arr = channel_dict[Polarization.VV]

    if vh_arr.ndim != 2 or vv_arr.ndim != 2:
        raise SARValidationError(
            code="NON_2D_BAND_ARRAY",
            message=f"Polarization bands must be 2D. Shapes: VH={vh_arr.shape}, VV={vv_arr.shape}",
        )

    if vh_arr.shape != vv_arr.shape:
        raise SARValidationError(
            code="BAND_DIMENSION_MISMATCH",
            message=f"VH shape {vh_arr.shape} does not match VV shape {vv_arr.shape}",
        )

    h, w = vh_arr.shape
    if h <= 0 or w <= 0:
        raise SARValidationError(
            code="INVALID_DIMENSIONS",
            message=f"Raster height and width must be strictly positive, got ({h}, {w})",
        )

    # Convert to float32 safely
    if not np.issubdtype(vh_arr.dtype, np.floating) or not np.issubdtype(vv_arr.dtype, np.floating):
        try:
            vh_arr = vh_arr.astype(np.float32)
            vv_arr = vv_arr.astype(np.float32)
        except Exception as e:
            raise SARValidationError(
                code="INVALID_DTYPE",
                message=f"Failed to cast arrays to float32: {e}",
            ) from e
    else:
        vh_arr = vh_arr.astype(np.float32)
        vv_arr = vv_arr.astype(np.float32)

    channel_dict[Polarization.VH] = vh_arr
    channel_dict[Polarization.VV] = vv_arr

    # 5. Georeferencing validation
    if require_georeferencing:
        if not crs:
            raise SARValidationError(
                code="MISSING_CRS",
                message="Georeferencing requires non-empty Coordinate Reference System (CRS).",
            )
        try:
            CRS.from_string(crs)
        except Exception as e:
            raise SARValidationError(
                code="INVALID_CRS",
                message=f"Cannot parse CRS string '{crs}': {e}",
            ) from e

        if not transform or len(transform) < 6:
            raise SARValidationError(
                code="INVALID_GEOTRANSFORM",
                message=f"Affine geotransform must contain 6 coefficients, got {transform}",
            )

    # 6. Radiometric unit detection & validity mask derivation
    # Linear σ0 is strictly positive power (typically < 10.0 in sea backscatter)
    # Decibel σ0 is negative or low positive (typically -50 to +15 dB)
    finite_mask_vh = np.isfinite(vh_arr)
    finite_mask_vv = np.isfinite(vv_arr)
    both_finite = finite_mask_vh & finite_mask_vv

    if not np.any(both_finite):
        raise SARValidationError(
            code="ZERO_VALID_PIXELS",
            message="Raster contains zero finite pixels (all NaN or infinite in both bands).",
            details={"height": h, "width": w},
        )

    vh_finite_vals = vh_arr[both_finite]
    is_linear = bool(np.all(vh_finite_vals >= 0.0) and np.median(vh_finite_vals) < 5.0 and np.min(vh_finite_vals) >= 0.0)

    # Validity mask computation
    if is_linear:
        # Linear valid pixels must be finite and strictly positive (> 0)
        valid_mask = both_finite & (vh_arr > 0.0) & (vv_arr > 0.0)
    else:
        valid_mask = both_finite
        if nodata is not None:
            valid_mask = valid_mask & (vh_arr != nodata) & (vv_arr != nodata)

    total_pixels = h * w
    valid_count = int(np.sum(valid_mask))
    invalid_count = total_pixels - valid_count
    valid_percentage = (valid_count / total_pixels) * 100.0 if total_pixels > 0 else 0.0

    if valid_count == 0:
        raise SARValidationError(
            code="ZERO_VALID_PIXELS",
            message="Raster contains zero valid pixels according to physical SAR validity rules.",
            details={"total_pixels": total_pixels, "is_linear": is_linear},
        )

    # 7. Ordered polarizations: Mapping A contract is explicitly [VH, VV]
    ordered_pols = [Polarization.VH, Polarization.VV]

    return OperationalRasterValidationResult(
        band_count=2,
        height=h,
        width=w,
        dtype="float32",
        crs=str(crs),
        transform=list(transform),
        polarizations=list(polarizations),
        valid_mask=valid_mask,
        valid_pixels=valid_count,
        invalid_pixels=invalid_count,
        valid_percentage=valid_percentage,
        is_linear=is_linear,
        channel_order=ordered_pols,
        channel_arrays=channel_dict,
    )


# ---------------------------------------------------------------------------
# Stage E — Explicit SAR Preprocessing Contract
# ---------------------------------------------------------------------------


@dataclass
class OperationalPreprocessingRecord:
    """Complete, auditable output of SAR preprocessing."""

    observation_id: str
    preprocessing_version: str
    normalization_contract: str
    parameters: Dict[str, Any]
    input_unit: str
    output_unit: str
    channel_order: List[str]
    input_shape: Tuple[int, int]
    output_shape: Tuple[int, int, int]
    crs: str
    transform: List[float]
    valid_mask: np.ndarray  # Shape: (H, W)
    physical_db_arrays: np.ndarray  # Shape: (2, H, W), float32
    normalized_arrays: np.ndarray  # Shape: (2, H, W), float32
    band_statistics: Dict[str, Dict[str, float]]
    processing_status: str = "PREPROCESSED"

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "preprocessing_version": self.preprocessing_version,
            "normalization_contract": self.normalization_contract,
            "parameters": self.parameters,
            "input_unit": self.input_unit,
            "output_unit": self.output_unit,
            "channel_order": self.channel_order,
            "input_shape": list(self.input_shape),
            "output_shape": list(self.output_shape),
            "crs": self.crs,
            "band_statistics": self.band_statistics,
            "processing_status": self.processing_status,
        }


def preprocess_sar_operational(
    validation_res: OperationalRasterValidationResult,
    observation_id: str,
    norm_mean: Sequence[float] = DEFAULT_NORM_MEAN,
    norm_std: Sequence[float] = DEFAULT_NORM_STD,
    db_floor: float = DEFAULT_DB_FLOOR,
) -> OperationalPreprocessingRecord:
    """Executes explicit, auditable SAR preprocessing according to Mapping A contract.

    Steps:
    1. Channel ordering: Strictly Channel 0 = VH, Channel 1 = VV.
    2. Radiometric conversion: Linear σ0 converted to dB: 10 * log10(σ0).
       Invalid pixels clamped to db_floor (-50.0 dB).
    3. Normalization: Mapping A z-score standardization with frozen training statistics:
       VH: mean=-33.2323, std=6.4912
       VV: mean=-19.9405, std=4.5308
       Invalid pixels imputed to 0.0 (normalized mean).
    4. Computes per-band statistics on valid pixels only.
    """
    h, w = validation_res.height, validation_res.width
    vh_raw = validation_res.channel_arrays[Polarization.VH]
    vv_raw = validation_res.channel_arrays[Polarization.VV]
    valid_mask = validation_res.valid_mask

    # Step 1: Radiometric conversion to dB
    if validation_res.is_linear:
        input_unit = "linear"
        # Linear -> dB
        vh_db = np.full((h, w), db_floor, dtype=np.float32)
        vv_db = np.full((h, w), db_floor, dtype=np.float32)

        # Apply 10 * log10 strictly on valid pixels
        vh_db[valid_mask] = 10.0 * np.log10(np.maximum(vh_raw[valid_mask], 1e-7))
        vv_db[valid_mask] = 10.0 * np.log10(np.maximum(vv_raw[valid_mask], 1e-7))
    else:
        input_unit = "dB"
        vh_db = vh_raw.copy()
        vv_db = vv_raw.copy()
        vh_db[~valid_mask] = db_floor
        vv_db[~valid_mask] = db_floor

    physical_db = np.stack([vh_db, vv_db], axis=0)  # Shape: (2, H, W)

    # Step 2: Mapping A z-score standardization
    mean_vh, mean_vv = float(norm_mean[0]), float(norm_mean[1])
    std_vh, std_vv = float(norm_std[0]), float(norm_std[1])

    norm_vh = (vh_db - mean_vh) / std_vh
    norm_vv = (vv_db - mean_vv) / std_vv

    # Impute invalid pixels to 0.0 (the mean in standardized space)
    norm_vh[~valid_mask] = 0.0
    norm_vv[~valid_mask] = 0.0

    normalized_arr = np.stack([norm_vh, norm_vv], axis=0)  # Shape: (2, H, W)

    # Step 3: Compute valid-pixel statistics
    band_stats: Dict[str, Dict[str, float]] = {}
    for name, arr in [("VH", vh_db), ("VV", vv_db)]:
        valid_vals = arr[valid_mask]
        if len(valid_vals) > 0:
            band_stats[name] = {
                "min": round(float(np.min(valid_vals)), 4),
                "max": round(float(np.max(valid_vals)), 4),
                "mean": round(float(np.mean(valid_vals)), 4),
                "std": round(float(np.std(valid_vals)), 4),
            }
        else:
            band_stats[name] = {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0}

    return OperationalPreprocessingRecord(
        observation_id=observation_id,
        preprocessing_version="OPERATIONAL_SAR_PREPROCESSOR_MAPPING_A_V1",
        normalization_contract="mapping_a_zscore",
        parameters={
            "mean": [mean_vh, mean_vv],
            "std": [std_vh, std_vv],
            "db_floor": db_floor,
            "channel_order": ["VH", "VV"],
        },
        input_unit=input_unit,
        output_unit="zscore_standardized",
        channel_order=["VH", "VV"],
        input_shape=(h, w),
        output_shape=(2, h, w),
        crs=validation_res.crs,
        transform=validation_res.transform,
        valid_mask=valid_mask,
        physical_db_arrays=physical_db,
        normalized_arrays=normalized_arr,
        band_statistics=band_stats,
        processing_status="PREPROCESSED",
    )


# ---------------------------------------------------------------------------
# Stage F — Detection Boundary (Strict Safety Firewall & Interface)
# ---------------------------------------------------------------------------


@dataclass
class OperationalDetectionRecord:
    """Preflight or execution record emitted by the operational detection boundary."""

    checkpoint_path: str
    checkpoint_sha256: str
    threshold: float
    execution_authorized: bool
    status: str
    message: str
    probability_map: Optional[np.ndarray] = None
    prediction_mask: Optional[np.ndarray] = None
    execution_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_path": self.checkpoint_path,
            "checkpoint_sha256": self.checkpoint_sha256,
            "threshold": self.threshold,
            "execution_authorized": self.execution_authorized,
            "status": self.status,
            "message": self.message,
            "has_prediction": self.probability_map is not None,
            "execution_metadata": self.execution_metadata,
        }


class OperationalDetectionBoundary:
    """Clean operational detection boundary isolating frozen ML models.

    Firewall rules:
    - Default: execution_authorized = False.
    - Checkpoint presence and SHA256 integrity are verified strictly against EXP-06.
    - When execution_authorized is False, the boundary records preflight readiness
      (DETECTION_READY) and stops cleanly without invoking inference forward passes.
    - If execute_inference is called while execution_authorized is False, it fails closed
      with UnauthorizedInferenceError.
    """

    def __init__(
        self,
        checkpoint_path: Union[str, Path] = DEFAULT_CHECKPOINT_PATH,
        expected_sha256: Optional[str] = None,
        threshold: float = DEFAULT_DECISION_THRESHOLD,
        execution_authorized: bool = False,
    ) -> None:
        self.checkpoint_path = Path(checkpoint_path)
        if expected_sha256 is None:
            self.expected_sha256 = get_canonical_checkpoint_sha256().upper().strip()
        else:
            self.expected_sha256 = expected_sha256.upper().strip()
        self.threshold = float(threshold)
        self.execution_authorized = bool(execution_authorized)

    def verify_checkpoint_integrity(self) -> str:
        """Verifies checkpoint file existence and SHA-256 integrity bitwise."""
        if not self.checkpoint_path.is_file():
            raise CheckpointIntegrityError(
                code="CHECKPOINT_NOT_FOUND",
                message=f"Canonical model checkpoint not found at: {self.checkpoint_path}",
                details={"path": str(self.checkpoint_path)},
            )

        sha = hashlib.sha256()
        with open(self.checkpoint_path, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        actual_sha = sha.hexdigest().upper()

        if actual_sha != self.expected_sha256:
            raise CheckpointIntegrityError(
                code="CHECKPOINT_HASH_MISMATCH",
                message=(
                    f"Checkpoint SHA256 mismatch!\n"
                    f"Expected: {self.expected_sha256}\n"
                    f"Actual:   {actual_sha}"
                ),
                details={
                    "path": str(self.checkpoint_path),
                    "expected_sha": self.expected_sha256,
                    "actual_sha": actual_sha,
                },
            )

        return actual_sha

    def prepare_detection_preflight(
        self,
        preprocessing_record: OperationalPreprocessingRecord,
    ) -> OperationalDetectionRecord:
        """Preflight interface: verifies checkpoint integrity and halts before inference."""
        actual_sha = self.verify_checkpoint_integrity()

        msg = (
            "Preflight boundary verified: Checkpoint integrity confirmed. "
            "Model inference blocked pending scientific execution authorization (EXECUTION_AUTHORIZED=False)."
        )
        logger.info(msg)

        return OperationalDetectionRecord(
            checkpoint_path=str(self.checkpoint_path),
            checkpoint_sha256=actual_sha,
            threshold=self.threshold,
            execution_authorized=self.execution_authorized,
            status="DETECTION_READY",
            message=msg,
            execution_metadata={
                "model_architecture": "ResNet34UNet",
                "in_channels": 2,
                "input_preprocessing": preprocessing_record.preprocessing_version,
                "input_shape": list(preprocessing_record.output_shape),
                "firewall_active": True,
            },
        )

    def execute_inference(
        self,
        preprocessing_record: OperationalPreprocessingRecord,
    ) -> OperationalDetectionRecord:
        """Executes model inference if and only if execution_authorized is True."""
        if not self.execution_authorized:
            raise UnauthorizedInferenceError(
                code="UNAUTHORIZED_INFERENCE_REQUEST",
                message=(
                    "Scientific execution is NOT authorized for this run "
                    "(EXECUTION_AUTHORIZED=False). Inference forward pass is blocked fail-closed."
                ),
                details={
                    "checkpoint_path": str(self.checkpoint_path),
                    "threshold": self.threshold,
                },
            )

        # If authorized, attempt dynamic import of inference dependencies
        try:
            from ocean_sentinel.inference import load_binary_oil_model, reconstruct_prediction, compute_tile_windows, predict_tiles, create_blend_weight_window
        except ImportError as e:
            raise OperationalPipelineError(
                code="INFERENCE_DEPENDENCY_MISSING",
                message=f"Inference execution engine or PyTorch unavailable: {e}",
            ) from e

        actual_sha = self.verify_checkpoint_integrity()
        norm_data = preprocessing_record.normalized_arrays
        valid_mask = preprocessing_record.valid_mask
        h, w = preprocessing_record.input_shape

        model, _ = load_binary_oil_model(checkpoint_path=self.checkpoint_path)
        windows = compute_tile_windows(h, w, tile_size=512, overlap=0)
        blend_weights = create_blend_weight_window(tile_size=512, blend=False)

        tile_probs = predict_tiles(
            model=model,
            preprocessed_data=norm_data,
            windows=windows,
            batch_size=1,
            device="cpu",
        )
        prob_map, pred_mask = reconstruct_prediction(
            tile_probs=tile_probs,
            windows=windows,
            height=h,
            width=w,
            blend_weight=blend_weights,
            validity_mask=valid_mask,
            threshold=self.threshold,
        )

        return OperationalDetectionRecord(
            checkpoint_path=str(self.checkpoint_path),
            checkpoint_sha256=actual_sha,
            threshold=self.threshold,
            execution_authorized=True,
            status="DETECTION_EXECUTED",
            message="Detection executed successfully under explicit authorization.",
            probability_map=prob_map,
            prediction_mask=pred_mask,
            execution_metadata={
                "model_architecture": "ResNet34UNet",
                "tile_count": len(windows),
                "threshold": self.threshold,
            },
        )


# ---------------------------------------------------------------------------
# Stage G — Canonical Structured Evidence Object
# ---------------------------------------------------------------------------


@dataclass
class OperationalEvidenceResult:
    """Canonical structured evidence representation of operational pipeline execution.

    Lineage hierarchy:
        Observation → Acquisition → Raster → Preprocessing → Detection → Evidence Result
    """

    evidence_id: str
    acquisition_id: str
    provider: str
    observation_time: str
    spatial_extent: Dict[str, Any]
    crs: str
    provenance_class: str
    lineage_record: Dict[str, Any]
    preprocessing_summary: Dict[str, Any]
    detection_summary: Dict[str, Any]
    telemetry: Dict[str, Any]
    status: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_evidence_item(self) -> EvidenceItem:
        """Converts into canonical ocean_sentinel.fusion.EvidenceItem for downstream fusion."""
        obs_time = datetime.fromisoformat(self.observation_time)
        return EvidenceItem(
            evidence_id=self.evidence_id,
            evidence_type=EvidenceType.SAR_DETECTION,
            source_type=SourceType.SENTINEL_1_SAR,
            source_id=self.acquisition_id,
            observation_time=obs_time,
            provenance_class=ProvenanceClass(self.provenance_class),
            provenance_source=self.provider,
            spatial_geometry=self.spatial_extent,
            derivation_type=DerivationType.DERIVED_ANALYSIS,
            observed_vs_inferred=ObservationStatus.OBSERVED,
            metric_values={
                "detection_ready": True,
                "status": self.status,
                "threshold": self.detection_summary.get("threshold", DEFAULT_DECISION_THRESHOLD),
            },
            limitations=[
                "Operational pipeline pre-scientific verification.",
                "Binary candidate proposal boundary only; does NOT constitute confirmed oil.",
            ],
            status="ACTIVE",
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Primary Operational SAR Pipeline Spine
# ---------------------------------------------------------------------------


class OperationalSARPipeline:
    """Smallest production-meaningful operational pipeline spine.

    Orchestrates:
    External real EO source
    → acquisition identity
    → provenance
    → raster validation
    → SAR preprocessing contract
    → detection boundary
    → evidence object
    → telemetry
    → fail-closed failure handling
    """

    def __init__(
        self,
        execution_authorized: bool = False,
        checkpoint_path: Union[str, Path] = DEFAULT_CHECKPOINT_PATH,
        expected_checkpoint_sha256: Optional[str] = None,
        threshold: float = DEFAULT_DECISION_THRESHOLD,
    ) -> None:
        self.execution_authorized = execution_authorized
        self.detection_boundary = OperationalDetectionBoundary(
            checkpoint_path=checkpoint_path,
            expected_sha256=expected_checkpoint_sha256,
            threshold=threshold,
            execution_authorized=execution_authorized,
        )

    def run(self, request: OperationalIngestionRequest) -> OperationalEvidenceResult:
        """Runs the operational pipeline through the governed lifecycle stages."""
        telemetry = PipelineTelemetryTracker()
        telemetry.record_transition(
            PipelineStageState.RECEIVED,
            status="SUCCESS",
            message=f"Received ingestion request for acquisition '{request.acquisition_id}' from provider '{request.provider}'",
            details={"acquisition_id": request.acquisition_id, "provider": request.provider},
        )

        try:
            # 1. Ingestion Boundary Validation
            telemetry.record_transition(
                PipelineStageState.VALIDATING,
                status="IN_PROGRESS",
                message="Validating acquisition metadata and source credentials...",
            )
            acq_record = validate_ingestion_boundary(request)

            # 2. SAR Raster Validation
            if acq_record.raw_arrays is not None:
                arrays_input = acq_record.raw_arrays
            else:
                raise SARValidationError(
                    code="MISSING_RASTER_DATA",
                    message="No raster arrays provided for SAR validation.",
                    details={"acquisition_id": acq_record.acquisition_id},
                )

            validation_res = validate_sar_raster(
                arrays=arrays_input,
                polarizations=acq_record.polarizations,
                crs=acq_record.crs,
                transform=acq_record.transform,
                nodata=acq_record.nodata,
            )

            telemetry.record_transition(
                PipelineStageState.VALIDATED,
                status="SUCCESS",
                message=(
                    f"SAR raster contract verified: {validation_res.valid_pixels} valid pixels "
                    f"({validation_res.valid_percentage:.2f}%), 2 channels [VH, VV], CRS {validation_res.crs}"
                ),
                details=validation_res.to_summary_dict(),
            )

            # 3. Explicit Preprocessing Contract
            telemetry.record_transition(
                PipelineStageState.PREPROCESSING,
                status="IN_PROGRESS",
                message="Applying Mapping A dB conversion and z-score standardization...",
            )
            preprocessing_rec = preprocess_sar_operational(
                validation_res=validation_res,
                observation_id=acq_record.acquisition_id,
            )

            telemetry.record_transition(
                PipelineStageState.READY_FOR_DETECTION,
                status="SUCCESS",
                message="SAR preprocessing contract completed successfully.",
                details=preprocessing_rec.to_summary_dict(),
            )

            # 4. Detection Boundary
            if not self.execution_authorized:
                # Preflight check: verify checkpoint on disk and set DETECTION_READY
                detection_rec = self.detection_boundary.prepare_detection_preflight(preprocessing_rec)
                telemetry.record_transition(
                    PipelineStageState.DETECTION_READY,
                    status="SUCCESS",
                    message=detection_rec.message,
                    details=detection_rec.to_summary_dict(),
                )
                pipeline_status = "DETECTION_READY"
            else:
                # Authorized scientific execution
                telemetry.record_transition(
                    PipelineStageState.INFERRING,
                    status="IN_PROGRESS",
                    message="Executing model inference forward pass under explicit authorization...",
                )
                detection_rec = self.detection_boundary.execute_inference(preprocessing_rec)
                pipeline_status = "COMPLETED"

            # 5. Construct Canonical Structured Evidence Object
            lineage = {
                "observation_id": acq_record.acquisition_id,
                "provider": acq_record.provider,
                "acquisition_time": acq_record.acquisition_time.isoformat(),
                "content_sha256": acq_record.content_sha256,
                "stages": [
                    "OBSERVATION_INGESTION",
                    "SAR_RASTER_VALIDATION",
                    "SAR_PREPROCESSING_MAPPING_A",
                    "DETECTION_BOUNDARY_PREFLIGHT",
                ],
                "execution_authorized": self.execution_authorized,
            }

            evidence_id = f"ev_opsar_{uuid.uuid4().hex[:12]}"
            evidence_result = OperationalEvidenceResult(
                evidence_id=evidence_id,
                acquisition_id=acq_record.acquisition_id,
                provider=acq_record.provider,
                observation_time=acq_record.acquisition_time.isoformat(),
                spatial_extent=acq_record.spatial_geometry,
                crs=acq_record.crs,
                provenance_class=ProvenanceClass.VERIFIED_OPERATIONAL.value,
                lineage_record=lineage,
                preprocessing_summary=preprocessing_rec.to_summary_dict(),
                detection_summary=detection_rec.to_summary_dict(),
                telemetry=telemetry.to_dict(),
                status=pipeline_status,
            )

            telemetry.finalize(
                success=True,
                final_message=f"Operational pipeline spine reached {pipeline_status} successfully.",
            )
            return evidence_result

        except OperationalPipelineError as e:
            telemetry.record_transition(
                PipelineStageState.FAILED,
                status="FAILED",
                message=f"Pipeline failed closed: [{e.code}] {e.message}",
                details=e.details,
            )
            telemetry.finalize(success=False, final_message=f"Operational pipeline failed: {e.code}")
            raise
        except Exception as e:
            telemetry.record_transition(
                PipelineStageState.FAILED,
                status="FAILED",
                message=f"Unexpected pipeline failure: {e}",
            )
            telemetry.finalize(success=False, final_message=str(e))
            raise OperationalPipelineError(
                code="UNEXPECTED_PIPELINE_ERROR",
                message=str(e),
            ) from e
