# Ocean Sentinel — Scientific Evaluation Contract: Trujillo Part III

**Document Identifier:** `TRUJILLO_PART_III_EVALUATION_CONTRACT_20260911`  
**Execution Phase:** Phase 4C (Evaluation Contract + External Benchmark Adapter Design)  
**Dataset Under Contract:** Trujillo Part III (`10.5281/zenodo.13761290`, `02_Test_images_and_ground_truth.7z`)  
**Authority:** Chief Architect Officer (CAO) Mandate  
**Execution Date:** 2026-09-11  
**Baseline Git HEAD:** `542bab19f6f08c9bba8b8762e6480386c8b6026b`  
**Active Git Branch:** `master`  
**ML Forward Passes:** Exactly 0 (Contract Design Only)  
**Contract Status:** **`FROZEN_PENDING_CAO_APPROVAL`**  

---

## 1. Absolute Scientific Firewall and Execution Boundary

This evaluation contract governs all future model evaluation on the Trujillo Part III external benchmark dataset. 

During the formulation and finalization of this contract:
- **ML Forward Passes:** Exactly 0.
- **Model Checkpoints Loaded:** Exactly 0.
- **Inference Models Instantiated:** Exactly 0.
- **Model Weights Evaluated:** Exactly 0.
- **Predictions Generated:** Exactly 0.
- **Benchmark Performance Computed:** None.
- **Threshold Tuning:** Prohibited.
- **Hyperparameter Optimization:** Prohibited.
- **Normalization Fitting on Benchmark Data:** Prohibited.
- **Canonical Dataset / Archive Mutation:** Prohibited (Read-only access strictly enforced).

All evaluation parameters, metrics, aggregation schemas, and sensitivity protocols defined in this document are **pre-specified and frozen before evaluation**. In accordance with the Permanent Principle of Ocean Sentinel:
> *Never let benchmark performance determine the interpretation of the benchmark. Benchmark outcomes shall not be used to resolve unknown physical or semantic properties.*

---

## 2. Section 5.1 — Scientific Question

The Trujillo Part III external benchmark is intended to measure the out-of-domain generalization and false-alarm resistance of the Ocean Sentinel deep learning models (specifically EXP-01 baseline, EXP-02B-1 hard-negative, and EXP-02C annealed hard-negative architectures) when applied to unseen dual-polarization SAR imagery originating from the same upstream repository (Trujillo-Acatitla et al., 2024).

Crucially, the benchmark answers **three distinct scientific questions**, which must never be collapsed into one undifferentiated aggregate metric:

### 2.1 Question 1: Positive Oil Spill Segmentation Fidelity
- **Target Population:** `Oil` directory (150 scenes containing confirmed annotated target polygons).
- **Core Scientific Inquiry:** *Can Ocean Sentinel accurately segment oil slicks in unseen $2048 \times 2048$ SAR scenes, preserving morphological boundaries and detecting slick area under shared repository preprocessing?*
- **Primary Metrics:** Intersection over Union (IoU / Jaccard Index), Dice Coefficient ($F_1$ Score), Precision, and Recall.

### 2.2 Question 2: False-Positive Suppression over Clean Sea Surfaces
- **Target Population:** `No oil` directory (150 scenes containing clean sea surfaces with all-zero target masks).
- **Core Scientific Inquiry:** *Does Ocean Sentinel maintain a clean operational false-alarm rate when surveying open water where no oil spills or confounding lookalikes are present?*
- **Primary Metrics:** False Positive Pixel Count ($FP_{\text{pixels}}$), False Positive Area Ratio ($FP_{\text{ratio}}$), and Scene-Level False Alarm Rate ($\text{FAR}_{\text{scene}}$).

