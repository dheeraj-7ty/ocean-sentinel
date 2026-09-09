"""Ocean Sentinel — Step 2C-B: Selective Decoder Layout Optimization Benchmark.

Controlled Prototype Benchmark:
Evaluates whether selective decoder memory-layout interventions can reduce
the NCHW <-> NHWC conversion overhead (~57 ms/batch) in ResNet34UNet while
preserving model semantics, numerical correctness, and training stability.

Strict Safety:
- NO modifications to production code, manifests, weights, or checkpoints.
- EXP01 artifact immutability verified before and after.
- Full observability via JSON and log.
"""
from __future__ import annotations

import copy
import datetime
import gc
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss
from ocean_sentinel.ml.unet_resnet import ResNet34UNet, DecoderBlock, DoubleConv

PERF_DIR = REPO_ROOT / "experiments" / "performance"
PROGRESS_JSON = PERF_DIR / "gpu_step2c_b_progress.json"
PROGRESS_LOG = PERF_DIR / "gpu_step2c_b.log"
RUN_STATE_JSON = PERF_DIR / "gpu_step2c_b_run_state.json"

MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

EXP01_FILES = [
    REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt",
    REPO_ROOT / "experiments" / "exp01_baseline" / "final_model.pt",
    REPO_ROOT / "experiments" / "exp01_baseline" / "latest_checkpoint.pt",
    REPO_ROOT / "experiments" / "exp01_baseline" / "history.json",
    REPO_ROOT / "experiments" / "exp01_baseline" / "config.json",
    REPO_ROOT / "experiments" / "exp01_baseline" / "run_state.json",
]

EXPECTED_EXP01_HASHES = {
    "experiments/exp01_baseline/best_model.pt": "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699",
    "experiments/exp01_baseline/final_model.pt": "2E4C0881DF2F16810C4494A4071EAB320D12418151CC5F74651E91FE1F0A41AA",
    "experiments/exp01_baseline/latest_checkpoint.pt": "2F8F7718D687FF1621F4D92FD7190AE3D582AC67CCD2A529F72E1088A139AA6A",
    "experiments/exp01_baseline/history.json": "E2B5EB5229E2529E1659E77D285E93275015F58DEDCA5AF1F539E45544D5FCBA",
    "experiments/exp01_baseline/config.json": "2DF14570974288E0E6985393E139F3E23F4DD02A02C008C8F1CF00060D9A10EA",
    "experiments/exp01_baseline/run_state.json": "F8EC3B5D461F13C8B4673E038E90CE6385E57F0B39EDD5B73156AAAD2DD0178C",
}


def log_msg(msg: str) -> None:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        PERF_DIR.mkdir(parents=True, exist_ok=True)
        with open(PROGRESS_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def get_gpu_telemetry() -> Dict[str, Any]:
    telemetry = {
        "temperature_c": None,
        "clock_mhz": None,
        "power_w": None,
        "utilization_pct": None,
        "vram_allocated_mb": round(torch.cuda.memory_allocated() / (1024 * 1024), 2) if torch.cuda.is_available() else 0.0,
        "vram_reserved_mb": round(torch.cuda.memory_reserved() / (1024 * 1024), 2) if torch.cuda.is_available() else 0.0,
        "vram_max_allocated_mb": round(torch.cuda.max_memory_allocated() / (1024 * 1024), 2) if torch.cuda.is_available() else 0.0,
    }
    try:
        cmd = ["nvidia-smi", "--query-gpu=temperature.gpu,clocks.current.graphics,power.draw,utilization.gpu", "--format=csv,noheader,nounits"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 4:
                telemetry["temperature_c"] = float(parts[0])
                telemetry["clock_mhz"] = float(parts[1])
                telemetry["power_w"] = float(parts[2])
                telemetry["utilization_pct"] = float(parts[3])
    except Exception:
        pass
    return telemetry


def update_state(
    phase: str,
    experiment_id: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    start_time: Optional[float] = None,
) -> None:
    now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    elapsed_sec = (time.time() - start_time) if start_time else 0.0
    telem = get_gpu_telemetry()
    state: Dict[str, Any] = {
        "task": "STEP_2C_B_DECODER_LAYOUT_OPTIMIZATION",
        "phase": phase,
        "experiment_id": experiment_id,
        "status": status,
        "elapsed_sec": round(elapsed_sec, 2),
        "last_updated_utc": now_ts,
        "device": str(DEVICE),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "gpu_telemetry": telem,
        "details": details or {},
    }
    try:
        PERF_DIR.mkdir(parents=True, exist_ok=True)
        tmp = RUN_STATE_JSON.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        if tmp.exists() and tmp.stat().st_size > 0:
            os.replace(tmp, RUN_STATE_JSON)

        tmp_p = PROGRESS_JSON.with_suffix(".tmp")
        tmp_p.write_text(json.dumps(state, indent=2), encoding="utf-8")
        if tmp_p.exists() and tmp_p.stat().st_size > 0:
            os.replace(tmp_p, PROGRESS_JSON)
    except Exception as e:
        log_msg(f"WARNING: Failed to write state: {e}")


def verify_exp01(tag: str = "CHECK") -> Dict[str, str]:
    log_msg(f"Verifying EXP01 artifact immutability [{tag}]...")
    current_hashes = {}
    for p in EXP01_FILES:
        rel_key = str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        if not p.exists():
            raise FileNotFoundError(f"EXP01 file missing: {p}")
        h = hashlib.sha256(p.read_bytes()).hexdigest().upper()
        current_hashes[rel_key] = h
        expected = EXPECTED_EXP01_HASHES.get(rel_key)
        if expected and h != expected:
            raise RuntimeError(
                f"IMMUTABILITY VIOLATION [{tag}] for {rel_key}!\\n"
                f"Expected: {expected}\\nActual:   {h}"
            )
        log_msg(f"  [OK] {rel_key}: {h[:16]}... (matches canonical)")
    log_msg(f"EXP01 immutability confirmed: all 6 files match canonical hashes [{tag}].")
    return current_hashes


# ===========================================================================
# ISOLATED PROTOTYPE MODULE DEFINITIONS (Pure Experimental Code)
# ===========================================================================

class DoubleConvSelectiveLayout(nn.Module):
    """Prototype DoubleConv: Executes Conv2d in NHWC layout, converts to NCHW for BatchNorm2d."""

    def __init__(self, in_channels: int, out_channels: int, mid_channels: int | None = None) -> None:
        super().__init__()
        if mid_channels is None:
            mid_channels = out_channels
        self.conv1 = nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1, bias=False).to(
            memory_format=torch.channels_last
        )
        self.bn1 = nn.BatchNorm2d(mid_channels)  # Remains NCHW
        self.relu1 = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1, bias=False).to(
            memory_format=torch.channels_last
        )
        self.bn2 = nn.BatchNorm2d(out_channels)  # Remains NCHW
        self.relu2 = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x_cl = x.contiguous(memory_format=torch.channels_last)
        out_c1 = self.conv1(x_cl)
        out_c1_nchw = out_c1.to(memory_format=torch.contiguous_format)
        out_bn1 = self.relu1(self.bn1(out_c1_nchw))

        out_bn1_cl = out_bn1.contiguous(memory_format=torch.channels_last)
        out_c2 = self.conv2(out_bn1_cl)
        out_c2_nchw = out_c2.to(memory_format=torch.contiguous_format)
        return self.relu2(self.bn2(out_c2_nchw))


