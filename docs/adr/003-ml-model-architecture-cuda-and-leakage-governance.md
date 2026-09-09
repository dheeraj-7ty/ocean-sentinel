# ADR 003: ML Model Architecture, 2-Channel ResNet-34 Adaptation, CUDA Environment Remediation & Spatial Leakage Governance

**Status**: APPROVED WITH CONDITIONS  
**Date**: September 2026  
**Author**: Implementation Engineer (under CAO Architectural Authority)  
**Phase**: 2.3  

---

## 1. Context & Problem Statement

Phase 2.2 defined the target architecture for Ocean Sentinel oil-spill segmentation: a primary U-Net with a pretrained ResNet-34 encoder taking 2-channel SAR input (`[B, 2, 512, 512]`) and returning single-channel unscaled logits (`[B, 1, 512, 512]`), trained using a composite loss ($0.5 \cdot \text{BCEWithLogits} + 0.5 \cdot \text{SoftDiceLoss}$).

Before commencing training experiments (EXP-01+), Phase 2.3 was mandated to address four critical architectural conditions:
1. **Scene-Level & Spatial Leakage Governance**: The Phase 2.1 split prevented parent-stem leakage, but spatial independence across the 1,200 Trujillo parent patches was unproven.
2. **CUDA / Hardware Environment Remediation**: The project previously ran on CPU-only PyTorch despite the presence of an NVIDIA RTX 3050 Laptop GPU (6 GB VRAM).
3. **ResNet-34 Two-Channel Input Adaptation**: Pretrained ImageNet weights are 3-channel. The mathematical rationale for 2-channel adaptation required explicit justification rather than ad-hoc weight slicing.
4. **EXP-00 Hardware Microbenchmark**: Measure real forward/backward latency, VRAM consumption across batch sizes, AMP FP16 feasibility, gradient accumulation, and real DataLoader throughput before attempting long runs.

---

## 2. Decision & Implementation

### 2.1 Model Architecture & Input/Output Contracts
- **Primary Model (`ResNet34UNet`)**:
  - Encoder: ResNet-34 backbone with standard skip connections at resolutions $H/2, H/4, H/8, H/16, H/32$.
  - Decoder: 4-stage upsampling via bilinear interpolation + DoubleConv ($3\times3$ Conv2D, BatchNorm2D, ReLU), with skip connection concatenation.
  - Final head: $1\times1$ Conv2D returning raw logits of shape `[B, 1, H, W]`. Sigmoid is never applied internally.
  - Total parameters: **24,346,305** (all trainable).
- **Secondary Baseline (`VanillaUNet`)**:
  - 4-stage encoder-decoder U-Net with 32 base channels (channels: 32, 64, 128, 256, 512).
  - Total parameters: **7,762,753** (retained for future EXP-04 ablation).

### 2.2 ResNet-34 Two-Channel Input Adaptation
ImageNet pretrained weights for ResNet-34 `conv1` have shape `[64, 3, 7, 7]`. Four adaptation hypotheses were evaluated:
1. **`slice_variance_scaled` (Selected Baseline)**:
   $$W' = W_{[:, 0:2, :, :]} \cdot \sqrt{\frac{3}{2}} \approx W_{[:, 0:2, :, :]} \cdot 1.2247$$
   *Mathematical Rationale*: For zero-mean unit-variance normalized inputs ($x_c \sim \mathcal{N}(0, 1)$), the activation variance of a sum of $C$ independent channels is $\text{Var}(\sum_{c=1}^C W_c x_c) = \sum_{c=1}^C W_c^2$. When reducing channels from 3 to 2, scaling weights by $\sqrt{3/2}$ exactly preserves the expected variance of the initial layer activations $\mathbb{E}[\text{Var}(y)]$. The earlier proposal of $3/2 = 1.5$ represented an L1-weight sum scaling which results in an excessive $1.5\times$ variance inflation.
