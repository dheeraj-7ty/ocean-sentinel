"""Domain models for offline dataset ingestion, provenance, validation, and tiling.

Defines the contract for ingesting offline radar imagery and mask datasets (such as
Trujillo Part I), enforcing strict provenance immutability, explicit radiometric unit
handling, clear source-truth distinction, deterministic tiling, and leakage-safe grouping.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from ocean_sentinel.models import OrbitDirection, Polarization
from ocean_sentinel.processing.models import BackscatterUnit


class VerificationStatus(str, Enum):
    """Source-truth classification for dataset metadata attributes.

    Distinguishes physically verified facts from reported literature claims,
    nominal assumptions, and unknown parameters.
    """

    VERIFIED = "VERIFIED"  # Directly verified via local bytes, code, or checksums
    REPORTED = "REPORTED"  # Stated in publications/metadata, awaiting local archive check
    ASSUMED = "ASSUMED"    # Working assumption (e.g. nominal 10m GSD), clearly labeled
    UNKNOWN = "UNKNOWN"    # Not reported or not present in source metadata


class DatasetPatchProvenance(BaseModel):
    """Immutable provenance record for a single offline dataset patch.

    Frozen at the model level to prevent accidental mutation. Captures complete
    lineage, radiometric units, spatial reference, and the verification status
    of each attribute without inventing unverified metadata.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    dataset_name: str = Field(..., description="Dataset identifier (e.g. 'trujillo_2024_part_i')")
    dataset_version: Optional[str] = Field(default=None, description="Dataset release version")
    source_archive: Optional[str] = Field(
        default=None, description="Source archive or package filename"
    )
    patch_stem: str = Field(..., description="Canonical patch stem identifier (e.g. '00000')")
    image_path: Optional[Path] = Field(default=None, description="Local path to image raster file")
    mask_path: Optional[Path] = Field(default=None, description="Local path to mask raster file")
    radiometric_unit: BackscatterUnit = Field(
        ...,
        description="Authoritative radiometric unit of input data (LINEAR or DECIBEL)",
    )

    # Polarizations / channels (configurable, reported vs unknown)
    polarizations: Optional[list[Polarization]] = Field(
        default=None,
        description="Polarization channels in raster band order (e.g. [VV, VH])",
    )
    polarization_status: VerificationStatus = Field(
        default=VerificationStatus.UNKNOWN,
        description="Verification status of polarization channel order",
    )

    # Native spatial geometry
    native_shape: tuple[int, int] = Field(
        default=(2048, 2048),
        description="Native (height, width) dimensions in pixels",
    )
    native_shape_status: VerificationStatus = Field(
        default=VerificationStatus.REPORTED,
        description="Verification status of native dimensions",
    )

    # Data type
    dtype: str = Field(default="float32", description="Image pixel data type")
    dtype_status: VerificationStatus = Field(
        default=VerificationStatus.REPORTED,
        description="Verification status of image dtype",
    )

    # Spatial resolution
    nominal_gsd_meters: Optional[float] = Field(
        default=10.0,
        description="Nominal ground sampling distance in metres",
    )
    nominal_gsd_status: VerificationStatus = Field(
        default=VerificationStatus.ASSUMED,
        description="Verification status of nominal GSD",
    )

    # Geospatial reference (None for unprojected rasters)
    crs: Optional[str] = Field(
        default=None,
        description="Coordinate Reference System identifier (None if unreferenced)",
    )
    crs_status: VerificationStatus = Field(
        default=VerificationStatus.UNKNOWN,
        description="Verification status of CRS",
    )
    transform: Optional[list[float]] = Field(
        default=None,
        description="Affine transform coefficients [a, b, c, d, e, f] (None if unreferenced)",
    )
    transform_status: VerificationStatus = Field(
        default=VerificationStatus.UNKNOWN,
        description="Verification status of geotransform",
    )

    # Satellite telemetry lineage
    parent_scene_id: Optional[str] = Field(
        default=None,
        description="Parent Sentinel-1 acquisition identifier if known",
    )
    parent_scene_status: VerificationStatus = Field(
        default=VerificationStatus.UNKNOWN,
        description="Verification status of parent Sentinel product ID",
    )
    acquisition_time: Optional[datetime] = Field(
        default=None,
        description="Acquisition datetime UTC if known",
    )
    acquisition_time_status: VerificationStatus = Field(
        default=VerificationStatus.UNKNOWN,
        description="Verification status of acquisition time",
    )
    orbit_direction: Optional[OrbitDirection] = Field(
        default=None,
        description="Orbit direction if known",
    )
    orbit_direction_status: VerificationStatus = Field(
        default=VerificationStatus.UNKNOWN,
        description="Verification status of orbit direction",
    )
    relative_orbit: Optional[int] = Field(
        default=None,
        description="Relative orbit number if known",
    )
    relative_orbit_status: VerificationStatus = Field(
        default=VerificationStatus.UNKNOWN,
        description="Verification status of relative orbit",
    )

    # Overall source status
    source_verification_status: VerificationStatus = Field(
        default=VerificationStatus.REPORTED,
        description="Overall verification status of source archive",
    )