### 2.3 Question 3: Lookalike Discrimination and Hard-Negative Resistance
- **Target Population:** `Lookalike` directory (150 scenes containing low-backscatter oceanic phenomena such as biogenic slicks, wind shadows, upwelling, or internal waves with all-zero target masks).
- **Core Scientific Inquiry:** *Does Ocean Sentinel successfully reject dark oceanic lookalikes without triggering false-positive slick alarms, or does it suffer catastrophic false-alarm collapse when confronted with low-wind features?*
- **Primary Metrics:** Lookalike False Positive Pixel Count ($FP_{\text{lookalike}}$), Lookalike False Positive Area Ratio ($FP_{\text{ratio}}$), and Lookalike Scene-Level False Alarm Rate ($\text{FAR}_{\text{lookalike}}$).

**Prohibition on Single-Metric Pooling:** Under no circumstances shall the performance on `Oil`, `No oil`, and `Lookalike` be averaged into a single unstratified headline mean IoU. Because 300 of the 450 scenes contain all-zero target masks, an unstratified average would be mathematically dominated by clean-water conventions rather than physical detection performance.

---

## 3. Section 5.2 — Evaluation Population and Complete Accounting

The evaluation population is strictly defined by the verified physical extraction inventory cataloged in `scratch/trujillo_part_iii_extracted_inventory.json` and `scratch/trujillo_part_iii_pairing.json`:

| Stratum / Directory | Image Count | Mask Count | Spatial Dimensions | Total Pixels per Raster | Total Stratum Pixels | Foreground Target Pixels | Foreground Area Ratio |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`Oil`** | 150 | 150 | $2048 \times 2048$ | $4,194,304$ | $629,145,600$ | $62,501,987$ | $9.9344\%$ |
| **`No oil`** | 150 | 150 | $2048 \times 2048$ | $4,194,304$ | $629,145,600$ | $0$ | $0.0000\%$ |
| **`Lookalike`** | 150 | 150 | $2048 \times 2048$ | $4,194,304$ | $629,145,600$ | $0$ | $0.0000\%$ |
| **Total Benchmark** | **450** | **450** | **$2048 \times 2048$** | **$4,194,304$** | **$1,887,436,800$** | **$62,501,987$** | **$3.3115\%$** |

### Accounting Invariants:
1. **Zero Silent Exclusions:** Exactly 450 scenes (450 images, 450 masks, total 900 files) constitute the benchmark denominator.
2. **Denominators:**
   - Stratified denominators: $N_{\text{Oil}} = 150$, $N_{\text{No\_oil}} = 150$, $N_{\text{Lookalike}} = 150$.
   - Dataset-wide denominator: $N_{\text{Total}} = 450$ is descriptive only and must not be used as a denominator for stratum-specific metrics.
3. **Audit Trail:** If any sample encounters technical failure during adapter processing or evaluation, its exact absolute path, SHA-256 hash, failure category, independent verification evidence, and impact on the denominator must be logged in the evaluation report.

---

## 4. Section 5.3 — Evaluation Units and Structural Tradeoff Analysis

The native input tensor resolution of Ocean Sentinel's U-Net architecture is $512 \times 512 \times 2$. However, Trujillo Part III rasters are provided as $2048 \times 2048$ full scenes. Three candidate evaluation structures were analyzed:

### Candidate A: Full Scene Native Evaluation
- **Description:** Resampling or interpolating the entire $2048 \times 2048$ scene down to $512 \times 512$ for single-pass inference.
- **Scientific Question Answered:** Macroscopic scene classification.
- **Risk of Metric Distortion:** **CATASTROPHIC.** Resampling SAR backscatter destroys fine slick boundaries, alters spatial frequency content, and violates the frozen $10\,\text{m}$ ground sampling distance (GSD). Mask interpolation would blur discrete $\{0, 1\}$ boundaries into continuous fractions.
- **Decision:** **REJECTED.** No spatial resampling or downsampling is permitted.

