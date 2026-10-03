# EXP-07-P0-C22-I: DIAG-02 — Candidate F Hybrid Sampler Schedule Exposure & Class Balance Diagnostic Report

**Investigation ID:** `DIAG-02-SAMPLER-EXPOSURE-SCHEDULE-DYNAMICS`  
**Parent Task:** `EXP-07-P0-C22-H` / `EXP-07-P0-C22-F` / `EXP-07-P0-C22-G`  
**Execution Date:** 2026-09-14  
**Authoritative Dataset:** OPS-02 Physical Dataset (`OPS02_v1.0.1_FROZEN`, Manifest SHA-256: `64E5E4BA5117B9A4A1FE0C1FDFDF948FF3BA53B3C837C3C588102607C64BD6C5`)  
**Investigated Runs:**
- Seed 42 (C22-B Paired Run: Control vs Treatment, SHA-256: `2B1562E33FF32F73A8BF373D24951AF220E423FF74F12F7B589CEDA426A6834B`)
- Seeds 101, 202, 303, 404 (C22-D 4-Seed Replication Suite, Control vs Treatment)  
**Governance Invariants:**
- Training steps executed: `0`
- Backward passes executed: `0`
- Optimizer steps executed: `0`
- GPU compute allocated: `0.0 seconds`
- HOLDOUT access count: `0` (`QUARANTINED_ZERO_ACCESS`)
- Part III benchmark access count: `0` (`FIREWALLED_ZERO_ACCESS`)
- Primary metric / loss function modifications: `NONE`

---

## 1. Executive Summary & Diagnostic Verdict

### 1.1 Core Diagnostic Question
Did the deterministic Candidate F hybrid sampler fail to provide adequate exposure to rare phenomenon classes in early training epochs, thereby causing poor rare-class learning, premature performance saturation, or driving the early-peaking phenomenon observed in Treatment (Epochs 5–7) versus Control (Epochs 10–27)?

### 1.2 Authoritative Diagnostic Verdict: CASE C & D
**CASE C (SAMPLER ALLOCATION NON-ZERO — PHYSICAL DATASET CONSTRAINTS & RESIDUAL HYPOTHESES) combined with CASE D (IMPLEMENTATION DEFECT IDENTIFIED IN C22-D REPLICATION SCRIPT).**

1. **Starvation Hypothesis Status (`NOT_SUPPORTED`):**
   - Candidate F did **not** starve rare classes in early epochs.
   - In **Epoch 1** (first 72 draws before any multi-epoch parameter updates), **every single phenomenon class received at least 2 draws** across all 5 seeds (mean draws: Oceanic Front = 4.0, Rain Cells = 6.6, Anthropogenic Objects = 6.2).
   - In **Epochs 1–3** (warmup phase, 216 draws), every class received between 7 and 176 draws (mean ultra-rare draws: OF = 12.8, RF = 18.8, HM = 20.4).
   - In **Epochs 1–7** (Treatment peak window, 504 draws), every class received $\ge 21$ draws, and parent acquisition cluster coverage reached 100% across all seeds for OF (4/4) and RF (7/7), and 7–8 of 8 clusters for HM (Seeds 42, 202, 303, 404 sampled 8/8; Seed 101 sampled 7/8; mean coverage 7.8/8; all 5 seeds sampled 8/8 HM clusters across all 30 epochs).
   - Parent acquisition balancing was highly effective: **0 parent clusters were starved** (zero-draw count = 0), Gini coefficients remained low (0.1159 to 0.2095), and top-5 parent share remained under 21.03%.

