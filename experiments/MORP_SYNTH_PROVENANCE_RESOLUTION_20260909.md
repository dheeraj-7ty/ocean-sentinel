# Phase 3.2B Authoritative MORP-Synth Provenance Resolution Report
**Date:** 2026-09-09T22:46:00+05:30  
**Authority:** Chief AI Officer (CAO) Directive — Phase 3.2B  
**Mission:** Determine whether an authoritative MORP-Synth dataset release currently exists and establish its exact canonical provenance without transferring dataset bytes.  
**Terminal State:** **`BLOCKED_DATASET_PROVENANCE`**  
**Data Access Status:** **`RED: MORP_SYNTH_DATA_ACCESS_UNRESOLVED`**  
**Committed Repository HEAD:** `97567f712684a011a6849c6bc0af7b6c561bef1e`  

---

### 1. EXECUTIVE DECISION
Exhaustive cross-source provenance investigation confirms that **no public, canonical dataset release of the MORP-Synth Peruvian coastal benchmark currently exists**.

The primary literature (arXiv:2512.02290v1, *"Enhancing Cross-Domain SAR Oil Spill Segmentation via Morphological Region Perturbation and Synthetic Label-to-SAR Generation"*, Andre Juarez et al., Dec 4, 2025) explicitly declares under *Data and Code Availability* that the Peruvian ground-truth masks and metadata will be deposited to Zenodo **upon manuscript acceptance**. 

Inspection of the primary GitHub code repository (`andrexandrex/MorpSynth`), the author's Hugging Face profile (`andrexandrex`), and public Zenodo registry indices establishes that:
1. Code modeling scripts are publicly available, but raw GeoTIFF rasters, patches, and segmentation masks have **not** been uploaded or released.
2. No Zenodo DOI or record has been minted for MORP-Synth by the authors or their institution (Universidad Nacional Agraria La Molina).
3. The previously referenced candidate DOI `10.5281/zenodo.19258036` belongs exclusively to **QPOSD** (NASA/JPL UAVSAR L-band quad-polarization airborne SAR over the U.S. Gulf of Mexico by Jamal & Li, Jan 15, 2026). Its association with MORP-Synth in earlier working notes was an artifact of search-index conflation between newly published 2026 SAR oil spill entries.

In accordance with CAO directive principles (*Provenance mismatch = HARD STOP; Missing authoritative evidence = BLOCK; Zero guessing*), the qualification state is finalized at **`BLOCKED_DATASET_PROVENANCE`**, with data access classified as **`MORP_SYNTH_DATA_ACCESS = UNRESOLVED`**. Exactly **0 dataset bytes** were downloaded or transferred.

---

### 2. TARGET DATASET IDENTITY
Derived strictly from primary literature (arXiv:2512.02290v1) and primary repository artifacts:

| Attribute | Expected Target Value | Source Citation | Evidentiary Status |
| :--- | :--- | :--- | :--- |
| **Dataset Name** | MORP-Synth Peruvian Coastal Dataset (and synthetic augmentations) | arXiv:2512.02290v1 Abstract, Sec 1 | **OBSERVED** |
| **Primary Authors** | Andre Juarez (André Juárez Castro), Luis Salsavilca, Frida Coaquira, Celso Gonzales | arXiv:2512.02290v1 Author Header | **OBSERVED** |
| **Affiliations** | Círculo de Investigación de Máquinas de Aprendizaje (CIMA) & Dpto. de Estadística e Informática, UNALM, Lima, Peru | arXiv:2512.02290v1 Affiliations | **OBSERVED** |
| **Study Purpose** | Cross-domain adaptation from Mediterranean (CleanSeaNet) to Peruvian waters (Humboldt Current upwelling) | arXiv:2512.02290v1 Sec 1 | **OBSERVED** |
| **Platform** | Copernicus Sentinel-1 | arXiv:2512.02290v1 Sec 2.1 | **OBSERVED** |
| **Sensor Band / Product** | C-band (5.405 GHz), IW swath, Ground Range Detected (GRD) | arXiv:2512.02290v1 Sec 2.1 | **OBSERVED** |
| **Polarization** | VV polarization only (IW swath retained, calibrated to $\sigma^0$, 10 m/pixel) | arXiv:2512.02290v1 Sec 2.2 | **OBSERVED** |
| **Geographic Domain** | Peruvian Coast (Southeast Pacific / Humboldt Current; Talara, Callao, Ilo) | arXiv:2512.02290v1 Sec 2.1, Fig 1 | **OBSERVED** |
| **Temporal Span** | 2014–2024 (40 selected scenes across 67 documented spill events) | arXiv:2512.02290v1 Sec 2.1 | **OBSERVED** |
| **Spatial Structure** | 2,112 labeled $512 \times 512$ patches extracted from 40 Sentinel-1 GRD scenes | arXiv:2512.02290v1 Abstract, Sec 2.1 | **OBSERVED** |
| **Mask Semantics** | 5 semantic classes harmonized with CleanSeaNet: Sea (0), Oil (1), Look-alike (2), Ship (3), Land (4) | arXiv:2512.02290v1 Sec 2.1 | **OBSERVED** |
| **Synthetic Components**| Stage A (MORP curvature-guided perturbation) + Stage B (INADE cGAN mask-to-SAR) | arXiv:2512.02290v1 Sec 2.4 | **OBSERVED** |
| **Code Repository** | `https://github.com/andrexandrex/MorpSynth.git` | arXiv:2512.02290v1 Abstract footer | **OBSERVED** |
| **Data Availability** | "Peruvian ground-truth masks and metadata will be uploaded to Zenodo upon manuscript acceptance" | arXiv:2512.02290v1 Data Availability | **OBSERVED** |
| **Canonical DOI** | Unassigned / Not yet minted | Zenodo & CrossRef queries | **UNKNOWN** |

---

### 3. AUTHORITATIVE SOURCES

#### Tier 1 — Primary / Authoritative:
1. **Preprint Publication:** Juarez et al., *"Enhancing Cross-Domain SAR Oil Spill Segmentation via Morphological Region Perturbation and Synthetic Label-to-SAR Generation"*, arXiv:2512.02290v1 (cs.CV, cs.AI), Dec 4, 2025.
2. **Official Code Repository:** `https://github.com/andrexandrex/MorpSynth` (maintained by lead author André Juárez Castro, commit author `20200396@lamolina.edu.pe`).

#### Tier 2 — Official Infrastructure:
1. **Zenodo REST API:** `https://zenodo.org/api/records` (searched for authors, institutions, and project titles).
2. **Hugging Face Hub:** `https://huggingface.co/andrexandrex` (author profile inspection).
3. **Institutional Domain:** Universidad Nacional Agraria La Molina (`lamolina.edu.pe`).

#### Tier 3 — Discovery Only:
1. **Crossref / OpenAlex / Google Scholar:** Citation tracking and author publication indexing.
2. **ResearchGate Profile:** Andre Juarez and co-authors publication listings.

---

### 4. CANDIDATE SOURCES

| Candidate ID | Source Type | URL / Identifier | Claimed / Surfaced Entity | Stated Owners |
| :--- | :--- | :--- | :--- | :--- |
| **CAND-01** | Zenodo Record | `10.5281/zenodo.19258036` | "QPOSD: Quad-Polarization Dataset..." | Sohail Jamal, Yu Li (Beijing Univ. of Tech.) |
| **CAND-02** | GitHub Repository | `github.com/andrexandrex/MorpSynth` | Official MORP-Synth code repository | André Juárez Castro (`andrexandrex`) |
| **CAND-03** | Hugging Face Profile| `huggingface.co/andrexandrex` | User profile of lead author | André Juárez Castro |
| **CAND-04** | Zenodo Author Query| `zenodo.org/api/records?q=Juarez` | Query for deposits by author group | UNALM / CIMA |

---

### 5. CANDIDATE RECONCILIATION

#### Reconciliation Matrix against Intended Target Identity:

| Field | Target Requirement | CAND-01 (DOI 19258036) | CAND-02 (GitHub Repo) | CAND-03 (HuggingFace) |
| :--- | :--- | :--- | :--- | :--- |
| **Dataset Identity** | MORP-Synth Peruvian S1 | QPOSD (**MISMATCH**) | MorpSynth Code (**PARTIAL**) | Empty Profile (**MISMATCH**) |
| **Authorship** | Juarez et al. (UNALM) | Jamal & Li (Beijing) (**MISMATCH**)| Juarez (`andrexandrex`) (**MATCH**)| Juarez (`andrexandrex`) (**MATCH**)|
| **Sensor / Platform** | Spaceborne Sentinel-1 | Airborne NASA UAVSAR (**MISMATCH**)| N/A (Code only) (**UNKNOWN**)| None (**UNKNOWN**) |
| **Radar Band** | C-band (5.405 GHz) | L-band (1.26 GHz) (**MISMATCH**) | N/A (**UNKNOWN**) | None (**UNKNOWN**) |
| **Polarization** | VV (or VV/VH dual-pol) | 9-channel Quad-Pol ($T$) (**MISMATCH**)| N/A (**UNKNOWN**) | None (**UNKNOWN**) |
| **Geography** | Peruvian Coast | U.S. Gulf of Mexico (**MISMATCH**) | N/A (**UNKNOWN**) | None (**UNKNOWN**) |
| **Rasters Included** | 2,112 patches ($512\times 512$) | 41 UAVSAR scenes (**MISMATCH**) | 0 rasters (**MISMATCH**) | 0 rasters (**MISMATCH**) |
| **Masks Included** | 5-class CleanSeaNet | 4-class RGB masks (**MISMATCH**) | 0 masks (**MISMATCH**) | 0 masks (**MISMATCH**) |
| **Disposition** | — | **REJECTED** | **REJECTED AS DATA SOURCE** | **REJECTED** |

**Rationale for Dispositions:**
- **CAND-01:** Absolute, irreconcilable physical and geographical mismatch. Sensor, band, polarimetry, channel depth, geography, and authors are entirely unrelated.
- **CAND-02:** While authoritative for pipeline code, the GitHub repository contains exactly 0 raw rasters, 0 GeoTIFFs, and 0 masks. It cannot serve as a dataset release.
- **CAND-03:** The author's Hugging Face profile hosts 0 public datasets or models.

---

