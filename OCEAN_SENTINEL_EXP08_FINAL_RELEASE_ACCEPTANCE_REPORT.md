# OCEAN SENTINEL — EXP-08 FINAL RELEASE ACCEPTANCE REPORT

**Document ID**: `OCEAN_SENTINEL_EXP08_FINAL_RELEASE_ACCEPTANCE_REPORT`  
**Task ID**: `OCEAN-SENTINEL-EXP08-FINAL-RELEASE-ACCEPTANCE` / `OCEAN-SENTINEL-EXP08-FINAL-MICRO-CLOSURE`  
**Date**: 2026-10-02  
**MODEL_REQUESTED**: Claude Sonnet Thinking / Gemini 3.8 Flash High  
**MODEL_ACTUALLY_USED**: Gemini 3.8 Flash High (Antigravity IDE 2.0)  
**TOOL_ACTUALLY_USED**: Antigravity IDE 2.0  
**Authority**: ChatGPT (CAO / Architecture Authority) / Human (Final Approval Authority)

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
> - **NETWORK**: `DOCS-ONLY`
>
> Zero inference forward passes. Zero model predictions. Zero checkpoint modifications. Zero holdout access. Zero training.

---

## 1. Repository State

| Property | Value |
|---|---|
| Branch | `master` |
| HEAD | `542bab1` — `docs(audit): document Phase 3.6 scientific consistency reconciliation` |
| Staged files | NONE |
| Committed during this run | ZERO |
| Pushed during this run | ZERO |
| Reset / clean / revert | ZERO |
| Pre-existing tracked modifications | 4 files (`.gitignore`, `experiments/EXTERNAL_VALIDATION_READINESS.md`, `pyproject.toml`, `src/ocean_sentinel/ingestion/dataset.py`) — preserved, NOT modified by this run |
| Protocol Version (after this run) | **V3.5** (`EXP08_CORRECTED_PROTOCOL_V3_5`) |

---

## 2. Model / Tool Provenance

| Item | Value |
|---|---|
| MODEL_REQUESTED | Claude Sonnet Thinking |
| MODEL_ACTUALLY_USED | Gemini 3.8 Flash High (Antigravity IDE 2.0) |
| TOOL_ACTUALLY_USED | Antigravity IDE 2.0 |
| Disclosure | Claude Sonnet Thinking was unavailable. Work continued under Gemini as the only available model. Disclosed per task model-provenance rule. |

---

## 3. Protected Artifact Verification — Actual Hashes (Pre- and Post-Run)

```
OK: .gitignore
    actual=A664092C8717F70F88941DCE08D8000E29CDCB453DF9B1D64D9EEAEB3DBD0444

OK: src\ocean_sentinel\ingestion\dataset.py
    actual=F5BF1387769E43462AF8E4E4DE37867C761DD7ADBC040455532A3463EBFA0B0C

OK: src\ocean_sentinel\governance\runner.py
    actual=DD345558C3118EE61C0C966744D539C66DCFAABEAB2B9C66B03903C66EB3C9E0

OK: data\metadata\governance_v2\rules.json
    actual=B216F369D68A027E4708E8CBCF3991D8EFFD5BA5A063A3B8B6B3FC2261D85C4E

OK: data\metadata\governance_v2\lessons.json
    actual=4784A440070BC00612BC3BFA9B29A7ACC181934F894A9E22BD340FAAB7076395

OK: data\metadata\governance_v2\incidents.json
    actual=FA3051A185894EE1FE46EDB5825EBCFE92B107F80FB7527BF5746D4EC5B91836

OK: src\ocean_sentinel\temporal.py
    actual=46614361E1BE20A278D0AF9CEEE222E4787DF1EADE7D52A88B372965170E26CF

OK: experiments\performance\exp06_positive_bce_weight\best_model.pt
    actual=B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF
```

`ALL_PROTECTED_ARTIFACTS_MATCH_FINAL_ACCEPTANCE`

---

## 4. Document Control — V3.4 → V3.5