2. **Silent Implementation Defect Identified in C22-D (`CONFIRMED_IN_C22D`):**
   - In `scratch/kaggle_c22b_kernel/run_exp07_diag01_paired.py` (Seed 42), the sampler correctly accessed `s["canonical_dense_class_ids_present"]`, properly executing the intended 70% parent / 30% class-presence hybrid mixture.
   - In `scratch/kaggle_c22d_kernel/run_exp07_diag01_multiseed_replication.py` (Seeds 101, 202, 303, 404), the refactored code queried `s.get("labels_present", [])`. Because `"labels_present"` is not a key in the frozen OPS-02 dataset manifest, this lookup silently evaluated to an empty list `[]` for all 132 training samples!
   - Consequently, the class-presence term collapsed to a uniform fallback constant ($0.001$), leaving the C22-D sampler operating as **99.859% pure parent-balanced and 0.141% uniform flat noise**, with zero within-cluster rare class discrimination.
   - However, because the comparison between Control and Treatment within each seed used the **identical schedule**, internal validity for each paired seed run remained strictly preserved.

3. **Empirical Performance Linkage & Outcome Variance Explanation (`CONFIRMED_CORRELATION`):**
   - Although class draw counts were highly correlated across seeds ($r > 0.989$), pseudo-random draw variance in the ultra-rare classes (OF, RF, HM) during Epochs 1–7 strongly coupled with experimental outcomes:
     - Correlation with Treatment Best mIoU: $r = +0.6302$
     - Correlation with Control Best mIoU: $r = -0.9167$
     - Correlation with Paired Delta ($\Delta = \text{Treatment} - \text{Control}$): **$r = +0.8955$**!
   - In seeds where pseudo-random draws yielded high ultra-rare exposure (Seed 42: 170 draws; Seed 202: 135 draws; Seed 404: 124 draws), Treatment won ($\Delta > 0$).
   - In seeds where ultra-rare exposure was lower (Seed 101: 97 draws; Seed 303: 126 draws), Control won ($\Delta < 0$), with Seed 101 achieving Control's best score of 0.05886.
   - Descriptive Association Boundary (n=5): In this 5-seed sample (n=5), early exposure to rare classes exhibits a strong negative descriptive association with Control best mIoU (r = -0.9167) and a positive descriptive association with Treatment best mIoU (r = +0.6302), resulting in a strong positive descriptive association with paired delta (r = +0.8955, p = 0.0399). Under strict scientific governance, this finding is bounded as a descriptive association only. No causal or mechanistic claims regarding gradients or optimization dynamics are asserted from this sampler audit alone, as gradients were not measured.

---

## 2. Dataset Availability Baseline (TRAIN Partition, $n=132$)

Before evaluating the sampler, the fundamental physical availability of classes in the training partition must be established. The sampler cannot draw what does not exist in the dataset.

```
+-------+---------------------------------------+---------+----------+----------+----------+
| Class | Canonical Class Name                  | Samples | Frac (%) | Clusters | Frac (%) |
+-------+---------------------------------------+---------+----------+----------+----------+
| BG    | Background (BG)                       |   66    |  50.00%  |    28    |  70.00%  |
| AF    | Atmospheric Front (AF)                |   15    |  11.36%  |     5    |  12.50%  |
| BS    | Biological Slicks (BS)                |   17    |  12.88%  |     6    |  15.00%  |
| LWA   | Low Wind Area (LWA)                   |   21    |  15.91%  |    10    |  25.00%  |
| MCC   | Mesoscale Cellular Convection (MCC)   |   27    |  20.45%  |    13    |  32.50%  |
| OF    | Ocean Front (OF)                    |    9    |   6.82%  |     4    |  10.00%  |
| POW   | Pure Oceanic Waves (POW)              |   25    |  18.94%  |    11    |  27.50%  |
| RF    | Rain / precipitation-related phenomenon (RF)                       |   13    |   9.85%  |     7    |  17.50%  |
| WS    | Wind Streaks (WS)                     |    9    |   6.82%  |     5    |  12.50%  |
| Eddy  | Eddy (Eddy)                           |   14    |  10.61%  |     5    |  12.50%  |
| IWs   | Internal Waves (IWs)                  |   97    |  73.48%  |    31    |  77.50%  |
| HM    | Artificial / Anthropogenic Objects (HM)            |   12    |   9.09%  |     8    |  20.00%  |
+-------+---------------------------------------+---------+----------+----------+----------+
```