class DecoderBlockPrototypeB(nn.Module):
    """Prototype Variant B: ConvTranspose2d in NHWC, DoubleConvSelectiveLayout."""

    def __init__(self, in_channels: int, skip_channels: int, out_channels: int) -> None:
        super().__init__()
        self.up = nn.ConvTranspose2d(
            in_channels, in_channels // 2, kernel_size=2, stride=2
        ).to(memory_format=torch.channels_last)
        self.conv = DoubleConvSelectiveLayout((in_channels // 2) + skip_channels, out_channels)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x_cl = x.contiguous(memory_format=torch.channels_last)
        x_up = self.up(x_cl)
        if x_up.shape[-2:] != skip.shape[-2:]:
            diff_y = skip.size(2) - x_up.size(2)
            diff_x = skip.size(3) - x_up.size(3)
            x_up = nn.functional.pad(
                x_up,
                [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2],
            )
        skip_cl = skip.contiguous(memory_format=torch.channels_last)
        x_cat = torch.cat([x_up, skip_cl], dim=1)
        return self.conv(x_cat)


class DecoderBlockPrototypeC(nn.Module):
    """Prototype Variant C: Standard ConvTranspose2d (NCHW), original DoubleConv, explicit layout hints."""

    def __init__(self, in_channels: int, skip_channels: int, out_channels: int) -> None:
        super().__init__()
        self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.conv = DoubleConv((in_channels // 2) + skip_channels, out_channels)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x_up = self.up(x)
        x_up_nchw = x_up.contiguous()
        x_cat = torch.cat([x_up_nchw, skip], dim=1)
        return self.conv(x_cat)


class DecoderBlockPrototypeD(nn.Module):
    """Prototype Variant D: ConvTranspose2d in NCHW, cat in NCHW, DoubleConv with selective layout."""

    def __init__(self, in_channels: int, skip_channels: int, out_channels: int) -> None:
        super().__init__()
        self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.conv = DoubleConvSelectiveLayout((in_channels // 2) + skip_channels, out_channels)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x_up = self.up(x)
        if x_up.shape[-2:] != skip.shape[-2:]:
            diff_y = skip.size(2) - x_up.size(2)
            diff_x = skip.size(3) - x_up.size(3)
            x_up = nn.functional.pad(
                x_up,
                [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2],
            )
        x_cat = torch.cat([x_up, skip], dim=1)
        return self.conv(x_cat)


class DecoderBlockBilinear(nn.Module):
    """Architectural Alternative: Bilinear Upsample + Conv2d + DoubleConv."""

    def __init__(self, in_channels: int, skip_channels: int, out_channels: int) -> None:
        super().__init__()
        self.upsample = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False)
        self.reduce = nn.Conv2d(in_channels, in_channels // 2, kernel_size=1, bias=False)
        self.conv = DoubleConv((in_channels // 2) + skip_channels, out_channels)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x_up = self.reduce(self.upsample(x))
        if x_up.shape[-2:] != skip.shape[-2:]:
            diff_y = skip.size(2) - x_up.size(2)
            diff_x = skip.size(3) - x_up.size(3)
            x_up = nn.functional.pad(
                x_up,
                [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2],
            )
        x_cat = torch.cat([x_up, skip], dim=1)
        return self.conv(x_cat)


class PrototypeResNet34UNet(nn.Module):
    """Prototype ResNet34UNet with pluggable decoder block strategy."""

    def __init__(
        self,
        strategy: str = "control_baseline",
        pretrained: bool = False,
    ) -> None:
        super().__init__()
        self.strategy = strategy
        self.base = ResNet34UNet(
            in_channels=2,
            num_classes=1,
            pretrained=pretrained,
            adaptation_method="slice_variance_scaled",
        )

        if strategy == "control_baseline":
            pass
        elif strategy == "prototype_s1_dec1":
            self.base.dec1 = DecoderBlockPrototypeD(64, 64, 32)
        elif strategy == "prototype_s2_final":
            self.base.final_conv = DoubleConvSelectiveLayout(16, 16)
        elif strategy == "prototype_s3_dec1_final":
            self.base.dec1 = DecoderBlockPrototypeD(64, 64, 32)
            self.base.final_conv = DoubleConvSelectiveLayout(16, 16)
        elif strategy == "prototype_s4_dec2_dec1_final":
            self.base.dec2 = DecoderBlockPrototypeD(128, 64, 64)
            self.base.dec1 = DecoderBlockPrototypeD(64, 64, 32)
            self.base.final_conv = DoubleConvSelectiveLayout(16, 16)
        elif strategy == "prototype_s5_all_decoder":
            self.base.dec4 = DecoderBlockPrototypeD(512, 256, 256)
            self.base.dec3 = DecoderBlockPrototypeD(256, 128, 128)
            self.base.dec2 = DecoderBlockPrototypeD(128, 64, 64)
            self.base.dec1 = DecoderBlockPrototypeD(64, 64, 32)
            self.base.final_conv = DoubleConvSelectiveLayout(16, 16)
        elif strategy == "bilinear_alternative":
            self.base.dec4 = DecoderBlockBilinear(512, 256, 256)
            self.base.dec3 = DecoderBlockBilinear(256, 128, 128)
            self.base.dec2 = DecoderBlockBilinear(128, 64, 64)
            self.base.dec1 = DecoderBlockBilinear(64, 64, 32)
            self.base.final_up = nn.Sequential(
                nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
                nn.Conv2d(32, 16, kernel_size=1, bias=False),
            )
        else:
            raise ValueError(f"Unknown prototype strategy: {strategy}")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.base(x)

    def load_state_dict(self, state_dict, strict: bool = False):
        return self.base.load_state_dict(state_dict, strict=strict)

    def state_dict(self, *args, **kwargs):
        return self.base.state_dict(*args, **kwargs)


def copy_weights_to_prototype(base_model: ResNet34UNet, proto_model: PrototypeResNet34UNet) -> None:
    with torch.no_grad():
        proto_model.base.conv1.weight.copy_(base_model.conv1.weight)
        proto_model.base.bn1.load_state_dict(base_model.bn1.state_dict())
        proto_model.base.layer1.load_state_dict(base_model.layer1.state_dict())
        proto_model.base.layer2.load_state_dict(base_model.layer2.state_dict())
        proto_model.base.layer3.load_state_dict(base_model.layer3.state_dict())
        proto_model.base.layer4.load_state_dict(base_model.layer4.state_dict())
        proto_model.base.head.load_state_dict(base_model.head.state_dict())

        def copy_dc(src_dc: DoubleConv, dst_sel: DoubleConvSelectiveLayout):
            dst_sel.conv1.weight.copy_(src_dc.double_conv[0].weight)
            dst_sel.bn1.load_state_dict(src_dc.double_conv[1].state_dict())
            dst_sel.conv2.weight.copy_(src_dc.double_conv[3].weight)
            dst_sel.bn2.load_state_dict(src_dc.double_conv[4].state_dict())

        for blk_name in ["dec4", "dec3", "dec2", "dec1"]:
            src_blk = getattr(base_model, blk_name)
            dst_blk = getattr(proto_model.base, blk_name)
            if hasattr(dst_blk, "up") and hasattr(src_blk, "up") and isinstance(dst_blk.up, nn.ConvTranspose2d):
                dst_blk.up.weight.copy_(src_blk.up.weight)
                if src_blk.up.bias is not None and dst_blk.up.bias is not None:
                    dst_blk.up.bias.copy_(src_blk.up.bias)
            if isinstance(dst_blk.conv, DoubleConvSelectiveLayout):
                copy_dc(src_blk.conv, dst_blk.conv)
            elif isinstance(dst_blk.conv, DoubleConv):
                dst_blk.conv.load_state_dict(src_blk.conv.state_dict())

        if isinstance(proto_model.base.final_up, nn.ConvTranspose2d):
            proto_model.base.final_up.weight.copy_(base_model.final_up.weight)
            if base_model.final_up.bias is not None:
                proto_model.base.final_up.bias.copy_(base_model.final_up.bias)

        if isinstance(proto_model.base.final_conv, DoubleConvSelectiveLayout):
            copy_dc(base_model.final_conv, proto_model.base.final_conv)
        elif isinstance(proto_model.base.final_conv, DoubleConv):
            proto_model.base.final_conv.load_state_dict(base_model.final_conv.state_dict())


# ===========================================================================
# EXPERIMENT EXECUTION ENGINE
# ===========================================================================

def build_dataloader() -> DataLoader:
    manifest = DatasetManifest.load(MANIFEST_PATH)
    dataset = TrujilloTileDataset(manifest, SplitName.TRAIN, normalize=True)
    loader = DataLoader(
        dataset,
        batch_size=8,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True,
        prefetch_factor=2,
        drop_last=True,
    )
    return loader


def run_training_loop_benchmark(
    model: nn.Module,
    candidate_name: str,
    repetition: int,
    loader_iter,
    num_warmup: int = 10,
    num_measure: int = 100,
    start_time: Optional[float] = None,
) -> Dict[str, Any]:
    log_msg(f"Running Full Training-Loop Benchmark: {candidate_name} [Repetition {repetition}]")
    update_state(
        "FULL_LOOP_BENCHMARK",
        f"{candidate_name}_rep{repetition}",
        "RUNNING",
        {"num_warmup": num_warmup, "num_measure": num_measure},
        start_time=start_time,
    )

    model.train()
    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)
    scaler = torch.amp.GradScaler(DEVICE.type, enabled=True)

    log_msg(f"  Warmup {num_warmup} steps...")
    for _ in range(num_warmup):
        imgs, masks = next(loader_iter)
        imgs = imgs.to(DEVICE, non_blocking=True)
        masks = masks.to(DEVICE, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=True):
            logits = model(imgs)
            loss = criterion(logits, masks)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()

    e_fwd_start = torch.cuda.Event(enable_timing=True)
    e_fwd_end = torch.cuda.Event(enable_timing=True)
    e_bwd_start = torch.cuda.Event(enable_timing=True)
    e_bwd_end = torch.cuda.Event(enable_timing=True)
    e_opt_start = torch.cuda.Event(enable_timing=True)
    e_opt_end = torch.cuda.Event(enable_timing=True)

    fwd_times, bwd_times, opt_times, step_times = [], [], [], []
    losses = []

    log_msg(f"  Measuring {num_measure} steps...")
    t_bench_start = time.perf_counter()

    for step_idx in range(num_measure):
        t0 = time.perf_counter()
        imgs, masks = next(loader_iter)
        imgs = imgs.to(DEVICE, non_blocking=True)
        masks = masks.to(DEVICE, non_blocking=True)

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
        dt_step = (time.perf_counter() - t0) * 1000.0
        step_times.append(dt_step)
        fwd_times.append(e_fwd_start.elapsed_time(e_fwd_end))
        bwd_times.append(e_bwd_start.elapsed_time(e_bwd_end))
        opt_times.append(e_opt_start.elapsed_time(e_opt_end))
        losses.append(loss.item())

        if (step_idx + 1) % 25 == 0 or (step_idx + 1) == num_measure:
            current_sps = (len(step_times) * 8.0) / (sum(step_times) / 1000.0)
            log_msg(f"    Step {step_idx + 1:3d}/{num_measure}: step={dt_step:6.2f}ms | avg={np.mean(step_times):6.2f}ms -> {current_sps:5.2f} samp/s")

    total_bench_time = time.perf_counter() - t_bench_start
    mean_step = float(np.mean(step_times))
    median_step = float(np.median(step_times))
    p95_step = float(np.percentile(step_times, 95))
    std_step = float(np.std(step_times))
    mean_fwd = float(np.mean(fwd_times))
    mean_bwd = float(np.mean(bwd_times))
    mean_opt = float(np.mean(opt_times))
    samples_per_sec = (num_measure * 8.0) / (sum(step_times) / 1000.0)

    telem = get_gpu_telemetry()
    peak_vram_mb = round(torch.cuda.max_memory_allocated() / (1024 * 1024), 2)

    res = {
        "candidate": candidate_name,
        "repetition": repetition,
        "num_measure": num_measure,
        "samples_per_sec": round(samples_per_sec, 2),
        "mean_step_ms": round(mean_step, 2),
        "median_step_ms": round(median_step, 2),
        "p95_step_ms": round(p95_step, 2),
        "std_step_ms": round(std_step, 2),
        "mean_fwd_ms": round(mean_fwd, 2),
        "mean_bwd_ms": round(mean_bwd, 2),
        "mean_opt_ms": round(mean_opt, 2),
        "peak_vram_mb": peak_vram_mb,
        "temperature_c": telem["temperature_c"],
        "clock_mhz": telem["clock_mhz"],
        "power_w": telem["power_w"],
        "utilization_pct": telem["utilization_pct"],
        "final_loss": round(float(np.mean(losses[-10:])), 4),
    }
    log_msg(f"  [{candidate_name} Rep {repetition}] Result: {samples_per_sec:.2f} samp/s (Step: {mean_step:.2f}ms, Fwd: {mean_fwd:.2f}ms, Bwd: {mean_bwd:.2f}ms, VRAM: {peak_vram_mb} MB)")
    
    # Cleanup memory
    del optimizer, scaler, criterion
    torch.cuda.empty_cache()
    gc.collect()
    return res


# ===========================================================================
# EXPERIMENT 1: OPERATOR MICROBENCHMARKS
# ===========================================================================

def run_experiment_1_microbenchmarks(start_time: Optional[float] = None) -> List[Dict[str, Any]]:
    log_msg("================================================================================")
    log_msg("EXPERIMENT 1: DECODER OPERATOR MICROBENCHMARKS")
    log_msg("================================================================================")
    update_state("EXPERIMENT_1_MICROBENCH", "EXP1_MICROBENCH", "RUNNING", start_time=start_time)

    results = []

    def profile_micro_op(
        op_name: str,
        runner_fn: Callable[[], Any],
        cleanup_fn: Optional[Callable[[], None]] = None,
        num_timing_reps: int = 20,
    ) -> Dict[str, Any]:
        torch.cuda.synchronize()
        torch.cuda.empty_cache()

        # Warmup
        for _ in range(5):
            out = runner_fn()
            if isinstance(out, torch.Tensor) and out.requires_grad:
                out.sum().backward()
            if cleanup_fn:
                cleanup_fn()
        torch.cuda.synchronize()

        # Timing pass with CUDA Events
        ev_start = torch.cuda.Event(enable_timing=True)
        ev_end = torch.cuda.Event(enable_timing=True)

        ev_start.record()
        for _ in range(num_timing_reps):
            out = runner_fn()
            if isinstance(out, torch.Tensor) and out.requires_grad:
                out.sum().backward()
            if cleanup_fn:
                cleanup_fn()
        ev_end.record()
        torch.cuda.synchronize()
        total_latency = ev_start.elapsed_time(ev_end) / num_timing_reps

        # Profiler pass (strictly 2 reps to measure conversion calls and time)
        with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CUDA]) as prof:
            for _ in range(2):
                out = runner_fn()
                if isinstance(out, torch.Tensor) and out.requires_grad:
                    out.sum().backward()
                if cleanup_fn:
                    cleanup_fn()
            torch.cuda.synchronize()

        events = prof.key_averages()
        c_nchw = sum(e.count for e in events if "nchwtonhwc" in e.key.lower()) // 2
        t_nchw = (sum(e.self_device_time_total for e in events if "nchwtonhwc" in e.key.lower()) / 2) / 1000.0
        c_nhwc = sum(e.count for e in events if "nhwctonchw" in e.key.lower()) // 2
        t_nhwc = (sum(e.self_device_time_total for e in events if "nhwctonchw" in e.key.lower()) / 2) / 1000.0
        conv_t = t_nchw + t_nhwc

        res = {
            "test_name": op_name,
            "total_latency_ms": round(total_latency, 3),
            "conversion_ms": round(conv_t, 3),
            "nchw_to_nhwc_calls": c_nchw,
            "nhwc_to_nchw_calls": c_nhwc,
            "conversion_pct": round((conv_t / total_latency * 100.0) if total_latency > 0 else 0.0, 1),
        }
        log_msg(f"  {op_name:46s} | Total: {total_latency:6.3f} ms | Conv: {c_nchw + c_nhwc:2d} calls ({conv_t:6.3f} ms, {res['conversion_pct']:4.1f}%)")

        torch.cuda.empty_cache()
        gc.collect()
        return res

    shapes = [
        ("dec1 (96->32, 256x256)", 96, 32, 256),
        ("final (16->16, 512x512)", 16, 16, 512),
        ("dec2 (128->64, 128x128)", 128, 64, 128),
    ]

    for label, in_c, out_c, spat in shapes:
        log_msg(f"--- Shape Cluster: {label} ---")
        x_nchw = torch.randn(8, in_c, spat, spat, device=DEVICE)
        x_nhwc = x_nchw.contiguous(memory_format=torch.channels_last)

        # A. Conv2d NCHW
        conv_nchw = nn.Conv2d(in_c, out_c, 3, padding=1, bias=False).to(DEVICE)
        with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
            results.append(profile_micro_op(
                f"A. Conv2d NCHW [{label}]",
                lambda: conv_nchw(x_nchw.detach().requires_grad_()),
                lambda: conv_nchw.zero_grad(set_to_none=True)
            ))

        # B. Conv2d NHWC
        conv_nhwc = nn.Conv2d(in_c, out_c, 3, padding=1, bias=False).to(DEVICE).to(memory_format=torch.channels_last)
        with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
            results.append(profile_micro_op(
                f"B. Conv2d NHWC [{label}]",
                lambda: conv_nhwc(x_nhwc.detach().requires_grad_()),
                lambda: conv_nhwc.zero_grad(set_to_none=True)
            ))

        # F. Conv2d -> BatchNorm2d (Standard NCHW)
        bn_nchw = nn.BatchNorm2d(out_c).to(DEVICE)
        with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
            results.append(profile_micro_op(
                f"F. Conv2d->BN2d NCHW [{label}]",
                lambda: bn_nchw(conv_nchw(x_nchw.detach().requires_grad_())),
                lambda: (conv_nchw.zero_grad(set_to_none=True), bn_nchw.zero_grad(set_to_none=True))
            ))

        # G. NHWC Conv2d -> NCHW BatchNorm2d (with explicit to(NCHW))
        with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
            results.append(profile_micro_op(
                f"G. NHWC Conv->to(NCHW)->BN [{label}]",
                lambda: bn_nchw(conv_nhwc(x_nhwc.detach().requires_grad_()).to(memory_format=torch.contiguous_format)),
                lambda: (conv_nhwc.zero_grad(set_to_none=True), bn_nchw.zero_grad(set_to_none=True))
            ))

        # I. NHWC Conv2d -> NHWC BatchNorm2d (Full channels_last)
        bn_nhwc = nn.BatchNorm2d(out_c).to(DEVICE).to(memory_format=torch.channels_last)
        with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
            results.append(profile_micro_op(
                f"I. NHWC Conv->BN NHWC [{label}]",
                lambda: bn_nhwc(conv_nhwc(x_nhwc.detach().requires_grad_())),
                lambda: (conv_nhwc.zero_grad(set_to_none=True), bn_nhwc.zero_grad(set_to_none=True))
            ))

        del x_nchw, x_nhwc, conv_nchw, conv_nhwc, bn_nchw, bn_nhwc
        torch.cuda.empty_cache()
        gc.collect()

    log_msg("--- ConvTranspose2d Microbenchmarks (dec1 up: 64->32, 128->256) ---")
    x_up_nchw = torch.randn(8, 64, 128, 128, device=DEVICE)
    x_up_nhwc = x_up_nchw.contiguous(memory_format=torch.channels_last)

    up_nchw = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2).to(DEVICE)
    up_nhwc = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2).to(DEVICE).to(memory_format=torch.channels_last)

    with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
        results.append(profile_micro_op(
            "C. ConvTranspose2d NCHW",
            lambda: up_nchw(x_up_nchw.detach().requires_grad_()),
            lambda: up_nchw.zero_grad(set_to_none=True)
        ))
        results.append(profile_micro_op(
            "D. ConvTranspose2d NHWC",
            lambda: up_nhwc(x_up_nhwc.detach().requires_grad_()),
            lambda: up_nhwc.zero_grad(set_to_none=True)
        ))

    c2_nchw = nn.Conv2d(32, 32, 3, padding=1, bias=False).to(DEVICE)
    c2_nhwc = nn.Conv2d(32, 32, 3, padding=1, bias=False).to(DEVICE).to(memory_format=torch.channels_last)
    with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
        results.append(profile_micro_op(
            "E1. ConvTrans->Conv2d NCHW",
            lambda: c2_nchw(up_nchw(x_up_nchw.detach().requires_grad_())),
            lambda: (up_nchw.zero_grad(set_to_none=True), c2_nchw.zero_grad(set_to_none=True))
        ))
        results.append(profile_micro_op(
            "E2. ConvTrans->Conv2d NHWC",
            lambda: c2_nhwc(up_nhwc(x_up_nhwc.detach().requires_grad_())),
            lambda: (up_nhwc.zero_grad(set_to_none=True), c2_nhwc.zero_grad(set_to_none=True))
        ))

    del x_up_nchw, x_up_nhwc, up_nchw, up_nhwc, c2_nchw, c2_nhwc
    torch.cuda.empty_cache()
    gc.collect()

    update_state("EXPERIMENT_1_MICROBENCH", "EXP1_MICROBENCH", "COMPLETED", {"ops_tested": len(results)}, start_time=start_time)
    return results


# ===========================================================================
# EXPERIMENT 2 & 3: SINGLE-BLOCK & HIGH-RESOLUTION PROTOTYPES
# ===========================================================================

def run_experiment_2_and_3_block_prototypes(start_time: Optional[float] = None) -> List[Dict[str, Any]]:
    log_msg("================================================================================")
    log_msg("EXPERIMENT 2 & 3: SINGLE-BLOCK & HIGH-RESOLUTION PROTOTYPES")
    log_msg("================================================================================")
    update_state("EXPERIMENT_2_3_BLOCK_PROTOS", "EXP2_3_BLOCK_PROTOS", "RUNNING", start_time=start_time)

    results = []

    def profile_block(
        block_name: str,
        runner_fn: Callable[[], Any],
        cleanup_fn: Optional[Callable[[], None]] = None,
        num_timing_reps: int = 20,
    ) -> Dict[str, Any]:
        torch.cuda.synchronize()
        torch.cuda.empty_cache()

        for _ in range(5):
            out = runner_fn()
            out.sum().backward()
            if cleanup_fn:
                cleanup_fn()
        torch.cuda.synchronize()

        ev_start = torch.cuda.Event(enable_timing=True)
        ev_end = torch.cuda.Event(enable_timing=True)

        ev_start.record()
        for _ in range(num_timing_reps):
            out = runner_fn()
            out.sum().backward()
            if cleanup_fn:
                cleanup_fn()
        ev_end.record()
        torch.cuda.synchronize()
        total_latency = ev_start.elapsed_time(ev_end) / num_timing_reps

        with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CUDA]) as prof:
            for _ in range(2):
                out = runner_fn()
                out.sum().backward()
                if cleanup_fn:
                    cleanup_fn()
            torch.cuda.synchronize()

        events = prof.key_averages()
        c_nchw = sum(e.count for e in events if "nchwtonhwc" in e.key.lower()) // 2
        t_nchw = (sum(e.self_device_time_total for e in events if "nchwtonhwc" in e.key.lower()) / 2) / 1000.0
        c_nhwc = sum(e.count for e in events if "nhwctonchw" in e.key.lower()) // 2
        t_nhwc = (sum(e.self_device_time_total for e in events if "nhwctonchw" in e.key.lower()) / 2) / 1000.0
        conv_t = t_nchw + t_nhwc

        res = {
            "block_test": block_name,
            "total_step_ms": round(total_latency, 3),
            "conversion_ms": round(conv_t, 3),
            "conversion_calls": c_nchw + c_nhwc,
            "conversion_pct": round((conv_t / total_latency * 100.0) if total_latency > 0 else 0.0, 1),
        }
        log_msg(f"  {block_name:46s} | Total: {total_latency:6.3f} ms | Conv: {c_nchw + c_nhwc:2d} calls ({conv_t:6.3f} ms, {res['conversion_pct']:4.1f}%)")

        torch.cuda.empty_cache()
        gc.collect()
        return res

    # 1. dec1 Block Variants (in=64, skip=64, out=32, spatial: 128 -> 256)
    log_msg("--- Evaluating dec1 Block Variants (128x128 -> 256x256) ---")
    x_d2 = torch.randn(8, 64, 128, 128, device=DEVICE)
    x_s0 = torch.randn(8, 64, 256, 256, device=DEVICE)

    dec1_a = DecoderBlock(64, 64, 32).to(DEVICE)
    with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
        results.append(profile_block(
            "dec1 Variant A (Original NCHW)",
            lambda: dec1_a(x_d2.detach().requires_grad_(), x_s0.detach()),
            lambda: dec1_a.zero_grad(set_to_none=True)
        ))

    dec1_b = DecoderBlockPrototypeB(64, 64, 32).to(DEVICE)
    with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
        results.append(profile_block(
            "dec1 Variant B (NHWC up + Selective DC)",
            lambda: dec1_b(x_d2.detach().requires_grad_(), x_s0.detach()),
            lambda: dec1_b.zero_grad(set_to_none=True)
        ))

    dec1_c = DecoderBlockPrototypeC(64, 64, 32).to(DEVICE)
    with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
        results.append(profile_block(
            "dec1 Variant C (NCHW explicit cat)",
            lambda: dec1_c(x_d2.detach().requires_grad_(), x_s0.detach()),
            lambda: dec1_c.zero_grad(set_to_none=True)
        ))

    dec1_d = DecoderBlockPrototypeD(64, 64, 32).to(DEVICE)
    with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
        results.append(profile_block(
            "dec1 Variant D (NCHW up + Selective DC)",
            lambda: dec1_d(x_d2.detach().requires_grad_(), x_s0.detach()),
            lambda: dec1_d.zero_grad(set_to_none=True)
        ))

    del x_d2, x_s0, dec1_a, dec1_b, dec1_c, dec1_d
    torch.cuda.empty_cache()
    gc.collect()

    # 2. Final stage: final_up + final_conv (in=32, out=16, 256x256 -> 512x512)
    log_msg("--- Evaluating Final Stage Variants (256x256 -> 512x512) ---")
    x_d1 = torch.randn(8, 32, 256, 256, device=DEVICE)

    final_up_a = nn.ConvTranspose2d(32, 16, kernel_size=2, stride=2).to(DEVICE)
    final_conv_a = DoubleConv(16, 16).to(DEVICE)

    with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
        results.append(profile_block(
            "final_stage Variant A (Original NCHW)",
            lambda: final_conv_a(final_up_a(x_d1.detach().requires_grad_())),
            lambda: (final_up_a.zero_grad(set_to_none=True), final_conv_a.zero_grad(set_to_none=True))
        ))

    final_conv_sel = DoubleConvSelectiveLayout(16, 16).to(DEVICE)
    with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
        results.append(profile_block(
            "final_stage Variant B (Selective DoubleConv)",
            lambda: final_conv_sel(final_up_a(x_d1.detach().requires_grad_())),
            lambda: (final_up_a.zero_grad(set_to_none=True), final_conv_sel.zero_grad(set_to_none=True))
        ))

    del x_d1, final_up_a, final_conv_a, final_conv_sel
    torch.cuda.empty_cache()
    gc.collect()

    # 3. dec2 Block Variants (in=128, skip=64, out=64, 64x64 -> 128x128)
    log_msg("--- Evaluating dec2 Block Variants (64x64 -> 128x128) ---")
    x_d3 = torch.randn(8, 128, 64, 64, device=DEVICE)
    x_s1 = torch.randn(8, 64, 128, 128, device=DEVICE)

    dec2_a = DecoderBlock(128, 64, 64).to(DEVICE)
    dec2_d = DecoderBlockPrototypeD(128, 64, 64).to(DEVICE)
    with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
        results.append(profile_block(
            "dec2 Variant A (Original NCHW)",
            lambda: dec2_a(x_d3.detach().requires_grad_(), x_s1.detach()),
            lambda: dec2_a.zero_grad(set_to_none=True)
        ))
        results.append(profile_block(
            "dec2 Variant D (NCHW up + Selective DC)",
            lambda: dec2_d(x_d3.detach().requires_grad_(), x_s1.detach()),
            lambda: dec2_d.zero_grad(set_to_none=True)
        ))

    del x_d3, x_s1, dec2_a, dec2_d
    torch.cuda.empty_cache()
    gc.collect()

    update_state("EXPERIMENT_2_3_BLOCK_PROTOS", "EXP2_3_BLOCK_PROTOS", "COMPLETED", {"variants_tested": len(results)}, start_time=start_time)
    return results


# ===========================================================================
# NUMERICAL CORRECTNESS GATE
# ===========================================================================

def run_numerical_correctness_gate(
    base_model: ResNet34UNet,
    candidates: List[Tuple[str, PrototypeResNet34UNet]],
) -> List[Dict[str, Any]]:
    log_msg("================================================================================")
    log_msg("NUMERICAL CORRECTNESS GATE")
    log_msg("================================================================================")

    results = []
    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0).to(DEVICE)

    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)
    x_test = torch.randn(8, 2, 512, 512, device=DEVICE)
    y_test = torch.randint(0, 2, (8, 1, 512, 512), device=DEVICE).float()

    base_model.eval()
    with torch.no_grad():
        with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
            base_logits = base_model(x_test)
            base_loss = criterion(base_logits, y_test).item()

    base_model.train()
    base_model.zero_grad(set_to_none=True)
    with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
        b_logits = base_model(x_test)
        b_loss = criterion(b_logits, y_test)
    b_loss.backward()
    base_grad_norm = float(torch.nn.utils.clip_grad_norm_(base_model.parameters(), max_norm=1e9))

    for cand_name, cand_model in candidates:
        copy_weights_to_prototype(base_model, cand_model)

        cand_model.eval()
        with torch.no_grad():
            with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
                c_logits = cand_model(x_test)
                c_loss = criterion(c_logits, y_test).item()

        cand_model.train()
        cand_model.zero_grad(set_to_none=True)
        with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16):
            c_tr_logits = cand_model(x_test)
            c_tr_loss = criterion(c_tr_logits, y_test)
        c_tr_loss.backward()
        cand_grad_norm = float(torch.nn.utils.clip_grad_norm_(cand_model.parameters(), max_norm=1e9))

        shape_match = (c_logits.shape == torch.Size([8, 1, 512, 512]))
        is_finite = bool(torch.isfinite(c_logits).all().item()) and bool(torch.isfinite(torch.tensor(cand_grad_norm)).item())

        max_abs_diff = float((base_logits - c_logits).abs().max().item())
        mean_abs_diff = float((base_logits - c_logits).abs().mean().item())
        loss_diff = abs(base_loss - c_loss)
        grad_norm_diff = abs(base_grad_norm - cand_grad_norm)

        n_params = sum(p.numel() for p in cand_model.parameters())
        base_params = sum(p.numel() for p in base_model.parameters())
        param_match = (n_params == base_params)

        passed = shape_match and is_finite and (max_abs_diff < 1.0) and (mean_abs_diff < 0.1)

        res = {
            "candidate": cand_name,
            "shape_match": shape_match,
            "is_finite": is_finite,
            "param_count": n_params,
            "param_count_matches_base": param_match,
            "max_abs_diff": round(max_abs_diff, 6),
            "mean_abs_diff": round(mean_abs_diff, 6),
            "base_loss": round(base_loss, 4),
            "cand_loss": round(c_loss, 4),
            "loss_diff": round(loss_diff, 6),
            "base_grad_norm": round(base_grad_norm, 4),
            "cand_grad_norm": round(cand_grad_norm, 4),
            "grad_norm_diff": round(grad_norm_diff, 4),
            "passed": passed,
        }
        results.append(res)
        log_msg(
            f"  {cand_name:30s} | Shape: {shape_match} | Finite: {is_finite} | Params: {n_params} (match: {param_match}) | "
            f"MaxDiff: {max_abs_diff:.5f} | MeanDiff: {mean_abs_diff:.5f} | LossDiff: {loss_diff:.5f} | Gate: {'PASS' if passed else 'FAIL'}"
        )

    del x_test, y_test, base_logits, b_logits
    torch.cuda.empty_cache()
    gc.collect()
    return results


