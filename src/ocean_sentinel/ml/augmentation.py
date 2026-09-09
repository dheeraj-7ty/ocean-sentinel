"""Physically Defensible SAR Augmentations for Ocean Sentinel.

Implements discrete geometric transformations appropriate for SAR backscatter:
1. Horizontal reflection (p_hflip).
2. Vertical reflection (p_vflip).
3. Discrete orthogonal 90° rotation (0°, 90°, 180°, 270°).

Guarantees:
- Identical geometric transformation applied simultaneously to image and mask.
- Discrete array indexing / axis flipping: ZERO spatial interpolation or resampling artifacts.
- Masks remain strictly binary {0.0, 1.0}.
- Both SAR polarization channels transformed synchronously.
- Fully deterministic mode available via explicit seed or random generator.
- Absolutely NO optical color jitter, arbitrary sub-pixel blur, or unapproved photometric
  modifications.
"""

from __future__ import annotations

import random
from typing import Tuple

import torch


class SARGeometricAugmentation:
    """Discrete geometric augmentations for 2-channel SAR tiles and binary masks.

    Parameters
    ----------
    p_hflip : float
        Probability of horizontal flip (default 0.50).
    p_vflip : float
        Probability of vertical flip (default 0.50).
    p_rot90 : float
        Probability of applying a random discrete 90° rotation (default 0.50).
    seed : int | None
        Optional random seed for deterministic augmentation (e.g. testing).
    """

    def __init__(
        self,
        p_hflip: float = 0.50,
        p_vflip: float = 0.50,
        p_rot90: float = 0.50,
        seed: int | None = None,
    ) -> None:
        self.p_hflip = p_hflip
        self.p_vflip = p_vflip
        self.p_rot90 = p_rot90
        self._rng = random.Random(seed) if seed is not None else random

    def seed(self, seed: int) -> None:
        """Set seed for deterministic execution."""
        self._rng = random.Random(seed)

    def __call__(
        self,
        image: torch.Tensor,
        mask: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Apply transforms to image [C, H, W] and mask [1, H, W] or [H, W].

        Parameters
        ----------
        image : torch.Tensor
            SAR image tensor [2, H, W] or [B, 2, H, W].
        mask : torch.Tensor
            Binary mask tensor [1, H, W] or [H, W] or [B, 1, H, W].

        Returns
        -------
        Tuple[torch.Tensor, torch.Tensor]
            Augmented (image, mask) pair with identical shapes and dtypes.
        """
        out_img = image
        out_mask = mask

        # Horizontal flip
        if self._rng.random() < self.p_hflip:
            out_img = torch.flip(out_img, dims=[-1])
            out_mask = torch.flip(out_mask, dims=[-1])

        # Vertical flip
        if self._rng.random() < self.p_vflip:
            out_img = torch.flip(out_img, dims=[-2])
            out_mask = torch.flip(out_mask, dims=[-2])

        # Discrete 90° rotation
        if self._rng.random() < self.p_rot90:
            k = self._rng.choice([1, 2, 3])  # 90°, 180°, or 270°
            out_img = torch.rot90(out_img, k=k, dims=[-2, -1])
            out_mask = torch.rot90(out_mask, k=k, dims=[-2, -1])

        return out_img, out_mask


class IdentityTransform:
    """No-op transform for validation and test splits (guarantees raw evaluation)."""

    def __call__(
        self,
        image: torch.Tensor,
        mask: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        return image, mask
