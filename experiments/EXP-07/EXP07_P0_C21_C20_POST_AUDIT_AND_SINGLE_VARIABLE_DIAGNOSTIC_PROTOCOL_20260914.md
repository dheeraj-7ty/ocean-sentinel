# EXP-07-P0-C21: C20 Forensic Post-Audit, Hypothesis Selection, Single-Variable Diagnostic Protocol Freeze, and Durable Agent Learning Framework

**Document Version:** 1.0.0  
**Effective Date:** 2026-09-14  
**Authoritative Machine Manifests:**  
- `data/ops02/audits/ops02_c21_c20_post_audit_v1.json`  
- `data/ops02/audits/ops02_c21_hypothesis_information_value_v1.json`  
- `data/ops02/audits/ops02_c21_single_variable_diagnostic_protocol_v1.json`  
- `data/metadata/exp07_p0_c21_incident_register_v1.json`  
- `data/metadata/ocean_sentinel_lessons_learned_v1.json`  
**Execution Mode:** Antigravity IDE / AG 2.0 (Model: Gemini 3.8 Flash High)  
**Execution Guardrails:** ZERO TRAINING, ZERO KAGGLE, ZERO HOLDOUT ACCESS, ZERO PART-III ACCESS  

---

## 1. Executive Verdict

Phase C21 successfully completes the rigorous forensic post-audit of Phase C20, rectifies narrative and epistemic overclaims in historical reporting against Level 5 machine truth, evaluates candidate hypotheses H1 through H7, freezes an immutable single-variable diagnostic protocol (`EXP07_DIAG01_PAIRED_PROTOCOL`), and installs the permanent Ocean Sentinel Agent Learning & Failure-Prevention Framework.

### Core Audit Findings & Determinations:
1. **C20 Execution Soundness:** The Tier-1 zero-compute cross-domain evaluation executed in C20 is technically valid, bitwise reproducible, and conducted under verified partition quarantine (zero HOLDOUT access, zero Part-III access).
2. **Epistemic Overclaim Rectification:** Narrative claims in C20 asserting (a) universal superiority of model-declared normalization, (b) causal limitation of OPS-02 performance to domain properties rather than optimization, and (c) a "100% bug-free" pipeline are formally refuted and corrected.
3. **Loss-Weight Precision Resolution:** A forensic audit of the C16 execution script uploaded to Kaggle (`scratch/kaggle_replicate003_kernel/train_replicate003.py`) confirms that C16 ingested the exact 6-decimal literal constants prescribed by the C15 protocol. The Historical C16 Executed Vector and Future EXP07_DIAG01 Control Vector are identical to 6 decimal places.
4. **Hypothesis Selection:** **H7 is currently the highest-information hypothesis that can be tested cleanly under the frozen OPS-02 dataset and protocol.**
5. **Strict Single-Variable Protocol Freeze:** Exactly one independent variable (`CLASS_LOSS_WEIGHT_VECTOR`) is varied between Control (Canonical Sqrt-Median-Frequency weights, 47.06:1 dynamic range) and Treatment (Uniform Unweighted weights, 1.00:1 dynamic range), while all 19 non-weight experimental/protocol dimensions are machine-locked.
6. **Durable Agent Learning Framework:** Deployed `data/metadata/ocean_sentinel_lessons_learned_v1.json` seeded with 20 regression-protected lessons, backed by an automated pytest suite.

---

## 2. C20 Forensic Corrections

The retrospective report for Phase C20 (`EXP07_P0_C20_TIER1_CROSS_DOMAIN_EVALUATION_REPORT_20260914.md`) contained three narrative overclaims that diverged from Level 5 machine truth:

### Correction 1: Input Normalization Superiority Claim Refutation
- **C20 Narrative Claim:** *"Model-declared normalization yielded consistently superior transfer fidelity across all evaluated models."*
- **Level 5 Machine Truth:**
  - **EVAL-A (C16 $\to$ OPS-01 DEV):** Target-Native Normalization achieved `0.028818` mIoU, which is **higher** than Model-Declared Normalization (`0.027285` mIoU). Delta: $+0.001533$ in favor of target-native.
  - **EVAL-B (C8 $\to$ OPS-02 DEV):** Model-Declared Normalization achieved `0.035332` mIoU vs `0.019896` target-native.
  - **EVAL-C (C10 $\to$ OPS-02 DEV):** Model-Declared Normalization achieved `0.029223` mIoU vs `0.019455` target-native.
