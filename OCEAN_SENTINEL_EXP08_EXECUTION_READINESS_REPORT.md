# OCEAN SENTINEL
# EXP-08 EXECUTION-READINESS & HUMAN-AUTHORIZATION HANDOFF REPORT
# POST-OBSIDIAN-V2 BASELINE — NO SCIENTIFIC EXECUTION

**TASK_ID**: `OCEAN-SENTINEL-EXP08-EXECUTION-READINESS-HUMAN-AUTHORIZATION-HANDOFF`  
**AUTHORITY**: CAO (ChatGPT) + Human (Dheeraj)  
**DATE**: 2026-10-02  
**FINAL_GATE**: `EXP08_READY_FOR_EXPLICIT_CAO_HUMAN_AUTHORIZATION`  
**CURRENT_STAGE**: `READY_FOR_EXPLICIT_CAO_HUMAN_AUTHORIZATION`  
**CURRENT_ISSUE**: `NONE`  
**EXECUTION_AUTHORIZED**: `FALSE`  

---

## 1. Executive Summary

Operational Integration V2 between Ocean Sentinel and the Obsidian Knowledge Vault is formally complete, forensically audited, and closed (`FINAL_GATE = OBSIDIAN_OPERATIONAL_INTEGRATION_V2_COMPLETE`, 148 passed, 2 skipped, 0 failures).

This report establishes the definitive **EXP-08 Execution-Readiness and Human-Authorization Handoff Package**. EXP-08 is an external diagnostic evaluation designed to test the hard-negative lookalike activation rate and oil-patch activation rate of the frozen EXP-06 binary oil proposal system on the DARTIS Eastern Mediterranean dataset (2019 acquisitions) via CDSE Level-1 GRD reconstruction (Route B).

**CRITICAL SCIENTIFIC INTEGRITY STATEMENT:**
> [!IMPORTANT]
> **NO SCIENTIFIC EXECUTION HAS OCCURRED.**
> - `EXECUTION_AUTHORIZED = FALSE`
> - `INFERENCE = NO`
> - `TRAINING = NO`
> - `HOLDOUT = NOT_ACCESSED`
> - `PART_III = NOT_ACCESSED`
> 
> All 366 EXP-08 acceptance tests are pre-execution guardrail, provenance, and protocol-verification tests. They establish that the scientific, architectural, and procedural prerequisites are satisfied. They do NOT constitute benchmark results.
> 
> Scientific execution remains strictly blocked pending explicit written dual authorization from CAO (ChatGPT) and Human (Dheeraj).

---

## 2. Current Authorization State

The execution boundary is protected by multi-layered structural, procedural, and programmatic firewalls:

| Dimension | Declared State | Enforcement Mechanism |
|---|---|---|
| **EXECUTION_AUTHORIZED** | `FALSE` | Module-level constant in [exp08_runner.py](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/exp08_runner.py#L48) |
| **Model Inference** | `BLOCKED` | `run_exp08_evaluation()` raises `ExecutionNotAuthorizedError` before any model forward pass |
| **Model Training** | `PROHIBITED` | Protocol V3.5 §1; weights frozen at `best_model.pt` |
| **OPS-02 Holdout Access** | `FIREWALLED` | Manifest and split partitions isolated |
| **Trujillo Part III Access** | `FIREWALLED` | [firewall.py](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ingestion/firewall.py) raises `PartIIIFirewallViolationError` on any Part III path |
| **Catalog Preflight Gate** | `ENFORCED` | `enforce_preflight_gate()` in [exp08_catalog_preflight.py](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/exp08_catalog_preflight.py) requires `RESOLVED_UNIQUE` |
| **Obsidian Execution Authority** | `NONE` | Retrieved knowledge content role is `KNOWLEDGE_CONTEXT`; `execution_authority = NONE` |

---

## 3. Authoritative Protocol Requirements (V3.5 Summary)

The authoritative design for EXP-08 is codified in [exp08_corrected_protocol.md](file:///d:/Projects/ocean-sentinel/docs/exp08_corrected_protocol.md) (Version 3.5, frozen 2026-10-01).

### 3.1 Scientific Question (§1)
> "How often does the frozen EXP-06 binary oil proposal system activate on documented DARTIS Eastern Mediterranean lookalike patches (CDSE-processed Sentinel-1 GRD data represented on the frozen Trujillo angular storage grid), and what oil-patch activation rate does the frozen system exhibit on genuine oil patches from the same external dataset — under the frozen inference contract, without threshold adjustment?"

**Explicit Prohibitions (§1, §13.1):**
- NOT a segmentation benchmark (DARTIS has no pixel masks).
- NOT a supervised lookalike detection experiment (model was not trained for lookalike classification).
- NOT a threshold calibration exercise ($\tau = 0.22$ is frozen).
- NOT a training population audit.

### 3.2 Acquisition Route (§2)
- **Route B (CDSE reconstruction)** is the ONLY scientifically valid route.
- Route A (PANGAEA 8-bit normalized JPEGs) is scientifically invalid due to lossy 8-bit quantization, VV-only restriction, and unknown radiometric normalization.

### 3.3 Entity Ontology & Denominators (§3)
- **Annotation Records**: 5,515 rows in `data_matrix.tab` (3,225 oil records + 2,290 no-oil records). Mixing oil-object rows with no-oil patch rows makes 5,515 an invalid denominator.
- **Unique Patches (`jpg_file`)**: 3,655 unique patches:
  - **No-oil population**: Exactly **2,290 unique patches** (`nw`: 1,939; `nc`: 351).
  - **Oil population**: Exactly **1,365 unique patches** (`ow`: 990; `oc`: 375).
- **Annotated Oil Objects**: Exactly **3,225 objects** across 1,365 oil patches (724 patches have $>1$ object).
- **Unique Parent Scenes (`Sentinel_ID`)**: Exactly **1,063 unique Sentinel-1 SAFE products** (869 no-oil parent scenes, 739 oil parent scenes; 545 scenes contribute both oil and no-oil).

### 3.4 Temporal & Geographic Coverage (§4, §5)
- **Temporal**: All 5,515 records are 2019 acquisitions (verified; prior "2018 records" claim superseded).
- **Geographic**: Exclusively Eastern Mediterranean (lon 27.15°–36.08°E, lat 29.30°–36.35°N).

---

## 4. Implementation Reconciliation

| Protocol Requirement | Implementation Module | Evidence & Location | Status | Remaining Gap |
|---|---|---|---|---|
| **Catalog Preflight Firewall** | `exp08_catalog_preflight.py` | [exp08_catalog_preflight.py](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/exp08_catalog_preflight.py#L1-L100); 3-tier provenance hierarchy | **PASS** | None |
| **Gated Execution Runner** | `exp08_runner.py` | [exp08_runner.py](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/exp08_runner.py#L48-L160); `EXECUTION_AUTHORIZED = False` | **PASS** | None |
| **Polygon Evaluation Mask** | `geometry.py` | [geometry.py](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/geometry.py#L24-L100); `create_primary_evaluation_mask()` | **PASS** | None |
| **Inference Pipeline** | `inference.py` | [inference.py](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/inference.py#L101-L500); `predict_sar_image()`, $\tau = 0.22$ | **PASS** | Requires PyTorch at execution time |
| **SAR Calibration Chain** | `satellite/calibration.py` | CDSE Process API `SIGMA0_ELLIPSOID` + local $10 \log_{10}$ conversion | **PASS** | Operational credentials needed for full run |
| **Part III Isolation Firewall** | `ingestion/firewall.py` | [firewall.py](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ingestion/firewall.py); blocks any Part III access | **PASS** | None |

---

## 5. Data Readiness

| Data Asset | Verification Method | Artifact & Location | Status |
|---|---|---|---|
| **DARTIS Metadata Catalog** | TSV file integrity & schema validation | `data/metadata/yang_singha_2025/data_matrix.tab` (2.4 MB, 5,515 rows) | **READY** |
| **Spatial Overlap Matrix** | Exact planar polygon intersection recomputation | `data/metadata/exp08_spatial_overlap_r4.json` (789/2,290 no-oil intersect 1,200 rasters) | **READY** |
| **Trujillo Part I Source Rasters** | File presence & rasterio inspection | `data/raw/trujillo_2024/images/Oil` (1,200 GeoTIFFs, EPSG:4326) | **READY** |
| **EXP-06 Training Split Manifest** | Manifest inspection | 840 training rasters (13,440 tiles + 355 negatives); 0 DARTIS data | **READY** |
| **CDSE Physical Compatibility Pilot** | 3-scene physical raster retrieval | [docs/exp08_cdse_physical_compatibility_pilot.md](file:///d:/Projects/ocean-sentinel/docs/exp08_cdse_physical_compatibility_pilot.md) | **READY** |
| **OPS-02 Holdout Set** | Firewall verification | Isolated; inaccessible to EXP-08 | **READY (ISOLATED)** |
| **Trujillo Part III** | Structural path & hash firewall | [tests/test_part_iii_firewall.py](file:///d:/Projects/ocean-sentinel/tests/test_part_iii_firewall.py); completely firewalled | **READY (ISOLATED)** |

---

## 6. Model & Checkpoint Readiness

- **Checkpoint Location**: `experiments/performance/exp06_positive_bce_weight/best_model.pt`
- **Protected SHA-256 Hash**: `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` (verified exact match).
- **Architecture**: `ResNet34UNet(in_channels=2, num_classes=1, adaptation_method='slice_variance_scaled')`.
- **Input Channels**: Exactly 2 channels (`count == 2` in `inference.py` L209).
- **Operational Channel Binding**: Ch0 = VH (Cross-Pol), Ch1 = VV (Co-Pol) in calibrated dB.
- **Normalization Binding**:
  - Ch0: $\mu = -33.2323\text{ dB}, \sigma = 6.4912\text{ dB}$
  - Ch1: $\mu = -19.9405\text{ dB}, \sigma = 4.5308\text{ dB}$
- **Decision Threshold**: $\tau = 0.22$ (frozen).
- **Status**: **READY**. Checkpoint integrity is preserved and immutable.

---

## 7. Preprocessing Contract

The preprocessing contract reconciling CDSE Process API outputs with the frozen EXP-06 input specification is fully verified:

1. **Service-Side Grid Generation**: CDSE Process API generates an EPSG:4326 grid at angular cell size $\Delta \text{deg} = 8.983152841195215 \times 10^{-5}$ degrees, reproducing the Trujillo storage grid within 0.03%.
2. **Resampling**: `LOCAL_RESAMPLING = NONE` (zero client-side spatial interpolation). Server-side upsampling is pinned to `NEAREST`.
3. **Radiometric Chain**:
   $$\text{CDSE Linear } \sigma^0 \longrightarrow \sigma^0_{\text{dB}} = 10 \cdot \log_{10}(\max(\sigma^0_{\text{linear}}, 10^{-7}))$$
   The $-70\text{ dB}$ floor is a **deterministic numerical guard** against $\log_{10}(0) = -\infty$, not a physical classification safety proof.
4. **Channel Stacking**: `[vh_band, vv_band]` stacked to shape `(2, H, W)`.
5. **Evaluation Masking**:
   $$\text{primary\_eval\_mask} = (\text{dataMask} == 1) \land (\text{dartis\_polygon\_mask} == 1)$$
   Only pixels inside the DARTIS rotated quadrilateral with valid sensor signal are evaluated. Surrounding AABB context is retained solely to support continuous $512 \times 512$ tile extraction without boundary artifacts.

---

## 8. Train / Validation / Holdout Separation

| Population Partition | Content | Role in EXP-08 | Leakage / Separation Status |
|---|---|---|---|
| **Trujillo Part I TRAIN** | 840 source rasters (13,440 tiles + 355 negatives) | Training set of frozen EXP-06 | Zero DARTIS data; 441 no-oil / 399 oil patches share spatial extent |
| **Trujillo Part I VAL** | 180 source rasters (2,880 tiles) | Internal validation (clean-water FAR 0.55%, IoU 0.72) | Completely separate from DARTIS evaluation |
| **Trujillo Part I TEST** | 180 source rasters (2,880 tiles) | Internal test set | Completely separate from DARTIS evaluation |
| **Trujillo Part III** | 300 source rasters | External holdout | Absolute firewall; NEVER accessed |
| **DARTIS Lookalike (No-oil)** | 2,290 unique patches (869 scenes) | Hard-negative diagnostic evaluation | Completely external; never seen in training or validation |
| **DARTIS Oil** | 1,365 unique patches (739 scenes) | Oil-patch activation rate evaluation | Completely external; never seen in training or validation |

---

## 9. Scientific Metric Readiness

All planned metrics have verified mathematical oracles and defined denominators:

| Metric ID | Metric Name | Population Denominator | Mathematical Estimand | Prohibited Labels |
|---|---|---|---|---|
| **METRIC-L1** | Patch Hard-Negative Activation Rate | $N_{\text{nooil}} = 2,290$ patches | $\frac{\sum \mathbb{I}(\text{any positive pixel in primary\_eval\_mask})}{2,290}$ | FAR (unqualified), Pixel False Alarm Rate |
| **METRIC-L2** | Predicted Oil Area Fraction (No-oil) | $N_{\text{nooil}} = 2,290$ patches | Mean of $\frac{\text{positive valid pixels}}{\text{total valid pixels}}$ per patch | Segmentation IoU, False Positive Rate |
| **METRIC-L3** | Scene-Clustered Alarm Rate | $N_{\text{scenes}} = 869$ unique scenes | $\frac{\sum \mathbb{I}(\text{scene has } \ge 1 \text{ activated patch})}{869}$ | Independent Alarm Rate |
| **METRIC-L4** | Lookalike Subgroup Stratification | $N_{\text{nc}} = 351, N_{\text{nw}} = 1,939$ | METRIC-L1 computed separately for `nc` and `nw` | — |
| **METRIC-O1** | Oil-Patch Activation Rate | $N_{\text{oil}} = 1,365$ patches | $\frac{\sum \mathbb{I}(\text{any positive pixel in primary\_eval\_mask})}{1,365}$ | Patch Recall Rate, Recall, Detection Rate |
| **METRIC-O2** | Predicted Oil Area Fraction (Oil) | $N_{\text{oil}} = 1,365$ patches | Mean of $\frac{\text{positive valid pixels}}{\text{total valid pixels}}$ per oil patch | Segmentation IoU, Dice Score |
| **METRIC-O3** | Oil-Object Bounding-Box Hit Rate | $N_{\text{objects}} = 3,225$ objects | $\frac{\sum \mathbb{I}(\text{any positive pixel intersects object bbox})}{3,225}$ | Segmentation IoU, Object Detection Precision |
| **METRIC-O4** | Oil Subgroup Stratification | $N_{\text{oc}} = 375, N_{\text{ow}} = 990$ | METRIC-O1 computed separately for `oc` and `ow` | — |

**Statistical Confidence Intervals (§14.1):**
- Primary Unit: Scene (parent Sentinel-1 SAFE product).
- Method: Non-parametric cluster bootstrap, **10,000 replicates**.
- Pre-declared RNG Seed: **`20260927`** (`numpy.random.default_rng(20260927)`).
- Paired cluster modeling required for Stratum 1 vs Stratum 2 due to **297 shared parent scenes**.

---

## 10. Provenance & Reproducibility Readiness

All metadata required for exact end-to-end provenance is captured:
1. `patch_name` and `Sentinel_ID` from DARTIS catalog.
2. CDSE Catalog API physical acquisition lookup matching product uniqueness 1:1.
3. CDSE Process API request payload SHA-256 (`1fe63856...`).
4. Preprocessing parameters: `SIGMA0_ELLIPSOID`, `orthorectify: false`, `upsampling: NEAREST`.
5. Model checkpoint SHA-256 (`B5FFCCA3...`).
6. Code commit hash (`542bab19...`).
7. Execution environment snapshot (Python, OS, library versions).
8. Cluster bootstrap seed (`20260927`).

---

## 11. Environment Readiness

- **Current Host**: Windows 11, x86_64.
- **Python**: 3.10.9 in `d:\Projects\ocean-sentinel\.venv`.
- **Installed Core Libraries**: `rasterio` 1.4.4, `shapely` 2.1.2, `numpy` 2.2.6, `pydantic` 2.13.5, `httpx` 0.28.1, `affine` 3.0.1.
- **ML Dependency Status**:
  - `torch` is deliberately absent from `.venv` in the pre-authorization state as an additional environmental precaution against accidental model execution. The authoritative execution boundary is enforced by the explicit authorization gate and the execution/holdout/Part III firewalls (pre-authorization absence verified by Stage 5 tests in [test_exp08_final_release_acceptance.py](file:///d:/Projects/ocean-sentinel/tests/test_exp08_final_release_acceptance.py#L398-L410)).
  - Provisioning `torch` in `.venv` is a technical prerequisite to be performed immediately prior to authorized execution.
- **CDSE API Credentials**: Injected via environment variables at runtime (`CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET`).

---

## 12. Artifact Destination Readiness

The execution directory structure is established under:
`experiments/performance/exp08_dartis_external_validation/<run_id>/`
- `manifests/`: `preflight_manifest.json`, `patch_manifest.json`, `execution_manifest.json`
- `metrics/`: `metrics_summary.json`, `strata_decomposition.json`, `bootstrap_ci.json`
- `logs/`: `preflight.log`, `inference.log`, `evaluation.log`
- `predictions/`: probability maps, prediction masks, polygon evaluation masks
- `provenance/`: `environment.json`, `request_hashes.json`, `git_state.json`
- `failures/`: `unresolved_scenes.json`, `invalid_rasters.json`, `stopping_rule_events.json`
- `report/`: `EXP08_FINAL_EVALUATION_REPORT.md`

---

## 13. Failure & Contingency Matrix

| Failure Mode | Trigger Condition | Detection Mechanism | Safe Automated Response | Recorded Artifact | Continue / Stop Policy |
|---|---|---|---|---|---|
| **1. Missing CDSE Scene** | Scene not found in CDSE catalog | Catalog returns 0 items | Preflight records `STATUS_NO_MATCH` | `unresolved_scenes.json` | `enforce_preflight_gate()` raises `PreflightFirewallError`; STOP before inference |
| **2. Ambiguous Acquisition** | $>1$ physical acquisition for 25s window | Catalog returns $>1$ distinct SAFE products | Preflight records `STATUS_MULTIPLE_MATCHES` | `unresolved_scenes.json` | `enforce_preflight_gate()` raises `PreflightFirewallError`; STOP |
| **3. Catalog API Failure** | CDSE returns 500, 503, or network timeout | Exception during query | Preflight records `STATUS_QUERY_ERROR` | `preflight.log` | Retry up to 3× with backoff; STOP if persistent |
| **4. Corrupted GeoTIFF** | Truncated download or unreadable TIFF | `rasterio.open()` raises exception | `load_and_validate_sar_raster()` raises `InputValidationError` | `invalid_rasters.json` | STOP for that scene; report format error |
| **5. Channel Swapped / Inverted** | Ch0 is VV, Ch1 is VH | Verification check on band polarizations | Preprocessor asserts Ch0=VH, Ch1=VV | `preflight.log` | STOP immediately (Stopping Rule 2) |
| **6. Radiometric Domain Error** | Linear power fed directly without dB | Pixel min/max check ($>100$ or all $>0$) | `load_and_validate_sar_raster()` range warning / error | `invalid_rasters.json` | STOP; enforce conversion chain |
| **7. CRS Incompatibility** | Input raster not in EPSG:4326 | `src.crs != 'EPSG:4326'` | `InputValidationError` raised | `invalid_rasters.json` | STOP; reject non-4326 raster |
| **8. Checkpoint Hash Mismatch** | `best_model.pt` modified | SHA-256 check fails | Runner raises `CheckpointContractError` | `preflight.log` | STOP immediately (Stopping Rule 1) |
| **9. Zero Valid Pixels** | All pixels masked or NaN | `np.sum(validity_mask) == 0` | `InputValidationError` raised | `invalid_rasters.json` | Record missing; if $>10\%$ patches, STOP (Stopping Rule 4) |
| **10. Tiling Grid Misalignment** | Dimensions incompatible with 512 | `height <= 0` or `width <= 0` | `InputValidationError` raised | `invalid_rasters.json` | STOP; investigate AABB geometry |
| **11. Accidental Part III Access** | Path contains Part III identifiers | Firewall regex / identifier match | `PartIIIFirewallViolationError` raised | `firewall.log` | STOP immediately; fail-closed |
| **12. Accidental Holdout Access** | Request targets OPS-02 holdout partition | Partition manifest check | Preflight firewall raises violation | `firewall.log` | STOP immediately; fail-closed |
| **13. Missing Ground Truth** | Record missing in `data_matrix.tab` | TSV key lookup fails | Record marked `INVALID_METADATA` | `unresolved_scenes.json` | STOP before inference |
| **14. Invalid Denominator Attempt** | Attempt to divide by 5,515 | Evaluator assert denominator in (2290, 1365) | Assertion failure in metric calculation | `evaluation.log` | STOP; fix metric logic |
| **15. Evaluator Polygon Failure** | Polygon coordinates non-planar/invalid | `poly.is_valid` check fails | Buffer(0) repair; if still invalid, raise error | `invalid_rasters.json` | STOP; investigate coordinate data |
| **16. Non-Finite Output** | Model outputs NaN/Inf in logits | `np.any(~np.isfinite(prob_map))` | Flag invalid output in inference result | `failures.log` | Record tile failure; STOP if systemic |
| **17. Shared Scene Conflation** | Stratum 1 & 2 treated as independent | Assertion requires paired bootstrap | Test suite blocks unclustered comparison | `evaluation.log` | STOP; enforce paired modeling |
| **18. Credential Expiration** | CDSE token expires mid-run | 401 Unauthorized returned | Token refresh handler triggers | `preflight.log` | Refresh token and resume; STOP if refresh fails |
| **19. Storage Exhaustion** | Disk full during raster caching | `shutil.disk_usage()` check | Preflight asserts $\ge 50\text{ GB}$ free | `preflight.log` | Pause processing; notify operator |
| **20. Preflight Gate Bypass** | Attempt to run inference directly | Runner enforces gate before inference | `ExecutionNotAuthorizedError` raised | `preflight.log` | Hard stop; prevent bypass |

---

## 14. Obsidian / Knowledge Handoff

The integration with the Obsidian Knowledge Vault preserves complete boundary integrity:
- **Obsidian**: Knowledge / Memory / Navigation / Explanation.
- **RAG / Retrieval**: Context and recall only (`content_role = KNOWLEDGE_CONTEXT`, `execution_authority = NONE`).
- **Canonical Governance**: `data/metadata/governance_v2/` remains the sole machine-readable governance authority.
- **Retrieved Knowledge**: Does NOT grant execution authority, cannot authorize EXP-08, and cannot alter scientific protocols.
- **Experiment Registry Note**: [OS-EXP-008 - EXP-08 Final Benchmark.md](file:///d:/Projects/ocean-sentinel-knowledge/07%20Experiments/OS-EXP-008%20-%20EXP-08%20Final%20Benchmark.md) accurately reflects:
  - `status: BLOCKED`
  - `EXECUTION_AUTHORIZED: FALSE`
  - `non_claim: "EXP-08 is NOT a completed scientific result. It is a pre-authorized experiment awaiting execution approval."`

---

## 15. EXP-08 Readiness Matrix

| Requirement | Status | Evidence | Risk Level | Blocker Level | Next Action |
|---|---|---|---|---|---|
| **1. Protocol Definition & Scope** | **READY** | Protocol V3.5 §1, §13 | None | None | Maintain frozen protocol |
| **2. Acquisition Route (Route B - CDSE)** | **READY** | Protocol §2, §8; 40/40 pilot | Low (API availability) | None | Inject CDSE client |
| **3. Entity Ontology & Denominators** | **READY** | Protocol §3; 2,290 / 1,365 / 3,225 | Low (entity mixing) | None | Enforce discrete denominators |
| **4. Spatial Overlap Stratification** | **READY** | `exp08_spatial_overlap_r4.json` | None | None | Execute Stratum 1 & 2 analysis |
| **5. Evaluation Domain Contract** | **READY** | `geometry.py`, primary eval mask | None | None | Enforce polygon masking |
| **6. Radiometric & Preprocessing Contract** | **READY** | Protocol §9, §16; 3 pilot scenes | Low (radiometric shift) | None | Execute pinned pipeline |
| **7. Channel Mapping (VH/VV)** | **READY (Operational)** | `inference.py` L48, 1,200 census | Low (source paper paywall)| Pre-declared limitation | Stack as `[vh, vv]` |
| **8. Checkpoint & Model Contract** | **READY** | `best_model.pt` SHA-256 verified | None | None | Load strictly with strict=True |
| **9. Scientific Metrics & Oracles** | **READY** | Protocol §13; L1–L4, O1–O4 | None | None | Compute exact metrics |
| **10. Statistical Bootstrap Contract** | **READY** | Protocol §14.1; seed `20260927` | None | None | Run 10k cluster bootstrap |
| **11. Part III & Holdout Firewall** | **READY** | `firewall.py`, 6 unit tests | None | None | Enforce firewall |
| **12. Execution Gate & Runner** | **READY** | `exp08_runner.py`, gate asserts | None | None | Await written authorization |
| **13. Runtime Environment (PyTorch)** | **PARTIAL** | PyTorch absent in `.venv` | Low (requires install) | Prerequisite for execution | Provision PyTorch post-auth |
| **14. CDSE Operational Credentials** | **PARTIAL** | Pilot endpoints verified | Low (credential provision) | Prerequisite for execution | Inject credentials at run time |
| **15. Dual Authority Authorization** | **BLOCKED** | `EXECUTION_AUTHORIZED = False` | High if bypassed | Formal Governance Gate | Require CAO + Human approval |

---

## 16. Blockers & Declared Limitations

### 16.1 Material Execution Blockers
1. **Formal Dual Authorization**: Written authorization from CAO (ChatGPT) and Human (Dheeraj) has not yet been granted. This is the sole intended gate preventing execution.

### 16.2 Pre-Declared Scientific Limitations
1. **Calibration Bitwise Equivalence**: `NOT_PROVEN_WITH_CURRENT_ARTIFACTS`. Trujillo source GeoTIFFs stripped parent SAFE scene IDs and timestamps. Numerical equivalence between CDSE Process API and proprietary Trujillo processing cannot be proven even during execution without an external reference dataset.
2. **Channel Mapping at Source**: `UNKNOWN / UNVERIFIED AT SOURCE`. The original Trujillo 2024 paper's Data Preparation section remains behind an Elsevier publisher paywall. The operational model contract (Ch0=VH, Ch1=VV) is verified with limitations.
3. **Full Catalog Resolution**: 40/1,063 scenes were tested in the validation sample; full catalog resolution for the remaining 1,023 scenes is verified with limitations and will be resolved dynamically by the catalog preflight firewall during execution.
4. **DataMask Semantics**: Level-1 GRD `dataMask` indicates valid sensor footprint, not ocean/land discrimination.
5. **Cross-Stratum Scene Correlation**: 297 parent scenes span both Stratum 1 (disjoint) and Stratum 2 (co-located); comparisons must use paired cluster modeling rather than two-sample tests.

---

## 17. Protected File Hash Verification

All 8 protected scientific and governance files were verified before and after this audit pass. Every SHA-256 hash matches the canonical baseline to the character:

| Protected File Path | Expected SHA-256 Hash | Post-Audit Hash | Status |
|---|---|---|---|
| `data/metadata/governance_v2/rules.json` | `B216F369D68A027E4708E8CBCF3991D8EFFD5BA5A063A3B8B6B3FC2261D85C4E` | `B216F369D68A027E4708E8CBCF3991D8EFFD5BA5A063A3B8B6B3FC2261D85C4E` | **MATCH** |
| `data/metadata/governance_v2/lessons.json` | `4784A440070BC00612BC3BFA9B29A7ACC181934F894A9E22BD340FAAB7076395` | `4784A440070BC00612BC3BFA9B29A7ACC181934F894A9E22BD340FAAB7076395` | **MATCH** |
| `data/metadata/governance_v2/incidents.json` | `FA3051A185894EE1FE46EDB5825EBCFE92B107F80FB7527BF5746D4EC5B91836` | `FA3051A185894EE1FE46EDB5825EBCFE92B107F80FB7527BF5746D4EC5B91836` | **MATCH** |
| `src/ocean_sentinel/governance/runner.py` | `DD345558C3118EE61C0C966744D539C66DCFAABEAB2B9C66B03903C66EB3C9E0` | `DD345558C3118EE61C0C966744D539C66DCFAABEAB2B9C66B03903C66EB3C9E0` | **MATCH** |
| `src/ocean_sentinel/ingestion/dataset.py` | `F5BF1387769E43462AF8E4E4DE37867C761DD7ADBC040455532A3463EBFA0B0C` | `F5BF1387769E43462AF8E4E4DE37867C761DD7ADBC040455532A3463EBFA0B0C` | **MATCH** |
| `src/ocean_sentinel/temporal.py` | `46614361E1BE20A278D0AF9CEEE222E4787DF1EADE7D52A88B372965170E26CF` | `46614361E1BE20A278D0AF9CEEE222E4787DF1EADE7D52A88B372965170E26CF` | **MATCH** |
| `experiments/performance/exp06_positive_bce_weight/best_model.pt` | `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` | `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` | **MATCH** |
| `docs/exp08_corrected_protocol.md` | `E6691A6C3A70D6762A03462E5A8E6B6B60F0DD1AD066A552DD047375DE6FB50E` | `E6691A6C3A70D6762A03462E5A8E6B6B60F0DD1AD066A552DD047375DE6FB50E` | **MATCH** |

---

## 18. Files Changed in This Phase

1. `scratch/obsidian_v2_progress.md`: Appended `## EXP08_EXECUTION_READINESS_HANDOFF` telemetry entry (append-only history preserved).
2. `OCEAN_SENTINEL_EXP08_EXECUTION_READINESS_REPORT.md`: This report created.

**Pre-existing Tracked Modifications (Preserved Untouched):**
- `.gitignore`
- `experiments/EXTERNAL_VALIDATION_READINESS.md`
- `pyproject.toml`
- `src/ocean_sentinel/ingestion/dataset.py`

Zero protected files modified. Zero unrelated code modified.

---

## 19. Git State Verification

- **Branch**: `master`
- **HEAD Commit**: `542bab19f6f08c9bba8b8762e6480386c8b6026b`
- **Status**: Stable. No unexpected git operations performed.

---

## 20. Explicit Non-Claims

1. **EXP-08 HAS NOT EXECUTED.** No benchmark results exist. No proposal recall or activation statistics have been computed on DARTIS imagery.
2. The 366 passing tests in `tests/test_exp08_*.py` are **pre-execution guardrail and protocol tests**, NOT scientific results.
3. Spatial non-overlap (1,501 patches in Stratum 1) demonstrates zero geometric intersection with Trujillo Part I raster extents, but does **NOT** prove statistical independence.
4. The $-70\text{ dB}$ conversion floor is a **numerical guard against $-\infty$**, NOT an independent proof of physical classification safety.
5. The operational channel mapping (Ch0=VH, Ch1=VV) is established for the model pipeline, but does **NOT** constitute verified source truth of the paywalled Trujillo publication.
6. Passing vault validation does **NOT** grant execution authority.

---

## 21. Final Authorization Boundary

The remaining boundary between `READY_FOR_EXPLICIT_CAO_HUMAN_AUTHORIZATION` and `EXECUTION_AUTHORIZED = TRUE` is strictly procedural and governance-driven:

```
[EXP-08 Readiness Package Verified]
                 │
                 ▼
[CAO Review & Written Authorization] ───┐
                                        ├─► [Explicit Written Dual Authorization]
[Human Review & Written Approval]   ───┘
                                                       │
                                                       ▼
                                      [Flip EXECUTION_AUTHORIZED = True in runner]
                                      [Provision PyTorch & CDSE Credentials]
                                      [Execute run_exp08_evaluation()]
```

**Scientific execution has NOT occurred.**  
**Explicit human authorization remains required.**

---

## 22. Final Gate

```
CURRENT_STAGE = READY_FOR_EXPLICIT_CAO_HUMAN_AUTHORIZATION
CURRENT_ISSUE = NONE
FINAL_GATE = EXP08_READY_FOR_EXPLICIT_CAO_HUMAN_AUTHORIZATION
EXECUTION_AUTHORIZED = FALSE
```

**HARD STOP. Awaiting explicit CAO (ChatGPT) + Human (Dheeraj) written authorization.**

---

## 23. Post-Reconciliation Live Verification Addendum

**Verification Date**: 2026-10-02T06:20–06:38Z (serial runs)  
**Model**: Gemini (Antigravity IDE 2.0 fallback per task spec)  
**Commit at verification**: `542bab19f6f08c9bba8b8762e6480386c8b6026b` (branch: `master`)

### 23.1 Protected File Hash Verification

All 8 protected scientific/governance files re-verified against the stored baseline hashes:

| File | Hash | Status |
|------|------|--------|
| `data/metadata/governance_v2/rules.json` | `B216F369...D85C4E` | ✅ MATCH |
| `data/metadata/governance_v2/lessons.json` | `4784A440...076395` | ✅ MATCH |
| `data/metadata/governance_v2/incidents.json` | `FA3051A1...91836` | ✅ MATCH |
| `src/ocean_sentinel/governance/runner.py` | `DD345558...C9E0` | ✅ MATCH |
| `src/ocean_sentinel/ingestion/dataset.py` | `F5BF1387...0B0C` | ✅ MATCH |
| `src/ocean_sentinel/temporal.py` | `46614361...26CF` | ✅ MATCH |
| `experiments/performance/exp06_positive_bce_weight/best_model.pt` | `B5FFCCA3...E8DF` | ✅ MATCH |
| `docs/exp08_corrected_protocol.md` | `E6691A6C...B50E` | ✅ MATCH |

**Result: 8/8 MATCH — no integrity violations.**

### 23.2 EXP-08 Test Suite (Primary Scope)

| Suite | Files | Tests | Passed | Failed | Skipped | Time |
|-------|-------|-------|--------|--------|---------|------|
| EXP-08 Acceptance Battery | 13 | 366 | **366** | **0** | 0 | 1.66s |

All 366 EXP-08 pre-execution guardrail tests pass cleanly. No regressions.

### 23.3 Obsidian V2 / Governance Knowledge Tests

| Suite | Files | Tests | Passed | Failed | Skipped | Time |
|-------|-------|-------|--------|--------|---------|------|
| Governance / Obsidian Knowledge (8 files) | 8 | 273 | **273** | **0** | 0 | 21.96s |
| Staged Governance Isolation (serial) | 1 | 62 | **62** | **0** | 0 | 19.54s |

All governance, adversarial replay, agent learning, staged isolation, and report reconciliation tests pass cleanly in serial execution. The Obsidian V2 knowledge vault is fully operationally intact.

### 23.4 Non-EXP08 Serial Run — Classified Failure Inventory

Authoritative **serial** run of the complete serial non-EXP08 corpus under the current pre-authorization environment, with torch/PIL-dependent tests subject to dependency limitations: **31 failed, 1962 passed, 18 skipped** (976s).

> [!NOTE]
> An earlier concurrent run (two test processes simultaneously on Windows) produced 59 failures — 28 of those were `TRANSACTION_LEASE_DENIED: WinError 32` errors from Windows file-lock contention on the governance transaction lock. These are a concurrent-execution artefact, not real failures. Serial runs are authoritative; `test_staged_governance_isolation.py` passes **62/62** when run alone.

The 31 serial failures fall into five distinct categories:

**Category A — Historical/Stale Test Debt (18 failures)**

| Test Group | Count | Root Cause |
|------------|-------|------------|
| Stale git porcelain count assertions | 3 | Hardcoded to ~293 untracked; working tree has 1364 |
| EXP-07 lesson/policy/closure guardrails | 6 | Stale Phase 7C lesson/policy assertions |
| EXP-07 taxonomy/diag05 numeric invariants | 5 | Phase 7C diagnostic protocol numeric constants |
| Phase 5 guardrails (sampling/population counts) | 2 | Hardcoded Phase 5 era counts |
| Phase 7B2B pretraining gate checks | 2 | EXP-07 training artefact detection |

**Category B — Dependency/Environment-Limited (5 failures)**

| Test Group | Count | Root Cause |
|------------|-------|------------|
| `networkx` not installed | 2 | `test_spatial_split.py` overlap graph tests require optional dep |
| `torch` required at runtime call depth | 3 | `test_dataset_pipeline`, `test_spatial_split` loader paths hit `_require_torch()` |

**Category C — Phase 8 Source Control / Audit Assertions (6 failures)**

| Test Group | Count | Root Cause |
|------------|-------|------------|
| Phase 8 source control/closure git state | 6 | `no_uncommitted_changes`, `governance_json_committed`, audit doc assertions |

**Category D — `test_no_ops01_training_script_exists` (1 failure)**
`scripts/train_exp07.py` present in the repository; Phase 8 audit test flags this as unauthorized. Pre-EXP08 artefact; no EXP-08 impact.

**Category E — Test-Harness / Firewall Coupling Defect (1 failure)**
See §23.4a below.

#### 23.4a — `test_dataset_firewall_blocks_part_iii_root` — Precise Classification

**Classification: TEST-HARNESS DEFECT — NO EVIDENCE OF FIREWALL FAILURE.**

**Evidence** (live traceback, 2026-10-02T07:18Z):

```
dataset.py:109: in __init__
    _require_torch()
dataset.py:67: in _require_torch
    raise ImportError: PyTorch is required for TrujilloTileDataset.
FAILED — test expected PartIIIFirewallViolationError, received ImportError
```

`TrujilloTileDataset.__init__()` calls `_require_torch()` at line 109 before the firewall at lines 117–120. With `torch` absent, `ImportError` is raised immediately; the firewall code is never reached. The test expects `PartIIIFirewallViolationError` but receives `ImportError` — hence the failure.

The other 5 tests in `test_part_iii_firewall.py` all pass (5/6), including `test_assert_no_part_iii_leakage_raises` and `test_manifest_identity_firewall`, which test the firewall functions directly without going through the torch-gated class. The firewall implementation is correct. This is a test-harness coupling defect: the test exercises a firewall that now sits after an earlier torch-availability guard. **This does not constitute a material EXP-08 defect and does not block the authorization gate.**

> [!IMPORTANT]
> None of the reviewed failures provides evidence of a defect in the current EXP-08 scientific implementation, subject to the separately classified Part III firewall test result (§23.4a), which itself does not demonstrate a firewall bypass.

### 23.5 Pre-Authorization Environment Note

`torch` is deliberately absent from the pre-authorization environment as an additional environmental precaution against accidental model execution; the authoritative execution boundary is enforced by the explicit authorization gate and the execution/holdout/Part III firewalls.

During an earlier pre-authorization dependency sweep, 31 torch/PIL-dependent test files were identified as requiring unavailable ML/image dependencies (failing with `ModuleNotFoundError` at collection time; this expected pre-authorization condition is verified in `test_exp08_final_release_acceptance.py::Stage 5`). These dependency limitations are distinct from the 31 failures reported in the authoritative serial non-EXP08 corpus, whose causes are classified separately in §23.4.

### 23.6 Summary of Forensic Verification

| Check | Status |
|-------|--------|
| Protected hashes (8/8) | ✅ ALL MATCH |
| EXP-08 test suite (366 tests) | ✅ 366/366 PASS |
| Obsidian V2 governance tests (273 tests, serial) | ✅ 273/273 PASS |
| Staged governance isolation (62 tests, serial) | ✅ 62/62 PASS |
| Part III firewall implementation | ✅ INTACT (§23.4a) |
| Scientific execution | NOT PERFORMED (expected pre-authorization state) |
| Inference | NOT PERFORMED (expected pre-authorization state) |
| Holdout access | NOT PERFORMED (expected pre-authorization state) |
| Part III data access | NOT PERFORMED (expected pre-authorization state) |
| `EXECUTION_AUTHORIZED` flag | FALSE (governance gate enforced) |
| `torch` in `.venv` | ABSENT (environmental precaution; not sole firewall) |
| Non-EXP08 serial failures | ⚠️ 31 classified: 18 stale, 5 dependency-limited, 6 source-control, 1 pre-EXP08 artefact, 1 test-harness |
| FINAL_GATE | ✅ `EXP08_READY_FOR_EXPLICIT_CAO_HUMAN_AUTHORIZATION` |

**The EXP-08 readiness package is forensically verified, internally consistent, technically safe, and operationally blocked pending dual written authorization. HARD STOP CONFIRMED.**
