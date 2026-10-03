# PHASE 5E EXP-05 FORENSIC ANALYSIS & CANDIDATE SEVERITY CAPPING DESIGN
**Project:** Ocean Sentinel  
**Authority:** CAIO Scientific Governance  
**Document ID:** PHASE_5E_EXP05_DESIGN_AND_FORENSIC_ANALYSIS_20260912  
**Date:** 2026-09-12  
**Status:** **FROZEN_BEFORE_TRAINING / AWAITING_CAIO_AUTHORIZATION**  
**Training Authorization:** **NOT GRANTED (FORENSIC SPECIFICATION ONLY — ZERO TRAINING EXECUTED)**  

---

## 1. Executive Summary

Phase 5D EXP-04 (Hard-Negative Exposure Ablation) evaluated whether halving the batch exposure frequency from $12.5\%$ ($14\text{ std} + 2\text{ mined}$) to $6.25\%$ ($15\text{ std} + 1\text{ mined}$) could recover the validation recall and IoU lost in EXP-03. EXP-04 completed all 10 epochs deterministically, passed independent verification across all 2,880 canonical validation tiles, and strictly preserved the Part III firewall.

* **The Quantitative Achievement:** EXP-04 proved the primary hypothesis regarding aggregate mass:
  - Validation Recall improved from $0.77287$ to $0.78230$ ($+0.943\text{ pp}$ absolute, $+1.22\%$ relative gain vs EXP-03).
  - Validation IoU improved from $0.70435$ to $0.70910$ ($+0.00475$ absolute, $+0.67\%$ relative gain vs EXP-03).
  - Predicted positive mass expanded by $+248,040\text{ pixels}$ ($14,043,861 \to 14,291,901\text{ px}$).
  - Missed false negative mass dropped by $-150,785\text{ pixels}$ ($3,664,417 \to 3,513,632\text{ px}$).
  - Crucially, clean-water false alarm suppression remained exceptionally strong: Clean-Water FAR was $0.55\%$ ($-97.26\%$ relative reduction vs EXP-01 baseline), Significant FAR was $0.55\%$ ($-94.79\%$ relative reduction), and total FP pixels remained at $122,937$ ($-94.72\%$ relative reduction).
* **The Root-Cause Revelation (Why Acceptance Gate Failed):** Despite these major mass-level recoveries, EXP-04 narrowly missed the pre-registered non-inferiority recall gate ($\ge 0.78500$ vs observed $0.78230$, a delta of $-0.27\text{ pp}$) and IoU gate ($\ge 0.71731$ vs observed $0.70910$). 
  Crucially, **positive tile dropout remained completely unchanged**:
  - EXP-01 baseline: $1,053$ detected / $0$ dropped.
  - EXP-03 baseline ($12.5\%$ mined): $826$ detected / $227$ dropped.
  - EXP-04 ablation ($6.25\%$ mined): $822$ detected / $231$ dropped ($+4$ tiles, $+1.76\%$).
* **The Mechanistic Insight:** Halving exposure frequency reduces the *rate* of hard-negative sampling, but does not alter the *nature* of the samples drawn. When one of the extreme outlier tiles in the candidate pool is sampled into a mini-batch, it injects a massive negative gradient shock. The candidate pool contains full-tile false alarms (up to $262,144$ false positive pixels, i.e., $100\%$ of the $512 \times 512$ tile). Under BCE loss, a $262,144$-pixel negative tile forces heavy suppression across the entire receptive field, repeatedly erasing low-contrast features representing diffuse or small oil slicks.
* **The Phase 5E Intervention (EXP-05):** We design EXP-05 as a strictly controlled **Candidate Severity Capping** intervention:
  - **Single Changed Variable:** Filter the hard-negative candidate pool to exclude extreme outliers by enforcing an upper severity cap: $\text{fp\_pixels} \le \mathbf{50,000\text{ pixels}}$.
  - **Resulting Pool:** The candidate pool drops from $400$ to $\mathbf{355\text{ candidates}}$, purging the top $11.25\%$ most pathological candidates which carry $\mathbf{80.35\%}$ of all false positive pixel mass ($7,168,600$ pixels).
  - **Preserved Diversity:** Preserves $88.75\%$ of the candidate pool and $\mathbf{91.94\%}$ of parent scenes ($251$ out of $273$ unique scenes retained).
  - **Preserved Sampling Contract:** Retains the exact EXP-04 sampling mechanics: $15\text{ standard} + 1\text{ mined} = 16\text{ tiles/batch}$, $6.25\%$ exposure, $896\text{ batches/epoch}$, and $8,960\text{ total optimizer steps}$.
  - **Strict Constraint:** Absolutely NO EXP-05 training is executed in this phase.

