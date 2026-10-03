# EXP-07-P0-C12: OPS-02 Multi-Scene Data Expansion Design, Acquisition Specification, Provenance Architecture, and Dataset-Readiness Gate

- **Phase:** `EXP-07-P0-C12`
- **Date:** `2026-09-14`
- **Role:** Data Architecture & Forensic Reviewer
- **Target Campaign:** `OPS-02 Multi-Scene Dataset Expansion`
- **Repository:** `D:\Projects\ocean-sentinel`
- **Branch:** `master`
- **Final Decision:** `A = PASS (OPS-02 design is scientifically coherent and ready for controlled acquisition/build)`
- **Training Authorization:** `NO (Strictly Prohibited in C12)`
- **Acquisition Authorization:** `YES (Authorized for Controlled Acquisition and Build under OPS-02 Specification)`

---

## 1. WHY OPS-02 EXISTS

Phase **OPS-02** exists because the forensic review in C11 decisively established that repeated model training on the frozen 27-parent OPS-01 dataset has reached a hard ceiling of scientific utility. 

In EXP-07 Seeds 42 and 101, the model achieved a modest DEV mIoU range of $[0.11903, 0.13782]$. Four rare classes (Atmospheric Front, Ocean Front, Rain Footprint, and Artificial Objects) produced an empirical IoU of `0.00000` across both seeds, and Parent Scene 01 suffered a 100% representation collapse into Background and Wind Streaks. 

Critically, C11 proved that **5 of the 12 canonical classes possessed exactly 0 Ground Truth pixels in the DEV split**, while training classes were represented by as few as 1 to 4 independent parent scenes. Under such severe scene scarcity, the model is forced to memorize scene-specific radiometric textures rather than learning generalized geophysical and hydrodynamic representations. 

Accumulating further training runs (such as Seed 2024) on the existing split consumes compute without answering any open scientific question. The primary structural bottleneck is not optimization stochasticity, loss weighting, or network architecture—it is **parent-scene scarcity and limited physical representation quality**. OPS-02 exists to expand the physical scene foundation from 27 parent scenes to at least 60–120 independent acquisitions, providing the statistical degrees of freedom necessary for true cross-scene generalization.

---

## 2. WHAT C11 ACTUALLY ESTABLISHED

The adversarial review in C11 established the following verified empirical facts:
1. **Zero Protocol Drift Replicate:** Seed 101 was executed with exact configuration fidelity to Seed 42 across all 17 parameter blocks.
2. **Two-Seed Headline Range:** DEV mIoU spanned $[0.11903, 0.13782]$ ($+15.79\%$ relative delta), establishing the baseline stochastic variation under fixed conditions.
3. **Reproducible Tail-Class Failure:** Tail classes (AF, OF, RF, HM) consistently failed to produce true positive predictions in both seeds.
4. **Third-Class Cannibalization Mechanism:** An inspection of the cell-level confusion matrices disproved the narrative that Biological Slicks (BS) and Low Wind Areas (LWA) simply swapped labels. In Seed 101, **Oceanic Eddy predictions acted as an attractor, absorbing 63.75% of Biological Slick pixels (82,851 pixels)**, which suppressed false-positive leakage into LWA and doubled LWA precision ($20.8\% \to 49.4\%$).
5. **Reproducible Scene-Level Collapse:** Parent Scene 01 suffered catastrophic collapse in both seeds ($0.0069 \to 0.0041$ mIoU), collapsing complex wave patterns into Background and Wind Streaks.
6. **Parameter-Count Ground Truth:** The model strictly contains **14,310,860 trainable parameters** and **14,322,666 state elements** across 192 tensors. The `14,328,268` reported in C10 was a typographical transcription error.

---

## 3. WHAT REMAINS UNKNOWN

Despite the progress of C11, several fundamental questions could not be answered from two seeds on 27 scenes:
1. **Causality of Tail-Class Zero-IoU:** Is tail-class failure caused by training parent scarcity, class-imbalance loss dynamics, or visual feature subtlety in SAR backscatter?
2. **Mechanism of Parent Scene 01 Collapse:** Is Scene 01 failure caused by an unmeasured physical sensor calibration shift, unusual incidence angle, extreme local wind conditions, or model bias toward dominant class priors?
3. **HM Small-Target Limitation:** Is the failure on Artificial Objects (HM) caused by 4-stage UNet spatial pooling dilution, or simply by the near-total absence of training mass (985 pixels, 0.021% of TRAIN) and zero DEV ground truth?
4. **Generalization Across Unseen Basins:** Does the learned segmentation transfer across different global oceanographic regimes, or is it bound to the specific regional waters sampled in OPS-01?
5. **Contextual Separability:** Can SAR backscatter alone distinguish biogenic films from low wind areas without auxiliary wind vector and sea-surface temperature data?

