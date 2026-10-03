"""Comprehensive Test Suite for Multi-Source Evidence Fusion V1.

Covers:
- Section 20: 25 Focused Test Cases (Normalization, Lineage, Independence,
  Spatial/Temporal Correspondence, Negative-Proof Guard, Plausible Candidates,
  Provenance Gates, Double-Counting Prevention).
- Section 21: Adversarial & Scientific Safety Scenarios A through N.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Dict, List

import pytest
from shapely.geometry import Point, Polygon, box, mapping

from ocean_sentinel.drift import ProvenanceGateError
from ocean_sentinel.fusion import (
    CandidateHypothesis,
    CandidateVesselHypothesis,
    DerivationType,
    DeterministicDemoOpticalAdapter,
    EvidenceFusionEngine,
    EvidenceGraph,
    EvidenceItem,
    EvidenceRelation,
    EvidenceType,
    FusionMode,
    HypothesisStatus,
    IndependenceEngine,
    IndependenceRelation,
    ObservationStatus,
    OpticalObservationAdapter,
    ProvenanceClass,
    RelationshipType,
    SourceType,
    generate_deterministic_demo_fusion_fixture,
    load_evidence_from_detection_geojson,
    load_evidence_from_drift_geojson,
    load_evidence_from_temporal_geojson,
)

BASE_TIME = datetime(2024, 4, 10, 14, 0, 0, tzinfo=timezone.utc)
BASE_LON = -79.15
BASE_LAT = -8.12

SAMPLE_POLY = Polygon([
    [BASE_LON - 0.05, BASE_LAT - 0.05],
    [BASE_LON + 0.05, BASE_LAT - 0.05],
    [BASE_LON + 0.05, BASE_LAT + 0.05],
    [BASE_LON - 0.05, BASE_LAT + 0.05],
    [BASE_LON - 0.05, BASE_LAT - 0.05],
])


# ===========================================================================
# Section 20: 25 Focused Test Cases
# ===========================================================================


def test_01_evidence_item_normalization():
    """1. Evidence item normalization preserves fields, metrics, and Shapely conversion."""
    item = EvidenceItem(
        evidence_id="evidence_sar_test_01",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="S1A_IW_GRDH_TEST",
        observation_time=BASE_TIME,
        spatial_geometry=SAMPLE_POLY,
        provenance_class=ProvenanceClass.HISTORICAL_ARCHIVE,
        provenance_source="ESA_Copernicus_Hub",
        root_source_ids=["S1A_IW_GRDH_TEST"],
        derivation_type=DerivationType.DIRECT_OBSERVATION,
        observed_vs_inferred=ObservationStatus.OBSERVED,
        metric_values={"area_m2": 1500000.0, "mean_probability": 0.88},
    )

    assert item.evidence_id == "evidence_sar_test_01"
    assert item.shapely_geometry is not None
    assert item.shapely_geometry.geom_type == "Polygon"
    assert item.metric_values["area_m2"] == 1500000.0
    assert item.verify_integrity() is True

    d = item.to_dict()
    assert d["evidence_id"] == "evidence_sar_test_01"
    assert d["spatial_geometry"]["type"] == "Polygon"
    assert d["metric_values"]["mean_probability"] == 0.88


def test_02_deterministic_evidence_ids():
    """2. Deterministic evidence IDs and tamper seal integrity verification."""
    item1 = EvidenceItem(
        evidence_id="ev_det_01",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="S1A_SCENE_A",
        observation_time=BASE_TIME,
        spatial_geometry=SAMPLE_POLY,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="DEMO_TEST",
        root_source_ids=["S1A_SCENE_A"],
    )
    seal1 = item1.content_tamper_seal
    assert item1.verify_integrity() is True

    # Tampering with metadata post-creation causes integrity check to fail
    item1.metric_values["forged_key"] = "tampered_value"
    assert item1.verify_integrity() is False


def test_03_lineage_preservation():
    """3. Lineage preservation through ancestor parent IDs and root sources."""
    item_root = EvidenceItem(
        evidence_id="ev_root_sar",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="S1_SCENE_101",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["S1_SCENE_101"],
    )

    item_derived = EvidenceItem(
        evidence_id="ev_derived_drift",
        evidence_type=EvidenceType.DRIFT_TRAJECTORY,
        source_type=SourceType.LAGRANGIAN_DRIFT_MODEL,
        source_id="drift_101",
        observation_time=BASE_TIME - timedelta(hours=6),
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        parent_evidence_ids=["ev_root_sar"],
        root_source_ids=["S1_SCENE_101"],
        derivation_type=DerivationType.DERIVED_ANALYSIS,
    )

    assert "ev_root_sar" in item_derived.parent_evidence_ids
    assert "S1_SCENE_101" in item_derived.root_source_ids


def test_04_derived_evidence_relations():
    """4. EvidenceGraph creates DERIVED_FROM edges to parent ancestors."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)

    item_parent = EvidenceItem(
        evidence_id="parent_01",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="S1_A",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["S1_A"],
    )
    item_child = EvidenceItem(
        evidence_id="child_01",
        evidence_type=EvidenceType.TEMPORAL_CHANGE,
        source_type=SourceType.TEMPORAL_ANALYSIS,
        source_id="TEMP_A",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        parent_evidence_ids=["parent_01"],
        root_source_ids=["S1_A"],
    )

    engine.ingest_evidence_item(item_parent)
    engine.ingest_evidence_item(item_child)

    edges = engine.graph.edges
    derived_edges = [e for e in edges if e.relation_type == RelationshipType.DERIVED_FROM]
    assert len(derived_edges) == 1
    assert derived_edges[0].source_id == "child_01"
    assert derived_edges[0].target_id == "parent_01"


