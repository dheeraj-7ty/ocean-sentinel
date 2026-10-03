# EXP-07 — SCIENTIFIC PROTOCOL SPECIFICATION & OPS-01 DATA INTERFACE CONTRACT
## Ocean Sentinel · Phase EXP-07-P0 · 2026-09-13

**Document ID:** `PHASE_EXP07_P0_SCIENTIFIC_PROTOCOL_AND_OPS01_CONTRACT_20260913`
**Status:** `DRAFT — AWAITING OPERATOR AUTHORIZATION FOR TRAINING`
**Branch:** `master`
**EXP-06 Baseline SHA:** `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` VERIFIED
**Part-I SHA:** `17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072` VERIFIED
**OPS-01 Manifest v4 SHA:** `FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E`
**Governance:** `ocean_sentinel_governance_rules_v1.md` (2.0.0, GOV-RULE-001 thru 045 ACTIVE)
**Reproducibility Level:** OPS-01 Level B (Level C and D permanently prohibited)

---

## PERMANENT EPISTEMIC DISCLOSURES (MANDATORY — DO NOT REMOVE)

1. `HOLDOUT_PARTIALLY_USED_FOR_SELECTION` — Holdout parent scenes were selected to satisfy class coverage criteria; holdout is not purely blind.
2. `CONDITIONAL_ENGINEERING_RECONSTRUCTION` — Spatial alignment reconstructed under engineering constraints; not physically measured.
3. `EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS` — 10x10 block mean correspondence is empirically supported, not historically confirmed.
4. `DATASET_GENERATION_METHOD = NOT_DIRECTLY_VERIFIED` — Li et al. source dataset generation was not independently executed.

---

## 1. EXECUTIVE OVERVIEW

EXP-07 is the first training experiment on the **OPS-01 dataset** — 147 Sentinel-1 IW GRD crops with multi-class semantic segmentation labels across 12 eligible classes. Class 14 (Mineral Oil Spill / OS) is permanently excluded with 0 admitted pixels.

EXP-07 differs fundamentally from EXP-01 through EXP-06:

| Dimension | EXP-01 through EXP-06 | EXP-07 |
|:---|:---:|:---:|
| Dataset | Part-I (Trujillo et al.) | OPS-01 (Li et al.) |
| Task | Binary: spill vs background | Multi-class maritime scene segmentation |
| Image bands | 2 (VV+VH, dB) | 1 (VV only, raw amplitude DN) |
| Image size | 512x512 | 256x256 |
| Mask type | Binary {0,1} | Integer class labels 0-14 |
| Training samples | ~13,440 tiles | 72 physical samples |
| Architecture | ResNet34UNet (binary head) | ResNet18-UNet (12-class head) |

EXP-07 is the **scientific foundation** of the Ocean Sentinel maritime intelligence platform. It is NOT merely an oil-spill detector.

---

## 2. THE SCIENTIFIC QUESTION

### Primary Question

> Can a compact deep learning segmentation model trained on 72 OPS-01 TRAIN samples (4,718,592 pixels, 12 eligible classes) learn to reliably distinguish major classes of Sentinel-1 SAR sea-surface backscatter phenomena, including natural lookalike classes that historically confound oil-spill detection?

### Secondary Questions

- **SQ-1:** Can the trained model suppress natural lookalike classes (Biological Slicks, Low Wind Area, Internal Waves) that caused >89% false alarm rates in EXP-06 proxy evaluation?
- **SQ-2:** Can multi-class supervision provide richer semantic gradients than binary supervision for maritime intelligence tasks?
- **SQ-3:** What is the achievable segmentation performance given severely limited sample count (72 TRAIN / 39 DEV) and extreme class imbalance?

### What EXP-07 Does NOT Claim To Test

- EXP-07 is NOT a direct oil-spill classifier (OS class is excluded from OPS-01).
- EXP-07 performance does NOT imply deployment readiness on Part-III or external benchmarks.
- EXP-07 holdout results are NOT fully blinded performance estimates (HOLDOUT_PARTIALLY_USED_FOR_SELECTION).

