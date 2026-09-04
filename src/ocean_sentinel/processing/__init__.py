"""SAR and raster processing subsystem for Ocean Sentinel.

Transforms validated satellite imagery into standardized, analysis-ready
numerical representations for downstream oil-spill detection and modeling.
"""

from __future__ import annotations

from ocean_sentinel.processing.models import (
    BackscatterUnit,
    NormalizationMetadata,
    NormalizationMethod,
    PreprocessedBand,
    PreprocessedBandStats,
    PreprocessedSAR,
    PreprocessingConfig,
    PreprocessingResult,
    QualityMetrics,
)
from ocean_sentinel.processing.sar import SARPreprocessor

__all__ = [
    "BackscatterUnit",
    "NormalizationMetadata",
    "NormalizationMethod",
    "PreprocessedBand",
    "PreprocessedBandStats",
    "PreprocessedSAR",
    "PreprocessingConfig",
    "PreprocessingResult",
    "QualityMetrics",
    "SARPreprocessor",
]
