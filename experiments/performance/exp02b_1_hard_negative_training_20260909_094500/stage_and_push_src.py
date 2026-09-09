"""
Stage and push updated ocean-sentinel-src dataset to Kaggle.
Includes:
- ocean_sentinel python package
- approved candidate_manifest.json (5876A4E6...)
- approved experiment_identity.json (D78497BC...)
- approved proposed_sampling_policy.md (F4F40D92...)
- approved proposed_success_criteria.md (DD777D1D...)
- approved GATE_EXP02B_0_REPORT.md (BB787BE7...)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path("D:/Projects/ocean-sentinel")
GATE_DIR = REPO_ROOT / "experiments/performance/exp02b_1_hard_negative_training_20260909_094500"
STAGING_DIR = GATE_DIR / "src_dataset_staging"
EXP02B_0_DIR = REPO_ROOT / "experiments/performance/exp02b_0_hard_negative_design_20260909_021500"
KAGGLE_BIN = Path(r"D:\Tools\cloud-tools\Scripts\kaggle.exe")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    print("=" * 80)
    print("STAGING & PUSHING EXP02B-1 SOURCE & CONFIG DATASET TO KAGGLE")
    print("=" * 80)

    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Copy src/ocean_sentinel
    src_dir = REPO_ROOT / "src" / "ocean_sentinel"
    dest_src = STAGING_DIR / "ocean_sentinel"

    def ignore_pycache(path, names):
        return [n for n in names if n == "__pycache__" or n.endswith(".pyc")]

    shutil.copytree(src_dir, dest_src, ignore=ignore_pycache)
    print(f"[PASS] Copied ocean_sentinel package ({len(list(dest_src.rglob('*.py')))} python files)")

    # 2. Copy approved EXP02B-0 artifacts into staging
    artifacts_to_copy = [
        ("candidate_manifest.json", "5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7"),
        ("experiment_identity.json", "D78497BC951348D6E5CA078648D34F040F43B7FBABB4C756B2CC1D256A7EC44C"),
        ("proposed_sampling_policy.md", "F4F40D921238EC34EE5F33A413D22CFB5138015F133E57BD74532B4ADAF42FC9"),
        ("proposed_success_criteria.md", "DD777D1D51C2751A5F7C6E960B941A83A4783435D0B4E9BA9FF0AE9053961D29"),
        ("GATE_EXP02B_0_REPORT.md", "BB787BE720BCCBF3BBDD27DD3E204C64BFFC4D11070C4E8A901197D82B36C502"),
    ]

    for fname, expected_sha in artifacts_to_copy:
        src_path = EXP02B_0_DIR / fname
        dest_path = STAGING_DIR / fname
        assert src_path.exists(), f"Missing artifact: {src_path}"
        actual_src_sha = sha256_file(src_path)
        assert actual_src_sha == expected_sha, f"SHA mismatch on {fname}: {actual_src_sha} != {expected_sha}"
        shutil.copy2(src_path, dest_path)
        actual_dest_sha = sha256_file(dest_path)
        assert actual_dest_sha == expected_sha
        print(f"[PASS] Staged {fname} (SHA: {actual_dest_sha[:16]}... size: {dest_path.stat().st_size:,} bytes)")

    # 3. Write dataset-metadata.json
    meta = {
        "title": "Ocean Sentinel Source Code",
        "id": "dheeraj12237/ocean-sentinel-src",
        "licenses": [{"name": "other"}],
    }
    meta_path = STAGING_DIR / "dataset-metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[PASS] Written dataset metadata to {meta_path}")

    # 4. Secret audit
    print("\nExecuting Secret Audit...")
    SECRET_PATTERNS = [
        re.compile(r"Bearer\s+[A-Za-z0-9\-_.]{20,}"),
        re.compile(r"api[_-]?key\s*[=:]\s*[A-Za-z0-9]{16,}", re.IGNORECASE),
        re.compile(r"token\s*[=:]\s*[A-Za-z0-9]{20,}", re.IGNORECASE),
    ]
    violations = 0
    for pyfile in STAGING_DIR.rglob("*.py"):
        content = pyfile.read_text(encoding="utf-8", errors="ignore")
        for pat in SECRET_PATTERNS:
            if pat.search(content):
                print(f"  SECRET VIOLATION: {pyfile}")
                violations += 1
    if violations > 0:
        print(f"[FAIL] Secret audit failed with {violations} violations.")
        sys.exit(1)
    print("[PASS] Secret audit passed (0 violations).")

    # 5. Push dataset version to Kaggle
    cmd = [
        str(KAGGLE_BIN),
        "datasets",
        "version",
        "-p",
        str(STAGING_DIR),
        "-m",
        "EXP02B-1: approved candidate manifest, experiment identity, sampling policy, success criteria",
        "-r",
        "zip",
    ]
    print(f"\nPushing dataset to Kaggle: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("STDOUT:\n", res.stdout)
    print("STDERR:\n", res.stderr)

    if res.returncode != 0:
        print(f"[FAIL] Kaggle dataset push failed (code {res.returncode})")
        sys.exit(res.returncode)

    print("[PASS] Dataset dheeraj12237/ocean-sentinel-src updated successfully!")


if __name__ == "__main__":
    main()
