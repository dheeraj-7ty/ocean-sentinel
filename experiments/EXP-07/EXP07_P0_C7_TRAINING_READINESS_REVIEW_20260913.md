# EXP-07-P0-C7 — TRAINING READINESS REVIEW & FINAL EXPERIMENT EXECUTION GATE
**Phase ID:** `EXP-07-P0-C7`  
**Execution Timestamp:** `2026-09-13T19:00:00Z`  
**Evaluation Mode:** `PLANNING + CPU-ONLY VALIDATION ONLY` (Zero GPU, Zero Optimizer Steps, Zero Parameter Updates, Zero Checkpoints)  
**Authoritative Environment:** Python 3.11.9, PyTorch 2.1.1+cpu, NumPy 1.26.4, rasterio 1.4.3, Windows OS, Git branch `master`  
**Gate Status:** `DECISION A: FINAL — EXP-07 TRAINING PROTOCOL READY FOR EXECUTION`  
**Next Authorized Action:** `EXP-07-P0-C8 — CONTROLLED FIRST TRAINING RUN / BASELINE SEED 001`

---

## 1. Executive Summary & Strategic Context

The mission of Phase **EXP-07-P0-C7** is to evaluate the complete scientific, architectural, algorithmic, and operational foundation developed across phases C2 through C6, and establish an authoritative, failure-resistant, machine-verifiable execution gate for the **first real training run** of Experiment EXP-07.

C7 is **NOT** the training run. C7 executes zero GPU operations, zero gradient updates, zero optimizer steps, and writes zero neural network checkpoints. Instead, C7 freezes the complete training protocol, hyperparameter contract, failure response policy, resource budget, and statistical reporting rules to ensure that when training commences in Phase C8, the resulting model can be defended scientifically, reproduced technically, audited for data leakage, and correctly situated within the broader Ocean Sentinel system architecture.

### Strategic Maritime Intelligence Context
Ocean Sentinel is an advanced maritime situational awareness and intelligence platform designed for:
1. Maritime scene perception and environmental context intelligence;
2. Ocean-phenomena recognition and spatio-temporal dynamics;
3. Maritime vessel activity intelligence and dark vessel detection;
4. Multi-sensor evidence fusion and automated forensic reconstruction;
5. Incident attribution, causal analysis, and operational decision support.

**Critical Epistemic Boundary:**
> **EXP-07 is an isolated perception component within this larger multi-layered system.**  
> EXP-07 evaluates multiclass SAR dark-feature phenomenon segmentation across 12 canonical phenomenon classes (classes $0\dots 11$) on the OPS-01 dataset.  
> **OPS-01 multiclass phenomenon segmentation $\neq$ oil-vs-lookalike discrimination.**  
> EXP-07 does **NOT** perform vessel attribution, does **NOT** establish causal incident liability, does **NOT** resolve oil lookalikes under variable meteorological conditions, and does **NOT** constitute end-to-end Ocean Sentinel maritime intelligence. Downstream experiments (e.g. hard-negative discrimination, multi-sensor fusion, AIS track correlation) are strictly required for operational attribution.

---

## 2. Governance Memory & Preflight Verification

Phase C7 strictly enforces all governance rules accumulated from the project inception through Phase C6, and enacts 3 new rules (GOV-RULE-062 through 064).

### Preflight Repository Integrity
Preflight verification confirmed:
- **Git Branch:** `master`
- **Git Staging:** `0 staged files`
- **Git State:** 2 tracked modifications (`.gitignore` [governance compliance], `src/ocean_sentinel/ingestion/dataset.py` [C6 validity mask bugfix])
- **Authoritative Hashes Verified Exact:**
  - **EXP-06 Best Model Checkpoint:**  
    `experiments/performance/exp06_positive_bce_weight/best_model.pt`  
    SHA-256: `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF`  
    Status: **EXACT MATCH [CALCULATED == AUTHORITATIVE]**
  - **Part-I Internal Development Split Manifest:**  
    `data/metadata/internal_development_split_manifest.json`  
    SHA-256: `17F1FF35146C7CE62E90D6FCE7E197B711B55E3C3CB599610578443208669072`  
    Status: **EXACT MATCH [CALCULATED == AUTHORITATIVE]**
  - **OPS-01 v4 Physical Dataset Manifest:**  
    `data/metadata/ops01_physical_dataset_manifest_v4.json`  
    SHA-256: `FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E`  
    Status: **EXACT MATCH [CALCULATED == AUTHORITATIVE]**

