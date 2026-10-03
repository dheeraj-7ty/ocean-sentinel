"""Explicit Scientific Directed Acyclic Graph (DAG) Engine (Phase 7A).

Provides typed dependency graph structures, topological sorting, dependency
validation, cycle rejection, and scientific execution gating enforcement.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from ocean_sentinel.orchestration.investigation_context import AuthorizationState
from ocean_sentinel.orchestration.investigation_run import StageRetryPolicy

logger = logging.getLogger(__name__)


class DAGValidationError(Exception):
    """Raised when DAG structure contains cycles or invalid dependencies."""


@dataclass
class DAGNode:
    """A single typed node within the scientific execution DAG."""

    id: str
    version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)
    retry_policy: StageRetryPolicy = field(default_factory=StageRetryPolicy)
    deterministic: bool = True
    parallelizable: bool = False
    is_scientific_gated: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "dependencies": self.dependencies,
            "retry_policy": self.retry_policy.to_dict(),
            "deterministic": self.deterministic,
            "parallelizable": self.parallelizable,
            "is_scientific_gated": self.is_scientific_gated,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DAGNode:
        rp = StageRetryPolicy.from_dict(data.get("retry_policy", {}))
        return cls(
            id=data["id"],
            version=data.get("version", "1.0.0"),
            dependencies=list(data.get("dependencies", [])),
            retry_policy=rp,
            deterministic=bool(data.get("deterministic", True)),
            parallelizable=bool(data.get("parallelizable", False)),
            is_scientific_gated=bool(data.get("is_scientific_gated", False)),
            description=data.get("description", ""),
        )


class ScientificDAG:
    """Explicit Directed Acyclic Graph defining stage dependencies and gating."""

    def __init__(self, graph_id: str = "canonical_scientific_dag_v1") -> None:
        self.graph_id = graph_id
        self.nodes: Dict[str, DAGNode] = {}

    def add_node(self, node: DAGNode) -> None:
        """Register a node into the graph."""
        self.nodes[node.id] = node

    def validate(self) -> None:
        """Validate DAG integrity: all dependencies exist and no cycles exist."""
        # 1. Dependency existence check
        for node_id, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise DAGValidationError(
                        f"Stage '{node_id}' depends on undefined stage '{dep}'"
                    )
                if dep == node_id:
                    raise DAGValidationError(
                        f"Stage '{node_id}' cannot depend on itself"
                    )

        # 2. Cycle detection via Kahn's algorithm
        in_degree: Dict[str, int] = {k: 0 for k in self.nodes}
        adj: Dict[str, List[str]] = {k: [] for k in self.nodes}

        for node_id, node in self.nodes.items():
            in_degree[node_id] = len(node.dependencies)
            for dep in node.dependencies:
                adj[dep].append(node_id)

        queue = deque([k for k, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if visited_count != len(self.nodes):
            raise DAGValidationError(
                f"Cyclic dependency detected in graph '{self.graph_id}'! "
                f"Visited {visited_count}/{len(self.nodes)} nodes."
            )

    def get_topological_order(self) -> List[str]:
        """Compute deterministic topological execution order.

        Prioritizes un-gated operational stages before scientific-gated stages
        so all permissible data preparation and analytical branches execute
        before halting fail-closed at the scientific boundary.
        """
        self.validate()

        in_degree: Dict[str, int] = {k: len(v.dependencies) for k, v in self.nodes.items()}
        adj: Dict[str, List[str]] = {k: [] for k in self.nodes}

        for node_id, node in self.nodes.items():
            for dep in node.dependencies:
                adj[dep].append(node_id)

        def sort_key(k: str) -> Tuple[bool, str]:
            return (self.nodes[k].is_scientific_gated, k)

        ready_nodes = sorted([k for k, deg in in_degree.items() if deg == 0], key=sort_key)
        order: List[str] = []

        while ready_nodes:
            curr = ready_nodes.pop(0)
            order.append(curr)
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    ready_nodes.append(nxt)
            ready_nodes.sort(key=sort_key)

        return order

    def get_ready_stages(self, completed_stages: Set[str]) -> List[str]:
        """Return list of stages whose dependencies are all satisfied and not yet completed."""
        ready: List[str] = []
        for node_id in self.get_topological_order():
            if node_id in completed_stages:
                continue
            node = self.nodes[node_id]
            if all(dep in completed_stages for dep in node.dependencies):
                ready.append(node_id)
        return ready

    def can_execute_stage(
        self,
        stage_id: str,
        completed_stages: Set[str],
        auth_state: Optional[AuthorizationState] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate if a stage is eligible for immediate execution."""
        if stage_id not in self.nodes:
            return False, f"Stage '{stage_id}' is not in graph '{self.graph_id}'"

        node = self.nodes[stage_id]

        # 1. Dependency check
        unmet = [dep for dep in node.dependencies if dep not in completed_stages]
        if unmet:
            return False, f"Unmet dependencies for '{stage_id}': {unmet}"

        # 2. Scientific safety gate check
        if node.is_scientific_gated:
            auth = auth_state or AuthorizationState()
            if not auth.SCIENTIFIC_EXECUTION_AUTHORIZED:
                return False, (
                    f"Stage '{stage_id}' is scientific-gated and "
                    f"SCIENTIFIC_EXECUTION_AUTHORIZED is False (fail-closed)."
                )

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ScientificDAG:
        dag = cls(graph_id=data.get("graph_id", "canonical_scientific_dag_v1"))
        for k, v in data.get("nodes", {}).items():
            dag.add_node(DAGNode.from_dict(v))
        return dag


