# EXP-07-P0-C6: Controlled CPU End-to-End Integration Validation and Pre-Training Audit

**Phase:** EXP-07-P0-C6  
**Date:** 2026-09-13  
**Status:** COMPLETE  
**Decision:** **A. FINAL — EXP-07 PRE-TRAINING CPU INTEGRATION GATE PASSED**  
**Next Authorized Action:** **EXP-07-P0-C7 — TRAINING READINESS REVIEW / FINAL EXPERIMENT EXECUTION GATE**

---

## Executive Summary

Phase **EXP-07-P0-C6** conducted the final controlled CPU integration gate before any EXP-07 model training is permitted. Operating under strict CPU-only constraints (**zero GPU usage, zero model parameter updates, zero optimizer steps, zero checkpoints created, zero Part-III access, and zero Git staging/commits**), this phase executed an adversarial contract audit and end-to-end dry-run across the complete software and data pipeline:

$$\text{Authoritative Manifest} \longrightarrow \text{Dataset Reader} \longrightarrow \text{Taxonomy Remap} \longrightarrow \text{Validity Mask} \longrightarrow \text{Log1p Transform} \longrightarrow \text{Standardization} \longrightarrow \text{DataLoader} \longrightarrow \text{ResNet18-UNet} \longrightarrow \text{Logits} \longrightarrow \text{Loss} \longrightarrow \text{Argmax} \longrightarrow \text{Confusion Matrix} \longrightarrow \text{Metrics}$$

### Core Scientific Findings & Epistemic Resolutions

1. **Input-Domain Radiometric Terminology Resolution (GOV-RULE-060 / INC-P0-C6-001):**
   Prior documentation described the runtime input pathway using the upstream validation title `EMPIRICALLY_CHARACTERIZED_APPROXIMATE_CALIBRATION_PATHWAY`. However, code and filesystem inspection confirmed that the runtime loader ingests raw, spatially aggregated Sentinel-1 GRD detected pixel DN values (uncalibrated detector counts) transformed via $\log(1 + DN)$ and fixed standardization. No calibration lookup tables ($A_\sigma$) or physical squaring ($DN^2$) are evaluated at runtime. The input domain has been formally designated **`AGGREGATED_RAW_DN_LOG1P_STANDARDIZED`**. Describing uncalibrated DN as physical backscatter ($\sigma^0, \gamma^0, \beta^0$) is strictly prohibited under new permanent rule `GOV-RULE-060`.
2. **First-Principles Independent Recomputations (GOV-RULE-061):**
   To eliminate self-referential validation ("function agrees with itself"), independent first-principles recomputations were executed for input normalization ($100\%$ agreement), weighted cross-entropy loss (within $4.20 \times 10^{-7}$ of PyTorch loss), $12 \times 12$ confusion matrix ($100\%$ bitwise agreement), per-class IoU ($100\%$ agreement), and Candidate F hybrid sampling distribution ($100\%$ bitwise agreement).
3. **Loss Frequency Recalculation directly from Physical Rasters:**
   Auditing uncovered that in C4, the numerator for Background (BG) frequency had included $6,510$ invalid border padding pixels from raw manifest annotations ($1,957,266$ raw BG vs $1,950,756$ valid BG), while dividing by the valid pixel denominator ($4,712,082$). Recalculating strictly from physical valid masks ($DN > 0$) established exact class frequencies summing to $1.00000000$, yielding an exact median frequency of $0.03090704$ and bounding square-root median-frequency weights between $0.273233$ (BG) and $12.159536$ (HM) (ratio: $44.5024\text{x}$). Zero pixels from DEV or HOLDOUT contributed to weights.
4. **Excluded Class Quarantine and Collision Prevention:**
   Physical masks in DEV ($4$ tiles, $261,120$ pixels) and HOLDOUT ($3$ tiles, $195,840$ pixels) contain non-eligible Class 9 (`Sea Ice`, `SI`). Explicit dense remapping maps classes 3 (`IB`), 9 (`SI`), and 14 (`OS`) to `ignore_index = -100`. Tests verified that source 9 never collides with dense class 9 (`Eddy`, source 11), and unknown source labels fail loudly with `ValueError`.