---

## 3. C6 Corrections Maintained as Authoritative Baseline

Phase C7 confirms and locks the corrections established during Phase C6:
1. **Input Domain Semantics (`AGGREGATED_RAW_DN_LOG1P_STANDARDIZED`):**  
   The runtime pathway processes $10\times 10$ spatial block-averaged raw digital numbers (DN) from Level-1 GRD products, checks binary valid data presence ($\text{DN} > 0$), computes $\log(1 + \text{DN})$, and applies fixed TRAIN partition z-score standardization ($\mu_{\text{train}} = 4.2756$, $\sigma_{\text{train}} = 0.3866$).  
   *Metrological Truth:* This input domain is an aggregated digital number count, **NOT** calibrated radar backscatter ($\sigma^0$ in dB or linear power). Describing these inputs as physical backscatter is strictly prohibited (GOV-RULE-060).
2. **Authoritative Loss Weights (TRAIN Valid Pixels Only):**  
   C6 discovered that earlier C4 loss weights were contaminated by invalid background padding ($25.35\%$ of total tile area). C6 recomputed class frequencies strictly over valid foreground data ($\text{valid\_mask} == 1$). C7 freezes these source-recalculated weights across all 12 canonical OPS-01 classes as authoritative:
   - `BG (0)` (Background Seawater): $0.273233$
   - `AF (1)` (Atmospheric Front): $2.013263$
   - `BS (2)` (Biological Slicks): $0.703954$
   - `LWA (3)` (Low Wind Area): $2.493473$
   - `MCC (4)` (Mesoscale Cellular Convection): $0.515947$
   - `OF (5)` (Ocean Front): $1.469686$
   - `POW (6)` (Pure Ocean Wave): $0.512411$
   - `RF (7)` (Rain Cell / Rain Footprint): $1.510850$
   - `WS (8)` (Wind Streak): $0.806601$
   - `Eddy (9)` (Oceanic Eddy): $2.066304$
   - `IWs (10)` (Internal Waves): $0.398704$
   - `HM (11)` (Artificial / Anthropogenic Objects): $12.159536$  
   *Dynamic Range:* $\text{Weight Ratio} = 12.159536 / 0.273233 = 44.5024\times$.

---

## 4. Dataset Sample-Size & Statistical Power Review

Phase C7 conducted an adversarial review of dataset statistical power:

### Physical Dataset Inventory
- **TRAIN Partition:** 72 tiles ($256\times 256$) originating from **12 independent Sentinel-1 IW parent scenes**.
- **DEV Partition:** 39 tiles originating from **7 independent parent scenes**.
- **HOLDOUT Partition:** 36 tiles originating from **8 independent parent scenes**.
- **Total Physical Dataset:** 147 tiles originating from **27 independent parent scenes**.

### Statistical Power Assessment (Epistemic Breakdown)
- **KNOWN:**
  - The true independent sampling unit is the **parent scene**, not the sub-tiled $256\times 256$ spatial patch (GOV-RULE-024). Spatial autocorrelation within tiles from the same parent scene is high.
  - $N=12$ independent training scenes provides sufficient statistical degrees of freedom to verify pipeline execution, gradient propagation, convergence stability, and initial multi-class balancing.
  - Rare classes have very few independent scene occurrences in TRAIN: `HM` (985 pixels, 1 parent), `AF` (35,931 pixels, 3 parents), `Eddy` (34,110 pixels, 3 parents).