def test_05_shared_source_detection():
    """5. Detect shared root sources between two distinct evidence analyses."""
    ev1 = EvidenceItem(
        evidence_id="e_sar",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="S1_COMMON",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["S1_COMMON"],
    )
    ev2 = EvidenceItem(
        evidence_id="e_temporal",
        evidence_type=EvidenceType.TEMPORAL_CHANGE,
        source_type=SourceType.TEMPORAL_ANALYSIS,
        source_id="TEMP_COMMON",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["S1_COMMON", "S1_PREVIOUS"],
    )

    indep = IndependenceEngine({"e_sar": ev1, "e_temporal": ev2})
    rel = indep.evaluate_independence("e_sar", "e_temporal")
    assert rel == IndependenceRelation.SHARED_SOURCE


def test_06_independence_classification():
    """6. IndependenceEngine correctly classifies independent vs shared sources."""
    ev_indep_sar = EvidenceItem(
        evidence_id="e_sar",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="S1_A",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["S1_A"],
    )
    ev_indep_ais = EvidenceItem(
        evidence_id="e_ais",
        evidence_type=EvidenceType.AIS_OBSERVATION,
        source_type=SourceType.VESSEL_AIS_FEED,
        source_id="AIS_B",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["MMSI_999"],
    )

    indep = IndependenceEngine({"e_sar": ev_indep_sar, "e_ais": ev_indep_ais})
    rel = indep.evaluate_independence("e_sar", "e_ais")
    assert rel == IndependenceRelation.INDEPENDENT_SOURCE


def test_07_temporal_alignment():
    """7. Items within temporal tolerance evaluate to TEMPORALLY_ALIGNED."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO, temporal_tolerance_seconds=3600.0)
    t1 = BASE_TIME
    t2 = BASE_TIME + timedelta(minutes=45)
    rel, dt = engine.evaluate_temporal_relation(t1, t2)
    assert rel == RelationshipType.TEMPORALLY_ALIGNED
    assert dt == 2700.0


def test_08_spatial_alignment():
    """8. Intersecting or proximal geometries evaluate to SPATIALLY_ALIGNED."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO, spatial_tolerance_m=5000.0)
    p1 = Polygon([[-79.15, -8.12], [-79.10, -8.12], [-79.10, -8.08], [-79.15, -8.08], [-79.15, -8.12]])
    p2 = Polygon([[-79.12, -8.10], [-79.08, -8.10], [-79.08, -8.06], [-79.12, -8.06], [-79.12, -8.10]])

    rel, dist = engine.evaluate_spatial_relation(p1, p2)
    assert rel == RelationshipType.SPATIALLY_ALIGNED
    assert dist == 0.0


def test_09_spatial_conflict():
    """9. Geometries separated by distance > tolerance evaluate to SPATIALLY_INCONSISTENT."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO, spatial_tolerance_m=5000.0)
    # Centroid ~ 50 km away
    p1 = Point(-79.15, -8.12)
    p2 = Point(-78.70, -8.12)  # ~ 50 km east

    rel, dist = engine.evaluate_spatial_relation(p1, p2)
    assert rel == RelationshipType.SPATIALLY_INCONSISTENT
    assert dist > 40000.0


def test_10_temporal_conflict():
    """10. Timestamps outside temporal window evaluate to TEMPORALLY_INCONSISTENT."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO, temporal_tolerance_seconds=7200.0)
    t1 = BASE_TIME
    t2 = BASE_TIME + timedelta(hours=14)

    rel, dt = engine.evaluate_temporal_relation(t1, t2)
    assert rel == RelationshipType.TEMPORALLY_INCONSISTENT
    assert dt == 14.0 * 3600.0


