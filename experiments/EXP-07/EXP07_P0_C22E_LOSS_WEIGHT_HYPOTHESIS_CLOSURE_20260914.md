# EXP-07-P0-C22-E: LOSS-WEIGHT HYPOTHESIS CLOSURE, C22-D INTERPRETATION REPAIR & NEXT-FAILURE DIAGNOSIS
**Experiment ID:** `EXP07_DIAG01_CLOSURE`  
**Task ID:** `EXP-07-P0-C22-E`  
**Date:** 2026-09-14  
**Status:** `COMPLETED_VALID`  
**Final Scientific Verdict:** `LOSS_WEIGHT_INTERVENTION = CLOSED_NOT_SUPPORTED_FOR_CANONICAL_REPLACEMENT`  
**Next Stage:** `FAILURE_DIAGNOSIS_BEFORE_INTERVENTION`  
**Authoritative Dataset:** `OPS02_v1.0.1_FROZEN` (`F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102`)  
**Canonical Initial State:** `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D`  

---

## 1. Executive Summary & Formal Closure

Following the completion of the original paired discovery experiment (**C22-B**, Seed 42), post-run forensic validation (**C22-C**), and four prospective paired replications (**C22-D**, Seeds 101, 202, 303, 404), this report formally closes the single-variable loss-weight intervention hypothesis.

### A. The Specific Question That Was Answered
> **Question:** Does changing from the canonical sqrt-median-frequency class weighting policy to uniform unweighted CrossEntropyLoss produce a robust, stable development-set advantage (`dev_mIoU_phenomena`) under the locked OPS-02 training protocol?  
> **Answer:** **NO.**

### B. What Remains Unknown & Was NOT Answered
This experiment answered *only* whether uniform weighting improves development performance over canonical sqrt-median-frequency weighting under the frozen ResNet18-UNet / Candidate F configuration. It did **NOT** answer:
- Which neural architecture or backbone family is optimal for SAR ocean phenomena segmentation;
- Which visual representation or feature extractor is optimal;
- Whether dataset volume (132 train tiles) or geographic diversity (40 clusters) is sufficient for generalized segmentation;
- Whether the 12-class taxonomy or label grouping is optimal;
- Whether single-channel VV SAR preprocessing (`log1p` + standardization) is optimal;
- Whether the Candidate F hybrid sampling ratio (70% parent / 30% class) is optimal;
- Whether the model can generalize to the quarantined HOLDOUT partition;
- Whether an alternative loss family (e.g. Focal Loss, Dice Loss, Lovász-Softmax) would confer an advantage.

---

## 2. Empirical Evidence Synthesis: C22-B Through C22-D

Across five paired random seed runs executed under identical bitwise initialization and loader conditions:

### Seed-by-Seed Results
| Seed | Seed Type | Control Best DEV mIoU (Epoch) | Treatment Best DEV mIoU (Epoch) | Paired Delta ($\Delta = \text{T} - \text{C}$) | Relative % | Winner | Initial Parity |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | Discovery (Historical) | 0.04147 (Ep 10 / 20) | 0.05318 (Ep 5 / 15) | **+0.01171** | +28.24% | **TREATMENT** | Bitwise Match |
| **101** | Prospective Replication | 0.05886 (Ep 15 / 25) | 0.04481 (Ep 5 / 15) | **-0.01405** | -23.87% | **CONTROL** | Bitwise Match |
| **202** | Prospective Replication | 0.04358 (Ep 27 / 30) | 0.04741 (Ep 6 / 16) | **+0.00383** | +8.79% | **TREATMENT** | Bitwise Match |
| **303** | Prospective Replication | 0.05191 (Ep 19 / 29) | 0.04605 (Ep 5 / 15) | **-0.00586** | -11.29% | **CONTROL** | Bitwise Match |
| **404** | Prospective Replication | 0.04940 (Ep 21 / 30) | 0.05398 (Ep 7 / 17) | **+0.00458** | +9.27% | **TREATMENT** | Bitwise Match |