# ---------------------------------------------------------------------------
# Canonical DAG Factory
# ---------------------------------------------------------------------------


def create_canonical_scientific_dag(graph_id: str = "canonical_scientific_dag_v1") -> ScientificDAG:
    """Factory creating the canonical 10-stage Ocean Sentinel scientific DAG.

    Stages:
    1. VALIDATE: Spatio-temporal and parameter checks (Root)
    2. INGEST: CDSE discovery & raster materialization (Depends on: VALIDATE)
    3. PREPROCESS: Radiometric normalization & SAR channel contract (Depends on: INGEST)
    4. INFER: Model forward pass (Depends on: PREPROCESS) [SCIENTIFIC_GATED]
    5. INTERPRET: Confidence thresholding & slick candidate extraction (Depends on: INFER) [SCIENTIFIC_GATED]
    6. TEMPORAL: Multi-temporal pair analysis (Depends on: PREPROCESS)
    7. DRIFT: Lagrangian particle trajectory modeling (Depends on: VALIDATE)
    8. AIS: Historical vessel trajectory correlation (Depends on: VALIDATE)
    9. FUSION: Multi-source hypothesis synthesis (Depends on: DRIFT, AIS, TEMPORAL)
    10. EXPORT: Investigation evidence packaging (Depends on: FUSION)
    """
    dag = ScientificDAG(graph_id=graph_id)

    dag.add_node(
        DAGNode(
            id="VALIDATE",
            version="1.0.0",
            dependencies=[],
            retry_policy=StageRetryPolicy(max_retries=2, backoff_seconds=1.0, is_safe_retry=True),
            deterministic=True,
            parallelizable=False,
            is_scientific_gated=False,
            description="AOI polygon, datetime window, and request parameter validation",
        )
    )

    dag.add_node(
        DAGNode(
            id="INGEST",
            version="1.0.0",
            dependencies=["VALIDATE"],
            retry_policy=StageRetryPolicy(max_retries=2, backoff_seconds=2.0, is_safe_retry=True),
            deterministic=True,
            parallelizable=False,
            is_scientific_gated=False,
            description="Copernicus CDSE STAC discovery and authenticated Process API retrieval",
        )
    )

    dag.add_node(
        DAGNode(
            id="PREPROCESS",
            version="1.0.0",
            dependencies=["INGEST"],
            retry_policy=StageRetryPolicy(max_retries=1, backoff_seconds=1.0, is_safe_retry=True),
            deterministic=True,
            parallelizable=False,
            is_scientific_gated=False,
            description="Dual-polarization channel contract (Ch0=VH, Ch1=VV) and radiometric checks",
        )
    )

    dag.add_node(
        DAGNode(
            id="INFER",
            version="1.0.0",
            dependencies=["PREPROCESS"],
            retry_policy=StageRetryPolicy(max_retries=0, is_safe_retry=False),
            deterministic=True,
            parallelizable=False,
            is_scientific_gated=True,
            description="Neural network forward pass on canonical checkpoint (STRICTLY GATED)",
        )
    )

    dag.add_node(
        DAGNode(
            id="INTERPRET",
            version="1.0.0",
            dependencies=["INFER"],
            retry_policy=StageRetryPolicy(max_retries=0, is_safe_retry=False),
            deterministic=True,
            parallelizable=False,
            is_scientific_gated=True,
            description="Confidence contouring and slick candidate polygonization (STRICTLY GATED)",
        )
    )

    dag.add_node(
        DAGNode(
            id="TEMPORAL",
            version="1.0.0",
            dependencies=["PREPROCESS"],
            retry_policy=StageRetryPolicy(max_retries=1, backoff_seconds=1.0, is_safe_retry=True),
            deterministic=True,
            parallelizable=True,
            is_scientific_gated=False,
            description="Multi-temporal SAR difference geometry and feature persistence tracking",
        )
    )

    dag.add_node(
        DAGNode(
            id="DRIFT",
            version="1.0.0",
            dependencies=["VALIDATE"],
            retry_policy=StageRetryPolicy(max_retries=1, backoff_seconds=1.0, is_safe_retry=True),
            deterministic=True,
            parallelizable=True,
            is_scientific_gated=False,
            description="Lagrangian backward/forward trajectory modeling under metocean forcing",
        )
    )

    dag.add_node(
        DAGNode(
            id="AIS",
            version="1.0.0",
            dependencies=["VALIDATE"],
            retry_policy=StageRetryPolicy(max_retries=2, backoff_seconds=1.0, is_safe_retry=True),
            deterministic=True,
            parallelizable=True,
            is_scientific_gated=False,
            description="Historical AIS vessel track interpolation and spatial encounter evaluation",
        )
    )

    dag.add_node(
        DAGNode(
            id="FUSION",
            version="1.0.0",
            dependencies=["DRIFT", "AIS", "TEMPORAL"],
            retry_policy=StageRetryPolicy(max_retries=1, backoff_seconds=1.0, is_safe_retry=True),
            deterministic=True,
            parallelizable=False,
            is_scientific_gated=False,
            description="Multi-source correlation scoring (AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE)",
        )
    )

    dag.add_node(
        DAGNode(
            id="EXPORT",
            version="1.0.0",
            dependencies=["FUSION"],
            retry_policy=StageRetryPolicy(max_retries=1, backoff_seconds=1.0, is_safe_retry=True),
            deterministic=True,
            parallelizable=False,
            is_scientific_gated=False,
            description="Investigation manifest, structured evidence object, and artifact export",
        )
    )

    dag.validate()
    return dag
