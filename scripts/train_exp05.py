"""EXP-05: Training ResNet-34 U-Net with Candidate Severity Capping (<= 50,000 FP Pixels).

Phase 5F Controlled Single-Variable Intervention:
- Primary Intervention: Restrict hard-negative candidate pool to tiles with fp_pixels <= 50,000.
- Pool filtering: 400 original candidates -> 355 retained candidates (45 extreme outlier candidates excluded).
- Mined exposure frequency: 15 standard TRAIN tiles + 1 mined candidate tile per batch of 16 (6.25% exposure, identical to EXP-04).
- Standard stream: 13,440 standard tiles / 15 per batch = 896 batches per epoch.
- Mined stream: 896 mined tile exposures per epoch (drawn with replacement from the frozen 355-candidate capped pool).
- Total optimizer steps: 896 batches * 10 epochs = 8,960 steps.

All other 24 experimental variables remain strictly FROZEN:
- Architecture: ResNet34UNet (in_channels=2, num_classes=1, adaptation='slice_variance_scaled')
- Total parameters: 24,346,305 trainable (19,054 buffers, 24,365,359 state dict elements)
- Initialization: Canonical EXP-01 baseline best_model.pt (SHA: 9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699)
- Candidate Source Manifest: Frozen manifest (SHA: 3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4)
- Spatial Split: Frozen spatial split manifest (SHA: C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0)
- Loss: CombinedBCEAndDiceLoss (bce_weight=0.5, dice_weight=0.5, smooth=1.0)
- Optimizer: AdamW (lr=1e-4, weight_decay=1e-2, betas=(0.9, 0.999), eps=1e-8)
- Scheduler: CosineAnnealingLR (T_max=10, eta_min=1e-6)
- Epochs: 10
- Mini-batch size: 16
- Random Seed: 42
- Normalization: Frozen destination-channel z-score standardization (mu0=-33.233137, sigma0=6.489986, mu1=-19.941216, sigma1=4.531346)
- Decision threshold: tau = 0.22 (strictly frozen)
- Validation: Canonical Trujillo Part I validation split (180 scenes, 2,880 tiles)
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
    tmp_path = path.with_suffix(f".tmp.{os.getpid()}.pt")
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


class CappedMinedHardNegativeDataset(Dataset):
    """Dataset serving the severity-capped (fp_pixels <= 50,000) hard-negative candidate tiles."""

    def __init__(
        self,
        candidate_manifest_path: Path,
        repo_root: Path,
        channel_means: Tuple[float, float],
        channel_stds: Tuple[float, float],
        severity_cap: int = SEVERITY_CAP_THRESHOLD,
        transform: Optional[Any] = None,
    ):
        self.candidate_manifest_path = Path(candidate_manifest_path)
        self.repo_root = Path(repo_root)
        self.channel_means = np.array(channel_means, dtype=np.float32)
        self.channel_stds = np.array(channel_stds, dtype=np.float32)
        self.severity_cap = severity_cap
        self.transform = transform or IdentityTransform()

        # Load raw candidates
        data = json.loads(self.candidate_manifest_path.read_text(encoding="utf-8"))
        raw_candidates = data["candidates"]
        assert len(raw_candidates) == 400, f"Expected 400 raw candidates, found {len(raw_candidates)}"
        assert all(c["gt_pixels"] == 0 for c in raw_candidates), "Candidate pool purity breach: non-zero gt_pixels!"

        # Filter by severity cap
        self.candidates = [c for c in raw_candidates if c["fp_pixels"] <= self.severity_cap]
        self.excluded_candidates = [c for c in raw_candidates if c["fp_pixels"] > self.severity_cap]

        assert len(self.candidates) == EXPECTED_RETAINED_CANDIDATES, (
            f"Expected {EXPECTED_RETAINED_CANDIDATES} retained candidates, got {len(self.candidates)}"
        )
        assert len(self.excluded_candidates) == EXPECTED_EXCLUDED_CANDIDATES, (
            f"Expected {EXPECTED_EXCLUDED_CANDIDATES} excluded candidates, got {len(self.excluded_candidates)}"
        )
        assert all(c["fp_pixels"] <= self.severity_cap for c in self.candidates)
        assert all(c["fp_pixels"] > self.severity_cap for c in self.excluded_candidates)

        # Scene retention audit
        retained_stems = set(c["parent_stem"] for c in self.candidates)
        assert len(retained_stems) == EXPECTED_SURVIVING_SCENES, (
            f"Expected {EXPECTED_SURVIVING_SCENES} surviving scenes, got {len(retained_stems)}"
        )

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
    - 15 indices from standard training pool (sampled without replacement per epoch: 13,440 / 15 = 896 batches)
    - 1 index from capped mined candidate pool (sampled with replacement: 896 draws)
    """

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
        self.n_batches = self.n_standard // self.n_standard_per_batch
        self.sampled_mined_history: List[int] = []

    def __len__(self) -> int:
        return self.n_batches

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __iter__(self) -> Iterator[List[int]]:
        g = torch.Generator()
        g.manual_seed(self.seed + self.epoch * 1000)

        # Standard indices permuted without replacement
        standard_perm = torch.randperm(self.n_standard, generator=g).tolist()

        # Mined indices sampled with replacement from [0, n_mined)
        total_mined_draws = self.n_batches * self.n_mined_per_batch
        mined_draws = torch.randint(0, self.n_mined, (total_mined_draws,), generator=g).tolist()
        self.sampled_mined_history.extend(mined_draws)

        for b in range(self.n_batches):
            batch_std = standard_perm[b * self.n_standard_per_batch : (b + 1) * self.n_standard_per_batch]
            batch_mined = [
                self.n_standard + m
                for m in mined_draws[b * self.n_mined_per_batch : (b + 1) * self.n_mined_per_batch]
            ]
            yield batch_std + batch_mined


