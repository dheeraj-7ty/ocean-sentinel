"""
Update the Ocean Sentinel source code package on Kaggle as a lightweight dataset.
Target: dheeraj12237/ocean-sentinel-src
Includes updated ml/gpu_qualification.py and ingestion/dataset.py.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path("D:/Projects/ocean-sentinel")
SRC_DIR = PROJECT_ROOT / "src"
GATE_DIR = PROJECT_ROOT / "experiments/performance/gate4_3C_A_gpu_qualification_20260908_194000"
STAGING_DIR = GATE_DIR / "src_dataset_staging"
METADATA_PATH = STAGING_DIR / "dataset-metadata.json"

# Clean and create staging
if STAGING_DIR.exists():
    shutil.rmtree(STAGING_DIR)
STAGING_DIR.mkdir(parents=True)

# Copy src/ocean_sentinel into staging, excluding __pycache__
ocean_src = SRC_DIR / "ocean_sentinel"
dest = STAGING_DIR / "ocean_sentinel"

def ignore_pycache(path, names):
    return [n for n in names if n == "__pycache__" or n.endswith(".pyc")]

shutil.copytree(ocean_src, dest, ignore=ignore_pycache)
print(f"Copied {len(list(dest.rglob('*.py')))} Python files to staging")

# Verify critical files are present
assert (dest / "ml" / "gpu_qualification.py").exists(), "ml/gpu_qualification.py missing"
assert (dest / "ml" / "canonical_exp01.py").exists(), "ml/canonical_exp01.py missing"
assert (dest / "ml" / "unet_resnet.py").exists(), "ml/unet_resnet.py missing"
assert (dest / "ingestion" / "dataset.py").exists(), "ingestion/dataset.py missing"
assert (dest / "ingestion" / "split.py").exists(), "ingestion/split.py missing"

# Write dataset-metadata.json
metadata = {
    "title": "Ocean Sentinel Source Code",
    "id": "dheeraj12237/ocean-sentinel-src",
    "licenses": [{"name": "other"}]
}
METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print(f"Metadata written: {METADATA_PATH}")

# Secret audit
print("\nSecret audit: checking for tokens/keys...")
SECRET_PATTERNS = [
    re.compile(r'Bearer\s+[A-Za-z0-9\-_.]{20,}'),
    re.compile(r'api[_-]?key\s*[=:]\s*[A-Za-z0-9]{16,}', re.IGNORECASE),
    re.compile(r'token\s*[=:]\s*[A-Za-z0-9]{20,}', re.IGNORECASE),
]
violations = 0
for pyfile in STAGING_DIR.rglob("*.py"):
    content = pyfile.read_text(encoding='utf-8', errors='ignore')
    for pat in SECRET_PATTERNS:
        if pat.search(content):
            print(f"  SECRET VIOLATION: {pyfile}")
            violations += 1

if violations == 0:
    print("SECRET_AUDIT: PASS (0 violations)")
else:
    print("SECRET_AUDIT: FAIL - do not push")
    sys.exit(1)

# Push new version to Kaggle
cmd = [
    r"D:\Tools\cloud-tools\Scripts\kaggle.exe",
    "datasets", "version",
    "-p", str(STAGING_DIR),
    "-m", "Gate 4.3C-A: add gpu_qualification and cross-platform dataset loader",
    "-r", "zip"
]
print(f"\nRunning Kaggle dataset version update: {' '.join(cmd)}")
res = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
if res.returncode != 0:
    print(f"Failed with returncode: {res.returncode}")
    sys.exit(res.returncode)

print("Dataset updated successfully!")
