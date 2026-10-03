"""Registered Real Repository Investigation Scenarios for Ocean Sentinel V1.

Provides authentic, verified repository scenario definitions based on real
Sentinel-1 SAR imagery and scientific pipeline artifacts without inventing
unverified metadata.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


@dataclass
class InvestigationScenario:
    """Canonical descriptor for a registered real repository investigation scenario."""

    scenario_id: str
    label: str
    dataset: str
    scene_pair: List[str]
    region: str
    centroid: List[float]  # [longitude, latitude]
    event_id: str
    artifacts: Dict[str, str]
    acquisition_timestamps: Dict[str, str]
    satellite_product_id: str = "METADATA UNAVAILABLE"
    vessel_truth: str = "METADATA UNAVAILABLE"
    physical_incident_label: str = "METADATA UNAVAILABLE"
    unverified_source_metadata: str = "METADATA UNAVAILABLE"
    provenance_class: str = "REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY"
    provenance_status: str = "PROVENANCE_LIMITED"
    has_synthetic_dependencies: bool = True
    source_pair_status: str = "VALID_CANDIDATE"
    temporal_status: str = "PENDING"
    reason: Optional[str] = None
    lineage_status: str = "CURRENT"
    stage_provenance: Dict[str, str] = field(default_factory=lambda: {
        "satellite": "HISTORICAL_ARCHIVE",
        "temporal": "HISTORICAL_ARCHIVE",
        "drift": "SYNTHETIC_DEMO",
        "ais": "SYNTHETIC_DEMO",
    })
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert scenario to dictionary."""
        return asdict(self)

    def validate_artifacts_exist(self, base_dir: Optional[Path] = None) -> List[str]:
        """Check that all registered artifact files actually exist on disk.
        
        Returns a list of missing relative paths, or empty list if all exist.
        """
        root = base_dir or REPO_ROOT
        missing = []
        for key, rel_path in self.artifacts.items():
            full_path = root / rel_path
            if not full_path.is_file():
                missing.append(f"{key}: {rel_path}")
        return missing


# ---------------------------------------------------------------------------
# Registered Scenarios Catalog
# ---------------------------------------------------------------------------

