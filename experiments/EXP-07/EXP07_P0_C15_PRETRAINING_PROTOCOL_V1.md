# EXP-07-P0-C15: Authoritative Pre-Training Protocol (v1.0)

**Project:** Ocean Sentinel  
**Phase:** EXP-07-P0-C15  
**Dataset Target:** OPS-02 (`OPS02_v1.0.0_FROZEN`)  
**Date:** 2026-09-14  
**Authoritative Status:** PROTOCOL SPECIFICATION ONLY — TRAINING STRICTLY PROHIBITED IN C15  

---

## 1. Executive Summary & Epistemic Boundaries

This document defines the frozen mathematical, architectural, and operational training protocol for future authorized model training on the expanded **OPS-02** dataset. 

> [!IMPORTANT]
> **Zero Training Authorization:** This document is a specification. It does NOT authorize training execution within C15. Training may only begin after formal user authorization following the C15 review.

---

## 2. Dataset Contract & Partition Quarantine

- **Frozen Dataset Version:** `OPS02_v1.0.0_FROZEN` (Manifest: `data/ops02/manifests/ops02_physical_dataset_manifest_v1.json`).
- **Active Development Splits:**
  - **TRAIN:** 40 independent parent clusters (40 mission datatakes, 54 Level-1 scenes), 132 physical sample pairs ($256 \times 256$ float32 image + $256 \times 256$ uint8 mask).
  - **DEV:** 12 independent parent clusters (12 mission datatakes, 15 Level-1 scenes), 41 physical sample pairs.
- **Quarantined Future Benchmark:**
  - **HOLDOUT:** 12 independent parent clusters (12 mission datatakes, 16 Level-1 scenes), 39 physical sample pairs.
  - **Firewall Invariant:** Zero model loading, zero forward inference, zero threshold calibration, zero hyperparameter selection, and zero normalization derivation from HOLDOUT during model training or checkpoint selection.

---

## 3. Input Domain & Radiometric Preprocessing

- **Mathematical Domain:** `AGGREGATED_RAW_DN_LOG1P_STANDARDIZED`
  - Input represents 10x10 block-mean aggregated raw detected digital numbers ($DN$) from Sentinel-1 Level-1 GRD IW mode measurements.
  - **Explicit Non-Calibration Notice:** Input is NOT physical radar backscatter ($\sigma^0$ or $\gamma^0$). Radiometric calibration LUTs and noise vectors have not been inverted or applied.
- **Validity Mask:**
  $$\text{validity\_mask} = (DN > 0.0)$$
  Border padding pixels ($DN = 0.0$) are strictly masked out.
- **Radiometric Transform:**
  $$x_{\text{log1p}} = \ln(1.0 + \max(DN, 0.0))$$
- **Standardization Contract:**
  $$x_{\text{norm}} = \frac{x_{\text{log1p}} - \mu_{\text{train}}}{\sigma_{\text{train}}}$$
  $$\text{where } \mu_{\text{train}} = 4.424158, \quad \sigma_{\text{train}} = 0.469261$$
  - Derived strictly from the 8,595,330 valid pixels of the 132 OPS-02 TRAIN samples. Zero leakage from DEV or HOLDOUT.
  - Invalid border pixels are zeroed in model tensor input: $x_{\text{norm}}[\neg \text{validity\_mask}] = 0.0$.

---

## 4. Canonical Multiclass Taxonomy & Remapping

- **Dense Output Classes (0..11):**
  - 0: Background Seawater (`BG`)
  - 1: Atmospheric Front (`AF`)
  - 2: Biological Slicks (`BS`)
  - 3: Low Wind Area (`LWA`)
  - 4: Mesoscale Cellular Convection (`MCC`)
  - 5: Ocean Front (`OF`) — *strictly natural front, NOT oil*
  - 6: Pure Ocean Wave (`POW`)
  - 7: Rain Cell / Rain Footprint (`RF`)
  - 8: Wind Streak (`WS`)
  - 9: Oceanic Eddy (`Eddy`)
  - 10: Internal Waves (`IWs`)
  - 11: Artificial / Anthropogenic Objects (`HM`) — *ships, platforms, structures*
- **Quarantined / Excluded Source Labels:**
  - Source 14: Mineral Oil Spill (Quarantined under `GOV-RULE-060`)
  - Source 3: Iceberg (Excluded from EXP-07 scope)
  - Source 9: Sea Ice (Excluded from EXP-07 scope)
- **Target Encoding:** Handled via `remap_source_mask_to_dense(source_mask, validity_mask)` where excluded classes and border padding are mapped to `IGNORE_INDEX = -100`.

---

## 5. Model Architecture Specification

- **Architecture Family:** ResNet18-UNet (Option B BatchNorm baseline, `src/ocean_sentinel/ml/exp07_reference.py::ResNet18UNet`).
- **Input Channels:** 1 (SAR VV single polarization).
- **Output Channels:** 12 (Dense logits for classes 0..11, linear head, no activation function).
- **Trainable Parameters:** Exactly 14,310,860 weights.
- **Normalization Layers:** Exactly 30 `BatchNorm2d` layers.
- **Encoder:** Standard ResNet18 backbone initialized with ImageNet pre-trained weights or random initialization depending on replicate contract (Seed 42 protocol uses standard ImageNet pretrained encoder weights).
- **Decoder:** 4-stage convolutional transpose upsampling with skip-connections and ReLU activations.