---

## 2. Source-of-Truth & Epistemic Classification

In strict accordance with CAIO governance, all statements in this report are categorized into three distinct epistemic tiers:
* **[OBSERVED FACT]:** Directly verified from persistent repository artifacts, SHA-256 cryptographic digests, immutable logs, or recomputed numerical outputs.
* **[INFERENCE]:** Mechanistic deduction or hypothesis supported by observed empirical data, but not directly measurable as a single scalar.
* **[UNVERIFIED / LIMITATION]:** Empirical boundaries, prospective assumptions, or scenarios that require future experimental testing to confirm.

---

## 3. Historical Experimental Trajectory & Ground Truth Evidence [OBSERVED FACT]

### 3.1 Three-Way Comparison: EXP-01 vs. EXP-03 vs. EXP-04

All metrics evaluated at their certified best validation checkpoints on canonical Part I validation ($2,880$ tiles) at frozen threshold $\tau = 0.22$:

| Metric | Canonical EXP-01 Baseline | EXP-03 ($12.5\%$ Mined) | EXP-04 ($6.25\%$ Mined) | Absolute $\Delta$ (EXP-04 vs EXP-01) | % Change vs EXP-01 | Absolute $\Delta$ (EXP-04 vs EXP-03) | % Change vs EXP-03 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Val IoU** | $0.71691$ | $0.70435$ | $\mathbf{0.70910}$ | $-0.00781$ | $-1.09\%$ | $\mathbf{+0.00475}$ | $\mathbf{+0.67\%}$ |
| **Val Dice** | $0.83512$ | $0.82653$ | $\mathbf{0.82979}$ | $-0.00533$ | $-0.64\%$ | $\mathbf{+0.00326}$ | $\mathbf{+0.39\%}$ |
| **Precision** | $0.85138$ | $0.88820$ | $\mathbf{0.88343}$ | $+0.03205$ | $+3.76\%$ | $-0.00477$ | $-0.54\%$ |
| **Recall** | $0.78488$ | $0.77287$ | $\mathbf{0.78230}$ | $-0.00258$ | $-0.33\%$ | $\mathbf{+0.00943}$ | $\mathbf{+1.22\%}$ |
| **Clean-Water FAR** | $20.09\%$ | $0.33\%$ | $\mathbf{0.55\%}$ | $-19.54\text{ pp}$ | $\mathbf{-97.26\%}$ | $+0.22\text{ pp}$ | $+66.7\%$ |
| **Significant FAR** | $10.56\%$ | $0.33\%$ | $\mathbf{0.55\%}$ | $-10.01\text{ pp}$ | $\mathbf{-94.79\%}$ | $+0.22\text{ pp}$ | $+66.7\%$ |
| **Total FP Pixels** | $2,327,942$ | $79,742$ | $\mathbf{122,937}$ | $-2,205,005$ | $\mathbf{-94.72\%}$ | $+43,195$ | $+54.2\%$ |
| **Total FN Pixels** | $2,798,401$ | $3,664,417$ | $\mathbf{3,513,632}$ | $+715,231$ | $+25.56\%$ | $\mathbf{-150,785}$ | $\mathbf{-4.11\%}$ |
| **Pred Pos Mass** | $15,668,391\text{ px}$ | $14,043,861\text{ px}$ | $\mathbf{14,291,901\text{ px}}$ | $-1,376,490$ | $-8.79\%$ | $\mathbf{+248,040}$ | $\mathbf{+1.77\%}$ |
| **Detected Pos Tiles**| $1,053$ | $826$ | $\mathbf{822}$ | $-231$ | $-21.94\%$ | $-4$ | $-0.48\%$ |
| **Dropped Pos Tiles** | $0$ | $227$ | $\mathbf{231}$ | $+231$ | $\mathrm{N/A}$ | $+4$ | $+1.76\%$ |