| Document | Version Before This Run | Version After This Run | Changes in This Run | Normative? |
|---|---|---|---|---|
| `docs/exp08_corrected_protocol.md` | V3.5 (from V2 closure) | **V3.5** | §1 scientific question updated: "proposal recall" → "oil-patch activation rate"; §12 section headings updated: "OIL PROPOSAL RECALL POPULATION" → "OIL PATCH ACTIVATION POPULATION" | Yes — terminology consistency |
| `docs/exp08_cdse_physical_compatibility_pilot.md` | V3.4 | **V3.4** (remains) | Added Protocol Consistency Note + BYTE-LEVEL SCOPE CLARIFICATION | Non-normative (note only) |
| `docs/exp08_spatial_overlap_r4.md` | 1.0 | 1.0 | No changes | — |
| `docs/exp08_cdse_route_architecture_decision.md` | as-is | as-is | No changes | — |

### Why pilot remains V3.4

V3.5 normative changes (§9.3 -70 dB reframing; §13.3 O1 rename; §14.1 bootstrap seed; §12 heading rename; §1 question update) do not alter any pilot procedure, API call, raster verification, or scientific finding documented in `exp08_cdse_physical_compatibility_pilot.md`. The pilot note explicitly states this. No pilot re-execution is required.

---

## 5. Physical Acquisition Identity Verification (Stage 3)

### Implementation Audit (`exp08_catalog_preflight.py`)

The physical acquisition identity resolution implements the **3-tier provenance hierarchy** via `extract_physical_acquisition_id()`:

1. **TIER 1 (Explicit Provider Linkage — Primary)**: Looks for machine-readable source product linkage (`source_product`, `source_product_id`, `origin_product_id`, or nested under `properties`). When available in CDSE catalog metadata, this is the authoritative physical acquisition ID.
2. **TIER 2 (Documented Acquisition Fields)**: For standard products (non-representation variants such as original SAFE products), the product ID itself represents the physical acquisition, validated by documented acquisition fields (`startDatetime`, `completionDatetime`, `bbox`, platform, orbit).
3. **TIER 3 (Controlled Representation Suffix Fallback)**: Suffix normalization (`_COG`, `_cog` stripping via `normalize_to_physical_id()`) is used ONLY as a controlled fallback for documented representation variants, and ONLY when the item contains valid acquisition provenance (`startDatetime`). If a representation variant lacks sufficient acquisition provenance, it is NOT merged or confirmed and yields a conservative unresolved outcome (`STATUS_INVALID_METADATA`).

**Controlled Merge Validation**:
`resolve_dartis_scene()` groups catalog items by canonical physical ID and verifies that items grouped together do not have conflicting acquisition timestamps. Conflicting timestamps prevent merge and yield `STATUS_MULTIPLE_MATCHES`.

### Case Results (All Tested & Verified)

| Case | Scenario | Result | Correct? |
|---|---|---|---|
| A | Original SAFE + documented COG representation (matching timestamps) | `physical_acquisition_count=1`, `RESOLVED_UNIQUE` | ✅ |
| B | Two genuinely different acquisitions (different orbit/product) | `physical_acquisition_count=2`, `MULTIPLE_MATCHES` | ✅ |
| C | IDs similar in string form but non-suffix difference (`_F282` vs `_F283`) | NOT merged, `MULTIPLE_MATCHES` | ✅ |
| D | COG-only record with insufficient provenance (missing acquisition timestamp) | `STATUS_INVALID_METADATA`, conservative unresolved | ✅ |
| D (pos) | COG-only record with verified acquisition provenance | `physical_acquisition_count=1`, `RESOLVED_UNIQUE` | ✅ |
| Tier 1 | Explicit machine-readable provider linkage present | Canonical physical ID from linked source product | ✅ |
| Conf | Same canonical ID base but conflicting acquisition start times | Split into distinct acquisitions, `MULTIPLE_MATCHES` | ✅ |

### Required Fields (All Present in `PreflightRecord`)

`catalog_item_count`, `physical_acquisition_count`, `representation_count`, `resolved_physical_acquisition_id`, `resolved_catalog_id`, `resolution_status`, `resolution_reason`

### Provenance Hierarchy Status

