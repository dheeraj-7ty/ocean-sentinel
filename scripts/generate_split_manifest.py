#!/usr/bin/env python
"""Phase 2.1 — Generate split manifest and compute normalization stats.

This script reads the already-audited Trujillo Part I dataset and produces:
  data/metadata/trujillo_2024/split_manifest.json

It also prints a performance benchmark over a small sample of tiles.

Usage:
    python scripts/generate_split_manifest.py [--max-norm-patches N]
"""

from __future__ import annotations

import argparse
import sys
import time
import warnings
from pathlib import Path

# ---------------------------------------------------------------------------
# Repository root
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

IMAGES_DIR = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images"
MASKS_DIR = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "masks"
METADATA_DIR = REPO_ROOT / "data" / "metadata" / "trujillo_2024"
MANIFEST_PATH = METADATA_DIR / "split_manifest.json"
AUDIT_REPORT = METADATA_DIR / "dataset_audit_report.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Trujillo split manifest")
    parser.add_argument(
        "--max-norm-patches",
        type=int,
        default=None,
        help="Limit normalization stats computation to N training patches (default: all)",
    )
    args = parser.parse_args()

    from ocean_sentinel.ingestion.split import GroupBasedSplitter, TilingConfig
    from ocean_sentinel.ingestion.trujillo import TrujilloDatasetLoader

    # ---------------------------------------------------------------------------
    # Step 1: Discover dataset
    # ---------------------------------------------------------------------------
    print("=" * 70)
    print("TRUJILLO PART I — PHASE 2.1 MANIFEST GENERATION")
    print("=" * 70)

    loader = TrujilloDatasetLoader(images_dir=IMAGES_DIR, masks_dir=MASKS_DIR)
    stems = loader.get_paired_stems()
    print(f"  Paired stems found: {len(stems)}")

    if len(stems) == 0:
        print("ERROR: No paired stems found. Check dataset paths.")
        sys.exit(1)

    # ---------------------------------------------------------------------------
    # Step 2: Build manifest
    # ---------------------------------------------------------------------------
    t0 = time.perf_counter()
    splitter = GroupBasedSplitter(
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=42,
        tiling_config=TilingConfig(
            tile_height=512,
            tile_width=512,
            stride_y=512,
            stride_x=512,
            edge_handling="drop",
        ),
    )
    manifest = splitter.build_manifest(
        loader,
        audit_report_path=str(AUDIT_REPORT),
    )
    t_manifest = time.perf_counter() - t0
    print(f"\n  Manifest built in {t_manifest:.2f}s")
    for summary in manifest.split_summaries:
        print(f"    {summary.split.value:5s}: {summary.n_patches:4d} patches, "
              f"{summary.n_tiles:5d} tiles")

    # ---------------------------------------------------------------------------
    # Step 3: Compute normalization statistics
    # ---------------------------------------------------------------------------
    max_p = args.max_norm_patches
    label = f"{max_p} patches" if max_p else "all training patches"
    print(f"\n  Computing normalization stats from {label}...")
    t1 = time.perf_counter()
    norm_stats = splitter.compute_normalization_stats(manifest, loader, max_patches=max_p)
    t_norm = time.perf_counter() - t1
    print(f"  Done in {t_norm:.1f}s")
    for c, (m, s, n) in enumerate(zip(
        norm_stats.channel_means, norm_stats.channel_stds, norm_stats.n_valid_pixels
    )):
        print(f"    channel_{c}: mean={m:.4f} dB, std={s:.4f} dB, n_valid={n:,}")

    manifest.normalization_stats = norm_stats

    # ---------------------------------------------------------------------------
    # Step 4: Save manifest
    # ---------------------------------------------------------------------------
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest.save(MANIFEST_PATH)
    manifest_size_kb = MANIFEST_PATH.stat().st_size / 1024
    print(f"\n  Saved: {MANIFEST_PATH} ({manifest_size_kb:.1f} KB)")

    # ---------------------------------------------------------------------------
    # Step 5: Performance benchmark (10 tiles from training split)
    # ---------------------------------------------------------------------------
    print("\n  PERFORMANCE BENCHMARK (10 tiles, training split, no PyTorch)")
    from ocean_sentinel.ingestion.split import SplitName

    train_tiles = manifest.tiles_for_split(SplitName.TRAIN)[:10]
    # Build patch path index
    patch_paths = {p.patch_stem: (p.image_path, p.mask_path) for p in manifest.patches}
    import numpy as np
    import rasterio
    from rasterio.errors import NotGeoreferencedWarning
    from rasterio.windows import Window

    norm_mean = np.array(norm_stats.channel_means, dtype=np.float32)
    norm_std = np.array(norm_stats.channel_stds, dtype=np.float32)
    norm_std = np.where(norm_std < 1e-8, 1.0, norm_std)

    t_total_start = time.perf_counter()
    for i, tile in enumerate(train_tiles):
        t_tile_start = time.perf_counter()
        img_path, mask_path = patch_paths[tile.parent_stem]
        window = Window(
            col_off=tile.col_offset,
            row_off=tile.row_offset,
            width=tile.width,
            height=tile.height,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=NotGeoreferencedWarning)
            with rasterio.open(img_path) as src:
                img = src.read(window=window).astype(np.float32)
            with rasterio.open(mask_path) as src:
                mask = src.read(1, window=window).astype(np.float32)

        # Apply normalization
        for c in range(img.shape[0]):
            img[c] = (img[c] - norm_mean[c]) / norm_std[c]

        dt = time.perf_counter() - t_tile_start
        if i == 0:
            print(f"    First tile: {dt*1000:.1f} ms  (image={img.shape}, mask={mask.shape})")

    t_total = time.perf_counter() - t_total_start
    throughput = len(train_tiles) / t_total if t_total > 0 else 0
    print(f"    {len(train_tiles)} tiles in {t_total*1000:.1f} ms → {throughput:.1f} tiles/sec")

    print("\n  DONE — Manifest generation and benchmark complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
