# EXP-07-P0-C22-A.4: Canonical ImageNet Backbone Provisioning, Verification, and Deterministic Initial-State Reconstruction

**Document Version:** 1.0.0  
**Date:** 2026-09-14  
**Task ID:** EXP-07-P0-C22-A.4  
**Repository:** `d:\Projects\ocean-sentinel`  
**Branch:** `master`  
**Environment:** Antigravity IDE / AG 2.0  
**Model:** Gemini 3.8 Flash High  
**Status:** COMPLETE (CANONICAL PROVISIONING & DETERMINISTIC RECONSTRUCTION VERIFIED)  
**Final Readiness Verdict:** `READY_FOR_NEXT_PREFLIGHT`  
*(Note: Final training authorization remains withheld until subsequent zero-step preflight rehearsal completes against the canonical state)*

---

## 1. Executive Summary & Readiness Verdict

Task **EXP-07-P0-C22-A.4** resolved the sole scientific blocker identified in `EXP-07-P0-C22-A.3`: the absence of the frozen ImageNet-pretrained backbone (`torchvision.models.ResNet18_Weights.IMAGENET1K_V1`) in the local environment and the non-canonical status of `data/ops02/initial_model_state.pt`.

### Key Outcomes:
1. **Official Pretrained Dependency Provisioned:** The authoritative pretrained weights file `resnet18-f37072fd.pth` was downloaded exclusively from the official PyTorch source (`https://download.pytorch.org/models/resnet18-f37072fd.pth`) into the standard local cache (`~/.cache/torch/hub/checkpoints/`).
2. **Cryptographic Integrity Proven:** The complete SHA256 cryptographic digest of the downloaded file was verified as:
   $$\text{SHA256} = \mathbf{\text{F37072FD47E89C5E827621C5BAFFA7500819F7896BBACEC160B1A16C560E07EC}}$$
   Confirming that the TorchVision filename prefix `f37072fd` strictly represents the first 8 characters of the complete file digest.
3. **Preservation of Non-Canonical Random Evidence:** The pre-existing random-initialized state artifact `data/ops02/initial_model_state.pt` (SHA256: `4BB233DB629E44DE12E41F11809024B7A5BDA4DBCFB19D13752295973117E45C`) was classified as `NON_CANONICAL_INITIALIZATION_ARTIFACT` and preserved in place without deletion or overwriting.
4. **Deterministic Canonical Model State Reconstructed:** A fresh canonical initial model state was materialized at `data/ops02/initial_model_state_canonical.pt` combining the official pretrained backbone, canonical 1-channel `conv1` arithmetic mean adaptation, and seed-42 decoder/head initialization.
5. **Clean-Process Determinism Verified:** Across two independent, clean Python processes, identical construction produced bitwise 100% identical state dictionaries across all 192 tensors ($192 / 192$ tensors equal, file SHA256: `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D`, state_dict fingerprint: `B472DBA86C0AA9CB1821B6C6CB172D8DCD93CE556AA256BDE931558D965F749C`).
6. **Strict Governance Adherence:** Zero training steps, zero backward passes, zero optimizer/scheduler steps, zero Kaggle runs, and zero HOLDOUT or Part-III access occurred. Network access was strictly restricted to downloading the single official PyTorch weights artifact.

### Final Readiness Decision: $\mathbf{READY\_FOR\_NEXT\_PREFLIGHT}$
All initialization lineage and scientific dependencies are resolved. In accordance with governance constraints, `READY_FOR_USER_AUTHORIZATION` is withheld until the end-to-end zero-step preflight rehearsal is repeated against the canonical state artifact.

---

## 2. Pretrained Dependency Forensic Manifest