- **Rectified Epistemic Position:** Input normalization sensitivity in cross-domain transfer is **EVALUATION-DEPENDENT**. In EVAL-A, target-native normalization achieved superior transfer fidelity. Normalization cannot be claimed to be universally superior.

### Correction 2: Domain Properties vs Optimization Causal Overclaim
- **C20 Narrative Claim:** OPS-02 performance is *"fundamentally bounded by dataset domain properties rather than an optimization failure."*
- **Level 5 Machine Truth:** Cross-domain evaluation provides observational transfer degradation data only. It does not isolate optimization parameters, loss weighting, or network capacity.
- **Rectified Epistemic Position:** Tier-1 cross-domain evaluation provides descriptive evidence demonstrating substantial transfer degradation and heterogeneous class-level behavior. It does **NOT** identify the causal source of OPS-02 development performance limitations.

### Correction 3: "100% Bug-Free" Language
- **C20 Narrative Claim:** The pipeline is *"100% bug-free and robust."*
- **Level 5 Machine Truth:** The evaluation suite passed 72 automated guardrails testing specific audited invariants.
- **Rectified Epistemic Position:** The pipeline is *"verified against the implemented guardrail suite and audited invariants."* Testing establishes that checked invariants held; it does not prove universal absence of defects.

---

## 3. Historical Baseline Reconciliation

Four generations of retrospective reports (C15 through C19) cited historical C8 and C10 DEV phenomena baselines as `~0.4072` (40.7%), framing C16 (`0.0494`) as an 88% collapse.

- **Forensic Audit (INC-C20-001):** Direct inspection of Level 5 machine artifacts (`data/metadata/exp07_p0_c8_training_results_seed42_v1.json` and `exp07_p0_c10_training_results_seed101_v1.json`) proves:
  - **C8 Best DEV Phenomena mIoU:** `0.11903` (11.90%)
  - **C10 Best DEV Phenomena mIoU:** `0.13782` (13.78%)
  - **Claimed 0.4072 Origin:** A narrative transcription error introduced in C15 that conflated an all-class or background-inclusive metric with phenomena-only mIoU.
- **Actual Historical Delta:** C16 (`0.0494`) represents an ~2.4x to 2.8x domain performance delta relative to C8/C10, rather than an 8.2x catastrophic collapse.
- **Seed Variance Status:** Existing C8/C10 runs do not provide a clean isolated estimate of random seed variance because historical execution records indicate differences beyond seed number alone.

---

## 4. Canonical Loss-Weight Precision Audit

A critical pre-freeze audit investigated whether historical C16 execution used higher precision than the six-decimal constants documented in protocol summaries.

### Comparative Audit Across Evidence Layers:
1. **Formula Derivation:** Calculated from 8,401,060 valid pixels across the 132 TRAIN partition tiles with median frequency $399,710.5$:
   - Float64 formula values: e.g. Class 0 (`BG`): $0.4039349690\dots$, Class 11 (`HM`): $18.2432107294\dots$
2. **Protocol Specification:** Prescribed in `EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md` as exact 6-decimal literals.
3. **Actual C16 Machine Execution Code:** Inspected `scratch/kaggle_replicate003_kernel/train_replicate003.py` lines 56–69 (the exact script executed on Kaggle in C16). The class weight dictionary was defined with explicit 6-decimal literals:
   ```python
   CLASS_WEIGHTS_SQRT_MEDIAN = {
       0: 0.403935, 1: 2.450546, 2: 0.876692, 3: 0.945945,
       4: 0.648189, 5: 4.211476, 6: 0.719641, 7: 2.956203,
       8: 1.064525, 9: 1.882870, 10: 0.387652, 11: 18.243211
   }
   ```
4. **Machine Alignment:** Converting these 6-decimal literals to `torch.float32` yields values whose difference from unrounded float64 formula values is $< 4.8 \times 10^{-7}$, which is below single-precision machine epsilon near 1.

### Audit Verdict:
- **Historical C16 Executed Vector == Future EXP07_DIAG01 Control Vector.**
- The control vector is frozen to 6 decimal places as executed. No silent historical rewriting or precision discrepancies exist.

