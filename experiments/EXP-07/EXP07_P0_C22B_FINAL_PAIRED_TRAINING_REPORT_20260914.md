# EXP-07-P0-C22-B — EXP07_DIAG01 FINAL PAIRED TRAINING REPORT
**Date:** 2026-09-14  
**Task ID:** EXP-07-P0-C22-B (Audited & Repaired in EXP-07-P0-C22-C)  
**Experiment ID:** EXP07_DIAG01  
**Project:** Ocean Sentinel (`D:\Projects\ocean-sentinel`)  
**Branch:** `master`  
**Execution Environment:** Remote Kaggle Cloud GPU (NVIDIA Tesla T4, 15.64 GB VRAM)  
**Final Status:** `COMPLETED_VALID` (Classification: `VALID_SINGLE_RUN_OBSERVATION`)

---

## Executive Summary

The authorized single-variable diagnostic experiment **EXP07_DIAG01 (EXP-07-P0-C22-B)** has completed execution in full compliance with the frozen Ocean Sentinel scientific protocol (`OPS02_v1.0.1_FROZEN`).

The objective was to test the preregistered single-variable hypothesis:
> **Hypothesis:** Canonical class-loss weighting alters optimization trajectory and development performance on OPS-02 relative to uniform unweighted loss under identical deterministic initialization and optimization dynamics.

### Primary Outcome
| Metric / Arm | Control (Arm A: Sqrt-Median-Freq) | Treatment (Arm B: Uniform Unweighted) | $\Delta$ (Treatment - Control) | Relative % |
| :--- | :--- | :--- | :--- | :--- |
| **Loss Vector** | Canonical C16 (12 elements) | Uniform 1.0 (12 elements) | Single-variable intervention | — |
| **Initial State SHA-256** | `67181C4ECD420DE...` | `67181C4ECD420DE...` | **Bitwise Identical** (`B472DB...`) | $0.0\%$ |
| **Candidate F Sampler** | Seed 42, 72 draws/epoch | Seed 42, 72 draws/epoch | **Identical Schedule** (`2B1562...`) | $0.0\%$ |
| **Total Epochs Trained** | 20 epochs | 15 epochs | Early stop (patience=10) | — |
| **Best Epoch** | **Epoch 10** | **Epoch 5** | -5 epochs | — |
| **Best DEV mIoU (Phenomena)** | **0.04147** | **0.05318** | **+0.01171** | **+28.24%** |

Both arms trained under identical hardware (NVIDIA Tesla T4), identical PyTorch/CUDA runtime, bitwise-identical initial model states, and identical stochastic draw schedules. Zero HOLDOUT payload access occurred (`holdout_access_count == 0`), and zero Part III access occurred (`part_iii_access_count == 0`).

---

## Section A: Objective and Hypothesis

### 1. Objective
To execute a strictly controlled, paired single-variable diagnostic experiment comparing:
- **Arm A (Control):** Canonical C16 square-root median-frequency class-weighted cross-entropy loss.
- **Arm B (Treatment):** Uniform unweighted cross-entropy loss (`weight=1.0` for all 12 classes).

### 2. Preregistered Hypothesis
The preregistered hypothesis tested whether canonical class-loss weighting alters optimization trajectory and development performance on OPS-02 relative to uniform unweighted loss under identical deterministic initialization and optimization dynamics.

---

## Section B: Exact Frozen Configuration

All 19 invariants established during Phase C19–C22A9 were programmatically verified prior to and during training:

1. **Dataset Specification:** `OPS02_v1.0.1_FROZEN`
2. **Physical Manifest:** `data/ops02/manifests/ops02_physical_dataset_manifest_v1.json` (SHA-256: `F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102`)
3. **Partition Sample Breakdown:** 132 TRAIN, 40 DEV, 40 HOLDOUT (Total: 212 physical tile pairs)
4. **Partition Independence Count:** 40 TRAIN clusters/datatakes, 12 DEV clusters/datatakes, 12 HOLDOUT clusters/datatakes (Total: 64 parent clusters, 0 partition leakage)
5. **Canonical Initial State:** `data/ops02/initial_model_state_canonical.pt` (SHA-256: `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D`)
6. **Pretrained Backbone:** `resnet18-f37072fd.pth` (SHA-256: `F37072FD47E89C5E827621C5BAFFA7500819F7896BBACEC160B1A16C560E07EC`)
7. **Model Architecture:** ResNet18-UNet (Option B: 14,310,860 parameters, 30 BatchNorm2d layers, BN momentum = 0.05)
8. **Input Modality:** Single-band VV SAR (`[B, 1, 256, 256]`, float32)
9. **Preprocessing Pipeline:** Valid DN > 0, `log1p(max(raw, 0))`, standardized with TRAIN mean $\mu = 4.424158$, standard deviation $\sigma = 0.469261$, unmasked nodata zeroed.
10. **Dense Taxonomy (12 classes):**
    - 0: Background (BG)
    - 1: Atmospheric Front (AF)
    - 2: Boundary Slick (BS)
    - 3: Low Wind Area (LWA)
    - 4: Macro-algal Canopy / Coral (MCC)
    - 5: Oceanic Front (OF)
    - 6: Polar Oceanic Wind (POW)
    - 7: Rain Footprint (RF)
    - 8: Wind Slick (WS)
    - 9: Eddy
    - 10: Internal Waves (IWs)
    - 11: Artificial / Anthropogenic Objects (HM)
11. **Excluded Source Labels:** 3, 9, 14 $\rightarrow$ `ignore_index = -100`
12. **Optimizer:** AdamW ($\text{lr} = 5\times 10^{-4}$, $\text{weight\_decay} = 0.01$ applied strictly to 2D weights; biases and 1D BN parameters excluded, $\beta = (0.9, 0.999)$, $\epsilon = 10^{-8}$)
13. **Scheduler:** LinearWarmupCosineAnnealingLR ($T_{\max} = 30$, warmup epochs = 3, $\eta_{\min} = 10^{-6}$)
14. **Batch Dynamics:** Physical batch size = 8, BatchNorm statistical batch = 8, gradient accumulation = 2, effective optimizer batch size = 16.
15. **Gradient Clipping:** Max norm = 1.0
16. **Sampling Strategy:** Candidate F Hybrid (70% parent-balanced, 30% class-balanced, 72 draws/epoch, replacement=True, seed=42)
17. **Augmentation:** Completely disabled (`AUGMENTATION = False`)
18. **Schedule Bounds:** Max epochs = 30, Min epochs = 15, Patience = 10
19. **Primary Development Metric:** `dev_mIoU_phenomena` (macro mean IoU across phenomena classes 1..11, Class 0 Background excluded).

---

## Section C: Environment and Hardware Reality

Execution was performed on remote cloud GPU infrastructure to adhere to battery/power safety governance rules:
- **Platform:** Remote Kaggle Cloud Worker
- **Device ID:** `cuda:0`
- **GPU Model:** NVIDIA Tesla T4
- **Total VRAM:** 14.56 GB ($15,636,037,632$ bytes)
- **CUDA Driver/Runtime:** CUDA 12.8
- **PyTorch Version:** `2.10.0+cu128`
- **cuDNN Version:** 91002
- **Kernel Identifier:** `dheeraj12237/ocean-sentinel-exp07-c22b-diag01` (Version 2)
- **Local Host Role:** Orchestration, preflight verification, artifact retrieval, and forensic regression auditing only (0 local training steps).

---

## Section D: Control Arm Initialization and Configuration

- **Arm Name:** `CONTROL`
- **Loss Vector (Exact 12-element canonical weights):**
  ```python
  [
      0.403935, 2.450546, 0.876692, 0.945945, 0.648189, 4.211476,
      0.719641, 2.956203, 1.064525, 1.882870, 0.387652, 18.243211
  ]
  ```
- **Initial State Tensor Fingerprint:** `B472DBA86C0AA9CB1821B6C6CB172D8DCD93CE556AA256BDE931558D965F749C`
- **Initial Canonical Checkpoint Source:** `dheeraj12237/ocean-sentinel-canonical-initial-state/initial_model_state_canonical.pt` (SHA-256: `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D`)

---

## Section E: Treatment Arm Initialization and Configuration

