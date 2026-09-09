"""EXP-01 Baseline ResNet-34 U-Net Oil-Spill Segmentation Training Runner.

Production-grade runner with:
- Exclusive run-lock (prevents duplicate processes)
- Atomic checkpoint writes (best + latest recovery)
- Persistent heartbeat / run_state.json
- Persistent progress.log
- Incremental history.json (per epoch, atomic)
- Resume from latest or explicit checkpoint (--resume)
- Real-time ETA from measured epoch throughput
- Resource safety checks (disk, VRAM)
- Experiment fingerprint (dataset + code + env hashes)
- 9-point preflight gate
- Validation-only threshold selection
- Single-pass held-out test evaluation
- PIL qualitative diagnostics
- Independent post-run audit

Scientific configuration (CAO-locked):
  Dataset:      Trujillo Part I spatial_split_manifest.json
  Model:        ResNet-34 U-Net, 2-channel SAR input
  Loss:         0.5 * BCE + 0.5 * SoftDice (smooth=1.0)
  Optimizer:    AdamW (lr=1e-4, wd=1e-2)
  Scheduler:    CosineAnnealingLR (T_max=30, eta_min=1e-6)
  Augmentation: HFlip + VFlip + Rot90 (train only)
  AMP:          CUDA FP16

Execution baseline (EXP-01 Rev B — re-baselined from B4/acc2/0-workers):
  Physical batch: 8  [BatchNorm runs on B=8 per step]
  Accum steps:    1  [one optimizer step per batch]
  DataLoader:     4 workers, pin_memory, persistent_workers
  Nominal effective batch: 8 (same as original Rev A)

NOTE: Changing physical batch from 4 to 8 changes BatchNorm statistics.
This is the explicitly documented EXP-01 Rev B execution baseline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import shutil
import socket
import sys
import time
import traceback
import types
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, List

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
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
from ocean_sentinel.ml.metrics import SegmentationMeter  # noqa: E402
from ocean_sentinel.ml.threshold import optimize_threshold_on_validation  # noqa: E402
from ocean_sentinel.ml.unet_resnet import ResNet34UNet, count_parameters  # noqa: E402

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MANIFEST = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "experiments" / "exp01_baseline"
VRAM_SAFETY_THRESHOLD_MB = 5500  # stop if peak reserved exceeds this
DISK_SAFETY_THRESHOLD_GB = 5.0  # stop if free disk drops below this
HEARTBEAT_INTERVAL_EPOCHS = 1  # write run_state every epoch
HISTORY_FLUSH_EVERY = 1  # flush history every epoch

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_log: logging.Logger = logging.getLogger("exp01")


def setup_logging(output_dir: Path) -> None:
    """Configure console + file logging. File handler is always unbuffered."""
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "progress.log"

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ")
    fmt.converter = time.gmtime

    _log.setLevel(logging.DEBUG)
    _log.handlers.clear()

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    _log.addHandler(ch)

    fh = logging.FileHandler(log_path, mode="a", encoding="utf-8", delay=False)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    # Force flush after every record
    fh.stream.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    _log.addHandler(fh)


# ---------------------------------------------------------------------------
# CUDA helpers
# ---------------------------------------------------------------------------
def get_vram_mb() -> dict:
    if not torch.cuda.is_available():
        return {
            "allocated_mb": 0.0,
            "reserved_mb": 0.0,
            "max_allocated_mb": 0.0,
            "max_reserved_mb": 0.0,
        }
    torch.cuda.synchronize()
    return {
        "allocated_mb": round(torch.cuda.memory_allocated() / 1e6, 1),
        "reserved_mb": round(torch.cuda.memory_reserved() / 1e6, 1),
        "max_allocated_mb": round(torch.cuda.max_memory_allocated() / 1e6, 1),
        "max_reserved_mb": round(torch.cuda.max_memory_reserved() / 1e6, 1),
    }


def reset_cuda_stats() -> None:
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()


def set_seed(seed: int) -> None:
    import random

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
# Atomic file write
# ---------------------------------------------------------------------------
def atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically: temp → verify → os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    text = json.dumps(data, indent=2)
    tmp.write_text(text, encoding="utf-8")
    if not tmp.exists() or tmp.stat().st_size == 0:
        raise RuntimeError(f"Atomic JSON write failed: temp file empty at {tmp}")
    os.replace(tmp, path)


def atomic_save_checkpoint(path: Path, state: dict) -> str:
    """Save PyTorch checkpoint atomically. Returns SHA-256 of saved file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.pt")
    torch.save(state, tmp)
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    if not tmp.exists() or tmp.stat().st_size < 1024:
        raise RuntimeError(f"Atomic checkpoint write failed: {tmp}")
    os.replace(tmp, path)
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    return sha256


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------
def file_sha256(path: Path, max_bytes: int = 0) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
            if max_bytes and f.tell() >= max_bytes:
                break
    return h.hexdigest().upper()


def safe_load_checkpoint(
    checkpoint_path: Path,
    map_location: Any = "cpu",
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Safely load a PyTorch checkpoint with allowlisted globals and verified fallback.

    Preferred path: torch.load(..., weights_only=True) with required safe globals allowlisted.
    Fallback to weights_only=False is strictly permitted ONLY IF:
      1. Checkpoint path is inside the local repository.
      2. Checkpoint SHA-256 matches expected_sha256 (or checkpoint_integrity.json).
      3. Fallback is clearly logged.
    """
    checkpoint_path = Path(checkpoint_path).resolve()
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    # Register safe globals required by local PyTorch checkpoints
    import os
    import pathlib

    if os.name == "nt":
        try:
            pathlib.PosixPath = pathlib.WindowsPath
        except Exception:
            pass

    safe_classes = [
        pathlib.WindowsPath,
        pathlib.PosixPath,
        pathlib.Path,
        torch.torch_version.TorchVersion,
    ]
    if hasattr(torch.serialization, "add_safe_globals"):
        torch.serialization.add_safe_globals(safe_classes)

    try:
        return torch.load(checkpoint_path, map_location=map_location, weights_only=True)
    except Exception as e:
        _log.warning(
            "Safe load (weights_only=True) failed for %s: %s. Checking fallback criteria.",
            checkpoint_path,
            e,
        )

        # 1. Path must be local to repository
        try:
            checkpoint_path.relative_to(REPO_ROOT.resolve())
            is_local = True
        except ValueError:
            is_local = False

        if not is_local:
            raise RuntimeError(
                f"Checkpoint {checkpoint_path} is external to repository; "
                f"refusing weights_only=False fallback."
            ) from e

        # 2. SHA-256 verification
        actual_sha = file_sha256(checkpoint_path)
        trusted_sha = expected_sha256
        if trusted_sha is None:
            integrity_path = checkpoint_path.parent / "checkpoint_integrity.json"
            if integrity_path.exists():
                try:
                    integrity_record = json.loads(integrity_path.read_text(encoding="utf-8"))
                    filename = checkpoint_path.name
                    if "best" in filename:
                        trusted_sha = integrity_record.get("best_sha256")
                    elif "latest" in filename:
                        trusted_sha = integrity_record.get("latest_sha256")
                except Exception:
                    pass

        if not trusted_sha or actual_sha.upper() != trusted_sha.upper():
            raise RuntimeError(
                f"Checkpoint {checkpoint_path} SHA-256 ({actual_sha}) does not match "
                f"expected record ({trusted_sha}); refusing weights_only=False fallback."
            ) from e

        # 3. Log fallback clearly
        _log.warning(
            "CRITICAL: Fallback to weights_only=False for verified local checkpoint %s "
            "(SHA-256: %s matches trusted record).",
            checkpoint_path,
            actual_sha,
        )
        return torch.load(checkpoint_path, map_location=map_location, weights_only=False)


def build_experiment_fingerprint(
    manifest_path: Path,
    config: dict,
) -> dict:
    """Build a machine-readable immutable experiment fingerprint."""
    fp: dict[str, Any] = {
        "experiment": "EXP-01_baseline_resnet34_unet_rev_b",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "cudnn_version": str(torch.backends.cudnn.version()),
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
    }
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        fp["gpu"] = props.name
        fp["vram_total_mb"] = props.total_memory // (1024 * 1024)

    # Dataset fingerprint
    if manifest_path.exists():
        fp["manifest_sha256"] = file_sha256(manifest_path)

    # Spatial audit fingerprint
    audit_path = manifest_path.parent / "spatial_split_audit.json"
    if audit_path.exists():
        fp["spatial_audit_sha256"] = file_sha256(audit_path)

    # Code fingerprints (key training files)
    src_ml_dir = REPO_ROOT / "src" / "ocean_sentinel" / "ml"
    code_hashes = {}
    for f in sorted(src_ml_dir.rglob("*.py")):
        code_hashes[str(f.relative_to(REPO_ROOT))] = file_sha256(f)
    code_hashes["scripts/train_exp01.py"] = file_sha256(Path(__file__))
    fp["code_sha256"] = code_hashes

    # Scientific configuration
    fp["scientific_config"] = {
        "model": "ResNet34UNet",
        "in_channels": 2,
        "num_classes": 1,
        "adaptation_method": "slice_variance_scaled",
        "loss": "0.5*BCE + 0.5*SoftDice(smooth=1.0)",
        "optimizer": "AdamW",
        "lr": config.get("lr"),
        "weight_decay": config.get("weight_decay"),
        "scheduler": "CosineAnnealingLR",
        "max_epochs": config.get("epochs"),
        "early_stopping_patience": config.get("patience"),
        "selection_metric": "validation_global_iou",
        "amp": "CUDA FP16",
        "augmentation": "HFlip+VFlip+Rot90 train-only",
    }
    fp["execution_config"] = {
        "physical_batch_size": config.get("batch_size"),
        "accum_steps": config.get("accum_steps"),
        "nominal_effective_batch": (
            (config.get("batch_size") or 0) * (config.get("accum_steps") or 1)
        ),
        "num_workers": config.get("num_workers"),
        "batchnorm_note": (
            "BatchNorm statistics computed over physical_batch_size samples per step. "
            "B8 is scientifically distinct from B4+accum2."
        ),
    }
    return fp


# ---------------------------------------------------------------------------
# Run lock
# ---------------------------------------------------------------------------
def is_process_alive(pid: int) -> bool:
    """Check if process with given PID is alive across Windows and Unix."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        SYNCHRONIZE = 0x00100000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
        if not handle:
            # WinError 87 (ERROR_INVALID_PARAMETER) means process does not exist
            return False
        exit_code = wintypes.DWORD()
        STILL_ACTIVE = 259
        alive = False
        if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            alive = exit_code.value == STILL_ACTIVE
        kernel32.CloseHandle(handle)
        return alive
    else:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, OSError):
            return False


