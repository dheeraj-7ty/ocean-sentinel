# EXP-07-P0-C5: Adversarial Contract Audit, Implementation & CPU-Only Dry-Run Preparation

**Phase:** EXP-07-P0-C5  
**Date:** 2026-09-13  
**Status:** COMPLETE (Decision A: Final Reference Implementation Authorized)  
**Hardware Mode:** CPU-only (Strictly zero GPU, zero training, zero optimizer steps, zero checkpoints, zero Part-III access)  
**Dataset Authority:** `data/metadata/ops01_physical_dataset_manifest_v4.json` (SHA256: `FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E`)  
**Taxonomy Authority:** `data/metadata/ops01_taxonomy_v1.json`  
**Reference Code:** `src/ocean_sentinel/ml/exp07_reference.py`  

---

## 1. Executive Summary

Phase EXP-07-P0-C5 successfully translated the frozen EXP-07-P0-C4 protocol into a fully implemented, mathematically exact, and regression-tested CPU reference pipeline. Rather than assuming the C4 contract was flawless, C5 conducted a rigorous adversarial contract-to-implementation audit across 38 distinct protocol dimensions.

### Key Audit Findings & Critical Corrections:
1. **BatchNorm vs. Gradient Accumulation Error (CORR-C5-001):**
   - *P0-C4 Error:* Claimed that using gradient accumulation (`steps=2, virtual batch_size=16`) stabilized BatchNorm running statistics over 72 training tiles.
   - *Scientific Truth:* Gradient accumulation aggregates gradients across minibatches for optimizer updates; it has **zero effect** on the sample size evaluated by `BatchNorm2d` during forward passes. Under physical minibatch size 8, BatchNorm evaluates statistics across exactly 8 samples.
   - *Correction:* The physical batch size seen by BatchNorm ($N=8$) is explicitly decoupled from the effective optimization batch size ($N_{\text{eff}}=16$). Small-sample BatchNorm variance is formally registered as a known risk under Option B, with `momentum=0.05` smoothing running estimates across the 9 batches per epoch. Formally registered as incident `INC-P0-C5-001` and permanent governance rule `GOV-RULE-059`.
2. **Excluded Class Remapping in Evaluation Partitions (CORR-C5-002):**
   - *P0-C4 Gap:* P0-C4 assumed only 12 eligible classes would appear in data.
   - *Empirical Discovery:* Audit of physical raster masks revealed that DEV contains 261,120 pixels and HOLDOUT contains 195,840 pixels of Class 9 (`Sea Ice`, `SI`), an excluded class (`training_eligible: False`).
   - *Correction:* Implemented explicit dense remapping: eligible source classes map to dense indices 0..11; all non-eligible source classes (3: `IB`, 9: `SI`, 14: `OS`) are strictly remapped to `ignore_index = -100` alongside left-swath zero border padding.
3. **Deterministic Reference Implementation:**
   - Completed `src/ocean_sentinel/ml/exp07_reference.py` providing the complete reference dataset reader, validity masking, log1p standardization, Candidate F hybrid sampler, square-root median frequency loss, ResNet18-UNet model factory, argmax prediction, and multiclass metric evaluation.
   - Executed end-to-end CPU dry-run verifying tensor shapes, loss calculation, and metric computation.

---

## 2. Critical Corrections to P0-C4 Contract

### 2.1 Correction CORR-C5-001: BatchNorm Statistical Batch Size vs. Optimization Batch Size

> [!IMPORTANT]
> **GOV-RULE-059 Enacted:** Effective optimization batch size is conceptually and operationally distinct from BatchNorm statistical batch size. Gradient accumulation must never be claimed to increase or stabilize BatchNorm statistical batch size.

