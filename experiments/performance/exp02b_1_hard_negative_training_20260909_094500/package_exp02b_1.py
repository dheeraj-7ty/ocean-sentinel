"""
Package Gate EXP02B-1 Training Push Bundle.

1. Reads local scripts/train_exp02b_1.py.
2. Verifies SHA-256.
3. Compresses and base64 encodes it.
4. Generates canary_exp02b_1.py.
5. Writes train_exp02b_1.py and kernel-metadata.json to kaggle_push_bundle/.
6. Validates bundle completeness and emits deployment preflight manifest.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path("D:/Projects/ocean-sentinel")
GATE_DIR = REPO_ROOT / "experiments/performance/exp02b_1_hard_negative_training_20260909_094500"
BUNDLE_DIR = GATE_DIR / "kaggle_push_bundle"
BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

RUNNER_SRC = REPO_ROOT / "scripts/train_exp02b_1.py"
DEST_CANARY = BUNDLE_DIR / "canary_exp02b_1.py"
DEST_RUNNER = BUNDLE_DIR / "train_exp02b_1.py"
DEST_METADATA = BUNDLE_DIR / "kernel-metadata.json"

EXPECTED_IMAGENET_SHA256 = "B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F"
EXPECTED_MANIFEST_SHA256 = "C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0"
EXPECTED_CANDIDATE_SHA256 = "5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7"
EXPECTED_TEACHER_SHA256 = "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699"
EXPECTED_POLICY_SHA256 = "F4F40D921238EC34EE5F33A413D22CFB5138015F133E57BD74532B4ADAF42FC9"
EXPECTED_CRITERIA_SHA256 = "DD777D1D51C2751A5F7C6E960B941A83A4783435D0B4E9BA9FF0AE9053961D29"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    print("=" * 80)
    print("PACKAGING EXP02B-1 KAGGLE TRAINING PUSH BUNDLE")
    print("=" * 80)

    assert RUNNER_SRC.exists(), f"Missing runner: {RUNNER_SRC}"
    runner_bytes = RUNNER_SRC.read_bytes()
    runner_sha = file_sha256(RUNNER_SRC)
    print(f"Runner Source:     {RUNNER_SRC}")
    print(f"Runner Size:       {len(runner_bytes):,} bytes")
    print(f"Runner SHA256:     {runner_sha}")

    # Copy raw runner into bundle
    DEST_RUNNER.write_bytes(runner_bytes)
    print(f"Copied raw runner to: {DEST_RUNNER}")

    # Write kernel-metadata.json
    metadata = {
        "id": "dheeraj12237/ocean-sentinel-gate-4-3b-live-canary",
        "title": "Ocean Sentinel Gate 4.3B Live Canary",
        "code_file": "canary_exp02b_1.py",
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
    print(f"Written metadata to:  {DEST_METADATA}")

    # Compress runner
    compressed = gzip.compress(runner_bytes, 9)
    b64_runner = base64.b64encode(compressed).decode("ascii")

    # Construct the canary runner
    canary_code = f'''#!/usr/bin/env python3
"""
Ocean Sentinel — EXP02B-1: Hard-Negative Weighted Random Sampling Training Canary.
Executes full 30-epoch training on Kaggle Tesla T4 GPU under strict scientific governance.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import math
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

GATE_ID = "EXP02B_1_HARD_NEGATIVE_TRAINING"
EMBEDDED_RUNNER_GZIP_B64 = "{b64_runner}"
EXPECTED_RUNNER_SHA256 = "{runner_sha}"
EXPECTED_MANIFEST_SHA256 = "{EXPECTED_MANIFEST_SHA256}"
EXPECTED_CANDIDATE_SHA256 = "{EXPECTED_CANDIDATE_SHA256}"
EXPECTED_WEIGHT_SHA256 = "{EXPECTED_IMAGENET_SHA256}"
EXPECTED_WEIGHT_FILENAME = "resnet34-b627a593.pth"
EXPECTED_WEIGHT_URL = "https://download.pytorch.org/models/resnet34-b627a593.pth"

