"""Segmentation Metrics for Ocean Sentinel SAR Oil-Spill Detection.

Implements:
1. Global and sample-level IoU (Jaccard Index).
2. Dice / F1 Score.
3. Precision and Recall.
4. SegmentationMeter: Streaming accumulator for dataset-level global metrics.

Conventions for Empty Ground Truth & Empty Prediction:
------------------------------------------------------
In SAR oil-spill surveillance, many tiles contain clean sea water (empty ground truth,
positive_pixels = 0). We define explicit, mathematically consistent conventions:

Case 1: Ground Truth is Empty (GT=0) AND Prediction is Empty (Pred=0):
    - Both ground truth and prediction agree there is zero oil spill (True Negative).
    - IoU = 1.0, Dice = 1.0, Precision = 1.0, Recall = 1.0.

Case 2: Ground Truth is Empty (GT=0) AND Prediction is Non-Empty (FP > 0):
    - False alarm over clean water.
    - IoU = 0.0, Dice = 0.0, Precision = 0.0, Recall = 0.0.

Case 3: Ground Truth is Non-Empty (GT > 0) AND Prediction is Empty (FN > 0, TP = 0):
    - Completely missed oil spill.
    - IoU = 0.0, Dice = 0.0, Precision = 0.0, Recall = 0.0.

Case 4: Ground Truth is Non-Empty (GT > 0) AND Prediction is Non-Empty:
    - Standard confusion matrix formulas:
      IoU = TP / (TP + FP + FN)
      Dice = 2 * TP / (2 * TP + FP + FN)
      Precision = TP / (TP + FP)
      Recall = TP / (TP + FN)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch


def compute_confusion_matrix_counts(
    logits_or_probs: torch.Tensor | np.ndarray,
    targets: torch.Tensor | np.ndarray,
    threshold: float = 0.50,
    is_logits: bool = True,
) -> tuple[int, int, int, int]:
    """Compute (TP, FP, FN, TN) count over tensors or numpy arrays.

    Parameters
    ----------
    logits_or_probs : torch.Tensor | np.ndarray
        Model output logits (if is_logits=True) or probabilities [0, 1].
    targets : torch.Tensor | np.ndarray
        Binary ground truth {0, 1}.
    threshold : float
        Binarization threshold (default 0.50).
    is_logits : bool
        Whether inputs are raw logits before sigmoid.

    Returns
    -------
    tuple[int, int, int, int]
        (tp, fp, fn, tn) as standard Python integers.
    """
    if isinstance(logits_or_probs, torch.Tensor):
        with torch.no_grad():
            if is_logits:
                probs = torch.sigmoid(logits_or_probs)
            else:
                probs = logits_or_probs
            pred_bin = (probs >= threshold).to(dtype=torch.bool)
            target_bin = (targets >= 0.5).to(dtype=torch.bool)

            tp = int(torch.sum(pred_bin & target_bin).item())
            fp = int(torch.sum(pred_bin & (~target_bin)).item())
            fn = int(torch.sum((~pred_bin) & target_bin).item())
            tn = int(torch.sum((~pred_bin) & (~target_bin)).item())
            return tp, fp, fn, tn
    else:
        arr_pred = np.asarray(logits_or_probs)
        arr_tgt = np.asarray(targets) >= 0.5
        if is_logits:
            probs = 1.0 / (1.0 + np.exp(-arr_pred))
        else:
            probs = arr_pred
        pred_bin = probs >= threshold

        tp = int(np.sum(pred_bin & arr_tgt))
        fp = int(np.sum(pred_bin & (~arr_tgt)))
        fn = int(np.sum((~pred_bin) & arr_tgt))
        tn = int(np.sum((~pred_bin) & (~arr_tgt)))
        return tp, fp, fn, tn


def compute_metrics_from_counts(tp: int, fp: int, fn: int, tn: int) -> dict[str, float]:
    """Compute IoU, Dice, Precision, Recall from confusion matrix totals."""
    # Case 1: Empty GT and Empty Prediction (clean water agreement)
    if (tp + fn == 0) and (tp + fp == 0):
        return {
            "iou": 1.0,
            "dice": 1.0,
            "precision": 1.0,
            "recall": 1.0,
            "tp": float(tp),
            "fp": float(fp),
            "fn": float(fn),
            "tn": float(tn),
        }

    # Case 2: Empty GT with false alarms (FP > 0)
    if tp + fn == 0 and fp > 0:
        return {
            "iou": 0.0,
            "dice": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "tp": float(tp),
            "fp": float(fp),
            "fn": float(fn),
            "tn": float(tn),
        }

    # Case 3 & 4: Non-empty GT
    denom_iou = tp + fp + fn
    denom_dice = 2 * tp + fp + fn
    denom_prec = tp + fp
    denom_rec = tp + fn

    iou = float(tp / denom_iou) if denom_iou > 0 else 0.0
    dice = float((2.0 * tp) / denom_dice) if denom_dice > 0 else 0.0
    precision = float(tp / denom_prec) if denom_prec > 0 else 0.0
    recall = float(tp / denom_rec) if denom_rec > 0 else 0.0

    return {
        "iou": iou,
        "dice": dice,
        "precision": precision,
        "recall": recall,
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "tn": float(tn),
    }


def compute_batch_metrics(
    logits: torch.Tensor,
    targets: torch.Tensor,
    threshold: float = 0.50,
) -> dict[str, float]:
    """Compute pooled batch metrics over logits and binary targets."""
    tp, fp, fn, tn = compute_confusion_matrix_counts(
        logits, targets, threshold=threshold, is_logits=True
    )
    return compute_metrics_from_counts(tp, fp, fn, tn)


class SegmentationMeter:
    """Streaming accumulator for dataset-level global metrics.

    Accumulates total TP, FP, FN, TN over all batches/tiles in a split,
    avoiding sample-averaging bias on empty tiles.

    Parameters
    ----------
    threshold : float
        Binarization threshold applied to logits via sigmoid (default 0.50).
    """

    def __init__(self, threshold: float = 0.50) -> None:
        self.threshold = threshold
        self.reset()

    def reset(self) -> None:
        """Reset all accumulators to zero."""
        self.tp: int = 0
        self.fp: int = 0
        self.fn: int = 0
        self.tn: int = 0
        self.n_samples: int = 0

    def update(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
    ) -> None:
        """Accumulate counts from a batch of logits and targets."""
        batch_size = logits.shape[0]
        self.n_samples += batch_size
        tp, fp, fn, tn = compute_confusion_matrix_counts(
            logits, targets, threshold=self.threshold, is_logits=True
        )
        self.tp += tp
        self.fp += fp
        self.fn += fn
        self.tn += tn

    def compute(self) -> dict[str, Any]:
        """Compute pooled global metrics over all accumulated samples."""
        res = compute_metrics_from_counts(self.tp, self.fp, self.fn, self.tn)
        res["n_samples"] = self.n_samples
        res["threshold"] = self.threshold
        return res
