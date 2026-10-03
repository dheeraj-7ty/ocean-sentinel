# EXP-07-P0-C22-F: C22-E ANALYTICAL CORRECTION & DIAGNOSTIC-ROADMAP VALIDATION REPORT

**Experiment ID:** `EXP07_DIAG01_ROADMAP_VALIDATION`  
**Task ID:** `EXP-07-P0-C22-F`  
**Parent Task:** `EXP-07-P0-C22-E`  
**Date:** 2026-09-14  
**Status:** `COMPLETED_VALID`  
**Final Terminal Status:** `C22E_ANALYTICAL_CORRECTION = COMPLETED_VALID`  
**Next Authorized Stage:** `EXECUTE ONLY THE HIGHEST-RANKED ZERO-COMPUTE DIAGNOSTIC` (Await explicit user authorization; do not auto-launch)  
**Authoritative Dataset:** `OPS02_v1.0.1_FROZEN` (`F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102`)  
**Canonical Initial State:** `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D`  

---

## Executive Summary

Task **EXP-07-P0-C22-F** is a focused analytical correction and pre-diagnostic validation gate. Following the completion of the five-pair loss-weighting replication study (C22-B through C22-D) and closure report (C22-E), an analytical audit identified critical overstatements and invalid mathematical ceiling claims in the C22-E diagnostic roadmap prose and Level 5 JSON priorities.

Specifically, C22-E asserted that single-scene rare classes in DEV *"mathematically cap macro mIoU at ~0.05"*. This claim was mathematically false. The primary metric is the arithmetic macro mean over classes 1..11. Sparse class support (1-3 DEV scenes) creates **high estimator variance, measurement instability, and sensitivity to individual scenes**—it does not establish a deterministic mathematical upper bound on the metric.

This task has audited all underlying five-seed empirical data, repaired all identified analytical overstatements in the C22-E artifacts, calibrated the diagnostic roadmap to sound scientific hypothesis framing, confirmed that the frozen primary benchmark metric remains strictly immutable, and established durable learning and regression guardrails.

**Execution Constraints Compliance:**
- **Model Training:** `0 steps` (`training = 0`)
- **GPU Compute:** `0 seconds` (`gpu_compute = 0`)
- **HOLDOUT Partition Reads:** `0 access` (`holdout_access_count = 0`, `QUARANTINED_ZERO_ACCESS`)
- **Part III Benchmark Reads:** `0 access` (`part_iii_access_count = 0`, `FIREWALLED_ZERO_ACCESS`)
- **New ML Interventions:** `0 created`

---

## 1. Exact Analytical Errors Found in C22-E

| Error ID | Section / Location | Original C22-E Prose | Scientific Flaw / Mathematical Error |
| :--- | :--- | :--- | :--- |
| **ERR-C22F-001** | Line 16 of `ops02_c22e_next_diagnostic_priorities_v1.json`, Lines 131, 150, 174 of `EXP07_P0_C22E_...md` | *"Macro mIoU masking and artificial compression caused by single-scene rare classes in DEV ... mathematically capping macro mIoU at ~0.05."* | **Conflation of Estimator Uncertainty with Mathematical Ceiling:** The primary metric is the macro arithmetic mean over classes 1..11. A class appearing in 1, 2, or 3 DEV scenes does not have an IoU mathematically capped at zero or any constant; if a model segments those pixels well, class IoU can be high. Rare support creates high estimator variance and sensitivity to individual scenes, not an arithmetic upper bound. The ~0.05 value is an empirical observation under the current model, not a mathematical ceiling. |
| **ERR-C22F-002** | Section 4, Line 101 of `EXP07_P0_C22E_...md` | Labeled **MCC** and **IWs** as *"Stable Strength (Consistently Learned Across All Runs)"*. | **Unwarranted Stability Claim:** High observed mean performance does not imply cross-seed stability. While MCC achieved high mean IoU ($0.257$ C, $0.212$ T) with high support (17 DEV scenes), its standard deviation across seeds was non-trivial ($\text{SD} = 0.028$ C, $0.047$ T). Similarly, IWs showed significant seed variability ($\text{SD} = 0.052$ C). Calling a class "stable" requires a quantitative stability rule satisfied by data. |
| **ERR-C22F-003** | Section 4, Line 118 & 122 of `EXP07_P0_C22E_...md` | *"The Underlying Zero-Sum Trade-off"*, *"Why the Loss-Weight Intervention Yielded Net Zero"*, and *"Uniform weighting did not improve representation learning."* | **Causal and Representation Overstatement:** The experiment measured task segmentation metrics (`dev_mIoU_phenomena`, class IoUs) under a locked protocol; it did not measure internal feature representations directly (e.g. via CKA, probing, or linear readout). Stating that uniform loss "did not improve representation learning" equates task performance with representation quality without measurement. |
| **ERR-C22F-004** | Section 8, Line 192 of `EXP07_P0_C22E_...md` and Line 50 of `ops02_c22e_next_diagnostic_priorities_v1.json` | *"Radiometric Contrast & Single-Channel Information Bottleneck Audit"* and assuming that between-seed variance in Rank 2 is caused by *"stochastic starvation"*. | **Premature Mechanistic Speculation:** Labeling single-channel VV SAR as an "information bottleneck" assumes a physical limitation before measuring class-conditional backscatter distributions. Similarly, attributing between-seed variance to "starvation" assumes a causal mechanism rather than a descriptive correlation. |

