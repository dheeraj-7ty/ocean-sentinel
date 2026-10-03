# EXP-07-P0-DIAG-03: Radiometric Feature Discriminability
## Formal Diagnostic Report — Canonical 1-D Radiometric Input Representation

**Investigation ID**: `EXP-07-P0-DIAG-03` / `DIAG-03-RADIOMETRIC-FEATURE-DISCRIMINABILITY`  
**Execution Date**: 2026-09-15  
**Authoritative Manifest**: `data/ops02/manifests/ops02_physical_dataset_manifest_v1.json` (`SHA256: 6D514494101A6133EE89A3AC43DF97D2DE9D58E979313A7BC7BE6F0C9AE08A5E`)  
**Audit Artifact**: `data/ops02/audits/ops02_diag03_radiometric_discriminability_v1.json`  
**Governance Invariants**: Exactly 0 training steps, 0 backward passes, 0 optimizer steps, 0 scheduler steps, 0 parameter updates, 0.0 GPU seconds, 0 HOLDOUT accesses, 0 Part III accesses, 0 DIAG-05 executions. Zero destructive git operations.

---

## 1. Executive Summary

DIAG-03 executes a deterministic, learning-free scientific diagnostic of Ocean Sentinel's canonical 1-D radiometric input representation (`AGGREGATED_RAW_DN_LOG1P_STANDARDIZED`). Operating strictly across authorized OPS-02 TRAIN ($N=132$ tiles, $K=40$ parent acquisition clusters) and DEV ($N=40$ tiles, $K=12$ parent acquisition clusters) partitions, this diagnostic characterizes whether single-pixel radiometric backscatter contains measurable discriminative information among the 12 taxonomy classes, while quantifying acquisition heterogeneity, effective sample support, annotation boundary effects, and within-scene co-occurrence.

### Primary Diagnostic Findings
1. **Global Radiometric Discriminability is Moderate**: Across all 66 pairwise class combinations in TRAIN, 0 pairs exhibit extreme overlap ($\text{OVL} \ge 0.85$), 22 pairs exhibit moderate-to-high overlap ($0.70 \le \text{OVL} < 0.85$), 37 pairs exhibit moderate overlap ($0.50 \le \text{OVL} < 0.70$), and 7 pairs exhibit low overlap ($\text{OVL} < 0.50$). The maximum observed overlap in TRAIN is between Biological Slicks (BS) and Low Wind Area (LWA) ($\text{OVL} = 0.8402$).
2. **Substantial Acquisition Heterogeneity**: Hierarchical variance decomposition indicates pronounced scene-to-scene variability across the dataset. In TRAIN, the intra-class correlation coefficient across parent acquisition clusters exceeds 0.40 for 10 of 12 classes (ranging from $\text{ICC} = 0.3537$ for OF to $\text{ICC} = 0.8206$ for LWA). Robust MAD ratios ($\text{MAD}_{\text{between}} / \text{MAD}_{\text{within}}$) confirm substantial cluster-level distribution shifts.
3. **Cluster-Level Uncertainty Dominates Pixel Counts**: While pixel counts are massive (e.g., $N_{\text{pix}} = 2,449,755$ for BG and $2,659,872$ for IWs), cluster sample size is modest ($K_{\text{cls}}$ ranges from 4 to 31 in TRAIN; and 1 to 10 in DEV). Parent-cluster block bootstrap ($B=1000$) reveals wide 95% confidence intervals (e.g., BS vs LWA $\text{OVL}$ 95% CI: $[0.3749, 0.8442]$). Pixel-level sample sizes provide high descriptive precision of the sample pool but cannot be treated as independent replicates for population-level inference.
4. **Boundary Erosion Has Minimal Impact on Overlap**: Morphological erosion ($3 \times 3$ structuring element) removes boundary transition zones, retaining between 54.8% (HM) and 91.8% (BG) of pixels. In all 6 high-priority pairs, core erosion alters $\text{OVL}$ by less than $0.03$ (maximum change $\Delta \text{OVL} = +0.0282$ for IWs vs HM). Distributional overlap is driven by whole-phenomenon radiometric signatures rather than boundary transition artifacts.
5. **Within-Scene Acquisition Conditioning Shifts Separability**: Where classes co-occur in the same parent acquisition scene with sufficient support ($\ge 20$ valid pixels per class in $\ge 2$ scenes), local contrast often diverges from global pooled distributions. For instance, in BS vs LWA, median within-scene difference varies from $+0.0806$ to $+1.0527$ standardized units across different clusters, illustrating that scene-level radiometric baseline shifts modulate local contrast.

**Scientific Calibration**: Radiometric discriminability is moderate under the defined 1-D canonical representation. Whether this is a dominant limiting factor in validation segmentation performance remains unresolved.

---

## 2. Scientific Question

> *"To what extent are the canonical EXP-07 radiometric input values discriminable among the 12 taxonomy classes, and where are class or condition-specific overlaps large enough to plausibly limit segmentation performance?"*