---

## 6. Optimization, Loss, & Batch Dynamics

- **Loss Function:** `nn.CrossEntropyLoss(weight=class_weights, ignore_index=-100)`
  - **OPS-02 TRAIN Square-Root Median-Frequency Weights:**
    - Class 0 (`BG`): 0.403935
    - Class 1 (`AF`): 2.450546
    - Class 2 (`BS`): 0.876692
    - Class 3 (`LWA`): 0.945945
    - Class 4 (`MCC`): 0.648189
    - Class 5 (`OF`): 4.211476
    - Class 6 (`POW`): 0.719641
    - Class 7 (`RF`): 2.956203
    - Class 8 (`WS`): 1.064525
    - Class 9 (`Eddy`): 1.882870
    - Class 10 (`IWs`): 0.387652
    - Class 11 (`HM`): 18.243211
- **Optimizer:** `torch.optim.AdamW`
  - Base learning rate: $\eta = 5 \times 10^{-4}$
  - Weight decay: $\lambda = 0.01$ (applied to 2D convolutional/linear weights; bias and 1D BN weights excluded)
  - Betas: $(0.9, 0.999)$, Epsilon: $1 \times 10^{-8}$
- **Gradient Clipping:**
  - Method: `torch.nn.utils.clip_grad_norm_`
  - Maximum norm: $1.0$, Norm type: $2.0$
- **Learning Rate Scheduler:**
  - `LinearWarmupCosineAnnealingLR`
  - Total Epochs: 30
  - Warmup Epochs: 3 (linear increase from $1 \times 10^{-6}$ to $5 \times 10^{-4}$)
  - Cosine Decay Epochs: 27 (decay from $5 \times 10^{-4}$ down to $\eta_{\min} = 1 \times 10^{-6}$)
- **Batch Dynamics:**
  - Minibatch size (per GPU forward/backward): $B_{\text{mini}} = 8$
  - Gradient Accumulation Steps: 2
  - Effective Virtual Optimizer Batch Size: $B_{\text{opt}} = 16$
  - BatchNorm Statistical Batch Size: $B_{\text{BN}} = 8$

---

## 7. Deterministic Sampling Strategy

- **Sampler:** Candidate F Hybrid Sampler (`src/ocean_sentinel/ml/exp07_reference.py::compute_candidate_f_hybrid_weights`).
  - Mixture: $70\%$ Parent-Cluster Balanced ($P_{\text{parent}}$) $+ 30\%$ Phenomenon-Presence Balanced ($P_{\text{presence}}$).
  - Sampling Mode: With replacement.
  - Draws per Epoch: Fixed at 72 tiles per epoch (or scaled to 108 draws for OPS-02 expanded pool).
  - Determinism: Per-epoch manual generator seed: $\text{seed} + \text{epoch} \times 1000$.

---

## 8. Evaluation & Model Selection Gate

- **Validation Frequency:** Evaluated at the conclusion of every training epoch on all 41 DEV samples.
- **Monitored Metric:** `dev_mIoU_phenomena`
  - Defined as the mean IoU across phenomena classes $1 \dots 11$ (excluding background Class 0).
  - Classes with 0 true and 0 predicted pixels in the evaluation set are excluded from the denominator to avoid penalizing partition sparsity.
- **Model Checkpoint Retention:**
  - `best_model.pt`: Checkpoint with highest `dev_mIoU_phenomena`.
  - `last_model.pt`: Checkpoint at completion of epoch 30.
- **Confusion Matrix:** Full $12 \times 12$ confusion matrix tracked across epochs.

---

## 9. Replicate Policy & Statistical Invariants

- **Historical Replicates:**
  - Run 001 (Seed 42): Completed in C8 on OPS-01 (`dev_mIoU_phenomena = 0.4072`).
  - Run 002 (Seed 101): Completed in C10 on OPS-01 (`dev_mIoU_phenomena = 0.4057`).
- **Seed 2024 Policy:**
  - Seed 2024 has NEVER been executed and is barred from execution until formally scheduled as a post-freeze replicate.
- **Generalization Standard:**
  - A single seed or pair of seeds is descriptive evidence only.
  - Scientific claims of "statistically robust generalization" require $N \ge 3$ independent training seeds with reported 95% confidence intervals and standard errors.

---

## 10. Summary Verification Contract

Prior to any future training execution, the runtime environment must execute a pre-flight verification verifying:
1. `data/ops02/OPS02_DATASET_FREEZE_SPEC_v1.json` is present and unmodified.
2. SHA-256 hashes of all 212 samples match the manifest.
3. PyTorch version $\ge 2.1$ and CUDA acceleration are available.
4. HOLDOUT files are locked and barred from DataLoader loading.
