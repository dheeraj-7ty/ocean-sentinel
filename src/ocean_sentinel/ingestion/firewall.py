"""Scientific firewall enforcing strict isolation of protected external benchmark data.

Crucial Scientific Boundary:
Trujillo Part III (450 scenes: 150 Oil, 150 No oil, 150 Lookalike, 900 GeoTIFFs)
is a FROZEN, CLOSED external evaluation benchmark.
Under the Ocean Sentinel scientific contract, Trujillo Part III MUST NEVER be used for:
- Model training
- Model fine-tuning
- Threshold selection or sweep
- Hyperparameter optimization
- Hard-negative candidate mining
- Checkpoint selection
- Early stopping
- Augmentation design

Protection Level:
The firewall enforces a multi-layered defense against operational leakage:
1. Path & Directory Signatures: Intercepts filesystem paths, parent subdirectories,
   and file naming conventions associated with Part III (e.g., 'external_validation',
   'Images/No oil', 'Images/Lookalike', '_segmentation.tif').
2. Identifier & Stem Signatures: Intercepts scene identifiers, pair IDs, and class-prefixed
   stems (e.g., 'Oil_00000'..'Oil_00149', 'No oil_00000'..'No oil_00149', 'Lookalike_...').
3. Manifest Identity: Intercepts manifest metadata fields (dataset_name, title, source_archive)
   matching Part III naming.
4. Content Hash Identity: Computes bitwise SHA-256 hashes of input raster files against
   the 900 certified Trujillo Part III GeoTIFF hashes. This detects renamed, moved,
   or symlinked/copied Part III rasters that have been stripped of canonical filenames.

Residual Limitations (Why Absolute Isolation Cannot Be Claimed):
- Re-encoded / Modified Rasters: If a Part III raster is re-saved, re-compressed, resampled,
  or converted to an altered byte stream with new GeoTIFF tags, bitwise SHA-256 matching
  will not match, and pathless detection would require deep georeferencing coordinate checks.
- In-Memory Objects: Tensors or raw numpy arrays instantiated directly in memory without
  associated filesystem provenance cannot be detected by filesystem or path inspection.
- Unindexed Artifacts: Files outside the certified 900-GeoTIFF SHA-256 registry that lack
  path or identifier markers cannot be intercepted by content hash.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PureWindowsPath, PurePosixPath
from typing import Any, Iterable, Optional, Sequence, Union

from ocean_sentinel.errors import DatasetErrorCode, DatasetProvenanceError


class PartIIIFirewallViolationError(DatasetProvenanceError):
    """Raised immediately when protected Trujillo Part III benchmark data is detected

    in a development, training, validation, mining, or threshold-tuning context.
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(
            f"SCIENTIFIC FIREWALL VIOLATION: {message}",
            **kwargs,
        )


# Canonical signatures and path fragments identifying protected Trujillo Part III data
PROTECTED_PART_III_PATH_FRAGMENTS: tuple[str, ...] = (
    "external_validation/trujillo_part_iii",
    "external_validation\\trujillo_part_iii",
    "trujillo_part_iii",
    "DATASET_MANIFEST_TRUJILLO_PART_III",
    "trujillo_part_iii_pairing",
    "trujillo_part_iii_eval",
)

# Substrings or directory components unique to Part III class structure
PROTECTED_PART_III_SUBDIRECTORIES: tuple[str, ...] = (
    "Images/No oil",
    "Images\\No oil",
    "Images/Lookalike",
    "Images\\Lookalike",
    "Mask/No oil",
    "Mask\\No oil",
    "Mask/Lookalike",
    "Mask\\Lookalike",
)

# Suffix unique to Part III masks
PROTECTED_PART_III_MASK_SUFFIX: str = "_segmentation.tif"

# Global cache for protected Part III SHA-256 content hashes
_PROTECTED_PART_III_HASHES: Optional[set[str]] = None


def get_protected_part_iii_hashes() -> set[str]:
    """Retrieve the set of uppercase SHA-256 hex digests for all protected Part III GeoTIFFs."""
    global _PROTECTED_PART_III_HASHES
    if _PROTECTED_PART_III_HASHES is not None:
        return _PROTECTED_PART_III_HASHES

    hashes: set[str] = set()
    repo_root = Path(__file__).resolve().parents[3]
    candidate_locations = [
        repo_root / "scratch" / "trujillo_part_iii_extracted_sha256.json",
        Path("scratch/trujillo_part_iii_extracted_sha256.json"),
    ]

    for p in candidate_locations:
        if p.is_file():
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("files", []):
                        h = item.get("sha256")
                        if h:
                            hashes.add(str(h).strip().upper())
                break
            except Exception:
                pass

    _PROTECTED_PART_III_HASHES = hashes
    return _PROTECTED_PART_III_HASHES