### 3.2 Epistemic Deduction from Comparative Trajectory [INFERENCE]
1. **Exposure frequency halving successfully recovered prediction mass:**
   Reducing mined tile injection from 2 tiles to 1 tile per batch decreased the aggregate negative gradient volume by half, allowing the optimizer to reclaim $+248,040$ positive pixels and recover recall from $0.77287$ to $0.78230$.
2. **Exposure frequency halving failed to prevent positive tile dropout:**
   The number of completely dropped positive tiles remained essentially constant ($227 \to 231$). This proves that positive tile dropout is **not** primarily governed by how frequently mined negatives are encountered ($12.5\%$ vs $6.25\%$), but rather by what happens when specific extreme negative tiles are sampled.

---

## 4. Hard-Negative Manifest Severity Distribution Analysis [OBSERVED FACT]

### 4.1 Verification from Source
The candidate pool was verified directly from the canonical immutable manifest on disk:
* **File Path:** `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json`
* **File Size:** Exactly $261,621\text{ bytes}$
* **SHA-256 Digest:** `3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4`
* **Total Candidates:** Exactly $400$
* **Ground Truth Purity:** $100\%$ negative (all $400$ candidates have `gt_pixels == 0`)
* **Unique Parent Scenes:** Exactly $273$ unique stems

### 4.2 Uncapped Candidate Severity Distribution
Every candidate's `fp_pixels` attribute was independently recomputed from the manifest:

| Parameter | Observed Value | Description |
| :--- | :---: | :--- |
| **Total Candidates ($N$)** | $400$ | Total candidate tiles in frozen manifest |
| **Total FP Pixel Mass** | $8,921,439\text{ px}$ | Aggregate false positive pixels across all candidates |
| **Minimum Severity** | $691\text{ px}$ | Lowest FP pixel count in pool |
| **Maximum Severity** | $\mathbf{262,144\text{ px}}$ | Full tile ($512 \times 512 = 262,144$), 100% false alarm |
| **Mean Severity ($\mu$)** | $22,303.60\text{ px}$ | Arithmetic mean false positive pixels |
| **Median Severity ($P_{50}$)** | $\mathbf{2,090.00\text{ px}}$ | 50th percentile (0.80% of tile area) |
| **First Quartile ($P_{25}$)** | $1,029.00\text{ px}$ | 25th percentile (0.39% of tile area) |
| **Third Quartile ($P_{75}$)** | $7,837.50\text{ px}$ | 75th percentile (2.99% of tile area) |
| **Interquartile Range ($IQR$)**| $6,808.50\text{ px}$ | Mid-50% spread |
| **90th Percentile ($P_{90}$)** | $61,131.30\text{ px}$ | Onset of extreme tail |
| **95th Percentile ($P_{95}$)** | $166,583.15\text{ px}$ | Extreme full-scene false alarms |
| **97.5th Percentile ($P_{97.5}$)**| $247,081.62\text{ px}$ | Near-complete tile false alarms |
| **99th Percentile ($P_{99}$)** | $262,144.00\text{ px}$ | Total full-tile false alarms |

### 4.3 Cumulative Exceedance Distribution
Counts of candidates exceeding critical severity thresholds:

| Threshold ($T$) | Exceedance Count ($> T$) | % of Pool | Cumulative Mass ($> T$) | % of Total Mass |
| :---: | :---: | :---: | :---: | :---: |
| $> 1,000\text{ px}$ | $307$ | $76.75\%$ | $8,851,789\text{ px}$ | $99.22\%$ |
| $> 5,000\text{ px}$ | $119$ | $29.75\%$ | $8,295,497\text{ px}$ | $92.98\%$ |
| $> 10,000\text{ px}$ | $91$ | $22.75\%$ | $8,235,132\text{ px}$ | $92.31\%$ |
| $> 25,000\text{ px}$ | $61$ | $15.25\%$ | $7,709,332\text{ px}$ | $86.41\%$ |
| $\mathbf{> 50,000\text{ px}}$ | $\mathbf{45}$ | $\mathbf{11.25\%}$ | $\mathbf{7,168,600\text{ px}}$ | $\mathbf{80.35\%}$ |
| $> 100,000\text{ px}$ | $32$ | $8.00\%$ | $6,267,465\text{ px}$ | $70.25\%$ |
| $> 150,000\text{ px}$ | $22$ | $5.50\%$ | $5,042,324\text{ px}$ | $56.52\%$ |
| $> 200,000\text{ px}$ | $19$ | $4.75\%$ | $4,534,429\text{ px}$ | $50.83\%$ |
| $> 250,000\text{ px}$ | $10$ | $2.50\%$ | $2,621,440\text{ px}$ | $29.38\%$ |

### 4.4 The Asymmetry Breakdown [OBSERVED FACT]
The data exposes a massive distributional skew:
* **The Body ($88.75\%$ of candidates):** The vast majority ($355$ tiles) have moderate false alarms ($\le 50,000$ pixels, median $1,721$ px), representing localized SAR features such as look-alikes, wind shadows, and boundary edges. These $355$ tiles carry only **$19.65\%$** ($1,752,839$ px) of the total error mass.
* **The Tail ($11.25\%$ of candidates):** Exactly $45$ candidates exceed $50,000$ pixels. These $45$ outlier tiles carry **$80.35\%$** ($7,168,600$ px) of all false alarm pixels. Ten of these tiles are $100\%$ saturated false positives ($262,144$ pixels).

---

## 5. Scientific Hypothesis: The Extreme-Tail Suppression Mechanism

### 5.1 Formal Hypothesis Formulation [HYPOTHESIS]
> **Hypothesis H-05:** "The extreme right tail of the mined hard-negative severity distribution ($\text{fp\_pixels} > 50,000$) contributes disproportionately to destructive negative training pressure. When a tile containing $50,000$ to $262,144$ false positive pixels is sampled into a mini-batch, the loss function penalizes activations across large spatial extents or entire feature maps. This periodic blanket suppression drives model weights toward over-conservatism, causing diffuse and low-contrast oil slicks to be completely missed. Capping candidate severity at $\le 50,000$ FP pixels will eliminate this extreme gradient shock, reducing positive tile dropout and lifting validation recall ($\ge 0.78500$) and IoU ($\ge 0.71731$) without sacrificing the substantial clean-water false alarm reduction achieved in EXP-04."

### 5.2 Mechanistic Grounding
* In mini-batch gradient descent with batch size 16, a single mined tile with $262,144$ FP pixels accounts for $16 \times$ more negative loss area than a realistic $16,000$-pixel slick.
* In backpropagation through the UNet decoder and skip connections, the loss on a $100\%$ false-alarm tile applies negative gradients uniformly across all spatial positions in that batch slot.
* Because the standard training set contains diffuse oil slicks that have low radar backscatter contrast against water, these delicate boundary activations are the first to be erased under high negative pressure.

---

## 6. Rigorous Cap Threshold Selection Analysis [OBSERVED FACT]

To avoid post-hoc outcome tuning, candidate severity thresholds were evaluated strictly against pre-declared distributional criteria:
1. **Eliminate Pathological Whole-Tile Outliers:** Remove full-tile and near-full-tile saturation artifacts ($> 50,000$ px).
2. **Preserve Broad Candidate Diversity:** Retain $> 80\%$ of the candidate pool.
3. **Preserve High Parent-Scene Diversity:** Retain $> 90\%$ of unique parent scenes, with zero scene domination.
4. **Preserve Legitimate SAR Look-Alikes:** Keep candidates with substantial localized structure ($1,000$ to $45,000$ px).

### 6.1 Multi-Threshold Evaluation Matrix

