# Ocean Sentinel — Phase 8-P0 Protocol Specification
## OPS-01 Dataset Construction & Leakage-Safe Train/Dev/Holdout Design

**Protocol Version:** `1.0.0-protocol`  
**Date:** 2026-09-13  
**Auditor / Protocol Architect:** Senior CAO Scientific Auditor, Sentinel-1 SAR Geolocation Specialist, Dataset Provenance Auditor, ML Protocol Auditor  
**Repository Root:** `D:\Projects\ocean-sentinel`  
**Branch:** `master`  
**Governance Scope:** Protocol Definition & Forensic Design Only (NO Training, NO GPU Compute, NO Dataset Freeze)  
**Authoritative Final Decision:** `A. PHASE 8 PROTOCOL READY FOR OPERATOR APPROVAL`

---

## 1. Executive Verdict

This protocol formally defines the construction and partitioning methodology for **OPS-01 (Ocean Phenomena Specialist 01)**, an auxiliary semantic segmentation engine designed to recognize common oceanic and atmospheric phenomena in Sentinel-1 SAR imagery and support downstream false-alarm suppression for the frozen **EXP-06** oil-spill detector.

### Core Scientific & Governance Declarations:
1. **Authoritative Evidence Boundary Upheld:** This protocol strictly incorporates the findings of the **Phase 7C-R2 Alignment Evidence Boundary Audit**. Geometric alignment between the Li et al. dataset and Sentinel-1 Level-1 GRD imagery remains a **conditional engineering reconstruction**; it is **NOT** independently validated physical ground truth.
2. **Permanent Distinction Enforced:**
   $$\text{“Conditional alignment is sufficient to design the OPS-01 construction protocol.”}$$
   $$\mathbf{\neq} \quad \text{“Alignment has been independently validated.”}$$
   $$\text{“47 labels have verified lineage to 12 controls.”}$$
   $$\mathbf{\neq} \quad \text{“47 source imagery slices were geometrically evaluated.”}$$
3. **Strict Training Authorization Boundary:**
   **Protocol definition does NOT authorize model training. Dataset construction does NOT authorize model training.** Model training requires a separate, explicit operator authorization following protocol approval, physical spot-checks, leakage verification, and split manifest freeze.
4. **Leakage Prevention Invariant:**
   $$\mathbf{\text{“Two slices belonging to the same parent SAR acquisition are never permitted to occupy different leakage partitions.”}}$$
   All partitioning is strictly grouped at the parent scene level (for Interferometric Wide swath) or orbit pass level (for Wave Mode). Random or per-slice splitting is permanently prohibited.

---

## 2. Authoritative Phase 7C-R2 Evidence Boundary Context

All downstream dataset construction steps must operate under the explicit evidence boundaries codified in Phase 7C-R2:
- **Source-Product Geolocation Model:** Sentinel-1 Level-1 XML Geolocation Grid is supported as an internal range-Doppler orbit model, not surveyed geodetic ground truth.
- **Li GeoTIFF Dimensions:** Directly established as $256 \times 256$ pixels.
- **Tag 33922 Metadata:** Directly established as recording outer boundary indices $0.0$ and $256.0$.
- **2550 vs 2560 Reconciliation:** Mathematically consistent with $10\times$ block averaging of a $2,560$-cell native window under the Center Convention ($255 \text{ index intervals} \times 10 = 2,550.0\text{ m}$). Dataset generation code remains unverified from source.
- **Li Crop Transformation:** NOT independently established; inferred from corner GCP inversion.
- **Model B Bilinear Model:** Conditionally supported only.
- **15.79 m Residual:** Strictly conditional on the assumed crop correspondence; not independent physical registration accuracy.
- **50 m Tolerance:** An a priori evaluation design parameter; not an empirical physical registration error bound.
- **Lineage vs Physical Samples:** 47 slice label masks are verified by filename lineage to 12 control products, but only 9 GeoTIFF imagery slices across 2 controls were physically evaluated in Phase 7C. Slices for Controls 3–12 remain uninspected in imagery space.
- **Orientation:** Directly verified for Controls 1 and 2 (Row = Range/Pixel, Col = Azimuth/Line after re-indexing); uncertain for Controls 3–12.
- **Model D (2D Affine):** "Not suitable as the general physical geolocation model for this SAR geometry under the tested spatial extent; may remain a local approximation."
- **Protected Part-III Benchmark:** Permanently quarantined under Rule 38.

