# PHASE 5H EXP-06 CLOSURE AUDIT & SCIENTIFIC DISPOSITION CERTIFICATE

**Project:** Ocean Sentinel  
**Authority:** CAIO Scientific Governance  
**Document ID:** `PHASE_5H_EXP06_CLOSURE_AUDIT_20260912`  
**Date:** 2026-09-12  
**Final Scientific Disposition:** **EXP-06 DEVELOPMENT/VALIDATION ACCEPTANCE: PASS — CERTIFIED & CLOSED WITHIN THE AUDITED PHASE 5H SCOPE.**  

---

## 1. Executive Summary & Audit Mandate

This closure audit provides the authoritative post-run verification and discrepancy reconciliation for **EXP-06 Positive-Class BCE Reweighting** (`EXP-06_POSITIVE_BCE_WEIGHT`, Attempt `EXP06_ATTEMPT_001`).

Under strict scientific governance, all conclusions are derived directly from on-disk machine-readable artifacts, binary hash calculations, and exact integer arithmetic rather than narrative text.

**Audit Finding:** The scientific disposition of **PASS** is 100% verified, validated, and mathematically supported. All five preregistered acceptance gates passed at the global best validation checkpoint (Epoch 9).

---

## 2. Checkpoint Provenance & Cryptographic Audit

All model checkpoints and input manifests were independently hashed directly from disk using Python `hashlib` SHA-256:

| Checkpoint / Artifact | Filesystem Path | SHA-256 Digest | Size (Bytes) | Verification Status |
| :--- | :--- | :--- | :---: | :---: |
| **EXP-01 Teacher Baseline** | `experiments/exp01_baseline/best_model.pt` | `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | $292,465,299$ | **CERTIFIED AUTHORITATIVE** |
| **EXP-03 Best Checkpoint** | `experiments/performance/exp03_baseline_hard_neg/best_model.pt` | `BE00C1C8B35A3648FCCAD3864F844ED2EB68E079F2CC390C1BA3EC147BF2DA57` | $292,463,187$ | **CERTIFIED UNCHANGED** |
| **EXP-04 Best Checkpoint** | `experiments/performance/exp04_hard_neg_ablation/best_model.pt` | `FAC3C313386F3FE561C2ECF0945B7F960CAA74897C5E8105FB68635529F1320B` | $292,466,907$ | **CERTIFIED UNCHANGED** |
| **EXP-05 Best Checkpoint** | `experiments/performance/exp05_candidate_severity_cap/best_model.pt` | `D9FC12E312E5DF012650E8106DCF90782534EFB1BD1E38BA7FDCF4E0802A0481` | $292,467,395$ | **CERTIFIED UNCHANGED** |
| **EXP-06 Best Checkpoint (Epoch 9)** | `experiments/performance/exp06_positive_bce_weight/best_model.pt` | `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` | $292,461,395$ | **CERTIFIED AUTHORITATIVE** |
| **EXP-06 Last Checkpoint (Epoch 10)** | `experiments/performance/exp06_positive_bce_weight/last_model.pt` | `9CA4D910C4804AC994EF8C3E8C96A88AC93BDA2FFD76F9C0817E6C54803D8025` | $292,461,395$ | **CERTIFIED AUTHORITATIVE** |
| **Capped Candidate Manifest** | `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json` | `3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4` | $261,621$ | **CERTIFIED UNCHANGED** |
| **Spatial Split Manifest** | `data/metadata/trujillo_2024/spatial_split_manifest.json` | `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` | $5,748,446$ | **CERTIFIED UNCHANGED** |

### Reconciliation of Teacher Checkpoint SHA Discrepancy
* **Audited Prompt Variant:** `9B8BD867DC02C68CC062125074E8E21789FBBBAA55C903D55D8904003BDD1699`
* **Authoritative On-Disk Digest:** `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
* **Discrepancy Analysis:** Character at index 28 (the 29th character) is `B` on disk vs. `E` in the prompt string.
* **Audit Disposition:** **REPORTING TYPO IN PROMPT**. The file on disk was verified directly via Python SHA-256 calculation. The binary has not changed. The on-disk hash is authoritative.

