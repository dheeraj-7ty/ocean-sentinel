# Ocean Sentinel — Phase 7: Post-Evaluation Failure Analysis & Development Protocol Design

**Document Identifier:** `PHASE_7_POST_EVALUATION_FAILURE_ANALYSIS_20260912`  
**Role:** Senior CAO Scientific Systems Architect / Experimental Design Auditor  
**Preceding Evaluation:** Trujillo Part III External Benchmark Evaluation (Phase 6, Frozen)  
**Status:** **`POST_EVALUATION_DIAGNOSTIC_COMPLETE`**  
**Immediate Operational Authorization:** **`DATA_AND_PROTOCOL_DESIGN_ONLY (NO EXP-07 TRAINING)`**  

---

## 1. Executive Summary & Permanent Phase 6 Freeze

The Phase 6 external evaluation of the frozen Ocean Sentinel `EXP-06` development checkpoint on the untouched Trujillo Part III benchmark is complete and frozen (`PHASE_6_PART_III_EXTERNAL_EVALUATION_REPORT_20260912`).

### 1.1 What Phase 6 Proved
1. **Strong Oil-Stratum Slick Segmentation Generalization:** Under canonical channel alignment (Mapping A), `EXP-06` achieved **`0.74486` Oil-stratum macro mean IoU** ($72.49\%$ micro-pooled), **`0.84070` macro Dice**, and **`0.89086` Recall** across 150 external scenes containing true oil slicks.
2. **Operational Stability on Clean Water:** Over 150 scenes of open clean ocean water, the model achieved a **`95.33%` clean scene rejection rate** (Primary Scene FAR $4.67\%$, $7/150$ scenes with false positives, median $0.0\text{ px}$), yielding a clean-water pixel specificity of **`99.985%`** ($95,157\text{ FP pixels}$ out of $629,145,600\text{ px}$).
3. **Severe Vulnerability to Natural Lookalikes:** Over 150 scenes containing natural low-backscatter dark ocean formations (biogenic films, low-wind shadows, internal waves, upwelling), Mapping A generated a Primary Scene FAR of **`90.67%`** ($136/150$ scenes) and $130,502,095\text{ FP pixels}$ ($20.74\%$ of the stratum surface area), yielding an overall whole-benchmark global pixel IoU of **`25.21%`**.
4. **Channel-Ordering Data-Contract Sensitivity:** Inverting channel ordering (Mapping B) caused catastrophic performance degradation across all strata (Oil macro IoU $9.17\%$, clean-water FAR $92.00\%$, lookalike FAR $98.00\%$).

### 1.2 What Phase 6 Did NOT Prove
- It did **not** prove universal operational or deployment readiness.
- It did **not** establish causal superiority of channel ordering over alternative sensor physical configurations.
- It did **not** establish that single-pass 2D SAR is fundamentally incapable of lookalike discrimination.
- It did **not** test multi-temporal SAR coherence or auxiliary meteorological features.

### 1.3 Absolute External-Benchmark Quarantine (Rule 38)
> [!IMPORTANT]
> **Rule 38 Firewall:** Trujillo Part III is now permanently retired as a blind external benchmark. All 450 scenes, raw GeoTIFFs, masks, and Phase 6 prediction outputs are strictly quarantined. **Under no circumstances may any Part III sample or metric be used to train models, select training candidates, tune decision thresholds, adjust loss weights, or choose model architectures.** All Phase 7 development must occur against leakage-safe internal development data.

---

## 2. Exhaustive Failure Taxonomy

Synthesizing all forensic evidence from EXP-01 through EXP-06 and the Phase 6 benchmark results, we establish the following 17-class failure taxonomy:

| Code | Failure Mechanism Class | Empirical Classification | Evidentiary Basis & Forensic Characterization |
|:---:|---|:---:|---|
| **A** | **Small / Low-Mass Oil Objects** | **OBSERVED** | Phase 5G forensics proved complete tile dropouts are concentrated in small slicks ($< 2,712\text{ px}$, $19.1\%$ of FN mass). EXP-06 recovered 29 tiles, but small-slick dropout remains the primary source of zero-recall tiles. |
| **B** | **Low-Contrast Oil Slicks** | **STRONGLY SUPPORTED** | Slicks with low damping contrast ($\Delta \sigma_0 < 3\text{ dB}$ vs background clutter) fail to cross the activation threshold ($p < 0.10$). Slicks in transition zones ($0.10 \le p \le 0.35$) are rare; probabilities are bimodal. |
| **C** | **Fragmented / Elongated Slicks** | **OBSERVED** | Boundary erosion and diffuse margin truncation account for $80.9\%$ of all FN pixel mass ($2.57\text{M px}$ in EXP-06). Multi-stage pooling in ResNet-34 erodes fine filaments and narrow tails. |
| **D** | **Background Texture False Positives** | **OBSERVED (MITIGATED)** | High-frequency clutter caused $20.09\%$ Clean FAR in EXP-01. Hard-negative mining in EXP-03 to EXP-06 mitigated this by $97.3\%$ (down to $0.55\%$ internal Clean FAR). |
| **E** | **Clean-Water False Positives** | **OBSERVED (CONTROLLED)** | Clean open water false alarms were verified at $4.67\%$ Primary Scene FAR ($99.985\%$ pixel specificity) in Phase 6 Mapping A. Baseline ocean water is well-controlled. |
| **F** | **Lookalike Dark Formation False Positives** | **OBSERVED (CRITICAL)** | Primary Scene FAR of $90.67\%$ ($136/150$ scenes, $130.5\text{M FP px}$) on Part III lookalikes. The frozen single-pass 2D SAR model cannot reliably differentiate natural biogenic/wind slicks from mineral oil. |
| **G** | **Channel-Order Sensitivity** | **OBSERVED** | Swapping channels (Mapping B) collapsed Oil IoU from $74.49\%$ to $9.17\%$ and escalated Clean FAR to $92.00\%$. Driven by asymmetric normalization statistics and learned filter specialization. |
| **H** | **Environmental / Domain Shift** | **STRONGLY SUPPORTED** | Part I training data spans limited geography and seasons. External Part III data includes diverse sea states, wind regimes, and upwelling zones not present in training. |
| **I** | **Resolution / Downsampling Effects** | **PLAUSIBLE** | Five $2\times$ pooling/stride stages reduce spatial resolution to $\frac{1}{32}$ ($16 \times 16$). Slicks narrower than 16 pixels lose distinct feature geometry at the bottleneck. |
| **J** | **Receptive-Field Contextual Limitations** | **PLAUSIBLE** | ResNet-34 lacks multi-scale dilated context. Differentiating localized oil spills from synoptic-scale wind shadows requires contextual receptive fields $> 2048\text{ px}$, exceeding tile bounds ($512 \times 512$). |
| **K** | **Loss Imbalance (Gradient Dominance)** | **OBSERVED (MITIGATED)** | Phase 5G proved negative background gradients dominated positive boundaries. Setting $\text{pos\_weight} = 2.0$ in EXP-06 resolved the deficit, but further scaling risks FP rebound. |
| **L** | **Threshold Sensitivity** | **OBSERVED** | Sigmoid outputs are strictly polarized ($p < 0.05$ or $p > 0.70$). Shifting $\tau$ alone cannot suppress lookalike false alarms without degrading oil recall. |
| **M** | **Data-Distribution Imbalance** | **OBSERVED (ROOT CAUSE)** | Part I contains 1,200 scenes, **all belonging to the `Oil` class**. Part I contains **zero dedicated clean-water scenes and zero lookalike scenes**. Lookalikes are absent from training. |
| **N** | **Model Calibration Deficits** | **PLAUSIBLE** | Cross-entropy loss without temperature scaling produces overconfident lookalike activations ($p > 0.80$). |
| **O** | **Ground-Truth Label Ambiguity** | **PLAUSIBLE** | Manual SAR annotation has inherent subjectivity at slick margins and thin sheen boundaries. Natural surfactants and biogenic sheens physically overlap with mineral films. |
| **P** | **Attribution / Vessel Linking Errors** | **UNKNOWN** | Ocean Sentinel Phases 1–6 evaluated segmentation only. Downstream AIS association layers have not yet been evaluated on external imagery. |
| **Q** | **Pipeline Preprocessing / Contract Errors** | **STRONGLY SUPPORTED** | Normalization statistics $(\mu, \sigma)$ are asymmetric and polarization-specific. Inverting channels without swapping normalization causes $\approx 2$ to $3\sigma$ radiometric input distortion. |

