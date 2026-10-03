"""Multi-Stratum Pre-Execution Determinism Micro-Test for Phase 6.

Authority: Ocean Sentinel Phase 6 Final Pre-Execution Scientific Integrity Auditor
Target: EXP-06 Best Checkpoint on representative Part III scenes:
- Oil: Oil_00000
- No oil: No oil_00000
- Lookalike: Lookalike_00000
Under both MAPPING_A and MAPPING_B (6 distinct execution units).

Verification Requirement:
Each unit is evaluated TWICE in FP32 mode under identical settings.
Bitwise array equality of probability mosaics, prediction masks, and confusion counts is asserted.
"""

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

CHECKPOINT_PATH = REPO_ROOT / "experiments/performance/exp06_positive_bce_weight/best_model.pt"
EXPECTED_CHECKPOINT_HASH = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
EXPECTED_CHECKPOINT_SIZE = 292461395

EXTRACTED_ROOT = REPO_ROOT / "data/raw/external_validation/trujillo_part_iii/extracted"
PAIRING_PATH = REPO_ROOT / "scratch/trujillo_part_iii_pairing.json"

FROZEN_NORM_MU0 = -33.233136989478695
FROZEN_NORM_SIGMA0 = 6.489985665955077
FROZEN_NORM_MU1 = -19.941215852796695
FROZEN_NORM_SIGMA1 = 4.531345684833188
FROZEN_THRESHOLD = 0.22

TILE_OFFSETS = [0, 512, 1024, 1536]
SCENE_DIM = 2048
TILE_DIM = 512


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024 * 4):
            h.update(chunk)
    return h.hexdigest().upper()


