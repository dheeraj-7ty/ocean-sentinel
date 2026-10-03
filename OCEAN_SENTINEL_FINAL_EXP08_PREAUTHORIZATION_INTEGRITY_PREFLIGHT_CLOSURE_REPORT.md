# OCEAN SENTINEL — FINAL EXP-08 PRE-AUTHORIZATION INTEGRITY PREFLIGHT CLOSURE REPORT

**Document ID**: `OCEAN_SENTINEL_FINAL_EXP08_PREAUTHORIZATION_INTEGRITY_PREFLIGHT_CLOSURE_REPORT`  
**Task ID**: `OCEAN-SENTINEL-FINAL-EXP08-PREAUTHORIZATION-INTEGRITY-PREFLIGHT-CLOSURE`  
**Date**: 2026-09-28  
**Model**: Gemini 3.8 Flash High (Antigravity IDE 2.0)  
**Authority**: ChatGPT (CAO / Architecture Authority) / Human (Final Approval Authority)  
**Protocol Version at Closure**: **3.4** (`docs/exp08_corrected_protocol.md`)  
**Pilot Document Version at Closure**: **3.4** (`docs/exp08_cdse_physical_compatibility_pilot.md`)  
**Supersedes**: All prior preflight, closure, and micro-closure reports (R5, R5.1, R5.2, R5.3, R5.4, R5.5)

---

> [!IMPORTANT]
> ### ABSOLUTE SCIENTIFIC FIREWALL — FULLY PRESERVED
> - **EXECUTION_AUTHORIZED**: `FALSE`
> - **SCIENTIFIC_EXECUTION**: `NO`
> - **INFERENCE**: `NO`
> - **TRAINING**: `NO`
> - **HOLDOUT**: `NOT_ACCESSED`
> - **PART_III**: `NOT_ACCESSED`
> - **GPU**: `NO`
> - **NETWORK**: `NO`
>
> Zero inference forward passes, zero model predictions, zero holdout data access, zero training, and zero checkpoint modifications occurred during this phase. No scientific output was produced. This document is a forensic integrity report only.

---

## 1. Purpose and Scope

This report is the **last preparatory document** in the EXP-08 pre-authorization chain. It consolidates the verified state of the repository, protocol, pilot, and test suite after the complete Phase 11 integrity remediation sequence (R2 → R5.5), confirming that the execution contract is internally consistent, scientifically honest, and ready for final human/CAO authorization.

This is **NOT**:
- A scientific results report
- A threshold calibration or model performance report
- A new broad audit phase
- An authorization to execute EXP-08

This is **ONLY**:
- A final consolidated integrity statement
- A reconciliation of the R5.5 Micro-Closure Report against the current repository state
- A re-verification of the 161-test suite
- A final enumeration of pre-declared limitations and open non-blockers

---

## 2. Integrity Remediation Lineage

The following sequence of phases produced the current frozen protocol state:

| Phase | Task ID | Key Resolutions |
|---|---|---|
| R2 | Phase11-R2 | Route A incompatibility established; PANGAEA JPEG ruled out |
| R3 | Phase11-R3 | DARTIS ontology forensically established; data_matrix.tab parsed |
| R4 | Phase11-R4 | DARTIS spatial footprint vs Trujillo raster extent geometry formally defined; R4 overlap computed |
| R5 | Phase11-R5 | Initial physical pilot conducted; coarse 64×64 spatial mismatch identified and corrected |
| R5.1 | Phase11-R5.1 | Full angular grid pilot executed at 8.983152841195215e-5° EPSG:4326; byte-level compatibility confirmed for 3/3 scenes |
| R5.2 | Phase11-R5.2 | Channel source-truth vs operational contract resolved; stale overlap denominator purged; native-resolution overclaims removed |
| R5.3 | Phase11-R5.3 | Provenance independence semantics clarified; evaluation domain geometry harmonized; dataMask semantics formalized |
| R5.4 | Phase11-R5.4 | Smart Expanded AABB vs clamped 12-window non-equivalence formalized; cluster/stratum interaction documented; Protocol V3.4 frozen |
| R5.5 | Phase11-R5.5 | -70 dB floor traced to `linear_to_db()` only; causal classification safety claims purged; geometry terminology synchronized; pilot scope boundaries made explicit |
| **PREFLIGHT** | **FINAL-PREAUTHORIZATION** | Full-suite re-verification: 161/161 passed; repository state confirmed; this report produced |