def compute_file_sha256(file_path: Union[str, Path]) -> Optional[str]:
    """Compute uppercase SHA-256 digest of a file if it exists and is accessible."""
    try:
        p = Path(file_path)
        if not p.is_file():
            return None
        hasher = hashlib.sha256()
        with p.open("rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest().upper()
    except Exception:
        return None


def is_protected_part_iii_content(file_path: Union[str, Path]) -> bool:
    """Return True if the file content matches a certified Trujillo Part III GeoTIFF SHA-256."""
    h = compute_file_sha256(file_path)
    if not h:
        return False
    protected_hashes = get_protected_part_iii_hashes()
    return h in protected_hashes


def is_protected_part_iii_path(path: Union[str, Path]) -> bool:
    """Return True if the given filesystem path references Trujillo Part III benchmark data."""
    if not path:
        return False
    path_str = str(path).replace("/", "\\").lower()

    for frag in PROTECTED_PART_III_PATH_FRAGMENTS:
        if frag.lower() in path_str:
            return True

    for subdir in PROTECTED_PART_III_SUBDIRECTORIES:
        if subdir.lower() in path_str:
            return True

    # Check for Part III mask naming convention (_segmentation.tif) combined with Part III stem patterns
    norm_path = Path(path)
    if norm_path.name.lower().endswith(PROTECTED_PART_III_MASK_SUFFIX):
        stem = norm_path.stem.lower().replace("_segmentation", "")
        if stem.isdigit() and len(stem) == 5:
            # 5-digit stem 00000-00149 with _segmentation
            try:
                val = int(stem)
                if 0 <= val <= 149:
                    return True
            except ValueError:
                pass

    return False


def is_protected_part_iii_identifier(ident: str) -> bool:
    """Return True if the given identifier string matches a Trujillo Part III scene or pair ID.

    Examples: 'Oil_00000' ... 'Oil_00149', 'No oil_00000', 'Lookalike_00000'.
    """
    if not ident:
        return False
    ident_clean = str(ident).strip()

    # Check pair_id patterns: Class_XXXXX where XXXXX in 00000..00149
    for prefix in ("Oil_", "No oil_", "Lookalike_", "oil_", "no oil_", "lookalike_"):
        if ident_clean.startswith(prefix):
            suffix = ident_clean[len(prefix):]
            if suffix.isdigit() and len(suffix) == 5:
                try:
                    val = int(suffix)
                    if 0 <= val <= 149:
                        return True
                except ValueError:
                    pass

    if is_protected_part_iii_path(ident_clean):
        return True

    return False


def assert_no_part_iii_leakage(
    items: Iterable[Any],
    context: str = "Unspecified Context",
    check_content_hashes: bool = True,
) -> None:
    """Assert that none of the candidate items, paths, or manifests reference Trujillo Part III.

    Performs multi-layered verification:
    1. Path pattern matching
    2. Identifier / stem matching
    3. Bitwise SHA-256 content verification (if item is an accessible file on disk)

    Raises
    ------
    PartIIIFirewallViolationError
        If any item matches a protected Trujillo Part III signature or content hash.
    """
    for item in items:
        if item is None:
            continue

        # Check string / Path representations
        if isinstance(item, (str, Path)):
            if is_protected_part_iii_path(item):
                raise PartIIIFirewallViolationError(
                    f"Attempted to access protected external benchmark path in {context}: {item}"
                )
            if is_protected_part_iii_identifier(str(item)):
                raise PartIIIFirewallViolationError(
                    f"Attempted to access protected external benchmark identifier in {context}: {item}"
                )
            if check_content_hashes:
                try:
                    p = Path(item)
                    if p.is_file() and is_protected_part_iii_content(p):
                        raise PartIIIFirewallViolationError(
                            f"Protected Part III content hash detected in renamed/copied file in {context}: {item}"
                        )
                except (OSError, ValueError):
                    pass

        # Check object with path/stem attributes (e.g. PatchMetadata, TileManifestEntry)
        for attr in ("image_path", "mask_path", "image_relative_path", "mask_relative_path", "path"):
            if hasattr(item, attr):
                val = getattr(item, attr)
                if val:
                    if is_protected_part_iii_path(str(val)):
                        raise PartIIIFirewallViolationError(
                            f"Attempted to load protected external benchmark item in {context} via attribute '{attr}': {val}"
                        )
                    if check_content_hashes:
                        try:
                            p = Path(val)
                            if p.is_file() and is_protected_part_iii_content(p):
                                raise PartIIIFirewallViolationError(
                                    f"Protected Part III content hash detected in {context} via '{attr}': {val}"
                                )
                        except (OSError, ValueError):
                            pass

        for attr in ("pair_id", "patch_stem", "stem", "id"):
            if hasattr(item, attr):
                val = getattr(item, attr)
                if val and is_protected_part_iii_identifier(str(val)):
                    raise PartIIIFirewallViolationError(
                        f"Attempted to load protected external benchmark item in {context} via attribute '{attr}': {val}"
                    )


def validate_manifest_against_firewall(manifest: Any, context: str = "DatasetManifest") -> None:
    """Validate that an entire DatasetManifest contains zero references to Trujillo Part III."""
    # Check dataset identity attributes
    for attr in ("dataset_name", "source_archive", "zenodo_record", "title"):
        if hasattr(manifest, attr):
            val = str(getattr(manifest, attr, "")).lower()
            if any(sig in val for sig in ("part_iii", "part 3", "part3", "part_3")):
                raise PartIIIFirewallViolationError(
                    f"Attempted to load protected external benchmark manifest with {attr}='{getattr(manifest, attr)}' in {context}"
                )

    if hasattr(manifest, "patches"):
        for p in manifest.patches:
            # Fast path check on patches (avoiding expensive hash re-read on all patches during init)
            assert_no_part_iii_leakage([p], context=f"{context}.patches", check_content_hashes=False)

    if hasattr(manifest, "tiles"):
        for t in manifest.tiles:
            # Fast path and identifier check on tiles
            assert_no_part_iii_leakage([t], context=f"{context}.tiles", check_content_hashes=False)

