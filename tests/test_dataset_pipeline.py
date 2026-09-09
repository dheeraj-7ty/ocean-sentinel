"""Phase 2.1 — Dataset pipeline tests: manifest, split, leakage, PyTorch Dataset.

Test architecture
-----------------
All tests use *synthetic* data (in-memory numpy arrays written to temporary
TIFF files) — no real Trujillo data is loaded.  This keeps tests fast,
CI-safe, and independent of large-file availability.

Real-data smoke tests (benchmark, full manifest) are kept in a separate
integration test file or run manually.

Coverage
--------
- DatasetManifest generation and JSON round-trip
- Deterministic split assignment (same seed → same result)
- Group leakage: no group_key appears in more than one split
- Tile membership: all tiles from a patch are in the same split
- Split totals are exhaustive (no patch/tile dropped)
- Normalization stats computed from TRAIN only
- Validation/test use training-derived stats (not their own)
- TrujilloTileDataset: tensor shapes, dtypes, binary mask
- Lazy loading: __getitem__ does NOT load all patches
- DataLoader batching
- normalize=True fails if manifest lacks normalization stats
- Manifest save/load round-trip preserves all fields
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds

# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

try:
    import torch as _torch_check  # noqa: F401

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

pytestmark_torch = pytest.mark.skipif(
    not TORCH_AVAILABLE, reason="PyTorch not installed"
)

# ---------------------------------------------------------------------------
# Synthetic dataset fixture
# ---------------------------------------------------------------------------

NATIVE_H = 512   # Synthetic TIFF height (= tile height → 1 tile per patch)
NATIVE_W = 512   # Synthetic TIFF width
TILE_H = 512
TILE_W = 512
N_CHANNELS = 2
N_PATCHES = 20   # Small enough for fast tests, large enough to split meaningfully


def _write_synthetic_tif(
    path: Path,
    height: int,
    width: int,
    n_bands: int,
    dtype: str = "float32",
    data: np.ndarray | None = None,
) -> None:
    """Write a minimal synthetic GeoTIFF to *path*."""
    if data is None:
        # dB-range values (negative floats) — realistic for SAR
        data = np.random.default_rng(0).uniform(-30.0, 0.0, (n_bands, height, width)).astype(dtype)
    transform = from_bounds(0, 0, 1, 1, width, height)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=n_bands,
            dtype=dtype,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(data)


def _write_synthetic_mask(
    path: Path,
    height: int,
    width: int,
    foreground_fraction: float = 0.05,
) -> None:
    """Write a binary uint8 mask TIFF."""
    rng = np.random.default_rng(1)
    mask = (rng.random((height, width)) < foreground_fraction).astype(np.uint8)
    transform = from_bounds(0, 0, 1, 1, width, height)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="uint8",
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(mask[np.newaxis, :, :])


@pytest.fixture(scope="module")
def synthetic_dataset_dir(tmp_path_factory) -> dict:
    """Create a synthetic Trujillo-like directory with N_PATCHES pairs.

    Returns a dict with:
        images_dir : Path  (contains Oil/ subdirectory)
        masks_dir  : Path  (contains Mask_oil/ subdirectory)
        stems      : list[str]
    """
    base = tmp_path_factory.mktemp("trujillo_synthetic")
    images_dir = base / "Oil"
    masks_dir = base / "Mask_oil"
    images_dir.mkdir()
    masks_dir.mkdir()

    stems = [f"{i:05d}" for i in range(N_PATCHES)]
    for stem in stems:
        _write_synthetic_tif(
            images_dir / f"{stem}.tif",
            height=NATIVE_H,
            width=NATIVE_W,
            n_bands=N_CHANNELS,
        )
        _write_synthetic_mask(
            masks_dir / f"{stem}.tif",
            height=NATIVE_H,
            width=NATIVE_W,
        )

    return {"images_dir": base, "masks_dir": base, "stems": stems}


@pytest.fixture(scope="module")
def loader(synthetic_dataset_dir):
    """Return a TrujilloDatasetLoader over the synthetic dataset."""
    from ocean_sentinel.ingestion.trujillo import TrujilloDatasetLoader

    return TrujilloDatasetLoader(
        images_dir=synthetic_dataset_dir["images_dir"],
        masks_dir=synthetic_dataset_dir["masks_dir"],
    )


@pytest.fixture(scope="module")
def splitter():
    """Return a GroupBasedSplitter with default parameters."""
    from ocean_sentinel.ingestion.split import GroupBasedSplitter, TilingConfig

    return GroupBasedSplitter(
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=42,
        tiling_config=TilingConfig(
            tile_height=TILE_H,
            tile_width=TILE_W,
            stride_y=TILE_H,
            stride_x=TILE_W,
            edge_handling="drop",
        ),
    )


@pytest.fixture(scope="module")
def manifest_no_norm(loader, splitter):
    """Build a manifest without normalization stats."""
    return splitter.build_manifest(
        loader,
        native_height=NATIVE_H,
        native_width=NATIVE_W,
    )


@pytest.fixture(scope="module")
def manifest_with_norm(loader, splitter, manifest_no_norm):
    """Compute normalization stats and attach to manifest."""
    stats = splitter.compute_normalization_stats(manifest_no_norm, loader)
    # NormalizationStats is a dataclass, attach directly
    manifest_no_norm.normalization_stats = stats
    return manifest_no_norm


# ===========================================================================
# 1. Manifest generation
# ===========================================================================


class TestManifestGeneration:
    def test_patch_count_equals_n_patches(self, manifest_no_norm):
        assert len(manifest_no_norm.patches) == N_PATCHES

    def test_tile_count_equals_patches_times_tiles_per_patch(self, manifest_no_norm):
        # Synthetic TIFFs are 512×512; tile config is 512×512 with stride 512
        # → exactly 1 tile per patch
        tiles_per_patch = manifest_no_norm.tiles_per_patch
        assert tiles_per_patch == 1
        assert len(manifest_no_norm.tiles) == N_PATCHES * tiles_per_patch

    def test_all_splits_populated(self, manifest_no_norm):
        from ocean_sentinel.ingestion.split import SplitName

        splits = {p.split for p in manifest_no_norm.patches}
        assert SplitName.TRAIN in splits
        assert SplitName.VAL in splits
        assert SplitName.TEST in splits

    def test_split_totals_exhaustive(self, manifest_no_norm):
        from ocean_sentinel.ingestion.split import SplitName

        n_train = len(manifest_no_norm.patches_for_split(SplitName.TRAIN))
        n_val = len(manifest_no_norm.patches_for_split(SplitName.VAL))
        n_test = len(manifest_no_norm.patches_for_split(SplitName.TEST))
        assert n_train + n_val + n_test == N_PATCHES

    def test_approximate_split_ratios(self, manifest_no_norm):
        from ocean_sentinel.ingestion.split import SplitName

        n_train = len(manifest_no_norm.patches_for_split(SplitName.TRAIN))
        n_val = len(manifest_no_norm.patches_for_split(SplitName.VAL))
        # With N=20 we get: floor(0.70*20)=14 train, floor(0.15*20)=3 val, 3 test
        assert n_train == 14
        assert n_val == 3

    def test_radiometric_unit_is_db(self, manifest_no_norm):
        for p in manifest_no_norm.patches:
            assert p.radiometric_unit == "dB"

    def test_polarization_mapping_unknown(self, manifest_no_norm):
        assert manifest_no_norm.polarization_mapping == "UNKNOWN"

    def test_dataset_name_correct(self, manifest_no_norm):
        assert manifest_no_norm.dataset_name == "trujillo_2024_part_i"

    def test_patch_image_paths_exist(self, manifest_no_norm):
        for p in manifest_no_norm.patches:
            assert Path(p.image_path).exists(), f"Missing image: {p.image_path}"

    def test_patch_mask_paths_exist(self, manifest_no_norm):
        for p in manifest_no_norm.patches:
            assert Path(p.mask_path).exists(), f"Missing mask: {p.mask_path}"


# ===========================================================================
# 2. Deterministic split — reproducibility
# ===========================================================================


class TestSplitDeterminism:
    def test_same_seed_produces_identical_assignment(self, loader):
        from ocean_sentinel.ingestion.split import GroupBasedSplitter, TilingConfig

        cfg = TilingConfig(tile_height=TILE_H, tile_width=TILE_W,
                           stride_y=TILE_H, stride_x=TILE_W)
        s1 = GroupBasedSplitter(seed=42, tiling_config=cfg)
        s2 = GroupBasedSplitter(seed=42, tiling_config=cfg)
        m1 = s1.build_manifest(loader)
        m2 = s2.build_manifest(loader)
        for p1, p2 in zip(m1.patches, m2.patches):
            assert p1.patch_stem == p2.patch_stem
            assert p1.split == p2.split

    def test_different_seed_may_differ(self, loader):
        from ocean_sentinel.ingestion.split import GroupBasedSplitter, TilingConfig

        cfg = TilingConfig(tile_height=TILE_H, tile_width=TILE_W,
                           stride_y=TILE_H, stride_x=TILE_W)
        s1 = GroupBasedSplitter(seed=42, tiling_config=cfg)
        s2 = GroupBasedSplitter(seed=99, tiling_config=cfg)
        m1 = s1.build_manifest(loader)
        m2 = s2.build_manifest(loader)
        assignments1 = {p.patch_stem: p.split for p in m1.patches}
        assignments2 = {p.patch_stem: p.split for p in m2.patches}
        # Different seeds should produce at least one different assignment
        # (extremely unlikely to be identical for N=20)
        assert assignments1 != assignments2, (
            "Different seeds unexpectedly produced identical assignments"
        )

    def test_patch_order_is_deterministic_regardless_of_filesystem(self, loader):
        from ocean_sentinel.ingestion.split import GroupBasedSplitter, TilingConfig

        cfg = TilingConfig(tile_height=TILE_H, tile_width=TILE_W,
                           stride_y=TILE_H, stride_x=TILE_W)
        sp = GroupBasedSplitter(seed=42, tiling_config=cfg)
        m1 = sp.build_manifest(loader)
        m2 = sp.build_manifest(loader)
        stems1 = [p.patch_stem for p in m1.patches]
        stems2 = [p.patch_stem for p in m2.patches]
        assert stems1 == stems2


# ===========================================================================
# 3. Leakage prevention
# ===========================================================================


class TestLeakagePrevention:
    def test_no_group_key_in_more_than_one_split(self, manifest_no_norm):
        from ocean_sentinel.ingestion.split import SplitName

        train_keys = manifest_no_norm.group_keys_for_split(SplitName.TRAIN)
        val_keys = manifest_no_norm.group_keys_for_split(SplitName.VAL)
        test_keys = manifest_no_norm.group_keys_for_split(SplitName.TEST)

        assert train_keys.isdisjoint(val_keys), "TRAIN and VAL share group_keys!"
        assert train_keys.isdisjoint(test_keys), "TRAIN and TEST share group_keys!"
        assert val_keys.isdisjoint(test_keys), "VAL and TEST share group_keys!"

    def test_all_tiles_from_same_patch_in_same_split(self, manifest_no_norm):
        # Build a mapping: tile → split for each tile.  Then verify that all
        # tiles sharing the same parent_stem have the same split.
        stem_splits: dict[str, set] = {}
        for tile in manifest_no_norm.tiles:
            stem_splits.setdefault(tile.parent_stem, set()).add(tile.split)
        for stem, splits in stem_splits.items():
            assert len(splits) == 1, (
                f"Tiles from patch {stem} are split across: {splits}"
            )

    def test_patch_group_key_equals_stem(self, manifest_no_norm):
        for p in manifest_no_norm.patches:
            assert p.group_key == p.patch_stem

    def test_tile_group_key_equals_parent_stem(self, manifest_no_norm):
        for t in manifest_no_norm.tiles:
            assert t.group_key == t.parent_stem


# ===========================================================================
# 4. Manifest JSON round-trip
# ===========================================================================


class TestManifestSerialization:
    def test_save_and_load_round_trip(self, manifest_with_norm, tmp_path):
        from ocean_sentinel.ingestion.split import DatasetManifest

        out = tmp_path / "split_manifest.json"
        manifest_with_norm.save(out)
        loaded = DatasetManifest.load(out)

        # Check counts
        assert len(loaded.patches) == len(manifest_with_norm.patches)
        assert len(loaded.tiles) == len(manifest_with_norm.tiles)

        # Check split assignment for first patch
        assert loaded.patches[0].patch_stem == manifest_with_norm.patches[0].patch_stem
        assert loaded.patches[0].split == manifest_with_norm.patches[0].split

        # Check normalization stats
        assert loaded.normalization_stats is not None
        assert len(loaded.normalization_stats.channel_means) == N_CHANNELS

    def test_saved_json_is_valid(self, manifest_no_norm, tmp_path):
        out = tmp_path / "manifest_test.json"
        manifest_no_norm.save(out)
        with out.open() as fh:
            data = json.load(fh)
        assert "dataset_name" in data
        assert "patches" in data
        assert "tiles" in data
        assert "split_summaries" in data

    def test_saved_manifest_does_not_contain_pixel_arrays(self, manifest_no_norm, tmp_path):
        out = tmp_path / "manifest_pixels.json"
        manifest_no_norm.save(out)
        raw = out.read_text(encoding="utf-8")
        # The manifest must not contain base64 blobs or large float arrays
        assert len(raw) < 5 * 1024 * 1024, "Manifest is suspiciously large"

    def test_normalization_stats_round_trip(self, manifest_with_norm, tmp_path):
        from ocean_sentinel.ingestion.split import DatasetManifest

        out = tmp_path / "manifest_norm.json"
        manifest_with_norm.save(out)
        loaded = DatasetManifest.load(out)
        assert loaded.normalization_stats is not None
        np.testing.assert_allclose(
            loaded.normalization_stats.channel_means,
            manifest_with_norm.normalization_stats.channel_means,
            rtol=1e-5,
        )


# ===========================================================================
# 5. Normalization contract
# ===========================================================================


class TestNormalizationContract:
    def test_stats_computed_from_train_only(self, manifest_with_norm):
        assert manifest_with_norm.normalization_stats is not None
        assert manifest_with_norm.normalization_stats.computed_from_split == "train"

    def test_stats_have_correct_channel_count(self, manifest_with_norm):
        stats = manifest_with_norm.normalization_stats
        assert len(stats.channel_means) == N_CHANNELS
        assert len(stats.channel_stds) == N_CHANNELS
        assert len(stats.n_valid_pixels) == N_CHANNELS

    def test_stats_are_finite(self, manifest_with_norm):
        stats = manifest_with_norm.normalization_stats
        for m in stats.channel_means:
            assert np.isfinite(m), f"Mean is not finite: {m}"
        for s in stats.channel_stds:
            assert np.isfinite(s), f"Std is not finite: {s}"

    def test_stats_are_nonzero_for_non_constant_data(self, manifest_with_norm):
        stats = manifest_with_norm.normalization_stats
        for s in stats.channel_stds:
            assert s > 0.0, f"Std should be positive for random data, got {s}"

    def test_means_in_expected_db_range(self, manifest_with_norm):
        # Synthetic data is uniform(-30, 0) so mean ~ -15 dB
        stats = manifest_with_norm.normalization_stats
        for m in stats.channel_means:
            assert -35.0 < m < 5.0, f"Mean {m} is outside expected dB range"


# ===========================================================================
# 6. PyTorch Dataset (all require torch)
# ===========================================================================


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")
class TestTrujilloTileDataset:
    def test_dataset_length_matches_split(self, manifest_with_norm):
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=True)
        expected = len(manifest_with_norm.tiles_for_split(SplitName.TRAIN))
        assert len(ds) == expected

    def test_getitem_returns_tuple(self, manifest_with_norm):
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=True)
        item = ds[0]
        assert isinstance(item, tuple)
        assert len(item) == 2

    def test_image_tensor_shape(self, manifest_with_norm):
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=True)
        img, _ = ds[0]
        assert img.shape == (N_CHANNELS, TILE_H, TILE_W), (
            f"Image shape {img.shape} != ({N_CHANNELS}, {TILE_H}, {TILE_W})"
        )

    def test_mask_tensor_shape(self, manifest_with_norm):
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=True)
        _, mask = ds[0]
        assert mask.shape == (1, TILE_H, TILE_W), (
            f"Mask shape {mask.shape} != (1, {TILE_H}, {TILE_W})"
        )

    def test_image_tensor_dtype_float32(self, manifest_with_norm):
        import torch

        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=True)
        img, _ = ds[0]
        assert img.dtype == torch.float32

    def test_mask_tensor_dtype_float32(self, manifest_with_norm):
        import torch

        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=True)
        _, mask = ds[0]
        assert mask.dtype == torch.float32

    def test_mask_binary_values(self, manifest_with_norm):
        import torch

        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=True)
        for i in range(min(5, len(ds))):
            _, mask = ds[i]
            unique_vals = torch.unique(mask)
            for v in unique_vals:
                assert v.item() in (0.0, 1.0), f"Non-binary mask value: {v.item()}"

    def test_val_dataset_length(self, manifest_with_norm):
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.VAL, normalize=True)
        expected = len(manifest_with_norm.tiles_for_split(SplitName.VAL))
        assert len(ds) == expected

    def test_test_dataset_length(self, manifest_with_norm):
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TEST, normalize=True)
        expected = len(manifest_with_norm.tiles_for_split(SplitName.TEST))
        assert len(ds) == expected

    def test_normalize_false_preserves_raw_db_range(self, manifest_with_norm):
        """Without normalization, raw dB values should be in expected range."""
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=False)
        img, _ = ds[0]
        # Synthetic data is uniform(-30, 0) so values must be in [-30, 0]
        assert img.min().item() >= -35.0
        assert img.max().item() <= 5.0

    def test_normalize_true_fails_without_stats(self, loader, splitter):
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        # Build a fresh isolated manifest with no normalization stats
        fresh_manifest = splitter.build_manifest(
            loader, native_height=NATIVE_H, native_width=NATIVE_W
        )
        # Confirm it has no stats
        assert fresh_manifest.normalization_stats is None
        with pytest.raises(RuntimeError, match="normalization_stats is None"):
            TrujilloTileDataset(fresh_manifest, SplitName.TRAIN, normalize=True)

    def test_tile_entry_returns_correct_metadata(self, manifest_with_norm):
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=False)
        entry = ds.tile_entry(0)
        assert entry.split == SplitName.TRAIN
        assert entry.height == TILE_H
        assert entry.width == TILE_W


# ===========================================================================
# 7. Lazy loading
# ===========================================================================


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")
class TestLazyLoading:
    def test_dataset_init_does_not_load_pixels(self, manifest_with_norm):
        """Constructing TrujilloTileDataset must not read any raster pixels."""
        import unittest.mock as mock

        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        open_calls = []
        original_open = rasterio.open

        def counting_open(*args, **kwargs):
            open_calls.append(args[0])
            return original_open(*args, **kwargs)

        # Patch in the dataset module's namespace
        patch_target = "ocean_sentinel.ingestion.dataset.rasterio.open"
        with mock.patch(patch_target, side_effect=counting_open):
            TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=True)

        assert len(open_calls) == 0, (
            f"Dataset __init__ opened {len(open_calls)} raster files unexpectedly"
        )

    def test_getitem_opens_exactly_two_files(self, manifest_with_norm):
        """Each __getitem__ must open exactly one image + one mask file."""
        import unittest.mock as mock

        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        original_open = rasterio.open
        open_calls = []

        def counting_open(*args, **kwargs):
            open_calls.append(str(args[0]))
            return original_open(*args, **kwargs)

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=True)
        # Patch in the dataset module's namespace
        patch_target = "ocean_sentinel.ingestion.dataset.rasterio.open"
        with mock.patch(patch_target, side_effect=counting_open):
            _ = ds[0]

        assert len(open_calls) == 2, (
            f"Expected 2 rasterio.open calls per __getitem__, got {len(open_calls)}"
        )


# ===========================================================================
# 8. DataLoader compatibility
# ===========================================================================


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")
class TestDataLoaderCompatibility:
    def test_make_dataloader_returns_dataloader(self, manifest_with_norm):
        from torch.utils.data import DataLoader

        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=True)
        dl = ds.make_dataloader(batch_size=2, shuffle=False, num_workers=0)
        assert isinstance(dl, DataLoader)

    def test_dataloader_batch_shape(self, manifest_with_norm):
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=True)
        dl = ds.make_dataloader(batch_size=2, shuffle=False, num_workers=0)
        batch = next(iter(dl))
        imgs, masks = batch
        assert imgs.shape[1] == N_CHANNELS    # channels
        assert imgs.shape[2] == TILE_H        # height
        assert imgs.shape[3] == TILE_W        # width
        assert masks.shape[1] == 1            # single mask channel

    def test_dataloader_iterates_all_samples(self, manifest_with_norm):
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.TRAIN, normalize=True)
        dl = ds.make_dataloader(batch_size=4, shuffle=False, num_workers=0)
        total = sum(imgs.shape[0] for imgs, _ in dl)
        assert total == len(ds)

    def test_val_dataloader_deterministic(self, manifest_with_norm):
        """Iterating the val DataLoader twice should yield identical tensor order."""
        import torch

        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import SplitName

        ds = TrujilloTileDataset(manifest_with_norm, SplitName.VAL, normalize=True)
        if len(ds) == 0:
            pytest.skip("Val split is empty for this synthetic dataset size")
        dl = ds.make_dataloader(batch_size=2, shuffle=False, num_workers=0)
        pass1 = [imgs.clone() for imgs, _ in dl]
        pass2 = [imgs.clone() for imgs, _ in dl]
        for p1, p2 in zip(pass1, pass2):
            assert torch.allclose(p1, p2)


# ===========================================================================
# 9. Split summary statistics
# ===========================================================================


class TestSplitSummaries:
    def test_split_summaries_all_three_present(self, manifest_no_norm):
        from ocean_sentinel.ingestion.split import SplitName

        split_names = {s.split for s in manifest_no_norm.split_summaries}
        assert SplitName.TRAIN in split_names
        assert SplitName.VAL in split_names
        assert SplitName.TEST in split_names

    def test_split_summary_totals_match_actual(self, manifest_no_norm):
        for summary in manifest_no_norm.split_summaries:
            actual_patches = len(manifest_no_norm.patches_for_split(summary.split))
            actual_tiles = len(manifest_no_norm.tiles_for_split(summary.split))
            assert summary.n_patches == actual_patches
            assert summary.n_tiles == actual_tiles


# ===========================================================================
# 10. Ratio validation in GroupBasedSplitter
# ===========================================================================


class TestSplitterValidation:
    def test_invalid_ratio_sum_raises(self):
        from ocean_sentinel.ingestion.split import GroupBasedSplitter

        with pytest.raises(ValueError, match="sum to 1.0"):
            GroupBasedSplitter(train_ratio=0.8, val_ratio=0.1, test_ratio=0.2)

    def test_valid_ratio_sum_succeeds(self):
        from ocean_sentinel.ingestion.split import GroupBasedSplitter

        sp = GroupBasedSplitter(train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
        assert abs(sp.train_ratio + sp.val_ratio + sp.test_ratio - 1.0) < 1e-6


# ===========================================================================
# 11. Cross-platform manifest path resolution regression tests (Gate 4.3B)
# ===========================================================================


@pytest.mark.unit
class TestCrossPlatformManifestPathResolution:
    """Permanent regression test suite for cross-platform manifest path handling.

    Protects against the Linux runtime defect discovered during Gate 4.3B canary v4:
    Manifest stores Windows-style absolute paths (e.g. D:\\Projects\\...\\00000.tif).
    On Linux/POSIX runtimes (such as Kaggle or Docker), standard PosixPath does not
    treat backslash as a path separator, causing Path(windows_path).name to return the
    entire Windows path string instead of just '00000.tif'.
    This resulted in invalid paths like:
        /kaggle/input/ocean-sentinel-trujillo-corpus/images/Oil/D:\\Projects\\...\\00000.tif
    The production fix uses PureWindowsPath(p.image_path).name in TrujilloTileDataset.
    """

    def test_pure_windows_path_vs_posix_path_contrast(self):
        """Demonstrate the POSIX failure mode and PureWindowsPath correction."""
        from pathlib import PurePosixPath, PureWindowsPath

        windows_path = (
            r"D:\Projects\ocean-sentinel\data\raw\trujillo_2024\images\Oil\00000.tif"
        )
        # On POSIX, PurePosixPath treats backslashes as regular characters,
        # so .name fails to extract just the leaf filename.
        assert PurePosixPath(windows_path).name == windows_path
        # PureWindowsPath parses Windows-style separators on any operating system.
        assert PureWindowsPath(windows_path).name == "00000.tif"

    def test_trujillo_tile_dataset_resolves_under_linux_posix_semantics(self, monkeypatch):
        """Exercise production TrujilloTileDataset under simulated Linux POSIX semantics.

        Demonstrates that a Windows-style manifest path:
            D:\\Projects\\ocean-sentinel\\data\\raw\\trujillo_2024\\images\\Oil\\00000.tif
        resolves strictly to:
            /kaggle/input/ocean-sentinel-trujillo-corpus/images/Oil/00000.tif
        and NOT:
            /kaggle/input/ocean-sentinel-trujillo-corpus/images/Oil/D:\\Projects\\...
        when running under Linux/POSIX path semantics.
        """
        from pathlib import PurePosixPath
        import ocean_sentinel.ingestion.dataset as ds_mod
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import (
            DatasetManifest,
            PatchManifestEntry,
            TileManifestEntry,
            SplitName,
            SplitSummary,
        )

        win_img = (
            r"D:\Projects\ocean-sentinel\data\raw\trujillo_2024\images\Oil\00000.tif"
        )
        win_mask = (
            r"D:\Projects\ocean-sentinel\data\raw\trujillo_2024\masks\Mask_oil\00000.tif"
        )

        patch = PatchManifestEntry(
            patch_stem="00000",
            image_path=win_img,
            mask_path=win_mask,
            group_key="00000",
            height=2048,
            width=2048,
            channels=2,
            dtype="float32",
            crs="EPSG:4326",
            radiometric_unit="dB",
            split=SplitName.TRAIN,
        )
        tile = TileManifestEntry(
            tile_id="00000_r0000_c0000",
            parent_stem="00000",
            group_key="00000",
            split=SplitName.TRAIN,
            row_idx=0,
            col_idx=0,
            row_offset=0,
            col_offset=0,
            height=512,
            width=512,
        )
        manifest = DatasetManifest(
            dataset_name="regression_test",
            source_archive="test.tar",
            zenodo_record="test",
            audit_report_path="test_audit.json",
            radiometric_unit="dB",
            polarization_mapping="unknown",
            split_seed=42,
            split_strategy="spatial",
            train_ratio=0.7,
            val_ratio=0.15,
            test_ratio=0.15,
            tile_height=512,
            tile_width=512,
            tile_stride_y=512,
            tile_stride_x=512,
            tiles_per_patch=16,
            patches=[patch],
            tiles=[tile],
            split_summaries=[SplitSummary(split=SplitName.TRAIN, n_patches=1, n_tiles=1)],
        )

        # Simulate Linux/POSIX runtime by monkeypatching Path in dataset module
        monkeypatch.setattr(ds_mod, "Path", PurePosixPath)

        cloud_root = "/kaggle/input/ocean-sentinel-trujillo-corpus"
        ds = TrujilloTileDataset(
            manifest=manifest,
            split=SplitName.TRAIN,
            data_root=cloud_root,
            normalize=False,
        )

        resolved_img, resolved_mask = ds._patch_paths["00000"]
        expected_img = f"{cloud_root}/images/Oil/00000.tif"
        expected_mask = f"{cloud_root}/masks/Mask_oil/00000.tif"

        assert resolved_img == expected_img, (
            f"Expected {expected_img} but got {resolved_img}. "
            f"Windows path was not properly parsed under POSIX semantics!"
        )
        assert resolved_mask == expected_mask, (
            f"Expected {expected_mask} but got {resolved_mask}. "
            f"Windows path was not properly parsed under POSIX semantics!"
        )

    def test_production_manifest_paths_resolve_cleanly_if_manifest_present(self):
        """If canonical spatial split manifest is present, verify all patches resolve without path pollution."""
        from pathlib import Path, PureWindowsPath
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
        from ocean_sentinel.ingestion.split import DatasetManifest, SplitName

        project_root = Path(__file__).resolve().parent.parent
        manifest_path = project_root / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
        if not manifest_path.exists():
            pytest.skip("Production manifest not present in workspace")

        manifest = DatasetManifest.load(manifest_path)
        data_root = "/mock/kaggle/input/ocean-sentinel-trujillo-corpus"
        ds = TrujilloTileDataset(
            manifest=manifest,
            split=SplitName.TRAIN,
            data_root=data_root,
            normalize=False,
        )

        for patch in manifest.patches:
            stem = patch.patch_stem
            img_p, mask_p = ds._patch_paths[stem]
            leaf_img = PureWindowsPath(img_p).name
            leaf_mask = PureWindowsPath(mask_p).name
            assert leaf_img == f"{stem}.tif", f"Leaf image mismatch for stem {stem}: {leaf_img}"
            assert leaf_mask == f"{stem}.tif", f"Leaf mask mismatch for stem {stem}: {leaf_mask}"
            assert "D:" not in leaf_img
            assert "\\" not in leaf_img
            assert "D:" not in leaf_mask
            assert "\\" not in leaf_mask

