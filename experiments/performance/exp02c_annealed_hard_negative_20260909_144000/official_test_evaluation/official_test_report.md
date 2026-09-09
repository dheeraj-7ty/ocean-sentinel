# OFFICIAL EXP-02C HELD-OUT TEST EVALUATION REPORT

**Experiment ID**: `EXP-02C`  
**Candidate Checkpoint**: Epoch 26 (`best_model.pt`)  
**Checkpoint SHA-256**: `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A`  
**Spatial Split Manifest SHA-256**: `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0`  
**Test Evaluator Script**: [`scripts/evaluate_exp02c_test.py`](file:///d:/Projects/ocean-sentinel/scripts/evaluate_exp02c_test.py)  
**Evaluator Script SHA-256**: `28CFBD57042009B386BFFF3EEE3A01840C2FFB10CE2344E021761E6056DE2869`  
**Decision Threshold**: `0.22` (Strictly constant; zero threshold search, zero tuning)  
**Execution Environment**: Local NVIDIA GeForce RTX 3050 6GB Laptop GPU (`sm_86`), CUDA 12.6, PyTorch 2.14.0+cu126  
**Evaluation Timestamp**: `2026-09-09T14:26:35Z`  
**Official Test Status**: `COMPLETE`  

---

## 1. PRE-EVALUATION AUDIT & TEST FIREWALL VERIFICATION

Prior to reading any test split data, automated integrity assertions strictly verified:
1. **Checkpoint Identity**: `best_model.pt` exists at `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/best_model.pt`. SHA-256 matches expected certified hash `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` exactly.
2. **Metadata Contract**: Checkpoint metadata verifies `epoch = 26`, `val_iou = 0.72879`, `val_recall = 0.8203`, and `threshold = 0.22`.
3. **Architecture Contract**: `ResNet34UNet` (`in_channels=2, num_classes=1, adaptation_method='slice_variance_scaled'`) loaded with zero missing and zero unexpected keys. Total parameters: `24,346,305` (100% finite real numbers).
4. **Data Partition Integrity**: Manifest `spatial_split_manifest.json` verified (`C052720A...`). Test partition cardinality = `2,880` tiles across 180 parent patches. Zero duplicate tile IDs. Zero test/train or test/val cross-split overlap.
5. **Preprocessing & Transforms**: Unaugmented `IdentityTransform()` + canonical z-score normalization ($\text{VV}: \mu=-33.233137, \sigma=6.489986; \text{VH}: \mu=-19.941216, \sigma=4.531346$).
6. **Execution Firewall**: Evaluator operated strictly in `torch.no_grad()` evaluation mode. Zero optimizer instances created, zero backward passes executed, zero model weights updated. Output written exclusively to isolated directory `official_test_evaluation/`.

---

## 2. OFFICIAL HELD-OUT TEST EVALUATION RESULTS

The single official pass over all 2,880 canonical test tiles produced the following certified metrics:

### Primary Segmentation Endpoints:
| Metric | Official Test Value | Definition / Calculation |
|---|:---:|---|
| **Global Test IoU** | **`0.79808`** | $\frac{\text{TP}}{\text{TP} + \text{FP} + \text{FN}}$ across all $754,974,720$ test pixels |
| **Test Dice (F1-Score)** | **`0.88770`** | $\frac{2 \cdot \text{TP}}{2 \cdot \text{TP} + \text{FP} + \text{FN}}$ |
| **Test Precision** | **`0.84864`** | $\frac{\text{TP}}{\text{TP} + \text{FP}}$ |
| **Test Recall** | **`0.93054`** | $\frac{\text{TP}}{\text{TP} + \text{FN}}$ |
| **Combined Test Loss** | **`0.08040`** | $0.5 \cdot \text{BCE} + 0.5 \cdot \text{Dice}$ ($\text{smooth}=1.0$) |
| **Tiles Consumed** | **`2,880`** | $100\%$ of canonical held-out test split |
| **Duration / Throughput** | **`53.3 s`** | $54.0$ tiles / second on RTX 3050 GPU |

### Pixel-Level Confusion Matrix ($2,880 \text{ tiles} \times 512 \times 512 = 754,974,720 \text{ pixels}$):
| Matrix Cell | Pixel Count | Percentage of Total Pixels |
|---|:---:|:---:|
| **True Positive (TP)** | $30,085,500$ | $3.985\%$ |
| **False Positive (FP)** | $5,365,909$ | $0.711\%$ |
| **False Negative (FN)** | $2,245,825$ | $0.297\%$ |
| **True Negative (TN)** | $717,277,486$ | $95.007\%$ |
| **Total Pixels** | $754,974,720$ | $100.000\%$ |

---

## 3. POPULATION-STRATIFIED & ERROR DIAGNOSTICS

### Ground-Truth Negative Test Tiles ($n = 1,772$ tiles, 61.53% of test split):
| Diagnostic Metric | Value | Reference / Criteria |
|---|:---:|---|
| **Total Negative Test Tiles** | `1,772` | Tiles with zero ground-truth oil spill pixels |
| **False Alarm Tiles ($\text{FP} \ge 1 \text{ px}$)** | **`48`** | Only 48 of 1,772 negative tiles produced any false alarm |
| **GT-Negative False-Alarm Rate** | **`2.7088%`** | Well below the $\le 12.00\%$ validation ceiling |
| **FP Pixel Burden Total** | `335,902` px | Total false-alarm pixels across all 1,772 negative tiles |
| **FP Pixel Fraction** | `0.000723` | $\frac{335,902}{1,772 \times 512 \times 512}$ |
| **Macro False-Alarm Tiles ($\text{FP} \ge 100 \text{ px}$)** | `45` | Macro FA Rate: $2.5401\%$ |
| **Extensive False-Alarm Tiles ($\text{FP} \ge 1000 \text{ px}$)** | `26` | Extensive FA Rate: $1.4673\%$ |

### Ground-Truth Positive Test Tiles ($n = 1,108$ tiles, 38.47% of test split):
| Diagnostic Metric | Value | Reference / Criteria |
|---|:---:|---|
| **Total Positive Test Tiles** | `1,108` | Tiles containing oil spill pixels |
| **Detected Positive Tiles ($\text{TP} \ge 1 \text{ px}$)** | `989` | Positive tiles with at least 1 true-positive pixel |
| **Positive-Tile Detection Rate** | **`89.2599%`** | $989 / 1,108$ positive tiles detected |
| **Predicted-to-Ground-Truth Area Ratio** | **`1.0861`** | $\frac{35,451,409 \text{ pred px}}{32,646,678 \text{ gt px}}$. The aggregate predicted-to-ground-truth area ratio was 1.0861, indicating that the test-set prediction area did not exhibit the strong aggregate shrinkage observed during the EXP02C mid-trajectory. However, 159 of 1,108 positive tiles remained individually undersegmented. |
| **Undersegmented Tiles ($\text{pred} < 0.80 \cdot \text{gt}$)** | `159` | Only 159 of 1,108 positive tiles undersegmented |
| **Tiny Spill Recall ($\text{area} < 500 \text{ px}$)** | **`53.46%`** | Recall on smallest spill fragments |
| **Medium Spill Recall ($500 \le \text{area} < 5000 \text{ px}$)** | **`79.83%`** | Recall on medium oil slicks |
| **Large Spill Recall ($\text{area} \ge 5000 \text{ px}$)** | **`93.34%`** | Recall on large continuous slicks |

---

## 4. COMPARATIVE MATRIX AGAINST CANONICAL BASELINES

All three models evaluated on the exact same canonical 2,880 test tiles using locked threshold `0.22`:

| Evaluation Metric | Baseline `EXP-01` | Candidate `EXP-02B-1` (Ep 3) | Official `EXP-02C` (Ep 26) | Delta vs EXP-01 | Delta vs EXP-02B-1 |
|---|:---:|:---:|:---:|:---:|:---:|
| **Checkpoint Path** | `exp01_baseline/best_model.pt` | `exp02b_1/.../best_model.pt` | `exp02c/.../best_model.pt` | — | — |
| **Checkpoint SHA-256** | `9B8BD867...` | `54B4B098...` | `14073F67...` | — | — |
| **Global Test IoU** | $0.78434$ | $0.74894$ | **`0.79808`** | **`+0.01374`** | **`+0.04914`** |
| **Test Dice (F1)** | $0.87914$ | $0.85645$ | **`0.88770`** | **`+0.00856`** | **`+0.03125`** |
| **Test Precision** | $0.81713$ | $0.80927$ | **`0.84864`** | **`+0.03151`** | **`+0.03937`** |
| **Test Recall** | $0.95133$ | $0.90947$ | **`0.93054`** | $-0.02079$ | **`+0.02107`** |
| **GT-Negative FA Rate** | $26.6930\%$ ($473$ tiles) | $9.1986\%$ ($163$ tiles) | **`2.7088%` ($48$ tiles)** | **`-23.9842 pp`** | **`-6.4898 pp`** |
| **Relative FA Reduction** | $0.00\%$ (Ref) | $65.54\%$ | **`89.85%`** | **`89.85% reduction`** | **`70.55% reduction`** |
| **Positive Tile Detection** | $92.42\%$ | $88.99\%$ | **`89.26%`** | $-3.16\text{ pp}$ | $+0.27\text{ pp}$ |
| **Extensive FA ($\ge 1000$ px)**| $145$ tiles ($8.18\%$) | $49$ tiles ($2.77\%$) | **`26` tiles (`1.47%`)** | **`-119 tiles`** | **`-23 tiles`** |

---

## 5. EXACT PAIRED TILE-LEVEL STATISTICAL CONTINGENCY

Because all models were evaluated sequentially on the exact same deterministic test loader, exact paired tile-level discordant outcomes were computed across all $n = 1,772$ negative test tiles.

### A. EXP-02C (Epoch 26) vs Baseline EXP-01 ($n = 1,772$ tiles)

#### Paired $2 \times 2$ Contingency Table:
```
                        EXP-02C Negative (Clean)    EXP-02C False Alarm       Total
EXP-01 Negative (Clean)          a = 1,298                  c = 1             1,299
EXP-01 False Alarm               b = 426                   d = 47               473
Total                            1,724                     48                 1,772
```

- **Cells**:
  - $a = 1,298$: Clean in both models
  - $b = 426$: False alarm in EXP-01, **clean in EXP-02C** (cured tiles)
  - $c = 1$: Clean in EXP-01, false alarm in EXP-02C (only 1 new false alarm tile across entire split)
  - $d = 47$: False alarm in both models
- **Net Alarm Reduction ($b - c$)**: $426 - 1 = \mathbf{425\text{ tiles}}$
- **Absolute FA Rate Reduction**: $\frac{425}{1,772} = \mathbf{23.9842\text{ percentage points}}$
- **Relative FA Reduction**: $\frac{425}{473} = \mathbf{89.85\%}$
- **Continuity-Corrected McNemar Test**:
  $$\chi^2 = \frac{(|b - c| - 1)^2}{b + c} = \frac{(|426 - 1| - 1)^2}{426 + 1} = \frac{424^2}{427} = \mathbf{421.0211}$$
  $$p\text{-value} = \mathbf{1.46 \times 10^{-93}}$$
- **Wald 95% Paired Confidence Interval**:
  $$\text{SE} = \sqrt{\frac{(b + c) - \frac{(b - c)^2}{n}}{n^2}} = \sqrt{\frac{427 - \frac{425^2}{1772}}{1772^2}} = 0.010174 \implies \mathbf{[21.99\%, 25.98\%]\text{ percentage points}}$$

---

### B. EXP-02C (Epoch 26) vs Candidate EXP-02B-1 Epoch 3 ($n = 1,772$ tiles)

#### Paired $2 \times 2$ Contingency Table:
```
                          EXP-02C Negative (Clean)    EXP-02C False Alarm       Total
EXP-02B-1 Negative (Clean)         a = 1,608                  c = 1             1,609
EXP-02B-1 False Alarm              b = 116                   d = 47               163
Total                              1,724                     48                 1,772
```

- **Cells**:
  - $a = 1,608$: Clean in both models
  - $b = 116$: False alarm in EXP-02B-1, **clean in EXP-02C** (cured tiles)
  - $c = 1$: Clean in EXP-02B-1, false alarm in EXP-02C (only 1 new false alarm tile)
  - $d = 47$: False alarm in both models
- **Net Alarm Reduction ($b - c$)**: $116 - 1 = \mathbf{115\text{ tiles}}$
- **Absolute FA Rate Reduction**: $\frac{115}{1,772} = \mathbf{6.4898\text{ percentage points}}$
- **Relative FA Reduction**: $\frac{115}{163} = \mathbf{70.55\%}$
- **Continuity-Corrected McNemar Test**:
  $$\chi^2 = \frac{(|b - c| - 1)^2}{b + c} = \frac{(|116 - 1| - 1)^2}{116 + 1} = \frac{114^2}{117} = \mathbf{111.0769}$$
  $$p\text{-value} = \mathbf{5.69 \times 10^{-26}}$$
- **Wald 95% Paired Confidence Interval**:
  $$\text{SE} = 0.005906 \implies \mathbf{[5.33\%, 7.65\%]\text{ percentage points}}$$

---

## 6. TRIPARTITE SCIENTIFIC ASSESSMENT

### A. Observed Facts
1. On the canonical 2,880 held-out test tiles, EXP-02C (Epoch 26) achieved Global IoU = **`0.79808`**, Recall = **`0.93054`**, Precision = **`0.84864`**, Dice = **`0.88770`**, and Loss = **`0.08040`**.
2. On the 1,772 ground-truth negative test tiles, EXP-02C produced **`48`** false alarm tiles (GT-Negative FA Rate = **`2.71%`**).
3. The exact paired contingency table against EXP-01 baseline demonstrates $b = 426$ cured false alarms and $c = 1$ new false alarm (net reduction: 425 tiles; $\chi^2 = 421.0211, p = 1.46 \times 10^{-93}$).
4. The exact paired contingency table against EXP-02B-1 Epoch 3 demonstrates $b = 116$ cured false alarms and $c = 1$ new false alarm (net reduction: 115 tiles; $\chi^2 = 111.0769, p = 5.69 \times 10^{-26}$).
5. On the 1,108 ground-truth positive test tiles, the predicted-to-ground-truth area ratio was **`1.0861`**, positive tile detection was **`89.26%`**, and undersegmented tile count was `159`.
6. Zero test tiles were evaluated more than once; zero optimizer updates or threshold adjustments occurred during or after evaluation.

### B. Inferences
1. On the canonical held-out Trujillo test split, EXP02C Epoch 26 outperforms both EXP-01 and EXP-02B-1 on global IoU and precision while substantially reducing GT-negative false alarms, with recall remaining high.
2. The aggregate predicted-to-ground-truth area ratio of 1.0861 is consistent with mitigation of the strong late-epoch aggregate area shrinkage observed earlier in the EXP02C trajectory. However, 159 of 1,108 positive tiles remained individually undersegmented, and tiny-spill recall was 53.46%.
3. The simultaneous improvement in Global IoU (+0.0137 vs EXP-01, +0.0491 vs EXP-02B-1) and Precision (+0.0315 vs EXP-01, +0.0394 vs EXP-02B-1) indicates that false alarms were suppressed without inducing aggregate perimeter collapse on positive test slicks.
4. This finding is an inference grounded in the empirical test measurements of the canonical Trujillo partition, not a universal mathematical proof for arbitrary SAR sensors or ocean basins.

### C. Unverified Mechanisms
1. The degree to which these exact false-alarm suppression and perimeter preservation boundaries generalize beyond the Sentinel-1 SAR imagery in the Trujillo 2024 distribution remains unverified.
2. The internal representations across specific encoder layers explaining why exactly one new false alarm tile was triggered relative to baseline remain unprobed at the latent activation level.

---

## 7. POST-EVALUATION INTEGRITY VERIFICATION

- [x] Exactly 2,880 test tiles consumed in a single deterministic pass.
- [x] Zero optimizer updates executed.
- [x] Zero threshold searches or post-hoc tunings performed (threshold locked at 0.22).
- [x] Checkpoint `best_model.pt` SHA-256 strictly unchanged: `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A`.
- [x] All 7 official test artifacts successfully generated and persisted.

---

## 8. OFFICIAL TEST CONCLUSION

On the canonical held-out Trujillo test split, EXP02C Epoch 26 outperforms both EXP-01 and EXP-02B-1 on global IoU and precision while substantially reducing GT-negative false alarms, with recall remaining high. The aggregate predicted-to-ground-truth area ratio of 1.0861 is consistent with mitigation of the strong late-epoch aggregate area shrinkage observed earlier in the EXP02C trajectory. However, 159 of 1,108 positive tiles remained individually undersegmented, and tiny-spill recall was 53.46%.

```
================================================================================
OFFICIAL TEST STATUS: COMPLETE
CANDIDATE CHECKPOINT: EXP-02C (EPOCH 26)
TEST GLOBAL IOU:      0.79808
TEST RECALL:          93.05%
TEST GT-NEG FA RATE:  2.71% (48 / 1,772 TILES)
VS EXP-01 BASELINE:   89.85% RELATIVE FA REDUCTION (p = 1.46e-93)
VS EXP-02B-1 CANDIDATE: 70.55% RELATIVE FA REDUCTION (p = 5.69e-26)
================================================================================
```

---

## 9. DOCUMENTATION CHANGE LOG: SCIENTIFIC LANGUAGE CORRECTIONS

| Item # | Previous Phrasing / Formulation | Corrected Formulation | Scientific Rationale |
|:---:|---|---|---|
| **1** | *"Perimeter shrinkage eliminated"* / *"Zero spatial undersegmentation/shrinkage"* | *"The aggregate predicted-to-ground-truth area ratio was 1.0861, indicating that the test-set prediction area did not exhibit the strong aggregate shrinkage observed during the EXP02C mid-trajectory. However, 159 of 1,108 positive tiles remained individually undersegmented."* | Corrected because aggregate area ratio exceeding 1.0 does not imply zero individually undersegmented tiles; 159 positive tiles remained undersegmented, and tiny-spill recall was 53.46%. |
| **2** | *"eliminates late-epoch perimeter shrinkage"* | *"is consistent with mitigation of the strong late-epoch aggregate area shrinkage observed earlier in the EXP02C trajectory."* | Formulates as an inference consistent with empirical trajectory measurements rather than an absolute claim of elimination. |
| **3** | Unqualified high-level summary claims | Explicit qualification: *"159 of 1,108 positive tiles remained individually undersegmented, and tiny-spill recall was 53.46%."* | Preserves crucial localized and small-object performance limitations alongside global macro metric gains. |
| **4** | *"decisively outperforms both..."* | *"On the canonical held-out Trujillo test split, EXP02C Epoch 26 outperforms both EXP-01 and EXP-02B-1 on global IoU and precision while substantially reducing GT-negative false alarms, with recall remaining high."* | Limits claim strictly to measured endpoints and population domain, eliminating ungrounded rhetorical overclaims. |

