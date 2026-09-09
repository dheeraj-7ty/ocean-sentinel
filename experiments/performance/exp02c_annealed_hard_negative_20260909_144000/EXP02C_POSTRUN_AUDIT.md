# EXP-02C POST-RUN SCIENTIFIC AUDIT & TEST-AUTHORIZATION GATE

**Experiment ID**: `EXP-02C`  
**Parent Experiment**: `EXP-02B-1`  
**Intervention**: Annealed Hard-Negative Sampling Pressure  
**Date / Timestamp**: `2026-09-09T13:45:00Z`  
**Author**: Implementation/Recovery Engineer under CAO Oversight  
**Status**: `COMPLETE`  
**Final Gate Decision**: `TEST ACCESS: AUTHORIZED`  

---

## 1. REPOSITORY REALITY AUDIT

| Field | Authority / Verified State | Confirmation |
|---|---|---|
| **Git HEAD** | `8f444de1d0fb35d09912a9e6bf27cebde8125f0d` | Verified (`git rev-parse HEAD`) |
| **Git Branch** | `master` | Verified (`git branch --show-current`) |
| **Git Status** | Uncommitted files preserved; zero reset, revert, stash, or clean executed | Verified |
| **Local Python Environment** | Python 3.10.9 (`D:\Projects\ocean-sentinel\venv\Scripts\python.exe`) | Verified |
| **Local PyTorch / CUDA** | PyTorch 2.14.0+cu126, CUDA 12.6, RTX 3050 Laptop GPU (`sm_86`) | Verified |
| **Cloud Tooling Isolation** | `D:\Tools\cloud-tools` (Isolated from project venv) | Verified |
| **Experiment Directory** | `d:\Projects\ocean-sentinel\experiments\performance\exp02c_annealed_hard_negative_20260909_144000` | Verified |

---

## 2. REMOTE JOB PROVENANCE & EXECUTION RECORD

| Provenance Dimension | Preregistered Contract | Remote Execution Observation | Audit Status |
|---|---|---|:---:|
| **Kaggle Kernel ID** | `dheeraj12237/ocean-sentinel-gate-4-3b-live-canary` | `dheeraj12237/ocean-sentinel-gate-4-3b-live-canary` | **MATCH** |
| **Kaggle Kernel Version** | Version 21 (Full 30-Epoch Training Run) | Version 21 | **MATCH** |
| **Execution Hardware** | NVIDIA Tesla T4 GPU (`sm_75`, 15,360 MiB VRAM) | Tesla T4 (`sm_75`) verified in runner log | **MATCH** |
| **Remote Software Stack** | Linux 6.12.90+, Python 3.10.16, PyTorch 2.10.0+cu128, CUDA 12.8, cuDNN 91002 | Verified in runner log | **MATCH** |
| **Remote Job Completion Status** | `KernelWorkerStatus.COMPLETE` | Verified via Kaggle CLI | **MATCH** |
| **Remote Subprocess Return Code** | `0` (Success) | Verified: returncode `0` | **MATCH** |
| **Total Training Duration** | 30 Epochs (Expected ~3.6 hours) | Finished in 3.60 hours (12,969 s) | **MATCH** |
| **Spatial Split Manifest SHA-256** | `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` | `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` | **MATCH** |
| **Candidate Manifest SHA-256** | `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7` | `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7` | **MATCH** |
| **ImageNet Pretrained Weights SHA** | `B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F` | `B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F` | **MATCH** |
| **Decompressed Runner SHA-256** | `F0F569F11E60777C41AD6D3082828BD43E195E910495EF2025310694B59EA347` | `F0F569F11E60777C41AD6D3082828BD43E195E910495EF2025310694B59EA347` | **MATCH** |
| **Step Accounting Total** | 50,400 Attempts ($30 \times 1,680$) | 50,380 Updates, 20 AMP Skips (99.96% efficiency) | **MATCH** |

---

## 3. ARTIFACT INVENTORY & CERTIFIED HASHES

