"""PyTorch Dataset wrapper for the Trujillo Part I oil-spill SAR dataset.

Provides a lazy, leakage-safe, reproducible ``torch.utils.data.Dataset``
implementation on top of the existing ingestion and split infrastructure.

Key design decisions
--------------------
Lazy loading
    The Dataset holds only a tile index (a list of ``TileManifestEntry``).
    Pixels are read from disk on demand in ``__getitem__``: one rasterio
    windowed read for the exact 512×512 tile region.  No full 2048×2048
    patches or batches of patches are materialised simultaneously.

dB semantics
    Native dB values are preserved until the explicit normalization step.
    ``BackscatterUnit.DECIBEL`` is hard-wired.  No 10·log10 re-application.
    No linear conversion unless the caller explicitly opts in.

Normalization
    If the manifest carries ``NormalizationStats``, per-channel z-score
    standardization is applied:
        x_norm = (x_db - channel_mean) / channel_std
    Statistics are derived from the training split only (enforced by
    ``GroupBasedSplitter.compute_normalization_stats``).  Validation and
    test instances receive the same training-derived parameters.

    If the manifest has no normalization stats (``normalization_stats is None``),
    the raw dB array is returned without modification.  This is the correct
    default when calling code has not yet computed statistics.

Channel semantics
    POLARIZATION_MAPPING = UNKNOWN.  The two channels are treated as
    ``channel_0`` and ``channel_1`` throughout.  No VV/VH labels are added.

Tensor contract
    image  : torch.float32, shape (2, 512, 512) — channels × height × width
    mask   : torch.float32, shape (1, 512, 512) — binary {0, 1}
"""

from __future__ import annotations

import warnings
from pathlib import Path, PureWindowsPath
from typing import Optional

import numpy as np

try:
    from torch.utils.data import DataLoader
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

import rasterio
from rasterio.errors import NotGeoreferencedWarning
from rasterio.windows import Window

from ocean_sentinel.ingestion.split import DatasetManifest, SplitName, TileManifestEntry
from ocean_sentinel.ingestion.firewall import (
    assert_no_part_iii_leakage,
    validate_manifest_against_firewall,
)


def _require_torch() -> None:
    if not _TORCH_AVAILABLE:
        raise ImportError(
            "PyTorch is required for TrujilloTileDataset. "
            "Install it via: pip install torch"
        )


