# EXP-07-P0-C4: Final Protocol Freeze & Implementation Contract

**Phase:** EXP-07-P0-C4  
**Date:** 2026-09-13  
**Status:** FROZEN — FINAL IMPLEMENTATION CONTRACT AUTHORIZED  
**Final Decision:** A. FINAL — EXP-07 PROTOCOL FROZEN; IMPLEMENTATION AUTHORIZED  
**Authorized Next Phase:** EXP-07-P0-C5 (Implementation Only / CPU Contract + Training Dry-Run Preparation)  
**Machine-Readable Companion:** `data/metadata/exp07_p0_c4_protocol_freeze_v1.json`  

---

## 1. Executive Summary & Scope

This document is the **authoritative, legally binding implementation contract** for **EXP-07** (Sentinel-1 OPS-01 Multiclass Phenomenon Segmentation Baseline). It converts the empirical findings of the **EXP-07-P0-C3** CPU-only validations into an unambiguous, machine-checkable specification.

### Absolute Boundaries
- **No Training:** Model training is strictly prohibited in this phase.
- **No GPU Execution:** All contracts and harnesses remain CPU-only.
- **No Model Checkpoints:** Creation of weight checkpoints is prohibited.
- **No Part-III Access:** Benchmark isolation remains absolute.
- **No Data Mutation:** Image and mask bytes on disk remain completely untouched.

A future implementation agent **MUST NOT** reinterpret, relax, or alter any scientific or operational decisions frozen in this contract.

---

## 2. Immutable Experiment Identity

| Parameter | Frozen Contract Value |
|---|---|
| **Experiment ID** | `EXP-07` |
| **Experiment Name** | Sentinel-1 OPS-01 Multiclass Phenomenon Segmentation Baseline |
| **Dataset Manifest** | `data/metadata/ops01_physical_dataset_manifest_v4.json` |
| **Dataset Manifest SHA256** | `FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E` |
| **Taxonomy ID** | `OPS-01-TAXONOMY-V1` (Version `1.0.0`) |
| **Partition Structure** | TRAIN: 72 tiles / 12 parents; DEV: 39 tiles / 7 parents; HOLDOUT: 36 tiles / 8 parents (Total: 147 / 27) |
| **Radiometric Pathway** | `EMPIRICALLY_CHARACTERIZED_APPROXIMATE_CALIBRATION_PATHWAY` |
| **Validity Policy** | `VALIDITY_MASK_RAW_GT_0_IGNORE_INDEX_M100` |
| **Normalization Policy** | `STANDARDIZED_LOG1P_TRAIN_ONLY_MEAN_4.2756_STD_0.3866` |
| **Training Sampler** | `CANDIDATE_F_HYBRID_70_PARENT_BALANCED_30_CLASS_PRESENCE` |
| **Loss Function** | `SQUARE_ROOT_MEDIAN_FREQUENCY_WEIGHTED_CROSS_ENTROPY` |
| **Model Architecture** | `RESNET18_UNET_IN1_OUT12` (Option B: BatchNorm Baseline with Stability Contract) |
| **Augmentation Policy** | `BASELINE_IDENTITY_NO_AUGMENTATION` |
| **Random Seed Protocol** | Three Seeds: `[42, 101, 2024]` |
| **Evaluation Protocol** | `ARGMAX_MULTICLASS_MIOU_MACRO_VALID_PIXELS_ONLY` |
| **Software Environment** | Python 3.10 / PyTorch CPU Reference |
| **Git Branch** | `master` |

---

## 3. Radiometric Domain & Preprocessing Contract

### Epistemic Truth Statement
> **Physical Sentinel-1 radiometric calibration is NOT identical to the OPS-01 aggregated preprocessing approximation.**

OPS-01 crops store a 10×10 spatial block-mean of detected amplitude ($DN$), not raw single-look parent pixels. By Jensen's inequality:
$$\text{calibrate}(\text{mean}(DN)) \ne \text{mean}(\text{calibrate}(DN))$$

