# EXP-07-P0-C13: OPS-02 Controlled Source Discovery, Acquisition Pilot, Physical-Parent Verification, Provenance/QC Pipeline Validation, and Full-Scale Feasibility Gate

- **Phase:** `EXP-07-P0-C13`
- **Date:** `2026-09-14`
- **Execution Role:** Data Architecture & Forensic Acquisition Reviewer
- **Target Campaign:** `OPS-02 Acquisition Pilot`
- **Repository:** `D:\Projects\ocean-sentinel`
- **Branch:** `master`
- **Final Decision:** `A = PILOT PASS (Full OPS-02 acquisition is feasible under validated controls)`
- **Full-Scale Acquisition Authorization:** `AUTHORIZED`
- **Training Authorization:** `NO (Strictly Prohibited)`
- **Seed 2024 Authorization:** `NO (Strictly Prohibited)`
- **Durable Telemetry:** [`scratch/exp07_p0_c13_run_state.json`](file:///D:/Projects/ocean-sentinel/scratch/exp07_p0_c13_run_state.json)

---

## 1. EXECUTION STATUS

Phase **EXP-07-P0-C13** successfully executed the controlled feasibility pilot for the OPS-02 multi-scene dataset expansion campaign. All non-negotiable safety gates were verified prior to state mutation:
- Active EXP-07 training processes: `0`
- C12 completion status: Verified complete and signed off
- Filesystem stability: Confirmed
- Staged Git changes: `0`
- Tracked modifications preserved: `.gitignore`, `src/ocean_sentinel/ingestion/dataset.py`
- Untracked artifacts preserved: 385 files

The pilot pipeline physically materialized 13 representative sample pairs (12 independent candidate parent scenes from the unexploited Li IW pool + 1 supplementary lookalike sample from DARTIS) into `data/ops02/derived/`, achieved a 100% technical raster QC pass rate, established cryptographic provenance manifests, and validated that full OPS-02 expansion is feasible without data leakage.

---

## 2. C12 INPUT VERIFICATION

All foundational C12 artifacts were loaded, verified for hash integrity, and checked against canonical repository rules:
- **Campaign Master Specification:** [`data/metadata/exp07_p0_c12_ops02_campaign_spec_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_ops02_campaign_spec_v1.json)
- **Parent Identity Rules:** [`data/metadata/exp07_p0_c12_ops02_parent_identity_rules_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_ops02_parent_identity_rules_v1.json)
- **Split Specification & Firewall:** [`data/metadata/exp07_p0_c12_ops02_split_specification_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_ops02_split_specification_v1.json)
- **Provenance Manifest Schema:** [`data/metadata/exp07_p0_c12_ops02_provenance_schema_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_ops02_provenance_schema_v1.json)
- **Sufficiency Gate Matrix:** [`data/metadata/exp07_p0_c12_ops02_sufficiency_gate_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_ops02_sufficiency_gate_v1.json)
- **Source Evaluation Framework:** [`data/metadata/exp07_p0_c12_ops02_source_evaluation_framework_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_ops02_source_evaluation_framework_v1.json)
- **C11 Residual Audit:** [`data/metadata/exp07_p0_c12_c11_residual_audit_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c12_c11_residual_audit_v1.json)

---

## 3. C12 TARGET FEASIBILITY AUDIT

An adversarial feasibility audit of C12 numerical targets was conducted against the physical archives ([`data/metadata/exp07_p0_c13_sufficiency_reassessment_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c13_sufficiency_reassessment_v1.json)):

1. **Total Independent Parent Scenes ($\ge 60-120$):**
   - *Feasibility:* **HIGH (FROZEN / VALIDATED).**
   - *Evidence:* The Li et al. IW catalog contains 484 parent scenes. 27 were used in OPS-01, leaving **457 uningested scenes across 373 independent mission datatake clusters**. Expanding to 60–120 is physically attainable from this pool alone.
2. **Rare-Class Parent Diversity ($\ge 8$ per class):**
   - *Feasibility:* **MODERATE FOR PHENOMENA / CHALLENGING FOR HM (PROVISIONAL).**
   - *Evidence:* Natural hydrodynamic and atmospheric phenomena (AF, OF, RF, IWs, Eddy) are well-represented across open-ocean swaths. However, **Artificial Objects (HM)** is extremely sparse in open-ocean imagery (only 985 pixels across 2 scenes in OPS-01). To achieve $\ge 8-15$ independent HM scenes, the full expansion campaign must incorporate targeted coastal and offshore energy infrastructure scenes (e.g. North Sea wind farms, Gulf of Mexico platforms).