class TrujilloTileDataset:
    """Lazy PyTorch Dataset for Trujillo Part I 512×512 SAR tiles.

    Parameters
    ----------
    manifest : DatasetManifest
        Populated manifest including split assignments and (optionally)
        normalization statistics.
    split : SplitName
        Which partition to expose (TRAIN, VAL, or TEST).
    normalize : bool
        Whether to apply training-derived z-score normalization.
        Default True.  If True but ``manifest.normalization_stats`` is None,
        a RuntimeError is raised at construction time so the caller cannot
        silently receive unnormalized data thinking it is normalized.

    Raises
    ------
    ImportError
        If PyTorch is not installed.
    RuntimeError
        If ``normalize=True`` but the manifest contains no normalization stats.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        manifest: DatasetManifest,
        split: SplitName,
        normalize: bool = True,
        transform: Optional[object] = None,
        data_root: Optional[Path | str] = None,
    ) -> None:
        _require_torch()

        self.manifest = manifest
        self.split = split
        self.normalize = normalize
        self.transform = transform
        self.data_root = Path(data_root) if data_root is not None else None

        # Absolute Scientific Firewall: Trujillo Part III isolation
        if self.data_root is not None:
            assert_no_part_iii_leakage([self.data_root], context="TrujilloTileDataset(data_root)")
        validate_manifest_against_firewall(manifest, context=f"TrujilloTileDataset({split})")

        self._tiles: list[TileManifestEntry] = manifest.tiles_for_split(split)

        # Build a patch-stem → (image_path, mask_path) index for O(1) lookup
        # during __getitem__ without re-iterating the full patch list each call.
        if self.data_root is not None:
            self._patch_paths: dict[str, tuple[str, str]] = {
                p.patch_stem: (
                    str(self.data_root / "images" / "Oil" / PureWindowsPath(p.image_path).name),
                    str(self.data_root / "masks" / "Mask_oil" / PureWindowsPath(p.mask_path).name),
                )
                for p in manifest.patches
            }
        else:
            self._patch_paths = {
                p.patch_stem: (p.image_path, p.mask_path)
                for p in manifest.patches
            }

        # Validate normalization contract
        if normalize and manifest.normalization_stats is None:
            raise RuntimeError(
                "normalize=True but manifest.normalization_stats is None. "
                "Run GroupBasedSplitter.compute_normalization_stats() first "
                "and attach the result to the manifest before constructing "
                "TrujilloTileDataset with normalize=True."
            )

        # Cache normalization params as numpy arrays for fast __getitem__
        if normalize and manifest.normalization_stats is not None:
            stats = manifest.normalization_stats
            self._norm_mean = np.array(stats.channel_means, dtype=np.float32)
            self._norm_std = np.array(stats.channel_stds, dtype=np.float32)
            # Guard against zero std (constant channels)
            self._norm_std = np.where(self._norm_std < 1e-8, 1.0, self._norm_std)
        else:
            self._norm_mean = None
            self._norm_std = None

    # ------------------------------------------------------------------
    # Dataset protocol
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        """Total number of tiles in this split."""
        return len(self._tiles)

    def __getitem__(self, idx: int) -> tuple:
        """Load and return one tile as (image_tensor, mask_tensor).

        Performs a rasterio windowed read of exactly the tile region —
        only the 512×512 window is read from the 2048×2048 file, keeping
        memory usage bounded.

        Parameters
        ----------
        idx : int
            Tile index within the split (0 … len-1).

        Returns
        -------
        image : torch.Tensor, dtype float32, shape (C, H, W)
            Per-channel dB backscatter values (possibly z-score normalized).
        mask : torch.Tensor, dtype float32, shape (1, H, W)
            Binary segmentation mask {0.0, 1.0}.
        """
        import torch

        entry = self._tiles[idx]

        # Resolve image and mask paths via the patch index
        img_path, mask_path = self._patch_paths[entry.parent_stem]

        # Windowed read: only reads the 512×512 region, not the full patch
        window = Window(
            col_off=entry.col_offset,
            row_off=entry.row_offset,
            width=entry.width,
            height=entry.height,
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=NotGeoreferencedWarning)
            with rasterio.open(img_path) as src:
                img = src.read(window=window).astype(np.float32)   # (C, H, W)
            with rasterio.open(mask_path) as src:
                mask = src.read(1, window=window).astype(np.float32)  # (H, W)

        # Apply training-derived z-score normalization channel-wise
        if self.normalize and self._norm_mean is not None:
            for c in range(img.shape[0]):
                img[c] = (img[c] - self._norm_mean[c]) / self._norm_std[c]

        image_tensor = torch.from_numpy(img)                        # (C, H, W)
        mask_tensor = torch.from_numpy(mask).unsqueeze(0)           # (1, H, W)

        if self.transform is not None:
            image_tensor, mask_tensor = self.transform(image_tensor, mask_tensor)

        return image_tensor, mask_tensor

    # ------------------------------------------------------------------
    # DataLoader factory
    # ------------------------------------------------------------------

    def make_dataloader(
        self,
        batch_size: int = 8,
        shuffle: bool = False,
        num_workers: int = 0,
        pin_memory: bool = False,
    ) -> "DataLoader":
        """Return a configured ``torch.utils.data.DataLoader``.

        Parameters
        ----------
        batch_size : int
            Number of tiles per batch.
        shuffle : bool
            Whether to shuffle tile order each epoch.  Recommended True
            for training, False for val/test (deterministic evaluation order).
        num_workers : int
            Worker processes for parallel prefetch.  Set 0 on Windows or
            when running tests (avoids spawn overhead).
        pin_memory : bool
            Whether to pin page memory for faster GPU transfer.

        Returns
        -------
        DataLoader
            Configured dataloader.
        """
        from torch.utils.data import DataLoader as TorchDataLoader

        # Wrap self as a torch Dataset
        wrapper = _TorchDatasetWrapper(self)
        return TorchDataLoader(
            wrapper,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            pin_memory=pin_memory,
        )

    # ------------------------------------------------------------------
    # Tile introspection
    # ------------------------------------------------------------------

    def tile_entry(self, idx: int) -> TileManifestEntry:
        """Return the manifest entry for tile *idx* (read-only)."""
        return self._tiles[idx]


class _TorchDatasetWrapper:
    """Thin wrapper so TrujilloTileDataset can be passed to torch DataLoader.

    Implements the ``__len__`` / ``__getitem__`` protocol required by
    ``torch.utils.data.Dataset`` without inheriting from it (the parent class
    is ``TrujilloTileDataset``, which avoids a hard torch import at module
    import time).
    """

    def __init__(self, inner: TrujilloTileDataset) -> None:
        self._inner = inner

    def __len__(self) -> int:
        return len(self._inner)

    def __getitem__(self, idx: int) -> tuple:
        return self._inner[idx]


# ---------------------------------------------------------------------------
# Manifest generation helper (convenience function)
# ---------------------------------------------------------------------------


def build_and_save_manifest(
    loader,
    manifest_path: Path | str,
    *,
    compute_norm_stats: bool = True,
    seed: int = 42,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    max_norm_patches: Optional[int] = None,
) -> DatasetManifest:
    """Build a manifest, optionally compute normalization stats, and save.

    Convenience function wrapping ``GroupBasedSplitter.build_manifest`` and
    ``GroupBasedSplitter.compute_normalization_stats``.

    Parameters
    ----------
    loader : TrujilloDatasetLoader
        Fully initialised loader.
    manifest_path : Path | str
        Where to write the JSON manifest.
    compute_norm_stats : bool
        Whether to compute training-split normalization statistics and embed
        them in the manifest.  Default True.
    seed, train_ratio, val_ratio, test_ratio
        Split configuration (see ``GroupBasedSplitter``).
    max_norm_patches : int | None
        Limit statistics computation to this many training patches (for
        fast smoke-tests on subsets).

    Returns
    -------
    DatasetManifest
        Saved manifest.
    """
    from ocean_sentinel.ingestion.split import GroupBasedSplitter

    splitter = GroupBasedSplitter(
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        seed=seed,
    )
    manifest = splitter.build_manifest(loader)

    if compute_norm_stats:
        norm_stats = splitter.compute_normalization_stats(
            manifest, loader, max_patches=max_norm_patches
        )
        manifest.normalization_stats = norm_stats

    manifest.save(manifest_path)
    return manifest