### Empirical Approximation Error (Frozen from C3 Measurement of 777,611 Blocks)
- **Central/Typical Error Regime:** Median relative error = **5.52%** (0.233 dB), Mean relative error = **5.81%** (0.244 dB).
- **LUT Spatial Variation ($E_1$):** Maximum observed **0.0335%** (typical $< 0.005\%$), confirming that LUT spatial smoothness is negligible.
- **Nonlinear Aggregation Discrepancy ($E_2$):** Accounts for **$> 99.4\%$** of the approximation error.
- **Extreme High-Reflectivity / Point Targets:** Error is **NOT globally bounded at 20–30%**. Strong metallic scatterers (e.g. Artificial Objects HM) and sharp high-contrast phenomenon boundaries produce localized errors up to **333.12%**.

### Prohibitions
1. **DO NOT** write or claim that "calibration is exact."
2. **DO NOT** write or claim that "error is globally bounded at 20–30%."
3. **DO NOT** claim that the approximation is justified by Sentinel-1 instrument radiometric accuracy (0.34 dB). Instrument accuracy and processing approximation errors are separate, orthogonal error budgets.

### Three-Tier Quantity Separation
The future implementation loader must maintain explicit variable naming:
1. **`raw_source_dn`:** The physical uint16/float32 crop array stored on disk (`derived_image_path`).
2. **`log1p_dn`:** The intermediate nonlinearly compressed representation: $z = \log(1 + \text{raw\_source\_dn})$.
3. **`model_input_tensor`:** The standardized float32 tensor: $\hat{x} = \frac{z - 4.2756}{0.3866}$.

---

## 4. Zero / Validity Masking Policy

### Formal Status: STRONGLY_SUPPORTED_INVALID
All 18,798 zero pixels across the dataset occur strictly as continuous left-border columns (columns 0–6 or 0–20) adjacent to the slant-to-ground range projection margin. There are **zero interior zeros**. In GeoTIFF metadata, the official tag `nodata: 0.0` is present per ESA S1-RS-MDA-52-7443 Section 4.2.1.

### Policy Rules
1. **Runtime Validity Mask:**
   $$\text{validity\_mask} = (\text{raw\_source\_dn} > 0)$$
2. **Loss Evaluation:**
   Zero-padding pixels are assigned `ignore_index = -100` during loss computation and are excluded from all gradient updates.
3. **Model Input at Padding:**
   At invalid locations (`~validity_mask`), the standardized input tensor is filled with `0.0` (neutral standardized mean).
4. **Source Mask Protection:**
   The ground-truth mask PNG files on disk **MUST NEVER BE MODIFIED**. Validity masking is strictly a decoupled runtime tensor operation.

---

## 5. Dataset Interface & Partition Structure

### Physical Partitions
- **TRAIN:** 72 tiles across 12 independent parent scenes.
- **DEV:** 39 tiles across 7 independent parent scenes.
- **HOLDOUT:** 36 tiles across 8 independent parent scenes.
- **TOTAL:** 147 physical tiles across 27 independent parent scenes.

### Tensor Input/Output Contract
- **Input Shape:** `[B, 1, 256, 256]` float32 tensor.
- **Output Shape:** `[B, 12, 256, 256]` float32 logits.
- **Head Activation:** **NONE**. Raw unnormalized logits must be output by the network. No sigmoid or softmax activation in the model forward pass.

---

## 6. Canonical 12-Class Taxonomy & Dense Mapping

The 12 training-eligible classes are mapped to immutable dense indices `0..11`:

| Dense Index | Abbr | Canonical Name | Source Label ID | Role | Training Eligibility |
|---|---|---|---|---|---|
| **0** | `BG` | Background Seawater | 0 | Core Background | ELIGIBLE |
| **1** | `AF` | Atmospheric Front | 1 | Auxiliary Meteorological | ELIGIBLE |
| **2** | `BS` | Biological Slicks | 2 | Core Lookalike | ELIGIBLE |
| **3** | `LWA` | Low Wind Area | 4 | Core Lookalike | ELIGIBLE |
| **4** | `MCC` | Mesoscale Cellular Convection | 5 | Auxiliary Meteorological | ELIGIBLE |
| **5** | `OF` | Ocean Front | 6 | Core Hydrodynamic | ELIGIBLE |
| **6** | `POW` | Pure Ocean Wave | 7 | Auxiliary Wave Field | ELIGIBLE |
| **7** | `RF` | Rain Cell / Rain Footprint | 8 | Core Meteorological | ELIGIBLE |
| **8** | `WS` | Wind Streak | 10 | Auxiliary Atmospheric | ELIGIBLE |
| **9** | `Eddy` | Oceanic Eddy | 11 | Core Hydrodynamic | ELIGIBLE |
| **10** | `IWs` | Internal Waves | 12 | Core Lookalike | ELIGIBLE |
| **11** | `HM` | Artificial / Anthropogenic Objects | 13 | Anthropogenic Objects | ELIGIBLE |

