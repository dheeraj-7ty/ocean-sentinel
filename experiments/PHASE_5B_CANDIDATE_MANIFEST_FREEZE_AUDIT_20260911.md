# Ocean Sentinel — Phase 5B: Candidate Manifest Freeze & Independent Integrity Audit

**Date:** 2026-09-11  
**Authority:** Chief Architect Officer (CAO)  
**Role:** Phase 5B Candidate Manifest Harvest & Independent Integrity Auditor  
**Document Identity:** `PHASE_5B_CANDIDATE_MANIFEST_FREEZE_AUDIT_20260911.md`  
**Execution Class:** Pre-Training Integrity Gate & Manifest Freeze  
**Target Manifest:** `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json`  

---

## 1. Executive Summary

Operating strictly under CAO authority, the deterministic hard-negative candidate harvest and independent manifest integrity gate for Phase 5B has been executed. No model training, checkpoint generation, validation evaluation, or Trujillo Part III evaluation was performed.

The objective of this gate was to generate the pre-registered 400-tile hard-negative candidate manifest exclusively from the development `SplitName.TRAIN` partition of the canonical Trujillo Part I dataset, prove absolute selection determinism, independently audit the manifest on disk, calculate and record its cryptographic SHA-256 digest, and freeze the candidate set as immutable prior to any training authorization.

All pre-flight safety gates, qualification invariants, firewall checks, and independent readback assertions **PASSED**. The manifest is formally frozen.

---

## 2. Input Artifact Identities