---

## 5. Hypothesis Ranking & Selection Rationale

Seven candidate hypotheses (H1–H7) were comparatively evaluated in `data/ops02/audits/ops02_c21_hypothesis_information_value_v1.json`:

1. **H1 (Parent/Datatake Diversity):** Requires re-curation or sub-sampling of datatakes; directly violates dataset freeze immutability.
2. **H2 (Geographic/Acquisition Shift):** Intrinsic observational property of satellite imagery; cannot be manipulated without re-partitioning.
3. **H3 (Class Imbalance & Co-occurrence):** Natural property of marine phenomena. Cannot be altered without synthetic data. However, the model's loss weighting response to imbalance is cleanly testable via H7.
4. **H4 (Spatial & Semantic Complexity):** Requires architectural interventions, confounding network capacity, parameter count, and optimizer dynamics.
5. **H5 (Radiometric Normalization):** Directly evaluated in C20 Tier-1 cross-evaluation. Normalization alone did not prevent transfer degradation.
6. **H6 (Optimization Instability & Seed Stochasticity):** Seed replication tests variance rather than an underlying mechanism.
7. **H7 (Class Loss Weighting Scheme):** Modifies exactly 1 tensor in memory while holding all 19 experimental dimensions identically locked.

**Conclusion:** **H7 is currently the highest-information hypothesis that can be tested cleanly under the frozen OPS-02 dataset and protocol.**

---

## 6. Final H7 Definition & Investigation Scope

> **“H7 — The canonical class-loss weighting scheme changes optimization behavior and development performance on OPS-02.”**

- **Investigation Scope:** The experiment tests the effect of the complete 12-element `CLASS_LOSS_WEIGHT_VECTOR` as a single object.
- **Explicit Non-Isolation:** The diagnostic does **NOT** isolate:
  - Rare classes individually
  - Heavy Machinery (`HM`) alone
  - Background (`BG`) alone
  - A specific dynamic range ratio (47.06:1)
  - Gradient competition as an established physical fact
- **Epistemic Qualification:** H7 is not claimed to be proven or the most likely true cause; it is selected as the highest-information hypothesis testable without protocol confounding.

---

## 7. Final Control Condition: EXP07_DIAG01_CONTROL

- **Name:** Canonical C16 Sqrt-Median-Frequency Class Weights
- **Formula:** $w_c = \sqrt{\frac{\text{median}(f_{\text{valid}})}{f_c}}$ computed on 8,401,060 OPS-02 TRAIN valid pixels.
- **Terminology Rule:** Strictly designated "Canonical Sqrt-Median-Frequency Class Weights". The term "inverse-frequency" is forbidden.
- **Exact Vector (float32):**
  `[0.403935, 2.450546, 0.876692, 0.945945, 0.648189, 4.211476, 0.719641, 2.956203, 1.064525, 1.882870, 0.387652, 18.243211]`
- **Dynamic Range:** $47.06 : 1$ (`HM` vs `IWs`).
- **Classification:** Historical reference control is C16; future execution is a concurrent paired control.

---

## 8. Final Treatment Condition: EXP07_DIAG01_TREATMENT

- **Name:** Uniform Unweighted Class Weights
- **Formula:** $w_c = 1.0 \quad \forall c \in \{0 \dots 11\}$
- **Exact Vector (float32):**
  `[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]`
- **Dynamic Range:** $1.00 : 1$.
- **No Background Weight Confounding:** All 12 classes, including Background (`BG`), are set to 1.0. Setting `BG = 0.2` or any separate penalty is strictly forbidden as it introduces a second confounding variable.

---

## 9. 19 Independently Machine-Locked Dimensions

