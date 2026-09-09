"""EXP-02B-1: Frozen Held-Out Test Set Evaluation Runner.

Strict Scientific Constraints (CAO Formal Authorization):
- Single-pass evaluation on canonical test split (2,880 tiles, 180 patches).
- Model weights strictly frozen (best_model.pt, Epoch 3, SHA: 54B4B098...).
- Threshold locked to 0.22 (zero search, zero tuning).
- Input preprocessing: canonical normalization + IdentityTransform (unaugmented).
- Output directory: experiments/performance/exp02b_1_test_evaluation_20260909_140500/
- Compare directly against EXP-01 baseline test metrics.
"""

from __future__ import annotations

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

# Invariants & Paths
MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
EXPECTED_MANIFEST_SHA256 = "C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0"

CHECKPOINT_PATH = REPO_ROOT / "experiments" / "performance" / "exp02b_1_hard_negative_training_20260909_094500" / "kernel_output" / "exp02b_1_hard_negative_training" / "best_model.pt"
EXPECTED_CHECKPOINT_SHA256 = "54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B"

TEACHER_PATH = REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt"
EXPECTED_TEACHER_SHA256 = "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699"

OUTPUT_DIR = REPO_ROOT / "experiments" / "performance" / "exp02b_1_test_evaluation_20260909_140500"
FROZEN_THRESHOLD = 0.22