---

## 2. Exact Corrections Made

All identified errors have been corrected in both `data/ops02/audits/ops02_c22e_next_diagnostic_priorities_v1.json` and `experiments/EXP-07/EXP07_P0_C22E_LOSS_WEIGHT_HYPOTHESIS_CLOSURE_20260914.md`:

1. **Rare-Class Metric Claim:**
   - *Replaced with evidence-calibrated concept:*  
     > *"Sparse class support in the DEV partition may reduce the reliability and stability of class-level IoU estimates, because individual scenes contribute disproportionately to the metric. This is a measurement-support concern, not a mathematical upper bound on macro mIoU."*
2. **Performance vs Stability Separation:**
   - Replaced *"Stable Strengths"* with **"High Observed Mean, Consistently Nonzero, Between-Seed Variability Present (`OBSERVED`)"**.
   - Added explicit qualifiers noting that high observed mean performance and between-seed variability are separate dimensions.
3. **Causal & Representation Language:**
   - Changed heading to: **"Observed Class-Level Trade-Off Associated With the Loss-Weight Intervention"**.
   - Changed representation claim to: **"Uniform weighting did not produce a robust aggregate DEV advantage in the five-pair study."**
4. **Diagnostic Framing for Ranks 2 and 3:**
   - Rank 2 framed as: *"Does the realized Candidate F sampling schedule produce materially different class/parent exposure patterns across seeds that are associated with the observed performance variance?"* (Descriptive correlation, no causal assertion).
   - Rank 3 framed as: *"Assess whether class-conditional backscatter distributions in the available single-band VV input exhibit substantial overlap that could plausibly limit discriminability."* (Hypothesis testing, no assumed bottleneck).

---

## 3. Verified Five-Seed Class-Support Observations

The raw five-seed replication artifacts (`data/ops02/audits/ops02_c22d_multiseed_replication_v1.json`, run metrics for Seeds 42, 101, 202, 303, 404) and dataset manifest (`ops02_physical_dataset_manifest_v1.json`) were independently re-audited without reading HOLDOUT content.

### Class Support and Performance Matrix (10 Evaluated Runs)

| Dense | Class | TRAIN Scenes ($n=132$) | TRAIN Px % | DEV Scenes ($n=40$) | DEV Px % | Control Mean IoU | Control SD | Nonzero Seeds (C) | Treatment Mean IoU | Treatment SD | Nonzero Seeds (T) | Mean Paired Delta ($\text{T}-\text{C}$) | Evidence Classification |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | BG | 132 | 55.94% | 40 | 43.61% | 0.07014 | 0.05089 | 5/5 | 0.06190 | 0.04366 | 5/5 | -0.00824 | `OBSERVED` |
| 1 | AF | 3 | 0.037% | 0 | 0.000% | 0.00001 | 0.00002 | 0/5 | 0.00401 | 0.00736 | 3/5 | +0.00400 | `OBSERVED` |
| 2 | BS | 1 | 0.210% | 0 | 0.000% | 0.07849 | 0.04938 | 5/5 | 0.05931 | 0.03321 | 5/5 | -0.01919 | `OBSERVED` |
| 3 | LWA | 0 | 0.000% | 0 | 0.000% | 0.00014 | 0.00027 | 1/5 | 0.01150 | 0.01765 | 4/5 | +0.01136 | `OBSERVED` |
| 4 | MCC | 27 | 11.33% | 17 | 33.35% | 0.25749 | 0.02769 | 5/5 | 0.21218 | 0.04690 | 5/5 | -0.04530 | `OBSERVED` |
| 5 | OF | 9 | 0.266% | 1 | 0.067% | 0.00099 | 0.00177 | 2/5 | 0.00036 | 0.00067 | 2/5 | -0.00062 | `OBSERVED` |
| 6 | POW | 2 | 0.070% | 0 | 0.000% | 0.06292 | 0.04014 | 5/5 | 0.00774 | 0.01128 | 5/5 | -0.05517 | `OBSERVED` |
| 7 | RF | 13 | 0.542% | 2 | 0.368% | 0.00000 | 0.00000 | 0/5 | 0.00000 | 0.00000 | 0/5 | 0.00000 | `OBSERVED` |
| 8 | WS | 3 | 0.018% | 0 | 0.000% | 0.01202 | 0.00635 | 4/5 | 0.00000 | 0.00000 | 0/5 | -0.01202 | `OBSERVED` |
| 9 | Eddy | 1 | 0.103% | 0 | 0.000% | 0.02362 | 0.03965 | 4/5 | 0.01530 | 0.02003 | 3/5 | -0.00832 | `OBSERVED` |
| 10 | IWs | 97 | 31.47% | 31 | 22.60% | 0.10380 | 0.05164 | 5/5 | 0.22949 | 0.01983 | 5/5 | +0.12569 | `OBSERVED` |
| 11 | HM | 12 | 0.016% | 3 | 0.005% | 0.00000 | 0.00000 | 0/5 | 0.00002 | 0.00005 | 1/5 | +0.00002 | `OBSERVED` |

