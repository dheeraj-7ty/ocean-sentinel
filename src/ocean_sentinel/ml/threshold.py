"""Validation-Only Threshold Selection for Ocean Sentinel Oil-Spill Detection.

Enforces strict CAO requirements:
1. Validation set ONLY — test set must NEVER participate in threshold tuning.
2. Single-pass evaluation: Runs the model once across the validation split to extract
   probabilities, evaluating confusion counts across the threshold search grid in memory.
3. Explicit target metric controls the decision (default: "iou").
4. Deterministic and fully reproducible.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ocean_sentinel.ml.metrics import compute_metrics_from_counts


@dataclass(frozen=True)
class ThresholdOptimizationResult:
    """Immutable result of validation threshold grid search."""

    best_threshold: float
    best_score: float
    target_metric: str
    grid: list[float]
    scores: dict[str, dict[str, float]]  # stringified threshold -> metric dictionary
    n_validation_samples: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def generate_default_threshold_grid(
    start: float = 0.10,
    stop: float = 0.90,
    step: float = 0.02,
) -> list[float]:
    """Generate default engineering grid: 0.10 to 0.90 with step 0.02 (41 points)."""
    n_points = int(round((stop - start) / step)) + 1
    # Round to 4 decimal places to prevent floating point inaccuracy
    return [round(start + i * step, 4) for i in range(n_points)]


def optimize_threshold_on_validation(
    model: nn.Module,
    val_loader: DataLoader,
    device: torch.device | str = "cuda" if torch.cuda.is_available() else "cpu",
    thresholds: Sequence[float] | None = None,
    target_metric: str = "iou",
    use_amp: bool = False,
) -> ThresholdOptimizationResult:
    """Find the optimal classification threshold using validation data only.

    Parameters
    ----------
    model : nn.Module
        Trained or checkpointed model returning raw logits.
    val_loader : DataLoader
        DataLoader exposing the VALIDATION split only.
    device : torch.device | str
        Execution device.
    thresholds : Sequence[float] | None
        Candidate threshold grid. If None, defaults to 0.10-0.90 step 0.02.
    target_metric : str
        Metric used to select the optimal threshold: "iou" (default), "dice",
        "precision", or "recall".
    use_amp : bool
        Whether to use torch.autocast for evaluation.

    Returns
    -------
    ThresholdOptimizationResult
        Complete search results with best threshold and full score table.
    """
    if thresholds is None:
        thresholds = generate_default_threshold_grid()

    grid = sorted([round(float(t), 4) for t in thresholds])
    if not grid:
        raise ValueError("Threshold grid cannot be empty.")

    target_metric = target_metric.lower()
    valid_metrics = {"iou", "dice", "precision", "recall"}
    if target_metric not in valid_metrics:
        msg = f"Invalid target metric '{target_metric}', expected one of {valid_metrics}"
        raise ValueError(msg)

    model.eval()
    dev = torch.device(device)
    model.to(dev)

    # Initialize accumulators for each candidate threshold
    tp_counts = {t: 0 for t in grid}
    fp_counts = {t: 0 for t in grid}
    fn_counts = {t: 0 for t in grid}
    tn_counts = {t: 0 for t in grid}
    total_samples = 0

    amp_dtype = torch.float16 if dev.type == "cuda" else torch.bfloat16

    with torch.no_grad():
        for images, targets in val_loader:
            b = images.shape[0]
            total_samples += b

            images = images.to(dev, non_blocking=True)
            targets = targets.to(dev, non_blocking=True)
            target_bin = (targets >= 0.5)

            if use_amp and dev.type == "cuda":
                with torch.autocast(device_type="cuda", dtype=amp_dtype):
                    logits = model(images)
            else:
                logits = model(images)

            probs = torch.sigmoid(logits)

            # Evaluate each threshold against the batch
            for t in grid:
                pred_bin = (probs >= t)
                tp = int(torch.sum(pred_bin & target_bin).item())
                fp = int(torch.sum(pred_bin & (~target_bin)).item())
                fn = int(torch.sum((~pred_bin) & target_bin).item())
                tn = int(torch.sum((~pred_bin) & (~target_bin)).item())

                tp_counts[t] += tp
                fp_counts[t] += fp
                fn_counts[t] += fn
                tn_counts[t] += tn

    # Compute metrics for each threshold
    all_scores: dict[str, dict[str, float]] = {}
    best_threshold = grid[0]
    best_score = -1.0

    for t in grid:
        metrics = compute_metrics_from_counts(
            tp=tp_counts[t],
            fp=fp_counts[t],
            fn=fn_counts[t],
            tn=tn_counts[t],
        )
        t_key = f"{t:.4f}"
        all_scores[t_key] = metrics

        score = metrics[target_metric]
        if score > best_score:
            best_score = score
            best_threshold = t

    return ThresholdOptimizationResult(
        best_threshold=best_threshold,
        best_score=best_score,
        target_metric=target_metric,
        grid=grid,
        scores=all_scores,
        n_validation_samples=total_samples,
    )
