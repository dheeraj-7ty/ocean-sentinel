# Ocean Sentinel — Phase 4D Benchmark Evaluation Preflight Record

**Document Identifier:** `TRUJILLO_PART_III_PHASE_4D_PREFLIGHT_20260911`  
**Execution Phase:** Phase 4D Preflight (Pre-Inference Operational Verification)  
**Dataset Under Preflight:** Trujillo Part III (`10.5281/zenodo.13761290`, `02_Test_images_and_ground_truth.7z`)  
**Authority:** Chief Architect Officer (CAO) Mandate  
**Execution Date:** 2026-09-11  
**Baseline Git HEAD:** `542bab19f6f08c9bba8b8762e6480386c8b6026b`  
**Active Git Branch:** `master`  
**ML Forward Passes:** Exactly 0  
**Models Loaded into Predictive Models:** Exactly 0  
**Predictions Generated:** Exactly 0  
**Benchmark Metrics Generated:** Exactly 0  
**Final Preflight Status:** **`PHASE_4D_PREFLIGHT_READY_FOR_CA0_AUTHORIZATION`**  

---

## Mandatory Execution Boundary Declaration

> **"No model checkpoint was loaded into a predictive model.  
> No inference was executed.  
> No benchmark predictions were generated.  
> No benchmark performance metrics were calculated."**

---

## 1. Phase 4C Closure Confirmation

Phase 4C methodology freeze is complete, audited, and locked:
1. **Evaluation Contract Frozen:** `experiments/TRUJILLO_PART_III_EVALUATION_CONTRACT_20260911.md` is pre-specified and frozen before evaluation. All methodology decisions required for the pre-specified evaluation are frozen, with unresolved scientific uncertainties explicitly handled by the contract.
2. **Adapter Design Frozen:** `experiments/TRUJILLO_PART_III_ADAPTER_DESIGN_20260911.md` specifies a read-only, deterministic, fail-closed adapter with a 29-item security/safety threat model.
3. **Phase 4C Final Closure:** `experiments/TRUJILLO_PART_III_PHASE_4C_FINAL_CLOSURE_20260911.md` confirms completion of all micro-phases 0 through 15 with zero model forward passes and zero checkpoints loaded into predictive models.
4. **Phase 4C Automated Self-Audit:** `scratch/trujillo_part_iii_phase_4c_self_audit.json` records status `ALL_CHECKS_PASS` across all 35 checks (A through AI).

---

## 2. Threshold Confirmation

Based on direct source code inspection of `src/ocean_sentinel/ml/threshold.py` (lines 121–125), `src/ocean_sentinel/ml/metrics.py` (lines 68–74), and `src/ocean_sentinel/ml/canonical_exp01.py` (line 80):

$$\text{Model Logits } \ell \xrightarrow{\text{torch.sigmoid}} \text{Probability } p \in [0.0, 1.0] \xrightarrow{p \ge 0.22} \text{Binary Decision Mask } \hat{y} \in \{0, 1\}$$

- **Authoritative Threshold:** $\tau = 0.22$.
- **Established Domain:** **`PROBABILITY_DOMAIN_SIGMOID`** ($p \in [0.0, 1.0]$).
- **Logit-Equivalent Threshold:** $\ell_{\tau} = \ln(0.22 / 0.78) \approx -1.265666373$.
- **Preflight Verdict:** **`VERIFIED`** (recorded in `scratch/phase_4d_threshold_preflight.json`).
- **Policy:** Strictly frozen. Threshold tuning, ROC grid search, or post-hoc threshold adjustment on Trujillo Part III is strictly prohibited.

---

## 3. Checkpoint Identity (Cryptographic Integrity Verification Only)

All checkpoint identity checks were conducted via binary file inspection and SHA-256 hashing. **No checkpoint was loaded into PyTorch or instantiated as a model.**

