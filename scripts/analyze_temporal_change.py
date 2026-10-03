#!/usr/bin/env python
"""CLI for Ocean Sentinel Temporal Change Reasoning.

Quantifies spatial and temporal change between sequential satellite observations (T0 and T1):
- Validates temporal ordering (T0 < T1).
- Checks and aligns spatial grids (nearest-neighbor for masks, bilinear for probabilities).
- Computes discrete change masks (PERSISTENT, NEW, DISAPPEARED).
- Computes probability delta summary over valid overlapping pixels.
- Performs spatial object matching (IoU) with metric area quantification.
- Outputs RFC 7946 compliant GeoJSON detection features and JSON summary report.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add src to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ocean_sentinel.temporal import analyze_temporal_change

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("analyze_temporal_change")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze temporal change between two sequential observations (T0 and T1)."
    )
    parser.add_argument(
        "--t0-mask",
        type=Path,
        required=True,
        help="Path to T0 binary prediction mask GeoTIFF.",
    )
    parser.add_argument(
        "--t1-mask",
        type=Path,
        required=True,
        help="Path to T1 binary prediction mask GeoTIFF.",
    )
    parser.add_argument(
        "--t0-probability",
        type=Path,
        default=None,
        help="Optional path to companion probability GeoTIFF for T0.",
    )
    parser.add_argument(
        "--t1-probability",
        type=Path,
        default=None,
        help="Optional path to companion probability GeoTIFF for T1.",
    )
    parser.add_argument(
        "--t0-time",
        type=str,
        default=None,
        help="Optional explicit ISO acquisition timestamp for T0 (used only if not embedded in raster metadata).",
    )
    parser.add_argument(
        "--t1-time",
        type=str,
        default=None,
        help="Optional explicit ISO acquisition timestamp for T1 (used only if not embedded in raster metadata).",
    )
    parser.add_argument(
        "--output-dir", "--output", "-o",
        type=Path,
        default=REPO_ROOT / "outputs" / "temporal",
        help="Directory to save temporal GeoJSON and summary JSON artifacts (default: outputs/temporal).",
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default=None,
        help="Optional filename prefix for exported files.",
    )
    parser.add_argument(
        "--min-pixels",
        type=int,
        default=0,
        help="Minimum pixel count filter for change objects (default: 0).",
    )
    parser.add_argument(
        "--min-area-m2",
        type=float,
        default=0.0,
        help="Minimum metric surface area in m^2 filter for change objects (default: 0.0).",
    )
    parser.add_argument(
        "--match-iou-threshold",
        type=float,
        default=0.10,
        help="Spatial IoU threshold for matching candidate T0 and T1 objects (default: 0.10).",
    )
    parser.add_argument(
        "--one-to-one",
        action="store_true",
        default=False,
        help="Enforce deterministic greedy 1-to-1 matching between T0 and T1 objects (default: False, candidate edges).",
    )
    parser.add_argument(
        "--disallow-reprojection",
        action="store_false",
        dest="allow_reprojection",
        default=True,
        help="Disallow automatic grid reprojection if T0 and T1 grids differ.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    print("=" * 80)
    print("OCEAN SENTINEL — TEMPORAL CHANGE REASONING PIPELINE")
    print("=" * 80)
    print(f"  T0 Mask:              {args.t0_mask}")
    print(f"  T1 Mask:              {args.t1_mask}")
    print(f"  T0 Probability:       {args.t0_probability or 'None'}")
    print(f"  T1 Probability:       {args.t1_probability or 'None'}")
    print(f"  Output Directory:     {args.output_dir}")
    print(f"  Match IoU Threshold:  {args.match_iou_threshold:.2f}")
    print(f"  One-to-One Matching:  {args.one_to_one}")
    print(f"  Min Pixel Filter:     {args.min_pixels} px")
    print(f"  Min Area Filter:      {args.min_area_m2:,.1f} m^2")
    print(f"  Allow Reprojection:   {args.allow_reprojection}")
    print("-" * 80)

    try:
        report, geojson_path, json_path = analyze_temporal_change(
            t0_mask_path=args.t0_mask,
            t1_mask_path=args.t1_mask,
            t0_prob_path=args.t0_probability,
            t1_prob_path=args.t1_probability,
            t0_time=args.t0_time,
            t1_time=args.t1_time,
            output_dir=args.output_dir,
            output_prefix=args.output_prefix,
            min_pixels=args.min_pixels,
            min_area_m2=args.min_area_m2,
            match_iou_threshold=args.match_iou_threshold,
            one_to_one=args.one_to_one,
            allow_reprojection=args.allow_reprojection,
        )
    except Exception as e:
        print(f"\n[ERROR] Temporal analysis failed: {e}", file=sys.stderr)
        logger.exception("Temporal analysis failed")
        return 1

    print("\n" + "=" * 80)
    print("TEMPORAL CHANGE SUMMARY")
    print("=" * 80)
    print(f"  Execution Time:         {report.execution_time_seconds:.4f} s")
    print(f"  T0 Timestamp:           {report.t0_time}")
    print(f"  T1 Timestamp:           {report.t1_time}")
    print(f"  Elapsed Interval:       {report.time_interval_hours:.2f} hours")
    if report.timestamp_provenance:
        tp = report.timestamp_provenance
        auth_tag = "[AUTHORITATIVE]" if tp.get("is_authoritative") else "[NON-AUTHORITATIVE TEST-SUPPLIED]"
        print(f"  Timestamp Provenance:   {auth_tag}")
        print(f"    - T0: {tp.get('t0_provenance')}")
        print(f"    - T1: {tp.get('t1_provenance')}")
    print(f"  Grid Alignment:         {report.spatial_alignment.get('strategy')}")
    print("-" * 80)
    print("REGION COUNTS:")
    print(f"  New Regions:            {report.counts['new_regions']:,}")
    print(f"  Persistent Regions:     {report.counts['persistent_regions']:,}")
    print(f"  Disappeared Regions:    {report.counts['disappeared_regions']:,}")
    print(f"  Total Change Objects:   {report.counts['total_change_regions']:,}")
    print(f"  Matched Object Pairs:   {report.counts['matched_object_pairs']:,} ({report.counts.get('matching_mode', 'default')})")
    print("-" * 80)
    print("SURFACE AREA MEASUREMENTS:")
    print(f"  New Area:               {report.areas_m2['new_area_m2']:,.2f} m^2 ({report.areas_km2['new_area_km2']:.4f} km^2)")
    print(f"  Persistent Area:        {report.areas_m2['persistent_area_m2']:,.2f} m^2 ({report.areas_km2['persistent_area_km2']:.4f} km^2)")
    print(f"  Disappeared Area:       {report.areas_m2['disappeared_area_m2']:,.2f} m^2 ({report.areas_km2['disappeared_area_km2']:.4f} km^2)")
    print(f"  Total Changed Area:     {report.areas_m2['total_changed_area_m2']:,.2f} m^2 ({report.areas_km2['total_changed_area_km2']:.4f} km^2)")
    print("-" * 80)
    print("PIXEL COUNTS:")
    print(f"  Persistent Pixels:      {report.pixel_counts['persistent_pixels']:,}")
    print(f"  New Pixels:             {report.pixel_counts['new_pixels']:,}")
    print(f"  Disappeared Pixels:     {report.pixel_counts['disappeared_pixels']:,}")
    print(f"  Unchanged Background:   {report.pixel_counts['unchanged_background_pixels']:,}")

    if report.probability_change_summary:
        pcs = report.probability_change_summary
        print("-" * 80)
        print("PROBABILITY DELTA (T1 - T0):")
        print(f"  Mean Delta:             {pcs['mean_delta']:+.4f}")
        print(f"  Min / Max Delta:        {pcs['min_delta']:+.4f} / {pcs['max_delta']:+.4f}")
        print(f"  Std Delta:              {pcs['std_delta']:.4f}")
        print(f"  Valid Pixel Count:      {pcs['valid_pixel_count']:,}")

    if report.matched_objects:
        print("-" * 80)
        print("MATCHED OBJECT PAIRS (TOP 5 BY OVERLAP IoU):")
        top_matches = sorted(report.matched_objects, key=lambda m: m.overlap_iou, reverse=True)[:5]
        for idx, m in enumerate(top_matches, 1):
            rel_str = f"{m.relative_area_change * 100:+.1f}%" if m.relative_area_change is not None else "N/A"
            print(
                f"  [{idx}] {m.t0_polygon_id} <-> {m.t1_polygon_id} | IoU: {m.overlap_iou:.3f} | "
                f"T0 Area: {m.area_t0_m2:,.1f} m^2 | T1 Area: {m.area_t1_m2:,.1f} m^2 | "
                f"Delta: {m.area_change_m2:+,.1f} m^2 ({rel_str}) | Displacement: {m.centroid_displacement_m:.1f} m"
            )

    print("-" * 80)
    print("OUTPUT ARTIFACTS:")
    print(f"  GeoJSON Events:         {geojson_path}")
    print(f"  Summary JSON:           {json_path}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
