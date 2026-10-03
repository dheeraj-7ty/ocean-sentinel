# OCEAN-SENTINEL — PATH B INDEPENDENT ADVERSARIAL CODE & SEMANTIC CONTRACT REVIEW
**TASK ID:** OCEAN-SENTINEL-PATH-B-INDEPENDENT-REVIEW-V1

---

## 1. REVIEW STATUS

**COMPLETE** — All 15 review areas inspected, counterexamples constructed and verified, protected file hashes confirmed.

---

## 2. REPOSITORY BASELINE

| Item | Value |
|------|-------|
| **Branch** | `main` (assumed, single branch repo) |
| **HEAD** | Latest commit in working directory |
| **Worktree Status** | Clean — no uncommitted changes to tracked files |
| **Protected Hashes Verified** | **ALL 7 FILES IDENTICAL** to authoritative baselines |

| File | Authoritative SHA-256 | Verified SHA-256 | Status |
|------|----------------------|------------------|--------|
| `.gitignore` | a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444 | a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444 | **IDENTICAL** |
| `src/ocean_sentinel/ingestion/dataset.py` | f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c | f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c | **IDENTICAL** |
| `src/ocean_sentinel/governance/runner.py` | dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0 | dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0 | **IDENTICAL** |
| `data/metadata/governance_v2/rules.json` | b216f369d68a027e4708e8cbcf3991d8effd5ba5a063a3b8b6b3fc2261d85c4e | b216f369d68a027e4708e8cbcf3991d8effd5ba5a063a3b8b6b3fc2261d85c4e | **IDENTICAL** |
| `data/metadata/governance_v2/lessons.json` | 4784a440070bc00612bc3bfa9b29a7acc181934f894a9e22bd340faab7076395 | 4784a440070bc00612bc3bfa9b29a7acc181934f894a9e22bd340faab7076395 | **IDENTICAL** |
| `data/metadata/governance_v2/incidents.json` | fa3051a185894ee1fe46edb5825ebcfe92b107f80fb7527bf5746d4ec5b91836 | fa3051a185894ee1fe46edb5825ebcfe92b107f80fb7527bf5746d4ec5b91836 | **IDENTICAL** |
| `src/ocean_sentinel/temporal.py` | 46614361e1be20a278d0af9ceee222e4787df1eade7d52a88b372965170e26cf | 46614361e1be20a278d0af9ceee222e4787df1eade7d52a88b372965170e26cf | **IDENTICAL** |

All contract tests pass (9/9).

---

## 3. MATERIAL DEFECTS

### MD-01: `LineageRecord.content_sha256` Misrepresents Content Identity

| Field | Detail |
|-------|--------|
| **File** | `src/ocean_sentinel/contracts/path_b.py` |
| **Class/Function** | `LineageRecord.__post_init__` (lines 183-193) |
| **Mechanism** | `content_sha256` hashes only lineage metadata: `stage_name`, `source_id`, `parent_hashes`, `timestamp_provenance`, `execution_mode`, `scenario_id`, `is_synthetic`. It does **not** hash the scientific payload (geometry, scores, metrics, morphology, etc.). |
| **Counterexample** | Two `LineageRecord` objects with identical lineage metadata but materially different scientific payloads produce **identical** `content_sha256` values (verified: `3a690484793c402de368a6c561cf335b48dd16e6a605d72ab3cb7bcd1acb3c17`). |
| **Observed Consequence** | The field name `content_sha256` and its documentation ("Deterministic hash of immutable lineage parameters") imply payload content integrity. Downstream systems may incorrectly rely on it for payload deduplication, change detection, or authentication. |
| **Why It Matters** | Violates the distinction between **lineage identity** (derivation ancestry) and **content identity** (payload integrity). A content hash that doesn't hash content is a semantic defect. |
| **Smallest Safe Correction** | Rename field to `lineage_sha256` or `provenance_sha256` and update all references. If payload content integrity is required, add a separate `payload_sha256` that hashes the actual scientific content. |
| **Existing Tests That Fail to Catch It** | `test_provenance_survives_stage_transitions` only verifies parent hash chain continuity, not content sensitivity. |
| **Proposed Regression Test** | Create two stage objects with identical lineage metadata but different `geometry_geojson`/`morphology_metrics`/`raw_scores`; assert their `content_sha256` values differ (if payload hashing added) or assert field is renamed. |

---

