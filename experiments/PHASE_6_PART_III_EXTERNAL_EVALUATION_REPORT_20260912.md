# Ocean Sentinel — Phase 6: Trujillo Part III External Benchmark Evaluation Report

**Document Identifier:** `PHASE_6_PART_III_EXTERNAL_EVALUATION_REPORT_20260912`  
**Execution Phase:** Phase 6 (External Benchmark Evaluation)  
**Evaluator Role:** Senior Scientific Reporting Auditor / CAO Documentation Closure Agent  
**Authorized Checkpoint:** `EXP-06` Best Checkpoint (`experiments/performance/exp06_positive_bce_weight/best_model.pt`)  
**External Benchmark:** Trujillo Part III (`data/raw/external_validation/trujillo_part_iii/extracted`)  
**Evaluation Units:** Exactly 450 scenes $\times$ 16 tiles = 7,200 tiles per mapping ($14,400$ total tile inferences)  
**Execution Precision:** Strict FP32 (`torch.float32`) end-to-end (zero AMP)  
**Frozen Decision Threshold:** $\tau = 0.22$ on logistic sigmoid probability domain  
**Benchmark Execution Status:** **`COMPLETE`**  
**Official Result Status:** **`OFFICIAL_RESULT_FROZEN = YES`**  
**Final Reporting Audit Disposition:** **`REPORTING_AUDIT = PASS WITH EVIDENCE LIMITATION`** (Scientific Benchmark Passed; Output Artifact Historical Immutability Unestablished)  

---

## 1. Executive Summary & Key External-Benchmark Findings

Under explicit Chief Architect Officer (CAO) authorization, the frozen Ocean Sentinel `EXP-06` development checkpoint was evaluated on the untouched Trujillo Part III external benchmark. The benchmark population comprises exactly 450 dual-polarization SAR scenes ($2048 \times 2048$ resolution, 16 non-overlapping $512 \times 512$ chips per scene, 7,200 tiles per mapping), stratified into 150 `Oil`, 150 `No oil`, and 150 `Lookalike` scenes.

Both pre-registered polarization channel mappings (Mapping A and Mapping B) were evaluated independently in canonical FP32 mode at $\tau = 0.22$. The results were independently audited directly against native GeoTIFF ground-truth masks with exact pixel conservation verification ($1,887,436,800$ total pixels evaluated per mapping).

### Key External-Benchmark Findings:
- **Oil-stratum Mapping A Macro Mean IoU:** **`0.74486`** ($74.49\%$)
- **No-Oil Primary Scene FAR:** **`0.04667`** ($4.67\%$, $7/150$ scenes)
- **Lookalike Primary Scene FAR:** **`0.90667`** ($90.67\%$, $136/150$ scenes)

> [!IMPORTANT]
> **Critical Scope Distinction — Oil-Stratum IoU vs. Whole-Benchmark Global IoU:**  
> The headline value **`0.74486`** ($74.49\%$) is strictly an **Oil-stratum macro mean IoU** (and **`0.72492`** is the **Oil-stratum micro pooled IoU**). It evaluates segmentation performance exclusively across the 150 scenes within the `Oil` stratum. It deliberately excludes the false-positive pixel burden accumulated over the `No oil` and `Lookalike` strata from the segmentation denominator. When evaluated over the full benchmark population ($N=450$ scenes), the **Whole-Benchmark Global Pixel IoU** is **`25.21%`** for Mapping A (due to lookalike false alarms). The Oil-stratum metric applies exclusively to the positive stratum and must not be represented as a whole-benchmark segmentation score.

---

## 2. Four-Level Metric Firewall

To ensure scientific integrity and prevent conflation of stratum-specific segmentation with whole-benchmark error burdens, all benchmark performance metrics are partitioned into an explicit four-level firewall:

### LEVEL A — OIL STRATUM SEGMENTATION ($N=150$ scenes with ground-truth oil slicks)
*Exclusively evaluates slick boundary delineation and coverage on scenes containing verified oil spills. Excludes No-Oil and Lookalike false positives.*

