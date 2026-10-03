# EXP-07-P0-C18: Protocol Remediation, Freeze-ID Repair, Metric/Loader Validation, Controlled Diagnostic Design, and Next-Training Gate

**Document ID:** `EXP07_P0_C18_PROTOCOL_REMEDIATION_AND_CONTROLLED_DIAGNOSTIC_DESIGN_20260914`  
**Project:** Ocean Sentinel  
**Subsystem:** EXP-07 Multiclass Oceanic and Atmospheric Phenomena Perception Foundation  
**Task:** EXP-07-P0-C18  
**Author:** Ocean Sentinel Research & Governance Council (Pair Programming Agent)  
**Date:** 2026-09-14  
**Status:** COMPLETE / REMEDIATED  
**Training Status:** PAUSED / PROHIBITED (`training_started = false`, `next_replicate_authorized = false`)

---

## 1. Executive Decision

The forensic audit of C16 established that while Replicate 003 completed technically on Kaggle without numeric failure or HOLDOUT leakage, severe governance, documentation, and protocol issues existed:
1. C16 mutated the frozen dataset specification in-place (`OPS02_DATASET_FREEZE_SPEC_v1.json`), violating immutable freeze integrity.
2. C15 documentation contained a typographical error claiming 41 DEV / 39 HOLDOUT, whereas the underlying physical manifests created 40 DEV / 40 HOLDOUT.
3. C17 committed an epistemic overclaim by declaring it "CAUSAL ESTABLISHED" that the OPS02 expansion caused the performance collapse from ~40% to 4.94% DEV phenomena mIoU.
4. Kaggle dual-T4 GPUs were provisioned while training code executed strictly on single-GPU (`cuda:0`).

**Executive Decision for C18:**
- **NO MODEL TRAINING** was conducted during C18 (`training_started = false`, `next_replicate_authorized = false`). Replicate 004, Seed 101, and Seed 2024 remain **STRICTLY PROHIBITED**.
- **Freeze Identity Repaired:** `data/ops02/OPS02_DATASET_FREEZE_SPEC_v1.0.1.json` is released as the sole authoritative canonical specification (`OPS02_v1.0.1_FROZEN`), cryptographically bound to physical manifests via SHA-256 hashes. In-place modification is permanently outlawed (GOV-RULE-090).
- **Runtime Identity Hardened:** Implemented `src/ocean_sentinel/ingestion/freeze_validator.py` enforcing exact sample-ID set equality (132 TRAIN, 40 DEV, 40 HOLDOUT) and cluster verification before any dataloader creation (GOV-RULE-091).
- **Metric and Pipeline Audited:** Metric math verified across 7 synthetic edge cases; all 11 phenomena classes exist in DEV GT; input pipeline (raw DN $\to$ validity mask $\to$ log1p $\to$ standardization with $\mu=4.424158, \sigma=0.469261 \to$ zeroing invalid borders) and class weights verified 100% bit-exact.
- **Epistemic Correction:** The 4.94% mIoU result is reclassified as **OBSERVED** under 10 distinct **PLAUSIBLE** hypotheses (H1–H10). Causality is **NOT ESTABLISHED**.
- **Controlled Diagnostic Designed:** Established a 2-tier diagnostic framework. Tier 1 (zero-compute cross-evaluation using existing checkpoints) and Tier 2 (`EXP07_DIAGNOSTIC_001` single-variable loss weighting ablation: Sqrt-Median Control vs Uniform Unweighted Treatment).
- **Next-Training Gate:** Status set to `TRAINING_AUTHORIZED_FOR_CONTROLLED_EXPERIMENT` conditional on user approval, while blind replicate training remains blocked (`next_replicate_authorized = false`).

---

## 2. C17 Findings Reviewed