### Invariant Rules
- **HM Invariant:** Class 11 (source 13) **MUST** remain named *Artificial / Anthropogenic Objects*. Renaming to *Vessel* is strictly prohibited.
- **OS Exclusion:** Class 14 (Mineral Oil Spill) has only 4 images (1,702 pixels, 0.0005% of dataset) and is **strictly excluded** from training.
- **Cryospheric Exclusions:** Class 3 (`IB`, Iceberg) and Class 9 (`SI`, Sea Ice) are domain-restricted and excluded.
- **Immutable Ordering:** The dense index ordering `0..11` is frozen and must not be re-ordered.

---

## 7. Deterministic Hybrid Training Sampler Specification

### Algorithm: Candidate F (70% Parent-Balanced + 30% Class-Presence)

Let $N = 72$ be the number of training tiles, and $K = 12$ be the number of independent parent scenes.

1. **Parent-Balanced Component ($p_{\text{parent}}$):**
   For each parent scene $P_k$ containing $M_k$ tiles, every tile $i \in P_k$ receives:
   $$p_{\text{parent}}(i) = \frac{1}{K \cdot M_k} = \frac{1}{12 \cdot M_k}$$
   This ensures that each parent scene has an aggregate selection probability of $\frac{1}{12}$, regardless of whether it contributed 1 tile or 12 tiles.

2. **Class-Presence Component ($p_{\text{presence}}$):**
   For each tile $i$, let $C_i \subseteq \{0..11\}$ be the set of eligible classes present in tile $i$ with $\text{pixel\_count} > 0$. Let $T_c$ be the total count of training tiles containing class $c$. The presence score is:
   $$s(i) = \sum_{c \in C_i} \frac{1}{T_c}$$
   Normalized across all training tiles:
   $$p_{\text{presence}}(i) = \frac{s(i)}{\sum_{j=1}^{72} s(j)}$$

3. **Hybrid Probability Vector ($p_{\text{hybrid}}$):**
   $$p_{\text{hybrid}}(i) = 0.70 \cdot p_{\text{parent}}(i) + 0.30 \cdot p_{\text{presence}}(i)$$
   $\sum_{i=1}^{72} p_{\text{hybrid}}(i) = 1.0$.

4. **Sampling Semantics:**
   - **Epoch Size:** Exactly 72 samples drawn per epoch.
   - **Replacement:** Drawn **with replacement** according to $p_{\text{hybrid}}$.
   - **Deterministic Seed Replay:** The sampler RNG is initialized with seed $S \in \{42, 101, 2024\}$ and advanced deterministically per epoch: $\text{seed}_{\text{epoch}} = S + \text{epoch}$.
   - **Performance Guarantees:**
     - Maximum parent multiplier $\le 1.370\times$ (prevents parent memorization).
     - Parent exposure $CV \approx 0.22$.
     - Expected rare-class exposure per epoch: $\text{HM} \approx 6.85$ tiles, $\text{LWA} \approx 3.10$ tiles, $\text{Eddy} \approx 4.96$ tiles.

---

## 8. Square-Root Median-Frequency Loss Contract

### Mathematical Formulation
Standard multi-class Cross-Entropy Loss with static class weights and spatial validity masking:
$$\mathcal{L} = -\frac{1}{\sum_{h, w} \mathbf{1}(y_{h,w} \ne -100)} \sum_{h, w} \mathbf{1}(y_{h,w} \ne -100) \cdot w_{y_{h,w}} \cdot \log\left(\frac{\exp(z_{y_{h,w}, h, w})}{\sum_{c=0}^{11} \exp(z_{c, h, w})}\right)$$

