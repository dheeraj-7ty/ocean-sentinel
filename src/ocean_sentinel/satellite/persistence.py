"""Ocean Sentinel Real-Data Acquisition & Persistence Boundary (Phase 6B).

Establishes the audited bridge between external real EO providers, local filesystem
persistence, and the Phase 6 Operational Pipeline:
    Real Provider (Copernicus CDSE / Sentinel Hub)
              ↓
    Acquisition Request (STAC Discovery / Process API Request)
              ↓
    Real Remote Observation Materialization
              ↓
    Deterministic Local File Persistence (GeoTIFF + Provenance Sidecar JSON)
              ↓
    Cryptographic Hash Binding (SHA-256 Content Digest)
              ↓
    SAR Raster Contract Validation (Bands, Dtype, Georeferencing, Finite Pixels)
              ↓
    Phase 6 Operational Pipeline Ingestion Handoff

Scientific & Real-Data Safety Boundaries:
------------------------------------------
1. ZERO SYNTHETIC FALLBACK:
   External network or provider failures fail closed immediately.
   Synthetic, mock, or demo providers are strictly rejected.
2. MANDATORY SOURCE REFERENCE:
   Every persisted acquisition artifact must carry an explicit, non-empty
   upstream source reference (canonical STAC item URL or provider product URN).
3. BITWISE CONTENT INTEGRITY:
   Persisted rasters are bound to their SHA-256 digest upon materialization.
   Loading from disk re-verifies this digest before feeding downstream validation.
4. FIREWALLED DETECTION BOUNDARY:
   Handoff into the Phase 6 pipeline enforces EXECUTION_AUTHORIZED = False.
   No scientific inference, forward passes, or model training occur.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine

from ocean_sentinel.errors import (
    ProviderTimeoutError,
    ProviderUnavailableError,
    RasterValidationError,
    SatelliteError,
    SatelliteErrorCode,
)
from ocean_sentinel.models import (
    AcquisitionMetadata,
    BoundingBox,
    ImageryRequest,
    ImageryResult,
    Polarization,
)
from ocean_sentinel.operational_pipeline import (
    OperationalEvidenceResult,
    OperationalIngestionRequest,
    OperationalSARPipeline,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_ACQUISITIONS_DIR = REPO_ROOT / "data" / "acquisitions"

RECOGNIZED_REAL_DATA_PROVIDERS = {
    "copernicus_cdse",
    "sentinel_hub",
    "esa_scihub",
    "asf",
    "peps",
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PersistenceError(Exception):
    """Base exception for errors in the acquisition persistence boundary."""

    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.code, "message": self.message, "details": self.details}


class MissingAcquisitionIdentityError(PersistenceError):
    """Raised when an acquisition identity is missing or empty."""

    pass


class UnauthorizedProviderError(PersistenceError):
    """Raised when a synthetic, demo, or unrecognized provider is encountered."""

    pass


class MissingSourceReferenceError(PersistenceError):
    """Raised when an acquisition lacks an authoritative remote source reference."""

    pass


class PersistenceIntegrityError(PersistenceError):
    """Raised when a persisted file is missing, corrupt, or fails SHA-256 verification."""

    pass


class RasterMaterializationError(PersistenceError):
    """Raised when raster bytes cannot be written, parsed, or decoded from disk."""

    pass


# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------


@dataclass
class PersistedAcquisitionArtifact:
    """Immutable record of an authoritative SAR acquisition persisted to disk."""

    acquisition_id: str
    provider: str
    acquisition_time: str
    spatial_extent: Dict[str, Any]
    bbox: List[float]
    crs: str
    transform: List[float]
    width: int
    height: int
    polarizations: List[str]
    source_reference: str
    geotiff_path: str
    metadata_path: str
    content_sha256: str
    file_size_bytes: int
    persisted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance_class: str = "VERIFIED_OPERATIONAL"
    status: str = "PERSISTED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PersistedAcquisitionArtifact:
        return cls(**data)


# ---------------------------------------------------------------------------
# Acquisition Persistence Service
# ---------------------------------------------------------------------------


class AcquisitionPersistenceService:
    """Manages atomic disk persistence and cryptographic binding for real EO rasters."""

    def __init__(self, storage_root: Optional[Union[str, Path]] = None) -> None:
        self.storage_root = Path(storage_root) if storage_root else DEFAULT_ACQUISITIONS_DIR

    def persist_acquisition(
        self,
        imagery: ImageryResult,
        request: ImageryRequest,
    ) -> PersistedAcquisitionArtifact:
        """Atomically persist a retrieved ImageryResult to disk with sidecar metadata.

        Enforces:
        - Non-empty acquisition ID
        - Recognized real-data provider (rejects synthetic / demo providers fail-closed)
        - Non-empty remote source reference (canonical STAC link or product URN)
        - Valid non-empty GeoTIFF bytes
        - SHA-256 computation over written disk artifact
        """
        # 1. Validate Acquisition ID
        acq_id = str(imagery.observation_id).strip() if imagery.observation_id else ""
        if not acq_id:
            raise MissingAcquisitionIdentityError(
                code="MISSING_ACQUISITION_ID",
                message="Cannot persist acquisition: acquisition identity is missing or empty.",
            )

        # 2. Validate Provider
        provider = str(request.observation.provider).strip().lower() if request.observation.provider else ""
        if not provider:
            raise UnauthorizedProviderError(
                code="MISSING_PROVIDER_ID",
                message="Data source provider identifier is required.",
                details={"acquisition_id": acq_id},
            )
        if any(f in provider for f in ["synthetic", "demo", "fake", "mock", "dummy"]):
            raise UnauthorizedProviderError(
                code="UNAUTHORIZED_PROVIDER",
                message=(
                    f"Provider '{provider}' is strictly rejected. "
                    "Only verified operational EO providers may be materialized to disk."
                ),
                details={"acquisition_id": acq_id, "provider": provider},
            )
        if provider not in RECOGNIZED_REAL_DATA_PROVIDERS:
            logger.warning(f"Uncommon provider '{provider}' being persisted for acquisition {acq_id}")

        # 3. Validate Source Reference
        source_ref = (
            request.observation.source_reference
            or request.observation.self_link
            or request.observation.source_collection
        )
        if not source_ref or not str(source_ref).strip():
            raise MissingSourceReferenceError(
                code="MISSING_SOURCE_REFERENCE",
                message=(
                    f"Acquisition '{acq_id}' lacks a canonical remote source reference "
                    "(source_reference or self_link is mandatory for operational provenance)."
                ),
                details={"acquisition_id": acq_id},
            )
        source_ref_clean = str(source_ref).strip()

        # 4. Validate Raw Bytes
        if not imagery.raw_bytes or len(imagery.raw_bytes) == 0:
            raise RasterMaterializationError(
                code="EMPTY_RASTER_BYTES",
                message="Cannot persist acquisition: raw GeoTIFF byte payload is empty.",
                details={"acquisition_id": acq_id},
            )

        # 5. Prepare Target Directory
        target_dir = self.storage_root / acq_id
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise PersistenceError(
                code="DIRECTORY_CREATION_FAILED",
                message=f"Failed to create persistence directory {target_dir}: {e}",
                details={"target_dir": str(target_dir)},
            ) from e

        geotiff_path = target_dir / f"{acq_id}.tif"
        metadata_path = target_dir / f"{acq_id}_metadata.json"

        # 6. Atomic Write of GeoTIFF
        temp_tif = target_dir / f"{acq_id}.tmp_{os.getpid()}_{int(datetime.now().timestamp())}.tif"
        try:
            with open(temp_tif, "wb") as f:
                f.write(imagery.raw_bytes)
            # Atomic rename / replace
            temp_tif.replace(geotiff_path)
        except Exception as e:
            if temp_tif.exists():
                try:
                    temp_tif.unlink()
                except Exception:
                    pass
            raise PersistenceError(
                code="GEOTIFF_WRITE_FAILED",
                message=f"Failed to write GeoTIFF to {geotiff_path}: {e}",
                details={"target_path": str(geotiff_path)},
            ) from e

        # 7. Compute SHA-256 of the persisted disk file
        sha256_hash = hashlib.sha256()
        file_size = 0
        with open(geotiff_path, "rb") as f:
            while chunk := f.read(65536):
                sha256_hash.update(chunk)
                file_size += len(chunk)
        content_digest = sha256_hash.hexdigest()

        # 8. Compile Provenance Sidecar Metadata
        acq_time_iso = (
            request.observation.acquisition_time.isoformat()
            if isinstance(request.observation.acquisition_time, datetime)
            else str(request.observation.acquisition_time)
        )
        geom = request.observation.geometry
        pols = [p.value for p in imagery.bands]

        artifact = PersistedAcquisitionArtifact(
            acquisition_id=acq_id,
            provider=provider,
            acquisition_time=acq_time_iso,
            spatial_extent=geom,
            bbox=list(imagery.bounds),
            crs=imagery.crs,
            transform=list(imagery.transform),
            width=imagery.width,
            height=imagery.height,
            polarizations=pols,
            source_reference=source_ref_clean,
            geotiff_path=str(geotiff_path),
            metadata_path=str(metadata_path),
            content_sha256=content_digest,
            file_size_bytes=file_size,
            provenance_class="VERIFIED_OPERATIONAL",
            status="PERSISTED",
        )

        # 9. Atomic Write of Metadata JSON
        temp_json = target_dir / f"{acq_id}_metadata.tmp_{os.getpid()}.json"
        try:
            with open(temp_json, "w", encoding="utf-8") as f:
                json.dump(artifact.to_dict(), f, indent=2)
            temp_json.replace(metadata_path)
        except Exception as e:
            if temp_json.exists():
                try:
                    temp_json.unlink()
                except Exception:
                    pass
            raise PersistenceError(
                code="METADATA_WRITE_FAILED",
                message=f"Failed to write metadata sidecar to {metadata_path}: {e}",
                details={"target_path": str(metadata_path)},
            ) from e

        logger.info(
            f"Successfully persisted real acquisition '{acq_id}' ({file_size} bytes, "
            f"SHA256={content_digest[:12]}...) to {geotiff_path}"
        )
        return artifact

    def load_persisted_acquisition(
        self,
        acquisition_id: str,
    ) -> Tuple[PersistedAcquisitionArtifact, Dict[Polarization, np.ndarray]]:
        """Loads a persisted acquisition artifact from disk and re-verifies its integrity.

        Returns:
            Tuple of (PersistedAcquisitionArtifact, dictionary of Polarization to 2D float32 numpy arrays)

        Raises:
            PersistenceIntegrityError: If sidecar or GeoTIFF is missing, or SHA256 mismatches.
            RasterMaterializationError: If GeoTIFF cannot be parsed or decoded.
        """
        acq_dir = self.storage_root / acquisition_id
        meta_path = acq_dir / f"{acquisition_id}_metadata.json"
        tif_path = acq_dir / f"{acquisition_id}.tif"

        if not meta_path.is_file():
            raise PersistenceIntegrityError(
                code="PERSISTED_METADATA_NOT_FOUND",
                message=f"Persisted metadata sidecar not found at: {meta_path}",
                details={"acquisition_id": acquisition_id},
            )
        if not tif_path.is_file():
            raise PersistenceIntegrityError(
                code="PERSISTED_GEOTIFF_NOT_FOUND",
                message=f"Persisted GeoTIFF raster not found at: {tif_path}",
                details={"acquisition_id": acquisition_id},
            )

        # 1. Load and parse metadata
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            artifact = PersistedAcquisitionArtifact.from_dict(data)
        except Exception as e:
            raise PersistenceIntegrityError(
                code="CORRUPT_METADATA_JSON",
                message=f"Failed to decode persisted metadata sidecar {meta_path}: {e}",
                details={"metadata_path": str(meta_path)},
            ) from e

        # 2. Verify bitwise SHA-256 digest of on-disk GeoTIFF
        sha256_hash = hashlib.sha256()
        with open(tif_path, "rb") as f:
            while chunk := f.read(65536):
                sha256_hash.update(chunk)
        current_digest = sha256_hash.hexdigest()

        if current_digest != artifact.content_sha256:
            raise PersistenceIntegrityError(
                code="PERSISTED_ARTIFACT_HASH_MISMATCH",
                message=(
                    f"Integrity check failed for persisted GeoTIFF '{tif_path.name}'!\n"
                    f"Expected SHA256: {artifact.content_sha256}\n"
                    f"Actual SHA256:   {current_digest}"
                ),
                details={
                    "acquisition_id": acquisition_id,
                    "expected_sha256": artifact.content_sha256,
                    "actual_sha256": current_digest,
                },
            )

        # 3. Read raster arrays via rasterio
        channel_arrays: Dict[Polarization, np.ndarray] = {}
        try:
            with rasterio.open(tif_path) as src:
                if src.count != len(artifact.polarizations):
                    raise RasterMaterializationError(
                        code="BAND_COUNT_MISMATCH_ON_LOAD",
                        message=f"GeoTIFF band count {src.count} != metadata polarizations count {len(artifact.polarizations)}",
                    )
                for idx, pol_str in enumerate(artifact.polarizations):
                    pol = Polarization(pol_str)
                    arr = src.read(idx + 1).astype(np.float32)
                    channel_arrays[pol] = arr
        except RasterMaterializationError:
            raise
        except Exception as e:
            raise RasterMaterializationError(
                code="GEOTIFF_READ_FAILED",
                message=f"Failed to read raster arrays from {tif_path}: {e}",
                details={"geotiff_path": str(tif_path)},
            ) from e

        return artifact, channel_arrays

    def to_operational_ingestion_request(
        self,
        artifact: PersistedAcquisitionArtifact,
        channel_arrays: Dict[Polarization, np.ndarray],
    ) -> OperationalIngestionRequest:
        """Converts a persisted acquisition artifact and its verified arrays into a Phase 6 pipeline request."""
        # Convert polarizations to enum list
        pols = [Polarization(p) for p in artifact.polarizations]

        return OperationalIngestionRequest(
            acquisition_id=artifact.acquisition_id,
            provider=artifact.provider,
            acquisition_time=artifact.acquisition_time,
            spatial_extent=artifact.spatial_extent,
            crs=artifact.crs,
            polarizations=pols,
            source_reference=artifact.source_reference,
            raw_arrays=channel_arrays,
            transform=artifact.transform,
            width=artifact.width,
            height=artifact.height,
            metadata_properties={
                "persisted_geotiff_path": artifact.geotiff_path,
                "persisted_metadata_path": artifact.metadata_path,
                "content_sha256": artifact.content_sha256,
                "file_size_bytes": artifact.file_size_bytes,
                "provenance_class": artifact.provenance_class,
            },
        )


# ---------------------------------------------------------------------------
# Real-Data Acquisition Bridge
# ---------------------------------------------------------------------------


class RealDataAcquisitionBridge:
    """Governed operational bridge coordinating real satellite acquisition,
    disk persistence, and handoff to the firewalled Phase 6 operational pipeline.
    """

    def __init__(
        self,
        persistence_service: Optional[AcquisitionPersistenceService] = None,
        operational_pipeline: Optional[OperationalSARPipeline] = None,
    ) -> None:
        self.persistence_service = persistence_service or AcquisitionPersistenceService()
        self.operational_pipeline = operational_pipeline or OperationalSARPipeline(execution_authorized=False)

    def persist_and_handoff(
        self,
        imagery: ImageryResult,
        request: ImageryRequest,
    ) -> Tuple[PersistedAcquisitionArtifact, OperationalEvidenceResult]:
        """Materializes an ImageryResult to disk and executes Phase 6 operational preflight."""
        # 1. Persist to disk with cryptographic binding
        artifact = self.persistence_service.persist_acquisition(imagery, request)

        # 2. Load from disk and verify SHA256 integrity
        verified_artifact, channel_arrays = self.persistence_service.load_persisted_acquisition(
            artifact.acquisition_id
        )

        # 3. Create pipeline ingestion request
        ingestion_req = self.persistence_service.to_operational_ingestion_request(
            verified_artifact, channel_arrays
        )

        # 4. Execute firewalled Phase 6 operational pipeline
        evidence_result = self.operational_pipeline.run(ingestion_req)

        return verified_artifact, evidence_result
