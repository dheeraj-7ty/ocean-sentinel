"""
Upload frozen C-C2 canonical epoch-1 seed to Kaggle as a private dataset.
Dataset ID: dheeraj12237/ocean-sentinel-c-c2-seed
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path("D:/Projects/ocean-sentinel")
C_C2_SEED = REPO_ROOT / "experiments/performance/gate4_3C_C2_canonical_seed_20260909_000500/kernel_output/latest_checkpoint.pt"
C_C2_INTEGRITY = REPO_ROOT / "experiments/performance/gate4_3C_C2_canonical_seed_20260909_000500/kernel_output/checkpoint_integrity.json"

STAGING_DIR = REPO_ROOT / "experiments/performance/gate4_3C_C4_resume_epoch2_20260909_002000/seed_dataset_staging"
METADATA_PATH = STAGING_DIR / "dataset-metadata.json"

KAGGLE_BIN = r"D:\Tools\cloud-tools\Scripts\kaggle.exe"
EXPECTED_SHA = "38E7B6E12177C9BAF60C98379C76E75684D8FC9CCB3E66BA0201B938EB29BCAA"


def main():
    print("=" * 65)
    print("STAGING & UPLOADING CANONICAL EPOCH-1 SEED DATASET TO KAGGLE")
    print("=" * 65)

    assert C_C2_SEED.exists(), f"Missing seed: {C_C2_SEED}"
    assert C_C2_INTEGRITY.exists(), f"Missing integrity manifest: {C_C2_INTEGRITY}"

    # Verify SHA
    import hashlib
    h = hashlib.sha256()
    with open(C_C2_SEED, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    actual_sha = h.hexdigest().upper()
    assert actual_sha == EXPECTED_SHA, f"SHA mismatch: {actual_sha} vs {EXPECTED_SHA}"
    print(f"Verified Seed Checkpoint SHA-256: {actual_sha} [BITWISE MATCH]")

    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True)

    dest_seed = STAGING_DIR / "latest_checkpoint.pt"
    dest_integrity = STAGING_DIR / "checkpoint_integrity.json"

    print("Copying frozen checkpoint to staging...")
    shutil.copy2(C_C2_SEED, dest_seed)
    shutil.copy2(C_C2_INTEGRITY, dest_integrity)
    print(f"Staged checkpoint size: {dest_seed.stat().st_size:,} bytes")

    metadata = {
        "title": "Ocean Sentinel C-C2 Canonical Epoch-1 Seed",
        "id": "dheeraj12237/ocean-sentinel-c-c2-seed",
        "licenses": [{"name": "other"}],
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote metadata: {METADATA_PATH}")

    # Check if dataset already exists or create new
    print(f"\nCreating Kaggle dataset via {KAGGLE_BIN}...")
    cmd = [KAGGLE_BIN, "datasets", "create", "-p", str(STAGING_DIR), "--dir-mode", "zip"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)
    if res.returncode != 0:
        if "already exists" in res.stderr.lower() or "already exists" in res.stdout.lower():
            print("Dataset already exists, updating with version...")
            up_cmd = [KAGGLE_BIN, "datasets", "version", "-p", str(STAGING_DIR), "-m", "Canonical Epoch-1 Seed", "--dir-mode", "zip"]
            up_res = subprocess.run(up_cmd, capture_output=True, text=True)
            print("UP STDOUT:", up_res.stdout)
            print("UP STDERR:", up_res.stderr)
            assert up_res.returncode == 0, f"Failed to update dataset: {up_res.stderr}"
        else:
            raise RuntimeError(f"Failed to create dataset: {res.stderr}")

    print("\nDataset successfully uploaded to Kaggle: dheeraj12237/ocean-sentinel-c-c2-seed")
    print("=" * 65)


if __name__ == "__main__":
    main()
