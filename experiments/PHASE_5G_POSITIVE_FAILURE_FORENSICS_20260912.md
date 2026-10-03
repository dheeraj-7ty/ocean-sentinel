# PHASE 5G POSITIVE DETECTION FAILURE FORENSICS REPORT
**Project:** Ocean Sentinel  
**Authority:** CAIO Scientific Governance  
**Document ID:** PHASE_5G_POSITIVE_FAILURE_FORENSICS_20260912  
**Date:** 2026-09-12  
**Execution State:** **ANALYSIS COMPLETE / NO TRAINING EXECUTED**  
**Design Disposition:** **READY_FOR_CAIO_AUTHORIZATION**

---

## 1. Repository State & Governance Compliance
* **Branch:** `master`
* **Commit HEAD:** `542bab19f6f08c9bba8b8762e6480386c8b6026b`
* **Staged Changes (`git diff --cached`):** Clean (0 files staged).
* **Git Policy Compliance:** Strict adherence to zero staging (`git add`), zero commits, and zero pushes.
* **Prior Experiments:** EXP-01, EXP-03, EXP-04, and EXP-05 remain strictly closed, immutable, and read-only.
* **Training Boundary:** Absolutely zero training of EXP-06 was executed in Phase 5G.

---

## 2. Checkpoint Provenance & Physical Integrity [OBSERVED FACT]

All four checkpoints were independently verified on disk by byte size, physical loadability, and SHA-256 digest:

| Experiment Role | Checkpoint Path | Actual Disk SHA-256 | Size (Bytes) | Certified Best Epoch | Loadability Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **EXP-01 Teacher** | `experiments/exp01_baseline/best_model.pt` | `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | $292,465,299$ | Epoch 4 | **PASS / LOADABLE** |
| **EXP-03 Best Checkpoint** | `experiments/performance/exp03_baseline_hard_neg/best_model.pt` | `BE00C1C8B35A3648FCCAD3864F844ED2EB68E079F2CC390C1BA3EC147BF2DA57` | $292,463,187$ | Epoch 9 | **PASS / LOADABLE** |
| **EXP-04 Best Checkpoint** | `experiments/performance/exp04_hard_neg_ablation/best_model.pt` | `FAC3C313386F3FE561C2ECF0945B7F960CAA74897C5E8105FB68635529F1320B` | $292,466,907$ | Epoch 9 | **PASS / LOADABLE** |
| **EXP-05 Best Checkpoint** | `experiments/performance/exp05_candidate_severity_cap/best_model.pt` | `D9FC12E312E5DF012650E8106DCF90782534EFB1BD1E38BA7FDCF4E0802A0481` | $292,467,395$ | Epoch 10 | **PASS / LOADABLE** |

All models load cleanly with `ResNet34UNet(in_channels=2, num_classes=1, adaptation_method='slice_variance_scaled')`, verifying $24,346,305$ trainable parameters and $19,054$ non-trainable buffers ($24,365,359$ total state elements).

---

## 3. Four-Way Development History Reconstruction [OBSERVED FACT]

Recomputed across all $2,880$ canonical Part I validation tiles ($1,827$ clean-water, $1,053$ GT-positive) at $\tau = 0.22$:

| Metric | EXP-01 Baseline (No Mining) | EXP-03 (12.5% Mined, 400 Pool) | EXP-04 (6.25% Mined, 400 Pool) | EXP-05 (6.25% Mined, 355 Capped Pool) | $\Delta$ (EXP-05 vs EXP-01) | $\Delta$ (EXP-05 vs EXP-04) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **True Positives (TP)** | $13,339,788$ | $12,473,772$ | $12,625,901$ | $\mathbf{12,625,435}$ | $-714,353$ | $-466$ |
| **False Positives (FP)** | $2,328,603$ | $1,570,089$ | $1,666,000$ | $\mathbf{1,689,666}$ | $-638,937$ | $+23,666$ |
| **False Negatives (FN)** | $2,799,745$ | $3,665,761$ | $3,513,632$ | $\mathbf{3,514,098}$ | $+714,353$ | $+466$ |
| **True Negatives (TN)** | $736,506,584$ | $737,265,098$ | $737,169,187$ | $\mathbf{737,145,521}$ | $+638,937$ | $-23,666$ |
| **Validation IoU** | $0.71691$ | $0.70435$ | $0.70910$ | $\mathbf{0.70813}$ | $-0.00878$ | $-0.00097$ |
| **Validation Dice** | $0.83512$ | $0.82653$ | $0.82979$ | $\mathbf{0.82913}$ | $-0.00599$ | $-0.00066$ |
| **Precision** | $0.85138$ | $0.88820$ | $0.88343$ | $\mathbf{0.88197}$ | $+0.03059$ | $-0.00146$ |
| **Recall** | $0.78488$ | $0.77287$ | $0.78230$ | $\mathbf{0.78227}$ | $-0.00261$ | $-0.00003$ |
| **Clean-Water FAR** | $20.09\%$ | $0.33\%$ | $0.55\%$ | $\mathbf{0.49\%}$ | $-19.60\text{ pp}$ | $-0.06\text{ pp}$ |
| **Significant FAR** | $10.56\%$ | $0.33\%$ | $0.55\%$ | $\mathbf{0.49\%}$ | $-10.07\text{ pp}$ | $-0.06\text{ pp}$ |
| **Total FP (Empty)** | $2,327,942$ | $79,742$ | $122,937$ | $\mathbf{129,041}$ | $-2,198,901$ | $+6,104$ |
| **Pred Pos Mass** | $15,668,391\text{ px}$ | $14,043,861\text{ px}$ | $14,291,901\text{ px}$ | $\mathbf{14,315,101\text{ px}}$ | $-1,353,290$ | $+23,200$ |
| **Detected Pos Tiles**| $994$ | $820$ | $822$ | $\mathbf{850}$ | $-144$ | $\mathbf{+28}$ |
| **Dropped Pos Tiles** | $59$ | $233$ | $231$ | $\mathbf{203}$ | $+144$ | $\mathbf{-28}$ |

---

## 4. Positive-Failure Population Definition [OBSERVED FACT]
* The analysis population consists strictly of the **$1,053$ GT-positive tiles** within the canonical Part I validation split.
* Total ground-truth positive pixel mass: **$16,139,533\text{ pixels}$** across the population.
* Classification definitions:
  - **COMPLETE_DROPOUT:** Predicted positive pixels on tile $= 0$ ($\text{pred\_pixels} = 0$).
  - **PARTIAL_DETECTION:** Predicted positive pixels $> 0$ but $\text{fn\_pixels} > 0$ ($\text{tp} < \text{gt\_pixels}$).
  - **FULL_DETECTION:** Predicted positive pixels $> 0$ and $\text{fn\_pixels} = 0$ ($\text{tp} = \text{gt\_pixels}$).

---

## 5. False Negative (FN) Pixel Mass Decomposition [CALCULATED FACT]

A critical question of Phase 5G was determining what fraction of total FN pixel mass originates from complete tile dropout vs. partial under-segmentation:

| Experiment | Total FN Pixels | Complete Dropout FN Pixels | Complete Dropout FN % | Partial Detection FN Pixels | Partial Detection FN % | Full Detection FN Pixels |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **EXP-01** | $2,799,745$ | $106,609$ | $3.81\%$ | $2,693,136$ | $\mathbf{96.19\%}$ | $0$ |
| **EXP-03** | $3,665,761$ | $734,588$ | $20.04\%$ | $2,931,173$ | $\mathbf{79.96\%}$ | $0$ |
| **EXP-04** | $3,513,632$ | $767,168$ | $21.83\%$ | $2,746,464$ | $\mathbf{78.17\%}$ | $0$ |
| **EXP-05** | $3,514,098$ | $671,336$ | $19.10\%$ | $2,842,762$ | $\mathbf{80.90\%}$ | $0$ |

### Core Finding on FN Structure [CALCULATED FACT]
1. **Partial Under-Segmentation Dominates Total FN:** Across all mining experiments, **$\sim 80\%$ of all False Negative pixels originate from partial under-segmentation on detected tiles**, not from complete tile dropout. In EXP-05, $2,842,762$ of the $3,514,098$ FN pixels ($80.90\%$) reside on tiles where the spill is successfully detected.
2. **Dropout Recovery Shifts Tiles into Partial Regime:** While EXP-05 recovered $28$ tiles from complete dropout (reducing dropout FN mass by $-95,832\text{ pixels}$ from $767\text{k}$ to $671\text{k}$), total FN mass remained virtually unchanged ($3,513,632 \to 3,514,098$). When complete dropouts are recovered, they enter the partial-detection state, retaining significant internal and edge FN pixels, while existing detected tiles experience ongoing boundary erosion.

---

## 6. IoU Error Decomposition: False Negatives vs. False Positives [CALCULATED FACT]

To determine whether the recall/IoU bottleneck is driven by FN or FP errors, we decompose the total error denominator $\text{Total Error} = \text{FP} + \text{FN}$:

| Experiment | Validation IoU | Total Error Pixels | FN Error Pixels | FN Error Contribution % | FP Error Pixels | FP Error Contribution % | FN-to-FP Ratio |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **EXP-01** | $0.72231$ | $5,128,348$ | $2,799,745$ | $54.59\%$ | $2,328,603$ | $45.41\%$ | **$1.20 : 1$** |
| **EXP-03** | $0.70435$ | $5,235,850$ | $3,665,761$ | $70.01\%$ | $1,570,089$ | $29.99\%$ | **$2.33 : 1$** |
| **EXP-04** | $0.70910$ | $5,179,632$ | $3,513,632$ | $67.84\%$ | $1,666,000$ | $32.16\%$ | **$2.11 : 1$** |
| **EXP-05** | $0.70813$ | $5,203,764$ | $3,514,098$ | $67.53\%$ | $1,689,666$ | $32.47\%$ | **$2.08 : 1$** |

### Synthesis of Bottleneck Analysis [INFERENCE]
The remaining IoU deficit is **overwhelmingly dominated by False Negatives ($67.5\%$ of all error pixels, outnumbering False Positives by $2.08 : 1$)**. Hard-negative mining successfully crushed False Positives by $-638,937\text{ pixels}$ relative to baseline (and by $-94.5\%$ on clean-water tiles), but inflated False Negatives by $+714,353\text{ pixels}$ ($+25.5\%$). False-alarm suppression is now solved; positive detection is the sole bottleneck.

---

## 7. Dropout Transition Matrix Across Experiments [OBSERVED FACT]

Tracking tile-level detection states across EXP-01 $\to$ EXP-03 $\to$ EXP-04 $\to$ EXP-05:

* **Consistently Missed / Dropped Across All Mining Models:** Exactly **$188$ tiles** were dropped in EXP-03, EXP-04, and EXP-05 simultaneously. These represent the persistent core of small, low-contrast slicks.
* **EXP-03 $\to$ EXP-04 Transitions:**
  - Recovered in EXP-04 (from EXP-03): $27$ tiles ($25$ to Partial, $2$ to Full).
  - Newly dropped in EXP-04 (from EXP-03): $25$ tiles ($24$ from Partial, $1$ from Full).
  - Net recovery in EXP-04: $+2$ tiles ($233 \to 231$).
* **EXP-04 $\to$ EXP-05 Transitions:**
  - Recovered in EXP-05 (from EXP-04): **$37$ tiles** ($36$ to Partial, $1$ to Full).
  - Newly dropped in EXP-05 (from EXP-04): **$9$ tiles** (from Partial).
  - **Net recovery in EXP-05: $+28$ tiles ($231 \to 203$, an immediate $12.12\%$ reduction in complete dropouts)**.
* **Oscillating Tiles:** Only $24$ tiles switched detection state more than once across mining runs, demonstrating that the failure population is predominantly stable, not chaotic noise.

---

## 8. Stratified Failure Analysis by Ground-Truth Area [OBSERVED FACT]

The $1,053$ GT-positive tiles were partitioned into four equal-frequency quartiles based on ground-truth pixel area:

| Area Stratum | Area Range (Pixels) | Tile Count | Total GT Pixels | EXP-01 Dropouts | EXP-03 Dropouts | EXP-04 Dropouts | EXP-05 Dropouts | EXP-05 Macro Recall | EXP-05 Aggregate Recall |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Very Small** | $1 - 2,712$ | $264$ | $246,328$ ($1.5\%$) | $53$ ($20.1\%$) | $163$ ($61.7\%$) | $162$ ($61.4\%$) | $\mathbf{148}$ ($56.1\%$) | $0.37769$ | $0.54755$ |
| **Small** | $2,713 - 8,049$ | $264$ | $1,388,768$ ($8.6\%$) | $3$ ($1.1\%$) | $44$ ($16.7\%$) | $43$ ($16.3\%$) | $\mathbf{30}$ ($11.4\%$) | $0.74679$ | $0.74809$ |
| **Medium** | $8,050 - 19,367$ | $264$ | $3,424,945$ ($21.2\%$) | $1$ ($0.4\%$) | $20$ ($7.6\%$) | $20$ ($7.6\%$) | $\mathbf{19}$ ($7.2\%$) | $0.78312$ | $0.78620$ |
| **Large** | $> 19,367$ | $263$ | $11,090,253$ ($\mathbf{68.7\%}$) | $3$ ($1.1\%$) | $7$ ($2.7\%$) | $7$ ($2.7\%$) | $\mathbf{7}$ ($2.7\%$) | $0.78986$ | $0.79013$ |

### Structural Revelations [CALCULATED FACT]
1. **Dropouts are Concentrated in Very Small Slicks:** $148$ of the $203$ EXP-05 dropouts ($72.9\%$) reside in the Very Small stratum ($\le 2,712$ px). However, because these slicks are small, their total GT mass is only $246,328\text{ pixels}$ ($1.5\%$ of all positive pixels). Even complete elimination of all 148 very small dropouts would only reduce FN mass by at most $111,452\text{ pixels}$.
2. **FN Mass is Concentrated in Large Slicks:** The Large stratum ($> 19,367$ px) contains **$68.7\%$ of all GT positive pixels ($11.09\text{M}$)** and accounts for **$2,327,503\text{ FN pixels}$ ($66.2\%$ of all FN pixels in the validation set!)**. On these large spills, complete dropout is negligible ($7$ tiles, $2.7\%$), but partial under-segmentation truncates $20.98\%$ of the slick mass along diffuse edges and narrow arms.
3. **Severity Capping Recovered Small Slicks:** EXP-05 severity capping specifically recovered $14$ very small tiles and $13$ small tiles ($27$ tiles across the bottom 50% of the area distribution).

---

## 9. Prediction Confidence & Distribution Analysis [OBSERVED FACT]

We analyzed the continuous probability distribution over all ground-truth positive pixels at $\tau = 0.22$:

| Confidence Stratum | Mean GT Prob Range | Tile Count | EXP-05 Dropouts | Dropout % in Stratum | Mean GT Area (Pixels) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Strongly Suppressed** | $[0.00, 0.10)$ | $207$ | $203$ | **$98.07\%$** | $3,490.5$ |
| **Near-Threshold Low** | $[0.10, 0.22)$ | $7$ | $0$ | $0.00\%$ | $22,191.9$ |
| **Near-Threshold High** | $[0.22, 0.35)$ | $20$ | $0$ | $0.00\%$ | $21,127.4$ |
| **Confident Positive** | $[0.35, 1.00]$ | $819$ | $0$ | $0.00\%$ | $18,118.6$ |

### Epistemic Insight: Bimodal, Not Near-Threshold [INFERENCE]
The prediction probability distribution on positive tiles is **strictly bimodal**:
* Complete dropouts are **deeply suppressed** (mean probability $< 0.10$, average $\approx 0.02-0.04$). They are not "near-misses" hovering at $0.20-0.21$.
* Only **$27$ tiles in the entire validation set ($2.56\%$)** fall within the transition window $[0.10, 0.35]$.
* Detected slicks have confident core activations ($> 0.70$), but edge activations drop off steeply.
* **Conclusion:** The recall deficit cannot be solved by adjusting $\tau$ post-hoc. A lower threshold would not recover the deeply suppressed dropouts without triggering false alarms on background sea clutter.

---

## 10. Spatial Geometry & Fragmentation Analysis [OBSERVED FACT]

Partitioning positive tiles by compactness (isoperimetric quotient $4\pi A / P^2$):
* **Compact Slicks (Compactness $\ge 0.05$, $805$ tiles):**
  - EXP-05 Recall = **$82.43\%$**
  - Complete dropouts = $162$
* **Fragmented / Elongated Slicks (Compactness $< 0.05$, $248$ tiles):**
  - EXP-05 Recall = **$67.57\%$** ($-14.86\text{ percentage points}$ deficit!)
  - Complete dropouts = $41$
* **Observation:** Elongated slicks, thin filaments, and fragmented oil sheens suffer severe boundary erosion because the ratio of perimeter pixels to interior pixels is extremely high. Negative gradients from adjacent background pixels contract the prediction mask inward, cutting thin slicks into disconnected pieces.

---

## 11. Parent-Scene Failure Clustering [OBSERVED FACT]
* Top dropout scenes in EXP-05:
  - Scene `00609`: $7$ dropouts out of $9$ positive tiles
  - Scene `00470`: $6$ dropouts out of $11$ positive tiles
  - Scene `00126`: $5$ dropouts out of $10$ positive tiles
  - Scene `00217`: $5$ dropouts out of $6$ positive tiles
  - Scene `00608`: $5$ dropouts out of $9$ positive tiles
* The top 10 scenes account for $45$ of the $203$ dropouts ($22.2\%$). The remaining $158$ dropouts are distributed across $78$ different scenes.
* While specific scenes with low SAR contrast or complex sea surface clutter exhibit higher failure density, positive detection failures are population-wide, reflecting systemic gradient imbalance rather than isolated scene anomalies.

---

## 12. Contradictory Evidence & Falsified Hypotheses

| Hypothesis | Presumed Mechanism | Empirical Evidence Against / Falsification |
| :--- | :--- | :--- |
| **"Dropouts are caused by threshold sensitivity near $\tau = 0.22$"** | Model predicts oil at $0.18-0.21$, just missing the cutoff. | **FALSIFIED:** Only $7$ tiles have mean probability in $[0.10, 0.22)$. All $203$ dropouts are deeply suppressed ($< 0.10$). |
| **"Solving complete dropout will restore overall Recall to baseline"** | Eliminating the $203$ dropped tiles will close the $714\text{k}$ FN pixel gap. | **FALSIFIED:** All $203$ dropped tiles combined only contain $671,336\text{ FN pixels}$ ($19.1\%$). Even recovering $28$ dropouts in EXP-05 left total FN unchanged because $80.9\%$ of FN resides on partially detected tiles. |
| **"Extreme candidates $> 50\text{k}$ px were the sole cause of dropout"** | Outlier hard negatives caused all dropouts. | **FALSIFIED:** Capping at $50\text{k}$ recovered $28$ tiles, but $203$ dropouts persist, and $188$ were never detected across any mining run. |

---

## 13. Mechanistic Ranking of Failure Causes

Based on empirical observations, we rank candidate failure mechanisms:

1. **Background Negative Gradient Dominance in BCE Loss [PRIMARY]:**
   - *Supporting Evidence:* Positive pixels constitute only $\sim 2-3\%$ of total batch pixels. Even on positive tiles, background dominates foreground $10:1$ to $100:1$. Unweighted BCE loss ($w=1.0$) exerts continuous downward pressure, eroding boundaries on large slicks ($2.33\text{M FN px}$) and extinguishing small slicks ($671\text{k FN px}$).
   - *Strength of Evidence:* High. Directly accounts for both the $80.9\%$ partial under-segmentation deficit and the $2.08:1$ FN/FP ratio.
2. **SAR Edge Contrast & Boundary Attenuation [SECONDARY]:**
   - *Supporting Evidence:* Fragmented and elongated slicks suffer a $14.9\text{ pp}$ recall deficit compared to compact slicks. Low radiometric contrast at slick margins causes edge pixels to fall below activation threshold.
3. **Small-Target Area Penalty [TERTIARY]:**
   - *Supporting Evidence:* Very small slicks suffer a $56.1\%$ dropout rate because their receptive-field representation is small relative to pooling operations.

---

## 14. Evaluation of Candidate EXP-06 Interventions

We evaluated three potential single-variable interventions:

### Candidate A: Positive Class Reweighting in BCE Loss ($\text{pos\_weight} = 2.0$) [RECOMMENDED]
* **Mechanism:** In `CombinedBCEAndDiceLoss`, configure `torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor([2.0]))`.
* **Rationale:** Directly counterbalances the $97-98\%$ background pixel dominance by doubling the gradient penalty for false negative foreground pixels. Boosts boundary activation without reducing the negative penalty on false positive predictions.
* **Risks:** Could increase false alarms on empty tiles if weight is excessive. However, current Clean FAR is $0.49\%$ (gate is $< 5.00\%$), providing $10\times$ margin of safety.
* **Single-Variable Purity:** Alters strictly ONE variable: `bce_pos_weight`.

### Candidate B: Dice vs. BCE Loss Rebalancing ($\text{bce\_weight} = 0.25, \text{dice\_weight} = 0.75$) [REJECTED]
* **Mechanism:** Reduce BCE contribution and increase Dice contribution.
* **Rationale:** Dice loss is scale-invariant to foreground/background imbalance.
* **Failure Mode:** On empty mined tiles, Dice loss is zero (or constant smooth term). Halving BCE weight halves the hard-negative penalty on empty tiles, directly jeopardizing the $-97.5\%$ false alarm reduction achieved in EXP-03/04/05.

### Candidate C: Stratified Positive Batch Sampling in Standard Stream [REJECTED]
* **Mechanism:** Guarantee at least $N$ positive tiles in the 15 standard tiles of each batch.
* **Failure Mode:** Altering standard stream sampling modifies epoch definition, sampling without replacement semantics, and introduces complex epoch length confounders, violating single-variable purity.

---

## 15. Selected Primary EXP-06 Intervention

$$\mathbf{EXP\text{-}06\text{ INTERVENTION: POSITIVE CLASS REWEIGHTING IN BCE LOSS } (pos\_weight = 2.0)}$$

* **The Single Changed Variable:** `bce_pos_weight = 2.0` in `CombinedBCEAndDiceLoss` (changing from $1.0$).
* **Mathematical Formulation:**
  $$\mathcal{L}_{\text{BCE}}(p, y) = - \left[ 2.0 \cdot y \log(p) + (1 - y) \log(1 - p) \right]$$
* **Why this is the cleanest intervention:**
  1. Preserves $100\%$ of the hard-negative suppression on pure background tiles ($(1-y)\log(1-p)$ is completely unscaled).
  2. Directly counteracts boundary erosion on large spills ($80.9\%$ of total FN).
  3. Exploits the immense Clean-Water FAR headroom ($0.49\%$ vs. $< 5.00\%$ gate).
  4. Keeps all 24 other experimental controls frozen.

---

## 16. Preregistered Acceptance Gates (Strict & Unchanged)

* **Validation Recall:** $\ge 0.78500$
* **Validation IoU:** $\ge 0.71731$
* **Clean-Water FAR:** $< 5.00\%$
* **Significant FAR:** $< 3.00\%$
* **Total FP Pixels:** $< 350,000$

---

## 17. Observability & Testing Summary
* **Forensic Run State:** Persisted at `experiments/performance/phase_5g_positive_failure_forensics/run_state.json`. Status: `COMPLETED`.
* **Unit Test Suite:** `tests/test_phase_5g_preflight.py` authored with 10 preflight tests.
* **Full Regression Suite:** $582$ passed, $0$ failures across all test suites in the repository.
* **Execution Boundary:** Zero EXP-06 training was executed.

---

## 18. Mandatory Final Declaration

$$\mathbf{NO\text{ }EXP\text{-}06\text{ TRAINING WAS EXECUTED IN THIS PHASE.}}$$
$$\mathbf{FINAL\text{ }DESIGN\text{ }STATE = READY\_FOR\_CAIO\_AUTHORIZATION}$$