---

## 3. Prior Internal Evidence Synthesis (EXP-01 Through EXP-06)

| Milestone | Core Intervention | Key Finding / Evidence Established | Status & Limitation |
|---|---|---|---|
| **EXP-01** | Baseline ResNet34UNet (BCE+Dice) | Established $0.7223$ validation IoU on Part I, but suffered severe clean-water false alarms ($20.09\%$ Clean FAR, $465\text{k FP px}$). | Baseline operating point; high false alarm rate. |
| **EXP-02b / EXP-03** | Hard-Negative Mining ($N=400$ tiles) | Clean FAR dropped from $20.09\%$ to $1.26\%$ ($-93.7\%$), but severe positive dropout occurred (Validation IoU collapsed to $0.6695$). | Proved hard negatives suppress false alarms but induce negative gradient dominance. |
| **EXP-04** | Balanced Ratio Hard-Negatives ($1:1$) | Mitigated negative gradient dominance, recovering IoU to $0.7091$ and Recall to $0.7719$. | Showed replacement sampling maintains stability. |
| **EXP-05** | Candidate Severity Cap ($FP \le 200\text{k}$) | Further stabilized training; Clean FAR reached $0.49\%$ ($-97.6\%$), but recall stagnated at $0.7823$, missing the $\ge 0.7850$ gate. | Disproved hypothesis that extreme severity outliers alone caused recall suppression. |
| **Phase 5G** | Positive Failure Forensic Audit | **Dual Error Structure:** Complete dropouts ($19.1\%$ FN mass, small slicks) vs. Boundary erosion ($80.9\%$ FN mass, large slicks). | Proved negative BCE gradient dominance caused boundary truncation. |
| **EXP-06** | Positive BCE Reweighting ($\text{pos\_weight} = 2.0$) | **All 5 acceptance gates passed simultaneously:** Recall rose to $0.8115$, IoU reached $0.7217$, Clean FAR stayed at $0.55\%$ ($97.3\%$ reduction). | **Global Best Development Checkpoint.** Frozen for Phase 6. |

---

## 4. Development-Data Diversity Audit (Trujillo Part I)

A systematic forensic audit of the development corpus (`data/raw/trujillo_2024`) reveals a fundamental structural limitation:

1. **Class Homogeneity:**
   - Total Parent Scenes: Exactly $1,200$ scenes ($2048 \times 2048$, dual-pol GeoTIFFs).
   - Class Breakdown: **100% `Oil` class** (`data/raw/trujillo_2024/images/Oil/`).
   - Dedicated Clean Water (`No oil`) Scenes: **0 scenes ($0.0\%$)**.
   - Dedicated Lookalike Scenes: **0 scenes ($0.0\%$)**.
2. **Negative Sampling Limitation:**
   - In Part I, "negative" tiles are strictly *empty ocean tiles surrounding oil spills in oil-positive scenes* ($1,827$ empty tiles in validation).
   - Hard negatives in EXP-03 through EXP-06 were mined exclusively from these peri-slick tiles (primarily open water clutter and coastal margins).
   - The model has literally **never been exposed during training to dedicated natural lookalike phenomena** (algal blooms, low-wind sea-surface slicks, internal wave packets, or upwelling).
