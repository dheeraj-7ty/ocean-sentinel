"""EXP-08 Gated Execution Runner — Pre-Authorization Scaffold.

This module defines the ONLY permitted EXP-08 execution entry point.
It enforces the mandatory control flow:

    target_scene_construction
        -> run_preflight()
        -> enforce_preflight_gate()     ← inference is BLOCKED if this raises
        -> [inference placeholder]      ← real inference via predict_sar_image()

EXECUTION_AUTHORIZED = FALSE at module definition time.

This scaffold exists so that:
1. The integration between catalog preflight and inference is explicit and testable.
2. No code path can invoke the inference stack without passing enforce_preflight_gate().
3. The execution guard can be statically and dynamically verified.

Usage (after explicit CAO + Human authorization):
    Flip EXECUTION_AUTHORIZED = True only upon written dual authorization.
    Then call run_exp08_evaluation() with a real catalog client and raster fetch function.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ocean_sentinel.exp08_catalog_preflight import (
    PatchManifest,
    PatchRecord,
    PreflightFirewallError,
    PreflightManifest,
    PreflightRecord,
    build_patch_manifest,
    enforce_preflight_gate,
    load_manifest,
    run_preflight,
    save_manifest,
)

logger = logging.getLogger(__name__)

# ============================================================
# ABSOLUTE EXECUTION GUARD — DO NOT FLIP WITHOUT WRITTEN
# DUAL-AUTHORITY AUTHORIZATION FROM CAO + HUMAN
# ============================================================
EXECUTION_AUTHORIZED: bool = False
"""Controls whether the inference phase of run_exp08_evaluation() may proceed.

EXECUTION_AUTHORIZED = False: All calls to run_exp08_evaluation() will raise
    ExecutionNotAuthorizedError after the preflight gate, before any model
    forward pass. This is the mandatory pre-authorization state.

EXECUTION_AUTHORIZED = True: ONLY set this after receiving explicit written
    authorization from both the CAO (ChatGPT / Architecture Authority) and
    the Human (Final Approval Authority). Setting this without dual
    authorization constitutes a protocol violation.