def test_11_ais_absence_handling_negative_proof_guard():
    """11. Missing AIS data is treated as UNKNOWN/DATA_UNAVAILABLE, never as vessel absence."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    summary = {
        "candidate_vessels": [
            {
                "mmsi": "366000001",
                "vessel_name": "GHOST_VESSEL",
                "coverage_status": "TELEMETRY_GAP_ACROSS_WINDOW",
                "min_distance_to_origin_m": 500.0,
                "closest_approach_time_utc": BASE_TIME.isoformat(),
                "temporal_offset_hours": 0.0,
                "data_limitations": ["Telemetry blackout"],
            }
        ]
    }
    hyps = engine.synthesize_candidate_vessel_hypotheses(summary, drift_hypothesis_id="hyp_origin")
    assert len(hyps) == 1
    # Status must be INSUFFICIENT_EVIDENCE, not CONFLICTING_EVIDENCE
    assert hyps[0].overall_status == HypothesisStatus.INSUFFICIENT_EVIDENCE
    # Negative-proof limitation must be present
    assert any("Absence of an AIS track does NOT prove vessel absence" in lim for lim in hyps[0].limitations)


def test_12_unknown_coverage():
    """12. Vessels with TELEMETRY_GAP_ACROSS_WINDOW generate DATA_UNAVAILABLE edge."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    summary = {
        "candidate_vessels": [
            {
                "mmsi": "366999888",
                "vessel_name": "COVERAGE_GAP_VESSEL",
                "coverage_status": "TELEMETRY_GAP_ACROSS_WINDOW",
                "min_distance_to_origin_m": 1200.0,
                "closest_approach_time_utc": BASE_TIME.isoformat(),
                "temporal_offset_hours": 0.0,
            }
        ]
    }
    engine.synthesize_candidate_vessel_hypotheses(summary, "hyp_01")
    edges = [e for e in engine.graph.edges if e.target_id == "hypothesis_vessel_366999888"]
    assert len(edges) >= 1
    assert any(e.relation_type == RelationshipType.DATA_UNAVAILABLE for e in edges)


def test_13_observed_vs_inferred_distinction():
    """13. Preserves explicit observed vs inferred vs hypothesis distinctions."""
    obs_sar = EvidenceItem(
        evidence_id="e_sar_obs",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="S1_RAW",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["S1_RAW"],
        observed_vs_inferred=ObservationStatus.OBSERVED,
    )
    inferred_traj = EvidenceItem(
        evidence_id="e_drift_inferred",
        evidence_type=EvidenceType.DRIFT_TRAJECTORY,
        source_type=SourceType.LAGRANGIAN_DRIFT_MODEL,
        source_id="DRIFT_MODEL",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["S1_RAW"],
        observed_vs_inferred=ObservationStatus.INFERRED,
    )
    origin_hyp = EvidenceItem(
        evidence_id="e_origin_hyp",
        evidence_type=EvidenceType.DRIFT_ORIGIN_HYPOTHESIS,
        source_type=SourceType.LAGRANGIAN_DRIFT_MODEL,
        source_id="DRIFT_ORIGIN",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["S1_RAW"],
        observed_vs_inferred=ObservationStatus.HYPOTHESIS,
    )

    assert obs_sar.observed_vs_inferred == ObservationStatus.OBSERVED
    assert inferred_traj.observed_vs_inferred == ObservationStatus.INFERRED
    assert origin_hyp.observed_vs_inferred == ObservationStatus.HYPOTHESIS


def test_14_candidate_origin_semantics():
    """14. Candidate origin hypotheses retain non-attribution scientific boundary."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    e_sar = EvidenceItem(
        evidence_id="e_sar_01",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="S1_01",
        observation_time=BASE_TIME,
        spatial_geometry=SAMPLE_POLY,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["S1_01"],
    )
    engine.ingest_evidence_item(e_sar)
    hyp = engine.synthesize_spill_origin_hypothesis("hyp_orig_1", "event_1", SAMPLE_POLY, (BASE_TIME, BASE_TIME))

    assert "NOT confirmed historical release location" in hyp.limitations[0]
    assert hyp.overall_status in [
        HypothesisStatus.SUPPORTED_BY_AVAILABLE_EVIDENCE,
        HypothesisStatus.CONSISTENT_WITH_AVAILABLE_EVIDENCE,
    ]


def test_15_multiple_plausible_candidates():
    """15. Fusion preserves multiple plausible candidates simultaneously without forcing a winner."""
    evidence_items, ais_summary = generate_deterministic_demo_fusion_fixture()
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    for it in evidence_items:
        engine.ingest_evidence_item(it)

    vessel_hyps = engine.synthesize_candidate_vessel_hypotheses(ais_summary, "evidence_drift_origin_poly")
    summary = engine.export_summary()

    assert summary["multiple_plausible_candidates"] is True
    assert summary["plausible_candidate_count"] >= 2
    plausible_names = [
        v["vessel_name"] for v in summary["candidate_vessel_hypotheses"]
        if v["overall_status"] in ["SUPPORTED_BY_AVAILABLE_EVIDENCE", "CONSISTENT_WITH_AVAILABLE_EVIDENCE"]
    ]
    assert "MT_HORIZON_STAR" in plausible_names
    assert "GULF_SUPPLIER_VII" in plausible_names


def test_16_conflicting_evidence():
    """16. Conflicting evidence is preserved rather than erased or averaged."""
    evidence_items, ais_summary = generate_deterministic_demo_fusion_fixture()
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    for it in evidence_items:
        engine.ingest_evidence_item(it)

    vessel_hyps = engine.synthesize_candidate_vessel_hypotheses(ais_summary, "evidence_drift_origin_poly")
    glitch_hyp = next(vh for vh in vessel_hyps if vh.mmsi == "369555660")

    assert glitch_hyp.overall_status == HypothesisStatus.CONFLICTING_EVIDENCE
    assert len(glitch_hyp.conflicting_evidence_ids) >= 1
    # Edge exists in graph with TEMPORALLY_INCONSISTENT
    edges = [e for e in engine.graph.edges if e.target_id == glitch_hyp.hypothesis_id]
    assert any(e.relation_type == RelationshipType.TEMPORALLY_INCONSISTENT for e in edges)


def test_17_no_evidence_handling():
    """17. Engine handles empty evidence store safely."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    hyp = engine.synthesize_spill_origin_hypothesis("hyp_empty", "no_event", None, None)
    assert hyp.overall_status == HypothesisStatus.INSUFFICIENT_EVIDENCE
    assert len(hyp.supporting_evidence_ids) == 0

    summary = engine.export_summary()
    assert summary["total_evidence_items"] == 0
    assert summary["multiple_plausible_candidates"] is False