---

## 3. Repository State Verification

### 3.1 Protected Artifacts

| Artifact | Expectation | Verified Status |
|---|---|---|
| `experiments/performance/exp06_positive_bce_weight/best_model.pt` | SHA-256 = `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` | ✅ EXACT MATCH |
| `data/metadata/governance_v2/rules.json` | Unchanged from governance_v2 canonical | ✅ UNTOUCHED |
| `data/metadata/governance_v2/lessons.json` | Unchanged from governance_v2 canonical | ✅ UNTOUCHED |
| `data/metadata/governance_v2/incidents.json` | Unchanged from governance_v2 canonical | ✅ UNTOUCHED |

### 3.2 Core Protocol Documents

| Document | Version | Status |
|---|---|---|
| `docs/exp08_corrected_protocol.md` | 3.4 | ✅ FROZEN — DESIGN ONLY |
| `docs/exp08_cdse_physical_compatibility_pilot.md` | 3.4 | ✅ PILOT SCOPE BOUNDED |
| `docs/exp08_spatial_overlap_r4.md` | R5.5-synchronized | ✅ GEOMETRY TERMINOLOGY CORRECT |
| `docs/exp08_cdse_route_architecture_decision.md` | Final | ✅ ROUTE B LOCKED |

### 3.3 Git Discipline

- Zero commits, zero git resets, zero git cleans, zero pushes during entire Phase 11 preflight sequence.
- All file modifications were documentation, test, and protocol harmonization only.
- No training artifacts, inference outputs, or checkpoint modifications occurred.

---

## 4. Test Suite Re-Verification

The EXP-08 guardrail test suite was re-executed in full:

```
tests/test_exp08_calibration.py                        PASSED ( 5/ 5)
tests/test_exp08_protocol_semantics.py                 PASSED (11/11)
tests/test_exp08_r3_protocol_semantics.py              PASSED (19/19)
tests/test_exp08_r4_prerequisite_closure.py            PASSED (20/20)
tests/test_exp08_r5_prerequisite_closure.py            PASSED (18/18)
tests/test_exp08_r5_1_prerequisite_closure.py          PASSED (20/20)
tests/test_exp08_r5_2_scientific_contract_closure.py   PASSED (15/15)
tests/test_exp08_r5_3_provenance_domain_closure.py     PASSED (25/25)
tests/test_exp08_r5_4_execution_readiness_closure.py   PASSED (21/21)
tests/test_exp08_r5_5_integrity_microclosure.py        PASSED ( 7/ 7)
----------------------------------------------------------------------
TOTAL: 161 passed in 0.88s  (0 failures, 0 errors, 0 skipped)
```

> [!NOTE]
> Collection errors exist in unrelated non-EXP-08 test files (`test_phase_8_p2_dataset_guardrails.py`, `test_pilot_runner.py`, `test_resume_qualification.py`) that are pre-existing from earlier phases. These files reference external dependencies or scratch fixtures not present in the clean workspace and do not affect the EXP-08 guardrail suite. All 161 EXP-08 tests passed without modification.

---

## 5. Consolidated Scientific Contract (Final Frozen State)

### 5.1 Scientific Question

> "How often does the frozen EXP-06 binary oil proposal system activate on documented DARTIS Eastern Mediterranean lookalike patches (CDSE-processed Sentinel-1 GRD data represented on the frozen Trujillo angular storage grid), and what proposal recall does the frozen system exhibit on genuine oil patches from the same external dataset — under the frozen inference contract, without threshold adjustment?"

### 5.2 Frozen Inference Contract

| Parameter | Frozen Value |
|---|---|
| Model | `best_model.pt` (SHA-256: `B5FFCCA3...`) |
| Architecture | ResNet34-UNet |
| Input channels | Ch0 = VH (cross-pol), Ch1 = VV (co-pol) — sigma0 dB after CDSE retrieval + local dB conversion |
| Threshold τ | 0.22 (frozen; no adjustment) |
| Normalization | Z-score: `(img - mean) / std` using EXP-06 training statistics |
| Tiling route | **Clamped 12-window** (`compute_tile_windows()`, ~17–19% duplicate forward passes) |
| Tile size | 512 × 512 pixels |
| Inference device | CPU (no GPU required) |

### 5.3 Calibration Chain

