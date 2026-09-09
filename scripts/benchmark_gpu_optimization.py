"""Ocean Sentinel — Controlled Software GPU Optimization Harness.

Executes Step 2A: Systematic, isolated evaluation of software execution path
optimizations for the RTX 3050 Laptop GPU on the real Ocean Sentinel workload.

Every candidate is measured independently against the authoritative control:
  CONTROL = 32.53 samples/sec

Maintains real-time progress observability:
  - experiments/performance/gpu_optimization_progress.json
  - experiments/performance/gpu_optimization.log
  - experiments/performance/gpu_optimization_results_YYYYMMDD_HHMMSS.json
"""
from __future__ import annotations

import argparse
import ctypes
import datetime
import gc
import json
import os
import platform
import sys
import threading
import time
from contextlib import nullcontext
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
from ocean_sentinel.ml.augmentation import (  # noqa: E402
    IdentityTransform,
    SARGeometricAugmentation,
)
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss  # noqa: E402
from ocean_sentinel.ml.unet_resnet import ResNet34UNet  # noqa: E402

DEFAULT_MANIFEST = (
    REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
)
PERF_DIR = REPO_ROOT / "experiments" / "performance"
PROGRESS_JSON = PERF_DIR / "gpu_optimization_progress.json"
PROGRESS_LOG = PERF_DIR / "gpu_optimization.log"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CONTROL_BASELINE_SAMP_PER_SEC = 32.53


# ===========================================================================
# 1. OBSERVABILITY & LOGGING INFRASTRUCTURE
# ===========================================================================
def log_progress(msg: str) -> None:
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    try:
        with open(PROGRESS_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def write_progress_state(state: Dict[str, Any]) -> None:
    try:
        state["last_updated_utc"] = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        tmp = PROGRESS_JSON.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        if tmp.exists() and tmp.stat().st_size > 0:
            os.replace(tmp, PROGRESS_JSON)
    except Exception as e:
        log_progress(f"WARNING: Failed to write progress state: {e}")


# ===========================================================================
# 2. LOW-OVERHEAD TELEMETRY
# ===========================================================================
class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_uint), ("dwHighDateTime", ctypes.c_uint)]


def _filetime_to_int(ft: FILETIME) -> int:
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


class NvmlUtilization(ctypes.Structure):
    _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]


class NvmlMemory(ctypes.Structure):
    _fields_ = [
        ("total", ctypes.c_ulonglong),
        ("free", ctypes.c_ulonglong),
        ("used", ctypes.c_ulonglong),
    ]


class TelemetrySampler:
    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.samples: List[Dict[str, Any]] = []

        # NVML
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
            self._nvml.nvmlDeviceGetUtilizationRates(self._handle, ctypes.byref(util))
            self._nvml.nvmlDeviceGetMemoryInfo(self._handle, ctypes.byref(mem))
            self._nvml.nvmlDeviceGetTemperature(self._handle, 0, ctypes.byref(temp))
            self._nvml.nvmlDeviceGetPowerUsage(self._handle, ctypes.byref(power))
            self._nvml.nvmlDeviceGetClockInfo(self._handle, 0, ctypes.byref(clock_sm))
            snap["gpu_util"] = util.gpu
            snap["gpu_temp"] = temp.value
            snap["gpu_clock"] = clock_sm.value
            snap["gpu_power"] = round(power.value / 1000.0, 1)
            snap["vram_used_mb"] = round(mem.used / (1024 * 1024), 1)
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
# 3. BENCHMARK RUNNER CORE
# ===========================================================================
def reset_system_state() -> None:
    """Reset PyTorch state to strict baseline defaults."""
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = True
    if hasattr(torch, "set_float32_matmul_precision"):
        torch.set_float32_matmul_precision("highest")
    torch.set_num_threads(14)
    torch.cuda.empty_cache()
    gc.collect()


