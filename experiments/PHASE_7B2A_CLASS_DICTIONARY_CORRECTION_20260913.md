# OCEAN SENTINEL — PHASE 7B.2A CLASS DICTIONARY FORENSIC CORRECTION
**Document Identifier:** `PHASE_7B2A_CLASS_DICTIONARY_CORRECTION_20260913`  
**Governing Roles:** Senior CAO Scientific Data / Benchmark Auditor, Remote-Sensing Benchmark Auditor, ML Protocol Auditor  
**Date:** September 13, 2026  
**Status:** **AUTHORITATIVE SCIENTIFIC CORRECTION & AUDIT PRESERVATION RECORD**  
**Associated Preserved Artifact:** [`data/metadata/li_class_dictionary.json`](file:///d:/Projects/ocean-sentinel/data/metadata/li_class_dictionary.json)  
**Authoritative Replacement:** [`data/metadata/li_authoritative_class_dictionary.json`](file:///d:/Projects/ocean-sentinel/data/metadata/li_authoritative_class_dictionary.json) (`SHA-256: 9377DA6310804E459F2113914F6C933FF42F03277EC2D740A1FE29630A46DE46`)  

---

### 1. EXECUTIVE STATEMENT OF AUDIT INCIDENT

A material inconsistency was detected between the project's initial assumed class dictionary (`li_class_dictionary.json`) and the authoritative published literature for the Li et al. dataset (`10.5281/zenodo.14279466`).

Earlier project summaries categorized the dataset as containing 15 viable semantic classes, including Class 14 as an "Oil Spill" class. An exhaustive byte-level scan across all **5,011 distributed label PNG masks** ($328,400,896$ total pixels) was conducted to resolve this discrepancy.

#### Critical Forensic Findings:
1. **The Authoritative Paper Focuses Exclusively on 12 Phenomena:**
   - The peer-reviewed paper (Li et al., *Remote Sensing* 2025, 18(1), 113; *ESSD Preprint* 2024-222) defines the dataset as **12 typical oceanic and atmospheric phenomena**: Atmospheric Front (AF), Oceanic Front (OF), Rainfall (RF/RC), Iceberg (IC/IB), Sea Ice (SI), Pure Ocean Wave (POW), Wind Streak (WS), Low Wind Area (LWA), Biological Slick (BS), Micro Convective Cells (MCC), Internal Waves (IWs), and Ocean Eddy.
   - The paper's benchmark evaluation (Tables 1 and 2) reports Dice coefficients strictly for these **12 phenomena plus Background (BG)**. Neither artificial objects (HM) nor oil spills (OS) were included in the paper's model training or reported metrics.
2. **The "Oil Spill" Tag (Class 14) is an Incidental Placeholder:**
   - The authors' Zenodo metadata catalog explicitly states:  
     *“15. OS: Unlike ‘BS’, ‘OS’ represents mineral oil spills appearing in the SAR image (currently, there is insufficient data available for training, which will be supplemented in the future).”*
   - Across the entire 5,011-image dataset, Class 14 appears in **exactly 4 images**, comprising only **1,702 pixels** ($0.000518\%$ of the dataset):
     - `s1a-iw-grd-vv-20180103t114323-20180103t114348-019990-0220c9-001-4.png`: 700 pixels
     - `s1a-iw-grd-vv-20220129t214214-20220129t214239-041681-04f588-001-54.png`: 640 pixels
     - `s1a-iw-grd-vv-20220717t114605-20220717t114635-044140-0544c1-001-25.png`: 103 pixels
     - `s1a-iw-grd-vv-20221003t141635-20221003t141700-045279-0569af-001-54.png`: 259 pixels
3. **Class 13 (HM: Artificial Objects) Contains 207 Images:**
   - Class 13 (Heavy Metal / ships / wind turbines / rafts) accounts for 30,647 pixels across 207 images (202 IW, 5 WV).
4. **Mandatory Protocol Action:**
   - The claim that the Li et al. dataset provides an oil spill segmentation target is **FORMALLY RETRACTED**.
   - The dataset must **NEVER** be used as an oil spill ground truth training or evaluation set.
   - The dataset is approved strictly as a **Tier-1 Ocean Phenomena Recognition & Look-Alike Benchmark** for training the Ocean Phenomena Specialist (OPS-01).

---

### 2. FORMAL RECONCILIATION TABLE

| Domain / Attribute | Authoritative Paper (ESSD / RS 2025) | Zenodo Record Description (14279466) | Distributed Files (Byte Audit of 5,011 Masks) | Ocean Sentinel Phase 7B.2 Interpretation | Corrected Scientific Status (Phase 7B.2A) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Phenomenon Count** | 12 phenomena + Background | 12 phenomena in narrative; 15 tags in label dictionary | 15 distinct pixel values observed (0 to 14) | Assumed 15 active classes | **12 core/auxiliary phenomena + BG + HM (vessels); OS excluded (insufficient data)** |
| **Class 0 (BG)** | Seawater background | Unlabelled parts in JSON | 32,264,741 pixels (1,769 images) | Background | **Core Background** |
| **Classes 1–12** | 12 phenomena (AF, OF, RF, IC, SI, POW, WS, LWA, BS, MCC, IWs, Eddy) | Enumerated as tags 2–13 | Dense pixel representations (1.4M to 91.5M pixels each) | 12 phenomena | **12 Valid Phenomena (6 core look-alikes, 4 auxiliary, 2 cryospheric)** |
| **Class 13 (HM)** | Not evaluated in model benchmark | Artificial objects (ships, wind turbines, rafts) | 30,647 pixels across 207 images | Artificial objects | **Maritime Attribution Context (ships/infrastructure)** |
| **Class 14 (OS)** | **NOT INCLUDED** (0 mention in results/tables) | Explicitly flagged: *“insufficient data available for training”* | **Only 4 images, 1,702 pixels (0.0005%)** | Listed as "Oil Spill" class | **EXCLUDED (Statistically unusable; 4 images only; zero training role)** |
| **Dataset Purpose** | Multi-phenomenon oceanic segmentation | Multi-phenomenon semantic segmentation | Multi-phenomenon segmentation masks | Proposed as look-alike & potential oil benchmark | **STRICTLY Ocean Phenomena & Look-Alikes (NO oil training/evaluation)** |

---

### 3. PRESERVATION OF HISTORICAL ARTIFACTS

To maintain immutable audit history under Ocean Sentinel Data Governance Rule 42:
- The historical artifact [`data/metadata/li_class_dictionary.json`](file:///d:/Projects/ocean-sentinel/data/metadata/li_class_dictionary.json) is **PRESERVED UNCHANGED**.
- All downstream pipelines and guardrails shall reference the authoritative artifact:
  [`data/metadata/li_authoritative_class_dictionary.json`](file:///d:/Projects/ocean-sentinel/data/metadata/li_authoritative_class_dictionary.json).
