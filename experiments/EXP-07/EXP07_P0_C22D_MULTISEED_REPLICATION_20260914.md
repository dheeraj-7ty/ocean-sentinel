# EXP-07-P0-C22-D: MULTI-SEED PAIRED REPLICATION REPORT
**Experiment ID:** `EXP07_DIAG01_REPLICATION`  
**Task ID:** `EXP-07-P0-C22-D`  
**Date:** 2026-09-14  
**Status:** `COMPLETED_VALID`  
**Scientific Classification:** `CASE_B_SEED_SENSITIVE_EFFECT_UNJUSTIFIED_FOR_CANONICAL_ADOPTION`  
**Authoritative Dataset:** `OPS02_v1.0.1_FROZEN`  

---

## 1. Executive Summary

Under the frozen Ocean Sentinel machine learning protocol (`OPS02_v1.0.1_FROZEN`), a prospective 4-seed paired replication study was executed to evaluate whether the initial single-run observation from **EXP-07-P0-C22-B** (Seed 42: Treatment $+0.01171$ over Control) generalizes across independent random initializations.

The sole experimental intervention remained the loss-weighting policy:
- **Control (Arm A):** Canonical C16 Sqrt-Median-Frequency Class Weights `[0.403935, 2.450546, 0.876692, 0.945945, 0.648189, 4.211476, 0.719641, 2.956203, 1.064525, 1.882870, 0.387652, 18.243211]`
- **Treatment (Arm B):** Uniform Unweighted CrossEntropyLoss `[1.0] * 12`

All 19 scientific invariants, the ImageNet-pretrained canonical initialization (`67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D`), Candidate F hybrid sampler schedule, ResNet18-UNet architecture (14,310,860 trainable parameters, 30 BatchNorm2d layers), optimizer (`AdamW`, lr=5e-4), scheduler (`LinearWarmupCosineAnnealingLR`), batch dynamics (physical 8, virtual 16), and early stopping rules (`MAX_EPOCHS=30, MIN_EPOCHS=15, PATIENCE=10`) were held strictly bitwise and functionally identical across paired arms.

### Primary Conclusion: **CASE B (Seed-Sensitive Effect)**
Across the prospective replication seeds (Seeds 101, 202, 303, 404), the results were evenly split:
- **Control won 2 seeds** (Seed 101: $-0.01405$, Seed 303: $-0.00586$).
- **Treatment won 2 seeds** (Seed 202: $+0.00383$, Seed 404: $+0.00458$).
- Mean prospective paired delta: $\mathbf{-0.00288}$ (in favor of Control).

Across all five paired seeds (including historical discovery Seed 42):
- **Treatment won 3, Control won 2, 0 ties.**
- Mean paired delta: $\mathbf{+0.00004}$ ($\approx 0.000$).
- Standard deviation of delta: $\mathbf{0.01006}$.
- Median paired delta: $\mathbf{+0.00383}$.
- Range of paired deltas: $\mathbf{[-0.01405, +0.01171]}$.

The original C22-B single-run observation does **NOT** reflect a consistent or robust development-set advantage under the frozen protocol. Consequently, **it does NOT justify replacing the canonical sqrt-median-frequency class weighting policy.**

---

## 2. Predeclared Statistical Protocol & Small-Sample Limitations

As predeclared prior to prospective execution (reconciling C22-C):
1. **Study Design:** Small-sample robustness and effect-consistency study ($n=5$ total pairs, $n=4$ prospective pairs), **NOT** a confirmatory hypothesis test.
2. **Success Criterion:** Scientific judgment based on effect direction, magnitude, and consistency. A rigid $p < 0.05$ threshold is mathematically unviable and invalid for small nonparametric sample sizes ($n=3$ or $n=5$) and was explicitly excluded as a pass/fail gate.
3. **Statistical Limitation Statement:** With $n=5$, confidence intervals (e.g., Student-$t$ 95% CI: $[-0.01244, +0.01253]$) are purely descriptive metrics of sample dispersion. They do not constitute confirmatory inferential proof.
4. **Seed Status Classification:**
   - **Seed 42:** Historical discovery observation (known outcome, pre-authorized, included in 5-pair aggregate but distinguished from prospective tests).
   - **Seeds 101, 202, 303, 404:** Prospective replication seeds executed under locked protocol.

---

## 3. Detailed Results by Seed

### A. Historical Discovery Observation (C22-B)
| Seed | Seed Type | Control Best DEV mIoU (Epoch) | Treatment Best DEV mIoU (Epoch) | Paired Delta ($\Delta$) | Relative % | Winner |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | Discovery (Historical) | 0.04147 (Ep 10 / 20) | 0.05318 (Ep 5 / 15) | **+0.01171** | +28.24% | **TREATMENT** |