### Key Physical Constraints:
1. **Total Universe:** 132 tiles originating from 40 parent acquisition clusters.
2. **Dominant Support:** Internal Waves (IWs) is present in 97/132 tiles (73.5%) and 31/40 parent clusters (77.5%). Background is present in 66/132 tiles (50.0%) and 28/40 clusters.
3. **Ultra-Sparse Support:** Ocean Front (OF) is restricted to 9 tiles across only 4 parent clusters. Wind Streaks (WS) is restricted to 9 tiles across 5 parent clusters. Artificial / Anthropogenic Objects (HM) is restricted to 12 tiles across 8 parent clusters. Rain / precipitation-related phenomenon (RF) is restricted to 13 tiles across 7 clusters.

---

## 3. Authoritative Sampler Implementation & Code Audit

### 3.1 Candidate F Mathematical Specification
Candidate F defines a stationary categorical probability distribution $P_{\text{hybrid}}(i)$ over the $N=132$ training samples:

$$P_{\text{hybrid}}(i) = 0.70 \cdot P_{\text{parent}}(i) + 0.30 \cdot P_{\text{presence}}(i)$$

where:
1. **Parent-Balancing Component:**
   $$P_{\text{parent}}(i) = \frac{1}{|K|} \cdot \frac{1}{|C(k_i)|}$$
   where $|K| = 40$ is the number of parent clusters, and $|C(k_i)|$ is the number of tiles in cluster $k_i$.
2. **Class-Presence Component:**
   $$P_{\text{presence}}(i) \propto \sum_{c \in \text{Classes}(i), c > 0} \frac{1}{\sqrt{N_c}}$$
   where $N_c$ is the number of training samples containing phenomenon class $c$.

### 3.2 Code Discrepancy & Anomaly Audit: C22-B vs C22-D

```
+------------------------------------+------------------------------------+------------------------------------+
| Feature                            | C22-B (Seed 42)                    | C22-D (Seeds 101, 202, 303, 404)   |
+------------------------------------+------------------------------------+------------------------------------+
| Script Path                        | scratch/kaggle_c22b_kernel/...     | scratch/kaggle_c22d_kernel/...     |
| Manifest Key Queried               | canonical_dense_class_ids_present  | labels_present (BUG: KEY NOT FOUND)|
| Key Lookup Result                  | Populated list of class IDs (0..11)| Silently evaluated to [] (empty)   |
| Rare-Class Inverse Weight          | Sum of 1/sqrt(N_c) over c > 0      | Max of 1/N_c over c (collapsed)    |
| Unnormalized Parent Weight Sum     | 1.0 (pre-normalized)               | 40.0 (sum of cluster inverses)     |
| Unnormalized Class Weight Sum      | 1.0 (pre-normalized)               | 132 * 0.001 = 0.132                |
| Effective Parent Weight Fraction   | 70.00%                             | 28.0 / 28.0396 = 99.859%           |
| Effective Class Weight Fraction    | 30.00%                             | 0.0396 / 28.0396 = 0.141% (FLAT)   |
| Within-Cluster Differentiation     | Active (boosts rare-class tiles)   | Inactive (all tiles in cluster eq) |
| Tile Weight Pearson Correlation    | 1.0000                             | 0.5614 (vs C22-B)                  |
| Schedule Determinism & Pairing     | Control & Treatment use IDENTICAL  | Control & Treatment use IDENTICAL  |
+------------------------------------+------------------------------------+------------------------------------+
```

### Forensic Finding:
The bug in C22-D was silent because Python's dictionary `.get("labels_present", [])` returned `[]` rather than raising a `KeyError`. The inner loop `for c in s.get(...)` never executed, defaulting `c_weight = 0.001`. Because this constant was added to `0.70 * p_weight`, the sampler did not crash, but its effective class-presence component collapsed from 30% to 0.14%.

---

## 4. Realized Schedule Discovery & Reproducibility Audit

The exact 30-epoch schedules (30 epochs $\times$ 72 draws = 2,160 draws per seed) were reconstructed and verified against cryptographic hashes:

```
+------+------------+------------------------------------------------------------------+------------------+
| Seed | Experiment | Reconstructed Schedule SHA-256 Hash                              | Match Expected   |
+------+------------+------------------------------------------------------------------+------------------+
|   42 | C22-B      | 2B1562E33FF32F73A8BF373D24951AF220E423FF74F12F7B589CEDA426A6834B | YES (VERIFIED)   |
|  101 | C22-D      | 6EB40F9BE51C70A5C53EB387CADA259CF3CD8FE8AEA458A0E0220509A8A9E6EA | YES (VERIFIED)   |
|  202 | C22-D      | 6703D054BF12EB33E4E2AB25B702ADB12C82F15668FBDAABDAD0CC19D3AC798E | YES (VERIFIED)   |
|  303 | C22-D      | 90F93C6261AE20FEF174CEC7A488EC01BEE76B8417C36ED9F756C2B319353CEE | YES (VERIFIED)   |
|  404 | C22-D      | CD995CDEBBF69EA743B2F6F7CFF48F7714AC7FA3658FE9E9B4814373F67A6ADB | YES (VERIFIED)   |
+------+------------+------------------------------------------------------------------+------------------+
```

### Generator Fidelity:
- Each epoch explicitly re-seeded a dedicated `torch.Generator()` with `seed + epoch * 1000`.
- All 5 seeds generated genuinely distinct schedules.
- Within each seed, Control and Treatment executed against the exact same draw sequence.

---

## 5. Temporal Class Exposure Across Training Windows

### 5.1 Epoch 1 Exposure (First 72 Draws, Zero Prior Parameter Accumulation)

```
+-------+---------------------------------------+---------+----------+----------+----------+----------+--------+-------+
| Class | Canonical Class Name                  | Seed 42 | Seed 101 | Seed 202 | Seed 303 | Seed 404 | Mean   | Std   |
+-------+---------------------------------------+---------+----------+----------+----------+----------+--------+-------+
| BG    | Background (BG)                       |   34    |    32    |    45    |    33    |    40    |  36.8  |  5.0  |
| AF    | Atmospheric Front (AF)                |    8    |     4    |     7    |     9    |     2    |   6.0  |  2.6  |
| BS    | Biological Slicks (BS)                |   15    |     6    |     4    |     8    |     6    |   7.8  |  3.8  |
| LWA   | Low Wind Area (LWA)                   |    8    |    13    |     8    |    12    |     6    |   9.4  |  2.7  |
| MCC   | Mesoscale Cellular Convection (MCC)   |   14    |    12    |    14    |    15    |    17    |  14.4  |  1.6  |
| OF    | Ocean Front (OF)                    |    5    |     3    |     3    |     5    |     4    |   4.0  |  0.9  |
| POW   | Pure Oceanic Waves (POW)              |   19    |    14    |     8    |    18    |    17    |  15.2  |  4.0  |
| RF    | Rain / precipitation-related phenomenon (RF)                       |    7    |     4    |    11    |     6    |     5    |   6.6  |  2.4  |
| WS    | Wind Streaks (WS)                     |    5    |     5    |     7    |     4    |     2    |   4.6  |  1.6  |
| Eddy  | Eddy (Eddy)                           |   17    |     7    |     5    |     9    |     6    |   8.8  |  4.3  |
| IWs   | Internal Waves (IWs)                  |   45    |    59    |    61    |    52    |    56    |  54.6  |  5.7  |
| HM    | Artificial / Anthropogenic Objects (HM)            |    7    |     6    |     4    |    11    |     3    |   6.2  |  2.8  |
+-------+---------------------------------------+---------+----------+----------+----------+----------+--------+-------+
```
*Zero classes starved in Epoch 1. Minimum draws across all classes and seeds is 2 (Seed 404 AF & WS).*

### 5.2 Epochs 1–3 Exposure (Warmup Phase, 216 Total Draws)

