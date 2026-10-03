# EXP-07-P0-C22-A.5: Final Canonical-State Zero-Step Rehearsal, Source/Protocol Reconciliation, and Pre-Training Gate

**Document Version:** 1.0.0  
**Date:** 2026-09-14  
**Task ID:** EXP-07-P0-C22-A.5  
**Repository:** `d:\Projects\ocean-sentinel`  
**Branch:** `master`  
**Environment:** Antigravity IDE / AG 2.0  
**Model:** Gemini 3.8 Flash High  
**Status:** COMPLETE (CANONICAL ZERO-STEP REHEARSAL VERIFIED)  
**Final Readiness Verdict:** `READY_FOR_USER_AUTHORIZATION`

---

## 1. Executive Summary & Final Readiness Gate

Task **EXP-07-P0-C22-A.5** completed the final zero-step end-to-end preflight rehearsal of the future single-variable diagnostic experiment (`EXP07_DIAG01`), executing against the newly reconstructed, authoritative ImageNet-pretrained initial model state:
```
data/ops02/initial_model_state_canonical.pt
```

### Key Rehearsal Results:
1. **Canonical Initial State Strict Verification:** The authoritative starting artifact was strictly loaded into fresh `ResNet18UNet` instances for both experimental arms (Control and Treatment). Verification confirmed exact parameters (14,310,860 trainable parameters, 11,806 buffers, 30 BatchNorm2d layers), zero missing keys, and zero unexpected keys.
2. **Preservation of Non-Canonical Random Artifact:** Historical evidence in `data/ops02/initial_model_state.pt` (SHA256: `4BB233DB629E44DE12E41F11809024B7A5BDA4DBCFB19D13752295973117E45C`) was maintained undisturbed as `NON_CANONICAL_INITIALIZATION_ARTIFACT`.
3. **End-to-End Pipeline Integration:** Full data ingestion, Candidate F hybrid sampling (72 draws/epoch, seed 42), radiometric SAR preprocessing ($\log(1+\text{DN})$, $\mu=4.424158$, $\sigma=0.469261$), and batch extraction succeeded. Control and Treatment processed the identical first batch of 8 tiles.
4. **Bitwise Pre-Loss Forward Logits Parity:** Executing the forward pass across the 30-layer BatchNorm neural network produced **bitwise identical logits** before loss calculation (Logits Checksum: `352A35C581C250FD2A1B7F507186958D91C1564C73797A8BA1E2D04301556039`).
5. **Loss Calculation Boundary:** Cross-entropy loss was evaluated without backpropagation:
   - **Control Loss (Batch 0):** `2.580346`
   - **Treatment Loss (Batch 0):** `2.626125`
   - **Loss Delta:** `+0.045779`
   Both losses are strictly finite, positive, and diverge solely as a mathematical consequence of the single independent variable (`CLASS_LOSS_WEIGHT_VECTOR`).
6. **Post-Forward BatchNorm Uniformity:** BatchNorm running statistics updated identically across both arms ($192 / 192$ tensors equal after step 0 forward pass).
7. **Strict Governance Adherence:** Zero training steps, zero backward passes, zero optimizer/scheduler steps, zero Kaggle runs, and zero HOLDOUT or Part-III access occurred.

### FINAL READINESS VERDICT: $\mathbf{READY\_FOR\_USER\_AUTHORIZATION}$
All 20 controlled dimensions, initialization lineages, data dependencies, and runtime pipelines are verified. The system is formally cleared for user authorization to execute the paired training experiment (`EXP-07-P0-C22-B`).

---

## 2. Git State & Working Tree Audit

Per governance reporting requirements, working tree state is documented transparently without misleading "clean" characterizations:

| Dimension | Observation | Lineage / Justification |
| :--- | :--- | :--- |
| **Active Branch** | `master` | Confirmed via `git branch --show-current` |
| **Staged Modifications** | 0 files | Zero staged changes (`git diff --cached --name-status` empty) |
| **Unstaged Tracked Modifications** | 2 files: `.gitignore`, `src/ocean_sentinel/ingestion/dataset.py` | Explicitly preserved pre-existing modifications mandated by task prompt |
| **Untracked Artifacts** | C22-A.5 artifacts, previous experiment audits, and test suites | Expected in-repo persistence of Level-5 machine audits |
| **C22-A.4 Source Update Audit** | `src/ocean_sentinel/ml/exp07_reference.py` | Added `ResNet18_Weights.IMAGENET1K_V1` import and 1-channel conv1 channel-mean adaptation; verified zero unintended side-effects |
| **Active Background Processes** | 0 tasks | Verified via Antigravity task manager |

---

## 3. Authoritative Preflight Cryptographic Checklist

