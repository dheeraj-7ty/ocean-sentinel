# EXP-07-P0-C22-A.3: Canonical Initialization Lineage Forensic Gate and Final EXP07_DIAG01 Readiness Decision

**Document Version:** 1.0.0  
**Date:** 2026-09-14  
**Task ID:** EXP-07-P0-C22-A.3  
**Repository:** `d:\Projects\ocean-sentinel`  
**Branch:** `master`  
**Environment:** Antigravity IDE / AG 2.0  
**Model:** Gemini 3.8 Flash High  
**Status:** COMPLETE (FORENSIC GATE EXECUTED)  
**Final Readiness Verdict:** `BLOCKED` (Supersedes C22-A.2 `READY_FOR_USER_AUTHORIZATION`)

---

## 1. Executive Summary & Readiness Decision

Task **EXP-07-P0-C22-A.3** conducted a forensic audit into the initialization lineage of `data/ops02/initial_model_state.pt` and established whether the future single-variable diagnostic experiment (`EXP07_DIAG01`) can legitimately proceed to training authorization.

### Core Forensic Findings:
1. **Material Protocol Inconsistency Confirmed:** Invariant **INV-10** in the authoritative protocol (`ops02_c21_single_variable_diagnostic_protocol_v1.json`) strictly mandates an ImageNet-pretrained backbone: `torchvision.models.ResNet18_Weights.IMAGENET1K_V1` (`resnet18-f37072fd.pth`).
2. **Current Artifact Provenance Established via Machine Verification:** Tensor-by-tensor comparison verified that `data/ops02/initial_model_state.pt` (SHA256: `4BB233DB629E44DE12E41F11809024B7A5BDA4DBCFB19D13752295973117E45C`) is **bitwise 100% identical** across all 192 tensors to an un-pretrained model instantiated with:
   ```python
   ResNet18UNet(in_channels=1, num_classes=12, pretrained=False, bn_momentum=0.05)
   ```
   under PyTorch CPU seed 42. It contains **zero ImageNet-pretrained weights**.
3. **Pairwise Parity vs. Canonical Provenance:** In C22-A.2, the zero-step rehearsal proved that Control and Treatment achieved perfect pairwise parity (both started from identical weights, processed identical batches, and produced identical logits). However, **pairwise parity does not equal canonical initialization**. Starting both conditions from an un-pretrained random model violates the frozen scientific protocol.
4. **Pretrained Weights Local Unavailability:** The official ImageNet weights file (`resnet18-f37072fd.pth`, 44.7 MB) was dynamically downloaded during the C16 Kaggle execution into the remote VM's cache (`/root/.cache/torch/hub/checkpoints/`), but was **never transferred or saved locally**. The local torch hub cache (`~/.cache/torch/hub/checkpoints/`) contains only `resnet34-b627a593.pth`.
5. **No-Network Governance Constraint:** Strict task governance prohibits network downloads merely to satisfy preflight documentation. Furthermore, ImageNet weights cannot be mathematically or deterministically reconstructed from local evidence.

### FINAL READINESS VERDICT: $\mathbf{BLOCKED}$
`EXP07_DIAG01` is formally **BLOCKED** from training authorization. This verdict supersedes the C22-A.2 rehearsal verdict of `READY_FOR_USER_AUTHORIZATION`. Under scientific governance, equalizing an incorrect random initialization between experimental conditions does not satisfy the frozen experimental contract.

---

## 2. Task Metadata & System Environment

| Dimension | Specification | Verification Status |
| :--- | :--- | :--- |
| **Task Identifier** | `EXP-07-P0-C22-A.3` | VERIFIED |
| **Execution Date** | 2026-09-14 | VERIFIED |
| **Repository Path** | `d:\Projects\ocean-sentinel` | VERIFIED |
| **Active Git Branch** | `master` | VERIFIED |
| **Staged Git Modifications** | 0 files | VERIFIED |
| **Tracked Git Modifications Preserved** | `.gitignore`, `src/ocean_sentinel/ingestion/dataset.py` | VERIFIED |
| **Active Background Processes** | 0 | VERIFIED |
| **Execution Mode** | Antigravity IDE / AG 2.0 (Single state-mutating task) | VERIFIED |
| **Python Environment** | Python 3.10.9 (`.venv`) | VERIFIED |
| **PyTorch Execution** | PyTorch 2.1.1 (CPU execution) | VERIFIED |