---

## 3. Training & Verification Lifecycle Certification

1. **Training Lifecycle:**
   - **Start:** `2026-09-12T03:45:54.406955+00:00`
   - **Completion:** `2026-09-12T07:35:51.570748+00:00`
   - **Duration:** $13,798.2\text{ s}$ ($230.0\text{ minutes}$)
   - **Epochs:** Exactly 10 / 10 epochs completed ($8,960 / 8,960$ optimizer steps).
   - **Global Best Epoch:** **Epoch 9** (Validation IoU = $0.72168$).
   - **Process Exit Code:** `0` (Success).
2. **Independent Verification Lifecycle:**
   - **Execution Script:** `scratch/independent_verify_exp06.py`
   - **Execution Task:** `task-5522` (`num_workers = 0`, project venv, CUDA)
   - **Completion:** `2026-09-12T07:38:10Z` (Duration: $119.3\text{ s}$, exit code 0)
   - **Validation Scope:** Evaluated all $2,880$ canonical Part I validation tiles ($180$ batches) at $\tau = 0.22$.
   - **Part III Isolation:** Strictly zero Part III tiles loaded or accessed.
   - **Status Reconciliation:** The transient note "is running" from earlier assistant output was an intermediate progress update while background task `task-5522` was executing; the task has completed and generated all verified artifacts.

---

## 4. Exact Integer Confusion Matrix & Metric Derivations

From `experiments/performance/exp06_positive_bce_weight/independent_validation_verification.json`:

### Confusion Matrix Integers (2,880 Tiles, 754,974,720 Total Pixels)
* **True Positives (TP):** $13,097,786\text{ px}$
* **False Positives (FP):** $2,009,530\text{ px}$
* **False Negatives (FN):** $3,041,747\text{ px}$
* **True Negatives (TN):** $736,825,657\text{ px}$
* **Sum Verification:** $13,097,786 + 2,009,530 + 3,041,747 + 736,825,657 = 754,974,720\text{ px}$ ($2,880 \times 512 \times 512$, $100.000\%$ accounted).

### Mathematical Metric Recomputations

| Metric | Formula | Calculated Value | Reported Value | Difference | Reconciliation Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Validation IoU** | $\frac{\text{TP}}{\text{TP} + \text{FP} + \text{FN}}$ | $\frac{13,097,786}{18,149,063} = 0.7216784...$ | `0.72168` | $0.00000$ | **DERIVATION MATCH** |
| **Validation Recall** | $\frac{\text{TP}}{\text{TP} + \text{FN}}$ | $\frac{13,097,786}{16,139,533} = 0.8115344...$ | `0.81153` | $0.00000$ | **DERIVATION MATCH** |
| **Validation Precision** | $\frac{\text{TP}}{\text{TP} + \text{FP}}$ | $\frac{13,097,786}{15,107,316} = 0.8669830...$ | `0.86698` | $0.00000$ | **DERIVATION MATCH** |
| **Validation Dice** | $\frac{2\cdot\text{TP}}{2\cdot\text{TP} + \text{FP} + \text{FN}}$ | $\frac{26,195,572}{31,246,849} = 0.8383428...$ | `0.83834` | $0.00000$ | **DERIVATION MATCH** |
| **Clean-Water FAR** | $\frac{10\text{ FA Tiles}}{1827\text{ Clean Tiles}}$ | $\frac{10}{1827} = 0.547345\%...$ | `0.55%` | $0.00\%$ | **DERIVATION MATCH** |
| **Significant FAR** | $\frac{10\text{ Sig FA Tiles}}{1827\text{ Clean Tiles}}$ | $\frac{10}{1827} = 0.547345\%...$ | `0.55%` | $0.00\%$ | **DERIVATION MATCH** |
| **Clean-Water FP Pixels (Empty Validation Tiles)** | Sum of FP on clean tiles | $113,187\text{ px}$ | `113,187` | $0$ | **EXACT MATCH** |