All remote artifacts were retrieved via Kaggle CLI to `remote_training_output/` and reconciled with the experiment root directory. Every downloaded file was verified using SHA-256:

| Artifact Name | File Path | Certified SHA-256 Hash | Size (Bytes) | Verification Status |
|---|---|---|---|:---:|
| **Authoritative Checkpoint** | `best_model.pt` | `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` | 292,467,955 | **VERIFIED** |
| **Final Epoch Checkpoint** | `final_model.pt` | `B3FC0DD08E8B2BD24025F8F7E22517739977B153AED82822B95B3ACBE0D161C2` | 292,470,107 | **VERIFIED** |
| **Latest Training Checkpoint** | `latest_checkpoint.pt` | `B250126F59A79BC23EF02A6BAD123D6B1655A76800AB590A0954194090428C60` | 292,474,571 | **VERIFIED** |
| **Complete History Record** | `history.json` | `E7B607DBF2DBA5E1817F0793216664AF2A6BE89A06B8E63E15ECCB3D0C8DCE3B` | 27,381 | **VERIFIED** |
| **Run State Document** | `run_state.json` | `3D4AA2290C8AC434EFEE36EE6E03E0A034F356C0D5D2146399720C773631896A` | 21,711 | **VERIFIED** |
| **Standard Output Training Log** | `stdout_training.log` | `35CFB2427EFBC29E2E2EE29138009F38226AE2F1490E81FFCF7A854328570E52` | 76,090 | **VERIFIED** |
| **Progress Log** | `progress.log` | `35CFB2427EFBC29E2E2EE29138009F38226AE2F1490E81FFCF7A854328570E52` | 76,090 | **VERIFIED** |
| **Training Runner Source** | `train_exp02c.py` | `F0F569F11E60777C41AD6D3082828BD43E195E910495EF2025310694B59EA347` | 31,068 | **VERIFIED** |
| **Remote Host Telemetry Log** | `ocean-sentinel-gate-4-3b-live-canary.log` | `0747F0870DF7687248F6C1957D24326019D354A6471800903AE92C3CF2825EDD` | 122,644 | **VERIFIED** |

*Note*: The subfolder copy in `remote_training_output/exp02c_annealed_hard_negative_training/` was bit-for-bit identical to the outer download (all SHA-256 hashes matched 1-to-1). Preflight logs from the local canary were preserved as `preflight_progress.log` and `preflight_run_state.json`.

---

## 4. COMPLETE 30-EPOCH TRAJECTORY RECONSTRUCTION

The complete empirical trajectory extracted directly from canonical `history.json` and reconciled against `stdout_training.log`:

| Ep | $w_{\text{hard}}$ | $E[P_{\text{hard}}]$ | TrainLoss | ValLoss | ValIoU | ValRecall | ValPrec | ValNegFA% | Pred/GT | Underseg | TinyRec | MedRec | LrgRec | Tier 1 | Tier 2 | Status |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 2.2500 | 26.25% | 0.6540 | 0.5709 | 0.1123 | 91.56% | 11.35% | 100.00% | 3.4236 | 27 | 70.60% | 86.45% | 91.82% | PASS | FAIL | Non-qualifying |
| 2 | 2.2456 | 26.21% | 0.5122 | 0.4703 | 0.6789 | 87.57% | 75.14% | 99.78% | 1.1466 | 94 | 61.34% | 88.69% | 87.55% | PASS | FAIL | Non-qualifying |
| 3 | 2.2325 | 26.10% | 0.4404 | 0.4182 | 0.7166 | 84.22% | 82.78% | 12.37% | 1.0028 | 156 | 64.77% | 88.97% | 84.03% | PASS | FAIL | Non-qualifying |
| 4 | 2.2107 | 25.91% | 0.4059 | 0.3983 | 0.7045 | 80.09% | 85.40% | 8.16% | 0.8963 | 281 | 62.18% | 79.83% | 80.12% | PASS | PASS | **QUALIFYING** |
| 5 | 2.1807 | 25.65% | 0.3915 | 0.3923 | 0.7184 | 80.86% | 86.55% | 5.86% | 0.9266 | 250 | 56.33% | 79.24% | 80.97% | PASS | PASS | **QUALIFYING** |
| 6 | 2.1426 | 25.31% | 0.3826 | 0.3864 | 0.7221 | 82.94% | 84.82% | 9.96% | 0.9726 | 226 | 60.53% | 79.19% | 83.13% | PASS | PASS | **QUALIFYING** |
| 7 | 2.0971 | 24.91% | 0.3477 | 0.2175 | 0.6951 | 77.70% | 86.83% | 2.08% | 0.8818 | 334 | 36.36% | 68.66% | 78.15% | FAIL | PASS | Non-qualifying |
| 8 | 2.0445 | 24.44% | 0.2372 | 0.1199 | 0.6563 | 72.21% | 87.81% | 2.08% | 0.8014 | 279 | 11.89% | 58.54% | 72.89% | FAIL | PASS | Non-qualifying |
| 9 | 1.9855 | 23.90% | 0.1749 | 0.2246 | 0.4875 | 54.73% | 81.70% | 2.85% | 0.6251 | 172 | 4.11% | 15.38% | 56.53% | FAIL | PASS | Non-qualifying |
| 10 | 1.9209 | 23.30% | 0.1515 | 0.1092 | 0.6622 | 73.42% | 87.10% | 0.93% | 0.8165 | 271 | 12.97% | 53.84% | 74.36% | FAIL | PASS | Non-qualifying |
| 11 | 1.8513 | 22.65% | 0.1360 | 0.0967 | 0.6604 | 74.84% | 84.89% | 1.37% | 0.8599 | 292 | 27.59% | 65.05% | 75.33% | FAIL | PASS | Non-qualifying |
| 12 | 1.7776 | 21.95% | 0.1322 | 0.1096 | 0.6366 | 73.33% | 82.83% | 0.82% | 0.8390 | 239 | 11.98% | 57.46% | 74.10% | FAIL | PASS | Non-qualifying |
| 13 | 1.7006 | 21.20% | 0.1246 | 0.0862 | 0.6780 | 78.45% | 83.31% | 1.26% | 0.9043 | 272 | 36.58% | 71.67% | 78.80% | FAIL | PASS | Non-qualifying |
| 14 | 1.6213 | 20.41% | 0.1271 | 0.0911 | 0.6558 | 79.23% | 79.19% | 1.31% | 0.9244 | 265 | 39.95% | 71.70% | 79.61% | PASS | PASS | **QUALIFYING** |
| 15 | 1.5406 | 19.59% | 0.1199 | 0.0926 | 0.6807 | 77.61% | 84.70% | 0.82% | 0.8969 | 255 | 18.01% | 62.82% | 78.33% | FAIL | PASS | Non-qualifying |
| 16 | 1.4594 | 18.75% | 0.1133 | 0.1066 | 0.6451 | 68.21% | 92.23% | 0.38% | 0.7343 | 360 | 16.69% | 55.99% | 68.81% | FAIL | PASS | Non-qualifying |
| 17 | 1.3787 | 17.90% | 0.1017 | 0.0913 | 0.6903 | 74.63% | 90.20% | 0.33% | 0.8230 | 303 | 32.49% | 63.16% | 75.19% | FAIL | PASS | Non-qualifying |
| 18 | 1.2994 | 17.05% | 0.1063 | 0.0826 | 0.7060 | 77.32% | 89.03% | 1.20% | 0.8601 | 366 | 42.75% | 67.00% | 77.82% | FAIL | PASS | Non-qualifying |
| 19 | 1.2224 | 16.20% | 0.1061 | 0.0792 | 0.7078 | 79.02% | 87.16% | 1.20% | 0.8960 | 267 | 42.78% | 74.79% | 79.25% | PASS | PASS | **QUALIFYING** |
| 20 | 1.1487 | 15.38% | 0.1020 | 0.0865 | 0.7023 | 76.44% | 89.63% | 0.99% | 0.8478 | 346 | 35.21% | 64.70% | 77.01% | FAIL | PASS | Non-qualifying |
| 21 | 1.0791 | 14.58% | 0.1035 | 0.0894 | 0.6668 | 70.43% | 92.60% | 0.93% | 0.7558 | 442 | 42.28% | 64.95% | 70.71% | FAIL | PASS | Non-qualifying |
| 22 | 1.0145 | 13.83% | 0.0967 | 0.0750 | 0.7257 | 81.64% | 86.72% | 1.81% | 0.9357 | 233 | 50.87% | 75.75% | 81.94% | PASS | PASS | **QUALIFYING** |
| 23 | 0.9555 | 13.13% | 0.0986 | 0.0763 | 0.7056 | 80.29% | 85.34% | 1.59% | 0.9103 | 267 | 44.68% | 77.03% | 80.47% | PASS | PASS | **QUALIFYING** |
| 24 | 0.9029 | 12.50% | 0.0950 | 0.0827 | 0.7059 | 76.74% | 89.80% | 0.71% | 0.8499 | 320 | 37.73% | 66.24% | 77.26% | FAIL | PASS | Non-qualifying |
| 25 | 0.8574 | 11.94% | 0.0917 | 0.0749 | 0.7268 | 80.21% | 88.56% | 0.88% | 0.9000 | 279 | 41.54% | 71.71% | 80.63% | PASS | PASS | **QUALIFYING** |
| 26 | 0.8193 | 11.47% | 0.0932 | 0.0729 | **0.7288** | 82.03% | 86.72% | 1.15% | 0.9394 | 244 | 43.16% | 76.13% | 82.34% | PASS | PASS | **BEST QUALIFYING** |
| 27 | 0.7893 | 11.10% | 0.0922 | 0.0757 | 0.7041 | 80.05% | 85.40% | 1.15% | 0.9046 | 290 | 43.30% | 73.65% | 80.37% | PASS | PASS | **QUALIFYING** |
| 28 | 0.7675 | 10.83% | 0.0901 | 0.0738 | 0.7222 | 80.28% | 87.80% | 1.26% | 0.9050 | 277 | 44.14% | 75.58% | 80.53% | PASS | PASS | **QUALIFYING** |
| 29 | 0.7544 | 10.66% | 0.0911 | 0.0743 | 0.7126 | 80.31% | 86.34% | 0.99% | 0.9077 | 276 | 41.49% | 73.88% | 80.64% | PASS | PASS | **QUALIFYING** |
| 30 | 0.7500 | 10.61% | 0.0890 | 0.0760 | 0.7153 | 79.27% | 87.99% | 0.93% | 0.8874 | 315 | 42.34% | 72.12% | 79.63% | PASS | PASS | **QUALIFYING** |