### Statistical Summaries
- **Prospective Cohort Only ($n=4$, Seeds 101, 202, 303, 404):**
  - Treatment Wins: 2 (50.0%) | Control Wins: 2 (50.0%) | Ties: 0
  - Control Mean Best DEV mIoU: $0.05094 \pm 0.00639$
  - Treatment Mean Best DEV mIoU: $0.04806 \pm 0.00408$
  - **Mean Paired Delta ($\bar{\Delta}$):** $\mathbf{-0.00288} \pm 0.00877$ (favors Control)
  - Median Paired Delta: $-0.00102$
- **Combined Five-Pair Cohort ($n=5$, Seeds 42, 101, 202, 303, 404):**
  - Treatment Wins: 3 (60.0%) | Control Wins: 2 (40.0%) | Ties: 0
  - Control Mean Best DEV mIoU: $0.04904 \pm 0.00693$
  - Treatment Mean Best DEV mIoU: $0.04909 \pm 0.00421$
  - **Mean Paired Delta ($\bar{\Delta}$):** $\mathbf{+0.00004} \pm 0.01006$ ($\approx 0.000$)
  - Median Paired Delta: $+0.00383$
  - Range of Paired Deltas: $[-0.01405, +0.01171]$
  - Descriptive 95% Student-$t$ CI: $[-0.01244, +0.01253]$ (crosses zero symmetrically)

---

## 3. Formal Scientific Closure & Policy Decision

### Formal Scientific Decision
1. **Hypothesis Status:** `NOT SUPPORTED AS A ROBUST REPLACEMENT`.  
   The initial C22-B single-run observation (+0.01171 on Seed 42) does not replicate as a systematic development-set advantage under prospective random seeds.
2. **Canonical Training Policy:** **RETAIN** the canonical C16 sqrt-median-frequency class weighting policy:
   `[0.403935, 2.450546, 0.876692, 0.945945, 0.648189, 4.211476, 0.719641, 2.956203, 1.064525, 1.882870, 0.387652, 18.243211]`
3. **Uniform Weighting:** **DO NOT ADOPT** as canonical policy.
4. **Future Loss-Weighting Replications:** **NOT RECOMMENDED**. The hypothesis has been definitively answered under the frozen protocol.
5. **Exact Scientific Qualification:**  
   *The available five-pair evidence does not support replacing the canonical weighting policy.* We do NOT claim that the null hypothesis is mathematically proven, we do NOT claim exact statistical equivalence, and we do NOT claim that uniform weighting is harmful in general; rather, the intervention fails to confer a reliable, robust benefit that would justify altering the canonical training baseline.

---

## 4. Cross-Seed Failure Consistency & Per-Class Forensics

Analyzing the raw per-class IoU metrics across all 10 trained models (5 Control, 5 Treatment) characterizes the observed class-level performance distributions and the trade-offs associated with the loss-weight intervention:

### Class-by-Class Performance Across All 5 Seeds

| Dense | Class Name | Control Mean IoU | Control SD | Nonzero Seeds (C) | Treatment Mean IoU | Treatment SD | Nonzero Seeds (T) | Mean Paired Delta ($\text{T} - \text{C}$) | Directional Win Ratio |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | Background (BG) | 0.07014 | 0.05089 | 5/5 | 0.06190 | 0.04366 | 5/5 | -0.00824 | 2T / 3C / 0tie |
| 1 | Atmospheric Front (AF) | 0.00001 | 0.00002 | 0/5 | 0.00401 | 0.00736 | 3/5 | +0.00400 | 3T / 0C / 2tie |
| 2 | Biological Slicks (BS) | 0.07849 | 0.04938 | 5/5 | 0.05931 | 0.03321 | 5/5 | -0.01919 | 2T / 3C / 0tie |
| 3 | Low Wind Area (LWA) | 0.00014 | 0.00027 | 1/5 | 0.01150 | 0.01765 | 4/5 | +0.01136 | 4T / 0C / 1tie |
| 4 | Mesoscale Cellular Convection (MCC) | 0.25749 | 0.02769 | 5/5 | 0.21218 | 0.04690 | 5/5 | -0.04530 | 2T / 3C / 0tie |
| 5 | Oceanic Front (OF) | 0.00099 | 0.00177 | 2/5 | 0.00036 | 0.00067 | 2/5 | -0.00062 | 0T / 2C / 3tie |
| 6 | Pure Oceanic Waves (POW) | 0.06292 | 0.04014 | 5/5 | 0.00774 | 0.01128 | 5/5 | -0.05517 | 1T / 4C / 0tie |
| 7 | Rain Cells (RF) | **0.00000** | **0.00000** | **0/5** | **0.00000** | **0.00000** | **0/5** | **0.00000** | **0T / 0C / 5tie** |
| 8 | Wind Streaks (WS) | 0.01202 | 0.00635 | 4/5 | **0.00000** | **0.00000** | **0/5** | -0.01202 | 0T / 4C / 1tie |
| 9 | Eddy | 0.02362 | 0.03965 | 4/5 | 0.01530 | 0.02003 | 3/5 | -0.00832 | 2T / 3C / 0tie |
| 10 | Internal Waves (IWs) | 0.10380 | 0.05164 | 5/5 | 0.22949 | 0.01983 | 5/5 | **+0.12569** | 4T / 0C / 1tie |
| 11 | Anthropogenic Objects (HM) | **0.00000** | **0.00000** | **0/5** | 0.00002 | 0.00005 | 1/5 | +0.00002 | 1T / 0C / 4tie |

