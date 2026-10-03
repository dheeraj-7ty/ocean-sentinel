# OCEAN SENTINEL — PHASE 7B.2A OPS-01 TRAINING READINESS CONTRACT
**Document Identifier:** `PHASE_7B2A_OPS01_TRAINING_READINESS_CONTRACT`  
**Governing Roles:** Senior CAO Scientific Data / Benchmark Auditor, Remote-Sensing Benchmark Auditor, ML Protocol Auditor  
**Date:** September 13, 2026  
**Status:** **PRE-REGISTERED SPECIFICATION — TRAINING STRICTLY UNEXECUTED IN THIS PHASE**  
**Associated Authoritative Manifests:**  
- [`data/metadata/li_authoritative_class_dictionary.json`](file:///d:/Projects/ocean-sentinel/data/metadata/li_authoritative_class_dictionary.json) (`SHA-256: 9377DA6310804E459F2113914F6C933FF42F03277EC2D740A1FE29630A46DE46`)  
- [`data/metadata/li_iw_source_scene_manifest.json`](file:///d:/Projects/ocean-sentinel/data/metadata/li_iw_source_scene_manifest.json)  
- [`data/metadata/li_wv_source_lineage_manifest.json`](file:///d:/Projects/ocean-sentinel/data/metadata/li_wv_source_lineage_manifest.json)  
- [`data/metadata/li_geometry_registration_audit_v2.json`](file:///d:/Projects/ocean-sentinel/data/metadata/li_geometry_registration_audit_v2.json)  
- [`data/metadata/benchmark_split_readiness.json`](file:///d:/Projects/ocean-sentinel/data/metadata/benchmark_split_readiness.json)  

---

### 1. GOVERNANCE MANDATE & INVARIANT GATE

This contract establishes the formal specification for the future Ocean Phenomena Specialist (OPS-01).  
**HARD PROTOCOL INVARIANT:**  
- **ZERO MODEL TRAINING AUTHORIZED IN THIS PHASE.**  
- **EXP-07 TRAINING: STRICTLY FORBIDDEN.**  
- **OPS-01 TRAINING: STRICTLY BLOCKED UNTIL FORMAL STAGE-GATE APPROVAL.**  
- **EXP-06 CHECKPOINT: BITWISE FROZEN** (`B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF`).  
- **INFERENCE THRESHOLD: FROZEN AT $\tau = 0.22$.**  

---

### 2. TARGET SCOPE & CAPABILITY GAP

The Ocean Sentinel system architecture requires multi-specialist evidence fusion:
$$\text{Perception (EXP-06)} + \text{Phenomena Recognition (OPS-01)} + \text{Environmental Context} + \text{Evidence Fusion}$$

#### Demonstrated Capability Gap:
The primary oil spill detection network (EXP-06) was trained on high-contrast petroleum slicks and exhibits false-positive sensitivity to low-backscatter natural look-alikes (biogenic slicks, low wind areas, internal wave dark crests, rain downdrafts). OPS-01 is chartered to provide an independent recognition engine that identifies these oceanographic and atmospheric phenomena, allowing downstream fusion to suppress look-alike false alarms without altering the frozen oil-detection model.

---

### 3. TARGET PHENOMENON TAXONOMY & CLASS ALLOCATION

Based on the exhaustive 5,011-mask forensic audit, classes are allocated into 4 strict operational tiers:

| Class ID | Abbreviation | Name | Total Labeled Pixels | Pixel % | Images | OPS-01 Operational Role | Rationale |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- | :--- |
| **0** | **BG** | Background Seawater | 32,264,741 | 9.82% | 1,769 | **CORE_BACKGROUND** | Ambient open-ocean baseline matrix |
| **2** | **BS** | Biological Slicks | 44,132,805 | 13.44% | 1,034 | **CORE_LOOKALIKE** | Primary global look-alike (Marangoni wave damping) |
| **4** | **LWA** | Low Wind Area | 22,918,463 | 6.98% | 601 | **CORE_LOOKALIKE** | Primary global look-alike (< 3 m/s calm sea) |
| **12** | **IWs** | Oceanic Internal Waves | 10,072,384 | 3.07% | 417 | **CORE_LOOKALIKE** | Soliton packet convergence/divergence stripes |
| **6** | **OF** | Oceanic Front | 1,467,020 | 0.45% | 437 | **CORE_LOOKALIKE** | Current shear lines collecting natural surfactants |
| **8** | **RC/RF** | Rainfall / Rain Cells | 8,424,986 | 2.57% | 484 | **CORE_LOOKALIKE** | Atmospheric downdraft dark footprints |
| **11** | **Eddy** | Ocean Eddy | 5,008,621 | 1.53% | 501 | **CORE_LOOKALIKE** | Spiraling surfactant lines in rotating vortices |
| **10** | **WS** | Wind Streak | 35,453,890 | 10.80% | 585 | **AUXILIARY_CONTEXT** | Boundary-layer roll structures |
| **7** | **POW** | Pure Ocean Wave | 91,480,185 | 27.86% | 1,746 | **AUXILIARY_CONTEXT** | Dominant ambient swell spectrum |
| **5** | **MCC** | Micro Convective Cells | 43,978,427 | 13.39% | 830 | **AUXILIARY_CONTEXT** | Honeycomb convective wind patterns |
| **1** | **AF** | Atmospheric Front | 3,726,670 | 1.13% | 644 | **AUXILIARY_CONTEXT** | Regional air mass wind steps |
| **13** | **HM** | Artificial Objects | 30,647 | 0.01% | 207 | **MARITIME_ATTRIBUTION** | Ships, platforms, offshore wind infrastructure |
| **9** | **SI** | Sea Ice | 29,179,492 | 8.89% | 454 | **CRYOSPHERIC_MODE** | Segregated to polar operational evaluation |
| **3** | **IB** | Iceberg | 260,863 | 0.08% | 398 | **CRYOSPHERIC_MODE** | Segregated to polar operational evaluation (100% WV) |
| **14** | **OS** | Mineral Oil Spill | 1,702 | 0.0005% | 4 | **STRICTLY_EXCLUDED** | Disqualified: 4 images only; zero statistical validity |

**Class Exclusion Mandate:** Class 14 (OS) is **STRICTLY EXCLUDED** from the training target. The specialist model learns phenomenon recognition; it does not predict oil.

---

### 4. INPUT REPRESENTATION & TRACK SEPARATION

To avoid domain conflation, future training and evaluation maintain two separate tracks:

- **TRACK A (Sentinel-1 IW Mode):**
  - Imagery: $256 \times 256$ patches, $100\text{ m}$ ground resolution ($25.6\text{ km} \times 25.6\text{ km}$) for initial specialist development; native $10\text{ m}$ Level-1 GRD dual-pol (VV+VH dB, $512 \times 512$) for operational deployment once ESA SAFE granules are recovered.
  - Channels: Single-pol VV uint16 normalized for prototype; dual-pol VV+VH decibels for native operational deployment.
- **TRACK B (Sentinel-1 WV Mode):**
  - Imagery: $256 \times 256$ vignettes from TenGeoP-SARwv ($N=2,383$).
  - Evaluated strictly as a distinct open-ocean track; never averaged into a single misleading headline score with IW coastal data.

---

### 5. SPLIT PROTOCOL & GEOGRAPHIC HOLDOUTS

1. **Parent-Scene / Orbit-Pass Partitioning:**
   - **IW Track:** 484 unique source scene stems partitioned into 70% Train (~338 scenes), 15% Dev (~73 scenes), 15% Test (~73 scenes). Zero sibling patch leakage across splits.
   - **WV Track:** 1,678 unique orbit passes partitioned into 70% Train (~1,174 passes), 15% Dev (~252 passes), 15% Test (~252 passes). Zero sibling vignette leakage across splits.
2. **Pre-Registered Geographic Holdouts:**
   - North Atlantic basin holdout
   - Mediterranean Sea basin holdout
   - Western Pacific / South China Sea basin holdout
3. **Temporal Holdout:**
   - Pre-2020 vs Post-2020 evaluation to quantify detector stability across sensor degradation and constellation changes.

---

### 6. ARCHITECTURE CANDIDATES & BENCHMARKING POLICY

The published SegFormer model from Li et al. is an empirical reference, not an entitled preference. The following 3 architecture families must be benchmarked under identical conditions:
1. **ResNet-34 / ConvNeXt-Tiny U-Net:** Proven inductive bias for spatial segmentation, lightweight parameter footprint, fast convergence.
2. **SegFormer-B2 / B3:** Hierarchical Transformer encoder with multi-scale attention and lightweight MLP decoder.
3. **Swin-UNet:** Shifted-window self-attention architecture capturing multi-scale oceanic wave packets.

---

### 7. LOSS FUNCTION & CLASS IMBALANCE HANDLING

Extreme class imbalance exists (POW has 91.5M pixels, while OF has 1.5M pixels and HM has 30.6k pixels).
- **Composite Loss Formulation:**
  $$\mathcal{L} = w_{\text{CE}} \mathcal{L}_{\text{Weighted-CE}} + w_{\text{Focal}} \mathcal{L}_{\text{Focal}} (\gamma=2.0) + w_{\text{Lovasz}} \mathcal{L}_{\text{Lovasz-Softmax}}$$
- **Dynamic Inverse-Frequency Weighting:** Class weights computed on training partition pixels:
  $$w_c = \frac{1}{\ln(1.02 + p_c)}$$
  where $p_c$ is the pixel frequency of class $c$.

---

### 8. EVALUATION METRICS & BOUNDARY UNCERTAINTY ZONE

1. **Mean Intersection over Union (mIoU):** Evaluated across classes 1–12 (excluding background).
2. **Per-Class IoU & Dice Score:** Tracked individually for each core look-alike class.
3. **Boundary F1 Score (BF-Score):** Evaluated with a 50-meter (5 native pixels) tolerance envelope.
4. **Boundary Erosion Protocol:** In accordance with `li_geometry_registration_audit_v2.json`, pixels within 50m of a phenomenon boundary must be segregated during high-resolution scoring to prevent penalizing models for genuine 10m morphology.

---

### 9. KAGGLE ACCELERATOR GOVERNANCE & BUDGET

- **Known-Good Target Accelerator:** 2 x NVIDIA Tesla T4 (16 GB VRAM each).
- **Compute Budget Allocation:**
  - Effective throughput: ~60 samples/sec across 2x T4 using PyTorch AMP (Automatic Mixed Precision, float16).
  - Training population: ~338 IW scenes + ~1,174 WV passes ($\approx 3,500$ patches).
  - Epoch runtime: $\approx 60$ seconds.
  - 50 epochs: $\approx 50$ minutes ($\approx 1.66$ T4 GPU-hours).
  - **Budget Impact:** Consumes $\approx 5.6\%$ of the weekly 30 GPU-hour allocation, preserving over 90% contingency margin.
- **Mandatory Runtime Snapshot Logging:** Every run must log GPU model, GPU count, VRAM, CUDA version, driver version, PyTorch version, AMP configuration, runtime, checkpoint hash, and quota usage.

---

### 10. EXP-06 INDEPENDENCE & BENCHMARK FIREWALL

1. **Strict Benchmark Separation:** Benchmark B (stress-testing EXP-06) and Benchmark A (training OPS-01) remain strictly isolated. No OPS-01 outputs may influence Benchmark B test construction.
2. **No Model-Output Label Contamination:** EXP-06 predictions, confidences, or false-positive alarms must NEVER be used to create labels, select patches, or adjust thresholds for OPS-01.