---

## 5. INDEPENDENT SELECTION & MARGIN ANALYSIS

### Authoritative Model Selection Hierarchy:
- **Tier 1**: Validation Recall $\ge 79.00\%$
- **Tier 2**: Validation GT-Negative False Alarm Rate $\le 12.00\%$
- **Tier 3**: Maximize Global Validation IoU among qualifying checkpoints

### Independent Ranking of All 13 Qualifying Epochs:

| Rank | Epoch | Validation IoU | Validation Recall | Validation GT-Neg FA % | Validation Loss | Qualification Margin vs Thresholds |
|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **1** | **Epoch 26** | **0.72879** | **82.03%** | **1.15%** | **0.0729** | **+3.03 pp Recall, -10.85 pp FA** |
| 2 | Epoch 25 | 0.72682 | 80.21% | 0.88% | 0.0749 | +1.21 pp Recall, -11.12 pp FA |
| 3 | Epoch 22 | 0.72567 | 81.64% | 1.81% | 0.0750 | +2.64 pp Recall, -10.19 pp FA |
| 4 | Epoch 28 | 0.72219 | 80.28% | 1.26% | 0.0738 | +1.28 pp Recall, -10.74 pp FA |
| 5 | Epoch 6 | 0.72215 | 82.94% | 9.96% | 0.3864 | +3.94 pp Recall, -2.04 pp FA |
| 6 | Epoch 5 | 0.71840 | 80.86% | 5.86% | 0.3923 | +1.86 pp Recall, -6.14 pp FA |
| 7 | Epoch 30 | 0.71529 | 79.27% | 0.93% | 0.0760 | +0.27 pp Recall, -11.07 pp FA |
| 8 | Epoch 29 | 0.71258 | 80.31% | 0.99% | 0.0743 | +1.31 pp Recall, -11.01 pp FA |
| 9 | Epoch 19 | 0.70780 | 79.02% | 1.20% | 0.0792 | +0.02 pp Recall, -10.80 pp FA |
| 10 | Epoch 23 | 0.70557 | 80.29% | 1.59% | 0.0763 | +1.29 pp Recall, -10.41 pp FA |
| 11 | Epoch 4 | 0.70445 | 80.09% | 8.16% | 0.3983 | +1.09 pp Recall, -3.84 pp FA |
| 12 | Epoch 27 | 0.70411 | 80.05% | 1.15% | 0.0757 | +1.05 pp Recall, -10.85 pp FA |
| 13 | Epoch 14 | 0.65575 | 79.23% | 1.31% | 0.0911 | +0.23 pp Recall, -10.69 pp FA |

