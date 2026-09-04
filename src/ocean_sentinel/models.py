"""Data models for Ocean Sentinel.

Defines the internal acquisition representation and request validation models.
These models normalize provider-specific responses into a common schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from shapely.geometry import shape
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


# ---------------------------------------------------------------------------
# Imagery Request (Process API request domain model)
# ---------------------------------------------------------------------------


class OutputFormat(str, Enum):
    """Supported output formats for the Sentinel Hub Process API.

    Only scientific formats suitable for downstream analysis are listed.
    PNG/JPEG are intentionally excluded — they are lossy and unsuitable
    for SAR signal processing.
    """

    TIFF = "image/tiff"


class OutputConfig(BaseModel):
    """Raster output configuration for the Process API.

    Controls the spatial resolution (or fixed pixel dimensions), output
    format, and CRS of the returned image.

    Exactly one of ``width``/``height`` OR ``resolution_meters`` must be
    specified. Specifying both is ambiguous and will fail validation.
    """

    format: OutputFormat = Field(
        default=OutputFormat.TIFF,
        description="Output MIME type",
    )
    width: Optional[int] = Field(
        default=None,
        ge=1,
        le=2500,
        description="Output width in pixels (1–2500)",
    )
    height: Optional[int] = Field(
        default=None,
        ge=1,
        le=2500,
        description="Output height in pixels (1–2500)",
    )
    resolution_meters: Optional[float] = Field(
        default=None,
        gt=0.0,
        description="Ground sampling distance in metres (> 0)",
    )
    crs_epsg: int = Field(
        default=4326,
        gt=0,
        description="EPSG code for the output CRS (default: WGS84 geographic)",
    )

    @model_validator(mode="after")
    def validate_dimensions(self) -> OutputConfig:
        """Either fixed pixel dimensions OR resolution_meters must be set."""
        width = self.width
        height = self.height
        resolution_meters = self.resolution_meters
        if width is None and height is None and resolution_meters is None:
            raise ValueError(
                "At least one of 'width'/'height' or 'resolution_meters' must be specified"
            )
        if (width is not None or height is not None) and resolution_meters is not None:
            raise ValueError(
                "Specify either pixel dimensions ('width'/'height') or "
                "'resolution_meters', not both"
            )
        if (width is None) != (height is None):
            raise ValueError("'width' and 'height' must both be specified or both be omitted")
        return self

    def to_sh_output(self) -> dict:
        """Serialise to Sentinel Hub Process API ``output`` section."""
        out: dict = {
            "responses": [
                {
                    "identifier": "default",
                    "format": {"type": self.format.value},
                }
            ]
        }
        if self.width is not None and self.height is not None:
            out["width"] = self.width
            out["height"] = self.height
        else:
            out["resx"] = self.resolution_meters
            out["resy"] = self.resolution_meters
        return out

    def to_crs_url(self) -> str:
        """Return OGC CRS URL for the configured EPSG code."""
        return f"http://www.opengis.net/def/crs/EPSG/0/{self.crs_epsg}"


class ImageryRequest(BaseModel):
    """Domain-level request for Sentinel-1 SAR imagery from the Process API.

    Represents everything needed to construct a valid Sentinel Hub
    Process API payload for one AOI and one Sentinel-1 acquisition.

    Validation enforces:

    - The requested bands must be a non-empty subset of the polarizations
      reported by the acquisition (``observation.polarizations``).
    - The bounding box must be non-degenerate.
    - The time range must be forward-ordered.
    - Output configuration must be consistent.

    This model does NOT contain authentication credentials; those are
    injected at the HTTP transport layer.
    """

    observation: AcquisitionMetadata = Field(
        ...,
        description="Sentinel-1 acquisition metadata from STAC discovery",
    )
    bbox: BoundingBox = Field(
        ...,
        description="AOI bounding box (must overlap the observation footprint)",
    )
    time_range: TimeRange = Field(
        ...,
        description="Temporal window for the Process API data filter",
    )
    requested_bands: list[Polarization] = Field(
        ...,
        min_length=1,
        description="Polarization channels to retrieve (e.g. [VV, VH])",
    )
    output: OutputConfig = Field(
        default_factory=lambda: OutputConfig(width=512, height=512),
        description="Raster output configuration",
    )

    @field_validator("requested_bands")
    @classmethod
    def bands_must_be_available(
        cls, requested: list[Polarization], info
    ) -> list[Polarization]:
        """Reject requests for polarizations not present in the observation."""
        observation = info.data.get("observation")
        if observation is None:
            # observation failed its own validation; skip this check
            return requested

        available = observation.polarizations
        if available is None:
            # Observation has no polarization metadata — cannot validate;
            # allow through and document the assumption.
            return requested

        unavailable = [p for p in requested if p not in available]
        if unavailable:
            available_str = ", ".join(p.value for p in available)
            requested_str = ", ".join(p.value for p in unavailable)
            raise ValueError(
                f"Requested band(s) [{requested_str}] not available in this observation "
                f"(available: [{available_str}])"
            )
        return requested


# ---------------------------------------------------------------------------
# Imagery Result (Process API response domain model)
# ---------------------------------------------------------------------------


class BandStatistics(BaseModel):
    """Numerical summary statistics for a single raster band."""

    polarization: Polarization = Field(..., description="Band polarization channel")
    min_value: float = Field(..., description="Minimum finite pixel value")
    max_value: float = Field(..., description="Maximum finite pixel value")
    mean_value: float = Field(..., description="Mean finite pixel value")
    finite_pixel_count: int = Field(..., ge=0, description="Count of finite (non-NaN/inf) pixels")
    total_pixel_count: int = Field(..., ge=1, description="Total pixel count in band")


class ImageryResult(BaseModel):
    """Result of a Sentinel-1 imagery retrieval operation.

    Encapsulates validated GeoTIFF raster data and extracted metadata.
    Contains no authentication credentials or raw HTTP objects.
    """

    observation_id: str = Field(..., description="ID of the source acquisition")
    width: int = Field(..., ge=1, description="Raster width in pixels")
    height: int = Field(..., ge=1, description="Raster height in pixels")
    band_count: int = Field(..., ge=1, description="Number of raster bands")
    bands: list[Polarization] = Field(
        ...,
        description="Polarization channel for each band in order",
    )
    dtype: str = Field(default="float32", description="Pixel data type")
    crs: str = Field(..., description="Coordinate reference system identifier")
    bounds: list[float] = Field(
        ...,
        description="Geographic bounding box [west, south, east, north]",
    )
    transform: list[float] = Field(
        ...,
        description="Affine geotransform coefficients [a, b, c, d, e, f]",
    )
    band_statistics: list[BandStatistics] = Field(
        default_factory=list,
        description="Summary statistics per band",
    )
    raw_bytes: bytes = Field(
        ...,
        repr=False,
        description="Raw GeoTIFF raster bytes",
    )

    def to_safe_summary(self) -> dict[str, Any]:
        """Return safe metadata summary without raw binary bytes."""
        return {
            "observation_id": self.observation_id,
            "width": self.width,
            "height": self.height,
            "band_count": self.band_count,
            "bands": [b.value for b in self.bands],
            "dtype": self.dtype,
            "crs": self.crs,
            "bounds": self.bounds,
            "byte_size": len(self.raw_bytes),
            "band_statistics": [s.model_dump() for s in self.band_statistics],
        }