Implementation reality matches the acceptance claim:
- Tier 1 explicit machine-readable provider linkage is checked first as primary.
- Tier 2 documented product fields govern standard products.
- Tier 3 suffix normalization operates only as a controlled fallback validated by acquisition timestamps.
- Insufficient provenance on representation variants yields a conservative unresolved failure.
- Conflicting timestamps prevent false merges.


---

## 6. Execution-Gate Proof (Stage 4)

### `exp08_runner.py` — Created This Run

The file `src/ocean_sentinel/exp08_runner.py` is the ONLY permitted EXP-08 execution entry point. It enforces the mandatory control flow:

```
run_preflight()
    → enforce_preflight_gate()       ← raises PreflightFirewallError if any non-RESOLVED_UNIQUE
    → if not EXECUTION_AUTHORIZED:   ← raises ExecutionNotAuthorizedError (pre-authorization state)
    → predict_sar_image()            ← reached only with EXECUTION_AUTHORIZED=True
```

**Static proof** (position-based):
- `enforce_preflight_gate()` call is at a later position than `run_preflight()` and before `if not EXECUTION_AUTHORIZED`
- `predict_sar_image()` import and call are INSIDE the `EXECUTION_AUTHORIZED=True` block only
- `torch` / `inference` are NOT imported at module level (deferred to the authorized block)

### Gate Integration Cases (All Tested)

| Case | Scenario | Predictor Reached? | Exception Type |
|---|---|---|---|
| A | All RESOLVED_UNIQUE | Boundary reached (BLOCKED by EXECUTION_AUTHORIZED=False) | `ExecutionNotAuthorizedError` |
| B | One NO_MATCH | NEVER | `PreflightFirewallError` |
| C | One MULTIPLE_MATCHES | NEVER | `PreflightFirewallError` |
| D | QUERY_ERROR (ConnectionError) | NEVER | `PreflightFirewallError` |
| E | INVALID_METADATA (empty scene ID) | NEVER | `PreflightFirewallError` |

`EXECUTION_AUTHORIZED = False` at module definition time. Confirmed by test.

---

## 7. Isolation Proof (Stage 5 — 0 Skips)

### Torch Absence Confirmed

```
$ python -c "import torch"
ModuleNotFoundError: No module named 'torch'
```

### Subprocess Isolation Test Results

- **`test_preflight_importable_without_torch_via_subprocess`**: PASSED — subprocess with `sys.modules["torch"] = None` imports `exp08_catalog_preflight` successfully, runs `PreflightRecord` and `normalize_to_physical_id()`, prints `PREFLIGHT_ISOLATION_PASS`
- **`test_preflight_torch_absent_in_this_environment`**: PASSED — confirms torch is genuinely absent
- **`test_preflight_imports_successfully_in_this_environment`**: PASSED — direct import in current environment
- **`test_ast_no_torch_import_in_preflight`**: PASSED — AST confirms no `import torch` or `from torch` in source
- **`test_ast_no_inference_import_in_preflight`**: PASSED — AST confirms no `from ocean_sentinel.inference import` in preflight
- **`test_ast_no_forward_call_in_preflight`**: PASSED — AST confirms no `.forward()` call
- **`test_runner_defers_torch_import_until_authorized`**: PASSED — torch/inference not at runner module level

**Total isolation skips: 0**

---

## 8. Population / Denominator Verification (Stage 7 + 8)

### Population Hierarchy & Denominator Decoupling

The EXP-08 evaluation architecture strictly separates the **Scene-Level Preflight Gate** from the **Patch-Level Metric Denominator**:

1. **SCENE TARGET POPULATION (Acquisition Preflight Gate)**:
   - Target Population = 869 unique parent scenes for No-oil, 739 unique parent scenes for Oil (1,063 unique physical scenes across the full study).
   - Preflight determines whether each parent scene resolves to `RESOLVED_UNIQUE` in the CDSE catalog.
   - Purpose: An acquisition prerequisite gate that ensures full catalog traceability before inference.

2. **PATCH TARGET POPULATION (Primary L/O Evaluation Denominators)**:
   - **No-oil Target Denominator: 2,290 patches** (Stratum 1 disjoint: 1,501; Stratum 2 co-located: 789).
   - **Oil Target Denominator: 1,365 patches** (Stratum 1 disjoint: 653; Stratum 2 co-located: 712).
   - **Total Target Denominator: 3,655 patches**.
   - These patch-level denominators are immutable. An unresolved parent scene NEVER reduces the patch target population denominator.