5. **Controlled CPU Dry-Run Execution:**
   Forward passes across minibatches of TRAIN, DEV, and HOLDOUT executed with zero errors, zero NaNs, and zero parameter mutations. Average batch loss was verified finite ($2.4035$ TRAIN, $2.5192$ DEV, $2.3964$ HOLDOUT).
6. **Regression Guardrails:**
   $31$ new integration tests passed ($100\%$). Combined with predecessor suites (C5: 25, C4: 25, C3: 35, C2: 41), a total of **157 regression tests** passed with zero failures and zero skips.

---

## 1. Fresh Preflight and Provenance Hashes

Preflight verified clean repository state:
- Branch: `master`
- Staged changes: `0`
- Tracked modified: `2` (`.gitignore`, `src/ocean_sentinel/ingestion/dataset.py` from earlier phases)
- Untracked files: preserved without deletion (`untracked != disposable` under GOV-RULE-032).

Authoritative frozen hashes independently verified via SHA-256:
- **EXP-06 Best Model:** `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` (OK)
- **Part-I Development Split Manifest:** `17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072` (OK)
- **OPS-01 Physical Dataset Manifest v4:** `FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E` (OK)

---

## 2. Critical Audit #1 — DN vs "Calibration" Semantic Mismatch

### Problem Statement
Earlier documentation used the phrase `EMPIRICALLY_CHARACTERIZED_APPROXIMATE_CALIBRATION_PATHWAY`. This wording risked implying that a physical calibration equation was executed on the fly or that model inputs represent radar backscatter ($\sigma^0, \gamma^0$).

### Empirical Evidence & Code Verification
Inspection of `src/ocean_sentinel/ml/exp07_reference.py` and OPS-01 GeoTIFF rasters confirmed:
1. Physical tiles store 10x10 block-averaged Sentinel-1 Level-1 GRD detected pixel DN counts (`uint16`).
2. The runtime preprocessing pipeline evaluates:
   $$\text{validity\_mask} = \text{raw} > 0$$
   $$\hat{x} = \frac{\log(1 + \text{raw}) - 4.2756}{0.3866}$$
   $$\hat{x}[\neg \text{validity\_mask}] = 0.0$$
3. No calibration vector ($A_\sigma$) is loaded or applied.
4. No amplitude squaring ($DN^2$) occurs.

### Resolution & Governance
Model inputs are strictly **uncalibrated aggregated raw Sentinel-1 GRD detected DN values transformed with log1p and standardization**.
The C3 calibration-order investigation remains valid as an empirical characterization of nonlinear Jensen bias ($\sim 5.5\%$ median error) between aggregated DN and true backscatter, but it is not a runtime calibration step.
Enacted **`GOV-RULE-060`**: Runtime input-domain terminology must distinguish raw uncalibrated DN, physical backscatter, and model-space representation.

---

## 3. Critical Audit #2 — Validity Masking, Transform, and Target Ignore

The execution order and semantics of validity masking were audited against 6 critical questions:

| Question | Analysis | Classification |
|---|---|---|
| **1. Are invalid pixels guaranteed not to contribute to normalization statistics?** | Normalization constants $\mu=4.2756, \sigma=0.3866$ were derived strictly from the $4,712,082$ valid pixels ($DN > 0$) of TRAIN. Border padding ($6,510$ pixels) was excluded. Constants are immutable in reference code. | **KNOWN AND ACCEPTED** |
| **2. Can invalid values influence convolutional receptive fields?** | Border padding pixels are set to $0.0$ after standardization. Convolution kernels overlapping the valid/invalid boundary include $0.0$ in their dot products. Receptive fields near the border experience standard CNN edge effects, identical to spatial boundary padding. | **KNOWN AND ACCEPTED** |
| **3. Is setting invalid input pixels to 0.0 after standardization distinguishable from setting before?** | Yes. Before transform: $DN=0 \implies \log(1+0)=0 \implies (0-4.2756)/0.3866 = -11.06$. Clamping to $0.0$ *after* standardization sets padding to the normalized feature mean ($z=0.0$), preventing massive negative feature spikes. | **KNOWN AND ACCEPTED** |
| **4. Can a normalized valid value legitimately equal the numeric 0.0 sentinel?** | Yes. A valid pixel with $DN \approx 71$ yields $\log(1+71) \approx 4.2767 \implies \hat{x} \approx 0.003$. Model input is 1-channel, but the target mask explicitly uses `-100`, preventing loss supervision on invalid pixels. | **KNOWN AND ACCEPTED** |
| **5. Does the model receive a separate validity channel?** | The model input contract is strictly 1-channel `[B, 1, 256, 256]`. It does not receive a second validity channel in baseline. | **DOCUMENTED LIMITATION** |
| **6. Can invalid border pixels indirectly affect predictions near the boundary?** | Yes, through convolutional receptive field overlap within boundary margins. Valid pixels near the border may have slight boundary modulation, but loss and metrics mask them out completely. | **KNOWN AND ACCEPTED** |

---

## 4. Critical Audit #3 — Excluded Classes & Taxonomy Protection

An exhaustive census across all 147 physical masks confirmed:
- **Class 3 (`IB`, Iceberg):** $0$ tiles, $0$ pixels in TRAIN, DEV, and HOLDOUT.
- **Class 9 (`SI`, Sea Ice):**
  - TRAIN: $0$ tiles, $0$ pixels.
  - DEV: $4$ tiles, $261,120$ valid pixels.
  - HOLDOUT: $3$ tiles, $195,840$ valid pixels.
  - Total: $7$ tiles, $456,960$ pixels.
- **Class 14 (`OS`, Mineral Oil Spill):** $0$ tiles, $0$ pixels in TRAIN, DEV, and HOLDOUT.

### Collision Prevention & Loud Failure
`remap_source_mask_to_dense` enforces:
1. Eligible source classes map to dense $0..11$.
2. Source 9 (`Sea Ice`) maps strictly to `ignore_index = -100`. Dense class 9 is strictly `Oceanic Eddy` (source 11).
3. Any label outside $0..14$ raises `ValueError(f"Corrupted or unknown source label IDs found in mask: ...")`, preventing silent conversion to Background.

---

## 5. Critical Audit #4 — Loss Frequencies Recalculated from Source Rasters

Recalculating directly from the 72 physical TRAIN GeoTIFF rasters and validity masks:
- **Total Valid Pixels:** $4,712,082$
- **Total Invalid Border Pixels:** $6,510$
- **DEV/HOLDOUT Contribution:** Exactly $0$ pixels.

### Canonical Class Accounting & Weights

| Dense ID | Abbr | Class Name | Valid Pixels | Exact Frequency | Sqrt-Median Weight |
|---|---|---|---|---|---|
| **0** | `BG` | Background Seawater | 1,950,756 | 0.41399025 | **0.273233** |
| **1** | `AF` | Atmospheric Front | 35,931 | 0.00762529 | **2.013263** |
| **2** | `BS` | Biological Slicks | 293,888 | 0.06236903 | **0.703954** |
| **3** | `LWA` | Low Wind Area | 23,424 | 0.00497105 | **2.493473** |
| **4** | `MCC` | Mesoscale Cellular Convection | 547,092 | 0.11610409 | **0.515947** |
| **5** | `OF` | Ocean Front | 67,425 | 0.01430896 | **1.469686** |
| **6** | `POW` | Pure Ocean Wave | 554,669 | 0.11771209 | **0.512411** |
| **7** | `RF` | Rain Cell / Rain Footprint | 63,801 | 0.01353987 | **1.510850** |
| **8** | `WS` | Wind Streak | 223,848 | 0.04750512 | **0.806601** |
| **9** | `Eddy` | Oceanic Eddy | 34,110 | 0.00723884 | **2.066304** |
| **10** | `IWs` | Internal Waves | 916,153 | 0.19442637 | **0.398704** |
| **11** | `HM` | Artificial / Anthropogenic Objects | 985 | 0.00020904 | **12.159536** |

