# PHASE 5G EXP-06 HYPOTHESIS & PRE-REGISTRATION TRAINING CONTRACT
**Project:** Ocean Sentinel  
**Authority:** CAIO Scientific Governance  
**Document ID:** PHASE_5G_EXP06_HYPOTHESIS_AND_CONTRACT_20260912  
**Date:** 2026-09-12  
**State:** **FROZEN_BEFORE_TRAINING / AWAITING_CAIO_AUTHORIZATION**  
**Execution Boundary:** **ZERO TRAINING EXECUTED IN THIS PHASE**

---

## 1. Executive Summary & Purpose

EXP-05 demonstrated that candidate severity capping ($\text{fp\_pixels} \le 50,000$) broke positive tile dropout stagnation, reducing complete dropouts by $12.12\%$ ($231 \to 203$) and increasing detected positive tiles from $822$ to $850$, while maintaining an exceptional $97.56\%$ reduction in clean-water false alarms ($0.49\%$ Clean-Water FAR).

However, rigorous forensic analysis in Phase 5G revealed that **$80.9\%$ of all False Negative pixels reside on partially detected tiles ($2.84\text{M}$ out of $3.51\text{M}$ FN px)**, dominated by boundary erosion and diffuse filament thinning on large slicks ($> 19,367$ px). False Negatives outnumber False Positives by $2.08 : 1$.

EXP-06 is designed as a **single-variable intervention** to rebalance positive vs. negative gradient forces during training by introducing positive class reweighting in the Binary Cross-Entropy loss ($\text{pos\_weight} = 2.0$), while leaving the hard-negative mining sampling contract and background suppression completely intact.

---

## 2. The Falsifiable Scientific Hypothesis

$$\mathbf{EXP\text{-}06\text{ HYPOTHESIS:}}$$
> "Setting positive class weighting in Binary Cross-Entropy loss to $\text{pos\_weight} = 2.0$ while keeping hard-negative exposure fixed at $6.25\%$ ($15+1$), the candidate pool capped at $\text{fp\_pixels} \le 50,000$ ($355$ candidates), and all other $24$ experimental controls frozen, will reduce partial under-segmentation on detected oil slicks and increase global Part I validation Recall to $\ge 0.78500$ and IoU to $\ge 0.71731$, because doubling the positive loss gradient directly counteracts background pixel dominance along diffuse slick boundaries without weakening the unscaled negative gradient penalty on pure background tiles."

### Explicit Falsification Conditions
The hypothesis will be considered **FALSIFIED** if any of the following occur:
1. Validation Recall at the global best checkpoint fails to exceed $0.78500$.
2. Validation IoU at the global best checkpoint fails to exceed $0.71731$.
3. Clean-Water FAR rises to $\ge 5.00\%$ or Significant FAR rises to $\ge 3.00\%$.
4. Total FP pixels on empty validation tiles rises to $\ge 350,000\text{ pixels}$.
5. Partial-detection FN pixel mass fails to decrease relative to EXP-05 ($2,842,762\text{ px}$).

---

## 3. The Single Experimental Variable

$$\mathbf{THE\text{ }ONE\text{ }CHANGED\text{ }VARIABLE:}$$

$$\mathbf{Loss\text{ }Formulation:\text{ }Positive\text{ }Class\text{ }Weight\text{ }in\text{ }BCE\text{ }Loss\text{ }(pos\_weight)}$$

* **EXP-05 Value:** $\text{pos\_weight} = 1.0$ (standard unweighted `torch.nn.BCEWithLogitsLoss()`)
* **EXP-06 Value:** $\text{pos\_weight} = 2.0$ (`torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor([2.0]))`)
* **Combined Loss Formulation:**
  $$\mathcal{L}_{\text{EXP-06}} = 0.5 \cdot \mathcal{L}_{\text{BCE}}(p, y; w_{\text{pos}}=2.0) + 0.5 \cdot \mathcal{L}_{\text{Dice}}(p, y; \text{smooth}=1.0)$$
  where
  $$\mathcal{L}_{\text{BCE}}(p, y; w_{\text{pos}}=2.0) = - \left[ 2.0 \cdot y \log(p) + (1 - y) \log(1 - p) \right]$$

No other variable may change.

---

## 4. Complete Frozen Controls Checklist (24 Invariants)