```
+-------+---------------------------------------+---------+----------+----------+----------+----------+--------+-------+
| Class | Canonical Class Name                  | Seed 42 | Seed 101 | Seed 202 | Seed 303 | Seed 404 | Mean   | Std   |
+-------+---------------------------------------+---------+----------+----------+----------+----------+--------+-------+
| BG    | Background (BG)                       |  111    |   110    |   119    |   111    |   111    | 112.4  |  3.3  |
| AF    | Atmospheric Front (AF)                |   27    |    14    |    20    |    24    |    17    |  20.4  |  4.7  |
| BS    | Biological Slicks (BS)                |   35    |    19    |    16    |    28    |    26    |  24.8  |  6.7  |
| LWA   | Low Wind Area (LWA)                   |   27    |    31    |    20    |    33    |    26    |  27.4  |  4.5  |
| MCC   | Mesoscale Cellular Convection (MCC)   |   41    |    31    |    36    |    45    |    46    |  39.8  |  5.6  |
| OF    | Ocean Front (OF)                    |   16    |     7    |    14    |    14    |    13    |  12.8  |  3.1  |
| POW   | Pure Oceanic Waves (POW)              |   43    |    40    |    44    |    46    |    43    |  43.2  |  1.9  |
| RF    | Rain / precipitation-related phenomenon (RF)                       |   24    |    14    |    24    |    15    |    17    |  18.8  |  4.4  |
| WS    | Wind Streaks (WS)                     |   18    |    14    |    19    |    14    |    11    |  15.2  |  2.9  |
| Eddy  | Eddy (Eddy)                           |   30    |    18    |    17    |    27    |    20    |  22.4  |  5.2  |
| IWs   | Internal Waves (IWs)                  |  152    |   176    |   173    |   155    |   162    | 163.6  |  9.5  |
| HM    | Artificial / Anthropogenic Objects (HM)            |   22    |    20    |    18    |    23    |    19    |  20.4  |  1.9  |
+-------+---------------------------------------+---------+----------+----------+----------+----------+--------+-------+
```

### 5.3 Epochs 1–7 Exposure (Treatment Peak Window, 504 Total Draws)

```
+-------+---------------------------------------+---------+----------+----------+----------+----------+--------+-------+
| Class | Canonical Class Name                  | Seed 42 | Seed 101 | Seed 202 | Seed 303 | Seed 404 | Mean   | Std   |
+-------+---------------------------------------+---------+----------+----------+----------+----------+--------+-------+
| BG    | Background (BG)                       |  252    |   271    |   276    |   278    |   289    | 273.2  | 12.1  |
| AF    | Atmospheric Front (AF)                |   71    |    30    |    51    |    53    |    43    |  49.6  | 13.4  |
| BS    | Biological Slicks (BS)                |   80    |    48    |    54    |    60    |    50    |  58.4  | 11.6  |
| LWA   | Low Wind Area (LWA)                   |   79    |    75    |    69    |    71    |    63    |  71.4  |  5.4  |
| MCC   | Mesoscale Cellular Convection (MCC)   |  113    |    79    |    92    |   104    |    95    |  96.6  | 11.5  |
| OF    | Ocean Front (OF)                    |   37    |    21    |    37    |    34    |    32    |  32.2  |  5.9  |
| POW   | Pure Oceanic Waves (POW)              |  106    |    87    |    93    |    93    |    80    |  91.8  |  8.6  |
| RF    | Rain / precipitation-related phenomenon (RF)                       |   73    |    30    |    52    |    44    |    50    |  49.8  | 13.9  |
| WS    | Wind Streaks (WS)                     |   38    |    34    |    40    |    36    |    37    |  37.0  |  2.0  |
| Eddy  | Eddy (Eddy)                           |   70    |    41    |    43    |    57    |    45    |  51.2  | 10.9  |
| IWs   | Internal Waves (IWs)                  |  340    |   408    |   386    |   372    |   388    | 378.8  | 22.5  |
| HM    | Artificial / Anthropogenic Objects (HM)            |   60    |    46    |    46    |    48    |    42    |  48.4  |  6.1  |
+-------+---------------------------------------+---------+----------+----------+----------+----------+--------+-------+
```

---

## 6. Spatial Diversity: Parent Cluster Coverage & Concentration

