# EXP-07-P0-C22-C — POST-RUN FORENSIC AUDIT, RESULT VALIDATION, SCIENTIFIC INTERPRETATION REPAIR & REPLICATION READINESS
**Date:** 2026-09-14  
**Task ID:** EXP-07-P0-C22-C  
**Parent Experiment:** EXP-07-P0-C22-B / EXP07_DIAG01  
**Project:** Ocean Sentinel (`D:\Projects\ocean-sentinel`)  
**Branch:** `master`  
**Classification:** `VALID_SINGLE_RUN_OBSERVATION`

---

## 1. Executive Summary & Audit Scope

Task **EXP-07-P0-C22-C** conducted an exhaustive post-run forensic audit of the completed C22-B paired training experiment (`EXP07_DIAG01`). The audit verified all raw machine-readable artifacts, recomputed numerical metrics from source tensors, audited single-variable isolation, excised unsupported causal/background claims, corrected taxonomy drift, permanently updated the repository learning framework, and formulated a defensible multi-seed replication protocol.

### Key Audit Verdicts
1. **Numerical Accuracy:** Every reported numerical metric reconciles bitwise to raw JSON artifacts in `experiments/EXP-07/runs/EXP07_DIAG01/`.
2. **Pair Integrity:** Control and Treatment differed strictly in the preregistered 12-element loss weight vector. All 14 other operational parameters were bitwise/configuration matches.
3. **Scientific Interpretation Calibrated:** Speculative causal mechanisms regarding boundary degradation and unverified background-loss attributions were formally excised and replaced with evidence-calibrated statements.
4. **Taxonomy Preserved:** Corrected informal aliases for Class 11 (`Artificial / Anthropogenic Objects (HM)`) and Class 5 (`Oceanic Front (OF)`).
5. **Durable Safeguards Installed:** Six new lessons (`LL-C22B-001` through `LL-C22B-006`) catalogued with active regression test protection.
6. **Final Classification:** Classified as **`VALID_SINGLE_RUN_OBSERVATION`**. Uniform loss is **NOT** declared a new canonical protocol pending multi-seed replication.

---

## 2. Phase 1: Artifact Identity & Cryptographic Integrity

All raw artifacts in `experiments/EXP-07/runs/EXP07_DIAG01/` were independently hashed and verified against the runtime manifest:

| Artifact Filename | Description | Verified SHA-256 Checksum | Match Status |
| :--- | :--- | :--- | :---: |
| `control_best_model.pt` | Control checkpoint at best epoch (Ep 10) | `FF98D4A93660BC70016FEEAF2F04450B7AC1110226DECBAE027F71FF286633FA` | **MATCH** |
| `control_last_model.pt` | Control checkpoint at final epoch (Ep 20) | `079A476F86BA581AE15F2FA7F2E4DAA274BF9D38C63358800E3C84B03B73B9C1` | **MATCH** |
| `control_history.json` | Control 20-epoch training and validation logs | `699B2B01D713EE40AD0801E318B87DBF1174290D5B5239601236CA0D8C496DA3` | **MATCH** |
| `control_metrics.json` | Control summary metrics and best evaluations | `07B43F8B8959A8EDB2B0F5155E2A1BB65A7C717160B8A3B5AE64C73C06AB4D69` | **MATCH** |
| `treatment_best_model.pt` | Treatment checkpoint at best epoch (Ep 5) | `0B7F51B1E902AAC9DF839D2864F1E9658F3B0631813FC47D8ADA1738FFC47745` | **MATCH** |
| `treatment_last_model.pt` | Treatment checkpoint at final epoch (Ep 15) | `4AFE95A823BE69A4DF4921BAE394C0F846B239728524B1C2704D37754E117573` | **MATCH** |
| `treatment_history.json` | Treatment 15-epoch training and validation logs | `020BF4F22147E03F370B80A53F00B31264F4F6DEFF1A037E7CBBB85B0ED2A420` | **MATCH** |
| `treatment_metrics.json` | Treatment summary metrics and best evaluations | `5397F75CC0CC03874C2262AF233024BFB7602B60ACC3DEBAA1BF1378217D810D` | **MATCH** |
| `exp07_diag01_paired_comparison.json` | Level 5 machine-readable paired comparison | `18CE7AD59694FE3FC90BEC831527043E2331B2A3A5D8F3AB7814465F7EE418F9` | **MATCH** |
| `exp07_diag01_manifest.json` | Runtime output manifest | `20E6CFBCD2CA2799F990CE818DF9DCBB646CBA870C74688864B9A213ACBA93F2` | **MATCH** |

