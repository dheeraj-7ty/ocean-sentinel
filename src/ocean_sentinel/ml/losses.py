"""Loss Functions for Ocean Sentinel SAR Oil-Spill Segmentation.

Implements:
1. SoftDiceLoss: Numerically stable soft Dice loss operating directly on logits.
2. CombinedBCEAndDiceLoss: Primary baseline loss (0.5 * BCEWithLogits + 0.5 * SoftDice).
3. FocalTverskyLoss: Secondary ablation loss (alpha=0.3, beta=0.7, gamma=4/3).

Mathematical and Engineering Considerations:
- Logits contract: Predictions are assumed to be raw logits. Sigmoid is computed
  internally in a numerically safe manner.
- Binary masks: Targets must be float32 in {0.0, 1.0} with shape [B, 1, H, W] or [B, H, W].
- Smoothing epsilon: Configurable epsilon (default 1e-6) prevents division by zero.
- Empty mask handling: When ground truth is empty and prediction is all negative
  (sigmoid ≈ 0), Soft Dice numerator is epsilon and denominator is epsilon, yielding
  Dice = 1.0, Loss = 0.0.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class SoftDiceLoss(nn.Module):
    """Soft Dice Loss operating on logits for binary segmentation.

    Formulation:
        p = sigmoid(logits)
        intersection = sum(p * targets)
        denominator = sum(p) + sum(targets)
        dice = (2 * intersection + smooth) / (denominator + smooth)
        loss = 1.0 - dice

    Parameters
    ----------
    smooth : float
        Laplace smoothing term (default 1.0, standard for pixel-count scale).
    square_denominator : bool
        If True, denominator is sum(p^2) + sum(y^2). Default is False (linear sum).
    reduction : str
        "mean" (batch-averaged loss) or "none". Default "mean".
    """

    def __init__(
        self,
        smooth: float = 1.0,
        square_denominator: bool = False,
        reduction: str = "mean",
    ) -> None:
        super().__init__()
        self.smooth = smooth
        self.square_denominator = square_denominator
        self.reduction = reduction

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """Compute Soft Dice Loss.

        Parameters
        ----------
        logits : torch.Tensor
            Raw prediction logits [B, 1, H, W] or [B, H, W].
        targets : torch.Tensor
            Binary ground truth [B, 1, H, W] or [B, H, W], values in {0, 1}.

        Returns
        -------
        torch.Tensor
            Scalar loss (if reduction="mean") or per-sample loss [B].
        """
        if logits.shape != targets.shape:
            # Squeeze or unsqueeze single channel if needed
            if logits.dim() == 4 and targets.dim() == 3:
                targets = targets.unsqueeze(1)
            elif logits.dim() == 3 and targets.dim() == 4:
                logits = logits.unsqueeze(1)
            else:
                msg = (
                    f"Shape mismatch: logits {tuple(logits.shape)} "
                    f"vs targets {tuple(targets.shape)}"
                )
                raise ValueError(msg)

        # Probabilities via numerically safe sigmoid
        probs = torch.sigmoid(logits)

        # Flatten per batch sample: [B, N]
        b = probs.shape[0]
        probs_flat = probs.view(b, -1)
        targets_flat = targets.view(b, -1).to(dtype=probs.dtype)

        intersection = torch.sum(probs_flat * targets_flat, dim=-1)

        if self.square_denominator:
            denominator = (
                torch.sum(probs_flat.pow(2), dim=-1)
                + torch.sum(targets_flat.pow(2), dim=-1)
            )
        else:
            denominator = torch.sum(probs_flat, dim=-1) + torch.sum(targets_flat, dim=-1)

        dice = (2.0 * intersection + self.smooth) / (denominator + self.smooth)
        loss = 1.0 - dice

        if self.reduction == "mean":
            return loss.mean()
        elif self.reduction == "none":
            return loss
        else:
            raise ValueError(f"Unknown reduction: {self.reduction}")


class CombinedBCEAndDiceLoss(nn.Module):
    """Primary baseline segmentation loss: 0.5 * BCEWithLogits + 0.5 * SoftDice.

    Parameters
    ----------
    bce_weight : float
        Weight for binary cross-entropy loss (default 0.5).
    dice_weight : float
        Weight for soft Dice loss (default 0.5).
    smooth : float
        Smoothing factor for SoftDice (default 1e-6).
    pos_weight : float | None
        Optional positive class weighting for BCE to handle extreme class imbalance.
    """

    def __init__(
        self,
        bce_weight: float = 0.5,
        dice_weight: float = 0.5,
        smooth: float = 1.0,
        pos_weight: float | None = None,
    ) -> None:
        super().__init__()
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight
        pos_weight_tensor = torch.tensor([pos_weight]) if pos_weight is not None else None
        self.bce = nn.BCEWithLogitsLoss(pos_weight=pos_weight_tensor)
        self.dice = SoftDiceLoss(smooth=smooth)

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """Compute weighted BCE and Soft Dice loss."""
        if logits.shape != targets.shape:
            if logits.dim() == 4 and targets.dim() == 3:
                targets = targets.unsqueeze(1)
            elif logits.dim() == 3 and targets.dim() == 4:
                logits = logits.unsqueeze(1)

        targets = targets.to(dtype=logits.dtype)
        bce_loss = self.bce(logits, targets)
        dice_loss = self.dice(logits, targets)

        return self.bce_weight * bce_loss + self.dice_weight * dice_loss


class FocalTverskyLoss(nn.Module):
    """Focal Tversky Loss for segmentation under severe class imbalance (EXP-02 ablation).

    Formulation:
        p = sigmoid(logits)
        TI = (TP + smooth) / (TP + alpha * FP + beta * FN + smooth)
        loss = (1 - TI) ** gamma

    Approved baseline parameters:
        alpha = 0.3 (weight on false positives)
        beta  = 0.7 (weight on false negatives — prioritizes oil spill recall)
        gamma = 4/3 ≈ 1.3333 (focusing parameter)
    """

    def __init__(
        self,
        alpha: float = 0.3,
        beta: float = 0.7,
        gamma: float = 4.0 / 3.0,
        smooth: float = 1.0,
        reduction: str = "mean",
    ) -> None:
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.smooth = smooth
        self.reduction = reduction

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if logits.shape != targets.shape:
            if logits.dim() == 4 and targets.dim() == 3:
                targets = targets.unsqueeze(1)
            elif logits.dim() == 3 and targets.dim() == 4:
                logits = logits.unsqueeze(1)

        probs = torch.sigmoid(logits)
        b = probs.shape[0]
        p_flat = probs.view(b, -1)
        t_flat = targets.view(b, -1).to(dtype=probs.dtype)

        tp = torch.sum(p_flat * t_flat, dim=-1)
        fp = torch.sum(p_flat * (1.0 - t_flat), dim=-1)
        fn = torch.sum((1.0 - p_flat) * t_flat, dim=-1)

        tversky = (tp + self.smooth) / (tp + self.alpha * fp + self.beta * fn + self.smooth)
        loss = torch.pow(1.0 - tversky, self.gamma)

        if self.reduction == "mean":
            return loss.mean()
        elif self.reduction == "none":
            return loss
        else:
            raise ValueError(f"Unknown reduction: {self.reduction}")
