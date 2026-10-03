# DIAG05_PREEXECUTION_AUDIT_AND_HARDENED_PLAN

**Investigation ID:** `DIAG-05-LOSS-LANDSCAPE-GRADIENT-DYNAMICS`  
**Formal Title:** Loss Landscape & Gradient Dynamics Diagnostic (Final Batch-to-Cluster Identifiability Audit Edition)  
**Task ID:** `EXP-07-P0-DIAG-05-FINAL-BATCH-CLUSTER-IDENTIFIABILITY-AUDIT`  
**Plan Version:** `v1.9.0`  
**Authoritative Dataset Contract:** Level 5 Canonical Physical Dataset Specification (OPS-02 v1.0.1, `OPS02_v1.0.1_FROZEN`)  
**Baseline Model:** ResNet18-UNet (14,310,860 trainable parameters, Option B BatchNorm baseline)  
**Target Execution Environment:** Local Python 3.10 virtual environment (`.venv`), CPU for static profiling / GPU for controlled intervention  
**Readiness Verdict:** `PLAN_READY_WITH_PREREQUISITES` (EXECUTION STRICTLY NOT AUTHORIZED; REQUIRES FORMAL PROTOCOL AMENDMENT FOR ISOLATED BACKWARD PASSES)  

---

## 1. Executive Summary & Audit Mandate

This document establishes the hardened pre-execution scientific audit and implementation plan for **DIAG-05** (`DIAG-05-LOSS-LANDSCAPE-GRADIENT-DYNAMICS`).

In accordance with strict Ocean Sentinel governance:
- **DIAG-05 SCIENTIFIC EXECUTION HAS NOT OCCURRED.**
- Zero model training steps, zero backward passes, zero optimizer updates, zero parameter modifications, and zero GPU seconds were executed during this planning task.
- Quarantined partitions (**HOLDOUT**: 40 tiles / 12 parent clusters; **Part III**: external benchmark) remain completely untouched (`0` access).
- The working tree modifications in `.gitignore` and `src/ocean_sentinel/ingestion/dataset.py` are preserved.

### Core Audit Finding & Bounded Scientific Justification:
DIAG-01 through DIAG-04 systematically narrowed and tested several structural hypotheses:
1. Metric calculation semantics and support sensitivity (DIAG-01).
2. Sampler exposure schedule dynamics and rare-class presence (DIAG-02).
3. 1-D radiometric backscatter overlap and scene heterogeneity (DIAG-03).
4. Multi-path architectural receptive field scale compatibility and edge censorship (DIAG-04).

None of these forward-only investigations demonstrated an absolute physical or structural barrier that prevents the network from receiving information. However, ruling out these specific structural obstacles does **NOT** exhaust all possible explanations of low validation performance, nor does it prove that optimization failure is the sole root cause. 

DIAG-05 specifically and narrowly tests whether **first-order gradient geometry and optimization dynamics** under canonical inverse-frequency class weighting provide additional explanatory evidence. DIAG-05 is **NOT** guaranteed to explain the performance deficit.

> [!NOTE]
> **Loss Landscape & Curvature Scope Limitation:** While the investigation ID is historically frozen as `DIAG-05-LOSS-LANDSCAPE-GRADIENT-DYNAMICS`, DIAG-05 directly evaluates first-order gradient dynamics (layer-wise gradient norms, norm dispersion, within-batch cross-class gradient direction alignment, and short-horizon trajectory evolution). It does **NOT** compute the Hessian matrix, Hessian-vector products, maximum eigenvalues ($\lambda_{\max}$), or landscape sharpness estimators, and makes zero claims of directly measuring loss-landscape curvature.

Because evaluating gradients requires invoking PyTorch `backward()` passes, DIAG-05 directly intersects `BLOCK-006-UNAUTHORIZED_TRAINING` of the diagnostic governance framework. Execution cannot proceed under standard diagnostic rules without an authorized protocol amendment that defines an isolated execution class. The investigation is therefore designated **`PLAN_READY_WITH_PREREQUISITES`**.

---

## 2. Full Diagnostic Chain Reconstruction: Baseline → DIAG-01 → DIAG-02 → DIAG-03 → DIAG-04 → DIAG-05

To ensure unbroken methodological provenance, the entire investigative chain is reconstructed from primary machine artifacts:

```
[EXP-07 Baseline C16/C22: dev_mIoU ~0.049 on OPS-02]
                         │
                         ▼
[DIAG-01 (C22-G)]: Class Support & Metric Semantics on OPS-02 DEV (40 tiles, 12 parent clusters)
   ├─ Exact Question: Is low mIoU an artifact of metric formulation, zero-denominator handling, or support sparsity?
   ├─ Exact Dataset: OPS-02 DEV partition (40 tiles, 12 parent clusters).
   ├─ Exact Evidence: OF (1 cluster, 1,709 px) and RF (1 cluster, 9,550 px) have ultra-sparse support in DEV; metric is support-sensitive.
   ├─ Exact Conclusion: Closed as CASE B (Structural multi-label ambiguity confirmed). Macro metric calculation is mathematically sound.
   └─ What Remained Unresolved: Does the training sampler starve rare classes of exposure during training?
                         │
                         ▼
[DIAG-02 (C22-I/J)]: Sampler Exposure & Schedule Invariance on OPS-02 TRAIN (132 tiles, 40 parent clusters)
   ├─ Exact Question: Does Candidate F hybrid sampler starve rare classes of batch exposure across training epochs?
   ├─ Exact Dataset: OPS-02 TRAIN partition (132 tiles, 40 parent clusters).
   ├─ Exact Evidence: Candidate F draws all 11 non-background classes; zero exposure was NOT observed, though huge pixel-volume disparity exists.
   ├─ Exact Conclusion: REPAIRED. Total starvation hypothesis is bounded; exposure absence does not explain failure.
   └─ What Remained Unresolved: Are the radiometric backscatter distributions of the 12 classes separable at the single-pixel level?
                         │
                         ▼
[DIAG-03]: Radiometric Feature Discriminability on OPS-02 TRAIN (132) + DEV (40) = 172 tiles, 52 clusters
   ├─ Exact Question: Are single-pixel SAR backscatter distributions distinguishable across classes, or does 1-D overlap explain failure?
   ├─ Exact Dataset: 172 development tiles (2,504,800 DEV pixels + 8,261,376 TRAIN valid pixels) across 52 parent clusters.
   ├─ Exact Evidence: Moderate 1-D overlap observed (22 of 66 class pairs OVL >= 0.70); BS vs LWA OVL = 0.8402; high scene heterogeneity.
   ├─ Exact Conclusion: COMPLETED. 1-D radiometry cannot uniquely separate several classes, proving spatial context is required.
   └─ What Remained Unresolved: Does the convolutional architecture provide receptive fields compatible with spatial annotation extents?
                         │
                         ▼
[DIAG-04]: Receptive Field & Spatial Scale Compatibility on OPS-02 TRAIN (132) + DEV (40) = 172 tiles, 52 clusters
   ├─ Exact Question: Does ResNet18-UNet provide multi-path receptive fields compatible with observed annotation scales on the 256x256 grid?
   ├─ Exact Dataset: 172 development tiles across 52 parent clusters (1,072 annotated connected components).
   ├─ Exact Evidence: Pervasive boundary contact (>80-98% for 8/10 phenomena); multi-path skip connections structurally overlap compact (HM: 8.1 px) and intermediate (RF: 35.4 px, Eddy: 62.1 px) targets; bottleneck TRF (531-563 px) is clipped by 256 px (25.6 km) aperture; radial PSD is monotonic broadband.
   ├─ Exact Conclusion: COMPLETED (DIAG04_VALID_RESULT). Structural scale overlap exists across skip paths. Structural overlap does NOT establish learned representational adequacy or explain low mIoU. Empirical learned-weight ERF remains unmeasured.
   └─ What Remained Unresolved: How does the network actually optimize its weights across these classes during backpropagation?
                         │
                         ▼
[DIAG-05]: Loss Landscape & Gradient Dynamics (CURRENT INVESTIGATION — PLAN ONLY)
   └─ Core Target: Direct measurement of per-layer gradient norms, gradient dispersion, and within-batch cross-class gradient direction conflict under Canonical vs Uniform loss weights.
```

---

## 3. Critical Post-DIAG04 Check: Exact Remaining Scientific Uncertainty

DIAG-04 established:
1. **Class-dependent annotation spatial scales**: Compact (HM: 8.1 px), intermediate (RF: 35.4 px, Eddy: 62.1 px), and mesoscale (MCC, IWs, AF).
2. **Pervasive crop boundary contact**: >80–98% in 8 of 10 oceanographic classes, meaning full extents are edge-censored by the $25.6\text{ km}$ tile aperture.
3. **Multi-path structural overlap**: The ResNet18-UNet provides parallel skip paths (Path A: 19 px, Path B: 71 px, Path C: 155–163 px) that structurally encompass compact and intermediate targets.
4. **Empirical learned-weight ERF remains unmeasured**: Architecture-only TRF was analyzed; data-dependent weight gradients were not computed.
5. **Structural overlap does not establish learned representational adequacy**: The existence of computational paths does not mean the optimizer successfully trains features along those paths.
6. **Spatial-scale findings do not establish the cause of low mIoU**: Scale mismatch was ruled out as an absolute structural impossibility, but the root cause of low mIoU remains unidentified.

### What DIAG-05 Can Validly Address:
DIAG-01 through DIAG-04 narrowed and tested several structural hypotheses, but did not exhaust all possible explanations of low validation performance. DIAG-05 specifically tests whether the **mechanics of backpropagation and loss formulation** provide additional explanatory evidence:
- **Gradient Magnitude Disparity**: Do canonical inverse-frequency class weights (which scale loss up to $\sim 10^3$ for rare classes) generate excessively volatile, exploding, or vanishing gradient norms across layers relative to uniform weighting?
- **Within-Batch Directional Alignment**: When evaluated on the *identical physical input minibatch*, do the masked gradient contributions from rare classes point in opposing directions (negative cosine similarity) relative to the aggregate common-class resultant vector?
- **Optimization Stability**: Does the optimizer make productive parameter progress for rare classes, or do dominant-class updates continually overwrite rare-class feature representations?
- **Interventional Comparison**: Does removing canonical class weights (uniform weight control arm) stabilize gradient magnitudes or alter within-batch directional alignment?

---

## 4. Authoritative DIAG-05 Question Specification

The authoritative definition from `AGENT_GOVERNANCE.md`, `data/ops02/audits/ops02_c22j_diag02_forensic_correction_v1.json`, and `experiments/EXP-07/EXP07_P0_C22J_DIAG02_FORENSIC_CORRECTION_20260914.md` is:

### 4.1 Primary Scientific Question
> **DIAG-05 PRIMARY SCIENTIFIC QUESTION:**  
> *"Across the 12 canonical Ocean Sentinel taxonomy classes on the OPS-02 development dataset using the baseline ResNet18-UNet architecture, does the canonical inverse-frequency class-weighting schedule induce severe Step-0 spatial cross-batch gradient-norm heterogeneity (dispersion across minibatches) or within-batch cross-class gradient direction interference (negative cosine similarity between rare-class masked gradients and dominant-class masked gradients on identical inputs) relative to an unweighted (uniform) control arm under strictly identical minibatch inputs?"*

### 4.2 Secondary Questions
1. **Layer-Wise Gradient Distribution:** How do gradient $L_2$ norms and log-ratios vary across network depth (encoder stages `conv1` through `layer4` vs decoder skip fusion blocks `dec4` through `dec1` and classification `head`) when evaluating rare classes vs dominant classes?
2. **Batch-Level Gradient Dispersion:** What is the robust dispersion (Interquartile Range, IQR) and tail ratio (max-to-median ratio) of gradient norms across training minibatches under canonical vs uniform weighting? (Coefficient of variation is eliminated due to instability from near-zero denominators).
3. **Continuous Cosine Angle Geometry:** What is the continuous empirical distribution of within-batch cosine similarity $\cos(g_{\text{rare}}, g_{\text{common}})$ at Step 0 initialization (`data/ops02/initial_model_state_canonical.pt`)?
4. **Relative Gradient Attenuation under Uniform Weights:** Under uniform weighting ($1.0$), do rare-class gradients exhibit severe magnitude attenuation relative to dominant-class gradients due to pixel volume disparity?

### 4.3 Non-Questions (Explicitly Out of Scope)
- **NOT an architecture search:** DIAG-05 does not test alternative network backbones (SegFormer, ConvNeXt, Swin).
- **NOT a loss-function benchmark:** DIAG-05 does not evaluate Focal Loss, Dice Loss, Lovasz-Softmax, or boundary losses. It evaluates *only* the baseline Cross-Entropy loss under canonical vs uniform weights.
- **NOT a hyperparameter optimization:** DIAG-05 does not tune learning rates, weight decays, or batch sizes.
- **NOT an evaluation on HOLDOUT:** Quarantined partitions remain strictly untouched (`0` access).
- **NOT a claim of full-protocol recovery:** Short-horizon 5-epoch interventions do NOT establish 20-epoch canonical training recovery.
- **NOT a guaranteed root-cause discovery:** DIAG-05 is not guaranteed to account for the performance deficit.

### 4.4 Original DIAG-05 Hypothesis Reconstruction & Estimand Mapping

Every measurement in DIAG-05 maps strictly to an identified scientific question or necessary validity check:

| Hypothesis | Scientific Question | Exact Estimand | Exact Measurement | Allowable Scientific Conclusion |
| :--- | :--- | :--- | :--- | :--- |
| **H1: Cross-Batch Heterogeneity** | Is canonical inverse-frequency class weighting associated with severe cross-batch gradient norm dispersion across physical minibatches compared to uniform weighting at Step 0 initialization? | Spatial cross-batch heterogeneity of within-batch unclipped gradient norms $\|g_{l,b}(\theta_0)\|_2$ across minibatches in Population B (unconditional full-dataset physical census, $B_{\text{phys}}=4$) at Step 0. Primary robust dispersion metric: raw $\text{IQR}(\|g_{l,b}\|_2)$ within each arm. Secondary comparative metrics: dispersion ratio $\frac{\text{IQR}_{\text{canonical}}}{\text{IQR}_{\text{uniform}}}$ and paired log-ratio difference $\Delta \log_{10}(\text{IQR}) = \log_{10}(\text{IQR}_{\text{canonical}}) - \log_{10}(\text{IQR}_{\text{uniform}})$ under strict categorical handling for zero denominators (`FINITE_RATIO`, `UNDEFINED_ZERO_DENOMINATOR`, `BOTH_IQR_ZERO`, `NONFINITE`). Purely descriptive physical-census profiling across 132 TRAIN tiles / 40 parent clusters; zero formal NHST tests registered. | For each stage-representative layer $l$ and global parameters $\theta$, compute within-batch unclipped gradient norm raw $\text{IQR}(\{\|g_{l,b}^{\text{canonical}}(\theta_0)\|_2\})$, raw $\text{IQR}(\{\|g_{l,b}^{\text{uniform}}(\theta_0)\|_2\})$, and secondary ratio/difference; along with tail ratio $\frac{\max_b \|g_{l,b}^{\text{canonical}}\|_2 / \text{median}_b \|g_{l,b}^{\text{canonical}}\|_2}{\max_b \|g_{l,b}^{\text{uniform}}\|_2 / \text{median}_b \|g_{l,b}^{\text{uniform}}\|_2}$. Terminology note: designated strictly as within-batch unclipped gradient norm; the word 'accumulated' is reserved exclusively for Tier 2 optimizer boundaries. Purely descriptive census evaluation. | If canonical weighting produces substantially elevated IQR or tail ratios, conclude that canonical weighting induces higher instantaneous spatial cross-batch gradient heterogeneity across minibatches at Step 0. Prohibit concluding that this constitutes temporal training volatility, iteration-to-iteration instability, or training divergence, and prohibit making formal NHST claims on H1 physical census data. |
| **H2: Directional Alignment** | Do masked gradient contributions from rare-core classes ($M_{\text{rare}}$) exhibit opposing directional geometry relative to the aggregate common-class resultant ($M_{\text{common}}$) within co-occurring observations, and does canonical weighting alter this directional alignment? | Continuous cosine similarity distribution $S_{\text{cos}}(g_{\text{rare}}, g_{\text{common}}) = \frac{\langle g_{\text{rare}}, g_{\text{common}} \rangle}{\|g_{\text{rare}}\|_2 \|g_{\text{common}}\|_2}$ evaluated on masked gradient contributions from dual-supported cluster-pure physical observations (Population A, cluster-pure observation $B_{\text{phys}}=1$ or single-cluster minibatch $\le 4$ tiles), evaluated under canonical weights and counterfactually under uniform weights on identical inputs and parameters $\theta_0$. As proven in `LL-DIAG05-PLAN-024`, batches mixing multiple parent clusters destroy cluster identifiability and are prohibited. Explicitly, H2 is a Step-0 directional-gradient diagnostic and does NOT reproduce the optimizer accumulation boundary; common scalar reduction denominator $D_{\text{batch}}$ cancels identically in cosine; weighting alters cosine strictly through numerator class reweighting. | Continuous empirical distribution of masked gradient contributions $\cos(g_{\text{rare}, b}, g_{\text{common}, b})$ for global $\theta$ and stage-representative layers $l$. Statistical unit structure: (1) Raw descriptive unit: cluster-pure physical Population-A tile observation ($B_{\text{phys}}=1$ or single-cluster minibatch $\le 4$ tiles); (2) Primary independence unit: parent acquisition mission datatake cluster; (3) Inferential unit: paired parent-cluster median summary. Formal paired inference uses Wilcoxon signed-rank test on matched cluster-level paired median differences $\Delta \cos_k = \text{median}_{b \in \mathcal{B}_k}(\cos_{\text{canonical}, b}) - \text{median}_{b \in \mathcal{B}_k}(\cos_{\text{uniform}, b})$. Zero-difference handling: pairs with $\Delta \cos_k = 0$ are handled per standard Wilcoxon convention (`zero_method="wilcox"`), with $n_{\text{paired}}$, $n_{\text{zero}}$, and $n_{\text{effective}} = n_{\text{paired}} - n_{\text{zero}}$ explicitly recorded in audit JSON rather than silently dropped. Tie handling: ties in $|\Delta \cos_k|$ receive average ranks, evaluating p-values with continuity-corrected tie adjustment (`correction=True`, `method="asymptotic"` in `scipy.stats.wilcoxon`). Minimum effective sample size condition: $n_{\text{effective}} \ge 10$; if $< 10$, designated `DESCRIPTIVE_ONLY_LOW_POWER`. If all differences zero, reported as `ZERO_DIFFERENCE_ALL_PAIRS`. Only matched clusters with valid dual-support observations in both arms enter paired inference; unmatched clusters are reported and excluded (`UNMATCHED_CLUSTER_EXCLUDED`). Confirmatory inference is restricted to the primary global full-network contrast; stage/layer-representative targets are secondary descriptive diagnostics without multiplicity inflation. | If the paired cluster-level contrast $\Delta \cos_k$ exhibits a consistent shift or if $\cos(g_{\text{rare}}, g_{\text{common}}) < 0$ across a substantial proportion of parent clusters, conclude that rare and aggregate-common within-batch masked gradient contributions exhibit an opposing gradient direction in parameter space at Step 0 initialization across independent parent clusters; cannot conclude destructive interference or optimization failure. Prohibit claiming destructive interference, optimization failure, or treating multiple batches from the same cluster as independent observations (pseudo-replication). |
| **H3: Weighting Dynamics** | Does changing the loss weighting intervention from canonical inverse-frequency weights to uniform weights alter short-horizon training dynamics, gradient clipping activation frequency, observed parameter displacement, and early validation performance? | Trajectory contrast between canonical-weighted and uniform-weighted models across 5 epochs under Candidate F sampling protocol with fixed learning rate ($\eta = 2 \times 10^{-4}$), evaluated across 3 paired random seeds (seeds 42, 101, 202). Evaluates 3 paired seed replications $\times$ 2 arms, NOT 6 independent runs. Accumulation across $A=2$ physical batches ($B_{\text{phys}}=8$, effective optimizer batch size 16) is evaluated at the optimizer accumulation boundary. | Global gradient clipping activation frequency at accumulation boundaries ($\mathbb{I}(\|g_t^{\text{accum}}\|_2 > 1.0)$), actual observed parameter displacement $\|\theta_t - \theta_{t-1}\|_2$, training loss trajectory $L(t)$, and end-of-5-epoch validation mIoU on phenomena classes ($\text{dev\_mIoU}_{\text{phenomena}}$). | If the uniform intervention yields consistent reductions in gradient clipping frequency across seeds, stabilizes observed parameter displacement, and improves $\text{dev\_mIoU}_{\text{phenomena}}$, conclude that this supports a causal effect of the loss-weighting intervention on short-horizon optimization behavior under this protocol. Endpoint-specific results must remain separately interpretable (clipping activation, observed parameter displacement, training loss, and DEV mIoU); inferring an unmeasured mechanism merely because multiple endpoints move together is prohibited. If no consistent difference across seeds is observed, conclude that no detectable difference was observed under the 3-seed short-horizon protocol; explicitly acknowledge that this protocol is powered only to observe gross trajectory divergence and cannot rule out moderate or longer-horizon effects. Prohibit claiming absence of effect or rejecting weighting as an optimization bottleneck based on $n=3$ non-significance. |

### 4.5 Success Criteria
1. Exact, deterministic computation of layer-wise gradient norms ($\|\nabla_\theta \mathcal{L}\|_2$) and log-ratios across all encoder and decoder modules for pre-registered minibatches.
2. Exact computation of within-batch gradient cosine similarity between paired masked rare-class and common-class gradient vectors on the identical input batch.
3. Strict single-variable interventional isolation: identical model weights, identical batch data, identical RNG seeds, varying *only* the class loss weight vector.
4. Cluster-level bootstrap aggregation across parent datatakes ($K=52$).
5. Strict adherence to evidence classification (`OBSERVED`, `SUPPORTED`, `PLAUSIBLE`, `CAUSAL_SHORT_HORIZON_INTERVENTION`).

### 4.6 Inconclusive Criteria
DIAG-05 must conclude **`INCONCLUSIVE`** if:
1. Inter-seed variability across random initializations exceeds the treatment effect size between canonical and uniform weighting.
2. Gradient norm distributions exhibit extreme multi-modality driven by single outlier scenes rather than systematic class properties.
3. Numerical instability (underflow to zero or floating-point denormals) prevents reliable calculation of cosine similarity vectors.
4. Insufficient dual-supported minibatches ($K < 5$ parent clusters represented with concurrent rare and common mask support).

### 4.7 Stop Conditions
Immediate execution termination if:
1. Any gradient computation produces `NaN`, `Inf`, or unrecoverable numerical overflow.
2. Any routine attempts file system access to `data/ops02/tiles/holdout` or Part III directories.
3. Any parameter update (`optimizer.step()`) occurs during a designated passive gradient profiling task.
4. Runtime compute exceeds pre-allocated budget thresholds (15 min CPU, 60 min GPU).

---

## 5. Evidence Level Discipline & Causal Scope Boundaries

In strict compliance with `BLOCK-004-CAUSAL_OVERCLAIM` and lessons learned from C22-D, C22-I/J, and DIAG-04 audits, all claims resulting from DIAG-05 are bound to three mutually exclusive causal tiers:

```
+---------------------------------------------------------------------------------------------------+
| LEVEL A: INSTANTANEOUS LOSS-GRADIENT EFFECT (Paired Counterfactual)                              |
| - Scope: Direct mathematical effect of swapping W_canonical for W_uniform on identical batch.     |
| - Classification: CAUSAL_ESTABLISHED (Single-variable mathematical intervention on fixed theta).  |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
| LEVEL B: SHORT-HORIZON TRAINING TRAJECTORY EFFECT (Controlled 5-Epoch Protocol)                   |
| - Scope: Trajectory divergence, gradient evolution, and 5-epoch dev_mIoU delta under constant LR. |
| - Classification: CAUSAL_SHORT_HORIZON_INTERVENTION (Strictly bounded to the defined protocol).   |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
| LEVEL C: FULL CANONICAL TRAINING RECOVERY (20-Epoch Protocol with Cosine Annealing)               |
| - Scope: Explaining baseline failure or predicting final convergence of the production model.     |
| - Classification: STRICTLY PROHIBITED TO CLAIM FROM DIAG-05 (Extrapolation beyond design).       |
+---------------------------------------------------------------------------------------------------+
```

### Evidence Hierarchy Table:
| Evidence Level | Permitted Scope in DIAG-05 | Prohibited Narrative Traps |
| :--- | :--- | :--- |
| **`OBSERVED`** | Direct, deterministic mathematical measurements: per-layer gradient $L_2$ norms, log-ratios $\Lambda_l$, exact vector cosine similarities on identical batches, finite-check booleans. | Stating that observed gradient norms "explain" final model accuracy. |
| **`SUPPORTED`** | Descriptive correspondence backed by multiple replications and non-overlapping confidence intervals across parent clusters ($K=52$) or seeds ($n=3$). | Concluding that gradient dispersion "causes" low mIoU without an interventional recovery experiment. |
| **`PLAUSIBLE`** | Mechanistic hypotheses consistent with observations: e.g., persistent negative cosine similarity between rare and common masks may induce destructive interference during SGD. | Asserting destructive interference as an established operational law without paired trajectory ablation. |
| **`CAUSAL_SHORT_HORIZON`** | Permitted **ONLY** for outcomes within the controlled 5-epoch, constant-LR intervention where all other variables are strictly locked. | Extrapolating short-horizon effects to full 20-epoch training recovery. |

---

## 6. Dataset Contract & Strict Lineage Lock

DIAG-05 inherits the frozen canonical OPS-02 dataset specification. Any divergence from this specification triggers an immediate fail-closed abort:

| Dataset Parameter | Canonical Authoritative Specification | Verification & Integrity Rule |
| :--- | :--- | :--- |
| **Dataset Identifier** | `OPS-02` | Must strictly match `OPS-02 Physical Dataset Manifest`. Reverting to OPS-01 is forbidden. |
| **Freeze Specification** | `OPS02_v1.0.1_FROZEN` | Governed by `data/ops02/OPS02_DATASET_FREEZE_SPEC_v1.0.1.json`. |
| **Physical Manifest Path** | `data/ops02/manifests/ops02_physical_dataset_manifest_v1.json` | Explicit path check. |
| **Manifest SHA-256** | `F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102` | Exact 64-character hexadecimal bitwise digest. |
| **TRAIN Partition** | **132 tiles** across **40 parent clusters** | Authorized for gradient profiling and controlled training. |
| **DEV Partition** | **40 tiles** across **12 parent clusters** | Authorized strictly for validation evaluation (`dev_mIoU_phenomena`). |
| **HOLDOUT Partition** | **40 tiles** across **12 parent clusters** | **STRICTLY QUARANTINED (`0` access)**. Governed by `BLOCK-001-HOLDOUT`. |
| **Part III External** | `experiments/performance/phase_6_part_iii_external_evaluation` | **STRICTLY FIREWALLED (`0` access)**. Governed by `BLOCK-002-PART_III`. |
| **Development Population** | **172 tiles** across **52 parent clusters** | Total accessible pool for model development. |
| **Nominal Pixel Spacing** | $100.0\text{ m}$ ($0.1\text{ km/pixel}$) | Canonical spatial resolution. |
| **Grid Dimensions** | $256 \times 256\text{ pixels}$ ($25.6 \times 25.6\text{ km}$) | Input tensor dimensions `[B, 1, 256, 256]`. |
| **Normalization Constants** | $\mu=4.424158, \sigma=0.469261$ (`INV-06`) | Immutable TRAIN valid-pixel standardization. |