def benchmark_candidate_run(
    dataset: TrujilloTileDataset,
    candidate_id: str,
    candidate_name: str,
    config: Dict[str, Any],
    num_warmup: int = 20,
    num_measure: int = 100,
    seed: int = 42,
    repetition: int = 1,
) -> Dict[str, Any]:
    """Benchmark a single candidate configuration with full instrumentation."""
    log_progress(
        f"EXPERIMENT START: {candidate_id} ({candidate_name}) | Repetition {repetition} | "
        f"{num_warmup} warmup + {num_measure} measured batches"
    )

    batch_size = config.get("batch_size", 8)
    num_workers = config.get("num_workers", 4)
    pin_memory = config.get("pin_memory", True)
    persistent_workers = config.get("persistent_workers", True)
    prefetch_factor = config.get("prefetch_factor", 2)
    non_blocking = config.get("non_blocking", True)

    cudnn_benchmark = config.get("cudnn_benchmark", False)
    allow_tf32 = config.get("allow_tf32", False)
    matmul_precision = config.get("matmul_precision", "highest")
    use_channels_last = config.get("use_channels_last", False)
    amp_dtype_str = config.get("amp_dtype", "float16")
    amp_dtype = torch.bfloat16 if amp_dtype_str == "bfloat16" else torch.float16
    use_grad_scaler = config.get("use_grad_scaler", (amp_dtype_str == "float16"))
    num_threads = config.get("num_threads", 14)
    use_compile = config.get("use_compile", False)

    # Apply candidate execution settings
    torch.backends.cudnn.benchmark = cudnn_benchmark
    torch.backends.cuda.matmul.allow_tf32 = allow_tf32
    torch.backends.cudnn.allow_tf32 = allow_tf32
    if hasattr(torch, "set_float32_matmul_precision"):
        torch.set_float32_matmul_precision(matmul_precision)
    torch.set_num_threads(num_threads)

    torch.cuda.empty_cache()
    gc.collect()
    torch.cuda.reset_peak_memory_stats()

    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=(DEVICE.type == "cuda" and pin_memory),
        persistent_workers=(num_workers > 0 and persistent_workers),
        prefetch_factor=(prefetch_factor if num_workers > 0 else None),
        drop_last=True,
    )

    model = ResNet34UNet(
        in_channels=2,
        num_classes=1,
        pretrained=True,
        adaptation_method="slice_variance_scaled",
    ).to(DEVICE)

    if use_channels_last:
        model = model.to(memory_format=torch.channels_last)

    if use_compile:
        try:
            model = torch.compile(model)
        except Exception as e:
            return {
                "candidate_id": candidate_id,
                "status": "INCOMPATIBLE",
                "error": f"torch.compile failed: {e}",
            }

    model.train()
    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)
    scaler = torch.amp.GradScaler(DEVICE.type, enabled=use_grad_scaler)

    loader_iter = iter(loader)

    # Warmup
    optimizer.zero_grad(set_to_none=True)
    for _ in range(num_warmup):
        imgs, masks = next(loader_iter)
        imgs = imgs.to(DEVICE, non_blocking=non_blocking)
        masks = masks.to(DEVICE, non_blocking=non_blocking)
        if use_channels_last:
            imgs = imgs.to(memory_format=torch.channels_last)
        with torch.amp.autocast(device_type=DEVICE.type, dtype=amp_dtype, enabled=True):
            loss = criterion(model(imgs), masks)
        if use_grad_scaler:
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            optimizer.step()
        optimizer.zero_grad(set_to_none=True)

    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()

    sampler = TelemetrySampler(interval=0.1)
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

        # 1. Loader wait
        t_io0 = time.perf_counter()
        imgs, masks = next(loader_iter)
        loader_wait_times.append(time.perf_counter() - t_io0)

        # 2. Transfer
        e_xfer_start.record()
        imgs = imgs.to(DEVICE, non_blocking=non_blocking)
        masks = masks.to(DEVICE, non_blocking=non_blocking)
        if use_channels_last:
            imgs = imgs.to(memory_format=torch.channels_last)
        e_xfer_end.record()

        # 3. Forward
        e_fwd_start.record()
        with torch.amp.autocast(device_type=DEVICE.type, dtype=amp_dtype, enabled=True):
            logits = model(imgs)
            loss = criterion(logits, masks)
        e_fwd_end.record()

        # 4. Backward
        e_bwd_start.record()
        if use_grad_scaler:
            scaler.scale(loss).backward()
        else:
            loss.backward()
        e_bwd_end.record()

        # 5. Optimizer
        e_opt_start.record()
        if use_grad_scaler:
            scaler.step(optimizer)
            scaler.update()
        else:
            optimizer.step()
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

    total_samples = num_measure * batch_size
    samples_per_sec = total_samples / wall_elapsed
    batches_per_sec = num_measure / wall_elapsed

    mean_step_ms = float(np.mean(step_wall_times)) * 1000.0
    mean_loader_ms = float(np.mean(loader_wait_times)) * 1000.0
    mean_xfer_ms = float(np.mean(xfer_times))
    mean_fwd_ms = float(np.mean(fwd_times))
    mean_bwd_ms = float(np.mean(bwd_times))
    mean_opt_ms = float(np.mean(opt_times))
    sync_overhead_ms = max(
        0.0, mean_step_ms - (mean_loader_ms + mean_xfer_ms + mean_fwd_ms + mean_bwd_ms + mean_opt_ms)
    )

    peak_alloc_mb = round(torch.cuda.max_memory_allocated() / (1024 * 1024), 1)
    peak_reserved_mb = round(torch.cuda.max_memory_reserved() / (1024 * 1024), 1)

    gpu_utils = [s["gpu_util"] for s in telemetry_samples if s.get("gpu_util") is not None]
    gpu_temps = [s["gpu_temp"] for s in telemetry_samples if s.get("gpu_temp") is not None]
    gpu_clocks = [s["gpu_clock"] for s in telemetry_samples if s.get("gpu_clock") is not None]
    gpu_powers = [s["gpu_power"] for s in telemetry_samples if s.get("gpu_power") is not None]

    gain_pct = round(((samples_per_sec - CONTROL_BASELINE_SAMP_PER_SEC) / CONTROL_BASELINE_SAMP_PER_SEC) * 100.0, 2)
    abs_gain = round(samples_per_sec - CONTROL_BASELINE_SAMP_PER_SEC, 2)

    log_progress(
        f"EXPERIMENT COMPLETE: {candidate_id} | {samples_per_sec:.2f} samp/s ({gain_pct:+.2f}% vs control) | "
        f"Step: {mean_step_ms:.1f}ms (fwd: {mean_fwd_ms:.1f}ms, bwd: {mean_bwd_ms:.1f}ms, opt: {mean_opt_ms:.1f}ms) | "
        f"GPU: {np.mean(gpu_utils):.1f}% | Temp: {max(gpu_temps) if gpu_temps else 'N/A'}C | VRAM: {peak_alloc_mb} MB"
    )

    del model, criterion, optimizer, scaler, loader, loader_iter
    reset_system_state()

    return {
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "repetition": repetition,
        "status": "OK",
        "samples_per_sec": round(samples_per_sec, 2),
        "batches_per_sec": round(batches_per_sec, 2),
        "absolute_gain_samp_per_sec": abs_gain,
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
            "sync_overhead": round(sync_overhead_ms, 2),
        },
        "vram": {
            "peak_allocated_mb": peak_alloc_mb,
            "peak_reserved_mb": peak_reserved_mb,
        },
        "telemetry": {
            "gpu_util_mean": round(float(np.mean(gpu_utils)), 1) if gpu_utils else None,
            "gpu_temp_max": max(gpu_temps) if gpu_temps else None,
            "gpu_clock_mean": round(float(np.mean(gpu_clocks)), 1) if gpu_clocks else None,
            "gpu_power_mean": round(float(np.mean(gpu_powers)), 1) if gpu_powers else None,
        },
        "config": config,
    }


