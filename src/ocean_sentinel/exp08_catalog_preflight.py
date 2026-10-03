"""EXP-08 Catalog Preflight — Deterministic CDSE Catalog Resolution Firewall.

This module implements the mandatory pre-inference catalog resolution step for EXP-08.
It must run BEFORE any model inference. If any required DARTIS scene does not satisfy
the frozen identity rule (exactly one physical acquisition resolved with status
RESOLVED_UNIQUE), the scientific run is aborted and inference is NOT called.

Firewall rule:
    BEFORE any inference forward pass, every DARTIS scene in the evaluation population
    must have status RESOLVED_UNIQUE in the preflight manifest. Any other status
    constitutes a blocking failure.

Status vocabulary:
    RESOLVED_UNIQUE    — exactly one physical Sentinel-1 product identified
    NO_MATCH           — zero products found in CDSE Catalog
    MULTIPLE_MATCHES   — two or more candidate products; ambiguous
    QUERY_ERROR        — CDSE Catalog API returned an error
    INVALID_METADATA   — DARTIS record has missing/malformed required fields

Denominator semantics:
    TARGET_POPULATION            — all unique DARTIS scenes submitted for preflight
    EVALUATION_ELIGIBLE          — scenes with RESOLVED_UNIQUE status
    INVALID_OR_UNRESOLVED_COUNT  — scenes not RESOLVED_UNIQUE (must be reported separately)

ABSOLUTE SCIENTIFIC FIREWALL:
    EXECUTION_AUTHORIZED = FALSE
    This module does NOT perform inference, training, or holdout access.
    It only establishes the physical acquisition identity of each scene.

Protocol reference: EXP08_CORRECTED_PROTOCOL_V3_4 §8, §17
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status constants (frozen vocabulary)
# ---------------------------------------------------------------------------
STATUS_RESOLVED_UNIQUE = "RESOLVED_UNIQUE"
STATUS_NO_MATCH = "NO_MATCH"
STATUS_MULTIPLE_MATCHES = "MULTIPLE_MATCHES"
STATUS_QUERY_ERROR = "QUERY_ERROR"
STATUS_INVALID_METADATA = "INVALID_METADATA"

VALID_STATUSES = frozenset({
    STATUS_RESOLVED_UNIQUE,
    STATUS_NO_MATCH,
    STATUS_MULTIPLE_MATCHES,
    STATUS_QUERY_ERROR,
    STATUS_INVALID_METADATA,
})

# Patch status constants (frozen patch-level accounting vocabulary)
PATCH_TARGET_INCLUDED = "TARGET_INCLUDED"
PATCH_TARGET_EXCLUDED = "TARGET_EXCLUDED"

PATCH_EVALUATION_ELIGIBLE = "EVALUATION_ELIGIBLE"
PATCH_EVALUATION_UNRESOLVED = "UNRESOLVED_ACQUISITION"
PATCH_EVALUATION_EVALUATED = "EVALUATED"

VALID_PATCH_TARGET_STATUSES = frozenset({
    PATCH_TARGET_INCLUDED,
    PATCH_TARGET_EXCLUDED,
})

VALID_PATCH_EVALUATION_STATUSES = frozenset({
    PATCH_EVALUATION_ELIGIBLE,
    PATCH_EVALUATION_UNRESOLVED,
    PATCH_EVALUATION_EVALUATED,
})

# The protocol version this firewall implements.
PREFLIGHT_PROTOCOL_VERSION = "EXP08_CORRECTED_PROTOCOL_V3_5"

# EXP-08 frozen Catalog resolution rule parameters.
# Spatio-temporal uniqueness window matching Phase 11-R5.1 pilot.
CATALOG_WINDOW_SECONDS = 25
CATALOG_PLATFORM = "sentinel-1"
CATALOG_INSTRUMENT_MODE = "IW"
CATALOG_POLARIZATION = "DV"  # Dual-VV-VH


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PreflightRecord:
    """Per-scene preflight resolution record.

    Distinguishes:
    - catalog_item_count: raw count of STAC/catalog items returned (may include COG, original,
      other representation variants of the same physical acquisition).
    - physical_acquisition_count: count of DISTINCT physical acquisitions after deduplicating
      representation variants (original vs _COG suffix, etc.). RESOLVED_UNIQUE requires exactly 1.
    - representation_count: count of catalog items sharing the resolved physical acquisition ID
      (e.g. original + COG = 2 representations of 1 physical acquisition).

    Fields with Optional[...] default to None for records that did not reach the query stage.
    """
    dartis_scene_id: str              # DARTIS Sentinel_ID (raw, may contain semicolons)
    acquisition_start: Optional[str] = None    # ISO-8601 UTC acquisition start
    acquisition_stop: Optional[str] = None     # ISO-8601 UTC acquisition stop
    bbox: Optional[List[float]] = None         # [min_lon, min_lat, max_lon, max_lat] EPSG:4326
    catalog_item_count: Optional[int] = None   # Raw count of STAC/catalog items returned
    physical_acquisition_count: Optional[int] = None  # Distinct physical acquisitions after dedup
    representation_count: Optional[int] = None  # Representations of the resolved physical acquisition
    resolved_physical_acquisition_id: Optional[str] = None  # Canonical physical ID (without _COG suffix)
    resolved_catalog_id: Optional[str] = None   # Exact catalog item ID (may be COG or original)
    resolution_status: str = STATUS_INVALID_METADATA
    resolution_reason: str = ""
    preflight_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    protocol_version: str = PREFLIGHT_PROTOCOL_VERSION

    def is_eligible(self) -> bool:
        """Return True if and only if this scene is RESOLVED_UNIQUE."""
        return self.resolution_status == STATUS_RESOLVED_UNIQUE

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PreflightManifest:
    """Complete preflight manifest for an EXP-08 run.

    Attributes:
        target_population: All unique DARTIS scenes submitted for preflight.
        evaluation_eligible: Scenes with RESOLVED_UNIQUE status.
        invalid_or_unresolved_count: Scenes that are NOT RESOLVED_UNIQUE.
        records: Per-scene resolution records.
        preflight_passed: True only if ALL scenes are RESOLVED_UNIQUE.
        preflight_timestamp: ISO-8601 UTC manifest creation time.
        protocol_version: Frozen protocol version string.
    """
    target_population: int = 0
    evaluation_eligible: int = 0
    invalid_or_unresolved_count: int = 0
    preflight_passed: bool = False
    preflight_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    protocol_version: str = PREFLIGHT_PROTOCOL_VERSION
    records: List[PreflightRecord] = field(default_factory=list)

    def compute_summary(self) -> None:
        """Recompute aggregate statistics from individual records."""
        self.target_population = len(self.records)
        eligible = [r for r in self.records if r.is_eligible()]
        self.evaluation_eligible = len(eligible)
        self.invalid_or_unresolved_count = self.target_population - self.evaluation_eligible
        self.preflight_passed = (
            self.target_population > 0
            and self.invalid_or_unresolved_count == 0
        )

    def as_dict(self) -> Dict[str, Any]:
        d = {
            "target_population": self.target_population,
            "evaluation_eligible": self.evaluation_eligible,
            "invalid_or_unresolved_count": self.invalid_or_unresolved_count,
            "preflight_passed": self.preflight_passed,
            "preflight_timestamp": self.preflight_timestamp,
            "protocol_version": self.protocol_version,
            "records": [r.as_dict() for r in self.records],
        }
        return d


class PreflightFirewallError(Exception):
    """Raised when the preflight firewall blocks inference.

    This exception is raised if any scene is NOT RESOLVED_UNIQUE at the
    time inference is requested. Model forward passes must NEVER be called
    if this exception would be raised.
    """
    pass


# ---------------------------------------------------------------------------
# Core preflight logic (pure Python; does not call model)
# ---------------------------------------------------------------------------

# Known representation-variant suffixes that identify different catalog representations
# of the same underlying physical acquisition (not different physical scenes).
_COG_SUFFIXES = ("_COG", "_cog")


def normalize_to_physical_id(catalog_item_id: str) -> str:
    """Normalize a CDSE catalog item ID to its canonical physical acquisition ID.

    CDSE STAC items for Sentinel-1 GRD products may appear in multiple representations:
        Original: S1A_IW_GRDH_1SDV_20190101T..._F282
        COG:      S1A_IW_GRDH_1SDV_20190101T..._F282_COG

    These represent the SAME physical observation. Only the storage/encoding format differs.
    This function strips known representation-variant suffixes to obtain the canonical
    physical acquisition ID, which is used for deduplication.

    IMPORTANT: This function must NEVER be used to merge genuinely different acquisitions.
    It is only for representation-variant deduplication as a controlled fallback (Tier 3).

    Args:
        catalog_item_id: A CDSE catalog item ID string.

    Returns:
        Canonical physical acquisition ID with representation suffixes removed.
    """
    pid = catalog_item_id
    for suffix in _COG_SUFFIXES:
        if pid.endswith(suffix):
            pid = pid[: -len(suffix)]
            break
    return pid


def extract_physical_acquisition_id(item: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """Resolve physical acquisition identity via the 3-tier provenance hierarchy.

    Hierarchy:
        Tier 1 (Explicit Provider Linkage): Machine-readable source product linkage
            (e.g., 'source_product', 'source_product_id', or nested under 'properties').
            When available, this is the authoritative physical ID.
        Tier 2 (Documented Acquisition Fields): If no explicit provider link is present
            and the item is not a representation variant (e.g. standard SAFE product),
            the item ID itself represents the physical acquisition, validated by
            acquisition metadata.
        Tier 3 (Controlled Representation Suffix Fallback): Suffix normalization (stripping
            '_COG'/'_cog') is permitted ONLY as a controlled fallback when the suffix is
            documented by the provider AND the item contains sufficient acquisition provenance
            (e.g., valid start/stop timestamps). If a representation variant lacks sufficient
            acquisition provenance, it cannot be safely merged or confirmed.

    Returns:
        (canonical_physical_id, tier_description)
        If provenance is insufficient, canonical_physical_id is None.
    """
    item_id = item.get("id") or item.get("product_id") or ""
    if not item_id or not isinstance(item_id, str):
        return None, "NO_IDENTIFIER"

    props = item.get("properties") if isinstance(item.get("properties"), dict) else {}

    # Tier 1: Explicit machine-readable provider linkage
    source_link = (
        item.get("source_product")
        or item.get("source_product_id")
        or item.get("origin_product_id")
        or props.get("source_product")
        or props.get("parentIdentifier")
        or props.get("origin_product_id")
    )
    if source_link and isinstance(source_link, str) and source_link.strip():
        return source_link.strip(), "TIER_1_EXPLICIT_PROVIDER_LINKAGE"

    # Check if item is a representation variant
    is_representation_variant = any(item_id.endswith(sfx) for sfx in _COG_SUFFIXES)

    # Documented acquisition fields (Tier 2/3 validation)
    start_time = (
        item.get("startDatetime")
        or item.get("start_time")
        or props.get("startDatetime")
        or props.get("start_time")
    )

    if not is_representation_variant:
        # Standard acquisition product (Tier 2)
        return item_id, "TIER_2_DOCUMENTED_PRODUCT_IDENTITY"

    # Tier 3: Controlled representation suffix fallback
    # Requires sufficient provenance (at minimum, valid acquisition timestamp)
    if not start_time:
        # Insufficient provenance to confirm physical identity of representation variant
        return None, "INSUFFICIENT_PROVENANCE"

    canonical_id = normalize_to_physical_id(item_id)
    return canonical_id, "TIER_3_CONTROLLED_SUFFIX_FALLBACK"


def resolve_dartis_scene(
    dartis_scene_id: str,
    catalog_client: Any,
    *,
    window_seconds: int = CATALOG_WINDOW_SECONDS,
) -> PreflightRecord:
    """Attempt to resolve a single DARTIS Sentinel_ID to a unique physical acquisition.

    SCIENTIFIC IDENTITY RULE:
    The unit of identity is the PHYSICAL ACQUISITION, not the catalog item.
    Multiple catalog items (original + COG) may represent the same physical observation.
    RESOLVED_UNIQUE requires exactly ONE physical acquisition after deduplication.

    This function NEVER calls the inference model. It performs only CDSE Catalog
    API queries to establish physical acquisition identity.

    Args:
        dartis_scene_id: Raw DARTIS Sentinel_ID field value (may contain semicolons
            for boundary-sliced scenes). The first semicolon-delimited token is the
            primary SAFE product ID.
        catalog_client: An object with a .query(scene_id, window_seconds) method
            returning a list of catalog results. Must be injected.
        window_seconds: Temporal search window in seconds around the acquisition.
            Defaults to CATALOG_WINDOW_SECONDS (25 seconds per protocol).

    Returns:
        PreflightRecord with resolution_status set to one of the frozen constants.
        Populates catalog_item_count (raw), physical_acquisition_count (deduplicated),
        and representation_count (representations of the resolved single physical ID).
    """
    record = PreflightRecord(dartis_scene_id=dartis_scene_id)

    if not dartis_scene_id or not isinstance(dartis_scene_id, str):
        record.resolution_status = STATUS_INVALID_METADATA
        record.resolution_reason = "dartis_scene_id is empty or non-string"
        return record

    # Semicolon-separated SAFE IDs: use the first token as primary ID.
    primary_id = dartis_scene_id.split(";")[0].strip()
    if not primary_id:
        record.resolution_status = STATUS_INVALID_METADATA
        record.resolution_reason = "Primary SAFE ID (first semicolon token) is empty"
        return record

    try:
        results = catalog_client.query(primary_id, window_seconds=window_seconds)
    except Exception as exc:
        record.resolution_status = STATUS_QUERY_ERROR
        record.resolution_reason = f"Catalog API query failed: {type(exc).__name__}: {exc}"
        return record

    if results is None:
        results = []

    catalog_item_count = len(results)
    record.catalog_item_count = catalog_item_count

    if catalog_item_count == 0:
        record.physical_acquisition_count = 0
        record.representation_count = 0
        record.resolution_status = STATUS_NO_MATCH
        record.resolution_reason = (
            f"No CDSE product found within {window_seconds}s window for scene {primary_id}"
        )
        return record

    # Deduplicate by physical acquisition ID using 3-tier provenance hierarchy.
    physical_id_to_items: Dict[str, List[Dict[str, Any]]] = {}
    for item in results:
        phys_id, tier = extract_physical_acquisition_id(item)
        if phys_id is None:
            # Item has insufficient provenance or invalid ID (Case D)
            item_id = item.get("id") or item.get("product_id") or "unknown"
            record.physical_acquisition_count = 0
            record.representation_count = 0
            record.resolution_status = STATUS_INVALID_METADATA
            record.resolution_reason = (
                f"Catalog item '{item_id}' has insufficient acquisition provenance "
                f"({tier}); scene identity cannot be safely resolved"
            )
            return record
        physical_id_to_items.setdefault(phys_id, []).append(item)

    # Validate that items sharing the same physical ID do not have conflicting acquisition timestamps.
    # Controlled fallback requires matching acquisition fields to justify the merge.
    validated_physical_groups: Dict[str, List[Dict[str, Any]]] = {}
    for pid, items in physical_id_to_items.items():
        start_times = set()
        for it in items:
            st = it.get("startDatetime") or it.get("start_time") or (
                it.get("properties", {}).get("startDatetime") if isinstance(it.get("properties"), dict) else None
            )
            if st:
                start_times.add(st)
        if len(start_times) > 1:
            # Conflicting acquisition timestamps: genuinely distinct observations despite similar IDs!
            # Must NOT merge them. Split into separate physical acquisitions.
            for idx, it in enumerate(items):
                validated_physical_groups[f"{pid}#conflict_{idx}"] = [it]
        else:
            validated_physical_groups[pid] = items

    physical_id_to_items = validated_physical_groups
    physical_acquisition_count = len(physical_id_to_items)
    record.physical_acquisition_count = physical_acquisition_count

    if physical_acquisition_count == 0:
        # Should not happen if catalog_item_count > 0, but guard defensively.
        record.representation_count = 0
        record.resolution_status = STATUS_QUERY_ERROR
        record.resolution_reason = "Catalog returned items but none had identifiable product IDs"
        return record

    elif physical_acquisition_count > 1:
        # Multiple DISTINCT physical acquisitions: genuinely ambiguous.
        record.representation_count = catalog_item_count  # all items span multiple physical scenes
        first_items = list(physical_id_to_items.values())[0]
        _populate_record_from_result(record, first_items[0])
        record.resolution_status = STATUS_MULTIPLE_MATCHES
        record.resolution_reason = (
            f"{catalog_item_count} catalog items found resolving to "
            f"{physical_acquisition_count} distinct physical acquisitions "
            f"(after COG/original deduplication); scene identity is ambiguous — "
            "inference is blocked until ambiguity is resolved"
        )
        return record

    else:
        # Exactly one physical acquisition (may have multiple representation items).
        phys_id = list(physical_id_to_items.keys())[0]
        phys_items = physical_id_to_items[phys_id]
        representation_count = len(phys_items)
        record.representation_count = representation_count
        # Prefer COG catalog ID as resolved_catalog_id (as CDSE currently distributes);
        # always set resolved_physical_acquisition_id to the canonical physical ID.
        record.resolved_physical_acquisition_id = phys_id
        # Pick the COG item if present, else the first item.
        cog_items = [it for it in phys_items if (it.get("id") or "").endswith("_COG")]
        best_item = cog_items[0] if cog_items else phys_items[0]
        record.resolved_catalog_id = best_item.get("id") or best_item.get("product_id")
        _populate_record_from_result(record, best_item)
        record.resolution_status = STATUS_RESOLVED_UNIQUE
        record.resolution_reason = (
            f"Exactly one physical acquisition identified: {phys_id} "
            f"({representation_count} catalog representation(s))"
        )
        return record



def _populate_record_from_result(record: PreflightRecord, result: Dict[str, Any]) -> None:
    """Populate metadata fields from a catalog API result dict."""
    record.acquisition_start = result.get("startDatetime") or result.get("start_time")
    record.acquisition_stop = result.get("completionDatetime") or result.get("stop_time")
    bbox = result.get("bbox") or result.get("geometry_bbox")
    if bbox and len(bbox) == 4:
        record.bbox = list(bbox)


def run_preflight(
    dartis_scene_ids: List[str],
    catalog_client: Any,
    *,
    window_seconds: int = CATALOG_WINDOW_SECONDS,
) -> PreflightManifest:
    """Run the full catalog preflight for a list of DARTIS scene IDs.

    BEFORE any model inference, every scene must be resolved.

    Args:
        dartis_scene_ids: List of unique DARTIS Sentinel_ID strings to resolve.
        catalog_client: Catalog API client (injected; see resolve_dartis_scene).
        window_seconds: Per-scene temporal search window.

    Returns:
        PreflightManifest with complete per-scene records and aggregate summary.
        Check manifest.preflight_passed to determine if inference may proceed.
    """
    manifest = PreflightManifest()

    for scene_id in dartis_scene_ids:
        record = resolve_dartis_scene(
            scene_id,
            catalog_client,
            window_seconds=window_seconds,
        )
        manifest.records.append(record)
        status = record.resolution_status
        logger.info(
            "Preflight: scene=%s status=%s reason=%s",
            scene_id[:40],
            status,
            record.resolution_reason[:80],
        )

    manifest.compute_summary()
    logger.info(
        "Preflight complete: %d/%d RESOLVED_UNIQUE, %d unresolved, passed=%s",
        manifest.evaluation_eligible,
        manifest.target_population,
        manifest.invalid_or_unresolved_count,
        manifest.preflight_passed,
    )
    return manifest


def enforce_preflight_gate(manifest: PreflightManifest) -> None:
    """Raise PreflightFirewallError if the manifest does not permit inference.

    This function MUST be called before any model forward pass in EXP-08.
    It enforces the hard firewall: if any scene is not RESOLVED_UNIQUE, inference
    is blocked.

    Args:
        manifest: The completed PreflightManifest from run_preflight().

    Raises:
        PreflightFirewallError: If manifest.preflight_passed is False or if
            invalid_or_unresolved_count > 0.
    """
    if not manifest.preflight_passed or manifest.invalid_or_unresolved_count > 0:
        unresolved = [
            r.dartis_scene_id
            for r in manifest.records
            if not r.is_eligible()
        ]
        raise PreflightFirewallError(
            f"EXP-08 preflight FAILED: {manifest.invalid_or_unresolved_count} scene(s) "
            f"not RESOLVED_UNIQUE out of {manifest.target_population} total. "
            f"Inference is BLOCKED. Unresolved scenes: {unresolved[:5]}"
            f"{'...' if len(unresolved) > 5 else ''}. "
            "Denominator MUST NOT be silently adjusted after seeing model predictions."
        )


def save_manifest(manifest: PreflightManifest, output_path: Path) -> None:
    """Persist the preflight manifest to a JSON file.

    Args:
        manifest: Completed PreflightManifest.
        output_path: Path to write the JSON file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest.as_dict(), f, indent=2, ensure_ascii=False)
    logger.info("Preflight manifest saved: %s", output_path)


