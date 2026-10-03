"""EXP-07 Authoritative Reference Implementation and Mathematical Contracts.

Phase: EXP-07-P0-C5
Domain: Multiclass Semantic Segmentation on OPS-01 SAR Imagery
Dataset: 147 physical tiles / 27 parent scenes (72 TRAIN / 39 DEV / 36 HOLDOUT)
Input: [B, 1, 256, 256] float32 (Sentinel-1 Level-1 GRD VV channel)
Output: [B, 12, 256, 256] float32 logits (no activation in head)
Architecture: ResNet18-UNet (14,310,860 trainable parameters, Option B BatchNorm baseline)
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import rasterio

# Optional PyTorch import with graceful fallback
try:
    import torch
    import torch.nn as nn
    from torchvision.models import resnet18, ResNet18_Weights
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    resnet18 = None
    ResNet18_Weights = None
    TORCH_AVAILABLE = False


# ==============================================================================
# 1. Authoritative Constants and Taxonomy
# ==============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OPS01_MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "ops01_physical_dataset_manifest_v4.json"
OPS01_TAXONOMY_PATH = REPO_ROOT / "data" / "metadata" / "ops01_taxonomy_v1.json"

# Normalization constants derived strictly from TRAIN split valid pixels (0 DEV/HOLDOUT leakage)
TRAIN_LOG1P_MEAN = 4.2756
TRAIN_LOG1P_STD = 0.3866

# Canonical dense class ordering (0..11)
DENSE_CLASSES = [
    "BG",    # 0: Background Seawater (source 0)
    "AF",    # 1: Atmospheric Front (source 1)
    "BS",    # 2: Biological Slicks (source 2)
    "LWA",   # 3: Low Wind Area (source 4)
    "MCC",   # 4: Mesoscale Cellular Convection (source 5)
    "OF",    # 5: Ocean Front (source 6)
    "POW",   # 6: Pure Ocean Wave (source 7)
    "RF",    # 7: Rain Cell / Rain Footprint (source 8)
    "WS",    # 8: Wind Streak (source 10)
    "Eddy",  # 9: Oceanic Eddy (source 11)
    "IWs",   # 10: Internal Waves (source 12)
    "HM",    # 11: Artificial / Anthropogenic Objects (source 13)
]

DENSE_CLASS_NAMES = DENSE_CLASSES

# Source label ID to dense class index (12 eligible classes)
# Excluded classes: 3 (IB), 9 (SI), 14 (OS) mapped to ignore_index (-100)
SOURCE_LABEL_TO_DENSE = {
    0: 0,
    1: 1,
    2: 2,
    4: 3,
    5: 4,
    6: 5,
    7: 6,
    8: 7,
    10: 8,
    11: 9,
    12: 10,
    13: 11,
}

IGNORE_INDEX = -100

# Square-root median-frequency class weights (computed strictly on TRAIN valid pixels)
# Source-recalculated in Phase C8 across all 4,712,082 valid pixels (DN > 0)
CLASS_WEIGHTS_SQRT_MEDIAN = {
    0: 0.273233,   # BG (Background Seawater, 1,950,756 valid pixels)
    1: 2.013263,   # AF (Atmospheric Front, 35,931 valid pixels)
    2: 0.703954,   # BS (Biological Slicks, 293,888 valid pixels)
    3: 2.493473,   # LWA (Low Wind Area, 23,424 valid pixels)
    4: 0.515947,   # MCC (Mesoscale Cellular Convection, 547,092 valid pixels)
    5: 1.469686,   # OF (Ocean Front, 67,425 valid pixels)
    6: 0.512411,   # POW (Pure Ocean Wave, 554,669 valid pixels)
    7: 1.510850,   # RF (Rain Cell / Rain Footprint, 63,801 valid pixels)
    8: 0.806601,   # WS (Wind Streak, 223,848 valid pixels)
    9: 2.066304,   # Eddy (Oceanic Eddy, 34,110 valid pixels)
    10: 0.398704,  # IWs (Internal Waves, 916,153 valid pixels)
    11: 12.159536, # HM (Artificial / Anthropogenic Objects, 985 valid pixels)
}


# ==============================================================================
# 2. Mathematical Preprocessing Pipeline
# ==============================================================================

def compute_validity_mask(raw_image: np.ndarray) -> np.ndarray:
    """Compute validity mask from raw SAR image array.
    
    Zero values correspond strictly to left-swath border padding (nodata: 0.0).
    Valid data is strictly > 0.
    """
    return (raw_image > 0).astype(bool)


def preprocess_sar_image(
    raw_image: np.ndarray,
    mean: float = TRAIN_LOG1P_MEAN,
    std: float = TRAIN_LOG1P_STD,
) -> Tuple[np.ndarray, np.ndarray]:
    """Execute the canonical EXP-07 input processing and normalization pipeline.
    
    Input Domain Specification (GOV-RULE-060):
    Input consists of aggregated raw Sentinel-1 Level-1 GRD detected pixel DN values (uncalibrated).
    Model operates in the log1p-transformed standardized DN domain, NOT physical backscatter (sigma0/gamma0).
    
    Pipeline sequence:
    1. Read raw aggregated DN input [1, 256, 256] float32
    2. Compute validity mask: validity_mask = raw_image > 0
    3. Compute log1p transform: log(1 + raw_image)
    4. Standardize using fixed TRAIN statistics: (log1p - mean) / std
    5. Mask invalid pixels to 0.0 in model input
    
    Returns
    -------
    normalized_image : np.ndarray
        Standardized image of shape [1, 256, 256] float32 with invalid pixels zeroed.
    validity_mask : np.ndarray
        Boolean array of shape [1, 256, 256] True for valid data, False for border padding.
    """
    if raw_image.ndim == 2:
        raw_image = raw_image[np.newaxis, :, :]
    elif raw_image.ndim != 3 or raw_image.shape[0] != 1:
        raise ValueError(f"Expected 1-channel image [1, H, W], got shape {raw_image.shape}")
        
    validity_mask = compute_validity_mask(raw_image)
    
    # Radiometric Log1p transform
    log1p_img = np.log1p(np.maximum(raw_image, 0.0, dtype=np.float32))
    
    # TRAIN-derived standardization
    standardized = (log1p_img - mean) / std
    
    # Zero-out invalid border padding in model input
    standardized[~validity_mask] = 0.0
    
    return standardized.astype(np.float32), validity_mask


# All 15 canonical source classes defined in ops01_taxonomy_v1.json (0..14)
KNOWN_SOURCE_LABELS = set(range(15))


def remap_source_mask_to_dense(
    source_mask: np.ndarray,
    validity_mask: Optional[np.ndarray] = None,
    ignore_index: int = IGNORE_INDEX,
) -> np.ndarray:
    """Remap 15-class source annotation mask to 12 dense training classes.
    
    - Eligible classes (0, 1, 2, 4, 5, 6, 7, 8, 10, 11, 12, 13) -> 0..11
    - Excluded classes (3: Iceberg, 9: Sea Ice, 14: Mineral Oil Spill) -> ignore_index (-100)
    - Border padding pixels (validity_mask == False) -> ignore_index (-100)
    - Unknown labels (not in 0..14) fail loudly with ValueError.
    """
    if source_mask.ndim == 3 and source_mask.shape[0] == 1:
        source_mask = source_mask[0]

    # Validate that all labels in source mask belong to known taxonomy
    unique_labels = set(np.unique(source_mask).tolist())
    unknown_labels = unique_labels - KNOWN_SOURCE_LABELS
    if unknown_labels:
        raise ValueError(
            f"Corrupted or unknown source label IDs found in mask: {sorted(list(unknown_labels))}. "
            f"Known taxonomy labels are 0..14."
        )
        
    dense_mask = np.full(source_mask.shape, ignore_index, dtype=np.int64)
    
    for src_id, dense_idx in SOURCE_LABEL_TO_DENSE.items():
        dense_mask[source_mask == src_id] = dense_idx
        
    if validity_mask is not None:
        if validity_mask.ndim == 3 and validity_mask.shape[0] == 1:
            v_mask_2d = validity_mask[0]
        else:
            v_mask_2d = validity_mask
        dense_mask[~v_mask_2d] = ignore_index
        
    return dense_mask


# ==============================================================================
# 3. Candidate F Hybrid Sampler Math
# ==============================================================================

def compute_candidate_f_hybrid_weights(
    manifest_path: Union[str, Path] = OPS01_MANIFEST_PATH,
    train_split_name: str = "TRAIN",
) -> Tuple[np.ndarray, List[Dict[str, Any]], Dict[str, Any]]:
    """Compute exact Candidate F Hybrid sampling probabilities over the training split.
    
    Candidate F specification:
    - 70% Parent-Balanced component:
        w_parent(i) = 1.0 / (num_parents * tiles_in_parent)
    - 30% Class-Presence component:
        S(i) = sum(1.0 / tiles_containing_class(c) for c in classes_in_tile(i))
        w_presence(i) = S(i) / sum(S)
    - Hybrid stationary distribution:
        w_hybrid = 0.70 * w_parent + 0.30 * w_presence
        w_hybrid /= sum(w_hybrid)
    
    Returns
    -------
    weights : np.ndarray
        Array of length 72 containing exact sampling probability for each training tile.
    train_samples : list of dict
        Metadata dict for each training sample in manifest order.
    diagnostics : dict
        Calculated diagnostic properties (parent multipliers, rare class exposures).
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.is_absolute() and not manifest_path.exists():
        manifest_path = REPO_ROOT / manifest_path

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    train_samples = [s for s in manifest["samples"] if s["partition"] == train_split_name]
    n_train = len(train_samples)
    if n_train != 72:
        raise ValueError(f"Expected 72 training tiles, found {n_train}")
        
    # Group tiles by parent scene
    parent_tiles: Dict[str, List[int]] = {}
    for idx, s in enumerate(train_samples):
        pid = s["parent_scene_id"]
        parent_tiles.setdefault(pid, []).append(idx)
        
    num_parents = len(parent_tiles)
    if num_parents != 12:
        raise ValueError(f"Expected 12 parent scenes in TRAIN, found {num_parents}")
        
    # 1. Parent-balanced probability vector
    w_parent = np.zeros(n_train, dtype=np.float64)
    for pid, indices in parent_tiles.items():
        prob_per_tile = 1.0 / (num_parents * len(indices))
        for idx in indices:
            w_parent[idx] = prob_per_tile
            
    # 2. Class-presence probability vector
    # Count tiles containing each phenomenon class (BG included)
    class_tile_counts: Dict[str, int] = {c: 0 for c in DENSE_CLASSES}
    for s in train_samples:
        comp = s.get("class_composition", {})
        for c in DENSE_CLASSES:
            if c in comp and comp[c]["pixel_count"] > 0:
                class_tile_counts[c] += 1
                
    w_presence = np.zeros(n_train, dtype=np.float64)
    for idx, s in enumerate(train_samples):
        comp = s.get("class_composition", {})
        score = sum(
            1.0 / class_tile_counts[c]
            for c in DENSE_CLASSES
            if c in comp and comp[c]["pixel_count"] > 0 and class_tile_counts[c] > 0
        )
        w_presence[idx] = score
    w_presence /= np.sum(w_presence)
    
    # 3. Hybrid 70/30 combination
    w_hybrid = 0.70 * w_parent + 0.30 * w_presence
    w_hybrid /= np.sum(w_hybrid)
    
    # Calculate diagnostics
    parent_exposures = [float(np.sum(w_hybrid[indices]) * n_train) for indices in parent_tiles.values()]
    max_parent_mult = float(max(parent_exposures) / (n_train / num_parents))
    parent_cv = float(np.std(parent_exposures) / np.mean(parent_exposures))
    
    rare_exposures = {}
    for c in ["HM", "LWA", "Eddy"]:
        rare_exp = float(sum(
            w_hybrid[idx] * n_train
            for idx, s in enumerate(train_samples)
            if c in s.get("class_composition", {}) and s["class_composition"][c]["pixel_count"] > 0
        ))
        rare_exposures[c] = rare_exp
        
    diagnostics = {
        "num_train_tiles": n_train,
        "num_parents": num_parents,
        "max_parent_multiplier": max_parent_mult,
        "parent_exposure_cv": parent_cv,
        "rare_class_exposures": rare_exposures,
    }
    
    return w_hybrid, train_samples, diagnostics


