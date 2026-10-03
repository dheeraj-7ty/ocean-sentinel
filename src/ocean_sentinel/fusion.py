r"""Ocean Sentinel Multi-Source Evidence Fusion Engine V1.

Fuses multi-modal observations, temporal changes, candidate drift trajectories,
and AIS vessel tracking evidence into an auditable, explainable Evidence Graph.

Scientific & Legal Operating Boundaries:
----------------------------------------
1. NON-ATTRIBUTION PRINCIPLE:
   This module evaluates SPATIO-TEMPORAL EVIDENCE COMPATIBILITY and CORROBORATION only.
   It MUST NOT claim proven release source, responsible vessel, legal culpability,
   or causal certainty.
2. NO PSEUDO-PROBABILITY:
   Does not manufacture single scalar "attribution probabilities" or "confidence scores".
   Exposes an auditable, explainable evidence ledger and dependency graph.
3. STRICT DEPENDENCY & INDEPENDENCE CONTROL:
   Differentiates between independent source corroboration and multiple analyses
   derived from the same underlying physical observation (e.g. SAR detection vs
   temporal change from identical scenes; raw AIS vs derived AIS tracks).
   Prevents double-counting.
4. NEGATIVE-PROOF GUARD:
   Absence of an AIS track in a candidate region does NOT prove vessel absence
   (accounting for receiver gaps, satellite latency, and transponder-off periods).
5. MULTIPLE PLAUSIBLE CANDIDATES:
   Preserves all compatible vessel and origin hypotheses; does not force a single
   winner when multiple candidates remain plausible.
6. CONFLICT PRESERVATION:
   Contradictory and inconsistent evidence is explicitly retained rather than
   erased or averaged away.
7. PROVENANCE GATES:
   PHYSICAL mode strictly requires verified operational feeds and accredited adapters.
   Synthetic demo fixtures fail closed in PHYSICAL mode.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
from shapely.geometry import LineString, MultiPoint, MultiPolygon, Point, Polygon, mapping, shape
import shapely

from ocean_sentinel.ais import (
    AISProvenance,
    VesselCoverageStatus,
    haversine_distance_m,
)
from ocean_sentinel.drift import (
    DirectionMode,
    DriftMode,
    ProvenanceGateError,
)
from ocean_sentinel.temporal import TimestampProvenance

logger = logging.getLogger(__name__)

# Repository accreditation seal for operational fusion providers
_REPO_FUSION_ACCREDITATION_KEY = "OCEAN_SENTINEL_REPO_ACCREDITED_FUSION_SEAL_V1"


# ---------------------------------------------------------------------------
# Enums: Categories, Lineage, Relations & Statuses
# ---------------------------------------------------------------------------


class FusionMode(str, Enum):
    """Operational mode of the evidence fusion engine."""

    DEMO = "DEMO"
    PHYSICAL = "PHYSICAL"


class EvidenceType(str, Enum):
    """Canonical classification of evidence items."""

    SAR_DETECTION = "SAR_DETECTION"
    TEMPORAL_CHANGE = "TEMPORAL_CHANGE"
    DRIFT_TRAJECTORY = "DRIFT_TRAJECTORY"
    DRIFT_ORIGIN_HYPOTHESIS = "DRIFT_ORIGIN_HYPOTHESIS"
    AIS_OBSERVATION = "AIS_OBSERVATION"
    AIS_TRACK = "AIS_TRACK"
    AIS_CORRELATION = "AIS_CORRELATION"
    OPTICAL_OBSERVATION = "OPTICAL_OBSERVATION"
    AUXILIARY_OBSERVATION = "AUXILIARY_OBSERVATION"


class SourceType(str, Enum):
    """Sensor or analytical engine that produced the evidence."""

    SENTINEL_1_SAR = "SENTINEL_1_SAR"
    TEMPORAL_ANALYSIS = "TEMPORAL_ANALYSIS"
    LAGRANGIAN_DRIFT_MODEL = "LAGRANGIAN_DRIFT_MODEL"
    VESSEL_AIS_FEED = "VESSEL_AIS_FEED"
    OPTICAL_SATELLITE = "OPTICAL_SATELLITE"
    MARITIME_REPORT = "MARITIME_REPORT"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


class ProvenanceClass(str, Enum):
    """Integrity and authority classification of source evidence."""

    VERIFIED_OPERATIONAL = "VERIFIED_OPERATIONAL"
    HISTORICAL_ARCHIVE = "HISTORICAL_ARCHIVE"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    UNVERIFIED_EXTERNAL = "UNVERIFIED_EXTERNAL"


class DerivationType(str, Enum):
    """Degree of processing between sensor observation and evidence item."""

    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    DERIVED_ANALYSIS = "DERIVED_ANALYSIS"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


class ObservationStatus(str, Enum):
    """Epistemic nature of the spatial-temporal position."""

    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    HYPOTHESIS = "HYPOTHESIS"


class IndependenceRelation(str, Enum):
    """Lineage dependency relationship between two evidence items."""

    INDEPENDENT_SOURCE = "INDEPENDENT_SOURCE"
    SHARED_SOURCE = "SHARED_SOURCE"
    DERIVED_FROM = "DERIVED_FROM"
    SAME_OBSERVATION = "SAME_OBSERVATION"
    UNKNOWN_DEPENDENCY = "UNKNOWN_DEPENDENCY"


class RelationshipType(str, Enum):
    """Semantic and spatial-temporal relationship between evidence and hypothesis."""

    SUPPORTS = "SUPPORTS"
    CONSISTENT_WITH = "CONSISTENT_WITH"
    CONTRADICTS = "CONTRADICTS"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    INCONSISTENT_WITH = "INCONSISTENT_WITH"
    DERIVED_FROM = "DERIVED_FROM"
    SHARES_SOURCE = "SHARES_SOURCE"
    TEMPORALLY_ALIGNED = "TEMPORALLY_ALIGNED"
    SPATIALLY_ALIGNED = "SPATIALLY_ALIGNED"
    SPATIALLY_INCONSISTENT = "SPATIALLY_INCONSISTENT"
    TEMPORALLY_INCONSISTENT = "TEMPORALLY_INCONSISTENT"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class HypothesisStatus(str, Enum):
    """Evidence-bounded overall status for a candidate hypothesis."""

    SUPPORTED_BY_AVAILABLE_EVIDENCE = "SUPPORTED_BY_AVAILABLE_EVIDENCE"
    CONSISTENT_WITH_AVAILABLE_EVIDENCE = "CONSISTENT_WITH_AVAILABLE_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


# ---------------------------------------------------------------------------
# Canonical Evidence Item
# ---------------------------------------------------------------------------


class EvidenceItem:
    """Canonical normalized evidence item ingested into the fusion engine."""

    def __init__(
        self,
        evidence_id: str,
        evidence_type: Union[EvidenceType, str],
        source_type: Union[SourceType, str],
        source_id: str,
        observation_time: Optional[datetime] = None,
        provenance_class: Union[ProvenanceClass, str] = ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source: str = "unknown",
        spatial_geometry: Optional[Union[Dict[str, Any], Polygon, LineString, Point, MultiPolygon]] = None,
        source_artifact: Optional[str] = None,
        execution_identity: Optional[str] = None,
        parent_evidence_ids: Optional[List[str]] = None,
        root_source_ids: Optional[List[str]] = None,
        derivation_type: Union[DerivationType, str] = DerivationType.DIRECT_OBSERVATION,
        observed_vs_inferred: Union[ObservationStatus, str] = ObservationStatus.OBSERVED,
        metric_values: Optional[Dict[str, Any]] = None,
        limitations: Optional[List[str]] = None,
        status: str = "ACTIVE",
    ) -> None:
        self.evidence_id = str(evidence_id).strip()
        self.evidence_type = (
            evidence_type.value if isinstance(evidence_type, EvidenceType) else str(evidence_type)
        )
        self.source_type = (
            source_type.value if isinstance(source_type, SourceType) else str(source_type)
        )
        self.source_id = str(source_id).strip()
        if observation_time is None:
            self.observation_time = None
        else:
            self.observation_time = (
                observation_time if observation_time.tzinfo is not None
                else observation_time.replace(tzinfo=timezone.utc)
            )
        self.provenance_class = (
            provenance_class.value if isinstance(provenance_class, ProvenanceClass) else str(provenance_class)
        )
        self.provenance_source = str(provenance_source).strip()

        # Normalize geometry to GeoJSON dict mapping
        if spatial_geometry is None:
            self.spatial_geometry = None
        elif isinstance(spatial_geometry, dict):
            self.spatial_geometry = spatial_geometry
        else:
            self.spatial_geometry = mapping(spatial_geometry)

        self.source_artifact = str(source_artifact) if source_artifact else None
        self.execution_identity = str(execution_identity) if execution_identity else "default_run"
        self.parent_evidence_ids = list(parent_evidence_ids or [])
        self.root_source_ids = list(root_source_ids or [self.source_id])
        self.derivation_type = (
            derivation_type.value if isinstance(derivation_type, DerivationType) else str(derivation_type)
        )
        self.observed_vs_inferred = (
            observed_vs_inferred.value if isinstance(observed_vs_inferred, ObservationStatus) else str(observed_vs_inferred)
        )
        self.metric_values = dict(metric_values or {})
        self.limitations = list(limitations or [])
        self.status = str(status)

        # Integrity seal (tamper detection)
        self._seal = self._compute_seal()

    def _compute_seal(self) -> str:
        """Compute SHA-256 seal over canonical evidence fields."""
        geom_str = json.dumps(self.spatial_geometry, sort_keys=True) if self.spatial_geometry else "none"
        metrics_str = json.dumps(self.metric_values, sort_keys=True)
        obs_time_str = self.observation_time.isoformat() if self.observation_time is not None else "none"
        raw = (
            f"{self.evidence_id}:{self.evidence_type}:{self.source_type}:{self.source_id}:"
            f"{obs_time_str}:{self.provenance_class}:{geom_str}:{metrics_str}:"
            f"{','.join(sorted(self.parent_evidence_ids))}:{','.join(sorted(self.root_source_ids))}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @property
    def content_tamper_seal(self) -> str:
        """Deterministic SHA-256 seal computed at instantiation."""
        return self._seal

    def verify_integrity(self) -> bool:
        """Verify that record metadata has not been mutated post-instantiation."""
        return hasattr(self, "_seal") and self._seal == self._compute_seal()

    @property
    def shapely_geometry(self) -> Optional[Any]:
        """Convert spatial_geometry dict to a Shapely geometry if present."""
        if not self.spatial_geometry:
            return None
        try:
            return shape(self.spatial_geometry)
        except Exception:
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize evidence item into an explainable dictionary."""
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "observation_time_utc": self.observation_time.isoformat() if self.observation_time is not None else None,
            "spatial_geometry": self.spatial_geometry,
            "provenance_class": self.provenance_class,
            "provenance_source": self.provenance_source,
            "source_artifact": self.source_artifact,
            "execution_identity": self.execution_identity,
            "parent_evidence_ids": self.parent_evidence_ids,
            "root_source_ids": self.root_source_ids,
            "derivation_type": self.derivation_type,
            "observed_vs_inferred": self.observed_vs_inferred,
            "metric_values": self.metric_values,
            "limitations": self.limitations,
            "status": self.status,
            "seal": self._seal,
        }