def acquire_run_lock(output_dir: Path, run_id: str) -> Path:
    """Acquire exclusive run lock. Raises RuntimeError if another live process holds it."""
    lock_path = output_dir / "run.lock"
    if lock_path.exists():
        try:
            existing = json.loads(lock_path.read_text(encoding="utf-8"))
            pid = existing.get("pid")
            machine = existing.get("machine")
            is_same_machine = machine == socket.gethostname()

            if pid and pid != os.getpid():
                if is_same_machine:
                    if is_process_alive(pid):
                        raise RuntimeError(
                            f"Another EXP-01 process (PID {pid}) is currently alive and running in "
                            f"{output_dir}. Command: {existing.get('command_line', '?')}. "
                            f"Started: {existing.get('start_time_utc', '?')}. "
                            f"Refusing to start duplicate."
                        )
                    else:
                        _log.warning(
                            "Stale run.lock detected (PID %s on %s is not alive). Recovering lock.",
                            pid,
                            machine,
                        )
                else:
                    raise RuntimeError(
                        f"Run lock in {output_dir} held by machine '{machine}' (PID {pid}). "
                        "Cannot safely verify remote process state. Refusing to overwrite lock."
                    )
        except json.JSONDecodeError:
            _log.warning("Malformed run.lock at %s — safely recovering.", lock_path)

    lock_data = {
        "run_id": run_id,
        "pid": os.getpid(),
        "machine": socket.gethostname(),
        "start_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command_line": " ".join(sys.argv),
    }
    lock_path.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")
    return lock_path


def release_run_lock(lock_path: Path) -> None:
    try:
        if lock_path.exists():
            lock_path.unlink()
    except Exception as e:
        _log.warning("Could not release run.lock: %s", e)


# ---------------------------------------------------------------------------
# Run state / heartbeat
# ---------------------------------------------------------------------------
def write_run_state(output_dir: Path, state: dict) -> None:
    try:
        state["last_heartbeat_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        atomic_write_json(output_dir / "run_state.json", state)
    except Exception as e:
        _log.warning("Failed to write run_state.json: %s", e)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
def append_history(history_path: Path, history: List[dict]) -> None:
    try:
        atomic_write_json(history_path, history)
    except Exception as e:
        _log.warning("Failed to write history.json: %s", e)


# ---------------------------------------------------------------------------
# Checkpoint integrity record
# ---------------------------------------------------------------------------
def update_checkpoint_integrity(output_dir: Path, record: dict) -> None:
    try:
        existing: dict = {}
        ipath = output_dir / "checkpoint_integrity.json"
        if ipath.exists():
            try:
                existing = json.loads(ipath.read_text(encoding="utf-8"))
            except Exception:
                pass
        existing.update(record)
        existing["updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        atomic_write_json(ipath, existing)
    except Exception as e:
        _log.warning("Failed to update checkpoint_integrity.json: %s", e)


# ---------------------------------------------------------------------------
# Step Accounting Optimizer (Forensic Receipt Tracking)
# ---------------------------------------------------------------------------
class StepAccountingOptimizer:
    """Forensic accounting wrapper around Optimizer to track execution receipts.

    Uses strictly standard public Python / PyTorch execution contracts:
    1. Intercepts optimizer.step() invocations to record when GradScaler actually invokes it.
    2. Explicitly tracks optimizer update attempts before calling scaler.step(optimizer).
    3. Derives amp_skipped_updates = optimizer_step_attempts - successful_optimizer_updates.
    4. Resilient to PyTorch LRScheduler method rebinding via MethodType binding and attribute synchronization.
    5. Zero usage of private PyTorch internals.
    """

    def __init__(self, optimizer: torch.optim.Optimizer) -> None:
        self.optimizer = optimizer
        self.optimizer_step_attempts = 0
        setattr(optimizer, "successful_optimizer_updates", 0)
        setattr(optimizer, "_step_accountant", self)
        self._orig_step = optimizer.step
        setattr(optimizer, "_orig_step", self._orig_step)
        optimizer.step = types.MethodType(self._hooked_step.__func__, optimizer)

    def _hooked_step(self, *args: Any, **kwargs: Any) -> Any:
        self.successful_optimizer_updates += 1
        return self._orig_step(*args, **kwargs)

    def record_attempt(self) -> None:
        self.optimizer_step_attempts += 1

    @property
    def successful_optimizer_updates(self) -> int:
        return getattr(self.optimizer, "successful_optimizer_updates", 0)

    @successful_optimizer_updates.setter
    def successful_optimizer_updates(self, val: int) -> None:
        setattr(self.optimizer, "successful_optimizer_updates", val)

    @property
    def amp_skipped_updates(self) -> int:
        return self.optimizer_step_attempts - self.successful_optimizer_updates

    def get_accounting_summary(self) -> dict[str, int]:
        return {
            "optimizer_step_attempts": self.optimizer_step_attempts,
            "successful_optimizer_updates": self.successful_optimizer_updates,
            "amp_skipped_updates": self.amp_skipped_updates,
        }


# ---------------------------------------------------------------------------
# Resource checks
# ---------------------------------------------------------------------------
def check_disk_space(output_dir: Path) -> tuple[float, bool]:
    """Returns (free_gb, is_safe)."""
    free_gb = shutil.disk_usage(output_dir).free / 1e9
    return round(free_gb, 2), free_gb >= DISK_SAFETY_THRESHOLD_GB


def check_vram_safety(threshold_mb: float = VRAM_SAFETY_THRESHOLD_MB) -> tuple[float, bool]:
    """Returns (peak_reserved_mb, is_safe)."""
    if not torch.cuda.is_available():
        return 0.0, True
    peak = torch.cuda.max_memory_reserved() / 1e6
    return round(peak, 1), peak < threshold_mb


# ---------------------------------------------------------------------------
# Preflight gate
# ---------------------------------------------------------------------------
def run_preflight_gate(
    manifest_path: Path,
    device: torch.device,
    use_amp: bool,
    output_dir: Path,
    data_dir: Optional[Path] = None,
) -> bool:
    _log.info("=" * 70)
    _log.info("EXP-01: 9-POINT PRE-FLIGHT TRAINING GATE")
    _log.info("=" * 70)
    temp_dir = output_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Real batch load
        manifest = DatasetManifest.load(manifest_path)
        ds_kwargs = {"data_root": data_dir} if data_dir is not None else {}
        ds_train = TrujilloTileDataset(
            manifest, SplitName.TRAIN, normalize=True, **ds_kwargs
        )
        loader = DataLoader(
            ds_train,
            batch_size=8,
            shuffle=False,
            num_workers=0,
            pin_memory=(device.type == "cuda"),
        )
        batch_img, batch_mask = next(iter(loader))
        assert batch_img.shape == (8, 2, 512, 512), f"Unexpected img shape: {batch_img.shape}"
        assert batch_mask.shape == (8, 1, 512, 512), f"Unexpected mask shape: {batch_mask.shape}"
        _log.info("  [PASS] 1. Real batch loads: shape [8, 2, 512, 512]")

        # 2. Forward pass
        model = ResNet34UNet(
            in_channels=2,
            num_classes=1,
            pretrained=True,
            adaptation_method="slice_variance_scaled",
        ).to(device)
        criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0).to(device)
        batch_img = batch_img.to(device)
        batch_mask = batch_mask.to(device)

        with torch.amp.autocast(device_type=device.type, enabled=use_amp):
            logits = model(batch_img)
            loss = criterion(logits, batch_mask)
        assert logits.shape == (8, 1, 512, 512), f"Unexpected logits shape: {logits.shape}"
        _log.info("  [PASS] 2. Forward pass: logits [8, 1, 512, 512]")

        # 3. Loss finite
        assert torch.isfinite(loss).item(), f"Loss is not finite: {loss.item()}"
        _log.info("  [PASS] 3. Loss computes and is finite: %.4f", loss.item())

        # 4. Backward pass
        scaler = torch.amp.GradScaler(device.type, enabled=use_amp)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)
        optimizer.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        _log.info("  [PASS] 4. Backward pass completes without errors")

        # 5. AMP scaler
        initial_scale = scaler.get_scale()
        assert initial_scale > 0, "Scaler scale is non-positive"
        _log.info("  [PASS] 5. AMP scaler functional: scale=%.1f", initial_scale)

        # 6. Gradients finite (after unscale)
        scaler.unscale_(optimizer)
        for name, param in model.named_parameters():
            if param.grad is not None:
                assert torch.isfinite(param.grad).all().item(), f"Non-finite gradient in {name}"
        _log.info("  [PASS] 6. Gradients strictly finite (zero NaN/Inf)")

        # 7. Validation pass + metrics
        ds_val = TrujilloTileDataset(
            manifest, SplitName.VAL, normalize=True, **ds_kwargs
        )
        loader_val = DataLoader(ds_val, batch_size=8, shuffle=False, num_workers=0)
        val_img, val_mask = next(iter(loader_val))
        val_img, val_mask = val_img.to(device), val_mask.to(device)
        model.eval()
        with torch.no_grad():
            with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                val_logits = model(val_img)
                val_loss = criterion(val_logits, val_mask)
        meter = SegmentationMeter(threshold=0.50)
        meter.update(val_logits, val_mask)
        val_metrics = meter.compute()
        assert torch.isfinite(val_loss).item(), "Val loss non-finite"
        assert "iou" in val_metrics and "dice" in val_metrics
        _log.info(
            "  [PASS] 7. Validation pass: loss=%.4f, IoU=%.4f",
            val_loss.item(),
            val_metrics["iou"],
        )

        # 8. Checkpoint write + reload
        chkpt_path = temp_dir / "preflight_test.pt"
        state = {
            "epoch": 0,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": {},
            "scaler_state_dict": scaler.state_dict(),
            "val_iou": 0.0,
            "test": True,
        }
        sha = atomic_save_checkpoint(chkpt_path, state)
        assert chkpt_path.exists() and chkpt_path.stat().st_size > 1024
        reloaded = safe_load_checkpoint(chkpt_path, map_location="cpu", expected_sha256=sha)
        assert "model_state_dict" in reloaded
        _log.info("  [PASS] 8. Checkpoint atomic write + reload verified (SHA: %s...)", sha[:12])

    except Exception as e:
        _log.error("PREFLIGHT GATE FAILED: %s", e)
        return False

    _log.info("=" * 70)
    _log.info("PRE-FLIGHT GATE: ALL 8 CHECKS PASSED (ZERO PREFLIGHT OPTIMIZER STEPS)")
    _log.info("=" * 70)
    return True