### Margins between Best (Epoch 26) and Second-Best (Epoch 25):
- **Global IoU Margin**: $0.72879 - 0.72682 = \mathbf{+0.00197}$ ($+0.197$ percentage points)
- **Validation Recall Margin**: $82.03\% - 80.21\% = \mathbf{+1.82\text{ percentage points}}$
- **Validation False Alarm Margin**: $1.15\% - 0.88\% = \mathbf{+0.27\text{ percentage points}}$ (Both far below the $12.00\%$ ceiling)
- **Validation Loss Margin**: $0.0729$ vs $0.0749$ (Epoch 26 achieved lower validation loss)

**Finding**: Epoch 26 is independently and unambiguously verified as the sole optimal qualifying checkpoint under the preregistered 3-tier hierarchy.

---

## 6. CHECKPOINT VERIFICATION & STATE RECONCILIATION

The authoritative saved checkpoint `best_model.pt` was loaded and audited offline:

1. **Existence & Size**:
   - File exists at `d:\Projects\ocean-sentinel\experiments\performance\exp02c_annealed_hard_negative_20260909_144000\best_model.pt`
   - Size: 292,467,955 bytes
   - SHA-256: `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A`
2. **Metadata Verification**:
   - `epoch`: `26` (Exact match with Best Qualifying Epoch)
   - `val_iou`: `0.72879` (Exact match with Epoch 26 history)
   - `val_recall`: `0.8203` (Exact match with Epoch 26 history)
   - `threshold`: `0.22` (Strictly constant)
3. **Architecture & Parameter Audit**:
   - Architecture: `ResNet34UNet` (`in_channels=2`, `num_classes=1`, `adaptation_method='slice_variance_scaled'`)
   - `missing_keys`: `[]` (Zero missing weights)
   - `unexpected_keys`: `[]` (Zero unexpected tensors)
   - Total model parameters: **`24,346,305`** (Exact invariant match)
   - Trainable parameters: **`24,346,305`**
   - Parameter finiteness: Strictly 100% finite (zero NaN, zero Inf across all weights and buffers)
4. **Execution Forward Pass**:
   - Input shape: `[1, 2, 512, 512]`
   - Output shape: `[1, 1, 512, 512]`
   - Output values: All finite real numbers
5. **Step Accounting**:
   - Attempts at Epoch 26: 43,680
   - Successful updates: 43,662
   - AMP GradScaler skips: 18 (0.041% skip rate)
   - Total attempts at Epoch 30: 50,400 (50,380 updates, 20 skips)

---

## 7. TEST FIREWALL VERIFICATION

Strict audit of the runner scripts, training logs, remote telemetry, and execution environments confirmed:
- `ds_test` remained strictly `None` throughout the entirety of the remote Kaggle run.
- Line 50 of runner log explicitly recorded:  
  `2026-09-09T09:43:33Z [INFO] [PASS] 8. Zero test dataset/loader constructed during training (ds_test = None)`
