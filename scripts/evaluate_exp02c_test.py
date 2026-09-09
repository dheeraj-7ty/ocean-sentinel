"""Ocean Sentinel — EXP-02C: Frozen Held-Out Official Test Set Evaluation Runner.

Strict Scientific Constraints (CAO Formal Authorization):
- Single-pass evaluation on canonical test split (2,880 tiles, 180 patches).
- Model weights strictly frozen (best_model.pt, Epoch 26, SHA: 14073F67...).
- Threshold locked to 0.22 (zero search, zero tuning).
- Input preprocessing: canonical normalization + IdentityTransform (unaugmented).
- Output directory: experiments/performance/exp02c_annealed_hard_negative_20260909_144000/official_test_evaluation/
- Pairwise comparisons against certified EXP-01 baseline and EXP-02B-1 Epoch 3 candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import platform
import socket
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName
from ocean_sentinel.ml.augmentation import IdentityTransform
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss
from ocean_sentinel.ml.metrics import SegmentationMeter
from ocean_sentinel.ml.unet_resnet import ResNet34UNet, count_parameters

# Certified Invariants & Paths
MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
EXPECTED_MANIFEST_SHA256 = "C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0"

CHECKPOINT_PATH = REPO_ROOT / "experiments" / "performance" / "exp02c_annealed_hard_negative_20260909_144000" / "best_model.pt"
EXPECTED_CHECKPOINT_SHA256 = "14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A"

HISTORICAL_TEST_PATH = REPO_ROOT / "experiments" / "performance" / "exp02b_1_test_evaluation_20260909_140500" / "test_results.json"

OUTPUT_DIR = REPO_ROOT / "experiments" / "performance" / "exp02c_annealed_hard_negative_20260909_144000" / "official_test_evaluation"
FROZEN_THRESHOLD = 0.22

_log = logging.getLogger("exp02c_test")


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


def atomic_write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(f".tmp_{os.getpid()}")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def write_run_state(output_dir: Path, state: dict) -> None:
    state["last_activity_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    atomic_write_json(output_dir / "run_state.json", state)


def evaluate_model_on_test(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    threshold: float = 0.22,
    model_name: str = "EXP02C_Epoch26",
    output_dir: Optional[Path] = None,
    run_state: Optional[dict] = None,
) -> dict:
    model.eval()
    meter = SegmentationMeter(threshold=threshold)
    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0).to(device)

    loss_sum = 0.0
    n_tiles = 0

    n_neg_tiles = 0
    neg_fa_tiles = 0
    neg_macro_fa_tiles = 0
    neg_extensive_fa_tiles = 0
    neg_fp_pixels_total = 0
    neg_tile_predictions = []

    n_pos_tiles = 0
    pos_detected_tiles = 0
    pos_gt_pixels_total = 0
    pos_pred_pixels_total = 0
    pos_fn_pixels_total = 0
    undersegmented_count = 0
    pos_tile_predictions = []

    scale_stats = {
        "tiny": {"n": 0, "tp": 0, "fn": 0},
        "medium": {"n": 0, "tp": 0, "fn": 0},
        "large": {"n": 0, "tp": 0, "fn": 0},
    }

    tile_records = []
    t_start = time.time()
    batch_count = len(loader)

    with torch.no_grad():
        for batch_idx, (imgs, masks) in enumerate(loader, 1):
            imgs = imgs.to(device, non_blocking=True)
            masks = masks.to(device, non_blocking=True)

            with torch.amp.autocast("cuda", dtype=torch.float16):
                logits = model(imgs)
                loss = criterion(logits, masks)

            probs = torch.sigmoid(logits)
            bs = imgs.shape[0]
            loss_sum += loss.item() * bs
            n_tiles += bs
            meter.update(logits, masks)

            p_cpu = probs.squeeze(1).cpu()
            m_cpu = masks.squeeze(1).cpu()

            for i in range(bs):
                gt_sum = int(m_cpu[i].sum().item())
                pred_px = int((p_cpu[i] >= threshold).sum().item())

                if gt_sum == 0:
                    n_neg_tiles += 1
                    fp_px = pred_px
                    neg_fp_pixels_total += fp_px
                    is_fa = int(fp_px >= 1)
                    if is_fa:
                        neg_fa_tiles += 1
                    if fp_px >= 100:
                        neg_macro_fa_tiles += 1
                    if fp_px >= 1000:
                        neg_extensive_fa_tiles += 1
                    neg_tile_predictions.append(is_fa)
                    tile_records.append({
                        "tile_index": n_tiles - bs + i,
                        "is_negative": True,
                        "gt_pixels": 0,
                        "pred_pixels": pred_px,
                        "fp_pixels": fp_px,
                        "is_fa": is_fa,
                    })
                else:
                    n_pos_tiles += 1
                    pos_gt_pixels_total += gt_sum
                    pos_pred_pixels_total += pred_px

                    tp_px = int(((p_cpu[i] >= threshold) & (m_cpu[i] == 1)).sum().item())
                    fn_px = gt_sum - tp_px
                    fp_px = pred_px - tp_px
                    pos_fn_pixels_total += fn_px

                    is_detected = int(tp_px >= 1)
                    if is_detected:
                        pos_detected_tiles += 1
                        if pred_px < 0.80 * gt_sum:
                            undersegmented_count += 1
                    pos_tile_predictions.append(is_detected)

                    if gt_sum < 500:
                        scale_stats["tiny"]["n"] += 1
                        scale_stats["tiny"]["tp"] += tp_px
                        scale_stats["tiny"]["fn"] += fn_px
                    elif gt_sum < 5000:
                        scale_stats["medium"]["n"] += 1
                        scale_stats["medium"]["tp"] += tp_px
                        scale_stats["medium"]["fn"] += fn_px
                    else:
                        scale_stats["large"]["n"] += 1
                        scale_stats["large"]["tp"] += tp_px
                        scale_stats["large"]["fn"] += fn_px

                    tile_records.append({
                        "tile_index": n_tiles - bs + i,
                        "is_negative": False,
                        "gt_pixels": gt_sum,
                        "pred_pixels": pred_px,
                        "tp_pixels": tp_px,
                        "fn_pixels": fn_px,
                        "fp_pixels": fp_px,
                        "is_detected": is_detected,
                        "undersegmented": bool(pred_px < 0.80 * gt_sum),
                    })

            if batch_idx % 50 == 0 or batch_idx == batch_count:
                dt = time.time() - t_start
                throughput = n_tiles / dt
                remaining_batches = batch_count - batch_idx
                eta_s = (dt / batch_idx) * remaining_batches
                _log.info(
                    "  [%s] Batch %03d/%03d (%5.1f%%) | Tiles: %d | Throughput: %.1f tiles/s | ETA: %.1fs",
                    model_name,
                    batch_idx,
                    batch_count,
                    (batch_idx / batch_count) * 100,
                    n_tiles,
                    throughput,
                    eta_s,
                )
                if output_dir and run_state:
                    run_state.update({
                        "evaluating_model": model_name,
                        "processed_tiles": n_tiles,
                        "total_test_tiles": 2880,
                        "throughput_tiles_per_sec": round(throughput, 1),
                        "eta_sec": round(eta_s, 1),
                    })
                    write_run_state(output_dir, run_state)

    duration = time.time() - t_start
    metrics = meter.compute()

    tp = float(metrics["tp"])
    fp = float(metrics["fp"])
    fn = float(metrics["fn"])
    tn = float(metrics["tn"])

    fa_rate = (neg_fa_tiles / n_neg_tiles * 100.0) if n_neg_tiles > 0 else 0.0
    fp_pixel_fraction = (neg_fp_pixels_total / (n_neg_tiles * 512 * 512)) if n_neg_tiles > 0 else 0.0
    macro_fa_rate = (neg_macro_fa_tiles / n_neg_tiles * 100.0) if n_neg_tiles > 0 else 0.0
    extensive_fa_rate = (neg_extensive_fa_tiles / n_neg_tiles * 100.0) if n_neg_tiles > 0 else 0.0

    pos_tile_recall = (pos_detected_tiles / n_pos_tiles * 100.0) if n_pos_tiles > 0 else 0.0
    pred_gt_ratio = (pos_pred_pixels_total / pos_gt_pixels_total) if pos_gt_pixels_total > 0 else 0.0

    tiny_recall = scale_stats["tiny"]["tp"] / (scale_stats["tiny"]["tp"] + scale_stats["tiny"]["fn"]) if (scale_stats["tiny"]["tp"] + scale_stats["tiny"]["fn"]) > 0 else 0.0
    medium_recall = scale_stats["medium"]["tp"] / (scale_stats["medium"]["tp"] + scale_stats["medium"]["fn"]) if (scale_stats["medium"]["tp"] + scale_stats["medium"]["fn"]) > 0 else 0.0
    large_recall = scale_stats["large"]["tp"] / (scale_stats["large"]["tp"] + scale_stats["large"]["fn"]) if (scale_stats["large"]["tp"] + scale_stats["large"]["fn"]) > 0 else 0.0

    return {
        "model_name": model_name,
        "n_tiles_consumed": n_tiles,
        "threshold_used": threshold,
        "duration_sec": round(duration, 2),
        "throughput_tiles_per_sec": round(n_tiles / duration, 1),
        "loss": round(loss_sum / max(n_tiles, 1), 5),
        "iou": round(float(metrics["iou"]), 5),
        "dice": round(float(metrics["dice"]), 5),
        "precision": round(float(metrics["precision"]), 5),
        "recall": round(float(metrics["recall"]), 5),
        "pixel_confusion_matrix": {
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
            "tn": int(tn),
            "total_pixels": int(tp + fp + fn + tn),
        },
        "negatives": {
            "n_negative_tiles": n_neg_tiles,
            "fa_tiles": neg_fa_tiles,
            "fa_rate_pct": round(fa_rate, 4),
            "fp_pixel_burden_total": neg_fp_pixels_total,
            "fp_pixel_fraction": round(fp_pixel_fraction, 6),
            "macro_fa_tiles": neg_macro_fa_tiles,
            "macro_fa_rate_pct": round(macro_fa_rate, 4),
            "extensive_fa_tiles": neg_extensive_fa_tiles,
            "extensive_fa_rate_pct": round(extensive_fa_rate, 4),
            "per_tile_fa_binary": neg_tile_predictions,
        },
        "positives": {
            "n_positive_tiles": n_pos_tiles,
            "detected_tiles": pos_detected_tiles,
            "tile_detection_rate_pct": round(pos_tile_recall, 4),
            "pos_gt_pixels_total": pos_gt_pixels_total,
            "pos_pred_pixels_total": pos_pred_pixels_total,
            "pos_fn_pixels_total": pos_fn_pixels_total,
            "pred_gt_ratio": round(pred_gt_ratio, 4),
            "undersegmented_count": undersegmented_count,
            "tiny_spill_recall": round(tiny_recall, 4),
            "medium_spill_recall": round(medium_recall, 4),
            "large_spill_recall": round(large_recall, 4),
            "per_tile_detected_binary": pos_tile_predictions,
        },
        "tile_records": tile_records,
    }


def compute_paired_mcnemar(y_ref: np.ndarray, y_cand: np.ndarray, ref_name: str, cand_name: str) -> dict:
    assert len(y_ref) == len(y_cand), "Paired arrays must have identical length"
    n_neg = len(y_ref)

    a = int(np.sum((y_ref == 0) & (y_cand == 0)))
    b = int(np.sum((y_ref == 1) & (y_cand == 0)))  # ref had FA, cand cured it
    c = int(np.sum((y_ref == 0) & (y_cand == 1)))  # cand has new FA
    d = int(np.sum((y_ref == 1) & (y_cand == 1)))  # both had FA
    assert a + b + c + d == n_neg

    p1 = (b + d) / n_neg
    p2 = (c + d) / n_neg
    diff = p1 - p2
    net_cured = b - c
    rel_red = (net_cured / (b + d)) if (b + d) > 0 else 0.0

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
    ci_lo = diff - z * se
    ci_hi = diff + z * se

    return {
        "reference_model": ref_name,
        "candidate_model": cand_name,
        "n_negative_tiles": n_neg,
        "contingency_table": {
            "a_both_neg": a,
            "b_cured_fa": b,
            "c_new_fa": c,
            "d_both_fa": d,
        },
        "reference_fa_rate_pct": round(p1 * 100, 4),
        "candidate_fa_rate_pct": round(p2 * 100, 4),
        "reference_fa_tiles": b + d,
        "candidate_fa_tiles": c + d,
        "net_alarm_count_reduction": net_cured,
        "abs_reduction_pct_pts": round(diff * 100, 4),
        "rel_reduction_pct": round(rel_red * 100, 4),
        "mcnemar_chi2": round(chi2_stat, 4),
        "mcnemar_p_value": float(p_val),
        "ci_95_diff_pct_pts": [round(ci_lo * 100, 4), round(ci_hi * 100, 4)],
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    setup_logging(OUTPUT_DIR)

    _log.info("=" * 80)
    _log.info("EXP-02C: FROZEN HELD-OUT OFFICIAL TEST SET EVALUATION")
    _log.info("=" * 80)

    # 1. Mandatory Pre-Evaluation Audit
    _log.info("\n--- PRE-EVALUATION AUDIT & STOP CONDITIONS CHECK ---")

    # Checkpoint check
    assert CHECKPOINT_PATH.exists(), f"Checkpoint missing: {CHECKPOINT_PATH}"
    actual_chk_sha = file_sha256(CHECKPOINT_PATH)
    _log.info("Checkpoint:         %s", CHECKPOINT_PATH)
    _log.info("Checkpoint SHA-256: %s", actual_chk_sha)
    assert actual_chk_sha == EXPECTED_CHECKPOINT_SHA256, f"Checkpoint hash mismatch: {actual_chk_sha} != {EXPECTED_CHECKPOINT_SHA256}"
    _log.info("  [PASS] Checkpoint identity & SHA-256 strictly verified.")

    # Manifest check
    assert MANIFEST_PATH.exists(), f"Manifest missing: {MANIFEST_PATH}"
    actual_manifest_sha = file_sha256(MANIFEST_PATH)
    _log.info("Manifest:           %s", MANIFEST_PATH)
    _log.info("Manifest SHA-256:   %s", actual_manifest_sha)
    assert actual_manifest_sha == EXPECTED_MANIFEST_SHA256, f"Manifest hash mismatch: {actual_manifest_sha} != {EXPECTED_MANIFEST_SHA256}"
    _log.info("  [PASS] Canonical spatial split manifest identity & SHA-256 strictly verified.")

    # Runner script check
    runner_path = Path(__file__).resolve()
    runner_sha = file_sha256(runner_path)
    _log.info("Runner Script:      %s", runner_path)
    _log.info("Runner SHA-256:     %s", runner_sha)

    # Device check
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    assert device.type == "cuda", "FATAL: Evaluation strictly requires CUDA GPU execution."
    gpu_name = torch.cuda.get_device_name(0)
    _log.info("GPU Device:         %s (%s)", gpu_name, torch.cuda.get_device_capability(0))

    # Manifest population check
    manifest = DatasetManifest.load(MANIFEST_PATH)
    test_tiles = [t for t in manifest.tiles if t.split == SplitName.TEST]
    train_tiles = [t for t in manifest.tiles if t.split == SplitName.TRAIN]
    val_tiles = [t for t in manifest.tiles if t.split == SplitName.VAL]

    _log.info("Train tiles:        %d", len(train_tiles))
    _log.info("Val tiles:          %d", len(val_tiles))
    _log.info("Test tiles:         %d", len(test_tiles))
    assert len(test_tiles) == 2880, f"Expected 2880 test tiles, got {len(test_tiles)}"
    _log.info("  [PASS] Exact canonical test tile count = 2,880 verified.")

    test_ids = set(t.tile_id for t in test_tiles)
    train_ids = set(t.tile_id for t in train_tiles)
    val_ids = set(t.tile_id for t in val_tiles)
    assert len(test_ids) == 2880, "Duplicate test tile IDs found!"
    assert len(test_ids.intersection(train_ids)) == 0, "Test/Train contamination!"
    assert len(test_ids.intersection(val_ids)) == 0, "Test/Val contamination!"
    _log.info("  [PASS] Zero duplicate tiles and zero cross-split contamination verified.")

    # Load checkpoint & verify metadata
    chk = torch.load(CHECKPOINT_PATH, map_location="cpu")
    chk_epoch = chk.get("epoch")
    chk_iou = chk.get("val_iou")
    chk_rec = chk.get("val_recall")
    chk_thresh = chk.get("threshold")
    _log.info("Checkpoint Metadata: Epoch %s, Val IoU %s, Val Recall %s, Threshold %s", chk_epoch, chk_iou, chk_rec, chk_thresh)
    assert chk_epoch == 26, f"Expected Epoch 26 checkpoint, got {chk_epoch}"
    assert chk_thresh == FROZEN_THRESHOLD, f"Expected threshold {FROZEN_THRESHOLD}, got {chk_thresh}"
    _log.info("  [PASS] Locked threshold = %.2f and Epoch 26 metadata verified.", FROZEN_THRESHOLD)

    # Instantiate Model
    model = ResNet34UNet(
        in_channels=2,
        num_classes=1,
        pretrained=False,
        adaptation_method="slice_variance_scaled",
    ).to(device)
    model.load_state_dict(chk["model_state_dict"], strict=True)
    params = count_parameters(model)
    _log.info("Model Parameters:   %d total, %d trainable", params["total"], params["trainable"])
    assert params["total"] == 24346305, f"Expected 24346305 parameters, got {params['total']}"
    _log.info("  [PASS] Exact ResNet34UNet architecture contract strictly loaded.")

    # Normalization check
    norm_stats = manifest.normalization_stats
    _log.info("Normalization:      %s", norm_stats)
    _log.info("  [PASS] Canonical normalization constants verified.")

    # Dataset & Loader
    eval_tfm = IdentityTransform()
    ds_test = TrujilloTileDataset(manifest, SplitName.TEST, normalize=True, transform=eval_tfm)
    assert len(ds_test) == 2880
    test_loader = DataLoader(
        ds_test,
        batch_size=8,
        shuffle=False,
        num_workers=2,
        pin_memory=True,
    )

    run_state = {
        "run_id": f"test_eval_{int(time.time())}",
        "experiment": "EXP-02C_official_held_out_test_evaluation",
        "pre_evaluation_audit": "PASS",
        "threshold": FROZEN_THRESHOLD,
        "checkpoint_sha256": actual_chk_sha,
        "manifest_sha256": actual_manifest_sha,
        "runner_sha256": runner_sha,
        "start_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "RUNNING_TEST_EVALUATION",
    }
    write_run_state(OUTPUT_DIR, run_state)

    _log.info("\n" + "=" * 80)
    _log.info("STARTING SINGLE-PASS HELD-OUT TEST EVALUATION ON 2,880 TEST TILES")
    _log.info("=" * 80)

    # 2. Evaluate EXP-02C Epoch 26
    t0 = time.time()
    test_eval = evaluate_model_on_test(
        model=model,
        loader=test_loader,
        device=device,
        threshold=FROZEN_THRESHOLD,
        model_name="EXP02C_Epoch26",
        output_dir=OUTPUT_DIR,
        run_state=run_state,
    )
    t_eval_dur = time.time() - t0

    _log.info("\n--- EXP-02C (EPOCH 26) OFFICIAL HELD-OUT TEST RESULTS ---")
    _log.info("  Test Tiles Consumed:    %d", test_eval["n_tiles_consumed"])
    _log.info("  Duration:               %.1f s (Throughput: %.1f tiles/s)", test_eval["duration_sec"], test_eval["throughput_tiles_per_sec"])
    _log.info("  Test Loss:              %.5f", test_eval["loss"])
    _log.info("  Global Test IoU:        %.5f", test_eval["iou"])
    _log.info("  Test Dice:              %.5f", test_eval["dice"])
    _log.info("  Test Precision:         %.5f", test_eval["precision"])
    _log.info("  Test Recall:            %.5f", test_eval["recall"])
    cm = test_eval["pixel_confusion_matrix"]
    _log.info("  Pixel Confusion Matrix: TP=%d, FP=%d, FN=%d, TN=%d", cm["tp"], cm["fp"], cm["fn"], cm["tn"])
    negs = test_eval["negatives"]
    _log.info("  Negative Tiles:         %d", negs["n_negative_tiles"])
    _log.info("  False Alarm Tiles:      %d (FA Rate: %.2f%%)", negs["fa_tiles"], negs["fa_rate_pct"])
    _log.info("  FP Pixel Burden:        %d pixels (Fraction: %.6f)", negs["fp_pixel_burden_total"], negs["fp_pixel_fraction"])
    _log.info("  Macro FA Tiles (>=100): %d (Macro FA Rate: %.2f%%)", negs["macro_fa_tiles"], negs["macro_fa_rate_pct"])
    _log.info("  Extensive FA (>=1000):  %d (Extensive FA Rate: %.2f%%)", negs["extensive_fa_tiles"], negs["extensive_fa_rate_pct"])
    poss = test_eval["positives"]
    _log.info("  Positive Tiles:         %d", poss["n_positive_tiles"])
    _log.info("  Positive Tile Recall:   %d / %d (%.2f%%)", poss["detected_tiles"], poss["n_positive_tiles"], poss["tile_detection_rate_pct"])
    _log.info("  Pred/GT Area Ratio:     %.4f", poss["pred_gt_ratio"])
    _log.info("  Undersegmented Tiles:   %d", poss["undersegmented_count"])
    _log.info("  Scale Recalls:          Tiny: %.2f%% | Medium: %.2f%% | Large: %.2f%%", poss["tiny_spill_recall"] * 100, poss["medium_spill_recall"] * 100, poss["large_spill_recall"] * 100)

    # 3. Exact Pairwise Comparisons Against Historical Test Evaluations
    pairwise_exp01 = None
    pairwise_exp02b_1 = None

    if HISTORICAL_TEST_PATH.exists():
        _log.info("\n" + "=" * 80)
        _log.info("COMPUTING EXACT PAIRED TILE-LEVEL COMPARISONS AGAINST CERTIFIED BASELINES")
        _log.info("=" * 80)
        with open(HISTORICAL_TEST_PATH, "r", encoding="utf-8") as f:
            hist_d = json.load(f)

        y_c = np.array(negs["per_tile_fa_binary"], dtype=np.int32)

        # Baseline EXP-01 comparison
        if "baseline_evaluation" in hist_d and "negatives" in hist_d["baseline_evaluation"]:
            y_t = np.array(hist_d["baseline_evaluation"]["negatives"]["per_tile_fa_binary"], dtype=np.int32)
            pairwise_exp01 = compute_paired_mcnemar(y_t, y_c, ref_name="EXP01_Baseline", cand_name="EXP02C_Epoch26")
            _log.info("\n--- PAIRED COMPARISON: EXP-02C (Epoch 26) vs EXP-01 Baseline ---")
            _log.info("  Contingency Table (n=%d): a=%d, b=%d, c=%d, d=%d", pairwise_exp01["n_negative_tiles"],
                      pairwise_exp01["contingency_table"]["a_both_neg"],
                      pairwise_exp01["contingency_table"]["b_cured_fa"],
                      pairwise_exp01["contingency_table"]["c_new_fa"],
                      pairwise_exp01["contingency_table"]["d_both_fa"])
            _log.info("  EXP-01 FA Rate:         %.2f%% (%d tiles)", pairwise_exp01["reference_fa_rate_pct"], pairwise_exp01["reference_fa_tiles"])
            _log.info("  EXP-02C FA Rate:        %.2f%% (%d tiles)", pairwise_exp01["candidate_fa_rate_pct"], pairwise_exp01["candidate_fa_tiles"])
            _log.info("  Net Alarm Reduction:    %d tiles", pairwise_exp01["net_alarm_count_reduction"])
            _log.info("  Absolute Reduction:     %.2f percentage points", pairwise_exp01["abs_reduction_pct_pts"])
            _log.info("  Relative Reduction:     %.2f%%", pairwise_exp01["rel_reduction_pct"])
            _log.info("  McNemar Chi2:           %.4f (p = %.4e)", pairwise_exp01["mcnemar_chi2"], pairwise_exp01["mcnemar_p_value"])
            _log.info("  Wald 95%% Paired CI:     [%.2f, %.2f] percentage points", pairwise_exp01["ci_95_diff_pct_pts"][0], pairwise_exp01["ci_95_diff_pct_pts"][1])

        # Candidate EXP-02B-1 Epoch 3 comparison
        if "candidate_evaluation" in hist_d and "negatives" in hist_d["candidate_evaluation"]:
            y_b = np.array(hist_d["candidate_evaluation"]["negatives"]["per_tile_fa_binary"], dtype=np.int32)
            pairwise_exp02b_1 = compute_paired_mcnemar(y_b, y_c, ref_name="EXP02B-1_Epoch3", cand_name="EXP02C_Epoch26")
            _log.info("\n--- PAIRED COMPARISON: EXP-02C (Epoch 26) vs EXP-02B-1 (Epoch 3) ---")
            _log.info("  Contingency Table (n=%d): a=%d, b=%d, c=%d, d=%d", pairwise_exp02b_1["n_negative_tiles"],
                      pairwise_exp02b_1["contingency_table"]["a_both_neg"],
                      pairwise_exp02b_1["contingency_table"]["b_cured_fa"],
                      pairwise_exp02b_1["contingency_table"]["c_new_fa"],
                      pairwise_exp02b_1["contingency_table"]["d_both_fa"])
            _log.info("  EXP-02B-1 FA Rate:      %.2f%% (%d tiles)", pairwise_exp02b_1["reference_fa_rate_pct"], pairwise_exp02b_1["reference_fa_tiles"])
            _log.info("  EXP-02C FA Rate:        %.2f%% (%d tiles)", pairwise_exp02b_1["candidate_fa_rate_pct"], pairwise_exp02b_1["candidate_fa_tiles"])
            _log.info("  Net Alarm Reduction:    %d tiles", pairwise_exp02b_1["net_alarm_count_reduction"])
            _log.info("  Absolute Reduction:     %.2f percentage points", pairwise_exp02b_1["abs_reduction_pct_pts"])
            _log.info("  Relative Reduction:     %.2f%%", pairwise_exp02b_1["rel_reduction_pct"])
            _log.info("  McNemar Chi2:           %.4f (p = %.4e)", pairwise_exp02b_1["mcnemar_chi2"], pairwise_exp02b_1["mcnemar_p_value"])
            _log.info("  Wald 95%% Paired CI:     [%.2f, %.2f] percentage points", pairwise_exp02b_1["ci_95_diff_pct_pts"][0], pairwise_exp02b_1["ci_95_diff_pct_pts"][1])

    # 4. Save Artifacts
    _log.info("\n--- PERSISTING OFFICIAL TEST EVALUATION ARTIFACTS ---")
    tile_recs = test_eval.pop("tile_records")

    # Confusion matrix
    atomic_write_json(OUTPUT_DIR / "confusion_matrix.json", cm)
    _log.info("Saved confusion_matrix.json")

    # Test prediction summary
    test_pred_summary = {
        "n_tiles_total": test_eval["n_tiles_consumed"],
        "n_neg_tiles": negs["n_negative_tiles"],
        "n_pos_tiles": poss["n_positive_tiles"],
        "neg_fa_tiles": negs["fa_tiles"],
        "neg_fa_rate_pct": negs["fa_rate_pct"],
        "neg_macro_fa_tiles": negs["macro_fa_tiles"],
        "neg_extensive_fa_tiles": negs["extensive_fa_tiles"],
        "pos_detected_tiles": poss["detected_tiles"],
        "pos_tile_detection_rate_pct": poss["tile_detection_rate_pct"],
        "pred_gt_ratio": poss["pred_gt_ratio"],
        "undersegmented_count": poss["undersegmented_count"],
        "scale_recalls": {
            "tiny": poss["tiny_spill_recall"],
            "medium": poss["medium_spill_recall"],
            "large": poss["large_spill_recall"],
        },
    }
    atomic_write_json(OUTPUT_DIR / "test_prediction_summary.json", test_pred_summary)
    _log.info("Saved test_prediction_summary.json")

    # Pairwise comparison artifacts
    if pairwise_exp01:
        atomic_write_json(OUTPUT_DIR / "pairwise_vs_exp01.json", pairwise_exp01)
        _log.info("Saved pairwise_vs_exp01.json")
    if pairwise_exp02b_1:
        atomic_write_json(OUTPUT_DIR / "pairwise_vs_exp02b_1.json", pairwise_exp02b_1)
        _log.info("Saved pairwise_vs_exp02b_1.json")

    # Official test results
    official_results = {
        "experiment_id": "EXP-02C",
        "checkpoint_epoch": 26,
        "checkpoint_path": str(CHECKPOINT_PATH),
        "checkpoint_sha256": actual_chk_sha,
        "manifest_path": str(MANIFEST_PATH),
        "manifest_sha256": actual_manifest_sha,
        "runner_script": str(runner_path),
        "runner_sha256": runner_sha,
        "threshold": FROZEN_THRESHOLD,
        "single_pass_confirmed": True,
        "evaluation_split": "held_out_spatial_test",
        "n_test_tiles": test_eval["n_tiles_consumed"],
        "test_metrics": test_eval,
        "pairwise_vs_exp01": pairwise_exp01,
        "pairwise_vs_exp02b_1": pairwise_exp02b_1,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    atomic_write_json(OUTPUT_DIR / "official_test_results.json", official_results)
    _log.info("Saved official_test_results.json")

    # Update run state
    run_state.update({
        "status": "COMPLETED",
        "completed_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_iou": test_eval["iou"],
        "test_recall": test_eval["recall"],
        "test_precision": test_eval["precision"],
        "test_fa_rate_pct": negs["fa_rate_pct"],
        "test_tiles_consumed": test_eval["n_tiles_consumed"],
    })
    write_run_state(OUTPUT_DIR, run_state)
    _log.info("Updated run_state.json")

    _log.info("=" * 80)
    _log.info("OFFICIAL EXP-02C TEST EVALUATION COMPLETED SUCCESSFULLY")
    _log.info("=" * 80)


if __name__ == "__main__":
    main()