---

## 7. Training & Gradient Governance: The `BLOCK-006` Reconciliation

### 7.1 The Methodological Conflict
- Computing gradient norms ($\|\nabla_\theta \mathcal{L}\|_2$) and gradient cosine similarities requires invoking `loss.backward()` to populate `.grad` attributes on model parameters.
- `AGENT_GOVERNANCE.md` Section 5 defines `BLOCK-006-UNAUTHORIZED_TRAINING`:  
  *"Invoking PyTorch backward passes, optimizer steps, or GPU allocations during diagnostic tasks. BLOCKS EXECUTION. Diagnostic governance counters must be 0."*
- In DIAG-01 through DIAG-04, this rule was strictly enforced (`backward_passes == 0`).
- If `BLOCK-006` is inherited unconditionally, DIAG-05 becomes **scientifically impossible** because gradients cannot be measured without backpropagation.

### 7.2 Governance Resolution & Two-Tier Architecture
We resolve this without weakening governance integrity by defining two distinct operational tiers:

```
+--------------------------------------------------------------------------------------------------+
| TIER 1: STATIC CHECKPOINT GRADIENT PROFILING (Passive Diagnostic Profiling)                     |
| - Model in eval mode (model.eval()), BatchNorm running stats frozen.                            |
| - Checkpoint is frozen (Step 0 init or Epoch 5 intermediate).                                    |
| - Backward passes executed on paired batches: backward_passes <= 120.                            |
| - ZERO optimizer steps (optimizer_steps == 0), ZERO parameter updates (parameter_updates == 0).  |
| - Measures instantaneous gradient geometry, layer norms, log-ratios, and within-batch cosine.   |
| - Governance Requirement: Requires a targeted protocol waiver authorizing backward_passes > 0   |
|   strictly bounded by optimizer_steps == 0 and parameter_updates == 0.                           |
+--------------------------------------------------------------------------------------------------+
                                                 │
                                                 ▼
+--------------------------------------------------------------------------------------------------+
| TIER 2: CONTROLLED SHORT-HORIZON TRAINING INTERVENTION (Active Interventional Experiment)       |
| - Twin paired training runs (Control vs Treatment) over 5 epochs on OPS-02 TRAIN.               |
| - optimizer_steps > 0, parameter_updates > 0, GPU compute authorized.                            |
| - Directly measures dynamic optimization trajectory, loss convergence, and dev_mIoU_phenomena.  |
| - Governance Requirement: CANNOT execute as a diagnostic task. Requires formal reclassification |
|   under an authorized interventional protocol (e.g. EXP07_P0_C23_DIAG05_PROTOCOL).              |
+--------------------------------------------------------------------------------------------------+
```

### 7.3 Prerequisite Authorization Gate
Because neither Tier 1 nor Tier 2 can be executed under the unmodified `diagnostic` task contract (`backward_passes == 0`), this pre-execution audit concludes that DIAG-05 is **`PLAN_READY_WITH_PREREQUISITES`**.

**Explicit Prerequisites for Execution:**
1. A formal protocol amendment authorizing **Tier 1 Static Profiling** under an isolated diagnostic execution class where `backward_passes <= 120` is permitted provided `optimizer_steps == 0`, `parameter_updates == 0`, and `holdout_access == 0`.
2. A separate user execution authorization explicitly approving Tier 1 execution.
3. If Tier 1 results indicate significant gradient conflict, a dedicated interventional protocol specification (`EXP07_P0_C23`) must be authored and approved before any Tier 2 dynamic training is initiated.

---

## 8. Causal Identification Audit: Within-Batch Counterfactual Masking

### 8.1 Methodological Mandate: Within-Batch Isolation & Subgradient Decomposition

Comparing gradients from separate physical minibatches (e.g., a "common batch" vs a "rare batch") fatally conflates scene content differences with loss-gradient dynamics. To achieve rigorous counterfactual isolation, DIAG-05 mandates **Within-Batch Counterfactual Masking**:

For every selected physical minibatch $B = \{(X_i, Y_i)\}_{i=1}^4$:
1. Both gradient vectors $g_{\text{rare}}$ and $g_{\text{common}}$ are computed from the **identical input image tensor $X$** and **identical ground-truth raster $Y$**.
2. Deterministic binary masks $M_{\text{rare}}$, $M_{\text{common}}$, and $M_{\text{other}}$ are constructed on $Y$.
3. **Mathematical Formulation of Masked Loss & Subgradient Decomposition (`LL-DIAG05-PLAN-010`):**
   - **The Full-Batch Weighted Objective:**
     In canonical training with `CrossEntropyLoss(reduction='mean')`, the total batch loss is:
     $$\mathcal{L}_{\text{batch}}(B; w) = \frac{\sum_{i \in B_{\text{valid}}} w_{y_i} \cdot \ell(f(X)_i, y_i)}{\sum_{i \in B_{\text{valid}}} w_{y_i}} = \frac{1}{D_{\text{batch}}(w)} \sum_{i \in B_{\text{valid}}} w_{y_i} \cdot \ell_i$$
     where $D_{\text{batch}}(w) = \sum_{i \in B_{\text{valid}}} w_{y_i}$ is the valid-pixel weight sum. Because $D_{\text{batch}}$ depends strictly on the ground-truth labels $Y$ and the fixed class-weight vector $w$, it is a constant scalar with respect to model parameters $\theta$ ($\nabla_\theta D_{\text{batch}} = 0$).
   - **Exact Condition for Linear Subgradient Decomposition:**
     The decomposition $g_{\text{rare}} + g_{\text{common}} + g_{\text{other}} = g_{\text{total}}$ holds mathematically from first principles **if and only if**:
     1. The subset masks form a mutually exclusive and exhaustive partition of all valid pixels:
        $$M_{\text{rare}} \cap M_{\text{common}} = \emptyset, \quad M_{\text{rare}} \cap M_{\text{other}} = \emptyset, \quad M_{\text{common}} \cap M_{\text{other}} = \emptyset, \quad M_{\text{rare}} \cup M_{\text{common}} \cup M_{\text{other}} = B_{\text{valid}}$$
     2. All 12 canonical classes are assigned to exactly one subset component.
     3. Ignored pixels ($y_i = -100$) are consistently excluded from all subset numerators and the shared denominator $D_{\text{batch}}$.
     4. Every component uses the **identical shared full-batch denominator** $D_{\text{batch}}(w)$.
   - **Mathematical Proof of Linearity:**
     $$\nabla_\theta \mathcal{L}_{\text{batch}} = \frac{1}{D_{\text{batch}}} \sum_{i \in B_{\text{valid}}} w_{y_i} \nabla_\theta \ell_i = \frac{1}{D_{\text{batch}}} \left[ \sum_{i \in M_{\text{rare}}} w_{y_i} \nabla_\theta \ell_i + \sum_{i \in M_{\text{common}}} w_{y_i} \nabla_\theta \ell_i + \sum_{i \in M_{\text{other}}} w_{y_i} \nabla_\theta \ell_i \right]$$
     $$= \nabla_\theta \left( \frac{\sum_{i \in M_{\text{rare}}} w_{y_i} \ell_i}{D_{\text{batch}}} \right) + \nabla_\theta \left( \frac{\sum_{i \in M_{\text{common}}} w_{y_i} \ell_i}{D_{\text{batch}}} \right) + \nabla_\theta \left( \frac{\sum_{i \in M_{\text{other}}} w_{y_i} \ell_i}{D_{\text{batch}}} \right) = g_{\text{rare}} + g_{\text{common}} + g_{\text{other}}$$
   - **Critical Estimand Distinction: Contribution vs Isolated Loss:**
     - **Estimand A (Measured & Reported):** "Masked gradient contribution under the full-batch reduction denominator":
       $$g_{\text{subset}} \triangleq \nabla_\theta \left( \frac{\sum_{i \in M_{\text{subset}}} w_{y_i} \ell_i}{D_{\text{batch}}(w)} \right) = \frac{1}{D_{\text{batch}}(w)} \sum_{i \in M_{\text{subset}}} w_{y_i} \nabla_\theta \ell_i$$
       This represents the actual force vector that the subset contributes to the full-batch step $\Delta \theta = -\eta g_{\text{total}}$ taken by the optimizer.
     - **Estimand B (Isolated Normalized Loss):** "Gradient of an isolated loss normalized only on that subset":
       $$g_{\text{isolated}} \triangleq \nabla_\theta \left( \frac{\sum_{i \in M_{\text{subset}}} w_{y_i} \ell_i}{\sum_{i \in M_{\text{subset}}} w_{y_i}} \right)$$
       This answers what the gradient would be if training solely on that subset. Crucially, $\sum_k g_{\text{isolated}, k} \neq g_{\text{total}}$.
     - **Mandatory Reporting Requirement:** All scientific reports MUST use the precise qualification: *"masked gradient contribution under the full-batch reduction denominator"*. Calling this simply "the class-specific loss gradient" without qualification is prohibited (`LL-DIAG05-PLAN-010`).
   - **Single-Class Weight Cancellation Proof (`LL-DIAG05-PLAN-005`):**
     If an isolated subset loss $\mathcal{L}_{\text{isolated}}$ is evaluated on a mask $M_c$ where all pixels belong to a single class $c$ ($y_i = c \;\forall i \in M_c$), the scalar weight $w_c$ factors out identically:
     $$\mathcal{L}_{\text{isolated}}(M_c; w) = \frac{\sum_{i \in M_c} w_{y_i} \ell_i}{\sum_{i \in M_c} w_{y_i}} = \frac{w_c \sum_{i \in M_c} \ell_i}{w_c |M_c|} = \frac{1}{|M_c|} \sum_{i \in M_c} \ell_i = \mathcal{L}_{\text{isolated}}(M_c; \mathbf{1})$$
     Consequently, $w_c$ cancels completely from both numerator and denominator, rendering isolated weighted and uniform loss gradients bitwise identical ($\nabla_\theta \mathcal{L}_{\text{isolated}}(M_c; w) \equiv \nabla_\theta \mathcal{L}_{\text{isolated}}(M_c; \mathbf{1})$). The full-batch denominator construction avoids this cancellation because $D_{\text{batch}}$ sums over all valid pixels in the entire scene, preserving the relative scaling $w_c / D_{\text{batch}}$.
   - **Weight Intervention Identifiability & Denominator Shift:**
     When comparing $\|g_{\text{subset}}^{\text{canonical}}\|_2$ vs $\|g_{\text{subset}}^{\text{uniform}}\|_2$, the denominator $D_{\text{batch}}(w)$ differs:
     $$D_{\text{batch}}(w^{\text{canonical}}) = \sum_{i \in B_{\text{valid}}} w_{y_i}^{\text{canonical}}, \quad D_{\text{batch}}(\mathbf{1}) = N_{\text{valid}}$$
     Comparing the two arms inherently reflects:
     1. Numerator class-weight scaling ($w_{y_i}$ vs $1.0$);
     2. Normalization denominator shift ($D_{\text{batch}}(w^{\text{canonical}})$ vs $N_{\text{valid}}$).
     This is explicitly intended, as it mirrors the exact operational reality experienced by the optimizer when switching loss configurations. For a single-class mask $c$, the ratio decomposes cleanly:
     $$\frac{\|g_c^{\text{canonical}}\|_2}{\|g_c^{\text{uniform}}\|_2} = w_c \cdot \frac{N_{\text{valid}}}{D_{\text{batch}}(w^{\text{canonical}})} = \frac{w_c}{\bar{w}_{\text{batch}}}$$
     where $\bar{w}_{\text{batch}} = D_{\text{batch}} / N_{\text{valid}}$ is the scene-mean class weight. The net gradient scaling experienced by AdamW is exactly $w_c$ normalized by the scene average weight.
   - **Exact Canonical Loss Weight Vector ($W_{\text{canonical}}$):**
     Programmatically bound to `exp07_fingerprint.py::CANONICAL_HISTORICAL_C16_LITERALS` and `data/ops02/audits/ops02_c19_loss_weight_canonicalization_v1.json`:
     $$W_{\text{canonical}} = [0.403935, 2.450546, 0.876692, 0.945945, 0.648189, 4.211476, 0.719641, 2.956203, 1.064525, 1.882870, 0.387652, 18.243211]$$
     Under Control (Uniform Arm): $W_{\text{uniform}} = \mathbf{1}_{12}$.
   - **Zero-Mask & Low-Support Policies (`LL-DIAG05-PLAN-007`):**
     - **Absent Mask ($|M_{\text{subset}}| = 0$):** Classified as `INELIGIBLE_ABSENT_MASK`. The backward pass is skipped, logged in the exclusion census, and strictly **zero** is NOT recorded as an observation in continuous distributions.
     - **Positive Low Support ($0 < |M_{\text{subset}}| < 16$):** RETAINED in the analysis. The exact pixel support count $|M_{\text{subset}}|$ is logged alongside gradient estimates. Flagged as `LOW_SUPPORT_ESTIMATE` to prevent rarity from becoming exclusion bias, and evaluated in sensitivity analyses against higher-support strata.
4. **Deterministic Forward Recomputation Invariant (`LL-DIAG05-PLAN-002`):**
   - Calling `loss_rare.backward(retain_graph=True)` causes intermediate activation retention bloat and fails with `RuntimeError` due to in-place ReLU operations in `DoubleConv` and torchvision's `resnet18` backbone.
   - Four backward passes are the registered execution implementation because the required masked gradient vectors are obtained through independent forward/backward evaluations without retained computation graphs; this avoids the memory and graph-lifetime risks of graph reuse.
   - DIAG-05 mandates **Deterministic Recomputation on Identical Inputs**:
     - Pass 1: Forward $X \to Z$, compute $\mathcal{L}_{\text{rare}}$, call `backward()`, extract and detach $g_{\text{rare}}$, call `optimizer.zero_grad()`.
     - Pass 2: Re-run forward pass with identical $X$ and $\theta$ under `model.eval()` (yielding bitwise identical logits $Z$), compute $\mathcal{L}_{\text{common}}$, call `backward()`, extract and detach $g_{\text{common}}$, call `optimizer.zero_grad()`.
     - Pass 3: Re-run forward pass with identical $X$ and $\theta$ under `model.eval()`, compute $\mathcal{L}_{\text{other}}$, call `backward()`, extract and detach $g_{\text{other}}$, call `optimizer.zero_grad()`.
     - Retaining computation graphs across backward passes is **prohibited**.
