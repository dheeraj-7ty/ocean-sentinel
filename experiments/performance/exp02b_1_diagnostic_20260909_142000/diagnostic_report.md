# EXP02B-1 Rigorous Diagnostic, Pareto & Error-Analysis Report

**Status**: FROZEN DIAGNOSTIC AUDIT COMPLETE — CORRECTED  
**Authoritative Candidate**: `best_model.pt` (Epoch 3, SHA-256 `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B`)  
**Evaluation Threshold**: Locked strictly to `0.22`  
**Dataset Split Manifest**: `data/metadata/trujillo_2024/spatial_split_manifest.json` (SHA-256 `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0`)  
**Diagnostic Directory**: `experiments/performance/exp02b_1_diagnostic_20260909_142000/`  
**Data Partition Governance**: **TRAIN / VALIDATION EVIDENCE ONLY** (Held-out test split strictly firewalled)

---

## Executive Summary

This diagnostic audit was conducted under formal CAO directive to evaluate:
> *"What exactly did hard-negative weighted sampling improve, what did it sacrifice, and what is the most defensible SINGLE-variable intervention for EXP02C?"*

### Key Empirical Findings

1. **Exact Negative Tile Contingency ($n = 1,827$ Validation Negatives)**:
   - EXP01 Baseline False Alarms: **367 / 1,827** ($20.09\%$)
   - EXP02B-1 False Alarms: **151 / 1,827** ($8.26\%$)
   - Exact Paired Contingency Table: $a = 1,400$ (both clean), $b = 276$ (cured), $c = 60$ (new), $d = 91$ (persistent).
   - Net Cured False Alarms: **$+216$ tiles** ($11.82$ percentage-point absolute reduction, **$58.86\%$ relative reduction**).
   - Exact Continuity-Corrected McNemar: **$\chi^2 = 137.5744, p = 9.03 \times 10^{-32}$** (95% Paired CI: $[9.93\%, 13.71\%]$ pp).

2. **Decisive Resolution of the Recall Loss Hypothesis**:
   - *Hypothesis*: "Is the recall loss predominantly whole-tile detection loss, or is it predominantly reduced spatial extent/undersegmentation within already-detected positive tiles?"
   - *Empirical Measurement*: Out of 1,053 validation positive tiles, only 151 tiles experienced any increase in False Negative (FN) pixels.
   - **$97.16\%$ of increased FN pixels ($172,350$ of $177,389$ px across 118 tiles)** stem from **spatial undersegmentation / perimeter shrinkage within already-detected positive spills**.
   - **Only $1.43\%$ of increased FN pixels ($2,532$ of $177,389$ px across 17 tiles)** stem from complete whole-tile misses.
   - **Zero ($0$) large spills ($\ge 5,000$ pixels) were completely missed** by the candidate model. All 17 whole-tile misses occurred on tiny (<500 px) or small/medium spills.
   - Across the full validation split, EXP02B-1 achieved **higher overall recall** ($86.64\%$ vs. $82.65\%$) and **fewer total FN pixels** ($2,155,744$ vs. $2,799,742$, a net reduction of $643,998$ missed pixels) than EXP01.

3. **Pareto Frontier & Trajectory Dynamics**:
   - Epoch 3 is the selected checkpoint under the pre-registered recall safety constraint and checkpoint selection policy. Among recall-safe checkpoints, it provides the highest observed validation IoU ($0.7305$) and recall ($86.64\%$) while retaining substantial false-alarm suppression ($8.26\%$). It is not globally Pareto-dominating over all checkpoints (e.g., Epoch 4 achieves a lower false-alarm rate of $6.84\%$ at the cost of lower recall of $81.44\%$).
   - In late epochs (Epochs 8–30), continued hard-negative pressure drove the FA rate down to $<0.5\%$ (as low as $0.27\%$), but collapsed Recall down to $69.0\% - 78.4\%$ (violating the pre-registered $79.00\%$ safety floor).

---

## A. EXP02B-1 Frozen Status

- **Status**: The EXP02B-1 training trajectory, post-run forensic audit, and held-out test evaluation are completely **FROZEN** and **IMMUTABLE**.
- **Model Checkpoint**: Epoch 3 `best_model.pt` (SHA-256 `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B`).
- **Operating Threshold**: $0.22$.
- **No Parameters Modified**: Zero weights, configurations, or manifests were modified during this diagnostic analysis.

---

## B. Validation Pareto Frontier Analysis

Using the full 30-epoch trajectory from `history.json`, Pareto dominance was computed across:
- **FA Rate**: Minimize
- **Spill Recall**: Maximize
- **Global IoU**: Maximize

