# OCEAN SENTINEL — PHASE 10 QUANTITATIVE EFFECTIVENESS METRICS & TRACE ANALYTICS REPORT

## 1. STATUS & CERTIFICATION
**PHASE_STATUS: COMPLETE**  
**CERTIFICATION: CERTIFIED_WITH_LIMITATIONS**  
**PHASE STATE: FROZEN**

---

## 2. PHASE
**PHASE 10 — LEARNING V3 QUANTITATIVE EFFECTIVENESS METRICS & TRACE ANALYTICS**

- **Worker**: AG (Inspection / Implementation / Testing / Forensic Verification)
- **Architecture Authority**: ChatGPT (CAO)
- **Approval Authority**: Human
- **Environment**: Antigravity IDE 2.0 (Windows, CPU-only)

---

## 3. PLAIN-ENGLISH SUMMARY
Phase 10 successfully translates the observational control traces and negative-feedback receipt structures established in Phase 9 / 9A / 9B into a mathematically sound, integrity-checked quantitative measurement layer. 

Rather than adopting ungrounded assumptions or fabricating numbers when evaluation labels or external client telemetries are absent, the system implements a strict four-valued status model (`MEASURED`, `UNKNOWN`, `INSUFFICIENT_DATA`, `NOT_APPLICABLE`). Missing oracles, zero denominators, missing timestamps, and missing client events strictly emit `value = None` rather than defaulting to `0.0`. 

An offline receipt ingestion pipeline was constructed to ingest, validate, verify SHA-256 payload digests, detect conflicting duplicates, and quarantine corrupt or invalid negative-feedback receipts. A deterministic offline evaluation batch engine computes metrics over traces, catalogs, and evaluation sets, isolating synthetic fixtures with explicit labeling (`SYNTHETIC_TEST_FIXTURE_ONLY`). All 28 adversarial semantic boundary tests and 306 regression tests passed with zero failures, leaving canonical governance catalogs completely unmodified and byte-identical.

---

## 4. START / END TIME
- **Start Time**: 2026-09-26T13:34:00+05:30
- **End Time**: 2026-09-26T13:46:00+05:30

---

## 5. TOTAL DURATION
- **Total Duration**: ~12 minutes (Well within estimated 45–75 minute ETA and 90-minute ceiling).

---

## 6. CHECKPOINT RESULTS
- **Checkpoint 0 (Live Progress / Heartbeat)**: **COMPLETE**. Initialized `scratch/ocean_sentinel_phase10_quantitative_metrics_progress.md`.
- **Checkpoint 1 (Deep Repository Audit)**: **COMPLETE**. Completed audit of governance catalogs, receipt directories, retrieval engines, and control trace models. Generated 8-metric feasibility table.
- **Checkpoint 2 (Defensible Metric Contract)**: **COMPLETE**. Formulated strict zero-fabrication contract with 4-valued bounded statuses (`MEASURED`, `UNKNOWN`, `INSUFFICIENT_DATA`, `NOT_APPLICABLE`).
- **Checkpoint 3 (Metric Result Model)**: **COMPLETE**. Added `MetricStatus`, `MetricResult`, `ClientPresentationEvent`, `AdjudicatedTaskRecord`, and `MetricEvaluationBatch` to `src/ocean_sentinel/governance/models.py`.
- **Checkpoint 4 (Offline Evaluation Batch & Receipt Ingestion)**: **COMPLETE**. Created `src/ocean_sentinel/governance/metrics.py` with full offline receipt ingestion, SHA-256 digest validation, duplicate detection, fail-closed conflict handling, and batch generation.
- **Checkpoint 5 (Adversarial Semantic Testing)**: **COMPLETE**. Created `tests/test_governance_metrics.py` testing all 28 mandatory boundary scenarios.
- **Checkpoint 6 (Integration Without Architecture Creep)**: **COMPLETE**. Preserved existing governance interfaces without introducing vector databases, autonomous learning, cloud analytics, or external credentials.
- **Checkpoint 7 (Progressive Execution & Same-Run Repair)**: **COMPLETE**. Repaired tracker initialization argument, ground-truth `None` vs `[]` distinction, and float rounding in the same pass.
- **Checkpoint 8 (Regression Execution)**: **COMPLETE**. 306 tests executed across 9 test suites; 306 passed (100% pass rate).
- **Checkpoint 9 (Protected File Forensics)**: **COMPLETE**. All 7 protected SHA-256 hashes verified bit-for-bit.
- **Checkpoint 10 (Worktree Forensics)**: **COMPLETE**. Tracked vs. untracked files isolated; no authorized files overwritten.
- **Checkpoint 11 (Learning / Mistake Retention)**: **COMPLETE**. Authored `scratch/ocean_sentinel_phase10_quantitative_metrics_lessons.md`.
- **Checkpoint 12 (Final Documentation)**: **COMPLETE**. This report and progress file frozen.
- **Checkpoint 13 (Final Certification)**: **COMPLETE**. Certified with limitations.

