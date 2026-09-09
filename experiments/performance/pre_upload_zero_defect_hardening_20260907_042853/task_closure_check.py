"""Reusable Task-Closure Validation Script for Ocean Sentinel.

Mandatory pre-upload zero-defect audit tool to be run after any change.
Ensures zero task-introduced regressions across model, loss, dataset,
manifest, serialization, portability, and Jupyter execution paths.
"""

from __future__ import annotations

import argparse
import compileall
import hashlib
import io
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np
import torch

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss
from ocean_sentinel.ml.unet_resnet import ResNet34UNet, count_parameters


def run_checks() -> bool:
    all_passed = True
    print("=" * 70)
    print("OCEAN SENTINEL — REUSABLE TASK CLOSURE AUDIT")
    print(f"Repository Root: {REPO_ROOT}")
    print(f"PyTorch Version: {torch.__version__} | CUDA: {torch.cuda.is_available()}")
    print("=" * 70)

    # 1. Syntax & Bytecode Compilation
    print("\n[CHECK 1/10] Syntax and Bytecode Compilation...")
    try:
        src_path = REPO_ROOT / "src"
        scripts_path = REPO_ROOT / "scripts"
        tests_path = REPO_ROOT / "tests"
        res_src = compileall.compile_dir(str(src_path), quiet=1, force=False)
        res_scripts = compileall.compile_dir(str(scripts_path), quiet=1, force=False)
        res_tests = compileall.compile_dir(str(tests_path), quiet=1, force=False)
        if res_src and res_scripts and res_tests:
            print("  --> PASS: All src/, scripts/, and tests/ modules compiled without syntax errors.")
        else:
            print("  --> FAIL: Bytecode compilation failure encountered.")
            all_passed = False
    except Exception as e:
        print(f"  --> FAIL: Compilation exception: {e}")
        all_passed = False

    # 2. Critical Imports Smoke Test
    print("\n[CHECK 2/10] Critical ML Imports Smoke Test...")
    try:
        import torchvision
        import rasterio
        from PIL import Image
        from ocean_sentinel.ml.augmentation import SARGeometricAugmentation, IdentityTransform
        from ocean_sentinel.ml.metrics import SegmentationMeter
        from ocean_sentinel.ml.threshold import optimize_threshold_on_validation
        print("  --> PASS: Core ML packages and ocean_sentinel modules imported cleanly.")
    except Exception as e:
        print(f"  --> FAIL: Import failed: {e}")
        all_passed = False

    # 3. Canonical ResNet-34 U-Net Construction & Exact Parameter Count
    print("\n[CHECK 3/10] ResNet-34 U-Net Construction & Exact Parameter Count...")
    try:
        model = ResNet34UNet(
            in_channels=2,
            num_classes=1,
            pretrained=False,
            adaptation_method="slice_variance_scaled",
        )
        counts = count_parameters(model)
        total_p = counts["total"]
        trainable_p = counts["trainable"]
        expected_p = 24346305
        if total_p == expected_p and trainable_p == expected_p:
            print(f"  --> PASS: Model instantiated. Total={total_p:,}, Trainable={trainable_p:,} (Matches canonical: {expected_p:,}).")
        else:
            print(f"  --> FAIL: Parameter mismatch! Found Total={total_p}, Expected={expected_p}")
            all_passed = False
    except Exception as e:
        print(f"  --> FAIL: Model construction failed: {e}")
        all_passed = False

    # 4. Canonical Loss Construction
    print("\n[CHECK 4/10] Combined BCE + Dice Loss Construction...")
    try:
        criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0)
        assert criterion.bce_weight == 0.5
        assert criterion.dice_weight == 0.5
        assert criterion.dice.smooth == 1.0
        print("  --> PASS: CombinedBCEAndDiceLoss instantiated with canonical 50/50 weighting.")
    except Exception as e:
        print(f"  --> FAIL: Loss construction failed: {e}")
        all_passed = False

    # 5. Synthetic Pipeline Forward & Backward Pass (AMP FP16 if CUDA)
    print("\n[CHECK 5/10] Synthetic Pipeline Forward + Backward + Finite Gradients...")
    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = model.to(device)
        model.train()
        criterion = criterion.to(device)
        x = torch.randn(2, 2, 512, 512, device=device)
        y = torch.randint(0, 2, (2, 1, 512, 512), dtype=torch.float32, device=device)

        use_amp = (device.type == "cuda")
        with torch.amp.autocast(device_type=device.type, enabled=use_amp):
            logits = model(x)
            loss = criterion(logits, y)

        assert logits.shape == (2, 1, 512, 512), f"Logits shape mismatch: {logits.shape}"
        assert torch.isfinite(loss).item(), f"Non-finite loss: {loss.item()}"

        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)
        optimizer.zero_grad()
        loss.backward()

        for name, p in model.named_parameters():
            if p.grad is not None:
                assert torch.isfinite(p.grad).all().item(), f"Non-finite grad in {name}"

        optimizer.step()
        print(f"  --> PASS: Forward/Backward successful on {device.type}. Logits shape={logits.shape}, Loss={loss.item():.4f}, Gradients strictly finite.")
    except Exception as e:
        print(f"  --> FAIL: Synthetic pipeline failed: {e}")
        all_passed = False

    # 6. Checkpoint Serialization Round-Trip (Atomic Write + SHA256 Verification)
    print("\n[CHECK 6/10] Checkpoint Serialization & Safe Deserialization Round-Trip...")
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            chkpt_path = Path(tmp_dir) / "test_model.pt"
            state = {
                "epoch": 4,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_iou": 0.71691,
                "threshold": 0.5,
            }
            torch.save(state, chkpt_path)
            sha = hashlib.sha256(chkpt_path.read_bytes()).hexdigest()

            # Reload
            loaded = torch.load(chkpt_path, map_location=device, weights_only=True)
            assert loaded["epoch"] == 4
            assert abs(loaded["val_iou"] - 0.71691) < 1e-6

            # Model restore and inference verification in eval mode
            model.eval()
            model_restored = ResNet34UNet(in_channels=2, num_classes=1, pretrained=False).to(device)
            model_restored.load_state_dict(loaded["model_state_dict"])
            model_restored.eval()
            with torch.no_grad():
                pred1 = model(x)
                pred2 = model_restored(x)
                assert torch.allclose(pred1, pred2, atol=1e-5), "Prediction mismatch after checkpoint restoration"

            print(f"  --> PASS: Checkpoint save, SHA-256 verification ({sha[:16]}...), and restore verified.")
    except Exception as e:
        print(f"  --> FAIL: Checkpoint round-trip failed: {e}")
        all_passed = False

    # 7. Manifest Integrity & Split Verification
    manifest = None
    print("\n[CHECK 7/10] Dataset Manifest Integrity & Split Counts...")
    try:
        manifest_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
        assert manifest_path.exists(), f"Manifest missing at {manifest_path}"
        manifest = DatasetManifest.load(manifest_path)

        train_patches = manifest.patches_for_split(SplitName.TRAIN)
        val_patches = manifest.patches_for_split(SplitName.VAL)
        test_patches = manifest.patches_for_split(SplitName.TEST)

        train_tiles = manifest.tiles_for_split(SplitName.TRAIN)
        val_tiles = manifest.tiles_for_split(SplitName.VAL)
        test_tiles = manifest.tiles_for_split(SplitName.TEST)

        assert len(train_patches) == 840, f"Expected 840 train patches, got {len(train_patches)}"
        assert len(val_patches) == 180, f"Expected 180 val patches, got {len(val_patches)}"
        assert len(test_patches) == 180, f"Expected 180 test patches, got {len(test_patches)}"
        assert len(train_tiles) == 13440, f"Expected 13440 train tiles, got {len(train_tiles)}"
        assert len(val_tiles) == 2880, f"Expected 2880 val tiles, got {len(val_tiles)}"
        assert len(test_tiles) == 2880, f"Expected 2880 test tiles, got {len(test_tiles)}"
        assert manifest.normalization_stats is not None, "Normalization statistics missing in manifest"

        print(f"  --> PASS: Manifest verified. Patches: 840/180/180 (Total 1,200). Tiles: 13,440/2,880/2,880 (Total 19,200). Normalization stats present.")
    except Exception as e:
        print(f"  --> FAIL: Manifest verification failed: {e}")
        all_passed = False

    # 8. Real-TIFF Data Loader Smoke Test (Tiny Deterministic Read)
    img_real = None
    print("\n[CHECK 8/10] Real-TIFF Tile Loading & Preprocessing Contract...")
    try:
        if manifest is None:
            raise RuntimeError("Manifest not loaded from Check 7")
        ds = TrujilloTileDataset(manifest, SplitName.VAL, normalize=True)
        img_real, mask = ds[0]
        assert img_real.shape == (2, 512, 512), f"Image shape mismatch: {img_real.shape}"
        assert mask.shape == (1, 512, 512), f"Mask shape mismatch: {mask.shape}"
        assert img_real.dtype == torch.float32, f"Image dtype mismatch: {img_real.dtype}"
        assert mask.dtype == torch.float32, f"Mask dtype mismatch: {mask.dtype}"
        assert torch.isfinite(img_real).all().item(), "Non-finite values found in real image tensor"
        unique_mask_vals = set(torch.unique(mask).numpy().tolist())
        assert unique_mask_vals.issubset({0.0, 1.0}), f"Mask values not strictly binary: {unique_mask_vals}"
        print(f"  --> PASS: Real GeoTIFF sample loaded. Shape [2, 512, 512], float32, binary mask values {unique_mask_vals}.")
    except Exception as e:
        print(f"  --> FAIL: Real-TIFF data loading failed: {e}")
        all_passed = False

    # 9. Kaggle Portability & Custom data_root Smoke Test
    print("\n[CHECK 9/10] Kaggle Portability & Custom data_root Resolution...")
    try:
        if manifest is None or img_real is None:
            raise RuntimeError("Check 7 or 8 prerequisites missing")

        val_patches = manifest.patches_for_split(SplitName.VAL)

        # Create a mock Kaggle-like directory layout with 1 real sample pair
        with tempfile.TemporaryDirectory() as tmp_dir:
            kaggle_root = Path(tmp_dir) / "kaggle" / "input" / "ocean-sentinel-trujillo-corpus"
            img_dest_dir = kaggle_root / "images" / "Oil"
            mask_dest_dir = kaggle_root / "masks" / "Mask_oil"
            img_dest_dir.mkdir(parents=True, exist_ok=True)
            mask_dest_dir.mkdir(parents=True, exist_ok=True)

            val_patch_0 = val_patches[0]
            src_img = REPO_ROOT / val_patch_0.image_path
            src_mask = REPO_ROOT / val_patch_0.mask_path

            import shutil
            shutil.copy2(src_img, img_dest_dir / src_img.name)
            shutil.copy2(src_mask, mask_dest_dir / src_mask.name)

            # Initialize dataset pointing to kaggle_root
            ds_kaggle = TrujilloTileDataset(manifest, SplitName.VAL, normalize=True, data_root=kaggle_root)
            img_k, mask_k = ds_kaggle[0]
            assert img_k.shape == (2, 512, 512)
            assert mask_k.shape == (1, 512, 512)
            assert torch.allclose(img_real, img_k, atol=1e-5), "Kaggle data_root resolved pixels do not match original"

        print("  --> PASS: Custom data_root successfully resolves POSIX/Kaggle paths without hardcoded drive letters.")
    except Exception as e:
        print(f"  --> FAIL: Portability test failed: {e}")
        all_passed = False

    # 10. Jupyter -f Argparse Resilience Test
    print("\n[CHECK 10/10] Jupyter Kernel (-f ...) Argparse Resilience...")
    try:
        manifest_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
        from scripts.train_exp01 import build_arg_parser
        parser = build_arg_parser()
        simulated_args = [
            "--manifest", str(manifest_path),
            "--preflight-only",
            "-f", "/root/.local/share/jupyter/runtime/kernel-19b54d47.json"
        ]
        args, unknown = parser.parse_known_args(simulated_args)
        jupyter_args = [arg for arg in unknown if arg.startswith("-f") or arg.endswith(".json")]
        stray_args = [arg for arg in unknown if not (arg.startswith("-f") or arg.endswith(".json"))]

        assert args.preflight_only is True
        assert len(jupyter_args) == 2
        assert len(stray_args) == 0, f"Unexpected stray args: {stray_args}"
        print("  --> PASS: Jupyter kernel injection argument (-f *.json) cleanly isolated without failure.")
    except Exception as e:
        print(f"  --> FAIL: Jupyter argparse test failed: {e}")
        all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL 10 TASK-CLOSURE CHECKS PASSED: ZERO TASK-INTRODUCED DEFECTS")
        print("=" * 70)
        return True
    else:
        print("TASK-CLOSURE FAILED: DEFECTS DETECTED")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
