# Ocean Sentinel — Path B Multi-Stage Architecture & Interface Foundation

**Document ID**: `OCEAN-SENTINEL-PATH-B-ARCHITECTURE-FOUNDATION-V1`  
**Phase**: `PATH B ARCHITECTURE & INTERFACE FOUNDATION`  
**Certification Status**: `CERTIFIED_WITH_LIMITATIONS`  
**Architecture Authority**: ChatGPT (CAO)  
**Worker**: AG (Controlled Repository Implementation Worker)  
**Repository**: `D:\Projects\ocean-sentinel`  
**Environment**: Antigravity IDE 2.0 (Windows, CPU-only, Python 3.10.9 in `.venv`, uv 0.11.7, pytest 9.1.1)  

---

## 1. Executive Summary & Objective

Following the forensic closure and freeze of EXP-07, Ocean Sentinel has initiated the authorized **Path B** development direction:

$$\text{Binary Candidate Proposal} \longrightarrow \text{Candidate-Region Extraction} \longrightarrow \text{Lookalike Suppression / Contextual Validation} \longrightarrow \text{Temporal Repeat-Pass Reasoning} \longrightarrow \text{AIS Correlation} \longrightarrow \text{Evidence Fusion / Attribution}$$

This task establishes the **Architecture and Interface Foundation Only**:
- Preserves EXP-07 and all historical forensic artifacts as immutable evidence.
- Treats EXP-06 binary detection strictly as an **existing internal candidate proposal front-end**, NOT as a universally validated detector.
- Introduces decoupled, type-safe, auditable contracts and protocols across all 6 pipeline stages.
- Enforces strict non-negotiable scientific boundaries preventing premature attribution, uncalibrated probability generation, or false-positive suppression overclaims.
- Ensures the candidate proposal front-end is pluggable and replaceable via `CandidateProposalProtocol`.
- Strictly maintains bit-for-bit integrity of all 7 protected repository files.

---

## 2. Non-Negotiable Scientific Boundaries

Every contract in `ocean_sentinel.contracts.path_b` strictly enforces the following scientific boundaries:

1. **Candidate Output is NOT Confirmed Oil**:
   - Upstream binary detectors (such as EXP-06) generate candidate proposals with raw sigmoid scores. They do not constitute scientific confirmation of oil slicks.
   - `CandidateProposal` and `CandidateRegion` default to `UNVERIFIED_CANDIDATE` and `PROPOSED` evidence statuses. No stage may silently convert an upstream proposal into confirmed oil.
2. **Binary Detector Proposal is NOT Attribution**:
   - Detection or region extraction does not imply vessel attribution, causal source release, or legal liability.
3. **Lookalike Suppression is NOT Physical Proof**:
   - `LookalikeAssessment` evaluates contextual evidence (wind speed, SST gradients, internal wave packets, natural seeps, biogenic slicks).
   - Modeled as an evidence assessment ledger, NOT as a magical deterministic truth oracle. Attempting to assert `is_confirmed_physical_identity = True` raises `ScientificBoundaryViolationError`.
4. **Temporal Recurrence is Evidence, NOT Proof of Causality**:
   - Persistence or dissipation observed across sequential Sentinel-1 passes is observational change evidence. Attempting to assert `causality_inferred = True` raises `ScientificBoundaryViolationError`.
5. **AIS Compatibility is Compatibility Evidence, NOT Vessel Identification**:
   - Spatio-temporal coincidence between candidate drift backtracks/regions and AIS tracks is uncalibrated compatibility ranking.
   - Multiple candidate vessels must remain representable. Absence of AIS tracks does not prove vessel absence. Attempting to assert `is_attribution_proven = True` or `ais_absence_proves_vessel_absence = True` raises `ScientificBoundaryViolationError`.
6. **Fusion Preserves Multiple Hypotheses and Uncertainty States**:
   - `FusionEvidence` preserves all plausible origin hypotheses and candidate vessels.
   - Forcing a single winner when multiple candidates remain plausible is strictly prohibited and raises `ScientificBoundaryViolationError`.
   - Single-scalar global confidence or pseudo-probabilities are not manufactured.
7. **Strict Separation Between DEMO and PHYSICAL Execution Modes**:
   - In `PHYSICAL` mode, synthetic demo fixtures, missing acquisition timestamps, or externally supplied test timestamps fail closed via `ProvenanceGateViolationError`.
   - `DEMO` mode accommodates synthetic test fixtures for functional validation.