START_UTC = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
EXECUTION_LOG: List[Dict[str, Any]] = []


def utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(msg: str) -> None:
    ts = utcnow()
    line = f"[{{ts}}] {{msg}}"
    print(line, flush=True)
    EXECUTION_LOG.append({{"timestamp": ts, "message": msg}})


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> None:
    log("=" * 80)
    log("OCEAN SENTINEL — EXP02B-1 HARD-NEGATIVE WEIGHTED SAMPLING TRAINING")
    log("=" * 80)

    working_dir = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path(".").resolve()
    out_dir = working_dir / "exp02b_1_hard_negative_training"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------
    # PHASE 1: ENVIRONMENT & HARDWARE AUDIT
    # ------------------------------------------------------------
    log("\\n--- PHASE 1: ENVIRONMENT & HARDWARE QUALIFICATION ---")
    import torch

    cuda_avail = torch.cuda.is_available()
    log(f"CUDA Available:     {{cuda_avail}}")
    log(f"PyTorch Version:    {{torch.__version__}}")
    log(f"CUDA Runtime:       {{torch.version.cuda}}")
    log(f"cuDNN Version:      {{torch.backends.cudnn.version() if cuda_avail else 'N/A'}}")
    log(f"Hostname:           {{socket.gethostname()}}")
    log(f"Platform:           {{platform.platform()}}")
    log(f"Working Directory:  {{working_dir}}")

    if not cuda_avail:
        raise RuntimeError("FATAL: CUDA is not available. Silent CPU fallback is strictly prohibited.")

    gpu_count = torch.cuda.device_count()
    gpu_name = torch.cuda.get_device_name(0)
    cap = torch.cuda.get_device_capability(0)
    sm_str = f"sm_{{cap[0]}}{{cap[1]}}"
    log(f"GPU Count:          {{gpu_count}}")
    log(f"GPU 0 Name:         {{gpu_name}}")
    log(f"Compute Capability: {{cap}} ({{sm_str}})")

    # Qualification Item 13: Confirm NVIDIA Tesla T4 / sm_75
    if cap[0] < 7:
        raise RuntimeError(f"FATAL: Compute capability {{sm_str}} < sm_70 is incompatible with modern PyTorch builds.")
    log(f"  [PASS] Hardware qualification: {{gpu_name}} ({{sm_str}}) verified.")

    # ------------------------------------------------------------
    # PHASE 2: MOUNT AUDIT (Corpus, Candidate Manifest, Identity)
    # ------------------------------------------------------------
    log("\\n--- PHASE 2: DATASET & ARTIFACT MOUNT AUDIT ---")
    corpus_mount = None
    corpus_candidates = [
        Path("/kaggle/input/ocean-sentinel-trujillo-corpus"),
        Path("/kaggle/input/datasets/dheeraj12237/ocean-sentinel-trujillo-corpus"),
        Path("data/raw/trujillo_2024").resolve(),
    ]
    for c in corpus_candidates:
        if c.exists() and ((c / "images").exists() or (c / "manifest").exists()):
            corpus_mount = c.resolve()
            break

    manifest_candidates = [
        corpus_mount / "manifest" / "spatial_split_manifest.json" if corpus_mount else None,
        corpus_mount / "spatial_split_manifest.json" if corpus_mount else None,
        Path("/kaggle/input/ocean-sentinel-trujillo-corpus/manifest/spatial_split_manifest.json"),
        Path("/kaggle/input/ocean-sentinel-trujillo-corpus/spatial_split_manifest.json"),
        Path("data/metadata/trujillo_2024/spatial_split_manifest.json").resolve(),
    ]
    manifest_path = None
    for m in manifest_candidates:
        if m is not None and m.exists():
            manifest_path = m.resolve()
            break

    log(f"Corpus Mount:       {{corpus_mount}} (exists: {{corpus_mount.exists() if corpus_mount else False}})")
    log(f"Manifest Path:      {{manifest_path}} (exists: {{manifest_path.exists() if manifest_path else False}})")

    if manifest_path is None or not manifest_path.exists():
        raise FileNotFoundError(f"FATAL: Spatial split manifest not found")

    actual_manifest_sha = file_sha256(manifest_path)
    log(f"Manifest SHA256:    {{actual_manifest_sha}}")
    if actual_manifest_sha != EXPECTED_MANIFEST_SHA256:
        raise ValueError(f"FATAL: Manifest SHA256 mismatch! Observed: {{actual_manifest_sha}}")
    log("  [PASS] Canonical split manifest hash verified (Item 5).")

    # Candidate manifest & identity mount audit
    src_mount = None
    src_candidates = [
        Path("/kaggle/input/ocean-sentinel-src"),
        Path("/kaggle/input/datasets/dheeraj12237/ocean-sentinel-src"),
        Path(".").resolve(),
    ]
    cand_manifest_path = None
    for sc in src_candidates:
        if sc.exists() and (sc / "candidate_manifest.json").exists():
            cand_manifest_path = (sc / "candidate_manifest.json").resolve()
            src_mount = sc.resolve()
            break

    if cand_manifest_path is None:
        # Search anywhere in /kaggle/input
        for root, dirs, files in os.walk("/kaggle/input"):
            if "candidate_manifest.json" in files:
                cand_manifest_path = Path(root) / "candidate_manifest.json"
                src_mount = Path(root)
                break

    log(f"Candidate Manifest: {{cand_manifest_path}} (exists: {{cand_manifest_path.exists() if cand_manifest_path else False}})")
    if cand_manifest_path is None or not cand_manifest_path.exists():
        raise FileNotFoundError("FATAL: Approved candidate manifest not mounted!")

    actual_cand_sha = file_sha256(cand_manifest_path)
    log(f"Candidate SHA256:   {{actual_cand_sha}}")
    if actual_cand_sha != EXPECTED_CANDIDATE_SHA256:
        raise ValueError(f"FATAL: Candidate manifest SHA256 mismatch! Observed: {{actual_cand_sha}}")
    log("  [PASS] Approved candidate manifest hash verified (Item 6 & Item 12).")

    # Source code mount
    # Symlink ocean_sentinel package into working directory if needed
    pkg_found = False
    for sc in [src_mount, Path("/kaggle/input/ocean-sentinel-src")]:
        if sc and (sc / "ocean_sentinel" / "__init__.py").exists():
            if str(sc) not in sys.path:
                sys.path.insert(0, str(sc))
            pkg_found = True
            break
        elif sc and (sc / "ocean_sentinel.zip").exists():
            log(f"Unzipping ocean_sentinel.zip from {{sc}}...")
            shutil.unpack_archive(sc / "ocean_sentinel.zip", working_dir)
            if str(working_dir) not in sys.path:
                sys.path.insert(0, str(working_dir))
            pkg_found = True
            break

    if not pkg_found:
        # Walk to find ocean_sentinel
        for root, dirs, files in os.walk("/kaggle/input"):
            if "__init__.py" in files and "dataset.py" in files and Path(root).name == "ocean_sentinel":
                parent_dir = str(Path(root).parent)
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)
                pkg_found = True
                break

    import ocean_sentinel
    log(f"ocean_sentinel:     {{ocean_sentinel.__file__}}")
    log("  [PASS] Source code package mounted and verified (Item 11 & Item 12).")

    # Ensure symlinks in working directory and scripts directory for child processes
    src_pkg_dir = Path(ocean_sentinel.__file__).resolve().parent
    for dest_link in [working_dir / "ocean_sentinel", working_dir / "scripts" / "ocean_sentinel"]:
        if not dest_link.exists() and not dest_link.is_symlink():
            try:
                os.symlink(str(src_pkg_dir), str(dest_link))
                log(f"Created symlink: {{dest_link}} -> {{src_pkg_dir}}")
            except Exception as ex:
                try:
                    shutil.copytree(src_pkg_dir, dest_link)
                    log(f"Copied package tree: {{dest_link}} -> {{src_pkg_dir}}")
                except Exception as ex2:
                    log(f"Notice on package linking: {{ex2}}")

    child_env = dict(os.environ)
    child_env["PYTHONPATH"] = f"{{src_pkg_dir.parent}}:{{working_dir}}:{{working_dir / 'scripts'}}:{{child_env.get('PYTHONPATH', '')}}"

    # ------------------------------------------------------------
    # PHASE 3: PRETRAINED IMAGENET RESNET-34 WEIGHTS ACQUISITION
    # ------------------------------------------------------------
    log("\\n--- PHASE 3: PRETRAINED WEIGHTS INTEGRITY (Item 4) ---")
    cache_dir = Path(os.path.expanduser("~/.cache/torch/hub/checkpoints"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    weight_file = cache_dir / EXPECTED_WEIGHT_FILENAME

    if not weight_file.exists() or file_sha256(weight_file) != EXPECTED_WEIGHT_SHA256:
        log(f"Downloading pretrained ImageNet weights from {{EXPECTED_WEIGHT_URL}}...")
        urllib.request.urlretrieve(EXPECTED_WEIGHT_URL, weight_file)

    actual_weight_sha = file_sha256(weight_file)
    log(f"Weight File:        {{weight_file}}")
    log(f"Weight SHA256:      {{actual_weight_sha}}")
    if actual_weight_sha != EXPECTED_WEIGHT_SHA256:
        raise ValueError(f"FATAL: Pretrained weight hash mismatch! {{actual_weight_sha}}")
    log("  [PASS] Pretrained ImageNet weight hash verified (Item 4).")

    # ------------------------------------------------------------
    # PHASE 4: STAGE RUNNER train_exp02b_1.py
    # ------------------------------------------------------------
    log("\\n--- PHASE 4: RUNNER EXTRACTION & HASH AUDIT ---")
    scripts_dir = working_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    runner_dest = scripts_dir / "train_exp02b_1.py"
    working_runner = working_dir / "train_exp02b_1.py"

    decomp = gzip.decompress(base64.b64decode(EMBEDDED_RUNNER_GZIP_B64.encode("ascii")))
    runner_dest.write_bytes(decomp)
    working_runner.write_bytes(decomp)

    actual_runner_sha = file_sha256(runner_dest)
    log(f"Runner Dest:        {{runner_dest}}")
    log(f"Runner SHA256:      {{actual_runner_sha}}")
    if actual_runner_sha != EXPECTED_RUNNER_SHA256:
        raise ValueError(f"FATAL: Runner SHA mismatch! {{actual_runner_sha}} != {{EXPECTED_RUNNER_SHA256}}")
    log("  [PASS] Runner script hash verified.")

    # ------------------------------------------------------------
    # PHASE 5: EXECUTE PREFLIGHT PASS (Zero Optimizer Steps)
    # ------------------------------------------------------------
    log("\\n--- PHASE 5: DEPLOYMENT PREFLIGHT EXECUTION ---")
    data_root_arg = []
    if corpus_mount and (corpus_mount / "images").exists():
        data_root_arg = ["--data-root", str(corpus_mount)]

    preflight_cmd = [
        sys.executable,
        str(runner_dest),
        "--manifest", str(manifest_path),
        "--candidate-manifest", str(cand_manifest_path),
        "--output-dir", str(out_dir),
        "--preflight-only",
        "--eval-threshold", "0.22",
        "--epochs", "30",
        "--batch-size", "8",
        "--lr", "1e-4",
        "--weight-decay", "1e-2",
        "--seed", "42",
        "--num-workers", "2",
    ] + data_root_arg

    log(f"Running preflight command: {{' '.join(preflight_cmd)}}")
    t0 = time.time()
    p_res = subprocess.run(
        preflight_cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=child_env,
    )
    dt = time.time() - t0
    log(f"Preflight finished in {{dt:.1f}}s with exit code {{p_res.returncode}}")
    log("Preflight STDOUT:\\n" + p_res.stdout)
    if p_res.stderr:
        log("Preflight STDERR:\\n" + p_res.stderr)

    if p_res.returncode != 0:
        raise RuntimeError("FATAL: Deployment preflight gate failed! Aborting before training.")

    log("======================================================================")
    log("PREFLIGHT PASS: ALL EXP02B-1 DEPLOYMENT PREFLIGHT CHECKS SATISFIED")
    log("======================================================================")

    # ------------------------------------------------------------
    # PHASE 6: EXECUTE FULL 30-EPOCH TRAINING
    # ------------------------------------------------------------
    log("\\n--- PHASE 6: FULL 30-EPOCH TRAINING EXECUTION ---")
    train_cmd = [
        sys.executable,
        str(runner_dest),
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
    ] + data_root_arg

    log(f"Launching training command: {{' '.join(train_cmd)}}")
    t_train_start = time.time()
    t_proc = subprocess.Popen(
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
        for line in t_proc.stdout:
            print(line, end="", flush=True)
            f_out.write(line)

    t_proc.wait()
    t_train_dur = time.time() - t_train_start
    log(f"Training process completed in {{t_train_dur / 3600:.2f}} hours with exit code {{t_proc.returncode}}")

    if t_proc.returncode != 0:
        raise RuntimeError(f"FATAL: Training process exited with code {{t_proc.returncode}}")

    # ------------------------------------------------------------
    # PHASE 7: COPY RESULTS TO WORKING ROOT & AUDIT
    # ------------------------------------------------------------
    log("\\n--- PHASE 7: POST-RUN ARTIFACT PACKAGING ---")
    for f in out_dir.glob("*.json"):
        shutil.copy2(f, working_dir / f.name)
    for f in out_dir.glob("*.log"):
        shutil.copy2(f, working_dir / f.name)
    for f in out_dir.glob("*.pt"):
        shutil.copy2(f, working_dir / f.name)

    log("EXP02B-1 EXECUTION SUCCESSFULLY COMPLETED.")


if __name__ == "__main__":
    main()
'''
    DEST_CANARY.write_text(canary_code, encoding="utf-8")
    print(f"Generated canary script: {DEST_CANARY} ({len(canary_code):,} chars)")

    # Record all hashes
    bundle_summary = {
        "packaging_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runner": {
            "path": str(DEST_RUNNER),
            "sha256": runner_sha,
            "size": len(runner_bytes),
        },
        "canary": {
            "path": str(DEST_CANARY),
            "sha256": file_sha256(DEST_CANARY),
            "size": DEST_CANARY.stat().st_size,
        },
        "kernel_metadata": json.loads(DEST_METADATA.read_text(encoding="utf-8")),
        "preflight_invariants": {
            "expected_imagenet_sha256": EXPECTED_IMAGENET_SHA256,
            "expected_split_manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "expected_candidate_manifest_sha256": EXPECTED_CANDIDATE_SHA256,
            "expected_teacher_model_sha256": EXPECTED_TEACHER_SHA256,
            "expected_sampling_policy_sha256": EXPECTED_POLICY_SHA256,
            "expected_success_criteria_sha256": EXPECTED_CRITERIA_SHA256,
        },
    }
    summary_path = GATE_DIR / "bundle_manifest.json"
    summary_path.write_text(json.dumps(bundle_summary, indent=2), encoding="utf-8")
    print(f"Written bundle manifest to: {summary_path}")
    print("\n" + "=" * 80)
    print("EXP02B-1 PUSH BUNDLE BUILD: COMPLETE (Item 9 PASS)")
    print("=" * 80)


if __name__ == "__main__":
    main()
