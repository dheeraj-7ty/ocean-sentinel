# Ocean Sentinel — Permanent Task-Closure Protocol & Reusable Validation Check

## Purpose & Mandate
Under Ocean Sentinel CAO governance, every implementation and hardening task must run and pass the automated closure check before declaring the task complete. No task may finish while a task-introduced error remains unresolved.

## Reusable Validation Script
**Path**: `experiments/performance/pre_upload_zero_defect_hardening_20260907_042853/task_closure_check.py`

### How to Run
From the repository root (`D:\Projects\ocean-sentinel` on Windows, or `/kaggle/working/ocean-sentinel` on Linux/Kaggle):

```bash
# Windows
venv\Scripts\python.exe experiments/performance/pre_upload_zero_defect_hardening_20260907_042853/task_closure_check.py

# Linux / Kaggle
python3 experiments/performance/pre_upload_zero_defect_hardening_20260907_042853/task_closure_check.py
```

### Checks Executed by `task_closure_check.py`
1. **Syntax & Bytecode Compilation**: Runs `compileall` across `src/`, `scripts/`, and `tests/` ensuring 0 syntax errors.
2. **Critical Imports**: Verifies importability of PyTorch, Torchvision, Rasterio, PIL, NumPy, and all `ocean_sentinel` ML/ingestion modules.
3. **Model Construction & Parameter Count**: Instantiates canonical `ResNet34UNet` (2-channel in, 1-channel out, `slice_variance_scaled`) and verifies exact parameter counts (`24,346,305` total, `24,346,305` trainable).
4. **Canonical Loss Construction**: Validates `CombinedBCEAndDiceLoss` with exact 50/50 weighting (`bce_weight=0.5, dice_weight=0.5, smooth=1.0`).
5. **Synthetic Pipeline**: Tests synthetic forward pass (`shape [2, 1, 512, 512]`), loss computation, backward pass, and verifies strictly finite gradients under AMP FP16.
6. **Checkpoint Round-Trip**: Writes synthetic checkpoint atomically, verifies SHA-256 hash, reloads via `torch.load(..., weights_only=True)`, and confirms restored inference matches original predictions within numerical tolerance (`1e-5`).
7. **Manifest Integrity & Split Counts**: Validates `spatial_split_manifest.json` ensuring 1,200 patches (840 train, 180 val, 180 test), 19,200 tiles (13,440 train, 2,880 val, 2,880 test), and presence of training-derived normalization stats.
8. **Real-TIFF Data Loader Smoke Test**: Loads 1 real GeoTIFF sample pair via `TrujilloTileDataset`, validating tensor contract (`[2, 512, 512]` float32 image, `[1, 512, 512]` float32 mask with binary values `{0, 1}`).
9. **Kaggle Portability (`data_root`)**: Simulates a POSIX `/kaggle/input/ocean-sentinel-trujillo-corpus` layout and verifies that `data_root` redirection correctly resolves without Windows drive letters.
10. **Jupyter Kernel Argparse Resilience**: Tests `train_exp01.py` argument parsing with simulated `-f /root/.local/share/jupyter/runtime/kernel-*.json` arguments to prevent Jupyter notebook kernel injection crashes.

## Mandatory Self-Healing Protocol
If any check fails:
1. Determine if failure was caused by the current task.
2. If YES: Repair the source code or test harness immediately.
3. Re-run the specific failing check.
4. Re-run `task_closure_check.py`.
5. Re-run existing unit tests (`pytest tests/test_exp01_eval.py`, `pytest tests/test_dataset_pipeline.py`, `pytest tests/test_ml_components.py`).
6. Repeat until all checks pass cleanly.
7. Document the error and repair in `closure_audit.md`.