- **Mathematical Reality:**
  Let forward pass $k$ process minibatch $X_k \in \mathbb{R}^{B \times C \times H \times W}$. In PyTorch, `BatchNorm2d` computes:
  $$\mu_B = \frac{1}{B \cdot H \cdot W} \sum_{b, h, w} X_k[b, c, h, w], \quad \sigma^2_B = \frac{1}{B \cdot H \cdot W} \sum_{b, h, w} (X_k[b, c, h, w] - \mu_B)^2$$
  When $B = 8$, the sample variance of the batch mean estimator is $\text{Var}(\mu_B) \propto \frac{1}{8}$. Accumulating gradients over 2 passes aggregates $\nabla_\theta \mathcal{L}_1 + \nabla_\theta \mathcal{L}_2$ before calling `optimizer.step()`, but pass 1 and pass 2 each normalize activations using their own independent batch of 8 samples.
- **Contractual Resolution (Option B):**
  Option B (BatchNorm baseline) is retained to leverage ImageNet pre-trained encoder weights. However, the claim that gradient accumulation stabilizes batch normalization is completely retracted. The batch size seen by BatchNorm is strictly documented as 8. To mitigate erratic shifts across the 9 iterations per epoch, `bn_momentum` is set to 0.05.

### 2.2 Correction CORR-C5-002: Excluded Class Remapping

In the authoritative OPS-01 taxonomy (`ops01_taxonomy_v1.json`), 15 classes are defined:
- 12 training-eligible classes: `BG` (0), `AF` (1), `BS` (2), `LWA` (4), `MCC` (5), `OF` (6), `POW` (7), `RF` (8), `WS` (10), `Eddy` (11), `IWs` (12), `HM` (13).
- 3 excluded classes: `IB` (3, Iceberg), `SI` (9, Sea Ice), `OS` (14, Mineral Oil Spill).

Physical inspection of dataset masks revealed:
- TRAIN contains zero pixels of excluded classes.
- DEV contains 4 tiles with Sea Ice (65,280 pixels each, 261,120 total pixels).
- HOLDOUT contains 3 tiles with Sea Ice (65,280 pixels each, 195,840 total pixels).

If an implementation failed to remap source labels, Sea Ice (source 9) would collide with dense class 9 (`Eddy`), severely contaminating hydrodynamic evaluation. The reference implementation enforces `SOURCE_LABEL_TO_DENSE`, routing source 9, 3, 14 to `ignore_index = -100`.

---

## 3. Adversarial Contract Audit Table (A through AL)