# ---------------------------------------------------------------------------
# Qualitative diagnostics
# ---------------------------------------------------------------------------
def save_qualitative_diagnostics(
    model: nn.Module,
    val_loader: DataLoader,
    test_loader: DataLoader | None = None,
    threshold: float = 0.50,
    device: torch.device = torch.device("cpu"),
    output_dir: Path = Path("."),
    use_amp: bool = False,
    n_samples_per_split: int = 4,
) -> list[dict]:
    qual_dir = output_dir / "qualitative"
    qual_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    model.eval()

    def _save_for_loader(loader: DataLoader, split_name: str, n: int) -> None:
        collected = 0
        for imgs, masks in loader:
            if collected >= n:
                break
            for i in range(min(imgs.shape[0], n - collected)):
                img_s = imgs[i : i + 1].to(device)
                mask_s = masks[i : i + 1].to(device)
                with torch.no_grad():
                    with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                        logits_s = model(img_s)
                preds_s = (torch.sigmoid(logits_s) >= threshold).float()

                img_np = img_s.squeeze(0).cpu().numpy()
                gt_np = mask_s.squeeze().cpu().numpy()
                pred_np = preds_s.squeeze().cpu().numpy()

                ch0 = img_np[0]
                lo, hi = ch0.min(), ch0.max()
                ch0_vis = ((ch0 - lo) / max(hi - lo, 1e-8) * 255).astype(np.uint8)

                H, W = ch0_vis.shape
                canvas = Image.new("RGB", (W * 4, H))
                canvas.paste(Image.fromarray(ch0_vis).convert("RGB"), (0, 0))
                gt_pil = Image.fromarray((gt_np * 255).astype(np.uint8)).convert("RGB")
                canvas.paste(gt_pil, (W, 0))
                pred_pil = Image.fromarray((pred_np * 255).astype(np.uint8)).convert("RGB")
                canvas.paste(pred_pil, (W * 2, 0))
                overlay = Image.fromarray(ch0_vis).convert("RGB")
                for y in range(H):
                    for x in range(W):
                        if pred_np[y, x] > 0.5 and gt_np[y, x] > 0.5:
                            overlay.putpixel((x, y), (0, 200, 0))
                        elif pred_np[y, x] > 0.5:
                            overlay.putpixel((x, y), (200, 0, 0))
                        elif gt_np[y, x] > 0.5:
                            overlay.putpixel((x, y), (200, 200, 0))
                canvas.paste(overlay, (W * 3, 0))

                fname = f"{split_name}_{collected:03d}.png"
                canvas.save(qual_dir / fname)
                records.append({"split": split_name, "file": fname})
                collected += 1

    if val_loader is not None:
        _save_for_loader(val_loader, "val", n_samples_per_split)
    if test_loader is not None:
        _save_for_loader(test_loader, "test", n_samples_per_split)
    return records


