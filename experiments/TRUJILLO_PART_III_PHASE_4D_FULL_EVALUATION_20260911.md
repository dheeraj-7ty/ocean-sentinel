# OCEAN SENTINEL — PHASE 4D-F
## FULL TRUJILLO PART III BENCHMARK EVALUATION REPORT
**Authority:** Chief Architect Officer (CAO)  
**Execution Class:** Full Frozen External Benchmark Evaluation  
**Dataset:** Trujillo Part III (`10.5281/zenodo.13761290`, `02_Test_images_and_ground_truth.7z`)  
**Primary Checkpoint:** [`experiments/exp01_baseline/best_model.pt`](file:///d:/Projects/ocean-sentinel/experiments/exp01_baseline/best_model.pt)  
**Evaluation Date:** 2026-09-11  
**Status:** `PHASE_4D_FULL_EVALUATION_PASS`  

---

## 1. Scope and Authority
This document records the official, CAO-authorized results of the first full external benchmark evaluation of Ocean Sentinel Baseline Model `EXP-01` (`best_model.pt`) on the Trujillo Part III external benchmark population. Execution was conducted under strict scientific firewalls with zero threshold tuning, zero normalization tuning, zero test-set fitting, zero post-hoc channel selection, and zero outcome-based exclusions.

The statements in this report strictly distinguish between:
- `[OBSERVED FACT]`: Directly measured empirical data and repository artifacts.
- `[INFERENCE]`: Methodological and empirical interpretations derived from the measurements.
- `[UNVERIFIED MECHANISM / LIMITATION]`: Hypotheses or physical conditions not established by benchmark evidence.

---

## 2. Frozen Methodology Identifiers
The evaluation strictly executed the frozen specifications established and locked prior to inference:
- **Evaluation Contract:** [`experiments/TRUJILLO_PART_III_EVALUATION_CONTRACT_20260911.md`](file:///d:/Projects/ocean-sentinel/experiments/TRUJILLO_PART_III_EVALUATION_CONTRACT_20260911.md)  
  *SHA-256:* `70319B82F6795FDEE5B7172BB63D3DD371E56B86F9EEA36D0F8DCCD21BA5A992`
- **Adapter Design Specification:** [`experiments/TRUJILLO_PART_III_ADAPTER_DESIGN_20260911.md`](file:///d:/Projects/ocean-sentinel/experiments/TRUJILLO_PART_III_ADAPTER_DESIGN_20260911.md)  
  *SHA-256:* `FC6EFBA6BF1D3F41BD9D3DB673DD3264E18ED5432CA4DB0EF1CF8AF45B372E1D`
- **Adapter Implementation:** [`scratch/trujillo_part_iii_adapter.py`](file:///d:/Projects/ocean-sentinel/scratch/trujillo_part_iii_adapter.py)  
  *SHA-256:* `986957C94F67286CB1B1F4530D2B1337C4205D509ED3261F8D9EA734D3581DF9`
- **Sample Pairing Manifest:** [`scratch/trujillo_part_iii_pairing.json`](file:///d:/Projects/ocean-sentinel/scratch/trujillo_part_iii_pairing.json)  
  *SHA-256:* `316D5E7DF8BAD266702C47C6671E497F655B7E5761C3467BD5B2CA20D9A727DC`
- **Source Hash Inventory:** [`scratch/trujillo_part_iii_extracted_sha256.json`](file:///d:/Projects/ocean-sentinel/scratch/trujillo_part_iii_extracted_sha256.json)
- **Repository Commit:** `542bab19f6f08c9bba8b8762e6480386c8b6026b` (branch `master`)

---

## 3. Checkpoint Integrity & Hash Verification
The model weights were loaded exclusively from the certified baseline checkpoint:
- **Path:** `experiments/exp01_baseline/best_model.pt`
- **File Size:** `292,465,299` bytes
- **SHA-256 (Pre-Inference):** `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
- **SHA-256 (Post-Inference):** `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
- **State:** `[OBSERVED FACT]` SHA-256 digest identical before and after evaluation, supporting unchanged checkpoint bytes across the entire execution.

---

## 4. Architecture Reconciliation & Structural Equivalence
Pre-execution inspection reconciled the descriptive vs programmatic representation:
- **Canonical Python Class:** `ResNet34UNet` ([`src/ocean_sentinel/ml/unet_resnet.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ml/unet_resnet.py))
- **Descriptive Literature Alias:** `UNet(backbone='resnet34', in_channels=2, num_classes=1)`
- **Encoder:** ImageNet-adapted ResNet-34 encoder with conv1 adapted via `slice_variance_scaled`
- **Total Parameters:** `24,346,305` (Trainable: `24,346,305`, Non-trainable: `0`)
- **State Dictionary Loading:** Loaded with `strict=True`; exactly 0 missing keys, 0 unexpected keys.
- **Equivalence Status:** Confirmed **Case A** (exact structural equivalence: identical module hierarchy, layer parameter tensors, and state dictionary keys).

---

## 5. Dataset Population & Stratification
The evaluation was executed over the full frozen 450-scene population of Trujillo Part III:
- **Oil Stratum:** 150 scenes (`Oil_00000` to `Oil_00149`) with foreground oil-slick targets.
- **No oil Stratum:** 150 scenes (`No oil_00000` to `No oil_00149`) with confirmed target-absence (all-zero target masks).
- **Lookalike Stratum:** 150 scenes (`Lookalike_00000` to `Lookalike_00149`) with natural/anthropogenic lookalike features (all-zero target masks).
- **Total Evaluated Population:** 450 scenes (900 source GeoTIFFs: 450 2-band SAR images + 450 segmentation masks).

---

## 6. Execution Accounting: Tiles, Batches, and Forward Calls
Inference was structured deterministically per scene and executed in bounded GPU batches:
- **Tile Geometry:** 16 non-overlapping $512 \times 512$ chips per $2048 \times 2048$ scene.
- **Offsets:** $[0, 512, 1024, 1536]$ along row and column dimensions.
- **Batch Size:** 16 tiles per model forward pass (1 complete whole-scene equivalent per forward pass).
- **Mapping A Inferences:** 450 scenes, 7,200 tiles, 450 model forward calls.
- **Mapping B Inferences:** 450 scenes, 7,200 tiles, 450 model forward calls.
- **TOTAL_TILES_INFERRED:** `14,400` tiles.
- **ACTUAL_MODEL_FORWARD_CALLS:** `900` forward calls.
- **SCENE_EVALUATIONS:** `900` scene evaluations (450 scenes $\times$ 2 mappings).

---

## 7. Input Normalization & Destination-Channel Rule
Numerical standardization strictly followed the destination model channel using frozen Part I training set statistics:
- **Channel 0:** $\mu_0 = -33.233136989478695, \quad \sigma_0 = 6.489985665955077$
- **Channel 1:** $\mu_1 = -19.941215852796695, \quad \sigma_1 = 4.531345684833188$
- **Mapping A (Direct):**  
  $\text{Ch}_0 = (\text{Band}_1 - \mu_0) / \sigma_0$  
  $\text{Ch}_1 = (\text{Band}_2 - \mu_1) / \sigma_1$
- **Mapping B (Inverted):**  
  $\text{Ch}_0 = (\text{Band}_2 - \mu_0) / \sigma_0$  
  $\text{Ch}_1 = (\text{Band}_1 - \mu_1) / \sigma_1$
- **Coupling Invariant:** Source bands were never normalized before channel assignment; normalization strictly followed the destination model channel. Zero test-set adaptation or recalibration.

---

## 8. Threshold & Continuous Probability Reconstruction
In accordance with Candidate C (Whole-Scene Probability Mosaic Reconstruction):
1. Model forward pass yielded raw logits for each $512 \times 512$ tile.
2. Logits were converted to continuous sigmoid probabilities in `float32`.
3. Tile probabilities were placed into a full $2048 \times 2048$ whole-scene continuous probability mosaic (`prob_mosaic`). Coverage was audited: every pixel covered exactly once with zero gaps or duplicate additions.
4. Frozen decision threshold $\tau = 0.22$ was applied exactly once to the full-precision continuous probability mosaic:
   $$\hat{Y}_{\text{pred}} = \mathbb{I}(\text{prob\_mosaic} \ge 0.22) \in \{0, 1\}^{2048 \times 2048}$$
5. The binary prediction mask is authoritative for all confusion and metric calculations.

---

## 9. Prediction Artifact Schema & Output Namespace
All artifacts were emitted into isolated, non-overwriting namespaces:
- **Directory:** `experiments/performance/trujillo_part_iii_eval_20260911_exp01/`
  - `mapping_a/`: 450 `.npz` arrays + 450 companion `.json` provenance records.
  - `mapping_b/`: 450 `.npz` arrays + 450 companion `.json` provenance records.
  - `manifests/`: Frozen pairing manifest and freeze hash registry.
  - `metrics/`: Primary machine-readable metric summaries and recomputation audit.
  - `logs/`: Runtime logs.
- **Array Storage:** `.npz` storing `probability_map` (`float16`), `prediction_mask` (`uint8`), and `target_mask` (`uint8`).
- **Metadata Records:** Every `.json` stores pair ID, class, source image/mask paths and SHA-256 hashes, checkpoint SHA-256, normalization parameters, tile geometry, confusion counts, and probability statistics.

---

## 10. Technical Failures & Exclusions
- **Technical Failures:** Exactly `0`. All 450 scenes evaluated cleanly under both mappings without raster read errors, NaN tensors, or write failures.
- **Outcome-Based Exclusions:** Exactly `0`. Zero scenes were removed or substituted based on prediction accuracy or difficulty.
- **Terminal State Accounting:**
  - `EVALUATED`: 450 / 450 in Mapping A; 450 / 450 in Mapping B (900 total).
  - `TECHNICAL_FAILURE`: 0.
  - `BLOCKED`: 0.

---

## 11. Benchmark Results: Oil Stratum ($N = 150$)
The Oil stratum contains 150 scenes with foreground target masks. Evaluated strictly using pixel-space segmentation metrics:

| Metric | Mapping A (Mean $\pm$ Std) | Mapping A (Median) | Mapping B (Mean $\pm$ Std) | Mapping B (Median) | Sensitivity Delta ($B - A$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Macro IoU** | **$0.7788 \pm 0.1629$** | **$0.8211$** | $0.1005 \pm 0.1362$ | $0.0473$ | **$-0.6783$** |
| **Macro Dice / $F_1$** | **$0.8639 \pm 0.1306$** | **$0.9017$** | $0.1605 \pm 0.1811$ | $0.0904$ | **$-0.7034$** |
| **Macro Precision** | **$0.8300 \pm 0.1654$** | **$0.8896$** | $0.1006 \pm 0.1364$ | $0.0473$ | **$-0.7294$** |
| **Macro Recall** | **$0.9406 \pm 0.1063$** | **$0.9846$** | $0.9992 \pm 0.0053$ | $1.0000$ | **$+0.0586$** |
| **Micro Pooled IoU** | **$0.8222$** | — | $0.1011$ | — | **$-0.7211$** |
| **Micro Pooled Dice** | **$0.9024$** | — | $0.1837$ | — | **$-0.7188$** |
| **Total True Positives (TP)** | $58,834,313$ px | — | $62,355,841$ px | — | $+3,521,528$ px |
| **Total False Positives (FP)** | $9,054,011$ px | — | $554,128,400$ px | — | $+545,074,389$ px |
| **Total False Negatives (FN)**| $3,667,674$ px | — | $146,146$ px | — | $-3,521,528$ px |

### Canonical Part I Test Comparison
- `[OBSERVED FACT]`: Canonical Part I held-out test IoU is **`0.79808`** (recorded in `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/official_test_evaluation/official_test_results.json` and established in `experiments/EXTERNAL_VALIDATION_READINESS.md`).
- `[OBSERVED FACT]`: Mapping A achieved a **`0.77882`** macro mean IoU on the 150-scene Oil stratum.
- `[DERIVED COMPARISON]`: Mapping A Oil macro mean IoU is **`0.01926`** lower than the canonical Part I test IoU of `0.79808` (a difference of **`1.926` percentage points**).
- `[INFERENCE]`: This delta provides a descriptive benchmark reference; it does not constitute a formal statistical significance test and does not imply identical spatial or sensor distributions between the datasets.

---

## 12. Benchmark Results: No Oil Stratum ($N = 150$)
All 150 scenes in the No oil stratum possess all-zero ground-truth masks. Performance is evaluated via False Alarm Rates and pixel counts:

| Diagnostic Metric | Mapping A | Mapping B | Comparison |
| :--- | :---: | :---: | :---: |
| **Scene-Level FAR ($\mathbb{I}(\text{FP} > 0)$)** | **$41.33\%$** (62 / 150 scenes) | $98.67\%$ (148 / 150 scenes) | $+57.34$ pp |
| **Significant FAR ($\mathbb{I}(\text{FP} \ge 100)$)** | **$30.67\%$** (46 / 150 scenes) | $98.67\%$ (148 / 150 scenes) | $+68.00$ pp |
| **Mean FP Pixels per Scene** | **$577.0$ px** ($0.0138\%$ of scene) | $3,411,369.0$ px ($81.33\%$ of scene) | $\times 5,912$ increase |
| **Median FP Pixels per Scene** | **$0.0$ px** (zero in $>50\%$ scenes) | $4,126,606.0$ px | Massive saturation |
| **Total FP Pixels across Stratum** | **$86,552$ px** | $511,705,344$ px | $\times 5,912$ increase |
| **Max FP Pixels in Single Scene** | $32,827$ px | $4,194,304$ px (100% false positive) | — |

---

## 13. Benchmark Results: Lookalike Stratum ($N = 150$)
All 150 scenes contain natural/anthropogenic slick lookalikes with all-zero ground-truth target masks:

| Diagnostic Metric | Mapping A | Mapping B | Comparison |
| :--- | :---: | :---: | :---: |
| **Scene-Level FAR ($\mathbb{I}(\text{FP} > 0)$)** | **$98.67\%$** (148 / 150 scenes) | $100.00\%$ (150 / 150 scenes) | $+1.33$ pp |
| **Significant FAR ($\mathbb{I}(\text{FP} \ge 100)$)** | **$98.00\%$** (147 / 150 scenes) | $100.00\%$ (150 / 150 scenes) | $+2.00$ pp |
| **Mean FP Pixels per Scene** | **$1,335,767.8$ px** ($31.85\%$ of scene) | $3,671,556.2$ px ($87.54\%$ of scene) | $\times 2.75$ increase |
| **Median FP Pixels per Scene** | **$637,136.0$ px** | $4,176,482.0$ px | High false alarm |
| **Total FP Pixels across Stratum** | **$200,365,167$ px** | $550,733,433$ px | $\times 2.75$ increase |
| **Max FP Pixels in Single Scene** | $4,194,304$ px | $4,194,304$ px | — |

- `[OBSERVED FACT]`: Under Mapping A, 148 of 150 lookalike scenes produced non-zero false positives ($98.67\%$ scene FAR), with an average of $1,335,767.8$ false-positive pixels per scene ($31.85\%$ of scene area).
- `[INFERENCE]`: Lookalike scenes constitute a major false-alarm failure mode for the baseline model under external benchmark conditions.

---

## 14. Polarization Sensitivity Comparison & Interpretation
In strict accordance with the CAO Scientific Firewall:
- `[OBSERVED FACT]`: Polarization channel order is physically uncalibrated in upstream source rasters.
- `[OBSERVED FACT]`: Mapping A yielded an Oil Macro IoU of $0.77882$ and $86,552$ false-positive pixels on No oil. Mapping B yielded an Oil Macro IoU of $0.10051$, $554,128,400$ false-positive pixels on Oil, and $511,705,344$ false-positive pixels on No oil.
- `[INFERENCE]`: The benchmark demonstrates extreme empirical sensitivity to polarization channel ordering. Neither Mapping A nor Mapping B can be declared physically "correct," "true," or a "winner" based on performance scores.
- `[UNVERIFIED MECHANISM]`: The internal neural feature representations causing this sensitivity and the physical channel identities of the source rasters remain unverified.

---

## 15. Execution Quality Note: Observability & Run State Defect
- `[OBSERVED FACT]`: During active evaluation monitoring, the expected durable state file at `experiments/performance/trujillo_part_iii_eval_20260911_exp01/run_state.json` was absent because the execution script maintained its durable run state at `scratch/trujillo_part_iii_evaluation_run_state.json`.
- `[OBSERVED FACT]`: Inference progress was continuously verified through the scene-level prediction artifacts on disk (`900` `.npz` arrays and `900` companion `.json` records), live process telemetry, and the scratch state file.
- `[EVALUATION QUALITY CLASSIFICATION]`: This is classified strictly as an **execution observability defect**, not a scientific integrity defect. The underlying prediction tensors, binary masks, and calculated metrics were unaffected. Future long-running benchmark runs must enforce in-namespace durable run state persistence as a blocking preflight requirement.

---

## 16. Independent Metric Recomputation Audit
In accordance with Section 30 of the CAO Directive, a separate validation script ([`scratch/audit_metric_recomputation.py`](file:///d:/Projects/ocean-sentinel/scratch/audit_metric_recomputation.py)) independently recomputed confusion counts and metrics from raw `.npz` arrays on disk:
- **Scope:** 900 scene artifacts (450 Mapping A + 450 Mapping B).
- **Confusion Matrix Recomputation:** $TP, FP, FN, TN$ recomputed from scratch using array operations.
- **Integer Count Match:** Exactly `100.0%` agreement with primary JSON metadata across all 900 scenes.
- **Floating-Point Metric Match:** Agreement within tolerance $\le 10^{-6}$ across all macro and micro metrics.
- **Audit File:** [`experiments/performance/trujillo_part_iii_eval_20260911_exp01/metrics/independent_recomputation_audit.json`](file:///d:/Projects/ocean-sentinel/experiments/performance/trujillo_part_iii_eval_20260911_exp01/metrics/independent_recomputation_audit.json)
- **Status:** **PASS**.

---

## 17. Comprehensive Self-Audit (Section 38: Checks A–AF)
The independent verification script ([`scratch/self_audit_phase_4d_full.py`](file:///d:/Projects/ocean-sentinel/scratch/self_audit_phase_4d_full.py)) audited all 32 mandatory gates:
1. `A. Correct Checkpoint Identity`: PASS (Size: 292,465,299, SHA: `9B8BD867DC02...`)
2. `B. Architecture Compatibility`: PASS (ResNet34UNet parameter count = 24,346,305)
3. `C. Exact Frozen Sample Population`: PASS (Total: 450; 150 Oil, 150 No oil, 150 Lookalike)
4. `D. Mapping A Evaluated Scenes`: PASS (450 artifacts present)
5. `E. Mapping B Evaluated Scenes`: PASS (450 artifacts present)
6. `F. Total Tiles`: PASS (14,400 tiles)
7. `G. Forward-Call Count Recorded Separately`: PASS (900 forward calls vs 14,400 tiles)
8. `H. Source Hashes Verified`: PASS (900 source GeoTIFF hashes unchanged)
9. `I. Checkpoint Hash Unchanged`: PASS (Pre and post-run hashes identical)
10. `J. Contract Hash Unchanged`: PASS (`70319B82F679...`)
11. `K. Adapter Hash Unchanged`: PASS (`986957C94F67...`)
12. `L. Deterministic Normalization`: PASS (Frozen Part I train split statistics)
13. `M. Destination-Channel Normalization Coupling`: PASS (Destination channel coupling verified)
14. `N. Polarization Policy Unchanged`: PASS (Dual-pass sensitivity active)
15. `O. Threshold = 0.22`: PASS ($\tau = 0.22$ strictly frozen)
16. `P. Threshold Domain = Sigmoid Probability`: PASS (Applied in probability domain)
17. `Q. Probability-First Reconstruction`: PASS (Full-precision mosaic reconstructed before thresholding)
18. `R. Binary Mask Authoritative for Metrics`: PASS (Metrics derived from binary mask)
19. `S. Metric Firewall Enforced`: PASS (Computed strictly after both mappings completed)
20. `T. Metric Stratification Enforced`: PASS (Zero pooled cross-strata headline IoU)
21. `U. Empty-Mask Handling Enforced`: PASS (Absence diagnostics evaluated via FAR)
22. `V. No Outcome-Based Exclusions`: PASS (Zero samples excluded, denominator $N = 450$)
23. `W. Contamination Disclosure Present`: PASS (Disclosures embedded in metadata and report)
24. `X. Independent Metric Recomputation Matches`: PASS (100% integer match, float $\le 10^{-6}$)
25. `Y. No Unexpected Prediction Artifacts`: PASS (Exactly 900 `.npz` files)
26. `Z. No Incomplete Prediction Artifacts`: PASS (All companion `.json` present and complete)
27. `AA. No Methodology Drift`: PASS (Environment parameters strictly locked)
28. `AB. No Network Invocation`: PASS (`NETWORK_ACCESS = NONE`)
29. `AC. No Unexplained Background Process`: PASS (All processes finished cleanly)
30. `AD. No Evaluation Lock Remains`: PASS (Lock cleanly released)
31. `AE. Report/Artifact Consistency`: PASS (All reported metrics match machine-readable files)
32. `AF. Git Audited`: PASS (0 staged files, 0 tracked modifications)

---

## 18. Contamination and Upstream Provenance Disclosure
In adherence to the non-negotiable scientific firewall:
- **Content Matching:** No exact SHA-256 content matches were detected between Part I and Part III rasters.
- **Acquisition Independence:** Acquisition-level independence remains **UNVERIFIED**.
- **Provenance:** Both Part I and Part III originate from the same research group (Trujillo et al., Universidad Industrial de Santander) using Sentinel-1 C-SAR archives. A degree of sensor, pre-processing, and geographic overlap is likely.
- **Scientific Claim:** This benchmark evaluation measures generalization to external scenes under the frozen contract; it does **not** claim complete acquisition-level domain independence.

---

## 19. Runtime Environment & Network Isolation
- **OS:** Windows 11 Pro (win32)
- **Python Environment:** Python 3.11.9, PyTorch `2.14.0+cu126`, CUDA 12.6, Rasterio `1.4.4`, GDAL `3.9.3`
- **GPU Hardware:** NVIDIA GeForce RTX 3060 (12 GB VRAM)
- **Network Status:** `NETWORK_ACCESS = NONE`. Zero external network calls were made during the entire evaluation pipeline.

---

## 20. Scientific Limitations
1. **Physical dB Calibration:** Raw digital numbers in the source GeoTIFFs are uncalibrated with respect to absolute radar backscatter ($\sigma_0$ in dB).
2. **Polarization Identity:** Upstream metadata does not authoritatively confirm whether Band 1 is VV and Band 2 is VH, or vice-versa.
3. **World Coordinate Alignment:** Unprojected array coordinates were used for mask matching; geodetic alignment remains unestablished.
4. **Lookalike Vulnerability:** The baseline model exhibits severe susceptibility to lookalike features ($98.67\%$ scene false alarm rate under Mapping A; $100.00\%$ under Mapping B). Lookalike discrimination constitutes the dominant false-alarm vulnerability identified by this benchmark.
5. **Execution Observability:** Run state pathing was split between scratch and the experiment performance namespace.

---

## 21. Final Benchmark Evaluation Status
All 15 closure-integrity acceptance criteria were satisfied for scientific result validity and report integrity. The previously identified execution-observability defect remains documented as an execution-quality limitation and does not alter the benchmark result because full scene coverage and persisted outputs were independently verified.

$$\mathbf{STATUS:}\quad \mathbf{PHASE\_4D\_FULL\_EVALUATION\_PASS}$$