### Class Weight Formula
$$w_c = \sqrt{\frac{\text{median}(f_0, f_1, \dots, f_{11})}{f_c}}$$
where $f_c = \frac{\text{valid\_pixels}_c}{\sum_{k=0}^{11} \text{valid\_pixels}_k}$ over the 4,712,082 valid TRAIN pixels.

### Exact Machine-Readable Weight Table
$$\text{median}(f) = 0.03086432$$

| Dense Index | Abbreviation | Frequency ($f_c$) | Exact Loss Weight ($w_c$) |
|---|---|---|---|
| **0** | `BG` | 0.415372 | **0.272584** |
| **1** | `AF` | 0.007625 | **2.011884** |
| **2** | `BS` | 0.062369 | **0.703478** |
| **3** | `LWA` | 0.004971 | **2.491745** |
| **4** | `MCC` | 0.116104 | **0.515568** |
| **5** | `OF` | 0.014309 | **1.468694** |
| **6** | `POW` | 0.117712 | **0.512036** |
| **7** | `RF` | 0.013540 | **1.509836** |
| **8** | `WS` | 0.047505 | **0.806037** |
| **9** | `Eddy` | 0.007239 | **2.064883** |
| **10** | `IWs` | 0.194426 | **0.398424** |
| **11** | `HM` | 0.000209 | **12.151197** |

- **Weight Range:** Max ($w_{\text{HM}} = 12.15$) to Min ($w_{\text{BG}} = 0.27$) ratio is **44.58**.
- **Double-Correction Control:** When combined with the Hybrid Sampler, effective rare-class gradient emphasis on HM is $\approx 43.5\times$ relative to Background (**LOW** risk of gradient instability).

---

## 9. Model Architecture & Normalization Specifications

### Architecture: ResNet18-UNet
- **Encoder:** ResNet-18 backbone initialized with pre-trained torchvision weights (adapted at `conv1` from 3 channels to 1 channel via sum/average slice weighting).
- **Decoder:** 4-stage upsampling with transposed convolutions and skip-connections.
- **Input Channels:** 1 (`in_channels=1`).
- **Output Classes:** 12 (`num_classes=12`).
- **Trainable Parameters:** **14,310,860** (54.64 MB).
- **Total Parameters:** **14,322,636**.

### Normalization Contract: OPTION B (BatchNorm Baseline with Stability Guardrail)
- **Decision:** Keep `BatchNorm2d` (30 layers in ResNet18-UNet) as the baseline architecture to preserve exact pre-trained ImageNet filter weights.
- **Small-Sample Stability Guardrail:** With 72 training tiles and `batch_size = 8`, an epoch contains only 9 batches. Default BatchNorm running statistics ($\text{momentum}=0.1$) risk volatile covariate shifts. The implementation **MUST**:
  1. Set BatchNorm running momentum to `0.05` (slower, smoother running statistic updates).
  2. Implement gradient accumulation with `steps=2` (achieving an effective virtual batch size of 16).

---

## 10. TRAIN-Only Standardization Pipeline

### Normalization Constants (FROZEN)
Computed strictly over **4,712,082 valid TRAIN pixels** (6,510 zero-padding pixels excluded; 0 DEV or HOLDOUT pixels):
$$\mu_{\text{train}} = 4.2756, \quad \sigma_{\text{train}} = 0.3866$$

### Mathematical Formula
$$\hat{x} = \frac{\log(1 + x) - 4.2756}{0.3866}$$

### Invariant Execution Order
The preprocessing pipeline **MUST** execute in this exact sequence:
1. Load raw crop array $x \in \mathbb{R}^{256 \times 256}$ float32.
2. Compute binary validity mask: $v = (x > 0)$.
3. Compute logarithmic compression: $z = \log(1 + x)$.
4. Apply standardization: $\hat{x} = \frac{z - 4.2756}{0.3866}$.
5. Mask invalid padding: $\hat{x}[\sim v] = 0.0$.
6. Reshape to tensor: `[1, 256, 256]`.

---

## 11. SAR-Specific Data Augmentation Policy

Generic computer-vision augmentations violate SAR physical geometry. All transforms are formally classified:

| Transform | Classification | Scientific Rationale |
|---|---|---|
| **Identity (No Augmentation)** | **BASELINE_FROZEN** | Eliminates confounding factors for baseline evaluation. |
| **Vertical Flip (Azimuth Reversal)** | **SAFE** | Satellite along-track flight direction preserves radar cross section and Doppler symmetry. |
| **Horizontal Flip (Range Reversal)** | **CONDITIONAL** | Inverts near-to-far incidence angle gradient; unvalidated for asymmetric phenomena. |
| **90° Rotations** | **DISALLOWED** | Swaps range and azimuth axes, violating SAR resolution and speckle correlation physics. |
| **Brightness / Contrast Jitter** | **DISALLOWED** | Artificially distorts physical radar backscatter, violating radiometric calibration integrity. |
| **Elastic Deformations / Blurring** | **DISALLOWED** | Distorts physical speckle texture and sharp point-target corners (critical for HM). |

**Frozen Implementation Rule:** EXP-07 baseline training **MUST** use `BASELINE_IDENTITY_NO_AUGMENTATION`.

---

## 12. Multiclass Evaluation Contract

### Prediction Rule
$$\hat{y}_{h, w} = \operatorname{argmax}_{c \in \{0..11\}} \text{logits}_{c, h, w}$$

### Strict Prohibitions
- **NO binary thresholding.**
- **PROHIBITED:** Reusing EXP-06 threshold $\tau = 0.22$. Any implementation referencing $\tau = 0.22$ will fail automated guardrails.

### Evaluation Metrics (Evaluated on `validity_mask == True` only)
1. **Per-Class IoU:**
   $$\text{IoU}_c = \frac{\text{TP}_c}{\text{TP}_c + \text{FP}_c + \text{FN}_c}$$
2. **Macro mIoU (Primary Metric):**
   $$\text{mIoU}_{\text{phenomena}} = \frac{1}{|C_{\text{phenomena}}|} \sum_{c=1}^{11} \text{IoU}_c$$
   Evaluated strictly over the 11 foreground phenomenon classes (excluding Background).
3. **Overall Macro mIoU:**
   $$\text{mIoU}_{\text{all}} = \frac{1}{12} \sum_{c=0}^{11} \text{IoU}_c$$
   Evaluated over all 12 classes (including Background).
4. **Absent-Class Handling:** If class $c$ has 0 true pixels in a partition, it is omitted from the macro-average denominator for that partition.

---

## 13. Holdout Epistemic Status

### Permanent Disclosure: `HOLDOUT_PARTIALLY_USED_FOR_SELECTION`
- The HOLDOUT partition (36 tiles / 8 parents) is **NOT PRISTINE**.
- It was partially inspected and used for selection during historical project phases (Phase 7 / Phase 8).
- **Prohibited Terms:** The holdout must **NEVER** be described as *pristine*, *untouched*, *unbiased*, or an *independent external benchmark*.
- All reports presenting holdout results must feature this disclosure.

---

## 14. Implementation Checklist for Phase C5

The Phase C5 implementation agent must satisfy the following checklist without deviation:
- [ ] Implement `OPS01Dataset` inheriting the exact 6-step normalization pipeline.
- [ ] Implement `OPS01HybridSampler` matching the exact 70/30 probability formula.
- [ ] Implement `SquareRootMedianFrequencyCrossEntropyLoss` with the exact 12-class weight vector.
- [ ] Instantiate `ResNet18UNet` with `in_channels=1`, `num_classes=12`, and `momentum=0.05`.
- [ ] Implement training loop with gradient accumulation (`steps=2`, effective batch size 16).
- [ ] Implement multiclass `argmax` evaluation harness computing `mIoU_phenomena` and `mIoU_all`.
- [ ] Verify 100% deterministic dry-run forward/backward pass on CPU before any training authorization.

---

## 15. Final Authorization Gate

### Final Decision: **A. FINAL — EXP-07 PROTOCOL FROZEN; IMPLEMENTATION AUTHORIZED**

The protocol specification is complete, machine-readable, and mathematically closed.

### Next Authorized Boundary:
**EXP-07-P0-C5 — IMPLEMENTATION ONLY / CPU CONTRACT + TRAINING DRY-RUN PREPARATION**

*Training remains strictly prohibited until authorized by a separate explicit decision gate following successful C5 implementation validation.*