| Dimension | Specification | Machine-Verified Value | Status |
| :--- | :--- | :--- | :--- |
| **TorchVision Weight Enum** | `torchvision.models.ResNet18_Weights.IMAGENET1K_V1` | Confirmed via `torchvision.models.resnet18` | MATCH |
| **Official Source URL** | `https://download.pytorch.org/models/resnet18-f37072fd.pth` | Confirmed from TorchVision metadata | MATCH |
| **Artifact Filename** | `resnet18-f37072fd.pth` | `resnet18-f37072fd.pth` | MATCH |
| **Local Cache Path** | `~/.cache/torch/hub/checkpoints/resnet18-f37072fd.pth` | `C:\Users\Dheeraj\.cache\torch\hub\checkpoints\resnet18-f37072fd.pth` | VERIFIED |
| **File Size (Bytes)** | 46,830,571 bytes (44.66 MB) | 46,830,571 bytes | EXACT MATCH |
| **Complete SHA256** | 64 hex characters | `F37072FD47E89C5E827621C5BAFFA7500819F7896BBACEC160B1A16C560E07EC` | VERIFIED |
| **Filename Prefix Match** | First 8 chars == `f37072fd` | `F37072FD` == `f37072fd` (case-insensitive) | EXACT MATCH |
| **Python Version** | 3.10.9 | Python 3.10.9 | VERIFIED |
| **PyTorch Version** | 2.1.1+cpu | 2.1.1+cpu | VERIFIED |
| **TorchVision Version** | 0.16.1+cpu | 0.16.1+cpu | VERIFIED |

---

## 3. Preservation of Historical Non-Canonical Evidence

Per task governance, historical evidence of the random initialization discovered in C22-A.3 is preserved without destruction:

| Field | Non-Canonical Historical Artifact | Canonical Future Artifact |
| :--- | :--- | :--- |
| **File Path** | `data/ops02/initial_model_state.pt` | `data/ops02/initial_model_state_canonical.pt` |
| **Classification** | `NON_CANONICAL_INITIALIZATION_ARTIFACT` | `CANONICAL_FUTURE_EXP07_DIAG01_INITIAL_STATE` |
| **File Size (Bytes)** | 57,354,338 | 57,356,426 |
| **File SHA256** | `4BB233DB629E44DE12E41F11809024B7A5BDA4DBCFB19D13752295973117E45C` | `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D` |
| **Tensor State Fingerprint** | `E9343B5DE995D2DD0985C62FC57FC9B154974732F48BF6CCA81F62CAA8C1FA7D` | `B472DBA86C0AA9CB1821B6C6CB172D8DCD93CE556AA256BDE931558D965F749C` |
| **Pretrained Status** | `False` (seed-42 random initialization) | `True` (ResNet18_Weights.IMAGENET1K_V1) |
| **Preservation Rule** | Kept in place; never overwritten | Created as dedicated canonical file |

---

## 4. Canonical Construction Protocol & RNG Sequencing

To guarantee absolute determinism, the model construction sequence was analyzed and locked to prevent RNG divergence between newly initialized decoder/head layers.

### Step-by-Step Construction Order:
1. **Base Seed Configuration:** `random.seed(42)`, `np.random.seed(42)`, `torch.manual_seed(42)` on CPU.
2. **Backbone Loading:** `base_resnet = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)`. Pretrained weights are loaded directly from the verified local checkpoint; zero RNG state is consumed.
3. **1-Channel Input Adaptation (`conv1`):** 
   - `self.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)` is instantiated.
   - Pretrained RGB weights from `base_resnet.conv1.weight` (shape `[64, 3, 7, 7]`) are averaged across dimension 1:
     $$\text{self.conv1.weight.copy\_}(\text{base\_resnet.conv1.weight.mean}(\text{dim}=1, \text{keepdim}=\text{True}))$$
   - Resulting `conv1.weight` has shape `[64, 1, 7, 7]` and exact channel-mean values.
4. **Encoder Block Binding:** Pretrained layers `bn1`, `relu`, `maxpool`, `layer1`, `layer2`, `layer3`, and `layer4` are bound directly from `base_resnet`. Zero RNG state is consumed.
5. **Decoder Instantiation:** Blocks `dec4`, `dec3`, `dec2`, `dec1`, `final_up`, and `final_conv` are sequentially instantiated under the deterministic PyTorch seed-42 stream (Kaiming uniform default init).
6. **12-Class Segmentation Head:** `self.head = nn.Conv2d(32, 12, kernel_size=1)` is instantiated under the active seed-42 stream.
7. **BatchNorm Momentum Uniformity:** `bn_momentum = 0.05` is uniformly applied across all 30 `BatchNorm2d` layers.

