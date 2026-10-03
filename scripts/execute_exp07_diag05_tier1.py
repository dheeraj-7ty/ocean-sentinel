"""EXP-07 DIAG-05 Tier-1 Static Gradient Profiling Execution Runner.

Protocol: DIAG-05 (Loss Landscape & Gradient Dynamics at Initialization)
Domain: Multiclass Semantic Segmentation on OPS-02 Sentinel-1 SAR Imagery
Model: ResNet18-UNet (Option B BatchNorm baseline, 14,310,860 parameters)
Dataset: OPS-02 TRAIN (132 physical tiles / 40 parent clusters)

CRITICAL GOVERNANCE AND SAFETY GATE:
User authorization explicitly granted for EXP-07-P0-DIAG-05-TIER1-STATIC-GRADIENT-PROFILING only.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import rasterio
from PIL import Image
import scipy.stats
import torch
import torch.nn as nn
import torch.nn.functional as F

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ocean_sentinel.ml.exp07_reference import (
    ResNet18UNet,
    compute_validity_mask,
    preprocess_sar_image,
    remap_source_mask_to_dense,
    TRAIN_LOG1P_MEAN,
    TRAIN_LOG1P_STD,
)

# User authorization status: fail-closed post-execution lock
EXECUTION_AUTHORIZED: bool = False

# Authoritative repository roots and paths
CHECKPOINT_CANONICAL_PATH = REPO_ROOT / "data" / "ops02" / "initial_model_state_canonical.pt"
CHECKPOINT_CANONICAL_SHA256 = "67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D"

MANIFEST_OPS02_PATH = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"
MANIFEST_OPS02_SHA256 = "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"

QUARANTINED_HOLDOUT_DIR = REPO_ROOT / "data" / "ops02" / "holdout"
QUARANTINED_PART_III_DIR = REPO_ROOT / "experiments" / "performance" / "phase_6_part_iii_external_evaluation"
AUDIT_OUTPUT_DIR = REPO_ROOT / "data" / "ops02" / "audits"
TELEMETRY_STATE_PATH = REPO_ROOT / "scratch" / "diag05_preexecution_audit_run_state.json"

# Compute envelope constants (LL-DIAG05-PLAN-025)
H1_EXPECTED_BACKWARD_PASSES: int = 66    # 33 batches of B_phys=4 x 2 arms
H2_EXPECTED_BACKWARD_PASSES: int = 112   # 28 physical tiles (B_phys=1) x 4 passes
TOTAL_DETERMINISTIC_PASSES: int = 178    # 66 + 112
HARD_AUTHORIZATION_CEILING: int = 200    # 178 + 22 contingency headroom
WALLCLOCK_LIMIT_SECONDS: int = 180

# Population constants
POPULATION_A_TILES_COUNT: int = 28
POPULATION_A_CLUSTERS_COUNT: int = 15
POPULATION_B_TILES_COUNT: int = 132
POPULATION_B_CLUSTERS_COUNT: int = 40
H1_BATCH_SIZE: int = 4
H1_BATCHES_COUNT: int = 33
H2_OBSERVATION_BATCH_SIZE: int = 1       # Cluster-pure B_phys=1 (LL-DIAG05-PLAN-024)

# Minimum pixel support criteria for H2 Population A
H2_RARE_MIN_PIXELS: int = 16
H2_COMMON_MIN_PIXELS: int = 64

# Canonical class groupings
RARE_CORE_CLASSES = [5, 7, 11]           # OF (5), RF (7), HM (11)
COMMON_7_CLASSES = [1, 2, 4, 6, 8, 9, 10] # AF (1), BS (2), MCC (4), POW (6), WS (8), Eddy (9), IWs (10)
OTHER_CLASSES = [0, 3]                   # BG (0), LWA (3)

# Canonical class weights
CANONICAL_CLASS_WEIGHTS = [
    0.403935, 2.450546, 0.876692, 0.945945, 0.648189, 4.211476,
    0.719641, 2.956203, 1.064525, 1.882870, 0.387652, 18.243211
]
UNIFORM_CLASS_WEIGHTS = [1.0] * 12

PRE_REGISTERED_LAYER_TARGETS = [
    "conv1",
    "layer1.0.conv1",
    "layer2.0.conv1",
    "layer3.0.conv1",
    "layer4.0.conv1",
    "dec4.conv.conv.0",
    "dec3.conv.conv.0",
    "dec2.conv.conv.0",
    "dec1.conv.conv.0",
    "head",
]


def assert_execution_authorized() -> None:
    """Enforce fail-closed gate prior to any scientific compute or model/data loading."""
    if not EXECUTION_AUTHORIZED:
        raise RuntimeError(
            "DIAG-05 Tier-1 execution is strictly NOT authorized. "
            "EXECUTION_AUTHORIZED is False. Execution requires explicit user authorization "
            "and protocol amendment before any backward passes or scientific evaluations may occur."
        )


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def verify_checkpoint_integrity(
    checkpoint_path: Path = CHECKPOINT_CANONICAL_PATH,
    expected_sha256: str = CHECKPOINT_CANONICAL_SHA256,
) -> Dict[str, Any]:
    """Verify integrity of the canonical model checkpoint (Phase 4)."""
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Canonical checkpoint missing at {checkpoint_path}")
    
    actual_sha = compute_sha256(checkpoint_path)
    if actual_sha != expected_sha256.upper():
        raise ValueError(
            f"Checkpoint SHA-256 mismatch!\nExpected: {expected_sha256}\nActual:   {actual_sha}"
        )
        
    state_dict = torch.load(checkpoint_path, map_location="cpu")
    if "model_state_dict" in state_dict:
        weights = state_dict["model_state_dict"]
    else:
        weights = state_dict

    total_params = sum(p.numel() for p in weights.values())
    
    return {
        "checkpoint_path": str(checkpoint_path),
        "sha256": actual_sha,
        "is_valid": True,
        "total_elements": total_params,
    }


def verify_dataset_manifest_integrity(
    manifest_path: Path = MANIFEST_OPS02_PATH,
    expected_sha256: str = MANIFEST_OPS02_SHA256,
) -> Dict[str, Any]:
    """Verify integrity of the OPS-02 physical dataset manifest (Phase 5)."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Dataset manifest missing at {manifest_path}")
        
    actual_sha = compute_sha256(manifest_path)
    if actual_sha != expected_sha256.upper():
        raise ValueError(
            f"Dataset manifest SHA-256 mismatch!\nExpected: {expected_sha256}\nActual:   {actual_sha}"
        )
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    train_samples = [s for s in data["samples"] if s.get("partition") == "TRAIN"]
    if len(train_samples) != POPULATION_B_TILES_COUNT:
        raise ValueError(f"Expected {POPULATION_B_TILES_COUNT} TRAIN tiles, found {len(train_samples)}")
        
    clusters = set(s["parent_scene_id"] for s in train_samples if "parent_scene_id" in s)
    if len(clusters) != POPULATION_B_CLUSTERS_COUNT:
        raise ValueError(f"Expected {POPULATION_B_CLUSTERS_COUNT} TRAIN clusters, found {len(clusters)}")
        
    return {
        "manifest_path": str(manifest_path),
        "sha256": actual_sha,
        "train_tiles_count": len(train_samples),
        "train_clusters_count": len(clusters),
        "is_valid": True,
    }


