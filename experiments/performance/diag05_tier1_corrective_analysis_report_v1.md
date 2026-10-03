# DIAG-05 Tier-1 Corrective Analysis and Forensic Closure Report (v1)

**Investigation ID:** `DIAG-05-LOSS-LANDSCAPE-GRADIENT-DYNAMICS`  
**Task ID:** `DIAG05-TIER1-CORRECTIVE-CLOSURE-AND-GOVERNANCE-HARDENING`  
**Execution Reference:** `EXP-07-P0-DIAG-05-TIER1-STATIC-GRADIENT-PROFILING`  
**Corrective Protocol Version:** `v1.9.0-hardened-corrective`  
**Evaluation Mode:** Analysis-Only Corrective Forensic Audit (Zero Scientific Re-execution, Zero Backward Passes)  
**Date:** 2026-09-17  

---

## 1. Executive Summary and Purpose of Corrective Pass

This corrective pass was executed to address technical debt and scientific discrepancies identified during the post-execution forensic review of DIAG-05 Tier-1:
1. **Population Construction Defect (F-DIAG05-001):** Evaluating sample support thresholds ($M_c \ge K$) on raw mask files on disk prior to applying SAR validity masking admitted one false-positive tile (`...-001-22`), which had zero valid rare support after sensor border exclusion.
2. **Statistical Method Provenance Mismatch (F-DIAG05-002):** The executed Wilcoxon signed-rank test in v1 computed an exact permutation p-value ($p = 0.1514$) while artifact metadata described asymptotic inference ($p = 0.1475$).
3. **Epistemic Over-Claiming:** Initial documentation over-generalized opposing gradient alignment as an inherent architecture-level feature across domains and risked conflating Step-0 non-significance with proof of "zero effect" or dynamic training stability.

This corrective analysis resolves all three issues without mutating the original immutable Tier-1 machine artifacts, establishing complete data provenance and hardening repository governance.

---

## 2. Status of Original v1 Artifacts

Per Governing Rule 0.8 and Rule 2, the original 7 Tier-1 scientific machine artifacts represent what was actually executed and remain **strictly immutable**:

| Artifact Filename | Size (Bytes) | Cryptographic SHA-256 Hash | Mutated? |
|---|---|---|---|
| `diag05_tier1_run_manifest_v1.json` | 1,467 | `F8ED430414351000CC3A6C9C184D2B29A18C64F3490295D9AECCF893D31C08A5` | NO (Immutable) |
| `diag05_tier1_h1_raw_metrics_v1.json` | 79,492 | `5962B1C3A360AADC0B6F5DEA6E9A10545370D06E9A47CD449DA592C38E30D072` | NO (Immutable) |
| `diag05_tier1_h1_summary_v1.json` | 6,113 | `6FCADA5DADCB5091E4EAB9260CFE758CA37125F11B3AB62A10072FA5FC565768` | NO (Immutable) |
| `diag05_tier1_h2_raw_tile_observations_v1.json` | 66,644 | `A5A384D25CFF22B9BF724493ACFEC4EAD163E77E3253ED773C83FB6EE7D2B586` | NO (Immutable) |
| `diag05_tier1_h2_cluster_summaries_v1.json` | 29,155 | `A7D2FC0618CB3CC823D3971045580650DC9B025E91274BF12AFACADD0FACDDD3` | NO (Immutable) |
| `diag05_tier1_h2_paired_inference_v1.json` | 545 | `8BF6C9B3396D21306B666F9B16DB5F9C5716FF126370B7940783D044393D94AB` | NO (Immutable) |
| `ops02_diag05_tier1_gradient_dynamics_v1.json` | 7,914 | `8DE5FF5383A2C36927673D977C062063FD4D9F144C42351D7E4E302CC2487250` | NO (Immutable) |