| Dimension | Specification / Artifact | Machine-Verified Value | Verification Status |
| :--- | :--- | :--- | :--- |
| **Pretrained Backbone Dependency** | `resnet18-f37072fd.pth` | `~/.cache/torch/hub/checkpoints/resnet18-f37072fd.pth` | `VERIFIED` |
| **Pretrained File Size** | 46,830,571 bytes | 46,830,571 bytes | `EXACT MATCH` |
| **Pretrained File SHA256** | 64-character SHA256 | `F37072FD47E89C5E827621C5BAFFA7500819F7896BBACEC160B1A16C560E07EC` | `EXACT MATCH` |
| **Canonical Initial Model State** | `data/ops02/initial_model_state_canonical.pt` | `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D` | `EXACT MATCH` |
| **Canonical State Tensor Fingerprint** | 64-character SHA256 | `B472DBA86C0AA9CB1821B6C6CB172D8DCD93CE556AA256BDE931558D965F749C` | `EXACT MATCH` |
| **Preserved Non-Canonical State** | `data/ops02/initial_model_state.pt` | `4BB233DB629E44DE12E41F11809024B7A5BDA4DBCFB19D13752295973117E45C` | `PRESERVED` |
| **Freeze Specification Hash** | `OPS02_DATASET_FREEZE_SPEC_v1.0.1.json` | `5717B6A45EB2A6EBBAF6A2BA67104B8C13FDFFCF525287CC6E95BA3D3F148FFD` | `EXACT MATCH` |
| **Physical Dataset Manifest Hash** | `ops02_physical_dataset_manifest_v1.json` | `F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102` | `EXACT MATCH` |
| **Partition Manifest Hash** | `ops02_partition_manifest_v1.json` | `757DEAF7A7E72BE331843B518A99AF32E14D68A080822F1D9B4FDBADF889F94D` | `EXACT MATCH` |
| **Parent Cluster Manifest Hash** | `ops02_parent_cluster_manifest_v1.json` | `88A835848FEA9EBA4AFEB77D01B6370E0D1DF7BCE640AE246F7A9B310F0A0E2B` | `EXACT MATCH` |
| **Taxonomy Canonicalization Hash** | `ops02_c19_taxonomy_canonicalization_v1.json` | `C201C7B1E9762BD0EAC0486D58019F0D90D9A1FDE918AC19E868725890C5369A` | `EXACT MATCH` |
| **Control Vector Compact JSON Hash** | Compact UTF-8 representation | `48B6F027519588324F2FE061BA6B8931B71339CDC410BF0FE19EF6A34AEF6039` | `EXACT MATCH` |
| **Treatment Vector Compact JSON Hash**| Compact UTF-8 representation | `42F09924BFFA5FC46DAF7E8E0FC36E08CFDC9900EF1447846F2C795105B9AF06` | `EXACT MATCH` |

---

## 4. Controlled Dimensions Taxonomy (1 IV + 18 Scientific Invariants + 1 Governance Invariant)

The experiment is strictly single-variable under the 20-dimensional specification:

```
EXP07_DIAG01 Controlled Experimental Framework
├── Independent Variable (1 Dimension)
│   └── CLASS_LOSS_WEIGHT_VECTOR: Control [Historical Inverse Frequency] vs Treatment [Uniform 1.0]
├── Scientific Invariants (18 Dimensions)
│   ├── INV-01: Dataset Specification (OPS02_v1.0.1_FROZEN, 212 sample pairs)
│   ├── INV-02: Partition Allocation (132 TRAIN / 40 DEV / 40 HOLDOUT)
│   ├── INV-04: Physical Image Format (GeoTIFF float32 single-band VV SAR, 256x256)
│   ├── INV-05: Preprocessing Pipeline (np.log1p, valid DN > 0, nodata = 0.0)
│   ├── INV-06: Radiometric Normalization (mu = 4.424158, sigma = 0.469261)
│   ├── INV-07: Canonical Taxonomy (12 dense classes 0..11)
│   ├── INV-08: Excluded Source Classes (Labels 3, 9, 14 mapped to ignore_index = -100)
│   ├── INV-09: Architecture Specification (ResNet18-UNet, 14,310,860 trainable parameters, 30 BN layers)
│   ├── INV-10: Pretrained Backbone (ResNet18_Weights.IMAGENET1K_V1, resnet18-f37072fd.pth)
│   ├── INV-11: Optimization Algorithm (AdamW, beta1=0.9, beta2=0.999, eps=1e-8)
│   ├── INV-12: Base Learning Rate (0.0005)
│   ├── INV-13: Weight Decay (0.01 applied to 2D conv/linear weights only)
│   ├── INV-14: Learning Rate Schedule (LinearWarmupCosineAnnealingLR, T_max=30, T_warmup=3, eta_min=1e-6)
│   ├── INV-15: Batch Dynamics (Physical batch = 8, accumulation = 2, effective batch = 16)
│   ├── INV-16: Sampler Strategy (Candidate F Hybrid, 72 draws/epoch, replacement=True)
│   ├── INV-17: RNG Architecture (Base seed 42, epoch formula 42 + epoch * 1000)
│   ├── INV-18: Data Augmentation (Disabled / deterministic loaders)
│   └── INV-19: Benchmark Metric & Stopping Rule (dev_mIoU_phenomena, patience=10, min_epoch=15)
└── Governance Invariant (1 Dimension)
    └── INV-03: Partition Firewall Boundaries (Zero HOLDOUT / Zero Part-III access)
```

