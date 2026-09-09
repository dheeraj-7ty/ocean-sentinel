"""Ocean Sentinel — Controlled Physical GPU Benchmark: Dell G15 G-Mode (F9).

Evaluates whether Dell G15 5530 Game Shift / G-mode (F9) produces a meaningful,
repeatable improvement in sustained CUDA training throughput over the canonical
AWCC Optimized + G-mode OFF configuration.

Protocol & Safety:
1. Strict Protocol Separation:
   - 100-batch repeatability protocol (20 warmup + 100 measure)
   - 300-batch sustained protocol (20 warmup + 300 measure)
   - 600-batch steady-state protocol (100 warmup + 600 measure, divided into Q1-Q4)
   - 1,200-batch extended steady-state protocol (100 warmup + 1200 measure, Q1-Q4)
2. Telemetry:
   - 5 Hz sampling via nvml.dll and Windows APIs
   - GPU util, clock, power, temp, VRAM, throttle reasons
   - CPU util, system RAM load
3. Causality Discipline:
   - Explicit separation of OBSERVED FACTS, INFERENCES, and UNVERIFIED MECHANISMS.
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

MANIFEST_PATH = (
    REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
)
HISTORICAL_CONTROL_JSON = (
    REPO_ROOT / "experiments" / "performance" / "gpu_step2b_results_20260906_131544.json"
)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Historical canonical control references
HISTORICAL_CONTROL_SUSTAINED_300_SAMP_SEC = 33.34
HISTORICAL_CONTROL_100_REPEAT_SAMP_SEC = 33.54


# ===========================================================================
# 1. HARDWARE & SYSTEM TELEMETRY SAMPLER (5 Hz)
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
# 2. CANONICAL BENCHMARK ENGINE
# ===========================================================================
def run_workload(
    dataset: TrujilloTileDataset,
    experiment_id: str,
    experiment_name: str,
    num_warmup: int,
    num_measure: int,
    quarter_split: Optional[Tuple[int, int, int, int]] = None,
    log_func: Optional[Any] = None,
    progress_cb: Optional[Any] = None,
) -> Dict[str, Any]:
    """Runs a rigorously instrumented training workload matching canonical Step 2A/2B."""
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

    # 1. Warmup Phase (STRICT: completely excluded from throughput calculation)
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

    # 2. Measured Phase
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

        if progress_cb and (step_i + 1) % 50 == 0:
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
    std_step_ms = float(np.std(step_wall_times)) * 1000.0
    cv_step_pct = round((std_step_ms / mean_step_ms) * 100.0, 2)
    p95_step_ms = float(np.percentile(step_wall_times, 95)) * 1000.0

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

    # Quarterly Breakdown
    if quarter_split and sum(quarter_split) == num_measure:
        q1_sz, q2_sz, q3_sz, q4_sz = quarter_split
        idx0 = 0
        idx1 = q1_sz
        idx2 = q1_sz + q2_sz
        idx3 = q1_sz + q2_sz + q3_sz
        idx4 = num_measure
        q1_times = step_wall_times[idx0:idx1]
        q2_times = step_wall_times[idx1:idx2]
        q3_times = step_wall_times[idx2:idx3]
        q4_times = step_wall_times[idx3:idx4]
    else:
        q_len = max(1, num_measure // 4)
        q1_times = step_wall_times[:q_len]
        q2_times = step_wall_times[q_len : 2 * q_len]
        q3_times = step_wall_times[2 * q_len : 3 * q_len]
        q4_times = step_wall_times[3 * q_len :]

    th_q1 = (len(q1_times) * 8) / sum(q1_times)
    th_q2 = (len(q2_times) * 8) / sum(q2_times) if q2_times else th_q1
    th_q3 = (len(q3_times) * 8) / sum(q3_times) if q3_times else th_q1
    th_q4 = (len(q4_times) * 8) / sum(q4_times) if q4_times else th_q1

    t_len = max(1, len(telemetry_samples) // 4)
    q1_telemetry = telemetry_samples[:t_len]
    q4_telemetry = telemetry_samples[3 * t_len :]

    clk_q1 = float(np.mean([s["gpu_clock_mhz"] for s in q1_telemetry if s.get("gpu_clock_mhz")])) if q1_telemetry else 0.0
    clk_q4 = float(np.mean([s["gpu_clock_mhz"] for s in q4_telemetry if s.get("gpu_clock_mhz")])) if q4_telemetry else 0.0
    temp_q1 = float(np.mean([s["gpu_temp_c"] for s in q1_telemetry if s.get("gpu_temp_c")])) if q1_telemetry else 0.0
    temp_q4 = float(np.mean([s["gpu_temp_c"] for s in q4_telemetry if s.get("gpu_temp_c")])) if q4_telemetry else 0.0
    pwr_q1 = float(np.mean([s["gpu_power_w"] for s in q1_telemetry if s.get("gpu_power_w")])) if q1_telemetry else 0.0
    pwr_q4 = float(np.mean([s["gpu_power_w"] for s in q4_telemetry if s.get("gpu_power_w")])) if q4_telemetry else 0.0

    if log_func:
        log_func(
            f"WORKLOAD COMPLETE: {experiment_id} | Throughput: {samples_per_sec:.2f} samp/s | "
            f"Step: {mean_step_ms:.1f} ms (CV: {cv_step_pct:.1f}%) | "
            f"Clocks: {clk_q1:.0f} -> {clk_q4:.0f} MHz | Power: {pwr_q1:.1f} -> {pwr_q4:.1f} W | "
            f"Temp: {temp_q1:.1f} -> {temp_q4:.1f} C (Peak: {max(gpu_temps) if gpu_temps else 'N/A'} C)"
        )

    del model, criterion, optimizer, scaler, loader, loader_iter
    torch.cuda.empty_cache()
    gc.collect()

    return {
        "experiment_id": experiment_id,
        "experiment_name": experiment_name,
        "num_warmup_batches": num_warmup,
        "num_measure_batches": num_measure,
        "wall_time_sec": round(wall_elapsed, 2),
        "samples_per_sec": round(samples_per_sec, 2),
        "batches_per_sec": round(batches_per_sec, 2),
        "timing_ms": {
            "mean_step": round(mean_step_ms, 2),
            "median_step": round(median_step_ms, 2),
            "std_step": round(std_step_ms, 2),
            "cv_step_pct": cv_step_pct,
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
            "q1_gpu_power_mean_w": round(pwr_q1, 2),
            "q4_gpu_power_mean_w": round(pwr_q4, 2),
            "power_change_w": round(pwr_q4 - pwr_q1, 2),
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
# 3. ORCHESTRATION & PERSISTENCE
# ===========================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Dell G-Mode Controlled Benchmark")
    parser.add_argument(
        "--phase",
        choices=["control", "gmode", "compare"],
        required=True,
        help="Benchmark execution phase",
    )
    parser.add_argument(
        "--exp-dir",
        type=str,
        default=None,
        help="Path to dedicated experiment output directory",
    )
    args = parser.parse_args()

    ts_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    if args.exp_dir:
        exp_dir = Path(args.exp_dir)
    else:
        exp_dir = REPO_ROOT / "experiments" / "performance" / f"gpu_gmode_{ts_str}"

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

    def update_run_state(phase_name: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        st = {
            "experiment_id": f"GPU_GMODE_CONTROLLED_{ts_str}",
            "phase": phase_name,
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
    log(f"OCEAN SENTINEL — DELL G15 G-MODE CONTROLLED BENCHMARK | PHASE: {args.phase.upper()}")
    log("================================================================================")
    log(f"Experiment Output Directory: {exp_dir}")

    # Load dataset
    log(f"Loading dataset manifest: {MANIFEST_PATH}")
    manifest = DatasetManifest.load(MANIFEST_PATH)
    train_dataset = TrujilloTileDataset(manifest, SplitName.TRAIN, normalize=True)
    log(f"Training dataset ready: {len(train_dataset)} tiles")

    # =========================================================================
    # PHASE: CONTROL (AWCC Optimized + G-Mode OFF)
    # =========================================================================
    if args.phase == "control":
        log("\n--- EXECUTING SAME-SESSION CONTROL PROTOCOLS (AWCC OPTIMIZED / G-MODE OFF) ---")
        update_run_state("CONTROL_PRE_FLIGHT", "RUNNING")

        # Record machine environment
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
            "awcc_mode": "Optimized (Operator Confirmed)",
            "g_mode_state": "OFF (Operator Confirmed)",
            "windows_power_mode": "Best Performance (ded574b5-45a0-4f42-8737-46345c09c238)",
            "ac_power": "Online (True)",
            "idle_telemetry": idle_snap,
        }
        with open(exp_dir / "machine_environment.json", "w", encoding="utf-8") as f:
            json.dump(env_data, f, indent=2)

        # 1. Fresh Control Repeatability: Run A (100 batches)
        update_run_state("CONTROL_RUN_A", "RUNNING")
        log("\n[CONTROL] Running 100-batch Repeatability: Run A...")
        ctrl_run_a = run_workload(
            dataset=train_dataset,
            experiment_id="CONTROL_RUN_A",
            experiment_name="Control 100-batch Repeatability Run A",
            num_warmup=20,
            num_measure=100,
            log_func=log,
        )
        with open(exp_dir / "telemetry_control_run_a.json", "w", encoding="utf-8") as f:
            json.dump(ctrl_run_a.pop("telemetry_samples"), f, indent=2)

        # Cooldown
        log("Controlled cooldown (30s)...")
        time.sleep(30)

        # 2. Fresh Control Repeatability: Run B (100 batches)
        update_run_state("CONTROL_RUN_B", "RUNNING")
        log("\n[CONTROL] Running 100-batch Repeatability: Run B...")
        ctrl_run_b = run_workload(
            dataset=train_dataset,
            experiment_id="CONTROL_RUN_B",
            experiment_name="Control 100-batch Repeatability Run B",
            num_warmup=20,
            num_measure=100,
            log_func=log,
        )
        with open(exp_dir / "telemetry_control_run_b.json", "w", encoding="utf-8") as f:
            json.dump(ctrl_run_b.pop("telemetry_samples"), f, indent=2)

        ctrl_100_mean = round((ctrl_run_a["samples_per_sec"] + ctrl_run_b["samples_per_sec"]) / 2.0, 2)
        ctrl_100_diff = round(abs(ctrl_run_a["samples_per_sec"] - ctrl_run_b["samples_per_sec"]), 2)
        ctrl_100_cv = round((ctrl_100_diff / ctrl_100_mean) * 100.0, 2)
        log(f"[CONTROL] 100-batch Repeatability: Run A = {ctrl_run_a['samples_per_sec']:.2f}, Run B = {ctrl_run_b['samples_per_sec']:.2f} (Mean: {ctrl_100_mean:.2f} samp/s, Var: {ctrl_100_cv:.2f}%)")

        # Cooldown
        log("Controlled cooldown before sustained control (30s)...")
        time.sleep(30)

        # 3. Same-Session Sustained Control (300 batches, direct historical match)
        update_run_state("CONTROL_SUSTAINED_300", "RUNNING")
        log("\n[CONTROL] Running 300-batch Sustained Control Workload...")
        ctrl_sustained_300 = run_workload(
            dataset=train_dataset,
            experiment_id="CONTROL_SUSTAINED_300",
            experiment_name="Control 300-batch Sustained Workload",
            num_warmup=20,
            num_measure=300,
            log_func=log,
        )
        with open(exp_dir / "telemetry_control_sustained_300.json", "w", encoding="utf-8") as f:
            json.dump(ctrl_sustained_300.pop("telemetry_samples"), f, indent=2)

        control_summary = {
            "protocol_100_repeatability": {
                "run_a": ctrl_run_a,
                "run_b": ctrl_run_b,
                "mean_samples_per_sec": ctrl_100_mean,
                "variation_pct": ctrl_100_cv,
                "historical_reference": HISTORICAL_CONTROL_100_REPEAT_SAMP_SEC,
            },
            "protocol_300_sustained": {
                "sustained_300": ctrl_sustained_300,
                "samples_per_sec": ctrl_sustained_300["samples_per_sec"],
                "historical_reference": HISTORICAL_CONTROL_SUSTAINED_300_SAMP_SEC,
                "delta_vs_historical_samples_sec": round(ctrl_sustained_300["samples_per_sec"] - HISTORICAL_CONTROL_SUSTAINED_300_SAMP_SEC, 2),
                "delta_vs_historical_pct": round(((ctrl_sustained_300["samples_per_sec"] - HISTORICAL_CONTROL_SUSTAINED_300_SAMP_SEC) / HISTORICAL_CONTROL_SUSTAINED_300_SAMP_SEC) * 100.0, 2),
            },
        }

        with open(exp_dir / "control_results.json", "w", encoding="utf-8") as f:
            json.dump(control_summary, f, indent=2)

        log("\n[CONTROL COMPLETE] Control results successfully saved to control_results.json")
        log(f"Same-Session 300-batch Sustained Control: {ctrl_sustained_300['samples_per_sec']:.2f} samp/s (Historical: {HISTORICAL_CONTROL_SUSTAINED_300_SAMP_SEC:.2f} samp/s)")
        update_run_state("WAITING_FOR_OPERATOR_GMODE", "AWAITING_F9_ACTIVATION", {
            "control_results_path": str(exp_dir / "control_results.json"),
            "exp_dir": str(exp_dir),
        })

    # =========================================================================
    # PHASE: GMODE (F9 Game Shift Confirmed ON)
    # =========================================================================
    elif args.phase == "gmode":
        log("\n--- EXECUTING G-MODE EVALUATION PROTOCOLS (F9 GAME SHIFT ON) ---")
        update_run_state("GMODE_POST_ACTIVATION_CHECK", "RUNNING")

        # 1. G-Mode Run 1: 100 warmup + 600 measured (Q1=100, Q2=200, Q3=100, Q4=200)
        update_run_state("GMODE_RUN_1", "RUNNING")
        log("\n[G-MODE] Running Steady-State Run 1 (100 warmup + 600 measured)...")
        gmode_run_1 = run_workload(
            dataset=train_dataset,
            experiment_id="GMODE_RUN_1",
            experiment_name="G-Mode 600-batch Steady-State Run 1",
            num_warmup=100,
            num_measure=600,
            quarter_split=(100, 200, 100, 200),
            log_func=log,
        )
        with open(exp_dir / "telemetry_gmode_run_1.json", "w", encoding="utf-8") as f:
            json.dump(gmode_run_1.pop("telemetry_samples"), f, indent=2)

        # Cooldown
        log("Controlled cooldown (45s)...")
        time.sleep(45)

        # 2. G-Mode Extended Sustained: 100 warmup + 1,200 measured
        update_run_state("GMODE_EXTENDED_1200", "RUNNING")
        log("\n[G-MODE] Running Extended Sustained Workload (100 warmup + 1200 measured)...")
        gmode_extended = run_workload(
            dataset=train_dataset,
            experiment_id="GMODE_EXTENDED_1200",
            experiment_name="G-Mode 1200-batch Extended Steady-State",
            num_warmup=100,
            num_measure=1200,
            quarter_split=(300, 300, 300, 300),
            log_func=log,
        )
        with open(exp_dir / "telemetry_gmode_extended.json", "w", encoding="utf-8") as f:
            json.dump(gmode_extended.pop("telemetry_samples"), f, indent=2)

        # Cooldown
        log("Controlled cooldown (45s)...")
        time.sleep(45)

        # 3. G-Mode Run 2: 100 warmup + 600 measured
        update_run_state("GMODE_RUN_2", "RUNNING")
        log("\n[G-MODE] Running Steady-State Run 2 (100 warmup + 600 measured)...")
        gmode_run_2 = run_workload(
            dataset=train_dataset,
            experiment_id="GMODE_RUN_2",
            experiment_name="G-Mode 600-batch Steady-State Run 2",
            num_warmup=100,
            num_measure=600,
            quarter_split=(100, 200, 100, 200),
            log_func=log,
        )
        with open(exp_dir / "telemetry_gmode_run_2.json", "w", encoding="utf-8") as f:
            json.dump(gmode_run_2.pop("telemetry_samples"), f, indent=2)

        gmode_results = {
            "run_1_600": gmode_run_1,
            "extended_1200": gmode_extended,
            "run_2_600": gmode_run_2,
            "repeatability_600": {
                "run_1_samples_sec": gmode_run_1["samples_per_sec"],
                "run_2_samples_sec": gmode_run_2["samples_per_sec"],
                "absolute_diff": round(abs(gmode_run_1["samples_per_sec"] - gmode_run_2["samples_per_sec"]), 2),
                "pct_diff": round(abs(gmode_run_1["samples_per_sec"] - gmode_run_2["samples_per_sec"]) / ((gmode_run_1["samples_per_sec"] + gmode_run_2["samples_per_sec"]) / 2.0) * 100.0, 2),
            },
        }

        with open(exp_dir / "gmode_results.json", "w", encoding="utf-8") as f:
            json.dump(gmode_results, f, indent=2)

        # Read control results for comparison
        ctrl_path = exp_dir / "control_results.json"
        if not ctrl_path.exists():
            log(f"WARNING: control_results.json not found in {exp_dir}")
            ctrl_results = {}
        else:
            with open(ctrl_path, "r", encoding="utf-8") as f:
                ctrl_results = json.load(f)

        # Compare and compile
        ctrl_sustained_samp = ctrl_results.get("protocol_300_sustained", {}).get("samples_per_sec", HISTORICAL_CONTROL_SUSTAINED_300_SAMP_SEC)
        gmode_sustained_samp = gmode_extended["samples_per_sec"]

        delta_samp = round(gmode_sustained_samp - ctrl_sustained_samp, 2)
        delta_pct = round((delta_samp / ctrl_sustained_samp) * 100.0, 2)

        # Decision rule
        if delta_pct >= 2.0:
            decision = "MEANINGFUL IMPROVEMENT"
        elif delta_pct <= -2.0:
            decision = "REGRESSION"
        elif abs(delta_pct) < 2.0 and gmode_extended["telemetry_summary"]["gpu_temp_peak"] < ctrl_results.get("protocol_300_sustained", {}).get("sustained_300", {}).get("telemetry_summary", {}).get("gpu_temp_peak", 999) - 3:
            decision = "THERMAL IMPROVEMENT WITHOUT MEANINGFUL THROUGHPUT IMPROVEMENT"
        elif abs(delta_pct) < 2.0:
            decision = "NEUTRAL"
        else:
            decision = "INCONCLUSIVE"

        comparison = {
            "primary_metric": {
                "control_sustained_samples_per_sec": ctrl_sustained_samp,
                "gmode_sustained_samples_per_sec": gmode_sustained_samp,
                "delta_samples_per_sec": delta_samp,
                "delta_percentage": delta_pct,
                "protocol_note": "Comparing Same-Session Sustained Control (300 batches) against G-Mode Extended Steady-State (1200 batches)",
            },
            "secondary_historical_comparison": {
                "historical_control_300_sustained": HISTORICAL_CONTROL_SUSTAINED_300_SAMP_SEC,
                "delta_vs_historical_samples_sec": round(gmode_sustained_samp - HISTORICAL_CONTROL_SUSTAINED_300_SAMP_SEC, 2),
                "delta_vs_historical_pct": round(((gmode_sustained_samp - HISTORICAL_CONTROL_SUSTAINED_300_SAMP_SEC) / HISTORICAL_CONTROL_SUSTAINED_300_SAMP_SEC) * 100.0, 2),
            },
            "decision": decision,
            "control_data": ctrl_results,
            "gmode_data": gmode_results,
        }

        with open(exp_dir / "comparison.json", "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2)

        # Artifact Hashes
        hashes = {}
        for p in exp_dir.glob("*.json"):
            hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest().upper()
        with open(exp_dir / "artifact_hashes.json", "w", encoding="utf-8") as f:
            json.dump(hashes, f, indent=2)

        update_run_state("EXPERIMENT_COMPLETE", "SUCCESS", {"decision": decision, "delta_pct": delta_pct})
        log("\n================================================================================")
        log(f"G-MODE BENCHMARK COMPLETE | DECISION: {decision}")
        log(f"Sustained Control: {ctrl_sustained_samp:.2f} samp/s | G-Mode Extended: {gmode_sustained_samp:.2f} samp/s ({delta_pct:+.2f}%)")
        log("================================================================================")


if __name__ == "__main__":
    main()