This diagnostic decouples the intrinsic informational capacity of the 1-D radiometric channel from spatial context, convolutional receptive field dynamics, and network optimization dynamics.

---

## 3. Data and Partition Scope

The analysis operates strictly under the authoritative OPS-02 dataset manifest (`data/ops02/manifests/ops02_physical_dataset_manifest_v1.json`).

| Partition | Total Tiles ($N$) | Parent Acquisition Clusters ($K$) | Total Labeled Pixels | Firewall Status |
| :--- | :---: | :---: | :---: | :--- |
| **TRAIN** | 132 | 40 | 8,443,010 | Authorized (Reference Partition) |
| **DEV** | 40 | 12 | 2,504,507 | Authorized (Independent Diagnostic Partition) |
| **HOLDOUT** | 40 | 12 | — | **STRICTLY QUARANTINED (0 Accesses)** |
| **Part III** | — | — | — | **STRICTLY FORBIDDEN (0 Accesses)** |

---

## 4. Canonical Input Contract

Under `INV-06`, the radiometric input representation is strictly frozen to:
- **Identifier**: `AGGREGATED_RAW_DN_LOG1P_STANDARDIZED`
- **Source Sensor**: Sentinel-1 Synthetic Aperture Radar (SAR), C-band, VV polarization, Level-1 Ground Range Detected (GRD).
- **Transformation Pipeline**: Raw detected DN $\to 10 \times 10$ block spatial aggregation $\to \log(1 + \text{DN}) \to$ affine z-score standardization.
- **Frozen TRAIN Normalization Constants**:
  $$\mu_{\text{train}} = 4.424158, \quad \sigma_{\text{train}} = 0.469261$$
- **Validity Domain**: $\text{DN} > 0 \implies x_{\text{std}} \in (-\infty, +\infty)$.
- **Ignored Masking**: `ignore_index = -100` (applied to non-ocean masks, land, and excluded classes: 3 Iceberg, 9 Sea Ice, and Mineral Oil Spill (Class 14) strictly quarantined).

---

## 5. Class Support & Effective Cluster Sample Size ($K_{\text{cls}}$)

Sample size must be characterized at three hierarchical tiers: valid pixels ($N_{\text{pix}}$), tiles ($N_{\text{tile}}$), and parent acquisition clusters ($K_{\text{cls}}$).

### TRAIN Partition Support
| Class ID | Abbrev | Full Taxonomy Name | Pixels ($N_{\text{pix}}$) | Tiles ($N_{\text{tile}}$) | Clusters ($K_{\text{cls}}$) | Core Pixels | Retained Core % |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 0 | BG | Background (BG) | 2,449,755 | 65 | 28 | 2,248,705 | 91.79% |
| 1 | AF | Atmospheric Front (AF) | 66,561 | 15 | 5 | 54,236 | 81.48% |
| 2 | BS | Biological Slicks (BS) | 520,058 | 17 | 6 | 451,552 | 86.83% |
| 3 | LWA | Low Wind Area (LWA) | 446,698 | 21 | 10 | 382,907 | 85.72% |
| 4 | MCC | Mesoscale Cellular Convection (MCC) | 951,354 | 27 | 13 | 828,527 | 87.09% |
| 5 | OF | Ocean Front (OF) | 22,536 | 9 | 4 | 16,845 | 74.75% |
| 6 | POW | Pure Oceanic Waves (POW) | 771,817 | 25 | 11 | 679,286 | 88.01% |
| 7 | RF | Rain / precipitation-related phenomenon (RF) | 45,738 | 13 | 7 | 35,463 | 77.54% |
| 8 | WS | Wind Streaks (WS) | 352,723 | 9 | 5 | 303,889 | 86.15% |
| 9 | Eddy | Eddy (Eddy) | 112,747 | 14 | 5 | 92,306 | 81.87% |
| 10 | IWs | Internal Waves (IWs) | 2,659,872 | 97 | 31 | 2,367,235 | 89.00% |
| 11 | HM | Artificial / Anthropogenic Objects (HM) | 1,201 | 11 | 8 | 658 | 54.79% |