5. Autograd backward passes compute parameter gradients against the identical model state $\theta$:
   $$g_{\text{rare}} = \nabla_\theta \mathcal{L}_{\text{rare}}(B), \quad g_{\text{common}} = \nabla_\theta \mathcal{L}_{\text{common}}(B), \quad g_{\text{other}} = \nabla_\theta \mathcal{L}_{\text{other}}(B)$$
6. The cosine similarity $\cos(g_{\text{rare}}, g_{\text{common}})$ isolates pure directional alignment on identical physical inputs.

```
       Identical Physical Minibatch B (X, Y) on Fixed Checkpoint θ (model.eval())
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
   [Forward Pass 1]         [Forward Pass 2]         [Forward Pass 3]
     Mask M_rare              Mask M_common            Mask M_other
     L_rare(B; W)             L_common(B; W)           L_other(B; W)
     g_rare (detached)        g_common (detached)      g_other (detached)
     zero_grad()              zero_grad()              zero_grad()
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
         Linear Decomposition: g_total = g_rare + g_common + g_other
         Within-Batch Cosine Alignment: cos(g_rare, g_common) on Identical B
```

### 8.2 Exact Taxonomy Class Groupings & Resultant Vector Caution

Class groupings are derived directly from canonical OPS-02 support and taxonomy definitions (`LL-EXP07-002`):
- **Rare-Class Set ($\mathcal{C}_{\text{rare}}$):**
  - **Classes:** `OF` (Class 5, Oceanic Front, 22,536 px, weight 4.211476), `RF` (Class 7, Rain Footprint, 45,738 px, weight 2.956203), `HM` (Class 11, Human-Made Objects, 1,201 px, weight 18.243211).
  - **Scientific Justification:** These three classes have the lowest total pixel support in OPS-02 TRAIN and the highest inverse-frequency loss weights in the canonical vector ($>2.95$). They represent the primary targets hypothesized to suffer severe gradient dispersion under canonical weighting.
- **Common-Phenomena Class Set ($\mathcal{C}_{\text{common}}$):**
  - **Classes:** `AF` (1, Atmospheric Front), `BS` (2, Biological Slicks), `MCC` (4, Mesoscale Cellular Convection), `POW` (6, Pure Ocean Wave), `WS` (8, Wind Streak), `Eddy` (9, Oceanic Eddy), `IWs` (10, Internal Waves).
  - **Scientific Justification:** Dynamic meteorological and oceanographic phenomena with moderate to high prevalence.
  - **Critical Resultant Vector Warning:**
    Because $\mathcal{C}_{\text{common}}$ aggregates 7 distinct phenomena, the aggregate gradient:
    $$g_{\text{common}} = \sum_{c \in \mathcal{C}_{\text{common}}} g_c$$
    is a **resultant vector**. Different phenomena classes (e.g. bright convective clouds in MCC vs dark biogenic slicks in BS) may have opposing gradient components ($g_{\text{MCC}} \cdot g_{\text{BS}} < 0$). Internal orthogonalities or cancellations among common classes can attenuate $\|g_{\text{common}}\|_2$ even when individual class gradients are large. Therefore, $\cos(g_{\text{rare}}, g_{\text{common}})$ evaluates alignment against this **net aggregate resultant force vector**, NOT a single representative "common-class direction".
- **Other Set ($\mathcal{C}_{\text{other}}$):**
  - **Classes:** `BG` (Class 0, Background Seawater, 2,449,755 px), `LWA` (Class 3, Low Wind Area, 446,698 px).
  - **Scientific Justification for Exclusion from Common Phenomena:**
    - **Background (`BG`):** Ambient seawater matrix (>28% of pixels), which represents the non-phenomenon baseline. In segmentation, the primary metric `dev_mIoU_phenomena` evaluates phenomena classes 1–11, excluding BG.
    - **Low Wind Area (`LWA`):** As established in C11, C12, C13, and DIAG-03 forensics, LWA is a calm sea state lookalike regime ($<2.5\text{ m/s}$ surface wind) characterized by the physical absence of Bragg backscatter rather than a dynamic convective or wave phenomenon.
    - Assigning `BG` and `LWA` to $\mathcal{C}_{\text{other}}$ ensures the 3-way partition covers 100% of valid pixels, strictly preserving the mathematical decomposition $g_{\text{rare}} + g_{\text{common}} + g_{\text{other}} = g_{\text{total}}$ without distorting the directional dynamics of dynamic common phenomena.
- **Authoritative Primary Estimand vs Secondary Sensitivity Sets:**
  - **Authoritative Primary Grouping:** The 3-way partition ($\mathcal{C}_{\text{rare}} = \{5, 7, 11\}$, $\mathcal{C}_{\text{common}} = \{1, 2, 4, 6, 8, 9, 10\}$, $\mathcal{C}_{\text{other}} = \{0, 3\}$) is the **ONE and ONLY PRIMARY CONFIRMATORY ESTIMAND** for H2. It directly tests the primary scientific question: *"Does changing the class-loss weighting alter the directional geometry between rare-class and aggregate-common masked gradient contributions at Step 0?"*
  - **Secondary Sensitivity Sets:** Alternative subsets (such as extended rare including BS $\{5, 7, 11, 2\}$, common with background $\{0, 4, 10\}$, or common phenomena subset $\{4, 10\}$) are strictly secondary exploratory sensitivity checks. They provide robustness context but must NEVER displace, alter, or dilute the primary H2 question.

### 8.3 Batch Selection Feasibility, Dual-Support Invariants & Dual-Population Reporting
- **Empirical Feasibility Census on OPS-02 TRAIN (132 tiles across 40 clusters):**
  - Exactly 31 tiles contain rare-core annotations (`OF`, `RF`, `HM`).
  - Under the authoritative Primary Common-7 grouping (`AF`, `BS`, `MCC`, `POW`, `WS`, `Eddy`, `IWs`), exactly **28 physical tiles** contain simultaneous rare-core and common-phenomena annotations ($M_{\text{rare}} \ge 16$ px and $M_{\text{common}} \ge 64$ px), spanning **15 parent acquisition clusters**.
  - *(Historical Sensitivity Context: The earlier exploratory draft using Common-2 [only `MCC` and `IWs`] contained 16 tiles spanning 12 clusters; under `LL-DIAG05-PLAN-024`, cluster-pure single-tile physical observations $B_{\text{phys}}=1$ replaced the obsolete 4-tile multi-cluster chunking that previously yielded 11 mixed minibatches).*
- **Ascertainment Bias Mitigation via Dual-Population Reporting (`LL-DIAG05-PLAN-003`):**
  - Filtering physical observations for simultaneous presence of rare and common classes conditions the estimand strictly on scene co-occurrence, introducing ascertainment bias.
  - To prevent biased generalization, DIAG-05 mandates **Dual-Population Reporting**:
    1. **Population 1 (Conditional Co-Occurrence Gradient-Geometry Estimand):** Evaluates within-batch cosine similarity $\cos(g_{\text{rare}}, g_{\text{common}})$ strictly on eligible dual-supported cluster-pure physical observations ($B_{\text{phys}}=1$, 28 tiles across 15 clusters). Must report: total physical observations evaluated, eligible count, excluded count, and exclusion reason breakdown (`INSUFFICIENT_RARE_SUPPORT`, `INSUFFICIENT_COMMON_SUPPORT`).
    2. **Population 2 (Full-Population Unconditional Gradient Profile):** Evaluates layer-wise gradient norm dispersion and Log-Norm Ratios $\Lambda_l$ across all 33 minibatches (132 physical tiles, $B_{\text{phys}}=4$) in OPS-02 TRAIN without conditioning on co-occurrence.
- **Support Logging & Sensitivity Stratification:**
  - Zero support ($|M_{\text{subset}}| = 0$): flagged as `INELIGIBLE_ABSENT_MASK`, backward pass skipped, excluded from continuous distributions.
  - Positive low support ($0 < |M_{\text{subset}}| < 16$): retained in analysis, exact support count logged, flagged as `LOW_SUPPORT_ESTIMATE` to avoid selection bias.
- **Deterministic Batch Selection & Parity Rule:**
  - Minibatches are chunked deterministically from the 132 sorted OPS-02 TRAIN tiles.
  - Exactly identical physical batches in identical order are evaluated under Control ($W_{\text{canonical}}$) and Treatment ($W_{\text{uniform}}$).
- **Model State & BatchNorm Invariant:**
  - Tier 1 runs strictly with `model.eval()`. All 30 BatchNorm2d layers (`affine=True`, canonical `momentum=0.05`) hold frozen running statistics ($\mu_{\text{running}}, \sigma^2_{\text{running}}$) from the canonical initialization checkpoint (`initial_model_state_canonical.pt`).
  - No BatchNorm running statistics updates occur during Tier 1 profiling.
  - H2 evaluates static Step-0 directional loss-gradient geometry on fixed representations; it is not equivalent to, and does not simulate, Tier-2 training-time batch-normalization or optimizer dynamics.
  - Under `model.eval()`, normalization is a fixed, deterministic linear transform per channel, guaranteeing exact counterfactual parity across sequential backward passes ($g_{\text{rare}}$, $g_{\text{common}}$, $g_{\text{other}}$) and mathematical validity for cluster-pure physical observations ($B_{\text{phys}}=1$).
  - Gradients $g_{\text{rare}}$, $g_{\text{common}}$, and $g_{\text{other}}$ are computed sequentially on identical model weights $\theta_0$ with `optimizer.zero_grad()` between passes.

---

## 9. Independent Units, Sample Size & Statistical Design

### 9.1 Separation of Computational Observations vs Statistical Independence
To eliminate pseudoreplication (`BLOCK-009-PSEUDO_REPLICATION`):
- **Computational Observations:** Individual pixel loss contributions ($N > 10^7$) and individual minibatches ($B=4$). Minibatches from the same Sentinel-1 datatake share environmental conditions and are clustered observations, NOT independent degrees of freedom.
- **Data-Domain Statistical Independence Unit:** The **Parent Acquisition Mission Datatake Cluster ($K$)** ($K=40$ TRAIN, $K=12$ DEV, $K=52$ Development total).
- **Model-Domain Replication Unit:** Independent initialization seeds ($n=3$: 42, 101, 202).
- **Resampling Method:** Parent-cluster block bootstrap ($B=1000$) resampling clusters with replacement to derive 95% confidence intervals.

### 9.2 Continuous Cosine Angle Distribution & Calibrated Thresholds
- **Primary Metric:** The **continuous empirical distribution** of $\cos(g_{\text{rare}}, g_{\text{common}}) \in [-1, 1]$ across all dual-supported minibatches and layers.
- **Descriptive Threshold Categories (Not Proof Cutoffs):**
  - **Strong Negative Alignment:** $\cos < -0.5$
  - **Moderate Negative Alignment:** $-0.5 \le \cos < -0.1$
  - **Orthogonal / Unaligned:** $-0.1 \le \cos \le 0.1$
  - **Moderate Positive Alignment:** $0.1 < \cos \le 0.5$
  - **Strong Positive Alignment:** $\cos > 0.5$
- **Calibration Rule:** Crossing an arbitrary threshold (e.g. $\cos < -0.2$) is **descriptive categorization**, NOT proof of harmful training dynamics or "destabilizing interference". Directional interference can only be claimed as harmful if paired dynamic training shows impaired learning on those specific layers.

### 9.3 Layer-Wise Norm Ratios, RMS Normalization & Denominator Handling Policy
For layer $l$, the raw norm ratio is $R_l = \frac{\|\nabla_{\theta_l} \mathcal{L}_{\text{canonical}}\|_2}{\|\nabla_{\theta_l} \mathcal{L}_{\text{uniform}}\|_2}$.

**Pre-Registered Handling Policy:**
1. **Primary Summary Metric — Log-Norm Ratio ($\Lambda_l$):**
   $$\Lambda_l = \log_{10} \|\nabla_{\theta_l} \mathcal{L}_{\text{canonical}}\|_2 - \log_{10} \|\nabla_{\theta_l} \mathcal{L}_{\text{uniform}}\|_2$$
   Log-ratio is preferred because it is symmetric around 0 ($\Lambda_l = 0 \iff$ equal norms), avoids division-by-near-zero instability, and maps 10-fold amplification to $+1.0$ and 10-fold attenuation to $-1.0$. Ratios are computed strictly when both $\|\nabla_{\theta_l} \mathcal{L}_{\text{canonical}}\|_2 > 0$ and $\|\nabla_{\theta_l} \mathcal{L}_{\text{uniform}}\|_2 > 0$.
2. **Exact Zero Denominator Policy & Categorical Censoring:**
   If $\|\nabla_{\theta_l} \mathcal{L}_{\text{uniform}}\|_2 = 0.0$, the event is flagged as `DENOMINATOR_EXACT_ZERO_VANISHED`. $R_l$ and $\Lambda_l$ are logged as undefined ($+\infty$) and excluded from continuous ratio aggregations. Zero occurrences are tracked and reported as discrete point masses.