- **Median Frequency:** $0.03090704$
- **Max Weight:** $12.159536$ (`HM`)
- **Min Weight:** $0.273233$ (`BG`)
- **Max / Min Weight Ratio:** $44.5024\text{x}$

---

## 6. Critical Audit #5 — Sampler Mathematics (Candidate F Hybrid)

Candidate F combines a parent-balanced component and a class-presence component into a stationary probability distribution sampled with replacement:

$$P_{\text{hybrid}}(i) = 0.70 \cdot P_{\text{parent}}(i) + 0.30 \cdot P_{\text{presence}}(i)$$

### Mathematical Verification
1. $\sum_{i=1}^{72} P_{\text{parent}}(i) = 1.000000000000$ (each of the 12 parents receives exactly $1/12$ total probability; within parent $p$, each tile receives $1/(12 \cdot N_p)$).
2. $\sum_{i=1}^{72} P_{\text{presence}}(i) = 1.000000000000$ (each tile scored by sum of inverse class tile counts).
3. $\sum_{i=1}^{72} P_{\text{hybrid}}(i) = 1.000000000000$.
4. Expected parent exposure per epoch (mean = 6.000): min = 4.282, max = 8.221 (max parent multiplier = $1.3701\text{x}$, well within $1.45\text{x}$ threshold; parent CV = $0.221$).
5. Rare class exposure per epoch: `HM` = 3.82 tiles/epoch, `LWA` = 3.10 tiles/epoch, `Eddy` = 4.19 tiles/epoch (all $\ge 3.0$ tiles/epoch).
6. Deterministic replay: fixed PyTorch Generator seed 42 produces identical draw sequences across independent runs. Different seeds (e.g. 43) produce distinct sequences.
7. Tile replacement: an epoch of 72 draws draws 37 unique tiles under seed 42, confirming replacement semantics.

---

## 7. Critical Audit #6 — Dataset Partition Integrity

Authoritative manifest `ops01_physical_dataset_manifest_v4.json` verification:
- **TRAIN:** 72 tiles / 12 parent scenes
- **DEV:** 39 tiles / 7 parent scenes
- **HOLDOUT:** 36 tiles / 8 parent scenes
- **Total:** 147 physical tiles / 27 parent scenes

Cross-Partition Disjointness:
- Parent scenes: pairwise disjoint ($\text{TRAIN} \cap \text{DEV} = \emptyset$, $\text{TRAIN} \cap \text{HOLDOUT} = \emptyset$, $\text{DEV} \cap \text{HOLDOUT} = \emptyset$).
- Image file hashes: zero duplicate image bytes across partitions.
- Mask file hashes: zero duplicate mask bytes across partitions.
- All 147 image paths and 147 mask paths exist and match SHA-256 hashes exactly.

---

## 8. Critical Audit #7 — Golden Sample Cryptographic Benchmarks

Golden samples were reconstructed from raw files across independent process boundaries:

| Split | Sample ID | Raw Dtype / Shape | Valid Px | Raw Mean | Norm Mean | Norm Image SHA-256 | Target Mask SHA-256 |
|---|---|---|---|---|---|---|---|
| **TRAIN** | `...004712-005d33-001-7` | float32 / (256, 256) | 65,536 | 131.1164 | 1.4391 | `2850D42E1191318184A64D06FC000F5DAAA22126DC564EAED2B345AF5BD8AEB7` | `380D55AB98A4F71814DCE01173528154D380E3C0951AE1710F19D87C6DE4DF3D` |
| **DEV** | `...019990-0220c9-001-3` | float32 / (256, 256) | 65,536 | 111.1231 | 1.0328 | `E5C455C0A8FF8C7C4C75882C44B37C6076E16C7A8020969BA09D047CC5BFC14F` | `EC663C1A4E794684F63E54D7E2DBD5BC7FED20AE95EB362A69592F1FBFC51EB3` |
| **HOLDOUT** | `...046987-05a2c5-001-58` | float32 / (256, 256) | 65,536 | 91.6570 | 0.5819 | `C8E8598DAD3A444F07E73104BF0BA1FF426E38A3FAEA70FB5EA326AA096DE557` | `960A91A637DCBB333EAB2AC3F27CDBC6892B6483908E3D7D7F52037CEC31DD25` |

