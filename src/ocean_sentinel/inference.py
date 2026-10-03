"""Ocean Sentinel Binary Oil-Spill Inference Pipeline (Phase 1).

Executes end-to-end inference on Sentinel-1 SAR GeoTIFF imagery using trained
binary segmentation models (specifically ResNet34-UNet from EXP-06).

Pipeline stages:
1. Input validation and inspection (bands, dtype, CRS, transform, nodata, validity)
2. Normalization using frozen training statistics (Mapping A contract)
3. Grid tiling with configurable overlap and edge-clamped windows
4. Batched GPU/CPU tile inference with mixed precision
5. Spatial reconstruction with weighted overlap blending
6. Geospatial prediction GeoTIFF generation (probability map & binary mask)
7. Optional evaluation against ground-truth mask using canonical metrics
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine
import torch
import torch.nn as nn

from ocean_sentinel.ml.unet_resnet import ResNet34UNet

logger = logging.getLogger(__name__)

# Canonical Frozen EXP-06 Constants
DEFAULT_CHECKPOINT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "experiments"
    / "performance"
    / "exp06_positive_bce_weight"
    / "best_model.pt"
)
EXPECTED_EXP06_CHECKPOINT_SHA256 = (
    "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
)

# Mapping A Normalization Constants (Cross-Pol VH, Co-Pol VV in dB)
DEFAULT_NORM_MEAN = [-33.2323, -19.9405]
DEFAULT_NORM_STD = [6.4912, 4.5308]

DEFAULT_TILE_SIZE = 512
DEFAULT_THRESHOLD = 0.22


class InferenceError(Exception):
    """Base exception for errors during SAR inference."""
    pass


class InputValidationError(InferenceError):
    """Raised when an input SAR GeoTIFF fails contract validation."""
    pass


class CheckpointContractError(InferenceError):
    """Raised when a model checkpoint violates expected structure or architecture."""
    pass


@dataclass
class RasterMetadata:
    """Geospatial and structural metadata of an input raster."""
    path: Path
    width: int
    height: int
    count: int
    dtypes: Tuple[str, ...]
    crs: Optional[CRS]
    transform: Affine
    nodata: Optional[float]
    driver: str
    bounds: Tuple[float, float, float, float]


@dataclass
class InferenceResult:
    """Complete prediction output and associated telemetry."""
    probability_map: np.ndarray  # Shape: (H, W), float32, range [0, 1] or NaN for invalid
    prediction_mask: np.ndarray  # Shape: (H, W), uint8, {0, 1}
    validity_mask: np.ndarray    # Shape: (H, W), bool, True for valid finite pixels
    metadata: RasterMetadata
    tile_count: int
    execution_time_seconds: float
    probability_path: Optional[Path] = None
    mask_path: Optional[Path] = None
    evaluation_metrics: Optional[Dict[str, Any]] = None
    stats: Dict[str, Any] = field(default_factory=dict)


def load_binary_oil_model(
    checkpoint_path: Union[str, Path] = DEFAULT_CHECKPOINT_PATH,
    device: Optional[Union[str, torch.device]] = None,
    strict: bool = True,
) -> Tuple[nn.Module, Dict[str, Any]]:
    """Instantiate ResNet34UNet and load weights from an EXP-06 checkpoint.

    Parameters
    ----------
    checkpoint_path : str | Path
        Path to the `.pt` checkpoint file.
    device : str | torch.device | None
        Target device ('cuda', 'cpu', or None for auto-detection).
    strict : bool
        Whether to enforce exact key match in state_dict.

    Returns
    -------
    model : nn.Module
        Loaded ResNet34UNet in evaluation mode.
    checkpoint_meta : dict[str, Any]
        Metadata extracted from checkpoint (epoch, val_metrics, git_commit, etc.).
    """
    ckpt_path = Path(checkpoint_path)
    if not ckpt_path.is_file():
        raise CheckpointContractError(f"Checkpoint file not found: {ckpt_path}")

    if device is None:
        target_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        target_device = torch.device(device)

    logger.info("Instantiating ResNet34UNet (in_channels=2, num_classes=1, adaptation='slice_variance_scaled')")
    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")

    try:
        ckpt = torch.load(ckpt_path, map_location=target_device, weights_only=False)
    except Exception as e:
        raise CheckpointContractError(f"Failed to load checkpoint file at {ckpt_path}: {e}") from e

    state_dict = ckpt.get("model_state_dict", ckpt) if isinstance(ckpt, dict) else ckpt

    try:
        model.load_state_dict(state_dict, strict=strict)
    except Exception as e:
        raise CheckpointContractError(
            f"State dict mismatch loading into ResNet34UNet from {ckpt_path}: {e}"
        ) from e

    model.to(target_device)
    model.eval()

    meta: Dict[str, Any] = {
        "checkpoint_path": str(ckpt_path),
        "device": str(target_device),
        "epoch": ckpt.get("epoch") if isinstance(ckpt, dict) else None,
        "val_metrics": ckpt.get("val_metrics") if isinstance(ckpt, dict) else None,
        "git_commit": ckpt.get("git_commit") if isinstance(ckpt, dict) else None,
        "train_loss": ckpt.get("train_loss") if isinstance(ckpt, dict) else None,
    }

    return model, meta


def load_and_validate_sar_raster(
    input_path: Union[str, Path],
    require_georeferencing: bool = True,
) -> Tuple[np.ndarray, RasterMetadata, np.ndarray]:
    """Inspect, validate, and load a SAR GeoTIFF image.

    Parameters
    ----------
    input_path : str | Path
        Path to the SAR GeoTIFF file.
    require_georeferencing : bool
        If True, rejects imagery missing valid CRS or affine geotransform.

    Returns
    -------
    image_data : np.ndarray
        Array of shape (2, H, W) with float32 values (typically in dB).
    metadata : RasterMetadata
        Parsed geospatial and raster attributes.
    validity_mask : np.ndarray
        Boolean array of shape (H, W) where True denotes finite, valid pixels.

    Raises
    ------
    InputValidationError
        If band count, dtype, geometry, or georeferencing violates the contract.
    """
    path = Path(input_path)
    if not path.is_file():
        raise InputValidationError(f"Input SAR raster not found: {path}")

    try:
        with rasterio.open(path) as src:
            count = src.count
            height = src.height
            width = src.width
            dtypes = src.dtypes
            crs = src.crs
            transform = src.transform
            nodata = src.nodata
            driver = src.driver
            bounds = tuple(src.bounds)

            # Contract validation
            if count != 2:
                raise InputValidationError(
                    f"Invalid band count: expected exactly 2 channels (Mapping A: VH, VV), "
                    f"got {count} bands in {path.name}"
                )

            if height <= 0 or width <= 0:
                raise InputValidationError(
                    f"Invalid dimensions: height={height}, width={width} in {path.name}"
                )

            if require_georeferencing:
                if crs is None:
                    raise InputValidationError(
                        f"Missing coordinate reference system (CRS) in georeferenced SAR raster: {path.name}"
                    )
                if transform is None or transform.is_identity:
                    logger.warning(
                        f"Raster {path.name} has identity or trivial geotransform."
                    )

            # Read full raster
            raw_data = src.read().astype(np.float32)  # Shape (2, H, W)
    except InputValidationError:
        raise
    except Exception as e:
        raise InputValidationError(f"Failed to read raster {path}: {e}") from e

    # Validity mask calculation: must be finite in both channels
    finite_mask = np.all(np.isfinite(raw_data), axis=0)  # (H, W)
    if nodata is not None:
        nodata_mask = np.all(raw_data != nodata, axis=0)
        validity_mask = finite_mask & nodata_mask
    else:
        validity_mask = finite_mask

    valid_pixel_count = int(np.sum(validity_mask))
    total_pixels = height * width

    if valid_pixel_count == 0:
        raise InputValidationError(
            f"Raster {path.name} contains zero valid/finite pixels (all NaN or nodata)."
        )

    # Radiometric sanity check: SAR dB values are typically between -60 and +15 dB
    valid_values_ch0 = raw_data[0][validity_mask]
    min_val, max_val = float(np.min(valid_values_ch0)), float(np.max(valid_values_ch0))
    if min_val < -100.0 or max_val > 100.0:
        logger.warning(
            f"Radiometric range suspicious for dB SAR backscatter: "
            f"min={min_val:.1f} dB, max={max_val:.1f} dB in {path.name}."
        )

    meta = RasterMetadata(
        path=path,
        width=width,
        height=height,
        count=count,
        dtypes=dtypes,
        crs=crs,
        transform=transform,
        nodata=nodata,
        driver=driver,
        bounds=bounds,
    )

    return raw_data, meta, validity_mask


def preprocess_sar(
    image_data: np.ndarray,
    validity_mask: np.ndarray,
    mean: Union[List[float], Tuple[float, float]] = DEFAULT_NORM_MEAN,
    std: Union[List[float], Tuple[float, float]] = DEFAULT_NORM_STD,
) -> np.ndarray:
    """Apply Mapping A z-score standardization to a 2-band SAR raster.

    Parameters
    ----------
    image_data : np.ndarray
        Array of shape (2, H, W) in dB units.
    validity_mask : np.ndarray
        Boolean array of shape (H, W) where True denotes valid pixels.
    mean : list[float] | tuple[float, float]
        Per-channel means [mean_ch0, mean_ch1].
    std : list[float] | tuple[float, float]
        Per-channel stds [std_ch0, std_ch1].

    Returns
    -------
    normalized_data : np.ndarray
        Standardized array of shape (2, H, W), with invalid pixels imputed to 0.0
        (which maps to channel mean in z-score space).
    """
    normalized = np.zeros_like(image_data, dtype=np.float32)
    norm_mean = np.array(mean, dtype=np.float32).reshape(2, 1, 1)
    norm_std = np.array(std, dtype=np.float32).reshape(2, 1, 1)

    # Standardize
    normalized = (image_data - norm_mean) / norm_std

    # Safe imputation: invalid pixels get 0.0 (mean value in normalized space)
    # to avoid NaN explosion during convolution. Final output will mask these out.
    for c in range(2):
        ch = normalized[c]
        ch[~validity_mask] = 0.0
        normalized[c] = ch

    return normalized


def compute_tile_windows(
    height: int,
    width: int,
    tile_size: int = DEFAULT_TILE_SIZE,
    overlap: int = 0,
) -> List[Tuple[int, int, int, int]]:
    """Compute grid of (row_start, row_end, col_start, col_end) tile windows.

    Guarantees:
    - Every tile has exact dimensions (tile_size, tile_size)
    - Full image coverage with no uncovered boundary regions
    - Edge boundaries clamped safely to image extent
    """
    if height < tile_size or width < tile_size:
        raise ValueError(
            f"Raster dimensions ({height}x{width}) smaller than tile size ({tile_size}x{tile_size})."
        )
    if overlap < 0 or overlap >= tile_size:
        raise ValueError(
            f"Overlap must be in range [0, {tile_size - 1}], got {overlap}"
        )

    stride = tile_size - overlap

    def get_axis_spans(length: int) -> List[Tuple[int, int]]:
        spans: List[Tuple[int, int]] = []
        pos = 0
        while pos + tile_size <= length:
            spans.append((pos, pos + tile_size))
            pos += stride

        # Ensure the final boundary is covered by clamping to the edge
        if spans and spans[-1][1] < length:
            spans.append((length - tile_size, length))
        elif not spans:
            spans.append((0, tile_size))

        # Deduplicate while preserving order
        unique_spans: List[Tuple[int, int]] = []
        for s in spans:
            if not unique_spans or unique_spans[-1] != s:
                unique_spans.append(s)
        return unique_spans

    row_spans = get_axis_spans(height)
    col_spans = get_axis_spans(width)

    windows: List[Tuple[int, int, int, int]] = []
    for r_start, r_end in row_spans:
        for c_start, c_end in col_spans:
            windows.append((r_start, r_end, c_start, c_end))

    return windows


def create_blend_weight_window(
    tile_size: int = DEFAULT_TILE_SIZE,
    blend: bool = True,
) -> np.ndarray:
    """Create a 2D weight matrix for tile reconstruction.

    If blend=False, returns uniform weights (ones).
    If blend=True, returns a 2D Bartlett-tapered weight matrix with a 0.1 floor.
    """
    if not blend:
        return np.ones((tile_size, tile_size), dtype=np.float32)

    w_1d = np.bartlett(tile_size).astype(np.float32)
    w_1d = 0.1 + 0.9 * w_1d  # Floor at 0.1 to avoid boundary zeros
    return np.outer(w_1d, w_1d)


def predict_tiles(
    model: nn.Module,
    preprocessed_data: np.ndarray,
    windows: List[Tuple[int, int, int, int]],
    batch_size: int = 8,
    device: Optional[torch.device] = None,
) -> List[np.ndarray]:
    """Execute batched model forward passes over preprocessed raster tiles.

    Parameters
    ----------
    model : nn.Module
        ResNet34UNet in eval mode.
    preprocessed_data : np.ndarray
        Array of shape (2, H, W).
    windows : list[tuple[int, int, int, int]]
        List of (r_start, r_end, c_start, c_end) windows.
    batch_size : int
        Number of tiles per forward pass.
    device : torch.device | None
        Computation device.

    Returns
    -------
    tile_probs : list[np.ndarray]
        List of probability maps of shape (tile_size, tile_size).
    """
    if device is None:
        device = next(model.parameters()).device

    tile_probs: List[np.ndarray] = []
    n_tiles = len(windows)

    with torch.no_grad():
        for start_idx in range(0, n_tiles, batch_size):
            batch_windows = windows[start_idx : start_idx + batch_size]
            batch_tiles = [
                preprocessed_data[:, r0:r1, c0:c1] for r0, r1, c0, c1 in batch_windows
            ]
            batch_np = np.stack(batch_tiles, axis=0)  # (B, 2, tile_size, tile_size)
            batch_t = torch.from_numpy(batch_np).to(device)

            use_amp = (device.type == "cuda")
            with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                logits = model(batch_t)
                probs = torch.sigmoid(logits)  # (B, 1, H, W)

            probs_np = probs.squeeze(1).cpu().numpy().astype(np.float32)
            for b in range(probs_np.shape[0]):
                tile_probs.append(probs_np[b])

    return tile_probs


def reconstruct_prediction(
    tile_probs: List[np.ndarray],
    windows: List[Tuple[int, int, int, int]],
    height: int,
    width: int,
    blend_weight: np.ndarray,
    validity_mask: np.ndarray,
    threshold: float = DEFAULT_THRESHOLD,
) -> Tuple[np.ndarray, np.ndarray]:
    """Reconstruct full-image probability map and thresholded prediction mask.

    Parameters
    ----------
    tile_probs : list[np.ndarray]
        List of tile probability arrays of shape (tile_size, tile_size).
    windows : list[tuple[int, int, int, int]]
        Grid coordinates corresponding to each tile.
    height : int
        Full raster height.
    width : int
        Full raster width.
    blend_weight : np.ndarray
        Weight matrix of shape (tile_size, tile_size).
    validity_mask : np.ndarray
        Boolean array of shape (H, W) indicating valid pixels.
    threshold : float
        Decision threshold tau for binary mask generation.

    Returns
    -------
    probability_map : np.ndarray
        Continuous probability map of shape (H, W), float32, NaN on invalid pixels.
    prediction_mask : np.ndarray
        Binary segmentation mask of shape (H, W), uint8 {0, 1}, 0 on invalid pixels.
    """
    accum_prob = np.zeros((height, width), dtype=np.float32)
    accum_weight = np.zeros((height, width), dtype=np.float32)

    for (r0, r1, c0, c1), t_prob in zip(windows, tile_probs):
        accum_prob[r0:r1, c0:c1] += t_prob * blend_weight
        accum_weight[r0:r1, c0:c1] += blend_weight

    # Normalized reconstruction
    prob_map = np.divide(accum_prob, np.maximum(accum_weight, 1e-7))

    # Enforce validity mask: invalid pixels are NaN in probability map
    prob_map[~validity_mask] = np.nan

    # Binary mask: threshold applied strictly to valid pixels
    pred_mask = np.zeros((height, width), dtype=np.uint8)
    valid_oil = (prob_map >= threshold) & validity_mask
    pred_mask[valid_oil] = 1

    return prob_map, pred_mask


def write_georeferenced_prediction(
    probability_map: np.ndarray,
    prediction_mask: np.ndarray,
    metadata: RasterMetadata,
    output_dir: Union[str, Path],
    output_prefix: Optional[str] = None,
) -> Tuple[Path, Path]:
    """Persist prediction probability map and binary mask as georeferenced GeoTIFFs.

    Parameters
    ----------
    probability_map : np.ndarray
        Full-resolution probability map (H, W), float32.
    prediction_mask : np.ndarray
        Full-resolution binary mask (H, W), uint8.
    metadata : RasterMetadata
        Source raster geospatial metadata.
    output_dir : str | Path
        Directory where GeoTIFFs will be saved.
    output_prefix : str | None
        Filename prefix. Defaults to input raster stem.

    Returns
    -------
    prob_path : Path
        Path to written probability GeoTIFF.
    mask_path : Path
        Path to written mask GeoTIFF.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    prefix = output_prefix or metadata.path.stem
    prob_path = out_dir / f"{prefix}_probability.tif"
    mask_path = out_dir / f"{prefix}_mask.tif"

    base_profile = {
        "driver": "GTiff",
        "height": metadata.height,
        "width": metadata.width,
        "crs": metadata.crs,
        "transform": metadata.transform,
    }

    # 1. Write Probability GeoTIFF (float32)
    prob_profile = {
        **base_profile,
        "count": 1,
        "dtype": "float32",
        "nodata": np.nan,
    }
    with rasterio.open(prob_path, "w", **prob_profile) as dst:
        dst.write(probability_map.astype(np.float32), 1)
        dst.set_band_description(1, "Oil Spill Detection Probability [0.0 - 1.0]")

    # 2. Write Mask GeoTIFF (uint8)
    mask_profile = {
        **base_profile,
        "count": 1,
        "dtype": "uint8",
        "nodata": 255,  # 255 for nodata, {0, 1} for valid predictions
    }
    with rasterio.open(mask_path, "w", **mask_profile) as dst:
        dst.write(prediction_mask.astype(np.uint8), 1)
        dst.set_band_description(1, "Oil Spill Binary Mask (0=water/background, 1=oil)")

    logger.info(f"Saved probability GeoTIFF to: {prob_path}")
    logger.info(f"Saved mask GeoTIFF to:        {mask_path}")

    return prob_path, mask_path