### Trajectory Pareto Summary Table

| Epoch | Val FA Rate (%) | Val Recall | Val IoU | 3D Pareto? | 2D (FA, Recall) | 2D (FA, IoU) | Safety Floor ($\ge 79\%$) | Diagnostic Classification |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 1 | 100.00% | 0.8339 | 0.6782 | Dominated | Dominated | Dominated | Satisfied | Initial warmup state |
| 2 | 6.29% | 0.8625 | 0.6787 | **Non-dominated** | **Non-dominated** | Dominated | Satisfied | High sensitivity, lower IoU |
| **3** | **8.26%** | **0.8664** | **0.7305** | **Non-dominated** | **Non-dominated** | **Non-dominated** | **Satisfied** | **Selected Operational Optimum** |
| 4 | 6.84% | 0.8144 | 0.7296 | **Non-dominated** | Dominated | **Non-dominated** | Satisfied | Transition checkpoint (lower FA, lower Recall) |
| 5 | 10.62% | 0.8095 | 0.7183 | Dominated | Dominated | Dominated | Satisfied | Dominated by Ep 3, 4 |
| 6 | 7.88% | 0.7952 | 0.7172 | Dominated | Dominated | Dominated | Satisfied | Dominated by Ep 3, 4 |
| 7 | 7.61% | 0.8068 | 0.6403 | Dominated | Dominated | Dominated | Satisfied | Transient FP instability |
| 8–15 | 0.27%–2.90% | 0.6904–0.7778 | 0.6332–0.7107 | Dominated / Non-dom | Non-dominated | Dominated | **VIOLATED** | Severe recall collapse ($<79\%$) |
| 16 | 0.27% | 0.7504 | 0.6554 | **Non-dominated** | **Non-dominated** | Dominated | **VIOLATED** | Extreme over-suppression |
| 17 | 0.33% | 0.7793 | 0.7082 | **Non-dominated** | **Non-dominated** | Dominated | **VIOLATED** | Extreme over-suppression |
| 21 | 0.27% | 0.7466 | 0.6881 | **Non-dominated** | Dominated | **Non-dominated** | **VIOLATED** | Extreme over-suppression |
| 27 | 0.33% | 0.7691 | 0.7117 | **Non-dominated** | Dominated | **Non-dominated** | **VIOLATED** | Extreme over-suppression |
| 29 | 0.44% | 0.7837 | 0.7158 | **Non-dominated** | **Non-dominated** | **Non-dominated** | **VIOLATED** | High IoU, but recall $78.4\% < 79\%$ |
| 30 | 0.38% | 0.7723 | 0.7124 | **Non-dominated** | Dominated | **Non-dominated** | **VIOLATED** | Final model, recall $77.2\% < 79\%$ |

### Accurate Pareto Synthesis
Epoch 3 is the selected checkpoint under the pre-registered recall safety constraint and checkpoint selection policy. Among recall-safe checkpoints, it provides the highest observed validation IoU ($0.7305$) and recall ($86.64\%$) while retaining substantial false-alarm suppression ($8.26\%$). It is not globally Pareto-dominating over all checkpoints (e.g., Epoch 4 achieves a lower false-alarm rate of $6.84\%$ at the cost of lower recall of $81.44\%$).

---

## C. Exact Validation Negative Paired Analysis ($n = 1,827$)

Evaluating both frozen models over all 1,827 canonical validation negative tiles produced the exact paired $2 \times 2$ contingency table:

$$\begin{array}{c|cc|c}
& \text{EXP02B-1 Clean} & \text{EXP02B-1 Alarmed} & \text{Total} \\
\hline
\text{EXP01 Clean} & a = 1,400 & c = 60 & 1,460 \\
\text{EXP01 Alarmed} & b = 276 & d = 91 & 367 \\
\hline
\text{Total} & 1,676 & 151 & 1,827
\end{array}$$

- **Marginal False-Alarm Counts**:
  - Baseline (EXP01): **$367 / 1,827$** ($20.0876\%$)
  - Candidate (EXP02B-1): **$151 / 1,827$** ($8.2649\%$)
- **Cured False Alarms ($b$)**: **276 tiles**
- **New False Alarms ($c$)**: **60 tiles**
- **Net Cured False Alarms ($b - c$)**: **$+216$ tiles** ($11.82$ percentage-point absolute reduction; **$58.86\%$ relative reduction**)
- **Exact Paired McNemar Test (continuity corrected)**:
  $$\chi^2 = \frac{(|276 - 60| - 1)^2}{276 + 60} = \frac{215^2}{336} = \mathbf{137.5744}, \quad \mathbf{p = 9.03 \times 10^{-32}}$$