# ==============================================================================
# 4. Multiclass Evaluation Metrics (Pure NumPy / Math)
# ==============================================================================

def compute_confusion_matrix_12x12(
    predictions: np.ndarray,
    targets: np.ndarray,
    validity_mask: Optional[np.ndarray] = None,
    num_classes: int = 12,
    ignore_index: int = IGNORE_INDEX,
) -> np.ndarray:
    """Compute exact 12x12 multiclass confusion matrix over valid pixels.
    
    Rows: Ground Truth class (0..11)
    Columns: Predicted class (0..11)
    """
    preds_flat = predictions.flatten()
    targets_flat = targets.flatten()
    
    # Valid pixel mask: inside swath AND not marked with ignore_index
    valid = targets_flat != ignore_index
    if validity_mask is not None:
        valid = valid & validity_mask.flatten().astype(bool)
        
    preds_valid = preds_flat[valid]
    targets_valid = targets_flat[valid]
    
    # Filter out-of-bounds predictions if any
    valid_range = (targets_valid >= 0) & (targets_valid < num_classes) & (preds_valid >= 0) & (preds_valid < num_classes)
    targets_valid = targets_valid[valid_range]
    preds_valid = preds_valid[valid_range]
    
    cm = np.bincount(
        targets_valid * num_classes + preds_valid,
        minlength=num_classes * num_classes,
    ).reshape(num_classes, num_classes)
    
    return cm.astype(np.int64)