---

## 3. OPS-01 Scientific Objective & Capability Gap

### Diagnosed System Need:
- **EXP-06 Baseline:** The EXP-06 petroleum slick detector is bitwise frozen (`B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF`, $\tau = 0.22$). It exhibits high detection sensitivity on authentic mineral oil, but suffers false alarms on natural low-backscatter ocean look-alikes (biogenic slicks, low wind areas, internal wave troughs).
- **Charter of OPS-01:** OPS-01 is chartered as an independent ocean phenomena recognition engine trained on natural SAR surface manifestations. In the Ocean Sentinel fusion architecture, OPS-01 outputs provide contextual intelligence to suppress false alarms without retraining or degrading the frozen oil detector.
- **Empirical Boundary:** OPS-01 is currently an **architectural hypothesis requiring validation**. Specific causal attribution of EXP-06 false alarms to individual Li classes is not yet demonstrated and must be tested empirically.

---

## 4. OPS-01 Class Taxonomy

The taxonomy is codified in `data/metadata/ops01_taxonomy_v1.json`:

| ID | Class Name | Abbr. | Operational Role | Training Eligible | Semantic Definition & Look-Alike Context |
| :---: | :--- | :---: | :--- | :---: | :--- |
| **0** | Background Seawater | `BG` | `CORE_BACKGROUND` | **YES** | Ambient open-ocean sea surface without discrete identifiable phenomena. Provides essential negative class baseline. |
| **1** | Atmospheric Front | `AF` | `AUXILIARY_METEOROLOGICAL` | **YES** | Synoptic/mesoscale air-mass boundaries causing sharp wind shifts and backscatter steps. |
| **2** | Biological Slicks | `BS` | `CORE_LOOKALIKE` | **YES** | Natural monomolecular surfactant films from plankton/algae damping capillary waves via Marangoni effect. Primary global oil look-alike. |
| **3** | Iceberg / Ice Cluster | `IB` | `CRYOSPHERIC_HAZARD` | **NO** | Floating glacial ice fragments in polar seas. Excluded from core OPS-01 training; domain-restricted. |
| **4** | Low Wind Area | `LWA` | `CORE_LOOKALIKE` | **YES** | Calm sea areas (< 2-3 m/s) with specular reflection and low backscatter. Major natural dark look-alike. |
| **5** | Mesoscale Cellular Convection | `MCC` | `AUXILIARY_METEOROLOGICAL` | **YES** | Boundary layer thermal convection creating polygonal honeycomb backscatter networks. |
| **6** | Ocean Front | `OF` | `CORE_HYDRODYNAMIC` | **YES** | Water mass convergence boundaries concentrating natural surfactants and modulating waves. |
| **7** | Pure Ocean Wave | `POW` | `AUXILIARY_WAVE_FIELD` | **YES** | Quasi-periodic swell wave modulation without slick disturbance. |
| **8** | Rain Cell / Rain Footprint | `RF` | `CORE_METEOROLOGICAL` | **YES** | Precipitation attenuation, volume scattering, surface splash, and downdraft gust fronts. |
| **9** | Sea Ice | `SI` | `CRYOSPHERIC_SURFACE` | **NO** | Frozen seawater (pack, grease, nilas). Excluded from core OPS-01 training; domain-restricted polar hazard. |
| **10** | Wind Streak | `WS` | `AUXILIARY_ATMOSPHERIC` | **YES** | Linear surface roughness modulation aligned with marine boundary layer Langmuir rolls. |
| **11** | Oceanic Eddy | `Eddy` | `CORE_HYDRODYNAMIC` | **YES** | Mesoscale rotating vortices visible via spiral convergence filaments of biogenic surfactants. |
| **12** | Internal Waves | `IWs` | `CORE_LOOKALIKE` | **YES** | Soliton packets along oceanic pycnoclines; divergence zones form pronounced dark look-alike bands. |
| **13** | Artificial / Anthropogenic Objects | `HM` | `ANTHROPOGENIC_OBJECTS` | **YES** | Ships, platforms, wind turbines, aquaculture. **STRICTLY PRESERVED AS "Artificial / Anthropogenic Objects"; NEVER RENAMED TO "Vessel".** |
| **14** | Mineral Oil Spill | `OS` | `EXCLUDED_DEFICIENT_DATA` | **NO** | **STRICTLY EXCLUDED.** Exactly 4 images (1,702 pixels, 0.0005% of dataset). Explicitly declared by Li et al. as insufficient data. Must NEVER be used for training. |