3. **Rigorous Floating-Point Precision & Zero-Regularizer Policy (`LL-DIAG05-PLAN-006`):**
   IEEE 754 single-precision float32 machine epsilon $\epsilon_{\text{mach}} = 2^{-23} \approx 1.1920929 \times 10^{-7}$ represents the relative unit roundoff for values of order unity. It is **not** an absolute lower bound on representable gradient magnitude, as float32 normal positive numbers extend down to $2^{-126} \approx 1.1754944 \times 10^{-38}$ (and subnormals to $1.40 \times 10^{-45}$).
   - **Direct Positive Logs Without Artificial Regularizers:** For all positive norms ($\|g_l\|_2 > 0$), $\log_{10}(\|g_l\|_2)$ is evaluated directly without adding any artificial regularizer $\tau_{\text{reg}}$ to physical gradient vectors.
   - **Categorical Censoring:** Exact zero norms ($\|g_l\|_2 == 0.0$) are categorically censored as `CENSORED_ZERO_GRADIENT`.
   - **Near-Zero Flagging:** Norms below $10^{-7}$ are flagged descriptively as `NEAR_ZERO_HIGH_VARIANCE` to alert analysts to potential numerical roundoff sensitivity, without modifying the underlying gradient values. Arbitrary ad-hoc epsilon constants in denominators remain strictly prohibited.
4. **Distinct Scientific Roles of Raw $L_2$ Norm vs RMS Gradient Scale (`LL-DIAG05-PLAN-011`, `LL-DIAG05-PLAN-016`):**
   - **Raw $L_2$ Norm ($\|g_l\|_2$):** Primary physical metric answering the total Euclidean force vector magnitude in the parameter subspace of module $l$. This directly determines global gradient clipping activation (`torch.nn.utils.clip_grad_norm_`, threshold $\text{max\_norm}=1.0$), but does **NOT** directly govern AdamW parameter update magnitude due to coordinate-wise second-moment preconditioning ($\sqrt{\hat{v}_t} + \epsilon$) and decoupled weight decay ($\eta \lambda \theta_{t-1}$). Under AdamW, coordinates with persistently large gradients experience automatic second-moment dampening. In Tier 2, parameter update magnitude is measured strictly as actual observed parameter displacement $\|\theta_t - \theta_{t-1}\|_2$.
   - **Root Mean Square (RMS) gradient magnitude ($\text{RMS}(g_l) = \|g_l\|_2 / \sqrt{P_l}$, also denoted RMS(g_l)):** Secondary normalized metric answering the root-mean-square gradient magnitude per scalar parameter, where $P_l$ is the parameter count of module $l$. Because $P_l$ spans orders of magnitude (from $780$ in `head` to $1,179,648$ in `layer4.0.conv1`), raw $L_2$ norms naturally scale with $\sqrt{P_l}$ under random initialization. RMS normalization is strictly required for cross-layer depth comparisons to assess per-parameter excitation across depths. Raw $L_2$ and RMS answer different legitimate scientific questions and are not interchangeable.
5. **Multiple Comparison Policy:**
   Tier 1 static profiling is primarily an exploratory/descriptive empirical characterization of initial gradient geometry across modules, not a family of null-hypothesis significance tests (NHST). Mechanically applying Benjamini-Hochberg FDR to descriptive histograms or distribution percentiles is a category error. If and only if formal hypothesis tests are conducted across the 10 stage-representative targets (e.g. testing directional opposition $H_0: \mathbb{E}[\cos] \ge 0$), Benjamini-Hochberg FDR at $q=0.05$ applies to that predefined 10-test family.

---

## 10. Two-Tier Experimental Methodology

### 10.1 Tier 1: Static Checkpoint Paired Gradient Geometry Profiling
1. **Model Loading, Checkpoint Provenance & Scope Limitation:**
   - Checkpoint is strictly: `data/ops02/initial_model_state_canonical.pt` at Step 0 (`epoch = 0, step = 0`).
   - Cryptographic SHA-256 Digest: `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D`.
   - Provenance: ImageNet pretrained ResNet18 backbone + Kaiming normal UNet decoder under seed 42 (`EXP07_P0_C22A4`).
   - Model set to `model.eval()` to strictly freeze BatchNorm running statistics across all 30 BatchNorm2d layers (no running statistics updates occur during Tier 1 profiling).
   - **Scope Limitation:** Tier 1 measures instantaneous loss-gradient geometry exclusively at initialization (Step 0) as a static directional diagnostic; it is not equivalent to, and does not simulate, Tier-2 training-time optimizer or BatchNorm dynamics. Because no post-adaptation checkpoint is authorized or exists, Tier 1 **CANNOT** answer whether gradient geometry changes after adaptation. Post-adaptation dynamics are investigated strictly through Tier 2 controlled training.
2. **Minibatch Evaluation & Population Definitions (`LL-DIAG05-PLAN-003`, `LL-DIAG05-PLAN-013`, `LL-DIAG05-PLAN-022`):**
   - **Population A (Co-Occurrence Interaction):** Deterministically evaluate eligible dual-supported physical observations as cluster-pure physical tile observations ($B_{\text{phys}}=1$ or cluster-pure minibatch of up to 4 tiles from that single cluster) from OPS-02 TRAIN satisfying $|M_{\text{rare}}| > 0$ and $|M_{\text{common}}| > 0$. As proven in `LL-DIAG05-PLAN-024`, physical batches of $B_{\text{phys}}=8$ in OPS-02 inevitably mix tiles across multiple parent acquisition clusters (since all TRAIN clusters have $\le 4$ tiles), destroying cluster identifiability. Raw H2 observations are strictly restricted to cluster-pure physical observations, guaranteeing an exact, unambiguous 1-to-1 mapping to parent acquisition clusters. Explicitly: H2 is a Step-0 directional-gradient diagnostic and does **NOT** reproduce the optimizer accumulation boundary (accumulation $A=2$ / effective batch size 16 is reserved strictly for Tier 2). Subject to ascertainment bias; evaluates directional alignment between rare and aggregate-common resultants.
   - **Population B (Full-Dataset Physical Census):** Unconditionally evaluate all 33 minibatches in OPS-02 TRAIN ($B_{\text{phys}}=4$, 132 physical tiles) for layer-wise within-batch unclipped gradient norm distributions $\|g_b(\theta_0)\|_2$. This is an unconditional full-dataset physical census, **NOT** a sample from the Candidate F dynamic class-conditioned sampler, and does not perform gradient accumulation. Option 1 (full-dataset deterministic census) is chosen for Tier 1 to provide exhaustive, zero-variance geometric coverage at Step 0, while Tier 2 evaluates operational Candidate F sampler dynamics.
3. **Paired Forward & Within-Batch Masked Backward Execution (`LL-DIAG05-PLAN-015`):**
   - **Deterministic Single-Environment Reproducibility:** Repeated evaluations on identical inputs and parameters yield reproducible results within a single execution environment. However, floating-point reductions (parallel atomicAdd, cuBLAS) are non-associative, so universal bitwise identity across different GPU hardware or CUDA stacks is not guaranteed.
   - Forward Pass 1: compute $\mathcal{L}_{\text{rare}}(B; W_{\text{canonical}})$, backward pass, extract layer gradient vectors $g_{\text{rare, ctrl}}$, `optimizer.zero_grad()`.
   - Forward Pass 2: compute $\mathcal{L}_{\text{common}}(B; W_{\text{canonical}})$, backward pass, extract layer gradient vectors $g_{\text{common, ctrl}}$, `optimizer.zero_grad()`.
   - Forward Pass 3: compute $\mathcal{L}_{\text{other}}(B; W_{\text{canonical}})$, backward pass, extract layer gradient vectors $g_{\text{other, ctrl}}$, `optimizer.zero_grad()`.
   - Forward Pass 4: compute $\mathcal{L}_{\text{rare}}(B; W_{\text{uniform}})$, backward pass, extract layer gradient vectors $g_{\text{rare, treat}}$, `optimizer.zero_grad()`.
   - Forward Pass 5: compute $\mathcal{L}_{\text{common}}(B; W_{\text{uniform}})$, backward pass, extract layer gradient vectors $g_{\text{common, treat}}$, `optimizer.zero_grad()`.
   - Forward Pass 6: compute $\mathcal{L}_{\text{other}}(B; W_{\text{uniform}})$, backward pass, extract layer gradient vectors $g_{\text{other, treat}}$, `optimizer.zero_grad()`.
4. **Target Submodules vs Global Aggregation (`LL-DIAG05-PLAN-008`):**
   - **Stage-Representative Target Modules (10 Named Modules):**
     - Encoder Stem: `conv1` (3,136 params)
     - Encoder Stages: `layer1.0.conv1` (36,864 params), `layer2.0.conv1` (73,728 params), `layer3.0.conv1` (294,912 params), `layer4.0.conv1` (1,179,648 params)
     - Decoder Stages: `dec4.conv.conv.0` (1,179,648 params), `dec3.conv.conv.0` (294,912 params), `dec2.conv.conv.0` (73,728 params), `dec1.conv.conv.0` (18,432 params)
     - Output Head: `head` (780 params)
     - *Interpretation Boundary:* These 10 modules sample key architectural depth transitions across the network. They represent stage depth representatives rather than an exhaustive layer-wise census.
   - **Global Gradient Aggregation (All Trainable Parameters):**
     - Flattened 1D concatenation across all 14,310,860 trainable parameters: convolution weights, convolution biases, and BatchNorm affine parameters ($\gamma, \beta$). Non-trainable buffers (BN running mean, running variance, `num_batches_tracked`) are strictly excluded. Falsely categorizing this aggregation as a neural network module is prohibited.
5. **Governance Safety:** Strictly `optimizer_steps == 0` and `parameter_updates == 0`. Model weights verified bitwise identical post-profiling.

### 10.2 Tier 2: Short-Horizon Controlled Training Intervention Protocol

To prevent narrative conflation between production training and diagnostic intervention, the protocols are explicitly contrasted:

| Dimension | Canonical EXP-07 Production Training | DIAG-05 Tier 2 Short-Horizon Intervention | Rationale for Deviation |
| :--- | :--- | :--- | :--- |
| **Optimizer** | AdamW | AdamW | Held strictly constant |
| **Betas / Eps** | $(0.9, 0.999), 10^{-8}$ | $(0.9, 0.999), 10^{-8}$ | Held strictly constant |
| **Gradient Clipping** | $1.0$ ($L_2$ norm) | $1.0$ ($L_2$ norm) | Held strictly constant |
| **Weight Decay** | $0.01$ (conv/linear only) | $0.01$ (conv/linear only) | Held strictly constant |
| **Batch Geometry** | Physical $8$, Accum $2$, Effective $16$, BN $8$ | Physical $8$, Accum $2$, Effective $16$, BN $8$ | Held constant to preserve BN noise scale |
| **Learning Rate** | $5 \times 10^{-4}$ base | Constant $2 \times 10^{-4}$ | Constant LR isolates loss weight dynamics from scheduler |
| **Scheduler** | LinearWarmupCosineAnnealing (30 epochs) | **Disabled** (constant LR across 5 epochs) | Eliminates learning rate decay confounder |
| **Training Horizon** | 30 epochs (min 15, patience 10) | **5 epochs** | Early trajectory window where divergence occurs |
| **Intervention Arm** | Canonical $W_{\text{canonical}}$ only | Arm 1: $W_{\text{canonical}}$ vs Arm 2: $W_{\text{uniform}}$ | Single independent variable: loss weight vector |
| **Causal Scope** | Full benchmark convergence | `CAUSAL_SHORT_HORIZON_INTERVENTION` | **Cannot** claim 20-epoch recovery |

**Causal Scope Limitation:**
- Establishes `CAUSAL_SHORT_HORIZON_INTERVENTION` regarding whether uniform weights alter early optimization trajectories under constant LR.
- **MUST NOT** be claimed to predict or recover 20-epoch canonical training performance with cosine scheduling.

### 10.3 Step Arithmetic & Dataloader Disambiguation (`LL-DIAG05-PLAN-009`)
- **Primary Canonical Dataloader (Candidate F Sampler Schedule):**
  - Parity with INV-16 training pipeline: Candidate F hybrid sampler draws exactly 72 tiles per epoch with replacement.
  - Physical Batch Size: $B=8$.
  - Gradient Accumulation: $2$ physical batches per optimizer step (Effective Virtual Batch: $16$, BN Statistical Batch: $8$).
  - Physical Batches per Epoch: $72 / 8 = 9$ physical batches (zero partial batches).
  - Optimizer Steps per Epoch: Batches 1&2 $\to$ Step 1, Batches 3&4 $\to$ Step 2, Batches 5&6 $\to$ Step 3, Batches 7&8 $\to$ Step 4, Batch 9 $\to$ Step 5 (flush at epoch boundary) $= 5$ optimizer steps per epoch.
  - Steps per Run (5 epochs): $5 \times 5 = 25$ optimizer steps per run.
  - Total across 6 runs (2 arms $\times$ 3 seeds): $6 \times 25 = 150$ optimizer steps total ($270$ physical batches total).
- **Alternative Sequential Traversal (132 Physical Tiles):**
  - 132 tiles per epoch $\to$ 16 full batches of 8 + 1 partial batch of 4 ($17$ physical batches).
  - 9 optimizer steps per epoch $\to$ 45 steps per run $\to$ 270 optimizer steps total across 6 runs ($510$ physical batches).
- **Parity Mandate:** Tier 2 defaults strictly to the **Candidate F Sampler Schedule** (150 optimizer steps across 6 runs) to maintain exact sampling distribution parity with canonical training.

### 10.4 Exact Gradient Clipping Execution Order & Accumulation Boundary (`LL-DIAG05-PLAN-017`)
In canonical training (verified from `scripts/train_exp07.py`), gradient clipping is executed **exclusively at the optimizer accumulation boundary** immediately prior to `optimizer.step()`, and **NEVER** on single physical minibatches:

```
[Physical Batch 1 (B_phys=8)] ──► Loss / 2 ──► Backward() ──► param.grad (unclipped partial)
                                                                    │ (accumulate)
                                                                    ▼
[Physical Batch 2 (B_phys=8)] ──► Loss / 2 ──► Backward() ──► param.grad (fully accumulated g_t^accum)
                                                                    │
                                                                    ▼
                                               torch.nn.utils.clip_grad_norm_(max_norm=1.0)
                                               ├─ Returns unclipped accumulated norm ||g_t^accum||_2
                                               ├─ Evaluates clipping indicator: I(||g_t^accum||_2 > 1.0)
                                               └─ Rescales param.grad in-place if ||g_t^accum||_2 > 1.0
                                                                    │
                                                                    ▼
                                                              optimizer.step()
                                                                    │
                                                                    ▼
                                                             optimizer.zero_grad()
```

- **Clipping Metric Definition:**
  - Raw unclipped accumulated gradient norm: $\|g_t^{\text{accum}}\|_2$ (captured directly as the float return value of `clip_grad_norm_`).
  - Clipping threshold: $\text{max\_norm} = 1.0$.
  - Clipping indicator: $\mathbb{I}(\|g_t^{\text{accum}}\|_2 > 1.0)$.
  - Clipped gradient: $g_t^{\text{clip}} = \min(1.0, 1.0 / \|g_t^{\text{accum}}\|_2) \cdot g_t^{\text{accum}}$.
- **Observed Parameter Displacement (`LL-DIAG05-PLAN-011`):**
  - Evaluated as $\|\theta_t - \theta_{t-1}\|_2$, where $\theta_{t-1}$ is captured immediately before `optimizer.step()` and $\theta_t$ immediately after `optimizer.step()`.
  - Constant learning rate $\eta = 2 \times 10^{-4}$ with scheduler disabled. Decoupled weight decay ($\lambda = 0.01$) is naturally integrated into parameter displacement.
  - Designated strictly as **"observed parameter displacement"**, NOT "gradient step size" or "raw optimizer force".

### 10.5 Paired Seed Design & Small-Sample ($n=3$) Inferential Discipline (`LL-DIAG05-PLAN-018`)
- **Paired Experimental Structure:**
  - Evaluates 3 paired seed replications (seeds 42, 101, 202) across 2 arms (Canonical vs Uniform).
  - Within each seed $s \in \{42, 101, 202\}$, Control ($W_{\text{canonical}}$) and Treatment ($W_{\text{uniform}}$) share the identical initialization weights $\theta_0$ and the identical sequence of Candidate F minibatch draws, varying *only* the loss weight vector $w$.
  - **Prohibition:** Prohibits describing Tier 2 as "6 independent runs." There are exactly 3 paired seed replications ($n=3$ pairs).
- **Small-Sample Inferential Limits:**
  - With $n=3$ pairs, statistical power to detect subtle or moderate differences is low; seed-to-seed variance can easily mask effects.
  - **Prohibition:** Prohibits concluding "no effect" or "reject weighting as an optimization bottleneck" based on a lack of statistically significant trajectory divergence.
  - **Allowable Interpretation:** If trajectories do not consistently diverge across seeds, conclude that *no detectable difference was observed under the 3-seed short-horizon protocol*; explicitly acknowledge that this protocol is powered only to detect gross divergence and cannot rule out moderate or longer-horizon effects.
- **Four Distinct Tier-2 Endpoints:**
  1. **Clipping Activation Frequency:** $\mathbb{I}(\|g_t^{\text{accum}}\|_2 > 1.0)$ at optimizer boundaries (tests gradient saturation).
  2. **Observed Parameter Displacement:** $\|\theta_t - \theta_{t-1}\|_2$ per optimizer step (tests actual displacement under AdamW second moments and weight decay).
  3. **Training Loss Trajectory:** $L(t)$ per optimizer step (tests objective convergence progress).
  4. **Validation Performance:** $\text{dev\_mIoU}_{\text{phenomena}}$ at epoch boundaries (tests generalization on rare and common phenomena).
  All four endpoints measure distinct physical stages and are non-redundant.

### 10.6 Three-Tier Statistical Unit Structure for H2 & Descriptive Census for H1 (`LL-DIAG05-PLAN-023`, `LL-DIAG05-PLAN-024`)
- **Three-Tier Statistical Unit Hierarchy for H2:**
  1. **Raw Descriptive Unit:** Cluster-pure physical Population-A tile observation ($B_{\text{phys}}=1$ or single-cluster minibatch $\le 4$ tiles). Raw observation-level cosine similarities are reported descriptively to characterize subgradient geometry distributions across all evaluated physical observations. Crucially, physical batches that mix tiles across multiple parent clusters are strictly prohibited from cluster-level inference (`LL-DIAG05-PLAN-024`), as they destroy cluster identifiability.
  2. **Primary Independence Unit:** Parent acquisition mission datatake cluster ($K=40$ in TRAIN, $K=12$ in DEV). In OPS-02 TRAIN, all 40 clusters contain between 2 and 4 tiles, and 17 clusters contain multiple tiles with dual-class support. Every raw observation belongs uniquely and unambiguously to exactly one parent acquisition cluster. Multiple observations originating from the same acquisition cluster are nested and non-independent; treating them as independent observations commits pseudo-replication.
  3. **Inferential Unit:** Paired parent-cluster median summary. Within each treatment arm (canonical vs uniform) and cluster $k$, observation-level cosine values are aggregated using the robust cluster median: $\bar{c}_{k} = \text{median}_{b \in \mathcal{B}_k}(\cos(g_{\text{rare}, b}, g_{\text{common}, b}))$.
- **Formal Paired Inference:**
  - Formal paired hypothesis testing (Wilcoxon signed-rank test) is performed on matched cluster-level paired median differences:
    $$\Delta \cos_k = \bar{c}_{k}^{\text{canonical}} - \bar{c}_{k}^{\text{uniform}}$$
  - **Implementation Specification:** Standardized execution via `scipy.stats.wilcoxon(diff, zero_method="wilcox", correction=True, method="asymptotic")`.
  - **Pairing Requirement:** Only parent clusters with valid dual-supported observations in *both* arms enter paired inference. Unmatched clusters are reported and excluded (`UNMATCHED_CLUSTER_EXCLUDED`). The exact count of independent paired clusters ($n_{\text{paired}}$) is documented.
  - **Parity Guarantee:** Canonical and uniform counterfactual H2 measurements evaluate the identical physical inputs $X, Y$ and identical initial weights $\theta_0$.
  - **Zero-Difference Handling ($\Delta \cos_k = 0$):** Zero differences are handled via standard Wilcoxon convention (`zero_method="wilcox"`), wherein $\Delta \cos_k = 0$ pairs are excluded from rank assignment. Crucially, zero differences are **NEVER silently dropped**: the execution schema explicitly records total paired clusters ($n_{\text{paired}}$), zero-difference cluster count ($n_{\text{zero}}$), and effective non-zero rankable pairs ($n_{\text{effective}} = n_{\text{paired}} - n_{\text{zero}}$) in the machine audit JSON (`data/ops02/audits/ops02_diag05_gradient_dynamics_v1.json`). If all differences are zero ($n_{\text{effective}} == 0$), the outcome is formally designated `ZERO_DIFFERENCE_ALL_PAIRS`.
  - **Tie Handling:** Ties in non-zero absolute differences $|\Delta \cos_k|$ receive average ranks. P-values are evaluated with continuity-corrected, tie-adjusted asymptotic normal distribution (`correction=True`, `method="asymptotic"`). Ad-hoc runtime switching between exact and asymptotic methods is strictly prohibited.
  - **Small-$n$ Inferential Discipline:** Minimum effective sample size condition: $n_{\text{effective}} \ge 10$. If $n_{\text{effective}} < 10$, formal inference is downgraded and designated `DESCRIPTIVE_ONLY_LOW_POWER`. Report paired effect direction, median paired difference, and effective sample size $n_{\text{effective}}$. Prohibit claiming absence of effect or rejecting H2 based on non-significance under small $n$.
- **Multiplicity Architecture:**
  - **Primary Confirmatory Comparison:** Global full-network paired cluster contrast $\cos(g_{\text{rare}}^{\text{global}}, g_{\text{common}}^{\text{global}})$.
  - **Secondary Descriptive Diagnostics:** The 10 stage-representative targets (`conv1`, `layer1..4`, `dec4..1`, `head`) are strictly secondary descriptive diagnostics reported without multiplicity inflation.
- **H1 Physical-Census Status:**
  - H1 evaluates the 132 TRAIN tiles (33 physical minibatches of $B_{\text{phys}}=4$) as an unconditional physical census across both canonical and uniform arms.
  - Primary robust dispersion is raw $\text{IQR}(\|g_{l,b}\|_2)$ within each arm; secondary comparisons include dispersion ratio $\frac{\text{IQR}_{\text{canonical}}}{\text{IQR}_{\text{uniform}}}$, log-ratio difference $\Delta \log_{10}(\text{IQR})$, and tail ratio contrast under strict categorical zero-denominator handling (`FINITE_RATIO`, `UNDEFINED_ZERO_DENOMINATOR`, `BOTH_IQR_ZERO`, `NONFINITE`).
  - H1 is strictly **descriptive physical-census profiling** at Step 0. Zero formal NHST hypothesis tests are registered for H1.

## 11. Performance Metric Contract

The primary evaluation metric remains strictly:
$$\mathbf{dev\_mIoU\_phenomena} = \frac{1}{11} \sum_{c=1}^{11} \text{IoU}_c$$
evaluated across the 11 non-background classes on the canonical 40 OPS-02 DEV tiles (`LL-EXP07-002`).

### Secondary Supporting Metrics:
- **`dev_mIoU_all`**: Macro mean IoU across all 12 classes (including Background).
- **Per-Class IoU**: Individual IoU for each of the 12 classes, with special focus on rare classes (HM, OF, RF).
- **Log-Norm Ratio ($\Lambda_l$)**: $\log_{10} \|\nabla_{\theta_l} \mathcal{L}_{\text{canonical}}\|_2 - \log_{10} \|\nabla_{\theta_l} \mathcal{L}_{\text{uniform}}\|_2$.
- **Within-Batch Cosine Distribution**: Continuous distribution and descriptive binned frequencies across layers.

---

## 12. Exhaustive 23-Threat Failure Mode Analysis (A through W)

| ID | Failure Mode / Threat | Prevention Control | Detection Routine | Stop Condition |
| :---: | :--- | :--- | :--- | :--- |
| **A** | **Dataset leakage** | Hard partition filter restricting training batches strictly to TRAIN tile IDs. | Cross-reference batch tile IDs against `ops02_physical_dataset_manifest_v1.json`. | Abort if non-TRAIN tile ID appears in training batch generator. |
| **B** | **Seed leakage / RNG reuse** | Isolated `torch.Generator()` instances for model initialization, data shuffling, and sampler draws. | Audit seed registry in execution state JSON. | Abort if RNG state is shared across modules. |
| **C** | **Checkpoint leakage** | Verify initial checkpoint SHA-256 digest before loading weights. | Programmatic hash check against baseline freeze. | Abort if checkpoint hash differs by a single bit. |
| **D** | **HOLDOUT contamination** | Filesystem path interception and firewall wrapper asserting 0 accesses to `holdout`. | Runtime access counter in preflight and postrun gates. | Immediate hard abort with `BLOCK-001-HOLDOUT`. |
| **E** | **Part III contamination** | Strict path firewall prohibiting access to `phase_6_part_iii_external_evaluation`. | Filesystem descriptor audit. | Immediate hard abort with `BLOCK-002-PART_III`. |
| **F** | **Parent pseudoreplication** | Aggregate gradient metrics at parent cluster level ($K$), applying cluster-level paired inference (`LL-DIAG05-PLAN-023`). | Verify datatake cluster ID tagging on all batch items. | Abort if p-values derive from unclustered pixel counts or unclustered raw physical batch counts without parent-cluster aggregation (`LL-DIAG05-PLAN-023`, `BLOCK-009`). |
| **G** | **Selection bias** | Deterministic dual-supported batch generation covering all rare-class occurrences in OPS-02 TRAIN. | Verify full support coverage against ground truth manifest. | Abort if candidate batches are discarded post-hoc. |
| **H** | **Hyperparameter cherry-picking** | Freeze AdamW parameters ($\text{lr}=10^{-4}, \beta=(0.9, 0.999), \text{decay}=10^{-4}$) to baseline spec. | Assert config JSON match prior to run. | Abort if any optimizer parameter deviates from freeze. |
| **I** | **Post-hoc endpoint selection** | Pre-register exact 9 layer targets and global norm in plan JSON. | Schema validation asserting all pre-registered endpoints are reported. | Abort if un-registered endpoints replace primary metrics. |
| **J** | **Multiple comparisons** | Apply Benjamini-Hochberg FDR ($q=0.05$) across layer-wise exploratory analyses. | Audit statistical analysis code for multiplicity correction. | Flag uncorrected p-values as strictly exploratory. |
| **K** | **Regression to the mean** | Evaluate stationary gradient distributions over multiple batches, not single-step spikes. | Quantile dispersion analysis across iteration windows. | Prohibit mechanistic claims from transient single steps. |
| **L** | **Random-seed variability** | Pre-specify multi-seed replication ($n=3$: seeds 42, 101, 202) and report inter-seed CIs. | Verify multi-seed variance computation in audit JSON. | Mark `INCONCLUSIVE_SEED_SENSITIVE` if seed variance > effect size. |
| **M** | **Optimization instability (NaNs)** | Layer-by-layer gradient norm monitoring at every step. | Automated assertion `torch.isfinite(grad).all()`. | Immediate halt if any NaN or Inf is encountered. |
| **N** | **Gradient clipping confounding** | Measure unclipped gradient norms *before* any clipping operation. | Assert gradient measurement hook precedes `clip_grad_norm_()`. | Abort if gradient norms are measured only post-clipping. |
| **O** | **BatchNorm statistics confounding** | Set `model.eval()` during Tier 1 static profiling to freeze running mean/variance. | Assert `model.training is False` during static profiling. | Abort if BN running statistics mutate during static profiling. |
| **P** | **LR / Scheduler confounding** | Disable scheduler (constant LR) during Tier 2 dynamic 5-epoch training. | Assert constant LR in step logs. | Abort if scheduler steps occur during static profiling. |
| **Q** | **Class-balance confounding** | Normalize cross-entropy loss by valid pixel count (`reduction="mean"` on valid mask). | Log valid pixel count per batch alongside gradient norms. | Abort if unnormalized loss sums are compared. |
| **R** | **Checkpoint selection confounding** | Pre-register exact checkpoint: Step 0 canonical initialization only (`data/ops02/initial_model_state_canonical.pt`). Tier 1 measures Step 0 initialization geometry only; post-adaptation dynamics are investigated strictly through Tier 2 controlled training. | Record checkpoint step and SHA in telemetry. | Prohibit introducing fictional intermediate checkpoints in Tier 1 static profiling. |
| **S** | **Metric denominator effects** | Enforce $\tau_{\text{floor}} = 10^{-7}$ and log-ratio $\Lambda_l$; flag zero denominators. | Assert floor threshold prior to division; log zero-denominator flags. | Exclude degenerate zero-denominator cases from ratio aggregations. |
| **T** | **Causal overclaiming** | Strict linguistic enforcement (`BLOCK-004`): claims graded as `OBSERVED` or `SUPPORTED`. | Automated regex scan for uncalibrated causal verbs. | Abort report generation if uncalibrated causal verbs appear. |
| **U** | **Narrative/report contradiction** | Narrative text generation binds directly to machine JSON values (`GOV-RULE-100`). | Automated test asserting bitwise agreement between report and JSON. | Test failure if narrative and JSON numbers diverge. |
| **V** | **Provenance drift** | Verify canonical OPS-02 manifest path and SHA-256 digest (`F5480EA2...`). | Preflight manifest hash verification. | Fail closed immediately if manifest path or hash deviates. |
| **W** | **Runaway compute** | Hard caps: max 200 backward passes (Tier 1: deterministic requirement 178 passes = 66 H1 + 112 H2, with 22-pass contingency buffer, `LL-DIAG05-PLAN-025`), max 6 runs / 5 epochs (Tier 2). | Wall-clock watchdog timer with automated subprocess termination. | Immediate abort if runtime exceeds 15 min CPU / 60 min GPU. |

