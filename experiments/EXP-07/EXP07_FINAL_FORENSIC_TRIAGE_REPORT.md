# OCEAN SENTINEL — EXP-07 FINAL SCIENTIFIC FORENSIC TRIAGE REPORT
**Document ID:** `EXP07_FINAL_FORENSIC_TRIAGE_REPORT_V2`  
**Phase:** `EXP-07 FINAL FORENSIC RECONCILIATION + FAILURE DECOMPOSITION + PIVOT GATE`  
**Date:** 2026-09-26  
**Author:** AG (Controlled Repository Inspection / Implementation / Testing / Forensic Verification Worker)  
**Architecture Authority:** ChatGPT (CAO)  
**Approval Authority:** Human  
**Environment:** Antigravity IDE 2.0 (Windows, CPU-only, Python 3.10.9 in `.venv`, uv 0.11.7, pytest 9.1.1)  
**Branch:** `master`  
**Baseline HEAD Commit:** `542bab19f6f08c9bba8b8762e6480386c8b6026b`  
**Evaluation Target:** Complete EXP-07 Experiment Family Lifecycle (Protocols, Manifests, Runs, Diagnostics)  
**Epistemic Taxonomy:** Every statement is classified as `MEASURED FACT`, `DOCUMENTATION ERROR`, `VERSIONED CHANGE`, `EXECUTION DRIFT`, `SUPPORTED INTERPRETATION`, `WORKING HYPOTHESIS`, `DEVELOPMENT RECOMMENDATION`, or `UNKNOWN`.  
**Final Development Direction Gate:** **C. PIVOT — PROPOSED MODULAR CANDIDATE-DETECTION + LOOKALIKE-VALIDATION ARCHITECTURE**

---

## 1. Executive Summary

This forensic triage report evaluates the empirical performance of EXP-07 to answer the primary operational question:
$$\mathbf{Why\;did\;EXP-07\;produce\;low\;cross-scene\;segmentation\;performance\;(\approx 0.04 - 0.05\;mIoU),\;and\;what\;is\;the\;smallest\;evidence-backed\;next\;step?}$$

Based on exhaustive forensic reconciliation across all machine-readable artifacts, code, checkpoints, and multi-seed replications, the contributing factors are classified:
$$\mathbf{Primary\;Classification:\;H.\;MULTIPLE\;CONTRIBUTING\;CAUSES}$$
Specifically:
1. **Task Formulation Concern (`SUPPORTED INTERPRETATION`):** While pixel-label exclusivity is mathematically satisfied because ground-truth rasters assign a single dense class ID (0..11) per pixel, physical oceanic and atmospheric phenomena frequently co-occur and interact across scenes. Imposing flat categorical softmax cross-entropy forces winner-take-all dominant-class boundaries between gradational physical processes.
2. **Physical Modality Separability Limitation (`SUPPORTED INTERPRETATION`):** Under the tested regime, single-polarization (VV) Sentinel-1 SAR backscatter measures only capillary-gravity surface roughness. Without multi-frequency, dual-polarization, or broad contextual environmental fields (wind, SST), distinct physical features (biological slicks, low-wind areas, rain downburst edges, and mineral oil films) can produce similar dark-patch radar signatures.
3. **Sparse & Uneven Data Support (`MEASURED FACT`):** The 132 training tiles across 40 parent acquisitions provide sparse and highly uneven representation across the 12 dense classes (ranging over 4 orders of magnitude from 2.66M pixels down to 1,201 pixels). Several classes appear in only 1–3 parent acquisitions in DEV.
4. **Evaluation Split Sensitivity (`MEASURED FACT`):** On OPS-02 DEV ($n=40$), 2 classes (OF, RF) depend on exactly 1 parent acquisition, and 3 classes (BS, WS, Eddy) depend on only 2 parents, creating high evaluation sensitivity to small-sample partition boundaries.
5. **Loss-Weighting Replication (`MEASURED FACT`):** Across 5 paired seeds in C22-B and C22-D, class loss weighting demonstrated no consistent benefit. Observed deltas alternated signs across seeds (3 Treatment wins, 2 Control wins), and the aggregate mean delta was near zero ($+0.00004$) relative to observed cross-seed variability.

**Implementation & Verification Boundaries:**
- No material implementation defect was identified in the audited data loader, UNet architecture, loss function, or metric evaluation code paths (`MEASURED FACT`).
- Zero execution drift occurred in the core diagnostic runs (`MEASURED FACT`).
- Radiometric input distributions were stable ($\mu \approx 4.44$ in both TRAIN and DEV) (`MEASURED FACT`).