---

## 3. Four-Way Initialization Taxonomy

To ensure scientific precision, four distinct states must be explicitly distinguished:

```
Initialization Taxonomy
├── 1. Historical C16 Initialization: ImageNet-pretrained (downloaded dynamically on Kaggle; never persisted at epoch 0)
├── 2. Current C22-A.2 Artifact: data/ops02/initial_model_state.pt (Randomly initialized with pretrained=False; non-canonical)
├── 3. Canonical Future Protocol: ResNet18_Weights.IMAGENET1K_V1 + channel-mean conv1 + seed 42 decoder/head
└── 4. Control/Treatment Pairwise Parity: Operational equivalence between concurrent experimental arms
```

### Table 3.1: Initialization Taxonomy Comparison

| Dimension | Historical C16 (Replicate 003) | Current C22-A.2 Artifact | Canonical Future Protocol | Pairwise Parity in C22-A.2 |
| :--- | :--- | :--- | :--- | :--- |
| **Backbone Weights** | `ResNet18_Weights.DEFAULT` (ImageNet) | Random (Kaiming uniform) | `ResNet18_Weights.IMAGENET1K_V1` | Equal (both random) |
| **conv1 Adaptation** | Mean across 3 RGB channels | Random (Kaiming uniform) | Mean across 3 RGB channels | Equal (both random) |
| **Decoder / Head** | PyTorch default under seed 42 | PyTorch default under seed 42 | PyTorch default under seed 42 | Equal (bitwise match) |
| **Epoch 0 State Persisted?**| **NO** (Only best/last models saved) | **YES** (`initial_model_state.pt`) | **REQUIRED** (`initial_model_state.pt`) | Cloned by both arms |
| **Scientific Protocol Status**| Executed baseline | **NON_CANONICAL** | Frozen target | Validated mechanics only |

---

## 4. Authoritative Protocol Requirements Audit (Part A)

Audit of `data/ops02/audits/ops02_c21_single_variable_diagnostic_protocol_v1.json` and `EXP07_P0_C21_C20_POST_AUDIT_AND_SINGLE_VARIABLE_DIAGNOSTIC_PROTOCOL_20260914.md` evaluated the 6 canonical initialization criteria:

1. **ImageNet-pretrained ResNet18 backbone:**
   - **Status:** `VERIFIED`.
   - **Evidence:** Invariant INV-10 explicitly specifies `torchvision.models.ResNet18_Weights.IMAGENET1K_V1` (`resnet18-f37072fd.pth`).
2. **Modification to one input channel:**
   - **Status:** `VERIFIED`.
   - **Evidence:** Invariant INV-04 and Section 10 specify `in_channels=1`, conv1 shape `[64, 1, 7, 7]`.
3. **Exact adaptation method for conv1:**
   - **Status:** `VERIFIED`.
   - **Evidence:** Section 10 explicitly specifies: mean of 3 RGB pretrained channels across dimension 1 (`base_resnet.conv1.weight.mean(dim=1, keepdim=True)`).
4. **Decoder/head initialization:**
   - **Status:** `VERIFIED`.
   - **Evidence:** Section 10 specifies standard PyTorch default initialization for newly introduced decoder and segmentation head modules.
5. **Exact random seed used when non-pretrained portions are initialized:**
   - **Status:** `VERIFIED`.
   - **Evidence:** Section 10 and INV-17 explicitly mandate fixed base seed 42 active during decoder/head construction.
6. **Exact order of model construction and state loading:**
   - **Status:** `VERIFIED`.
   - **Evidence:** Model construction sequence: (a) set seed 42, (b) load pretrained ResNet18 backbone, (c) copy channel mean into 1-channel conv1, (d) instantiate decoder and head blocks sequentially, (e) export state dict to `initial_model_state.pt`.

---

## 5. Forensic Audit of `data/ops02/initial_model_state.pt` (Part B)

A dedicated tensor-level inspection was performed comparing `data/ops02/initial_model_state.pt` against a freshly constructed `ResNet18UNet(in_channels=1, num_classes=12, pretrained=False)` under `torch.manual_seed(42)`:

```
Comparison Results:
- Total tensors in state dict: 192
- Trainable parameter tensors: 62 (14,310,860 elements)
- Running mean buffers: 30 (5,888 elements)
- Running var buffers: 30 (5,888 elements)
- Num batches tracked buffers: 30 (30 elements)
- Bitwise tensor matches: 192 / 192 (100.0%)
- Bitwise tensor mismatches: 0 / 192 (0.0%)
```

### Table 5.1: Artifact Lineage Summary

| Field | Forensic Finding |
| :--- | :--- |
| **Artifact Path** | `data/ops02/initial_model_state.pt` |
| **File Size** | 57,354,338 bytes |
| **SHA256 Hash** | `4BB233DB629E44DE12E41F11809024B7A5BDA4DBCFB19D13752295973117E45C` |
| **Creation Method** | `ResNet18UNet(in_channels=1, num_classes=12, pretrained=False)` in `rehearse_exp07_diag01_zero_step.py` |
| **Pretrained Backbone?** | **NO** (`pretrained=False` used; `resnet18(weights=None)`) |
| **Random Initialized Layers** | **ALL** (conv1, layer1..4, dec1..4, final_up, final_conv, head) |
| **RNG Seed** | PyTorch CPU seed 42 |
| **Evidence Source** | Bitwise identity with synthetic un-pretrained model under seed 42 |
| **Artifact Classification** | `NON_CANONICAL_INITIALIZATION_ARTIFACT` |

---

## 6. Pairwise Parity vs. Canonical Parity (Part C)

In C22-A.2, the preflight rehearsal verified:
$$\text{Control initial state} == \text{Treatment initial state}$$
$$\text{Control input batch} == \text{Treatment input batch}$$
$$\text{Control forward logits} == \text{Treatment forward logits}$$

While this confirmed that the execution pipeline contains no unintended divergent mechanics between experimental arms, it created an epistemic hazard: **mistaking internal relative consistency for protocol validity**.

```
                           PAIRWISE PARITY
               [Control Initial] == [Treatment Initial]
                                  │
                   ┌──────────────┴──────────────┐
                   ▼                             ▼
       CANONICAL PROVENANCE           NON-CANONICAL PROVENANCE
   Both from Pretrained ImageNet    Both from Random Weights
       [SCIENTIFICALLY VALID]           [SCIENTIFICALLY INVALID]
                                        (Current State of Repo)
```

Pairwise parity is a necessary prerequisite, but it is **insufficient** to authorize training. If both arms start from an invalid un-pretrained state, the entire diagnostic comparison evaluates the wrong scientific regime (scratch training vs. fine-tuning).

---

## 7. Historical C16 Lineage Audit (Parts D & E)

Inspection of `scratch/kaggle_replicate003_kernel/train_replicate003.py` and the remote execution log `experiments/EXP-07/runs/EXP07_RUN003_SEED42/ocean-sentinel-exp07-c16-replicate-003.txt`:

1. **Was C16 ImageNet-pretrained?**
   - **YES.** Line 433 of `train_replicate003.py`: `model = ResNet18UNet(num_classes=12, in_channels=1, pretrained=True)`.
2. **How was the backbone loaded?**
   - Via `resnet18(weights=ResNet18_Weights.DEFAULT)`.
   - Log lines 12–13 record:
     ```
     Downloading: "https://download.pytorch.org/models/resnet18-f37072fd.pth" to /root/.cache/torch/hub/checkpoints/resnet18-f37072fd.pth
     100%|██████████| 44.7M/44.7M [00:00<00:00, 146MB/s]
     ```
3. **How was one-channel input handled?**
   - Line 208: `self.conv1.weight.copy_(base_resnet.conv1.weight.mean(dim=1, keepdim=True))`.
4. **Was C16's initial state persisted?**
   - **NO.** The training script saved only `best_model.pt` (epoch 17, SHA256: `936EF935...`) and `last_model.pt` (epoch 27, SHA256: `60411490...`).
5. **Can the initial state be recovered from trained checkpoints?**
   - **NO.** Trained weights reflect 17–27 epochs of gradient updates on OPS-02; the initial weights were irreversibly overwritten during optimization.

---

## 8. Pretrained File Availability & Recovery Analysis (Part F)