8. **Never Fabricate Evidence**:
   - Downstream stages inherit authoritative metadata strictly from upstream inputs. If an acquisition timestamp is missing, it remains genuinely `None` with `TimestampProvenance.UNKNOWN`; downstream stages never fabricate epoch timestamps or artificial confidence values.
9. **Canonical Evidence Translation Boundary**:
   - Path B stage-specific contracts define intermediate representations along the 6-stage pipeline. The canonical `EvidenceItem` and `EvidenceGraph` in `ocean_sentinel.fusion` remain the canonical evidence-system representation. Path B contracts translate cleanly into `EvidenceItem` via explicit methods (such as `CandidateRegion.to_evidence_item()`) rather than forking a competing evidence truth system.

---

## 3. Implemented Stage Contracts & Interfaces

The contracts are implemented in `src/ocean_sentinel/contracts/path_b.py` and exported through `src/ocean_sentinel/contracts`:

### Stage 1: `CandidateProposal`
- **Purpose**: Output of the binary candidate proposal front-end.
- **Fields**: `proposal_id`, `source_scene_id`, `source_model_identity`, `execution_mode`, `scenario_id`, `grid_crs`, `grid_transform`, `acquisition_timestamp_utc`, `timestamp_provenance`, `raw_scores`, `evidence_status`, `lineage`, `scientific_disclaimer`.
- **Invariants**: `evidence_status` defaults to `UNVERIFIED_CANDIDATE`. Validates fail-closed provenance in `PHYSICAL` mode.

### Stage 2: `CandidateRegion`
- **Purpose**: Output of candidate region extraction (polygonization / connected component analysis).
- **Fields**: `region_id`, `parent_proposal_id`, `source_scene_id`, `execution_mode`, `scenario_id`, `geometry_geojson`, `geometry_crs`, `bbox`, `centroid`, `pixel_count`, `area_m2`, `area_crs`, `morphology_metrics`, `acquisition_timestamp_utc`, `timestamp_provenance`, `score_statistics`, `evidence_status`, `lineage`, `scientific_disclaimer`.
- **Integration**: Provides `to_evidence_item()` to map directly into canonical `EvidenceItem` for backend/evidence graph interoperability:
  - **Defensive Re-Validation (Decision 5 / SR-03)**: Revalidates current mutable state before assigning `ProvenanceClass.VERIFIED_OPERATIONAL` to ensure post-instantiation mutation fails closed.
  - **Missing Timestamp Semantics (Decision 2 / MD-02)**: Absence of an authoritative acquisition timestamp remains genuinely `None`. Never substitutes Unix epoch or synthetic date sentinels.
  - **Derived Analysis Status (Decision 3 / MD-03)**: Marks derived analytical candidate regions as canonical `ObservationStatus.INFERRED` rather than direct sensor `ObservationStatus.OBSERVED`.

### Stage 3: `LookalikeAssessment`
- **Purpose**: Output of lookalike suppression and contextual validation.
- **Fields**: `assessment_id`, `parent_region_id`, `execution_mode`, `scenario_id`, `suppression_category`, `suppression_action`, `assessment_rationale`, `contextual_factors`, `lookalike_evidence_indicators`, `is_confirmed_physical_identity`, `evidence_status`, `lineage`, `scientific_disclaimer`.
- **Invariants**: `is_confirmed_physical_identity` is strictly invariant to `False`.

### Stage 4: `TemporalEvidence`
- **Purpose**: Output of temporal repeat-pass reasoning.
- **Fields**: `temporal_evidence_id`, `parent_region_id`, `execution_mode`, `scenario_id`, `t0_scene_id`, `t1_scene_id`, `t0_acquisition_utc`, `t1_acquisition_utc`, `timestamp_provenance_t0`, `timestamp_provenance_t1`, `temporal_status`, `change_category`, `overlap_iou`, `area_delta_m2`, `causality_inferred`, `evidence_status`, `lineage`, `scientific_disclaimer`.
- **Invariants**:
  - `causality_inferred` is strictly invariant to `False`.
  - **T0/T1 Provenance Gate (Decision 4 / SR-01)**: Requires authoritative provenance for BOTH T0 and T1 when both participate in repeat-pass reasoning in `PHYSICAL` mode.