- **Arm Name:** `TREATMENT`
- **Loss Vector (Uniform unweighted):**
  ```python
  [
      1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
      1.0, 1.0, 1.0, 1.0, 1.0, 1.0
  ]
  ```
- **Initial State Tensor Fingerprint:** `B472DBA86C0AA9CB1821B6C6CB172D8DCD93CE556AA256BDE931558D965F749C`
- **Isolation Guarantee:** Treatment was re-instantiated directly from `initial_model_state_canonical.pt` after GPU memory purging (`torch.cuda.empty_cache()` and garbage collection). **Treatment inherited ZERO weights or optimizer states from Control.**

---

## Section F: Evidence that the Two Arms Differed Only in Loss Vector

1. **Model Weights at Epoch 0:** Bitwise identical across all 192 tensors (Fingerprint: `B472DBA86C0AA9CB1821B6C6CB172D8DCD93CE556AA256BDE931558D965F749C`).
2. **Optimizer & Parameter Groups:** Identical 2-group AdamW configuration (Group 0: 2D weights with weight_decay=0.01; Group 1: bias/1D BN weights with weight_decay=0.0).
3. **Stochastic Data Order:** Identical precomputed Candidate F batch sequence across all epochs (Schedule SHA-256: `2B1562E33FF32F73A8BF373D24951AF220E423FF74F12F7B589CEDA426A6834B`).
4. **Learning Rate Schedule:** Identical LinearWarmupCosineAnnealingLR ($T_{\max}=30$, warmup=3, $\eta_{\min}=10^{-6}$).
5. **Architectural & Batch Parity:** Identical batch size (8), gradient accumulation (2), and clipping (1.0).
6. **Loss Formulation Difference:** Strictly the parameter `weight=w` in `nn.CrossEntropyLoss(weight=w, ignore_index=-100, reduction="mean")`.

---

## Section G: Training Curves / Epoch History

### Arm A: Control Epoch-by-Epoch History
| Epoch | Train Loss | DEV Loss | DEV mIoU (Phenomena) | Best So Far | LR | Duration |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 2.56775 | 2.46276 | 0.00006 | 0.00006 (Ep 1) | 3.33e-4 | 6.8s |
| 2 | 2.52985 | 2.45935 | 0.00006 | 0.00006 (Ep 1) | 5.00e-4 | 3.7s |
| 3 | 2.47176 | 2.51476 | 0.00671 | 0.00671 (Ep 3) | 5.00e-4 | 3.6s |
| 4 | 2.43570 | 3.16025 | 0.02738 | 0.02738 (Ep 4) | 4.98e-4 | 3.6s |
| 5 | 2.36858 | 3.40504 | 0.03674 | 0.03674 (Ep 5) | 4.93e-4 | 3.6s |
| 6 | 2.37025 | 5.27304 | 0.01989 | 0.03674 (Ep 5) | 4.85e-4 | 3.6s |
| 7 | 2.40068 | 9.70610 | 0.01871 | 0.03674 (Ep 5) | 4.73e-4 | 3.6s |
| 8 | 2.31402 | 2.60338 | 0.03133 | 0.03674 (Ep 5) | 4.59e-4 | 3.6s |
| 9 | 2.31935 | 3.45472 | 0.02941 | 0.03674 (Ep 5) | 4.42e-4 | 3.7s |
| **10** | **2.29980** | **2.34518** | **0.04147** | **0.04147 (Ep 10)** | **4.22e-4** | **3.6s** |
| 11 | 2.32576 | 2.41885 | 0.04075 | 0.04147 (Ep 10) | 3.99e-4 | 3.7s |
| 12 | 2.27693 | 3.14567 | 0.02875 | 0.04147 (Ep 10) | 3.75e-4 | 3.7s |
| 13 | 2.24720 | 2.36310 | 0.04136 | 0.04147 (Ep 10) | 3.49e-4 | 3.6s |
| 14 | 2.23256 | 2.47065 | 0.03359 | 0.04147 (Ep 10) | 3.22e-4 | 3.6s |
| 15 | 2.24458 | 2.57355 | 0.03421 | 0.04147 (Ep 10) | 2.93e-4 | 3.7s |
| 16 | 2.12180 | 2.56099 | 0.03251 | 0.04147 (Ep 10) | 2.65e-4 | 3.6s |
| 17 | 2.18220 | 2.33905 | 0.03294 | 0.04147 (Ep 10) | 2.35e-4 | 3.6s |
| 18 | 2.21709 | 2.36166 | 0.03416 | 0.04147 (Ep 10) | 2.07e-4 | 3.6s |
| 19 | 2.10632 | 2.37611 | 0.03914 | 0.04147 (Ep 10) | 1.78e-4 | 3.6s |
| 20 | 2.10349 | 2.39650 | 0.03272 | 0.04147 (Ep 10) | 1.51e-4 | 3.7s |
*Early stopping triggered at Epoch 20 (patience = 10 epochs post-best epoch 10).*

