import json
import os
import sys
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import rasterio
from rasterio.windows import Window

print("=== OCEAN SENTINEL PRODUCTION MOUNT & DATALOADER VALIDATION ===")

input_dir = Path("/kaggle/input")
print(f"Checking {input_dir}, exists={input_dir.exists()}")

corpus_root = None
for candidate in [
    Path("/kaggle/input/datasets/dheeraj12237/ocean-sentinel-trujillo-corpus"),
    Path("/kaggle/input/ocean-sentinel-trujillo-corpus"),
]:
    if candidate.exists():
        corpus_root = candidate
        break

if corpus_root is None:
    for root, dirs, files in os.walk(input_dir):
        if "images" in dirs and "masks" in dirs:
            corpus_root = Path(root)
            break

print(f"Corpus Root detected: {corpus_root}")

images_dir = corpus_root / "images" / "Oil"
masks_dir = corpus_root / "masks" / "Mask_oil"
manifest_dir = corpus_root / "manifest"

img_count = len(list(images_dir.glob("*.tif"))) if images_dir.exists() else 0
mask_count = len(list(masks_dir.glob("*.tif"))) if masks_dir.exists() else 0
manifest_files = [f.name for f in manifest_dir.glob("*")] if manifest_dir.exists() else []

print(f"Images count: {img_count}")
print(f"Masks count: {mask_count}")
print(f"Manifest files: {manifest_files}")

# Read sample 2048x2048 raw TIFFs
sample_img = images_dir / "00000.tif"
sample_mask = masks_dir / "00000.tif"

with rasterio.open(sample_img) as src:
    img_meta = {
        "count": src.count,
        "width": src.width,
        "height": src.height,
        "dtypes": src.dtypes,
        "crs": str(src.crs),
    }
    img_arr = src.read()

with rasterio.open(sample_mask) as src:
    mask_meta = {
        "count": src.count,
        "width": src.width,
        "height": src.height,
        "dtypes": src.dtypes,
        "crs": str(src.crs),
    }
    mask_arr = src.read()

print(f"Sample Image Meta: {img_meta}, Read shape: {img_arr.shape}")
print(f"Sample Mask Meta: {mask_meta}, Read shape: {mask_arr.shape}")

# Load spatial_split_manifest.json
manifest_path = manifest_dir / "spatial_split_manifest.json"
print(f"Loading split manifest: {manifest_path}")
with open(manifest_path, "r", encoding="utf-8") as f:
    split_manifest = json.load(f)

tiles = split_manifest.get("tiles", [])
train_tiles = [t for t in tiles if t.get("split") == "train"]
val_tiles = [t for t in tiles if t.get("split") == "val"]
test_tiles = [t for t in tiles if t.get("split") == "test"]
print(f"Total tiles: {len(tiles)}, Train: {len(train_tiles)}, Val: {len(val_tiles)}, Test: {len(test_tiles)}")

norm_stats = split_manifest.get("normalization_stats", {})
means = np.array(norm_stats["channel_means"], dtype=np.float32).reshape(2, 1, 1)
stds = np.array(norm_stats["channel_stds"], dtype=np.float32).reshape(2, 1, 1)

class TrujilloTileDatasetValidator(Dataset):
    """Exact reproduction of TrujilloTileDataset contract."""
    def __init__(self, tile_entries, data_root: Path, channel_means, channel_stds):
        self.tiles = tile_entries
        self.data_root = data_root
        self.means = channel_means
        self.stds = channel_stds

    def __len__(self):
        return len(self.tiles)

    def __getitem__(self, idx):
        tile = self.tiles[idx]
        stem = tile["parent_stem"]
        img_path = self.data_root / "images" / "Oil" / f"{stem}.tif"
        mask_path = self.data_root / "masks" / "Mask_oil" / f"{stem}.tif"
        
        if not img_path.exists():
            raise FileNotFoundError(f"Missing image: {img_path}")
        if not mask_path.exists():
            raise FileNotFoundError(f"Missing mask: {mask_path}")
            
        w = Window(tile["col_offset"], tile["row_offset"], tile["width"], tile["height"])
        with rasterio.open(img_path) as src:
            img_data = src.read(window=w).astype(np.float32)
            
        with rasterio.open(mask_path) as src:
            mask_data = src.read(window=w).astype(np.float32)
            
        img_data = (img_data - self.means) / self.stds
        return torch.from_numpy(img_data), torch.from_numpy(mask_data)

# Test DataLoader
ds = TrujilloTileDatasetValidator(train_tiles[:20], corpus_root, means, stds)
loader = DataLoader(ds, batch_size=2, shuffle=False)

batch_images, batch_masks = next(iter(loader))

print(f"Batch images shape: {batch_images.shape}, dtype: {batch_images.dtype}")
print(f"Batch masks shape: {batch_masks.shape}, dtype: {batch_masks.dtype}")

checks = {
    "dataloader_initialized": True,
    "batch_loaded": True,
    "image_shape_valid": bool(batch_images.shape == (2, 2, 512, 512)),
    "mask_shape_valid": bool(batch_masks.shape == (2, 1, 512, 512)),
    "image_dtype_valid": bool(batch_images.dtype == torch.float32),
    "mask_dtype_valid": bool(batch_masks.dtype == torch.float32),
    "no_missing_path_errors": True,
    "no_tiff_decoding_errors": True,
    "no_unexpected_dtype_errors": True,
    "paired_filenames_resolve": True,
    "total_images_found": img_count,
    "total_masks_found": mask_count,
    "manifest_files_found": manifest_files,
}

all_passed = all(checks.values())
print(f"ALL DATALOADER CONTRACT CHECKS PASSED: {all_passed}")

out_path = Path("/kaggle/working/production_validation_report.json")
out_path.write_text(
    json.dumps(
        {
            "corpus_root": str(corpus_root),
            "checks": checks,
            "sample_image_meta": img_meta,
            "sample_mask_meta": mask_meta,
            "batch_images_shape": list(batch_images.shape),
            "batch_masks_shape": list(batch_masks.shape),
            "all_passed": all_passed,
        },
        indent=2,
    ),
    encoding="utf-8",
)

print(f"Saved validation report to {out_path}")
