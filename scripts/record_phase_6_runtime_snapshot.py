"""Record Phase 0 Final Runtime Snapshot immediately before official execution."""

import ctypes
import datetime
import hashlib
import json
import os
import platform
import socket
import sys
from pathlib import Path

import torch
import torchvision

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "experiments/performance/phase_6_part_iii_external_evaluation/attempt_001"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_PATH = REPO_ROOT / "experiments/performance/exp06_positive_bce_weight/best_model.pt"
RUNNER_PATH = REPO_ROOT / "scripts/run_phase_6_full_evaluation.py"
MODEL_PATH = REPO_ROOT / "src/ocean_sentinel/ml/unet_resnet.py"
SPLIT_MANIFEST_PATH = REPO_ROOT / "data/metadata/trujillo_2024/spatial_split_manifest.json"
PAIRING_PATH = REPO_ROOT / "scratch/trujillo_part_iii_pairing.json"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024 * 4):
            h.update(chunk)
    return h.hexdigest().upper()


def get_ram_stats():
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    return stat.ullTotalPhys / (1024**3), stat.ullAvailPhys / (1024**3)


total_ram, avail_ram = get_ram_stats()

snapshot = {
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "hostname": socket.gethostname(),
    "os": platform.platform(),
    "python_version": sys.version,
    "pytorch_version": torch.__version__,
    "torchvision_version": torchvision.__version__,
    "cuda_version": torch.version.cuda if torch.cuda.is_available() else "N/A",
    "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
    "vram_total_gb": torch.cuda.get_device_properties(0).total_memory / (1024**3) if torch.cuda.is_available() else 0.0,
    "cpu": platform.processor(),
    "ram_total_gb": total_ram,
    "ram_avail_gb": avail_ram,
    "repository_head": "542bab19f6f08c9bba8b8762e6480386c8b6026b",
    "git_branch": "master",
    "checkpoint": {
        "path": str(CHECKPOINT_PATH).replace("\\", "/"),
        "byte_size": os.path.getsize(CHECKPOINT_PATH),
        "sha256": compute_sha256(CHECKPOINT_PATH),
        "trainable_parameters": 24346305,
    },
    "runner_sha256": compute_sha256(RUNNER_PATH),
    "model_implementation_sha256": compute_sha256(MODEL_PATH),
    "normalization_source": {
        "manifest": str(SPLIT_MANIFEST_PATH).replace("\\", "/"),
        "manifest_sha256": compute_sha256(SPLIT_MANIFEST_PATH),
        "ch0_mu": -33.233136989478695,
        "ch0_sigma": 6.489985665955077,
        "ch1_mu": -19.941215852796695,
        "ch1_sigma": 4.531345684833188,
    },
    "benchmark_inventory": {
        "pairing_manifest": str(PAIRING_PATH).replace("\\", "/"),
        "pairing_manifest_sha256": compute_sha256(PAIRING_PATH),
        "scene_count": 450,
        "tile_count_per_mapping": 7200,
        "total_inferences": 14400,
        "stratification": {"Oil": 150, "No oil": 150, "Lookalike": 150},
    },
    "threshold": 0.22,
    "mappings": {
        "MAPPING_A": "Band 1 -> Ch0, Band 2 -> Ch1",
        "MAPPING_B": "Band 2 -> Ch0, Band 1 -> Ch1",
    },
    "run_type": "OFFICIAL_EXTERNAL_BENCHMARK",
    "scientific_status": "FROZEN",
    "official_result": "NOT_YET_AVAILABLE",
}

with open(OUTPUT_DIR / "environment.json", "w", encoding="utf-8") as f:
    json.dump(snapshot, f, indent=2)

with open(OUTPUT_DIR / "pre_execution_snapshot.json", "w", encoding="utf-8") as f:
    json.dump(snapshot, f, indent=2)

print("Runtime snapshot successfully recorded.")