### Candidate B: Model-Sized Patch Evaluation ($512 \times 512$)
- **Description:** Tiling each $2048 \times 2048$ scene into 16 non-overlapping $512 \times 512$ chips ($450 \times 16 = 7,200$ total tiles: 2,400 Oil, 2,400 No oil, 2,400 Lookalike). Evaluating each patch independently.
- **Scientific Question Answered:** How does the model perform on localized patches matching its training distribution?
- **Risk of Metric Distortion:** **HIGH.** Evaluating at the patch level inflates the sample denominator by $16\times$. Furthermore, in the `Oil` stratum, many tiles are completely empty (clean water surrounding the slick). Patch-level macro-averaging would heavily penalize or artificially inflate metrics depending on empty-patch conventions.
- **Decision:** **SECONDARY DIAGNOSTIC ONLY.** Useful for patch-level confusion matrices, but rejected as the primary benchmark unit.

### Candidate C: Whole-Scene Reconstructed Mosaic ($2048 \times 2048$) — CANONICAL SELECTION
- **Description:** 
  1. Each $2048 \times 2048$ scene is deterministically partitioned into 16 non-overlapping $512 \times 512$ tiles (row-major order).
  2. Model inference generates logit/probability tiles of shape $(1, 512, 512)$.
  3. The 16 prediction tiles are stitched into a full $2048 \times 2048$ reconstructed probability mosaic using identical offsets.
  4. Binary thresholding ($\tau = 0.22$) is applied to the mosaic, and metrics are computed against the native $2048 \times 2048$ target mask.
- **Scientific Question Answered:** How effectively does Ocean Sentinel survey and detect slicks across an entire operational SAR scene?
- **Scientific Advantages:**
  - Preserves exact 1-to-1 pixel correspondence with the author-provided $2048 \times 2048$ ground truth mask.
  - Zero spatial distortion or interpolation.
  - Exactly 1 observation per physical scene ($N=150$ per stratum), matching the physical acquisition design.
  - Clean water in an oil scene is evaluated in its true context as background to the slick, not as an isolated empty scene.
- **Scientific Risks and Limitations of Candidate C:**
  - *Tile boundary effects:* Receptive fields of convolutional kernels near the edge of each $512 \times 512$ tile lack spatial context from adjacent tiles.
  - *Limited receptive context:* Large continuous oil slicks spanning across tile boundaries are segmented independently without cross-tile feature aggregation.
  - *Prediction seam artifacts:* Reconstructing the mosaic from independent tile predictions can introduce discrete probability discontinuities along tile boundary seams.
  - *Absence of overlap context:* With stride equal to tile size (512), boundary pixels receive single evaluation without blend-averaging or soft windowing.
- **Methodological Distinction:** Structural validation proves that the selected tiling is **geometrically complete**; it does **NOT** prove Candidate C is mathematically or scientifically optimal. Whole-scene reconstructed mosaic is a frozen methodological choice for this evaluation, not a claim of scientifically optimal evaluation design. Candidate C is an adopted methodological choice balancing operational scene realism against computational patch constraints.
- **Decision:** **CANONICAL EVALUATION UNIT.**

---

## 5. Section 5.4 — Mask Semantics and Epistemic Status

Based strictly on direct physical evidence established in Phase 4B-3:
- **Observed Physical Encoding:** Binary-valued mask encoding $\{0, 1\}$ was observed. Mask rasters are stored as 1-band `uint8` GeoTIFFs.
- **Foreground Distribution:** Foreground pixels ($1$) occur exclusively in `Mask/Oil/` ($62,501,987$ pixels).
- **All-Zero Distribution:** 300 target masks are all-zero arrays (100% of masks in `Mask/No oil/` and `Mask/Lookalike/`).
- **Epistemic Limitation:** Upstream container metadata contains no semantic text attributes (e.g., "1 = crude oil slick", "0 = clean ocean"). The semantic mapping is an inference from directory structure. In benchmark reporting, foreground values shall be formally termed **`target-mask foreground`** and background values **`target-mask background`**.
- **Prohibition on Ground-Truth Overclaims:** All-zero masks must NOT be termed "confirmed physical absence of oil" or "field-validated true negatives" as an objective truth claim, because field-level physical ground-truthing was not conducted by Ocean Sentinel.

