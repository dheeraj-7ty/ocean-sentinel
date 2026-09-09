"""
EXP02B-0 Phase 2: Train-Only Hard-Negative Mining & RAW Distribution Audit.

Audits all 13,440 tiles from SplitName.TRAIN.
- Strictly excludes VAL (2,880) and TEST (2,880).
- Classifies tiles initially into 'eligible_gt_negative' vs 'positive_spill_tile'.
- Evaluates teacher model under strict protocol:
    model.eval(), torch.no_grad(), canonical normalization, no augmentation,
    2-channel slice_variance_scaled input, sigmoid(raw_logits), diagnostic threshold 0.22.
- Computes per-tile diagnostics: max_prob, mean_prob, fp_pixel_count, fp_fraction,
  connected-component metrics (N_cc, max_cc_area).
- Compiles raw continuous distribution tables across all eligible GT-negatives.
- Outputs candidate_manifest_raw.json and candidate_audit_raw.json.
"""

import sys
import os
import time
import json
import hashlib
from pathlib import Path

# Fix Windows pathlib unpickling
if sys.platform == "win32":
    import pathlib
    pathlib.PosixPath = pathlib.WindowsPath

import numpy as np
import torch
from torch.utils.data import DataLoader

def count_connected_components(mask: np.ndarray):
    """8-connectivity BFS connected component labeling without external dependencies."""
    H, W = mask.shape
    visited = np.zeros((H, W), dtype=bool)
    components = []
    
    pos_coords = np.argwhere(mask > 0)
    if len(pos_coords) == 0:
        return 0, 0, 0
        
    for r, c in pos_coords:
        if visited[r, c]:
            continue
        q = [(r, c)]
        visited[r, c] = True
        area = 0
        while q:
            cr, cc = q.pop()
            area += 1
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < H and 0 <= nc < W and mask[nr, nc] and not visited[nr, nc]:
                        visited[nr, nc] = True
                        q.append((nr, nc))
        components.append(area)
        
    n_cc = len(components)
    max_area = max(components) if components else 0
    mean_area = float(np.mean(components)) if components else 0.0
    return n_cc, max_area, mean_area

sys.path.insert(0, ".")
sys.path.insert(0, "./src")

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName
from ocean_sentinel.ml.unet_resnet import ResNet34UNet
from scripts.train_exp01 import safe_load_checkpoint

MANIFEST_PATH = Path("data/metadata/trujillo_2024/spatial_split_manifest.json")
TEACHER_PATH = Path("experiments/exp01_baseline/best_model.pt")
OUT_DIR = Path("experiments/performance/exp02b_0_hard_negative_design_20260909_021500")
EXPECTED_TEACHER_HASH = "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699"
EXPECTED_MANIFEST_HASH = "C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DIAGNOSTIC_THRESHOLD = 0.22


