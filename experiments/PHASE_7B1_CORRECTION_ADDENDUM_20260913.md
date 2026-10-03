# OCEAN SENTINEL — PHASE 7B.1 CORRECTION ADDENDUM
**Document Identifier:** `PHASE_7B1_CORRECTION_ADDENDUM_20260913`  
**Governing Role:** Senior CAO Scientific Benchmark / Data Governance Auditor  
**Date:** September 13, 2026  
**Status:** **AUTHORITATIVE CORRECTION ADDENDUM TO PHASE 7B.1 REPORT**  
**Associated Historical Report:** [PHASE_7B1_EXTERNAL_LOOKALIKE_PROTOCOL_20260913.md](file:///d:/Projects/ocean-sentinel/experiments/PHASE_7B1_EXTERNAL_LOOKALIKE_PROTOCOL_20260913.md)

---

### 1. GOVERNANCE PURPOSE & AUDIT SCOPE

In strict compliance with Ocean Sentinel audit policies, historical reports remain preserved bitwise. This correction addendum formally amends scientific terminology, independence qualifications, and statistical interpretations present in `experiments/PHASE_7B1_EXTERNAL_LOOKALIKE_PROTOCOL_20260913.md`.

During Phase 7B.2 forensic source-granule reconstruction, deeper lineage analysis revealed that several characterizations in Phase 7B.1 overstated the empirical independence, statistical isolation, and source-level identity of the Li et al. (2024/2025) dataset.

---

### 2. TERMINOLOGY & INDEPENDENCE AUDIT CORRECTIONS

| Area | Phase 7B.1 Phrasing | Phase 7B.2 Corrected Scientific Formulation | Rationale & Governance Rule |
| :--- | :--- | :--- | :--- |
| **Dataset Characterization** | "outstanding candidate resource" / "outstanding resource" | **"high-value candidate resource"** | Avoid hyperbolic characterizations ("outstanding"). The dataset possesses significant known physical limitations ($100\text{ m}$ decimation, single-pol VV, non-calibrated `uint16`, missing CRS). |
| **Dataset Independence** | "genuinely independent of Ocean Sentinel" | **"independent in research authorship, but represents a derived synthesis with shared sensor lineage"** | While the authors and catalog entries are separate from Ocean Sentinel, Li et al. explicitly incorporates imagery from TenGeoP-SARwv (Wang et al. 2019) and Tao et al. (2022). It is a derived secondary compilation, not an independent de novo acquisition program. |
| **Wave Mode Independence** | "2,383 independent Sentinel-1 Wave Mode (WV) vignettes" | **"2,383 Wave Mode vignettes originating from 1,678 unique orbit passes"** | The 2,383 WV vignettes are not 2,383 statistically independent observations. Sibling vignettes from the same satellite pass share orbit trajectories, sensor geometry, and regional weather states. There are at most 1,678 independent observation passes (averaging 1.42 vignettes per pass, range 1–13). |
| **Parent-Product Identity** | "484 unique parent products" | **"484 unique source scene stems (Level-1 GRD measurement slices)"** | A single Sentinel-1 IW measurement stem (e.g. `...-004712-005d33-001`) represents an individual frame along an orbit datatake, not necessarily an isolated global product. In addition, 2,628 slices come from these 484 scene stems, averaging 5.43 slices per scene. |
| **External Generalization** | "enables true category-by-category false-alarm evaluation of Ocean Sentinel" | **"provides a high-value candidate resource for category-by-category phenomenon recognition and stress analysis under explicit sensor constraints"** | Cannot claim general false-alarm evaluation for Ocean Sentinel, because Ocean Sentinel requires $10\text{ m}$ dual-pol (VH/VV) decibel backscatter, which is physically absent from the distributed Li et al. files. |
| **Statistical Independence** | "independent sampling unit is the Parent Product" | **"parent-product clustering must be strictly accounted for via cluster-robust variance estimation"** | Acknowledges that even parent products from the same regional basin or seasonal synoptic event exhibit covariance that must be modelled statistically. |

---

### 3. GOVERNANCE INVARIANT RE-AFFIRMATION

1. **Exp-07 Model Training:** **STRICTLY FORBIDDEN**.
2. **Exp-06 Checkpoint & Threshold:** **FROZEN** (Checkpoint `B5FFCCA3...`, $\tau = 0.22$).
3. **Part-I & Part-III Integrity:** Part-I Internal Development Split Manifest (`data/metadata/internal_development_split_manifest.json`) is **BITWISE FROZEN** (`17F1FF35...`). Part-III is **PERMANENTLY QUARANTINED** under Rule 38.
4. **DARTIS Status:** Remains **SEMANTICALLY UNRESOLVED**.