| Step | Operation | Notes |
|---|---|---|
| 1 | CDSE Process API request | `backCoeff: SIGMA0_ELLIPSOID`, `orthorectify: false`, `upsampling: NEAREST` |
| 2 | Output format | Float32 GeoTIFF in EPSG:4326 at Δ = 8.983152841195215e-5° |
| 3 | dB conversion (client-side) | `10 * log10(max(x, 1e-7))` via `linear_to_db()` |
| 4 | Normalization | Z-score using EXP-06 statistics |
| **FORBIDDEN** | Raw DN → ESA LUT calibration | Incompatible with Process API output (double-calibration) |

### 5.4 Spatial Contract

| Element | Definition |
|---|---|
| RETRIEVAL_DOMAIN | DARTIS AABB (axis-aligned bounding box) used for CDSE API retrieval bounds |
| PRIMARY_EVALUATION_DOMAIN | DARTIS rotated quadrilateral footprint (4-corner Polygon) |
| Mask generation | `src/ocean_sentinel/geometry.py` — rotated polygon rasterized to CDSE grid |
| Grid fidelity | Δdeg = 8.9831528e-5° (EPSG:4326), verified for 3/3 pilot scenes |
| Pixel validity | dataMask = 1 required; dataMask = 0 pixels excluded from evaluation |

### 5.5 Evaluation Domain Strata

> [!IMPORTANT]
> **Strata are defined at the PATCH level.** The unit of stratification is the unique DARTIS patch (`jpg_file`). Parent scenes are the statistical clustering unit — a single parent scene can contribute patches to both strata.

| Stratum | Definition (PATCH-LEVEL) | No-Oil Patch Count | Parent Scene Count |
|---|---|---|---|
| **Stratum 1** (Spatially Disjoint) | DARTIS no-oil patches whose rotated quadrilateral footprint has ZERO geometric intersection with any Trujillo Part I Oil raster extent | **1,501 patches** (65.55% of 2,290) | **719 unique parent scenes** |
| **Stratum 2** (Spatially Co-located) | DARTIS no-oil patches whose rotated quadrilateral footprint intersects ≥1 Trujillo Part I Oil raster extent | **789 patches** (34.45% of 2,290) | **447 unique parent scenes** |
| **Shared parent scenes** | Parent scenes contributing patches to BOTH Stratum 1 AND Stratum 2 | N/A | **297 scenes** (34.2% of 869) |

> [!IMPORTANT]
> Because 297 parent scenes contribute patches to both strata, Stratum 1 and Stratum 2 are **NOT independent scene populations**. Cross-stratum comparisons must use paired cluster-aware modeling. Do NOT describe strata as "disjoint scenes" vs "co-located scenes" — a single scene may appear in both.


---

## 6. Final Pre-Declared Limitations

The following limitations are permanently declared and non-negotiable:

1. **Trujillo Preprocessing Equivalence**: `NOT_PROVEN_WITH_CURRENT_ARTIFACTS`
   - CDSE Process API produces SIGMA0_ELLIPSOID (linear power). dB conversion is applied client-side.
   - Original Trujillo source SAFE filenames and processing timestamps are stripped in GeoTIFF files; bitwise equivalence to Trujillo's original processing pipeline cannot be independently verified.
   - This does NOT prevent EXP-08 execution under the stated design intent (CDSE Route B with client-side dB conversion).

2. **Channel Source-Truth**: `UNKNOWN` at dataset source
   - The Trujillo et al. (2021) paper is paywalled; direct confirmation of VH/VV band assignment in the published manuscript was not obtained.
   - **Operational contract is binding**: Ch0 = VH, Ch1 = VV per EXP-06 training manifest and `src/ocean_sentinel/ingestion/dataset.py`.

3. **Catalog Resolution Scope**: `SAMPLE_VERIFIED (40/1,063)`
   - 40 of 1,063 DARTIS scenes were empirically verified for 1:1 CDSE catalog match via Catalog API.
   - Remaining 1,023 scenes are unverified prior to full execution.

4. **Cross-Stratum Correlation**: `MUST_BE_MODELED`
   - Strata are **PATCH-level**: 1,501 patches in Stratum 1 (spatially disjoint), 789 patches in Stratum 2 (spatially co-located).
   - 297 parent scenes contribute patches to BOTH strata — Stratum 1 and Stratum 2 are not independent scene populations.
   - Statistical reporting must use cluster-aware methods (parent scene as resampling unit); IID reporting is forbidden.


