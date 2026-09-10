"""Authoritative dataset provenance verification gate and transfer governance.

Enforces the non-negotiable architectural invariant:
PROVENANCE CHECK MUST PASS BEFORE ANY LARGE DATA DOWNLOAD.

Enforces trust boundary:
DatasetProvenanceSpecification
        ↓
AuthoritativeRecordResolver
        ↓
ProvenanceGate
        ↓
VerifiedProvenanceToken
        ↓
DatasetTransferManager (Transfer Layer)
        ↓
ArtifactChecksumVerification
        ↓
Extraction
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
import hmac
import json
from pathlib import Path
import re
from typing import Any, Callable, Optional, Union
import urllib.request
import uuid

from pydantic import BaseModel, ConfigDict, Field

from ocean_sentinel.errors import DatasetErrorCode, DatasetProvenanceError


class ProvenanceGateDecision(str, Enum):
    """Explicit decision enum for the provenance gate."""

    PASSED = "PASSED"
    BLOCKED_DATASET_PROVENANCE = "BLOCKED_DATASET_PROVENANCE"


class QualificationStateEnum(str, Enum):
    """Explicit states for the dataset qualification state machine."""

    UNINITIALIZED = "UNINITIALIZED"
    PROVENANCE_CHECK_IN_PROGRESS = "PROVENANCE_CHECK_IN_PROGRESS"
    BLOCKED_DATASET_PROVENANCE = "BLOCKED_DATASET_PROVENANCE"
    PROVENANCE_VERIFIED = "PROVENANCE_VERIFIED"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOAD_COMPLETED = "DOWNLOAD_COMPLETED"
    CHECKSUM_VERIFIED = "CHECKSUM_VERIFIED"
    EXTRACTING = "EXTRACTING"
    PHYSICAL_QUALIFYING = "PHYSICAL_QUALIFYING"
    QUALIFIED = "QUALIFIED"


class DatasetProvenanceSpecification(BaseModel):
    """Structured expectation specification for an external dataset target.

    Enforces that canonical dataset identity is defined by authoritative attributes
    rather than local directory names or speculative assumptions.
    """

    model_config = ConfigDict(frozen=True)

    target_identity: str = Field(
        ...,
        description="Authoritative identity description of the target dataset",
    )
    expected_doi: Optional[str] = Field(
        default=None,
        description="Expected DOI string if formally assigned, or None if pending",
    )
    expected_record_id: Optional[int] = Field(
        default=None,
        description="Expected repository record ID if established, or None",
    )
    expected_platform: Optional[str] = Field(
        default="Sentinel-1",
        description="Expected satellite or sensor platform (e.g. 'Sentinel-1')",
    )
    expected_sensor_band: Optional[str] = Field(
        default="C-band",
        description="Expected microwave radar frequency band (e.g. 'C-band')",
    )
    expected_polarizations: list[str] = Field(
        default_factory=lambda: ["VV", "VH"],
        description="Expected polarization channels (e.g. ['VV', 'VH'])",
    )
    expected_geographic_domain: Optional[str] = Field(
        default="Peru",
        description="Expected geographical domain / country / sea (e.g. 'Peru')",
    )
    required_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords that MUST be present in title or description",
    )
    prohibited_keywords: list[str] = Field(
        default_factory=lambda: [
            "UAVSAR",
            "airborne",
            "L-band",
            "Gulf of Mexico",
            "QPOSD",
            "Quad-Polarization",
        ],
        description="Keywords that indicate an incompatible or substituted dataset",
    )

    def fingerprint(self) -> str:
        """Compute deterministic SHA-256 fingerprint of specification."""
        payload = json.dumps(
            {
                "target_identity": self.target_identity,
                "expected_doi": self.expected_doi,
                "expected_record_id": self.expected_record_id,
                "expected_platform": self.expected_platform,
                "expected_sensor_band": self.expected_sensor_band,
                "expected_polarizations": sorted(self.expected_polarizations),
                "expected_geographic_domain": self.expected_geographic_domain,
                "required_keywords": sorted(self.required_keywords),
                "prohibited_keywords": sorted(self.prohibited_keywords),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()

    @classmethod
    def morp_synth_peru_spec(cls) -> DatasetProvenanceSpecification:
        """Construct the canonical specification for Peruvian Sentinel-1 MORP-Synth."""
        return cls(
            target_identity="Peruvian S1 / MORP-Synth (Andrex et al., arXiv:2512.02290)",
            expected_doi=None,  # Not yet released on Zenodo pending paper acceptance
            expected_record_id=None,
            expected_platform="Sentinel-1",
            expected_sensor_band="C-band",
            expected_polarizations=["VV", "VH"],
            expected_geographic_domain="Peru",
            required_keywords=["MORP", "Peru"],
            prohibited_keywords=[
                "UAVSAR",
                "airborne",
                "L-band",
                "Gulf of Mexico",
                "QPOSD",
                "Quad-Polarization",
            ],
        )

    @classmethod
    def trujillo_part_iii_spec(cls) -> DatasetProvenanceSpecification:
        """Construct the canonical specification for Trujillo Part III Held-Out Test Set."""
        return cls(
            target_identity="Trujillo Part III Held-Out Test Set (Zenodo 10.5281/zenodo.13761290)",
            expected_doi="10.5281/zenodo.13761290",
            expected_record_id=13761290,
            expected_platform="Sentinel-1",
            expected_sensor_band="C-band",
            expected_polarizations=["VV", "VH"],
            expected_geographic_domain="Gulf of Mexico",
            required_keywords=["Sentinel-1", "Part III"],
            prohibited_keywords=[
                "UAVSAR",
                "airborne",
                "L-band",
                "QPOSD",
                "Quad-Polarization",
            ],
        )


class ResolvedRecordMetadata(BaseModel):
    """Authoritative metadata parsed from a remote repository record (e.g. Zenodo)."""

    model_config = ConfigDict(frozen=True)

    record_id: int = Field(..., description="Repository record identifier")
    doi: str = Field(..., description="Canonical DOI string")
    title: str = Field(..., description="Official title of the published record")
    description: str = Field(default="", description="Official record description / abstract")
    creators: list[str] = Field(default_factory=list, description="List of author / creator names")
    keywords: list[str] = Field(default_factory=list, description="Author / record keywords")
    file_names: list[str] = Field(default_factory=list, description="Archive and companion filenames")
    related_identifiers: list[dict[str, Any]] = Field(
        default_factory=list, description="Related DOIs, papers, or repositories"
    )
    publication_date: Optional[str] = Field(default=None, description="Published date")
    primary_archive_url: Optional[str] = Field(
        default=None, description="Direct download URL of the primary archive"
    )
    primary_archive_filename: Optional[str] = Field(
        default=None, description="Filename of primary archive"
    )
    raw_payload: Optional[dict[str, Any]] = Field(
        default=None, repr=False, description="Raw JSON response from provider"
    )

    def fingerprint(self) -> str:
        """Compute deterministic SHA-256 fingerprint of resolved metadata."""
        payload = json.dumps(
            {
                "record_id": self.record_id,
                "doi": self.doi,
                "title": self.title,
                "description": self.description,
                "creators": self.creators,
                "keywords": sorted(self.keywords),
                "file_names": sorted(self.file_names),
                "publication_date": self.publication_date,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


class ProvenanceGateResult(BaseModel):
    """Structured report of provenance validation checks."""

    model_config = ConfigDict(frozen=True)

    decision: ProvenanceGateDecision
    is_valid: bool
    target_identity: str
    resolved_title: str
    resolved_doi: str
    resolved_record_id: int
    mismatches: list[str]
    warnings: list[str]
    timestamp_utc: str


# Fixed HMAC salt for process-local integrity validation of tokens
_TOKEN_INTEGRITY_KEY = b"ocean-sentinel-provenance-gate-v1-sealed"


class VerifiedProvenanceToken(BaseModel):
    """Cryptographic, non-forgeable token issued ONLY upon successful provenance passage.

    The transfer layer strictly requires a valid, verified token to initiate any download.
    """

    model_config = ConfigDict(frozen=True)

    token_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    target_identity: str
    spec_fingerprint: str
    resolved_record_id: int
    resolved_doi: str
    resolved_title: str
    resolved_metadata_fingerprint: str
    authorized_archive_url: str
    authorized_archive_filename: str
    issued_at_utc: str
    decision: ProvenanceGateDecision = ProvenanceGateDecision.PASSED
    signature: str

    @classmethod
    def create(
        cls,
        spec: DatasetProvenanceSpecification,
        resolved: ResolvedRecordMetadata,
        archive_url: str,
        archive_filename: str,
    ) -> VerifiedProvenanceToken:
        """Factory method that signs token fields."""
        token_id = uuid.uuid4().hex
        issued_at = datetime.now(timezone.utc).isoformat()
        spec_fp = spec.fingerprint()
        meta_fp = resolved.fingerprint()

        msg = f"{token_id}|{spec.target_identity}|{spec_fp}|{resolved.record_id}|{resolved.doi}|{meta_fp}|{archive_url}|{archive_filename}|{issued_at}"
        sig = hmac.new(_TOKEN_INTEGRITY_KEY, msg.encode("utf-8"), hashlib.sha256).hexdigest()

        return cls(
            token_id=token_id,
            target_identity=spec.target_identity,
            spec_fingerprint=spec_fp,
            resolved_record_id=resolved.record_id,
            resolved_doi=resolved.doi,
            resolved_title=resolved.title,
            resolved_metadata_fingerprint=meta_fp,
            authorized_archive_url=archive_url,
            authorized_archive_filename=archive_filename,
            issued_at_utc=issued_at,
            decision=ProvenanceGateDecision.PASSED,
            signature=sig,
        )

    def verify_integrity(self) -> bool:
        """Verify HMAC signature and decision of token."""
        if self.decision != ProvenanceGateDecision.PASSED:
            return False
        msg = f"{self.token_id}|{self.target_identity}|{self.spec_fingerprint}|{self.resolved_record_id}|{self.resolved_doi}|{self.resolved_metadata_fingerprint}|{self.authorized_archive_url}|{self.authorized_archive_filename}|{self.issued_at_utc}"
        expected_sig = hmac.new(
            _TOKEN_INTEGRITY_KEY, msg.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(self.signature, expected_sig)

    def is_stale(self, max_age_seconds: float = 3600.0) -> bool:
        """Check whether token has expired or has an invalid future timestamp."""
        try:
            issued = datetime.fromisoformat(self.issued_at_utc)
            age = (datetime.now(timezone.utc) - issued).total_seconds()
            # Stale if older than max_age_seconds or future-dated beyond 60s clock skew
            return age > max_age_seconds or age < -60.0
        except Exception:
            return True


class ProvenanceGateError(DatasetProvenanceError):
    """Exception raised when authoritative dataset provenance fails validation."""

    def __init__(self, message: str, result: ProvenanceGateResult, **kwargs: Any) -> None:
        super().__init__(
            message=message,
            details={
                "decision": result.decision.value,
                "is_valid": result.is_valid,
                "target_identity": result.target_identity,
                "resolved_title": result.resolved_title,
                "resolved_doi": result.resolved_doi,
                "resolved_record_id": result.resolved_record_id,
                "mismatches": result.mismatches,
            },
            **kwargs,
        )
        self.result = result


class ProvenanceBypassAttemptError(DatasetProvenanceError):
    """Raised when transfer is attempted without valid provenance verification."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message=message, **kwargs)