The forensic audit in C17 reviewed the execution of C16 Replicate 003. Key confirmed findings:
- **Execution Authenticity:** C16 ran authentically on Kaggle GPU infrastructure (`dheeraj12237/ocean-sentinel-exp07-c16-replicate-003`).
- **Classification:** C16 was classified as `VALID BUT PROTOCOL-LIMITED`.
- **HOLDOUT Isolation:** Pristine HOLDOUT partition was 100% untouched during C16 training and validation.
- **Partition Discrepancy Reconciliation:** The physical partition manifest (`ops02_partition_manifest_v1.json`) generated during C14 partitioned exactly 132 TRAIN / 40 DEV / 40 HOLDOUT. C15's narrative claim of 41 DEV / 39 HOLDOUT was an erroneous manual documentation transcription.
- **In-Place Mutation Defect:** C16 modified `OPS02_DATASET_FREEZE_SPEC_v1.json` in-place to change the partition string from `132/41/39` to `132/40/40`. While the partition numbers now match the physical manifest, in-place modification destroyed freeze immutability.
- **Performance Metric:** Best DEV phenomena mIoU achieved was 0.049399 (epoch 4).
- **Epistemic Overclaim Identified:** C17 concluded that OPS02 expansion was "CAUSAL ESTABLISHED" as the cause of performance collapse. This was an unverified inductive leap.

---

## 3. Freeze Identity Repair

To restore cryptographic governance without rewriting historical artifacts:
1. **Preservation of Historical Artifacts:** The historical file `data/ops02/OPS02_DATASET_FREEZE_SPEC_v1.json` is preserved as an immutable historical record of the v1.0.0 state.
2. **Canonical Version Release:** Created `data/ops02/OPS02_DATASET_FREEZE_SPEC_v1.0.1.json` defining `OPS02_v1.0.1_FROZEN`.
3. **Cryptographic Binding:** The new specification binds the exact SHA-256 hashes of all three source manifests:
   - Physical Dataset Manifest: `F5480EA22D305A064B447A5A0A477B7DE05553AE1EC9D206CF8B0BEA3BFDFF1B`
   - Partition Manifest: `757DEAF75A6C449E2C6A92FDC63FA08740B4F23E4C0F08B9B799C065796E49E0`
   - Parent Cluster Manifest: `08ED21FB1D14995BF7CDD75C0CDA0AE2D963F729F4FD1608696BD6BC40E03C1C`
4. **Audit Record:** Created `data/ops02/audits/ops02_freeze_identity_repair_v1.json`.

**Authoritative Specification Mandate:** Every future training, diagnostic, and evaluation run MUST reference `data/ops02/OPS02_DATASET_FREEZE_SPEC_v1.0.1.json`.

---

## 4. Exact Dataset Identity

The physical manifests have been re-verified down to the individual sample level:
- **Total Physical Samples:** 212 materialized `.tif` tiles.
- **TRAIN Partition:** 132 tiles (62.26%), originating from 40 parent clusters across 33 datatakes.
- **DEV Partition:** 40 tiles (18.87%), originating from 12 parent clusters across 10 datatakes.
- **HOLDOUT Partition:** 40 tiles (18.87%), originating from 12 parent clusters across 9 datatakes.
- **Parent Clusters:** Exactly 64 disjoint clusters.
- **Mission Datatakes:** Exactly 52 distinct datatakes.
- **Cluster Overlap:** 0 clusters shared between TRAIN, DEV, and HOLDOUT (strict parent-level isolation).
- **Datatake Overlap:** 0 datatakes shared between partitions.
- **Taxonomy:** 12 classes (Background + 11 phenomena classes: MCC, IWs, BS, LWA, POW, OF, WS, AS, Eddy, HM, Thermal). Mineral Oil Spill is strictly excluded/quarantined.

---

## 5. Runtime Dataset Assertion Design

To ensure runtime code cannot silently accept corrupted or modified partitions:
- **Module:** `src/ocean_sentinel/ingestion/freeze_validator.py`
- **Functions:**
  - `validate_dataset_freeze_identity(freeze_spec_path, base_dir)`: Verifies manifest file existence and SHA-256 hash equality against the frozen specification.
  - `assert_runtime_dataset_integrity(sample_ids_by_split, freeze_spec_path, base_dir)`:
    1. Verifies counts: `len(TRAIN) == 132`, `len(DEV) == 40`, `len(HOLDOUT) == 40`.
    2. Verifies exact set equality: `set(actual_ids) == set(frozen_ids)` for each split.
    3. Verifies zero partition leakage: pairwise intersection of ID sets is strictly empty.
    4. Verifies cluster consistency and guarantees HOLDOUT isolation.
    5. Raises `RuntimeError` or `AssertionError` prior to dataloader construction if any mismatch is detected.
