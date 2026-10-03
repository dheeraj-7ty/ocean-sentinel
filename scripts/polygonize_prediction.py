#!/usr/bin/env python
"""CLI for Ocean Sentinel Geospatial Prediction Interpretation.

Transforms raster prediction masks and probability maps into georeferenced
detection event polygons with real-world metric surface areas and GeoJSON output.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ocean_sentinel.interpretation import interpret_prediction


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert binary segmentation prediction mask into geospatial detection events."
    )
    parser.add_argument(
        "--mask", "-m",
        type=Path,
        required=True,
        help="Path to prediction mask GeoTIFF.",
    )
    parser.add_argument(
        "--probability", "-p",
        type=Path,
        default=None,
        help="Optional path to companion probability GeoTIFF for score aggregation.",
    )
    parser.add_argument(
        "--output-dir", "--output", "-o",
        type=Path,
        default=REPO_ROOT / "outputs" / "detections",
        help="Directory to save output GeoJSON file.",
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default=None,
        help="Optional prefix for output filename (default: mask stem without '_mask').",
    )
    parser.add_argument(
        "--detection-class",
        type=str,
        default="oil_spill",
        help="Detection class label (default: 'oil_spill').",
    )
    parser.add_argument(
        "--min-pixels",
        type=int,
        default=0,
        help="Minimum pixel count threshold for noise filtering (default: 0).",
    )
    parser.add_argument(
        "--min-area-m2",
        type=float,
        default=0.0,
        help="Minimum real-world area in m^2 for noise filtering (default: 0.0).",
    )
    parser.add_argument(
        "--connectivity",
        type=int,
        choices=[4, 8],
        default=8,
        help="Pixel connectivity for connected component extraction: 4 or 8 (default: 8).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.22,
        help="Decision threshold used to generate mask (default: 0.22).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    print("=" * 78)
    print("OCEAN SENTINEL — GEOSPATIAL PREDICTION INTERPRETATION")
    print("=" * 78)
    print(f"  Input Mask:           {args.mask}")
    print(f"  Input Probability:    {args.probability if args.probability else 'None (binary mask only)'}")
    print(f"  Detection Class:      {args.detection_class}")
    print(f"  Connectivity:         {args.connectivity}-connected")
    print(f"  Min Pixel Filter:     {args.min_pixels} px")
    print(f"  Min Area Filter:      {args.min_area_m2:,.1f} m^2")
    print(f"  Output Directory:     {args.output_dir}")
    print("-" * 78)

    try:
        report, geojson_path = interpret_prediction(
            mask_path=args.mask,
            probability_path=args.probability,
            output_dir=args.output_dir,
            output_prefix=args.output_prefix,
            min_pixels=args.min_pixels,
            min_area_m2=args.min_area_m2,
            connectivity=args.connectivity,
            detection_class=args.detection_class,
            threshold=args.threshold,
        )
    except Exception as e:
        print(f"\n[ERROR] Interpretation failed: {e}", file=sys.stderr)
        return 1

    print("\n" + "=" * 78)
    print("GEOSPATIAL INTERPRETATION SUMMARY")
    print("=" * 78)
    print(f"  Execution Time:       {report.execution_time_seconds:.4f} s")
    print(f"  Source Raster CRS:    {report.source_crs}")
    print(f"  Total Regions Found:  {report.total_detected_regions}")
    print(f"  Filtered Regions:     {report.filtered_regions}")
    print(f"  Retained Detections:  {report.retained_regions}")
    print(f"  Total Sfc Area:       {report.total_area_m2:,.2f} m^2 ({report.total_area_km2:.4f} km^2)")
    print("-" * 78)
    print("OUTPUT ARTIFACT:")
    print(f"  GeoJSON Path:         {geojson_path}")

    if report.events:
        print("-" * 78)
        print("TOP 5 LARGEST DETECTION EVENTS:")
        top_events = sorted(report.events, key=lambda e: e.area_m2, reverse=True)[:5]
        for idx, ev in enumerate(top_events, 1):
            prob_info = ""
            if ev.probability_statistics is not None:
                prob_info = f" | mean_prob={ev.probability_statistics.mean_probability:.4f}"
            print(
                f"  [{idx}] {ev.event_id}: {ev.area_m2:,.1f} m^2 ({ev.area_km2:.4f} km^2) | "
                f"{ev.pixel_count:,} px{prob_info}"
            )

    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
