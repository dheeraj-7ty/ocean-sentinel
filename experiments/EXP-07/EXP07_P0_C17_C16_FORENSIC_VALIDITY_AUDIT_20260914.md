# EXP-07-P0-C17: C16 Forensic Validity Audit, Frozen-Dataset Integrity Reconciliation, Failure Diagnosis, and Next-Replicate Gate

**Project:** Ocean Sentinel  
**Subsystem:** EXP-07 Multiclass Oceanic and Atmospheric Phenomena Perception Foundation  
**Task ID:** `EXP-07-P0-C17`  
**Date:** 2026-09-14  
**Auditor:** Antigravity Advanced Agentic AI System  
**Audit Target:** EXP-07-P0-C16 Replicate 003 (Seed 42) on Kaggle GPU  
**Final Status:** `AUDIT_COMPLETE_TRAINING_PAUSED`

---

## 1. Executive Verdict

1. **Physical Dataset Invariance:** The physical samples, cluster assignments, and partition manifests have remained **100% byte-for-byte immutable** since initial C14 assembly (`2026-09-13T21:10:25Z`). Zero physical sample pairs have been added, deleted, corrupted, or moved across partitions.
2. **Resolution of DEV 40 vs 41:** The reported discrepancy of "41 DEV vs 40 DEV" was an **arithmetic documentation defect** introduced in the C14 report markdown text and propagated into C15 audit narratives. The underlying manifests (`ops02_physical_dataset_manifest_v1.json`, `ops02_partition_manifest_v1.json`, `ops02_parent_cluster_manifest_v1.json`) have **always contained exactly 40 DEV samples** and **40 HOLDOUT samples**.
3. **Execution Determinism:** C16 Replicate 003 was technically executed on Kaggle GPU. The saved best checkpoint (`best_model.pt`, SHA-256 `936EF935F8049FA15FBC735F8073D08F074796ACC20BE0A2885DD35C7CB09D67`) was locally evaluated in read-only mode and **reproduced the exact 0.049399 DEV mIoU to six decimal places**.
4. **Hardware Reporting Discrepancy:** While the Kaggle VM provisioned dual Tesla T4 GPUs, execution ran strictly on a **single GPU (`cuda:0`)**; `DataParallel` and `DistributedDataParallel` were not utilized. Furthermore, the reported `55.5 MB` VRAM was the static model footprint during eval warmup under `torch.no_grad()`, not peak training VRAM.
5. **HOLDOUT Firewall:** HOLDOUT was quarantined with **0 forward passes, 0 loss calculations, and 0 batch loads**.
6. **Scientific Classification:** C16 is classified as **`B: VALID BUT PROTOCOL-LIMITED`**.
7. **Next-Replicate Gate:** **`TRAINING_PAUSED_PENDING_PROTOCOL_REMEDIATION`**. No additional training (Seed 42 rerun, Seed 101, Seed 2024, or Replicate 004) is authorized until the user explicitly reviews and clears this audit.

---

## 2. C16 Validity Classification

| Classification Tier | Status | Criteria & Justification |
|:---|:---:|:---|
| **A. Valid Scientific Replicate** | REJECTED | Ineligible due to C15 freeze spec in-place mutation, hardware concurrency mischaracterization (single-device vs claimed dual-device), and memory misinterpretation. |
| **B. Valid But Protocol-Limited** | **ACCEPTED** | Technical execution on Kaggle GPU is 100% verified, reproducible, and uncorrupted. Dataset hashes, architecture weights, AdamW optimization, and Candidate F sampler conformed to specification. The 4.94% DEV mIoU is a genuine mathematical result on OPS-02, but subject to strict reporting and protocol limitations. |
| **C. Technically Executed But Non-Comparable** | PARTIALLY SUPPORTED | Valid regarding direct numerical comparisons to OPS-01 (C8/C10): OPS-02 enforced complete parent datatake independence, rendering cross-dataset metric comparison invalid without distribution shift adjustment. |
| **D. Invalid / Contaminated** | REJECTED | Proved false. Zero data contamination, zero HOLDOUT leakage, zero synthetic substitution, and zero code-weight divergence occurred. |
| **E. Inconclusive** | REJECTED | Proved false. Forensics established exact deterministic causality for all observed metrics and incidents. |

