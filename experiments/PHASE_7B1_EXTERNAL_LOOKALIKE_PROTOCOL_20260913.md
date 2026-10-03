# OCEAN SENTINEL — PHASE 7B.1 SCIENTIFIC PROTOCOL PRE-REGISTRATION
**Document Identifier:** `PHASE_7B1_EXTERNAL_LOOKALIKE_PROTOCOL_20260913`  
**Governing Role:** Senior CAO Scientific Benchmark / Data Governance Auditor and Implementation Engineer  
**Date:** September 13, 2026  
**Status:** **AUTHORITATIVE PHASE 7B.1 PROTOCOL & FORENSIC DISCOVERY SPECIFICATION**  
**Associated Artifacts:**
- [external_lookalike_benchmark_matrix.json](file:///d:/Projects/ocean-sentinel/data/metadata/external_lookalike_benchmark_matrix.json)
- [PHASE_7B0_CORRECTION_ADDENDUM_20260913.md](file:///d:/Projects/ocean-sentinel/experiments/PHASE_7B0_CORRECTION_ADDENDUM_20260913.md)
- [PHASE_7B0_EXTERNAL_LOOKALIKE_BENCHMARK_AUDIT_20260913.md](file:///d:/Projects/ocean-sentinel/experiments/PHASE_7B0_EXTERNAL_LOOKALIKE_BENCHMARK_AUDIT_20260913.md)

---

## 1. GOVERNANCE CHARTER & STRICT OPERATIONAL BOUNDARIES

This protocol governs the forensic audit, leakage screening, and pre-registration of evaluation protocols for external look-alike and ocean phenomena datasets.

> [!CAUTION]
> ### STRICT GOVERNANCE INVARIANTS (PHASE 7B.1)
> 1. **EXP-07 Model Training:** **STRICTLY FORBIDDEN**. Zero training runs, fine-tuning, or parameter updates are authorized.
> 2. **Candidate Mining / Model Selection:** **FORBIDDEN**. No candidate model may be trained or selected.
> 3. **Threshold Calibration / Search:** **FORBIDDEN**. The operational decision threshold is frozen at $\tau = 0.22$. ROC sweeps, PR optimizations, or benchmark-specific thresholds are prohibited.
> 4. **Model Checkpoint Immutability:** The EXP-06 checkpoint is cryptographically frozen at:
>    `experiments/performance/exp06_positive_bce_weight/best_model.pt`  
>    $$\mathbf{SHA\text{-}256:}\ \mathtt{B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF}$$
> 5. **Internal Split Protection:** Part-I Internal Development Split Manifest (`data/metadata/internal_development_split_manifest.json`) is bitwise frozen (SHA-256: `17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072`).
> 6. **Quarantine Firewall:** Trujillo Part III is **PERMANENTLY QUARANTINED** under Rule 38. Zero access to Part III images or masks is permitted.
> 7. **Proxy Status:** The 517 physically validated DARTIS proxy candidates remain **SEMANTICALLY UNRESOLVED** (`PROVISIONAL_PROXY_DIAGNOSTIC_ONLY`). They cannot be converted into an official False Alarm Rate (FAR).

---

## 2. AUTHORITATIVE FORENSIC AUDIT OF LI ET AL. (2024/2025)

The primary candidate audited is the Sentinel-1 Typical Oceanic and Atmospheric Phenomena Semantic Segmentation Dataset:
- **Repository:** Zenodo Record `14279466` (Version 2, December 7, 2024)
- **DOI:** [`10.5281/zenodo.14279466`](https://doi.org/10.5281/zenodo.14279466)
- **Peer-Reviewed Reference:** Li, Q., Bai, X., Hu, L., Li, L., Bao, Y., Geng, X., & Yan, X.-H. (2025). *Semantic Segmentation of Typical Oceanic and Atmospheric Phenomena in SAR Images Based on Modified Segformer*. **Remote Sensing**, 18(1), 113. https://doi.org/10.3390/rs18010113.
- **Preprint:** Earth System Science Data (ESSD), https://doi.org/10.5194/essd-2024-222.
- **License:** Creative Commons Attribution 4.0 International (CC-BY-4.0).
- **Archive Checksum:** `Sentinel-1 oceanic and atmospheric Phenomena dataset_V2.rar` ($818,667,409\text{ bytes}$, MD5: `5bf6e338dd2a686de5ecd5fee3e139cd`).

### 2.1 Verified Physical & Sensor Properties

Direct machine-reading of the archive table of contents, GeoTIFF IFD tags, and image rasters established:
1. **Total Population:** Exactly **5,011 image slices** with corresponding palette-indexed PNG masks.
2. **Dual-Mode Composition:**
   - **Interferometric Wide (IW) Mode:** **2,628 sub-images** (52.44%) derived from **484 unique source scenes** acquired between 2015-02-20 and 2023-01-28.
   - **Wave Mode (WV):** **2,383 vignettes** (47.56%) comprising **1,731 WV1 vignettes** (steep incidence angle $\sim 23^\circ$) and **652 WV2 vignettes** (mid incidence angle $\sim 36^\circ$).
3. **Polarization:** **100% Single-Polarization VV**. Exactly 5,011 / 5,011 slices are VV (`s1a-...-vv-...`). Zero VH channels exist in the distributed files.
4. **Spatial Resolution & Dimensions:**
   - Dimensions: Exactly **$256 \times 256$ pixels**.
   - Pixel Size: Exactly **$100\text{ m}$** ($10\times$ downsampled from native $10\text{ m}$ Sentinel-1 GRD).
   - Geographic Coverage per Slice: **$25.6\text{ km} \times 25.6\text{ km}$** (vs. Ocean Sentinel's $5.12\text{ km} \times 5.12\text{ km}$).
5. **Radiometric Representation:**
   - Distributed as unsigned 16-bit integers (`uint16`, range $[0, 65535]$).
   - Generated via an internal pipeline: $\text{Radiometric Calibrate} \to \text{Down-sample} \to \text{Sea-Land Mask} \to \text{Re-calibration} \to \text{Normalization}$.
   - No inverse calibration function or physical float32 $\sigma^0$ conversion tables are provided.
6. **Georeferencing:**
   - Tag 33922 (`ModelTiepointTag`) stores 4 corner Ground Control Points (GCPs).
   - GeoTIFF `CRS` tag is `None`. Rasterio reads affine transform as identity $(1.0, 1.0)$. Geographic coordinates must be derived from corner tiepoints.

---

## 3. SENSOR & CANONICAL PREPROCESSING COMPATIBILITY FIREWALL

### 3.1 The Canonical EXP-06 Input Contract

Inspection of the frozen EXP-06 inference pipeline (`src/ocean_sentinel/ingestion/dataset.py`, `scripts/evaluate_exp06_dev_baseline.py`, and `data/metadata/trujillo_2024/spatial_split_manifest.json`) codifies the canonical contract:
- **Input Channels:** Dual-polarization 2-channel tensor: `Channel 0` (VH), `Channel 1` (VV).
- **Physical Units:** Decibels ($\text{dB}$) of calibrated backscatter: $\sigma^0_{\text{dB}} = 10 \cdot \log_{10}(\sigma^0 + 10^{-7})$.
- **Normalization (Z-Score Standardization):**
  $$\text{norm\_ch0} = \frac{x_0 - (-33.233136989478695)}{6.489985665955077}$$
  $$\text{norm\_ch1} = \frac{x_1 - (-19.941215852796695)}{4.531345684833188}$$
- **Spatial Grid:** $512 \times 512$ pixels at native $10\text{ m}$ resolution. Tensor shape: `torch.float32`, `(2, 512, 512)`.
- **Decision Rule:** Sigmoid logit activation followed by frozen threshold $\tau = 0.22$.

### 3.2 Compatibility Comparison & Disposition

| Physical Dimension | Canonical EXP-06 Contract | Li et al. (2024/2025) Distributed Data | Compatibility Disposition |
| :--- | :--- | :--- | :--- |
| **Sensor Frequency** | C-band ($5.55\text{ cm}$) | C-band ($5.55\text{ cm}$) | **COMPATIBLE** |
| **Observation Mode** | IW GRDH Swath Mode | 52.4% IW, 47.6% WV | **PARTIAL MISMATCH (WV mode incompatible)** |
| **Polarization Channels** | Dual-channel: (VH, VV) | Single-channel: VV only (100%) | **FATAL MISMATCH (Channel 0 missing)** |
| **Spatial Resolution** | $10\text{ m}$ native GRD | $100\text{ m}$ downsampled | **FATAL MISMATCH ($10\times$ missing high-frequency)** |
| **Array Dimensions** | $512 \times 512$ ($5.12\text{ km}$) | $256 \times 256$ ($25.6\text{ km}$) | **FATAL MISMATCH ($25\times$ footprint area difference)** |
| **Radiometric Units** | Float32 decibels (dB) | Scaled unsigned 16-bit int (`uint16`) | **FATAL MISMATCH (Quantized image intensity)** |
| **Z-Score Normalization** | Training stats $[\mu_0, \mu_1]$ | Unknown internal scaling | **FATAL MISMATCH (Non-invertible)** |

> [!IMPORTANT]
> ### FORMAL SCIENTIFIC DISPOSITION
> The distributed Li et al. dataset is:
> $$\mathbf{METHODOLOGICALLY\ USEFUL}$$
> $$\mathbf{BUT\ NOT\ DIRECTLY\ SUITABLE\ FOR\ ZERO-SHOT\ EXP-06\ EVALUATION.}$$
> 
> Direct evaluation of EXP-06 on the $100\text{ m}$ `uint16` slices would violate the physical observation contract of the model, generating spurious artifacts from missing VH backscatter and extreme spatial blur. No synthetic upsampling or arbitrary channel duplication will be performed.

---

## 4. LINEAGE & LEAKAGE SCREENING AUDIT

### 4.1 Upstream Source Lineage
The Li dataset is a derived compilation incorporating:
1. **TenGeoP-SARwv:** 2,383 Wave Mode vignettes from Wang et al. (2019/2022) (*Geoscience Data Journal*, SEANOE DOI: `10.17882/81577`). Originally single-label classification; annotated with pixel-level polygons by Li et al.
2. **IWs Dataset:** 156 Sentinel-1 IW scenes from Tao et al. (2022) (*Earth and Space Science*, figshare DOI: `10.6084/m9.figshare.21365835.v3`). Originally bounding-box object detection; segmented into pixel-level wave crest polygons by Li et al.
3. **Curated IW Scenes:** 328 additional Sentinel-1 IW scenes selected by Li et al. (2015–2022) covering coastal and open-sea phenomena.

### 4.2 Leakage Screening Results
- **Overlap with DARTIS Proxy Population:** Exactly **0 shared parent products** (DARTIS surveyed Eastern Mediterranean in 2019; Li et al. sampled global/Western Pacific IW and open-ocean WV).
- **Overlap with Trujillo Part III (Quarantine):** Exactly **0 shared product IDs**.
- **Overlap with Trujillo Part I:** Lineage is orthogonal (Trujillo collected petroleum slicks; Li et al. collected geophysical ocean/atmosphere phenomena).
- **Internal Split Leakage in Li et al.:** Slices were partitioned randomly (8:1:1), scattering sub-images from the same IW scene across training, validation, and test sets. Any future training of an Ocean Sentinel specialist must enforce **strict parent-scene splitting**.

---

## 5. CLASS-SEMANTIC TAXONOMY & LOOK-ALIKE SUITABILITY

Li et al. provides 15 semantic classes. Each was audited for physical mechanism, annotation fidelity, and oil-spill look-alike relevance:

| Index | Code | Class Name | Physical Damping / Backscatter Mechanism | Annotation Quality | Look-alike Benchmark Suitability |
| :---: | :---: | :--- | :--- | :--- | :--- |
| **0** | **BG** | Background (Clean Sea) | Equilibrium capillary-gravity wave backscatter | Labelme unannotated | Valid clean-water reference |
| **1** | **AF** | Atmospheric Front | Surface wind shear / pressure discontinuity lines | Polygon contours | Secondary meteorological context |
| **2** | **BS** | **Biological Slick** | Monomolecular biogenic surfactant film dampening capillary waves identically to thin oil | Dense pixel polygons | **PRIMARY LOOK-ALIKE BENCHMARK CLASS** |
| **3** | **IB** | Iceberg | Hard corner-reflector target | Point/small polygon | Navigation safety context (not look-alike) |
| **4** | **LWA** | **Low Wind Area** | Sub-threshold wind ($<2\text{ m/s}$) causing specular reflection / total backscatter dropout | Dense pixel polygons | **PRIMARY LOOK-ALIKE BENCHMARK CLASS** |
| **5** | **MCC** | Micro Convective Cells | Mesoscale cellular convection producing dark downdrafts | Polygon clusters | Secondary meteorological context |
| **6** | **OF** | **Oceanic Front** | Thermal/salinity convergence collecting natural surfactants | Linear boundary masks | **PRIMARY LOOK-ALIKE BENCHMARK CLASS** |
| **7** | **POW** | Pure Ocean Waves | Undisturbed swell and wind-sea field | Background texture | Clean-sea baseline (not look-alike) |
| **8** | **RC** | Rain Cells / Rainfall | Rain splash attenuation and downdraft gust fronts | Dense patches | Atmospheric disturbance context |
| **9** | **SI** | Sea Ice | High-latitude frozen surface | Broad regions | Cryospheric context (not look-alike) |
| **10** | **WS** | Wind Streaks | Boundary-layer roll vortices modulating surface roughness | Linear features | Atmospheric context |
| **11** | **Eddy** | Ocean Eddy | Mesoscale/submesoscale cyclonic/anticyclonic vorticity | Spiral dark spirals | Secondary look-alike class |
| **12** | **IWs** | **Internal Waves** | Pycnocline solitary wave packets producing dark trough bands | Exact wave crests | **PRIMARY LOOK-ALIKE BENCHMARK CLASS** |
| **13** | **HM** | Artificial Objects | Ships, aquaculture rafts, offshore platforms | Small bright targets | Target masking context |
| **14** | **OS** | Mineral Oil Spill | Petroleum hydrocarbon layer | Insufficient data ($N \approx 0$) | Not suitable (use Trujillo Part I for oil) |

---

## 6. SPECIFICATION OF TWO DISTINCT FUTURE BENCHMARKS

To prevent conflating phenomenon recognition with oil-model error rates, two separate benchmark specifications are pre-registered:

```
+-----------------------------------------------------------------------------------+
|                           OCEAN SENTINEL BENCHMARK SUITE                          |
+-----------------------------------------+-----------------------------------------+
|              BENCHMARK A                |              BENCHMARK B                |
|         PHENOMENON RECOGNITION          |       OIL-MODEL LOOK-ALIKE STRESS       |
+-----------------------------------------+-----------------------------------------+
| Purpose:                                | Purpose:                                |
| Evaluate specialist model capability to | Measure oil detector (EXP-06) false-    |
| recognize and segment SAR phenomena.    | alarm response over verified non-oil.   |
|                                         |                                         |
| Evaluated Models:                       | Evaluated Models:                       |
| Ocean Phenomena Specialist              | EXP-06 (frozen $\tau = 0.22$)           |
| Look-alike Specialist                   | Future oil detection checkpoints        |
|                                         |                                         |
| Data Domain:                            | Data Domain:                            |
| Li et al. $256 \times 256$ uint16 at    | Native Level-1 GRD re-acquisitions      |
| $100\text{ m}$ (IW + WV partitions).    | ($10\text{ m}$, dual-pol VH/VV, dB).    |
|                                         |                                         |
| Evaluation Classes:                     | Evaluation Classes:                     |
| Multi-class: BS, LWA, IWs, OF, RF, etc. | Delineated BS, LWA, IWs, OF masks.      |
|                                         |                                         |
| Key Metrics:                            | Key Metrics:                            |
| Class-stratified IoU, Dice, Precision,  | Patch Alarm Rate, Predicted-Positive    |
| Recall.                                 | Pixel Fraction, Clustered Product Rate. |
+-----------------------------------------+-----------------------------------------+
```

### 6.1 Benchmark A Protocol: Phenomenon Segmentation Specialist
- **Objective:** Quantify segmentation accuracy of specialist neural networks on known ocean phenomena.
- **Dataset Splitting Rule:** The 484 IW parent scenes and 2,383 WV vignettes must be split into **Train (70%)**, **Dev (15%)**, and **Holdout (15%)** strictly at the **parent-product / source-scene level**. Random patch splitting is prohibited.
- **Metrics:**
  $$\text{IoU}_c = \frac{|P_c \cap G_c|}{|P_c \cup G_c|}, \quad \text{Dice}_c = \frac{2 |P_c \cap G_c|}{|P_c| + |G_c|}$$
  Computed separately for each class $c \in \{\text{BS}, \text{LWA}, \text{IWs}, \text{OF}, \dots\}$.

### 6.2 Benchmark B Protocol: Oil Detector Look-alike Stress Test
- **Objective:** Quantify the false-positive response of an oil-detection model when exposed to verified non-oil features.
- **Prerequisite Execution Gate:** Because EXP-06 requires $10\text{ m}$ dual-pol calibrated dB imagery, **Benchmark B cannot be evaluated on the distributed 100m uint16 files**.
- **Re-acquisition Requirement:** Benchmark B requires querying Copernicus Open Access / ESA archives for the original 484 Sentinel-1 IW SAFE products, cropping the $512 \times 512$ native $10\text{ m}$ dual-pol tiles corresponding to the polygon coordinates, and applying canonical Ocean Sentinel normalization.
- **Stress Metrics:**
  1. **Patch Alarm Rate ($\text{PAR}_c$):** Fraction of patches containing phenomenon $c$ that produce at least one positive pixel at $\tau = 0.22$:
     $$\text{PAR}_c = \frac{1}{N_c} \sum_{i=1}^{N_c} \mathbb{I}\left(\sum_{p \in \text{patch}_i} \mathbb{I}(\hat{y}_p \ge 0.22) > 0\right)$$
  2. **Predicted-Positive Pixel Fraction ($\text{PPF}_c$):**
     $$\text{PPF}_c = \frac{\sum_{p \in \text{mask}_c} \mathbb{I}(\hat{y}_p \ge 0.22)}{|G_c|}$$
  3. **Parent-Product Alarm Rate:** Fraction of unique parent Sentinel-1 granules alarmed, preventing pseudo-replication from correlated sub-images.

---

## 7. PARENT-PRODUCT CLUSTERING & STATISTICAL SAMPLING CONTRACT

Sub-images extracted from the same parent Sentinel-1 pass share:
1. Identical atmospheric background states and wind regimes.
2. Identical satellite orbit trajectories and Doppler centroids.
3. Coherent cross-track incidence angle profiles ($\sim 29^\circ$ to $46^\circ$).

Therefore, the **independent statistical sampling unit is the Parent Product / Source Scene**, not the cropped patch:
- In Benchmark A: 484 independent IW clusters + 2,383 independent WV clusters.
- In Benchmark B: 484 independent IW observation granules.
All statistical confidence intervals (95% CI) and standard errors must be computed using cluster-robust variance estimation grouped by parent scene ID.

---

## 8. DEFINITIVE ANSWERS TO MANDATED SCIENTIFIC QUESTIONS

### A. Is Li et al. genuinely independent of Ocean Sentinel?
**Yes, in origin and authorship; but it is a derived compilation.**  
It was independently developed by physical oceanographers at Ocean University of China / University of Delaware. It has zero product overlap with DARTIS (Eastern Mediterranean 2019) and zero overlap with Trujillo Part III. However, it is not de novo imagery: it explicitly incorporated 2,383 Wave Mode vignettes from TenGeoP-SARwv and 156 IW scenes from Tao et al. (2022).

### B. Exactly what data does it contain?
**5,011 image slices of $256 \times 256$ pixels at $100\text{ m}$ spatial resolution in single-polarization VV, stored as scaled `uint16` integers.**  
- 2,628 slices come from 484 Sentinel-1 IW scenes (2015–2022).
- 2,383 slices come from Sentinel-1 Wave Mode (1,731 WV1 + 652 WV2).
- 0 VH channels exist in the distributed files.
- Each slice is paired with a palette-indexed PNG segmentation mask covering 12 ocean/atmosphere classes plus background and artificial structures.

### C. Exactly which classes can serve as look-alikes?
Four specific classes provide scientifically valid look-alike evidence:
1. **Biological Slicks (BS):** Natural organic surfactants dampening capillary waves.
2. **Low Wind Areas (LWA):** Wind shadows and calm sea zones.
3. **Internal Waves (IWs):** Solitary wave packets producing dark backscatter troughs.
4. **Oceanic Fronts (OF):** Current shear and convergence boundaries.

### D. Can EXP-06 be evaluated directly on it?
**No.** Direct zero-shot evaluation on the distributed dataset is physically invalid due to:
- Spatial resolution mismatch ($100\text{ m}$ vs $10\text{ m}$).
- Array dimension mismatch ($256 \times 256$ vs $512 \times 512$).
- Polarization mismatch (single-pol VV vs dual-pol VH/VV).
- Radiometric format mismatch (quantized `uint16` image intensity vs calibrated float32 dB).
Evaluating EXP-06 directly would test image resampling artifacts rather than model radar perception.

### E. Can a future Lookalike Specialist be trained from it?
**Yes, for an Ocean Phenomena Specialist or Look-alike Specialist.**  
Because it contains 5,011 high-quality multi-class segmentation masks, it is an outstanding candidate for training a multi-class phenomenon recognition model (e.g., Segformer / U-Net) at $100\text{ m}$ resolution. However, it must **never enter EXP-07 oil-detection training**, and its partitions must be split strictly by parent scene ID.

### F. What information is missing?
1. The **VH polarization channel** is absent from the distributed dataset.
2. Native **$10\text{ m}$ spatial resolution** is absent (imagery is decimated to $100\text{ m}$).
3. **Calibrated float32 $\sigma^0$ values** and explicit calibration formulas are absent (`uint16` integers).
4. **Standard GeoTIFF CRS projections** are absent (only corner GCP tiepoints are provided).

### G. What uncertainty remains?
1. **Parent SAFE Granule Recovery:** Whether all 484 IW parent scenes can be matched to publicly accessible Level-1 GRDH SAFE archives for full $10\text{ m}$ dual-pol re-acquisition.
2. **Geographic Spatial Leakage against Trujillo Part I:** While product IDs differ, whether any of the 484 scenes fall within $5\text{ km}$ of Trujillo Gulf of Mexico or North Sea training patches must be confirmed via bounding-box intersection before Benchmark B execution.

### H. What should the next scientific intervention be?
1. **Phase 7B.2:** Pre-register and train an **Ocean Phenomena Specialist (OPS-01)** on Li et al. (using parent-product split) to establish the first multi-class non-oil recognition capability.
2. **Phase 7B.3:** Re-acquire the native $10\text{ m}$ dual-pol Level-1 GRD SAFE products for the 484 IW parent scenes to execute **Benchmark B (Oil Detector Look-alike Stress Test)** with zero domain distortion.
3. **Phase 7C:** Architect an **Evidence Fusion Engine** that pairs EXP-06 (oil detector) with OPS-01 (phenomena specialist) to suppress look-alike false alarms without retraining or corrupting the baseline oil detector.