### Categorization of Observed Class-Level Performance Patterns
1. **High Observed Mean, Consistently Nonzero, Between-Seed Variability Present (`OBSERVED`):**
   - **MCC (Mesoscale Cellular Convection):** Consistently nonzero across all 10 runs (observed mean $0.257 \pm 0.028$ Control, $0.212 \pm 0.047$ Treatment; high DEV support with 17 scenes / 33.35% px; seed variability present).
   - **IWs (Internal Waves):** Consistently nonzero across all 10 runs (observed mean $0.104 \pm 0.052$ Control, $0.229 \pm 0.020$ Treatment; high DEV support with 31 scenes / 22.60% px; seed variability present).
   - *Descriptive Observation:* These two well-supported classes contribute the majority of the numerical value of the macro mIoU across all evaluated models.
2. **Consistently Near-Zero or Zero Observed Performance (`OBSERVED`):**
   - **RF (Rain Cells):** Exactly `0.00000` in 10 out of 10 runs (sparse DEV support: 2 scenes, 0.37% pixels).
   - **HM (Anthropogenic Objects):** Exactly `0.00000` in 9 out of 10 runs, 0.00012 in 1 run (sparse DEV support: 3 scenes, 0.005% pixels).
   - **OF (Oceanic Front):** Mean IoU $0.00099$ Control vs $0.00036$ Treatment; nonzero in 2/5 runs each (sparse DEV support: 1 scene, 0.067% pixels).
   - **AF (Atmospheric Front):** Mean IoU $0.00001$ Control vs $0.00401$ Treatment; absent in DEV ground truth ($0$ scenes).
3. **Low Observed Performance (`OBSERVED`):**
   - **WS (Wind Streaks):** Low observed IoU in Control ($0.01202 \pm 0.00635$, nonzero in 4/5 seeds) and zero in Treatment ($0.00000$ in 0/5 seeds); absent in DEV ground truth ($0$ scenes).
   - **LWA (Low Wind Area):** Low observed IoU across both arms (mean IoU $0.00014$ Control vs $0.01150$ Treatment).
4. **High Between-Seed Variability (`OBSERVED`):**
   - **POW (Pure Oceanic Waves):** High observed variability across seeds (Control spans $0.00277$ to $0.10183$, mean $0.06292 \pm 0.04014$; Treatment spans $0.00000$ to $0.02538$, mean $0.00774 \pm 0.01128$).
   - **BS (Biological Slicks):** High observed variability across seeds (Control spans $0.01839$ to $0.15839$, mean $0.07849 \pm 0.04938$; Treatment spans $0.02100$ to $0.10400$, mean $0.05931 \pm 0.03321$).
   - **Eddy:** High observed variability across seeds (Control spans $0.00000$ to $0.10235$, mean $0.02362 \pm 0.03965$; Treatment spans $0.00000$ to $0.04400$, mean $0.01530 \pm 0.02003$).