### Arm B: Treatment Epoch-by-Epoch History
| Epoch | Train Loss | DEV Loss | DEV mIoU (Phenomena) | Best So Far | LR | Duration |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 2.59107 | 2.45801 | 0.00006 | 0.00006 (Ep 1) | 3.33e-4 | 3.7s |
| 2 | 2.54520 | 2.44882 | 0.00021 | 0.00021 (Ep 2) | 5.00e-4 | 3.6s |
| 3 | 2.43986 | 2.86059 | 0.00583 | 0.00583 (Ep 3) | 5.00e-4 | 3.6s |
| 4 | 2.39772 | 2.86964 | 0.03383 | 0.03383 (Ep 4) | 4.98e-4 | 3.7s |
| **5** | **2.28436** | **4.22013** | **0.05318** | **0.05318 (Ep 5)** | **4.93e-4** | **3.6s** |
| 6 | 2.27476 | 3.89799 | 0.02791 | 0.05318 (Ep 5) | 4.85e-4 | 3.6s |
| 7 | 2.33169 | 6.58257 | 0.02113 | 0.05318 (Ep 5) | 4.73e-4 | 3.6s |
| 8 | 2.22759 | 2.63320 | 0.03643 | 0.05318 (Ep 5) | 4.59e-4 | 3.6s |
| 9 | 2.21383 | 2.47604 | 0.03540 | 0.05318 (Ep 5) | 4.42e-4 | 3.6s |
| 10 | 2.17444 | 2.27191 | 0.03203 | 0.05318 (Ep 5) | 4.22e-4 | 3.7s |
| 11 | 2.26336 | 2.28407 | 0.03795 | 0.05318 (Ep 5) | 3.99e-4 | 3.7s |
| 12 | 2.18274 | 2.26659 | 0.05049 | 0.05318 (Ep 5) | 3.75e-4 | 3.6s |
| 13 | 2.14617 | 2.21910 | 0.04882 | 0.05318 (Ep 5) | 3.49e-4 | 3.6s |
| 14 | 2.10401 | 2.17866 | 0.04324 | 0.05318 (Ep 5) | 3.22e-4 | 3.6s |
| 15 | 2.13417 | 2.16656 | 0.04275 | 0.05318 (Ep 5) | 2.93e-4 | 3.7s |
*Early stopping triggered at Epoch 15 (MIN_EPOCHS=15 reached and patience=10 satisfied post-best epoch 5).*

---

## Section H & I: Primary Metric and Secondary Descriptive Diagnostics

### 1. Primary Development Metric Comparison
- **Control Best `dev_mIoU_phenomena`:** `0.04147` (achieved at Epoch 10)
- **Treatment Best `dev_mIoU_phenomena`:** `0.05318` (achieved at Epoch 5)
- **Delta ($\text{Treatment} - \text{Control}$):** `+0.01171` (`+28.24%` relative change based on `(delta / control) * 100`)

