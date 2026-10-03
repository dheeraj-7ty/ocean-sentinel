# PHASE 5C EXP-04 HYPOTHESIS AND TRAINING CONTRACT
**Project:** Ocean Sentinel  
**Authority:** CAIO Scientific Governance  
**Document ID:** PHASE_5C_EXP04_CONTRACT_20260911  
**Date:** 2026-09-11  
**Status:** PREREGISTERED & FROZEN (TRAINING NOT AUTHORIZED)  

---

## 1. EXP-03 Empirical Findings Summary

EXP-03 evaluated fine-tuning the canonical EXP-01 baseline checkpoint with hard-negative mining at a $12.5\%$ exposure rate (2 mined empty tiles + 14 standard tiles per batch of 16) over 10 epochs.
* **Authoritative Trajectory Metrics (Best Validation IoU at Epoch 9):**
  - **Val Loss:** $0.00977$
  - **IoU:** $0.70435$ (EXP-01 baseline: $0.71691$, gate: $\ge 0.71731$) $\longrightarrow$ **FAIL** ($-1.75\%$ relative)
  - **Dice:** $0.82653$ (EXP-01 baseline: $0.83512$) $\longrightarrow$ ($-1.03\%$ relative)
  - **Precision:** $0.88820$ (EXP-01 baseline: $0.85138$) $\longrightarrow$ ($+3.68$ pp gain)
  - **Recall:** $0.77287$ (EXP-01 baseline: $0.78488$, gate: $\ge 0.80000$) $\longrightarrow$ **FAIL** ($-1.53\%$ relative)
  - **Clean-Water FAR:** $0.33\%$ (EXP-01 baseline: $20.09\%$, gate: $< 20.09\%$) $\longrightarrow$ **PASS** ($-98.4\%$ relative)
  - **Significant FAR:** $0.33\%$ (EXP-01 baseline: $10.56\%$, gate: $< 10.56\%$) $\longrightarrow$ **PASS** ($-96.9\%$ relative)
  - **Total FP Pixels:** $79,742$ (EXP-01 baseline: $2,327,942$, gate: $< 2,327,942$) $\longrightarrow$ **PASS** ($-96.6\%$ relative)

* **Prediction-Mass Forensic Findings:**
  - Tiles with predicted positive pixels dropped from $1,361$ to $826$ out of $1,053$ ground-truth positive validation tiles.
  - **$227$ ground-truth positive tiles suffered complete dropout** (predicted 0 positive pixels in EXP-03 vs. positive detections in EXP-01).
  - Total predicted positive pixel mass shrank by $10.4\%$ (from $15,668,391$ to $14,043,861$ pixels).
  - False Negative pixels increased from $2,798,401$ to $3,664,417$ ($+866,016$ pixels, $+30.9\%$).

---

## 2. Exact Failure / Gate Analysis

| Metric | EXP-01 Baseline | EXP-03 Observed | EXP-03 Gate | Gate Status | Cause of Failure |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Validation IoU** | $0.71691$ | $0.70435$ | $\ge 0.71731$ | **FAIL** | Boundary shrinkage & positive tile dropout |
| **Validation Recall** | $0.78488$ | $0.77287$ | $\ge 0.80000$ | **FAIL** | Excessive suppression of low/medium-confidence oil pixels |
| **Clean-Water FAR** | $20.09\%$ | $0.33\%$ | $< 20.09\%$ | **PASS** | Vast suppression of ocean clutter false alarms |
| **Significant FAR** | $10.56\%$ | $0.33\%$ | $< 10.56\%$ | **PASS** | Elimination of multi-component clean-water false alarms |
| **Total FP Pixels** | $2,327,942$ | $79,742$ | $< 2,327,942$ | **PASS** | $96.6\%$ reduction in false positive mass |

**Scientific Interpretation:** EXP-03 succeeded operationally and scientifically proved that hard-negative mining powerfully suppresses false alarms. However, at $12.5\%$ exposure (2 mined tiles every batch), the negative gradient penalty was excessively strong, penalizing borderline features and collapsing subtle slicks.

---

## 3. Primary Scientific Hypothesis (EXP-04)

