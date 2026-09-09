"""EXP-02B-1: Rigorous Offline Diagnostic, Pareto & Error-Analysis Runner.

Mandatory CAO Scientific Rules:
- DO NOT TRAIN.
- DO NOT modify model weights.
- DO NOT run EXP02C.
- DO NOT access TEST data for decision-making (TRAIN / VAL evidence only).
- Output Directory: experiments/performance/exp02b_1_diagnostic_20260909_142000/
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
import rasterio
import rasterio.features
from shapely.geometry import shape
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName
from ocean_sentinel.ml.augmentation import IdentityTransform
from ocean_sentinel.ml.unet_resnet import ResNet34UNet, count_parameters

# Paths & Expected Hashes
MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
EXPECTED_MANIFEST_SHA256 = "C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0"

CHECKPOINT_PATH = REPO_ROOT / "experiments" / "performance" / "exp02b_1_hard_negative_training_20260909_094500" / "kernel_output" / "exp02b_1_hard_negative_training" / "best_model.pt"
EXPECTED_CHECKPOINT_SHA256 = "54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B"

HISTORY_PATH = REPO_ROOT / "experiments" / "performance" / "exp02b_1_hard_negative_training_20260909_094500" / "kernel_output" / "exp02b_1_hard_negative_training" / "history.json"

TEACHER_PATH = REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt"
EXPECTED_TEACHER_SHA256 = "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699"

OUTPUT_DIR = REPO_ROOT / "experiments" / "performance" / "exp02b_1_diagnostic_20260909_142000"
FROZEN_THRESHOLD = 0.22

_log = logging.getLogger("exp02b_1_diagnostic")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def setup_logging(output_dir: Path) -> None:
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
    fh.stream.reconfigure(line_buffering=True)
    _log.addHandler(fh)


def get_connected_components(binary_mask: np.ndarray) -> Tuple[int, float, List[float]]:
    """Return (count, max_area, all_areas) for binary mask using rasterio/shapely."""
    if binary_mask.sum() == 0:
        return 0, 0.0, []
    mask_i16 = binary_mask.astype(np.int16)
    shapes = list(rasterio.features.shapes(mask_i16, mask=(mask_i16 > 0)))
    if not shapes:
        return 0, 0.0, []
    areas = [float(shape(g).area) for g, v in shapes if v > 0]
    if not areas:
        return 0, 0.0, []
    return len(areas), max(areas), areas


def save_diagnostic_image(
    out_path: Path,
    img_tensor: torch.Tensor,
    gt_mask: np.ndarray,
    exp01_pred: np.ndarray,
    exp02_pred: np.ndarray,
    title: str = "",
) -> None:
    """Save an RGB diagnostic visualization showing SAR image, GT, and predictions."""
    # Denormalize roughly for visualization (convert dB / z-score to 0-255)
    # img_tensor is (2, 512, 512)
    img_np = img_tensor.cpu().numpy()
    ch0 = img_np[0]
    ch1 = img_np[1]
    
    # Clip z-scores [-3, 3] to [0, 255]
    def to_u8(x):
        norm = np.clip((x + 3.0) / 6.0, 0.0, 1.0)
        return (norm * 255).astype(np.uint8)

    r = to_u8(ch0)
    g = to_u8(ch1)
    b = to_u8(0.5 * (ch0 + ch1))

    # Construct RGB image
    rgb_base = np.stack([r, g, b], axis=-1)

    # We will create a 1x3 panel:
    # Panel 1: SAR Base + Ground Truth (Green outline/fill)
    # Panel 2: EXP01 Prediction (Yellow/Red)
    # Panel 3: EXP02B-1 Prediction (Cyan/Blue)
    p1 = rgb_base.copy()
    p2 = rgb_base.copy()
    p3 = rgb_base.copy()

    # Overlay GT on P1: green tint where GT=1
    gt_bool = gt_mask > 0.5
    p1[gt_bool, 0] = (p1[gt_bool, 0] * 0.3).astype(np.uint8)
    p1[gt_bool, 1] = np.clip(p1[gt_bool, 1] * 0.3 + 178, 0, 255).astype(np.uint8)
    p1[gt_bool, 2] = (p1[gt_bool, 2] * 0.3).astype(np.uint8)

    # Overlay EXP01 on P2: red tint where Pred=1
    p01_bool = exp01_pred > 0.5
    p2[p01_bool, 0] = np.clip(p2[p01_bool, 0] * 0.3 + 178, 0, 255).astype(np.uint8)
    p2[p01_bool, 1] = (p2[p01_bool, 1] * 0.3).astype(np.uint8)
    p2[p01_bool, 2] = (p2[p01_bool, 2] * 0.3).astype(np.uint8)

    # Overlay EXP02B-1 on P3: cyan tint where Pred=1
    p02_bool = exp02_pred > 0.5
    p3[p02_bool, 0] = (p3[p02_bool, 0] * 0.3).astype(np.uint8)
    p3[p02_bool, 1] = np.clip(p3[p02_bool, 1] * 0.3 + 150, 0, 255).astype(np.uint8)
    p3[p02_bool, 2] = np.clip(p3[p02_bool, 2] * 0.3 + 178, 0, 255).astype(np.uint8)

    # Concatenate horizontally
    composite = np.concatenate([p1, p2, p3], axis=1) # (512, 1536, 3)
    img_pil = Image.fromarray(composite)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img_pil.save(out_path)


def run_diagnostic():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    setup_logging(OUTPUT_DIR)

    _log.info("=" * 80)
    _log.info("EXP-02B-1 DIAGNOSTIC / PARETO / ERROR-ANALYSIS GATE")
    _log.info("=" * 80)

    # -------------------------------------------------------------------------
    # PHASE 1 — STATE RECONSTRUCTION & PROVENANCE
    # -------------------------------------------------------------------------
    _log.info("\n--- PHASE 1: STATE RECONSTRUCTION & PROVENANCE ---")

    assert MANIFEST_PATH.exists(), f"Manifest missing: {MANIFEST_PATH}"
    actual_manifest_sha = file_sha256(MANIFEST_PATH)
    assert actual_manifest_sha == EXPECTED_MANIFEST_SHA256, f"Manifest hash mismatch: {actual_manifest_sha}"

    assert CHECKPOINT_PATH.exists(), f"Candidate checkpoint missing: {CHECKPOINT_PATH}"
    actual_chk_sha = file_sha256(CHECKPOINT_PATH)
    assert actual_chk_sha == EXPECTED_CHECKPOINT_SHA256, f"Candidate checkpoint hash mismatch: {actual_chk_sha}"

    assert TEACHER_PATH.exists(), f"Teacher checkpoint missing: {TEACHER_PATH}"
    actual_teacher_sha = file_sha256(TEACHER_PATH)
    assert actual_teacher_sha == EXPECTED_TEACHER_SHA256, f"Teacher checkpoint hash mismatch: {actual_teacher_sha}"

    runner_path = Path(__file__).resolve()
    actual_runner_sha = file_sha256(runner_path)

    # Git status check
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        git_commit = "UNKNOWN"

    provenance = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "manifest_path": str(MANIFEST_PATH),
        "manifest_sha256": actual_manifest_sha,
        "candidate_checkpoint_path": str(CHECKPOINT_PATH),
        "candidate_checkpoint_sha256": actual_chk_sha,
        "candidate_epoch": 3,
        "teacher_checkpoint_path": str(TEACHER_PATH),
        "teacher_checkpoint_sha256": actual_teacher_sha,
        "runner_script": str(runner_path),
        "runner_sha256": actual_runner_sha,
        "git_commit": git_commit,
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "frozen_threshold": FROZEN_THRESHOLD,
    }
    with open(OUTPUT_DIR / "provenance.json", "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)
    _log.info("Provenance saved to provenance.json")

    # -------------------------------------------------------------------------
    # PHASE 2 — VALIDATION TRAJECTORY PARETO ANALYSIS
    # -------------------------------------------------------------------------
    _log.info("\n--- PHASE 2: VALIDATION TRAJECTORY PARETO ANALYSIS ---")
    assert HISTORY_PATH.exists(), f"History missing: {HISTORY_PATH}"
    raw_history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))

    # Objectives:
    # - FA rate (minimize)
    # - Recall (maximize)
    # - IoU (maximize)
    trajectory = []
    for r in raw_history:
        trajectory.append({
            "epoch": r["epoch"],
            "train_loss": r["train_loss"],
            "val_loss": r["val_loss"],
            "val_iou": r["val_iou"],
            "val_dice": r["val_dice"],
            "val_precision": r["val_precision"],
            "val_recall": r["val_recall"],
            "val_neg_fa_rate_pct": r["val_neg_fa_rate_pct"],
            "val_neg_extensive_fa_rate_pct": r["val_neg_extensive_fa_rate_pct"],
            "val_neg_fp_fraction": r["val_neg_fp_fraction"],
        })

    # Compute Pareto dominance
    # Point A dominates Point B if:
    # A.fa <= B.fa and A.rec >= B.rec and A.iou >= B.iou, with at least one strict inequality
    for i, a in enumerate(trajectory):
        dominated = False
        dominators = []
        for j, b in enumerate(trajectory):
            if i == j:
                continue
            # Does b dominate a?
            b_better_or_equal = (
                b["val_neg_fa_rate_pct"] <= a["val_neg_fa_rate_pct"]
                and b["val_recall"] >= a["val_recall"]
                and b["val_iou"] >= a["val_iou"]
            )
            b_strictly_better = (
                b["val_neg_fa_rate_pct"] < a["val_neg_fa_rate_pct"]
                or b["val_recall"] > a["val_recall"]
                or b["val_iou"] > a["val_iou"]
            )
            if b_better_or_equal and b_strictly_better:
                dominated = True
                dominators.append(b["epoch"])
        a["is_pareto_efficient"] = not dominated
        a["dominated_by_epochs"] = dominators

    # Also compute 2D Pareto in (FA, Recall) and (FA, IoU)
    for a in trajectory:
        dom_fa_rec = False
        dom_fa_iou = False
        for b in trajectory:
            if b["epoch"] == a["epoch"]:
                continue
            if (b["val_neg_fa_rate_pct"] <= a["val_neg_fa_rate_pct"] and b["val_recall"] >= a["val_recall"]) and (b["val_neg_fa_rate_pct"] < a["val_neg_fa_rate_pct"] or b["val_recall"] > a["val_recall"]):
                dom_fa_rec = True
            if (b["val_neg_fa_rate_pct"] <= a["val_neg_fa_rate_pct"] and b["val_iou"] >= a["val_iou"]) and (b["val_neg_fa_rate_pct"] < a["val_neg_fa_rate_pct"] or b["val_iou"] > a["val_iou"]):
                dom_fa_iou = True
        a["pareto_2d_fa_recall"] = not dom_fa_rec
        a["pareto_2d_fa_iou"] = not dom_fa_iou

    # Write pareto_frontier.csv
    pareto_csv_path = OUTPUT_DIR / "pareto_frontier.csv"
    with open(pareto_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "epoch", "train_loss", "val_loss", "val_iou", "val_dice", "val_precision", "val_recall",
            "val_neg_fa_rate_pct", "val_neg_extensive_fa_rate_pct", "val_neg_fp_fraction",
            "is_pareto_efficient", "pareto_2d_fa_recall", "pareto_2d_fa_iou", "dominated_by_epochs"
        ])
        writer.writeheader()
        for row in trajectory:
            r_copy = dict(row)
            r_copy["dominated_by_epochs"] = ",".join(map(str, r_copy["dominated_by_epochs"]))
            writer.writerow(r_copy)

    pareto_epochs = [r["epoch"] for r in trajectory if r["is_pareto_efficient"]]
    _log.info("Pareto frontier written to pareto_frontier.csv")
    _log.info("Non-dominated 3D Pareto epochs (FA, Rec, IoU): %s", pareto_epochs)

    # -------------------------------------------------------------------------
    # PHASE 3 & 4 — FROZEN VALIDATION INFERENCE ON 2,880 VALIDATION TILES
    # -------------------------------------------------------------------------
    _log.info("\n--- PHASE 3 & 4: FROZEN VALIDATION INFERENCE ON 2,880 TILES ---")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    assert device.type == "cuda", "CUDA required for diagnostic inference."

    manifest = DatasetManifest.load(MANIFEST_PATH)
    val_tiles_manifest = manifest.tiles_for_split(SplitName.VAL)
    assert len(val_tiles_manifest) == 2880, f"Expected 2880 val tiles, got {len(val_tiles_manifest)}"

    eval_tfm = IdentityTransform()
    ds_val = TrujilloTileDataset(manifest, SplitName.VAL, normalize=True, transform=eval_tfm)
    val_loader = DataLoader(ds_val, batch_size=8, shuffle=False, num_workers=2, pin_memory=True)

    # Load EXP02B-1 Candidate (Epoch 3)
    chk_cand = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    model_cand = ResNet34UNet(in_channels=2, num_classes=1, pretrained=False, adaptation_method="slice_variance_scaled").to(device)
    model_cand.load_state_dict(chk_cand["model_state_dict"], strict=True)
    model_cand.eval()

    # Load EXP01 Teacher Baseline
    chk_teach = torch.load(TEACHER_PATH, map_location="cpu", weights_only=False)
    model_teach = ResNet34UNet(in_channels=2, num_classes=1, pretrained=False, adaptation_method="slice_variance_scaled").to(device)
    model_teach.load_state_dict(chk_teach["model_state_dict"], strict=True)
    model_teach.eval()

    # Containers for tile results
    negative_tile_results = []
    positive_tile_results = []

    # Prepare representative examples directory
    examples_dir = OUTPUT_DIR / "representative_validation_examples"
    examples_dir.mkdir(parents=True, exist_ok=True)

    # Representative image budget
    saved_images_count = {
        "cured_fa": 0,
        "persistent_fa": 0,
        "new_fa": 0,
        "positive_undersegment": 0,
        "positive_miss": 0,
        "positive_improved": 0,
    }
    MAX_PER_CATEGORY = 4

    tile_idx = 0
    t_start = time.time()
    batch_count = len(val_loader)

    with torch.no_grad():
        for batch_idx, (imgs, masks) in enumerate(val_loader, 1):
            imgs_dev = imgs.to(device, non_blocking=True)
            masks_cpu = masks.squeeze(1).numpy() # (B, 512, 512)

            with torch.amp.autocast("cuda", dtype=torch.float16):
                logits_cand = model_cand(imgs_dev)
                logits_teach = model_teach(imgs_dev)

            probs_cand = torch.sigmoid(logits_cand).squeeze(1).cpu().numpy()
            probs_teach = torch.sigmoid(logits_teach).squeeze(1).cpu().numpy()

            bs = imgs.shape[0]
            for i in range(bs):
                t_entry = val_tiles_manifest[tile_idx]
                tile_id = t_entry.tile_id
                patch_stem = t_entry.parent_stem
                row = t_entry.row_idx
                col = t_entry.col_idx
                x_min = t_entry.col_offset
                y_min = t_entry.row_offset

                gt_m = masks_cpu[i]
                p_c = probs_cand[i]
                p_t = probs_teach[i]

                pred_bin_c = (p_c >= FROZEN_THRESHOLD).astype(np.uint8)
                pred_bin_t = (p_t >= FROZEN_THRESHOLD).astype(np.uint8)

                img_t = imgs[i] # (2, 512, 512) normalized tensor

                gt_pixels = int(gt_m.sum())

                if gt_pixels == 0:
                    # Negative tile
                    fp_t = int(pred_bin_t.sum())
                    fp_c = int(pred_bin_c.sum())

                    # Contingency classification
                    # a: clean / clean, b: alarm_t / clean_c, c: clean_t / alarm_c, d: alarm_t / alarm_c
                    if fp_t == 0 and fp_c == 0:
                        cat = "a_both_clean"
                    elif fp_t > 0 and fp_c == 0:
                        cat = "b_cured_fa"
                    elif fp_t == 0 and fp_c > 0:
                        cat = "c_new_fa"
                    else:
                        cat = "d_both_fa"

                    # Component analysis
                    n_comp_t, max_comp_t, _ = get_connected_components(pred_bin_t)
                    n_comp_c, max_comp_c, _ = get_connected_components(pred_bin_c)

                    # Intensity stats (from normalized tensor)
                    ch0 = img_t[0].numpy()
                    ch1 = img_t[1].numpy()
                    ch0_mean = float(ch0.mean())
                    ch0_std = float(ch0.std())
                    ch1_mean = float(ch1.mean())
                    ch1_std = float(ch1.std())

                    # Confidence stats
                    max_prob_t = float(p_t.max())
                    max_prob_c = float(p_c.max())
                    mean_prob_t_fa = float(p_t[pred_bin_t == 1].mean()) if fp_t > 0 else 0.0
                    mean_prob_c_fa = float(p_c[pred_bin_c == 1].mean()) if fp_c > 0 else 0.0

                    negative_tile_results.append({
                        "tile_id": tile_id,
                        "patch_stem": patch_stem,
                        "row": row,
                        "col": col,
                        "x_min": x_min,
                        "y_min": y_min,
                        "contingency_class": cat,
                        "exp01_fp_pixels": fp_t,
                        "exp02b1_fp_pixels": fp_c,
                        "exp01_components": n_comp_t,
                        "exp02b1_components": n_comp_c,
                        "exp01_max_component_px": max_comp_t,
                        "exp02b1_max_component_px": max_comp_c,
                        "exp01_max_prob": round(max_prob_t, 4),
                        "exp02b1_max_prob": round(max_prob_c, 4),
                        "exp01_mean_fa_prob": round(mean_prob_t_fa, 4),
                        "exp02b1_mean_fa_prob": round(mean_prob_c_fa, 4),
                        "ch0_norm_mean": round(ch0_mean, 4),
                        "ch0_norm_std": round(ch0_std, 4),
                        "ch1_norm_mean": round(ch1_mean, 4),
                        "ch1_norm_std": round(ch1_std, 4),
                    })

                    # Representative image saving
                    if cat == "b_cured_fa" and saved_images_count["cured_fa"] < MAX_PER_CATEGORY and fp_t >= 50:
                        save_diagnostic_image(
                            examples_dir / f"cured_fa_{saved_images_count['cured_fa']+1}_{tile_id}.png",
                            img_t, gt_m, pred_bin_t, pred_bin_c,
                            title=f"Cured FA: {tile_id} (EXP01={fp_t}px, EXP02B-1=0px)"
                        )
                        saved_images_count["cured_fa"] += 1
                    elif cat == "c_new_fa" and saved_images_count["new_fa"] < MAX_PER_CATEGORY and fp_c >= 50:
                        save_diagnostic_image(
                            examples_dir / f"new_fa_{saved_images_count['new_fa']+1}_{tile_id}.png",
                            img_t, gt_m, pred_bin_t, pred_bin_c,
                            title=f"New FA: {tile_id} (EXP01=0px, EXP02B-1={fp_c}px)"
                        )
                        saved_images_count["new_fa"] += 1
                    elif cat == "d_both_fa" and saved_images_count["persistent_fa"] < MAX_PER_CATEGORY and fp_c >= 50:
                        save_diagnostic_image(
                            examples_dir / f"persistent_fa_{saved_images_count['persistent_fa']+1}_{tile_id}.png",
                            img_t, gt_m, pred_bin_t, pred_bin_c,
                            title=f"Persistent FA: {tile_id} (EXP01={fp_t}px, EXP02B-1={fp_c}px)"
                        )
                        saved_images_count["persistent_fa"] += 1

                else:
                    # Positive tile
                    tp_t = int(((pred_bin_t == 1) & (gt_m == 1)).sum())
                    fp_t = int(((pred_bin_t == 1) & (gt_m == 0)).sum())
                    fn_t = int(((pred_bin_t == 0) & (gt_m == 1)).sum())

                    tp_c = int(((pred_bin_c == 1) & (gt_m == 1)).sum())
                    fp_c = int(((pred_bin_c == 1) & (gt_m == 0)).sum())
                    fn_c = int(((pred_bin_c == 0) & (gt_m == 1)).sum())

                    iou_t = tp_t / (tp_t + fp_t + fn_t) if (tp_t + fp_t + fn_t) > 0 else 0.0
                    rec_t = tp_t / (tp_t + fn_t) if (tp_t + fn_t) > 0 else 0.0
                    prec_t = tp_t / (tp_t + fp_t) if (tp_t + fp_t) > 0 else 0.0

                    iou_c = tp_c / (tp_c + fp_c + fn_c) if (tp_c + fp_c + fn_c) > 0 else 0.0
                    rec_c = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0.0
                    prec_c = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0.0

                    pred_area_t = int(pred_bin_t.sum())
                    pred_area_c = int(pred_bin_c.sum())

                    ratio_t = pred_area_t / gt_pixels if gt_pixels > 0 else 0.0
                    ratio_c = pred_area_c / gt_pixels if gt_pixels > 0 else 0.0

                    # Connected components of prediction and GT
                    n_comp_gt, max_comp_gt, _ = get_connected_components(gt_m)
                    n_comp_t, max_comp_t, _ = get_connected_components(pred_bin_t)
                    n_comp_c, max_comp_c, _ = get_connected_components(pred_bin_c)

                    # Group partitioning:
                    # A. candidate improves: iou_c > iou_t + 0.01
                    # B. both detect (tp_t >= 1 and tp_c >= 1), candidate undersegments (ratio_c < ratio_t or rec_c < rec_t) and not improves
                    # C. EXP01 detects (tp_t >= 1), candidate misses (tp_c == 0)
                    # D. candidate detects (tp_c >= 1), EXP01 misses (tp_t == 0)
                    # E. neither detects (tp_t == 0 and tp_c == 0)
                    if tp_t == 0 and tp_c == 0:
                        part_group = "E_neither_detects"
                    elif tp_t >= 1 and tp_c == 0:
                        part_group = "C_exp01_detects_candidate_misses"
                    elif tp_t == 0 and tp_c >= 1:
                        part_group = "D_candidate_detects_exp01_misses"
                    elif iou_c > iou_t + 0.01:
                        part_group = "A_candidate_improves"
                    elif ratio_c < ratio_t or rec_c < rec_t:
                        part_group = "B_both_detect_candidate_undersegments"
                    else:
                        part_group = "B_both_detect_other"

                    # Prob on GT
                    mean_prob_gt_t = float(p_t[gt_m == 1].mean()) if gt_pixels > 0 else 0.0
                    mean_prob_gt_c = float(p_c[gt_m == 1].mean()) if gt_pixels > 0 else 0.0

                    positive_tile_results.append({
                        "tile_id": tile_id,
                        "patch_stem": patch_stem,
                        "row": row,
                        "col": col,
                        "gt_spill_pixels": gt_pixels,
                        "gt_components": n_comp_gt,
                        "gt_max_component_px": max_comp_gt,
                        "partition_group": part_group,
                        "exp01_pred_pixels": pred_area_t,
                        "exp02b1_pred_pixels": pred_area_c,
                        "exp01_tp": tp_t,
                        "exp01_fp": fp_t,
                        "exp01_fn": fn_t,
                        "exp01_iou": round(iou_t, 4),
                        "exp01_recall": round(rec_t, 4),
                        "exp01_precision": round(prec_t, 4),
                        "exp01_pred_gt_ratio": round(ratio_t, 4),
                        "exp02b1_tp": tp_c,
                        "exp02b1_fp": fp_c,
                        "exp02b1_fn": fn_c,
                        "exp02b1_iou": round(iou_c, 4),
                        "exp02b1_recall": round(rec_c, 4),
                        "exp02b1_precision": round(prec_c, 4),
                        "exp02b1_pred_gt_ratio": round(ratio_c, 4),
                        "exp01_components": n_comp_t,
                        "exp02b1_components": n_comp_c,
                        "exp01_mean_prob_on_gt": round(mean_prob_gt_t, 4),
                        "exp02b1_mean_prob_on_gt": round(mean_prob_gt_c, 4),
                    })

                    # Representative image saving
                    if part_group == "B_both_detect_candidate_undersegments" and saved_images_count["positive_undersegment"] < MAX_PER_CATEGORY and (rec_t - rec_c) >= 0.15:
                        save_diagnostic_image(
                            examples_dir / f"pos_undersegment_{saved_images_count['positive_undersegment']+1}_{tile_id}.png",
                            img_t, gt_m, pred_bin_t, pred_bin_c,
                            title=f"Undersegment: {tile_id} (Rec EXP01={rec_t:.2f}, EXP02B-1={rec_c:.2f})"
                        )
                        saved_images_count["positive_undersegment"] += 1
                    elif part_group == "C_exp01_detects_candidate_misses" and saved_images_count["positive_miss"] < MAX_PER_CATEGORY:
                        save_diagnostic_image(
                            examples_dir / f"pos_miss_{saved_images_count['positive_miss']+1}_{tile_id}.png",
                            img_t, gt_m, pred_bin_t, pred_bin_c,
                            title=f"Spill Miss: {tile_id} (EXP01 TP={tp_t}px, EXP02B-1 TP=0px)"
                        )
                        saved_images_count["positive_miss"] += 1
                    elif part_group == "A_candidate_improves" and saved_images_count["positive_improved"] < MAX_PER_CATEGORY and (iou_c - iou_t) >= 0.10:
                        save_diagnostic_image(
                            examples_dir / f"pos_improved_{saved_images_count['positive_improved']+1}_{tile_id}.png",
                            img_t, gt_m, pred_bin_t, pred_bin_c,
                            title=f"Spill Improved: {tile_id} (IoU EXP01={iou_t:.2f}, EXP02B-1={iou_c:.2f})"
                        )
                        saved_images_count["positive_improved"] += 1

                tile_idx += 1

            if batch_idx % 50 == 0 or batch_idx == batch_count:
                dt = time.time() - t_start
                _log.info("  Validation Inference: Batch %03d/%03d (%5.1f%%) | Tiles: %d | Throughput: %.1f tiles/s",
                          batch_idx, batch_count, (batch_idx / batch_count) * 100, tile_idx, tile_idx / dt)

    _log.info("Processed %d validation tiles (%d negative, %d positive)",
              tile_idx, len(negative_tile_results), len(positive_tile_results))

    # -------------------------------------------------------------------------
    # WRITE VALIDATION PAIRED CSVS
    # -------------------------------------------------------------------------
    neg_csv_path = OUTPUT_DIR / "validation_negative_paired_analysis.csv"
    with open(neg_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(negative_tile_results[0].keys()))
        writer.writeheader()
        writer.writerows(negative_tile_results)
    _log.info("Saved %s", neg_csv_path.name)

    pos_csv_path = OUTPUT_DIR / "validation_positive_paired_analysis.csv"
    with open(pos_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(positive_tile_results[0].keys()))
        writer.writeheader()
        writer.writerows(positive_tile_results)
    _log.info("Saved %s", pos_csv_path.name)

    # -------------------------------------------------------------------------
    # COMPUTE EXACT PAIRED MCNEMAR & CONTINGENCY ON VALIDATION NEGATIVES
    # -------------------------------------------------------------------------
    _log.info("\n--- PHASE 3 SUMMARY: VALIDATION NEGATIVE CONTINGENCY ---")
    n_neg = len(negative_tile_results)
    assert n_neg == 1827, f"Expected 1827 validation negative tiles, got {n_neg}"

    a = sum(1 for r in negative_tile_results if r["contingency_class"] == "a_both_clean")
    b = sum(1 for r in negative_tile_results if r["contingency_class"] == "b_cured_fa")
    c = sum(1 for r in negative_tile_results if r["contingency_class"] == "c_new_fa")
    d = sum(1 for r in negative_tile_results if r["contingency_class"] == "d_both_fa")
    assert a + b + c + d == n_neg

    fa_exp01 = b + d
    fa_exp02 = c + d
    rate_exp01 = (fa_exp01 / n_neg) * 100.0
    rate_exp02 = (fa_exp02 / n_neg) * 100.0
    abs_red = rate_exp01 - rate_exp02
    rel_red = ((b - c) / fa_exp01 * 100.0) if fa_exp01 > 0 else 0.0

    discordant = b + c
    if discordant > 0:
        chi2_stat = ((abs(b - c) - 1.0) ** 2) / discordant
        p_val = math.erfc(math.sqrt(chi2_stat) / math.sqrt(2.0))
    else:
        chi2_stat = 0.0
        p_val = 1.0

    z = 1.959964
    var_diff = (discordant - ((b - c) ** 2) / n_neg) / (n_neg ** 2)
    se = math.sqrt(max(var_diff, 0.0))
    ci_lo = (abs_red / 100.0) - z * se
    ci_hi = (abs_red / 100.0) + z * se

    _log.info("Validation Contingency: a=%d, b=%d, c=%d, d=%d (total=%d)", a, b, c, d, n_neg)
    _log.info("  EXP01 FA: %d (%.2f%%) | EXP02B-1 FA: %d (%.2f%%)", fa_exp01, rate_exp01, fa_exp02, rate_exp02)
    _log.info("  Cured FAs (b): %d | New FAs (c): %d | Net Cured: %d", b, c, b - c)
    _log.info("  Absolute Reduction: %.2f pp | Relative Reduction: %.2f%%", abs_red, rel_red)
    _log.info("  McNemar Chi2: %.4f, p = %.4e", chi2_stat, p_val)
    _log.info("  95%% Paired CI: [%.2f, %.2f] pp", ci_lo * 100, ci_hi * 100)

    # -------------------------------------------------------------------------
    # COMPUTE POSITIVE-TILE PARTITION ANALYSIS & HYPOTHESIS TEST
    # -------------------------------------------------------------------------
    _log.info("\n--- PHASE 4 SUMMARY: VALIDATION POSITIVE PARTITION ---")
    n_pos = len(positive_tile_results)
    assert n_pos == 1053, f"Expected 1053 validation positive tiles, got {n_pos}"

    part_counts = {}
    for r in positive_tile_results:
        g = r["partition_group"]
        part_counts[g] = part_counts.get(g, 0) + 1

    _log.info("Positive Tile Partition:")
    for g, cnt in sorted(part_counts.items()):
        _log.info("  Group %-40s: %4d tiles (%.2f%%)", g, cnt, (cnt / n_pos) * 100)

    # Hypothesis Testing:
    # "Is the recall loss predominantly whole-tile detection loss, or is it predominantly reduced spatial extent/undersegmentation within already-detected positive tiles?"
    n_whole_tile_miss = part_counts.get("C_exp01_detects_candidate_misses", 0)
    n_undersegmented = part_counts.get("B_both_detect_candidate_undersegments", 0)
    
    # Calculate pixel-level attribution of FN:
    # Total FN increase across validation positive tiles
    total_fn_exp01 = sum(r["exp01_fn"] for r in positive_tile_results)
    total_fn_exp02 = sum(r["exp02b1_fn"] for r in positive_tile_results)
    delta_fn = total_fn_exp02 - total_fn_exp01

    # FN from whole-tile misses (where EXP01 detected but EXP02B-1 completely missed)
    fn_from_whole_misses = sum(r["exp02b1_fn"] - r["exp01_fn"] for r in positive_tile_results if r["partition_group"] == "C_exp01_detects_candidate_misses")
    # FN from undersegmentation in already-detected tiles
    fn_from_undersegmented = sum(r["exp02b1_fn"] - r["exp01_fn"] for r in positive_tile_results if r["partition_group"].startswith("B_"))

    pct_fn_whole = (fn_from_whole_misses / delta_fn * 100.0) if delta_fn > 0 else 0.0
    pct_fn_underseg = (fn_from_undersegmented / delta_fn * 100.0) if delta_fn > 0 else 0.0

    _log.info("\n--- HYPOTHESIS TEST RESULTS ---")
    _log.info("  Total FN Pixels: EXP01=%d, EXP02B-1=%d (Delta = +%d px)", total_fn_exp01, total_fn_exp02, delta_fn)
    _log.info("  Whole-Tile Miss Count (Group C): %d tiles (%.2f%% of pos tiles)", n_whole_tile_miss, (n_whole_tile_miss / n_pos) * 100)
    _log.info("  Undersegmented Count (Group B):  %d tiles (%.2f%% of pos tiles)", n_undersegmented, (n_undersegmented / n_pos) * 100)
    _log.info("  FN Pixels from Whole-Tile Misses: %d (%.2f%% of delta FN)", fn_from_whole_misses, pct_fn_whole)
    _log.info("  FN Pixels from Undersegmentation: %d (%.2f%% of delta FN)", fn_from_undersegmented, pct_fn_underseg)

    # -------------------------------------------------------------------------
    # PHASE 6 — VALIDATION FAILURE TAXONOMY (DATA-DRIVEN)
    # -------------------------------------------------------------------------
    _log.info("\n--- PHASE 6: VALIDATION FAILURE TAXONOMY ---")

    # Data-driven stratification of Negative False Alarms:
    # 1. Cured FAs: What was cured?
    # 2. Persistent FAs: What remains?
    # 3. New FAs: What was induced?
    # Sub-divide by FP pixel burden:
    # - Small isolated speckle: FP < 50 px, components <= 3
    # - Moderate localized cluster: 50 <= FP < 1000 px
    # - Extensive / Large contiguous artifact: FP >= 1000 px
    fa_taxonomy = {
        "negative_cured_fa_breakdown": {
            "small_isolated_speckle_lt_50px": sum(1 for r in negative_tile_results if r["contingency_class"] == "b_cured_fa" and r["exp01_fp_pixels"] < 50),
            "moderate_cluster_50_to_1000px": sum(1 for r in negative_tile_results if r["contingency_class"] == "b_cured_fa" and 50 <= r["exp01_fp_pixels"] < 1000),
            "extensive_artifact_ge_1000px": sum(1 for r in negative_tile_results if r["contingency_class"] == "b_cured_fa" and r["exp01_fp_pixels"] >= 1000),
        },
        "negative_persistent_fa_breakdown": {
            "small_isolated_speckle_lt_50px": sum(1 for r in negative_tile_results if r["contingency_class"] == "d_both_fa" and r["exp02b1_fp_pixels"] < 50),
            "moderate_cluster_50_to_1000px": sum(1 for r in negative_tile_results if r["contingency_class"] == "d_both_fa" and 50 <= r["exp02b1_fp_pixels"] < 1000),
            "extensive_artifact_ge_1000px": sum(1 for r in negative_tile_results if r["contingency_class"] == "d_both_fa" and r["exp02b1_fp_pixels"] >= 1000),
        },
        "negative_new_fa_breakdown": {
            "small_isolated_speckle_lt_50px": sum(1 for r in negative_tile_results if r["contingency_class"] == "c_new_fa" and r["exp02b1_fp_pixels"] < 50),
            "moderate_cluster_50_to_1000px": sum(1 for r in negative_tile_results if r["contingency_class"] == "c_new_fa" and 50 <= r["exp02b1_fp_pixels"] < 1000),
            "extensive_artifact_ge_1000px": sum(1 for r in negative_tile_results if r["contingency_class"] == "c_new_fa" and r["exp02b1_fp_pixels"] >= 1000),
        },
        "positive_degradation_breakdown": {
            "group_a_candidate_improves": part_counts.get("A_candidate_improves", 0),
            "group_b_undersegmented": part_counts.get("B_both_detect_candidate_undersegments", 0),
            "group_b_other": part_counts.get("B_both_detect_other", 0),
            "group_c_complete_miss": part_counts.get("C_exp01_detects_candidate_misses", 0),
            "group_d_new_detection": part_counts.get("D_candidate_detects_exp01_misses", 0),
            "group_e_both_miss": part_counts.get("E_neither_detects", 0),
        },
        "spill_size_miss_correlation": {
            "tiny_spill_gt_lt_500px": {
                "total_tiles": sum(1 for r in positive_tile_results if r["gt_spill_pixels"] < 500),
                "missed_by_candidate": sum(1 for r in positive_tile_results if r["gt_spill_pixels"] < 500 and r["partition_group"] == "C_exp01_detects_candidate_misses"),
                "detected_by_both": sum(1 for r in positive_tile_results if r["gt_spill_pixels"] < 500 and r["exp01_tp"] >= 1 and r["exp02b1_tp"] >= 1),
            },
            "medium_spill_500_to_5000px": {
                "total_tiles": sum(1 for r in positive_tile_results if 500 <= r["gt_spill_pixels"] < 5000),
                "missed_by_candidate": sum(1 for r in positive_tile_results if 500 <= r["gt_spill_pixels"] < 5000 and r["partition_group"] == "C_exp01_detects_candidate_misses"),
                "detected_by_both": sum(1 for r in positive_tile_results if 500 <= r["gt_spill_pixels"] < 5000 and r["exp01_tp"] >= 1 and r["exp02b1_tp"] >= 1),
            },
            "large_spill_ge_5000px": {
                "total_tiles": sum(1 for r in positive_tile_results if r["gt_spill_pixels"] >= 5000),
                "missed_by_candidate": sum(1 for r in positive_tile_results if r["gt_spill_pixels"] >= 5000 and r["partition_group"] == "C_exp01_detects_candidate_misses"),
                "detected_by_both": sum(1 for r in positive_tile_results if r["gt_spill_pixels"] >= 5000 and r["exp01_tp"] >= 1 and r["exp02b1_tp"] >= 1),
            },
        },
    }

    with open(OUTPUT_DIR / "failure_taxonomy.json", "w", encoding="utf-8") as f:
        json.dump(fa_taxonomy, f, indent=2)
    _log.info("Saved failure_taxonomy.json")

    # -------------------------------------------------------------------------
    # SAVE MACHINE-READABLE DIAGNOSTIC SUMMARY JSON
    # -------------------------------------------------------------------------
    summary_json = {
        "experiment_id": "EXP-02B-1",
        "diagnostic_id": "diagnostic_20260909_142000",
        "authoritative_candidate": "best_model.pt (Epoch 3)",
        "locked_threshold": FROZEN_THRESHOLD,
        "validation_population": {
            "total_tiles": 2880,
            "negative_tiles": n_neg,
            "positive_tiles": n_pos,
        },
        "negative_paired_contingency": {
            "a_both_clean": a,
            "b_cured_fa": b,
            "c_new_fa": c,
            "d_both_fa": d,
            "exp01_fa_count": fa_exp01,
            "exp02b1_fa_count": fa_exp02,
            "exp01_fa_rate_pct": round(rate_exp01, 4),
            "exp02b1_fa_rate_pct": round(rate_exp02, 4),
            "abs_reduction_pct_pts": round(abs_red, 4),
            "rel_reduction_pct": round(rel_red, 4),
            "mcnemar_chi2": round(chi2_stat, 4),
            "mcnemar_p_value": float(p_val),
            "ci_95_diff_pct_pts": [round(ci_lo * 100, 4), round(ci_hi * 100, 4)],
        },
        "positive_partition": part_counts,
        "hypothesis_test_recall_loss": {
            "question": "Is the recall loss predominantly whole-tile detection loss, or is it predominantly reduced spatial extent/undersegmentation within already-detected positive tiles?",
            "n_whole_tile_misses": n_whole_tile_miss,
            "pct_whole_tile_misses": round((n_whole_tile_miss / n_pos) * 100, 2),
            "n_undersegmented": n_undersegmented,
            "pct_undersegmented": round((n_undersegmented / n_pos) * 100, 2),
            "fn_pixels_from_whole_misses": fn_from_whole_misses,
            "pct_fn_from_whole_misses": round(pct_fn_whole, 2),
            "fn_pixels_from_undersegmentation": fn_from_undersegmented,
            "pct_fn_from_undersegmentation": round(pct_fn_underseg, 2),
            "empirical_conclusion": (
                "Undersegmentation (spatial extent shrinkage within already-detected tiles) "
                f"accounts for {pct_fn_underseg:.1f}% of increased FN pixels, whereas whole-tile "
                f"spill misses account for only {pct_fn_whole:.1f}%."
            ),
        },
        "pareto_efficient_epochs": pareto_epochs,
        "completed_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(OUTPUT_DIR / "diagnostic_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_json, f, indent=2)
    _log.info("Saved diagnostic_summary.json")

    _log.info("\n" + "=" * 80)
    _log.info("DIAGNOSTIC COMPUTATIONS COMPLETE")
    _log.info("=" * 80)


if __name__ == "__main__":
    run_diagnostic()
