# EXP01 Canonical Metric Reproduction Report

**Audit Reference**: `GATE4_2P_POST_UPLOAD_FORENSIC_CLOSURE_AUDIT`  
**Execution Timestamp**: `2026-09-08T07:28:14Z`  
**Working Directory**: `D:\Projects\ocean-sentinel`  
**Evaluator**: Implementation Engineer under Ocean Sentinel CAO Governance  
**Script Executed**: `experiments/performance/gate4_2P_post_upload_forensic_audit_20260908_070310/reproduce_exp01_eval.py`  
**Target Checkpoint**: `experiments/exp01_baseline/best_model.pt`  
**Checkpoint SHA-256**: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`  
**Reproduction Decision**: **CERTIFIED NUMERICAL PARITY (PASS)**  

---

## 1. Executive Summary

Without altering or mutating any canonical EXP-01 baseline artifact, the full evaluation pipeline was re-executed using the authoritative checkpoint `best_model.pt` against the certified spatial split manifest `data/metadata/trujillo_2024/spatial_split_manifest.json`.

All metrics reproduced the certified baseline values within numerical floating-point precision ($\Delta < 0.000004$).

---

## 2. Reproduction Pipeline Configuration

- **Model Architecture**: `ResNet34UNet`
- **Parameter Count**: `24,346,305` total & trainable (`0` non-trainable)
- **Input Channels**: `2` (VV, VH)
- **Output Channels**: `1` (binary raw logits)
- **Channel Adaptation**: `slice_variance_scaled` ($W' = W[:, 0:2] \times \sqrt{3/2}$)
- **Checkpoint Source**: `experiments/exp01_baseline/best_model.pt` (Epoch 4, best val IoU at 0.5 = 0.71691)
- **Dataset Manifest**: `data/metadata/trujillo_2024/spatial_split_manifest.json` (SHA-256: `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0`)
- **Normalization Used**:
  - `channel_means`: `[-33.233136989478695, -19.941215852796695]`
  - `channel_stds`: `[6.489985665955077, 4.531345684833188]`
  - Provenance: strictly computed from all 840 train patches ($3,523,215,360$ valid pixels)
- **Binarization Threshold**: **FROZEN AT `0.22`** (strictly non-tuned, zero test leakage)
- **Loss Formulation**: `CombinedBCEAndDiceLoss` (`bce_weight=0.5, dice_weight=0.5, smooth=1.0`)
- **Hardware Acceleration**: `NVIDIA GeForce RTX 3050 Laptop GPU` (`cuda:0`)
- **Precision**: `CUDA FP16` (`torch.amp.autocast('cuda')`)
- **DataLoader**: Batch size 16, 4 workers, pin_memory=True

---

## 3. Reproduced Metrics vs. Certified Baseline

### Validation Split Evaluation (2,880 Tiles, 180 Patches)
- **Evaluation Duration**: 43.13 seconds
- **Tiles Evaluated**: 2,880
- **Threshold**: 0.22 (frozen)
- **Validation Loss**: `0.38564`

| Metric | Reproduced Value | Certified Value | Absolute Delta | Percentage Match | Status |
| :--- | :--- | :--- | :--- | :--- | :-: |
| **Validation IoU** | `0.722314` | `0.722310` | `+0.000004` | `99.999%` | **MATCH** |
| **Validation Dice** | `0.838771` | `0.838771` | `+0.000000` | `100.000%` | **MATCH** |
| **Validation Precision** | `0.851382` | `0.851382` | `+0.000000` | `100.000%` | **MATCH** |
| **Validation Recall** | `0.826529` | `0.826529` | `-0.000000` | `100.000%` | **MATCH** |

### Test Split Evaluation (2,880 Tiles, 180 Patches)
- **Evaluation Duration**: 42.02 seconds
- **Tiles Evaluated**: 2,880
- **Threshold**: 0.22 (frozen)
- **Test Loss**: `0.37854`

| Metric | Reproduced Value | Certified Value | Absolute Delta | Percentage Match | Status |
| :--- | :--- | :--- | :--- | :--- | :-: |
| **Test IoU** | `0.784344` | `0.784340` | `+0.000004` | `99.999%` | **MATCH** |
| **Test Dice** | `0.879140` | `0.879140` | `-0.000000` | `100.000%` | **MATCH** |
| **Test Precision** | `0.817131` | `0.817130` | `+0.000001` | `100.000%` | **MATCH** |
| **Test Recall** | `0.951333` | `0.951330` | `+0.000003` | `100.000%` | **MATCH** |

---

## 4. Confusion Matrix Raw Pixel Counts (Test Set)

- **True Positives (TP)**: `30,757,854` pixels
- **False Positives (FP)**: `6,883,423` pixels
- **False Negatives (FN)**: `1,573,471` pixels
- **True Negatives (TN)**: `715,759,972` pixels
- **Total Pixels Evaluated**: $2,880 \times 512 \times 512 = 754,974,720$ pixels
- **Sum Verification**: $30,757,854 + 6,883,423 + 1,573,471 + 715,759,972 = 754,974,720$ (**Exact match**)

---

## 5. Certification Confirmation

1. **Zero Artifact Mutation**: `best_model.pt`, `final_model.pt`, `config.json`, `history.json`, and `spatial_split_manifest.json` remain byte-for-byte identical to their pre-audit hashes.
2. **Zero Test Threshold Tuning**: The test set was evaluated strictly once at the frozen threshold of `0.22`.
3. **Parity Certified**: The observed difference of $\pm 0.000004$ is attributable solely to floating-point rounding across CUDA tensor operations.
4. **Final Decision**: **REPRODUCTION CERTIFIED PASS**.
