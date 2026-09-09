#!/usr/bin/env python3
"""
Non-Destructive Capability & Framework Smoke Probe for Ocean Sentinel.
Compatible with both Local (Windows) and Cloud (Kaggle/Linux) environments.

Performs:
1. Host system telemetry (OS, Python, CPU count, RAM).
2. CUDA accelerator telemetry (device count, name, compute capability, VRAM).
3. PyTorch runtime telemetry (torch, cuda, cudnn, AMP FP16, bfloat16, TF32).
4. Environment & package compatibility check (torchvision, albumentations, rasterio, etc.).
5. Filesystem inspection (/kaggle/working, /kaggle/input, /kaggle/temp, disk capacity).
6. Basic CUDA smoke tests (allocation, matmul, conv2d, AMP).
7. Ocean Sentinel synthetic framework smoke test:
   - ResNet34UNet instantiation (24,346,305 parameters)
   - Synthetic 2-channel forward pass ([1, 2, 512, 512])
   - Output logit shape verification ([1, 1, 512, 512])
   - Combined BCE + Dice loss computation
   - Autograd backward pass
   - Optimizer step
   - Peak VRAM recording

Zero dataset transfer. Zero training. Quota consumption < 10 seconds.
"""

from __future__ import annotations

import argparse
import ctypes
import datetime
import json
import math
import os
import platform
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# =====================================================================
# 1. HOST SYSTEM & RAM TELEMETRY
# =====================================================================

def get_ram_info() -> Tuple[Optional[float], Optional[float]]:
    """Return (total_ram_gb, available_ram_gb) using standard library."""
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


# =====================================================================
# 2. CANONICAL RESNET34-UNET & LOSS DEFINITIONS (SELF-CONTAINED)
# =====================================================================

import torch
import torch.nn as nn
import torchvision.models as models
from torchvision.models import ResNet34_Weights