# ===========================================================================
# PROFILER TRACE COMPARISON
# ===========================================================================

def run_profiler_comparison(
    control_model: nn.Module,
    candidate_model: nn.Module,
    candidate_name: str,
    loader_iter,
) -> Dict[str, Any]:
    log_msg("================================================================================")
    log_msg(f"PROFILER TRACE COMPARISON: Control vs {candidate_name}")
    log_msg("================================================================================")

    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0).to(DEVICE)
    scaler = torch.amp.GradScaler(DEVICE.type, enabled=True)

    def profile_single_step(m: nn.Module) -> Dict[str, Any]:
        imgs, masks = next(loader_iter)
        imgs = imgs.to(DEVICE, non_blocking=True)
        masks = masks.to(DEVICE, non_blocking=True)
        m.train()
        m.zero_grad(set_to_none=True)

        with torch.profiler.profile(
            activities=[torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA],
            record_shapes=False,
        ) as prof:
            with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=True):
                logits = m(imgs)
                loss = criterion(logits, masks)
            scaler.scale(loss).backward()
            torch.cuda.synchronize()

        events = prof.key_averages()
        c_nchw = sum(e.count for e in events if "nchwtonhwc" in e.key.lower())
        t_nchw = sum(e.self_device_time_total for e in events if "nchwtonhwc" in e.key.lower()) / 1000.0
        c_nhwc = sum(e.count for e in events if "nhwctonchw" in e.key.lower())
        t_nhwc = sum(e.self_device_time_total for e in events if "nhwctonchw" in e.key.lower()) / 1000.0
        total_dev = sum(e.self_device_time_total for e in events) / 1000.0
        conv_t = t_nchw + t_nhwc

        m.zero_grad(set_to_none=True)
        del imgs, masks, logits, loss
        torch.cuda.empty_cache()
        gc.collect()

        return {
            "total_cuda_time_ms": round(total_dev, 2),
            "conversion_calls": c_nchw + c_nhwc,
            "conversion_ms": round(conv_t, 2),
            "nchw_to_nhwc": {"calls": c_nchw, "ms": round(t_nchw, 2)},
            "nhwc_to_nchw": {"calls": c_nhwc, "ms": round(t_nhwc, 2)},
        }

    control_prof = profile_single_step(control_model)
    cand_prof = profile_single_step(candidate_model)

    comp = {
        "control": control_prof,
        "candidate_name": candidate_name,
        "candidate": cand_prof,
        "conversion_calls_change": cand_prof["conversion_calls"] - control_prof["conversion_calls"],
        "conversion_ms_change": round(cand_prof["conversion_ms"] - control_prof["conversion_ms"], 2),
        "total_cuda_ms_change": round(cand_prof["total_cuda_time_ms"] - control_prof["total_cuda_time_ms"], 2),
    }
    log_msg(f"  Control:   {control_prof['conversion_calls']:3d} conversion calls ({control_prof['conversion_ms']:5.2f} ms) | Total CUDA: {control_prof['total_cuda_time_ms']:6.2f} ms")
    log_msg(f"  Candidate: {cand_prof['conversion_calls']:3d} conversion calls ({cand_prof['conversion_ms']:5.2f} ms) | Total CUDA: {cand_prof['total_cuda_time_ms']:6.2f} ms")
    log_msg(f"  Delta:     {comp['conversion_calls_change']:+3d} conversion calls ({comp['conversion_ms_change']:+5.2f} ms) | Delta CUDA: {comp['total_cuda_ms_change']:+6.2f} ms")

    return comp