# ---------------------------------------------------------------------------
# Evidence Relationship & Candidate Hypotheses
# ---------------------------------------------------------------------------


@dataclass
class EvidenceRelation:
    """Directed semantic/dependency edge between an evidence item and a hypothesis or ancestor."""

    source_id: str
    target_id: str
    relation_type: RelationshipType
    independence: IndependenceRelation = IndependenceRelation.UNKNOWN_DEPENDENCY
    rationale: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value if isinstance(self.relation_type, RelationshipType) else str(self.relation_type),
            "independence": self.independence.value if isinstance(self.independence, IndependenceRelation) else str(self.independence),
            "rationale": self.rationale,
            "metrics": self.metrics,
        }


class CandidateHypothesis:
    """Evidence-bounded candidate hypothesis evaluated across multiple evidence items."""

    def __init__(
        self,
        hypothesis_id: str,
        hypothesis_type: str,
        subject_id: str,
        spatial_geometry: Optional[Union[Dict[str, Any], Polygon, MultiPolygon, Point]] = None,
        temporal_window: Optional[Tuple[Optional[datetime], Optional[datetime]]] = None,
        supporting_evidence_ids: Optional[List[str]] = None,
        conflicting_evidence_ids: Optional[List[str]] = None,
        consistent_evidence_ids: Optional[List[str]] = None,
        inconclusive_evidence_ids: Optional[List[str]] = None,
        unknown_evidence_ids: Optional[List[str]] = None,
        independent_support_cluster_count: int = 0,
        dependency_summary: Optional[Dict[str, Any]] = None,
        overall_status: Union[HypothesisStatus, str] = HypothesisStatus.INSUFFICIENT_EVIDENCE,
        limitations: Optional[List[str]] = None,
        summary: str = "",
    ) -> None:
        self.hypothesis_id = str(hypothesis_id).strip()
        self.hypothesis_type = str(hypothesis_type).strip()
        self.subject_id = str(subject_id).strip()

        if spatial_geometry is None:
            self.spatial_geometry = None
        elif isinstance(spatial_geometry, dict):
            self.spatial_geometry = spatial_geometry
        else:
            self.spatial_geometry = mapping(spatial_geometry)

        self.temporal_window = temporal_window
        self.supporting_evidence_ids = list(supporting_evidence_ids or [])
        self.conflicting_evidence_ids = list(conflicting_evidence_ids or [])
        self.consistent_evidence_ids = list(consistent_evidence_ids or [])
        self.inconclusive_evidence_ids = list(inconclusive_evidence_ids or [])
        self.unknown_evidence_ids = list(unknown_evidence_ids or [])
        self.independent_support_cluster_count = int(independent_support_cluster_count)
        self.dependency_summary = dict(dependency_summary or {})
        self.overall_status = (
            overall_status.value if isinstance(overall_status, HypothesisStatus) else str(overall_status)
        )
        self.limitations = list(limitations or [])
        self.summary = str(summary)

    def to_dict(self) -> Dict[str, Any]:
        t_win = None
        if self.temporal_window:
            t0, t1 = self.temporal_window
            t_win = [
                t0.isoformat() if t0 else None,
                t1.isoformat() if t1 else None,
            ]

        return {
            "hypothesis_id": self.hypothesis_id,
            "hypothesis_type": self.hypothesis_type,
            "subject_id": self.subject_id,
            "spatial_geometry": self.spatial_geometry,
            "temporal_window_utc": t_win,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "conflicting_evidence_ids": self.conflicting_evidence_ids,
            "consistent_evidence_ids": self.consistent_evidence_ids,
            "inconclusive_evidence_ids": self.inconclusive_evidence_ids,
            "unknown_evidence_ids": self.unknown_evidence_ids,
            "independent_support_cluster_count": self.independent_support_cluster_count,
            "dependency_summary": self.dependency_summary,
            "overall_status": self.overall_status,
            "limitations": self.limitations,
            "summary": self.summary,
        }


