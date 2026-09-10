# Trujillo Part III Frozen EXP02C Evaluation Report

**Date:** September 9, 2026  
**Investigator:** CAO & Antigravity IDE Agent  
**Frozen Checkpoint:** EXP02C Epoch 26 (`best_model.pt`)  
**Checkpoint SHA-256:** `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A`  
**Locked Inference Threshold:** `0.22`  
**Evaluation Status:** **`FROZEN INFERENCE FIREWALL ENFORCED — ZERO INFERENCE EXECUTED`**  

---

## 1. Executive Decision
- **Evaluation Status:** **`BLOCKED AT INGESTION BOUNDARY`** [OBSERVED FACT].
- **Inference Decision:** Exactly **0 forward passes** were executed [OBSERVED FACT].
- **Firewall Enforcement:** Under the CAO core safety principle:
  $$\text{PROVENANCE} \rightarrow \text{ARCHIVE INTEGRITY} \rightarrow \text{PHYSICAL CONTRACT} \rightarrow \text{MODEL COMPATIBILITY} \rightarrow \text{FROZEN INFERENCE}$$
  Because physical acquisition was halted at the network boundary due to Zenodo IP rate-limiting (`TRUJILLO_PART_III_ACQUISITION_FAILED`), physical qualification was not performed. The model inference firewall was strictly enforced. No unverified, synthetic, or corrupted data was passed into the model.

---

## 2. Frozen Model Identity
- **Architecture:** SegFormer-B2 with Dual-Polarization SAR Head (`in_channels=2`, classes=1).
- **Run Identifier:** `exp02c_annealed_hard_negative_20260909_144000` (Epoch 26).
- **Canonical Checkpoint Path:** `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/best_model.pt`
- **Verified SHA-256:** `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` (Verified 100% PASS).
- **Canonical Frozen Normalization Contract:**
  - Channel Means: `-33.2331369895`, `-19.9412158528`
  - Channel Standard Deviations: `6.4899856660`, `4.5313456848`
  - Channel Order Mapping: **UNKNOWN** (do NOT claim channel 0=VH or channel 1=VV as fact without authoritative source evidence).
- **Model State Modification:** Strictly prohibited and verified unchanged ($0\text{ weight modifications}$).

---

## 3. Threshold
- **Locked Production Threshold:** **`0.22`**
- **Threshold Optimization:** **`STRICTLY FORBIDDEN`**. No threshold sweeps, calibration tuning, or Pareto searches were performed or permitted.

---

## 4. Dataset Role
- **Scientific Role:** **`SAME-FAMILY HELD-OUT TEST SET / SAME-FAMILY GENERALIZATION`**
- **Non-Equivalence Clarification:** Trujillo Part III is NOT an independent cross-domain benchmark, NOT a cross-basin generalization test, and NOT an independent geographic acquisition. It represents held-out test scenes from the same Gulf of Mexico geographic basin and SNAP preprocessing pipeline as canonical Part I.

---

## 5. Evaluation Population
- **Target Population (Reported by Authors):** 450 test image samples (150 oil spill, 150 look-alike, 150 clean sea) [UNVERIFIED until physically inspected].
- **Evaluated Population:** **`0 samples`** (Acquisition blocked at network boundary) [OBSERVED FACT].

---

## 6. Global Metrics
- **Global IoU:** `N/A (Zero inference executed)`
- **Global Dice:** `N/A`
- **Precision:** `N/A`
- **Recall:** `N/A`

---

## 7. Category Metrics
- **Oil Spill Category:** `N/A`
- **Look-Alike Category:** `N/A`
- **Clean Sea Category:** `N/A`

---

## 8. Size-Bucket Metrics
- **Small (<500 positive pixels):** `N/A`
- **Medium (500–2500 positive pixels):** `N/A`
- **Large (>2500 positive pixels):** `N/A`

---

## 9. False-Positive Analysis
- **False-Positive Pixel Burden:** `N/A`
- **False-Positive Connected Components:** `N/A`

---

## 10. Area-Ratio Analysis
- **Predicted / Ground-Truth Area Ratio:** `N/A`

---

## 11. Distribution Statistics
- **Per-Sample Distribution:** `N/A`

---

## 12. Failure Analysis
- **Model Failure Modes:** None observed (model never executed on unverified data).
- **System Failure Mode [OBSERVED FACT]:** Network acquisition access failure resulting from Zenodo rate-limiting (`HTTP 403 Forbidden`).
- **Causality [INFERENCE]:** Host network IP rate-limiting following earlier high-frequency parallel requests is an inference supported by chronology. Handled safely without data corruption or pipeline leakage.

---

## 13. Comparison to Frozen Baseline
- **Canonical EXP02C Official Benchmark (Trujillo Part I Test Partition):**
  - **IoU:** `0.79808`
  - **Dice:** `0.88770`
  - **Precision:** `0.84864`
  - **Recall:** `0.93054`
- **Part III Observed Comparison:** Awaiting physical data acquisition and qualification.
- **Firewall Integrity:** Official baseline metrics remain 100% certified and untouched.

---

## 14. Scientific Interpretation
- **Scientific Conclusion:** The scientific firewall successfully prevented unverified or corrupted inference. In real-world remote sensing deployments, robust fail-closed gates must halt the evaluation pipeline before inference when external data acquisition cannot be authoritatively completed.
- **Language Invariant:** When Part III acquisition is successfully completed under a cleared network route, its evaluation must be classified strictly as **"same-family held-out evaluation"**, never as "cross-domain generalization".

---

## 15. Limitations
1. **Network Transfer Barrier:** Direct byte acquisition from Zenodo was prevented by Cloudflare IP rate-limiting (`HTTP 403 Forbidden`).
2. **Same-Family Confounding:** Even upon acquisition, Part III shares spatial domain (Gulf of Mexico) and calibration pipeline with training data, precluding claims of cross-sensor or cross-basin domain shift robustness.

---

## 16. Reproducibility Information
- **Environment:** Windows 10/11, Python 3.10.9 (`D:\Projects\ocean-sentinel\venv\Scripts\python.exe`).
- **Resumability Verification:** 5/5 automated unit tests passing (`tests/test_acquisition_resumability.py`), proving deterministic detection of stale states, checksum errors, DOI mismatches, unexpected filenames, and incomplete archives.
- **Git Commit Boundary:** Tracked working tree clean (0 staged, 0 tracked modified, untracked artifacts present outside Git), HEAD locked at `97567f712684a011a6849c6bc0af7b6c561bef1e`.