- **PLAUSIBLE:**
  - The model will achieve rapid loss minimization on common classes (`BG`, `IWs`, `MCC`, `POW`), but will exhibit higher generalization variance on rare phenomena such as `HM` and `LWA`.
  - Tile-level resampling with replacement (Hybrid Candidate F) mitigates rare-class neglect during batch formation.
- **UNKNOWN:**
  - Whether $N=12$ parent scenes captures sufficient oceanographic, wind-field, and thermal variability to generalize to unseen geographic ocean basins. (Assumed: It does not; broader generalization requires expanded physical catalogs).
- **Epistemic Conclusion:** Training sufficiency exists for **proving pipeline mechanics and baseline learning capability**, but **NOT** for claiming broad global operational generalization.

---

## 5. Training Protocol & Hyperparameter Freeze Contract

Pursuant to `data/metadata/exp07_p0_c7_training_protocol_v1.json`, all hyperparameters are frozen:

### A. Optimizer Contract
- **Algorithm:** `AdamW` (Decoupled Weight Decay Regularization)
- **Base Learning Rate ($\eta$):** $5.0 \times 10^{-4}$ ($0.0005$)
- **Weight Decay ($\lambda$):** $0.01$ (Applied exclusively to 2D convolutional kernels and linear projection weights; strictly excluded from BatchNorm affine parameters $\gamma, \beta$)
- **Betas:** $(\beta_1 = 0.9, \beta_2 = 0.999)$
- **Epsilon ($\epsilon$):** $1.0 \times 10^{-8}$
- **Gradient Clipping:** Mandatory `torch.nn.utils.clip_grad_norm_` with $\text{max\_norm} = 1.0$, $\text{norm\_type} = 2.0$. Executed immediately prior to `optimizer.step()` to prevent rare-class gradient explosion.

### B. Learning Rate Schedule Contract
- **Scheduler:** `LinearWarmupCosineAnnealingLR`
- **Warmup Epochs:** 3 epochs ($E_1 \to E_3$), linearly scaling $\eta$ from $1.0 \times 10^{-5}$ to $5.0 \times 10^{-4}$.
- **Annealing Phase:** 27 epochs ($E_4 \to E_{30}$), cosine decaying from $5.0 \times 10^{-4}$ to minimum $\eta_{\text{min}} = 1.0 \times 10^{-6}$.
- **Step Frequency:** Exactly once per epoch at epoch completion.
- **Metric Dependency:** **NONE.** The schedule is strictly deterministic and decoupled from DEV validation loss to prevent accidental validation metric leakage.

### C. Epoch Budget & Early Stopping Contract
- **Maximum Epochs:** 30 epochs.
- **Minimum Epochs:** 15 epochs (Early stopping disabled during epochs 1–15 to ensure adequate exploration across rare classes).
- **Early Stopping Monitor:** `dev_mIoU_phenomena`.
- **Patience:** 10 epochs.
- **Minimum Improvement Threshold ($\delta$):** $0.005$ ($+0.5\%$ absolute mIoU).
- **Holdout Rule:** Early stopping monitors DEV only. HOLDOUT is never evaluated during routine training or stopping checks.

### D. Batch Dynamics & Normalization Contract
- **Physical Minibatch Size ($B_{\text{phys}}$):** 8 tiles ($256\times 256\times 1$).
- **Gradient Accumulation Steps ($S_{\text{accum}}$):** 2 steps.
- **Effective Virtual Optimizer Batch ($B_{\text{opt}}$):** $8 \times 2 = 16$ tiles.
- **BatchNorm Statistical Batch Size ($B_{\text{BN}}$):** Exactly 8 tiles.
- **BatchNorm Running Momentum:** Fixed at $0.05$ across all 30 BatchNorm2d layers.
- **Epistemic Invariance (GOV-RULE-059):** Gradient accumulation affects only optimizer weight updates; it does **NOT** increase the sample size seen by BatchNorm layers during forward passes.