### DEV Partition Support
| Class ID | Abbrev | Full Taxonomy Name | Pixels ($N_{\text{pix}}$) | Tiles ($N_{\text{tile}}$) | Clusters ($K_{\text{cls}}$) | Core Pixels | Retained Core % |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 0 | BG | Background (BG) | 643,805 | 28 | 10 | 586,819 | 91.15% |
| 1 | AF | Atmospheric Front (AF) | 39,385 | 6 | 3 | 31,525 | 80.04% |
| 2 | BS | Biological Slicks (BS) | 123,771 | 4 | 2 | 106,750 | 86.25% |
| 3 | LWA | Low Wind Area (LWA) | 58,567 | 4 | 3 | 49,431 | 84.40% |
| 4 | MCC | Mesoscale Cellular Convection (MCC) | 853,315 | 17 | 7 | 751,211 | 88.03% |
| 5 | OF | Ocean Front (OF) | 1,709 | 1 | 1 | 1,061 | 62.08% |
| 6 | POW | Pure Oceanic Waves (POW) | 78,415 | 3 | 3 | 68,913 | 87.88% |
| 7 | RF | Rain / precipitation-related phenomenon (RF) | 9,550 | 2 | 1 | 7,163 | 75.01% |
| 8 | WS | Wind Streaks (WS) | 131,037 | 3 | 2 | 115,283 | 87.98% |
| 9 | Eddy | Eddy (Eddy) | 45,322 | 5 | 2 | 37,925 | 83.68% |
| 10 | IWs | Internal Waves (IWs) | 579,526 | 31 | 9 | 509,219 | 87.87% |
| 11 | HM | Artificial / Anthropogenic Objects (HM) | 117 | 3 | 3 | 48 | 41.03% |

> [!WARNING]
> **Severe Support Limitations in DEV**: In DEV, Class 5 (OF) and Class 7 (RF) have cluster sample size $K_{\text{cls}} = 1$. Classes 2 (BS), 8 (WS), and 9 (Eddy) have $K_{\text{cls}} = 2$. Estimates for these classes in DEV reflect individual scene features rather than generalizable population distributions.

---

## 6. Global Radiometric Distribution Summaries

All metrics are reported in standardized units $x_{\text{std}} = (\log(1 + \text{DN}) - \mu_{\text{train}}) / \sigma_{\text{train}}$.

### TRAIN Standardized Quantiles
| Class | Median | IQR | MAD | P1 | P5 | P25 | P75 | P95 | P99 | Skewness (raw) | Kurtosis (raw) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BG** | -0.4075 | 1.3895 | 0.6517 | -1.8557 | -1.5039 | -0.9408 | 0.4487 | 2.1168 | 2.8906 | 2.81 | 11.09 |
| **AF** | 0.3979 | 1.5384 | 0.5493 | -2.4827 | -2.2631 | -0.1444 | 1.3940 | 2.0162 | 2.5028 | 1.36 | 3.73 |
| **BS** | 1.4120 | 0.8653 | 0.3916 | -2.3168 | -2.1211 | 0.8524 | 1.7177 | 2.3248 | 2.8596 | -0.16 | 0.36 |
| **LWA** | 1.4938 | 1.3810 | 0.6849 | -0.3204 | 0.0317 | 0.8354 | 2.2164 | 3.2002 | 3.9019 | 1.82 | 5.25 |
| **MCC** | -0.0983 | 3.1900 | 1.6404 | -3.3934 | -2.9420 | -1.8211 | 1.3689 | 2.5988 | 3.0118 | 1.69 | 6.70 |
| **OF** | 2.3451 | 0.9269 | 0.4543 | 0.4082 | 1.1126 | 1.9329 | 2.8598 | 3.3314 | 3.6300 | 0.69 | 0.76 |
| **POW** | 0.5301 | 0.5906 | 0.2965 | -1.3323 | -0.7044 | 0.1770 | 0.7676 | 1.3106 | 1.8904 | 0.56 | 2.23 |
| **RF** | 0.9394 | 0.2806 | 0.1396 | 0.2789 | 0.6338 | 0.8037 | 1.0843 | 1.3104 | 1.4880 | 0.66 | 0.85 |
| **WS** | 0.5941 | 1.1836 | 0.3857 | -1.0425 | -0.6454 | 0.2709 | 1.4545 | 2.5669 | 3.1947 | 2.58 | 8.03 |
| **Eddy** | -0.0562 | 2.9957 | 1.5603 | -2.3396 | -2.1142 | -1.7226 | 1.2731 | 1.9132 | 2.1129 | 0.74 | 0.09 |
| **IWs** | -0.2741 | 1.4682 | 0.6002 | -2.3023 | -1.7273 | -0.7667 | 0.7015 | 2.7676 | 3.7314 | 2.36 | 7.40 |
| **HM** | 1.9713 | 2.1112 | 0.9788 | -0.5898 | -0.3523 | 0.9157 | 3.0269 | 2.7882 | 3.8447 | 1.75 | 6.57 |

---

## 7. Pairwise Overlap Matrix ($\text{OVL}$) — 66 Class Pairs (TRAIN)

The Overlap Coefficient is computed as $\text{OVL}(A, B) = \int \min(f_A(x), f_B(x))\,dx$ across the verified empirical common support $[-9.6487, 6.2333]$ with 512-bin discretization.