---

## 6. Section 5.5 — Polarization Channel Policy

### 6.1 Status of Physical Polarization
In GeoTIFF container metadata, image band descriptions are `(None, None)`. The true physical polarization channel order remains **UNKNOWN**.

### 6.2 Pre-Specified Sensitivity Analysis Protocol
The evaluation contract mandates a **pre-specified dual-pass sensitivity protocol frozen before evaluation**:

1. **Mapping A (`MAPPING_A` — Direct Band Order):**
   $$\text{Channel 0} = \text{Band 1}, \quad \text{Channel 1} = \text{Band 2}$$
   - *Rationale:* Band 1 empirical mean ($-26.02$) is lower than Band 2 empirical mean ($-18.71$). In Part I training data, Channel 0 mean was $-33.23$ and Channel 1 mean was $-19.94$. Mapping A aligns the lower-mean band to Channel 0.
2. **Mapping B (`MAPPING_B` — Inverted Band Order):**
   $$\text{Channel 0} = \text{Band 2}, \quad \text{Channel 1} = \text{Band 1}$$
   - *Rationale:* Evaluates the exact reciprocal channel configuration to quantify model sensitivity to polarization ordering.

### 6.3 Mandatory Declaration and Prohibitions
> **"Neither mapping is asserted to represent the true physical polarization order. The two mappings constitute a pre-specified sensitivity analysis over unresolved channel-order uncertainty."**

**ABSOLUTELY PROHIBITED:**
- Running both mappings, selecting the higher-scoring mapping, and declaring it to be "correct".
- Using benchmark performance outcomes to infer or resolve the physical polarization order.
- Averaging the two mappings into a single blended physical score.
- Both results must be reported side-by-side with explicit sensitivity gap:
  $$\Delta_{\text{polarization}} = |\text{Score}_{\text{Mapping A}} - \text{Score}_{\text{Mapping B}}|$$

---

## 7. Section 5.6 & 5.7 — Radiometric and Normalization Policy

### 7.1 Radiometric Status
- **Observed Physical Reality:** Pixel values in Part III images are stored as `float32` with observed negative numerical ranges predominantly in $[-40.0, +10.0]$ (empirical overall means: Band 1 = $-26.02$, Band 2 = $-18.71$).
- **Allowed Epistemic States:**
  - Storage dtype: **KNOWN** (`float32`).
  - Numerical distribution: **KNOWN** (finite real numbers).
  - Physical calibration ($\sigma^0, \gamma^0, \beta^0$): **UNKNOWN**.
  - Physical units ($\text{dB}$ vs linear): **UNKNOWN** (negative numerical values do not prove decibel scaling without metadata tags).
- **Prohibition on Fabricated Physical Calibration:** Negative values do NOT prove decibels. The data must NOT be described as calibrated $\sigma^0$ or confirmed dB. The adapter shall **NOT** apply any uncalibrated physical conversions, arbitrary log offsets, or linear scaling.

### 7.2 Frozen Normalization Policy
Ocean Sentinel's frozen training pipeline applies channel-wise numerical standardization derived strictly from the 840 training patches of Trujillo Part I ($3,523,215,360$ valid pixels):
- **Channel 0 (VV convention):**
  $$\mu_0 = -33.233136989478695, \quad \sigma_0 = 6.489985665955077$$
- **Channel 1 (VH convention):**
  $$\mu_1 = -19.941215852796695, \quad \sigma_1 = 4.531345684833188$$

**Strict Invariants:**
1. **Disaggregation of Transformation from Physical Calibration:**
   > **"The adapter preserves source float32 values and applies the frozen Ocean Sentinel numerical standardization parameters without attempting an uncalibrated physical conversion. Equivalence of Trujillo source units to the physical training-unit interpretation is not independently established."**
   This transform is strictly a **model-input compatibility transformation**; it is NOT "validated physical normalization".