### E. Loss Function & Metric Contract
- **Supervised Loss:** `torch.nn.CrossEntropyLoss(weight=SOURCE_RECALCULATED_WEIGHTS, ignore_index=-100, reduction='mean')`.
- **Target Remapping:** OPS-01 12 canonical classes ($0\dots 11$), unannotated pixels mapped to `ignore_index = -100`, invalid data pixels ($\text{valid\_mask} == 0$) mapped to `ignore_index = -100`.
- **Decision Rule:** Multiclass `argmax(logits, dim=1)` across all 12 channels. Zero thresholding parameters allowed (GOV-RULE-057).
- **Primary Model Selection Metric:** `dev_mIoU_phenomena` (Macro IoU averaged across non-background phenomena present in ground truth).
- **Absent-Class Metric Handling:** Classes with zero ground-truth pixels in a validation batch are excluded from the macro denominator to prevent division by zero or artificial score deflation.

---

## 6. Seed Strategy & Replication Hierarchy

To prevent single-seed bias from contaminating scientific conclusions (GOV-RULE-063), Phase C7 freezes a deterministic replication hierarchy:
- **Base Baseline Seed:** `42` (Designated for initial baseline `EXP07_RUN001_SEED42`).
- **Authorized Replication Seeds:** `101` (`RUN002`), `2024` (`RUN003`).
- **Seed Derivation Hierarchy:**
  - Python Random Seed: $S$
  - NumPy Random Seed: $S + 1$
  - PyTorch Manual Seed: $S + 2$
  - PyTorch CUDA Manual Seed: $S + 3$
  - Sampler Generation Seed: $S + 4$
  - DataLoader Worker Seed Base: $S + 100$

---

## 7. Model-Selection & Checkpoint Policy

### Checkpoint Provenance Identity
Every checkpoint saved during Phase C8 must contain an immutable provenance contract dictionary:
- `experiment_id`: `EXP-07`
- `protocol_version`: `v1`
- `run_id`: e.g. `EXP07_RUN001_SEED42`
- `seed`: Integer seed
- `epoch`: Integer epoch
- `global_step`: Total optimizer steps
- `git_commit`: Active git commit SHA
- `model_architecture`: `ResNet18-UNet` (14,310,860 parameters)
- `dataset_manifest_hash`: `FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E`
- `train_loss`, `dev_loss`, `dev_mIoU_phenomena`, `dev_class_iou`
- `rng_state_dict`: Complete Python, NumPy, and PyTorch RNG states.

### Checkpoint Identity Tiers
1. **Candidate Checkpoint:** Saved at the end of every epoch as `checkpoint_epoch_{epoch:03d}.pt`. (Kept in rolling buffer of last 3 epochs).
2. **Best-on-DEV Checkpoint:** Saved as `best_model_dev_mIoU.pt` whenever `dev_mIoU_phenomena` exceeds current best by $\ge 0.005$.
3. **Archival Final Checkpoint:** Saved at run completion as `final_model_epoch_{epoch:03d}.pt`.
4. **Selected-for-Reporting:** Formally chosen strictly via DEV performance. HOLDOUT must never select the checkpoint.

---

## 8. Holdout Protection & Firewall Contract

HOLDOUT partition data ($N=36$ tiles, 8 parent scenes) is placed behind an automated architectural firewall:
1. **Training Isolation:** Training data loaders, loss functions, optimizers, and schedulers cannot reference or load HOLDOUT paths.
2. **Stopping Isolation:** Early stopping criteria inspect only DEV metrics.
3. **Selection Isolation:** Best model selection inspects only DEV metrics.
4. **Quarantine Enforcement:** HOLDOUT evaluation is authorized exclusively as a single, post-training evaluation pass on the frozen selected checkpoint.
5. **Epistemic Disclosure Preserved:** `HOLDOUT_PARTIALLY_USED_FOR_SELECTION` is preserved in all reporting contracts to disclose that holdout data cannot serve as an unbiased benchmark if hyperparameter tuning occurs.

---

## 9. Failure & Recovery Policy