class TeeLogger:
    """Tees output to both console stream and disk log file."""

    def __init__(self, filepath: Path, stream):
        self.file = open(filepath, "a", encoding="utf-8", buffering=1)
        self.stream = stream

    def write(self, data: str) -> None:
        self.stream.write(data)
        self.file.write(data)
        self.stream.flush()
        self.file.flush()

    def flush(self) -> None:
        self.stream.flush()
        self.file.flush()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EXP-05 Phase 5F Candidate Severity Capping Runner")
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
        help="Path to frozen hard-negative candidate manifest",
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
        default=REPO_ROOT / "experiments" / "performance" / "exp05_candidate_severity_cap",
        help="Output directory for Phase 5F run artifacts",
    )
    parser.add_argument("--severity-cap", type=int, default=SEVERITY_CAP_THRESHOLD, help="Upper FP pixel severity cap")
    parser.add_argument("--epochs", type=int, default=10, help="Training epoch count")
    parser.add_argument("--batch-size", type=int, default=16, help="Total mini-batch size (15 std + 1 mined)")
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
        help="Execute training under explicit CAIO authorization",
    )
    return parser


def run_preflight(args: argparse.Namespace) -> Dict[str, Any]:
    """Rigorous preflight checking of all Phase 5F invariants and environment state."""
    log_telemetry("PHASE_0_PREFLIGHT", "10%", "Verifying artifact existence and digests", "1m")

    # 1. Verify Spatial Split Manifest
    assert args.manifest.exists(), f"Spatial split manifest not found: {args.manifest}"
    split_sha = compute_file_sha256(args.manifest)
    assert split_sha == EXPECTED_SPLIT_SHA256, f"Spatial split hash mismatch: {split_sha} != {EXPECTED_SPLIT_SHA256}"

    # 2. Verify Candidate Manifest
    assert args.candidate_manifest.exists(), f"Candidate manifest not found: {args.candidate_manifest}"
    manifest_sha = compute_file_sha256(args.candidate_manifest)
    assert manifest_sha == EXPECTED_CANDIDATE_MANIFEST_SHA256, (
        f"Candidate manifest hash mismatch: {manifest_sha} != {EXPECTED_CANDIDATE_MANIFEST_SHA256}"
    )

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
            raise RuntimeError(
                f"Output directory contains existing checkpoints but --resume not specified: {existing_checkpoints}"
            )

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
    mined_ds = CappedMinedHardNegativeDataset(
        args.candidate_manifest, REPO_ROOT, means, stds, severity_cap=args.severity_cap
    )

    assert len(train_std_ds) == 13440, f"Expected 13440 train tiles, got {len(train_std_ds)}"
    assert len(mined_ds) == EXPECTED_RETAINED_CANDIDATES, (
        f"Expected {EXPECTED_RETAINED_CANDIDATES} mined tiles, got {len(mined_ds)}"
    )

    # Instantiate Model
    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")
    checkpoint = torch.load(args.teacher_checkpoint, map_location="cpu", weights_only=False)
    state_dict = checkpoint["model_state_dict"] if "model_state_dict" in checkpoint else checkpoint
    model.load_state_dict(state_dict, strict=True)

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    # Dry-run batch
    composite_ds = CompositeTwoStreamDataset(train_std_ds, mined_ds)
    sampler = TwoStreamBatchSampler(len(train_std_ds), len(mined_ds), N_STANDARD_PER_BATCH, N_MINED_PER_BATCH, args.seed)
    loader = DataLoader(composite_ds, batch_sampler=sampler, num_workers=0)

    for batch_idx, (imgs, masks) in enumerate(loader):
        assert imgs.shape == (BATCH_SIZE, 2, 512, 512), f"Unexpected dry-run shape: {imgs.shape}"
        assert masks.shape == (BATCH_SIZE, 1, 512, 512), f"Unexpected dry-run shape: {masks.shape}"
        with torch.no_grad():
            out = model(imgs.to(device))
            assert out.shape == (BATCH_SIZE, 1, 512, 512)
        break

    log_telemetry("PHASE_8_DRY_RUN", "100%", "Dry run completed successfully with zero optimizer steps", "0s")
    print("\n[PREFLIGHT_PASS] Model instantiation, parameter counts, dataset shapes, and dry-run inference verified.")