**Development Recommendation:**
The evidence supports a **DEVELOPMENT DECISION to PIVOT (Decision C)**. Ocean Sentinel should not continue the exact 12-class flat phenomenon segmentation formulation unchanged. The recommended development direction is a modular, cascaded pipeline:
$$\mathbf{Existing\;EXP-06\;Binary\;Detector\;\longrightarrow\;Candidate\;Region\;Extraction\;\longrightarrow\;Lookalike\;Suppression\;(Contextual/Meteorological)\;\longrightarrow\;Temporal\;Drift\;\longrightarrow\;AIS\;Correlation\;\longrightarrow\;Evidence\;Fusion}$$
This is a **DEVELOPMENT RECOMMENDATION** and a **WORKING HYPOTHESIS**, not a universal scientific proof that multi-class segmentation is impossible or that the proposed cascade is already validated.

---

## 2. Evidence Inventory

All repository material belonging to EXP-07 was inventoried and verified against machine-readable ground truth (`MEASURED FACT`):
- **Protocol Specifications & Contracts:** 
  - `experiments/PHASE_EXP07_P0_SCIENTIFIC_PROTOCOL_AND_OPS01_CONTRACT_20260913.md` (Initial draft proposal)
  - `experiments/EXP-07/EXP07_P0_C4_FINAL_PROTOCOL_FREEZE_IMPLEMENTATION_CONTRACT_20260913.md` (OPS-01 frozen contract)
  - `experiments/EXP-07/EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md` (OPS-02 pretraining protocol)
  - `experiments/EXP-07/EXP07_P0_C21_C20_POST_AUDIT_AND_SINGLE_VARIABLE_DIAGNOSTIC_PROTOCOL_20260914.md` (Diagnostic protocol)
  - `experiments/EXP-07/EXP07_P0_C22A9_FINAL_PROTOCOL_CONSISTENCY_AND_READINESS_20260914.md` (Pre-training readiness audit)
- **Dataset Manifests & Freeze Specifications:**
  - `data/metadata/ops01_physical_dataset_manifest_v4.json` (OPS-01 manifest, 147 sample pairs)
  - `data/ops02/OPS02_DATASET_FREEZE_SPEC_v1.0.1.json` (OPS-02 dataset freeze specification)
  - `data/ops02/manifests/ops02_physical_dataset_manifest_v1.json` (OPS-02 physical manifest, 212 sample pairs, SHA256: `F5480EA2...`)
  - `data/ops02/manifests/ops02_partition_manifest_v1.json` (132 TRAIN / 40 DEV / 40 HOLDOUT)
  - `data/ops02/manifests/ops02_parent_cluster_manifest_v1.json` (64 independent clusters)
- **Executable Machine-Readable Run Manifests & Checkpoints:**
  - `experiments/EXP-07/runs/EXP07_RUN001_SEED42/` (OPS-01 Baseline Run 001, Seed 42, `dev_mIoU_phenomena` = 0.11903)
  - `experiments/EXP-07/runs/EXP07_RUN002_SEED101/` (OPS-01 Replicate Run 002, Seed 101, `dev_mIoU_phenomena` = 0.13782)
  - `experiments/EXP-07/runs/EXP07_RUN003_SEED42/metrics.json` (OPS-02 Replicate Run 003, Seed 42, `dev_mIoU_phenomena` = 0.04940)
  - `experiments/EXP-07/runs/EXP07_DIAG01/exp07_diag01_paired_comparison.json` (C22-B paired run Seed 42, Control: 0.04147, Treatment: 0.05318)
  - `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/exp07_diag01_replication_aggregate.json` (C22-D 5-seed aggregate)
  - `data/ops02/initial_model_state_canonical.pt` (SHA256: `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D`)
- **Diagnostic Reports:** 42 markdown reports spanning C2 through C22-J.
- **AI-Agent Attributions:** Reports attributed to AG, Antigravity, Perplexity, and Claude were treated as secondary observational evidence. The authoritative source of truth for each historical run remains: binding protocol version + execution manifest + raw result artifacts + cryptographic hashes + recorded runtime environment.

---

## 3. Protocol Lineage Matrix