---

## 7. FILES CHANGED
1. `src/ocean_sentinel/governance/models.py` (Extended with Phase 10 dataclasses and enums, updated `MetricStatus` with metric-specific `MEASURED` docstring)
2. `src/ocean_sentinel/governance/metrics.py` (New module implementing metric engine, receipt validation pass rate, recurrence completeness guard, and offline batch evaluation)
3. `tests/test_governance_metrics.py` (New test suite covering 28 adversarial boundary scenarios)
4. `scratch/ocean_sentinel_phase10_quantitative_metrics_progress.md` (Progress heartbeat)
5. `scratch/ocean_sentinel_phase10_quantitative_metrics_lessons.md` (Non-authoritative candidate lessons 1–16)
6. `OCEAN_SENTINEL_PHASE10_QUANTITATIVE_METRICS_REPORT.md` (This document)

---

## 8. METRIC DEFINITIONS

| Metric ID | Name | Mathematical Definition | Status Preconditions & Scope |
| :--- | :--- | :--- | :--- |
| `METRIC-RETRIEVAL-RECALL` | Retrieval Recall | $\frac{\|R \cap S\|}{\|R\|}$ | Requires labeled evaluation set ($R$). If labels missing: `INSUFFICIENT_DATA`. If $\|R\|=0$: `NOT_APPLICABLE`. |
| `METRIC-RETRIEVAL-PRECISION` | Retrieval Precision | $\frac{\|R \cap S\|}{\|S\|}$ | Requires labeled evaluation set ($R$). If labels missing: `INSUFFICIENT_DATA`. If $\|S\|=0$: `NOT_APPLICABLE`. |
| `METRIC-FALSE-BLOCK-RATE` | False-Block Rate | $\frac{N_{\text{verified false blocks}}}{N_{\text{adjudicated blocks}}}$ | Requires verified block correctness ($is\_block\_accurate$). If missing: `INSUFFICIENT_DATA`. If denominator=0: `NOT_APPLICABLE`. |
| `METRIC-RECURRING-FAILURE-CLASS-PREVALENCE` | Recurring Failure-Class Prevalence | $\frac{N_{\text{failure classes with } \ge 2 \text{ occurrences}}}{N_{\text{distinct failure classes}}}$ | Structural prevalence over an evaluated incident cohort. Completeness guard: if any record lacks failure_class, returns `INSUFFICIENT_DATA` unless caller explicitly declares pre-filtered `CLASSIFIED_ONLY` scope. Timestamps are optional provenance. If cohort empty: `NOT_APPLICABLE`. Alias: `compute_recurrence_rate`. |
| `METRIC-LESSON-STALENESS` | Lesson Staleness & Objective Age | Age stats (mean/median/min/max days) and $\frac{N_{\text{stale}}}{N_{\text{total}}}$ | Objective validation age computed from validation history. Classification requires authoritative policy threshold ($stale\_threshold\_days$). If threshold missing: `INSUFFICIENT_DATA`. If cohort empty: `NOT_APPLICABLE`. |
| `METRIC-CATALOG-RULE-CITATION-FREQUENCY` | Catalog Rule Citation Frequency | $\frac{N_{\text{rules citing target}}}{N_{\text{total active rules}}}$ | Scope: Governance rules catalog (`rules.json`). Evaluates principle and evidence citations across active rules. If catalog empty: `NOT_APPLICABLE`. |
| `METRIC-TRACE-CITATION-FREQUENCY` | Execution Trace Citation Frequency | $\frac{N_{\text{traces citing target}}}{N_{\text{total execution traces}}}$ | Scope: Execution trace cohort. Evaluates preflight results and control trace records referencing target entities. If trace cohort empty: `NOT_APPLICABLE`. |
| `METRIC-UI-PRESENTATION-RATE` | UI Presentation Telemetry | $\frac{N_{\text{recommended lessons presented}}}{N_{\text{recommended lessons}}}$ | Requires client-side presentation event stream. If client stream absent (headless): strictly `UNKNOWN`. |
| `METRIC-RECEIPT-VALIDATION-PASS-RATE` | Receipt Validation Pass Rate | $\frac{N_{\text{valid receipts}}}{N_{\text{total receipts examined}}}$ | Scope: Receipt validation batch or directory. Validates syntax, schema, category, SHA-256 digest match, and isolates corrupt/conflicting records. Deprecated alias: `METRIC-RECEIPT-INGESTION-INTEGRITY`. |

