# EXP02C Preregistration Protocol (DRAFT ONLY)
**Status**: DRAFT FOR CAO REVIEW ONLY — DO NOT IMPLEMENT OR EXECUTE  
**Timestamp**: 2026-09-09T14:27:00Z  
**Authoritative Reference Experiment**: EXP02B-1 (Epoch 3, SHA-256 `54B4B098...`)  

---

> [!WARNING]  
> **GOVERNANCE NOTICE**: This document is a DRAFT preregistration proposal prepared for Chief AI Officer (CAO) review.  
> **NO CODE CHANGES, TRAINING, TUNING, OR EXECUTION ARE PERMITTED WITHOUT EXPLICIT CAO AUTHORIZATION.**

---

## 1. Scientific Objective & Justification

### Primary Scientific Question
> *"Can calibrating the hard-negative sampling pressure maintain the $>58\%$ false-alarm reduction achieved by EXP02B-1 while preventing the late-epoch recall collapse and boundary undersegmentation identified in the diagnostic audit?"*

### Empirical Evidence from EXP02B-1 Diagnostic
1. **False-Positive Suppression is Real**: EXP02B-1 proved that hard-negative sampling drastically reduces false alarms ($58.86\%$ relative reduction on validation, $p = 9.03 \times 10^{-32}$; $65.54\%$ relative reduction on test, $p = 9.77 \times 10^{-56}$).
2. **Recall Loss is $97.16\%$ Boundary Undersegmentation**: Out of 1,053 positive validation tiles, $97.16\%$ of deteriorating false-negative pixels ($172,350$ px across 118 tiles) stemmed from spatial extent shrinkage on detected spills. Complete whole-tile misses were rare ($1.61\%$, $2,532$ px, zero large spills missed).
3. **Constant Resampling Causes Trajectory Over-Suppression**: In Epoch 3, Recall was $86.64\%$. However, maintaining unrelenting $20\times$ negative oversampling across 30 epochs continuously eroded spill margins, causing Recall to systematically collapse to $75\% - 78\%$ in late epochs (violating the $79.0\%$ safety floor).

---

## 2. Experimental Intervention Contract (Strictly Single-Variable)

### The Single Variable Under Intervention
- **Baseline (EXP02B-1)**: Static hard-negative sampling weight $w_{\text{hn}} = 1.0$ (a $20\times$ oversampling ratio relative to clean negatives $w_{\text{cn}} = 0.05$) applied uniformly across all 30 epochs.
- **Candidate Intervention (EXP02C)**: **Calibrated Hard-Negative Oversampling Schedule**.
  - *Option A (Recommended: Annealed Weight)*: Cosine decay of hard-negative sampling weight from $w_{\text{hn}} = 1.0$ down to $w_{\text{hn}} = 0.20$ across epochs $1 \dots 30$, reducing negative pressure as background silence is established.
  - *Option B (Constant Reduced Ratio)*: Static reduced hard-negative oversampling ratio of $5\times$ ($w_{\text{hn}} = 0.25, w_{\text{cn}} = 0.05$) throughout training.

### Locked Scientific Invariants (Zero Modification)
1. **Model Architecture**: ResNet34UNet (24,346,305 parameters, `slice_variance_scaled` 2-channel adaptation).
2. **Optimization Protocol**: AdamW ($\text{lr} = 1 \times 10^{-4}, \text{weight\_decay} = 1 \times 10^{-2}, \beta = (0.9, 0.999), \epsilon = 1 \times 10^{-8}$).
3. **Learning Rate Scheduler**: CosineAnnealingLR ($T_{\max} = 30, \eta_{\min} = 1 \times 10^{-6}$).
4. **Batch Size & Precision**: Batch size 8, effective batch size 8, CUDA AMP float16 with GradScaler.
5. **Loss Function**: CombinedBCEAndDiceLoss ($0.5$ BCE, $0.5$ Dice, smooth $1.0$).
6. **Data Partition**: Canonical `spatial_split_manifest.json` (SHA-256 `C052720A...`, 840 train, 180 val, 180 test patches).
7. **Input Normalization**: Canonical training-derived statistics (`vv_mean = -33.2331`, `vh_mean = -19.9412`).
8. **Data Augmentation**: Canonical training augmentation pipeline.
9. **Decision Threshold**: Strictly locked to **$0.22$** (zero search, zero tuning).
10. **Test Firewall**: Zero access to held-out test data during training or model selection.

---

## 3. Preregistered Balanced Model-Selection Hierarchy

Checkpoint selection at the conclusion of training must follow this strict 3-tier hierarchy:

- **Tier 1: Mandatory Safety Gate (Recall)**
  $$\text{Validation Recall} \ge \mathbf{79.00\%}$$
  *(Any checkpoint with recall $< 79.00\%$ is disqualified immediately, regardless of FA or IoU).*

- **Tier 2: False-Alarm Ceiling Gate**
  $$\text{Validation GT-Negative FA Rate} \le \mathbf{12.00\%}$$
  *(Locks in at least a $40\%$ relative reduction compared to EXP01's $20.09\%$, preventing false-alarm rebound).*

- **Tier 3: Optimization Criterion (Segmentation Quality)**
  Among all checkpoints satisfying Tier 1 and Tier 2, select the model that maximizes:
  $$\mathbf{\max \text{Global Validation IoU}}$$

---

## 4. Preregistered Hypotheses & Falsification Criteria

- **Primary Hypothesis $H_1$**: Calibrating hard-negative resampling pressure will prevent late-epoch recall collapse, maintaining validation recall $\ge 82.0\%$ through Epochs 5–25 while keeping the validation negative FA rate $\le 12.0\%$.
- **Falsification Condition $F_1$**: If reducing negative pressure causes the validation FA rate to rebound above $15.0\%$ in early epochs without improving late-epoch recall, $H_1$ is rejected.
- **Falsification Condition $F_2$**: If late-epoch recall still collapses below $79.0\%$ despite weight reduction, $H_1$ is rejected (indicating that negative sampling alone cannot decouple boundary erosion from false-alarm suppression, motivating Rank 2 boundary loss).

---

## 5. Execution Preconditions

Before EXP02C can be scheduled:
1. Formal CAO review and sign-off on this preregistration draft.
2. Selection between Option A (Annealed) and Option B (Reduced Constant) by CAO.
3. Creation of locked configuration and candidate manifest for EXP02C.