### Frozen Population Counts (All Verified by Arithmetic + Protocol Reference)

| Cohort | Patches | Parent Scenes |
|---|---|---|
| No-oil total | 2,290 | 869 |
| No-oil Stratum 1 (disjoint) | 1,501 | 719 |
| No-oil Stratum 2 (co-located) | 789 | 447 |
| No-oil shared parent scenes | — | 297 |
| Oil total | 1,365 | 739 |
| Oil disjoint | 653 | 457 |
| Oil co-located | 712 | 422 |
| Oil shared parent scenes | — | 140 |
| Annotated oil objects | 3,225 | — |

**Arithmetic checks**: 719 + 447 − 297 = 869 ✅; 457 + 422 − 140 = 739 ✅; 1,501 + 789 = 2,290 ✅; 653 + 712 = 1,365 ✅

### Patch-Level Missingness State Machine (`PatchRecord` & `PatchManifest`)

For every target patch, the system explicitly preserves:
- `PATCH_ID`
- `PARENT_SCENE_ID`
- `STRATUM`
- `TARGET_STATUS` (`TARGET_INCLUDED`)
- `ACQUISITION_STATUS` (derived from parent scene resolution status)
- `EVALUATION_STATUS` (`EVALUATION_ELIGIBLE` or `UNRESOLVED_ACQUISITION`)
- `PREDICTION_SCORE` (`None` for unresolved patches)
- `IS_MISSING` (`True` if parent scene unresolved)

### Patch Denominator Integrity Proof (Tested & Verified)

Implemented non-scientific proof test `test_patch_level_denominator_integrity_5_patches_2_scenes`:
- **Scenario**: Scene A contains 3 target patches; Scene B contains 2 target patches (Total Target N = 5).
- **Condition**: Scene B fails catalog resolution (`NO_MATCH`).
- **Verified Behavior**:
  - Scene B is flagged as unresolved (`STATUS_NO_MATCH`).
  - Target denominator remains **N = 5** (NOT reduced to 3).
  - Explicit missingness accounting records `evaluation_eligible_patches = 3` and `unresolved_or_invalid_patches = 2`.
  - The 2 patches belonging to Scene B have `is_missing = True` and `evaluation_status = UNRESOLVED_ACQUISITION`.
  - **Zero Imputation Prohibited**: Unresolved patches are **NOT** converted into scientific zero scores (`prediction_score is None`, `prediction_score != 0.0`).
  - `enforce_preflight_gate()` message explicitly prohibits post-hoc denominator adjustment.


---

## 9. Geometry Verification (Stage 7)

| Property | Verified State |
|---|---|
| Primary scientific entity | DARTIS PATCH |
| Statistical cluster | parent Sentinel-1 SCENE |
| Stratification geometry | DARTIS rotated quadrilateral ∩ Trujillo raster extent polygon |
| Retrieval geometry | DARTIS AABB (acceptable for catalog query, NOT for stratum membership) |
| AABB as primary stratum | NOT permitted |
| Source footprint | Tracked separately from training footprint |
| `SOURCE_FOOTPRINT_OVERLAP` ≠ `TRAINING_SOURCE_FOOTPRINT_OVERLAP` | Verified in protocol |

---

## 10. Metric Terminology Verification (Stage 6)

| Location | Old Terminology | New Terminology | Status |
|---|---|---|---|
| Protocol §1 scientific question | "proposal recall" | "**oil-patch activation rate**" | ✅ FIXED this run |
| Protocol §12 section heading | "OIL PROPOSAL RECALL POPULATION" | "**OIL PATCH ACTIVATION POPULATION**" | ✅ FIXED this run |
| Protocol §12 cohort heading | "Oil Proposal Recall Cohorts" | "**Oil Patch Activation Cohorts**" | ✅ FIXED this run |
| Protocol §13.3 METRIC-O1 | "Patch Recall Rate" | "**Oil-Patch Activation Rate**" | ✅ Already fixed in V2 |
| Protocol §13.3 METRIC-O3 | — | "**Oil-Object Bounding-Box Hit Rate**" | ✅ Already fixed in V2 |
| Pilot doc | N/A | No O1 metric definition present | ✅ CLEAN |

