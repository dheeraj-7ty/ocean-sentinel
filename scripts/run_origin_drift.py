#!/usr/bin/env python
"""CLI for Ocean Sentinel Origin & Drift Reasoning Engine.

Computes candidate Lagrangian trajectories and candidate origin regions:
- Forward drift forecasting (monitoring & trajectory prediction).
- Backward origin reconstruction (candidate source region estimation).
- Strict provenance gates separating PHYSICAL mode from DEMO mode.
- RFC 7946 WGS84 GeoJSON output.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add src to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ocean_sentinel.drift import (
    DirectionMode,
    DriftMode,
    ForcingSourceType,
    MetoceanForcingField,
    ObservationRecord,
    ProvenanceGateError,
    run_origin_drift_analysis,
)
from ocean_sentinel.temporal import TimestampProvenance

# Exit code contract
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_PROVENANCE_REJECTION = 2
EXIT_INVALID_INPUT = 3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run_origin_drift")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute candidate Lagrangian drift trajectory or candidate origin region."
    )
    parser.add_argument(
        "--event", "-e",
        type=Path,
        required=True,
        help="Path to temporal/geospatial detection GeoJSON or summary JSON.",
    )
    parser.add_argument(
        "--event-id",
        type=str,
        default=None,
        help="Optional specific event ID to select from a FeatureCollection.",
    )
    parser.add_argument(
        "--direction", "-d",
        type=str,
        choices=["forward", "backward"],
        default="backward",
        help="Trajectory integration direction: 'backward' (candidate origin) or 'forward' (drift forecast).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["demo", "physical"],
        default="demo",
        help="Execution mode: 'physical' (strictly requires authoritative data) or 'demo' (allows test fixtures).",
    )
    parser.add_argument(
        "--duration-hours", "--backtrack-hours",
        type=float,
        default=24.0,
        help="Duration of integration in hours (default: 24.0).",
    )
    parser.add_argument(
        "--timestep-seconds",
        type=float,
        default=1800.0,
        help="Numerical integration timestep in seconds (default: 1800.0 / 30 min).",
    )
    parser.add_argument(
        "--particle-count",
        type=int,
        default=5,
        help="Number of spatial seed particles to initialize across the detection (default: 5).",
    )
    parser.add_argument(
        "--windage-min",
        type=float,
        default=0.01,
        help="Minimum windage leeway factor (default: 0.01 / 1%%).",
    )
    parser.add_argument(
        "--windage-max",
        type=float,
        default=0.04,
        help="Maximum windage leeway factor (default: 0.04 / 4%%).",
    )
    parser.add_argument(
        "--windage-steps",
        type=int,
        default=4,
        help="Number of windage steps in the parameter sweep (default: 4).",
    )
    parser.add_argument(
        "--current-u",
        type=float,
        default=0.15,
        help="Eastward surface ocean current velocity in m/s (default: 0.15).",
    )
    parser.add_argument(
        "--current-v",
        type=float,
        default=0.10,
        help="Northward surface ocean current velocity in m/s (default: 0.10).",
    )
    parser.add_argument(
        "--wind-u",
        type=float,
        default=-3.5,
        help="Eastward 10m wind velocity in m/s (default: -3.5).",
    )
    parser.add_argument(
        "--wind-v",
        type=float,
        default=4.0,
        help="Northward 10m wind velocity in m/s (default: 4.0).",
    )
    parser.add_argument(
        "--forcing-source",
        type=str,
        default="synthetic_deterministic_fixture",
        help="Name of the metocean environmental forcing source.",
    )
    parser.add_argument(
        "--authoritative-forcing",
        action="store_true",
        default=False,
        help="Declare metocean forcing as verified operational/reanalysis authoritative data.",
    )
    parser.add_argument(
        "--output-dir", "--output", "-o",
        type=Path,
        default=REPO_ROOT / "outputs" / "drift",
        help="Directory to save drift GeoJSON and summary JSON artifacts (default: outputs/drift).",
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default=None,
        help="Optional filename prefix for exported files.",
    )
    return parser


def load_observation_from_file(file_path: Path, target_event_id: str | None = None) -> ObservationRecord:
    """Load and parse an ObservationRecord from GeoJSON FeatureCollection or JSON summary."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("type") == "FeatureCollection":
        features = data.get("features", [])
        if not features:
            raise ValueError(f"FeatureCollection in {file_path.name} contains zero features.")

        # Find target feature or pick largest detection/change event
        selected_feature = None
        if target_event_id:
            for feat in features:
                if feat.get("id") == target_event_id or feat.get("properties", {}).get("event_id") == target_event_id:
                    selected_feature = feat
                    break
            if not selected_feature:
                raise ValueError(f"Event ID '{target_event_id}' not found in {file_path.name}.")
        else:
            # Sort by area_m2 descending
            features_sorted = sorted(
                features,
                key=lambda x: x.get("properties", {}).get("area_m2", 0.0),
                reverse=True,
            )
            selected_feature = features_sorted[0]

        return ObservationRecord.from_temporal_event(selected_feature)

    if "events" in data and isinstance(data["events"], list):
        events = data["events"]
        if not events:
            raise ValueError(f"Summary JSON in {file_path.name} contains zero events.")
        selected = events[0]
        if target_event_id:
            for ev in events:
                if ev.get("event_id") == target_event_id:
                    selected = ev
                    break
        return ObservationRecord.from_temporal_event(selected)

    raise ValueError(f"Unrecognized file format in {file_path.name}. Expected GeoJSON FeatureCollection or summary JSON.")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    start_time = time.time()
    direction = DirectionMode.BACKWARD if args.direction.lower() == "backward" else DirectionMode.FORWARD
    mode = DriftMode.PHYSICAL if args.mode.lower() == "physical" else DriftMode.DEMO

    print("=" * 80)
    print("OCEAN SENTINEL — ORIGIN & DRIFT REASONING ENGINE")
    print("=" * 80)
    print(f"  Input Event File:     {args.event}")
    print(f"  Execution Mode:       {mode.value}")
    print(f"  Trajectory Direction: {direction.value}")
    print(f"  Duration:             {args.duration_hours:.1f} hours")
    print(f"  Integration Timestep: {args.timestep_seconds:.1f} s")
    print(f"  Particle Seed Count:  {args.particle_count}")
    print(f"  Windage Range:        {args.windage_min:.3f} to {args.windage_max:.3f} ({args.windage_steps} steps)")
    print(f"  Forcing Source:       {args.forcing_source} (authoritative: {args.authoritative_forcing})")
    print(f"  Surface Current:      u={args.current_u:+.2f} m/s, v={args.current_v:+.2f} m/s")
    print(f"  10m Wind:             u={args.wind_u:+.2f} m/s, v={args.wind_v:+.2f} m/s")
    print(f"  Output Directory:     {args.output_dir}")
    print("-" * 80)

    # 1. Load observation record
    try:
        obs = load_observation_from_file(args.event, args.event_id)
    except (FileNotFoundError, ValueError) as ve:
        print(f"\n[INVALID INPUT] Observation event loading failed: {ve}", file=sys.stderr)
        return EXIT_INVALID_INPUT
    except Exception as e:
        print(f"\n[ERROR] Failed to load observation event: {e}", file=sys.stderr)
        return EXIT_ERROR

    print(f"OBSERVED DETECTION STATE:")
    print(f"  Event ID:             {obs.event_id}")
    print(f"  Source Scene:         {obs.source_scene}")
    print(f"  Observation Time:     {obs.observation_time.isoformat()}")
    print(f"  Timestamp Provenance: {obs.timestamp_provenance}")
    print(f"  Centroid [lon, lat]:  [{obs.centroid[0]:.6f}, {obs.centroid[1]:.6f}]")
    print(f"  Observed Area:        {obs.area_m2:,.2f} m^2")
    print("-" * 80)

    # 2. Build forcing field
    forcing_field = MetoceanForcingField(
        forcing_source=args.forcing_source,
        source_type=(
            ForcingSourceType.OPERATIONAL_ANALYSIS
            if args.authoritative_forcing
            else ForcingSourceType.SYNTHETIC_TEST_FIXTURE
        ),
        is_authoritative=args.authoritative_forcing,
        constant_current_u=args.current_u,
        constant_current_v=args.current_v,
        constant_wind_u=args.wind_u,
        constant_wind_v=args.wind_v,
    )

    # 3. Execute analysis
    try:
        report, geojson_path, json_path = run_origin_drift_analysis(
            observation=obs,
            forcing_field=forcing_field,
            direction=direction,
            mode=mode,
            duration_hours=args.duration_hours,
            timestep_seconds=args.timestep_seconds,
            windage_min=args.windage_min,
            windage_max=args.windage_max,
            windage_steps=args.windage_steps,
            particle_count=args.particle_count,
            output_dir=args.output_dir,
            output_prefix=args.output_prefix,
        )
    except ProvenanceGateError as pge:
        print(f"\n[PROVENANCE GATE REJECTION] Execution blocked by scientific gate: {pge}", file=sys.stderr)
        print("  Rationale: PHYSICAL mode forbids non-authoritative timestamps or synthetic forcing.", file=sys.stderr)
        print("  Workaround: Use --mode demo for non-physical pipeline testing.", file=sys.stderr)
        return EXIT_PROVENANCE_REJECTION
    except Exception as e:
        print(f"\n[ERROR] Drift execution failed: {e}", file=sys.stderr)
        logger.exception("Drift execution failed")
        return EXIT_ERROR

    elapsed = time.time() - start_time
    stats = report["summary_statistics"]
    envelopes = report["envelopes"]

    print("\n" + "=" * 80)
    print("ORIGIN & DRIFT EXECUTION SUMMARY")
    print("=" * 80)
    print(f"  Runtime:                {elapsed:.4f} s")
    print(f"  Ensemble Particles:     {stats['trajectory_count']}")
    print(f"  Dominant Driver:        {stats['dominant_driver']}")
    print(f"  Current Speed:          {stats['sample_surface_current_speed_ms']:.3f} m/s")
    print(f"  Mean Wind Leeway Speed: {stats['sample_wind_leeway_speed_ms']:.3f} m/s")
    print(f"  Net Displacement (Mean):{stats['mean_net_displacement_m']:,.1f} m "
          f"[{stats['min_net_displacement_m']:,.1f} - {stats['max_net_displacement_m']:,.1f} m]")
    print(f"  Trajectory Envelope:    {envelopes['trajectory_envelope_area_m2']:,.2f} m^2 "
          f"({envelopes['trajectory_envelope_area_km2']:.4f} km^2)")

    if direction == DirectionMode.BACKWARD and envelopes.get("candidate_origin_region_area_m2"):
        print(f"  Candidate Origin Region:{envelopes['candidate_origin_region_area_m2']:,.2f} m^2 "
              f"({envelopes['candidate_origin_region_area_km2']:.4f} km^2)")

    print("-" * 80)
    print("OUTPUT ARTIFACTS:")
    print(f"  GeoJSON Trajectories:   {geojson_path}")
    print(f"  Summary JSON:           {json_path}")
    print("-" * 80)
    print("SCIENTIFIC BOUNDARY NOTICE:")
    for lim in report["scientific_limitations"]:
        print(f"  * {lim}")
    print("=" * 80)
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
