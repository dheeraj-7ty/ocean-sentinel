"""Deterministic manifest generation and leakage-safe group-based split for Trujillo Part I.

Implements:
- DatasetManifest: machine-readable record of dataset identity, patch info, and tile catalogue.
- GroupBasedSplitter: deterministic 70/15/15 train/val/test partition at the patch-stem level.
- NormalizationStats: per-channel statistics derived exclusively from the training split.

Split design
------------
The split unit is the *parent patch stem*, not the individual tile.  Every tile
derived from the same 2048×2048 patch is assigned to the same partition, giving
hard spatial leakage prevention.

Because Trujillo Part I is fully positive (every patch contains oil), conventional
stratified-group splitting by class label is degenerate.  Instead we use a
deterministic sorted-group assignment:

  1. Sort stems lexicographically (guarantees filesystem-order independence).
  2. Use a seeded random.shuffle of the sorted list (reproducible permutation).
  3. Assign the first floor(0.70 * N) groups to TRAIN, the next floor(0.15 * N)
     to VAL, and the remainder to TEST.

The same seed always produces the same assignment (verified by tests).

The manifest is persisted to JSON so downstream code never has to recompute it.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from ocean_sentinel.ingestion.models import TilingConfig
from ocean_sentinel.ingestion.tiling import compute_tile_definitions


class SplitName(str, Enum):
    """Dataset split partition names."""

    TRAIN = "train"
    VAL = "val"
    TEST = "test"


# ---------------------------------------------------------------------------
# Manifest entry models (pure dataclasses – no Pydantic overhead for large lists)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PatchManifestEntry:
    """Manifest record for one Trujillo patch."""

    patch_stem: str
    image_path: str           # Relative or absolute str path to image TIFF
    mask_path: str            # Relative or absolute str path to mask TIFF
    group_key: str            # Leakage partition key (== patch_stem for Trujillo)
    height: int
    width: int
    channels: int
    dtype: str
    crs: Optional[str]
    radiometric_unit: str     # "dB" or "linear"
    split: SplitName          # Assigned partition


@dataclass(frozen=True)
class TileManifestEntry:
    """Manifest record for one tile derived from a parent patch."""

    tile_id: str
    parent_stem: str
    group_key: str
    split: SplitName
    row_idx: int
    col_idx: int
    row_offset: int
    col_offset: int
    height: int
    width: int


@dataclass
class NormalizationStats:
    """Per-channel normalization statistics derived from the TRAINING split only.

    Statistics are computed over valid (finite) dB values from all training tiles.
    They are persisted in the manifest and reused by validation and test splits
    to prevent test-set information leaking into normalization.

    Channel ordering matches the image band order: channel_0, channel_1 (unknown
    polarization mapping until authoritative evidence is discovered).
    """

    channel_means: list[float]   # Per-channel mean of valid training pixels
    channel_stds: list[float]    # Per-channel std  of valid training pixels
    n_valid_pixels: list[int]    # Total valid pixels per channel used for computation
    computed_from_split: str = "train"

    def to_dict(self) -> dict:
        return {
            "computed_from_split": self.computed_from_split,
            "channel_means": self.channel_means,
            "channel_stds": self.channel_stds,
            "n_valid_pixels": self.n_valid_pixels,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NormalizationStats":
        return cls(
            channel_means=d["channel_means"],
            channel_stds=d["channel_stds"],
            n_valid_pixels=d["n_valid_pixels"],
            computed_from_split=d.get("computed_from_split", "train"),
        )


@dataclass
class SplitSummary:
    """Summary statistics for one split partition."""

    split: SplitName
    n_patches: int
    n_tiles: int


# ---------------------------------------------------------------------------
# DatasetManifest
# ---------------------------------------------------------------------------


@dataclass
class DatasetManifest:
    """Machine-readable dataset manifest for Trujillo Part I Phase 2.1.

    Contains:
    - Dataset identity metadata (name, archive, audit reference).
    - Per-patch provenance and split assignment.
    - Derived tile catalogue.
    - Split summary statistics.
    - Normalization statistics (training-derived only).
    - Split configuration (seed, ratios, method).
    """

    # Dataset identity
    dataset_name: str
    source_archive: str
    zenodo_record: str
    audit_report_path: str
    radiometric_unit: str           # "dB" for Trujillo Part I
    polarization_mapping: str       # "UNKNOWN" until authoritative evidence found

    # Split configuration
    split_seed: int
    split_strategy: str             # e.g. "deterministic_sorted_group"
    train_ratio: float
    val_ratio: float
    test_ratio: float

    # Tiling configuration
    tile_height: int
    tile_width: int
    tile_stride_y: int
    tile_stride_x: int
    tiles_per_patch: int

    # Patch and tile catalogues
    patches: list[PatchManifestEntry] = field(default_factory=list)
    tiles: list[TileManifestEntry] = field(default_factory=list)

    # Split summaries
    split_summaries: list[SplitSummary] = field(default_factory=list)

    # Normalization (populated separately after training-split statistics pass)
    normalization_stats: Optional[NormalizationStats] = None

    # ---------------------------------------------------------------------------
    # Summary helpers
    # ---------------------------------------------------------------------------

    def patches_for_split(self, split: SplitName) -> list[PatchManifestEntry]:
        """Return all patches assigned to *split*."""
        return [p for p in self.patches if p.split == split]

    def tiles_for_split(self, split: SplitName) -> list[TileManifestEntry]:
        """Return all tiles assigned to *split*."""
        return [t for t in self.tiles if t.split == split]

    def group_keys_for_split(self, split: SplitName) -> set[str]:
        """Return set of group_keys in *split* (for leakage verification)."""
        return {p.group_key for p in self.patches_for_split(split)}

    # ---------------------------------------------------------------------------
    # Serialisation
    # ---------------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict.  Large pixel arrays are never included."""
        patches_list = [
            {
                "patch_stem": p.patch_stem,
                "image_path": p.image_path,
                "mask_path": p.mask_path,
                "group_key": p.group_key,
                "height": p.height,
                "width": p.width,
                "channels": p.channels,
                "dtype": p.dtype,
                "crs": p.crs,
                "radiometric_unit": p.radiometric_unit,
                "split": p.split.value,
            }
            for p in self.patches
        ]
        tiles_list = [
            {
                "tile_id": t.tile_id,
                "parent_stem": t.parent_stem,
                "group_key": t.group_key,
                "split": t.split.value,
                "row_idx": t.row_idx,
                "col_idx": t.col_idx,
                "row_offset": t.row_offset,
                "col_offset": t.col_offset,
                "height": t.height,
                "width": t.width,
            }
            for t in self.tiles
        ]
        summaries = [
            {"split": s.split.value, "n_patches": s.n_patches, "n_tiles": s.n_tiles}
            for s in self.split_summaries
        ]
        return {
            "dataset_name": self.dataset_name,
            "source_archive": self.source_archive,
            "zenodo_record": self.zenodo_record,
            "audit_report_path": self.audit_report_path,
            "radiometric_unit": self.radiometric_unit,
            "polarization_mapping": self.polarization_mapping,
            "split_seed": self.split_seed,
            "split_strategy": self.split_strategy,
            "train_ratio": self.train_ratio,
            "val_ratio": self.val_ratio,
            "test_ratio": self.test_ratio,
            "tile_height": self.tile_height,
            "tile_width": self.tile_width,
            "tile_stride_y": self.tile_stride_y,
            "tile_stride_x": self.tile_stride_x,
            "tiles_per_patch": self.tiles_per_patch,
            "split_summaries": summaries,
            "normalization_stats": (
                self.normalization_stats.to_dict()
                if self.normalization_stats is not None
                else None
            ),
            "patches": patches_list,
            "tiles": tiles_list,
        }

    def save(self, path: Path | str) -> None:
        """Persist manifest to a JSON file at *path*."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    @classmethod
    def load(cls, path: Path | str) -> "DatasetManifest":
        """Load a previously saved manifest from *path*."""
        with Path(path).open("r", encoding="utf-8") as fh:
            d = json.load(fh)

        patches = [
            PatchManifestEntry(
                patch_stem=p["patch_stem"],
                image_path=p["image_path"],
                mask_path=p["mask_path"],
                group_key=p["group_key"],
                height=p["height"],
                width=p["width"],
                channels=p["channels"],
                dtype=p["dtype"],
                crs=p.get("crs"),
                radiometric_unit=p["radiometric_unit"],
                split=SplitName(p["split"]),
            )
            for p in d["patches"]
        ]
        tiles = [
            TileManifestEntry(
                tile_id=t["tile_id"],
                parent_stem=t["parent_stem"],
                group_key=t["group_key"],
                split=SplitName(t["split"]),
                row_idx=t["row_idx"],
                col_idx=t["col_idx"],
                row_offset=t["row_offset"],
                col_offset=t["col_offset"],
                height=t["height"],
                width=t["width"],
            )
            for t in d["tiles"]
        ]
        summaries = [
            SplitSummary(
                split=SplitName(s["split"]),
                n_patches=s["n_patches"],
                n_tiles=s["n_tiles"],
            )
            for s in d.get("split_summaries", [])
        ]
        norm = (
            NormalizationStats.from_dict(d["normalization_stats"])
            if d.get("normalization_stats")
            else None
        )

        return cls(
            dataset_name=d["dataset_name"],
            source_archive=d["source_archive"],
            zenodo_record=d["zenodo_record"],
            audit_report_path=d["audit_report_path"],
            radiometric_unit=d["radiometric_unit"],
            polarization_mapping=d["polarization_mapping"],
            split_seed=d["split_seed"],
            split_strategy=d["split_strategy"],
            train_ratio=d["train_ratio"],
            val_ratio=d["val_ratio"],
            test_ratio=d["test_ratio"],
            tile_height=d["tile_height"],
            tile_width=d["tile_width"],
            tile_stride_y=d["tile_stride_y"],
            tile_stride_x=d["tile_stride_x"],
            tiles_per_patch=d["tiles_per_patch"],
            patches=patches,
            tiles=tiles,
            split_summaries=summaries,
            normalization_stats=norm,
        )


# ---------------------------------------------------------------------------
# GroupBasedSplitter
# ---------------------------------------------------------------------------


class GroupBasedSplitter:
    """Deterministic group-level train/val/test splitter.

    Guarantees:
    - The split unit is the parent patch stem (group_key).
    - No tile crosses split boundaries (enforced by construction).
    - Re-running with the same seed produces identical assignments.
    - No filesystem traversal order dependency (stems sorted before shuffle).

    Parameters
    ----------
    train_ratio : float
        Target fraction of patches for training (default 0.70).
    val_ratio : float
        Target fraction of patches for validation (default 0.15).
    test_ratio : float
        Remainder fraction for test (default 0.15).  Must sum to 1.0 with
        the others.
    seed : int
        Random seed for the permutation shuffle.
    tiling_config : TilingConfig | None
        Tile geometry to use for tile catalogue generation.
    """

    def __init__(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
        tiling_config: Optional[TilingConfig] = None,
    ) -> None:
        total = train_ratio + val_ratio + test_ratio
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Split ratios must sum to 1.0; got {total:.6f} "
                f"(train={train_ratio}, val={val_ratio}, test={test_ratio})"
            )
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.seed = seed
        self.tiling_config = tiling_config or TilingConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_manifest(
        self,
        loader,  # TrujilloDatasetLoader — typed generically to avoid circular import
        *,
        dataset_name: str = "trujillo_2024_part_i",
        source_archive: str = "01_Train_Val_Oil_Spill_images.7z",
        zenodo_record: str = "8346860",
        audit_report_path: str = "data/metadata/trujillo_2024/dataset_audit_report.json",
        native_height: int = 2048,
        native_width: int = 2048,
        native_channels: int = 2,
        native_dtype: str = "float32",
        native_crs: Optional[str] = "EPSG:4326",
        radiometric_unit: str = "dB",
    ) -> DatasetManifest:
        """Build a complete DatasetManifest from a TrujilloDatasetLoader.

        Steps
        -----
        1. Discover and sort paired stems (deterministic order).
        2. Apply seeded random shuffle and assign group-level splits.
        3. Generate tile catalogue for each patch (geometry only – no pixel reads).
        4. Compute split summary statistics.

        Parameters
        ----------
        loader : TrujilloDatasetLoader
            Fully initialised loader pointing at the Trujillo image/mask directories.
        dataset_name, source_archive, zenodo_record, audit_report_path
            Identity metadata recorded in the manifest.
        native_height, native_width, native_channels, native_dtype, native_crs
            Physical properties of each patch (verified from Phase 2.0 audit).
        radiometric_unit
            Radiometric unit string (must be "dB" for Trujillo Part I).

        Returns
        -------
        DatasetManifest
            Fully populated manifest (normalization_stats will be None until
            :meth:`compute_normalization_stats` is called separately).
        """
        stems = loader.get_paired_stems()  # Already sorted (alphabetically)
        n = len(stems)
        if n == 0:
            raise ValueError("No paired stems found; cannot build manifest.")

        # Seeded deterministic permutation
        rng = random.Random(self.seed)
        shuffled = stems[:]
        rng.shuffle(shuffled)

        # Compute split boundaries (floor ensures we never exceed total)
        n_train = int(self.train_ratio * n)
        n_val = int(self.val_ratio * n)
        # Remainder goes to test (avoids rounding loss)

        train_stems = set(shuffled[:n_train])
        val_stems = set(shuffled[n_train : n_train + n_val])
        # test_stems = remainder – everything else

        def _split_for(stem: str) -> SplitName:
            if stem in train_stems:
                return SplitName.TRAIN
            if stem in val_stems:
                return SplitName.VAL
            return SplitName.TEST

        # Build patch entries
        patches: list[PatchManifestEntry] = []
        for stem in stems:
            split = _split_for(stem)
            patches.append(
                PatchManifestEntry(
                    patch_stem=stem,
                    image_path=str(loader.get_image_path(stem)),
                    mask_path=str(loader.get_mask_path(stem)),
                    group_key=stem,
                    height=native_height,
                    width=native_width,
                    channels=native_channels,
                    dtype=native_dtype,
                    crs=native_crs,
                    radiometric_unit=radiometric_unit,
                    split=split,
                )
            )

        # Generate tile catalogue (geometry only – no raster reads)
        tiles: list[TileManifestEntry] = []
        for patch in patches:
            tile_defs = compute_tile_definitions(
                parent_height=patch.height,
                parent_width=patch.width,
                parent_stem=patch.patch_stem,
                config=self.tiling_config,
                group_key=patch.group_key,
            )
            for td in tile_defs:
                tiles.append(
                    TileManifestEntry(
                        tile_id=td.tile_id,
                        parent_stem=td.parent_stem,
                        group_key=td.group_key,
                        split=patch.split,
                        row_idx=td.row_idx,
                        col_idx=td.col_idx,
                        row_offset=td.row_offset,
                        col_offset=td.col_offset,
                        height=td.height,
                        width=td.width,
                    )
                )

        tiles_per_patch = len(tiles) // n if n > 0 else 0

        # Build split summaries
        split_summaries = []
        for split_name in (SplitName.TRAIN, SplitName.VAL, SplitName.TEST):
            np_count = sum(1 for p in patches if p.split == split_name)
            nt_count = sum(1 for t in tiles if t.split == split_name)
            split_summaries.append(
                SplitSummary(split=split_name, n_patches=np_count, n_tiles=nt_count)
            )

        cfg = self.tiling_config
        return DatasetManifest(
            dataset_name=dataset_name,
            source_archive=source_archive,
            zenodo_record=zenodo_record,
            audit_report_path=audit_report_path,
            radiometric_unit=radiometric_unit,
            polarization_mapping="UNKNOWN",
            split_seed=self.seed,
            split_strategy="deterministic_sorted_group_shuffle",
            train_ratio=self.train_ratio,
            val_ratio=self.val_ratio,
            test_ratio=self.test_ratio,
            tile_height=cfg.tile_height,
            tile_width=cfg.tile_width,
            tile_stride_y=cfg.stride_y,
            tile_stride_x=cfg.stride_x,
            tiles_per_patch=tiles_per_patch,
            patches=patches,
            tiles=tiles,
            split_summaries=split_summaries,
            normalization_stats=None,
        )

    def compute_normalization_stats(
        self,
        manifest: DatasetManifest,
        loader,  # TrujilloDatasetLoader
        max_patches: Optional[int] = None,
    ) -> NormalizationStats:
        """Compute per-channel mean and std from TRAINING patches only.

        Reads each training image in full to accumulate running statistics using
        a vectorized form of Welford's parallel algorithm (Chan et al., 1979).
        Numerically stable, single-pass, and efficient enough for 840 patches.

        Only TRAINING patches contribute.  Validation and test patches are never
        read during this pass.

        Parameters
        ----------
        manifest : DatasetManifest
            Populated manifest with split assignments.
        loader : TrujilloDatasetLoader
            Loader used to locate image files.
        max_patches : int | None
            If set, limit statistics to the first *max_patches* training patches
            (useful for fast smoke-tests on subsets).

        Returns
        -------
        NormalizationStats
            Per-channel mean, std, and valid pixel counts.

        Algorithm
        ---------
        Uses Chan et al. parallel Welford combination:
            Given two groups A (count_a, mean_a, M2_a) and B (count_b, mean_b, M2_b):
                count  = count_a + count_b
                delta  = mean_b - mean_a
                mean   = mean_a + delta * count_b / count
                M2     = M2_a + M2_b + delta**2 * count_a * count_b / count
        Applied per-patch with count_b = n_finite pixels in that patch.
        """
        import numpy as np

        train_patches = manifest.patches_for_split(SplitName.TRAIN)
        if max_patches is not None:
            train_patches = train_patches[:max_patches]

        if not train_patches:
            raise ValueError("No training patches found in manifest; cannot compute stats.")

        # Determine channel count from first patch
        n_channels = train_patches[0].channels

        # Chan et al. parallel Welford accumulators per channel (float64 precision)
        counts = np.zeros(n_channels, dtype=np.float64)   # running total pixel count
        means = np.zeros(n_channels, dtype=np.float64)    # running mean
        M2s = np.zeros(n_channels, dtype=np.float64)      # running sum of squared devs

        import warnings

        import rasterio
        from rasterio.errors import NotGeoreferencedWarning

        n_processed = 0
        for entry in train_patches:
            img_path = entry.image_path
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=NotGeoreferencedWarning)
                with rasterio.open(img_path) as src:
                    img = src.read().astype(np.float64)  # (C, H, W), float64 for precision

            for c in range(n_channels):
                channel_data = img[c]
                valid = channel_data[np.isfinite(channel_data)]
                n_b = len(valid)
                if n_b == 0:
                    continue

                # Batch statistics for this patch
                mean_b = valid.mean()
                M2_b = float(np.sum((valid - mean_b) ** 2))

                # Chan et al. parallel combination
                n_a = counts[c]
                n_total = n_a + n_b
                delta = mean_b - means[c]
                means[c] = means[c] + delta * n_b / n_total
                M2s[c] = M2s[c] + M2_b + delta ** 2 * n_a * n_b / n_total
                counts[c] = n_total

            n_processed += 1
            if n_processed % 100 == 0:
                import sys
                msg = (f"  Normalization stats: processed"
                       f" {n_processed}/{len(train_patches)} patches")
                print(msg, file=sys.stderr, flush=True)

        stds: list[float] = []
        for c in range(n_channels):
            variance = M2s[c] / counts[c] if counts[c] > 1 else 0.0
            stds.append(float(variance ** 0.5))

        return NormalizationStats(
            channel_means=[float(m) for m in means],
            channel_stds=stds,
            n_valid_pixels=[int(c) for c in counts],
            computed_from_split="train",
        )


# ---------------------------------------------------------------------------
# SpatialGroupSplitter
# ---------------------------------------------------------------------------


class SpatialGroupSplitter(GroupBasedSplitter):
    """Deterministic spatial connected-component train/val/test splitter.

    Guarantees:
    - Patches that have positive-area spatial footprint overlap in EPSG:4326 belong
      to the same connected spatial component.
    - Each connected component is treated as an indivisible spatial group and is
      assigned entirely to a single partition (TRAIN, VAL, or TEST).
    - Zero positive-area footprint intersection crosses split boundaries.
    - Zero identical geotransforms cross split boundaries.
    - All 16 tiles derived from each parent patch inherit the parent's split.
    - Deterministic platform-independent canonical ordering: identical seed
      guarantees identical partition.
    """

    def __init__(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
        tiling_config: Optional[TilingConfig] = None,
    ) -> None:
        super().__init__(
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=seed,
            tiling_config=tiling_config,
        )

    @staticmethod
    def extract_patch_bounds(
        loader, stems: list[str]
    ) -> dict[str, tuple[float, float, float, float]]:
        """Extract spatial bounds (left, bottom, right, top) in EPSG:4326 for all stems."""
        import warnings

        import rasterio
        from rasterio.errors import NotGeoreferencedWarning

        bounds_map: dict[str, tuple[float, float, float, float]] = {}
        for stem in stems:
            img_path = loader.get_image_path(stem)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=NotGeoreferencedWarning)
                with rasterio.open(img_path) as src:
                    b = src.bounds
                    bounds_map[stem] = (b.left, b.bottom, b.right, b.top)
        return bounds_map

    @staticmethod
    def build_overlap_graph(
        patch_bounds: dict[str, tuple[float, float, float, float]]
    ):
        """Construct an undirected graph of spatial footprint overlaps.

        An edge connects two patches if their bounding rectangles have positive-area
        intersection:
            max(l1, l2) < min(r1, r2) and max(b1, b2) < min(t1, t2)
        """
        import networkx as nx

        stems = sorted(patch_bounds.keys())
        g = nx.Graph()
        for stem in stems:
            g.add_node(stem)

        n = len(stems)
        for i in range(n):
            s1 = stems[i]
            b1 = patch_bounds[s1]
            for j in range(i + 1, n):
                s2 = stems[j]
                b2 = patch_bounds[s2]
                if max(b1[0], b2[0]) < min(b1[2], b2[2]) and max(b1[1], b2[1]) < min(b1[3], b2[3]):
                    g.add_edge(s1, s2)
        return g

    @staticmethod
    def compute_connected_components(graph) -> list[list[str]]:
        """Extract connected components with canonical, platform-independent ordering.

        - Stems within each component are sorted lexicographically.
        - The list of components is sorted canonically by (len(c) descending, c[0] ascending)
          or (c[0] ascending, len(c) ascending).
        """
        import networkx as nx

        raw_comps = list(nx.connected_components(graph))
        components = [sorted(list(c)) for c in raw_comps]
        # Canonical sort key: first stem lexicographically, then size
        components.sort(key=lambda c: (c[0], len(c)))
        return components

    def partition_components(
        self,
        components: list[list[str]],
        total_patches: int,
    ) -> tuple[list[str], list[str], list[str]]:
        """Deterministically partition connected components into train, val, and test.

        Uses capacity-aware largest-first greedy bin balancing seeded by self.seed.
        """
        target_train = int(self.train_ratio * total_patches)
        target_val = int(self.val_ratio * total_patches)
        target_test = total_patches - target_train - target_val

        rng = random.Random(self.seed)
        shuffled = list(components)
        rng.shuffle(shuffled)
        # Largest first bin packing ensures larger components find suitable bins
        shuffled.sort(key=lambda c: len(c), reverse=True)

        train_stems: list[str] = []
        val_stems: list[str] = []
        test_stems: list[str] = []
        n_train, n_val, n_test = 0, 0, 0

        for comp in shuffled:
            sz = len(comp)
            options: list[tuple[str, float]] = []
            if n_train + sz <= target_train:
                options.append(("train", (target_train - n_train - sz) / float(target_train)))
            if n_val + sz <= target_val:
                options.append(("val", (target_val - n_val - sz) / float(target_val)))
            if n_test + sz <= target_test:
                options.append(("test", (target_test - n_test - sz) / float(target_test)))

            if options:
                # Pick option that has the highest remaining fraction needed
                options.sort(key=lambda x: x[1], reverse=True)
                target_bin = options[0][0]
            else:
                # Fallback to least filled relative to target
                fracs = [
                    ("train", n_train / float(target_train)),
                    ("val", n_val / float(target_val)),
                    ("test", n_test / float(target_test)),
                ]
                fracs.sort(key=lambda x: x[1])
                target_bin = fracs[0][0]

            if target_bin == "train":
                train_stems.extend(comp)
                n_train += sz
            elif target_bin == "val":
                val_stems.extend(comp)
                n_val += sz
            else:
                test_stems.extend(comp)
                n_test += sz

        return train_stems, val_stems, test_stems

    def build_manifest(
        self,
        loader,
        *,
        patch_bounds: Optional[dict[str, tuple[float, float, float, float]]] = None,
        dataset_name: str = "trujillo_2024_part_i",
        source_archive: str = "01_Train_Val_Oil_Spill_images.7z",
        zenodo_record: str = "8346860",
        audit_report_path: str = "data/metadata/trujillo_2024/spatial_split_audit.json",
        native_height: int = 2048,
        native_width: int = 2048,
        native_channels: int = 2,
        native_dtype: str = "float32",
        native_crs: Optional[str] = "EPSG:4326",
        radiometric_unit: str = "dB",
    ) -> DatasetManifest:
        """Build a complete spatially defensible DatasetManifest from a TrujilloDatasetLoader."""
        stems = loader.get_paired_stems()
        n = len(stems)
        if n == 0:
            raise ValueError("No paired stems found; cannot build spatial manifest.")

        if patch_bounds is None:
            patch_bounds = self.extract_patch_bounds(loader, stems)

        graph = self.build_overlap_graph(patch_bounds)
        components = self.compute_connected_components(graph)
        train_stems_list, val_stems_list, test_stems_list = self.partition_components(components, n)

        train_stems = set(train_stems_list)
        val_stems = set(val_stems_list)

        def _split_for(stem: str) -> SplitName:
            if stem in train_stems:
                return SplitName.TRAIN
            if stem in val_stems:
                return SplitName.VAL
            return SplitName.TEST

        # Build patch entries
        patches: list[PatchManifestEntry] = []
        for stem in stems:
            split = _split_for(stem)
            patches.append(
                PatchManifestEntry(
                    patch_stem=stem,
                    image_path=str(loader.get_image_path(stem)),
                    mask_path=str(loader.get_mask_path(stem)),
                    group_key=stem,
                    height=native_height,
                    width=native_width,
                    channels=native_channels,
                    dtype=native_dtype,
                    crs=native_crs,
                    radiometric_unit=radiometric_unit,
                    split=split,
                )
            )

        # Generate tile catalogue
        tiles: list[TileManifestEntry] = []
        for patch in patches:
            tile_defs = compute_tile_definitions(
                parent_height=patch.height,
                parent_width=patch.width,
                parent_stem=patch.patch_stem,
                config=self.tiling_config,
                group_key=patch.group_key,
            )
            for td in tile_defs:
                tiles.append(
                    TileManifestEntry(
                        tile_id=td.tile_id,
                        parent_stem=td.parent_stem,
                        group_key=td.group_key,
                        split=patch.split,
                        row_idx=td.row_idx,
                        col_idx=td.col_idx,
                        row_offset=td.row_offset,
                        col_offset=td.col_offset,
                        height=td.height,
                        width=td.width,
                    )
                )

        tiles_per_patch = len(tiles) // n if n > 0 else 0

        # Build split summaries
        split_summaries = []
        for split_name in (SplitName.TRAIN, SplitName.VAL, SplitName.TEST):
            np_count = sum(1 for p in patches if p.split == split_name)
            nt_count = sum(1 for t in tiles if t.split == split_name)
            split_summaries.append(
                SplitSummary(split=split_name, n_patches=np_count, n_tiles=nt_count)
            )

        cfg = self.tiling_config
        return DatasetManifest(
            dataset_name=dataset_name,
            source_archive=source_archive,
            zenodo_record=zenodo_record,
            audit_report_path=audit_report_path,
            radiometric_unit=radiometric_unit,
            polarization_mapping="UNKNOWN",
            split_seed=self.seed,
            split_strategy="spatial_connected_component_partition",
            train_ratio=self.train_ratio,
            val_ratio=self.val_ratio,
            test_ratio=self.test_ratio,
            tile_height=cfg.tile_height,
            tile_width=cfg.tile_width,
            tile_stride_y=cfg.stride_y,
            tile_stride_x=cfg.stride_x,
            tiles_per_patch=tiles_per_patch,
            patches=patches,
            tiles=tiles,
            split_summaries=split_summaries,
            normalization_stats=None,
        )

