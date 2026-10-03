# PHASE EXP-07-P0 — SCIENTIFIC PROTOCOL DESIGN CLOSURE REPORT
## Ocean Sentinel · 2026-09-13

---

## 1. EXECUTIVE DECISION

> A. COMPLETE — EXP-07 SCIENTIFIC PROTOCOL FULLY SPECIFIED

All 14 Open Protocol Decisions from the Phase 8-P3 pre-training audit have been resolved and frozen.
Training remains PROHIBITED until explicit operator GPU authorization.

---

## 2. PREFLIGHT STATE (STEP 0)

| Check | Result |
|:---|:---:|
| Branch | master |
| Staged changes | 0 |
| Tracked modified | 2 (.gitignore, dataset.py) |
| EXP-06 best_model.pt SHA256 | VERIFIED |
| Part-I manifest SHA256 | VERIFIED |
| OPS-01 manifest_v4 SHA256 | VERIFIED |

---

## 3. EVIDENCE SURVEYED (STEPS 1-5)

| Artifact | Reviewed |
|:---|:---:|
| ops01_taxonomy_v1.json | YES |
| ops01_dataset_sufficiency_v5.json | YES |
| ops01_physical_dataset_manifest_v4.json | YES |
| ops01_p3_preprocessing_audit_v1.json | YES |
| ops01_p3_training_readiness_contract_v1.json | YES |
| ocean_sentinel_governance_rules_v1.md (GOV-RULE-001..045) | YES |
| ocean_sentinel_reproducibility_levels_v1.json | YES |
| exp06_frozen_dev_baseline.json | YES |
| acceptance_gate_semantics_audit.json | YES |
| exp06_proxy_zero_shot_diagnostic.json | YES (header + tail) |
| exp06_proxy_zero_shot_diagnostic_reproduction.json | YES (scientific interpretation) |
| run_manifest.json (EXP-06) | YES |
| PHASE_8_P3_FINAL_PRETRAINING_AUDIT_20260913.md | YES (all 528 lines) |
| PHASE_5G_EXP06_HYPOTHESIS_AND_TRAINING_CONTRACT_20260912.md | YES |
| src/ocean_sentinel/models.py | YES |

---

## 4. SCIENTIFIC QUESTION FORMULATED

Primary: Can a compact ResNet18-UNet trained on 72 OPS-01 TRAIN samples achieve DEV mIoU >= 0.30 across 12 eligible maritime SAR backscatter classes?

Secondary:
- SQ-1: Can multi-class supervision suppress natural lookalike classes (BS, LWA, IWs) that caused >89% proxy alarm rate in EXP-06?
- SQ-2: Does multi-class training produce better ocean scene representations than EXP-06's binary approach?
- SQ-3: What is achievable segmentation performance given 72 TRAIN samples and severe class imbalance?

Evidence basis: EXP-06 proxy evaluation (89.75% provisional alarm rate across 517 patches, SEMANTIC_STATUS_UNRESOLVED) motivates multi-class supervision. Per GOV-RULE-008: this is correlational evidence, NOT confirmed causation.

---

## 5. HYPOTHESIS AND ACCEPTANCE GATES

Hypothesis: ResNet18-UNet with 12-class CE + inverse-frequency class weighting + WeightedRandomSampler + 50-epoch CosineAnnealing + conservative flip augmentation on OPS-01 TRAIN will achieve DEV mIoU >= 0.30.

Falsification: DEV mIoU < 0.30 OR DEV BG IoU < 0.60 OR HOLDOUT contamination OR OS pixels in pipeline.

Acceptance Gates (FROZEN):

| Gate | Metric | Threshold |
|:---|:---|:---:|
| AG-EXP07-01 | DEV mIoU | >= 0.30 |
| AG-EXP07-02 | DEV BG IoU | >= 0.60 |
| AG-EXP07-03 | DEV Macro Recall | >= 0.25 |
| AG-EXP07-04 | Training completed | 50 epochs or documented early stop |
| AG-EXP07-05 | HOLDOUT timing | Exactly once post-DEV selection |
| AG-EXP07-06 | OS pixels in pipeline | = 0 |

---

## 6. ALL 14 OPEN PROTOCOL DECISIONS RESOLVED

