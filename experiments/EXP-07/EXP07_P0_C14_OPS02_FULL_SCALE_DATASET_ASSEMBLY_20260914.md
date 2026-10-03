# EXP-07-P0-C14: OPS-02 Full-Scale Physical Acquisition, Independent-Parent Clustering, Pre-Slice Partitioning, Dataset Assembly, Provenance/QC, and Training-Readiness Gate

```
================================================================================
FINAL FEASIBILITY DECISION: A = DATASET ASSEMBLY PASS
PHYSICAL ACQUISITION: COMPLETE (64 Independent Datatake Clusters / 212 Samples)
DATASET CANDIDATE STATUS: OPS02_v1_CANDIDATE
MODEL TRAINING AUTHORIZATION: NO (Strictly Prohibited in C14)
SEED 2024 EXECUTION: NO (Strictly Prohibited)
PROTECTED EXP-07 HOLDOUT ACCESS: ZERO / PRISTINE AND UNTOUCHED
================================================================================
```

---

## 1. Execution Identity

- **Experiment / Phase:** `EXP-07-P0-C14`
- **Campaign Title:** OPS-02 Full-Scale Physical Acquisition, Independent-Parent/Datatake Clustering, Pre-Slice Partitioning, Provenance/QC Pipeline Validation, and Training-Readiness Gate
- **Execution Date:** 2026-09-14 (UTC)
- **Repository:** `D:\Projects\ocean-sentinel`
- **Branch:** `master`
- **Execution Engine:** Python 3.10.9 with GDAL/rasterio via `.venv\Scripts\python.exe`
- **Authoritative Telemetry:** [`scratch/exp07_p0_c14_run_state.json`](file:///D:/Projects/ocean-sentinel/scratch/exp07_p0_c14_run_state.json) (`status: COMPLETED`, elapsed: 1353.9s)
- **Safety Boundary Invariants:** Zero active training processes, zero inference for model selection, zero alteration to frozen EXP-07 training hyperparameters, zero access to the protected EXP-07 holdout.

---

## 2. C13 Input Verification

All primary C13 reports and specifications were verified directly from disk before state mutation:
1. `experiments/EXP-07/EXP07_P0_C13_OPS02_ACQUISITION_PILOT_AND_FEASIBILITY_20260914.md`
2. `data/metadata/exp07_p0_c13_source_registry_v1.json`
3. `data/metadata/exp07_p0_c13_candidate_inventory_v1.json`
4. `data/metadata/exp07_p0_c13_parent_identity_audit_v1.json`
5. `data/metadata/exp07_p0_c13_provenance_manifest_v1.json`
6. `data/metadata/exp07_p0_c13_qc_results_v1.json`
7. `data/metadata/exp07_p0_c13_coverage_matrix_v1.json`
8. `data/metadata/exp07_p0_c13_sufficiency_reassessment_v1.json`
9. `data/metadata/exp07_p0_c13_source_crosswalk_v1.json`

---

## 3. C13 Residual Audit & Recomputed Reconciliation

Rather than accepting C13 narrative assertions at face value, all critical candidate and catalog statistics were independently recomputed from the filesystem and recorded in [`data/metadata/exp07_p0_c14_c13_reconciliation_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c14_c13_reconciliation_v1.json):

| Metric Name | C13 Reported | C14 Observed | Difference | Reconciliation Status | Primary Evidence Source |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **OPS-01 Unique Parents** | 27 | 27 | 0 | **EXACT MATCH** | `data/metadata/ops01_physical_dataset_manifest_v4.json` |
| **Li IW Total Scenes** | 484 | 484 | 0 | **EXACT MATCH** | `data/metadata/li_iw_source_scene_manifest.json` |
| **Li IW Total Slices** | 2,628 | 2,628 | 0 | **EXACT MATCH** | `data/metadata/li_iw_source_scene_manifest.json` |
| **OPS-01 Overlap Scenes** | 27 | 27 | 0 | **EXACT MATCH** | Intersection of OPS-01 parents and Li IW catalog |
| **Uningested Candidate Scenes** | 457 | 457 | 0 | **EXACT MATCH** | 484 total scenes minus 27 OPS-01 overlap scenes |
| **Uningested Datatakes** | 373 | 373 | 0 | **EXACT MATCH** | Unique `mission_data_take_id` across 457 uningested scenes |
| **Uningested Slices with Labels** | 2,480 | 2,480 | 0 | **EXACT MATCH** | Physical PNG files present in `scratch/all_labels/label/*.png` |

---

## 4. Source Candidate Pool

The candidate pool consists of 457 uningested scenes spanning 373 independent mission datatakes from the authoritative Li et al. (2020) Interferometric Wide (IW) archive (Zenodo 10.5281/zenodo.14279466). Each candidate record tracks:
- Canonical Sentinel-1 scene ID
- Sentinel-1 mission datatake identifier
- Satellite platform (Sentinel-1A: 455, Sentinel-1B: 2)
- Absolute and relative orbital passes
- Coordinated Universal Time (UTC) start/stop timestamps
- Ground Range Detected (GRD) sensor mode with VV co-polarization
- WKT geographic footprint
- Physical slice indexes and matching label mask availability.

---

## 5. Parent Clustering Methodology (`GOV-RULE-077`)

To prevent along-track pseudo-replication, all scenes sharing a Sentinel-1 mission datatake ID (`mission_data_take_id`), platform, and relative orbit were clustered into unified parent acquisition clusters prior to partitioning:
- 457 uningested scenes consolidated into **373 independent datatake clusters**.
- Multi-slice acquisitions acquired within seconds of each other along the same orbital track are treated as a single physical degree of freedom.
- Authoritative manifest: [`data/ops02/manifests/ops02_parent_cluster_manifest_v1.json`](file:///D:/Projects/ocean-sentinel/data/ops02/manifests/ops02_parent_cluster_manifest_v1.json).

---

## 6. Cross-Source Deduplication (`GOV-RULE-078`)

Deduplication was evaluated across candidate sources:
- Zero overlap with the 27 historical OPS-01 parent scenes (`ops01_parent_overlap_count = 0`).
- Cross-repository acquisitions (DARTIS, TenGeoP-SARwv) were crosswalked against the Sentinel-1 master catalog; no duplicates entered the candidate selection pool.
- Authoritative audit: [`data/ops02/audits/ops02_cross_source_duplicate_audit_v1.json`](file:///D:/Projects/ocean-sentinel/data/ops02/audits/ops02_cross_source_duplicate_audit_v1.json).

---

## 7. Selected Independent Parents

From the 373 available datatakes, a stratified pool of **64 independent datatake clusters** was selected:
- Exceeds the C12 minimum target of $\ge 60$ independent parent acquisitions.
- Spans all 8 operational Sentinel-1 years from 2015 through 2022.
- Represents major global oceanic basins and marginal seas.
- Balances tail-class phenomena (HM, OF, Eddy, WS, BS, LWA, AF, RF, POW, MCC, IWs, BG).

---

## 8. HM / Artificial-Object Targeted Acquisition

In accordance with Section 9 of the campaign specification, open-ocean random sampling was avoided for HM because offshore platforms and artificial structures are geographically clustered. Instead, scenes from known offshore infrastructure basins were targeted:
- **North Sea** (offshore wind farms and oil/gas platforms)
- **Gulf of Mexico** (offshore drilling infrastructure)
- **East China Sea** (shipping lanes, aquaculture rafts, and platforms)
- Result: **14 independent parent clusters** containing HM (8 TRAIN, 3 DEV, 3 HOLDOUT), yielding 20 physical samples, fully overcoming the single-scene limitation observed in OPS-01.

---

## 9. Physical Acquisition Results

Physical imagery was materialized using direct windowed reads from the authoritative Level-1 GRD measurement GeoTIFFs on AWS Open Data (`sentinel-s1-l1c`) via rasterio `/vsicurl/`:
- **Total parent clusters assembled:** 64
- **Total physical samples assembled:** 212
- **Image format:** Single-band 32-bit floating point GeoTIFF (`float32`), $256 \times 256$ pixels.
- **Mask format:** Single-band 8-bit unsigned integer PNG (`uint8`), $256 \times 256$ pixels.
- **Storage location:**
  - Images: `data/ops02/derived/images/*.tif`
  - Masks: `data/ops02/derived/masks/*.png`
- **Authoritative manifest:** [`data/ops02/manifests/ops02_physical_dataset_manifest_v1.json`](file:///D:/Projects/ocean-sentinel/data/ops02/manifests/ops02_physical_dataset_manifest_v1.json).

---

## 10. Source License & Redistribution Status

- **Primary Source Archive:** Li et al. (2020) Marine SAR Dataset distributed via Zenodo (DOI: 10.5281/zenodo.14279466) under Creative Commons Attribution 4.0 International (CC-BY 4.0). Permitted for research, adaptation, and redistribution with appropriate attribution.
- **Sensor Data Authority:** Copernicus Sentinel-1 data processed by ESA; open access governed by the European Commission Legal Notice on the use of Copernicus Sentinel data and service information.

---

## 11. Image Quality Control (Layer A — Technical Integrity)

All 212 materialized GeoTIFF rasters passed exhaustive technical verification:
- Dimensionality: Exact $256 \times 256$ pixels (100% pass rate).
- Band count: Exactly 1 band (100% pass rate).
- Data type: 32-bit floating point (`float32`) (100% pass rate).
- Value integrity: Zero `NaN`, zero `Inf`, zero unintended negative values (100% pass rate).
- Radiometric statistics recorded per tile: `raw_min`, `raw_max`, `raw_mean`, `raw_std`, `zeros_count`, `valid_mean`.

---

## 12. Annotation Quality Control (Layer C — Semantic Label Integrity)

All 212 label masks passed semantic verification:
- Spatial correspondence: Exactly matched to image raster dimensions ($256 \times 256$).
- Data format: 8-bit unsigned integer PNG (`uint8`).
- Label values: Strictly bounded within canonical taxonomy space $[0, 11]$.
- **Task Firewall:** Exactly 0 samples contain Mineral Oil Spill (Class 14) (`GOV-RULE-060`).

---

## 13. Taxonomy Mapping

The canonical dense taxonomy established in C12/C13 was preserved without drift:

| Dense Index | Canonical Class Name | Abbreviation | Source Class ID | Semantic Definition |
| :---: | :--- | :---: | :---: | :--- |
| **0** | Background Seawater | BG | 0 | Ambient open ocean surface clutter |
| **1** | Atmospheric Front | AF | 1 | Synoptic/mesoscale air-mass boundary |
| **2** | Biological Slicks | BS | 2 | Natural biogenic surfactant films |
| **3** | Low Wind Area | LWA | 4 | Calm ocean zones ($< 2.5-3.0$ m/s) |
| **4** | Mesoscale Cellular Convection | MCC | 5 | Boundary-layer atmospheric convection cells |
| **5** | Oceanic Front | OF | 6 | Water mass boundary current convergence (*NOT oil*) |
| **6** | Pure Ocean Wave | POW | 7 | Regular swell wave trains |
| **7** | Rain Cell / Footprint | RF | 8 | Precipitation downdraft splash rings |
| **8** | Wind Streaks | WS | 10 | Boundary-layer roll vortex wind streaks |
| **9** | Oceanic Eddy | Eddy | 11 | Mesoscale spiral current shear vortex |
| **10** | Oceanic Internal Waves | IWs | 12 | Subsurface solitary gravity wave packets |
| **11** | Artificial / Anthropogenic Objects | HM | 13 | Offshore platforms, vessels, wind farms (*NOT vessel-only*) |

*Excluded Classes:* Source Label 3 (Iceberg), Source Label 9 (Sea Ice), and Source Label 14 (Mineral Oil Spill) are strictly mapped to `ignore_index = -100`.

---

## 14. Raw $\rightarrow$ Derived Lineage Architecture

Complete bidirectional lineage is maintained for every physical sample:
```
AUTHORITATIVE S3 PRODUCT (e.g. S1A_IW_GRDH_1SDV_20151031T215610...306E)
   │
   ▼
PARENT SCENE / DATATAKE CLUSTER (ops02_cluster_001_00BDE6)
   │
   ▼
EXACT NATIVE WINDOW (row_off=50..2610, col_off=50..2610, 2560x2560 pixels)
   │
   ▼
SPATIAL AGGREGATION (10x10 Block-Mean Amplitude DN Domain)
   │
   ▼
DERIVED SAMPLE PAIR (256x256 float32 GeoTIFF + uint8 PNG mask)
   ├── data/ops02/derived/images/s1a-...-001-16.tif (SHA-256: 554C3ACE...)
   └── data/ops02/derived/masks/s1a-...-001-16.png  (SHA-256: BC1CD47D...)
```

---

## 15. Pre-Slice Partitioning Methodology (`GOV-RULE-075`)

Partitioning was strictly enforced at the **parent datatake cluster level BEFORE spatial tiling**:
- **TRAIN Partition:** 40 parent clusters (~62.5%), 132 physical samples.
- **DEV Partition:** 12 parent clusters (~18.75%), 41 physical samples.
- **HOLDOUT Partition:** 12 parent clusters (~18.75%), 39 physical samples.
- **Inter-partition leakage:** 0% verified (0 shared datatakes, 0 shared parents).
- Authoritative manifest: [`data/ops02/manifests/ops02_partition_manifest_v1.json`](file:///D:/Projects/ocean-sentinel/data/ops02/manifests/ops02_partition_manifest_v1.json).

---

## 16. Holdout Firewall & Protection

The OPS-02 HOLDOUT partition was cryptographically sealed upon creation:
- **Status:** `READ_ONLY_CRYPTOGRAPHICALLY_LOCKED`
- **Model selection access count:** 0
- **Hyperparameter tuning access count:** 0
- **Training access count:** 0
- **Integrity verdict:** `PRISTINE_AND_UNTOUCHED`
- Authoritative audit: [`data/ops02/audits/ops02_holdout_integrity_v1.json`](file:///D:/Projects/ocean-sentinel/data/ops02/audits/ops02_holdout_integrity_v1.json).

---

## 17. Dataset-Wide Multi-Layer QC Results

Audited across all 4 distinct quality control layers ([`data/ops02/audits/ops02_dataset_qc_v1.json`](file:///D:/Projects/ocean-sentinel/data/ops02/audits/ops02_dataset_qc_v1.json)):

| QC Layer | Audit Dimension | Evaluated Criteria | Passed | Failed | Pass Rate |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Layer A** | **Technical Integrity** | Shape $(256, 256)$, bands $= 1$, `float32`/`uint8`, 0 NaN/Inf | 212 | 0 | **100.0%** |
| **Layer B** | **Provenance Integrity** | Product ID, datatake ID, scene ID, SHA-256 hashes complete | 212 | 0 | **100.0%** |
| **Layer C** | **Semantic Label Integrity**| Canonical dense taxonomy $[0, 11]$, 0 Mineral Oil Spill (14) | 212 | 0 | **100.0%** |
| **Layer D** | **Scientific Independence** | 0 cross-split datatake leakage, conservative parent grouping | 212 | 0 | **100.0%** |

---

## 18. Class Coverage Matrix

Audited from the assembled physical dataset ([`data/ops02/audits/ops02_class_coverage_v1.json`](file:///D:/Projects/ocean-sentinel/data/ops02/audits/ops02_class_coverage_v1.json)):

| Canonical Class | Dense Index | TRAIN Parents | DEV Parents | HOLDOUT Parents | Total Parents | TRAIN Samples | DEV Samples | HOLDOUT Samples | Total Samples |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BG** (Background) | 0 | 28 | 10 | 11 | **49** | 66 | 28 | 30 | **124** |
| **AF** (Atmospheric Front) | 1 | 5 | 3 | 2 | **10** | 15 | 6 | 3 | **24** |
| **BS** (Biological Slicks) | 2 | 6 | 2 | 3 | **11** | 17 | 4 | 9 | **30** |
| **LWA** (Low Wind Area) | 3 | 10 | 3 | 2 | **15** | 21 | 4 | 4 | **29** |
| **MCC** (Convective Cells) | 4 | 13 | 7 | 2 | **22** | 27 | 17 | 5 | **49** |
| **OF** (Oceanic Front) | 5 | 4 | 1 | 2 | **7** | 9 | 1 | 3 | **13** |
| **POW** (Ocean Waves) | 6 | 11 | 3 | 3 | **17** | 25 | 3 | 6 | **34** |
| **RF** (Rain Cells) | 7 | 7 | 1 | 4 | **12** | 13 | 2 | 6 | **21** |
| **WS** (Wind Streaks) | 8 | 5 | 2 | 1 | **8** | 9 | 3 | 1 | **13** |
| **Eddy** (Ocean Eddy) | 9 | 5 | 2 | 2 | **9** | 14 | 5 | 6 | **25** |
| **IWs** (Internal Waves) | 10 | 31 | 9 | 9 | **49** | 97 | 31 | 28 | **156** |
| **HM** (Artificial Objects) | 11 | 8 | 3 | 3 | **14** | 12 | 3 | 5 | **20** |

---

## 19. Source Dominance Audit

Audited in [`data/ops02/audits/ops02_source_dominance_v1.json`](file:///D:/Projects/ocean-sentinel/data/ops02/audits/ops02_source_dominance_v1.json):
- Primary Source Archive: Li et al. (2020) Marine SAR Dataset represents 100% of candidate acquisitions in this release.
- Epistemic disclosure: The dataset expands independent physical acquisitions from 27 to 91 total parents, but remains grounded in the single expert-annotated Li IW archive. Multi-source integration (DARTIS, TenGeoP-SARwv) remains conditional pending spatial realignment standards.

---

## 20. Geographic Coverage Audit

Audited in [`data/ops02/audits/ops02_geographic_coverage_v1.json`](file:///D:/Projects/ocean-sentinel/data/ops02/audits/ops02_geographic_coverage_v1.json):
- **North Pacific Ocean:** 10 clusters (East China Sea, South China Sea)
- **North Atlantic Ocean:** 19 clusters (North Sea, Norwegian Sea, Gulf of Mexico, Caribbean Sea)
- **Indian Ocean:** 31 clusters (Arabian Sea, Bay of Bengal)
- **Mediterranean Sea:** 4 clusters (Levantine Basin, Ionian Sea)
- Maximum single-basin concentration: 48.4% (Indian Ocean; well within scientific multi-basin requirements).

---

## 21. Temporal Coverage Audit

Audited in [`data/ops02/audits/ops02_temporal_coverage_v1.json`](file:///D:/Projects/ocean-sentinel/data/ops02/audits/ops02_temporal_coverage_v1.json):
- Earliest acquisition: `2015-10-31T21:56:10Z`
- Latest acquisition: `2022-06-19T06:50:05Z`
- Years represented: 2015 (2), 2016 (8), 2017 (17), 2018 (24), 2019 (4), 2020 (2), 2021 (2), 2022 (5).
- Spans 8 distinct operational years of Sentinel-1.

---

## 22. Acquisition-Condition Coverage Audit

Audited in [`data/ops02/audits/ops02_acquisition_coverage_v1.json`](file:///D:/Projects/ocean-sentinel/data/ops02/audits/ops02_acquisition_coverage_v1.json):
- Sensor mode: 100% Interferometric Wide (IW) swath mode.
- Polarization: 100% VV co-polarized channel.
- Satellite platforms: Sentinel-1A (64 clusters, 100%).
- Spatial aggregation: Standardized 10x10 spatial block mean matching the 100 m nominal multi-looked resolution.

---

## 23. Sufficiency Gate Reassessment

Evaluated in [`data/ops02/audits/ops02_sufficiency_gate_v1.json`](file:///D:/Projects/ocean-sentinel/data/ops02/audits/ops02_sufficiency_gate_v1.json):

```
================================================================================
CRITERION                                  TARGET       ACHIEVED     VERDICT
--------------------------------------------------------------------------------
Total Independent Parent Clusters          >= 60        64           PASS
DEV Partition Parent Clusters              >= 10        12           PASS
HOLDOUT Partition Parent Clusters          >= 10        12           PASS
HM (Artificial Objects) Parent Presence    >= 8         14           PASS
OF (Ocean Front) Parent Presence           >= 6         7            PASS
Inter-Partition Leakage                    0%           0%           PASS
Technical & Provenance QC Pass Rate        100%         100.0%       PASS
================================================================================
OVERALL SUFFICIENCY VERDICT: READY_FOR_DATASET_FREEZE_REVIEW
MODEL TRAINING AUTHORIZATION: NOT_AUTHORIZED_IN_C14
================================================================================
```

---

## 24. Incident Register

Audited in [`data/metadata/exp07_p0_c14_incident_register_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c14_incident_register_v1.json):
- **Total new unhandled incidents during C14:** 0.
- `INC-P0-C13-001` (along-track datatake pseudo-replication) was proactively resolved by enforcing `GOV-RULE-077` during cluster construction.

---

## 25. Governance Updates

Two permanent governance rules were codified in [`data/metadata/ocean_sentinel_governance_rules_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/ocean_sentinel_governance_rules_v1.json):
1. **`GOV-RULE-079` (Four-Layer Distinct Quality Control Standard):** Every physical dataset assembly must evaluate and report Technical Integrity, Provenance Integrity, Semantic/Label Integrity, and Scientific Independence as four distinct audit layers. Conflating these layers into a single aggregate figure without individual reporting is prohibited.
2. **`GOV-RULE-080` (Dataset Assembly Candidate Freeze vs Model Training Gating):** Assembling, verifying, and freezing a physical dataset candidate (e.g. `OPS02_v1_CANDIDATE`) constitutes a data engineering milestone only. Model training remains strictly prohibited until a separate formal scientific training-readiness authorization gate is passed.

---

## 26. Test Results

Executed complete regression suite:
```
================================================================================
Suite 1: Dedicated C14 OPS-02 Dataset Assembly Guardrails
Command: .venv\Scripts\python.exe -m pytest tests/test_exp07_p0_c14_ops02_dataset_assembly_guardrails.py
Result:  11 passed in 0.13s

Suite 2: EXP-07 Regression Suite (C2 through C14)
Command: .venv\Scripts\python.exe -m pytest (Get-ChildItem tests/test_exp07_p0_c*.py)
Result:  235 passed, 5 warnings in 24.92s

Suite 3: Artifact Policy & Part-III External Firewall
Command: .venv\Scripts\python.exe -m pytest tests/test_artifact_policy.py tests/test_part_iii_firewall.py
Result:  12 passed in 3.19s

TOTAL REGRESSION TESTS: 247 / 247 PASSED (100% Pass Rate)
================================================================================
```

---

## 27. Git Working Tree State

- **Branch:** `master`
- **Active processes:** 0 running
- **Staged files:** 0
- **Tracked modified files:** 2 preserved (`.gitignore`, `src/ocean_sentinel/ingestion/dataset.py`)
- **Untracked files:** Preserved intact. Zero destructive Git commands (`git reset`, `git clean`, `git checkout`) were executed.

---

## 28. Dataset Version and Status

- **Dataset Identifier:** `OPS-02`
- **Candidate Release Version:** `OPS02_v1_CANDIDATE`
- **Dataset Composition:** 64 independent parent clusters, 212 physical sample pairs.
- **Physical Directory:** `data/ops02/`

---

## 29. Scientific Training-Readiness Assessment

Although `OPS02_v1_CANDIDATE` has satisfied all technical, geographic, temporal, and independence sufficiency criteria:
- **MODEL TRAINING IN C14: STRICTLY PROHIBITED.**
- In accordance with `GOV-RULE-080`, dataset assembly completion does not authorize training.
- Training authorization is deferred to a future dedicated phase (`EXP-07-P0-C15`) following formal dataset freeze review.

---

## 30. Final Decision & Next Phase Directives

```
================================================================================
FINAL FEASIBILITY DECISION: A = DATASET ASSEMBLY PASS
PHYSICAL ACQUISITION: COMPLETE (64 Datatake Clusters / 212 Physical Samples)
DATASET FREEZE STATUS: READY FOR FORMAL FREEZE REVIEW (OPS02_v1_CANDIDATE)
MODEL TRAINING AUTHORIZATION: NO (Strictly Prohibited in C14)
SEED 2024 STATUS: DEFERRED / PROHIBITED
NEXT AUTHORIZED TASK: FORMAL DATASET FREEZE REVIEW & PRE-TRAINING PROTOCOL (C15)
================================================================================
```
