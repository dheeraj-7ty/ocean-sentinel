# EXP02C PRE-TRAINING GATE REPORT

**Experiment ID**: `EXP-02C`  
**Experiment Title**: Annealed Hard-Negative Sampling Pressure in SAR Oil-Spill Semantic Segmentation  
**Timestamp UTC**: 2026-09-09T09:19:17Z  
**Execution Node**: NVIDIA GeForce RTX 3050 6GB Laptop GPU (`sm_86`)  
**Authorization**: CAO FORMAL AUTHORIZATION — EXP02C TRAINING (APPROVED)  
**Status**: **ALL PREFLIGHT CHECKS PASSED — READY FOR FULL 30-EPOCH TRAINING**

---

## 1. FIXED SCIENTIFIC INVARIANTS AUDIT

All fixed scientific invariants inherited bit-for-bit from EXP02B-1 are verified and frozen:

| Parameter | Specification | Verification Method | Status |
| :--- | :--- | :--- | :---: |
| **Architecture** | `ResNet34UNet(in_channels=2, num_classes=1)` | Model instantiation check | **PASS** |
| **Adaptation Method** | `slice_variance_scaled` | Method parameter check | **PASS** |
| **Total Parameters** | `24,346,305` | Exact parameter count | **PASS** |
| **Pretrained Weights** | ImageNet ResNet-34 (`B627A593...`) | Local hub cache SHA-256 | **PASS** |
| **Loss Function** | Combined BCE (0.5) + SoftDice (0.5), smooth 1.0 | Criterion verification | **PASS** |
| **Optimizer** | AdamW ($\text{lr}=10^{-4}, \text{wd}=10^{-2}, \beta=(0.9, 0.999), \epsilon=10^{-8}$) | Parameter dict inspection | **PASS** |
| **LR Scheduler** | `CosineAnnealingLR` ($T_{\max}=30, \eta_{\min}=10^{-6}$) | Scheduler inspection | **PASS** |
| **Batch Size** | 8 physical, 1 accumulation step, effective batch size 8 | DataLoader inspection | **PASS** |
| **Precision** | PyTorch CUDA AMP FP16 + dynamic `GradScaler` | Runtime AMP check | **PASS** |
| **Master Seed** | `42` | Python/PyTorch/CUDA seed | **PASS** |
| **Epoch Count** | Exactly 30 epochs ($50,400$ optimization update attempts) | Trajectory configuration | **PASS** |
| **Samples per Epoch**| 13,440 tiles per epoch ($1,680$ batches of 8) | Sampler length check | **PASS** |
| **Sampling Mode** | `WeightedRandomSampler(replacement=True, generator=seed42)` | Sampler configuration | **PASS** |
| **Canonical Normalization** | VV: $\mu=-33.2331, \sigma=6.4900$; VH: $\mu=-19.9412, \sigma=4.5313$ | Dataset initialization | **PASS** |
| **Data Augmentation** | Train: HFlip(0.5) + VFlip(0.5) + Rot90(0.5); Val: `IdentityTransform` | Pipeline check | **PASS** |
| **Decision Threshold** | Strictly locked to **0.22** (NO threshold search/tuning) | Code enforcement | **PASS** |
| **Test Firewall** | `ds_test = None`, zero test tiles loaded, zero test metrics | Isolation check | **PASS** |

---

## 2. ARTIFACT & PROVENANCE HASH VERIFICATION

All core dataset, model, and script SHA-256 hashes verified against authoritative references:

| Artifact | Expected SHA-256 | Actual SHA-256 | Status |
| :--- | :--- | :--- | :---: |
| **Spatial Split Manifest** | `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` | `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` | **MATCH** |
| **Candidate Manifest** | `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7` | `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7` | **MATCH** |
| **EXP01 Baseline Checkpoint**| `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | **MATCH** |
| **EXP02B-1 Checkpoint** | `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B` | `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B` | **MATCH** |
| **Pretrained ResNet-34** | `B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F` | `B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F` | **MATCH** |
| **train_exp02c.py** | — | `B45331E86932C9D1C83158C27D1E6F71A5FAE2769007656BF411516B982C762A` | **VERIFIED** |

---

## 3. SINGLE CHANGED VARIABLE: ANNEALED SAMPLING SCHEDULE

The single changed scientific variable is the hard-negative sampling weight schedule:

$$w_{\text{hard}}(e) = 0.75 + 0.75 \times \left(1.0 + \cos\left(\frac{e - 1}{29} \pi\right)\right)$$

### Canonical Tile Population:
- Positive spill tiles ($n = 5,083$): $w_{\text{pos}} = 1.00$ (strictly fixed)
- Candidate hard-negative tiles ($n = 1,605$): $w_{\text{hard}}(e)$ follows schedule
- Ordinary GT-negative tiles ($n = 6,752$): $w_{\text{ord\_neg}} = 0.75$ (strictly fixed)

### Exact Endpoints:
- **Epoch 1**: $w_{\text{hard}}(1) = 2.250000$ ($3.00\times$ ratio over ordinary negatives, expected hard fraction: $26.25\%$)
- **Epoch 30**: $w_{\text{hard}}(30) = 0.750000$ ($1.00\times$ ratio over ordinary negatives, expected hard fraction: $10.61\%$)
- **Condition at Epoch 30**: **Hard-negative / ordinary-negative per-tile weight parity** ($w_{\text{hard}} = w_{\text{ord}} = 0.75$).

### Trajectory Sampling Schedule (Subset):
| Epoch | $w_{\text{hard}}(e)$ | $w_{\text{ord}}$ | $w_{\text{pos}}$ | Expected Hard % | Expected Pos % | Expected Ord % | Hard/Ord Ratio |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **2.250000** | 0.75 | 1.00 | **26.25%** | 36.95% | 36.81% | **3.000x** |
| 2 | 2.245603 | 0.75 | 1.00 | 26.21% | 36.96% | 36.83% | 2.994x |
| 3 | 2.232465 | 0.75 | 1.00 | 26.10% | 37.02% | 36.88% | 2.977x |
| 5 | 2.180682 | 0.75 | 1.00 | 25.65% | 37.25% | 37.11% | 2.908x |
| 10 | 1.920890 | 0.75 | 1.00 | 23.30% | 38.42% | 38.28% | 2.561x |
| 15 | 1.540604 | 0.75 | 1.00 | 19.59% | 40.28% | 40.13% | 2.054x |
| 20 | 1.148694 | 0.75 | 1.00 | 15.38% | 42.39% | 42.23% | 1.532x |
| 25 | 0.857357 | 0.75 | 1.00 | 11.94% | 44.11% | 43.95% | 1.143x |
| **30** | **0.750000** | 0.75 | 1.00 | **10.61%** | 44.78% | 44.61% | **1.000x** |

*(Complete 30-epoch schedule persisted in `exp02c_sampling_schedule.csv`).*

---

## 4. RANDOMNESS & DETERMINISM INTEGRITY

- **Master Seed**: 42.
- **Generator**: `torch.Generator().manual_seed(42)` instantiated once at sampler construction.
- **Dynamic Weight Updates**: In PyTorch, assigning `train_loader.sampler.weights = new_weights` dynamically updates multinomial probabilities for `__iter__` without re-instantiating or resetting the generator.
- **Empirical Verification**: Repeated executions produced bit-for-bit identical draw sequences across all epochs, while generator state advances naturally without cyclic repetition.

---

## 5. REAL DATA DRY RUN (ZERO-RISK PREFLIGHT)

Executed on live canonical dataset with zero retained weights:
- **Input Batch Shape**: `torch.Size([8, 2, 512, 512])` (**PASS**)
- **Model Logits Shape**: `torch.Size([8, 1, 512, 512])` (**PASS**)
- **Forward Combined Loss**: `0.8507` (finite, zero NaN/Inf) (**PASS**)
- **Backward Pass**: Succeeded under FP16 autocast (**PASS**)
- **Gradients**: Strictly finite across all 24,346,305 parameters (**PASS**)
- **GradScaler Update**: Clean step, zero scale reduction (**PASS**)
- **Gradients Cleared**: Zero optimizer steps retained (**PASS**)
- **Atomic Save/Load**: Checkpoint serialization and reload integrity verified (**PASS**)

---

## 6. MODEL SELECTION HIERARCHY & TEST FIREWALL

### Model Selection Hierarchy (Validation-Only):
- **Tier 1 (Mandatory Safety Floor)**: Validation Oil Spill Recall $\ge \mathbf{79.00\%}$.
- **Tier 2 (False-Alarm Ceiling Gate)**: Validation GT-Negative FA Rate $\le \mathbf{12.00\%}$.
- **Tier 3 (Optimization Criterion)**: Among qualifying checkpoints (satisfying Tiers 1 and 2), select the checkpoint that maximizes **Global Validation IoU**.

### Test Split Isolation:
- `ds_test` is strictly `None`.
- `test_loader` is strictly `None`.
- Zero test tiles loaded, read, or evaluated during training or model selection.
- Single-pass test evaluation is firewalled and deferred until separate CAO authorization.

---

## 7. PREFLIGHT GATE CONCLUSION

```
================================================================================
EXP02C PRETRAINING GATE STATUS: PASS (11/11 CHECKS SATISFIED)
ZERO INVARIANT DRIFT DETECTED. AUTHORIZED FOR FULL TRAINING EXECUTION.
================================================================================
```