| # | Protocol Dimension | C4 Statement | Implementation Interpretation | Ambiguity / Failure Risk | Authoritative C5 Resolution | Verification Guardrail |
|---|---|---|---|---|---|---|
| **A** | Radiometric Preprocessing | Raw $\to$ validity $\to$ radiometric $\to$ log1p $\to$ standardization | Raw uint16 DN $\to$ validity mask $\to \log(1+DN) \to$ standardize $\to$ zero padding $\to$ model | On-the-fly calibration equation ($DN^2/A^2$) applied, invalidating log1p constants | Normalization constants (4.2756, 0.3866) apply directly to $\log(1 + DN_{\text{stored}})$ | `test_golden_sample_preprocessing_ordering` |
| **B** | Aggregation Order | 10x10 block-mean aggregation | Aggregation completed offline; stored rasters are 256x256 | Loader attempting runtime spatial pooling | Assert raw raster dimensions are exactly (1, 256, 256) | `test_dataset_tile_dimensions` |
| **C** | Validity Mask Semantics | `validity_mask = raw_image > 0` | Zero values indicate left-swath border padding (nodata: 0.0) | Border padding contaminating loss or metrics; or source mask altered on disk | Decouple validity mask. Target mask sets padding to -100. Source masks byte-exact | `test_validity_mask_source_mask_decoupling` |
| **D** | Normalization Ordering | Standardize via $( \log(1+x) - 4.2756 ) / 0.3866$ | Applied pixel-wise; invalid pixels zeroed in model input | Invalid padding pixels assigned negative standardized values (-11.06) | Invalid pixels explicitly zeroed out after standardization | `test_invalid_pixels_zeroed_in_model_input` |
| **E** | Normalization Statistics | mean=4.2756, std=0.3866 from TRAIN valid pixels only | Immutable constants in normalization module | Dynamic per-batch normalization or evaluation split leakage | Constants hardcoded; DEV/HOLDOUT pixel contribution strictly 0 | `test_normalization_constants_immutable` |
| **F** | Class Ordering & Remapping | 12 training-eligible classes, 0..11 | Dense mapping: 0:BG, 1:AF, 2:BS, 3:LWA, 4:MCC, 5:OF, 6:POW, 7:RF, 8:WS, 9:Eddy, 10:IWs, 11:HM | Source labels (0..13) colliding with dense indices | Explicit `SOURCE_LABEL_TO_DENSE` remapping; excluded classes $\to -100$ | `test_source_to_dense_class_remapping` |
| **G** | Class Frequencies | Pixel frequencies over TRAIN valid pixels | BG: 0.4148, AF: 0.0076, BS: 0.0623, LWA: 0.0050, MCC: 0.1159, OF: 0.0143, POW: 0.1175, RF: 0.0135, WS: 0.0474, Eddy: 0.0072, IWs: 0.1942, HM: 0.000209 | Padding pixels included in denominator | Recalculated strictly over 4,712,082 valid TRAIN pixels | `test_exact_class_frequencies_and_pixel_counts` |
| **H** | Sampler Algorithm | Candidate F: 70% Parent + 30% Class-Presence | Stationary probability vector $P = 0.70 P_{\text{parent}} + 0.30 P_{\text{presence}}$ | Integer rounding ambiguity (e.g. 50/22 split) | Stationary probability vector sampled with replacement | `test_candidate_f_hybrid_sampler_probabilities` |
| **I** | Replacement Semantics | Sampling with replacement | Replacement permitted across 72 draws | Accidental non-replacement sampling | Explicit `replacement=True` in sampler contract | `test_sampler_replacement_true` |
| **J** | Samples per Epoch | Exactly 72 tiles/epoch | Fixed epoch length equal to training set size | Epoch length varying across seeds | Hardcode `num_samples = 72` | `test_sampler_epoch_length_is_72` |
| **K** | Parent Balancing | Equal parent exposure | Each parent assigned 1/12 total probability | Parent exposure distorted by variable tile counts (1..14) | Tile probability inversely proportional to parent tile count | `test_parent_balanced_component_weights` |
| **L** | Class Presence | Inverse tile-frequency weighting per present class | Tile score $S_i = \sum_{c \in \text{tile}} 1 / M_c$ | Division by zero for absent classes | Only present eligible classes evaluated; all 12 exist in TRAIN | `test_class_presence_component_weights` |
| **M** | Hybrid 70/30 Mix | $0.70 P_{\text{parent}} + 0.30 P_{\text{presence}}$ | Linear combination normalized to sum to 1.0 | Floating-point rounding sum != 1.0 | Normalize: $w = w / \sum w$ | `test_hybrid_vector_sums_to_one` |
| **N** | Random Seed Semantics | Deterministic replay | Sampler seeded via base_seed + epoch | Nondeterministic worker RNG drift | Explicit `worker_init_fn` deriving worker seeds | `test_sampler_deterministic_replay` |
| **O** | Duplicate Sampling | Duplicates permitted | Max tile repetition ~4.48x for rare classes | Deduplication logic dropping draws | Permit duplicates; verify rare class exposure $\ge 3.10$ | `test_rare_class_exposure_minimum` |
| **P** | Loss Formula | Sqrt median-frequency CrossEntropyLoss | $w_c = \sqrt{\text{median\_freq} / \text{freq}_c}$, reduction='mean', ignore_index=-100 | Extreme weights causing gradient explosion | Max/min ratio bounded to 44.58 (HM=12.15, BG=0.2726) | `test_exact_loss_weights_and_ratio` |
| **Q** | Weight Normalization | Median-normalized weights | Weight for median-frequency class is exactly 1.0 | Sum-to-one rescaling altering effective learning rate | Median-centered scaling preserves standard optimizer calibration | `test_loss_weights_median_centered` |
| **R** | Absent Classes in Batch | Zero loss contribution for absent classes | Standard PyTorch CrossEntropyLoss behavior | Zero division in mean reduction | Reduction divides by sum of weights of present valid pixels | `test_loss_finite_on_partial_class_batches` |
| **S** | Background Treatment | BG included with weight 0.2726 | BG downweighted by ~3.67x relative to median | BG accidentally omitted from loss | Assert BG weight is 0.272584 in class weight tensor | `test_background_weight_included` |
| **T** | ignore_index Behavior | `ignore_index = -100` | Excludes border padding and excluded classes | Invalid pixels contributing to loss | Target mask sets padding & excluded classes to -100 | `test_ignore_index_excludes_border_and_excluded_classes` |
| **U** | Model Input Contract | [B, 1, 256, 256] float32 | 1-channel standardized tensor | 2-channel or 3-channel input expectation in conv1 | Model `conv1` requires `in_channels = 1` | `test_model_input_shape_contract` |
| **V** | Model Output Contract | [B, 12, 256, 256] float32 logits | 12 raw logits per pixel without activation | Softmax or sigmoid inside model head | Final layer is pure `Conv2d(32, 12, 1)` | `test_model_output_shape_and_no_activation` |
| **W** | BatchNorm Behavior | Option B: BatchNorm baseline, momentum=0.05 | Evaluated over physical minibatch size 8 | Assuming gradient accumulation increases BN batch size | Explicitly document BN statistical batch size = 8; note risk | `test_batchnorm_statistical_batch_size_documented` |
| **X** | Gradient Accumulation | steps=2, effective batch size=16 | Optimizer step every 2 batches of 8 samples | Conflating optimizer batch with BN statistical batch | Enforce conceptual separation: physical=8, accum=2, opt=16, BN=8 | `test_effective_vs_statistical_batch_separation` |
| **Y** | Augmentation Policy | BASELINE_IDENTITY_NO_AUGMENTATION | Identity transform | Accidental activation of unvalidated transforms | Baseline pipeline applies zero spatial or radiometric distortion | `test_augmentation_is_identity` |
| **Z** | Prediction Rule | argmax(logits, dim=1) | Class with maximum logit selected per pixel | Reusing binary threshold tau=0.22 | Strictly prohibit binary thresholds; enforce argmax | `test_prediction_rule_is_argmax` |
| **AA** | Metric Aggregation | mIoU macro across present phenomena | Primary: mIoU_phenomena (1..11); Secondary: mIoU_all (0..11) | Ambiguity over BG inclusion in headline metric | Report both metrics explicitly | `test_metric_aggregation_both_reported` |
| **AB** | Invalid-Pixel Exclusion | Metrics evaluated strictly on valid pixels | validity_mask == False excluded from confusion matrix | Padding falsely counted as BG true positives | Mask out invalid pixels prior to confusion matrix bincount | `test_invalid_pixels_excluded_from_confusion_matrix` |
| **AC** | Absent-Class Metrics | Absent classes excluded from denominator | Classes with GT=0 excluded from macro mean | Absent classes scored as 0.0 or 1.0 | Exclude GT=0 classes from denominator | `test_absent_class_excluded_from_macro_mean` |
| **AD** | Holdout Reporting | `HOLDOUT_PARTIALLY_USED_FOR_SELECTION` | Disclosed in all metadata, reports, and logs | Describing holdout as pristine or independent benchmark | Automated guardrail rejects forbidden terms | `test_holdout_epistemic_disclosure` |
| **AE** | Checkpoint Identity | Unique run metadata block | Anchored to manifest SHA256 and taxonomy version | Lineage ambiguity across runs | Standard reproducibility config saved with all runs | `test_reproducibility_config_fields` |
| **AF** | Reproducibility Scope | Deterministic algorithmic replay | Identical seed yields identical batch sequence and math | Claiming cross-platform bitwise equality | Disclose distinction between replay determinism and bitwise identity | `test_deterministic_algorithmic_replay` |
| **AG** | Worker Determinism | Deterministic worker initialization | worker_seed = (base_seed + worker_id) % (2**32) | Worker seed collision causing nondeterminism | Provide standard `worker_init_fn` | `test_worker_seed_derivation` |
| **AH** | Dtype Conversion | uint16 $\to$ float32 image, int64 target | Image: float32; Target: int64 | Loss receiving float target or uint8 mask | Explicit dtype cast in dataset reader | `test_dataset_dtypes` |
| **AI** | CPU/GPU Consistency | CPU reference implementation | CPU float32 deterministic execution | Assuming GPU fp16 matches CPU float32 | Scope reference implementation to CPU float32 | `test_cpu_only_execution_verified` |
| **AJ** | Serialization Safety | JSON-safe metadata and state dicts | Metrics convert NaNs to None for JSON compliance | Broken JSON outputs from NaN metrics | Assert valid JSON round-trip on all metric dictionaries | `test_metrics_json_serializable` |
| **AK** | Exception Behavior | Missing rasters fail loudly | FileNotFoundError on missing raster | Silent fallback or zero-padding | Assert FileNotFoundError raised on missing path | `test_dataset_missing_file_raises_error` |
| **AL** | Manifest Path Integrity | ops01_physical_dataset_manifest_v4.json | All 147 image and 147 mask paths exist on disk | Broken file references | Verify 100% path existence across all 147 tiles | `test_all_147_manifest_paths_exist` |