| Authoritative Metric | Mapping A (Direct: Band 1 $\rightarrow$ Ch0, Band 2 $\rightarrow$ Ch1) | Mapping B (Inverted: Band 2 $\rightarrow$ Ch0, Band 1 $\rightarrow$ Ch1) | Signed Delta (A − B) |
|---|:---:|:---:|:---:|
| **Oil-stratum Macro Mean IoU** | **`0.74486`** ($74.49\%$) | **`0.09171`** ($9.17\%$) | **`+0.65315`** ($+65.31\text{ pp}$) |
| **Oil-stratum Micro Pooled IoU** | **`0.72492`** ($72.49\%$) | **`0.09223`** ($9.22\%$) | **`+0.63269`** ($+63.27\text{ pp}$) |
| **Oil-stratum Macro Mean Dice ($F_1$)** | **`0.84070`** ($84.07\%$) | **`0.14975`** ($14.97\%$) | **`+0.69095`** ($+69.10\text{ pp}$) |
| **Oil-stratum Macro Mean Precision** | **`0.83964`** ($83.96\%$) | **`0.09463`** ($9.46\%$) | **`+0.74501`** ($+74.50\text{ pp}$) |
| **Oil-stratum Macro Mean Recall** | **`0.89086`** ($89.09\%$) | **`0.96174`** ($96.17\%$) | **`-0.07088`** ($-7.09\text{ pp}$) |
| **Oil-stratum Macro Median IoU** | **`0.78512`** ($78.51\%$) | **`0.04734`** ($4.73\%$) | **`+0.73778`** ($+73.78\text{ pp}$) |
| **Oil-stratum Macro Median Recall** | **`0.97126`** ($97.13\%$) | **`1.00000`** ($100.00\%$) | **`-0.02874`** ($-2.87\text{ pp}$) |

### LEVEL B — CLEAN WATER / NO-OIL STRATUM ($N=150$ scenes with zero oil slicks)
*Evaluates baseline operational false-alarm generation over open water lacking mineral slicks.*

| Authoritative Metric | Mapping A (Direct) | Mapping B (Inverted) | Signed Delta (A − B) |
|---|:---:|:---:|:---:|
| **No-Oil Primary Scene FAR** ($\mathbb{I}(FP > 0)$) | **`0.04667`** ($4.67\%$, $7/150$ scenes) | **`0.92000`** ($92.00\%$, $138/150$ scenes) | **`-0.87333`** ($-87.33\text{ pp}$) |
| **No-Oil Clean Scene Rejection Rate** ($1 - \text{Scene FAR}$) | **`0.95333`** ($95.33\%$, $143/150$ scenes) | **`0.08000`** ($8.00\%$, $12/150$ scenes) | **`+0.87333`** ($+87.33\text{ pp}$) |
| **No-Oil Significant Scene FAR** ($\mathbb{I}(FP \ge 100)$) | **`0.04667`** ($4.67\%$, $7/150$ scenes) | **`0.90000`** ($90.00\%$, $135/150$ scenes) | **`-0.85333`** ($-85.33\text{ pp}$) |
| **No-Oil Total FP Pixel Burden** | **`95,157`** pixels ($0.015\%$ of clean surface) | **`373,131,634`** pixels ($59.31\%$ of clean surface) | **`-373,036,477`** pixels |
| **No-Oil Mean FP Pixels / Scene** | **`634.38`** pixels (Median: `0.0`) | **`2,487,544.23`** pixels (Median: `3,685,494.5`) | **`-2,486,909.85`** pixels |
| **No-Oil Maximum FP Pixels in Scene** | **`43,007`** pixels ($1.03\%$ of scene) | **`4,194,304`** pixels ($100.00\%$ of scene) | **`-4,151,297`** pixels |
| **No-Oil Pixel Specificity** ($\frac{TN}{TN+FP}$) | **`0.99985`** ($99.985\%$) | **`0.40692`** ($40.69\%$) | **`+0.59293`** ($+59.29\text{ pp}$) |

*Note on Denominators & Terminology: The clean-water stratum surface consists of $150 \text{ scenes} \times 2048 \times 2048 = 629,145,600 \text{ pixels}$. Total FP pixel burdens represent proportions of this stratum surface. Primary Scene FAR ($4.67\%$) and Clean Scene Rejection Rate ($95.33\%$) are scene-level binomial metrics and must never be labeled or conflated with pixel-level specificity ($99.985\%$).*