The complete 36-dimension machine-readable lineage matrix was compiled in [`experiments/EXP-07/EXP07_FORENSIC_PROTOCOL_LINEAGE.json`](file:///d:/Projects/ocean-sentinel/experiments/EXP-07/EXP07_FORENSIC_PROTOCOL_LINEAGE.json) (`MEASURED FACT`).

Summary across the 6 formal stages of EXP-07:

| Dimension Group | Dimensions Included | Lineage Status | Classification |
| :--- | :--- | :--- | :---: |
| **Dataset & Splits** | Dataset ID, Sample Count, Split Allocation, Parent Counts (Dims 1–4) | Formally expanded from OPS-01 (147 samples, 27 parents) to OPS-02 (212 samples, 64 parents) in C12–C15. | `VERSIONED_CHANGE` |
| **Input & Preprocessing** | Channels, Representation, Radiometric Transform, Normalization (Dims 5–8) | Single-band VV SAR (1 channel), 10x10 block-mean DN, `np.log1p(max(DN,0))`. Normalization updated to match OPS-02 TRAIN ($\mu=4.424158, \sigma=0.469261$). | `VERSIONED_CHANGE` |
| **Taxonomy & Labels** | Label Encoding, Taxonomy Version, Ignore Index, Augmentation (Dims 9–12) | 12 dense classes (0..11), source 3/9/14 mapped to -100. Augmentation frozen as disabled (`BASELINE_IDENTITY_NO_AUGMENTATION`) in C4. | `VERSIONED_CHANGE` |
| **Sampling & Batching** | Sampler, Batch Size, Gradient Accumulation (Dims 13–15) | Candidate F Hybrid (70% parent, 30% class, 72 draws/epoch), $B_{\text{mini}}=8$, accum=2, virtual batch=16. | `VERSIONED_CHANGE` |
| **Architecture & Init** | Architecture, Param Count, Initialization (Dims 16–18) | ResNet18-UNet (14,310,860 trainable params). Initialization canonicalized to ImageNet ResNet18 + Kaiming UNet decoder under seed 42 (`initial_model_state_canonical.pt`). | `VERSIONED_CHANGE` |
| **Optimization & Schedule** | Loss, Class Weights, Optimizer, LR, WD, Scheduler, Epoch Limits, Stopping (Dims 19–27) | CrossEntropyLoss; AdamW (lr=5e-4, wd=0.01); Cosine Annealing; `MAX_EPOCHS=30, MIN_EPOCHS=15, PATIENCE=10` monitoring `dev_mIoU_phenomena`. | `VERSIONED_CHANGE` |
| **Evaluation & Governance** | Seed Policy, Primary Metric, Secondary Metrics, Checkpoint Rule, HOLDOUT, Part-III, Hardware, Software, Source Commit (Dims 28–36) | Primary metric strictly `dev_mIoU_phenomena` (classes 1..11, BG excluded). Checkpoint selection strictly maximized primary metric. HOLDOUT access = 0; Part-III access = 0. | `SAME_AS_PREVIOUS` |

---

## 4. Documentation Errors

Four documentation drafting errors were identified in historical markdown reports and reconciled (`DOCUMENTATION ERROR`):
1. **Modality Misnomer (C22-A.8 Q4):** Described input data as "SAR VV/VH Tiles" despite the dataset physically containing solely single-channel VV GeoTIFFs. Repaired in C22-A.9 erratum.
2. **Truncated Loss Vector (C22-A.8 Q10):** Listed an erroneous 3-element draft vector (`[0.0898, 0.9069, 1.0033]`) instead of the actual 12-element Sqrt-Median Frequency vector. Repaired in C22-A.9 erratum.
3. **Epoch Schedule Conflation (C22-A.8 Q10):** Described schedule as "epochs = 15," conflating `MIN_EPOCHS = 15` with `MAX_EPOCHS = 30`. Repaired in C22-A.9 erratum.
4. **OPS-02 Split Narrative Typo (C15 Review):** Claimed 41 DEV / 39 HOLDOUT in narrative prose, while manifests and filesystem stored exactly 40 DEV / 40 HOLDOUT. Formalized and corrected in `OPS02_DATASET_FREEZE_SPEC_v1.0.1.json`.

---

## 5. Execution Drift Findings

$$\mathbf{Material\;Execution\;Drift:\;0}$$
No material execution drift occurred between the authoritative frozen protocols (C15, C21, C22-A.9) and executable training runs (`MEASURED FACT`):
- In C22-B (`EXP07_DIAG01`), all 22 operational parameters matched the frozen specification bit-for-bit.
- In C22-D (`EXP07_DIAG01_REPLICATION`), all 4 prospective replications executed under bitwise identical invariants.
- Sampler schedules and initial weight states matched verified cryptographic hashes.

---

## 6. Dataset-Version Lineage

The progression from OPS-01 to OPS-02 was a formal, intentional dataset expansion (`VERSIONED CHANGE`):
- **OPS-01 (`OPS01_v1.0.0`):** 147 physical sample pairs from 27 parent scenes (72 TRAIN / 39 DEV / 36 HOLDOUT). Used for Run 001 and Run 002.
  - On OPS-01, models achieved ~0.119 to ~0.138 `dev_mIoU_phenomena`. However, C11 adversarial review revealed that 7 DEV parents shared identical regional/sensor conditions with training scenes, allowing cross-tile spatial correlation.
- **OPS-02 (`OPS02_v1.0.1_FROZEN`):** 212 physical sample pairs from 64 independent parent clusters (132 TRAIN / 40 DEV / 40 HOLDOUT).
  - Enforced strict mission datatake clustering (GOV-RULE-077) and spatial pre-slice isolation (GOV-RULE-075).
  - On OPS-02, `dev_mIoU_phenomena` settled at ~0.049 across Run 003, C22-B, and C22-D.
  - The change in score reflected the elimination of along-track spatial correlation and exposed the difficulty of cross-scene generalization under the tested setup.

---

## 7. C22-B Configuration Isolation

In C22-B (`EXP07_DIAG01`), paired training was executed under Seed 42 (`MEASURED FACT`):
- **Target Variable:** Loss function class weighting.
  - Control Arm: Sqrt-Median Frequency weights (47.06:1 dynamic range).
  - Treatment Arm: Uniform unweighted (`[1.0] * 12`, 1.00:1 dynamic range).
- **Audit Findings:**
  - Initial weights: Bitwise identical (`initial_model_state_canonical.pt`, fingerprint `B472DBA8...`).
  - Sampling schedule: Bitwise identical (Candidate F Hybrid, schedule SHA256: `2B1562E3...`).
  - Dataset: Bitwise identical (`OPS02_v1.0.1_FROZEN`).
  - Optimizer, LR, scheduler, batch dynamics, stopping rule: Bitwise identical.
- **Pairing Classification:** **VALID** (`MEASURED FACT`). The single-variable isolation held.

---

## 8. C22-D Configuration Isolation

In C22-D (`EXP07_DIAG01_REPLICATION`), paired training was replicated across 4 prospective seeds (101, 202, 303, 404) (`MEASURED FACT`):
- **Audit Findings:**
  - Within each seed, Control and Treatment shared bitwise identical initial weights, identical seed-specific Candidate F sampling schedules, and identical hyperparameters, differing solely in the loss weight vector.
  - All 8 runs were evaluated strictly under the frozen early stopping rule (`min_epochs=15`, `patience=10`).
- **Pairing Classification:** **VALID** (`MEASURED FACT`). Single-variable isolation held across all 4 replication pairs.

---

## 9. Exact Numerical Reconciliation

All values verified directly from raw run artifacts (`exp07_diag01_paired_comparison.json`, `exp07_diag01_replication_aggregate.json`) (`MEASURED FACT`):

| Seed | Seed Type | Control dev_mIoU | Treatment dev_mIoU | Delta (Trt - Ctrl) | Relative Change | Winner |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **42** | Discovery Observation | 0.04147 | 0.05318 | **+0.01171** | +28.24% | Treatment |
| **101** | Prospective Replication | 0.05886 | 0.04481 | **-0.01405** | -23.87% | Control |
| **202** | Prospective Replication | 0.04358 | 0.04741 | **+0.00383** | +8.79% | Treatment |
| **303** | Prospective Replication | 0.05191 | 0.04605 | **-0.00586** | -11.29% | Control |
| **404** | Prospective Replication | 0.04940 | 0.05398 | **+0.00458** | +9.27% | Treatment |

### Statistical Synthesis (`MEASURED FACT`):
- **Prospective Replications Only (Seeds 101, 202, 303, 404):**
  - Control Mean: $0.05094$
  - Treatment Mean: $0.04806$
  - Mean Delta: $\mathbf{-0.00288}$ (raw: $-0.002875$)
  - Sample SD Delta: $0.00884$
  - Median Delta: $-0.00101$
  - Min Delta: $-0.01405$ | Max Delta: $+0.00458$
  - Wins: 2 Treatment, 2 Control
- **All Five Pairs (Including Discovery Seed 42):**
  - Control Mean: $0.04904$ ($\sigma = 0.00693$)
  - Treatment Mean: $0.04909$ ($\sigma = 0.00421$)
  - Mean Delta: $\mathbf{+0.00004}$ (raw: $+0.000042$)
  - Sample SD Delta: $0.01006$
  - Delta Median: $+0.00383$
  - Delta Min: $-0.01405$ | Delta Max: $+0.01171$
  - Wins: 3 Treatment, 2 Control (60% win rate)
  - Student's $t$ 95% Confidence Interval for Delta: $[-0.01244, +0.01253]$ (Encompasses zero)
- **Ratio Note:** The ratio of sample SD ($0.01006$) to $\mid\text{mean delta}\mid$ ($0.000042$) is approximately $240$. However, this ratio is numerically volatile because the denominator is near zero; it is not cited as a standard measure of effect size.
- **Evidence-Bounded Interpretation (`SUPPORTED INTERPRETATION`):** No consistent weighting benefit was observed in this small paired study. The observed deltas alternated signs across seeds, and the aggregate mean delta was near zero relative to observed cross-seed variability.

---

## 10. Radiometric & Preprocessing Lineage Reconciliation

Formally documented in [`experiments/EXP-07/EXP07_RADIOMETRIC_LINEAGE_RECONCILIATION.json`](file:///d:/Projects/ocean-sentinel/experiments/EXP-07/EXP07_RADIOMETRIC_LINEAGE_RECONCILIATION.json) (`MEASURED FACT`):
- **Early Proposal Draft:** The initial proposal in `PHASE_EXP07_P0_SCIENTIFIC_PROTOCOL_AND_OPS01_CONTRACT_20260913.md` and `ops01_loader_contract_v1.json` proposed $10\log_{10}(\text{DN} + 10^{-6})$ and loosely labeled it "pseudo-dB."
- **Executed Machine Truth:** The frozen protocol contract (C4 Section 3, C15, C21) and 100% of executable training runs (Run 001, Run 002, Run 003, C22-B, C22-D) executed:
  $$z = \log(1 + \max(\text{raw\_dn}, 0.0)) = \text{np.log1p}(\max(\text{raw\_dn}, 0.0))$$
  followed by TRAIN-derived standardization: $\hat{x} = (z - \mu_{\text{train}}) / \sigma_{\text{train}}$.
- **Mathematical Relationship:** $\text{np.log1p}(x)$ (natural log) and $10\log_{10}(x)$ (base-10 decibels) are mathematically distinct functions ($\approx 4.34\times$ scale difference plus offset). Subsequent standardization absorbs linear scaling, but they are not identical.
- **Calibration Status:** Physical calibrated $\sigma_0$ dB was **never established** because 10x10 spatial block-averaging of detected DN violates Jensen's inequality for radiometric calibration. The authorized terminology across all executed runs is `log1p-transformed DN` or `AGGREGATED_RAW_DN_LOG1P_STANDARDIZED`.

---

## 11. Taxonomy & Task Formulation Audit

An explicit separation is established across three distinct levels (`SUPPORTED INTERPRETATION`):
1. **Physical Co-occurrence (`TRUE`):** Real-world oceanic and atmospheric phenomena frequently co-occur within the same marine region. For example, wind streaks (WS) and low-wind areas (LWA) overlay internal waves (IWs) and biological slicks (BS); rain cells (RF) induce atmospheric fronts (AF) and downdrafts.
2. **Pixel-Label Exclusivity (`TRUE`):** In the physical GeoTIFF/PNG ground-truth masks, each valid pixel is assigned exactly one integer class ID ($0..11$) or $-100$ for ignore/border. There are no multi-label or multi-hot arrays on disk.
3. **Scientific Semantic Exclusivity (`TASK FORMULATION CONCERN`):** Because ground-truth rasters are single-label, flat categorical softmax cross-entropy is mathematically well-defined on the data representation. However, forcing human annotators and neural networks to pick a single winner-take-all dominant class at diffuse, overlapping boundaries creates significant task formulation ambiguity.

**Conclusion:** The task formulation is classified as a **TASK FORMULATION CONCERN** (`SUPPORTED INTERPRETATION`). It is not mathematically contradictory on single-label rasters, but its suitability for representing complex physical phenomena in single-band SAR is not established.

---

## 12. Failure Decomposition

Compiled in [`experiments/EXP-07/EXP07_FAILURE_DECOMPOSITION.json`](file:///d:/Projects/ocean-sentinel/experiments/EXP-07/EXP07_FAILURE_DECOMPOSITION.json):

1. **Dataset Adequacy (`LOW`):** 132 TRAIN tiles across 40 parent acquisitions provide sparse coverage for 11 dynamic phenomena, with several classes appearing in only 1–3 parent acquisitions in DEV.
2. **Label/Taxonomy Compatibility (`TASK FORMULATION CONCERN`):** Co-occurring natural phenomena create dominant-class assignment ambiguity under flat categorical softmax.
3. **Physical Modality Separability (`SUPPORTED INTERPRETATION`):** Single-polarization (VV) radar backscatter alone showed poor empirical separability across dark-patch phenomena under the tested setup.
4. **Label Quality (`MEDIUM`):** Boundary delineations for diffuse phenomena (WS, LWA, AF) are subject to annotator variability; HM point targets (117 px in DEV) suffer high IoU sensitivity from minor spatial offsets.
5. **Input Distribution (`PASS`):** Preprocessing and normalization are verified mathematically consistent.
6. **Loader Correctness (`PASS`):** No material defect was identified in the audited loader paths.
7. **Metric Correctness (`PASS`):** Verified mathematically sound; absent-class handling properly maintains denominator 11 on DEV.
8. **Optimization Behavior (`MEASURED_PLATEAU`):** Training loss decreases, but DEV mIoU plateaus at ~0.04–0.05 as 8 of 11 classes fail to achieve substantial cross-scene learning.
9. **Generalization/Split Effect (`HIGH_SENSITIVITY`):** Leave-one-parent-out analysis demonstrates high sensitivity to individual parent acquisitions.
10. **Randomness/Stability (`UNSTABLE`):** Variation across random seeds dominates the loss weighting intervention effect.

---

## 13. Cheap Baseline Context

Non-learning diagnostic baselines computed directly on OPS-02 DEV labels ($2,564,519$ valid pixels) (`MEASURED FACT`):

| Baseline Predictor | Strategy | dev_mIoU_phenomena | dev_mIoU_all | Role & Classification |
| :--- | :--- | :---: | :---: | :--- |
| **All-Background Predictor** | Predict Class 0 (BG) everywhere | **0.00000** | 0.02092 | Descriptive trivial baseline |
| **TRAIN Majority-Phenomenon Predictor** | Predict Class 10 (IWs) everywhere | **0.02054** | 0.01883 | Descriptive constant baseline |
| **DEV Majority-Class Predictor** | Predict Class 4 (MCC) everywhere | **0.03025** | 0.02773 | Descriptive constant baseline |
| **TRAIN-Prior Random Predictor** | Random draw matching TRAIN marginals | **0.03192** | 0.04225 | Descriptive stochastic prior baseline |
| **DEV-Oracle Random Predictor** | Random draw matching DEV oracle marginals | **0.03853** | 0.04728 | **Descriptive Oracle-Prior Baseline** (Contextualization only; not an independent benchmark) |
| **Trained ResNet18-UNet (EXP-07)** | 14.3M parameter model across 5 seeds | **0.04147 – 0.05886** (Mean **0.04907**) | **0.045 – 0.062** | Evaluated experimental models |

### Contextual Interpretation (`SUPPORTED INTERPRETATION`):
The trained ResNet18-UNet model achieves an average `dev_mIoU_phenomena` of **0.04907**:
- Margin above a trivial constant predictor (MCC everywhere): **+0.01882**
- Margin above an independent random predictor using oracle class priors: **+0.01054**

A small margin over non-learning baselines combined with high cross-seed instability indicates that the model has not established robust spatial multi-class discrimination across the full taxonomy under the tested regime.

---

## 14. Stability Analysis

Across 5 paired seeds (10 runs total) (`MEASURED FACT`):
- Control scores range from 0.04147 to 0.05886 (range = 0.01739).
- Treatment scores range from 0.04481 to 0.05398 (range = 0.00917).
- Deltas alternate signs across seeds (+0.01171, -0.01405, +0.00383, -0.00586, +0.00458).
- The sample standard deviation of deltas ($0.01006$) is substantially larger than the mean delta ($0.000042$).
This demonstrates that class loss weighting did not consistently improve performance across independent random seeds.

---

## 15. Repairs & Corrections Made

1. **Claims Audit Created:** Generated [`experiments/EXP-07/EXP07_CLAIMS_AUDIT.json`](file:///d:/Projects/ocean-sentinel/experiments/EXP-07/EXP07_CLAIMS_AUDIT.json) formalizing 10 reworded claims to prevent overclaiming (`MEASURED FACT`).
2. **Radiometric Lineage Reconciled:** Generated [`experiments/EXP-07/EXP07_RADIOMETRIC_LINEAGE_RECONCILIATION.json`](file:///d:/Projects/ocean-sentinel/experiments/EXP-07/EXP07_RADIOMETRIC_LINEAGE_RECONCILIATION.json) formalizing the distinction between `np.log1p(DN)` and $10\log_{10}(\text{DN})$ across all runs (`MEASURED FACT`).
3. **Candidate Lessons Updated:** Hardened all 7 candidate lessons in [`scratch/exp07_final_forensic_triage_lessons.md`](file:///d:/Projects/ocean-sentinel/scratch/exp07_final_forensic_triage_lessons.md) with explicit evidence statuses, counterexamples, and non-authoritative tagging (`MEASURED FACT`).
4. **Corrective Learnings Recorded:** Captured 7 new corrective learnings in [`scratch/exp07_final_forensic_corrective_lessons.md`](file:///d:/Projects/ocean-sentinel/scratch/exp07_final_forensic_corrective_lessons.md) (`MEASURED FACT`).
5. **No Code Mutations Needed:** Audited loader, model, loss, and metric code were verified free of material implementation bugs; zero speculative code mutations were performed (`MEASURED FACT`).

---

## 16. Tests

- **Governance Metrics Suite (`tests/test_governance_metrics.py`):** **28 passed / 28 collected (100% in 0.29s)**.
- **Selected Nine-Suite Governance Regression Gate:** **306 passed / 306 collected (100% in 22.77s)**:
  - `tests/test_governance_metrics.py`: 28 passed
  - `tests/test_governance_control_effectiveness.py`: 48 passed
  - `tests/test_ocean_sentinel_agent_learning_framework.py`: 12 passed
  - `tests/test_governance_v2_adversarial_replay.py`: 27 passed
  - `tests/test_governance_v2_architecture.py`: 21 passed
  - `tests/test_ocean_sentinel_agent_governance.py`: 27 passed
  - `tests/test_staged_governance_isolation.py`: 62 passed
  - `tests/test_report_reconciliation_learning.py`: 48 passed
  - `tests/test_ais_adversarial.py`: 33 passed
- **Scientific Training Executed:** Exactly **0 epochs, 0 backward passes**.

---

## 17. Protected Hashes

All 7 protected files verified bit-for-bit against established baselines (`MEASURED FACT`):

| File Path | Established Baseline SHA-256 | Current Observed SHA-256 | Verification Status |
| :--- | :--- | :--- | :---: |
| `.gitignore` | `a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444` | `a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444` | **IDENTICAL** |
| `src/ocean_sentinel/ingestion/dataset.py` | `f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c` | `f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c` | **IDENTICAL** |
| `src/ocean_sentinel/governance/runner.py` | `dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0` | `dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0` | **IDENTICAL** |
| `data/metadata/governance_v2/rules.json` | `b216f369d68a027e4708e8cbcf3991d8effd5ba5a063a3b8b6b3fc2261d85c4e` | `b216f369d68a027e4708e8cbcf3991d8effd5ba5a063a3b8b6b3fc2261d85c4e` | **IDENTICAL** |
| `data/metadata/governance_v2/lessons.json` | `4784a440070bc00612bc3bfa9b29a7acc181934f894a9e22bd340faab7076395` | `4784a440070bc00612bc3bfa9b29a7acc181934f894a9e22bd340faab7076395` | **IDENTICAL** |
| `data/metadata/governance_v2/incidents.json` | `fa3051a185894ee1fe46edb5825ebcfe92b107f80fb7527bf5746d4ec5b91836` | `fa3051a185894ee1fe46edb5825ebcfe92b107f80fb7527bf5746d4ec5b91836` | **IDENTICAL** |
| `src/ocean_sentinel/temporal.py` | `46614361e1be20a278d0af9ceee222e4787df1eade7d52a88b372965170e26cf` | `46614361e1be20a278d0af9ceee222e4787df1eade7d52a88b372965170e26cf` | **IDENTICAL** |

---

## 18. Git State

- **Branch:** `master`
- **Baseline HEAD Commit:** `542bab19f6f08c9bba8b8762e6480386c8b6026b`
- **Staged Modifications:** Exactly **0** (verified via `git diff --cached --name-status`).
- **Tracked Modified Files:** Exactly **3** (pre-existing authorized baseline state: `.gitignore`, `pyproject.toml`, `src/ocean_sentinel/ingestion/dataset.py`).
- **Git Operations Executed:** Exactly **0** commits, **0** pushes, **0** resets, **0** checkouts, **0** stashes.

---

## 19. Candidate Lessons

Documented in [`scratch/exp07_final_forensic_triage_lessons.md`](file:///d:/Projects/ocean-sentinel/scratch/exp07_final_forensic_triage_lessons.md) (`NON_AUTHORITATIVE / PROPOSED_ONLY`):
- `EXP07-01`: Protocol Version Evolution Must Be Formally Decoupled from Execution Drift
- `EXP07-02`: Binding Historical Protocol and Manifest Precedence Over Later Code States
- `EXP07-03`: Model Initialization Is a First-Class Scientific Invariant
- `EXP07-04`: Task Formulation Must Be Checked for Consistency Across Modality, Taxonomy, and Labels
- `EXP07-05`: Low Performance Must Be Decomposed Before Initiating Hyperparameter Tuning
- `EXP07-06`: Directionally Mixed Multi-Seed Evidence Precludes Canonical Baseline Replacement
- `EXP07-07`: Negative Experiments Can Justify Changing Development Direction Without Proving the Success of the Pivot

---

## 20. Final Decision Gate

$$\mathbf{FINAL\;DEVELOPMENT\;DIRECTION:\;C.\;PIVOT}$$

---

## 21. Exact Reason for Decision

The decision to **PIVOT** is a **DEVELOPMENT DECISION** based on converging empirical observations (`SUPPORTED INTERPRETATION`):
1. **Implementation is verified:** No material defect was identified in data loading, normalization, architecture, or evaluation metrics that would explain the low cross-scene scores.
2. **Modality separability concern:** Single-polarization (VV) SAR backscatter showed poor empirical separability among dark-patch features under the tested setup without ancillary contextual data.
3. **Task formulation concern:** While pixel-label exclusivity is mathematically satisfied by single-label rasters, physical co-occurrence creates ambiguity in dominant-class pixel assignment.
4. **Data support is sparse:** 132 training tiles across 40 parent acquisitions provides limited coverage for 11 dynamic phenomena across global oceans.
5. **Loss weighting did not resolve the issue:** Across 5 paired seeds, the mean delta was near zero ($+0.00004$) with mixed signs, showing that class loss weighting did not overcome the low performance ceiling.

The current EXP-07 formulation produced poor and unstable cross-scene development performance under the tested dataset, taxonomy, modality, and protocol. Continuing the exact formulation unchanged is not justified by current evidence.

---

## 22. Exact Next Authorized Scientific Action

The recommended next scientific direction for Ocean Sentinel is **PATH B (Proposed Development Architecture)**:
1. **Preserve the Existing EXP-06 Binary Oil Detection Baseline:** Retain the binary segmentation model as an internal candidate proposal component.
2. **Design a Dedicated Candidate Lookalike-Suppression Stage:** Extract candidate dark patches identified by the binary detector and classify/filter them using:
   - Patch morphology, texture, and contrast features.
   - Auxiliary contextual and environmental data (wind speed vectors, SST gradients) as future hypotheses.
3. **Integrate Downstream Pipeline Modules:**
   - Temporal pair reasoning (persistence vs atmospheric dissipation).
   - AIS maritime traffic correlation.
   - Multi-source evidence fusion.

*Note: Path B is a proposed development direction, not an already-validated architecture. No training or model implementation of Path B is authorized within this triage phase.*

---

## 23. Explicit Non-Claims

To maintain absolute epistemic integrity:
1. We do **NOT** claim that EXP-06 binary detection alone is sufficient for operational real-world deployment without false-positive lookalike suppression.
2. We do **NOT** claim that EXP-07 proves multi-class maritime phenomenon segmentation is universally impossible under other modalities or larger datasets.
3. We do **NOT** claim that uniform loss weighting has a proven zero effect; evidence establishes only that no consistent benefit was demonstrated in this small paired study ($+0.00004$ mean delta, mixed seed wins).
4. We do **NOT** claim that any automated governance rule was promoted or altered in Governance V2.
5. We do **NOT** claim universal repository-wide test passing beyond the 306 verified regression tests.
6. We do **NOT** claim to have inspected, evaluated, or accessed any part of the quarantined HOLDOUT or Part-III benchmarks.

---

$$\mathbf{EXP-07\;FINAL\;SCIENTIFIC\;FORENSIC\;TRIAGE\;PHASE\;STATE:\;FROZEN}$$