---

## 3. EVIDENCE-BASIS FOR PROTOCOL DECISIONS

### 3.1 Why Multi-Class OPS-01 Is the Next Scientific Step

EXP-06 proxy zero-shot evaluation (Phase 7A.2/7A.3) revealed:
- Provisional Proxy Alarm Rate: **89.75%** across 517 patches (semantic ground truth: SEMANTIC_STATUS_UNRESOLVED)
- Parent Product Alarm Rate: **89.23%** across 325 parent acquisitions
- Pixel False Positive Rate: **71.61%**

This diagnostic suggests EXP-06 cannot distinguish petroleum spill signatures from natural sea-surface phenomena sharing low-backscatter characteristics. The scientifically justified remediation is multi-class supervision that explicitly recognizes and distinguishes natural classes.

> Per GOV-RULE-008: Class presence != causal model failure. This is correlational evidence of a detection gap, NOT confirmed causation. EXP-07 is designed to TEST whether multi-class supervision reduces this gap.

### 3.2 Class Distribution in TRAIN (Evidence for Weighting Decisions)

From OPS-01 manifest radiometric_stats and class_composition (72 TRAIN samples, 4,718,592 pixels):

| Class | Pixels | Fraction | Samples |
|:---|---:|:---:|:---:|
| BG (Background Seawater) | 1,957,266 | 41.48% | 56 |
| IWs (Internal Waves) | 916,153 | 19.42% | 36 |
| POW (Pure Ocean Wave) | 554,669 | 11.75% | 15 |
| MCC (Mesoscale Cellular Convection) | 547,092 | 11.59% | 12 |
| BS (Biological Slicks) | 293,888 | 6.23% | 7 |
| WS (Wind Streak) | 223,848 | 4.74% | 6 |
| OF (Ocean Front) | 67,425 | 1.43% | 24 |
| RF (Rain Cell / Rain Footprint) | 63,801 | 1.35% | 8 |
| AF (Atmospheric Front) | 35,931 | 0.76% | 9 |
| Eddy (Oceanic Eddy) | 34,110 | 0.72% | 3 |
| LWA (Low Wind Area) | 23,424 | 0.50% | 2 |
| HM (Artificial/Anthropogenic Objects) | 985 | 0.02% | 7 |

---

## 4. RESOLVED PROTOCOL DECISIONS — ALL 14 OPEN ISSUES CLOSED

### OPEN-PREPROC-001: Value Domain

**DECISION: 10*log10 pseudo-dB of raw amplitude DN**

Formula: `preprocessed = 10 * log10(DN + 1e-6)`

Rationale: Raw amplitude DN is right-skewed (TRAIN mean ~76.65, max ~2698.93). Log transform compresses dynamic range, produces approximately Gaussian distributions, and is standard SAR practice. The epsilon `1e-6` guards against log(0) on zero-valued pixels.

Caveats: Non-calibrated pseudo-dB transform — NOT ESA-calibrated Sigma0. Absence of absolute radiometric calibration is a permanent epistemic limitation.

**Scientific status:** ENGINEERING DECISION (domain normalization). Frozen.

---

### OPEN-PREPROC-002: Normalization Statistics

**DECISION: Computed on TRAIN split only, applied uniformly to DEV and HOLDOUT**

Method: Pixel-wise streaming statistics across all 72 TRAIN samples AFTER pseudo-dB conversion.

The frozen normalization constants MUST be computed at EXP-07 preflight as the first executable step, stored in `data/metadata/exp07_normalization_stats.json`, and verified by SHA256 before model training begins.

Preliminary approximation (from manifest raw DN stats, NOT the frozen values):
- Raw DN pooled mean: ~76.65, pooled std: ~31.84
- After 10*log10: approximate mean ~17-19 dB, std ~4-6 dB (ORDER OF MAGNITUDE ONLY)