---

## 5. Acceptance Gate Recomputation & Certification

Recomputed against authoritative on-disk independent verification values:

| Gate | Registered Criterion | Recomputed Actual Value | Acceptance Headroom (Passing Margin) | Signed Delta (Observed − Limit) | Audit Result |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **Gate 1** | **Validation Recall $\ge 0.78500$** | **$0.81153$** | **$+0.02653$ ($+2.653\text{ pp}$)** | $+0.02653$ ($+2.653\text{ pp}$) | **PASS** |
| **Gate 2** | **Validation IoU $\ge 0.71731$** | **$0.72168$** | **$+0.00437$ ($+0.437\text{ pp}$)** | $+0.00437$ ($+0.437\text{ pp}$) | **PASS** |
| **Gate 3** | **Clean-Water FAR $< 5.00\%$** | **$0.55\%$** | **$+4.45\text{ pp}$** | $-4.45\text{ pp}$ | **PASS** |
| **Gate 4** | **Significant FAR $< 3.00\%$** | **$0.55\%$** | **$+2.45\text{ pp}$** | $-2.45\text{ pp}$ | **PASS** |
| **Gate 5** | **Clean-Water FP Pixels (Empty Validation Tiles) $< 350,000$** | **$113,187$** | **$+236,813\text{ px}$** | $-236,813\text{ px}$ | **PASS** |

*Acceptance Headroom Definition:* For lower-bound gates (Gates 1 & 2), $\text{Headroom} = \text{Observed} - \text{Required Minimum}$. For upper-bound gates (Gates 3, 4 & 5), $\text{Headroom} = \text{Required Maximum} - \text{Observed}$. All five positive headrooms indicate PASS. The Signed Delta ($\text{Observed} - \text{Limit}$) is provided for directional displacement.

**Gate Certification:** **5 / 5 GATES PASSED (100.0%)**.

### Gate #5 Forensic Semantic Audit & Resolution:
* **Contracted Quantity:** In the earliest authoritative pre-training contract document (`experiments/PHASE_5G_EXP06_HYPOTHESIS_AND_TRAINING_CONTRACT_20260912.md`), Gate 5 is explicitly stated in Section 2 (line 31) as: *"Total FP pixels on empty validation tiles rises to $\ge 350,000\text{ pixels}$"* and in Section 6 (line 106) as *"Total FP Pixels (Empty) $< 350,000$"*.
* **Implementation:** `scripts/train_exp06.py` (line 281) accumulates this metric strictly on empty tiles (`if m_sum == 0: total_fp_pixels += fp_px`), evaluating to $113,187\text{ px}$.
* **Independent Verifier:** `scratch/independent_verify_exp06.py` (line 165) evaluates identical logic (`if m_sum == 0: total_fp_pixels += p_sum`), confirming $113,187\text{ px}$.
* **Total Validation FP:** Global confusion matrix FP is $2,009,530\text{ px}$, which partitions exactly into $113,187\text{ px}$ on empty ocean tiles and $1,896,343\text{ px}$ on positive slick tiles ($113,187 + 1,896,343 = 2,009,530\text{ px}$).
* **Disposition:** **CASE A (CONTRACT CLEARLY DEFINES CLEAN-WATER / EMPTY-TILE FP)**. PASS is certified. Shorthand report labeling amended to prevent conflation.

### Complete Formal Five-Stage Gate-Trace:

```
ORIGINAL CONTRACT (Phase 5G Contract §2 & §6)
    ↓
IMPLEMENTATION (scripts/train_exp06.py)
    ↓
TRAINING ARTIFACT (history.json & metrics.json)
    ↓
INDEPENDENT VERIFIER (scratch/independent_verify_exp06.py -> independent_validation_verification.json)
    ↓
FINAL REPORT (PHASE_5H_EXP06_TRAINING_EXECUTION_REPORT_20260912.md)
```

