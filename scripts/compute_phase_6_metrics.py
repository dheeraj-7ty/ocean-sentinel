"""Phase 6: Benchmark Metric Computation and Polarization Sensitivity Aggregator.

Authority: Ocean Sentinel Phase 6 Official Benchmark Execution Agent
Execution Class: Stratified External Benchmark Metrics

Invariants:
- Frozen threshold = 0.22 on probability domain.
- Frozen normalization: spatial_split_manifest.json parameters.
- Stratified evaluation across Oil (150), No oil (150), Lookalike (150).
- Candidate C whole-scene reconstructed continuous probability mosaic (2048x2048).
- Polarization sensitivity comparison side-by-side (Mapping A vs Mapping B).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

RUN_ID = "phase_6_part_iii_external_evaluation"
ATTEMPT_ID = "attempt_001"
OUTPUT_DIR = REPO_ROOT / "experiments/performance" / RUN_ID / ATTEMPT_ID

CHECKPOINT_PATH = REPO_ROOT / "experiments/performance/exp06_positive_bce_weight/best_model.pt"
EXPECTED_CHECKPOINT_HASH = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
EXPECTED_CHECKPOINT_SIZE = 292461395

MANIFEST_PATH = REPO_ROOT / "scratch/trujillo_part_iii_pairing.json"
EXTRACTED_ROOT = REPO_ROOT / "data/raw/external_validation/trujillo_part_iii/extracted"
TOTAL_SCENE_PIXELS = 2048 * 2048  # 4,194,304


def compute_stratum_metrics_for_mapping(mapping_name: str) -> Dict[str, Any]:
    m_dir = OUTPUT_DIR / mapping_name.lower()
    assert m_dir.is_dir(), f"Missing mapping directory: {m_dir}"

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    oil_scenes: List[Dict[str, Any]] = []
    no_oil_scenes: List[Dict[str, Any]] = []
    lookalike_scenes: List[Dict[str, Any]] = []

    for p in pairs:
        pair_id = p["pair_id"]
        class_name = p["class_directory"]
        json_f = m_dir / f"{pair_id}.json"
        assert json_f.is_file(), f"Missing json: {json_f}"

        with open(json_f, "r", encoding="utf-8") as f:
            meta = json.load(f)

        counts = meta["confusion_counts"]
        tp = counts["tp"]
        fp = counts["fp"]
        fn = counts["fn"]
        tn = counts["tn"]
        assert tp + fp + fn + tn == TOTAL_SCENE_PIXELS

        scene_rec = {
            "pair_id": pair_id,
            "class_name": class_name,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "pred_positive": tp + fp,
            "target_positive": tp + fn,
        }

        if class_name == "Oil":
            denom_iou = tp + fp + fn
            iou = (tp / denom_iou) if denom_iou > 0 else (1.0 if (tp + fn == 0 and tp + fp == 0) else 0.0)
            denom_dice = 2 * tp + fp + fn
            dice = (2 * tp / denom_dice) if denom_dice > 0 else (1.0 if (tp + fn == 0 and tp + fp == 0) else 0.0)
            denom_prec = tp + fp
            prec = (tp / denom_prec) if denom_prec > 0 else (1.0 if (tp + fn == 0) else 0.0)
            denom_rec = tp + fn
            rec = (tp / denom_rec) if denom_rec > 0 else (1.0 if (tp + fp == 0) else 0.0)

            scene_rec.update({
                "iou": float(iou),
                "dice": float(dice),
                "precision": float(prec),
                "recall": float(rec),
            })
            oil_scenes.append(scene_rec)
        elif class_name == "No oil":
            scene_rec.update({
                "fp_pixels": fp,
                "fp_fraction": float(fp / TOTAL_SCENE_PIXELS),
                "false_alarm": bool(fp > 0),
                "significant_false_alarm": bool(fp >= 100),
            })
            no_oil_scenes.append(scene_rec)
        elif class_name == "Lookalike":
            scene_rec.update({
                "fp_pixels": fp,
                "fp_fraction": float(fp / TOTAL_SCENE_PIXELS),
                "false_alarm": bool(fp > 0),
                "significant_false_alarm": bool(fp >= 100),
            })
            lookalike_scenes.append(scene_rec)

    assert len(oil_scenes) == 150
    assert len(no_oil_scenes) == 150
    assert len(lookalike_scenes) == 150

    # Oil Stratum Aggregates
    oil_ious = [s["iou"] for s in oil_scenes]
    oil_dices = [s["dice"] for s in oil_scenes]
    oil_precs = [s["precision"] for s in oil_scenes]
    oil_recs = [s["recall"] for s in oil_scenes]

    total_tp = sum(s["tp"] for s in oil_scenes)
    total_fp = sum(s["fp"] for s in oil_scenes)
    total_fn = sum(s["fn"] for s in oil_scenes)
    total_tn = sum(s["tn"] for s in oil_scenes)

    micro_iou = float(total_tp / (total_tp + total_fp + total_fn)) if (total_tp + total_fp + total_fn) > 0 else 0.0
    micro_dice = float(2 * total_tp / (2 * total_tp + total_fp + total_fn)) if (2 * total_tp + total_fp + total_fn) > 0 else 0.0
    micro_prec = float(total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 0.0
    micro_rec = float(total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else 0.0

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
            "total_tp": total_tp,
            "total_fp": total_fp,
            "total_fn": total_fn,
            "total_tn": total_tn,
        },
    }

    # No-Oil Stratum Aggregates
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

    # Lookalike Stratum Aggregates
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

    return {
        "mapping": mapping_name,
        "run_id": RUN_ID,
        "attempt_id": ATTEMPT_ID,
        "checkpoint_sha256": EXPECTED_CHECKPOINT_HASH,
        "oil_stratum": oil_summary,
        "no_oil_stratum": no_oil_summary,
        "lookalike_stratum": lookalike_summary,
    }


def main() -> int:
    print("=" * 80)
    print("PHASE 6: COMPUTING STRATIFIED EXTERNAL BENCHMARK METRICS")
    print("=" * 80)

    metrics_dir = OUTPUT_DIR / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    res_a = compute_stratum_metrics_for_mapping("MAPPING_A")
    out_a = metrics_dir / "metrics_mapping_a.json"
    with open(out_a, "w", encoding="utf-8") as f:
        json.dump(res_a, f, indent=2)
    print(f"[METRICS] Saved: {out_a}")

    res_b = compute_stratum_metrics_for_mapping("MAPPING_B")
    out_b = metrics_dir / "metrics_mapping_b.json"
    with open(out_b, "w", encoding="utf-8") as f:
        json.dump(res_b, f, indent=2)
    print(f"[METRICS] Saved: {out_b}")

    delta_macro_iou = res_b["oil_stratum"]["macro_mean"]["iou"] - res_a["oil_stratum"]["macro_mean"]["iou"]
    delta_micro_iou = res_b["oil_stratum"]["micro_pooled"]["iou"] - res_a["oil_stratum"]["micro_pooled"]["iou"]

    comparison = {
        "benchmark_dataset": "Trujillo Part III External Benchmark",
        "checkpoint_path": str(CHECKPOINT_PATH).replace("\\", "/"),
        "checkpoint_sha256": EXPECTED_CHECKPOINT_HASH,
        "computed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "oil_stratum_comparison": {
            "macro_mean_iou": {
                "MAPPING_A": res_a["oil_stratum"]["macro_mean"]["iou"],
                "MAPPING_B": res_b["oil_stratum"]["macro_mean"]["iou"],
                "delta_b_minus_a": delta_macro_iou,
                "abs_gap": abs(delta_macro_iou),
            },
            "micro_pooled_iou": {
                "MAPPING_A": res_a["oil_stratum"]["micro_pooled"]["iou"],
                "MAPPING_B": res_b["oil_stratum"]["micro_pooled"]["iou"],
                "delta_b_minus_a": delta_micro_iou,
                "abs_gap": abs(delta_micro_iou),
            },
        },
        "no_oil_stratum_comparison": {
            "scene_far_primary": {
                "MAPPING_A": res_a["no_oil_stratum"]["scene_far_primary"]["far"],
                "MAPPING_B": res_b["no_oil_stratum"]["scene_far_primary"]["far"],
                "delta_b_minus_a": res_b["no_oil_stratum"]["scene_far_primary"]["far"] - res_a["no_oil_stratum"]["scene_far_primary"]["far"],
            },
            "significant_far_secondary": {
                "MAPPING_A": res_a["no_oil_stratum"]["scene_significant_far_secondary"]["significant_far"],
                "MAPPING_B": res_b["no_oil_stratum"]["scene_significant_far_secondary"]["significant_far"],
            },
        },
        "lookalike_stratum_comparison": {
            "scene_far_primary": {
                "MAPPING_A": res_a["lookalike_stratum"]["scene_far_primary"]["far"],
                "MAPPING_B": res_b["lookalike_stratum"]["scene_far_primary"]["far"],
                "delta_b_minus_a": res_b["lookalike_stratum"]["scene_far_primary"]["far"] - res_a["lookalike_stratum"]["scene_far_primary"]["far"],
            },
            "significant_far_secondary": {
                "MAPPING_A": res_a["lookalike_stratum"]["scene_significant_far_secondary"]["significant_far"],
                "MAPPING_B": res_b["lookalike_stratum"]["scene_significant_far_secondary"]["significant_far"],
            },
        },
    }

    comp_out = metrics_dir / "comparison_summary.json"
    with open(comp_out, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)
    print(f"[METRICS] Saved: {comp_out}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