HOLDOUT and Part III payload access counts: **0**.

---

## 3. Phase 2: Numerical Reconciliation

Recomputing directly from `control_history.json` and `treatment_history.json` confirms all summary metrics:
- **Control Best `dev_mIoU_phenomena`:** `0.04147` at **Epoch 10**
- **Treatment Best `dev_mIoU_phenomena`:** `0.05318` at **Epoch 5**
- **Absolute Delta ($\text{Treatment} - \text{Control}$):** `+0.01171`
- **Relative Difference:** $+28.24\%$ computed via $\frac{0.01171}{0.04147} \times 100\%$

### Per-Class Metrics and Denominator Sensitivity Audit
| Class Acronym | Canonical Class Name | Control IoU (Ep 10) | Treatment IoU (Ep 5) | Absolute Delta | Percentage Assessment / Stability |
| :---: | :--- | :---: | :---: | :---: | :--- |
| *BG* | *Background (Excluded)* | *0.01198* | *0.00502* | *-0.00696* | *-58.10% (Descriptive only)* |
| AF | Atmospheric Front | 0.00005 | 0.00000 | -0.00005 | -100.00% (Near-zero baseline $5\times 10^{-5}$) |
| BS | Boundary Slick | 0.04431 | 0.09515 | **+0.05084** | **+114.74% (Substantial baseline)** |
| LWA | Low Wind Area | 0.00068 | 0.00549 | **+0.00481** | **+707.35% (Elevated by small baseline)** |
| MCC | Macro-algal Canopy / Coral | 0.26843 | 0.21160 | -0.05683 | -21.17% (Substantial baseline) |
| OF | Oceanic Front | 0.00043 | 0.00011 | -0.00032 | -74.42% (Near-zero baseline $0.00043$) |
| POW | Polar Oceanic Wind | 0.02849 | 0.00295 | -0.02554 | -89.65% (Substantial baseline) |
| RF | Rain Footprint | 0.00000 | 0.00000 | 0.00000 | **UNDEFINED (Zero baseline)** |
| WS | Wind Slick | 0.01544 | 0.00000 | -0.01544 | -100.00% (Substantial baseline) |
| Eddy | Eddy | 0.00201 | 0.00639 | **+0.00438** | **+217.91% (Elevated by small baseline)** |
| IWs | Internal Waves | 0.09634 | 0.26326 | **+0.16692** | **+173.26% (Substantial baseline)** |
| HM | Artificial / Anthropogenic Objects | 0.00000 | 0.00000 | 0.00000 | **UNDEFINED (Zero baseline)** |

**Safeguard Rule Applied:** For classes with zero baselines (RF, HM), percentages are mathematically undefined. For classes with baselines $< 0.001$ (AF, LWA, OF, Eddy), relative percentage changes are numerically hypersensitive. Absolute IoU delta is the sole reliable indicator.

---

## 4. Phase 3: Paired Single-Variable Isolation Proof

To prove single-variable isolation, every operational condition between Control and Treatment was programmatically compared:

```
====================================================================================================
PARAMETER                              CONTROL VALUE           TREATMENT VALUE         STATUS
====================================================================================================
Loss Weight Vector                     [0.403935, ..., 18.24]  [1.0, 1.0, ..., 1.0]    DIFFERENCE (Expected)
Initial State Model Checkpoint         67181C4ECD420DE...      67181C4ECD420DE...      MATCH
Initial Tensor State Fingerprint       B472DBA86C0AA9C...      B472DBA86C0AA9C...      MATCH
Dataset Specification                  OPS02_v1.0.1_FROZEN     OPS02_v1.0.1_FROZEN     MATCH
Physical Manifest SHA-256              F5480EA2E26AF8D...      F5480EA2E26AF8D...      MATCH
TRAIN Partition Sample Count           132                     132                     MATCH
DEV Partition Sample Count             40                      40                      MATCH
Candidate F Schedule SHA-256           2B1562E33FF32F7...      2B1562E33FF32F7...      MATCH
Optimizer & Weight Decay Rules         AdamW (lr=5e-4, wd=0.01)AdamW (lr=5e-4, wd=0.01)MATCH
Scheduler Configuration                Cosine Anneal (Tmax=30) Cosine Anneal (Tmax=30) MATCH
Batch Dynamics & Accumulation          phys=8, accum=2, vir=16 phys=8, accum=2, vir=16 MATCH
Augmentation                           DISABLED                DISABLED                MATCH
Stopping Rule & Bounds                 max=30, min=15, pat=10  max=30, min=15, pat=10  MATCH
Primary Monitored Metric               dev_mIoU_phenomena      dev_mIoU_phenomena      MATCH
Hardware Acceleration Worker           Tesla T4 (CUDA 12.8)    Tesla T4 (CUDA 12.8)    MATCH
====================================================================================================
```
**Conclusion:** Exactly one difference exists between Control and Treatment: the loss weight vector. Single-variable experimental isolation is strictly verified.

---

## 5. Phase 4 & 5: Scientific Interpretation & Loss Attribution Corrections

### Excised / Calibrated Statements
1. **Unsubstantiated Spatial Boundary Mechanism:**
   - *Previous Prose:* "Heavy inverse-frequency weighting penalizes prevalent phenomena, degrading boundary resolution and retarding convergence."
   - *Correction:* Replaced with evidence-calibrated language:
     > "Under the frozen OPS-02 protocol, the weighted-loss control produced lower peak DEV mIoU than the uniform-loss treatment in this paired run. The observed class-level pattern is consistent with the intervention changing optimization emphasis, but the specific mechanism affecting boundary resolution or convergence is not established by this experiment."
2. **Unsupported Background Loss Attribution:**
   - *Previous Prose:* "Treatment experienced higher penalty on background."
   - *Correction:* Excised completely. Aggregate DEV cross-entropy loss is an unweighted average over all valid pixels; without a dedicated class-wise loss decomposition artifact, attributing overall loss differences specifically to background is mathematically unsupported.

---

## 6. Phase 6: Canonical Taxonomy & Terminology Firewall

All occurrences of non-canonical shorthand and lookalike aliases were audited:
- **Class 11:** Strictly **Artificial / Anthropogenic Objects (HM)**. Forbids "Heavy Metal", "Marine Vessel", "Vessel", "Ship".
- **Class 5:** Strictly **Oceanic Front (OF)**. Forbids "Oil Spill", "Oil Film".
- **Class 2:** Strictly **Boundary Slick (BS)**. Forbids "Oil Slick".

Automated test `test_canonical_taxonomy_no_illegal_aliases` in `tests/test_exp07_p0_c22c_postrun_guardrails.py` now enforces zero illegal taxonomy aliases in reports.

---

## 7. Phase 7 & 8: Calibrated Evidence Hierarchy & Model Selection Context

### Hierarchy of Evidence for EXP07_DIAG01
- **OBSERVED (Level 5 Machine Proof):**
  - Uniform weighting achieved a higher peak `dev_mIoU_phenomena` ($0.05318$) than canonical inverse-frequency weighting ($0.04147$) in this paired run on Seed 42.
  - The $+0.01171$ delta was driven by large gains on Internal Waves ($+0.16692$) and Boundary Slicks ($+0.05084$), while Control outperformed Treatment on Macro-algal Canopy ($0.26843$ vs $0.21160$) and Polar Oceanic Wind ($0.02849$ vs $0.00295$).
  - Rare classes RF and HM scored $0.0$ IoU in both models.
- **SUPPORTED BY EVIDENCE:**
  - Class weighting acts as an empirical trade-off across categories rather than a uniform performance booster.
  - Sqrt-median-frequency weighting down-weights high-prevalence oceanic phenomena in favor of rare categories.