2. **Zero Test-Set Fitting:** Parameters $\mu$ and $\sigma$ shall **NEVER** be fitted, calculated, or adapted on Trujillo Part III. No test-set mean/std adaptation.
3. **Standardization Formula:** For each input channel $c \in \{0, 1\}$:
   $$x_{\text{norm}}[c] = \frac{x[c] - \mu_c}{\sigma_c}$$
4. **Execution Site:** Applied deterministically per tile immediately after channel ordering and prior to tensor collation. Output dtype is `torch.float32`.

---

## 8. Section 5.8 & 5.9 — Tiling and Coordinate Correspondence Contract

### 8.1 Geometric Tiling Specification
- **Parent Scene Dimensions:** $H_{\text{scene}} = 2048$, $W_{\text{scene}} = 2048$.
- **Tile Dimensions:** $H_{\text{tile}} = 512$, $W_{\text{tile}} = 512$.
- **Strides:** $S_y = 512$, $S_x = 512$.
- **Edge Handling Mode:** `drop` (exact grid since $2048 \pmod{512} \equiv 0$).
- **Tile Grid Calculation:**
  $$Y_{\text{offsets}} = [0, 512, 1024, 1536], \quad X_{\text{offsets}} = [0, 512, 1024, 1536]$$
- **Total Tiles per Scene:** Exactly $4 \times 4 = 16$ tiles.
- **Row-Major Deterministic Ordering:**
  Deterministic raster index mapping: `tile_index = row_idx * 4 + col_idx`, where `row_idx, col_idx in {0, 1, 2, 3}`.
  $$\text{tile\_index} = \text{row\_idx} \times 4 + \text{col\_idx}, \quad \text{where } \text{row\_idx}, \text{col\_idx} \in \{0, 1, 2, 3\}$$

### 8.2 Proof of Geometric Completeness
1. **Pixel Accounting:**
   $$\sum_{i=0}^{15} \text{Area}(\text{Tile}_i) = 16 \times (512 \times 512) = 16 \times 262,144 = 4,194,304 \text{ pixels}$$
   $$\text{Area}(\text{Scene}) = 2048 \times 2048 = 4,194,304 \text{ pixels}$$
   $$\Delta_{\text{pixels}} = 4,194,304 - 4,194,304 = 0 \text{ (Zero pixel loss, zero silent clipping)}$$
2. **Non-Overlapping Proof:**
   $$\forall j, k \in \{0, 1, 2, 3\} \text{ with } j < k: [j \cdot 512, (j+1) \cdot 512) \cap [k \cdot 512, (k+1) \cdot 512) = \emptyset$$
   Intersection area between any two tiles is exactly 0. Zero unintended duplicate coverage.

### 8.3 Mask/Tiling Array Coordinate Correspondence
- **Coordinate System:** Array index coordinates $[r, c]$ with origin $(0, 0)$ at the top-left pixel.
- **World-Coordinate Policy:** Because world-coordinate registration is not established, the default contract MUST operate in array coordinates:
  Direct array indexing: `Tile_Mask[r, c] = Scene_Mask[r_off + r, c_off + c]` and `Tile_Image[b, r, c] = Scene_Image[b, r_off + r, c_off + c]`.
  $$\text{Tile\_Mask}[r, c] = \text{Scene\_Mask}[r_{\text{off}} + r, c_{\text{off}} + c]$$
  $$\text{Tile\_Image}[b, r, c] = \text{Scene\_Image}[b, r_{\text{off}} + r, c_{\text{off}} + c]$$
- **Strict Prohibitions:**
  - Prohibit CRS-based reprojection or warping.
  - Prohibit continuous spatial resampling or interpolation.
  - Prohibit inferred spatial shifts or one-pixel alignment corrections.
  - Prohibit manual or visual registration adjustment.
  - Prohibit coordinate transposition ($r \leftrightarrow c$) or axis flipping.
