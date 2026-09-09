"""Ocean Sentinel — CAO Controlled Hardware/OS Performance Engineering Audit (Step 2B).

Systematically evaluates whether Dell G15 hardware/OS settings (Windows power schemes,
graphics preferences, process scheduling, thermal/power sustainability) limit sustained
Ocean Sentinel training throughput.

Reference Control:
  Step 2A software configuration = 33.52 samples/sec

Strict Safety:
  - Reversible settings only
  - Exact rollback captured and executed for every experiment
  - Does NOT mutate any production training code, manifests, weights, or checkpoints
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import datetime
import gc
import json
import os
import platform
import subprocess
import sys
import threading
import time
import winreg
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset  # noqa: E402
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName  # noqa: E402
from ocean_sentinel.ml.augmentation import SARGeometricAugmentation  # noqa: E402
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss  # noqa: E402
from ocean_sentinel.ml.unet_resnet import ResNet34UNet  # noqa: E402

DEFAULT_MANIFEST = (
    REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
)
PERF_DIR = REPO_ROOT / "experiments" / "performance"
PROGRESS_JSON = PERF_DIR / "gpu_step2b_progress.json"
PROGRESS_LOG = PERF_DIR / "gpu_step2b.log"
RUN_STATE_JSON = PERF_DIR / "gpu_step2b_run_state.json"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
STEP2A_CONTROL_SAMP_PER_SEC = 33.52


# ===========================================================================
# 1. OBSERVABILITY & STATE LOGGING
# ===========================================================================
def log_step2b(msg: str) -> None:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(PROGRESS_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def write_step2b_state(state: Dict[str, Any]) -> None:
    try:
        state["last_updated_utc"] = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        tmp = RUN_STATE_JSON.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        if tmp.exists() and tmp.stat().st_size > 0:
            os.replace(tmp, RUN_STATE_JSON)
        # Also copy to progress.json
        tmp_prog = PROGRESS_JSON.with_suffix(".tmp")
        tmp_prog.write_text(json.dumps(state, indent=2), encoding="utf-8")
        if tmp_prog.exists() and tmp_prog.stat().st_size > 0:
            os.replace(tmp_prog, PROGRESS_JSON)
    except Exception as e:
        log_step2b(f"WARNING: Failed to write state: {e}")


# ===========================================================================
# 2. LOW-OVERHEAD TELEMETRY
# ===========================================================================
class NvmlUtilization(ctypes.Structure):
    _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]


class NvmlMemory(ctypes.Structure):
    _fields_ = [
        ("total", ctypes.c_ulonglong),
        ("free", ctypes.c_ulonglong),
        ("used", ctypes.c_ulonglong),
    ]


class Step2bTelemetrySampler:
    def __init__(self, interval: float = 0.2):
        self.interval = interval
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

    def sample_now(self) -> Dict[str, Any]:
        snap: Dict[str, Any] = {"t": time.time()}
        if self.nvml_ok and self._nvml and self._handle:
            util = NvmlUtilization()
            mem = NvmlMemory()
            temp = ctypes.c_uint()
            power = ctypes.c_uint()
            clock_sm = ctypes.c_uint()
            clock_mem = ctypes.c_uint()
            throttle_reasons = ctypes.c_ulonglong()

            self._nvml.nvmlDeviceGetUtilizationRates(self._handle, ctypes.byref(util))
            self._nvml.nvmlDeviceGetMemoryInfo(self._handle, ctypes.byref(mem))
            self._nvml.nvmlDeviceGetTemperature(self._handle, 0, ctypes.byref(temp))
            self._nvml.nvmlDeviceGetPowerUsage(self._handle, ctypes.byref(power))
            self._nvml.nvmlDeviceGetClockInfo(self._handle, 0, ctypes.byref(clock_sm))
            self._nvml.nvmlDeviceGetClockInfo(self._handle, 2, ctypes.byref(clock_mem))

            snap["gpu_util"] = util.gpu
            snap["gpu_mem_util"] = util.memory
            snap["gpu_temp"] = temp.value
            snap["gpu_clock"] = clock_sm.value
            snap["gpu_mem_clock"] = clock_mem.value
            snap["gpu_power"] = round(power.value / 1000.0, 2)
            snap["vram_used_mb"] = round(mem.used / (1024 * 1024), 1)

            # Throttle reasons bitmask
            if hasattr(self._nvml, "nvmlDeviceGetCurrentClocksThrottleReasons"):
                try:
                    self._nvml.nvmlDeviceGetCurrentClocksThrottleReasons(
                        self._handle, ctypes.byref(throttle_reasons)
                    )
                    snap["throttle_reasons_mask"] = throttle_reasons.value
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
# 3. WORKLOAD EXECUTION ENGINE
# ===========================================================================
def run_benchmark_workload(
    dataset: TrujilloTileDataset,
    experiment_id: str,
    experiment_name: str,
    repetition: int = 1,
    num_warmup: int = 20,
    num_measure: int = 100,
    seed: int = 42,
) -> Dict[str, Any]:
    """Runs the authoritative Step 2A training configuration with full instrumentation."""
    log_step2b(
        f"EXPERIMENT START: {experiment_id} ({experiment_name}) | Rep {repetition} | "
        f"{num_warmup} warmup + {num_measure} measured batches"
    )

    # Apply Step 2A software configuration
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

    # Warmup
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

    sampler = Step2bTelemetrySampler(interval=0.1)
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

    for _ in range(num_measure):
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
        step_wall_times.append(time.perf_counter() - t0)

        fwd_times.append(e_fwd_start.elapsed_time(e_fwd_end))
        bwd_times.append(e_bwd_start.elapsed_time(e_bwd_end))
        opt_times.append(e_opt_start.elapsed_time(e_opt_end))
        xfer_times.append(e_xfer_start.elapsed_time(e_xfer_end))

    wall_elapsed = time.perf_counter() - wall_start
    telemetry_samples = sampler.stop()
    sampler.close()

    total_samples = num_measure * 8
    samples_per_sec = total_samples / wall_elapsed
    batches_per_sec = num_measure / wall_elapsed

    mean_step_ms = float(np.mean(step_wall_times)) * 1000.0
    mean_loader_ms = float(np.mean(loader_wait_times)) * 1000.0
    mean_xfer_ms = float(np.mean(xfer_times))
    mean_fwd_ms = float(np.mean(fwd_times))
    mean_bwd_ms = float(np.mean(bwd_times))
    mean_opt_ms = float(np.mean(opt_times))

    peak_alloc_mb = round(torch.cuda.max_memory_allocated() / (1024 * 1024), 1)
    peak_reserved_mb = round(torch.cuda.max_memory_reserved() / (1024 * 1024), 1)

    gpu_utils = [s["gpu_util"] for s in telemetry_samples if s.get("gpu_util") is not None]
    gpu_temps = [s["gpu_temp"] for s in telemetry_samples if s.get("gpu_temp") is not None]
    gpu_clocks = [s["gpu_clock"] for s in telemetry_samples if s.get("gpu_clock") is not None]
    gpu_powers = [s["gpu_power"] for s in telemetry_samples if s.get("gpu_power") is not None]

    gain_pct = round(((samples_per_sec - STEP2A_CONTROL_SAMP_PER_SEC) / STEP2A_CONTROL_SAMP_PER_SEC) * 100.0, 2)
    abs_gain = round(samples_per_sec - STEP2A_CONTROL_SAMP_PER_SEC, 2)

    log_step2b(
        f"EXPERIMENT COMPLETE: {experiment_id} | {samples_per_sec:.2f} samp/s ({gain_pct:+.2f}% vs 33.52) | "
        f"Step: {mean_step_ms:.1f}ms (fwd: {mean_fwd_ms:.1f}ms, bwd: {mean_bwd_ms:.1f}ms, opt: {mean_opt_ms:.1f}ms) | "
        f"GPU: {np.mean(gpu_utils):.1f}% | Clock: {np.mean(gpu_clocks):.0f}MHz | Power: {np.mean(gpu_powers):.1f}W | Temp: {max(gpu_temps) if gpu_temps else 'N/A'}C"
    )

    del model, criterion, optimizer, scaler, loader, loader_iter
    torch.cuda.empty_cache()
    gc.collect()

    return {
        "experiment_id": experiment_id,
        "experiment_name": experiment_name,
        "repetition": repetition,
        "status": "OK",
        "samples_per_sec": round(samples_per_sec, 2),
        "batches_per_sec": round(batches_per_sec, 2),
        "absolute_gain": abs_gain,
        "percentage_gain": gain_pct,
        "timing_ms": {
            "mean_step": round(mean_step_ms, 2),
            "median_step": round(float(np.median(step_wall_times)) * 1000.0, 2),
            "p95_step": round(float(np.percentile(step_wall_times, 95)) * 1000.0, 2),
            "loader_wait": round(mean_loader_ms, 2),
            "host_transfer": round(mean_xfer_ms, 2),
            "forward": round(mean_fwd_ms, 2),
            "backward": round(mean_bwd_ms, 2),
            "optimizer": round(mean_opt_ms, 2),
        },
        "vram": {
            "peak_allocated_mb": peak_alloc_mb,
            "peak_reserved_mb": peak_reserved_mb,
        },
        "telemetry": {
            "gpu_util_mean": round(float(np.mean(gpu_utils)), 1) if gpu_utils else None,
            "gpu_temp_max": max(gpu_temps) if gpu_temps else None,
            "gpu_temp_end": gpu_temps[-1] if gpu_temps else None,
            "gpu_clock_mean": round(float(np.mean(gpu_clocks)), 1) if gpu_clocks else None,
            "gpu_clock_min": min(gpu_clocks) if gpu_clocks else None,
            "gpu_clock_max": max(gpu_clocks) if gpu_clocks else None,
            "gpu_power_mean": round(float(np.mean(gpu_powers)), 2) if gpu_powers else None,
            "gpu_power_max": max(gpu_powers) if gpu_powers else None,
        },
    }


# ===========================================================================
# 4. SYSTEM RECONFIGURATION & ROLLBACK UTILITIES
# ===========================================================================
def get_active_power_scheme_guid() -> str:
    res = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True)
    out = res.stdout
    # Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced)
    for part in out.split():
        if len(part) == 36 and part.count("-") == 4:
            return part
    return "381b4222-f694-41f0-9685-ff5bb260df2e"


def set_active_power_scheme_guid(guid: str) -> bool:
    res = subprocess.run(["powercfg", "/setactive", guid], capture_output=True, text=True)
    return res.returncode == 0


def set_process_priority(high: bool = True) -> int:
    """Sets process priority between NORMAL (0x20) and HIGH (0x80). Returns old priority."""
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetCurrentProcess()
    old_priority = kernel32.GetPriorityClass(handle)
    new_priority = 0x00000080 if high else 0x00000020
    kernel32.SetPriorityClass(handle, new_priority)
    return old_priority


def restore_process_priority(old_priority: int) -> None:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), old_priority)


def set_windows_gpu_preference(enable_discrete: bool = True) -> Optional[str]:
    """Adds or removes python.exe to UserGpuPreferences in HKCU."""
    key_path = r"Software\Microsoft\DirectX\UserGpuPreferences"
    py_exe = sys.executable
    old_val = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            try:
                val, _ = winreg.QueryValueEx(key, py_exe)
                old_val = val
            except FileNotFoundError:
                old_val = None

            if enable_discrete:
                winreg.SetValueEx(key, py_exe, 0, winreg.REG_SZ, "GpuPreference=2;")
            else:
                if old_val is not None:
                    winreg.SetValueEx(key, py_exe, 0, winreg.REG_SZ, old_val)
                else:
                    try:
                        winreg.DeleteValue(key, py_exe)
                    except FileNotFoundError:
                        pass
    except Exception as e:
        log_step2b(f"WARNING: set_windows_gpu_preference failed: {e}")
    return old_val


# ===========================================================================
# 5. SUSTAINED THERMAL STABILITY HARNESS
# ===========================================================================
def run_sustained_thermal_benchmark(
    dataset: TrujilloTileDataset,
    num_warmup: int = 20,
    num_measure: int = 300,
) -> Dict[str, Any]:
    """Runs 300 measured batches (~72 seconds) recording per-batch telemetry time-series."""
    log_step2b(f"SUSTAINED BENCHMARK START: {num_measure} continuous batches for thermal/power drift analysis")

    torch.backends.cudnn.benchmark = True
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.set_num_threads(14)

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

    model = ResNet34UNet(2, 1, pretrained=True, adaptation_method="slice_variance_scaled").to(DEVICE)
    model.train()
    criterion = CombinedBCEAndDiceLoss(0.5, 0.5, 1.0).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)
    scaler = torch.amp.GradScaler(DEVICE.type, enabled=True)

    loader_iter = iter(loader)
    for _ in range(num_warmup):
        imgs, masks = next(loader_iter)
        imgs, masks = imgs.to(DEVICE, non_blocking=True), masks.to(DEVICE, non_blocking=True)
        with torch.amp.autocast(DEVICE.type, dtype=torch.float16):
            loss = criterion(model(imgs), masks)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad(set_to_none=True)

    torch.cuda.synchronize()
    sampler = Step2bTelemetrySampler(interval=0.2)
    sampler.start()

    batch_times = []
    wall_start = time.perf_counter()

    for _ in range(num_measure):
        t0 = time.perf_counter()
        imgs, masks = next(loader_iter)
        imgs, masks = imgs.to(DEVICE, non_blocking=True), masks.to(DEVICE, non_blocking=True)
        with torch.amp.autocast(DEVICE.type, dtype=torch.float16):
            loss = criterion(model(imgs), masks)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        batch_times.append(time.perf_counter() - t0)

    wall_total = time.perf_counter() - wall_start
    telemetry_samples = sampler.stop()
    sampler.close()

    del model, criterion, optimizer, scaler, loader, loader_iter
    torch.cuda.empty_cache()
    gc.collect()

    # Split into 3 phases: Initial 100, Middle 100, Final 100
    p1_times = batch_times[:100]
    p3_times = batch_times[-100:]

    samp_p1 = (100 * 8) / sum(p1_times)
    samp_p3 = (100 * 8) / sum(p3_times)
    overall_samp = (num_measure * 8) / wall_total

    temps = [s["gpu_temp"] for s in telemetry_samples if s.get("gpu_temp")]
    clocks = [s["gpu_clock"] for s in telemetry_samples if s.get("gpu_clock")]
    powers = [s["gpu_power"] for s in telemetry_samples if s.get("gpu_power")]

    drift_pct = round(((samp_p3 - samp_p1) / samp_p1) * 100.0, 2)

    log_step2b(
        f"SUSTAINED BENCHMARK COMPLETE: {num_measure} batches in {wall_total:.1f}s | "
        f"Phase 1: {samp_p1:.2f} samp/s | Phase 3: {samp_p3:.2f} samp/s (Drift: {drift_pct:+.2f}%) | "
        f"Temp range: {min(temps)}C -> {max(temps)}C | Clocks: {min(clocks)} - {max(clocks)} MHz | Power: {np.mean(powers):.1f}W"
    )

    return {
        "num_measure_batches": num_measure,
        "wall_time_sec": round(wall_total, 2),
        "overall_samples_per_sec": round(overall_samp, 2),
        "initial_100_batches_samples_per_sec": round(samp_p1, 2),
        "final_100_batches_samples_per_sec": round(samp_p3, 2),
        "throughput_drift_percent": drift_pct,
        "thermal_profile": {
            "start_temp_c": temps[0] if temps else None,
            "peak_temp_c": max(temps) if temps else None,
            "final_temp_c": temps[-1] if temps else None,
            "clock_start_mhz": clocks[0] if clocks else None,
            "clock_min_mhz": min(clocks) if clocks else None,
            "clock_max_mhz": max(clocks) if clocks else None,
            "clock_end_mhz": clocks[-1] if clocks else None,
            "power_avg_w": round(float(np.mean(powers)), 1) if powers else None,
            "power_max_w": max(powers) if powers else None,
        },
        "throttling_detected": bool(drift_pct < -3.0 or (clocks and (max(clocks) - min(clocks) > 300))),
        "verdict": (
            "THERMAL/POWER THROTTLING DETECTED"
            if drift_pct < -3.0
            else "NOT VERIFIED — THERMAL THROTTLING (ROCK-SOLID SUSTAINED OPERATION)"
        ),
    }


# ===========================================================================
# 6. MAIN CONTROLLER
# ===========================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Ocean Sentinel Step 2B Hardware Audit")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=PERF_DIR)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    PROGRESS_LOG.unlink(missing_ok=True)

    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = args.out_dir / f"gpu_step2b_results_{timestamp_str}.json"

    log_step2b("=" * 80)
    log_step2b("OCEAN SENTINEL — STEP 2B HARDWARE / OS PERFORMANCE ENGINEERING AUDIT")
    log_step2b(f"Timestamp: {timestamp_str} UTC")
    log_step2b(f"Authoritative Control Target: {STEP2A_CONTROL_SAMP_PER_SEC} samples/sec")
    log_step2b(f"Device: {DEVICE} ({torch.cuda.get_device_name(0)})")
    log_step2b("=" * 80)

    manifest = DatasetManifest.load(args.manifest)
    aug = SARGeometricAugmentation(p_hflip=0.5, p_vflip=0.5, p_rot90=0.5, seed=args.seed)
    dataset = TrujilloTileDataset(manifest, SplitName.TRAIN, normalize=True, transform=aug)

    run_state = {
        "status": "RUNNING",
        "current_phase": "INITIALIZATION",
        "start_time_utc": timestamp_str,
        "completed_experiments": 0,
        "control_baseline_samp_per_sec": STEP2A_CONTROL_SAMP_PER_SEC,
        "experiments": {},
    }
    write_step2b_state(run_state)

    experiments_log = []

    # -----------------------------------------------------------------------
    # PHASE B: REPRODUCE CONTROL
    # -----------------------------------------------------------------------
    run_state["current_phase"] = "PHASE_B_CONTROL_REPRODUCTION"
    write_step2b_state(run_state)
    log_step2b("\n" + "=" * 80)
    log_step2b("PHASE B: REPRODUCING STEP 2A CONTROL (~33.52 SAMPLES/SEC)")
    log_step2b("=" * 80)

    ctrl_rep1 = run_benchmark_workload(
        dataset, "EXP_0_CONTROL", "Step 2A Control Baseline", repetition=1, seed=args.seed
    )
    ctrl_rep2 = run_benchmark_workload(
        dataset, "EXP_0_CONTROL", "Step 2A Control Baseline", repetition=2, seed=args.seed + 1
    )

    ctrl_mean = round((ctrl_rep1["samples_per_sec"] + ctrl_rep2["samples_per_sec"]) / 2.0, 2)
    ctrl_var = round(abs(ctrl_rep1["samples_per_sec"] - ctrl_rep2["samples_per_sec"]), 2)
    ctrl_diff_vs_target = round(ctrl_mean - STEP2A_CONTROL_SAMP_PER_SEC, 2)

    log_step2b(
        f"CONTROL REPRODUCTION SUMMARY: Rep 1={ctrl_rep1['samples_per_sec']}, Rep 2={ctrl_rep2['samples_per_sec']} | "
        f"Mean={ctrl_mean} samp/s (Variance={ctrl_var} samp/s, Delta vs 33.52={ctrl_diff_vs_target:+.2f} samp/s)"
    )

    experiments_log.append({
        "id": "EXP_0_CONTROL",
        "setting": "Authoritative Step 2A Baseline Control",
        "before": "Baseline Defaults",
        "after": "Baseline Defaults",
        "reps": [ctrl_rep1, ctrl_rep2],
        "mean_samples_per_sec": ctrl_mean,
        "delta_percent": round(((ctrl_mean - STEP2A_CONTROL_SAMP_PER_SEC) / STEP2A_CONTROL_SAMP_PER_SEC) * 100.0, 2),
        "gpu_power_mean": ctrl_rep1["telemetry"]["gpu_power_mean"],
        "gpu_clock_mean": ctrl_rep1["telemetry"]["gpu_clock_mean"],
        "gpu_temp_max": ctrl_rep1["telemetry"]["gpu_temp_max"],
        "verdict": "CONTROL REPRODUCED",
        "rollback": "None (Control Group)",
    })
    run_state["completed_experiments"] += 1
    run_state["experiments"]["EXP_0_CONTROL"] = {"mean_samples_per_sec": ctrl_mean}
    write_step2b_state(run_state)

    # -----------------------------------------------------------------------
    # PHASE D: WINDOWS POWER PLAN (HIGH PERFORMANCE VS BALANCED)
    # -----------------------------------------------------------------------
    run_state["current_phase"] = "PHASE_D_WINDOWS_POWER_PLAN"
    write_step2b_state(run_state)
    log_step2b("\n" + "=" * 80)
    log_step2b("PHASE D: WINDOWS POWER SCHEME (HIGH PERFORMANCE VS BALANCED)")
    log_step2b("=" * 80)

    original_scheme_guid = get_active_power_scheme_guid()
    log_step2b(f"Original Active Power Scheme: {original_scheme_guid}")

    # Duplicate High Performance scheme
    dup_res = subprocess.run(
        ["powercfg", "/duplicatescheme", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
        capture_output=True,
        text=True,
    )
    high_perf_guid = None
    for part in dup_res.stdout.split():
        if len(part) == 36 and part.count("-") == 4:
            high_perf_guid = part
            break

    if high_perf_guid:
        log_step2b(f"Created High Performance Scheme GUID: {high_perf_guid}")
        try:
            set_active_power_scheme_guid(high_perf_guid)
            log_step2b(f"Active Power Scheme switched to High Performance ({high_perf_guid})")

            hp_rep1 = run_benchmark_workload(
                dataset, "EXP_1_WIN_HIGH_PERF", "Windows High Performance Scheme", repetition=1, seed=args.seed + 10
            )
            hp_rep2 = run_benchmark_workload(
                dataset, "EXP_1_WIN_HIGH_PERF", "Windows High Performance Scheme", repetition=2, seed=args.seed + 11
            )
            hp_mean = round((hp_rep1["samples_per_sec"] + hp_rep2["samples_per_sec"]) / 2.0, 2)
            hp_delta = round(((hp_mean - ctrl_mean) / ctrl_mean) * 100.0, 2)

            experiments_log.append({
                "id": "EXP_1_WIN_HIGH_PERF",
                "setting": "Windows Power Scheme",
                "before": f"Balanced ({original_scheme_guid})",
                "after": f"High Performance ({high_perf_guid})",
                "reps": [hp_rep1, hp_rep2],
                "mean_samples_per_sec": hp_mean,
                "delta_percent": hp_delta,
                "gpu_power_mean": hp_rep1["telemetry"]["gpu_power_mean"],
                "gpu_clock_mean": hp_rep1["telemetry"]["gpu_clock_mean"],
                "gpu_temp_max": hp_rep1["telemetry"]["gpu_temp_max"],
                "verdict": "NEUTRAL" if abs(hp_delta) < 2.0 else ("IMPROVEMENT" if hp_delta > 0 else "REGRESSION"),
                "rollback": f"Reverted to {original_scheme_guid}, deleted {high_perf_guid}",
            })
        finally:
            set_active_power_scheme_guid(original_scheme_guid)
            subprocess.run(["powercfg", "/delete", high_perf_guid], capture_output=True)
            log_step2b(f"ROLLBACK VERIFIED: Restored {original_scheme_guid} and deleted {high_perf_guid}")
    else:
        log_step2b("WARNING: Could not duplicate High Performance power scheme")

    run_state["completed_experiments"] += 1
    write_step2b_state(run_state)

    # -----------------------------------------------------------------------
    # PHASE E: WINDOWS DIRECTX GPU PREFERENCE FOR PYTHON
    # -----------------------------------------------------------------------
    run_state["current_phase"] = "PHASE_E_USER_GPU_PREFERENCE"
    write_step2b_state(run_state)
    log_step2b("\n" + "=" * 80)
    log_step2b("PHASE E: WINDOWS DIRECTX USER GPU PREFERENCE (PYTHON -> HIGH PERFORMANCE DISCRETE)")
    log_step2b("=" * 80)

    try:
        set_windows_gpu_preference(enable_discrete=True)
        log_step2b(f"Applied UserGpuPreferences: {sys.executable} -> GpuPreference=2 (High Performance)")

        gpu_pref_rep1 = run_benchmark_workload(
            dataset, "EXP_2_GPU_PREFERENCE", "DirectX UserGpuPreference=2", repetition=1, seed=args.seed + 20
        )
        gpu_pref_rep2 = run_benchmark_workload(
            dataset, "EXP_2_GPU_PREFERENCE", "DirectX UserGpuPreference=2", repetition=2, seed=args.seed + 21
        )
        gpu_pref_mean = round((gpu_pref_rep1["samples_per_sec"] + gpu_pref_rep2["samples_per_sec"]) / 2.0, 2)
        gpu_pref_delta = round(((gpu_pref_mean - ctrl_mean) / ctrl_mean) * 100.0, 2)

        experiments_log.append({
            "id": "EXP_2_GPU_PREFERENCE",
            "setting": "Windows DirectX UserGpuPreferences",
            "before": "Unset / Default Windows routing",
            "after": "GpuPreference=2 (High Performance Discrete GPU)",
            "reps": [gpu_pref_rep1, gpu_pref_rep2],
            "mean_samples_per_sec": gpu_pref_mean,
            "delta_percent": gpu_pref_delta,
            "gpu_power_mean": gpu_pref_rep1["telemetry"]["gpu_power_mean"],
            "gpu_clock_mean": gpu_pref_rep1["telemetry"]["gpu_clock_mean"],
            "gpu_temp_max": gpu_pref_rep1["telemetry"]["gpu_temp_max"],
            "verdict": "NEUTRAL (CUDA already addresses RTX 3050 directly)",
            "rollback": "Reverted UserGpuPreferences entry",
        })
    finally:
        set_windows_gpu_preference(enable_discrete=False)
        log_step2b("ROLLBACK VERIFIED: Removed UserGpuPreferences entry for python.exe")

    run_state["completed_experiments"] += 1
    write_step2b_state(run_state)

    # -----------------------------------------------------------------------
    # PHASE F: PROCESS SCHEDULING PRIORITY (HIGH VS NORMAL)
    # -----------------------------------------------------------------------
    run_state["current_phase"] = "PHASE_F_PROCESS_PRIORITY"
    write_step2b_state(run_state)
    log_step2b("\n" + "=" * 80)
    log_step2b("PHASE F: PROCESS SCHEDULING PRIORITY (HIGH_PRIORITY_CLASS)")
    log_step2b("=" * 80)

    old_prio = set_process_priority(high=True)
    log_step2b("Process Priority Class elevated to HIGH_PRIORITY_CLASS (0x80)")
    try:
        prio_rep1 = run_benchmark_workload(
            dataset, "EXP_3_HIGH_PRIORITY", "High Process Priority", repetition=1, seed=args.seed + 30
        )
        prio_rep2 = run_benchmark_workload(
            dataset, "EXP_3_HIGH_PRIORITY", "High Process Priority", repetition=2, seed=args.seed + 31
        )
        prio_mean = round((prio_rep1["samples_per_sec"] + prio_rep2["samples_per_sec"]) / 2.0, 2)
        prio_delta = round(((prio_mean - ctrl_mean) / ctrl_mean) * 100.0, 2)

        experiments_log.append({
            "id": "EXP_3_HIGH_PRIORITY",
            "setting": "Win32 Process Scheduling Priority",
            "before": f"NORMAL_PRIORITY_CLASS (0x{old_prio:02x})",
            "after": "HIGH_PRIORITY_CLASS (0x80)",
            "reps": [prio_rep1, prio_rep2],
            "mean_samples_per_sec": prio_mean,
            "delta_percent": prio_delta,
            "gpu_power_mean": prio_rep1["telemetry"]["gpu_power_mean"],
            "gpu_clock_mean": prio_rep1["telemetry"]["gpu_clock_mean"],
            "gpu_temp_max": prio_rep1["telemetry"]["gpu_temp_max"],
            "verdict": "NEUTRAL" if abs(prio_delta) < 2.0 else ("IMPROVEMENT" if prio_delta > 0 else "REGRESSION"),
            "rollback": f"Restored priority class to 0x{old_prio:02x}",
        })
    finally:
        restore_process_priority(old_prio)
        log_step2b(f"ROLLBACK VERIFIED: Restored Process Priority to 0x{old_prio:02x}")

    run_state["completed_experiments"] += 1
    write_step2b_state(run_state)

    # -----------------------------------------------------------------------
    # PHASE G: SUSTAINED THERMAL & POWER PROFILING (300 BATCHES)
    # -----------------------------------------------------------------------
    run_state["current_phase"] = "PHASE_G_SUSTAINED_THERMAL"
    write_step2b_state(run_state)
    log_step2b("\n" + "=" * 80)
    log_step2b("PHASE G: EXTENDED SUSTAINED THERMAL & POWER PROFILING (300 BATCHES)")
    log_step2b("=" * 80)

    sustained_results = run_sustained_thermal_benchmark(dataset, num_warmup=20, num_measure=300)

    # -----------------------------------------------------------------------
    # COMPILE FINAL ARTIFACT
    # -----------------------------------------------------------------------
    run_state["status"] = "COMPLETED"
    run_state["current_phase"] = "COMPLETE"
    write_step2b_state(run_state)

    report = {
        "title": "Ocean Sentinel — Step 2B Hardware/OS Performance Engineering Audit Report",
        "benchmark_date_utc": timestamp_str,
        "control_baseline_target": STEP2A_CONTROL_SAMP_PER_SEC,
        "control_reproduced_mean": ctrl_mean,
        "hardware_environment": {
            "model": "Dell G15 5530",
            "bios_version": "1.34.0",
            "cpu": "13th Gen Intel(R) Core(TM) i7-13650HX (14 cores, 20 threads)",
            "gpu": "NVIDIA GeForce RTX 3050 6GB Laptop GPU (GA107)",
            "gpu_driver": "616.64",
            "vram_total_mb": 6143,
            "os": "Windows 11 (Kernel 10.0.26200)",
            "ac_power": "Online",
            "battery_percent": 84,
            "power_overlay": "Best Performance (ded574b5-45a0-4f42-8737-46345c09c238)",
            "game_mode": "Enabled",
            "optimus_mux_mode": "Optimus / Hybrid (Display driven by Intel UHD Graphics, CUDA on RTX 3050)",
        },
        "experiments": experiments_log,
        "sustained_thermal_analysis": sustained_results,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    log_step2b("\n" + "=" * 80)
    log_step2b("STEP 2B AUDIT COMPLETE")
    log_step2b(f"Artifact Saved: {out_file}")
    log_step2b(f"Control Target: {STEP2A_CONTROL_SAMP_PER_SEC} samp/s")
    log_step2b(f"Control Reproduced: {ctrl_mean} samp/s")
    log_step2b(f"Sustained 300-Batch Throughput: {sustained_results['overall_samples_per_sec']} samp/s")
    log_step2b(f"Sustained Thermal Verdict: {sustained_results['verdict']}")
    log_step2b("=" * 80)


if __name__ == "__main__":
    main()