5. **Clamped Route vs Expanded AABB Non-Equivalence**: `PRE-REGISTERED`
   - Clamped 12-window route is the frozen deterministic inference route.
   - Smart Expanded AABB (1536 × 2048) is a pre-registered alternative route with non-equivalent spatial context (different tile boundaries, different receptive field context for edge pixels).
   - **Frozen route must not be switched post-hoc based on model outputs.**

6. **-70 dB Floor**: `NUMERICAL GUARD ONLY`
   - The clamp `max(x, 1e-7)` in `linear_to_db()` prevents log₁₀(0) = -∞.
   - This applies only to CDSE linear-power → dB conversion path.
   - It is NOT present in EXP-06 training preprocessing; Trujillo GeoTIFFs were distributed in dB.
   - Classification safety from this floor is NOT independently established.

7. **No Guaranteed False Alarm Rate**:
   - EXP-08 will produce an empirical false activation rate under the frozen inference contract.
   - This rate is not pre-guaranteed to fall below any scientific threshold.

---

## 7. Execution Authorization Gate

> [!CAUTION]
> **EXECUTION_AUTHORIZED = FALSE**
>
> Scientific execution of EXP-08 requires separate, explicit, written authorization by:
> 1. **CAO (ChatGPT / Architecture Authority)**: Confirms the scientific contract meets research objectives.
> 2. **Human (Final Approval Authority)**: Provides final execution approval.
>
> This document does NOT constitute authorization. It is a readiness attestation only.

### Final Gate Matrix

| Gate Criterion | Status |
|---|---|
| A. Intended Sentinel-1 acquisition identity established (1:1 Catalog match) | ✅ SATISFIED |
| B. Process API processing contract explicit and reproducible | ✅ SATISFIED |
| C. No false operative parameter claims (downsampling inactive, speckleFilter omitted) | ✅ SATISFIED |
| D. Spatial grid compatibility demonstrated (8.98315e-5° EPSG:4326, 3/3 pilot scenes) | ✅ SATISFIED |
| E. Evaluation polygon mask is executable and deterministic | ✅ SATISFIED |
| F. R4 overlap geometry precisely defined (rotated polygon vs raster extent box) | ✅ SATISFIED |
| G. Source vs training footprint distinction explicit (1,200 source vs 840 train) | ✅ SATISFIED |
| H. Tiling route frozen; Smart Expanded AABB non-equivalence explicit | ✅ SATISFIED |
| I. -70 dB floor framed strictly as numerical guard; training trace complete | ✅ SATISFIED |
| J. Channel mapping operational contract coherent (Ch0=VH, Ch1=VV frozen) | ✅ SATISFIED |
| K. Catalog scope honestly limited (40/1,063 verified) | ✅ SATISFIED |
| L. Cross-stratum clustering interaction understood and declared | ✅ SATISFIED |
| M. DARTIS absence from EXP-06 training evidence-backed | ✅ SATISFIED |
| N. No live contradictory scientific claims remaining in repository | ✅ SATISFIED |
| O. EXP-08 guardrail test suite: 161/161 passing with zero failures | ✅ SATISFIED |
| P. Protected checkpoint SHA-256 verified exact match | ✅ SATISFIED |
| Q. Governance canonical files untouched | ✅ SATISFIED |

### **FINAL PREFLIGHT GATE:**

```
PREFLIGHT_STATUS = COMPLETE
EXECUTION_CONTRACT = FROZEN_AND_CONSISTENT
SCIENTIFIC_FIREWALL = INTACT
FINAL_GATE = READY_FOR_EXPLICIT_CAO_HUMAN_AUTHORIZATION
```

---

## 8. Anti-Loop Compliance

In strict accordance with the Anti-Loop Rule established in Phase 11-R5.5:

- No material blocker remains.
- No new broad audit phase is warranted.
- No further preparatory investigation is justified.

**All preparatory prerequisite work for EXP-08 is CONCLUDED.**

---

## 9. Required Next Action

**AWAIT formal external authorization decision** from:
1. CAO (ChatGPT / Architecture Authority)
2. Human (Final Approval Authority)

Upon receipt of written dual-authority authorization, EXP-08 may proceed under Protocol Version 3.4 with the frozen inference contract, clamped 12-window tiling route, and CDSE Route B acquisition pipeline.

**STOP.**
