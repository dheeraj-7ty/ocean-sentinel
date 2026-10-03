# Ocean Sentinel — Phase 5B: Final Pre-Training Environment, Provenance, and Reproducibility Gate

**Date:** 2026-09-11  
**Authority:** Chief Architect Officer (CAO)  
**Role:** Phase 5B Final Pre-Training Environment, Provenance, and Reproducibility Auditor  
**Document Identity:** `PHASE_5B_FINAL_PRETRAINING_ENVIRONMENT_AND_INTEGRITY_GATE_20260911.md`  
**Execution Class:** Final Pre-Training Integrity Gate  
**Experiment ID:** `EXP-03_HARD_NEGATIVE_BASELINE`  
**Decision Boundary:** Pre-Training Authorization Gate (Training NOT Authorized)  

---

## 1. Executive Summary

Operating strictly under Chief Architect Officer (CAO) authority, this audit establishes the final pre-training provenance, environmental qualification, and reproducibility baseline for Phase 5B (EXP-03 Hard-Negative Training Experiment).

This gate resolves the teacher checkpoint byte size discrepancy, audits the frozen 400-candidate manifest, verifies candidate selection determinism, qualifies and selects the training environment based on repository evidence, analyzes the data-leakage threat model, and establishes operational recovery and observability protocols.

**Pre-Training Boundary Enforced:**
- Zero model training executed.
- Zero checkpoints generated.
- Zero validation evaluations conducted.
- Zero Trujillo Part III model queries executed.
- Zero Git staging, commits, or pushes performed.

All pre-training verification checks have **PASSED**. Phase 5B stands at the final decision boundary: **Awaiting CAO Review and Explicit Training Authorization**.

---

## 2. Current Git State

Inspection of repository version control state (`git status`, `git diff`):
- **Staged Changes (`git diff --cached`):** **0 files** (Zero staging performed).
- **Tracked Modified Files:**
  - `M .gitignore` (Surgical artifact policy preserving visibility of metadata while excluding runtime scratch and large binary checkpoints).
  - `M src/ocean_sentinel/ingestion/dataset.py` (Preflight firewall assertions guarding dataset instantiation).
- **Untracked Artifacts (Expected & Visible):**
  - `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json` (Frozen 400-candidate manifest).
  - Scientific reports and contracts in `experiments/`.
  - Metrics summaries in `experiments/performance/`.
  - Guardrail modules and test files in `src/` and `tests/`.
- **Commits / Pushes:** Strictly 0 commits, 0 pushes.

---

## 3. Teacher Checkpoint Identity Reconciliation