def run_scene_inference(
    pair: Dict[str, Any],
    mapping_name: str,
    model: torch.nn.Module,
    device: torch.device,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    img_rel = pair["image_relative_path"]
    mask_rel = pair["mask_relative_path"]
    img_p = EXTRACTED_ROOT / img_rel
    mask_p = EXTRACTED_ROOT / mask_rel

    with rasterio.open(img_p) as src_img:
        img_data = src_img.read().astype(np.float32)

    with rasterio.open(mask_p) as src_mask:
        target_mask = (src_mask.read(1) > 0).astype(np.uint8)

    tiles = []
    tile_coords = []
    for r_off in TILE_OFFSETS:
        for c_off in TILE_OFFSETS:
            tile_raw = img_data[:, r_off : r_off + TILE_DIM, c_off : c_off + TILE_DIM]
            if mapping_name == "MAPPING_A":
                ch0 = (tile_raw[0] - FROZEN_NORM_MU0) / FROZEN_NORM_SIGMA0
                ch1 = (tile_raw[1] - FROZEN_NORM_MU1) / FROZEN_NORM_SIGMA1
            elif mapping_name == "MAPPING_B":
                ch0 = (tile_raw[1] - FROZEN_NORM_MU0) / FROZEN_NORM_SIGMA0
                ch1 = (tile_raw[0] - FROZEN_NORM_MU1) / FROZEN_NORM_SIGMA1
            else:
                raise ValueError(f"Unknown mapping: {mapping_name}")
            tile_tensor = np.stack([ch0, ch1], axis=0)
            tiles.append(tile_tensor)
            tile_coords.append((r_off, c_off))

    batch_tensor = torch.from_numpy(np.stack(tiles, axis=0)).float().to(device)
    with torch.no_grad():
        logits = model(batch_tensor)
        probs = torch.sigmoid(logits).squeeze(1).cpu().numpy()

    prob_mosaic = np.zeros((SCENE_DIM, SCENE_DIM), dtype=np.float32)
    for idx, (r_off, c_off) in enumerate(tile_coords):
        prob_mosaic[r_off : r_off + TILE_DIM, c_off : c_off + TILE_DIM] = probs[idx]

    pred_mask = (prob_mosaic >= FROZEN_THRESHOLD).astype(np.uint8)

    tp = int(np.sum((pred_mask == 1) & (target_mask == 1)))
    fp = int(np.sum((pred_mask == 1) & (target_mask == 0)))
    fn = int(np.sum((pred_mask == 0) & (target_mask == 1)))
    tn = int(np.sum((pred_mask == 0) & (target_mask == 0)))

    return prob_mosaic, pred_mask, {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def main() -> int:
    print("=" * 80)
    print("OCEAN SENTINEL — MULTI-STRATUM DETERMINISM MICRO-TEST (PHASE 6 PREFLIGHT)")
    print("=" * 80)

    # 1. Checkpoint Verification
    assert CHECKPOINT_PATH.is_file(), f"Missing checkpoint: {CHECKPOINT_PATH}"
    assert os.path.getsize(CHECKPOINT_PATH) == EXPECTED_CHECKPOINT_SIZE
    runtime_hash = compute_sha256(CHECKPOINT_PATH)
    assert runtime_hash == EXPECTED_CHECKPOINT_HASH, f"Checkpoint hash mismatch: {runtime_hash}"
    print(f"[CHECKPOINT] Runtime SHA-256 verified: {runtime_hash}")

    # 2. Model Setup in FP32
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[DEVICE] Determinism test running on: {device} ({torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'})")

    torch.manual_seed(42)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(42)

    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")
    ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"], strict=True)
    model.to(device)
    model.eval()

    # 3. Load Pairing Manifest and pick one of each stratum
    with open(PAIRING_PATH, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    test_pairs = {
        "Oil": next(p for p in pairs if p["pair_id"] == "Oil_00000"),
        "No oil": next(p for p in pairs if p["pair_id"] == "No oil_00000"),
        "Lookalike": next(p for p in pairs if p["pair_id"] == "Lookalike_00000"),
    }

    test_results = {}

    for stratum, pair in test_pairs.items():
        pair_id = pair["pair_id"]
        for mapping in ["MAPPING_A", "MAPPING_B"]:
            test_key = f"{pair_id}_{mapping}"
            print(f"\n[TEST UNIT] Running dual-pass determinism for {test_key}...", flush=True)

            # Pass 1
            prob1, pred1, counts1 = run_scene_inference(pair, mapping, model, device)

            # Pass 2
            prob2, pred2, counts2 = run_scene_inference(pair, mapping, model, device)

            # Bitwise Assertions
            np.testing.assert_array_equal(prob1, prob2, err_msg=f"Probability mosaic divergence in {test_key}")
            np.testing.assert_array_equal(pred1, pred2, err_msg=f"Prediction mask divergence in {test_key}")
            assert counts1 == counts2, f"Confusion counts divergence in {test_key}: {counts1} vs {counts2}"

            test_results[test_key] = {
                "status": "DETERMINISTIC_PASS",
                "counts": counts1,
                "prob_min": float(np.min(prob1)),
                "prob_max": float(np.max(prob1)),
                "prob_mean": float(np.mean(prob1)),
                "prob_hash": compute_sha256_bytes(prob1),
            }
            print(f"[TEST UNIT] {test_key} PASSED bitwise determinism. Counts: {counts1}")

    # Persist determinism results
    out_path = REPO_ROOT / "scratch/phase_6_determinism_test_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "tested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "checkpoint_sha256": runtime_hash,
            "device": str(device),
            "status": "ALL_6_UNITS_BITWISE_DETERMINISTIC",
            "results": test_results,
        }, f, indent=2)

    print("\n" + "=" * 80)
    print("ALL 6 STRATUM/MAPPING DETERMINISM TEST UNITS PASSED WITH EXACT BITWISE EQUALITY")
    print(f"Results saved to: {out_path}")
    print("=" * 80)
    return 0


def compute_sha256_bytes(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest().upper()


if __name__ == "__main__":
    sys.exit(main())
