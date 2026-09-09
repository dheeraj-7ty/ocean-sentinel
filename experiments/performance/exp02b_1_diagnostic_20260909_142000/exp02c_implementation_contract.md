# EXP02C Implementation & Reproducibility Contract

**Status**: TECHNICAL RECONCILIATION COMPLETE — SUBMITTED FOR CAO AUTHORIZATION  
**Target Experiment**: EXP-02C (Annealed Hard-Negative Sampling Pressure)  
**Parent Reference**: EXP-02B-1 (Epoch 3, SHA-256 `54B4B098...`)  
**Date**: 2026-09-09T14:37:00Z  

---

> [!IMPORTANT]  
> **BINDING SCIENTIFIC CONTRACT**: This document specifies the exact code delta, mathematical schedule, random generator mechanics, and invariant parameters for EXP02C. Zero modification of parameters outside the single declared intervention variable is permitted.

---

## 1. Single Changed Scientific Variable

EXP02C alters **EXACTLY ONE** scientific variable relative to EXP02B-1:
- **Intervention Variable**: Hard-negative sampling weight schedule $w_{\text{hard}}(e)$ as a function of epoch $e \in \{1, \dots, 30\}$.
- **Baseline (EXP02B-1)**: Static weight $w_{\text{hard}} = 2.25$ for all 30 epochs.
- **Intervention (EXP02C)**: Half-Cycle Cosine Annealed weight decaying deterministically from $2.25$ to $0.75$.

---

## 2. Exact Mathematical Annealing Schedule

For each epoch $e \in \{1, 2, \dots, 30\}$ (1-indexed):

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

---

## 3. Expected Sampler Probabilities Across Trajectory

Under `WeightedRandomSampler(replacement=True, num_samples=13440)`, the expected probability of selecting tile $i$ in epoch $e$ is:
$$p_i^{(e)} = \frac{w_i^{(e)}}{\sum_{k=1}^{13440} w_k^{(e)}}$$