| Artifact Role | Repository Path | Expected SHA-256 Digest | Verified SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Teacher Checkpoint** | `experiments/exp01_baseline/best_model.pt` | `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | **MATCH** |
| **Spatial Split Manifest** | `data/metadata/trujillo_2024/spatial_split_manifest.json` | `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` | `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` | **MATCH** |
| **Phase 5B Training Contract** | `experiments/PHASE_5B_HARD_NEGATIVE_TRAINING_CONTRACT_20260911.md` | Pre-registered 2026-09-11 | Pre-registered 2026-09-11 | **VERIFIED** |
| **Hardware Environment** | Local Host | NVIDIA GeForce RTX 3050 6GB Laptop GPU | CUDA:0 (`sm_86`) | **VERIFIED** |

---

## 3. Teacher Checkpoint Hash

- **Path:** `experiments/exp01_baseline/best_model.pt`
- **Expected Digest:** `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
- **Observed Digest:** `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
- **Integrity Assessment:** SHA-256 digest matched before and after execution, supporting unchanged checkpoint bytes. Model architecture strictly confirmed as `ResNet34UNet` with `slice_variance_scaled` adaptation (24,346,305 parameters).

---

## 4. Spatial Split Manifest Hash

- **Path:** `data/metadata/trujillo_2024/spatial_split_manifest.json`
- **Expected Digest:** `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0`
- **Observed Digest:** `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0`
- **Integrity Assessment:** Confirmed partition distribution:
  - `SplitName.TRAIN`: 840 parent patches (13,440 tiles)
  - `SplitName.VAL`: 180 parent patches (2,880 tiles)
  - `SplitName.TEST`: 180 parent patches (2,880 tiles)

---

## 5. Train-Split Reservoir Recount

Exhaustive unaugmented inference was conducted over all 13,440 tiles of `SplitName.TRAIN` using the teacher checkpoint under canonical normalization:
- **Total Training Tiles Scanned:** 13,440
- **Empty Training Tiles ($GT == 0$):** 8,357 tiles (62.18% of training partition)
- **Oil-Containing Training Tiles ($GT > 0$):** 5,083 tiles (37.82% of training partition)
- **Tiles with False Alarm Area $FP \ge 100\text{ px}$ ($\tau = 0.22$):** 1,605 tiles
- **Tiles with False Alarm Area $FP \ge 1,000\text{ px}$ ($\tau = 0.22$):** 528 tiles
- **Fully Qualified Candidate Reservoir:** 1,539 tiles satisfying all four qualification criteria ($GT == 0$, $FP \ge 100$, component area $\ge 100$, $P_{\max} \ge 0.50$).

Historical numbers from Phase 5A development analysis were independently re-derived and verified from fresh repository execution.

---

## 6. Exact Candidate Rule

Candidates were qualified and ranked using the frozen pre-registered Phase 5B rules:
1. **Purity Gate:** Ground-truth oil mask must be strictly empty ($GT = 0$). Any positive pixel causes categorical exclusion.
2. **Detection Threshold:** Decision threshold frozen at $\tau = 0.22$.
3. **False Alarm Area:** Total false-positive pixels $FP \ge 100$.
4. **Morphological Coherence:** At least 1 connected component with area $\ge 100$ pixels (8-connectivity), eliminating isolated sensor speckle.
5. **Confidence Ceiling:** Peak false-positive probability $P_{\max} \ge 0.50$.
6. **Parent-Scene Cap:** Maximum 2 candidate tiles selected per parent scene stem.
7. **Deterministic Tie-Breaking Sort Key:**
   $$\text{sort\_key} = (-\text{fp\_pixels}, \text{parent\_stem}, \text{row\_offset}, \text{col\_offset})$$

---

## 7. Selected Candidate Count

- **Target Candidate Count:** 400
- **Selected Candidate Count:** **400 unique tiles**
- **Rank 1 Candidate:** Tile `00088_r03_c00` ($FP = 262,144\text{ px}$, $P_{\max} = 0.9961$, mean FP conf $= 0.9707$)
- **Rank 400 Candidate:** Tile `00876_r00_c02` ($FP = 691\text{ px}$, $P_{\max} = 0.6558$, max component $= 691\text{ px}$)
- **Candidate Pool Summary:**
  - Max FP pixels: 262,144
  - Min FP pixels: 691
  - Median FP pixels: 2,090
  - Mean FP pixels: 22,303.6

---

## 8. Parent-Scene Distribution

To prevent spatial over-concentration on individual large scenes, the 2-candidate parent cap was enforced:
- **Total Unique Parent Scenes Represented:** **273 parent scenes**
- **Scenes contributing exactly 1 candidate tile:** 146 scenes ($146 \times 1 = 146$ tiles)
- **Scenes contributing exactly 2 candidate tiles:** 127 scenes ($127 \times 2 = 254$ tiles)
- **Scenes contributing $> 2$ candidate tiles:** 0 scenes (0% violation)
- **Total Candidates:** $146 + 254 = \mathbf{400}$

---

## 9. Determinism Recheck

Two completely independent passes of the parent-scene capping and sorting algorithm were executed on the qualified candidate pool within the runtime session.
- **Run 1 Candidate List vs Run 2 Candidate List:** Bit-for-bit identical across all 400 entries, ranks, coordinates, and metrics.
- **Determinism Proof:** Confirmed. The sort key $(-\text{fp\_pixels}, \text{parent\_stem}, \text{row\_offset}, \text{col\_offset})$ resolves all ties deterministically without runtime jitter.

---

## 10. Manifest Path

- **Relative Path:** `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json`
- **Absolute Path:** `D:\Projects\ocean-sentinel\data\metadata\trujillo_2024\exp03_hard_negative_manifest.json`

---

## 11. Manifest Size

- **Exact File Size:** **261,621 bytes**

---

## 12. Manifest SHA-256

- **Cryptographic SHA-256 Digest:**
  $$\mathbf{3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4}$$

---

## 13. Independent Manifest Verification

An independent auditor script (`scratch/audit_phase_5b_manifest.py`) and dedicated unit test (`test_exp03_hard_negative_manifest_integrity` in `tests/test_phase_5_guardrails.py`) verified the manifest directly from disk:
1. File exists, reads cleanly as valid JSON, and matches exact byte length (261,621 bytes).
2. Computed SHA-256 matches `3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4`.
3. Every candidate entry (400/400) has verified image and mask paths on the filesystem.
4. Every candidate entry (400/400) satisfies $GT = 0$, $FP \ge 100$, $P_{\max} \ge 0.50$, and connected component area $\ge 100$.
5. No duplicate tile paths or duplicate $(r, c)$ coordinate offsets exist.
6. Ordering strictly obeys $(-\text{fp\_pixels}, \text{parent\_stem}, \text{row\_offset}, \text{col\_offset})$.

---

## 14. Part III Firewall Result

The multi-layer scientific firewall (`src/ocean_sentinel/ingestion/firewall.py`) was invoked across all 400 candidate tile identifiers, image paths, and mask paths:
- **Forward Passes on Part III:** 0
- **Part III Tiles in Mining Pool:** 0
- **Part III Path / Token Matches:** 0
- **Firewall Status:** **100% PASS**

---

## 15. Validation Leakage Result

Every candidate's parent patch stem was cross-referenced against `spatial_split_manifest.json`:
- **Candidates from Train Split (`splits.train`):** 400 / 400 (100.0%)
- **Candidates from Validation Split (`splits.val`):** 0 / 400 (0.0%)
- **Candidates from Test Split (`splits.test`):** 0 / 400 (0.0%)
- **Leakage Status:** **100% PASS (Zero Validation Leakage)**

---

## 16. Test Results

The full suite of relevant guardrails and pipeline tests was executed via `pytest`:
```
.\venv\Scripts\pytest.exe tests/test_part_iii_firewall.py tests/test_phase_5_guardrails.py tests/test_artifact_policy.py tests/test_dataset_pipeline.py
```
**Outcome:** **71 passed in 4.35s (0 failures, 0 errors)**.
- `tests/test_part_iii_firewall.py`: 6 passed
- `tests/test_phase_5_guardrails.py`: 8 passed (including `test_exp03_hard_negative_manifest_integrity`)
- `tests/test_artifact_policy.py`: 6 passed
- `tests/test_dataset_pipeline.py`: 51 passed

---

## 17. Git Final State

Execution of `git status` and `git diff` confirms:
- **Staged Changes (`git diff --cached`):** **0 entries** (Strictly no staging performed)
- **Tracked Modified Files (`git diff --name-status`):**
  - `M .gitignore` (tightened artifact policy preserving visibility of metadata)
  - `M src/ocean_sentinel/ingestion/dataset.py` (preflight firewall assertions)
- **Untracked Manifest:**
  - `?? data/metadata/trujillo_2024/exp03_hard_negative_manifest.json` (Visible, untracked, ready for inspection)
- **Commits / Pushes:** Strictly 0 commits, 0 pushes.

---

## 18. Observed Facts

1. The canonical teacher checkpoint `experiments/exp01_baseline/best_model.pt` has SHA-256 `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` [OBSERVED FACT].
2. The spatial split manifest `data/metadata/trujillo_2024/spatial_split_manifest.json` has SHA-256 `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` [OBSERVED FACT].
3. Evaluating the 13,440 training tiles identified exactly 8,357 empty tiles, 1,605 tiles with $FP \ge 100$, and 1,539 fully qualified candidate tiles [OBSERVED FACT].
4. Capping at 2 tiles per parent scene and sorting by $(-\text{fp\_pixels}, \text{parent\_stem}, \text{row\_offset}, \text{col\_offset})$ selected exactly 400 unique candidate tiles from 273 unique parent scenes [OBSERVED FACT].
5. The generated manifest `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json` has size 261,621 bytes and SHA-256 `3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4` [OBSERVED FACT].
6. All 400 selected candidate tiles originate from parent scenes partitioned into `SplitName.TRAIN`; zero originate from validation, test, or Trujillo Part III [OBSERVED FACT].

---

## 19. Inferences

1. Because the candidate pool was harvested exclusively from `SplitName.TRAIN` under frozen model weights, training Phase 5B with these candidates cannot leak validation or Part III outcome information [INFERENCE].
2. The deterministic tie-breaking key guarantees that any independent reconstruction following the Phase 5B protocol will yield an identical 400-tile manifest [INFERENCE].
3. The parent scene cap ensures spatial diversity across 273 scenes, preventing local coastal/island artifact dominance from skewing gradient updates [INFERENCE].

---

## 20. Unverified / Blocking Gaps

1. **Model Training Not Authorized [BLOCKING GAP]:** Generation and freeze of the candidate manifest does not authorize model training. Training requires explicit CAO review and authorization.
2. **Empirical Generalization Unverified [LIMITATION]:** Whether exposure to these 400 mined training negatives will reduce validation false-positive burden without degrading oil recall remains an empirical hypothesis to be tested under Phase 5B.

---

## Final Declarations

| Gate / Audit Dimension | Declaration |
| :--- | :--- |
| **PHASE_5B_CANDIDATE_HARVEST** | **PASS** |
| **PHASE_5B_MANIFEST_INTEGRITY** | **PASS** |
| **PHASE_5B_MANIFEST_FROZEN** | **PASS** |
| **VALIDATION_LEAKAGE_CHECK** | **PASS** |
| **PART_III_LEAKAGE_CHECK** | **PASS** |
| **CANONICAL_TEACHER_CHECKPOINT_INTEGRITY** | **PASS** |
| **GIT_AUDIT** | **PASS** |
| **PHASE_5B_TRAINING_AUTHORIZATION** | **NOT_GRANTED** |

> [!IMPORTANT]
> **CAO REVIEW BOUNDARY**:
> Passing this integrity gate authorizes advancement solely to CAO Review of the Frozen 400-Candidate Manifest.
> **HARD STOP: No model training, no checkpoint generation, no validation evaluation, and no Part III evaluation may occur without explicit CAO authorization.**
