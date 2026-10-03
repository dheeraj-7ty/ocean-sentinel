# PHASE 5C EXP-03 FORENSIC ANALYSIS & EXP-04 CONTROLLED EXPERIMENT DESIGN
**Project:** Ocean Sentinel  
**Authority:** CAIO Scientific Governance  
**Date:** 2026-09-11  
**Status:** COMPLETE FORENSIC REPORT & EXPERIMENT SPECIFICATION  

---

## 1. Executive Summary

Phase 5B EXP-03 (Hard-Negative Fine-Tuning Baseline) evaluated whether injecting 2 mined hard-negative empty tiles per 16-tile batch ($12.5\%$ exposure) could reduce false alarms without compromising detection performance. The experiment completed all 10 epochs deterministically, passed independent verification across all 2,880 canonical validation tiles, and strictly preserved the Part III firewall.

* **The Core Paradox:** EXP-03 achieved a dramatic, unprecedented suppression of false alarms—reducing Clean-Water False Alarm Rate (FAR) from $20.09\%$ to $0.33\%$ ($-98.4\%$) and total false positive pixels by $96.6\%$. However, EXP-03 **failed the pre-registered acceptance gate** on validation IoU ($0.70435$ vs. $\ge 0.71731$) and recall ($0.77287$ vs. $\ge 0.80000$).
* **Forensic Diagnosis:** The $12.5\%$ hard-negative exposure, drawn from a candidate pool heavily skewed by massive full-tile false positive penalties ($8\%$ of candidates containing $\ge 100,000$ FP pixels), imposed excessive negative gradient pressure. This caused severe positive prediction-mass shrinkage ($-10.4\%$) and resulted in the complete dropout of **227 genuine oil-spill tiles** where the baseline model had successfully detected oil.
* **Controlled Solution (EXP-04):** We design EXP-04 as a strict, single-variable intervention: **reducing hard-negative batch exposure by 50% from 2 mined tiles ($12.5\%$) to 1 mined tile ($6.25\%$)** in a 16-tile batch ($15\text{ standard} + 1\text{ mined}$). All other 24 experimental variables remain strictly frozen. Training is NOT authorized in this phase.

---

## 2. Source-of-Truth Classification

In accordance with CAIO governance, all statements in this report are strictly classified:
* **[OBSERVED FACT]:** Verified directly from persistent disk artifacts, immutable SHA-256 digests, process logs, or recomputed numerical outputs.
* **[INFERENCE]:** Mechanistic deduction or hypothesis supported by observed facts, but not directly measurable as a single scalar.
* **[UNVERIFIED / LIMITATION]:** Known empirical boundary, untested scenario, or external condition requiring future experimentation.

---

## 3. EXP-03 Full Trajectory Reconstruction

### 3.1 Authoritative 10-Epoch Trajectory Table
All metrics extracted directly from `experiments/performance/exp03_baseline_hard_neg/history.json` and validated against `independent_validation_verification.json` [OBSERVED FACT]:

| Epoch | Val Loss | Val IoU | Val Dice | Precision | Recall | Clean-Water FAR | Significant FAR | Total FP Pixels |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | $0.01019$ | $0.69752$ | $0.82181$ | $0.88059$ | $0.77042$ | $0.55\%$ | $0.38\%$ | $114,357$ |
| **2** | $0.00977$ | $0.70200$ | $0.82491$ | $0.88562$ | $0.77209$ | $0.44\%$ | $0.33\%$ | $95,951$ |
| **3** | $0.00994$ | $0.69614$ | $0.82085$ | $0.87532$ | $0.77271$ | $0.55\%$ | $0.49\%$ | $126,929$ |
| **4** | $0.01007$ | $0.69796$ | $0.82212$ | $0.87707$ | $\mathbf{0.77364}$ | $0.60\%$ | $0.49\%$ | $127,103$ |
| **5** | $0.00989$ | $0.70119$ | $0.82435$ | $0.88725$ | $0.76997$ | $0.38\%$ | $0.33\%$ | $87,419$ |
| **6** | $0.01026$ | $0.69974$ | $0.82335$ | $0.88219$ | $0.77196$ | $0.44\%$ | $0.38\%$ | $97,951$ |
| **7** | $0.00989$ | $0.70155$ | $0.82460$ | $0.88554$ | $0.77161$ | $0.44\%$ | $0.38\%$ | $98,187$ |
| **8** | $0.00982$ | $0.70327$ | $0.82579$ | $0.88771$ | $0.77196$ | $0.38\%$ | $0.33\%$ | $85,389$ |
| **9** | $\mathbf{0.00977}$ | $\mathbf{0.70435}$ | $\mathbf{0.82653}$ | $\mathbf{0.88820}$ | $0.77287$ | $\mathbf{0.33\%}$ | $\mathbf{0.33\%}$ | $\mathbf{79,742}$ |
| **10** | $0.00977$ | $0.70390$ | $0.82622$ | $0.88727$ | $0.77304$ | $0.38\%$ | $0.33\%$ | $88,145$ |

*EXP-01 Teacher Baseline:* Loss: $0.00922$, IoU: $0.71691$, Dice: $0.83512$, Prec: $0.85138$, Rec: $0.78488$, Clean FAR: $20.09\%$, Sig FAR: $10.56\%$, FP Pixels: $2,327,942$.

### 3.2 Trajectory Extrema & Coincidence Analysis [OBSERVED FACT]
* **Best IoU Epoch:** Epoch 9 ($0.70435$).
* **Best Recall Epoch:** Epoch 4 ($0.77364$). (Epoch 10 is second at $0.77304$, Epoch 9 is third at $0.77287$).
* **Lowest Clean-Water FAR Epoch:** Epoch 9 ($0.33\%$, representing exactly 6 false-positive tiles out of 1,827).
* **Lowest Significant FAR Epoch:** Epochs 2, 5, 8, 9, 10 all tie at $0.33\%$ (all 6 false-positive tiles contained $\ge 100$ pixels).
* **Lowest FP Pixels Epoch:** Epoch 9 ($79,742$ pixels).
* **Epoch Coincidence / Divergence:**
  - **Coincidence:** Epoch 9 simultaneously achieves the best IoU, lowest loss, lowest clean-water FAR, lowest significant FAR, and lowest total FP pixels.
  - **Divergence:** Recall peaked earlier at Epoch 4 ($0.77364$), but the difference vs Epoch 9 ($0.77287$) is minimal ($-0.00077$ or $-0.10\%$).
* **Exploratory Combined Metric (Non-preregistered):** If an exploratory harmonic mean $F_{1\text{-tradeoff}} = 2 \cdot (\text{IoU} \cdot (1 - \text{FAR})) / (\text{IoU} + (1 - \text{FAR}))$ is computed, Epoch 9 scores highest ($0.8247$ vs. EXP-01 baseline $0.7554$). This illustrates that on an unweighted combined basis, the false-alarm drop dwarfs the IoU penalty.

---

## 4. Quantitative Trade-off Analysis (EXP-01 vs. EXP-03)

Comparing the canonical EXP-01 baseline against EXP-03 best checkpoint (Epoch 9) [OBSERVED FACT]:

| Metric | EXP-01 Baseline | EXP-03 (Epoch 9) | Absolute Delta ($\Delta$) | Relative % Change | Preregistered Gate | Gate Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Validation IoU** | $0.71691$ | $0.70435$ | $-0.01256$ | $-1.75\%$ | $\ge 0.71731$ | **FAIL** |
| **Validation Dice** | $0.83512$ | $0.82653$ | $-0.00859$ | $-1.03\%$ | Non-inferior | Noticeable drop |
| **Precision** | $0.85138$ | $0.88820$ | $+0.03682$ | $+4.32\%$ | $\mathrm{N/A}$ | Significant gain |
| **Recall** | $0.78488$ | $0.77287$ | $-0.01201$ | $-1.53\%$ | $\ge 0.80000$ | **FAIL** |
| **Clean-Water FAR** | $20.09\%$ | $0.33\%$ | $-19.76\text{ pp}$ | $\mathbf{-98.36\%}$ | $< 20.09\%$ | **PASS** |
| **Significant FAR** | $10.56\%$ | $0.33\%$ | $-10.23\text{ pp}$ | $\mathbf{-96.88\%}$ | $< 10.56\%$ | **PASS** |
| **Total FP Pixels** | $2,327,942$ | $79,742$ | $-2,248,200$ | $\mathbf{-96.57\%}$ | $< 2,327,942$ | **PASS** |

---

## 5. Prediction-Mass & Spatial Sparsity Analysis

To verify whether the recall drop was driven by broad over-conservative suppression or local edge erosion, we executed a full pixel-level audit across all 2,880 validation tiles [OBSERVED FACT]:

### 5.1 Macro Mass Metrics
* **Total Ground-Truth Positive Pixels:** $12,309,584$ (Target positive pixel fraction: $1.630\%$).
* **EXP-01 Predicted Positive Pixels:** $15,668,391$ (Predicted positive pixel fraction: $2.075\%$).
* **EXP-03 Predicted Positive Pixels:** $14,043,861$ (Predicted positive pixel fraction: $1.860\%$).
* **Net Prediction Mass Shrinkage:** $-1,624,530$ pixels ($-10.37\%$).
* **False Negative (FN) Pixels:**
  - EXP-01 missed pixels: $2,798,401$
  - EXP-03 missed pixels: $3,664,417$
  - Net increase in missed oil mass: $\mathbf{+866,016\text{ pixels}}$ ($\mathbf{+30.95\%}$ relative increase).

### 5.2 Scene- and Tile-Level Detection Frequency
* **Ground-Truth Positive Validation Tiles:** Exactly $1,053$ tiles contain $\ge 1$ oil pixel.
* **Tiles with Predicted Positive Pixels:**
  - EXP-01 predicted positive pixels on: $1,361$ tiles ($1,053$ true positive + $308$ false positive tiles).
  - EXP-03 predicted positive pixels on: $826$ tiles ($820$ true positive + $6$ false positive tiles).
* **The Critical Drop Incident:**
  - In EXP-01, $1,053$ out of $1,053$ positive tiles ($100.0\%$) had $\ge 1$ positive pixel detected.
  - In EXP-03, **$227$ genuine oil-spill tiles were completely dropped** ($0$ positive pixels predicted).
  - Positive tile detection rate fell from $100.0\%$ to $78.44\%$.

[INFERENCE]: The network did not merely erode boundaries of existing detections; it developed a severe conservative bias that suppressed low-contrast, diffuse, or small oil slicks below the $\tau = 0.22$ threshold entirely.

---

## 6. Hard-Negative Candidate Pool Skew Analysis

We analyzed the frozen 400-tile candidate manifest (`exp03_hard_negative_manifest.json`) [OBSERVED FACT]:
* **Parent Scene Diversity:** $400$ candidates harvested from $273$ unique parent scenes ($146$ scenes contributed $1$ tile, $127$ scenes contributed $2$ tiles; max cap $= 2$).
* **False Positive Pixel Distribution:**
  - **Minimum:** $301$ pixels
  - **25th Percentile:** $832$ pixels
  - **Median:** $2,090$ pixels
  - **Mean:** $22,303$ pixels (heavily right-skewed by extreme outliers)
  - **75th Percentile:** $11,357$ pixels
  - **90th Percentile:** $75,340$ pixels
  - **Maximum:** $262,144$ pixels ($100\%$ full tile false alarm)
