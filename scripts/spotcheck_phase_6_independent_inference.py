"""Independent Inference Spot-Check Evaluator for Phase 6.

Authority: Ocean Sentinel Phase 6 Final Scientific Integrity Auditor
Execution Class: Independent Methodological Cross-Verification Gate
Target: EXP-06 Best Checkpoint evaluated on a deterministic stratified subset of native Part III imagery.

Selection Rule:
DETERMINISTIC_FIRST_TWO_LEXICOGRAPHICAL_PER_STRATUM:
- Oil: Oil_00000, Oil_00001
- No oil: No oil_00000, No oil_00001
- Lookalike: Lookalike_00000, Lookalike_00001
Across both MAPPING_A and MAPPING_B (12 evaluation units total).

Core Purpose:
Eliminates the single-implementation hazard where official inference and independent verification
might share common systematic bugs in:
- Tile extraction coordinates
- Destination channel mapping
- Normalization standardization
- Logistic sigmoid application
- Mosaic assembly
- Threshold binarization

Independent Implementation Boundary:
1. Shared Primitives: Frozen model class (ResNet34UNet), normalization constants (from spatial_split_manifest.json).
2. Independent Pipeline: Custom slice generator, custom destination channel normalization,
   independent batching, custom mosaic reconstruction, independent thresholding, and direct native rasterio reading.
3. Verification: Asserts bitwise array equality against the official runner's inference output.
"""

from __future__ import annotations

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
import torch
import warnings

warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.ocean_sentinel.ml.unet_resnet import ResNet34UNet
from scripts.run_phase_6_full_evaluation import execute_scene_inference_fp32

CHECKPOINT_PATH = REPO_ROOT / "experiments/performance/exp06_positive_bce_weight/best_model.pt"
EXPECTED_CHECKPOINT_HASH = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
EXPECTED_CHECKPOINT_SIZE = 292461395

EXTRACTED_ROOT = REPO_ROOT / "data/raw/external_validation/trujillo_part_iii/extracted"
PAIRING_PATH = REPO_ROOT / "scratch/trujillo_part_iii_pairing.json"
SPLIT_MANIFEST_PATH = REPO_ROOT / "data/metadata/trujillo_2024/spatial_split_manifest.json"

FROZEN_NORM_MU0 = -33.233136989478695
FROZEN_NORM_SIGMA0 = 6.489985665955077
FROZEN_NORM_MU1 = -19.941215852796695
FROZEN_NORM_SIGMA1 = 4.531345684833188
FROZEN_THRESHOLD = 0.22


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024 * 4):
            h.update(chunk)
    return h.hexdigest().upper()