"""


class ExecutionNotAuthorizedError(Exception):
    """Raised when run_exp08_evaluation() is called without explicit authorization.

    This exception is raised AFTER enforce_preflight_gate() (which validates catalog
    integrity) and BEFORE any model forward pass. It is the last line of defense
    ensuring no inference occurs without explicit dual-authority authorization.
    """
    pass


def run_exp08_evaluation(
    dartis_scene_ids: List[str],
    catalog_client: Any,
    raster_fetch_fn: Optional[Callable] = None,
    *,
    window_seconds: int = 25,
    manifest_save_path: Optional[Path] = None,
) -> PreflightManifest:
    """EXP-08 gated evaluation entry point.

    This is the ONLY permitted code path from scene construction to inference.
    It enforces the mandatory preflight-gate-before-inference control flow.

    CONTROL FLOW:
        1. Construct target scene list (caller's responsibility; passed as dartis_scene_ids)
        2. run_preflight()          — resolve all scenes to physical acquisitions
        3. enforce_preflight_gate() — BLOCK if any scene is not RESOLVED_UNIQUE
        4. EXECUTION_AUTHORIZED?   — BLOCK if False (pre-authorization state)
        5. [inference placeholder] — real inference via predict_sar_image() (AUTHORIZED ONLY)

    Args:
        dartis_scene_ids: List of DARTIS Sentinel_ID strings to resolve and evaluate.
            Must be pre-constructed from the frozen DARTIS catalog extract.
        catalog_client: CDSE catalog client (injected). Must implement:
            .query(scene_id: str, window_seconds: int) -> List[Dict]
        raster_fetch_fn: Optional callable that fetches a raster given a resolved
            catalog ID. Signature: (catalog_id: str) -> Path.
            If None and EXECUTION_AUTHORIZED is True, raises ValueError.
        window_seconds: Temporal search window for catalog resolution (default: 25s).
        manifest_save_path: If provided, the preflight manifest is persisted to this path.

    Returns:
        The completed PreflightManifest (with or without inference results).

    Raises:
        PreflightFirewallError: If any scene is not RESOLVED_UNIQUE. Raised before
            any model forward pass. This exception MUST NOT be caught to allow inference.
        ExecutionNotAuthorizedError: If EXECUTION_AUTHORIZED is False. Raised after
            the preflight gate passes but before inference. The manifest is still
            returned to allow preflight verification even in pre-authorization state.

    Protocol Reference:
        EXP08_CORRECTED_PROTOCOL_V3_5, §17 (Authorization prerequisites)
    """
    logger.info(
        "EXP-08 runner: starting preflight for %d scene(s). "
        "EXECUTION_AUTHORIZED=%s",
        len(dartis_scene_ids),
        EXECUTION_AUTHORIZED,
    )

    # STEP 1 + 2: Run catalog preflight for all scenes.
    manifest = run_preflight(
        dartis_scene_ids,
        catalog_client,
        window_seconds=window_seconds,
    )

    # Optionally persist the manifest for audit trail.
    if manifest_save_path is not None:
        save_manifest(manifest, Path(manifest_save_path))
        logger.info("Preflight manifest saved: %s", manifest_save_path)

    # STEP 3: Enforce preflight gate — raises PreflightFirewallError on any failure.
    # This MUST occur before any model forward pass. Catching this exception to
    # proceed with inference is a PROTOCOL VIOLATION.
    enforce_preflight_gate(manifest)

    logger.info(
        "EXP-08 preflight PASSED: %d/%d scenes RESOLVED_UNIQUE.",
        manifest.evaluation_eligible,
        manifest.target_population,
    )

    # STEP 4: Check explicit dual-authority authorization.
    if not EXECUTION_AUTHORIZED:
        logger.warning(
            "EXECUTION_AUTHORIZED=False — inference is BLOCKED. "
            "Returning manifest for preflight verification only. "
            "Set EXECUTION_AUTHORIZED=True only after explicit written "
            "CAO + Human authorization."
        )
        raise ExecutionNotAuthorizedError(
            "EXP-08 inference is blocked: EXECUTION_AUTHORIZED=False. "
            "Explicit written authorization from CAO (ChatGPT) and Human "
            "(Final Approval Authority) is required before any model forward pass. "
            f"Preflight passed ({manifest.evaluation_eligible}/{manifest.target_population} "
            "scenes RESOLVED_UNIQUE). This error is expected in pre-authorization state."
        )

    # =========================================================================
    # STEP 5: Inference placeholder.
    # THIS BLOCK IS ONLY REACHED WHEN EXECUTION_AUTHORIZED = True.
    # It must only be activated after explicit dual-authority authorization.
    # =========================================================================

    if raster_fetch_fn is None:
        raise ValueError(
            "raster_fetch_fn must be provided when EXECUTION_AUTHORIZED=True. "
            "Supply a callable that fetches CDSE rasters by catalog ID."
        )

    logger.info("EXP-08 inference phase: AUTHORIZED — proceeding with model inference.")

    # Import inference only when execution is authorized (avoids torch import
    # in pre-authorization state where torch may be unavailable).
    from ocean_sentinel.inference import predict_sar_image  # noqa: PLC0415

    results: List[Dict] = []
    for record in manifest.records:
        if not record.is_eligible():
            # Should not reach here (enforce_preflight_gate already checked).
            logger.error(
                "INVARIANT VIOLATION: non-eligible scene reached inference: %s",
                record.dartis_scene_id,
            )
            continue
        catalog_id = record.resolved_catalog_id
        assert catalog_id is not None, (
            f"RESOLVED_UNIQUE record has no resolved_catalog_id: {record.dartis_scene_id}"
        )
        raster_path = raster_fetch_fn(catalog_id)
        # predict_sar_image() is the canonical inference function from inference.py.
        # It handles: checkpoint loading, preprocessing, tiling, prediction, reconstruction.
        result = predict_sar_image(raster_path)
        results.append({
            "dartis_scene_id": record.dartis_scene_id,
            "resolved_catalog_id": catalog_id,
            "physical_acquisition_id": record.resolved_physical_acquisition_id,
            "result": result,
        })

    logger.info(
        "EXP-08 inference complete: %d/%d scenes evaluated.",
        len(results),
        manifest.evaluation_eligible,
    )
    # Attach results to manifest for downstream metric computation.
    manifest.inference_results = results  # type: ignore[attr-defined]
    return manifest