### MD-02: `CandidateRegion.to_evidence_item()` Fabricates Unix Epoch Timestamp

| Field | Detail |
|-------|--------|
| **File** | `src/ocean_sentinel/contracts/path_b.py` |
| **Class/Function** | `CandidateRegion.to_evidence_item()` (lines 380-384) |
| **Mechanism** | When `acquisition_timestamp_utc` is `None`, the method substitutes `datetime.fromtimestamp(0, tz=timezone.utc)` (Unix epoch: 1970-01-01 00:00:00+00:00) instead of preserving absence. |
| **Counterexample** | A `CandidateRegion` with `acquisition_timestamp_utc=None` and `timestamp_provenance=UNKNOWN` converts to an `EvidenceItem` with `observation_time=1970-01-01 00:00:00+00:00`. Verified via test execution. |
| **Observed Consequence** | Downstream systems (fusion, API, visualization) receive a concrete timestamp that will be interpreted as an actual observation time. The `limitations` list includes `"NO_AUTHORITATIVE_TIMESTAMP"` but the timestamp field itself is populated with a fabricated value. |
| **Why It Matters** | Directly violates the "Never Fabricate Evidence" boundary (Architecture Foundation §8). A missing authoritative timestamp must remain semantically missing, not replaced with a default that pollutes temporal reasoning. |
| **Smallest Safe Correction** | Make `observation_time` optional in `EvidenceItem` (requires canonical schema change) OR represent absence explicitly with a sentinel that cannot be confused with a real timestamp (e.g., `None` with a mandatory `timestamp_provenance=MISSING` enum value). The current `EvidenceItem` constructor requires `observation_time: datetime` — this canonical schema must be extended. |
| **Existing Tests That Fail to Catch It** | `test_proposal_to_region_interface_is_valid` checks `ev_item.source_id` and limitations but does not verify `observation_time` semantics when source timestamp is missing. `test_downstream_stages_do_not_fabricate_timestamps_or_confidence` verifies `CandidateRegion` preserves `None` but does not check the `to_evidence_item()` conversion. |
| **Proposed Regression Test** | Create `CandidateRegion` with `acquisition_timestamp_utc=None`; convert to `EvidenceItem`; assert `observation_time` is `None` or a distinct sentinel (after schema change), not Unix epoch. |

---

### MD-03: `CandidateRegion.to_evidence_item()` Assigns `observed_vs_inferred=OBSERVED` for `DERIVED_ANALYSIS`

| Field | Detail |
|-------|--------|
| **File** | `src/ocean_sentinel/contracts/path_b.py` |
| **Class/Function** | `CandidateRegion.to_evidence_item()` (line 411) |
| **Mechanism** | Hard-codes `observed_vs_inferred=ObservationStatus.OBSERVED` while simultaneously setting `derivation_type=DerivationType.DERIVED_ANALYSIS`. |
| **Counterexample** | A `CandidateRegion` (extracted from a binary detector proposal via polygonization) is a **derived analytical product**, not a direct sensor observation. Yet its `EvidenceItem` representation claims `OBSERVED`. Verified: `derivation_type=DERIVED_ANALYSIS` but `observed_vs_inferred=OBSERVED`. |
| **Observed Consequence** | Evidence graph consumers cannot distinguish direct observations from derived analytical products. This erodes the epistemic boundary between "what the sensor saw" and "what the algorithm inferred." |
| **Why It Matters** | Violates the provenance semantics in `fusion.py` where `ObservationStatus.OBSERVED` means "directly observed by sensor" and `INFERRED`/`HYPOTHESIS` mean derived. A polygonized candidate region is manifestly inferred/derived. |
| **Smallest Safe Correction** | Change line 411 to `observed_vs_inferred=ObservationStatus.INFERRED` (or `HYPOTHESIS` per canonical semantics). |
| **Existing Tests That Fail to Catch It** | `test_proposal_to_region_interface_is_valid` does not assert `observed_vs_inferred` value. |
| **Proposed Regression Test** | Assert `region.to_evidence_item().observed_vs_inferred == ObservationStatus.INFERRED` (or `HYPOTHESIS`). |

---

## 4. SEMANTIC RISKS REQUIRING CAO DECISION

### SR-01: TemporalEvidence PHYSICAL Validation Asymmetry (T0 vs T1)