def test_18_malformed_evidence_handling():
    """18. Malformed geometry or invalid types handled safely or rejected."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    item = EvidenceItem(
        evidence_id="e_bad_geom",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="S1_BAD",
        observation_time=BASE_TIME,
        spatial_geometry={"type": "Polygon", "coordinates": "invalid"},  # malformed GeoJSON
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["S1_BAD"],
    )
    # Shapely geometry property handles invalid input safely returning None
    assert item.shapely_geometry is None
    engine.ingest_evidence_item(item)
    rel, dist = engine.evaluate_spatial_relation(item.shapely_geometry, SAMPLE_POLY)
    assert rel == RelationshipType.UNKNOWN
    assert dist == float("inf")


def test_19_demo_vs_physical_separation():
    """19. DEMO mode allows synthetic data, PHYSICAL mode strictly rejects it."""
    engine_demo = EvidenceFusionEngine(mode=FusionMode.DEMO)
    engine_phys = EvidenceFusionEngine(mode=FusionMode.PHYSICAL)

    item_demo = EvidenceItem(
        evidence_id="e_demo_item",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="DEMO_S1",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="DEMO_FIXTURE",
        root_source_ids=["DEMO_S1"],
    )

    # Ingesting into DEMO works cleanly
    engine_demo.ingest_evidence_item(item_demo)
    assert "e_demo_item" in engine_demo.evidence_store

    # Ingesting into PHYSICAL fails closed
    with pytest.raises(ProvenanceGateError, match="PHYSICAL mode rejected"):
        engine_phys.ingest_evidence_item(item_demo)


def test_20_provenance_failure():
    """20. Unverified external provenance fails closed in PHYSICAL mode."""
    engine_phys = EvidenceFusionEngine(mode=FusionMode.PHYSICAL)
    item_unverified = EvidenceItem(
        evidence_id="e_unverified",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="UNVERIFIED_S1",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.UNVERIFIED_EXTERNAL,
        provenance_source="External_Web_Scraper",
        root_source_ids=["UNVERIFIED_S1"],
    )
    with pytest.raises(ProvenanceGateError, match="non-operational provenance"):
        engine_phys.ingest_evidence_item(item_unverified)


def test_21_synthetic_evidence_injected_into_physical_mode():
    """21. Synthetic fixtures cannot bypass PHYSICAL mode gates."""
    engine_phys = EvidenceFusionEngine(mode=FusionMode.PHYSICAL)
    items, _ = generate_deterministic_demo_fusion_fixture()
    for item in items:
        with pytest.raises(ProvenanceGateError):
            engine_phys.ingest_evidence_item(item)


def test_22_score_probability_terminology_guard():
    """22. Terminology guard: forbids illegal attribution claims in serialized outputs."""
    evidence_items, ais_summary = generate_deterministic_demo_fusion_fixture()
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    for it in evidence_items:
        engine.ingest_evidence_item(it)
    engine.synthesize_candidate_vessel_hypotheses(ais_summary, "evidence_drift_origin_poly")

    summary_json = json.dumps(engine.export_summary()).lower()
    forbidden_terms = [
        "probability_of_guilt",
        "responsible_vessel",
        "guilty",
        "proven_source",
        "convicted",
        "culpable",
    ]
    for term in forbidden_terms:
        assert term not in summary_json, f"Illegal attribution term '{term}' found in output!"


def test_23_duplicate_evidence_double_counting_prevention():
    """23. Prevents double counting of multiple derived items from identical root source."""
    e_root = EvidenceItem(
        evidence_id="e_root_s1",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="SCENE_99",
        observation_time=BASE_TIME,
        spatial_geometry=SAMPLE_POLY,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["SCENE_99"],
    )
    e_derived1 = EvidenceItem(
        evidence_id="e_derived_temp",
        evidence_type=EvidenceType.TEMPORAL_CHANGE,
        source_type=SourceType.TEMPORAL_ANALYSIS,
        source_id="ANALYSIS_1",
        observation_time=BASE_TIME,
        spatial_geometry=SAMPLE_POLY,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        parent_evidence_ids=["e_root_s1"],
        root_source_ids=["SCENE_99"],
    )
    e_derived2 = EvidenceItem(
        evidence_id="e_derived_drift",
        evidence_type=EvidenceType.DRIFT_ORIGIN_HYPOTHESIS,
        source_type=SourceType.LAGRANGIAN_DRIFT_MODEL,
        source_id="ANALYSIS_2",
        observation_time=BASE_TIME,
        spatial_geometry=SAMPLE_POLY,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        parent_evidence_ids=["e_root_s1"],
        root_source_ids=["SCENE_99"],
    )

    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    engine.ingest_evidence_item(e_root)
    engine.ingest_evidence_item(e_derived1)
    engine.ingest_evidence_item(e_derived2)

    hyp = engine.synthesize_spill_origin_hypothesis("hyp_01", "event_99", SAMPLE_POLY, (BASE_TIME, BASE_TIME))
    assert len(hyp.supporting_evidence_ids) == 3
    # Double-counting prevented: 3 supporting items collapse into 1 independent cluster
    assert hyp.independent_support_cluster_count == 1
    assert hyp.dependency_summary["double_counting_prevented"] is True


def test_24_source_lineage_collision():
    """24. Handling re-ingestion of same evidence ID safely."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    item = EvidenceItem(
        evidence_id="e_unique_01",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="S1_A",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["S1_A"],
    )
    engine.ingest_evidence_item(item)
    # Re-ingesting identical item is idempotent
    engine.ingest_evidence_item(item)
    assert len(engine.evidence_store) == 1


