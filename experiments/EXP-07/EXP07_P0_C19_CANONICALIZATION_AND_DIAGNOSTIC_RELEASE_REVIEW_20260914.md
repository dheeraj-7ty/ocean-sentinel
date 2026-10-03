# EXP-07-P0-C19: C18 Self-Correction, Canonical Taxonomy/Protocol Reconciliation, Artifact Consistency Repair, and Controlled-Diagnostic Release Review

**Document ID:** `EXP07_P0_C19_CANONICALIZATION_AND_DIAGNOSTIC_RELEASE_REVIEW_20260914`  
**Project:** Ocean Sentinel  
**Subsystem:** EXP-07 Multiclass Oceanic and Atmospheric Phenomena Perception Foundation  
**Task:** EXP-07-P0-C19  
**Author:** Ocean Sentinel Research & Governance Council (Pair Programming Agent)  
**Date:** 2026-09-14  
**Status:** COMPLETE / CANONICALIZED  
**Training Status:** PAUSED / PROHIBITED (`training_started = false`, `next_training_authorized = false`, `kaggle_started = false`)

---

## 1. Executive Verdict

Phase C18 successfully resolved the physical manifest transcription discrepancy (reconciling 40 DEV / 40 HOLDOUT) and established the post-freeze dataset identity `OPS02_v1.0.1_FROZEN`. However, a forensic review of C18 revealed material internal contradictions and documentation drift between C18 narrative text and underlying machine-readable artifacts.

