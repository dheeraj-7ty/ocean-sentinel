# CAO HELD-OUT TEST EVALUATION REPORT — EXP02B-1
**Status**: COMPLETED — IMMUTABLE FINAL AUDIT  
**Evaluation Mode**: Single-Pass Held-Out Test Evaluation  
**Timestamp UTC**: 2026-09-09T08:40:36Z  
**Authoritative Evaluator**: `scripts/evaluate_exp02b_1_test.py`  

---

## A. Experiment ID
- **Experiment Name**: EXP-02B-1 (Hard Negative SAR Tile Mining & Weighted Resampling)
- **Evaluation Run ID**: `test_eval_1788943005`
- **Output Artifact Directory**: `experiments/performance/exp02b_1_test_evaluation_20260909_140500/`

---

## B. Checkpoint Identity and SHA-256
- **Selected Checkpoint**: Epoch 3 (Certified Best Model from Remote 30-Epoch Training)
- **Checkpoint Path**: `experiments/performance/exp02b_1_hard_negative_training_20260909_094500/kernel_output/exp02b_1_hard_negative_training/best_model.pt`
- **File Size**: 292,538,013 bytes (292.5 MB)
- **Verified SHA-256**: `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B`
- **Checkpoint Metadata**:
  - `epoch`: 3
  - `val_iou`: 0.73054
  - `val_recall`: 0.86643
  - `val_neg_fa_rate`: 8.2649%
  - `threshold`: 0.22

---

## C. Manifest Identity and SHA-256
- **Source of Truth**: `data/metadata/trujillo_2024/spatial_split_manifest.json`
- **Verified SHA-256**: `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0`
- **Normalization Parameters** (computed strictly from Train split):
  - `channel_means`: `[-33.233136989478695, -19.941215852796695]`
  - `channel_stds`: `[6.489985665955077, 4.531345684833188]`
  - `computed_from_split`: `train`

---

## D. Runner/Source Identity and SHA-256
- **Runner Script Path**: `d:\Projects\ocean-sentinel\scripts\evaluate_exp02b_1_test.py`
- **Verified SHA-256**: `E68C372CAFD9CAC5656E191718FE82AC9D5233DF2ACEAE0E9F761700A4D4B5BD`
- **Execution Platform**: Windows 11, Python 3.10 / PyTorch 2.14.0+cu126, NVIDIA GeForce RTX 3050 Laptop GPU (sm_86)
- **Execution Mode**: CUDA AMP float16, batch size = 8, num_workers = 2

---

## E. Exact Test Population
- **Canonical Test Split Size**: Exactly **2,880 tiles** derived from **180 parent patches** (15.0% of the 19,200 total dataset tiles).
- **Exact Tiles Consumed**: **2,880 / 2,880** (100.0%).
- **Tile Breakdown**:
  - Ground-Truth Negative Tiles (clean seawater): **1,772 tiles** (61.53%)
  - Ground-Truth Positive Tiles (oil spill present): **1,108 tiles** (38.47%)
- **Data Integrity Audit**:
  - Test Tile ID Duplicates: 0
  - Cross-Split Contamination with Train (13,440 tiles): 0
  - Cross-Split Contamination with Val (2,880 tiles): 0

---

## F. Frozen Threshold
- **Decision Threshold**: Strictly locked to **0.22**.
- **Threshold Search / Tuning**: Exactly **0** search iterations. Zero post-hoc threshold modifications.

---

## G. Full Test Confusion Matrix
All metrics computed pixel-wise over all 2,880 512×512 test tiles (total pixels: 754,974,720):

| Cell | Definition | Pixel Count | Percentage of Test Domain |
| :--- | :--- | :--- | :--- |
| **TP** | True Positive (Oil correctly detected) | 29,404,493 | 3.8948% |
| **FP** | False Positive (False alarm over water/land) | 6,930,009 | 0.9179% |
| **FN** | False Negative (Missed oil spill) | 2,926,832 | 0.3877% |
| **TN** | True Negative (Clean water correctly silent) | 715,713,386 | 94.7996% |
| **Total** | All Pixels | 754,974,720 | 100.0000% |