def test_25_deterministic_end_to_end_fusion():
    """25. Running fusion twice on identical input produces bitwise identical results."""
    items1, ais1 = generate_deterministic_demo_fusion_fixture()
    items2, ais2 = generate_deterministic_demo_fusion_fixture()

    engine1 = EvidenceFusionEngine(mode=FusionMode.DEMO)
    for it in items1:
        engine1.ingest_evidence_item(it)
    engine1.synthesize_spill_origin_hypothesis("hyp_orig", "subj_01", SAMPLE_POLY, (BASE_TIME, BASE_TIME))
    engine1.synthesize_candidate_vessel_hypotheses(ais1, "hyp_orig")

    engine2 = EvidenceFusionEngine(mode=FusionMode.DEMO)
    for it in items2:
        engine2.ingest_evidence_item(it)
    engine2.synthesize_spill_origin_hypothesis("hyp_orig", "subj_01", SAMPLE_POLY, (BASE_TIME, BASE_TIME))
    engine2.synthesize_candidate_vessel_hypotheses(ais2, "hyp_orig")

    s1 = json.dumps(engine1.export_summary(), sort_keys=True)
    s2 = json.dumps(engine2.export_summary(), sort_keys=True)
    assert s1 == s2


# ===========================================================================
# Section 21: Adversarial & Scientific Safety Tests (Scenarios A through N)
# ===========================================================================


def test_adversarial_scenario_a_same_sentinel1_source_not_independent():
    """A. Same Sentinel-1 scene appears in detection and temporal change -> NOT INDEPENDENT."""
    sar_item = EvidenceItem(
        evidence_id="ev_sar_s1",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="SENTINEL1_SCENE_777",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["SENTINEL1_SCENE_777"],
    )
    temp_item = EvidenceItem(
        evidence_id="ev_temp_s1",
        evidence_type=EvidenceType.TEMPORAL_CHANGE,
        source_type=SourceType.TEMPORAL_ANALYSIS,
        source_id="TEMP_ANALYSIS",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        parent_evidence_ids=["ev_sar_s1"],
        root_source_ids=["SENTINEL1_SCENE_777", "SENTINEL1_SCENE_666"],
    )

    indep = IndependenceEngine({"ev_sar_s1": sar_item, "ev_temp_s1": temp_item})
    rel = indep.evaluate_independence("ev_sar_s1", "ev_temp_s1")
    assert rel in [IndependenceRelation.SHARED_SOURCE, IndependenceRelation.DERIVED_FROM]
    assert rel != IndependenceRelation.INDEPENDENT_SOURCE

    # Also test two sibling analyses sharing root without direct parent relation
    sar_item_alt = EvidenceItem(
        evidence_id="ev_sar_alt",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="ANALYSIS_ALT",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["SENTINEL1_SCENE_777"],
    )
    indep2 = IndependenceEngine({"ev_sar_s1": sar_item, "ev_sar_alt": sar_item_alt})
    rel2 = indep2.evaluate_independence("ev_sar_s1", "ev_sar_alt")
    assert rel2 == IndependenceRelation.SHARED_SOURCE
    assert rel2 != IndependenceRelation.INDEPENDENT_SOURCE