### 6. QPOSD / DOI 19258036 REGRESSION
- **Record Identifier:** Zenodo Record `19258036` (DOI: `10.5281/zenodo.19258036`)
- **Resolved Title:** *"Quad-Polarization Dataset for Marine Oil Spill and Look-Alike Segmentation"* (QPOSD)
- **Resolved Authors:** Sohail Jamal and Yu Li, School of Information and Communication Engineering, Beijing University of Technology.
- **Associated Journal Publication:** IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing (JSTARS), DOI: `10.1109/JSTARS.2025.3591692`.
- **Primary Archive:** `QPOSD.zip` ($3,871,940,048$ bytes, MD5: `876771b06f9ae344bdb1843f98b0a7aa`).
- **Physical Characteristics:** 41 multi-look complex (MLC) scenes acquired by NASA/JPL airborne UAVSAR over the U.S. Gulf of Mexico (2010–2022). Polarimetry is fully polarimetric L-band represented by a 9-channel coherency matrix ($T_{11}, T_{12}, \dots, T_{33}$).
- **Mechanism of Historical Conflation:** Record 19258036 was deposited on Zenodo on January 15, 2026. During preliminary literature exploration in Phase 3.1, search queries for newly indexed 2026 SAR oil spill Zenodo entries returned this record alongside recent 2025/2026 preprints. Secondary AI search indices conflated the preprint citation of MORP-Synth with this newly minted SAR dataset record.
- **Automated Regression Guard:** An executable regression test (`test_4_1_exact_qposd_incident_regression` in [`tests/test_provenance_gate.py`](file:///d:/Projects/ocean-sentinel/tests/test_provenance_gate.py)) and negative keyword guards (`UAVSAR`, `L-band`, `Gulf of Mexico`, `QPOSD`, `Quad-Polarization`) ensure that this record is rejected by the pre-download gate during automated execution with zero network bytes transferred.

---

### 7. CROSS-SOURCE CORROBORATION
The required corroboration chain:
$$\text{PAPER} \longrightarrow \text{AUTHOR REPOSITORY} \longrightarrow \text{DOI / DATA RECORD} \longrightarrow \text{METADATA}$$
was evaluated:
1. $\text{Paper} \longrightarrow \text{Author Repository}$: **CONVERGES**. arXiv:2512.02290v1 explicitly points to `github.com/andrexandrex/MorpSynth`.
2. $\text{Author Repository} \longrightarrow \text{DOI / Data Record}$: **BROKEN**. The GitHub repository does not link to any Zenodo DOI or data hosting URL.
3. $\text{Paper} \longrightarrow \text{DOI / Data Record}$: **BROKEN**. The paper states masks *will be* uploaded upon acceptance; no DOI is minted.
4. $\text{Data Record} \longrightarrow \text{Metadata}$: **NON-EXISTENT**. No published Zenodo record exists for MORP-Synth.

The trust chain fails at the data record stage. Status remains **UNVERIFIED / UNRESOLVED**.

---

### 8. VERSION / RECORD RECONCILIATION
- **Preprint Version:** arXiv:2512.02290 has exactly one submitted version (`v1`, submitted Dec 4, 2025). No `v2` or revised submission exists.
- **GitHub Version:** The repository `andrexandrex/MorpSynth` contains 7 commits on branch `main` (last commit `6ad25de8f411` on Nov 30, 2025). No release tags exist (`[]`).
- **Zenodo Versions:** No concept record or version record exists for MORP-Synth on Zenodo.

---

### 9. OBSERVED FACTS
1. arXiv:2512.02290v1 is authored by Andre Juarez, Luis Salsavilca, Frida Coaquira, and Celso Gonzales at UNALM, Lima, Peru.
2. The MORP-Synth Peruvian dataset comprises 2,112 labeled $512 \times 512$ patches from 40 Sentinel-1 GRD IW VV scenes (2014–2024).
3. The preprint explicitly notes under Data Availability that Peruvian ground-truth masks and metadata will be uploaded to Zenodo upon manuscript acceptance.
4. The GitHub repository `andrexandrex/MorpSynth` contains code but 0 dataset rasters or masks.
5. Zenodo record 19258036 is titled *"Quad-Polarization Dataset for Marine Oil Spill and Look-Alike Segmentation"* (QPOSD) by Sohail Jamal and Yu Li (Beijing University of Technology), containing airborne UAVSAR L-band data over the Gulf of Mexico.
6. The directory `data/raw/external_validation` does not exist on disk (0 external bytes).
7. Zero active curl or python download processes exist on the system.
8. All six frozen scientific artifact hashes match certified values.
9. Canonical EXP-02C test metrics are verified as: $\text{IoU} = 0.79808$, $\text{Dice} = 0.88770$, $\text{Precision} = 0.84864$, $\text{Recall} = 0.93054$, Threshold $= 0.22$.

---

### 10. INFERENCES
1. The authors of MORP-Synth have not yet received formal journal manuscript acceptance, or have not completed the Zenodo upload post-acceptance.
2. Initial protocol drafts in Phase 3.1 ingested a secondary search engine result that hallucinated an association between the newly minted QPOSD Zenodo record (Jan 15, 2026) and the MORP-Synth preprint (Dec 2025).

---

### 11. UNVERIFIED
1. The exact journal to which the MORP-Synth manuscript was submitted and its current peer-review status.
2. The projected date when the Peruvian ground-truth masks will be released to Zenodo.
3. Whether the authors would provide pre-publication access to the masks upon private academic request.

---

### 12. DATA ACCESS STATUS
**Classification:** **`RED: MORP_SYNTH_DATA_ACCESS_UNRESOLVED`**  
The dataset is publicly unavailable in raw raster/mask format. No authorized download can occur.

---

### 13. PRE-DOWNLOAD PREFLIGHT STATUS
The preflight contract at [`experiments/DATASET_PREFLIGHT_MORP_SYNTH.json`](file:///d:/Projects/ocean-sentinel/experiments/DATASET_PREFLIGHT_MORP_SYNTH.json) has been updated to Version 1.1.0:
- Target status: **`UNRESOLVED`**
- Verified target specifications: Sentinel-1 C-band IW VV GRD, 2,112 patches ($512\times 512$), 5-class CleanSeaNet harmonization, Peruvian coastal domain.
- Candidate 19258036: Evaluated and marked **`REJECTED (BLOCKED_DATASET_PROVENANCE)`**.
- Token status: `token_issued = null`.
- Bytes authorized: **`0`**.

---

### 14. ACQUISITION FIREWALL
- **Dataset bytes downloaded:** **`0`**
- **Archive transfer requests issued:** **`0`**
- **Archives extracted:** **`0`**
- **External model inference executed:** **`0`**
- **Retraining / fine-tuning executed:** **`0`**
- **Threshold tuning executed:** **`0`**
- **External raster bytes on disk:** **`0`**

The acquisition firewall is 100% intact.

---

### 15. SCIENTIFIC FIREWALL
Re-verified canonical test results for production model EXP-02C (`official_test_results.json`):
- **Threshold:** `0.22` (strictly locked)
- **IoU:** `0.79808`
- **Dice:** `0.88770`
- **Precision:** `0.84864`
- **Recall:** `0.93054`

Zero model weights, thresholds, or benchmark metrics were modified.

---

### 16. STALE / CONTRADICTORY DOCUMENT CHECK

| File Path | Location | Historical Stale Claim | Authoritative Resolution |
| :--- | :--- | :--- | :--- |
| `docs/dataset-selection.md` | Lines 37, 118 | Lists DOI `10.5281/zenodo.19258036` as Peruvian MORP-Synth | Marked as historical error; resolved as QPOSD |
| `docs/dataset-reconnaissance.md`| Lines 27, 114, 439, 487 | Lists `10.5281/zenodo.19258036` as Peruvian S1 (~3.2 GB) | Marked as historical error; resolved as QPOSD |
| `experiments/EXTERNAL_VALIDATION_READINESS.md` | Line 283 | Lists `10.5281/zenodo.19258036` as Peruvian S1 DOI | Marked as historical error; superseded by remediation |
| `experiments/MORP_SYNTH_ACQUISITION_BLOCKED_20260909.md` | Incident Audit | Documents QPOSD abort incident | Kept intact as permanent historical evidence |

---

### 17. FINAL DECISION
**Terminal State:** **`BLOCKED_DATASET_PROVENANCE`**  
Because no authoritative, public dataset release of MORP-Synth exists, external validation data acquisition remains strictly blocked.

---

### 18. NEXT PERMITTED ACTION
1. Stand down external data acquisition for MORP-Synth until the authors announce manuscript acceptance and publish an authoritative Zenodo DOI.
2. Present findings to the CAO. If external validation is required prior to MORP-Synth publication, the CAO may designate an alternative, already-published spaceborne Sentinel-1 C-band marine oil spill dataset for evaluation under the pre-download provenance gate.

---

### 19. PROHIBITED ACTIONS
1. **DO NOT** download QPOSD or any files from Zenodo record 19258036.
2. **DO NOT** substitute another dataset without explicit CAO authorization and provenance gate qualification.
3. **DO NOT** attempt to guess or synthesize missing MORP-Synth masks.
4. **DO NOT** execute model inference on unverified external rasters.
5. **DO NOT** train, fine-tune, or adjust production model weights.
6. **DO NOT** alter the locked production threshold (`0.22`).
7. **DO NOT** stage or commit working tree changes.