---

## 4. WHAT OPS-02 IS DESIGNED TO TEST

OPS-02 is engineered as a controlled scientific expansion to test five pre-declared hypotheses:
- **Q1 (Parent-Scene Generalization):** Does expanding independent parent-scene diversity from 27 to $\ge 60-120$ significantly reduce cross-scene variance and improve DEV mIoU across unseen acquisitions?
- **Q2 (Scene-Level Representation Collapse):** Does a broader distribution of acquisition geometries and background sea states eliminate catastrophic parent-specific collapse like that observed in Scene 01?
- **Q3 (Rare-Class Learnability):** Does providing $\ge 8$ independent parent scenes per class (with guaranteed representation in DEV and HOLDOUT) enable stable feature learning and nonzero IoU for tail classes (AF, OF, RF, HM, IWs)?
- **Q4 (Geographic and Seasonal Stability):** Does multi-basin sampling across distinct calendar seasons produce models that resist localized seasonal weather bias?
- **Q5 (Lookalike Disambiguation):** Does broader physical context and diverse wind regimes resolve the competitive attractor dynamics observed between BS, LWA, and Eddy?

---

## 5. DEFINITION OF INDEPENDENT PARENT SCENE

In OPS-02, **independence is strictly defined by physical acquisition reality, never by filenames, crops, slices, or annotation boxes**. Two candidates are classified according to the following hierarchy ([`exp07_p0_c12_ops02_parent_identity_rules_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_ops02_parent_identity_rules_v1.json)):

### 5.1 Hierarchy of Independence
1. **`SAME_PARENT` (Identical Physical Acquisition):**
   - Identical complete Sentinel-1 product identifier (e.g. `S1A_IW_GRDH_1SDV_20220201T...`).
   - Or identical raw datatake ID and zero-Doppler time range.
   - Or spatial intersection $\ge 90\%$ with acquisition time delta $\Delta t < 60$ seconds.
   - *Rule:* All tiles from the `SAME_PARENT` must reside in the exact same partition.
2. **`RELATED_ACQUISITIONS` (Correlated Along-Track Passes):**
   - Adjacent along-track slices from the same satellite pass ($\Delta t < 10$ minutes).
   - Or same footprint (overlap $\ge 20\%$) acquired within $\Delta t \le 24$ hours.
   - *Rule:* Must be co-partitioned with their related counterpart or quarantined.
3. **`POTENTIALLY_DEPENDENT` (Repeat-Pass Overlaps):**
   - Same relative orbit track with spatial overlap $\ge 10\%$ acquired within the 12-day repeat cycle.
   - Or persistent stationary targets (fixed offshore platforms, reefs).
   - *Rule:* Requires spatial buffering ($\ge 15\text{ km}$) and feature masking before cross-partition assignment.
4. **`INDEPENDENT` (True Physical Independence):**
   - Geographically disjoint footprints (zero spatial intersection; centroid distance $\ge 50\text{ km}$).
   - Or overlapping footprints separated by $\Delta t \ge 30$ days under independently verified distinct synoptic wind/wave conditions.
   - Or different orbital tracks with negligible spatial intersection ($< 5\%$).

---

## 6. DEPENDENCY AND LEAKAGE RULES

To guarantee that OPS-02 does not introduce data leakage:
- **Rule of Pre-Slicing Partitioning (`GOV-RULE-075`):** Partitioning into TRAIN, DEV, and HOLDOUT occurs strictly at the parent scene cluster level **BEFORE** spatial tiling or patch extraction.
- **No Cross-Partition Slicing:** Under no circumstances may adjacent or overlapping crops from a single parent scene be distributed across different partitions.
- **Duplicate Imagery Firewall:** Exhaustive pairwise SHA256 hashing across raw image files and derived masks ensures zero identical or shifted duplicate crops enter the splits.
- **Reprocessed Version Lock:** Reprocessed products (e.g. IPF 2.x vs IPF 3.x) of the same datatake must be locked to the same partition.

---

## 7. GEOGRAPHIC DESIGN

Geographic diversity must prevent the model from overfitting to regional bathymetry, localized current systems, or confined inland waters.

### 7.1 Formal Geographic Ontology
Each candidate scene must record both its broad **Ocean Basin** and its specific **Regional / Marginal Sea**:
- **Major Basins:** North Atlantic, South Atlantic, North Pacific, South Pacific, Indian Ocean, Mediterranean Sea, Arctic Marginal Seas.
- **Marginal / Regional Seas:** South China Sea, East China Sea, Gulf of Mexico, North Sea, Baltic Sea, Arabian Sea, Bay of Bengal, Norwegian Sea.
- **Coastal Proximity Regimes:** `OPEN_OCEAN` ($> 50\text{ km}$ from land), `CONTINENTAL_SHELF` ($10-50\text{ km}$), `COASTAL_NEARSHORE` ($< 10\text{ km}$), `ENCLOSED_BAY_HARBOR`.
- **Anti-Conflation Invariant:** Never collapse marginal seas into generic basins without recording the specific sea name. No single geographic region may constitute $> 50\%$ of the dataset.

---

## 8. TEMPORAL DESIGN

Temporal diversity must cover seasonal and synoptic meteorological variations:
- **Time Window:** 2016 to present (spanning operational Sentinel-1A and Sentinel-1B missions).
- **Temporal Distribution Invariant:** Acquisitions must be distributed across at least 3 distinct calendar years and at least 8 distinct calendar months.
- **Anti-Clustering Rule:** No single calendar quarter (e.g. Q1 winter) may account for $> 35\%$ of acquired parent scenes, preventing seasonal bias in wind regimes or biogenic plankton blooms.

---

## 9. SENSOR AND ACQUISITION CONDITION DESIGN

Sentinel-1 SAR acquisition conditions strongly influence surface signature contrast:
- **Polarization:** Primary priority is **VV** (vertical transmit, vertical receive), which provides the strongest sensitivity to ocean capillary wave roughness. Secondary priority is dual-polarization **VV + VH**, where cross-polarized VH provides valuable contrast for vessels, rain cells, and high-wind boundaries.
- **Swath Mode:** Interferometric Wide (IW) swath mode (250 km swath width, $5\text{m} \times 20\text{m}$ spatial resolution).
- **Pass Direction:** Balanced sampling requiring at least $30\%$ Ascending and at least $30\%$ Descending passes to ensure look-direction diversity relative to prevailing wind vectors.
- **Incidence Angles:** Representation across all three IW sub-swaths (IW1: $29.1^\circ - 35.8^\circ$, IW2: $34.8^\circ - 40.0^\circ$, IW3: $38.7^\circ - 46.0^\circ$).

---

## 10. CLASS-COVERAGE TARGETS

Targets are defined across three tiers: **Independent Parent Scenes**, **Derived Tiles**, and **Valid Pixel Mass** ([`exp07_p0_c12_ops02_campaign_spec_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_ops02_campaign_spec_v1.json)):