---

## 5. Source Identity Hierarchy Contract

To prevent spatial, temporal, and metadata leakage, every OPS-01 sample must be identified through a strict 4-level immutable hierarchy:

```
Level 1: Ultimate Source Product (ESA Copernicus Sentinel-1 SAFE Granule)
   └── Level 2: Parent Acquisition Scene (source_scene_id / parent_acquisition_stem)
         └── Level 3: Satellite Orbit Pass (orbit_pass_id: satellite, orbit, datatake, date)
               └── Level 4: Slice / Vignette Instance (slice_index / vignette_index)
```

### Identity Invariants:
- A slice filename alone (e.g. `...-010.tiff`) does **not** constitute an identity.
- Two slices derived from the same Level-2 parent acquisition scene share hydrodynamic, atmospheric, and radar backscatter conditions and are **strictly co-dependent**.
- Any sample whose Level-2 parent identity cannot be unambiguously traced to an authoritative source is classified as `UNKNOWN` and is **strictly prohibited from entering the holdout benchmark**.

---

## 6. Scene-Level Grouping Firewall

### Partitioning Target Ratios:
- **TRAIN:** $\sim 70\%$ of unique parent groups
- **DEV (Validation):** $\sim 15\%$ of unique parent groups
- **HOLDOUT (Benchmark):** $\sim 15\%$ of unique parent groups

### Deterministic Group Partitioning Algorithm:
```python
# Deterministic Scene-Level Grouping Pseudocode
1. Extract all unique parent grouping keys:
     G_IW = {scene_id for all IW slices}          # 484 unique parent scenes
     G_WV = {orbit_pass_id for all WV vignettes}  # 1,678 unique orbit passes
     G_all = sorted(list(G_IW.union(G_WV)))       # Lexicographically sorted

2. For each group g in G_all:
     hash_val = SHA256(SALT + g.encode('utf-8'))
     group_sort_key[g] = hash_val
     slice_count[g] = count_slices_in_group(g)

3. Sort G_all by group_sort_key to achieve deterministic pseudo-random order.

4. Initialize partition bins:
     TRAIN_groups, DEV_groups, HOLDOUT_groups = [], [], []
     target_train = 0.70 * total_slices
     target_dev   = 0.15 * total_slices
     target_hold  = 0.15 * total_slices

5. Sequentially assign entire groups to partitions using constrained greedy bin-packing:
     For g in sorted_G_all:
         Assign all slices in g to exactly ONE partition (TRAIN, DEV, or HOLDOUT)
         Enforce: slices(g) are NEVER divided across partition boundaries.

6. Strict Firewall Assertion:
     assert intersection(TRAIN_groups, DEV_groups) == empty
     assert intersection(TRAIN_groups, HOLDOUT_groups) == empty
     assert intersection(DEV_groups, HOLDOUT_groups) == empty
```

---

## 7. IW and WV Independence Architecture

The dataset comprises two distinct operational acquisition modes with different spatial-temporal dependencies:

| Mode | Volume | Intermediate Origin | Grouping Key | Group Count | Independence Governance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IW** (Interferometric Wide) | 2,628 slices | Li et al. (Zenodo) from S1 Level-1 GRD | `source_scene_id` | 484 scenes | Slices from the same IW scene represent contiguous along-track and across-swath segments of a single $250\text{ km} \times 200\text{ km}$ acquisition. Grouping unit: **Parent Scene**. |
| **WV** (Wave Mode) | 2,383 vignettes | TenGeoP-SARwv (Wang et al., 2019) from S1 Level-1 SLC | `orbit_pass_id` | 1,678 passes | Vignettes are $20\text{ km} \times 20\text{ km}$ leap-frog ocean snapshots acquired every 100 km along orbit tracks. Sibling vignettes from the same pass share atmospheric stability and wave conditions. Grouping unit: **Orbit Pass**. |

---

## 8. Label / Image Correspondence Contracts

To ensure scientific integrity without premature geodetic overclaims, three separate correspondence contracts are established:

```
Contract A: Pixel-Space Label/Image Alignment
   (Does label mask pixel [r, c] match Li SAR image pixel [r, c]?)
   --> MANDATORY PREREQUISITE FOR OPS-01 TRAINING ELIGIBILITY.
   --> Verified via spatial resolution (256x256), dtype, and raster bounding checks.

Contract B: Geographic Coordinate Correspondence
   (Does pixel [r, c] map to exact geodetic latitude/longitude?)
   --> CONDITIONAL ENGINEERING RECONSTRUCTION.
   --> Based on Model B bilinear interpolation; must NOT be claimed as independent georegistration.

Contract C: Parent-Scene Provenance Correspondence
   (Does slice belong to the declared Sentinel-1 SAFE acquisition?)
   --> MANDATORY PREREQUISITE FOR LEAKAGE FIREWALL.
   --> Verified via multi-archive manifest lineage.
```

---

## 9. Backscatter Intensity Cross-Correlation Spot-Check Design

Prior to authorizing OPS-01 training or final dataset freeze, an empirical physical spot-check must be executed on all control scenes where Level-1 SAFE granules and Li GeoTIFF slices are co-located:

### Execution Protocol:
1. **Target Granules:** Available Level-1 GRD products (including Controls 1 and 2).
2. **Native Window Extraction:** Extract native Level-1 window $[min\_line, max\_line] \times [min\_pixel, max\_pixel]$.
3. **Radiometric Calibration:** Convert digital numbers (DN) to radar backscatter cross-section $\sigma^0$ using XML calibration look-up tables (LUTs).
4. **Resampling Simulation:** Apply $10\times 10$ block averaging to the native window to produce a simulated $256 \times 256$ 100 m raster under both Center and Edge conventions.
5. **Dynamic Range Normalization:** Convert both simulated native raster and Li GeoTIFF to decibels ($\text{dB}$) and apply zero-mean unit-variance ($z$-score) standardization.
6. **Cross-Correlation Computation:**
   - Compute 2D Normalized Cross-Correlation (NCC) surface over $\pm 10$ pixel search window.
   - Compute Pearson correlation coefficient ($r$).
   - Compute Normalized Root Mean Squared Error (NRMSE).
7. **Orientation & Inversion Checks:** Test row-flip, col-flip, and transpose to empirically verify coordinate axes.

---

## 10. Alignment Decision Gate

| Gate State | Quantitative Threshold Criteria | Operational Consequence |
| :--- | :--- | :--- |
| **`ALIGNMENT_PASS`** | NCC peak at $(0, 0) \pm 0.5$ pixels, $\text{NCC} \ge 0.85$, Pearson $r \ge 0.85$. | Alignment confirmed in physical intensity space; sub-pixel registration valid for 100 m grid. |
| **`ALIGNMENT_CONDITIONAL`** | NCC peak displacement within $\pm 2.0$ pixels, $\text{NCC} \ge 0.70$. Sub-pixel offset quantified. | Permitted for OPS-01 training only as a conditional engineering reconstruction with declared offset buffer. |
| **`ALIGNMENT_FAIL`** | NCC peak displacement $> 2.0$ pixels or $\text{NCC} < 0.70$, or persistent axis reflection. | Physical correspondence refuted. Slices from this parent are **STRICTLY DISQUALIFIED** from training and benchmarking. |