### LEVEL C — LOOKALIKE STRATUM ($N=150$ scenes containing natural low-backscatter ocean features)
*Evaluates discrimination against dark ocean lookalike phenomena (biogenic films, low-wind shadows, internal waves, upwelling).*

| Authoritative Metric | Mapping A (Direct) | Mapping B (Inverted) | Signed Delta (A − B) |
|---|:---:|:---:|:---:|
| **Lookalike Primary Scene FAR** ($\mathbb{I}(FP > 0)$) | **`0.90667`** ($90.67\%$, $136/150$ scenes) | **`0.98000`** ($98.00\%$, $147/150$ scenes) | **`-0.07333`** ($-7.33\text{ pp}$) |
| **Lookalike Significant Scene FAR** ($\mathbb{I}(FP \ge 100)$) | **`0.90000`** ($90.00\%$, $135/150$ scenes) | **`0.98000`** ($98.00\%$, $147/150$ scenes) | **`-0.08000`** ($-8.00\text{ pp}$) |
| **Lookalike Total FP Pixel Burden** | **`130,502,095`** pixels ($20.74\%$ of lookalike surface) | **`478,285,600`** pixels ($76.02\%$ of lookalike surface) | **`-347,783,505`** pixels |
| **Lookalike Mean FP Pixels / Scene** | **`870,013.97`** pixels (Median: `276,174.0`) | **`3,188,570.67`** pixels (Median: `3,753,396.0`) | **`-2,318,556.70`** pixels |
| **Lookalike Maximum FP Pixels in Scene** | **`4,188,549`** pixels ($99.86\%$ of scene) | **`4,194,304`** pixels ($100.00\%$ of scene) | **`-5,755`** pixels |
| **Lookalike Pixel Specificity** ($\frac{TN}{TN+FP}$) | **`0.79257`** ($79.26\%$) | **`0.23979`** ($23.98\%$) | **`+0.55278`** ($+55.28\text{ pp}$) |

*Note on Denominators: The lookalike stratum surface consists of $150 \text{ scenes} \times 2048 \times 2048 = 629,145,600 \text{ pixels}$. Total FP pixel burdens represent proportions of this stratum surface, distinct from whole-benchmark surface area.*

### LEVEL D — WHOLE-BENCHMARK PIXEL CONFUSION ($N=450$ scenes, $1,887,436,800$ total pixels)
*Comprehensive pixel-level confusion matrix independently verified directly against native ground-truth masks.*

| Dimension | Ground-Truth Invariant | Mapping A Recomputed Count | Mapping B Recomputed Count | Discrepancy | Status |
|---|---|---|---|:---:|:---:|
| **Whole-Benchmark True Positives ($TP$)** | Direct verification | $50,477,786$ | $56,333,470$ | $0$ | **VERIFIED** |
| **Whole-Benchmark False Positives ($FP$)** | Direct verification | $137,727,437$ | $1,399,686,042$ | $0$ | **VERIFIED** |
| **Whole-Benchmark False Negatives ($FN$)** | Direct verification | $12,024,201$ | $6,168,517$ | $0$ | **VERIFIED** |
| **Whole-Benchmark True Negatives ($TN$)** | Direct verification | $1,687,207,376$ | $425,248,771$ | $0$ | **VERIFIED** |
| **Whole-Benchmark Foreground Conservation** | $TP + FN == N_{\text{fg}}$ | $50,477,786 + 12,024,201 = 62,501,987$ | $56,333,470 + 6,168,517 = 62,501,987$ | $0$ | **EXACT MATCH** |
| **Whole-Benchmark Background Conservation** | $FP + TN == N_{\text{bg}}$ | $137,727,437 + 1,687,207,376 = 1,824,934,813$ | $1,399,686,042 + 425,248,771 = 1,824,934,813$ | $0$ | **EXACT MATCH** |
| **Whole-Benchmark Total Pixel Conservation** | $TP + FP + FN + TN == \text{Total}$ | $1,887,436,800$ | $1,887,436,800$ | $0$ | **EXACT MATCH** |
| **Whole-Benchmark Pixel Specificity** | $\frac{TN}{TN + FP}$ | **`0.92453`** ($92.45\%$) | **`0.23302`** ($23.30\%$) | $0$ | **DERIVED** |
| **Whole-Benchmark Global Pixel IoU** | $\frac{TP}{TP + FP + FN}$ | **`0.25209`** ($25.21\%$) | **`0.03853`** ($3.85\%$) | $0$ | **DERIVED** |