def verify_h2_population_census(
    manifest_path: Path = MANIFEST_OPS02_PATH,
) -> Dict[str, Any]:
    """Verify the exact H2 Population A census from manifest and physical masks."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    train_samples = [s for s in data["samples"] if s.get("partition") == "TRAIN"]
    
    # Dense class mapping: Rare {5,7,11} -> source {6,8,13}; Common-7 -> source {1,2,5,7,10,11,12}
    rare_sources = {6, 8, 13}
    common_sources = {1, 2, 5, 7, 10, 11, 12}
    
    eligible_tiles = []
    eligible_clusters = set()
    eligible_samples = []
    
    for s in train_samples:
        mask_path = REPO_ROOT / s["derived_mask_path"]
        mask_arr = np.array(Image.open(mask_path))
        rare_pixels = int(np.isin(mask_arr, list(rare_sources)).sum())
        common_pixels = int(np.isin(mask_arr, list(common_sources)).sum())
        
        if rare_pixels >= H2_RARE_MIN_PIXELS and common_pixels >= H2_COMMON_MIN_PIXELS:
            eligible_tiles.append(s["sample_id"])
            eligible_clusters.add(s["parent_scene_id"])
            eligible_samples.append({
                "sample": s,
                "rare_pixel_count": rare_pixels,
                "common_pixel_count": common_pixels,
            })
            
    if len(eligible_tiles) != POPULATION_A_TILES_COUNT:
        raise ValueError(
            f"Population A census violation: expected {POPULATION_A_TILES_COUNT} eligible tiles, "
            f"found {len(eligible_tiles)}. Silent truncation or alteration is forbidden."
        )
        
    if len(eligible_clusters) != POPULATION_A_CLUSTERS_COUNT:
        raise ValueError(
            f"Population A cluster violation: expected {POPULATION_A_CLUSTERS_COUNT} parent clusters, "
            f"found {len(eligible_clusters)}."
        )
        
    return {
        "eligible_tiles_count": len(eligible_tiles),
        "eligible_clusters_count": len(eligible_clusters),
        "eligible_tile_ids": sorted(eligible_tiles),
        "eligible_cluster_ids": sorted(list(eligible_clusters)),
        "eligible_samples": sorted(eligible_samples, key=lambda x: x["sample"]["sample_id"]),
        "is_census_locked": True,
    }


def verify_compute_envelope_limits(
    h1_expected: int = H1_EXPECTED_BACKWARD_PASSES,
    h2_expected: int = H2_EXPECTED_BACKWARD_PASSES,
    hard_ceiling: int = HARD_AUTHORIZATION_CEILING,
    wallclock_limit: int = WALLCLOCK_LIMIT_SECONDS,
) -> Dict[str, Any]:
    """Verify compute envelope constraints before execution."""
    total_deterministic = h1_expected + h2_expected
    if total_deterministic != TOTAL_DETERMINISTIC_PASSES:
        raise ValueError(
            f"Mismatched deterministic passes: {h1_expected} + {h2_expected} = {total_deterministic} "
            f"!= {TOTAL_DETERMINISTIC_PASSES}"
        )
    if total_deterministic > hard_ceiling:
        raise ValueError(
            f"Requested compute {total_deterministic} exceeds hard ceiling {hard_ceiling}!"
        )
    return {
        "h1_expected_passes": h1_expected,
        "h2_expected_passes": h2_expected,
        "total_deterministic_passes": total_deterministic,
        "hard_ceiling": hard_ceiling,
        "wallclock_limit_seconds": wallclock_limit,
        "is_valid": True,
    }


def configure_h1_model_mode(model: nn.Module) -> None:
    """Configure model mode and BatchNorm invariants for Tier-1 H1/H2 static profiling."""
    model.eval()
    if model.training:
        raise ValueError("Model must be in eval() mode for static Step-0 gradient profiling.")
    
    bn_count = 0
    for name, module in model.named_modules():
        if isinstance(module, (nn.BatchNorm1d, nn.BatchNorm2d, nn.BatchNorm3d)):
            bn_count += 1
            if module.training:
                raise ValueError(f"BatchNorm layer {name} must have module.training == False.")
    
    if bn_count != 30:
        raise ValueError(f"Expected exactly 30 BatchNorm2d layers in ResNet18-UNet, found {bn_count}.")


def compute_h2_masked_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    mask: torch.Tensor,
    class_weights: torch.Tensor,
    ignore_index: int = -100,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Compute masked subgradient loss contribution under the full-observation reduction denominator."""
    valid_pixels = (targets != ignore_index) & (targets >= 0) & (targets < class_weights.shape[0])
    
    # 1. Full-observation weighted denominator D_batch
    d_batch = class_weights[targets[valid_pixels]].sum()
    if d_batch <= 0:
        raise ValueError("Full-observation denominator D_batch must be strictly positive.")
    
    # 2. Unweighted per-pixel loss elements ell_i = -log p(y_i)
    pixel_losses = F.cross_entropy(logits, targets, reduction="none", ignore_index=ignore_index)
    
    # 3. Selected masked subset valid pixels
    subset_valid = mask & valid_pixels
    
    if not subset_valid.any():
        loss_masked = torch.tensor(0.0, device=logits.device, dtype=logits.dtype, requires_grad=True)
        return loss_masked, d_batch
    
    # 4. Weighted numerator for subset
    subset_targets = targets[subset_valid]
    subset_weights = class_weights[subset_targets]
    subset_losses = pixel_losses[subset_valid]
    weighted_numerator = (subset_weights * subset_losses).sum()
    
    # 5. Normalized strictly by full-observation denominator D_batch
    loss_masked = weighted_numerator / d_batch
    
    return loss_masked, d_batch


