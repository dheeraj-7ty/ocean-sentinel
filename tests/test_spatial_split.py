"""Tests for Phase 2.4 Spatially Defensible Dataset Partition and Ingestion.

Verifies:
1. Spatial overlap graph construction and connected component extraction.
2. Deterministic partition reproducibility across seeds.
3. Full manifest schema compatibility and tile inheritance.
4. Independent verification: zero cross-split positive-area overlaps.
5. Independent verification: zero cross-split identical geotransforms.
6. Indivisibility of connected spatial components.
7. Normalization statistics provenance from train split only.
8. Spatial proximity bounds (>10 km cross-split separation).
9. Integration with TrujilloTileDataset.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest
import rasterio
from rasterio.errors import NotGeoreferencedWarning
from shapely.geometry import box

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
from ocean_sentinel.ingestion.split import (
    DatasetManifest,
    SpatialGroupSplitter,
    SplitName,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = REPO_ROOT / "data" / "metadata" / "trujillo_2024"
SPATIAL_MANIFEST_PATH = MANIFESTS_DIR / "spatial_split_manifest.json"
SPATIAL_AUDIT_PATH = MANIFESTS_DIR / "spatial_split_audit.json"
IMAGES_DIR = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil"


# ---------------------------------------------------------------------------
# Unit tests on synthetic geometries
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyntheticSpatialSplitter:
    """Test SpatialGroupSplitter logic using controlled synthetic bounding boxes."""

    def test_overlap_graph_construction(self):
        # 3 boxes: A overlaps B, B overlaps C, D is isolated
        bounds = {
            "A": (0.0, 0.0, 2.0, 2.0),
            "B": (1.0, 1.0, 3.0, 3.0),
            "C": (2.5, 2.5, 4.0, 4.0),
            "D": (10.0, 10.0, 12.0, 12.0),
        }
        g = SpatialGroupSplitter.build_overlap_graph(bounds)
        assert set(g.nodes()) == {"A", "B", "C", "D"}
        assert g.has_edge("A", "B")
        assert g.has_edge("B", "C")
        assert not g.has_edge("A", "C")
        assert g.degree("D") == 0

        comps = SpatialGroupSplitter.compute_connected_components(g)
        assert len(comps) == 2
        # One component has A, B, C; other has D
        comp_sets = [set(c) for c in comps]
        assert {"A", "B", "C"} in comp_sets
        assert {"D"} in comp_sets

    def test_non_overlapping_boxes_no_edges(self):
        # Touching at boundary edge (zero positive area) should not form edge
        bounds = {
            "A": (0.0, 0.0, 1.0, 1.0),
            "B": (1.0, 0.0, 2.0, 1.0),  # touches on x=1.0 line
            "C": (5.0, 5.0, 6.0, 6.0),
        }
        g = SpatialGroupSplitter.build_overlap_graph(bounds)
        assert g.number_of_edges() == 0
        comps = SpatialGroupSplitter.compute_connected_components(g)
        assert len(comps) == 3

    def test_deterministic_component_partition(self):
        # 10 components of varying sizes
        components = [
            ["001", "002"],
            ["003"],
            ["004", "005", "006"],
            ["007"],
            ["008"],
            ["009"],
            ["010"],
        ]
        total = 10
        splitter = SpatialGroupSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42)
        train1, val1, test1 = splitter.partition_components(components, total)
        train2, val2, test2 = splitter.partition_components(components, total)

        assert train1 == train2
        assert val1 == val2
        assert test1 == test2

        all_assigned = set(train1) | set(val1) | set(test1)
        assert len(all_assigned) == total

        # Check indivisibility: each component's stems are in the same split
        for c in components:
            splits_for_c = set()
            for s in c:
                if s in train1:
                    splits_for_c.add("train")
                elif s in val1:
                    splits_for_c.add("val")
                else:
                    splits_for_c.add("test")
            assert len(splits_for_c) == 1, f"Component {c} was split across: {splits_for_c}"


# ---------------------------------------------------------------------------
# Real-data Manifest and Independent Leakage Tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def spatial_manifest() -> DatasetManifest:
    return DatasetManifest.load(SPATIAL_MANIFEST_PATH)


@pytest.fixture(scope="module")
def spatial_audit_data() -> dict:
    with SPATIAL_AUDIT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def raw_geotiff_records(spatial_manifest: DatasetManifest) -> list[dict]:
    """Independently inspect all 1,200 raw GeoTIFF headers once from disk.

    Extracts bounds, shapely bounding box polygon, and geotransform matrix for each raw file.
    Shared across real-data tests to eliminate redundant disk I/O from opening all 1,200
    files twice sequentially, while maintaining 100% real-data verification coverage.
    """
    patch_split = {p.patch_stem: p.split for p in spatial_manifest.patches}
    records = []
    for stem, split in patch_split.items():
        img_path = IMAGES_DIR / f"{stem}.tif"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=NotGeoreferencedWarning)
            with rasterio.open(img_path) as src:
                b = src.bounds
                gt = tuple(float(x) for x in src.transform)
        records.append({
            "stem": stem,
            "split": split,
            "bounds": (b.left, b.bottom, b.right, b.top),
            "poly": box(b.left, b.bottom, b.right, b.top),
            "gt": gt,
        })
    return records


@pytest.mark.slow
@pytest.mark.real_data
@pytest.mark.skipif(
    not SPATIAL_MANIFEST_PATH.exists(), reason="Spatial split manifest not yet generated"
)
class TestRealSpatialSplitManifest:
    """Rigorous tests on the generated spatial_split_manifest.json and raw rasters."""

    def test_manifest_counts_and_percentages(self, spatial_manifest: DatasetManifest):
        assert len(spatial_manifest.patches) == 1200
        assert len(spatial_manifest.tiles) == 19200

        train_patches = spatial_manifest.patches_for_split(SplitName.TRAIN)
        val_patches = spatial_manifest.patches_for_split(SplitName.VAL)
        test_patches = spatial_manifest.patches_for_split(SplitName.TEST)

        assert len(train_patches) == 840
        assert len(val_patches) == 180
        assert len(test_patches) == 180

        assert len(train_patches) / 1200.0 == 0.70
        assert len(val_patches) / 1200.0 == 0.15
        assert len(test_patches) / 1200.0 == 0.15

    def test_tile_counts_and_inheritance(self, spatial_manifest: DatasetManifest):
        train_tiles = spatial_manifest.tiles_for_split(SplitName.TRAIN)
        val_tiles = spatial_manifest.tiles_for_split(SplitName.VAL)
        test_tiles = spatial_manifest.tiles_for_split(SplitName.TEST)

        assert len(train_tiles) == 13440
        assert len(val_tiles) == 2880
        assert len(test_tiles) == 2880

        patch_map = {p.patch_stem: p.split for p in spatial_manifest.patches}
        parent_tile_counts = {}
        for t in spatial_manifest.tiles:
            assert t.split == patch_map[t.parent_stem]
            assert t.group_key == t.parent_stem
            parent_tile_counts[t.parent_stem] = parent_tile_counts.get(t.parent_stem, 0) + 1

        assert len(parent_tile_counts) == 1200
        for stem, cnt in parent_tile_counts.items():
            assert cnt == 16, f"Parent {stem} has {cnt} tiles instead of 16"

    def test_normalization_statistics(self, spatial_manifest: DatasetManifest):
        stats = spatial_manifest.normalization_stats
        assert stats is not None
        assert stats.computed_from_split == "train"
        assert len(stats.channel_means) == 2
        assert len(stats.channel_stds) == 2
        assert len(stats.n_valid_pixels) == 2

        assert -40.0 < stats.channel_means[0] < -20.0
        assert -30.0 < stats.channel_means[1] < -10.0
        assert 3.0 < stats.channel_stds[0] < 10.0
        assert 2.0 < stats.channel_stds[1] < 10.0
        assert stats.n_valid_pixels[0] == 840 * 2048 * 2048
        assert stats.n_valid_pixels[1] == 840 * 2048 * 2048

    def test_zero_cross_split_spatial_intersection_against_raw_geotiffs(
        self, raw_geotiff_records: list[dict]
    ):
        """Independently inspect all 1,200 raw GeoTIFF headers and verify 0 cross-split overlaps."""
        n = len(raw_geotiff_records)
        cross_overlaps = []
        for i in range(n):
            r1 = raw_geotiff_records[i]
            b1 = r1["bounds"]
            for j in range(i + 1, n):
                r2 = raw_geotiff_records[j]
                if r1["split"] == r2["split"]:
                    continue
                b2 = r2["bounds"]
                if (
                    b1[0] >= b2[2]
                    or b1[2] <= b2[0]
                    or b1[1] >= b2[3]
                    or b1[3] <= b2[1]
                ):
                    continue
                inter = r1["poly"].intersection(r2["poly"])
                if not inter.is_empty and inter.area > 0:
                    cross_overlaps.append((r1["stem"], r2["stem"], inter.area))

        msg = (
            f"Found {len(cross_overlaps)} cross-split positive-area overlaps: "
            f"{cross_overlaps[:3]}"
        )
        assert len(cross_overlaps) == 0, msg

    def test_zero_cross_split_identical_geotransforms(
        self, raw_geotiff_records: list[dict]
    ):
        """Verify identical geotransforms never cross split boundaries."""
        gt_map = {}
        for r in raw_geotiff_records:
            gt_map.setdefault(r["gt"], []).append((r["stem"], r["split"]))

        multi_patch_gts = {k: v for k, v in gt_map.items() if len(v) > 1}
        assert len(multi_patch_gts) == 2
        for gt, entries in multi_patch_gts.items():
            splits = set(sp for _, sp in entries)
            assert len(splits) == 1, f"Identical geotransform shared across splits: {entries}"

    def test_audit_report_certification(self, spatial_audit_data: dict):
        concl = spatial_audit_data["conclusions"]
        assert concl["certification_status"] == "CERTIFIED_LEAKAGE_FREE"

        ov = spatial_audit_data["spatial_overlap_analysis"]
        assert ov["cross_split_overlapping_pairs"] == 0
        assert ov["cross_split_overlap_gte_10pct"] == 0
        assert ov["cross_split_overlap_gte_50pct"] == 0

        gt = spatial_audit_data["geotransform_analysis"]
        assert gt["identical_gt_cross_split_count"] == 0

        comp = spatial_audit_data["connected_components_analysis"]
        assert comp["cross_split_components"] == 0
        assert comp["total_components"] == 204

        prox = spatial_audit_data["proximity_analysis"]
        assert prox["val_to_train_km"]["min"] > 10.0
        assert prox["test_to_train_km"]["min"] > 10.0
        assert prox["val_to_train_km"]["lt_5km"] == 0
        assert prox["test_to_train_km"]["lt_5km"] == 0

    def test_dataset_loader_integration(self, spatial_manifest: DatasetManifest):
        dataset_train = TrujilloTileDataset(
            manifest=spatial_manifest,
            split=SplitName.TRAIN,
        )
        assert len(dataset_train) == 13440

        dataset_val = TrujilloTileDataset(
            manifest=spatial_manifest,
            split=SplitName.VAL,
        )
        assert len(dataset_val) == 2880

        dataset_test = TrujilloTileDataset(
            manifest=spatial_manifest,
            split=SplitName.TEST,
        )
        assert len(dataset_test) == 2880

        # Load first sample
        img_tensor, mask_tensor = dataset_train[0]
        assert img_tensor.shape == (2, 512, 512)
        assert mask_tensor.shape == (1, 512, 512)
