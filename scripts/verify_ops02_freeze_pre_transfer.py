"""Verify OPS02_v1.0.0_FROZEN dataset integrity before Kaggle transfer."""

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FREEZE_SPEC = REPO_ROOT / "data" / "ops02" / "OPS02_DATASET_FREEZE_SPEC_v1.json"
PHYSICAL_MANIFEST = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"
PARTITION_MANIFEST = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_partition_manifest_v1.json"
CLUSTER_MANIFEST = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_parent_cluster_manifest_v1.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    print("=" * 80)
    print("EXP-07-P0-C16: PRE-TRANSFER INTEGRITY VERIFICATION")
    print("=" * 80)

    assert FREEZE_SPEC.exists(), "Freeze spec missing"
    with open(FREEZE_SPEC, "r", encoding="utf-8") as f:
        spec = json.load(f)

    assert spec["dataset_version"] == "OPS02_v1.0.0_FROZEN"
    assert spec["freeze_status"] == "FROZEN"
    print("[PASS] Dataset Version: OPS02_v1.0.0_FROZEN")

    with open(PHYSICAL_MANIFEST, "r", encoding="utf-8") as f:
        phys = json.load(f)
    samples = phys["samples"]
    assert len(samples) == 212, f"Expected 212 samples, got {len(samples)}"
    print(f"[PASS] Total Samples: {len(samples)} (matches spec 212)")

    with open(CLUSTER_MANIFEST, "r", encoding="utf-8") as f:
        clust = json.load(f)
    clusters = clust["clusters"]
    assert len(clusters) == 64, f"Expected 64 clusters, got {len(clusters)}"
    print(f"[PASS] Total Parent Clusters: {len(clusters)} (matches spec 64)")

    part_counts = {"TRAIN": 0, "DEV": 0, "HOLDOUT": 0}
    part_clusters = {"TRAIN": set(), "DEV": set(), "HOLDOUT": set()}
    for s in samples:
        part_counts[s["partition"]] += 1
        part_clusters[s["partition"]].add(s["cluster_id"])

    assert part_counts["TRAIN"] == 132, f"TRAIN samples: {part_counts['TRAIN']} != 132"
    assert len(part_clusters["TRAIN"]) == 40, f"TRAIN clusters: {len(part_clusters['TRAIN'])} != 40"
    assert part_counts["DEV"] == 40, f"DEV samples: {part_counts['DEV']} != 40"
    assert len(part_clusters["DEV"]) == 12, f"DEV clusters: {len(part_clusters['DEV'])} != 12"
    assert part_counts["HOLDOUT"] == 40, f"HOLDOUT samples: {part_counts['HOLDOUT']} != 40"
    assert len(part_clusters["HOLDOUT"]) == 12, f"HOLDOUT clusters: {len(part_clusters['HOLDOUT'])} != 12"
    print(f"[PASS] Partition Sample Counts: TRAIN={part_counts['TRAIN']}, DEV={part_counts['DEV']}, HOLDOUT={part_counts['HOLDOUT']}")
    print(f"[PASS] Partition Cluster Counts: TRAIN={len(part_clusters['TRAIN'])}, DEV={len(part_clusters['DEV'])}, HOLDOUT={len(part_clusters['HOLDOUT'])}")

    # Verify physical file existence and SHA-256 hashes
    print("Verifying 212 image and 212 mask SHA-256 hashes...")
    hash_mismatches = 0
    missing_files = 0
    for s in samples:
        img_p = REPO_ROOT / s["derived_image_path"]
        mask_p = REPO_ROOT / s["derived_mask_path"]

        if not img_p.exists():
            missing_files += 1
        elif sha256_file(img_p) != s["image_sha256"].upper():
            hash_mismatches += 1

        if not mask_p.exists():
            missing_files += 1
        elif sha256_file(mask_p) != s["mask_sha256"].upper():
            hash_mismatches += 1

    assert missing_files == 0, f"Missing files: {missing_files}"
    assert hash_mismatches == 0, f"Hash mismatches: {hash_mismatches}"
    print(f"[PASS] 100% SHA-256 Verified across all {len(samples)} sample pairs (0 mismatches, 0 missing).")
    print("=" * 80)
    print("PRE-TRANSFER VERIFICATION COMPLETE: READY FOR KAGGLE TRANSFER")
    print("=" * 80)


if __name__ == "__main__":
    main()