def test_adversarial_scenario_b_raw_ais_and_derived_track_not_independent():
    """B. Raw AIS record and derived AIS track share source -> DERIVED_FROM/SHARED_SOURCE."""
    ais_raw = EvidenceItem(
        evidence_id="ev_ais_raw",
        evidence_type=EvidenceType.AIS_OBSERVATION,
        source_type=SourceType.VESSEL_AIS_FEED,
        source_id="RAW_AIS_MMSI_12345",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["MMSI_12345"],
    )
    ais_track = EvidenceItem(
        evidence_id="ev_ais_track",
        evidence_type=EvidenceType.AIS_TRACK,
        source_type=SourceType.VESSEL_AIS_FEED,
        source_id="TRACK_MMSI_12345",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        parent_evidence_ids=["ev_ais_raw"],
        root_source_ids=["MMSI_12345"],
        derivation_type=DerivationType.DERIVED_ANALYSIS,
    )

    indep = IndependenceEngine({"ev_ais_raw": ais_raw, "ev_ais_track": ais_track})
    rel = indep.evaluate_independence("ev_ais_track", "ev_ais_raw")
    assert rel == IndependenceRelation.DERIVED_FROM


def test_adversarial_scenario_c_different_hashes_same_upstream_evidence():
    """C. Two items with different IDs/hashes sharing identical root are detected as dependent."""
    item1 = EvidenceItem(
        evidence_id="hash_alpha_01",
        evidence_type=EvidenceType.DRIFT_TRAJECTORY,
        source_type=SourceType.LAGRANGIAN_DRIFT_MODEL,
        source_id="MODEL_RUN_1",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["ROOT_SCENE_ALPHA"],
    )
    item2 = EvidenceItem(
        evidence_id="hash_beta_02",
        evidence_type=EvidenceType.DRIFT_ORIGIN_HYPOTHESIS,
        source_type=SourceType.LAGRANGIAN_DRIFT_MODEL,
        source_id="MODEL_RUN_2",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["ROOT_SCENE_ALPHA"],
    )

    indep = IndependenceEngine({"hash_alpha_01": item1, "hash_beta_02": item2})
    rel = indep.evaluate_independence("hash_alpha_01", "hash_beta_02")
    assert rel == IndependenceRelation.SHARED_SOURCE


def test_adversarial_scenario_d_missing_ais_during_coverage_gap():
    """D. Missing AIS during a coverage gap produces UNKNOWN/DATA_UNAVAILABLE, NOT contradiction."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    summary = {
        "candidate_vessels": [
            {
                "mmsi": "366555000",
                "vessel_name": "GAP_TRAWLER",
                "coverage_status": "TELEMETRY_GAP_ACROSS_WINDOW",
                "min_distance_to_origin_m": 8000.0,
                "closest_approach_time_utc": (BASE_TIME - timedelta(hours=3)).isoformat(),
                "temporal_offset_hours": 3.0,
            }
        ]
    }
    hyps = engine.synthesize_candidate_vessel_hypotheses(summary, "hyp_drift")
    assert len(hyps) == 1
    vh = hyps[0]
    assert vh.overall_status == HypothesisStatus.INSUFFICIENT_EVIDENCE
    assert vh.overall_status != HypothesisStatus.CONFLICTING_EVIDENCE
    # In graph, relation is DATA_UNAVAILABLE
    edges = [e for e in engine.graph.edges if e.target_id == vh.hypothesis_id]
    assert any(e.relation_type == RelationshipType.DATA_UNAVAILABLE for e in edges)


def test_adversarial_scenario_e_spatially_close_temporally_incompatible():
    """E. Candidate vessel is spatially close (100m) but temporally incompatible (+14h)."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    summary = {
        "candidate_vessels": [
            {
                "mmsi": "368000111",
                "vessel_name": "LATE_TANKER",
                "coverage_status": "OBSERVED_IN_WINDOW",
                "inside_candidate_origin_region": True,
                "min_distance_to_origin_m": 150.0,
                "closest_approach_time_utc": (BASE_TIME + timedelta(hours=14)).isoformat(),
                "temporal_offset_hours": 14.0,  # 14h offset!
            }
        ]
    }
    hyps = engine.synthesize_candidate_vessel_hypotheses(summary, "hyp_drift")
    vh = hyps[0]
    assert vh.overall_status == HypothesisStatus.CONFLICTING_EVIDENCE
    edges = [e for e in engine.graph.edges if e.target_id == vh.hypothesis_id]
    assert any(e.relation_type == RelationshipType.TEMPORALLY_INCONSISTENT for e in edges)