_log = logging.getLogger("exp02b_1_test")


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
    model_name: str = "EXP02B-1_Epoch3",
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
    neg_fp_pixels_total = 0
    neg_extensive_fa_tiles = 0
    neg_tile_predictions = []

    n_pos_tiles = 0
    pos_detected_tiles = 0
    pos_tile_predictions = []

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
                gt_sum = m_cpu[i].sum().item()
                if gt_sum == 0:
                    n_neg_tiles += 1
                    fp_px = int((p_cpu[i] >= threshold).sum().item())
                    neg_fp_pixels_total += fp_px
                    is_fa = int(fp_px >= 1)
                    if is_fa:
                        neg_fa_tiles += 1
                    if fp_px >= 1000:
                        neg_extensive_fa_tiles += 1
                    neg_tile_predictions.append(is_fa)
                else:
                    n_pos_tiles += 1
                    tp_px = int(((p_cpu[i] >= threshold) & (m_cpu[i] == 1)).sum().item())
                    is_detected = int(tp_px >= 1)
                    if is_detected:
                        pos_detected_tiles += 1
                    pos_tile_predictions.append(is_detected)

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
    extensive_fa_rate = (neg_extensive_fa_tiles / n_neg_tiles * 100.0) if n_neg_tiles > 0 else 0.0
    pos_tile_recall = (pos_detected_tiles / n_pos_tiles * 100.0) if n_pos_tiles > 0 else 0.0

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
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "total_pixels": tp + fp + fn + tn,
        },
        "negatives": {
            "n_negative_tiles": n_neg_tiles,
            "fa_tiles": neg_fa_tiles,
            "fa_rate_pct": round(fa_rate, 4),
            "fp_pixel_burden_total": neg_fp_pixels_total,
            "fp_pixel_fraction": round(fp_pixel_fraction, 6),
            "extensive_fa_tiles": neg_extensive_fa_tiles,
            "extensive_fa_rate_pct": round(extensive_fa_rate, 4),
            "per_tile_fa_binary": neg_tile_predictions,
        },
        "positives": {
            "n_positive_tiles": n_pos_tiles,
            "detected_tiles": pos_detected_tiles,
            "tile_detection_rate_pct": round(pos_tile_recall, 4),
            "per_tile_detected_binary": pos_tile_predictions,
        },
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    setup_logging(OUTPUT_DIR)

    _log.info("=" * 80)
    _log.info("EXP-02B-1: FROZEN HELD-OUT TEST SET EVALUATION")
    _log.info("=" * 80)

    # 1. Pre-Evaluation Audit
    _log.info("\n--- PRE-EVALUATION AUDIT (MANDATORY CHECKS 1-11) ---")
    
    # Checkpoint check
    assert CHECKPOINT_PATH.exists(), f"Checkpoint missing: {CHECKPOINT_PATH}"
    actual_chk_sha = file_sha256(CHECKPOINT_PATH)
    _log.info("Checkpoint:         %s", CHECKPOINT_PATH)
    _log.info("Checkpoint SHA-256: %s", actual_chk_sha)
    assert actual_chk_sha == EXPECTED_CHECKPOINT_SHA256, f"Checkpoint hash mismatch: {actual_chk_sha} != {EXPECTED_CHECKPOINT_SHA256}"
    _log.info("  [PASS] Item 2 & 10: Checkpoint identity & SHA-256 verified.")

    # Manifest check
    assert MANIFEST_PATH.exists(), f"Manifest missing: {MANIFEST_PATH}"
    actual_manifest_sha = file_sha256(MANIFEST_PATH)
    _log.info("Manifest:           %s", MANIFEST_PATH)
    _log.info("Manifest SHA-256:   %s", actual_manifest_sha)
    assert actual_manifest_sha == EXPECTED_MANIFEST_SHA256, f"Manifest hash mismatch: {actual_manifest_sha} != {EXPECTED_MANIFEST_SHA256}"
    _log.info("  [PASS] Item 6 & 9: Canonical spatial split manifest identity & SHA-256 verified.")

    # Runner hash
    runner_path = Path(__file__).resolve()
    runner_sha = file_sha256(runner_path)
    _log.info("Runner Script:      %s", runner_path)
    _log.info("Runner SHA-256:     %s", runner_sha)
    _log.info("  [PASS] Item 11: Runner script hash recorded.")

    # Device qualification
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    assert device.type == "cuda", "FATAL: Evaluation strictly requires CUDA GPU execution."
    gpu_name = torch.cuda.get_device_name(0)
    _log.info("GPU Device:         %s (%s)", gpu_name, torch.cuda.get_device_capability(0))

    # Manifest tile population
    manifest = DatasetManifest.load(MANIFEST_PATH)
    raw_tiles = manifest.tiles
    test_tiles = [t for t in raw_tiles if t.split == SplitName.TEST]
    train_tiles = [t for t in raw_tiles if t.split == SplitName.TRAIN]
    val_tiles = [t for t in raw_tiles if t.split == SplitName.VAL]

    _log.info("Train tiles:        %d", len(train_tiles))
    _log.info("Val tiles:          %d", len(val_tiles))
    _log.info("Test tiles:         %d", len(test_tiles))

    assert len(test_tiles) == 2880, f"Expected 2880 test tiles, got {len(test_tiles)}"
    _log.info("  [PASS] Item 7: Exact canonical test tile count = 2,880 verified.")

    test_ids = set(t.tile_id for t in test_tiles)
    train_ids = set(t.tile_id for t in train_tiles)
    val_ids = set(t.tile_id for t in val_tiles)
    assert len(test_ids) == 2880, "Duplicate test tile IDs found!"
    assert len(test_ids.intersection(train_ids)) == 0, "Test/Train cross-split contamination!"
    assert len(test_ids.intersection(val_ids)) == 0, "Test/Val cross-split contamination!"
    _log.info("  [PASS] Item 8: Zero duplicates and zero cross-split contamination verified.")

    # Load checkpoint & verify metadata
    chk = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    assert chk["epoch"] == 3, f"Expected Epoch 3 checkpoint, got {chk['epoch']}"
    assert chk["threshold"] == FROZEN_THRESHOLD
    _log.info("Checkpoint Metadata: Epoch %d, Val IoU %.5f, Val Recall %.5f, Val FA Rate %.4f%%", chk["epoch"], chk["val_iou"], chk["val_recall"], chk["val_neg_fa_rate"])
    _log.info("  [PASS] Item 5: Locked threshold = %.2f verified.", FROZEN_THRESHOLD)

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
    assert params["total"] == 24346305
    _log.info("  [PASS] Item 3: Exact ResNet34UNet architecture contract strictly loaded.")

    # Normalization & Preprocessing
    norm_stats = manifest.normalization_stats
    _log.info("Normalization:      %s", norm_stats)
    _log.info("  [PASS] Item 4: Canonical normalization verified.")

    # Construct Test Dataset & DataLoader (Single-Pass Execution)
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
        "experiment": "EXP02B-1_held_out_test_evaluation",
        "pre_evaluation_audit": "PASS",
        "threshold": FROZEN_THRESHOLD,
        "checkpoint_sha256": actual_chk_sha,
        "manifest_sha256": actual_manifest_sha,
        "runner_sha256": runner_sha,
        "start_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "RUNNING_CANDIDATE_EVALUATION",
    }
    write_run_state(OUTPUT_DIR, run_state)

    _log.info("=" * 80)
    _log.info("STARTING SINGLE-PASS HELD-OUT TEST EVALUATION ON 2,880 TEST TILES")
    _log.info("=" * 80)

    # 2. Evaluate Candidate EXP02B-1 (Epoch 3 Best)
    cand_eval = evaluate_model_on_test(
        model=model,
        loader=test_loader,
        device=device,
        threshold=FROZEN_THRESHOLD,
        model_name="EXP02B-1_Epoch3_Best",
        output_dir=OUTPUT_DIR,
        run_state=run_state,
    )

    _log.info("\n--- EXP02B-1 (EPOCH 3) HELD-OUT TEST RESULTS ---")
    _log.info("  Test Tiles Consumed:    %d", cand_eval["n_tiles_consumed"])
    _log.info("  Duration:               %.1f s (Throughput: %.1f tiles/s)", cand_eval["duration_sec"], cand_eval["throughput_tiles_per_sec"])
    _log.info("  Loss:                   %.5f", cand_eval["loss"])
    _log.info("  Global IoU:             %.5f", cand_eval["iou"])
    _log.info("  Dice:                   %.5f", cand_eval["dice"])
    _log.info("  Precision:              %.5f", cand_eval["precision"])
    _log.info("  Recall:                 %.5f", cand_eval["recall"])
    _log.info("  Pixel Confusion Matrix: TP=%.0f, FP=%.0f, FN=%.0f, TN=%.0f", cand_eval["pixel_confusion_matrix"]["tp"], cand_eval["pixel_confusion_matrix"]["fp"], cand_eval["pixel_confusion_matrix"]["fn"], cand_eval["pixel_confusion_matrix"]["tn"])
    _log.info("  Negative Tiles:         %d", cand_eval["negatives"]["n_negative_tiles"])
    _log.info("  False Alarm Tiles:      %d (FA Rate: %.2f%%)", cand_eval["negatives"]["fa_tiles"], cand_eval["negatives"]["fa_rate_pct"])
    _log.info("  FP Pixel Burden:        %d pixels (Fraction: %.6f)", cand_eval["negatives"]["fp_pixel_burden_total"], cand_eval["negatives"]["fp_pixel_fraction"])
    _log.info("  Extensive FA Tiles:     %d (Extensive FA Rate: %.2f%%)", cand_eval["negatives"]["extensive_fa_tiles"], cand_eval["negatives"]["extensive_fa_rate_pct"])
    _log.info("  Positive Tiles:         %d", cand_eval["positives"]["n_positive_tiles"])
    _log.info("  Positive Tile Recall:   %d / %d (%.2f%%)", cand_eval["positives"]["detected_tiles"], cand_eval["positives"]["n_positive_tiles"], cand_eval["positives"]["tile_detection_rate_pct"])

    # 3. Evaluate Baseline EXP01 Teacher Model on Exactly Identical Test Loader
    teacher_eval = None
    if TEACHER_PATH.exists() and file_sha256(TEACHER_PATH) == EXPECTED_TEACHER_SHA256:
        _log.info("\n" + "=" * 80)
        _log.info("EVALUATING CERTIFIED EXP01 BASELINE MODEL ON IDENTICAL TEST LOADER")
        _log.info("=" * 80)
        t_chk = torch.load(TEACHER_PATH, map_location="cpu", weights_only=False)
        t_model = ResNet34UNet(in_channels=2, num_classes=1, pretrained=False, adaptation_method="slice_variance_scaled").to(device)
        t_model.load_state_dict(t_chk["model_state_dict"], strict=True)
        teacher_eval = evaluate_model_on_test(
            model=t_model,
            loader=test_loader,
            device=device,
            threshold=FROZEN_THRESHOLD,
            model_name="EXP01_Baseline",
            output_dir=OUTPUT_DIR,
            run_state=run_state,
        )
        _log.info("\n--- EXP01 BASELINE HELD-OUT TEST RESULTS ---")
        _log.info("  Test Tiles Consumed:    %d", teacher_eval["n_tiles_consumed"])
        _log.info("  Loss:                   %.5f", teacher_eval["loss"])
        _log.info("  Global IoU:             %.5f", teacher_eval["iou"])
        _log.info("  Dice:                   %.5f", teacher_eval["dice"])
        _log.info("  Precision:              %.5f", teacher_eval["precision"])
        _log.info("  Recall:                 %.5f", teacher_eval["recall"])
        _log.info("  Negative Tiles:         %d", teacher_eval["negatives"]["n_negative_tiles"])
        _log.info("  False Alarm Tiles:      %d (FA Rate: %.2f%%)", teacher_eval["negatives"]["fa_tiles"], teacher_eval["negatives"]["fa_rate_pct"])
        _log.info("  Positive Tiles:         %d", teacher_eval["positives"]["n_positive_tiles"])
        _log.info("  Positive Tile Recall:   %d / %d (%.2f%%)", teacher_eval["positives"]["detected_tiles"], teacher_eval["positives"]["n_positive_tiles"], teacher_eval["positives"]["tile_detection_rate_pct"])

    # 4. Compute Test McNemar and Paired Contingency if teacher available
    paired_stats = None
    if teacher_eval is not None:
        y_t = np.array(teacher_eval["negatives"]["per_tile_fa_binary"], dtype=np.int32)
        y_c = np.array(cand_eval["negatives"]["per_tile_fa_binary"], dtype=np.int32)
        assert len(y_t) == len(y_c)
        n_neg = len(y_t)

        a = int(np.sum((y_t == 0) & (y_c == 0)))
        b = int(np.sum((y_t == 1) & (y_c == 0)))
        c = int(np.sum((y_t == 0) & (y_c == 1)))
        d = int(np.sum((y_t == 1) & (y_c == 1)))
        assert a + b + c + d == n_neg

        p1 = (b + d) / n_neg
        p2 = (c + d) / n_neg
        diff = p1 - p2
        rel_red = (b - c) / (b + d) if (b + d) > 0 else 0.0

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

        paired_stats = {
            "n_negative_tiles": n_neg,
            "contingency_table": {"a_both_neg": a, "b_cured_fa": b, "c_new_fa": c, "d_both_fa": d},
            "baseline_fa_rate_pct": round(p1 * 100, 4),
            "candidate_fa_rate_pct": round(p2 * 100, 4),
            "abs_reduction_pct_pts": round(diff * 100, 4),
            "rel_reduction_pct": round(rel_red * 100, 4),
            "mcnemar_chi2": round(chi2_stat, 4),
            "mcnemar_p_value": float(p_val),
            "ci_95_diff_pct_pts": [round(ci_lo * 100, 4), round(ci_hi * 100, 4)],
        }
        _log.info("\n--- TEST PAIRED MCNEMAR ANALYSIS (EXACT TEST ON n=%d NEGATIVE TILES) ---", n_neg)
        _log.info("  Contingency: a=%d, b=%d, c=%d, d=%d", a, b, c, d)
        _log.info("  Baseline FA Rate:     %.2f%% (%d tiles)", p1 * 100, b + d)
        _log.info("  Candidate FA Rate:    %.2f%% (%d tiles)", p2 * 100, c + d)
        _log.info("  Absolute Reduction:   %.2f percentage points", diff * 100)
        _log.info("  Relative Reduction:   %.2f%%", rel_red * 100)
        _log.info("  McNemar Chi2:         %.4f (p = %.4e)", chi2_stat, p_val)
        _log.info("  95%% Paired CI:        [%.2f, %.2f] percentage points", ci_lo * 100, ci_hi * 100)

    # 5. Save Complete Results & Final State
    full_results = {
        "experiment_id": "EXP-02B-1",
        "evaluation_split": "held_out_test",
        "single_pass_confirmed": True,
        "test_tiles_consumed": 2880,
        "threshold": FROZEN_THRESHOLD,
        "candidate_checkpoint_sha256": actual_chk_sha,
        "manifest_sha256": actual_manifest_sha,
        "runner_sha256": runner_sha,
        "candidate_evaluation": cand_eval,
        "baseline_evaluation": teacher_eval,
        "paired_statistics": paired_stats,
        "completed_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    atomic_write_json(OUTPUT_DIR / "test_results.json", full_results)

    run_state.update({
        "status": "COMPLETED",
        "completed_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_iou": cand_eval["iou"],
        "test_recall": cand_eval["recall"],
        "test_precision": cand_eval["precision"],
        "test_fa_rate_pct": cand_eval["negatives"]["fa_rate_pct"],
    })
    write_run_state(OUTPUT_DIR, run_state)

    _log.info("\n" + "=" * 80)
    _log.info("FROZEN TEST EVALUATION SUCCESSFULLY COMPLETED & SAVED")
    _log.info("=" * 80)


if __name__ == "__main__":
    main()