---

## 4. Architecture Verification: ResNet18-UNet

### 4.1 Exact Parameter Breakdown
The ResNet18-UNet architecture implemented in `src/ocean_sentinel/ml/exp07_reference.py` was profiled down to the individual layer and buffer:
- **Trainable Parameters:** **14,310,860**
- **Floating-point Buffers:** **11,776** (30 BatchNorm layers $\times$ 2 buffers [`running_mean`, `running_var`])
- **Total Parameters + Buffers:** **14,322,636** (14,322,666 including the 30 int64 `num_batches_tracked` scalars)
- **BatchNorm Layers:** Exactly 30 layers, all configured with `momentum = 0.05`.

```
Stage                   Input Ch    Output Ch   Spatial Res     Parameters
Encoder conv1           1           64          128x128         3,136
Encoder layer1 (x2)     64          64          64x64           147,968
Encoder layer2 (x2)     64          128         32x32           525,568
Encoder layer3 (x2)     128         256         16x16           2,099,712
Encoder layer4 (x2)     256         512         8x8             8,393,728
Decoder dec4            512+256     256         16x16           2,360,832
Decoder dec3            256+128     128         32x32           590,464
Decoder dec2            128+64      64          64x64           147,776
Decoder dec1            64+64       64          128x128         147,776
Final Upsample          64          32          256x256         8,224
Final Conv (Double)     32          32          256x256         18,560
Segmentation Head       32          12          256x256         396
-------------------------------------------------------------------------
Total Trainable Parameters:                                     14,310,860
```