### Synthesis of All Evaluated Strata & Whole Benchmark (Signed Deltas)
*Direct comparison between Mapping A and Mapping B across all four evaluation levels.*

| Evaluation Level | Authoritative Metric | Mapping A (Direct) | Mapping B (Inverted) | Signed Delta (A − B) |
|---|---|:---:|:---:|:---:|
| **Level A: Oil Stratum** ($N=150$) | **Oil Macro IoU** | `0.74486` ($74.49\%$) | `0.09171` ($9.17\%$) | **`+0.65315`** ($+65.31\text{ pp}$) |
| **Level A: Oil Stratum** ($N=150$) | **Oil Micro IoU** | `0.72492` ($72.49\%$) | `0.09223` ($9.22\%$) | **`+0.63269`** ($+63.27\text{ pp}$) |
| **Level A: Oil Stratum** ($N=150$) | **Oil Dice** | `0.84070` ($84.07\%$) | `0.14975` ($14.97\%$) | **`+0.69095`** ($+69.10\text{ pp}$) |
| **Level A: Oil Stratum** ($N=150$) | **Oil Precision** | `0.83964` ($83.96\%$) | `0.09463` ($9.46\%$) | **`+0.74501`** ($+74.50\text{ pp}$) |
| **Level A: Oil Stratum** ($N=150$) | **Oil Recall** | `0.89086` ($89.09\%$) | `0.96174` ($96.17\%$) | **`-0.07088`** ($-7.09\text{ pp}$) |
| **Level B: Clean Water** ($N=150$) | **No-Oil Primary Scene FAR** | `0.04667` ($4.67\%$) | `0.92000` ($92.00\%$) | **`-0.87333`** ($-87.33\text{ pp}$) |
| **Level B: Clean Water** ($N=150$) | **No-Oil Clean Scene Rejection Rate** | `0.95333` ($95.33\%$) | `0.08000` ($8.00\%$) | **`+0.87333`** ($+87.33\text{ pp}$) |
| **Level B: Clean Water** ($N=150$) | **No-Oil Significant Scene FAR** | `0.04667` ($4.67\%$) | `0.90000` ($90.00\%$) | **`-0.85333`** ($-85.33\text{ pp}$) |
| **Level B: Clean Water** ($N=150$) | **No-Oil Total FP Pixel Burden** | `95,157` pixels | `373,131,634` pixels | **`-373,036,477`** pixels |
| **Level B: Clean Water** ($N=150$) | **No-Oil Pixel Specificity** | `0.99985` ($99.985\%$) | `0.40692` ($40.69\%$) | **`+0.59293`** ($+59.29\text{ pp}$) |
| **Level C: Lookalike** ($N=150$) | **Lookalike Primary Scene FAR** | `0.90667` ($90.67\%$) | `0.98000` ($98.00\%$) | **`-0.07333`** ($-7.33\text{ pp}$) |
| **Level C: Lookalike** ($N=150$) | **Lookalike Significant Scene FAR** | `0.90000` ($90.00\%$) | `0.98000` ($98.00\%$) | **`-0.08000`** ($-8.00\text{ pp}$) |
| **Level C: Lookalike** ($N=150$) | **Lookalike Total FP Pixel Burden** | `130,502,095` pixels | `478,285,600` pixels | **`-347,783,505`** pixels |
| **Level C: Lookalike** ($N=150$) | **Lookalike Pixel Specificity** | `0.79257` ($79.26\%$) | `0.23979` ($23.98\%$) | **`+0.55278`** ($+55.28\text{ pp}$) |
| **Level D: Whole Benchmark** ($N=450$) | **Whole-Benchmark Pixel Specificity** | `0.92453` ($92.45\%$) | `0.23302` ($23.30\%$) | **`+0.69151`** ($+69.15\text{ pp}$) |
| **Level D: Whole Benchmark** ($N=450$) | **Whole-Benchmark Global Pixel IoU** | `0.25209` ($25.21\%$) | `0.03853` ($3.85\%$) | **`+0.21356`** ($+21.36\text{ pp}$) |


