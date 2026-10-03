"""EXP-07 Pre-Training Runtime Fingerprinting and Parity Verification Tooling.

Provides deterministic machine contracts for EXP07_DIAG01:
- Captures and verifies multi-engine RNG state snapshots (Python, NumPy, PyTorch CPU, CUDA)
- Computes cryptographic SHA-256 digests of complete model state dictionaries
- Enforces dataset lineage and cryptographic manifest bindings before step 1
- Enforces single-variable loss weight vector contract (19 locked invariants, 1 variable)
- Hardens partition firewalls against HOLDOUT and Part-III directory access
- Guarantees zero automatic invalidation for empirical model behaviors (such as background collapse)
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    TORCH_AVAILABLE = False


# Canonical Lineage Hashes
FREEZE_SPEC_SHA256 = "3B362DECD210679DCC7BF5EB6879A020416E4A8BB780845F3FCC59A4DFBF3B35"
PHYSICAL_MANIFEST_SHA256 = "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"
PARTITION_MANIFEST_SHA256 = "757DEAF7A7E72BE331843B518A99AF32E14D68A080822F1D9B4FDBADF889F94D"
PARENT_CLUSTER_MANIFEST_SHA256 = "08ED21FBB492363E1D05040020F73177BFD4DC84F1A39E2D9C5C9B38BC97D10B"
TAXONOMY_SPEC_SHA256 = "182722015335317286CDAF43F2F73353CDB9B302C91F377FE0A16E5DFE508B85"
WEIGHT_PROVENANCE_SHA256 = "C3B8DB7D971A22BC45D29AF4F49F3D6C4EC3549E1B13BAAB998DBA36006F858B"

CANONICAL_HISTORICAL_C16_LITERALS = [
    0.403935, 2.450546, 0.876692, 0.945945, 0.648189, 4.211476,
    0.719641, 2.956203, 1.064525, 1.882870, 0.387652, 18.243211
]
UNIFORM_TREATMENT_LITERALS = [1.0] * 12

FORBIDDEN_DATA_PATHS = [
    "data/ops02/holdout",
    "data/trujillo_part_iii",
    "experiments/performance/phase_6_part_iii_external_evaluation",
]


def capture_rng_snapshot() -> Dict[str, Any]:
    """Capture complete state across all active random engines."""
    snapshot: Dict[str, Any] = {
        "python_random_state": random.getstate(),
        "numpy_random_state": np.random.get_state(),
    }
    if TORCH_AVAILABLE and torch is not None:
        snapshot["torch_cpu_state"] = torch.get_rng_state()
        if torch.cuda.is_available():
            snapshot["torch_cuda_states"] = torch.cuda.get_rng_state_all()
        else:
            snapshot["torch_cuda_states"] = None
    return snapshot


def restore_rng_snapshot(snapshot: Dict[str, Any]) -> None:
    """Restore state deterministically across all random engines."""
    random.setstate(snapshot["python_random_state"])
    np.random.set_state(snapshot["numpy_random_state"])
    if TORCH_AVAILABLE and torch is not None:
        if "torch_cpu_state" in snapshot and snapshot["torch_cpu_state"] is not None:
            torch.set_rng_state(snapshot["torch_cpu_state"])
        if torch.cuda.is_available() and snapshot.get("torch_cuda_states") is not None:
            torch.cuda.set_rng_state_all(snapshot["torch_cuda_states"])


def fingerprint_model_state_dict(state_dict: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 digest of a PyTorch model state dictionary."""
    hasher = hashlib.sha256()
    for key in sorted(state_dict.keys()):
        val = state_dict[key]
        hasher.update(key.encode("utf-8"))
        if hasattr(val, "cpu"):
            arr = val.detach().cpu().numpy()
            hasher.update(arr.tobytes())
        elif isinstance(val, np.ndarray):
            hasher.update(val.tobytes())
        else:
            hasher.update(str(val).encode("utf-8"))
    return hasher.hexdigest().upper()


def assert_quarantine_firewall(paths: List[Union[str, Path]]) -> None:
    """Verify that no protected HOLDOUT or Part-III paths are present in access paths."""
    for p in paths:
        normalized = str(p).replace("\\", "/").lower()
        for forbidden in FORBIDDEN_DATA_PATHS:
            if forbidden.lower() in normalized:
                raise PermissionError(
                    f"Firewall breach blocked: Access to protected path '{p}' violates quarantine rules."
                )