_SCENARIO_CATALOG: Dict[str, InvestigationScenario] = {
    "TRUJILLO_00007_01339": InvestigationScenario(
        scenario_id="TRUJILLO_00007_01339",
        label="Trujillo 2024 S1 Scene Pair 00007 / 01339 (Eastern Mediterranean)",
        dataset="Trujillo et al., 2024 Sentinel-1 SAR Oil Spill Dataset",
        scene_pair=["00007", "01339"],
        region="Eastern Mediterranean (Offshore Nile Delta)",
        centroid=[30.652577, 32.137832],
        event_id="00007_01339_persistent_0003",
        artifacts={
            "detection_mask_t0": "outputs/inference/00007_mask.tif",
            "detection_mask_t1": "outputs/inference/01339_mask.tif",
            "temporal_geojson": "outputs/temporal/00007_to_01339_temporal_events.geojson",
            "drift_geojson": "outputs/origin_drift/trujillo_00007_01339.geojson",
            "ais_summary": "outputs/ais/trujillo_00007_01339_summary.json",
            "ais_geojson": "outputs/ais/trujillo_00007_01339.geojson",
        },
        acquisition_timestamps={
            "t0": "2024-04-05T14:00:00+00:00 (EXTERNALLY_SUPPLIED_TEST_TIMESTAMP)",
            "t1": "2024-04-10T14:00:00+00:00 (EXTERNALLY_SUPPLIED_TEST_TIMESTAMP)",
        },
        satellite_product_id="METADATA UNAVAILABLE",
        vessel_truth="METADATA UNAVAILABLE",
        physical_incident_label="METADATA UNAVAILABLE",
        unverified_source_metadata="METADATA UNAVAILABLE",
        provenance_class="REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY",
        provenance_status="PROVENANCE_LIMITED",
        has_synthetic_dependencies=True,
        source_pair_status="INVALID_DUPLICATE_IMAGE_PAIR",
        temporal_status="BLOCKED",
        reason="IDENTICAL_SOURCE_RASTERS",
        lineage_status="LEGACY_INVALID_TEMPORAL_PAIR",
        stage_provenance={
            "satellite": "HISTORICAL_ARCHIVE",
            "temporal": "BLOCKED",
            "drift": "SYNTHETIC_DEMO",
            "ais": "SYNTHETIC_DEMO",
        },
        limitations=[
            "CRITICAL DEFECT: 00007.tif and 01339.tif are byte-for-byte identical source rasters; differing annotation masks represent annotation/label divergence whose cause is NOT established by this evidence. Mask differences MUST NOT be interpreted as physical SAR change.",
            "Scenario source_pair_status is INVALID_DUPLICATE_IMAGE_PAIR; temporal physical-change reasoning is BLOCKED (reason: IDENTICAL_SOURCE_RASTERS).",
            "Downstream historical artifacts derived from this pair are marked LEGACY_INVALID_TEMPORAL_PAIR and cannot enter historical attribution reasoning.",
            "Data originates from Trujillo et al. (2024) repository baseline; physical external feeds remain unavailable.",
            "Scenario contains downstream drift and AIS artifacts generated with synthetic forcing and DEMO feeds (SYNTHETIC_DEMO); they are NOT historical metocean observations or physical vessel tracks.",
            "Overall scenario provenance is classified as REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY and cannot claim pure HISTORICAL_ARCHIVE.",
            "Candidate vessels reflect spatio-temporal compatibility hypotheses only; NO legal responsibility or causal guilt is established.",
            "Absence of AIS signals does NOT prove vessel absence (AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE).",
            "Acquisition timestamps are test conventions as exact Sentinel-1 header metadata is not embedded in dataset.",
        ],
    ),
    "TRUJILLO_00260_00608": InvestigationScenario(
        scenario_id="TRUJILLO_00260_00608",
        label="Trujillo 2024 S1 Scene Pair 00260 / 00608 (Gulf of Mexico)",
        dataset="Trujillo et al., 2024 Sentinel-1 SAR Oil Spill Dataset",
        scene_pair=["00260", "00608"],
        region="Gulf of Mexico (Deepwater offshore)",
        centroid=[-90.386402, 27.0864],
        event_id="00260_00608_new_0010",
        artifacts={
            "detection_mask_t0": "outputs/inference/00260_mask.tif",
            "detection_mask_t1": "outputs/inference/00608_mask.tif",
            "temporal_geojson": "outputs/temporal/00260_to_00608_temporal_events.geojson",
            "drift_geojson": "outputs/drift/00260_00608_new_0010_backward_drift.geojson",
            "ais_summary": "outputs/ais/00260_00608_new_0010_ais_correlation_summary.json",
            "ais_geojson": "outputs/ais/00260_00608_new_0010_ais_correlation.geojson",
        },
        acquisition_timestamps={
            "t0": "2024-05-01T00:00:00+00:00 (EXTERNALLY_SUPPLIED_TEST_TIMESTAMP)",
            "t1": "2024-05-13T00:00:00+00:00 (EXTERNALLY_SUPPLIED_TEST_TIMESTAMP)",
        },
        satellite_product_id="METADATA UNAVAILABLE",
        vessel_truth="METADATA UNAVAILABLE",
        physical_incident_label="METADATA UNAVAILABLE",
        unverified_source_metadata="METADATA UNAVAILABLE",
        provenance_class="REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY",
        provenance_status="PROVENANCE_LIMITED",
        has_synthetic_dependencies=True,
        source_pair_status="POTENTIAL_TEMPORAL_PAIR",
        temporal_status="BLOCKED_AWAITING_AUTHORITATIVE_TIMESTAMPS",
        reason="TEMPORAL_ORDER_UNKNOWN",
        lineage_status="CURRENT",
        stage_provenance={
            "satellite": "HISTORICAL_ARCHIVE",
            "temporal": "BLOCKED",
            "drift": "SYNTHETIC_DEMO",
            "ais": "SYNTHETIC_DEMO",
        },
        limitations=[
            "Candidate image pair is non-identical but temporal order is TEMPORAL_ORDER_UNKNOWN; filename/archive order CANNOT establish chronology.",
            "Data originates from Trujillo et al. (2024) repository baseline; physical external feeds remain unavailable.",
            "Scenario contains downstream drift and AIS artifacts generated with synthetic forcing and DEMO feeds (SYNTHETIC_DEMO); they are NOT historical metocean observations or physical vessel tracks.",
            "Overall scenario provenance is classified as REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY and cannot claim pure HISTORICAL_ARCHIVE.",
            "Candidate vessels reflect spatio-temporal compatibility hypotheses only; NO legal responsibility or causal guilt is established.",
            "Absence of AIS signals does NOT prove vessel absence (AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE).",
            "Acquisition timestamps are test conventions as exact Sentinel-1 header metadata is not embedded in dataset.",
        ],
    ),
}


def get_scenario(scenario_id: str) -> Optional[InvestigationScenario]:
    """Lookup a registered investigation scenario by ID."""
    return _SCENARIO_CATALOG.get(scenario_id)


def list_scenarios() -> List[InvestigationScenario]:
    """Return all registered investigation scenarios."""
    return list(_SCENARIO_CATALOG.values())
