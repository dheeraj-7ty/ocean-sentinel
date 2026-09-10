# Phase 3.2 Abort-and-Reconcile Forensic Audit Report: Invalid Dataset Provenance & QPOSD Acquisition Hard Stop

**Audit Date:** 2026-09-09  
**Authority:** Chief AI Officer (CAO) Directive  
**Status:** **BLOCKED_DATASET_PROVENANCE**  
**Data Access Status:** **MORP_SYNTH_DATA_ACCESS = UNRESOLVED**  
**Repository Branch:** `master`  
**Committed HEAD:** `97567f712684a011a6849c6bc0af7b6c561bef1e`  

---

## 1. Executive Decision

The invalid QPOSD acquisition was halted during execution and the partial artifacts were removed after forensic capture due to a fatal dataset provenance mismatch. 

During the initial acquisition phase, the candidate DOI `10.5281/zenodo.19258036` (previously assumed in Phase 3.1 protocol notes to host Peruvian Sentinel-1 / MORP-Synth) was authoritatively resolved via the Zenodo REST API. The resolved record identity was discovered to be:
- **Title:** *"Quad-Polarization Dataset for Marine Oil Spill and Look-Alike Segmentation"* (QPOSD)
- **Authors:** Sohail Jamal & Yu Li (Beijing University of Technology, published Jan 2026, IEEE JSTARS)
- **Sensor & Platform:** Airborne UAVSAR L-band quad-polarization ($T$ coherency matrix, 9 channels)
- **Geographic Domain:** U.S. Gulf of Mexico (2010–2022)
- **Target Semantic:** 4-class RGB masks (Sea, Oil, Look-alike, Land)

This dataset directly violates every physical and architectural requirement of our frozen production model (spaceborne Sentinel-1 C-band dual-polarization VV/VH, 2 channels, Peruvian Humboldt Current upwelling zone, binary $\{0, 1\}$ masks). Despite this mismatch, the execution script initiated a download of `QPOSD.zip` and companion scripts, accumulating 977,315,023 bytes (~977 MB) across partial stream chunks before intervention.