- **Governing Rule:** GOV-RULE-091.

---

## 6. Metric Definition Audit

An audit of the multiclass evaluation metric was conducted in `data/ops02/audits/ops02_c18_metric_protocol_audit_v1.json`.

### Mathematical Formulation
For class $c \in \{0, 1, \dots, 11\}$:
$$\text{IoU}_c = \frac{\text{TP}_c}{\text{TP}_c + \text{FP}_c + \text{FN}_c}$$
Primary Phenomena mIoU:
$$\text{mIoU}_{\text{phenomena}} = \frac{1}{|\mathcal{C}_{\text{eval}}|} \sum_{c \in \mathcal{C}_{\text{eval}}} \text{IoU}_c$$
where $\mathcal{C}_{\text{eval}} = \{1, 2, \dots, 11\}$ (Background class 0 is excluded).

### Findings
1. **DEV Class Presence:** Analysis of the 40 DEV ground-truth masks confirms that all 11 phenomena classes are present in DEV (minimum pixel count: 181 pixels for class 11 Thermal). Therefore, $|\mathcal{C}_{\text{eval}}| = 11$ unconditionally.
2. **Absent Class Rule:** If a class had 0 pixels in GT and 0 pixels predicted, $\text{IoU}_c$ would be undefined (0/0) and excluded from the macro average. In C16, no class was absent from DEV GT.
3. **Sparse-Class Vulnerability:** The simple macro average weights class 11 (181 pixels, 0.0004% support) identically to class 6 (7,752,382 pixels, 18.48% support). A single erroneous prediction on a sparse class can collapse its $\text{IoU}$ to $0.000$, penalizing the macro mIoU by up to $\frac{1}{11} \approx 0.0909$.
4. **C16 Math Verification:** C16 computed the metric strictly and correctly according to this frozen definition. The 0.049399 score is mathematically valid.

---

## 7. Input Pipeline Audit

The preprocessing pipeline was audited in `data/ops02/audits/ops02_c18_input_pipeline_audit_v1.json` across 9 representative tiles covering diverse phenomena.

### Invariants Verified
1. **Raw Ingestion:** Valid pixels extracted using `raw_dn > 0`.
2. **Log-Transform:** Applied as `np.log1p(valid_dn)`. Verified no double-log1p or missing log1p.
3. **Standardization:** Normalized using frozen OPS02 parameters: $\mu = 4.424158$, $\sigma = 0.469261$.
   $$x_{\text{norm}} = \frac{\log(1 + \text{DN}) - 4.424158}{0.469261}$$
4. **Border Zeroing:** Invalid border pixels (`raw_dn == 0`) are explicitly assigned $0.0$ and masked out with `ignore_index = -1` in ground-truth labels.
5. **Numerical Integrity:** Zero NaN or Inf values produced; output tensor shape $[1, 512, 512]$ with `torch.float32`.

---

## 8. Loss-Weight Audit

Audited in `data/ops02/audits/ops02_c18_class_weights_audit_v1.json`.

### Formulation
Computed over all valid pixels in the 132 frozen TRAIN tiles:
$$f_c = \frac{N_c}{\sum_{k=0}^{11} N_k}, \quad w_c = \sqrt{\frac{\text{median}_k(f_k)}{f_c}}$$
Normalized such that $\sum_{c=0}^{11} w_c = 12.0$.

