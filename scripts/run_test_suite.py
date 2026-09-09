#!/usr/bin/env python3
"""Deterministic Test Suite Runner & Observability Harness for Ocean Sentinel.

Provides deterministic, observable, bounded test execution across classified suites:
- default: Fast, representative test suite excluding heavyweight slow tests (pytest -m "not slow")
- heavyweight: Real-data validation suite exercising physical GeoTIFFs, masks, and checkpoints (pytest -m "slow or real_data")
- full: Complete repository test suite (all 473 tests)
- unit: Fast isolated unit tests only (pytest -m "unit")
- regression: Specific Gate 4.3B cross-platform manifest path resolution regression suite

Features:
- Enforces strict process-level wall-clock timeouts without in-process thread contamination
- Real-time line-buffered console streaming for maximum observability
- Unambiguous status classification: PASS, PASS WITH WARNINGS, FAIL, TIMEOUT, INCOMPLETE
- Machine-readable JSON summary export for CI/CD and audit trails
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent

# Evidence-based suite configurations and default timeouts (seconds)
SUITE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "default": {
        "description": "Standard repository test suite excluding heavyweight slow tests",
        "pytest_args": ["-m", "not slow", "-v"],
        "default_timeout": 120.0,
    },
    "heavyweight": {
        "description": "Heavyweight real-data validation suite (1,200 GeoTIFFs, masks, checkpoints)",
        "pytest_args": ["-m", "slow or real_data", "-v"],
        "default_timeout": 180.0,
    },
    "full": {
        "description": "Complete test suite (all collected tests)",
        "pytest_args": ["-v"],
        "default_timeout": 300.0,
    },
    "unit": {
        "description": "Fast unit tests only",
        "pytest_args": ["-m", "unit", "-v"],
        "default_timeout": 60.0,
    },
    "regression": {
        "description": "Gate 4.3B cross-platform manifest path resolution regression suite",
        "pytest_args": ["-k", "TestCrossPlatformManifestPathResolution", "-v"],
        "default_timeout": 30.0,
    },
}


def parse_pytest_summary(output_text: str) -> Dict[str, int]:
    """Parse pytest terminal output line to extract exact test counts."""
    counts = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "deselected": 0,
        "errors": 0,
        "warnings": 0,
    }

    # Match summary patterns like: "466 passed, 7 deselected, 77 warnings in 36.42s"
    # or "1 failed, 2 passed in 1.23s"
    summary_match = re.search(r"=+ (.*) in \d+\.\d+s =+", output_text)
    if summary_match:
        content = summary_match.group(1)
        for part in content.split(","):
            part = part.strip()
            num_match = re.match(r"(\d+)\s+([a-zA-Z_]+)", part)
            if num_match:
                n = int(num_match.group(1))
                word = num_match.group(2).lower()
                if "pass" in word:
                    counts["passed"] = n
                elif "fail" in word:
                    counts["failed"] = n
                elif "skip" in word:
                    counts["skipped"] = n
                elif "deselect" in word:
                    counts["deselected"] = n
                elif "warning" in word:
                    counts["warnings"] = n
                elif "error" in word:
                    counts["errors"] = n

    return counts


def run_test_suite(
    suite_name: str,
    timeout_sec: Optional[float] = None,
    extra_pytest_args: Optional[List[str]] = None,
    json_output_path: Optional[Path] = None,
) -> int:
    """Execute the specified test suite with bounded timeout and observability."""
    if suite_name not in SUITE_CONFIGS:
        print(f"Error: Unknown suite '{suite_name}'. Allowed: {list(SUITE_CONFIGS.keys())}")
        return 1

    cfg = SUITE_CONFIGS[suite_name]
    timeout = timeout_sec if timeout_sec is not None else cfg["default_timeout"]
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *cfg["pytest_args"],
        *(extra_pytest_args or []),
    ]

    print("=" * 70)
    print("OCEAN SENTINEL TEST SUITE EXECUTION")
    print("=" * 70)
    print(f"Suite:           {suite_name} ({cfg['description']})")
    print(f"Timeout Limit:   {timeout:.1f}s")
    print(f"Command:         {' '.join(cmd)}")
    print(f"Working Dir:     {REPO_ROOT}")
    print(f"Python:          {sys.executable}")
    print(f"Start Time UTC:  {datetime.now(timezone.utc).isoformat()}")
    print("-" * 70)

    start_time = time.time()
    last_test_nodeid: Optional[str] = None
    output_lines: List[str] = []
    is_timed_out = False

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    try:
        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                is_timed_out = True
                print(f"\n[TIMEOUT ENFORCED] Process exceeded execution limit of {timeout:.1f}s!")
                proc.terminate()
                try:
                    proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2.0)
                break

            line = proc.stdout.readline() if proc.stdout else ""
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.02)
                continue

            output_lines.append(line)
            sys.stdout.write(line)
            sys.stdout.flush()

            # Track currently running test nodeid
            m = re.match(r"(tests/\S+::\S+)", line.strip())
            if m:
                last_test_nodeid = m.group(1)

        proc.wait()
    except KeyboardInterrupt:
        print("\n[ABORT] User interrupted execution.")
        proc.terminate()
        proc.wait()
        return 130

    elapsed_sec = time.time() - start_time
    full_output = "".join(output_lines)
    counts = parse_pytest_summary(full_output)

    # Determine status
    if is_timed_out:
        status = "TIMEOUT"
        exit_code = 124
    elif proc.returncode == 0:
        if counts["warnings"] > 0:
            status = "PASS WITH WARNINGS"
        else:
            status = "PASS"
        exit_code = 0
    else:
        status = "FAIL"
        exit_code = proc.returncode

    print("\n" + "=" * 70)
    print("TEST SUITE EXECUTION SUMMARY")
    print("=" * 70)
    print(f"SUITE:           {suite_name}")
    print(f"STATUS:          {status}")
    print(f"EXIT CODE:       {exit_code}")
    print(f"ELAPSED TIME:    {elapsed_sec:.2f}s (limit {timeout:.1f}s)")
    print(f"PASSED:          {counts['passed']}")
    print(f"FAILED:          {counts['failed']}")
    print(f"TIMED_OUT:       {1 if is_timed_out else 0}")
    print(f"SKIPPED:         {counts['skipped']}")
    print(f"DESELECTED:      {counts['deselected']}")
    print(f"ERRORS:          {counts['errors']}")
    print(f"WARNINGS:        {counts['warnings']}")
    if is_timed_out:
        print(f"LAST ACTIVE:     {last_test_nodeid or 'Unknown'}")
    print("=" * 70)

    summary_data = {
        "suite": suite_name,
        "description": cfg["description"],
        "status": status,
        "exit_code": exit_code,
        "elapsed_sec": round(elapsed_sec, 2),
        "timeout_limit_sec": timeout,
        "is_timed_out": is_timed_out,
        "last_active_test": last_test_nodeid,
        "counts": counts,
        "command": cmd,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    if json_output_path:
        json_output_path.parent.mkdir(parents=True, exist_ok=True)
        with json_output_path.open("w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)
        print(f"Summary JSON saved to: {json_output_path}")

    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ocean Sentinel Deterministic Test Suite Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--suite",
        choices=list(SUITE_CONFIGS.keys()),
        default="default",
        help="Test suite category to execute",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Override wall-clock timeout in seconds",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional path to write machine-readable summary JSON",
    )
    parser.add_argument(
        "extra_pytest_args",
        nargs=argparse.REMAINDER,
        help="Extra arguments passed directly to pytest (prefix with --)",
    )

    args = parser.parse_args()
    code = run_test_suite(
        suite_name=args.suite,
        timeout_sec=args.timeout,
        extra_pytest_args=args.extra_pytest_args,
        json_output_path=args.json_output,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