def verify_h2_loss_decomposition(
    logits: torch.Tensor,
    targets: torch.Tensor,
    rare_mask: torch.Tensor,
    common_mask: torch.Tensor,
    other_mask: torch.Tensor,
    class_weights: torch.Tensor,
    ignore_index: int = -100,
) -> Dict[str, Any]:
    """Verify exact linear decomposition L_total = L_rare + L_common + L_other on identical logits."""
    valid_pixels = (targets != ignore_index) & (targets >= 0) & (targets < class_weights.shape[0])
    
    assert not (rare_mask & common_mask).any(), "Rare and Common masks must be mutually exclusive."
    assert not (rare_mask & other_mask).any(), "Rare and Other masks must be mutually exclusive."
    assert not (common_mask & other_mask).any(), "Common and Other masks must be mutually exclusive."
    
    union_mask = rare_mask | common_mask | other_mask
    assert torch.equal(union_mask & valid_pixels, valid_pixels), "Mask partition must cover all valid pixels."
    
    l_rare, d_batch_rare = compute_h2_masked_loss(logits, targets, rare_mask, class_weights, ignore_index)
    l_common, d_batch_common = compute_h2_masked_loss(logits, targets, common_mask, class_weights, ignore_index)
    l_other, d_batch_other = compute_h2_masked_loss(logits, targets, other_mask, class_weights, ignore_index)
    l_total, d_batch_total = compute_h2_masked_loss(logits, targets, valid_pixels, class_weights, ignore_index)
    
    assert torch.equal(d_batch_rare, d_batch_total), "D_batch must be identical across all components."
    assert torch.equal(d_batch_common, d_batch_total), "D_batch must be identical across all components."
    assert torch.equal(d_batch_other, d_batch_total), "D_batch must be identical across all components."
    
    sum_losses = l_rare + l_common + l_other
    diff = torch.abs(sum_losses - l_total).item()
    
    return {
        "l_rare": l_rare.item(),
        "l_common": l_common.item(),
        "l_other": l_other.item(),
        "l_total": l_total.item(),
        "l_sum": sum_losses.item(),
        "absolute_difference": diff,
        "is_exact_decomposition": diff < 1e-6,
        "d_batch": d_batch_total.item(),
    }