---

## 5. Model Structure & Tensor Count Verification

Validation against frozen protocol specifications confirmed exact architectural conformance:

| Structural Metric | Frozen Contract Requirement | Canonical Model Verification | Conformance |
| :--- | :--- | :--- | :--- |
| **Input Channels** | 1 (`[B, 1, 256, 256]`) | 1 | PASS |
| **Output Classes** | 12 (`[B, 12, 256, 256]`) | 12 | PASS |
| **BatchNorm Momentum** | 0.05 | 0.05 across all 30 BN layers | PASS |
| **BatchNorm2d Modules** | 30 | 30 | PASS |
| **Trainable Parameters** | 14,310,860 | 14,310,860 | EXACT MATCH |
| **Float Buffers** | 11,776 | 11,776 | EXACT MATCH |
| **Integer Buffers** | 30 (`num_batches_tracked`) | 30 | EXACT MATCH |
| **Total State Elements** | 14,322,666 | 14,322,666 | EXACT MATCH |
| **Total StateDict Tensors** | 192 | 192 | EXACT MATCH |
| **Strict Loading (`strict=True`)** | Fresh model loads with 0 errors | 0 missing keys, 0 unexpected keys | PASS |
| **Numerical Integrity** | No NaN, no Inf | 0 NaN, 0 Inf across all 192 tensors | PASS |

### Pretrained Backbone Identity Verification:
- `layer1.0.conv1.weight`: bitwise identical to `resnet18-f37072fd.pth` (`layer1.0.conv1.weight`).
- `layer4.1.bn2.running_mean`: bitwise identical to `resnet18-f37072fd.pth` (`layer4.1.bn2.running_mean`).
- `conv1.weight`: exact channel-mean of checkpoint RGB tensor; maximum absolute difference between `conv1.weight` and mean of RGB tensor is $0.0$.

---

## 6. Deterministic Reconstruction Verification

To establish Level-5 reproducibility, the canonical initial state was independently reconstructed from scratch in two separate clean Python processes:

| Run Identifier | Process Scope | Target Output Path | File SHA256 | StateDict Fingerprint | Bitwise Tensor Match |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Run A** | Clean Process 1 | `initial_model_state_canonical.pt` | `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D` | `B472DBA86C0AA9CB1821B6C6CB172D8DCD93CE556AA256BDE931558D965F749C` | Baseline |
| **Run B** | Clean Process 2 | `initial_model_state_canonical.pt` | `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D` | `B472DBA86C0AA9CB1821B6C6CB172D8DCD93CE556AA256BDE931558D965F749C` | **192 / 192 Tensors Equal** |

Both runs generated 100% byte-identical serialized files and identical SHA256 digests.

---

## 7. Historical C16 vs. Future Canonical Initialization Boundary

To prevent epistemic overclaim, the exact relationship between historical C16 and future `EXP07_DIAG01` is formally documented:

1. **Historical C16 Execution:** Executed with `pretrained=True` on a Kaggle cloud VM where `resnet18-f37072fd.pth` was downloaded at runtime. Training produced `best_model.pt` (epoch 17) and `last_model.pt` (epoch 27). The initial epoch-0 state dictionary was **not persisted to disk**.
2. **Future Canonical Replicate:** Independently reconstructed from the authoritative frozen protocol rules and the exact same pretrained weights artifact.
3. **Epistemic Boundary:** No claim of unseen historical C16 epoch-0 byte identity is made. Future canonical state is verified against the canonical protocol specification, not against unpersisted historical artifacts.

---

## 8. Governance & Zero-Training Compliance

All non-training boundaries were strictly enforced throughout task execution:

```
[GOVERNANCE BOUNDARY VERIFICATION]
--------------------------------------------------------------------------------
1. Model Training Updates (optimizer.step)        : ZERO (0 calls)
2. Gradient Backpropagation (loss.backward)      : ZERO (0 calls)
3. Learning Rate Scheduler Steps (scheduler.step) : ZERO (0 calls)
4. Training Epochs Executed                       : ZERO (0 epochs)
5. Cloud Execution (Kaggle API)                   : ZERO (0 runs)
6. Part-III Benchmark Ground Truth Access         : ZERO (0 reads)
7. HOLDOUT Partition Access                       : ZERO (0 reads)
8. Network Activity                               : Download of resnet18-f37072fd.pth only
9. Active Background Tasks                        : ZERO (0 tasks)
10. Git Branch & Modifications                    : master (0 staged, 0 commit/push)
--------------------------------------------------------------------------------
COMPLIANCE STATUS                                 : 100% COMPLIANT
```

---

## 9. Comprehensive Guardrail Verification Matrix

A comprehensive test suite of 110 tests across 10 test modules was executed to guarantee system-wide integrity:

| Test Module | Focus Area | Tests Run | Passed | Failed | Skipped |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `test_exp07_p0_c22a4_initialization_provisioning_guardrails.py` | C22-A.4 Provisioning & Determinism | 12 | 12 | 0 | 0 |
| `test_exp07_p0_c22a3_initialization_guardrails.py` | C22-A.3 Forensic Lineage Gate | 8 | 8 | 0 | 0 |
| `test_exp07_p0_c22a2_preflight_guardrails.py` | C22-A.2 Zero-Step Rehearsal | 8 | 8 | 0 | 0 |
| `test_exp07_p0_c22a1_closure_guardrails.py` | C22-A.1 Governance Closure | 10 | 10 | 0 | 0 |
| `test_exp07_p0_c22a_readiness_guardrails.py` | C22-A Loss Weight Reconciliation | 16 | 16 | 0 | 0 |
| `test_exp07_p0_c21_diagnostic_protocol_guardrails.py` | C21 Protocol Invariants | 21 | 21 | 0 | 0 |
| `test_exp07_p0_c20_cross_domain_guardrails.py` | C20 Cross-Domain Governance | 11 | 11 | 0 | 0 |
| `test_artifact_policy.py` | Artifact Ingestion Policy | 6 | 6 | 0 | 0 |
| `test_part_iii_firewall.py` | Part-III Isolation Firewall | 6 | 6 | 0 | 0 |
| `test_ocean_sentinel_agent_learning_framework.py` | Agent Learning Framework | 12 | 12 | 0 | 0 |
| **TOTAL** | **10 Test Suites** | **110** | **110** | **0** | **0** |

Execution time: **5.81s** across 110 tests. 100% pass rate.

---

## 10. Durable Artifacts Created / Updated

1. `scratch/exp07_p0_c22a4_run_state.json`: Live operational telemetry tracking task progression and safety boundaries.
2. `data/ops02/audits/ops02_c22a4_initialization_provisioning_v1.json`: Formal operational audit documenting the download, verification, and deterministic construction.
3. `data/ops02/manifests/exp07_diag01_initialization_lineage_v1.json`: Machine-readable lineage manifest connecting architecture, weights, adaptation rules, and hashes.
4. `data/metadata/exp07_p0_c22a4_incident_register_v1.json`: Incident register cataloging the resolution of `INC-C22A4-001`.
5. `data/ops02/initial_model_state_canonical.pt`: Authoritative canonical initial model state tensor artifact.
6. `tests/test_exp07_p0_c22a4_initialization_provisioning_guardrails.py`: Automated regression test suite enforcing all C22-A.4 requirements.
7. `experiments/EXP-07/EXP07_P0_C22A4_INITIALIZATION_PROVISIONING_AND_RECONSTRUCTION_20260914.md`: This completion report.

---

## 11. Final Recommendation & Authorization Boundary

The scientific blocker that prohibited `EXP07_DIAG01` from proceeding in `C22-A.3` is fully resolved:
- The authoritative ImageNet weights are locally provisioned and cryptographically verified.
- The canonical initial state has been deterministically built and proven identical across independent clean builds.
- The non-canonical random state has been preserved as forensic evidence.

**Next Action:** Advance to the next preflight phase (`EXP-07-P0-C22-A.5` or equivalent preflight rehearsal) to execute an end-to-end zero-step rehearsal using the canonical artifact `data/ops02/initial_model_state_canonical.pt`.