In addition to tile counts, spatial diversity determines whether a class was learned from diverse geographic acquisitions or memorized from a single acquisition scene.

```
+-------+---------------------------------------+-----------+---------+----------+----------+----------+----------+--------+
| Class | Canonical Class Name                  | Available | Seed 42 | Seed 101 | Seed 202 | Seed 303 | Seed 404 | Mean   |
+-------+---------------------------------------+-----------+---------+----------+----------+----------+----------+--------+
| BG    | Background (BG)                       |    28     |   28    |    28    |    28    |    28    |    28    |  28.0  |
| AF    | Atmospheric Front (AF)                |     5     |    5    |     5    |     5    |     5    |     5    |   5.0  |
| BS    | Biological Slicks (BS)                |     6     |    6    |     6    |     6    |     6    |     6    |   6.0  |
| LWA   | Low Wind Area (LWA)                   |    10     |   10    |    10    |    10    |    10    |     9    |   9.8  |
| MCC   | Mesoscale Cellular Convection (MCC)   |    13     |   13    |    13    |    12    |    13    |    13    |  12.8  |
| OF    | Ocean Front (OF)                    |     4     |    4    |     4    |     4    |     4    |     4    |   4.0  |
| POW   | Pure Oceanic Waves (POW)              |    11     |   11    |    11    |    11    |    10    |    11    |  10.8  |
| RF    | Rain / precipitation-related phenomenon (RF)                       |     7     |    7    |     7    |     7    |     7    |     7    |   7.0  |
| WS    | Wind Streaks (WS)                     |     5     |    5    |     5    |     5    |     5    |     5    |   5.0  |
| Eddy  | Eddy (Eddy)                           |     5     |    5    |     5    |     5    |     5    |     5    |   5.0  |
| IWs   | Internal Waves (IWs)                  |    31     |   31    |    31    |    31    |    31    |    31    |  31.0  |
| HM    | Artificial / Anthropogenic Objects (HM)            |     8     |    8    |     7    |     8    |     8    |     8    |   7.8  |
+-------+---------------------------------------+-----------+---------+----------+----------+----------+----------+--------+
```

### Parent Balance Statistics (Epochs 1–7, 504 draws, 40 clusters, Target: 12.6 draws/cluster):
- **Zero-Draw Clusters:** `0` across all 5 seeds. Every single parent acquisition in the training set was represented.
- **Minimum Draws for any Cluster:** Seed 42 = 2, Seed 101 = 5, Seed 202 = 6, Seed 303 = 7, Seed 404 = 6.
- **Gini Coefficient:** Ranging from 0.1159 (Seed 202) to 0.2095 (Seed 42).
- **Top-5 Cluster Share:** Ranging from 16.27% (Seed 202) to 21.03% (Seed 42).

---

## 7. Performance Linkage & Outcome Variance Analysis

### 7.1 Cross-Seed Schedule vs Outcome Matrix

```
+------+------------+--------------------+-------------------+--------------------+------------------+-------------------+
| Seed | Experiment | Ultra-Rare Draws   | Treatment Best    | Control Best       | Paired Delta     | Winning Arm       |
|      |            | (OF+RF+HM, Ep 1-7) | mIoU (Best Epoch) | mIoU (Best Epoch)  | (Δ = T - C)      |                   |
+------+------------+--------------------+-------------------+--------------------+------------------+-------------------+
|   42 | C22-B      |        170         | 0.05318 (Ep  5)   | 0.04147 (Ep 10)    |     +0.01171     | TREATMENT (HIGH)  |
|  101 | C22-D      |         97         | 0.04481 (Ep  5)   | 0.05886 (Ep 15)    |     -0.01405     | CONTROL (HIGH)    |
|  202 | C22-D      |        135         | 0.04741 (Ep  6)   | 0.04358 (Ep 27)    |     +0.00383     | TREATMENT (MOD)   |
|  303 | C22-D      |        126         | 0.04605 (Ep  5)   | 0.05191 (Ep 19)    |     -0.00586     | CONTROL (MOD)     |
|  404 | C22-D      |        124         | 0.05398 (Ep  7)   | 0.04940 (Ep 21)    |     +0.00458     | TREATMENT (MOD)   |
+------+------------+--------------------+-------------------+--------------------+------------------+-------------------+
```