---

## 11. Negative Sampling Strategy

OPS-01 must be protected against false-positive look-alike over-prediction through balanced negative sampling:
- **Anchor 1: Ambient Clean Seawater (`BG`):** Sample across calm, moderate, and rough sea states.
- **Anchor 2: Natural Dark Look-Alikes (`BS`, `LWA`, `IWs`, `OF`, `Eddy`):** Ensure sufficient representation of biogenic films, wind shadows, and internal wave troughs to train discriminative boundaries.
- **Anchor 3: Bright Atmospheric & Wave Clutter (`AF`, `RF`, `WS`, `POW`, `MCC`):** Represent rain downdrafts, wind streaks, and swell fields to prevent weather-induced false alarms.
- **Anchor 4: Anthropogenic Corner Reflectors (`HM`):** Include ships and platforms as discrete point-target negatives.

---

## 12. Class-Balance Measurement Plan

Before any loss-function weighting or data rebalancing is applied:
1. **Mandatory Pre-Training Metrics:**
   - Image count per class ($N_{\text{images}}$).
   - Pixel count and dataset area percentage ($N_{\text{pixels}}$, $\%$).
   - Connected-component (instance) count per class.
   - Source scene diversity (number of unique parent scenes containing each class).
   - Dominant-parent concentration ratio ($\max(\text{slices from single scene}) / N_{\text{total slices}}$).
2. **Policy Against Premature Reweighting:**
   No arbitrary inverse-frequency or focal weighting may be introduced without first evaluating an unweighted baseline model on the DEV split to diagnose actual capability deficits.

---

## 13. Comprehensive 10-Point Leakage Audit

Prior to freezing any split manifest, the dataset must pass all 10 automated leakage checks:
1. **Parent Scene Overlap:** $\text{TRAIN} \cap \text{DEV} = \emptyset$, $\text{TRAIN} \cap \text{HOLDOUT} = \emptyset$, $\text{DEV} \cap \text{HOLDOUT} = \emptyset$.
2. **Source Product ID Overlap:** Zero Level-1 SAFE granule overlap across splits.
3. **Duplicate File Content:** Zero SHA-256 bitwise duplicate images across splits.
4. **Spatial Footprint Overlap:** Bounding polygons of slices in different partitions must not intersect unless verified as independent temporal acquisitions.
5. **Temporal Proximity:** Slices from the same orbit pass or within $< 1\text{ hour}$ must occupy the same partition.
6. **Wave Mode Orbit Pass Overlap:** Zero `orbit_pass_id` overlap across splits.
7. **Cache & Derivative Isolation:** Zero shared preprocessing caches across partitions.
8. **Mask Identicality:** Zero duplicated annotation masks across splits.
9. **Geographic Cluster Separation:** Maximum feasible geographic cluster grouping.
10. **Metadata Manifest Leakage:** Verify that no split manifest incorporates holdout labels into training normalization statistics.

---

## 14. Untouched Holdout Governance

- **Firewall Isolation:** The OPS-01 holdout split ($\sim 15\%$ of parent groups) is permanently isolated.
- **Strict Prohibitions:**
  - Zero decision threshold tuning against holdout.
  - Zero hyperparameter or architecture selection using holdout metrics.
  - Zero loss reweighting iterations guided by holdout performance.
- **Independence from Part-III:** OPS-01's holdout is an internal look-alike capability benchmark; it is completely independent of the quarantined external **Part-III** benchmark.

---

## 15. Dataset Versioning Schema

