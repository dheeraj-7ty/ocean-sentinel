"""Source Inventory Generator for Gate 4.1 Trujillo Dataset Preflight."""

import json
import os
import datetime
from pathlib import Path

def main():
    raw_dir = Path('data/raw/trujillo_2024').resolve()
    img_dir = raw_dir / 'images' / 'Oil'
    mask_dir = raw_dir / 'masks' / 'Mask_oil'
    sample_dir = raw_dir / 'sample_images'
    
    img_files = sorted(list(img_dir.glob('*.tif')))
    mask_files = sorted(list(mask_dir.glob('*.tif')))
    
    img_stems = sorted([f.stem for f in img_files])
    mask_stems = sorted([f.stem for f in mask_files])
    
    img_bytes = sum(f.stat().st_size for f in img_files)
    mask_bytes = sum(f.stat().st_size for f in mask_files)
    extracted_bytes = img_bytes + mask_bytes
    
    orphan_images = sorted(list(set(img_stems) - set(mask_stems)))
    orphan_masks = sorted(list(set(mask_stems) - set(img_stems)))
    paired_stems = sorted(list(set(img_stems) & set(mask_stems)))
    
    arch_img_file = raw_dir / '01_Train_Val_Oil_Spill_images.7z'
    arch_mask_file = raw_dir / '01_Train_Val_Oil_Spill_mask.7z'
    
    arch_img_bytes = arch_img_file.stat().st_size if arch_img_file.exists() else 0
    arch_mask_bytes = arch_mask_file.stat().st_size if arch_mask_file.exists() else 0
    total_arch_bytes = arch_img_bytes + arch_mask_bytes
    
    sample_files = sorted(list(sample_dir.glob('**/*.*')))
    sample_bytes = sum(f.stat().st_size for f in sample_files if f.is_file())
    
    # All files in raw dir
    all_raw_files = [f for f in raw_dir.glob('**/*') if f.is_file()]
    total_raw_bytes = sum(f.stat().st_size for f in all_raw_files)
    
    inventory = {
        "dataset_name": "Trujillo Part I (July 2024)",
        "zenodo_doi": "10.5281/zenodo.8346860",
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_directory": str(raw_dir),
        "summary": {
            "image_file_count": len(img_files),
            "mask_file_count": len(mask_files),
            "total_extracted_tiffs": len(img_files) + len(mask_files),
            "exact_pair_count": len(paired_stems),
            "orphan_images_count": len(orphan_images),
            "orphan_masks_count": len(orphan_masks),
            "naming_range": {
                "min_stem": min(img_stems) if img_stems else None,
                "max_stem": max(img_stems) if img_stems else None,
                "stem_format": "5-digit zero-padded integer (e.g. 00000 to 01339, non-contiguous)"
            },
            "image_bytes": {
                "bytes": img_bytes,
                "gib": round(img_bytes / (1024**3), 6),
                "gb": round(img_bytes / 1e9, 6)
            },
            "mask_bytes": {
                "bytes": mask_bytes,
                "gib": round(mask_bytes / (1024**3), 6),
                "gb": round(mask_bytes / 1e9, 6)
            },
            "extracted_total_bytes": {
                "bytes": extracted_bytes,
                "gib": round(extracted_bytes / (1024**3), 6),
                "gb": round(extracted_bytes / 1e9, 6)
            },
            "archive_bytes": {
                "images_7z_filename": arch_img_file.name,
                "images_7z_bytes": arch_img_bytes,
                "images_7z_gib": round(arch_img_bytes / (1024**3), 6),
                "images_7z_gb": round(arch_img_bytes / 1e9, 6),
                "masks_7z_filename": arch_mask_file.name,
                "masks_7z_bytes": arch_mask_bytes,
                "masks_7z_gib": round(arch_mask_bytes / (1024**3), 6),
                "masks_7z_gb": round(arch_mask_bytes / 1e9, 6),
                "total_archive_bytes": total_arch_bytes,
                "total_archive_gib": round(total_arch_bytes / (1024**3), 6),
                "total_archive_gb": round(total_arch_bytes / 1e9, 6)
            },
            "sample_images": {
                "file_count": len(sample_files),
                "files": [str(f.relative_to(raw_dir)) for f in sample_files],
                "bytes": sample_bytes,
                "gib": round(sample_bytes / (1024**3), 6),
                "gb": round(sample_bytes / 1e9, 6),
                "is_redundant": True,
                "status": "EXCLUDED_FROM_PACKAGE"
            },
            "total_raw_directory_on_disk": {
                "file_count": len(all_raw_files),
                "bytes": total_raw_bytes,
                "gib": round(total_raw_bytes / (1024**3), 6),
                "gb": round(total_raw_bytes / 1e9, 6)
            }
        },
        "redundant_files": [
            {
                "path": str(arch_img_file.relative_to(raw_dir)),
                "bytes": arch_img_bytes,
                "reason": "Original compressed 7z image archive; redundant with extracted TIFFs"
            },
            {
                "path": str(arch_mask_file.relative_to(raw_dir)),
                "bytes": arch_mask_bytes,
                "reason": "Original compressed 7z mask archive; redundant with extracted TIFFs"
            },
            {
                "path": "sample_images",
                "bytes": sample_bytes,
                "reason": "Redundant 3-tile duplicate sample of Oil/00000.tif, 00002.tif, 00003.tif"
            }
        ],
        "orphan_images": orphan_images,
        "orphan_masks": orphan_masks,
        "actual_file_stems": paired_stems
    }
    
    out_path = Path('experiments/performance/cloud_kaggle_dataset_package_preflight_20260907_022953/source_inventory.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2)
        
    print(f'Wrote {out_path} ({len(paired_stems)} stems, {extracted_bytes:,} extracted bytes)')

if __name__ == '__main__':
    main()