---

## 3. Core Scientific Findings (Evidence-Bounded)

### Finding 1: Strong Oil-Stratum Slick Segmentation Generalization (Mapping A)
On external imagery under canonical channel alignment (Mapping A), `EXP-06` achieved **`0.74486` Oil-stratum macro mean IoU** ($72.49\%$ micro-pooled) and **`0.84070` Oil-stratum macro Dice** with **`0.89086` Recall**. This demonstrates effective cross-domain morphological transfer of oil slick segmentation from Part I training imagery to Part III external scenes when evaluating scenes containing true slicks.

### Finding 2: Low False-Alarm Burden on Clean Water (Mapping A)
Over clean open water (`No oil` stratum, 150 scenes), the model demonstrated a **95.33% clean scene rejection rate** (only $4.67\%$ No-Oil Primary Scene FAR, 7 scenes with false alarms). The median scene false-alarm count was exactly `0.0` pixels, and total false-positive pixels across all 150 clean scenes amounted to only `95,157` pixels ($0.015\%$ of clean-water stratum surface area, $629,145,600 \text{ px}$). Calculated on the stratum pixel population, clean-water pixel specificity is **`99.985%`**.

### Finding 3: Substantial Vulnerability to the Benchmark Lookalike Class
Over dark ocean lookalike phenomena (`Lookalike` stratum, 150 scenes containing biogenic films, wind shadows, internal waves, or upwelling), the evaluation revealed substantial vulnerability of the frozen single-pass 2D SAR configuration to the benchmark Lookalike class:
- Under Mapping A, 136 of 150 Lookalike scenes contained at least one false-positive pixel, corresponding to a Primary Scene FAR of **`90.67%`**.
- The total false-positive pixel burden was **`130,502,095` pixels** ($20.74\%$ of the lookalike stratum surface area, $629,145,600 \text{ px}$).
- Lookalike stratum pixel specificity was **`79.26%`**.

*Scientific Bound on Lookalike Remediation:* While hard-negative mining in EXP-03 through EXP-06 maintained clean-water false alarms at low levels, the tested single-pass 2D SAR configuration exhibited high vulnerability to benchmark lookalikes. Multi-temporal SAR coherence and/or auxiliary environmental information (such as wind fields or sea surface temperature) are plausible future avenues to investigate, but their effectiveness was not tested in this benchmark.

### Finding 4: High Model Sensitivity to Channel Ordering
The frozen model exhibited strong sensitivity to the tested channel ordering. Under the fixed evaluation protocol, Mapping A substantially outperformed Mapping B:
- Oil-stratum Macro Mean IoU dropped by **$65.31\text{ pp}$** ($74.49\% \rightarrow 9.17\%$).
- No-Oil Primary Scene FAR escalated by **$87.33\text{ pp}$** ($4.67\% \rightarrow 92.00\%$, generating $373\text{M}$ false-positive pixels).
- Lookalike Primary Scene FAR escalated to **$98.00\%$** ($478\text{M}$ false-positive pixels).
- Whole-Benchmark pixel specificity dropped from **$92.45\%$** to **$23.30\%$**.

The model exhibited catastrophic performance degradation under inverted channel ordering across all evaluation strata. This confirms that the trained weights of `ResNet34UNet` are strongly coupled to the channel ordering of the training distribution. Physical channel identity and causal interpretations (e.g. relating channels to specific polarization states or backscatter statistics) are not inferred from performance alone and are governed by source sensor documentation.

---

## 4. Cryptographic Provenance & Runtime Environment