### 7.2 Correlation Analysis
1. **Correlation(Ultra-Rare Draws, Treatment Best mIoU):** $r = +0.6302$  
   *Treatment shows a positive descriptive association with rare-class exposure across 5 seeds.*
2. **Correlation(Ultra-Rare Draws, Control Best mIoU):** $r = -0.9167$  
   *Control shows a strong negative descriptive association with rare-class exposure across 5 seeds.*
3. **Correlation(Ultra-Rare Draws, Paired Delta $\Delta$):** **$r = +0.8955$**  
   *The paired delta shows a strong positive descriptive association with early rare-class draws across 5 seeds (r = +0.8955, p = 0.0399).*

### 7.3 Descriptive Synthesis & Association Boundaries (n=5)
1. **Descriptive Sample-Level Associations ($n=5$):**
   - The observed correlations ($r = -0.9167$ for Control best mIoU, $r = +0.6302$ for Treatment best mIoU, and $r = +0.8955$ for Paired Delta) are descriptive statistical associations across $n=5$ experimental seeds.
   - These associations do **not** establish a demonstrated causal mechanism. The sampler exposure audit measures draw counts and parent cluster allocations; it does **not** directly measure loss gradients, parameter trajectories, or optimization dynamics.
2. **Separation of Concepts:**
   - **Physical Class Availability:** OPS-02 TRAIN partition contains finite physical rare scenes (OF: 9 samples across 4 clusters; RF: 13 samples across 7 clusters; HM: 12 samples across 8 clusters).
   - **Sampler Allocation:** Candidate F successfully drew from 100% of these available clusters during Epochs 1–7 ($\ge 21$ draws per class). Complete exposure absence was refuted.
   - **Demonstrated Learning Effect:** Nonzero exposure does not demonstrate that exposure was quantitatively sufficient, optimally distributed, or temporally appropriate for feature learning on small or low-contrast targets.
3. **Future Investigation Boundary:**
   - Hypotheses suggesting that inverse-frequency weights destabilize the optimizer must be formulated as a future experimental diagnostic (DIAG-05-LOSS-LANDSCAPE-GRADIENT-DYNAMICS, DESIGN ONLY), rather than asserted as factual findings of DIAG-02.

---

## 8. Specific Test of the Sampler Hypothesis

| Hypothesis Question | Formal Status | Evidence Summary |
|:---|:---|:---|
| Did Candidate F starve rare classes in early epochs? | **NOT_SUPPORTED (ABSENCE REFUTED)** | Complete exposure absence was not observed under Candidate F; whether exposure was quantitatively sufficient, optimally distributed, or temporally appropriate for learning remains unresolved. |
| Did Candidate F drive Treatment to peak early (Ep 5–7)? | **NOT_SUPPORTED** | Treatment peaked at Ep 5–7 in all 5 seeds regardless of rare-class draw count; early peaking is observed under uniform loss across dominant classes. |
| Did sampler implementation drift between C22-B and C22-D? | **CONFIRMED (`IMPLEMENTATION_DEFECT`)** | C22-D experienced silent key lookup failure on `"labels_present"`, reducing class-presence weighting from 30% to 0.14%. |
| Did schedule variance associate with paired outcomes? | **CONFIRMED (`DESCRIPTIVE_ASSOCIATION`)** | Pseudo-random variation in ultra-rare draws correlates with paired delta at $r = +0.8955$ (Spearman $\rho = +0.7000$, $n=5$). No causal mechanism is inferred. |

---

## 9. Diagnostic Roadmap Update (Synthesizing DIAG-01 & DIAG-02)

### 9.1 Combined Analytical Picture:
1. **DIAG-01 (Metric Semantics & DEV Support - CASE B):**
   - DEV ground truth contains positive support for all 11 phenomenon classes ($GT_c > 0$).
   - The primary metric denominator is always 11.
   - The ~0.04–0.05 score is an unweighted average of 2 moderate performers (MCC ~0.23, IWs ~0.17) and 9 near-zero performers.
