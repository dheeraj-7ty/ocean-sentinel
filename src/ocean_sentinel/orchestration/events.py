"""Investigation Event Spine Domain Primitives (Phase 7B).

Provides strongly-typed event contracts, canonical event taxonomy, serialization,
security assertions against credential leakage and host-path exposure, and SSE formatting.

Governance & Safety Principles:
--------------------------------
1. Events represent observability history, NOT execution authorization.
2. Canonical InvestigationRun state remains the authoritative domain root.
3. Event sequence is monotonic and strictly ordered per investigation run.
4. Raw credentials, access tokens, and host-specific absolute paths are strictly prohibited.
5. Gated scientific stages emit STAGE_BLOCKED, never STAGE_STARTED.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import logging
import re
import secrets
from typing import Any, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical Event Taxonomy
# ---------------------------------------------------------------------------


class InvestigationEventType(str, Enum):
    """Enumeration of canonical, bounded Phase 7B investigation event types."""

    # Run Lifecycle Events
    RUN_CREATED = "RUN_CREATED"
    RUN_STARTED = "RUN_STARTED"
    RUN_VALIDATED = "RUN_VALIDATED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"
    RUN_SUSPENDED = "RUN_SUSPENDED"
    RUN_RESUMED = "RUN_RESUMED"
    RUN_CANCELLED = "RUN_CANCELLED"

    # Stage Lifecycle Events
    STAGE_QUEUED = "STAGE_QUEUED"
    STAGE_STARTED = "STAGE_STARTED"
    STAGE_PROGRESS = "STAGE_PROGRESS"
    STAGE_COMPLETED = "STAGE_COMPLETED"
    STAGE_FAILED = "STAGE_FAILED"
    STAGE_SKIPPED = "STAGE_SKIPPED"
    STAGE_INTERRUPTED = "STAGE_INTERRUPTED"
    STAGE_BLOCKED = "STAGE_BLOCKED"

    # Artifact Lifecycle Events
    ARTIFACT_DISCOVERED = "ARTIFACT_DISCOVERED"
    ARTIFACT_REGISTERED = "ARTIFACT_REGISTERED"
    ARTIFACT_VALIDATED = "ARTIFACT_VALIDATED"
    ARTIFACT_CORRUPTED = "ARTIFACT_CORRUPTED"

    # Governance & Provenance Boundary Events
    PROVENANCE_BLOCKED = "PROVENANCE_BLOCKED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"

    # Recovery Events
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"
    RECOVERY_BLOCKED = "RECOVERY_BLOCKED"

    # Operational Telemetry Events
    TELEMETRY_SNAPSHOT = "TELEMETRY_SNAPSHOT"


class EventSeverity(str, Enum):
    """Severity classification for operational investigation events."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Security & Secret Sanitization Guardrails
# ---------------------------------------------------------------------------

EVENT_FORBIDDEN_SECRET_KEYS: frozenset[str] = frozenset({
    "password", "secret", "client_secret", "access_token",
    "refresh_token", "bearer_token", "api_key", "private_key",
    "auth_token", "id_token", "authorization",
})

# Matches drive letters like C:\ or D:/ or unix roots like /Users/ or /home/
HOST_PATH_PATTERNS = (
    re.compile(r"^[A-Za-z]:[\\/].*"),
    re.compile(r"^/(Users|home|root|tmp|var|private|etc)/.*"),
)


def assert_no_event_secrets_or_host_paths(data: Any, context_path: str = "root") -> None:
    """Validate recursively that no secrets or host absolute paths exist in event payloads.

    Raises:
        ValueError: If forbidden credential keys or host paths are discovered.
    """
    if isinstance(data, dict):
        for k, v in data.items():
            key_lower = str(k).lower().strip()
            field_path = f"{context_path}.{k}"
            if key_lower in EVENT_FORBIDDEN_SECRET_KEYS or any(
                secret_sub in key_lower for secret_sub in ["token", "secret", "password"]
            ):
                raise ValueError(
                    f"Forbidden credential key '{k}' detected at '{field_path}' in event payload."
                )
            assert_no_event_secrets_or_host_paths(v, field_path)
    elif isinstance(data, (list, tuple, set)):
        for idx, item in enumerate(data):
            assert_no_event_secrets_or_host_paths(item, f"{context_path}[{idx}]")
    elif isinstance(data, str):
        # Check for host path leakage
        for pattern in HOST_PATH_PATTERNS:
            if pattern.match(data):
                raise ValueError(
                    f"Host-specific absolute filesystem path '{data}' detected at '{context_path}' in event payload. "
                    "Sanitize to relative path before recording event."
                )