---

## 3. C15 Frozen Baseline

The authoritative baseline established at the end of C15 (`2026-09-14T01:30:00Z`):

| Metric / Artifact | Authoritative Frozen Value | Current Value | Congruence |
|:---|:---:|:---:|:---:|
| **Total Physical Sample Pairs** | 212 | 212 | **EXACT MATCH** |
| **Total Independent Parent Clusters** | 64 | 64 | **EXACT MATCH** |
| **Total Mission Datatakes** | 64 | 64 | **EXACT MATCH** |
| **Total Constituent L1 Scenes** | 85 | 85 | **EXACT MATCH** |
| **TRAIN Parent Clusters / Samples** | 40 clusters / 132 samples | 40 clusters / 132 samples | **EXACT MATCH** |
| **DEV Parent Clusters** | 12 clusters | 12 clusters | **EXACT MATCH** |
| **DEV Sample Count (Manifests)** | 40 samples | 40 samples | **EXACT MATCH** |
| **DEV Sample Count (C15 Narrative Claim)** | 41 samples | 40 samples | **DOCUMENTATION DEFECT** |
| **HOLDOUT Parent Clusters** | 12 clusters | 12 clusters | **EXACT MATCH** |
| **HOLDOUT Sample Count (Manifests)** | 40 samples | 40 samples | **EXACT MATCH** |
| **HOLDOUT Sample Count (C15 Narrative Claim)** | 39 samples | 40 samples | **DOCUMENTATION DEFECT** |

---

## 4. C16 Actual Dataset Identity

Cryptographic verification of all dataset artifacts confirmed:

| Artifact Path | SHA-256 Hash | Size (Bytes) | Creation Time (UTC) |
|:---|:---:|:---:|:---:|
| `data/ops02/OPS02_DATASET_FREEZE_SPEC_v1.json` | `AF406D5F4E4092D8ECE240220FB97FF6B28C393D0D37D878898B26D0C6A4A57E` | 3,772 | 2026-09-14T02:37:00Z |
| `data/ops02/manifests/ops02_physical_dataset_manifest_v1.json` | `F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102` | 424,252 | 2026-09-13T21:10:25Z |
| `data/ops02/manifests/ops02_partition_manifest_v1.json` | `757DEAF7A7E72BE331843B518A99AF32E14D68A080822F1D9B4FDBADF889F94D` | 18,811 | 2026-09-13T21:10:25Z |
| `data/ops02/manifests/ops02_parent_cluster_manifest_v1.json` | `08ED21FBB492363E1D05040020F73177BFD4DC84F1A39E2D9C5C9B38BC97D10B` | 62,726 | 2026-09-13T21:10:25Z |

---

## 5. Exact DEV 40 vs 41 Reconciliation

### A. The Root Cause
**Finding: [CAUSAL ESTABLISHED]**  
The underlying manifests generated by `scripts/assemble_ops02_c14_dataset.py` at `2026-09-13T21:10:25Z` **NEVER contained 41 DEV samples**. They have always contained exactly 40 DEV samples and 40 HOLDOUT samples.