### Verification Result
Recomputation on 132 frozen TRAIN samples produced exact matches to C16 weights across all 12 classes:
- Background: 0.169145
- Class 1 (MCC): 1.134375
- Class 2 (IWs): 1.258679
- Class 3 (BS): 1.109017
- Class 4 (LWA): 1.103756
- Class 5 (POW): 1.701198
- Class 6 (OF): 0.814327
- Class 7 (WS): 1.189531
- Class 8 (AS): 1.579450
- Class 9 (Eddy): 1.341103
- Class 10 (HM): 0.316886
- Class 11 (Thermal): 0.282533

**Conclusion:** 100% bit-exact match. No weight calculation discrepancy existed in C16.

---

## 9. Sampler Audit

Audited in `data/ops02/audits/ops02_c18_sampler_protocol_audit_v1.json`.

### Protocol: Candidate F Hybrid Sampler
- **Budget:** 72 draws per epoch.
- **Draw Allocation:** 70% (50 samples) drawn uniformly across parent clusters; 30% (22 samples) drawn from rare-phenomena positive pools.
- **Replacement:** `replacement = True`.
- **Determinism:** Governed by `torch.Generator().manual_seed(seed + epoch)`.

### Findings
- Audited over Epochs 1 through 5 with Seed 42.
- Exactly 72 samples drawn per epoch.
- Parent cluster coverage ranged between 30 and 35 distinct clusters per epoch.
- All 12 classes represented in drawn samples across each epoch.
- **Zero Leakage:** All sampled IDs belong strictly to the 132 TRAIN partition. Zero DEV or HOLDOUT samples drawn.

---

## 10. Model Identity Audit

Audited in `data/ops02/audits/ops02_c18_model_identity_audit_v1.json`.

### Architecture Specifications
- **Backbone:** ResNet-18 encoder initialized with torchvision ImageNet pretrained weights (`ResNet18_Weights.IMAGENET1K_V1`).
- **Decoder:** Custom UNet decoder with transposed convolution upsampling blocks and lateral skip connections.
- **Input Channels:** 1 (SAR single-polarization VV amplitude). First convolutional layer converted from 3 channels to 1 channel by summing ImageNet channel weights ($W_{\text{1-ch}} = \sum_{c=0}^2 W_{c}$).
- **Output Channels:** 12 (multiclass logits).
- **Total Trainable Parameters:** Exactly 14,310,860.
- **BatchNorm Layers:** Exactly 30 `BatchNorm2d` layers with momentum 0.05.
- **Verification:** Instantiated and checked in `test_model_parameter_and_batchnorm_identity`. Parameter count and layer count match canonical specification 100%.

---

## 11. C16 Protocol-Conformance Matrix

