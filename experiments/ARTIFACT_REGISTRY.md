# Ocean Sentinel — Scientific Artifact Registry & Management Policy

**Date:** 2026-09-11  
**Authority:** Chief Architect Officer (CAO)  
**Document Identity:** `experiments/ARTIFACT_REGISTRY.md`  
**Status:** ACTIVE REPOSITORY POLICY  

---

## 1. Purpose & Governing Principles

This registry establishes an auditable, reproducible, and non-destructive management contract for all scientific assets in Ocean Sentinel. 

### Core Tenets:
1. **Provenance Over Convenience:** We do not optimize for a clean Git status panel at the expense of scientific traceability.
2. **Non-Destructive Storage:** Untracked scientific artifacts are never deleted simply because they are outside Git version control.
3. **Surgical Boundary Rules:** Broad wildcard ignores (`*.json`, `*.npz`, `*.pt`, `experiments/`, `experiments/performance/`) are strictly prohibited. Git ignore rules must be path-specific and purpose-specific.
4. **Permanent Immutability of Evaluation Holdouts:** External evaluation benchmarks (specifically Trujillo Part III) and canonical checkpoints are permanently frozen.

---

## 2. Classification Taxonomy

Every artifact in the repository falls into one of four distinct management tiers:

| Tier | Lifecycle Definition | Storage Location | Git Status |
| :--- | :--- | :--- | :--- |
| **GIT-TRACKED** | Human-readable source code, unit tests, canonical manifests, core reports, and lightweight metrics summaries | `src/`, `tests/`, `data/metadata/`, `experiments/*.md`, `experiments/**/metrics/*.json` | Tracked in Git |
| **GIT-IGNORED BUT PRESERVED** | Large generated scientific payloads, per-sample inference tensors, specifically registered binary checkpoint weights, and diagnostic image panels | Registered paths in `.gitignore` (`experiments/exp01_baseline/*.pt`, `experiments/performance/trujillo_part_iii_eval_20260911_exp01/mapping_*/`, etc.) | Preserved on disk; excluded from Git via narrow `.gitignore` rules |
| **PRESERVED ON DISK** | Historical experiment records, cloud rehearsal logs, and qualification trial outputs | `experiments/performance/*_2026*` | Preserved on disk for forensic reproducibility; selectively tracked or ignored |
| **DISPOSABLE / TEMPORARY** | Ephemeral process locks, unbuffered test scratch files, and temporary OS cache debris | `scratch/`, `*.pyc`, `.pytest_cache/` | Excluded from Git; safe to purge only upon explicit verification |

---

## 3. Scientific Checkpoints & Exact Ignore Policy

Model checkpoint binaries (`*.pt`) contain floating-point parameter weights (~278 MB each). To prevent Git repository bloat, specifically identified and generated `.pt` binaries are **GIT-IGNORED BUT PRESERVED**, with their identity, file size, and SHA-256 digest permanently recorded in scientific reports and verified by automated audit scripts.

### Explicitly Registered Checkpoint Paths in `.gitignore`:
1. `experiments/exp01_baseline/*.pt` (EXP-01 baseline best, final, and latest recovery checkpoints)
2. `experiments/archive/exp01_interrupted_20260906_135852/*.pt` (Historical interrupted run)
3. `experiments/performance/exp02b_1_hard_negative_training_20260909_094500/kernel_output/exp02b_1_hard_negative_training/*.pt` (Historical EXP-02B-1 run)
4. `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/*.pt` (Historical EXP-02C run)
5. `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/remote_training_output/*.pt` (Historical EXP-02C remote download)

### Critical Distinction: Future Canonical Experiment Checkpoints
- Global wildcard ignore rules such as `*.pt` or `experiments/**/*.pt` are **STRICTLY PROHIBITED**.
- Any future experiment checkpoint (e.g. `experiments/exp03_future_experiment/best_model.pt`) will **NOT** be hidden automatically from Git status.
- Future checkpoints will remain visible in the working tree until explicitly evaluated, registered in this registry with full provenance (SHA-256, parameter count, validation metrics), and granted an explicit, narrow path in `.gitignore` upon CAO authorization.