- **Dtype Cast:** Target mask cast from `uint8` $\{0, 1\} \rightarrow \text{float32}$ $\{0.0, 1.0\}$.

---

## 9. Section 5.10 — Decision Threshold Contract

### 9.1 Verification of Threshold Output Domain
Based on direct source code evidence from `src/ocean_sentinel/ml/threshold.py` (lines 116-125), `src/ocean_sentinel/ml/metrics.py` (lines 68-74), and `src/ocean_sentinel/ml/canonical_exp01.py` (line 80):

$$\text{Model Forward Pass} \rightarrow \text{Raw Logit Tensor } \ell \in \mathbb{R}^{(B, 1, 512, 512)}$$
$$\downarrow$$
$$\text{Logistic Sigmoid Activation } p = \sigma(\ell) = \frac{1}{1 + e^{-\ell}} \in [0.0, 1.0]$$
$$\downarrow$$
$$\text{Threshold Application } \hat{y} = \mathbb{I}(p \ge 0.22)$$
$$\downarrow$$
$$\text{Binary Decision Mask } \hat{y} \in \{0, 1\}^{(B, 1, 512, 512)}$$

- **Threshold Value:** $\tau = 0.22$.
- **Output Domain:** **`PROBABILITY_DOMAIN_SIGMOID`** ($p \in [0.0, 1.0]$).
- **Logit-Equivalent Threshold:** $\ell_{\tau} = \ln\left(\frac{0.22}{1.0 - 0.22}\right) = \ln\left(\frac{0.22}{0.78}\right) \approx -1.265666$.
- **Threshold Semantics Status:** **`VERIFIED`**.
- **Tuning Policy:** Strictly frozen. Zero threshold search, ROC grid optimization, or post-hoc threshold adjustment on Trujillo Part III is permitted.

---

## 10. Section 5.11 & 5.12 — Metrics, Denominators, and Aggregation Schema

### 10.1 Mathematical Metric Definitions

Let the reconstructed scene prediction mask be $P \in \{0, 1\}^{2048 \times 2048}$ (thresholded at $\tau = 0.22$ on sigmoid probability) and the ground-truth target mask be $Y \in \{0, 1\}^{2048 \times 2048}$.
Confusion matrix pixel counts are defined as:
$$TP = \sum_{r, c} \mathbb{I}(P_{r, c} == 1 \land Y_{r, c} == 1)$$
$$FP = \sum_{r, c} \mathbb{I}(P_{r, c} == 1 \land Y_{r, c} == 0)$$
$$FN = \sum_{r, c} \mathbb{I}(P_{r, c} == 0 \land Y_{r, c} == 1)$$
$$TN = \sum_{r, c} \mathbb{I}(P_{r, c} == 0 \land Y_{r, c} == 0)$$

#### A. Stratum 1: Oil Scenes (Positive Target Stratum, $N_{\text{Oil}}=150$)
For each scene $s \in \text{Oil}$:
$$\text{IoU}_s = \frac{TP_s}{TP_s + FP_s + FN_s}$$
$$\text{Precision}_s = \begin{cases} \frac{TP_s}{TP_s + FP_s}, & \text{if } TP_s + FP_s > 0 \\ 0.0, & \text{if } TP_s + FP_s == 0 \land TP_s + FN_s > 0 \end{cases}$$
$$\text{Recall}_s = \frac{TP_s}{TP_s + FN_s} \quad (\text{denom } > 0 \text{ guaranteed for all 150 Oil scenes})$$
$$F_{1, s} = \frac{2 \cdot TP_s}{2 \cdot TP_s + FP_s + FN_s}$$

#### B. Stratum 2: No oil Scenes (Clean Ocean Negative Stratum, $N_{\text{No\_oil}}=150$)
For each scene $s \in \text{No oil}$, ground truth is strictly empty ($TP_s = 0, FN_s = 0, TN_s + FP_s = 4,194,304$):
$$FP_{\text{pixels}, s} = FP_s = \sum_{r, c} \mathbb{I}(P_{r, c} == 1)$$
$$FP_{\text{ratio}, s} = \frac{FP_{\text{pixels}, s}}{2048 \times 2048} = \frac{FP_s}{4,194,304}$$
$$\text{Scene False Alarm Indicator}_s = \mathbb{I}(FP_{\text{pixels}, s} > 0)$$