All corrective evaluations are encapsulated in new versioned artifacts:
- `data/ops02/audits/diag05_tier1_corrected_h2_eligibility_census_v1.json` (`C4093EF5EACD1870113AEF7DADD5653E9F0B95F65D08DFB6359B1C577F418BE4`)
- `data/ops02/audits/diag05_tier1_corrected_h2_cluster_summaries_v1.json` (`D61084A5CB5A9A395F5F1D4BF1E58D15A0915A36525B4317E9338D88C97E14A3`)
- `data/ops02/audits/diag05_tier1_corrected_h2_paired_inference_v1.json` (`4F16287C8EC294CD040EA2288F5E2D95EF65DAB0E3114B1D0E2F80D175B9EA29`)

---

## 3. Full Post-Validity Eligibility Census

A deterministic brute-force census was performed across all 132 physical tiles in the OPS-02 TRAIN partition by applying the canonical SAR sensor validity mask (`compute_validity_mask`) and dense taxonomy remapping (`remap_source_mask_to_dense`):

```
================================================================================
DETERMINISTIC TRAIN POPULATION SUPPORT CENSUS (132 TILES)
================================================================================
Total TRAIN Tiles Audited:            132
Originally Eligible (Raw Mask):       28
Correctly Eligible (Post-Validity):   27
False Positives:                      1 (Tile ...-001-22)
False Negatives:                      0
Correctly Ineligible:                 104
Represented Clusters (Corrected):     15 (100% of originally represented clusters)
Empty Clusters Created:               0
================================================================================
```

### Detailed Forensic Audit of the False-Positive Tile
- **Sample ID:** `s1a-iw-grd-vv-20220129t174639-20220129t174704-041679-04f573-001-22`
- **Parent Scene ID:** `s1a-iw-grd-vv-20220129t174639-20220129t174704-041679-04f573-001` (Cluster 11)
- **Raw Disk Mask Support:** Rare = 119 pixels (source label 13, `HM`), Common = 65,417 pixels ($119 \ge 16$ and $65,417 \ge 64$; raw eligibility passed).
- **Post-Validity Support:** The SAR raster contained 11,390 invalid border pixels ($N_{\text{invalid}}=11,390$). All 119 pixels of label 13 were located entirely within these invalid border coordinates.
- **Valid Tensor Support:** Valid Rare = 0 pixels, Valid Common = 54,146 pixels, Valid Total = 54,146 pixels.
- **Root Defect:** Decoupling pre-execution census queries from SAR validity masking allowed an observation with zero valid rare pixels to enter the H2 execution loop, producing an all-zero subgradient and $\cos = 0.0$.
- **Corrective Action:** Classified as `INVALID_AND_EXCLUDE_FROM_H2_INFERENCE`.

---

## 4. Corrected H2 Population and Cluster Data

Because the remaining 27 physical tiles possess non-zero, valid post-preprocessing pixel counts satisfying dual support ($M_{\text{rare}} \ge 16$, $M_{\text{common}} \ge 64$), their original gradient calculations are **scientifically valid and fully reusable**. No backward passes were rerun.

Cluster 11 (`...-041679-04f573-001`) originally contained 2 tiles:
- Tile 21: Valid Rare = 76 px, Valid Common = 65,460 px ($\cos_{\text{can}} = -0.061275, \cos_{\text{uni}} = -0.059192, \Delta = -0.002083$).
- Tile 22 (Defective): Valid Rare = 0 px ($\cos_{\text{can}} = 0.0, \cos_{\text{uni}} = 0.0$).

Excluding Tile 22 leaves Cluster 11 represented by Tile 21 alone. **Zero clusters were eliminated**, maintaining $N_{\text{paired}} = 15$ clusters.

### Corrected Cluster Summaries (15 Clusters)