class DatasetPatchMetadata(BaseModel):
    """Compositional summary metadata for a validated dataset patch.

    Immutable model capturing patch dimensions, foreground statistics,
    and the canonical group key for leakage-safe partitioning.
    """

    model_config = ConfigDict(frozen=True)

    provenance: DatasetPatchProvenance
    total_pixels: int = Field(..., ge=1, description="Total pixels in patch (height * width)")
    foreground_pixels: int = Field(..., ge=0, description="Count of foreground (oil) pixels")
    foreground_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of foreground pixels: foreground_pixels / total_pixels",
    )
    has_oil: bool = Field(..., description="True if foreground_pixels > 0")
    group_key: str = Field(
        ...,
        description="Grouping key for train/val/test split to guarantee zero spatial leakage",
    )


class TileProvenance(BaseModel):
    """Provenance record for a cropped tile, inheriting immutable parent patch provenance.

    Composes the parent DatasetPatchProvenance and adds tile-specific spatial indices
    and bounds without duplicating mutable state.
    """

    model_config = ConfigDict(frozen=True)

    parent: DatasetPatchProvenance = Field(
        ..., description="Immutable parent patch provenance reference"
    )
    tile_id: str = Field(..., description="Unique tile identifier (e.g. '00000_r01_c02')")
    parent_stem: str = Field(..., description="Parent patch stem")
    group_key: str = Field(..., description="Grouping key for leakage prevention (matches parent)")
    row_idx: int = Field(..., ge=0, description="Tile grid row index (0-based)")
    col_idx: int = Field(..., ge=0, description="Tile grid column index (0-based)")
    row_offset: int = Field(..., ge=0, description="Pixel Y offset in parent patch")
    col_offset: int = Field(..., ge=0, description="Pixel X offset in parent patch")
    height: int = Field(..., ge=1, description="Tile height in pixels")
    width: int = Field(..., ge=1, description="Tile width in pixels")


class TileDefinition(BaseModel):
    """Geometric definition and statistical summary of a single tile crop.

    Used by the generic tiler to define chip boundaries and metadata.
    """

    model_config = ConfigDict(frozen=True)

    tile_id: str = Field(..., description="Unique tile identifier (e.g. '00000_r00_c00')")
    parent_stem: str = Field(..., description="Parent patch stem identifier")
    group_key: str = Field(..., description="Partition grouping key (stem or parent scene ID)")
    row_idx: int = Field(..., ge=0, description="Tile grid row index")
    col_idx: int = Field(..., ge=0, description="Tile grid column index")
    row_offset: int = Field(..., ge=0, description="Pixel row (Y) offset in parent patch")
    col_offset: int = Field(..., ge=0, description="Pixel column (X) offset in parent patch")
    height: int = Field(..., ge=1, description="Tile height in pixels")
    width: int = Field(..., ge=1, description="Tile width in pixels")
    foreground_pixels: Optional[int] = Field(
        default=None, ge=0, description="Count of foreground (oil) pixels in tile"
    )
    foreground_ratio: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Foreground fraction: foreground_pixels / (height * width)",
    )
    has_oil: Optional[bool] = Field(
        default=None, description="True if foreground_pixels > 0"
    )


class TilingConfig(BaseModel):
    """Configuration for deterministic sliding-window tiling.

    Defines window dimensions, strides, and edge-handling policies.
    """

    tile_height: int = Field(default=512, ge=1, description="Height of each tile in pixels")
    tile_width: int = Field(default=512, ge=1, description="Width of each tile in pixels")
    stride_y: int = Field(default=512, ge=1, description="Vertical stride in pixels")
    stride_x: int = Field(default=512, ge=1, description="Horizontal stride in pixels")
    edge_handling: str = Field(
        default="drop",
        description="Policy for boundaries: 'drop' (discard partial tiles), 'pad', or 'crop'",
    )
    min_valid_ratio_policy: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Policy default for minimum required fraction of valid pixels",
    )