- Zero test data loaders were instantiated.
- Zero test tiles were read or processed.
- Zero test metrics were computed, displayed, or logged.
- The training run explicitly terminated immediately upon completion of Epoch 30 validation with log line:  
  `2026-09-09T13:19:18Z [INFO] EXP02C TRAINING & VALIDATION COMPLETE. STOPPED BEFORE TEST ACCESS.`
- Zero post-hoc threshold tuning or threshold search was conducted (threshold locked to `0.22`).
- **Verdict**: The test firewall was 100% unbreached.

---

## 8. SCIENTIFIC INVARIANT VERIFICATION

Every preregistered scientific invariant was checked across `train_exp02c.py`, `config.json`, `run_state.json`, and the remote runner execution environment:

| Scientific Invariant | Preregistered Specification | Reconciled Audit Value | Status |
|---|---|---|:---:|
| **Model Architecture** | ResNet34UNet, 2 channels in, 1 class out | ResNet34UNet, 2 in, 1 out | **PASS** |
| **Channel Adaptation** | `slice_variance_scaled` | `slice_variance_scaled` | **PASS** |
| **Model Parameters** | 24,346,305 parameters | 24,346,305 parameters | **PASS** |
| **Pretrained Weights** | ImageNet ResNet-34 (`B627A593...`) | `B627A593...` verified | **PASS** |
| **Loss Function** | Combined BCE (0.5) + Dice (0.5, smooth 1.0) | Combined BCE (0.5) + Dice (0.5) | **PASS** |
| **Optimizer** | AdamW ($\text{lr}=10^{-4}, \text{wd}=10^{-2}, \beta=(0.9, 0.999), \epsilon=10^{-8}$) | AdamW verified | **PASS** |
| **Scheduler** | CosineAnnealingLR ($T_{\max}=30, \eta_{\min}=10^{-6}$) | CosineAnnealingLR verified | **PASS** |
| **Batch Size** | 8 (effective batch size 8, accum=1) | Batch size 8 verified | **PASS** |
| **Precision** | CUDA AMP FP16 + GradScaler | FP16 + GradScaler (20 skips / 50.4k) | **PASS** |
| **Seed** | 42 (`torch.Generator().manual_seed(42)`) | Seed 42 verified | **PASS** |
| **Samples per Epoch** | 13,440 with replacement | 13,440 samples/epoch ($1,680 \times 8$) | **PASS** |
| **Data Partition** | Canonical Trujillo Spatial Split (`C052720A...`) | Manifest `C052720A...` verified | **PASS** |
| **Candidate Partition** | Approved Candidate Manifest (`5876A4E6...`) | Candidate `5876A4E6...` verified | **PASS** |
| **Normalization** | Canonical VV (-33.23 / 6.49), VH (-19.94 / 4.53) | Exact constants verified | **PASS** |
| **Train Transform** | `SARGeometricAugmentation` | Exact augmentation pipeline | **PASS** |
| **Validation Transform**| `IdentityTransform` | Exact identity pipeline | **PASS** |
| **Decision Threshold** | Constant `0.22` (NO search) | Locked `0.22` verified | **PASS** |
| **Annealing Equation** | $w_{\text{hard}}(e) = 0.75 + 0.75(1 + \cos((e-1)\pi / 29))$ | Verified ($2.25 \to 0.75$) | **PASS** |

---

## 9. DISCREPANCIES & DISPOSITIONS

1. **Preflight File Naming Reconciliation**:
   - *Observation*: The local preflight verification created `progress.log` and `run_state.json` (timestamped 09:19Z). The full remote training run also produced `progress.log` and `run_state.json` (timestamped 13:19Z).
   - *Disposition*: The preflight files were cleanly preserved as `preflight_progress.log` and `preflight_run_state.json`. The full 30-epoch training artifacts were placed in the experiment root directory alongside the pristine downloaded copies in `remote_training_output/`. No historical artifact was deleted.
