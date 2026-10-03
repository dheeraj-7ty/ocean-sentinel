# DIAG04_PREEXECUTION_AUDIT_AND_HARDENED_PLAN

**Investigation ID:** `DIAG-04-RECEPTIVE-FIELD-SCALE-COMPATIBILITY`  
**Task ID:** `EXP-07-P0-DIAG-04-LINEAGE-GATE`  
**Authoritative Dataset Contract:** Level 5 Canonical Physical Dataset Specification (OPS-02 v1.0.1, `OPS02_v1.0.1_FROZEN`)  
**Baseline Model:** ResNet18-UNet (14,310,860 trainable parameters, Option B BatchNorm baseline)  
**Target Execution Environment:** CPU-only, local Python 3.10 virtual environment (`.venv`)  
**Authorization State:** `READY_WITH_PREREQUISITES` (EXECUTION STRICTLY NOT AUTHORIZED)  

---

## 1. Current DIAG-04 Definition & Errata Resolution

In the canonical Ocean Sentinel diagnostic roadmap established in C22-F, restored in C22-H, and reaffirmed in C22-J and DIAG-03, DIAG-04 is designated as:
- **Identifier:** `DIAG-04-RECEPTIVE-FIELD-SCALE-COMPATIBILITY`
- **Formal Title:** Receptive Field & Spatial Scale Compatibility Diagnostic
- **Roadmap Position:** Priority 4 (following DIAG-01, DIAG-02, and DIAG-03; strictly preceding DIAG-05).
- **Core Focus:** Evaluates whether convolutional receptive fields, multi-path skip connections, and downsampling strides of the baseline architecture are demonstrably compatible, incompatible, or simply uncertain relative to the observed spatial structure and boundary extents of the 12 canonical taxonomy classes.