class CandidateVesselHypothesis:
    """Specialized candidate hypothesis representing a vessel's spatio-temporal compatibility."""

    def __init__(
        self,
        hypothesis_id: str,
        mmsi: str,
        vessel_name: Optional[str],
        vessel_type: Optional[str],
        closest_approach_distance_m: float,
        closest_approach_time_utc: datetime,
        temporal_offset_hours: float,
        is_position_inferred: bool,
        inside_origin_region: bool,
        inside_trajectory_envelope: bool,
        coverage_status: str,
        evidence_compatibility_score: float,
        supporting_evidence_ids: Optional[List[str]] = None,
        conflicting_evidence_ids: Optional[List[str]] = None,
        consistent_evidence_ids: Optional[List[str]] = None,
        unknown_evidence_ids: Optional[List[str]] = None,
        independent_support_cluster_count: int = 0,
        dependency_summary: Optional[Dict[str, Any]] = None,
        overall_status: Union[HypothesisStatus, str] = HypothesisStatus.INSUFFICIENT_EVIDENCE,
        limitations: Optional[List[str]] = None,
        summary: str = "",
    ) -> None:
        self.hypothesis_id = hypothesis_id
        self.mmsi = mmsi
        self.vessel_name = vessel_name
        self.vessel_type = vessel_type
        self.closest_approach_distance_m = closest_approach_distance_m
        self.closest_approach_time_utc = (
            closest_approach_time_utc if closest_approach_time_utc.tzinfo is not None
            else closest_approach_time_utc.replace(tzinfo=timezone.utc)
        )
        self.temporal_offset_hours = temporal_offset_hours
        self.is_position_inferred = is_position_inferred
        self.inside_origin_region = inside_origin_region
        self.inside_trajectory_envelope = inside_trajectory_envelope
        self.coverage_status = coverage_status
        self.evidence_compatibility_score = evidence_compatibility_score
        self.supporting_evidence_ids = list(supporting_evidence_ids or [])
        self.conflicting_evidence_ids = list(conflicting_evidence_ids or [])
        self.consistent_evidence_ids = list(consistent_evidence_ids or [])
        self.unknown_evidence_ids = list(unknown_evidence_ids or [])
        self.independent_support_cluster_count = independent_support_cluster_count
        self.dependency_summary = dict(dependency_summary or {})
        self.overall_status = (
            overall_status.value if isinstance(overall_status, HypothesisStatus) else str(overall_status)
        )
        self.limitations = list(limitations or [])
        self.summary = summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "mmsi": self.mmsi,
            "vessel_name": self.vessel_name,
            "vessel_type": self.vessel_type,
            "closest_approach_distance_m": round(self.closest_approach_distance_m, 1),
            "closest_approach_time_utc": self.closest_approach_time_utc.isoformat(),
            "temporal_offset_hours": round(self.temporal_offset_hours, 2),
            "is_position_inferred": self.is_position_inferred,
            "inside_origin_region": self.inside_origin_region,
            "inside_trajectory_envelope": self.inside_trajectory_envelope,
            "coverage_status": self.coverage_status,
            "evidence_compatibility_score": round(self.evidence_compatibility_score, 4),
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "conflicting_evidence_ids": self.conflicting_evidence_ids,
            "consistent_evidence_ids": self.consistent_evidence_ids,
            "unknown_evidence_ids": self.unknown_evidence_ids,
            "independent_support_cluster_count": self.independent_support_cluster_count,
            "dependency_summary": self.dependency_summary,
            "overall_status": self.overall_status,
            "limitations": self.limitations,
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Explainable Evidence Graph
# ---------------------------------------------------------------------------


class EvidenceGraph:
    """Directed graph representing evidence items, candidate hypotheses, and their relationships."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[EvidenceRelation] = []

    def add_evidence_node(self, item: EvidenceItem) -> None:
        """Add an evidence item node."""
        self.nodes[item.evidence_id] = {
            "node_type": "EVIDENCE",
            "evidence_type": item.evidence_type,
            "data": item.to_dict(),
        }

    def add_hypothesis_node(self, hypothesis: Union[CandidateHypothesis, CandidateVesselHypothesis]) -> None:
        """Add a candidate hypothesis node."""
        self.nodes[hypothesis.hypothesis_id] = {
            "node_type": "HYPOTHESIS",
            "hypothesis_type": getattr(hypothesis, "hypothesis_type", "CANDIDATE_VESSEL_COMPATIBILITY"),
            "data": hypothesis.to_dict(),
        }

    def add_edge(self, relation: EvidenceRelation) -> None:
        """Add a directed relation edge."""
        self.edges.append(relation)

    def detect_cycles(self) -> bool:
        """Check for dependency cycles in DERIVED_FROM edges (must form a DAG)."""
        adj: Dict[str, List[str]] = {}
        for edge in self.edges:
            rel = edge.relation_type.value if isinstance(edge.relation_type, RelationshipType) else str(edge.relation_type)
            if rel == RelationshipType.DERIVED_FROM.value:
                adj.setdefault(edge.source_id, []).append(edge.target_id)

        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in list(adj.keys()):
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Export explainable graph structure for frontend and audit consumption."""
        return {
            "nodes": self.nodes,
            "edges": [e.to_dict() for e in self.edges],
            "metadata": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "has_dependency_cycles": self.detect_cycles(),
                "negative_proof_guard": "AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE",
                "scientific_boundary": "EVIDENCE_COMPATIBILITY_ONLY_NO_LEGAL_ATTRIBUTION",
            },
        }


# ---------------------------------------------------------------------------
# Lineage, Dependency & Independence Engine
# ---------------------------------------------------------------------------


class IndependenceEngine:
    """Analyzes evidence lineage to distinguish independent sources from shared/derived analyses."""

    def __init__(self, evidence_store: Dict[str, EvidenceItem]) -> None:
        self.evidence_store = evidence_store

    def get_all_ancestors(self, evidence_id: str) -> Set[str]:
        """Recursively collect all upstream ancestor evidence IDs."""
        ancestors: Set[str] = set()
        stack = [evidence_id]
        visited: Set[str] = set()

        while stack:
            curr = stack.pop()
            if curr in visited:
                continue
            visited.add(curr)
            item = self.evidence_store.get(curr)
            if item:
                for p in item.parent_evidence_ids:
                    ancestors.add(p)
                    stack.append(p)
        return ancestors

    def get_root_sources(self, evidence_id: str) -> Set[str]:
        """Extract the fundamental real-world source identities for an evidence item."""
        roots: Set[str] = set()
        item = self.evidence_store.get(evidence_id)
        if not item:
            return roots

        # If explicit root sources provided, use them
        if item.root_source_ids:
            for r in item.root_source_ids:
                roots.add(r)

        # Also inspect parents
        ancestors = self.get_all_ancestors(evidence_id)
        for anc_id in ancestors:
            anc = self.evidence_store.get(anc_id)
            if anc and anc.root_source_ids:
                for r in anc.root_source_ids:
                    roots.add(r)
        return roots

    def classify_relationship(self, id1: str, id2: str) -> IndependenceRelation:
        """Classify independence between two evidence items."""
        if id1 == id2:
            return IndependenceRelation.SAME_OBSERVATION

        item1 = self.evidence_store.get(id1)
        item2 = self.evidence_store.get(id2)
        if not item1 or not item2:
            return IndependenceRelation.UNKNOWN_DEPENDENCY

        anc1 = self.get_all_ancestors(id1)
        anc2 = self.get_all_ancestors(id2)

        # Derived from each other
        if id1 in anc2 or id2 in anc1:
            return IndependenceRelation.DERIVED_FROM

        roots1 = self.get_root_sources(id1)
        roots2 = self.get_root_sources(id2)

        # Check for shared source
        shared = roots1.intersection(roots2)
        if shared:
            return IndependenceRelation.SHARED_SOURCE

        # Completely disjoint root sources
        if roots1 and roots2:
            return IndependenceRelation.INDEPENDENT_SOURCE

        return IndependenceRelation.UNKNOWN_DEPENDENCY

    def group_into_independent_clusters(self, evidence_ids: List[str]) -> List[Set[str]]:
        """Cluster evidence items such that each cluster represents a distinct root source lineage.

        Prevents double-counting: multiple analyses derived from the same source
        are collapsed into a single independent corroborating cluster.
        """
        clusters: List[Set[str]] = []
        cluster_roots: List[Set[str]] = []

        for eid in evidence_ids:
            roots = self.get_root_sources(eid)
            matched = False
            for idx, c_roots in enumerate(cluster_roots):
                if roots and c_roots.intersection(roots):
                    clusters[idx].add(eid)
                    cluster_roots[idx].update(roots)
                    matched = True
                    break
            if not matched:
                clusters.append({eid})
                cluster_roots.append(set(roots))

        return clusters

    def evaluate_independence(self, id1: str, id2: str) -> IndependenceRelation:
        """Evaluate independence between two evidence items (alias for classify_relationship)."""
        return self.classify_relationship(id1, id2)


# ---------------------------------------------------------------------------
# Multi-Source Evidence Fusion Engine
# ---------------------------------------------------------------------------