*Note on HOLDOUT:* Target mask unique labels are `[-100, 0]`. Sea Ice (source label 9) is safely remapped to `-100` (`ignore_index`).

---

## 9. Critical Audit #8 & #9 — BatchNorm Semantics and DataLoader Determinism

### BatchNorm Option B Semantics (GOV-RULE-059)
- Physical minibatch: 8 samples.
- Gradient accumulation: 2 steps.
- Effective optimization batch size: 16 samples.
- BatchNorm statistical evaluation window: strictly 8 samples per forward pass.
- Train vs Eval verification:
  - In `model.eval()`, `running_mean`, `running_var`, and `num_batches_tracked` remain strictly frozen.
  - In `model.train()`, each forward pass increments `num_batches_tracked` by 1 and updates running statistics over that specific 8-sample minibatch.
  - Gradient accumulation aggregates loss gradients over 2 backward passes; it executes 2 distinct 8-sample updates to BatchNorm, NOT a single 16-sample update.
  - Batches per epoch: 9 physical forward passes per epoch. Running stats evolve smoothly via `momentum = 0.05`.

### DataLoader Determinism
- Under `num_workers = 0`, DataLoader operates synchronously in the main process, achieving 100% bitwise identical sample batch sequences across repeated runs.
- Windows multiprocessing (`num_workers > 0`) spawns child interpreters that encounter function pickling and rasterio context hazards. Therefore, `num_workers = 0` is frozen as the mandatory reference contract.

---

## 10. Critical Audit #10 & #11 — Model Architecture & Metrics Contracts

### ResNet18-UNet Architecture
- Trainable parameters: **14,310,860**
- Floating-point buffers: **11,776** (30 BatchNorm layers $\times 2$)
- Integer scalar buffers: **30** (`num_batches_tracked`)
- Total state size: **14,322,666** tensors
- Input contract: `[B, 1, 256, 256]` float32
- Output contract: `[B, 12, 256, 256]` float32 raw logits (no softmax or sigmoid inside head)

### Metrics Evaluation
- Prediction rule: strictly $\text{argmax}(\text{logits}, \text{dim}=1)$.
- Ignored pixels (`-100`) and border padding (`validity_mask == False`) are strictly masked out of the $12 \times 12$ confusion matrix.
- Absent classes ($GT_c = 0$) return `IoU = None` and are cleanly excluded from macro denominators.
- Dual metric reporting:
  - `mIoU_phenomena`: Macro IoU across present phenomenon classes ($1..11$, excluding Background). Primary scientific metric.
  - `mIoU_all`: Macro IoU across all present classes ($0..11$, including Background).

---

## 11. Controlled CPU End-to-End Dry-Run

The complete integration pipeline was exercised on CPU across minibatches from all three partitions in strictly evaluation mode:

```
TRAIN DRY-RUN (8 samples):
  Avg Loss: 2.4035
  mIoU_all: 0.0916
  mIoU_phenomena: 0.0000
  Present classes (all): 6
  Present classes (phenomena): 5

DEV DRY-RUN (8 samples):
  Avg Loss: 2.5192
  mIoU_all: 0.0631
  mIoU_phenomena: 0.0000
  Present classes (all): 6
  Present classes (phenomena): 5

HOLDOUT DRY-RUN (8 samples):
  Avg Loss: 2.3964
  mIoU_all: 0.3248
  mIoU_phenomena: 0.0000
  Present classes (all): 3
  Present classes (phenomena): 2
```

- Zero NaNs, zero Infs, zero exceptions.
- Zero model parameter updates, zero optimizer steps, zero checkpoints saved.

---

## 12. Independent First-Principles Cross-Checks (GOV-RULE-061)

