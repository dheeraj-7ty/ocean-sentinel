"""
Package and Deploy Full 30-Epoch Training Kernel for EXP02C.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path("D:/Projects/ocean-sentinel")
EXP_DIR = REPO_ROOT / "experiments/performance/exp02c_annealed_hard_negative_20260909_144000"
BUNDLE_DIR = EXP_DIR / "kaggle_training_bundle"
BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

DEST_RUNNER_KAGGLE = BUNDLE_DIR / "run_exp02c_training.py"
DEST_METADATA = BUNDLE_DIR / "kernel-metadata.json"

EXPECTED_IMAGENET_SHA256 = "B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F"
EXPECTED_MANIFEST_SHA256 = "C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0"
EXPECTED_CANDIDATE_SHA256 = "5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7"

RUNNER_SRC = REPO_ROOT / "scripts/train_exp02c.py"
runner_bytes = RUNNER_SRC.read_bytes()
runner_sha = hashlib.sha256(runner_bytes).hexdigest().upper()
compressed = gzip.compress(runner_bytes, 9)
b64_runner = base64.b64encode(compressed).decode("ascii")

metadata = {
    "id": "dheeraj12237/ocean-sentinel-gate-4-3b-live-canary",
    "title": "Ocean Sentinel Gate 4.3B Live Canary",
    "code_file": "run_exp02c_training.py",
    "language": "python",
    "kernel_type": "script",
    "is_private": True,
    "enable_gpu": True,
    "enable_tpu": False,
    "enable_internet": True,
    "machine_shape": "NvidiaTeslaT4",
    "dataset_sources": [
        "dheeraj12237/ocean-sentinel-trujillo-corpus",
        "dheeraj12237/ocean-sentinel-src",
    ],
}
DEST_METADATA.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

kaggle_launcher_code = f'''#!/usr/bin/env python3
"""
Ocean Sentinel — EXP02C Full 30-Epoch Training Runner on Kaggle Tesla T4.
Executes the preregistered Annealed Hard-Negative Sampling intervention.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

EXPERIMENT_ID = "EXP-02C"
EXPECTED_RUNNER_SHA256 = "{runner_sha}"
EXPECTED_MANIFEST_SHA256 = "{EXPECTED_MANIFEST_SHA256}"
EXPECTED_CANDIDATE_SHA256 = "{EXPECTED_CANDIDATE_SHA256}"
EXPECTED_WEIGHT_SHA256 = "{EXPECTED_IMAGENET_SHA256}"
EXPECTED_WEIGHT_FILENAME = "resnet34-b627a593.pth"
EXPECTED_WEIGHT_URL = "https://download.pytorch.org/models/resnet34-b627a593.pth"


def utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(msg: str) -> None:
    ts = utcnow()
    line = f"[{{ts}}] {{msg}}"
    print(line, flush=True)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> None:
    log("=" * 80)
    log("OCEAN SENTINEL — EXP-02C FULL 30-EPOCH TRAINING LAUNCH")
    log("ANNEALED HARD-NEGATIVE SAMPLING PRESSURE INTERVENTION")
    log("=" * 80)

    working_dir = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path(".").resolve()
    out_dir = working_dir / "exp02c_annealed_hard_negative_training"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Environment & Hardware Audit
    log("\\n--- 1. ENVIRONMENT & HARDWARE QUALIFICATION ---")
    import torch

    assert torch.cuda.is_available(), "FATAL: CUDA is not available"
    gpu_name = torch.cuda.get_device_name(0)
    cap = torch.cuda.get_device_capability(0)
    sm_str = f"sm_{{cap[0]}}{{cap[1]}}"
    log(f"CUDA Version:       {{torch.version.cuda}}")
    log(f"PyTorch Version:    {{torch.__version__}}")
    log(f"cuDNN Version:      {{torch.backends.cudnn.version()}}")
    log(f"Hostname:           {{socket.gethostname()}}")
    log(f"Platform:           {{platform.platform()}}")
    log(f"GPU Device:         {{gpu_name}} ({{sm_str}})")

    # 2. Mount Audit
    log("\\n--- 2. DATASET & ARTIFACT MOUNT AUDIT ---")
    corpus_mount = None
    for c in [Path("/kaggle/input/ocean-sentinel-trujillo-corpus"), Path("/kaggle/input/datasets/dheeraj12237/ocean-sentinel-trujillo-corpus")]:
        if c.exists():
            corpus_mount = c.resolve()
            break
    log(f"Corpus Mount:       {{corpus_mount}}")
    assert corpus_mount is not None, "Missing corpus mount"

    manifest_path = None
    for m in [corpus_mount / "manifest" / "spatial_split_manifest.json",
             corpus_mount / "spatial_split_manifest.json",
             Path("/kaggle/input/ocean-sentinel-trujillo-corpus/manifest/spatial_split_manifest.json")]:
        if m.exists():
            manifest_path = m.resolve()
            break
    log(f"Manifest Path:      {{manifest_path}}")
    assert manifest_path is not None and manifest_path.exists(), "Missing manifest"
    actual_manifest_sha = file_sha256(manifest_path)
    log(f"Manifest SHA256:    {{actual_manifest_sha}}")
    assert actual_manifest_sha == EXPECTED_MANIFEST_SHA256, f"Manifest mismatch: {{actual_manifest_sha}}"
    log("  [PASS] Canonical spatial split manifest verified.")

    cand_manifest_path = None
    for sc in [Path("/kaggle/input/ocean-sentinel-src"), Path("/kaggle/input/datasets/dheeraj12237/ocean-sentinel-src")]:
        if sc.exists() and (sc / "candidate_manifest.json").exists():
            cand_manifest_path = (sc / "candidate_manifest.json").resolve()
            break
    if cand_manifest_path is None:
        for root, dirs, files in os.walk("/kaggle/input"):
            if "candidate_manifest.json" in files:
                cand_manifest_path = Path(root) / "candidate_manifest.json"
                break
    log(f"Candidate Manifest: {{cand_manifest_path}}")
    assert cand_manifest_path is not None and cand_manifest_path.exists(), "Missing candidate manifest"
    actual_cand_sha = file_sha256(cand_manifest_path)
    log(f"Candidate SHA256:   {{actual_cand_sha}}")
    assert actual_cand_sha == EXPECTED_CANDIDATE_SHA256, f"Candidate manifest mismatch: {{actual_cand_sha}}"
    log("  [PASS] Candidate manifest verified.")

    # 3. Source Package Mount
    log("\\n--- 3. SOURCE PACKAGE & RUNNER AUDIT ---")
    src_pkg_root = None
    for sp in [Path("/kaggle/input/ocean-sentinel-src"), Path("/kaggle/input/datasets/dheeraj12237/ocean-sentinel-src")]:
        if sp.exists() and (sp / "ocean_sentinel").exists():
            src_pkg_root = sp.resolve()
            break
    if src_pkg_root is None:
        for root, dirs, files in os.walk("/kaggle/input"):
            if "ocean_sentinel" in dirs:
                src_pkg_root = Path(root)
                break
    log(f"Source Package Root: {{src_pkg_root}}")
    assert src_pkg_root is not None, "Missing ocean_sentinel python package"

    # Decompress embedded runner to disk
    runner_py = working_dir / "train_exp02c.py"
    decompressed = gzip.decompress(base64.b64decode("{b64_runner}"))
    runner_py.write_bytes(decompressed)
    actual_runner_sha = file_sha256(runner_py)
    log(f"Decompressed Runner SHA256: {{actual_runner_sha}}")
    assert actual_runner_sha == EXPECTED_RUNNER_SHA256, f"Runner SHA mismatch: {{actual_runner_sha}}"
    log("  [PASS] EXP02C runner decompressed and SHA-256 verified.")

    # 4. Pretrained ImageNet ResNet-34 Weights
    log("\\n--- 4. PRETRAINED WEIGHTS AUDIT ---")
    hub_dir = Path(torch.hub.get_dir()) / "checkpoints"
    hub_dir.mkdir(parents=True, exist_ok=True)
    target_weight = hub_dir / EXPECTED_WEIGHT_FILENAME

    if not target_weight.exists():
        log(f"Downloading ImageNet ResNet-34 weights to {{target_weight}}...")
        urllib.request.urlretrieve(EXPECTED_WEIGHT_URL, target_weight)
    actual_weight_sha = file_sha256(target_weight)
    log(f"Pretrained Weight SHA256: {{actual_weight_sha}}")
    assert actual_weight_sha == EXPECTED_WEIGHT_SHA256, f"Pretrained weight mismatch: {{actual_weight_sha}}"
    log("  [PASS] Pretrained ImageNet weights verified.")

    # 5. Launch Full Scientific Training Subprocess
    log("\\n--- 5. LAUNCHING FULL SCIENTIFIC TRAINING SUBPROCESS (30 EPOCHS) ---")
    child_env = os.environ.copy()
    child_env["PYTHONPATH"] = str(src_pkg_root) + os.pathsep + child_env.get("PYTHONPATH", "")

    train_cmd = [
        sys.executable,
        str(runner_py),
        "--manifest", str(manifest_path),
        "--candidate-manifest", str(cand_manifest_path),
        "--output-dir", str(out_dir),
        "--eval-threshold", "0.22",
        "--epochs", "30",
        "--batch-size", "8",
        "--lr", "1e-4",
        "--weight-decay", "1e-2",
        "--seed", "42",
        "--num-workers", "2",
        "--data-root", str(corpus_mount),
    ]

    log(f"Training Command: {{' '.join(train_cmd)}}")
    t_start = time.time()

    proc = subprocess.Popen(
        train_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=child_env,
    )

    with open(out_dir / "stdout_training.log", "w", encoding="utf-8") as f_out:
        for line in proc.stdout:
            print(line, end="", flush=True)
            f_out.write(line)

    proc.wait()
    t_dur = time.time() - t_start
    log(f"Training process finished in {{t_dur / 3600:.2f}} hours with returncode {{proc.returncode}}")

    if proc.returncode != 0:
        raise RuntimeError(f"FATAL: Training process failed with code {{proc.returncode}}")

    # 6. Post-Run Artifact Packaging to /kaggle/working
    log("\\n--- 6. POST-RUN ARTIFACT PACKAGING ---")
    for f in out_dir.glob("*.json"):
        shutil.copy2(f, working_dir / f.name)
        log(f"Copied {{f.name}} to {{working_dir / f.name}}")
    for f in out_dir.glob("*.log"):
        shutil.copy2(f, working_dir / f.name)
        log(f"Copied {{f.name}} to {{working_dir / f.name}}")
    for f in out_dir.glob("*.pt"):
        shutil.copy2(f, working_dir / f.name)
        log(f"Copied {{f.name}} to {{working_dir / f.name}}")

    log("=" * 80)
    log("EXP-02C TRAINING AND VALIDATION SUCCESSFULLY COMPLETED.")
    log("=" * 80)


if __name__ == "__main__":
    main()
'''

DEST_RUNNER_KAGGLE.write_text(kaggle_launcher_code, encoding="utf-8")
print(f"Generated Training Launcher: {DEST_RUNNER_KAGGLE} ({len(kaggle_launcher_code):,} chars)")
print(f"Generated Kernel Metadata: {DEST_METADATA}")
print(f"Runner embedded SHA256: {runner_sha}")
print("Training bundle packaging complete.")
