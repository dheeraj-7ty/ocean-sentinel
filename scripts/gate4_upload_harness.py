#!/usr/bin/env python3
"""CLI Entrypoint for Ocean Sentinel Gate 4.2 Pre-Upload Operations Harness.

Subcommands:
  preflight    - Collect and display complete environmental/staging preflight metrics
  benchmark    - Measure baseline network upload throughput
  probe        - Prepare isolated canary dataset probe (unexecuted)
  prod-cmd     - Generate exact certified production upload command (unexecuted)
  resumability - Inspect Kaggle CLI resume state and active upload tokens
  diagnose     - Collect non-secret system diagnostics and classify failure
  simulate     - Safe synthetic end-to-end simulation of upload telemetry & stall detection
  monitor      - Real-time monitor attaching to ongoing process or progress stream
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from ocean_sentinel.cloud.upload_harness import (  # noqa: E402
    ControlledUploadProbe,
    DiagnosticSnapshotCollector,
    FailureClassifier,
    NetworkBaselineBenchmarker,
    PersistentObservabilityWriter,
    PreflightCollector,
    ProductionCommandGenerator,
    ResumabilityInspector,
    StallDetector,
    UploadState,
    UploadTelemetryMonitor,
)


def cmd_preflight(args: argparse.Namespace) -> int:
    collector = PreflightCollector()
    record = collector.collect()

    print("\n" + "=" * 80)
    print("OCEAN SENTINEL GATE 4.2 PRE-UPLOAD PREFLIGHT")
    print("=" * 80)
    print(f"Timestamp (UTC)          : {record['timestamp']}")
    print(f"Git Branch / Commit      : {record['git_branch']} ({record['git_commit'][:10]})")
    status_str = f"{record['git_status']} ({record['git_dirty_files_count']} untracked/modified)"
    print(f"Git Working Tree State   : {status_str}")
    print(f"Dataset Staging Path     : {record['dataset_staging_path']}")
    total_bytes = record["exact_total_byte_count"]
    total_gb = total_bytes / (1024**3)
    print(f"Exact Byte Count         : {total_bytes:,} bytes ({total_gb:.2f} GB)")
    print(f"Exact Total File Count   : {record['exact_file_count']:,} files")
    img_cnt = record["image_count"]
    mask_cnt = record["mask_count"]
    print(f"Image Count / Mask Count : {img_cnt:,} images / {mask_cnt:,} masks")
    print(f"Manifest Root SHA256     : {record['manifest_root_sha256']}")
    print(f"Kaggle Dataset Slug      : {record['kaggle_dataset_slug']}")
    print(f"Kaggle CLI Version       : {record['kaggle_cli_version']}")
    print(f"Python Executable (Env)  : {record['python_executable']}")
    print(f"Authentication State     : {record['authentication_state']} (Secrets hidden)")
    adapter_name = record["active_network_adapter"].get("name")
    adapter_desc = record["active_network_adapter"].get("interface_description")
    print(f"Active Network Adapter   : {adapter_name} ({adapter_desc})")
    print(f"Negotiated Link Speed    : {record['negotiated_link_speed']}")
    p_ac = record["system_power_state"].get("ac_line_status")
    p_bat = record["system_power_state"].get("battery_percent")
    print(f"System Power State       : AC={p_ac} Battery={p_bat}%")

    disk = record.get("local_disk_free_space", {})
    for drive, info in disk.items():
        if isinstance(info, dict):
            free_g = info.get("free_gb")
            tot_g = info.get("total_gb")
            print(f"Disk Free ({drive})          : {free_g} GB free of {tot_g} GB")

    net = record.get("current_network_connectivity", {})
    k_net = net.get("kaggle_com", {})
    g_net = net.get("storage_googleapis_com", {})
    k_up = "UP" if k_net.get("reachable") else "DOWN"
    g_up = "UP" if g_net.get("reachable") else "DOWN"
    print(f"kaggle.com Reachability  : {k_up} ({k_net.get('rtt_ms')} ms)")
    print(f"GCS Reachability         : {g_up} ({g_net.get('rtt_ms')} ms)")
    print("=" * 80 + "\n")

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(f"Preflight saved to: {out_p}")

    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    benchmarker = NetworkBaselineBenchmarker()
    print(
        f"Executing upload benchmark to {args.endpoint} (payload={args.payload_mb} MB)..."
    )
    res = benchmarker.measure(
        endpoint=args.endpoint,
        payload_size_bytes=int(args.payload_mb * 1024 * 1024),
        timeout_sec=args.timeout,
    )
    print("\n" + "=" * 80)
    print("NETWORK BASELINE UPLOAD BENCHMARK RESULT")
    print("=" * 80)
    print(f"Timestamp           : {res['timestamp']}")
    print(f"Endpoint Tested     : {res['endpoint']}")
    print(f"Test Method         : {res['test_method']}")
    print(f"Success             : {res.get('success')}")
    print(f"Duration            : {res.get('duration_sec')} s")
    t_mbs = res.get("measured_throughput_mb_s")
    t_mbps = res.get("measured_throughput_mbps")
    print(f"Measured Throughput : {t_mbs} MB/s ({t_mbps} Mbps)")
    print("\nLIMITATIONS AND UNCERTAINTY:")
    print(res["limitations_and_uncertainty"])
    print("=" * 80 + "\n")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    probe = ControlledUploadProbe()
    res = probe.prepare()
    print("\n" + "=" * 80)
    print("CONTROLLED UPLOAD PROBE CANARY (PREPARED - UNEXECUTED)")
    print("=" * 80)
    print(f"Status               : {res['status']}")
    print(f"Probe Staging Path   : {res['probe_dir']}")
    print(f"Probe Dataset Slug   : {res['probe_slug']}")
    print(f"Private Enforcement  : {res['is_private']}")
    print(f"Payload Size         : {res['payload_bytes']} bytes")
    print(f"Executable           : {res['executable']}")
    print("\nPROBE EXECUTION COMMAND (RUN MANUALLY WHEN AUTHORIZED):")
    print(f"  {res['command']}")
    print("=" * 80 + "\n")
    return 0


def cmd_prod_cmd(args: argparse.Namespace) -> int:
    gen = ProductionCommandGenerator()
    res = gen.generate()
    print("\n" + "=" * 80)
    print("CERTIFIED PRODUCTION KAGGLE UPLOAD COMMAND (UNEXECUTED)")
    print("=" * 80)
    print(f"Dataset Slug         : {res['certified_slug']}")
    print(f"Staging Directory    : {res['staging_dir']}")
    print(f"Private Enforced     : {res['is_private_enforced']}")
    print(f"Kaggle Executable    : {res['kaggle_executable']}")
    print(f"Execution Policy     : {res['execution_policy']}")
    print("\nEXACT PRODUCTION COMMAND:")
    print(f"  {res['production_upload_command']}")
    print("\nSAFETY CONFIRMATION:")
    print("  This command was GENERATED ONLY and has NOT been executed.")
    print("  Production upload of 56.19 GB requires explicit operator verification.")
    print("=" * 80 + "\n")
    return 0


def cmd_resumability(args: argparse.Namespace) -> int:
    res = ResumabilityInspector.inspect()
    print("\n" + "=" * 80)
    print("KAGGLE CLI / GCS RESUMABILITY INSPECTION")
    print("=" * 80)
    print(f"Resumability Supported : {res['resumability_supported_by_cli']}")
    print(f"Protocol               : {res['protocol']}")
    print(f"State Storage Path     : {res['state_storage_path']}")
    print(f"Active Tokens Found    : {res['active_resume_tokens_count']}")
    print("\nRECOVERY MECHANISM:")
    print(res["recovery_mechanism"])
    print("\nCAVEATS & WARNINGS:")
    print(res["caveats"])
    print("=" * 80 + "\n")
    return 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    collector = DiagnosticSnapshotCollector()
    snapshot = collector.collect(target_pid=args.pid)
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SNAPSHOT")
    print("=" * 80)
    print(json.dumps(snapshot, indent=2))
    print("=" * 80 + "\n")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    """Run a safe synthetic simulation of upload telemetry, rolling windows, and stall detection."""
    out_dir = (
        Path(args.output_dir)
        if args.output_dir
        else (REPO_ROOT / "temp" / "synthetic_upload_telemetry_test")
    )
    writer = PersistentObservabilityWriter(out_dir)
    stall_detector = StallDetector(
        heartbeat_interval_sec=1.0,
        warning_threshold_sec=3.0,
        critical_stall_threshold_sec=6.0,
    )
    # Simulate a 100 MB synthetic upload
    total_test_bytes = 100 * 1024 * 1024
    monitor = UploadTelemetryMonitor(
        total_bytes=total_test_bytes,
        total_files=10,
        writer=writer,
        stall_detector=stall_detector,
    )

    print(f"Starting synthetic upload telemetry simulation into: {out_dir}")
    writer.append_event("SIMULATION_START", "Initiating synthetic upload simulation")

    # Step 1: Active upload simulation (40 MB at 10 MB/s)
    current_bytes = 0
    for step in range(4):
        time.sleep(0.5)
        current_bytes += 10 * 1024 * 1024
        t = monitor.update_bytes(current_bytes, file_info=f"synthetic_part_{step + 1}.dat")
        monitor.tick()
        rate_mb = t.instantaneous_throughput_bps / (1024**2)
        print(
            f"  [Active] Progress: {t.percentage_bytes:5.1f}% | "
            f"Rate: {rate_mb:.1f} MB/s | State: {t.current_state.value}"
        )

    # Step 2: Injected Stall simulation (no progress for 7 seconds)
    print("  [Simulating Network / Remote Stall for 7 seconds...]")
    for _ in range(7):
        time.sleep(1.0)
        t = monitor.tick()
        print(
            f"  [Stall Check] State: {t.current_state.value} | "
            f"Stalled for {t.time_since_last_progress_sec:.1f}s"
        )

    # Step 3: Classification of stall
    snapshot = DiagnosticSnapshotCollector().collect()
    diag_report = FailureClassifier.classify(
        telemetry=t,
        exit_code=None,
        diagnostic_snapshot=snapshot,
        log_content="",
    )
    print(f"\n  Failure Classification Result : {diag_report['classification']}")
    print(f"  Evidence                      : {diag_report['evidence']}")
    print(f"  Recommended Action            : {diag_report['recommended_action']}\n")

    # Step 4: Resume and Complete upload
    print("  [Resuming upload to completion...]")
    current_bytes = total_test_bytes
    t = monitor.update_bytes(current_bytes, file_info="synthetic_part_final.dat")
    monitor.tick()
    print(f"  [Complete] Progress: {t.percentage_bytes:5.1f}% | State: {t.current_state.value}")

    print("\nSynthetic simulation completed successfully.")
    print(f"Observability files verified in: {out_dir}")
    print(f"  - {writer.status_file.name} ({writer.status_file.stat().st_size} bytes)")
    print(f"  - {writer.progress_file.name} ({writer.progress_file.stat().st_size} bytes)")
    print(f"  - {writer.events_file.name} ({writer.events_file.stat().st_size} bytes)\n")
    return 0


def cmd_monitor(args: argparse.Namespace) -> int:
    """Attach real-time telemetry monitor to an ongoing upload via stdin or log file."""
    out_dir = (
        Path(args.output_dir)
        if args.output_dir
        else (REPO_ROOT / "experiments" / "performance" / "upload_telemetry")
    )
    writer = PersistentObservabilityWriter(out_dir)
    stall_detector = StallDetector()
    total_bytes = args.total_bytes if args.total_bytes is not None else 56_193_499_563
    total_files = args.total_files if args.total_files is not None else 2403

    monitor = UploadTelemetryMonitor(
        total_bytes=total_bytes,
        total_files=total_files,
        writer=writer,
        stall_detector=stall_detector,
    )

    writer.append_event(
        "MONITOR_ATTACHED",
        "Telemetry monitor attached to upload stream",
        {"log_file": args.log_file},
    )
    monitor.tick()  # Immediate initial status flush
    print(f"Monitoring upload into {out_dir} (target: {total_bytes:,} bytes)")

    if args.log_file:
        log_path = Path(args.log_file)
        wait_start = time.time()
        while not log_path.exists() and (time.time() - wait_start < 30.0):
            time.sleep(0.5)

        if not log_path.exists():
            print(f"Error: Log file not found: {log_path}", file=sys.stderr)
            return 1

        with open(log_path, "r", encoding="utf-8", errors="replace") as fp:
            last_tick = time.monotonic()
            while True:
                line = fp.readline()
                if line:
                    monitor.parse_cli_line(line.strip())
                    monitor.tick()
                    last_tick = time.monotonic()
                else:
                    time.sleep(0.2)

                now = time.monotonic()
                if now - last_tick >= 1.0:
                    t = monitor.tick()
                    last_tick = now
                    if t.current_state == UploadState.COMPLETE:
                        print(f"Upload COMPLETE reached ({t.percentage_bytes:.1f}%).")
                        break
                    if args.exit_on_idle and (t.time_since_last_progress_sec > args.exit_on_idle):
                        idle_sec = t.time_since_last_progress_sec
                        print(f"Monitor idle timeout reached ({idle_sec:.1f}s).")
                        break
    else:
        last_tick = time.monotonic()
        for raw_line in sys.stdin:
            line = raw_line.strip()
            print(raw_line, end="", flush=True)
            monitor.parse_cli_line(line)
            now = time.monotonic()
            if now - last_tick >= 1.0:
                monitor.tick()
                last_tick = now
        monitor.tick()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ocean Sentinel Gate 4.2 Pre-Upload Operations Harness CLI"
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # preflight
    p_pre = subparsers.add_parser("preflight", help="Run pre-upload preflight check")
    p_pre.add_argument("--output", "-o", help="Output path for preflight JSON")

    # benchmark
    p_bench = subparsers.add_parser("benchmark", help="Measure baseline network upload speed")
    p_bench.add_argument(
        "--endpoint", default="https://httpbin.org/post", help="Test upload endpoint"
    )
    p_bench.add_argument("--payload-mb", type=float, default=1.0, help="Payload size in MB")
    p_bench.add_argument("--timeout", type=float, default=10.0, help="Timeout in seconds")

    # probe
    subparsers.add_parser("probe", help="Stage isolated canary upload probe")

    # prod-cmd
    subparsers.add_parser("prod-cmd", help="Generate production upload command (unexecuted)")

    # resumability
    subparsers.add_parser("resumability", help="Inspect Kaggle CLI resume state")

    # diagnose
    p_diag = subparsers.add_parser("diagnose", help="Collect non-secret system diagnostics")
    p_diag.add_argument("--pid", type=int, help="Target process PID to inspect")

    # simulate
    p_sim = subparsers.add_parser("simulate", help="Run synthetic simulation of upload telemetry")
    p_sim.add_argument("--output-dir", help="Directory for simulation logs and status")

    # monitor
    p_mon = subparsers.add_parser("monitor", help="Attach real-time telemetry monitor to upload")
    p_mon.add_argument("--log-file", help="Path to stdout/stderr log file to tail")
    p_mon.add_argument(
        "--output-dir", "--out-dir", dest="output_dir", help="Directory for telemetry outputs"
    )
    p_mon.add_argument(
        "--total-bytes", type=int, default=56_193_499_563, help="Expected total byte count"
    )
    p_mon.add_argument("--total-files", type=int, default=2403, help="Expected total file count")
    p_mon.add_argument(
        "--exit-on-idle", type=float, default=None, help="Exit after N seconds of inactivity"
    )

    args = parser.parse_args()

    dispatch = {
        "preflight": cmd_preflight,
        "benchmark": cmd_benchmark,
        "probe": cmd_probe,
        "prod-cmd": cmd_prod_cmd,
        "resumability": cmd_resumability,
        "diagnose": cmd_diagnose,
        "simulate": cmd_simulate,
        "monitor": cmd_monitor,
    }

    handler = dispatch.get(args.subcommand)
    if not handler:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