def assert_dataset_lineage_hashes(repo_root: Path) -> Dict[str, str]:
    """Verify cryptographic bindings for dataset specifications and manifests."""
    manifest_checks = {
        "freeze_spec": (repo_root / "data" / "ops02" / "OPS02_DATASET_FREEZE_SPEC_v1.0.1.json", FREEZE_SPEC_SHA256),
        "physical_manifest": (repo_root / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json", PHYSICAL_MANIFEST_SHA256),
        "partition_manifest": (repo_root / "data" / "ops02" / "manifests" / "ops02_partition_manifest_v1.json", PARTITION_MANIFEST_SHA256),
        "parent_cluster_manifest": (repo_root / "data" / "ops02" / "manifests" / "ops02_parent_cluster_manifest_v1.json", PARENT_CLUSTER_MANIFEST_SHA256),
        "taxonomy_spec": (repo_root / "data" / "ops02" / "audits" / "ops02_c19_taxonomy_canonicalization_v1.json", TAXONOMY_SPEC_SHA256),
    }

    verified_hashes: Dict[str, str] = {}
    for name, (path, expected_hash) in manifest_checks.items():
        if not path.exists():
            raise FileNotFoundError(f"Authoritative artifact missing: {path}")
        computed_hash = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        if computed_hash != expected_hash:
            raise ValueError(
                f"Lineage integrity violation for {name} ({path}):\n"
                f"  Expected: {expected_hash}\n"
                f"  Computed: {computed_hash}"
            )
        verified_hashes[name] = computed_hash

    return verified_hashes


def assert_loss_weight_vector_contract(
    control_vector: Union[List[float], Any],
    treatment_vector: Union[List[float], Any]
) -> None:
    """Assert exact definition of single independent variable CLASS_LOSS_WEIGHT_VECTOR."""
    if TORCH_AVAILABLE and isinstance(control_vector, torch.Tensor):
        expected_t = torch.tensor(CANONICAL_HISTORICAL_C16_LITERALS, dtype=torch.float32, device=control_vector.device)
        if not torch.equal(control_vector, expected_t):
            raise ValueError(
                f"Control weight tensor does not bitwise match canonical C16 float32 tensor:\n"
                f"  Expected: {expected_t}\n"
                f"  Actual:   {control_vector}"
            )
    else:
        c_list = [round(float(x), 6) for x in control_vector]
        if c_list != CANONICAL_HISTORICAL_C16_LITERALS:
            raise ValueError(
                f"Control vector does not match canonical historical C16 literals:\n"
                f"  Expected: {CANONICAL_HISTORICAL_C16_LITERALS}\n"
                f"  Actual:   {c_list}"
            )

    if TORCH_AVAILABLE and isinstance(treatment_vector, torch.Tensor):
        expected_treat_t = torch.tensor(UNIFORM_TREATMENT_LITERALS, dtype=torch.float32, device=treatment_vector.device)
        if not torch.equal(treatment_vector, expected_treat_t):
            raise ValueError(
                f"Treatment weight tensor does not bitwise match uniform [1.0]*12 float32 tensor:\n"
                f"  Expected: {expected_treat_t}\n"
                f"  Actual:   {treatment_vector}"
            )
    else:
        t_list = [round(float(x), 6) for x in treatment_vector]
        if t_list != UNIFORM_TREATMENT_LITERALS:
            raise ValueError(
                f"Treatment vector does not match uniform [1.0]*12 contract:\n"
                f"  Expected: {UNIFORM_TREATMENT_LITERALS}\n"
                f"  Actual:   {t_list}"
            )


def verify_runtime_initialization_parity(
    control_fingerprint: Dict[str, Any],
    treatment_fingerprint: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """Assert bitwise initial state parity between control and treatment runs."""
    mismatches: List[str] = []
    required_keys = [
        "initial_model_state_sha256",
        "sample_schedule_sha256",
        "batch_schedule_sha256",
        "dataset_manifest_sha256",
        "partition_manifest_sha256",
        "freeze_spec_sha256",
    ]

    for key in required_keys:
        val_c = control_fingerprint.get(key)
        val_t = treatment_fingerprint.get(key)
        if val_c is None or val_t is None:
            mismatches.append(f"Missing fingerprint key: {key} (control: {val_c}, treatment: {val_t})")
        elif val_c != val_t:
            mismatches.append(f"Parity mismatch on {key}: control={val_c} vs treatment={val_t}")

    # Verify that ONLY the loss weight vector differs
    weights_c = control_fingerprint.get("loss_weight_vector_sha256")
    weights_t = treatment_fingerprint.get("loss_weight_vector_sha256")
    if weights_c == weights_t:
        mismatches.append(
            f"Single-variable violation: Control and Treatment loss weight vector hashes are identical ({weights_c}). "
            "They must differ by design."
        )

    return (len(mismatches) == 0, mismatches)
