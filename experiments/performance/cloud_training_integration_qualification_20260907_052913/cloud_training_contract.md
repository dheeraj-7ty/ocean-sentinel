# Ocean Sentinel — Cloud Training Contract

**Status**: PERMANENT BINDING CONTRACT  
**Authority**: Ocean Sentinel Chief AI Officer (CAO) Governance  
**Target Runtime**: Kaggle Cloud GPU Environments & Distributed Training Nodes  
**Canonical Experiment**: EXP-01 (Rev B: B8, accum=1, 4 workers)  

---

## 1. Canonical EXP01 Scientific Fingerprint

The scientific semantics of EXP-01 are permanently locked. Any change to these parameters constitutes an architectural deviation requiring explicit CAO sign-off.

- **Architecture**: `ResNet34UNet` with 2-channel input and 1-channel binary segmentation output.
- **Backbone**: ImageNet-pretrained ResNet-34.
- **Input Adaptation**: `slice_variance_scaled` (preserves variance of RGB weights across the 2 SAR channels).
- **Exact Parameter Counts**:
  - Total Parameters: `24,346,305`
  - Trainable Parameters: `24,346,305`
  - Non-Trainable Parameters: `0`
- **Loss Formulation**: `CombinedBCEAndDiceLoss`
  - `bce_weight = 0.5`
  - `dice_weight = 0.5`
  - `dice_smooth = 1.0`
- **Optimizer**: `AdamW(lr=1e-4, weight_decay=1e-2, betas=(0.9, 0.999), eps=1e-8)`
- **Learning Rate Scheduler**: `CosineAnnealingLR(T_max=30, eta_min=1e-6)`
- **Physical Batch Size**: `8`
- **Gradient Accumulation Steps**: `1` (Effective batch size = 8; BatchNorm operates on B=8 per step)
- **Precision**: CUDA AMP FP16 (`torch.amp.autocast('cuda')` + `torch.amp.GradScaler('cuda')`)
- **Dataset Partition**: `spatial_split_manifest.json` (SHA-256: `c052720a954c2e7a3e9a87aa64557450bf0deabec71d54c2a813849db60812e0`)
  - Train: 840 patches (13,440 tiles)
  - Validation: 180 patches (2,880 tiles)
  - Test: 180 patches (2,880 tiles)
  - Split seed: `42`
- **Data Augmentation**: Training split only: `SARGeometricAugmentation(p_hflip=0.5, p_vflip=0.5, p_rot90=0.5, seed=42)`. Validation and test splits use `IdentityTransform`.
- **Normalization**: Training-derived z-score normalization computed strictly over the 840 training patches:
  - Channel 0 Mean: `-33.233136989478695` dB, Std: `6.489985665955077` dB
  - Channel 1 Mean: `-19.941215852796695` dB, Std: `4.531345684833188` dB
- **Evaluation Protocol**:
  - Optimal threshold chosen via validation grid search in `[0.10, 0.90]` with step `0.05` on `val` split.
  - Held-out test set evaluated exactly once using the frozen validation threshold. Zero test leakage.

---

## 2. Dataset Root & Filesystem Configuration

- **Dataset Root Option**: The training runner must accept `--data-dir <PATH>` or the environment variable `OCEAN_SENTINEL_DATA_DIR`.
- **Kaggle Ingestion Mount**: Read-only FUSE mount at `/kaggle/input/ocean-sentinel-trujillo-corpus`.
- **Directory Hierarchy Expected**:
  ```text
  <data-dir>/
  ├── images/
  │   └── Oil/
  │       ├── 00001.tif ... 01200.tif
  └── masks/
      └── Mask_oil/
          ├── 00001.tif ... 01200.tif
  ```
