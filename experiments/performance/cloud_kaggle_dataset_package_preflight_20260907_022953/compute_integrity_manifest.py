"""Compute SHA-256 Integrity Manifest for Gate 4.1 Trujillo Dataset Preflight."""

import hashlib
import json
import os
import sys
import time
import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

def hash_single_file(args):
    rel_path_str, abs_path_str = args
    abs_p = Path(abs_path_str)
    size_bytes = abs_p.stat().st_size
    h = hashlib.sha256()
    with open(abs_p, "rb") as fp:
        while chunk := fp.read(4 * 1024 * 1024):
            h.update(chunk)
    return {
        "relative_path": rel_path_str.replace("\\", "/"),
        "filename": abs_p.name,
        "size_bytes": size_bytes,
        "sha256": h.hexdigest()
    }

def main():
    repo_root = Path("D:/Projects/ocean-sentinel").resolve()
    raw_dir = repo_root / "data" / "raw" / "trujillo_2024"
    img_dir = raw_dir / "images" / "Oil"
    mask_dir = raw_dir / "masks" / "Mask_oil"
    split_manifest = repo_root / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
    
    out_dir = repo_root / "experiments" / "performance" / "cloud_kaggle_dataset_package_preflight_20260907_022953"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_manifest_path = out_dir / "integrity_manifest.json"
    
    # Gather all target files
    work_items = []
    
    img_files = sorted(list(img_dir.glob("*.tif")))
    for f in img_files:
        rel = f"images/Oil/{f.name}"
        work_items.append((rel, str(f)))
        
    mask_files = sorted(list(mask_dir.glob("*.tif")))
    for f in mask_files:
        rel = f"masks/Mask_oil/{f.name}"
        work_items.append((rel, str(f)))
        
    # Include the canonical spatial split manifest
    if split_manifest.exists():
        work_items.append(("manifest/spatial_split_manifest.json", str(split_manifest)))

    total_items = len(work_items)
    print(f"Starting SHA-256 calculation for {total_items} files across 8 worker processes...")
    t0 = time.perf_counter()
    
    results = []
    total_bytes_processed = 0
    
    with ProcessPoolExecutor(max_workers=8) as executor:
        # Submit all tasks
        futures = {executor.submit(hash_single_file, item): item for item in work_items}
        done_count = 0
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            total_bytes_processed += res["size_bytes"]
            done_count += 1
            if done_count % 300 == 0 or done_count == total_items:
                elapsed = time.perf_counter() - t0
                rate_mb = (total_bytes_processed / 1e6) / (elapsed + 1e-6)
                print(f"[{done_count}/{total_items}] Hashed {total_bytes_processed / (1024**3):.2f} GiB in {elapsed:.1f}s ({rate_mb:.1f} MB/s)")
                
    # Sort results deterministically by relative_path
    results.sort(key=lambda x: x["relative_path"])
    
    # Compute an overall root checksum across all sorted entries
    root_hasher = hashlib.sha256()
    for item in results:
        entry_str = f"{item['relative_path']}:{item['size_bytes']}:{item['sha256']}\n"
        root_hasher.update(entry_str.encode("utf-8"))
    corpus_root_sha256 = root_hasher.hexdigest()
    
    t_end = time.perf_counter()
    total_time = t_end - t0
    
    img_entries = [r for r in results if r["relative_path"].startswith("images/")]
    mask_entries = [r for r in results if r["relative_path"].startswith("masks/")]
    manifest_entries = [r for r in results if r["relative_path"].startswith("manifest/")]
    
    manifest_doc = {
        "dataset_name": "ocean-sentinel-trujillo-corpus",
        "package_slug": "dheeraj12237/ocean-sentinel-trujillo-corpus",
        "package_version": "1.0.0",
        "source_dataset_identifier": "Trujillo-Acatitla et al. (July 2024) Part I",
        "zenodo_doi": "10.5281/zenodo.8346860",
        "zenodo_url": "https://zenodo.org/records/8346860",
        "generation_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "hashing_wallclock_seconds": round(total_time, 2),
        "corpus_root_sha256": corpus_root_sha256,
        "summary": {
            "total_files": len(results),
            "total_bytes": total_bytes_processed,
            "total_gib": round(total_bytes_processed / (1024**3), 6),
            "total_gb": round(total_bytes_processed / 1e9, 6),
            "image_files_count": len(img_entries),
            "image_bytes": sum(e["size_bytes"] for e in img_entries),
            "mask_files_count": len(mask_entries),
            "mask_bytes": sum(e["size_bytes"] for e in mask_entries),
            "metadata_files_count": len(manifest_entries),
            "metadata_bytes": sum(e["size_bytes"] for e in manifest_entries)
        },
        "files": results
    }
    
    with open(out_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_doc, f, indent=2)
        
    print(f"Integrity manifest successfully written: {out_manifest_path}")
    print(f"Total files: {len(results)}, Total bytes: {total_bytes_processed:,} ({total_bytes_processed / (1024**3):.4f} GiB)")
    print(f"Corpus Root SHA256: {corpus_root_sha256}")
    print(f"Completed in {total_time:.2f}s")

if __name__ == "__main__":
    main()
