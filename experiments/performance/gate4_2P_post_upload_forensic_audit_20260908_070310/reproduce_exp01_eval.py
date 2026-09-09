import json
import sys
import time
from pathlib import Path
import torch
from torch.utils.data import DataLoader

REPO_ROOT = Path(r"D:\Projects\ocean-sentinel")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss
from ocean_sentinel.ml.metrics import SegmentationMeter
from ocean_sentinel.ml.unet_resnet import ResNet34UNet, count_parameters
from scripts.train_exp01 import file_sha256, safe_load_checkpoint

def main():
    audit_dir = Path(r"D:\Projects\ocean-sentinel\experiments\performance\gate4_2P_post_upload_forensic_audit_20260908_070310")
    chkpt_path = REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt"
    manifest_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"

    print("--- CANONICAL EXP01 REPRODUCTION ---")
    print(f"Checkpoint: {chkpt_path}")
    chkpt_sha = file_sha256(chkpt_path)
    print(f"Checkpoint SHA256: {chkpt_sha}")
    manifest_sha = file_sha256(manifest_path)
    print(f"Manifest SHA256: {manifest_sha}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Evaluation Device: {device}")

    # Reconstruct Model
    model = ResNet34UNet(
        in_channels=2,
        num_classes=1,
        pretrained=False,
        adaptation_method="slice_variance_scaled"
    )
    param_counts = count_parameters(model)
    print(f"Model Parameters: {param_counts}")

    # Load Checkpoint Weights
    chkpt = safe_load_checkpoint(chkpt_path, map_location=device)
    load_res = model.load_state_dict(chkpt["model_state_dict"], strict=True)
    print(f"Weights loaded: missing={len(load_res.missing_keys)}, unexpected={len(load_res.unexpected_keys)}")
    model.to(device)
    model.eval()

    # Load Manifest
    manifest = DatasetManifest.load(manifest_path)
    norm_stats = manifest.normalization_stats
    print(f"Normalization Stats: means={norm_stats.channel_means}, stds={norm_stats.channel_stds}")

    # Initialize Datasets
    val_dataset = TrujilloTileDataset(
        manifest=manifest,
        split=SplitName.VAL,
        normalize=True,
        transform=None,
    )
    test_dataset = TrujilloTileDataset(
        manifest=manifest,
        split=SplitName.TEST,
        normalize=True,
        transform=None,
    )
    print(f"Val tiles: {len(val_dataset)}, Test tiles: {len(test_dataset)}")

    val_loader = DataLoader(
        val_dataset,
        batch_size=16,
        shuffle=False,
        num_workers=4,
        pin_memory=(device.type == "cuda"),
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=16,
        shuffle=False,
        num_workers=4,
        pin_memory=(device.type == "cuda"),
    )

    criterion = CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0)
    use_amp = (device.type == "cuda")

    FROZEN_THRESHOLD = 0.22

    # 1. Evaluate VAL split at threshold 0.22
    print("\nEvaluating VAL split at frozen threshold 0.22...")
    val_meter = SegmentationMeter(threshold=FROZEN_THRESHOLD)
    val_loss_sum = 0.0
    val_n = 0
    t0 = time.time()

    with torch.no_grad():
        for imgs, masks in val_loader:
            imgs = imgs.to(device, non_blocking=True)
            masks = masks.to(device, non_blocking=True)
            with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                logits = model(imgs)
                loss = criterion(logits, masks)
            val_loss_sum += loss.item() * imgs.shape[0]
            val_n += imgs.shape[0]
            val_meter.update(logits, masks)

    val_time = time.time() - t0
    val_metrics = val_meter.compute()
    val_loss = val_loss_sum / max(1, val_n)
    val_metrics["loss"] = val_loss
    val_metrics["duration_sec"] = val_time
    print(f"VAL Results (t={val_time:.1f}s): IoU={val_metrics['iou']:.5f}, Dice={val_metrics['dice']:.5f}, Prec={val_metrics['precision']:.5f}, Recall={val_metrics['recall']:.5f}, Loss={val_loss:.5f}")

    # 2. Evaluate TEST split at threshold 0.22
    print("\nEvaluating TEST split at frozen threshold 0.22...")
    test_meter = SegmentationMeter(threshold=FROZEN_THRESHOLD)
    test_loss_sum = 0.0
    test_n = 0
    t1 = time.time()

    with torch.no_grad():
        for imgs, masks in test_loader:
            imgs = imgs.to(device, non_blocking=True)
            masks = masks.to(device, non_blocking=True)
            with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                logits = model(imgs)
                loss = criterion(logits, masks)
            test_loss_sum += loss.item() * imgs.shape[0]
            test_n += imgs.shape[0]
            test_meter.update(logits, masks)

    test_time = time.time() - t1
    test_metrics = test_meter.compute()
    test_loss = test_loss_sum / max(1, test_n)
    test_metrics["loss"] = test_loss
    test_metrics["duration_sec"] = test_time
    print(f"TEST Results (t={test_time:.1f}s): IoU={test_metrics['iou']:.5f}, Dice={test_metrics['dice']:.5f}, Prec={test_metrics['precision']:.5f}, Recall={test_metrics['recall']:.5f}, Loss={test_loss:.5f}")

    # Certified reference comparison
    certified = {
        "val_iou": 0.72231,
        "test_iou": 0.78434,
        "test_dice": 0.87914,
        "test_precision": 0.81713,
        "test_recall": 0.95133,
    }

    comparison = {
        "val_iou_diff": val_metrics["iou"] - certified["val_iou"],
        "test_iou_diff": test_metrics["iou"] - certified["test_iou"],
        "test_dice_diff": test_metrics["dice"] - certified["test_dice"],
        "test_precision_diff": test_metrics["precision"] - certified["test_precision"],
        "test_recall_diff": test_metrics["recall"] - certified["test_recall"],
    }

    print("\n--- COMPARISON WITH CERTIFIED EXP01 VALUES ---")
    print(f"Val IoU:  Reproduced={val_metrics['iou']:.5f}, Certified={certified['val_iou']}, Diff={comparison['val_iou_diff']:+.6f}")
    print(f"Test IoU: Reproduced={test_metrics['iou']:.5f}, Certified={certified['test_iou']}, Diff={comparison['test_iou_diff']:+.6f}")
    print(f"Test Dice: Reproduced={test_metrics['dice']:.5f}, Certified={certified['test_dice']}, Diff={comparison['test_dice_diff']:+.6f}")
    print(f"Test Prec: Reproduced={test_metrics['precision']:.5f}, Certified={certified['test_precision']}, Diff={comparison['test_precision_diff']:+.6f}")
    print(f"Test Rec:  Reproduced={test_metrics['recall']:.5f}, Certified={certified['test_recall']}, Diff={comparison['test_recall_diff']:+.6f}")

    results_payload = {
        "checkpoint": str(chkpt_path),
        "checkpoint_sha256": chkpt_sha,
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_sha,
        "device": str(device),
        "amp_enabled": use_amp,
        "frozen_threshold": FROZEN_THRESHOLD,
        "normalization": {
            "channel_means": norm_stats.channel_means,
            "channel_stds": norm_stats.channel_stds,
            "computed_from_split": norm_stats.computed_from_split,
        },
        "adaptation_method": "slice_variance_scaled",
        "param_counts": param_counts,
        "val_evaluation": val_metrics,
        "test_evaluation": test_metrics,
        "certified_reference": certified,
        "comparison_diff": comparison,
        "reproduction_match": (
            abs(comparison["val_iou_diff"]) < 1e-4
            and abs(comparison["test_iou_diff"]) < 1e-4
        )
    }

    out_file = audit_dir / "reproduction_metrics.json"
    out_file.write_text(json.dumps(results_payload, indent=2), encoding="utf-8")
    print(f"\nSaved reproduction metrics to {out_file}")
    print(f"Reproduction match status: {results_payload['reproduction_match']}")

if __name__ == "__main__":
    main()