No unqualified "proposal recall" or "Patch Recall Rate" remains as a positive metric definition in any living scientific document.

---

## 11. -70 dB Verification (Stage 9)

| Claim | Status |
|---|---|
| "total signal extinction" | REMOVED — appears only in CAUTION block as prohibited phrase |
| "physical extinction" | NOT FOUND in any living document |
| "safely saturate" | NOT FOUND |
| "classification safety" | Present only as "not independently established" (negated) |
| "numerical guard only" | PRESENT — correct framing |
| CAUTION block in §9.3 | PRESENT — explicit prohibition |
| Training path (already-dB Trujillo data) | Documented as no additional floor applied |
| Route B: `10·log10(max(x, 1e-7))` | Single path confirmed |
| Double calibration | NOT present |

---

## 12. Route-B Calibration Verification (Stage 9)

```
CDSE Process API → sentinel-1-grd → SIGMA0_ELLIPSOID (linear power)
    → local 10·log10(max(x, 1e-7)) [implemented in calibration.py]
    → dB [Ch0=VH cross-pol, Ch1=VV co-pol]
    → EXP-06 z-score normalization (Mapping A contract)
```

Single path only. No ESA LUT after Process API. No double calibration. Verified in protocol §9 and `calibration.py`.

---

## 13. Bootstrap Determinism Verification (Stage 11)

| Parameter | Protocol V3.5 |
|---|---|
| Method | Cluster bootstrap |
| Replicates | 10,000 |
| CI | 95% percentile |
| Seed | **`20260927`** (pre-declared before execution) |
| RNG implementation | `numpy.random.default_rng(20260927)` |
| Resampling unit | Parent scene |
| IID patch bootstrap | PROHIBITED |
| Shared no-oil scenes (297) | Jointly represented in both strata |
| Shared oil scenes (140) | Same principle |
| Execution-time seed choice | PROHIBITED |
| Post-hoc method choice | PROHIBITED |

---

## 14. Contradiction Sweep Classification (Stage 12 / 13)

| Term / Phrase | Document | Classification | Status |
|---|---|---|---|
| "proposal recall" (§1 question) | Protocol | Was ASSERTION → now FIXED | ✅ RESOLVED |
| "Oil-patch activation rate" (§1 question) | Protocol | CORRECT ASSERTION | ✅ |
| "OIL PATCH ACTIVATION POPULATION" (§12) | Protocol | CORRECT ASSERTION | ✅ |
| "total signal extinction" | Protocol §9.3 | PROHIBITION (CAUTION block) | ✅ CLEAN |
| "classification safety from this floor" | Protocol | NEGATED ("not independently established") | ✅ CLEAN |
| "byte-level compatibility" | Pilot, Historical report | DESCRIPTION (format/storage) + BYTE-LEVEL SCOPE CLARIFICATION note | ✅ CLEAN |
| "bitwise equivalence" | Historical report | HISTORICAL — paired with "cannot be independently verified" | ✅ CLEAN |
| "catalog_candidate_count" | V2 report (historical), V2 tests | HISTORICAL / PROHIBITION context only; AST confirms not in executable code | ✅ CLEAN |
| "segmentation IoU" | Protocol | PROHIBITION | ✅ CLEAN |
| "Patch Recall Rate" | Protocol §13.3 | NOT-called list only (prohibition) | ✅ CLEAN |
| "execution-time seed" | Protocol §14 | PROHIBITION | ✅ CLEAN |
| "2,468" / "3,047" / "5,515" | r4 doc | SUPERSEDED notice | ✅ CLEAN |
| "unclustered confidence interval" | Protocol | PROHIBITION | ✅ CLEAN |
| "linear polarization" | Protocol | NOT present as channel descriptor | ✅ CLEAN |
| "2,290 independent" | Protocol | NOT present as assertion; prohibition present | ✅ CLEAN |
| "100% resolvable" | All docs | NOT FOUND | ✅ CLEAN |
| "filled bounding box" | All docs | NOT FOUND | ✅ CLEAN |
| "bounding box has zero intersection" as stratum | All docs | NOT FOUND | ✅ CLEAN |
| "NOT_PROVEN_WITH_CURRENT_ARTIFACTS" | Protocol, Pilot | PRESENT — correctly maintained | ✅ CLEAN |