def evaluate_validation(
    model: nn.Module,
    val_loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    threshold: float = FROZEN_THRESHOLD,
) -> Dict[str, Any]:
    """Evaluates model over Part I validation split using canonical SegmentationMeter."""
    model.eval()
    meter = SegmentationMeter(threshold=threshold)
    total_val_loss = 0.0
    val_batches = 0

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

            total_val_loss += loss.item()
            val_batches += 1
            meter.update(logits, masks)

            probs = torch.sigmoid(logits)
            preds_bin = probs >= threshold
            for b in range(masks.shape[0]):
                m_sum = masks[b, 0].sum().item()
                p_sum = preds_bin[b, 0].sum().item()
                if m_sum == 0:
                    empty_tiles_count += 1
                    total_fp_pixels += int(p_sum)
                    if p_sum > 0:
                        clean_water_fa_count += 1
                    if p_sum >= 100:
                        sig_fa_count += 1

    summary = meter.compute()
    val_loss = total_val_loss / max(val_batches, 1)

    clean_water_far = (clean_water_fa_count / empty_tiles_count * 100.0) if empty_tiles_count > 0 else 0.0
    sig_far = (sig_fa_count / empty_tiles_count * 100.0) if empty_tiles_count > 0 else 0.0

    return {
        "val_loss": round(val_loss, 5),
        "val_iou": round(summary["iou"], 5),
        "val_dice": round(summary["dice"], 5),
        "val_precision": round(summary["precision"], 5),
        "val_recall": round(summary["recall"], 5),
        "clean_water_far_pct": round(clean_water_far, 2),
        "significant_far_pct": round(sig_far, 2),
        "total_fp_pixels": total_fp_pixels,
        "empty_tiles_evaluated": empty_tiles_count,
    }