| Field | Detail |
|-------|--------|
| **File** | `src/ocean_sentinel/contracts/path_b.py` |
| **Class/Function** | `TemporalEvidence.validate_fail_closed_provenance()` (lines 530-545) |
| **Issue** | PHYSICAL mode validation checks `timestamp_provenance_t1` but **does not validate** `timestamp_provenance_t0`. A `TemporalEvidence` in PHYSICAL mode can have `t0_acquisition_utc` with `EXTERNALLY_SUPPLIED_TEST_TIMESTAMP` or `UNKNOWN` provenance and pass validation. |
| **Tradeoff** | The architecture may intentionally only require T1 (current observation) to be authoritative since T0 is historical context. However, temporal reasoning depends on **both** timestamps being authoritative for PHYSICAL drift/origin inference. |
| **CAO Decision Required** | Should PHYSICAL mode require authoritative provenance for **both** T0 and T1 timestamps? If yes, add symmetric validation. If no, document the rationale explicitly. |
| **Risk if Unresolved** | PHYSICAL drift/origin analyses could be anchored on unverified historical timestamps, invalidating the entire backward trajectory chain. |

---

### SR-02: Parallel Provenance/Evidence Concepts Between Path B and Canonical Modules

| Field | Detail |
|-------|--------|
| **Files** | `src/ocean_sentinel/contracts/path_b.py` vs `src/ocean_sentinel/fusion.py`, `src/ocean_sentinel/orchestration/jobs.py` |
| **Issue** | Path B introduces parallel concepts that duplicate or overlap with canonical modules: |
| | • `LineageRecord` vs `EvidenceItem.parent_evidence_ids` + `root_source_ids` |
| | • `FusionEvidence` vs `EvidenceGraph` + `CandidateHypothesis` |
| | • `ExecutionMode` (DEMO/PHYSICAL) vs `JobMode` (DEMO/REAL_REPOSITORY/PHYSICAL) |
| | • `timestamp_provenance` in `LineageRecord` vs `TimestampProvenance` enum usage in `temporal.py` |
| **Tradeoff** | Path B contracts are designed as a **self-contained architecture foundation** with strict boundaries. Canonical modules evolved separately with different semantics (e.g., `EvidenceGraph` supports independence analysis, double-counting prevention, conflict preservation). Unification would require significant refactoring. |
| **CAO Decision Required** | Should Path B contracts **reuse** canonical evidence graph semantics (preventing divergence) or **remain independent** (preserving architectural isolation)? If independent, a clear mapping/translation layer must be maintained. |
| **Risk if Unresolved** | Semantic drift between two provenance/evidence systems; conversion losses; audit confusion. |

---

### SR-03: `ProvenanceClass.VERIFIED_OPERATIONAL` Assignment Without Full Validation Re-check

| Field | Detail |
|-------|--------|
| **File** | `src/ocean_sentinel/contracts/path_b.py` |
| **Class/Function** | `CandidateRegion.to_evidence_item()` (lines 385-392) |
| **Issue** | `VERIFIED_OPERATIONAL` is assigned based solely on `execution_mode == PHYSICAL and not lineage.is_synthetic`. It does **not** re-validate that `timestamp_provenance` is authoritative and `acquisition_timestamp_utc` is present. The constructor validates this, but `to_evidence_item()` can be called later on an object that was mutated or constructed in a context where validation was bypassed. |
| **Tradeoff** | Re-validating in `to_evidence_item()` adds defensive depth but duplicates logic. The dataclass is not frozen, so post-construction mutation is theoretically possible. |
| **CAO Decision Required** | Should `to_evidence_item()` re-validate PHYSICAL provenance requirements, or is constructor-time validation sufficient given the architecture's trust boundaries? |
| **Risk if Unresolved** | A mutated or improperly constructed `CandidateRegion` could produce a `VERIFIED_OPERATIONAL` `EvidenceItem` with invalid provenance. |

---

## 5. MINOR FINDINGS

