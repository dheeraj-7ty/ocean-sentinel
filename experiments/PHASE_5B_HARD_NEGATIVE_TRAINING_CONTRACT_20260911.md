# Ocean Sentinel — Phase 5B: Hard-Negative Training Experiment Contract

**Date:** 2026-09-11  
**Authority:** Chief Architect Officer (CAO)  
**Document Identity:** `PHASE_5B_HARD_NEGATIVE_TRAINING_CONTRACT_20260911.md`  
**Status:** DRAFT PRE-REGISTRATION — AWAITING CAO AUTHORIZATION BEFORE EXECUTION  
**Execution Class:** Controlled One-Variable Intervention  
**Experiment ID:** `EXP-03_HARD_NEGATIVE_BASELINE`  

---

## 1. Scientific Objective & Rationale

In Phase 5A, empirical diagnostic evaluation of the baseline checkpoint (`experiments/exp01_baseline/best_model.pt`) on the development validation split revealed that:
1. High-false-positive validation scenes exhibit very low measured SAR backscatter (mean $-38.43\text{ dB}$, min $-50.78\text{ dB}$) and visual characteristics consistent with calm/low-wind sea conditions [OBSERVED FACT], which is consistent with reduced sea-surface roughness producing dark SAR signatures resembling oil slicks [INFERENCE]. Causal meteorological attribution is not established without independent meteorological observations [UNVERIFIED MECHANISM].
2. In the canonical Trujillo Part I dataset, 100% of parent patches (840/840 train, 180/180 val) contain confirmed oil annotations. Negative examples exist exclusively at the tile level (empty tiles inside oil-containing parent scenes) [OBSERVED FACT]. Although empty tiles already contribute negative-pixel supervision through BCE, the development analysis indicates that the baseline training distribution may provide insufficient or compositionally limited hard-negative supervision for the specific dark-water false-positive structures observed at validation.
3. The training split contains a reproducible reservoir of baseline false-positive negative tiles suitable for testing a controlled hard-negative mining intervention: 1,605 candidate tiles with $FP \ge 100$ and 528 candidate tiles with $FP \ge 1,000$ [OBSERVED FACT].

The objective of Phase 5B is to test the hypothesis that **augmenting the baseline training distribution with mined hard negatives from the training split reduces false-positive burden without degrading oil segmentation recall**, while changing **exactly ONE principal scientific variable**.

> [!IMPORTANT]
> **PRE-REGISTRATION GATE**: This document freezes all experimental parameters. No model training may commence until the Chief Architect Officer reviews and explicitly authorizes execution of Phase 5B.

---

## 2. One-Variable Scientific Boundary

To preserve strict causal attribution, Phase 5B alters exactly **ONE** variable:
$$\text{INTERVENTION: } \mathbf{\text{BASELINE}} + \mathbf{\text{TRAINING-SPLIT HARD-NEGATIVE MINING}} \quad (\Delta \mathcal{D}_{\text{train}})$$

Only training-data composition changes. Everything else remains strictly frozen:
- **Model Architecture:** Strictly identical to EXP-01 (`ResNet34UNet`, 24,346,305 parameters, `slice_variance_scaled`).
- **Loss Function:** Strictly identical to EXP-01 (`CombinedBCEAndDiceLoss`, BCE weight 0.5, Dice weight 0.5).
- **Optimization:** Strictly identical to EXP-01 (AdamW, $\text{lr} = 1\times 10^{-4}$, $\text{weight\_decay} = 1\times 10^{-2}$).
- **Learning Rate Schedule:** Strictly identical to EXP-01 (CosineAnnealingLR, $T_{\max} = 10$, $\eta_{\min} = 1\times 10^{-6}$).
- **Training Epochs & Batch Size:** 10 epochs, effective batch size 16.
- **Normalization:** Frozen destination-channel z-score standardization ($\mu_0 = -33.233137, \sigma_0 = 6.489986, \mu_1 = -19.941216, \sigma_1 = 4.531346$).
- **Decision Threshold:** Frozen at $\tau = 0.22$.
- **Validation Dataset:** Strictly identical to EXP-01 (`trujillo_2024_part_i_val`, 180 scenes, 2,880 tiles).
- **Random Seed:** Seed 42 with deterministic CUDA flags.

---