2. **`average_distributed`**:
   $$W'_{[:, 0]} = W_{[:, 0]} + 0.5 \cdot W_{[:, 2]}, \quad W'_{[:, 1]} = W_{[:, 1]} + 0.5 \cdot W_{[:, 2]}$$
   Distributes the omitted third channel equally across the first two.
3. **`slice`**: Direct unscaled truncation $W' = W_{[:, 0:2, :, :]}$.
4. **`rgb_luminance`**: ITU-R BT.601 linear combination.

All four methods are implemented and selectable via the `adaptation_method` argument. `slice_variance_scaled` is set as the authoritative default.

### 2.3 Loss Functions & Metrics
- **Primary Loss (`CombinedBCEAndDiceLoss`)**:
  $$\mathcal{L} = 0.5 \cdot \text{BCEWithLogitsLoss}(z, y) + 0.5 \cdot \text{SoftDiceLoss}(z, y)$$
  with Laplace pixel smoothing (`smooth=1.0`) ensuring numerical stability on sparse masks.
- **Secondary Loss (`FocalTverskyLoss`)**:
  $\alpha=0.3, \beta=0.7, \gamma=4/3$ implemented for EXP-02 ablation.
- **Metrics**:
  - Global IoU, Dice, Precision, Recall computed over accumulated streaming counts via `SegmentationMeter`.
  - Empty-mask convention: When ground truth is empty ($y=0$), a prediction of empty ($p=0$) yields $\text{IoU}=1.0, \text{Dice}=1.0, \text{Recall}=1.0, \text{Precision}=1.0$; predicting foreground pixels yields $\text{IoU}=0.0, \text{Dice}=0.0, \text{Precision}=0.0, \text{Recall}=1.0$.
- **Threshold Selection**:
  `optimize_threshold_on_validation()` searches a 41-point grid ($0.10 \dots 0.90$, step $0.02$) on validation data only. Test data is strictly prohibited from threshold optimization.

### 2.4 Baseline SAR Augmentation
Implemented in `SARGeometricAugmentation`:
- Discrete horizontal flip ($p=0.5$).
- Discrete vertical flip ($p=0.5$).
- Discrete 90° rotation ($k \in \{0, 1, 2, 3\}$).
- Zero spatial interpolation (pure array indexing).
- Strict rejection of optical color jitter, blur, or arbitrary continuous affine warping.
- Deterministic seeding available for testing.

### 2.5 CUDA Environment Remediation
- Installed official stable PyTorch wheels:
  - `torch==2.14.0+cu126`
  - `torchvision==0.29.0+cu126`
- Hardware verified:
  - GPU: NVIDIA GeForce RTX 3050 6GB Laptop GPU
  - Compute Capability: 8.6 (Ampere)
  - CUDA Runtime: 12.6
  - cuDNN: 9.1.0 (version 91002)
  - VRAM: 6,143.5 MB

---

## 3. Empirical Hardware Microbenchmark (EXP-00 Results)

Conducted on `NVIDIA GeForce RTX 3050 6GB Laptop GPU` (Driver 616.64, Windows 11):

| Configuration | Batch Size | Forward (ms) | Backward (ms) | Peak Alloc VRAM | Peak Rsrv VRAM | Headroom | Throughput |
|---|---|---|---|---|---|---|---|
| **CPU Baseline** | 1 | 198.7 ms | 349.7 ms | N/A | N/A | N/A | 1.82 smp/s |
| **CUDA FP32** | 1 | 20.5 ms | 39.9 ms | 657.7 MB | 768.0 MB | 5,375.5 MB | 16.5 smp/s |
| **CUDA FP32** | 2 | 39.2 ms | 74.9 ms | 1,030.5 MB | 1,216.0 MB | 4,927.5 MB | 17.5 smp/s |
| **CUDA FP32** | 4 | 74.3 ms | 139.0 ms | 1,776.6 MB | 2,098.0 MB | 4,045.5 MB | 18.7 smp/s |
| **CUDA FP32** | 8 | 137.8 ms | 268.3 ms | 3,258.8 MB | 3,886.0 MB | 2,257.5 MB | 19.7 smp/s |
| **CUDA AMP FP16** | 1 | 12.7 ms | 24.9 ms | 523.8 MB | 568.0 MB | 5,575.5 MB | 26.6 smp/s |
| **CUDA AMP FP16** | 2 | 22.0 ms | 43.6 ms | 718.0 MB | 806.0 MB | 5,337.5 MB | 30.5 smp/s |
| **CUDA AMP FP16** | 4 | 40.1 ms | 77.9 ms | 1,105.0 MB | 1,280.0 MB | 4,863.5 MB | 33.9 smp/s |
| **CUDA AMP FP16** | 8 | 77.4 ms | 149.4 ms | 1,889.2 MB | 2,210.0 MB | 3,933.5 MB | 35.3 smp/s |

