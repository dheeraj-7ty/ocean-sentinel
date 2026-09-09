# Git History Evidence & Provenance Forensics

**Investigation Target**: Provenance and timeline of `lr = 1e-4` vs `5e-4` and `CosineAnnealingLR` vs `CosineAnnealingWarmRestarts`.  
**Repository**: `D:\Projects\ocean-sentinel`  
**HEAD Commit**: `8f444de0d2516429cbe2a7a40b3c2d431c4f526c` (Initial baseline commit)  
**Branch**: `master`

---

## 1. Git Log & Pickaxe Search

To determine whether `5e-4` or `CosineAnnealingWarmRestarts` was ever introduced into the repository, we performed exhaustive pickaxe searches (`git log -S`) across all branches, tags, and commits.

### Search A: `CosineAnnealingWarmRestarts`
```bash
git log -S "CosineAnnealingWarmRestarts" --all --full-history --oneline
```
**Result**: `0 commits found`.  
`CosineAnnealingWarmRestarts` has NEVER existed in any committed file or commit diff throughout the entire history of this repository.

### Search B: `5e-4`
```bash
git log -S "5e-4" --all --full-history --oneline
```
**Result**: `0 commits found`.  
`5e-4` has NEVER existed in any committed file or commit diff throughout the entire history of this repository.

### Search C: `T_0` / `T_mult`
```bash
git log -S "T_0" --all --full-history --oneline
git log -S "T_mult" --all --full-history --oneline
```
**Result**: `0 commits found`.  
Warm restart hyperparameters were never present in git history.

### Search D: `1e-4` and `CosineAnnealingLR`
```bash
git log -S "CosineAnnealingLR" --all --full-history --oneline
git log -S "1e-4" --all --full-history --oneline
```
**Result**:
```
8f444de Initial commit
```
Both `lr = 1e-4` and `scheduler = CosineAnnealingLR` were introduced in the initial canonical commit (`8f444de`) in `scripts/train_exp01.py` and have remained unchanged.

---

## 2. Working Tree & Untracked Code Search

Ripgrep searches across all untracked and tracked files in `src/`, `scripts/`, `tests/`, and `experiments/` yielded:
- `grep "CosineAnnealingWarmRestarts"`: 0 occurrences in source code or configuration files.
- `grep "5e-4"`: 0 occurrences in any training script, configuration, or model file.

All occurrences of `CosineAnnealingWarmRestarts` or `5e-4` in the entire repository are found strictly in:
1. The user's forensic mission prompt prompting this investigation.
2. The newly created regression test `tests/test_canonical_exp01_fingerprint.py` which explicitly tests rejection of `5e-4` and `CosineAnnealingWarmRestarts`.

---

## 3. Transcript Forensics: Root Cause of Hallucinated Claims

Investigation of the Antigravity agent transcript logs at:
`C:\Users\Dheeraj\.gemini\antigravity-ide\brain\308f8c25-7910-4ffa-bd2b-d0acf98875f7\.system_generated\logs\transcript_full.jsonl`

Revealed the exact origin:
- At line 4008 of `transcript_full.jsonl`, during the previous turn's final response rendering ("Section 29: Final Certification"), the LLM generated summary text in chat.
- While writing the free-form markdown response text, the assistant erroneously hallucinated:
  ```
  AdamW:
  - lr = 5e-4
  - weight_decay = 1e-2

  Scheduler:
  - CosineAnnealingWarmRestarts
  - T_0 = 5
  - T_mult = 1
  - eta_min = 1e-6
  ```
- **Crucial Corroborating Finding**: In that very same turn, the assistant created the audit directory `experiments/performance/pre_upload_zero_defect_hardening_20260907_042853/`.
  Inspection of the files written by that turn:
  - `canonical_fingerprint.json`: Contained `"learning_rate": 0.0001`, `"scheduler": "CosineAnnealingLR"`, `"T_max": 30`.
  - `report.md`: Recorded `learning_rate = 1e-4` and `CosineAnnealingLR`.
  
Thus, the actual files, code, and serialized fingerprints remained 100% faithful to canonical EXP01 (`1e-4`, `CosineAnnealingLR`), while the chat output suffered from a transient textual hallucination.

---

## 4. Git Forensic Conclusion

1. Neither `5e-4` nor `CosineAnnealingWarmRestarts` is part of git history or code.
2. `1e-4` and `CosineAnnealingLR` are the sole and undisputed canonical configuration parameters present since repository inception (`8f444de`).
3. No later experiment branching or silent code drift occurred.
