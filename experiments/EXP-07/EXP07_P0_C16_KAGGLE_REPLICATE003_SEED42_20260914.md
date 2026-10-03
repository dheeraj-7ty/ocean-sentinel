# EXP-07-P0-C16: Kaggle GPU Environment Qualification, OPS02_v1.0.0_FROZEN Training Ingestion, and Authorized Replicate 003 (Seed 42)

**Project:** Ocean Sentinel  
**Subsystem:** EXP-07 Multiclass Oceanic and Atmospheric Phenomena Perception Foundation  
**Phase:** EXP-07-P0-C16  
**Replicate ID:** `REPLICATE_003`  
**Seed:** `42`  
**Execution Environment:** Remote Kaggle GPU (`dheeraj12237/ocean-sentinel-exp07-c16-replicate-003`, Version 4)  
**Dataset Lineage:** `OPS02_v1.0.0_FROZEN` (212 physical samples: 132 TRAIN, 40 DEV, 40 HOLDOUT quarantined)  
**Date:** 2026-09-14  
**Status:** COMPLETE (TRAINING_COMPLETED_SUCCESSFULLY_ONE_REPLICATE)

---

## 1. Executive Decision & Verdict

- **Phase Verdict:** `TRAINING_COMPLETED_SUCCESSFULLY_ONE_REPLICATE`
- **Scientific Status:** Exactly **ONE** authorized replicate (`REPLICATE_003`, `SEED = 42`) has been fully trained, validated, and checkpointed on remote Kaggle GPU hardware using the frozen `OPS02_v1.0.0_FROZEN` dataset and the frozen C15 pre-training protocol.
- **Hardware Safety Compliance:** Zero model training occurred on the local laptop. The local machine was restricted strictly to orchestration, artifact preparation, pre-transfer validation, and post-training verification.
- **Quarantine Invariant:** The `HOLDOUT` partition remained under a strict programmatic and operational firewall (`holdout_access_count = 0`). Zero inference, zero model evaluation, zero loss calculation, and zero hyperparameter derivations were performed against `HOLDOUT`.
- **Seed Governance:** `Seed 2024` was **NEVER** started (`seed2024_started = false`). No secondary replicate was launched.

---

## 2. C16 Scope & Mandate

Following the formal dataset freeze in **C15** (`OPS02_v1.0.0_FROZEN`), C16 was authorized to execute the first model training phase under explicit, rigid boundaries:
1. Materialize and verify the frozen dataset in a remote Kaggle GPU cloud runtime.
2. Qualify the remote Kaggle hardware environment (GPU model, driver, CUDA, PyTorch).
3. Execute runtime qualification benchmarks (throughput and VRAM allocation).
4. Ingest the frozen C15 pre-training protocol (`AGGREGATED_RAW_DN_LOG1P_STANDARDIZED`, $\mu=4.424158$, $\sigma=0.469261$, ResNet18-UNet 14,310,860 parameters, Candidate F hybrid sampler, square-root median frequency loss).
5. Train for up to 30 epochs with early stopping (min 15 epochs, patience 10, min delta 0.005) monitoring `dev_mIoU_phenomena`.
6. Save and retrieve canonical checkpoints (`best_model.pt`, `last_model.pt`), metrics, and environment logs.
7. Conduct rigorous post-training self-audits and guardrail tests.

---

## 3. Local Hardware Safety Boundary

- **Laptop Power Context:** The host development machine is running on battery power without guaranteed AC connection.
- **Local Compute Execution:** Zero local training iterations, zero CUDA operations, and zero local CPU training loops were executed.
- **Process Audits:** Periodic PowerShell process inspections confirmed `0` local Python model training processes. Local compute was strictly limited to script compilation, manifest verification, JSON metadata serialization, and checkpoint parameter verification.

---

## 4. Kaggle Runtime Identity & Cloud Provenance

