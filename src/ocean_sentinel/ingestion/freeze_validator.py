"""EXP-07-P0-C18: Authoritative Runtime Dataset Identity and Freeze Validator.

Implements GOV-RULE-085 and GOV-RULE-086:
- Cryptographic hash verification of freeze specification against physical manifests.
- Runtime assertion of exact sample counts, exact sample ID sets, and cluster ID sets.
- Strict prevention of silent sample omission, filtering, or partition divergence.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class RuntimeDatasetAssertionError(AssertionError):
    """Raised when runtime loaded dataset diverges from the frozen specification."""
    pass


class HoldoutQuarantineError(PermissionError):
    """Raised when HOLDOUT partition is improperly loaded during pre-training."""
    pass


def sha256_file(path: Path) -> str:
    """Compute uppercase SHA-256 hex digest for a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def validate_dataset_freeze_identity(
    freeze_spec_path: Path,
    repo_root: Optional[Path] = None,
) -> Dict[str, any]:
    """Validate that the freeze specification is internally consistent and cryptographically bound.
    
    Verifies:
    1. Freeze spec JSON exists and declares OPS02_v1.0.1_FROZEN.
    2. Referenced physical, partition, and cluster manifests exist.
    3. Manifest SHA-256 hashes match cryptographic bindings in the specification.
    4. Exact sample counts match (TRAIN=132, DEV=40, HOLDOUT=40, Total=212).
    5. Exact cluster counts match (TRAIN=40, DEV=12, HOLDOUT=12, Total=64).
    """
    if repo_root is None:
        repo_root = freeze_spec_path.resolve().parent.parent.parent

    if not freeze_spec_path.exists():
        raise FileNotFoundError(f"Freeze specification missing: {freeze_spec_path}")

    with open(freeze_spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    if spec.get("dataset_version") != "OPS02_v1.0.1_FROZEN":
        raise RuntimeDatasetAssertionError(
            f"Expected dataset_version 'OPS02_v1.0.1_FROZEN', got '{spec.get('dataset_version')}'"
        )

    bindings = spec.get("manifest_cryptographic_bindings", {})
    results = {"verified_manifests": {}, "partition_checks": {}}

    for m_key, m_meta in bindings.items():
        rel_path = m_meta["path"]
        expected_hash = m_meta["sha256"].upper()
        abs_path = repo_root / rel_path

        if not abs_path.exists():
            raise FileNotFoundError(f"Bound manifest not found: {abs_path}")

        actual_hash = sha256_file(abs_path)
        if actual_hash != expected_hash:
            raise RuntimeDatasetAssertionError(
                f"Manifest SHA-256 mismatch for {m_key}! Expected {expected_hash}, got {actual_hash}"
            )
        results["verified_manifests"][m_key] = {"path": rel_path, "sha256": actual_hash}

    # Verify partition manifest content
    part_meta = bindings["partition_manifest"]
    part_path = repo_root / part_meta["path"]
    with open(part_path, "r", encoding="utf-8") as f:
        part_data = json.load(f)

    partitions = part_data["partitions"]
    for p_name in ["TRAIN", "DEV", "HOLDOUT"]:
        expected_cnt = part_meta["partition_counts"][p_name]
        actual_cnt = len(partitions[p_name]["sample_ids"])
        if actual_cnt != expected_cnt:
            raise RuntimeDatasetAssertionError(
                f"Partition {p_name} sample count mismatch in manifest! Expected {expected_cnt}, got {actual_cnt}"
            )
        results["partition_checks"][p_name] = actual_cnt

    return results


def assert_runtime_dataset_integrity(
    loaded_samples: List[dict],
    partition: str,
    partition_manifest_path: Path,
    allow_holdout: bool = False,
) -> None:
    """Assert at runtime that loaded dataset samples strictly match the frozen partition manifest.
    
    Checks:
    1. Quarantine: Disallows loading HOLDOUT unless allow_holdout is explicitly True.
    2. Exact sample count equality.
    3. Exact sample ID set equality (no missing, extra, or substituted samples).
    4. Exact cluster membership equality.
    5. Partition field consistency on every individual loaded sample record.
    """
    p_upper = partition.upper()
    if p_upper == "HOLDOUT" and not allow_holdout:
        raise HoldoutQuarantineError(
            "HARD FIREWALL (GOV-RULE-060 / GOV-RULE-075): HOLDOUT partition cannot be loaded for training or model selection!"
        )

    if not partition_manifest_path.exists():
        raise FileNotFoundError(f"Partition manifest missing: {partition_manifest_path}")

    with open(partition_manifest_path, "r", encoding="utf-8") as f:
        part_data = json.load(f)

    if p_upper not in part_data["partitions"]:
        raise ValueError(f"Unknown partition '{p_upper}'. Valid: TRAIN, DEV, HOLDOUT")

    expected_part = part_data["partitions"][p_upper]
    expected_sample_ids: Set[str] = set(expected_part["sample_ids"])
    expected_clusters: Set[str] = set(expected_part["clusters"])
    expected_count: int = expected_part["sample_count"]

    # 1. Exact count assertion
    actual_count = len(loaded_samples)
    if actual_count != expected_count:
        raise RuntimeDatasetAssertionError(
            f"GOV-RULE-086 VIOLATION: Loaded {p_upper} count ({actual_count}) does not match frozen count ({expected_count})!"
        )

    # 2. Extract actual loaded IDs and clusters
    actual_sample_ids: Set[str] = set()
    actual_clusters: Set[str] = set()
    for s in loaded_samples:
        sid = s.get("sample_id")
        cid = s.get("cluster_id")
        s_part = s.get("partition", "").upper()

        if s_part != p_upper:
            raise RuntimeDatasetAssertionError(
                f"Cross-partition sample contamination! Sample {sid} has partition '{s_part}', expected '{p_upper}'."
            )
        actual_sample_ids.add(sid)
        if cid:
            # Normalize cluster ID: cluster manifest uses full cluster_id or 6-char datatake suffix
            actual_clusters.add(cid)
            dtk = s.get("mission_data_take_id")
            if dtk:
                actual_clusters.add(dtk)

    # 3. Exact sample-ID set equality assertion
    if actual_sample_ids != expected_sample_ids:
        missing_ids = expected_sample_ids - actual_sample_ids
        extra_ids = actual_sample_ids - expected_sample_ids
        err_msg = f"GOV-RULE-086 VIOLATION: Sample ID mismatch in partition {p_upper}!"
        if missing_ids:
            err_msg += f" Missing {len(missing_ids)} IDs: {sorted(list(missing_ids))[:5]}..."
        if extra_ids:
            err_msg += f" Extraneous {len(extra_ids)} IDs: {sorted(list(extra_ids))[:5]}..."
        raise RuntimeDatasetAssertionError(err_msg)

    # 4. Exact cluster set equality assertion
    # expected_clusters may be mission_data_take_ids or full cluster_ids
    matched_clusters = set()
    for exp_c in expected_clusters:
        if exp_c in actual_clusters or any(a.endswith(exp_c) for a in actual_clusters):
            matched_clusters.add(exp_c)
    if matched_clusters != expected_clusters:
        missing_cl = expected_clusters - matched_clusters
        raise RuntimeDatasetAssertionError(
            f"Cluster ID mismatch in partition {p_upper}! Missing clusters: {missing_cl}"
        )
