# Ocean Sentinel — Phase 5A: Development-Split Failure Analysis & Hard-Negative Mining Design

**Date:** 2026-09-11  
**Status:** COMPLETED & AUDITED (SCIENTIFIC INTEGRITY REPAIRED)  
**Execution Authority:** Chief Architect Officer (CAO)  
**Document Identity:** `PHASE_5A_DEVELOPMENT_FAILURE_ANALYSIS_20260911.md`  
**Primary Checkpoint Audited:** `experiments/exp01_baseline/best_model.pt`  
**Evaluation Target:** Trujillo Part I Validation Split (`trujillo_2024_part_i_val`, 180 scenes, 2,880 tiles)  
**Scientific Boundary:** Zero use or consumption of frozen external benchmark Trujillo Part III.

---

## 1. Executive Summary

Following the formal closure and immutability freeze of the Phase 4D-F Trujillo Part III external benchmark, Phase 5A executed an exhaustive, development-side diagnostic audit of the baseline oil-spill segmentation model (`experiments/exp01_baseline/best_model.pt`). The primary objective was to characterize the model's false-positive failure modes on scientifically permitted development data and determine whether **Hard-Negative Mining** is an empirically justified intervention hypothesis for future training.

### Key Empirical Findings:

1. **Checkpoint Integrity:** SHA-256 digest matched before and after execution (`9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`), supporting unchanged checkpoint bytes [OBSERVED FACT].
2. **Multi-Layered Scientific Firewall Activated:** Programmatic defenses (`src/ocean_sentinel/ingestion/firewall.py`) were established and integrated into data pipelines, enforcing multi-layered isolation of Trujillo Part III (450 scenes, 900 rasters) across path, identifier, manifest, and content SHA-256 hash layers.
3. **Dataset Structure & Negative Supervision Context:** In the canonical Trujillo Part I dataset, **100% of parent scenes (180/180 in validation, 840/840 in train)** contain confirmed oil annotations. Negative examples exist exclusively at the **tile level** (1,827 empty tiles out of 2,880 validation tiles, 63.44%). Empty training and validation tiles occur inside oil-containing parent scenes [OBSERVED FACT].
4. **False Alarm Burden on Development Data:**
   - On the 1,827 empty validation tiles, **1,460 tiles (79.91%)** are clean true negatives ($FP = 0$) [OBSERVED FACT].
   - **367 tiles (20.09%)** exhibit false alarms ($FP > 0$) [OBSERVED FACT].
   - **193 tiles (10.56%)** exhibit significant false alarms ($FP \ge 100$ pixels) [OBSERVED FACT].
   - Total validation false-positive pixels: **2,327,942 pixels** distributed across **19,807 connected components** [OBSERVED FACT].
5. **Low-Backscatter SAR Signatures & Physical Calibration:**
   - *Observed Fact:* The examined high-false-positive scenes have very low measured SAR backscatter (Band 0 mean $-38.43\text{ dB}$, min $-50.78\text{ dB}$; Band 1 mean $-29.72\text{ dB}$) and visual characteristics consistent with calm/low-wind sea conditions [OBSERVED FACT].
   - *Inference:* These observations are consistent with reduced sea-surface roughness producing dark SAR signatures that can resemble oil-slick signatures [INFERENCE].
   - *Unverified Mechanism:* Causal meteorological attribution is not established without independent meteorological, in-situ, or acquisition evidence [UNVERIFIED MECHANISM].
   - *Confidence Morphology:* Over **21.9% of all false-positive pixels (510,620 pixels)** are predicted with extreme confidence ($\ge 0.95$), demonstrating that errors are not merely threshold jitter near $\tau = 0.22$ [OBSERVED FACT].