### Authoritative Artifact Hashes (Direct On-Disk Recalculation)
- **Repository Baseline Commit:** `542bab19f6f08c9bba8b8762e6480386c8b6026b` (`master`)
- **Evaluation Checkpoint:** `experiments/performance/exp06_positive_bce_weight/best_model.pt`
  - Byte Size: `292,461,395` bytes
  - Full SHA-256: `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF`
  - Trainable Parameters: `24,346,305` (Total: `24,346,305`, Buffers: `19,054`)
  - Checkpoint Epoch: `Epoch 9` (strict load verified)
- **Official Evaluation Runner:** `scripts/run_phase_6_full_evaluation.py`
  - SHA-256: `53D3CC769777B33531048DCE4BBA88FE7F2749E7A3AE4A907983A7C4064A9787`
- **Independent Spot-Check Evaluator:** `scripts/spotcheck_phase_6_independent_inference.py`
  - SHA-256: `D4EEC8CB2315740CAF3B54530E16CA1F1D543CE975F4E5D8A866BF1CD87F354A`
- **Independent Scientific Verifier:** `scripts/independent_verify_phase_6.py`
  - SHA-256: `A7D2C562FF21FF4B50352F39C293910E3EE4D59F5FD83EE82EF5B6A879667798`
- **Model Architecture Implementation:** `src/ocean_sentinel/ml/unet_resnet.py`
  - SHA-256: `E94AA2043EBBED2D33FCA39EC3068D14A51234EDFBB58B1155684965689DFA1F`
- **Authoritative Normalization Source:** `data/metadata/trujillo_2024/spatial_split_manifest.json`
  - SHA-256: `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0`
  - Channel 0: $\mu_0 = -33.233136989478695, \quad \sigma_0 = 6.489985665955077$
  - Channel 1: $\mu_1 = -19.941215852796695, \quad \sigma_1 = 4.531345684833188$
- **Pairing Manifest:** `scratch/trujillo_part_iii_pairing.json`
  - SHA-256: `CF8CA581D1ED8CC0C5832E96C37424197AE1F399F7CC7CE525E73199B35C1DA9`
- **Source Immutability Audit:**
  - 900 / 900 native Part III GeoTIFFs ($450$ images, $450$ masks) verified against pre-evaluation SHA-256 manifest.
  - Zero files modified, deleted, created, or renamed.

### Hardware & Software Environment
- **Operating System:** `Windows-10-10.0.26200-SP0` (64-bit AMD64)
- **Python:** `3.10.9` (tags/v3.10.9:1dd9be6, MSC v.1934)
- **PyTorch:** `2.14.0+cu126` | **Torchvision:** `0.29.0+cu126` | **CUDA:** `12.6`
- **GPU Accelerator:** `NVIDIA GeForce RTX 3050 6GB Laptop GPU` ($5.9995\text{ GB}$ VRAM)
- **System RAM:** $15.69\text{ GB}$ total ($3.90\text{ GB}$ available at launch)
- **Free Disk Space (D: Drive):** $355.32\text{ GB}$ free at launch

---

## 5. Official Artifact Completeness & Independent Verification