def compute_metrics_from_confusion_matrix(
    cm: np.ndarray,
    class_names: Sequence[str] = DENSE_CLASSES,
) -> Dict[str, Any]:
    """Compute per-class IoU, Dice, Recall, and macro mIoU from 12x12 confusion matrix.
    
    Handling of absent classes:
    - If a class has zero true pixels in ground truth (GT == 0), it is marked as NaN
      and excluded from the macro average denominator.
    - mIoU_all: macro mean of IoU over all present classes (including BG).
    - mIoU_phenomena: macro mean of IoU over all present phenomenon classes (classes 1..11, excluding BG).
    """
    num_classes = cm.shape[0]
    tp = np.diag(cm).astype(np.float64)
    fp = (np.sum(cm, axis=0) - tp).astype(np.float64)
    fn = (np.sum(cm, axis=1) - tp).astype(np.float64)
    gt = tp + fn
    pred = tp + fp
    union = gt + pred - tp
    
    iou_per_class: Dict[str, Optional[float]] = {}
    dice_per_class: Dict[str, Optional[float]] = {}
    recall_per_class: Dict[str, Optional[float]] = {}
    
    present_classes_all: List[float] = []
    present_classes_phenomena: List[float] = []
    
    for c in range(num_classes):
        c_name = class_names[c]
        if gt[c] > 0:
            iou_val = float(tp[c] / union[c]) if union[c] > 0 else 0.0
            dice_val = float(2 * tp[c] / (gt[c] + pred[c])) if (gt[c] + pred[c]) > 0 else 0.0
            recall_val = float(tp[c] / gt[c])
            
            iou_per_class[c_name] = iou_val
            dice_per_class[c_name] = dice_val
            recall_per_class[c_name] = recall_val
            
            present_classes_all.append(iou_val)
            if c > 0:  # Exclude BG for phenomena metric
                present_classes_phenomena.append(iou_val)
        else:
            iou_per_class[c_name] = None
            dice_per_class[c_name] = None
            recall_per_class[c_name] = None
            
    miou_all = float(np.mean(present_classes_all)) if present_classes_all else 0.0
    miou_phenomena = float(np.mean(present_classes_phenomena)) if present_classes_phenomena else 0.0
    
    return {
        "confusion_matrix": cm.tolist(),
        "iou_per_class": iou_per_class,
        "dice_per_class": dice_per_class,
        "recall_per_class": recall_per_class,
        "mIoU_all": miou_all,
        "mIoU_phenomena": miou_phenomena,
        "num_classes_present_all": len(present_classes_all),
        "num_classes_present_phenomena": len(present_classes_phenomena),
    }


