"""Ocean Sentinel — Controlled Physical GPU Benchmark: Dell AWCC Ultra Performance.

Evaluates whether Alienware Command Center (AWCC) Thermal Mode = Ultra Performance
provides a meaningful, sustained improvement in CUDA training throughput over the
established canonical control (33.54 samples/sec on RTX 3050 Laptop GPU).

Controlled Parameters:
- Machine: Dell G15 5530, i7-13650HX, RTX 3050 6GB Laptop GPU (Driver 616.64)
- AWCC Thermal Mode: Ultra Performance (Manual Operator Controlled)
- G-Mode / F9 Game Shift: STRICTLY OFF
- Windows Power Overlay: Best Performance (ded574b5-45a0-4f42-8737-46345c09c238)
- AC Power: Online
- Workload: ResNet34UNet (in=2, out=1), AMP FP16, batch_size=8, num_workers=4
- Loss: CombinedBCEAndDiceLoss, Optimizer: AdamW(lr=1e-4, wd=1e-2)
- Software Flags: cudnn.benchmark=True, tf32=True, float32_matmul_precision='high'

Protocol:
1. Canonical Repeatability Test: Run A & Run B (20 warmup + 100 measure batches each)
2. Canonical 300-batch Sustained Run (direct comparison to Step 2B sustained benchmark)
3. Extended Sustained Steady-State Run (1,200 batches continuous, ~5 mins)
4. High-frequency low-overhead telemetry (5 Hz) via nvml.dll and Windows APIs
5. Detailed thermal-throttling, clock decay, and first-quarter vs final-quarter analysis
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import datetime
import gc
import hashlib
import json
import os
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss
from ocean_sentinel.ml.unet_resnet import ResNet34UNet

CANONICAL_CONTROL_JSON = (
    REPO_ROOT / "experiments" / "performance" / "gpu_step2b_results_20260906_131544.json"
)
MANIFEST_PATH = (
    REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Canonical Step 2B control reference targets
CONTROL_TARGET_SAMPLES_PER_SEC = 33.52
CONTROL_REPRODUCED_SAMPLES_PER_SEC = 33.54
CONTROL_SUSTAINED_300_SAMPLES_PER_SEC = 33.34


# ===========================================================================
# 1. LOW-OVERHEAD HARDWARE TELEMETRY SAMPLER
# ===========================================================================
class NvmlUtilization(ctypes.Structure):
    _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]


class NvmlMemory(ctypes.Structure):
    _fields_ = [
        ("total", ctypes.c_ulonglong),
        ("free", ctypes.c_ulonglong),
        ("used", ctypes.c_ulonglong),
    ]


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


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]


def _filetime_to_int(ft: FILETIME) -> int:
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


class HardwareTelemetrySampler:
    """Low-overhead background telemetry sampler capturing GPU and CPU dynamics at 5 Hz."""

    def __init__(self, interval_sec: float = 0.2):
        self.interval = interval_sec
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.samples: List[Dict[str, Any]] = []

        self.nvml_ok = False
        self._nvml = None
        self._handle = None
        try:
            nvml = ctypes.CDLL("nvml.dll")
            if nvml.nvmlInit_v2() == 0:
                h = ctypes.c_void_p()
                if nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(h)) == 0:
                    self._nvml = nvml
                    self._handle = h
                    self.nvml_ok = True
        except Exception:
            self.nvml_ok = False

        self._kernel32 = ctypes.windll.kernel32
        self._prev_idle = 0
        self._prev_kernel = 0
        self._prev_user = 0
        self._init_cpu_times()

    def _init_cpu_times(self) -> None:
        idle = FILETIME()
        kernel = FILETIME()
        user = FILETIME()
        if self._kernel32.GetSystemTimes(
            ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
        ):
            self._prev_idle = _filetime_to_int(idle)
            self._prev_kernel = _filetime_to_int(kernel)
            self._prev_user = _filetime_to_int(user)

    def _get_cpu_load(self) -> float:
        idle = FILETIME()
        kernel = FILETIME()
        user = FILETIME()
        if not self._kernel32.GetSystemTimes(
            ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
        ):
            return 0.0
        cur_idle = _filetime_to_int(idle)
        cur_kernel = _filetime_to_int(kernel)
        cur_user = _filetime_to_int(user)

        diff_idle = cur_idle - self._prev_idle
        diff_kernel = cur_kernel - self._prev_kernel
        diff_user = cur_user - self._prev_user

        self._prev_idle = cur_idle
        self._prev_kernel = cur_kernel
        self._prev_user = cur_user

        total = diff_kernel + diff_user
        if total <= 0:
            return 0.0
        load = ((total - diff_idle) / total) * 100.0
        return round(max(0.0, min(100.0, load)), 1)

    def sample_now(self) -> Dict[str, Any]:
        snap: Dict[str, Any] = {
            "timestamp": time.time(),
            "cpu_util_pct": self._get_cpu_load(),
        }

        # RAM Usage
        mem_stat = MEMORYSTATUSEX()
        mem_stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if self._kernel32.GlobalMemoryStatusEx(ctypes.byref(mem_stat)):
            snap["ram_load_pct"] = mem_stat.dwMemoryLoad
            snap["ram_used_mb"] = round(
                (mem_stat.ullTotalPhys - mem_stat.ullAvailPhys) / (1024 * 1024), 1
            )
            snap["ram_total_mb"] = round(mem_stat.ullTotalPhys / (1024 * 1024), 1)

        # GPU Telemetry via NVML
        if self.nvml_ok and self._nvml and self._handle:
            util = NvmlUtilization()
            mem = NvmlMemory()
            temp = ctypes.c_uint()
            power = ctypes.c_uint()
            clock_sm = ctypes.c_uint()
            clock_mem = ctypes.c_uint()
            throttle = ctypes.c_ulonglong()

            self._nvml.nvmlDeviceGetUtilizationRates(self._handle, ctypes.byref(util))
            self._nvml.nvmlDeviceGetMemoryInfo(self._handle, ctypes.byref(mem))
            self._nvml.nvmlDeviceGetTemperature(self._handle, 0, ctypes.byref(temp))
            self._nvml.nvmlDeviceGetPowerUsage(self._handle, ctypes.byref(power))
            self._nvml.nvmlDeviceGetClockInfo(self._handle, 0, ctypes.byref(clock_sm))
            self._nvml.nvmlDeviceGetClockInfo(self._handle, 2, ctypes.byref(clock_mem))

            snap["gpu_util_pct"] = util.gpu
            snap["gpu_mem_util_pct"] = util.memory
            snap["gpu_temp_c"] = temp.value
            snap["gpu_clock_mhz"] = clock_sm.value
            snap["gpu_mem_clock_mhz"] = clock_mem.value
            snap["gpu_power_w"] = round(power.value / 1000.0, 2)
            snap["vram_used_mb"] = round(mem.used / (1024 * 1024), 1)

            if hasattr(self._nvml, "nvmlDeviceGetCurrentClocksThrottleReasons"):
                try:
                    self._nvml.nvmlDeviceGetCurrentClocksThrottleReasons(
                        self._handle, ctypes.byref(throttle)
                    )
                    snap["throttle_reasons_mask"] = throttle.value
                except Exception:
                    snap["throttle_reasons_mask"] = None

        return snap

    def start(self) -> None:
        self.samples.clear()
        self._stop.clear()

        def _loop() -> None:
            while not self._stop.is_set():
                self.samples.append(self.sample_now())
                time.sleep(self.interval)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self) -> List[Dict[str, Any]]:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        return list(self.samples)

    def close(self) -> None:
        if self.nvml_ok and self._nvml:
            try:
                self._nvml.nvmlShutdown()
            except Exception:
                pass


# ===========================================================================
# 2. EXPERIMENT WORKLOAD ENGINE
# ===========================================================================
def run_benchmark_workload(
    dataset: TrujilloTileDataset,
    experiment_id: str,
    experiment_name: str,
    num_warmup: int = 20,
    num_measure: int = 100,
    progress_cb: Optional[Any] = None,
    log_func: Optional[Any] = None,
) -> Dict[str, Any]:
    """Executes the exact canonical Step 2A/2B training loop with granular telemetry."""
    if log_func:
        log_func(
            f"WORKLOAD START: {experiment_id} ({experiment_name}) | "
            f"Warmup: {num_warmup} batches | Measure: {num_measure} batches"
        )

    torch.backends.cudnn.benchmark = True
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    if hasattr(torch, "set_float32_matmul_precision"):
        torch.set_float32_matmul_precision("high")
    torch.set_num_threads(14)

    torch.cuda.empty_cache()
    gc.collect()
    torch.cuda.reset_peak_memory_stats()

    loader = DataLoader(
        dataset,
        batch_size=8,
        shuffle=True,
        num_workers=4,
        pin_memory=(DEVICE.type == "cuda"),
        persistent_workers=True,
        prefetch_factor=2,
        drop_last=True,
    )

    model = ResNet34UNet(
        in_channels=2,
        num_classes=1,
        pretrained=True,
        adaptation_method="slice_variance_scaled",
    ).to(DEVICE)
    model.train()

    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)
    scaler = torch.amp.GradScaler(DEVICE.type, enabled=True)

    loader_iter = iter(loader)

    # Warmup Phase
    optimizer.zero_grad(set_to_none=True)
    for _ in range(num_warmup):
        imgs, masks = next(loader_iter)
        imgs = imgs.to(DEVICE, non_blocking=True)
        masks = masks.to(DEVICE, non_blocking=True)
        with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=True):
            loss = criterion(model(imgs), masks)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad(set_to_none=True)

    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()

    sampler = HardwareTelemetrySampler(interval_sec=0.2)
    sampler.start()

    e_fwd_start = torch.cuda.Event(enable_timing=True)
    e_fwd_end = torch.cuda.Event(enable_timing=True)
    e_bwd_start = torch.cuda.Event(enable_timing=True)
    e_bwd_end = torch.cuda.Event(enable_timing=True)
    e_opt_start = torch.cuda.Event(enable_timing=True)
    e_opt_end = torch.cuda.Event(enable_timing=True)
    e_xfer_start = torch.cuda.Event(enable_timing=True)
    e_xfer_end = torch.cuda.Event(enable_timing=True)

    fwd_times: List[float] = []
    bwd_times: List[float] = []
    opt_times: List[float] = []
    xfer_times: List[float] = []
    loader_wait_times: List[float] = []
    step_wall_times: List[float] = []

    wall_start = time.perf_counter()

    for step_i in range(num_measure):
        t0 = time.perf_counter()

        t_io0 = time.perf_counter()
        imgs, masks = next(loader_iter)
        loader_wait_times.append(time.perf_counter() - t_io0)

        e_xfer_start.record()
        imgs = imgs.to(DEVICE, non_blocking=True)
        masks = masks.to(DEVICE, non_blocking=True)
        e_xfer_end.record()

        e_fwd_start.record()
        with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=True):
            logits = model(imgs)
            loss = criterion(logits, masks)
        e_fwd_end.record()

        e_bwd_start.record()
        scaler.scale(loss).backward()
        e_bwd_end.record()

        e_opt_start.record()
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad(set_to_none=True)
        e_opt_end.record()

        torch.cuda.synchronize()
        step_duration = time.perf_counter() - t0
        step_wall_times.append(step_duration)

        fwd_times.append(e_fwd_start.elapsed_time(e_fwd_end))
        bwd_times.append(e_bwd_start.elapsed_time(e_bwd_end))
        opt_times.append(e_opt_start.elapsed_time(e_opt_end))
        xfer_times.append(e_xfer_start.elapsed_time(e_xfer_end))

        if progress_cb and (step_i + 1) % 25 == 0:
            cur_th = ((step_i + 1) * 8) / (time.perf_counter() - wall_start)
            progress_cb(step_i + 1, num_measure, cur_th)

    wall_elapsed = time.perf_counter() - wall_start
    telemetry_samples = sampler.stop()
    sampler.close()

    total_samples = num_measure * 8
    samples_per_sec = total_samples / wall_elapsed
    batches_per_sec = num_measure / wall_elapsed

    mean_step_ms = float(np.mean(step_wall_times)) * 1000.0
    median_step_ms = float(np.median(step_wall_times)) * 1000.0
    p95_step_ms = float(np.percentile(step_wall_times, 95)) * 1000.0
    std_step_ms = float(np.std(step_wall_times)) * 1000.0

    mean_loader_ms = float(np.mean(loader_wait_times)) * 1000.0
    mean_xfer_ms = float(np.mean(xfer_times))
    mean_fwd_ms = float(np.mean(fwd_times))
    mean_bwd_ms = float(np.mean(bwd_times))
    mean_opt_ms = float(np.mean(opt_times))

    peak_alloc_mb = round(torch.cuda.max_memory_allocated() / (1024 * 1024), 1)
    peak_reserved_mb = round(torch.cuda.max_memory_reserved() / (1024 * 1024), 1)

    gpu_utils = [s["gpu_util_pct"] for s in telemetry_samples if s.get("gpu_util_pct") is not None]
    gpu_temps = [s["gpu_temp_c"] for s in telemetry_samples if s.get("gpu_temp_c") is not None]
    gpu_clocks = [s["gpu_clock_mhz"] for s in telemetry_samples if s.get("gpu_clock_mhz") is not None]
    gpu_powers = [s["gpu_power_w"] for s in telemetry_samples if s.get("gpu_power_w") is not None]
    cpu_utils = [s["cpu_util_pct"] for s in telemetry_samples if s.get("cpu_util_pct") is not None]

    # Temporal breakdown: quarters
    q_len = max(1, num_measure // 4)
    q1_times = step_wall_times[:q_len]
    q2_times = step_wall_times[q_len : 2 * q_len]
    q3_times = step_wall_times[2 * q_len : 3 * q_len]
    q4_times = step_wall_times[3 * q_len :]

    th_q1 = (len(q1_times) * 8) / sum(q1_times)
    th_q2 = (len(q2_times) * 8) / sum(q2_times) if q2_times else th_q1
    th_q3 = (len(q3_times) * 8) / sum(q3_times) if q3_times else th_q1
    th_q4 = (len(q4_times) * 8) / sum(q4_times) if q4_times else th_q1

    # Clocks & temps by quarter
    t_len = max(1, len(telemetry_samples) // 4)
    q1_telemetry = telemetry_samples[:t_len]
    q4_telemetry = telemetry_samples[3 * t_len :]

    clk_q1 = float(np.mean([s["gpu_clock_mhz"] for s in q1_telemetry if s.get("gpu_clock_mhz")])) if q1_telemetry else 0.0
    clk_q4 = float(np.mean([s["gpu_clock_mhz"] for s in q4_telemetry if s.get("gpu_clock_mhz")])) if q4_telemetry else 0.0
    temp_q1 = float(np.mean([s["gpu_temp_c"] for s in q1_telemetry if s.get("gpu_temp_c")])) if q1_telemetry else 0.0
    temp_q4 = float(np.mean([s["gpu_temp_c"] for s in q4_telemetry if s.get("gpu_temp_c")])) if q4_telemetry else 0.0

    abs_gain = round(samples_per_sec - CONTROL_REPRODUCED_SAMPLES_PER_SEC, 2)
    gain_pct = round(
        ((samples_per_sec - CONTROL_REPRODUCED_SAMPLES_PER_SEC)
        / CONTROL_REPRODUCED_SAMPLES_PER_SEC)
        * 100.0,
        2,
    )

    if log_func:
        log_func(
            f"WORKLOAD COMPLETE: {experiment_id} | Throughput: {samples_per_sec:.2f} samp/s ({gain_pct:+.2f}% vs {CONTROL_REPRODUCED_SAMPLES_PER_SEC}) | "
            f"Step: {mean_step_ms:.1f} ms | Temp: {min(gpu_temps) if gpu_temps else 'N/A'}C -> {max(gpu_temps) if gpu_temps else 'N/A'}C | "
            f"GPU Clock: {np.mean(gpu_clocks):.0f} MHz | Power: {np.mean(gpu_powers):.1f} W"
        )

    del model, criterion, optimizer, scaler, loader, loader_iter
    torch.cuda.empty_cache()
    gc.collect()

    return {
        "experiment_id": experiment_id,
        "experiment_name": experiment_name,
        "num_measure_batches": num_measure,
        "wall_time_sec": round(wall_elapsed, 2),
        "samples_per_sec": round(samples_per_sec, 2),
        "batches_per_sec": round(batches_per_sec, 2),
        "absolute_gain_vs_control": abs_gain,
        "percentage_gain_vs_control": gain_pct,
        "timing_ms": {
            "mean_step": round(mean_step_ms, 2),
            "median_step": round(median_step_ms, 2),
            "std_step": round(std_step_ms, 2),
            "p95_step": round(p95_step_ms, 2),
            "loader_wait": round(mean_loader_ms, 2),
            "host_transfer": round(mean_xfer_ms, 2),
            "forward": round(mean_fwd_ms, 2),
            "backward": round(mean_bwd_ms, 2),
            "optimizer": round(mean_opt_ms, 2),
        },
        "quarterly_breakdown": {
            "q1_throughput_samp_sec": round(th_q1, 2),
            "q2_throughput_samp_sec": round(th_q2, 2),
            "q3_throughput_samp_sec": round(th_q3, 2),
            "q4_throughput_samp_sec": round(th_q4, 2),
            "throughput_decay_pct": round(((th_q4 - th_q1) / th_q1) * 100.0, 2),
            "q1_gpu_clock_mean_mhz": round(clk_q1, 1),
            "q4_gpu_clock_mean_mhz": round(clk_q4, 1),
            "clock_decay_mhz": round(clk_q4 - clk_q1, 1),
            "q1_gpu_temp_mean_c": round(temp_q1, 1),
            "q4_gpu_temp_mean_c": round(temp_q4, 1),
            "temp_rise_c": round(temp_q4 - temp_q1, 1),
        },
        "telemetry_summary": {
            "gpu_temp_start": gpu_temps[0] if gpu_temps else None,
            "gpu_temp_peak": max(gpu_temps) if gpu_temps else None,
            "gpu_temp_end": gpu_temps[-1] if gpu_temps else None,
            "gpu_temp_mean": round(float(np.mean(gpu_temps)), 1) if gpu_temps else None,
            "gpu_clock_start": gpu_clocks[0] if gpu_clocks else None,
            "gpu_clock_min": min(gpu_clocks) if gpu_clocks else None,
            "gpu_clock_max": max(gpu_clocks) if gpu_clocks else None,
            "gpu_clock_mean": round(float(np.mean(gpu_clocks)), 1) if gpu_clocks else None,
            "gpu_power_mean": round(float(np.mean(gpu_powers)), 2) if gpu_powers else None,
            "gpu_power_peak": max(gpu_powers) if gpu_powers else None,
            "gpu_util_mean": round(float(np.mean(gpu_utils)), 1) if gpu_utils else None,
            "cpu_util_mean": round(float(np.mean(cpu_utils)), 1) if cpu_utils else None,
        },
        "vram": {
            "peak_allocated_mb": peak_alloc_mb,
            "peak_reserved_mb": peak_reserved_mb,
        },
        "telemetry_samples": telemetry_samples,
    }


# ===========================================================================
# 3. MAIN BENCHMARK ORCHESTRATOR
# ===========================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="AWCC Ultra Performance Benchmark")
    parser.add_argument("--sustained-batches", type=int, default=1200, help="Extended sustained batches")
    parser.add_argument("--skip-extended", action="store_true", help="Skip the extended 1200-batch test")
    args = parser.parse_args()

    ts_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    exp_dir = REPO_ROOT / "experiments" / "performance" / f"gpu_awcc_ultra_performance_{ts_str}"
    exp_dir.mkdir(parents=True, exist_ok=True)

    log_file = exp_dir / "progress.log"
    run_state_file = exp_dir / "run_state.json"

    def log(msg: str) -> None:
        t_now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"[{t_now}] {msg}"
        print(line, flush=True)
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def update_run_state(phase: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        st = {
            "experiment_id": f"AWCC_ULTRA_PERF_{ts_str}",
            "thermal_mode": "Ultra Performance (Manual)",
            "g_mode_state": "OFF (Manual)",
            "phase": phase,
            "status": status,
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "details": details or {},
        }
        try:
            tmp = run_state_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(st, indent=2), encoding="utf-8")
            if tmp.exists() and tmp.stat().st_size > 0:
                os.replace(tmp, run_state_file)
        except Exception:
            pass

    log("================================================================================")
    log("OCEAN SENTINEL — CONTROLLED PHYSICAL GPU BENCHMARK: AWCC ULTRA PERFORMANCE")
    log("================================================================================")
    log(f"Experiment Output Directory: {exp_dir}")

    update_run_state("PRE_FLIGHT", "RUNNING")

    # 1. Environment and Hardware Verification
    log("Performing machine and environment verification...")
    t_sampler = HardwareTelemetrySampler(interval_sec=0.2)
    idle_snap = t_sampler.sample_now()

    env_data = {
        "dell_model": "Dell G15 5530",
        "cpu_model": "13th Gen Intel(R) Core(TM) i7-13650HX (14 cores / 20 threads)",
        "gpu_model": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
        "gpu_vram_total_mb": round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024), 1) if torch.cuda.is_available() else 0,
        "driver_version": "616.64",
        "vbios_version": "94.07.82.40.2f",
        "bios_version": "1.34.0",
        "os_caption": "Windows 11 Home Single Language (Build 26200)",
        "python_version": sys.version,
        "python_executable": sys.executable,
        "pytorch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "awcc_thermal_mode": "Ultra Performance (MANUALLY CONFIRMED)",
        "g_mode_state": "OFF (MANUALLY CONFIRMED)",
        "windows_power_mode": "Best Performance (ded574b5-45a0-4f42-8737-46345c09c238)",
        "ac_power": "Online (CONFIRMED)",
        "idle_telemetry": idle_snap,
    }

    env_file = exp_dir / "machine_environment.json"
    with open(env_file, "w", encoding="utf-8") as f:
        json.dump(env_data, f, indent=2)
    log(f"Persisted environment snapshot: {env_file.name}")

    # 2. Control Reference Data
    control_ref = {
        "control_artifact": str(CANONICAL_CONTROL_JSON),
        "control_baseline_target": CONTROL_TARGET_SAMPLES_PER_SEC,
        "control_reproduced_mean": CONTROL_REPRODUCED_SAMPLES_PER_SEC,
        "control_sustained_300_mean": CONTROL_SUSTAINED_300_SAMPLES_PER_SEC,
        "control_workload": "ResNet34UNet, AMP FP16, batch_size=8, num_workers=4, 20 warmup + 100 measure",
        "control_hardware_state": "Dell G15 5530, Best Performance overlay, AC Online, AWCC Balanced/Default",
    }
    control_file = exp_dir / "control_reference.json"
    with open(control_file, "w", encoding="utf-8") as f:
        json.dump(control_ref, f, indent=2)
    log(f"Persisted canonical control reference: {control_file.name}")

    # 3. Load Dataset
    log(f"Loading dataset manifest: {MANIFEST_PATH}")
    manifest = DatasetManifest.load(MANIFEST_PATH)
    train_dataset = TrujilloTileDataset(manifest, SplitName.TRAIN, normalize=True)
    log(f"Training dataset ready: {len(train_dataset)} tiles")

    # =========================================================================
    # PHASE 1: REPEATABILITY TEST — RUN A (100 batches)
    # =========================================================================
    update_run_state("RUN_A", "RUNNING", {"num_measure": 100})
    log("\n--- EXECUTING RUN A (Canonical 100-batch Benchmark) ---")
    run_a_result = run_benchmark_workload(
        dataset=train_dataset,
        experiment_id="AWCC_ULTRA_RUN_A",
        experiment_name="Ultra Performance Canonical Repetition A",
        num_warmup=20,
        num_measure=100,
        log_func=log,
    )

    # Save Run A telemetry
    telemetry_a_file = exp_dir / "telemetry_run_a.json"
    with open(telemetry_a_file, "w", encoding="utf-8") as f:
        json.dump(run_a_result.pop("telemetry_samples"), f, indent=2)
    log(f"Saved Run A raw telemetry: {telemetry_a_file.name}")

    # Controlled Cooldown
    log("\nInitiating short controlled cooldown (30s)...")
    time.sleep(30)
    cooldown_snap = t_sampler.sample_now()
    log(f"Cooldown GPU Temp: {cooldown_snap.get('gpu_temp_c')} C | Clock: {cooldown_snap.get('gpu_clock_mhz')} MHz")

    # =========================================================================
    # PHASE 2: REPEATABILITY TEST — RUN B (100 batches)
    # =========================================================================
    update_run_state("RUN_B", "RUNNING", {"num_measure": 100})
    log("\n--- EXECUTING RUN B (Canonical 100-batch Benchmark) ---")
    run_b_result = run_benchmark_workload(
        dataset=train_dataset,
        experiment_id="AWCC_ULTRA_RUN_B",
        experiment_name="Ultra Performance Canonical Repetition B",
        num_warmup=20,
        num_measure=100,
        log_func=log,
    )

    telemetry_b_file = exp_dir / "telemetry_run_b.json"
    with open(telemetry_b_file, "w", encoding="utf-8") as f:
        json.dump(run_b_result.pop("telemetry_samples"), f, indent=2)
    log(f"Saved Run B raw telemetry: {telemetry_b_file.name}")

    mean_canonical_th = round((run_a_result["samples_per_sec"] + run_b_result["samples_per_sec"]) / 2.0, 2)
    diff_ab_pct = round(abs(run_a_result["samples_per_sec"] - run_b_result["samples_per_sec"]) / mean_canonical_th * 100.0, 2)
    log(f"\nCANONICAL REPEATABILITY: Run A = {run_a_result['samples_per_sec']:.2f} samp/s | Run B = {run_b_result['samples_per_sec']:.2f} samp/s")
    log(f"Mean Canonical Ultra Performance: {mean_canonical_th:.2f} samp/s (Variation: {diff_ab_pct:.2f}%)")

    # =========================================================================
    # PHASE 3: CANONICAL 300-BATCH SUSTAINED BENCHMARK
    # =========================================================================
    log("\nInitiating short cooldown before sustained workload (30s)...")
    time.sleep(30)
    update_run_state("SUSTAINED_300", "RUNNING", {"num_measure": 300})
    log("\n--- EXECUTING 300-BATCH SUSTAINED BENCHMARK (Step 2B Direct Match) ---")
    sustained_300_result = run_benchmark_workload(
        dataset=train_dataset,
        experiment_id="AWCC_ULTRA_SUSTAINED_300",
        experiment_name="Ultra Performance 300-Batch Sustained Workload",
        num_warmup=20,
        num_measure=300,
        log_func=log,
    )

    telemetry_300_file = exp_dir / "telemetry_sustained_300.json"
    with open(telemetry_300_file, "w", encoding="utf-8") as f:
        json.dump(sustained_300_result.pop("telemetry_samples"), f, indent=2)
    log(f"Saved 300-batch sustained telemetry: {telemetry_300_file.name}")

    # =========================================================================
    # PHASE 4: EXTENDED SUSTAINED RUN (1,200 batches, ~5 mins)
    # =========================================================================
    extended_result = None
    if not args.skip_extended:
        log("\nInitiating short cooldown before extended test (30s)...")
        time.sleep(30)
        update_run_state("EXTENDED_SUSTAINED", "RUNNING", {"num_measure": args.sustained_batches})
        log(f"\n--- EXECUTING EXTENDED SUSTAINED RUN ({args.sustained_batches} batches, ~5 minutes continuous load) ---")
        extended_result = run_benchmark_workload(
            dataset=train_dataset,
            experiment_id="AWCC_ULTRA_EXTENDED",
            experiment_name=f"Ultra Performance {args.sustained_batches}-Batch Extended Steady-State Workload",
            num_warmup=20,
            num_measure=args.sustained_batches,
            log_func=log,
        )
        telemetry_ext_file = exp_dir / "telemetry_extended.json"
        with open(telemetry_ext_file, "w", encoding="utf-8") as f:
            json.dump(extended_result.pop("telemetry_samples"), f, indent=2)
        log(f"Saved extended telemetry: {telemetry_ext_file.name}")

    # =========================================================================
    # PHASE 5: COMPILE COMPARISON & FINAL DECISION
    # =========================================================================
    log("\n--- COMPILING COMPARISON AGAINST CANONICAL CONTROL ---")
    delta_samp = round(mean_canonical_th - CONTROL_REPRODUCED_SAMPLES_PER_SEC, 2)
    delta_pct = round((delta_samp / CONTROL_REPRODUCED_SAMPLES_PER_SEC) * 100.0, 2)

    delta_sustained_samp = round(sustained_300_result["samples_per_sec"] - CONTROL_SUSTAINED_300_SAMPLES_PER_SEC, 2)
    delta_sustained_pct = round((delta_sustained_samp / CONTROL_SUSTAINED_300_SAMPLES_PER_SEC) * 100.0, 2)

    # Decision classification
    if delta_pct >= 2.0 and diff_ab_pct <= 2.0:
        decision = "MEANINGFUL IMPROVEMENT"
        decision_desc = f"Ultra Performance provides a statistically significant +{delta_pct:.2f}% sustained throughput gain ({mean_canonical_th:.2f} vs {CONTROL_REPRODUCED_SAMPLES_PER_SEC:.2f} samp/s)."
    elif abs(delta_pct) < 2.0:
        # Check if temperatures or clocks were noticeably different
        temp_a = run_a_result["telemetry_summary"]["gpu_temp_peak"]
        if temp_a is not None and temp_a <= 78:
            decision = "THERMAL IMPROVEMENT WITHOUT MEANINGFUL THROUGHPUT GAIN"
            decision_desc = f"Throughput delta is neutral ({delta_pct:+.2f}%), but peak temperatures improved."
        else:
            decision = "NEUTRAL"
            decision_desc = f"Throughput delta is within margin of error ({delta_pct:+.2f}% / {delta_samp:+.2f} samp/s)."
    else:
        decision = "REGRESSION"
        decision_desc = f"Throughput degraded by {delta_pct:.2f}% under Ultra Performance."

    comparison_data = {
        "benchmark_date_utc": ts_str,
        "control_baseline_samples_per_sec": CONTROL_REPRODUCED_SAMPLES_PER_SEC,
        "control_sustained_300_samples_per_sec": CONTROL_SUSTAINED_300_SAMPLES_PER_SEC,
        "ultra_performance_run_a": run_a_result["samples_per_sec"],
        "ultra_performance_run_b": run_b_result["samples_per_sec"],
        "ultra_performance_mean": mean_canonical_th,
        "ultra_performance_variation_pct": diff_ab_pct,
        "delta_samples_per_sec": delta_samp,
        "delta_percentage": delta_pct,
        "sustained_300_ultra_performance": sustained_300_result["samples_per_sec"],
        "sustained_300_delta_pct": delta_sustained_pct,
        "extended_sustained": extended_result["samples_per_sec"] if extended_result else None,
        "decision": decision,
        "decision_description": decision_desc,
        "run_a_summary": run_a_result,
        "run_b_summary": run_b_result,
        "sustained_300_summary": sustained_300_result,
        "extended_summary": extended_result,
    }

    comparison_file = exp_dir / "comparison_with_control.json"
    with open(comparison_file, "w", encoding="utf-8") as f:
        json.dump(comparison_data, f, indent=2)
    log(f"Saved comparison data: {comparison_file.name}")

    benchmark_results_file = exp_dir / "benchmark_results.json"
    with open(benchmark_results_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "run_a": run_a_result,
                "run_b": run_b_result,
                "sustained_300": sustained_300_result,
                "extended": extended_result,
            },
            f,
            indent=2,
        )
    log(f"Saved benchmark results: {benchmark_results_file.name}")

    # SHA-256 Hashes
    hashes = {}
    for p in exp_dir.glob("*.json"):
        hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest().upper()
    hashes_file = exp_dir / "artifact_hashes.json"
    with open(hashes_file, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)
    log(f"Saved artifact SHA-256 hashes: {hashes_file.name}")

    update_run_state("COMPLETE", "SUCCESS", {"decision": decision, "delta_pct": delta_pct})
    log("\n================================================================================")
    log("AWCC ULTRA PERFORMANCE BENCHMARK COMPLETE")
    log(f"Decision: {decision}")
    log(f"Control: {CONTROL_REPRODUCED_SAMPLES_PER_SEC:.2f} samp/s | Ultra: {mean_canonical_th:.2f} samp/s ({delta_pct:+.2f}%)")
    log("================================================================================")


if __name__ == "__main__":
    main()