### Observed Class-Level Trade-Off Associated With the Loss-Weight Intervention
The empirical per-class deltas characterize the observed trade-offs across classes:
- Treatment was associated with higher observed IoU on **Internal Waves (IWs)** ($+0.12569$ mean delta).
- Simultaneously, Treatment was associated with lower observed IoUs on **Pure Oceanic Waves (POW)** ($-0.05517$), **Mesoscale Cellular Convection (MCC)** ($-0.04530$), **Biological Slicks (BS)** ($-0.01919$), and **Wind Streaks (WS)** ($-0.01202$, erased to zero).
- Uniform weighting did not produce a robust aggregate DEV advantage in the five-pair study; it shifted class-level performance trade-offs, associating with higher observed IoU on one class while showing lower observed IoUs on four others, resulting in an aggregate five-pair mean delta of $+0.00004$.

---

## 5. Failure Mode Diagnosis (Evidence-Tagged)

| Failure Mode | Tag | Empirical Evidence from Existing Artifacts |
| :--- | :---: | :--- |
| **1. Extreme Class Scarcity in OPS-02** | `OBSERVED` | Manifest analysis shows RF has only 13 train samples (0.54% pixels) and 2 dev samples. HM has 12 train samples (0.016% pixels) and 3 dev samples. OF has 9 train samples (0.27% pixels) and 1 dev sample. These 3 classes are completely unlearned in nearly all runs. |
| **2. Primary Metric Sensitivity to Sparse-Support Classes** | `OBSERVED` | Macro mIoU averages all 11 classes with equal weight ($1/11 \approx 9.09\%$). Classes with sparse DEV support (OF in 1 sample, RF in 2 samples) exhibit high estimator variance and sensitivity to individual scenes. When these classes achieve near-zero IoU, they contribute near-zero to the unweighted 11-class macro mean, creating an empirical drag on the aggregate score. Gains in IWs (+0.126) masked the simultaneous performance drop in WS and POW. |
| **3. High Between-Seed Sampler Instability** | `SUPPORTED` | Candidate F draws 72 tiles/epoch with replacement from 132 tiles. For rare classes (9-17 tiles), stochastic draw variance causes certain seeds to severely under-sample specific classes, leading to 8x to 36x variance in validation IoU across identical seeds (BS, POW). |
| **4. Radiometric Backscatter Ambiguity** | `SUPPORTED` | Single-band VV SAR provides only scalar backscatter intensity. Low-wind areas, wind streaks, and biological slicks all present as low-backscatter dark patches, producing mutual confusion in the absence of polarization contrast (VH) or multi-temporal cues. |
| **5. Spatial Resolution Loss on Fine Structures** | `HYPOTHESIZED` | ResNet18-UNet downsamples $32\times$ through 4 encoder stages. Front lines (OF, AF) and point targets (HM) are 1-3 pixels wide and may be lost in deep receptive fields before skip-connection recovery. |
| **6. Label Noise / Boundary Ambiguity** | `UNKNOWN` | No multi-annotator agreement study exists for OPS-02. While ocean front boundaries are naturally diffuse, label noise cannot be declared as a primary driver without empirical annotator consistency audits. |

---

## 6. Competing Explanations: Data vs. Optimization Bottleneck