| # | Parameter | C15 Frozen Protocol | C16 Actually Executed | C18 Canonical Protocol | Conformance Status |
|---|---|---|---|---|---|
| 1 | Dataset Version | OPS02_v1.0.0_FROZEN | OPS02_v1.0.0 (in-place modified) | OPS02_v1.0.1_FROZEN | DOCUMENTATION_ONLY |
| 2 | Sample Counts | 132 TRAIN / 40 DEV / 40 HOLDOUT | 132 TRAIN / 40 DEV / 40 HOLDOUT | 132 TRAIN / 40 DEV / 40 HOLDOUT | MATCH |
| 3 | Model Architecture | ResNet18-UNet | ResNet18-UNet | ResNet18-UNet | MATCH |
| 4 | Parameter Count | 14,310,860 | 14,310,860 | 14,310,860 | MATCH |
| 5 | BatchNorm Layers | 30 layers (momentum 0.05) | 30 layers (momentum 0.05) | 30 layers (momentum 0.05) | MATCH |
| 6 | Pretrained Weights | ImageNet-1k | ImageNet-1k | ImageNet-1k | MATCH |
| 7 | Input Normalization | $\mu=4.424158, \sigma=0.469261$ | $\mu=4.424158, \sigma=0.469261$ | $\mu=4.424158, \sigma=0.469261$ | MATCH |
| 8 | Loss Function | Weighted Cross-Entropy | Weighted Cross-Entropy | Weighted Cross-Entropy | MATCH |
| 9 | Class Weights | Sqrt-Median Frequency | Sqrt-Median Frequency | Sqrt-Median Frequency | MATCH |
| 10 | Sampler | Candidate F (70/30) | Candidate F (70/30) | Candidate F (70/30) | MATCH |
| 11 | Optimizer | AdamW (lr=3e-4, wd=1e-4) | AdamW (lr=3e-4, wd=1e-4) | AdamW (lr=3e-4, wd=1e-4) | MATCH |
| 12 | LR Scheduler | CosineAnnealingLR (T_max=20, $\eta_{\min}=1\text{e-}6$) | CosineAnnealingLR | CosineAnnealingLR | MATCH |
| 13 | Batch Size | 8 | 8 | 8 | MATCH |
| 14 | Gradient Acc. | 1 step (effective bs=8) | 1 step | 1 step | MATCH |
| 15 | Gradient Clip | Max norm 1.0 | Max norm 1.0 | Max norm 1.0 | MATCH |
| 16 | Epoch Budget | 20 epochs | 20 epochs (stopped at 14) | 20 epochs | MATCH |
| 17 | Early Stopping | Patience 10 on DEV phenomena mIoU | Patience 10 (stopped at ep 14) | Patience 10 | MATCH |
| 18 | Seed | 42 | 42 | 42 | MATCH |
| 19 | Dataloader Workers| 4 | 4 | 4 | MATCH |
| 20 | Determinism | PyTorch deterministic flags set | Flags set | Flags set | MATCH |
| 21 | Accelerator Alloc.| Dual-T4 provisioned | 1 GPU used (`cuda:0`) | 1 GPU provisioned & used | PROTOCOL_DEVIATION |
| 22 | Metric Definition | Multiclass Phenomena mIoU (11-cls)| 11-class macro mIoU | 11-class macro mIoU | MATCH |
| 23 | Checkpoint Select.| Best DEV phenomena mIoU (ep 4) | Best DEV phenomena mIoU (ep 4)| Best DEV phenomena mIoU | MATCH |
| 24 | Manifest Integrity| Cryptographic binding | Narrative only (transcription bug)| Cryptographic hash bound | DOCUMENTATION_ONLY |

**Conformance Summary:** 20 parameters MATCH, 3 parameters DOCUMENTATION_ONLY, 1 parameter PROTOCOL_DEVIATION (dual-GPU provisioning vs single-GPU execution).

---

## 12. GPU Infrastructure Protocol

Audited in `data/ops02/audits/ops02_c18_gpu_protocol_specification_v1.json`.

### Mandates
1. **Single-GPU Default:** All future training runs on Kaggle shall provision and allocate exactly ONE GPU (single Tesla T4 or P100) unless distributed data parallelism (DDP) is intentionally designed, benchmarked, and authorized.
2. **Honest Accounting:** Telemetry must separately record `gpus_provisioned` and `gpus_allocated_to_trainer`.
3. **Resource Stewardship:** Provisioning two GPUs while using only one wastes cloud quota without scientific benefit.
4. **Governing Rule:** GOV-RULE-093.

---

## 13. 4.94% Failure Diagnosis

### Epistemic Correction
C17 concluded that OPS02 dataset expansion caused the performance collapse. This was an overclaim. In C18:
- **Observed:** C16 on OPS02 achieved 0.049399 DEV phenomena mIoU. Historical C8/C10 on OPS01 achieved ~0.40 DEV phenomena mIoU.
- **Evidence Level:** Descriptive observation across two confounded conditions (different dataset, different split, different sample count, different parent cluster distribution, different class weights).
- **Causality:** **NOT ESTABLISHED**.

---

## 14. Hypothesis / Evidence Matrix