| Dimension ID | Dimension Name | Locked Value | Source Authority |
|---|---|---|---|
| **INV-01** | Dataset Specification | `OPS02_v1.0.1_FROZEN` | `OPS02_DATASET_FREEZE_SPEC_v1.0.1.json` |
| **INV-02** | Partition Allocation | 132 TRAIN / 40 DEV / 40 HOLDOUT | `ops02_physical_dataset_manifest_v1.json` |
| **INV-03** | Partition Firewall Boundaries | Zero HOLDOUT / Zero Part-III access | `ops02_c20_dataset_firewall_v1.json` |
| **INV-04** | Physical Image Representation | GeoTIFF float32 single-band VV SAR, $256 \times 256$, 10x10 block DN | `ops02_c20_preprocessing_compatibility_v1.json` |
| **INV-05** | Preprocessing Transformation | `np.log1p(raw_image)`, valid DN > 0, nodata = 0.0 | `src/ocean_sentinel/ml/exp07_reference.py` |
| **INV-06** | Radiometric Normalization | TRAIN $\mu=4.424158, \sigma=0.469261$ | `EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md` |
| **INV-07** | Taxonomy & Index Ordering | 12 dense classes (0: BG ... 11: HM; Dense 3=`LWA`, Dense 9=`Eddy`) | `ops02_c19_taxonomy_canonicalization_v1.json` |
| **INV-08** | Excluded Source Labels | SOURCE LABELS 3 (Iceberg), 9 (Sea Ice), 14 (Mineral Oil Spill) $\to$ -100 | `ops02_c20_taxonomy_compatibility_v1.json` |
| **INV-09** | Neural Network Architecture | ResNet18-UNet (14,310,860 parameters, 30 BatchNorm layers) | `src/ocean_sentinel/ml/exp07_reference.py` |
| **INV-10** | Pretrained Encoder Weights | `ResNet18_Weights.IMAGENET1K_V1` (`resnet18-f37072fd.pth`) | `ops02_c19_canonical_protocol_v1.json` |
| **INV-11** | Optimization Algorithm | AdamW ($\beta_1=0.9, \beta_2=0.999, \epsilon=10^{-8}$) | `EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md` |
| **INV-12** | Base Learning Rate | $\eta = 5 \times 10^{-4}$ ($0.0005$) | `EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md` |
| **INV-13** | Weight Decay | $\lambda = 0.01$ (2D conv/linear only; bias and 1D BN excluded) | `EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md` |
| **INV-14** | Learning Rate Schedule | `LinearWarmupCosineAnnealingLR` ($T_{\max}=30, T_{\text{warmup}}=3, \eta_{\min}=10^{-6}$) | `EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md` |
| **INV-15** | Batch Dynamics & Acc. | Physical batch = 8, accumulation = 2, effective batch = 16 | `EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md` |
| **INV-16** | Sampler Strategy | Candidate F Hybrid (70% parent, 30% class, 72 draws) | `ops02_c19_canonical_protocol_v1.json` |
| **INV-17** | Random Seed Formula | Base seed = 42, epoch seed = `42 + epoch * 1000` | `ops02_c19_canonical_protocol_v1.json` |
| **INV-18** | Data Augmentation | Disabled (deterministic loaders, transformations disabled) | `EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md` |
| **INV-19** | Benchmark Metric & Stopping | `dev_mIoU_phenomena` (1..11, BG excl), patience=10, min=15 | `EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md` |
| **DIFF-01** | **CLASS_LOSS_WEIGHT_VECTOR** | **Canonical Sqrt-Median (`[0.403935 ... 18.243211]`)** vs **Uniform (`[1.0 ... 1.0]`)** | **SINGLE INDEPENDENT VARIABLE** |

---

## 10. Initialization Contract

1. **Conceptual Separation:** `PRETRAINED_BACKBONE_IDENTITY` identifies the TorchVision encoder (`ResNet18_Weights.IMAGENET1K_V1`, `resnet18-f37072fd.pth`, suffix `f37072fd` is a filename identifier). `FULL_INITIAL_MODEL_STATE_IDENTITY` represents the complete instantiated ResNet18-UNet architecture.
2. **Instantiation Procedure:**
   - Instantiate ResNet18-UNet.
   - Adapt `conv1` ($64 \times 1 \times 7 \times 7$) by taking the mean across the 3 RGB channels of pretrained weights.
   - Initialize decoder and segmentation head layers under fixed random seed 42.
   - Save complete model state dictionary to disk (`initial_model_state.pt`) and compute SHA-256 digest.
3. **Pre-Epoch 0 Parity Assertion:**
   $$\text{SHA256}(\text{control\_initial\_state}) == \text{SHA256}(\text{treatment\_initial\_state})$$
   must hold byte-identically before epoch 0.

---