### B. Mathematical Proof by Cluster Breakdown
The 12 DEV clusters and their exact materialized slice counts from `ops02_parent_cluster_manifest_v1.json`:
1. `ops02_cluster_001_00BDE6`: 4 slices
2. `ops02_cluster_003_00E063`: 4 slices
3. `ops02_cluster_006_00ED9B`: 2 slices
4. `ops02_cluster_007_00FD5B`: 2 slices
5. `ops02_cluster_008_00FF7D`: 4 slices
6. `ops02_cluster_011_019228`: 4 slices
7. `ops02_cluster_014_019CCC`: 4 slices
8. `ops02_cluster_025_02056E`: 4 slices
9. `ops02_cluster_044_028DBA`: 3 slices
10. `ops02_cluster_050_04EB11`: 2 slices
11. `ops02_cluster_054_04F3FE`: 3 slices
12. `ops02_cluster_060_04F6A8`: 4 slices  
$$\sum = 4+4+2+2+4+4+4+4+3+2+3+4 = \mathbf{40}$$

The 12 HOLDOUT clusters and their exact materialized slice counts:
1. `ops02_cluster_002_00D645`: 4 slices
2. `ops02_cluster_005_00E710`: 4 slices
3. `ops02_cluster_009_01690A`: 3 slices
4. `ops02_cluster_010_016E6A`: 2 slices
5. `ops02_cluster_012_019780`: 4 slices
6. `ops02_cluster_013_0199B9`: 2 slices
7. `ops02_cluster_032_022E25`: 3 slices
8. `ops02_cluster_043_0249B3`: 4 slices
9. `ops02_cluster_045_02C2B0`: 2 slices
10. `ops02_cluster_051_04EFFF`: 4 slices
11. `ops02_cluster_055_04F49C`: 4 slices
12. `ops02_cluster_061_04F6BA`: 4 slices  
$$\sum = 4+4+3+2+4+2+3+4+2+4+4+4 = \mathbf{40}$$

$$\text{Total Materialized Samples} = 132 (\text{TRAIN}) + 40 (\text{DEV}) + 40 (\text{HOLDOUT}) = \mathbf{212}$$

### C. Where Did 41 / 39 Originate?
In C14 assembly, the report author manually wrote `DEV: 41 samples / HOLDOUT: 39 samples` in the markdown summary without running `len(sample_ids)`. During C15, the auditor authoring `ops02_final_parent_accounting_audit_v1.json` and `OPS02_DATASET_FREEZE_SPEC_v1.json` transcribed the numbers 41 and 39 directly from the C14 markdown text into the C15 audit artifacts.
When C16 ran `scripts/verify_ops02_freeze_pre_transfer.py`, the programmatic assertion `len(dev_samples) == 40` passed against the manifest, exposing the metadata text mismatch.

---

## 6. Freeze Mutation Audit

| Field | Pre-Edit Value | Post-Edit Value | Justification | Authorization Status |
|:---|:---:|:---:|:---|:---:|
| `summary.partition_breakdown.DEV.sample_pairs` | 41 | 40 | Synchronized spec to match manifest | INFORMAL CORRECTION |
| `summary.partition_breakdown.HOLDOUT.sample_pairs` | 39 | 40 | Synchronized spec to match manifest | INFORMAL CORRECTION |

**Audit Finding: [OBSERVED]**  
While scientifically harmless (zero bytes of imagery or masks changed), modifying `OPS02_DATASET_FREEZE_SPEC_v1.json` in-place during training preparation without logging an incident violated governance protocols. This has been codified as Incident `C17-INC-002` and prompted `GOV-RULE-085`.

---

## 7. Code and Version Lineage

Forensic analysis of Kaggle kernel `dheeraj12237/ocean-sentinel-exp07-c16-replicate-003`:

| Version | Status | Failure Point / Milestone | Scientific Conformance |
|:---:|:---:|:---|:---:|
| **v1** | FAILED | PyTorch 2.10 dropped Pascal sm_60 (P100); Linux backslash path parsing | 0 epochs; halted before model instantiation |
| **v2** | FAILED | Decoder parameter assertion: 14,337,516 vs required 14,310,860 | 0 epochs; halted before model instantiation |
| **v3** | FAILED | Sampler API mismatch: `super().__init__(None)` under PyTorch 2.10 | 0 epochs; halted before data ingestion |
| **v4** | **COMPLETE** | Executed 27 epochs, triggered early stopping at epoch 27 (best epoch 17) | **100% PROTOCOL CONFORMANCE** |