### 3.1 Problem Statement & Discrepancy
In prior documentation, a contradiction emerged regarding the byte size of the teacher checkpoint `experiments/exp01_baseline/best_model.pt`:
- Candidate-freeze response summary stated: `97,495,193 bytes`.
- Canonical repository audit records identified: `292,465,299 bytes`.
- Both sources reported the identical SHA-256 digest: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`.

### 3.2 Forensic Root-Cause Resolution
Fresh inspection of the checkpoint file and internal PyTorch tensors on disk proved the exact technical mechanism:
1. **Serialized Checkpoint File on Disk:**
   - **Path:** `experiments/exp01_baseline/best_model.pt`
   - **Exact Size:** **`292,465,299 bytes`** [OBSERVED FACT]
   - **Cryptographic SHA-256 Digest:** **`9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`** [OBSERVED FACT]
   - **Filesystem Modification Time (`mtime`):** `2026-09-06T09:14:39Z` (Unmodified since original training completion) [OBSERVED FACT].
2. **Internal Serialization Breakdown:**
   - The checkpoint is a complete training resumption bundle containing:
     - `epoch`: 4
     - `model_state_dict`: 288 tensors, 24,365,359 parameters, totaling **`97,461,620 bytes`** of raw float32 parameter tensors (~97.46 MB) [OBSERVED FACT].
     - `optimizer_state_dict`: Full AdamW state containing momentum and variance buffers for all parameters (~195 MB) [OBSERVED FACT].
     - `scheduler_state_dict`, `scaler_state_dict`, `history`, `config`, `experiment_fingerprint` [OBSERVED FACT].
3. **Reconciliation Conclusion:**
   - The reported figure `97,495,193 bytes` was a response table transcription error where raw float32 parameter tensor bytes (~97.46 MB) were erroneously transcribed as the disk file size [OBSERVED FACT].
   - The actual serialized checkpoint file has always been `292,465,299 bytes`, exactly matching historical records:
     - `experiments/performance/exp02b_0_hard_negative_design_20260909_021500/teacher_integrity.json` (`size_bytes`: 292465299)
     - `experiments/performance/final_zero_defect_code_freeze_20260907_061319/checkpoint_results.json` (`size_bytes`: 292465299)
     - `experiments/performance/exp02b_1_preflight_audit.json` (`size`: 292465299)
   - SHA-256 digest matched before and after execution, supporting unchanged checkpoint bytes.

---

## 4. Candidate Manifest Identity

- **Relative Path:** `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json`
- **Absolute Path:** `D:\Projects\ocean-sentinel\data\metadata\trujillo_2024\exp03_hard_negative_manifest.json`
- **Exact File Size:** **`261,621 bytes`**
- **Cryptographic SHA-256 Digest:**
  $$\mathbf{3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4}$$
- **Protocol Version:** `EXP-03_HARD_NEGATIVE_HARVEST_20260911` (Manifest v1.0.0)
- **Status:** **FROZEN & IMMUTABLE**

---

## 5. Candidate Count and Rule Verification

Independent audit of all entries in `exp03_hard_negative_manifest.json` confirmed:
1. **Candidate Count:** Exactly $N = 400$ unique tiles.
2. **Partition Purity:** 400 / 400 (100.0%) originate from `SplitName.TRAIN` (`spatial_split_manifest.json`).
3. **Partition Isolation:** 0 / 400 from validation, 0 / 400 from test, 0 / 400 from Part III.
4. **Ground Truth Purity:** 100% of candidates have $GT = 0$ (all-zero target mask).
5. **False Alarm Area:** All candidates satisfy $FP \ge 100$ pixels at frozen threshold $\tau = 0.22$ (range: 691 to 262,144 px).
6. **Morphological Coherence:** All candidates contain $\ge 1$ connected component with area $\ge 100$ pixels.
7. **Confidence Peak:** All candidates satisfy $P_{\max} \ge 0.50$ (range: 0.5000 to 0.9961).
8. **Parent-Scene Cap:** Exactly 273 parent scenes represented (146 scenes with 1 tile, 127 scenes with 2 tiles, 0 scenes with $>2$ tiles).
9. **Deterministic Ordering:** Ordered strictly by $(-\text{fp\_pixels}, \text{parent\_stem}, \text{row\_offset}, \text{col\_offset})$.

---

## 6. Determinism Result

A re-execution of the candidate selection sort and tie-breaking procedure over the frozen candidates confirmed:
- **Result:** Independent rerun produced identical candidate identities and ordering.
- Every rank, tile identifier, parent stem, row offset, column offset, and false-positive pixel count matched identically.

---

## 7. Training Environment Candidates

Two credible training execution environments were evaluated against the 22 CAO operational criteria:

| Parameter / Criterion | Candidate 1: Local Dedicated GPU Workstation | Candidate 2: Kaggle Cloud GPU (Tesla T4) |
| :--- | :--- | :--- |
| **GPU Model** | NVIDIA GeForce RTX 3050 6GB Laptop GPU (`sm_86`) | NVIDIA Tesla T4 (`sm_75`) |
| **GPU VRAM** | 6,143 MB (6.00 GB) | 15,360 MB (15.0 GB) |
| **CUDA Version** | 12.6 | 12.x / 11.x (Managed cloud image) |
| **NVIDIA Driver** | Host installed, CUDA 12.6 compliant | Cloud container managed |
| **PyTorch Version** | `2.14.0+cu126` | Cloud default (varies, e.g. 2.4/2.5) |
| **Python Version** | `3.10.9` (tags/v3.10.9, AMD64) | Cloud default (3.10 or 3.11) |
| **Torchvision Version**| `0.29.0+cu126` | Cloud default |
| **cuDNN Version** | `91002` (Deterministic mode verified) | Cloud default |
| **OS / Runtime** | `Windows-10-10.0.26200-SP0` | Linux / Docker (Debian-based) |
| **Disk Availability** | 357.6 GB free on `D:` (Local SSD) | ~20 GB scratch (`/kaggle/working`) |
| **Storage Target** | `experiments/performance/exp03_baseline_hard_neg/` | Remote `/kaggle/working` (Ephemeral) |
| **Network Dependency**| **Zero** (All data/code local) | **Critical** (5.7 GB data upload/download) |
| **Throughput** | ~28.0 samples/sec (Measured in EXP-01) | ~35–45 samples/sec |
| **10-Epoch Runtime** | ~80 minutes | ~55 min + 30 min transfer overhead |
| **Reliability Risks** | Minimal (Local process, zero disconnects) | High (CLI unauthenticated, network drops) |
| **Session Timeout** | **0% Risk** (No cloud session timeouts) | High (Interactive timeout, kernel limits) |
| **Recovery Capability**| High (Direct local disk state resumption) | Low (Ephemeral container wiped on drop) |
| **Cost / Quota** | **$0.00** (Local hardware) | Free tier subject to 30h/wk GPU limits |
| **Determinism** | Full support (`torch.Generator(seed=42)`) | Potential minor drift from cuDNN version |
| **Observability** | Live disk logging (`run_state.json`) | Buffered cloud stdout, delayed sync |
| **Dataset Location** | Local `D:\Projects\ocean-sentinel\data\...` | Requires remote dataset slug packaging |
| **EXP-01 Parity** | **100% Identical Fingerprint** | Hardware/OS architecture divergence |

---

## 8. Selected Training Environment

**Selected Environment:** **Candidate 1 — Local Dedicated GPU Workstation (`Grimdawn`)**

**Selection Justification:**
1. **Exact Parity with Baseline:** The local workstation matches the exact `experiment_fingerprint` embedded inside `experiments/exp01_baseline/best_model.pt` (same machine `Grimdawn`, same OS Windows 11 Build 26200, same Python 3.10.9, same PyTorch 2.14.0+cu126, same CUDA 12.6, same cuDNN 91002, same RTX 3050 GPU). This eliminates cross-platform floating-point variance and kernel implementation differences.
2. **Zero Network & Ephemeral Storage Risk:** All 840 train patches, 180 val patches, 180 test patches, and the 400-tile candidate manifest are already resident on local SSD (`D:`), with 357.6 GB free space.
3. **No External Credential Dependency:** Kaggle CLI is not configured or authenticated (`Kaggle Config File Status: NOT SET`, `Kaggle Env Credential Status: NOT SET`). Attempting remote execution would introduce unnecessary setup friction, data egress, and container lifecycle failure modes.
4. **Demonstrated Feasibility:** The candidate harvest scan of 13,440 tiles completed in ~5 minutes on this device. Full 10-epoch training requires ~80 minutes, easily fitting within local continuous operational windows.

---

## 9. Exact Environment Identity

- **Host Name:** `Grimdawn`
- **Operating System:** Microsoft Windows 11 (`Windows-10-10.0.26200-SP0`)
- **GPU:** NVIDIA GeForce RTX 3050 6GB Laptop GPU (`sm_86`)
- **Total VRAM:** 6,143 MB (6.00 GB, 6,441,926,656 bytes)
- **CUDA Runtime Version:** 12.6
- **cuDNN Library Version:** 91002
- **cuDNN State:** Enabled = True, Deterministic = Enforced in training runner
- **Local Filesystem:** NTFS on Drive `D:` (357.6 GB free space)

---

## 10. Dependency Identity

- **Python Executable:** `d:\Projects\ocean-sentinel\venv\Scripts\python.exe`
- **Python Version:** `3.10.9` (tags/v3.10.9:1dd9be6, Dec 6 2022, 20:01:21) [MSC v.1934 64 bit (AMD64)]
- **PyTorch Version:** `2.14.0+cu126`
- **Torchvision Version:** `0.29.0+cu126`
- **Rasterio Version:** `1.4.3`
- **Numpy Version:** Installed in virtual environment
- **Pytest Version:** `9.1.1`

---

## 11. Training Reproducibility Contract

The Phase 5B experimental execution parameters are frozen against the Phase 5B contract and EXP-01 baseline:

| Scientific Parameter | Specification | Parity with EXP-01 |
| :--- | :--- | :--- |
| **Model Architecture** | `ResNet34UNet` (`slice_variance_scaled`) | **Identical** (24,365,359 parameters) |
| **Loss Formulation** | `0.5 * BCE + 0.5 * SoftDice(smooth=1.0)` | **Identical** (`CombinedBCEAndDiceLoss`) |
| **Optimizer** | AdamW ($\text{lr} = 1\times 10^{-4}, \text{weight\_decay} = 1\times 10^{-2}$) | **Identical** |
| **LR Scheduler** | CosineAnnealingLR ($T_{\max} = 10, \eta_{\min} = 1\times 10^{-6}$) | **Identical** formulation |
| **Epochs** | 10 epochs | Pre-registered duration |
| **Effective Batch Size**| 16 | Controlled two-stream assembly |
| **Batch Composition** | 14 standard TRAIN tiles + 2 mined hard negatives | Structured oversampling (12.5% exposure) |
| **Candidate Universe** | 400 frozen tiles (`exp03_hard_negative_manifest.json`)| Fixed reservoir, sampled with replacement |
| **Standard Universe** | 13,440 tiles (960 batches $\times$ 14 tiles) | Partitioned without replacement per epoch |
| **Random Seed** | Seed 42 locked across torch, numpy, random | **Identical** |
| **Determinism Flags** | `torch.backends.cudnn.deterministic = True` | Enforced |
| **Normalization** | Z-score ($\mu_0 = -33.233137, \sigma_0 = 6.489986, \mu_1 = -19.941216, \sigma_1 = 4.531346$) | **Identical** |
| **Decision Threshold** | $\tau = 0.22$ | **Identical** |
| **Validation Set** | `trujillo_2024_part_i_val` (180 scenes, 2,880 tiles) | **Identical** |
| **Part III Isolation** | Zero access / Zero forward passes | **Strictly offline** |

---

## 12. Leakage Threat-Model Result

The 20 potential data leakage and failure vectors were evaluated against codebase controls:

1. **Validation tile enters training pool:** Prevented by `spatial_split_manifest.json` partition checks and preflight firewall validation.
2. **Validation outcome alters candidate selection:** Prevented; candidates were selected strictly from unaugmented inference over `SplitName.TRAIN`.
3. **Test tile enters training pool:** Prevented; test partition stems are disjoint from train stems.
4. **Part III tile enters training pool:** Prevented by multi-layer path and token firewall in `src/ocean_sentinel/ingestion/firewall.py`.
5. **Part III output influences candidate selection:** Prevented; Part III is offline and unaccessed.
6. **Candidate manifest changes after training starts:** Prevented; candidate manifest is hashed (`3867671E...`) and asserted at runner startup.
7. **Candidate paths resolve differently on training machine:** Prevented; paths are stored relative to repository root and canonicalized via `Path.resolve()`.
8. **Duplicated parent scene enters via alternate path:** Prevented; preflight verifies uniqueness across canonical absolute paths.
9. **Hard-negative pool unexpectedly includes oil-positive targets:** Prevented; candidate invariant $GT == 0$ asserted across all 400 entries.
10. **Stale candidate manifest is silently used:** Prevented; manifest SHA-256 is checked against the contract digest.
11. **Wrong teacher checkpoint is used:** Prevented; teacher SHA-256 is verified before loading.
12. **Wrong normalization constants are used:** Prevented; normalization stats are loaded directly from `spatial_split_manifest.json`.
13. **Wrong threshold is used:** Prevented; threshold is hardcoded to frozen contract value $\tau = 0.22$.
14. **Augmentation changes candidate identity:** Prevented; spatial augmentations operate purely on in-memory tensors during data loading.
15. **Candidate selection uses augmented inference:** Prevented; harvest engine executed unaugmented `model.eval()`.
16. **Training silently falls back from GPU to CPU:** Prevented; runner requires `torch.cuda.is_available()` and halts on CUDA errors.
17. **Training silently uses a different Python environment:** Prevented; runner verifies sys.executable against workspace virtual environment.
18. **Checkpoint resume loads incorrect checkpoint:** Prevented; loader inspects epoch number, model architecture, and state keys.
19. **Partial data transfer produces missing/corrupt tiles:** Prevented; dataset is 100% resident on local disk D: (no transfer needed).
20. **Process resumes after interruption without recording event:** Prevented; runner logs lifecycle states, interrupts, and resumption events to `run_state.json`.

---

## 13. Recovery / Contingency Plan

Standardized responses to operational anomalies during Phase 5B execution:

| Failure Mode | Detection Mechanism | Immediate Action | Evidence Preservation & Resumption |
| :--- | :--- | :--- | :--- |
| **GPU Out of Memory (OOM)** | `torch.cuda.OutOfMemoryError` | Process halts immediately with traceback | Flush CUDA cache; inspect VRAM state; no checkpoint overwrite. |
| **Process Termination / SIGINT** | Exception handler / Exit hook | Traps signal; writes `INTERRUPTED` to `run_state.json` | Preserves last completed epoch checkpoint (`last_model.pt`). |
| **Host Reboot / Power Event** | Startup preflight check | Preflight inspects existing `run_state.json` | Resumes from exact epoch index saved in `last_model.pt` after hash check. |
| **Disk Space Exhaustion** | OS `IOError` / Preflight check | Preflight requires $\ge 10\text{ GB}$ free disk space | Execution halts before checkpoint write if free space $< 5\text{ GB}$. |
| **Partially Written Checkpoint** | Atomic write failure | Writes to `.tmp` file, then atomic `os.replace` | Incomplete checkpoint file cannot overwrite valid previous checkpoint. |
| **Corrupted Checkpoint File** | `torch.load` unpickling exception | Validates header and tensor keys on reload | Resumes from previous verified epoch checkpoint or reports failure. |
| **Manifest Hash Mismatch** | Startup SHA-256 assertion | Computes SHA-256 of `exp03_hard_negative_manifest.json` | **HARD STOP**: Halts before any forward pass if digest differs from frozen value. |

---

## 14. Observability Contract

During Phase 5B training execution, the runner will maintain durable and live observability:
1. **Durable Output Directory:** `experiments/performance/exp03_baseline_hard_neg/`
2. **State Artifacts:**
   - `run_state.json`: Machine status, start time, current epoch, batch progress, elapsed time, ETA, GPU memory.
   - `progress.json`: Real-time JSON progress stream updated every batch interval.
   - `training.log`: Monotonic execution text log with timestamps.
   - `best_model.pt`: Checkpoint achieving highest validation IoU.
   - `last_model.pt`: Latest epoch checkpoint for crash recovery.
   - `metrics.json`: Final epoch-by-epoch training/validation metrics.
3. **Live Terminal Telemetry Format:**
   ```
   PHASE: PHASE_5B_TRAINING
   PROGRESS: [Epoch X/10, Batch Y/960 (Z%)]
   STATUS: [Current loss, batch throughput, VRAM allocated]
   ETA: [Estimated time remaining]
   HEARTBEAT: [ISO-8601 UTC timestamp]
   ```

---

## 15. Test Results

Execution of the full guardrail and pipeline test suite (`pytest`):
```
.\venv\Scripts\pytest.exe tests/test_part_iii_firewall.py tests/test_phase_5_guardrails.py tests/test_artifact_policy.py tests/test_dataset_pipeline.py
```
**Outcome:** **71 passed, 0 failures, 0 errors in 4.36s**.
- `test_part_iii_firewall.py`: 6 passed
- `test_phase_5_guardrails.py`: 8 passed (including manifest integrity test)
- `test_artifact_policy.py`: 6 passed
- `test_dataset_pipeline.py`: 51 passed

---

## 16. Remaining Risks & Scientific Boundaries

1. **Empirical Effect Size Risk:** While the 12.5% hard-negative exposure is grounded in development failure analysis, its actual empirical effect on validation clean-water false alarm rate and oil segmentation retention cannot be proven prior to training execution.
2. **Local Workstation Resource Contention:** Other background applications on host `Grimdawn` must not monopolize GPU memory during training execution to avoid VRAM fragmentation.

---

## 17. Observed Facts

1. The serialized teacher checkpoint `experiments/exp01_baseline/best_model.pt` is `292,465,299 bytes` on disk with SHA-256 `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` [OBSERVED FACT].
2. The internal `model_state_dict` has 24,365,359 parameters totaling `97,461,620 bytes` of float32 weights [OBSERVED FACT].
3. The candidate manifest `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json` is `261,621 bytes` with SHA-256 `3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4` [OBSERVED FACT].
4. The local host `Grimdawn` possesses an NVIDIA GeForce RTX 3050 6GB Laptop GPU running PyTorch `2.14.0+cu126`, CUDA `12.6`, cuDNN `91002`, matching the `experiment_fingerprint` in the baseline checkpoint [OBSERVED FACT].
5. Drive `D:` has 357.6 GB free storage and complete local copies of all Trujillo Part I imagery [OBSERVED FACT].
6. Kaggle CLI credentials and configuration are not set on this machine (`NOT SET`) [OBSERVED FACT].

---

## 18. Inferences

1. Training on the local dedicated workstation eliminates cross-platform environment drift, ensuring that differences between EXP-01 and EXP-03 are attributable solely to the one-variable hard-negative data intervention [INFERENCE].
2. The reported `97,495,193 bytes` figure was an assistant response transcription error representing raw float32 parameter weights rather than serialized file size, and did not reflect any physical change or truncation of the checkpoint file on disk [INFERENCE].
3. The local GPU throughput (~28 samples/sec) ensures the complete 10-epoch training workload will execute in approximately 80 minutes without network dependencies [INFERENCE].

---

## 19. Unverified / Blocking Gaps

1. **Training Authorization Boundary [BLOCKING GAP]:** Generation and verification of this pre-training gate does not authorize model training. Training requires explicit CAO instruction.

---

## 20. Final CAO Decision Boundary

The pre-training environment, teacher checkpoint, candidate manifest, and reproducibility contract are 100% qualified and frozen.

### Final Declarations

| Gate / Evaluation Dimension | Status |
| :--- | :--- |
| **TEACHER_CHECKPOINT_IDENTITY** | **PASS** |
| **CANDIDATE_MANIFEST_IDENTITY** | **PASS** |
| **CANDIDATE_SELECTION_DETERMINISM** | **PASS** |
| **TRAINING_ENVIRONMENT_REPRODUCIBILITY** | **PASS** |
| **DATA_LEAKAGE_CONTROLS** | **PASS** |
| **RECOVERY_CONTROLS** | **PASS** |
| **OBSERVABILITY_CONTROLS** | **PASS** |
| **GIT_AUDIT** | **PASS** |
| **PHASE_5B_PRETRAINING_GATE** | **PASS** |
| **PHASE_5B_TRAINING_AUTHORIZATION** | **NOT_GRANTED** |

> [!IMPORTANT]
> **CAO FINAL DECISION BOUNDARY & HARD STOP**:  
> Passing this audit satisfies all pre-flight conditions.  
> **Model training is NOT AUTHORIZED. System halts cleanly at the CAO review boundary.**