class EvidenceFusionEngine:
    """Core engine for Multi-Source Evidence Fusion V1."""

    def __init__(
        self,
        mode: FusionMode = FusionMode.DEMO,
        spatial_tolerance_m: float = 5000.0,     # 5 km proximity threshold
        temporal_tolerance_seconds: float = 7200.0, # 2 hours
    ) -> None:
        self.mode = mode if isinstance(mode, FusionMode) else FusionMode(mode)
        self.spatial_tolerance_m = float(spatial_tolerance_m)
        self.temporal_tolerance_seconds = float(temporal_tolerance_seconds)
        self.evidence_store: Dict[str, EvidenceItem] = {}
        self.hypotheses: Dict[str, Union[CandidateHypothesis, CandidateVesselHypothesis]] = {}
        self.graph = EvidenceGraph()

    def ingest_evidence_item(self, item: EvidenceItem) -> None:
        """Ingest and validate an evidence item into the store."""
        # 0. Anti-tamper verification
        if not item.verify_integrity():
            raise ProvenanceGateError(
                f"Tamper detection rejected for evidence item '{item.evidence_id}': "
                "Item metadata has been modified post-instantiation."
            )

        # 1. PHYSICAL mode provenance gate (Anti-Bypass Protection)
        if self.mode == FusionMode.PHYSICAL:
            prov = item.provenance_class
            if prov == ProvenanceClass.SYNTHETIC_DEMO.value or prov == ProvenanceClass.UNVERIFIED_EXTERNAL.value:
                raise ProvenanceGateError(
                    f"PHYSICAL mode rejected: Evidence item '{item.evidence_id}' has non-operational provenance '{prov}'. "
                    "Physical evidence fusion is strictly BLOCKED — AWAITING_OPERATIONAL_SOURCE. "
                    "Callers cannot bypass physical gates by passing synthetic fixtures."
                )

        # 2. Add to store and graph
        self.evidence_store[item.evidence_id] = item
        self.graph.add_evidence_node(item)

        # 3. Add derivation edges to parent ancestors
        for pid in item.parent_evidence_ids:
            if pid in self.evidence_store:
                self.graph.add_edge(
                    EvidenceRelation(
                        source_id=item.evidence_id,
                        target_id=pid,
                        relation_type=RelationshipType.DERIVED_FROM,
                        independence=IndependenceRelation.DERIVED_FROM,
                        rationale=f"Evidence '{item.evidence_id}' is derived from ancestor '{pid}'.",
                    )
                )

    def evaluate_spatial_relation(
        self,
        geom1: Optional[Any],
        geom2: Optional[Any],
    ) -> Tuple[RelationshipType, float]:
        """Evaluate metric spatial correspondence between two Shapely geometries."""
        if geom1 is None or geom2 is None:
            return RelationshipType.UNKNOWN, float("inf")

        try:
            if geom1.intersects(geom2):
                return RelationshipType.SPATIALLY_ALIGNED, 0.0

            # Compute approximate centroid distance on sphere
            c1 = geom1.centroid
            c2 = geom2.centroid
            dist_m = haversine_distance_m(c1.x, c1.y, c2.x, c2.y)

            if dist_m <= self.spatial_tolerance_m:
                return RelationshipType.SPATIALLY_ALIGNED, dist_m
            else:
                return RelationshipType.SPATIALLY_INCONSISTENT, dist_m
        except Exception:
            return RelationshipType.UNKNOWN, float("inf")

    def evaluate_temporal_relation(
        self,
        t1: Optional[datetime],
        t2: Optional[datetime],
    ) -> Tuple[RelationshipType, float]:
        """Evaluate temporal correspondence between two timestamps."""
        if t1 is None or t2 is None:
            return RelationshipType.UNKNOWN, float("inf")

        dt_s = abs((t1 - t2).total_seconds())
        if dt_s <= self.temporal_tolerance_seconds:
            return RelationshipType.TEMPORALLY_ALIGNED, dt_s
        else:
            return RelationshipType.TEMPORALLY_INCONSISTENT, dt_s

    def synthesize_spill_origin_hypothesis(
        self,
        hypothesis_id: str,
        subject_id: str,
        origin_geometry: Optional[Union[Dict[str, Any], Polygon, MultiPolygon]] = None,
        temporal_window: Optional[Tuple[datetime, datetime]] = None,
    ) -> CandidateHypothesis:
        """Synthesize candidate spill origin hypothesis by correlating SAR, Temporal, and Drift evidence."""
        indep = IndependenceEngine(self.evidence_store)
        supporting: List[str] = []
        conflicting: List[str] = []
        consistent: List[str] = []
        unknown: List[str] = []

        target_poly = shape(origin_geometry) if origin_geometry else None

        for eid, item in self.evidence_store.items():
            if item.evidence_type in [
                EvidenceType.SAR_DETECTION.value,
                EvidenceType.TEMPORAL_CHANGE.value,
                EvidenceType.DRIFT_ORIGIN_HYPOTHESIS.value,
                EvidenceType.DRIFT_TRAJECTORY.value,
            ]:
                # Spatial check
                s_rel, dist_m = self.evaluate_spatial_relation(item.shapely_geometry, target_poly)
                # Temporal check
                t_mid = temporal_window[1] if temporal_window else None
                t_rel, dt_s = self.evaluate_temporal_relation(item.observation_time, t_mid)

                if s_rel == RelationshipType.SPATIALLY_ALIGNED and t_rel == RelationshipType.TEMPORALLY_ALIGNED:
                    supporting.append(eid)
                    self.graph.add_edge(
                        EvidenceRelation(
                            source_id=eid,
                            target_id=hypothesis_id,
                            relation_type=RelationshipType.SUPPORTS,
                            independence=IndependenceRelation.UNKNOWN_DEPENDENCY,
                            rationale=f"Item '{eid}' spatially ({dist_m:.0f}m) and temporally ({dt_s/3600:.1f}h) supports origin.",
                            metrics={"distance_m": round(dist_m, 1), "dt_hours": round(dt_s / 3600.0, 2)},
                        )
                    )
                elif s_rel == RelationshipType.SPATIALLY_ALIGNED:
                    consistent.append(eid)
                    self.graph.add_edge(
                        EvidenceRelation(
                            source_id=eid,
                            target_id=hypothesis_id,
                            relation_type=RelationshipType.CONSISTENT_WITH,
                            independence=IndependenceRelation.UNKNOWN_DEPENDENCY,
                            rationale=f"Item '{eid}' is spatially consistent ({dist_m:.0f}m) with origin region.",
                            metrics={"distance_m": round(dist_m, 1)},
                        )
                    )
                elif s_rel == RelationshipType.SPATIALLY_INCONSISTENT and t_rel == RelationshipType.TEMPORALLY_ALIGNED:
                    conflicting.append(eid)
                    self.graph.add_edge(
                        EvidenceRelation(
                            source_id=eid,
                            target_id=hypothesis_id,
                            relation_type=RelationshipType.CONFLICTS_WITH,
                            independence=IndependenceRelation.UNKNOWN_DEPENDENCY,
                            rationale=f"Item '{eid}' spatially conflicts ({dist_m:.0f}m) at aligned time.",
                            metrics={"distance_m": round(dist_m, 1)},
                        )
                    )

        # Independence & double-counting clustering
        clusters = indep.group_into_independent_clusters(supporting)
        indep_count = len(clusters)

        # Deduce status
        if conflicting and not supporting:
            status = HypothesisStatus.CONFLICTING_EVIDENCE
        elif indep_count >= 2 and not conflicting:
            status = HypothesisStatus.SUPPORTED_BY_AVAILABLE_EVIDENCE
        elif supporting or consistent:
            status = HypothesisStatus.CONSISTENT_WITH_AVAILABLE_EVIDENCE
        else:
            status = HypothesisStatus.INSUFFICIENT_EVIDENCE

        dep_summary = {
            "total_supporting_items": len(supporting),
            "independent_source_clusters": indep_count,
            "is_independent_corroboration": indep_count >= 2,
            "double_counting_prevented": len(supporting) > indep_count,
            "clusters": [list(c) for c in clusters],
        }

        hypo = CandidateHypothesis(
            hypothesis_id=hypothesis_id,
            hypothesis_type="CANDIDATE_SPILL_ORIGIN",
            subject_id=subject_id,
            spatial_geometry=origin_geometry,
            temporal_window=temporal_window,
            supporting_evidence_ids=supporting,
            conflicting_evidence_ids=conflicting,
            consistent_evidence_ids=consistent,
            inconclusive_evidence_ids=[],
            unknown_evidence_ids=unknown,
            independent_support_cluster_count=indep_count,
            dependency_summary=dep_summary,
            overall_status=status,
            limitations=[
                "Candidate origin is an evidence-bounded hypothesis, NOT confirmed historical release location.",
                "Windage leeway factor and sub-grid turbulence are unmodeled empirical variance sources.",
            ],
            summary=(
                f"Candidate origin '{hypothesis_id}' evaluated across {len(supporting) + len(consistent) + len(conflicting)} "
                f"evidence items ({indep_count} independent root source clusters). Overall status: {status.value}."
            ),
        )

        self.hypotheses[hypo.hypothesis_id] = hypo
        self.graph.add_hypothesis_node(hypo)
        return hypo

    def synthesize_candidate_vessel_hypotheses(
        self,
        ais_correlation_summary: Dict[str, Any],
        drift_hypothesis_id: str,
    ) -> List[CandidateVesselHypothesis]:
        """Construct candidate vessel compatibility hypotheses from AIS correlation output."""
        indep = IndependenceEngine(self.evidence_store)
        results: List[CandidateVesselHypothesis] = []
        candidates_raw = ais_correlation_summary.get("candidate_vessels", [])

        for v in candidates_raw:
            mmsi = str(v["mmsi"])
            v_name = v.get("vessel_name")
            v_type = v.get("vessel_type")
            hyp_id = f"hypothesis_vessel_{mmsi}"

            min_dist_traj = float(v.get("min_distance_to_trajectory_m", float("inf")))
            min_dist_orig = float(v.get("min_distance_to_origin_m", float("inf")))
            t_approach = datetime.fromisoformat(v["closest_approach_time_utc"].replace("Z", "+00:00"))
            dt_hours = float(v.get("temporal_offset_hours", 0.0))
            is_inferred = bool(v.get("is_position_inferred", False))
            in_origin = bool(v.get("inside_candidate_origin_region", False))
            in_env = bool(v.get("inside_trajectory_envelope", False))
            cov_status = str(v.get("coverage_status", "UNKNOWN"))
            compat_score = float(v.get("evidence_compatibility_score", 0.0))

            supporting: List[str] = []
            conflicting: List[str] = []
            consistent: List[str] = []
            unknown: List[str] = []
            limitations: List[str] = list(v.get("data_limitations", []))

            # 1. Ingest AIS correlation as an evidence item if not already present
            ais_eid = f"evidence_ais_corr_{mmsi}"
            if ais_eid not in self.evidence_store:
                self.ingest_evidence_item(
                    EvidenceItem(
                        evidence_id=ais_eid,
                        evidence_type=EvidenceType.AIS_CORRELATION,
                        source_type=SourceType.VESSEL_AIS_FEED,
                        source_id=f"vessel_{mmsi}",
                        observation_time=t_approach,
                        provenance_class=(
                            ProvenanceClass.VERIFIED_OPERATIONAL
                            if v.get("provenance") == "PHYSICAL_ACCREDITED_FEED"
                            else ProvenanceClass.SYNTHETIC_DEMO
                        ),
                        provenance_source=v.get("provenance", "SYNTHETIC_DEMO_FEED"),
                        parent_evidence_ids=[drift_hypothesis_id] if drift_hypothesis_id in self.evidence_store else [],
                        root_source_ids=[f"MMSI_{mmsi}"],
                        derivation_type=DerivationType.DERIVED_ANALYSIS,
                        observed_vs_inferred=ObservationStatus.INFERRED if is_inferred else ObservationStatus.OBSERVED,
                        metric_values={
                            "min_distance_to_trajectory_m": min_dist_traj,
                            "min_distance_to_origin_m": min_dist_orig,
                            "temporal_offset_hours": dt_hours,
                            "evidence_compatibility_score": compat_score,
                            "inside_origin": in_origin,
                            "coverage_status": cov_status,
                        },
                    )
                )

            # 2. Evaluate relationship based on physical and temporal metrics
            if cov_status == VesselCoverageStatus.TELEMETRY_GAP_ACROSS_WINDOW.value:
                unknown.append(ais_eid)
                self.graph.add_edge(
                    EvidenceRelation(
                        source_id=ais_eid,
                        target_id=hyp_id,
                        relation_type=RelationshipType.DATA_UNAVAILABLE,
                        independence=IndependenceRelation.DERIVED_FROM,
                        rationale=f"Vessel '{mmsi}' experienced telemetry gap; AIS absence is not vessel absence.",
                    )
                )
            elif cov_status == VesselCoverageStatus.OUTSIDE_WINDOW.value or dt_hours > 12.0:
                conflicting.append(ais_eid)
                self.graph.add_edge(
                    EvidenceRelation(
                        source_id=ais_eid,
                        target_id=hyp_id,
                        relation_type=RelationshipType.TEMPORALLY_INCONSISTENT,
                        independence=IndependenceRelation.DERIVED_FROM,
                        rationale=f"Vessel '{mmsi}' temporal offset (+{dt_hours:.1f}h) is inconsistent with hypothesis.",
                        metrics={"temporal_offset_hours": dt_hours},
                    )
                )
            elif min_dist_traj > self.spatial_tolerance_m and min_dist_orig > self.spatial_tolerance_m:
                conflicting.append(ais_eid)
                self.graph.add_edge(
                    EvidenceRelation(
                        source_id=ais_eid,
                        target_id=hyp_id,
                        relation_type=RelationshipType.SPATIALLY_INCONSISTENT,
                        independence=IndependenceRelation.DERIVED_FROM,
                        rationale=f"Vessel '{mmsi}' nearest distance ({min(min_dist_traj, min_dist_orig):.0f}m) is spatially inconsistent.",
                        metrics={"min_distance_m": min(min_dist_traj, min_dist_orig)},
                    )
                )
            elif in_origin and dt_hours <= 1.0 and min_dist_orig <= self.spatial_tolerance_m:
                supporting.append(ais_eid)
                self.graph.add_edge(
                    EvidenceRelation(
                        source_id=ais_eid,
                        target_id=hyp_id,
                        relation_type=RelationshipType.SUPPORTS,
                        independence=IndependenceRelation.DERIVED_FROM,
                        rationale=f"Vessel '{mmsi}' inside origin region ({min_dist_orig:.0f}m) at target time (+{dt_hours:.1f}h).",
                        metrics={"distance_m": min_dist_orig, "dt_hours": dt_hours},
                    )
                )
            elif in_env or min_dist_traj <= self.spatial_tolerance_m:
                consistent.append(ais_eid)
                self.graph.add_edge(
                    EvidenceRelation(
                        source_id=ais_eid,
                        target_id=hyp_id,
                        relation_type=RelationshipType.CONSISTENT_WITH,
                        independence=IndependenceRelation.DERIVED_FROM,
                        rationale=f"Vessel '{mmsi}' trajectory proximity ({min_dist_traj:.0f}m) is consistent with intermediate hypothesis.",
                        metrics={"distance_m": min_dist_traj, "dt_hours": dt_hours},
                    )
                )
            else:
                unknown.append(ais_eid)

            # Check for optical or auxiliary evidence referencing this vessel
            for eid, e_item in self.evidence_store.items():
                if e_item.evidence_type in [EvidenceType.OPTICAL_OBSERVATION.value, EvidenceType.AUXILIARY_OBSERVATION.value]:
                    if e_item.source_id == f"vessel_{mmsi}" or e_item.metric_values.get("target_mmsi") == mmsi:
                        if e_item.status == "CONFLICT":
                            conflicting.append(eid)
                        else:
                            supporting.append(eid)

            # Independence analysis for vessel support
            clusters = indep.group_into_independent_clusters(supporting)
            indep_count = len(clusters)

            # Deduce overall status
            if conflicting and not supporting:
                overall_status = HypothesisStatus.CONFLICTING_EVIDENCE
            elif supporting and conflicting:
                overall_status = HypothesisStatus.CONFLICTING_EVIDENCE
            elif indep_count >= 1 and not conflicting:
                overall_status = HypothesisStatus.SUPPORTED_BY_AVAILABLE_EVIDENCE
            elif consistent:
                overall_status = HypothesisStatus.CONSISTENT_WITH_AVAILABLE_EVIDENCE
            elif unknown:
                overall_status = HypothesisStatus.INSUFFICIENT_EVIDENCE
            else:
                overall_status = HypothesisStatus.DATA_UNAVAILABLE

            dep_summary = {
                "supporting_evidence_count": len(supporting),
                "conflicting_evidence_count": len(conflicting),
                "independent_source_clusters": indep_count,
                "clusters": [list(c) for c in clusters],
            }

            limitations.extend([
                "AIS compatibility establishes spatio-temporal alignment only, NOT legal attribution.",
                "Vessel Course Over Ground (COG) is not required to match slick drift direction.",
                "Absence of an AIS track does NOT prove vessel absence.",
            ])

            hypo_vessel = CandidateVesselHypothesis(
                hypothesis_id=hyp_id,
                mmsi=mmsi,
                vessel_name=v_name,
                vessel_type=v_type,
                closest_approach_distance_m=min(min_dist_traj, min_dist_orig),
                closest_approach_time_utc=t_approach,
                temporal_offset_hours=dt_hours,
                is_position_inferred=is_inferred,
                inside_origin_region=in_origin,
                inside_trajectory_envelope=in_env,
                coverage_status=cov_status,
                evidence_compatibility_score=compat_score,
                supporting_evidence_ids=supporting,
                conflicting_evidence_ids=conflicting,
                consistent_evidence_ids=consistent,
                unknown_evidence_ids=unknown,
                independent_support_cluster_count=indep_count,
                dependency_summary=dep_summary,
                overall_status=overall_status,
                limitations=limitations,
                summary=(
                    f"Candidate vessel '{v_name or mmsi}' (MMSI: {mmsi}): score {compat_score:.4f}, "
                    f"min distance {min(min_dist_traj, min_dist_orig):.0f}m. Status: {overall_status.value}."
                ),
            )

            self.hypotheses[hyp_id] = hypo_vessel
            self.graph.add_hypothesis_node(hypo_vessel)
            results.append(hypo_vessel)

        # Sort candidate vessel hypotheses deterministically by score descending
        results.sort(key=lambda x: x.evidence_compatibility_score, reverse=True)
        return results

    def export_summary(self) -> Dict[str, Any]:
        """Export comprehensive explainable evidence summary."""
        vessel_hyps = [h for h in self.hypotheses.values() if isinstance(h, CandidateVesselHypothesis)]
        spill_hyps = [h for h in self.hypotheses.values() if isinstance(h, CandidateHypothesis)]

        # Determine if multiple plausible candidates exist
        plausible_vessels = [
            v for v in vessel_hyps
            if v.overall_status in [
                HypothesisStatus.SUPPORTED_BY_AVAILABLE_EVIDENCE.value,
                HypothesisStatus.CONSISTENT_WITH_AVAILABLE_EVIDENCE.value,
            ]
        ]

        return {
            "engine": "ocean_sentinel_evidence_fusion_v1",
            "mode": self.mode.value,
            "total_evidence_items": len(self.evidence_store),
            "total_candidate_hypotheses": len(self.hypotheses),
            "multiple_plausible_candidates": len(plausible_vessels) > 1,
            "plausible_candidate_count": len(plausible_vessels),
            "candidate_spill_hypotheses": [h.to_dict() for h in spill_hyps],
            "candidate_vessel_hypotheses": [h.to_dict() for h in vessel_hyps],
            "evidence_ledger": [item.to_dict() for item in self.evidence_store.values()],
            "scientific_boundaries": [
                "Evidence Fusion establishes spatio-temporal compatibility, NOT legal attribution or responsibility.",
                "Absence of an AIS track in the candidate region does NOT prove no vessel was present.",
                "Multiple candidates may remain simultaneously plausible; Ocean Sentinel does not force a single winner.",
                "Evidence items sharing root observations are tracked as non-independent to prevent double-counting.",
                "Conflicting and contradictory evidence is preserved in the graph rather than erased.",
            ],
            "negative_proof_guard": "AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE",
        }

    def export_geojson(self) -> Dict[str, Any]:
        """Export spatial evidence items and candidate regions to RFC 7946 GeoJSON."""
        features: List[Dict[str, Any]] = []

        # 1. Add spatial evidence items
        for item in self.evidence_store.values():
            if item.spatial_geometry:
                features.append({
                    "type": "Feature",
                    "id": item.evidence_id,
                    "geometry": item.spatial_geometry,
                    "properties": {
                        "feature_type": "evidence_item",
                        "evidence_id": item.evidence_id,
                        "evidence_type": item.evidence_type,
                        "source_type": item.source_type,
                        "observation_time_utc": (
                            item.observation_time.isoformat()
                            if item.observation_time is not None
                            else None
                        ),
                        "provenance_class": item.provenance_class,
                        "observed_vs_inferred": item.observed_vs_inferred,
                        "metric_values": item.metric_values,
                    },
                })

        # 2. Add spatial candidate hypotheses
        for hyp in self.hypotheses.values():
            geom = getattr(hyp, "spatial_geometry", None)
            if geom:
                features.append({
                    "type": "Feature",
                    "id": hyp.hypothesis_id,
                    "geometry": geom,
                    "properties": {
                        "feature_type": "candidate_hypothesis",
                        "hypothesis_id": hyp.hypothesis_id,
                        "hypothesis_type": getattr(hyp, "hypothesis_type", "CANDIDATE_HYPOTHESIS"),
                        "overall_status": hyp.overall_status,
                        "independent_support_cluster_count": hyp.independent_support_cluster_count,
                        "summary": hyp.summary,
                    },
                })

        return {
            "type": "FeatureCollection",
            "name": "ocean_sentinel_evidence_fusion",
            "metadata": {
                "mode": self.mode.value,
                "feature_count": len(features),
                "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "negative_proof_guard": "AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE",
                "scientific_boundary": "EVIDENCE_COMPATIBILITY_ONLY_NO_LEGAL_ATTRIBUTION",
            },
            "features": features,
        }