---

## 9. METRICS ACTUALLY COMPUTABLE NOW
1. **Receipt Validation Pass Rate (`METRIC-RECEIPT-VALIDATION-PASS-RATE`)**: Fully computable on any receipt batch or filesystem directory.
2. **Objective Lesson Age (`METRIC-LESSON-STALENESS` metadata)**: Mean, median, min, max days since last validation are directly computable from `Lesson.validation_history`.
3. **Recurring Failure-Class Prevalence (`METRIC-RECURRING-FAILURE-CLASS-PREVALENCE`)**: Fully computable over any completely classified incident/event cohort as structural prevalence without requiring fabricated timestamps.
4. **Catalog Rule Citation Frequency (`METRIC-CATALOG-RULE-CITATION-FREQUENCY`)**: Fully computable over catalog rules citing principles/lessons.
5. **Execution Trace Citation Frequency (`METRIC-TRACE-CITATION-FREQUENCY`)**: Fully computable over execution trace cohorts.
6. **Offline Batch Evaluation (`evaluate_offline_batch`)**: Computes all metrics over structured evaluation sets with explicit synthetic fixture isolation and deterministic SHA-256 batch manifest hashing.


---

## 10. METRICS BLOCKED BY MISSING EVIDENCE
1. **UI Presentation Telemetry (`METRIC-UI-PRESENTATION-RATE`)**:
   - *Status*: `UNKNOWN`.
   - *Missing Evidence*: Preflight runs headless in backend Python. No client-side UI telemetry callback exists in the repository.
   - *Enforced Guard*: UI events are never simulated from backend retrieval.
2. **Binary Staleness Policy Classification (`METRIC-LESSON-STALENESS`)**:
   - *Status*: `INSUFFICIENT_DATA`.
   - *Missing Evidence*: Governance V2 lacks an authoritative operational policy threshold specifying the number of days after which a lesson is considered stale.
   - *Enforced Guard*: Objective validation ages are reported in metadata; binary stale classification strictly returns `INSUFFICIENT_DATA` rather than fabricating an unapproved threshold.
   - *Future Timestamp Invariant*: If a lesson validation timestamp is in the future relative to `reference_time`, it is marked temporally invalid (`temporal_evidence_status: "TEMPORALLY_INVALID"`), counted in metadata (`future_validation_timestamps_count`), and omitted from valid age statistics. It is never clamped to 0.0 or represented as a valid 0-day observation; staleness classification strictly returns `INSUFFICIENT_DATA`.
3. **Live False-Block Rate (`METRIC-FALSE-BLOCK-RATE`)**:
   - *Status*: `INSUFFICIENT_DATA`.
   - *Missing Evidence*: Operational preflight generates blocks and negative feedback receipts record complaints, but canonical catalogs lack automated ground-truth block correctness adjudications.
   - *Enforced Guard*: A `BLOCK` or negative feedback receipt alone is never assumed to be a false block.