### Key Empirical Takeaways
1. **DEV Ground Truth Distribution:** Exactly 5 phenomenon classes have positive ground truth pixel counts in OPS-02 DEV: MCC (17 scenes), IWs (31 scenes), RF (2 scenes), HM (3 scenes), and OF (1 scene). Classes AF, BS, LWA, POW, WS, Eddy have zero ground truth pixels in DEV.
2. **Primary Metric Numerics:** The primary metric (`dev_mIoU_phenomena`) averages all 11 phenomenon classes. Because classes 1..11 are weighted equally ($1/11 \approx 9.09\%$), classes with near-zero IoU contribute near-zero to the sum, resulting in an aggregate score around $0.049$.
3. **Measurement Reliability vs Cap:** When OF appears in 1 scene (1,749 pixels) or HM in 3 scenes (137 pixels), the class IoU is subject to extreme estimator variance. A single scene dictates the class IoU entirely. This is an estimator reliability concern, not an arithmetic ceiling.

---

## 4. Corrected Priority Rationales

### Corrected Rank-1 Rationale
- **Investigation ID:** `DIAG-01-CLASS-SUPPORT-METRIC-SENSITIVITY`
- **Title:** Class-Support Stratification and Primary Metric Sensitivity Diagnostic
- **Core Diagnostic Question:** *Does DEV class-support imbalance make the primary macro-mIoU estimate disproportionately sensitive to a small number of physical acquisitions, and how much does the interpretation change when results are stratified by class support?*
- **Target Failure:** Disproportionate sensitivity of the primary unweighted macro metric to small acquisition subsets in DEV.
- **Why It Resolves Uncertainty:** Evaluates whether model assessment changes when stratified by support level (e.g. well-supported MCC/IWs vs sparse-support RF/HM/OF vs zero-support classes), quantifying sensitivity to individual parent acquisitions without altering or replacing the frozen primary metric contract.

### Corrected Rank-2 Rationale
- **Investigation ID:** `DIAG-02-SAMPLER-EXPOSURE-SCHEDULE-AUDIT`
- **Title:** Candidate F Sampler Schedule Exposure and Seed-Variance Audit
- **Core Diagnostic Question:** *Does the realized Candidate F sampling schedule produce materially different class/parent exposure patterns across seeds that are associated with the observed performance variance?*
- **Target Failure:** High between-seed performance volatility on moderately rare classes (BS spans 0.018 to 0.158; POW spans 0.003 to 0.102 in Control).
- **Why It Resolves Uncertainty:** Measures the empirical realized sampling draws across 30 epochs for each seed, establishing whether exposure frequency correlates descriptively with validation variance, without altering the sampler or presuming causal starvation.

### Corrected Rank-3 Rationale
- **Investigation ID:** `DIAG-03-RADIOMETRIC-INPUT-DISCRIMINABILITY`
- **Title:** Single-Band VV SAR Radiometric Contrast and Distributional Overlap Diagnostic
- **Core Diagnostic Question:** *Assess whether class-conditional backscatter distributions in the available single-band VV input exhibit substantial overlap that could plausibly limit discriminability.*
- **Target Failure:** Persistent near-zero IoU on RF, HM, and lower observed performance on dark-slick classes under uniform loss.
- **Why It Resolves Uncertainty:** Measures empirical backscatter distributions (mean, variance, signal-to-clutter ratio, histogram overlap) within ground truth polygons across classes to test whether single-channel VV backscatter overlaps significantly, without assuming an information bottleneck.

---

## 5. Final Diagnostic Ranking & Evidence Classification

