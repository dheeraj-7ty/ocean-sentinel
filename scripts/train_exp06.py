"""EXP-06: Training ResNet-34 U-Net with Positive-Class BCE Reweighting (pos_weight = 2.0).

Phase 5H Controlled Single-Variable Intervention:
- Primary Intervention: Positive-class weighting in Binary Cross-Entropy loss (pos_weight = 2.0).
- Combined Loss Formulation: 0.5 * BCE(pos_weight=2.0) + 0.5 * SoftDice(smooth=1.0).
- All 24 other experimental variables remain strictly FROZEN:
  - Starting Checkpoint: Canonical EXP-01 baseline teacher best_model.pt (SHA: 9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699)
  - Architecture: ResNet34UNet (in_channels=2, num_classes=1, adaptation='slice_variance_scaled')
  - Total parameters: 24,346,305 trainable, 19,054 buffers, 24,365,359 state dict elements
  - Standard training pool: 13,440 tiles from canonical spatial split (SHA: C052720A...)
  - Hard-negative candidate manifest: Frozen manifest (SHA: 3867671E...)
  - Candidate pool cap: fp_pixels <= 50,000 (355 retained, 45 excluded)
  - Mined exposure frequency: 15 standard + 1 mined = 16 tiles/batch (6.25% exposure)
  - Batches per epoch: 896
  - Total epochs: 10
  - Total optimizer steps: 8,960
  - Optimizer: AdamW(lr=1e-4, weight_decay=1e-2)
  - Scheduler: CosineAnnealingLR(T_max=10, eta_min=1e-6)
  - Random Seed: 42 (sampler seed: 42 + 1000 * epoch)
  - Operating decision threshold: tau = 0.22 (strictly frozen)
  - Validation: Canonical Part I validation (2,880 tiles, 1,053 positive)
  - Part III Firewall: 100% closed
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
from collections import Counter
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

SEVERITY_CAP_THRESHOLD = 50000
EXPECTED_RETAINED_CANDIDATES = 355
EXPECTED_EXCLUDED_CANDIDATES = 45
EXPECTED_SURVIVING_SCENES = 251

# Single Experimental Variable
POS_WEIGHT = 2.0
BCE_COEFF = 0.5
DICE_COEFF = 0.5
DICE_SMOOTH = 1.0

FROZEN_THRESHOLD = 0.22
TOTAL_EPOCHS = 10
BATCH_SIZE = 16
N_STANDARD_PER_BATCH = 15
N_MINED_PER_BATCH = 1
MIN_DISK_FREE_GB = 5.0


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f".tmp.{os.getpid()}")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


def atomic_save_checkpoint(path: Path, state: Dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f".tmp.{os.getpid()}")
    torch.save(state, tmp_path)
    sha256 = compute_file_sha256(tmp_path)
    os.replace(tmp_path, path)
    return sha256


class CappedMinedHardNegativeDataset(Dataset):
    """Mined hard negative tiles filtered strictly by fp_pixels <= severity_cap."""

    def __init__(
        self,
        manifest_path: Path,
        repo_root: Path,
        mean: Tuple[float, float],
        std: Tuple[float, float],
        severity_cap: int = SEVERITY_CAP_THRESHOLD,
        transform=None,
    ):
        self.manifest_path = manifest_path
        self.repo_root = repo_root
        self.mean = np.array(mean, dtype=np.float32)
        self.std = np.array(std, dtype=np.float32)
        self.severity_cap = severity_cap
        self.transform = transform

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_candidates = data["candidates"]
        assert len(raw_candidates) == 400, f"Expected 400 raw candidates, got {len(raw_candidates)}"

        # Strict filtering
        self.candidates = [c for c in raw_candidates if c["fp_pixels"] <= self.severity_cap]
        self.excluded_candidates = [c for c in raw_candidates if c["fp_pixels"] > self.severity_cap]

        assert len(self.candidates) == EXPECTED_RETAINED_CANDIDATES, (
            f"Expected {EXPECTED_RETAINED_CANDIDATES} retained, got {len(self.candidates)}"
        )
        assert len(self.excluded_candidates) == EXPECTED_EXCLUDED_CANDIDATES, (
            f"Expected {EXPECTED_EXCLUDED_CANDIDATES} excluded, got {len(self.excluded_candidates)}"
        )
        assert all(c["gt_pixels"] == 0 for c in self.candidates), "Contaminated candidate with GT > 0 found!"
        assert all(c["fp_pixels"] <= self.severity_cap for c in self.candidates), "Retained candidate exceeds cap!"
        assert all(c["fp_pixels"] > self.severity_cap for c in self.excluded_candidates), "Excluded candidate below cap!"

        self.surviving_scenes = sorted(list(set(c["parent_stem"] for c in self.candidates)))
        assert len(self.surviving_scenes) == EXPECTED_SURVIVING_SCENES, (
            f"Expected {EXPECTED_SURVIVING_SCENES} surviving scenes, got {len(self.surviving_scenes)}"
        )

    def __len__(self) -> int:
        return len(self.candidates)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        cand = self.candidates[idx]
        img_path = self.repo_root / cand["relative_image_path"]
        row_offset = cand["row_offset"]
        col_offset = cand["col_offset"]
        height = cand["height"]
        width = cand["width"]

        window = Window(col_offset, row_offset, width, height)
        with rasterio.open(img_path) as src:
            img_arr = src.read(window=window).astype(np.float32)

        # Standardize using destination stats
        for c in range(2):
            img_arr[c] = (img_arr[c] - self.mean[c]) / self.std[c]

        mask_arr = np.zeros((1, height, width), dtype=np.float32)

        if self.transform is not None:
            img_t = torch.from_numpy(img_arr)
            mask_t = torch.from_numpy(mask_arr)
            img_t, mask_t = self.transform(img_t, mask_t)
            return img_t, mask_t

        return torch.from_numpy(img_arr), torch.from_numpy(mask_arr)


class CompositeTwoStreamDataset(Dataset):
    """Combines standard train dataset and mined hard-negative dataset."""

    def __init__(self, standard_ds: Dataset, mined_ds: Dataset):
        self.standard_ds = standard_ds
        self.mined_ds = mined_ds
        self.n_standard = len(standard_ds)
        self.n_mined = len(mined_ds)

    def __len__(self) -> int:
        return self.n_standard + self.n_mined

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        if idx < self.n_standard:
            return self.standard_ds[idx]
        else:
            return self.mined_ds[idx - self.n_standard]


class TwoStreamBatchSampler(Sampler[List[int]]):
    """Yields batches of exactly 15 standard tiles + 1 mined tile (batch size 16)."""

    def __init__(
        self,
        n_standard: int,
        n_mined: int,
        n_standard_per_batch: int = 15,
        n_mined_per_batch: int = 1,
        seed: int = 42,
    ):
        self.n_standard = n_standard
        self.n_mined = n_mined
        self.n_standard_per_batch = n_standard_per_batch
        self.n_mined_per_batch = n_mined_per_batch
        self.seed = seed
        self.epoch = 0

        self.n_batches = n_standard // n_standard_per_batch
        assert self.n_batches == 896, f"Expected 896 batches, got {self.n_batches}"

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __len__(self) -> int:
        return self.n_batches

    def __iter__(self) -> Iterator[List[int]]:
        g = torch.Generator()
        g.manual_seed(self.seed + self.epoch * 1000)

        std_indices = torch.randperm(self.n_standard, generator=g).tolist()
        mined_draws = torch.randint(0, self.n_mined, (self.n_batches * self.n_mined_per_batch,), generator=g).tolist()

        for b in range(self.n_batches):
            std_batch = std_indices[b * self.n_standard_per_batch : (b + 1) * self.n_standard_per_batch]
            mined_idx = self.n_standard + mined_draws[b]
            batch = std_batch + [mined_idx]
            assert len(batch) == 16
            yield batch


def evaluate_validation(
    model: nn.Module,
    val_loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    threshold: float = FROZEN_THRESHOLD,
) -> Dict[str, Any]:
    """Independent validation evaluator computing streaming metrics via SegmentationMeter."""
    model.eval()
    meter = SegmentationMeter(threshold=threshold)
    total_loss = 0.0
    val_batches = 0

    clean_water_fa_count = 0
    sig_fa_count = 0
    empty_tiles_count = 0
    total_fp_pixels = 0

    with torch.no_grad():
        for imgs, masks in val_loader:
            imgs = imgs.to(device)
            masks = masks.to(device)

            with torch.amp.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                logits = model(imgs)
                loss = criterion(logits, masks)

            total_loss += loss.item()
            val_batches += 1
            meter.update(logits, masks)

            probs = torch.sigmoid(logits)
            preds_bin = probs >= threshold
            for b in range(masks.shape[0]):
                m_sum = masks[b, 0].sum().item()
                if m_sum == 0:
                    empty_tiles_count += 1
                    fp_px = int(preds_bin[b, 0].sum().item())
                    total_fp_pixels += fp_px
                    if fp_px > 0:
                        clean_water_fa_count += 1
                    if fp_px >= 100:
                        sig_fa_count += 1

    summary = meter.compute()
    clean_water_far = (clean_water_fa_count / empty_tiles_count * 100.0) if empty_tiles_count > 0 else 0.0
    sig_far = (sig_fa_count / empty_tiles_count * 100.0) if empty_tiles_count > 0 else 0.0

    return {
        "val_loss": round(total_loss / max(1, val_batches), 5),
        "val_iou": round(summary["iou"], 5),
        "val_dice": round(summary["dice"], 5),
        "val_precision": round(summary["precision"], 5),
        "val_recall": round(summary["recall"], 5),
        "clean_water_far_pct": round(clean_water_far, 2),
        "significant_far_pct": round(sig_far, 2),
        "total_fp_pixels": int(total_fp_pixels),
        "empty_tiles_evaluated": int(empty_tiles_count),
    }


def run_preflight(args: argparse.Namespace) -> Dict[str, Any]:
    """Verifies all hashes, parameters, and loss implementation invariants before training."""
    print("[PREFLIGHT] Checking input provenance and loss implementation...")

    split_sha = compute_file_sha256(args.manifest)
    assert split_sha == EXPECTED_SPLIT_SHA256, f"Split SHA mismatch: {split_sha}"

    candidate_sha = compute_file_sha256(args.candidate_manifest)
    assert candidate_sha == EXPECTED_CANDIDATE_MANIFEST_SHA256, f"Candidate SHA mismatch: {candidate_sha}"

    teacher_sha = compute_file_sha256(args.teacher_checkpoint)
    assert teacher_sha == EXPECTED_TEACHER_SHA256, f"Teacher SHA mismatch: {teacher_sha}"
    teacher_size = args.teacher_checkpoint.stat().st_size
    assert teacher_size == EXPECTED_TEACHER_SIZE, f"Teacher size mismatch: {teacher_size}"

    # Analytical Loss Verification
    loss_w1 = CombinedBCEAndDiceLoss(bce_weight=BCE_COEFF, dice_weight=DICE_COEFF, smooth=DICE_SMOOTH, pos_weight=1.0)
    loss_w2 = CombinedBCEAndDiceLoss(bce_weight=BCE_COEFF, dice_weight=DICE_COEFF, smooth=DICE_SMOOTH, pos_weight=POS_WEIGHT)

    dummy_logits = torch.tensor([[-1.0, 2.0], [0.5, -2.0]], dtype=torch.float32)
    dummy_targets = torch.tensor([[0.0, 1.0], [1.0, 0.0]], dtype=torch.float32)

    bce1 = nn.BCEWithLogitsLoss(reduction="none")(dummy_logits, dummy_targets)
    bce2 = nn.BCEWithLogitsLoss(reduction="none", pos_weight=torch.tensor([POS_WEIGHT]))(dummy_logits, dummy_targets)

    # Negative targets must have diff == 0.0
    diff_neg = (bce2[dummy_targets == 0] - bce1[dummy_targets == 0]).abs().max().item()
    assert diff_neg < 1e-7, f"Analytical check failed: negative targets modified by pos_weight! diff={diff_neg}"

    # Positive targets must have ratio == 2.0
    ratio_pos = (bce2[dummy_targets == 1] / bce1[dummy_targets == 1])
    assert torch.allclose(ratio_pos, torch.tensor([POS_WEIGHT, POS_WEIGHT]), atol=1e-6), "Positive targets ratio != 2.0"

    # Dice term must be bitwise identical
    dice1 = loss_w1.dice(dummy_logits, dummy_targets)
    dice2 = loss_w2.dice(dummy_logits, dummy_targets)
    assert (dice1 - dice2).abs().item() == 0.0, "Dice loss affected by pos_weight!"

    # Disk Space Check
    free_gb = shutil.disk_usage(REPO_ROOT).free / (1024 ** 3)
    assert free_gb >= MIN_DISK_FREE_GB, f"Insufficient disk space: {free_gb:.1f} GB"

    return {
        "split_sha256": split_sha,
        "candidate_manifest_sha256": candidate_sha,
        "teacher_checkpoint_sha256": teacher_sha,
        "teacher_checkpoint_size_bytes": teacher_size,
        "loss_verification": {
            "pos_weight": POS_WEIGHT,
            "negative_target_diff": diff_neg,
            "positive_target_ratio": POS_WEIGHT,
            "dice_identity_diff": 0.0,
            "status": "PASS",
        },
        "disk_free_gb": round(free_gb, 1),
        "preflight_status": "PASS",
    }


def train_exp06(args: argparse.Namespace) -> None:
    if not args.authorized:
        raise RuntimeError(
            "PHASE 5H TRAINING EXECUTION NOT AUTHORIZED: Must pass --authorized flag "
            "confirming explicit CAIO scientific governance authorization."
        )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log_path = out_dir / "training.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path, mode="w"), logging.StreamHandler(sys.stdout)],
    )

    state_path = out_dir / "run_state.json"
    start_time_sec = time.time()

    def log_telemetry(phase: str, progress: str, status: str, eta: str):
        heartbeat = datetime.datetime.now(datetime.timezone.utc).isoformat()
        msg = f"PHASE: {phase} | PROGRESS: {progress} | STATUS: {status} | ETA: {eta} | HEARTBEAT: {heartbeat}"
        logging.info(msg)

    print("================================================================================")
    print("OCEAN SENTINEL: EXP-06 POSITIVE-CLASS BCE REWEIGHTING (pos_weight = 2.0)")
    print("================================================================================")

    # 1. Preflight Verification
    preflight_info = run_preflight(args)
    print("[PREFLIGHT] Artifact integrity, loss implementation, and filesystem safety certified.")

    # 2. Dataset Construction
    log_telemetry("PHASE_1_DATA_PREPARATION", "15%", "Loading spatial split and capped candidate pool", "90m")
    dataset_manifest = DatasetManifest.load(args.manifest)
    assert_no_part_iii_leakage([p.image_path for p in dataset_manifest.patches], check_content_hashes=False)

    means = tuple(dataset_manifest.normalization_stats.channel_means)
    stds = tuple(dataset_manifest.normalization_stats.channel_stds)

    train_aug = SARGeometricAugmentation(p_hflip=0.5, p_vflip=0.5, p_rot90=0.5, seed=args.seed)
    train_std_ds = TrujilloTileDataset(dataset_manifest, split=SplitName.TRAIN, transform=train_aug, normalize=True)
    mined_ds = CappedMinedHardNegativeDataset(
        args.candidate_manifest, REPO_ROOT, means, stds, severity_cap=args.severity_cap, transform=train_aug
    )

    composite_train_ds = CompositeTwoStreamDataset(train_std_ds, mined_ds)
    batch_sampler = TwoStreamBatchSampler(
        len(train_std_ds), len(mined_ds), N_STANDARD_PER_BATCH, N_MINED_PER_BATCH, args.seed
    )

    val_ds = TrujilloTileDataset(dataset_manifest, split=SplitName.VAL, transform=IdentityTransform(), normalize=True)
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,  # Single-process for Windows evaluation stability
        pin_memory=(args.device == "cuda"),
    )

    train_loader = DataLoader(
        composite_train_ds,
        batch_sampler=batch_sampler,
        num_workers=args.num_workers,
        pin_memory=(args.device == "cuda"),
    )

    batches_per_epoch = len(batch_sampler)
    total_training_steps = batches_per_epoch * args.epochs
    assert batches_per_epoch == 896, f"Expected 896 batches per epoch, got {batches_per_epoch}"
    assert total_training_steps == 8960, f"Expected 8,960 total steps, got {total_training_steps}"

    # 3. Model & Checkpoint Initialization
    log_telemetry("PHASE_2_MODEL_INITIALIZATION", "20%", "Instantiating ResNet34UNet from canonical teacher", "85m")
    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")
    param_counts = count_parameters(model)
    assert param_counts["trainable"] == 24346305, f"Parameter count drift: {param_counts['trainable']}"

    teacher_ckpt = torch.load(args.teacher_checkpoint, map_location="cpu", weights_only=False)
    state_dict = teacher_ckpt["model_state_dict"] if "model_state_dict" in teacher_ckpt else teacher_ckpt
    model.load_state_dict(state_dict, strict=True)

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    model.to(device)

    # 4. Optimizer, Scheduler, Loss, and Scaler
    criterion = CombinedBCEAndDiceLoss(
        bce_weight=BCE_COEFF, dice_weight=DICE_COEFF, smooth=DICE_SMOOTH, pos_weight=POS_WEIGHT
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)
    scaler = torch.amp.GradScaler(device.type, enabled=(device.type == "cuda"))

    # 5. Persist Run Manifest
    run_manifest = {
        "experiment_id": "EXP-06_POSITIVE_BCE_WEIGHT",
        "attempt_id": "EXP06_ATTEMPT_001",
        "timestamp_start_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pid": os.getpid(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "device": str(device),
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "preflight": preflight_info,
        "model_architecture": "ResNet34UNet(in_channels=2, num_classes=1, adaptation_method='slice_variance_scaled')",
        "parameters": param_counts,
        "single_changed_variable": {
            "name": "loss_bce_pos_weight",
            "exp05_value": 1.0,
            "exp06_value": POS_WEIGHT,
            "formula": "L_total = 0.5 * BCE(pos_weight=2.0) + 0.5 * Dice(smooth=1.0)",
        },
        "severity_cap_threshold": args.severity_cap,
        "retained_candidate_count": len(mined_ds),
        "excluded_candidate_count": len(mined_ds.excluded_candidates),
        "surviving_scenes_count": len(mined_ds.surviving_scenes),
        "batch_composition": {
            "standard_tiles": N_STANDARD_PER_BATCH,
            "mined_tiles": N_MINED_PER_BATCH,
            "total": BATCH_SIZE,
        },
        "batches_per_epoch": batches_per_epoch,
        "total_epochs": args.epochs,
        "total_optimizer_steps": total_training_steps,
        "operating_threshold": FROZEN_THRESHOLD,
    }
    atomic_write_json(out_dir / "run_manifest.json", run_manifest)

    # 6. Mini Epoch Transaction Preflight
    print("[PREFLIGHT] Executing mini epoch transaction preflight...")
    model.eval()
    with torch.no_grad():
        dummy_x = torch.randn(2, 2, 64, 64, device=device)
        dummy_y = torch.randint(0, 2, (2, 1, 64, 64), dtype=torch.float32, device=device)
        d_logits = model(dummy_x)
        d_loss = criterion(d_logits, dummy_y)
        assert torch.isfinite(d_loss).item(), "Non-finite loss in preflight transaction"
    print("[PREFLIGHT] Mini epoch transaction succeeded.")

    # 7. Training Loop
    history: List[Dict[str, Any]] = []
    sampled_candidate_counter: Counter = Counter()
    sampled_candidate_sequence: List[str] = []
    loss_balance_records: List[Dict[str, Any]] = []

    best_val_iou = -1.0
    best_epoch = -1
    best_ckpt_sha = ""
    completed_batches = 0

    log_telemetry("PHASE_3_TRAINING_EXECUTION", "25%", "Entering Epoch 1 training", "80m")

    for epoch in range(1, args.epochs + 1):
        epoch_start_time = time.time()
        batch_sampler.set_epoch(epoch)
        model.train()

        running_train_loss = 0.0
        running_bce_loss = 0.0
        running_dice_loss = 0.0

        for batch_idx, (imgs, masks) in enumerate(train_loader, start=1):
            imgs = imgs.to(device)
            masks = masks.to(device)

            optimizer.zero_grad()

            with torch.amp.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                logits = model(imgs)
                # Compute individual terms for loss-balance diagnostic
                targets = masks.to(dtype=logits.dtype)
                bce_term = criterion.bce_weight * criterion.bce(logits, targets)
                dice_term = criterion.dice_weight * criterion.dice(logits, targets)
                loss = bce_term + dice_term

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_train_loss += loss.item()
            running_bce_loss += bce_term.item()
            running_dice_loss += dice_term.item()

            completed_batches += 1

            # Log candidate audit
            mined_tile_cand = mined_ds.candidates[batch_sampler.epoch % len(mined_ds)]
            sampled_candidate_counter[mined_tile_cand["tile_id"]] += 1
            sampled_candidate_sequence.append(mined_tile_cand["tile_id"])

            if batch_idx % 20 == 0 or batch_idx == batches_per_epoch:
                elapsed_total = time.time() - start_time_sec
                steps_remaining = total_training_steps - completed_batches
                rate = completed_batches / max(1e-5, elapsed_total)
                eta_sec = steps_remaining / max(1e-5, rate)
                pct_complete = (completed_batches / total_training_steps) * 100.0

                vram_mb = torch.cuda.memory_allocated(0) / (1024 ** 2) if torch.cuda.is_available() else 0.0
                curr_lr = optimizer.param_groups[0]["lr"]

                run_state = {
                    "experiment_id": "EXP-06_POSITIVE_BCE_WEIGHT",
                    "attempt_id": "EXP06_ATTEMPT_001",
                    "pid": os.getpid(),
                    "command_line": f"scripts\\train_exp06.py --authorized",
                    "git_commit": "542bab19f6f08c9bba8b8762e6480386c8b6026b",
                    "status": "TRAINING",
                    "phase": f"EPOCH_{epoch}_TRAIN",
                    "start_time_iso": run_manifest["timestamp_start_utc"],
                    "last_heartbeat_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "current_epoch": epoch,
                    "current_batch": batch_idx,
                    "completed_batches": completed_batches,
                    "total_batches": total_training_steps,
                    "percent_complete": round(pct_complete, 2),
                    "eta_seconds": int(eta_sec),
                    "current_train_loss": round(running_train_loss / batch_idx, 5),
                    "current_lr": curr_lr,
                    "best_val_iou": round(best_val_iou, 5) if best_val_iou > 0 else None,
                    "best_epoch": best_epoch if best_epoch > 0 else None,
                    "latest_checkpoint": f"best_model.pt (IoU={best_val_iou:.5f}, SHA={best_ckpt_sha[:12]})" if best_ckpt_sha else None,
                    "gpu_vram_allocated_mb": round(vram_mb, 1),
                    "failure_reason": None,
                }
                atomic_write_json(state_path, run_state)

                if batch_idx % 200 == 0 or batch_idx == batches_per_epoch:
                    log_telemetry(
                        f"EPOCH_{epoch}_STEP_{batch_idx}",
                        f"{pct_complete:.1f}%",
                        f"loss={running_train_loss / batch_idx:.5f} (bce={running_bce_loss / batch_idx:.4f}, dice={running_dice_loss / batch_idx:.4f}) lr={curr_lr:.2e}",
                        f"{int(eta_sec // 60)}m {int(eta_sec % 60)}s",
                    )

        scheduler.step()
        epoch_train_loss = running_train_loss / batches_per_epoch
        epoch_bce_loss = running_bce_loss / batches_per_epoch
        epoch_dice_loss = running_dice_loss / batches_per_epoch

        # Loss Balance Record
        loss_balance_records.append({
            "epoch": epoch,
            "train_loss": round(epoch_train_loss, 5),
            "bce_term": round(epoch_bce_loss, 5),
            "dice_term": round(epoch_dice_loss, 5),
            "bce_to_dice_ratio": round(epoch_bce_loss / max(1e-5, epoch_dice_loss), 3),
        })

        # Validation Step
        log_telemetry(f"EPOCH_{epoch}_VALIDATION", f"{pct_complete:.1f}%", "Evaluating on canonical Part I validation", "calculating...")
        val_metrics = evaluate_validation(model, val_loader, criterion, device, threshold=FROZEN_THRESHOLD)
        epoch_duration = time.time() - epoch_start_time

        val_iou = val_metrics["val_iou"]
        is_best = val_iou > best_val_iou

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(epoch_train_loss, 5),
            **val_metrics,
            "is_best": is_best,
            "epoch_duration_sec": round(epoch_duration, 1),
        }
        history.append(epoch_record)
        atomic_write_json(out_dir / "history.json", history)

        ckpt_state = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "val_metrics": val_metrics,
            "train_loss": epoch_train_loss,
            "git_commit": "542bab19f6f08c9bba8b8762e6480386c8b6026b",
        }

        # Save last checkpoint
        last_sha = atomic_save_checkpoint(out_dir / "last_model.pt", ckpt_state)

        if is_best:
            best_val_iou = val_iou
            best_epoch = epoch
            best_ckpt_sha = atomic_save_checkpoint(out_dir / "best_model.pt", ckpt_state)
            logging.info(
                f"[CHECKPOINT] NEW GLOBAL BEST at Epoch {epoch}: Val IoU = {val_iou:.5f} (SHA: {best_ckpt_sha})"
            )

        logging.info(
            f"[EPOCH {epoch}/{args.epochs}] Train Loss: {epoch_train_loss:.5f} | "
            f"Val Loss: {val_metrics['val_loss']:.5f} | Val IoU: {val_metrics['val_iou']:.5f} | "
            f"Val Recall: {val_metrics['val_recall']:.5f} | Clean FAR: {val_metrics['clean_water_far_pct']:.2f}% | "
            f"Total FP: {val_metrics['total_fp_pixels']:,} px | Duration: {epoch_duration:.1f}s"
        )

    # 8. Final Summaries and Candidate Exposure Audit
    total_elapsed = time.time() - start_time_sec

    final_metrics = {
        "experiment_id": "EXP-06_POSITIVE_BCE_WEIGHT",
        "attempt_id": "EXP06_ATTEMPT_001",
        "best_epoch": best_epoch,
        "best_val_iou": best_val_iou,
        "best_checkpoint_sha256": best_ckpt_sha,
        "last_checkpoint_sha256": last_sha,
        "total_training_duration_seconds": round(total_elapsed, 1),
        "metrics_at_best_epoch": next((h for h in history if h["epoch"] == best_epoch), None),
    }
    atomic_write_json(out_dir / "metrics.json", final_metrics)

    seq_sha = hashlib.sha256(json.dumps(sampled_candidate_sequence).encode()).hexdigest().upper()
    sampled_candidate_audit = {
        "experiment_id": "EXP-06_POSITIVE_BCE_WEIGHT",
        "total_mined_draws": len(sampled_candidate_sequence),
        "retained_pool_size": len(mined_ds),
        "unique_candidates_sampled": len(sampled_candidate_counter),
        "coverage_percentage": round(len(sampled_candidate_counter) / len(mined_ds) * 100.0, 2),
        "min_exposures_per_candidate": min(sampled_candidate_counter.values()) if sampled_candidate_counter else 0,
        "max_exposures_per_candidate": max(sampled_candidate_counter.values()) if sampled_candidate_counter else 0,
        "mean_exposures_per_candidate": round(float(np.mean(list(sampled_candidate_counter.values()))), 2) if sampled_candidate_counter else 0.0,
        "sampled_sequence_sha256": seq_sha,
    }
    atomic_write_json(out_dir / "sampled_candidate_audit.json", sampled_candidate_audit)
    atomic_write_json(out_dir / "loss_balance_audit.json", loss_balance_records)

    final_run_state = {
        "experiment_id": "EXP-06_POSITIVE_BCE_WEIGHT",
        "attempt_id": "EXP06_ATTEMPT_001",
        "pid": os.getpid(),
        "command_line": f"scripts\\train_exp06.py --authorized",
        "git_commit": "542bab19f6f08c9bba8b8762e6480386c8b6026b",
        "status": "COMPLETED",
        "phase": "COMPLETE",
        "start_time_iso": run_manifest["timestamp_start_utc"],
        "last_heartbeat_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "current_epoch": args.epochs,
        "current_batch": batches_per_epoch,
        "completed_batches": total_training_steps,
        "percent_complete": 100.0,
        "eta_seconds": 0,
        "current_train_loss": round(epoch_train_loss, 5),
        "current_lr": optimizer.param_groups[0]["lr"],
        "best_val_iou": best_val_iou,
        "best_epoch": best_epoch,
        "latest_checkpoint": f"best_model.pt (IoU={best_val_iou:.5f}, SHA={best_ckpt_sha[:12]})",
        "gpu_vram_allocated_mb": round(torch.cuda.memory_allocated(0) / (1024 ** 2), 1) if torch.cuda.is_available() else 0.0,
        "failure_reason": None,
    }
    atomic_write_json(state_path, final_run_state)

    print("\n================================================================================")
    print("EXP-06 TRAINING COMPLETE")
    print(f"  Best Epoch:           {best_epoch}")
    print(f"  Best Val IoU:         {best_val_iou:.5f}")
    print(f"  Best Checkpoint SHA:  {best_ckpt_sha}")
    print(f"  Total Duration:       {total_elapsed / 60.0:.1f} minutes")
    print("================================================================================")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EXP-06: ResNet34 U-Net with BCE pos_weight=2.0")
    parser.add_argument("--authorized", action="store_true", help="Confirm CAIO scientific authorization")
    parser.add_argument("--epochs", type=int, default=TOTAL_EPOCHS)
    parser.add_argument("--batch_size", type=int, default=BATCH_SIZE)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight_decay", type=float, default=1e-2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--severity_cap", type=int, default=SEVERITY_CAP_THRESHOLD)
    parser.add_argument("--pos_weight", type=float, default=POS_WEIGHT)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--num_workers", type=int, default=0)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json",
    )
    parser.add_argument(
        "--candidate_manifest",
        type=Path,
        default=REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "exp03_hard_negative_manifest.json",
    )
    parser.add_argument(
        "--teacher_checkpoint",
        type=Path,
        default=REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight",
    )
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    train_exp06(args)


if __name__ == "__main__":
    main()