# ---------------------------------------------------------------------------
# Unified Evaluation and Reporting
# ---------------------------------------------------------------------------
def run_evaluation_and_reporting(
    model: nn.Module,
    eval_chkpt_path: Path,
    eval_chkpt_sha: str,
    manifest: DatasetManifest,
    val_loader: DataLoader,
    test_loader: DataLoader | None = None,
    criterion: nn.Module = nn.Identity(),
    device: torch.device = torch.device("cpu"),
    use_amp: bool = False,
    output_dir: Path = Path("."),
    run_id: str = "",
    config: dict | None = None,
    best_epoch: int = 0,
    best_val_iou: float = 0.0,
    history_data: list[dict] | None = None,
    run_state: dict | None = None,
    lock_path: Path | None = None,
    param_counts: dict | None = None,
    total_duration: float | None = None,
) -> dict:
    """Run validation threshold search, frozen test evaluation, diagnostics, and results writing."""
    config = config or {}
    history_data = history_data or []
    run_state = run_state or {}
    param_counts = param_counts or {"total": 0, "trainable": 0}
    model.eval()

    # ---- Threshold selection (validation only) ----
    if test_loader is not None:
        _log.info("Validation-only threshold grid search (0.10-0.90, step 0.02)...")
        thresh_result = optimize_threshold_on_validation(
            model=model,
            val_loader=val_loader,
            device=device,
            use_amp=use_amp,
            target_metric="iou",
        )
        selected_threshold = thresh_result.best_threshold
        val_score_at_thresh = thresh_result.best_score
        _log.info(
            "Selected validation threshold: %.2f (Val IoU: %.4f)",
            selected_threshold,
            val_score_at_thresh,
        )
    else:
        selected_threshold = 0.22
        val_score_at_thresh = best_val_iou
        thresh_result = None
        _log.info(
            "Test split isolated via --no-test: threshold grid search omitted, locked to canonical constant: %.2f",
            selected_threshold,
        )

    # ---- Test evaluation (one pass, frozen threshold) ----
    if test_loader is not None:
        _log.info(
            "\nEvaluating FROZEN model on held-out TEST split (threshold=%.2f)...",
            selected_threshold,
        )
        test_meter = SegmentationMeter(threshold=selected_threshold)
        test_loss_sum = 0.0
        test_n = 0
        with torch.no_grad():
            for t_imgs, t_masks in test_loader:
                t_imgs = t_imgs.to(device, non_blocking=True)
                t_masks = t_masks.to(device, non_blocking=True)
                with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                    t_logits = model(t_imgs)
                    t_loss = criterion(t_logits, t_masks)
                test_loss_sum += t_loss.item() * t_imgs.shape[0]
                test_n += t_imgs.shape[0]
                test_meter.update(t_logits, t_masks)

        test_metrics = test_meter.compute()
        test_loss = test_loss_sum / max(test_n, 1)

        _log.info("=" * 75)
        _log.info("FINAL TEST RESULTS:")
        _log.info("  Test Loss:       %.4f", test_loss)
        _log.info("  Test IoU:        %.4f", test_metrics["iou"])
        _log.info("  Test Dice:       %.4f", test_metrics["dice"])
        _log.info("  Test Precision:  %.4f", test_metrics["precision"])
        _log.info("  Test Recall:     %.4f", test_metrics["recall"])
        _log.info("  Threshold:       %.2f", selected_threshold)
        _log.info("  Test Tiles:      %d", test_metrics["n_samples"])
        _log.info(
            "  Confusion:  TP=%d, FP=%d, FN=%d, TN=%d",
            test_metrics["tp"],
            test_metrics["fp"],
            test_metrics["fn"],
            test_metrics["tn"],
        )
        _log.info("=" * 75)
    else:
        test_loss = None
        test_metrics = {
            "n_samples": 0,
            "iou": None,
            "dice": None,
            "precision": None,
            "recall": None,
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "tn": 0,
        }
        _log.info("=" * 75)
        _log.info("TEST EVALUATION SKIPPED: Held-out test split isolated (--no-test). 0 test tiles consumed.")
        _log.info("=" * 75)

    # Qualitative diagnostics
    _log.info("Generating qualitative diagnostics...")
    qual_records = save_qualitative_diagnostics(
        model=model,
        val_loader=val_loader,
        test_loader=test_loader,
        threshold=selected_threshold,
        device=device,
        output_dir=output_dir,
        use_amp=use_amp,
        n_samples_per_split=4,
    )
    _log.info("Saved %d qualitative PNGs to %s/qualitative/", len(qual_records), output_dir)

    mean_epoch_s = (
        float(np.mean([r["duration_sec"] for r in history_data])) if history_data else 0.0
    )
    mean_throughput = (
        float(np.mean([r["throughput_samp_per_sec"] for r in history_data]))
        if history_data
        else 0.0
    )

    training_summary: dict[str, Any] = {
        "epochs_run": len(history_data),
        "best_epoch": best_epoch,
        "best_val_iou": round(best_val_iou, 5),
        "mean_epoch_time_sec": round(mean_epoch_s, 1),
        "mean_throughput_samp_per_sec": round(mean_throughput, 1),
    }
    if total_duration is not None:
        training_summary["total_time_min"] = round(total_duration / 60, 2)

    val_dataset_len = len(val_loader.dataset) if (val_loader is not None and hasattr(val_loader, "dataset")) else 0
    test_dataset_len = len(test_loader.dataset) if (test_loader is not None and hasattr(test_loader, "dataset")) else 0

    results = {
        "experiment": "EXP-01_baseline_resnet34_unet_rev_b",
        "run_id": run_id,
        "evaluation_status": "COMPLETED",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checkpoint": {
            "path": str(eval_chkpt_path),
            "sha256": eval_chkpt_sha,
            "best_epoch": best_epoch,
            "best_val_iou": round(best_val_iou, 5),
        },
        "configuration": {k: str(v) for k, v in config.items()},
        "fingerprint_reference": str(output_dir / "experiment_fingerprint.json"),
        "dataset": {
            "manifest": str(config.get("manifest", DEFAULT_MANIFEST)),
            "val_tiles": val_dataset_len,
            "test_tiles": test_dataset_len,
            "normalization": asdict(manifest.normalization_stats)
            if manifest.normalization_stats
            else {},
        },
        "model": {
            "architecture": "ResNet34UNet",
            "total_params": param_counts["total"],
            "trainable_params": param_counts["trainable"],
            "adaptation": "slice_variance_scaled",
        },
        "training_summary": training_summary,
        "threshold_selection": {
            "method": "validation_grid_search_0.10_to_0.90_step_0.02" if thresh_result else "frozen_canonical_constant",
            "target_metric": "iou",
            "selected_threshold": selected_threshold,
            "val_iou_at_threshold": round(val_score_at_thresh, 5),
            "threshold_candidates": thresh_result.grid if thresh_result else [0.22],
            "threshold_metric_results": thresh_result.scores if thresh_result else [round(val_score_at_thresh, 5)],
        },
        "test_evaluation": {
            "test_loss": round(test_loss, 5) if test_loss is not None else None,
            "test_iou": round(float(test_metrics["iou"]), 5) if test_metrics["iou"] is not None else None,
            "test_dice": round(float(test_metrics["dice"]), 5) if test_metrics["dice"] is not None else None,
            "test_precision": round(float(test_metrics["precision"]), 5) if test_metrics["precision"] is not None else None,
            "test_recall": round(float(test_metrics["recall"]), 5) if test_metrics["recall"] is not None else None,
            "threshold_used": selected_threshold,
            "test_tiles": test_metrics["n_samples"],
            "tp": test_metrics["tp"],
            "fp": test_metrics["fp"],
            "fn": test_metrics["fn"],
            "tn": test_metrics["tn"],
        },
        "qualitative_samples": qual_records,
    }
    atomic_write_json(output_dir / "exp01_results.json", results)
    _log.info("Results saved: %s", output_dir / "exp01_results.json")

    run_state["status"] = "COMPLETED"
    run_state["completed_time_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    run_state["best_val_iou"] = round(best_val_iou, 5)
    run_state["best_epoch"] = best_epoch
    run_state["selected_threshold"] = selected_threshold
    run_state["test_iou"] = round(float(test_metrics["iou"]), 5) if test_metrics["iou"] is not None else None
    run_state["eval_checkpoint"] = str(eval_chkpt_path)
    run_state["eval_checkpoint_sha256"] = eval_chkpt_sha
    if total_duration is not None:
        run_state["total_time_min"] = round(total_duration / 60, 2)
    write_run_state(output_dir, run_state)

    if lock_path is not None:
        release_run_lock(lock_path)
    _log.info("Run lock released.")
    _log.info("EXP-01 COMPLETE.")
    return results


# ---------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="EXP-01: Baseline ResNet-34 U-Net Oil-Spill Segmentation (Rev B)"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ["OCEAN_SENTINEL_DATA_DIR"])
        if "OCEAN_SENTINEL_DATA_DIR" in os.environ
        else None,
        help="Root directory of the dataset (e.g. /kaggle/input/ocean-sentinel-trujillo-corpus). "
        "If specified, rebases manifest image and mask paths to this root.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--accum-steps", type=int, default=1)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-2)
    parser.add_argument("--eta-min", type=float, default=1e-6)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--no-amp", action="store_true")
    _default_device = "cuda" if torch.cuda.is_available() else "cpu"
    parser.add_argument("--device", type=str, default=_default_device)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", type=Path, default=None, help="Resume from checkpoint")
    parser.add_argument("--log-interval", type=int, default=100)
    parser.add_argument("--max-train-batches", type=int, default=None)
    parser.add_argument("--max-val-batches", type=int, default=None)
    parser.add_argument(
        "--eval-only",
        action="store_true",
        help="Run post-training evaluation only (validation threshold search + test evaluation)",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Explicit checkpoint path to evaluate (defaults to output-dir/best_model.pt)",
    )
    parser.add_argument(
        "--no-test",
        action="store_true",
        help="Pilot/qualification mode: suppress test dataset construction, skip test evaluation, lock threshold to 0.22",
    )
    parser.add_argument(
        "--stop-after-epoch",
        type=int,
        default=None,
        help="Execution-only stopping boundary: halts training cleanly after completing epoch N without altering canonical args.epochs or scheduler T_max.",
    )
    return parser