class DatasetSample(BaseModel):
    """In-memory representation of a single loaded and validated dataset patch.

    Contains 3D multi-channel image array, 2D binary mask array, and both per-channel
    and reduced 2D validity masks.

    VALID MASK SEMANTICS:
    - `valid_mask_per_channel`: 3D boolean array of shape (num_channels, height, width).
      A pixel (c, y, x) is True if and only if image_data[c, y, x] is finite (not NaN, +inf, -inf).
    - `valid_mask`: 2D boolean array of shape (height, width).
      A spatial pixel (y, x) is True if and only if it is valid across ALL channels:
      `valid_mask = np.all(valid_mask_per_channel, axis=0)`.
      This guarantees that any pixel marked valid in the 2D mask has valid data in all bands.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: DatasetPatchMetadata = Field(..., description="Patch summary metadata")
    image_data: np.ndarray = Field(
        ...,
        repr=False,
        description="Multi-channel image array of shape (num_channels, height, width), float32",
    )
    mask_data: np.ndarray = Field(
        ...,
        repr=False,
        description="Binary segmentation mask array of shape (height, width), uint8 {0, 1}",
    )
    valid_mask: np.ndarray = Field(
        ...,
        repr=False,
        description="2D validity mask: np.all(valid_per_channel, axis=0)",
    )
    valid_mask_per_channel: np.ndarray = Field(
        ...,
        repr=False,
        description="3D boolean validity mask per channel of shape (num_channels, height, width)",
    )

    def to_safe_summary(self) -> dict[str, Any]:
        """Return safe metadata summary without raw array content."""
        return {
            "patch_stem": self.metadata.provenance.patch_stem,
            "dataset_name": self.metadata.provenance.dataset_name,
            "radiometric_unit": self.metadata.provenance.radiometric_unit.value,
            "image_shape": list(self.image_data.shape),
            "mask_shape": list(self.mask_data.shape),
            "dtype": str(self.image_data.dtype),
            "foreground_pixels": self.metadata.foreground_pixels,
            "foreground_ratio": self.metadata.foreground_ratio,
            "has_oil": self.metadata.has_oil,
            "group_key": self.metadata.group_key,
        }


class TileSample(BaseModel):
    """In-memory representation of a single tile crop ready for preprocessing/training.

    Carries tile definition, compositional tile provenance, cropped image and mask arrays,
    and validity masks.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    definition: TileDefinition = Field(..., description="Tile geometric definition and statistics")
    provenance: TileProvenance = Field(..., description="Tile provenance referencing parent patch")
    image_data: np.ndarray = Field(
        ...,
        repr=False,
        description="Tile image array of shape (num_channels, tile_height, tile_width), float32",
    )
    mask_data: np.ndarray = Field(
        ...,
        repr=False,
        description="Tile binary mask of shape (tile_height, tile_width), uint8 {0, 1}",
    )
    valid_mask: np.ndarray = Field(
        ...,
        repr=False,
        description="2D boolean validity mask for tile, shape (tile_height, tile_width)",
    )
    valid_mask_per_channel: np.ndarray = Field(
        ...,
        repr=False,
        description="3D validity mask per channel, shape (C, H, W)",
    )

    def to_safe_summary(self) -> dict[str, Any]:
        """Return safe metadata summary without raw array content."""
        return {
            "tile_id": self.definition.tile_id,
            "parent_stem": self.definition.parent_stem,
            "group_key": self.definition.group_key,
            "row_offset": self.definition.row_offset,
            "col_offset": self.definition.col_offset,
            "dimensions": [self.definition.height, self.definition.width],
            "foreground_pixels": self.definition.foreground_pixels,
            "foreground_ratio": self.definition.foreground_ratio,
            "has_oil": self.definition.has_oil,
        }


class DatasetValidationConfig(BaseModel):
    """Configurable policy expectations for offline dataset validation.

    None of these are hardcoded physical constants; they are configurable policies
    that default to reported/expected properties of the target dataset.
    """

    expected_shape: Optional[tuple[int, int]] = Field(
        default=(2048, 2048),
        description="Expected (height, width) spatial dimensions, or None to skip check",
    )
    expected_channels: Optional[int] = Field(
        default=2,
        description="Expected number of raster channels, or None to skip check",
    )
    expected_image_dtype: Optional[str] = Field(
        default="float32",
        description="Expected image pixel data type, or None to skip check",
    )
    expected_mask_dtype: Optional[str] = Field(
        default="uint8",
        description="Expected mask pixel data type, or None to skip check",
    )
    min_valid_ratio_policy: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Policy default for minimum required fraction of valid (finite) pixels",
    )
    require_binary_mask: bool = Field(
        default=True,
        description="Require mask unique values to be a subset of {0, 1}",
    )
    check_corruption: bool = Field(
        default=True,
        description="Verify raster file integrity and readability",
    )


class DatasetValidationResult(BaseModel):
    """Structured report of dataset sample validation checks."""

    is_valid: bool = Field(..., description="True if all mandatory checks passed")
    patch_stem: str = Field(..., description="Patch stem identifier evaluated")
    checks_passed: list[str] = Field(
        default_factory=list, description="List of check names that passed"
    )
    checks_failed: list[str] = Field(
        default_factory=list, description="List of check names that failed"
    )
    errors: list[str] = Field(
        default_factory=list, description="Error descriptions for failed checks"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Non-fatal warnings or policy notes"
    )
    metadata: Optional[DatasetPatchMetadata] = Field(
        default=None, description="Constructed metadata if validation succeeded"
    )
