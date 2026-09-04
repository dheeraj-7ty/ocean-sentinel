"""Data models for Ocean Sentinel.

Defines the internal acquisition representation and request validation models.
These models normalize provider-specific responses into a common schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator
from shapely.geometry import box, shape
from shapely.validation import explain_validity


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Polarization(str, Enum):
    """SAR polarization modes."""

    VV = "VV"
    VH = "VH"
    HH = "HH"
    HV = "HV"


class OrbitDirection(str, Enum):
    """Satellite orbit direction."""

    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


class ProductType(str, Enum):
    """Sentinel-1 product types."""

    GRD = "GRD"
    SLC = "SLC"
    OCN = "OCN"


# ---------------------------------------------------------------------------
# Area of Interest
# ---------------------------------------------------------------------------


class BoundingBox(BaseModel):
    """Geographic bounding box in WGS84 (EPSG:4326).

    Coordinates follow the convention: [west, south, east, north].
    """

    west: float = Field(..., ge=-180.0, le=180.0, description="Western longitude")
    south: float = Field(..., ge=-90.0, le=90.0, description="Southern latitude")
    east: float = Field(..., ge=-180.0, le=180.0, description="Eastern longitude")
    north: float = Field(..., ge=-90.0, le=90.0, description="Northern latitude")

    @field_validator("north")
    @classmethod
    def north_must_exceed_south(cls, v: float, info) -> float:
        south = info.data.get("south")
        if south is not None and v <= south:
            raise ValueError(f"north ({v}) must be greater than south ({south})")
        return v

    @field_validator("east")
    @classmethod
    def east_must_exceed_west(cls, v: float, info) -> float:
        west = info.data.get("west")
        if west is not None and v <= west:
            raise ValueError(f"east ({v}) must be greater than west ({west})")
        return v

    def to_list(self) -> list[float]:
        """Return as [west, south, east, north]."""
        return [self.west, self.south, self.east, self.north]

    def to_geojson_polygon(self) -> dict:
        """Convert to GeoJSON Polygon geometry."""
        return {
            "type": "Polygon",
            "coordinates": [[
                [self.west, self.south],
                [self.east, self.south],
                [self.east, self.north],
                [self.west, self.north],
                [self.west, self.south],
            ]],
        }

    @property
    def area_degrees_squared(self) -> float:
        """Approximate area in square degrees (for sanity checking)."""
        return abs((self.east - self.west) * (self.north - self.south))


class TimeRange(BaseModel):
    """Temporal search window."""

    start: datetime = Field(..., description="Start of the time range (inclusive)")
    end: datetime = Field(..., description="End of the time range (inclusive)")

    @field_validator("end")
    @classmethod
    def end_must_follow_start(cls, v: datetime, info) -> datetime:
        start = info.data.get("start")
        if start is not None and v <= start:
            raise ValueError(f"end ({v}) must be after start ({start})")
        return v

    def to_stac_datetime(self) -> str:
        """Format as STAC datetime interval string.

        Produces ISO 8601 UTC strings with 'Z' suffix, e.g.:
        ``2026-08-01T00:00:00Z/2026-09-01T00:00:00Z``
        """
        def _fmt(dt: datetime) -> str:
            # Normalize to UTC if timezone-aware
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc)
            # Format without tz suffix, then append Z
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        return f"{_fmt(self.start)}/{_fmt(self.end)}"


class SearchRequest(BaseModel):
    """A satellite imagery search request."""

    bbox: BoundingBox
    time_range: TimeRange
    product_type: ProductType = Field(default=ProductType.GRD)
    polarizations: list[Polarization] = Field(
        default=[Polarization.VV, Polarization.VH],
    )
    max_results: int = Field(default=10, ge=1, le=100)


# ---------------------------------------------------------------------------
# Acquisition Metadata (internal normalized representation)
# ---------------------------------------------------------------------------


class AcquisitionMetadata(BaseModel):
    """Normalized Sentinel-1 acquisition metadata.

    This is the internal data contract between the discovery service
    and downstream consumers. It normalizes provider-specific STAC
    responses into a consistent schema.

    Fields marked Optional may not be available from all providers
    or for all product types.
    """

    # --- Required fields ---
    id: str = Field(..., description="Unique acquisition identifier")
    mission: str = Field(..., description="Mission identifier (e.g. 'sentinel-1')")
    product_type: ProductType = Field(..., description="Product type")
    acquisition_time: datetime = Field(..., description="Acquisition datetime (UTC)")
    geometry: dict = Field(..., description="GeoJSON geometry of the acquisition footprint")

    # --- Optional fields ---
    bbox: Optional[list[float]] = Field(
        default=None,
        description="Bounding box [west, south, east, north]",
    )
    polarizations: Optional[list[Polarization]] = Field(
        default=None,
        description="Available polarization channels",
    )
    orbit_direction: Optional[OrbitDirection] = Field(
        default=None,
        description="Orbit direction",
    )
    acquisition_mode: Optional[str] = Field(
        default=None,
        description="Acquisition mode (e.g. 'IW', 'EW')",
    )
    relative_orbit: Optional[int] = Field(
        default=None,
        description="Relative orbit number",
    )
    platform: Optional[str] = Field(
        default=None,
        description="Satellite platform (e.g. 'sentinel-1a', 'sentinel-1c')",
    )

    # --- STAC / provider-specific ---
    provider: str = Field(
        default="copernicus_cdse",
        description="Data provider identifier",
    )
    source_collection: Optional[str] = Field(
        default=None,
        description="Source collection identifier in the provider catalog",
    )
    source_reference: Optional[str] = Field(
        default=None,
        description="Direct reference URL or ID in the provider system",
    )
    self_link: Optional[str] = Field(
        default=None,
        description="Canonical STAC item URL (self link)",
    )
    stac_assets: Optional[dict[str, Any]] = Field(
        default=None,
        description="STAC asset catalog (keys → asset metadata) for future retrieval",
    )
    provider_properties: Optional[dict[str, Any]] = Field(
        default=None,
        description="Raw provider-specific metadata (preserved for debugging)",
    )

    @field_validator("geometry")
    @classmethod
    def validate_geometry(cls, v: dict) -> dict:
        """Validate that geometry is a valid GeoJSON geometry."""
        try:
            geom = shape(v)
            if not geom.is_valid:
                reason = explain_validity(geom)
                raise ValueError(f"Invalid geometry: {reason}")
        except Exception as e:
            if "Invalid geometry" in str(e):
                raise
            raise ValueError(f"Cannot parse GeoJSON geometry: {e}") from e
        return v