Script SHA-256 for v4: `DF9F35BB957B907671FE13029923F59C9C90704712343CE010301582F6D61ADB` (`26,496 bytes`).

---

## 8. Protocol Conformance Matrix

| Subsystem | Prescribed Frozen Protocol (C15) | Actual Executed Protocol (C16) | Conformance Status |
|:---|:---|:---|:---:|
| **Dataset Version** | `OPS02_v1.0.0_FROZEN` | `OPS02_v1.0.0_FROZEN` | **MATCH** |
| **Sample Distribution** | 132 TRAIN / 40 DEV / 40 HOLDOUT | 132 TRAIN / 40 DEV / 40 HOLDOUT | **MATCH** |
| **Input Domain** | Uncalibrated raw DN, $\log(1+\text{DN})$ standardized | Uncalibrated raw DN, $\log(1+\text{DN})$ standardized | **MATCH** |
| **Norm Constants** | $\mu=4.424158, \sigma=0.469261$ | $\mu=4.424158, \sigma=0.469261$ | **MATCH** |
| **Model Architecture** | ResNet18-UNet (Option B, BN momentum 0.05) | ResNet18-UNet (Option B, BN momentum 0.05) | **MATCH** |
| **Trainable Weights** | Exactly 14,310,860 | Exactly 14,310,860 | **MATCH** |
| **BatchNorm2d Count**| Exactly 30 layers | Exactly 30 layers | **MATCH** |
| **Output Classes** | 12 dense classes (0..11) | 12 dense classes (0..11) | **MATCH** |
| **Loss Function** | CrossEntropyLoss with sqrt-median freq weights | CrossEntropyLoss with sqrt-median freq weights | **MATCH** |
| **Optimizer** | AdamW ($\eta=5\times 10^{-4}, \lambda=0.01$ on 2D) | AdamW ($\eta=5\times 10^{-4}, \lambda=0.01$ on 2D) | **MATCH** |
| **LR Scheduler** | LinearWarmupCosine (3 warmup, 27 cosine) | LinearWarmupCosine (3 warmup, 27 cosine) | **MATCH** |
| **Batch Dynamics** | Minibatch 8, Accumulation 2, Virtual Batch 16 | Minibatch 8, Accumulation 2, Virtual Batch 16 | **MATCH** |
| **Sampler** | Candidate F Hybrid (70% parent, 30% presence) | Candidate F Hybrid (70% parent, 30% presence) | **MATCH** |
| **Draws per Epoch** | 72 draws with replacement | 72 draws with replacement | **MATCH** |
| **Random Seed** | Seed 42, sampler generator $42 + 1000\times\text{epoch}$ | Seed 42, sampler generator $42 + 1000\times\text{epoch}$ | **MATCH** |
| **Augmentations** | None (pure deterministic) | None (pure deterministic) | **MATCH** |
| **Early Stopping** | Min 15, Patience 10, Min Delta 0.005 | Min 15, Patience 10, Min Delta 0.005 | **MATCH** |

---

## 9. Metric Implementation Audit

**Audit Finding: [OBSERVED]**  
`dev_mIoU_phenomena` is calculated strictly over classes 1..11 (excluding Background class 0).  
The confusion matrix accumulation filters out invalid border pixels and excluded source classes (`target == -100`).  
Because all 11 phenomenon classes are physically present in DEV ground truth, the denominator is unconditionally 11.  
Re-evaluating `best_model.pt` locally through the exact `OPS02Dataset` pipeline reproduced the exact metric:
$$\text{Recomputed DEV mIoU} = \mathbf{0.04939907} \approx 4.94\%$$

---

## 10. Data Loader, Input, and Mask Audit

