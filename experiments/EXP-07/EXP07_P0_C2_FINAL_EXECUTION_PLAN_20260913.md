# EXP-07-P0-C2: Final Execution Plan — Second-Order Scientific Review

**Phase:** EXP-07-P0-C2
**Date:** 2026-09-13
**Status:** CONDITIONAL — CPU-ONLY VALIDATION REQUIRED BEFORE PLAN FREEZE
**Predecessor:** EXP-07-P0-C1 (Red-Team Review)

---

## 1. Executive Summary

This document is the product of a second-order adversarial review of the P0-C1 red-team correction plan. P0-C1 itself identified major scientific defects in the original P0 protocol. This P0-C2 review subjects the P0-C1 corrections to the same rigor and discovers additional defects, most critically:

1. **P0-C1 declared σ⁰ calibration INFEASIBLE.** This is **REJECTED**. All 27 parent-product calibration XMLs are publicly accessible via AWS S3. Targeted recovery requires ~54 MB, no authentication, and is fully automated.

2. **P0-C1 did not analyze calibration nonlinearity.** OPS-01 crops store `mean(DN)` (10×10 block mean of amplitude values). The calibration equation uses `DN²`. Therefore `(mean(DN))² ≠ mean(DN²)`. This introduces a **systematic ~6% bias** in homogeneous regions and **larger content-dependent bias** at feature boundaries. This error was not addressed by P0-C1's LUT-smoothness analysis. Exact calibration requires recovering raw parent pixels.

3. **P0-C1's sampler and class-weight conclusions survive** with minor corrections. The dominant-class inverse-frequency sampler failure is confirmed. Class-presence-aware and parent-balanced samplers remain `REQUIRES_VALIDATION`.

4. **P0-C1's zero/nodata analysis is confirmed.** All 7 zero-containing samples have zeros exclusively at image borders (columns 0-6 or 0-20), labelled BG in source masks. Classification: `STRONGLY_SUPPORTED_INVALID`.

---

## 2. P0-C1 Findings: Surviving vs Corrected vs Rejected

### Surviving (Confirmed by P0-C2)

| Finding | Status |
|---|---|
| SQ-1 reformulation: EXP-07 = phenomenon segmentation, NOT oil-suppression | FROZEN |
| Dominant-class sampler logic failure (6 classes never dominant) | FROZEN |
| `10*log10(DN+eps)` = empirical log transform, NOT physical dB | FROZEN |
| Zero-pixel border padding confirmed (7 samples, exclusively borders) | FROZEN |
| LR=1e-3 "compensates for fewer batches" rationale rejected | FROZEN |
| 3-seed protocol (42, 101, 2024) | FROZEN |
| HOLDOUT_PARTIALLY_USED_FOR_SELECTION disclosure | FROZEN |
| OS=0 as dataset integrity invariant | FROZEN |
| DEV mIoU ≥ 0.30 = exploratory target, NOT confirmatory gate | FROZEN |

### Corrected by P0-C2