# ==============================================================================
# 5. Architecture Specification: ResNet18-UNet
# ==============================================================================

if TORCH_AVAILABLE:
    class DoubleConv(nn.Module):
        """Two consecutive [Conv2d -> BatchNorm2d -> ReLU] blocks."""

        def __init__(
            self,
            in_channels: int,
            out_channels: int,
            bn_momentum: float = 0.05,
        ) -> None:
            super().__init__()
            self.conv = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels, momentum=bn_momentum),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels, momentum=bn_momentum),
                nn.ReLU(inplace=True),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.conv(x)

    class DecoderBlock(nn.Module):
        """Decoder block: ConvTranspose2d upsampling + Skip concatenation + DoubleConv."""

        def __init__(
            self,
            in_channels: int,
            skip_channels: int,
            out_channels: int,
            bn_momentum: float = 0.05,
        ) -> None:
            super().__init__()
            self.up = nn.ConvTranspose2d(
                in_channels,
                in_channels // 2,
                kernel_size=2,
                stride=2,
            )
            self.conv = DoubleConv(
                (in_channels // 2) + skip_channels,
                out_channels,
                bn_momentum=bn_momentum,
            )

        def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
            x_up = self.up(x)
            if x_up.shape[-2:] != skip.shape[-2:]:
                diff_y = skip.size(2) - x_up.size(2)
                diff_x = skip.size(3) - x_up.size(3)
                x_up = nn.functional.pad(
                    x_up,
                    [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2],
                )
            x_cat = torch.cat([x_up, skip], dim=1)
            return self.conv(x_cat)

    class ResNet18UNet(nn.Module):
        """Authoritative ResNet18-UNet Architecture for EXP-07.
        
        Exact parameter counts:
        - Trainable parameters: 14,310,860
        - Floating-point running buffers: 11,776 (30 BatchNorm layers * 2 floating-point buffers)
        - Integer running buffers: 30 (30 BatchNorm layers * 1 int64 num_batches_tracked buffer)
        - Total state_dict elements: 14,322,666 (14,310,860 params + 11,806 buffers)
        - Input contract: [B, 1, 256, 256] float32
        - Output contract: [B, 12, 256, 256] float32 raw logits (no softmax / sigmoid)
        
        Normalization Option B:
        - Retains BatchNorm2d with momentum=0.05.
        - Physical minibatch: 8 samples. BatchNorm statistics computed over exactly 8 samples.
        - Gradient accumulation (virtual batch size = 16) stabilizes optimizer gradient estimation,
          NOT BatchNorm statistical batch size.
        """

        def __init__(
            self,
            in_channels: int = 1,
            num_classes: int = 12,
            pretrained: bool = True,
            bn_momentum: float = 0.05,
        ) -> None:
            super().__init__()
            self.in_channels = in_channels
            self.num_classes = num_classes

            # Instantiate ResNet-18 backbone
            if pretrained and ResNet18_Weights is not None:
                base_resnet = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
            else:
                base_resnet = resnet18(weights=None)

            # Adapt conv1 for 1-channel SAR input
            self.conv1 = nn.Conv2d(
                in_channels=in_channels,
                out_channels=64,
                kernel_size=7,
                stride=2,
                padding=3,
                bias=False,
            )
            if pretrained and in_channels == 1:
                with torch.no_grad():
                    self.conv1.weight.copy_(base_resnet.conv1.weight.mean(dim=1, keepdim=True))

            self.bn1 = base_resnet.bn1
            self.relu = base_resnet.relu
            self.maxpool = base_resnet.maxpool

            self.layer1 = base_resnet.layer1  # 64 ch
            self.layer2 = base_resnet.layer2  # 128 ch
            self.layer3 = base_resnet.layer3  # 256 ch
            self.layer4 = base_resnet.layer4  # 512 ch

            # Decoder stages matching exact 14,310,860 parameter specification
            self.dec4 = DecoderBlock(512, 256, 256, bn_momentum=bn_momentum)
            self.dec3 = DecoderBlock(256, 128, 128, bn_momentum=bn_momentum)
            self.dec2 = DecoderBlock(128, 64, 64, bn_momentum=bn_momentum)
            self.dec1 = DecoderBlock(64, 64, 64, bn_momentum=bn_momentum)

            # Final stage: 64 -> 32 -> 12
            self.final_up = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
            self.final_conv = DoubleConv(32, 32, bn_momentum=bn_momentum)
            self.head = nn.Conv2d(32, num_classes, kernel_size=1)

            # Apply momentum=0.05 to all BatchNorm layers
            for m in self.modules():
                if isinstance(m, nn.BatchNorm2d):
                    m.momentum = bn_momentum

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            if x.dim() != 4:
                raise ValueError(f"Expected 4D input [B, 1, H, W], got {x.dim()}D (shape {tuple(x.shape)})")
            if x.shape[1] != self.in_channels:
                raise ValueError(f"Expected {self.in_channels} input channels, got {x.shape[1]}")

            # Encoder
            x0 = self.relu(self.bn1(self.conv1(x)))  # [B, 64, H/2, W/2]
            xp = self.maxpool(x0)                   # [B, 64, H/4, W/4]
            x1 = self.layer1(xp)                    # [B, 64, H/4, W/4]
            x2 = self.layer2(x1)                    # [B, 128, H/8, W/8]
            x3 = self.layer3(x2)                    # [B, 256, H/16, W/16]
            x4 = self.layer4(x3)                    # [B, 512, H/32, W/32]

            # Decoder
            d4 = self.dec4(x4, x3)  # [B, 256, H/16, W/16]
            d3 = self.dec3(d4, x2)  # [B, 128, H/8, W/8]
            d2 = self.dec2(d3, x1)  # [B, 64, H/4, W/4]
            d1 = self.dec1(d2, x0)  # [B, 64, H/2, W/2]

            # Full-resolution upsampling and head
            up0 = self.final_up(d1)      # [B, 32, H, W]
            feat = self.final_conv(up0)  # [B, 32, H, W]
            logits = self.head(feat)     # [B, 12, H, W]

            return logits

    def create_exp07_loss() -> nn.CrossEntropyLoss:
        """Create exact square-root median-frequency CrossEntropyLoss for EXP-07."""
        weight_tensor = torch.tensor(
            [CLASS_WEIGHTS_SQRT_MEDIAN[c] for c in range(12)],
            dtype=torch.float32,
        )
        return nn.CrossEntropyLoss(
            weight=weight_tensor,
            ignore_index=IGNORE_INDEX,
            reduction="mean",
        )

else:
    ResNet18UNet = None
    create_exp07_loss = None


# ==============================================================================
# 6. OPS-01 Dataset Loader
# ==============================================================================

class OPS01Dataset:
    """Authoritative OPS-01 Dataset Reader for EXP-07.
    
    Reads physical tiles through the authoritative manifest:
    - Partition: TRAIN (72), DEV (39), or HOLDOUT (36)
    - Validates file existence and dimensions
    - Performs canonical validity masking and log1p standardization
    - Remaps 15-class source annotations to 12 dense indices
    - Emits both NumPy arrays and (if torch is available) PyTorch tensors.
    """

    def __init__(
        self,
        manifest_path: Union[str, Path] = OPS01_MANIFEST_PATH,
        partition: str = "TRAIN",
        mean: float = TRAIN_LOG1P_MEAN,
        std: float = TRAIN_LOG1P_STD,
        as_torch: bool = True,
    ) -> None:
        self.manifest_path = Path(manifest_path)
        if not self.manifest_path.is_absolute() and not self.manifest_path.exists():
            self.manifest_path = REPO_ROOT / self.manifest_path
        self.partition = partition.upper()
        self.mean = mean
        self.std = std
        self.as_torch = as_torch and TORCH_AVAILABLE

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        self.samples = [s for s in manifest_data["samples"] if s["partition"] == self.partition]
        if not self.samples:
            raise ValueError(f"No samples found for partition '{self.partition}' in {manifest_path}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        sample = self.samples[idx]
        img_path = Path(sample["derived_image_path"])
        msk_path = Path(sample["derived_mask_path"])
        if not img_path.is_absolute() and not img_path.exists():
            img_path = REPO_ROOT / img_path
        if not msk_path.is_absolute() and not msk_path.exists():
            msk_path = REPO_ROOT / msk_path

        if not img_path.exists():
            raise FileNotFoundError(f"Derived image not found: {img_path}")
        if not msk_path.exists():
            raise FileNotFoundError(f"Derived mask not found: {msk_path}")

        # Read GeoTIFF rasters using rasterio
        with rasterio.open(img_path) as src_img:
            raw_img = src_img.read(1).astype(np.float32)
        with rasterio.open(msk_path) as src_msk:
            raw_msk = src_msk.read(1)

        # Preprocessing: validity mask and standardization
        norm_img, validity_mask = preprocess_sar_image(raw_img, mean=self.mean, std=self.std)

        # Dense target mask remapping
        dense_msk = remap_source_mask_to_dense(raw_msk, validity_mask=validity_mask)

        payload = {
            "sample_id": sample["sample_id"],
            "parent_scene_id": sample["parent_scene_id"],
            "partition": sample["partition"],
            "raw_image": raw_img,
            "raw_mask": raw_msk,
            "image": norm_img,
            "target": dense_msk,
            "validity_mask": validity_mask,
        }

        if self.as_torch:
            payload["image"] = torch.from_numpy(norm_img)
            payload["target"] = torch.from_numpy(dense_msk)
            payload["validity_mask"] = torch.from_numpy(validity_mask)

        return payload


# ==============================================================================
# 7. Reproducibility Configuration
# ==============================================================================

@dataclass
class EXP07ReproducibilityConfig:
    experiment_id: str = "EXP-07-P0-C5-OPS01-V1"
    manifest_path: str = "data/metadata/ops01_physical_dataset_manifest_v4.json"
    manifest_sha256: str = "FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E"
    taxonomy_path: str = "data/metadata/ops01_taxonomy_v1.json"
    protocol_version: str = "EXP-07-P0-C4-OPS01-V1"
    git_branch: str = "master"
    base_seed: int = 42
    physical_batch_size: int = 8
    gradient_accumulation_steps: int = 2
    effective_optimization_batch_size: int = 16
    batchnorm_statistical_batch_size: int = 8
    batchnorm_momentum: float = 0.05
    train_log1p_mean: float = 4.2756
    train_log1p_std: float = 0.3866
    num_classes: int = 12
    ignore_index: int = -100
    holdout_status: str = "HOLDOUT_PARTIALLY_USED_FOR_SELECTION"
    device: str = "cpu"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