3. **Polarization & Radiometric Coverage:**
   - Band 1: Mean $-33.23\text{ dB}$, Std $6.49\text{ dB}$ (Cross-polarization characteristics, consistent with Sentinel-1 VH).
   - Band 2: Mean $-19.94\text{ dB}$, Std $4.53\text{ dB}$ (Co-polarization characteristics, consistent with Sentinel-1 VV).
   - Both channels are strictly required; neither channel alone provides unambiguous mineral-vs-biogenic film separation in single-pass 2D SAR.
4. **Structural Conclusion:**
   **The observed Phase 6 Lookalike failure is fundamentally a DATA LIMITATION, not an architecture failure.** No neural network backbone can learn to reject dark lookalike formations when zero lookalike examples exist in its training distribution.

---

## 5. Channel-Ordering Investigation & Data Contract

The severe sensitivity observed in Phase 6 Mapping B (IoU $9.17\%$, FAR $92.00\%$) was forensically analyzed:

1. **Physical Sensor Alignment:**
   - Sentinel-1 dual-polarization SAR captures Co-polarization (VV or HH) and Cross-polarization (VH or HV).
   - Over the ocean, cross-polarization backscatter is substantially weaker (typically $-25$ to $-35\text{ dB}$) than co-polarization ($-15$ to $-22\text{ dB}$).
   - In Trujillo 2024 Part I, Band 1 ($\mu = -33.23\text{ dB}$) corresponds to Cross-Pol, and Band 2 ($\mu = -19.94\text{ dB}$) corresponds to Co-Pol.
2. **Normalization Coupling:**
   - Normalization statistics are asymmetric:
     $$\text{Ch0 (Band 1)}: \mu_0 = -33.233, \sigma_0 = 6.490 \qquad \text{Ch1 (Band 2)}: \mu_1 = -19.941, \sigma_1 = 4.531$$
   - In Mapping B, Band 2 (mean $-19.94$) was normalized with Channel 0's statistics:
     $$\frac{-19.94 - (-33.23)}{6.49} \approx +2.05\sigma$$
   - Band 1 (mean $-33.23$) was normalized with Channel 1's statistics:
     $$\frac{-33.23 - (-19.94)}{4.53} \approx -2.93\sigma$$
3. **Architectural Specialization:**
   - In `ResNet34UNet`, the first convolutional layer (`conv1`: $2 \rightarrow 64$) learned specialized spatial-polarization filters tied to this channel alignment.
4. **Verdict:**
   Channel sensitivity is **not an architectural deficiency to be mitigated through permutation invariance**. It is a **strict pipeline data-contract invariant**. Mapping A (Band 1 $\rightarrow$ Ch0, Band 2 $\rightarrow$ Ch1 with matching statistics) is the unique canonical interface.

---

## 6. Leakage-Safe Internal Development Holdout Protocol

To enable future model development without contaminating the frozen Trujillo Part III benchmark, a new three-way internal evaluation protocol is established:

```
+-----------------------------------------------------------------------------+
|                     EXPANDED INTERNAL DEVELOPMENT CORPUS                    |
|             (Trujillo Part I + Curated Lookalike/Negative Proxy)            |
+------------------------------------+----------------------------------------+
                                     |
         +---------------------------+---------------------------+
         |                                                       |
         v                                                       v
+-------------------------------+                       +-------------------------------+
|      TRAINING SPLIT (70%)     |                       |       DEV SPLIT (15%)         |
|  - Model Parameter Updates    |                       |  - Epoch Validation           |
|  - Hard-Negative Mining       |                       |  - Checkpoint Selection       |
|  - Data Augmentation          |                       |  - Hyperparameter Tuning      |
+-------------------------------+                       +-------------------------------+
                                                                 |
                                                                 v
                                                +-------------------------------+
                                                |   INTERNAL HOLDOUT (15%)      |
                                                |  - ZERO Checkpoint Selection  |
                                                |  - ZERO Threshold Tuning      |
                                                |  - Evaluated ONCE per Gate    |
                                                |  - Preregistered SHA-256      |
                                                +-------------------------------+
```