> **Hypothesis H-04:**  
> Reducing the hard-negative exposure rate by 50%—from 2 mined tiles per batch ($12.5\%$) to 1 mined tile per batch ($6.25\%$) while holding the total batch size constant at 16 tiles ($15\text{ standard} + 1\text{ mined}$)—will reduce negative gradient pressure sufficiently to recover validation Recall ($\ge 0.78500$) and IoU ($\ge 0.71731$) toward baseline non-inferiority, while preserving at least $75\%$ of the false-alarm reduction achieved in EXP-03 (Clean-Water FAR $< 5.0\%$, Significant FAR $< 3.0\%$, Total FP Pixels $< 350,000$).

---

## 4. One Selected Intervention

* **Selected Intervention:** **Halved Hard-Negative Batch Exposure Rate (6.25% mined stream).**
* **Rationale:** This is the minimal, most direct single-variable intervention. It alters zero data manifests, zero loss formulations, zero optimizer settings, zero architectures, and zero thresholds. It directly tests the exposure-rate dose-response curve between $0\%$ (EXP-01), $6.25\%$ (EXP-04), and $12.5\%$ (EXP-03).

---

## 5. Exact Variable Change

* **EXP-03 Formulation:**
  $$\text{Batch Composition} = 14 \text{ Standard Train Tiles} + 2 \text{ Mined Candidate Tiles} = 16 \text{ tiles } (12.5\% \text{ mined})$$
  $$\text{Batches per Epoch} = 13,440 / 14 = 960 \text{ batches}$$
  $$\text{Mined exposures per epoch} = 960 \times 2 = 1,920 \text{ tile evaluations}$$

* **EXP-04 Formulation (THE SOLE VARIABLE):**
  $$\text{Batch Composition} = 15 \text{ Standard Train Tiles} + 1 \text{ Mined Candidate Tile} = 16 \text{ tiles } (6.25\% \text{ mined})$$
  $$\text{Batches per Epoch} = \lfloor 13,440 / 15 \rfloor = 896 \text{ batches}$$
  $$\text{Mined exposures per epoch} = 896 \times 1 = 896 \text{ tile evaluations}$$

$$\Delta \text{ Exposure} = -50.0\% \text{ per batch}, \quad -53.3\% \text{ total mined exposures per epoch}$$

---

## 6. All Frozen Variables

To guarantee strict scientific control, all other parameters remain **FROZEN AND IMMUTABLE**:

| Category | Parameter | Frozen Value / Identity |
| :--- | :--- | :--- |
| **Model Architecture** | Backbone & Head | `ResNet34UNet(in_channels=2, num_classes=1, adaptation_method="slice_variance_scaled")` |
| **Trainable Weights** | Count | Exactly $24,346,305$ trainable parameters |
| **Buffers** | Count | Exactly $19,054$ non-trainable buffers |
| **Initial Weights** | Teacher Checkpoint | `experiments/exp01_baseline/best_model.pt` (SHA-256 `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`) |
| **Candidate Pool** | Manifest | `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json` (SHA-256 `3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4`) |
| **Data Split** | Manifest | `data/metadata/trujillo_2024/spatial_split_manifest.json` (SHA-256 `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0`) |
| **Loss Function** | Formulation | `CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0)` |
| **Optimizer** | Type & Settings | `AdamW(lr=1e-4, weight_decay=1e-2)` |
| **Learning Rate Schedule** | Type & Settings | `CosineAnnealingLR(optimizer, T_max=10, eta_min=1e-6)` |
| **Epochs** | Count | Exactly $10$ epochs |
| **Batch Size** | Total Tiles | Exactly $16$ tiles ($512 \times 512$, 2-channel) |
| **Random Seed** | Determinism | Seed = $42$ (`torch.manual_seed(42)`, deterministic sampler) |
| **Operating Threshold** | Inference $\tau$ | Strictly $\tau = 0.22$ |
| **Normalization** | Channel Stats | Pre-computed training split statistics (VV mean/std, VH mean/std in dB) |
| **Data Augmentations** | Policy | Random horizontal flip ($p=0.5$), random vertical flip ($p=0.5$) |
| **Validation Split** | Tile Set | Canonical 2,880 Part I validation tiles evaluated deterministically at epoch end |
| **Part III Isolation** | Firewall | Absolute zero access to Trujillo Part III data or references |