def load_manifest(manifest_path: Path) -> PreflightManifest:
    """Load and reconstruct a PreflightManifest from a JSON file.

    Args:
        manifest_path: Path to a previously saved manifest JSON.

    Returns:
        PreflightManifest with records populated from disk.

    Raises:
        FileNotFoundError: If the manifest file does not exist.
        KeyError / ValueError: If the manifest structure is invalid.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Preflight manifest not found: {manifest_path}")

    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    records = [PreflightRecord(**rec) for rec in data.get("records", [])]
    manifest = PreflightManifest(
        target_population=data["target_population"],
        evaluation_eligible=data["evaluation_eligible"],
        invalid_or_unresolved_count=data["invalid_or_unresolved_count"],
        preflight_passed=data["preflight_passed"],
        preflight_timestamp=data["preflight_timestamp"],
        protocol_version=data.get("protocol_version", PREFLIGHT_PROTOCOL_VERSION),
        records=records,
    )
    return manifest


# ---------------------------------------------------------------------------
# Patch-level Denominator and Missingness Accounting (Stage 7 + 8)
# ---------------------------------------------------------------------------

@dataclass
class PatchRecord:
    """Individual patch tracking record preserving denominator integrity.

    Fields required by EXP-08 protocol:
        patch_id: Unique patch identifier (e.g., DARTIS patch ID).
        parent_scene_id: Identifier of the parent Sentinel-1 scene.
        stratum: Stratum membership (e.g., 'no_oil_disjoint', 'oil_colocated').
        target_status: Inclusion status in target population ('TARGET_INCLUDED').
        acquisition_status: Resolution status of parent scene (from PreflightRecord).
        evaluation_status: Evaluation status ('EVALUATION_ELIGIBLE', 'UNRESOLVED_ACQUISITION').
        prediction_score: Optional model output; MUST remain None for unresolved acquisitions.
        is_missing: Boolean flag indicating unresolved/missing status.
    """
    patch_id: str
    parent_scene_id: str
    stratum: str
    target_status: str = PATCH_TARGET_INCLUDED
    acquisition_status: str = "PENDING"
    evaluation_status: str = "PENDING"
    prediction_score: Optional[float] = None
    is_missing: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "parent_scene_id": self.parent_scene_id,
            "stratum": self.stratum,
            "target_status": self.target_status,
            "acquisition_status": self.acquisition_status,
            "evaluation_status": self.evaluation_status,
            "prediction_score": self.prediction_score,
            "is_missing": self.is_missing,
        }


@dataclass
class PatchManifest:
    """Patch-level manifest preserving frozen population denominators and missingness.

    The target patch population (N=2,290 for no-oil, N=1,365 for oil) is immutable.
    If a parent scene fails preflight or cannot be retrieved, its patches are marked
    as UNRESOLVED_ACQUISITION and is_missing=True. They are NEVER dropped from the
    denominator and NEVER converted into scientific zero predictions.
    """
    target_patch_population: int
    evaluation_eligible_patches: int
    unresolved_or_invalid_patches: int
    records: List[PatchRecord] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "target_patch_population": self.target_patch_population,
            "evaluation_eligible_patches": self.evaluation_eligible_patches,
            "unresolved_or_invalid_patches": self.unresolved_or_invalid_patches,
            "records": [r.as_dict() for r in self.records],
        }


def build_patch_manifest(
    patch_target_definitions: List[Dict[str, Any]],
    scene_manifest: PreflightManifest,
) -> PatchManifest:
    """Construct a patch-level manifest linked to the scene preflight manifest.

    Enforces the firewall rule: scene preflight eligibility determines patch
    evaluation eligibility, but an unresolved scene NEVER reduces the patch target
    population denominator and NEVER assigns zero scores to missing patches.
    """
    scene_records = {r.dartis_scene_id: r for r in scene_manifest.records}
    records: List[PatchRecord] = []
    eligible_count = 0
    unresolved_count = 0

    for pdef in patch_target_definitions:
        pid = pdef["patch_id"]
        sid = pdef["parent_scene_id"]
        stratum = pdef.get("stratum", "unspecified")
        target_status = pdef.get("target_status", PATCH_TARGET_INCLUDED)

        s_rec = scene_records.get(sid)
        if s_rec is not None and s_rec.is_eligible():
            acq_status = s_rec.resolution_status  # STATUS_RESOLVED_UNIQUE
            eval_status = PATCH_EVALUATION_ELIGIBLE
            is_missing = False
            eligible_count += 1
        else:
            acq_status = s_rec.resolution_status if s_rec is not None else "SCENE_NOT_FOUND"
            eval_status = PATCH_EVALUATION_UNRESOLVED
            is_missing = True
            unresolved_count += 1

        rec = PatchRecord(
            patch_id=pid,
            parent_scene_id=sid,
            stratum=stratum,
            target_status=target_status,
            acquisition_status=acq_status,
            evaluation_status=eval_status,
            prediction_score=None,  # NEVER convert missing to 0.0
            is_missing=is_missing,
        )
        records.append(rec)

    return PatchManifest(
        target_patch_population=len(records),
        evaluation_eligible_patches=eligible_count,
        unresolved_or_invalid_patches=unresolved_count,
        records=records,
    )