2. **Local Machine Shutdown Resilience**:
   - *Observation*: The local development laptop shut down during Epoch 11 while the remote Kaggle job continued asynchronously.
   - *Disposition*: The remote worker executed completely autonomously to Epoch 30 completion, returned code 0, atomic checkpoints were verified intact, and full execution logs and history records were retrieved with zero data loss.

---

## 10. SCIENTIFIC HYPOTHESIS ASSESSMENT (VALIDATION EVIDENCE)

**Preregistered Hypothesis**:
> *"Reducing hard-negative sampling pressure over the training trajectory will test whether the observed late-epoch spatial undersegmentation can be mitigated while retaining useful false-alarm suppression."*

### Empirical Validation Findings:

#### A. Observed Facts
1. **Validation Metrics Across Trajectory**:
   - In `EXP-02B-1` (static $w_{\text{hard}} = 2.25$), Epoch 3 achieved Val IoU 0.7305, Recall 86.64%, FA 8.26% (151 tiles / 1,827). By Epoch 30, validation recall was 77.23% (failing Tier 1 qualification $\ge 79.00\%$), with Val IoU 0.7124 and FA 0.38% (7 tiles / 1,827).
   - In `EXP-02C` (annealed $w_{\text{hard}} = 2.25 \to 0.75$), validation recall was 54.73% at Epoch 9 (mid-trajectory), 82.03% at Epoch 26, and 79.27% at Epoch 30.
   - Validation global IoU was 0.4875 at Epoch 9, 0.7288 (0.72879) at Epoch 26, and 0.7153 (0.71529) at Epoch 30.
   - The predicted-to-ground-truth area ratio was 0.6251 at Epoch 9, 0.9394 at Epoch 26, and 0.8874 at Epoch 30.
   - Undersegmented tile count was 172 at Epoch 9, 244 at Epoch 26, and 315 at Epoch 30.
   - Validation GT-negative false alarms were 100.00% (Epoch 1), 2.85% (Epoch 9), 1.15% (21 tiles / 1,827 at Epoch 26), and 0.93% (17 tiles / 1,827 at Epoch 30).
2. **Marginal Alarm Count Reductions**:
   - Compared to baseline `EXP-01` (367 false alarm tiles / 1,827; 20.09%), `EXP-02C` Epoch 26 produced 21 false alarm tiles (1.15%), representing a net reduction in alarm count of 346 tiles (a 94.28% relative reduction in total false-alarm count).
   - Compared to parent `EXP-02B-1` Epoch 3 (151 false alarm tiles / 1,827; 8.26%), `EXP-02C` Epoch 26 produced 21 false alarm tiles (1.15%), representing a net reduction in alarm count of 130 tiles (an 86.09% relative reduction in total false-alarm count).
3. **Statistical Bounds on Marginal Discordance**:
   - Determining exact individually cured tiles requires exact paired tile-level contingency cell counts ($a, b, c, d$), where $b$ is the count of tiles alarmed by EXP-01 but not EXP-02C, and $c$ is the count of tiles alarmed by EXP-02C but not EXP-01.
   - In the absence of an exact paired contingency vector, the net difference is fixed by observed marginals: $b - c = 367 - 21 = 346$.
   - Evaluating across all mathematically possible values of mutual false alarms $d \in [0, 21]$ defines statistical bounds:
     - Worst-case bound ($d = 0, b = 367, c = 21, b+c = 388$): continuity-corrected $\chi^2 = 306.77, p = 1.11 \times 10^{-68}$; Wald 95% paired CI: $[17.01\%, 20.86\%]$.
     - Best-case bound ($d = 21, b = 346, c = 0, b+c = 346$): continuity-corrected $\chi^2 = 344.00, p = 8.57 \times 10^{-77}$.
   - These statistics represent mathematical bounds derived from marginal counts, not an exact paired McNemar test result.