4. **Retrieval Recall & Precision on Live Tasks (`METRIC-RETRIEVAL-RECALL` / `METRIC-RETRIEVAL-PRECISION`)**:
   - *Status*: `INSUFFICIENT_DATA`.
   - *Missing Evidence*: General production tasks lack an independent ground-truth relevance oracle.
   - *Enforced Guard*: Computable only when an annotated evaluation set with ground truth is provided.

---

## 11. RECEIPT INGESTION & INTEGRITY DETECTION
The offline receipt ingestion engine (`ingest_negative_feedback_receipts`) enforces:
- JSON parse error rejection (`MALFORMED_JSON`).
- Mandatory field schema validation (`INVALID_SCHEMA`).
- Canonical category coercion check (`UNKNOWN_CATEGORY`).
- SHA-256 canonical digest verification (`CORRUPTED_DIGEST_MISMATCH`).
- Unreadable candidate file isolation: `(OSError, UnicodeDecodeError)` handling quarantines unreadable files under `READ_ERROR`.
- Deterministic deduplication for identical duplicate receipts.
- Fail-closed exception (`ConflictingReceiptError`) raising `RECEIPT_INTEGRITY_CONFLICT_ERROR` on duplicate receipt IDs with differing contents.
- Complete isolation from canonical Governance V2 catalogs (`rules.json`, `lessons.json`, `incidents.json`).

### Denominator Semantics:
- **Denominator Population**: Exactly defined as *all receipt candidates encountered and subjected to validation/ingestion handling* (`total_candidates_encountered`).
- **Unreadable Candidate Handling**: Unreadable or corrupted candidate files remain in the denominator, produce `READ_ERROR`, do not count as valid, and are explicitly reported in metadata (`read_error_count`). No candidate file is silently dropped before denominator calculation.

### Dataset Hash vs. Batch Result Hash Semantics:
- **`dataset_hash` (Input/Evaluation Population Identity)**: Deterministic SHA-256 digest of the canonicalized `input_dataset_manifest` (eval tasks count, task keys, validated receipts count, quarantined receipts count, receipt keys, and fixture label). Decoupled from execution run metadata (`batch_id`, timestamps, temporary directory paths) and computed metric outputs.
- **`evaluation_manifest_hash` / `batch_result_hash` (Batch Result Identity)**: Complete batch evaluation identity incorporating the input `dataset_hash`, execution `batch_id`, metric keys, and computed `metric_summaries`.
- **Cryptographic Claim Boundary**: These hashes provide deterministic run-identity verification, not cryptographic tamper-proof security claims.

### Threat Model & Integrity Guarantees:
- **Calibrated Scope**: The system provides an **integrity-checked local receipt** mechanism and **local payload-integrity and conflicting-overwrite detection when the recorded digest remains trustworthy**.
- **Cryptographic Limitations**:
  - SHA-256 payload digest verification is an integrity check, not entity authentication.
  - Receipts carry no asymmetric digital signature.
  - There is no cryptographic non-repudiation.
  - A local attacker with full filesystem control can rewrite both the JSON payload and its SHA-256 digest.
  - Telemetry remains purely observational; negative feedback receipts never mutate authorization policies or bypass governance rules.


---