| ID | Finding | File/Location | Severity |
|----|---------|---------------|----------|
| MN-01 | `content_sha256` uses only 8 hex chars for ID generation (`lineage.content_sha256[:8]`), increasing collision probability in large-scale deployments. | `path_b.py` lines 793, 808, 964, 1024, 1067, 1112 | Low |
| MN-02 | `assess_lookalikes()` uses hard-coded heuristic thresholds (wind < 3.0 m/s, etc.) with no configurability or uncertainty quantification. Documented as "baseline heuristic evaluators" but embedded in contract transition function. | `path_b.py` lines 920-985 | Low |
| MN-03 | `reason_temporal_repeat_pass()` uses hard-coded IoU thresholds (0.20, 0.05) for temporal classification with no provenance of threshold selection. | `path_b.py` lines 988-1044 | Low |
| MN-04 | `CandidateProposalProtocol` uses `**kwargs` which weakens static type checking; `raw_scores` and `parent_hashes` are in `**kwargs` for adapters but not in protocol signature. | `path_b.py` lines 723-746 | Low |
| MN-05 | `FusionEvidence.uncertainty_state` default initialization sets `"sensor_latency_uncalibrated": True` and `"ais_coverage_gaps_present": True` unconditionally, even when evidence may not have these limitations. | `path_b.py` lines 1114-1117 | Low |
| MN-06 | `JobMode.REAL_REPOSITORY` and `PipelineType.REAL_REPOSITORY` exist in orchestration but have no counterpart in Path B `ExecutionMode` (only DEMO/PHYSICAL). Creates mapping ambiguity. | `jobs.py` lines 26-40 vs `path_b.py` lines 112-116 | Low |

---

## 6. AREAS VERIFIED SOUND

| Review Area | Status | Notes |
|-------------|--------|-------|
| **Area 5: Scientific Boundaries** | ✅ **SOUND** | All boundary violations (`is_confirmed_physical_identity`, `causality_inferred`, `is_attribution_proven`, `ais_absence_proves_vessel_absence`, `single_winner_forced`, `attribution_adjudicated`) raise `ScientificBoundaryViolationError` at construction. No bypass paths in transition functions. |
| **Area 6: DEMO vs PHYSICAL Separation** | ✅ **SOUND** | PHYSICAL mode rejects synthetic lineage, missing timestamps, and test timestamps at every stage constructor. No path found for DEMO→PHYSICAL leakage or PHYSICAL→DEMO downgrade. |
| **Area 7: Replaceable Candidate Front-End** | ✅ **SOUND** | `CandidateProposalProtocol` fully decouples downstream stages from EXP-06. Both `EXP06CandidateProposalAdapter` and `ReplaceableCandidateProposalEngine` satisfy protocol. Transition functions use only `CandidateProposal` contract fields. |
| **Area 8: Score/Confidence Semantics** | ✅ **SOUND** | Raw scores remain raw; no calibration or probability reinterpretation. `FusionEvidence` explicitly preserves `has_unresolved_uncertainty=True` and forbids `single_winner_forced`. Tests verify no `global_confidence`/`attribution_probability` fabrication. |
| **Area 10: AIS Semantics** | ✅ **SOUND** | Multiple candidate vessels preserved; `is_attribution_proven` and `ais_absence_proves_vessel_absence` enforced False; `candidate_count` matches `len(candidate_vessels)`; fusion preserves all hypotheses. |
| **Area 11: Fusion Semantics** | ✅ **SOUND** (within Path B) | `FusionEvidence` preserves multiple hypotheses, uncertainty, contributing evidence traceability, parent lineage. No forced single winner. |
| **Area 13: Lineage Transition Invariants** | ✅ **SOUND** | Every transition function correctly binds upstream `content_sha256` into `parent_hashes` and inherits `execution_mode`, `scenario_id`, `timestamp_provenance`, `is_synthetic`. |

---

## 7. TEST ADEQUACY ASSESSMENT

| Test Requirement | Current Test | Catches Material Defects? | Gap |
|------------------|--------------|---------------------------|-----|
| Content-vs-lineage hash collision | ❌ None | **NO** | MD-01 not caught |
| Fake/default timestamp conversion | ❌ Partial | **NO** | MD-02 not caught (test checks `CandidateRegion` preserves `None` but not `to_evidence_item()`) |
| Provenance downgrade | ⚠️ Partial | Partial | SR-03 not tested |
| Confidence reinterpretation | ✅ Yes | Yes | `test_downstream_stages_do_not_fabricate_timestamps_or_confidence` |
| Hidden EXP-06 dependency | ✅ Yes | Yes | `test_exp06_replaceable_without_changing_downstream_contracts` |
| Candidate collapse | ✅ Yes | Yes | `test_multiple_candidate_vessels_remain_representable` |
| DEMO/PHYSICAL leakage | ✅ Yes | Yes | `test_demo_and_physical_separation_remains_enforced` |
| T0 timestamp provenance symmetry | ❌ None | **NO** | SR-01 not caught |
| Observed vs inferred semantics | ❌ None | **NO** | MD-03 not caught |

