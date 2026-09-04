"""SAR Preprocessor implementation (Phase 1C.1).

Converts validated Sentinel-1 GeoTIFF rasters into standardized, deterministic,
analysis-ready numerical representations (PreprocessingResult).

Performs:
1. In-memory raster decoding preserving band-to-polarization mapping.
2. Deterministic invalid pixel detection and boolean validity mask generation.
3. Numerically safe linear σ0 to decibel (dB) conversion with configurable floor.
4. Independent per-band normalization (Percentile, MinMax, Z-score).
5. Comprehensive per-band scientific statistical metrics.
6. Full geospatial and provenance metadata preservation.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from rasterio.io import MemoryFile

from ocean_sentinel.errors import PreprocessingError
from ocean_sentinel.models import ImageryResult, Polarization
from ocean_sentinel.processing.models import (
    NormalizationMetadata,
    NormalizationMethod,
    PreprocessedBand,
    PreprocessedBandStats,
    PreprocessingConfig,
    PreprocessingResult,
    QualityMetrics,
)

logger = logging.getLogger(__name__)


class SARPreprocessor:
    """Scientific SAR preprocessor for Sentinel-1 backscatter imagery."""

    def __init__(self, default_config: Optional[PreprocessingConfig] = None) -> None:
        """Initialize preprocessor with optional default configuration."""
        self.default_config = default_config or PreprocessingConfig()

    def process(
        self,
        imagery: ImageryResult,
        config: Optional[PreprocessingConfig] = None,
    ) -> PreprocessingResult:
        """Process an ImageryResult into a scientifically validated PreprocessingResult.

        Args:
            imagery: Validated ImageryResult containing raw GeoTIFF bytes and metadata.
            config: Optional override configuration; defaults to preprocessor's default.

        Returns:
            PreprocessingResult containing physical linear, physical dB, validity masks,
            and optional normalized representations per polarization band.

        Raises:
            PreprocessingError: If input data is corrupt, dimension-mismatched,
                or contains zero valid pixels.
        """
        cfg = config or self.default_config

        if not imagery.raw_bytes:
            raise PreprocessingError(
                "ImageryResult contains empty raw_bytes",
                details={"observation_id": imagery.observation_id},
            )

        # 1. Read GeoTIFF bands in-memory via rasterio
        try:
            with MemoryFile(imagery.raw_bytes) as memfile:
                with memfile.open() as dataset:
                    if dataset.count != len(imagery.bands):
                        raise PreprocessingError(
                            f"Band count mismatch: GeoTIFF has {dataset.count} bands, "
                            f"but imagery.bands has {len(imagery.bands)}",
                            details={
                                "dataset_count": dataset.count,
                                "metadata_bands": len(imagery.bands),
                            },
                        )

                    raw_bands: dict[Polarization, np.ndarray] = {}
                    for idx, pol in enumerate(imagery.bands):
                        band_arr = dataset.read(idx + 1).astype(np.float32)
                        raw_bands[pol] = band_arr

        except PreprocessingError:
            raise
        except Exception as e:
            raise PreprocessingError(
                f"Failed to decode GeoTIFF raster bytes: {e}",
                cause=e,
                details={"observation_id": imagery.observation_id},
            ) from e

        # 2. Process extracted arrays
        return self.process_arrays(
            arrays=raw_bands,
            polarizations=list(imagery.bands),
            observation_id=imagery.observation_id,
            width=imagery.width,
            height=imagery.height,
            crs=imagery.crs,
            bounds=imagery.bounds,
            transform=imagery.transform,
            config=cfg,
        )

    def process_arrays(
        self,
        arrays: dict[Polarization, np.ndarray],
        polarizations: list[Polarization],
        observation_id: str,
        width: int,
        height: int,
        crs: str,
        bounds: list[float],
        transform: list[float],
        config: Optional[PreprocessingConfig] = None,
    ) -> PreprocessingResult:
        """Process raw 2D NumPy arrays for each polarization channel.

        Args:
            arrays: Mapping of Polarization to 2D float32 numpy array.
            polarizations: Explicit ordered list of polarizations (e.g. [VV, VH]).
            observation_id: Source acquisition ID.
            width: Expected raster width in pixels.
            height: Expected raster height in pixels.
            crs: Coordinate Reference System identifier.
            bounds: Bounding box [west, south, east, north].
            transform: Affine geotransform coefficients.
            config: Preprocessing configuration.

        Returns:
            PreprocessingResult with complete scientific validation.
        """
        cfg = config or self.default_config
        processed_bands: dict[Polarization, PreprocessedBand] = {}

        for pol in polarizations:
            if pol not in arrays:
                raise PreprocessingError(
                    f"Missing polarization array for {pol.value}",
                    details={"missing_polarization": pol.value},
                )

            raw_arr = arrays[pol]

            # Validate dimensions
            if raw_arr.ndim != 2:
                raise PreprocessingError(
                    f"Band {pol.value} array must be 2D, got shape {raw_arr.shape}",
                    details={"polarization": pol.value, "shape": list(raw_arr.shape)},
                )
            if raw_arr.shape != (height, width):
                raise PreprocessingError(
                    f"Band {pol.value} shape {raw_arr.shape} "
                    f"does not match expected ({height}, {width})",
                    details={
                        "polarization": pol.value,
                        "actual_shape": list(raw_arr.shape),
                        "expected_shape": [height, width],
                    },
                )

            # Process single band
            band_res = self._process_single_band(raw_arr, pol, cfg)
            processed_bands[pol] = band_res

        return PreprocessingResult(
            observation_id=observation_id,
            width=width,
            height=height,
            band_count=len(polarizations),
            polarizations=polarizations,
            crs=crs,
            bounds=bounds,
            transform=transform,
            config=cfg,
            bands=processed_bands,
        )

    def _process_single_band(
        self,
        raw_arr: np.ndarray,
        polarization: Polarization,
        config: PreprocessingConfig,
    ) -> PreprocessedBand:
        """Process a single 2D float32 array for one polarization band."""
        total_pixels = int(raw_arr.size)

        # 1. Deterministic Validity Mask
        # A pixel is valid if it is finite and strictly positive in linear backscatter
        valid_mask = np.isfinite(raw_arr) & (raw_arr > 0.0)
        valid_count = int(np.sum(valid_mask))
        invalid_count = total_pixels - valid_count
        valid_percentage = (
            float((valid_count / total_pixels) * 100.0) if total_pixels > 0 else 0.0
        )

        quality = QualityMetrics(
            total_pixels=total_pixels,
            valid_pixels=valid_count,
            invalid_pixels=invalid_count,
            valid_percentage=valid_percentage,
        )

        # Check for all-invalid array
        if valid_count == 0:
            raise PreprocessingError(
                f"Band {polarization.value} contains zero valid pixels "
                f"(all {total_pixels} pixels are non-positive, NaN, or infinite)",
                details={
                    "polarization": polarization.value,
                    "total_pixels": total_pixels,
                },
            )

        valid_linear = raw_arr[valid_mask]

        # 2. Linear Statistics
        linear_stats = PreprocessedBandStats(
            min=float(np.min(valid_linear)),
            max=float(np.max(valid_linear)),
            mean=float(np.mean(valid_linear)),
            median=float(np.median(valid_linear)),
            std=float(np.std(valid_linear)),
        )

        # Optional preservation of linear data
        linear_data = raw_arr.copy() if config.preserve_linear else None

        # 3. Decibel (dB) Conversion
        # Formula: σ0_dB = 10 * log10(σ0_linear)
        # Invalid pixels are clamped to config.db_floor (default -50.0 dB)
        db_data = np.full_like(raw_arr, fill_value=config.db_floor, dtype=np.float32)

        if config.convert_to_db:
            # Clamping linear input strictly to linear_min_threshold for numerical safety
            clamped_linear = np.maximum(valid_linear, config.linear_min_threshold)
            computed_db = 10.0 * np.log10(clamped_linear)
            db_data[valid_mask] = computed_db.astype(np.float32)
        else:
            # If dB conversion disabled, physical data is linear
            db_data[valid_mask] = valid_linear

        valid_db = db_data[valid_mask]
        db_stats = PreprocessedBandStats(
            min=float(np.min(valid_db)),
            max=float(np.max(valid_db)),
            mean=float(np.mean(valid_db)),
            median=float(np.median(valid_db)),
            std=float(np.std(valid_db)),
        )

        # 4. Independent Per-Band Normalization
        normalized_data: Optional[np.ndarray] = None
        norm_metadata: Optional[NormalizationMetadata] = None

        if config.normalization_method == NormalizationMethod.PERCENTILE:
            normalized_data, norm_metadata = self._normalize_percentile(
                db_data, valid_mask, valid_db, config
            )
        elif config.normalization_method == NormalizationMethod.MINMAX:
            normalized_data, norm_metadata = self._normalize_minmax(
                db_data, valid_mask, valid_db, config
            )
        elif config.normalization_method == NormalizationMethod.ZSCORE:
            normalized_data, norm_metadata = self._normalize_zscore(
                db_data, valid_mask, valid_db
            )
        elif config.normalization_method == NormalizationMethod.NONE:
            normalized_data = None
            norm_metadata = None

        return PreprocessedBand(
            polarization=polarization,
            valid_mask=valid_mask,
            db_data=db_data,
            linear_data=linear_data,
            normalized_data=normalized_data,
            quality=quality,
            db_stats=db_stats,
            linear_stats=linear_stats,
            normalization_metadata=norm_metadata,
        )

    def _normalize_percentile(
        self,
        db_data: np.ndarray,
        valid_mask: np.ndarray,
        valid_db: np.ndarray,
        config: PreprocessingConfig,
    ) -> tuple[np.ndarray, NormalizationMetadata]:
        """Apply percentile normalization to valid pixels."""
        norm_arr = np.zeros_like(db_data, dtype=np.float32)
        p_min = float(np.percentile(valid_db, config.percentile_min))
        p_max = float(np.percentile(valid_db, config.percentile_max))

        denom = p_max - p_min
        if abs(denom) < 1e-10:
            # Constant or near-constant array; avoid division by zero
            norm_arr[valid_mask] = 0.5
        else:
            scaled = (valid_db - p_min) / denom
            if config.clip_normalized:
                scaled = np.clip(scaled, 0.0, 1.0)
            norm_arr[valid_mask] = scaled.astype(np.float32)

        metadata = NormalizationMetadata(
            method=NormalizationMethod.PERCENTILE,
            parameters={"p_min": p_min, "p_max": p_max},
        )
        return norm_arr, metadata

    def _normalize_minmax(
        self,
        db_data: np.ndarray,
        valid_mask: np.ndarray,
        valid_db: np.ndarray,
        config: PreprocessingConfig,
    ) -> tuple[np.ndarray, NormalizationMetadata]:
        """Apply min-max scaling to valid pixels."""
        norm_arr = np.zeros_like(db_data, dtype=np.float32)
        min_val = float(np.min(valid_db))
        max_val = float(np.max(valid_db))

        denom = max_val - min_val
        if abs(denom) < 1e-10:
            # Constant array; avoid division by zero
            norm_arr[valid_mask] = 0.5
        else:
            scaled = (valid_db - min_val) / denom
            if config.clip_normalized:
                scaled = np.clip(scaled, 0.0, 1.0)
            norm_arr[valid_mask] = scaled.astype(np.float32)

        metadata = NormalizationMetadata(
            method=NormalizationMethod.MINMAX,
            parameters={"min": min_val, "max": max_val},
        )
        return norm_arr, metadata

    def _normalize_zscore(
        self,
        db_data: np.ndarray,
        valid_mask: np.ndarray,
        valid_db: np.ndarray,
    ) -> tuple[np.ndarray, NormalizationMetadata]:
        """Apply z-score standardization (x - mean) / std to valid pixels."""
        norm_arr = np.zeros_like(db_data, dtype=np.float32)
        mean_val = float(np.mean(valid_db))
        std_val = float(np.std(valid_db))

        if abs(std_val) < 1e-10:
            # Zero variance (constant array); avoid division by zero
            norm_arr[valid_mask] = 0.0
        else:
            scaled = (valid_db - mean_val) / std_val
            norm_arr[valid_mask] = scaled.astype(np.float32)

        metadata = NormalizationMetadata(
            method=NormalizationMethod.ZSCORE,
            parameters={"mean": mean_val, "std": std_val},
        )
        return norm_arr, metadata
