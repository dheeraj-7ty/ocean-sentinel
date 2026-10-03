"""EXP-07-P0-DIAG-03: Radiometric Feature Discriminability Diagnostic Analysis Script.

Deterministic, learning-free scientific diagnostic evaluating the canonical EXP-07
radiometric input representation (AGGREGATED_RAW_DN_LOG1P_STANDARDIZED) across the
12-class Ocean Sentinel phenomenon taxonomy on authorized OPS-02 TRAIN and DEV partitions.

Governance Invariants:
- Exactly 0 training steps, 0 backward passes, 0 optimizer steps, 0 GPU seconds.
- Exactly 0 HOLDOUT access (programmatically firewalled).
- Exactly 0 Part III access.
- Canonical constants: TRAIN mu=4.424158, sigma=0.469261 (INV-06).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image
import rasterio
import scipy.ndimage as ndimage
import scipy.stats as stats
from scipy.stats import gaussian_kde

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ocean_sentinel.ingestion.firewall import assert_no_part_iii_leakage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DIAG03_ANALYSIS")

# Canonical Constants
TRAIN_LOG1P_MEAN = 4.424158
TRAIN_LOG1P_STD = 0.469261
IGNORE_INDEX = -100

DENSE_CLASSES = [
    "BG",    # 0: Background (BG)
    "AF",    # 1: Atmospheric Front (AF)
    "BS",    # 2: Biological Slicks (BS)
    "LWA",   # 3: Low Wind Area (LWA)
    "MCC",   # 4: Mesoscale Cellular Convection (MCC)
    "OF",    # 5: Ocean Front (OF)
    "POW",   # 6: Pure Oceanic Waves (POW)
    "RF",    # 7: Rain / precipitation-related phenomenon (RF)
    "WS",    # 8: Wind Streaks (WS)
    "Eddy",  # 9: Eddy (Eddy)
    "IWs",   # 10: Internal Waves (IWs)
    "HM",    # 11: Artificial / Anthropogenic Objects (HM)
]

DENSE_NAMES = {
    0: "Background (BG)",
    1: "Atmospheric Front (AF)",
    2: "Biological Slicks (BS)",
    3: "Low Wind Area (LWA)",
    4: "Mesoscale Cellular Convection (MCC)",
    5: "Ocean Front (OF)",
    6: "Pure Oceanic Waves (POW)",
    7: "Rain / precipitation-related phenomenon (RF)",
    8: "Wind Streaks (WS)",
    9: "Eddy (Eddy)",
    10: "Internal Waves (IWs)",
    11: "Artificial / Anthropogenic Objects (HM)",
}

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

HIGH_PRIORITY_PAIRS = [
    (2, 3),   # BS vs LWA
    (0, 5),   # BG vs OF
    (0, 7),   # BG vs RF
    (6, 7),   # POW vs RF
    (0, 11),  # BG vs HM
    (10, 11), # IWs vs HM
]


def assert_firewall(sample: Dict[str, Any]) -> None:
    partition = sample.get("partition", "").upper()
    if partition == "HOLDOUT":
        raise PermissionError(
            f"FIREWALL VIOLATION: Attempted to access quarantined HOLDOUT sample {sample.get('sample_id')}!"
        )
    if partition not in ("TRAIN", "DEV"):
        raise PermissionError(f"Unexpected partition '{partition}' barred by firewall policy.")
    
    img_path = str(sample.get("derived_image_path", ""))
    mask_path = str(sample.get("derived_mask_path", ""))
    assert_no_part_iii_leakage(img_path)
    assert_no_part_iii_leakage(mask_path)
    if "holdout" in img_path.lower() or "holdout" in mask_path.lower():
        raise PermissionError(f"FIREWALL VIOLATION: HOLDOUT substring in path: {img_path}")


def fit_class_kde(samples: np.ndarray, seed: int = 42, max_points: int = 25000) -> Optional[gaussian_kde]:
    """Fit Gaussian KDE on class samples with reproducible sub-sampling for efficiency."""
    if len(samples) < 5:
        return None
    rng = np.random.RandomState(seed)
    if len(samples) > max_points:
        sub = rng.choice(samples, size=max_points, replace=False)
    else:
        sub = samples
    try:
        return gaussian_kde(sub)
    except Exception as e:
        logger.warning(f"KDE fitting failed: {e}")
        return None


def evaluate_kde_pdf(kde: Optional[gaussian_kde], grid: np.ndarray, dx: float) -> Optional[np.ndarray]:
    if kde is None:
        return None
    pdf = kde(grid)
    total = pdf.sum() * dx
    if total > 0:
        pdf /= total
    return pdf


def compute_ovl_from_pdfs(pdf_a: np.ndarray, pdf_b: np.ndarray, dx: float) -> float:
    """Compute 1D Overlap Coefficient between two discretized probability densities."""
    overlap = np.minimum(pdf_a, pdf_b).sum() * dx
    return float(np.clip(overlap, 0.0, 1.0))


def compute_cliffs_delta_from_samples(x_a: np.ndarray, x_b: np.ndarray, seed: int = 42) -> float:
    """Compute Cliff's Delta using exact Mann-Whitney U on stratified sub-samples if large."""
    n_a, n_b = len(x_a), len(x_b)
    if n_a == 0 or n_b == 0:
        return 0.0
    
    rng = np.random.RandomState(seed)
    max_pts = 10000
    s_a = rng.choice(x_a, size=min(n_a, max_pts), replace=False) if n_a > max_pts else x_a
    s_b = rng.choice(x_b, size=min(n_b, max_pts), replace=False) if n_b > max_pts else x_b
        
    u_stat, _ = stats.mannwhitneyu(s_a, s_b, alternative="two-sided")
    delta = (2.0 * u_stat) / (len(s_a) * len(s_b)) - 1.0
    return float(np.clip(delta, -1.0, 1.0))