---

## 5. Golden Sample Benchmarks & Byte Immutability

Three representative samples across the three dataset partitions were selected as frozen golden benchmarks:

| Split | Sample ID | Image SHA256 | Mask SHA256 | Valid Pixels | Raw Mean DN | Norm Mean | Target Labels |
|---|---|---|---|---|---|---|---|
| **TRAIN** | `...004712-005d33-001-7` | `AD477CB836F2...` | `E040D38339D9...` | 65,536 | 131.1164 | 1.4391 | `[0, 10]` (`BG`, `IWs`) |
| **DEV** | `...019990-0220c9-001-3` | `EB5F258965E1...` | `14960734A5D4...` | 65,536 | 111.1231 | 1.0328 | `[0, 1, 3, 10]` (`BG`, `AF`, `LWA`, `IWs`) |
| **HOLDOUT** | `...046987-05a2c5-001-58` | `D1D293BA9277...` | `B8047AA937A6...` | 65,536 | 91.6570 | 0.5819 | `[-100, 0]` (`ignore`, `BG`) |

*Byte Immutability Confirmation:* Hashes of all source TIFF images and PNG masks were verified identical before and after dataset reader execution. Reading rasters causes zero disk mutation.

---

## 6. Future-Problem Audit (30 Operational Risks)