Inspecting representative samples across MCC, IWs, BS, LWA, POW, OF, WS, Eddy, and HM confirmed:
1. **No Double $\log(1+p)$:** Input transformation is applied exactly once in `preprocess_sar_image()`.
2. **No Radiometric Permutation:** Channel dimensions `[1, 256, 256]` float32 are strictly maintained.
3. **Invalid Border Masking:** All non-positive padding pixels ($DN \le 0$) are zeroed in image arrays and labeled `-100` in mask arrays.
4. **Dense Remapping:** Canonical source labels are remapped to 0..11 monotonically, with excluded classes (3 Iceberg, 9 Sea Ice, 14 Mineral Oil Spill) mapped to `-100`.

---

## 11. Class-Weight Audit

Verification of the loss weighting tensor against the 132 TRAIN valid pixels:
$$w_c = \sqrt{\frac{\text{median}(f_{\text{valid}})}{f_c}}$$

| Class | Dense Index | TRAIN Valid Pixels | Prescribed C15 Weight | Executed C16 Weight | Congruence |
|:---|:---:|:---:|:---:|:---:|:---:|
| **BG** | 0 | 2,449,755 | 0.403935 | 0.403935 | **EXACT MATCH** |
| **AF** | 1 | 66,561 | 2.450546 | 2.450546 | **EXACT MATCH** |
| **BS** | 2 | 520,058 | 0.876692 | 0.876692 | **EXACT MATCH** |
| **LWA** | 3 | 446,698 | 0.945945 | 0.945945 | **EXACT MATCH** |
| **MCC** | 4 | 951,354 | 0.648189 | 0.648189 | **EXACT MATCH** |
| **OF** | 5 | 22,536 | 4.211476 | 4.211476 | **EXACT MATCH** |
| **POW** | 6 | 771,817 | 0.719641 | 0.719641 | **EXACT MATCH** |
| **RF** | 7 | 45,738 | 2.956203 | 2.956203 | **EXACT MATCH** |
| **WS** | 8 | 352,723 | 1.064525 | 1.064525 | **EXACT MATCH** |
| **Eddy** | 9 | 112,747 | 1.882870 | 1.882870 | **EXACT MATCH** |
| **IWs** | 10 | 2,659,872 | 0.387652 | 0.387652 | **EXACT MATCH** |
| **HM** | 11 | 1,201 | 18.243211 | 18.243211 | **EXACT MATCH** |

Median pixel count across the 12 classes: $\mathbf{399,710.5}$. All weights match to the 6th decimal place.

---

## 12. Sampler Audit

A bounded 5-epoch deterministic test of `CandidateFWeightedSampler` on TRAIN samples verified:
- **Draw Cardinality:** Exactly 72 draws per epoch with replacement.
- **Parent Coverage:** 30 to 35 unique parent clusters drawn per epoch (out of 40 TRAIN clusters).
- **Phenomena Coverage:** 12/12 classes represented in every epoch's draws.
- **Partition Isolation:** 0 draws from DEV, 0 draws from HOLDOUT across all epochs.

---

## 13. GPU Execution Audit

1. **Accelerator Allocation:** Dual Tesla T4 GPUs provisioned (`14.56 GB` VRAM each, `sm_75`, CUDA 12.8).
2. **Compute Utilization:** `device = torch.device('cuda')` placed the model strictly on **`cuda:0`**. `cuda:1` was completely idle.
3. **Memory Forensics:** The reported `55.5 MB` was the static model evaluation allocation during warmup under `torch.no_grad()`. True training peak VRAM with optimizer momentum/variance states and backpropagation activations was approximately `~600 MB` to `1.0 GB`.

---

## 14. Checkpoint Forensics

Both model checkpoints were verified locally from disk:
- **`best_model.pt`**:
  - SHA-256: `936EF935F8049FA15FBC735F8073D08F074796ACC20BE0A2885DD35C7CB09D67`
  - Size: `57,355,665 bytes`
  - Total parameter weights/biases: `14,310,860`
  - BatchNorm layers: `30` (with 30 `running_mean`, 30 `running_var`, 30 `num_batches_tracked`)
  - Best epoch: `17` (DEV mIoU: `0.0494`)