| Dense Index | Class Name | Source Label ID | Minimum Parent Scenes | Target Derived Tiles | Target Valid Pixel Mass |
| :---: | :--- | :---: | :---: | :---: | :---: |
| 0 | BG (Background Seawater) | 0 | 60 | 300 | $\ge 2,000,000$ |
| 1 | AF (Atmospheric Front) | 1 | 10 | 50 | $\ge 200,000$ |
| 2 | BS (Biological Slicks) | 2 | 20 | 100 | $\ge 400,000$ |
| 3 | LWA (Low Wind Area) | 4 | 15 | 75 | $\ge 300,000$ |
| 4 | MCC (Mesoscale Cellular Convection)| 5 | 15 | 75 | $\ge 500,000$ |
| 5 | OF (Ocean Front) | 6 | 12 | 60 | $\ge 250,000$ |
| 6 | POW (Pure Ocean Wave) | 7 | 15 | 75 | $\ge 500,000$ |
| 7 | RF (Rain Cell / Footprint) | 8 | 12 | 60 | $\ge 250,000$ |
| 8 | WS (Wind Streaks) | 10 | 25 | 125 | $\ge 800,000$ |
| 9 | Eddy (Oceanic Eddy) | 11 | 15 | 75 | $\ge 350,000$ |
| 10 | IWs (Internal Waves) | 12 | 12 | 60 | $\ge 300,000$ |
| 11 | HM (Artificial Objects) | 13 | 15 | 50 | $\ge 15,000$ |

*Excluded Source Classes:* Source Label 3 (Iceberg), Source Label 9 (Sea Ice), and Source Label 14 (Mineral Oil Spill) are strictly mapped to `ignore_index = -100`.

---

## 11. HARD-NEGATIVE AND LOOKALIKE STRATEGY