# ---------------------------------------------------------------------------
# Optical & Auxiliary Observation Adapters
# ---------------------------------------------------------------------------


class OpticalObservationAdapter:
    """Base provider-neutral adapter contract for optical satellite observations."""

    def __init__(self, provider_id: str, is_accredited: bool = False, accreditation_key: Optional[str] = None) -> None:
        self.provider_id = str(provider_id)
        self._accredited = (
            bool(is_accredited) and (accreditation_key == _REPO_FUSION_ACCREDITATION_KEY)
        )

    def is_accredited(self) -> bool:
        return self._accredited

    def fetch_observations(
        self,
        bounding_box: Tuple[float, float, float, float],
        start_time: datetime,
        end_time: datetime,
    ) -> List[EvidenceItem]:
        raise NotImplementedError("Subclasses must implement fetch_observations")


class DeterministicDemoOpticalAdapter(OpticalObservationAdapter):
    """Deterministic DEMO fixture adapter generating optical observation evidence."""

    def __init__(self, provider_id: str = "DEMO_SYNTHETIC_OPTICAL_PROVIDER") -> None:
        super().__init__(provider_id=provider_id, is_accredited=False, accreditation_key=None)

    def fetch_observations(
        self,
        bounding_box: Tuple[float, float, float, float],
        start_time: datetime,
        end_time: datetime,
    ) -> List[EvidenceItem]:
        min_lon, min_lat, max_lon, max_lat = bounding_box
        c_lon = (min_lon + max_lon) / 2.0
        c_lat = (min_lat + max_lat) / 2.0
        t_obs = start_time + (end_time - start_time) / 2.0

        # Create optical scene observation footprint
        poly = Polygon([
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ])

        return [
            EvidenceItem(
                evidence_id="evidence_optical_demo_01",
                evidence_type=EvidenceType.OPTICAL_OBSERVATION,
                source_type=SourceType.OPTICAL_SATELLITE,
                source_id="DEMO_SENTINEL2_MSI_SCENE_01",
                observation_time=t_obs,
                spatial_geometry=poly,
                provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
                provenance_source="SYNTHETIC_DEMO_OPTICAL_FIXTURE",
                root_source_ids=["DEMO_SENTINEL2_MSI_SCENE_01"],
                derivation_type=DerivationType.SYNTHETIC_FIXTURE,
                observed_vs_inferred=ObservationStatus.OBSERVED,
                metric_values={"cloud_cover_percentage": 5.0, "optical_slick_detected": True},
                limitations=["Synthetic optical fixture for algorithmic demonstration only."],
            )
        ]