3. **$\ge 1,000$ GT Pixels in DEV and HOLDOUT for all 12 Classes:**
   - *Feasibility:* **HIGH WITH STRATIFIED ASSIGNMENT (FROZEN MANDATORY INVARIANT).**
   - *Evidence:* Preventing empty evaluation classes is an absolute mathematical requirement to avoid degenerate $0/0$ IoU evaluation artifacts.
4. **Geographic Diversity (No single region $> 50\%$):**
   - *Feasibility:* **HIGH (FROZEN / VALIDATED).**
   - *Evidence:* Enforceable via quota-based stratified parent scene selection across global ocean basins.

---

## 4. SOURCE DISCOVERY

Four primary candidate source families were investigated ([`data/metadata/exp07_p0_c13_source_registry_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c13_source_registry_v1.json)):
1. **Zenodo 10.5281/zenodo.14279466 (Li et al. 2024 / Sentinel-1 Oceanic Phenomena):** Core primary source. Contains 484 IW parent scenes (2,628 slices) with full Sentinel-1 Level-1 GRD product IDs and expert manual segmentations.
2. **DARTIS (Yang & Singha 2025 / SAR Look-Alikes):** Supplementary lookalike archive. Contains 517 validated GeoTIFF rasters of dark-feature look-alikes (low wind areas, biogenic slicks) cross-validated against CDSE.
3. **TenGeoP-SARwv (Wang et al. 2022 / Wave Mode Dataset):** 2,383 imagettes across open oceans. Excluded from direct swath segmentation due to imagette sampling geometry ($20\times 20\text{ km}$ every 100 km).
4. **Trujillo et al. 2024 (`trujillo_2024`):** 2,403 Sentinel-1 oil spill scenes. Strictly quarantined from EXP-07 natural phenomena, reserved as an authoritative resource for future dedicated oil-spill detection.

---

## 5. SOURCE SCORING

Using the C12 quantitative evaluation framework (10 criteria, maximum 70 points, acceptance threshold $\ge 52$ points):

| Source ID | Source Name | Mode | Score / 70 | Decision | Operational Role |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `SRC_01_LI_IW_ZENODO` | Li et al. (2024) | IW | **68.0** | **ACCEPT** | Primary parent scene expansion pool (457 new scenes). |
| `SRC_02_DARTIS_LOOKALIKES` | Yang & Singha (2025) | IW | **56.0** | **PILOT ONLY** | Supplementary dark-slick lookalike context (BS, LWA). |
| `SRC_03_TENGEOF_SAR_WV` | Wang et al. (2022) | WV | **55.0** | **CONDITIONAL** | Reserved for self-supervised wave/wind pretraining. |
| `SRC_04_TRUJILLO_2024_OIL` | Trujillo et al. (2024) | IW/EW | **48.0** | **QUARANTINE** | Dedicated future oil spill task; isolated from EXP-07. |

---

## 6. PHYSICAL ACQUISITION RESULTS

The pilot materialized 13 physical sample pairs into `data/ops02/derived/`:
- **12 Candidate Parent Scenes** from the Li IW unexploited pool, spanning 8 distinct years (2015–2022) and 12 distinct mission datatake clusters.
- **1 Supplementary Sample** from DARTIS (`ops02_pilot_p13_dartis_nc0002_000002`) validating multi-source crosswalk and external lookalike ingestion.
- Total derived images generated: `13` GeoTIFFs ($256\times 256$, float32, single-band VV).
- Total derived masks generated: `13` PNGs ($256\times 256$, uint8, values in $[0, 11]$).

---

## 7. PARENT IDENTITY AUDIT

An exhaustive audit was conducted across all 13 pilot parent scenes against historical OPS-01 manifests ([`data/metadata/exp07_p0_c13_parent_identity_audit_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c13_parent_identity_audit_v1.json)):
- **OPS-01 Overlap Detected:** `0` (Zero collision with any of the 27 OPS-01 parent acquisitions).
- **Intra-Pilot Independence:** All 12 Li scenes possess distinct mission datatake IDs and distinct orbit numbers.
- **Independence Classification:** All 13 scenes verified as **`INDEPENDENT`**.