| Final Rank | Investigation ID | Evidence Strength | Expected Information Gain | Compute Cost | Confounding Risk | Feasible Without Training? | Requires Only Existing Artifacts? |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **RANK 1** | `DIAG-01-CLASS-SUPPORT-METRIC-SENSITIVITY` | `HIGH` | `VERY_HIGH` | **ZERO GPU** (CPU analytical) | `LOW` | **YES** | **YES** |
| **RANK 2** | `DIAG-02-SAMPLER-EXPOSURE-SCHEDULE-AUDIT` | `MODERATE-HIGH` | `HIGH` | **ZERO GPU** (Combinatorial) | `LOW` | **YES** | **YES** |
| **RANK 3** | `DIAG-03-RADIOMETRIC-INPUT-DISCRIMINABILITY` | `MODERATE` | `MODERATE-HIGH` | **ZERO GPU** (CPU NumPy) | `LOW` | **YES** | **YES** |

### Justification for Maintaining Rank 1 as Highest Priority
1. **Immediate Diagnostic Leverage:** Rank 1 addresses how the primary benchmark metric evaluates existing models on the DEV partition ($n=40$). Before investing time in sampler exposure or radiometric extraction, we must understand how sensitive the primary evaluation metric is to individual acquisitions.
2. **Zero Compute & Zero Confounding:** Rank 1 operates entirely on existing evaluated prediction tensors and confusion matrices across Seeds 42, 101, 202, 303, 404. It requires no retraining, no parameter updates, and introduces no training confounders.
3. **Strict Benchmark Invariance:** Rank 1 does **not** change the frozen primary metric (`dev_mIoU_phenomena` over classes 1..11). Alternative aggregations (support-stratified, parent-weighted) are evaluated strictly as descriptive secondary diagnostics.

---

## 6. Primary Benchmark Metric Contract Confirmation

- **Primary Metric:** `dev_mIoU_phenomena`
- **Evaluated Classes:** Classes 1 through 11 (dense taxonomy indices 1..11)
- **Background Class 0:** Strictly excluded from the phenomena metric
- **Status:** **FROZEN, UNCHANGED, IMMUTABLE**
- **Strict Governance Ruling:**
  > [!IMPORTANT]
  > The primary metric contract is not being modified. Support-stratified or frequency-weighted aggregations are authorized solely as descriptive secondary sensitivity analyses. They must NOT redefine the benchmark, alter early stopping decisions, or serve as training targets.

---

## 7. Governance, Quarantine & Resource Invariants

- **Model Training Steps:** `0` (Zero backward passes, zero optimizer steps)
- **GPU Compute Seconds:** `0.0s` (Zero GPU utilization)
- **HOLDOUT Partition Access Count:** `0` (`QUARANTINED_ZERO_ACCESS`)
- **Part III Benchmark Access Count:** `0` (`FIREWALLED_ZERO_ACCESS`)
- **Staged Git Modifications:** `0`
- **Tracked Unstaged Files Preserved:** `.gitignore`, `src/ocean_sentinel/ingestion/dataset.py`
- **Active Background Processes:** `0`

---

## 8. Durable Agent Learning Encoded

The durable learning framework (`data/metadata/ocean_sentinel_lessons_learned_v1.json`) has been updated with lessons validated by C22-F:

1. **`LL-C22F-001` (Scientific Validity):**  
   *Sparse class support can reduce metric reliability without creating a mathematical upper bound on macro performance; distinguish estimator uncertainty from deterministic metric bounds.*
2. **`LL-C22F-002` (Scientific Validity):**  
   *High mean class performance does not imply stability across seeds; report these as separate properties.*
3. **`LL-C22F-003` (Scientific Validity):**  
   *Performance changes do not establish representation-level changes without representation-level measurements.*
4. **`LL-C22F-004` (Scientific Validity):**  
   *Input information limitation must be measured, not assumed; frame modality constraints as testable distributional hypotheses.*

---

## 9. Final Terminal Status & Next Authorized Stage

- **FINAL TERMINAL STATUS:**  
  `C22E_ANALYTICAL_CORRECTION = COMPLETED_VALID`

- **NEXT AUTHORIZED STAGE:**  
  `EXECUTE ONLY THE HIGHEST-RANKED ZERO-COMPUTE DIAGNOSTIC`  
  *(Investigation `DIAG-01-CLASS-SUPPORT-METRIC-SENSITIVITY`: Class-Support Stratification and Primary Metric Sensitivity Diagnostic)*

> [!CAUTION]
> **Execution Hold:** Do NOT automatically launch the Rank-1 diagnostic in this task. C22-F is strictly limited to correcting and validating the roadmap. Execution must pause here and await explicit user authorization.
