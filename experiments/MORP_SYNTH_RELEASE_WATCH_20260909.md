# MORP-Synth Public Dataset Release Watch Record
**Date of Audit:** 2026-09-09T23:06:00+05:30  
**Authority:** CAO Directive — Phase 3.2C Release Watch  
**Target Entity:** MORP-Synth Peruvian Ground-Truth Masks and Metadata (arXiv:2512.02290v1)  
**Primary Authors:** Andre Juarez, Luis Salsavilca, Frida Coaquira, Celso Gonzales  
**Primary Repository:** `https://github.com/andrexandrex/MorpSynth`  
**Current Status:** **`MORP_SYNTH_DATA_ACCESS = UNRESOLVED`**  

---

### 1. SOURCES AND REPOSITORIES CHECKED

| Source Category | Exact URI / Endpoint Consulted | Retrieval Mechanism | Observed State |
| :--- | :--- | :--- | :--- |
| **Official GitHub Repository** | `https://github.com/andrexandrex/MorpSynth` | GitHub REST API v3 / Raw Read | Head commit `6ad25de8f411aedc6784a2f882b4b2a89710d12c` (Nov 30, 2025). Code for INADE and MORP present. Exactly 0 raw raster, GeoTIFF, or mask files present. |
| **GitHub Release Tags** | `https://api.github.com/repos/andrexandrex/MorpSynth/tags` | GitHub REST API v3 | Empty array (`[]`). Exactly 0 tags created. |
| **GitHub Releases** | `https://api.github.com/repos/andrexandrex/MorpSynth/releases` | GitHub REST API v3 | Empty array (`[]`). Exactly 0 releases published. |
| **Primary Preprint Record** | `https://arxiv.org/abs/2512.02290` | arXiv API / HTML metadata | Single version (`v1`, submitted Dec 4, 2025). No `v2` or revised submission exists. Stated under Data Availability: "The Peruvian ground-truth masks and metadata will be uploaded to Zenodo upon manuscript acceptance." |
| **Author Profile Hub** | `https://huggingface.co/andrexandrex` | Hugging Face Hub metadata | Profile exists for André Juárez Castro. 0 public models and 0 public datasets hosted. |
| **Zenodo DOI Registry** | `https://zenodo.org/api/records` | REST API query | Zero records matching MORP-Synth or author deposits identified. |
| **Candidate DOI Check** | `10.5281/zenodo.19258036` | Zenodo Record API | Belongs exclusively to QPOSD (airborne UAVSAR, Gulf of Mexico, Jamal & Li, Jan 15, 2026). Unrelated to MORP-Synth. |

---

### 2. AUDIT FINDINGS

1. **New Release Detection:** No authoritative public data release was identified in the sources and searches reviewed during this audit.
2. **DOI Status:** No public canonical DOI or Zenodo record has been minted for the MORP-Synth dataset as of the audit date.
3. **Repository Files:** The GitHub repository remains a code-only repository. No raw SAR rasters or segmentation masks are hosted.
4. **Peer-Review / Acceptance Status:** The peer-review and publication status of the manuscript is unverified from public sources. No formal journal citation has been published.
5. **Data Access Classification:** The public access status of the dataset remains:
   $$\mathbf{MORP\_SYNTH\_DATA\_ACCESS = UNRESOLVED}$$

---

### 3. PROTOCOL FOR SUBSEQUENT MONITORING

Subsequent audits shall check the following specific trigger conditions:
1. **GitHub Commit Activity:** Monitor `andrexandrex/MorpSynth` for new commits adding data download URLs or zenodo badge links.
2. **GitHub Releases:** Monitor `andrexandrex/MorpSynth/releases` for tagged dataset releases.
3. **arXiv Updates:** Monitor arXiv:2512.02290 for a revised `v2` manuscript containing an updated Data Availability statement with an active Zenodo DOI.
4. **Zenodo Publication:** Query Zenodo for new deposits associated with authors Andre Juarez, Luis Salsavilca, Frida Coaquira, Celso Gonzales, or Universidad Nacional Agraria La Molina.

**Acquisition Boundary:**  
Under no circumstances may any data transfer begin without a formal, authenticated `VerifiedProvenanceToken` issued by the pre-download provenance gate.