#### C. Stratum 3: Lookalike Scenes (Confirmatory Hard-Negative Stratum, $N_{\text{Lookalike}}=150$)
For each scene $s \in \text{Lookalike}$, ground truth is strictly empty ($TP_s = 0, FN_s = 0$):
$$FP_{\text{lookalike}, s} = FP_s = \sum_{r, c} \mathbb{I}(P_{r, c} == 1)$$
$$FP_{\text{lookalike\_ratio}, s} = \frac{FP_{\text{lookalike}, s}}{4,194,304}$$
$$\text{Lookalike Scene FAR}_s = \mathbb{I}(FP_{\text{lookalike}, s} > 0)$$

### 10.2 Treatment of Confusion Matrix Cases
| Ground Truth | Model Prediction | Oil Stratum Behavior | Negative Strata (No oil / Lookalike) Behavior |
|---|---|---|---|
| **Empty ($Y=0$)** | **Empty ($P=0$)** | Not applicable (all 150 Oil scenes contain targets). | Clean agreement: $FP=0, \text{FAR}=0$. |
| **Empty ($Y=0$)** | **Non-Empty ($P>0$)** | False alarm pixels count toward $FP$. | False alarm: $FP>0, \text{FAR}=1$. |
| **Non-Empty ($Y>0$)** | **Empty ($P=0$)** | Complete detection failure: $TP=0, \text{IoU}=0.0, \text{Precision}=0.0, \text{Recall}=0.0$. | Not applicable (300 negative masks are all-zero). |
| **Non-Empty ($Y>0$)** | **Non-Empty ($P>0$)** | Standard overlap formulas: $\text{IoU} = \frac{TP}{TP+FP+FN}$. | Not applicable. |

### 10.3 Significant FAR Metric Classification
The secondary metric condition $FP \ge 100 \text{ pixels}$ per scene is formally classified as:
# **`SECONDARY DIAGNOSTIC — FIXED A PRIORI`**
- **Role:** Ordinary False Alarm Rate ($\text{FAR} = \mathbb{I}(FP > 0)$) remains the **primary** negative-scene evaluation metric.
- **Tuning Prohibition:** The 100-pixel threshold is pre-specified and frozen before evaluation; it shall never be tuned, fitted, or optimized based on model performance.

### 10.4 Aggregation Formulas and Denominator Rules
- **Stratified Denominators:** $N_{\text{Oil}} = 150$, $N_{\text{No\_oil}} = 150$, $N_{\text{Lookalike}} = 150$.
- **Macro-Averaged Oil Metrics:**
  $$\text{IoU}_{\text{macro}}(\text{Oil}) = \frac{1}{150} \sum_{s=1}^{150} \text{IoU}_s, \quad F_{1, \text{macro}}(\text{Oil}) = \frac{1}{150} \sum_{s=1}^{150} F_{1, s}$$
- **Micro-Averaged Oil Metrics:**
  $$\text{IoU}_{\text{micro}}(\text{Oil}) = \frac{\sum_{s \in \text{Oil}} TP_s}{\sum_{s \in \text{Oil}} (TP_s + FP_s + FN_s)}$$
- **Negative Strata Aggregate FAR:**
  $$\text{FAR}_{\text{scene}}(\text{No oil}) = \frac{1}{150} \sum_{s \in \text{No oil}} \mathbb{I}(FP_s > 0), \quad \text{FAR}_{\text{scene}}(\text{Lookalike}) = \frac{1}{150} \sum_{s \in \text{Lookalike}} \mathbb{I}(FP_s > 0)$$

---