**Executive Verdict for C19:**
1. **NO MODEL TRAINING** was performed in C19 (`training_started = false`, `next_training_authorized = false`). All training runs (Replicate 004, Seed 101, Seed 2024) remain **STRICTLY BLOCKED**.
2. **Canonical Taxonomy Restored and Locked:** Repudiated unauthorized synonym tokens (`AS`, `Thermal`) introduced in C18 narrative reports. Canonical 12-class dense ordering (0: BG, 1: AF, 2: BS, 3: LWA, 4: MCC, 5: OF, 6: POW, 7: RF, 8: WS, 9: Eddy, 10: IWs, 11: HM) is permanently locked under [GOV-RULE-095](file:///d:/Projects/ocean-sentinel/data/metadata/ocean_sentinel_governance_rules_v1.json).
3. **Canonical Training Protocol Reconciled:** Formally rejected C18 report narrative drift (`lr=3e-4, wd=1e-4, 20 epochs, accumulation=1, effective_bs=8, seed+epoch`). Reaffirmed the frozen Level 4 protocol: AdamW ($\eta=5\times 10^{-4}$, $\lambda=0.01$), LinearWarmupCosineAnnealingLR (30 epochs, 3 warmup, $\eta_{\min}=1\times 10^{-6}$), batch 8, accumulation 2 (effective batch 16), Candidate F sampler (72 draws, `base_seed + epoch * 1000`). Codified under [GOV-RULE-096](file:///d:/Projects/ocean-sentinel/data/metadata/ocean_sentinel_governance_rules_v1.json).
4. **C16 Execution Machine Truth Reconstructed:** Verified from machine artifacts (`metrics.json`, `epoch_history.json`, Kaggle execution logs) that C16 achieved its peak DEV phenomena mIoU of 0.049399 at **Epoch 17** (not epoch 4), trained for 27 epochs before triggering early stopping, executed on single-GPU `cuda:0`, and ingested 132 TRAIN / 40 DEV samples with 0 HOLDOUT access.
5. **Input Tensor Shape Reconciled:** Verified that 100% of the 212 physical samples are $256 \times 256$ pixels. C18's mention of `[1, 512, 512]` was an isolated documentation typo. Input contract is strictly `[B, 1, 256, 256]`.
6. **Tier-1 Cross-Evaluation Epistemic Standard Enforced:** Downgraded C18's overclaim that cross-evaluation "directly separates" causal hypotheses. Cross-domain evaluation across confounded dataset pairs is descriptive transfer diagnostics only ([GOV-RULE-098](file:///d:/Projects/ocean-sentinel/data/metadata/ocean_sentinel_governance_rules_v1.json)).
7. **Tier-1 Release Gate:** Status set to **`TIER1_AUTHORIZED_WITH_LIMITATIONS`**. Tier-1 zero-compute cross-evaluation is cleared for subsequent execution in Phase C20, but execution within C19 is prohibited.

---

## 2. C18 Errors Discovered and Catalogued

Detailed in [exp07_p0_c19_incident_register_v1.json](file:///d:/Projects/ocean-sentinel/data/metadata/exp07_p0_c19_incident_register_v1.json):

| Incident ID | Severity | Description in C18 Report | Actual Machine Truth | Root Cause & Remediation |
|---|---|---|---|---|
| **INC-C18-001** | HIGH | Section 11 table stated best DEV mIoU was at Epoch 4. | Best DEV mIoU was at **Epoch 17** (0.049399). Stopped at epoch 27. | Transcription error in markdown table compilation. Machine truth restored from `metrics.json` under GOV-RULE-097. |
| **INC-C18-002** | CRITICAL | Section 11 table listed lr=3e-4, wd=1e-4, 20 epochs, accum=1, effective_bs=8. | Executed and frozen protocol was lr=5e-4, wd=0.01, 30 epochs budget (3 warmup, 27 decay), accum=2, effective_bs=16. | Unverified draft template values copied into report. Erroneous values permanently purged; canonical protocol restored under GOV-RULE-096. |
| **INC-C18-003** | MEDIUM | Section 9 narrative stated sampler seed formula as `seed + epoch`. | Established protocol and executed script used `base_seed + epoch * 1000`. | Omission of `* 1000` in narrative text (underlying JSON audit had correct formula). Formula locked across all specs. |
| **INC-C18-004** | HIGH | Section 4, 6, 8, 14, 15 introduced `AS` and `Thermal` and jumbled class indices. | Canonical taxonomy: 0 BG, 1 AF, 2 BS, 3 LWA, 4 MCC, 5 OF, 6 POW, 7 RF, 8 WS, 9 Eddy, 10 IWs, 11 HM. | Narrative synonym substitution during C18 drafting. Repudiated drifted terms under GOV-RULE-095. |
| **INC-C18-005** | HIGH | Section 7 narrative stated tensor dimensions as `[1, 512, 512]`. | Physical samples and model input contract are strictly $256 \times 256$. | Documentation copy-paste typo from generic UNet literature. Reconciled in `ops02_c19_input_shape_audit_v1.json`. |
| **INC-C18-006** | HIGH | C18 claimed Tier 1 cross-evaluation would "directly separate" distribution shift from optimization defect. | Cross-evaluation across multi-factor confounded datasets is descriptive transfer evidence only. | Inductive overclaim conflating transfer diagnostics with counterfactual ablation. Epistemic status downgraded under GOV-RULE-098. |

---

## 3. Authoritative-Source Hierarchy

To prevent narrative documentation from overriding empirical engineering realities, C19 establishes a formal 6-level authority hierarchy:

- **LEVEL 1 — PHYSICAL DATA / DIRECT ARTIFACT TRUTH:**
  - Materialized GeoTIFF and PNG files under `data/ops02/`
  - Exact image and mask byte contents, dimensions, and radiometric values
  - Cryptographic SHA-256 digests
  - Manifests: `ops02_physical_dataset_manifest_v1.json`, `ops02_partition_manifest_v1.json`, `ops02_parent_cluster_manifest_v1.json`
- **LEVEL 2 — FROZEN SPECIFICATION:**
  - `data/ops02/OPS02_DATASET_FREEZE_SPEC_v1.0.1.json` (cryptographically bound to Level 1)
- **LEVEL 3 — CANONICAL IMPLEMENTATION:**
  - `src/ocean_sentinel/ml/exp07_reference.py`
  - `src/ocean_sentinel/ingestion/freeze_validator.py`
- **LEVEL 4 — FORMAL FROZEN PROTOCOL:**
  - `experiments/EXP-07/EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md`
- **LEVEL 5 — EXECUTED RUN RECORDS:**
  - Kaggle execution logs (`ocean-sentinel-exp07-c16-replicate-003.txt`)
  - Run metadata: `metrics.json`, `epoch_history.json`, `training_environment.json`
  - Checkpoint binaries: `best_model.pt`, `last_model.pt`
- **LEVEL 6 — RETROSPECTIVE AUDIT REPORTS:**
  - Markdown reports for C16, C17, C18, C19.

**Operational Mandate:** Narrative reports (Level 6) MUST NOT override direct artifact truth (Levels 1–5). Whenever a discrepancy exists, Level 1–5 machine artifacts are authoritative.

---

## 4. Taxonomy Reconciliation

Audited and locked in [ops02_c19_taxonomy_canonicalization_v1.json](file:///d:/Projects/ocean-sentinel/data/ops02/audits/ops02_c19_taxonomy_canonicalization_v1.json).

### Canonical 12-Class Dense Taxonomy
```
Index 0:  BG    (Background Seawater, Source 0)
Index 1:  AF    (Atmospheric Front, Source 1)
Index 2:  BS    (Biological Slicks, Source 2)
Index 3:  LWA   (Low Wind Area, Source 4)
Index 4:  MCC   (Mesoscale Cellular Convection, Source 5)
Index 5:  OF    (Ocean Front, Source 6 - strictly natural oceanographic front, NOT oil)
Index 6:  POW   (Pure Ocean Wave, Source 7)
Index 7:  RF    (Rain Cell / Rain Footprint, Source 8)
Index 8:  WS    (Wind Streak, Source 10)
Index 9:  Eddy  (Oceanic Eddy, Source 11)
Index 10: IWs   (Internal Waves, Source 12)
Index 11: HM    (Artificial / Anthropogenic Objects, Source 13 - vessels, platforms, infrastructure)
```

### Quarantined / Excluded Source Labels (Mapped to `IGNORE_INDEX = -100`)
- **Source 14:** Mineral Oil Spill (Quarantined under `GOV-RULE-060`)
- **Source 3:** Iceberg (Excluded from EXP-07 perception scope)
- **Source 9:** Sea Ice (Excluded from EXP-07 perception scope)

### Terminology Discrepancy Findings
- The token `AS` does NOT exist in the canonical taxonomy and was an unauthorized hallucination.
- The token `Thermal` does NOT exist in the canonical taxonomy and was an unauthorized hallucination.
- `OF` strictly denotes Ocean Fronts (water mass boundaries), not oil film.
- `HM` denotes Human-Made / Anthropogenic Objects, not vessel-only.
- All future training configs, loss weight vectors, confusion matrices, and reports must adhere strictly to these 12 class names and indices under [GOV-RULE-095](file:///d:/Projects/ocean-sentinel/data/metadata/ocean_sentinel_governance_rules_v1.json).

---

## 5. Canonical Protocol Reconciliation

Audited in [ops02_c19_canonical_protocol_v1.json](file:///d:/Projects/ocean-sentinel/data/ops02/audits/ops02_c19_canonical_protocol_v1.json).

| Parameter | Level 4 Frozen Protocol | C16 Machine Truth | C18 Report Narrative | C19 Canonical Resolution | Status |
|---|---|---|---|---|---|
| **Dataset Version** | OPS02_v1.0.0_FROZEN | OPS02_v1.0.0_FROZEN | OPS02_v1.0.1_FROZEN | `OPS02_v1.0.1_FROZEN` | VERIFIED |
| **Model Architecture** | ResNet18-UNet | ResNet18-UNet | ResNet18-UNet | `ResNet18-UNet` | VERIFIED |
| **Trainable Parameters**| 14,310,860 | 14,310,860 | 14,310,860 | `14,310,860` | VERIFIED |
| **BatchNorm Layers** | 30 layers | 30 layers | 30 layers | `30 BatchNorm2d (mom=0.05)` | VERIFIED |
| **Input Dimensions** | $256 \times 256$ | $256 \times 256$ | $[1, 512, 512]$ (typo) | `[B, 1, 256, 256]` | VERIFIED |
| **Pretrained Encoder** | ImageNet-1K | ImageNet-1K | ImageNet-1K | `ImageNet-1K (TorchVision)` | VERIFIED |
| **Normalization** | $\mu=4.424, \sigma=0.469$ | $\mu=4.424, \sigma=0.469$ | $\mu=4.424, \sigma=0.469$ | `\mu=4.424158, \sigma=0.469261` | VERIFIED |
| **Optimizer** | AdamW ($\eta=5\text{e-}4, \lambda=0.01$) | AdamW ($\eta=5\text{e-}4, \lambda=0.01$) | AdamW ($\eta=3\text{e-}4, \lambda=1\text{e-}4$) | `AdamW (5e-4, wd=0.01)` | VERIFIED |
| **Gradient Clipping** | Max norm 1.0 | Max norm 1.0 | Max norm 1.0 | `max_norm=1.0 (L2)` | VERIFIED |
| **LR Scheduler** | LinearWarmupCosineAnneal | LinearWarmupCosineAnneal | CosineAnnealingLR | `LinearWarmupCosineAnneal` | VERIFIED |
| **Epoch Budget** | 30 epochs (3 warmup) | 30 epochs (stopped at 27) | 20 epochs (stopped at 14) | `30 epochs (3 warmup, 27 decay)`| VERIFIED |
| **Minibatch Size** | 8 | 8 | 8 | `8` | VERIFIED |
| **Gradient Accum.** | 2 steps | 2 steps | 1 step | `2 steps` | VERIFIED |
| **Effective Batch** | 16 | 16 | 8 | `16` | VERIFIED |
| **BatchNorm Batch** | 8 | 8 | 8 | `8` | VERIFIED |
| **Sampler** | Candidate F (70/30) | Candidate F (70/30) | Candidate F (70/30) | `Candidate F Hybrid (70/30)` | VERIFIED |
| **Sampler Draws** | 72 draws/epoch | 72 draws/epoch | 72 draws/epoch | `72 draws/epoch` | VERIFIED |
| **Sampler Seed Rule** | `seed + epoch * 1000` | `seed + epoch * 1000` | `seed + epoch` | `base_seed + epoch * 1000` | VERIFIED |
| **Early Stopping** | Patience 10 (min 15) | Triggered at Ep 27 | Stopped at Ep 14 | `patience=10, min_epoch=15` | VERIFIED |
| **Primary Metric** | `dev_mIoU_phenomena` | `dev_mIoU_phenomena` | `dev_mIoU_phenomena` | `dev_mIoU_phenomena (cls 1..11)`| VERIFIED |
| **Hardware Default** | Single GPU | Single GPU (`cuda:0`) | Single GPU (`cuda:0`) | `Single GPU (cuda:0)` | VERIFIED |

---

## 6. C16 Execution Reconstruction

Reconstructed in [ops02_c19_c16_execution_reconstruction_v1.json](file:///d:/Projects/ocean-sentinel/data/ops02/audits/ops02_c19_c16_execution_reconstruction_v1.json) directly from Kaggle stdout logs and `metrics.json`:
- **Run Identifier:** `EXP07_RUN003_SEED42` (Replicate 003, Seed 42)
- **Execution Platform:** Kaggle GPU Container (`dheeraj12237/ocean-sentinel-exp07-c16-replicate-003`, Version 4)
- **Best Epoch:** **17** (DEV mIoU = 0.049399).
  - C18's narrative claim of Epoch 4 was an erroneous transcription. At Epoch 4, DEV mIoU was 0.0272.
- **Total Epochs Trained:** **27 epochs**.
  - Early stopping triggered at Epoch 27 because no epoch surpassed Epoch 17 by $\ge 0.005$ within 10 epochs ($17 + 10 = 27$).
- **Training Time:** 120.63 seconds (~2.01 minutes, ~4.1 seconds/epoch).
- **Partition Counts Ingested:** 132 TRAIN samples, 40 DEV samples, 0 HOLDOUT samples.
- **HOLDOUT Isolation:** Access count = 0 (100% pristine).
- **Per-Class IoU at Best Epoch (Epoch 17):**
  - Background (`BG`): 0.026583
  - Atmospheric Front (`AF`): 0.000000
  - Biological Slicks (`BS`): 0.102585
  - Low Wind Area (`LWA`): 0.029385
  - Mesoscale Convection (`MCC`): 0.228572
  - Ocean Front (`OF`): 0.000510
  - Pure Ocean Wave (`POW`): 0.042972
  - Rain Cell (`RF`): 0.000000
  - Wind Streak (`WS`): 0.022378
  - Oceanic Eddy (`Eddy`): 0.013127
  - Internal Waves (`IWs`): 0.103862
  - Anthropogenic Objects (`HM`): 0.000000
  - **Macro Phenomena mIoU (Classes 1..11):** **0.049399**

---

## 7. Input-Shape Audit

Audited in [ops02_c19_input_shape_audit_v1.json](file:///d:/Projects/ocean-sentinel/data/ops02/audits/ops02_c19_input_shape_audit_v1.json):
- **Physical Tile Verification:** Manifest examination of all 212 samples in `ops02_physical_dataset_manifest_v1.json` confirmed unique dimensions are strictly `{(256, 256)}`.
- **Pre-processing Specification:** `OPS02_DATASET_FREEZE_SPEC_v1.0.1.json` mandates $10 \times 10$ block-mean aggregation from native $2560 \times 2560$ GRD imagery to a $256 \times 256$ grid.
- **Model Contract:** `src/ocean_sentinel/ml/exp07_reference.py` defines forward pass on `[B, 1, 256, 256]`.
- **Forensic Finding on `[1, 512, 512]`:** C18 narrative Section 7 mentioned `output tensor shape [1, 512, 512]`. This was an isolated typographical copy-paste error from standard UNet literature. Zero code files perform resizing; Kaggle execution throughput (17.35 samples/sec on a single T4) confirms native $256 \times 256$ processing.

---

## 8. Metric Lock

Audited in [ops02_c19_metric_lock_v1.json](file:///d:/Projects/ocean-sentinel/data/ops02/audits/ops02_c19_metric_lock_v1.json):
- **Primary Benchmark Metric:** `dev_mIoU_phenomena`
  $$\text{mIoU}_{\text{phenomena}} = \frac{1}{|\mathcal{C}_{\text{eval}}|} \sum_{c=1}^{11} \frac{\text{TP}_c}{\text{TP}_c + \text{FP}_c + \text{FN}_c}$$
- **Evaluated Classes:** Classes 1 through 11. Background (Class 0) is excluded.
- **Ground-Truth Presence:** All 11 phenomena classes exist in the 40 DEV ground-truth masks ($|\mathcal{C}_{\text{eval}}| = 11$ unconditionally).
- **Immutability Mandate:** Under [GOV-RULE-094](file:///d:/Projects/ocean-sentinel/data/metadata/ocean_sentinel_governance_rules_v1.json), the primary metric is permanently frozen and will not be altered or discarded due to poor numerical results.
- **Secondary Diagnostic Subgroups:** Permitted strictly as auxiliary reporting metrics:
  - *Dominant Subgroup* (LWA, MCC, POW; support $> 5\%$): C16 baseline = 0.100310
  - *Intermediate Subgroup* (AF, BS, WS, Eddy, IWs; support $0.5\% - 5\%$): C16 baseline = 0.048390
  - *Ultra-Sparse Subgroup* (OF, RF, HM; support $< 0.5\%$): C16 baseline = 0.000170

---

## 9. Sampler Lock

Audited in [ops02_c19_sampler_canonicalization_v1.json](file:///d:/Projects/ocean-sentinel/data/ops02/audits/ops02_c19_sampler_canonicalization_v1.json):
- **Architecture:** Candidate F Hybrid Weighted Sampler.
- **Mixture Ratio:** $70\%$ parent-cluster balanced draws $+ 30\%$ rare-phenomenon presence draws.
- **Draws per Epoch:** Exactly 72 draws.
- **Sampling Mode:** With replacement (`replacement = True`).
- **Eligible Set:** 132 samples from TRAIN split strictly (zero DEV/HOLDOUT leakage).
- **Generator Seed Formula:** $\text{seed} + \text{epoch} \times 1000$.
- **Verification:** Actual C16 execution used `seed + epoch * 1000` (recorded in `exp07_p0_c16_training_environment_v1.json`). C18 narrative omission of `* 1000` is formally corrected.

---

## 10. Loss-Weight Lock

Audited in [ops02_c19_loss_weight_canonicalization_v1.json](file:///d:/Projects/ocean-sentinel/data/ops02/audits/ops02_c19_loss_weight_canonicalization_v1.json):
- **Formula:** $w_c = \sqrt{\frac{\text{median}(f_{\text{valid}})}{f_c}}$ computed over the 8,595,330 valid pixels of the 132 OPS02 TRAIN samples (median frequency = 399,710.5).
- **Canonical Loss Weights:**
  - 0 `BG`: **0.403935**
  - 1 `AF`: **2.450546**
  - 2 `BS`: **0.876692**
  - 3 `LWA`: **0.945945**
  - 4 `MCC`: **0.648189**
  - 5 `OF`: **4.211476**
  - 6 `POW`: **0.719641**
  - 7 `RF`: **2.956203**
  - 8 `WS`: **1.064525**
  - 9 `Eddy`: **1.882870**
  - 10 `IWs`: **0.387652**
  - 11 `HM`: **18.243211**
- **Discrepancy Resolution:** C18's markdown table presented normalized sum-to-12 weights under corrupted names (`AS`, `Thermal`). The canonical unnormalized weights above match C15 prescribed weights and C16 actual executed weights to 6 decimal places.

---

## 11. Cross-Evaluation Interpretation

Audited in [ops02_c19_cross_eval_interpretation_v1.json](file:///d:/Projects/ocean-sentinel/data/ops02/audits/ops02_c19_cross_eval_interpretation_v1.json):
- **Epistemic Classification:** **OBSERVED / DESCRIPTIVE DOMAIN-TRANSFER DIAGNOSTIC**.
- **C18 Overclaim Corrected:** C18 stated that Tier 1 cross-evaluation would "directly separate" dataset distribution shift from optimization defects. This is invalid.
- **Methodological Confounding:** OPS-01 and OPS-02 differ simultaneously in sample count (72 vs 132 TRAIN), parent clusters (20 vs 64), geographic coverage, radiometric normalization ($\mu=4.28$ vs $4.42$), and loss weights ($w_{\text{HM}}=4.61$ vs $18.24$). Cross-evaluating C8/C10 and C16 cannot mathematically isolate which factor drives performance.
- **Governing Standard:** [GOV-RULE-098](file:///d:/Projects/ocean-sentinel/data/metadata/ocean_sentinel_governance_rules_v1.json) requires cross-evaluation results to be reported strictly as domain transfer behavior. Causal attribution is disallowed.

---

## 12. Repaired Diagnostic Design

### Tier 1: Zero-Compute Cross-Domain Evaluation
- **Action:** Read-only forward inference of existing checkpoints across historical DEV splits. Zero training.
  - C16 best model (`c16_replicate_003_best.pt`) evaluated on OPS-01 DEV (39 samples).
  - C8 best model (`c8_replicate_001_best.pt`) and C10 best model (`c10_replicate_002_best.pt`) evaluated on OPS-02 DEV (40 samples).
- **Compute Cost:** 0 GPU hours training (< 2 minutes local CPU/GPU inference).
- **Quarantine:** HOLDOUT strictly locked (0 access).
- **Goal:** Measure forward and backward transfer degradation across OPS-01 and OPS-02 development sets.

### Tier 2: EXP07_DIAGNOSTIC_001 (Single-Variable Controlled Training)
- **Condition:** Executed only if authorized following Tier 1 review and explicit user sign-off.
- **Independent Variable:** Loss Class Weighting Scheme.
  - *Control:* C16 Canonical Protocol with Sqrt-Median Weights ($[0.403935 \dots 18.243211]$).
  - *Treatment:* Uniform Unweighted Loss ($w_c = 1.0$ for all $c \ge 1$, $w_0 = 0.2$ for background).
- **Constant Variables (Locked to Canonical Protocol under GOV-RULE-099):**
  - Dataset: `OPS02_v1.0.1_FROZEN` (132 TRAIN, 40 DEV, 40 HOLDOUT quarantined)
  - Architecture: ResNet18-UNet (14,310,860 params, ImageNet pretrained encoder)
  - Input: $[B, 1, 256, 256]$
  - Normalization: $\mu = 4.424158, \sigma = 0.469261$
  - Optimizer: AdamW ($\eta = 5\times 10^{-4}$, $\lambda = 0.01$, max norm 1.0)
  - Scheduler: LinearWarmupCosineAnnealingLR (30 epochs, 3 warmup, $\eta_{\min} = 1\times 10^{-6}$)
  - Batch dynamics: minibatch 8, accumulation 2, effective batch 16, BN batch 8
  - Sampler: Candidate F Hybrid (70/30, 72 draws/epoch, `base_seed + epoch * 1000`)
  - Seed: 42
  - Hardware: Single Tesla T4 GPU (`cuda:0`)
- **Explicit Purging:** All C18 draft values (3e-4, 1e-4, 20 epochs, accumulation 1, effective batch 8) are permanently barred.

---

## 13. Information-Value Analysis

| Experiment | Independent Variable | Control | Treatment | Uncertainty Reduced | Risk of Inconclusive Result | Information Value |
|---|---|---|---|---|---|---|
| **Blind Replicate 004** (Seed 101/2024) | Random Seed | Seed 42 on OPS-02 | Seed 101 on OPS-02 | Minimal (produces another confounded data point without testing any mechanism). | High (likely repeats ~5% score with minor variance). | **VERY LOW / REJECTED** |
| **Tier 1 Cross-Eval** | Evaluation Domain | C16 on OPS-02 DEV; C10 on OPS-01 DEV | C16 on OPS-01 DEV; C10 on OPS-02 DEV | Quantifies bidirectional domain transfer gap between OPS-01 and OPS-02 feature distributions. | Low (zero-compute, pure observation of existing models). | **HIGH (PRE-REQUISITE)** |
| **Tier 2 Diagnostic 001** | Loss Weighting | Sqrt-Median Weights ($w_{\text{HM}}=18.24, w_{\text{BG}}=0.40$) | Uniform Unweighted ($w_c=1.0, w_0=0.2$) | Isolates whether extreme rare-class loss weighting suppressed background seawater learning and collapsed mIoU. | Low (single-variable controlled ablation on identical frozen dataset). | **VERY HIGH (IF CLEARED)** |

---

## 14. Governance Updates

Added [GOV-RULE-095 through GOV-RULE-099](file:///d:/Projects/ocean-sentinel/data/metadata/ocean_sentinel_governance_rules_v1.json) to `ocean_sentinel_governance_rules_v1.json` (Total active rules: **99**):

- **GOV-RULE-095: Canonical Taxonomy Vocabulary and Index Immutability**  
  The 12-class canonical taxonomy (0: BG to 11: HM) and its dense index assignments are permanently frozen. Unauthorized synonyms (e.g. 'AS', 'Thermal') are strictly barred from all code and reports.
- **GOV-RULE-096: Canonical Training Protocol Single-Source Authority**  
  All future training and diagnostic runs must reference the verified Level 4 frozen protocol (`EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md`) and Level 3 reference implementation (`src/ocean_sentinel/ml/exp07_reference.py`). Narrative report tables cannot alter hyperparameters.
- **GOV-RULE-097: Machine-Readable Forensic Reconstruction Priority**  
  Forensic audits of past runs must reconstruct parameters and metrics exclusively from direct machine artifacts (JSON run manifests, environment dumps, checkpoint state_dicts, execution logs). Narrative descriptions cannot override machine records.
- **GOV-RULE-098: Cross-Domain Evaluation Epistemic Standard**  
  Cross-domain evaluation across multi-variable confounded datasets provides descriptive transfer diagnostics only. Causal attribution is prohibited.
- **GOV-RULE-099: Machine-Checkable Single-Variable Isolation for Diagnostic Training**  
  Any diagnostic training experiment designed to test a causal hypothesis must vary exactly ONE independent parameter relative to control, keeping all other hyperparameters machine-checked against the canonical protocol.

---

## 15. Tests and Verification

1. **C19 Canonicalization Guardrails:** [test_exp07_p0_c19_canonicalization_guardrails.py](file:///d:/Projects/ocean-sentinel/tests/test_exp07_p0_c19_canonicalization_guardrails.py)
   - 11 test functions covering canonical taxonomy immutability, prohibition of `AS`/`Thermal`, frozen manifest bindings, exact partition membership, input dimensions ($256 \times 256$), protocol values, metric lock, C16 machine truth reconstruction, cross-evaluation epistemic classification, governance rules (99 active rules), and Tier 1 release gate.
   - **Result:** **11 PASSED** in 1.82s.
2. **Complete EXP-07 & Security Suite:**
   - Executed all 18 test files (`test_exp07_p0_c2` through `test_exp07_p0_c19` plus `test_artifact_policy.py` and `test_part_iii_firewall.py`).
   - **Result:** **297 PASSED, 0 FAILED** in 13.94s.

---

## 16. Tier-1 Release Gate

Documented in [ops02_c19_tier1_release_gate_v1.json](file:///d:/Projects/ocean-sentinel/data/ops02/audits/ops02_c19_tier1_release_gate_v1.json):
- **Verdict:** **`TIER1_AUTHORIZED_WITH_LIMITATIONS`**
- **Authorization Scope:** Tier-1 zero-compute cross-evaluation is authorized for subsequent execution in Phase C20.
- **Prohibitions Maintained:**
  - Zero model training in C19 (`training_started = false`).
  - Zero HOLDOUT access (`holdout_access = false`).
  - Zero blind replicate execution (Replicate 004 is **BLOCKED**).
  - C19 itself does not execute Tier 1; execution is deferred to the next authorized task.

---

## 17. Remaining Uncertainties

1. **True Driver of OPS-02 mIoU Collapse:** Whether the 4.94% result stems predominantly from out-of-distribution parent cluster diversity (H1/H2), severe class imbalance (H3), or loss-weight gradient instability (H7) remains an open scientific question.
2. **Transfer Degradation Symmetry:** It is currently unknown whether C16 transfers better to OPS-01 than C8/C10 transfers to OPS-02. Tier 1 cross-evaluation will provide the first empirical data on this bidirectional transfer.
3. **Sparse-Class Lower Bound:** Even under optimal loss weighting, minority classes with $< 100$ pixels on DEV may inherently exhibit high IoU variance.

---

## 18. Exact Next Authorized Action

1. **Phase C20 Authorization:** Proceed to Phase EXP-07-P0-C20 to execute **Tier 1 Zero-Compute Cross-Domain Evaluation**:
   - Run inference of C16 checkpoint (`c16_replicate_003_best.pt`) on OPS-01 DEV split.
   - Run inference of C8/C10 checkpoints (`c8_replicate_001_best.pt`, `c10_replicate_002_best.pt`) on OPS-02 DEV split.
   - Compute 12-class confusion matrices, primary `dev_mIoU_phenomena`, and secondary tiered subgroup metrics.
2. **Analysis:** Evaluate domain transfer degradation under the descriptive framework of [GOV-RULE-098](file:///d:/Projects/ocean-sentinel/data/metadata/ocean_sentinel_governance_rules_v1.json).
3. **Decision Point:** If Tier 1 transfer metrics indicate severe optimization distortion from loss weighting, submit proposal to user for executing Tier 2 (`EXP07_DIAGNOSTIC_001`).
4. **Firewall:** Maintain strict zero access to the HOLDOUT partition.

---

## 19. Git / Process Self-Audit

- **Python Background Processes:** 0 running.
- **Git State:** Clean branch `master`. Zero staged changes, zero commits, zero pushes, zero checkouts, zero branch switches, zero stashes, zero file deletions.
- **Tracked Modifications Preserved:** Only the two pre-existing files (`.gitignore` and `src/ocean_sentinel/ingestion/dataset.py`) remain in modified state.
- **Historical Reports:** C8, C10, C16, C17, C18 markdown reports preserved unmodified.
- **Part-III Quarantine:** 100% verified; zero leakage.
- **Telemetry State:** [scratch/exp07_p0_c19_run_state.json](file:///d:/Projects/ocean-sentinel/scratch/exp07_p0_c19_run_state.json) synchronized and marked `COMPLETED`.

---

### Epistemic Assessment Summary
- **C16 Performance Metric (0.049399 mIoU at Epoch 17):** OBSERVED & VERIFIED FROM MACHINE TRUTH
- **Physical Dataset 256x256 Dimensions:** OBSERVED & VERIFIED FROM ALL 212 SAMPLES
- **Canonical Taxonomy (AF, BS, LWA, MCC, OF, POW, RF, WS, Eddy, IWs, HM):** VERIFIED & LOCKED
- **Canonical Training Protocol (AdamW 5e-4, wd 0.01, 30 ep, accum 2, eff bs 16):** VERIFIED & RESTORED
- **Cross-Domain Evaluation Role:** DESCRIPTIVE DOMAIN TRANSFER DIAGNOSTIC (NON-CAUSAL)
- **Single-Variable Controlled Training Necessity:** SUPPORTED