### B. Prospective Replications (C22-D)
| Seed | Seed Type | Control Best DEV mIoU (Epoch) | Treatment Best DEV mIoU (Epoch) | Paired Delta ($\Delta$) | Relative % | Winner | Initial Parity |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **101** | Prospective | 0.05886 (Ep 15 / 25) | 0.04481 (Ep 5 / 15) | **-0.01405** | -23.87% | **CONTROL** | Bitwise Match |
| **202** | Prospective | 0.04358 (Ep 27 / 30) | 0.04741 (Ep 6 / 16) | **+0.00383** | +8.79% | **TREATMENT** | Bitwise Match |
| **303** | Prospective | 0.05191 (Ep 19 / 29) | 0.04605 (Ep 5 / 15) | **-0.00586** | -11.29% | **CONTROL** | Bitwise Match |
| **404** | Prospective | 0.04940 (Ep 21 / 30) | 0.05398 (Ep 7 / 17) | **+0.00458** | +9.27% | **TREATMENT** | Bitwise Match |

---

## 4. Aggregate Statistical Summaries

### Summary Comparison Table

| Metric | Prospective Only ($n=4$) | All Five Pairs ($n=5$) |
| :--- | :---: | :---: |
| **Control Mean Best DEV mIoU** | $0.05094$ | $0.04904$ |
| **Control SD Best DEV mIoU** | $0.00639$ | $0.00693$ |
| **Treatment Mean Best DEV mIoU** | $0.04806$ | $0.04909$ |
| **Treatment SD Best DEV mIoU** | $0.00408$ | $0.00421$ |
| **Mean Paired Delta ($\bar{\Delta}$)** | $\mathbf{-0.00288}$ | $\mathbf{+0.00004}$ |
| **SD of Paired Delta ($s_\Delta$)** | $0.00877$ | $0.01006$ |
| **Median Paired Delta** | $-0.00102$ | $+0.00383$ |
| **Minimum Paired Delta** | $-0.01405$ | $-0.01405$ |
| **Maximum Paired Delta** | $+0.00458$ | $+0.01171$ |
| **Treatment Wins** | 2 (50.0%) | 3 (60.0%) |
| **Control Wins** | 2 (50.0%) | 2 (40.0%) |
| **Ties** | 0 | 0 |
| **Descriptive 95% CI of $\Delta$** | $[-0.01683, +0.01107]$ | $[-0.01244, +0.01253]$ |

---

## 5. Observed Checkpoint and Epoch Timing Patterns

A descriptive difference in best DEV checkpoint epoch timing was observed across the five seeds:

1. **Treatment Best DEV Checkpoint Timing:**
   - Across all five seeds, the unweighted Treatment arm reached its peak development metric at earlier epochs:
     - Seed 42: Epoch 5 (total 15 epochs)
     - Seed 101: Epoch 5 (total 15 epochs)
     - Seed 202: Epoch 6 (total 16 epochs)
     - Seed 303: Epoch 5 (total 15 epochs)
     - Seed 404: Epoch 7 (total 17 epochs)
   - Across the replicated runs, the unweighted treatment often reached its best DEV checkpoint earlier, but this observation alone does not establish a mechanism of faster convergence, overfitting, or feature dominance. The replicated result demonstrates variability in the effect of the loss-weight intervention rather than a stable performance advantage.
   - Mean measured runtime per treatment arm: ~28.8 seconds.

2. **Control Best DEV Checkpoint Timing:**
   - In contrast, the class-weighted Control arm reached its peak development metric at later epochs:
     - Seed 42: Epoch 10 (total 20 epochs)
     - Seed 101: Epoch 15 (total 25 epochs)
     - Seed 202: Epoch 27 (total 30 epochs)
     - Seed 303: Epoch 19 (total 29 epochs)
     - Seed 404: Epoch 21 (total 30 epochs)
   - Control trained for more epochs before early stopping triggered, achieving higher peak development scores than Treatment in 2 of the 4 prospective seeds (including the highest individual DEV mIoU observed across the entire study: **0.05886** at Epoch 15 in Seed 101, and 0.05191 at Epoch 19 in Seed 303).
   - While Control reached its peak DEV score later, this timing difference does not by itself prove a causal mechanism; it is recorded purely as a descriptive empirical trait of the training trajectories.
   - Mean measured runtime per control arm: ~49.6 seconds.

3. **Comparison with Historical Seed 42:**
   - In Seed 42, Treatment exceeded Control by +0.01171. However, under prospective random initializations (Seeds 101, 202, 303, 404), this advantage failed to hold consistently (Control won Seeds 101 and 303; Treatment won Seeds 202 and 404). The prospective replication evidence indicates that the single-run Seed 42 advantage was seed-sensitive rather than systematic.