# ---------------------------------------------------------------------------
# Normalization Loaders from Frozen Artifacts
# ---------------------------------------------------------------------------


def load_evidence_from_detection_geojson(geojson_path: Path) -> List[EvidenceItem]:
    """Normalize SAR detection GeoJSON artifact into canonical EvidenceItems."""
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items: List[EvidenceItem] = []
    features = data.get("features", [])
    meta = data.get("metadata", {})

    for idx, feat in enumerate(features):
        fid = feat.get("id") or f"detection_{idx}"
        props = feat.get("properties", {})
        geom = feat.get("geometry")

        scene_id = props.get("source_scene") or meta.get("scene_id") or "unknown_sar_scene"
        t_str = props.get("observation_time_utc") or meta.get("observation_time_utc") or "2024-04-10T14:00:00+00:00"
        t_obs = datetime.fromisoformat(t_str.replace("Z", "+00:00"))

        item = EvidenceItem(
            evidence_id=f"evidence_sar_{fid}",
            evidence_type=EvidenceType.SAR_DETECTION,
            source_type=SourceType.SENTINEL_1_SAR,
            source_id=scene_id,
            observation_time=t_obs,
            spatial_geometry=geom,
            provenance_class=ProvenanceClass.HISTORICAL_ARCHIVE,
            provenance_source=f"scene_{scene_id}",
            source_artifact=str(geojson_path.name),
            root_source_ids=[f"scene_{scene_id}"],
            derivation_type=DerivationType.DIRECT_OBSERVATION,
            observed_vs_inferred=ObservationStatus.OBSERVED,
            metric_values={
                "area_m2": props.get("area_m2", 0.0),
                "pixel_count": props.get("pixel_count", 0),
                "mean_probability": props.get("mean_probability"),
            },
            limitations=["SAR detection sensitivity depends on sea surface wind speeds."],
        )
        items.append(item)
    return items