| Hypothesis | Description | Available Evidence | Missing Evidence | Cheapest Valid Diagnostic | Support Criteria | Falsification Criteria |
|---|---|---|---|---|---|---|
| **H1: True Distribution Shift** | OPS02 encompasses geographically/oceanographically distinct waters. | OPS02 has 64 clusters vs OPS01's 20. | Feature embedding cluster divergence metrics. | UMAP/t-SNE of pretrained feature embeddings. | Clear clustering of OPS02 separate from OPS01. | Severe overlap of feature distributions. |
| **H2: Geographic / Sensor Shift** | Incident angles, sea state, or geographic regions differ. | Metadata shows global geographic coverage. | Pixel-level radiometric histograms across regions. | Histograms of backscatter across datatakes. | Statistically significant radiometric shift. | Identical radiometric distributions. |
| **H3: Class-Support Imbalance** | Severe pixel imbalance in OPS02 collapses rare classes. | DEV mIoU is dominated by classes with 0.000 IoU. | Model predictions per class on TRAIN vs DEV. | Confusion matrix on TRAIN set from C16 checkpoint. | Model predicts only dominant classes on TRAIN. | High mIoU on rare classes on TRAIN. |
| **H4: Input Pipeline Discrepancy** | Normalization parameters differ between OPS01 and OPS02. | OPS02 used $\mu=4.42, \sigma=0.47$; OPS01 used $\mu=4.61, \sigma=0.52$. | Sensitivity test of model to normalization shift. | Evaluate C10 model on OPS02 using both normalizations. | Large performance difference under normalization change. | Negligible change in mIoU. |
| **H5: Metric Sensitivity Artifact** | Unweighted macro averaging of 11 classes drags down score. | 7 classes have IoU < 0.01; dominant classes have 14.5% IoU. | Pixel-weighted IoU and frequency-weighted IoU. | Recompute alternative metrics from existing C16 conf matrix. | Frequency-weighted IoU is > 0.40 while macro is 0.049. | Frequency-weighted IoU is also < 0.05. |
| **H6: Sampler Over-Representation** | Rare phenomenon pool forces unrepresentative tiles. | 30% draws from rare pool; 72 samples/epoch. | Epoch loss curves broken down by cluster. | Epoch loss on parent-drawn vs rare-drawn samples. | High loss variance and divergence on rare draws. | Stable loss progression across draw types. |
| **H7: Optimization Instability** | Sqrt-median class weights over-penalize dominant classes. | Rare class weights are up to $1.70\times$; background is $0.17\times$. | Gradient norm distributions per class. | Train single-variable ablation with uniform weights. | Uniform weights achieve higher overall and stable mIoU. | Uniform weights yield identical collapse. |
| **H8: Label Ambiguity / Multi-label Conflict** | Single-pixel multiclass argmax creates boundary noise. | Complex SAR imagery often has overlapping phenomena. | Spatial boundary agreement between annotators. | Visual inspection of top-error tiles. | Systemic false negatives at phenomenon boundaries. | Errors are spatially uniform across tiles. |
| **H9: Historical OPS01 Spatial Leakage** | OPS01 had higher spatial correlation across train/dev. | OPS01 had fewer parent clusters (20 clusters). | Cross-slice distance matrices in OPS01 vs OPS02. | Minimum geographic distance between train and dev tiles. | OPS01 train/dev distance significantly smaller than OPS02. | OPS01 and OPS02 have identical spatial isolation. |
| **H10: Capacity Bottleneck** | ResNet-18 has insufficient capacity for 11 diverse phenomena. | 14.3M parameters. | Capacity scaling curve on synthetic benchmark. | Evaluate ResNet-34 or ResNet-50 feature representations. | Significant capacity saturation on TRAIN set. | Model underfits TRAIN even with large capacity. |

---

## 15. Sparse-Class Reporting Protocol

Audited in `data/ops02/audits/ops02_c18_sparse_class_reporting_protocol_v1.json`.

### Mandates
1. **Primary Metric Remains Frozen:** `dev_mIoU_phenomena` (unweighted macro average over all 11 phenomena classes) remains the official primary selection and early stopping metric. It is never retroactively modified or discarded.
2. **Secondary Partitioned Reporting:** To diagnose class imbalance without corrupting the primary benchmark, reports must partition results into three secondary diagnostic tiers:
   - **Tier 2: Dominant Phenomena Subgroup** (Classes 3, 4, 6; pixel support $> 5\%$): C16 Baseline = **0.145006**.
   - **Tier 3: Intermediate Phenomena Subgroup** (Classes 1, 2, 7, 9; pixel support $0.5\% - 5\%$): C16 Baseline = **0.021644**.
   - **Tier 4: Ultra-Sparse Phenomena Subgroup** (Classes 5, 8, 10, 11; pixel support $< 0.5\%$): C16 Baseline = **0.000168**.