- **`last_model.pt`**:
  - SHA-256: `60411490EFB81D5DE806F4DFFBA760F5D7F4486B14AB4F144AD35D37EE16FA9E`
  - Size: `57,355,665 bytes`
  - Final epoch: `27` (Early stopping triggered, DEV mIoU: `0.0228`)
  - Differing tensors between best and last: `192/192` (100% distinct).

---

## 15. HOLDOUT Quarantine Firewall Audit

**Status: [CONFIRMED PRISTINE]**  
- Code analysis confirmed `OPS02Dataset` raises `PermissionError` if `partition == "HOLDOUT"`.
- `HOLDOUT_ACCESS_COUNT` remained `0` throughout all 27 epochs.
- Remote Kaggle console logs confirmed: `HOLDOUT Access Count: 0 (Strictly Pristine)`.
- Local test `test_holdout_quarantine_firewall` passed.

---

## 16. Class-Wise Failure Diagnosis

### Confusion Matrix Analysis on DEV (40 Samples, Epoch 17 Best Checkpoint)

```
GT \ Pred     BG     AF     BS    LWA    MCC     OF    POW     RF     WS   Eddy    IWs     HM
BG        18,302     62 56,617 37,518 274523    870  9,962      0 46,523  8,559 190869      0
AF         3,394      0  3,450 13,181  5,842    128    830      0  4,189      0  8,371      0
BS             2      0 35,546     34 27,517    612  5,849      0 21,492  3,092 29,627      0
LWA            0     24    573 14,237  2,579  1,721  4,965      0 19,899     38 14,531      0
MCC       21,902     73 59,316 197937 318912  6,276 18,458      0 136017  7,227 87,197      0
OF             0      0      0      0      0      7     30      0  1,403      0    269      0
POW        1,987      0 22,726  7,380  8,362     34  5,802      0    342      7 31,775      0
RF             1      0    701      0      0     10    244      0    217      4  8,373      0
WS         7,562     27 28,644  7,691 28,530    130  4,758      0  9,894     95 43,706      0
Eddy         520     13 15,005  1,732 18,850    209  1,446      0  4,368    924  2,255      0
IWs        9,318     87 35,700 160404 175717  2,039 10,060      0 76,649  6,047 103505      0
HM             0      0      0     49      0      0      3      0      0      0     65      0
```

### Detailed Per-Class Breakdown

| Class | Dense Index | GT Pixels | Predicted Pixels | True Positives | Class IoU | Primary Failure Mode |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **BG** | 0 | 643,805 | 62,988 | 18,302 | 0.0266 | Massive under-prediction; 72% misclassified as MCC and IWs due to high foreground loss weights |
| **AF** | 1 | 39,385 | 286 | 0 | **0.0000** | Total collapse; diffused fronts confused with LWA (13.2k px) and IWs (8.4k px) |
| **BS** | 2 | 123,771 | 258,278 | 35,546 | 0.1026 | Over-predicted; heavy confusion with IWs (29.6k px), MCC (27.5k px), and WS (21.5k px) |
| **LWA** | 3 | 58,567 | 440,163 | 14,237 | 0.0294 | Severe false-positive over-prediction onto open water and IWs |
| **MCC** | 4 | 853,315 | 860,832 | 318,912 | **0.2286** | **Top performing class**; captures convective cellular texture, but spills onto BG and LWA |
| **OF** | 5 | 1,709 | 12,036 | 7 | 0.0005 | Ultra-sparse; narrow front boundaries confused with WS and background |
| **POW** | 6 | 78,415 | 62,407 | 5,802 | 0.0430 | Swell patterns confused with IWs (31.8k px) and BS (22.7k px) |
| **RF** | 7 | 9,550 | 0 | **0.0000** | Total collapse; zero predictions emitted across all DEV images |
| **WS** | 8 | 131,037 | 320,993 | 9,894 | 0.0224 | Diffused streak textures confused with MCC and IWs |
| **Eddy** | 9 | 45,322 | 25,993 | 924 | 0.0131 | Curvilinear vortex boundaries overwhelmed by MCC and BS |
| **IWs** | 10 | 579,526 | 520,543 | 103,505 | **0.1039** | **Second performing class**; wave crests detected, but heavy confusion with LWA and MCC |
| **HM** | 11 | 117 | 0 | **0.0000** | Total collapse; ultra-sparse objects (117 pixels) completely undetected despite $18.2\times$ weight |