## 11. Complete RNG Contract

1. **Multi-Engine State Capture:** Captures complete state structures before training:
   - Python `random.getstate()`
   - NumPy `np.random.get_state()`
   - PyTorch CPU `torch.get_rng_state()`
   - PyTorch CUDA `torch.cuda.get_rng_state_all()`
   - DataLoader worker seed configuration (`worker_init_fn`)
   - Sampler generator state (`torch.Generator().get_state()`)
2. **Restoration & Assertion:** Snapshot is persisted as `initial_rng_state.pt`. Restored identically and independently for control and treatment. Equality verified immediately before epoch 0 via machine assertion.
3. **Bounded Reproducibility Disclaimer:** Universal bitwise reproducibility is not claimed beyond what the verified execution environment (PyTorch determinism flags, specific GPU/CUDA libraries) supports.

---

## 12. Schedule & Data Parity Contract

1. **Precomputed Sample Schedule Reuse:** The canonical training sample schedule is generated once, persisted as `canonical_sample_schedule.json`, hashed, and fed identically to both control and treatment DataLoaders. Eliminates runtime sampler divergence.
2. **Batch Parity Enforcement:** Before every forward pass:
   $$\text{control batch IDs} == \text{treatment batch IDs}$$
   $$\text{control input tensors} == \text{treatment input tensors}$$
   $$\text{control target tensors} == \text{treatment target tensors}$$
3. **Per-Sample Checksum Integrity:** Deterministic SHA-256 digests computed for every sample's transformed input, target, and valid mask. Verified identical across conditions without duplicating large GeoTIFF files.
4. **BatchNorm Parity:** `model.train()` active with identical 30 BN layers, initial running stats, momentum 0.05, and eps $10^{-5}$. Non-determinism caveat: Any incidental numerical nondeterminism must be monitored and documented.
5. **Step-1 Divergence Sanity Check:** Control and treatment model states must be byte-identical before step 1. Weight divergence is expected after step 1 optimization and logged as an execution sanity check (not evidence for H7).

---

## 13. Metric Contract

- **Primary Metric:** `dev_mIoU_phenomena` (unweighted macro mean of IoU over classes 1 through 11, background excluded).
- **Comparison Metric:** $\Delta\text{mIoU} = \text{treatment\_mIoU} - \text{control\_mIoU}$.
- **Reporting Obligation:** Always report exact `control_mIoU`, `treatment_mIoU`, and $\Delta\text{mIoU}$.
- **Secondary Metrics Reported Concurrently:**
  - Per-class $\Delta\text{IoU}$ and support
  - Full 12-class confusion matrix
  - Subgroup metrics (Dominant: MCC/POW/IWs, Intermediate: BS/WS/Eddy, Ultra-Sparse: AF/OF/RF/LWA/HM)
  - Background IoU and prediction distribution
  - Observational training diagnostics (gradient norms, loss trajectories, learning rate schedule)
- **No Fabricated Significance:** Spatially correlated pixels inside images prohibit manufacturing p-values or confidence intervals from pixel counts.

---

## 14. Invalidation Criteria (No Arbitrary Thresholds)

A diagnostic run is classified as **`INVALID / INCONCLUSIVE`** strictly for:
1. `NaN` or `Inf` in loss, logits, or gradients.
2. Corrupted input, target, or mask tensors.
3. Checksum or SHA-256 mismatch in initial model state, RNG state, sample schedule, or batch IDs.
4. Optimizer or scheduler state mismatch before step 1.
5. BatchNorm configuration or initial running stats mismatch.
6. Zero foreground predictions across all validation batches (collapse to 100% background).
7. Firewall breach: any access to the HOLDOUT partition (`holdout_access_count > 0`) or Part-III directory.
8. Unhandled runtime crash or CUDA out-of-memory error.

*Gradient Norm Policy:* Arbitrary thresholds (e.g. `gradient norm > 100` or `= 0`) are removed. Large but finite gradients are recorded and tracked; zero gradients are recorded and investigated.

---

## 15. Outcome Interpretation Framework