Ocean Sentinel's long-term operational mission is automated mineral oil spill detection. However, EXP-07 and OPS-02 represent multiclass marine phenomenon segmentation, not the oil-spill classification task itself:
- **Lookalike Preservation:** Natural dark-slick phenomena (BS, LWA, IWs) produce low radar backscatter through short-wave dampening or specular reflection. They must be rigorously preserved as distinct classes so future oil-spill models can learn robust false-positive suppression.
- **Boundary Discipline:** OF (Ocean Front) must never be conflated with oil slicks (`GOV-RULE-011`, `GOV-RULE-072`).
- **No Conflated Lookalike Superclasses:** Lookalikes must not be collapsed into an ad-hoc "lookalike" class during OPS-02; each natural phenomenon must retain its specific physical identity.

---

## 12. HM / ANTHROPOGENIC TARGET STRATEGY

- **Canonical Identity:** Class 11 is **Artificial / Anthropogenic Objects (HM)** (`GOV-RULE-072`). It encompasses offshore oil platforms, drilling rigs, offshore wind turbines, aquaculture infrastructure, and vessels.
- **No Premature Taxonomy Mutation:** HM will not be renamed to "Ship" or "Vessel".
- **Roadmap Decoupling:** Future vessel attribution, kinematic tracking, and AIS fusion will be handled via an auxiliary point-target detection/kinematics layer operating in tandem with the semantic segmentation backbone, maintaining clean architectural modularity.

---

## 13. DATA-SOURCE EVALUATION FRAMEWORK

Candidate external data sources are evaluated using a 10-criterion quantitative rubric ([`exp07_p0_c12_ops02_source_evaluation_framework_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_ops02_source_evaluation_framework_v1.json)):
- **Maximum Score:** 70 points. Acceptance requires $\ge 52$ points ($\ge 74\%$) with no critical score $< 3$.
- **Critical Gates:** Parent Traceability (CRIT_02), Annotation Quality (CRIT_04), and Taxonomy Compatibility (CRIT_07) are hard gating criteria. Any candidate source failing any critical gate is automatically quarantined.

---

## 14. LABEL-PROVENANCE STANDARDS

OPS-02 enforces four distinct annotation tiers (`GOV-RULE-076`):
- **Tier A (Expert Manual):** Pixel-level annotations produced by oceanographers and validated by cross-annotator agreement. Eligible for TRAIN, DEV, and HOLDOUT.
- **Tier B (Verified Semi-Automated):** Machine-assisted segmentations reviewed and corrected by marine specialists. Eligible for TRAIN and DEV.
- **Tier C (Reconstructed Legacy):** Restored masks from documented scientific publications. Eligible for TRAIN only.
- **Tier D (Weak / Unverified):** Coarse bounding boxes or unvalidated model pseudo-labels. **Strictly Quarantined.**

---

## 15. RAW VS. DERIVED DATA POLICY

- **Authoritative Raw Artifacts:** Immutable Level-1 GRD GeoTIFF files and original vector annotation layers stored in cold storage with permanent SHA256 hashes.
- **Deterministic Derivation:** Derived $256\times 256$ patches and dense masks are generated via fully deterministic, reproducible scripts.
- **Lineage Integrity:** Every derived tile must record its source product ID, bounding polygon, processing version, and derivation timestamp. If a derived tile cannot be deterministically regenerated, it is invalid.

---

## 16. DATA-QUALITY GATES

Before ingestion into the OPS-02 manifest, every candidate tile must pass 7 automated raster checks:
1. Valid GeoTIFF format readable by GDAL / rasterio without errors.
2. Exact spatial dimensions ($256\times 256$ pixels).
3. Single-band float32/uint16 data type.
4. Zero NaN, Inf, or unmasked negative values.
5. NoData / out-of-swath pixels correctly masked to `ignore_index = -100`.
6. Mask values strictly bounded in $[0, 11]$ or equal to `-100`.
7. Perfect cryptographic hash verification against raw source bytes.

---

## 17. SPLIT DESIGN

The dataset is partitioned into three disjoint subsets ([`exp07_p0_c12_ops02_split_specification_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_ops02_split_specification_v1.json)):
- **TRAIN (60% - 70% of parent scenes):** Dedicated to representation learning.
- **DEV (15% - 20% of parent scenes):** Dedicated to checkpoint selection, early stopping, and hyperparameter tuning.
- **HOLDOUT (15% - 20% of parent scenes):** Dedicated to final uncompromised benchmark evaluation.
- **Zero Cross-Split Overlap:** TRAIN, DEV, and HOLDOUT share zero parent acquisitions, zero along-track passes, and maintain a $\ge 50\text{ km}$ spatial buffer between repeat passes.

---

## 18. HOLDOUT PRESERVATION

