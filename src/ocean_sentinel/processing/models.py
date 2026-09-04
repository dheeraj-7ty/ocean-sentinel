"""Domain models for SAR Preprocessing & Scientific Data Pipeline (Phase 1C.1).

Defines configuration, quality metrics, per-band representations, and top-level
results for processed SAR backscatter data.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ocean_sentinel.models import Polarization


class BackscatterUnit(str, Enum):
    """Scientific representation unit for SAR backscatter values."""

    LINEAR = "linear"  # Linear intensity σ0 (power / ratio)
    DECIBEL = "dB"     # Decibel logarithmic scale (10 * log10(σ0))


class NormalizationMethod(str, Enum):
    """Normalization strategies for downstream ML and visualization."""

    NONE = "none"              # No normalization
    MINMAX = "minmax"          # Min-max scaling to [0, 1]
    PERCENTILE = "percentile"  # Percentile clipping and scaling to [0, 1]
    ZSCORE = "zscore"          # Standardization (x - mean) / std


class NormalizationMetadata(BaseModel):
    """Metadata capturing the exact parameters used during normalization."""

    method: NormalizationMethod
    parameters: dict[str, float] = Field(
        default_factory=dict,
        description="Parameters such as p_min/p_max, min/max, or mean/std",
    )


class QualityMetrics(BaseModel):
    """Quality and validity metrics for a SAR raster band."""

    total_pixels: int = Field(..., ge=0, description="Total number of pixels in band")
    valid_pixels: int = Field(..., ge=0, description="Count of valid scientific observations")
    invalid_pixels: int = Field(
        ..., ge=0, description="Count of non-positive, NaN, or infinite pixels"
    )
    valid_percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of valid pixels")

    @property
    def all_valid(self) -> bool:
        """True if 100% of pixels are valid."""
        return self.invalid_pixels == 0

    @property
    def all_invalid(self) -> bool:
        """True if 0% of pixels are valid."""
        return self.valid_pixels == 0


class PreprocessedBandStats(BaseModel):
    """Statistical metrics calculated strictly over valid pixels."""

    min: float = Field(..., description="Minimum value of valid pixels")
    max: float = Field(..., description="Maximum value of valid pixels")
    mean: float = Field(..., description="Mean value of valid pixels")
    median: float = Field(..., description="Median value of valid pixels")
    std: float = Field(..., description="Standard deviation of valid pixels")


class PreprocessingConfig(BaseModel):
    """Configuration for SAR preprocessing operations.

    Controls dB conversion, invalid-pixel clamping floor, and per-band normalization.
    """

    convert_to_db: bool = Field(
        default=True,
        description="Convert linear σ0 intensity to decibels (10 * log10(σ0))",
    )
    db_floor: float = Field(
        default=-50.0,
        description="Configurable floor in dB applied to invalid/non-positive pixels",
    )
    linear_min_threshold: float = Field(
        default=1e-6,
        description="Lower threshold for linear σ0 to avoid log10 of non-positive values",
    )
    preserve_linear: bool = Field(
        default=True,
        description="Retain original physical linear arrays alongside dB arrays",
    )
    normalization_method: NormalizationMethod = Field(
        default=NormalizationMethod.PERCENTILE,
        description="Normalization strategy to apply per polarization band",
    )
    percentile_min: float = Field(
        default=1.0,
        ge=0.0,
        lt=100.0,
        description="Lower percentile for PERCENTILE normalization",
    )
    percentile_max: float = Field(
        default=99.0,
        gt=0.0,
        le=100.0,
        description="Upper percentile for PERCENTILE normalization",
    )
    clip_normalized: bool = Field(
        default=True,
        description="Whether to clip normalized values to [0.0, 1.0]",
    )

    @field_validator("percentile_max")
    @classmethod
    def max_must_exceed_min(cls, v: float, info) -> float:
        min_val = info.data.get("percentile_min")
        if min_val is not None and v <= min_val:
            raise ValueError(
                f"percentile_max ({v}) must be greater than percentile_min ({min_val})"
            )
        return v


class PreprocessedBand(BaseModel):
    """Preprocessed representation of a single SAR polarization band.

    Contains physical arrays, boolean validity mask, optional normalized array,
    quality metrics, and per-band statistics. Large NumPy arrays are excluded from repr.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    polarization: Polarization = Field(..., description="Band polarization channel (e.g. VV, VH)")
    valid_mask: np.ndarray = Field(
        ..., repr=False, description="2D boolean mask (True = valid pixel)"
    )
    db_data: np.ndarray = Field(
        ..., repr=False, description="2D float32 physical dB backscatter array"
    )
    linear_data: Optional[np.ndarray] = Field(
        default=None,
        repr=False,
        description="2D float32 physical linear backscatter array",
    )
    normalized_data: Optional[np.ndarray] = Field(
        default=None,
        repr=False,
        description="2D float32 normalized array (ML/visualization representation)",
    )
    quality: QualityMetrics = Field(..., description="Validity and quality metrics")
    db_stats: PreprocessedBandStats = Field(..., description="Statistics of valid dB pixels")
    linear_stats: Optional[PreprocessedBandStats] = Field(
        default=None,
        description="Statistics of valid linear pixels",
    )
    normalization_metadata: Optional[NormalizationMetadata] = Field(
        default=None,
        description="Normalization parameters applied to this band",
    )

    def to_safe_summary(self) -> dict[str, Any]:
        """Return safe metadata summary without raw array content."""
        return {
            "polarization": self.polarization.value,
            "has_linear": self.linear_data is not None,
            "has_db": self.db_data is not None,
            "has_normalized": self.normalized_data is not None,
            "quality": self.quality.model_dump(),
            "db_stats": self.db_stats.model_dump(),
            "linear_stats": self.linear_stats.model_dump() if self.linear_stats else None,
            "normalization": (
                self.normalization_metadata.model_dump()
                if self.normalization_metadata
                else None
            ),
        }


