#!/usr/bin/env python
"""CLI for Ocean Sentinel Binary SAR Oil-Spill Inference.

Executes end-to-end inference on a Sentinel-1 SAR GeoTIFF image using a trained
binary segmentation checkpoint (defaulting to EXP-06 ResNet34-UNet).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Add src to python path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ocean_sentinel.inference import (
    DEFAULT_CHECKPOINT_PATH,
    DEFAULT_THRESHOLD,
    DEFAULT_TILE_SIZE,
    predict_sar_image,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute binary oil-spill inference on a Sentinel-1 SAR GeoTIFF."
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="Path to input 2-band SAR GeoTIFF.",
    )
    parser.add_argument(
        "--checkpoint", "-c",
        type=Path,
        default=DEFAULT_CHECKPOINT_PATH,
        help=f"Path to model checkpoint (default: {DEFAULT_CHECKPOINT_PATH}).",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=REPO_ROOT / "outputs" / "inference",
        help="Directory to save output GeoTIFFs (probability and mask).",
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default=None,
        help="Optional prefix for output filenames (defaults to input image stem).",
    )
    parser.add_argument(
        "--tile-size",
        type=int,
        default=DEFAULT_TILE_SIZE,
        help=f"Tile window dimension (default: {DEFAULT_TILE_SIZE}).",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=0,
        help="Overlap in pixels between adjacent tiles (default: 0).",
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Binarization decision threshold tau (default: {DEFAULT_THRESHOLD}).",
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=8,
        help="Batch size for tile inference (default: 8).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Compute device ('cuda' or 'cpu', default: auto-detect).",
    )
    parser.add_argument(
        "--ground-truth", "-g",
        type=Path,
        default=None,
        help="Optional path to ground-truth mask GeoTIFF for instant evaluation.",
    )
    parser.add_argument(
        "--allow-non-georeferenced",
        action="store_true",
        help="Allow images without valid CRS or affine georeferencing.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    print("=" * 78)
    print("OCEAN SENTINEL — BINARY SAR INFERENCE PIPELINE")
    print("=" * 78)
    print(f"  Input SAR GeoTIFF:    {args.input}")
    print(f"  Model Checkpoint:     {args.checkpoint}")
    print(f"  Architecture:         ResNet34UNet (in_channels=2, num_classes=1)")
    print(f"  Tile Size:            {args.tile_size}x{args.tile_size}")
    print(f"  Overlap:              {args.overlap} px")
    print(f"  Operating Threshold:  {args.threshold}")
    print(f"  Batch Size:           {args.batch_size}")
    print(f"  Output Directory:     {args.output_dir}")
    print("-" * 78)

    try:
        result = predict_sar_image(
            input_path=args.input,
            checkpoint_path=args.checkpoint,
            output_dir=args.output_dir,
            output_prefix=args.output_prefix,
            tile_size=args.tile_size,
            overlap=args.overlap,
            threshold=args.threshold,
            device=args.device,
            batch_size=args.batch_size,
            ground_truth_path=args.ground_truth,
            require_georeferencing=not args.allow_non_georeferenced,
        )
    except Exception as e:
        print(f"\n[ERROR] Inference failed: {e}", file=sys.stderr)
        return 1

    print("\n" + "=" * 78)
    print("INFERENCE EXECUTION SUMMARY")
    print("=" * 78)
    print(f"  Execution Time:       {result.execution_time_seconds:.3f} s")
    print(f"  Tiles Processed:      {result.tile_count}")
    print(f"  Compute Device:       {result.stats['device']}")
    print(f"  Total Pixels:         {result.stats['total_pixels']:,}")
    print(f"  Valid Pixels:         {result.stats['valid_pixels']:,}")
    print(f"  Invalid/Nodata:       {result.stats['invalid_pixels']:,}")
    print(f"  Oil Pixels Detected:  {result.stats['oil_pixels']:,} ({result.stats['oil_area_fraction'] * 100.0:.2f}%)")
    print(f"  Mean Valid Score:     {result.stats['mean_valid_probability']:.4f}")
    print("-" * 78)
    print("OUTPUT ARTIFACTS:")
    print(f"  Probability GeoTIFF:  {result.probability_path}")
    print(f"  Binary Mask GeoTIFF:  {result.mask_path}")

    if result.evaluation_metrics is not None:
        m = result.evaluation_metrics
        print("-" * 78)
        print("GROUND TRUTH EVALUATION METRICS:")
        print(f"  True Positives (TP):  {m['tp']:,}")
        print(f"  False Positives (FP): {m['fp']:,}")
        print(f"  False Negatives (FN): {m['fn']:,}")
        print(f"  True Negatives (TN):  {m['tn']:,}")
        print(f"  IoU (Jaccard Index):  {m['iou']:.4f}")
        print(f"  Dice / F1 Score:      {m['dice']:.4f}")
        print(f"  Precision:            {m['precision']:.4f}")
        print(f"  Recall:               {m['recall']:.4f}")

    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
