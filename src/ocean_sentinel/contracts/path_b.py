"""Ocean Sentinel Path B Multi-Stage Architecture & Interface Foundation.

Implements the authorized Path B architectural progression:
    binary candidate proposal
            ↓
    candidate-region extraction
            ↓
    lookalike suppression / contextual validation
            ↓
    temporal repeat-pass reasoning
            ↓
    AIS correlation
            ↓
    evidence fusion / attribution

Scientific & Operating Boundaries:
----------------------------------
1. CANDIDATE IS NOT CONFIRMED OIL:
   Binary detector proposal output represents an unverified candidate proposal,
   NOT confirmed oil. No stage may silently convert an upstream proposal into a
   confirmed scientific fact.
2. PROPOSAL IS NOT ATTRIBUTION:
   A candidate proposal or spatial region extraction does not imply vessel
   attribution, source release identity, or causal liability.
3. LOOKALIKE SUPPRESSION IS NOT PHYSICAL PROOF:
   Lookalike suppression evaluates contextual evidence (wind, SST, morphology,
   internal waves, biogenic context). It is an assessment ledger, NOT a magical
   deterministic truth oracle.
4. TEMPORAL RECURRENCE IS NOT PROOF OF CAUSALITY:
   Persistence or dissipation between repeat passes constitutes observational
   change evidence, NOT proof of causal release dynamics.
5. AIS COMPATIBILITY IS NOT VESSEL IDENTIFICATION:
   Spatio-temporal intersection with an AIS trajectory is compatibility evidence.
   Multiple candidate vessels must remain representable. AIS absence does not prove
   vessel absence.
6. UNCERTAINTY & MULTIPLE HYPOTHESES PRESERVED:
   Fusion preserves multiple candidate hypotheses, conflicting observations, and
   unresolved uncertainty states without manufacturing single-scalar confidence.
7. STRICT DEMO VS PHYSICAL SEPARATION:
   PHYSICAL execution mode strictly requires verified operational lineage and
   authoritative metadata; synthetic demo fixtures fail closed.
8. NEVER FABRICATE EVIDENCE:
   No downstream stage may synthesize timestamps, scalar confidences, or
   vessel attributions where authoritative data does not exist.
9. CANONICAL EVIDENCE TRANSLATION BOUNDARY:
   Path B stage-specific contracts define intermediate representations along the 6-stage
   pipeline. The canonical EvidenceItem and EvidenceGraph in `ocean_sentinel.fusion` remain
   the canonical evidence-system representation. Path B contracts translate cleanly into
   EvidenceItem via explicit methods (such as `CandidateRegion.to_evidence_item()`) rather than
   forking a competing evidence truth system.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple, Union, runtime_checkable

from ocean_sentinel.ais import (
    AISProvenance,
    VesselCoverageStatus,
    haversine_distance_m,
)
from ocean_sentinel.drift import DriftMode, ProvenanceGateError
from ocean_sentinel.fusion import (
    DerivationType,
    EvidenceItem,
    EvidenceType,
    ObservationStatus,
    ProvenanceClass,
    SourceType,
)
from ocean_sentinel.temporal import ChangeCategory, TimestampProvenance

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PathBContractError(Exception):
    """Base exception for Path B architectural contract errors."""

    pass


class ScientificBoundaryViolationError(PathBContractError):
    """Raised when an operation attempts to violate non-negotiable scientific boundaries.

    Examples:
    - Attempting to declare a candidate proposal as confirmed oil.
    - Attempting to force vessel attribution without unproven hypothesis representation.
    - Attempting to claim lookalike suppression provides physical identity proof.
    - Attempting to infer causal origin from temporal recurrence alone.
    """

    pass


class ProvenanceGateViolationError(ProvenanceGateError, PathBContractError):
    """Raised when PHYSICAL execution receives synthetic fixtures or lacks authoritative provenance."""

    pass


# ---------------------------------------------------------------------------
# Enums: Execution Modes, Evidence Statuses & Stage Classifications
# ---------------------------------------------------------------------------


class ExecutionMode(str, Enum):
    """Operational execution mode enforcing separation between physical and demo runs."""

    DEMO = "DEMO"
    PHYSICAL = "PHYSICAL"


class EvidenceStatus(str, Enum):
    """Auditable evidence lifecycle status across pipeline stages."""

    UNVERIFIED_CANDIDATE = "UNVERIFIED_CANDIDATE"
    PROPOSED = "PROPOSED"
    ASSESSED = "ASSESSED"
    CORRELATED = "CORRELATED"
    FUSED = "FUSED"
    SUPPRESSED_LOOKALIKE = "SUPPRESSED_LOOKALIKE"
    INCONCLUSIVE = "INCONCLUSIVE"
    REJECTED_PROVENANCE = "REJECTED_PROVENANCE"


class LookalikeSuppressionCategory(str, Enum):
    """Contextual physical or oceanographic phenomenon associated with false-positive lookalikes."""

    POSSIBLE_BIOGENIC_SLICK = "POSSIBLE_BIOGENIC_SLICK"
    LOW_WIND_AREA = "LOW_WIND_AREA"
    INTERNAL_WAVES = "INTERNAL_WAVES"
    RAIN_CELL_DOWNDRAFT = "RAIN_CELL_DOWNDRAFT"
    CURRENT_SHEAR = "CURRENT_SHEAR"
    TERRAIN_SHADOW = "TERRAIN_SHADOW"
    UNRESOLVED_TEXTURE = "UNRESOLVED_TEXTURE"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


class LookalikeSuppressionAction(str, Enum):
    """Actionable recommendation resulting from contextual lookalike evaluation."""

    NO_SUPPRESSION = "NO_SUPPRESSION"
    FLAGGED_SUSPECT_LOOKALIKE = "FLAGGED_SUSPECT_LOOKALIKE"
    STRONGLY_SUPPRESSED = "STRONGLY_SUPPRESSED"
    INSUFFICIENT_EVALUATION_DATA = "INSUFFICIENT_EVALUATION_DATA"


class TemporalConsistencyStatus(str, Enum):
    """Temporal recurrence and persistence classification across repeat satellite passes."""

    SINGLE_PASS_UNOBSERVED_PRIOR = "SINGLE_PASS_UNOBSERVED_PRIOR"
    PERSISTENT_FEATURE = "PERSISTENT_FEATURE"
    NEW_CANDIDATE = "NEW_CANDIDATE"
    DISSIPATED_NO_LONGER_DETECTED = "DISSIPATED_NO_LONGER_DETECTED"
    RAPID_DISPERSION_ATMOSPHERIC = "RAPID_DISPERSION_ATMOSPHERIC"
    INSUFFICIENT_TEMPORAL_COVERAGE = "INSUFFICIENT_TEMPORAL_COVERAGE"


# ---------------------------------------------------------------------------
# Provenance & Lineage Tracking
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LineageRecord:
    """Immutable provenance and cryptographic lineage tracker for every pipeline stage object.

    DECISION 1 — LINEAGE IDENTITY SEMANTICS:
    `lineage_sha256` proves derivational lineage identity only (stage name, source identity,
    parent hashes, timestamp provenance, execution mode, scenario context, and synthetic flag).
    It does NOT prove:
    - payload integrity
    - authenticity
    - authentication
    - non-repudiation
    Payload content hashing is deferred to future scope when a canonical, circularity-free
    payload serialization representation is available.
    """

    stage_name: str
    source_id: str
    parent_hashes: Tuple[str, ...] = field(default_factory=tuple)
    timestamp_provenance: TimestampProvenance = TimestampProvenance.UNKNOWN
    execution_mode: ExecutionMode = ExecutionMode.DEMO
    scenario_id: Optional[str] = None
    is_synthetic: bool = False
    lineage_sha256: str = ""

    def __post_init__(self) -> None:
        if not self.lineage_sha256:
            # Deterministic hash of immutable lineage parameters
            raw = (
                f"{self.stage_name}:{self.source_id}:{','.join(self.parent_hashes)}:"
                f"{self.timestamp_provenance.value}:{self.execution_mode.value}:"
                f"{self.scenario_id or 'none'}:{self.is_synthetic}"
            )
            object.__setattr__(
                self, "lineage_sha256", hashlib.sha256(raw.encode("utf-8")).hexdigest()
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "source_id": self.source_id,
            "parent_hashes": list(self.parent_hashes),
            "timestamp_provenance": self.timestamp_provenance.value,
            "execution_mode": self.execution_mode.value,
            "scenario_id": self.scenario_id,
            "is_synthetic": self.is_synthetic,
            "lineage_sha256": self.lineage_sha256,
        }


# ---------------------------------------------------------------------------
# Stage 1: Candidate Proposal Contract
# ---------------------------------------------------------------------------


@dataclass
class CandidateProposal:
    """Contract representing candidate proposal front-end output (e.g. from EXP-06 or alternative model).

    NON-NEGOTIABLE SCIENTIFIC BOUNDARY:
    A candidate proposal is an unverified hypothesis produced by a front-end proposal model.
    It is NOT confirmed oil.
    """

    proposal_id: str
    source_scene_id: str
    source_model_identity: str
    execution_mode: ExecutionMode
    grid_crs: str
    lineage: LineageRecord
    scenario_id: Optional[str] = None
    acquisition_timestamp_utc: Optional[datetime] = None
    timestamp_provenance: TimestampProvenance = TimestampProvenance.UNKNOWN
    grid_transform: Optional[Tuple[float, ...]] = None
    raw_scores: Dict[str, float] = field(default_factory=dict)
    evidence_status: EvidenceStatus = EvidenceStatus.UNVERIFIED_CANDIDATE
    scientific_disclaimer: str = (
        "NON-CONFIRMED CANDIDATE PROPOSAL: Binary detector output represents an uncalibrated "
        "candidate proposal front-end and does not constitute confirmed oil detection."
    )

    def __post_init__(self) -> None:
        # Enforce fail-closed provenance in PHYSICAL mode
        self.validate_fail_closed_provenance()

    def validate_fail_closed_provenance(self) -> None:
        """Fail closed if execution mode is PHYSICAL but provenance is synthetic or unverified."""
        if self.execution_mode == ExecutionMode.PHYSICAL:
            if self.lineage.is_synthetic:
                raise ProvenanceGateViolationError(
                    f"PHYSICAL mode rejected proposal '{self.proposal_id}': "
                    "Synthetic demo lineage detected in physical candidate proposal."
                )
            if self.timestamp_provenance in (
                TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP,
                TimestampProvenance.UNKNOWN,
            ):
                raise ProvenanceGateViolationError(
                    f"PHYSICAL mode rejected proposal '{self.proposal_id}': "
                    f"Invalid timestamp provenance '{self.timestamp_provenance.value}'. "
                    "PHYSICAL mode strictly requires verified authoritative observation timestamps."
                )
            if self.acquisition_timestamp_utc is None:
                raise ProvenanceGateViolationError(
                    f"PHYSICAL mode rejected proposal '{self.proposal_id}': "
                    "Acquisition timestamp missing in physical candidate proposal."
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "source_scene_id": self.source_scene_id,
            "source_model_identity": self.source_model_identity,
            "execution_mode": self.execution_mode.value,
            "scenario_id": self.scenario_id,
            "grid_crs": self.grid_crs,
            "grid_transform": list(self.grid_transform) if self.grid_transform else None,
            "acquisition_timestamp_utc": (
                self.acquisition_timestamp_utc.isoformat()
                if self.acquisition_timestamp_utc
                else None
            ),
            "timestamp_provenance": self.timestamp_provenance.value,
            "raw_scores": self.raw_scores,
            "evidence_status": self.evidence_status.value,
            "lineage": self.lineage.to_dict(),
            "scientific_disclaimer": self.scientific_disclaimer,
        }


# ---------------------------------------------------------------------------
# Stage 2: Candidate Region Contract
# ---------------------------------------------------------------------------


@dataclass
class CandidateRegion:
    """Contract representing a polygonized candidate spatial region extracted from a proposal.

    Preserves spatial coordinates, real-world metric morphology, and upstream provenance.
    NON-NEGOTIABLE SCIENTIFIC BOUNDARY:
    An extracted candidate region is a geometric representation of an unverified candidate proposal.
    It does not prove physical presence of oil.
    """

    region_id: str
    parent_proposal_id: str
    source_scene_id: str
    execution_mode: ExecutionMode
    geometry_geojson: Dict[str, Any]
    geometry_crs: str
    bbox: Tuple[float, float, float, float]
    centroid: Tuple[float, float]
    pixel_count: int
    area_m2: float
    area_crs: str
    lineage: LineageRecord
    scenario_id: Optional[str] = None
    morphology_metrics: Dict[str, Any] = field(default_factory=dict)
    acquisition_timestamp_utc: Optional[datetime] = None
    timestamp_provenance: TimestampProvenance = TimestampProvenance.UNKNOWN
    score_statistics: Optional[Dict[str, float]] = None
    evidence_status: EvidenceStatus = EvidenceStatus.PROPOSED
    scientific_disclaimer: str = (
        "EXTRACTED CANDIDATE REGION: Vectorized polygon representation of an unverified "
        "candidate proposal. Does not constitute confirmed oil detection."
    )

    def __post_init__(self) -> None:
        self.validate_fail_closed_provenance()

    def validate_fail_closed_provenance(self) -> None:
        """Fail closed if execution mode is PHYSICAL but provenance is synthetic or unverified."""
        if self.execution_mode == ExecutionMode.PHYSICAL:
            if self.lineage.is_synthetic:
                raise ProvenanceGateViolationError(
                    f"PHYSICAL mode rejected candidate region '{self.region_id}': "
                    "Synthetic demo lineage detected in physical candidate region."
                )
            if self.timestamp_provenance in (
                TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP,
                TimestampProvenance.UNKNOWN,
            ):
                raise ProvenanceGateViolationError(
                    f"PHYSICAL mode rejected candidate region '{self.region_id}': "
                    f"Invalid timestamp provenance '{self.timestamp_provenance.value}'."
                )
            if self.acquisition_timestamp_utc is None:
                raise ProvenanceGateViolationError(
                    f"PHYSICAL mode rejected candidate region '{self.region_id}': "
                    "Acquisition timestamp missing in physical candidate region."
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "parent_proposal_id": self.parent_proposal_id,
            "source_scene_id": self.source_scene_id,
            "execution_mode": self.execution_mode.value,
            "scenario_id": self.scenario_id,
            "geometry_geojson": self.geometry_geojson,
            "geometry_crs": self.geometry_crs,
            "bbox": list(self.bbox),
            "centroid": list(self.centroid),
            "pixel_count": self.pixel_count,
            "area_m2": round(self.area_m2, 2),
            "area_crs": self.area_crs,
            "morphology_metrics": self.morphology_metrics,
            "acquisition_timestamp_utc": (
                self.acquisition_timestamp_utc.isoformat()
                if self.acquisition_timestamp_utc
                else None
            ),
            "timestamp_provenance": self.timestamp_provenance.value,
            "score_statistics": self.score_statistics,
            "evidence_status": self.evidence_status.value,
            "lineage": self.lineage.to_dict(),
            "scientific_disclaimer": self.scientific_disclaimer,
        }

    def to_evidence_item(self) -> EvidenceItem:
        """Convert CandidateRegion to canonical EvidenceItem for fusion graph integration.

        Defensive Provenance Re-Validation (Decision 5 / SR-03):
        Revalidates current mutable state before assigning ProvenanceClass.VERIFIED_OPERATIONAL
        to ensure post-instantiation mutation fails closed.

        Missing Timestamp Semantics (Decision 2 / MD-02):
        Absence of an authoritative acquisition timestamp remains genuinely None.
        Never substitutes Unix epoch or synthetic date sentinels.

        Derived Analysis Status (Decision 3 / MD-03):
        Marks derived analytical candidate regions as canonical ObservationStatus.INFERRED
        rather than direct sensor ObservationStatus.OBSERVED.
        """
        if self.execution_mode == ExecutionMode.PHYSICAL:
            # Defensive re-validation of actual mutable state (Decision 5 / SR-03)
            self.validate_fail_closed_provenance()
            prov_class = ProvenanceClass.VERIFIED_OPERATIONAL
        else:
            prov_class = ProvenanceClass.SYNTHETIC_DEMO

        obs_time = self.acquisition_timestamp_utc  # Genuinely None if absent, NEVER Unix epoch

        limitations = []
        if self.acquisition_timestamp_utc is None:
            limitations.append("NO_AUTHORITATIVE_TIMESTAMP")
        limitations.append("UNVERIFIED_CANDIDATE_PROPOSAL")

        return EvidenceItem(
            evidence_id=f"ev_region_{self.region_id}",
            evidence_type=EvidenceType.SAR_DETECTION,
            source_type=SourceType.SENTINEL_1_SAR,
            source_id=self.source_scene_id,
            observation_time=obs_time,
            provenance_class=prov_class,
            provenance_source=self.lineage.source_id,
            spatial_geometry=self.geometry_geojson,
            execution_identity=self.scenario_id or "path_b_execution",
            parent_evidence_ids=list(self.lineage.parent_hashes),
            root_source_ids=[self.source_scene_id],
            derivation_type=DerivationType.DERIVED_ANALYSIS,
            observed_vs_inferred=ObservationStatus.INFERRED,
            metric_values={
                "area_m2": self.area_m2,
                "pixel_count": self.pixel_count,
                "morphology": self.morphology_metrics,
            },
            limitations=limitations,
            status=self.evidence_status.value,
        )


# ---------------------------------------------------------------------------
# Stage 3: Lookalike Assessment Contract
# ---------------------------------------------------------------------------


@dataclass
class LookalikeAssessment:
    """Contract representing contextual validation and lookalike suppression evidence.

    NON-NEGOTIABLE SCIENTIFIC BOUNDARY:
    Lookalike suppression is modeled as evidence/assessment, NOT as a magical
    deterministic truth oracle. It does NOT prove physical identity.
    """

    assessment_id: str
    parent_region_id: str
    execution_mode: ExecutionMode
    suppression_category: LookalikeSuppressionCategory
    suppression_action: LookalikeSuppressionAction
    assessment_rationale: str
    lineage: LineageRecord
    scenario_id: Optional[str] = None
    contextual_factors: Dict[str, Any] = field(default_factory=dict)
    lookalike_evidence_indicators: List[str] = field(default_factory=list)
    is_confirmed_physical_identity: bool = False
    evidence_status: EvidenceStatus = EvidenceStatus.ASSESSED
    scientific_disclaimer: str = (
        "CONTEXTUAL LOOKALIKE ASSESSMENT: Evaluates contextual lookalike evidence only. "
        "Lookalike suppression is an evidentiary assessment and not a proof of physical identity."
    )

    def __post_init__(self) -> None:
        if self.is_confirmed_physical_identity:
            raise ScientificBoundaryViolationError(
                "Violation of non-negotiable boundary: Lookalike suppression must NEVER claim "
                "proof of physical identity. `is_confirmed_physical_identity` must remain False."
            )
        self.validate_fail_closed_provenance()

    def validate_fail_closed_provenance(self) -> None:
        """Fail closed if execution mode is PHYSICAL but provenance is synthetic."""
        if self.execution_mode == ExecutionMode.PHYSICAL and self.lineage.is_synthetic:
            raise ProvenanceGateViolationError(
                f"PHYSICAL mode rejected lookalike assessment '{self.assessment_id}': "
                "Synthetic demo lineage detected in physical assessment."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "parent_region_id": self.parent_region_id,
            "execution_mode": self.execution_mode.value,
            "scenario_id": self.scenario_id,
            "suppression_category": self.suppression_category.value,
            "suppression_action": self.suppression_action.value,
            "assessment_rationale": self.assessment_rationale,
            "contextual_factors": self.contextual_factors,
            "lookalike_evidence_indicators": self.lookalike_evidence_indicators,
            "is_confirmed_physical_identity": self.is_confirmed_physical_identity,
            "evidence_status": self.evidence_status.value,
            "lineage": self.lineage.to_dict(),
            "scientific_disclaimer": self.scientific_disclaimer,
        }


# ---------------------------------------------------------------------------
# Stage 4: Temporal Evidence Contract
# ---------------------------------------------------------------------------


@dataclass
class TemporalEvidence:
    """Contract representing temporal repeat-pass reasoning evidence.

    NON-NEGOTIABLE SCIENTIFIC BOUNDARY:
    Temporal recurrence is evidence of persistence or dissipation, NOT proof of causality.
    """

    temporal_evidence_id: str
    parent_region_id: str
    execution_mode: ExecutionMode
    t1_scene_id: str
    temporal_status: TemporalConsistencyStatus
    lineage: LineageRecord
    scenario_id: Optional[str] = None
    t0_scene_id: Optional[str] = None
    t0_acquisition_utc: Optional[datetime] = None
    t1_acquisition_utc: Optional[datetime] = None
    timestamp_provenance_t0: TimestampProvenance = TimestampProvenance.UNKNOWN
    timestamp_provenance_t1: TimestampProvenance = TimestampProvenance.UNKNOWN
    change_category: Optional[ChangeCategory] = None
    overlap_iou: Optional[float] = None
    area_delta_m2: Optional[float] = None
    causality_inferred: bool = False
    evidence_status: EvidenceStatus = EvidenceStatus.ASSESSED
    scientific_disclaimer: str = (
        "TEMPORAL REPEAT-PASS EVIDENCE: Quantifies observational persistence or dissipation. "
        "Temporal recurrence is observational evidence, not proof of causality or source release."
    )

    def __post_init__(self) -> None:
        if self.causality_inferred:
            raise ScientificBoundaryViolationError(
                "Violation of non-negotiable boundary: Temporal repeat-pass reasoning must NEVER "
                "claim causality inference. `causality_inferred` must remain False."
            )
        self.validate_fail_closed_provenance()

    def validate_fail_closed_provenance(self) -> None:
        """Fail closed if execution mode is PHYSICAL but provenance is synthetic or unverified.

        Enforces authoritative provenance for BOTH T0 and T1 when both timestamps are part of
        the repeat-pass evidence object (Decision 4 / SR-01).
        """
        if self.execution_mode == ExecutionMode.PHYSICAL:
            if self.lineage.is_synthetic:
                raise ProvenanceGateViolationError(
                    f"PHYSICAL mode rejected temporal evidence '{self.temporal_evidence_id}': "
                    "Synthetic demo lineage detected in physical temporal evidence."
                )

            # T1 provenance validation
            if self.t1_acquisition_utc is None:
                raise ProvenanceGateViolationError(
                    f"PHYSICAL mode rejected temporal evidence '{self.temporal_evidence_id}': "
                    "Missing required T1 acquisition timestamp in physical temporal evidence."
                )
            if self.timestamp_provenance_t1 in (
                TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP,
                TimestampProvenance.UNKNOWN,
            ):
                raise ProvenanceGateViolationError(
                    f"PHYSICAL mode rejected temporal evidence '{self.temporal_evidence_id}': "
                    f"Invalid T1 timestamp provenance '{self.timestamp_provenance_t1.value}'."
                )

            # T0 provenance validation: Required for repeat-pass evidence
            is_repeat_pass = (
                self.temporal_status != TemporalConsistencyStatus.SINGLE_PASS_UNOBSERVED_PRIOR
                or self.t0_scene_id is not None
                or self.t0_acquisition_utc is not None
            )
            if is_repeat_pass:
                if self.t0_acquisition_utc is None:
                    raise ProvenanceGateViolationError(
                        f"PHYSICAL mode rejected temporal evidence '{self.temporal_evidence_id}': "
                        "Missing required T0 acquisition timestamp for repeat-pass evidence."
                    )
                if self.timestamp_provenance_t0 in (
                    TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP,
                    TimestampProvenance.UNKNOWN,
                ):
                    raise ProvenanceGateViolationError(
                        f"PHYSICAL mode rejected temporal evidence '{self.temporal_evidence_id}': "
                        f"Invalid T0 timestamp provenance '{self.timestamp_provenance_t0.value}'."
                    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temporal_evidence_id": self.temporal_evidence_id,
            "parent_region_id": self.parent_region_id,
            "execution_mode": self.execution_mode.value,
            "scenario_id": self.scenario_id,
            "t0_scene_id": self.t0_scene_id,
            "t1_scene_id": self.t1_scene_id,
            "t0_acquisition_utc": (
                self.t0_acquisition_utc.isoformat() if self.t0_acquisition_utc else None
            ),
            "t1_acquisition_utc": (
                self.t1_acquisition_utc.isoformat() if self.t1_acquisition_utc else None
            ),
            "timestamp_provenance_t0": self.timestamp_provenance_t0.value,
            "timestamp_provenance_t1": self.timestamp_provenance_t1.value,
            "temporal_status": self.temporal_status.value,
            "change_category": self.change_category.value if self.change_category else None,
            "overlap_iou": round(self.overlap_iou, 4) if self.overlap_iou is not None else None,
            "area_delta_m2": (
                round(self.area_delta_m2, 2) if self.area_delta_m2 is not None else None
            ),
            "causality_inferred": self.causality_inferred,
            "evidence_status": self.evidence_status.value,
            "lineage": self.lineage.to_dict(),
            "scientific_disclaimer": self.scientific_disclaimer,
        }


# ---------------------------------------------------------------------------
# Stage 5: AIS Compatibility Evidence Contract
# ---------------------------------------------------------------------------


@dataclass
class AISCompatibilityEvidence:
    """Contract representing spatio-temporal AIS vessel correlation evidence.

    NON-NEGOTIABLE SCIENTIFIC BOUNDARY:
    AIS compatibility is spatio-temporal compatibility evidence, NOT vessel identification
    or proof of legal culpability. Multiple candidate vessels must remain representable.
    Absence of AIS does not prove vessel absence.
    """

    correlation_evidence_id: str
    parent_region_id: str
    execution_mode: ExecutionMode
    candidate_vessels: List[Dict[str, Any]]
    lineage: LineageRecord
    scenario_id: Optional[str] = None
    is_attribution_proven: bool = False
    ais_absence_proves_vessel_absence: bool = False
    evidence_status: EvidenceStatus = EvidenceStatus.CORRELATED
    scientific_disclaimer: str = (
        "AIS COMPATIBILITY EVIDENCE: Evaluates spatio-temporal vessel compatibility. "
        "AIS compatibility is not vessel identification or attribution by itself. "
        "Absence of AIS does not prove vessel absence."
    )

    def __post_init__(self) -> None:
        if self.is_attribution_proven:
            raise ScientificBoundaryViolationError(
                "Violation of non-negotiable boundary: AIS correlation must NEVER claim "
                "proven attribution. `is_attribution_proven` must remain False."
            )
        if self.ais_absence_proves_vessel_absence:
            raise ScientificBoundaryViolationError(
                "Violation of non-negotiable boundary: AIS absence MUST NOT be interpreted "
                "as proof of vessel absence. `ais_absence_proves_vessel_absence` must remain False."
            )
        self.validate_fail_closed_provenance()

    def validate_fail_closed_provenance(self) -> None:
        """Fail closed if execution mode is PHYSICAL but provenance is synthetic."""
        if self.execution_mode == ExecutionMode.PHYSICAL and self.lineage.is_synthetic:
            raise ProvenanceGateViolationError(
                f"PHYSICAL mode rejected AIS correlation '{self.correlation_evidence_id}': "
                "Synthetic demo lineage detected in physical AIS correlation."
            )

    @property
    def candidate_count(self) -> int:
        return len(self.candidate_vessels)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_evidence_id": self.correlation_evidence_id,
            "parent_region_id": self.parent_region_id,
            "execution_mode": self.execution_mode.value,
            "scenario_id": self.scenario_id,
            "candidate_vessels": self.candidate_vessels,
            "candidate_count": self.candidate_count,
            "is_attribution_proven": self.is_attribution_proven,
            "ais_absence_proves_vessel_absence": self.ais_absence_proves_vessel_absence,
            "evidence_status": self.evidence_status.value,
            "lineage": self.lineage.to_dict(),
            "scientific_disclaimer": self.scientific_disclaimer,
        }


# ---------------------------------------------------------------------------
# Stage 6: Fusion Evidence Contract
# ---------------------------------------------------------------------------


@dataclass
class FusionEvidence:
    """Contract representing multi-source evidence fusion and attribution reasoning.

    NON-NEGOTIABLE SCIENTIFIC BOUNDARY:
    Fusion synthesizes multi-source corroboration and compatibility. It preserves multiple
    candidate hypotheses and explicit uncertainty states. It does not force a single winner
    or manufacture single-scalar global confidence scores.
    """

    fusion_evidence_id: str
    execution_mode: ExecutionMode
    candidate_region_ids: List[str]
    synthesized_hypotheses: List[Dict[str, Any]]
    uncertainty_state: Dict[str, Any]
    lineage: LineageRecord
    scenario_id: Optional[str] = None
    has_unresolved_uncertainty: bool = True
    single_winner_forced: bool = False
    attribution_adjudicated: bool = False
    contributing_evidence_ids: List[str] = field(default_factory=list)
    evidence_status: EvidenceStatus = EvidenceStatus.FUSED
    scientific_disclaimer: str = (
        "MULTI-SOURCE EVIDENCE FUSION: Synthesizes multi-source evidence into an auditable graph. "
        "Preserves multiple hypotheses and uncertainty states without manufactured single-scalar confidence."
    )

    def __post_init__(self) -> None:
        if self.single_winner_forced and len(self.synthesized_hypotheses) > 1:
            raise ScientificBoundaryViolationError(
                "Violation of non-negotiable boundary: Evidence fusion must preserve all plausible "
                "candidates; single-winner hypothesis selection is prohibited when multiple candidates exist."
            )
        if self.attribution_adjudicated:
            raise ScientificBoundaryViolationError(
                "Violation of non-negotiable boundary: Multi-source evidence fusion must NOT claim "
                "adjudicated legal or causal attribution proof."
            )
        self.validate_fail_closed_provenance()

    def validate_fail_closed_provenance(self) -> None:
        """Fail closed if execution mode is PHYSICAL but provenance is synthetic."""
        if self.execution_mode == ExecutionMode.PHYSICAL and self.lineage.is_synthetic:
            raise ProvenanceGateViolationError(
                f"PHYSICAL mode rejected fusion evidence '{self.fusion_evidence_id}': "
                "Synthetic demo lineage detected in physical evidence fusion."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fusion_evidence_id": self.fusion_evidence_id,
            "execution_mode": self.execution_mode.value,
            "scenario_id": self.scenario_id,
            "candidate_region_ids": self.candidate_region_ids,
            "synthesized_hypotheses": self.synthesized_hypotheses,
            "uncertainty_state": self.uncertainty_state,
            "has_unresolved_uncertainty": self.has_unresolved_uncertainty,
            "single_winner_forced": self.single_winner_forced,
            "attribution_adjudicated": self.attribution_adjudicated,
            "contributing_evidence_ids": self.contributing_evidence_ids,
            "evidence_status": self.evidence_status.value,
            "lineage": self.lineage.to_dict(),
            "scientific_disclaimer": self.scientific_disclaimer,
        }


# ---------------------------------------------------------------------------
# Replaceable Candidate Proposal Protocol & Implementations
# ---------------------------------------------------------------------------


@runtime_checkable
class CandidateProposalProtocol(Protocol):
    """Protocol defining the interface for candidate proposal front-ends.

    Ensures downstream Path B stages are completely decoupled from any single model
    architecture (e.g. EXP-06 is replaceable with zero changes to downstream contracts).
    """

    proposer_identity: str

    def propose(
        self,
        scene_identifier: str,
        execution_mode: ExecutionMode,
        scenario_id: Optional[str] = None,
        acquisition_timestamp_utc: Optional[datetime] = None,
        timestamp_provenance: TimestampProvenance = TimestampProvenance.UNKNOWN,
        grid_crs: str = "EPSG:4326",
        grid_transform: Optional[Tuple[float, ...]] = None,
        is_synthetic: bool = False,
        **kwargs: Any,
    ) -> CandidateProposal:
        """Generate a structured CandidateProposal adhering to the Path B contract."""
        ...


class EXP06CandidateProposalAdapter:
    """Adapter wrapping the existing EXP-06 binary detection model as a candidate proposal front-end.

    TREATMENT:
    Treats EXP-06 binary detection as an EXISTING INTERNAL CANDIDATE PROPOSAL FRONT-END,
    NOT as a universally validated detector.
    """

    def __init__(
        self,
        model_name: str = "EXP-06-ResNet34UNet",
        decision_threshold: float = 0.22,
    ) -> None:
        self.proposer_identity = model_name
        self.decision_threshold = decision_threshold

    def propose(
        self,
        scene_identifier: str,
        execution_mode: ExecutionMode,
        scenario_id: Optional[str] = None,
        acquisition_timestamp_utc: Optional[datetime] = None,
        timestamp_provenance: TimestampProvenance = TimestampProvenance.UNKNOWN,
        grid_crs: str = "EPSG:4326",
        grid_transform: Optional[Tuple[float, ...]] = None,
        is_synthetic: bool = False,
        raw_scores: Optional[Dict[str, float]] = None,
        parent_hashes: Sequence[str] = (),
        **kwargs: Any,
    ) -> CandidateProposal:
        """Produce an unverified candidate proposal from EXP-06 output."""
        scores = dict(raw_scores or {})
        scores.setdefault("decision_threshold", self.decision_threshold)

        lineage = LineageRecord(
            stage_name="candidate_proposal",
            source_id=f"{self.proposer_identity}:{scene_identifier}",
            parent_hashes=tuple(parent_hashes),
            timestamp_provenance=timestamp_provenance,
            execution_mode=execution_mode,
            scenario_id=scenario_id,
            is_synthetic=is_synthetic,
        )

        proposal_id = f"proposal_{scene_identifier}_{lineage.lineage_sha256[:8]}"

        return CandidateProposal(
            proposal_id=proposal_id,
            source_scene_id=scene_identifier,
            source_model_identity=self.proposer_identity,
            execution_mode=execution_mode,
            scenario_id=scenario_id,
            grid_crs=grid_crs,
            grid_transform=grid_transform,
            acquisition_timestamp_utc=acquisition_timestamp_utc,
            timestamp_provenance=timestamp_provenance,
            raw_scores=scores,
            evidence_status=EvidenceStatus.UNVERIFIED_CANDIDATE,
            lineage=lineage,
        )


class ReplaceableCandidateProposalEngine:
    """Alternative candidate proposal front-end used for testing and substitution.

    Proves that candidate proposal is pluggable and that downstream Path B contracts
    do not hard-code dependencies on EXP-06.
    """

    def __init__(self, engine_name: str = "CustomCandidateProposalModelV2") -> None:
        self.proposer_identity = engine_name

    def propose(
        self,
        scene_identifier: str,
        execution_mode: ExecutionMode,
        scenario_id: Optional[str] = None,
        acquisition_timestamp_utc: Optional[datetime] = None,
        timestamp_provenance: TimestampProvenance = TimestampProvenance.UNKNOWN,
        grid_crs: str = "EPSG:4326",
        grid_transform: Optional[Tuple[float, ...]] = None,
        is_synthetic: bool = False,
        raw_scores: Optional[Dict[str, float]] = None,
        parent_hashes: Sequence[str] = (),
        **kwargs: Any,
    ) -> CandidateProposal:
        """Produce candidate proposal using the alternative engine."""
        lineage = LineageRecord(
            stage_name="candidate_proposal",
            source_id=f"{self.proposer_identity}:{scene_identifier}",
            parent_hashes=tuple(parent_hashes),
            timestamp_provenance=timestamp_provenance,
            execution_mode=execution_mode,
            scenario_id=scenario_id,
            is_synthetic=is_synthetic,
        )

        proposal_id = f"proposal_{scene_identifier}_{lineage.lineage_sha256[:8]}"

        return CandidateProposal(
            proposal_id=proposal_id,
            source_scene_id=scene_identifier,
            source_model_identity=self.proposer_identity,
            execution_mode=execution_mode,
            scenario_id=scenario_id,
            grid_crs=grid_crs,
            grid_transform=grid_transform,
            acquisition_timestamp_utc=acquisition_timestamp_utc,
            timestamp_provenance=timestamp_provenance,
            raw_scores=raw_scores or {"custom_confidence": 0.50},
            evidence_status=EvidenceStatus.UNVERIFIED_CANDIDATE,
            lineage=lineage,
        )


# ---------------------------------------------------------------------------
# Stage Transition Wiring & Functions
# ---------------------------------------------------------------------------


def extract_candidate_regions(
    proposal: CandidateProposal,
    extracted_features: Sequence[Dict[str, Any]],
) -> List[CandidateRegion]:
    """Stage 1 -> Stage 2: Extract polygonized candidate regions from a CandidateProposal.

    Enforces lineage tracking (parent hash is bound to proposal's content hash)
    and strictly inherits execution mode, scenario context, and timestamp provenance.
    """
    regions: List[CandidateRegion] = []

    for idx, feat in enumerate(extracted_features):
        region_suffix = f"{idx:04d}"
        region_id = f"{proposal.proposal_id}_reg_{region_suffix}"

        # Bind lineage to parent proposal
        lineage = LineageRecord(
            stage_name="candidate_region_extraction",
            source_id=region_id,
            parent_hashes=(proposal.lineage.lineage_sha256,),
            timestamp_provenance=proposal.timestamp_provenance,
            execution_mode=proposal.execution_mode,
            scenario_id=proposal.scenario_id,
            is_synthetic=proposal.lineage.is_synthetic,
        )

        region = CandidateRegion(
            region_id=region_id,
            parent_proposal_id=proposal.proposal_id,
            source_scene_id=proposal.source_scene_id,
            execution_mode=proposal.execution_mode,
            scenario_id=proposal.scenario_id,
            geometry_geojson=feat.get("geometry", {}),
            geometry_crs=feat.get("geometry_crs", proposal.grid_crs),
            bbox=tuple(feat.get("bbox", (0.0, 0.0, 0.0, 0.0))),  # type: ignore[arg-type]
            centroid=tuple(feat.get("centroid", (0.0, 0.0))),    # type: ignore[arg-type]
            pixel_count=feat.get("pixel_count", 1),
            area_m2=feat.get("area_m2", 0.0),
            area_crs=feat.get("area_crs", "EPSG:3857"),
            morphology_metrics=feat.get("morphology_metrics", {}),
            acquisition_timestamp_utc=proposal.acquisition_timestamp_utc,
            timestamp_provenance=proposal.timestamp_provenance,
            score_statistics=feat.get("score_statistics"),
            evidence_status=EvidenceStatus.PROPOSED,
            lineage=lineage,
        )
        regions.append(region)

    return regions


def assess_lookalikes(
    region: CandidateRegion,
    contextual_factors: Optional[Dict[str, Any]] = None,
    evaluation_rules: Optional[Dict[str, Any]] = None,
) -> LookalikeAssessment:
    """Stage 2 -> Stage 3: Perform contextual validation and lookalike assessment.

    Evaluates contextual factors (e.g. low wind, internal wave patterns, proximity to seeps)
    without claiming deterministic physical proof of identity.
    """
    factors = dict(contextual_factors or {})
    wind_speed = factors.get("wind_speed_mps")

    category = LookalikeSuppressionCategory.INSUFFICIENT_CONTEXT
    action = LookalikeSuppressionAction.NO_SUPPRESSION
    indicators: List[str] = []
    rationale = "Contextual observations evaluated."

    if wind_speed is not None and wind_speed < 3.0:
        category = LookalikeSuppressionCategory.LOW_WIND_AREA
        action = LookalikeSuppressionAction.FLAGGED_SUSPECT_LOOKALIKE
        indicators.append("WIND_SPEED_BELOW_SAR_BRAGG_FLOOR")
        rationale = f"Observed wind speed {wind_speed} m/s is below 3.0 m/s Bragg scatter threshold."
    elif factors.get("internal_wave_pattern_detected", False):
        category = LookalikeSuppressionCategory.INTERNAL_WAVES
        action = LookalikeSuppressionAction.STRONGLY_SUPPRESSED
        indicators.append("CREST_TROUGH_PERIODICITY_MATCH")
        rationale = "Spatial geometry matches oceanic internal wave packet dispersion morphology."
    elif factors.get("biogenic_film_detected", False):
        category = LookalikeSuppressionCategory.POSSIBLE_BIOGENIC_SLICK
        action = LookalikeSuppressionAction.FLAGGED_SUSPECT_LOOKALIKE
        indicators.append("LOW_CONTRAST_GRADIENT")
        rationale = "Slick boundary exhibits diffuse transition characteristic of natural biogenic surfactants."

    lineage = LineageRecord(
        stage_name="lookalike_assessment",
        source_id=f"lookalike_{region.region_id}",
        parent_hashes=(region.lineage.lineage_sha256,),
        timestamp_provenance=region.timestamp_provenance,
        execution_mode=region.execution_mode,
        scenario_id=region.scenario_id,
        is_synthetic=region.lineage.is_synthetic,
    )

    assessment_id = f"lookalike_eval_{region.region_id}_{lineage.lineage_sha256[:8]}"

    status = (
        EvidenceStatus.SUPPRESSED_LOOKALIKE
        if action == LookalikeSuppressionAction.STRONGLY_SUPPRESSED
        else EvidenceStatus.ASSESSED
    )

    return LookalikeAssessment(
        assessment_id=assessment_id,
        parent_region_id=region.region_id,
        execution_mode=region.execution_mode,
        scenario_id=region.scenario_id,
        suppression_category=category,
        suppression_action=action,
        assessment_rationale=rationale,
        contextual_factors=factors,
        lookalike_evidence_indicators=indicators,
        is_confirmed_physical_identity=False,
        evidence_status=status,
        lineage=lineage,
    )


def reason_temporal_repeat_pass(
    region: CandidateRegion,
    prior_scene_id: Optional[str] = None,
    prior_timestamp_utc: Optional[datetime] = None,
    prior_timestamp_provenance: TimestampProvenance = TimestampProvenance.UNKNOWN,
    overlap_iou: Optional[float] = None,
    area_delta_m2: Optional[float] = None,
) -> TemporalEvidence:
    """Stage 2/3 -> Stage 4: Perform temporal repeat-pass reasoning.

    Quantifies persistence vs dissipation across sequential observations.
    Never infers causality or source release proof.
    """
    if prior_scene_id is None or prior_timestamp_utc is None:
        temp_status = TemporalConsistencyStatus.SINGLE_PASS_UNOBSERVED_PRIOR
        change_cat = None
    elif overlap_iou is not None and overlap_iou >= 0.20:
        temp_status = TemporalConsistencyStatus.PERSISTENT_FEATURE
        change_cat = ChangeCategory.PERSISTENT
    elif overlap_iou is not None and overlap_iou < 0.05:
        temp_status = TemporalConsistencyStatus.DISSIPATED_NO_LONGER_DETECTED
        change_cat = ChangeCategory.DISAPPEARED
    else:
        temp_status = TemporalConsistencyStatus.NEW_CANDIDATE
        change_cat = ChangeCategory.NEW

    lineage = LineageRecord(
        stage_name="temporal_reasoning",
        source_id=f"temporal_{region.region_id}",
        parent_hashes=(region.lineage.lineage_sha256,),
        timestamp_provenance=region.timestamp_provenance,
        execution_mode=region.execution_mode,
        scenario_id=region.scenario_id,
        is_synthetic=region.lineage.is_synthetic,
    )

    temporal_id = f"temp_ev_{region.region_id}_{lineage.lineage_sha256[:8]}"

    return TemporalEvidence(
        temporal_evidence_id=temporal_id,
        parent_region_id=region.region_id,
        execution_mode=region.execution_mode,
        scenario_id=region.scenario_id,
        t0_scene_id=prior_scene_id,
        t1_scene_id=region.source_scene_id,
        t0_acquisition_utc=prior_timestamp_utc,
        t1_acquisition_utc=region.acquisition_timestamp_utc,
        timestamp_provenance_t0=prior_timestamp_provenance,
        timestamp_provenance_t1=region.timestamp_provenance,
        temporal_status=temp_status,
        change_category=change_cat,
        overlap_iou=overlap_iou,
        area_delta_m2=area_delta_m2,
        causality_inferred=False,
        evidence_status=EvidenceStatus.ASSESSED,
        lineage=lineage,
    )


def correlate_ais_candidates(
    region: CandidateRegion,
    candidate_vessels: Sequence[Dict[str, Any]],
) -> AISCompatibilityEvidence:
    """Stage 4 -> Stage 5: Correlate candidate vessel tracks against candidate region.

    Preserves multiple candidate vessels. Does not declare vessel attribution or proven release.
    """
    vessels = [dict(v) for v in candidate_vessels]

    lineage = LineageRecord(
        stage_name="ais_correlation",
        source_id=f"ais_{region.region_id}",
        parent_hashes=(region.lineage.lineage_sha256,),
        timestamp_provenance=region.timestamp_provenance,
        execution_mode=region.execution_mode,
        scenario_id=region.scenario_id,
        is_synthetic=region.lineage.is_synthetic,
    )

    ais_id = f"ais_ev_{region.region_id}_{lineage.lineage_sha256[:8]}"

    return AISCompatibilityEvidence(
        correlation_evidence_id=ais_id,
        parent_region_id=region.region_id,
        execution_mode=region.execution_mode,
        scenario_id=region.scenario_id,
        candidate_vessels=vessels,
        is_attribution_proven=False,
        ais_absence_proves_vessel_absence=False,
        evidence_status=EvidenceStatus.CORRELATED,
        lineage=lineage,
    )


def fuse_path_b_evidence(
    region: CandidateRegion,
    lookalike: LookalikeAssessment,
    temporal: TemporalEvidence,
    ais: AISCompatibilityEvidence,
    synthesized_hypotheses: Optional[Sequence[Dict[str, Any]]] = None,
    uncertainty_state: Optional[Dict[str, Any]] = None,
) -> FusionEvidence:
    """Stage 5 -> Stage 6: Fuse all stage evidence into an auditable FusionEvidence ledger.

    Preserves multiple hypotheses and explicit uncertainty states.
    Does not force a single winner or manufacture single-scalar confidence.
    """
    parent_hashes = (
        region.lineage.lineage_sha256,
        lookalike.lineage.lineage_sha256,
        temporal.lineage.lineage_sha256,
        ais.lineage.lineage_sha256,
    )

    lineage = LineageRecord(
        stage_name="evidence_fusion",
        source_id=f"fusion_{region.region_id}",
        parent_hashes=parent_hashes,
        timestamp_provenance=region.timestamp_provenance,
        execution_mode=region.execution_mode,
        scenario_id=region.scenario_id,
        is_synthetic=region.lineage.is_synthetic,
    )

    fusion_id = f"fusion_ev_{region.region_id}_{lineage.lineage_sha256[:8]}"

    unc = dict(uncertainty_state or {})
    unc.setdefault("sensor_latency_uncalibrated", True)
    unc.setdefault("ais_coverage_gaps_present", True)
    unc.setdefault("multiple_plausible_origins_retained", len(synthesized_hypotheses or []) > 1)

    return FusionEvidence(
        fusion_evidence_id=fusion_id,
        execution_mode=region.execution_mode,
        scenario_id=region.scenario_id,
        candidate_region_ids=[region.region_id],
        synthesized_hypotheses=[dict(h) for h in (synthesized_hypotheses or [])],
        uncertainty_state=unc,
        has_unresolved_uncertainty=True,
        single_winner_forced=False,
        attribution_adjudicated=False,
        contributing_evidence_ids=[
            lookalike.assessment_id,
            temporal.temporal_evidence_id,
            ais.correlation_evidence_id,
        ],
        evidence_status=EvidenceStatus.FUSED,
        lineage=lineage,
    )