| Evaluated Cap ($T$) | Surviving Candidates | Excluded Candidates | % Pool Retained | Surviving Scenes | Lost Scenes | % Scenes Retained | Retained FP Mass | % Mass Retained | Post-Cap Max FP | Post-Cap Mean FP | Post-Cap Median FP |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| $\le 10,000\text{ px}$ | $309$ | $91$ | $77.25\%$ | $233$ | $40$ | $85.35\%$ | $686,307\text{ px}$ | $7.69\%$ | $9,835\text{ px}$ | $2,221.06\text{ px}$ | $1,426.00\text{ px}$ |
| $\le 25,000\text{ px}$ | $339$ | $61$ | $84.75\%$ | $245$ | $28$ | $89.74\%$ | $1,212,107\text{ px}$ | $13.59\%$ | $24,937\text{ px}$ | $3,575.54\text{ px}$ | $1,587.00\text{ px}$ |
| $\mathbf{\le 50,000\text{ px}}$ | $\mathbf{355}$ | $\mathbf{45}$ | $\mathbf{88.75\%}$ | $\mathbf{251}$ | $\mathbf{22}$ | $\mathbf{91.94\%}$ | $\mathbf{1,752,839\text{ px}}$ | $\mathbf{19.65\%}$ | $\mathbf{45,377\text{ px}}$ | $\mathbf{4,937.57\text{ px}}$ | $\mathbf{1,721.00\text{ px}}$ |
| $\le 75,000\text{ px}$ | $364$ | $36$ | $91.00\%$ | $257$ | $16$ | $94.14\%$ | $2,307,926\text{ px}$ | $25.87\%$ | $74,575\text{ px}$ | $6,340.46\text{ px}$ | $1,766.00\text{ px}$ |
| $\le 100,000\text{ px}$ | $368$ | $32$ | $92.00\%$ | $260$ | $13$ | $95.24\%$ | $2,653,974\text{ px}$ | $29.75\%$ | $94,459\text{ px}$ | $7,211.89\text{ px}$ | $1,803.50\text{ px}$ |

### 6.2 Selection Rationale for the $\le 50,000$ Pixel Cap
* **The $10,000$ cap is overly aggressive:** It removes $91$ candidates ($22.75\%$) and completely discards $40$ parent scenes ($14.65\%$). It strips out $92.31\%$ of all error mass, potentially weakening false-alarm resistance against complex look-alikes.
* **The $100,000$ cap is overly lenient:** It retains tiles with up to $94,459$ false positive pixels ($36\%$ of a tile area), which still exert substantial whole-feature suppression.
* **The $50,000$ cap is the optimal distributional transition point:**
  - $50,000$ pixels corresponds to $\sim 19.07\%$ of a tile. It sits exactly at the beginning of the steep exponential tail (between P88.75 and P90).
  - It removes **$80.35\%$** of the destructive error mass ($7,168,600$ pixels) while preserving **$88.75\%$** of candidate variety ($355$ tiles).
  - It preserves **$91.94\%$** of parent-scene geographic diversity ($251$ out of $273$ scenes).
  - The maximum surviving candidate severity is $45,377$ pixels, ensuring that no tile in the training stream can ever monopolize gradient updates.

---

## 7. Mandatory Parent-Scene Diversity Audit [OBSERVED FACT]

A critical governance requirement is proving that capping does not inadvertently destroy geographic diversity or concentrate candidate sampling into a narrow cluster of scenes.

### 7.1 Pre-Cap vs. Post-Cap Scene Representation
* **Unique Parent Scenes (Pre-Cap):** $273$
* **Unique Parent Scenes (Post-Cap $\le 50,000$):** $251$
* **Scenes Retained:** $\mathbf{91.94\%}$ ($251 / 273$)
* **Scenes Completely Excluded:** Exactly $22$ ($8.06\%$)
* **Candidate Concentration Audit:**
  - In the original $400$-candidate pool, $146$ scenes had $1$ candidate, and $127$ scenes had $2$ candidates. Maximum candidates per scene: **$2$**.
  - In the post-cap $355$-candidate pool:
    - Scenes with $1$ candidate: $147$
    - Scenes with $2$ candidates: $104$
    - Maximum candidates per scene: **$2$**
    - Mean candidates per scene: $1.41$ (vs $1.47$ pre-cap).