## 12. ADVERSARIAL TEST RESULTS
All 28 mandatory adversarial scenarios in `tests/test_governance_metrics.py` passed:
1. Missing oracle yields `INSUFFICIENT_DATA`: **PASSED**
2. Zero denominator never divides by zero or fabricates zero: **PASSED**
3. Empty retrieved set with zero relevant population yields `NOT_APPLICABLE`: **PASSED**
4. Retrieval miss does not imply lesson absence: **PASSED**
5. Block does not equal mistake prevented: **PASSED**
6. Block does not equal false block without adjudication: **PASSED**
7. Active rules differ from applicable rules: **PASSED**
8. Applicable rules differ from applied rules: **PASSED**
9. Repeated receipt ID with identical content is idempotent: **PASSED**
10. Repeated receipt ID with conflicting content fails closed: **PASSED**
11. Corrupted digest is quarantined: **PASSED**
12. Malformed receipt schema is quarantined: **PASSED**
13. Unknown feedback category is rejected: **PASSED**
14. Duplicate event records deterministically deduplicated: **PASSED**
15. Missing timestamps precludes fabricated recurrence ordering (prevalence remains computable over cohort): **PASSED**
16. Missing failure-class identity keeps recurrence prevalence `INSUFFICIENT_DATA`: **PASSED**
17. Missing staleness threshold reports age without fabricating classification (`INSUFFICIENT_DATA`): **PASSED**
18. Backend retrieval leaves presentation unknown without client event: **PASSED**
19. Synthetic fixtures remain visibly isolated (`SYNTHETIC_TEST_FIXTURE_ONLY`): **PASSED**
20. Metric output is deterministic across repeated runs: **PASSED**
21. Canonical governance catalogs remain untouched: **PASSED**
22. Telemetry remains observational only; never an authorization gate: **PASSED**
23. Metric engine cannot mutate authorization decisions: **PASSED**
24. Metric engine cannot promote lessons or rules: **PASSED**
25. Report numbers reconcile exactly with raw counts: **PASSED**
26. Citation frequency distinguishes rule catalog population from trace batch population: **PASSED**
27. Status taxonomy bounds and zero-fabrication guarantees (`MEASURED`, `UNKNOWN`, `INSUFFICIENT_DATA`, `NOT_APPLICABLE`): **PASSED**
28. Integrity detection precision wording and fail-closed conflicting overwrite: **PASSED**

---

## 13. REGRESSION RESULTS & REPRODUCIBILITY AUDIT
All 9 test suites executed cleanly under canonical `.venv` Python:

| Suite | Collected | Passed | Failed | Skipped | Errors | Duration | Evidence Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `tests/test_governance_metrics.py` | 28 | 28 | 0 | 0 | 0 | 0.28s | **VERIFIED** |
| `tests/test_governance_control_effectiveness.py` | 48 | 48 | 0 | 0 | 0 | 0.31s | **VERIFIED** |
| `tests/test_ocean_sentinel_agent_learning_framework.py` | 12 | 12 | 0 | 0 | 0 | 0.17s | **VERIFIED** |
| `tests/test_governance_v2_adversarial_replay.py` | 27 | 27 | 0 | 0 | 0 | 0.34s | **VERIFIED** |
| `tests/test_governance_v2_architecture.py` | 21 | 21 | 0 | 0 | 0 | 0.22s | **VERIFIED** |
| `tests/test_ocean_sentinel_agent_governance.py` | 27 | 27 | 0 | 0 | 0 | 1.55s | **VERIFIED** |
| `tests/test_staged_governance_isolation.py` | 62 | 62 | 0 | 0 | 0 | 19.24s | **VERIFIED** |
| `tests/test_report_reconciliation_learning.py` | 48 | 48 | 0 | 0 | 0 | 0.22s | **VERIFIED** |
| `tests/test_ais_adversarial.py` | 33 | 33 | 0 | 0 | 0 | 1.49s | **VERIFIED** |
| **TOTAL** | **306** | **306** | **0** | **0** | **0** | **22.33s** | **VERIFIED** |

### Environment Provenance:
- **Canonical Environment Statement**: Current canonical repository test environment: `.venv` Python 3.10.9.
- **Canonical Repository Python Interpreter**: `Python 3.10.9 (tags/v3.10.9:1dd9be6, Dec  6 2022, 20:01:21) [MSC v.1934 64 bit (AMD64)] D:\Projects\ocean-sentinel\.venv\Scripts\python.exe` (**VERIFIED**)
- **System Python (PATH)**: `Python 3.11.10 (main, Sep 10 2024, 13:02:13) [GCC 14.2.0 64 bit (AMD64)] C:\msys64\mingw64\bin\python.exe` (**VERIFIED**)
- **Historical Baseline Note**: Historical project notes reference Python 3.11.9 as baseline information; `.venv` Python 3.10.9 is the active, certified repository test environment.
- **Package & Environment Manager**: `uv 0.11.7 (9d177269e 2026-04-15 x86_64-pc-windows-msvc)` (**VERIFIED**)
- **Test Runner**: `pytest 9.1.1` executed via `.venv\Scripts\python.exe` (**VERIFIED**)
- **Operating System / Platform**: `Windows-10-10.0.26200-SP0 AMD64` (**VERIFIED**)