---

## 6. Hardware & Experimental Environment Parity

The prospective replication was executed on a remote dedicated Kaggle worker with an NVIDIA GPU:
- **GPU Device:** NVIDIA Tesla T4 (Single GPU, 14.56 GB / 15,636,037,632 bytes VRAM)
- **CUDA Version:** 12.8
- **PyTorch Version:** `2.10.0+cu128`
- **cuDNN Version:** `91002`
- **Initial State Loading:** Canonical state `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D` verified bitwise identical on entry for all 8 arms (`initial_state_bitwise_equal == True`).
- **Data Loaders:** Standard PIL TIFF/PNG loader matching the frozen physical manifest hash (`F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102`).

---

## 7. Firewall Audit

- **HOLDOUT Partition Access Count:** **0**
- **Part III Payload Access Count:** **0**
- Hard quarantine firewalls remained fully active throughout the entire replication run. No holdout data was loaded, evaluated, or touched.

---

## 8. Artifact Provenance & Checksums

All artifacts are persisted in `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/` with complete SHA-256 integrity verified against `exp07_diag01_replication_manifest.json`:

| File | SHA-256 Checksum |
| :--- | :--- |
| `exp07_diag01_replication_aggregate.json` | `90236AAAE2C937775932D46E3CA57F54B19798364D3F7E2C63B3727D4F1AC2BB` |
| `exp07_diag01_replication_manifest.json` | `5C695E69B9E784D8E24FA7EBD7F09230553A81878E315024476F5E385D6F9EB4` |
| `seed_101/seed_101_paired_comparison.json` | `D158B0782840F83C66577992FF17A271D6E40ED7E3AE1EEFDEF0C547E1760005` |
| `seed_101/control/control_best_model.pt` | `86F1AF99128797DCD9024117B8BF9051FD2AD7575DFC2AD0BA4BCC87A6218F97` |
| `seed_101/treatment/treatment_best_model.pt` | `CDBA3618FE4A7BECA0D82B11E8E57BE9DD82DA31360C85A523A96577866B74FC` |
| `seed_202/seed_202_paired_comparison.json` | `E899C1415E0D0E076B6E5298BD0E5F0005F03F78B9711318D5BE36484BF24D0B` |
| `seed_202/control/control_best_model.pt` | `23DEFB142B43375F2E93A5E16590AE8843A87311A6221786FC43D539C5156E63` |
| `seed_202/treatment/treatment_best_model.pt` | `000D4E7E0D37CB6A6D562C7B81B8AD2CAE85483BE6BCE07706AD97F709EA1CDD` |
| `seed_303/seed_303_paired_comparison.json` | `B13BB1BA7F76A43AE1F4CCF1CFAD8CD67745A1C5A52218FC1A06685B0AFE7F66` |
| `seed_303/control/control_best_model.pt` | `1E5D948B323AA97AD1A0B381128C2697806E23973D30E31BD25313DA68E723DB` |
| `seed_303/treatment/treatment_best_model.pt` | `837068454D10BF82B8AE85A52D618CD99B7AED4F1E0371B034B73C763663FF8B` |
| `seed_404/seed_404_paired_comparison.json` | `BA2FAE4E185E68FCB7A702ACB2FC464F837822E777E9FC31CE0BA580AA08A7AD` |
| `seed_404/control/control_best_model.pt` | `E2F180A0439C75588EDCDFE27D72A4B5FCCF08C4EB5BB3AB8B50CA5E4217B3A3` |
| `seed_404/treatment/treatment_best_model.pt` | `B8286A1CD00EF5D1CA1E00BCC4A8211BEBF751A96832D91E1439F1061C3D1D79` |

---

## 9. Scientific Classification & Operational Recommendation

### Scientific Classification: `CASE B`
The C22-B single-run observation (+0.01171 at Seed 42) does **NOT** replicate as a systematic development-set advantage under prospective random seeds. Across prospective seeds, the effect is neutral to slightly negative (mean delta $-0.00288$), and across all five paired seeds, the mean delta is $+0.00004$ with wide variance.

### Operational Recommendation:
1. **Maintain Canonical Weighting:** The Ocean Sentinel canonical training protocol must **retain** the C16 sqrt-median-frequency class weighting policy.
2. **Do Not Adopt Uniform Weighting:** Uniform weighting does not confer a reproducible advantage and demonstrates substantial effect variability across seeds.
3. **Transition State:** The replication phase is `COMPLETED_VALID`. No modification to the canonical baseline or holdout evaluation is justified by this experiment.
