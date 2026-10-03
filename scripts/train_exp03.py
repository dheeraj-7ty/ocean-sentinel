"""EXP-03: Training ResNet-34 U-Net with Development-Split Hard-Negative Mining.

Phase 5B Controlled One-Variable Intervention:
- Architecture: ResNet34UNet (in_channels=2, num_classes=1, adaptation='slice_variance_scaled')
- Total parameters: 24,346,305 (24,365,359 with persistent BatchNorm buffers)
- Initialization: Canonical EXP-01 baseline best_model.pt (SHA: 9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699)
- Loss: CombinedBCEAndDiceLoss (bce_weight=0.5, dice_weight=0.5, smooth=1.0)
- Optimizer: AdamW (lr=1e-4, weight_decay=1e-2, betas=(0.9, 0.999), eps=1e-8)
- Scheduler: CosineAnnealingLR (T_max=10, eta_min=1e-6)
- Epochs: 10
- Effective batch size: 16 (14 standard TRAIN tiles + 2 mined hard-negative TRAIN tiles)
- Hard-negative exposure: 12.5% fixed per mini-batch
- Seed: 42
- Normalization: Frozen destination-channel z-score standardization (mu0=-33.233137, sigma0=6.489986, mu1=-19.941216, sigma1=4.531346)
- Decision threshold: tau = 0.22 (strictly frozen)
- Validation: Canonical Trujillo Part I validation split (180 scenes, 2,880 tiles)
- Isolated Test Split: Zero test tiles loaded or evaluated during training
- Isolated Part III: Multi-layer firewall blocks any Part III forward pass or data access
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import math
import os
import platform
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np
import rasterio
from rasterio.windows import Window
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, Sampler

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
from ocean_sentinel.ingestion.firewall import assert_no_part_iii_leakage
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName
from ocean_sentinel.ml.augmentation import IdentityTransform, SARGeometricAugmentation
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss
from ocean_sentinel.ml.metrics import SegmentationMeter, compute_confusion_matrix_counts
from ocean_sentinel.ml.unet_resnet import ResNet34UNet, count_parameters

# Expected Provenance Constants
EXPECTED_SPLIT_SHA256 = "C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0"
EXPECTED_CANDIDATE_MANIFEST_SHA256 = "3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4"
EXPECTED_TEACHER_SHA256 = "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699"
EXPECTED_TEACHER_SIZE = 292465299

FROZEN_THRESHOLD = 0.22
TOTAL_EPOCHS = 10
BATCH_SIZE = 16
N_STANDARD_PER_BATCH = 14
N_MINED_PER_BATCH = 2
MIN_DISK_FREE_GB = 5.0


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


def atomic_save_checkpoint(path: Path, state: Dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp.pt")
    torch.save(state, tmp_path)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    # Transactional load verification before atomic rename
    loaded = torch.load(tmp_path, map_location="cpu", weights_only=False)
    assert "model_state_dict" in loaded, "Incomplete checkpoint: missing model_state_dict"
    assert len(loaded["model_state_dict"]) > 0, "Incomplete checkpoint: empty model_state_dict"
    os.replace(tmp_path, path)
    return compute_file_sha256(path)


def log_telemetry(phase: str, progress: str, status: str, eta: str = "N/A") -> None:
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(
        f"PHASE: {phase} / PROGRESS: {progress} / STATUS: {status} / ETA: {eta} / HEARTBEAT: {now_utc}",
        flush=True,
    )


class MinedHardNegativeDataset(Dataset):
    """Dataset serving the frozen 400 hard-negative candidate tiles from SplitName.TRAIN."""

    def __init__(
        self,
        candidate_manifest_path: Path,
        repo_root: Path,
        channel_means: Tuple[float, float],
        channel_stds: Tuple[float, float],
        transform: Optional[Any] = None,
    ):
        self.candidate_manifest_path = Path(candidate_manifest_path)
        self.repo_root = Path(repo_root)
        self.channel_means = np.array(channel_means, dtype=np.float32)
        self.channel_stds = np.array(channel_stds, dtype=np.float32)
        self.transform = transform or IdentityTransform()

        # Load candidates
        data = json.loads(self.candidate_manifest_path.read_text(encoding="utf-8"))
        self.candidates = data["candidates"]
        assert len(self.candidates) == 400, f"Expected 400 candidates, found {len(self.candidates)}"

        # Preflight firewall check
        image_paths = [c["relative_image_path"] for c in self.candidates]
        assert_no_part_iii_leakage(image_paths, check_content_hashes=False)

    def __len__(self) -> int:
        return len(self.candidates)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        c = self.candidates[idx]
        img_path = self.repo_root / c["relative_image_path"]
        row_offset = c["row_offset"]
        col_offset = c["col_offset"]
        h = c["height"]
        w = c["width"]

        with rasterio.open(img_path) as src:
            window = Window(col_off=col_offset, row_off=row_offset, width=w, height=h)
            tile_data = src.read(window=window).astype(np.float32)

        # Z-score normalization
        for ch in range(2):
            tile_data[ch] = (tile_data[ch] - self.channel_means[ch]) / self.channel_stds[ch]

        # Target mask is strictly zero for clean negative tiles
        mask_data = np.zeros((1, h, w), dtype=np.float32)

        # Convert to torch.Tensor
        img_t = torch.from_numpy(tile_data)
        mask_t = torch.from_numpy(mask_data)

        # Apply spatial augmentations
        if self.transform is not None:
            img_t, mask_t = self.transform(img_t, mask_t)
        return img_t, mask_t


class CompositeTwoStreamDataset(Dataset):
    """Composite dataset indexing standard train tiles (0..N_std-1) and mined tiles (N_std..N_std+N_mined-1)."""

    def __init__(self, std_ds: Dataset, mined_ds: Dataset):
        self.std_ds = std_ds
        self.mined_ds = mined_ds
        self.n_std = len(std_ds)
        self.n_mined = len(mined_ds)

    def __len__(self) -> int:
        return self.n_std + self.n_mined

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        if idx < self.n_std:
            return self.std_ds[idx]
        else:
            return self.mined_ds[idx - self.n_std]


class TwoStreamBatchSampler(Sampler[List[int]]):
    """Batched sampler that yields mini-batches of 16 containing:
    - 14 indices from standard training pool (sampled without replacement per epoch)
    - 2 indices from mined candidate pool (sampled with replacement)
    """

    def __init__(
        self,
        n_standard: int,
        n_mined: int,
        n_standard_per_batch: int = 14,
        n_mined_per_batch: int = 2,
        seed: int = 42,
    ):
        self.n_standard = n_standard
        self.n_mined = n_mined
        self.n_standard_per_batch = n_standard_per_batch
        self.n_mined_per_batch = n_mined_per_batch
        self.seed = seed
        self.epoch = 0
        self.n_batches = self.n_standard // self.n_standard_per_batch

    def __len__(self) -> int:
        return self.n_batches

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __iter__(self) -> Iterator[List[int]]:
        g = torch.Generator()
        g.manual_seed(self.seed + self.epoch * 1000)

        # Standard indices permuted without replacement
        standard_perm = torch.randperm(self.n_standard, generator=g).tolist()

        # Mined indices sampled with replacement
        total_mined_draws = self.n_batches * self.n_mined_per_batch
        mined_draws = torch.randint(0, self.n_mined, (total_mined_draws,), generator=g).tolist()

        for b in range(self.n_batches):
            batch_std = standard_perm[b * self.n_standard_per_batch : (b + 1) * self.n_standard_per_batch]
            batch_mined = [
                self.n_standard + m
                for m in mined_draws[b * self.n_mined_per_batch : (b + 1) * self.n_mined_per_batch]
            ]
            yield batch_std + batch_mined


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EXP-03 Phase 5B Hard-Negative Training Runner")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json",
        help="Path to spatial split manifest",
    )
    parser.add_argument(
        "--candidate-manifest",
        type=Path,
        default=REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "exp03_hard_negative_manifest.json",
        help="Path to frozen 400 hard-negative candidate manifest",
    )
    parser.add_argument(
        "--teacher-checkpoint",
        type=Path,
        default=REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt",
        help="Path to canonical EXP-01 baseline teacher checkpoint",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "experiments" / "performance" / "exp03_baseline_hard_neg",
        help="Output directory for Phase 5B run artifacts",
    )
    parser.add_argument("--epochs", type=int, default=10, help="Training epoch count")
    parser.add_argument("--batch-size", type=int, default=16, help="Total mini-batch size (14 std + 2 mined)")
    parser.add_argument("--lr", type=float, default=1e-4, help="AdamW initial learning rate")
    parser.add_argument("--weight-decay", type=float, default=1e-2, help="AdamW weight decay")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--num-workers", type=int, default=4, help="DataLoader workers")
    parser.add_argument("--device", type=str, default="cuda", help="Target device")
    parser.add_argument("--resume", type=Path, default=None, help="Path to checkpoint for crash resumption")
    parser.add_argument(
        "--preflight-only",
        "--dry-run",
        action="store_true",
        dest="preflight_only",
        help="Execute preflight gate and dry-run validation without performing training steps",
    )
    parser.add_argument(
        "--authorized",
        action="store_true",
        dest="authorized",
        help="Execute training under explicit CAO authorization",
    )
    return parser


def run_preflight(args: argparse.Namespace) -> Dict[str, Any]:
    """Rigorous preflight checking of all Phase 5B invariants and environment state."""
    log_telemetry("PHASE_0_PREFLIGHT", "10%", "Verifying artifact existence and digests", "1m")

    # 1. Verify Spatial Split Manifest
    assert args.manifest.exists(), f"Spatial split manifest not found: {args.manifest}"
    split_sha = compute_file_sha256(args.manifest)
    assert split_sha == EXPECTED_SPLIT_SHA256, f"Spatial split hash mismatch: {split_sha} != {EXPECTED_SPLIT_SHA256}"

    # 2. Verify Candidate Manifest
    assert args.candidate_manifest.exists(), f"Candidate manifest not found: {args.candidate_manifest}"
    manifest_sha = compute_file_sha256(args.candidate_manifest)
    assert manifest_sha == EXPECTED_CANDIDATE_MANIFEST_SHA256, f"Candidate manifest hash mismatch: {manifest_sha} != {EXPECTED_CANDIDATE_MANIFEST_SHA256}"

    # 3. Verify Teacher Checkpoint
    assert args.teacher_checkpoint.exists(), f"Teacher checkpoint not found: {args.teacher_checkpoint}"
    ckpt_size = args.teacher_checkpoint.stat().st_size
    assert ckpt_size == EXPECTED_TEACHER_SIZE, f"Teacher checkpoint size mismatch: {ckpt_size} != {EXPECTED_TEACHER_SIZE}"
    ckpt_sha = compute_file_sha256(args.teacher_checkpoint)
    assert ckpt_sha == EXPECTED_TEACHER_SHA256, f"Teacher checkpoint hash mismatch: {ckpt_sha} != {EXPECTED_TEACHER_SHA256}"

    # 4. Verify Disk Space
    d_free_gb = shutil.disk_usage(REPO_ROOT).free / (1024**3)
    assert d_free_gb >= MIN_DISK_FREE_GB, f"Insufficient disk space: {d_free_gb:.1f} GB < {MIN_DISK_FREE_GB} GB"

    # 5. Verify Device
    if args.device == "cuda":
        assert torch.cuda.is_available(), "CUDA device requested but torch.cuda.is_available() is False"

    # 6. Verify Output Directory Safety
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.resume is None:
        existing_checkpoints = list(args.output_dir.glob("*.pt"))
        if existing_checkpoints:
            raise RuntimeError(f"Output directory contains existing checkpoints but --resume not specified: {existing_checkpoints}")

    return {
        "split_sha256": split_sha,
        "candidate_manifest_sha256": manifest_sha,
        "teacher_checkpoint_sha256": ckpt_sha,
        "teacher_checkpoint_size_bytes": ckpt_size,
        "disk_free_gb": round(d_free_gb, 1),
        "preflight_status": "PASS",
    }


def dry_run_launch(args: argparse.Namespace) -> None:
    """Safe dry-run: constructs model, dataloaders, and verifies memory without optimizer steps."""
    preflight_info = run_preflight(args)

    log_telemetry("PHASE_8_DRY_RUN", "50%", "Constructing datasets and model for launch dry-run", "30s")

    # Dataset Manifest
    dataset_manifest = DatasetManifest.load(args.manifest)
    assert_no_part_iii_leakage([p.image_path for p in dataset_manifest.patches], check_content_hashes=False)

    means = tuple(dataset_manifest.normalization_stats.channel_means)
    stds = tuple(dataset_manifest.normalization_stats.channel_stds)

    train_std_ds = TrujilloTileDataset(dataset_manifest, split=SplitName.TRAIN, normalize=True)
    mined_ds = MinedHardNegativeDataset(args.candidate_manifest, REPO_ROOT, means, stds)

    assert len(train_std_ds) == 13440, f"Expected 13440 train tiles, got {len(train_std_ds)}"
    assert len(mined_ds) == 400, f"Expected 400 mined tiles, got {len(mined_ds)}"

    # Instantiate Model
    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")
    checkpoint = torch.load(args.teacher_checkpoint, map_location="cpu", weights_only=False)
    state_dict = checkpoint["model_state_dict"] if "model_state_dict" in checkpoint else checkpoint
    model.load_state_dict(state_dict, strict=True)

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    # Dry-run batch assembly test (1 batch, forward pass only, zero optimizer step)
    log_telemetry("PHASE_8_DRY_RUN", "80%", "Verifying two-stream batch assembly", "10s")
    std_batch = torch.stack([train_std_ds[i][0] for i in range(14)]).to(device)
    mined_batch = torch.stack([mined_ds[i][0] for i in range(2)]).to(device)
    full_batch = torch.cat([std_batch, mined_batch], dim=0)

    assert full_batch.shape == (16, 2, 512, 512), f"Unexpected batch shape: {full_batch.shape}"

    with torch.no_grad():
        out = model(full_batch)
        assert out.shape == (16, 1, 512, 512), f"Unexpected output shape: {out.shape}"

    vram_alloc = torch.cuda.memory_allocated() / (1024**2) if torch.cuda.is_available() else 0.0

    log_telemetry("PHASE_8_DRY_RUN", "100%", "Launch dry-run successfully passed", "0s")
    print(f"DRY-RUN COMPLETE:")
    print(f"  Batch shape verified: {full_batch.shape}")
    print(f"  Output shape verified: {out.shape}")
    print(f"  Allocated VRAM: {vram_alloc:.1f} MB")
    print(f"  Preflight check: {preflight_info['preflight_status']}")
    print(f"  Manifest SHA-256: {preflight_info['candidate_manifest_sha256']}")
    print(f"  Teacher SHA-256: {preflight_info['teacher_checkpoint_sha256']}")
    print("SYSTEM IS LOCKED AT PRE-TRAINING GATE. TRAINING NOT AUTHORIZED.")


def evaluate_validation(
    model: nn.Module,
    val_loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    threshold: float = 0.22,
) -> Dict[str, float]:
    """Run validation evaluation over canonical validation split."""
    model.eval()
    val_loss_total = 0.0
    val_batches = 0
    meter = SegmentationMeter(threshold=threshold)

    empty_tiles_count = 0
    clean_water_fa_count = 0
    sig_fa_count = 0
    total_fp_pixels = 0

    with torch.no_grad():
        for imgs, masks in val_loader:
            imgs = imgs.to(device)
            masks = masks.to(device)

            with torch.amp.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                logits = model(imgs)
                loss = criterion(logits, masks)

            val_loss_total += loss.item()
            val_batches += 1

            probs = torch.sigmoid(logits)
            meter.update(logits, masks)

            # Per-tile false alarm calculations
            preds_bin = probs >= threshold
            for b in range(masks.shape[0]):
                m_b = masks[b, 0]
                p_b = preds_bin[b, 0]
                if m_b.sum().item() == 0:
                    empty_tiles_count += 1
                    fp_pix = p_b.sum().item()
                    total_fp_pixels += fp_pix
                    if fp_pix > 0:
                        clean_water_fa_count += 1
                    if fp_pix >= 100:
                        sig_fa_count += 1

    summary = meter.compute()
    clean_water_far = (clean_water_fa_count / empty_tiles_count * 100.0) if empty_tiles_count > 0 else 0.0
    sig_far = (sig_fa_count / empty_tiles_count * 100.0) if empty_tiles_count > 0 else 0.0

    return {
        "val_loss": round(val_loss_total / max(1, val_batches), 5),
        "val_iou": round(summary["iou"], 5),
        "val_dice": round(summary["dice"], 5),
        "val_precision": round(summary["precision"], 5),
        "val_recall": round(summary["recall"], 5),
        "clean_water_far_pct": round(clean_water_far, 2),
        "significant_far_pct": round(sig_far, 2),
        "total_fp_pixels": int(total_fp_pixels),
        "empty_tiles_evaluated": int(empty_tiles_count),
    }


def train_exp03(args: argparse.Namespace) -> None:
    """Execute authorized Phase 5B EXP-03 training run."""
    if not getattr(args, "authorized", False):
        raise RuntimeError(
            "PHASE 5B TRAINING EXECUTION NOT AUTHORIZED.\n"
            "Direct function invocation blocked: Phase 5B training requires explicit CAO authorization (--authorized)."
        )
    start_time_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    preflight_info = run_preflight(args)

    # Determinism
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    log_telemetry("INITIALIZATION", "0%", f"Using device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    # Load Spatial Split Manifest
    manifest = DatasetManifest.load(args.manifest)
    assert_no_part_iii_leakage([p.image_path for p in manifest.patches], check_content_hashes=False)

    means = tuple(manifest.normalization_stats.channel_means)
    stds = tuple(manifest.normalization_stats.channel_stds)

    # Augmentations
    train_transform = SARGeometricAugmentation(p_hflip=0.5, p_vflip=0.5, p_rot90=0.5, seed=args.seed)
    val_transform = IdentityTransform()

    # Datasets
    std_train_ds = TrujilloTileDataset(manifest, split=SplitName.TRAIN, transform=train_transform, normalize=True)
    mined_train_ds = MinedHardNegativeDataset(args.candidate_manifest, REPO_ROOT, means, stds, transform=train_transform)
    composite_train_ds = CompositeTwoStreamDataset(std_train_ds, mined_train_ds)

    val_ds = TrujilloTileDataset(manifest, split=SplitName.VAL, transform=val_transform, normalize=True)

    # Two-Stream Batch Sampler
    two_stream_sampler = TwoStreamBatchSampler(
        n_standard=len(std_train_ds),
        n_mined=len(mined_train_ds),
        n_standard_per_batch=N_STANDARD_PER_BATCH,
        n_mined_per_batch=N_MINED_PER_BATCH,
        seed=args.seed,
    )

    train_loader = DataLoader(
        composite_train_ds,
        batch_sampler=two_stream_sampler,
        num_workers=args.num_workers,
        pin_memory=(device.type == "cuda"),
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=(device.type == "cuda"),
    )

    # Model
    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")

    # Load Teacher Checkpoint
    checkpoint = torch.load(args.teacher_checkpoint, map_location="cpu", weights_only=False)
    state_dict = checkpoint["model_state_dict"] if "model_state_dict" in checkpoint else checkpoint
    model.load_state_dict(state_dict, strict=True)
    model.to(device)

    # Loss, Optimizer, Scheduler, Scaler
    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)
    scaler = torch.amp.GradScaler(device.type, enabled=(device.type == "cuda"))

    # State Tracking
    start_epoch = 1
    completed_epochs_count = 0
    best_val_iou = 0.0
    history: List[Dict[str, Any]] = []
    latest_valid_ckpt_path: Optional[str] = None
    latest_val_metrics: Optional[Dict[str, Any]] = None

    # Resume handling if specified
    if args.resume is not None:
        assert args.resume.exists(), f"Resume checkpoint not found: {args.resume}"
        res_ckpt = torch.load(args.resume, map_location=device, weights_only=False)
        model.load_state_dict(res_ckpt["model_state_dict"])
        optimizer.load_state_dict(res_ckpt["optimizer_state_dict"])
        scheduler.load_state_dict(res_ckpt["scheduler_state_dict"])
        scaler.load_state_dict(res_ckpt["scaler_state_dict"])
        start_epoch = res_ckpt["epoch"] + 1
        completed_epochs_count = res_ckpt["epoch"]
        best_val_iou = res_ckpt.get("best_val_iou", 0.0)
        history = res_ckpt.get("history", [])
        latest_valid_ckpt_path = str(args.resume)
        latest_val_metrics = res_ckpt.get("val_metrics", None)
        log_telemetry("RESUME", f"Epoch {start_epoch}", f"Resumed from {args.resume}")

    run_state_path = args.output_dir / "run_state.json"
    history_path = args.output_dir / "history.json"
    training_log_path = args.output_dir / "training.log"

    def write_run_state(current_epoch: int, current_batch: int, status: str, loss_val: float = 0.0) -> None:
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        vram_mb = round(torch.cuda.memory_allocated() / (1024**2), 1) if torch.cuda.is_available() else 0.0
        state_payload = {
            "experiment_id": "EXP-03_HARD_NEGATIVE_BASELINE",
            "attempt_id": "EXP03_ATTEMPT_002",
            "status": status,
            "start_time_utc": start_time_utc,
            "latest_heartbeat_utc": now_str,
            "last_update_time_utc": now_str,
            "current_epoch": current_epoch,
            "total_epochs": args.epochs,
            "current_batch": current_batch,
            "total_batches": len(two_stream_sampler),
            "completed_epochs": completed_epochs_count,
            "current_loss": round(loss_val, 5),
            "best_val_iou": round(best_val_iou, 5),
            "latest_valid_checkpoint": latest_valid_ckpt_path,
            "latest_validation_metrics": latest_val_metrics,
            "allocated_vram_mb": vram_mb,
            "teacher_checkpoint_sha256": preflight_info["teacher_checkpoint_sha256"],
            "candidate_manifest_sha256": preflight_info["candidate_manifest_sha256"],
            "spatial_split_manifest_sha256": preflight_info["split_sha256"],
        }
        atomic_write_json(run_state_path, state_payload)

    # Initial Pre-Training Smoke Test
    log_telemetry("PRE_TRAIN_SMOKE", "0%", "Executing pre-training forward/loss smoke test", "1m")
    model.eval()
    with torch.no_grad():
        smoke_imgs = torch.stack([std_train_ds[i][0] for i in range(14)] + [mined_train_ds[i][0] for i in range(2)]).to(device)
        smoke_masks = torch.stack([std_train_ds[i][1] for i in range(14)] + [mined_train_ds[i][1] for i in range(2)]).to(device)
        smoke_preds = model(smoke_imgs)
        smoke_loss = criterion(smoke_preds, smoke_masks)
        assert torch.isfinite(smoke_loss), "Pre-train smoke test loss non-finite!"
    log_telemetry("PRE_TRAIN_SMOKE", "0%", "PRE_TRAIN_SMOKE = PASS", "0s")

    training_start_time = time.time()

    # Main Training Loop
    for epoch in range(start_epoch, args.epochs + 1):
        two_stream_sampler.set_epoch(epoch)
        model.train()
        epoch_loss_total = 0.0
        epoch_start_time = time.time()

        for batch_idx, (batch_imgs, batch_masks) in enumerate(train_loader):
            batch_imgs = batch_imgs.to(device, non_blocking=True)
            batch_masks = batch_masks.to(device, non_blocking=True)

            optimizer.zero_grad()
            with torch.amp.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                preds = model(batch_imgs)
                loss = criterion(preds, batch_masks)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            batch_loss = loss.item()
            epoch_loss_total += batch_loss

            if batch_idx % 50 == 0 or batch_idx == len(two_stream_sampler) - 1:
                elapsed_sec = time.time() - training_start_time
                batches_done = (epoch - 1) * len(two_stream_sampler) + (batch_idx + 1)
                total_batches_all = args.epochs * len(two_stream_sampler)
                eta_sec = (elapsed_sec / max(1, batches_done)) * (total_batches_all - batches_done)
                eta_str = f"{int(eta_sec // 60)}m {int(eta_sec % 60)}s"

                write_run_state(epoch, batch_idx + 1, "RUNNING", batch_loss)
                log_telemetry(
                    "TRAINING",
                    f"Epoch {epoch}/{args.epochs}, Batch {batch_idx + 1}/{len(two_stream_sampler)}",
                    f"Loss: {batch_loss:.4f}, LR: {scheduler.get_last_lr()[0]:.2e}",
                    eta_str,
                )

        scheduler.step()
        avg_train_loss = epoch_loss_total / len(two_stream_sampler)

        # Validation Evaluation
        log_telemetry("VALIDATION", f"Epoch {epoch}/{args.epochs}", "Evaluating on validation split", "2m")
        val_metrics = evaluate_validation(model, val_loader, criterion, device, threshold=FROZEN_THRESHOLD)

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 5),
            "lr": float(scheduler.get_last_lr()[0]),
            "duration_sec": round(time.time() - epoch_start_time, 1),
            **val_metrics,
        }
        history.append(epoch_record)
        atomic_write_json(history_path, history)

        # Checkpoint Management
        is_best = val_metrics["val_iou"] > best_val_iou
        if is_best:
            best_val_iou = val_metrics["val_iou"]

        checkpoint_state = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "scaler_state_dict": scaler.state_dict(),
            "val_metrics": val_metrics,
            "best_val_iou": best_val_iou,
            "history": history,
            "seed": args.seed,
            "experiment_id": "EXP-03_HARD_NEGATIVE_BASELINE",
        }

        # Save last checkpoint
        last_ckpt_path = args.output_dir / "last_model.pt"
        last_sha = atomic_save_checkpoint(last_ckpt_path, checkpoint_state)

        # Save best checkpoint
        best_sha = ""
        if is_best:
            best_ckpt_path = args.output_dir / "best_model.pt"
            best_sha = atomic_save_checkpoint(best_ckpt_path, checkpoint_state)
            log_telemetry("CHECKPOINT", f"Epoch {epoch}/{args.epochs}", f"NEW BEST MODEL SAVED: Val IoU = {val_metrics['val_iou']:.5f} (SHA: {best_sha[:8]}...)")

        # Transactional commit: all validation, metric persistence, and checkpoint writes succeeded
        completed_epochs_count = epoch
        latest_val_metrics = val_metrics
        latest_valid_ckpt_path = str(last_ckpt_path)
        write_run_state(epoch, len(two_stream_sampler), "RUNNING", avg_train_loss)

    # Finalize
    total_duration_sec = time.time() - training_start_time
    write_run_state(args.epochs, len(two_stream_sampler), "COMPLETED", avg_train_loss)

    # Save final metrics summary
    metrics_summary_path = args.output_dir / "metrics.json"
    atomic_write_json(
        metrics_summary_path,
        {
            "experiment_id": "EXP-03_HARD_NEGATIVE_BASELINE",
            "completion_time_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_duration_sec": round(total_duration_sec, 1),
            "total_epochs": args.epochs,
            "best_val_iou": best_val_iou,
            "final_epoch_metrics": history[-1],
            "history": history,
        },
    )

    log_telemetry("TRAINING_COMPLETE", "100%", f"Phase 5B EXP-03 Training Completed in {int(total_duration_sec//60)}m {int(total_duration_sec%60)}s! Best Val IoU: {best_val_iou:.5f}")


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.preflight_only:
        dry_run_launch(args)
        return

    if not args.authorized:
        raise RuntimeError(
            "PHASE 5B TRAINING EXECUTION NOT AUTHORIZED.\n"
            "To execute authorized training, pass --authorized.\n"
            "To perform preflight/dry-run, pass --preflight-only."
        )

    train_exp03(args)


if __name__ == "__main__":
    main()
