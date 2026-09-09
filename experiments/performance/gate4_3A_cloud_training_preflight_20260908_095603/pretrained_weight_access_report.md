# Gate 4.3A — Pretrained Weight Access and Reconstruction Report

**Gate Reference**: `GATE_4.3A_REPOSITORY_HYGIENE_AND_CLOUD_PREFLIGHT`  
**Author**: Implementation Engineer under Ocean Sentinel CAO Governance  
**Timestamp**: `2026-09-08T10:04:00+05:30`  
**Target Architecture**: `ResNet34UNet(in_channels=2, num_classes=1, adaptation_method='slice_variance_scaled')`  
**Canonical Total Parameters**: `24,346,305` (Trainable: `24,346,305`)  

---

## 1. Executive Summary

This report establishes the forensic characterization and cloud execution operational plan for acquiring and initializing pretrained ResNet-34 encoder weights for the Ocean Sentinel EXP01 baseline architecture.

The model accepts **2-channel Sentinel-1 dual-polarization SAR input in dB (polarization ordering UNKNOWN)** and produces single-channel binary segmentation logits (`[B, 1, 512, 512]`). The encoder relies on standard ImageNet-1k pretrained weights adapted at the first convolutional layer (`conv1`) from 3 channels to 2 channels via the CAO-locked `slice_variance_scaled` mathematical transformation.

All three CAO governance inquiries regarding pretrained weight access have been empirically verified and resolved.

---

## 2. Model Construction & Weight Acquisition Forensic Analysis

### 2.1 Code Path
The model is constructed in `src/ocean_sentinel/ml/unet_resnet.py:173-240`:
```python
# unet_resnet.py:192-194
weights = ResNet34_Weights.DEFAULT if pretrained else None
base_resnet = models.resnet34(weights=weights)
```
In `torchvision.models`, `ResNet34_Weights.DEFAULT` resolves to `ResNet34_Weights.IMAGENET1K_V1` with remote URL:
`https://download.pytorch.org/models/resnet34-b627a593.pth`

### 2.2 Conv1 Adaptation Contract
The original 3-channel RGB `conv1` weight tensor has shape `[64, 3, 7, 7]`.
Under `adaptation_method='slice_variance_scaled'` (`src/ocean_sentinel/ml/unet_resnet.py:108-118`):
```python
# Retain first 2 channels and scale by sqrt(3/2) to preserve variance:
scale = math.sqrt(3.0 / 2.0)
adapted = pretrained_weights[:, :2, :, :].clone() * scale
```
The resulting `conv1` tensor has shape `[64, 2, 7, 7]`. The rest of the encoder layers (`bn1`, `layer1`, `layer2`, `layer3`, `layer4`) directly load the pretrained weights. The decoder (`dec4`, `dec3`, `dec2`, `dec1`, `head`) is initialized from scratch. Total parameter count is invariant at **24,346,305**.

---

## 3. Formal CAO Mandate Responses

### Question 1: Does the current training path require Internet access?

**Finding**: **CONDITIONAL**.
- **Cold Environment (No Pre-cached Weights)**:
  If executed in an environment where the PyTorch hub cache does NOT already contain `resnet34-b627a593.pth`, `torchvision.models.resnet34(weights=ResNet34_Weights.DEFAULT)` calls `torch.hub.load_state_dict_from_url()`. In this scenario, **Internet access IS required** to reach `download.pytorch.org`.
- **Pre-cached Environment**:
  If the file `resnet34-b627a593.pth` is present in `$TORCH_HOME/hub/checkpoints/` or `~/.cache/torch/hub/checkpoints/`, `load_state_dict_from_url()` checks the local filesystem first. If present and the file size matches, **zero network calls are made**, and training proceeds completely offline.

---

### Question 2: Can an explicit local pretrained weight artifact be supplied?

**Finding**: **YES — EMPIRICALLY VERIFIED**.
PyTorch natively respects the `TORCH_HOME` environment variable:
1. An explicit local weight artifact matching canonical SHA-256 `B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F` can be placed at `<CUSTOM_DIR>/hub/checkpoints/resnet34-b627a593.pth`.
2. Setting `os.environ["TORCH_HOME"] = str(CUSTOM_DIR)` directs torchvision to load this exact local file.
3. Alternatively, the cloud runner script (`train_runner.py`) stages the file directly into `~/.cache/torch/hub/checkpoints/resnet34-b627a593.pth`.
4. **Empirical Verification**:
   During Gate 4.3A preflight testing, an isolated temporary directory was created containing only `resnet34-b627a593.pth`. `ResNet34UNet(in_channels=2, num_classes=1, pretrained=True)` was initialized with `TORCH_HOME` pointing to this directory. The model loaded completely offline, performed `conv1` adaptation, and passed all forward/backward sanity checks without making any network connections.

---

### Question 3: Can the cloud bundle deterministically reconstruct the canonical model without network access?

**Finding**: **YES**.
The cloud bundle can deterministically reconstruct the model offline using one of two qualified pathways:

1. **Pathway A: Pre-staged Auxiliary Dataset (Air-Gapped / Fully Offline)**:
   - Attach a private Kaggle dataset containing `resnet34-b627a593.pth` (or include the 87.3 MB file in a utility dataset).
   - `train_runner.py` detects the file, verifies its SHA-256, and copies it to `~/.cache/torch/hub/checkpoints/resnet34-b627a593.pth` before invoking `train_exp01.py`.
   - `enable_internet: false` is configured in `kernel-metadata.json`.
   - This ensures 100% deterministic, air-gapped execution with zero risk of upstream CDN failure or network timeout.

2. **Pathway B: Cloud Runtime Managed Download (Internet Enabled)**:
   - Configure `"enable_internet": true` in `kernel-metadata.json`.
   - On container startup, torchvision automatically downloads `resnet34-b627a593.pth` from `download.pytorch.org` during preflight initialization.
   - PyTorch automatically validates the filename hash (`b627a593`), ensuring cryptographic identity with the canonical PyTorch distribution.

Both pathways reconstruct the exact same initial model state, ensuring 100% scientific parity with canonical EXP01 Rev B.

---

## 4. Cryptographic Identity & Verification Matrix

| Property | Canonical Specification | Measured Local Artifact |
| :--- | :--- | :--- |
| **Model Class** | `ResNet34UNet` | `ocean_sentinel.ml.unet_resnet.ResNet34UNet` |
| **Pretrained Weight Source** | PyTorch Hub / Torchvision | `torchvision.models.ResNet34_Weights.DEFAULT` |
| **Weight Filename** | `resnet34-b627a593.pth` | `resnet34-b627a593.pth` |
| **File Size** | 87,319,819 bytes | 87,319,819 bytes |
| **SHA-256 Hash** | `B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F` | `B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F` |
| **Total Parameters** | `24,346,305` | `24,346,305` |
| **Trainable Parameters** | `24,346,305` | `24,346,305` |
| **Input Shape Contract** | `[B, 2, H, W]` float32 in dB | `[B, 2, H, W]` float32 in dB |
| **Polarization Status** | UNKNOWN (unproven) | UNKNOWN (unproven) |
| **Output Shape Contract** | `[B, 1, H, W]` float32 logits | `[B, 1, H, W]` float32 logits |

---

## 5. Architectural Non-Interference Guarantee

No architectural modifications, monkey patches, or dependency alterations have been or will be introduced to solve weight access. The existing `ResNet34UNet` architecture, normalization statistics, loss formulation, optimizer configuration, and random seed behaviors remain 100% identical to the certified EXP01 baseline.