| Decision | Topic | Resolution |
|:---|:---|:---|
| OPEN-PREPROC-001 | Value domain | 10*log10(DN+1e-6) pseudo-dB |
| OPEN-PREPROC-002 | Normalization stats | TRAIN only, computed at EXP-07-P1 preflight |
| OPEN-PREPROC-003 | Augmentation | H-flip + V-flip p=0.5, TRAIN only |
| OPEN-PREPROC-004 | Label encoding | 12-class CE, IGNORE=255 |
| OPEN-LOADER-001 | DataLoader | OPS01Dataset (contract specified) |
| OPEN-LOADER-002 | Class balancing | WeightedRandomSampler (inverse dom-class-freq) |
| OPEN-LOADER-003 | num_workers | 0, pin_memory=False |
| OPEN-LOADER-004 | Batch size | 8 |
| OPEN-ARCH-001 | Architecture | ResNet18-UNet, 1-band, 12-class, from scratch |
| OPEN-LOSS-001 | Loss function | Weighted multi-class CE, median-normalized, cap=10 |
| OPEN-OPT-001 | Optimizer/scheduler | AdamW(lr=1e-3,wd=1e-2) + CosineAnnealingLR(T_max=50) |
| OPEN-SEED-001 | Seed policy | GLOBAL_SEED=42, cuDNN deterministic |
| OPEN-METRIC-001 | Metric definitions | mIoU (12 classes), DEV-based selection, HOLDOUT once |
| OPEN-CKPT-001 | Checkpoint policy | Save on best DEV mIoU; best_model.pt + last_model.pt |

---

## 7. OPS-01 DATA INTERFACE CONTRACT

Loader contract formally specified in: data/metadata/ops01_loader_contract_v1.json
SHA256: 0E31378071E102EE4896D2AA7F2777F66908EFF5A7494844B611CF3F6B7D67C8

Key contract invariants:
- OPS01Dataset (new class, distinct from TrujilloTileDataset)
- Returns (float32 (1,256,256), int64 (256,256))
- LABEL_LUT: source_label_id -> output_idx (0-11) or IGNORE (255)
- Part-III firewall assertion at init
- Zero silent failures; SHA256 verified on every sample

Label LUT (FROZEN):
  BG=0->0, AF=1->1, BS=2->2, IB=3->255(IGNORE), LWA=4->3,
  MCC=5->4, OF=6->5, POW=7->6, RF=8->7, SI=9->255(IGNORE),
  WS=10->8, Eddy=11->9, IWs=12->10, HM=13->11, OS=14->255(EXCLUDED)

---

## 8. ARTIFACTS PRODUCED

| Artifact | Path | SHA256 |
|:---|:---|:---|
| Protocol specification | experiments/PHASE_EXP07_P0_SCIENTIFIC_PROTOCOL_AND_OPS01_CONTRACT_20260913.md | F7BDE340... |
| Loader contract JSON | data/metadata/ops01_loader_contract_v1.json | 0E313780... |
| Protocol design JSON | data/metadata/exp07_protocol_design_v1.json | 2B292174... |
| Run state (ignored) | scratch/exp07_p0_run_state.json | IGNORED (+0 porcelain) |

---

## 9. FINAL GIT STATE (POST-ARTIFACT — PER GOV-RULE-042)

| Check | Count |
|:---|:---:|
| Staged changes | 0 |
| Tracked modifications | 2 (.gitignore, dataset.py — unchanged from P3 baseline) |
| Untracked files (total) | 298 |
| C3/C6 baseline | 295 |
| P0 new untracked | +3 (protocol MD, loader_contract JSON, protocol_design JSON) |
| P0 telemetry (scratch/) | +0 (ignored by .gitignore:50) |

---

## 10. TRAINING AUTHORIZATION STATUS

Training remains PROHIBITED. The following 4 prerequisites are outstanding:

1. OPS01Dataset class: TO_BE_IMPLEMENTED (contract: data/metadata/ops01_loader_contract_v1.json)
2. exp07_normalization_stats.json: TO_BE_COMPUTED (requires rasterio on TRAIN images)
3. class_weights_exp07.json: TO_BE_COMPUTED (from TRAIN class pixel distribution)
4. Operator GPU training authorization: PENDING

---

## 11. EXPLICIT NON-CLAIMS

P0 does NOT establish:
- Training has been executed
- Model performance on any benchmark
- OS class detection of any kind
- Part-III access or evaluation
- Modification of EXP-06 or Part-I frozen artifacts
- That 72 TRAIN samples are sufficient (this is what EXP-07 will test)

---

*Generated: 2026-09-13 | EXP-07-P0 | Ocean Sentinel | Branch: master*
*14/14 Open Protocol Decisions resolved. 3 P0 artifacts created. Git: 0 staged, 2 tracked mods, 298 untracked.*
*Training PROHIBITED pending operator GPU authorization.*