def evaluate_prediction_against_ground_truth(
    prediction_prob_or_mask: np.ndarray,
    ground_truth_mask: np.ndarray,
    threshold: float = DEFAULT_THRESHOLD,
    is_probability: bool = True,
    validity_mask: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Compute standard segmentation evaluation metrics against ground truth.

    Uses canonical confusion matrix calculation:
    TP, FP, FN, TN, IoU (Jaccard), Dice (F1), Precision, Recall.
    """
    from ocean_sentinel.ml.metrics import (
        compute_confusion_matrix_counts,
        compute_metrics_from_counts,
    )

    pred = np.asarray(prediction_prob_or_mask)
    gt = (np.asarray(ground_truth_mask) >= 0.5)

    if validity_mask is not None:
        pred_eval = pred[validity_mask]
        gt_eval = gt[validity_mask]
    else:
        pred_eval = pred.flatten()
        gt_eval = gt.flatten()

    tp, fp, fn, tn = compute_confusion_matrix_counts(
        pred_eval, gt_eval, threshold=threshold, is_logits=False
    )
    metrics = compute_metrics_from_counts(tp, fp, fn, tn)

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "threshold": threshold,
        **metrics,
    }


def predict_sar_image(
    input_path: Union[str, Path],
    checkpoint_path: Union[str, Path] = DEFAULT_CHECKPOINT_PATH,
    output_dir: Optional[Union[str, Path]] = None,
    output_prefix: Optional[str] = None,
    tile_size: int = DEFAULT_TILE_SIZE,
    overlap: int = 0,
    threshold: float = DEFAULT_THRESHOLD,
    device: Optional[Union[str, torch.device]] = None,
    batch_size: int = 8,
    model: Optional[nn.Module] = None,
    ground_truth_path: Optional[Union[str, Path]] = None,
    require_georeferencing: bool = True,
) -> InferenceResult:
    """Full-pipeline execution on a single SAR GeoTIFF image.

    Parameters
    ----------
    input_path : str | Path
        Path to SAR GeoTIFF image.
    checkpoint_path : str | Path
        Path to model checkpoint.
    output_dir : str | Path | None
        Directory to save prediction GeoTIFFs (if None, files are not saved to disk).
    output_prefix : str | None
        Prefix for output GeoTIFF files.
    tile_size : int
        Window size for tiled inference (default 512).
    overlap : int
        Overlap in pixels between adjacent windows (default 0).
    threshold : float
        Decision threshold tau (default 0.22).
    device : str | torch.device | None
        Device ('cuda' or 'cpu').
    batch_size : int
        Tiles per batch for forward pass.
    model : nn.Module | None
        Preloaded model instance (optional; loads checkpoint if None).
    ground_truth_path : str | Path | None
        Optional path to ground-truth mask GeoTIFF for evaluation.
    require_georeferencing : bool
        Whether to enforce CRS and affine transform presence.

    Returns
    -------
    InferenceResult
        Prediction maps, metadata, and execution telemetry.
    """
    start_time = time.time()

    # 1. Model Preparation
    if model is None:
        model, _ = load_binary_oil_model(checkpoint_path=checkpoint_path, device=device)
    target_device = next(model.parameters()).device

    # 2. Input Validation and Ingestion
    raw_data, metadata, validity_mask = load_and_validate_sar_raster(
        input_path, require_georeferencing=require_georeferencing
    )

    # 3. Preprocessing
    norm_data = preprocess_sar(raw_data, validity_mask)

    # 4. Tiling
    windows = compute_tile_windows(
        metadata.height, metadata.width, tile_size=tile_size, overlap=overlap
    )
    use_blend = (overlap > 0)
    blend_weights = create_blend_weight_window(tile_size=tile_size, blend=use_blend)

    # 5. Batched Tile Inference
    tile_probs = predict_tiles(
        model=model,
        preprocessed_data=norm_data,
        windows=windows,
        batch_size=batch_size,
        device=target_device,
    )

    # 6. Spatial Reconstruction
    prob_map, pred_mask = reconstruct_prediction(
        tile_probs=tile_probs,
        windows=windows,
        height=metadata.height,
        width=metadata.width,
        blend_weight=blend_weights,
        validity_mask=validity_mask,
        threshold=threshold,
    )

    # 7. Geospatial GeoTIFF Output (if output_dir provided)
    prob_path = None
    mask_path = None
    if output_dir is not None:
        prob_path, mask_path = write_georeferenced_prediction(
            probability_map=prob_map,
            prediction_mask=pred_mask,
            metadata=metadata,
            output_dir=output_dir,
            output_prefix=output_prefix,
        )

    # 8. Ground Truth Evaluation (if provided)
    eval_metrics = None
    if ground_truth_path is not None:
        gt_path = Path(ground_truth_path)
        if gt_path.is_file():
            with rasterio.open(gt_path) as src_gt:
                gt_mask = src_gt.read(1)
            eval_metrics = evaluate_prediction_against_ground_truth(
                prediction_prob_or_mask=prob_map,
                ground_truth_mask=gt_mask,
                threshold=threshold,
                is_probability=True,
                validity_mask=validity_mask,
            )

    elapsed = time.time() - start_time

    # Compute descriptive prediction statistics
    valid_pixels = int(np.sum(validity_mask))
    oil_pixels = int(np.sum(pred_mask == 1))
    oil_fraction = (oil_pixels / valid_pixels) if valid_pixels > 0 else 0.0
    mean_prob = float(np.nanmean(prob_map)) if valid_pixels > 0 else 0.0

    stats = {
        "total_pixels": metadata.height * metadata.width,
        "valid_pixels": valid_pixels,
        "invalid_pixels": (metadata.height * metadata.width) - valid_pixels,
        "oil_pixels": oil_pixels,
        "oil_area_fraction": round(oil_fraction, 6),
        "mean_valid_probability": round(mean_prob, 6),
        "tile_count": len(windows),
        "tile_size": tile_size,
        "overlap": overlap,
        "threshold": threshold,
        "device": str(target_device),
    }

    return InferenceResult(
        probability_map=prob_map,
        prediction_mask=pred_mask,
        validity_mask=validity_mask,
        metadata=metadata,
        tile_count=len(windows),
        execution_time_seconds=round(elapsed, 4),
        probability_path=prob_path,
        mask_path=mask_path,
        evaluation_metrics=eval_metrics,
        stats=stats,
    )