| Model Designation | Relative File Path | File Size (Bytes) | Computed SHA-256 Checksum | Certified Baseline Reference |
|---|---|:---:|---|---|
| **Primary Baseline: EXP-01** | `experiments/exp01_baseline/best_model.pt` | $292,465,299$ | `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | `src/ocean_sentinel/ml/canonical_exp01.py:88` (Exact Match) |
| **EXP-01 Final Model** | `experiments/exp01_baseline/final_model.pt` | $292,467,835$ | `2E4C0881DF2F16810C4494A4071EAB320D12418151CC5F74651E91FE1F0A41AA` | `src/ocean_sentinel/ml/canonical_exp01.py:89` (Exact Match) |
| **EXP-01 Latest Checkpoint** | `experiments/exp01_baseline/latest_checkpoint.pt` | $292,472,299$ | `2F8F7718D687FF1621F4D92FD7190AE3D582AC67CCD2A529F72E1088A139AA6A` | `src/ocean_sentinel/ml/canonical_exp01.py:90` (Exact Match) |
| **EXP-02B-1 Hard Negative** | `experiments/performance/exp02b_1_hard_negative_training_20260909_094500/kernel_output/exp02b_1_hard_negative_training/best_model.pt` | $292,459,315$ | `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B` | Verified on Disk |
| **EXP-02C Annealed Hard Negative** | `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/best_model.pt` | $292,467,955$ | `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` | Verified on Disk |

- **Expected Architecture:** `UNet(backbone='resnet34', in_channels=2, num_classes=1)`.
- **Preflight Verdict:** **`VERIFIED`** (recorded in `scratch/phase_4d_checkpoint_identity.json`).

---

## 4. Normalization Confirmation

- **Semantic Classification:** **`FROZEN_NUMERICAL_STANDARDIZATION`**.
- **Transformation Formula:** $x_{\text{norm}}[c] = (x[c] - \mu_c) / \sigma_c$.
- **Frozen Parameters:**
  - Channel 0 (VV convention): $\mu_0 = -33.233136989478695, \quad \sigma_0 = 6.489985665955077$
  - Channel 1 (VH convention): $\mu_1 = -19.941215852796695, \quad \sigma_1 = 4.531345684833188$
- **Derivation Provenance:** Strictly derived from the 840 Part I training patches ($3,523,215,360$ pixels) in `data/metadata/trujillo_2024/spatial_split_manifest.json`.
- **Zero Adaptation Invariant:** Zero mean/std calculations or adaptations were performed on Trujillo Part III.
- **Physical Calibration Disaggregation:** The transformation is preserved strictly as a numerical model-input compatibility transformation; it does NOT establish physical units (such as dB) or calibrated radar backscatter ($\sigma^0$).
- **Preflight Verdict:** **`VERIFIED`** (recorded in `scratch/phase_4d_normalization_preflight.json`).

---

## 5. Polarization Policy

The true physical polarization channel order remains **UNKNOWN** in container metadata.

- **Pre-Specified Protocol:**
  - `MAPPING_A`: Band 1 $\rightarrow$ Model Channel 0, Band 2 $\rightarrow$ Model Channel 1.
  - `MAPPING_B`: Band 2 $\rightarrow$ Model Channel 0, Band 1 $\rightarrow$ Model Channel 1.
- **Mandatory Declaration:**
  > *"Neither mapping is asserted to represent the true physical polarization order. The two mappings constitute a pre-specified sensitivity analysis over unresolved channel-order uncertainty."*
- **Prohibitions:** Selecting a winner post-hoc by evaluation score is strictly prohibited. Both mappings must be reported side-by-side with the sensitivity gap $\Delta_{\text{polarization}}$.
- **Preflight Verdict:** **`VERIFIED`**.

---

## 6. Dataset Identity and No-Silent-Modification Verification

Exhaustive cryptographic auditing verified the physical dataset and canonical archive:
1. **Canonical Archive:**
   - Path: `data/raw/external_validation/trujillo_part_iii/02_Test_images_and_ground_truth.7z`
   - File Size: Exactly $9,859,650,011$ bytes.
   - MD5 Checksum: `5dce64cd7ff9d80189d13504bd3bcbf5` (Exact Match).
2. **Extracted Source TIFFs:**
   - 450 Image TIFFs, 450 Mask TIFFs (Total 900 files).
   - Audited against `scratch/trujillo_part_iii_extracted_sha256.json`: **900 / 900 files verified exact bitwise match**.
   - Missing files: 0. Mismatches: 0.
3. **Bijective Pairing Manifest:**
   - `scratch/trujillo_part_iii_pairing.json`: Exactly 450 pairs (150 Oil, 150 No oil, 150 Lookalike).
   - Stem rule: `stem_image == stem_mask.replace('_segmentation', '')`.
- **Preflight Verdict:** **`VERIFIED`**.

---

## 7. Array / Tiling Verification

- **Parent Scene Dimensions:** $2048 \times 2048$ pixels ($4,194,304$ pixels per raster).
- **Tile Dimensions:** $512 \times 512$ pixels ($262,144$ pixels per tile).
- **Grid Offsets:** $Y, X \in [0, 512, 1024, 1536]$ (16 non-overlapping tiles per scene).
- **Total Benchmark Tiles:** $450 \times 16 = 7,200$ tiles (2,400 Oil, 2,400 No oil, 2,400 Lookalike).
- **Geometric Accounting:** $16 \times 262,144 = 4,194,304$ pixels ($\Delta_{\text{pixels}} = 0$; zero pixel loss, zero unintended duplicate coverage).
- **Canonical Evaluation Unit:** Candidate C (Whole-Scene Reconstructed Mosaic).
- **Epistemic Distinction:**
  > *"Whole-scene reconstructed mosaic is a frozen methodological choice for this evaluation, not a claim of scientifically optimal evaluation design."*
- **Preflight Verdict:** **`VERIFIED`**.

---

## 8. Mask Verification

- **Observed Encoding:** Binary-valued $\{0, 1\}$ stored as 1-band `uint8`. Cast to `float32` $\{0.0, 1.0\}$.
- **All-Zero Masks:** Exactly 300 masks are all-zero arrays (100% of No oil and Lookalike scenes).
- **Coordinate System:** Strict array-coordinate slicing:
  $$\text{Tile\_Mask}[r, c] = \text{Scene\_Mask}[r_{\text{off}} + r, c_{\text{off}} + c]$$
- **Epistemic Labeling:** Formally termed **`target-mask foreground`** and **`target-mask background`**. Prohibited from being overclaimed as field-validated physical oil or true clean ocean.
- **Prohibitions:** Prohibit CRS reprojection, continuous resampling, inferred spatial shifts, or subpixel corrections.
- **Preflight Verdict:** **`VERIFIED`**.

---

## 9. Metric Verification & Denominator Rules

- **Oil Stratum ($N_{\text{Oil}} = 150$):** Per-scene and stratum aggregate IoU, Dice/$F_1$, Precision, Recall.
- **No Oil Stratum ($N_{\text{No\_oil}} = 150$):** False Positive Pixels ($FP$), False Positive Area Ratio ($FP / 4,194,304$), Scene-Level False Alarm Rate ($\text{FAR} = \mathbb{I}(FP > 0)$).
- **Lookalike Stratum ($N_{\text{Lookalike}} = 150$):** Lookalike False Positive Pixels, False Positive Area Ratio, Scene-Level False Alarm Rate ($\text{FAR} = \mathbb{I}(FP > 0)$).
- **Domain Coverage:** All 4 confusion matrix combinations defined; zero divide-by-zero errors.
- **Significant FAR Classification:** $FP \ge 100 \text{ pixels}$ per scene is designated **`SECONDARY DIAGNOSTIC — FIXED A PRIORI`**. Ordinary FAR ($\mathbb{I}(FP > 0)$) remains primary.
- **Prohibition on Single-Metric Pooling:** Under no circumstances shall metrics across `Oil`, `No oil`, and `Lookalike` be collapsed into a single unstratified headline mean IoU.
- **Preflight Verdict:** **`VERIFIED`**.

---

## 10. Exclusion Policy

- **Principle:** Zero outcome-based exclusions. No sample may be dropped due to poor model performance.
- **Technical Failures:** Preflight observed technical failure count is exactly 0. If an unexpected runtime failure occurs, evaluation will **BLOCK** rather than silently shrinking the denominator ($N=450$).
- **Preflight Verdict:** **`VERIFIED`**.

---

## 11. Contamination Disclosure

The official benchmark reporting incorporates the following verbatim disclosure:
> **"No exact SHA-256 content matches were detected against the audited Trujillo Part I files across 2,400 audited rasters. However, acquisition-level independence remains UNVERIFIED. Both datasets originate from the same upstream repository (Trujillo-Acatitla et al., 2024; Zenodo deposit 13761290). Shared upstream provenance exists. Trujillo Part III constitutes an external benchmark under shared repository provenance, not a fully independent sensor acquisition."**

- **Preflight Verdict:** **`VERIFIED`**.

---

## 12. Adapter Safety Preflight

`scratch/trujillo_part_iii_adapter.py` was inspected and verified:
- **Read-Only Enforced:** All file descriptors opened strictly with mode `"r"`.
- **Zero In-Place Mutation:** No write, create, or modify raster routines exist.
- **Zero Model Dependencies:** Zero imports of `torch.nn`, model architectures, or checkpoint loading code.
- **Fail-Closed:** Blocks execution upon unexpected dimensions, non-finite values, or metadata anomalies.
- **Preflight Verdict:** **`VERIFIED`**.

---

## 13. Environment Preflight

| Environment Component | Recorded Specification |
|---|---|
| **Operating System** | Windows 11 Pro (Build 26100), Shell: PowerShell 7 (`pwsh`) |
| **Python Executable** | `D:\Projects\ocean-sentinel\venv\Scripts\python.exe` (Python 3.11.9) |
| **Core Machine Learning** | PyTorch `2.14.0+cu126` (CUDA 12.6 runtime available) |
| **Geospatial Processing** | Rasterio `1.4.4` (GDAL 3.9.3 backend) |
| **Repository Baseline** | Branch `master` at commit `542bab19f6f08c9bba8b8762e6480386c8b6026b` |
| **Git Working Tree** | Clean of tracked modifications (0 staged files, 0 tracked modifications) |
| **Active Processes** | 0 predictive/inference processes, 0 competing preflight processes |
| **Locks** | 0 active lock files in `scratch/` |

---

## 14. Non-Model Data Path Dry-Run Verification

A non-model dry-run was executed via `scratch/phase_4d_preflight_runner.py`:
- **Scope:** Tested complete data ingestion pipeline from source GeoTIFFs through reading, channel mapping, normalization, tiling, and mask slicing.
- **Samples Tested:** 3 complete scenes (1 Oil: `Images/Oil/00000.tif`, 1 No oil: `Images/No oil/00000.tif`, 1 Lookalike: `Images/Lookalike/00000.tif`).
- **Channel Mappings Tested:** Both `MAPPING_A` and `MAPPING_B`.
- **Tiles Emitted:** Exactly 16 tiles per scene per mapping (total 96 tensor chip pairs).
- **Tensor Contract Verified:**
  - Image Tensor Shape: `(1, 2, 512, 512)`
  - Mask Tensor Shape: `(1, 1, 512, 512)`
  - Dtype: `torch.float32`
  - Values: 100% finite real numbers (zero `NaN`, zero `Inf`)
  - Target Mask Values: Exclusively in $\{0.0, 1.0\}$
- **Execution Firewall Maintained:** **Zero model calls, zero checkpoint loads, zero inferences.**
- **Preflight Verdict:** **`PASS`** (recorded in `scratch/phase_4d_dry_run_summary.json`).

---

## 15. Final Preflight Audit (Checks A through Z)

Automated verification suite `scratch/phase_4d_preflight_audit.py` executed cleanly:

```
==================================================
STARTING PHASE 4D PREFLIGHT AUDIT (CHECKS A - Z)
==================================================
[A_contract_frozen] PASS
[B_adapter_design_frozen] PASS
[C_threshold_domain_verified] PASS
[D_normalization_verified] PASS
[E_polarization_protocol_frozen] PASS
[F_tiling_verified] PASS
[G_mask_policy_verified] PASS
[H_metrics_verified] PASS
[I_denominator_rules_verified] PASS
[J_exclusion_rules_verified] PASS
[K_contamination_disclosure_verified] PASS
[L_checkpoint_identity_verified] PASS
[M_source_hashes_verified] PASS
[N_archive_md5_verified] PASS
[O_source_tiffs_unchanged] PASS
[P_checkpoints_unchanged] PASS
[Q_ml_forward_passes_zero] PASS
[R_models_loaded_zero] PASS
[S_predictions_generated_zero] PASS
[T_benchmark_metrics_generated_zero] PASS
[U_no_network_invoked] PASS
[V_no_locks_remain] PASS
[W_no_background_evaluation_process] PASS
[X_git_audited] PASS
[Y_no_unexplained_changes] PASS
[Z_no_methodology_contradiction] PASS
==================================================
FINAL PREFLIGHT AUDIT OVERALL: ALL_PREFLIGHT_CHECKS_PASS
Audit Report: scratch\phase_4d_preflight_audit.json
==================================================
```

---

## 16. Unresolved Scientific Uncertainties

The following properties remain intentionally unresolved and are handled by the evaluation contract:
1. **Physical Radiometric Calibration:** Metadata tags omit calibration standard ($\sigma^0/\gamma^0/\beta^0$) and units. Preserved as uncalibrated `float32`.
2. **Physical Polarization Channel Order:** Band headers are `(None, None)`. Preserved as unresolved and evaluated via dual-pass sensitivity protocol (`MAPPING_A` vs `MAPPING_B`).
3. **Acquisition-Level Sensor Independence:** SAFE product IDs absent. Shared upstream provenance disclosed.
4. **World-Coordinate Image/Mask Registration:** Handled via exact pixel array coordinates.

---

## 17. Final Preflight Status & Exact Authorization Boundary

### Final Preflight Status:
# **`PHASE_4D_PREFLIGHT_READY_FOR_CA0_AUTHORIZATION`**

Every prerequisite, data path, tensor contract, and safety constraint has been verified.

---

## 18. Absolute Hard Stop

Execution is halted at the mandatory Phase 4D preflight boundary.

**DO NOT:**
- load checkpoint weights (`best_model.pt`) into a model
- instantiate predictive model architectures
- call `model(tensor)` or execute inference
- generate prediction masks or benchmark metrics
- tune thresholds or normalization parameters

Awaiting explicit Chief Architect Officer (CAO) authorization for the first model forward pass.