### Protocol Specifications:
1. **Scene-Level Spatial Isolation:** Partitions are assigned strictly by parent scene stem. All 16 chips from a scene must reside in the same partition (0% spatial leakage).
2. **Stratified Balancing:** If natural lookalike proxy scenes are added, they must be split proportionally across Train ($70\%$), Dev ($15\%$), and Internal Holdout ($15\%$).
3. **Preregistered Manifest:** The split manifest must be serialized to `data/metadata/internal_development_split_manifest.json` with an immutable SHA-256 hash before any training begins.

---

## 7. Candidate Intervention Families (Max 3 Families)

We define three candidate intervention families emerging strictly from diagnosed failure mechanisms:

```
                                  DIAGNOSED FAILURES
                                          |
            +-----------------------------+-----------------------------+
            |                             |                             |
            v                             v                             v
    [LOOKALIKE ALARMS]           [BOUNDARY EROSION]            [PHYSICAL AMBIGUITY]
   (0 Lookalike Training)        (Bottleneck Pooling)        (Single-Pass 2D SAR)
            |                             |                             |
            v                             v                             v
+-----------------------+     +-----------------------+     +-----------------------+
|  FAMILY A: DATA       |     |  FAMILY B: PERCEPTION |     |  FAMILY C: DECISION   |
|  Lookalike Proxy Pool |     |  ASPP / Multi-Scale   |     |  Two-Stage Rejector   |
|  & Balanced Training  |     |  Contextual Backbone  |     |  (Classifier Filter)  |
+-----------------------+     +-----------------------+     +-----------------------+
```

### Family A: Data Intervention — Curated Lookalike Proxy Pool & Balanced Mining
- **Diagnosed Failure Addressed:** Failure F (Lookalike False Alarms, $90.67\%$ Scene FAR) and Failure M (Data Distribution Imbalance).
- **Hypothesis:** Exposing the model during training to an independent, leakage-safe dataset of natural dark ocean features (biogenic films, low-wind shadows, internal waves) will teach convolutional filters to differentiate biological surfactants from mineral oil.
- **Intervention:** Curate $\sim 150$ non-Part-III natural lookalike scenes from public Sentinel-1 archives; integrate into internal Train ($70\%$) and Dev/Holdout ($30\%$); train with balanced sampling ($1:1$ positive to hard-negative/lookalike).
- **Expected Result:** $> 50\%$ reduction in internal lookalike FAR while maintaining clean-water FAR $< 1.0\%$ and Oil macro IoU $\ge 0.72$.
- **Falsifier:** Lookalike FAR remains $> 80\%$ on internal holdout despite lookalike training, proving single-pass SAR intensity is physically ambiguous.
- **Contamination Guard:** Part III is strictly excluded; candidate proxy scenes verified against Part III manifest by date, orbit, and bounding box.

### Family B: Perception Intervention — Multi-Scale Receptive Field & Dilated Context (ASPP)
- **Diagnosed Failure Addressed:** Failure C (Boundary Erosion, $80.9\%$ FN mass) and Failure J (Receptive-Field Contextual Limits).
- **Hypothesis:** Downsampling to $\frac{1}{32}$ resolution erodes narrow filaments. Adding an Atrous Spatial Pyramid Pooling (ASPP) block at the bottleneck with dilation rates $r \in \{1, 6, 12, 18\}$ will capture synoptic context while preserving fine boundary detail.
- **Intervention:** Integrate an ASPP module between ResNet-34 encoder and decoder; freeze all 24 training hyperparameters identical to EXP-06.
- **Expected Result:** Validation Recall $\ge 0.8300$ (+1.8 pp over EXP-06) with reduced boundary FN mass and zero Clean FAR regression.
- **Falsifier:** ASPP increases parameters ($+3.5\text{M}$) but yields $< +0.5\text{ pp}$ recall gain or destabilizes clean FAR.
- **Contamination Guard:** Evaluated exclusively on internal Dev and Internal Holdout.