| Verification Item | Reference Implementation | Independent First-Principles Implementation | Agreement Status |
|---|---|---|---|
| **Input Normalization** | `preprocess_sar_image()` | Pure NumPy double loop with log1p & standardization | **100% Agreement** |
| **CrossEntropy Loss** | `create_exp07_loss()` | Pure NumPy manual softmax + weighted negative log-likelihood with ignore index | **Agreement within $4.20 \times 10^{-7}$** |
| **Confusion Matrix** | `compute_confusion_matrix_12x12()` | Pure Python loop bincount over valid coordinate pairs | **100% Bitwise Agreement** |
| **Per-Class IoU** | `compute_metrics_from_confusion_matrix()` | Manual formula $TP / (TP + FP + FN)$ | **100% Agreement** |
| **Candidate F Vector** | `compute_candidate_f_hybrid_weights()` | Independent formula combination of parent and presence probabilities | **100% Bitwise Agreement ($0.00\text{e}+00$)** |

---

## 13. Future Risk Register Summary (40 Risks Audited)

All 40 future risks identified in the contract audit were cataloged and verified in `data/metadata/exp07_p0_c6_risk_register_v1.json`:
- **Guardrails:** 22 risks mitigated by automated code constraints and governance rules.
- **Tests:** 14 risks verified by automated regression test assertions.
- **Documented Limitations:** 4 risks bounded by explicit epistemic disclosures (small-batch BN variance, uncalibrated DN representation, single-process worker contract, and CPU algorithmic replay scope).

---

## 14. Incident and Governance Learning

### Incident Logged: `INC-P0-C6-001`
- **Title:** Runtime input domain terminology mismatch (uncalibrated aggregated DN vs calibration pathway)
- **Root Cause:** Upstream documents designated the runtime input pipeline using the title of the calibration aggregation research study, rather than the literal mathematical operations performed on model inputs.
- **Corrective Action:** Formally classified runtime input domain as `AGGREGATED_RAW_DN_LOG1P_STANDARDIZED`. Enacted `GOV-RULE-060` and `GOV-RULE-061`.
- **Status:** `RESOLVED`.

### Governance Rules Enacted
- **`GOV-RULE-060` (Metrological Discipline):** Runtime input-domain terminology must distinguish raw uncalibrated DN, physical backscatter, and model-space representation.
- **`GOV-RULE-061` (Verification Discipline):** Independent recomputation is mandatory for high-impact pipeline validation.

Total rules in repository governance register: **61**.

---

## 15. Test Suite Verification

Pytest execution results across all 5 regression suites:
- `tests/test_exp07_p0_c6_integration_guardrails.py`: **31 passed**
- `tests/test_exp07_p0_c5_implementation_guardrails.py`: **25 passed**
- `tests/test_exp07_p0_c4_protocol_freeze_guardrails.py`: **25 passed**
- `tests/test_exp07_p0_c3_cpu_validation_guardrails.py`: **35 passed**
- `tests/test_exp07_p0_c2_final_plan_guardrails.py`: **41 passed**

**Total:** **157 passed, 0 failed, 0 skipped** across all 5 test suites.

---

## 16. Final Decision & Next Action Boundary

### Final Decision
**`A. FINAL — EXP-07 PRE-TRAINING CPU INTEGRATION GATE PASSED`**

All static audits, mathematical contracts, data integrity checks, and CPU dry-runs passed with complete fidelity to frozen governance.

### Authorization Boundary
**NO ACTUAL MODEL TRAINING IS AUTHORIZED BY THIS DECISION.**
Zero optimizer steps were performed. Zero weights were updated. Zero checkpoints were saved. Zero GPU operations occurred. Zero Part-III files were accessed.

### Next Authorized Phase
**`EXP-07-P0-C7 — TRAINING READINESS REVIEW / FINAL EXPERIMENT EXECUTION GATE`**
Phase C7 must separately review training readiness (seed schedules, learning rate warmup/decay, early stopping, checkpoint retention policy, failure recovery, monitoring telemetry, and compute budget) before any experiment execution is authorized.