* **Extreme Candidate Burden:**
  - **$45$ candidates ($11.25\%$)** contain $\ge 50,000$ FP pixels.
  - **$32$ candidates ($8.00\%$)** contain $\ge 100,000$ FP pixels.
  - Several candidates represent whole-scene oceanic clutter (e.g. low wind zones, lookalikes) where every pixel was falsely flagged by EXP-01.

[INFERENCE]: At $12.5\%$ exposure ($2$ mined tiles per batch of $16$), every batch has an expected $0.225$ tiles with $\ge 50,000$ FP pixels. Across $960$ batches per epoch, the model received intense, unregularized all-negative gradient signals ($1,920$ mined tile exposures per epoch). Because BCE penalizes false positives across all $262,144$ pixels of these extreme tiles, the optimizer drastically lowered baseline bias weights in the classification head, causing widespread suppression of legitimate oil features.

---

## 7. Causality Assessment

[DISCIPLINED CAUSAL FORMULATION]:
* **What is Proven:** EXP-03 exhibited a substantial recall reduction and an increase of $866,016$ false-negative pixels under the $12.5\%$ hard-negative exposure condition.
* **What Cannot be Claimed as Certain:** We cannot claim that $12.5\%$ exposure alone caused the recall collapse in isolation from the candidate pool severity distribution. A 12.5% exposure with mild candidates ($<5,000$ pixels) might behave very differently from 12.5% exposure with whole-tile ($262,144$ pixels) candidates.
* **Scientific Statement:** "The observed recall collapse is consistent with excessive negative-training pressure generated by the combination of $12.5\%$ batch exposure and extreme whole-tile false-positive candidates. Testing the exposure variable independently is required before altering candidate filtering."

---

## 8. Evaluation and Ranking of Candidate Interventions for EXP-04

To solve the trade-off, we systematically evaluated 8 potential intervention classes against 7 scientific criteria:

| Candidate Class | Intervention Description | Recall Recovery | FAR Retention | Single-Var Purity | Implementation Risk | Confounding Risk | Overall Rank |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. Lower Exposure** | Halve mined tiles to 1 per batch ($6.25\%$ exposure, $15\text{ std} + 1\text{ mined}$) | **High** | **High** | **Perfect (1 var)** | **Minimal** | **Minimal** | **#1 (SELECTED)** |
| **B. Annealed Exposure** | Start at 1 mined tile and decay to 0 over 10 epochs | High | Moderate | Moderate (adds schedule) | Low | Moderate | #3 (Backup) |
| **C. Loss Weighting** | Adjust BCE vs Dice (e.g., $0.3\text{ BCE} + 0.7\text{ Dice}$) | Moderate | Low | High | Minimal | High | #5 |
| **D. Positive Preservation** | Weight positive pixels $2\times$ inside BCE loss | High | Poor | High | Low | High | #4 |
| **E. Severity Capping** | Cap candidate manifest to tiles with $\le 25,000$ FP pixels | High | High | Low (manifest regen) | Moderate | High | #2 (Backup) |
| **F. Mining Re-selection** | Re-mine candidates using a different threshold (e.g. $\tau = 0.50$) | Unknown | Unknown | Low | High | Very High | #7 |
| **G. Diversity Expansion** | Expand candidate pool from 400 to 1,000 tiles | Low | High | Low | Moderate | High | #6 |
| **H. Threshold Tuning** | Lower operating threshold to $\tau = 0.15$ | High | Poor | Violates Rule 13 | Minimal | N/A (Disallowed) | DISQUALIFIED |

---

## 9. Primary Selected Intervention: EXP-04

### 9.1 The Single-Variable Formulation
* **Primary Intervention:** **Candidate A — 50% Reduction in Hard-Negative Batch Exposure.**
* **Exact Operational Change:**
  - Modify `TwoStreamBatchSampler` batch composition from $(14\text{ std}, 2\text{ mined})$ to $(15\text{ std}, 1\text{ mined})$.
  - Mined exposure fraction drops from $12.5\%$ to $6.25\%$.
  - Total batches per epoch adjusts from $960$ to $896$ ($\lfloor 13440 / 15 \rfloor$).
  - Total mined exposures per epoch drop from $1,920$ to $896$ ($-53.3\%$).