def atomic_write_json(data: Dict[str, Any], destination_path: Path) -> str:
    """Safely write JSON artifact atomically via temporary file and return its SHA-256."""
    destination_path = Path(destination_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    
    temp_dir = destination_path.parent
    with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
        json.dump(data, tf, indent=2)
        temp_path = Path(tf.name)
        
    os.replace(temp_path, destination_path)
    return compute_sha256(destination_path)


def load_single_tile(sample: Dict[str, Any]) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Load and preprocess a single physical tile from disk."""
    img_path = REPO_ROOT / sample["derived_image_path"]
    mask_path = REPO_ROOT / sample["derived_mask_path"]
    
    with rasterio.open(img_path) as src:
        raw_image = src.read(1).astype(np.float32)
        
    validity_mask = compute_validity_mask(raw_image)
    norm_image, _ = preprocess_sar_image(raw_image, mean=TRAIN_LOG1P_MEAN, std=TRAIN_LOG1P_STD)
    raw_mask = np.array(Image.open(mask_path), dtype=np.int64)
    target = remap_source_mask_to_dense(raw_mask, validity_mask=validity_mask)
    
    # Shapes: input [1, 256, 256], target [256, 256], valid [1, 256, 256]
    input_t = torch.from_numpy(norm_image).float()
    target_t = torch.from_numpy(target).long()
    valid_t = torch.from_numpy(validity_mask).bool()
    return input_t, target_t, valid_t


def extract_gradient_norms(model: nn.Module) -> Tuple[float, Dict[str, float]]:
    """Extract global and layer-wise L2 gradient norms from model parameters."""
    layer_norms: Dict[str, float] = {}
    all_grads = []
    
    for target in PRE_REGISTERED_LAYER_TARGETS:
        target_grads = []
        for name, param in model.named_parameters():
            if name.startswith(target) and param.grad is not None:
                target_grads.append(param.grad.detach().flatten())
        if target_grads:
            norm_val = torch.norm(torch.cat(target_grads), p=2).item()
            layer_norms[target] = float(norm_val)
        else:
            layer_norms[target] = 0.0
            
    for param in model.parameters():
        if param.grad is not None:
            all_grads.append(param.grad.detach().flatten())
            
    if all_grads:
        global_norm = float(torch.norm(torch.cat(all_grads), p=2).item())
    else:
        global_norm = 0.0
        
    return global_norm, layer_norms


def extract_gradient_vector(model: nn.Module) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
    """Extract detached flattened gradient vector globally and per layer target."""
    layer_vectors: Dict[str, torch.Tensor] = {}
    all_grads = []
    
    for target in PRE_REGISTERED_LAYER_TARGETS:
        target_grads = []
        for name, param in model.named_parameters():
            if name.startswith(target) and param.grad is not None:
                target_grads.append(param.grad.detach().flatten())
        if target_grads:
            layer_vectors[target] = torch.cat(target_grads)
        else:
            layer_vectors[target] = torch.zeros(1)
            
    for param in model.parameters():
        if param.grad is not None:
            all_grads.append(param.grad.detach().flatten())
            
    if all_grads:
        global_vector = torch.cat(all_grads)
    else:
        global_vector = torch.zeros(1)
        
    return global_vector, layer_vectors


def compute_vector_cosine_similarity(v1: torch.Tensor, v2: torch.Tensor, eps: float = 1e-12) -> float:
    """Compute cosine similarity between two 1D gradient vectors."""
    n1 = torch.norm(v1, p=2)
    n2 = torch.norm(v2, p=2)
    if n1 <= eps or n2 <= eps:
        return 0.0
    cos_val = torch.dot(v1, v2) / (n1 * n2)
    return float(torch.clamp(cos_val, -1.0, 1.0).item())


def execute_tier1_static_gradient_profiling() -> Dict[str, Any]:
    """Execute complete Tier-1 Static Gradient Profiling protocol (H1 + H2)."""
    start_time = time.time()
    iso_start = datetime.now(timezone.utc).isoformat()
    
    # 1. Enforce Pre-Execution Authorization & Integrity Gates
    assert_execution_authorized()
    chk_meta = verify_checkpoint_integrity()
    man_meta = verify_dataset_manifest_integrity()
    cen_meta = verify_h2_population_census()
    env_meta = verify_compute_envelope_limits()
    
    # Scientific counters initialized to 0
    counters = {
        "backward_passes": 0,
        "optimizer_steps": 0,
        "scheduler_steps": 0,
        "parameter_updates": 0,
        "training_steps": 0,
        "gpu_seconds": 0.0,
        "holdout_access_count": 0,
        "part_iii_access_count": 0,
    }
    
    # Device: strictly CPU
    device = torch.device("cpu")
    
    # Initialize Model & Load Canonical Checkpoint
    model = ResNet18UNet(in_channels=1, num_classes=12, bn_momentum=0.05).to(device)
    chk_data = torch.load(CHECKPOINT_CANONICAL_PATH, map_location=device)
    state = chk_data["model_state_dict"] if "model_state_dict" in chk_data else chk_data
    model.load_state_dict(state, strict=True)
    
    # Configure model to eval mode and verify frozen BatchNorm
    configure_h1_model_mode(model)
    
    # Record initial model parameter hash to guarantee zero parameter mutation
    with torch.no_grad():
        initial_param_bytes = b"".join(p.detach().cpu().numpy().tobytes() for p in model.parameters())
        initial_param_sha256 = hashlib.sha256(initial_param_bytes).hexdigest().upper()
        
    # Weight tensors
    w_canonical = torch.tensor(CANONICAL_CLASS_WEIGHTS, dtype=torch.float32, device=device)
    w_uniform = torch.tensor(UNIFORM_CLASS_WEIGHTS, dtype=torch.float32, device=device)
    
    # Load manifest data
    with open(MANIFEST_OPS02_PATH, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    train_samples = [s for s in manifest_data["samples"] if s.get("partition") == "TRAIN"]
    train_samples = sorted(train_samples, key=lambda s: s["sample_id"])
    assert len(train_samples) == POPULATION_B_TILES_COUNT
    
    # ==============================================================================
    # H1: Step-0 Spatial Cross-Batch Gradient-Norm Heterogeneity (33 batches, 66 passes)
    # ==============================================================================
    h1_raw_metrics = []
    
    for batch_idx in range(H1_BATCHES_COUNT):
        batch_slice = train_samples[batch_idx * H1_BATCH_SIZE : (batch_idx + 1) * H1_BATCH_SIZE]
        batch_inputs = []
        batch_targets = []
        batch_tile_ids = []
        batch_cluster_ids = []
        
        for sample in batch_slice:
            in_t, tar_t, _ = load_single_tile(sample)
            batch_inputs.append(in_t)
            batch_targets.append(tar_t)
            batch_tile_ids.append(sample["sample_id"])
            batch_cluster_ids.append(sample["parent_scene_id"])
            
        inputs = torch.stack(batch_inputs, dim=0).to(device)  # [4, 1, 256, 256]
        targets = torch.stack(batch_targets, dim=0).to(device) # [4, 256, 256]
        
        # --- Arm 1: Canonical Arm ---
        model.zero_grad(set_to_none=True)
        logits_canonical = model(inputs)
        loss_canonical = F.cross_entropy(logits_canonical, targets, weight=w_canonical, ignore_index=-100, reduction="mean")
        loss_canonical.backward()
        counters["backward_passes"] += 1
        global_norm_can, layer_norms_can = extract_gradient_norms(model)
        model.zero_grad(set_to_none=True)
        
        # --- Arm 2: Uniform Arm ---
        logits_uniform = model(inputs)
        loss_uniform = F.cross_entropy(logits_uniform, targets, weight=w_uniform, ignore_index=-100, reduction="mean")
        loss_uniform.backward()
        counters["backward_passes"] += 1
        global_norm_uni, layer_norms_uni = extract_gradient_norms(model)
        model.zero_grad(set_to_none=True)
        
        # Log-norm ratios Lambda_l = log10(norm_can) - log10(norm_uni)
        eps_floor = 1e-12
        lambda_global = float(np.log10(max(global_norm_can, eps_floor)) - np.log10(max(global_norm_uni, eps_floor)))
        layer_lambdas = {}
        for target in PRE_REGISTERED_LAYER_TARGETS:
            n_c = layer_norms_can.get(target, 0.0)
            n_u = layer_norms_uni.get(target, 0.0)
            layer_lambdas[target] = float(np.log10(max(n_c, eps_floor)) - np.log10(max(n_u, eps_floor)))
            
        h1_raw_metrics.append({
            "batch_index": batch_idx,
            "tile_ids": batch_tile_ids,
            "cluster_ids": list(set(batch_cluster_ids)),
            "canonical": {
                "loss": float(loss_canonical.item()),
                "global_gradient_norm": global_norm_can,
                "layer_gradient_norms": layer_norms_can,
            },
            "uniform": {
                "loss": float(loss_uniform.item()),
                "global_gradient_norm": global_norm_uni,
                "layer_gradient_norms": layer_norms_uni,
            },
            "log_norm_ratio_lambda": {
                "global": lambda_global,
                "layer_ratios": layer_lambdas,
            },
        })
        
    assert counters["backward_passes"] == H1_EXPECTED_BACKWARD_PASSES, f"Expected {H1_EXPECTED_BACKWARD_PASSES} H1 passes"
    
    # H1 Summary Dispersion Metrics
    def compute_dispersion(vals: Sequence[float]) -> Dict[str, float]:
        arr = np.array(vals)
        q25, q75 = np.percentile(arr, [25, 75])
        med = float(np.median(arr))
        mx = float(np.max(arr))
        mn = float(np.min(arr))
        iqr = float(q75 - q25)
        tail_ratio = float(mx / med) if med > 0 else 0.0
        return {"iqr": iqr, "median": med, "max": mx, "min": mn, "tail_ratio": tail_ratio}
        
    can_globals = [m["canonical"]["global_gradient_norm"] for m in h1_raw_metrics]
    uni_globals = [m["uniform"]["global_gradient_norm"] for m in h1_raw_metrics]
    
    h1_disp_can = compute_dispersion(can_globals)
    h1_disp_uni = compute_dispersion(uni_globals)
    
    global_iqr_ratio = float(h1_disp_can["iqr"] / h1_disp_uni["iqr"]) if h1_disp_uni["iqr"] > 0 else 0.0
    global_delta_log10_iqr = float(np.log10(max(h1_disp_can["iqr"], 1e-12)) - np.log10(max(h1_disp_uni["iqr"], 1e-12)))
    
    h1_summary = {
        "interpretation": "Spatial cross-batch heterogeneity of within-batch gradient norms at Step 0",
        "batches_evaluated": H1_BATCHES_COUNT,
        "batch_size_physical": H1_BATCH_SIZE,
        "canonical_dispersion": h1_disp_can,
        "uniform_dispersion": h1_disp_uni,
        "comparative_metrics": {
            "global_iqr_ratio": global_iqr_ratio,
            "global_delta_log10_iqr": global_delta_log10_iqr,
            "tail_ratio_contrast": float(h1_disp_can["tail_ratio"] / max(h1_disp_uni["tail_ratio"], 1e-12)),
        },
        "per_layer_dispersion": {},
    }
    for target in PRE_REGISTERED_LAYER_TARGETS:
        c_layer_vals = [m["canonical"]["layer_gradient_norms"].get(target, 0.0) for m in h1_raw_metrics]
        u_layer_vals = [m["uniform"]["layer_gradient_norms"].get(target, 0.0) for m in h1_raw_metrics]
        d_c = compute_dispersion(c_layer_vals)
        d_u = compute_dispersion(u_layer_vals)
        ratio = float(d_c["iqr"] / d_u["iqr"]) if d_u["iqr"] > 0 else 0.0
        h1_summary["per_layer_dispersion"][target] = {
            "canonical": d_c,
            "uniform": d_u,
            "iqr_ratio": ratio,
        }
        
    # ==============================================================================
    # H2: Static Step-0 Directional Gradient Geometry (28 tiles, 112 passes)
    # ==============================================================================
    eligible_samples_meta = cen_meta["eligible_samples"]
    h2_raw_observations = []
    
    for item in eligible_samples_meta:
        sample = item["sample"]
        in_t, tar_t, _ = load_single_tile(sample)
        
        inputs = in_t.unsqueeze(0).to(device)   # [1, 1, 256, 256]
        targets = tar_t.unsqueeze(0).to(device) # [1, 256, 256]
        
        valid_mask = (targets != -100)
        rare_mask = torch.isin(targets, torch.tensor(RARE_CORE_CLASSES, device=device)) & valid_mask
        common_mask = torch.isin(targets, torch.tensor(COMMON_7_CLASSES, device=device)) & valid_mask
        other_mask = torch.isin(targets, torch.tensor(OTHER_CLASSES, device=device)) & valid_mask
        
        # 1. Canonical Arm - Rare Subgradient
        model.zero_grad(set_to_none=True)
        logits = model(inputs)
        loss_rare_can, d_batch_can = compute_h2_masked_loss(logits, targets, rare_mask, w_canonical)
        loss_rare_can.backward()
        counters["backward_passes"] += 1
        g_rare_can_global, g_rare_can_layers = extract_gradient_vector(model)
        model.zero_grad(set_to_none=True)
        
        # 2. Canonical Arm - Common Subgradient
        logits = model(inputs)
        loss_common_can, _ = compute_h2_masked_loss(logits, targets, common_mask, w_canonical)
        loss_common_can.backward()
        counters["backward_passes"] += 1
        g_common_can_global, g_common_can_layers = extract_gradient_vector(model)
        model.zero_grad(set_to_none=True)
        
        # 3. Uniform Arm - Rare Subgradient
        logits = model(inputs)
        loss_rare_uni, d_batch_uni = compute_h2_masked_loss(logits, targets, rare_mask, w_uniform)
        loss_rare_uni.backward()
        counters["backward_passes"] += 1
        g_rare_uni_global, g_rare_uni_layers = extract_gradient_vector(model)
        model.zero_grad(set_to_none=True)
        
        # 4. Uniform Arm - Common Subgradient
        logits = model(inputs)
        loss_common_uni, _ = compute_h2_masked_loss(logits, targets, common_mask, w_uniform)
        loss_common_uni.backward()
        counters["backward_passes"] += 1
        g_common_uni_global, g_common_uni_layers = extract_gradient_vector(model)
        model.zero_grad(set_to_none=True)
        
        # Compute Cosine Similarities
        cos_can_global = compute_vector_cosine_similarity(g_rare_can_global, g_common_can_global)
        cos_uni_global = compute_vector_cosine_similarity(g_rare_uni_global, g_common_uni_global)
        delta_cos_global = float(cos_can_global - cos_uni_global)
        
        layer_cos_can = {}
        layer_cos_uni = {}
        layer_delta_cos = {}
        for target in PRE_REGISTERED_LAYER_TARGETS:
            c_cos = compute_vector_cosine_similarity(g_rare_can_layers[target], g_common_can_layers[target])
            u_cos = compute_vector_cosine_similarity(g_rare_uni_layers[target], g_common_uni_layers[target])
            layer_cos_can[target] = c_cos
            layer_cos_uni[target] = u_cos
            layer_delta_cos[target] = float(c_cos - u_cos)
            
        h2_raw_observations.append({
            "sample_id": sample["sample_id"],
            "parent_scene_id": sample["parent_scene_id"],
            "rare_pixel_count": int(rare_mask.sum().item()),
            "common_pixel_count": int(common_mask.sum().item()),
            "valid_pixel_count": int(valid_mask.sum().item()),
            "canonical": {
                "d_batch": float(d_batch_can.item()),
                "loss_rare": float(loss_rare_can.item()),
                "loss_common": float(loss_common_can.item()),
                "g_rare_norm": float(torch.norm(g_rare_can_global, p=2).item()),
                "g_common_norm": float(torch.norm(g_common_can_global, p=2).item()),
                "cos_sim_global": cos_can_global,
                "layer_cos_sim": layer_cos_can,
            },
            "uniform": {
                "d_batch": float(d_batch_uni.item()),
                "loss_rare": float(loss_rare_uni.item()),
                "loss_common": float(loss_common_uni.item()),
                "g_rare_norm": float(torch.norm(g_rare_uni_global, p=2).item()),
                "g_common_norm": float(torch.norm(g_common_uni_global, p=2).item()),
                "cos_sim_global": cos_uni_global,
                "layer_cos_sim": layer_cos_uni,
            },
            "delta_cos_sim_global": delta_cos_global,
            "layer_delta_cos_sim": layer_delta_cos,
        })
        
    assert counters["backward_passes"] == TOTAL_DETERMINISTIC_PASSES, (
        f"Expected total {TOTAL_DETERMINISTIC_PASSES} backward passes, executed {counters['backward_passes']}"
    )
    
    # Verify zero parameter updates occurred
    with torch.no_grad():
        final_param_bytes = b"".join(p.detach().cpu().numpy().tobytes() for p in model.parameters())
        final_param_sha256 = hashlib.sha256(final_param_bytes).hexdigest().upper()
    assert initial_param_sha256 == final_param_sha256, "Model parameter mutation detected! Parameters must remain bitwise identical."
    
    # Verify zero BatchNorm running stat updates occurred
    for name, module in model.named_modules():
        if isinstance(module, (nn.BatchNorm1d, nn.BatchNorm2d, nn.BatchNorm3d)):
            assert module.num_batches_tracked.item() == 0, f"BatchNorm layer {name} updated running stats!"
            
    # ==============================================================================
    # H2 Cluster-Level Paired Median Aggregation (15 clusters)
    # ==============================================================================
    cluster_to_obs: Dict[str, List[Dict[str, Any]]] = {}
    for obs in h2_raw_observations:
        cid = obs["parent_scene_id"]
        cluster_to_obs.setdefault(cid, []).append(obs)
        
    assert len(cluster_to_obs) == POPULATION_A_CLUSTERS_COUNT, f"Expected {POPULATION_A_CLUSTERS_COUNT} clusters"
    
    h2_cluster_summaries = []
    canonical_cluster_medians = []
    uniform_cluster_medians = []
    paired_differences = []
    
    for cid in sorted(cluster_to_obs.keys()):
        obs_list = cluster_to_obs[cid]
        c_cos_vals = [o["canonical"]["cos_sim_global"] for o in obs_list]
        u_cos_vals = [o["uniform"]["cos_sim_global"] for o in obs_list]
        
        c_med = float(np.median(c_cos_vals))
        u_med = float(np.median(u_cos_vals))
        delta_med = float(c_med - u_med)
        
        canonical_cluster_medians.append(c_med)
        uniform_cluster_medians.append(u_med)
        paired_differences.append(delta_med)
        
        layer_c_meds = {}
        layer_u_meds = {}
        layer_delta_meds = {}
        for target in PRE_REGISTERED_LAYER_TARGETS:
            c_l_vals = [o["canonical"]["layer_cos_sim"][target] for o in obs_list]
            u_l_vals = [o["uniform"]["layer_cos_sim"][target] for o in obs_list]
            c_l_m = float(np.median(c_l_vals))
            u_l_m = float(np.median(u_l_vals))
            layer_c_meds[target] = c_l_m
            layer_u_meds[target] = u_l_m
            layer_delta_meds[target] = float(c_l_m - u_l_m)
            
        h2_cluster_summaries.append({
            "parent_scene_id": cid,
            "tile_count": len(obs_list),
            "tile_ids": [o["sample_id"] for o in obs_list],
            "canonical_median_cos_sim": c_med,
            "uniform_median_cos_sim": u_med,
            "delta_median_cos_sim": delta_med,
            "layer_medians_canonical": layer_c_meds,
            "layer_medians_uniform": layer_u_meds,
            "layer_delta_medians": layer_delta_meds,
        })
        
    # ==============================================================================
    # H2 Paired Wilcoxon Signed-Rank Test (Non-parametric Inference)
    # ==============================================================================
    n_paired = len(paired_differences)
    n_zero = sum(1 for d in paired_differences if abs(d) < 1e-12)
    n_effective = n_paired - n_zero
    
    # Scipy wilcoxon paired test
    wilcox_res = scipy.stats.wilcoxon(
        canonical_cluster_medians,
        uniform_cluster_medians,
        zero_method="wilcox",
        correction=True,
        alternative="two-sided",
    )
    
    h2_paired_inference = {
        "primary_contrast": "global_full_network",
        "n_paired": n_paired,
        "n_zero": n_zero,
        "n_effective": n_effective,
        "statistic": float(wilcox_res.statistic),
        "p_value": float(wilcox_res.pvalue),
        "method": "Wilcoxon signed-rank test (asymptotic with continuity correction)",
        "alternative": "two-sided",
        "correction": True,
        "zero_method": "wilcox",
        "tie_handling": "average_ranks",
        "cluster_level_canonical_median_mean": float(np.mean(canonical_cluster_medians)),
        "cluster_level_uniform_median_mean": float(np.mean(uniform_cluster_medians)),
        "cluster_level_delta_median_mean": float(np.mean(paired_differences)),
    }
    
    # Master Consolidated Summary
    ops02_master_summary = {
        "protocol": "DIAG-05",
        "tier": "TIER_1_STATIC_GRADIENT_PROFILING",
        "status": "COMPLETED",
        "execution_timestamp": iso_start,
        "runtime_seconds": float(time.time() - start_time),
        "checkpoint_sha256": CHECKPOINT_CANONICAL_SHA256,
        "manifest_sha256": MANIFEST_OPS02_SHA256,
        "counters": counters,
        "h1_summary": h1_summary,
        "h2_paired_inference": h2_paired_inference,
        "population_counts": {
            "h1_train_tiles": POPULATION_B_TILES_COUNT,
            "h1_physical_batches": H1_BATCHES_COUNT,
            "h2_eligible_tiles": POPULATION_A_TILES_COUNT,
            "h2_parent_clusters": POPULATION_A_CLUSTERS_COUNT,
        },
    }
    
    end_time = time.time()
    elapsed = end_time - start_time
    iso_end = datetime.now(timezone.utc).isoformat()
    assert elapsed <= WALLCLOCK_LIMIT_SECONDS, f"Execution time {elapsed:.2f}s exceeded limit {WALLCLOCK_LIMIT_SECONDS}s"
    
    # Run Manifest with Hashes
    run_manifest = {
        "protocol_version": "v1.9.0-hardened",
        "task_id": "EXP-07-P0-DIAG-05-TIER1-STATIC-GRADIENT-PROFILING",
        "execution_authorized": True,
        "start_time_utc": iso_start,
        "end_time_utc": iso_end,
        "wallclock_elapsed_seconds": float(elapsed),
        "checkpoint_sha256": CHECKPOINT_CANONICAL_SHA256,
        "manifest_sha256": MANIFEST_OPS02_SHA256,
        "counters": counters,
        "artifact_hashes": {},
    }
    
    # Atomic writing of all 7 artifacts
    artifact_paths = {
        "diag05_tier1_h1_raw_metrics_v1.json": AUDIT_OUTPUT_DIR / "diag05_tier1_h1_raw_metrics_v1.json",
        "diag05_tier1_h1_summary_v1.json": AUDIT_OUTPUT_DIR / "diag05_tier1_h1_summary_v1.json",
        "diag05_tier1_h2_raw_tile_observations_v1.json": AUDIT_OUTPUT_DIR / "diag05_tier1_h2_raw_tile_observations_v1.json",
        "diag05_tier1_h2_cluster_summaries_v1.json": AUDIT_OUTPUT_DIR / "diag05_tier1_h2_cluster_summaries_v1.json",
        "diag05_tier1_h2_paired_inference_v1.json": AUDIT_OUTPUT_DIR / "diag05_tier1_h2_paired_inference_v1.json",
        "ops02_diag05_tier1_gradient_dynamics_v1.json": AUDIT_OUTPUT_DIR / "ops02_diag05_tier1_gradient_dynamics_v1.json",
    }
    
    run_manifest["artifact_hashes"]["diag05_tier1_h1_raw_metrics_v1.json"] = atomic_write_json(h1_raw_metrics, artifact_paths["diag05_tier1_h1_raw_metrics_v1.json"])
    run_manifest["artifact_hashes"]["diag05_tier1_h1_summary_v1.json"] = atomic_write_json(h1_summary, artifact_paths["diag05_tier1_h1_summary_v1.json"])
    run_manifest["artifact_hashes"]["diag05_tier1_h2_raw_tile_observations_v1.json"] = atomic_write_json(h2_raw_observations, artifact_paths["diag05_tier1_h2_raw_tile_observations_v1.json"])
    run_manifest["artifact_hashes"]["diag05_tier1_h2_cluster_summaries_v1.json"] = atomic_write_json(h2_cluster_summaries, artifact_paths["diag05_tier1_h2_cluster_summaries_v1.json"])
    run_manifest["artifact_hashes"]["diag05_tier1_h2_paired_inference_v1.json"] = atomic_write_json(h2_paired_inference, artifact_paths["diag05_tier1_h2_paired_inference_v1.json"])
    run_manifest["artifact_hashes"]["ops02_diag05_tier1_gradient_dynamics_v1.json"] = atomic_write_json(ops02_master_summary, artifact_paths["ops02_diag05_tier1_gradient_dynamics_v1.json"])
    
    # Write run manifest last with all hashes
    manifest_out_path = AUDIT_OUTPUT_DIR / "diag05_tier1_run_manifest_v1.json"
    run_manifest["artifact_hashes"]["diag05_tier1_run_manifest_v1.json"] = atomic_write_json(run_manifest, manifest_out_path)
    
    return {
        "status": "COMPLETED",
        "run_manifest": run_manifest,
        "elapsed_seconds": elapsed,
    }


def main() -> None:
    """Execution entrypoint."""
    assert_execution_authorized()
    res = execute_tier1_static_gradient_profiling()
    print("Tier-1 Static Gradient Profiling COMPLETED successfully!")
    print(f"Elapsed: {res['elapsed_seconds']:.2f}s")
    print(f"Backward passes: {res['run_manifest']['counters']['backward_passes']}")


if __name__ == "__main__":
    main()