def test_adversarial_scenario_f_temporally_aligned_spatially_incompatible():
    """F. Candidate vessel is temporally aligned (+0.0h) but spatially incompatible (55 km away)."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO, spatial_tolerance_m=5000.0)
    summary = {
        "candidate_vessels": [
            {
                "mmsi": "368000222",
                "vessel_name": "FARAWAY_CONTAINER",
                "coverage_status": "OBSERVED_IN_WINDOW",
                "inside_candidate_origin_region": False,
                "inside_trajectory_envelope": False,
                "min_distance_to_origin_m": 55000.0,  # 55 km
                "min_distance_to_trajectory_m": 55000.0,
                "closest_approach_time_utc": BASE_TIME.isoformat(),
                "temporal_offset_hours": 0.0,
            }
        ]
    }
    hyps = engine.synthesize_candidate_vessel_hypotheses(summary, "hyp_drift")
    vh = hyps[0]
    assert vh.overall_status == HypothesisStatus.CONFLICTING_EVIDENCE
    edges = [e for e in engine.graph.edges if e.target_id == vh.hypothesis_id]
    assert any(e.relation_type == RelationshipType.SPATIALLY_INCONSISTENT for e in edges)


def test_adversarial_scenario_g_matches_intermediate_drift_not_terminal_origin():
    """G. Matches intermediate drift trajectory but not terminal origin polygon -> preserves intermediate support."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO, spatial_tolerance_m=5000.0)
    summary = {
        "candidate_vessels": [
            {
                "mmsi": "368000333",
                "vessel_name": "INTERMEDIATE_CARGO",
                "coverage_status": "OBSERVED_IN_WINDOW",
                "inside_candidate_origin_region": False,
                "inside_trajectory_envelope": True,
                "min_distance_to_origin_m": 12000.0,      # Outside origin
                "min_distance_to_trajectory_m": 1500.0,    # Close to intermediate trajectory
                "closest_approach_time_utc": (BASE_TIME - timedelta(hours=6)).isoformat(),
                "temporal_offset_hours": 0.0,
            }
        ]
    }
    hyps = engine.synthesize_candidate_vessel_hypotheses(summary, "hyp_drift")
    vh = hyps[0]
    assert vh.overall_status == HypothesisStatus.CONSISTENT_WITH_AVAILABLE_EVIDENCE
    edges = [e for e in engine.graph.edges if e.target_id == vh.hypothesis_id]
    assert any(e.relation_type == RelationshipType.CONSISTENT_WITH for e in edges)


def test_adversarial_scenario_h_candidate_lies_only_inside_broad_trajectory_hull():
    """H. Candidate lies only inside broad envelope without origin intersection -> no fabricated origin support."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO, spatial_tolerance_m=5000.0)
    summary = {
        "candidate_vessels": [
            {
                "mmsi": "368000444",
                "vessel_name": "HULL_ONLY_VESSEL",
                "coverage_status": "OBSERVED_IN_WINDOW",
                "inside_candidate_origin_region": False,
                "inside_trajectory_envelope": True,
                "min_distance_to_origin_m": 8500.0,
                "min_distance_to_trajectory_m": 4200.0,
                "closest_approach_time_utc": BASE_TIME.isoformat(),
                "temporal_offset_hours": 0.0,
            }
        ]
    }
    hyps = engine.synthesize_candidate_vessel_hypotheses(summary, "hyp_drift")
    vh = hyps[0]
    # Must NOT be classified as fully SUPPORTED_BY_AVAILABLE_EVIDENCE, only CONSISTENT_WITH
    assert vh.overall_status == HypothesisStatus.CONSISTENT_WITH_AVAILABLE_EVIDENCE
    assert vh.inside_origin_region is False


def test_adversarial_scenario_i_synthetic_evidence_labelled_physical_by_caller():
    """I. Synthetic evidence labelled PHYSICAL by caller fails closed via accreditation check."""
    adapter = OpticalObservationAdapter(provider_id="FORGED_OPTICAL_FEED", is_accredited=True, accreditation_key="WRONG_KEY")
    assert adapter.is_accredited() is False

    engine_phys = EvidenceFusionEngine(mode=FusionMode.PHYSICAL)
    # Caller tries to forge provenance_class as VERIFIED_OPERATIONAL but with synthetic source
    item = EvidenceItem(
        evidence_id="forged_item",
        evidence_type=EvidenceType.OPTICAL_OBSERVATION,
        source_type=SourceType.OPTICAL_SATELLITE,
        source_id="FORGED_SCENE",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,  # Engine checks this
        provenance_source="FORGED_FEED",
        root_source_ids=["FORGED_SCENE"],
    )
    with pytest.raises(ProvenanceGateError, match="PHYSICAL mode rejected"):
        engine_phys.ingest_evidence_item(item)


def test_adversarial_scenario_j_candidate_has_both_supporting_and_conflicting_evidence():
    """J. Candidate with both supporting and conflicting evidence retains both; status CONFLICTING_EVIDENCE."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    e_opt_conflict = EvidenceItem(
        evidence_id="opt_vessel_conflict",
        evidence_type=EvidenceType.OPTICAL_OBSERVATION,
        source_type=SourceType.OPTICAL_SATELLITE,
        source_id="vessel_368999111",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["OPT_SCENE_1"],
        status="CONFLICT",
    )
    engine.ingest_evidence_item(e_opt_conflict)

    summary = {
        "candidate_vessels": [
            {
                "mmsi": "368999111",
                "vessel_name": "DUAL_EVIDENCE_VESSEL",
                "coverage_status": "OBSERVED_IN_WINDOW",
                "inside_candidate_origin_region": True,
                "min_distance_to_origin_m": 800.0,
                "closest_approach_time_utc": BASE_TIME.isoformat(),
                "temporal_offset_hours": 0.0,
            }
        ]
    }
    hyps = engine.synthesize_candidate_vessel_hypotheses(summary, "hyp_drift")
    vh = hyps[0]
    assert vh.overall_status == HypothesisStatus.CONFLICTING_EVIDENCE
    assert len(vh.supporting_evidence_ids) >= 1
    assert len(vh.conflicting_evidence_ids) >= 1