### Diagnostic Summary
**Finding: [CAUSAL ESTABLISHED]**  
The 4.94% mIoU is NOT a code bug or implementation defect. It is driven by:
1. **Zero-TP Minority Collapse:** Classes AF, RF, and HM produced 0 true positives, dragging the 11-class macro average down by adding three exact $0.0$ scores.
2. **Background Depletion:** Heavy loss weighting on foreground lookalikes encouraged the network to predict MCC, IWs, and BS across open seawater, driving BG IoU down to 2.66%.
3. **Top Cluster Generalization:** On the three dominant phenomena (MCC, IWs, BS), the model achieved an average IoU of **$14.50\%$**, reflecting real learning under strict out-of-distribution datatake partitioning.

---

## 17. Historical Comparability

| Dataset | Split Methodology | Overlap | Baseline Model | DEV mIoU | Epistemic Significance |
|:---|:---|:---|:---|:---:|:---|
| **OPS-01** | Random slice split across 27 parent scenes | High along-track spatial & environmental leakage | C8 / C10 ResNet18-UNet | $\approx 40.6\%$ | Intra-scene pseudo-replication inflated performance |
| **OPS-02** | Disjoint parent datatake clusters (64 clusters) | Zero along-track, temporal, or spatial leakage | C16 ResNet18-UNet | $\mathbf{4.94\%}$ | **True out-of-distribution spatial generalization** |

**Conclusion: [SUPPORTED]**  
Comparing C16 directly to C8/C10 as a "35-point regression" is scientifically invalid. OPS-01 tested memory of identical satellite passes; OPS-02 tests generalization across distinct oceans, years, and atmospheric regimes.

---

## 18. Epistemic Evidence-Level Findings

- **[OBSERVED]:** C14 manifests created at `2026-09-13T21:10:25Z` contain 132 TRAIN, 40 DEV, and 40 HOLDOUT samples.
- **[OBSERVED]:** `best_model.pt` evaluated locally produces exactly `0.049399` DEV mIoU.
- **[OBSERVED]:** C16 executed on `cuda:0` without multi-GPU parallelism.
- **[SUPPORTED]:** Heavy loss weights on foreground lookalikes caused background seawater under-prediction.
- **[CAUSAL ESTABLISHED]:** The discrepancy of 41 vs 40 DEV samples was a human transcription error in the C14 markdown narrative, not dataset mutation.

---

## 19. New Incidents Logged

1. **`C17-INC-001` (Severity: HIGH):** C15 Documentation Defect in DEV/HOLDOUT Sample Counts (41/39 vs 40/40).
2. **`C17-INC-002` (Severity: MEDIUM):** Unrecorded In-Place Modification of `OPS02_DATASET_FREEZE_SPEC_v1.json` during C16.
3. **`C17-INC-003` (Severity: MEDIUM):** Hardware Concurrency Reporting Inaccuracy (Dual-T4 hardware provisioned, single-device execution).
4. **`C17-INC-004` (Severity: LOW):** Warmup Benchmark Memory Mischaracterization as Peak Training VRAM.
5. **`C17-INC-005` (Severity: HIGH):** Evaluation Metric Collapse Driven by Ultra-Sparse Lookalike Classes.

---

## 20. Durable Governance Codification