In accordance with the CAO Non-Negotiable Rule (**A provenance mismatch is a HARD STOP**), the following immediate actions were executed:
1. All download processes (task handles, `curl.exe`, and `python.exe` streams) were immediately terminated.
2. Complete forensic evidence was cataloged with individual SHA-256 hashes for all 11 downloaded partial files in [`scratch/morp_synth_forensic_evidence.json`](file:///d:/Projects/ocean-sentinel/scratch/morp_synth_forensic_evidence.json).
3. All partial files and the directory `data/raw/external_validation` were wiped from disk. Exactly 0 external bytes remain.
4. The qualification state machine was transitioned to **`BLOCKED_DATASET_PROVENANCE`**.
5. The ingestion subsystem was hardened with a mandatory pre-download provenance gate ([`src/ocean_sentinel/ingestion/provenance_gate.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ingestion/provenance_gate.py)) and validated with a comprehensive test suite ([`tests/test_provenance_gate.py`](file:///d:/Projects/ocean-sentinel/tests/test_provenance_gate.py)).
6. All six frozen scientific hashes were re-verified (100% PASS).
7. External dataset acquisition remains strictly blocked pending independent, authoritative resolution of the true Peruvian MORP-Synth data access location.

---

## 2. Observed Facts

The following statements are verified physical facts observed directly from repository state, system processes, remote API responses, and local file audits:

1. **Zenodo Record 19258036 Identity:** Querying `https://zenodo.org/api/records/19258036` returns metadata for *"Quad-Polarization Dataset for Marine Oil Spill and Look-Alike Segmentation"* (QPOSD) by Sohail Jamal and Yu Li, Beijing University of Technology, associated with DOI `10.1109/JSTARS.2025.3591692`.
2. **Sensor & Polarimetry:** The authoritative Zenodo metadata description and companion script `load_qposd_example.py` establish that QPOSD consists of airborne UAVSAR L-band polarimetric SAR data providing 9-channel coherency matrix ($T$) arrays.
3. **Geographic Domain:** The metadata and companion documentation define the geographic acquisition domain as the U.S. Gulf of Mexico.
4. **Archive Filename & Size:** The primary archive on Zenodo record 19258036 is named `QPOSD.zip`, with expected byte size $3,871,940,048$ bytes ($3,692.6$ MB) and MD5 checksum `876771b06f9ae344bdb1843f98b0a7aa`.
5. **Partial Download Execution:** Prior to abort, `scratch/parallel_download.py` spawned 8 curl streams and downloaded two companion python scripts plus 9 partial chunk files under `data/raw/external_validation/morp_synth_zenodo_19258036/`.
6. **Total Downloaded Volume:** The total volume written to disk across all 11 files before termination was exactly $977,315,023$ bytes ($932.04$ MB).
7. **Process Termination:** Background task `task-11952` was terminated. Subsequent inspection via `Get-WmiObject Win32_Process` confirmed exactly 0 active `curl.exe` processes and 0 active download `python.exe` processes.
8. **Filesystem Cleanup:** Deletion of `data/raw/external_validation` was executed via `Remove-Item -Recurse -Force`. A post-cleanup check confirmed `Test-Path data/raw/external_validation` returned `False`. Exactly 0 external bytes exist on disk.
9. **Canonical Raw Directory:** `data/raw` contains exclusively `trujillo_2024` with its 1,200 canonical `.tif` files.
10. **Six Certified Hashes:** All six frozen scientific hashes match their certified expected values with 100% precision.
11. **Git Index Cleanliness:** `git diff --cached --name-only` is completely empty (zero staged files).

---

## 3. Inferences

The following statements are logical deductions derived from observed facts:

1. **Origin of DOI Error:** DOI `10.5281/zenodo.19258036` was recorded in the Phase 3.1 protocol draft as a presumed Zenodo deposit for MORP-Synth because an early search query associated with recent 2025/2026 oil spill SAR datasets surfaced this newly minted Zenodo record (published Jan 15, 2026), which was conflated with the Andrex et al. (arXiv:2512.02290) preprint without verifying the underlying metadata attributes.
2. **Incompatibility with Model Architecture:** Even if fully downloaded, QPOSD could never be ingested by the production ResNet34-UNet model without fundamentally altering the model input layer (`in_channels=2` vs 9-channel coherency matrix), which is strictly forbidden by scientific firewalls.
3. **Control Flow Omission:** The workflow scripts `download_morp_zenodo.py` and `parallel_download.py` lacked a pre-download provenance assertion block; they deferred dataset validation to post-extraction physical audits (`extract_and_inventory.py`), allowing byte transfer to start on any target specified in the protocol configuration.

---

## 4. Unverified

The following statements cannot be verified from local evidence or current public APIs:

1. **Exact Release Date of Peruvian MORP-Synth Zenodo Deposit:** The preprint (arXiv:2512.02290v1, Dec 2025) states: *"The Peruvian ground-truth masks and metadata will be uploaded to Zenodo upon manuscript acceptance."* Whether manuscript acceptance has occurred or what the future Zenodo DOI will be cannot be verified from public sources at this time.
2. **Alternate Host Locations:** Whether raw Peruvian Sentinel-1 tiles corresponding to the MORP-Synth study are hosted on private institutional Google Drive, HuggingFace, or personal servers is unverified.

---

## 5. Invalid Acquisition Stop

### 5.1 Process Discovery and Inspection
Immediately upon receipt of the CAO Directive at 22:03:59+05:30, process inspection was executed:
- Background task: `task-11952` (running `python scratch/parallel_download.py`).
- Child processes: Multiple `curl.exe` processes downloading byte-range chunks from `https://zenodo.org/api/records/19258036/files/QPOSD.zip/content`.

### 5.2 Termination Method
Termination was executed via the agent task management subsystem:
1. `manage_task kill` invoked on `task-11952`.
2. Process tree audit executed via PowerShell:
   ```powershell
   Get-WmiObject Win32_Process | Where-Object { $_.Name -match "curl|python" -and $_.CommandLine -match "QPOSD|parallel_download|19258036" }
   ```
3. Returned: **0 processes**.
4. Termination mode: **Graceful task tree termination followed by process audit confirmation**.

---

## 6. Forensic Evidence

Before any file was removed from disk, complete forensic evidence was captured, including file paths, byte sizes, and individual SHA-256 checksums, persisted in [`scratch/morp_synth_forensic_evidence.json`](file:///d:/Projects/ocean-sentinel/scratch/morp_synth_forensic_evidence.json).

### 6.1 Metadata Summary
- **Requested Identity:** Peruvian S1 / MORP-Synth (Andrex et al., arXiv:2512.02290)
- **Requested DOI:** `10.5281/zenodo.19258036`
- **Resolved Record ID:** `19258036`
- **Resolved Title:** `Quad-Polarization Dataset for Marine Oil Spill and Look-Alike Segmentation`
- **Resolved DOI:** `10.5281/zenodo.19258036`
- **Resolved Authors:** Sohail Jamal, Yu Li (Beijing University of Technology)
- **Resolved Publication Date:** 2026-01-15
- **Archive URL:** `https://zenodo.org/api/records/19258036/files/QPOSD.zip/content`
- **Expected Archive Size:** 3,871,940,048 bytes (3,692.6 MB)
- **Expected Archive MD5:** `876771b06f9ae344bdb1843f98b0a7aa`
- **Actual Downloaded Bytes at Stop:** **977,315,023 bytes** (~977.3 MB)
- **Archive Status:** Partial / Incomplete (24.6% of archive chunks)

### 6.2 Catalog of Partial Files Captured Before Deletion
| File | Path | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| `chunk_0.part` | `.../chunk_0.part` | 146,710,528 | `64960677E8E98B8AC47C04FC972037AFC1A459DD1F32B329FCD79133296C6D7D` |
| `chunk_0.part.tmp` | `.../chunk_0.part.tmp` | 83,968,000 | `E0C65E1B04595B6A6D45294D62C8A9138DF0B2EC0B1627F328BB71671866DF7F` |
| `chunk_1.part.tmp` | `.../chunk_1.part.tmp` | 111,632,384 | `BE0ADB10060EAEBA1C9A318CE99F6BF654513BD73D0A01CF59209BEB4A43BA4C` |
| `chunk_2.part.tmp` | `.../chunk_2.part.tmp` | 81,821,696 | `4B98A6F068AA8CDE57E57F590E4298F4DFB214FEAC7D1C8430CCB4DE8DCF0E33` |
| `chunk_3.part.tmp` | `.../chunk_3.part.tmp` | 112,902,144 | `1D68E7E5A44F49ADF4EFDB57A005BDEE94D78568163675C594008F1C044D2CD7` |
| `chunk_4.part.tmp` | `.../chunk_4.part.tmp` | 119,439,360 | `C0A5E2833DFAF547F8B9A1677114EFFDEB348D4BFDC3FD02D085AA72DE648DB1` |
| `chunk_5.part.tmp` | `.../chunk_5.part.tmp` | 82,964,480 | `7BE6CFFD6CB4B27FFBBC8CF1CDC60BA9B0B62F90FC3A077C46EC32BE8C21A5BF` |
| `chunk_6.part.tmp` | `.../chunk_6.part.tmp` | 115,425,280 | `78A3F419A8F2F4B193D84F33AA522AF2659A5A8D2E2275EAF1669E0D3FF11AFD` |
| `chunk_7.part.tmp` | `.../chunk_7.part.tmp` | 122,441,728 | `17701E28B820DEB86740C84974FF16D8885A6021731B8190729A0E1600F5B277` |
| `load_qposd_example.py` | `.../load_qposd_example.py` | 2,249 | `7D0A4B8C0D366765AA5AB3BA3414620E0729ABC136B667C67E5F59DED29013B6` |
| `patchify_qposd_example.py` | `.../patchify_qposd_example.py` | 7,174 | `355A6F8A2B6C5D7E36C4A14957FAAF68BC1D69DD8646DC6886E3A2690D8574AA` |
| **Total** | **11 files** | **977,315,023** | — |

---

## 7. Root Cause / Control-Flow Failure Analysis

### 7.1 Detailed Failure Path
The failure sequence unfolded through the following control-flow progression:

```
[Phase 3.1 Protocol Design]
  └─ Literature search noted candidate DOI: 10.5281/zenodo.19258036
  └─ Stored in EXTERNAL_VALIDATION_READINESS.md as target DOI

[Phase 3.2 Execution Initialization]
  └─ phase0_recon.py verified clean HEAD and 6 frozen hashes (PASS)
  └─ Execution passed to download_morp_zenodo.py / parallel_download.py

[Acquisition Failure Point]
  └─ Downloader queried Zenodo API for record 19258036
  └─ Extracted archive download URL: .../files/QPOSD.zip/content
  └─ NO PRE-DOWNLOAD PROVENANCE ASSERTION EXISTED
  └─ Workflow assumed validation would occur AFTER download in extract_and_inventory.py
  └─ 8 curl streams initiated, downloading 977 MB of QPOSD.zip
```

### 7.2 Root Cause Categorization
1. **Deferred Validation Architecture:** The initial workflow was architected with a sequential "Download $\rightarrow$ Extract $\rightarrow$ Inspect" pipeline. It placed dataset qualification inside Phase 3 (`extract_and_inventory.py`) and Phase 4 (`physical_raster_audit.py`). This allowed invalid bytes to be transferred before any identity check was performed.
2. **Directory-Name Presumption:** The destination folder was named `data/raw/external_validation/morp_synth_zenodo_19258036/`. The presence of `morp_synth` in the directory string masked the fact that the underlying payload was `QPOSD.zip`. A dataset must never become "MORP-Synth" merely because its local directory name says MORP-Synth.
3. **Absence of Negative Keyword Guards:** The download code lacked negative keyword guards (e.g. `UAVSAR`, `airborne`, `L-band`, `Gulf of Mexico`, `QPOSD`).

---

## 8. Cleanup Result

Following forensic evidence capture, safety verification was conducted:
1. **Canonical Dataset Safety:** Verified that `data/raw/trujillo_2024` was completely isolated and unaffected.
2. **Frozen Checkpoint Safety:** Verified that none of the 13 untracked `.pt` checkpoints resided anywhere near `data/raw/external_validation`.
3. **Removal:** The invalid directory tree `data/raw/external_validation` was completely removed.
4. **Post-Cleanup Audit:**
   ```powershell
   Test-Path data/raw/external_validation -> False
   Get-ChildItem data/raw -> Only trujillo_2024 (1200 .tif files)
   ```
5. **Disk State:** Exactly **0 invalid or external bytes** remain in the repository.

---

## 9. Workflow Hardening

To prevent this class of provenance failure from silently recurring in automated workflows, the codebase has been hardened with an enforceable provenance gate.

### 9.1 New Module: `src/ocean_sentinel/ingestion/provenance_gate.py`
A new domain module was implemented providing:
- **`DatasetProvenanceSpecification`:** Structured Pydantic model encapsulating authoritative dataset criteria:
  - `target_identity`: Explicit name (e.g. `Peruvian S1 / MORP-Synth`)
  - `expected_platform`: Platform expectation (e.g. `Sentinel-1`)
  - `expected_sensor_band`: Radar frequency band (`C-band`)
  - `expected_polarizations`: Polarizations (`['VV', 'VH']`)
  - `expected_geographic_domain`: Target region (`Peru`)
  - `required_keywords`: Mandatory keywords (`['MORP', 'Peru']`)
  - `prohibited_keywords`: Immediate-rejection guards (`['UAVSAR', 'airborne', 'L-band', 'Gulf of Mexico', 'QPOSD', 'Quad-Polarization']`)
- **`ResolvedRecordMetadata`:** Structured representation of remote record identity parsed from API responses.
- **`ProvenanceGateDecision`:** Explicit enum (`PASSED`, `BLOCKED_DATASET_PROVENANCE`).
- **`ProvenanceGateError`:** Specialized exception inheriting from `DatasetProvenanceError`.
- **`ProvenanceGate`:** Enforces evaluation logic:
  - Validates DOI and Record ID if specified.
  - Scans title, description, keywords, and file names against prohibited keywords.
  - Verifies presence of required keywords and geographic domain.
  - `enforce_gate()`: Raises `ProvenanceGateError` before any socket or file stream can be opened.

### 9.2 Unit Test Suite: `tests/test_provenance_gate.py`
A comprehensive 7-test suite was implemented and verified (100% PASS):
1. `test_morp_synth_spec_defaults`: Verifies canonical specification defaults.
2. `test_qposd_fails_morp_synth_gate`: Confirms QPOSD fails with `BLOCKED_DATASET_PROVENANCE` and identifies prohibited keywords (`UAVSAR`, `QPOSD`, `Gulf of Mexico`).
3. `test_enforce_gate_raises_on_qposd`: Confirms `enforce_gate()` raises `ProvenanceGateError`.
4. `test_valid_morp_synth_passes_gate`: Confirms a valid Peruvian MORP-Synth record passes cleanly.
5. `test_doi_mismatch_detection`: Verifies rejection of unexpected DOIs.
6. `test_record_id_mismatch_detection`: Verifies rejection of unexpected record IDs.
7. `test_parse_zenodo_record`: Verifies deterministic parsing of raw Zenodo API JSON.

### 9.3 Hardened Download Scripts
Both [`scratch/download_morp_zenodo.py`](file:///d:/Projects/ocean-sentinel/scratch/download_morp_zenodo.py) and [`scratch/parallel_download.py`](file:///d:/Projects/ocean-sentinel/scratch/parallel_download.py) were refactored to execute `ProvenanceGate.enforce_gate()` prior to any file or process initialization. When tested against record `19258036`, they immediately exit with code 1 and transition state to `BLOCKED_DATASET_PROVENANCE` with 0 bytes transferred.

---

## 10. MORP-Synth Provenance Status

A thorough investigation of authoritative public literature and repository sources was conducted:

1. **Preprint Evidence (arXiv:2512.02290v1, 2 Dec 2025):**
   - Title: *"Enhancing Cross Domain SAR Oil Spill Segmentation via Morphological Region Perturbation"*
   - Authors: Andrex Jara, Gabriel E. Humpire-Mamani, Ronald M. Hernandez, Cesar Beltran (Pontificia Universidad Catolica del Peru)
   - Section *Data and Code Availability*:
     > *"The Peruvian ground-truth masks and metadata will be uploaded to Zenodo upon manuscript acceptance. The code is publicly available at https://github.com/andrexandrex/MorpSynth."*
2. **GitHub Code Repository (`andrexandrex/MorpSynth`):**
   - Contains PyTorch code for the MORP synthesis pipeline, data transforms, and model architectures.
   - Contains script `dataset_peru_train.py` referencing local paths to Peruvian Sentinel-1 GeoTIFF patches (`/data/peru/...`).
   - Does **NOT** host the raw GeoTIFF rasters or ground truth masks in the Git repository.
3. **Zenodo Query:**
   - A search of Zenodo records using query keywords `"MORP-Synth"` and `"Morphological Region Perturbation"` returned **0 published records**.
4. **Current Status Declaration:**
   - The Peruvian ground-truth dataset has **not yet been published to Zenodo with an active DOI**.
   - Status: **`MORP_SYNTH_DATA_ACCESS = UNRESOLVED`**.

---

## 11. Scientific Firewall

The scientific firewall has remained 100% impenetrable throughout this entire incident:
- **Model Inference:** Exactly **0** model inferences were performed on QPOSD or any other external data.
- **Model Retraining:** Exactly **0** training loops were executed.
- **Fine-Tuning:** Exactly **0** fine-tuning operations occurred.
- **Threshold Tuning:** The production threshold remains frozen at `0.22`.
- **Data Mixing:** Exactly **0** external rasters or masks were mixed with `trujillo_2024`.
- **Benchmark Integrity:** Frozen EXP-02C official test metrics ($\text{IoU} = 0.79808$, $\text{Dice} = 0.88770$, $\text{Precision} = 0.84864$, $\text{Recall} = 0.93054$, Threshold $= 0.22$; derived $F_1 = 0.88770$) remain untouched and uncompromised.

---

## 12. Frozen Hash Verification

All six certified frozen scientific artifacts were re-verified via SHA-256 computation:

| Artifact | Path | Expected Hash | Actual Hash | Status |
| :--- | :--- | :--- | :--- | :--- |
| **EXP02C Best Model** | `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/best_model.pt` | `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` | `14073F677F0525D2...` | **PASS** |
| **Official Test Results** | `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/official_test_evaluation/official_test_results.json` | `ECF2D4AE10AFDE939BA3DDA99912488D1C3632EFD460118A26B17AD393437C6F` | `ECF2D4AE10AFDE93...` | **PASS** |
| **Spatial Split Manifest** | `data/metadata/trujillo_2024/spatial_split_manifest.json` | `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` | `C052720A954C2E7A...` | **PASS** |
| **Candidate Manifest** | `experiments/performance/exp02b_0_hard_negative_design_20260909_021500/candidate_manifest.json` | `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7` | `5876A4E65FA636F6...` | **PASS** |
| **EXP01 Best Model** | `experiments/exp01_baseline/best_model.pt` | `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | `9B8BD867DC02C68C...` | **PASS** |
| **EXP02B-1 Best Model** | `experiments/performance/exp02b_1_hard_negative_training_20260909_094500/kernel_output/.../best_model.pt` | `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B` | `54B4B098E1EB64A7...` | **PASS** |

**Firewall Result:** **ALL 6 CERTIFIED ARTIFACTS VERIFIED 100% PASS.**

---

## 13. Git / Source Control Audit

A strict Source Control audit was conducted in compliance with CAO Git Safety rules:
- **Staged Changes:** `git diff --cached --name-only` returns **0 files**. Exactly zero files are staged.
- **Tracked Modifications:** `git diff --name-only` returns **0 files**. The tracked working tree is completely clean.
- **Untracked Checkpoints:** Exactly 13 authorized `.pt` binary checkpoints remain safely outside Git.
- **Untracked Task Files:**
  - `experiments/EXTERNAL_VALIDATION_READINESS.md` (Phase 3.1 protocol)
  - `experiments/MORP_SYNTH_ACQUISITION_BLOCKED_20260909.md` (this report)
  - `src/ocean_sentinel/ingestion/provenance_gate.py` (workflow hardening module)
  - `tests/test_provenance_gate.py` (provenance gate unit tests)
- **Git Commit / Push:** Exactly 0 commits and 0 pushes were executed. Repository HEAD remains `97567f712684a011a6849c6bc0af7b6c561bef1e`.

---

## 14. Final State

The system state machine has been transitioned to:

```json
{
  "status": "BLOCKED",
  "qualification_decision": "BLOCKED_DATASET_PROVENANCE",
  "current_phase": "BLOCKED_DATASET_PROVENANCE",
  "provenance_resolution_status": "MORP_SYNTH_DATA_ACCESS = UNRESOLVED",
  "external_validation_status": "BLOCKED",
  "inference_status": "NOT_RUN",
  "training_status": "NOT_RUN",
  "resumability_expectations": "BLOCKED_PENDING_AUTHORITATIVE_MORP_SYNTH_PROVENANCE"
}
```

The acquisition is **officially stopped, quarantined data deleted, workflow hardened, and Phase 3.2 blocked**.

---

## 15. Next Permitted Action

The only permitted next actions are:
1. **Authoritative Literature & Author Inquiry:** Contact the authors of the MORP-Synth paper (Andrex Jara / Pontificia Universidad Catolica del Peru) or monitor their official GitHub repository (`https://github.com/andrexandrex/MorpSynth`) for the official Zenodo DOI announcement upon manuscript acceptance.
2. **Alternative Standard Benchmark Sourcing:** If the CAO designates an alternative external benchmark dataset with established authoritative provenance (e.g. standard Sentinel-1 C-band dual-pol spaceborne SAR datasets), define its `DatasetProvenanceSpecification` first, pass the provenance gate, and only then authorize acquisition.

---

## 16. Prohibited Actions

Until authoritative MORP-Synth provenance is formally established and approved by the CAO, the following actions remain **strictly prohibited**:
1. **NO downloading of QPOSD or resumption of record 19258036.**
2. **NO automatic substitution of another unverified dataset.**
3. **NO renaming of any dataset to MORP-Synth.**
4. **NO model inference on unverified external rasters.**
5. **NO model retraining or fine-tuning.**
6. **NO threshold searching or tuning.**
7. **NO staging or committing of unapproved files.**
8. **NO modification of frozen benchmark artifacts or split manifests.**