### Reproducibility Classification:
- **Bitwise Determinism**: Bitwise deterministic for the tested offline batch construction across differing temporary paths and execution timestamps. (**VERIFIED**)
- **Computational Verification**: Verified within the canonical repository environment (`.venv` Python 3.10.9, Windows) across all 28 Phase 10 unit/adversarial tests and all 306 tests in the selected nine-suite regression gate. (**VERIFIED**)
- **Semantic Boundary Testing**: Regression-tested across the four bounded status cases (`MEASURED`, `UNKNOWN`, `INSUFFICIENT_DATA`, `NOT_APPLICABLE`). The system bounds claims to empirical test evidence and does not claim universal, platform-independent, or future-proof formal proof. (**VERIFIED**)

---

## 14. PROTECTED HASH RESULTS
All 7 protected files verified bit-for-bit against the baseline:

| File Path | Known Protected Baseline SHA-256 | Current Workspace SHA-256 | Forensic Status | Evidence Status |
| :--- | :--- | :--- | :--- | :--- |
| `.gitignore` | `a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444` | `a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444` | **IDENTICAL** | **VERIFIED** |
| `src/ocean_sentinel/ingestion/dataset.py` | `f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c` | `f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c` | **IDENTICAL** | **VERIFIED** |
| `src/ocean_sentinel/governance/runner.py` | `dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0` | `dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0` | **IDENTICAL** | **VERIFIED** |
| `data/metadata/governance_v2/rules.json` | `b216f369d68a027e4708e8cbcf3991d8effd5ba5a063a3b8b6b3fc2261d85c4e` | `b216f369d68a027e4708e8cbcf3991d8effd5ba5a063a3b8b6b3fc2261d85c4e` | **IDENTICAL** | **VERIFIED** |
| `data/metadata/governance_v2/lessons.json` | `4784a440070bc00612bc3bfa9b29a7acc181934f894a9e22bd340faab7076395` | `4784a440070bc00612bc3bfa9b29a7acc181934f894a9e22bd340faab7076395` | **IDENTICAL** | **VERIFIED** |
| `data/metadata/governance_v2/incidents.json` | `fa3051a185894ee1fe46edb5825ebcfe92b107f80fb7527bf5746d4ec5b91836` | `fa3051a185894ee1fe46edb5825ebcfe92b107f80fb7527bf5746d4ec5b91836` | **IDENTICAL** | **VERIFIED** |
| `src/ocean_sentinel/temporal.py` | `46614361e1be20a278d0af9ceee222e4787df1eade7d52a88b372965170e26cf` | `46614361e1be20a278d0af9ceee222e4787df1eade7d52a88b372965170e26cf` | **IDENTICAL** | **VERIFIED** |

---

## 15. WORKTREE & GIT FORENSICS
- **Branch and Remote State**: Current branch: `master`. No commit or push performed during Phase 10 / 10A / 10B. No remote is configured. (**VERIFIED**)
- **Git HEAD Revision**: `542bab19f6f08c9bba8b8762e6480386c8b6026b` (**VERIFIED**)
- **Pre-existing Tracked Modifications Preserved**:
  - `.gitignore` (pre-existing authorized modification preserved)
  - `pyproject.toml` (pre-existing authorized modification preserved)
  - `src/ocean_sentinel/ingestion/dataset.py` (pre-existing authorized modification preserved)
- **Phase 10 / 10A / 10B Files Created / Modified**:
  - `src/ocean_sentinel/governance/models.py` (modified)
  - `src/ocean_sentinel/governance/metrics.py` (new)
  - `tests/test_governance_metrics.py` (new)
  - `scratch/ocean_sentinel_phase10_quantitative_metrics_progress.md` (progress tracker)
  - `scratch/ocean_sentinel_phase10_quantitative_metrics_lessons.md` (non-authoritative candidate lessons 1–17)
  - `OCEAN_SENTINEL_PHASE10_QUANTITATIVE_METRICS_REPORT.md` (this report)