| Gate ID | Original Contract Wording | Mathematical Definition | Threshold | Authoritative Contract File | Implementation Location | Test / Guardrail Location | Training Metric Source | Independent Verifier Source | Final Report Wording | Final Value | Recomputed Value | Pass / Fail | Semantic Consistency | Disposition |
| :---: | :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Gate 1** | `Validation Recall >= 0.78500` | $\frac{\text{TP}}{\text{TP} + \text{FN}}$ over Part I val | $\ge 0.78500$ | `PHASE_5G_EXP06_HYPOTHESIS_AND_CONTRACT_20260912` §2, §6 | `SegmentationMeter.compute()['recall']` | `test_phase_5h_preflight.py` | `history.json` (Epoch 9) & `metrics.json` | `independent_validation_verification.json` | Validation Recall | `0.81153` | `0.8115344` | **PASS** | CONSISTENT | Verified |
| **Gate 2** | `Validation IoU >= 0.71731` | $\frac{\text{TP}}{\text{TP} + \text{FP} + \text{FN}}$ over Part I val | $\ge 0.71731$ | `PHASE_5G_EXP06_HYPOTHESIS_AND_CONTRACT_20260912` §2, §6 | `SegmentationMeter.compute()['iou']` | `test_phase_5h_preflight.py` | `history.json` (Epoch 9) & `metrics.json` | `independent_validation_verification.json` | Validation IoU | `0.72168` | `0.7216784` | **PASS** | CONSISTENT | Verified |
| **Gate 3** | `Clean-Water FAR < 5.00%` | $\frac{\text{Empty Tiles with FP} \ge 1}{1827} \times 100$ | $< 5.00\%$ | `PHASE_5G_EXP06_HYPOTHESIS_AND_CONTRACT_20260912` §2, §6 | `train_exp06.py:evaluate_validation` | `test_phase_5_guardrails.py` | `history.json` (Epoch 9) & `metrics.json` | `independent_validation_verification.json` | Clean-Water FAR | `0.55%` | `0.54735%` | **PASS** | CONSISTENT | Verified |
| **Gate 4** | `Significant FAR < 3.00%` | $\frac{\text{Empty Tiles with FP} \ge 100}{1827} \times 100$ | $< 3.00\%$ | `PHASE_5G_EXP06_HYPOTHESIS_AND_CONTRACT_20260912` §2, §6 | `train_exp06.py:evaluate_validation` | `test_phase_5_guardrails.py` | `history.json` (Epoch 9) & `metrics.json` | `independent_validation_verification.json` | Significant FAR | `0.55%` | `0.54735%` | **PASS** | CONSISTENT | Verified |
| **Gate 5** | `Total FP pixels on empty validation tiles < 350,000` | $\sum_{i \in \text{empty tiles}} \text{FP}_i$ | $< 350,000$ | `PHASE_5G_EXP06_HYPOTHESIS_AND_CONTRACT_20260912` §2, §6 | `train_exp06.py` (`if m_sum == 0: fp += p`) | `test_phase_5_guardrails.py` | `history.json` (Epoch 9) & `metrics.json` | `independent_validation_verification.json` | Clean-Water FP Pixels (Empty Validation Tiles) | `113,187` | `113,187` | **PASS** | NAMING_ERROR (in report label) | Verified & Repaired |

---

## 6. Five-Way Longitudinal Progression (Evaluated at Coherent Operating Threshold $\tau = 0.22$)

All models below are compared at the frozen canonical operating threshold $\mathbf{\tau = 0.22}$ across all $2,880$ Part I validation tiles ($1,827$ clean-water, $1,053$ GT-positive). Each column represents a single, coherent evaluation configuration without cross-threshold mixing:

| Metric | EXP-01 Teacher ($\tau=0.22$) | EXP-03 (12.5% Mined) | EXP-04 (6.25% Mined) | EXP-05 (50k Cap) | EXP-06 (pos_weight=2.0) | EXP-05 $\rightarrow$ EXP-06 $\Delta$ | EXP-01 $\rightarrow$ EXP-06 $\Delta$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Validation IoU** | 0.72231 | 0.70435 | 0.70910 | 0.70813 | **0.72168** | **+0.01355 (+1.355 pp)** | -0.00063 (-0.063 pp)* |
| **Validation Recall** | 0.82653 | 0.77287 | 0.78230 | 0.78227 | **0.81153** | **+0.02926 (+2.926 pp)** | -0.01500 (-1.500 pp) |
| **Validation Precision** | 0.85138 | 0.88820 | 0.88343 | 0.88197 | **0.86698** | -0.01499 (-1.499 pp) | **+0.01560 (+1.560 pp)** |
| **Validation Dice** | 0.83877 | 0.82653 | 0.82979 | 0.82913 | **0.83834** | **+0.00921 (+0.921 pp)** | -0.00043 (-0.043 pp) |
| **Clean-Water FAR (%)** | 20.09% | 0.33% | 0.55% | 0.49% | **0.55%** | +0.06 pp | **-19.54 pp (-97.3% rel)** |
| **Significant FAR (%)** | 10.56% | 0.33% | 0.55% | 0.49% | **0.55%** | +0.06 pp | **-10.01 pp (-94.8% rel)** |
| **Clean-Water FP Pixels (Empty Tiles)** | 465,950 | 79,742 | 122,937 | 129,041 | **113,187** | **-15,854 px (-12.29%)** | **-352,763 px (-75.71%)** |
| **Slick-Tile FP Pixels (Positive Tiles)** | 1,862,663 | 1,490,347 | 1,543,063 | 1,560,625 | **1,896,343** | +335,718 px (+21.51%) | +33,680 px (+1.81%) |
| **Global Confusion-Matrix FP** | 2,328,613 | 1,570,089 | 1,666,000 | 1,689,666 | **2,009,530** | +319,864 px (+18.93%) | **-319,083 px (-13.70%)** |
| **Total FN Pixels** | 2,799,742 | 3,664,417 | 3,513,632 | 3,514,098 | **3,041,747** | **-472,351 px (-13.44%)** | +242,005 px (+8.64%) |
| **Dropped Pos Tiles** | 59 | 227 | 231 | 203 | **174** | **-29 tiles (-14.29%)** | +115 tiles |

*\*Note on Gate 2 Non-Inferiority Floor Derivation:* The preregistered Gate 2 non-inferiority bound ($\ge 0.71731$) was formally derived in `PHASE_5B_HARD_NEGATIVE_TRAINING_CONTRACT_20260911.md` §4.2 as $0.72231 - 0.0050 = \mathbf{0.71731}$. EXP-06 ($0.72168$) clears this non-inferiority bound by $+0.00437$ ($+0.437\text{ pp}$), confirming non-inferiority against the baseline operating point.