- **Gradient Accumulation (Physical B=4, Accum=2 $\to$ Eff B=8, AMP FP16)**:
  Step latency 258.5 ms, throughput 30.94 samples/s, peak VRAM 1,098.0 MB, finite gradients verified.
- **AMP Stability**:
  Dynamic loss scale remained stable at 65,536.0 with finite loss and gradients across all steps.
- **Real DataLoader Throughput (100 batches, B=4, `num_workers=0`)**:
  First batch latency: 119.7 ms. Steady-state mean batch latency: 156.3 ms (25.59 samples/s).
- **Real Training Loop (25 batches, B=4, AMP FP16)**:
  Steady-state step: 134.0 ms (29.86 samples/s). Peak VRAM: 1,156.0 MB (4,987.5 MB headroom).
  Estimated 1-epoch training time (13,440 tiles): **7.5 minutes**.

---

## 4. Spatial & Scene-Level Leakage Audit Findings

An exhaustive geospatial audit of all 1,200 Trujillo Part I parent GeoTIFFs revealed:
1. **Absence of Scene Identifiers & Timestamps**:
   TIFF headers contain only `AREA_OR_POINT`, `TIFFTAG_RESOLUTIONUNIT`, `TIFFTAG_XRESOLUTION`, `TIFFTAG_YRESOLUTION`. No Sentinel-1 product IDs, orbit numbers, or timestamps exist.
2. **Duplicate Geotransforms Across Split**:
   Two exact geotransform pairs cross splits:
   - Patches `00007` (test) and `01339` (train): Identical transform `[-88.35, 0.0001, 0.0, 28.53, 0.0, -0.0001]`.
   - Patches `00356` (val) and `00357` (test): Identical transform.
3. **Severe Spatial Overlap**:
   - Out of 9,319 total overlapping pairs, **4,496 pairs cross split boundaries** (train-val: 2,371; train-test: 1,695; val-test: 430).
   - **3,548 cross-split pairs share $\ge 10\%$ spatial area**.
   - **1,234 cross-split pairs share $\ge 50\%$ spatial area**.
4. **Centroid Proximity**:
   Median distance from val patch to nearest train patch is **7.56 km**; 66/180 val patches are $<5$ km from train. Median distance from test to train is **8.12 km**; 63/180 test patches are $<5$ km from train.

### Architectural Governance Decision on Leakage:
- The current split manifest is preserved for EXP-00 (environment, hardware, and integration verification).
- However, for scientific model evaluation (EXP-01+), the current split contains substantial spatial correlation. A spatial cluster-based split (or tile-disjoint spatial bounding box split) is strongly recommended before drawing benchmark conclusions.

---

## 5. Consequences

- **Positive**:
  - Full CUDA acceleration unlocked on RTX 3050 (over $16\times$ speedup vs CPU).
  - Memory-safe baseline batch configuration identified: physical batch 4 + gradient accumulation 2 + AMP FP16 consumes only 1.2 GB VRAM, leaving 4.8 GB safety margin.
  - Complete ML test suite passes (395/395 tests).
- **Caveats**:
  - Training metrics on the current split must be interpreted as spatially-correlated validation until a spatial-clustering split remediation is approved by CAO.