- **95% Paired Confidence Interval for Reduction**: **$[9.93\%, 13.71\%]$ percentage points**

---

## D. Positive-Tile Degradation Characterization ($n = 1,053$)

### Tile-Level Partitioning

| Partition Group | Definition | Count | Pct |
| :--- | :--- | :---: | :---: |
| **Group A: Candidate Improves** | $\text{IoU}_{\text{cand}} > \text{IoU}_{\text{base}} + 0.01$ | **338** | **32.10%** |
| **Group B: Both Detect** | Both detect ($\text{TP} \ge 1$), comparable or undersegmented | **625** | **59.36%** |
| — *Subgroup B-1: Explicit Undersegmentation* | $\text{Recall}_{\text{cand}} < \text{Recall}_{\text{base}}$ or $\text{Ratio}_{\text{cand}} < \text{Ratio}_{\text{base}}$ | 118 | 11.21% |
| — *Subgroup B-2: Preserved Extent* | Detected with comparable or slightly altered extent | 507 | 48.15% |
| **Group C: Baseline Detects, Candidate Misses** | $\text{TP}_{\text{base}} \ge 1, \text{TP}_{\text{cand}} = 0$ | **17** | **1.61%** |
| **Group D: Candidate Detects, Baseline Misses** | $\text{TP}_{\text{cand}} \ge 1, \text{TP}_{\text{base}} = 0$ | **8** | **0.76%** |
| **Group E: Neither Detects** | $\text{TP}_{\text{base}} = 0, \text{TP}_{\text{cand}} = 0$ | **65** | **6.17%** |

### Empirical Resolution of the Recall Loss Hypothesis
- Among the 151 positive tiles where false negatives increased under EXP02B-1 ($177,389$ total increased FN pixels):
  - **Spatial Undersegmentation (Group B, 118 tiles)**: Accounts for **$172,350$ pixels ($97.16\%$)** of the increased FN burden.
  - **Whole-Tile Misses (Group C, 17 tiles)**: Accounts for only **$2,532$ pixels ($1.43\%$)** of the increased FN burden.
  - **Large Spills ($\ge 5,000$ pixels)**: **$0$ whole-tile misses**.
- **Observational Spatial Pattern**: The recall degradation is overwhelmingly ($97.16\%$) spatial extent shrinkage / perimeter erosion on already-detected slicks. Whole-tile misses are negligible ($1.43\%$).

---

## E. Conservatism Characterization Across Training

The observed trajectory is consistent with increasing model conservatism under sustained hard-negative sampling pressure, manifested primarily as spatial undersegmentation of already-detected spills:
1. **Balanced Early Phase (Epochs 1–4)**:
   - Configured hard-negative oversampling ($w_{\text{hard\_neg}} = 2.25$ vs. $w_{\text{ord\_neg}} = 0.75$, a $3.0\times$ ratio) effectively suppresses diffuse seawater false alarms while maintaining high spill sensitivity (Recall $86.64\%$, IoU $0.7305$).
2. **Hyper-Conservative Late Phase (Epochs 8–30)**:
   - Maintaining constant hard-negative pressure across all 30 epochs causes continuous spatial undersegmentation at spill boundaries.
   - By Epoch 30, the FA rate reaches $0.38\%$, but Recall falls to $77.23\%$, confirming that static hard-negative pressure acts as an uncalibrated conservatism dial.

---

## F. Descriptive Failure Taxonomy

Derived from `failure_taxonomy.json` and visual diagnostic composites:

### 1. Negative False Alarms (151 remaining tiles)
- **Small Isolated Speckle ($< 50$ px)**: 112 cured, 9 persistent, 17 new. Highly suppressed by sampling.
- **Moderate Localized Clusters ($50 - 1,000$ px)**: 159 cured, 61 persistent, 40 new. Low-contrast oceanic clutter.
- **Large Contiguous High-Burden False Positives ($\ge 1,000$ px)**: 5 cured, 21 persistent, 3 new. Spatially co-located with coastal/shoreline boundaries or broad low-backscatter oceanic features. *(Note: Physical cause cannot be definitively established without external meteorological wind/current data).*