---

## 7. Dataset Definition

* **Source:** Trujillo et al. (2024) Sentinel-1 SAR imagery.
* **Standard Training Stream:** 13,440 tiles from the canonical development TRAIN split ($512 \times 512$ pixels, 2 bands: VV and VH in dB).
* **Validation Stream:** 2,880 canonical validation tiles from the spatial validation split (1,053 positive tiles, 1,827 empty tiles).

---

## 8. Candidate Definition

* **Hard-Negative Pool:** The frozen 400-tile manifest harvested from the TRAIN split under EXP-01 baseline false-positive analysis.
* **Integrity Constraint:** Candidates are 100% pure clean-water tiles (0 ground-truth oil pixels) from 273 unique parent scenes, capped at $\le 2$ tiles per parent scene.

---

## 9. Sampler Definition

* **Class:** `TwoStreamBatchSampler(n_standard=13440, n_mined=400, n_standard_per_batch=15, n_mined_per_batch=1, seed=42)`.
* **Standard Stream:** Shuffled permutation of $13,440$ indices sampled without replacement ($15 \times 896 = 13,440$). Every standard tile is seen exactly once per epoch.
* **Mined Stream:** Deterministically sampled with replacement from $[0, 400)$ using seed $42 + \text{epoch}$. Exactly $1$ mined tile per batch ($896$ total mined draws per epoch).

---

## 10. Loss Function

* `CombinedBCEAndDiceLoss`:
  $$\mathcal{L}(y, \hat{y}) = 0.5 \cdot \text{BCEWithLogitsLoss}(y, \hat{y}) + 0.5 \cdot \text{DiceLoss}(y, \sigma(\hat{y}))$$
  with Laplace smoothing $\epsilon = 1.0$.

---

## 11. Optimizer

* `torch.optim.AdamW`:
  - Learning rate: $\eta = 1.0 \times 10^{-4}$
  - Weight decay: $\lambda = 1.0 \times 10^{-2}$
  - Betas: $(0.9, 0.999)$, eps: $1.0 \times 10^{-8}$

---

## 12. Scheduler

* `torch.optim.lr_scheduler.CosineAnnealingLR`:
  - $T_{\max} = 10$ epochs
  - $\eta_{\min} = 1.0 \times 10^{-6}$

---

## 13. Epochs

* Exactly $10$ epochs ($8,960$ total optimizer steps).

---

## 14. Seed & Determinism

* Seed: $42$.
* `torch.manual_seed(42)`, `torch.cuda.manual_seed_all(42)`, `np.random.seed(42)`, `random.seed(42)`.
* Deterministic CUDA operations enabled where possible.

---

## 15. Validation Protocol

* Validation is executed at the end of every epoch across all $2,880$ canonical validation tiles.
* Evaluated at threshold $\tau = 0.22$.
* Metrics accumulated via canonical `SegmentationMeter` using `.compute()`.
* Must evaluate: `val_loss`, `val_iou`, `val_dice`, `val_precision`, `val_recall`, `clean_water_far_pct`, `significant_far_pct`, `total_fp_pixels`.

---

## 16. Threshold

* Canonical threshold remains strictly **$\tau = 0.22$**.
* Post-hoc threshold tuning is strictly prohibited for model selection.

---

## 17. Success / Failure Gates for EXP-04

To pass acceptance, EXP-04 must satisfy **BOTH** the Primary Objective and the Guardrail Objective at its best validation IoU epoch:

### Primary Objective: Non-Inferiority Recovery
1. **Validation IoU Gate:** $\text{Val IoU} \ge 0.71731$ (Canonical non-inferiority bound).
2. **Validation Recall Gate:** $\text{Val Recall} \ge 0.78500$ (Matches or exceeds EXP-01 baseline $0.78488$).