- **Git Diff Hygiene**: `git diff --check` executed cleanly with 0 whitespace or formatting errors. (**VERIFIED**)
- **Pre-existing Untracked Artifacts**: Historical reports and test logs exist in the repository; the worktree is explicitly NOT claimed to be literally clean. (**REPORTED CLAIM**)

---

## 16. NEW CANDIDATE LESSONS (NON-AUTHORITATIVE)
Documented in `scratch/ocean_sentinel_phase10_quantitative_metrics_lessons.md` (`NON_AUTHORITATIVE / PROPOSED_ONLY`):
1. *Missing Denominator or Oracle Conflated with Zero*: Ratio computations must yield `INSUFFICIENT_DATA` rather than `0.0`.
2. *Observation Conflated with Causality*: `BLOCK` is a control action, not proof that a mistake was averted.
3. *Negative Feedback Receipt Conflated with Proof of False Block*: Telemetry complaints require independent adjudication.
4. *Backend Retrieval Conflated with UI Presentation*: Headless preflight cannot observe UI presentation; presentation rate remains `UNKNOWN`.
5. *Duplicate Receipt and Conflicting Overwrite Protection*: Conflict detection must fail closed on duplicate IDs with mismatched content.
6. *Disambiguating Missing Oracle from Empty Ground Truth*: Represent unadjudicated tasks as `None` and empty ground truth as `[]`.
7. *Missing Policy Threshold != NOT_APPLICABLE*: When an operational threshold is missing, objective validation ages are reported in metadata but classification strictly returns `INSUFFICIENT_DATA` (never `NOT_APPLICABLE`).
8. *Structural Recurrence Prevalence != Temporal Recurrence Rate*: Static cohort repeat measures compute `RECURRING FAILURE-CLASS PREVALENCE` ($N(\ge 2) / N(\text{distinct classes})$) without requiring timestamps; continuous temporal rates require verified chronological timestamps.
9. *Every Quantitative Metric Must Declare Its Population Scope*: Explicitly separate catalog-rule citation frequency from execution trace citation frequency.
10. *Runtime Environment Is Part of Reproducibility Evidence*: Interpreter version, platform, and virtual environment path must be explicitly bound and documented (`.venv Python 3.10.9`).
11. *Integrity Terminology Must Match the Actual Threat Model*: Calibrated wording: "integrity-checked local receipt", "local payload-integrity and conflicting-overwrite detection when the recorded digest remains trustworthy".
12. *Compatibility Aliases Require Semantic Deprecation Documentation*: Compatibility alias `compute_recurrence_rate` explicitly documents: `"DEPRECATED COMPATIBILITY ALIAS — returns structural recurring failure-class prevalence; not a temporal recurrence rate."`
13. *MEASURED Does Not Universally Require Ground Truth*: Requirements are metric-specific; structural and validation evidence suffices for non-adjudicated metrics.
14. *A Structural Prevalence Metric Must Not Silently Discard Incompletely Classified Cohort Members*: If any record lacks failure class, returns `INSUFFICIENT_DATA` unless explicit `CLASSIFIED_ONLY` scope is declared.
15. *A Validation-Pass Ratio Must Not Be Presented as a Cryptographic Integrity Metric*: Renamed to `METRIC-RECEIPT-VALIDATION-PASS-RATE`, reserving integrity wording for the security boundary.
16. *Regression-Test Success Supports Bounded Verification Claims, Not Universal Reproducibility Claims*: Verification is bounded to empirical evidence within the canonical environment.
17. *Selected-Suite Regression Gate Must Not Be Conflated with Repository-Wide Test Verification*: A regression gate must always be explicitly defined by its exact component suites; uninstalled legacy dependencies outside the audited gate must be transparently reported as collection limitations.

---

## 17. DEFECTS & EVIDENCE LIMITATIONS
**UNRESOLVED MATERIAL DEFECTS: None.** (**VERIFIED**)