def main():
    start_time = time.time()
    print("=" * 80)
    print("EXP02B-0 PHASE 2: TRAIN-ONLY HARD-NEGATIVE MINING & RAW DISTRIBUTION AUDIT")
    print("=" * 80)
    print(f"Device: {DEVICE} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    # 1. Verify Manifest Integrity
    manifest_bytes = MANIFEST_PATH.read_bytes()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest().upper()
    assert manifest_hash == EXPECTED_MANIFEST_HASH, f"Manifest hash mismatch: {manifest_hash}"
    print(f"[PASS] Spatial split manifest hash: {manifest_hash}")

    manifest = DatasetManifest.load(MANIFEST_PATH)
    train_entries = manifest.tiles_for_split(SplitName.TRAIN)
    assert len(train_entries) == 13440, f"Expected 13440 train tiles, got {len(train_entries)}"
    print(f"[PASS] Loaded {len(train_entries)} canonical train tiles. (VAL and TEST strictly excluded)")

    # 2. Verify Teacher Model
    teacher_bytes = TEACHER_PATH.read_bytes()
    teacher_hash = hashlib.sha256(teacher_bytes).hexdigest().upper()
    assert teacher_hash == EXPECTED_TEACHER_HASH, f"Teacher hash mismatch: {teacher_hash}"
    print(f"[PASS] Teacher checkpoint hash: {teacher_hash}")

    chkpt = safe_load_checkpoint(TEACHER_PATH, map_location=DEVICE, expected_sha256=EXPECTED_TEACHER_HASH)
    model = ResNet34UNet(in_channels=2, num_classes=1, pretrained=False, adaptation_method="slice_variance_scaled").to(DEVICE)
    model.load_state_dict(chkpt["model_state_dict"], strict=True)
    model.eval()
    print("[PASS] Teacher model initialized in model.eval() mode.")

    # 3. Construct Train Dataset (unaugmented, canonical normalization)
    train_dataset = TrujilloTileDataset(manifest, SplitName.TRAIN, normalize=True)
    train_loader = DataLoader(
        train_dataset,
        batch_size=32,
        shuffle=False,
        num_workers=2,
        pin_memory=True,
        drop_last=False,
    )
    print(f"[INFO] DataLoader constructed: batch_size=32, {len(train_loader)} batches total.")

    # 4. Mine Candidates Across All 13,440 Training Tiles
    print("\n[INFO] Starting inference and diagnostic extraction across all train tiles...")
    records = []
    tile_idx = 0
    batch_idx = 0
    t0_infer = time.time()

    total_gt_negative = 0
    total_positive_spill = 0
    total_fp_tiles = 0

    with torch.no_grad():
        for images, masks in train_loader:
            batch_size = images.size(0)
            images = images.to(DEVICE, non_blocking=True)
            # Forward pass
            logits = model(images)
            probs = torch.sigmoid(logits)

            # Bring to CPU for per-tile diagnostics
            probs_cpu = probs.squeeze(1).cpu().numpy()  # (B, 512, 512)
            masks_cpu = masks.squeeze(1).cpu().numpy()  # (B, 512, 512)

            for b in range(batch_size):
                entry = train_entries[tile_idx]
                gt_mask = masks_cpu[b]
                gt_pixels = int(np.sum(gt_mask > 0.5))
                is_gt_neg = (gt_pixels == 0)

                tile_record = {
                    "tile_index": tile_idx,
                    "tile_id": entry.tile_id,
                    "parent_stem": entry.parent_stem,
                    "group_key": entry.group_key,
                    "split": "train",
                    "row_idx": entry.row_idx,
                    "col_idx": entry.col_idx,
                    "gt_pixels": gt_pixels,
                    "is_gt_negative": is_gt_neg,
                    "initial_classification": "eligible_gt_negative" if is_gt_neg else "positive_spill_tile",
                }

                if is_gt_neg:
                    total_gt_negative += 1
                    pred_p = probs_cpu[b]
                    max_p = float(np.max(pred_p))
                    mean_p = float(np.mean(pred_p))
                    fp_bin = pred_p >= DIAGNOSTIC_THRESHOLD
                    fp_pixels = int(np.sum(fp_bin))

                    if fp_pixels > 0:
                        total_fp_tiles += 1
                        num_features, max_cc, mean_cc = count_connected_components(fp_bin)
                    else:
                        num_features = 0
                        max_cc = 0
                        mean_cc = 0.0

                    tile_record["max_prob"] = round(max_p, 6)
                    tile_record["mean_prob"] = round(mean_p, 6)
                    tile_record["fp_pixel_count"] = fp_pixels
                    tile_record["fp_fraction"] = round(fp_pixels / 262144.0, 6)
                    tile_record["n_connected_components"] = num_features
                    tile_record["max_cc_area"] = max_cc
                    tile_record["mean_cc_area"] = round(mean_cc, 2)
                else:
                    total_positive_spill += 1
                    tile_record["max_prob"] = None
                    tile_record["mean_prob"] = None
                    tile_record["fp_pixel_count"] = None
                    tile_record["fp_fraction"] = None
                    tile_record["n_connected_components"] = None
                    tile_record["max_cc_area"] = None
                    tile_record["mean_cc_area"] = None

                records.append(tile_record)
                tile_idx += 1

            batch_idx += 1
            if batch_idx % 25 == 0 or batch_idx == len(train_loader):
                elapsed = time.time() - t0_infer
                rate = tile_idx / elapsed
                print(f"  Processed {tile_idx:5d}/{len(train_entries)} tiles ({batch_idx}/{len(train_loader)} batches) | {rate:.1f} tiles/s | Elapsed: {elapsed:.1f}s")

    infer_dur = time.time() - t0_infer
    print(f"\n[PASS] Completed mining across {len(records)} train tiles in {infer_dur:.2f}s ({len(records)/infer_dur:.1f} tiles/s).")
    print(f"  Eligible GT-negative tiles: {total_gt_negative} ({total_gt_negative/len(records)*100:.2f}%)")
    print(f"  Positive spill tiles:       {total_positive_spill} ({total_positive_spill/len(records)*100:.2f}%)")
    print(f"  GT-negative tiles with FP:  {total_fp_tiles} ({total_fp_tiles/total_gt_negative*100:.2f}% of negatives)")

    # 5. Compile Raw Continuous Distributions Across Eligible GT-Negatives
    print("\n[INFO] Compiling raw empirical distributions across GT-negative tiles...")
    gt_neg_records = [r for r in records if r["is_gt_negative"]]
    max_probs = [r["max_prob"] for r in gt_neg_records]
    mean_probs = [r["mean_prob"] for r in gt_neg_records]
    fp_counts = [r["fp_pixel_count"] for r in gt_neg_records]
    fp_pos_counts = [r["fp_pixel_count"] for r in gt_neg_records if r["fp_pixel_count"] > 0]
    max_ccs = [r["max_cc_area"] for r in gt_neg_records]
    max_ccs_pos = [r["max_cc_area"] for r in gt_neg_records if r["max_cc_area"] > 0]

    def calc_quantiles(arr):
        if not arr:
            return {}
        a = np.array(arr)
        return {
            "min": float(np.min(a)),
            "p10": float(np.percentile(a, 10)),
            "p25": float(np.percentile(a, 25)),
            "p50": float(np.percentile(a, 50)),
            "p75": float(np.percentile(a, 75)),
            "p90": float(np.percentile(a, 90)),
            "p95": float(np.percentile(a, 95)),
            "p99": float(np.percentile(a, 99)),
            "max": float(np.max(a)),
            "mean": float(np.mean(a)),
            "std": float(np.std(a)),
        }

    max_prob_dist = calc_quantiles(max_probs)
    mean_prob_dist = calc_quantiles(mean_probs)
    fp_count_all_dist = calc_quantiles(fp_counts)
    fp_count_pos_dist = calc_quantiles(fp_pos_counts)
    max_cc_pos_dist = calc_quantiles(max_ccs_pos)

    # Threshold area frequencies
    area_freqs = {
        "fp_gte_1": len([c for c in fp_counts if c >= 1]),
        "fp_gte_10": len([c for c in fp_counts if c >= 10]),
        "fp_gte_50": len([c for c in fp_counts if c >= 50]),
        "fp_gte_100": len([c for c in fp_counts if c >= 100]),
        "fp_gte_500": len([c for c in fp_counts if c >= 500]),
        "fp_gte_1000": len([c for c in fp_counts if c >= 1000]),
        "fp_gte_5000": len([c for c in fp_counts if c >= 5000]),
        "fp_gte_10000": len([c for c in fp_counts if c >= 10000]),
    }

    # Parent patch concentration audit
    patch_fp_counts = {}
    patch_neg_counts = {}
    for r in gt_neg_records:
        p_stem = r["parent_stem"]
        patch_neg_counts[p_stem] = patch_neg_counts.get(p_stem, 0) + 1
        if r["fp_pixel_count"] > 0:
            patch_fp_counts[p_stem] = patch_fp_counts.get(p_stem, 0) + 1

    patch_fp_rates = [
        {"parent_stem": stem, "neg_tiles": patch_neg_counts[stem], "fp_tiles": patch_fp_counts.get(stem, 0), "fp_rate": round(patch_fp_counts.get(stem, 0) / patch_neg_counts[stem], 4)}
        for stem in patch_neg_counts
    ]
    patch_fp_rates.sort(key=lambda x: x["fp_tiles"], reverse=True)

    # Teacher-population diagnostic
    teacher_diag = {
        "limitation_statement": (
            "Hard-negative candidates are mined from teacher inferences on the teacher's own training population. "
            "Because the teacher was trained on these tiles, low false-positive rates on training negatives may reflect "
            "training-set memorization. Conversely, persistent false positives on training negatives indicate severe "
            "lookalike features, high radar clutter, or unmodeled ocean backscatter ambiguity that survived 30 epochs of optimization."
        ),
        "total_parent_patches_with_negatives": len(patch_neg_counts),
        "parent_patches_with_any_fp": len([p for p in patch_fp_rates if p["fp_tiles"] > 0]),
        "parent_patches_with_all_fp": len([p for p in patch_fp_rates if p["fp_rate"] == 1.0]),
        "top_10_fp_concentrated_patches": patch_fp_rates[:10],
    }

    # Summary audit document
    audit_summary = {
        "phase": "EXP02B-0_PHASE_2",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_split": "train_only",
        "total_train_tiles": len(records),
        "eligible_gt_negative_tiles": total_gt_negative,
        "eligible_gt_negative_pct": round(total_gt_negative / len(records) * 100, 2),
        "positive_spill_tiles": total_positive_spill,
        "positive_spill_pct": round(total_positive_spill / len(records) * 100, 2),
        "diagnostic_threshold": DIAGNOSTIC_THRESHOLD,
        "zero_fp_tiles": total_gt_negative - total_fp_tiles,
        "zero_fp_pct": round((total_gt_negative - total_fp_tiles) / total_gt_negative * 100, 2),
        "any_fp_tiles": total_fp_tiles,
        "any_fp_pct": round(total_fp_tiles / total_gt_negative * 100, 2),
        "max_prob_distribution": max_prob_dist,
        "mean_prob_distribution": mean_prob_dist,
        "fp_pixel_count_all_negatives": fp_count_all_dist,
        "fp_pixel_count_pos_only": fp_count_pos_dist,
        "max_connected_component_pos_only": max_cc_pos_dist,
        "fp_area_frequencies": area_freqs,
        "teacher_population_diagnostic": teacher_diag,
        "status": "PASS",
    }

    # Save outputs
    out_manifest = OUT_DIR / "candidate_manifest_raw.json"
    out_manifest.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"\n[INFO] Saved raw candidate manifest to: {out_manifest}")

    out_audit = OUT_DIR / "candidate_audit_raw.json"
    out_audit.write_text(json.dumps(audit_summary, indent=2), encoding="utf-8")
    print(f"[INFO] Saved raw candidate audit to: {out_audit}")

    print("\n" + "=" * 80)
    print("PHASE 2 SUMMARY FACTS:")
    print(f"  Total Train Tiles Audited:           {len(records):,}")
    print(f"  Eligible GT-Negative Tiles:         {total_gt_negative:,} ({total_gt_negative/len(records)*100:.2f}%)")
    print(f"  Positive Oil Spill Tiles:           {total_positive_spill:,} ({total_positive_spill/len(records)*100:.2f}%)")
    print(f"  GT-Negatives with ZERO FP:          {total_gt_negative - total_fp_tiles:,} ({(total_gt_negative - total_fp_tiles)/total_gt_negative*100:.2f}%)")
    print(f"  GT-Negatives with ANY FP (>=1 px):   {total_fp_tiles:,} ({total_fp_tiles/total_gt_negative*100:.2f}%)")
    print(f"  GT-Negatives with FP >= 100 px:      {area_freqs['fp_gte_100']:,} ({area_freqs['fp_gte_100']/total_gt_negative*100:.2f}%)")
    print(f"  GT-Negatives with FP >= 1000 px:     {area_freqs['fp_gte_1000']:,} ({area_freqs['fp_gte_1000']/total_gt_negative*100:.2f}%)")
    print(f"  Max FP Area Observed in Single Tile: {max_prob_dist.get('max')} max_prob, {max_cc_pos_dist.get('max')} max_cc px")
    print("=" * 80)


if __name__ == "__main__":
    main()