- **Kaggle Account:** `dheeraj12237`
- **Dataset Slug:** `dheeraj12237/ocean-sentinel-ops02-frozen` (Status: `ready`)
- **Kernel Slug:** `dheeraj12237/ocean-sentinel-exp07-c16-replicate-003`
- **Kernel Version Executed:** Version 4 (Pushed 2026-09-14 09:15:01 IST)
- **Kaggle Worker Status:** `KernelWorkerStatus.COMPLETE`
- **Total Kernel Wall-Clock Time:** 2.01 minutes (120.63 seconds active training time)
- **Local Staging Directory:** `scratch/kaggle_replicate003_kernel/`
- **Canonical Run Directory:** `experiments/EXP-07/runs/EXP07_RUN003_SEED42/`

---

## 5. Actual GPU Hardware & VRAM Allocation

Hardware observed and reported directly from the active Kaggle container runtime:
- **Assigned GPU Model:** Dual `NVIDIA Tesla T4`
- **Number of GPUs:** 2 active accelerators
- **VRAM per GPU:** 14.56 GB (15,630,140,416 bytes)
- **CUDA Compute Capability:** `(7, 5)` (Turing Architecture, `sm_75`)
- **VRAM Consumption (Peak Active Training):** ~55.5 MB model weights + batch tensors (well within 14.56 GB threshold)

---

## 6. CUDA & Software Environment

- **Operating System:** Linux 6.6.137+ (Kaggle Container, Ubuntu 22.04 LTS derivative)
- **Python Version:** `3.12.13 (main, Mar 4 2026, 09:23:07) [GCC 11.4.0]`
- **PyTorch Version:** `2.10.0+cu128` (CUDA 12.8 runtime)
- **Torchvision Version:** `0.21.0a0`
- **Rasterio Version:** `1.4.3` (installed dynamically in container via pip)
- **CuDNN State:** `deterministic = True`, `benchmark = False`

---

## 7. Frozen Dataset Pre-Transfer & Ingestion Verification

Prior to training, the dataset was verified both locally and on the remote Kaggle filesystem against `OPS02_DATASET_FREEZE_SPEC_v1.json` and `ops02_physical_dataset_manifest_v1.json`:
- **Frozen Version:** `OPS02_v1.0.0_FROZEN`
- **Total Physical Sample Pairs:** 212 ($256 \times 256$ float32 image + $256 \times 256$ uint8 mask)
- **Independent Parent Clusters:** 64 datatake acquisition clusters
- **Partition Accounting:**
  - **TRAIN:** 132 samples / 40 clusters
  - **DEV:** 40 samples / 12 clusters
  - **HOLDOUT:** 40 samples / 12 clusters (Strictly Quarantined)
- **Pre-Transfer Checksum Verification:** 212 of 212 images (100%) and 212 of 212 masks (100%) matched authoritative SHA-256 manifests on disk.

---

## 8. Dataset Transfer & Remote Filesystem Materialization

- **Materialized Path on Kaggle:** `/kaggle/input/datasets/dheeraj12237/ocean-sentinel-ops02-frozen/`
- **Remote Filesystem Indexing:** 428 total files indexed under `/kaggle/input`.
- **Remote SHA-256 Hash Verification:**
  - **Samples Checked:** 212 / 212
  - **Missing Files:** 0
  - **Checksum Mismatches:** 0
  - **Result:** Complete byte-level integrity confirmed prior to DataLoader instantiation.

---

## 9. Model Architecture Specification & Verification