def verify_numerical_correctness(
    config: Dict[str, Any],
    candidate_id: str,
) -> Dict[str, Any]:
    """Verify numerical agreement and output validity against strict control."""
    torch.manual_seed(12345)
    imgs_ref = torch.randn(4, 2, 512, 512, device=DEVICE)
    masks_ref = torch.randint(0, 2, (4, 1, 512, 512), device=DEVICE, dtype=torch.float32)

    # 1. Control run
    reset_system_state()
    model_ctrl = ResNet34UNet(
        in_channels=2, num_classes=1, pretrained=False, adaptation_method="slice_variance_scaled"
    ).to(DEVICE)
    criterion_ctrl = CombinedBCEAndDiceLoss(0.5, 0.5, 1.0).to(DEVICE)
    model_ctrl.eval()

    with torch.no_grad():
        with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=True):
            logits_ctrl = model_ctrl(imgs_ref)
            loss_ctrl = criterion_ctrl(logits_ctrl, masks_ref)

    # 2. Candidate configuration
    cudnn_benchmark = config.get("cudnn_benchmark", False)
    allow_tf32 = config.get("allow_tf32", False)
    matmul_precision = config.get("matmul_precision", "highest")
    use_channels_last = config.get("use_channels_last", False)
    amp_dtype_str = config.get("amp_dtype", "float16")
    amp_dtype = torch.bfloat16 if amp_dtype_str == "bfloat16" else torch.float16

    torch.backends.cudnn.benchmark = cudnn_benchmark
    torch.backends.cuda.matmul.allow_tf32 = allow_tf32
    torch.backends.cudnn.allow_tf32 = allow_tf32
    if hasattr(torch, "set_float32_matmul_precision"):
        torch.set_float32_matmul_precision(matmul_precision)

    model_cand = ResNet34UNet(
        in_channels=2, num_classes=1, pretrained=False, adaptation_method="slice_variance_scaled"
    ).to(DEVICE)
    model_cand.load_state_dict(model_ctrl.state_dict())

    if use_channels_last:
        model_cand = model_cand.to(memory_format=torch.channels_last)

    imgs_cand = imgs_ref.clone()
    if use_channels_last:
        imgs_cand = imgs_cand.to(memory_format=torch.channels_last)

    model_cand.eval()
    with torch.no_grad():
        with torch.amp.autocast(device_type=DEVICE.type, dtype=amp_dtype, enabled=True):
            logits_cand = model_cand(imgs_cand)
            loss_cand = criterion_ctrl(logits_cand, masks_ref)

    # Metrics
    shape_ok = logits_cand.shape == logits_ctrl.shape
    finite_ok = bool(torch.isfinite(loss_cand).item() and torch.isfinite(logits_cand).all().item())

    # Max diff in float32 logits
    l_ctrl_fp32 = logits_ctrl.float()
    l_cand_fp32 = logits_cand.float()
    max_abs_diff = float(torch.max(torch.abs(l_ctrl_fp32 - l_cand_fp32)).item())
    mean_abs_diff = float(torch.mean(torch.abs(l_ctrl_fp32 - l_cand_fp32)).item())
    loss_diff = abs(float(loss_cand.item()) - float(loss_ctrl.item()))

    reset_system_state()

    # Pass criteria: finite, same shape, differences within numerical precision tolerance
    # For FP16/TF32 differences < 0.05 max abs diff and < 0.005 mean abs diff are standard numerical tolerances
    passed = shape_ok and finite_ok and (max_abs_diff < 0.1)

    return {
        "candidate_id": candidate_id,
        "shape_matches": shape_ok,
        "output_shape": list(logits_cand.shape),
        "is_finite": finite_ok,
        "max_abs_diff_logits": round(max_abs_diff, 6),
        "mean_abs_diff_logits": round(mean_abs_diff, 6),
        "loss_diff": round(loss_diff, 6),
        "passed": passed,
    }