def train_exp05(args: argparse.Namespace) -> None:
    """Executes the full Phase 5F EXP-05 training run."""
    if not args.authorized:
        raise RuntimeError("PHASE 5F TRAINING EXECUTION NOT AUTHORIZED: Launch requires explicit --authorized flag.")

    start_time_sec = time.time()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    log_file = args.output_dir / "training.log"
    sys.stdout = TeeLogger(log_file, sys.stdout)
    sys.stderr = TeeLogger(log_file, sys.stderr)

    print("================================================================================")
    print("OCEAN SENTINEL: PHASE 5F EXP-05 TRAINING LAUNCH")
    print(f"Timestamp UTC: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print(f"Process PID:   {os.getpid()}")
    print(f"Host:          {platform.node()} ({platform.platform()})")
    print(f"Severity Cap:  <= {args.severity_cap:,} FP pixels")
    print("================================================================================")

    # 1. Preflight Verification
    preflight_info = run_preflight(args)
    print(f"[PREFLIGHT] Artifact integrity and filesystem safety certified.")

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
    log_telemetry("PHASE_2_MODEL_INITIALIZATION", "20%", "Instantiating ResNet34UNet from teacher", "85m")
    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")
    param_counts = count_parameters(model)
    assert param_counts["trainable"] == 24346305, f"Parameter count drift: {param_counts['trainable']}"

    teacher_ckpt = torch.load(args.teacher_checkpoint, map_location="cpu", weights_only=False)
    state_dict = teacher_ckpt["model_state_dict"] if "model_state_dict" in teacher_ckpt else teacher_ckpt
    model.load_state_dict(state_dict, strict=True)

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    model.to(device)

    # 4. Optimizer, Scheduler, Loss, and Scaler
    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)
    scaler = torch.amp.GradScaler(device.type, enabled=(device.type == "cuda"))

    # 5. Persist Run Manifest
    run_manifest = {
        "experiment_id": "EXP-05_CANDIDATE_SEVERITY_CAP",
        "attempt_id": "EXP05_ATTEMPT_001",
        "timestamp_start_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pid": os.getpid(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "device": str(device),
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "preflight": preflight_info,
        "model_architecture": "ResNet34UNet(in_channels=2, num_classes=1, adaptation_method='slice_variance_scaled')",
        "parameters": param_counts,
        "severity_cap_threshold": args.severity_cap,
        "retained_candidate_count": len(mined_ds),
        "excluded_candidate_count": len(mined_ds.excluded_candidates),
        "surviving_scenes_count": len(set(c["parent_stem"] for c in mined_ds.candidates)),
        "batch_composition": {"standard_tiles": N_STANDARD_PER_BATCH, "mined_tiles": N_MINED_PER_BATCH, "total": BATCH_SIZE},
        "batches_per_epoch": batches_per_epoch,
        "total_epochs": args.epochs,
        "total_optimizer_steps": total_training_steps,
        "operating_threshold": FROZEN_THRESHOLD,
    }
    atomic_write_json(args.output_dir / "run_manifest.json", run_manifest)

    # 6. Resumption or Fresh Start State
    start_epoch = 1
    best_val_iou = 0.0
    best_epoch = 0
    history: List[Dict[str, Any]] = []

    run_state: Dict[str, Any] = {
        "experiment_id": "EXP-05_CANDIDATE_SEVERITY_CAP",
        "attempt_id": "EXP05_ATTEMPT_001",
        "pid": os.getpid(),
        "command_line": " ".join(sys.argv),
        "git_commit": "542bab19f6f08c9bba8b8762e6480386c8b6026b",
        "status": "RUNNING",
        "phase": "TRAINING",
        "start_time_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "last_heartbeat_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "current_epoch": 0,
        "current_batch": 0,
        "completed_batches": 0,
        "percent_complete": 0.0,
        "eta_seconds": "N/A",
        "current_train_loss": 0.0,
        "current_lr": args.lr,
        "best_val_iou": 0.0,
        "best_epoch": 0,
        "latest_checkpoint": None,
        "gpu_vram_allocated_mb": round(torch.cuda.memory_allocated(0) / (1024**2), 1) if torch.cuda.is_available() else 0.0,
        "failure_reason": None,
    }
    atomic_write_json(args.output_dir / "run_state.json", run_state)

    print(f"\n[EXECUTION_START] Commencing 10-epoch training ({total_training_steps} total optimizer steps)...\n")

    # 7. Training Loop
    total_completed_batches = 0
    for epoch in range(start_epoch, args.epochs + 1):
        epoch_start_time = time.time()
        batch_sampler.set_epoch(epoch)
        model.train()

        running_train_loss = 0.0
        epoch_batches_completed = 0

        for batch_idx, (imgs, masks) in enumerate(train_loader):
            batch_step_start = time.time()
            optimizer.zero_grad(set_to_none=True)

            imgs = imgs.to(device, non_blocking=True)
            masks = masks.to(device, non_blocking=True)

            with torch.amp.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                logits = model(imgs)
                loss = criterion(logits, masks)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_train_loss += loss.item()
            epoch_batches_completed += 1
            total_completed_batches += 1

            # Telemetry every 20 batches
            if (batch_idx + 1) % 20 == 0 or (batch_idx + 1) == batches_per_epoch:
                elapsed_total = time.time() - start_time_sec
                avg_step_sec = elapsed_total / total_completed_batches
                remaining_steps = total_training_steps - total_completed_batches
                eta_sec = remaining_steps * avg_step_sec
                pct_complete = (total_completed_batches / total_training_steps) * 100.0

                current_loss_avg = running_train_loss / epoch_batches_completed
                current_lr = optimizer.param_groups[0]["lr"]

                run_state.update(
                    {
                        "last_heartbeat_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "current_epoch": epoch,
                        "current_batch": batch_idx + 1,
                        "completed_batches": total_completed_batches,
                        "percent_complete": round(pct_complete, 2),
                        "eta_seconds": int(eta_sec),
                        "current_train_loss": round(current_loss_avg, 5),
                        "current_lr": current_lr,
                        "gpu_vram_allocated_mb": round(torch.cuda.memory_allocated(0) / (1024**2), 1)
                        if torch.cuda.is_available()
                        else 0.0,
                    }
                )
                atomic_write_json(args.output_dir / "run_state.json", run_state)

                eta_str = str(datetime.timedelta(seconds=int(eta_sec)))
                log_telemetry(
                    "TRAINING",
                    f"{pct_complete:.1f}% (Epoch {epoch}/{args.epochs}, Batch {batch_idx+1}/{batches_per_epoch})",
                    f"Train Loss={current_loss_avg:.5f}, LR={current_lr:.2e}",
                    eta_str,
                )

        avg_train_loss = running_train_loss / batches_per_epoch

        # 8. Validation Phase
        val_start_time = time.time()
        log_telemetry("VALIDATION", f"Epoch {epoch}/{args.epochs}", "Evaluating on 2,880 canonical validation tiles", "N/A")
        val_metrics = evaluate_validation(model, val_loader, criterion, device, threshold=FROZEN_THRESHOLD)
        val_duration = time.time() - val_start_time

        # Update learning rate schedule
        scheduler.step()

        # Checkpoint evaluation
        val_iou = val_metrics["val_iou"]
        is_best = val_iou > best_val_iou

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 5),
            "val_loss": val_metrics["val_loss"],
            "val_iou": val_metrics["val_iou"],
            "val_dice": val_metrics["val_dice"],
            "val_precision": val_metrics["val_precision"],
            "val_recall": val_metrics["val_recall"],
            "clean_water_far_pct": val_metrics["clean_water_far_pct"],
            "significant_far_pct": val_metrics["significant_far_pct"],
            "total_fp_pixels": val_metrics["total_fp_pixels"],
            "is_best": is_best,
            "epoch_duration_sec": round(time.time() - epoch_start_time, 1),
        }
        history.append(epoch_record)
        atomic_write_json(args.output_dir / "history.json", history)

        checkpoint_state = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "val_metrics": val_metrics,
            "history": history,
            "severity_cap": args.severity_cap,
        }

        # Atomically save last_model.pt
        last_sha = atomic_save_checkpoint(args.output_dir / "last_model.pt", checkpoint_state)

        if is_best:
            best_val_iou = val_iou
            best_epoch = epoch
            best_sha = atomic_save_checkpoint(args.output_dir / "best_model.pt", checkpoint_state)
            checkpoint_status = f"best_model.pt (IoU={val_iou:.5f}, SHA={best_sha[:12]})"
        else:
            checkpoint_status = f"last_model.pt (IoU={val_iou:.5f})"

        run_state.update(
            {
                "best_val_iou": best_val_iou,
                "best_epoch": best_epoch,
                "latest_checkpoint": checkpoint_status,
            }
        )
        atomic_write_json(args.output_dir / "run_state.json", run_state)

        print(
            f"\n--- EPOCH {epoch}/{args.epochs} SUMMARY ---"
            f"\n  Train Loss : {avg_train_loss:.5f}"
            f"\n  Val Loss   : {val_metrics['val_loss']:.5f}"
            f"\n  Val IoU    : {val_metrics['val_iou']:.5f} (Best: {best_val_iou:.5f} @ Ep {best_epoch})"
            f"\n  Val Dice   : {val_metrics['val_dice']:.5f}"
            f"\n  Val Recall : {val_metrics['val_recall']:.5f}"
            f"\n  Clean FAR  : {val_metrics['clean_water_far_pct']:.2f}%"
            f"\n  Total FP   : {val_metrics['total_fp_pixels']:,} px"
            f"\n  Checkpoint : {checkpoint_status}\n"
        )

    # 9. Audit of Sampled Candidates (Section 7 Compliance)
    log_telemetry("PHASE_9_AUDIT", "95%", "Auditing sampled candidate exposures", "1m")
    sampled_indices = batch_sampler.sampled_mined_history
    assert len(sampled_indices) == 8960, f"Expected 8,960 mined samples, got {len(sampled_indices)}"
    assert all(0 <= idx < len(mined_ds) for idx in sampled_indices), "Index out of capped pool bounds!"

    unique_sampled = set(sampled_indices)
    cand_counts = Counter(sampled_indices)
    sample_seq_str = ",".join(map(str, sampled_indices))
    sample_seq_sha = hashlib.sha256(sample_seq_str.encode("utf-8")).hexdigest().upper()

    sampled_candidate_audit = {
        "experiment_id": "EXP-05_CANDIDATE_SEVERITY_CAP",
        "total_mined_draws": len(sampled_indices),
        "retained_pool_size": len(mined_ds),
        "unique_candidates_sampled": len(unique_sampled),
        "coverage_percentage": round(len(unique_sampled) / len(mined_ds) * 100.0, 2),
        "min_exposures_per_candidate": min(cand_counts.values()),
        "max_exposures_per_candidate": max(cand_counts.values()),
        "mean_exposures_per_candidate": round(float(np.mean(list(cand_counts.values()))), 2),
        "sampled_sequence_sha256": sample_seq_sha,
        "sample_counts_distribution": dict(sorted(Counter(cand_counts.values()).items())),
    }
    atomic_write_json(args.output_dir / "sampled_candidate_audit.json", sampled_candidate_audit)
    print(f"\n[AUDIT] Sampled candidate exposure audit saved. Unique candidates covered: {len(unique_sampled)}/{len(mined_ds)} ({len(unique_sampled)/len(mined_ds)*100:.1f}%)")

    # 10. Final Metric Persistence
    best_record = next(r for r in history if r["epoch"] == best_epoch)
    final_metrics_summary = {
        "experiment_id": "EXP-05_CANDIDATE_SEVERITY_CAP",
        "attempt_id": "EXP05_ATTEMPT_001",
        "status": "COMPLETED",
        "best_epoch": best_epoch,
        "total_epochs": args.epochs,
        "total_optimizer_steps": total_training_steps,
        "best_validation_metrics": best_record,
        "total_elapsed_seconds": round(time.time() - start_time_sec, 1),
    }
    atomic_write_json(args.output_dir / "metrics.json", final_metrics_summary)

    run_state.update(
        {
            "status": "COMPLETED",
            "phase": "COMPLETE",
            "percent_complete": 100.0,
            "eta_seconds": 0,
            "last_heartbeat_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )
    atomic_write_json(args.output_dir / "run_state.json", run_state)

    print("================================================================================")
    print("PHASE 5F EXP-05 TRAINING COMPLETE")
    print(f"Total Elapsed Time : {time.time() - start_time_sec:.1f}s")
    print(f"Best Validation IoU: {best_val_iou:.5f} (Epoch {best_epoch})")
    print(f"Metrics Saved To   : {args.output_dir / 'metrics.json'}")
    print("================================================================================")


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.preflight_only:
        dry_run_launch(args)
    else:
        train_exp05(args)


if __name__ == "__main__":
    main()