---

## H–L. Primary Held-Out Test Metrics

| Metric | Measured Test Value | Description / Scope |
| :--- | :--- | :--- |
| **Test Global IoU** | **0.74894** | Intersection-over-Union at pixel level |
| **Test Dice Score** | **0.85645** | Harmonic mean of precision and recall |
| **Test Precision** | **0.80927** | Positive predictive value ($TP / (TP + FP)$) |
| **Test Recall** | **0.90947** | Sensitivity ($TP / (TP + FN)$) |
| **Test Loss** | **0.40903** | Combined BCE + Dice loss (weights 0.5/0.5, smooth 1.0) |
| **GT-Negative FA Rate** | **9.1986%** | **163 / 1,772** ground-truth negative tiles with $\ge 1$ FP pixel |
| **Extensive FA Rate** | **3.3860%** | **60 / 1,772** ground-truth negative tiles with $\ge 1,000$ FP pixels |
| **FP Pixel Burden** | **488,603 px** | Total FP pixels across all 1,772 negative tiles ($0.1052\%$ pixel fraction) |
| **Positive Tile Recall** | **94.4043%** | **1,046 / 1,108** positive tiles successfully detected |

---

## M. Comparison with Locked EXP01 Baseline on Same Canonical Test Split

Both models were evaluated on the **exact same 2,880 test tiles** using the exact same data pipeline, normalization, and frozen threshold $0.22$.

### Benchmark Comparison Table

| Metric | EXP01 Baseline (Teacher) | EXP02B-1 (Candidate) | Absolute Change | Relative Change |
| :--- | :--- | :--- | :--- | :--- |
| **Test Tiles Evaluated** | 2,880 | 2,880 | 0 | — |
| **GT-Negative FA Rate** | **26.6930%** (473 / 1,772) | **9.1986%** (163 / 1,772) | **-17.4944 pp** | **-65.54%** |
| **Global IoU** | **0.78434** | **0.74894** | -0.03540 | -4.51% |
| **Dice Score** | **0.87914** | **0.85645** | -0.02269 | -2.58% |
| **Precision** | **0.81713** | **0.80927** | -0.00786 | -0.96% |
| **Recall** | **0.95133** | **0.90947** | -0.04186 | -4.40% |
| **Positive Tile Detection** | **94.6751%** (1,049 / 1,108) | **94.4043%** (1,046 / 1,108) | -0.2708 pp (-3 tiles) | -0.29% |
| **FP Pixel Burden (Negatives)** | 529,139 px | 488,603 px | -40,536 px | -7.66% |
| **Test Loss** | 0.37854 | 0.40903 | +0.03049 | +8.05% |

### Exact Paired McNemar Test on All $n = 1,772$ Test Negative Tiles

Because both models were evaluated sequentially on the exact same tile order, the exact paired $2 \times 2$ contingency table was directly observed:

$$\begin{array}{c|cc|c}
& \text{EXP02B-1 Clean} & \text{EXP02B-1 Alarmed} & \text{Total} \\
\hline
\text{EXP01 Clean} & a = 1,261 & c = 38 & 1,299 \\
\text{EXP01 Alarmed} & b = 348 & d = 125 & 473 \\
\hline
\text{Total} & 1,609 & 163 & 1,772
\end{array}$$

- **Cured False Alarms ($b$)**: **348 tiles** (alarmed by EXP01, silenced by EXP02B-1)
- **New False Alarms ($c$)**: **38 tiles** (clean in EXP01, alarmed by EXP02B-1)
- **Net Cured Tiles ($b - c$)**: **+310 tiles**
- **McNemar $\chi^2$ (continuity corrected)**:
  $$\chi^2 = \frac{(|348 - 38| - 1)^2}{348 + 38} = \frac{309^2}{386} = \mathbf{247.3601}$$
- **Asymptotic $p$-value**: **$p = 9.77 \times 10^{-56}$**
- **95% Paired Confidence Interval for FA Rate Reduction**: **$[15.48\%, 19.51\%]$ percentage points**