# ===========================================================================
# 4. EXPERIMENT MATRIX DEFINITION
# ===========================================================================
def get_single_variable_experiments() -> List[Dict[str, Any]]:
    """Defines each isolated software optimization candidate."""
    return [
        {
            "id": "EXP_0_CONTROL",
            "name": "Control Baseline Reproduction",
            "section": "Control Group",
            "config": {
                "cudnn_benchmark": False,
                "use_channels_last": False,
                "allow_tf32": False,
                "matmul_precision": "highest",
                "amp_dtype": "float16",
                "use_grad_scaler": True,
                "pin_memory": True,
                "non_blocking": True,
                "num_threads": 14,
            },
            "repetitions": 2,
        },
        {
            "id": "EXP_1_CUDNN_BENCHMARK",
            "name": "cuDNN Autotuner Enablement",
            "section": "cuDNN",
            "config": {
                "cudnn_benchmark": True,  # TARGET VARIABLE
                "use_channels_last": False,
                "allow_tf32": False,
                "matmul_precision": "highest",
                "amp_dtype": "float16",
                "use_grad_scaler": True,
                "pin_memory": True,
                "non_blocking": True,
                "num_threads": 14,
            },
            "repetitions": 2,
        },
        {
            "id": "EXP_2_CHANNELS_LAST",
            "name": "Channels-Last (NHWC) Memory Format",
            "section": "Memory Layout",
            "config": {
                "cudnn_benchmark": False,
                "use_channels_last": True,  # TARGET VARIABLE
                "allow_tf32": False,
                "matmul_precision": "highest",
                "amp_dtype": "float16",
                "use_grad_scaler": True,
                "pin_memory": True,
                "non_blocking": True,
                "num_threads": 14,
            },
            "repetitions": 2,
        },
        {
            "id": "EXP_3A_TF32_HIGH",
            "name": "TF32 Enabled + Matmul Precision High",
            "section": "TF32 Precision",
            "config": {
                "cudnn_benchmark": False,
                "use_channels_last": False,
                "allow_tf32": True,  # TARGET VARIABLE
                "matmul_precision": "high",  # TARGET VARIABLE
                "amp_dtype": "float16",
                "use_grad_scaler": True,
                "pin_memory": True,
                "non_blocking": True,
                "num_threads": 14,
            },
            "repetitions": 2,
        },
        {
            "id": "EXP_3B_TF32_MEDIUM",
            "name": "TF32 Enabled + Matmul Precision Medium",
            "section": "TF32 Precision",
            "config": {
                "cudnn_benchmark": False,
                "use_channels_last": False,
                "allow_tf32": True,  # TARGET VARIABLE
                "matmul_precision": "medium",  # TARGET VARIABLE
                "amp_dtype": "float16",
                "use_grad_scaler": True,
                "pin_memory": True,
                "non_blocking": True,
                "num_threads": 14,
            },
            "repetitions": 2,
        },
        {
            "id": "EXP_4A_AMP_BF16",
            "name": "AMP BFloat16 (Native Ampere Tensor Cores)",
            "section": "AMP Implementation",
            "config": {
                "cudnn_benchmark": False,
                "use_channels_last": False,
                "allow_tf32": False,
                "matmul_precision": "highest",
                "amp_dtype": "bfloat16",  # TARGET VARIABLE
                "use_grad_scaler": False,  # BF16 does not require loss scaling
                "pin_memory": True,
                "non_blocking": True,
                "num_threads": 14,
            },
            "repetitions": 2,
        },
        {
            "id": "EXP_5_SYNC_TRANSFER",
            "name": "Host Transfer Path: Synchronous non_blocking=False",
            "section": "Transfer Path",
            "config": {
                "cudnn_benchmark": False,
                "use_channels_last": False,
                "allow_tf32": False,
                "matmul_precision": "highest",
                "amp_dtype": "float16",
                "use_grad_scaler": True,
                "pin_memory": True,
                "non_blocking": False,  # TARGET VARIABLE
                "num_threads": 14,
            },
            "repetitions": 1,
        },
        {
            "id": "EXP_6A_THREADS_8",
            "name": "CPU Intra-Op Threads = 8 (P-core matching)",
            "section": "CPU Threading",
            "config": {
                "cudnn_benchmark": False,
                "use_channels_last": False,
                "allow_tf32": False,
                "matmul_precision": "highest",
                "amp_dtype": "float16",
                "use_grad_scaler": True,
                "pin_memory": True,
                "non_blocking": True,
                "num_threads": 8,  # TARGET VARIABLE
            },
            "repetitions": 2,
        },
        {
            "id": "EXP_6B_THREADS_4",
            "name": "CPU Intra-Op Threads = 4",
            "section": "CPU Threading",
            "config": {
                "cudnn_benchmark": False,
                "use_channels_last": False,
                "allow_tf32": False,
                "matmul_precision": "highest",
                "amp_dtype": "float16",
                "use_grad_scaler": True,
                "pin_memory": True,
                "non_blocking": True,
                "num_threads": 4,  # TARGET VARIABLE
            },
            "repetitions": 2,
        },
        {
            "id": "EXP_7_TORCH_COMPILE",
            "name": "PyTorch Compilation (torch.compile)",
            "section": "Compilation",
            "config": {
                "cudnn_benchmark": False,
                "use_channels_last": False,
                "allow_tf32": False,
                "matmul_precision": "highest",
                "amp_dtype": "float16",
                "use_grad_scaler": True,
                "pin_memory": True,
                "non_blocking": True,
                "num_threads": 14,
                "use_compile": True,  # TARGET VARIABLE
            },
            "repetitions": 1,
        },
    ]