---

## 13. Brute Force vs Smart Workaround Decisions

| Investigation Dimension | Strategy Chosen | Rationale & Scientific Justification |
| :--- | :--- | :--- |
| **Initial Gradient Geometry** | **Smart Workaround** (Tier 1 Static Profiling) | Evaluating gradients on frozen checkpoints resolves within-batch directional alignment in $< 2\text{ minutes}$ on CPU/GPU without spending hours training models. |
| **Causal Weight Intervention** | **Brute Force** (Within-Batch Counterfactuals) | True counterfactual isolation requires strictly identical physical minibatches across rare and common masks; comparing different batches is scientifically invalid. |
| **Replication Strategy** | **Brute Force** ($n=3$ Independent Seeds) | Multi-seed replication is mandatory to prevent repeating the C22-D error of over-interpreting single-seed variance. |
| **Trajectory Duration** | **Smart Workaround** (Short 5-Epoch Horizon) | Restricting interventional training to 5 epochs captures initial optimization divergence while saving 75% of GPU compute relative to a 20-epoch run. |
| **Statistical Inference** | **Brute Force** (Parent-Cluster Bootstrap) | Preserving datatake-level clustering ($K=52$) is mathematically non-negotiable to prevent pseudoreplication. |

---

## 14. Compute Budget & Resource Allocations

```yaml
compute_budget_specification:
  tier_1_static_profiling:
    target_hardware: "CPU or local GPU"
    max_wallclock_seconds: 180.0  # 3 minutes
    backward_passes_limit: 120
    optimizer_steps_limit: 0
    parameter_updates_limit: 0
    checkpoint_evaluations: 1  # Step 0 Canonical Init (SHA256: 67181C4E...)
    memory_peak_mb: 2048
    disk_output_mb: 15

  tier_2_dynamic_intervention:
    target_hardware: "NVIDIA GPU (CUDA)"
    max_wallclock_minutes: 60.0  # 1 hour maximum
    number_of_arms: 2  # Control (Canonical), Treatment (Uniform)
    seeds: [42, 101, 202]
    total_runs: 6
    epochs_per_run: 5
    batch_geometry:
      physical_batch_size: 8
      gradient_accumulation_steps: 2
      effective_optimizer_batch_size: 16
      batchnorm_statistical_batch_size: 8
    step_arithmetic_options:
      candidate_f_sampler_parity_primary:
        description: "Exact parity with canonical INV-16 training (72 draws/epoch with replacement)"
        batches_per_epoch: 9  # 72 draws / physical batch 8
        partial_batches_per_epoch: 0
        optimizer_steps_per_epoch: 5  # 4 pairs of 16 + 1 step on batch 8
        optimizer_steps_per_run: 25  # 5 epochs * 5 steps
        total_optimizer_steps_6_runs: 150  # 6 runs * 25 steps
        total_physical_forward_backward_passes: 270  # 6 runs * 5 epochs * 9 batches
      full_dataset_traversal_alternative:
        description: "Sequential unweighted pass over all 132 physical TRAIN tiles"
        batches_per_epoch: 17  # 132 TRAIN tiles / physical batch 8 (16 full + 1 partial of 4)
        partial_batches_per_epoch: 1  # Batch 16 has size 4
        optimizer_steps_per_epoch: 9  # 16 / 2 + 1 partial step
        optimizer_steps_per_run: 45  # 5 epochs * 9 steps
        total_optimizer_steps_6_runs: 270  # 6 runs * 45 steps
        total_physical_forward_backward_passes: 510  # 6 runs * 5 epochs * 17 batches
    checkpoint_retention: 6  # Final epoch 5 checkpoint per run
    memory_peak_mb: 6144
    disk_output_mb: 400

  early_stopping_criteria:
    nan_or_inf_detected: "IMMEDIATE_TERMINATION"
    divergent_loss_threshold: 10.0
    exploding_gradient_norm_threshold: 10000.0
```

---

## 15. Reproducibility & Governance Contract

```yaml
reproducibility_contract:
  execution_scripts:
    tier_1_static: "scripts/execute_exp07_diag05_tier1.py"
    tier_2_dynamic: "scripts/execute_exp07_diag05_controlled_intervention.py"
  python_environment: ".venv (Python 3.10.9)"
  authoritative_dataset: "OPS-02 (OPS02_v1.0.1_FROZEN)"
  manifest_sha256: "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"
  canonical_initial_checkpoint:
    path: "data/ops02/initial_model_state_canonical.pt"
    sha256: "67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D"
  random_seeds:
    primary: 42
    replications: [101, 202]
  output_artifacts:
    machine_audit_json: "data/ops02/audits/ops02_diag05_gradient_dynamics_v1.json"
    narrative_report: "experiments/EXP-07/EXP07_P0_DIAG05_GRADIENT_DYNAMICS_20260915.md"
    run_state_telemetry: "scratch/diag05_execution_run_state.json"
  governance_assertions:
    zero_holdout_access: true
    zero_part_iii_access: true
    zero_destructive_git: true
    verified_preflight_receipt_required: true
```

---

## 16. Calibrated Contingency Matrix

| Scenario | Trigger Condition | Operational & Analytical Response | Stop Condition | Scientific Consequence |
| :---: | :--- | :--- | :--- | :--- |
| **1. Extreme Gradient Norm** | Any layer gradient norm $\|\nabla_{\theta_l} \mathcal{L}\|_2 > 10^4$ or `Inf`. | Log offending batch, tile IDs, and class presence; abort run. | Immediate run abort. | Observed numerical event demonstrating extreme gradient magnitude under the tested batch and weight condition; prompts operational halt to prevent corrupted updates, but does not prove a universal instability mechanism. |
| **2. Near-Zero Gradient Norm** | Rare-class gradient norm $\|\nabla_\theta \mathcal{L}_{\text{rare}}\|_2 < 10^{-8}$. | Log layer-wise norm profile; flag vanishing layers. | Do not abort static profiling. | Direct descriptive observation supporting gradient magnitude attenuation. |
| **3. Negative Alignment Dominance** | Median within-batch $\cos(g_{\text{rare}}, g_{\text{common}}) < -0.3$ across $\ge 50\%$ of layers. | Confirm vector alignment; compute cluster bootstrap CI. | Do not abort. | Provides descriptive evidence of within-batch gradient opposition. |
| **4. Orthogonal Alignment** | $-0.1 \le \text{Median}(\cos) \le 0.1$ across all layers. | Evaluate log-norm ratio $\Lambda_l$; test if dominant gradients merely drown rare gradients. | Do not abort. | Disproves active antagonism; supports gradient magnitude imbalance. |
| **5. High Seed Sensitivity** | Inter-seed variance in median cosine $> 0.4$. | Report seed-specific distributions; declare inconclusive if treatment effect is masked. | Do not abort. | Finding declared `INCONCLUSIVE_SEED_SENSITIVE`. |
| **6. Checkpoint Divergence** | Step 0 init shows negative alignment, but later checkpoint shows alignment (or vice versa). | Report both checkpoints separately; contrast initialization vs adapted dynamics. | Do not abort. | Distinguishes transient initialization geometry from adapted dynamics. |
| **7. Treatment Fails to Alter Trajectory** | Uniform weighting stabilizes gradients but 5-epoch `dev_mIoU_phenomena` remains $\approx 0.049$. | Record finding; evaluate per-class IoU trade-offs (e.g. BG vs rare classes). | Do not abort. | Decouples short-horizon gradient stability from representation learning capacity. |
| **8. Memory OOM during Backward** | CUDA out of memory during backward pass on batch size 4. | Reduce profiling batch size to $B=2$ with gradient accumulation ($2\times$). | Do not abort if $B=2$ succeeds. | Profiling proceeds with identical mathematical gradient. |
| **9. Accidental Optimizer Step in Tier 1** | Parameter hash changes during Tier 1 static profiling. | Immediate script termination; discard results. | Immediate hard abort. | Invalidates diagnostic profiling due to state corruption. |
| **10. Manifest Hash Mismatch** | Manifest SHA differs from `F5480EA2...`. | Halt immediately; fail closed. | Immediate hard abort. | Prevents execution on wrong dataset. |
| **11. HOLDOUT Access Attempt** | File descriptor opened in `holdout/`. | Firewall intercepts and raises `PermissionError`. | Immediate hard abort (`BLOCK-001`). | Quarantines HOLDOUT unconditionally. |
| **12. GPU Timeout** | Dynamic training exceeds 60 minutes. | Watchdog timer terminates process; saves partial epoch logs. | Immediate termination. | Protects compute budget from runaway processes. |

---

## 17. Historical Lessons Applied & New Lessons Formulated

### 17.1 Applicable Historical Lessons
- `LL-EXP07-001`: Quantitative assertions must derive directly from machine JSON (`GOV-RULE-100`).
- `LL-EXP07-002` / `LL-C22B-004`: Dense taxonomy nomenclature frozen (`HM`, `OF`).
- `LL-EXP07-007`: Standard PyTorch tensor notation `[B, 1, 256, 256]` and $256 \times 256$ grid geometry.
- `LL-EXP07-008` / `LL-DIAG03-006`: Non-causal observational language on descriptive data (`BLOCK-004`).
- `LL-EXP07-010`: Historical baseline performance verified against machine records (mIoU $\approx 0.049$).
- `LL-C22I-001`: Samplers must not silently fall back on missing manifest keys.
- `LL-C22I-002`: Empirical audit must precede speculative training-starvation claims.
- `LL-C22J-001` (`CRITICAL`): Sampler exposure is not direct evidence of gradient dynamics; gradient dynamics require direct measurement.
- `LL-C22J-002`: Small-sample ($n=5$) correlations are descriptive associations, not causal proof.
- `LL-C22J-004`: Diagnostic roadmap integrity requires unique IDs; DIAG-05 isolated as DESIGN ONLY.
- `LL-DIAG04-PLAN-002`: Zero backward passes in standard diagnostics; requires formal protocol amendment for gradient studies.
- `LL-DIAG04-PLAN-003`: Diagnostic dataset continuity across roadmap investigations (OPS-02 canonicality locked).
- `LL-DIAG05-PLAN-001`: Gradient diagnostics require explicit protocol separation from zero-backward diagnostic rules.

### 17.2 Newly Discovered Recurring Patterns Formulated in DIAG-05
- **`LL-DIAG05-PLAN-002` (Scientific Validity / Causal Identification):**
  *Gradient Conflict Claims Require Within-Batch Counterfactual Masking, Not Merely Differently Composed Minibatches.*
  Evaluating cross-class gradient direction conflict across separate minibatches conflates imagery and environmental differences with loss dynamics. Mandates Within-Batch Counterfactual Masking on the identical physical minibatch $B$.
- **`LL-DIAG05-PLAN-003` (Scientific Validity / Statistical Design):**
  *Conditioning Gradient Conflict Analysis on Dual-Support Minibatches Creates Ascertainment Bias Requiring Dual-Population Reporting.*
  Selecting only minibatches with co-occurring rare and common classes conditions the estimand on co-occurrence (~11-12 minibatches in OPS-02 TRAIN). Mandates dual-population reporting: (1) conditioned co-occurrence interaction with explicit exclusion accounting, and (2) unconditional population-wide gradient norm profile across all 33 minibatches.
- **`LL-DIAG05-PLAN-004` (Scientific Validity / Documentation Integrity):**
  *First-Order Gradient Dynamics Must Not Be Claimed as Loss-Landscape Curvature Without Hessian or Second-Order Measurement.*
  Gradient norms and cosine similarities measure directional slopes and alignment, not curvature, Hessians, or landscape sharpness. Restricts all DIAG-05 scientific prose to First-Order Gradient Dynamics.