---

## N. Validation-to-Test Generalization Gap (EXP02B-1)

| Metric | Validation (180 Patches / 2,880 Tiles) | Test (180 Patches / 2,880 Tiles) | Generalization Gap (Test − Val) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Global IoU** | 0.73054 | 0.74894 | **+0.01840** (+1.84 pp) | Positive Generalization |
| **Recall** | 0.86643 | 0.90947 | **+0.04304** (+4.30 pp) | Positive Generalization |
| **Precision** | 0.81710 | 0.80927 | **-0.00783** (-0.78 pp) | Consistent ($< 1$ pp shift) |
| **GT-Negative FA Rate** | 8.2649% (151 / 1,827) | 9.1986% (163 / 1,772) | **+0.9337 pp** | Stable within $< 1$ pp |

**Observation**: The candidate model exhibits zero sign of negative overfitting. Test IoU is $+1.84$ points higher than validation, test recall is $+4.30$ points higher, and the GT-negative false alarm rate remains stable at $9.20\%$ (vs. $8.26\%$ in validation).

---

## O. Integrity Audit Summary
1. **Pre-evaluation Audit**: 11 out of 11 mandatory checks strictly passed prior to loading test data.
2. **Contamination Check**: Zero overlap between train, val, and test tile IDs. Zero spatial parent patch leakage.
3. **Model Weights**: Bit-for-bit identical to training checkpoint (`54B4B098...`). No parameter modification.
4. **Decision Threshold**: Strictly frozen at $0.22$. No search grid was evaluated.
5. **Tile Population**: Exactly 2,880 tiles consumed from `spatial_split_manifest.json` (`C052720A...`).

---

## P. Confirmation of Single-Pass Evaluation
- Exactly **one single forward pass** over the 2,880 test tiles was executed.
- No rerun, no subsetting, no re-thresholding, and no hyperparameter adjustments were performed.
- All evaluation logs, timestamps, and step counters in `progress.log` and `run_state.json` confirm contiguous execution without repetition.

---

## Q. Final Scientific Interpretation

### Observed Facts
1. On the canonical 2,880 held-out test tiles, EXP02B-1 achieved an IoU of **0.74894**, recall of **0.90947**, and GT-negative tile false alarm rate of **9.1986%**.
2. Compared to the locked EXP01 baseline on the identical test split, EXP02B-1 reduced false alarms from $26.69\%$ to $9.20\%$ (an absolute reduction of **17.49 percentage points**, or a **65.54% relative reduction**).
3. In exact paired McNemar testing on the 1,772 test negative tiles, EXP02B-1 cured 348 false alarms while inducing 38 new ones ($\chi^2 = 247.36, p = 9.77 \times 10^{-56}$).
4. The reduction in false alarms was accompanied by a moderate trade-off in recall ($90.95\%$ vs. $95.13\%$, $-4.19$ percentage points) and global IoU ($0.7489$ vs. $0.7843$, $-0.0354$ IoU points), while positive tile detection remained essentially intact ($94.40\%$ vs. $94.68\%$, a difference of only 3 tiles out of 1,108).

### Inferences
1. The hard-negative mining and weighted resampling strategy demonstrably suppressed false alarms on unseen geographic regions without collapsing segmentation performance or violating the pre-registered safety boundary ($\text{Recall} \ge 79.0\%$).
2. The close agreement between validation metrics ($\text{IoU} = 0.7305, \text{FA} = 8.26\%$) and held-out test metrics ($\text{IoU} = 0.7489, \text{FA} = 9.20\%$) suggests stable out-of-sample generalization within the Trujillo Part I domain.

### Unverified
1. Performance on cross-sensor SAR data (e.g., Sentinel-1 GRD from other geographic basins or different satellite platforms) was not evaluated in this experiment.
2. Causal attribution of the suppression mechanism to specific architectural layers or loss components remains unmeasured without targeted ablation studies.
3. Operational production readiness under real-time streaming constraints was not tested.