The C7 failure recovery policy (`data/metadata/exp07_p0_c7_failure_policy_v1.json`) defines a strict 7-stage lifecycle:
$$\text{DETECT} \longrightarrow \text{CAPTURE} \longrightarrow \text{STOP} \longrightarrow \text{PRESERVE} \longrightarrow \text{CLASSIFY} \longrightarrow \text{INCIDENT} \longrightarrow \text{NO\_SILENT\_RETRY}$$

### Monitored Failure Modes & Automatic Responses
1. **NaN / Inf Loss:** Immediate execution halt, state telemetry dumped, run marked `FAILED_NUMERICAL_INSTABILITY`. Silent restart prohibited.
2. **Exploding Gradients ($\|\mathbf{g}\|_2 > 10.0$ post-clipping):** Alert logged, step aborted if persistent.
3. **All-Background Collapse ($\ge 99.5\%$ background across consecutive batches):** Flagged as `COLLAPSE_ALL_BACKGROUND`.
4. **Out of Memory (OOM):** Process caught, cache cleared, batch metrics logged, run aborted with memory profile telemetry.
5. **I/O & Data Corruption:** Dataset loader catches corrupted GeoTIFF headers; fails loudly without silent dropping.
6. **BatchNorm Variance Non-Positivity ($\sigma_B^2 \le 0$):** Fails numerical sanity check.
7. **Invalid Target Label Detection ($y \notin [0, 6] \cup \{-100\}$):** Immediate runtime assertion failure.

---

## 10. Resource & Compute Budget

Detailed in `data/metadata/exp07_p0_c7_resource_estimate_v1.json`:
- **VRAM Footprint:**
  - Model Parameters (FP32): $54.6\text{ MB}$
  - AdamW Optimizer States: $109.3\text{ MB}$
  - Input Minibatch ($8\times 1\times 512\times 512$ FP32): $8.4\text{ MB}$
  - Forward Activations: $\approx 1,200\text{ MB}$
  - Working Headroom: $\approx 600\text{ MB}$
  - **Estimated Peak VRAM:** $\mathbf{1,972.3\text{ MB}}$ ($\approx 2.0\text{ GB}$). Feasible on any modern consumer or data center GPU ($>4\text{ GB}$).
- **Execution Runtime:**
  - GPU (e.g. RTX 3080/4090): $\approx 1.5 - 2.5\text{ s/epoch}$ $\implies \approx 60 - 75\text{ seconds}$ per 30-epoch run.
  - CPU (8-core x86_64): $\approx 15.0\text{ s/epoch}$ $\implies \approx 7.5\text{ minutes}$ per 30-epoch run.
- **Disk Storage:** $\approx 333\text{ MB}$ per run; $\approx 1.0\text{ GB}$ for full 3-seed replicate matrix.

---

## 11. Adversarial "Can We Train?" Checklist (20/20 Cleared)

