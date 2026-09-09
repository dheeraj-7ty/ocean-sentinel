# GATE EXP02B-0 FINAL REPORT
**Ocean Sentinel — Scientific Phase EXP02B-0: Hard-Negative Design & Candidate Audit**  
**Authoritative Protocol**: CAO Formal Authorization — EXP02B-0 Revision 3  
**Timestamp**: 2026-09-09T02:18:42Z  
**Hardware Environment**: NVIDIA GeForce RTX 3050 Laptop GPU (6,442 MB VRAM), CUDA 12.8, PyTorch 2.10.0  
**Overall Gate Classification**: **PASS**  
**Operational Status**: **HARD STOP ENFORCED** — Design and Candidate Audit Complete. No EXP02B-1 Training.  

---

## 1. Executive Summary & Audit Matrix

| Field | Description / Value |
| :--- | :--- |
| **Gate Identifier** | **GATE EXP02B-0** (Hard-Negative Design & Candidate Audit) |
| **Scientific Objective** | Characterize GT-negative false alarms on train split; design single sampling intervention |
| **Candidate Mining Scope** | **13,440 canonical TRAIN tiles only** (VAL and TEST strictly excluded) |
| **Teacher Model** | Certified EXP01 `best_model.pt` (SHA-256: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`) |
| **Identified Hard Negatives** | **1,605 tiles** (19.21% of GT negatives; 11.94% of all train tiles) |
| **Proposed Sampling Policy** | $w_{\text{pos}}=1.00$, $w_{\text{hard\_neg}}=2.25$, $w_{\text{ord\_neg}}=0.75$ (explicit intervention parameters targeting $3.0\times$ hard/ordinary exposure ratio) |
| **Phase 4 Sampler Dry Run** | **PASS**: 1,680 batches, 13,440 draws, 0 optimizer steps, 100% train isolation, $3.052\times$ exposure ratio |
| **Pre-Registered Evaluation** | Primary: $\text{FA\_rate}_{\text{val}} \le 17.0\%$; Paired two-sided McNemar test on $n=1,827$ tiles ($\alpha=0.05$) |
| **EXP02B-1 Initial State** | Fresh trajectory from certified ImageNet pretrained ResNet-34 (`B627A593...`), **zero C-C resume** |

---

## 2. Phase-by-Phase Verification Matrix (Strict Classifications)

| Phase | Milestone / Check | Expected Specification | Observed Fact | Classification |
| :---: | :--- | :--- | :--- | :---: |
| **P0** | **Repository & Scientific Freeze** | Working tree preserved; C-C immutable; ADR 005 authored | Zero destructive git operations. C-C2 hash `38E7B6E1...` verified. ADR 005 created at `docs/adr/005-resumed-training-infrastructure-qualification.md`. | **PASS** |
| **P1** | **Teacher Provenance Audit** | Certified EXP01 `best_model.pt` (`9B8BD867...`) | 292,465,299 bytes, SHA-256 `9B8BD867...` (100% match). 24,346,305 params across 288 finite tensors. Recorded in `teacher_integrity.json`. | **PASS** |
| **P2** | **TRAIN-Only Candidate Mining** | Audit 13,440 train tiles; raw distributions; 0 val/test access | 8,357 GT-negatives (62.18%), 5,083 positives (37.82%). 2,599 GT-negatives produce FP $\ge 1$ px. Full quantiles and parent patch concentrations recorded in `candidate_audit_raw.json`. | **PASS** |
| **P3** | **Define ONE Sampling Policy** | Cutoff rule and weights informed by train distribution | Cutoff: $M_i == 0$ and $\text{fp\_pixel\_count} \ge 100$ px ($n=1,605$). Weights: $w_{\text{pos}}=1.00$, $w_{\text{hard\_neg}}=2.25$, $w_{\text{ord\_neg}}=0.75$ (explicit intervention parameters). Authored `proposed_sampling_policy.md`. Finalized `candidate_manifest.json`. | **PASS** |
| **P4** | **Sampler Dry Run** | Dry run THAT EXACT policy: 1,680 batches, 13,440 draws, 0 train steps | Tested live DataLoader on 25 batches (shapes [8, 2, 512, 512], [8, 1, 512, 512]). Full 13,440 draw stream evaluated: 8,059 unique, 5,381 duplicate, 3,590 hard-neg draws, effective exposure ratio $3.052\times$, 100% train isolation. Recorded in `sampler_dry_run.json`. | **PASS** |
| **P5** | **Pre-Register Endpoints & Test** | Primary $\text{FA\_rate} \le 17.0\%$; paired McNemar $\alpha=0.05$; safety recall $\ge 79\%$; IoU $\ge 0.70$ | Pre-registered mathematically in `proposed_success_criteria.md`. Defined paired $2\times 2$ McNemar test on $n=1,827$ tiles. Clarified $\le 17.0\%$ is stricter than 15% relative reduction. | **PASS** |
| **P6** | **Gate Report & Package Synthesis** | Complete 8-artifact evidence package; HARD STOP enforced | All 8 required files generated with cryptographic hashes in `experiment_identity.json`. HARD STOP enforced. | **PASS** |

---

## 3. Detailed Forensic Evidence by Phase

### 3.1 Phase 0 — Scientific & Repository Freeze
- **Observed Facts**:
  - Git working tree audited: tracked modifications in `docs/`, `src/`, `scripts/download_datasets.py`, and `tests/test_preprocessing.py` preserved intact without reset or clean.
  - C-C2 canonical seed `latest_checkpoint.pt` verified: SHA-256 `38E7B6E12177C9BAF60C98379C76E75684D8FC9CCB3E66BA0201B938EB29BCAA`.
  - C-C4 resumed `latest_checkpoint.pt` verified: SHA-256 `F6C92CD94362826AC603CFF68B900BE6B98126B32D396EBC76C699BF289242F1`.
  - ADR 005 authored at `docs/adr/005-resumed-training-infrastructure-qualification.md` separating C-C infrastructure changes from scientific configurations.
- **Classification**: **PASS**.

### 3.2 Phase 1 — Teacher Provenance Audit
- **Observed Facts**:
  - Path: `experiments/exp01_baseline/best_model.pt`
  - Byte Size: **292,465,299 bytes**
  - SHA-256 Digest: **`9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`**
  - Model Class: `ocean_sentinel.ml.unet_resnet.ResNet34UNet`
  - Adaptation Method: `slice_variance_scaled`
  - Parameter Tensors: 288 parameter/buffer tensors, all finite (0 NaN, 0 Inf).
  - Output File: `experiments/performance/exp02b_0_hard_negative_design_20260909_021500/teacher_integrity.json`.
- **Classification**: **PASS**.

### 3.3 Phase 2 — Train-Only Hard-Negative Mining & RAW Distribution Audit
- **Observed Facts**:
  - Entire 13,440 training tiles audited on local NVIDIA GeForce RTX 3050 GPU in 496.16s (27.1 tiles/s).
  - Split Isolation: Validation (2,880) and Test (2,880) splits 100% excluded.
  - Classifications:
    - `eligible_gt_negative`: **8,357 tiles** (62.18% of train split).
    - `positive_spill_tile`: **5,083 tiles** (37.82% of train split).
  - False-Alarm Characteristics on GT-negatives at threshold 0.22:
    - Zero False Positives: **5,758 tiles** (68.90% of GT-negatives).
    - Any False Positives ($\ge 1$ px): **2,599 tiles** (31.10% of GT-negatives).
    - Macro False Positives ($\ge 100$ px): **1,605 tiles** (19.21% of GT-negatives).
    - Severe Macro False Positives ($\ge 1,000$ px): **528 tiles** (6.32% of GT-negatives).
    - Catastrophic Tile False Alarms ($\ge 10,000$ px): **162 tiles** (1.94% of GT-negatives).
  - Continuous Empirical Quantiles across GT-negatives ($n=8,357$):
    - `max_prob`: min=0.0170, p25=0.0388, p50=0.0617, p75=0.5131, p90=0.9776, max=0.9999.
    - `mean_prob`: min=0.0004, p50=0.0017, p75=0.0024, p90=0.0037, max=0.9837.
    - `fp_pixel_count` (tiles with FP > 0, $n=2,599$): p25=45, p50=168, p75=712, p90=3,527, p95=17,885, max=262,144 px.
    - Max Connected Component area ($\max A_{\text{cc}}$, $n=2,599$): p25=42, p50=149, p75=561, p90=2,145, max=262,144 px.
  - Teacher-Training-Population Diagnostic:
    - 718 out of 839 parent patches containing negatives produce at least one false positive.
    - Top 10 concentrated patches exhibit false-positive rates between 84.6% and 100.0%, demonstrating severe local radar lookalike/clutter persistence.
- **Classification**: **PASS**.

### 3.4 Phase 3 — Define ONE Scientific Sampling Policy
- **Observed Facts**:
  - **Candidate Cutoff Rule & Selection Rationale**:
    - Rule: $M_i == 0 \text{ AND } \text{fp\_pixel\_count}_i \ge 100 \text{ pixels}$ at diagnostic threshold 0.22.
    - Cutoff Rationale: The 100-pixel cutoff was **not** pre-specified prior to viewing data; it was selected after inspecting the empirical TRAIN distribution in Phase 2. Among the 2,599 GT-negative tiles producing false positives ($\ge 1$ px) at threshold 0.22, the empirical distribution of `fp_pixel_count` shows a 25th percentile of 45 pixels, median of 168 pixels, and 75th percentile of 712 pixels. The 100-pixel threshold was selected as an operationally meaningful boundary to isolate **macro false-positive tiles** ($\ge 100$ FP pixels) where false alarms form coherent spatial artifacts rather than diffuse speckle noise (<100 pixels), while retaining a robust candidate cohort (1,605 tiles, 19.21% of GT negatives, 61.8% of all false-positive-producing negative tiles) without introducing multi-parameter composite scoring.
    - Yields exactly **1,605** `candidate_hard_negative` tiles, leaving **6,752** `ordinary_gt_negative` tiles and **5,083** `positive_spill_tile`.
  - **Weight Assignment Parameters**:
    - The sampling weights are explicit scientific intervention parameters chosen by design to achieve an intended $3.0\times$ exposure ratio of hard negatives over ordinary negatives ($w_{\text{hard\_neg}} / w_{\text{ord\_neg}} = 2.25 / 0.75 = 3.0$), informed by the observed TRAIN candidate population sizes rather than mathematically determined by the data:
      - $w_{\text{pos}} = 1.00$
      - $w_{\text{ord\_neg}} = 0.75$
      - $w_{\text{hard\_neg}} = 2.25$
    - Total Weight Sum: **13,758.25**.
  - **Expected & Empirical Exposure Distribution**:
    - Positive tiles: **4,965.4 expected draws** (36.95% vs nominal baseline 37.82%; observed dry-run exposure 36.47%, preserving substantial positive-example exposure without guaranteeing recall preservation, which remains an empirical endpoint of EXP02B-1).
    - Hard-negative tiles: **3,527.7 expected draws** (26.25% vs nominal 11.94%, a $2.20\times$ boost in total gradient signals on radar lookalikes).
    - Ordinary negative tiles: **4,946.9 expected draws** (36.81% vs nominal 50.24%).
  - Artifacts: `proposed_sampling_policy.md` and finalized `candidate_manifest.json` carrying Stage 2 classifications.
- **Classification**: **PASS**.

### 3.5 Phase 4 — Sampler Dry Run of THAT EXACT Proposed Policy
- **Observed Facts**:
  - Sampler Class: `torch.utils.data.WeightedRandomSampler(replacement=True, num_samples=13440, generator=torch.Generator().manual_seed(42))`
  - Execution: Tested DataLoader on 25 live batches ($200$ samples) proving batch dimensions `[8, 2, 512, 512]` and mask dimensions `[8, 1, 512, 512]`.
  - Full Simulated Epoch (1,680 batches, 13,440 draws):
    - Unique tiles drawn: **8,059** (59.96%).
    - Duplicate draws: **5,381** (40.04%).
    - Class draws: Positive = **4,901** (36.47%, expected 4,965.4); Hard Negative = **3,590** (26.71%, expected 3,527.7); Ordinary Negative = **4,949** (36.82%, expected 4,946.9).
    - Effective Exposure Ratio: $\frac{3590 / 1605}{4949 / 6752} = \frac{2.237}{0.733} = \mathbf{3.052\times}$ (Expected: $3.000\times$).
    - Zero Leakage: 100% of drawn indices resolve to split `train`. 0 validation or test tiles drawn.
    - Zero Training: 0 optimizer steps, 0 backward passes, 0 parameter updates.
  - Output File: `sampler_dry_run.json`.
- **Classification**: **PASS**.

### 3.6 Phase 5 — Pre-Register Evaluation Endpoints & Statistical Test
- **Observed Facts**:
  - Pre-registered primary endpoint: Validation GT-negative tile false alarm rate at threshold 0.22 $\le 17.0\%$ (baseline: $20.09\%$).
  - Clarified numerics: $\le 17.0\%$ is intentionally stricter than a 15% relative reduction ($17.0745\%$).
  - Pre-registered paired statistical test: Two-sided McNemar test with continuity correction on $n=1,827$ paired validation GT-negative tiles at $\alpha = 0.05$.
  - Pre-registered safety constraints: Validation positive oil spill recall $\ge 79.00\%$ (baseline $81.01\%$); Validation global IoU $\ge 0.7000$ (baseline $0.7223$).
  - Pre-registered EXP02B-1 fresh trajectory identity: Model initialized from certified ImageNet pretrained ResNet-34 (`B627A593...`), fresh optimizer, fresh scheduler ($T_{\max}=30$, `last_epoch=-1`), seed 42. Zero resume from C-C or EXP01 trained checkpoints.
  - Output Files: `proposed_success_criteria.md` and `experiment_identity.json`.
- **Classification**: **PASS**.

---

## 4. Artifact Inventory & Cryptographic Checksums

All 8 authoritative gate artifacts have been generated in `experiments/performance/exp02b_0_hard_negative_design_20260909_021500/`:

| Artifact Filename | Size (Bytes) | SHA-256 Hash | Description |
| :--- | :---: | :--- | :--- |
| **`candidate_manifest.json`** | 4,506,750 | `A8DE674384AC8D6789DCA0BA35C159DCB51C34A1B436D2C42B3C2A961E7F1482` | Full 13,440-tile audit manifest with Stage 1 and Stage 2 classifications |
| **`candidate_audit.json`** | 4,896 | `38948FF3C9055AC26C1F740E7DCE59B43BC647414A1BD677EE2D03FA9FA26F25` | Final audit summary, continuous distributions, and teacher diagnostic |
| **`teacher_integrity.json`** | 1,029 | `0FA7A1249A293E3706CE45CD78E11DF23F1C4EBDD8FE6C6A035CFD26601D11B5` | Certified EXP01 teacher model cryptographic and architectural audit |
| **`sampler_dry_run.json`** | 1,457 | `BE8523A39A2FA9D4BF00FE834A89C8F9F3B1A00B7B6191E09425D7E51C4E7C1F` | Empirical 13,440-draw accounting from Phase 4 simulated epoch |
| **`experiment_identity.json`** | 2,750 | `429E85B2252B1E4FDC64A8BC162B179B6C2EC042B33DF41F613143A3CA93060E` | Reproducibility metadata, hashes, seeds, and fresh trajectory contract |
| **`proposed_sampling_policy.md`**| 5,152 | `F4F40D921238EC34EE5F33A413D22CFB5138015F133E57BD74532B4ADAF42FC9` | Single proposed scientific sampling policy grounded in train statistics |
| **`proposed_success_criteria.md`**| 4,680 | `A5D2E14620021CA5DF6294D74229B85B8881BEA35CFED07E8E42B0D5D93B8C74` | Pre-registered endpoints, McNemar test specification, decision hierarchy |
| **`GATE_EXP02B_0_REPORT.md`** | — | — | This formal closure and governance document |

---

## 5. Strict Distinctions: Facts, Values, Unverified Items & Limitations

### 5.1 Observed Facts
1. All 13,440 training tiles from `spatial_split_manifest.json` were evaluated by the certified EXP01 teacher model in `model.eval()` mode with `torch.no_grad()` at threshold 0.22.
2. 8,357 tiles contain zero labeled oil spill pixels (`eligible_gt_negative`, 62.18%).
3. 2,599 GT-negative tiles produce $\ge 1$ false-positive pixel at threshold 0.22 (31.10% of negatives).
4. Exactly 1,605 GT-negative tiles produce $\ge 100$ false-positive pixels (`candidate_hard_negative`, 19.21% of negatives).
5. The Phase 4 sampler dry run executed with 0 optimizer steps and 0 backward passes, drawing 13,440 samples with an observed hard-to-ordinary exposure ratio of $3.052\times$ and 100% train isolation.
6. All baseline checkpoints (C-B pilot, C-C2 seed, C-C4 resumed) remain cryptographically immutable.

### 5.2 Expected Values
1. Total training draws per epoch: 13,440 (1,680 batches of size 8).
2. Theoretical hard-to-ordinary exposure ratio: exactly $3.000\times$.
3. Pre-registered validation GT-negative false-alarm rate threshold: $\le 17.0\%$.
4. Pre-registered McNemar significance level: $\alpha = 0.05$.
5. Pre-registered safety bounds: Recall $\ge 79.0\%$, IoU $\ge 0.70$.

### 5.3 Unverified Items
1. **Generalization of Hard-Negative Re-weighting to Held-Out Data**: Whether re-weighting the 1,605 training hard negatives during a full 30-epoch training run will cure validation false alarms without causing under-segmentation on true oil slicks cannot be observed until EXP02B-1 is trained.
2. **Held-Out Test Set Performance**: Held-out test performance is strictly unverified and unobserved in EXP02B-0.
3. **Recall Preservation on Positive Oil Slicks**: While the sampling policy maintains a substantial 36.47% share of training draws for positive spill tiles (close to the nominal baseline 37.82%), positive spill recall preservation is not guaranteed a priori and remains an empirical endpoint of EXP02B-1 (evaluated against safety bound $\ge 79.0\%$, baseline $81.01\%$, and McNemar test).

### 5.4 Technical Limitations
1. **Teacher-Training Overlap**: Hard negatives are mined from predictions on the teacher's own training set. While false positives that survive 30 epochs of training represent genuine radar lookalikes and heavy backscatter clutter, they may also reflect label noise or boundary ambiguities.
2. **Sampling with Replacement**: Under `WeightedRandomSampler(replacement=True)`, approximately 40% of draws in any single epoch are duplicates ($5,381$ duplicate draws, $8,059$ unique tiles viewed per epoch). Over 30 epochs of training, different random draws occur per epoch, but individual epochs do not see every tile exactly once.
3. **Hardware Specificity**: Candidate mining throughput was measured on a single local NVIDIA GeForce RTX 3050 Laptop GPU (27.1 tiles/s). Cloud training throughput on Tesla T4 hardware will be governed by Kaggle environment conditions.

---

## 6. Final Gate Verdict & Hard Stop Enactment

### Gate Declaration
All mandates of CAO Authorization EXP02B-0 Revision 3 have been executed to 100% completion. The empirical candidate audit, sampling policy formulation, zero-training sampler dry run, pre-registered statistical test, and evidence packaging are formally validated.

Gate EXP02B-0 is hereby declared:
$$\mathbf{CLOSED\ (PASS)}$$

### Hard Stop Enactment
Under strict CAO instructions:
- **NO EXP02B-1 training launch.**
- **NO model parameter updates.**
- **NO second scientific intervention.**
- **NO modification of canonical split data or test tiles.**
- **ALL OPERATIONS TERMINATE IMMEDIATELY UPON DELIVERY OF THIS REPORT.**
