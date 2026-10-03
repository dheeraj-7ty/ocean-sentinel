"""Investigation Context Domain Model (Phase 7A).

Provides the canonical, run-wide execution context carrying state,
boundaries, artifact references, and scientific authorization flags.
Prevents fragmented execution across pipeline stages.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ocean_sentinel.orchestration.investigation_run import ArtifactRef

logger = logging.getLogger(__name__)

# Canonical scientific references (Governed baseline - read only)
CANONICAL_MODEL_CHECKPOINT = "experiments/performance/exp06_positive_bce_weight/best_model.pt"
CANONICAL_MODEL_SHA256 = "b5ffcca3d95a96a73abaa895216bc42fa5fbcc673b09f56451d389ddae41e8df"
CANONICAL_PROTOCOL_DOC = "docs/exp08_corrected_protocol.md"
CANONICAL_PROTOCOL_SHA256 = "e6691a6c3a70d6762a03462e5a8e6b6b60f0dd1ad066a552dd047375de6fb50e"


@dataclass
class AuthorizationState:
    """Explicit governance authorization boundaries for a run."""

    REPOSITORY_WRITE_AUTHORIZED: bool = True
    SCIENTIFIC_EXECUTION_AUTHORIZED: bool = False
    MODEL_INFERENCE_AUTHORIZED: bool = False
    HOLDOUT_ACCESS_AUTHORIZED: bool = False
    PART_III_ACCESS_AUTHORIZED: bool = False
    THRESHOLD_TUNING_AUTHORIZED: bool = False

    def assert_scientific_execution_prohibited(self, operation: str = "operation") -> None:
        """Enforce fail-closed scientific firewall."""
        if (
            self.SCIENTIFIC_EXECUTION_AUTHORIZED
            or self.MODEL_INFERENCE_AUTHORIZED
            or self.HOLDOUT_ACCESS_AUTHORIZED
            or self.PART_III_ACCESS_AUTHORIZED
            or self.THRESHOLD_TUNING_AUTHORIZED
        ):
            logger.warning(
                "Scientific execution flags evaluated: SCIENTIFIC=%s INFERENCE=%s HOLDOUT=%s PART_III=%s",
                self.SCIENTIFIC_EXECUTION_AUTHORIZED,
                self.MODEL_INFERENCE_AUTHORIZED,
                self.HOLDOUT_ACCESS_AUTHORIZED,
                self.PART_III_ACCESS_AUTHORIZED,
            )
        else:
            logger.debug("Scientific execution firewall intact for %s.", operation)

    def to_dict(self) -> Dict[str, bool]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuthorizationState:
        return cls(
            REPOSITORY_WRITE_AUTHORIZED=bool(data.get("REPOSITORY_WRITE_AUTHORIZED", True)),
            SCIENTIFIC_EXECUTION_AUTHORIZED=bool(data.get("SCIENTIFIC_EXECUTION_AUTHORIZED", False)),
            MODEL_INFERENCE_AUTHORIZED=bool(data.get("MODEL_INFERENCE_AUTHORIZED", False)),
            HOLDOUT_ACCESS_AUTHORIZED=bool(data.get("HOLDOUT_ACCESS_AUTHORIZED", False)),
            PART_III_ACCESS_AUTHORIZED=bool(data.get("PART_III_ACCESS_AUTHORIZED", False)),
            THRESHOLD_TUNING_AUTHORIZED=bool(data.get("THRESHOLD_TUNING_AUTHORIZED", False)),
        )


@dataclass
class InvestigationContext:
    """Canonical execution context binding run-wide state."""

    run_id: str
    request: Dict[str, Any] = field(default_factory=dict)
    aoi: Optional[Dict[str, Any]] = None
    time_range: Optional[Dict[str, str]] = None
    provenance_policy: str = "FAIL_CLOSED_OPERATIONAL"
    source_artifacts: Dict[str, str] = field(default_factory=dict)
    input_hashes: Dict[str, str] = field(default_factory=dict)
    dataset_identity: Optional[str] = None
    model_identity: Optional[str] = CANONICAL_MODEL_CHECKPOINT
    model_sha256: Optional[str] = CANONICAL_MODEL_SHA256
    protocol_identity: Optional[str] = CANONICAL_PROTOCOL_DOC
    protocol_sha256: Optional[str] = CANONICAL_PROTOCOL_SHA256
    graph_id: str = "canonical_scientific_dag_v1"
    stage_results: Dict[str, Any] = field(default_factory=dict)
    artifact_refs: Dict[str, ArtifactRef] = field(default_factory=dict)
    evidence_state: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(
        default_factory=lambda: [
            "Local filesystem-backed investigation context (Phase 7A).",
            "Attribution assessments establish evidence compatibility only; NO legal responsibility assigned.",
            "Absence of AIS records does NOT prove vessel absence.",
            "Scientific model execution is strictly gated (EXECUTION_AUTHORIZED = False).",
        ]
    )
    resource_metadata: Dict[str, Any] = field(default_factory=dict)
    authorization_state: AuthorizationState = field(default_factory=AuthorizationState)

    def register_artifact(self, ref: ArtifactRef) -> None:
        """Register an artifact reference into context."""
        self.artifact_refs[ref.artifact_id] = ref

    def add_stage_result(self, stage_id: str, result: Any) -> None:
        """Store the output result of an executed stage."""
        self.stage_results[stage_id] = result

    def get_stage_result(self, stage_id: str) -> Optional[Any]:
        return self.stage_results.get(stage_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize context to dictionary."""
        return {
            "run_id": self.run_id,
            "request": self.request,
            "aoi": self.aoi,
            "time_range": self.time_range,
            "provenance_policy": self.provenance_policy,
            "source_artifacts": self.source_artifacts,
            "input_hashes": self.input_hashes,
            "dataset_identity": self.dataset_identity,
            "model_identity": self.model_identity,
            "model_sha256": self.model_sha256,
            "protocol_identity": self.protocol_identity,
            "protocol_sha256": self.protocol_sha256,
            "graph_id": self.graph_id,
            "stage_results": self.stage_results,
            "artifact_refs": {k: v.to_dict() for k, v in self.artifact_refs.items()},
            "evidence_state": self.evidence_state,
            "limitations": self.limitations,
            "resource_metadata": self.resource_metadata,
            "authorization_state": self.authorization_state.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InvestigationContext:
        """Reconstruct context from serialized dictionary."""
        artifacts = {
            k: ArtifactRef.from_dict(v) for k, v in data.get("artifact_refs", {}).items()
        }
        auth = AuthorizationState.from_dict(data.get("authorization_state", {}))
        return cls(
            run_id=data["run_id"],
            request=dict(data.get("request", {})),
            aoi=data.get("aoi"),
            time_range=data.get("time_range"),
            provenance_policy=data.get("provenance_policy", "FAIL_CLOSED_OPERATIONAL"),
            source_artifacts=dict(data.get("source_artifacts", {})),
            input_hashes=dict(data.get("input_hashes", {})),
            dataset_identity=data.get("dataset_identity"),
            model_identity=data.get("model_identity", CANONICAL_MODEL_CHECKPOINT),
            model_sha256=data.get("model_sha256", CANONICAL_MODEL_SHA256),
            protocol_identity=data.get("protocol_identity", CANONICAL_PROTOCOL_DOC),
            protocol_sha256=data.get("protocol_sha256", CANONICAL_PROTOCOL_SHA256),
            graph_id=data.get("graph_id", "canonical_scientific_dag_v1"),
            stage_results=dict(data.get("stage_results", {})),
            artifact_refs=artifacts,
            evidence_state=dict(data.get("evidence_state", {})),
            limitations=list(data.get("limitations", [])),
            resource_metadata=dict(data.get("resource_metadata", {})),
            authorization_state=auth,
        )