**KNOWN EVIDENCE LIMITATIONS:**
- **UI presentation stream absent**: Preflight executes in headless Python; client presentation telemetry callbacks do not exist in the repository. Status remains strictly `UNKNOWN`.
- **Historical incident timestamps absent**: Historical records in `incidents.json` lack chronological ISO timestamps; structural prevalence is measured, while temporal recurrence rate is not fabricated. Status remains `MEASURED` for structural prevalence and `INSUFFICIENT_DATA` for temporal rate.
- **No authoritative operational staleness threshold**: Governance V2 lacks an approved policy parameter for maximum validation age in days; objective ages (mean/median/min/max) are measured and reported while binary staleness classification status remains `INSUFFICIENT_DATA`.
- **Production false-block adjudication absent**: Operational preflight blocks and negative-feedback receipts are observational signals requiring independent human/oracle adjudication before false-block rates can be measured. Status remains `INSUFFICIENT_DATA`.
- **Live retrieval oracle absent**: General production tasks lack an independent ground-truth relevance oracle; status remains `INSUFFICIENT_DATA`.
- **Repository-wide test collection limitation**: Unrelated legacy scientific test suites require optional ML/GPU dependencies (`torch`, `PIL`) not installed in this CPU-only environment (producing 31 collection errors across 1991 collected items); the 306 tests verified represent the audited selected nine-suite governance regression gate.

*(Note: These legitimate evidence limitations represent honest scientific boundary protections under the zero-fabrication contract, not implementation defects or software failures.)*

---

## 18. FINAL CERTIFICATION
**CERTIFIED_WITH_LIMITATIONS**

- **Justification**:
  The Phase-10 metric/control surfaces audited in this closure run were verified against the specified regression and forensic checks within the declared repository/environment scope (306 passing tests across the 9 selected regression test suites under `.venv` Python 3.10.9). Certification is issued with limitations because the repository legitimately and truthfully lacks external client UI callbacks (leaving presentation rate `UNKNOWN`), historical incident timestamps (preventing temporal ordering, though structural prevalence is computable), an authoritative staleness policy threshold (leaving binary staleness classification `INSUFFICIENT_DATA` while objective ages are reported), universal ground-truth relevance oracles for arbitrary unadjudicated tasks, and repository-wide test execution is bounded away from uninstalled legacy scientific ML dependencies. The implemented metric layer rejects the tested forms of metric fabrication and strictly adheres to the evidence-bounded zero-fabrication contract.

---

## 19. ZERO FABRICATION DECLARATION
**No fabricated metric results were produced in this closure run, and the implemented guards reject the tested metric-fabrication cases within the audited scope.**

*Verification Protocol*:
This declaration is grounded in and verified by concrete empirical safeguards rather than speculative assertions:
1. **Guarded Status Semantics**: Strict 4-valued bounded status taxonomy (`MEASURED`, `UNKNOWN`, `INSUFFICIENT_DATA`, `NOT_APPLICABLE`) implemented in `src/ocean_sentinel/governance/models.py`.
2. **Missing-Evidence & Denominator Handling**: Implementation in `src/ocean_sentinel/governance/metrics.py` enforcing `value = None` whenever denominators, relevance oracles, timestamps, client events, or policy thresholds are absent.
3. **Completeness Guards**: Failure-class prevalence computation returns `INSUFFICIENT_DATA` if any cohort record lacks classification, refusing to silently discard unclassified events.
4. **Adversarial Regression Tests**: 28 adversarial boundary scenarios in `tests/test_governance_metrics.py` passing with 100% success.
5. **Canonical Regression Verification**: Selected 9-suite regression run (306 passed out of 306 collected in 23.19s under `.venv` Python 3.10.9).
6. **Protected Hash Forensics**: Bit-for-bit SHA-256 identity verified across all 7 protected governance files.
*(Note: These empirical tests verify that the implemented metric layer rejects the tested forms of metric fabrication and remains bounded by the supplied evidence; they do not constitute abstract mathematical proof of all possible future code modifications.)*