**Scientific status:** SCIENTIFIC PROTOCOL DECISION. Must not vary between epochs.

---

### OPEN-PREPROC-003: Augmentation Policy

**DECISION: Conservative two-flip augmentation (TRAIN only)**

Policy:
- Random horizontal flip: p=0.5
- Random vertical flip: p=0.5
- NO rotation (SAR imagery has look-direction semantics)
- NO intensity jitter (would corrupt calibrated DN)
- NO elastic deformation (would corrupt co-registered mask boundaries)
- DEV and HOLDOUT: identity transform only

Seed: `AUG_SEED = GLOBAL_SEED + epoch_index * 100` per epoch

**Scientific status:** SCIENTIFIC PROTOCOL DECISION. Frozen.

---

### OPEN-PREPROC-004: Label Encoding

**DECISION: Multi-class cross-entropy with 12 eligible classes**

Label LUT (FROZEN — DO NOT MODIFY):

```
LABEL_LUT = {
    0:  0,   # Background Seawater (BG)
    1:  1,   # Atmospheric Front (AF)
    2:  2,   # Biological Slicks (BS)
    3:  255, # Iceberg / Ice Cluster (IB) — IGNORE
    4:  3,   # Low Wind Area (LWA)
    5:  4,   # Mesoscale Cellular Convection (MCC)
    6:  5,   # Ocean Front (OF)
    7:  6,   # Pure Ocean Wave (POW)
    8:  7,   # Rain Cell / Rain Footprint (RF)
    9:  255, # Sea Ice (SI) — IGNORE
    10: 8,   # Wind Streak (WS)
    11: 9,   # Oceanic Eddy (Eddy)
    12: 10,  # Internal Waves (IWs)
    13: 11,  # Artificial/Anthropogenic Objects (HM)
    14: 255, # Mineral Oil Spill (OS) — PERMANENTLY EXCLUDED; assert 0 pixels
}
IGNORE_INDEX = 255
NUM_CLASSES = 12
```

Output index table:

| Output Idx | Class | source_label_id |
|:---:|:---|:---:|
| 0 | Background Seawater (BG) | 0 |
| 1 | Atmospheric Front (AF) | 1 |
| 2 | Biological Slicks (BS) | 2 |
| 3 | Low Wind Area (LWA) | 4 |
| 4 | Mesoscale Cellular Convection (MCC) | 5 |
| 5 | Ocean Front (OF) | 6 |
| 6 | Pure Ocean Wave (POW) | 7 |
| 7 | Rain Cell / Rain Footprint (RF) | 8 |
| 8 | Wind Streak (WS) | 10 |
| 9 | Oceanic Eddy (Eddy) | 11 |
| 10 | Internal Waves (IWs) | 12 |
| 11 | Artificial/Anthropogenic Objects (HM) | 13 |

**Scientific status:** SCIENTIFIC PROTOCOL DECISION. Frozen.

---

### OPEN-LOADER-001: OPS-01 DataLoader Implementation

**DECISION: Implement OPS01Dataset (new class, distinct from TrujilloTileDataset)**

Contract:
- Reads from `data/metadata/ops01_physical_dataset_manifest_v4.json` (SHA verified at init)
- Partition-filtered (TRAIN / DEV / HOLDOUT — no cross-contamination)
- Part-III firewall assertion: raises ValueError if any path matches Part-III patterns
- Returns: `(image_tensor: float32 (1,256,256), label_tensor: int64 (256,256))`
- Zero silent failures: raises on missing file, corrupted file, SHA256 mismatch
- Label LUT applied at load time

**Scientific status:** ENGINEERING IMPLEMENTATION, but the contract is scientific.

---

### OPEN-LOADER-002: Class Balancing / Oversampling

**DECISION: Inverse-frequency sample-level oversampling via WeightedRandomSampler (TRAIN only)**

Method: Each TRAIN sample weight = inverse of its dominant class pixel fraction. Samples from rare-class-dominated tiles (LWA: 2 samples, Eddy: 3 samples) are upsampled proportionally.

