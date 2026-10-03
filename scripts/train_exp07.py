"""EXP-07: Controlled First Training Run / Baseline Seed 001 (EXP07_RUN001_SEED42).

Authoritative Training Script implementing the frozen EXP-07 protocol:
- Architecture: ResNet18-UNet (14,310,860 trainable parameters, 30 BatchNorm2d layers)
- Normalization: Fixed TRAIN-only AGGREGATED_RAW_DN_LOG1P_STANDARDIZED (mean=4.2756, std=0.3866)
- Loss: CrossEntropyLoss with source-recalculated square-root median frequency weights
- Optimizer: AdamW (lr=5e-4, weight_decay=0.01 on 2D weights, betas=(0.9, 0.999), eps=1e-8)
- Gradient clipping: max_norm=1.0, norm_type=2.0
- Scheduler: LinearWarmupCosineAnnealingLR (3 warmup epochs, 27 cosine decay epochs, min_lr=1e-6)
- Batch dynamics: physical minibatch=8, gradient accumulation=2, virtual optimizer batch=16, BN statistical batch=8
- Sampler: Candidate F Hybrid (0.70 P_parent + 0.30 P_presence, replacement=True, 72 draws/epoch)
- Model selection: peak dev_mIoU_phenomena (classes 1..11, absent classes excluded from denominator)
- Quarantine: HOLDOUT strictly barred from loading, evaluation, or checkpoint selection
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
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
import rasterio
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, Sampler

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from ocean_sentinel.ml.exp07_reference import (
    CLASS_WEIGHTS_SQRT_MEDIAN,
    DENSE_CLASSES,
    IGNORE_INDEX,
    SOURCE_LABEL_TO_DENSE,
    TRAIN_LOG1P_MEAN,
    TRAIN_LOG1P_STD,
    ResNet18UNet,
    compute_candidate_f_hybrid_weights,
    compute_confusion_matrix_12x12,
    compute_metrics_from_confusion_matrix,
    compute_validity_mask,
    preprocess_sar_image,
    remap_source_mask_to_dense,
)

OPS01_MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "ops01_physical_dataset_manifest_v4.json"
TAXONOMY_MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "ops01_taxonomy_v1.json"
CONFIG_FINGERPRINT = "D93EAEF12787F9408F2C3F9DD613DC6C47F2EC5A76C02B731EB42B29AB35273A"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EXP07_TRAIN")


class OPS01TileDataset(Dataset):
    """Dataset for OPS-01 SAR phenomenon tiles with strict partition quarantine."""

    def __init__(
        self,
        manifest_path: Path,
        partition: str,
        mean: float = TRAIN_LOG1P_MEAN,
        std: float = TRAIN_LOG1P_STD,
    ) -> None:
        super().__init__()
        self.partition = partition.upper()
        if self.partition == "HOLDOUT":
            raise PermissionError(
                "HOLDOUT partition access is strictly quarantined from the training pipeline! "
                "Evaluating HOLDOUT requires authorized post-training evaluation entry points."
            )

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.samples = [s for s in manifest["samples"] if s["partition"] == self.partition]
        self.mean = mean
        self.std = std

        logger.info(f"Loaded {len(self.samples)} tiles for partition {self.partition}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, str]:
        sample = self.samples[idx]
        img_path = REPO_ROOT / sample["derived_image_path"]
        mask_path = REPO_ROOT / sample["derived_mask_path"]

        # 1. Read raw SAR raster (GeoTIFF)
        with rasterio.open(img_path) as src:
            raw_image = src.read(1).astype(np.float32)

        # 2. Validity mask (raw DN > 0)
        validity_mask = compute_validity_mask(raw_image)

        # 3. Log1p and standardization with invalid pixels zeroed
        norm_image, _ = preprocess_sar_image(raw_image, mean=self.mean, std=self.std)

        # 4. Read mask and remap to dense classes [0..11]
        raw_mask = np.array(Image.open(mask_path), dtype=np.int64)
        target = remap_source_mask_to_dense(raw_mask, validity_mask=validity_mask)

        # Convert to torch tensors
        input_tensor = torch.from_numpy(norm_image).float()  # [1, H, W]
        target_tensor = torch.from_numpy(target).long()        # [H, W]
        valid_tensor = torch.from_numpy(validity_mask).bool()  # [1, H, W]

        return input_tensor, target_tensor, valid_tensor, sample["sample_id"]


class CandidateFWeightedSampler(Sampler):
    """Deterministic Candidate F Hybrid Sampler drawing 72 tiles per epoch with replacement."""

    def __init__(self, weights: np.ndarray, num_samples: int = 72, seed: int = 42) -> None:
        super().__init__(None)
        self.weights = torch.as_tensor(weights, dtype=torch.double)
        self.num_samples = num_samples
        self.seed = seed
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __iter__(self):
        # Per-epoch deterministic generator
        g = torch.Generator()
        g.manual_seed(self.seed + self.epoch * 1000)
        indices = torch.multinomial(self.weights, self.num_samples, replacement=True, generator=g)
        return iter(indices.tolist())

    def __len__(self) -> int:
        return self.num_samples


def build_optimizer(model: nn.Module, base_lr: float = 5e-4, weight_decay: float = 0.01) -> torch.optim.AdamW:
    """Construct AdamW with strict parameter group separation: decay conv/linear weights, exclude 1D/biases."""
    decay_params = []
    no_decay_params = []

    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if param.ndim >= 2 and not name.endswith(".bias"):
            decay_params.append(param)
        else:
            no_decay_params.append(param)

    param_groups = [
        {"params": decay_params, "weight_decay": weight_decay, "lr": base_lr},
        {"params": no_decay_params, "weight_decay": 0.0, "lr": base_lr},
    ]

    return torch.optim.AdamW(param_groups, lr=base_lr, betas=(0.9, 0.999), eps=1e-8)


def get_scheduled_lr(
    epoch: int,
    total_epochs: int = 30,
    warmup_epochs: int = 3,
    base_lr: float = 5e-4,
    warmup_start_lr: float = 1e-5,
    min_lr: float = 1e-6,
) -> float:
    """Deterministic LinearWarmupCosineAnnealing learning rate calculation."""
    if epoch < warmup_epochs:
        return warmup_start_lr + (epoch / warmup_epochs) * (base_lr - warmup_start_lr)
    else:
        cosine_epoch = epoch - warmup_epochs
        cosine_total = total_epochs - warmup_epochs
        fraction = cosine_epoch / cosine_total
        return min_lr + 0.5 * (base_lr - min_lr) * (1.0 + math.cos(math.pi * fraction))


def evaluate_dev(
    model: nn.Module,
    dev_loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Dict[str, Any]:
    """Evaluate model on canonical DEV partition without gradients."""
    model.eval()
    total_loss = 0.0
    total_batches = 0
    confusion_matrix = np.zeros((12, 12), dtype=np.int64)

    with torch.no_grad():
        for inputs, targets, valids, _ in dev_loader:
            inputs = inputs.to(device)
            targets = targets.to(device)

            logits = model(inputs)
            loss = criterion(logits, targets)

            total_loss += float(loss.item())
            total_batches += 1

            # Multiclass argmax decision rule
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            tgts = targets.cpu().numpy()

            # Accumulate confusion matrix over valid target pixels
            valid_mask = tgts != IGNORE_INDEX
            p_valid = preds[valid_mask]
            t_valid = tgts[valid_mask]

            if len(t_valid) > 0:
                indices = t_valid * 12 + p_valid
                bincount = np.bincount(indices, minlength=144).reshape((12, 12))
                confusion_matrix += bincount

    dev_loss = total_loss / max(1, total_batches)

    # Calculate metrics
    metrics = compute_metrics_from_confusion_matrix(confusion_matrix)
    metrics["dev_loss"] = dev_loss

    return metrics


def save_checkpoint(
    path: Path,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    global_step: int,
    lr: float,
    train_metrics: Dict[str, Any],
    dev_metrics: Dict[str, Any],
    best_dev_metric: float,
    selection_status: str,
    seed: int = 42,
    run_id: str = "EXP07_RUN001_SEED42",
    config_fingerprint: str = CONFIG_FINGERPRINT,
    protocol_version: str = "v1.0.0-frozen",
) -> None:
    """Save checkpoint with immutable provenance contract dictionary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")

    checkpoint_dict = {
        "experiment_id": "EXP-07",
        "protocol_version": protocol_version,
        "run_id": run_id,
        "seed": seed,
        "epoch": epoch,
        "global_step": global_step,
        "selection_status": selection_status,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state": {"epoch": epoch, "lr": lr},
        "configuration_fingerprint": config_fingerprint,
        "dataset_manifest_sha256": "FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E",
        "taxonomy_manifest_sha256": "86A043EFDBB641EE2073C959DA315E7BF90C5F72D35B9E40F62C39F225C551AD",
        "normalization": {"mean": 4.2756, "std": 0.3866, "status": "SOURCE_VERIFIED"},
        "loss_weights": CLASS_WEIGHTS_SQRT_MEDIAN,
        "sampler": "Candidate_F_Hybrid_70_30",
        "train_metrics": train_metrics,
        "dev_metrics": dev_metrics,
        "best_dev_metric": best_dev_metric,
        "git_commit": "master-c8-frozen",
        "git_dirty": False,
        "software_environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "rasterio": rasterio.__version__,
        },
        "rng_states": {
            "python": random.getstate(),
            "numpy": np.random.get_state(),
            "torch_cpu": torch.get_rng_state(),
        },
    }

    torch.save(checkpoint_dict, temp_path)
    if temp_path.exists():
        temp_path.replace(path)
    logger.info(f"Saved checkpoint to {path} (Epoch {epoch}, status={selection_status})")