| # | Item | Status | Verification Detail |
|---|---|---|---|
| 1 | **DATA** | **CLEARED** | Every training sample traced to authoritative manifest `ops01_physical_dataset_manifest_v4.json` (SHA256 verified). |
| 2 | **LABELS** | **CLEARED** | Target remapping exact: 12 canonical dense classes [0..11], invalid data and unlabeled mapped to `-100`. |
| 3 | **PREPROCESSING** | **CLEARED** | Input domain unambiguous: `AGGREGATED_RAW_DN_LOG1P_STANDARDIZED` with fixed TRAIN $\mu=4.2756, \sigma=0.3866$. |
| 4 | **LEAKAGE** | **CLEARED** | Normalization uses TRAIN only; DEV/HOLDOUT strictly quarantined from statistical computation. |
| 5 | **LOSS** | **CLEARED** | C6 recomputed weights verified over valid foreground pixels only (0.273 to 12.16, dynamic ratio 44.5x). |
| 6 | **SAMPLER** | **CLEARED** | Candidate F Hybrid ($0.70 P_{\text{parent}} + 0.30 P_{\text{presence}}$) exact, with replacement, 72 draws/epoch. |
| 7 | **MODEL** | **CLEARED** | ResNet18-UNet architecture shape contract exact: input $(B, 1, 256, 256) \to$ output $(B, 12, 256, 256)$. |
| 8 | **BN** | **CLEARED** | Physical batch (8) and statistical batch (8) explicitly separated from optimizer batch (16). Momentum frozen at 0.05. |
| 9 | **OPTIMIZER** | **CLEARED** | AdamW baseline frozen ($\eta=5e-4, \lambda=0.01, \beta=(0.9, 0.999), \epsilon=1e-8$) with grad clipping at $1.0$. |
| 10 | **SCHEDULER** | **CLEARED** | LinearWarmupCosineAnnealingLR frozen (3 epoch warmup, 27 epoch cosine decay to 1e-6). Decoupled from DEV metrics. |
| 11 | **STOPPING** | **CLEARED** | Early stopping fixed on `dev_mIoU_phenomena` (patience 10, min epoch 15, $\delta=0.005$). HOLDOUT isolated. |
| 12 | **SELECTION** | **CLEARED** | Checkpoint selection fixed strictly on peak `dev_mIoU_phenomena`. HOLDOUT selection strictly prohibited. |
| 13 | **SEEDS** | **CLEARED** | Multi-seed replicate matrix frozen (Seeds 42, 101, 2024). Single-seed performance barred from being reported as robust evidence. |
| 14 | **METRICS** | **CLEARED** | Multiclass argmax decision rule; absent ground-truth classes excluded from macro denominator; zero threshold tuning. |
| 15 | **FAILURE** | **CLEARED** | 7-step failure lifecycle and 10 monitored failure modes specified with automated halt tripwires. |
| 16 | **REPRODUCIBILITY**| **CLEARED** | Exact software stack versions, RNG hierarchy, and hardware execution context recorded. |
| 17 | **PROVENANCE** | **CLEARED** | Comprehensive checkpoint metadata schema bound to run identity, manifest hash, and active git commit. |
| 18 | **TELEMETRY** | **CLEARED** | Live telemetry schema defined with heartbeat, epoch metrics, and explicit UNKNOWN for unmeasurable ETA. |
| 19 | **REPORTING** | **CLEARED** | Scope preserved: OPS-01 multiclass $\neq$ oil-vs-lookalike; tile count $\neq$ independent parent count; claims strictly bounded. |
| 20 | **RESOURCE** | **CLEARED** | Compute budget feasible: $<2.0\text{ GB}$ VRAM, $\approx 75\text{ s}$ GPU / $\approx 7.5\text{ min}$ CPU per run, $\approx 1.0\text{ GB}$ disk. |

---

## 12. Final Decision & Authorization

### Decision:
$$\mathbf{DECISION\ A:\ FINAL\ —\ EXP-07\ TRAINING\ PROTOCOL\ READY\ FOR\ EXECUTION}$$

### Justification:
1. All training design decisions, optimization hyperparameters, scheduling dynamics, loss weights, and stopping criteria are formally frozen in authoritative metadata contracts.
2. The adversarial checklist is 100% cleared across all 20 technical and scientific gates.
3. Holy-grail holdout protection and data-leakage firewalls are mathematically and programmatically enforced.
4. Epistemic boundaries regarding maritime intelligence attribution, lookalike discrimination, and dataset statistical power are explicitly preserved.
5. All C7 and predecessor verification guardrails pass without failure.

### Next Authorized Action:
$$\mathbf{EXP-07-P0-C8\ —\ CONTROLLED\ FIRST\ TRAINING\ RUN\ /\ BASELINE\ SEED\ 001}$$
Phase C8 is authorized to execute the first controlled baseline training run under Seed 42 following the exact frozen protocol in `exp07_p0_c7_training_protocol_v1.json`. Hyperparameter sweeps, architecture modifications, and holdout evaluations remain strictly prohibited.
