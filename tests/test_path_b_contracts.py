"""Contract Tests for Ocean Sentinel Path B Architecture Foundation.

Verifies the 10 contract requirements:
1. proposal -> region interface is valid
2. proposal does not equal confirmed detection
3. provenance survives stage transitions
4. execution mode/scenario context survives stage transitions
5. missing required provenance fails closed
6. multiple candidate vessels remain representable
7. DEMO/PHYSICAL separation remains enforced
8. downstream stages do not fabricate timestamps or confidence
9. an EXP-06-specific implementation can be replaced without changing downstream contracts
10. existing critical regression suites remain green
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from ocean_sentinel.contracts.path_b import (
    AISCompatibilityEvidence,
    CandidateProposal,
    CandidateProposalProtocol,
    CandidateRegion,
    EXP06CandidateProposalAdapter,
    EvidenceStatus,
    ExecutionMode,
    FusionEvidence,
    LineageRecord,
    LookalikeAssessment,
    LookalikeSuppressionAction,
    LookalikeSuppressionCategory,
    PathBContractError,
    ProvenanceGateViolationError,
    ReplaceableCandidateProposalEngine,
    ScientificBoundaryViolationError,
    TemporalConsistencyStatus,
    TemporalEvidence,
    assess_lookalikes,
    correlate_ais_candidates,
    extract_candidate_regions,
    fuse_path_b_evidence,
    reason_temporal_repeat_pass,
)
from ocean_sentinel.temporal import ChangeCategory, TimestampProvenance


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------


def make_valid_demo_proposal(
    scene_id: str = "S1A_IW_GRDH_1SDV_20260901_TEST",
    scenario_id: str = "SCENARIO_TRUJILLO_01",
) -> CandidateProposal:
    adapter = EXP06CandidateProposalAdapter()
    return adapter.propose(
        scene_identifier=scene_id,
        execution_mode=ExecutionMode.DEMO,
        scenario_id=scenario_id,
        acquisition_timestamp_utc=datetime(2026, 9, 1, 10, 30, 0, tzinfo=timezone.utc),
        timestamp_provenance=TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA,
        grid_crs="EPSG:4326",
        is_synthetic=True,
    )


def sample_feature_dict() -> dict:
    return {
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-79.15, -8.15],
                    [-79.10, -8.15],
                    [-79.10, -8.10],
                    [-79.15, -8.10],
                    [-79.15, -8.15],
                ]
            ],
        },
        "geometry_crs": "EPSG:4326",
        "bbox": (-79.15, -8.15, -79.10, -8.10),
        "centroid": (-79.125, -8.125),
        "pixel_count": 450,
        "area_m2": 3125000.0,
        "area_crs": "EPSG:32717",
        "morphology_metrics": {
            "perimeter_m": 8500.0,
            "elongation_ratio": 3.2,
        },
        "score_statistics": {
            "mean": 0.68,
            "max": 0.89,
            "min": 0.23,
            "std": 0.14,
        },
    }


# ---------------------------------------------------------------------------
# Test 1: proposal -> region interface is valid
# ---------------------------------------------------------------------------


def test_proposal_to_region_interface_is_valid() -> None:
    proposal = make_valid_demo_proposal()
    features = [sample_feature_dict()]

    regions = extract_candidate_regions(proposal, features)

    assert len(regions) == 1
    region = regions[0]
    assert isinstance(region, CandidateRegion)
    assert region.parent_proposal_id == proposal.proposal_id
    assert region.source_scene_id == proposal.source_scene_id
    assert region.pixel_count == 450
    assert region.area_m2 == 3125000.0
    assert region.centroid == (-79.125, -8.125)
    assert region.bbox == (-79.15, -8.15, -79.10, -8.10)
    assert region.evidence_status == EvidenceStatus.PROPOSED
    assert region.geometry_geojson["type"] == "Polygon"

    # Test conversion to canonical EvidenceItem
    ev_item = region.to_evidence_item()
    assert ev_item.evidence_id.startswith("ev_region_")
    assert ev_item.source_id == proposal.source_scene_id
    assert "UNVERIFIED_CANDIDATE_PROPOSAL" in ev_item.limitations


# ---------------------------------------------------------------------------
# Test 2: proposal does not equal confirmed detection
# ---------------------------------------------------------------------------


def test_proposal_does_not_equal_confirmed_detection() -> None:
    proposal = make_valid_demo_proposal()

    # Invariant: status is candidate proposal, not confirmed detection
    assert proposal.evidence_status == EvidenceStatus.UNVERIFIED_CANDIDATE
    assert "NON-CONFIRMED CANDIDATE PROPOSAL" in proposal.scientific_disclaimer

    region = extract_candidate_regions(proposal, [sample_feature_dict()])[0]
    assert region.evidence_status == EvidenceStatus.PROPOSED
    assert "Does not constitute confirmed oil detection" in region.scientific_disclaimer

    # Invariant: Lookalike assessment cannot claim physical identity proof
    with pytest.raises(ScientificBoundaryViolationError):
        LookalikeAssessment(
            assessment_id="eval_01",
            parent_region_id=region.region_id,
            execution_mode=ExecutionMode.DEMO,
            suppression_category=LookalikeSuppressionCategory.LOW_WIND_AREA,
            suppression_action=LookalikeSuppressionAction.FLAGGED_SUSPECT_LOOKALIKE,
            assessment_rationale="Low wind test",
            lineage=region.lineage,
            is_confirmed_physical_identity=True,  # VIOLATION
        )

    # Invariant: Temporal reasoning cannot claim causality
    with pytest.raises(ScientificBoundaryViolationError):
        TemporalEvidence(
            temporal_evidence_id="temp_01",
            parent_region_id=region.region_id,
            execution_mode=ExecutionMode.DEMO,
            t1_scene_id="SCENE_01",
            temporal_status=TemporalConsistencyStatus.PERSISTENT_FEATURE,
            lineage=region.lineage,
            causality_inferred=True,  # VIOLATION
        )

    # Invariant: AIS correlation cannot claim proven attribution
    with pytest.raises(ScientificBoundaryViolationError):
        AISCompatibilityEvidence(
            correlation_evidence_id="ais_01",
            parent_region_id=region.region_id,
            execution_mode=ExecutionMode.DEMO,
            candidate_vessels=[],
            lineage=region.lineage,
            is_attribution_proven=True,  # VIOLATION
        )

    # Invariant: AIS absence cannot claim proof of vessel absence
    with pytest.raises(ScientificBoundaryViolationError):
        AISCompatibilityEvidence(
            correlation_evidence_id="ais_02",
            parent_region_id=region.region_id,
            execution_mode=ExecutionMode.DEMO,
            candidate_vessels=[],
            lineage=region.lineage,
            ais_absence_proves_vessel_absence=True,  # VIOLATION
        )

    # Invariant: Fusion cannot claim adjudicated attribution proof
    with pytest.raises(ScientificBoundaryViolationError):
        FusionEvidence(
            fusion_evidence_id="fusion_01",
            execution_mode=ExecutionMode.DEMO,
            candidate_region_ids=[region.region_id],
            synthesized_hypotheses=[],
            uncertainty_state={},
            lineage=region.lineage,
            attribution_adjudicated=True,  # VIOLATION
        )


# ---------------------------------------------------------------------------
# Test 3: provenance survives stage transitions
# ---------------------------------------------------------------------------


def test_provenance_survives_stage_transitions() -> None:
    proposal = make_valid_demo_proposal()
    assert proposal.lineage.lineage_sha256 != ""

    regions = extract_candidate_regions(proposal, [sample_feature_dict()])
    region = regions[0]
    # Region must cite proposal's hash
    assert proposal.lineage.lineage_sha256 in region.lineage.parent_hashes

    lookalike = assess_lookalikes(region, contextual_factors={"wind_speed_mps": 2.1})
    assert region.lineage.lineage_sha256 in lookalike.lineage.parent_hashes

    temporal = reason_temporal_repeat_pass(
        region,
        prior_scene_id="S1A_PRIOR_SCENE",
        prior_timestamp_utc=datetime(2026, 8, 20, 10, 30, 0, tzinfo=timezone.utc),
        prior_timestamp_provenance=TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA,
        overlap_iou=0.45,
    )
    assert region.lineage.lineage_sha256 in temporal.lineage.parent_hashes

    ais = correlate_ais_candidates(
        region,
        candidate_vessels=[{"mmsi": "123456789", "evidence_compatibility_score": 0.72}],
    )
    assert region.lineage.lineage_sha256 in ais.lineage.parent_hashes

    fusion = fuse_path_b_evidence(
        region,
        lookalike,
        temporal,
        ais,
        synthesized_hypotheses=[{"hypothesis_id": "hyp_01", "mmsi": "123456789"}],
    )
    # Fusion cites all contributing stages
    assert region.lineage.lineage_sha256 in fusion.lineage.parent_hashes
    assert lookalike.lineage.lineage_sha256 in fusion.lineage.parent_hashes
    assert temporal.lineage.lineage_sha256 in fusion.lineage.parent_hashes
    assert ais.lineage.lineage_sha256 in fusion.lineage.parent_hashes


# ---------------------------------------------------------------------------
# Test 4: execution mode/scenario context survives stage transitions
# ---------------------------------------------------------------------------


def test_execution_mode_and_scenario_context_survive_stage_transitions() -> None:
    expected_mode = ExecutionMode.DEMO
    expected_scenario = "TRUJILLO_00007_01339"

    adapter = EXP06CandidateProposalAdapter()
    proposal = adapter.propose(
        scene_identifier="S1A_TEST_SCENE",
        execution_mode=expected_mode,
        scenario_id=expected_scenario,
        acquisition_timestamp_utc=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
        timestamp_provenance=TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA,
        is_synthetic=True,
    )

    region = extract_candidate_regions(proposal, [sample_feature_dict()])[0]
    lookalike = assess_lookalikes(region)
    temporal = reason_temporal_repeat_pass(region)
    ais = correlate_ais_candidates(region, candidate_vessels=[])
    fusion = fuse_path_b_evidence(region, lookalike, temporal, ais)

    for stage_obj in [proposal, region, lookalike, temporal, ais, fusion]:
        assert stage_obj.execution_mode == expected_mode
        assert stage_obj.scenario_id == expected_scenario
        assert stage_obj.lineage.execution_mode == expected_mode
        assert stage_obj.lineage.scenario_id == expected_scenario


# ---------------------------------------------------------------------------
# Test 5: missing required provenance fails closed
# ---------------------------------------------------------------------------


def test_missing_required_provenance_fails_closed() -> None:
    adapter = EXP06CandidateProposalAdapter()

    # Case 1: PHYSICAL mode rejects synthetic data
    with pytest.raises(ProvenanceGateViolationError, match="Synthetic demo lineage detected"):
        adapter.propose(
            scene_identifier="S1A_PHYSICAL_SCENE",
            execution_mode=ExecutionMode.PHYSICAL,
            acquisition_timestamp_utc=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
            timestamp_provenance=TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA,
            is_synthetic=True,  # VIOLATION for PHYSICAL
        )

    # Case 2: PHYSICAL mode rejects missing acquisition timestamp
    with pytest.raises(ProvenanceGateViolationError, match="Acquisition timestamp missing"):
        adapter.propose(
            scene_identifier="S1A_PHYSICAL_SCENE",
            execution_mode=ExecutionMode.PHYSICAL,
            acquisition_timestamp_utc=None,  # VIOLATION
            timestamp_provenance=TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA,
            is_synthetic=False,
        )

    # Case 3: PHYSICAL mode rejects unverified/test timestamps
    with pytest.raises(ProvenanceGateViolationError, match="Invalid timestamp provenance"):
        adapter.propose(
            scene_identifier="S1A_PHYSICAL_SCENE",
            execution_mode=ExecutionMode.PHYSICAL,
            acquisition_timestamp_utc=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
            timestamp_provenance=TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP,  # VIOLATION
            is_synthetic=False,
        )


# ---------------------------------------------------------------------------
# Test 6: multiple candidate vessels remain representable
# ---------------------------------------------------------------------------


def test_multiple_candidate_vessels_remain_representable() -> None:
    proposal = make_valid_demo_proposal()
    region = extract_candidate_regions(proposal, [sample_feature_dict()])[0]

    vessels = [
        {"mmsi": "111111111", "vessel_name": "VESSEL_ALPHA", "evidence_compatibility_score": 0.81},
        {"mmsi": "222222222", "vessel_name": "VESSEL_BETA", "evidence_compatibility_score": 0.74},
        {"mmsi": "333333333", "vessel_name": "VESSEL_GAMMA", "evidence_compatibility_score": 0.69},
    ]

    ais = correlate_ais_candidates(region, candidate_vessels=vessels)
    assert ais.candidate_count == 3
    assert [v["mmsi"] for v in ais.candidate_vessels] == ["111111111", "222222222", "333333333"]

    lookalike = assess_lookalikes(region)
    temporal = reason_temporal_repeat_pass(region)

    # Invariant: Fusion cannot force a single winner when multiple candidates exist
    with pytest.raises(ScientificBoundaryViolationError, match="single-winner hypothesis selection is prohibited"):
        FusionEvidence(
            fusion_evidence_id="fusion_mult_01",
            execution_mode=ExecutionMode.DEMO,
            candidate_region_ids=[region.region_id],
            synthesized_hypotheses=[
                {"hypothesis_id": "hyp_01", "mmsi": "111111111"},
                {"hypothesis_id": "hyp_02", "mmsi": "222222222"},
            ],
            uncertainty_state={"multiple_plausible_origins_retained": True},
            lineage=region.lineage,
            single_winner_forced=True,  # VIOLATION
        )

    # Valid fusion preserves all multiple candidates
    fusion = fuse_path_b_evidence(
        region,
        lookalike,
        temporal,
        ais,
        synthesized_hypotheses=[
            {"hypothesis_id": "hyp_01", "mmsi": "111111111"},
            {"hypothesis_id": "hyp_02", "mmsi": "222222222"},
            {"hypothesis_id": "hyp_03", "mmsi": "333333333"},
        ],
    )
    assert len(fusion.synthesized_hypotheses) == 3
    assert fusion.has_unresolved_uncertainty is True
    assert fusion.single_winner_forced is False


# ---------------------------------------------------------------------------
# Test 7: DEMO/PHYSICAL separation remains enforced
# ---------------------------------------------------------------------------


def test_demo_and_physical_separation_remains_enforced() -> None:
    adapter = EXP06CandidateProposalAdapter()

    # DEMO mode accommodates synthetic data
    demo_prop = adapter.propose(
        scene_identifier="S1A_DEMO_SCENE",
        execution_mode=ExecutionMode.DEMO,
        acquisition_timestamp_utc=None,
        timestamp_provenance=TimestampProvenance.UNKNOWN,
        is_synthetic=True,
    )
    assert demo_prop.execution_mode == ExecutionMode.DEMO
    assert demo_prop.lineage.is_synthetic is True

    # PHYSICAL mode rejects synthetic data with explicit error
    with pytest.raises(ProvenanceGateViolationError):
        adapter.propose(
            scene_identifier="S1A_DEMO_SCENE",
            execution_mode=ExecutionMode.PHYSICAL,
            acquisition_timestamp_utc=None,
            timestamp_provenance=TimestampProvenance.UNKNOWN,
            is_synthetic=True,
        )


# ---------------------------------------------------------------------------
# Test 8: downstream stages do not fabricate timestamps or confidence
# ---------------------------------------------------------------------------


def test_downstream_stages_do_not_fabricate_timestamps_or_confidence() -> None:
    adapter = EXP06CandidateProposalAdapter()
    # Create proposal with NO timestamp
    proposal = adapter.propose(
        scene_identifier="S1A_NOTIME_SCENE",
        execution_mode=ExecutionMode.DEMO,
        acquisition_timestamp_utc=None,
        timestamp_provenance=TimestampProvenance.UNKNOWN,
        is_synthetic=True,
    )
    assert proposal.acquisition_timestamp_utc is None

    # Extraction must preserve None timestamp; it must NOT fabricate a default timestamp
    regions = extract_candidate_regions(proposal, [sample_feature_dict()])
    region = regions[0]
    assert region.acquisition_timestamp_utc is None
    assert region.timestamp_provenance == TimestampProvenance.UNKNOWN

    lookalike = assess_lookalikes(region)
    temporal = reason_temporal_repeat_pass(region)
    ais = correlate_ais_candidates(region, candidate_vessels=[])
    fusion = fuse_path_b_evidence(region, lookalike, temporal, ais)

    # Ensure no fabricated global scalar confidence exists
    fusion_dict = fusion.to_dict()
    assert "global_confidence" not in fusion_dict
    assert "attribution_probability" not in fusion_dict
    assert fusion.has_unresolved_uncertainty is True


# ---------------------------------------------------------------------------
# Test 9: EXP-06 replaceable without changing downstream contracts
# ---------------------------------------------------------------------------


def test_exp06_replaceable_without_changing_downstream_contracts() -> None:
    # 1. Proposer 1: EXP-06 adapter
    exp06_proposer = EXP06CandidateProposalAdapter()
    assert isinstance(exp06_proposer, CandidateProposalProtocol)

    # 2. Proposer 2: Alternative proposal engine
    alt_proposer = ReplaceableCandidateProposalEngine(engine_name="FutureMultiScaleProposalV3")
    assert isinstance(alt_proposer, CandidateProposalProtocol)

    scene_id = "S1A_COMPARISON_SCENE"
    t_utc = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)

    prop1 = exp06_proposer.propose(
        scene_identifier=scene_id,
        execution_mode=ExecutionMode.DEMO,
        acquisition_timestamp_utc=t_utc,
        timestamp_provenance=TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA,
        is_synthetic=True,
    )
    prop2 = alt_proposer.propose(
        scene_identifier=scene_id,
        execution_mode=ExecutionMode.DEMO,
        acquisition_timestamp_utc=t_utc,
        timestamp_provenance=TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA,
        is_synthetic=True,
    )

    feat = sample_feature_dict()

    # Pass prop1 through downstream pipeline
    reg1 = extract_candidate_regions(prop1, [feat])[0]
    look1 = assess_lookalikes(reg1)
    temp1 = reason_temporal_repeat_pass(reg1)
    ais1 = correlate_ais_candidates(reg1, candidate_vessels=[{"mmsi": "123", "evidence_compatibility_score": 0.8}])
    fuse1 = fuse_path_b_evidence(reg1, look1, temp1, ais1)

    # Pass prop2 through identical downstream pipeline
    reg2 = extract_candidate_regions(prop2, [feat])[0]
    look2 = assess_lookalikes(reg2)
    temp2 = reason_temporal_repeat_pass(reg2)
    ais2 = correlate_ais_candidates(reg2, candidate_vessels=[{"mmsi": "123", "evidence_compatibility_score": 0.8}])
    fuse2 = fuse_path_b_evidence(reg2, look2, temp2, ais2)

    # Both produced valid, type-identical contracts
    assert type(reg1) is type(reg2) is CandidateRegion
    assert type(look1) is type(look2) is LookalikeAssessment
    assert type(temp1) is type(temp2) is TemporalEvidence
    assert type(ais1) is type(ais2) is AISCompatibilityEvidence
    assert type(fuse1) is type(fuse2) is FusionEvidence

    assert prop1.source_model_identity == "EXP-06-ResNet34UNet"
    assert prop2.source_model_identity == "FutureMultiScaleProposalV3"


# ---------------------------------------------------------------------------
# Mandatory Adversarial Tests (CAO Decisions 1-6)
# ---------------------------------------------------------------------------


def test_adversarial_lineage_hash_is_not_content_hash() -> None:
    """Adversarial Test 1 (MD-01 / Decision 1):

    LineageRecord.lineage_sha256 proves derivational lineage identity only.
    Two objects with identical lineage parameters have the same lineage_sha256,
    even if their scientific payloads (geometry, area, pixel count) differ.
    """
    lineage1 = LineageRecord(
        stage_name="candidate_region",
        source_id="region_001",
        execution_mode=ExecutionMode.DEMO,
        is_synthetic=True,
    )
    lineage2 = LineageRecord(
        stage_name="candidate_region",
        source_id="region_001",
        execution_mode=ExecutionMode.DEMO,
        is_synthetic=True,
    )
    assert lineage1.lineage_sha256 == lineage2.lineage_sha256

    feat_a = sample_feature_dict()
    feat_b = sample_feature_dict()
    feat_b["area_m2"] = 9999999.0
    feat_b["pixel_count"] = 99999

    # Payloads differ materially, but lineage_sha256 is lineage identity, not payload hash
    assert feat_a["area_m2"] != feat_b["area_m2"]
    assert lineage1.lineage_sha256 == lineage2.lineage_sha256
    assert hasattr(lineage1, "lineage_sha256")
    assert not hasattr(lineage1, "content_sha256")


def test_adversarial_timestamp_fabrication_never_uses_epoch() -> None:
    """Adversarial Test 2 (MD-02 / Decision 2):

    When CandidateRegion has no authoritative acquisition timestamp (None),
    conversion to EvidenceItem MUST leave observation_time as genuinely None,
    and MUST NEVER substitute Unix epoch (1970-01-01) or any fake date sentinel.
    """
    proposal = make_valid_demo_proposal()
    proposal.acquisition_timestamp_utc = None
    proposal.timestamp_provenance = TimestampProvenance.UNKNOWN

    region = extract_candidate_regions(proposal, [sample_feature_dict()])[0]
    assert region.acquisition_timestamp_utc is None

    ev_item = region.to_evidence_item()
    # Genuinely None, NOT epoch
    assert ev_item.observation_time is None
    assert ev_item.observation_time != datetime.fromtimestamp(0, tz=timezone.utc)
    assert "NO_AUTHORITATIVE_TIMESTAMP" in ev_item.limitations

    ev_dict = ev_item.to_dict()
    assert ev_dict["observation_time_utc"] is None


def test_adversarial_derived_observation_status_is_inferred() -> None:
    """Adversarial Test 3 (MD-03 / Decision 3):

    A candidate region produced by model segmentation and polygonization is a
    DERIVED_ANALYSIS product. to_evidence_item() must assign the canonical derived status
    ObservationStatus.INFERRED, NOT direct sensor ObservationStatus.OBSERVED.
    """
    from ocean_sentinel.fusion import DerivationType, ObservationStatus

    proposal = make_valid_demo_proposal()
    region = extract_candidate_regions(proposal, [sample_feature_dict()])[0]

    ev_item = region.to_evidence_item()
    assert ev_item.derivation_type == DerivationType.DERIVED_ANALYSIS.value
    assert ev_item.observed_vs_inferred == ObservationStatus.INFERRED.value
    assert ev_item.observed_vs_inferred != ObservationStatus.OBSERVED.value


def test_adversarial_t0_t1_physical_provenance_validation() -> None:
    """Adversarial Test 4 (SR-01 / Decision 4):

    PHYSICAL TemporalEvidence requires authoritative provenance for BOTH T0 and T1
    when both timestamps participate in repeat-pass reasoning.
    """
    valid_t0 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    valid_t1 = datetime(2026, 9, 12, 10, 0, 0, tzinfo=timezone.utc)
    authoritative_prov = TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA

    lineage = LineageRecord(
        stage_name="temporal_reasoning",
        source_id="temporal_test",
        execution_mode=ExecutionMode.PHYSICAL,
        is_synthetic=False,
    )

    # 1. Both valid -> PASS
    ev_valid = TemporalEvidence(
        temporal_evidence_id="temp_valid",
        parent_region_id="reg_01",
        execution_mode=ExecutionMode.PHYSICAL,
        t0_scene_id="SCENE_T0",
        t1_scene_id="SCENE_T1",
        t0_acquisition_utc=valid_t0,
        t1_acquisition_utc=valid_t1,
        timestamp_provenance_t0=authoritative_prov,
        timestamp_provenance_t1=authoritative_prov,
        temporal_status=TemporalConsistencyStatus.PERSISTENT_FEATURE,
        lineage=lineage,
    )
    assert ev_valid.temporal_status == TemporalConsistencyStatus.PERSISTENT_FEATURE

    # 2. Invalid T0 + valid T1 -> FAIL
    with pytest.raises(ProvenanceGateViolationError, match="Invalid T0 timestamp provenance"):
        TemporalEvidence(
            temporal_evidence_id="temp_inv_t0",
            parent_region_id="reg_01",
            execution_mode=ExecutionMode.PHYSICAL,
            t0_scene_id="SCENE_T0",
            t1_scene_id="SCENE_T1",
            t0_acquisition_utc=valid_t0,
            t1_acquisition_utc=valid_t1,
            timestamp_provenance_t0=TimestampProvenance.UNKNOWN,  # VIOLATION
            timestamp_provenance_t1=authoritative_prov,
            temporal_status=TemporalConsistencyStatus.PERSISTENT_FEATURE,
            lineage=lineage,
        )

    # 3. Valid T0 + invalid T1 -> FAIL
    with pytest.raises(ProvenanceGateViolationError, match="Invalid T1 timestamp provenance"):
        TemporalEvidence(
            temporal_evidence_id="temp_inv_t1",
            parent_region_id="reg_01",
            execution_mode=ExecutionMode.PHYSICAL,
            t0_scene_id="SCENE_T0",
            t1_scene_id="SCENE_T1",
            t0_acquisition_utc=valid_t0,
            t1_acquisition_utc=valid_t1,
            timestamp_provenance_t0=authoritative_prov,
            timestamp_provenance_t1=TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP,  # VIOLATION
            temporal_status=TemporalConsistencyStatus.PERSISTENT_FEATURE,
            lineage=lineage,
        )

    # 4. Missing T0 on repeat-pass -> FAIL
    with pytest.raises(ProvenanceGateViolationError, match="Missing required T0 acquisition timestamp"):
        TemporalEvidence(
            temporal_evidence_id="temp_missing_t0",
            parent_region_id="reg_01",
            execution_mode=ExecutionMode.PHYSICAL,
            t0_scene_id="SCENE_T0",
            t1_scene_id="SCENE_T1",
            t0_acquisition_utc=None,  # VIOLATION
            t1_acquisition_utc=valid_t1,
            timestamp_provenance_t0=authoritative_prov,
            timestamp_provenance_t1=authoritative_prov,
            temporal_status=TemporalConsistencyStatus.PERSISTENT_FEATURE,
            lineage=lineage,
        )

    # 5. Missing T1 -> FAIL
    with pytest.raises(ProvenanceGateViolationError, match="Missing required T1 acquisition timestamp"):
        TemporalEvidence(
            temporal_evidence_id="temp_missing_t1",
            parent_region_id="reg_01",
            execution_mode=ExecutionMode.PHYSICAL,
            t0_scene_id="SCENE_T0",
            t1_scene_id="SCENE_T1",
            t0_acquisition_utc=valid_t0,
            t1_acquisition_utc=None,  # VIOLATION
            timestamp_provenance_t0=authoritative_prov,
            timestamp_provenance_t1=authoritative_prov,
            temporal_status=TemporalConsistencyStatus.PERSISTENT_FEATURE,
            lineage=lineage,
        )


def test_adversarial_defensive_revalidation_catches_mutation() -> None:
    """Adversarial Test 5 (SR-03 / Decision 5):

    A CandidateRegion constructed validly in PHYSICAL mode that is later mutated
    must fail closed when to_evidence_item() is called.
    """
    valid_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    lineage = LineageRecord(
        stage_name="candidate_region",
        source_id="reg_phys_01",
        execution_mode=ExecutionMode.PHYSICAL,
        is_synthetic=False,
    )

    region = CandidateRegion(
        region_id="reg_phys_01",
        parent_proposal_id="prop_01",
        source_scene_id="SCENE_01",
        execution_mode=ExecutionMode.PHYSICAL,
        geometry_geojson={"type": "Polygon", "coordinates": []},
        geometry_crs="EPSG:4326",
        bbox=(0.0, 0.0, 1.0, 1.0),
        centroid=(0.5, 0.5),
        pixel_count=100,
        area_m2=10000.0,
        area_crs="EPSG:32717",
        acquisition_timestamp_utc=valid_time,
        timestamp_provenance=TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA,
        lineage=lineage,
    )

    # Valid state converts with VERIFIED_OPERATIONAL
    ev = region.to_evidence_item()
    from ocean_sentinel.fusion import ProvenanceClass
    assert ev.provenance_class == ProvenanceClass.VERIFIED_OPERATIONAL.value

    # Mutate state 1: set acquisition_timestamp_utc to None post-instantiation
    region.acquisition_timestamp_utc = None
    with pytest.raises(ProvenanceGateViolationError, match="Acquisition timestamp missing"):
        region.to_evidence_item()

    # Restore timestamp, mutate state 2: invalid timestamp provenance
    region.acquisition_timestamp_utc = valid_time
    region.timestamp_provenance = TimestampProvenance.UNKNOWN
    with pytest.raises(ProvenanceGateViolationError, match="Invalid timestamp provenance"):
        region.to_evidence_item()

    # Restore provenance, mutate state 3: synthetic lineage
    region.timestamp_provenance = TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA
    region.lineage = LineageRecord(
        stage_name="candidate_region",
        source_id="reg_phys_01",
        execution_mode=ExecutionMode.PHYSICAL,
        is_synthetic=True,  # MUTATED VIOLATION
    )
    with pytest.raises(ProvenanceGateViolationError, match="Synthetic demo lineage detected"):
        region.to_evidence_item()


def test_adversarial_canonical_semantics_reuse_not_fork() -> None:
    """Adversarial Test 6 (SR-02 / Decision 6):

    Verify Path B translation boundary reuses canonical EvidenceItem,
    ObservationStatus, and ProvenanceClass rather than forking a competing
    evidence schema.
    """
    from ocean_sentinel.fusion import (
        EvidenceItem,
        ObservationStatus,
        ProvenanceClass,
        SourceType,
        EvidenceType,
    )

    proposal = make_valid_demo_proposal()
    region = extract_candidate_regions(proposal, [sample_feature_dict()])[0]
    ev = region.to_evidence_item()

    assert isinstance(ev, EvidenceItem)
    assert ev.provenance_class in [p.value for p in ProvenanceClass]
    assert ev.observed_vs_inferred in [o.value for o in ObservationStatus]
    assert ev.source_type == SourceType.SENTINEL_1_SAR.value
    assert ev.evidence_type == EvidenceType.SAR_DETECTION.value