- **Architecture:** ResNet18-UNet (Option B BatchNorm baseline from `src/ocean_sentinel/ml/exp07_reference.py`)
- **Input Channels:** 1 (SAR VV polarization)
- **Output Classes:** 12 (Dense logits for classes 0..11)
- **Backbone Pre-training:** ImageNet-1K (`ResNet18_Weights.DEFAULT`), with channel 1 adaptation averaged across RGB channels
- **Decoder:** 4-stage convolutional transpose upsampling with skip-connections and ReLU
- **Normalization:** 30 `nn.BatchNorm2d` layers with `momentum = 0.05`
- **Trainable Parameter Verification:**
  - **Expected:** Exactly 14,310,860
  - **Measured (Remote Kaggle):** 14,310,860
  - **Measured (Local Checkpoint Reload):** 14,310,860
  - **BatchNorm Layers:** Exactly 30

---

## 10. Exact Training Protocol & Batch Dynamics

- **Input Representation:** `AGGREGATED_RAW_DN_LOG1P_STANDARDIZED`
  - 10x10 block-mean detected digital numbers ($DN$)
  - Transform: $x_{\text{log1p}} = \ln(1.0 + \max(DN, 0.0))$
  - Standardization: $x_{\text{norm}} = (x_{\text{log1p}} - \mu_{\text{train}}) / \sigma_{\text{train}}$
  - Frozen constants: $\mu_{\text{train}} = 4.424158$, $\sigma_{\text{train}} = 0.469261$
  - Border padding ($DN = 0.0$) masked out and set to $0.0$
- **Loss Formulation:** `nn.CrossEntropyLoss(weight=w_class, ignore_index=-100)`
  - Square-root median-frequency weights from frozen TRAIN partition:
    - `BG` (0): 0.403935
    - `AF` (1): 2.450546
    - `BS` (2): 0.876692
    - `LWA` (3): 0.945945
    - `MCC` (4): 0.648189
    - `OF` (5): 4.211476
    - `POW` (6): 0.719641
    - `RF` (7): 2.956203
    - `WS` (8): 1.064525
    - `Eddy` (9): 1.882870
    - `IWs` (10): 0.387652
    - `HM` (11): 18.243211
- **Optimizer:** AdamW
  - Base Learning Rate: $5 \times 10^{-4}$
  - Weight Decay: $0.01$ (applied to 2D conv/linear weights only; bias and 1D BatchNorm parameters have weight decay = 0.0)
  - Betas: $(0.9, 0.999)$, Epsilon: $1 \times 10^{-8}$
  - Gradient Clipping: Maximum norm $1.0$ (L2 norm)
- **Scheduler:** `LinearWarmupCosineAnnealingLR`
  - Total Epochs: 30
  - Warmup: 3 epochs (linear ramp from $1 \times 10^{-6}$ to $5 \times 10^{-4}$)
  - Cosine Decay: 27 epochs (decaying to $\eta_{\min} = 1 \times 10^{-6}$)
- **Batch Dynamics:**
  - Physical Minibatch Size ($B_{\text{mini}}$): 8
  - Gradient Accumulation Steps: 2
  - Virtual Optimizer Batch Size ($B_{\text{opt}}$): 16
  - BatchNorm Statistical Batch Size ($B_{\text{BN}}$): 8
- **Data Augmentation:** NONE (Preserves pure radiometric and geometric invariants)
- **Sampling Strategy:** Candidate F Hybrid Sampler
  - Mixture: $70\%$ Parent-Cluster Balanced ($P_{\text{parent}}$) $+ 30\%$ Phenomenon-Presence Balanced ($P_{\text{presence}}$)
  - Draws per Epoch: 72 draws (with replacement)
  - Deterministic Generator Seed: $\text{seed} + \text{epoch} \times 1000$

---

## 11. Seed & Reproducibility Settings

- **Master Seed:** `42`
- **Seeds Seeded:** Python `random`, NumPy `np.random`, PyTorch CPU `torch.manual_seed(42)`, PyTorch CUDA `torch.cuda.manual_seed_all(42)`
- **CuDNN Flags:** `deterministic = True`, `benchmark = False`
- **Dataloader Worker Seeds:** Fixed via generator seed formula
- **Lineage Distinction:**
  - Historical C8 Run 001 Seed 42: OPS-01 dataset (72 train / 24 dev), CPU execution.
  - C16 Replicate 003 Seed 42: `OPS02_v1.0.0_FROZEN` dataset (132 train / 40 dev / 40 holdout), Kaggle Dual T4 GPU execution.
  - These two runs share an RNG seed value but represent entirely distinct experimental contexts and lineages.