| Cluster Index | Parent Scene ID | Retained Tiles ($n$) | Canonical Median $\cos$ | Uniform Median $\cos$ | $\Delta \cos_k$ (Can - Uni) | Sign |
|---|---|---|---|---|---|---|
| 1 | `...-017861-01df20-001` | 1 | -0.1054 | -0.0978 | -0.007568 | Negative |
| 2 | `...-019602-0214b7-001` | 2 | +0.0158 | +0.0158 | -0.000008 | Negative |
| 3 | `...-020054-0222c6-001` | 1 | +0.0180 | +0.0180 | -0.000009 | Negative |
| 4 | `...-020690-023709-001` | 1 | -0.0760 | -0.0760 | -0.000001 | Negative |
| 5 | `...-021104-02442b-001` | 1 | +0.0147 | +0.0147 | -0.000011 | Negative |
| 6 | `...-021113-02446f-001` | 2 | -0.0737 | -0.0737 | +0.000004 | Positive |
| 7 | `...-030554-037fde-001` | 1 | -0.0791 | -0.0791 | -0.000000 | Negative |
| 8 | `...-031852-03ad13-001` | 1 | -0.0797 | -0.0797 | -0.000002 | Negative |
| 9 | `...-037985-047bb3-001` | 1 | -0.0770 | -0.0770 | -0.000000 | Negative |
| 10 | `...-041657-04f4b1-001` | 3 | -0.0697 | -0.0709 | +0.001158 | Positive |
| 11 | `...-041679-04f573-001` | 1 (Tile 21 only) | -0.0613 | -0.0592 | -0.002083 | Negative |
| 12 | `...-041696-04f609-001` | 4 | -0.1361 | -0.1170 | -0.019054 | Negative |
| 13 | `...-041709-04f685-001` | 3 | -0.1150 | -0.1163 | +0.001227 | Positive |
| 14 | `...-042056-05028e-001` | 1 | -0.1093 | -0.1093 | +0.000003 | Positive |
| 15 | `...-042057-05028f-001` | 4 | -0.1761 | -0.1352 | -0.040943 | Negative |

---

## 5. Statistical Provenance and Reconciled Inference

### Reconciliation of Executed vs. Corrected Quantities

| Parameter / Statistic | Original Executed Result (v1) | Corrected Registered Result (Asymptotic) | Corrected Exact Permutation Result |
|---|---|---|---|
| **Underlying Tiles ($n$)** | 28 physical tiles | 27 physical tiles | 27 physical tiles |
| **Inferential Clusters ($K$)** | 15 parent clusters | 15 parent clusters | 15 parent clusters |
| **Zero Differences ($n_{\text{zero}}$)** | 0 clusters | 0 clusters | 0 clusters |
| **Effective Pairs ($n_{\text{eff}}$)** | 15 clusters | 15 clusters | 15 clusters |
| **Positive / Negative Pairs** | 4 positive / 11 negative | 4 positive / 11 negative | 4 positive / 11 negative |
| **Wilcoxon Statistic ($W$)** | 34.0 | **32.0** | **32.0** |
| **p-value** | 0.151428 (labeled asymptotic) | **0.118313** ($Z = -1.562$) | **0.120483** ($= 3948 / 32768$) |
| **Statistical Decision ($\alpha=0.05$)** | Non-significant ($p > 0.05$) | Non-significant ($p > 0.05$) | Non-significant ($p > 0.05$) |

### Decoupling Method Metadata
In v1, calling `scipy.stats.wilcoxon` without `method="asymptotic"` defaulted to `method="exact"` under SciPy 1.15.3 ($N \le 50$), creating a discrepancy between the metadata string and the mathematical calculation. In the corrected paired inference artifact (`diag05_tier1_corrected_h2_paired_inference_v1.json`), the two distributions are explicitly separated and bound via their runtime function arguments (`method="asymptotic"` and `method="exact"`).

---

## 6. Corrected Scientific Language Standard

### H1 (Cross-Batch Dispersion)
- **Verified Facts:** Under the registered Step-0 minibatch diagnostic ($B_{\text{phys}}=4$, 132 TRAIN tiles), canonical weighting produced a lower observed global gradient-norm IQR ($0.1457$) than uniform weighting ($0.1763$), with an IQR ratio of $0.8266$ and $\Delta \log_{10}(\text{IQR}) = -0.0827$.
- **Corrected Language:**  
  *"Under the registered Step-0 minibatch diagnostic, canonical weighting produced lower observed global gradient-norm IQR than uniform weighting across minibatches. The observed result does not support the registered dispersion-expansion hypothesis."*