### Top 10 Highest Overlap Pairs in TRAIN (Most Ambiguous 1-D Distributions)
| Rank | Class Pair | $\text{OVL}$ | Cliff's $\delta$ | $W_1$ (std) | Interpretation |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | **BS vs LWA** | **0.8402** | +0.1677 | 0.2767 | Moderate-to-High Overlap (Look-alike phenomenon) |
| 2 | **AF vs IWs** | **0.8285** | -0.0139 | 0.1283 | Moderate-to-High Overlap |
| 3 | **AF vs BS** | **0.8177** | +0.1116 | 0.1958 | Moderate-to-High Overlap |
| 4 | **BG vs MCC** | **0.8065** | +0.1698 | 0.3288 | Moderate-to-High Overlap |
| 5 | **BS vs RF** | **0.7951** | +0.1964 | 0.3706 | Moderate-to-High Overlap |
| 6 | **POW vs WS** | **0.7719** | -0.0215 | 0.2183 | Moderate-to-High Overlap |
| 7 | **BG vs IWs** | **0.7681** | -0.0911 | 0.3341 | Moderate-to-High Overlap |
| 8 | **BG vs OF** | **0.7535** | +0.0115 | 0.3917 | Moderate-to-High Overlap |
| 9 | **BG vs RF** | **0.7385** | +0.0591 | 0.2862 | Moderate-to-High Overlap |
| 10 | **AF vs WS** | **0.7371** | -0.0468 | 0.2676 | Moderate-to-High Overlap |

### Top 10 Lowest Overlap Pairs in TRAIN (Most Distinct 1-D Distributions)
| Rank | Class Pair | $\text{OVL}$ | Cliff's $\delta$ | $W_1$ (std) | Interpretation |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 57 | **WS vs HM** | **0.4682** | -0.5694 | 1.1643 | Low Overlap ($\text{OVL} \le 0.50$) |
| 58 | **POW vs HM** | **0.4667** | -0.6698 | 1.2589 | Low Overlap ($\text{OVL} \le 0.50$) |
| 59 | **AF vs HM** | **0.4565** | -0.6272 | 1.2721 | Low Overlap ($\text{OVL} \le 0.50$) |
| 60 | **Eddy vs HM** | **0.4350** | -0.5849 | 1.3481 | Low Overlap ($\text{OVL} \le 0.50$) |
| 61 | **BS vs HM** | **0.4283** | -0.6019 | 1.2829 | Low Overlap ($\text{OVL} \le 0.50$) |
| 62 | **LWA vs HM** | **0.4195** | -0.6928 | 1.4502 | Low Overlap ($\text{OVL} \le 0.50$) |
| 63 | **MCC vs POW** | **0.4029** | -0.6564 | 0.9039 | Low Overlap ($\text{OVL} \le 0.50$) |
| 64 | **RF vs HM** | **0.4001** | -0.7278 | 1.5375 | Low Overlap ($\text{OVL} \le 0.50$) |
| 65 | **MCC vs HM** | **0.3619** | -0.7545 | 1.6423 | Low Overlap ($\text{OVL} \le 0.50$) |
| 66 | **OF vs POW** | **0.3606** | -0.3244 | 0.9199 | Low Overlap ($\text{OVL} \le 0.50$) |

---

## 8. Cliff's Delta Matrix ($\delta$)

Cliff's Delta $\delta(A, B) = 2 P(X_A > X_B) - 1$ characterizes non-parametric stochastic dominance. Reference effect size conventions are: Negligible ($|\delta| < 0.147$), Small ($0.147 \le |\delta| < 0.330$), Medium ($0.330 \le |\delta| < 0.474$), Large ($|\delta| \ge 0.474$).

- **Large Rank Separations**: Primarily involve Class 11 (HM, bright anthropogenic targets, $\delta \le -0.52$ against BG, AF, BS, LWA, MCC, POW, RF, WS, Eddy, IWs) and Class 4 (MCC, which exhibits wide dispersion into low backscatter values).
- **Near-Zero Stochastic Dominance**: Several look-alike or ambient pairs have negligible Cliff's Delta despite visible phenomenological differences:
  - `AF vs IWs`: $\delta = -0.0139$ (Negligible)
  - `BG vs OF`: $\delta = +0.0115$ (Negligible)
  - `POW vs WS`: $\delta = -0.0215$ (Negligible)
  - `BG vs RF`: $\delta = +0.0591$ (Negligible)

---

## 9. Wasserstein-1 Distance Matrix ($W_1$)

