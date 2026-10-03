"""Pydantic Request and Response Schemas for Ocean Sentinel API V1.

Enforces strict input validation, security controls (anti-path-traversal),
and machine-readable response structures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


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