def compute_array_sha256(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest().upper()


# ==============================================================================
# Independently Implemented Inference Pipeline
# ==============================================================================

def independent_extract_tiles_and_normalize(
    image_2band: np.ndarray,
    mapping_name: str,
) -> Tuple[torch.Tensor, List[Tuple[slice, slice]]]:
    """Independent implementation of tile slicing and destination-channel normalization."""
    assert image_2band.shape == (2, 2048, 2048)
    assert image_2band.dtype == np.float32

    # Deterministic slice grid
    grid_offsets = [0, 512, 1024, 1536]
    slices = []
    tile_list = []

    for r_start in grid_offsets:
        r_slice = slice(r_start, r_start + 512)
        for c_start in grid_offsets:
            c_slice = slice(c_start, c_start + 512)
            slices.append((r_slice, c_slice))

            raw_chip = image_2band[:, r_slice, c_slice]  # (2, 512, 512)

            # Independent destination-channel assignment logic
            if mapping_name == "MAPPING_A":
                # Band 1 -> Destination Ch0 (VV norm), Band 2 -> Destination Ch1 (VH norm)
                dest_ch0 = (raw_chip[0] - FROZEN_NORM_MU0) / FROZEN_NORM_SIGMA0
                dest_ch1 = (raw_chip[1] - FROZEN_NORM_MU1) / FROZEN_NORM_SIGMA1
            elif mapping_name == "MAPPING_B":
                # Band 2 -> Destination Ch0 (VV norm), Band 1 -> Destination Ch1 (VH norm)
                dest_ch0 = (raw_chip[1] - FROZEN_NORM_MU0) / FROZEN_NORM_SIGMA0
                dest_ch1 = (raw_chip[0] - FROZEN_NORM_MU1) / FROZEN_NORM_SIGMA1
            else:
                raise ValueError(f"Invalid mapping name: {mapping_name}")

            norm_chip = np.stack([dest_ch0, dest_ch1], axis=0).astype(np.float32)
            tile_list.append(norm_chip)

    assert len(tile_list) == 16
    batch_tensor = torch.from_numpy(np.stack(tile_list, axis=0))  # (16, 2, 512, 512)
    return batch_tensor, slices


def independent_scene_inference_fp32(
    img_data: np.ndarray,
    target_mask: np.ndarray,
    mapping_name: str,
    model: torch.nn.Module,
    device: torch.device,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    """Completely independent implementation of scene-level inference."""
    batch_tensor, slice_grid = independent_extract_tiles_and_normalize(img_data, mapping_name)
    batch_tensor = batch_tensor.to(device)

    with torch.no_grad():
        logits = model(batch_tensor)  # (16, 1, 512, 512)
        assert logits.dtype == torch.float32
        probs = torch.sigmoid(logits)[:, 0, :, :].cpu().numpy().astype(np.float32)

    # Independent mosaic assembly
    prob_mosaic = np.zeros((2048, 2048), dtype=np.float32)
    for idx, (r_sl, c_sl) in enumerate(slice_grid):
        prob_mosaic[r_sl, c_sl] = probs[idx]

    # Independent binarization
    pred_mask = np.where(prob_mosaic >= FROZEN_THRESHOLD, 1, 0).astype(np.uint8)

    # Independent confusion calculation
    tp = int(np.count_nonzero((pred_mask == 1) & (target_mask == 1)))
    fp = int(np.count_nonzero((pred_mask == 1) & (target_mask == 0)))
    fn = int(np.count_nonzero((pred_mask == 0) & (target_mask == 1)))
    tn = int(np.count_nonzero((pred_mask == 0) & (target_mask == 0)))
    assert tp + fp + fn + tn == 2048 * 2048

    return prob_mosaic, pred_mask, {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


# ==============================================================================
# Spot-Check Orchestrator
# ==============================================================================

def main() -> int:
    print("=" * 80)
    print("OCEAN SENTINEL — PHASE 6 INDEPENDENT INFERENCE SPOT-CHECK EVALUATOR")
    print(f"Timestamp UTC: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print("=" * 80)

    # 1. Full Checkpoint Runtime SHA-256 Hash
    print("[CHECKPOINT] Performing independent runtime SHA-256 recalculation...", flush=True)
    assert CHECKPOINT_PATH.is_file(), f"Missing checkpoint: {CHECKPOINT_PATH}"
    sz = os.path.getsize(CHECKPOINT_PATH)
    assert sz == EXPECTED_CHECKPOINT_SIZE, f"Size mismatch: {sz} vs {EXPECTED_CHECKPOINT_SIZE}"
    runtime_chk_sha = compute_file_sha256(CHECKPOINT_PATH)
    assert runtime_chk_sha == EXPECTED_CHECKPOINT_HASH, f"Checkpoint hash mismatch: {runtime_chk_sha}"
    print(f"[CHECKPOINT] Runtime SHA-256: {runtime_chk_sha} (Size: {sz} bytes) — MATCH")

    # 2. Record Code-Path Provenance Hashes
    runner_script_path = REPO_ROOT / "scripts/run_phase_6_full_evaluation.py"
    spotcheck_script_path = REPO_ROOT / "scripts/spotcheck_phase_6_independent_inference.py"
    model_impl_path = REPO_ROOT / "src/ocean_sentinel/ml/unet_resnet.py"

    provenance_hashes = {
        "repository_head": "542bab19f6f08c9bba8b8762e6480386c8b6026b",
        "checkpoint_sha256": runtime_chk_sha,
        "official_runner_sha256": compute_file_sha256(runner_script_path) if runner_script_path.exists() else "NOT_FOUND",
        "spotcheck_evaluator_sha256": compute_file_sha256(spotcheck_script_path),
        "model_implementation_sha256": compute_file_sha256(model_impl_path),
        "spatial_split_manifest_sha256": compute_file_sha256(SPLIT_MANIFEST_PATH),
    }
    print("[PROVENANCE] Code-path file hashes recorded:")
    for k, v in provenance_hashes.items():
        print(f"  {k:32s}: {v}")

    # 3. Model Setup in FP32
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[DEVICE] Spot-check running on: {device} ({torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'})")

    torch.manual_seed(42)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(42)

    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")
    ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"], strict=True)
    model.to(device)
    model.eval()

    # 4. Load Pairing Manifest and Predeclare Selection
    with open(PAIRING_PATH, "r", encoding="utf-8") as f:
        all_pairs = json.load(f)

    # Deterministic Rule: First two lexicographical scenes per stratum
    oil_pairs = sorted([p for p in all_pairs if p["class_directory"] == "Oil"], key=lambda x: x["pair_id"])
    no_oil_pairs = sorted([p for p in all_pairs if p["class_directory"] == "No oil"], key=lambda x: x["pair_id"])
    lookalike_pairs = sorted([p for p in all_pairs if p["class_directory"] == "Lookalike"], key=lambda x: x["pair_id"])

    selected_pairs = [
        oil_pairs[0], oil_pairs[1],
        no_oil_pairs[0], no_oil_pairs[1],
        lookalike_pairs[0], lookalike_pairs[1],
    ]
    selected_pair_ids = [p["pair_id"] for p in selected_pairs]
    print(f"[SELECTION] Predeclared 6 spot-check scenes: {selected_pair_ids}")
    assert selected_pair_ids == [
        "Oil_00000", "Oil_00001",
        "No oil_00000", "No oil_00001",
        "Lookalike_00000", "Lookalike_00001",
    ]

    spotcheck_results = {}
    unit_count = 0

    for pair in selected_pairs:
        pair_id = pair["pair_id"]
        class_name = pair["class_directory"]
        img_rel = pair["image_relative_path"]
        mask_rel = pair["mask_relative_path"]

        img_p = EXTRACTED_ROOT / img_rel
        mask_p = EXTRACTED_ROOT / mask_rel

        # Read native data directly
        with rasterio.open(img_p) as src_i:
            assert src_i.count == 2
            assert src_i.width == 2048 and src_i.height == 2048
            img_data = src_i.read().astype(np.float32)

        with rasterio.open(mask_p) as src_m:
            assert src_m.width == 2048 and src_m.height == 2048
            target_mask = (src_m.read(1) > 0).astype(np.uint8)

        for mapping_name in ["MAPPING_A", "MAPPING_B"]:
            unit_key = f"{pair_id}_{mapping_name}"
            unit_count += 1
            print(f"\n[{unit_count:02d}/12] Evaluating spot-check unit: {unit_key} ({class_name})...", flush=True)

            # Flow A: Independent Implementation
            indep_prob, indep_pred, indep_counts = independent_scene_inference_fp32(
                img_data, target_mask, mapping_name, model, device
            )

            # Flow B: Official Runner Implementation
            off_prob, off_pred, off_counts = execute_scene_inference_fp32(
                img_data, target_mask, mapping_name, model, device
            )

            # Assert Bitwise Array Equivalence
            assert indep_prob.shape == (2048, 2048) and indep_prob.dtype == np.float32
            assert off_prob.shape == (2048, 2048) and off_prob.dtype == np.float32
            np.testing.assert_array_equal(
                indep_prob, off_prob, err_msg=f"Probability mosaic divergence in {unit_key}"
            )

            assert indep_pred.shape == (2048, 2048) and indep_pred.dtype == np.uint8
            assert off_pred.shape == (2048, 2048) and off_pred.dtype == np.uint8
            np.testing.assert_array_equal(
                indep_pred, off_pred, err_msg=f"Prediction mask divergence in {unit_key}"
            )

            assert indep_counts == off_counts, f"Confusion counts mismatch in {unit_key}: {indep_counts} vs {off_counts}"
            assert indep_counts["tp"] + indep_counts["fp"] + indep_counts["fn"] + indep_counts["tn"] == 2048 * 2048

            spotcheck_results[unit_key] = {
                "unit_id": unit_key,
                "pair_id": pair_id,
                "class_name": class_name,
                "mapping": mapping_name,
                "status": "EXACT_BITWISE_RECONCILED",
                "counts": indep_counts,
                "prob_sha256": compute_array_sha256(indep_prob),
                "pred_sha256": compute_array_sha256(indep_pred),
                "mask_sha256": compute_array_sha256(target_mask),
                "prob_min": float(np.min(indep_prob)),
                "prob_max": float(np.max(indep_prob)),
                "prob_mean": float(np.mean(indep_prob)),
            }
            print(f"[{unit_count:02d}/12] {unit_key} RECONCILED: counts={indep_counts}, prob_mean={np.mean(indep_prob):.5f}")

    assert unit_count == 12, f"Expected 12 units, evaluated {unit_count}"

    # Persist Complete Audit
    out_payload = {
        "audit_identifier": "PHASE_6_INDEPENDENT_INFERENCE_SPOTCHECK_20260912",
        "executed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "CERTIFIED_PASS",
        "selection_rule": "DETERMINISTIC_FIRST_TWO_LEXICOGRAPHICAL_PER_STRATUM",
        "selected_scenes": selected_pair_ids,
        "total_units_evaluated": unit_count,
        "provenance_hashes": provenance_hashes,
        "units": spotcheck_results,
    }

    out_file = REPO_ROOT / "scratch/phase_6_independent_inference_spotcheck.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out_payload, f, indent=2)

    print("\n" + "=" * 80)
    print("ALL 12 INDEPENDENT SPOT-CHECK UNITS RECONCILED WITH ZERO DIVERGENCE")
    print(f"Audit record saved: {out_file}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