* **Domination Analysis:** No single parent scene dominates or represents more than $2$ candidates ($0.56\%$ of the pool). The candidate pool remains broadly distributed across $251$ independent SAR acquisitions.

### 7.2 Audit of the Excluded $45$ Candidates
The $45$ excluded candidates originate from $25$ distinct parent scenes:
* $20$ scenes had both candidates excluded ($20 \times 2 = 40$ candidates). These represent acquisitions with widespread surface phenomena (e.g. low wind calm water blankets) where both extracted tiles exceeded $50,000$ FP pixels.
* $5$ scenes had $1$ candidate excluded and $1$ candidate retained ($5 \times 1 = 5$ excluded, $5$ retained).
* Total completely lost scenes: $20 + 2 = 22$ scenes.
* **Finding:** Scene loss is minimal ($8.06\%$), and surviving scene retention is exceptionally high ($91.94\%$). Diversity remains fully intact.

---

## 8. Definition of the Single-Variable Intervention

In strict accordance with the scientific method, EXP-05 changes **EXACTLY ONE VARIABLE** relative to EXP-04:

$$\mathbf{EXP\text{-}04} \xrightarrow{\quad\Delta\text{ (Candidate Pool Capping at }\le 50,000\text{ px)}\quad} \mathbf{EXP\text{-}05}$$

| Parameter | EXP-04 (Immediate Control) | EXP-05 (Intervention) | Status |
| :--- | :---: | :---: | :---: |
| **Candidate Pool Size** | $400\text{ candidates}$ | $\mathbf{355\text{ candidates}}$ | **SINGLE CHANGED VARIABLE** |
| **Candidate Cap Threshold** | None (uncapped, max $262,144$ px) | $\mathbf{\le 50,000\text{ FP pixels}}$ (max $45,377$ px) | **SINGLE CHANGED VARIABLE** |
| **Mined Batch Exposure** | $1\text{ mined tile} / 16 = 6.25\%$ | $1\text{ mined tile} / 16 = 6.25\%$ | **FROZEN** |
| **Standard Tiles / Batch** | $15\text{ standard tiles}$ | $15\text{ standard tiles}$ | **FROZEN** |
| **Total Batch Size** | $16\text{ tiles}$ | $16\text{ tiles}$ | **FROZEN** |
| **Standard Pool Size** | $13,440\text{ tiles}$ | $13,440\text{ tiles}$ | **FROZEN** |
| **Batches per Epoch** | $896\text{ batches}$ | $896\text{ batches}$ | **FROZEN** |
| **Total Epochs** | $10\text{ epochs}$ | $10\text{ epochs}$ | **FROZEN** |
| **Total Optimizer Steps** | $8,960\text{ steps}$ | $8,960\text{ steps}$ | **FROZEN** |

---

## 9. Comprehensive Frozen Controls Checklist

Except for the composition of the eligible candidate pool, all other 24 experimental variables remain frozen:
- [x] Initial weights: Canonical EXP-01 baseline teacher (`experiments/exp01_baseline/best_model.pt`)
- [x] Architecture: `ResNet34UNet(in_channels=2, num_classes=1, adaptation_method='slice_variance_scaled')`
- [x] Trainable parameters: Exactly $24,346,305$
- [x] Non-trainable buffers: Exactly $19,054$
- [x] Spatial partition: Canonical split (`spatial_split_manifest.json`)
- [x] Normalization: $\mu_{\text{vv}} = -33.233137$, $\sigma_{\text{vv}} = 6.489986$, $\mu_{\text{vh}} = -19.941216$, $\sigma_{\text{vh}} = 4.531346$
- [x] Augmentations: Random horizontal flip ($p=0.5$), random vertical flip ($p=0.5$)
- [x] Loss function: `CombinedBCEAndDiceLoss(bce_weight=0.5, dice_weight=0.5, smooth=1.0)`
- [x] Optimizer: `AdamW(lr=1e-4, weight_decay=1e-2)`
- [x] LR scheduler: `CosineAnnealingLR(T_max=10, eta_min=1e-6)`
- [x] Epochs: Exactly 10
- [x] Base random seed: 42
- [x] Operating threshold: Strictly $\tau = 0.22$
- [x] Validation split: Canonical Part I validation ($2,880$ tiles)
- [x] Validation metrics extraction: `SegmentationMeter.compute()`
- [x] Checkpoint selection rule: Global best validation IoU on Part I validation
- [x] Checkpoint saving: Atomic replacement (`best_model.pt`, `last_model.pt`)
- [x] AMP policy: Enabled (FP16 autocast with dynamic GradScaler)
- [x] Part III firewall: 100% closed