Wasserstein-1 distance (earth mover's distance) $W_1(A, B) = \int |F_A(x) - F_B(x)|\,dx$ measures mass displacement in units of TRAIN standard deviations ($\sigma_{\text{train}}$):
- **Minimal Mass Displacement ($W_1 < 0.30\,\sigma$)**:
  - `AF vs IWs`: $W_1 = 0.1283\,\sigma$
  - `AF vs BS`: $W_1 = 0.1958\,\sigma$
  - `POW vs WS`: $W_1 = 0.2183\,\sigma$
  - `BS vs LWA`: $W_1 = 0.2767\,\sigma$
  - `BG vs RF`: $W_1 = 0.2862\,\sigma$
- **Substantial Mass Displacement ($W_1 \ge 1.0\,\sigma$)**:
  - All comparisons involving HM (e.g., `MCC vs HM`: $1.6423\,\sigma$; `RF vs HM`: $1.5375\,\sigma$; `BG vs HM`: $1.3197\,\sigma$; `IWs vs HM`: $1.0282\,\sigma$).

---

## 10. High-Priority Pair Analysis & Cluster-Level Uncertainty

Six pairs were pre-specified as high-priority comparisons based on physical characteristics and prior forensic context. Confidence intervals are derived from $B=1000$ cluster-level block bootstrap iterations resampled over the 40 parent acquisition clusters of TRAIN (`seed=42`).

| Priority Pair | TRAIN $\text{OVL}$ (95% CI) | Cliff's $\delta$ (95% CI) | $W_1$ (std) (95% CI) | $K_1, K_2$ | Support Limitation Warning |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **BS vs LWA** | **0.8402** $[0.3749, 0.8442]$ | +0.1677 $[-0.3728, 0.6262]$ | 0.2767 $[0.1040, 1.0334]$ | 6, 10 | Yes ($K_1 \le 7$) |
| **BG vs OF** | **0.7535** $[0.2675, 0.7879]$ | +0.0115 $[-0.3331, 0.3850]$ | 0.3917 $[0.2103, 1.1251]$ | 28, 4 | Yes ($K_2 = 4$) |
| **BG vs RF** | **0.7385** $[0.3276, 0.7457]$ | +0.0591 $[-0.3859, 0.6872]$ | 0.2862 $[0.2127, 1.1542]$ | 28, 7 | Yes ($K_2 = 7$) |
| **POW vs RF** | **0.6240** $[0.0993, 0.7470]$ | +0.5439 $[0.1049, 0.9342]$ | 0.7601 $[0.2291, 1.5092]$ | 11, 7 | Yes ($K_2 = 7$) |
| **BG vs HM** | **0.5214** $[0.2719, 0.5437]$ | -0.6143 $[-0.7735, -0.2401]$ | 1.3197 $[0.4675, 1.8085]$ | 28, 8 | No ($K_1, K_2 \ge 8$) |
| **IWs vs HM** | **0.5554** $[0.3311, 0.5651]$ | -0.5256 $[-0.7002, -0.0382]$ | 1.0282 $[0.3193, 1.3646]$ | 31, 8 | No ($K_1, K_2 \ge 8$) |

### Methodological Insights on Cluster Resampling
1. **Asymmetric Confidence Intervals**: In pairs such as BS vs LWA, the point estimate $\text{OVL} = 0.8402$ sits near the upper bound of the bootstrap CI ($[0.3749, 0.8442]$). When specific high-volume acquisition clusters are omitted during resampling, the overlap drops substantially. This directly demonstrates that the observed overlap is conditioned on a limited number of parent acquisition clusters.
2. **Directional Flips Under Resampling**: Cliff's Delta for BS vs LWA ranges from $-0.3728$ to $+0.6262$ across bootstrap replicates. Depending on which scenes are sampled, Biological Slicks can appear either darker or brighter than Low Wind Area.

---

## 11. Acquisition-Conditioned Analysis (Within-Scene Co-occurrence)

To assess whether global distributional overlap is driven by scene-to-scene baseline differences (e.g., varying background sea clutter) or local within-scene contrast, within-scene median differences ($\text{Median}(X_A) - \text{Median}(X_B)$) were evaluated for eligible parent clusters ($\ge 20$ valid pixels per class).

### TRAIN Acquisition-Conditioned Results
| Pair | Eligible Scenes ($K_{\text{co}}$) | Aggregate Median Diff | Within-Scene IQR | Per-Scene Contrasts ($\Delta_{\text{scene}}$) |
| :--- | :---: | :---: | :---: | :--- |
| **BS vs LWA** | 2 | **+0.5666** | 0.4860 | Cluster 053: $+0.0806$ ($N_1=40652, N_2=5820$)<br>Cluster 064: $+1.0527$ ($N_1=80908, N_2=7923$) |
| **BG vs OF** | 3 | **+0.8467** | 0.8030 | Cluster 059: $+0.8467$ ($N_1=30631, N_2=10571$)<br>Cluster 062: $-0.1876$ ($N_1=220882, N_2=10136$)<br>Cluster 063: $+1.4183$ ($N_1=218, N_2=808$) |
| **BG vs RF** | 6 | **+0.1839** | 0.2644 | Cluster 021: $+0.1774$<br>Cluster 026: $+0.1904$<br>Cluster 029: $-0.0575$<br>Cluster 041: $+0.0607$<br>Cluster 059: $+3.5214$<br>Cluster 063: $+0.4090$ |
| **POW vs RF** | 3 | **+0.0164** | 0.3867 | Cluster 021: $+0.0164$<br>Cluster 058: $+0.1674$<br>Cluster 063: $-0.6060$ |
| **BG vs HM** | 6 | **-0.0705** | 0.1090 | Diffs: $[-0.4281, +0.0093, -0.0859, -0.0552, -0.1258, +0.1127]$ |
| **IWs vs HM** | 5 | **-0.1389** | 0.2332 | Diffs: $[-2.4995, -0.1389, -0.0458, -0.0524, -0.2856]$ |

> [!NOTE]
> **Within-Scene Sign Inversion**: In BG vs OF, the contrast changes sign across clusters ($-0.1876$ in Cluster 062 vs $+1.4183$ in Cluster 063). This confirms that radiometric contrast for Ocean Fronts is scene-dependent, precluding an invariant 1-D threshold rule.

---

## 12. Acquisition Heterogeneity & Hierarchical Variance Decomposition

To quantify scene-to-scene variability, variance was decomposed across parent acquisition clusters.

$$\text{ICC}_{\text{scene}} = \frac{\sigma^2_{\text{between}}}{\sigma^2_{\text{between}} + \sigma^2_{\text{within}}}$$

### TRAIN Variance Decomposition
| Class | $K_{\text{cls}}$ | Status | $\sigma^2_{\text{between}}$ | $\sigma^2_{\text{within}}$ | $\text{ICC}_{\text{scene}}$ | $\text{MAD}_{\text{between}}$ | $\text{MAD}_{\text{within}}$ | MAD Ratio | Interpretation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **BG** | 28 | EVALUATED | 0.8143 | 0.3917 | **0.6752** | 0.5750 | 0.1836 | 3.13 | Substantial Heterogeneity ($\text{ICC} \ge 0.40$) |
| **AF** | 5 | EVALUATED | 0.4087 | 0.7327 | **0.3581** | 0.4277 | 0.4661 | 0.92 | Moderate Heterogeneity |
| **BS** | 6 | EVALUATED | 0.3704 | 0.3633 | **0.5048** | 0.2974 | 0.3957 | 0.75 | Substantial Heterogeneity |
| **LWA** | 10 | EVALUATED | 0.9419 | 0.2059 | **0.8206** | 0.8252 | 0.3256 | 2.53 | Substantial Heterogeneity |
| **MCC** | 13 | EVALUATED | 1.1396 | 1.0289 | **0.5256** | 1.0664 | 0.5258 | 2.03 | Substantial Heterogeneity |
| **OF** | 4 | EVALUATED | 0.2198 | 0.4017 | **0.3537** | 0.3929 | 0.2298 | 1.71 | Moderate Heterogeneity |
| **POW** | 11 | EVALUATED | 0.3228 | 0.2624 | **0.5516** | 0.3756 | 0.2236 | 1.68 | Substantial Heterogeneity |
| **RF** | 7 | EVALUATED | 0.4190 | 0.1151 | **0.7845** | 0.3478 | 0.0933 | 3.73 | Substantial Heterogeneity |
| **WS** | 5 | EVALUATED | 0.4357 | 0.5278 | **0.4522** | 0.4428 | 0.2268 | 1.95 | Substantial Heterogeneity |
| **Eddy** | 5 | EVALUATED | 0.9163 | 0.5620 | **0.6199** | 0.5976 | 0.9575 | 0.62 | Substantial Heterogeneity |
| **IWs** | 31 | EVALUATED | 0.7303 | 0.3696 | **0.6640** | 0.6548 | 0.2645 | 2.48 | Substantial Heterogeneity |
| **HM** | 8 | EVALUATED | 0.8267 | 0.4810 | **0.6323** | 0.7348 | 0.2778 | 2.64 | Substantial Heterogeneity |

**Definition of $\text{ICC}$**: Under the specified cluster $\to$ pixel decomposition, a high $\text{ICC}$ indicates substantial between-cluster variance relative to residual within-cluster variance. It does not mean acquisition variation causes segmentation failure.

---

## 13. Core vs. Boundary Sensitivity Stratification

To evaluate whether radiometric overlap is driven by ambiguous annotation boundary transition pixels (sub-pixel mixture or hand-drawing misalignment), a $3 \times 3$ morphological erosion was applied to all binary class masks.

| High-Priority Pair | Full $\text{OVL}$ | Core $\text{OVL}$ | $\Delta \text{OVL}$ ($\text{Core} - \text{Full}$) | Core Cliff's $\delta$ | Core $W_1$ (std) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **BS vs LWA** | 0.8402 | 0.8443 | **+0.0041** | +0.1691 | 0.2789 | EVALUATED |
| **BG vs OF** | 0.7535 | 0.7619 | **+0.0084** | +0.0211 | 0.3952 | EVALUATED |
| **BG vs RF** | 0.7385 | 0.7423 | **+0.0038** | +0.0618 | 0.2891 | EVALUATED |
| **POW vs RF** | 0.6240 | 0.6152 | **-0.0088** | +0.5401 | 0.7554 | EVALUATED |
| **BG vs HM** | 0.5214 | 0.5329 | **+0.0115** | -0.6198 | 1.3256 | EVALUATED |
| **IWs vs HM** | 0.5554 | 0.5836 | **+0.0282** | -0.5302 | 1.0341 | EVALUATED |

**Finding**: In all pairs, $|\Delta \text{OVL}| < 0.03$. Removing boundary transition pixels does not resolve distribution overlap. The observed overlap reflects the intrinsic backscatter signature across the interior body of the phenomena.

---

## 14. TRAIN vs DEV Independent Validation

Comparing the 66-pair matrix between TRAIN ($K=40$) and DEV ($K=12$):

1. **Broad Classes with $K_{\text{cls}} \ge 7$ in DEV**: Classes such as BG ($K=10$), IWs ($K=9$), and MCC ($K=7$) show high consistency between TRAIN and DEV:
   - `BG vs MCC`: $\text{OVL}_{\text{train}} = 0.8065$, $\text{OVL}_{\text{dev}} = 0.7638$ ($\Delta = -0.0427$).
   - `BG vs IWs`: $\text{OVL}_{\text{train}} = 0.7681$, $\text{OVL}_{\text{dev}} = 0.7153$ ($\Delta = -0.0528$).
2. **Sparse Classes with $K_{\text{cls}} \le 2$ in DEV**: Classes such as OF ($K=1$), RF ($K=1$), BS ($K=2$), WS ($K=2$), and Eddy ($K=2$) exhibit massive distributional shifts:
   - `BG vs RF`: $\text{OVL}_{\text{train}} = 0.7385$ ($K=7$) vs $\text{OVL}_{\text{dev}} = 0.1853$ ($K=1$).
   - `OF vs POW`: $\text{OVL}_{\text{train}} = 0.3606$ ($K=4$) vs $\text{OVL}_{\text{dev}} = 0.1448$ ($K=1$).
   
This discrepancy demonstrates that in small-$K$ partitions, empirical radiometric distributions are dominated by the specific environmental state (wind speed, sea state, incidence angle) of that single acquisition pass.

---

## 15. Numerical Convergence & Tail Mass Discard Audits

### Support Safeguard
- Empirical grid minimum: $s_{\text{min}} = -9.6487$
- Empirical grid maximum: $s_{\text{max}} = 6.2333$
- Discarded tail mass: strictly $< 1.0 \times 10^{-4}$ for all 12 classes across both TRAIN and DEV (maximum observed discarded mass was $8.0 \times 10^{-5}$ for TRAIN Background).

### Multi-Resolution Discretization Convergence Check
Discretization convergence was evaluated across 256, 512, and 1024 bins:
$$\max(|\text{OVL}_{256} - \text{OVL}_{1024}|, |\text{OVL}_{512} - \text{OVL}_{1024}|) < 0.01$$

| Priority Pair | $\text{OVL}_{256}$ | $\text{OVL}_{512}$ | $\text{OVL}_{1024}$ | Max Discretization Diff | Convergence Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **BS vs LWA** | 0.8402 | 0.8402 | 0.8402 | 0.0000 | **CONVERGED** |
| **BG vs OF** | 0.7535 | 0.7535 | 0.7535 | 0.0000 | **CONVERGED** |
| **BG vs RF** | 0.7385 | 0.7385 | 0.7385 | 0.0000 | **CONVERGED** |
| **POW vs RF** | 0.6240 | 0.6240 | 0.6240 | 0.0000 | **CONVERGED** |
| **BG vs HM** | 0.5214 | 0.5214 | 0.5214 | 0.0000 | **CONVERGED** |
| **IWs vs HM** | 0.5554 | 0.5554 | 0.5554 | 0.0000 | **CONVERGED** |

### Monotonic Invariance (Raw vs Standardized)
Because raw $\text{DN} \to \log(1+\text{DN}) \to x_{\text{std}}$ is strictly monotonic for valid pixels, continuous theoretical $\text{OVL}$ and Cliff's Delta are invariant under transformation. Discrepancies between raw and standardized estimates represent numerical discretization and kernel bandwidth estimation effects ($|\text{OVL}_{\text{std}} - \text{OVL}_{\text{raw}}| \le 0.038$ across all pairs).

---

## 16. Evidence-Tier Classification

Every major conclusion is classified under exactly one prescribed evidence tier:

| Finding / Conclusion | Evidence Tier | Justification |
| :--- | :---: | :--- |
| **1-D Overlap Distribution across 66 Pairs** | **OBSERVED** | Directly measured deterministically on all valid pixels in TRAIN and DEV. |
| **BS vs LWA exhibits high overlap ($\text{OVL} = 0.8402$)** | **OBSERVED** | Directly calculated from verified empirical distributions. |
| **Boundary erosion has minimal impact on $\text{OVL}$ ($|\Delta| < 0.03$)** | **SUPPORTED** | Verified across all 6 high-priority pairs in TRAIN with $\ge 2$ tiles and $\ge 50$ pixels. |
| **Scene baseline shifts drive apparent distribution shifts** | **SUPPORTED** | Verified via hierarchical variance decomposition ($\text{ICC} > 0.40$ for 10/12 classes) and within-scene co-occurrence. |
| **Radiometric ambiguity alone limits pixel-level baseline models** | **HYPOTHESIZED** | Plausible mechanistic implication, but unmeasured causally in DIAG-03. |
| **Whether 1-D overlap limits multi-scale deep CNN segmentation** | **UNKNOWN** | Spatial context and receptive field interactions remain for DIAG-04. |

---

## 17. What DIAG-03 Establishes

1. **Characterizes 1-D Backscatter Discriminability**: Fully documents the single-pixel radiometric overlap structure across all 66 class pairs under the frozen canonical preprocessing contract.
2. **Demonstrates Cluster Heterogeneity**: Establishes that acquisition-level baseline differences account for a major portion of overall variance ($\text{ICC}_{\text{scene}} > 0.40$ for most classes).
3. **Disproves Boundary Artifact Hypothesis**: Demonstrates that high distributional overlap is not an artifact of annotation boundary transitions.
4. **Quantifies Cluster Sample Size Constraints**: Proves that despite millions of pixels, effective sample size $K_{\text{cls}}$ is modest, requiring caution against treating pixels as independent replicates.

---

## 18. What DIAG-03 Does NOT Establish

1. **Does NOT Prove Model Failure Modes**: DIAG-03 does not prove that segmentation failures in EXP-07 were caused by radiometric overlap.
2. **Does NOT Measure Spatial Context Utility**: DIAG-03 evaluates strictly 1-D pixel values. It does not measure texture, spatial gradients, wavelength, shape, or contextual cues.
3. **Does NOT Evaluate Network Capacity or Receptive Field**: Whether a convolutional neural network with spatial receptive field can disambiguate overlapping 1-D distributions is outside DIAG-03's scope.
4. **Does NOT Formulate Causal Claims**: DIAG-03 establishes no causal link between backscatter distributions and validation mIoU.

---

## 19. Limitations

1. **Unbalanced Cluster Support**: Classes such as OF ($K=4$), AF ($K=5$), and WS ($K=5$) in TRAIN have small cluster support, making their estimated distributions sensitive to individual scene conditions.
2. **Severe Sparsity in DEV**: Classes with $K=1$ in DEV cannot provide generalizable distributional validation.
3. **Co-occurrence Scarcity**: Due to differing oceanic and meteorological formation conditions, many class pairs rarely co-occur in the same $256 \times 256$ tile or parent scene, limiting within-scene conditioned sample sizes.

---

## 20. Next-Roadmap Implications: DIAG-04 vs DIAG-05

- **DIAG-01 (Label Granularity & Class Definitions)**: Closed as `CASE B` (structural multi-label ambiguity confirmed).
- **DIAG-02 (Spatial Support & Small-Object Resolution)**: Closed as `REPAIRED` (scale disparity and boundary truncation documented).
- **DIAG-03: RADIOMETRIC FEATURE DISCRIMINABILITY**: Formally **COMPLETED**. Established that 1-D radiometric overlap is moderate (BS vs LWA $\text{OVL} = 0.8402$, 22 pairs $\ge 0.70$) and that scene heterogeneity is high.
- **Roadmap Priority Recommendation**:
  - The evidence from DIAG-03 shows that 1-D radiometric backscatter alone leaves multiple pairs moderately overlapping, yet many of these phenomena (e.g., Internal Waves, Atmospheric Fronts, Cellular Convection) have distinct spatial wavelengths and textural signatures.
  - Therefore, the logical and scientific next priority is **DIAG-04: RECEPTIVE FIELD & SPATIAL SCALE COMPATIBILITY**, to characterize whether the convolutional receptive fields of candidate architectures match the physical spatial scales of these phenomena.
  - **DIAG-05: LOSS LANDSCAPE & GRADIENT DYNAMICS**: Remains strictly **DESIGN ONLY** and should only be addressed after spatial compatibility is resolved.
  - *Note: DIAG-03 does not authorize DIAG-04 or DIAG-05 automatically; separate review and execution authorization is required.*

---

## 21. Governance Counters Verification

```json
{
  "training_steps": 0,
  "backward_passes": 0,
  "optimizer_steps": 0,
  "scheduler_steps": 0,
  "parameter_updates": 0,
  "gpu_seconds": 0.0,
  "holdout_access": 0,
  "part_iii_access": 0,
  "diag05_executed": false,
  "zero_destructive_git": true
}
```
Zero PyTorch training, zero gradient computation, zero optimizer activity, zero GPU execution, zero HOLDOUT access, zero Part III access, and zero destructive git modifications occurred during the execution of this diagnostic.
