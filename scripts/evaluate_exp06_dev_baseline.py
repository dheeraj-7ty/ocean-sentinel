"""Evaluate Frozen EXP-06 Checkpoint on the Newly Frozen DEV Population.

Protocol Reference: PHASE_7A_DATA_PROTOCOL_FOUNDATION_20260912 (Section 9, 11, 12).
Evaluates the canonical best model from EXP-06 strictly on the DEV split of
data/metadata/internal_development_split_manifest.json at frozen tau = 0.22.

Records:
- Model checkpoint SHA-256
- Manifest SHA-256
- Environment and CUDA hardware fingerprint
- Preprocessing and normalization parameters
- Exact streaming confusion matrix (TP, FP, FN, TN)
- Micro and macro IoU, Dice, Precision, Recall
- Clean Water FAR (tile denominator: 1,827)
- Significant FAR (>= 100 FP pixels, denominator: 1,827)
- Complete tile dropout count (denominator: 1,053)
- Execution duration and throughput
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import platform
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import rasterio
from rasterio.windows import Window
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss
from ocean_sentinel.ml.metrics import SegmentationMeter
from ocean_sentinel.ml.unet_resnet import ResNet34UNet

# Frozen Constants
FROZEN_THRESHOLD = 0.22
EXPECTED_CHECKPOINT_SHA256 = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
EXPECTED_MANIFEST_SHA256 = "F6F785D4218DDCB3BDA8DB7A626B6016DC43D0B5652A9E43195580F47DE1D427"
CHECKPOINT_PATH = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "internal_development_split_manifest.json"
OUTPUT_BASELINE_PATH = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "exp06_frozen_dev_baseline.json"

# Normalization constants (Mapping A contract)
NORM_MEAN = [-33.2323, -19.9405]
NORM_STD = [6.4912, 4.5308]


def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


class InternalDevTileDataset(Dataset):
    """Dataset serving exact 512x512 tiles from the frozen DEV population."""

    def __init__(self, manifest_path: Path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # Filter scenes for DEV split
        self.scenes = {s["parent_scene_id"]: s for s in manifest["scenes"] if s["split"] == "DEV"}
        # Filter tiles for DEV split
        self.tiles = [t for t in manifest["tiles"] if t["split"] == "DEV"]

        self.norm_mean = np.array(NORM_MEAN, dtype=np.float32).reshape(2, 1, 1)
        self.norm_std = np.array(NORM_STD, dtype=np.float32).reshape(2, 1, 1)

    def __len__(self) -> int:
        return len(self.tiles)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, Any]]:
        t_meta = self.tiles[idx]
        parent_id = t_meta["parent_scene_id"]
        s_meta = self.scenes[parent_id]

        row_off = t_meta["row_offset"]
        col_off = t_meta["col_offset"]
        h = t_meta["height"]
        w = t_meta["width"]
        win = Window(col_off=col_off, row_off=row_off, width=w, height=h)

        # Read image
        with rasterio.open(s_meta["image_path"]) as src_img:
            img = src_img.read(window=win).astype(np.float32)

        # Read mask
        with rasterio.open(s_meta["mask_path"]) as src_mask:
            mask = src_mask.read(1, window=win).astype(np.float32)

        # Normalize image (Mapping A)
        img = (img - self.norm_mean) / self.norm_std

        # Format tensors
        img_t = torch.from_numpy(img)
        mask_t = torch.from_numpy(mask).unsqueeze(0)  # (1, 512, 512)

        info = {
            "tile_id": t_meta["tile_id"],
            "parent_scene_id": parent_id,
            "has_oil_gt": (mask.sum() > 0),
        }

        return img_t, mask_t, info


def evaluate_exp06_dev_baseline():
    print("=" * 75)
    print("FROZEN EXP-06 BASELINE EVALUATION ON NEW DEV POPULATION")
    print("=" * 75)
    start_time = time.time()

    # 1. Preflight Verification
    print("[1/4] Preflight verification of inputs and cryptographic integrity...")
    assert CHECKPOINT_PATH.is_file(), f"Checkpoint missing: {CHECKPOINT_PATH}"
    assert MANIFEST_PATH.is_file(), f"Manifest missing: {MANIFEST_PATH}"

    ckpt_sha = compute_file_sha256(CHECKPOINT_PATH)
    assert ckpt_sha == EXPECTED_CHECKPOINT_SHA256, f"Checkpoint SHA mismatch: {ckpt_sha}"
    print(f"  Checkpoint SHA-256: {ckpt_sha} (VERIFIED)")

    manifest_sha = compute_file_sha256(MANIFEST_PATH)
    assert manifest_sha == EXPECTED_MANIFEST_SHA256, f"Manifest SHA mismatch: {manifest_sha}"
    print(f"  Manifest SHA-256:   {manifest_sha} (VERIFIED)")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Inference Device:   {device} ({torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'})")

    # 2. Model Initialization & Checkpoint Loading
    print("[2/4] Initializing ResNet34UNet architecture and loading weights...")
    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")
    ckpt = torch.load(CHECKPOINT_PATH, map_location=device)
    if "model_state_dict" in ckpt:
        model.load_state_dict(ckpt["model_state_dict"])
    else:
        model.load_state_dict(ckpt)
    model.to(device)
    model.eval()

    # 3. DataLoader Setup
    print("[3/4] Preparing DEV dataset and DataLoader...")
    dev_dataset = InternalDevTileDataset(MANIFEST_PATH)
    print(f"  DEV tiles total: {len(dev_dataset)} across {len(dev_dataset.scenes)} parent scenes.")
    dev_loader = DataLoader(
        dev_dataset,
        batch_size=16,
        shuffle=False,
        num_workers=0,
        pin_memory=(device.type == "cuda"),
    )

    criterion = CombinedBCEAndDiceLoss(
        bce_weight=0.5,
        dice_weight=0.5,
        smooth=1.0,
        pos_weight=2.0,  # EXP-06 positive class weighting
    ).to(device)

    # 4. Evaluation Loop
    print(f"[4/4] Executing evaluation loop at frozen tau = {FROZEN_THRESHOLD}...")
    meter = SegmentationMeter(threshold=FROZEN_THRESHOLD)
    total_loss = 0.0
    batch_count = 0

    # Categorical accumulators
    clean_water_tiles_total = 0
    clean_water_fa_tiles = 0
    significant_fa_tiles = 0
    clean_water_fp_pixels = 0

    positive_tiles_total = 0
    positive_tiles_detected = 0
    positive_tiles_dropped = 0
    positive_gt_pixels_total = 0
    positive_pred_pixels_total = 0

    per_scene_confusion = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})

    with torch.no_grad():
        for batch_idx, (imgs, masks, infos) in enumerate(dev_loader):
            imgs = imgs.to(device)
            masks = masks.to(device)

            with torch.amp.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                logits = model(imgs)
                loss = criterion(logits, masks)

            total_loss += loss.item()
            batch_count += 1
            meter.update(logits, masks)

            probs = torch.sigmoid(logits)
            preds_bin = probs >= FROZEN_THRESHOLD

            b_size = masks.shape[0]
            for b in range(b_size):
                p_id = infos["parent_scene_id"][b]
                m_sum = int(masks[b, 0].sum().item())
                p_sum = int(preds_bin[b, 0].sum().item())

                # Pixel confusion for this tile
                t_gt = masks[b, 0].bool()
                t_pred = preds_bin[b, 0].bool()
                tp = int((t_gt & t_pred).sum().item())
                fp = int((~t_gt & t_pred).sum().item())
                fn = int((t_gt & ~t_pred).sum().item())
                tn = int((~t_gt & ~t_pred).sum().item())

                per_scene_confusion[p_id]["tp"] += tp
                per_scene_confusion[p_id]["fp"] += fp
                per_scene_confusion[p_id]["fn"] += fn
                per_scene_confusion[p_id]["tn"] += tn

                if m_sum == 0:
                    clean_water_tiles_total += 1
                    clean_water_fp_pixels += fp
                    if fp > 0:
                        clean_water_fa_tiles += 1
                    if fp >= 100:
                        significant_fa_tiles += 1
                else:
                    positive_tiles_total += 1
                    positive_gt_pixels_total += m_sum
                    positive_pred_pixels_total += p_sum
                    if tp > 0:
                        positive_tiles_detected += 1
                    else:
                        positive_tiles_dropped += 1

            if (batch_idx + 1) % 40 == 0 or (batch_idx + 1) == len(dev_loader):
                elapsed = time.time() - start_time
                pct = (batch_idx + 1) / len(dev_loader) * 100.0
                print(f"  PROGRESS: {pct:5.1f}% ({batch_idx + 1}/{len(dev_loader)}) | Elapsed: {elapsed:5.1f}s")

    # Compute aggregate micro metrics
    meter_summary = meter.compute()
    val_loss = total_loss / max(1, batch_count)

    clean_water_far_pct = (clean_water_fa_tiles / max(1, clean_water_tiles_total)) * 100.0
    significant_far_pct = (significant_fa_tiles / max(1, clean_water_tiles_total)) * 100.0
    clean_water_specificity = 1.0 - (clean_water_fp_pixels / (clean_water_tiles_total * 512 * 512))

    # Compute scene-level macro metrics
    scene_ious = []
    scene_dices = []
    scene_recalls = []
    scene_precisions = []

    for p_id, counts in per_scene_confusion.items():
        tp = counts["tp"]
        fp = counts["fp"]
        fn = counts["fn"]
        denom_iou = tp + fp + fn
        if denom_iou > 0:
            scene_ious.append(tp / denom_iou)
            scene_dices.append((2 * tp) / (2 * tp + fp + fn))
            scene_recalls.append(tp / (tp + fn) if (tp + fn) > 0 else 0.0)
            scene_precisions.append(tp / (tp + fp) if (tp + fp) > 0 else 0.0)

    macro_iou = float(np.mean(scene_ious))
    macro_dice = float(np.mean(scene_dices))
    macro_recall = float(np.mean(scene_recalls))
    macro_precision = float(np.mean(scene_precisions))

    total_duration = time.time() - start_time

    # Construct Baseline Artifact
    baseline_result = {
        "evaluation_document": "PHASE_7A_DATA_PROTOCOL_FOUNDATION_20260912",
        "evaluation_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": {
            "checkpoint_path": str(CHECKPOINT_PATH),
            "checkpoint_sha256": ckpt_sha,
            "architecture": "ResNet34UNet",
            "adaptation": "slice_variance_scaled",
            "total_parameters": 24346305,
        },
        "dataset": {
            "manifest_path": str(MANIFEST_PATH),
            "manifest_sha256": manifest_sha,
            "population_evaluated": "DEV",
            "parent_scenes_count": len(dev_dataset.scenes),
            "total_tiles_evaluated": len(dev_dataset),
            "positive_tiles_count": positive_tiles_total,
            "clean_water_tiles_count": clean_water_tiles_total,
        },
        "protocol": {
            "decision_threshold_tau": FROZEN_THRESHOLD,
            "channel_contract": "Mapping A (Band 1 VH -> Ch0, Band 2 VV -> Ch1)",
            "normalization_mean": NORM_MEAN,
            "normalization_std": NORM_STD,
            "evaluation_device": str(device),
            "cuda_device_name": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        },
        "primary_micro_metrics": {
            "val_loss": round(val_loss, 5),
            "val_iou": round(meter_summary["iou"], 5),
            "val_dice": round(meter_summary["dice"], 5),
            "val_recall": round(meter_summary["recall"], 5),
            "val_precision": round(meter_summary["precision"], 5),
        },
        "primary_macro_metrics": {
            "macro_mean_iou": round(macro_iou, 5),
            "macro_mean_dice": round(macro_dice, 5),
            "macro_mean_recall": round(macro_recall, 5),
            "macro_mean_precision": round(macro_precision, 5),
            "scenes_evaluated_count": len(scene_ious),
        },
        "negative_rejection_metrics": {
            "clean_water_tiles_evaluated": clean_water_tiles_total,
            "clean_water_fa_tiles": clean_water_fa_tiles,
            "clean_water_far_pct": round(clean_water_far_pct, 4),
            "significant_fa_tiles": significant_fa_tiles,
            "significant_far_pct": round(significant_far_pct, 4),
            "clean_water_fp_pixels": clean_water_fp_pixels,
            "clean_water_pixel_specificity": round(clean_water_specificity, 6),
        },
        "positive_dropout_metrics": {
            "positive_tiles_evaluated": positive_tiles_total,
            "positive_tiles_detected": positive_tiles_detected,
            "positive_tiles_dropped": positive_tiles_dropped,
            "tile_dropout_rate_pct": round((positive_tiles_dropped / max(1, positive_tiles_total)) * 100.0, 2),
            "positive_gt_pixels_total": positive_gt_pixels_total,
            "positive_pred_pixels_total": positive_pred_pixels_total,
        },
        "timing_and_throughput": {
            "total_duration_seconds": round(total_duration, 2),
            "throughput_tiles_per_sec": round(len(dev_dataset) / max(0.1, total_duration), 2),
        },
    }

    with open(OUTPUT_BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(baseline_result, f, indent=2)

    print("\n" + "=" * 75)
    print("FROZEN EXP-06 DEV BASELINE RESULTS SUMMARY")
    print("=" * 75)
    print(f"Micro Mean IoU:          {baseline_result['primary_micro_metrics']['val_iou']:.5f}")
    print(f"Micro Dice:              {baseline_result['primary_micro_metrics']['val_dice']:.5f}")
    print(f"Micro Recall:            {baseline_result['primary_micro_metrics']['val_recall']:.5f}")
    print(f"Micro Precision:         {baseline_result['primary_micro_metrics']['val_precision']:.5f}")
    print(f"Macro Mean IoU:          {baseline_result['primary_macro_metrics']['macro_mean_iou']:.5f}")
    print(f"Macro Recall:            {baseline_result['primary_macro_metrics']['macro_mean_recall']:.5f}")
    print(f"Clean Water FAR:         {baseline_result['negative_rejection_metrics']['clean_water_far_pct']:.2f}% ({clean_water_fa_tiles}/{clean_water_tiles_total} tiles)")
    print(f"Significant FAR:         {baseline_result['negative_rejection_metrics']['significant_far_pct']:.2f}% ({significant_fa_tiles}/{clean_water_tiles_total} tiles)")
    print(f"Clean Water FP Pixels:   {clean_water_fp_pixels:,} px (Specificity: {clean_water_specificity * 100:.4f}%)")
    print(f"Complete Tile Dropouts:  {positive_tiles_dropped} tiles ({positive_tiles_dropped / positive_tiles_total * 100:.2f}%)")
    print(f"Saved baseline to:       {OUTPUT_BASELINE_PATH}")
    print("=" * 75)


if __name__ == "__main__":
    evaluate_exp06_dev_baseline()