- **Prohibitions:** Strictly prohibit converting this descriptive IQR reduction into an inferential claim or inferring temporal training-time gradient volatility from static Step-0 dispersion.

### H2 (Directional Alignment)
- **Verified Facts:** In this Step-0 OPS-02 evaluation across 15 parent clusters, negative directional cosine similarity between rare-class and common-class subgradients was observed under both canonical weighting (median $-0.0720$) and uniform weighting (median $-0.0675$).
- **Corrected Language:**  
  *"Negative rare-vs-common directional cosine was observed under both weighting regimes in this Step-0 OPS-02 evaluation. Under the registered paired cluster design ($N_{\text{paired}}=15$), the Wilcoxon signed-rank test did not detect a statistically distinguishable paired difference between canonical and uniform weighting ($W = 32.0, p = 0.1183$ asymptotic, $p = 0.1205$ exact)."*
- **Prohibitions:** Strictly prohibit claiming that opposing orientation is an architectural invariant of ResNet18-UNet, SAR imagery generally, or later training dynamics. Strictly prohibit claiming that canonical weighting has zero effect on gradient geometry or asserting dynamic training stability without evidence.

---

## 7. Overall Validity Matrix

| Area | Status | Basis |
|---|---|---|
| **Execution Artifact Integrity** | `VALID_AND_IMMUTABLE` | All 7 original v1 machine JSON artifacts match cryptographic SHA-256 hashes bit-for-bit. |
| **H1 Descriptive Analysis** | `VALID_STEP0_DESCRIPTIVE_RESULT` | Complete 132-tile census verified; arithmetic matches raw data to machine precision. |
| **H2 Original Execution Population** | `DEFECTIVE_ELIGIBILITY_CONSTRUCTION` | Pre-validity census admitted Tile 22, which had zero post-validity rare support ($M_{\text{rare}}=0$). |
| **H2 Corrected Population Analysis** | `SCIENTIFICALLY_RECONCILED_POST_CORRECTION` | 27 post-validity tiles across 15 clusters verified; non-significance confirmed ($W=32.0, p=0.1183$). |
| **Statistical Provenance** | `EXPLICITLY_BOUND_AND_RECONCILED` | Exact permutation ($p=0.1205$) and asymptotic ($p=0.1183$) methods separated and verified. |
| **Scientific Interpretation** | `EPISTEMICALLY_BOUNDED` | Unsupported "intrinsicness" and "no effect" language completely removed. |
| **Governance Posture** | `HARDENED_AND_REGRESSION_PROTECTED` | Lessons `LL-DIAG05-EXEC-001` through `003` active; 8 automated tests passing. |
| **Tier-2 / H3 Readiness** | `NOT_JUSTIFIED_YET` | No static gradient pathology diagnosed; multi-epoch training interventions remain blocked. |

---

## 8. Governance Hardening and Added Rules

1. **`GOV-RULE-129` (Post-Validity Support Census):** Any sample eligibility query involving class support thresholds ($M_c \ge K$) must be evaluated *after* all preprocessing transformations that affect validity (specifically sensor validity masking $Y_{\text{valid}} \ne -100$, nodata exclusion, and border cropping). Samples with zero valid support for a target subset must be classified as `INELIGIBLE_ABSENT_MASK` and excluded from continuous directional distributions.
2. **`GOV-RULE-130` (Explicit Statistical Method Binding):** Non-parametric statistical tests must explicitly bind the execution parameter `method` (`exact` vs `asymptotic`) in code. Machine artifact schemas must state the exact distribution used to compute the reported p-value.
3. **`GOV-RULE-131` (Bounded Negative Epistemic Reporting):** Non-significant diagnostic findings under sample-constrained designs must be reported as bounded negative findings under the registered design envelope. Agents are strictly prohibited from asserting "no effect", "eliminated interference", or dynamic optimization stability without multi-step dynamic observation.