---

## 15. Test Results

```
tests/test_exp08_calibration.py                            PASSED   ( 7/  7)
tests/test_exp08_protocol_semantics.py                     PASSED   (14/ 14)
tests/test_exp08_r3_protocol_semantics.py                  PASSED   (26/ 26)
tests/test_exp08_r4_prerequisite_closure.py                PASSED   (29/ 29)
tests/test_exp08_r5_prerequisite_closure.py                PASSED   (11/ 11)
tests/test_exp08_r5_1_prerequisite_closure.py              PASSED   (14/ 14)
tests/test_exp08_r5_2_scientific_contract_closure.py       PASSED   (17/ 17)
tests/test_exp08_r5_3_provenance_domain_closure.py         PASSED   (15/ 15)
tests/test_exp08_r5_4_execution_readiness_closure.py       PASSED   (21/ 21)
tests/test_exp08_r5_5_integrity_microclosure.py            PASSED   ( 7/  7)
tests/test_exp08_final_corrective_closure.py               PASSED   (46/ 46)
tests/test_exp08_final_corrective_closure_v2.py            PASSED   (71/ 71)
tests/test_exp08_final_release_acceptance.py               PASSED   (88/ 88)
─────────────────────────────────────────────────────────────────────────────
TOTAL: 366 passed, 0 skipped, 0 failed, 0 errors
```

**Arithmetic Reconciliation**: 7 + 14 + 26 + 29 + 11 + 14 + 17 + 15 + 21 + 7 + 46 + 71 + 88 = 366 ✅.
**Skips: ZERO.** All acceptance requirements are positively proven, including the preflight isolation requirement.

### `catalog_candidate_count` Stale Reference Audit

AST scan of all `test_exp08*.py` files: no executable code (keyword arguments, attribute accesses) uses `catalog_candidate_count`. The field appears only in docstring/comment context in the acceptance test as a historical reference. **CLEAN**.

---

## 16. Protected Artifact Post-Check

```
.gitignore                                           A664092C...  OK
src/ocean_sentinel/ingestion/dataset.py              F5BF1387...  OK
src/ocean_sentinel/governance/runner.py              DD345558...  OK
data/metadata/governance_v2/rules.json               B216F369...  OK
data/metadata/governance_v2/lessons.json             4784A440...  OK
data/metadata/governance_v2/incidents.json           FA3051A1...  OK
src/ocean_sentinel/temporal.py                       46614361...  OK
experiments/performance/exp06_positive_bce_weight/best_model.pt  B5FFCCA3...  OK

ALL_PROTECTED_ARTIFACTS_MATCH_FINAL_ACCEPTANCE
```

**git status**: 0 staged, 0 committed, 0 pushed. Pre-existing 4-file modification preserved.

---

## 17. Files Created/Modified by This Acceptance Run

| File | Action | Description |
|---|---|---|
| `docs/exp08_corrected_protocol.md` | Modified | §1: "proposal recall" → "oil-patch activation rate"; §12: section headings updated |
| `docs/exp08_cdse_physical_compatibility_pilot.md` | Modified | Protocol Consistency Note + BYTE-LEVEL SCOPE CLARIFICATION added |
| `src/ocean_sentinel/exp08_catalog_preflight.py` | Modified | 3-tier provenance hierarchy (`extract_physical_acquisition_id`); timestamp conflict check; `PatchRecord`, `PatchManifest`, `build_patch_manifest` |
| `src/ocean_sentinel/exp08_runner.py` | **Created** | Canonical EXP-08 gated execution entry point |
| `tests/test_exp08_final_release_acceptance.py` | **Created** | 88-test acceptance verification suite (0 skips; includes Cases A–D & patch denominator integrity proof) |
| `scratch/ocean_sentinel_final_exp08_corrective_closure_lessons.md` | Modified | CC-7 provenance hierarchy rewritten; CC-8 "essential rule" framing; CC-10 added |
| `scratch/ocean_sentinel_exp08_final_micro_closure_progress.md` | **Created** | Micro-closure live telemetry tracker |
| `OCEAN_SENTINEL_EXP08_FINAL_RELEASE_ACCEPTANCE_REPORT.md` | **Updated** | This reconciled acceptance report |