DEV / HOLDOUT: Sequential sampler, no oversampling.

**Scientific status:** SCIENTIFIC PROTOCOL DECISION (affects gradient composition).

---

### OPEN-LOADER-003: num_workers and pin_memory

**DECISION: num_workers=0, pin_memory=False**

Rationale: Windows IPC deadlock issue documented in EXP-06 training prohibits num_workers>0 without CUDA guard. These settings sacrifice throughput for determinism and stability.

**Scientific status:** ENGINEERING DECISION.

---

### OPEN-LOADER-004: Batch Size

**DECISION: Batch size = 8**

Rationale: 72 TRAIN samples / batch_size=8 = 9 batches per epoch. Provides stable gradient estimates. Batch_size=16 would yield only ~4-5 batches/epoch (too coarse). Batch_size=4 yields ~18 batches (acceptable but slower).

**Scientific status:** ENGINEERING DECISION with scientific consequence.

---

## 5. ARCHITECTURE (OPEN-ARCH-001)

**DECISION: ResNet18-UNet, 1 input channel, 12 output classes**

| Parameter | Value | Justification |
|:---|:---:|:---|
| Backbone | ResNet18 | 72 TRAIN samples; ResNet34 likely over-parameterized |
| Input channels | 1 (VV pseudo-dB) | Physical constraint |
| Input spatial | 256x256 | Physical constraint |
| Decoder | Standard U-Net skip connections | Dense prediction |
| Output head | 12-class softmax | Multi-class supervision |
| Pre-training | Scratch | ImageNet weights inapplicable to SAR |
| Weight init | Kaiming uniform (He initialization) | Standard for ReLU |
| Parameters | To be recorded in run_manifest.json | — |

> WARNING: EXP-06 used ResNet34UNet with 24,346,305 parameters trained on 13,440 tiles. OPS-01 has only 72 TRAIN tiles. ResNet34 is almost certainly over-parameterized. ResNet18 (~11M parameters) is the conservative scientifically justified choice. Do NOT substitute ResNet34 without re-evaluating this rationale.

**Scientific status:** SCIENTIFIC PROTOCOL DECISION. Frozen.

---

## 6. LOSS FUNCTION (OPEN-LOSS-001)

**DECISION: Weighted multi-class cross-entropy with inverse-frequency class weights**

Formula: L = -sum_c(w_c * 1[y=c] * log(p_c))

Weight formula: w_c = median(f_0,...,f_11) / f_c, capped at w_max = 10.0

Where f_c = fraction of TRAIN pixels belonging to class c.

IGNORE_INDEX = 255 pixels contribute zero loss.

Rationale: Standard CE without class weighting would be dominated by BG (41.48%) and IWs (19.42%). Pure inverse-frequency weighting would assign extreme weight to HM (0.02%), destabilizing training. The median-normalized, capped scheme balances the gradient signal.

Class weights MUST be computed from TRAIN split statistics before training and stored in `experiments/performance/exp07_ops01_multiclass/class_weights.json`.

**Scientific status:** SCIENTIFIC PROTOCOL DECISION. Frozen.

---

## 7. OPTIMIZER AND SCHEDULER (OPEN-OPT-001)

**DECISION:**
- Optimizer: `AdamW(lr=1e-3, weight_decay=1e-2, betas=(0.9, 0.999))`
- Scheduler: `CosineAnnealingLR(T_max=50, eta_min=1e-5)`
- Total epochs: 50
- Early stopping: patience=15 epochs on DEV mIoU (guard against overfitting; does not modify acceptance gates)