# ---------------------------------------------------------------------------
# Typed Investigation Event Model
# ---------------------------------------------------------------------------


@dataclass
class InvestigationEvent:
    """Canonical domain model for durable, streamable investigation events."""

    event_id: str
    run_id: str
    sequence: int
    event_type: str
    schema_version: str = "1.0"
    occurred_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    stage_id: Optional[str] = None
    attempt_id: Optional[str] = None
    producer: str = "InvestigationEngine"
    severity: str = EventSeverity.INFO.value
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError(f"Event sequence must be >= 1, got {self.sequence}")
        # Normalize event_type if enum
        if isinstance(self.event_type, InvestigationEventType):
            self.event_type = self.event_type.value
        # Normalize severity if enum
        if isinstance(self.severity, EventSeverity):
            self.severity = self.severity.value
        # Validate payload security
        assert_no_event_secrets_or_host_paths(self.payload, "payload")

    @classmethod
    def create(
        cls,
        run_id: str,
        sequence: int,
        event_type: Union[InvestigationEventType, str],
        payload: Optional[Dict[str, Any]] = None,
        stage_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
        producer: str = "InvestigationEngine",
        severity: Union[EventSeverity, str] = EventSeverity.INFO,
        correlation_id: Optional[str] = None,
    ) -> InvestigationEvent:
        """Factory constructor ensuring valid deterministic event_id generation."""
        type_str = event_type.value if isinstance(event_type, InvestigationEventType) else str(event_type)
        severity_str = severity.value if isinstance(severity, EventSeverity) else str(severity)
        rand_suffix = secrets.token_hex(3)
        event_id = f"evt_{run_id}_{sequence:06d}_{rand_suffix}"
        clean_payload = payload or {}
        return cls(
            event_id=event_id,
            run_id=run_id,
            sequence=sequence,
            event_type=type_str,
            stage_id=stage_id,
            attempt_id=attempt_id,
            producer=producer,
            severity=severity_str,
            payload=clean_payload,
            correlation_id=correlation_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to serializable dictionary."""
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "occurred_at": self.occurred_at,
            "stage_id": self.stage_id,
            "attempt_id": self.attempt_id,
            "producer": self.producer,
            "severity": self.severity,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
        }

    def to_json(self) -> str:
        """Convert event to single-line JSON string without indentation."""
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InvestigationEvent:
        """Construct event from dictionary representation."""
        return cls(
            event_id=str(data["event_id"]),
            run_id=str(data["run_id"]),
            sequence=int(data["sequence"]),
            event_type=str(data["event_type"]),
            schema_version=str(data.get("schema_version", "1.0")),
            occurred_at=str(data.get("occurred_at", datetime.now(timezone.utc).isoformat())),
            stage_id=data.get("stage_id"),
            attempt_id=data.get("attempt_id"),
            producer=str(data.get("producer", "InvestigationEngine")),
            severity=str(data.get("severity", EventSeverity.INFO.value)),
            payload=dict(data.get("payload", {})),
            correlation_id=data.get("correlation_id"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> InvestigationEvent:
        """Parse event from single JSON string."""
        return cls.from_dict(json.loads(json_str))

    def to_sse(self) -> str:
        """Format event according to Server-Sent Events (SSE) standard framing.

        Format:
            id: <sequence>
            event: <event_type>
            data: <json_string>
            \n\n
        """
        payload_json = self.to_json()
        return f"id: {self.sequence}\nevent: {self.event_type}\ndata: {payload_json}\n\n"