| P0-C1 Claim | Correction | Status |
|---|---|---|
| σ⁰ calibration INFEASIBLE from retained artifacts | Calibration XMLs accessible via public S3 for all 27 products | **REQUIRES_VALIDATION** |
| LUT smoothness proves block-mean calibration equivalent | Nonlinearity analysis shows ~6% systematic bias (Jensen's inequality) | **REQUIRES_VALIDATION** |
| Sampler: "class-presence-aware" recommended | Both class-presence-aware AND parent-balanced remain candidates | **REQUIRES_VALIDATION** |
| Loss cap=10: arbitrary but acceptable | No defensible basis for cap value; must analyze sampler×loss interaction | **REQUIRES_VALIDATION** |

### Rejected by P0-C2

| P0-C1 Claim | Reason |
|---|---|
| "Calibration to physical σ⁰ is INFEASIBLE" | All 27 calibration XMLs publicly accessible. Recovery ≈ 54 MB. |
| "LUT varies ~0.01% over 10px, therefore negligible" | Conflates LUT smoothness with calibration equivalence; ignores DN² nonlinearity |

---

## 3. Calibration Analysis: Complete Findings

### 3.1 Calibration Metadata Availability

- **27/27** parent-product calibration XMLs accessible via public AWS S3 (HTTP 200)
- **27/27** noise XMLs accessible
- S3 URL derivable from source recovery inventory
- Calibration XML naming differs between SAFE manifest (full product name) and S3 (simplified); confirmed functional for all products
- Total download: ~54 MB, no authentication required

### 3.2 Calibration Formula

ESA Sentinel-1 GRD calibration for detected products:

```
sigma0(i) = DN(i)² / A_sigma(i)²
```

Where:
- DN(i) = detected amplitude value (uint16 in parent, float32 block-mean in crop)
- A_sigma(i) = sigmaNought calibration vector, bilinearly interpolated at pixel/line coordinates

### 3.3 Calibration Nonlinearity (CRITICAL)

OPS-01 crops store: `x_crop = mean(DN_1, ..., DN_100)` (10×10 block mean)

Applying calibration to block-mean:
```
sigma0_approx = x_crop² / A² = (mean(DN))² / A²
```

Physically correct:
```
sigma0_exact = mean(DN_i² / A_i²) ≈ mean(DN²) / A²
```

By Jensen's inequality:
```
mean(DN²) - (mean(DN))² = Var(DN) ≥ 0
```

Therefore:
```
sigma0_exact / sigma0_approx = 1 + CV²
```

Where CV = within-block coefficient of variation of raw DN.

**Error estimates:**
- Homogeneous regions (speckle only): CV ≈ 0.25 → **~6% systematic underestimate** (~0.25 dB)
- Feature boundaries: CV >> 0.25 → **potentially 25-100% error**
- The bias is systematic and approximately constant → removable in relative comparisons
- The 0.25 dB offset is within Sentinel-1 absolute radiometric accuracy (0.34 dB specification)

### 3.4 Calibration Decision

**Classification: CALIBRATION APPROXIMATELY RECONSTRUCTABLE BUT ERROR NOT FULLY ESTABLISHED**

**Rationale:**
- Approximate calibration (dividing block-mean DN² by LUT²) removes the dominant **17% cross-swath incidence-angle confound**
- The ~6% nonlinearity bias is systematic and smaller than the confound it removes
- Empirical validation of the theoretical CV estimate requires reading raw parent pixels via range requests (feasible: S3 supports byte-range access)
- For segmentation (not absolute radiometry), the approximate calibration is scientifically superior to no calibration

**Status: REQUIRES_VALIDATION** via CPU-only empirical test in P0-C3

### 3.5 Crop-to-Parent Mapping

- source_window field provides exact parent pixel coordinates
- Aggregation: 10×10 spatial block mean
- Calibration LUT interpolation at center of each 10×10 block: sufficient (LUT varies <0.01% over block)
- Parent measurement TIFFs support HTTP range requests (verified: 206 Partial Content)
- GDAL `/vsicurl/` can read arbitrary windows from remote TIFFs

---

## 4. Zero/NoData Analysis

### Findings

| Property | Result |
|---|---|
| Zero-containing TRAIN samples | 4 (all from parent ...041694-04f5f9...) |
| Zero-containing DEV samples | 2 (from parent ...041718-04f6ce...) |
| Zero-containing HOLDOUT samples | 1 (from parent ...042485-051115...) |
| Zero location | Exclusively left-border columns (col 0-6 or 0-20) |
| Interior zeros (10px margin excluded) | 0 in TRAIN, 2596 in DEV (col 0-20) |
| Mask labels at zeros | All BG (0) |
| Negative pixels | 0 anywhere |
| Min nonzero value | 7.99 |

**Classification:** STRONGLY_SUPPORTED_INVALID — zeros are swath-edge padding/NoData

### Validity Mask Design

- Do NOT rewrite source masks
- Future loader creates a validity mask: `valid = (raw_image > 0)`
- Model target: `effective_target = where(valid, source_mask, IGNORE_INDEX)`
- Normalization: compute statistics excluding invalid pixels
- Status: **PROVISIONAL** (evidence is strong but not formally PROVEN from GRD NoData documentation)

---

## 5. Class Distribution & Sampler Analysis

### TRAIN Class Distribution (72 samples, 12 parents)

| Class | Tiles | Pixels | Fraction | Parents | Dominant-tiles |
|---|---|---|---|---|---|
| BG | 56 | 1,957,266 | 41.48% | 12 | 34 |
| IWs | 36 | 916,153 | 19.42% | 8 | 11 |
| POW | 15 | 554,669 | 11.76% | 5 | 9 |
| MCC | 12 | 547,092 | 11.59% | 5 | 9 |
| BS | 7 | 293,888 | 6.23% | 2 | 5 |
| WS | 6 | 223,848 | 4.74% | 2 | 4 |
| OF | 24 | 67,425 | 1.43% | 4 | 0 |
| RF | 8 | 63,801 | 1.35% | 4 | 0 |
| AF | 9 | 35,931 | 0.76% | 4 | 0 |
| Eddy | 3 | 34,110 | 0.72% | 1 | 0 |
| LWA | 2 | 23,424 | 0.50% | 1 | 0 |
| HM | 7 | 985 | 0.02% | 5 | 0 |

**Confirmed:** 6 classes (AF, Eddy, HM, LWA, OF, RF) are NEVER dominant → P0 inverse-dominant-class sampler fails.

### Sampler Comparison (1000-epoch simulation)

Uniform and parent-balanced both provide different exposure profiles. Parent-balanced achieves near-1:1 parent ratio (1.1x) but may overexpose rare-class parents. **Status: REQUIRES_VALIDATION**

### Loss Weights (Median-Frequency, TRAIN)

| Class | Weight (raw) | Cap=10 | Cap=5 |
|---|---|---|---|
| BG | 0.074 | 0.074 | 0.074 |
| IWs | 0.159 | 0.159 | 0.159 |
| POW | 0.263 | 0.263 | 0.263 |
| MCC | 0.266 | 0.266 | 0.266 |
| BS | 0.496 | 0.496 | 0.496 |
| WS | 0.651 | 0.651 | 0.651 |
| OF | 2.160 | 2.160 | 2.160 |
| RF | 2.283 | 2.283 | 2.283 |
| AF | 4.053 | 4.053 | 4.053 |
| Eddy | 4.270 | 4.270 | 4.270 |
| LWA | 6.217 | 6.217 | 5.000 |
| HM | 147.854 | 10.000 | 5.000 |

**HM weight is extreme** (147.9× raw). Cap=10 is arbitrary. Combined sampler×loss interaction must be analyzed before freezing. **Status: REQUIRES_VALIDATION**

---

## 6. Architecture

### Current Repository Models

| Model | Params (est.) | Normalization | Input | Output | Notes |
|---|---|---|---|---|---|
| ResNet34UNet | ~24M | BatchNorm2d | [B,2,H,W] | [B,1,H,W] | Hardcoded 2ch/1class |
| VanillaUNet | ~5.5M | BatchNorm2d | [B,2,H,W] | [B,1,H,W] | Hardcoded 2ch/1class |

Both require modification for EXP-07: `in_channels=1, num_classes=12`.

**BatchNorm concern:** With batch_size=8 and 72 TRAIN samples (~9 batches/epoch), BN statistics are estimated from small batches. GroupNorm or InstanceNorm may be more stable. **Status: REQUIRES_VALIDATION**

**ImageNet pretraining:** NOT categorically invalid for SAR. Low-level features (edges, textures) transfer across domains. However, channel adaptation (3→1) is needed. Primary baseline: train from scratch. Ablation: pretrained encoder. **Status: PROVISIONAL**

---

## 7. Optimizer & LR

- **P0 rationale REJECTED:** "1e-3 compensates for fewer batches" has no theoretical basis
- AdamW with lr=1e-3, wd=1e-2 is a reasonable starting point but NOT validated for this specific dataset
- CosineAnnealing LR schedule: standard practice, no objection
- With only ~9 batches/epoch, total optimizer steps per epoch are very few
- **Status: REQUIRES_VALIDATION** — pilot training (when authorized) should test lr sensitivity

---

## 8. Task Formulation

### Primary: 12-class flat softmax segmentation

- 12 training-eligible classes from OPS-01 taxonomy
- Flat softmax is the simplest formulation
- Pixel-level mutual exclusivity: generally satisfied by source annotations (single label per pixel)
- Scene-level co-occurrence: multiple classes per tile (e.g., BG + IWs + OF)
- Hierarchical formulation: NOT justified for initial baseline; adds complexity without clear benefit

### Separation of Concerns (FROZEN)

- **EXP-07:** OPS-01 phenomenon segmentation. No oil-spill class. No lookalike discrimination.
- **Future experiment:** Fusion/cascaded integration with EXP-06 oil detector for false-positive suppression
- OPS-01 contains 0 OS (oil spill) pixels → cannot learn oil-vs-lookalike from OPS-01 alone

---

## 9. Metrics

### Definitions

| Metric | Definition | Absent-class handling |
|---|---|---|
| Per-class IoU | TP/(TP+FP+FN) | If class absent in GT AND pred: exclude from average |
| Foreground macro mIoU | Mean of per-class IoU for classes 1-12 (excluding BG) | Exclude absent classes |
| All-class macro mIoU | Mean of per-class IoU for all 12 classes | Exclude absent classes |
| Pooled IoU | Sum(TP) / Sum(TP+FP+FN) across all classes | N/A |
| Parent-macro mIoU | Compute mIoU per parent, then average | Per-parent absent-class exclusion |

### Edge Cases

- union=0 (class absent in both GT and prediction): exclude from mean, do NOT count as 0 or 1
- All-ignore samples: skip in metric computation
- Class absent across entire partition: report as N/A, not 0

---

## 10. Acceptance Targets

| Target | Type | Status |
|---|---|---|
| DEV mIoU ≥ 0.30 | EXPLORATORY PERFORMANCE TARGET | No external benchmark basis |
| OS pixel count = 0 | DATASET INTEGRITY INVARIANT | FROZEN |

---

## 11. Seed & Holdout Protocol (FROZEN)

- Seeds: 42, 101, 2024
- Each seed controls: data sampler, augmentation, weight initialization
- DEV model selection: per seed (best epoch by DEV mIoU)
- HOLDOUT evaluation: once per seed, no post-hoc selection
- Aggregation: report mean ± std across seeds
- HOLDOUT status: PARTIALLY_USED_FOR_SELECTION (never claim "pristine")

---

## 12. EXP-06 Comparison (FROZEN)

- EXP-06: frozen binary oil-spill detector on Part-I
- EXP-07: multi-class phenomenon segmentation on OPS-01
- **NOT directly comparable** via any single scalar metric
- Future integration experiment required for oil false-positive analysis

---

## 13. Confounder Register Summary

| Confounder | Risk | Mechanism | Mitigation | Residual |
|---|---|---|---|---|
| Incidence angle gradient | HIGH | Uncalibrated DN varies ~17% across swath | Approximate calibration | ~6% nonlinearity bias |
| Parent concentration | MEDIUM | 12 TRAIN parents, some with 1-2 tiles | Parent-balanced sampler candidate | Low parent diversity |
| Block-mean nonlinearity | MEDIUM | mean(DN)² ≠ mean(DN²) | Document bias; validate empirically | Scene-dependent at boundaries |
| BatchNorm with batch_size=8 | MEDIUM | Unstable statistics with ~9 batches/epoch | Consider GroupNorm | Not validated |
| Geographic concentration | LOW-MEDIUM | Unknown geographic diversity | Inspect coordinates | Cannot fix without new data |
| Rare-class parent diversity | HIGH | Eddy: 1 parent, LWA: 1 parent | None available | Model cannot generalize beyond 1 scene |
| Seed variance | MEDIUM | 72 samples → high run-to-run variance | 3-seed protocol | 3 seeds may be insufficient |
| Calibration representation | MEDIUM | Empirical log vs calibrated σ⁰ | Decision pending validation | Depends on calibration feasibility |

---

## 14. Required CPU-Only Validations (P0-C3)

These must be completed BEFORE implementation authorization:

### V-01: Calibration Error Empirical Validation (CRITICAL)

- Read a small window of raw parent DN values via `/vsicurl/` range request
- Compute exact σ⁰ = DN²/A² for one 10×10 block
- Compare to approximate σ⁰ = (mean DN)²/A²
- Measure actual within-block CV and compare to theoretical 0.25
- Repeat for ≥3 samples across different scene content (homogeneous, feature boundary, rare class)

### V-02: Zero/NoData Formal Verification

- Check GRD product specification for formal NoData definition
- Verify that zero-border pixels correspond to documented NoData behavior
- Confirm validity mask design

### V-03: Sampler Exposure Distribution

- Extended simulation with all candidate samplers
- Measure parent oversampling risk
- Measure rare-class (Eddy, LWA, HM) exposure frequency

### V-04: Sampler×Loss Interaction

- Compute effective class gradient magnitudes under each (sampler, loss-weight) combination
- Identify double-correction risks (e.g., upsampled rare class + high loss weight)

### V-05: Deterministic Dataloader Test

- Verify that identical seed produces identical batch sequence
- Verify IGNORE_INDEX propagation through loss

### V-06: Architecture Parameter Count

- Instantiate candidate architectures with in_channels=1, num_classes=12
- Measure exact parameter counts
- Verify BN behavior at batch_size=8

### V-07: Normalization Statistics (TRAIN-only, valid-pixels-only)

- Compute mean/std of raw DN values excluding zeros
- Compute mean/std of log-transformed values excluding zeros
- Compute mean/std of approximate σ⁰ (if calibration validation passes)

---

## 15. Dependency Order

```
V-01 (calibration error) → Radiometric domain decision → V-07 (normalization)
V-02 (zero/nodata) → Validity mask design → V-05 (loader), V-07
V-03, V-04 (sampler/loss) → Sampler+loss freeze
V-06 (architecture) → Architecture freeze
All validations → Implementation plan freeze → Training authorization
```

---

## 16. Stop Conditions

- **STOP if** calibration error empirical validation shows >20% error in homogeneous regions (contradicts theoretical estimate, requires investigation)
- **STOP if** raw parent pixel retrieval fails (S3 access revoked, range requests unsupported by GDAL)
- **STOP if** zero-pixel investigation reveals non-border zeros or negative values
- **STOP if** deterministic loader test fails
- **STOP if** any frozen hash changes

---

## 17. Training Boundary

**TRAINING REMAINS EXPLICITLY UNAUTHORIZED.**

Authorization requires:
1. All V-01 through V-07 validations completed
2. Radiometric domain decision frozen
3. Sampler + loss combination frozen
4. Architecture frozen (with normalization layer decision)
5. Explicit user authorization

---

## 18. Final Decision

**B. CONDITIONAL — CPU-ONLY VALIDATION REQUIRED BEFORE PLAN FREEZE**

The most critical validation is **V-01 (Calibration Error Empirical Validation)**, which determines whether approximate σ⁰ from block-mean DN is defensible or whether raw parent pixel recovery is required.

### Next Phase: EXP-07-P0-C3 — CPU-Only Pre-Training Validation