- **NOT ESTABLISHED:**
  - Universal superiority of uniform weighting across other architectures or multi-channel SAR inputs.
  - Statistical significance across seeds.
  - Performance or generalization on HOLDOUT.
  - Causal degradation of spatial boundaries.

### Model Selection Context
- Control reached its peak at Epoch 10; Treatment reached its peak at Epoch 5.
- Both arms were evaluated strictly under the frozen early stopping rule (`min_epochs=15`, `patience=10`).
- Reaching peak DEV earlier in one run does not establish that uniform weighting converges universally faster across arbitrary initializations.

---

## 8. Phase 10: Durable Agent Learning Framework Updates

Six new lessons were formally added to `data/metadata/ocean_sentinel_lessons_learned_v1.json` and protected via `tests/test_exp07_p0_c22c_postrun_guardrails.py`:

1. **`LL-C22B-001` (SCIENTIFIC_VALIDITY):** Single paired run establishes an observed difference, not replication-level robustness.
2. **`LL-C22B-002` (SCIENTIFIC_VALIDITY):** Aggregate cross-entropy loss must not be attributed to a specific class without decomposition.
3. **`LL-C22B-003` (SCIENTIFIC_VALIDITY):** Mechanistic causal language requires mechanistic evidence; performance metrics alone do not establish mechanisms.
4. **`LL-C22B-004` (DOCUMENTATION_INTEGRITY):** Canonical class names and semantic definitions must override informal aliases (HM is Artificial / Anthropogenic Objects; OF is Oceanic Front).
5. **`LL-C22B-005` (SCIENTIFIC_VALIDITY):** Best DEV checkpoint selection under early stopping and robust generalization across seeds are distinct concepts.
6. **`LL-C22B-006` (SCIENTIFIC_VALIDITY):** A validated experimental intervention must not become the new canonical protocol solely from one paired run without multi-seed replication.

---

## 9. Phase 13: Minimum Scientifically Defensible Replication Plan

To advance beyond a single-run observation without wasting compute, the following minimal replication protocol is established:

1. **Experiment Structure:** Paired Same-Seed Control vs. Uniform Treatment.
2. **Random Seeds:** Exactly 3 seeds:
   - **Seed 42** (Already completed in C22-B)
   - **Seed 101** (Independent replicate 1)
   - **Seed 202** (Independent replicate 2)
3. **Hardware Invariant:** NVIDIA Tesla T4 GPU (to isolate stochastic algorithmic behavior from hardware/compiler variance).
4. **Optimization Protocol:** Bitwise locked to `OPS02_v1.0.1_FROZEN` (same optimizer, Candidate F schedule generated per seed, 30 max epochs, 15 min epochs, 10 patience).
5. **Statistical Evaluation:**
   - Report Mean $\pm$ Standard Deviation for Control and Treatment DEV mIoU.
   - Paired sample t-test or Wilcoxon signed-rank test across paired seed deltas.
   - Class-level consistency check (verifying if IWs and BS gains persist across all seeds).
6. **HOLDOUT Policy:** HOLDOUT remains strictly firewalled and quarantined. HOLDOUT evaluation is permitted **only** after multi-seed development replication confirms consistent directional superiority.

---

## 10. Phase 14: Final Tests & Git Forensics

- **Test Suite Status:** **176 passed in 7.35s** (170 baseline + 6 C22-C post-run guardrail tests).
- **Git Status:** Clean; tracked user modifications in `.gitignore` and `src/ocean_sentinel/ingestion/dataset.py` remain preserved. Zero commits, zero pushes, zero staged changes.
- **HOLDOUT Access Count:** `0`.
- **Part III Access Count:** `0`.
- **Telemetry Final State:** `COMPLETE` in `scratch/exp07_p0_c22c_run_state.json`.

---

### Final Classification
$$\mathbf{EXP07\_DIAG01 = VALID\_SINGLE\_RUN\_OBSERVATION}$$
*(Uniform weighting demonstrated an empirical advantage on Seed 42; replication across Seeds 101 & 202 is required before modifying canonical baseline policy).*