#### B. Inferences
1. **Hypothesis Consistency**:
   - The observed EXP02C trajectory is consistent with annealed hard-negative pressure mitigating the late-epoch recall degradation observed under the static EXP02B-1 schedule.
   - The predicted-to-ground-truth area ratio increased from 0.6251 at Epoch 9 to 0.9394 at Epoch 26, coinciding with recovery in validation recall and IoU.
   - Low GT-negative false-alarm rates remained during the late qualifying epochs (1.15% at Epoch 26, 0.93% at Epoch 30).
2. **Hypothesis Verdict**:
   - **SUPPORTED (INFERENCE)**: The empirical validation measurements are consistent with the hypothesis that reducing hard-negative pressure over the training trajectory mitigates late-epoch undersegmentation while retaining false-alarm suppression. This verdict is classified strictly as an INFERENCE consistent with the observed trajectory, not a causal proof.

#### C. Unverified Mechanisms
1. **Layer-Level Discriminator Dynamics**:
   - The internal representation dynamics and gradient mechanisms governing how the network retains false-alarm suppression while expanding segmented area remain unprobed at the layer-activation and feature-space level.
2. **Generalization to Held-Out Partition**:
   - Performance on the held-out test split ($n = 2,880$ tiles) remains strictly unverified pending authorized test gate execution.

---

## 11. FINAL PRE-TEST GATE DECISION

Every strict precondition specified in the CAO Master Directive has been verified and satisfied:
- [x] Repository reality audited and unmodified
- [x] Remote Kaggle run completed with code 0 on qualified Tesla T4
- [x] All 9 critical artifacts downloaded and SHA-256 verified
- [x] Checkpoint `best_model.pt` authenticated to Epoch 26
- [x] Parameter count verified at 24,346,305 (all finite)
- [x] 30-epoch trajectory independently reconstructed
- [x] Epoch 26 independently verified as Rank 1 qualifying model
- [x] Test firewall unbreached (zero test tiles accessed)
- [x] All scientific invariants verified

### CERTIFIED GATE STATEMENT:

```
================================================================================
ALL POST-RUN SCIENTIFIC, PROVENANCE, AND CHECKPOINT GATES PASSED.
EXP-02C EPOCH 26 IS CERTIFIED AS THE OFFICIAL CANDIDATE CHECKPOINT.
TEST ACCESS: AUTHORIZED
================================================================================
```

---

## 12. SCIENTIFIC LANGUAGE CORRECTION CHANGE LOG

| Item # | Previous Phrasing / Formulation | Corrected Formulation | Scientific Rationale |
|:---:|---|---|---|
| **1** | *"cured 346 net false alarm tiles"* / uncaveated McNemar statistic | *"net reduction in alarm count of 346 tiles"* / labeled explicitly as *"marginal mathematical bounds"* | Distinguishes aggregate marginal count reductions from individually verified paired transitions ($b, c$); avoids claiming exact paired McNemar statistics when exact paired discordance data is not logged. |
| **2** | *"annealing hard-negative pressure prevented the late-epoch recall collapse"* / *"conclusively demonstrates"* | *"The observed EXP02C trajectory is consistent with annealed hard-negative pressure mitigating the late-epoch recall degradation observed under the static EXP02B-1 schedule"* | Demotes causal assertion to an inference consistent with empirical trajectory measurements; avoids overclaiming causal proof from a single comparative trajectory. |
| **3** | *"The learned discriminator features against hard-negative radar look-alikes remained robustly encoded"* | *"Low GT-negative false-alarm rates remained during the late qualifying epochs"* | Eliminates an unsupported internal representation claim; replaces with direct, measurement-grounded validation observations. |
| **4** | *"restored the model's spatial perimeter detection"* | *"The predicted-to-ground-truth area ratio increased from 0.6251 at Epoch 9 to 0.9394 at Epoch 26, coinciding with recovery in validation recall and IoU"* | Replaces interpretive spatial wording with exact quantitative area-ratio and metric measurements. |
| **5** | Ad-hoc narrative structure | Explicit tripartite separation: **Observed Facts**, **Inferences**, **Unverified Mechanisms** | Enforces strict epistemic boundaries between directly measured data, derived interpretations, and unexamined mechanistic hypotheses. |