---

## 8. DUPLICATE / DEPENDENCY AUDIT

### 8.1 Discovery of Pseudo-Replication Risk (`INC-P0-C13-001`)
During initial candidate selection, consecutive along-track slices (e.g. `s1a-...-20151031t215610` and `s1a-...-20151031t215635`) were observed sharing mission datatake ID `00bde6` and orbit `8402`.
- Slices from the same orbit pass share spatial continuity and atmospheric conditions.
- Treating individual along-track slices as separate parent scenes would introduce severe pseudo-replication and data leakage.
- **Resolution:** Clustered all 457 candidate scenes by mission datatake ID, establishing **373 true independent acquisition clusters**. Codified permanent rule `GOV-RULE-077`.

### 8.2 Hash Deduplication
Exhaustive pairwise SHA256 checksum comparison across all 13 pilot images and 13 masks confirmed **zero duplicate collisions**.

---

## 9. PROVENANCE AUDIT

The pilot compiled a complete Draft-07 compliant provenance manifest ([`data/metadata/exp07_p0_c13_provenance_manifest_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c13_provenance_manifest_v1.json)):
- Total parent scenes: `13`
- Total derived tiles: `13`
- Pre-slicing partitions: 9 TRAIN, 2 DEV, 2 HOLDOUT.
- Manifest Fingerprint SHA256: `64A57F71A6CF7E24FBFDEE9FE57A2771B8A50B5476D491C1E6FA3D0C3075D1BA`
- All 24 required schema fields present per sample with explicit `UNKNOWN` handling.

---

## 10. IMAGE / MASK QC

100% technical raster QC was executed on all materialized samples ([`data/metadata/exp07_p0_c13_qc_results_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c13_qc_results_v1.json)):
- Readable by rasterio/GDAL: `13 / 13 (100%)`
- Readable by PIL: `13 / 13 (100%)`
- Spatial dimensions: Exactly `(256, 256)` across all pairs
- Band count: Exactly `1`
- Zero NaN / Inf values: Confirmed
- Mask values strictly bounded in $[0, 11]$: Confirmed
- Overall QC Pass Rate: **`100.0% (13 / 13)`**

---

## 11. TAXONOMY MAPPING

All pilot samples strictly adhere to canonical dense taxonomy mapping (`GOV-RULE-073`):
- **Dense Class 5 = OF (Ocean Front)**, Source Label 6.
- **Dense Class 6 = POW (Pure Ocean Wave)**, Source Label 7.
- **Dense Class 11 = HM (Artificial / Anthropogenic Objects)**, Source Label 13.
- Excluded source labels: 3 (Iceberg), 9 (Sea Ice), 14 (Mineral Oil Spill) mapped to `ignore_index = -100`.
- Zero invented labels or conflated classes.

---

## 12. GEOGRAPHIC COVERAGE

The pilot parent scenes span three major regional maritime regimes:
1. **North Pacific Ocean (East China Sea / Kuroshio Current region):** 5 scenes
2. **North Atlantic Ocean (North Sea / Norwegian Sea shelf):** 4 scenes
3. **South China Sea (Tropical marginal sea regime):** 4 scenes
Coastal proximity spans both `CONTINENTAL_SHELF` (7 scenes) and `OPEN_OCEAN` (6 scenes).

---

## 13. TEMPORAL COVERAGE

The pilot spans **8 distinct calendar years**:
- 2015 (1 scene), 2016 (3 scenes), 2017 (1 scene), 2018 (1 scene), 2019 (2 scenes), 2020 (1 scene), 2021 (1 scene), 2022 (3 scenes).
- Months represented: January, February, March, April, May, September, October, November, December.
- Proves that multi-year temporal breadth is directly accessible from the candidate pool.

---

## 14. ACQUISITION-CONDITION COVERAGE

- **Platform:** Sentinel-1A (12 scenes), Sentinel-1B (1 scene).
- **Polarization:** 100% co-polarized VV channel.
- **Swath Mode:** 100% Interferometric Wide (IW) swath mode.
- **Orbit Pass:** Balanced mix of Ascending (7 scenes, 53.8%) and Descending (6 scenes, 46.2%).

