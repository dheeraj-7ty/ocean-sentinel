"""Deterministic Representative TIFF Validation for Gate 4.1."""

import json
import numpy as np
import rasterio
from pathlib import Path

def validate_image_file(p: Path, role: str):
    print(f"\n--- Validating Image [{role}]: {p.name} ---")
    with rasterio.open(p) as src:
        h, w = src.height, src.width
        bands = src.count
        dtype = src.dtypes[0]
        crs = src.crs
        transform = src.transform
        compression = src.compression
        
        print(f"Dimensions: {h} x {w}")
        print(f"Band Count: {bands}")
        print(f"Data Type:  {dtype}")
        print(f"CRS:        {crs}")
        print(f"Transform:  {transform}")
        print(f"Compression:{compression}")
        
        # Read data
        data = src.read()
        finite = np.isfinite(data).all()
        nan_count = np.isnan(data).sum()
        inf_count = np.isinf(data).sum()
        
        b1_min, b1_max, b1_mean = float(data[0].min()), float(data[0].max()), float(data[0].mean())
        b2_min, b2_max, b2_mean = float(data[1].min()), float(data[1].max()), float(data[1].mean())
        
        b1_neg_pct = float((data[0] < 0).mean() * 100)
        b2_neg_pct = float((data[1] < 0).mean() * 100)
        
        print(f"Finite:     {finite} (NaN: {nan_count}, Inf: {inf_count})")
        print(f"Band 1 dB:  min={b1_min:.2f}, max={b1_max:.2f}, mean={b1_mean:.2f} ({b1_neg_pct:.2f}% negative)")
        print(f"Band 2 dB:  min={b2_min:.2f}, max={b2_max:.2f}, mean={b2_mean:.2f} ({b2_neg_pct:.2f}% negative)")
        
        # Contract checks
        checks = {
            "height_2048": h == 2048,
            "width_2048": w == 2048,
            "bands_2": bands == 2,
            "dtype_float32": dtype == "float32",
            "crs_epsg4326": str(crs) == "EPSG:4326",
            "lzw_compression": str(compression).lower() == "compression.lzw" or "lzw" in str(compression).lower(),
            "all_finite": bool(finite),
            "decibel_radiometry": b1_mean < -10.0 and b2_mean < -10.0
        }
        print("Contract Checks:", checks)
        
        return {
            "role": role,
            "filename": p.name,
            "path": str(p),
            "dimensions": [h, w],
            "band_count": bands,
            "dtype": dtype,
            "crs": str(crs) if crs else None,
            "transform": [list(transform[0:3]), list(transform[3:6])],
            "compression": str(compression),
            "all_finite": bool(finite),
            "band_1_stats": {"min": b1_min, "max": b1_max, "mean": b1_mean, "negative_pct": b1_neg_pct},
            "band_2_stats": {"min": b2_min, "max": b2_max, "mean": b2_mean, "negative_pct": b2_neg_pct},
            "contract_compliance": all(checks.values()),
            "checks": checks
        }

def validate_mask_file(p: Path, role: str):
    print(f"\n--- Validating Mask [{role}]: {p.name} ---")
    with rasterio.open(p) as src:
        h, w = src.height, src.width
        bands = src.count
        dtype = src.dtypes[0]
        crs = src.crs
        transform = src.transform
        compression = src.compression
        
        print(f"Dimensions: {h} x {w}")
        print(f"Band Count: {bands}")
        print(f"Data Type:  {dtype}")
        print(f"CRS:        {crs}")
        print(f"Transform:  {transform}")
        print(f"Compression:{compression}")
        
        data = src.read(1)
        unique_vals = np.unique(data).tolist()
        finite = np.isfinite(data).all()
        oil_pixel_count = int((data == 1).sum())
        background_pixel_count = int((data == 0).sum())
        total_pixels = data.size
        oil_ratio = oil_pixel_count / total_pixels
        
        print(f"Unique Values: {unique_vals}")
        print(f"Oil Pixels:    {oil_pixel_count} ({oil_ratio*100:.3f}%)")
        print(f"Background:    {background_pixel_count}")
        
        checks = {
            "height_2048": h == 2048,
            "width_2048": w == 2048,
            "bands_1": bands == 1,
            "dtype_uint8": dtype == "uint8",
            "binary_semantics": set(unique_vals).issubset({0, 1}),
            "all_finite": bool(finite)
        }
        print("Contract Checks:", checks)
        
        return {
            "role": role,
            "filename": p.name,
            "path": str(p),
            "dimensions": [h, w],
            "band_count": bands,
            "dtype": dtype,
            "crs": str(crs) if crs else None,
            "unique_values": unique_vals,
            "oil_pixel_count": oil_pixel_count,
            "background_pixel_count": background_pixel_count,
            "oil_pixel_ratio": round(oil_ratio, 6),
            "contract_compliance": all(checks.values()),
            "checks": checks
        }

def main():
    raw_dir = Path("data/raw/trujillo_2024").resolve()
    img_dir = raw_dir / "images" / "Oil"
    mask_dir = raw_dir / "masks" / "Mask_oil"
    
    samples = [
        ("early_filename", img_dir / "00000.tif", "image"),
        ("median_sized_image", img_dir / "00789.tif", "image"),
        ("largest_image", img_dir / "01325.tif", "image"),
        ("representative_mask", mask_dir / "00000.tif", "mask"),
        ("train_scene_image", img_dir / "00000.tif", "image"),
        ("train_scene_mask", mask_dir / "00000.tif", "mask"),
        ("val_scene_image", img_dir / "00012.tif", "image"),
        ("val_scene_mask", mask_dir / "00012.tif", "mask"),
        ("test_scene_image", img_dir / "00005.tif", "image"),
        ("test_scene_mask", mask_dir / "00005.tif", "mask")
    ]
    
    results = []
    for role, path, kind in samples:
        if kind == "image":
            res = validate_image_file(path, role)
        else:
            res = validate_mask_file(path, role)
        results.append(res)
        
    out_dir = Path("experiments/performance/cloud_kaggle_dataset_package_preflight_20260907_022953")
    out_path = out_dir / "representative_tiff_validation.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nWrote representative TIFF validation results to {out_path}")
    all_passed = all(r["contract_compliance"] for r in results)
    print(f"Overall Representative Validation Status: {'PASS' if all_passed else 'FAIL'}")

if __name__ == "__main__":
    main()