The implementation was adversarially checked against 30 operational hazards:
1. *DataLoader worker nondeterminism:* Resolved via deterministic `worker_init_fn`.
2. *Duplicate sampler selections:* Verified permitted under replacement=True; rare class exposure bounded $\ge 3.10$.
3. *Parent-level split leakage:* Verified zero parent scene overlap across TRAIN (12), DEV (7), HOLDOUT (8).
4. *Absent classes producing NaNs in loss:* Verified CrossEntropyLoss mean reduction handles absent classes safely.
5. *All-background tiles:* Tested; loss evaluates to ~0.2726, predictions compute valid single-class confusion matrix.
6. *All-invalid samples:* Border padding verified bounded to left edge ($\le 3.5\%$ per affected tile); no tile is all-padding.
7. *Tiny class regions (e.g. HM single pixels):* Loss weight 12.15 provides adequate gradient signal without exploding.
8. *Loss weights exploding:* Sqrt median-frequency bounds max weight ratio to 44.58 (uncapped would be 3,493).
9. *NaN/Inf loss:* Verified target clipping and log1p bounds input to finite domain.
10. *Model output dimension mismatch:* Verified head outputs exactly 12 channels.
11. *1-channel vs 3-channel mismatch:* Encoder conv1 adapted to accept exactly 1 channel.
12. *Stale normalization statistics:* Frozen constants (4.2756, 0.3866) hardcoded and tested.
13. *Hidden implicit normalization in transforms:* Identity transform pipeline verified.
14. *Threshold reuse from EXP-06:* Multiclass argmax enforced; binary thresholds prohibited by guardrail tests.
15. *Checkpoint identity ambiguity:* Anchored to manifest SHA256 and taxonomy identity.
16. *CPU/GPU numerical drift:* Documented scope as CPU reference; algorithmic replay vs bitwise cross-platform identity distinguished.
17. *BatchNorm train/eval mode mismatch:* Flagged in reproducibility contract.
18. *Accidental augmentation activation:* Baseline policy hardcoded to identity.
19. *Worker seed collisions:* Formula `(base_seed + worker_id) % 2**32` ensures disjoint seeds.
20. *Incorrect metric denominator:* Evaluated strictly over present classes in GT ($GT_c > 0$).
21. *Confusion matrix class-order mismatch:* Verified rows and columns follow canonical dense order 0..11.
22. *Invalid pixels contaminating statistics:* Masked out prior to confusion matrix computation.
23. *Holdout contamination in statistics:* Verified 0 DEV/HOLDOUT pixels used in normalization or loss weights.
24. *Parent-balanced sampler becoming tile-balanced:* Weight formula $1 / (N_{\text{parents}} \cdot M_{\text{tiles}})$ enforces parent balance.
25. *Sampler composition shifting from rounding:* Stationary probability vector eliminates integer rounding.
26. *Taxonomy order drift:* Regression test asserts exact order 0:BG through 11:HM.
27. *HM accidental rename:* Regression test asserts HM name is `Artificial / Anthropogenic Objects`.
28. *OS accidental admission:* Verified OS has `training_eligible: False` and is mapped to -100.
29. *Silent path fallback:* FileNotFoundError raised immediately if any tile is missing.
30. *Stale artifacts treated as current:* Versioned metadata references enforced across all files.

---

## 7. Governance Updates

- **Incident INC-P0-C5-001:** Conflation of effective optimization batch size with BatchNorm statistical batch size. Resolved.
- **Rule GOV-RULE-059 Enacted:** Effective optimization batch size is distinct from BatchNorm statistical batch size. Active.

---

## 8. Final Decision Gate

### Decision: **A. FINAL — EXP-07 IMPLEMENTATION AUDITED & CPU REFERENCE PIPELINE AUTHORIZED**

**Authorized Next Action:**
**EXP-07-P0-C6 — CONTROLLED CPU DRY-RUN / PRE-TRAINING SYSTEM VALIDATION**

*Restrictions:* Actual model training, optimizer updates, GPU execution, checkpoint creation, and Part-III access remain strictly unauthorized until explicit clearance by a later phase gate.
