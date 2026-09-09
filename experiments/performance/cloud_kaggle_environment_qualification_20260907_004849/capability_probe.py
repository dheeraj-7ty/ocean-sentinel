#!/usr/bin/env python3
"""
Non-Destructive Capability Probe for Ocean Sentinel.
Compatible with both Local (Windows) and Cloud (Kaggle/Linux) environments.

Gathers hardware, PyTorch, CUDA, cuDNN, and precision telemetry without
loading training datasets or consuming meaningful GPU quota.
"""

from __future__ import annotations

import argparse
import ctypes
import datetime
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_ram_info() -> Tuple[Optional[float], Optional[float]]:
    """Return (total_ram_gb, available_ram_gb) in standard library."""
    if sys.platform == "win32":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return round(stat.ullTotalPhys / (1024**3), 2), round(stat.ullAvailPhys / (1024**3), 2)
    elif os.path.exists("/proc/meminfo"):
        mem: Dict[str, int] = {}
        try:
            with open("/proc/meminfo", "r", encoding="ascii", errors="ignore") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        mem[parts[0].strip()] = int(parts[1].split()[0])
            total = round(mem.get("MemTotal", 0) / (1024 * 1024), 2)
            avail = round(mem.get("MemAvailable", mem.get("MemFree", 0)) / (1024 * 1024), 2)
            return total, avail
        except Exception:
            pass
    return None, None