All 24 other experimental parameters must be preserved with exact mathematical identity:
- [x] Model architecture: `ResNet34UNet(in_channels=2, num_classes=1, adaptation_method='slice_variance_scaled')`
- [x] Trainable parameters: Exactly $24,346,305$
- [x] Buffers: Exactly $19,054$ (BatchNorm running stats)
- [x] State dict total elements: Exactly $24,365,359$
- [x] Initial weights source: Pretrained EXP-01 baseline teacher checkpoint
- [x] Teacher checkpoint SHA-256: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
- [x] Standard training pool: Canonical $13,440$ tiles from TRAIN split
- [x] Spatial split manifest: `data/metadata/trujillo_2024/spatial_split_manifest.json` (SHA: `C052720A...`)
- [x] Hard-negative candidate manifest: `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json` (SHA: `3867671E...`)
- [x] Candidate pool cap: Exactly $\text{fp\_pixels} \le 50,000$
- [x] Retained candidate pool: Exactly $355$ candidates (SHA: `66421C5F...`, 0 positive pixels, 251 scenes)
- [x] Batch composition: Exactly $15\text{ standard} + 1\text{ mined} = 16\text{ tiles per batch}$
- [x] Mined exposure rate: Exactly $1 / 16 = 6.25\%$
- [x] Batches per epoch: Exactly $896$ ($13,440 / 15$)
- [x] Total epochs: Exactly $10$
- [x] Total optimizer steps: Exactly $8,960$ ($896 \times 10$)
- [x] Random seed: Exactly $42$
- [x] Sampler seed formula: $42 + 1000 \times \text{epoch}$
- [x] Optimizer: `AdamW(lr=1e-4, weight_decay=1e-2)`
- [x] Scheduler: `CosineAnnealingLR(T_max=10, eta_min=1e-6)` stepped once per epoch
- [x] Normalization constants: VV $\mu = -33.233137, \sigma = 6.489986$; VH $\mu = -19.941216, \sigma = 4.531346$
- [x] Augmentation pipeline: Random horizontal flip ($p=0.5$), random vertical flip ($p=0.5$)
- [x] Operating threshold: Fixed $\tau = 0.22$
- [x] Checkpoint selection rule: Global best Part I validation IoU
- [x] Part III firewall: 100% closed and blocked

---

## 5. Sampling Contract & Mathematics

* **Batch Size:** $16$ tiles
* **Standard Tiles per Batch:** $15$ tiles sampled without replacement per epoch from the $13,440$ standard TRAIN pool.
* **Mined Tiles per Batch:** $1$ tile sampled with replacement per epoch from the frozen $355$ capped candidate pool.
* **Exposures per Epoch:**
  - Standard exposures: $15 \times 896 = 13,440$
  - Mined exposures: $1 \times 896 = 896$
* **Candidate Draw Auditing:** Sampled candidate IDs must be logged with deterministic sequence hashing to ensure 100% pool coverage and verify zero excluded candidate injection.

---

## 6. Pre-Registered Acceptance Gates (Strict & Non-Negotiable)

The criteria for scientific success are preserved from Phase 5E/5F:

| Metric | Preregistered Success Gate | EXP-05 Baseline Value | EXP-04 Baseline Value | EXP-01 Baseline Value |
| :--- | :---: | :---: | :---: | :---: |
| **Validation Recall** | $\ge \mathbf{0.78500}$ | $0.78227$ | $0.78230$ | $0.78488$ |
| **Validation IoU** | $\ge \mathbf{0.71731}$ | $0.70813$ | $0.70910$ | $0.71691$ |
| **Clean-Water FAR** | $< \mathbf{5.00\%}$ | $0.49\%$ | $0.55\%$ | $20.09\%$ |
| **Significant FAR** | $< \mathbf{3.00\%}$ | $0.49\%$ | $0.55\%$ | $10.56\%$ |
| **Total FP Pixels (Empty)** | $< \mathbf{350,000}$ | $129,041$ | $122,937$ | $2,327,942$ |

* Acceptance requires **all five gates to PASS simultaneously** at the certified global best Part I validation checkpoint.
* No post-hoc gate modification or threshold tuning is permitted.

---

## 7. Part III Scientific Firewall

* **Part III is completely inaccessible.**
* Preflight, training, and validation scripts must enforce `assert_no_part_iii_leakage`.
* Zero Part III paths may appear in data loaders, manifests, or evaluations.

---

## 8. Observability & Telemetry Requirements

Upon authorization, EXP-06 execution must be isolated under:
`experiments/performance/exp06_positive_class_reweight/`

Required artifacts:
1. `run_state.json`: Real-time phase, progress, heartbeat (every 20 batches), ETA, loss, LR, best IoU.
2. `training.log`: Full execution log with timestamped progress lines.
3. `run_manifest.json`: Provenance record with input hashes, parameter counts, and environment metadata.
4. `history.json`: Complete 10-epoch validation metrics table.
5. `metrics.json`: Final metrics for best checkpoint.
6. `best_model.pt`: Checkpoint with highest validation IoU.
7. `last_model.pt`: Epoch 10 final checkpoint.
8. `sampled_candidate_audit.json`: Deterministic 8,960-draw sequence audit.

---

## 9. Failure & Contingency Plan

1. **Gate Failure (Recall or IoU < threshold):** If EXP-06 fails the acceptance gate, the result will be documented truthfully as FAIL without threshold manipulation.
2. **FAR Breach (Clean FAR $\ge 5.00\%$):** If positive reweighting excessively inflates false positives, the hypothesis that $\text{pos\_weight}=2.0$ preserves false-alarm gains will be rejected.
3. **Windows IPC Deadlock:** Any independent evaluation or training script must strictly run with `num_workers=0` and main entry guard.
4. **Metric API Integrity:** Training script must use `SegmentationMeter.compute()`. Epoch transaction preflight must be executed before launch.

---

## 10. Mandatory Execution Status Declaration

$$\mathbf{EXP\text{-}06\text{ STATUS: FROZEN\_BEFORE\_TRAINING}}$$
$$\mathbf{AWAITING\text{ }CAIO\text{ }TRAINING\text{ }AUTHORIZATION}$$
$$\mathbf{NO\text{ }EXP\text{-}06\text{ TRAINING\text{ }WAS\text{ }EXECUTED.}}$$