The post-evaluation independent audit ([`scripts/independent_verify_phase_6.py`](file:///D:/Projects/ocean-sentinel/scripts/independent_verify_phase_6.py)) consumed zero derived summary JSONs. It directly opened all 450 native source mask GeoTIFFs, asserted bitwise equality with stored target masks, independently binarized FP32 probability mosaics at $\tau = 0.22$, and recalculated all confusion matrix counts from scratch.

- **Total Scenes Planned:** Exactly $450$ scenes
- **Total Tiles Planned:** Exactly $7,200$ tiles per mapping ($14,400$ total)
- **Total Scenes Inferred (Mapping A):** $450$ ($100.0\%$, $0$ failed, $0$ skipped)
- **Total Scenes Inferred (Mapping B):** $450$ ($100.0\%$, $0$ failed, $0$ skipped)
- **Total Scene Artifacts on Disk:** Exactly $900$ `.npz` files (FP32 probability mosaics, uint8 predictions, uint8 targets) and $900$ companion `.json` metadata files.
- **Output Storage Root:** `experiments/performance/phase_6_part_iii_external_evaluation/attempt_001/`
- **Native Mask Bitwise Match:** $450/450$ scenes bitwise identical between native rasterio GeoTIFF and saved target mask.
- **Cross-Mapping Mask Match:** $450/450$ scenes bitwise identical between Mapping A and Mapping B targets.
- **Prediction Reconstruction Match:** $450/450$ scenes bitwise identical between independently recomputed masks and saved prediction masks.

> [!NOTE]
> **Critical Artifact Provenance Distinction:**  
> - **Current Artifact Integrity:** Exactly 900 `.npz` files and 900 `.json` files are currently present on disk with zero missing, zero extra, zero duplicates, and verified metadata consistency (`pair_id`, `checkpoint_sha256`, `threshold = 0.22`, `precision = FP32`, `attempt_id = attempt_001`, `run_id = phase_6_part_iii_external_evaluation`).
> - **Computational / Result Consistency:** Independent reconstruction directly against native GeoTIFF masks verified identical confusion matrix counts and segmentation results with zero discrepancy.
> - **Historical Bitwise Immutability:** Because these large volumetric output artifacts are untracked by Git, historical bitwise immutability of these untracked output artifacts cannot be independently established from the available evidence.


---

## 6. Full Regression Test Suite Results

- **Total Test Items Collected:** `622`
- **Passed:** `620`
- **Skipped:** `2` (historical resume checkpoint tests `tests/test_resume_qualification.py`)
- **Failed:** `0`
- **Execution Duration:** $1098.72\text{ seconds}$ ($0:18:18$)
- **Warnings Summary:** Exactly $77$ warnings:
  - $65\times$ `PendingDeprecationWarning`: Rasterio Affine `@` matmul syntax (benign upstream library notice)
  - $12\times$ `NotGeoreferencedWarning`: Rasterio non-georeferenced GeoTIFF notices (benign, expected for pixel-space arrays)
  - **Warning Classification:** 100% `BENIGN`. Exactly $0$ material or unknown warnings. These warnings concern absent georeferencing metadata in raw pixel-space test inputs; the affected tests operate on pixel values rather than geospatial coordinates.

---

## 7. Permanent Governance Lesson: Metric Scope Is Part of Scientific Correctness

A central scientific lesson established by this benchmark evaluation is that **metric scope is an integral component of scientific correctness**:
- A valid numerical metric can still be scientifically misleading if its evaluation population and scope are not explicitly declared.
- Reporting an IoU of `74.49%` without specifying that it applies strictly to the `Oil` stratum creates the erroneous impression that the model achieved $74.49\%$ IoU across the external benchmark as a whole, concealing the $130.5\text{M}$ false-positive pixels generated over lookalikes.
- Similarly, reporting a clean-water scene rejection rate of `95.33%` as "specificity" conflates a scene-level binomial rate with a pixel-level metric.
- Permanent doctrine requires all future external benchmarks to report metrics under the four-level firewall (stratum segmentation, clean-scene rejection, lookalike vulnerability, and whole-benchmark confusion).

---

## 8. Final Scientific Conclusion

On the authorized Trujillo Part III external benchmark, the frozen EXP-06 model showed strong Oil-stratum segmentation performance under Mapping A (macro IoU 0.74486; macro Dice 0.84070; macro Recall 0.89086), but this performance coexisted with substantial false-positive burden outside the Oil stratum, particularly on the Lookalike class, yielding a whole-benchmark global pixel IoU of 25.21%.

The frozen model exhibited strong sensitivity to the tested channel ordering. Under the fixed evaluation protocol, Mapping B produced markedly poorer Oil-stratum segmentation metrics and much higher scene-level false-alarm rates on the No-Oil and Lookalike strata.

Under Mapping A, 136 of 150 Lookalike scenes contained at least one false-positive pixel, corresponding to a Primary Scene FAR of 90.67%. This characterizes a substantial vulnerability of the tested single-pass 2D SAR configuration to the benchmark Lookalike class. Multi-temporal and/or auxiliary environmental information remain plausible future avenues to investigate, but their effectiveness was not tested in this benchmark.

These results characterize performance on the authorized external benchmark. They do not establish universal generalization, causal superiority of the channel ordering, operational readiness, deployment readiness, or the effectiveness of untested future interventions.