### Guardrail Objective: False Alarm Retention
3. **Clean-Water FAR Gate:** $\text{Clean-Water FAR} < 5.00\%$ (EXP-01 baseline was $20.09\%$, EXP-03 was $0.33\%$).
4. **Significant FAR Gate:** $\text{Significant FAR} < 3.00\%$ (EXP-01 baseline was $10.56\%$, EXP-03 was $0.33\%$).
5. **Total FP Pixels Gate:** $\text{Total FP Pixels} < 350,000$ (EXP-01 baseline was $2,327,942$, EXP-03 was $79,742$).

### Overall Acceptance Rule
* **PASS:** Both Primary and Guardrail Gates satisfied.
* **FAIL:** Any Primary or Guardrail Gate breached.

---

## 18. Expected Outcomes

* **Expected IoU:** $\sim 0.718 - 0.722$ (slight gain due to false positive reduction without excessive boundary shrinkage).
* **Expected Recall:** $\sim 0.785 - 0.792$ (recovery from EXP-03's $0.77287$).
* **Expected Clean-Water FAR:** $\sim 1.0\% - 3.5\%$ (slight increase from EXP-03's $0.33\%$, but vastly below baseline $20.09\%$).
* **Expected Total FP Pixels:** $\sim 150,000 - 300,000$ (retaining $87\% - 93\%$ false positive suppression vs. EXP-01).

---

## 19. Stop Conditions & Abort Criteria

Training must immediately halt if any of the following occur:
1. `train_loss` or `val_loss` becomes `NaN` or `Inf`.
2. GPU Out of Memory error occurs.
3. Checkpoint write transaction fails or leaves a corrupt file.
4. Part III path or data access is detected by the firewall.
5. Disk space falls below $5\text{ GB}$.

---

## 20. Contingency Handling

If EXP-04 passes Guardrail Gates but fails Primary IoU/Recall recovery:
* The hypothesis is rejected: simple uniform exposure reduction is insufficient.
* Backup Candidate B (Annealed exposure: start at 1 mined tile and decay) or Backup Candidate E (Candidate severity capping: filter out whole-tile $\ge 50,000$ FP candidates) will be preregistered for EXP-05.

---

## 21. No-Post-Hoc-Tuning Rule

* All evaluation is performed strictly at $\tau = 0.22$.
* Model selection is determined solely by the epoch with highest validation IoU.
* No sweep over learning rates, batch compositions, or loss weights is permitted post-hoc.

---

## 22. Part III Scientific Firewall

* Trujillo Part III data remains strictly **CLOSED**.
* Under no circumstances may any Part III file, patch, or reference be imported, inspected, trained upon, or evaluated during Phase 5C.
* Any contact with Part III invalidates the experiment.

---

## 23. Observability Requirements

The training script must maintain:
* Continuous real-time updates to `experiments/performance/exp04_half_hard_neg/run_state.json`.
* Persistent fields: `pid`, `epoch`, `batch`, `total_batches` ($896$), `phase`, `status`, `elapsed_seconds`, `eta_seconds`, `last_heartbeat_iso`.
* Explicit stdout batch progress logging every $20$ batches.

---

## 24. Checkpoint Requirements

* Checkpoints saved atomically via temporary file and `os.replace`.
* Checkpoints to persist:
  - `best_model.pt`: Checkpoint achieving the highest validation IoU.
  - `last_model.pt`: Checkpoint at completion of Epoch 10.
* Each checkpoint must contain: `epoch`, `model_state_dict`, `optimizer_state_dict`, `val_metrics`, `config`.

---

## 25. Reproducibility Requirements

* Environment: Python 3.10.9 in project venv (`D:\Projects\ocean-sentinel\venv`).
* PyTorch 2.5.1+cu124, torchvision 0.20.1+cu124.
* Hardware: NVIDIA RTX 4070 Laptop GPU (8GB VRAM).
* Deterministic seeding: seed 42.
* Independent verification script matching EXP-03 protocol (Windows safe, `num_workers=0`, `if __name__ == '__main__':`) to be run post-training.

---

## 26. Authorization Status

$$\text{EXP04\_TRAINING\_AUTHORIZATION} = \mathbf{NOT\_GRANTED}$$
**Strict Hard Stop:** No model training, no optimizer steps, and no checkpoints are permitted until explicit CAIO authorization.