The complete 30-epoch trajectory is persisted in [`exp02c_expected_sampling_schedule.csv`](file:///d:/Projects/ocean-sentinel/experiments/performance/exp02b_1_diagnostic_20260909_142000/exp02c_expected_sampling_schedule.csv):

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

*(Note: These figures represent exact expected sampler probabilities, not empirical realized draw counts).*

---

## 4. Implementation Reconciliation & Minimal Code Delta

### Implementation Mechanism
In PyTorch, `WeightedRandomSampler` holds `self.weights` as a 1D double tensor. The main DataLoader process generates batch indices by calling `torch.multinomial(self.weights, self.num_samples, self.replacement, generator=self.generator)`.

To support $w_{\text{hard}}(e)$ without altering dataset structures or worker processes:
1. Define deterministic function `compute_hard_negative_weight(epoch: int, total_epochs: int = 30) -> float`.
2. Construct pre-indexed boolean masks for candidate classes:
   - `pos_mask`: indices of positive tiles ($n = 5,083$)
   - `hard_mask`: indices of hard negative tiles ($n = 1,605$)
   - `ord_mask`: indices of ordinary negative tiles ($n = 6,752$)
3. At the start of each epoch $e$ in the training loop:
   ```python
   w_hard = 0.75 + 0.75 * (1.0 + math.cos((epoch - 1) * math.pi / 29.0))
   new_weights = torch.empty(13440, dtype=torch.double)
   new_weights[pos_mask] = 1.00
   new_weights[hard_mask] = w_hard
   new_weights[ord_mask] = 0.75
   train_loader.sampler.weights = new_weights
   ```
4. **Verification of Non-Interference**:
   - Dataloader workers (`num_workers=4`, `pin_memory=True`, `persistent_workers=True`) receive indices generated in the main process. Updating `sampler.weights` between epochs updates the multinomial probability vector cleanly and deterministically.
   - Zero modifications to model, loss, optimizer, or step accounting.

---

## 5. Randomness & Reproducibility Contract

1. **Sampler Random Generator**:
   - The sampler generator is initialized with `torch.Generator().manual_seed(42)`.
   - The sequential state of the generator advances deterministically with each `torch.multinomial` call across epochs.
   - Verified empirically: two separate complete runs executing the dynamic schedule produce bit-for-bit identical sample index sequences.
2. **Worker Seed Determinism**:
   - Worker seed initialization in `DataLoader(worker_init_fn=...)` is locked to `seed + worker_id`.
   - Python `random`, `numpy.random`, and `torch.manual_seed` are seeded to `42`.
3. **Hardware Determinism**:
   - `torch.backends.cudnn.benchmark = False`
   - `torch.backends.cudnn.deterministic = True`

---

## 6. Scientific Invariants Checklist (All 15 Variables Locked)

| Parameter | EXP02B-1 Value | EXP02C Value | Invariance Status |
| :--- | :--- | :--- | :---: |
| **Model Architecture** | ResNet34UNet (slice_variance_scaled) | ResNet34UNet (slice_variance_scaled) | **LOCKED** |
| **Total Parameters** | 24,346,305 | 24,346,305 | **LOCKED** |
| **Pretrained Weights** | ImageNet ResNet-34 (SHA: `B627A593...`) | ImageNet ResNet-34 (SHA: `B627A593...`) | **LOCKED** |
| **Loss Function** | CombinedBCEAndDiceLoss (0.5/0.5, smooth=1.0)| CombinedBCEAndDiceLoss (0.5/0.5, smooth=1.0)| **LOCKED** |
| **Optimizer** | AdamW ($\text{lr}=10^{-4}, \text{wd}=10^{-2}$) | AdamW ($\text{lr}=10^{-4}, \text{wd}=10^{-2}$) | **LOCKED** |
| **LR Scheduler** | CosineAnnealingLR ($T_{\max}=30, \eta_{\min}=10^{-6}$)| CosineAnnealingLR ($T_{\max}=30, \eta_{\min}=10^{-6}$)| **LOCKED** |
| **Batch Size** | 8 (effective 8, accum_steps=1) | 8 (effective 8, accum_steps=1) | **LOCKED** |
| **AMP Precision** | FP16 + GradScaler | FP16 + GradScaler | **LOCKED** |
| **Data Partition** | Canonical `spatial_split_manifest.json` | Canonical `spatial_split_manifest.json` | **LOCKED** |
| **Normalization** | Canonical Train NormalizationStats | Canonical Train NormalizationStats | **LOCKED** |
| **Data Augmentation** | Canonical Train Flip/Rotate90 | Canonical Train Flip/Rotate90 | **LOCKED** |
| **Master Seed** | 42 | 42 | **LOCKED** |
| **Epoch Count** | 30 epochs (50,400 update attempts) | 30 epochs (50,400 update attempts) | **LOCKED** |
| **Decision Threshold** | 0.22 (strictly frozen) | 0.22 (strictly frozen) | **LOCKED** |
| **Samples / Epoch** | 13,440 with replacement | 13,440 with replacement | **LOCKED** |

---

## 7. Model-Selection Hierarchy & Gating Rules

Model selection is strictly **validation-only** following this operational hierarchy:

- **Tier 1 (Mandatory Safety Floor)**:
  $$\text{Validation Spill Recall} \ge \mathbf{79.00\%}$$
  *(Any checkpoint with recall $< 79.00\%$ is disqualified immediately).*

- **Tier 2 (Operational False-Alarm Ceiling)**:
  $$\text{Validation GT-Negative FA Rate} \le \mathbf{12.00\%}$$
  *(Documented as an operational design threshold guaranteeing $\ge 40.26\%$ relative reduction vs. EXP01 baseline [20.09%], providing tolerance buffer above EXP02B-1 [8.26%] to allow boundary restoration).*

- **Tier 3 (Optimization Criterion)**:
  Among checkpoints satisfying Tier 1 and Tier 2, select the model that maximizes:
  $$\mathbf{\max \text{Global Validation IoU}}$$

---

## 8. Hypothesis-Support Diagnostics (Non-Selection Metrics)

The following diagnostics will be logged at every epoch to evaluate the scientific hypothesis:
- Positive-tile false negative pixel count
- Mean predicted-to-ground-truth area ratio
- Undersegmented tile count
- Scale-stratified recall: tiny (<500 px), medium (500–5,000 px), large ($\ge 5,000$ px)
- Positive-tile detection rate (tiles with $\text{TP} \ge 1$)
- Macro false alarm rate ($\text{FP} \ge 100$ px) and extensive false alarm rate ($\text{FP} \ge 1,000$ px)

**GOVERNANCE RULE**: These diagnostic metrics test whether spatial undersegmentation changes as hypothesized. They are **NOT** additional hidden optimization gates. Checkpoint selection is strictly governed by Tiers 1–3.

---

## 9. Test Firewall

- The held-out test split ($2,880$ tiles, 180 patches) is completely firewalled.
- Zero test data may be accessed or processed during EXP02C training, hyperparameter validation, or model selection.
- Test evaluation will only be permitted after formal CAO validation audit and closure authorization.