A thorough search across the local environment was conducted:
- Local Torch Hub Cache (`C:\Users\Dheeraj\.cache\torch\hub\checkpoints\`): `resnet18-f37072fd.pth` **NOT FOUND** (only `resnet34-b627a593.pth` exists).
- Local Repository (`d:\Projects\ocean-sentinel`): `resnet18-f37072fd.pth` **NOT FOUND**.
- Network Downloads: **PROHIBITED** under absolute governance.
- Deterministic Reconstructability: **IMPOSSIBLE** (ImageNet-1k weights cannot be synthesized from a mathematical formula or pseudo-random generator).

**Outcome Classification:** `CANONICAL_INIT_STATE_NOT_RECOVERABLE`.

---

## 9. Incident Management & Lesson Learned (Parts M & N)

### Incident Record
Catalogued in `data/metadata/exp07_p0_c22a3_incident_register_v1.json`:
- **ID:** `INC-C22A3-001`
- **Severity:** `CRITICAL`
- **Category:** `SCIENTIFIC_VALIDITY / INITIALIZATION_PROVENANCE`
- **Status:** `BLOCKED`
- **Description:** `data/ops02/initial_model_state.pt` is purely random-initialized (`pretrained=False`), violating invariant **INV-10**. Pretrained weights are not locally available.

### Durable Agent Learning Framework Entry
Registered in `data/metadata/ocean_sentinel_lessons_learned_v1.json`:
- **Lesson ID:** `LL-EXP07-024`
- **Category:** `SCIENTIFIC_VALIDITY`
- **Title:** Conflating pairwise condition parity with canonical protocol initialization.
- **Principle:** Relative parity between experimental conditions (Control == Treatment) must never be accepted as proof of canonical experimental initialization. Initial-state artifacts must have verifiable provenance linking back to the frozen scientific specification.
- **Status:** `REGRESSION_PROTECTED` (Guarded by `tests/test_exp07_p0_c22a3_initialization_guardrails.py`).

---

## 10. Comprehensive Guardrail Test Results (Part P)

The complete suite of 9 guardrail test files was executed:

```bash
pytest tests/test_exp07_p0_c22a3_initialization_guardrails.py \
       tests/test_exp07_p0_c22a2_preflight_guardrails.py \
       tests/test_exp07_p0_c22a1_closure_guardrails.py \
       tests/test_exp07_p0_c22a_readiness_guardrails.py \
       tests/test_exp07_p0_c21_diagnostic_protocol_guardrails.py \
       tests/test_ops02_c20_cross_domain_guardrails.py \
       tests/test_artifact_policy.py \
       tests/test_part_iii_firewall.py \
       tests/test_ocean_sentinel_agent_learning_framework.py -v
```

### Exact Results
- **Tests Passed:** **98**
- **Tests Failed:** **0**
- **Tests Skipped:** **0**
- **Runtime:** **5.40 seconds**
- **Pass Rate:** **100.0%**

---

## 11. Process Integrity & Git Forensics

- **Active Background Processes:** 0
- **Git Branch:** `master`
- **Staged Git Modifications:** 0
- **Tracked Unstaged Files Preserved:** `.gitignore`, `src/ocean_sentinel/ingestion/dataset.py` (zero resets, checkouts, pushes, stashes, or deletions).
- **Telemetry File Updated:** `scratch/exp07_p0_c22a3_run_state.json` (Phase: `COMPLETE`, Status: `BLOCKED`).

---

## 12. Resolution Protocol for Future Authorization

For `EXP07_DIAG01` to achieve training authorization in a future task:
1. **Provision Pretrained Backbone Offline:** The canonical `resnet18-f37072fd.pth` weights file must be placed into `C:\Users\Dheeraj\.cache\torch\hub\checkpoints\` or staged in `data/ops02/` under explicit user instruction.
2. **Materialize Canonical Initial State:**
   ```python
   torch.manual_seed(42)
   model = ResNet18UNet(in_channels=1, num_classes=12, pretrained=True, bn_momentum=0.05)
   torch.save(model.state_dict(), "data/ops02/initial_model_state.pt")
   ```
3. **Re-run Zero-Step Rehearsal:** Execute `scripts/rehearse_exp07_diag01_zero_step.py` against the true canonical pretrained state, re-verifying forward and loss boundaries.
4. **Submit for User Authorization Gate:** Only after canonical provenance and rehearsal pass can `READY_FOR_USER_AUTHORIZATION` be reinstated.

Until the above steps are executed, training remains strictly **BLOCKED**.