| Model Checkpoint Path | Size (Bytes) | SHA-256 Digest | Status & Role |
| :--- | :--- | :--- | :--- |
| `experiments/exp01_baseline/best_model.pt` | 292,465,299 | `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | **CANONICAL EXP-01 BASELINE (FROZEN)** |
| `experiments/exp01_baseline/final_model.pt` | 292,465,299 | `2E4C0881DF2F16810C4494A4071EAB320D12418151CC5F74651E91FE1F0A41AA` | EXP-01 Epoch 30 final state |
| `experiments/exp01_baseline/latest_checkpoint.pt` | 292,469,763 | `2F8F7718D687FF1621F4D92FD7190AE3D582AC67CCD2A529F72E1088A139AA6A` | EXP-01 Recovery state |
| `experiments/archive/exp01_interrupted_20260906_135852/best_model.pt` | 292,458,975 | `8B306D97FA22A8B79E7E0C3F82CD1A60ED85B5DCA903697D4D1771F740AE53B6` | Historical interrupted run |
| `experiments/performance/exp02b_1_hard_negative_training_20260909_094500/kernel_output/exp02b_1_hard_negative_training/best_model.pt` | 292,465,299 | `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B` | Historical EXP-02B-1 candidate |
| `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/best_model.pt` | 292,465,299 | `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` | Historical EXP-02C candidate |

*Rule:* If the SHA-256 digest of `experiments/exp01_baseline/best_model.pt` deviates from `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`, all evaluation and training activities halt immediately. Checkpoint integrity is verified as: *“SHA-256 digest matched before and after execution, supporting unchanged checkpoint bytes.”*

---

## 4. Protected Benchmark Payloads (Trujillo Part III)

The Phase 4D full external benchmark produced 1,806 discrete output files (~3.84 GB total) stored under:
`experiments/performance/trujillo_part_iii_eval_20260911_exp01/`

### Composition & Integrity Structure:
- **`mapping_a/` (900 files, ~1.92 GB):** 450 per-scene prediction JSON metadata files + 450 per-scene float16 prediction NPZ arrays (150 Oil, 150 No oil, 150 Lookalike).
- **`mapping_b/` (900 files, ~1.92 GB):** 450 per-scene prediction JSON metadata files + 450 per-scene float16 prediction NPZ arrays (150 Oil, 150 No oil, 150 Lookalike).
- **`metrics/` (4 files, ~378 KB):** Canonical summary metrics and audit records (`metrics_mapping_a.json`, `metrics_mapping_b.json`, `comparison_summary.json`, `independent_recomputation_audit.json`).
- **`manifests/` (2 files, ~235 KB):** Pairing manifests and input integrity hashes (`freeze_hashes.json`, `trujillo_part_iii_pairing.json`).
- **`logs/` (0 files):** Empty run directory.

### Tracking & Protection Policy:
1. **Per-Scene Prediction Arrays (`mapping_a/`, `mapping_b/`):** Classified as **GIT-IGNORED BUT PRESERVED**. They remain permanently on disk to allow exact re-computation of any metric or spatial figure, but are excluded from Git to prevent repository bloat.
2. **Summary Metrics & Pairing Manifests (`metrics/`, `manifests/`):** Classified as **GIT-TRACKED**. They provide full, human- and machine-readable provenance within version control.
3. **Firewall Isolation:** Trujillo Part III files are programmatically protected by `src/ocean_sentinel/ingestion/firewall.py`. No training, mining, or threshold-tuning code may access this directory.

---

## 5. Development Diagnostic Artifacts (Phase 5A)

1. **Failure Analysis Machine Report (`experiments/performance/phase_5a_failure_analysis/failure_analysis_report.json`):**
   - Classified as **GIT-TRACKED**. Contains full quantitative distributions, connected component statistics, and training split harvest counts.
2. **Visual Diagnostic Panels (`experiments/performance/phase_5a_diagnostics/*.png`):**
   - Classified as **GIT-IGNORED BUT PRESERVED**. 7 composite forensic images ($1536 \times 1024$) demonstrating severe, median, and clean water validation failure modes.

---

## 6. Registration Policy for Future Experiments (Phase 5B and Beyond)

All future experimental workflows (e.g. Phase 5B `EXP-03`) must adhere to this registration protocol:

1. **Pre-Registration Gate:** Before execution, experimental parameters must be frozen in a dedicated contract document (e.g., `experiments/PHASE_5B_HARD_NEGATIVE_TRAINING_CONTRACT_20260911.md`).
2. **Candidate Manifest Registration:** Mined candidate sets must be serialized to `data/metadata/` with per-tile SHA-256 hashes, receive a file-level SHA-256 digest, and be recorded in the audit log prior to training.
3. **In-Namespace Telemetry:** Training runs must emit machine-readable telemetry (`run_state.json`, `progress.json`) to an isolated directory under `experiments/performance/<experiment_id>/`.
4. **Artifact Splitting:**
   - Summary results, configs, and metrics JSON files are to be Git-tracked.
   - Raw `.pt` checkpoint binaries and dense prediction arrays are to be preserved on disk and ignored via narrow `.gitignore` entries.

---

## 7. Active Post-Phase 5A Checkpoint Inventory & Governance Reconciliation (October 2026)

In accordance with Section 3 ("Future checkpoints will remain visible in the working tree until explicitly evaluated, registered in this registry with full provenance... and granted an explicit, narrow path in `.gitignore` upon CAO authorization"), this section registers the inventory of 36 floating-point model checkpoint binaries currently present in the working tree.

### 7.1 Checkpoint Inventory & Canonical Verification
All 36 checkpoint binaries contain floating-point parameter weights (~4.5 GB total). They are explicitly itemized and classified as **PRESERVED ON DISK / GIT_IGNORED_BUT_PRESERVED** with narrow, exact path-specific entries in `.gitignore` under CAO repository policy. Every binary remains physically intact, with integrity currently verified against the registered size and SHA-256 baseline; future immutability is not implied by this record.

| Checkpoint Path | Size (Bytes) | SHA-256 Digest | Governance & Operational Role | Policy Status |
| :--- | :--- | :--- | :--- | :--- |
| `data/ops02/initial_model_state_canonical.pt` | 57,356,426 | `67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D` | OPS-02 canonical initialization state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `data/ops02/initial_model_state.pt` | 57,354,338 | `4BB233DB629E44DE12E41F11809024B7A5BDA4DBCFB19D13752295973117E45C` | OPS-02 initialization state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/performance/exp06_positive_bce_weight/best_model.pt` | 292,461,395 | `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` | **CANONICAL PROTECTED EXP-06 BASELINE** | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/performance/exp06_positive_bce_weight/last_model.pt` | 292,461,395 | `9CA4D910C4804AC994EF8C3E8C96A88AC93BDA2FFD76F9C0817E6C54803D8025` | EXP-06 final epoch state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/performance/exp05_candidate_severity_cap/best_model.pt` | 292,467,395 | `D9FC12E312E5DF012650E8106DCF90782534EFB1BD1E38BA7FDCF4E0802A0481` | EXP-05 best validation state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/performance/exp05_candidate_severity_cap/last_model.pt` | 292,467,395 | `730436C1D97E8F1ABBBBD65739135B986623CF751A202BE1E396BFCCB472A3C0` | EXP-05 final epoch state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/performance/exp04_hard_neg_ablation/best_model.pt` | 292,466,907 | `FAC3C313386F3FE561C2ECF0945B7F960CAA74897C5E8105FB68635529F1320B` | EXP-04 best validation state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/performance/exp04_hard_neg_ablation/last_model.pt` | 292,467,099 | `E6B06344898AA3C3E338E1B9392BABF93A601F1AEDC19740D7AC6411D9A34A7F` | EXP-04 final epoch state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/performance/exp03_baseline_hard_neg/best_model.pt` | 292,463,187 | `BE00C1C8B35A3648FCCAD3864F844ED2EB68E079F2CC390C1BA3EC147BF2DA57` | EXP-03 best validation state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/performance/exp03_baseline_hard_neg/last_model.pt` | 292,463,315 | `811B8C2B04696C8C3C7D30305DB64D926AAA6321B56BBE1B7ED07167CDB2B98A` | EXP-03 final epoch state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01/control_best_model.pt` | 57,350,273 | `FF98D4A93660BC70016FEEAF2F04450B7AC1110226DECBAE027F71FF286633FA` | EXP-07 DIAG01 control best validation state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01/control_last_model.pt` | 57,357,249 | `079A476F86BA581AE15F2FA7F2E4DAA274BF9D38C63358800E3C84B03B73B9C1` | EXP-07 DIAG01 control final epoch state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01/treatment_best_model.pt` | 57,350,669 | `0B7F51B1E902AAC9DF839D2864F1E9658F3B0631813FC47D8ADA1738FFC47745` | EXP-07 DIAG01 treatment best validation state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01/treatment_last_model.pt` | 57,357,645 | `4AFE95A823BE69A4DF4921BAE394C0F846B239728524B1C2704D37754E117573` | EXP-07 DIAG01 treatment final epoch state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_101/control/control_best_model.pt` | 57,350,273 | `86F1AF99128797DCD9024117B8BF9051FD2AD7575DFC2AD0BA4BCC87A6218F97` | EXP-07 DIAG01 replication seed 101 control best state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_101/control/control_last_model.pt` | 57,357,249 | `03F33B5FC6C6462D32B5F0D89454A364597D48A8FEE581193A11F5172A4EE0A6` | EXP-07 DIAG01 replication seed 101 control last state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_101/treatment/treatment_best_model.pt` | 57,350,669 | `CDBA3618FE4A7BECA0D82B11E8E57BE9DD82DA31360C85A523A96577866B74FC` | EXP-07 DIAG01 replication seed 101 treatment best state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_101/treatment/treatment_last_model.pt` | 57,357,645 | `EF4CC726EBEC00DEA1FB7A0F59FD2E02B00C569EA733ED4F6D6251F1740BC74B` | EXP-07 DIAG01 replication seed 101 treatment last state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_202/control/control_best_model.pt` | 57,350,273 | `23DEFB142B43375F2E93A5E16590AE8843A87311A6221786FC43D539C5156E63` | EXP-07 DIAG01 replication seed 202 control best state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_202/control/control_last_model.pt` | 57,357,249 | `EB111C06D59436C0C054964D6E9613D8A7714FA910CFC6041957C633EE97DA32` | EXP-07 DIAG01 replication seed 202 control last state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_202/treatment/treatment_best_model.pt` | 57,350,669 | `000D4E7E0D37CB6A6D562C7B81B8AD2CAE85483BE6BCE07706AD97F709EA1CDD` | EXP-07 DIAG01 replication seed 202 treatment best state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_202/treatment/treatment_last_model.pt` | 57,357,645 | `D79B6F75EA48EE89DDD62092D2983F884958A9234B79530F7D6596650D892A73` | EXP-07 DIAG01 replication seed 202 treatment last state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_303/control/control_best_model.pt` | 57,350,273 | `1E5D948B323AA97AD1A0B381128C2697806E23973D30E31BD25313DA68E723DB` | EXP-07 DIAG01 replication seed 303 control best state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_303/control/control_last_model.pt` | 57,357,249 | `8581F9E5F683CD113634D03FEADED2FE9F069C1F5B3B2F5C0C3E384CE6B1A0C9` | EXP-07 DIAG01 replication seed 303 control last state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_303/treatment/treatment_best_model.pt` | 57,350,669 | `837068454D10BF82B8AE85A52D618CD99B7AED4F1E0371B034B73C763663FF8B` | EXP-07 DIAG01 replication seed 303 treatment best state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_303/treatment/treatment_last_model.pt` | 57,357,645 | `D917796974DBBE2B0D940C6B109E8B054FA424128DBDB4CC131C9F58ACDC82A0` | EXP-07 DIAG01 replication seed 303 treatment last state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_404/control/control_best_model.pt` | 57,350,273 | `E2F180A0439C75588EDCDFE27D72A4B5FCCF08C4EB5BB3AB8B50CA5E4217B3A3` | EXP-07 DIAG01 replication seed 404 control best state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_404/control/control_last_model.pt` | 57,357,249 | `73315143D2D542454E4C46FCFAD7236DB6056B2B5427497847C1F8F521F35802` | EXP-07 DIAG01 replication seed 404 control last state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_404/treatment/treatment_best_model.pt` | 57,350,669 | `B8286A1CD00EF5D1CA1E00BCC4A8211BEBF751A96832D91E1439F1061C3D1D79` | EXP-07 DIAG01 replication seed 404 treatment best state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_DIAG01_REPLICATION/seed_404/treatment/treatment_last_model.pt` | 57,357,645 | `4863142510DA450850DEF4E01BF087F91FD0CE40C8091F756E85FE60930B7910` | EXP-07 DIAG01 replication seed 404 treatment last state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_RUN001_SEED42/best_model.pt` | 171,939,633 | `FF30EDCFEFBDF3C321F2D531BF3A8031ABB6F8481FC4F89D3DD8E2781ACAD9D7` | EXP-07 RUN001 seed 42 best validation state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_RUN001_SEED42/last_model.pt` | 171,939,697 | `50673001346BD66DABADBEF0DDC1AD1316D4E9459E983BD8E21EEEE5C9761030` | EXP-07 RUN001 seed 42 final epoch state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_RUN002_SEED101/best_model.pt` | 171,939,633 | `D64FE6197B73F47A1B97D2881E273441C61F6562D0B68B4B3C1A9322E6C2190E` | EXP-07 RUN002 seed 101 best validation state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_RUN002_SEED101/last_model.pt` | 171,939,633 | `F3361BC02BD695108B3B449FE21AB7845CE06C7257173DD8DF7056480C7F87B7` | EXP-07 RUN002 seed 101 final epoch state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_RUN003_SEED42/best_model.pt` | 57,355,665 | `936EF935F8049FA15FBC735F8073D08F074796ACC20BE0A2885DD35C7CB09D67` | EXP-07 RUN003 seed 42 best validation state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |
| `experiments/EXP-07/runs/EXP07_RUN003_SEED42/last_model.pt` | 57,355,665 | `60411490EFB81D5DE806F4DFFBA760F5D7F4486B14AB4F144AD35D37EE16FA9E` | EXP-07 RUN003 seed 42 final epoch state | `REGISTERED (GIT_IGNORED_BUT_PRESERVED)` |

### 7.2 Semantic Telemetry and Metrics Classification Rule
Consistent with Section 6.4:
- All lightweight summary metrics (`metrics.json`, `*_metrics.json`), comparison summaries (`comparison_summary.json`), epoch histories (`history.json`), run manifests (`run_manifest.json`), configurations (`*environment.json`), and forensic audit records are **GIT-TRACKED**.
- Dense per-tile prediction payloads (`positive_tiles_forensics.json`), ephemeral unbuffered execution heartbeats (`live_progress.json`), and raw console output logs (`*.txt` console streams) are **PRESERVED ON DISK** outside Git.

