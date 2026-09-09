"""Canonical EXP-01 specification, immutable fingerprint generator, and configuration verifier.

This module establishes the authoritative ground truth for EXP-01 (Baseline ResNet-34 U-Net, Rev B).
Any attempt to deviate from these parameters (e.g. lr=5e-4 instead of 1e-4, or CosineAnnealingWarmRestarts
instead of CosineAnnealingLR) is treated as scientific experiment drift and rejected.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict

# ===========================================================================
# Authoritative EXP-01 Canonical Constants
# ===========================================================================

EXP01_NAME = "EXP-01"
EXP01_REVISION = "Rev B"
EXP01_DESCRIPTION = "Baseline ResNet-34 U-Net Oil-Spill Segmentation (Rev B)"

# Model
CANONICAL_MODEL_ARCHITECTURE = "ResNet34UNet"
CANONICAL_INPUT_CHANNELS = 2
CANONICAL_OUTPUT_CHANNELS = 1
CANONICAL_ADAPTATION_METHOD = "slice_variance_scaled"
CANONICAL_TOTAL_PARAMETERS = 24_346_305
CANONICAL_TRAINABLE_PARAMETERS = 24_346_305
CANONICAL_NON_TRAINABLE_PARAMETERS = 0
CANONICAL_PRETRAINED_BACKBONE = True

# Loss
CANONICAL_LOSS_CLASS = "CombinedBCEAndDiceLoss"
CANONICAL_LOSS_BCE_WEIGHT = 0.5
CANONICAL_LOSS_DICE_WEIGHT = 0.5
CANONICAL_LOSS_DICE_SMOOTH = 1.0

# Optimizer
CANONICAL_OPTIMIZER_CLASS = "AdamW"
CANONICAL_OPTIMIZER_LR = 1e-4  # 0.0001 — strictly certified
CANONICAL_OPTIMIZER_WEIGHT_DECAY = 1e-2  # 0.01 — strictly certified
CANONICAL_OPTIMIZER_BETAS = (0.9, 0.999)
CANONICAL_OPTIMIZER_EPS = 1e-8

# Scheduler
CANONICAL_SCHEDULER_CLASS = "CosineAnnealingLR"
CANONICAL_SCHEDULER_T_MAX = 30
CANONICAL_SCHEDULER_ETA_MIN = 1e-6

# Training Lifecycle & Policy
CANONICAL_MAX_EPOCHS = 30
CANONICAL_EARLY_STOPPING_PATIENCE = 10
CANONICAL_PHYSICAL_BATCH_SIZE = 8
CANONICAL_ACCUMULATION_STEPS = 1
CANONICAL_EFFECTIVE_BATCH_SIZE = 8
CANONICAL_SEED = 42
CANONICAL_NUM_WORKERS = 4
CANONICAL_AMP_ENABLED = True
CANONICAL_AMP_PRECISION = "CUDA FP16"

# Dataset & Manifest
CANONICAL_DATASET_NAME = "Trujillo Part I Oil Spill Dataset"
CANONICAL_MANIFEST_REL_PATH = "data/metadata/trujillo_2024/spatial_split_manifest.json"
CANONICAL_MANIFEST_SHA256 = "C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0"
CANONICAL_TOTAL_PATCHES = 1200
CANONICAL_TOTAL_TILES = 19200
CANONICAL_TRAIN_PATCHES = 840
CANONICAL_TRAIN_TILES = 13440
CANONICAL_VAL_PATCHES = 180
CANONICAL_VAL_TILES = 2880
CANONICAL_TEST_PATCHES = 180
CANONICAL_TEST_TILES = 2880
CANONICAL_NORMALIZATION_TYPE = "training_derived_zscore"

# Evaluation & Certified Results
CANONICAL_SELECTION_METRIC = "Validation Global IoU"
CANONICAL_BEST_EPOCH = 4
CANONICAL_BEST_VAL_IOU = 0.71691
CANONICAL_STOPPED_EPOCH = 14
CANONICAL_SELECTED_THRESHOLD = 0.22
CANONICAL_TEST_IOU = 0.78434
CANONICAL_TEST_DICE = 0.87914
CANONICAL_TEST_PRECISION = 0.81713
CANONICAL_TEST_RECALL = 0.95133

# Certified Artifact SHA-256 Hashes
CERTIFIED_BASELINE_HASHES = {
    "best_model.pt": "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699",
    "final_model.pt": "2E4C0881DF2F16810C4494A4071EAB320D12418151CC5F74651E91FE1F0A41AA",
    "latest_checkpoint.pt": "2F8F7718D687FF1621F4D92FD7190AE3D582AC67CCD2A529F72E1088A139AA6A",
    "history.json": "E2B5EB5229E2529E1659E77D285E93275015F58DEDCA5AF1F539E45544D5FCBA",
    "config.json": "2DF14570974288E0E6985393E139F3E23F4DD02A02C008C8F1CF00060D9A10EA",
    "run_state.json": "F8EC3B5D461F13C8B4673E038E90CE6385E57F0B39EDD5B73156AAAD2DD0178C",
}


# ===========================================================================
# Verification Functions
# ===========================================================================

def verify_canonical_exp01_config(config: Dict[str, Any]) -> None:
    """Verify that a given configuration dictionary strictly matches canonical EXP-01.

    Raises AssertionError if any parameter deviates from certified EXP-01 baseline.
    """
    # 1. Learning rate check
    lr = config.get("lr")
    if lr is not None:
        lr_float = float(lr)
        if abs(lr_float - CANONICAL_OPTIMIZER_LR) > 1e-9:
            raise AssertionError(
                f"EXP-01 LR mismatch: expected {CANONICAL_OPTIMIZER_LR} (1e-4), "
                f"got {lr_float}. (Deviation from certified EXP-01 baseline)."
            )

    # 2. Weight decay check
    wd = config.get("weight_decay")
    if wd is not None:
        wd_float = float(wd)
        if abs(wd_float - CANONICAL_OPTIMIZER_WEIGHT_DECAY) > 1e-9:
            raise AssertionError(
                f"EXP-01 weight_decay mismatch: expected {CANONICAL_OPTIMIZER_WEIGHT_DECAY} (1e-2), "
                f"got {wd_float}."
            )

    # 3. Scheduler class check
    sched = config.get("scheduler") or config.get("scheduler_class")
    if sched is not None:
        if sched != CANONICAL_SCHEDULER_CLASS:
            raise AssertionError(
                f"EXP-01 scheduler mismatch: expected '{CANONICAL_SCHEDULER_CLASS}', "
                f"got '{sched}'. CosineAnnealingWarmRestarts or other variants violate EXP-01 identity."
            )

    # 4. Epochs check
    epochs = config.get("epochs") or config.get("max_epochs")
    if epochs is not None:
        epochs_int = int(epochs)
        if epochs_int != CANONICAL_MAX_EPOCHS:
            raise AssertionError(
                f"EXP-01 epochs mismatch: expected {CANONICAL_MAX_EPOCHS}, got {epochs_int}."
            )

    # 5. Patience check
    patience = config.get("patience") or config.get("early_stopping_patience")
    if patience is not None:
        patience_int = int(patience)
        if patience_int != CANONICAL_EARLY_STOPPING_PATIENCE:
            raise AssertionError(
                f"EXP-01 patience mismatch: expected {CANONICAL_EARLY_STOPPING_PATIENCE}, got {patience_int}."
            )

    # 6. Eta min check
    eta_min = config.get("eta_min") or config.get("scheduler_eta_min")
    if eta_min is not None:
        eta_min_float = float(eta_min)
        if abs(eta_min_float - CANONICAL_SCHEDULER_ETA_MIN) > 1e-9:
            raise AssertionError(
                f"EXP-01 eta_min mismatch: expected {CANONICAL_SCHEDULER_ETA_MIN}, got {eta_min_float}."
            )

    # 7. Batch size check
    batch_size = config.get("batch_size") or config.get("physical_batch_size")
    if batch_size is not None:
        b_int = int(batch_size)
        if b_int != CANONICAL_PHYSICAL_BATCH_SIZE:
            raise AssertionError(
                f"EXP-01 physical batch_size mismatch: expected {CANONICAL_PHYSICAL_BATCH_SIZE}, got {b_int}."
            )

    # 8. Accumulation steps check
    accum = config.get("accum_steps") or config.get("accumulation_steps")
    if accum is not None:
        accum_int = int(accum)
        if accum_int != CANONICAL_ACCUMULATION_STEPS:
            raise AssertionError(
                f"EXP-01 accumulation_steps mismatch: expected {CANONICAL_ACCUMULATION_STEPS}, got {accum_int}."
            )

    # 9. Model architecture check
    arch = config.get("model") or config.get("architecture")
    if arch is not None:
        if arch != CANONICAL_MODEL_ARCHITECTURE:
            raise AssertionError(
                f"EXP-01 architecture mismatch: expected '{CANONICAL_MODEL_ARCHITECTURE}', got '{arch}'."
            )

    # 10. Seed check
    seed = config.get("seed")
    if seed is not None:
        if int(seed) != CANONICAL_SEED:
            raise AssertionError(
                f"EXP-01 seed mismatch: expected {CANONICAL_SEED}, got {int(seed)}."
            )


def build_canonical_fingerprint_dict(repo_root: Path | None = None) -> Dict[str, Any]:
    """Generate the complete authoritative EXP-01 configuration fingerprint."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]

    manifest_file = repo_root / CANONICAL_MANIFEST_REL_PATH
    manifest_sha = ""
    if manifest_file.exists():
        h = hashlib.sha256()
        with open(manifest_file, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        manifest_sha = h.hexdigest().upper()

    return {
        "experiment_name": EXP01_NAME,
        "experiment_revision": EXP01_REVISION,
        "fingerprint_version": "1.0-locked",
        "model": {
            "architecture": CANONICAL_MODEL_ARCHITECTURE,
            "source_file": "src/ocean_sentinel/ml/unet_resnet.py",
            "source_section": "class ResNet34UNet",
            "input_channels": CANONICAL_INPUT_CHANNELS,
            "output_channels": CANONICAL_OUTPUT_CHANNELS,
            "total_parameters": CANONICAL_TOTAL_PARAMETERS,
            "trainable_parameters": CANONICAL_TRAINABLE_PARAMETERS,
            "non_trainable_parameters": CANONICAL_NON_TRAINABLE_PARAMETERS,
            "adaptation_method": CANONICAL_ADAPTATION_METHOD,
            "pretrained_backbone": CANONICAL_PRETRAINED_BACKBONE,
        },
        "loss": {
            "class": CANONICAL_LOSS_CLASS,
            "source_file": "src/ocean_sentinel/ml/losses.py",
            "source_section": "class CombinedBCEAndDiceLoss",
            "bce_weight": CANONICAL_LOSS_BCE_WEIGHT,
            "dice_weight": CANONICAL_LOSS_DICE_WEIGHT,
            "dice_smooth": CANONICAL_LOSS_DICE_SMOOTH,
        },
        "optimizer": {
            "class": CANONICAL_OPTIMIZER_CLASS,
            "source_file": "scripts/train_exp01.py",
            "source_section": "Optimizer initialization",
            "lr": CANONICAL_OPTIMIZER_LR,
            "weight_decay": CANONICAL_OPTIMIZER_WEIGHT_DECAY,
            "betas": list(CANONICAL_OPTIMIZER_BETAS),
            "eps": CANONICAL_OPTIMIZER_EPS,
        },
        "scheduler": {
            "class": CANONICAL_SCHEDULER_CLASS,
            "source_file": "scripts/train_exp01.py",
            "source_section": "Scheduler initialization",
            "T_max": CANONICAL_SCHEDULER_T_MAX,
            "eta_min": CANONICAL_SCHEDULER_ETA_MIN,
        },
        "training": {
            "max_epochs": CANONICAL_MAX_EPOCHS,
            "early_stopping_patience": CANONICAL_EARLY_STOPPING_PATIENCE,
            "physical_batch_size": CANONICAL_PHYSICAL_BATCH_SIZE,
            "accumulation_steps": CANONICAL_ACCUMULATION_STEPS,
            "effective_batch_size": CANONICAL_EFFECTIVE_BATCH_SIZE,
            "seed": CANONICAL_SEED,
            "dataloader_num_workers": CANONICAL_NUM_WORKERS,
            "amp_enabled": CANONICAL_AMP_ENABLED,
            "amp_precision": CANONICAL_AMP_PRECISION,
        },
        "data": {
            "dataset_identity": CANONICAL_DATASET_NAME,
            "manifest_path": CANONICAL_MANIFEST_REL_PATH,
            "manifest_sha256": manifest_sha or CANONICAL_MANIFEST_SHA256,
            "total_patches": CANONICAL_TOTAL_PATCHES,
            "total_tiles": CANONICAL_TOTAL_TILES,
            "train_patches": CANONICAL_TRAIN_PATCHES,
            "train_tiles": CANONICAL_TRAIN_TILES,
            "val_patches": CANONICAL_VAL_PATCHES,
            "val_tiles": CANONICAL_VAL_TILES,
            "test_patches": CANONICAL_TEST_PATCHES,
            "test_tiles": CANONICAL_TEST_TILES,
            "normalization_type": CANONICAL_NORMALIZATION_TYPE,
        },
        "evaluation": {
            "selection_metric": CANONICAL_SELECTION_METRIC,
            "best_epoch": CANONICAL_BEST_EPOCH,
            "best_val_iou": CANONICAL_BEST_VAL_IOU,
            "stopped_epoch": CANONICAL_STOPPED_EPOCH,
            "selected_threshold": CANONICAL_SELECTED_THRESHOLD,
            "test_iou": CANONICAL_TEST_IOU,
            "test_dice": CANONICAL_TEST_DICE,
            "test_precision": CANONICAL_TEST_PRECISION,
            "test_recall": CANONICAL_TEST_RECALL,
        },
        "certified_artifacts": CERTIFIED_BASELINE_HASHES,
    }
