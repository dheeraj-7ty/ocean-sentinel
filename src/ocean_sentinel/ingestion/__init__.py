"""Offline dataset ingestion, provenance, pairing, validation, and tiling package."""

from ocean_sentinel.ingestion.dataset import (
    TrujilloTileDataset,
    build_and_save_manifest,
)
from ocean_sentinel.ingestion.models import (
    DatasetPatchMetadata,
    DatasetPatchProvenance,
    DatasetSample,
    DatasetValidationConfig,
    DatasetValidationResult,
    TileDefinition,
    TileProvenance,
    TileSample,
    TilingConfig,
    VerificationStatus,
)
from ocean_sentinel.ingestion.split import (
    DatasetManifest,
    GroupBasedSplitter,
    NormalizationStats,
    PatchManifestEntry,
    SpatialGroupSplitter,
    SplitName,
    SplitSummary,
    TileManifestEntry,
)
from ocean_sentinel.ingestion.tiling import (
    compute_tile_definitions,
    tile_sample,
)
from ocean_sentinel.ingestion.trujillo import (
    TrujilloDatasetLoader,
)

__all__ = [
    # models
    "VerificationStatus",
    "DatasetPatchProvenance",
    "DatasetPatchMetadata",
    "TileProvenance",
    "TileDefinition",
    "TilingConfig",
    "DatasetSample",
    "TileSample",
    "DatasetValidationConfig",
    "DatasetValidationResult",
    # tiling
    "compute_tile_definitions",
    "tile_sample",
    # loader
    "TrujilloDatasetLoader",
    # split
    "SplitName",
    "PatchManifestEntry",
    "TileManifestEntry",
    "SplitSummary",
    "NormalizationStats",
    "DatasetManifest",
    "GroupBasedSplitter",
    "SpatialGroupSplitter",
    # dataset
    "TrujilloTileDataset",
    "build_and_save_manifest",
]