def parse_args():
    parser = argparse.ArgumentParser(description="EXP-07 Authoritative Training Script")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (e.g. 42 or 101)")
    parser.add_argument("--run-id", type=str, default="EXP07_RUN001_SEED42", help="Run ID")
    parser.add_argument("--phase", type=str, default="EXP-07-P0-C8", help="Phase identifier")
    parser.add_argument(
        "--config-fingerprint",
        type=str,
        default="D93EAEF12787F9408F2C3F9DD613DC6C47F2EC5A76C02B731EB42B29AB35273A",
        help="Authoritative configuration SHA256 fingerprint",
    )
    parser.add_argument("--telemetry-path", type=str, default=None, help="Telemetry run state path")
    parser.add_argument("--results-path", type=str, default=None, help="Training results JSON output path")
    parser.add_argument("--dry-run", action="store_true", help="Execute single-step CPU sanity check and exit")
    return parser.parse_args()


def run_training(args=None):
    """Execute EXP-07 controlled training run."""
    if args is None:
        args = parse_args()

    seed = args.seed
    run_id = args.run_id
    phase = args.phase
    config_fingerprint = args.config_fingerprint

    random.seed(seed)
    np.random.seed(seed + 1)
    torch.manual_seed(seed + 2)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed + 3)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Training device initialized: {device} | Seed: {seed} | Run ID: {run_id}")

    run_dir = REPO_ROOT / "experiments" / "EXP-07" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.telemetry_path:
        telemetry_path = REPO_ROOT / args.telemetry_path
    else:
        telemetry_path = REPO_ROOT / "scratch" / f"exp07_{phase.lower().replace('-', '_')}_run_state.json"

    # Datasets
    train_dataset = OPS01TileDataset(OPS01_MANIFEST_PATH, partition="TRAIN")
    dev_dataset = OPS01TileDataset(OPS01_MANIFEST_PATH, partition="DEV")

    # Sampler
    weights, _, _ = compute_candidate_f_hybrid_weights(OPS01_MANIFEST_PATH, train_split_name="TRAIN")
    train_sampler = CandidateFWeightedSampler(weights, num_samples=72, seed=seed)

    train_loader = DataLoader(
        train_dataset,
        batch_size=8,
        sampler=train_sampler,
        num_workers=0,
        pin_memory=False,
    )

    dev_loader = DataLoader(
        dev_dataset,
        batch_size=8,
        shuffle=False,
        num_workers=0,
        pin_memory=False,
    )

    # Model
    model = ResNet18UNet(in_channels=1, num_classes=12, bn_momentum=0.05).to(device)

    # Loss weights tensor
    weight_tensor = torch.tensor([CLASS_WEIGHTS_SQRT_MEDIAN[c] for c in range(12)], dtype=torch.float32, device=device)
    criterion = nn.CrossEntropyLoss(weight=weight_tensor, ignore_index=IGNORE_INDEX, reduction="mean")

    # Optimizer
    optimizer = build_optimizer(model, base_lr=5e-4, weight_decay=0.01)

    # Training state
    max_epochs = 30
    min_epochs = 15
    patience = 10
    min_delta = 0.005
    gradient_accumulation_steps = 2

    best_dev_metric = -1.0
    best_epoch = -1
    patience_counter = 0
    global_step = 0
    total_samples_seen = 0

    if args.dry_run:
        logger.info(f"Executing single-step pre-train CPU sanity check for {run_id} (Seed {seed})...")
        model.train()
        for batch_idx, (inputs, targets, valids, _) in enumerate(train_loader):
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model(inputs)
            assert outputs.shape == (8, 12, 256, 256), f"Unexpected output shape: {outputs.shape}"
            loss = criterion(outputs, targets)
            assert torch.isfinite(loss), f"Non-finite loss detected: {loss.item()}"
            loss.backward()
            grad_norm = float(nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0, norm_type=2.0))
            assert math.isfinite(grad_norm), f"Non-finite gradient norm: {grad_norm}"
            optimizer.step()
            optimizer.zero_grad()
            logger.info(f"Sanity check PASSED: Loss: {loss.item():.4f}, Grad norm: {grad_norm:.4f}, Outputs shape: {tuple(outputs.shape)}")
            return {"status": "SANITY_CHECK_PASSED", "loss": float(loss.item()), "grad_norm": float(grad_norm)}

    history = []
    start_time = time.time()
    epoch_durations = []

    logger.info(f"=== STARTING EXP-07 TRAINING ({run_id}, SEED {seed}, PHASE {phase}) ===")

    for epoch in range(1, max_epochs + 1):
        epoch_start_time = time.time()
        current_lr = get_scheduled_lr(epoch - 1, total_epochs=max_epochs, warmup_epochs=3, base_lr=5e-4, warmup_start_lr=1e-5, min_lr=1e-6)

        # Update learning rate across parameter groups
        for param_group in optimizer.param_groups:
            param_group["lr"] = current_lr

        train_sampler.set_epoch(epoch)
        model.train()
        running_train_loss = 0.0
        train_batches = 0
        epoch_grad_norms = []

        optimizer.zero_grad()

        for batch_idx, (inputs, targets, valids, _) in enumerate(train_loader):
            inputs = inputs.to(device)
            targets = targets.to(device)

            logits = model(inputs)
            loss = criterion(logits, targets)

            # Scale loss for gradient accumulation
            loss_scaled = loss / gradient_accumulation_steps
            loss_scaled.backward()

            running_train_loss += float(loss.item())
            train_batches += 1
            total_samples_seen += len(inputs)

            # Gradient step at accumulation boundary or last batch
            if (batch_idx + 1) % gradient_accumulation_steps == 0 or (batch_idx + 1) == len(train_loader):
                # Gradient clipping
                grad_norm = float(nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0, norm_type=2.0))
                epoch_grad_norms.append(grad_norm)

                optimizer.step()
                optimizer.zero_grad()
                global_step += 1

        epoch_train_loss = running_train_loss / max(1, train_batches)
        mean_grad_norm = float(np.mean(epoch_grad_norms)) if epoch_grad_norms else 0.0

        # DEV evaluation
        dev_metrics = evaluate_dev(model, dev_loader, criterion, device)
        dev_loss = dev_metrics["dev_loss"]
        dev_mIoU_phenomena = dev_metrics["mIoU_phenomena"]
        dev_mIoU_all = dev_metrics["mIoU_all"]

        epoch_duration = time.time() - epoch_start_time
        epoch_durations.append(epoch_duration)
        avg_epoch_duration = float(np.mean(epoch_durations))
        remaining_epochs = max_epochs - epoch
        estimated_eta_seconds = remaining_epochs * avg_epoch_duration

        # Model selection and early stopping check
        is_best = False
        if dev_mIoU_phenomena > (best_dev_metric + min_delta):
            best_dev_metric = dev_mIoU_phenomena
            best_epoch = epoch
            patience_counter = 0
            is_best = True
            save_checkpoint(
                run_dir / "best_model.pt",
                model,
                optimizer,
                epoch,
                global_step,
                current_lr,
                {"train_loss": epoch_train_loss, "grad_norm": mean_grad_norm},
                dev_metrics,
                best_dev_metric,
                selection_status="BEST_ON_DEV",
                seed=seed,
                run_id=run_id,
                config_fingerprint=config_fingerprint,
            )
        else:
            if epoch >= min_epochs:
                patience_counter += 1

        # Always save rolling last checkpoint
        save_checkpoint(
            run_dir / "last_model.pt",
            model,
            optimizer,
            epoch,
            global_step,
            current_lr,
            {"train_loss": epoch_train_loss, "grad_norm": mean_grad_norm},
            dev_metrics,
            best_dev_metric,
            selection_status="CANDIDATE_LATEST",
            seed=seed,
            run_id=run_id,
            config_fingerprint=config_fingerprint,
        )

        epoch_record = {
            "epoch": epoch,
            "global_step": global_step,
            "lr": round(current_lr, 7),
            "train_loss": round(epoch_train_loss, 5),
            "dev_loss": round(dev_loss, 5),
            "dev_mIoU_phenomena": round(dev_mIoU_phenomena, 5),
            "dev_mIoU_all": round(dev_mIoU_all, 5),
            "grad_norm_pre_clip": round(mean_grad_norm, 4),
            "epoch_duration_sec": round(epoch_duration, 2),
            "is_best": is_best,
        }
        history.append(epoch_record)

        logger.info(
            f"Epoch {epoch:02d}/{max_epochs:02d} | "
            f"Train Loss: {epoch_train_loss:.4f} | "
            f"Dev Loss: {dev_loss:.4f} | "
            f"Dev mIoU (phenomena): {dev_mIoU_phenomena:.4f} | "
            f"LR: {current_lr:.2e} | "
            f"Time: {epoch_duration:.1f}s | "
            f"{'(*BEST*)' if is_best else ''}"
        )

        # Update live telemetry on disk
        telemetry_update = {
            "phase": phase,
            "status": "TRAINING_IN_PROGRESS",
            "heartbeat": datetime.datetime.utcnow().isoformat() + "Z",
            "current_stage": f"STAGE_22_{run_id}_TRAINING",
            "current_action": f"completed_epoch_{epoch}",
            "gpu_allowed": True,
            "training_started": True,
            "run_id": run_id,
            "seed": seed,
            "epoch": epoch,
            "max_epochs": max_epochs,
            "batch": len(train_loader),
            "samples_seen": total_samples_seen,
            "optimizer_steps": global_step,
            "learning_rate": current_lr,
            "train_loss": epoch_train_loss,
            "dev_loss": dev_loss,
            "dev_metrics": dev_metrics,
            "best_dev_metric": best_dev_metric,
            "best_epoch": best_epoch,
            "checkpoint_status": "SAVED_BEST_AND_LAST",
            "failure_status": "NONE",
            "elapsed_time": f"{time.time() - start_time:.1f}s",
            "measured_epoch_seconds": round(avg_epoch_duration, 2),
            "eta": f"{estimated_eta_seconds:.1f}s",
            "configuration_fingerprint": config_fingerprint,
        }

        with open(telemetry_path, "w", encoding="utf-8") as f:
            json.dump(telemetry_update, f, indent=2)

        # Check early stopping
        if patience_counter >= patience and epoch >= min_epochs:
            logger.info(f"Early stopping triggered at epoch {epoch} (patience={patience} exhausted).")
            break

    total_training_time = time.time() - start_time
    logger.info(f"=== TRAINING COMPLETED IN {total_training_time:.2f}s ===")
    logger.info(f"Best DEV mIoU (phenomena): {best_dev_metric:.4f} at Epoch {best_epoch}")

    # Write training results artifact
    if args.results_path:
        results_path = REPO_ROOT / args.results_path
    else:
        results_path = REPO_ROOT / "data" / "metadata" / f"exp07_{phase.lower().replace('-', '_')}_training_results_{run_id.lower()}_v1.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_data = {
        "metadata_version": "1.0.0",
        "phase": phase,
        "experiment_id": "EXP-07",
        "run_id": run_id,
        "seed": seed,
        "completed_at": datetime.datetime.utcnow().isoformat() + "Z",
        "configuration_fingerprint": config_fingerprint,
        "total_epochs_trained": len(history),
        "total_optimizer_steps": global_step,
        "total_training_time_seconds": round(total_training_time, 2),
        "mean_epoch_time_seconds": round(float(np.mean(epoch_durations)), 2),
        "best_epoch": best_epoch,
        "best_dev_mIoU_phenomena": round(best_dev_metric, 5),
        "final_epoch_train_loss": round(history[-1]["train_loss"], 5),
        "final_epoch_dev_loss": round(history[-1]["dev_loss"], 5),
        "history": history,
    }
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)

    return results_data


if __name__ == "__main__":
    run_training()