def run_probe(target_label: str = "LOCAL") -> Dict[str, Any]:
    """Execute non-destructive capability probe."""
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    total_ram, avail_ram = get_ram_info()

    report: Dict[str, Any] = {
        "probe_metadata": {
            "target": target_label.upper(),
            "timestamp_utc": started_at,
            "status": "RUNNING",
            "probe_script_version": "1.0.0",
        },
        "system": {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "platform_string": platform.platform(),
            "hostname": platform.node(),
            "python_version": sys.version,
            "python_executable": sys.executable,
            "cpu_count_logical": os.cpu_count(),
            "ram_total_gb": total_ram,
            "ram_available_gb": avail_ram,
        },
        "pytorch": {},
        "gpu": {
            "cuda_available": False,
            "device_count": 0,
            "devices": [],
        },
        "safe_smoke_tests": {
            "performed": False,
            "all_passed": False,
            "checks": {},
        },
        "errors": [],
    }

    # Import torch and examine runtime
    try:
        import torch
        import torch.nn as nn

        report["pytorch"] = {
            "torch_version": torch.__version__,
            "torch_cuda_version": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "cudnn_version": torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None,
            "cudnn_enabled": torch.backends.cudnn.enabled,
            "cudnn_benchmark": torch.backends.cudnn.benchmark,
            "cudnn_deterministic": torch.backends.cudnn.deterministic,
            "allow_tf32_matmul": getattr(torch.backends.cuda.matmul, "allow_tf32", None),
            "allow_tf32_cudnn": getattr(torch.backends.cudnn, "allow_tf32", None),
            "amp_supported": hasattr(torch.amp, "autocast"),
            "autocast_available": hasattr(torch.cuda.amp, "autocast"),
            "bfloat16_supported": torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False,
            "float16_supported": True if torch.cuda.is_available() else False,
        }

        cuda_ok = torch.cuda.is_available()
        report["gpu"]["cuda_available"] = cuda_ok
        if cuda_ok:
            dev_count = torch.cuda.device_count()
            report["gpu"]["device_count"] = dev_count
            for i in range(dev_count):
                props = torch.cuda.get_device_properties(i)
                cap = torch.cuda.get_device_capability(i)
                try:
                    free_vram, total_vram = torch.cuda.mem_get_info(i)
                    free_mb = round(free_vram / (1024 * 1024), 2)
                    total_mb = round(total_vram / (1024 * 1024), 2)
                except Exception:
                    free_mb = None
                    total_mb = round(props.total_memory / (1024 * 1024), 2)

                dev_info = {
                    "index": i,
                    "name": props.name,
                    "compute_capability": f"{cap[0]}.{cap[1]}",
                    "total_memory_mb": total_mb,
                    "free_memory_mb": free_mb,
                    "multi_processor_count": getattr(props, "multi_processor_count", None),
                }
                report["gpu"]["devices"].append(dev_info)

            # Safe smoke tests
            report["safe_smoke_tests"]["performed"] = True
            checks: Dict[str, Any] = {}
            smoke_all_ok = True

            # Check 1: Tiny allocation
            t0 = time.perf_counter()
            try:
                t = torch.zeros((4, 4), device="cuda", dtype=torch.float32)
                torch.cuda.synchronize()
                elapsed_alloc = (time.perf_counter() - t0) * 1000
                checks["tiny_tensor_allocation"] = {
                    "status": "PASS",
                    "shape": list(t.shape),
                    "device": str(t.device),
                    "elapsed_ms": round(elapsed_alloc, 3),
                }
            except Exception as e:
                smoke_all_ok = False
                checks["tiny_tensor_allocation"] = {"status": "FAIL", "error": str(e)}

            # Check 2: Tiny matmul
            t0 = time.perf_counter()
            try:
                a = torch.randn((64, 64), device="cuda", dtype=torch.float32)
                b = torch.randn((64, 64), device="cuda", dtype=torch.float32)
                c = torch.matmul(a, b)
                torch.cuda.synchronize()
                elapsed_mm = (time.perf_counter() - t0) * 1000
                checks["tiny_matmul"] = {
                    "status": "PASS",
                    "shape": list(c.shape),
                    "elapsed_ms": round(elapsed_mm, 3),
                }
            except Exception as e:
                smoke_all_ok = False
                checks["tiny_matmul"] = {"status": "FAIL", "error": str(e)}

            # Check 3: Tiny conv2d matching Ocean Sentinel input (2 channels, 512x512 tile)
            t0 = time.perf_counter()
            try:
                conv = nn.Conv2d(2, 64, kernel_size=7, stride=2, padding=3, bias=False).cuda()
                x = torch.randn((1, 2, 128, 128), device="cuda", dtype=torch.float32)
                out = conv(x)
                torch.cuda.synchronize()
                elapsed_conv = (time.perf_counter() - t0) * 1000
                checks["tiny_conv2d"] = {
                    "status": "PASS",
                    "input_shape": list(x.shape),
                    "output_shape": list(out.shape),
                    "elapsed_ms": round(elapsed_conv, 3),
                }
            except Exception as e:
                smoke_all_ok = False
                checks["tiny_conv2d"] = {"status": "FAIL", "error": str(e)}

            # Check 4: AMP FP16 forward pass
            t0 = time.perf_counter()
            try:
                with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                    out_amp = conv(x)
                torch.cuda.synchronize()
                elapsed_amp = (time.perf_counter() - t0) * 1000
                checks["tiny_amp_fp16"] = {
                    "status": "PASS",
                    "dtype": str(out_amp.dtype),
                    "elapsed_ms": round(elapsed_amp, 3),
                }
            except Exception as e:
                smoke_all_ok = False
                checks["tiny_amp_fp16"] = {"status": "FAIL", "error": str(e)}

            report["safe_smoke_tests"]["all_passed"] = smoke_all_ok
            report["safe_smoke_tests"]["checks"] = checks

        else:
            report["safe_smoke_tests"]["performed"] = False
            report["safe_smoke_tests"]["reason"] = "CUDA is not available on this system."

        report["probe_metadata"]["status"] = "COMPLETE"

    except Exception as e:
        report["probe_metadata"]["status"] = "ERROR"
        report["errors"].append(str(e))

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Ocean Sentinel Non-Destructive Capability Probe")
    parser.add_argument(
        "--target",
        type=str,
        default="LOCAL",
        choices=["LOCAL", "KAGGLE"],
        help="Execution environment label (LOCAL or KAGGLE)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("capability_probe_results.json"),
        help="Path to save output JSON",
    )
    args = parser.parse_args()

    print(f"=== Ocean Sentinel Capability Probe [{args.target.upper()}] ===")
    results = run_probe(target_label=args.target)

    # Print summary
    print(f"Target:            {results['probe_metadata']['target']}")
    print(f"OS:                {results['system']['os']} {results['system']['os_release']}")
    print(f"Python:            {results['system']['python_version'].split()[0]}")
    print(f"RAM:               {results['system']['ram_total_gb']} GB total ({results['system']['ram_available_gb']} GB free)")
    pt = results.get("pytorch", {})
    print(f"PyTorch:           {pt.get('torch_version', 'N/A')}")
    print(f"CUDA Available:    {pt.get('cuda_available', False)}")
    gpu = results.get("gpu", {})
    if gpu.get("cuda_available"):
        print(f"CUDA Devices:      {gpu.get('device_count', 0)}")
        for d in gpu.get("devices", []):
            print(f"  [{d['index']}] {d['name']} | CC {d['compute_capability']} | VRAM: {d['total_memory_mb']} MB ({d['free_memory_mb']} MB free)")
        smoke = results.get("safe_smoke_tests", {})
        print(f"Smoke Tests:       {'ALL PASSED' if smoke.get('all_passed') else 'FAILED'}")
    else:
        print("GPU:               NO CUDA ACCELERATOR DETECTED")

    # Save JSON
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="ascii") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to:  {output_path}")

    # Return exit code
    if results["probe_metadata"]["status"] != "COMPLETE":
        return 1
    if gpu.get("cuda_available") and not results.get("safe_smoke_tests", {}).get("all_passed", False):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