class DoubleConv(nn.Module):
    """Two consecutive [Conv2d -> BatchNorm2d -> ReLU] blocks."""
    def __init__(self, in_channels: int, out_channels: int, mid_channels: Optional[int] = None) -> None:
        super().__init__()
        if mid_channels is None:
            mid_channels = out_channels
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(mid_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.double_conv(x)


class DecoderBlock(nn.Module):
    """Decoder block: ConvTranspose2d upsampling + Skip concatenation + DoubleConv."""
    def __init__(self, in_channels: int, skip_channels: int, out_channels: int) -> None:
        super().__init__()
        self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.conv = DoubleConv((in_channels // 2) + skip_channels, out_channels)

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


def adapt_resnet_conv1_weights(
    pretrained_weights: torch.Tensor,
    method: str = "slice_variance_scaled",
) -> torch.Tensor:
    """Adapt pretrained 3-channel conv1 kernel to 2-channel SAR input."""
    w = pretrained_weights.clone()
    if method == "slice_variance_scaled":
        scale = math.sqrt(3.0 / 2.0)
        return w[:, 0:2, :, :] * scale
    elif method == "slice":
        return w[:, 0:2, :, :]
    else:
        raise ValueError(f"Unknown adaptation method: {method}")


class ResNet34UNet(nn.Module):
    """Canonical ResNet34UNet for Ocean Sentinel SAR imagery (2-channel input)."""
    def __init__(
        self,
        in_channels: int = 2,
        num_classes: int = 1,
        pretrained: bool = False,
        adaptation_method: str = "slice_variance_scaled",
    ) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.num_classes = num_classes

        # ResNet-34 encoder
        weights = ResNet34_Weights.DEFAULT if pretrained else None
        base_resnet = models.resnet34(weights=weights)

        orig_conv1 = base_resnet.conv1
        new_conv1 = nn.Conv2d(
            in_channels=2,
            out_channels=orig_conv1.out_channels,
            kernel_size=orig_conv1.kernel_size,
            stride=orig_conv1.stride,
            padding=orig_conv1.padding,
            bias=orig_conv1.bias is not None,
        )

        if pretrained:
            adapted_w = adapt_resnet_conv1_weights(orig_conv1.weight.data, method=adaptation_method)
            new_conv1.weight.data.copy_(adapted_w)
            if orig_conv1.bias is not None:
                new_conv1.bias.data.copy_(orig_conv1.bias.data)
        else:
            nn.init.kaiming_normal_(new_conv1.weight, mode="fan_out", nonlinearity="relu")
            if new_conv1.bias is not None:
                nn.init.constant_(new_conv1.bias, 0)

        self.conv1 = new_conv1
        self.bn1 = base_resnet.bn1
        self.relu = base_resnet.relu
        self.maxpool = base_resnet.maxpool

        self.layer1 = base_resnet.layer1
        self.layer2 = base_resnet.layer2
        self.layer3 = base_resnet.layer3
        self.layer4 = base_resnet.layer4

        # Decoder stages
        self.dec4 = DecoderBlock(in_channels=512, skip_channels=256, out_channels=256)
        self.dec3 = DecoderBlock(in_channels=256, skip_channels=128, out_channels=128)
        self.dec2 = DecoderBlock(in_channels=128, skip_channels=64, out_channels=64)
        self.dec1 = DecoderBlock(in_channels=64, skip_channels=64, out_channels=32)

        self.final_up = nn.ConvTranspose2d(32, 16, kernel_size=2, stride=2)
        self.final_conv = DoubleConv(16, 16)
        self.head = nn.Conv2d(16, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x0 = self.relu(self.bn1(self.conv1(x)))
        x_pool = self.maxpool(x0)
        x1 = self.layer1(x_pool)
        x2 = self.layer2(x1)
        x3 = self.layer3(x2)
        x4 = self.layer4(x3)

        d4 = self.dec4(x4, x3)
        d3 = self.dec3(d4, x2)
        d2 = self.dec2(d3, x1)
        d1 = self.dec1(d2, x0)

        up0 = self.final_up(d1)
        feat = self.final_conv(up0)
        logits = self.head(feat)
        return logits


class SoftDiceLoss(nn.Module):
    """Soft Dice Loss operating directly on logits."""
    def __init__(self, smooth: float = 1.0) -> None:
        super().__init__()
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if logits.shape != targets.shape:
            if logits.dim() == 4 and targets.dim() == 3:
                targets = targets.unsqueeze(1)
            elif logits.dim() == 3 and targets.dim() == 4:
                logits = logits.unsqueeze(1)

        probs = torch.sigmoid(logits)
        b = probs.shape[0]
        probs_flat = probs.view(b, -1)
        targets_flat = targets.view(b, -1).to(dtype=probs.dtype)

        intersection = torch.sum(probs_flat * targets_flat, dim=-1)
        denominator = torch.sum(probs_flat, dim=-1) + torch.sum(targets_flat, dim=-1)
        dice = (2.0 * intersection + self.smooth) / (denominator + self.smooth)
        return (1.0 - dice).mean()


class CombinedBCEAndDiceLoss(nn.Module):
    """Canonical loss: 0.5 * BCEWithLogits + 0.5 * SoftDice."""
    def __init__(self, bce_weight: float = 0.5, dice_weight: float = 0.5, smooth: float = 1.0) -> None:
        super().__init__()
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight
        self.bce = nn.BCEWithLogitsLoss()
        self.dice = SoftDiceLoss(smooth=smooth)

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if logits.shape != targets.shape:
            if logits.dim() == 4 and targets.dim() == 3:
                targets = targets.unsqueeze(1)
            elif logits.dim() == 3 and targets.dim() == 4:
                logits = logits.unsqueeze(1)
        targets = targets.to(dtype=logits.dtype)
        return self.bce_weight * self.bce(logits, targets) + self.dice_weight * self.dice(logits, targets)


# =====================================================================
# 3. PROBE EXECUTION HARNESS
# =====================================================================

def run_probe(target_label: str = "LOCAL") -> Dict[str, Any]:
    """Execute complete non-destructive capability and smoke probe."""
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    total_ram, avail_ram = get_ram_info()

    report: Dict[str, Any] = {
        "probe_metadata": {
            "target": target_label.upper(),
            "timestamp_utc": started_at,
            "status": "RUNNING",
            "probe_script_version": "2.0.0-gate3",
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
        "packages": {},
        "filesystem": {},
        "safe_smoke_tests": {
            "performed": False,
            "all_passed": False,
            "checks": {},
        },
        "ocean_sentinel_framework_test": {
            "performed": False,
            "all_passed": False,
            "checks": {},
        },
        "errors": [],
    }

    # 1. Package compatibility checks
    packages_to_check = [
        "torch", "torchvision", "torchaudio", "numpy", "scipy",
        "albumentations", "rasterio", "cv2", "PIL", "yaml", "tqdm"
    ]
    for pkg in packages_to_check:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "INSTALLED")
            report["packages"][pkg] = {"status": "AVAILABLE", "version": str(ver)}
        except ImportError:
            report["packages"][pkg] = {"status": "NOT_INSTALLED", "version": None}
        except Exception as ex:
            report["packages"][pkg] = {"status": "ERROR", "error": str(ex)}

    # 2. Filesystem checks
    fs_targets = ["/kaggle/working", "/kaggle/input", "/kaggle/temp", ".", "temp"]
    for path_str in fs_targets:
        p = Path(path_str)
        if p.exists() or path_str.startswith("/kaggle"):
            fs_info: Dict[str, Any] = {
                "exists": p.exists(),
                "is_dir": p.is_dir() if p.exists() else False,
            }
            if p.exists():
                try:
                    usage = shutil.disk_usage(str(p))
                    fs_info["total_gb"] = round(usage.total / (1024**3), 2)
                    fs_info["used_gb"] = round(usage.used / (1024**3), 2)
                    fs_info["free_gb"] = round(usage.free / (1024**3), 2)
                except Exception as e:
                    fs_info["disk_usage_error"] = str(e)

                # Writable test
                test_file = p / "_probe_fs_write_test.tmp"
                try:
                    with open(test_file, "w", encoding="ascii") as f:
                        f.write("OK")
                    test_file.unlink()
                    fs_info["writable"] = True
                except Exception:
                    fs_info["writable"] = False
            report["filesystem"][path_str] = fs_info

    # 3. PyTorch runtime and CUDA checks
    try:
        import torchvision
        report["pytorch"] = {
            "torch_version": torch.__version__,
            "torch_cuda_version": torch.version.cuda,
            "torchvision_version": torchvision.__version__,
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

            # 4. Basic Smoke Tests
            report["safe_smoke_tests"]["performed"] = True
            smoke_checks: Dict[str, Any] = {}
            smoke_all_ok = True

            # Check 1: Allocation
            t0 = time.perf_counter()
            try:
                t = torch.zeros((4, 4), device="cuda", dtype=torch.float32)
                torch.cuda.synchronize()
                elapsed_alloc = (time.perf_counter() - t0) * 1000
                smoke_checks["tiny_tensor_allocation"] = {
                    "status": "PASS",
                    "shape": list(t.shape),
                    "device": str(t.device),
                    "elapsed_ms": round(elapsed_alloc, 3),
                }
            except Exception as e:
                smoke_all_ok = False
                smoke_checks["tiny_tensor_allocation"] = {"status": "FAIL", "error": str(e)}

            # Check 2: MatMul
            t0 = time.perf_counter()
            try:
                a = torch.randn((64, 64), device="cuda", dtype=torch.float32)
                b = torch.randn((64, 64), device="cuda", dtype=torch.float32)
                c = torch.matmul(a, b)
                torch.cuda.synchronize()
                elapsed_mm = (time.perf_counter() - t0) * 1000
                smoke_checks["tiny_matmul"] = {
                    "status": "PASS",
                    "shape": list(c.shape),
                    "elapsed_ms": round(elapsed_mm, 3),
                }
            except Exception as e:
                smoke_all_ok = False
                smoke_checks["tiny_matmul"] = {"status": "FAIL", "error": str(e)}

            # Check 3: Conv2D
            t0 = time.perf_counter()
            try:
                conv = nn.Conv2d(2, 64, kernel_size=7, stride=2, padding=3, bias=False).cuda()
                x = torch.randn((1, 2, 128, 128), device="cuda", dtype=torch.float32)
                out = conv(x)
                torch.cuda.synchronize()
                elapsed_conv = (time.perf_counter() - t0) * 1000
                smoke_checks["tiny_conv2d"] = {
                    "status": "PASS",
                    "input_shape": list(x.shape),
                    "output_shape": list(out.shape),
                    "elapsed_ms": round(elapsed_conv, 3),
                }
            except Exception as e:
                smoke_all_ok = False
                smoke_checks["tiny_conv2d"] = {"status": "FAIL", "error": str(e)}

            # Check 4: AMP FP16
            t0 = time.perf_counter()
            try:
                with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                    out_amp = conv(x)
                torch.cuda.synchronize()
                elapsed_amp = (time.perf_counter() - t0) * 1000
                smoke_checks["tiny_amp_fp16"] = {
                    "status": "PASS",
                    "dtype": str(out_amp.dtype),
                    "elapsed_ms": round(elapsed_amp, 3),
                }
            except Exception as e:
                smoke_all_ok = False
                smoke_checks["tiny_amp_fp16"] = {"status": "FAIL", "error": str(e)}

            report["safe_smoke_tests"]["all_passed"] = smoke_all_ok
            report["safe_smoke_tests"]["checks"] = smoke_checks

            # 5. Ocean Sentinel Synthetic Framework Smoke Test
            report["ocean_sentinel_framework_test"]["performed"] = True
            framework_checks: Dict[str, Any] = {}
            framework_all_ok = True

            # Step 5.1: Model Instantiation & Parameter Verification
            t0 = time.perf_counter()
            try:
                torch.cuda.reset_peak_memory_stats(0)
                model = ResNet34UNet(
                    in_channels=2,
                    num_classes=1,
                    pretrained=False,
                    adaptation_method="slice_variance_scaled",
                ).cuda()
                param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
                elapsed_inst = (time.perf_counter() - t0) * 1000
                
                expected_params = 24346305
                param_match = (param_count == expected_params)
                if not param_match:
                    framework_all_ok = False
                
                framework_checks["model_instantiation"] = {
                    "status": "PASS" if param_match else "FAIL",
                    "model_class": "ResNet34UNet",
                    "in_channels": 2,
                    "num_classes": 1,
                    "first_conv_adaptation": "slice_variance_scaled",
                    "parameter_count": param_count,
                    "expected_parameter_count": expected_params,
                    "parameter_match": param_match,
                    "elapsed_ms": round(elapsed_inst, 3),
                }
            except Exception as e:
                framework_all_ok = False
                framework_checks["model_instantiation"] = {"status": "FAIL", "error": str(e)}

            # Step 5.2: Synthetic Forward Pass (AMP FP16, [1, 2, 512, 512])
            t0 = time.perf_counter()
            try:
                x_synth = torch.randn((1, 2, 512, 512), device="cuda", dtype=torch.float32)
                with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                    logits = model(x_synth)
                torch.cuda.synchronize()
                elapsed_fwd = (time.perf_counter() - t0) * 1000

                expected_shape = [1, 1, 512, 512]
                shape_match = (list(logits.shape) == expected_shape)
                if not shape_match:
                    framework_all_ok = False

                framework_checks["synthetic_forward_pass"] = {
                    "status": "PASS" if shape_match else "FAIL",
                    "input_shape": list(x_synth.shape),
                    "output_shape": list(logits.shape),
                    "expected_shape": expected_shape,
                    "shape_match": shape_match,
                    "output_dtype": str(logits.dtype),
                    "elapsed_ms": round(elapsed_fwd, 3),
                }
            except Exception as e:
                framework_all_ok = False
                framework_checks["synthetic_forward_pass"] = {"status": "FAIL", "error": str(e)}

            # Step 5.3: Loss Computation (CombinedBCEAndDiceLoss)
            t0 = time.perf_counter()
            try:
                criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0)
                y_synth = torch.randint(0, 2, (1, 1, 512, 512), device="cuda", dtype=torch.float32)
                with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                    loss = criterion(logits, y_synth)
                torch.cuda.synchronize()
                elapsed_loss = (time.perf_counter() - t0) * 1000

                loss_val = float(loss.item())
                loss_valid = (not math.isnan(loss_val)) and (not math.isinf(loss_val)) and (loss_val > 0)
                if not loss_valid:
                    framework_all_ok = False

                framework_checks["loss_computation"] = {
                    "status": "PASS" if loss_valid else "FAIL",
                    "loss_function": "CombinedBCEAndDiceLoss(0.5 BCE + 0.5 SoftDice)",
                    "loss_value": round(loss_val, 6),
                    "loss_valid": loss_valid,
                    "elapsed_ms": round(elapsed_loss, 3),
                }
            except Exception as e:
                framework_all_ok = False
                framework_checks["loss_computation"] = {"status": "FAIL", "error": str(e)}

            # Step 5.4: Autograd Backward & Optimizer Step
            t0 = time.perf_counter()
            try:
                optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)
                scaler = torch.amp.GradScaler('cuda')
                optimizer.zero_grad()
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
                torch.cuda.synchronize()
                elapsed_opt = (time.perf_counter() - t0) * 1000

                peak_vram_bytes = torch.cuda.max_memory_allocated(0)
                peak_vram_mb = round(peak_vram_bytes / (1024 * 1024), 2)

                framework_checks["autograd_and_optimizer_step"] = {
                    "status": "PASS",
                    "optimizer": "AdamW(lr=1e-4, weight_decay=1e-2)",
                    "grad_scaler": "torch.amp.GradScaler('cuda')",
                    "backward_pass": "SUCCESS",
                    "optimizer_step": "SUCCESS",
                    "peak_vram_allocated_mb": peak_vram_mb,
                    "elapsed_ms": round(elapsed_opt, 3),
                }
            except Exception as e:
                framework_all_ok = False
                framework_checks["autograd_and_optimizer_step"] = {"status": "FAIL", "error": str(e)}

            report["ocean_sentinel_framework_test"]["all_passed"] = framework_all_ok
            report["ocean_sentinel_framework_test"]["checks"] = framework_checks

        else:
            report["safe_smoke_tests"]["performed"] = False
            report["safe_smoke_tests"]["reason"] = "CUDA is not available on this system."
            report["ocean_sentinel_framework_test"]["performed"] = False
            report["ocean_sentinel_framework_test"]["reason"] = "CUDA is not available on this system."

        report["probe_metadata"]["status"] = "COMPLETE"

    except Exception as e:
        report["probe_metadata"]["status"] = "ERROR"
        report["errors"].append(str(e))

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Ocean Sentinel Live Capability & Framework Smoke Probe")
    is_kaggle = os.path.exists("/kaggle")
    default_target = "KAGGLE" if is_kaggle else "LOCAL"
    default_output = Path("/kaggle/working/capability_probe_results.json") if is_kaggle else Path("capability_probe_results.json")

    parser.add_argument(
        "--target",
        type=str,
        default=default_target,
        choices=["LOCAL", "KAGGLE"],
        help="Execution environment label (LOCAL or KAGGLE)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help="Path to save output JSON",
    )
    args = parser.parse_args()

    print("=================================================================")
    print(f"=== Ocean Sentinel Capability & Framework Smoke Probe [{args.target.upper()}] ===")
    print("=================================================================")
    results = run_probe(target_label=args.target)

    # Print summary
    print(f"Target:            {results['probe_metadata']['target']}")
    print(f"Timestamp UTC:     {results['probe_metadata']['timestamp_utc']}")
    print(f"OS:                {results['system']['os']} {results['system']['os_release']} ({results['system']['platform_string']})")
    print(f"Python:            {results['system']['python_version'].split()[0]} ({results['system']['python_executable']})")
    print(f"CPU Cores:         {results['system']['cpu_count_logical']} logical")
    print(f"Host RAM:          {results['system']['ram_total_gb']} GB total ({results['system']['ram_available_gb']} GB free)")
    
    pt = results.get("pytorch", {})
    print(f"PyTorch:           {pt.get('torch_version', 'N/A')} (CUDA {pt.get('torch_cuda_version', 'N/A')}, cuDNN {pt.get('cudnn_version', 'N/A')})")
    print(f"Torchvision:       {pt.get('torchvision_version', 'N/A')}")
    print(f"CUDA Available:    {pt.get('cuda_available', False)}")
    
    gpu = results.get("gpu", {})
    if gpu.get("cuda_available"):
        print(f"CUDA Devices:      {gpu.get('device_count', 0)}")
        for d in gpu.get("devices", []):
            print(f"  [{d['index']}] {d['name']} | Compute Cap: {d['compute_capability']} | VRAM: {d['total_memory_mb']} MB total ({d['free_memory_mb']} MB free)")
        
        smoke = results.get("safe_smoke_tests", {})
        smoke_passed = smoke.get("all_passed", False)
        print(f"Smoke Tests:       {'ALL PASSED' if smoke_passed else 'FAILED'}")
        for k, v in smoke.get("checks", {}).items():
            print(f"  - {k}: {v.get('status')} ({v.get('elapsed_ms', 'N/A')} ms)")
        
        fw = results.get("ocean_sentinel_framework_test", {})
        fw_passed = fw.get("all_passed", False)
        print(f"Framework Test:    {'ALL PASSED' if fw_passed else 'FAILED'}")
        for k, v in fw.get("checks", {}).items():
            print(f"  - {k}: {v.get('status')} ({v.get('elapsed_ms', 'N/A')} ms)")
            if k == "model_instantiation":
                print(f"      Parameters: {v.get('parameter_count')} (Expected: {v.get('expected_parameter_count')}, Match: {v.get('parameter_match')})")
            elif k == "loss_computation":
                print(f"      Loss Value: {v.get('loss_value')}")
            elif k == "autograd_and_optimizer_step":
                print(f"      Peak VRAM:  {v.get('peak_vram_allocated_mb')} MB")
    else:
        print("GPU:               NO CUDA ACCELERATOR DETECTED")

    # Filesystem summary
    fs = results.get("filesystem", {})
    if fs:
        print("\nFilesystem Status:")
        for path, info in fs.items():
            if info.get("exists"):
                print(f"  {path:20s}: Total: {info.get('total_gb', 'N/A')} GB | Free: {info.get('free_gb', 'N/A')} GB | Writable: {info.get('writable', 'N/A')}")
            else:
                print(f"  {path:20s}: DOES NOT EXIST")

    # Packages summary
    pkgs = results.get("packages", {})
    if pkgs:
        print("\nPackage Compatibility:")
        for p, s in pkgs.items():
            print(f"  {p:15s}: {s.get('status')} ({s.get('version')})")

    # Save JSON
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="ascii") as f:
        json.dump(results, f, indent=2)
    print(f"\nStructured results saved to: {output_path}")

    # Return exit code
    if results["probe_metadata"]["status"] != "COMPLETE":
        return 1
    if gpu.get("cuda_available"):
        if not results.get("safe_smoke_tests", {}).get("all_passed", False):
            return 2
        if not results.get("ocean_sentinel_framework_test", {}).get("all_passed", False):
            return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