def compute_wasserstein1(x_a: np.ndarray, x_b: np.ndarray) -> float:
    """Compute Wasserstein-1 distance using scipy.stats.wasserstein_distance."""
    if len(x_a) == 0 or len(x_b) == 0:
        return 0.0
    return float(stats.wasserstein_distance(x_a, x_b))


def run_diag03() -> Dict[str, Any]:
    manifest_path = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_text = f.read()
        manifest_hash = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest().upper()
        manifest = json.loads(manifest_text)

    # 1. Filter authorized samples & enforce firewall
    train_samples = []
    dev_samples = []
    holdout_quarantined_count = 0
    for s in manifest["samples"]:
        part = s.get("partition", "").upper()
        if part == "HOLDOUT":
            holdout_quarantined_count += 1
            continue  # Quarantined: completely bypassed and barred from loading
        
        assert_firewall(s)
        if part == "TRAIN":
            train_samples.append(s)
        elif part == "DEV":
            dev_samples.append(s)
        else:
            raise PermissionError(f"Unexpected partition '{part}' barred by firewall policy.")

    logger.info(
        f"Manifest partition audit: TRAIN={len(train_samples)}, DEV={len(dev_samples)}, "
        f"HOLDOUT={holdout_quarantined_count} (quarantined/unloaded)"
    )
    assert holdout_quarantined_count == 40, f"Expected 40 quarantined HOLDOUT samples, found {holdout_quarantined_count}"
    assert len(train_samples) == 132, f"Expected 132 TRAIN samples, got {len(train_samples)}"
    assert len(dev_samples) == 40, f"Expected 40 DEV samples, got {len(dev_samples)}"

    # 2. Ingestion & Feature Extraction (One-Pass Streaming)
    data_by_partition: Dict[str, Dict[int, List[Dict[str, Any]]]] = {
        "TRAIN": {c: [] for c in range(12)},
        "DEV": {c: [] for c in range(12)},
    }
    
    cluster_scene_data: Dict[str, Dict[str, Dict[int, List[np.ndarray]]]] = {
        "TRAIN": {},
        "DEV": {},
    }

    erosion_struct = np.ones((3, 3), dtype=bool)
    total_tiles = len(train_samples) + len(dev_samples)
    logger.info(f"Starting single-pass raster extraction across {total_tiles} authorized tiles...")

    for idx, sample in enumerate(train_samples + dev_samples, 1):
        part = sample["partition"]
        tile_id = sample["sample_id"]
        cluster_id = sample["cluster_id"]
        img_path = REPO_ROOT / sample["derived_image_path"]
        mask_path = REPO_ROOT / sample["derived_mask_path"]

        if cluster_id not in cluster_scene_data[part]:
            cluster_scene_data[part][cluster_id] = {c: [] for c in range(12)}

        with rasterio.open(img_path) as src:
            raw_img = src.read(1).astype(np.float32)

        mask_img = np.array(Image.open(mask_path))

        validity_mask = raw_img > 0.0
        log1p_img = np.log1p(np.maximum(raw_img, 0.0))
        std_img = (log1p_img - TRAIN_LOG1P_MEAN) / TRAIN_LOG1P_STD
        std_img[~validity_mask] = 0.0

        dense_mask = np.full(mask_img.shape, IGNORE_INDEX, dtype=np.int64)
        for src_lbl, d_lbl in SOURCE_LABEL_TO_DENSE.items():
            dense_mask[mask_img == src_lbl] = d_lbl
        dense_mask[~validity_mask] = IGNORE_INDEX

        for c in range(12):
            c_mask = (dense_mask == c)
            if not np.any(c_mask):
                continue

            c_raw = raw_img[c_mask]
            c_std = std_img[c_mask]

            c_core_mask = ndimage.binary_erosion(c_mask, structure=erosion_struct)
            c_core_std = std_img[c_core_mask] if np.any(c_core_mask) else np.array([], dtype=np.float32)

            data_by_partition[part][c].append({
                "tile_id": tile_id,
                "cluster_id": cluster_id,
                "raw": c_raw,
                "std": c_std,
                "core_std": c_core_std,
            })

            cluster_scene_data[part][cluster_id][c].append(c_std)

        if idx % 40 == 0 or idx == total_tiles:
            logger.info(f"Extracted {idx}/{total_tiles} tiles...")

    # 3. Class Support Validation & Effective K
    support_stats = {"TRAIN": {}, "DEV": {}}
    pooled_data = {"TRAIN": {}, "DEV": {}}
    all_std_values = []

    for part in ["TRAIN", "DEV"]:
        for c in range(12):
            records = data_by_partition[part][c]
            clusters = sorted(list(set(r["cluster_id"] for r in records)))
            tiles = [r["tile_id"] for r in records]
            raw_pixels = np.concatenate([r["raw"] for r in records]) if records else np.array([], dtype=np.float32)
            std_pixels = np.concatenate([r["std"] for r in records]) if records else np.array([], dtype=np.float32)
            core_std_pixels = np.concatenate([r["core_std"] for r in records if len(r["core_std"]) > 0]) if records else np.array([], dtype=np.float32)

            pooled_data[part][c] = {
                "clusters": clusters,
                "tiles": tiles,
                "raw": raw_pixels,
                "std": std_pixels,
                "core_std": core_std_pixels,
            }

            if len(std_pixels) > 0:
                all_std_values.append(std_pixels)

            raw_skew = float(stats.skew(raw_pixels)) if len(raw_pixels) > 10 else 0.0
            raw_kurt = float(stats.kurtosis(raw_pixels)) if len(raw_pixels) > 10 else 0.0

            support_stats[part][c] = {
                "class_id": c,
                "class_name": DENSE_CLASSES[c],
                "full_name": DENSE_NAMES[c],
                "tile_count": len(tiles),
                "parent_cluster_count": len(clusters),
                "valid_pixel_count": int(len(std_pixels)),
                "core_pixel_count": int(len(core_std_pixels)),
                "retained_core_fraction": float(len(core_std_pixels) / len(std_pixels)) if len(std_pixels) > 0 else 0.0,
                "raw_skewness": round(raw_skew, 4),
                "raw_kurtosis": round(raw_kurt, 4),
                "raw_quantiles": {
                    "P1": round(float(np.percentile(raw_pixels, 1)), 4) if len(raw_pixels) > 0 else None,
                    "P5": round(float(np.percentile(raw_pixels, 5)), 4) if len(raw_pixels) > 0 else None,
                    "P25": round(float(np.percentile(raw_pixels, 25)), 4) if len(raw_pixels) > 0 else None,
                    "median": round(float(np.median(raw_pixels)), 4) if len(raw_pixels) > 0 else None,
                    "P75": round(float(np.percentile(raw_pixels, 75)), 4) if len(raw_pixels) > 0 else None,
                    "P95": round(float(np.percentile(raw_pixels, 95)), 4) if len(raw_pixels) > 0 else None,
                    "P99": round(float(np.percentile(raw_pixels, 99)), 4) if len(raw_pixels) > 0 else None,
                    "IQR": round(float(np.percentile(raw_pixels, 75) - np.percentile(raw_pixels, 25)), 4) if len(raw_pixels) > 0 else None,
                    "MAD": round(float(np.median(np.abs(raw_pixels - np.median(raw_pixels)))), 4) if len(raw_pixels) > 0 else None,
                },
                "std_quantiles": {
                    "P1": round(float(np.percentile(std_pixels, 1)), 4) if len(std_pixels) > 0 else None,
                    "P5": round(float(np.percentile(std_pixels, 5)), 4) if len(std_pixels) > 0 else None,
                    "P25": round(float(np.percentile(std_pixels, 25)), 4) if len(std_pixels) > 0 else None,
                    "median": round(float(np.median(std_pixels)), 4) if len(std_pixels) > 0 else None,
                    "P75": round(float(np.percentile(std_pixels, 75)), 4) if len(std_pixels) > 0 else None,
                    "P95": round(float(np.percentile(std_pixels, 95)), 4) if len(std_pixels) > 0 else None,
                    "P99": round(float(np.percentile(std_pixels, 99)), 4) if len(std_pixels) > 0 else None,
                    "IQR": round(float(np.percentile(std_pixels, 75) - np.percentile(std_pixels, 25)), 4) if len(std_pixels) > 0 else None,
                    "MAD": round(float(np.median(np.abs(std_pixels - np.median(std_pixels)))), 4) if len(std_pixels) > 0 else None,
                },
            }

    # 4. Determine Dynamic Support Bounds & Tail Mass Safeguard
    flat_all_std = np.concatenate(all_std_values)
    # Use percentiles 0.001 to 99.999 plus generous margin to ensure tail mass < 1e-4
    s_min = float(np.percentile(flat_all_std, 0.001)) - 0.5
    s_max = float(np.percentile(flat_all_std, 99.999)) + 0.5
    
    # Check tail mass discard for all classes and expand support if necessary
    tail_mass_results = {}
    for part in ["TRAIN", "DEV"]:
        tail_mass_results[part] = {}
        for c in range(12):
            std_p = pooled_data[part][c]["std"]
            if len(std_p) == 0:
                tail_mass_results[part][c] = 0.0
                continue
            discarded = float(np.mean((std_p < s_min) | (std_p > s_max)))
            while discarded >= 1e-4:
                s_min -= 0.5
                s_max += 0.5
                discarded = float(np.mean((std_p < s_min) | (std_p > s_max)))
            tail_mass_results[part][c] = round(discarded, 6)

    logger.info(f"Final deterministic empirical support grid: [{s_min:.4f}, {s_max:.4f}]")
    logger.info("Tail mass discard check passed (< 1e-4 for all classes in TRAIN and DEV).")

    # 5. Fit KDEs & OVL Discretization Convergence Check (256, 512, 1024 bins)
    kdes_std: Dict[str, Dict[int, Optional[gaussian_kde]]] = {"TRAIN": {}, "DEV": {}}
    kdes_raw: Dict[str, Dict[int, Optional[gaussian_kde]]] = {"TRAIN": {}, "DEV": {}}
    
    for part in ["TRAIN", "DEV"]:
        for c in range(12):
            kdes_std[part][c] = fit_class_kde(pooled_data[part][c]["std"], seed=42 + c)
            kdes_raw[part][c] = fit_class_kde(pooled_data[part][c]["raw"], seed=42 + c)

    convergence_diagnostics = {}
    for part in ["TRAIN", "DEV"]:
        convergence_diagnostics[part] = {}
        for c1, c2 in HIGH_PRIORITY_PAIRS:
            kde1 = kdes_std[part][c1]
            kde2 = kdes_std[part][c2]
            pair_key = f"{DENSE_CLASSES[c1]}_vs_{DENSE_CLASSES[c2]}"
            if kde1 is None or kde2 is None:
                convergence_diagnostics[part][pair_key] = {"status": "UNAVAILABLE_ZERO_SUPPORT"}
                continue

            ovl_res = {}
            for n_bins in [256, 512, 1024]:
                grid = np.linspace(s_min, s_max, n_bins)
                dx = grid[1] - grid[0]
                p1 = evaluate_kde_pdf(kde1, grid, dx)
                p2 = evaluate_kde_pdf(kde2, grid, dx)
                ovl_val = compute_ovl_from_pdfs(p1, p2, dx)
                ovl_res[n_bins] = ovl_val

            diff_256 = abs(ovl_res[256] - ovl_res[1024])
            diff_512 = abs(ovl_res[512] - ovl_res[1024])
            max_diff = max(diff_256, diff_512)
            
            convergence_diagnostics[part][pair_key] = {
                "ovl_256": round(ovl_res[256], 4),
                "ovl_512": round(ovl_res[512], 4),
                "ovl_1024": round(ovl_res[1024], 4),
                "max_diff": round(max_diff, 6),
                "converged": bool(max_diff < 0.01),
            }
            assert max_diff < 0.01, f"OVL convergence failed for {pair_key} in {part}: max_diff={max_diff:.6f} >= 0.01"

    logger.info("OVL numerical convergence verified (< 0.01 across 256/512/1024 bins).")

    # 6. Complete 66-Pair Matrix Evaluated at 1024 Bins
    pairwise_matrices = {"TRAIN": {}, "DEV": {}}
    eval_bins = 1024
    grid_eval = np.linspace(s_min, s_max, eval_bins)
    dx_eval = grid_eval[1] - grid_eval[0]

    for part in ["TRAIN", "DEV"]:
        # Precompute standardized PDFs on eval grid
        std_pdfs = {}
        for c in range(12):
            std_pdfs[c] = evaluate_kde_pdf(kdes_std[part][c], grid_eval, dx_eval)

        # Precompute raw PDFs on raw support
        all_raw_p = [pooled_data[part][c]["raw"] for c in range(12) if len(pooled_data[part][c]["raw"]) > 0]
        flat_raw = np.concatenate(all_raw_p) if all_raw_p else np.array([0.0, 100.0])
        r_min = max(0.0, float(np.percentile(flat_raw, 0.001)) - 1.0)
        r_max = float(np.percentile(flat_raw, 99.999)) + 5.0
        grid_raw = np.linspace(r_min, r_max, eval_bins)
        dx_raw = grid_raw[1] - grid_raw[0]
        raw_pdfs = {}
        for c in range(12):
            raw_pdfs[c] = evaluate_kde_pdf(kdes_raw[part][c], grid_raw, dx_raw)

        pairs_dict = {}
        for i in range(12):
            for j in range(i + 1, 12):
                c1_name = DENSE_CLASSES[i]
                c2_name = DENSE_CLASSES[j]
                pair_name = f"{c1_name}_vs_{c2_name}"

                p1_std = pooled_data[part][i]["std"]
                p2_std = pooled_data[part][j]["std"]
                p1_raw = pooled_data[part][i]["raw"]
                p2_raw = pooled_data[part][j]["raw"]

                pdf1_std = std_pdfs[i]
                pdf2_std = std_pdfs[j]

                if pdf1_std is None or pdf2_std is None:
                    pairs_dict[pair_name] = {
                        "class_1": c1_name, "class_2": c2_name,
                        "status": "UNAVAILABLE_ZERO_SUPPORT",
                    }
                    continue

                ovl_std = compute_ovl_from_pdfs(pdf1_std, pdf2_std, dx_eval)
                cliffs_delta = compute_cliffs_delta_from_samples(p1_std, p2_std)
                w1_dist = compute_wasserstein1(p1_std, p2_std)

                # Raw metrics for numerical consistency check
                pdf1_raw = raw_pdfs[i]
                pdf2_raw = raw_pdfs[j]
                if pdf1_raw is not None and pdf2_raw is not None:
                    ovl_raw = compute_ovl_from_pdfs(pdf1_raw, pdf2_raw, dx_raw)
                    delta_raw = compute_cliffs_delta_from_samples(p1_raw, p2_raw)
                    mono_diff = abs(ovl_std - ovl_raw)
                else:
                    ovl_raw, delta_raw, mono_diff = None, None, None

                pairs_dict[pair_name] = {
                    "class_1": c1_name,
                    "class_2": c2_name,
                    "k1": len(pooled_data[part][i]["clusters"]),
                    "k2": len(pooled_data[part][j]["clusters"]),
                    "n1": len(p1_std),
                    "n2": len(p2_std),
                    "ovl": round(ovl_std, 4),
                    "ovl_raw": round(ovl_raw, 4) if ovl_raw is not None else None,
                    "ovl_monotonic_diff": round(mono_diff, 4) if mono_diff is not None else None,
                    "cliffs_delta": round(cliffs_delta, 4),
                    "cliffs_delta_raw": round(delta_raw, 4) if delta_raw is not None else None,
                    "wasserstein_1_std": round(w1_dist, 4),
                    "interpretation": (
                        "HIGH_OVERLAP" if ovl_std >= 0.85 else
                        ("LOW_OVERLAP" if ovl_std <= 0.50 else "MODERATE_OVERLAP")
                    ),
                    "cliffs_category": (
                        "NEGLIGIBLE" if abs(cliffs_delta) < 0.147 else
                        ("SMALL" if abs(cliffs_delta) < 0.330 else
                         ("MEDIUM" if abs(cliffs_delta) < 0.474 else "LARGE"))
                    )
                }

        pairwise_matrices[part] = pairs_dict

    # 7. Acquisition-Conditioned Analysis (Within-Scene Co-occurrence)
    acquisition_conditioned_results = {}
    for c1, c2 in HIGH_PRIORITY_PAIRS:
        c1_name = DENSE_CLASSES[c1]
        c2_name = DENSE_CLASSES[c2]
        pair_key = f"{c1_name}_vs_{c2_name}"
        acquisition_conditioned_results[pair_key] = {}

        for part in ["TRAIN", "DEV"]:
            eligible_clusters = []
            within_scene_diffs = []
            
            for cluster_id, class_dict in cluster_scene_data[part].items():
                p1_cluster = np.concatenate(class_dict[c1]) if class_dict[c1] else np.array([], dtype=np.float32)
                p2_cluster = np.concatenate(class_dict[c2]) if class_dict[c2] else np.array([], dtype=np.float32)

                if len(p1_cluster) >= 20 and len(p2_cluster) >= 20:
                    med1 = float(np.median(p1_cluster))
                    med2 = float(np.median(p2_cluster))
                    diff = med1 - med2
                    eligible_clusters.append({
                        "cluster_id": cluster_id,
                        "n1": len(p1_cluster),
                        "n2": len(p2_cluster),
                        "median_diff": round(diff, 4),
                    })
                    within_scene_diffs.append(diff)

            if len(eligible_clusters) >= 2:
                status = "EVALUATED"
                agg_median_diff = round(float(np.median(within_scene_diffs)), 4)
                agg_iqr = round(float(np.percentile(within_scene_diffs, 75) - np.percentile(within_scene_diffs, 25)), 4)
            else:
                status = "INSUFFICIENT_CO_OCCURRENCE_SUPPORT"
                agg_median_diff = None
                agg_iqr = None

            acquisition_conditioned_results[pair_key][part] = {
                "status": status,
                "eligible_cluster_count": len(eligible_clusters),
                "per_cluster_contrasts": eligible_clusters,
                "aggregate_within_scene_median_diff": agg_median_diff,
                "aggregate_within_scene_iqr": agg_iqr,
            }

    # 8. Hierarchical Variance Decomposition
    variance_decomposition_results = {}
    for part in ["TRAIN", "DEV"]:
        variance_decomposition_results[part] = {}
        for c in range(12):
            c_name = DENSE_CLASSES[c]
            records = data_by_partition[part][c]
            k_cls = len(pooled_data[part][c]["clusters"])

            if k_cls < 3:
                variance_decomposition_results[part][c_name] = {
                    "k_cls": k_cls,
                    "status": "INSUFFICIENT_CLUSTER_SUPPORT",
                    "icc_scene": None,
                    "mad_ratio": None,
                }
                continue

            cluster_medians = []
            within_residuals = []
            for cluster_id in pooled_data[part][c]["clusters"]:
                c_pix = np.concatenate([r["std"] for r in records if r["cluster_id"] == cluster_id])
                c_med = float(np.median(c_pix))
                cluster_medians.append(c_med)
                within_residuals.append(c_pix - c_med)

            all_residuals = np.concatenate(within_residuals)
            var_between = float(np.var(cluster_medians, ddof=1))
            var_within = float(np.var(all_residuals, ddof=1))
            icc = var_between / (var_between + var_within) if (var_between + var_within) > 0 else 0.0

            mad_between = float(np.median(np.abs(cluster_medians - np.median(cluster_medians))))
            mad_within = float(np.median(np.abs(all_residuals - np.median(all_residuals))))
            mad_ratio = mad_between / mad_within if mad_within > 0 else 0.0

            variance_decomposition_results[part][c_name] = {
                "k_cls": k_cls,
                "status": "EVALUATED",
                "var_between_clusters": round(var_between, 4),
                "var_within_clusters": round(var_within, 4),
                "icc_scene": round(icc, 4),
                "mad_between_clusters": round(mad_between, 4),
                "mad_within_clusters": round(mad_within, 4),
                "mad_ratio": round(mad_ratio, 4),
                "interpretation": (
                    "SUBSTANTIAL_HETEROGENEITY" if icc >= 0.40 else "MODERATE_OR_LOW_HETEROGENEITY"
                ),
            }

    # 9. Core vs. Boundary Sensitivity Stratification
    core_sensitivity_results = {}
    for c1, c2 in HIGH_PRIORITY_PAIRS:
        c1_name = DENSE_CLASSES[c1]
        c2_name = DENSE_CLASSES[c2]
        pair_key = f"{c1_name}_vs_{c2_name}"
        core_sensitivity_results[pair_key] = {}

        for part in ["TRAIN", "DEV"]:
            core1 = pooled_data[part][c1]["core_std"]
            core2 = pooled_data[part][c2]["core_std"]
            tiles1 = len(set(r["tile_id"] for r in data_by_partition[part][c1] if len(r["core_std"]) > 0))
            tiles2 = len(set(r["tile_id"] for r in data_by_partition[part][c2] if len(r["core_std"]) > 0))

            full_ovl = pairwise_matrices[part][pair_key]["ovl"]

            if len(core1) >= 50 and len(core2) >= 50 and tiles1 >= 2 and tiles2 >= 2:
                kde_c1 = fit_class_kde(core1, seed=42 + c1)
                kde_c2 = fit_class_kde(core2, seed=42 + c2)
                p1_c = evaluate_kde_pdf(kde_c1, grid_eval, dx_eval)
                p2_c = evaluate_kde_pdf(kde_c2, grid_eval, dx_eval)
                core_ovl = compute_ovl_from_pdfs(p1_c, p2_c, dx_eval) if p1_c is not None and p2_c is not None else full_ovl
                core_delta = compute_cliffs_delta_from_samples(core1, core2)
                core_w1 = compute_wasserstein1(core1, core2)
                status = "EVALUATED"
                delta_ovl = round(core_ovl - full_ovl, 4)
            else:
                status = "SUPPORT_COLLAPSED_UNDER_EROSION"
                core_ovl, core_delta, core_w1, delta_ovl = None, None, None, None

            core_sensitivity_results[pair_key][part] = {
                "status": status,
                "n_core_1": len(core1),
                "n_core_2": len(core2),
                "tiles_core_1": tiles1,
                "tiles_core_2": tiles2,
                "full_ovl": full_ovl,
                "core_ovl": round(core_ovl, 4) if core_ovl is not None else None,
                "delta_ovl": delta_ovl,
                "core_cliffs_delta": round(core_delta, 4) if core_delta is not None else None,
                "core_w1": round(core_w1, 4) if core_w1 is not None else None,
            }

    # 10. Cluster-Level Block Bootstrap on TRAIN (B=1000, seed=42)
    logger.info("Executing Cluster-Level Block Bootstrap on TRAIN (B=1000, seed=42)...")
    np.random.seed(42)
    B_iterations = 1000
    all_train_clusters = sorted(list(set(s["cluster_id"] for s in train_samples)))
    assert len(all_train_clusters) == 40

    # Pre-aggregate histogram per cluster for fast bootstrap
    cluster_hists = {c: [] for c in range(12)}
    cluster_samples = {c: [] for c in range(12)}
    
    for c in range(12):
        for cid in all_train_clusters:
            matching = [r["std"] for r in data_by_partition["TRAIN"][c] if r["cluster_id"] == cid]
            pix = np.concatenate(matching) if matching else np.array([], dtype=np.float32)
            cluster_samples[c].append(pix)
            h, _ = np.histogram(pix, bins=np.linspace(s_min, s_max, eval_bins + 1))
            cluster_hists[c].append(h)

    bootstrap_results = {}
    for c1, c2 in HIGH_PRIORITY_PAIRS:
        c1_name = DENSE_CLASSES[c1]
        c2_name = DENSE_CLASSES[c2]
        pair_key = f"{c1_name}_vs_{c2_name}"

        boot_ovl = []
        boot_delta = []
        boot_w1 = []

        for b in range(B_iterations):
            sampled_indices = np.random.choice(len(all_train_clusters), size=len(all_train_clusters), replace=True)
            
            # Sum histograms for OVL
            h1_sum = sum(cluster_hists[c1][idx] for idx in sampled_indices).astype(np.float64)
            h2_sum = sum(cluster_hists[c2][idx] for idx in sampled_indices).astype(np.float64)

            tot1, tot2 = h1_sum.sum(), h2_sum.sum()
            if tot1 == 0 or tot2 == 0:
                continue

            pdf1 = h1_sum / (tot1 * dx_eval)
            pdf2 = h2_sum / (tot2 * dx_eval)
            ovl = compute_ovl_from_pdfs(pdf1, pdf2, dx_eval)
            boot_ovl.append(ovl)

            # Subsample for Delta and W1 (deterministic per resample)
            if b < 200:  # 200 reps sufficient for stable delta/w1 CI
                sub_pix1 = np.concatenate([cluster_samples[c1][idx] for idx in sampled_indices if len(cluster_samples[c1][idx]) > 0])
                sub_pix2 = np.concatenate([cluster_samples[c2][idx] for idx in sampled_indices if len(cluster_samples[c2][idx]) > 0])
                if len(sub_pix1) > 0 and len(sub_pix2) > 0:
                    delta = compute_cliffs_delta_from_samples(sub_pix1, sub_pix2, seed=b)
                    w1 = compute_wasserstein1(sub_pix1, sub_pix2)
                    boot_delta.append(delta)
                    boot_w1.append(w1)

        bootstrap_results[pair_key] = {
            "pair": pair_key,
            "iterations": len(boot_ovl),
            "effective_k1": len(pooled_data["TRAIN"][c1]["clusters"]),
            "effective_k2": len(pooled_data["TRAIN"][c2]["clusters"]),
            "ovl_observed": pairwise_matrices["TRAIN"][pair_key]["ovl"],
            "ovl_ci_95": [round(float(np.percentile(boot_ovl, 2.5)), 4), round(float(np.percentile(boot_ovl, 97.5)), 4)],
            "delta_observed": pairwise_matrices["TRAIN"][pair_key]["cliffs_delta"],
            "delta_ci_95": [round(float(np.percentile(boot_delta, 2.5)), 4), round(float(np.percentile(boot_delta, 97.5)), 4)] if boot_delta else None,
            "w1_observed": pairwise_matrices["TRAIN"][pair_key]["wasserstein_1_std"],
            "w1_ci_95": [round(float(np.percentile(boot_w1, 2.5)), 4), round(float(np.percentile(boot_w1, 97.5)), 4)] if boot_w1 else None,
            "small_k_warning": bool(min(len(pooled_data["TRAIN"][c1]["clusters"]), len(pooled_data["TRAIN"][c2]["clusters"])) <= 7),
        }

    logger.info("Cluster-level bootstrap complete.")

    # 11. Compile Output Machine-Readable Audit JSON
    audit_output = {
        "audit_version": "1.0.0",
        "task_id": "EXP-07-P0-DIAG-03",
        "investigation_id": "DIAG-03-RADIOMETRIC-FEATURE-DISCRIMINABILITY",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "manifest_path": "data/ops02/manifests/ops02_physical_dataset_manifest_v1.json",
        "manifest_sha256": manifest_hash,
        "governance": {
            "training_steps": 0,
            "backward_passes": 0,
            "optimizer_steps": 0,
            "scheduler_steps": 0,
            "parameter_updates": 0,
            "gpu_seconds": 0.0,
            "holdout_access": 0,
            "part_iii_access": 0,
            "diag05_executed": False,
            "zero_destructive_git": True,
        },
        "canonical_input_contract": {
            "name": "AGGREGATED_RAW_DN_LOG1P_STANDARDIZED",
            "polarization": "VV",
            "dimensions": [1, 256, 256],
            "train_log1p_mean": TRAIN_LOG1P_MEAN,
            "train_log1p_std": TRAIN_LOG1P_STD,
            "ignore_index": IGNORE_INDEX,
        },
        "taxonomy": {str(c): {"abbrev": DENSE_CLASSES[c], "full_name": DENSE_NAMES[c]} for c in range(12)},
        "partitions": {
            "TRAIN": {"tiles": 132, "parent_clusters": 40},
            "DEV": {"tiles": 40, "parent_clusters": 12},
            "HOLDOUT": {"tiles": 40, "parent_clusters": 12, "access_status": "STRICTLY_QUARANTINED_0_ACCESS"},
        },
        "support_statistics": support_stats,
        "numerical_safeguards": {
            "common_support": [round(s_min, 4), round(s_max, 4)],
            "tail_mass_discard": tail_mass_results,
            "convergence_diagnostics": convergence_diagnostics,
        },
        "pairwise_matrices": pairwise_matrices,
        "acquisition_conditioned_co_occurrence": acquisition_conditioned_results,
        "variance_decomposition": variance_decomposition_results,
        "core_sensitivity_stratification": core_sensitivity_results,
        "cluster_bootstrap_uncertainty_train": bootstrap_results,
        "evidence_tiers": {
            "OBSERVED": "Direct empirical distributions and 1-D density overlap metrics (OVL, Delta, W1).",
            "SUPPORTED": "Separability metrics confirmed across multiple clusters and invariant to core-erosion where K >= 5.",
            "HYPOTHESIZED": "Potential contribution of 1-D overlap to model confusion; requires DIAG-04/05 to confirm.",
            "UNKNOWN": "Causal root cause of segmentation error; effect of spatial receptive field; gradient dynamics.",
        },
    }

    output_audit_path = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_diag03_radiometric_discriminability_v1.json"
    output_audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_output, f, indent=2)

    logger.info(f"Machine-readable audit artifact written to: {output_audit_path}")
    return audit_output


if __name__ == "__main__":
    run_diag03()