## 11. Section 5.13 — Inclusion and Exclusion Policy

1. **Zero Outcome-Based Exclusion:** No sample may be excluded from evaluation due to poor IoU, high false-alarm count, low backscatter contrast, ambiguous slick features, or unexpected radar reflections.
2. **Disaggregation of Dataset Inclusion from Evaluation Validity:**
   - All 450 scenes remain permanently in the dataset accounting inventory ($N=450$).
   - A sample can be excluded from evaluation validity if and only if it encounters a mandatory technical failure state:
     - `INVALID_CONTAINER`: Raster header corrupted or unreadable.
     - `INVALID_SHAPE`: Spatial dimensions $\neq 2048 \times 2048$ or band count $\neq 2$ (image) / $\neq 1$ (mask).
     - `INVALID_DTYPE`: Image dtype $\neq \text{float32}$ or mask dtype $\neq \text{uint8}$.
     - `NONFINITE`: Presence of $\text{NaN}, +\infty, -\infty$ pixels.
     - `PAIRING_FAILURE`: Missing partner raster or broken filename stem pairing.
     - `ADAPTER_CONTRACT_FAILURE`: Tiling geometry mismatch or memory layout discontinuity.
     - `UNKNOWN_REQUIRED_SEMANTIC`: Unresolved mandatory operational policy.
3. **Current Preflight Status:** All 450 images and all 450 masks have been physically verified in Phase 4B-3. Exactly 0 samples exhibit technical failure states.
4. **Mandatory Action on Technical Failure:** If an unanticipated technical failure occurs during future execution, the sample must NOT be silently removed. The exact path, failure category, and error must be recorded, and benchmark evaluation shall be **BLOCKED** pending investigation.

---

## 12. Section 5.14 — Contamination and Independence Disclosure

The official benchmark report must display the following disclosure verbatim:
> **"No exact SHA-256 content matches were detected against the audited Trujillo Part I files across 2,400 audited rasters. However, acquisition-level independence remains UNVERIFIED. Both datasets originate from the same upstream repository (Trujillo-Acatitla et al., 2024; Zenodo deposit 13761290). Shared upstream provenance exists. Trujillo Part III constitutes an external benchmark under shared repository provenance, not a fully independent sensor acquisition."**

---

## 13. Section 5.15 — Reproducibility and Checkpoint Boundary

| Dimension | Frozen Specification |
|---|---|
| **Repository Baseline** | `master` branch at commit `542bab19f6f08c9bba8b8762e6480386c8b6026b` |
| **Python Environment** | Python 3.12 (managed via `uv`) |
| **Core Libraries** | PyTorch 2.6.0+cu124, Rasterio 1.4.3, NumPy 2.2.3 |
| **Dataset Inventory** | `scratch/trujillo_part_iii_extracted_inventory.json` (900 files) |
| **Cryptographic Hashes** | `scratch/trujillo_part_iii_extracted_sha256.json` |
| **Pairing Manifest** | `scratch/trujillo_part_iii_pairing.json` (450 bijective pairs) |
| **Candidate Checkpoints** | EXP-01 (`best_model.pt`), EXP-02B-1 (`best_model.pt`), EXP-02C (`best_model.pt`) |
| **Evaluation Adapter** | `scratch/trujillo_part_iii_adapter.py` (Version `1.0.0`) |
| **Random Seeds** | Deterministic inference (`torch.manual_seed(42)`, DataLoader `shuffle=False`) |
| **Checkpoint Loading Status** | **ZERO CHECKPOINTS LOADED** (Phase 4C is design-only; checkpoint loading deferred to Phase 4D upon CAO authorization) |

---

## 14. Document Status and CAO Handoff

This Scientific Evaluation Contract is complete, verified against repository code, and formally **FROZEN**.

**Status:** **`PHASE_4C_DESIGN_READY_FOR_CAO_EVALUATION_AUTHORIZATION`**  
Zero model forward passes, checkpoint loading, or inference routines have been performed.