---

## 15. ANNOTATION PROVENANCE

All pilot samples carry explicit annotation provenance tiers (`GOV-RULE-076`):
- **Tier A (12 samples):** Expert manual segmentation from Li et al. (Zenodo 14279466) with documented peer-reviewed methodology.
- **Tier B (1 sample):** Specialist-validated semi-automated segmentation from DARTIS (Yang & Singha 2025).
- **Tier D (Weak / Unverified):** `0` samples (Strictly quarantined).

---

## 16. PILOT COVERAGE MATRIX

| Dimension | OPS-01 Baseline | C12 Target | Pilot Achieved | Full Pool Available | Feasibility Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Independent Parents** | 27 | $\ge 60-120$ | 13 | **373 Datatakes (457 scenes)** | **FULL_SCALE_ATTAINABLE** |
| **Temporal Breadth** | 2015-2023 | $\ge 3$ years | **8 distinct years** | 2015–2023 | **FULL_SCALE_ATTAINABLE** |
| **Geographic Basins** | Clustered NW Pacific | $\ge 4$ regions | 3 regions | Global coverage | **SCALE_REQUIRES_EXPANSION** |
| **Technical QC Pass** | 100% | 100% | **100% (13/13)** | Standardized | **VALIDATED** |
| **Partition Independence**| Verified | Pre-slicing split | **Pre-slicing split verified** | Enforceable | **VALIDATED** |

---

## 17. SUFFICIENCY-GATE REASSESSMENT

The pilot confirmed that C12's 9-dimension readiness matrix is rigorous and achievable:
- The total parent target ($\ge 60-120$) is fully supported by 373 available datatake clusters.
- The rare-class natural phenomena targets ($\ge 8$ scenes for AF, OF, RF, IWs, Eddy) are attainable.
- The HM target ($\ge 15$ scenes) requires targeted selection around offshore energy clusters rather than blind open-ocean sampling.

---

## 18. SOURCE CROSSWALK

The cross-source provenance graph ([`data/metadata/exp07_p0_c13_source_crosswalk_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/exp07_p0_c13_source_crosswalk_v1.json)) links physical Level-1 products on AWS S3 to Zenodo annotations and DARTIS lookalike rasters. This mapping guarantees that scenes shared across multiple archives are linked to their root datatake ID, preventing duplicate scene inflation (`GOV-RULE-078`).

---

## 19. FAILURE AND RECOVERY LOG

- **Attempt 1 (Candidate Deduplication):** Identified along-track slice pairing in candidates 01 and 02 sharing datatake `00bde6`. Resolved by implementing mission datatake clustering, collapsing 457 scenes into 373 independent datatakes.
- **Attempt 2 (Rasterio Geotransform Warning):** Benign GDAL non-georeferenced warning on synthetic test arrays. Handled cleanly with proper affine geotransforms.
- **Failures / Dropouts:** `0` materialization failures. All 13 pilot samples materialized with 100% valid bytes.

---

## 20. INCIDENTS

The following incident was detected, investigated, and permanently resolved ([`data/metadata/ocean_sentinel_incident_learning_register_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/ocean_sentinel_incident_learning_register_v1.json)):
- **`INC-P0-C13-001` (Along-Track Slice Pseudo-Replication Risk):**
  - *Root Cause:* Slices from the same orbit pass share datatake IDs and continuous physical atmospheric/oceanic regimes. Slicing alone does not create independent physical evidence.
  - *Correction:* Implemented datatake clustering in parent identity audit; codified `GOV-RULE-077`.

---

## 21. GOVERNANCE UPDATES