Every generated manifest and model artifact must record:
```json
{
  "ops01_dataset_version": "1.0.0",
  "source_manifest_sha256": "<SHA256 of source catalog>",
  "split_manifest_sha256": "<SHA256 of split manifest>",
  "taxonomy_version": "1.0.0",
  "alignment_protocol_version": "1.0.0-protocol",
  "preprocessing_version": "canonical-100m-v1",
  "sampling_strategy_version": "scene-grouped-70-15-15-v1",
  "random_seed": 42,
  "creation_timestamp_utc": "2026-09-13T..."
}
```

---

## 16. Incident Governance

Any failure during dataset construction, spot-checking, or leakage auditing must generate a formal incident record in telemetry and reports:
- `incident_id`: e.g. `INC-8-01`
- `title`: Short descriptive title
- `severity`: `LOW` / `MEDIUM` / `HIGH` / `CRITICAL`
- `description`: Detailed technical description
- `root_cause`: Underlying architectural or methodological flaw
- `guardrail_blindspot`: Why existing tests did not prevent it
- `correction`: Implemented technical fix
- `regression_test`: Test name verifying prevention
- `lesson_learned`: Institutional methodology rule

---

## 17. Regression Guardrail Test Results

The protocol test suite was executed via pytest:
```bash
python -m pytest tests/test_phase_7c_alignment_guardrails.py tests/test_phase_7c_r1_methodology_guardrails.py tests/test_phase_7c_r2_alignment_evidence_guardrails.py tests/test_phase_8_p0_ops01_protocol_guardrails.py -v
```

**Results:**
- `test_phase_7c_alignment_guardrails.py`: **30 passed**
- `test_phase_7c_r1_methodology_guardrails.py`: **20 passed**
- `test_phase_7c_r2_alignment_evidence_guardrails.py`: **15 passed**
- `test_phase_8_p0_ops01_protocol_guardrails.py`: **17 passed**
- **Cumulative Test Count:** **82 passed, 0 failed** in 1.49s.

---

## 18. Training Authorization Boundary

$$\mathbf{\text{CRITICAL PROTOCOL INVARIANT}}$$
1. **Protocol definition does NOT authorize model training.**
2. **Dataset construction does NOT automatically authorize model training.**
3. **Training requires a separate, explicit operator authorization after:**
   - Formal operator sign-off on this protocol specification.
   - Successful execution of the Backscatter Intensity Cross-Correlation Spot-Check.
   - Completion and passage of the 10-Point Leakage Audit.
   - Freeze and SHA-256 hashing of the split manifest.
   - Formal isolation of the Holdout benchmark.
   - Final end-to-end dataset integrity verification.

Zero training scripts were run. Zero GPU compute was invoked.

---

## 19. Git State & Frozen Invariants

- **Git Branch:** `master`
- **Staged Changes:** **0 files (empty)** (`git diff --cached --name-status`)
- **Unstaged Tracked Changes:** 2 pre-existing files (`.gitignore`, `src/ocean_sentinel/ingestion/dataset.py`)
- **Zero Mutating Git Commands:** `git add`, `commit`, `push`, `reset`, `clean` strictly avoided.
- **EXP-06 Checkpoint (`best_model.pt`):** `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` (BITWISE VERIFIED)
- **Part-I Manifest (`internal_development_split_manifest.json`):** `17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072` (BITWISE VERIFIED)
- **Operating Threshold $\tau$:** `0.22` (BITWISE VERIFIED)
- **Part-III Benchmark:** Quarantined under Rule 38 (UNTOUCHED)

---

## 20. Final Decision & Recommendation

### Authoritative Decision:
$$\mathbf{A. \text{ PHASE 8 PROTOCOL READY FOR OPERATOR APPROVAL}}$$

The Phase 8-P0 protocol specification is mathematically sound, forensically complete, strictly respects the Phase 7C-R2 evidence boundary, enforces hard scene-level leakage firewalls, eliminates premature training assumptions, and establishes clear gates prior to dataset freeze or training.

### Next Authorized Action:
Await operator review and formal approval of this protocol. Upon approval, proceed to **Phase 8-P1: Forensic Source Verification & Cross-Correlation Spot-Check Execution**.
