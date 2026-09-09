"""
Upload the Ocean Sentinel source code package to Kaggle as a lightweight dataset.
This creates: dheeraj12237/ocean-sentinel-src
"""
import json, shutil, subprocess, sys
from pathlib import Path

PROJECT_ROOT = Path("D:/Projects/ocean-sentinel")
SRC_DIR = PROJECT_ROOT / "src"
STAGING_DIR = PROJECT_ROOT / "experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118/src_dataset_staging"
METADATA_PATH = STAGING_DIR / "dataset-metadata.json"

# Build staging directory
if STAGING_DIR.exists():
    shutil.rmtree(STAGING_DIR)
STAGING_DIR.mkdir(parents=True)

# Copy src/ocean_sentinel into staging
ocean_src = SRC_DIR / "ocean_sentinel"
dest = STAGING_DIR / "ocean_sentinel"
shutil.copytree(ocean_src, dest)
print(f"Copied {len(list(dest.rglob('*.py')))} Python files to staging")

# Write dataset-metadata.json
metadata = {
    "title": "Ocean Sentinel Source Code",
    "id": "dheeraj12237/ocean-sentinel-src",
    "licenses": [{"name": "other"}]
}
METADATA_PATH.write_text(json.dumps(metadata, indent=2))
print(f"Metadata written: {METADATA_PATH}")

# Show staging tree
print("\nStaging tree:")
for f in sorted(STAGING_DIR.rglob("*")):
    if f.is_file():
        print(f"  {f.relative_to(STAGING_DIR)} ({f.stat().st_size} bytes)")

# Secret audit: no credential content
print("\nSecret audit: checking for tokens/keys...")
import re
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
print(f"Secret violations: {violations}")

if violations == 0:
    print("\nSECRET_AUDIT: PASS")
    print(f"\nRun push command:")
    print(f"  D:\\Tools\\cloud-tools\\Scripts\\kaggle.exe datasets create -p {STAGING_DIR}")
else:
    print("\nSECRET_AUDIT: FAIL — do NOT push")
    sys.exit(1)
