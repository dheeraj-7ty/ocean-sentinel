# EXP02C Formal Preregistration Protocol (FINAL DRAFT)

**Experiment ID**: EXP-02C  
**Experiment Title**: Annealed Hard-Negative Sampling Pressure in SAR Oil-Spill Semantic Segmentation  
**Status**: SUBMITTED FOR CAO FORMAL AUTHORIZATION — ZERO IMPLEMENTATION OR TRAINING PERMITTED  
**Date**: 2026-09-09T14:38:00Z  
**Parent Reference Experiment**: EXP-02B-1 (Epoch 3, SHA-256 `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B`)  
**Baseline Reference Experiment**: EXP-01 (Epoch 4, SHA-256 `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`)  

---

> [!WARNING]  
> **CAO GOVERNANCE PROTOCOL**: This document is the FINAL DRAFT preregistration protocol submitted for Chief AI Officer (CAO) authorization.  
> **STRICT COMPLIANCE DIRECTIVE**: No code changes, no kernel pushes, no hyperparameter tuning, no remote runs, and no held-out test data access may occur without formal, explicit CAO authorization.

---

## 1. Experiment Hypothesis

Reducing hard-negative sampling pressure over the training trajectory will test whether the observed late-epoch spatial undersegmentation can be mitigated while retaining useful false-alarm suppression.

---

## 2. Primary Scientific Question

Does dynamically relaxing the hard-negative oversampling ratio from its initial $3.0\times$ exposure ratio down to ordinary-negative per-tile weight parity ($1.0\times$) over 30 epochs allow the network to retain background noise suppression on radar look-alikes while mitigating spatial undersegmentation on genuine oil spills, thereby stabilizing late-epoch validation recall above the $79.00\%$ operational safety floor?

---

## 3. Single Changed Variable Under Intervention

EXP02C is a **strictly single-variable intervention**:

- **Baseline Condition (EXP02B-1)**: Static hard-negative sampling weight $w_{\text{hard\_neg}} = 2.25$ applied uniformly across all 30 epochs ($3.0\times$ ratio over ordinary negatives).
- **Intervention Condition (EXP02C)**: **Annealed Hard-Negative Sampling Weight Schedule $w_{\text{hard}}(e)$**.
  - All positive tile weights ($w_{\text{pos}} = 1.00$) remain strictly fixed for all epochs.
  - All ordinary negative tile weights ($w_{\text{ord\_neg}} = 0.75$) remain strictly fixed for all epochs.
  - Only the hard-negative tile weight $w_{\text{hard}}(e)$ varies deterministically as a function of epoch $e$.

---

## 4. Exact Mathematical Sampling Schedule

For each epoch $e \in \{1, 2, \dots, 30\}$ (1-indexed), the hard-negative sampling weight $w_{\text{hard}}(e)$ is defined by a deterministic **Half-Cycle Cosine Annealing Schedule**:

$$w_{\text{hard}}(e) = 0.75 + 0.75 \times \left(1 + \cos\left(\frac{e - 1}{29} \pi\right)\right)$$

### Canonical Tile Population & Weight Invariants
- Positive spill tiles ($n = 5,083$): $w_{\text{pos}} = 1.00$ (**strictly fixed for all epochs**)
- Ordinary negative tiles ($n = 6,752$): $w_{\text{ord\_neg}} = 0.75$ (**strictly fixed for all epochs**)
- Candidate hard-negative tiles ($n = 1,605$): $w_{\text{hard}}(e)$ follows the schedule above.

### Exact Boundary Endpoints & Terminology
- **Epoch 1**: $w_{\text{hard}}(1) = 2.250000$ (Configured $3.0\times$ hard-to-ordinary negative ratio; identical to EXP02B-1).
- **Epoch 30**: $w_{\text{hard}}(30) = 0.750000$ (Configured $1.0\times$ ratio).
- **CRITICAL TERMINOLOGY RULE**: At Epoch 30, hard-negative and ordinary-negative per-tile weights reach exact equality:
  $$w_{\text{hard}}(30) = w_{\text{ord\_neg}} = 0.75$$
  This condition is strictly designated as **"hard-negative / ordinary-negative per-tile weight parity"**. It is **NOT** "uniform sampling parity" or "uniform dataset exposure", because positive tiles retain higher weight ($w_{\text{pos}} = 1.00$).

### Complete Expected Sampling Probability Schedule Across Trajectory

