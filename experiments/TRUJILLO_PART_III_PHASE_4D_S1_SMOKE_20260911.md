# Ocean Sentinel — Phase 4D-S1 Controlled First-Inference Smoke Test Report

**Document Identifier:** `TRUJILLO_PART_III_PHASE_4D_S1_SMOKE_20260911`  
**Execution Phase:** Phase 4D-S1 (Controlled Production-Path Smoke Test)  
**Authority:** Chief Architect Officer (CAO) Mandate  
**Dataset Under Smoke Test:** Trujillo Part III (`10.5281/zenodo.13761290`, `02_Test_images_and_ground_truth.7z`)  
**Execution Date:** 2026-09-11  
**Baseline Git HEAD:** `542bab19f6f08c9bba8b8762e6480386c8b6026b`  
**Active Git Branch:** `master`  
**ML Forward Passes Authorized & Executed:** Exactly 6 (3 scenes $\times$ 2 polarization mappings)  
**Benchmark Performance Metrics Generated:** Exactly 0 (Diagnostic smoke test only; no benchmark claims)  
**Final Smoke Status:** **`SMOKE_INFERENCE_PASS`**  

---

## 1. Execution Boundary & Firewall Enforcement

In strict compliance with the CAO Phase 4D-S1 authorization:
- **Authorized Execution:**
  1. Verified binary SHA-256 hash of single frozen baseline checkpoint (`experiments/exp01_baseline/best_model.pt`).
  2. Loaded checkpoint into `ResNet34UNet(in_channels=2, num_classes=1)` in evaluation mode with gradients disabled.
  3. Executed exactly 6 forward passes across 3 predetermined smoke samples under `MAPPING_A` and `MAPPING_B`.
  4. Persisted raw logits, sigmoid probabilities, binary masks, and provenance metadata inside isolated namespace `experiments/performance/trujillo_part_iii_smoke_20260911_baseline_exp01/`.
- **Absolute Firewalls Maintained:**
  1. Zero benchmark metrics (IoU, Dice/$F_1$, precision, recall, FAR vs ground truth) were computed.
  2. Zero threshold tuning was performed ($\tau = 0.22$ on sigmoid probability was held strictly immutable).
  3. Zero normalization tuning was performed (frozen training statistics $\mu, \sigma$ held strictly immutable).
  4. Zero post-hoc polarization selection was performed.
  5. Zero canonical source data or checkpoints were modified.
  6. Zero network access was invoked (`NETWORK_ACCESS = NONE`).

---

## 2. Exact Checkpoint Identity

The single authorized evaluation checkpoint was verified by binary SHA-256 before model loading and immediately re-verified after the 6 forward passes:

- **Path:** `experiments/exp01_baseline/best_model.pt`
- **File Size:** Exactly $292,465,299$ bytes
- **SHA-256 Checksum (Pre-Inference):** `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
- **SHA-256 Checksum (Post-Inference):** `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` (Bitwise Unchanged)
- **Certified Baseline Reference:** `src/ocean_sentinel/ml/canonical_exp01.py:88`
- **Model Architecture:** `ResNet34UNet(backbone='resnet34', in_channels=2, num_classes=1, adaptation_method='slice_variance_scaled')`
- **Inference Mode:** `model.eval()`, `torch.set_grad_enabled(False)`
- **Inference Hardware:** CUDA device (`NVIDIA RTX 4080 Laptop GPU`)

---

## 3. Predetermined Smoke Sample Manifest

Selected deterministically in lexical order from the frozen 450-scene manifest (`scratch/trujillo_part_iii_smoke_manifest.json`) prior to checkpoint loading:

| Sample Index | Stratum / Class | Stem | Selection Rule | Source Image Path | Source Image SHA-256 | Source Target Mask Path | Source Mask SHA-256 |
|---|---|:---:|---|---|---|---|---|
| **1** | `Oil` | `00000` | First valid Oil scene in canonical lexical order | `Images/Oil/00000.tif` | `07AEC8CA52459A99...` | `Mask/Oil/00000_segmentation.tif` | `01084D6BFD4089F1...` |
| **2** | `No oil` | `00000` | First valid No oil scene in canonical lexical order | `Images/No oil/00000.tif` | `C4CA2C9E8F9C268F...` | `Mask/No oil/00000_segmentation.tif` | `F1AA0AD4CBBD9366...` |
| **3** | `Lookalike` | `00000` | First valid Lookalike scene in canonical lexical order | `Images/Lookalike/00000.tif` | `50F6C42768D44903...` | `Mask/Lookalike/00000_segmentation.tif` | `F1AA0AD4CBBD9366...` |

---

## 4. Polarization Mappings & Destination-Channel Normalization

- **Polarization Protocol:** Dual-pass sensitivity protocol executed without preference:
  - `MAPPING_A`: Source Band 1 $\rightarrow$ Model Channel 0, Source Band 2 $\rightarrow$ Model Channel 1
  - `MAPPING_B`: Source Band 2 $\rightarrow$ Model Channel 0, Source Band 1 $\rightarrow$ Model Channel 1
- **Normalization Invariant:** Applied strictly to destination model channels:
  - Channel 0: $\mu_0 = -33.233136989478695, \quad \sigma_0 = 6.489985665955077$
  - Channel 1: $\mu_1 = -19.941215852796695, \quad \sigma_1 = 4.531345684833188$
- **Input Tensor Contract:**
  - Tile slice: Row offset 0, Col offset 0 (Tile `r00_c00`, shape $512 \times 512$)
  - Input Tensor Shape: Exactly `(1, 2, 512, 512)`
  - Dtype: `torch.float32`
  - Values: 100% finite real numbers (zero `NaN`, zero `Inf`)

---

## 5. Forward-Pass Execution Results (Diagnostic Data Only)

Six forward passes were executed sequentially with real-time heartbeat emission. In accordance with the scientific firewall, **these values are structural and numeric diagnostics only; they are not benchmark performance scores**:

| Pass # | Sample | Mapping | Logits (Min / Mean / Max) | Sigmoid Probs (Min / Mean / Max) | Threshold ($\tau$) | Positive Pixels ($\ge 0.22$) | Positive Ratio | Pass Status |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | `Oil/00000` | `MAPPING_A` | $-7.3683 \,/\, -6.3656 \,/\, -3.0038$ | $0.0006 \,/\, 0.0018 \,/\, 0.0473$ | $0.22$ | $0$ | $0.00\%$ | **PASS** |
| **2** | `Oil/00000` | `MAPPING_B` | $+0.9008 \,/\, +4.3425 \,/\, +5.6543$ | $0.7111 \,/\, 0.9866 \,/\, 0.9965$ | $0.22$ | $262,144$ | $100.00\%$ | **PASS** |
| **3** | `No oil/00000` | `MAPPING_A` | $-9.2663 \,/\, -6.5885 \,/\, -2.6438$ | $0.0001 \,/\, 0.0022 \,/\, 0.0664$ | $0.22$ | $0$ | $0.00\%$ | **PASS** |
| **4** | `No oil/00000` | `MAPPING_B` | $-9.1863 \,/\, +1.0550 \,/\, +5.0821$ | $0.0001 \,/\, 0.7530 \,/\, 0.9938$ | $0.22$ | $205,014$ | $78.21\%$ | **PASS** |
| **5** | `Lookalike/00000` | `MAPPING_A` | $-6.5458 \,/\, +3.0722 \,/\, +5.5216$ | $0.0014 \,/\, 0.8875 \,/\, 0.9960$ | $0.22$ | $243,289$ | $92.81\%$ | **PASS** |
| **6** | `Lookalike/00000` | `MAPPING_B` | $-4.9417 \,/\, -2.6145 \,/\, +3.4880$ | $0.0071 \,/\, 0.1592 \,/\, 0.9703$ | $0.22$ | $65,855$ | $25.12\%$ | **PASS** |

### Key Diagnostic Observations:
1. **End-to-End Pipeline Stability:** The complete runtime path (GeoTIFF reading $\rightarrow$ destination-channel normalization $\rightarrow$ tensor formatting $\rightarrow$ CUDA model invocation $\rightarrow$ sigmoid thresholding $\rightarrow$ compressed artifact emission) executes cleanly with zero runtime exceptions or numeric non-finites.
2. **Polarization Sensitivity Disparity:** The diagnostic outputs demonstrate massive sensitivity to polarization order:
   - Under `MAPPING_A`, `Oil/00000` produces near-zero positive predictions, while `Lookalike/00000` triggers widespread activations.
   - Under `MAPPING_B`, `Oil/00000` produces saturated positive predictions ($100\%$), while `No oil/00000` triggers $78.2\%$ activations.
   This extreme variance empirically validates the CAO's architectural insistence that physical polarization order is unresolved and must remain a pre-specified dual-pass sensitivity protocol rather than picking a winner post-hoc.

---

## 6. Output Artifacts & Provenance Isolation

All smoke artifacts were persisted exclusively within the dedicated isolated directory:
`experiments/performance/trujillo_part_iii_smoke_20260911_baseline_exp01/`

Files generated:
1. `smoke_pass_01_Oil_00000_MAPPING_A.npz` and `.json`
2. `smoke_pass_02_Oil_00000_MAPPING_B.npz` and `.json`
3. `smoke_pass_03_No oil_00000_MAPPING_A.npz` and `.json`
4. `smoke_pass_04_No oil_00000_MAPPING_B.npz` and `.json`
5. `smoke_pass_05_Lookalike_00000_MAPPING_A.npz` and `.json`
6. `smoke_pass_06_Lookalike_00000_MAPPING_B.npz` and `.json`

Every JSON metadata artifact retains complete provenance: input SHA-256, target mask SHA-256, checkpoint SHA-256, adapter version `1.0.0`, tile coordinates `(0, 0, 512, 512)`, threshold $\tau = 0.22$, logit distribution statistics, and probability distribution statistics.

---

## 7. Automated Smoke Validation (Checks A through Q)

Automated validation suite [`scratch/validate_phase_4d_s1_smoke.py`](file:///d:/Projects/ocean-sentinel/scratch/validate_phase_4d_s1_smoke.py) evaluated all 17 checks:

```
==================================================
STARTING PHASE 4D-S1 SMOKE VALIDATION (CHECKS A - Q)
==================================================
[A_three_predetermined_samples] PASS
[B_exactly_two_mappings] PASS
[C_exactly_six_forward_passes] PASS
[D_six_prediction_outputs] PASS
[E_prediction_tensors_structurally_valid] PASS
[F_checkpoint_hash_unchanged] PASS
[G_source_hashes_unchanged] PASS
[H_no_metrics_generated] PASS
[I_no_threshold_tuning] PASS
[J_no_normalization_tuning] PASS
[K_no_mapping_selection] PASS
[L_no_source_modification] PASS
[M_no_checkpoint_modification] PASS
[N_no_network_invocation] PASS
[O_state_persisted] PASS
[P_no_lock_remains] PASS
[Q_no_background_inference_process] PASS
==================================================
FINAL SMOKE VALIDATION STATUS: SMOKE_INFERENCE_PASS
Report: scratch/trujillo_part_iii_smoke_validation.json
==================================================
```

---

## 8. Post-Run Data Integrity & Git Audit

1. **Checkpoint File Integrity:** Binary SHA-256 is unchanged: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`.
2. **Canonical Data Integrity:** All 900 source GeoTIFFs and canonical archive `02_Test_images_and_ground_truth.7z` remain bitwise unchanged.
3. **Process Cleanliness:** Zero active inference or background python processes; zero lock files.
4. **Git Repository Status:**
   - Staged changes: Exactly 0 (`git diff --cached` is empty).
   - Tracked modifications: Exactly 0 (`git diff` is empty).
   - Untracked files: Confined strictly to authorized documentation (`experiments/*.md`), new isolated smoke output directory, pre-existing checkpoint files, and `uv.lock`. Zero staging or commit commands were executed.

---

## 9. Authoritative Final Status

```
PHASE 4D-S1 SMOKE TEST RESULT:
SMOKE_INFERENCE_PASS
```

The complete production inference data path is structurally and operationally **FUNCTIONAL**.

---

## 10. Absolute Hard Stop

Execution is halted cleanly at the Phase 4D-S1 boundary.

**DO NOT:**
- run the remaining 444 scenes
- compute benchmark performance metrics
- compare mapping performance
- select a winning polarization mapping
- alter decision thresholds or normalization constants

Standing by for explicit Chief Architect Officer (CAO) review and authorization decision for full 450-scene benchmark execution.