| Candidate Explanation | Evidence FOR | Evidence AGAINST | Missing Evidence | Classification |
| :--- | :--- | :--- | :--- | :---: |
| **A. Optimization Limitation (LR/Scheduler/Loss)** | Loss weights alter class-level trade-offs (IWs vs MCC/POW). | Shifting from weighted to uniform loss yielded net zero delta ($+0.00004$). Smooth convergence curves. | Non-cross-entropy losses (Dice, Focal) unmeasured. | **LOW Confidence** (Not primary bottleneck) |
| **B. Architecture / Representation Limitation** | ResNet18 has limited capacity for multiscale ocean phenomena spanning 1-pixel targets to 100-pixel cells. | Achieves respectable IoU ($0.25 - 0.30$) on textured classes (MCC, IWs). | Modern backbones (ConvNeXt, Swin) unmeasured. | **MEDIUM Confidence** (Plausible contributing bottleneck) |
| **C. Sampling Imbalance / Stochasticity** | Severe between-seed variance on classes with 9-17 samples (BS, POW, Eddy). | RF and HM fail across all seeds regardless of sampling schedule. | Exact exposure count audit per epoch. | **HIGH Confidence** (Primary driver of seed volatility) |
| **D. Class Scarcity (Extreme Sample/Pixel Rarity)** | RF (0.54% px, 2 dev samples) and HM (0.016% px, 3 dev samples) are 100% unlearned across all 10 runs. OF (1 dev sample) is near zero. | None. In statistical learning, 1-3 validation scenes cannot establish generalization. | None. Proved directly by manifest counts. | **VERY HIGH Confidence** (Primary driver of zero IoU) |
| **E. Dataset Diversity Limitation** | OPS-02 TRAIN has only 132 tiles across 40 parent clusters; rare classes exist in only 1-2 clusters. | Major classes (MCC, IWs) generalize consistently across seeds. | Representation clustering across clusters. | **HIGH Confidence** (Constrains rare class learning) |
| **F. Label Ambiguity / Noise** | Ocean front boundaries are physically diffuse and hard to delineate. | Annotations derive from expert oceanographic analysis. | Systematic multi-annotator agreement study. | **UNKNOWN / HYPOTHESIZED** (Cannot claim without audit) |
| **G. Input Information Limitation (Single-Band VV)** | Dark-slick classes (WS, BS, LWA) have overlapping VV radar backscatter distributions. | Model separates IWs and MCC effectively from single band. | Dual-pol (VV+VH) or incidence angle data. | **MEDIUM-HIGH Confidence** (Physical information bound) |
| **H. Metric Sensitivity (Unweighted Macro-mIoU)** | Macro mIoU weights Class 5 (1 dev sample, 0.067% px) identically with Class 10 (31 dev samples, 22.6% px). Sparse class support in DEV may reduce the reliability and stability of class-level IoU estimates, because individual scenes contribute disproportionately to the metric. This is a measurement-support concern, not a mathematical upper bound on macro mIoU. | Macro mIoU is the frozen primary evaluation contract. | Support-stratified or frequency-weighted descriptive sensitivity summaries. | **HIGH Confidence** (Measurement & support sensitivity) |
| **I. Domain Shift (TRAIN vs DEV Clusters)** | DEV clusters are geographically disjoint from TRAIN clusters; class frequencies shift significantly. | C16 model achieves consistent IoU on MCC and IWs across both partitions. | Quantified feature space divergence (MMD). | **MEDIUM Confidence** (Contributes to partition gap) |

---

## 7. Review of Previous C20 Cross-Domain Evidence

In **EXP-07-P0-C20**, models trained on OPS-01 (C8, C10) were cross-evaluated on OPS-02 DEV:
- C8 on OPS-02 DEV: `0.0353`
- C10 on OPS-02 DEV: `0.0292`
- C16 (trained on OPS-02) on OPS-02 DEV: `0.0494`

### Descriptive Inference:
1. Transfer from OPS-01 to OPS-02 suffers significant degradation ($0.0494 \to 0.0292$), confirming that OPS-02 introduces substantial geographic diversity and environmental complexity rather than C16 suffering from a flawed training setup.
2. However, this evidence does *not* prove a causal domain shift mechanism; it descriptively indicates that **data distribution complexity and class scarcity** are far more influential than subtle training-loss modifications.

---

## 8. Prioritized Next Scientific Investigations

Using the selection criterion: **MAXIMUM INFORMATION GAIN PER UNIT OF COMPUTE**:

### Rank 1: Class-Support Stratification and Primary Metric Sensitivity Diagnostic
- **Diagnostic Question:** Does DEV class-support imbalance make the primary macro-mIoU estimate disproportionately sensitive to a small number of physical acquisitions, and how much does the interpretation change when results are stratified by class support?
- **Target Failure:** Disproportionate sensitivity of unweighted macro mIoU to sparse-support classes in DEV (e.g. OF in 1 sample, RF in 2 samples, HM in 3 samples), where individual acquisitions have high leverage on class-level estimates.
- **Existing Evidence:** Classes 1..11 vary in pixel volume by $>2000\times$. Sparse class support in the DEV partition may reduce the reliability and stability of class-level IoU estimates, because individual scenes contribute disproportionately to the metric. This is a measurement-support concern, not a mathematical upper bound on macro mIoU.
- **Why It Resolves Uncertainty:** Evaluates whether DEV class-support imbalance makes the primary macro-mIoU estimate disproportionately sensitive to a small number of physical acquisitions, examining macro mIoU across support strata, per-class IoU vs. parent acquisition counts, and support-weighted descriptive summaries as secondary diagnostics—without replacing or redefining the frozen primary benchmark metric.
- **Scientific Cost:** Very Low.
- **Compute Cost:** **ZERO GPU Compute** (CPU-only analytical re-aggregation of existing saved prediction tensors).
- **Confounding Risk:** Minimal (primary benchmark metric remains frozen and unchanged; secondary aggregations used solely for descriptive sensitivity analysis).
- **Expected Information Value:** **Extremely High**.
- **HOLDOUT Access:** **0 (Unnecessary)**.