Persisted in machine-readable format at [`exp02c_expected_sampling_schedule.csv`](file:///d:/Projects/ocean-sentinel/experiments/performance/exp02b_1_diagnostic_20260909_142000/exp02c_expected_sampling_schedule.csv):

| Epoch ($e$) | $w_{\text{hard}}(e)$ | $w_{\text{ord}}$ | $w_{\text{pos}}$ | Expected Hard Fraction | Expected Pos Fraction | Expected Ord Fraction | Hard / Ord Weight Ratio | Hard Wt Rel to EXP02B-1 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **2.250000** | 0.75 | 1.00 | **26.25%** | 36.95% | 36.81% | **3.00x** | **1.000x** |
| 2 | 2.245603 | 0.75 | 1.00 | 26.21% | 36.96% | 36.83% | 2.99x | 0.998x |
| 3 | 2.232465 | 0.75 | 1.00 | 26.10% | 37.02% | 36.88% | 2.98x | 0.992x |
| 5 | 2.180682 | 0.75 | 1.00 | 25.65% | 37.25% | 37.11% | 2.91x | 0.969x |
| 10 | 1.920890 | 0.75 | 1.00 | 23.30% | 38.42% | 38.28% | 2.56x | 0.854x |
| 15 | 1.540604 | 0.75 | 1.00 | 19.59% | 40.28% | 40.13% | 2.05x | 0.685x |
| 20 | 1.148694 | 0.75 | 1.00 | 15.38% | 42.39% | 42.23% | 1.53x | 0.511x |
| 25 | 0.857357 | 0.75 | 1.00 | 11.94% | 44.11% | 43.95% | 1.14x | 0.381x |
| **30** | **0.750000** | 0.75 | 1.00 | **10.61%** | 44.78% | 44.61% | **1.00x** | **0.333x** |

*(Note: These values are exact expected probabilities under the sampler, not empirical realized draw counts).*

---

## 5–15. Locked Scientific Invariants (Zero Modification Permitted)

5. **All Fixed Variables**: Only $w_{\text{hard}}(e)$ varies. All other pipeline elements are locked.
6. **Fixed Decision Threshold**: Strictly locked to **$0.22$** across all evaluations. Zero threshold search or tuning permitted.
7. **Fixed Architecture**: `ResNet34UNet(in_channels=2, num_classes=1, adaptation_method='slice_variance_scaled')` ($24,346,305$ total parameters).
8. **Fixed Input Normalization**: Canonical training-derived stats:
   - Channel 0 (VV): $\text{mean} = -33.233137, \text{std} = 6.489986$
   - Channel 1 (VH): $\text{mean} = -19.941216, \text{std} = 4.531346$
9. **Fixed Spatial Dataset Split**: Canonical `spatial_split_manifest.json` (SHA-256 `C052720A...`):
   - Train: 840 parent patches ($13,440$ tiles, $70\%$)
   - Validation: 180 parent patches ($2,880$ tiles, $15\%$)
   - Test: 180 parent patches ($2,880$ tiles, $15\%$)
10. **Fixed Data Augmentation**: Canonical training pipeline (`RandomHorizontalFlip(0.5)`, `RandomVerticalFlip(0.5)`, `RandomRotate90(0.5)`). Validation uses unaugmented `IdentityTransform`.
11. **Fixed Optimization Protocol**: AdamW ($\text{lr} = 1 \times 10^{-4}, \text{weight\_decay} = 1 \times 10^{-2}, \beta = (0.9, 0.999), \epsilon = 1 \times 10^{-8}$).
12. **Fixed Learning Rate Schedule**: `CosineAnnealingLR` ($T_{\max} = 30, \eta_{\min} = 1 \times 10^{-6}$).
13. **Fixed Master Seed**: `42`.
14. **Fixed Epoch Count**: Exactly $30$ epochs ($50,400$ optimization update attempts).
15. **Fixed Checkpointing Rule**: At each epoch end, evaluate validation split ($2,880$ tiles, threshold $0.22$). Track best model according to the preregistered balanced selection hierarchy. Save `latest_checkpoint.pt`, `best_model.pt`, and `final_model.pt`.

---

## 16–17. Balanced Model-Selection Hierarchy (Validation-Only)

16. **Validation-Only Selection**: Model selection is governed exclusively by validation split metrics. Test data is strictly firewalled.
17. **Selection Hierarchy**:
    - **Tier 1 (Mandatory Safety Floor)**:
      $$\text{Validation Spill Recall} \ge \mathbf{79.00\%}$$
      *Any checkpoint with validation recall $< 79.00\%$ is disqualified immediately, regardless of false-alarm rate or IoU.*
    - **Tier 2 (Operational False-Alarm Ceiling Gate)**:
      $$\text{Validation GT-Negative FA Rate} \le \mathbf{12.00\%}$$
      *Operational Rationale*: Documented as an explicit operational design choice. Baseline EXP01 exhibited an unweighted FA rate of $20.09\%$ ($367 / 1,827$ tiles). A ceiling of $12.00\%$ ($219 / 1,827$ tiles) guarantees at least an **$8.09$ percentage-point absolute reduction** and a **$40.26\%$ relative reduction** in false-alarm tiles vs. baseline, while providing a $+3.74$ percentage-point tolerance buffer above EXP02B-1 ($8.26\%$) to permit restoration of ambiguous boundary pixels on genuine slicks without accepting noisy models.
    - **Tier 3 (Optimization Criterion)**:
      Among all checkpoints satisfying Tier 1 ($\text{Recall} \ge 79.00\%$) and Tier 2 ($\text{FA} \le 12.00\%$), select the checkpoint that maximizes:
      $$\mathbf{\max \text{Global Validation IoU}}$$

---

## 18–19. Exact Success & Failure Criteria

18. **Success Criteria**:
    - **Primary Success**: A checkpoint is identified that satisfies Tier 1 ($\text{Recall} \ge 79.00\%$) and Tier 2 ($\text{FA} \le 12.00\%$) with $\text{Global IoU} \ge 0.7305$ (matching or exceeding EXP02B-1 Epoch 3).
    - **Trajectory Stability Success**: Validation recall remains $\ge 79.00\%$ for at least 10 consecutive epochs in the second half of training (Epochs 15–30), demonstrating that annealing mitigates late-epoch recall collapse.
    - **Statistical Significance**: The selected checkpoint demonstrates a statistically significant reduction in negative false alarms compared to EXP01 via continuity-corrected McNemar test ($p < 0.01$).

19. **Failure Criteria**:
    - **Safety Failure**: Zero checkpoints satisfy Tier 1 ($\text{Recall} \ge 79.00\%$) while simultaneously satisfying Tier 2 ($\text{FA} \le 12.00\%$).
    - **Noise Rebound Failure**: Relaxing hard-negative weight causes the validation FA rate to rebound above $12.00\%$ across all recall-compliant epochs.
    - **Degradation Failure**: The selected model fails to achieve $\text{Global IoU} \ge 0.7000$.

---

## 20. Explicit No-Test-Tuning Clause

Held-out test split data ($2,880$ tiles, 180 patches) must **NOT** be accessed, read, evaluated, or loaded during the execution of EXP02C or during checkpoint selection. Test evaluation may only be requested after formal CAO validation audit and closure authorization.

---

## 21–22. Directional Effects & Falsification Logic

21. **Expected Directional Effects**:
    - Compared to EXP02B-1 in late epochs (Epochs 15–30), EXP02C is expected to exhibit **higher spill recall** and **larger predicted spill area** due to reduced boundary shrinkage.
    - Compared to EXP01 baseline throughout training, EXP02C is expected to maintain a **substantially lower false-alarm rate** on negative tiles ($\le 12.00\%$ vs. $20.09\%$).
22. **Falsification Logic**:
    - If reducing negative pressure causes validation FA rate to immediately rebound to baseline levels ($\ge 18.0\%$) without improving boundary recall, the hypothesis that negative sampling can be annealed independently of false-positive memory is **falsified**.
    - If late-epoch recall still collapses below $79.00\%$ despite $w_{\text{hard}}(e)$ decaying to $0.75$, the hypothesis that oversampling was the sole cause of late-epoch shrinkage is **falsified** (indicating that loss objective modifications are mandatory).

---

## 23. Hypothesis-Support Diagnostics (Non-Selection Metrics)

The following diagnostics will be tracked at every epoch solely to evaluate the scientific hypothesis:
- Positive-tile false-negative pixel count
- Mean predicted-to-ground-truth area ratio
- Undersegmented tile count
- Scale-stratified recall: tiny (<500 px), medium (500–5,000 px), large ($\ge 5,000$ px)
- Positive-tile detection rate (tiles with $\text{TP} \ge 1$)
- Macro false-alarm rate ($\text{FP} \ge 100$ px) and extensive false-alarm rate ($\text{FP} \ge 1,000$ px)

**CRITICAL RULE**: These metrics diagnose whether undersegmentation changes as hypothesized. They are **NOT** additional hidden model-selection criteria. Checkpoint selection is governed strictly by Tiers 1–3.

---

## 24. Provenance & Cryptographic Hashes

- `data/metadata/trujillo_2024/spatial_split_manifest.json`:  
  `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0`
- `experiments/performance/exp02b_1_hard_negative_training_20260909_094500/kernel_output/exp02b_1_hard_negative_training/best_model.pt`:  
  `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B`
- `experiments/exp01_baseline/best_model.pt`:  
  `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
- `experiments/performance/exp02b_1_hard_negative_training_20260909_094500/src_dataset_staging/candidate_manifest.json`:  
  `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7`
- Pretrained ImageNet ResNet-34:  
  `B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F`
