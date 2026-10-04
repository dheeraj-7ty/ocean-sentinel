"""Pydantic Request and Response Schemas for Ocean Sentinel API V1.

Enforces strict input validation, security controls (anti-path-traversal),
and machine-readable response structures.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class HealthResponse(BaseModel):
    """Health endpoint response model."""

    service: str = "ocean-sentinel-backend"
    status: str = "healthy"
    api_version: str = "1.0.0"
    app_version: str = "0.1.0"
    mode_info: Dict[str, Any] = Field(
        default_factory=lambda: {
            "supported_modes": ["DEMO", "REAL_REPOSITORY", "PHYSICAL"],
            "default_mode": "DEMO",
            "physical_operational_status": "BLOCKED — AWAITING_OPERATIONAL_SOURCE",
        }
    )
    frozen_subsystems: Dict[str, str] = Field(
        default_factory=lambda: {
            "sar_inference": "FROZEN",
            "interpretation": "FROZEN",
            "temporal_change": "FROZEN",
            "drift_origin": "FROZEN",
            "ais_correlation": "FROZEN",
            "evidence_fusion": "FROZEN",
        }
    )


class CreateJobRequest(BaseModel):
    """Request schema to initialize and execute a pipeline job."""

    mode: str = Field("DEMO", description="Execution mode: 'DEMO', 'REAL_REPOSITORY', or 'PHYSICAL'")
    pipeline_type: str = Field(
        "DEMO_FUSION",
        description="Pipeline workflow type: 'DEMO_FUSION', 'ARTIFACT_FUSION', 'REAL_REPOSITORY', or 'PHYSICAL'",
    )
    scenario_id: Optional[str] = Field(
        default=None,
        description="Registered scenario identifier (e.g. 'TRUJILLO_00007_01339')",
    )
    investigation_label: Optional[str] = Field(
        default=None,
        description="Optional human-readable label for the investigation",
    )
    input_artifacts: Optional[Dict[str, str]] = Field(
        default=None,
        description="Relative path references to input artifacts (e.g. temporal_geojson, drift_geojson, ais_summary)",
    )
    spatial_tolerance_m: float = Field(
        5000.0,
        description="Spatial proximity tolerance in meters (must be > 0)",
    )
    temporal_tolerance_hours: float = Field(
        2.0,
        description="Temporal tolerance window in hours (must be > 0)",
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        val = v.strip().upper()
        if val not in ["DEMO", "REAL_REPOSITORY", "PHYSICAL"]:
            raise ValueError("mode must be 'DEMO', 'REAL_REPOSITORY', or 'PHYSICAL'")
        return val

    @field_validator("pipeline_type")
    @classmethod
    def validate_pipeline_type(cls, v: str) -> str:
        val = v.strip().upper()
        if val not in ["DEMO_FUSION", "ARTIFACT_FUSION", "REAL_REPOSITORY", "PHYSICAL"]:
            raise ValueError(
                "pipeline_type must be one of 'DEMO_FUSION', 'ARTIFACT_FUSION', 'REAL_REPOSITORY', 'PHYSICAL'"
            )
        return val

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        val = v.strip()
        if not val:
            return None
        if ".." in val or val.startswith(("/", "\\")):
            raise ValueError(f"Path traversal characters rejected in scenario_id: '{val}'")
        if any(char in val for char in [":", "*", "?", '"', "<", ">", "|"]):
            raise ValueError(f"Invalid characters in scenario_id: '{val}'")
        return val

    @field_validator("spatial_tolerance_m")
    @classmethod
    def validate_spatial_tolerance(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("spatial_tolerance_m must be a positive number greater than 0")
        if v > 500000.0:
            raise ValueError("spatial_tolerance_m exceeds maximum allowed threshold (500 km)")
        return v

    @field_validator("temporal_tolerance_hours")
    @classmethod
    def validate_temporal_tolerance(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("temporal_tolerance_hours must be a positive number greater than 0")
        if v > 168.0:
            raise ValueError("temporal_tolerance_hours exceeds maximum allowed threshold (168 hours / 7 days)")
        return v

    @field_validator("input_artifacts")
    @classmethod
    def validate_input_artifacts(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        if not v:
            return v
        for key, path_str in v.items():
            if not isinstance(path_str, str):
                raise ValueError(f"Artifact reference for '{key}' must be a string path")
            # Security: Path traversal hardening
            if ".." in path_str or path_str.startswith(("/", "\\")):
                raise ValueError(f"Path traversal characters rejected in '{key}': '{path_str}'")
            if any(char in path_str for char in [":", "*", "?", '"', "<", ">", "|"]):
                raise ValueError(f"Invalid path characters in '{key}': '{path_str}'")
        return v


class JobLinks(BaseModel):
    """Hypermedia navigation links for a job."""

    self: str
    artifacts: str
    result: str


class JobResponse(BaseModel):
    """Complete machine-readable job state response."""

    job_id: str
    mode: str
    pipeline_type: str
    status: str
    scenario_id: Optional[str] = None
    investigation_label: Optional[str] = None
    current_stage: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    requested_config: Dict[str, Any] = Field(default_factory=dict)
    stage_status: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[Dict[str, Any]] = None
    limitations: List[str] = Field(default_factory=list)
    links: JobLinks


class ScenarioResponse(BaseModel):
    """Details for a registered real repository scenario."""

    scenario_id: str
    label: str
    dataset: str
    scene_pair: List[str]
    region: str
    centroid: List[float]
    event_id: str
    artifacts: Dict[str, str]
    acquisition_timestamps: Dict[str, str]
    satellite_product_id: str
    vessel_truth: str
    physical_incident_label: str
    unverified_source_metadata: str
    provenance_class: str
    provenance_status: Optional[str] = "PROVENANCE_LIMITED"
    has_synthetic_dependencies: Optional[bool] = True
    source_pair_status: Optional[str] = "VALID_CANDIDATE"
    temporal_status: Optional[str] = "PENDING"
    reason: Optional[str] = None
    lineage_status: Optional[str] = "CURRENT"
    stage_provenance: Optional[Dict[str, str]] = None
    limitations: List[str]


class ScenarioListResponse(BaseModel):
    """List response for registered real repository scenarios."""

    total_scenarios: int
    scenarios: List[ScenarioResponse]


class ArtifactListResponse(BaseModel):
    """Response model for job artifacts endpoint."""

    job_id: str
    total_artifacts: int
    artifacts: List[Dict[str, Any]]


class ErrorResponse(BaseModel):
    """Standardized error response model."""

    code: str
    message: str
    stage: Optional[str] = None
    retryable: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Operational Acquisition Job Schemas (Phase 6C)
# ---------------------------------------------------------------------------


class AcquisitionJobRequest(BaseModel):
    """Request schema to initialize and execute an operational acquisition job."""

    west: float = Field(..., ge=-180.0, le=180.0, description="Western longitude")
    south: float = Field(..., ge=-90.0, le=90.0, description="Southern latitude")
    east: float = Field(..., ge=-180.0, le=180.0, description="Eastern longitude")
    north: float = Field(..., ge=-90.0, le=90.0, description="Northern latitude")
    start_time: datetime = Field(..., description="Start of temporal window (UTC)")
    end_time: datetime = Field(..., description="End of temporal window (UTC)")
    provider: str = Field(
        default="copernicus_cdse",
        description="Approved Earth observation provider (default: copernicus_cdse)",
    )
    platform: str = Field(
        default="sentinel-1",
        description="Satellite platform (default: sentinel-1)",
    )
    polarizations: List[str] = Field(
        default_factory=lambda: ["VV", "VH"],
        description="Requested polarization channels (e.g. ['VV', 'VH'])",
    )
    width: Optional[int] = Field(
        default=512,
        ge=1,
        le=2500,
        description="Target output raster width in pixels (1-2500)",
    )
    height: Optional[int] = Field(
        default=512,
        ge=1,
        le=2500,
        description="Target output raster height in pixels (1-2500)",
    )
    investigation_label: Optional[str] = Field(
        default=None,
        description="Optional human-readable label for the acquisition investigation",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        val = str(v).strip().lower()
        if not val:
            raise ValueError("provider cannot be empty")
        if any(f in val for f in ["synthetic", "mock", "demo", "dummy", "fake", "simulated"]):
            raise ValueError(f"Provider '{v}' rejected: only real operational EO providers are authorized.")
        return val

    @field_validator("polarizations")
    @classmethod
    def validate_polarizations(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one polarization channel must be specified")
        allowed = {"VV", "VH", "HH", "HV"}
        clean = []
        for p in v:
            up = str(p).strip().upper()
            if up not in allowed:
                raise ValueError(f"Polarization '{p}' invalid. Allowed: {allowed}")
            if up not in clean:
                clean.append(up)
        return clean

    @model_validator(mode="after")
    def validate_spatial_and_temporal_extents(self) -> AcquisitionJobRequest:
        if self.east <= self.west:
            raise ValueError(f"east ({self.east}) must be strictly greater than west ({self.west})")
        if self.north <= self.south:
            raise ValueError(f"north ({self.north}) must be strictly greater than south ({self.south})")
        if self.end_time <= self.start_time:
            raise ValueError(f"end_time ({self.end_time}) must be strictly after start_time ({self.start_time})")
        return self


class AcquisitionJobLinks(BaseModel):
    """Hypermedia navigation links for an operational acquisition job."""

    self: str
    result: str
    geotiff: Optional[str] = None


class AcquisitionJobResponse(BaseModel):
    """Machine-readable operational acquisition job state response."""

    job_id: str
    status: str
    current_stage: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    request_params: Dict[str, Any] = Field(default_factory=dict)
    stage_timings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    acquisition_id: Optional[str] = None
    provider: Optional[str] = None
    source_reference: Optional[str] = None
    geotiff_path: Optional[str] = None
    metadata_path: Optional[str] = None
    content_sha256: Optional[str] = None
    sar_validation: Optional[Dict[str, Any]] = None
    evidence_id: Optional[str] = None
    execution_authorized: bool = False
    has_prediction: bool = False
    error: Optional[Dict[str, Any]] = None
    limitations: List[str] = Field(default_factory=list)
    links: AcquisitionJobLinks


class AcquisitionJobListResponse(BaseModel):
    """List response model for acquisition jobs endpoint."""

    total_jobs: int
    limit: int
    jobs: List[Dict[str, Any]]


class CreateInvestigationRequest(BaseModel):
    """Request schema to initialize a Phase 7 investigation run."""

    aoi: Optional[Dict[str, Any]] = Field(None, description="AOI GeoJSON geometry or bounding box dict")
    bbox: Optional[List[float]] = Field(None, description="Bounding box [west, south, east, north]")
    start_time: Optional[str] = Field(None, description="Start time ISO UTC")
    end_time: Optional[str] = Field(None, description="End time ISO UTC")
    polarizations: Optional[List[str]] = Field(default_factory=lambda: ["VV", "VH"])
    analysis_mode: str = Field("OPERATIONAL", description="Analysis mode: 'OPERATIONAL' or 'DEMO'")
    investigation_label: Optional[str] = Field(None, description="Human readable label for investigation")
    scenario_id: Optional[str] = Field(None, description="Registered scenario ID if applicable")