- **Path Resolution**: `TrujilloTileDataset` rebases patch stems directly to `{data_root}/images/Oil/{stem}.tif` and `{data_root}/masks/Mask_oil/{stem}.tif`.
- **Zero Drive Letter Dependency**: No path may assume `D:\`, `C:\`, or Windows drive letters. All paths must be manipulated using `pathlib.Path` with POSIX-compatible `/` separators.

---

## 3. Kaggle Cloud Runtime Assumptions

- **Host Environment**: Ubuntu 22.04 LTS / Linux kernel 6.12+ (Kaggle Standard Container).
- **Python**: Python 3.10 to 3.12.
- **PyTorch**: PyTorch 2.1+ with CUDA 12.x backend.
- **Accelerators**: NVIDIA Tesla T4 x2 (Compute Capability 7.5, 14.9 GB VRAM per device).
- **Execution Target**: Single-node training on `cuda:0` (primary baseline).
- **DataLoader Multiprocessing**:
  - Workers: 4 workers on Kaggle (4 vCPUs allocated).
  - Memory: `pin_memory = True` when using CUDA.
  - Workers Persistence: `persistent_workers = True` when `num_workers > 0`.
  - Process Safety: Multi-worker reads must strictly scope `rasterio.open()` within `__getitem__` to prevent handle leakage across fork/spawn boundaries.

---

## 4. CLI and Jupyter Execution Contract

- **Jupyter Kernel Injection Rule**:
  Kaggle notebook environments automatically append kernel connection parameters (e.g. `-f /root/.local/share/jupyter/runtime/kernel-*.json`).
  The training entry point MUST use `parser.parse_known_args()`, cleanly filter and log any `-f` / `*.json` arguments, and proceed without termination.
- **Strict Unknown Argument Rejection**:
  Any unknown application argument that does not match the Jupyter kernel signature MUST raise a fatal CLI error (`parser.error()`) and terminate with non-zero exit code.
- **Interactive Guard**:
  Importing or loading `train_exp01.py` as a module must NOT invoke training. Training execution is restricted to explicit `main()` invocation inside `if __name__ == '__main__':`.

---

## 5. Checkpoint & Serialization Contract

- **Atomic Writes**: Checkpoint files (`best_model.pt`, `latest_checkpoint.pt`) MUST be written to a temporary filename (`*.tmp`) and renamed atomically to prevent corrupted files if preempted or killed.
- **Checkpoint Payload**:
  Checkpoints must serialize:
  1. `model_state_dict`: Complete state dictionary of `ResNet34UNet`.
  2. `optimizer_state_dict`: AdamW momentum and variance buffers.
  3. `scheduler_state_dict`: CosineAnnealingLR step counters.
  4. `scaler_state_dict`: GradScaler scaling factor.
  5. `epoch`: Integer epoch index.
  6. `val_iou`: Validation Global IoU achieved.
  7. `manifest_sha256`: SHA-256 hash of the dataset manifest used for training.
- **Deserialization Safety**:
  All checkpoint loading must use `torch.load(..., map_location=device, weights_only=True)` via `safe_load_checkpoint()`. Fallback to `weights_only=False` is strictly prohibited for untrusted or external files.
- **Immutability of Canonical Artifacts**:
  Checkpoints in `experiments/exp01_baseline/` are immutable historical baselines and must NEVER be overwritten by new runs.

---

## 6. Observability & Logging Contract

The training system must emit unbuffered, structured observability artifacts:
1. **`run_state.json`**:
   - Updated at every phase transition (`INITIALIZING`, `PREFLIGHT`, `RUNNING`, `VALIDATING`, `CHECKPOINTING`, `EVALUATING`, `COMPLETED`, `INTERRUPTED`, `FAILED`).
   - Contains real-time heartbeat timestamp `last_heartbeat_utc`.
   - On error: records `status: "FAILED"`, `failed_time_utc`, `error`, and full `traceback`.
2. **`progress.log`**:
   - Streamed to console and written to disk without buffering.
   - ISO-8601 UTC timestamps on every line (`YYYY-MM-DDTHH:MM:SSZ`).
3. **`history.json`**:
   - Flushed atomically at the end of every epoch.
   - Contains per-epoch metrics: loss, throughput (samples/sec), learning rate, validation loss, validation IoU, and epoch duration.
4. **`run.lock`**:
   - File-based mutex locking execution to a single process. Contains PID, hostname, and start time.

---

## 7. Failure Semantics & Resume Contract

- **Preflight Gate Failures**:
  If any of the 9 preflight checks fail (data loading, forward, backward, finite loss, finite gradients, optimizer step, validation pass, atomic checkpoint write/read), training terminates IMMEDIATELY before starting Epoch 1.
- **Non-Finite Loss/Gradient**:
  If non-finite loss (NaN/Inf) is encountered during training, the run terminates immediately, updates `run_state.json` with `status: "FAILED"`, and preserves the last known good checkpoint.
- **Resume Protocol**:
  - Invoked with `--resume <checkpoint_path>`.
  - Verifies that `manifest_sha256` stored in the checkpoint exactly matches the current dataset manifest. If mismatched, halts execution with fatal error.
  - Restores model weights, optimizer buffers, and scheduler learning rate. Resumes training from `epoch + 1`.

---

## 8. Prohibited Actions in Cloud Runs

1. Uploading unvalidated datasets or corrupt archives.
2. Altering spatial split definitions or tile dimensions.
3. Overriding training-only normalization with full-dataset statistics.
4. Enabling test data evaluation before validation threshold freezing.
5. Modifying model architecture without prior CAO qualification.
6. Changing batch size, accumulation steps, or optimizer parameters under the `EXP-01` label.
7. Discarding uncommitted repository work.

---

## 9. Mandatory Task-Closure Protocol

Before any future cloud implementation task is declared complete:
1. Re-inspect all modified files.
2. Run narrow unit tests on changed components.
3. Run `experiments/performance/cloud_training_integration_qualification_20260907_052913/qualification_runner.py`.
4. Run `experiments/performance/pre_upload_zero_defect_hardening_20260907_042853/task_closure_check.py`.
5. Fix every task-introduced defect before declaring completion.