class PreprocessingResult(BaseModel):
    """Complete result of SAR preprocessing for a Sentinel-1 observation.

    Preserves full geospatial provenance, explicit polarization ordering,
    quality metrics, and separated physical/normalized representations.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    observation_id: str = Field(..., description="ID of the source acquisition")
    width: int = Field(..., ge=1, description="Raster width in pixels")
    height: int = Field(..., ge=1, description="Raster height in pixels")
    band_count: int = Field(..., ge=1, description="Number of polarization bands")
    polarizations: list[Polarization] = Field(
        ...,
        description="Explicit ordered list of polarizations (e.g. [VV, VH])",
    )
    crs: str = Field(..., description="Coordinate reference system identifier (e.g. EPSG:4326)")
    bounds: list[float] = Field(
        ...,
        description="Geographic bounding box [west, south, east, north]",
    )
    transform: list[float] = Field(
        ...,
        description="Affine geotransform coefficients [a, b, c, d, e, f]",
    )
    config: PreprocessingConfig = Field(..., description="Configuration used for preprocessing")
    bands: dict[Polarization, PreprocessedBand] = Field(
        ...,
        description="Mapping from Polarization to PreprocessedBand container",
    )

    def get_band(self, polarization: Polarization) -> PreprocessedBand:
        """Retrieve preprocessed band for the specified polarization."""
        if polarization not in self.bands:
            avail = [p.value for p in self.bands.keys()]
            raise KeyError(
                f"Polarization {polarization.value} not present in result. Available: {avail}"
            )
        return self.bands[polarization]

    def get_db(self, polarization: Polarization) -> np.ndarray:
        """Get 2D float32 dB array for a polarization."""
        return self.get_band(polarization).db_data

    def get_linear(self, polarization: Polarization) -> np.ndarray:
        """Get 2D float32 linear array for a polarization."""
        band = self.get_band(polarization)
        if band.linear_data is None:
            raise ValueError(
                f"Linear data was not preserved for polarization {polarization.value} "
                "(preserve_linear was False in configuration)"
            )
        return band.linear_data

    def get_valid_mask(self, polarization: Polarization) -> np.ndarray:
        """Get 2D boolean validity mask for a polarization."""
        return self.get_band(polarization).valid_mask

    def get_normalized(self, polarization: Polarization) -> Optional[np.ndarray]:
        """Get 2D float32 normalized array for a polarization (None if method is NONE)."""
        return self.get_band(polarization).normalized_data

    def to_multichannel_array(self, kind: str = "db") -> np.ndarray:
        """Stack bands into a 3D NumPy array of shape (num_bands, height, width).

        Band ordering strictly follows self.polarizations (e.g. [VV, VH]).

        Args:
            kind: 'db', 'linear', or 'normalized'.
        """
        kind_lower = kind.lower()
        arrays: list[np.ndarray] = []
        for pol in self.polarizations:
            band = self.get_band(pol)
            if kind_lower == "db":
                arrays.append(band.db_data)
            elif kind_lower == "linear":
                if band.linear_data is None:
                    raise ValueError("Linear data was not preserved in this result")
                arrays.append(band.linear_data)
            elif kind_lower == "normalized":
                if band.normalized_data is None:
                    raise ValueError(
                        f"Normalized data is None for polarization {pol.value} "
                        f"(normalization method was {self.config.normalization_method.value})"
                    )
                arrays.append(band.normalized_data)
            else:
                raise ValueError(
                    f"Unknown array kind: {kind!r}. Must be 'db', 'linear', or 'normalized'"
                )

        return np.stack(arrays, axis=0)

    def to_safe_summary(self) -> dict[str, Any]:
        """Return safe metadata summary without raw array content."""
        return {
            "observation_id": self.observation_id,
            "width": self.width,
            "height": self.height,
            "band_count": self.band_count,
            "polarizations": [p.value for p in self.polarizations],
            "crs": self.crs,
            "bounds": self.bounds,
            "transform": self.transform,
            "config": self.config.model_dump(),
            "bands": {
                pol.value: band.to_safe_summary()
                for pol, band in self.bands.items()
            },
        }


# Architectural alias for conceptual clarity
PreprocessedSAR = PreprocessingResult