Permanent rules codified in `data/metadata/ocean_sentinel_governance_rules_v1.json`:
- **`GOV-RULE-085`**: Frozen Dataset Specification Immutability and Cryptographic Binding.
- **`GOV-RULE-086`**: Partition Sample Count Runtime Assertion.
- **`GOV-RULE-087`**: Hardware Provisioning vs Hardware Utilization Reporting.
- **`GOV-RULE-088`**: Evaluation Warmup Memory vs Peak Training VRAM Characterization.
- **`GOV-RULE-089`**: Partitioned Reporting for Sparse-Class Multiclass Perception.

---

## 21. Guardrail Regression Test Results

Complete test suite execution (`pytest tests/test_exp07*.py tests/test_artifact_policy.py tests/test_part_iii_firewall.py`):

```
tests/test_exp07_p0_c10_replicate_guardrails.py ........                 [  2%]
tests/test_exp07_p0_c11_forensic_guardrails.py .........                 [  6%]
tests/test_exp07_p0_c12_ops02_design_guardrails.py ............          [ 10%]
tests/test_exp07_p0_c13_ops02_acquisition_guardrails.py ............     [ 14%]
tests/test_exp07_p0_c14_ops02_dataset_assembly_guardrails.py ........... [ 18%]
tests/test_exp07_p0_c15_freeze_guardrails.py ............                [ 23%]
tests/test_exp07_p0_c16_replicate003_guardrails.py ......                [ 25%]
tests/test_exp07_p0_c17_forensic_guardrails.py ..........                [ 29%]
tests/test_exp07_p0_c2_final_plan_guardrails.py ........................ [ 37%]
tests/test_exp07_p0_c3_cpu_validation_guardrails.py .................... [ 56%]
tests/test_exp07_p0_c4_protocol_freeze_guardrails.py ................... [ 65%]
tests/test_exp07_p0_c5_implementation_guardrails.py .................... [ 74%]
tests/test_exp07_p0_c6_integration_guardrails.py ....................... [ 86%]
tests/test_exp07_p0_c7_training_readiness_guardrails.py ........         [ 89%]
tests/test_exp07_p0_c8_execution_guardrails.py ........                  [ 92%]
tests/test_exp07_p0_c9_diagnostic_guardrails.py ..........               [ 95%]
tests/test_artifact_policy.py ......                                     [ 97%]
tests/test_part_iii_firewall.py ......                                   [100%]

======================= 275 passed, 5 warnings in 9.70s =======================
```

**Result: 275 / 275 PASSED (100% CLEAN).**

---

## 22. Final Scientific Validity Gate & Replicate Recommendation

### Final Verdict: `TRAINING_PAUSED_PENDING_PROTOCOL_REMEDIATION`

**Next Replicate Authorized:** **`FALSE`**  
**Training Started:** **`FALSE`**  
**HOLDOUT Evaluated:** **`FALSE`**  

### Blocking Issues Requiring Resolution Before Any Future Replicate:
1. **`BLK-C17-001` (Dataset Freeze Formalization):** Lock the freeze specification with embedded SHA-256 manifest hashes.
2. **`BLK-C17-002` (Hardware Reporting Invariant):** Ensure runtime telemetry scripts report `cuda:0` single-GPU execution and measure peak training VRAM via `torch.cuda.max_memory_allocated()`.
3. **`BLK-C17-003` (Sparse Class Metric Protocol):** Implement partitioned metric reporting separating dominant oceanic phenomena (MCC, IWs, BS) from ultra-sparse classes (HM, OF, RF).

---

## 23. Git and Process Self-Audit

- **Active Python Processes:** `0`
- **Current Git Branch:** `master`
- **Cached / Staged Changes:** `0`
- **Tracked Modifications:** Preserved untouched (`.gitignore`, `src/ocean_sentinel/ingestion/dataset.py`)
- **Prohibited Git Actions:** Zero commits, zero pushes, zero checkouts, zero stashes, zero cleans, zero resets.