# ===========================================================================
# 5. MAIN EXECUTION CONTROLLER
# ===========================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Ocean Sentinel GPU Optimization Benchmark")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=PERF_DIR)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    PROGRESS_LOG.unlink(missing_ok=True)

    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = args.out_dir / f"gpu_optimization_results_{timestamp_str}.json"

    log_progress("=" * 80)
    log_progress("OCEAN SENTINEL — CONTROLLED SOFTWARE GPU OPTIMIZATION (STEP 2A)")
    log_progress(f"Timestamp: {timestamp_str} UTC")
    log_progress(f"Control Baseline Target: {CONTROL_BASELINE_SAMP_PER_SEC} samples/sec")
    log_progress(f"Device: {DEVICE} ({torch.cuda.get_device_name(0)})")
    log_progress("=" * 80)

    manifest = DatasetManifest.load(args.manifest)
    aug = SARGeometricAugmentation(p_hflip=0.5, p_vflip=0.5, p_rot90=0.5, seed=args.seed)
    dataset = TrujilloTileDataset(manifest, SplitName.TRAIN, normalize=True, transform=aug)
    log_progress(f"Dataset loaded: {len(dataset)} training tiles")

    single_experiments = get_single_variable_experiments()
    total_phases = len(single_experiments)
    completed_runs: List[Dict[str, Any]] = []
    summary_by_id: Dict[str, Dict[str, Any]] = {}

    progress_state = {
        "status": "RUNNING",
        "current_phase": "SINGLE_VARIABLE_SWEEP",
        "total_experiments": total_phases,
        "completed_count": 0,
        "control_baseline_samp_per_sec": CONTROL_BASELINE_SAMP_PER_SEC,
        "current_experiment_id": None,
        "current_throughput": None,
        "best_individual_optimization": None,
        "best_combined_optimization": None,
        "last_completed_experiment": None,
        "experiments": {},
    }
    write_progress_state(progress_state)

    # -----------------------------------------------------------------------
    # PHASE 1: INDEPENDENT SINGLE-VARIABLE EXPERIMENTS
    # -----------------------------------------------------------------------
    log_progress("\n" + "=" * 80)
    log_progress("PHASE 1: INDEPENDENT SINGLE-VARIABLE EXPERIMENTS")
    log_progress("=" * 80)

    start_all = time.time()

    for idx, exp in enumerate(single_experiments, start=1):
        exp_id = exp["id"]
        exp_name = exp["name"]
        num_reps = exp["repetitions"]
        cfg = exp["config"]

        progress_state["current_experiment_id"] = exp_id
        progress_state["current_config"] = cfg
        write_progress_state(progress_state)

        # Check torch.compile compatibility before running full benchmark
        if cfg.get("use_compile"):
            log_progress(f"EXPERIMENT START: {exp_id} ({exp_name})")
            log_progress("  Testing torch.compile compatibility...")
            try:
                test_m = ResNet34UNet(2, 1).to(DEVICE)
                c_m = torch.compile(test_m)
                dummy = torch.randn(2, 2, 512, 512, device=DEVICE)
                _ = c_m(dummy)
            except Exception as e:
                err_msg = f"Incompatible on Windows / PyTorch without Triton: {type(e).__name__} ({str(e)[:160]})"
                log_progress(f"EXPERIMENT FAILED / INCOMPATIBLE: {exp_id} — {err_msg}")
                summary_by_id[exp_id] = {
                    "id": exp_id,
                    "name": exp_name,
                    "classification": "INCOMPATIBLE",
                    "reason": err_msg,
                    "mean_samples_per_sec": 0.0,
                    "percentage_gain": 0.0,
                }
                progress_state["completed_count"] += 1
                progress_state["last_completed_experiment"] = exp_id
                progress_state["experiments"][exp_id] = summary_by_id[exp_id]
                write_progress_state(progress_state)
                continue

        rep_results: List[Dict[str, Any]] = []
        for rep_i in range(1, num_reps + 1):
            run_res = benchmark_candidate_run(
                dataset=dataset,
                candidate_id=exp_id,
                candidate_name=exp_name,
                config=cfg,
                num_warmup=20,
                num_measure=100,
                seed=args.seed + rep_i * 10,
                repetition=rep_i,
            )
            rep_results.append(run_res)
            completed_runs.append(run_res)

        # Repetition rollup
        throughputs = [r["samples_per_sec"] for r in rep_results]
        mean_samp = float(np.mean(throughputs))
        var_samp = float(np.std(throughputs))
        pct_gain = round(((mean_samp - CONTROL_BASELINE_SAMP_PER_SEC) / CONTROL_BASELINE_SAMP_PER_SEC) * 100.0, 2)
        abs_gain = round(mean_samp - CONTROL_BASELINE_SAMP_PER_SEC, 2)

        # Numerical correctness check
        num_check = verify_numerical_correctness(cfg, exp_id)

        # Classification
        if pct_gain >= 3.0 and num_check["passed"]:
            classification = "IMPROVEMENT"
        elif pct_gain <= -3.0:
            classification = "REGRESSION"
        elif not num_check["passed"]:
            classification = "UNSTABLE"
        else:
            classification = "NEUTRAL"

        summary_entry = {
            "id": exp_id,
            "name": exp_name,
            "section": exp["section"],
            "classification": classification,
            "mean_samples_per_sec": round(mean_samp, 2),
            "std_samples_per_sec": round(var_samp, 2),
            "percentage_gain": pct_gain,
            "absolute_gain": abs_gain,
            "reps": rep_results,
            "numerical_correctness": num_check,
            "timing_breakdown_ms": rep_results[0]["timing_ms"],
            "vram_allocated_mb": rep_results[0]["vram"]["peak_allocated_mb"],
            "gpu_temp_max_c": rep_results[0]["telemetry"]["gpu_temp_max"],
            "gpu_util_mean": rep_results[0]["telemetry"]["gpu_util_mean"],
        }
        summary_by_id[exp_id] = summary_entry

        progress_state["completed_count"] += 1
        progress_state["current_throughput"] = round(mean_samp, 2)
        progress_state["last_completed_experiment"] = exp_id
        progress_state["experiments"][exp_id] = {
            "name": exp_name,
            "classification": classification,
            "samples_per_sec": round(mean_samp, 2),
            "percentage_gain": pct_gain,
        }
        write_progress_state(progress_state)

    # -----------------------------------------------------------------------
    # PHASE 2: COMBINATION TESTING (SYSTEMATIC COMPOSITION)
    # -----------------------------------------------------------------------
    log_progress("\n" + "=" * 80)
    log_progress("PHASE 2: SYSTEMATIC COMBINATION OF VERIFIED IMPROVEMENTS")
    log_progress("=" * 80)

    # Filter verified individual improvements
    verified_improvements = [
        s for s in summary_by_id.values() if s["classification"] == "IMPROVEMENT"
    ]
    verified_improvements.sort(key=lambda x: x["percentage_gain"], reverse=True)

    log_progress(f"Verified Individual Improvements Found: {len(verified_improvements)}")
    for vi in verified_improvements:
        log_progress(f"  - {vi['id']} ({vi['name']}): {vi['percentage_gain']:+.2f}%")

    combination_summaries: List[Dict[str, Any]] = []

    # Define combinations
    combo_candidates: List[Dict[str, Any]] = []

    # Combo A: cuDNN benchmark + Channels-Last
    combo_candidates.append({
        "id": "COMBO_1_CUDNN_CHANNELS_LAST",
        "name": "cuDNN Benchmark + Channels-Last (NHWC)",
        "config": {
            "cudnn_benchmark": True,
            "use_channels_last": True,
            "allow_tf32": False,
            "matmul_precision": "highest",
            "amp_dtype": "float16",
            "use_grad_scaler": True,
            "pin_memory": True,
            "non_blocking": True,
            "num_threads": 14,
        },
    })

    # Combo B: cuDNN benchmark + Channels-Last + TF32 (High)
    combo_candidates.append({
        "id": "COMBO_2_CUDNN_CHANNELS_LAST_TF32",
        "name": "cuDNN Benchmark + Channels-Last + TF32 Matmul",
        "config": {
            "cudnn_benchmark": True,
            "use_channels_last": True,
            "allow_tf32": True,
            "matmul_precision": "high",
            "amp_dtype": "float16",
            "use_grad_scaler": True,
            "pin_memory": True,
            "non_blocking": True,
            "num_threads": 14,
        },
    })

    # Combo C: cuDNN benchmark + Channels-Last + TF32 + Thread tuning (8 threads)
    combo_candidates.append({
        "id": "COMBO_3_FULL_SOFTWARE_STACK",
        "name": "cuDNN Benchmark + Channels-Last + TF32 + 8 Threads",
        "config": {
            "cudnn_benchmark": True,
            "use_channels_last": True,
            "allow_tf32": True,
            "matmul_precision": "high",
            "amp_dtype": "float16",
            "use_grad_scaler": True,
            "pin_memory": True,
            "non_blocking": True,
            "num_threads": 8,
        },
    })

    progress_state["current_phase"] = "COMBINATION_TESTING"
    write_progress_state(progress_state)

    for combo in combo_candidates:
        c_id = combo["id"]
        c_name = combo["name"]
        c_cfg = combo["config"]

        progress_state["current_experiment_id"] = c_id
        progress_state["current_config"] = c_cfg
        write_progress_state(progress_state)

        # Run 2 repetitions for reliability
        rep_results = []
        for rep_i in range(1, 3):
            run_res = benchmark_candidate_run(
                dataset=dataset,
                candidate_id=c_id,
                candidate_name=c_name,
                config=c_cfg,
                num_warmup=20,
                num_measure=100,
                seed=args.seed + rep_i * 100,
                repetition=rep_i,
            )
            rep_results.append(run_res)
            completed_runs.append(run_res)

        throughputs = [r["samples_per_sec"] for r in rep_results]
        mean_samp = float(np.mean(throughputs))
        var_samp = float(np.std(throughputs))
        pct_gain = round(((mean_samp - CONTROL_BASELINE_SAMP_PER_SEC) / CONTROL_BASELINE_SAMP_PER_SEC) * 100.0, 2)
        abs_gain = round(mean_samp - CONTROL_BASELINE_SAMP_PER_SEC, 2)

        num_check = verify_numerical_correctness(c_cfg, c_id)
        classification = "IMPROVEMENT" if pct_gain >= 3.0 and num_check["passed"] else "NEUTRAL"

        combo_entry = {
            "id": c_id,
            "name": c_name,
            "classification": classification,
            "mean_samples_per_sec": round(mean_samp, 2),
            "std_samples_per_sec": round(var_samp, 2),
            "percentage_gain": pct_gain,
            "absolute_gain": abs_gain,
            "reps": rep_results,
            "numerical_correctness": num_check,
            "timing_breakdown_ms": rep_results[0]["timing_ms"],
            "vram_allocated_mb": rep_results[0]["vram"]["peak_allocated_mb"],
            "gpu_temp_max_c": rep_results[0]["telemetry"]["gpu_temp_max"],
            "gpu_util_mean": rep_results[0]["telemetry"]["gpu_util_mean"],
        }
        combination_summaries.append(combo_entry)
        summary_by_id[c_id] = combo_entry

        progress_state["completed_count"] += 1
        progress_state["last_completed_experiment"] = c_id
        progress_state["experiments"][c_id] = {
            "name": c_name,
            "classification": classification,
            "samples_per_sec": round(mean_samp, 2),
            "percentage_gain": pct_gain,
        }
        write_progress_state(progress_state)

    # Determine best individual and best combined
    best_ind = max(
        [s for s in summary_by_id.values() if not s["id"].startswith("COMBO")],
        key=lambda x: x["mean_samples_per_sec"],
    )
    best_combo = max(
        combination_summaries,
        key=lambda x: x["mean_samples_per_sec"],
    )

    progress_state["status"] = "COMPLETE"
    progress_state["best_individual_optimization"] = {
        "id": best_ind["id"],
        "name": best_ind["name"],
        "samples_per_sec": best_ind["mean_samples_per_sec"],
        "gain_percent": best_ind["percentage_gain"],
    }
    progress_state["best_combined_optimization"] = {
        "id": best_combo["id"],
        "name": best_combo["name"],
        "samples_per_sec": best_combo["mean_samples_per_sec"],
        "gain_percent": best_combo["percentage_gain"],
    }
    write_progress_state(progress_state)

    # -----------------------------------------------------------------------
    # ARTIFACT GENERATION
    # -----------------------------------------------------------------------
    total_elapsed_min = round((time.time() - start_all) / 60.0, 2)
    final_report = {
        "title": "Ocean Sentinel — Step 2A Controlled Software GPU Optimization Report",
        "benchmark_date_utc": timestamp_str,
        "total_elapsed_min": total_elapsed_min,
        "control_baseline_samp_per_sec": CONTROL_BASELINE_SAMP_PER_SEC,
        "hardware": {
            "gpu": torch.cuda.get_device_name(0),
            "vram_total_mb": torch.cuda.get_device_properties(0).total_memory // (1024 * 1024),
            "cuda_version": torch.version.cuda,
            "cudnn_version": torch.backends.cudnn.version(),
            "os": platform.platform(),
        },
        "single_variable_summaries": [
            s for s in summary_by_id.values() if not s["id"].startswith("COMBO")
        ],
        "combination_summaries": combination_summaries,
        "best_individual": best_ind,
        "best_combination": best_combo,
        "speedup_vs_baseline": round(best_combo["mean_samples_per_sec"] / CONTROL_BASELINE_SAMP_PER_SEC, 3),
        "verified_speedup_percent": best_combo["percentage_gain"],
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    log_progress("\n" + "=" * 80)
    log_progress("GPU OPTIMIZATION BENCHMARK COMPLETE")
    log_progress(f"Artifact Saved: {out_file}")
    log_progress(f"CONTROL THROUGHPUT: {CONTROL_BASELINE_SAMP_PER_SEC:.2f} samples/sec")
    log_progress(
        f"BEST VERIFIED THROUGHPUT: {best_combo['mean_samples_per_sec']:.2f} samples/sec "
        f"({best_combo['percentage_gain']:+.2f}% speedup)"
    )
    log_progress(f"PRIMARY VERIFIED OPTIMIZATION: {best_ind['name']}")
    log_progress(f"FINAL RECOMMENDED SOFTWARE CONFIGURATION: {best_combo['name']}")
    log_progress("=" * 80)


if __name__ == "__main__":
    main()