`data/metadata/governance_v2/lessons.json` was **NOT modified**.

---

## 18. Candidate Lessons Status

Ten lessons in [`scratch/ocean_sentinel_final_exp08_corrective_closure_lessons.md`](file:///d:/Projects/ocean-sentinel/scratch/ocean_sentinel_final_exp08_corrective_closure_lessons.md):

| Lesson | Status |
|---|---|
| CL-EXP08-CC-1 through CC-6 | Preserved from prior closure |
| CL-EXP08-CC-7 (Catalog item count ≠ physical acquisition count) | **Updated** — 3-tier provenance hierarchy; explicit "Do NOT merge" rules |
| CL-EXP08-CC-8 (Bootstrap requires pre-declared deterministic seed) | **Updated** — "Essential rule" framing; date-based seed no longer claimed as universally preferred |
| CL-EXP08-CC-9 (Patch Recall Rate terminology) | Preserved from V2 closure |
| CL-EXP08-CC-10 (Scene preflight vs patch denominator decoupling) | **Created** — Patch denominator immutable under scene preflight resolution failures |

`governance_v2/lessons.json`: **NOT modified** (hash matches).

---

## 19. Remaining Declared Limitations

The following evidence limitations remain valid, documented, and **acceptable** — they do not make EXP-08 methodologically undefined.

1. **Trujillo Preprocessing Equivalence**: `NOT_PROVEN_WITH_CURRENT_ARTIFACTS`. Trujillo source rasters have no embedded provenance. Route-B numerical values cannot be proven identical to Trujillo training data without a calibrated external reference. This limitation is not upgraded by byte-level format verification.

2. **Channel Source-Truth**: VERIFIED_WITH_LIMITATIONS — EXP-06 operational contract (Ch0=VH, Ch1=VV) is binding. Trujillo dataset-source channel provenance remains UNKNOWN at source.

3. **Catalog Full-Population Resolution**: 40/1,063 scenes explicitly confirmed; 1,023 extrapolated from sample. Extrapolation requires caution.

4. **Cross-Stratum Statistical Independence**: 297 shared no-oil parent scenes and 140 shared oil parent scenes require paired cluster-aware modeling. Spatial non-overlap does NOT prove statistical independence.

5. **dataMask is not an ocean/land classifier**: Valid pixels include both ocean and land. No ocean masking is applied beyond the primary evaluation quadrilateral.

6. **-70 dB Classification Safety**: Not independently established. The floor is a numerical guard, not a proven safe-activation threshold.

7. **Physical Acquisition Provenance (implementation reality)**: `extract_physical_acquisition_id()` implements the 3-tier hierarchy: Tier 1 explicit provider source-product linkage (primary); Tier 2 documented product identity; Tier 3 controlled representation suffix fallback validated against matching acquisition timestamps. Insufficient provenance yields conservative unresolved outcomes.

---

## 20. Acceptance Gate Criterion Matrix

| # | Criterion | Evidence | Status |
|---|---|---|---|
| 1 | Physical acquisition identity is provenance-safe | 3-tier hierarchy in `extract_physical_acquisition_id()`; Cases A–D proven by tests | ✅ |
| 2 | COG/original representations cannot create false multiplicity | `normalize_to_physical_id()` + `physical_acquisition_count==1` check | ✅ |
| 3 | Genuine distinct acquisitions cannot be merged | Cases B & C tested; timestamp conflict validation tested | ✅ |
| 4 | Real EXP-08 inference entry is gated by preflight | `exp08_runner.py` enforces full call-graph | ✅ |
| 5 | Unresolved catalog scenes cannot reach inference | Cases B–E: `PreflightFirewallError` raised before predictor | ✅ |
| 6 | Isolation test is positively proven (not skipped) | 7 isolation tests, 0 skips, subprocess proof | ✅ |
| 7 | Population denominators remain frozen | Patch-level denominators frozen (N=2,290 no-oil, N=1,365 oil, total N=3,655); 5-patch/2-scene test proves decoupling | ✅ |
| 8 | Missingness cannot become scientific zero | `PatchRecord` prediction_score remains None for unresolved acquisitions; test verifies prediction_score != 0.0 | ✅ |
| 9 | Primary stratification uses quadrilateral geometry | Protocol §12 verified | ✅ |
| 10 | O1 terminology globally consistent | Scientific question + §12 headings + §13.3 all updated | ✅ |
| 11 | O3 terminology globally consistent | "Oil-Object Bounding-Box Hit Rate" confirmed | ✅ |
| 12 | -70 dB has no unsupported physical/safety interpretation | Physical assertion removed; CAUTION block present | ✅ |
| 13 | Route-B calibration is single-path | One calibration path confirmed; no double calibration | ✅ |
| 14 | Byte-level language does not imply radiometric equivalence | BYTE-LEVEL SCOPE CLARIFICATION added to pilot | ✅ |
| 15 | Bootstrap method and seed are frozen | Seed `20260927`, `numpy.random.default_rng(20260927)`, pre-declared | ✅ |
| 16 | Shared-scene clustering is preserved | 297 no-oil, 140 oil shared scenes explicitly documented | ✅ |
| 17 | Protocol/pilot/report versions are consistent | Protocol V3.5; Pilot V3.4 with V3.5 consistency note | ✅ |
| 18 | All required EXP-08 tests pass | 366/366 passed, 0 skipped | ✅ |
| 19 | Protected artifacts are bit-for-bit intact | 8/8 hashes match | ✅ |
| 20 | `EXECUTION_AUTHORIZED` remains `False` | Module-level constant verified by test | ✅ |

---

## 21. Material Blockers

```
MATERIAL_BLOCKER_REMAINS = NONE
```

All 20 acceptance gate criteria are satisfied. No issue requires new scientific evidence, new experimental data, a new methodological assumption, or changes to the frozen checkpoint.

---

## 22. Final Gate

```
TASK_ID:                    OCEAN-SENTINEL-EXP08-FINAL-MICRO-CLOSURE
STATUS:                     COMPLETE
MODEL_REQUESTED:            Claude Sonnet Thinking
MODEL_ACTUALLY_USED:        Gemini 3.8 Flash High (Antigravity IDE 2.0)
TOOL_ACTUALLY_USED:         Antigravity IDE 2.0
PROTOCOL_VERSION:           V3.5 (EXP08_CORRECTED_PROTOCOL_V3_5)
TOTAL_TESTS:                366 passed, 0 skipped, 0 failed, 0 errors
NEW_TESTS_ADDED:            88 (test_exp08_final_release_acceptance.py)
EXECUTION_AUTHORIZED:       FALSE
INFERENCE:                  NO
TRAINING:                   NO
HOLDOUT:                    NOT_ACCESSED
PART_III:                   NOT_ACCESSED
GPU:                        NO
NETWORK:                    DOCS-ONLY
MATERIAL_BLOCKERS:          NONE
FINAL_GATE:                 READY_FOR_EXPLICIT_CAO_HUMAN_AUTHORIZATION
```


---

## 23. Next Required Action

**AWAIT formal dual-authority authorization from:**

1. **CAO (ChatGPT / Architecture Authority)** — explicit written authorization
2. **Human (Final Approval Authority)** — explicit written authorization

Upon both written authorizations, EXP-08 may proceed under:
- Protocol **V3.5** (`EXP08_CORRECTED_PROTOCOL_V3_5`)
- `exp08_runner.py` as the ONLY permitted execution entry point
- `enforce_preflight_gate()` must pass before ANY inference forward pass
- Bootstrap seed `20260927` (`numpy.random.default_rng(20260927)`)
- METRIC-O1 = Oil-Patch Activation Rate (NOT Patch Recall Rate, NOT proposal recall)
- METRIC-O3 = Oil-Object Bounding-Box Hit Rate (NOT segmentation IoU)
- `EXECUTION_AUTHORIZED` must be flipped to `True` only after written dual authorization is received

**STOP.**