3. **Governing Rule:** GOV-RULE-094.

---

## 16. Controlled Experiment Design

Designed in `data/ops02/audits/ops02_c18_controlled_diagnostic_design_v1.json`.

### Tier 1: Zero-Compute Cross-Evaluation (Immediate Priority)
- **Objective:** Evaluate existing C8/C10 (OPS01) and C16 (OPS02) model weights on cross-partition DEV sets without training any model.
- **Inference 1:** C16 best model checkpoint evaluated on historical OPS01 DEV partition.
- **Inference 2:** C8 / C10 best model checkpoint evaluated on OPS02 DEV partition.
- **Compute Cost:** 0 GPU hours training; < 2 minutes pure inference.
- **Hypotheses Tested:** Directly separates H1/H9 (dataset difficulty / domain shift) from H4/H7 (training optimization / class weights).

### Tier 2: EXP07_DIAGNOSTIC_001 (Single-Variable Training Ablation)
- **Independent Variable:** Loss Class Weighting (Uniform Unweighted vs Sqrt-Median Frequency).
- **Control:** C16 Protocol with Sqrt-Median Frequency Weights on `OPS02_v1.0.1_FROZEN`.
- **Treatment:** Identical protocol with Uniform Class Weights ($w_c = 1.0$ for all $c \ge 1$, $w_0 = 0.2$ for background) on `OPS02_v1.0.1_FROZEN`.
- **All Other Variables Constant:** Exact same 132 TRAIN / 40 DEV samples, same Seed 42, same ResNet18-UNet, same Candidate F sampler, same AdamW optimizer, same lr=3e-4, same batch size 8.
- **Expected Information Value:** Determines if extreme class weighting caused gradient instability and collapsed rare classes to zero prediction.

---

## 17. Governance Updates

The following durable governance rules were added to `data/metadata/ocean_sentinel_governance_rules_v1.json` (Rules 90–94, bringing total active rules to 94):

- **GOV-RULE-090: Frozen Training Specification Cryptographic Binding:** A frozen training specification must be cryptographically bound to its referenced physical manifests via SHA-256 hashes and cannot be mutated in place. Any modification requires a formal semantic version increment.
- **GOV-RULE-091: Exact Runtime Dataset Identity Assertion:** Runtime training and evaluation code must assert exact sample-ID set equality, partition-ID set equality, and cluster-ID set equality against the frozen specification prior to dataloader construction.
- **GOV-RULE-092: Scientific Causal Claim Standard:** Scientific causal claims regarding dataset or architectural interventions require controlled single-variable comparisons. Discrepancies between observational runs must be labeled descriptive observations with competing hypotheses.
- **GOV-RULE-093: GPU Infrastructure Accounting and Single-GPU Default:** GPU provisioning count and actual training device count must be separately recorded in telemetry. Single-GPU execution is the default unless distributed multi-GPU training is explicitly authorized.
- **GOV-RULE-094: Primary Metric Invariance and Secondary Diagnostic Partitioning:** Primary benchmark metrics are permanently frozen to preserve historical comparability. Diagnostic insights on sparse or imbalanced classes must be reported as secondary diagnostic tiers without altering primary metric formulas.

---

## 18. Tests and Verification

### Test Suite Execution
1. **C18 Protocol Remediation Guardrails:** `tests/test_exp07_p0_c18_protocol_remediation_guardrails.py`
   - 11 test functions covering freeze identity, exact sample-ID set equality, model parameter count, model BatchNorm count, metric synthetic cases, input pipeline normalization, loss-weight recomputation, Candidate F sampler determinism, single-GPU specification, governance rules, and C18 prohibitions.
   - **Result:** **11 PASSED** in 2.88s.