### 2. Per-Class IoU Breakdown (Best Checkpoint Evaluation)
| Class Index | Class Acronym | Canonical Class Name | Control IoU (Ep 10) | Treatment IoU (Ep 5) | Absolute Delta | Percentage Assessment |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| *0* | *BG* | *Background (Excluded from primary)* | *0.01198* | *0.00502* | *-0.00696* | *-58.10%* |
| 1 | AF | Atmospheric Front | 0.00005 | 0.00000 | -0.00005 | -100.00% (Near-zero baseline $5\times 10^{-5}$) |
| 2 | BS | Boundary Slick | 0.04431 | 0.09515 | **+0.05084** | **+114.74% (Substantial baseline)** |
| 3 | LWA | Low Wind Area | 0.00068 | 0.00549 | **+0.00481** | **+707.35% (Elevated by small baseline)** |
| 4 | MCC | Macro-algal Canopy / Coral | 0.26843 | 0.21160 | -0.05683 | -21.17% (Substantial baseline) |
| 5 | OF | Oceanic Front | 0.00043 | 0.00011 | -0.00032 | -74.42% (Near-zero baseline $0.00043$) |
| 6 | POW | Polar Oceanic Wind | 0.02849 | 0.00295 | -0.02554 | -89.65% (Substantial baseline) |
| 7 | RF | Rain Footprint | 0.00000 | 0.00000 | 0.00000 | **UNDEFINED (Zero baseline)** |
| 8 | WS | Wind Slick | 0.01544 | 0.00000 | -0.01544 | -100.00% (Substantial baseline) |
| 9 | Eddy | Eddy | 0.00201 | 0.00639 | **+0.00438** | **+217.91% (Elevated by small baseline)** |
| 10 | IWs | Internal Waves | 0.09634 | 0.26326 | **+0.16692** | **+173.26% (Substantial baseline)** |
| 11 | HM | Artificial / Anthropogenic Objects | 0.00000 | 0.00000 | 0.00000 | **UNDEFINED (Zero baseline)** |
| **1..11** | **Mean** | **Phenomena Macro mIoU** | **0.04147** | **0.05318** | **+0.01171** | **+28.24%** |

### 3. Detailed Class-Wise Observations
- **Internal Waves (IWs):** Treatment showed higher DEV segmentation performance ($0.09634 \rightarrow 0.26326$, absolute delta $+0.16692$, relative $+173.3\%$). In the control arm, IWs was assigned a lower loss weight ($0.387652$) under sqrt-median-frequency weighting due to high training pixel prevalence, whereas uniform weighting treats all classes symmetrically ($1.0$).
- **Boundary Slicks (BS):** Treatment improved from $0.04431 \rightarrow 0.09515$ ($+0.05084$).
- **Eddy & Low Wind Area (LWA):** Treatment achieved higher IoUs on both ($+0.00438$ and $+0.00481$ absolute gains respectively, though relative percentages are inflated due to small baselines).
- **Macro-algal Canopy (MCC):** Control maintained higher IoU ($0.26843$ vs $0.21160$), where moderate down-weighting ($0.648189$) balanced favorably.
- **Polar Oceanic Wind (POW) & Wind Slicks (WS):** Control achieved better scores ($0.02849$ vs $0.00295$, and $0.01544$ vs $0.00000$).
- **Rare Classes (RF, HM):** Both models registered $0.0$ IoU on Rain Footprints and Artificial / Anthropogenic Objects under early stopping. The absolute delta for both classes is $0.00000$, and relative percentage changes are mathematically undefined due to zero baselines.

---

## Section J & K: Best Epoch and Delta Summary

- **Control Best Epoch:** 10
- **Treatment Best Epoch:** 5
- **Delta `dev_mIoU_phenomena`:** $+0.01171$
- **Relative Improvement:** $+28.24\%$
- **Model Selection Context:** The best DEV checkpoints occurred at different epochs under early stopping (patience=10). This constitutes a valid model-selection observation for this run, but does NOT establish that uniform weighting converges universally faster across seeds.

---

## Section L: Artifact Inventory and SHA-256 Hashes

All artifacts reside in `experiments/EXP-07/runs/EXP07_DIAG01/` and have been cryptographically verified against the run manifest:

| Artifact Filename | Description | File Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| `control_best_model.pt` | Model checkpoint at Control Best Epoch (Ep 10) | ~55 MB | `FF98D4A93660BC70016FEEAF2F04450B7AC1110226DECBAE027F71FF286633FA` |
| `control_last_model.pt` | Model checkpoint at Control Final Epoch (Ep 20) | ~55 MB | `079A476F86BA581AE15F2FA7F2E4DAA274BF9D38C63358800E3C84B03B73B9C1` |
| `control_history.json` | Full 20-epoch training and DEV metrics for Control | 4.6 KB | `699B2B01D713EE40AD0801E318B87DBF1174290D5B5239601236CA0D8C496DA3` |
| `control_metrics.json` | Summary metrics and best epoch evaluations for Control | 1.1 KB | `07B43F8B8959A8EDB2B0F5155E2A1BB65A7C717160B8A3B5AE64C73C06AB4D69` |
| `treatment_best_model.pt` | Model checkpoint at Treatment Best Epoch (Ep 5) | ~55 MB | `0B7F51B1E902AAC9DF839D2864F1E9658F3B0631813FC47D8ADA1738FFC47745` |
| `treatment_last_model.pt` | Model checkpoint at Treatment Final Epoch (Ep 15) | ~55 MB | `4AFE95A823BE69A4DF4921BAE394C0F846B239728524B1C2704D37754E117573` |
| `treatment_history.json` | Full 15-epoch training and DEV metrics for Treatment | 3.5 KB | `020BF4F22147E03F370B80A53F00B31264F4F6DEFF1A037E7CBBB85B0ED2A420` |
| `treatment_metrics.json` | Summary metrics and best epoch evaluations for Treatment | 1.1 KB | `5397F75CC0CC03874C2262AF233024BFB7602B60ACC3DEBAA1BF1378217D810D` |
| `exp07_diag01_paired_comparison.json` | Machine-readable paired evaluation report | 4.4 KB | `18CE7AD59694FE3FC90BEC831527043E2331B2A3A5D8F3AB7814465F7EE418F9` |
| `exp07_diag01_manifest.json` | Cryptographic manifest of output artifacts | 875 B | `611C54D857EC0740E7D38D64F5050C3A004C7BCBFFEC84992564259A845C3F03` |
| `ocean-sentinel-exp07-c22b-diag01.log` | Kaggle worker stdout/stderr execution log | 12.8 KB | `8B0D701DC972A0D81CC18C4BC1C80E10AC6732B03CEACCAE45E8F3D1F5B0CA8E` |

---

## Section M: Reproducibility Evidence

Every step of this experiment can be independently replicated bitwise:
1. **Container Environment:** Kaggle Python 3.12, PyTorch 2.10.0+cu128, NVIDIA Tesla T4 GPU.
2. **Deterministic Sampler:** Candidate F draws generated using explicit PyTorch generators seeded with `seed = 42 + epoch * 1000`. Schedule hash: `2B1562E33FF32F73A8BF373D24951AF220E423FF74F12F7B589CEDA426A6834B`.
3. **Data Feeds:** Input pairs read directly from uncalibrated raw DN and log1p standardized with fixed constants $(\mu=4.424158, \sigma=0.469261)$.
4. **Seed Invariance:** Control and Treatment initialized from bitwise-identical starting tensor state `B472DBA86C0AA9CB1821B6C6CB172D8DCD93CE556AA256BDE931558D965F749C`.

---

## Section N: Infrastructure Events and Retries

- **Version 1 Attempt:** Pushed script to Kaggle. Discovered that script-only pushes do not persist accompanying large binary checkpoints into `/kaggle/src/`. Reconstructing initial state inside container on newer PyTorch/Python produced minor floating-point divergence in CPU model generation.
- **Remediation:** Staged `initial_model_state_canonical.pt` into dedicated private Kaggle dataset `dheeraj12237/ocean-sentinel-canonical-initial-state`. Mounted dataset in kernel Version 2.
- **Version 2 Execution:** Succeeded on first attempt with 0 errors, full preflight assertion passes, clean training curves, and automatic artifact packaging.

---

## Section O & P: HOLDOUT and Part III Access Confirmations

- **HOLDOUT Access Count:** `0` (Quarantined; zero test or validation reads occurred against HOLDOUT partitions).
- **Part III Access Count:** `0` (Quarantined; zero external benchmark reads).

---

## Section Q: Git and Source Control Audit

- **Branch:** `master`
- **Tracked Modifications Preserved:**
  - `.gitignore`
  - `src/ocean_sentinel/ingestion/dataset.py`
- **Staged Modifications:** `0`
- **Commits / Pushes / Resets / Stashes:** `0` executed during this run.
- **Process Cleanliness:** Zero orphan background processes running.

---

