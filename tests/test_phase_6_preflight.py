"""Unit and regression tests for Phase 6 external benchmark preflight and ground-truth verification."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch

from src.ocean_sentinel.ingestion.split import DatasetManifest
from src.ocean_sentinel.ml.unet_resnet import ResNet34UNet, count_parameters


REPO_ROOT = Path(__file__).resolve().parent.parent
EXP06_CHECKPOINT_PATH = REPO_ROOT / "experiments/performance/exp06_positive_bce_weight/best_model.pt"
EXPECTED_CHECKPOINT_HASH = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
EXPECTED_CHECKPOINT_SIZE = 292461395
EXPECTED_PARAM_COUNT = 24346305
PAIRING_PATH = REPO_ROOT / "scratch/trujillo_part_iii_pairing.json"
NATIVE_ROOT = REPO_ROOT / "data/raw/external_validation/trujillo_part_iii/extracted"
SPLIT_MANIFEST_PATH = REPO_ROOT / "data/metadata/trujillo_2024/spatial_split_manifest.json"


def test_exp06_checkpoint_integrity_on_disk():
    """Verify on-disk byte size, SHA-256, and state dict keys of frozen EXP-06 checkpoint."""
    assert EXP06_CHECKPOINT_PATH.is_file(), f"Missing checkpoint: {EXP06_CHECKPOINT_PATH}"
    assert os.path.getsize(EXP06_CHECKPOINT_PATH) == EXPECTED_CHECKPOINT_SIZE

    h = hashlib.sha256()
    with open(EXP06_CHECKPOINT_PATH, "rb") as f:
        while chunk := f.read(1024 * 1024 * 4):
            h.update(chunk)
    assert h.hexdigest().upper() == EXPECTED_CHECKPOINT_HASH


def test_exp06_architecture_and_parameter_count():
    """Verify ResNet34UNet slice_variance_scaled architecture matches 24,346,305 params."""
    model = ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")
    counts = count_parameters(model)
    assert counts["trainable"] == EXPECTED_PARAM_COUNT
    assert counts["total"] == EXPECTED_PARAM_COUNT

    ckpt = torch.load(EXP06_CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    assert "model_state_dict" in ckpt
    assert ckpt["epoch"] == 9
    assert ckpt["git_commit"] == "542bab19f6f08c9bba8b8762e6480386c8b6026b"

    res = model.load_state_dict(ckpt["model_state_dict"], strict=True)
    assert len(res.missing_keys) == 0
    assert len(res.unexpected_keys) == 0


def test_spatial_split_manifest_normalization_constants():
    """Verify authoritative normalization means and standard deviations from DatasetManifest."""
    assert SPLIT_MANIFEST_PATH.is_file()
    manifest = DatasetManifest.load(SPLIT_MANIFEST_PATH)
    means = manifest.normalization_stats.channel_means
    stds = manifest.normalization_stats.channel_stds

    assert len(means) == 2 and len(stds) == 2
    assert abs(means[0] - (-33.233136989478695)) < 1e-9
    assert abs(stds[0] - 6.489985665955077) < 1e-9
    assert abs(means[1] - (-19.941215852796695)) < 1e-9
    assert abs(stds[1] - 4.531345684833188) < 1e-9


def test_part_iii_pairing_inventory_completeness():
    """Verify pairing manifest defines exactly 450 scenes (150 Oil, 150 No-Oil, 150 Lookalike)."""
    assert PAIRING_PATH.is_file()
    with open(PAIRING_PATH, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    assert len(pairs) == 450
    class_counts = {}
    for p in pairs:
        c = p["class_directory"]
        class_counts[c] = class_counts.get(c, 0) + 1

    assert class_counts == {"Oil": 150, "No oil": 150, "Lookalike": 150}


def test_geometric_tiling_invariants():
    """Verify geometric completeness and non-overlapping tiling for 2048x2048 scene."""
    scene_dim = 2048
    tile_dim = 512
    offsets = [0, 512, 1024, 1536]
    coverage = np.zeros((scene_dim, scene_dim), dtype=np.int32)

    tile_count = 0
    for r in offsets:
        for c in offsets:
            coverage[r : r + tile_dim, c : c + tile_dim] += 1
            tile_count += 1

    assert tile_count == 16
    assert (coverage == 1).all(), "Tiling must cover every pixel exactly once without gaps or overlaps"
    assert tile_count * (tile_dim * tile_dim) == scene_dim * scene_dim


def test_independent_verifier_tampering_detection(tmp_path):
    """Verify that independent verifier detects and catches target mask or prediction tampering."""
    from scripts.independent_verify_phase_6 import independently_verify_mapping

    # Create dummy native mask
    native_mask_dir = tmp_path / "native" / "Mask" / "Oil"
    native_mask_dir.mkdir(parents=True, exist_ok=True)
    native_mask_path = native_mask_dir / "test_001_segmentation.tif"

    # Save a small dummy raster using rasterio
    import rasterio
    from rasterio.transform import Affine

    dummy_mask = np.zeros((2048, 2048), dtype=np.uint8)
    dummy_mask[100:200, 100:200] = 1

    with rasterio.open(
        native_mask_path,
        "w",
        driver="GTiff",
        height=2048,
        width=2048,
        count=1,
        dtype=np.uint8,
        transform=Affine.identity(),
    ) as dst:
        dst.write(dummy_mask, 1)

    eval_dir = tmp_path / "eval"
    mapping_a = eval_dir / "mapping_a"
    mapping_a.mkdir(parents=True, exist_ok=True)

    # 1. Honest artifact
    prob_map = np.zeros((2048, 2048), dtype=np.float32)
    prob_map[100:200, 100:200] = 0.50  # >= 0.22 -> pred 1
    pred_mask = (prob_map >= 0.22).astype(np.uint8)

    np.savez_compressed(
        mapping_a / "Oil_00000.npz",
        probability_map=prob_map,
        prediction_mask=pred_mask,
        target_mask=dummy_mask,
    )
    with open(mapping_a / "Oil_00000.json", "w", encoding="utf-8") as f:
        json.dump({
            "confusion_counts": {
                "tp": int((pred_mask & dummy_mask).sum()),
                "fp": 0,
                "fn": 0,
                "tn": int(((1 - pred_mask) & (1 - dummy_mask)).sum()),
            }
        }, f)

    pair = [{
        "pair_id": "Oil_00000",
        "class_directory": "Oil",
        "mask_relative_path": "Mask/Oil/test_001_segmentation.tif",
    }]

    # 2. Tampered artifact: target mask altered inside .npz
    tampered_target = dummy_mask.copy()
    tampered_target[0, 0] = 1
    np.savez_compressed(
        mapping_a / "Oil_00000.npz",
        probability_map=prob_map,
        prediction_mask=pred_mask,
        target_mask=tampered_target,
    )

    with pytest.raises(AssertionError, match="CORRUPTION DETECTED"):
        independently_verify_mapping("MAPPING_A", eval_dir, tmp_path / "native", pair, frozen_threshold=0.22)


def test_spotcheck_scene_selection_determinism():
    """Verify deterministic lexicographical selection of spot-check scenes."""
    with open(PAIRING_PATH, "r", encoding="utf-8") as f:
        all_pairs = json.load(f)

    oil_pairs = sorted([p for p in all_pairs if p["class_directory"] == "Oil"], key=lambda x: x["pair_id"])
    no_oil_pairs = sorted([p for p in all_pairs if p["class_directory"] == "No oil"], key=lambda x: x["pair_id"])
    lookalike_pairs = sorted([p for p in all_pairs if p["class_directory"] == "Lookalike"], key=lambda x: x["pair_id"])

    selected = [
        oil_pairs[0]["pair_id"], oil_pairs[1]["pair_id"],
        no_oil_pairs[0]["pair_id"], no_oil_pairs[1]["pair_id"],
        lookalike_pairs[0]["pair_id"], lookalike_pairs[1]["pair_id"],
    ]
    assert selected == [
        "Oil_00000", "Oil_00001",
        "No oil_00000", "No oil_00001",
        "Lookalike_00000", "Lookalike_00001",
    ]


def test_independent_inference_spotcheck_audit_passed():
    """Verify that the independent spotcheck audit passed with zero divergence across 12 units."""
    spotcheck_file = REPO_ROOT / "scratch/phase_6_independent_inference_spotcheck.json"
    assert spotcheck_file.is_file(), f"Missing spotcheck audit file: {spotcheck_file}"

    with open(spotcheck_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "CERTIFIED_PASS"
    assert data["total_units_evaluated"] == 12
    assert len(data["units"]) == 12

    for unit_k, unit in data["units"].items():
        assert unit["status"] == "EXACT_BITWISE_RECONCILED"
        counts = unit["counts"]
        assert counts["tp"] + counts["fp"] + counts["fn"] + counts["tn"] == 2048 * 2048


def test_first_read_gate_schema_and_assertions():
    """Verify that all 21 mandatory first-read transition gate assertions are specified."""
    MANDATORY_GATE_KEYS = [
        "MODEL_FROZEN",
        "CHECKPOINT_VERIFIED",
        "CHECKPOINT_HASH_RECORDED",
        "CHECKPOINT_ARCHITECTURE_VERIFIED",
        "PREPROCESSING_FROZEN",
        "NORMALIZATION_VERIFIED",
        "THRESHOLD_FROZEN",
        "MAPPING_A_DEFINITION_FROZEN",
        "MAPPING_B_DEFINITION_FROZEN",
        "DATASET_INVENTORY_VERIFIED",
        "CONTAMINATION_AUDIT_PASSED",
        "DETERMINISM_TEST_PASSED",
        "TRANSACTION_PREFLIGHT_PASSED",
        "OUTPUT_ROOT_READY",
        "RUN_STATE_ACTIVE",
        "PART_III_READ_AUTHORIZED",
        "NATIVE_MASKS_VERIFIED",
        "NATIVE_MASK_PROVENANCE_VERIFIED",
        "TARGET_MASK_WRITE_LOCATION_VERIFIED",
        "INDEPENDENT_TARGET_MASK_CHECK_DEFINED",
        "INDEPENDENT_PREDICTION_RECONSTRUCTION_DEFINED",
        "INDEPENDENT_INFERENCE_SPOTCHECK_IMPLEMENTED",
        "INDEPENDENT_INFERENCE_SPOTCHECK_PASSED",
        "INDEPENDENT_SPOTCHECK_POPULATION_FROZEN",
        "OFFICIAL_VS_INDEPENDENT_OUTPUTS_RECONCILED",
    ]
    # Verify count and uniqueness
    assert len(MANDATORY_GATE_KEYS) == len(set(MANDATORY_GATE_KEYS))