*\*\*Note on EXP-01 FP Partition and Historical Provenance:*
- **Authoritative Empty-Tile Baseline (Gate 5 Scope):** Strictly evaluated on the $1,827$ pure empty clean-water validation tiles (367 with false alarms), EXP-01 recorded **$465,950\text{ FP px}$** (`failure_analysis_report.json`, line 48). Against this authoritative empty-tile baseline, EXP-06 ($113,187\text{ px}$) represents a **$-352,763\text{ px}$ ($-75.71\%$) reduction**.
- **Authoritative Slick-Tile Baseline:** On the $1,053$ positive validation tiles containing oil slicks, EXP-01 recorded **$1,862,663\text{ FP px}$** ($2,328,613 - 465,950$). EXP-06 recorded **$1,896,343\text{ FP px}$** ($+33,680\text{ px}$, $+1.81\%$).
- **Authoritative Global Confusion-Matrix FP:** Across all $2,880$ validation tiles, EXP-01 recorded **$2,328,613\text{ FP px}$** (`exp02a_threshold_analysis.json`). EXP-06 recorded **$2,009,530\text{ FP px}$** (a **$-319,083\text{ px}$ / $-13.70\%$ reduction**). Note: $465,950 + 1,862,663 = 2,328,613$ (exact conservation, difference == 0).
- **Historical All-Tile Failure Analysis Scalar ($2,327,942$):** In historical Phase 5B-5G artifacts, EXP-01 FP was cited as $2,327,942\text{ px}$ from the Phase 5A streaming failure analysis all-tile sum across 1,268 tiles with false alarms (`failure_analysis_report.json`, lines 62, 78). This differed by $671\text{ px}$ ($0.028\%$) from the global confusion matrix ($2,328,613\text{ px}$). Earlier draft comparison tables had mistakenly placed this all-tile figure into the empty-tiles row; it has now been correctly restored to its historical context.
- **Authoritative Significant FAR:** Significant FAR for EXP-01 is **$10.56\%$** ($193 / 1,827$ empty validation tiles with $\text{FP} \ge 100\text{ px}$, `failure_analysis_report.json` line 34, `PHASE_5B_HARD_NEGATIVE_TRAINING_CONTRACT_20260911.md` line 129). The figure $12.37\%$ was an erroneous cross-experiment conflation originating from intermediate experiment EXP-02C (`exp02c_annealed_hard_negative_20260909_144000/history.json` line 68) and has been completely purged.

### Separate Reference: EXP-01 at Default Sigmoid Midpoint ($\tau = 0.50$)
At the unweighted training evaluation threshold $\tau = 0.50$ (checkpoint selection criterion in `exp01_results.json`):
- $\text{IoU} = 0.71691$, $\text{Recall} = 0.78488$, $\text{Precision} = 0.89223$, $\text{Dice} = 0.83512$, $\text{Global FP} = 1,530,098$, $\text{FN} = 3,471,942$.
- *Provenance Resolution on 2,798,401:* Historical summaries in EXP-04/05 reported an EXP-01 FN value of $2,798,401$. Forensic tracing reveals this originated as a manual transcription error in `scratch/compute_exp04_comparisons.py` differing by $1,341\text{ pixels}$ from the calculated on-disk value ($2,799,742$). It was not rounding and has been removed from all authoritative comparison tables.
- *Provenance Resolution on FP32 vs. AMP FN:* The canonical on-disk FP32 confusion matrix records EXP-01 Total FN as **$2,799,742\text{ px}$** (`exp02a_threshold_analysis.json`). The Phase 5G GPU forensic script (`scratch/run_phase_5g_forensics.py`) evaluated models under mixed-precision AMP, recording EXP-01 Total FN as **$2,799,745\text{ px}$** (`forensics_summary.json`), exactly decomposing into $106,609\text{ px}$ dropout mass and $2,693,136\text{ px}$ partial under-segmentation mass ($106,609 + 2,693,136 = 2,799,745$). The 3-pixel difference is an observed precision-mode reproduction difference; these values are not interchangeable.

---

## 7. Forensic Verification of Mechanism

Forensic breakdown from `exp06_positive_tile_forensics.json`:
- **Partial Under-Segmentation FN Mass:** Reduced from $2,842,762\text{ px}$ to **$2,572,918\text{ px}$** ($-269,844\text{ px}$, $-9.49\%$).
- **Complete Dropout FN Mass:** Reduced from $671,336\text{ px}$ to **$468,829\text{ px}$** ($-202,507\text{ px}$, $-30.16\%$).
- **Complete Tile Dropouts:** Reduced from $203$ to **$174$ tiles** ($-29$ tiles, $-14.29\%$).
- **Large-Slick Recall ($> 19,367\text{ px}$):** Increased from $79.01\%$ to **$81.60\%$**, recovering $286,777\text{ pixels}$ of slick area.
- **Scientific Interpretation:** The observed reductions are consistent with the Phase 5G hypothesis that positive-target BCE weighting could reduce positive under-segmentation, particularly partial FN mass, but the experiment does not by itself establish exclusive causal attribution.