- **Scientific Question:** *"Does changing only the class-loss-weight vector change development performance under the frozen OPS-02 protocol?"*
- **Descriptive Evidence Grades:**
  - **`POSITIVE OBSERVED DIFFERENCE` ($\Delta\text{mIoU} > 0$):** Observed development performance with uniform weighting exceeds canonical weighting. Supports a contribution of the class-loss-weighting scheme to development performance under this protocol. Does not prove gradient competition, optimization instability, sole causality, or global optimality.
  - **`NEGATIVE OBSERVED DIFFERENCE` ($\Delta\text{mIoU} < 0$):** Observed development performance with uniform weighting is lower than canonical weighting. Provides empirical evidence that uniform weighting did not improve performance under this protocol. Does not prove canonical weighting is globally optimal.
  - **`NEAR-ZERO OBSERVED DIFFERENCE`:** Applied only where the practical magnitude of $\Delta\text{mIoU}$ is judged small using an explicitly reported post hoc descriptive context. Weakens the hypothesis that class-loss weighting is a major contributor to the limitation under this protocol. Does not eliminate every possible effect of weighting.
  - **`INVALID / INCONCLUSIVE RUN`:** Triggered by any invalidation condition. Yields zero scientific conclusions.

---

## 16. Agent Learning & Failure-Prevention Framework

Deployed `data/metadata/ocean_sentinel_lessons_learned_v1.json` and `docs/OCEAN_SENTINEL_AGENT_LEARNING_FRAMEWORK.md`.

### Core Lifecycle:
$$\text{DETECTED} \longrightarrow \text{RECORDED} \longrightarrow \text{MITIGATED} \longrightarrow \text{REGRESSION\_PROTECTED} \longrightarrow \text{PROVEN\_STABLE}$$

- **Mandatory Rule:** A lesson is **NEVER** considered learned merely because an agent documented it. It becomes `REGRESSION_PROTECTED` only when a preventive control is defined and an automated test exists that future tasks execute.

---

## 17. Initial Seed Lesson Catalog (20 Lessons)

All 20 lessons are fully populated and initialized as `REGRESSION_PROTECTED`:
1. `LL-EXP07-001`: Narrative claims overriding machine truth (INC-C20-001, INC-C20-004).
2. `LL-EXP07-002`: Taxonomy and terminology drift across iterations.
3. `LL-EXP07-003`: Source-label vs dense-index confusion (conflating source labels 3, 9, 14 with dense classes).
4. `LL-EXP07-004`: Historical vs current dataset identity confusion (INC-C20-002).
5. `LL-EXP07-005`: Protocol hyperparameter drift across iterations.
6. `LL-EXP07-006`: Incorrect sampler seed formulation (static seed vs epoch formula).
7. `LL-EXP07-007`: Incorrect input-shape documentation (omitting singleton channel dimension).
8. `LL-EXP07-008`: Unsupported causal inference from descriptive evidence (INC-C20-005).
9. `LL-EXP07-009`: Interpreting 'tests passed' as '100% bug-free' (INC-C20-006).
10. `LL-EXP07-010`: Unverified historical performance baselines (0.4072 vs 0.1190).
11. `LL-EXP07-011`: Normalization conclusions generalized beyond observed evaluations.
12. `LL-EXP07-012`: Loss-weight terminology confusion (sqrt-median vs inverse-frequency).
13. `LL-EXP07-013`: Arbitrary experimental thresholds (heuristic cutoffs without empirical basis).
14. `LL-EXP07-014`: Incomplete checkpoint lineage (lacking SHA-256 and script hashes).
15. `LL-EXP07-015`: Pretrained-weight identifier suffix mistaken for cryptographic hash.
16. `LL-EXP07-016`: Failure to verify exact initial model state (cloning full architecture state dict).
17. `LL-EXP07-017`: Assuming same seed integer guarantees execution parity.
18. `LL-EXP07-018`: Failure to enforce sample schedule parity (runtime sampler drift).
19. `LL-EXP07-019`: Failure to distinguish sample count (132 tiles) from independent parent count (40 datatakes).
20. `LL-EXP07-020`: Repeated correction without automated recurrence protection.

---

## 18. Governance Updates