6. **Training Split Candidate Harvest:** An exhaustive audit of the 13,440 tiles in the Training Split identified **8,357 empty tiles** (derived from oil-containing parent scenes), yielding **1,605 candidate tiles with $FP \ge 100$** and **528 candidate tiles with $FP \ge 1,000$** [OBSERVED FACT].
7. **Candidate Reservoir Characterization:** The training split contains a reproducible reservoir of baseline false-positive negative tiles suitable for testing a controlled hard-negative mining intervention. This provides a candidate reservoir for testing a controlled intervention, not advance proof that hard-negative mining will resolve the issue [INFERENCE].

---

## 2. Scientific Firewall: Trujillo Part III Isolation

Under the Ocean Sentinel governance rules, Trujillo Part III is a permanently frozen, external evaluation benchmark. To prevent accidental contamination in training, validation, or mining routines, a programmatic firewall has been created and verified.

### 2.1 Protected Inventory
The protected evaluation universe comprises:
- **Filesystem Directory:** `data/raw/external_validation/trujillo_part_iii/`
- **Total Scenes:** 450 scenes (150 Oil, 150 No oil, 150 Lookalike)
- **Total GeoTIFFs:** 900 files (450 2-band radar images, 450 binary segmentation masks)
- **Manifest Artifacts:** `experiments/DATASET_MANIFEST_TRUJILLO_PART_III.json`, `scratch/trujillo_part_iii_pairing.json`
- **Evaluation Artifacts:** `experiments/performance/trujillo_part_iii_eval_20260911_exp01/`

### 2.2 Programmatic Enforcement & Protection Level
A dedicated module `src/ocean_sentinel/ingestion/firewall.py` implements:
1. **Path & Directory Signatures:** `is_protected_part_iii_path(path)` matches directory fragments (`external_validation/trujillo_part_iii`, `Images/No oil`, `Images/Lookalike`) and mask conventions (`_segmentation.tif`).
2. **Identifier Signatures:** `is_protected_part_iii_identifier(ident)` detects scene identifiers (`Oil_00000`..`Oil_00149`, `No oil_00000`..`No oil_00149`, `Lookalike_00000`..`Lookalike_00149`).
3. **Manifest Identity:** `validate_manifest_against_firewall(manifest)` checks `dataset_name`, `title`, and `source_archive` fields for Part III designations.
4. **Content Hash Identity:** `is_protected_part_iii_content(file_path)` computes the SHA-256 hash of input rasters against the 900 certified Trujillo Part III GeoTIFF hashes (`scratch/trujillo_part_iii_extracted_sha256.json`), intercepting renamed or copied Part III files.
5. **Fail-Closed Gate:** `assert_no_part_iii_leakage(items, context)` raises `PartIIIFirewallViolationError` upon detecting any protected signature or matching content hash.
6. **Integration into Pipelines:** `TrujilloTileDataset.__init__` programmatically verifies data roots and manifests on initialization.

### 2.3 Residual Limitations (Scope of Protection)
While the firewall provides rigorous, multi-layered protection against operational leakage:
- **Re-encoded / Modified Rasters:** If a Part III raster is re-exported, re-compressed, resampled, or modified (altering its raw byte stream and GeoTIFF tags) and stripped of path markers, byte-level SHA-256 matching will not match.
- **In-Memory Objects:** Raw numpy arrays or PyTorch tensors instantiated directly in memory without filesystem paths cannot be tracked by filesystem or hash inspection.
- **Unindexed Artifacts:** Files outside the certified 900-GeoTIFF registry that lack path or identifier markers cannot be intercepted by content hash.
Therefore, the protection level is described accurately as robust multi-layered operational isolation, rather than an unqualifiable claim of absolute isolation.

---

## 3. Development Data Universe Reconstruction

All data assets currently present in the repository were catalogued and audited for scientific legitimacy, provenance, and split integrity:

| Asset / Dataset | Role in Repository | Provenance Completeness | Physical / Raster Semantics | Positive / Negative Class | Split Assignment | Training Eligibility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Trujillo 2024 Part I** (`data/raw/trujillo_2024`) | Core Development & In-domain Benchmark | COMPLETE (Zenodo DOI: 10.5281/zenodo.10900078; SHA-256 verified) | Dual-band SAR, native dB backscatter, calibrated units, unknown polarization mapping (`channel_0`, `channel_1`) | Positive (Oil spills annotated at pixel level); empty tiles serve as negative ocean | 1,200 parent patches ($2048 \times 2048$):<br>• Train: 840 (13,440 tiles)<br>• Val: 180 (2,880 tiles)<br>• Test: 180 (2,880 tiles) | **PERMITTED** (Train split only; Val and Test remain locked) |
| **Trujillo Part III** (`data/raw/external_validation/trujillo_part_iii`) | External Evaluation Benchmark | COMPLETE (Phase 4D-F closed and frozen) | Dual-band SAR, native dB scale, unknown polarization order | 150 Oil, 150 No oil, 150 Lookalike | External Holdout Benchmark (Phase 4D-F) | **STRICTLY DISALLOWED** (0% permitted) |
| **Yang & Singha 2025 (DARTIS)** (`data/metadata/yang_singha_2025`) | External Candidate Assessment | Incomplete (metadata table and CDSE report only; zero rasters ingested) | N/A (no rasters on disk) | Tabular oil slick metadata | Not partitioned | **UNAVAILABLE** (No image data downloaded) |
| **MORP_SYNTH** (`experiments/DATASET_PREFLIGHT_MORP_SYNTH.json`) | Synthetic Benchmark Candidate | REJECTED at Provenance Gate (Unverified license and generation parameters) | N/A | Synthetic oil slicks | Blocked | **DISALLOWED** (Provenance Gate violation) |

---

## 4. Split and Spatial Leakage Audit

The Trujillo Part I spatial partition was generated using connected-component spatial graph partitioning (`data/metadata/trujillo_2024/spatial_split_manifest.json`):
- **Spatial Connected Components:** 204 total spatial clusters; **0 cross-split components** [OBSERVED FACT].
- **Geotransform Uniqueness:** 1,198 unique geotransforms; **0 identical geotransforms across splits** [OBSERVED FACT].
- **Spatial Overlap:** **0 cross-split overlapping bounding boxes** [OBSERVED FACT].
- **Proximity Buffer:** Minimum validation-to-train centroid distance is **18.39 km** (median: 52.11 km; 0 pairs < 5 km) [OBSERVED FACT].
- **Parent Scene Isolation:** All 16 $512 \times 512$ tiles derived from any $2048 \times 2048$ parent scene are strictly co-located in the same partition. Zero parent-scene fragmentation exists across train, val, and test [OBSERVED FACT].

---

## 5. Baseline Checkpoint Verification