### Stage 5: `AISCompatibilityEvidence`
- **Purpose**: Output of spatio-temporal AIS vessel correlation.
- **Fields**: `correlation_evidence_id`, `parent_region_id`, `execution_mode`, `scenario_id`, `candidate_vessels`, `candidate_count`, `is_attribution_proven`, `ais_absence_proves_vessel_absence`, `evidence_status`, `lineage`, `scientific_disclaimer`.
- **Invariants**: `is_attribution_proven` and `ais_absence_proves_vessel_absence` are strictly invariant to `False`. Multiple candidate vessels remain representable.

### Stage 6: `FusionEvidence`
- **Purpose**: Output of multi-source evidence fusion and attribution reasoning.
- **Fields**: `fusion_evidence_id`, `execution_mode`, `scenario_id`, `candidate_region_ids`, `synthesized_hypotheses`, `uncertainty_state`, `has_unresolved_uncertainty`, `single_winner_forced`, `attribution_adjudicated`, `contributing_evidence_ids`, `evidence_status`, `lineage`, `scientific_disclaimer`.
- **Invariants**: `single_winner_forced` and `attribution_adjudicated` are strictly invariant to `False`.

---

## 4. Cryptographic Lineage Tracking

All contract objects embed an immutable `LineageRecord`:
```python
@dataclass(frozen=True)
class LineageRecord:
    stage_name: str
    source_id: str
    parent_hashes: Tuple[str, ...]
    timestamp_provenance: TimestampProvenance
    execution_mode: ExecutionMode
    scenario_id: Optional[str]
    is_synthetic: bool
    lineage_sha256: str
```
### Decision 1 — Lineage Identity vs Payload Content:
`lineage_sha256` proves derivational lineage identity only (stage name, source identity, parent hashes, timestamp provenance, execution mode, scenario context, and synthetic flag).
It does **NOT** prove:
- payload integrity
- authenticity
- authentication
- non-repudiation

Every stage transitions by binding the upstream object's `lineage_sha256` into its own `parent_hashes`. This guarantees unbroken forensic auditability from raw candidate proposal through multi-source fusion. Payload content hashing is deferred to future scope when a canonical, circularity-free payload serialization representation is available.

---

## 5. Replaceable Candidate Proposal Protocol

To prevent hard-coding downstream pipeline stages to EXP-06, a runtime-checkable Protocol is introduced:
```python
@runtime_checkable
class CandidateProposalProtocol(Protocol):
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
    ) -> CandidateProposal: ...
```

Two reference implementations are provided:
1. `EXP06CandidateProposalAdapter`: Wraps EXP-06 ResNet34-UNet output as an existing candidate proposal front-end.
2. `ReplaceableCandidateProposalEngine`: Demonstrates that alternative model architectures or future front-ends plug into the exact same downstream pipeline without modifying any contracts.

---

## 6. Verification and Contract Test Matrix