Rationale: Higher initial LR (1e-3 vs EXP-06's 1e-4) compensates for fewer batches per epoch (9 vs 896 in EXP-06). 50 epochs x 9 batches = 450 total optimizer steps.

**Scientific status:** SCIENTIFIC PROTOCOL DECISION. Frozen.

---

## 8. SEED POLICY (OPEN-SEED-001)

**DECISION:**
- GLOBAL_SEED = 42
- Weight initialization: torch.manual_seed(42) + torch.cuda.manual_seed(42)
- DataLoader sampler: generator.manual_seed(42 + epoch * 1000)
- Augmentation: random.seed(42 + epoch * 100) per epoch
- Determinism flags: torch.backends.cudnn.deterministic = True, benchmark = False

**Scientific status:** SCIENTIFIC PROTOCOL DECISION. Frozen.

---

## 9. METRIC DEFINITIONS & THRESHOLD PROTOCOL (OPEN-METRIC-001)

### Primary Metric

Mean Intersection-over-Union (mIoU) across 12 eligible classes (IGNORE pixels excluded):

  mIoU = (1/12) * sum_c(TP_c / (TP_c + FP_c + FN_c))

### Secondary Metrics (All Computed on DEV)

| Metric | Definition |
|:---|:---|
| Per-class IoU | TP_c / (TP_c + FP_c + FN_c) |
| Per-class F1/Dice | 2*TP_c / (2*TP_c + FP_c + FN_c) |
| Per-class Recall | TP_c / (TP_c + FN_c) |
| Per-class Precision | TP_c / (TP_c + FP_c) |
| Overall Pixel Accuracy | sum_c(TP_c) / N_valid |
| Macro Recall (unweighted) | mean of per-class recall |

### Threshold Protocol

EXP-07 uses a softmax head. Predicted class = argmax(softmax(logits)). No operating threshold parameter.

### Holdout Evaluation Protocol

1. Evaluate on HOLDOUT exactly ONCE, after training is complete and DEV-selected best checkpoint is frozen.
2. Report with `HOLDOUT_PARTIALLY_USED_FOR_SELECTION` disclosure.
3. Do not use HOLDOUT metrics to re-select checkpoints or modify any parameter.

**Scientific status:** SCIENTIFIC PROTOCOL DECISION. Frozen.

---

## 10. CHECKPOINT POLICY (OPEN-CKPT-001)

**DECISION:**
- Save checkpoint whenever DEV mIoU improves over all prior epochs
- Best checkpoint: `experiments/performance/exp07_ops01_multiclass/best_model.pt`
- Final checkpoint: `experiments/performance/exp07_ops01_multiclass/last_model.pt`
- SHA256 of best_model.pt must be recorded in run_manifest.json before HOLDOUT eval

**Scientific status:** SCIENTIFIC PROTOCOL DECISION. Frozen.

---

## 11. THE FALSIFIABLE SCIENTIFIC HYPOTHESIS

> "Training a ResNet18-UNet segmentation model on the 72-sample OPS-01 TRAIN partition with 12-class cross-entropy supervision, inverse-frequency class weighting, WeightedRandomSampler oversampling, 50-epoch CosineAnnealing training, and conservative flip augmentation will produce a model achieving **DEV mIoU >= 0.30** across 12 eligible classes, demonstrating that the OPS-01 dataset is sufficient to teach a compact model to distinguish major maritime SAR backscatter classes despite severely limited training sample count."

### Explicit Falsification Conditions

1. DEV mIoU at best checkpoint **< 0.30** (below threshold for meaningful class discrimination).
2. Per-class IoU for Background Seawater (BG) **< 0.60** (41.48% of pixels; failure = fundamental instability).
3. Any evidence of HOLDOUT partition contamination during training or threshold selection.
4. OS pixels detected in the training pipeline (must remain 0).

### Success (PASS) Enables

- Proceed to EXP-08: threshold-calibrated multi-class maritime scene classification
- Baseline DEV mIoU for future regression testing
- Evidence that OPS-01 supports multi-class learning at 72 samples
- Foundation for Ocean Sentinel maritime intelligence roadmap

### Failure (FALSIFIED) Implies

- OPS-01 at 72 samples may be insufficient for 12-class segmentation
- Architecture or training changes required (new experiment)
- The FALSIFIED result is a valid scientific outcome and must be reported truthfully

---

## 12. PREREGISTERED ACCEPTANCE GATES (FROZEN — IMMUTABLE POST-TRAINING-START)

| Gate ID | Metric | Scope | Threshold | Type |
|:---|:---|:---|:---:|:---:|
| AG-EXP07-01 | DEV mIoU at best checkpoint | 12 eligible classes, 39 DEV samples | >= 0.30 | PRIMARY SCIENTIFIC |
| AG-EXP07-02 | DEV BG IoU | Background Seawater only | >= 0.60 | STABILITY GUARD |
| AG-EXP07-03 | DEV Macro Recall | All 12 classes, unweighted | >= 0.25 | SECONDARY |
| AG-EXP07-04 | Training completed | 50 epochs (or early stop, documented) | Documented | COMPLETION |
| AG-EXP07-05 | HOLDOUT evaluation timing | Single eval after DEV selection | Exactly once | PROTOCOL |
| AG-EXP07-06 | OS pixels in pipeline | Must be zero | = 0 | SAFETY |

> CAUTION: Acceptance gate thresholds are FROZEN at time of this protocol document. They MAY NOT be modified after training begins. Any post-hoc modification is a protocol violation (p-hacking equivalent).

---

## 13. OPS-01 DATA INTERFACE CONTRACT

### 13.1 Dataset Identity

| Field | Value |
|:---|:---|
| Manifest | data/metadata/ops01_physical_dataset_manifest_v4.json |
| Manifest SHA256 | FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E |
| Taxonomy | data/metadata/ops01_taxonomy_v1.json |
| Split Manifest | data/metadata/ops01_split_manifest_v4.json |
| Total Samples | 147 (72 TRAIN / 39 DEV / 36 HOLDOUT) |
| Parent Scenes | 27 independent IW GRD acquisitions |
| Physical Format | 1-band float32 GeoTIFF (256x256) + uint8 PNG mask |

### 13.2 OPS01Dataset Class Contract

```python
class OPS01Dataset(torch.utils.data.Dataset):
    """
    OPS-01 dataset loader for Ocean Sentinel EXP-07.

    Invariants (tested by guardrail suite):
    - Only loads samples from the specified partition {"TRAIN","DEV","HOLDOUT"}.
    - Returns (image_tensor: float32 (1,256,256), label_tensor: int64 (256,256)).
    - Applies pseudo-dB: image = 10 * log10(raw_DN + 1e-6).
    - Applies normalization: (image - TRAIN_MEAN) / TRAIN_STD (from exp07_normalization_stats.json).
    - Applies LABEL_LUT: source_label_id -> output_idx; excluded classes -> 255.
    - Applies flip augmentation in TRAIN mode only; identity in DEV/HOLDOUT.
    - Raises ValueError on: missing file, SHA256 mismatch, Part-III path, unknown label ID.
    - Part-III firewall: raises if any resolved path matches Part-III identifiers.
    - Zero OS pixels in TRAIN/DEV/HOLDOUT: assert on any occurrence.
    """
```

### 13.3 Normalization Constants (To Be Frozen at EXP-07 Preflight)

Must be computed by the EXP-07 preflight script:
1. Load all 72 TRAIN images with rasterio
2. Apply `10 * log10(pixel + 1e-6)` transform
3. Compute global mean and std over all pixels
4. Store in `data/metadata/exp07_normalization_stats.json`
5. Record SHA256 of normalization file in run_manifest.json

### 13.4 Sampling Strategy

| Partition | Sampler | Notes |
|:---|:---:|:---|
| TRAIN | WeightedRandomSampler | Inverse-dominant-class-freq weights |
| DEV | SequentialSampler | Deterministic |
| HOLDOUT | SequentialSampler | Single final evaluation only |

---

## 14. EXPERIMENT TELEMETRY & OBSERVABILITY

Required artifacts (ALL mandatory):

| Artifact | Path |
|:---|:---|
| Run manifest | experiments/performance/exp07_ops01_multiclass/run_manifest.json |
| Run state | experiments/performance/exp07_ops01_multiclass/run_state.json |
| Training log | experiments/performance/exp07_ops01_multiclass/training.log |
| Per-epoch history | experiments/performance/exp07_ops01_multiclass/history.json |
| Best checkpoint | experiments/performance/exp07_ops01_multiclass/best_model.pt |
| Final checkpoint | experiments/performance/exp07_ops01_multiclass/last_model.pt |
| Normalization stats | data/metadata/exp07_normalization_stats.json |
| Final DEV metrics | experiments/performance/exp07_ops01_multiclass/metrics.json |
| HOLDOUT eval | experiments/performance/exp07_ops01_multiclass/holdout_eval.json |
| Class weight record | experiments/performance/exp07_ops01_multiclass/class_weights.json |

---

## 15. SCOPE RESTRICTIONS

| Restriction | Authority |
|:---|:---:|
| No HOLDOUT access during training | ABSOLUTE |
| No Part-III access | ABSOLUTE (GOV-RULE-026) |
| No EXP-06 frozen artifacts modification | ABSOLUTE |
| OS pixels never enter training pipeline | ABSOLUTE |
| Normalization computed on TRAIN only | ABSOLUTE (GOV-RULE-025) |
| Acceptance gates not modifiable post-training-start | ABSOLUTE |
| HOLDOUT evaluated exactly once, post-DEV-selection | ABSOLUTE |

---

## 16. GOVERNANCE COMPLIANCE

This document resolves:
- GOV-RULE-023: Scientific protocol decisions frozen before implementation — COMPLIANT
- GOV-RULE-024: DataLoader contract specified before implementation — COMPLIANT
- GOV-RULE-025: Value domain explicitly resolved (OPEN-PREPROC-001 CLOSED) — COMPLIANT
- GOV-RULE-026: Training authorization still required from operator — PENDING

**Training remains PROHIBITED until the operator grants explicit GPU training authorization.**

---

## 17. TRAINING AUTHORIZATION CHECKLIST

Before any training execution, ALL must be confirmed:

- [ ] data/metadata/exp07_normalization_stats.json exists (computed from TRAIN-only images)
- [ ] OPS01Dataset implementation verified by guardrail test suite
- [ ] data/metadata/class_weights_exp07.json exists (computed from TRAIN class pixel distribution)
- [ ] experiments/performance/exp07_ops01_multiclass/ directory created
- [ ] run_manifest.json initialized with all frozen hashes and hyperparameters
- [ ] SHA256 of this protocol document recorded in run_manifest.json
- [ ] All 14 Open Protocol Decisions confirmed CLOSED (resolved in this document)
- [ ] Operator GPU training authorization: [ ] GRANTED

---

## 18. FUTURE WORK (OUT OF SCOPE FOR EXP-07)

- EXP-08: Threshold calibration, ROC analysis on DEV
- EXP-09: External lookalike benchmark evaluation (requires resolved semantic status)
- Part-III Evaluation: Permanently protected
- OPS-01 Dataset Expansion: Requires new data protocol
- Multi-band Extension: Adding VH requires re-auditing alignment and band registration

---

## 19. EXPLICIT NON-CLAIMS

This protocol does NOT establish:
- Expected performance on any external benchmark
- Superiority over EXP-06 on oil-spill detection
- Global representativeness of OPS-01 geographic sample
- Unbiased holdout performance estimate
- Physical georegistration ground truth
- Validated Li dataset-generation procedure
- That 72 TRAIN samples are sufficient for any downstream task beyond EXP-07

---

*Generated: 2026-09-13 | EXP-07-P0 | Ocean Sentinel | Branch: master*
*Protocol authored under GOV-RULE-023. Frozen hashes verified. 14/14 Open Protocol Decisions resolved.*
*Training prohibited until explicit operator GPU authorization.*