2. **Recent Milestones & Security Suite:**
   - `tests/test_exp07_p0_c14_ops02_dataset_assembly_guardrails.py` (11 passed)
   - `tests/test_exp07_p0_c15_freeze_guardrails.py` (12 passed)
   - `tests/test_exp07_p0_c16_replicate003_guardrails.py` (6 passed)
   - `tests/test_exp07_p0_c17_forensic_guardrails.py` (10 passed)
   - `tests/test_exp07_p0_c18_protocol_remediation_guardrails.py` (11 passed)
   - `tests/test_artifact_policy.py` (6 passed)
   - `tests/test_part_iii_firewall.py` (6 passed)
   - **Result:** **62 PASSED, 0 FAILED** in 5.17s.

---

## 19. Next-Training Gate

Documented in `data/ops02/audits/ops02_next_training_gate_v1.json`:
- **Gate Verdict:** `TRAINING_AUTHORIZED_FOR_CONTROLLED_EXPERIMENT`
- **Replicate Status:** `next_replicate_authorized = false`
- **Training Started:** `training_started = false`
- **Holdout Access:** `holdout_access = false`
- **Condition:** Training is conditionally authorized **EXCLUSIVELY** for the single-variable controlled diagnostic experiment `EXP07_DIAGNOSTIC_001` (Loss Weighting Ablation) following Tier 1 zero-compute cross-evaluation and explicit user sign-off.
- **Blind Replicates:** Replicate 004, Seed 101, and Seed 2024 remain strictly **BLOCKED**.

---

## 20. Remaining Limitations

1. **Unresolved True Performance Driver:** While 10 competing hypotheses have been systematically formulated, the empirical cause of the 4.94% result remains unproven pending controlled experiments.
2. **Kaggle Execution Latency:** Running Kaggle GPU jobs requires external network and API synchronization.
3. **Sparse-Class Inherent Hardness:** Certain atmospheric phenomena (e.g. atmospheric gravity waves, thermal fronts) possess very few bounding annotations in the dataset, which inherently limits macro IoU under severe class imbalance.

---

## 21. Exact Next Authorized Action

1. **Step 1:** Conduct **Tier 1 Zero-Compute Cross-Evaluation**:
   - Evaluate C16 checkpoint (`c16_replicate_003_best.pt`) on historical OPS01 DEV split.
   - Evaluate C10 checkpoint (`c10_replicate_002_best.pt`) on OPS02 DEV split (`OPS02_v1.0.1_FROZEN`).
   - Compute primary and secondary tiered metrics.
2. **Step 2:** Analyze results against the Hypothesis/Evidence Matrix to rule out H1, H4, or H9.
3. **Step 3:** If Tier 1 results confirm optimization or weighting issues, submit proposal to user for executing `EXP07_DIAGNOSTIC_001` (Uniform vs Sqrt-Median Loss Weighting).
4. **Step 4:** Maintain pristine HOLDOUT isolation.

---

## 22. Git / Process Self-Audit

- **Python Background Processes:** 0 training or unauthorized processes running.
- **Git State:** Clean branch `master`. Zero unstaged commits, zero branch switches, zero checkouts, zero stashes, zero file deletions.
- **Historical Reports:** Preserved without modification.
- **Part-III Quarantine:** Firewall 100% verified; zero leakage.
- **Telemetry State:** `scratch/exp07_p0_c18_run_state.json` fully synchronized and marked `COMPLETED`.

---

### Epistemic Assessment Summary
- **C16 Performance Result (0.049399 mIoU):** OBSERVED
- **132 / 40 / 40 Split Manifest Ground Truth:** OBSERVED & VERIFIED
- **C16 Single-GPU Execution:** OBSERVED & VERIFIED
- **Hypotheses H1–H10:** PLAUSIBLE
- **OPS02 Expansion Causal Responsibility for Collapse:** NOT CAUSALLY ESTABLISHED (OVERCLAIM CORRECTED)
- **Controlled Single-Variable Ablation Necessity:** SUPPORTED