All 15 contract test requirements (including 6 mandatory adversarial tests) are verified in [tests/test_path_b_contracts.py](file:///d:/Projects/ocean-sentinel/tests/test_path_b_contracts.py):

| Requirement ID | Test Function | Result | Scope / Invariant Verified |
| :--- | :--- | :--- | :--- |
| **REQ-01** | `test_proposal_to_region_interface_is_valid` | **PASS** | Proposal -> Region extraction, geometry, metric area, and `to_evidence_item()` compatibility. |
| **REQ-02** | `test_proposal_does_not_equal_confirmed_detection` | **PASS** | Status is unverified candidate. Boundary violation exceptions trigger on attempts to claim confirmed oil, attribution, or physical identity proof. |
| **REQ-03** | `test_provenance_survives_stage_transitions` | **PASS** | Unbroken SHA-256 parent hash chain across all 6 stages. |
| **REQ-04** | `test_execution_mode_and_scenario_context_survive_stage_transitions` | **PASS** | Execution mode (`DEMO`) and scenario context (`TRUJILLO_00007_01339`) preserved identically at every stage. |
| **REQ-05** | `test_missing_required_provenance_fails_closed` | **PASS** | `PHYSICAL` mode rejects synthetic data, missing timestamps, and test timestamps fail-closed. |
| **REQ-06** | `test_multiple_candidate_vessels_remain_representable` | **PASS** | Preserves 3 distinct candidate vessels in AIS evidence and blocks single-winner forced selection in fusion. |
| **REQ-07** | `test_demo_and_physical_separation_remains_enforced` | **PASS** | Strict isolation between `DEMO` and `PHYSICAL` operational modes. |
| **REQ-08** | `test_downstream_stages_do_not_fabricate_timestamps_or_confidence` | **PASS** | Downstream stages do not invent timestamps or single-scalar confidence scores. |
| **REQ-09** | `test_exp06_replaceable_without_changing_downstream_contracts` | **PASS** | `EXP06CandidateProposalAdapter` and `ReplaceableCandidateProposalEngine` both satisfy protocol and feed identical downstream stages. |
| **ADV-01** | `test_adversarial_lineage_hash_is_not_content_hash` | **PASS** | `lineage_sha256` represents derivational lineage identity, not payload content hash. (MD-01 / Decision 1) |
| **ADV-02** | `test_adversarial_timestamp_fabrication_never_uses_epoch` | **PASS** | Absence of timestamp leaves `observation_time` as genuinely `None`; never substitutes Unix epoch sentinel. (MD-02 / Decision 2) |
| **ADV-03** | `test_adversarial_derived_observation_status_is_inferred` | **PASS** | Derived analytical candidate regions marked as canonical `ObservationStatus.INFERRED`. (MD-03 / Decision 3) |
| **ADV-04** | `test_adversarial_t0_t1_physical_provenance_validation` | **PASS** | PHYSICAL mode requires authoritative provenance for BOTH T0 and T1 when participating in repeat pass. (SR-01 / Decision 4) |
| **ADV-05** | `test_adversarial_defensive_revalidation_catches_mutation` | **PASS** | Post-init mutation of mutable candidate region fails closed on `to_evidence_item()`. (SR-03 / Decision 5) |
| **ADV-06** | `test_adversarial_canonical_semantics_reuse_not_fork` | **PASS** | Verifies reuse of canonical `EvidenceItem`, `ObservationStatus`, and `ProvenanceClass`. (SR-02 / Decision 6) |

---

## 7. Protected File Integrity Verification

All 7 protected repository files were verified bit-for-bit against their authoritative SHA-256 baseline hashes:

| File Path | Authoritative SHA-256 Baseline | Post-Implementation SHA-256 | Status |
| :--- | :--- | :--- | :--- |
| `.gitignore` | `a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444` | `a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444` | **IDENTICAL** |
| `src/ocean_sentinel/ingestion/dataset.py` | `f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c` | `f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c` | **IDENTICAL** |
| `src/ocean_sentinel/governance/runner.py` | `dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0` | `dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0` | **IDENTICAL** |
| `data/metadata/governance_v2/rules.json` | `b216f369d68a027e4708e8cbcf3991d8effd5ba5a063a3b8b6b3fc2261d85c4e` | `b216f369d68a027e4708e8cbcf3991d8effd5ba5a063a3b8b6b3fc2261d85c4e` | **IDENTICAL** |
| `data/metadata/governance_v2/lessons.json` | `4784a440070bc00612bc3bfa9b29a7acc181934f894a9e22bd340faab7076395` | `4784a440070bc00612bc3bfa9b29a7acc181934f894a9e22bd340faab7076395` | **IDENTICAL** |
| `data/metadata/governance_v2/incidents.json` | `fa3051a185894ee1fe46edb5825ebcfe92b107f80fb7527bf5746d4ec5b91836` | `fa3051a185894ee1fe46edb5825ebcfe92b107f80fb7527bf5746d4ec5b91836` | **IDENTICAL** |
| `src/ocean_sentinel/temporal.py` | `46614361e1be20a278d0af9ceee222e4787df1eade7d52a88b372965170e26cf` | `46614361e1be20a278d0af9ceee222e4787df1eade7d52a88b372965170e26cf` | **IDENTICAL** |

---

## 8. Scientific Limitations & Intentionally Unimplemented Scope

1. **Software/Contract Scope Only**:
   - Certification applies strictly to the implemented software contracts, schemas, and test suites. It does NOT claim that Path B is scientifically validated or benchmarked.
2. **Zero Model Training & Zero Parameter Tuning**:
   - No models were trained, fine-tuned, or retrained.
3. **Zero Holdout / Benchmark Access**:
   - Neither Part-III nor any holdout dataset was accessed.
4. **Zero Frontend Redesign**:
   - The user-facing dashboard was not redesigned; existing API and evidence schemas remain fully supported.
5. **Heuristic Contextual Rules**:
   - Lookalike assessment and temporal classification logic in the reference transition functions represent baseline heuristic evaluators, not universally validated oceanographic physics models.