- **Checkpoint File:** `experiments/exp01_baseline/best_model.pt`
- **File Size:** 292,465,299 bytes
- **Canonical SHA-256:** `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
- **Audit Status:** [OBSERVED FACT] SHA-256 digest matched before and after execution, supporting unchanged checkpoint bytes.
- **Architecture:** `ResNet34UNet` (24,346,305 parameters, `slice_variance_scaled` 2-channel adaptation).
- **Training Origin:** Trained for 10 epochs on `trujillo_2024_part_i` train split using `CombinedBCEAndDiceLoss` (0.5/0.5), AdamW, CosineAnnealingLR.
- **State:** LOCKED. No model weights were modified or overwritten during Phase 5A.

---

## 6. Development Evaluation Contract

To maintain strict scientific control, the development evaluation contract was frozen prior to failure extraction:
1. **Dataset Split:** `trujillo_2024_part_i_val` (180 parent patches, 2,880 tiles).
2. **Tile Geometry:** $512 \times 512$ non-overlapping windows read directly from 16-bit GeoTIFFs.
3. **Radiometric Normalization:** Destination-channel z-score standardization using training-derived statistics:
   $$\mu_0 = -33.233137, \quad \sigma_0 = 6.489986$$
   $$\mu_1 = -19.941216, \quad \sigma_1 = 4.531346$$
4. **Decision Threshold:** Frozen at $\tau = 0.22$ on the sigmoid output probability domain (inherited from `exp02a_threshold_analysis.json`).
5. **Sample Inclusion:** 100% evaluated (2,880/2,880 tiles). Zero sample exclusion.

---

## 7. Baseline Failure Analysis: Quantitative Statistics

The baseline model was evaluated across all 2,880 validation tiles on CUDA. Detailed confusion counts, connected components, probability histograms, and backscatter statistics were extracted.

### 7.1 Tile-Level False Alarm Distribution
- **Total Validation Tiles:** 2,880
- **Empty (Clean Ocean, $GT = 0$) Tiles:** 1,827 (63.44%)
- **Clean Water True Negatives ($FP = 0$):** 1,460 tiles (**79.91%** of empty tiles)
- **Clean Water False Alarms ($FP > 0$):** 367 tiles (**20.09%** of empty tiles)
- **Significant False Alarms ($FP \ge 100$):** 193 tiles (**10.56%** of empty tiles)
- **Severe False Alarms ($FP \ge 1,000$):** 38 tiles (**2.08%** of empty tiles)

### 7.2 False-Positive Area Distribution on Empty Tiles
For the 367 empty tiles exhibiting false alarms:
- **Total FP Pixels:** 465,950 pixels
- **Mean FP Area:** 1,269.62 pixels
- **Std Dev:** 8,998.12 pixels
- **Min:** 1 pixel
- **25th Percentile (p25):** 33.0 pixels
- **Median (p50):** 109.0 pixels
- **75th Percentile (p75):** 330.5 pixels
- **90th Percentile (p90):** 837.6 pixels
- **95th Percentile (p95):** 1,588.1 pixels
- **99th Percentile (p99):** 27,681.8 pixels
- **Maximum:** 118,792 pixels (Tile #2131, parent scene `00932`)

### 7.3 Connected Component Morphology
BFS connected-component extraction identified **19,807 false-positive components** across the validation split:
- **Total FP Components:** 19,807
- **Mean Component Area:** 117.53 pixels
- **Std Dev:** 1,299.99 pixels
- **Median Component Area:** 2.0 pixels
- **p75 Area:** 15.0 pixels
- **p90 Area:** 124.0 pixels
- **p95 Area:** 366.4 pixels
- **p99 Area:** 2,108.94 pixels
- **Maximum Component Area:** 115,060 pixels

> **Morphology Interpretation [INFERENCE]:** The false-positive distribution exhibits a dual morphology:
> 1. **High-frequency, low-area noise:** 75% of components have an area $\le 15$ pixels, representing edge jitter and sensor speckle.
> 2. **Low-frequency, massive coherent structures:** The top 1% of components account for the vast majority of false-positive area, consisting of large contiguous dark patches spanning tens of thousands of pixels.

### 7.4 Prediction Confidence Distribution
Analysis of prediction probabilities on all false-positive pixels across $[0.22, 1.00]$:

| Probability Bin | False-Positive Pixel Count | Percentage of FP Pixels |
| :--- | :--- | :--- |
| **$[0.22, 0.30)$** | 247,228 | 10.62% |
| **$[0.30, 0.40)$** | 254,134 | 10.92% |
| **$[0.40, 0.50)$** | 297,000 | 12.76% |
| **$[0.50, 0.60)$** | 188,606 | 8.10% |
| **$[0.60, 0.70)$** | 168,846 | 7.25% |
| **$[0.70, 0.80)$** | 188,462 | 8.10% |
| **$[0.80, 0.90)$** | 263,409 | 11.32% |
| **$[0.90, 0.95)$** | 209,637 | 9.01% |
| **$[0.95, 1.00)$** | **510,620** | **21.93%** |

> **Critical Finding [OBSERVED FACT]:** Over **21.9% of all false-positive pixels (510,620 pixels)** are predicted with extreme confidence ($\ge 0.95$). The model is not hesitating near the threshold; it is saturating with certainty on specific non-oil ocean structures.

---

## 8. Visual Forensics: Diagnostic Failure Cases

A deterministic sample of development-split cases was extracted, and 6-panel composite diagnostics ($1536 \times 1024$) were rendered to `experiments/performance/phase_5a_diagnostics/`:

```
+-------------------+-------------------+-------------------+
| SAR Band 0 (dB)   | SAR Band 1 (dB)   | Ground Truth Mask |
+-------------------+-------------------+-------------------+
| Probability Map   | Prediction Mask   | Error Diagnostic  |
| (False-Color)     | (\tau = 0.22)     | Overlay (RGB)     |
+-------------------+-------------------+-------------------+
```

### Forensic Sample Summary:
1. **Worst False Positive Tile (`forensic_worst_fp_01_tile_2131_00932.png`):**
   - **Provenance:** Tile #2131 (col 1536, row 0), Parent Scene `00932` (Eastern Mediterranean Sea).
   - **Metrics:** $GT = 0$, $FP = 118,792$, $TP = 0$, $FN = 0$, $\text{IoU} = 0.0000$ [OBSERVED FACT].
   - **Radar Signature:** Band 0 mean $-38.43\text{ dB}$ (min $-50.78\text{ dB}$); Band 1 mean $-29.72\text{ dB}$ [OBSERVED FACT].
   - **Physical Calibration:**
     - *Observed Fact:* The examined scene exhibits very low measured SAR backscatter across the entire eastern sector [OBSERVED FACT].
     - *Inference:* Visual morphology is consistent with reduced sea-surface roughness producing dark SAR signatures resembling oil slicks [INFERENCE].
     - *Unverified Mechanism:* Causal meteorological attribution (e.g., local calm-sea atmospheric conditions) is not established without independent meteorological observations [UNVERIFIED MECHANISM].
     - *Model Response:* Under this low-backscatter signature, the baseline model predicts oil spill with mean confidence $0.4927$ and widespread saturation $>0.90$.
2. **2nd Worst False Positive Tile (`forensic_worst_fp_02_tile_2147_00933.png`):**
   - **Provenance:** Tile #2147 (col 1536, row 0), Parent Scene `00933` (Adjacent to `00932`).
   - **Metrics:** $GT = 0$, $FP = 101,779$, $TP = 0$, $FN = 0$, $\text{IoU} = 0.0000$ [OBSERVED FACT].
   - **Physical Calibration:** Adjacent parent scene exhibiting contiguous low-backscatter regions structurally aligned with `00932` [OBSERVED FACT], consistent with a coherent spatial zone of reduced sea-surface roughness spanning adjacent acquisitions [INFERENCE]. Causal meteorological attribution is not established without independent weather data [UNVERIFIED MECHANISM].
3. **Median False Positive Tile (`forensic_median_fp_tile_1351_00512.png`):**
   - **Provenance:** Tile #1351 (col 1536, row 512), Parent Scene `00512` (Cyprus basin).
   - **Metrics:** $GT = 0$, $FP = 109$, $TP = 0$, $FN = 0$, $\text{IoU} = 0.0000$ [OBSERVED FACT].
   - **Physical Morphology:** Isolated linear low-backscatter feature consistent with an internal wave or ship wake boundary [INFERENCE].
4. **Moderate False Positive Tile (`forensic_moderate_fp_tile_2287_00941.png`):**
   - **Provenance:** Tile #2287 (col 1536, row 1536), Parent Scene `00941` (Gulf of Mexico).
   - **Metrics:** $GT = 0$, $FP = 332$, $TP = 0$, $FN = 0$, $\text{IoU} = 0.0000$ [OBSERVED FACT].
   - **Physical Morphology:** Localized dark slick-like eddy structure surrounded by rougher open water [INFERENCE].
5. **Borderline False Positive Tile (`forensic_borderline_fp_tile_2338_01009.png`):**
   - **Provenance:** Tile #2338 (col 1024, row 0), Parent Scene `01009` (Gulf of Mexico).
   - **Metrics:** $GT = 0$, $FP = 300$, $TP = 0$, $FN = 0$, $\text{IoU} = 0.0000$ [OBSERVED FACT].
   - **Physical Morphology:** Fragmented boundary noise near tile margins [INFERENCE].
6. **Clean Water True Negative (`forensic_true_negative_clean_tile_0003_00012.png`):**
   - **Provenance:** Tile #0003 (col 1536, row 0), Parent Scene `00012` (Off Alexandria, Egypt).
   - **Metrics:** $GT = 0$, $FP = 0$, $TP = 0$, $FN = 0$, $\text{IoU} = 1.0000$ [OBSERVED FACT].
   - **Radar Signature:** Homogeneous open ocean with healthy capillary wave backscatter (Band 0 mean $-28.5\text{ dB}$, Band 1 mean $-16.8\text{ dB}$). Prediction probability remains strictly $<0.05$ [OBSERVED FACT].
7. **Mixed Spill Tile with False Positives (`forensic_mixed_spill_with_fp_tile_0002_00012.png`):**
   - **Provenance:** Tile #0002 (col 1024, row 0), Parent Scene `00012`.
   - **Metrics:** $GT = 19,353$, $TP = 18,737$, $FP = 1,070$, $FN = 616$, $\text{IoU} = 0.9175$ [OBSERVED FACT].
   - **Physical Morphology:** Large confirmed oil spill accurately delineated, but accompanied by false alarms along the diffuse thin-sheen boundary [INFERENCE].

---

## 9. Failure-Mode Taxonomy

Based on visual and quantitative forensic inspection, the baseline's false-positive errors fall into four distinct, physically motivated classes:

1. **Class A: Large Contiguous Low-Backscatter / Calm-Water Zones (Dominant Error by Area)**
   - *Characteristics [OBSERVED FACT]:* Smooth, expansive dark regions spanning $10,000$ to $120,000$ pixels. Both channels drop below $-35\text{ dB}$ (Band 0) and $-28\text{ dB}$ (Band 1).
   - *Mechanism Interpretation [INFERENCE]:* Consistent with specular radar reflection away from the satellite in calm water conditions where capillary wave roughness is suppressed.
   - *Unverified Limitation [UNVERIFIED MECHANISM]:* Causal meteorological attribution to specific atmospheric low-wind fronts is not established without independent meteorological observations.
   - *Remediation Hypothesis:* The training split contains a reproducible reservoir of baseline false-positive negative tiles suitable for testing a controlled hard-negative mining intervention.
2. **Class B: Linear Wave Boundaries, Internal Waves & Wakes**
   - *Characteristics:* Narrow linear or curvilinear dark tracks spanning $100$ to $1,000$ pixels [OBSERVED FACT].
   - *Mechanism Interpretation:* Oceanic internal waves and hydrodynamic ship wakes modulating surface roughness [INFERENCE].
   - *Remediation Hypothesis:* Testable via hard-negative mining.
3. **Class C: Spill Boundary Dilation & Sheen Leakage**
   - *Characteristics:* 100–1,000 pixels adjacent to genuine oil spills [OBSERVED FACT].
   - *Mechanism Interpretation:* Model over-predicts spill perimeters into diffuse sheens or low-contrast boundary pixels [INFERENCE].
   - *Remediation Potential:* Moderate via loss or boundary weighting (outside single-variable scope).
4. **Class D: Isolated High-Frequency Speckle**
   - *Characteristics:* Scattered 1-to-5 pixel components across otherwise clean water [OBSERVED FACT].
   - *Mechanism Interpretation:* Inherent SAR speckle noise [INFERENCE].
   - *Remediation Potential:* Minimal area impact ($<1\%$ of total FP pixels). Effectively filtered by post-processing or morphological opening.

---

## 10. Evaluation of Competing Hypotheses

| Hypothesis | Description | Repository Evidence | Classification |
| :--- | :--- | :--- | :--- |
| **H1: Reusable Negative Structures** | False positives are concentrated in reusable negative structures suitable for candidate mining. | • 79.91% of empty tiles have zero false alarms; errors concentrate in dark calm-water tiles.<br>• The training split contains a reproducible reservoir of baseline false-positive negative tiles suitable for testing a controlled hard-negative mining intervention ($N = 1,605$ with $FP \ge 100$, $N = 528$ with $FP \ge 1,000$).<br>• Structures are spatially contiguous across adjacent scenes (`00932`, `00933`). | **SUPPORTED AS HYPOTHESIS** |
| **H2: Preprocessing / Channel Mismatch** | False positives arise mainly from preprocessing, normalization, or channel ordering mismatch. | • On Part III, swapped Mapping B produced 100% lookalike saturation.<br>• However, on the development validation split where normalization and channel order are strictly identical to training, clean water FAR remains 20.09% with >500,000 saturated FP pixels. Channel consistency is necessary but insufficient. | **PARTIALLY SUPPORTED** |
| **H3: Insufficient Geographic Diversity** | False-positive burden may be associated with compositional underrepresentation of clean ocean and diverse sea states in baseline training. | • In Trujillo Part I, 100% of parent scenes contain oil spills (0 empty scenes).<br>• Regional precision varies widely (SE Asia 68.4% vs North Sea 92.4%). Clean water without spills was never presented as independent negative scenes during training. | **SUPPORTED** |
| **H4: Architectural Deficiencies** | False positives require architectural changes (e.g. deeper backbone, attention) rather than data rebalancing. | • ResNet34UNet (24.3M params) achieves 95.1% recall on test and 82.7% on val.<br>• Although empty tiles already contribute negative-pixel supervision through BCE, the development analysis indicates that the baseline training distribution may provide insufficient or compositionally limited hard-negative supervision for the specific dark-water false-positive structures observed at validation. | **NOT SUPPORTED** |
| **H5: Threshold & Calibration Issues** | False positives are primarily boundary artifacts resolvable by threshold tuning. | • Sweeping threshold across $[0.10, 0.90]$ demonstrates an empirical plateau near $\tau = 0.22$.<br>• Raising threshold destroys recall without eliminating the 510,620 saturated FP pixels in $[0.95, 1.00]$. | **NOT SUPPORTED** |
| **H6: Multiple Contributing Factors** | Multiple factors contribute to false alarms. | • Data composition and exposure (H1/H3) are primary contributors, with channel handling (H2) and speckle (D) contributing secondary effects. | **SUPPORTED** |

---

## 11. Training Split Candidate Harvest: Feasibility Characterization

To confirm that a hard-negative candidate reservoir exists without touching held-out validation or test data, the 13,440 tiles of the Training Split were evaluated under the baseline checkpoint:
- **Total Training Tiles:** 13,440 [OBSERVED FACT]
- **Empty Ground-Truth Tiles ($GT = 0$):** 8,357 (62.18%, derived from oil-containing parent scenes) [OBSERVED FACT]
- **Empty Training Tiles with False Positives ($FP > 0$):** 2,599 (31.10% of empty training tiles) [OBSERVED FACT]
- **Candidate Pool ($FP \ge 100$ pixels):** **1,605 tiles** (19.21%) [OBSERVED FACT]
- **Candidate Pool ($FP \ge 500$ pixels):** **786 tiles** (9.41%) [OBSERVED FACT]
- **Candidate Pool ($FP \ge 1,000$ pixels):** **528 tiles** (6.32%) [OBSERVED FACT]
- **Severe Candidate Pool ($FP \ge 5,000$ pixels):** **213 tiles** (2.55%) [OBSERVED FACT]
- **Fully Saturated Tiles ($FP = 262,144$ pixels, 100% false alarm):** 10 tiles (found in parent stems `00088`, `00526`, `00751`, `00752`, `01130`, `00657` with mean confidence $>0.95$) [OBSERVED FACT].

> **Candidate Reservoir Characterization:** The training split contains a reproducible reservoir of baseline false-positive negative tiles suitable for testing a controlled hard-negative mining intervention ($N = 1,605$ with $FP \ge 100$, $N = 528$ with $FP \ge 1,000$). There is zero need to access validation data, test data, or external benchmarks to mine candidate negative examples. Whether hard-negative mining will significantly reduce false alarms without degrading recall remains an empirical hypothesis to be tested in Phase 5B.

---

## 12. Recommendation: Authorized Intervention Hypothesis

**Recommendation:** Proceed with a strictly controlled **One-Variable Intervention** in Phase 5B:
$$\text{BASELINE} \quad + \quad \text{TRAINING-SPLIT HARD-NEGATIVE MINING}$$

### Prohibited Co-Variables:
To maintain causal clarity, the following must remain strictly unchanged:
- Architecture: Locked to `ResNet34UNet` (`slice_variance_scaled`).
- Loss Function: Locked to `CombinedBCEAndDiceLoss` (0.5 BCE, 0.5 Dice).
- Optimizer & Scheduler: Locked to AdamW, CosineAnnealingLR.
- Decision Threshold: Locked to $\tau = 0.22$.
- Normalization: Locked to training stats ($\mu_0, \sigma_0, \mu_1, \sigma_1$).
- Augmentations: Locked to canonical flip/rotations.
- Validation Partition: Locked to `trujillo_2024_part_i_val`.

---

## 13. Guardrails Implemented in Phase 5A

1. **Firewall Gate (`src/ocean_sentinel/ingestion/firewall.py`):** Blocks paths, filenames, identifiers, manifest metadata, and SHA-256 digests of Trujillo Part III artifacts.
2. **Dataset Interceptor (`TrujilloTileDataset.__init__`):** Programmatically inspects manifests and root paths on construction; fails closed on Part III.
3. **Cross-Split Isolation Test (`tests/test_phase_5_guardrails.py`):** Validates disjoint parent scenes across splits and enforces authorized mining thresholds.
4. **Deterministic Candidate Rules:** Hard-negative mining criteria pre-registered before candidate selection.

---

## 14. Remaining Scientific Uncertainties

1. **Negative Sampling Ratio Selection:** The 12.5% hard-negative exposure ratio was selected *a priori* as a balanced starting point; it is not claimed to be optimal and will not be tuned against external benchmark Part III outcomes.
2. **Supervision Dynamics on Empty Tiles:** Although empty tiles already contribute negative-pixel supervision through BCE (and Soft Dice contributes gradient when predictions are positive), the development analysis indicates that the baseline training distribution may provide insufficient or compositionally limited hard-negative supervision for the specific dark-water false-positive structures observed at validation.
3. **Polarization Ambiguity:** Because the physical polarization mapping of Trujillo Part I remains UNKNOWN, both bands are learned symmetrically as destination channels.

---

## 15. Git State Audit

```
Branch: master
Tracked Modifications:
- src/ocean_sentinel/ingestion/dataset.py (Firewall verification hook)
- src/ocean_sentinel/ingestion/firewall.py (Hardened multi-layer firewall)
- tests/test_part_iii_firewall.py (Firewall unit test suite)
- experiments/PHASE_5A_DEVELOPMENT_FAILURE_ANALYSIS_20260911.md (Evidence-calibrated report)
Untracked Artifacts:
- tests/test_phase_5_guardrails.py
- scratch/analyze_phase_5a_development_failures.py
- experiments/performance/phase_5a_failure_analysis/
- experiments/performance/phase_5a_diagnostics/
```
No commits, pushes, or untracked additions have been performed.