# ===========================================================================
# MAIN HARNESS
# ===========================================================================

def main() -> None:
    start_time = time.time()
    log_msg("================================================================================")
    log_msg("OCEAN SENTINEL — STEP 2C-B: SELECTIVE DECODER LAYOUT OPTIMIZATION BENCHMARK")
    log_msg("================================================================================")

    update_state("PRE_AUDIT", "EXP01_HASHES", "RUNNING", start_time=start_time)
    pre_hashes = verify_exp01("PRE-RUN")
    update_state("PRE_AUDIT", "EXP01_HASHES", "COMPLETED", {"hashes": pre_hashes}, start_time=start_time)

    torch.backends.cudnn.benchmark = True
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    if hasattr(torch, "set_float32_matmul_precision"):
        torch.set_float32_matmul_precision("high")
    torch.set_num_threads(14)

    log_msg("Initializing production DataLoader...")
    loader = build_dataloader()
    loader_iter = iter(loader)

    # 1. Baseline Control Reproduction (2 repetitions x 100 batches)
    log_msg("--- REPRODUCING BASELINE CONTROL ---")
    control_model = ResNet34UNet(
        in_channels=2,
        num_classes=1,
        pretrained=False,
        adaptation_method="slice_variance_scaled",
    ).to(DEVICE)

    control_rep1 = run_training_loop_benchmark(
        control_model, "Control_Baseline", repetition=1, loader_iter=loader_iter,
        num_warmup=10, num_measure=100, start_time=start_time
    )
    control_rep2 = run_training_loop_benchmark(
        control_model, "Control_Baseline", repetition=2, loader_iter=loader_iter,
        num_warmup=5, num_measure=100, start_time=start_time
    )

    control_mean_sps = round((control_rep1["samples_per_sec"] + control_rep2["samples_per_sec"]) / 2.0, 2)
    control_mean_step = round((control_rep1["mean_step_ms"] + control_rep2["mean_step_ms"]) / 2.0, 2)
    log_msg(f"Baseline Control Established: {control_mean_sps:.2f} samp/s ({control_mean_step:.2f} ms/step)")

    # 2. Experiment 1: Operator Microbenchmarks
    exp1_microbench = run_experiment_1_microbenchmarks(start_time=start_time)

    # 3. Experiment 2 & 3: Single-Block & High-Resolution Prototypes
    exp2_3_blocks = run_experiment_2_and_3_block_prototypes(start_time=start_time)

    # 4. Full Training-Loop Benchmarks on Multi-Block Prototypes
    log_msg("--- EVALUATING MULTI-BLOCK PROTOTYPES (FULL TRAINING LOOP) ---")
    candidates = [
        ("Prototype_S1_dec1", PrototypeResNet34UNet(strategy="prototype_s1_dec1").to(DEVICE)),
        ("Prototype_S2_final", PrototypeResNet34UNet(strategy="prototype_s2_final").to(DEVICE)),
        ("Prototype_S3_dec1_final", PrototypeResNet34UNet(strategy="prototype_s3_dec1_final").to(DEVICE)),
        ("Prototype_S5_all_dec", PrototypeResNet34UNet(strategy="prototype_s5_all_decoder").to(DEVICE)),
        ("Alternative_Bilinear", PrototypeResNet34UNet(strategy="bilinear_alternative").to(DEVICE)),
    ]

    full_loop_results = []
    full_loop_results.append({
        "candidate": "Control_Baseline",
        "rep1_sps": control_rep1["samples_per_sec"],
        "rep2_sps": control_rep2["samples_per_sec"],
        "mean_sps": control_mean_sps,
        "mean_step_ms": control_mean_step,
        "gain_vs_control_pct": 0.0,
        "peak_vram_mb": max(control_rep1["peak_vram_mb"], control_rep2["peak_vram_mb"]),
        "temp_c": control_rep2["temperature_c"],
        "verdict": "REFERENCE CONTROL",
    })

    for cand_name, cand_mod in candidates:
        r1 = run_training_loop_benchmark(
            cand_mod, cand_name, repetition=1, loader_iter=loader_iter,
            num_warmup=10, num_measure=100, start_time=start_time
        )
        r2 = run_training_loop_benchmark(
            cand_mod, cand_name, repetition=2, loader_iter=loader_iter,
            num_warmup=5, num_measure=100, start_time=start_time
        )
        m_sps = round((r1["samples_per_sec"] + r2["samples_per_sec"]) / 2.0, 2)
        m_step = round((r1["mean_step_ms"] + r2["mean_step_ms"]) / 2.0, 2)
        gain_pct = round(((m_sps - control_mean_sps) / control_mean_sps) * 100.0, 2)
        vram = max(r1["peak_vram_mb"], r2["peak_vram_mb"])

        if gain_pct > 5.0:
            verdict = "MEANINGFUL SPEEDUP"
        elif gain_pct > 2.0:
            verdict = "MARGINAL GAIN"
        elif gain_pct >= -2.0:
            verdict = "PARITY / NO MATERIAL GAIN"
        else:
            verdict = "REGRESSION"

        full_loop_results.append({
            "candidate": cand_name,
            "rep1_sps": r1["samples_per_sec"],
            "rep2_sps": r2["samples_per_sec"],
            "mean_sps": m_sps,
            "mean_step_ms": m_step,
            "gain_vs_control_pct": gain_pct,
            "peak_vram_mb": vram,
            "temp_c": r2["temperature_c"],
            "verdict": verdict,
        })

    # 5. Numerical Correctness Gate
    gate_results = run_numerical_correctness_gate(control_model, candidates)

    # 6. Profiler Comparison (Control vs best selective prototype, e.g. S1 or S3)
    best_proto_candidate = candidates[0][1]
    best_proto_name = candidates[0][0]
    prof_comparison = run_profiler_comparison(control_model, best_proto_candidate, best_proto_name, loader_iter)

    # 7. Post-experiment EXP01 hash verification
    update_state("POST_AUDIT", "EXP01_HASHES", "RUNNING", start_time=start_time)
    post_hashes = verify_exp01("POST-RUN")
    update_state("POST_AUDIT", "EXP01_HASHES", "COMPLETED", {"hashes": post_hashes}, start_time=start_time)

    # 8. Results JSON persistence
    total_elapsed = time.time() - start_time
    now_tag = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_filename = PERF_DIR / f"gpu_step2c_b_results_{now_tag}.json"

    full_report = {
        "title": "Ocean Sentinel — Step 2C-B Selective Decoder Layout Optimization Benchmark Results",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_elapsed_sec": round(total_elapsed, 2),
        "environment": {
            "gpu": torch.cuda.get_device_name(0),
            "vram_total_mb": round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024), 1),
            "driver": "616.64",
            "compute_capability": f"{torch.cuda.get_device_capability(0)[0]}.{torch.cuda.get_device_capability(0)[1]}",
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "cudnn_version": torch.backends.cudnn.version(),
            "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        },
        "exp01_hashes_pre": pre_hashes,
        "exp01_hashes_post": post_hashes,
        "control_reproduction": {
            "rep1": control_rep1,
            "rep2": control_rep2,
            "mean_sps": control_mean_sps,
            "mean_step_ms": control_mean_step,
        },
        "microbenchmarks": exp1_microbench,
        "single_block_prototypes": exp2_3_blocks,
        "full_loop_results": full_loop_results,
        "numerical_correctness_gate": gate_results,
        "profiler_comparison": prof_comparison,
    }

    with open(results_filename, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    log_msg(f"Complete Step 2C-B results saved to: {results_filename}")
    update_state(
        "ALL_PHASES_COMPLETE",
        "STEP_2C_B",
        "COMPLETED",
        {
            "results_file": str(results_filename),
            "control_sps": control_mean_sps,
            "candidates_tested": len(candidates),
        },
        start_time=start_time,
    )
    log_msg("Step 2C-B Benchmark execution finished successfully.")


if __name__ == "__main__":
    main()