**Overall Test Quality**: Good for functional contract validation; **insufficient for semantic defect detection**. Tests exercise "happy path" fixtures but do not construct adversarial counterexamples for the identified material defects.

---

## 8. PRIORITIZED CORRECTIVE ACTIONS

| Priority | Action | Defect(s) Addressed | Effort |
|----------|--------|---------------------|--------|
| **P0** | Rename `LineageRecord.content_sha256` → `lineage_sha256` (or `provenance_sha256`) and update all references; add separate `payload_sha256` if content integrity needed. | MD-01 | Low (rename + test) |
| **P0** | Fix `CandidateRegion.to_evidence_item()`: make `observation_time` optional in `EvidenceItem` (canonical) or use explicit MISSING sentinel; never fabricate Unix epoch. | MD-02 | Medium (requires `fusion.py` `EvidenceItem` schema change) |
| **P0** | Fix `CandidateRegion.to_evidence_item()`: set `observed_vs_inferred=ObservationStatus.INFERRED` (or `HYPOTHESIS`) for `DERIVED_ANALYSIS` items. | MD-03 | Low (one-line change) |
| **P1** | Add symmetric T0/T1 timestamp provenance validation in `TemporalEvidence.validate_fail_closed_provenance()` for PHYSICAL mode. | SR-01 | Low |
| **P1** | Add re-validation of PHYSICAL provenance in `CandidateRegion.to_evidence_item()` before assigning `VERIFIED_OPERATIONAL`. | SR-03 | Low |
| **P2** | Document/decide on Path B ↔ Canonical provenance concept unification strategy. | SR-02 | Architectural (CAO decision) |
| **P3** | Add regression tests for MD-01, MD-02, MD-03, SR-01. | All | Medium |

---

## 9. OVERALL REVIEW CONCLUSION

**Path B Architecture Foundation is structurally sound and enforces its declared scientific boundaries at construction time.** The six-stage pipeline correctly preserves provenance lineage, execution mode, scenario context, and multiple hypotheses through all transitions. The replaceable candidate proposal protocol is well-designed and verified.

**However, three material semantic defects exist** that violate the "Never Fabricate Evidence" and content-identity principles:

1. **MD-01**: `content_sha256` misnamed — hashes lineage metadata only, not scientific payload.
2. **MD-02**: `to_evidence_item()` fabricates Unix epoch timestamps for missing authoritative timestamps.
3. **MD-03**: `to_evidence_item()` claims `OBSERVED` status for derived analytical products.

**Two semantic risks require CAO architectural decisions** regarding temporal validation symmetry and provenance concept unification with canonical modules.

**The test suite passes but does not catch these semantic defects** — it validates instantiation and happy-path transitions, not adversarial semantic correctness.

---

## 10. CERTIFICATION

### CERTIFIED_WITH_LIMITATIONS

**Certification applies ONLY to the software/contract review.**  
It does **NOT** mean Path B is scientifically validated.

**Limitations:**
- Three material defects (MD-01, MD-02, MD-03) must be corrected before PHYSICAL mode deployment.
- Two semantic risks (SR-01, SR-02) require CAO decisions.
- Test suite requires adversarial augmentation.
- Canonical `EvidenceItem` schema must be extended to support optional/missing timestamps for MD-02 fix.

---

## SUMMARY STATISTICS

| Category | Count |
|----------|-------|
| **Material Defects** | 3 |
| **Semantic Risks Requiring CAO Decision** | 3 |
| **Minor Findings** | 6 |
| **Areas Verified Sound** | 7 of 15 |
| **Requires Targeted Corrective Pass** | **YES** |

**Exact Reason**: Three material defects violate stated contracts (content identity, timestamp fabrication, observed-vs-inferred semantics). Two semantic risks require architectural decisions on temporal validation symmetry and provenance concept unification.

**Exact Next Action for CAO**:
1. Approve P0 corrections (MD-01, MD-02, MD-03) — minimal, localized fixes.
2. Decide on SR-01 (T0/T1 temporal validation symmetry) and SR-02 (Path B ↔ Canonical provenance unification).
3. Assign test augmentation for adversarial semantic coverage.

---

**REVIEWER**: Independent Adversarial Reviewer  
**DATE**: 2026-09-26  
**SIGNATURE**: Review complete — no self-repair performed, no files modified.