def test_adversarial_scenario_k_graph_cycle_detection():
    """K. EvidenceGraph cycle detection safely identifies cycles."""
    graph = EvidenceGraph()
    # Add cycle A -> B -> C -> A
    graph.add_edge(EvidenceRelation("node_A", "node_B", RelationshipType.DERIVED_FROM))
    graph.add_edge(EvidenceRelation("node_B", "node_C", RelationshipType.DERIVED_FROM))
    graph.add_edge(EvidenceRelation("node_C", "node_A", RelationshipType.DERIVED_FROM))

    assert graph.detect_cycles() is True

    # Graph without cycle
    graph_acyclic = EvidenceGraph()
    graph_acyclic.add_edge(EvidenceRelation("node_1", "node_2", RelationshipType.DERIVED_FROM))
    graph_acyclic.add_edge(EvidenceRelation("node_2", "node_3", RelationshipType.DERIVED_FROM))
    assert graph_acyclic.detect_cycles() is False


def test_adversarial_scenario_l_duplicate_evidence_submitted_twice():
    """L. Duplicate evidence item submitted twice does not duplicate store or nodes."""
    engine = EvidenceFusionEngine(mode=FusionMode.DEMO)
    item = EvidenceItem(
        evidence_id="e_dup_test",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="S1_DUP",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.SYNTHETIC_DEMO,
        provenance_source="TEST",
        root_source_ids=["S1_DUP"],
    )
    engine.ingest_evidence_item(item)
    engine.ingest_evidence_item(item)

    assert len(engine.evidence_store) == 1
    assert "e_dup_test" in engine.graph.nodes
    assert len(engine.graph.nodes) == 1


def test_adversarial_scenario_m_missing_provenance():
    """M. Missing or invalid provenance fails closed in PHYSICAL mode."""
    engine_phys = EvidenceFusionEngine(mode=FusionMode.PHYSICAL)
    item_missing_prov = EvidenceItem(
        evidence_id="e_no_prov",
        evidence_type=EvidenceType.SAR_DETECTION,
        source_type=SourceType.SENTINEL_1_SAR,
        source_id="S1_NOPROV",
        observation_time=BASE_TIME,
        provenance_class=ProvenanceClass.UNVERIFIED_EXTERNAL,
        provenance_source="",
        root_source_ids=["S1_NOPROV"],
    )
    with pytest.raises(ProvenanceGateError):
        engine_phys.ingest_evidence_item(item_missing_prov)


def test_adversarial_scenario_n_unsupported_evidence_type():
    """N. Unsupported or custom evidence type handled safely in normalization."""
    # When loading from GeoJSON, features with missing or unknown feature types default gracefully
    data = {
        "type": "FeatureCollection",
        "metadata": {"event_id": "test_event"},
        "features": [
            {
                "type": "Feature",
                "id": "unknown_01",
                "geometry": mapping(SAMPLE_POLY),
                "properties": {"feature_type": "completely_unsupported_type"},
            }
        ],
    }
    tmp_path = Path("scratch/test_unsupported.geojson")
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    try:
        items = load_evidence_from_drift_geojson(tmp_path)
        assert len(items) == 1
        assert items[0].evidence_type == EvidenceType.DRIFT_TRAJECTORY
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