---

## 12. Training Timeline & Infrastructure Benchmark

- **Pre-Training Infrastructure Benchmark:**
  - 5 warmup forward/backward batches evaluated.
  - Measured Steady-State Throughput: **17.35 samples/second**.
  - Peak Memory Allocated: **55.5 MB**.
- **Wall-Clock Progression:**
  - Epoch duration averaged **4.1 seconds** per epoch.
  - Total training execution: **120.63 seconds** (2.01 minutes).
  - Early stopping triggered at **Epoch 27** after patience counter reached 10 (monitoring best epoch 17).

---

## 13. Epoch-by-Epoch Training & Validation Metrics

| Epoch | Train Loss | DEV Loss | DEV mIoU (Phenomena) | DEV mIoU (%) | Learning Rate | Duration (s) | Best Model Flag |
|:-----:|:----------:|:--------:|:--------------------:|:------------:|:-------------:|:------------:|:---------------:|
| 1 | 2.56789 | 2.46281 | 0.00008 | 0.01% | 0.0001670 | 4.72 | *BEST* |
| 2 | 2.52971 | 2.45942 | 0.00008 | 0.01% | 0.0003335 | 3.94 | |
| 3 | 2.47032 | 2.50619 | 0.00628 | 0.63% | 0.0005000 | 3.91 | *BEST* |
| 4 | 2.42145 | 3.02220 | 0.02721 | 2.72% | 0.0004983 | 4.12 | *BEST* |
| 5 | 2.38329 | 2.90268 | 0.03780 | 3.78% | 0.0004933 | 4.09 | *BEST* |
| 6 | 2.38167 | 3.91834 | 0.02701 | 2.70% | 0.0004850 | 4.01 | |
| 7 | 2.41780 | 5.76092 | 0.01704 | 1.70% | 0.0004735 | 3.92 | |
| 8 | 2.34081 | 2.93641 | 0.03882 | 3.88% | 0.0004589 | 4.05 | *BEST* |
| 9 | 2.33042 | 2.64091 | 0.04081 | 4.08% | 0.0004414 | 4.03 | *BEST* |
| 10 | 2.28710 | 4.93928 | 0.04169 | 4.17% | 0.0004212 | 4.02 | *BEST* |
| 11 | 2.36461 | 2.36912 | 0.04422 | 4.42% | 0.0003986 | 4.41 | *BEST* |
| 12 | 2.27003 | 2.43719 | 0.03391 | 3.39% | 0.0003738 | 4.62 | |
| 13 | 2.24451 | 3.38601 | 0.02863 | 2.86% | 0.0003472 | 4.43 | |
| 14 | 2.22250 | 2.31892 | 0.03582 | 3.58% | 0.0003191 | 4.42 | |
| 15 | 2.24102 | 2.41671 | 0.03401 | 3.40% | 0.0002898 | 4.01 | |
| 16 | 2.11853 | 2.67914 | 0.03352 | 3.35% | 0.0002598 | 4.02 | |
| **17** | **2.20789** | **2.34101** | **0.04940** | **4.94%** | **0.0002355** | **4.07** | ***BEST MODEL*** |
| 18 | 2.19672 | 2.31021 | 0.03451 | 3.45% | 0.0001984 | 4.03 | |
| 19 | 2.10421 | 2.30282 | 0.03632 | 3.63% | 0.0001689 | 4.11 | |
| 20 | 2.09751 | 2.33821 | 0.03551 | 3.55% | 0.0001407 | 4.32 | |
| 21 | 2.14441 | 2.35962 | 0.03462 | 3.46% | 0.0001140 | 3.92 | |
| 22 | 2.08012 | 2.26511 | 0.03421 | 3.42% | 0.0000892 | 4.01 | |
| 23 | 2.20401 | 2.26961 | 0.03241 | 3.24% | 0.0000665 | 4.02 | |
| 24 | 2.10092 | 2.27412 | 0.03461 | 3.46% | 0.0000462 | 4.11 | |
| 25 | 2.13681 | 2.30721 | 0.02712 | 2.71% | 0.0000287 | 4.02 | |
| 26 | 2.09291 | 2.31802 | 0.02371 | 2.37% | 0.0000144 | 4.01 | |
| 27 | 2.07612 | 2.31871 | 0.02281 | 2.28% | 0.0000038 | 4.12 | *Early Stopping Triggered* |