## 3. Hard-Negative Mining Specification

### 3.1 Source Isolation & Ground Truth Purity
- **Eligible Universe:** Exclusively tiles from `trujillo_2024_part_i` **Train Split** (840 parent patches / 13,440 tiles).
- **Purity Gate:** Strictly $GT = 0$ (all-zero target mask). Any tile with even 1 ground-truth positive pixel is categorically excluded.
- **Scientific Firewall:** Multi-layer firewall (`src/ocean_sentinel/ingestion/firewall.py`) enforces that zero samples from Validation Split, Test Split, or Trujillo Part III may enter the candidate pool.

### 3.2 Deterministic Candidate Criteria
A training-split empty tile qualifies as a Hard-Negative Candidate if and only if:
1. **Purity:** $GT = 0$.
2. **Baseline False Alarm Area:** $FP \ge 100$ pixels when evaluated under baseline model at frozen threshold $\tau = 0.22$ (inherited from the frozen benchmark definition of Significant False Alarm).
3. **Component Coherence:** Contains at least one connected component with area $\ge 100$ pixels (filtering out high-frequency speckle).
4. **Confidence Peak:** Maximum predicted probability on false-positive pixels exceeds $P_{\max} \ge 0.50$.

### 3.3 Deduplication & Geographic Balancing
- **Parent-Scene Capping:** To prevent training dominance by individual large low-backscatter zones (e.g. parent `01130` which contains multiple saturated tiles), a maximum of **2 candidates per parent scene** will be sampled.
- **Candidate Pool Cap:** Exactly **$N = 400$ candidates** will be selected deterministically, ranked by false-positive area.
- **Candidate Manifest:** Serialized to `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json` with SHA-256 tile hashes prior to training.

### 3.4 Batch Integration / Sampling Policy
- **Batch Composition:** In each mini-batch of size 16:
  - **14 tiles** sampled from the standard training split (spill patches + standard background).
  - **2 tiles** sampled from the mined hard-negative pool ($GT = 0$).
  - Target Label: All-zero mask ($Y = 0$).
- **A Priori Specification:** The **12.5% hard-negative exposure ratio** (2 hard-negative tiles per mini-batch of 16) was selected *a priori* as a balanced starting point.
- **Non-Optimality Acknowledgment:** The 12.5% ratio is **not claimed to be optimal** and has not been tuned against any test or validation benchmark.
- **Firewall Decoupling:** The sampling ratio **will not be altered or tuned using Trujillo Part III outcomes**, nor will Part III ever be accessed for ratio selection.
- **Composition-Only Intervention:** The first experiment changes **training-data composition only** ($\Delta \mathcal{D}_{\text{train}}$), keeping batch size, optimizer, scheduler, loss formulation, and architecture strictly identical to EXP-01.

### 3.5 HARD-NEGATIVE SAMPLING / REPRODUCIBILITY CONTRACT

This sub-contract specifies the exact, mechanically enforced rules for candidate harvesting, manifest immutability, and batch construction:

#### 3.5.1 Exact Candidate-Generation Rules
1. **Source Universe:** Exclusively `trujillo_2024_part_i` Train Split (840 parent patches / 13,440 tiles) from `data/metadata/trujillo_2024/spatial_split_manifest.json` (SHA-256: `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0`). Validation (180), test (180), and Part III (450) are strictly excluded.
2. **Teacher Checkpoint:** `experiments/exp01_baseline/best_model.pt` (SHA-256: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`).
3. **Mining Protocol:** Unaugmented evaluation (`model.eval()`, `torch.no_grad()`), canonical z-score normalization ($\mu_0, \sigma_0, \mu_1, \sigma_1$), sigmoid output probabilities, frozen binarization threshold $\tau = 0.22$.
4. **Qualification Criteria:**
   - Ground truth purity: $GT = 0$ (all pixels zero; any positive pixel triggers categorical rejection).
   - False alarm area: $FP \ge 100$ pixels at $\tau = 0.22$.
   - Coherence: At least one 8-connected component with area $\ge 100$ pixels (suppresses sensor speckle).
   - Confidence peak: $P_{\max} \ge 0.50$ on false-positive pixels.
5. **Parent-Scene Capping:** Maximum of **2 candidate tiles per parent scene** (preventing regional overfitting).
6. **Deterministic Ordering & Tie-Breaking:** Candidate tiles are sorted by:
   $$\text{order\_key} = (-\text{fp\_pixels}, \text{parent\_stem}, \text{row\_offset}, \text{col\_offset})$$
   ensuring deterministic candidate ranking regardless of execution environment or dictionary ordering.
7. **Candidate Pool Cap:** Exactly **$N = 400$ unique tiles**.
8. **Manifest Immutability & Hash Verification:** Mined candidates are serialized to `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json`. The candidate manifest is immutable and frozen as verified under CAO pre-training gate:
   - **Manifest Path:** `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json`
   - **Exact Candidate Count:** 400 unique tiles
   - **File Size:** 261,621 bytes
   - **Manifest SHA-256:** `3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4`
   - **Teacher Checkpoint SHA-256:** `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
   - **Spatial Split Manifest SHA-256:** `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0`
   - **Generation Protocol / Version:** `EXP-03_HARD_NEGATIVE_HARVEST_20260911` (Manifest v1.0.0)
   - **Date of Freeze:** 2026-09-11

#### 3.5.2 Exact Sampling Mechanics & Classification
1. **Mechanistic Classification:** **Fixed-ratio two-stream mini-batch assembly (structured negative oversampling)**.
   - *Distinction from Historical Runs:* Historical experiments (`train_exp02b_1.py`, `train_exp02c.py`) implemented hard-negative exposure via single-dataset `WeightedRandomSampler` over all 13,440 tiles. For Phase 5B EXP-03, exposure is implemented as **two-stream composite batch assembly** to guarantee exact, constant per-batch negative representation.
   - *Exposure Mechanism:* In each mini-batch of 16, exactly **14 tiles** are drawn from the standard training split (spill + background) and **2 tiles** are drawn from the mined candidate pool. It is not unconstrained data augmentation or unbounded dataset expansion; it is structured, fixed-ratio oversampling of mined hard negatives alongside standard training tiles.
2. **Epoch-Level Dynamics & Candidate Reuse:**
   - 13,440 standard training tiles $\div$ 14 tiles/batch = **960 mini-batches per epoch** (drawn without replacement across the standard pool each epoch).
   - $960 \text{ batches} \times 2 \text{ mined tiles} = \mathbf{1,920 \text{ mined tile draws per epoch}}$.
   - Because the candidate pool contains exactly $N = 400$ tiles, supplying 1,920 draws per epoch requires **sampling the candidate pool with replacement across the epoch** (approximately $4.8$ exposures per unique candidate tile per epoch).
3. **Supervision Label:** Mined negative tiles are supervised with all-zero ground-truth masks ($Y = 0$), delivering pure negative supervision via BCE gradient $\sigma(z) > 0$.
4. **Seed & Runtime Determinism:** Seed 42 is locked. Both data streams (standard and mined) are governed by deterministic PyTorch generators (`torch.Generator(seed=42)`), deterministic worker initialization functions (`worker_init_fn`), and deterministic CUDA runtime flags (`torch.backends.cudnn.deterministic = True`).

---

## 4. Pre-Registered Experiment Success Framework

Success is evaluated against explicit scalar acceptance criteria pre-registered prior to training execution:

> [!IMPORTANT]
> **Interpretation Principle & Pre-Registration Scope:**  
> The scalar thresholds defined below represent **minimum pre-registered acceptance/non-inferiority gates, not a claim of a practically meaningful effect size.**  
> **The primary quantitative endpoint is continuous false-positive burden, with scene/tile FAR as secondary diagnostics; success should be interpreted from the magnitude and consistency of the observed change, not from merely crossing a one-tile boundary.**

### 4.1 Primary Objective: Reduce Validation False-Positive Burden
The primary purpose of the intervention is to reduce false alarms on non-oil ocean water:
1. **Validation Clean Water False Alarm Rate ($\text{FAR}_{\text{clean\_water}}$):**
   - *Baseline Reference:* $20.09\%$ ($367 / 1,827$ empty validation tiles).
   - *Pre-Registered Scalar Ceiling:* $\mathbf{\text{FAR}_{\text{clean\_water}} < 20.09\%}$.
2. **Validation Significant Clean Water False Alarm Rate ($\text{FAR}_{\text{sig}}$, $FP \ge 100$ px):**
   - *Baseline Reference:* $10.56\%$ ($193 / 1,827$ empty validation tiles).
   - *Pre-Registered Scalar Ceiling:* $\mathbf{\text{FAR}_{\text{sig}} < 10.56\%}$.
3. **Total Validation False-Positive Pixels:**
   - *Baseline Reference:* $2,327,942$ pixels across 19,807 components.
   - *Pre-Registered Directional Target:* Total FP pixels $< 2,327,942$.

### 4.2 Non-Inferiority Constraint: Oil Segmentation Retention
The intervention must not degrade the model's core ability to detect genuine oil spills:
1. **Validation Global IoU ($\text{IoU}_{\text{val}}$):**
   - *Baseline Reference:* $0.72231$ (EXP-01 evaluation on `trujillo_2024_part_i_val`).
   - *Scientific Non-Inferiority Floor:* $\mathbf{\text{IoU}_{\text{val}} \ge 0.71731}$ (pre-registered margin of $-0.0050$, bounding maximum tolerable variance drift to $\le 0.50\text{ pp}$).
2. **Validation Recall ($\text{Recall}_{\text{val}}$):**
   - *Baseline Reference:* $0.8265$ ($82.65\%$).
   - *Pre-Registered Scalar Floor:* $\mathbf{\text{Recall}_{\text{val}} \ge 0.80000}$ ($80.00\%$, preventing conservative collapse or under-segmentation).

### 4.3 External Confirmation Gate: Untouched Trujillo Part III
- **Strict Benchmark Isolation:** Trujillo Part III remains completely offline, untouched, and unaccessed throughout model training, validation monitoring, and checkpoint selection:
  - **Zero Part III model forward passes** during training, validation, or model selection.
  - **Zero Part III training use** in any form.
  - **Zero Part III mining use** in candidate generation or harvesting.
  - **Zero Part III threshold tuning** or decision boundary selection.
  - **Zero Part III checkpoint selection** or early stopping.
- **Evaluation Timing:** Evaluation on Trujillo Part III occurs **exclusively after** the Phase 5B candidate checkpoint is finalized, frozen, and its SHA-256 hash recorded in the audit record.
- **Zero-Feedback Rule:** Benchmark outcomes on Trujillo Part III will not be used to tune thresholds, select checkpoints, or adjust Phase 5B parameters post-hoc.

---

## 5. Observability & Recovery Requirements

To ensure complete diagnostic transparency and avoid split-path observability defects, the Phase 5B training engine enforces:
1. **Unified In-Namespace State Path:**
   - Run state: `experiments/performance/exp03_baseline_hard_neg/run_state.json`
   - Progress state: `experiments/performance/exp03_baseline_hard_neg/progress.json`
   - Execution log: `experiments/performance/exp03_baseline_hard_neg/training.log`
2. **Mandatory Telemetry Fields:**
   - `phase`, `epoch`, `batch`, `epoch_loss`, `val_iou`, `val_far`, `elapsed_sec`, `eta_sec`, `heartbeat_utc`, `device_vram_mb`.
3. **Preflight Failure Mode:** If state files cannot be written or heartbeat expires for $>60\text{ s}$, execution halts immediately.

---

## 6. Prohibited Actions in Phase 5B

- ❌ DO NOT evaluate Trujillo Part III during training or for checkpoint selection.
- ❌ DO NOT tune the 12.5% sampling ratio based on Part III outcomes.
- ❌ DO NOT change the network backbone from ResNet-34.
- ❌ DO NOT change loss function weights or formulations away from CombinedBCEAndDiceLoss (0.5/0.5).
- ❌ DO NOT change decision threshold away from $\tau = 0.22$.
- ❌ DO NOT use external datasets (DARTIS, MORP_SYNTH).
- ❌ DO NOT perform tile-level splitting that leaks parent scenes.
- ❌ DO NOT commit or push without explicit CAO authorization.

---

## 7. Pre-Flight Acceptance Gate

Phase 5B training will be declared ready for CAO review under status:
$$\mathbf{PHASE\_5B\_CONTRACT\_PRE\_REGISTERED}$$
Training execution requires explicit instruction:
`CAO AUTHORIZATION: PROCEED WITH PHASE 5B TRAINING`