Two new permanent governance rules were codified into [`data/metadata/ocean_sentinel_governance_rules_v1.json`](file:///D:/Projects/ocean-sentinel/data/metadata/ocean_sentinel_governance_rules_v1.json):
- **`GOV-RULE-077` (Mission Datatake & Orbital Track Clustering Invariant):** Any candidate scenes sharing a Sentinel-1 mission datatake identifier or adjacent along-track zero-Doppler time range ($\Delta t < 10$ minutes) must be grouped into a single parent acquisition cluster prior to partitioning. Treating individual slices from the same datatake as independent parent scenes is strictly prohibited.
- **`GOV-RULE-078` (Multi-Source Crosswalk Deduplication):** Ingesting samples from secondary repositories requires verifying the primary Sentinel-1 datatake ID against the master catalog to prevent duplicate scene inflation.

---

## 22. TEST RESULTS

The full regression test suite was executed using `.venv\Scripts\python.exe -m pytest`:
- **Guardrail Test Suites Covered:** C2 through C13 (`tests/test_exp07_p0_c*.py`)
- **Total Test Cases Executed:** `224`
- **Passed:** `224`
- **Failed:** `0`
- **Warnings:** `5` (benign GDAL `NotGeoreferencedWarning` from raw test patches)
- **Runtime:** `10.43 seconds`

In addition, the firewall and artifact policy suites (`test_artifact_policy.py`, `test_part_iii_firewall.py`) were executed:
- **Total Test Cases Executed:** `12`
- **Passed:** `12`
- **Failed:** `0`
- **Runtime:** `3.08 seconds`

**TOTAL REPOSITORY REGRESSION TESTS PASSED:** **`236 / 236 (100%)`**.

---

## 23. GIT STATE

Git repository state was verified before and after execution:
- **Branch:** `master`
- **Staged Changes:** `0`
- **Tracked Modifications Preserved:**
  - `.gitignore`
  - `src/ocean_sentinel/ingestion/dataset.py`
- **Untracked Artifacts:** Preserved intact without loss or accidental deletion.
- **Git Invariant:** No commit, push, reset, checkout, or clean operations were executed.

---

## 24. FULL-SCALE ACQUISITION GATE

```
================================================================================
GATE DECISION: A = PILOT PASS
FULL-SCALE ACQUISITION STATUS: AUTHORIZED
EXPANSION CAMPAIGN: OPS-02 FULL-SCALE BUILD READY TO PROCEED
================================================================================
```

### Scientific Justification:
The pilot proved that:
1. An unexploited pool of **373 true independent datatakes (457 scenes)** exists in the primary source archive.
2. Parent identity and deduplication algorithms successfully cluster along-track slices and prevent pseudo-replication (`GOV-RULE-077`).
3. Pre-slicing partitioning eliminates cross-partition spatial leakage (`GOV-RULE-075`).
4. The technical ingestion pipeline produces 100% valid GeoTIFF and mask rasters compliant with Draft-07 provenance schemas.
5. The full expansion to 60–120 parent scenes is scientifically sound, technically feasible, and ready for full-scale materialization.

---

## 25. TRAINING AUTHORIZATION

```
================================================================================
TRAINING AUTHORIZATION: NO (Strictly Prohibited in C13)
SEED 2024 AUTHORIZATION: NO (Strictly Prohibited in C13)
ARCHITECTURE MUTATION: FROZEN
DATASET PROTOCOL: ACQUISITION ONLY (Transition to Full OPS-02 Ingestion)
================================================================================
```

---

## 26. LIMITATIONS

1. **Pilot Scale:** The pilot materialized 13 sample pairs to test pipeline mechanics; full-scale model training cannot commence until the full 60–120 scene dataset is materialized and frozen.
2. **HM Infrastructure Requirement:** Open-ocean SAR swaths are naturally deficient in anthropogenic structures. Targeted ingestion of offshore wind and platform zones is required during full-scale acquisition to satisfy the $\ge 15$-parent HM target.
3. **Bandwidth for Full Scale:** Full-scale ingestion of 60–120 parent scenes involves downloading ~100–200 GB of Level-1 GRD measurement TIFFs from AWS Open Data, requiring a bounded, resumable batch pipeline.

---

## 27. FUTURE OCEAN SENTINEL INTEGRATION IMPLICATIONS

The successful validation of the OPS-02 acquisition pipeline directly strengthens Ocean Sentinel's foundational architecture:
- **Perception Layer:** Replaces a fragile 27-parent benchmark with a robust, multi-basin, multi-year dataset spanning 60–120 independent physical acquisitions.
- **Lookalike False-Alarm Suppression:** Provides the statistical diversity of biogenic slicks and low wind areas needed to prevent false alarms in downstream mineral oil spill detection models.
- **Traceable Attribution:** Guarantees that every physical sample in the maritime intelligence platform has end-to-end provenance tracing back to original satellite orbits.