---

## 8. Firewall, Regression, and Git Safety Audits

- **Part III Firewall:** The Phase 5H pipeline recorded zero Part III access/read/evaluation/mining events, and the automated firewall suite passed 6/6 tests across all 7,200 Trujillo Part III benchmark tiles ($450$ scenes $\times 16$ non-overlapping chips: 2,400 Oil, 2,400 No oil, 2,400 Lookalike). **PASS**.
- **Full Test Suite:** `.\venv\Scripts\pytest.exe -rs` executed post-run: **603 passed, 2 skipped, 0 failed, 77 warnings in 158.02s** (605 collected). **PASS**.
- **Git Policy Compliance:** `git diff --cached` is empty (zero files staged). Pre-existing working-tree modifications (`.gitignore`, `src/ocean_sentinel/ingestion/dataset.py`) preserved. Zero commits or pushes performed. **PASS**.

---

## 9. Final Declarations

```
EXP06_TRAINING = PASS
EXP06_INDEPENDENT_VERIFICATION = PASS
EXP06_ACCEPTANCE = PASS
PART_III_FIREWALL = PASS
DATA_LEAKAGE_CONTROLS = PASS
ARTIFACT_INTEGRITY = PASS
REPRODUCIBILITY = PASS
OBSERVABILITY = PASS
WINDOWS_SAFETY = PASS
REGRESSION_TESTS = PASS
LOSS_IMPLEMENTATION_VERIFICATION = PASS
ONE_VARIABLE_PURITY = PASS

UNREGISTERED_VARIABLES_CHANGED = NONE
PRIOR_EXPERIMENTS_MODIFIED = NO
PART_III_ACCESSED = NO
EXCLUDED_CANDIDATES_SAMPLED = NO
```

---

## 10. Final Scientific Disposition

# **EXP-06 DEVELOPMENT/VALIDATION ACCEPTANCE: PASS — CERTIFIED & CLOSED WITHIN THE AUDITED PHASE 5H SCOPE.**

> **Scope Limitation & Certification Boundary:**  
> EXP-06 PASS certifies the predefined development/validation acceptance gates within the audited Phase 5H scope; it does not constitute Part III external evaluation, deployment validation, or evidence of generalization beyond the development/validation domain.

* **Artifact Consistency:** All current canonical artifacts agree within their declared evaluation and provenance contexts; intentionally distinct historical and diagnostic pipelines are explicitly segregated.
* **Acceptance Gates:** All 5 preregistered acceptance gates passed at $\tau = 0.22$: Validation Recall $0.81153$ (Headroom $+0.02653$), Validation IoU $0.72168$ (Headroom $+0.00437$), Clean-Water FAR $0.55\%$ (Headroom $+4.45\text{ pp}$), Significant FAR $0.55\%$ (Headroom $+2.45\text{ pp}$), Clean-Water FP Pixels on Empty Validation Tiles $113,187$ (Headroom $+236,813\text{ px}$).
* **Metric Independence:** Global validation FP ($2,009,530\text{ px}$) and Gate 5 Clean-Water FP Pixels on Empty Validation Tiles ($113,187\text{ px}$) are distinct quantities.
* **FAR Metric Distinction:** Clean-Water FAR and Significant FAR are distinct metrics; they happen to be numerically equal at $0.55\%$ because the same 10 empty validation tiles satisfy both false-alarm definitions for the final EXP-06 checkpoint (all 10 false-positive empty validation tiles contained at least 100 false-positive pixels).