class IllegalStateTransitionError(DatasetProvenanceError):
    """Raised when an illegal transition out of BLOCKED_DATASET_PROVENANCE is attempted."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message=message, **kwargs)


class ProvenanceGate:
    """Evaluates remote repository record identity against dataset specifications."""

    @staticmethod
    def parse_zenodo_record(raw: dict[str, Any]) -> ResolvedRecordMetadata:
        """Parse raw Zenodo API JSON response into structured metadata."""
        record_id = int(raw.get("id", 0))
        doi = raw.get("doi", raw.get("metadata", {}).get("doi", ""))
        metadata = raw.get("metadata", {})
        title = metadata.get("title", "")
        description = metadata.get("description", "")

        creators = [
            c.get("name", "") for c in metadata.get("creators", []) if c.get("name")
        ]
        keywords = metadata.get("keywords", [])

        files = raw.get("files", [])
        file_names = [f.get("key", f.get("filename", "")) for f in files if isinstance(f, dict)]

        # Extract primary archive URL and filename
        primary_url = None
        primary_name = None
        for f in files:
            fname = f.get("key", f.get("filename", ""))
            if fname.endswith((".zip", ".tar.gz", ".tar", ".7z")):
                primary_name = fname
                primary_url = f.get("links", {}).get("self", f.get("links", {}).get("content"))
                if not primary_url and record_id and primary_name:
                    primary_url = f"https://zenodo.org/api/records/{record_id}/files/{primary_name}/content"
                break

        related = metadata.get("related_identifiers", [])

        return ResolvedRecordMetadata(
            record_id=record_id,
            doi=doi,
            title=title,
            description=description,
            creators=creators,
            keywords=keywords,
            file_names=file_names,
            related_identifiers=related,
            publication_date=metadata.get("publication_date"),
            primary_archive_url=primary_url,
            primary_archive_filename=primary_name,
            raw_payload=raw,
        )

    @classmethod
    def fetch_zenodo_record(
        cls,
        record_id_or_doi: str | int,
        timeout_sec: float = 20.0,
    ) -> ResolvedRecordMetadata:
        """Query the Zenodo REST API for a record or DOI."""
        query = str(record_id_or_doi).strip()
        if "zenodo." in query:
            rec_id = query.split("zenodo.")[-1]
        elif query.isdigit():
            rec_id = query
        else:
            rec_id = query

        url = f"https://zenodo.org/api/records/{rec_id}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "OceanSentinel-ProvenanceGate/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return cls.parse_zenodo_record(data)

    @classmethod
    def evaluate_provenance(
        cls,
        spec: DatasetProvenanceSpecification,
        resolved: ResolvedRecordMetadata,
    ) -> ProvenanceGateResult:
        """Evaluate resolved record identity against expected dataset specification."""
        mismatches: list[str] = []
        warnings: list[str] = []

        # 0. Missing required metadata check (fail closed)
        if not resolved.title or not resolved.title.strip():
            mismatches.append("MISSING_REQUIRED_METADATA: Record title is empty or missing.")
        if not resolved.doi or not resolved.doi.strip():
            mismatches.append("MISSING_REQUIRED_METADATA: Record DOI is empty or missing.")
        if resolved.record_id <= 0:
            mismatches.append("MISSING_REQUIRED_METADATA: Record ID is invalid or <= 0.")

        # 1. DOI check if explicitly specified
        if spec.expected_doi is not None:
            clean_expected = spec.expected_doi.strip().lower()
            clean_resolved = resolved.doi.strip().lower()
            if clean_expected != clean_resolved:
                mismatches.append(
                    f"DOI mismatch: expected '{spec.expected_doi}', resolved '{resolved.doi}'"
                )

        # 2. Record ID check if explicitly specified
        if spec.expected_record_id is not None:
            if spec.expected_record_id != resolved.record_id:
                mismatches.append(
                    f"Record ID mismatch: expected {spec.expected_record_id}, resolved {resolved.record_id}"
                )

        # Searchable corpus from resolved record, normalizing separators to spaces
        raw_corpus = f"{resolved.title} {resolved.description} {' '.join(resolved.keywords)} {' '.join(resolved.file_names)}"
        corpus_lower = raw_corpus.lower()
        delimited_corpus = re.sub(r"[_\-\.\/\\:]", " ", corpus_lower)

        # 3. Prohibited keyword guards (immediate conflict indicators)
        for prohibited in spec.prohibited_keywords:
            pattern = rf"\b{re.escape(prohibited.lower())}\b"
            if re.search(pattern, corpus_lower) or re.search(pattern, delimited_corpus):
                mismatches.append(
                    f"PROHIBITED_KEYWORD_DETECTED: Record contains prohibited keyword '{prohibited}', "
                    f"indicating mismatched dataset domain or sensor platform."
                )

        # 4. Required keywords
        for required in spec.required_keywords:
            pattern = rf"\b{re.escape(required.lower())}\b"
            if not (re.search(pattern, corpus_lower) or re.search(pattern, delimited_corpus)):
                mismatches.append(
                    f"MISSING_REQUIRED_KEYWORD: Required keyword '{required}' was not found in title, "
                    f"description, keywords, or filenames of resolved record."
                )

        # 5. Geographic domain check
        if spec.expected_geographic_domain:
            geo_pattern = rf"\b{re.escape(spec.expected_geographic_domain.lower())}\b"
            if not (re.search(geo_pattern, corpus_lower) or re.search(geo_pattern, delimited_corpus)):
                mismatches.append(
                    f"GEOGRAPHIC_DOMAIN_MISMATCH: Expected region '{spec.expected_geographic_domain}' "
                    f"not referenced in record metadata."
                )

        # 6. Platform / Sensor check
        if spec.expected_platform:
            platform_pattern = rf"\b{re.escape(spec.expected_platform.lower())}\b"
            if not (re.search(platform_pattern, corpus_lower) or re.search(platform_pattern, delimited_corpus)):
                warnings.append(
                    f"Platform keyword '{spec.expected_platform}' not explicitly declared in record."
                )

        # 7. Ambiguity check: if record title contains conflicting sensor families
        if "uavsar" in corpus_lower and "sentinel" in corpus_lower:
            mismatches.append(
                "AMBIGUOUS_DATASET_IDENTITY: Record contains references to multiple competing sensor platforms."
            )

        is_valid = len(mismatches) == 0
        decision = (
            ProvenanceGateDecision.PASSED
            if is_valid
            else ProvenanceGateDecision.BLOCKED_DATASET_PROVENANCE
        )

        now_utc = datetime.now(timezone.utc).isoformat()
        return ProvenanceGateResult(
            decision=decision,
            is_valid=is_valid,
            target_identity=spec.target_identity,
            resolved_title=resolved.title,
            resolved_doi=resolved.doi,
            resolved_record_id=resolved.record_id,
            mismatches=mismatches,
            warnings=warnings,
            timestamp_utc=now_utc,
        )

    @classmethod
    def enforce_gate(
        cls,
        spec: DatasetProvenanceSpecification,
        resolved: ResolvedRecordMetadata,
        archive_url: Optional[str] = None,
        archive_filename: Optional[str] = None,
    ) -> VerifiedProvenanceToken:
        """Evaluate and raise ProvenanceGateError immediately if validation fails.

        Returns VerifiedProvenanceToken upon successful validation.
        """
        result = cls.evaluate_provenance(spec, resolved)
        if not result.is_valid:
            msg = (
                f"PROVENANCE GATE FAILED: Resolved record '{resolved.title}' (DOI {resolved.doi}) "
                f"conflicts with expected dataset '{spec.target_identity}'. "
                f"Violations: {'; '.join(result.mismatches)}"
            )
            raise ProvenanceGateError(message=msg, result=result)

        # Determine archive URL and filename
        url = archive_url or resolved.primary_archive_url or f"https://zenodo.org/api/records/{resolved.record_id}/archive"
        fname = archive_filename or resolved.primary_archive_filename or f"record_{resolved.record_id}.zip"

        return VerifiedProvenanceToken.create(
            spec=spec,
            resolved=resolved,
            archive_url=url,
            archive_filename=fname,
        )


class DatasetQualificationStateMachine:
    """Rigorous state machine governing dataset qualification phases.

    Enforces that BLOCKED_DATASET_PROVENANCE cannot transition directly into
    DOWNLOADING, EXTRACTING, or QUALIFIED states without a fresh successful verification event.
    """

    ALLOWED_TRANSITIONS: dict[QualificationStateEnum, set[QualificationStateEnum]] = {
        QualificationStateEnum.UNINITIALIZED: {
            QualificationStateEnum.PROVENANCE_CHECK_IN_PROGRESS,
            QualificationStateEnum.BLOCKED_DATASET_PROVENANCE,
        },
        QualificationStateEnum.PROVENANCE_CHECK_IN_PROGRESS: {
            QualificationStateEnum.PROVENANCE_VERIFIED,
            QualificationStateEnum.DOWNLOADING,
            QualificationStateEnum.BLOCKED_DATASET_PROVENANCE,
        },
        QualificationStateEnum.BLOCKED_DATASET_PROVENANCE: {
            # Can ONLY transition back to fresh PROVENANCE_CHECK_IN_PROGRESS
            QualificationStateEnum.PROVENANCE_CHECK_IN_PROGRESS,
        },
        QualificationStateEnum.PROVENANCE_VERIFIED: {
            QualificationStateEnum.DOWNLOADING,
            QualificationStateEnum.BLOCKED_DATASET_PROVENANCE,
        },
        QualificationStateEnum.DOWNLOADING: {
            QualificationStateEnum.DOWNLOAD_COMPLETED,
            QualificationStateEnum.BLOCKED_DATASET_PROVENANCE,
        },
        QualificationStateEnum.DOWNLOAD_COMPLETED: {
            QualificationStateEnum.CHECKSUM_VERIFIED,
            QualificationStateEnum.BLOCKED_DATASET_PROVENANCE,
        },
        QualificationStateEnum.CHECKSUM_VERIFIED: {
            QualificationStateEnum.EXTRACTING,
            QualificationStateEnum.BLOCKED_DATASET_PROVENANCE,
        },
        QualificationStateEnum.EXTRACTING: {
            QualificationStateEnum.PHYSICAL_QUALIFYING,
            QualificationStateEnum.BLOCKED_DATASET_PROVENANCE,
        },
        QualificationStateEnum.PHYSICAL_QUALIFYING: {
            QualificationStateEnum.QUALIFIED,
            QualificationStateEnum.BLOCKED_DATASET_PROVENANCE,
        },
        QualificationStateEnum.QUALIFIED: set(),
    }

    def __init__(self, initial_state: QualificationStateEnum = QualificationStateEnum.UNINITIALIZED) -> None:
        self.current_state = initial_state
        self.last_verified_token: Optional[VerifiedProvenanceToken] = None

    def transition_to(
        self,
        new_state: QualificationStateEnum,
        token: Optional[VerifiedProvenanceToken] = None,
    ) -> None:
        """Transition to new state, enforcing transition permissions and token freshness."""
        allowed = self.ALLOWED_TRANSITIONS.get(self.current_state, set())
        if new_state not in allowed:
            raise IllegalStateTransitionError(
                f"Illegal state transition attempted: {self.current_state.value} -> {new_state.value}. "
                f"Allowed destinations: {[s.value for s in allowed]}"
            )

        # Transitioning to PROVENANCE_VERIFIED or DOWNLOADING strictly requires a verified token
        if new_state in (QualificationStateEnum.PROVENANCE_VERIFIED, QualificationStateEnum.DOWNLOADING):
            if token is None:
                raise ProvenanceBypassAttemptError(
                    f"Transition to {new_state.value} rejected: Requires a VerifiedProvenanceToken."
                )
            if not token.verify_integrity():
                raise ProvenanceBypassAttemptError(
                    f"Transition to {new_state.value} rejected: Token integrity verification failed."
                )
            if token.is_stale():
                raise ProvenanceBypassAttemptError(
                    f"Transition to {new_state.value} rejected: Token is stale or expired."
                )
            self.last_verified_token = token

        self.current_state = new_state


class DatasetTransferManager:
    """Architectural download layer enforcing the VerifiedProvenanceToken barrier.

    Under no circumstances can an archive request be issued or archive bytes transferred
    without a valid, fresh, non-tampered VerifiedProvenanceToken.
    """

    def __init__(
        self,
        state_machine: Optional[DatasetQualificationStateMachine] = None,
        transport: Optional[Callable[[str, Path], int]] = None,
    ) -> None:
        self.state_machine = state_machine or DatasetQualificationStateMachine()
        self.transport = transport
        self.archive_requests_issued = 0
        self.bytes_transferred = 0

    def download_archive(
        self,
        token: Any,
        destination_dir: Path,
        expected_metadata: Optional[ResolvedRecordMetadata] = None,
    ) -> Path:
        """Download dataset archive governed strictly by VerifiedProvenanceToken.

        Raises ProvenanceBypassAttemptError if token is missing, invalid, forged, or stale.
        Guarantees archive GET requests = 0 and bytes transferred = 0 upon failure.
        """
        # 1. Type validation
        if not isinstance(token, VerifiedProvenanceToken):
            raise ProvenanceBypassAttemptError(
                "DIRECT_DOWNLOADER_BYPASS_ATTEMPT: Transfer function invoked without a VerifiedProvenanceToken instance."
            )

        # 2. Cryptographic integrity check
        if not token.verify_integrity():
            raise ProvenanceBypassAttemptError(
                "FORGED_TOKEN_ATTEMPT: VerifiedProvenanceToken failed cryptographic integrity check."
            )

        # 3. Decision check
        if token.decision != ProvenanceGateDecision.PASSED:
            raise ProvenanceBypassAttemptError(
                f"INVALID_TOKEN_DECISION: Token decision is '{token.decision.value}', transfer unauthorized."
            )

        # 4. Freshness check
        if token.is_stale(max_age_seconds=600.0):
            raise ProvenanceBypassAttemptError(
                "STALE_TOKEN_ATTEMPT: VerifiedProvenanceToken has expired and cannot authorize transfer."
            )

        # 5. Metadata drift check if live metadata provided
        if expected_metadata is not None:
            if expected_metadata.fingerprint() != token.resolved_metadata_fingerprint:
                raise ProvenanceBypassAttemptError(
                    "METADATA_DRIFT_DETECTED: Remote metadata has changed since token issuance. Re-verification required."
                )

        # 6. State machine transition check
        self.state_machine.transition_to(QualificationStateEnum.DOWNLOADING, token=token)

        # 7. Safe download execution with path traversal defense
        destination_dir = Path(destination_dir).resolve()
        destination_dir.mkdir(parents=True, exist_ok=True)

        raw_fname = token.authorized_archive_filename
        clean_fname = Path(raw_fname).name
        if not clean_fname or clean_fname != raw_fname or ".." in raw_fname or "/" in raw_fname or "\\" in raw_fname:
            raise ProvenanceBypassAttemptError(
                f"PATH_TRAVERSAL_DETECTED: Archive filename '{raw_fname}' contains illegal path components."
            )
        dest_file = (destination_dir / clean_fname).resolve()
        if not str(dest_file).startswith(str(destination_dir)):
            raise ProvenanceBypassAttemptError(
                f"PATH_TRAVERSAL_DETECTED: Destination '{dest_file}' escapes directory '{destination_dir}'."
            )

        self.archive_requests_issued += 1

        if self.transport is not None:
            transferred = self.transport(token.authorized_archive_url, dest_file)
            self.bytes_transferred += transferred
        else:
            # Default urllib transport with Content-Length truncation check
            req = urllib.request.Request(
                token.authorized_archive_url,
                headers={"User-Agent": "OceanSentinel-HardenedDownloader/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp, open(dest_file, "wb") as out_f:
                content_len_hdr = resp.headers.get("Content-Length")
                expected_bytes = int(content_len_hdr) if content_len_hdr and content_len_hdr.isdigit() else None
                file_bytes = 0
                while chunk := resp.read(65536):
                    out_f.write(chunk)
                    file_bytes += len(chunk)
                    self.bytes_transferred += len(chunk)
                if expected_bytes is not None and file_bytes < expected_bytes:
                    if dest_file.exists():
                        dest_file.unlink()
                    self.state_machine.transition_to(QualificationStateEnum.BLOCKED_DATASET_PROVENANCE)
                    raise ProvenanceBypassAttemptError(
                        f"PARTIAL_DOWNLOAD_DETECTED: Received {file_bytes} bytes, "
                        f"expected {expected_bytes} bytes from Content-Length."
                    )

        self.state_machine.transition_to(QualificationStateEnum.DOWNLOAD_COMPLETED)
        return dest_file

    def verify_archive_checksum(
        self,
        archive_path: Path,
        expected_checksum: str,
        algorithm: str = "sha256",
    ) -> bool:
        """Authoritatively verify checksum of downloaded archive and advance state machine.

        Raises ProvenanceBypassAttemptError if checksum does not match.
        Transitions state machine to CHECKSUM_VERIFIED upon success.
        """
        p = Path(archive_path)
        if not p.is_file():
            raise ProvenanceBypassAttemptError(f"Archive file not found for checksum verification: {archive_path}")

        hasher = hashlib.new(algorithm.lower())
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        computed = hasher.hexdigest().lower()
        clean_expected = expected_checksum.strip().lower()

        if computed != clean_expected:
            self.state_machine.transition_to(QualificationStateEnum.BLOCKED_DATASET_PROVENANCE)
            raise ProvenanceBypassAttemptError(
                f"CHECKSUM_MISMATCH: Computed {algorithm.upper()} '{computed}' "
                f"does not match expected '{clean_expected}'."
            )

        self.state_machine.transition_to(QualificationStateEnum.CHECKSUM_VERIFIED)
        return True


class DatasetPreflightContract(BaseModel):
    """Formal preflight contract documenting expected vs resolved attributes before acquisition."""

    intended_dataset_identity: str = Field(..., description="[OBSERVED] Specified target identity")
    requested_doi: Optional[str] = Field(default=None, description="[OBSERVED] Requested DOI")
    resolved_record_id: int = Field(..., description="[OBSERVED] Resolved repository record ID")
    resolved_record_title: str = Field(..., description="[OBSERVED] Resolved record title")
    resolved_record_doi: str = Field(..., description="[OBSERVED] Resolved record DOI")
    expected_platform: str = Field(..., description="[OBSERVED] Expected satellite/sensor platform")
    expected_sensor_band: str = Field(..., description="[OBSERVED] Expected radar frequency band")
    expected_geographic_domain: str = Field(..., description="[OBSERVED] Expected geographic domain")
    prohibited_guards: list[str] = Field(..., description="[OBSERVED] Negative keyword guards")
    required_keywords: list[str] = Field(..., description="[OBSERVED] Positive mandatory keywords")
    verification_decision: ProvenanceGateDecision
    mismatches: list[str] = Field(default_factory=list)
    timestamp_utc: str
    token_fingerprint: Optional[str] = None
    data_access_status: str = "MORP_SYNTH_DATA_ACCESS = UNRESOLVED"

    @classmethod
    def generate(
        cls,
        spec: DatasetProvenanceSpecification,
        resolved: ResolvedRecordMetadata,
        token: Optional[VerifiedProvenanceToken] = None,
    ) -> DatasetPreflightContract:
        """Generate a preflight contract from spec and resolved record."""
        result = ProvenanceGate.evaluate_provenance(spec, resolved)
        now_utc = datetime.now(timezone.utc).isoformat()
        token_fp = token.signature if token else None

        return cls(
            intended_dataset_identity=spec.target_identity,
            requested_doi=spec.expected_doi,
            resolved_record_id=resolved.record_id,
            resolved_record_title=resolved.title,
            resolved_record_doi=resolved.doi,
            expected_platform=spec.expected_platform or "Sentinel-1",
            expected_sensor_band=spec.expected_sensor_band or "C-band",
            expected_geographic_domain=spec.expected_geographic_domain or "Peru",
            prohibited_guards=spec.prohibited_keywords,
            required_keywords=spec.required_keywords,
            verification_decision=result.decision,
            mismatches=result.mismatches,
            timestamp_utc=now_utc,
            token_fingerprint=token_fp,
            data_access_status="MORP_SYNTH_DATA_ACCESS = UNRESOLVED",
        )