---

## 5. First-Batch Execution & Parity Verification

The rehearsal verified that prior to the loss calculation boundary, both experimental conditions execute over identical data and produce identical activations:

```
[FIRST MINIBATCH REHEARSAL METRICS]
--------------------------------------------------------------------------------
1. Candidate F Sampler Schedule (72 draws) SHA256 : 6462A1ED44D93FAC2603EEC0DFF1C05D25F03586AA2732B84E359823782F3C95
2. First Batch Sample IDs (8 samples)             : Exactly identical across Control and Treatment
3. First Batch Input Image Checksum               : 5119CC6280FDE65702DC58D2856E6E472A4A8C9AAE13F866F5E34C526EFCB9A6
4. First Batch Target Tensor Checksum             : BA88C7851EF76FEB1035E9A33CFB2CCF696489FCDF8C032D2E854CB4BA52582C
5. First Batch Validity Mask Checksum             : 33A150BCEB13C1A992231E65B4FAD16815212FC06CDB408996D32EEB2CEF9EBB
6. Pre-Loss Output Logits Checksum                : 352A35C581C250FD2A1B7F507186958D91C1564C73797A8BA1E2D04301556039
7. Pre-Forward BatchNorm State Parity             : 30 / 30 layers bitwise identical
8. Post-Forward BatchNorm Running Stats Parity    : 30 / 30 layers bitwise identical (1 batch tracked)
--------------------------------------------------------------------------------
FIRST BATCH LOGITS BITWISE EQUALITY               : 100% BITWISE EQUAL
```

---

## 6. Loss Boundary Calculation

Loss was computed across the first batch of 8 samples ($[8, 12, 256, 256]$ logits against $[8, 256, 256]$ targets):

$$\mathcal{L}_{\text{Control}} = 2.580346, \quad \mathcal{L}_{\text{Treatment}} = 2.626125, \quad \Delta \mathcal{L} = +0.045779$$

Both values are mathematically finite, strictly positive, and demonstrate the expected divergence resulting from the differing loss weight contracts. Immediately following the loss calculation, execution terminated without initiating backpropagation.

---

## 7. Zero-Training & Quarantine Compliance Audit

```
[GOVERNANCE BOUNDARY VERIFICATION]
--------------------------------------------------------------------------------
1. Training Optimization Steps (optimizer.step)   : ZERO (0 calls)
2. Gradient Backpropagation (loss.backward)      : ZERO (0 calls)
3. Learning Rate Scheduler Steps (scheduler.step) : ZERO (0 calls)
4. Training Epochs Executed                       : ZERO (0 epochs)
5. Cloud Execution (Kaggle API)                   : ZERO (0 runs)
6. Part-III Benchmark Ground Truth Access         : ZERO (0 reads)
7. HOLDOUT Partition Access                       : ZERO (0 reads)
8. Network Activity                               : ZERO (0 network requests)
9. Active Background Tasks                        : ZERO (0 tasks)
10. Git Operations                                : master (0 staged, 0 commit/push)
--------------------------------------------------------------------------------
COMPLIANCE STATUS                                 : 100% COMPLIANT
```

---

## 8. Automated Guardrail Verification Matrix

A comprehensive suite of 121 tests across 11 test modules was executed:

| Test Module | Coverage Area | Tests Run | Passed | Failed | Skipped |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [test_exp07_p0_c22a5_canonical_preflight_guardrails.py](file:///d:/Projects/ocean-sentinel/tests/test_exp07_p0_c22a5_canonical_preflight_guardrails.py) | C22-A.5 Canonical Rehearsal & Readiness | 11 | 11 | 0 | 0 |
| [test_exp07_p0_c22a4_initialization_provisioning_guardrails.py](file:///d:/Projects/ocean-sentinel/tests/test_exp07_p0_c22a4_initialization_provisioning_guardrails.py) | C22-A.4 Provisioning & Determinism | 12 | 12 | 0 | 0 |
| [test_exp07_p0_c22a3_initialization_guardrails.py](file:///d:/Projects/ocean-sentinel/tests/test_exp07_p0_c22a3_initialization_guardrails.py) | C22-A.3 Forensic Lineage Gate | 8 | 8 | 0 | 0 |
| [test_exp07_p0_c22a2_preflight_guardrails.py](file:///d:/Projects/ocean-sentinel/tests/test_exp07_p0_c22a2_preflight_guardrails.py) | C22-A.2 Historical Zero-Step Rehearsal | 8 | 8 | 0 | 0 |
| [test_exp07_p0_c22a1_closure_guardrails.py](file:///d:/Projects/ocean-sentinel/tests/test_exp07_p0_c22a1_closure_guardrails.py) | C22-A.1 Governance Closure | 10 | 10 | 0 | 0 |
| [test_exp07_p0_c22a_readiness_guardrails.py](file:///d:/Projects/ocean-sentinel/tests/test_exp07_p0_c22a_readiness_guardrails.py) | C22-A Loss Weight Reconciliation | 16 | 16 | 0 | 0 |
| [test_exp07_p0_c21_diagnostic_protocol_guardrails.py](file:///d:/Projects/ocean-sentinel/tests/test_exp07_p0_c21_diagnostic_protocol_guardrails.py) | C21 Diagnostic Protocol Invariants | 21 | 21 | 0 | 0 |
| [test_exp07_p0_c20_cross_domain_guardrails.py](file:///d:/Projects/ocean-sentinel/tests/test_exp07_p0_c20_cross_domain_guardrails.py) | C20 Cross-Domain Governance | 11 | 11 | 0 | 0 |
| [test_artifact_policy.py](file:///d:/Projects/ocean-sentinel/tests/test_artifact_policy.py) | Repository Artifact Policy | 6 | 6 | 0 | 0 |
| [test_part_iii_firewall.py](file:///d:/Projects/ocean-sentinel/tests/test_part_iii_firewall.py) | Part-III Isolation Firewall | 6 | 6 | 0 | 0 |
| [test_ocean_sentinel_agent_learning_framework.py](file:///d:/Projects/ocean-sentinel/tests/test_ocean_sentinel_agent_learning_framework.py) | Agent Learning Framework | 12 | 12 | 0 | 0 |
| **TOTAL** | **Comprehensive System Gate** | **121** | **121** | **0** | **0** |

**Execution Runtime:** 6.80 seconds.

---

## 9. Durable Output Artifacts Created / Updated

1. Live Telemetry: [exp07_p0_c22a5_run_state.json](file:///d:/Projects/ocean-sentinel/scratch/exp07_p0_c22a5_run_state.json)
2. Canonical Rehearsal Script: [rehearse_exp07_diag01_canonical_zero_step.py](file:///d:/Projects/ocean-sentinel/scripts/rehearse_exp07_diag01_canonical_zero_step.py)
3. Operational Audit: [ops02_c22a5_canonical_zero_step_preflight_v1.json](file:///d:/Projects/ocean-sentinel/data/ops02/audits/ops02_c22a5_canonical_zero_step_preflight_v1.json)
4. Incident Register: [exp07_p0_c22a5_incident_register_v1.json](file:///d:/Projects/ocean-sentinel/data/metadata/exp07_p0_c22a5_incident_register_v1.json)
5. Automated Guardrails: [test_exp07_p0_c22a5_canonical_preflight_guardrails.py](file:///d:/Projects/ocean-sentinel/tests/test_exp07_p0_c22a5_canonical_preflight_guardrails.py)
6. Pre-Training Completion Report: [EXP07_P0_C22A5_CANONICAL_ZERO_STEP_PREFLIGHT_AND_READINESS_20260914.md](file:///d:/Projects/ocean-sentinel/experiments/EXP-07/EXP07_P0_C22A5_CANONICAL_ZERO_STEP_PREFLIGHT_AND_READINESS_20260914.md)

---

## 10. Pre-Training Authorization Boundary

$$\mathbf{FINAL\;VERDICT:\;READY\_FOR\_USER\_AUTHORIZATION}$$

All preconditions for Level-5 operational reproducibility are satisfied:
- The canonical ImageNet-pretrained initial model state is verified and loaded.
- Control and Treatment arms are proven identical across data, architecture, and activations prior to loss calculation.
- The loss calculation boundary operates cleanly with finite, strictly positive losses.
- All non-training and data quarantine boundaries remain 100% intact.

The system is fully prepared for user authorization to proceed to **EXP-07-P0-C22-B** (execution of the paired diagnostic training runs).
