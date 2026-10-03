# PROVENANCE DISCREPANCY FORENSIC AUDIT & RECONCILIATION
**Project:** Ocean Sentinel  
**Authority:** CAIO Scientific Governance  
**Experiment ID:** EXP-04_HARD_NEGATIVE_ABLATION  
**Attempt ID:** EXP04_ATTEMPT_001  
**Target Artifact:** `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json`  
**Date:** 2026-09-11  
**Status:** FULLY RECONCILED & VERIFIED  

---

## 1. Executive Summary

During the execution of EXP-04 (PID 6872), CAIO scientific oversight flagged a hash discrepancy between the hash stated in the Phase 5D prompt instructions:
$$\text{Prompt String: } \mathbf{3867671E639F020CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699}$$
and the hash reported by the preflight audit and training script:
$$\text{Actual Digest: } \mathbf{3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4}$$

In accordance with CAIO protocol, an immediate forensic investigation was launched without assuming the discrepancy was benign. The investigation conclusively established:
1. **The physical file on disk has never been modified** since its initial creation on 2026-09-11 at 20:41:01 UTC.
2. **Three independent cryptographic methods** (Python `hashlib`, PowerShell `Get-FileHash`, Windows `CertUtil`) produce identical digests: `3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4`.
3. **Every pre-existing repository artifact, contract, and test suite**—dating back to Phase 5B candidate freeze—explicitly codified this exact digest.
4. **The prompt string was mathematically identified as a prompt-level copy-paste collision:** characters 17–64 of the anomalous prompt string are character-for-character identical to the 48-character suffix of the canonical teacher baseline checkpoint hash (`9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`).
5. **Verdict:** `MANIFEST_PROVENANCE = VERIFIED`, `EXP04_RUN_VALIDITY = VALID`.

---

## 2. Character-by-Character Forensic Deconstruction

A side-by-side alignment reveals the exact mechanism of the text splicing collision:

| Source | Prefix (Chars 1–16) | Suffix (Chars 17–64) |
| :--- | :--- | :--- |
| **Actual Manifest on Disk** | `3867671E639F020A` | `686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4` |
| **Teacher Baseline Checkpoint** | `9B8BD867DC02C68C` | `C062125074E8B21789FBBBAA55C903D55D8904003BDD1699` |
| **Prompt String (Discrepancy)** | `3867671E639F020C` | `C062125074E8B21789FBBBAA55C903D55D8904003BDD1699` |

### Key Observations:
* **Characters 17 to 64:** In the prompt string, characters 17 to 64 are **100% identical** to the second half of the teacher baseline hash (`C062125074E8B21789FBBBAA55C903D55D8904003BDD1699`).
* **Character 16:** In the prompt string, character 16 was transcribed as `C` instead of `A`.
* **Conclusion:** During the compilation of the Phase 5D prompt, a multi-line buffer copy operation accidentally spliced the 48-character suffix of the teacher baseline hash onto the manifest prefix.

---

## 3. Independent Cryptographic Multi-Method Audit

The manifest `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json` was independently evaluated using three disjoint implementations [OBSERVED FACT]:

1. **Python 3.10 `hashlib.sha256()`:**
   `3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4`
2. **PowerShell `Get-FileHash -Algorithm SHA256`:**
   `3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4`
3. **Windows Native `certutil -hashfile ... SHA256`:**
   `3867671e639f020a686c5acca4fe5da4280eb7daeab9bd9fef467c192aa9f9f4`

* **File Size:** Exactly `261,621` bytes across all file system queries.
* **Filesystem Timestamps:**
  - `CreationTime:` `2026-09-11 20:41:01`
  - `LastWriteTime:` `2026-09-11 20:41:01`
  *(Zero bytes modified since initial harvest).*

---

## 4. Repository-Wide Provenance Evidence

A global ripgrep audit across the entire repository confirmed that `3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4` is the sole, authoritative hash recorded in every historical document, test, script, and contract:

1. `tests/test_phase_5_guardrails.py:148` (Phase 5B integrity test)
2. `scripts/train_exp03.py:58` (Phase 5B training constant)
3. `scripts/train_exp04.py:64` (Phase 5D training constant)
4. `experiments/PHASE_5B_CANDIDATE_MANIFEST_FREEZE_AUDIT_20260911.md:131,200` (Original candidate freeze audit)
5. `experiments/PHASE_5B_EXP03_TRAINING_EXECUTION_REPORT_20260911.md:175` (EXP-03 execution report)
6. `experiments/PHASE_5B_FINAL_PRETRAINING_ENVIRONMENT_AND_INTEGRITY_GATE_20260911.md:83,294`
7. `experiments/PHASE_5B_FINAL_TRAINING_LAUNCH_READINESS_AUDIT_20260911.md:33,300`
8. `experiments/PHASE_5B_HARD_NEGATIVE_TRAINING_CONTRACT_20260911.md:95`
9. `experiments/PHASE_5C_EXP04_HYPOTHESIS_AND_TRAINING_CONTRACT_20260911.md:85` (EXP-04 preregistration contract)
10. `experiments/performance/exp03_baseline_hard_neg/run_state.json:29` (EXP-03 actual run state)
11. `experiments/performance/exp04_hard_neg_ablation/run_state.json:33` (EXP-04 actual run state)
12. `experiments/performance/exp04_hard_neg_ablation/run_manifest.json:24` (EXP-04 initialization manifest)

**Crucially:** The anomalous prompt string `3867671E639F020CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` returned **zero matches** anywhere in the repository.

---

## 5. Candidate Content Integrity Verification

To ensure zero internal drift or candidate corruption, every candidate entry was re-verified against the canonical specification:
* **Total Candidates:** Exactly $400$.
* **Unique Parent Scenes:** Exactly $273$ (maximum $2$ candidates per parent scene).
* **Ground Truth Purity:** $100.0\%$ clean water ($GT = 0$ for all $400$ candidates).
* **False Positive Pixel Range:** Min $691$ pixels, Max $262,144$ pixels (median $2,090$, mean $22,303.6$).
* **Candidate Ordering:** Strictly verified to match $(- \text{fp\_pixels}, \text{parent\_stem}, \text{row\_offset}, \text{col\_offset})$.
* **First Candidate:** `00088_r03_c00` ($262,144$ FP pixels).
* **Last Candidate:** `00553_r01_c00` ($691$ FP pixels).

---

## 6. Scientific Governance Disposition

* **Classification:** External prompt typographical paste collision (the repository and on-disk files are 100% pure and untouched).
* **Manifest Provenance:** **VERIFIED**
* **EXP-04 Run Validity:** **VALID** (Operating under PID 6872 on the exact frozen manifest from EXP-03).
* **Action Taken:** PID 6872 remains authorized to continue execution without interruption.