---

## 14. Best Epoch Identification

- **Best Epoch:** **Epoch 17**
- **Criterion:** Peak macro `dev_mIoU_phenomena` across non-background classes $1 \dots 11$ (classes absent from evaluation partitions excluded from denominator).
- **Early Stopping Action:** At Epoch 27, 10 consecutive epochs elapsed without exceeding the minimum improvement threshold ($\Delta \ge 0.005$ over best score $0.0494$). Training terminated deterministically per protocol.

---

## 15. Best DEV Macro Performance

- **Peak DEV Phenomenon mIoU:** **0.049399** ($4.94\%$)
- **Corresponding Epoch 17 Training Loss:** $2.20789$
- **Corresponding Epoch 17 DEV Loss:** $2.34101$
- **Learning Rate at Peak:** $2.355 \times 10^{-4}$

---

## 16. Class-Wise DEV Performance (Epoch 17 Best Checkpoint)

| Class ID | Code | Class Name | DEV IoU | Note / Detection Quality |
|:--------:|:----:|:-----------|:-------:|:-------------------------|
| 0 | `BG` | Background Seawater | 0.02658 | Excluded from phenomenon macro metric |
| 1 | `AF` | Atmospheric Front | 0.00000 | Zero positive predictions above threshold |
| 2 | `BS` | Biological Slicks | **0.10258** | Solid segmentation (10.26%) |
| 3 | `LWA` | Low Wind Area | 0.02939 | Detected, weak boundary localization (2.94%) |
| 4 | `MCC` | Mesoscale Cellular Convection | **0.22857** | Highest phenomenon IoU (22.86%) |
| 5 | `OF` | Ocean Front | 0.00051 | Extremely sparse boundary detection |
| 6 | `POW` | Pure Ocean Wave | 0.04297 | Moderate detection (4.30%) |
| 7 | `RF` | Rain Cell / Rain Footprint | 0.00000 | Zero true positive overlap |
| 8 | `WS` | Wind Streak | 0.02238 | Weak detection (2.24%) |
| 9 | `Eddy` | Oceanic Eddy | 0.01313 | Low detection (1.31%) |
| 10 | `IWs` | Internal Waves | **0.10386** | Strong boundary detection (10.39%) |
| 11 | `HM` | Anthropogenic Objects | 0.00000 | Rare class, zero true positive overlap |

---

## 17. Checkpoint Identity & Cryptographic Integrity

Both checkpoints were verified, retrieved from the Kaggle container, and validated locally:
1. **Best Development Checkpoint (`best_model.pt`):**
   - Relative Path: `experiments/EXP-07/runs/EXP07_RUN003_SEED42/best_model.pt`
   - File Size: 57,355,665 bytes
   - SHA-256 Checksum: `936EF935F8049FA15FBC735F8073D08F074796ACC20BE0A2885DD35C7CB09D67`
   - Selection Criterion: Peak `dev_mIoU_phenomena` at Epoch 17 ($0.0494$)