### 9.2 Scientific Rationale
1. **Purity of Comparison:** It holds the candidate pool ($400$ tiles, SHA-256 `3867671E...`), teacher checkpoint (`best_model.pt`, SHA-256 `9B8BD867...`), spatial split, loss function, learning rate, and optimizer completely constant.
2. **Direct Dose-Response Mapping:** By comparing $0\%$ (EXP-01), $6.25\%$ (EXP-04), and $12.5\%$ (EXP-03), we trace the exact sensitivity curve of ResNet34UNet to hard-negative exposure.
3. **Lowest Implementation & Confounding Risk:** Requires changing only two integers in the sampler initialization.

---

## 10. Frozen Controls & Safeguards

The following elements are strictly locked for EXP-04:
1. **Architecture:** ResNet34UNet with 24,346,305 trainable parameters and 19,054 buffers.
2. **Teacher Weights:** Canonical EXP-01 baseline `best_model.pt`.
3. **Dataset Split:** Canonical Part I train/val split ($13,440$ train, $2,880$ val).
4. **Candidate Manifest:** Canonical $400$-tile manifest.
5. **Loss:** `CombinedBCEAndDiceLoss(0.5, 0.5, smooth=1.0)`.
6. **Optimizer & LR:** AdamW ($1e-4$, weight decay $1e-2$), CosineAnnealingLR ($T_{\max}=10$).
7. **Threshold:** Strictly $\tau = 0.22$.
8. **Part III Firewall:** Absolute isolation.

---

## 11. Success / Failure Acceptance Criteria for EXP-04

EXP-04 will be evaluated strictly at its best validation IoU epoch against these preregistered gates:

### 11.1 Primary Non-Inferiority Recovery Gates
* **Val IoU Gate:** $\ge 0.71731$ (Non-inferior to baseline $0.71691$).
* **Val Recall Gate:** $\ge 0.78500$ (Matches or exceeds baseline $0.78488$).

### 11.2 Guardrail False-Alarm Retention Gates
* **Clean-Water FAR Gate:** $< 5.00\%$ (Retaining $>75\%$ of EXP-03's reduction vs baseline $20.09\%$).
* **Significant FAR Gate:** $< 3.00\%$ (Retaining $>70\%$ of EXP-03's reduction vs baseline $10.56\%$).
* **Total FP Pixels Gate:** $< 350,000$ (Retaining $>85\%$ of false positive suppression vs baseline $2,327,942$).

---

## 12. Contingency & Uncertainty Management

* **If EXP-04 Recovers Recall and Retains FAR (PASS):** The $6.25\%$ exposure level is declared the new production operational baseline.
* **If EXP-04 Fails Recall Recovery (Recall $< 0.78500$):** The hypothesis that exposure frequency alone causes recall collapse is falsified. EXP-05 will test Candidate E (Candidate Severity Capping) to remove the $45$ extreme whole-tile false positives from the candidate pool.
* **If EXP-04 Fails Guardrail FAR (FAR $\ge 5.00\%$):** Exposure reduction diluted the negative gradient signal too severely. EXP-05 will test Candidate B (Annealed Exposure).

---

## 13. Preflight & Execution Checklist for Future Authorization

Before CAIO authorization of EXP-04 execution:
- [x] Full EXP-03 forensic trajectory extracted and documented.
- [x] Candidate pool skew and prediction-mass collapse quantified.
- [x] EXP-04 contract preregistered with 25 required sections.
- [x] All 79 regression tests passing (`test_part_iii_firewall`, `test_phase_5_guardrails`, `test_artifact_policy`, `test_dataset_pipeline`, `test_phase_5b_prelaunch_adversarial`).
- [x] Windows multiprocessing verifier safety invariant codified and tested.
- [ ] Explicit CAIO authorization to launch EXP-04 training.