Because the OPS-01 HOLDOUT was historically evaluated, OPS-02 establishes a **pristine, cryptographically locked evaluation set**:
- Quarantined in an isolated directory tree with read-only permissions.
- Absolute prohibition of holdout access for exploratory data analysis, class weighting, loss balancing, or threshold tuning.
- Any unauthorized access immediately invalidates the benchmark run.

---

## 19. MINIMUM DATASET SUFFICIENCY GATE

OPS-02 defines a 9-dimension readiness matrix ([`exp07_p0_c12_ops02_sufficiency_gate_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_ops02_sufficiency_gate_v1.json)). Hard failure conditions include:
- Total parent scenes $< 50$.
- Any priority class with $< 4$ independent parent scenes.
- Any canonical class with 0 GT pixels in DEV or HOLDOUT.
- Geographic dominance $> 70\%$ from a single regional sea.
- Any shared parent acquisition across partitions.

---

## 20. STOP CONDITIONS

Acquisition must immediately halt and trigger quarantine if:
- Candidate imagery cannot be unambiguously linked to an authentic Level-1 product ID.
- Spatial overlap $> 5\%$ is detected between a candidate scene and an existing DEV/HOLDOUT parent.
- Mineral oil spills are found conflated with natural slicks.
- Source annotations fall to Tier D quality.
- Licensing terms restrict open research redistribution.

---

## 21. BRUTE-FORCE VS. OPTIMIZED-CHECK STRATEGY

OPS-02 establishes clear rules for computational optimization:
- **Brute-Force Mandatory:** Pairwise SHA256 hash collision checks across all images and masks; exact product ID string comparison against historical OPS-01 catalogs; 100% technical raster QC on every tile.
- **Safe Optimization Permitted:** Spatial overlap detection may utilize an R-tree minimum bounding box (MBB) index to filter candidate pairs before computing expensive polygon intersections. *Proof of Safety:* An MBB filter is guaranteed to produce zero false negatives; non-overlapping bounding boxes mathematically cannot have overlapping polygons.

---

## 22. PROVENANCE MANIFEST SCHEMA

All OPS-02 samples will be indexed in a unified machine-readable JSON manifest compliant with Draft-07 schema specifications ([`exp07_p0_c12_ops02_provenance_schema_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_ops02_provenance_schema_v1.json)), requiring 24 standardized attributes per tile, including platform, orbit pass, relative track, geographic metadata, annotation tier, source/derived hashes, and quarantine status. Unknown values are represented explicitly as `"UNKNOWN"` or `null`.

---

## 23. REPRODUCIBILITY REQUIREMENTS

OPS-02 adheres to **Level A / Level B Operational Reproducibility**:
- Complete configuration files, manifest fingerprints, and environment locks (`uv.lock`) are committed to version control.
- Ingestion and tiling pipelines are fully script-driven and deterministic.
- Given the raw Sentinel-1 Level-1 products and the frozen derivation code, the entire dataset can be rebuilt bit-for-bit.

---

## 24. FUTURE OCEAN SENTINEL INTEGRATION

OPS-02 provides the foundational perception layer for the broader Ocean Sentinel roadmap:
```
[OPS-02 Multiclass Perception Backbone]
      │
      ├──> [Contextual Hard-Negative Layer] ──> [Mineral Oil Spill Detection Engine]
      │                                                │
      └──> [Anthropogenic HM Detections]               │
                  │                                    │
                  v                                    v
      [Vessel Kinematics & AIS Fusion] ────> [Investigative Attribution & Tracking]
```
By maintaining clean task boundaries, OPS-02 enriches the environmental context without entangling the model in downstream task-specific requirements.

---

## 25. FINAL TRAINING-READINESS GATE

```
================================================================================
FINAL DECISION: A = PASS
TRAINING AUTHORIZATION: NO (Strictly Prohibited in C12)
ACQUISITION AUTHORIZATION: YES (Authorized for Controlled Acquisition and Build)
CAMPAIGN STATUS: OPS-02 ACQUISITION DESIGN FORMALLY FROZEN
================================================================================
```

### Pre-Training Checklist (Must be satisfied before Phase C13 Training Authorization):
- [ ] $\ge 60$ independent parent scenes successfully acquired, verified, and ingested.
- [ ] All 12 canonical classes verified present in TRAIN, DEV, and HOLDOUT splits.
- [ ] Zero parent-scene or along-track pass sharing across partitions.
- [ ] 100% technical raster QC pass rate across all candidate tiles.
- [ ] Cryptographic hash manifest compiled and locked (`ops02_dataset_manifest_v1.json`).
- [ ] Automated regression tests passing across all data-quality and firewall guardrails.