### Family C: Specialist Decision Intervention — Cascaded Lookalike Rejection Classifier
- **Diagnosed Failure Addressed:** Failure F (Lookalike Ambiguity) and Failure P (Specialist Component Separation).
- **Hypothesis:** Pixel-level segmentation and patch-level false-alarm discrimination are conflicting tasks for a single backbone. A lightweight secondary classifier trained on proposed slick candidates (evaluating patch morphology, perimeter-to-area ratio, damping depth, and auxiliary ECMWF wind speed) can filter lookalikes without compromising slick segmentation recall.
- **Intervention:** Two-stage pipeline: Stage 1 (Frozen EXP-06 segmentation proposer) $\rightarrow$ Stage 2 (Morphological/Environmental Lookalike Filter).
- **Expected Result:** Rejection of $> 75\%$ of lookalike scenes with $< 2\%$ loss in true oil slick recall.
- **Falsifier:** Secondary classifier drops true slick recall by $> 5\%$ or fails to distinguish proxy lookalikes from oil.
- **Contamination Guard:** Stage 2 trained and validated exclusively on internal holdout candidate proposals.

---

## 8. Acceptance Gates for Any Future Model

Any future candidate model (e.g., candidate EXP-07) must satisfy all preregistered gates simultaneously on the internal Dev/Holdout protocol:

| Gate Category | Metric Name | Population / Scope | Acceptance Floor | Baseline Reference (EXP-06) |
|---|---|---|:---:|:---:|
| **PRIMARY** | **Internal Oil Macro Mean IoU** | Internal Positive Dev ($N=180$ patches) | $\mathbf{\ge 0.7200}$ | $0.7217$ |
| **PRIMARY** | **Internal Oil Macro Recall** | Internal Positive Dev ($N=180$ patches) | $\mathbf{\ge 0.8100}$ | $0.8115$ |
| **PRIMARY** | **Internal Oil Macro Dice ($F_1$)** | Internal Positive Dev ($N=180$ patches) | $\mathbf{\ge 0.8250}$ | $0.8290$ |
| **SECONDARY** | **Internal Clean-Water FAR** | Empty Ocean Dev Tiles ($N=1,827$ tiles) | $\mathbf{\le 1.00\%}$ | $0.55\%$ |
| **SECONDARY** | **Internal Significant FAR** | Empty Ocean Dev Tiles ($N=1,827$ tiles) | $\mathbf{\le 1.00\%}$ | $0.55\%$ |
| **SECONDARY** | **Complete Tile Dropouts** | GT-Positive Dev Tiles ($N=1,053$ tiles) | $\mathbf{\le 174\text{ tiles}}$ | $174$ tiles ($16.5\%$) |
| **SECONDARY** | **Lookalike Proxy Scene FAR** | Internal Lookalike Proxy Dev | $\mathbf{\le 45.00\%}$ | N/A (untested) |
| **REGRESSION** | **Clean-Water FP Pixels** | Empty Ocean Dev Tiles ($N=1,827$ tiles) | $\mathbf{\le 150,000\text{ px}}$ | $113,187\text{ px}$ |

---

## 9. Contingency Matrix

| ID | Trigger Condition | Mandatory Operational Contingency Action |
|:---:|---|---|
| **A** | **No suitable internal Lookalike data available** | **Do NOT tune against Part III.** Pause model training. Acquire and annotate open Sentinel-1 dark feature imagery. Equivalence remains unverified until internal holdout exists. |
| **B** | **Channel-ordering pipeline ambiguity** | Maintain Mapping A as fixed canonical contract. Add strict assertion in DataLoader verifying Band 1 $\rightarrow$ Ch0 and Band 2 $\rightarrow$ Ch1. Prohibit dynamic channel permutation. |
| **C** | **Lookalike problem appears data-limited** | Prioritize dataset expansion (Family A) over architectural complexity (Family B). Do not train larger backbones on homogeneous data. |
| **D** | **Lookalike problem persists after proxy data** | If single-pass SAR fails to differentiate lookalikes under Family A, activate Family C (Specialist Decision Filter with auxiliary wind/temperature features). |
| **E** | **Small-slick boundary erosion remains bottleneck** | If Lookalike FAR is stabilized but slick margins remain diffuse, activate Family B (ASPP multi-scale dilated convolutions). |
| **F** | **Multiple failure mechanisms interact** | Execute strictly one-factor-at-a-time experiments. Never combine data intervention (Family A) and architecture changes (Family B) in a single run. |
| **G** | **No single intervention satisfies all gates** | Do not force an end-to-end monolithic architecture. Adopt the specialist decomposition: segmentation proposer + lookalike classifier. |

