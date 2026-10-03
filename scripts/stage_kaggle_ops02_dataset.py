"""Prepare Kaggle dataset staging directory for OPS02_v1.0.0_FROZEN."""

import json
import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGING_DIR = REPO_ROOT / "scratch" / "kaggle_ops02_staging"

if STAGING_DIR.exists():
    shutil.rmtree(STAGING_DIR)
STAGING_DIR.mkdir(parents=True, exist_ok=True)

# Create subdirectories
(STAGING_DIR / "data" / "ops02" / "manifests").mkdir(parents=True, exist_ok=True)
(STAGING_DIR / "data" / "ops02" / "derived" / "images").mkdir(parents=True, exist_ok=True)
(STAGING_DIR / "data" / "ops02" / "derived" / "masks").mkdir(parents=True, exist_ok=True)

# Copy freeze spec and manifests
shutil.copy2(
    REPO_ROOT / "data" / "ops02" / "OPS02_DATASET_FREEZE_SPEC_v1.json",
    STAGING_DIR / "data" / "ops02" / "OPS02_DATASET_FREEZE_SPEC_v1.json"
)
for m_name in [
    "ops02_physical_dataset_manifest_v1.json",
    "ops02_parent_cluster_manifest_v1.json",
    "ops02_partition_manifest_v1.json"
]:
    shutil.copy2(
        REPO_ROOT / "data" / "ops02" / "manifests" / m_name,
        STAGING_DIR / "data" / "ops02" / "manifests" / m_name
    )

# Read physical manifest to copy all 212 images and 212 masks
with open(REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json", "r", encoding="utf-8") as f:
    phys = json.load(f)

samples = phys["samples"]
print(f"Staging {len(samples)} samples into {STAGING_DIR}...")

for s in samples:
    src_img = REPO_ROOT / s["derived_image_path"]
    src_mask = REPO_ROOT / s["derived_mask_path"]
    dst_img = STAGING_DIR / "data" / "ops02" / "derived" / "images" / src_img.name
    dst_mask = STAGING_DIR / "data" / "ops02" / "derived" / "masks" / src_mask.name
    shutil.copy2(src_img, dst_img)
    shutil.copy2(src_mask, dst_mask)

# Create dataset-metadata.json
metadata = {
    "title": "Ocean Sentinel OPS02 Frozen Dataset",
    "id": "dheeraj12237/ocean-sentinel-ops02-frozen",
    "licenses": [
        {
            "name": "CC-BY-4.0"
        }
    ],
    "isPrivate": True,
    "description": "Authoritative frozen OPS-02 dataset (OPS02_v1.0.0_FROZEN) for Ocean Sentinel EXP-07 multiclass SAR perception. Contains 212 sample pairs (132 TRAIN, 40 DEV, 40 HOLDOUT) across 64 independent datatake clusters.",
    "keywords": [
        "sar",
        "ocean-sentinel",
        "remote-sensing",
        "sentinel-1",
        "multiclass-segmentation"
    ]
}

with open(STAGING_DIR / "dataset-metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2)

staged_images = len(list((STAGING_DIR / "data" / "ops02" / "derived" / "images").glob("*.tif")))
staged_masks = len(list((STAGING_DIR / "data" / "ops02" / "derived" / "masks").glob("*.png")))
print(f"Staging complete: {staged_images} images, {staged_masks} masks.")