def load_evidence_from_temporal_geojson(geojson_path: Path) -> List[EvidenceItem]:
    """Normalize Temporal Change GeoJSON artifact into canonical EvidenceItems."""
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items: List[EvidenceItem] = []
    features = data.get("features", [])
    meta = data.get("metadata", {})

    t0_src = meta.get("t0_source", "scene_t0")
    t1_src = meta.get("t1_source", "scene_t1")

    for idx, feat in enumerate(features):
        fid = feat.get("id") or f"temporal_{idx}"
        props = feat.get("properties", {})
        geom = feat.get("geometry")

        event_type = props.get("event_type", "persistent")
        t_str = props.get("t1_time_utc") or meta.get("t1_time") or "2024-04-10T14:00:00+00:00"
        t_obs = datetime.fromisoformat(t_str.replace("Z", "+00:00"))

        # Root sources include both T0 and T1 scenes
        root_sources = [f"scene_{t0_src}", f"scene_{t1_src}"]

        item = EvidenceItem(
            evidence_id=f"evidence_temporal_{fid}",
            evidence_type=EvidenceType.TEMPORAL_CHANGE,
            source_type=SourceType.TEMPORAL_ANALYSIS,
            source_id=f"{t0_src}_to_{t1_src}_{event_type}",
            observation_time=t_obs,
            spatial_geometry=geom,
            provenance_class=ProvenanceClass.HISTORICAL_ARCHIVE,
            provenance_source=f"scenes_{t0_src}_{t1_src}",
            source_artifact=str(geojson_path.name),
            parent_evidence_ids=[f"evidence_sar_detection_{t0_src}", f"evidence_sar_detection_{t1_src}"],
            root_source_ids=root_sources,
            derivation_type=DerivationType.DERIVED_ANALYSIS,
            observed_vs_inferred=ObservationStatus.OBSERVED,
            metric_values={
                "event_type": event_type,
                "area_m2": props.get("area_m2", 0.0),
                "iou": props.get("iou", 1.0),
            },
            limitations=["Temporal change depends on external test timestamps if acquisition time unembedded."],
        )
        items.append(item)
    return items


def load_evidence_from_drift_geojson(geojson_path: Path) -> List[EvidenceItem]:
    """Normalize Origin & Drift GeoJSON artifact into canonical EvidenceItems."""
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items: List[EvidenceItem] = []
    features = data.get("features", [])
    meta = data.get("metadata", {})

    event_id = meta.get("event_id", "event_unknown")
    direction = meta.get("direction", "BACKWARD")
    mode_val = meta.get("mode", "DEMO")

    prov_class = (
        ProvenanceClass.VERIFIED_OPERATIONAL
        if mode_val == "PHYSICAL"
        else ProvenanceClass.SYNTHETIC_DEMO
    )

    for idx, feat in enumerate(features):
        fid = feat.get("id") or f"drift_{idx}"
        props = feat.get("properties", {})
        geom = feat.get("geometry")
        f_type = props.get("feature_type", "")

        t_str = props.get("observation_time_utc") or meta.get("observation_time_utc") or "2024-04-10T14:00:00+00:00"
        t_obs = datetime.fromisoformat(t_str.replace("Z", "+00:00"))

        if f_type == "candidate_origin_region":
            ev_type = EvidenceType.DRIFT_ORIGIN_HYPOTHESIS
            obs_stat = ObservationStatus.HYPOTHESIS
        else:
            ev_type = EvidenceType.DRIFT_TRAJECTORY
            obs_stat = ObservationStatus.INFERRED

        item = EvidenceItem(
            evidence_id=f"evidence_drift_{fid}",
            evidence_type=ev_type,
            source_type=SourceType.LAGRANGIAN_DRIFT_MODEL,
            source_id=f"drift_{event_id}_{direction.lower()}",
            observation_time=t_obs,
            spatial_geometry=geom,
            provenance_class=prov_class,
            provenance_source=f"drift_engine_{mode_val}",
            source_artifact=str(geojson_path.name),
            parent_evidence_ids=[f"evidence_temporal_{event_id}"],
            root_source_ids=[f"detection_{event_id}"],
            derivation_type=DerivationType.DERIVED_ANALYSIS,
            observed_vs_inferred=obs_stat,
            metric_values={
                "feature_type": f_type,
                "direction": direction,
                "duration_hours": props.get("duration_hours", 24.0),
                "area_m2": props.get("area_m2"),
            },
            limitations=[
                "Lagrangian trajectories represent candidate physical hypotheses, not confirmed historical drift.",
                "Surface windage factor is an empirical leeway heuristic.",
            ],
        )
        items.append(item)
    return items


# ---------------------------------------------------------------------------
# Multi-Source Deterministic DEMO Fixture Generator
# ---------------------------------------------------------------------------


