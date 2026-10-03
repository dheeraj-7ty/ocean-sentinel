"""Temporal Pair Forensic & Duplicate-Image Guard V1.

Provides fail-closed scientific verification at the orchestration/scenario boundary:
- Locates source image artifacts for T0 and T1.
- Computes canonical SHA-256 for both rasters.
- If hashes are identical, rejects pair as TEMPORAL_PAIR_INVALID_DUPLICATE_IMAGE.
- Forbids treating annotation mask differences as physical temporal change.
- Enforces TEMPORAL_ORDER_UNKNOWN for candidate pairs (disallowing chronological inference from filenames).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
import rasterio

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def compute_file_sha256(filepath: Union[str, Path]) -> str:
    """Compute canonical full SHA-256 of a file."""
    p = Path(filepath)
    if not p.is_file():
        raise FileNotFoundError(f"File not found for hashing: {p}")
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1048576):
            h.update(chunk)
    return h.hexdigest()


def check_temporal_pair_validity(
    t0_path: Union[str, Path],
    t1_path: Union[str, Path],
) -> Dict[str, Any]:
    """Inspect and validate a candidate temporal image pair before execution.
    
    Returns a structured verdict. If T0 and T1 source rasters are byte-for-byte
    identical, returns status TEMPORAL_PAIR_INVALID_DUPLICATE_IMAGE and fails closed.
    """
    p0 = Path(t0_path)
    p1 = Path(t1_path)

    if not p0.is_file():
        return {
            "valid": False,
            "status": "SOURCE_NOT_FOUND",
            "reason": f"T0 source raster not found: {p0}",
            "source_pair_status": "SOURCE_NOT_FOUND",
            "temporal_status": "BLOCKED",
        }
    if not p1.is_file():
        return {
            "valid": False,
            "status": "SOURCE_NOT_FOUND",
            "reason": f"T1 source raster not found: {p1}",
            "source_pair_status": "SOURCE_NOT_FOUND",
            "temporal_status": "BLOCKED",
        }

    sha0 = compute_file_sha256(p0)
    sha1 = compute_file_sha256(p1)

    if sha0 == sha1:
        return {
            "valid": False,
            "status": "TEMPORAL_PAIR_INVALID_DUPLICATE_IMAGE",
            "source_pair_status": "INVALID_DUPLICATE_IMAGE_PAIR",
            "temporal_status": "BLOCKED",
            "reason": "T0 and T1 source rasters are byte-for-byte identical.",
            "t0_sha256": sha0,
            "t1_sha256": sha1,
            "t0_path": str(p0),
            "t1_path": str(p1),
            "scientific_interpretation": (
                "T0 and T1 source rasters are byte-for-byte identical observations. "
                "Any apparent difference in associated annotation masks represents annotation/label divergence "
                "whose cause is NOT established by this evidence alone. "
                "Such mask differences MUST NOT be interpreted as physical temporal SAR change. "
                "Physical temporal differencing is invalid for this pair."
            ),
        }

    # Distinct rasters: inspect geometry
    with rasterio.open(p0) as src0, rasterio.open(p1) as src1:
        dim0 = (src0.height, src0.width)
        dim1 = (src1.height, src1.width)
        b0 = (src0.bounds.left, src0.bounds.bottom, src0.bounds.right, src0.bounds.top)
        b1 = (src1.bounds.left, src1.bounds.bottom, src1.bounds.right, src1.bounds.top)
        crs0 = str(src0.crs) if src0.crs else None
        crs1 = str(src1.crs) if src1.crs else None

        overlap = (
            b0[0] < b1[2]
            and b0[2] > b1[0]
            and b0[1] < b1[3]
            and b0[3] > b1[1]
        )

    return {
        "valid": True,
        "status": "POTENTIAL_TEMPORAL_PAIR",
        "source_pair_status": "POTENTIAL_TEMPORAL_PAIR",
        "temporal_status": "PENDING_AUTHORITATIVE_TIMESTAMP",
        "temporal_chronology": "TEMPORAL_ORDER_UNKNOWN",
        "reason": None,
        "t0_sha256": sha0,
        "t1_sha256": sha1,
        "same_dimensions": dim0 == dim1,
        "crs_t0": crs0,
        "crs_t1": crs1,
        "spatial_overlap": overlap,
        "chronology_warning": (
            "Numeric filename order, archive order, train/test order, or directory order "
            "CANNOT be used to infer acquisition chronology. Authoritative timestamps required."
        ),
    }


def classify_duplicate_mask_difference(
    mask0_path: Union[str, Path],
    mask1_path: Union[str, Path],
) -> Dict[str, Any]:
    """Classify mask relationship for confirmed duplicate image rasters."""
    p0 = Path(mask0_path)
    p1 = Path(mask1_path)

    sha0 = compute_file_sha256(p0)
    sha1 = compute_file_sha256(p1)

    with rasterio.open(p0) as src0, rasterio.open(p1) as src1:
        arr0 = src0.read(1)
        arr1 = src1.read(1)

    all_equal = np.array_equal(arr0, arr1)
    diff_pixels = int(np.sum(arr0 != arr1))
    fg0 = int(np.sum(arr0 > 0))
    fg1 = int(np.sum(arr1 > 0))

    classification = (
        "IDENTICAL_IMAGE_IDENTICAL_ANNOTATION"
        if all_equal
        else "IDENTICAL_IMAGE_DIFFERENT_ANNOTATION"
    )

    return {
        "classification": classification,
        "all_masks_equal": all_equal,
        "mask0_sha256": sha0,
        "mask1_sha256": sha1,
        "mask0_foreground_pixels": fg0,
        "mask1_foreground_pixels": fg1,
        "pixel_difference_count": diff_pixels,
        "scientific_interpretation": (
            "Underlying source rasters are byte-for-byte identical; masks differ. "
            "The difference is annotation/label divergence. The cause of that divergence "
            "(human re-annotation, model prediction, labeling noise, or other) is NOT "
            "established by this evidence. It MUST NOT be interpreted as physical temporal SAR change."
        ),
    }
