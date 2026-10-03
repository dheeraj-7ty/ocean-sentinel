# PHASE 7B.2B-R4: COMPLETE RAW GIT STATE FORENSIC CAPTURE
**Document Reference:** `experiments/PHASE_7B2B_R4_GIT_STATE_FORENSIC_20260913.md`  
**Execution Phase:** Phase 7B.2B-R4 (Repository-State Provenance Gate)  
**Execution Timestamp:** 2026-09-13T06:06:00Z  
**Branch:** `master`  
**Classification:** RAW REPOSITORY FORENSIC CAPTURE  

---

## 1. RAW COMMAND OUTPUTS

### 1.1 `git branch --show-current`
```
master
```

### 1.2 `git diff --cached --name-status`
```
(EMPTY - ZERO FILES STAGED)
```

### 1.3 `git diff --name-status`
```
M	.gitignore
M	src/ocean_sentinel/ingestion/dataset.py
```

### 1.4 `git status --ignored --porcelain`
```
!! scratch/
```

### 1.5 `git status --porcelain -uall` (Summary & Full Accounting)
- **Total Lines Returned:** 1,991
- **Tracked Modified (` M`):** 2
  - `.gitignore` (Mtime: pre-existing baseline; modifies ignore rules for weights & Phase 5/Part-III artifacts)
  - `src/ocean_sentinel/ingestion/dataset.py` (Mtime: pre-existing baseline; dataset ingestion logic)
- **Tracked Deleted (` D`):** 0
- **Untracked Files (`??`):** 1,989

---

## 2. RECONCILIATION OF THE "1,988 PENDING CHANGES" DISCREPANCY

During IDE inspection, the Source Control panel indicated approximately 1,988 pending changes. Forensic analysis of `git status --porcelain -uall` reveals the exact source of this number:

1. **Phase 6 Part-III Evaluation Payload Files ($N = 1,808$, 90.9% of untracked files):**
   - Location: `experiments/performance/phase_6_part_iii_external_evaluation/attempt_001/`
   - Content: 900 `.npz` binary prediction arrays (450 mapping_a, 450 mapping_b) and 908 `.json` per-scene metrics and run snapshots generated during Phase 6 external evaluation.
   - Root Cause: While `.gitignore` was updated to ignore `trujillo_part_iii_eval_20260911_exp01/mapping_a/` and `mapping_b/`, `phase_6_part_iii_external_evaluation/attempt_001/` was never added to `.gitignore`. Because git evaluates directories recursively with `-uall`, all 1,808 files appear individually in Git status and IDE Source Control.

2. **Historical Performance & Audit Reports in `experiments/` ($N = 101$, 5.1%):**
   - 6 files in `trujillo_part_iii_eval_20260911_exp01/` (metrics and freeze hashes).
   - 95 historical markdown audit reports and summaries from Phases 5A–5H, 6, 7A, 7B.0, 7B.1, 7B.2, 7B.2A, 7B.2B, 7B.2B-R2, and 7B.2B-R3.

3. **Metadata Manifests in `data/metadata/` ($N = 29$, 1.5%):**
   - Historical manifests and audit records spanning Phase 5, Phase 7A proxy datasets, Phase 7B.1, and Phase 7B.2/7B.2B.

4. **Execution Scripts in `scripts/` ($N = 26$, 1.3%):**
   - Pre-existing standalone evaluation, clustering, and audit scripts from Phases 5, 6, 7A, and 7B.

5. **Regression Test Suites in `tests/` ($N = 17$, 0.9%):**
   - Pre-existing regression suites from Phase 5 (10 files), Phase 6 (2 files), Phase 7A (1 file), Phase 7B.0 (1 file), Phase 7B.1 (1 file), Phase 7B.2 (1 file), Phase 7B.2A (1 file), and Phase 7B.2B (1 file).

6. **Source Code Modifications in `src/` ($N = 1$, 0.05%):**
   - `src/ocean_sentinel/ingestion/firewall.py` (pre-existing Part-III quarantine firewall enforcement module from Phase 6).

7. **Root Dependency Lockfile ($N = 1$, 0.05%):**
   - `uv.lock` (package dependency lockfile).

---

## 3. SUMMARY STATUS
- **Total Untracked:** 1,989
- **Total Tracked Modified:** 2
- **Total Tracked Deleted:** 0
- **Total Porcelain Status Entries:** 1,991
- **Machine-Readable Ledger:** Codified in [`data/metadata/phase_7b2b_r4_repository_artifact_ledger.json`](file:///d:/Projects/ocean-sentinel/data/metadata/phase_7b2b_r4_repository_artifact_ledger.json).