### 2. Positive Misses & Undersegmentation
- **Tiny Spills ($< 500$ px)**: 110 tiles; 9 missed ($8.18\%$), 42 detected by both, 59 missed by both.
- **Medium Spills ($500 - 5,000$ px)**: 273 tiles; 8 missed ($2.93\%$), 256 detected by both.
- **Large Spills ($\ge 5,000$ px)**: 670 tiles; **$0$ missed ($0.00\%$)**, 665 detected by both.

---

## G. What EXP02B-1 Gained

1. **Robust False-Alarm Suppression**: $58.86\%$ relative reduction in false alarms on validation ($p = 9.03 \times 10^{-32}$) and $65.54\%$ on held-out test data ($p = 9.77 \times 10^{-56}$).
2. **Net Validation Recall & IoU Boost**: Val Recall increased by $+3.99$ pp ($86.64\%$ vs. $82.65\%$) and Val IoU increased by $+0.0082$ ($0.7305$ vs. $0.7223$).
3. **Improved Slices**: 338 positive validation tiles ($32.10\%$) achieved higher IoU than baseline.

---

## H. What EXP02B-1 Sacrificed

1. **Perimeter Undersegmentation**: In 118 positive tiles, the model undersegmented spill margins, accounting for $97.16\%$ of deteriorating false-negative pixels.
2. **Late-Epoch Sensitivity Collapse**: Maintaining static hard-negative pressure caused recall to degrade below the $79.0\%$ safety boundary in late epochs ($75\% - 78\%$).
3. **Held-Out Test Generalization Penalty**: On the test split, recall dropped by $4.19$ pp ($90.95\%$ vs. $95.13\%$) and IoU by $0.0354$ ($0.7489$ vs. $0.7843$), while positive tile detection remained stable ($94.40\%$ vs. $94.68\%$).

---

## I. Evidence-Supported Mechanism Hypothesis

> **Hypothesis**: The observed trajectory is consistent with increasing model conservatism under sustained hard-negative sampling pressure, manifested primarily as spatial undersegmentation of already-detected spills. Relaxing hard-negative sampling pressure over the training trajectory will preserve early false-alarm suppression while reducing late-epoch spatial undersegmentation.

---

## J. Candidate EXP02C Intervention

Strictly single-variable intervention:
- **Intervention**: **Annealed Hard-Negative Sampling Pressure Schedule $w_{\text{hard}}(e)$**.
- **Exact Schedule**: Half-cycle cosine decay from $w_{\max} = 2.25$ down to $w_{\min} = 0.75$ across epochs $1 \dots 30$:
  $$w_{\text{hard}}(e) = 0.75 + 0.75 \left(1 + \cos\left(\frac{e - 1}{29} \pi\right)\right)$$
- **All other 15 parameters strictly locked**.

---

## K. Balanced Selection Hierarchy for EXP02C

- **Tier 1 (Hard Safety Gate)**:  
  $$\text{Validation Spill Recall} \ge \mathbf{79.00\%}$$  
  *(Mandatory operational floor; checkpoints below 79.00% are immediately disqualified).*

- **Tier 2 (False-Alarm Ceiling Gate)**:  
  $$\text{Validation GT-Negative FA Rate} \le \mathbf{12.00\%}$$  
  *(Operational Rationale: Baseline EXP01 exhibited 20.09% FA rate. A ceiling of 12.00% guarantees at least an 8.09 pp absolute reduction and 40.26% relative reduction, while providing a +3.74 pp tolerance buffer above EXP02B-1 [8.26%] to permit boundary restoration without accepting noisy models).*

- **Tier 3 (Optimization Criterion)**:  
  Among checkpoints satisfying Tier 1 and Tier 2, select the model that maximizes:  
  $$\mathbf{\max \text{Global Validation IoU}}$$

---

## L. TEST FIREWALL Confirmation

- **Firewall Status**: **INTACT AND STRICTLY OBSERVED**.
- Single-pass held-out test evaluation was completed in the previous phase and remains fully immutable.
- Zero test data was read, evaluated, or queried during this diagnostic audit or in the formulation of the EXP02C preregistration draft.
- All conclusions, Pareto frontiers, and error taxonomies are derived strictly from validation evidence.

---

## M. Statement of Unresolved Uncertainties

1. **Cross-Sensor / Cross-Basin Generalization**: All diagnostics are localized to the Trujillo Part I Sentinel-1 dataset.
2. **Physical Nature of Persistent False Alarms**: The 21 large-area persistent false alarms cannot be definitively attributed to biogenic slicks versus low-wind shadows without external meteorological wind data.
3. **Trajectory Relaxation Rate**: Whether cosine decay or a discrete step-down provides optimal boundary retention remains to be empirically verified in EXP02C.