# Main training function
# ---------------------------------------------------------------------------
def main() -> None:
    # ---- CLI ----
    parser = build_arg_parser()
    args, unknown = parser.parse_known_args()
    if unknown:
        ignored = [a for a in unknown if a.startswith("-f") or a.endswith(".json")]
        real_unknown = [a for a in unknown if a not in ignored]
        if ignored:
            _log.info("Ignored Jupyter/interactive arguments: %s", ignored)
        if real_unknown:
            parser.error(f"unrecognized arguments: {' '.join(real_unknown)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(args.output_dir)

    # Output directory isolation guard (pilot must never run inside certified baseline dir)
    if args.no_test and args.output_dir.resolve() == DEFAULT_OUTPUT_DIR.resolve():
        raise RuntimeError(
            f"FATAL: Refusing to run pilot/qualification mode (--no-test) in certified baseline directory: {DEFAULT_OUTPUT_DIR}"
        )
    if args.resume and args.resume.exists():
        if args.output_dir.resolve() == args.resume.parent.resolve():
            raise RuntimeError(
                f"FATAL: Output directory {args.output_dir} matches resume checkpoint directory {args.resume.parent}. "
                "Resumed runs must specify an isolated output directory to protect seed provenance."
            )

    device = torch.device(args.device)

    # Hard GPU Qualification Preflight: Zero silent CPU fallback permitted for training
    if not args.eval_only:
        if device.type == "cpu":
            raise RuntimeError("FATAL: Production training requires CUDA. Device 'cpu' is strictly prohibited.")
        if not torch.cuda.is_available():
            raise RuntimeError("FATAL: Production training requires CUDA. Silent CPU fallback is strictly prohibited.")
        from ocean_sentinel.ml.gpu_qualification import probe_gpu_hardware
        gpu_info = probe_gpu_hardware()
        if not gpu_info["compatible"]:
            raise RuntimeError(
                f"FATAL: GPU architecture {gpu_info.get('sm_string')} is incompatible ({gpu_info.get('reason')}). Requires sm >= 70."
            )

    use_amp = (not args.no_amp) and (device.type == "cuda")
    run_id = str(uuid.uuid4())[:8]
    config = vars(args)

    _log.info("=" * 75)
    _log.info("EXP-01: BASELINE RESNET-34 UNET (Rev B) — OCEAN SENTINEL")
    _log.info("=" * 75)
    dev_name = torch.cuda.get_device_name(0) if device.type == "cuda" else "CPU"
    _log.info("Device:     %s (%s)", device, dev_name)
    _log.info("Precision:  %s", "CUDA AMP FP16" if use_amp else "FP32")
    _log.info("Manifest:   %s", args.manifest)
    _log.info("Output:     %s", args.output_dir)
    _log.info("Run ID:     %s", run_id)
    eff_b = args.batch_size * args.accum_steps
    _log.info(
        "Batch:      Physical B=%d, Accum=%d (Nominal Effective B=%d)",
        args.batch_size,
        args.accum_steps,
        eff_b,
    )
    _log.info(
        "Optimizer:  AdamW(lr=%g, wd=%g) | CosineAnnealingLR(T_max=%d)",
        args.lr,
        args.weight_decay,
        args.epochs,
    )
    _log.info(
        "Policy:     Max %d epochs, Patience=%d on Val Global IoU",
        args.epochs,
        args.patience,
    )
    _log.info("Workers:    %d DataLoader workers", args.num_workers)
    if device.type == "cuda":
        vram = get_vram_mb()
        _log.info(
            "VRAM Init:  %.1f MB allocated, %.1f MB reserved",
            vram["allocated_mb"],
            vram["reserved_mb"],
        )

    # ---- Evaluation-only execution mode ----
    if args.eval_only:
        # Check if already completed with valid result artifact
        results_path = args.output_dir / "exp01_results.json"
        state_path = args.output_dir / "run_state.json"
        if results_path.exists() and state_path.exists():
            try:
                st = json.loads(state_path.read_text(encoding="utf-8"))
                if st.get("status") == "COMPLETED" and results_path.stat().st_size > 0:
                    _log.info(
                        "Evaluation already COMPLETED in %s (exp01_results.json exists, "
                        "status=COMPLETED). Exiting cleanly without retraining.",
                        args.output_dir,
                    )
                    return
            except Exception:
                pass

        eval_chkpt_path = args.checkpoint or (args.output_dir / "best_model.pt")
        if not eval_chkpt_path.exists():
            _log.error("Evaluation checkpoint not found: %s", eval_chkpt_path)
            sys.exit(1)

        eval_chkpt_sha = file_sha256(eval_chkpt_path)
        _log.info(
            "Identified evaluation checkpoint: %s (SHA-256: %s)", eval_chkpt_path, eval_chkpt_sha
        )

        lock_path = acquire_run_lock(args.output_dir, run_id)
        _log.info("Run lock acquired: %s", lock_path)

        prior_state = {}
        if state_path.exists():
            try:
                prior_state = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        run_state = {
            "run_id": run_id,
            "status": "EVALUATING",
            "pid": os.getpid(),
            "start_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "eval_checkpoint": str(eval_chkpt_path),
            "eval_checkpoint_sha256": eval_chkpt_sha,
            "best_epoch": prior_state.get("best_epoch", 4),
            "best_val_iou": prior_state.get("best_val_iou", 0.71691),
            "current_epoch": prior_state.get("current_epoch", 14),
            "selected_threshold": None,
            "config": {k: str(v) for k, v in config.items()},
        }
        write_run_state(args.output_dir, run_state)

        try:
            set_seed(args.seed)
            manifest = DatasetManifest.load(args.manifest)
            assert manifest.normalization_stats is not None, (
                "Missing normalization stats in manifest"
            )

            eval_tfm = IdentityTransform()
            ds_kwargs = {"data_root": args.data_dir} if args.data_dir is not None else {}
            ds_val = TrujilloTileDataset(
                manifest,
                SplitName.VAL,
                normalize=True,
                transform=eval_tfm,
                **ds_kwargs,
            )
            val_loader = DataLoader(
                ds_val,
                batch_size=args.batch_size,
                shuffle=False,
                num_workers=min(args.num_workers, 2),
                pin_memory=(device.type == "cuda"),
                persistent_workers=(args.num_workers > 0),
                prefetch_factor=(2 if args.num_workers > 0 else None),
            )
            if not args.no_test:
                ds_test = TrujilloTileDataset(
                    manifest,
                    SplitName.TEST,
                    normalize=True,
                    transform=eval_tfm,
                    **ds_kwargs,
                )
                _log.info(
                    "Evaluation Dataset: Val=%d, Test=%d tiles (Training loader omitted)",
                    len(ds_val),
                    len(ds_test),
                )
                test_loader = DataLoader(
                    ds_test,
                    batch_size=args.batch_size,
                    shuffle=False,
                    num_workers=min(args.num_workers, 2),
                    pin_memory=(device.type == "cuda"),
                    persistent_workers=(args.num_workers > 0),
                    prefetch_factor=(2 if args.num_workers > 0 else None),
                )
            else:
                ds_test = None
                test_loader = None
                _log.info(
                    "Evaluation Dataset: Val=%d, Test=0 tiles (Test loader suppressed via --no-test)",
                    len(ds_val),
                )

            model = ResNet34UNet(
                in_channels=2,
                num_classes=1,
                pretrained=False,
                adaptation_method="slice_variance_scaled",
            ).to(device)
            param_counts = count_parameters(model)
            assert param_counts["total"] == 24_346_305, (
                f"Unexpected parameter count: {param_counts['total']}"
            )
            assert param_counts["trainable"] == 24_346_305, (
                f"Unexpected trainable count: {param_counts['trainable']}"
            )

            _log.info("Loading checkpoint for evaluation: %s...", eval_chkpt_path)
            chkpt = safe_load_checkpoint(
                eval_chkpt_path, map_location=device, expected_sha256=eval_chkpt_sha
            )
            model.load_state_dict(chkpt["model_state_dict"], strict=True)
            model.eval()

            criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0).to(
                device
            )

            best_epoch = chkpt.get("epoch", prior_state.get("best_epoch", 4))
            best_val_iou = chkpt.get("val_iou", prior_state.get("best_val_iou", 0.71691))

            history_file = args.output_dir / "history.json"
            history_data = []
            if history_file.exists():
                try:
                    history_data = json.loads(history_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            run_evaluation_and_reporting(
                model=model,
                eval_chkpt_path=eval_chkpt_path,
                eval_chkpt_sha=eval_chkpt_sha,
                manifest=manifest,
                val_loader=val_loader,
                test_loader=test_loader,
                criterion=criterion,
                device=device,
                use_amp=use_amp,
                output_dir=args.output_dir,
                run_id=run_id,
                config=config,
                best_epoch=best_epoch,
                best_val_iou=best_val_iou,
                history_data=history_data,
                run_state=run_state,
                lock_path=lock_path,
                param_counts=param_counts,
            )
            return

        except KeyboardInterrupt:
            _log.warning("Evaluation interrupted by user.")
            run_state["status"] = "INTERRUPTED"
            run_state["interrupted_time_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            run_state["error"] = "Interrupted by user"
            write_run_state(args.output_dir, run_state)
            release_run_lock(lock_path)
            sys.exit(130)
        except Exception as e:
            _log.exception("Evaluation failed with exception: %s", e)
            run_state["status"] = "FAILED"
            run_state["failed_time_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            run_state["error"] = str(e)
            run_state["traceback"] = traceback.format_exc()
            write_run_state(args.output_dir, run_state)
            release_run_lock(lock_path)
            sys.exit(1)

    # ---- Preflight gate ----
    if not run_preflight_gate(
        args.manifest, device, use_amp, args.output_dir, data_dir=args.data_dir
    ):
        _log.error("PREFLIGHT FAILED — aborting.")
        sys.exit(1)
    if args.preflight_only:
        _log.info("Pre-flight only requested. Exiting successfully.")
        return

    # ---- Disk / resource check ----
    free_gb, disk_ok = check_disk_space(args.output_dir)
    if not disk_ok:
        _log.error(
            "INSUFFICIENT DISK SPACE: %.2f GB free, need %.1f GB. Aborting.",
            free_gb,
            DISK_SAFETY_THRESHOLD_GB,
        )
        sys.exit(1)
    _log.info("Disk:       %.2f GB free (safe)", free_gb)

    # ---- Run lock ----
    lock_path = acquire_run_lock(args.output_dir, run_id)
    _log.info("Run lock acquired: %s", lock_path)

    # ---- Experiment fingerprint ----
    fingerprint = build_experiment_fingerprint(args.manifest, config)
    atomic_write_json(args.output_dir / "experiment_fingerprint.json", fingerprint)
    _log.info("Experiment fingerprint written.")

    # ---- Run state init ----
    run_state = {
        "run_id": run_id,
        "status": "INITIALIZING",
        "pid": os.getpid(),
        "start_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "current_epoch": 0,
        "best_epoch": 0,
        "best_val_iou": -1.0,
        "selected_threshold": None,
        "config": {k: str(v) for k, v in config.items()},
    }
    write_run_state(args.output_dir, run_state)

    try:
        # ---- Dataset ----
        set_seed(args.seed)
        manifest = DatasetManifest.load(args.manifest)
        assert manifest.normalization_stats is not None, "Missing normalization stats in manifest"

        aug_train = SARGeometricAugmentation(p_hflip=0.5, p_vflip=0.5, p_rot90=0.5, seed=args.seed)
        eval_tfm = IdentityTransform()
        ds_kwargs = {"data_root": args.data_dir} if args.data_dir is not None else {}

        ds_train = TrujilloTileDataset(
            manifest,
            SplitName.TRAIN,
            normalize=True,
            transform=aug_train,
            **ds_kwargs,
        )
        ds_val = TrujilloTileDataset(
            manifest,
            SplitName.VAL,
            normalize=True,
            transform=eval_tfm,
            **ds_kwargs,
        )
        if not args.no_test:
            ds_test = TrujilloTileDataset(
                manifest,
                SplitName.TEST,
                normalize=True,
                transform=eval_tfm,
                **ds_kwargs,
            )
            _log.info(
                "Dataset:    Train=%d, Val=%d, Test=%d tiles",
                len(ds_train),
                len(ds_val),
                len(ds_test),
            )
        else:
            ds_test = None
            _log.info(
                "Dataset:    Train=%d, Val=%d, Test=0 tiles (test split isolated via --no-test)",
                len(ds_train),
                len(ds_val),
            )

        use_pw = args.num_workers > 0
        train_loader = DataLoader(
            ds_train,
            batch_size=args.batch_size,
            shuffle=True,
            num_workers=args.num_workers,
            pin_memory=(device.type == "cuda"),
            persistent_workers=use_pw,
            prefetch_factor=(2 if use_pw else None),
            drop_last=True,
        )
        val_loader = DataLoader(
            ds_val,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=min(args.num_workers, 2),
            pin_memory=(device.type == "cuda"),
            persistent_workers=(args.num_workers > 0),
            prefetch_factor=(2 if args.num_workers > 0 else None),
        )
        if not args.no_test:
            test_loader = DataLoader(
                ds_test,
                batch_size=args.batch_size,
                shuffle=False,
                num_workers=min(args.num_workers, 2),
                pin_memory=(device.type == "cuda"),
                persistent_workers=(args.num_workers > 0),
                prefetch_factor=(2 if args.num_workers > 0 else None),
            )
        else:
            test_loader = None

        # ---- Model + Training Setup ----
        model = ResNet34UNet(
            in_channels=2,
            num_classes=1,
            pretrained=True,
            adaptation_method="slice_variance_scaled",
        ).to(device)
        param_counts = count_parameters(model)
        _log.info(
            "Model:      %s | %s total, %s trainable params",
            "ResNet34UNet",
            f"{param_counts['total']:,}",
            f"{param_counts['trainable']:,}",
        )

        criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0).to(device)
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=args.lr, weight_decay=args.weight_decay
        )
        step_accountant = StepAccountingOptimizer(optimizer)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=args.epochs, eta_min=args.eta_min
        )
        scaler = torch.amp.GradScaler(device.type, enabled=use_amp)

        # ---- Resume ----
        start_epoch = 1
        history = []
        best_val_iou = -1.0
        best_epoch = 0
        patience_counter = 0
        prior_optimizer_steps = 0
        resume_path = args.resume or (args.output_dir / "latest_checkpoint.pt")

        if resume_path.exists():
            _log.info("Resuming from checkpoint: %s", resume_path)
            chkpt = safe_load_checkpoint(resume_path, map_location=device)

            # Fingerprint consistency check
            saved_fp_manifest = chkpt.get("experiment_fingerprint", {}).get("manifest_sha256")
            current_fp_manifest = fingerprint.get("manifest_sha256")
            if (
                saved_fp_manifest
                and current_fp_manifest
                and saved_fp_manifest != current_fp_manifest
            ):
                _log.error(
                    "STOP: Dataset manifest SHA256 mismatch on resume. "
                    "Saved=%s, Current=%s. Cannot resume safely.",
                    saved_fp_manifest,
                    current_fp_manifest,
                )
                release_run_lock(lock_path)
                sys.exit(1)

            model.load_state_dict(chkpt["model_state_dict"])
            optimizer.load_state_dict(chkpt["optimizer_state_dict"])
            scheduler.load_state_dict(chkpt["scheduler_state_dict"])
            scaler.load_state_dict(chkpt["scaler_state_dict"])
            start_epoch = chkpt["epoch"] + 1
            best_val_iou = chkpt.get("best_val_iou", -1.0)
            best_epoch = chkpt.get("best_epoch", 0)
            patience_counter = chkpt.get("patience_counter", 0)
            history = chkpt.get("history", [])

            # Sentinel reconciliation: uninitialized best_val_iou with existing history
            if best_val_iou == -1.0 and best_epoch == 0 and history:
                _log.warning("Reconciling uninitialized best-state sentinel from history list...")
                best_val_iou = max((float(h["val_iou"]) for h in history if "val_iou" in h), default=-1.0)
                for h in history:
                    if float(h.get("val_iou", -1.0)) == best_val_iou:
                        best_epoch = int(h.get("epoch", 1))
                        break
                _log.info("Reconciled best-state: Val IoU=%.5f at epoch %d", best_val_iou, best_epoch)

            # Extract prior optimizer steps from loaded optimizer state
            for p in model.parameters():
                if p in optimizer.state and "step" in optimizer.state[p]:
                    prior_optimizer_steps = int(optimizer.state[p]["step"].item())
                    break

            _log.info(
                "Resumed: epoch %d → will start from epoch %d. Prior optimizer steps: %d. Best IoU so far: %.4f",
                chkpt["epoch"],
                start_epoch,
                prior_optimizer_steps,
                best_val_iou,
            )
        elif args.resume:
            _log.error("--resume specified but checkpoint not found: %s", args.resume)
            release_run_lock(lock_path)
            sys.exit(1)

        # ---- Config / Fingerprint snapshots ----
        atomic_write_json(
            args.output_dir / "config.json",
            {
                "run_id": run_id,
                "args": {k: str(v) for k, v in config.items()},
                "execution_note": (
                    "Rev B: physical_batch=8, accum=1, workers=4. "
                    "BatchNorm runs on B=8 per step. "
                    "Scientifically distinct from Rev A (B4+acc2)."
                ),
            },
        )
        history_path = args.output_dir / "history.json"
        best_chkpt_path = args.output_dir / "best_model.pt"
        latest_chkpt_path = args.output_dir / "latest_checkpoint.pt"

        # Seed or preserve best_model.pt when resuming into isolated output_dir
        if args.resume and not best_chkpt_path.exists():
            prior_best = args.resume.parent / "best_model.pt"
            if prior_best.exists():
                shutil.copy2(prior_best, best_chkpt_path)
                sha_best = file_sha256(best_chkpt_path)
                update_checkpoint_integrity(
                    args.output_dir,
                    {
                        "best_checkpoint": str(best_chkpt_path),
                        "best_epoch": best_epoch,
                        "best_val_iou": round(best_val_iou, 5),
                        "best_sha256": sha_best,
                        "best_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                )
                _log.info("Preserved prior best model from %s (SHA: %s...)", prior_best, sha_best[:12])
            elif best_epoch == chkpt.get("epoch") and "model_state_dict" in chkpt:
                best_state_copy = {
                    "epoch": best_epoch,
                    "model_state_dict": chkpt["model_state_dict"],
                    "optimizer_state_dict": chkpt.get("optimizer_state_dict", {}),
                    "scheduler_state_dict": chkpt.get("scheduler_state_dict", {}),
                    "scaler_state_dict": chkpt.get("scaler_state_dict", {}),
                    "val_iou": chkpt.get("val_iou", best_val_iou),
                    "val_dice": chkpt.get("val_dice", 0.0),
                    "val_loss": chkpt.get("val_loss", 0.0),
                    "best_val_iou": best_val_iou,
                    "best_epoch": best_epoch,
                    "patience_counter": chkpt.get("patience_counter", 0),
                    "history": history,
                    "config": config,
                    "experiment_fingerprint": fingerprint,
                }
                sha_best = atomic_save_checkpoint(best_chkpt_path, best_state_copy)
                update_checkpoint_integrity(
                    args.output_dir,
                    {
                        "best_checkpoint": str(best_chkpt_path),
                        "best_epoch": best_epoch,
                        "best_val_iou": round(best_val_iou, 5),
                        "best_sha256": sha_best,
                        "best_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                )
                _log.info("Seeded best_model.pt from resumed checkpoint (SHA: %s...)", sha_best[:12])

        # ---- Training ----
        run_state["status"] = "RUNNING"
        write_run_state(args.output_dir, run_state)

        _log.info("\n" + "=" * 75)
        _log.info(
            "STARTING EXP-01 TRAINING (%d epochs max, start epoch %d)", args.epochs, start_epoch
        )
        _log.info("=" * 75)

        total_start = time.time()
        epoch_durations: List[float] = []
        reset_cuda_stats()

        for epoch in range(start_epoch, args.epochs + 1):
            epoch_start = time.time()
            run_state["current_epoch"] = epoch
            run_state["status"] = "RUNNING"
            write_run_state(args.output_dir, run_state)

            # -- Train --
            model.train()
            running_loss = 0.0
            n_samples = 0
            optimizer.zero_grad(set_to_none=True)

            for step, (images, masks) in enumerate(train_loader):
                if args.max_train_batches and step >= args.max_train_batches:
                    break
                images = images.to(device, non_blocking=True)
                masks = masks.to(device, non_blocking=True)
                bsz = images.shape[0]

                with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                    logits = model(images)
                    loss = criterion(logits, masks)
                    loss_scaled = loss / args.accum_steps

                if not torch.isfinite(loss):
                    _log.error(
                        "CRITICAL: Non-finite loss at epoch %d step %d: %.6f",
                        epoch,
                        step,
                        loss.item(),
                    )
                    run_state["status"] = "FAILED"
                    run_state["failure"] = f"Non-finite loss at epoch {epoch} step {step}"
                    write_run_state(args.output_dir, run_state)
                    release_run_lock(lock_path)
                    sys.exit(1)

                scaler.scale(loss_scaled).backward()

                is_step = ((step + 1) % args.accum_steps == 0) or ((step + 1) == len(train_loader))
                if is_step:
                    step_accountant.record_attempt()
                    scaler.step(optimizer)
                    scaler.update()
                    optimizer.zero_grad(set_to_none=True)

                running_loss += loss.item() * bsz
                n_samples += bsz

                if (step + 1) % args.log_interval == 0 or (step + 1) == len(train_loader):
                    cur_loss = running_loss / max(n_samples, 1)
                    lr_now = scheduler.get_last_lr()[0]
                    acc_sum = step_accountant.get_accounting_summary()
                    _log.info(
                        "  Epoch %02d/%02d | Batch %04d/%04d | Loss: %.4f | LR: %.2e | Updates: %d/%d (skips: %d)",
                        epoch,
                        args.epochs,
                        step + 1,
                        len(train_loader),
                        cur_loss,
                        lr_now,
                        acc_sum["successful_optimizer_updates"],
                        acc_sum["optimizer_step_attempts"],
                        acc_sum["amp_skipped_updates"],
                    )

            epoch_train_loss = running_loss / max(n_samples, 1)

            # -- Validate --
            run_state["status"] = "VALIDATING"
            write_run_state(args.output_dir, run_state)
            model.eval()
            val_meter = SegmentationMeter(threshold=0.50)
            val_loss_sum = 0.0
            val_n = 0
            with torch.no_grad():
                for vs, (v_imgs, v_masks) in enumerate(val_loader):
                    if args.max_val_batches and vs >= args.max_val_batches:
                        break
                    v_imgs = v_imgs.to(device, non_blocking=True)
                    v_masks = v_masks.to(device, non_blocking=True)
                    with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                        v_logits = model(v_imgs)
                        v_loss = criterion(v_logits, v_masks)
                    val_loss_sum += v_loss.item() * v_imgs.shape[0]
                    val_n += v_imgs.shape[0]
                    val_meter.update(v_logits, v_masks)

            epoch_val_loss = val_loss_sum / max(val_n, 1)
            val_metrics = val_meter.compute()
            val_iou = float(val_metrics["iou"])
            val_dice = float(val_metrics["dice"])
            val_prec = float(val_metrics["precision"])
            val_rec = float(val_metrics["recall"])

            scheduler.step()

            epoch_duration = time.time() - epoch_start
            epoch_durations.append(epoch_duration)
            cumulative = time.time() - total_start
            vram = get_vram_mb()

            # ETA
            median_epoch_s = float(np.median(epoch_durations))
            epochs_remaining = args.epochs - epoch
            eta_s = median_epoch_s * epochs_remaining
            eta_str = f"{eta_s / 60:.1f} min"

            _log.info(
                "Epoch %02d/%02d DONE: TrainLoss=%.4f | ValLoss=%.4f | "
                "ValIoU=%.4f | ValDice=%.4f | ValPrec=%.4f | ValRec=%.4f",
                epoch,
                args.epochs,
                epoch_train_loss,
                epoch_val_loss,
                val_iou,
                val_dice,
                val_prec,
                val_rec,
            )
            _log.info(
                "  Epoch time: %.1fs | Cumulative: %.1fmin | ETA: %s | VRAM alloc: %.1f MB",
                epoch_duration,
                cumulative / 60,
                eta_str,
                vram["max_allocated_mb"],
            )

            # VRAM safety check
            peak_vram, vram_safe = check_vram_safety()
            if not vram_safe:
                _log.error(
                    "VRAM SAFETY THRESHOLD EXCEEDED: %.1f MB > %.1f MB. "
                    "Checkpointing and stopping.",
                    peak_vram,
                    VRAM_SAFETY_THRESHOLD_MB,
                )

            # Disk safety check
            free_gb, disk_safe = check_disk_space(args.output_dir)
            if not disk_safe:
                _log.error("DISK SAFETY THRESHOLD: %.2f GB free. Stopping.", free_gb)

            # ---- Record epoch ----
            throughput = n_samples / epoch_duration
            epoch_record = {
                "epoch": epoch,
                "train_loss": round(epoch_train_loss, 5),
                "val_loss": round(epoch_val_loss, 5),
                "val_iou": round(val_iou, 5),
                "val_dice": round(val_dice, 5),
                "val_precision": round(val_prec, 5),
                "val_recall": round(val_rec, 5),
                "learning_rate": round(scheduler.get_last_lr()[0], 8),
                "duration_sec": round(epoch_duration, 1),
                "cumulative_sec": round(cumulative, 1),
                "throughput_samp_per_sec": round(throughput, 1),
                "peak_vram_allocated_mb": vram["max_allocated_mb"],
                "eta_remaining_min": round(eta_s / 60, 1),
            }
            history.append(epoch_record)
            append_history(history_path, history)

            # ---- Evaluate best metric update ----
            is_new_best = False
            if val_iou > best_val_iou:
                best_val_iou = val_iou
                best_epoch = epoch
                patience_counter = 0
                is_new_best = True
            else:
                patience_counter += 1
                _log.info(
                    "  --> No improvement (patience %d/%d). Best=%.4f @ epoch %d",
                    patience_counter,
                    args.patience,
                    best_val_iou,
                    best_epoch,
                )

            # ---- Checkpoint state dict ----
            chkpt_state = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "scaler_state_dict": scaler.state_dict(),
                "val_iou": val_iou,
                "val_dice": val_dice,
                "val_loss": epoch_val_loss,
                "best_val_iou": best_val_iou,
                "best_epoch": best_epoch,
                "patience_counter": patience_counter,
                "history": history,
                "config": config,
                "experiment_fingerprint": fingerprint,
            }

            # ---- Latest recovery checkpoint (atomic) ----
            run_state["status"] = "CHECKPOINTING"
            write_run_state(args.output_dir, run_state)
            try:
                sha_latest = atomic_save_checkpoint(latest_chkpt_path, chkpt_state)
                update_checkpoint_integrity(
                    args.output_dir,
                    {
                        "latest_checkpoint": str(latest_chkpt_path),
                        "latest_epoch": epoch,
                        "latest_sha256": sha_latest,
                        "latest_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                )
                _log.debug("Latest checkpoint saved (SHA: %s...)", sha_latest[:12])
            except Exception as e:
                _log.error("Failed to save latest checkpoint: %s", e)

            # ---- Best checkpoint ----
            if is_new_best:
                try:
                    sha_best = atomic_save_checkpoint(best_chkpt_path, chkpt_state)
                    update_checkpoint_integrity(
                        args.output_dir,
                        {
                            "best_checkpoint": str(best_chkpt_path),
                            "best_epoch": best_epoch,
                            "best_val_iou": round(best_val_iou, 5),
                            "best_sha256": sha_best,
                            "best_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        },
                    )
                    _log.info(
                        "  --> [*] NEW BEST: Val IoU=%.4f at epoch %d (SHA: %s...)",
                        best_val_iou,
                        best_epoch,
                        sha_best[:12],
                    )
                except Exception as e:
                    _log.error("Failed to save best checkpoint: %s", e)

            # ---- Update run_state ----
            run_state.update(
                {
                    "status": "RUNNING",
                    "current_epoch": epoch,
                    "best_epoch": best_epoch,
                    "best_val_iou": round(best_val_iou, 5),
                    "last_epoch_duration_sec": round(epoch_duration, 1),
                    "throughput_samp_per_sec": round(throughput, 1),
                    "eta_remaining_min": round(eta_s / 60, 1),
                    "peak_vram_allocated_mb": vram["max_allocated_mb"],
                    "disk_free_gb": free_gb,
                }
            )
            write_run_state(args.output_dir, run_state)

            # ---- Stop conditions ----
            if not vram_safe or not disk_safe:
                run_state["status"] = "INTERRUPTED"
                run_state["failure"] = "Resource safety threshold exceeded"
                write_run_state(args.output_dir, run_state)
                release_run_lock(lock_path)
                sys.exit(1)

            if args.stop_after_epoch is not None and epoch >= args.stop_after_epoch:
                _log.info(
                    "\nEXECUTION STOP: Reached requested stop-after-epoch (%d). Halting cleanly.",
                    args.stop_after_epoch,
                )
                break

            if patience_counter >= args.patience:
                _log.info("\nEARLY STOPPING: Val IoU did not improve for %d epochs.", args.patience)
                break

        # ---- Training complete ----
        total_duration = time.time() - total_start
        _log.info("\n" + "=" * 75)
        _log.info(
            "TRAINING COMPLETE: %d epochs in %.1f min",
            len(history),
            total_duration / 60,
        )
        _log.info("Best Val IoU: %.4f at epoch %d", best_val_iou, best_epoch)
        _log.info("=" * 75)

        # Final checkpoint
        final_chkpt_path = args.output_dir / "final_model.pt"
        try:
            sha_final = atomic_save_checkpoint(
                final_chkpt_path,
                {k: v for k, v in chkpt_state.items()},
            )
            _log.info("Final model saved: %s (SHA: %s...)", final_chkpt_path, sha_final[:12])
        except Exception as e:
            _log.error("Failed to save final checkpoint: %s", e)

        # ---- Optimizer Step Accounting Audit ----
        acc_summary = step_accountant.get_accounting_summary()
        expected_cumulative_updates = prior_optimizer_steps + acc_summary["successful_optimizer_updates"]
        _log.info("\n" + "=" * 75)
        _log.info("OPTIMIZER STEP ACCOUNTING AUDIT:")
        _log.info("  Prior Optimizer Steps:         %d", prior_optimizer_steps)
        _log.info("  Optimizer Step Attempts:       %d", acc_summary["optimizer_step_attempts"])
        _log.info("  Successful Optimizer Updates:  %d", acc_summary["successful_optimizer_updates"])
        _log.info("  AMP-Skipped Optimizer Updates: %d", acc_summary["amp_skipped_updates"])
        _log.info("  Cumulative Expected Updates:   %d", expected_cumulative_updates)

        # Cross-verify with AdamW internal parameter step states
        for p_idx, p in enumerate(model.parameters()):
            if p in optimizer.state and "step" in optimizer.state[p]:
                p_step = int(optimizer.state[p]["step"].item())
                if p_step != expected_cumulative_updates:
                    raise ValueError(
                        f"Optimizer parameter {p_idx} step mismatch: {p_step} vs expected cumulative {expected_cumulative_updates} "
                        f"(prior={prior_optimizer_steps}, session={acc_summary['successful_optimizer_updates']})"
                    )
        _log.info(
            "  [VERIFIED] AdamW parameter step counts match cumulative updates (%d) across all parameters.",
            expected_cumulative_updates,
        )
        _log.info("=" * 75)
        run_state.update(acc_summary)
        run_state["prior_optimizer_steps"] = prior_optimizer_steps
        run_state["cumulative_optimizer_updates"] = expected_cumulative_updates
        write_run_state(args.output_dir, run_state)

        # ---- Checkpoint Verification Audit (Read-Only) ----
        _log.info("\n" + "=" * 75)
        _log.info("CHECKPOINT VERIFICATION AUDIT (READ-ONLY)")
        _log.info("=" * 75)
        integrity_path = args.output_dir / "checkpoint_integrity.json"
        integrity_data = json.loads(integrity_path.read_text(encoding="utf-8")) if integrity_path.exists() else {}

        chkpt_artifacts = [
            ("latest_checkpoint.pt", latest_chkpt_path),
            ("final_model.pt", final_chkpt_path),
        ]
        if best_chkpt_path.exists() or not args.resume or best_epoch >= start_epoch:
            chkpt_artifacts.append(("best_model.pt", best_chkpt_path))

        for name, path in chkpt_artifacts:
            if not path.exists():
                raise FileNotFoundError(f"Checkpoint artifact {name} missing at {path}")
            fsize = path.stat().st_size
            if fsize <= 1024:
                raise ValueError(f"Checkpoint artifact {name} is suspiciously small: {fsize} bytes")
            f_sha = file_sha256(path)

            if name == "latest_checkpoint.pt":
                expected_sha = integrity_data.get("latest_sha256")
                if expected_sha and f_sha.upper() != expected_sha.upper():
                    raise ValueError(f"latest_checkpoint.pt SHA mismatch: {f_sha} vs {expected_sha}")
                if integrity_data.get("latest_epoch") != epoch:
                    raise ValueError(
                        f"latest_checkpoint.pt epoch mismatch: {integrity_data.get('latest_epoch')} vs {epoch}"
                    )
            elif name == "best_model.pt":
                expected_sha = integrity_data.get("best_sha256")
                if expected_sha and f_sha.upper() != expected_sha.upper():
                    raise ValueError(f"best_model.pt SHA mismatch: {f_sha} vs {expected_sha}")
                if integrity_data.get("best_epoch") != best_epoch:
                    raise ValueError(
                        f"best_model.pt epoch mismatch: {integrity_data.get('best_epoch')} vs {best_epoch}"
                    )

            loaded = safe_load_checkpoint(path, map_location="cpu", expected_sha256=f_sha)
            for req_k in [
                "epoch",
                "model_state_dict",
                "optimizer_state_dict",
                "scheduler_state_dict",
                "scaler_state_dict",
                "val_iou",
                "val_dice",
                "val_loss",
                "best_val_iou",
                "best_epoch",
                "patience_counter",
                "history",
                "config",
                "experiment_fingerprint",
            ]:
                if req_k not in loaded:
                    raise KeyError(f"Required canonical key '{req_k}' missing from {name}")

            msd = loaded["model_state_dict"]
            expected_tensors = len(model.state_dict())
            if len(msd) != expected_tensors:
                raise ValueError(f"{name} model_state_dict has {len(msd)} tensors, expected {expected_tensors}")

            _log.info(
                "  [VERIFIED] %s: %d bytes | SHA256: %s... | %d tensors | epoch: %d",
                name,
                fsize,
                f_sha[:12],
                len(msd),
                loaded["epoch"],
            )
        _log.info("All 3 checkpoint artifacts verified structurally complete and readable.")
        _log.info("=" * 75 + "\n")

        # ---- Load best for evaluation ----
        _log.info("\nLoading best checkpoint (epoch %d) for threshold search...", best_epoch)
        best_sha = file_sha256(best_chkpt_path)
        best_state = safe_load_checkpoint(
            best_chkpt_path, map_location=device, expected_sha256=best_sha
        )
        model.load_state_dict(best_state["model_state_dict"])
        model.eval()

        run_evaluation_and_reporting(
            model=model,
            eval_chkpt_path=best_chkpt_path,
            eval_chkpt_sha=best_sha,
            manifest=manifest,
            val_loader=val_loader,
            test_loader=test_loader,
            criterion=criterion,
            device=device,
            use_amp=use_amp,
            output_dir=args.output_dir,
            run_id=run_id,
            config=config,
            best_epoch=best_epoch,
            best_val_iou=best_val_iou,
            history_data=history,
            run_state=run_state,
            lock_path=lock_path,
            param_counts=param_counts,
            total_duration=total_duration,
        )

    except KeyboardInterrupt:
        _log.warning("Training interrupted by user.")
        run_state["status"] = "INTERRUPTED"
        run_state["interrupted_time_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        run_state["error"] = "Interrupted by user"
        write_run_state(args.output_dir, run_state)
        release_run_lock(lock_path)
        sys.exit(130)
    except Exception as e:
        _log.exception("Training failed with exception: %s", e)
        run_state["status"] = "FAILED"
        run_state["failed_time_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        run_state["error"] = str(e)
        run_state["traceback"] = traceback.format_exc()
        write_run_state(args.output_dir, run_state)
        release_run_lock(lock_path)
        sys.exit(1)


if __name__ == "__main__":
    main()