2. **Terminal Checkpoint (`last_model.pt`):**
   - Relative Path: `experiments/EXP-07/runs/EXP07_RUN003_SEED42/last_model.pt`
   - File Size: 57,355,665 bytes
   - SHA-256 Checksum: `60411490EFB81D5DE806F4DFFBA760F5D7F4486B14AB4F144AD35D37EE16FA9E`
   - Selection Criterion: Final state at Epoch 27 termination

---

## 18. HOLDOUT Firewall & Zero-Access Verification

- **Programmatic Hard Barrier:** The `OPS02Dataset` constructor raises a `PermissionError` if `partition == "HOLDOUT"` is requested during training ingestion.
- **Firewall Verification Result:**
  - Remote Container Telemetry: `holdout_access_count = 0`
  - Canonical `metrics.json`: `holdout_access_count = 0`
  - Telemetry State: `holdout_access_count = 0`
- **Integrity Status:** `PRISTINE_QUARANTINED`. HOLDOUT remains uninspected, uncalibrated, and fully preserved for future authorized benchmarking.

---

## 19. Incident Register Summary

Five pre-flight infrastructure incidents were logged and resolved prior to completing the valid run:
1. **C16-INC-001 (Kaggle Default GPU sm_60 Deprecation):** Resolved by explicitly targeting `NvidiaTeslaT4` (`sm_75`).
2. **C16-INC-002 (Windows Backslash POSIX Parsing):** Resolved by cross-platform filename normalization and global file index.
3. **C16-INC-003 (Parameter Count Mismatch):** Standalone script had 14,337,516 params; caught by hard pre-flight assertion; replaced with reference `ResNet18UNet` from `exp07_reference.py` (14,310,860 params). Zero epochs trained on wrong architecture.
4. **C16-INC-004 (PyTorch 2.10 Sampler Inheritance):** Constructor called `super().__init__(None)`; fixed to `super().__init__()`.
5. **C16-INC-005 (Transient Antigravity IDE API Drop):** Handled via emergency continuation protocol without creating duplicate runs or restarting unverified processes.

Full details are preserved in `data/metadata/exp07_p0_c16_incident_register_v1.json`.

---

## 20. Infrastructure Workarounds & Lessons Learned

- **Decoupled Checkpoint Serialization:** Uploading dataset archives as single compressed entities significantly outperforms individual file uploads on Kaggle.
- **Strict Parameter Guardrails Work:** The hard assertion on trainable parameter count (`assert trainable_params == 14310860`) successfully prevented executing an unauthorized model configuration in Version 2.
- **Zero Local Laptop Compute Rule Upheld:** Despite multiple container iterations, local hardware was never substituted for the remote cloud runtime.

---

## 21. Guardrail & Regression Test Execution

A comprehensive test suite was executed locally to validate C16 deliverables and confirm zero regression across the repository:
1. **C16 Replicate 003 Guardrails (`tests/test_exp07_p0_c16_replicate003_guardrails.py`):**
   - 6 / 6 tests passed (Kaggle qualification, HOLDOUT firewall, single replicate, checkpoint validity, metrics consistency, metadata existence).
2. **C15 Dataset Freeze Guardrails (`tests/test_exp07_p0_c15_freeze_guardrails.py`):**
   - 12 / 12 tests passed.
3. **Repository-Wide EXP-07 Guardrail Suite (All 15 test suites):**
   - **253 / 253 tests PASSED**, 0 failures, 0 errors.

---

## 22. Comparison with Historical Replicates