---

## 10. Durable Filesystem Telemetry Design

In accordance with Rule 3, Rule 4, and Rule 9, any future training or evaluation task must implement atomic, durable telemetry:

### Schema: `run_state.json`
```json
{
  "timestamp_utc": "2026-09-12T19:50:00.000000+00:00",
  "heartbeat": "2026-09-12T19:55:00.000000+00:00",
  "pid": 12345,
  "status": "RUNNING",
  "phase": "TRAINING_EPOCH",
  "current_epoch": 3,
  "total_epochs": 10,
  "progress_pct": 30.0,
  "batch_current": 150,
  "batch_total": 500,
  "throughput_samples_per_sec": 42.5,
  "estimated_time_remaining_sec": 1250,
  "gpu_memory_used_gb": 4.12,
  "gpu_memory_total_gb": 6.00,
  "system_ram_used_gb": 8.45,
  "active_checkpoint_sha256": "B5FFCCA3...",
  "exit_code": null,
  "error_message": null
}
```

### Human-Readable Telemetry Invariant:
Every batch update must print a standardized one-line heartbeated progress indicator:
```
PHASE: TRAINING_EPOCH_3 | PROGRESS: 30.0% (150/500) | STATUS: RUNNING | ETA: 00:20:50 | HEARTBEAT: 2026-09-12T19:55:00Z
```

---

## 11. Regression Guardrail Plan

To permanently guard against the errors diagnosed in Phases 5 and 6, the following automated regression test suites are mandated:

1. **`test_channel_contract.py`:** Assert that `TrujilloTileDataset` binds Band 1 to Channel 0 and Band 2 to Channel 1, verifying that $\mu_0 = -33.23$ and $\mu_1 = -19.94$ are correctly applied.
2. **`test_part_iii_firewall.py`:** Cryptographically assert that zero Part III image paths or file hashes exist in any training, validation, or candidate pool manifest.
3. **`test_metric_scope_semantics.py`:** Verify that all reporting tools enforce the four-level metric firewall and label directional comparisons as `Signed Delta (A − B)`.
4. **`test_telemetry_durability.py`:** Simulate sudden process termination and verify that `run_state.json` is atomically updated and readable without file corruption.

---

## 12. Definitive CAO Recommendation

Based on rigorous empirical evidence across EXP-01 through EXP-06 and the frozen Phase 6 external evaluation, the definitive recommendation is:

### **RECOMMENDATION: OPTION A — DATA FIRST (PHASE 7A)**

**Rationale:**
1. **Root Cause Isolated:** The external lookalike failure ($90.67\%$ Scene FAR) was caused by complete absence of lookalikes in the training corpus ($0$ lookalike scenes in Part I).
2. **Architecture is NOT the Current Bottleneck:** ResNet34UNet demonstrated excellent cross-domain segmentation on true slicks ($74.49\%$ macro IoU) and open ocean ($99.985\%$ specificity). Changing the neural network architecture before exposing it to lookalike training data would be ungrounded and ineffective.
3. **No Premature Training:** No training run (EXP-07) is authorized until a dedicated, leakage-safe internal Lookalike & Dark-Feature Proxy Dataset is curated, validated, and partitioned under the new internal holdout protocol.

---