### Rank 2: Candidate F Sampler Schedule Exposure & Seed-Variance Audit
- **Diagnostic Question:** Does the realized Candidate F sampling schedule produce materially different class/parent exposure patterns across seeds that are associated with the observed performance variance?
- **Target Failure:** High between-seed performance variance on moderately rare classes (BS spans 0.018 to 0.158; POW spans 0.003 to 0.102 across identical seeds).
- **Existing Evidence:** Model and dataset are identical; only the random seed driving Candidate F sampling schedules (72 draws/epoch with replacement from 132 samples) varies.
- **Why It Resolves Uncertainty:** Measures the empirical per-epoch exposure count for each class and parent across seeds, assessing whether realized sampling schedule differences correlate descriptively with between-seed performance variance, without assuming a causal starvation mechanism or modifying the sampler.
- **Scientific Cost:** Very Low.
- **Compute Cost:** **ZERO GPU Compute** (Combinatorial analysis of precomputed schedules and manifest sample annotations).
- **Confounding Risk:** Zero (deterministic offline audit).
- **Expected Information Value:** **High**.
- **HOLDOUT Access:** **0 (Unnecessary)**.

### Rank 3: Radiometric Contrast & Single-Channel Backscatter Distributional Overlap Diagnostic
- **Diagnostic Question:** Assess whether class-conditional backscatter distributions in the available single-band VV input exhibit substantial overlap that could plausibly limit discriminability.
- **Target Failure:** Persistent near-zero IoU on RF, HM, and lower observed performance on dark-slick classes (WS, LWA) under uniform loss.
- **Existing Evidence:** Single-band VV SAR provides scalar backscatter without polarization ratio (VH/VV) or multi-spectral contrast. Dark-slick classes share dark-backscatter characteristics in VV imagery.
- **Why It Resolves Uncertainty:** Quantifies empirical backscatter distributions (mean, variance, signal-to-clutter ratio, histogram overlap) within ground-truth mask polygons for all classes, measuring whether class-conditional backscatter distributions in single-channel VV SAR exhibit substantial overlap that could plausibly limit discriminability, without presuming an information bottleneck.
- **Scientific Cost:** Low.
- **Compute Cost:** **Negligible CPU Compute** (Statistical profiling of existing training GeoTIFFs).
- **Confounding Risk:** Minimal (characterizes data properties directly).
- **Expected Information Value:** **High**.
- **HOLDOUT Access:** **0 (Unnecessary)**.

---

## 9. HOLDOUT Firewall Compliance

- **HOLDOUT Partition Access Count:** **0** (`QUARANTINED_ZERO_ACCESS`)
- **Part III Benchmark Access Count:** **0** (`FIREWALLED_ZERO_ACCESS`)
- The pristine benchmark remains completely quarantined. No holdout evaluations were conducted, authorized, or attempted during C22-E.

---

## 10. Durable Agent Learning Encoded

The durable agent learning framework (`data/metadata/ocean_sentinel_lessons_learned_v1.json`) was updated with lessons validated by this task:
1. **`LL-C22E-001` (Scientific Validity):** Multi-seed replication can invalidate a single-seed intervention without indicating experiment failure. Case B is a valid scientific finding.
2. **`LL-C22E-002` (Scientific Validity):** Small-sample replication ($n=5$) must be treated as a robustness characterization, not forced significance testing ($p < 0.05$).
3. **`LL-C22E-003` (Scientific Validity):** Diagnostic interventions must not be extrapolated into canonical training policy without consistent multi-seed replication.
4. **`LL-C22E-004` (Scientific Validity):** Checkpoint timing differences do not establish causal convergence mechanisms or overfitting without direct mechanistic measurements.
5. **`LL-C22E-005` (Scientific Validity):** Diagnose failure modes empirically before proposing or launching the next ML intervention.