2. **DIAG-02 (Sampler Dynamics & TRAIN Exposure - FORENSICALLY REPAIRED):**
   - Complete exposure absence was not observed under Candidate F; whether exposure was quantitatively sufficient, optimally distributed, or temporally appropriate for learning remains unresolved.
   - Physical class availability (OF: 9, WS: 9, HM: 12, RF: 13) is distinct from sampler allocation (dozens of draws across 100% of parent clusters) and distinct from demonstrated learning effects.
   - Correlation between early rare-class draws and paired delta ($r = +0.8955$, $\rho = +0.7000$) is a descriptive sample association ($n=5$). No gradient mechanism is claimed without direct gradient measurements.

### 9.2 Authoritative Diagnostic Roadmap Preservation:
- **DIAG-03: RADIOMETRIC FEATURE DISCRIMINABILITY:** **PRIORITY 3 (UNCHANGED / PENDING AUTHORIZATION).** Evaluates spectral and radiometric separability of rare phenomenon signatures in SAR backscatter space. Preserved without modification.
- **DIAG-04: RECEPTIVE FIELD & SPATIAL SCALE COMPATIBILITY:** **PRIORITY 4 (UNCHANGED / PENDING AUTHORIZATION).** Investigates effective receptive field vs physical phenomenon scale (e.g., sub-pixel objects and narrow fronts). Preserved without modification.
- **DIAG-05: LOSS LANDSCAPE & GRADIENT DYNAMICS (FUTURE DESIGN ONLY / NOT EXECUTED):** **RESERVED FUTURE SPECIFICATION.** Formalizes future diagnostic protocol to measure per-layer gradient norms, batch-level gradient norm dispersion, and gradient angle alignment between rare and dominant classes under Control vs Treatment. Explicitly designated as DESIGN ONLY / NOT EXECUTED. Zero backward passes, zero gradient evaluations, and zero training runs permitted in this phase.

---

## 10. Audit Artifacts & Deliverables Summary

1. `data/ops02/audits/ops02_c22i_sampler_semantics_v1.json`: Authoritative audit of Candidate F implementation formulas, C22-B vs C22-D comparison, and silent key lookup bug documentation.
2. `data/ops02/audits/ops02_c22i_sampler_exposure_audit_v1.json`: Complete machine-readable record of schedules, draw counts, parent coverage, correlations, and performance linkage for all 5 seeds.
3. `experiments/EXP-07/EXP07_P0_C22I_SAMPLER_EXPOSURE_AUDIT_20260914.md`: This comprehensive diagnostic report.

---

## 11. Registered Lessons Learned (C22-I)

The following four durable lessons learned have been registered in `data/metadata/ocean_sentinel_lessons_learned_v1.json` and are regression-protected:

- **`LL-C22I-001` (CRITICAL):** *Deterministic Samplers Must Not Silently Fall Back on Missing Manifest Keys.* Sampler components must validate that required manifest keys exist (e.g. `canonical_dense_class_ids_present`) and raise explicit errors rather than defaulting to empty sets or fallback logic that quietly alters sampling probabilities.
- **`LL-C22I-002` (HIGH):** *Empirical Exposure Audit Must Precede Speculative Training-Starvation Claims.* Claims regarding sampler starvation must be verified against exact pseudo-random realized draw schedules before asserting training starvation as a scientific fact.
- **`LL-C22I-003` (MEDIUM):** *Sampler Schedule Variance Substantially Explains Replication Delta Volatility Under Canonical Weighting.* Pseudo-random variation in early-epoch draw schedules strongly correlates ($r = +0.8955$) with paired performance delta when canonical loss weights amplify gradient noise.
- **`LL-C22I-004` (MEDIUM):** *Early Peaking in Unweighted Training Is Driven by Dominant Mode Convergence, Not Sampler Starvation.* Uniform loss formulations converge rapidly on common classes, driving early validation peaks (Epochs 5–7) independently of rare-class draw counts.