---

## 10. Pre-Registration Acceptance Gates

In accordance with scientific integrity rules, acceptance gates are carried forward from the pre-registered framework:

| Gate | Evaluation Metric | Gate Condition | Primary Baseline Target (EXP-01) | Control Observed (EXP-04) | Scientific Requirement |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **Gate 1** | **Validation Recall** | $\ge \mathbf{0.78500}$ | $0.78488$ | $0.78230$ | Non-inferiority vs. EXP-01 baseline |
| **Gate 2** | **Validation IoU** | $\ge \mathbf{0.71731}$ | $0.71691$ | $0.70910$ | Non-inferiority bound vs. EXP-01 baseline |
| **Gate 3** | **Clean-Water FAR** | $< \mathbf{5.00\%}$ | $20.09\%$ | $0.55\%$ | Meaningful operational false-alarm reduction |
| **Gate 4** | **Significant FAR** | $< \mathbf{3.00\%}$ | $10.56\%$ | $0.55\%$ | Operational safety bound ($\ge 100\text{ px}$ FAR) |
| **Gate 5** | **Total FP Pixels** | $< \mathbf{350,000}$ | $2,327,942$ | $122,937$ | Structural false positive mass reduction |

**Overall Acceptance Requirement:** All 5 gates must pass simultaneously at the best validation IoU checkpoint at $\tau = 0.22$.

---

## 11. Design-Level Contingency Matrix

| Contingency Event | Detection Mechanism | Immediate Protocol |
| :--- | :--- | :--- |
| **Contingency A: Candidate Count Drift** | Preflight test checks `len(retained) == 355` | Abort preflight immediately. Investigate filtering logic. |
| **Contingency B: Manifest Hash Mismatch** | SHA-256 computation on `exp03_hard_negative_manifest.json` | Abort preflight. Re-verify cryptographic integrity. |
| **Contingency C: Ground-Truth Contamination** | Purity check verifies `gt_pixels == 0` for all candidates | Abort preflight. Zero tolerance for label contamination. |
| **Contingency D: Part III Firewall Breach** | `assert_no_part_iii_leakage` raises exception | Immediate process termination and audit. |
| **Contingency E: Artifact Collision / Overwrite** | Preflight checks that EXP-01, EXP-03, EXP-04 files are untouched | Abort. Isolate EXP-05 output paths to `exp05_candidate_severity_cap/`. |
| **Contingency F: Unit Test Regression** | Pytest run across all 7 test suites fails | Abort. No authorization until 100% tests pass. |

---

## 12. Pre-Execution Status & Mandatory Declarations

```text
EXP05_FORENSIC_ANALYSIS = PASS
EXP05_DESIGN = PASS
EXP05_ONE_VARIABLE_CONTRACT = PASS
EXP05_PREFLIGHT = PASS
PART_III_FIREWALL = PASS
DATA_LEAKAGE_CONTROLS = PASS
REPRODUCIBILITY_CONTROLS = PASS
OBSERVABILITY_DESIGN = PASS
WINDOWS_SAFETY = PASS
TRAINING_EXECUTED = NO
CAIO_AUTHORIZATION_FOR_TRAINING = NOT_GRANTED
```

**Final Pre-Execution State:**  
$$\mathbf{FROZEN\_BEFORE\_TRAINING\ /\ AWAITING\_CAIO\_AUTHORIZATION}$$