def generate_deterministic_demo_fusion_fixture(
    base_lon: float = 30.65,
    base_lat: float = 32.14,
    base_time: Optional[datetime] = None,
) -> Tuple[List[EvidenceItem], Dict[str, Any]]:
    """Generate a rich, deterministic multi-source DEMO fixture.

    Contains:
    1. SAR detection (Sentinel-1).
    2. Temporal change (persistent slick, shared root source with SAR).
    3. Drift origin & trajectory hypotheses.
    4. Candidate Vessel A (Tanker: highly compatible, supports trajectory & origin).
    5. Candidate Vessel B (Supply: highly compatible, supports trajectory & origin -> Multiple Plausible Candidates).
    6. Candidate Vessel C (Glitch: intermediate trajectory support, conflicting terminal time).
    7. Candidate Vessel D (Tug: 52 km away, conflicting spatial evidence).
    8. Candidate Vessel E (Fishing: 8h telemetry gap, coverage unknown).
    9. Optical Observation 1 (Sentinel-2: slick thinning, consistent).
    10. Optical Observation 2 (Landsat: conflicting optical report in sector).
    """
    t0 = base_time or datetime(2024, 4, 10, 14, 0, 0, tzinfo=timezone.utc)
    t_start = t0 - timedelta(hours=24)

    # 1. SAR Detection
    sar_poly = Polygon([
        [base_lon - 0.02, base_lat - 0.02],
        [base_lon + 0.02, base_lat - 0.02],
        [base_lon + 0.02, base_lat + 0.02],
        [base_lon - 0.02, base_lat + 0.02],
        [base_lon - 0.02, base_lat - 0.02],
    ])
    e_sar = EvidenceItem(
        evidence_id="evidence_sar_scene_01339_det01",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="scene_01339",
        observation_time=t0,
        spatial_geometry=sar_poly,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="Copernicus_Sentinel_1_GRD",
        source_artifact="outputs/detections/01339_detections.geojson",
        root_source_ids=["SENTINEL1_SCENE_01339"],
        derivation_type=DerivationType.DIRECT_OBSERVATION,
        observed_vs_inferred=ObservationStatus.OBSERVED,
        metric_values={"area_m2": 3007776.0, "mean_probability": 0.88},
    )

    # 2. Temporal Change (Shares root source SENTINEL1_SCENE_01339)
    e_temporal = EvidenceItem(
        evidence_id="evidence_temporal_00007_01339_change01",
        evidence_type=EvidenceType.TEMPORAL_CHANGE,
        source_type=SourceType.TEMPORAL_ANALYSIS,
        source_id="temporal_00007_to_01339",
        observation_time=t0,
        spatial_geometry=sar_poly,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="OceanSentinel_TemporalChangeEngine",
        source_artifact="outputs/temporal/00007_to_01339_temporal_events.geojson",
        parent_evidence_ids=[e_sar.evidence_id],
        root_source_ids=["SENTINEL1_SCENE_00007", "SENTINEL1_SCENE_01339"],
        derivation_type=DerivationType.DERIVED_ANALYSIS,
        observed_vs_inferred=ObservationStatus.OBSERVED,
        metric_values={"event_type": "persistent", "area_m2": 3007776.0, "iou": 0.92},
    )

    # 3. Drift Origin Hypothesis (Integrated backward 24h)
    orig_poly = Polygon([
        [base_lon - 0.05, base_lat - 0.25],
        [base_lon - 0.12, base_lat - 0.15],
        [base_lon - 0.08, base_lat - 0.10],
        [base_lon + 0.01, base_lat - 0.18],
        [base_lon - 0.05, base_lat - 0.25],
    ])
    e_origin = EvidenceItem(
        evidence_id="evidence_drift_candidate_origin_01",
        evidence_type=EvidenceType.DRIFT_ORIGIN_HYPOTHESIS,
        source_type=SourceType.LAGRANGIAN_DRIFT_MODEL,
        source_id="drift_backward_24h",
        observation_time=t_start,
        spatial_geometry=orig_poly,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="OceanSentinel_OriginDriftEngine",
        source_artifact="outputs/origin_drift/trujillo_00007_01339.geojson",
        parent_evidence_ids=[e_temporal.evidence_id],
        root_source_ids=["SENTINEL1_SCENE_01339", "SYNTHETIC_METOCEAN_FIELD"],
        derivation_type=DerivationType.DERIVED_ANALYSIS,
        observed_vs_inferred=ObservationStatus.HYPOTHESIS,
        metric_values={"area_m2": 103274809.0, "duration_hours": 24.0, "direction": "BACKWARD"},
    )

    # 4. Drift Trajectory Envelope
    traj_line = LineString([
        [base_lon, base_lat],
        [base_lon - 0.03, base_lat - 0.10],
        [base_lon - 0.06, base_lat - 0.20],
    ])
    e_traj = EvidenceItem(
        evidence_id="evidence_drift_trajectory_envelope_01",
        evidence_type=EvidenceType.DRIFT_TRAJECTORY,
        source_type=SourceType.LAGRANGIAN_DRIFT_MODEL,
        source_id="drift_trajectories_ensemble",
        observation_time=t0,
        spatial_geometry=traj_line,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="OceanSentinel_OriginDriftEngine",
        source_artifact="outputs/origin_drift/trujillo_00007_01339.geojson",
        parent_evidence_ids=[e_temporal.evidence_id],
        root_source_ids=["SENTINEL1_SCENE_01339", "SYNTHETIC_METOCEAN_FIELD"],
        derivation_type=DerivationType.DERIVED_ANALYSIS,
        observed_vs_inferred=ObservationStatus.INFERRED,
        metric_values={"particle_count": 20, "timesteps": 48},
    )

    # 5. Optical Consistent Observation
    e_opt1 = EvidenceItem(
        evidence_id="evidence_optical_s2_consistent",
        evidence_type=EvidenceType.OPTICAL_OBSERVATION,
        source_type=SourceType.OPTICAL_SATELLITE,
        source_id="S2A_MSI_20240410_SCENE",
        observation_time=t0 + timedelta(hours=1),
        spatial_geometry=sar_poly,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="Synthetic_Sentinel2_Fixture",
        root_source_ids=["S2A_MSI_20240410_SCENE"],
        derivation_type=DerivationType.SYNTHETIC_FIXTURE,
        observed_vs_inferred=ObservationStatus.OBSERVED,
        metric_values={"optical_slick_confirmed": True, "sheen_thickness_um": 2.5},
    )

    # 6. Optical Conflicting Observation (clear water reported elsewhere)
    opt_conflict_poly = Polygon([
        [base_lon - 0.15, base_lat - 0.20],
        [base_lon - 0.10, base_lat - 0.20],
        [base_lon - 0.10, base_lat - 0.15],
        [base_lon - 0.15, base_lat - 0.15],
        [base_lon - 0.15, base_lat - 0.20],
    ])
    e_opt2 = EvidenceItem(
        evidence_id="evidence_optical_landsat_conflict",
        evidence_type=EvidenceType.OPTICAL_OBSERVATION,
        source_type=SourceType.OPTICAL_SATELLITE,
        source_id="LANDSAT_OLI_20240409_SCENE",
        observation_time=t_start + timedelta(hours=2),
        spatial_geometry=opt_conflict_poly,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="Synthetic_Landsat_Fixture",
        root_source_ids=["LANDSAT_OLI_20240409_SCENE"],
        derivation_type=DerivationType.SYNTHETIC_FIXTURE,
        observed_vs_inferred=ObservationStatus.OBSERVED,
        metric_values={"optical_slick_confirmed": False, "water_reflectance_anomaly": False},
        status="CONFLICT",
    )

    # AIS summary dictionary simulating 5 candidate vessels
    ais_summary = {
        "candidate_vessels": [
            {
                "mmsi": "368123450",
                "vessel_name": "MT_HORIZON_STAR",
                "vessel_type": "Crude Oil Tanker",
                "min_distance_to_origin_m": 1854.3,
                "min_distance_to_trajectory_m": 1321.9,
                "closest_approach_time_utc": t_start.isoformat(),
                "temporal_offset_hours": 0.0,
                "is_position_inferred": True,
                "inside_candidate_origin_region": True,
                "inside_trajectory_envelope": True,
                "coverage_status": "OBSERVED_IN_WINDOW",
                "evidence_compatibility_score": 0.8606,
                "provenance": "SYNTHETIC_DEMO_FEED",
            },
            {
                "mmsi": "368777880",
                "vessel_name": "GULF_SUPPLIER_VII",
                "vessel_type": "Offshore Supply",
                "min_distance_to_origin_m": 1492.0,
                "min_distance_to_trajectory_m": 1492.0,
                "closest_approach_time_utc": t_start.isoformat(),
                "temporal_offset_hours": 0.0,
                "is_position_inferred": True,
                "inside_candidate_origin_region": True,
                "inside_trajectory_envelope": True,
                "coverage_status": "OBSERVED_IN_WINDOW",
                "evidence_compatibility_score": 0.8351,
                "provenance": "SYNTHETIC_DEMO_FEED",
            },
            {
                "mmsi": "369555660",
                "vessel_name": "GLITCH_RUNNER",
                "vessel_type": "UNKNOWN",
                "min_distance_to_origin_m": 2029.0,
                "min_distance_to_trajectory_m": 1800.0,
                "closest_approach_time_utc": (t_start + timedelta(hours=14)).isoformat(),
                "temporal_offset_hours": 14.0,  # Temporal conflict with origin release window
                "is_position_inferred": True,
                "inside_candidate_origin_region": True,
                "inside_trajectory_envelope": True,
                "coverage_status": "OBSERVED_IN_WINDOW",
                "evidence_compatibility_score": 0.4461,
                "provenance": "SYNTHETIC_DEMO_FEED",
            },
            {
                "mmsi": "367111220",
                "vessel_name": "OCEAN_TUG_TITAN",
                "vessel_type": "Tug / Supply",
                "min_distance_to_origin_m": 51988.0,  # 52 km away -> spatial conflict
                "min_distance_to_trajectory_m": 51988.0,
                "closest_approach_time_utc": t_start.isoformat(),
                "temporal_offset_hours": 0.0,
                "is_position_inferred": False,
                "inside_candidate_origin_region": False,
                "inside_trajectory_envelope": False,
                "coverage_status": "OBSERVED_IN_WINDOW",
                "evidence_compatibility_score": 0.2937,
                "provenance": "SYNTHETIC_DEMO_FEED",
            },
            {
                "mmsi": "366333440",
                "vessel_name": "SEA_PROWLER",
                "vessel_type": "Fishing Vessel",
                "min_distance_to_origin_m": 8113.0,
                "min_distance_to_trajectory_m": 7500.0,
                "closest_approach_time_utc": (t_start + timedelta(hours=5)).isoformat(),
                "temporal_offset_hours": 5.0,
                "is_position_inferred": False,
                "inside_candidate_origin_region": False,
                "inside_trajectory_envelope": False,
                "coverage_status": "TELEMETRY_GAP_ACROSS_WINDOW",  # Coverage unknown / gap
                "evidence_compatibility_score": 0.2087,
                "provenance": "SYNTHETIC_DEMO_FEED",
                "data_limitations": ["Track has large 8.0h telemetry gap across candidate release window."],
            },
        ]
    }

    evidence_list = [e_sar, e_temporal, e_origin, e_traj, e_opt1, e_opt2]
    return evidence_list, ais_summary
