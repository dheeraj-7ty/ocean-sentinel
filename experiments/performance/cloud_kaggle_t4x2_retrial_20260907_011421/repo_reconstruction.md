# Gate 3.1 — State Reconstruction & Problem Diagnosis

**Timestamp**: 2026-09-06T19:44:21Z  
**Audit Directory**: `experiments/performance/cloud_kaggle_t4x2_retrial_20260907_011421/`  
**Authority**: Ocean Sentinel Chief Architect Officer (CAO)  
**Worker**: Implementation / Validation Worker  

---

## 1. Context & Working Tree

- **Repository**: `D:\Projects\ocean-sentinel`
- **Branch**: `master`
- **HEAD Commit**: `8f444de1d0fb35d09912a9e6bf27cebde8125f0d`
- **Working Tree Integrity**: Cumulative uncommitted project files preserved. Zero commits, zero reversions.

---

## 2. Canonical EXP-01 Baseline (Repository Facts)

- **Architecture**: `ResNet34UNet` (`src/ocean_sentinel/ml/unet_resnet.py`)
- **Parameter Count**: Exactly 24,346,305 parameters (all trainable)
- **Input Contract**: 2-channel SAR (VV, VH) in dB, `[B, 2, 512, 512]`, float32
- **First-Layer Adaptation**: `slice_variance_scaled` ($W' = W[:, 0:2] \times \sqrt{3/2}$)
- **Output Contract**: Single raw logit channel, `[B, 1, 512, 512]`, float32
- **Loss**: `CombinedBCEAndDiceLoss` ($0.5 \times \text{BCE} + 0.5 \times \text{SoftDice}$, smooth=1.0)
- **Optimizer**: AdamW (`lr=1e-4`, `weight_decay=1e-2`, `eps=1e-8`)
- **Precision**: CUDA AMP FP16
- **Scheduler**: Canonical pure `CosineAnnealingLR` without warmup
- **Spatial Partition**: 840 train scenes / 180 val scenes / 180 test scenes (13,440 / 2,880 / 2,880 tiles)

---

## 3. Diagnosis of Gate 3.1 Incident

### Observed Symptom
When executing inside the Kaggle notebook/Jupyter kernel on **GPU T4 x2**, the probe terminated prematurely before running tests, logging:
```text
usage: capability_probe.py [-h] [--target {LOCAL,KAGGLE}] [--output OUTPUT]
capability_probe.py: error: unrecognized arguments: -f /root/.local/share/jupyter/runtime/kernel-....json
```

### Root Cause
1. In Jupyter notebook environments, the ipykernel runner automatically passes `-f <kernel_connection_file>` to the Python process.
2. In `capability_probe.py`, argument parsing was implemented using strict `parser.parse_args()`.
3. Because `-f` was not an explicitly registered argument, `parse_args()` raised `SystemExit(2)` and printed the usage error.
4. **Crucial Finding**: This error occurred before any CUDA call. It is purely a CLI/Jupyter argument integration mismatch and **NOT** evidence of hardware, driver, or CUDA failure.

---

## 4. Remediation Architecture

1. Replace `parser.parse_args()` with `parser.parse_known_args()`.
2. Explicitly inspect any unknown arguments:
   - If unknown arguments exist (such as `-f <kernel_connection_file>`), record them in the report under `ignored_jupyter_args` inside `probe_metadata`.
   - Log them clearly to stdout.
3. Keep all probe mechanics, CUDA smoke tests, synthetic ResNet34UNet tests, filesystem inspections, and package checks 100% identical.
4. Verify the updated script locally first, including testing `--help`, `--target LOCAL`, and passing dummy `-f dummy.json` to prove argument tolerance.