- **GOV-RULE-100:** Historical performance baseline claims must be machine-traceable directly to Level 5 JSON run records. Narrative citations without machine proof are forbidden.
- **GOV-RULE-101:** Sensitivity analysis conclusions must remain evaluation-specific. Broad generalization across opposing transfer directions is prohibited.
- **GOV-RULE-102:** Passing guardrail test suites confirms tested invariants only; declaring software "100% bug-free" is prohibited.
- **GOV-RULE-103:** Experimental diagnostic designs must prove strictly one intentional independent variable change across locked dimensions.
- **GOV-RULE-104:** Checkpoint identifiers and weight URLs must distinguish filename identifier suffixes from cryptographic SHA-256 digests.
- **GOV-RULE-105:** Every catalogued recurring agent failure must have a permanent automated regression test before achieving `REGRESSION_PROTECTED` status.

---

## 19. Tests and Exact Execution Results

Testing was executed in the repository's dedicated virtual environment (`.venv\Scripts\pytest.exe`).

### Execution Summary:
- **C21 Guardrails Suite (`tests/test_exp07_p0_c21_diagnostic_protocol_guardrails.py`):** **21 PASSED**, 0 failed in 0.15s.
- **Agent Learning Framework Suite (`tests/test_ocean_sentinel_agent_learning_framework.py`):** **12 PASSED**, 0 failed in 0.15s.
- **C20 Cross-Domain Guardrails (`tests/test_exp07_p0_c20_cross_domain_guardrails.py`):** **10 PASSED**, 0 failed.
- **C19 Canonicalization Guardrails (`tests/test_exp07_p0_c19_canonicalization_guardrails.py`):** **11 PASSED**, 0 failed.
- **C18 Protocol Remediation Guardrails (`tests/test_exp07_p0_c18_protocol_remediation_guardrails.py`):** **11 PASSED**, 0 failed.
- **C17 Forensic Guardrails (`tests/test_exp07_p0_c17_forensic_guardrails.py`):** **10 PASSED**, 0 failed.
- **C16 Replicate-003 Guardrails (`tests/test_exp07_p0_c16_replicate003_guardrails.py`):** **6 PASSED**, 0 failed.
- **C15 Freeze Guardrails (`tests/test_exp07_p0_c15_freeze_guardrails.py`):** **12 PASSED**, 0 failed.
- **Artifact Policy Suite (`tests/test_artifact_policy.py`):** **6 PASSED**, 0 failed.
- **Part-III Firewall Suite (`tests/test_part_iii_firewall.py`):** **6 PASSED**, 0 failed.

**Grand Total:** **105 PASSED**, 0 FAILED, 0 SKIPPED. Total test duration: 5.68s.

---

## 20. HOLDOUT & Part-III Firewall Verification

- **HOLDOUT Partition Verification:** `holdout_access_count == 0`. Zero read, write, or inference operations on the 40 HOLDOUT tiles.
- **Part-III Firewall Verification:** `part_iii_access == false`. The Part-III directory and identifiers remain strictly quarantined. All 6 firewall tests passed.

---

## 21. Git & Process Forensic Self-Audit

- `git status --porcelain -uall`: Zero staged changes.
- `git diff --cached --name-status`: Empty (0 staged files).
- `git diff --name-status`: Only the two pre-existing known tracked modifications:
  - `M .gitignore`
  - `M src/ocean_sentinel/ingestion/dataset.py`
- `git branch --show-current`: `master` (no branch switches, no resets, no stashes).
- Historical reports and checkpoints: 100% untouched and preserved.

---

## 22. Remaining Uncertainties

1. **Hardware / Kernel Determinism:** Certain parallel CUDA operations on Tesla T4 GPUs exhibit non-deterministic floating-point accumulation across parallel threads even with deterministic algorithm flags enabled.
2. **Historical Seed Variance Baseline:** Existing C8/C10 historical runs contain additional execution differences; clean isolated seed variance on OPS-02 is not yet independently established.
3. **Observational Spatial Co-occurrence:** Physical spatial co-occurrence of multiple marine phenomena within individual Sentinel-1 scenes cannot be manipulated independently under a frozen dataset protocol.

---

## 23. Exact Next Action

Phase C21 is **COMPLETE**. All C21 artifacts are generated, tested, and verified.

**Next Action:** Await explicit user authorization for Phase C22 (execution of the frozen `EXP07_DIAG01` paired experiment). **DO NOT TRAIN. DO NOT LAUNCH KAGGLE. DO NOT ACCESS HOLDOUT. DO NOT ACCESS PART-III.**