## Section R: Scientific Interpretation with Explicit Evidence Levels

### Level 1: DIRECTLY OBSERVED (Level 5 Machine Proof)
- Under the frozen OPS-02 protocol, unweighted CrossEntropyLoss achieved higher peak `dev_mIoU_phenomena` ($0.05318$) than canonical sqrt-median-frequency weighted loss ($0.04147$).
- The delta is $+0.01171$ ($+28.24\%$).
- The improvement was driven predominantly by higher segmentation performance on dominant natural oceanic phenomena: Internal Waves ($+0.16692$) and Boundary Slicks ($+0.05084$).
- Canonical class-loss weighting achieved higher performance on Macro-algal Canopy / Coral ($0.26843$ vs $0.21160$) and Polar Oceanic Winds ($0.02849$ vs $0.00295$).
- In both arms, rare classes RF (Rain Footprint) and HM (Artificial / Anthropogenic Objects) scored $0.0$ IoU on DEV.

### Level 2: SUPPORTED BY EVIDENCE
- Under the frozen OPS-02 protocol, the weighted-loss control produced lower peak DEV mIoU than the uniform-loss treatment in this paired run. The observed class-level pattern is consistent with the intervention changing optimization emphasis, but the specific mechanism affecting boundary resolution or convergence is not established by this experiment.
- In this run, class weighting acted as an empirical trade-off across classes (favoring MCC and POW in Control, and favoring BS, LWA, Eddy, and IWs in Treatment) rather than monotonically improving all categories.

### Level 3: NOT ESTABLISHED (Must NOT be Claimed)
- Universal superiority of uniform weighting over class weighting across all SAR tasks or future architectures.
- Generalization to unseen geographic domains, other satellite sensors, or full multi-frequency SAR.
- Statistical significance across multiple seeds (this run tested seed 42 specifically as preregistered).
- Superiority or generalization on HOLDOUT.
- Causal attribution of aggregate cross-entropy loss without explicit per-class loss decomposition.
- Robustness across repeated training runs.

---

## Section S: Limitations

1. **Single Random Seed:** This experiment evaluates Seed 42 only. Multi-seed replication (e.g. Seeds 42, 101, 202) is strictly required before changing baseline policies.
2. **Early Stopping Dynamics:** Treatment peaked at Epoch 5 before over-fitting to the 132 training datatakes, triggering early stopping at Epoch 15. Control peaked at Epoch 10 and stopped at Epoch 20.
3. **Severe Class Imbalance:** Extremely rare classes (RF, HM) remained unlearned under both uniform and inverse-frequency weighting under current capacity and data scale.

---

## Section T: Final Experiment Status

The experimental protocol, preflight assertions, execution parity, checkpoint preservation, and regression suite have executed without deviation or failure.

$$\mathbf{EXP07\_DIAG01 = COMPLETED\_VALID \quad (Classification: \ VALID\_SINGLE\_RUN\_OBSERVATION)}$$

---

## Section U: Forensic Reconciliation & Erratum (EXP-07-P0-C22-C)

In accordance with the C22-C forensic review, the following report repairs and corrections were executed:
1. **Taxonomy Repair (HM & OF):** Replaced non-canonical historical shorthand for Class 11 with the authoritative canonical taxonomy name **Artificial / Anthropogenic Objects (HM)** and confirmed **Oceanic Front (OF)** across all sections and tables.
2. **Causal Language Calibration:** Replaced speculative mechanistic assertions regarding spatial feature resolution and convergence rates with calibrated empirical statements reflecting that causal mechanisms were not directly measured.
3. **Removal of Unsupported Loss Attribution:** Excised the unverified statement attributing aggregate DEV loss differences to background, as aggregate DEV cross-entropy loss alone does not provide a per-class loss decomposition.
4. **Percentage Interpretation Safeguards:** Explicitly annotated that percentage changes on classes with zero or near-zero baselines (RF, HM, AF, LWA, OF, Eddy) are mathematically undefined or unstable, establishing absolute IoU delta as the primary descriptive standard.
5. **Separation of Checkpoint Selection and Robustness:** Clarified that peak DEV epochs (Ep 10 vs Ep 5) represent early-stopping model selection events on a single seed, not generalized convergence rates.