### Errata Resolution & Architectural Facts
1. **Dataset Provenance & Tile Counts (OPS-02: 132 TRAIN / 40 DEV / 40 HOLDOUT = 212 Total):**
   - Preliminary planning drafts informally referenced an unverified count of "104 TRAIN and 42 DEV tiles (total 146)". Subsequent audit passes temporarily cited OPS-01 (72 TRAIN / 39 DEV / 36 HOLDOUT = 147 tiles) from historical C5 baseline metadata.
   - **Forensic Correction & Lineage Restoration (`LL-DIAG04-PLAN-003`):** Authoritative machine manifests ([`data/ops02/manifests/ops02_physical_dataset_manifest_v1.json`](file:///d:/Projects/ocean-sentinel/data/ops02/manifests/ops02_physical_dataset_manifest_v1.json) and [`data/ops02/OPS02_DATASET_FREEZE_SPEC_v1.0.1.json`](file:///d:/Projects/ocean-sentinel/data/ops02/OPS02_DATASET_FREEZE_SPEC_v1.0.1.json)) prove that the canonical EXP-07 diagnostic benchmark dataset is **OPS-02**, containing exactly **212 physical tiles** across **64 independent parent clusters / mission datatakes** and **85 constituent Level-1 GRD scenes**:
     - **TRAIN Partition:** **132 tiles** across **40 independent parent clusters**.
     - **DEV Partition:** **40 tiles** across **12 independent parent clusters**.
     - **HOLDOUT Partition:** **40 tiles** across **12 independent parent clusters** (strictly firewalled, zero access!).
     - **Accessible Development Set (TRAIN + DEV):** **172 tiles** across **52 independent parent clusters**.
     - **Physical Disk Paths:** `data/ops02/derived/images/*.tif` (uncalibrated SAR DN) and `data/ops02/derived/masks/*.png` (labels).
     - **Normalization Constants:** $\mu=4.424158, \sigma=0.469261$ (INV-06).
2. **Encoder Layer 4 Receptive Field ($435\text{ pixels}$ vs Stated $483\text{ pixels}$):**
   - Preliminary drafts cited a theoretical receptive field (TRF) of "483 pixels" for the ResNet-18 encoder.
   - **Forensic Correction:** Layer-by-layer analytical recurrence directly on the authoritative implementation ([`src/ocean_sentinel/ml/exp07_reference.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ml/exp07_reference.py)) proves that the Layer 4 encoder output has a theoretical receptive field of exactly **$435\text{ pixels}$** (stride 32), NOT 483 pixels. All plan artifacts and numerical benchmarks are corrected to 435 pixels.
3. **Multi-Path UNet Dependency & Exact Phase Spans:**
   - Preliminary drafts treated the network as a single-path feedforward pipeline with a single receptive field.
   - **Forensic Correction:** The model is a **UNet with skip connections**. Output pixels possess multiple parallel dependency paths with exact index bounds:
     - **Path A ($x_0$ shallow skip from Conv1):** $\mathbf{19\text{ pixels}}$ ($1.9\text{ km}$), phase-invariant across all output coordinates.
     - **Path B ($x_1$ skip from Layer 1):** $\mathbf{71\text{ pixels}}$ ($7.1\text{ km}$), phase-invariant across all output coordinates.
     - **Path C ($x_2$ skip from Layer 2):** $\mathbf{155\text{ to }163\text{ pixels}}$ ($15.5\text{ to }16.3\text{ km}$), phase-dependent.
     - **Path D ($x_3$ skip from Layer 3):** $\mathbf{323\text{ to }339\text{ pixels}}$ ($32.3\text{ to }33.9\text{ km}$), phase-dependent.
     - **Path E ($x_4$ bottleneck path):** $\mathbf{531\text{ to }563\text{ pixels}}$ ($53.1\text{ to }56.3\text{ km}$), phase-dependent.
4. **Theoretical Dependency Envelope vs Crop-Clipped Usable Context (`LL-EXP07-028`):**
   - Stating that the model has a 563 px receptive field does **NOT** mean the model sees 563 px of physical ocean context.
   - On a canonical $256 \times 256$ input tile ($25.6 \times 25.6\text{ km}$), the computational dependency envelope is **strictly clipped by the $256 \times 256$ crop border**. Outside the tile, inputs are zero-padded or swath-masked. The available physical context is at most $25.6\text{ km}$.
5. **Bottleneck Stride ($32\times = 3.2\text{ km}$) is NOT a Hard Detection Limit:**
   - Downsampling stride defines the **encoder bottleneck sampling scale** ($3.2\text{ km}$ grid interval), NOT a hard detectability threshold. Skip connections carry high-resolution features ($1\times$ and $2\times$ scale) directly to the decoder, preserving localization for sub-stride targets (HM: 1–3 px).
6. **Effective Receptive Field (ERF) Status:**
   - True empirical ERF is a learned-weight sensitivity distribution requiring gradient backpropagation, which is strictly prohibited in diagnostics (`BLOCK-006`). DIAG-04 evaluates architecture-only TRFs and analytical Gaussian proxies; **true learned-weight ERF is NOT measured in DIAG-04**.
7. **PSD Threshold Audit & Removal of Arbitrary 3 dB Cutoff:**
   - The preliminary "3 dB over background" rule was an arbitrary threshold with no oceanographic or mathematical justification and no operational definition of "background".
   - It is replaced by **peak stability and continuous prominence reporting**: verifying local maxima, windowing invariance ($< 15\%$ wavenumber shift across Hann, Hamming, and Blackman tapers), and classifying monotonic spectra as **`BROADBAND_MONOTONIC`**.

---

## 2. Scientific Motivation

Semantic segmentation models do not classify pixels as isolated radiometric samples; they assign class labels by aggregating spatial contextual cues across convolutional receptive fields.

In DIAG-03, we established that single-pixel 1-D radiometric backscatter distributions exhibit moderate overlap across multiple classes (e.g., Biological Slicks vs Low Wind Area, $\text{OVL} = 0.8402$; 22 of 66 pairs $\ge 0.70$), along with substantial scene-to-scene environmental heterogeneity. This 1-D radiometric overlap motivates evaluating whether spatial context provides additional discriminative information, as 1-D radiometry alone does not uniquely separate several observed class distributions. However, radiometric overlap is an observational finding, not proof that 2D spatial context is necessary or sufficient. In visual SAR interpretation and physical oceanographic observation, differentiation is hypothesized to rely on **spatial structures**:
1. Internal waves (IWs) exhibit distinct periodic soliton wave-packet crests.
2. Mesoscale Cellular Convection (MCC) forms open or closed polygonal convective cells.
3. Wind Streaks (WS) manifest as linear rolls aligned with surface wind vectors.
4. Biological Slicks (BS) form sinuous, narrow surface filaments.
5. Artificial/Anthropogenic Objects (HM) appear as localized, highly reflective point-like structures.

If a deep neural network achieves low mIoU on these classes, the limitation could arise from optimization failure, loss weights, or an architectural **spatial scale mismatch** (evaluated here strictly as a structural compatibility hypothesis, NOT as an established explanation or cause of low mIoU):
- **Data-Window Scale ($25.6\text{ km}$):** Large mesoscale phenomena may be bounded by the $256 \times 256$ ($25.6\text{ km}$) tile boundary (`EDGE_CENSORED_OBSERVATION`), preventing the network from observing the full enclosing spatial envelope.
- **Architectural Sampling Scale ($3.2\text{ km}$):** Compact annotated components (e.g., HM: 1-3 pixels; point-like RF) fall below the 32-pixel bottleneck sampling interval. While skip connections provide high-resolution paths, bottleneck features sample these features coarsely.
- **Architectural Receptive Field Scale:** The network's receptive field across intermediate and bottleneck stages may differ in scale from the characteristic spatial organization of wave or convective annotations.

**Methodological Boundary (`BLOCK-004`):** Characterizing these spatial scale relationships is essential before undertaking compute-intensive gradient or optimization diagnostics (DIAG-05). However, DIAG-04 evaluates scale compatibility as an observational hypothesis; it does **NOT** assume that spatial scale mismatch produces or explains poor model performance.

---

## 3. Evidence Already Established & Diagnostic Lineage Continuity

### 3.1 Canonical Diagnostic Lineage: DIAG-01 → DIAG-02 → DIAG-03 → DIAG-04
All roadmap diagnostics form an unbroken investigative chain evaluating the **canonical OPS-02 benchmark**:

```
[EXP-07 Baseline C16/C22: dev_mIoU ~0.049 on OPS-02]
                         │
                         ▼
[DIAG-01 (C22-G)]: Class Support & Metric Semantics on OPS-02 DEV (40 tiles, 12 parent clusters)
   └─ Result: Macro score is valid but support-sensitive; OF (1 cluster, 1,709 px) & RF (1 cluster, 9,550 px) ultra-sparse.
                         │
                         ▼
[DIAG-02 (C22-I/J)]: Sampler Exposure & Schedule Dynamics on OPS-02 TRAIN (132 tiles, 40 parent clusters)
   └─ Result: Candidate F hybrid sampler provided non-zero exposure across all rare classes; starvation bounded.
                         │
                         ▼
[DIAG-03]: Radiometric Feature Discriminability on OPS-02 TRAIN (132) + DEV (40) = 172 tiles, 52 clusters
   └─ Result: 1-D pixel backscatter overlap is moderate (22 of 66 pairs >= 0.70); scene heterogeneity is high.
                         │
                         ▼
[DIAG-04]: Receptive Field & Spatial Scale Compatibility on OPS-02 TRAIN (132) + DEV (40) = 172 tiles, 52 clusters
   └─ Goal: Evaluate whether spatial context provides additional discriminative information and whether multi-path receptive fields match annotation scales.
```

### 3.2 Authoritative Direct Reconciliation: OPS-01 vs OPS-02

| Metric / Dimension | Historical Exploratory Dataset (OPS-01) | Canonical Diagnostic Benchmark (OPS-02) | Reconciliation Status & Scientific Decision |
| :--- | :--- | :--- | :--- |
| **Dataset Identifier** | `OPS-01` | `OPS-02` | **OPS-02 is the AUTHORITATIVE benchmark**; OPS-01 is historical exploratory baseline. |
| **Specification / Freeze Version** | `v1.0.0` (Informally referenced as `v1.0.1`) | `OPS02_v1.0.1_FROZEN` (`OPS02_DATASET_FREEZE_SPEC_v1.0.1.json`) | Locked under `GOV-RULE-085` cryptographic binding. |
| **Manifest Path** | `data/metadata/ops01_physical_dataset_manifest_v4.json` | `data/ops02/manifests/ops02_physical_dataset_manifest_v1.json` | Explicit file separation; different root directories. |
| **Manifest SHA-256** | `FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E` | `F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102` | Programmatically verified bitwise digests. |
| **Dataset Purpose** | Initial single-scene exploratory baseline (C1-C11) | Multi-scene, geographically diverse benchmark (C12-C22, Diagnostics) | Diagnostic roadmap evaluates the hard OPS-02 benchmark (~0.049 mIoU). |
| **Total Physical Tiles** | **147** | **212** | OPS-02 expanded tile inventory by +65 tiles (+44.2%). |
| **TRAIN Tiles** | 72 | **132** | OPS-02 TRAIN partition contains 132 tiles. |
| **DEV Tiles** | 39 | **40** | OPS-02 DEV partition contains 40 tiles. |
| **HOLDOUT Tiles** | 36 (quarantined) | **40 (quarantined)** | Both partitions strictly firewalled (`0` access permitted). |
| **Accessible Development Tiles** | 111 (72 TRAIN + 39 DEV) | **172 (132 TRAIN + 40 DEV)** | **DIAG-04 analyzes exactly 172 development tiles**. |
| **Parent Acquisition Clusters (K)** | 27 scenes (12 TRAIN / 7 DEV / 8 HOLDOUT) | **64 clusters (40 TRAIN / 12 DEV / 12 HOLDOUT)** | OPS-02 has 52 accessible development clusters. |
| **Mission Datatakes** | Inferred 1:1 with scenes (27) | **64 datatakes** (datatake-level clustering under `GOV-RULE-077`) | Resolves along-track pseudo-replication. |
| **Constituent Level-1 Scenes** | 27 | **85 scenes** | Full multi-scene coverage. |
| **Normalization Constants** | $\mu=4.275600, \sigma=0.386600$ | $\mu=4.424158, \sigma=0.469261$ (INV-06) | Fixed TRAIN valid-pixel standardization. |
| **Taxonomy Scope** | 12 dense classes (Classes 3, 9, 14 excluded) | 12 dense classes (Classes 3, 9, 14 excluded) | Identical canonical 12-class phenomenon taxonomy. |
| **Historical Baseline Score** | $\approx 0.119 - 0.138$ mIoU (C8, C10) | $\approx 0.049$ mIoU (C16 replicate, C22 multiseed) | DIAG-04 characterizes spatial scale relationships on active benchmark. |
| **Used by Prior Diagnostics?** | NO (Only target in C20 cross-evaluation) | **YES: DIAG-01, DIAG-02, and DIAG-03 all used OPS-02** | Lineage continuity requires OPS-02 for DIAG-04. |

### 3.3 Protection Against Future Path Drift: Historical Baseline vs Active Diagnostics

To protect DIAG-04 and subsequent diagnostics from path drift:
- **Historical Baseline (`scripts/train_exp07.py`):** Derived from early single-scene exploratory phases (C5-C11) and bound to OPS-01 (`data/metadata/ops01_physical_dataset_manifest_v4.json`). It remains preserved strictly as an archival baseline and MUST NOT be used to derive or define dataset contracts for active diagnostics.
- **Active Diagnostic Lineage:** All active canonical diagnostics (DIAG-01, DIAG-02, DIAG-03, and future DIAG-04) strictly target the multi-scene OPS-02 benchmark (`data/ops02/manifests/ops02_physical_dataset_manifest_v1.json`, SHA-256 `F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102`).
- **Future DIAG-04 Contract:** The future DIAG-04 execution script must directly ingest the authoritative OPS-02 manifest through its machine data contract and fail closed if OPS-01 or any unexpected dataset identifier, path, or hash appears.

---

## 4. Unresolved Scientific Uncertainty

Despite DIAG-01, DIAG-02, and DIAG-03, critical spatial uncertainties remain unresolved:
1. **Observed Annotation Scale Distribution:** What are the empirical spatial footprints (equivalent diameter, pixel area, bounding box extent) of annotated connected components on the canonical $256 \times 256$ grid of OPS-02?
2. **Edge-Censored Annotation Prevalence:** What proportion of annotated connected components intersect the tile boundary (`EDGE_CENSORED_OBSERVATION`), and how does size distribution differ when excluding boundary-contact components?
3. **Encoder Bottleneck Sampling Alignment:** Which classes have annotated components smaller than the 32-pixel ($3.2\text{ km}$) encoder bottleneck feature spacing, and how are these supported by multi-path skip connections?
4. **Architectural Receptive Field Scale Compatibility:** How do the multi-path theoretical receptive fields (19 pixels via skip to 563 pixels via bottleneck) and analytical Gaussian proxies compare to the spatial organization and empirical periodicity of annotation masks?

---

## 5. Readiness Assessment

| Readiness Criterion | Audit Finding | Status |
| :--- | :--- | :--- |
| **Data Availability** | Ground truth segmentation masks and metadata for all 132 TRAIN and 40 DEV tiles verified present on disk (`data/ops02/derived/`). | **SATISFIED** |
| **Dataset Lineage Lock** | Authoritative manifest locked to `data/ops02/manifests/ops02_physical_dataset_manifest_v1.json` (`F5480EA2...`). | **SATISFIED** |
| **Protocol Stability** | Canonical $256 \times 256$ grid, 100m pixel spacing, and ResNet18-UNet architecture are fully frozen and documented. | **SATISFIED** |
| **Prior Diagnostic Completion** | DIAG-01, DIAG-02, and DIAG-03 are formally closed with verified Level 5 audit artifacts on OPS-02. | **SATISFIED** |
| **Zero-Compute Invariant** | Analysis can be executed entirely on CPU in $< 60\text{ seconds}$ without GPU compute, training, or backward passes. | **SATISFIED** |
| **Firewall Integrity** | HOLDOUT (40 tiles) and Part III partitions are quarantined and firewalled. | **SATISFIED** |
| **Baseline Architecture Frozen** | ResNet18-UNet exact parameters (14,310,860) and layer dimensions are fully specified in `exp07_reference.py`. | **SATISFIED** |
| **Roadmap Alignment** | DIAG-04 is the next sequential roadmap item approved by C22-F, C22-H, C22-J, and DIAG-03. | **SATISFIED** |

**Dependency Verdict:** **`READY_WITH_PREREQUISITES`** (Prerequisites established: dataset lineage locked to OPS-02, manifest hashes verified, execution script data contract bound; execution authorization strictly pending).

---

## 6. Primary Question

> **DIAG-04 PRIMARY SCIENTIFIC QUESTION:**  
> *"Across the 12 canonical Ocean Sentinel taxonomy classes on the $256 \times 256$ (100m pixel, $25.6 \times 25.6\text{ km}$) grid, does the canonical ResNet18-UNet baseline architecture provide spatial and receptive-field scales (multi-path theoretical receptive fields from 19 pixels along shallow skip paths to 531–563 pixels through the bottleneck, and 32-pixel / 3.2 km encoder bottleneck sampling scale) that are demonstrably compatible, incompatible, or uncertain relative to the observed spatial structure and boundary extents of annotated connected components in the canonical training/development masks?"*

### Scientific Guardrails on Primary Question
- **DO NOT** assume spatial incompatibility causes poor model performance or explains low mIoU.
- **DO NOT** assume the 32-pixel bottleneck creates a hard detectability threshold.
- **DO NOT** infer physical oceanographic phenomenon dimensions merely from semantic annotation polygons.
- **DO NOT** conflate the unbounded theoretical dependency envelope ($563\text{ px}$) with available physical context inside a $256 \times 256$ crop.

---

## 7. Scope Control & Analysis Classification

To maintain rigorous scientific focus, all proposed analyses in DIAG-04 are formally classified into four mutually exclusive categories:

### A. PRIMARY ANALYSIS (Core Question)
- **Scale Synthesis Matrix:** Systematic comparison between observed annotation scale distributions (equivalent diameter, bounding box) and architectural scales (TRF across skip/bottleneck paths, bottleneck sampling scale).

### B. SECONDARY SUPPORTING ANALYSES
1. **Edge-Censored Support Quantification:** Proportion of annotated connected components touching tile boundaries (`EDGE_CENSORED_OBSERVATION`), quantified across parent scenes.
2. **Annotation Morphology Spatial Organization:** 2D spatial autocorrelation and radial Power Spectral Density (PSD) of binary annotation masks for structured classes (IWs, POW, WS, MCC), evaluated with spectral windowing sensitivity and explicitly labeled as mask morphology, not physical radar backscatter wavelength.
3. **Multi-Path Architectural TRF Profiling:** Layer-by-layer derivation of theoretical receptive field across all encoder stages and decoder skip fusion paths, reporting phase dependence.

### C. SENSITIVITY ONLY ANALYSES
1. **Censorship Sensitivity Analysis:** Stratified evaluation of component size distributions for strictly interior components ($E_i = 0$) versus all components including edge-censored ones ($E_i = 1$).
2. **Cluster Resampling Sensitivity:** Parent-cluster block bootstrap stability ($B \ge 1000$) across the 40 TRAIN and 12 DEV clusters (52 development clusters total) to demonstrate that findings are not driven by a single outlier acquisition.

### D. OUT OF SCOPE (Strictly Prohibited)
- **NO Model Training:** Zero epochs, zero minibatches, zero parameter updates.
- **NO Backward Passes or Optimization Measurements:** DIAG-04 does not compute gradient norms, loss landscapes, or empirical learned-weight ERFs (strictly reserved for DIAG-05).
- **NO HOLDOUT or Part III Access:** Quarantined partitions remain completely untouched.
- **NO Metric Mutation:** The primary evaluation metric (`dev_mIoU_phenomena` over classes 1..11) remains frozen.
- **NO Causal Overclaiming (`BLOCK-004`):** Scale mismatches cannot be claimed as the "root cause" of model failure.

---

## 8. Five Distinct Spatial Scale Concepts

To eliminate ambiguous "upper / lower scale" terminology, DIAG-04 formally defines and separates five distinct spatial scales:

```
+---------------------------------------------------------------------------------------+
| 1. DATA-WINDOW SCALE:         256 x 256 pixels = 25.6 x 25.6 km (Crop Aperture)      |
| 2. ARCHITECTURAL SAMPLING:    32 pixels = 3.2 km (Encoder Bottleneck Feature Spacing)  |
| 3. ARCHITECTURAL RF SCALE:    19 px (Skip) to 531-563 px (Bottleneck Path) (TRF)      |
| 4. OBSERVED ANNOTATION SCALE: Empirical dimensions of annotated connected components  |
| 5. INFERRED PHYSICAL SCALE:   True oceanographic phenomenon scale in nature          |
+---------------------------------------------------------------------------------------+
```

1. **DATA-WINDOW SCALE:** The spatial extent of the canonical cropped input tile ($256 \times 256$ pixels at 100m spacing = $25.6 \times 25.6\text{ km}$). Any component reaching the crop border is an `EDGE_CENSORED_OBSERVATION`; its observed size is bounded by the observation window.
2. **ARCHITECTURAL SAMPLING SCALE:** The spatial stride of feature maps across encoder stages ($2\times, 4\times, 8\times, 16\times, 32\times$). At Layer 4, features are spaced every 32 input pixels ($3.2\text{ km}$). This represents the spatial sampling density of deep semantic features, NOT a hard limit on target detectability.
3. **ARCHITECTURAL RECEPTIVE FIELD SCALE:** The spatial support over which input pixels can mathematically contribute to an output activation. In ResNet18-UNet, skip connections create a multi-scale spectrum from 19 pixels ($1.9\text{ km}$, shallow skip) to 531–563 pixels ($53.1\text{ to }56.3\text{ km}$, bottleneck path).
4. **OBSERVED ANNOTATION SCALE:** The geometric dimensions (pixel area, equivalent diameter, bounding box) of annotated connected components within the $256 \times 256$ label raster.
5. **INFERRED PHYSICAL SCALE:** The true physical dimensions of the oceanic phenomenon in nature. This scale can only be inferred when external oceanographic metadata or physical domain theory confirms instance boundaries.

---

## 9. Receptive Field Concepts & ConvTranspose2d Mathematical Identity

### 9.1 Exact ConvTranspose2d Index Propagation
In PyTorch, for a transpose convolution with kernel size $k$, stride $s$, and padding $p$, an output element $i$ receives contributions from input elements $j$ satisfying:
$$j \in \mathbb{Z} \quad \text{and} \quad \left\lceil \frac{i + p - k + 1}{s} \right\rceil \le j \le \left\lfloor \frac{i + p}{s} \right\rfloor$$
In the ResNet18-UNet decoder (`exp07_reference.py`), all transpose convolutions use $k=2, s=2, p=0$:
$$\left\lceil \frac{i - 1}{2} \right\rceil \le j \le \left\lfloor \frac{i}{2} \right\rfloor \implies j = \left\lfloor \frac{i}{2} \right\rfloor$$
**Every single output pixel $i$ depends on EXACTLY ONE input pixel $\lfloor i/2 \rfloor$ in ConvTranspose2d.**

### 9.2 Layer-by-Layer Computational Graph Dependencies

```
INPUT: [B, 1, 256, 256] float32

ENCODER:
  conv1:       k=7, s=2, p=3  -> x0 [B, 64, 128, 128]  | TRF = 7,   stride = 2
  maxpool:     k=3, s=2, p=1  -> xp [B, 64, 64, 64]    | TRF = 11,  stride = 4
  layer1:      4 x (3x3, s=1) -> x1 [B, 64, 64, 64]    | TRF = 43,  stride = 4  (Skip to dec2)
  layer2:      4 x (3x3), s=2 -> x2 [B, 128, 32, 32]   | TRF = 99,  stride = 8  (Skip to dec3)
  layer3:      4 x (3x3), s=2 -> x3 [B, 256, 16, 16]   | TRF = 211, stride = 16 (Skip to dec4)
  layer4:      4 x (3x3), s=2 -> x4 [B, 512, 8, 8]     | TRF = 435, stride = 32 (Bottleneck)

DECODER FUSION & MULTI-PATH SPANS:
  - Path A (via x0 skip):   Output pixel -> head (1x1) -> final_conv (5x5 span) -> final_up (3x3 span in d1)
                            -> dec1.conv (7x7 span in x0) -> conv1 (19x19 span in X).
                            Span: EXACTLY 19 PIXELS (Phase-invariant).
  - Path B (via x1 skip):   d1 (7x7 span) -> dec1.up (4x4 span in d2) -> dec2.conv (8x8 span in x1)
                            -> layer1 (71x71 span in X).
                            Span: EXACTLY 71 PIXELS (Phase-invariant).
  - Path C (via x2 skip):   d2 (8x8 span) -> dec2.up (4 or 5 span in d3) -> dec3.conv (8 or 9 span in x2)
                            -> layer2.
                            Span: 155 to 163 PIXELS (Phase-dependent).
  - Path D (via x3 skip):   d3 (8 or 9 span) -> dec3.up (4 or 5 span in d4) -> dec4.conv (8 or 9 span in x3)
                            -> layer3.
                            Span: 323 to 339 PIXELS (Phase-dependent).
  - Path E (bottleneck x4): d4 (8 or 9 span) -> dec4.up (4 or 5 span in x4) -> layer4.
                            Span: 531 to 563 PIXELS (Phase-dependent).
```

### 9.3 Receptive Field Semantic Partition
- **A. Encoder Bottleneck TRF:** Exactly 435 pixels at stride 32.
- **B. Multi-Path Decoder TRFs:** 19 px ($x_0$), 71 px ($x_1$), [155, 163] px ($x_2$), [323, 339] px ($x_3$), [531, 563] px ($x_4$).
- **C. Computational Graph Reachability Envelope:** 531–563 pixels in an infinite, unbounded grid.
- **D. Crop-Clipped Usable Context:** On a $256 \times 256$ tile, any theoretical reachability outside $[0, 255]$ is padded or masked. The maximum physical ground context available to any output pixel is strictly bounded by the $256 \times 256$ ($25.6 \times 25.6\text{ km}$) observation aperture (`LL-EXP07-028`).
- **E. Effective Receptive Field (ERF):** Unmeasured in DIAG-04 (`BLOCK-006`).

---

## 10. Connected Component Semantics & Edge Censorship

### 10.1 Connected Component $\neq$ Physical Instance
- In semantic segmentation of SAR imagery, a single physical phenomenon (e.g., an internal wave packet, a fragmented biological slick, or a distributed rain squall) frequently manifests as multiple disconnected polygons in ground truth annotations.
- Conversely, a single annotated polygon may encompass multiple coalesced physical structures.
- **Plan Mandate:** DIAG-04 uses strictly neutral terminology: **"annotated connected component"** or **"annotated region"**. It does **NOT** refer to connected components as "physical instances" unless external instance metadata explicitly establishes identity.

### 10.2 Edge Censorship: `EDGE_CENSORED_OBSERVATION`
- A component touching the $256 \times 256$ crop border proves only:
  *"The observed annotated support reaches the crop boundary."*
- It does **NOT** prove:
  - that the physical phenomenon exceeds $25.6\text{ km}$;
  - that the phenomenon was truncated (it may naturally terminate 10 meters outside the tile, or extend for 50 km);
  - that the bounding box represents true physical length.
- **Plan Mandate:** All boundary-contact components are formally designated as **`EDGE_CENSORED_OBSERVATION`** ("bounded by crop boundary").
- Size distributions must report:
  1. Uncensored component statistics ($E_i = 0$, strictly interior);
  2. Edge-censored component counts ($E_i = 1$);
  3. Sensitivity comparison between uncensored and combined sets.
  No ad-hoc correction multipliers may be applied without empirical evidence.

---

## 11. Measurement Categorization & Semantic Audit

Every measurement planned in DIAG-04 is audited and classified into its precise scientific domain:

| Measurement Metric | Mathematical Quantity | Formal Category | Valid Scientific Interpretation | Prohibited Overclaim |
| :--- | :--- | :--- | :--- | :--- |
| **Pixel Area ($A_i$)** | $\sum_{(r,c) \in C_i} 1$ | ANNOTATION GEOMETRY | Observed pixel support of annotation component within tile. | "Physical surface area of oceanic phenomenon." |
| **Equivalent Diameter ($D_{\text{eq}, i}$)** | $2 \sqrt{A_i / \pi} \times 100\text{ m}$ | PROXY / ANNOTATION GEOMETRY | Circularized geometric scale proxy of 2D annotation footprint. | "True physical diameter of phenomenon." |
| **Bounding Box ($W_i, H_i$)** | $\max(c) - \min(c) + 1$ | ANNOTATION GEOMETRY | Raster bounding extent within tile aperture. | "Full physical length/width of phenomenon." |
| **Major Axis Length ($L_{\text{maj}, i}$)** | Maximum convex hull caliper | ANNOTATION GEOMETRY | Maximum 2D elongation of annotated mask region. | "Physical crest length or frontal extent." |
| **Boundary Complexity ($P_i^2 / 4\pi A_i$)** | Isoperimetric quotient | ANNOTATION GEOMETRY | Compactness vs thinness/filamentation of annotation boundary. | "Turbulent fractal dimension of ocean surface." |
| **Edge Intersection ($E_i \in \{0, 1\}$)** | Touch row/col $0$ or $255$ | ANNOTATION GEOMETRY | Flag for `EDGE_CENSORED_OBSERVATION`. | "Proof phenomenon exceeds 25.6 km." |
| **Mask 2D Radial PSD** | $|\mathcal{F}\{\text{mask} \cdot w\}|^2$ | ANNOTATION MORPHOLOGY PROXY | Spatial periodicity and layout of human annotation polygons. | "Physical radar backscatter wavelength." |
| **Theoretical RF (TRF)** | Exact recursive formula | ARCHITECTURAL SCALE | Maximum mathematical dependency extent of network graph. | "Effective receptive field of trained model." |
| **Bottleneck Stride** | $32\times = 3.2\text{ km}$ | ARCHITECTURAL SAMPLING SCALE | Feature grid sampling interval at encoder bottleneck. | "Hard lower-bound detection limit." |

---

## 12. 2D Power Spectral Density (PSD) Analysis Controls

### 12.1 Input Data Specification
- In DIAG-04, 2D PSD is evaluated on **binary semantic annotation masks** (with optional masked SAR intensity exploratory checks).
- It is explicitly designated as **"annotation morphology / spatial organization analysis"**, NOT "physical wave spectrum analysis".
- Determining physical sea surface backscatter wavelength requires continuous calibrated SAR intensity spectrum inversion, which is a distinct physical analysis outside DIAG-04 scope.

### 12.2 Methodological Controls & Technical Limitations
1. **Finite Window Resolution:** On a $256 \times 256$ grid at 100m spacing ($L = 25.6\text{ km}$), the fundamental spatial frequency resolution is:
   $$\Delta k = \frac{1}{25.6\text{ km}} \approx 0.039\text{ km}^{-1} \quad (\Delta \lambda \text{ is coarse at long wavelengths})$$
2. **Hann Windowing:** Applied prior to 2D FFT to suppress boundary discontinuities. Hann windowing broadens spectral peaks by $\approx 1.5\times$, reducing apparent frequency resolution.
3. **Sparse Binary Mask Leakage:** Sparse binary masks (e.g., thin slicks, small isolated cells) have sharp step edges that generate high-frequency sinc leakage, which can produce spurious high-wavenumber energy unrelated to physical periodicity.
4. **Peak Stability & Continuous Prominence Criterion:**
   - Instead of an arbitrary fixed threshold (e.g., "3 dB"), spatial periodicity requires demonstrated **spectral peak stability**:
     a. Verification of a distinct local maximum with negative second difference;
     b. Peak wavenumber stability across spectral tapering windows ($< 15\%$ wavenumber shift between Hann, Hamming, and Blackman tapers);
     c. Monotonically decreasing power spectra are classified as **`BROADBAND_MONOTONIC`**;
     d. Prominence above local median continuum is reported continuously as a sensitivity curve, not an arbitrary step decision.
5. **Anisotropy:** Ocean waves and wind streaks are highly directional. Radially averaged PSD averages out directional peaks. Directional 2D spectra must be inspected before asserting isotropic wavelengths.

---

## 13. Data Contract & Authoritative Manifests

```yaml
data_contract:
  dataset_identifier: "OPS-02"
  dataset_version: "OPS02_v1.0.1_FROZEN (Level 5 Canonical Physical Dataset Specification)"
  freeze_specification: "data/ops02/OPS02_DATASET_FREEZE_SPEC_v1.0.1.json"
  freeze_specification_sha256: "3B362DECD210679DCC7BF5EB6879A020416E4A8BB780845F3FCC59A4DFBF3B35"
  authoritative_physical_manifest: "data/ops02/manifests/ops02_physical_dataset_manifest_v1.json"
  authoritative_physical_manifest_sha256: "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"
  partition_manifest: "data/ops02/manifests/ops02_partition_manifest_v1.json"
  partition_manifest_sha256: "757DEAF7A7E72BE331843B518A99AF32E14D68A080822F1D9B4FDBADF889F94D"
  parent_cluster_manifest: "data/ops02/manifests/ops02_parent_cluster_manifest_v1.json"
  parent_cluster_manifest_sha256: "08ED21FBB492363E1D05040020F73177BFD4DC84F1A39E2D9C5C9B38BC97D10B"
  authorized_partitions:
    - "TRAIN (data/ops02/derived/images, masks)"
    - "DEV (data/ops02/derived/images, masks)"
  strictly_forbidden_partitions:
    - "HOLDOUT (quarantined across 40 tiles / 12 parent clusters)"
    - "PART_III (quarantined external evaluation)"
  grid_specifications:
    dimensions_pixels: [256, 256]
    nominal_pixel_spacing_meters: 100.0
    spatial_coverage_km: [25.6, 25.6]
    coordinate_reference: "Local patch raster space (row, col)"
  input_data_files:
    derived_image_pattern: "data/ops02/derived/images/*.tif"
    derived_mask_pattern: "data/ops02/derived/masks/*.png"
  normalization_constants:
    train_log1p_mean: 4.424158
    train_log1p_std: 0.469261
  sample_counts:
    total_physical_tiles: 212
    total_independent_parent_clusters: 64
    total_mission_datatakes: 64
    total_constituent_level1_scenes: 85
    train_tiles: 132
    train_parent_clusters: 40
    dev_tiles: 40
    dev_parent_clusters: 12
    holdout_tiles: 40
    holdout_parent_clusters: 12
    accessible_development_tiles: 172
    accessible_development_clusters: 52
```

---

## 14. Statistical Independence & Cluster Design

- **Unit of Scientific Independence:** Parent acquisition mission datatake cluster ($K$), defined by Sentinel-1 datatake clustering (`GOV-RULE-077`).
- **Cluster Counts:**
  - TRAIN: $K=40$ independent acquisition clusters (132 tiles).
  - DEV: $K=12$ independent acquisition clusters (40 tiles).
  - Development Total: $K=52$ independent clusters (172 tiles).
- **DEV Class Support per Parent Cluster ($K$) & Empirical Frequencies (OPS-02 DEV):**
  - $K=1$ (Descriptive Only; CIs prohibited under `GOV-RULE-101`):
    - `OF` ($K=1$ cluster, 1 tile, 1,709 valid pixels)
    - `RF` ($K=1$ cluster, 2 tiles, 9,550 valid pixels)
  - $K=2$ (Extreme Uncertainty Caveat; CIs reported with severe caution flag):
    - `BS` ($K=2$ clusters, 4 tiles, 123,771 valid pixels)
    - `WS` ($K=2$ clusters, 3 tiles, 131,037 valid pixels)
    - `Eddy` ($K=2$ clusters, 5 tiles, 45,322 valid pixels)
  - $K=3$:
    - `AF` ($K=3$ clusters, 6 tiles, 39,385 valid pixels)
    - `LWA` ($K=3$ clusters, 4 tiles, 58,567 valid pixels)
    - `POW` ($K=3$ clusters, 3 tiles, 78,415 valid pixels)
    - `HM` ($K=3$ clusters, 3 tiles, 117 valid pixels)
  - $K=7$:
    - `MCC` ($K=7$ clusters, 17 tiles, 853,315 valid pixels)
  - $K=9$:
    - `IWs` ($K=9$ clusters, 31 tiles, 579,526 valid pixels)
  - $K=10$:
    - `BG` ($K=10$ clusters, 28 tiles, 643,805 valid pixels)
- **Pseudo-Replication Prohibition (`BLOCK-009`):** Individual pixels and individual annotated connected components from the same parent acquisition cluster are spatially autocorrelated.
- **Exhaustive Component Extraction:** Extracting all components across 172 development tiles is an **exhaustive descriptive enumeration** of the dataset, NOT a sample of thousands of independent scientific observations.
- **Resampling:** When confidence intervals are computed for mean component properties, they must use **parent-cluster block bootstrap** ($B \ge 1000$). For $K=1$ strata (OF, RF), bootstrap resampling across clusters is degenerate; between-cluster CIs are strictly suppressed.

---

## 15. Evidence Levels & Scientific Inference Rules

Every finding in DIAG-04 must be assigned an explicit evidence level:

| Evidence Level | Definition | Acceptable in DIAG-04? | Example Statement |
| :--- | :--- | :--- | :--- |
| `OBSERVED` | Direct mathematical or geometric measurement on the data or architecture. | **YES** | "In TRAIN annotations, 82% of MCC connected components touch the tile boundary." |
| `SUPPORTED` | Descriptive correspondence supported by multiple geometric and architectural metrics. | **YES** | "HM component equivalent diameters (1-3 px) are sub-scale relative to the 32-pixel bottleneck sampling stride, but fully contained within the 19-pixel skip path receptive field." |
| `PLAUSIBLE` | Hypothesis logically consistent with observations but not definitively established. | **YES** | "It is plausible that large mesoscale MCC structures are incompletely represented within single 25.6 km crops." |
| `CAUSAL_ESTABLISHED` | Proven causal mechanism validated through single-variable intervention. | **STRICTLY PROHIBITED** | Prohibited assertion: *"Spatial mismatch proves why mIoU is low on HM."* (`BLOCK-004`). |

### Prohibited Shortcut Inferences
1. Observed spatial mismatch $\rightarrow$ proved cause of model failure.
2. 32-pixel bottleneck stride $\rightarrow$ hard detection limit or proof of information loss.
3. Touching tile border $\rightarrow$ proof phenomenon exceeds 25.6 km.
4. Binary mask periodicity $\rightarrow$ physical sea surface backscatter wavelength.
5. Small object size $\rightarrow$ proof network cannot detect it.
6. 563 px theoretical graph envelope $\rightarrow$ 563 px of available physical context inside a 256 px tile.
7. Radiometric overlap $\rightarrow$ proof that 2D spatial context is necessary.
8. DIAG-04 findings $\rightarrow$ explanation of low mIoU.
9. Spatial-scale mismatch $\rightarrow$ proved model failure cause.

---

## 16. Failure-Mode Threat Model

| Risk Category | Potential Failure Mechanism | Preventive Control |
| :--- | :--- | :--- |
| **A. Data Leakage** | Accidentally scanning HOLDOUT or Part III masks. | Pre-execution assertion verifying sample partitions strictly match `partition in ['TRAIN', 'DEV']`. |
| **B. Pseudoreplication** | Treating 1,000 components from the same parent scene as independent. | Block bootstrap at parent-scene level ($K$). |
| **C. Censorship Bias** | Treating edge-touching components as unbiased physical size measurements. | Report uncensored ($E_i=0$) and edge-censored ($E_i=1$) separately; designate edge contact as `EDGE_CENSORED_OBSERVATION`. |
| **D. Metric Pathology** | Conflating high edge truncation with low performance without checking cluster counts. | Report class support $K$ alongside truncation rates; label $K \le 2$ as inconclusive. |
| **E. Semantic Conflation** | Equating connected components with physical phenomenon instances. | Restrict language to "annotated connected component". |
| **F. Spectral Overclaim** | Claiming mask PSD represents physical radar backscatter wavelength. | Label PSD strictly as "annotation morphology / spatial organization". |
| **G. Crop Context Overclaim** | Claiming 563 px TRF means the model sees 563 px of ground context. | State explicitly that usable context is clipped by the $256 \times 256$ crop border (`LL-EXP07-028`). |
| **H. Arbitrary Cutoff** | Using an unjustified "3 dB over background" threshold. | Replace with multi-taper peak stability and continuous prominence reporting. |
| **I. Governance Tripwire** | Calling PyTorch `backward()` to compute ERF, tripping `BLOCK-006`. | Restrict diagnostic to architecture-only TRF and analytical Gaussian proxy; explicitly state true ERF is unmeasured. |
| **J. Terminology Drift** | Referring to HM as "vessel" or OF as "oil spill". | Automated terminology filter enforcing canonical names (`BLOCK-008`). |
| **K. Causal Overclaiming** | Unsubstantiated causal assertions linking spatial dimensions to model performance. | Enforce non-causal language ("is associated with", "observed mismatch", "HYPOTHESIZED") (`BLOCK-004`). |

---

## 17. Expanded Contingency Matrix

| Contingency Scenario | Trigger Condition | Operational & Analytical Response | Stop Condition | Scientific Consequence |
| :--- | :--- | :--- | :--- | :--- |
| **1. All components touch tile boundary** | 100% of components for class $c$ have $E_i = 1$. | Report uncensored size distribution as EMPTY; report observed bounding box as lower bound; flag as fully censored. | Do not abort. | Class spatial extent is unconstrained by $256 \times 256$ tile aperture. |
| **2. Class contains only tiny components** | 100% of components have $A_i \le 4\text{ pixels}$ (e.g., HM). | Report discrete pixel histogram; analyze overlap with 19-pixel skip RF vs 32-pixel bottleneck stride. | Do not abort. | Confirms feature is sub-scale for bottleneck sampling; relies on skip connections. |
| **3. Insufficient cluster support ($K \le 2$)** | Class appears in $K=1, 2$ parent scenes in DEV (LWA, RF, WS, Eddy, AF, BS, OF, POW). | $K=1$: descriptive only, suppress CIs. $K=2$: flag extreme uncertainty. | Do not abort. | Population-level scale compatibility is declared `INCONCLUSIVE_INSUFFICIENT_K`. |
| **4. Disconnected components cannot map to instances** | Multi-component annotations in single scenes (e.g., IWs, BS). | Treat each 8-connected polygon strictly as an annotated connected component; do not attempt heuristic clustering. | Do not abort. | Findings apply to annotation morphology, not physical instance size. |
| **5. PSD has no stable spectral peak** | Radial PSD is monotonically decreasing or peak shifts $> 15\%$ across tapering windows. | Classify class as `BROADBAND_MONOTONIC`; report spectral slope; do not force harmonic peak. | Do not abort. | Conclude annotation lacks characteristic spatial wavelength. |
| **6. PSD peak changes with windowing/grid** | Peak wavenumber shifts $> 15\%$ between Hann, Hamming, and Blackman windows. | Report peak sensitivity range; declare wavelength estimate unstable. | Do not abort. | Periodicity is flagged as artifact of finite windowing rather than robust spatial pattern. |
| **7. Analytical ERF proxy disagrees with TRF** | Gaussian ERF proxy ($4\sigma$) covers $< 20\%$ of TRF. | Report both values explicitly; explain that TRF is mathematical support while Gaussian proxy is central tendency under random weights. | Do not abort. | Highlights distinction between maximum dependency and effective sensitivity. |
| **8. Multi-path UNet architecture dependency** | Output pixel receives inputs via both skip ($19\text{ px}$) and bottleneck ($531-563\text{ px}$) paths. | Report multi-scale RF profile across all 5 paths; do not reduce architecture to a single scalar RF. | Do not abort. | Demonstrates that UNet possesses multi-scale spatial processing capability. |
| **9. Actual architecture differs from roadmap description** | Inspection reveals Layer 4 TRF is 435 px (not 483 px). | Update all diagnostic artifacts to authoritative implementation value (435 px). | Do not abort. | Corrects documentation errata without impacting runtime execution. |
| **10. Proposed metric cannot support interpretation** | Metric requires assumptions violated by data (e.g., assuming mask PSD = physical backscatter wavelength). | Re-label metric to its true descriptive scope ("annotation layout periodicity"); state exact boundary. | Do not abort. | Preserves scientific defensibility of published claims. |

---

## 18. Reproducibility & Governance Contract

- **Execution Script:** `scripts/analyze_exp07_diag04_spatial_scale_compatibility.py`
- **RNG Seeds:** Fixed seed `42` for bootstrap resampling.
- **Python Environment:** `.venv` (Python 3.10.9, `numpy`, `scipy`, `torch`, `rasterio`).
- **Command Line:** `.venv\Scripts\python scripts/analyze_exp07_diag04_spatial_scale_compatibility.py`
- **Output Artifacts:**
  - Machine-readable audit JSON: `data/ops02/audits/ops02_diag04_spatial_scale_compatibility_v1.json`
  - Narrative report: `experiments/EXP-07/EXP07_P0_DIAG04_RECEPTIVE_FIELD_SCALE_COMPATIBILITY_20260915.md`
  - Run state telemetry: `scratch/exp07_p0_diag04_run_state.json`

```yaml
governance_verification:
  preflight_receipt_valid: true
  receipt_path: "scratch/agent_governance_preflight_receipt.json"
  task_category: "diagnostic"
  training_steps: 0
  backward_passes: 0
  optimizer_steps: 0
  scheduler_steps: 0
  parameter_updates: 0
  gpu_seconds: 0.0
  holdout_access: 0
  part_iii_access: 0
  diag04_executed: false
  diag05_executed: false
  zero_destructive_git: true
  working_tree_clean_except_tracked: true

machine_execution_data_contract:
  dataset_id: "OPS-02"
  freeze_spec: "OPS02_v1.0.1_FROZEN"
  manifest_path: "data/ops02/manifests/ops02_physical_dataset_manifest_v1.json"
  manifest_sha256: "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"
  train_tile_count: 132
  dev_tile_count: 40
  holdout_tile_count: 40
  development_tile_count: 172
  development_cluster_count: 52
  fail_closed_triggers:
    - "manifest hash differs"
    - "manifest path differs"
    - "partition counts differ"
    - "unexpected dataset identifier appears"
    - "HOLDOUT appears in selected analysis population"
    - "Part III paths appear"
```

---

## 19. Applicable Historical Lessons

The hardened plan complies with all applicable institutional lessons:
- `LL-EXP07-001`: Quantitative assertions must derive directly from machine JSON (`GOV-RULE-100`).
- `LL-EXP07-002` / `LL-C22B-004`: Canonical class nomenclature enforced (`HM`, `OF`).
- `LL-EXP07-007`: Standard PyTorch tensor shape notation `[B, 1, 256, 256]` and canonical grid geometry ($256 \times 256$ at 100m, 25.6 km).
- `LL-EXP07-008` / `LL-DIAG03-006`: Non-causal observational language on descriptive data (`BLOCK-004`).
- `LL-C22F-001`: Sparse class support framed as estimator variance, not mathematical capping.
- `LL-C22F-004`: Scale mismatch framed as testable descriptive hypothesis.
- `LL-C22J-001`: Zero unsupported gradient claims; diagnostics strictly maintain `backward_passes == 0` (`BLOCK-006`).
- `LL-C22J-004`: Diagnostic roadmap integrity preserved (DIAG-04 precedes DIAG-05).
- `LL-DIAG03-001` / `LL-EXP07-019`: Parent acquisition clustering mandatory for statistical inference (`BLOCK-009`).
- `LL-EXP07-027`: Independence counts derived directly from frozen physical manifest.
- `LL-EXP07-028`: Distinction between unbounded theoretical dependency envelope and crop-clipped context; multi-path RF reporting.
- `LL-DIAG04-PLAN-001`: Strict verification of 256x256 grid dimensions; rejection of legacy 512x512 drafts.
- `LL-DIAG04-PLAN-002`: Zero backward passes in diagnostics; analytical or forward-only ERF calculation.
- `LL-DIAG04-PLAN-003`: Diagnostic dataset continuity across roadmap investigations (OPS-02 canonicality locked).
- `LL-GOV-001`: Cryptographic preflight receipt required.
- `LL-GOV-002`: Semantic paraphrase causal blocking enforced.

---

## 20. Final Authorization Gate

> [!IMPORTANT]
> **DIAG-04 SCIENTIFIC EXECUTION HAS NOT OCCURRED.**  
> **DIAG-04 EXECUTION AUTHORIZATION: NOT GRANTED.**  
>  
> This document represents a complete, hardened, peer-reviewed pre-execution implementation plan. Scientific execution requires explicit, separate user authorization.