- **`LL-DIAG05-PLAN-005` (Data Integrity / Provenance):**
  *Loss Weight Vectors Must Be Programmatically Bound to Frozen Canonical Artifacts, Not Reconstructed from Memory or Normalized Ad-Hoc.*
  Prevents introduction of ungrounded loss weights by asserting exact equality against `CANONICAL_HISTORICAL_C16_LITERALS` (`[0.403935 ... 18.243211]`).
- **`LL-DIAG05-PLAN-006` (Scientific Validity / Numerical Analysis):**
  *Floating-Point Machine Epsilon Is a Relative Unit Roundoff, Not an Absolute Lower Bound on Gradient Magnitude or Noise Floor.*
  Clarifies float32 precision: normal numbers extend to $1.18 \times 10^{-38}$. Threshold $\tau_{\text{reg}} = 10^{-7}$ is an arbitrary regularizer for ratio plotting, not a physical noise limit.
- **`LL-DIAG05-PLAN-007` (Scientific Validity / Mask Semantics):**
  *Absent Mask Support in a Batch Represents an Ineligible Condition, Not a Zero-Gradient Observation.*
  Prevents silent zero substitution by flagging zero-mask batches as `INELIGIBLE_ABSENT_MASK`, skipping backward passes, and excluding them from continuous gradient norm distributions.
- **`LL-DIAG05-PLAN-008` (Documentation Integrity / Architecture):**
  *Global Parameter Gradient Aggregation Must Be Distinguished from Architectural Submodule Targets.*
  Strictly separates the 10 named PyTorch submodules from the 14,310,860-parameter concatenated global gradient vector. Mandates RMS normalization for cross-layer norm comparisons.
- **`LL-DIAG05-PLAN-009` (Scientific Validity / Training Dynamics):**
  *Training Step Arithmetic Must Reconcile Batch Size, Sampler Draws, Accumulation, and Partial Batches.*
  Explicitly disambiguates step arithmetic between Candidate F sampler schedule (72 draws, 9 batches, 5 steps) and full dataset traversal (132 tiles, 17 batches with 1 partial of 4, 9 steps).
- **`LL-DIAG05-PLAN-010` (Scientific Validity / Subgradient Decomposition):**
  *Masked Subset Gradient Contribution Under Full-Batch Reduction Denominator Is Not Equivalent to an Independently Normalized Subset Loss Gradient.*
  Mandates using the full-batch reduction denominator $D_{\text{batch}} = \sum_{i \in B_{\text{valid}}} w_{y_i}$ to preserve exact linear subgradient decomposition ($g_{\text{rare}} + g_{\text{common}} + g_{\text{other}} = g_{\text{total}}$) and prevent single-class weight cancellation ($w_c / \bar{w}_{\text{batch}}$).
- **`LL-DIAG05-PLAN-011` (Scientific Validity / Optimizer Dynamics):**
  *AdamW Parameter Update Magnitude Is Governed by Adaptive Moments and Decoupled Weight Decay, Not Directly by Raw Gradient L2 Norm.*
  Distinguishes raw gradient $L_2$ norm, clipped gradient norm, AdamW preconditioned update, and observed parameter displacement. Prohibits claiming raw gradient $L_2$ directly governs AdamW parameter update magnitude; raw $L_2$ determines global gradient clipping activation (threshold $\text{max\_norm}=1.0$).
- **`LL-DIAG05-PLAN-012` (Scientific Validity / Directional Alignment):**
  *Negative Gradient Cosine Similarity Denotes Opposing Instantaneous Directional Geometry and Does Not Prove Destructive Interference or Optimization Failure Without Paired Intervention.*
  Enforces strictly "opposing gradient direction" for $\cos < 0$. Prohibits causal claims of "destructive interference", "harmful conflict", or "optimization failure" without paired dynamic trajectory evidence from Tier 2.
- **`LL-DIAG05-PLAN-013` (Scientific Validity / Sampling Population):**
  *Deterministic Full-Dataset Traversal Represents a Physical Census and Must Not Be Conflated with the Stochastic Candidate F Sampling Distribution.*
  Designates Population B as an unconditional full-dataset physical census across all 132 TRAIN physical tiles ($B_{\text{phys}}=4$), distinguishing it from the Candidate F dynamic class-conditioned sampler.
- **`LL-DIAG05-PLAN-014` (Scientific Validity / Resultant Vectors):**
  *Aggregate Class Subset Gradients Are Resultant Vectors Subject to Internal Multi-Class Cancellation and Cannot Be Interpreted as Uniform Individual Class Directions.*
  Acknowledges that $g_{\text{common}}$ (7 classes) and $g_{\text{rare}}$ (3 classes) are aggregate resultant vectors subject to internal multi-class cancellation. Framing of cosine similarity is strictly rare-vs-aggregate-common resultant directional alignment.
- **`LL-DIAG05-PLAN-015` (Reproducibility / Floating-Point Determinism):**
  *Deterministic Numerical Reproducibility Within a Single Environment Does Not Guarantee Bitwise Identity Across Heterogeneous Hardware or Software Stacks.*
  Separates mathematical equivalence, single-environment deterministic reproducibility, and cross-platform bitwise identity. Single-environment determinism is the operational guarantee; universal bitwise identity is not claimed.
- **`LL-DIAG05-PLAN-016` (Scientific Validity / Dimensional Scaling):**
  *Raw L2 Norm and RMS Per-Parameter Scale Serve Distinct Roles and Must Not Be Conflated When Comparing Modules of Different Parameter Counts.*
  Restricts raw $L_2$ norm to within-layer physical magnitude and global clipping triggers, while assigning RMS norm to cross-layer depth comparisons. Prohibits asserting either metric alone captures all dimensions of gradient scale.
- **`LL-DIAG05-PLAN-017` (Scientific Validity / Implementation Integrity):**
  *Gradient Clipping Activation Must Be Evaluated at the Optimizer Accumulation Boundary on Accumulated Gradients, Not on Unaccumulated Per-Physical-Batch Gradients.*
  Mandates capturing the unclipped accumulated norm $\|g_t^{\text{accum}}\|_2$ and clipping indicator $\mathbb{I}(\|g_t^{\text{accum}}\|_2 > 1.0)$ exclusively at the accumulation boundary immediately prior to `optimizer.step()`, mirroring exact training execution in `scripts/train_exp07.py`.
- **`LL-DIAG05-PLAN-018` (Scientific Validity / Statistical Design):**
  *Small-Sample (n=3) Non-Significant Differences Must Not Be Interpreted as Proof of No Effect or Grounds to Reject an Optimization Bottleneck.*
  Prohibits claiming that non-significance under $n=3$ paired seeds proves absence of effect or justifies rejecting a hypothesis. Requires reporting observed effect direction, estimated effect size, and uncertainty, acknowledging that $n=3$ cannot rule out moderate or longer-horizon effects.
- **`LL-DIAG05-PLAN-019` (Scientific Validity / Numerical Analysis):**
  *Dispersion Ratios with Potentially Vanishing Denominators Require Categorical Censoring Rather Than Artificial Epsilon Regularizers.*
  Pre-registers categorical handling for zero and non-finite dispersion denominators (`FINITE_RATIO`, `UNDEFINED_ZERO_DENOMINATOR`, `BOTH_IQR_ZERO`, `NONFINITE`) and prohibits adding ad-hoc regularizers to gradient norm denominators.
- **`LL-DIAG05-PLAN-020` (Scientific Validity / Training Dynamics):**
  *Step 0 Cross-Batch Gradient Dispersion Represents Spatial Dataset Heterogeneity at Initialization and Must Not Be Claimed as Temporal Training Volatility.*
  Restricts H1 gradient dispersion interpretation strictly to spatial cross-batch heterogeneity across physical dataset scenes at Step 0, prohibiting claims of iteration-to-iteration training volatility or trajectory instability.
- **`LL-DIAG05-PLAN-021` (Scientific Validity / Directional Alignment):**
  *Within-Batch Cosine Similarity Cancels the Common Scalar Reduction Denominator Identically and Is Altered Across Weighting Arms Strictly by Numerator Vector Reweighting.*
  Proves that shared positive scalar denominator $D_{\text{batch}}$ cancels identically from cosine similarity, establishing that loss weighting shifts cosine alignment exclusively through numerator constituent class reweighting.
- **`LL-DIAG05-PLAN-022` (Scientific Validity / Terminology & Scope Discipline):**
  *Accumulated Gradient Terminology Must Be Reserved for Optimizer Accumulation Boundaries and Excluded from Step 0 Physical Census Profiling.*
  Mandates designating Tier 1 gradient metrics strictly as "within-batch unclipped gradient norm" $g_b(\theta_0)$ and "within-batch masked gradient contributions", reserving "accumulated" for Tier 2 optimizer boundaries ($A=2$, $B_{\text{eff}}=16$). Bounds H3 causal language to "supports a causal effect of the loss-weighting intervention on short-horizon optimization behavior under this protocol" with separately interpretable endpoints, prohibiting mechanistic claims of "causal driver of instability".
- **`LL-DIAG05-PLAN-023` (Scientific Validity / Cluster Independence & Inference Units):**
  *Paired Inference on Within-Batch Subgradient Geometry Must Aggregate to Parent Acquisition Clusters to Prevent Batch-Level Pseudo-Replication.*
  Mandates a three-tier statistical unit structure for H2: (1) Raw descriptive unit: physical Population-A tile observation; (2) Primary independence unit: parent acquisition mission datatake cluster ($K=40$ in TRAIN); (3) Inferential unit: paired parent-cluster median summary. Requires paired Wilcoxon tests to evaluate cluster-level paired median differences ($\Delta \cos_k$) rather than raw batches, excludes unmatched clusters (`UNMATCHED_CLUSTER_EXCLUDED`), designates the global full-network contrast as primary confirmatory inference, and treats stage-representative layers as secondary descriptive diagnostics.
- **`LL-DIAG05-PLAN-024` (Scientific Validity / Batch-to-Cluster Identifiability):**
  *Raw Physical Observations for Cluster-Level Paired Inference Must Be Cluster-Pure to Prevent Non-Identifiable Multi-Cluster Batch Mixing.*
  An exhaustive audit of OPS-02 TRAIN revealed all 40 parent clusters have $\le 4$ tiles (max 4), meaning 100% of 8-tile batches mix multiple clusters, destroying cluster identifiability. H2 raw observations are redefined as cluster-pure physical observations ($B_{\text{phys}}=1$ or cluster-pure batch $\le 4$ tiles from that single cluster), guaranteeing an exact, unambiguous 1-to-1 mapping to parent acquisition clusters. Prohibits arbitrary assignment rules, dominant-cluster shortcuts, or batch splitting.
- **`LL-DIAG05-PLAN-025` (Scientific Validity / Compute Budget Reconciliation):**
  *Execution Authorization Compute Ceilings Must Be Mathematically Reconciled with Deterministic Scientific Population Requirements to Prevent Population Truncation or Execution Failure.*
  In DIAG-05, expanding from the exploratory 2-class common subset (16 tiles across 12 clusters) to the authoritative Primary Common-7 grouping (28 tiles across 15 clusters) under cluster-pure observations ($B_{\text{phys}}=1$, `LL-DIAG05-PLAN-024`) deterministically requires 112 H2 backward passes (28 tiles $\times$ 4 passes: rare and common gradients across Control and Treatment arms; four backward passes are the registered execution implementation because the required masked gradient vectors are obtained through independent forward/backward evaluations without retained computation graphs; this avoids the memory and graph-lifetime risks of graph reuse). Adding the 66 H1 census passes (33 batches of $B_{\text{phys}}=4 \times 2$ arms) yields exactly 178 deterministic backward passes. The authorization ceiling is reconciled to max 200 backward passes (providing 22 passes contingency headroom), eliminating the operational contradiction of the obsolete 120 ceiling and strictly prohibiting arbitrary subsampling or population truncation.

---

## 18. Pre-Execution Test Plan

Before DIAG-05 execution can be authorized, the following automated regression and invariant tests must be executed:

```bash
# 1. Governance preflight verification
.venv\Scripts\python scripts/agent_governance_preflight.py --task-type diagnostic
.venv\Scripts\python scripts/agent_governance_preflight.py --verify-receipt --task-type diagnostic

# 2. Dataset contract and manifest hash verification
.venv\Scripts\pytest -v tests/test_ocean_sentinel_agent_governance.py::test_canonical_roadmap_integrity
.venv\Scripts\pytest -v tests/test_ocean_sentinel_agent_governance.py::test_dataset_freeze_spec_integrity

# 3. Quarantined partition firewalls
.venv\Scripts\pytest -v tests/test_part_iii_firewall.py
.venv\Scripts\pytest -v tests/test_ocean_sentinel_agent_governance.py::test_preflight_blocks_holdout_access

# 4. DIAG-05 planning guardrails
.venv\Scripts\pytest -v tests/test_exp07_p0_diag05_preexecution_guardrails.py
```

---

## 19. Final Readiness Verdict

### **`PLAN_READY_WITH_PREREQUISITES`**

**Prerequisites Summary:**
1. Authorize a formal governance protocol amendment permitting Tier 1 Static Checkpoint Gradient Profiling (deterministic requirement: 178 backward passes = 66 H1 + 112 H2; hard ceiling: `backward_passes <= 200`, `optimizer_steps == 0`, `parameter_updates == 0`).
2. Verify that GPU/CPU resources are available and preflight receipt is authentic.
3. Explicit user execution authorization granted for DIAG-05.

> [!IMPORTANT]
> **DIAG-05 SCIENTIFIC EXECUTION HAS NOT OCCURRED.**  
> **DIAG-05 EXECUTION AUTHORIZATION: NOT GRANTED.**  
> This plan is hardened, mathematically specified, and protected by governance. Execution remains blocked until explicit user authorization and prerequisite protocol amendments are issued.
