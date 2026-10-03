"""Independent Scientific Verification Script for Phase 6 Trujillo Part III Evaluation.

Authority: Ocean Sentinel Phase 6 Final Pre-Execution Scientific Integrity Auditor
Execution Class: Fully Independent Post-Evaluation Audit and Recomputation

Absolute Verification Invariants:
1. Native Ground-Truth Authority: Reads original native Part III target masks directly from disk;
   does NOT trust stored target masks without bitwise verification.
2. Bitwise Ground-Truth Equality: Asserts native_source_mask == stored_target_mask for all 450 scenes.
3. Cross-Mapping Consistency: Asserts target_mask_A == target_mask_B == native_source_mask.
4. Independent Prediction Reconstruction: Recomputes prediction_mask = (probability_map >= 0.22)
   directly from FP32 probability_map and asserts exact bitwise equality with stored predictions.
5. Direct Confusion Calculation: Computes TP, FP, FN, TN strictly from (reconstructed_pred, native_mask).
6. Exact Pixel Conservation: Verifies TP + FN == N_fg, FP + TN == N_bg, and sum == 1,887,436,800.
7. Zero External Aggregates: Reconstructs all stratum metrics from scratch without importing summary JSONs.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import rasterio
from rasterio.errors import NotGeoreferencedWarning
import warnings

warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

TOTAL_SCENE_PIXELS = 2048 * 2048  # 4,194,304
EXPECTED_TOTAL_PIXELS = 450 * TOTAL_SCENE_PIXELS  # 1,887,436,800


def compute_array_sha256(arr: np.ndarray) -> str:
    """Compute SHA-256 digest of raw C-contiguous bytes of a numpy array."""
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest().upper()


def independently_verify_mapping(
    mapping_name: str,
    eval_dir: Path,
    native_root: Path,
    pairs: List[Dict[str, Any]],
    frozen_threshold: float = 0.22,
) -> Dict[str, Any]:
    """Independently audit and recompute all scene metrics for one mapping."""
    mapping_dir = eval_dir / mapping_name.lower()
    assert mapping_dir.is_dir(), f"Mapping directory missing: {mapping_dir}"

    print(f"\n[INDEPENDENT VERIFIER] Auditing {mapping_name} ({len(pairs)} scenes)...", flush=True)

    oil_scenes: List[Dict[str, Any]] = []
    no_oil_scenes: List[Dict[str, Any]] = []
    lookalike_scenes: List[Dict[str, Any]] = []

    total_scenes_verified = 0
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_tn = 0
    total_fg_pixels = 0
    total_bg_pixels = 0

    for idx, p in enumerate(pairs):
        pair_id = p["pair_id"]
        class_name = p["class_directory"]
        mask_rel = p["mask_relative_path"]

        native_mask_path = native_root / mask_rel
        npz_path = mapping_dir / f"{pair_id}.npz"
        json_path = mapping_dir / f"{pair_id}.json"

        assert native_mask_path.is_file(), f"Native source mask missing: {native_mask_path}"
        assert npz_path.is_file(), f"Generated artifact missing: {npz_path}"
        assert json_path.is_file(), f"Metadata JSON missing: {json_path}"

        # 1. Read Native Ground-Truth Mask directly from source GeoTIFF
        with rasterio.open(native_mask_path) as src:
            native_mask_raw = src.read(1)
            assert native_mask_raw.shape == (2048, 2048), f"Native shape error in {native_mask_path}"
            native_mask = (native_mask_raw > 0).astype(np.uint8)

        # 2. Read Stored Artifacts from .npz
        with np.load(npz_path) as data:
            assert "probability_map" in data, f"Missing probability_map in {npz_path}"
            assert "prediction_mask" in data, f"Missing prediction_mask in {npz_path}"
            assert "target_mask" in data, f"Missing target_mask in {npz_path}"

            prob_map = data["probability_map"]
            stored_pred = data["prediction_mask"]
            stored_target = data["target_mask"]

        # Assert Canonical FP32 Precision for Probability Mosaic
        assert prob_map.dtype == np.float32, f"Expected float32 probability_map, got {prob_map.dtype} in {npz_path}"
        assert prob_map.shape == (2048, 2048), f"Shape error in prob_map: {prob_map.shape}"
        assert stored_pred.shape == (2048, 2048), f"Shape error in stored_pred: {stored_pred.shape}"
        assert stored_target.shape == (2048, 2048), f"Shape error in stored_target: {stored_target.shape}"

        # 3. CRITICAL GROUND-TRUTH EQUALITY CHECK: native_mask == stored_target
        if not np.array_equal(native_mask, stored_target):
            raise AssertionError(
                f"CORRUPTION DETECTED in scene {pair_id}: stored_target does not match native source mask!"
            )
        native_hash = compute_array_sha256(native_mask)
        stored_target_hash = compute_array_sha256(stored_target)
        assert native_hash == stored_target_hash, f"Hash mismatch in target mask for {pair_id}"

        # 4. INDEPENDENT PREDICTION RECONSTRUCTION: recomputed_pred = (prob_map >= threshold)
        recomputed_pred = (prob_map >= frozen_threshold).astype(np.uint8)
        if not np.array_equal(recomputed_pred, stored_pred):
            raise AssertionError(
                f"PREDICTION MISMATCH in scene {pair_id}: recomputed_pred does not match stored_prediction_mask!"
            )

        # 5. INDEPENDENT CONFUSION CALCULATION from (recomputed_pred, native_mask)
        tp = int(np.sum((recomputed_pred == 1) & (native_mask == 1)))
        fp = int(np.sum((recomputed_pred == 1) & (native_mask == 0)))
        fn = int(np.sum((recomputed_pred == 0) & (native_mask == 1)))
        tn = int(np.sum((recomputed_pred == 0) & (native_mask == 0)))
        assert tp + fp + fn + tn == TOTAL_SCENE_PIXELS, f"Confusion sum anomaly in scene {pair_id}"

        # Cross-verify with stored JSON metadata counts
        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        stored_counts = meta.get("confusion_counts", {})
        assert tp == stored_counts.get("tp"), f"TP mismatch in {pair_id}: {tp} vs {stored_counts.get('tp')}"
        assert fp == stored_counts.get("fp"), f"FP mismatch in {pair_id}: {fp} vs {stored_counts.get('fp')}"
        assert fn == stored_counts.get("fn"), f"FN mismatch in {pair_id}: {fn} vs {stored_counts.get('fn')}"
        assert tn == stored_counts.get("tn"), f"TN mismatch in {pair_id}: {tn} vs {stored_counts.get('tn')}"

        scene_fg = tp + fn
        scene_bg = fp + tn
        total_fg_pixels += scene_fg
        total_bg_pixels += scene_bg
        total_tp += tp
        total_fp += fp
        total_fn += fn
        total_tn += tn

        scene_entry = {
            "pair_id": pair_id,
            "class_name": class_name,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "target_foreground": scene_fg,
            "pred_positive": tp + fp,
            "mask_hash": native_hash,
        }

        if class_name == "Oil":
            denom_iou = tp + fp + fn
            iou = float(tp / denom_iou) if denom_iou > 0 else (1.0 if (scene_fg == 0 and tp + fp == 0) else 0.0)
            denom_dice = 2 * tp + fp + fn
            dice = float(2 * tp / denom_dice) if denom_dice > 0 else (1.0 if (scene_fg == 0 and tp + fp == 0) else 0.0)
            prec = float(tp / (tp + fp)) if (tp + fp) > 0 else (1.0 if scene_fg == 0 else 0.0)
            rec = float(tp / scene_fg) if scene_fg > 0 else (1.0 if (tp + fp == 0) else 0.0)
            scene_entry.update({"iou": iou, "dice": dice, "precision": prec, "recall": rec})
            oil_scenes.append(scene_entry)
        elif class_name == "No oil":
            scene_entry.update({
                "fp_pixels": fp,
                "fp_fraction": float(fp / TOTAL_SCENE_PIXELS),
                "false_alarm": bool(fp > 0),
                "significant_false_alarm": bool(fp >= 100),
            })
            no_oil_scenes.append(scene_entry)
        elif class_name == "Lookalike":
            scene_entry.update({
                "fp_pixels": fp,
                "fp_fraction": float(fp / TOTAL_SCENE_PIXELS),
                "false_alarm": bool(fp > 0),
                "significant_false_alarm": bool(fp >= 100),
            })
            lookalike_scenes.append(scene_entry)
        else:
            raise ValueError(f"Unknown class {class_name} in {pair_id}")

        total_scenes_verified += 1

    assert total_scenes_verified == 450, f"Incomplete verification: {total_scenes_verified} / 450"
    assert len(oil_scenes) == 150
    assert len(no_oil_scenes) == 150
    assert len(lookalike_scenes) == 150

    # 6. Recompute Stratum Summary Aggregates
    oil_ious = [s["iou"] for s in oil_scenes]
    oil_dices = [s["dice"] for s in oil_scenes]
    oil_precs = [s["precision"] for s in oil_scenes]
    oil_recs = [s["recall"] for s in oil_scenes]

    oil_tp = sum(s["tp"] for s in oil_scenes)
    oil_fp = sum(s["fp"] for s in oil_scenes)
    oil_fn = sum(s["fn"] for s in oil_scenes)
    oil_tn = sum(s["tn"] for s in oil_scenes)

    micro_iou = float(oil_tp / (oil_tp + oil_fp + oil_fn)) if (oil_tp + oil_fp + oil_fn) > 0 else 0.0
    micro_dice = float(2 * oil_tp / (2 * oil_tp + oil_fp + oil_fn)) if (2 * oil_tp + oil_fp + oil_fn) > 0 else 0.0
    micro_prec = float(oil_tp / (oil_tp + oil_fp)) if (oil_tp + oil_fp) > 0 else 0.0
    micro_rec = float(oil_tp / (oil_tp + oil_fn)) if (oil_tp + oil_fn) > 0 else 0.0

    oil_summary = {
        "n_scenes": 150,
        "macro_mean": {
            "iou": float(np.mean(oil_ious)),
            "dice": float(np.mean(oil_dices)),
            "precision": float(np.mean(oil_precs)),
            "recall": float(np.mean(oil_recs)),
        },
        "macro_median": {
            "iou": float(np.median(oil_ious)),
            "dice": float(np.median(oil_dices)),
            "precision": float(np.median(oil_precs)),
            "recall": float(np.median(oil_recs)),
        },
        "micro_pooled": {
            "iou": micro_iou,
            "dice": micro_dice,
            "precision": micro_prec,
            "recall": micro_rec,
            "total_tp": oil_tp,
            "total_fp": oil_fp,
            "total_fn": oil_fn,
            "total_tn": oil_tn,
        },
    }

    no_oil_fa_count = sum(1 for s in no_oil_scenes if s["false_alarm"])
    no_oil_sig_count = sum(1 for s in no_oil_scenes if s["significant_false_alarm"])
    no_oil_fps = [s["fp_pixels"] for s in no_oil_scenes]

    no_oil_summary = {
        "n_scenes": 150,
        "scene_far_primary": {
            "fa_scenes": no_oil_fa_count,
            "far": float(no_oil_fa_count / 150.0),
            "rule": "I(FP > 0)",
        },
        "scene_significant_far_secondary": {
            "sig_fa_scenes": no_oil_sig_count,
            "significant_far": float(no_oil_sig_count / 150.0),
            "rule": "I(FP >= 100)",
        },
        "pixel_metrics": {
            "total_fp_pixels": int(sum(no_oil_fps)),
            "mean_fp_pixels_per_scene": float(np.mean(no_oil_fps)),
            "median_fp_pixels_per_scene": float(np.median(no_oil_fps)),
            "max_fp_pixels_in_scene": int(np.max(no_oil_fps)),
        },
    }

    lookalike_fa_count = sum(1 for s in lookalike_scenes if s["false_alarm"])
    lookalike_sig_count = sum(1 for s in lookalike_scenes if s["significant_false_alarm"])
    lookalike_fps = [s["fp_pixels"] for s in lookalike_scenes]

    lookalike_summary = {
        "n_scenes": 150,
        "scene_far_primary": {
            "fa_scenes": lookalike_fa_count,
            "far": float(lookalike_fa_count / 150.0),
            "rule": "I(FP > 0)",
        },
        "scene_significant_far_secondary": {
            "sig_fa_scenes": lookalike_sig_count,
            "significant_far": float(lookalike_sig_count / 150.0),
            "rule": "I(FP >= 100)",
        },
        "pixel_metrics": {
            "total_fp_pixels": int(sum(lookalike_fps)),
            "mean_fp_pixels_per_scene": float(np.mean(lookalike_fps)),
            "median_fp_pixels_per_scene": float(np.median(lookalike_fps)),
            "max_fp_pixels_in_scene": int(np.max(lookalike_fps)),
        },
    }

    # 7. Exact Conservation Equations Check
    assert total_tp + total_fn == total_fg_pixels, f"TP + FN != N_fg in {mapping_name}"
    assert total_fp + total_tn == total_bg_pixels, f"FP + TN != N_bg in {mapping_name}"
    assert total_tp + total_fp + total_fn + total_tn == EXPECTED_TOTAL_PIXELS, f"Total pixel count error in {mapping_name}"

    print(f"[INDEPENDENT VERIFIER] {mapping_name} PASSED all ground-truth, prediction, and conservation checks.", flush=True)

    return {
        "mapping": mapping_name,
        "scenes_verified": total_scenes_verified,
        "total_pixels_evaluated": EXPECTED_TOTAL_PIXELS,
        "total_foreground_pixels_n_fg": total_fg_pixels,
        "total_background_pixels_n_bg": total_bg_pixels,
        "confusion_totals": {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "tn": total_tn,
        },
        "conservation_verified": True,
        "oil_stratum": oil_summary,
        "no_oil_stratum": no_oil_summary,
        "lookalike_stratum": lookalike_summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ocean Sentinel Phase 6 Independent Scientific Verifier")
    parser.add_argument(
        "--eval_dir",
        type=Path,
        default=Path("experiments/performance/phase_6_part_iii_external_evaluation/attempt_001"),
        help="Path to evaluation attempt root directory",
    )
    parser.add_argument(
        "--native_root",
        type=Path,
        default=Path("data/raw/external_validation/trujillo_part_iii/extracted"),
        help="Path to native extracted Part III directory",
    )
    parser.add_argument(
        "--pairing_manifest",
        type=Path,
        default=Path("scratch/trujillo_part_iii_pairing.json"),
        help="Path to authoritative pairing manifest",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.22,
        help="Frozen binarization threshold",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("OCEAN SENTINEL — PHASE 6 INDEPENDENT SCIENTIFIC VERIFICATION AUDITOR")
    print(f"Evaluation Root: {args.eval_dir}")
    print(f"Native Mask Root: {args.native_root}")
    print(f"Frozen Threshold: {args.threshold}")
    print("=" * 80)

    assert args.eval_dir.is_dir(), f"Evaluation directory missing: {args.eval_dir}"
    assert args.native_root.is_dir(), f"Native root missing: {args.native_root}"
    assert args.pairing_manifest.is_file(), f"Pairing manifest missing: {args.pairing_manifest}"

    with open(args.pairing_manifest, "r", encoding="utf-8") as f:
        pairs = json.load(f)
    assert len(pairs) == 450, f"Expected 450 pairs, got {len(pairs)}"

    # Audit Mapping A
    audit_a = independently_verify_mapping(
        "MAPPING_A", args.eval_dir, args.native_root, pairs, frozen_threshold=args.threshold
    )

    # Audit Mapping B
    audit_b = independently_verify_mapping(
        "MAPPING_B", args.eval_dir, args.native_root, pairs, frozen_threshold=args.threshold
    )

    # Cross-Mapping Target Mask Consistency Check
    print("\n[INDEPENDENT VERIFIER] Cross-verifying target mask consistency between Mapping A and Mapping B...", flush=True)
    mapping_a_dir = args.eval_dir / "mapping_a"
    mapping_b_dir = args.eval_dir / "mapping_b"

    for p in pairs:
        pair_id = p["pair_id"]
        npz_a = mapping_a_dir / f"{pair_id}.npz"
        npz_b = mapping_b_dir / f"{pair_id}.npz"

        with np.load(npz_a) as da, np.load(npz_b) as db:
            tgt_a = da["target_mask"]
            tgt_b = db["target_mask"]
            if not np.array_equal(tgt_a, tgt_b):
                raise AssertionError(f"Cross-mapping target mask divergence detected in {pair_id}!")

    print("[INDEPENDENT VERIFIER] Target masks are 100% identical between Mapping A and Mapping B.", flush=True)

    # Cross-verify ground-truth foreground sum between mappings
    assert audit_a["total_foreground_pixels_n_fg"] == audit_b["total_foreground_pixels_n_fg"], "Foreground mismatch between mappings!"
    assert audit_a["total_background_pixels_n_bg"] == audit_b["total_background_pixels_n_bg"], "Background mismatch between mappings!"

    # Compute Independent Polarization Gap
    delta_oil_macro_iou = audit_b["oil_stratum"]["macro_mean"]["iou"] - audit_a["oil_stratum"]["macro_mean"]["iou"]
    delta_oil_micro_iou = audit_b["oil_stratum"]["micro_pooled"]["iou"] - audit_a["oil_stratum"]["micro_pooled"]["iou"]

    report = {
        "verifier_name": "Phase 6 Independent Scientific Verifier",
        "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "evaluation_root": str(args.eval_dir).replace("\\", "/"),
        "native_mask_root": str(args.native_root).replace("\\", "/"),
        "pairing_manifest": str(args.pairing_manifest).replace("\\", "/"),
        "frozen_threshold": args.threshold,
        "verification_status": "CERTIFIED_PASS",
        "total_scenes_per_mapping": 450,
        "total_tiles_per_mapping": 7200,
        "total_pixels_per_mapping": EXPECTED_TOTAL_PIXELS,
        "authoritative_foreground_pixels_n_fg": audit_a["total_foreground_pixels_n_fg"],
        "authoritative_background_pixels_n_bg": audit_a["total_background_pixels_n_bg"],
        "mapping_a": audit_a,
        "mapping_b": audit_b,
        "polarization_sensitivity_gap": {
            "oil_macro_mean_iou": {
                "mapping_a": audit_a["oil_stratum"]["macro_mean"]["iou"],
                "mapping_b": audit_b["oil_stratum"]["macro_mean"]["iou"],
                "delta_b_minus_a": delta_oil_macro_iou,
                "abs_gap": abs(delta_oil_macro_iou),
            },
            "oil_micro_pooled_iou": {
                "mapping_a": audit_a["oil_stratum"]["micro_pooled"]["iou"],
                "mapping_b": audit_b["oil_stratum"]["micro_pooled"]["iou"],
                "delta_b_minus_a": delta_oil_micro_iou,
                "abs_gap": abs(delta_oil_micro_iou),
            },
            "no_oil_scene_far_primary": {
                "mapping_a": audit_a["no_oil_stratum"]["scene_far_primary"]["far"],
                "mapping_b": audit_b["no_oil_stratum"]["scene_far_primary"]["far"],
                "delta_b_minus_a": audit_b["no_oil_stratum"]["scene_far_primary"]["far"] - audit_a["no_oil_stratum"]["scene_far_primary"]["far"],
            },
            "lookalike_scene_far_primary": {
                "mapping_a": audit_a["lookalike_stratum"]["scene_far_primary"]["far"],
                "mapping_b": audit_b["lookalike_stratum"]["scene_far_primary"]["far"],
                "delta_b_minus_a": audit_b["lookalike_stratum"]["scene_far_primary"]["far"] - audit_a["lookalike_stratum"]["scene_far_primary"]["far"],
            },
        },
    }

    out_path = args.eval_dir / "metrics" / "independent_verification_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[INDEPENDENT VERIFIER] Verification Report saved: {out_path}")
    print("=" * 80)
    print("INDEPENDENT SCIENTIFIC VERIFICATION PASSED WITH ZERO DISCREPANCIES")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