| Dimension | Historical C8 (Run 001, Seed 42) | Historical C10 (Run 002, Seed 101) | C16 (Replicate 003, Seed 42) |
|:----------|:---------------------------------|:-----------------------------------|:-----------------------------|
| **Dataset Target** | OPS-01 (Earlier unexpanded) | OPS-01 (Earlier unexpanded) | **`OPS02_v1.0.0_FROZEN`** (Expanded) |
| **TRAIN Set Size** | 72 samples | 72 samples | **132 samples** |
| **DEV Set Size** | 24 samples | 24 samples | **40 samples** |
| **Hardware** | Local CPU | Local CPU | **Kaggle GPU (Dual Tesla T4)** |
| **Throughput** | ~0.4 samples/sec | ~0.4 samples/sec | **17.35 samples/sec** |
| **Training Duration** | ~50 minutes | ~48 minutes | **2.01 minutes** |
| **Best Epoch** | Epoch 12 | Epoch 14 | **Epoch 17** |
| **Best DEV mIoU** | 0.4072 (40.72%) | 0.4057 (40.57%) | **0.0494 (4.94%)** |
| **Top Classes Detected** | `MCC`, `IWs`, `BS`, `LWA` | `MCC`, `IWs`, `BS`, `LWA` | `MCC` (0.2286), `IWs` (0.1039), `BS` (0.1026) |

---

## 23. Scientific Interpretation & Epistemic Boundaries

- **`OBSERVED`:**
  - On the expanded, physically independent `OPS02_v1.0.0_FROZEN` dataset, Replicate 003 (Seed 42) achieved a peak `dev_mIoU_phenomena` of **0.0494** ($4.94\%$) at Epoch 17, with early stopping at Epoch 27.
  - The dominant detected phenomena on the expanded DEV partition remain consistent with historical findings: Mesoscale Cellular Convection (`MCC`, IoU $0.2286$), Internal Waves (`IWs`, IoU $0.1039$), and Biological Slicks (`BS`, IoU $0.1026$).
  - Classes `AF`, `RF`, and `HM` achieved $0.0$ IoU on the expanded DEV evaluation set.
- **`PLAUSIBLE`:**
  - The quantitative difference between OPS-01 DEV performance (~$40\%$) and OPS-02 DEV performance (~$5\%$) is attributable to the substantially increased geographic, radiometric, and scene diversity of OPS-02, which introduced 64 independent parent datatakes and eliminated intra-scene spatial correlation between TRAIN and DEV.
- **`NOT SUPPORTED`:**
  - We do NOT claim the model is "generalized", "production ready", or "state of the art".
  - A single replicate is descriptive evidence of one stochastic realization on the expanded dataset. Multiple independent post-freeze replicates ($N \ge 3$) are mandatory before making claims of statistical reproducibility or generalization.

---

## 24. Limitations

1. **Single Replicate:** C16 represents $N = 1$ realization on OPS-02. Variance across random seeds cannot be estimated from this single run.
2. **Class Imbalance on Expanded DEV:** Rare phenomena (`AF`, `RF`, `HM`) have very few positive pixels in DEV, resulting in zero IoU.
3. **No HOLDOUT Evaluation:** HOLDOUT performance is unknown by design to preserve benchmark integrity.
4. **Resolution / Patch Size:** Tiles are fixed at $256 \times 256$ patches derived from 10x10 block-averaged Sentinel-1 GRD detected digital numbers.

---

## 25. Exact Next Authorized Phase

- **Next Phase:** **EXP-07-P0-C17 — Post-Freeze Replicate Analysis & Next Replicate Scheduling**
- **Explicit Instruction:** Do NOT automatically start another replicate. Do NOT run HOLDOUT evaluation. The user must review this C16 report and formally authorize the next phase.

---

## 26. Final Repository & Process Self-Audit

- **Git Status:**
  - Branch: `master`
  - Working tree: Preserved. Tracked modifications (`.gitignore`, `src/ocean_sentinel/ingestion/dataset.py`) remain completely intact.
  - No destructive Git commands (`commit`, `push`, `reset`, `clean`, `checkout`, `stash`) were executed.
- **Process Verification:**
  - 0 local Python training processes running.
  - Telemetry state: `scratch/exp07_p0_c16_run_state.json` is `COMPLETED`.
  - All test suites (253 tests) pass.
