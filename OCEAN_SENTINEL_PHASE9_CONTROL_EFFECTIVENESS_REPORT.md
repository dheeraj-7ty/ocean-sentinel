# OCEAN SENTINEL — PHASE 9 REPORT: CONTROL-EFFECTIVENESS & NEGATIVE FEEDBACK INSTRUMENTATION

**Task ID**: `OCEAN-SENTINEL-PHASE9-CONTROL-EFFECTIVENESS-AND-NEGATIVE-FEEDBACK-INSTRUMENTATION-V1`  
**Phase**: `PHASE 9 / PHASE 9A / PHASE 9B — LEARNING V3 CONTROL-EFFECTIVENESS & NEGATIVE FEEDBACK INSTRUMENTATION`  
**Worker**: AG (Inspection, Implementation, Testing & Forensic Verification)  
**Chief Architecture Officer (CAO)**: ChatGPT (Architecture & Reasoning Authority)  
**Approval Authority**: Human  
**Environment**: Antigravity IDE 2.0 (Windows, CPU-only)  
**Status**: `PHASE 9 / 9A / 9B COMPLETE / FROZEN`  
**Date**: 2026-09-26  

---

## 1. Plain-English Summary

Phase 9 (with Phase 9A and 9B micro-closures) establishes the foundational, lightweight observational instrumentation layer required for Ocean Sentinel's Learning V3 architecture. Prior to this phase, governance preflight could retrieve lessons and evaluate safety rules, but could not distinguish whether a retrieved lesson was actually presented to an operator/UI, whether a rule application was distinct from lesson retrieval, whether active catalog rules differed from task-applicable rules, or whether a blocked execution plan genuinely prevented a mistake in the physical or operational world.

To prevent cognitive leaps and fabricated evidence, the implementation formalizes a 6-stage learning-to-prevention control chain with 4-valued bounded observation semantics (`TRUE`, `FALSE`, `UNKNOWN`, `NOT_APPLICABLE`), implements an in-memory `ControlEffectivenessTracker`, instruments `evaluate_task_preflight()`, and establishes an integrity-checked local receipt persistence mechanism under `outputs/receipts/learning_feedback/`.

Crucially:
- **Phase 9A** decoupled `LESSON_EXISTS` from `LESSON_RETRIEVED`: because the current architecture possesses a retrieval engine but lacks an independent task-relevance existence oracle, `LESSON_EXISTS` is honestly recorded as `UNKNOWN` in preflight rather than inferred from retrieval success or failure.
- **Phase 9B** decoupled active catalog rules from task-applicable rules and task-applicable rules from applied rules: `RULE_APPLIED` enforces a strict 5-case matrix ensuring that active catalog rules are not used as an applicability proxy, and that zero applied rules does not manufacture `NOT_APPLICABLE` when rules were applicable.

No canonical governance catalogs (`rules.json`, `lessons.json`, `incidents.json`) are modified, no autonomous learning or promotion logic is enabled, and telemetry remains strictly observational.

---

## 2. Exact Scope

The scope of Phase 9 / 9A / 9B is strictly bounded to the observational substrate:

1. **Data Model Additions** (`src/ocean_sentinel/governance/models.py`):
   - `NegativeFeedbackCategory` enum (exact 9 canonical failure modes).
   - `ControlStage` enum (exact 6 stages of the control chain).
   - `ControlStageOutcome` enum (`TRUE`, `FALSE`, `UNKNOWN`, `NOT_APPLICABLE`).
   - `ControlTraceRecord` dataclass (serializable, evidence-oriented stage observation).
   - `PreflightV2Result.control_trace` field (additive trace integration).

2. **Control Effectiveness & Feedback Engine** (`src/ocean_sentinel/governance/control.py`):
   - `ControlEffectivenessTracker`: pure in-memory trace builder with overwrite guards, anti-fabrication guards (preventing retrieval from claiming existence proof, preflight from claiming presentation proof, and rule blocks from claiming prevention proof), and deterministic finalization.
   - `resolve_rule_applied_outcome()` and `record_rule_applied()`: deterministic implementation of the 5-case active vs applicable vs applied matrix.
   - `record_negative_feedback()`: integrity-checked local receipt generator persisting atomic JSON receipts under `outputs/receipts/learning_feedback/` with canonical SHA-256 payload verification and fail-closed overwrite protection.
   - Non-authoritative mapping between `NegativeFeedbackCategory` and `ReworkClass`.

3. **Preflight Instrumentation** (`src/ocean_sentinel/governance/interface.py`):
   - `evaluate_task_preflight()` instrumented to populate and finalize a 6-stage control trace in `PreflightV2Result` without mutating existing rule, precedence, or blocking behaviors.

4. **Contract & Adversarial Test Suite** (`tests/test_governance_control_effectiveness.py`):
   - 48 comprehensive unit, integration, semantic guard, anti-fabrication, and adversarial matrix tests.

5. **Baseline Test Count Reconciliation**:
   - Reconciled Phase 8 descriptive sub-counts against the literal 149 collected tests across the five governance test files, documented via a frozen-phase erratum in `OCEAN_SENTINEL_LEARNING_V3_GAP_AUDIT.md`.

---

## 3. Current Observable Control Chain

The six-stage learning-control chain distinguishes the following distinct phenomena:

$$\text{lesson\_exists} \neq \text{lesson\_retrieved} \neq \text{lesson\_applicable} \neq \text{lesson\_presented} \neq \text{rule\_applied} \neq \text{mistake\_prevented}$$

### Bounded Semantic Handling:
- **`LESSON_EXISTS`**:
  - `TRUE`: Relevant lesson independently verified to exist by an authoritative existence oracle.
  - `FALSE`: Authoritative existence oracle confirms no relevant lesson exists.
  - `UNKNOWN`: The current system possesses a retrieval operation but does not have an independent observation proving that a relevant lesson exists separately from whether retrieval returned it. Recorded as `UNKNOWN` in preflight.
- **`LESSON_RETRIEVED`**:
  - `TRUE`: Hybrid retrieval returned one or more relevant lessons for the context.
  - `FALSE`: Retrieval executed and returned zero lessons matching context.
  - `UNKNOWN`: Retrieval stage uninstrumented or skipped.
- **`LESSON_APPLICABLE`**:
  - `TRUE`: Lesson-specific applicability evaluator explicitly confirms lesson applicability.
  - `FALSE`: Lesson-specific applicability evaluator explicitly confirms lesson does not apply.
  - `UNKNOWN`: The current Governance V2 architecture evaluates rule applicability, not lesson applicability; hence preflight records `UNKNOWN`.
- **`LESSON_PRESENTED`**:
  - `TRUE`: Explicit evidence exists that the lesson was displayed in UI/client/operator dialog.
  - `FALSE`: Presentation attempt was made and failed/omitted.
  - `UNKNOWN`: Preflight evaluation occurs inside backend pipeline; presentation is unobserved.
- **`RULE_APPLIED`**:
  - `TRUE`: One or more applicable rules were actually applied by enforcement and contributed to the preflight decision (blocker, warning, or recommendation).
  - `FALSE`: One or more rules were applicable, but none triggered violations against proposed context.
  - `NOT_APPLICABLE`: Zero rules were applicable to the task context (even if active catalog rules > 0).
  - `UNKNOWN`: Applicability or enforcement evaluation is indeterminate or unobserved.
- **`MISTAKE_PREVENTED`**:
  - `TRUE`: Explicit post-action outcome evidence confirms mistake was averted.
  - `FALSE`: Explicit evidence confirms mistake occurred despite governance intervention.
  - `UNKNOWN`: Preflight evaluation occurs prior to execution; outcome evidence is unobserved.

---

## 4. New Data Model

Implemented in `src/ocean_sentinel/governance/models.py`:

```python
class NegativeFeedbackCategory(str, Enum):
    FALSE_BLOCK = "FALSE_BLOCK"
    MISSED_LESSON = "MISSED_LESSON"
    WRONG_APPLICABILITY = "WRONG_APPLICABILITY"
    WRONG_SCOPE = "WRONG_SCOPE"
    WRONG_PRECEDENCE = "WRONG_PRECEDENCE"
    WEAK_ENFORCEMENT = "WEAK_ENFORCEMENT"
    STALE_LESSON = "STALE_LESSON"
    DUPLICATE_LESSON = "DUPLICATE_LESSON"
    CONTRADICTORY_LESSON = "CONTRADICTORY_LESSON"

class ControlStage(str, Enum):
    LESSON_EXISTS = "LESSON_EXISTS"
    LESSON_RETRIEVED = "LESSON_RETRIEVED"
    LESSON_APPLICABLE = "LESSON_APPLICABLE"
    LESSON_PRESENTED = "LESSON_PRESENTED"
    RULE_APPLIED = "RULE_APPLIED"
    MISTAKE_PREVENTED = "MISTAKE_PREVENTED"

class ControlStageOutcome(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"

@dataclass
class ControlTraceRecord:
    stage: ControlStage
    outcome: ControlStageOutcome
    observed_at: str
    reason: str
    entity_refs: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    source: str = "governance_preflight"
    control_trace_id: str = ""
```

---

## 5. Instrumentation Behavior

Inside `evaluate_task_preflight()` (`src/ocean_sentinel/governance/interface.py`):
1. Accepts optional caller-supplied `tracker: Optional[ControlEffectivenessTracker] = None`. If none is supplied, initializes an in-memory tracker with task ID.
2. During hybrid retrieval:
   - If lessons match: records `LESSON_RETRIEVED=TRUE` with matched lesson IDs.
   - If zero lessons match: records `LESSON_RETRIEVED=FALSE`.
3. Records `LESSON_EXISTS=UNKNOWN`: preflight does not possess an independent existence oracle separate from retrieval.
4. Records `LESSON_APPLICABLE=UNKNOWN`: governance applicability engine evaluates rules, not lessons.
5. Records `LESSON_PRESENTED=UNKNOWN`: backend pipeline cannot observe UI presentation without an explicit client event.
6. During enforcement:
   - Employs `active_tracker.record_rule_applied()` which evaluates:
     * If `applicable_rules_count == 0`: records `NOT_APPLICABLE` (regardless of active catalog count).
     * If `applicable_rules_count > 0` and `applied_rule_ids == []`: records `FALSE`.
     * If `applicable_rules_count > 0` and `len(applied_rule_ids) > 0`: records `TRUE` with applied rule IDs.
7. Records `MISTAKE_PREVENTED=UNKNOWN`: task has not yet executed; outcome evidence is unobserved.
8. Calls `tracker.finalize_trace()` which fills any unobserved stages with bounded `UNKNOWN` records and emits a 6-record deterministic trace attached to `PreflightV2Result.control_trace`.

---

## 6. Negative Feedback Receipt Model

Implemented in `src/ocean_sentinel/governance/control.py`:

```
User/Agent records negative feedback
  │
  ├─ Validates category ∈ NegativeFeedbackCategory (exact 9)
  ├─ Coerces payload to canonical JSON structure
  ├─ Computes SHA-256 via canonicalize_json_v1
  ├─ Attaches integrity note: INTEGRITY-CHECKED LOCAL RECEIPT
  │
  ├─ Writes atomically (.tmp file + os.replace) to:
  │    outputs/receipts/learning_feedback/<receipt_id>.json
  │
  └─ If receipt_id already exists:
       ├─ Identical SHA-256: Idempotent return
       └─ Differing SHA-256: FAILS CLOSED (RuntimeError: TAMPER_PROTECTION_ERROR)
```

**Guarantees & Accurately Bounded Semantics**:
- **Conflict Detection**: Detects conflicting overwrites through stored payload digest comparison.
- **Local Integrity**: SHA-256 payload digests provide local payload-integrity checks and conflicting overwrite detection when the recorded digest remains trustworthy.
- **No External Authentication**: Does not establish external identity or use asymmetric keys.
- **No Digital Signatures**: Does not provide cryptographic signatures or non-repudiation.
- **Threat Model Limitation**: Does not guarantee detection if an attacker with local filesystem access maliciously rewrites both the entire receipt file and its stored digest simultaneously.
- **Persistence Boundary Isolation**: Stored exclusively under `outputs/receipts/learning_feedback/`. No file is written to `data/metadata/governance_v2/`.

---

## 7. What the System Explicitly Does NOT Infer

1. **`lesson_exists` is NOT inferred from retrieval**: Preflight retrieval returning a lesson does not prove that an independent relevance oracle confirms its existence; conversely, a retrieval miss does not prove absence. `LESSON_EXISTS` remains `UNKNOWN`.
2. **`lesson_presented` is NOT inferred from retrieval**: Preflight returning a relevant lesson does not prove that an operator or client interface rendered it. Without an explicit presentation event from a UI/client source, `LESSON_PRESENTED` remains `UNKNOWN`.
3. **`mistake_prevented` is NOT inferred from `BLOCK`**: An enforcement engine blocking a task does not prove that the user would have executed a dangerous operation or that a physical error was averted. Without post-action outcome evidence, `MISTAKE_PREVENTED` remains `UNKNOWN`.
4. **`rule_applied` is NOT inferred from active catalog rules**: Active rules existing in the repository catalog does not mean any rule is applicable to the context. `RULE_APPLIED = NOT_APPLICABLE` when context applicability is zero.
5. **`rule_applied` is NOT marked `NOT_APPLICABLE` merely because zero rules triggered**: If rules were applicable but none triggered violations, `RULE_APPLIED = FALSE`.
6. **`negative feedback` is an event receipt, NOT canonical governance**: Receipts document observations and candidate feedback. They do not alter rules, change precedence, promote lessons, or create blocking actions.
7. **`telemetry` is observational only**: Traces and receipts are forensic audit artifacts; they never function as authorization gates or operational switches.
8. **Receipt `SHA-256` provides payload integrity verification and conflict detection, NOT authentication**: Payload hashing detects disk corruption and bitrot; it does not constitute cryptographic digital signatures, external identity verification, or non-repudiation.
9. **No autonomous learning or promotion**: Candidate lessons remain `NON_AUTHORITATIVE_PROPOSED_ONLY`. No automated promotion pipeline exists or was introduced.

---

## 8. Test Results

### New Test Suite (`tests/test_governance_control_effectiveness.py`):
- **Collected**: 48 tests
- **Passed**: 48 tests (100%)
- **Failed**: 0
- **Duration**: 0.30s

Groups Covered:
- Group A: `NegativeFeedbackCategory` (9 categories, uniqueness, serialization, rework mapping)
- Group B: `ControlStage` (6 stages, uniqueness, canonical ordering)
- Group C: `ControlStageOutcome` (4 outcomes, semantic distinctness)
- Group D: `ControlTraceRecord` (creation, dictionary serialization, round-trip)
- Group E: `ControlEffectivenessTracker` (in-memory tracking, overwrite guards, unknown filling, finalization)
- Group F: Critical Semantic Guards (anti-fabrication rules for presentation, prevention, and existence evidence)
- Group G: Preflight Integration (trace population, dictionary inclusion, holdout blocking preservation, existence decoupling)
- Group H: Negative Feedback Receipts (atomic writes, deterministic sha256, conflicting overwrite rejection, complete disclaimers, governance catalog isolation)
- Group I: Adversarial & Boundary Scenarios (retrieval misses, coercion rejections, corrupted file handling, telemetry-authorization isolation)
- Group J: Rule Applicability Matrix (5-case matrix, active vs applicable vs applied decoupling, adversarial counterexamples, trustworthy digest wording)

### Regression Test Suites:
1. **Grouped Governance Suites** (5 files):
   - `tests/test_ocean_sentinel_agent_learning_framework.py`: 12 passed
   - `tests/test_governance_v2_adversarial_replay.py`: 27 passed
   - `tests/test_governance_v2_architecture.py`: 21 passed
   - `tests/test_ocean_sentinel_agent_governance.py`: 27 passed
   - `tests/test_staged_governance_isolation.py`: 62 passed
   - **Total**: **149 passed** in 22.30s (Exit Code: 0, 0 regressions)
2. **Report Reconciliation Suite**:
   - `tests/test_report_reconciliation_learning.py`: **48 passed** in 0.18s (Exit Code: 0, 0 regressions)
3. **AIS Adversarial Suite**:
   - `tests/test_ais_adversarial.py`: **33 passed** in 1.40s (Exit Code: 0, 0 regressions)

**Total Test Suite Execution**: **278 passed, 0 failed, 0 regressions**.

---

## 9. Baseline Count Reconciliation

The Phase 8 report described historical test counts as:
- 65 architecture tests
- 12 adversarial tests
- 40 governance tests
- 52 isolation tests
(summing descriptively to 169).

Literal collection via `pytest --collect-only -q` across the five governance files measured:
- `test_ocean_sentinel_agent_learning_framework.py`: 12
- `test_governance_v2_adversarial_replay.py`: 27
- `test_governance_v2_architecture.py`: 21
- `test_ocean_sentinel_agent_governance.py`: 27
- `test_staged_governance_isolation.py`: 62
- **Sum**: Exactly **149 tests**.

The discrepancy arose because the Phase 8 descriptive text referenced earlier conceptual groupings rather than exact file-level pytest counts. A formal frozen-phase erratum was appended to Section 14 of `OCEAN_SENTINEL_LEARNING_V3_GAP_AUDIT.md`. The true, measured baseline is **149 tests**.

---

## 10. Protected Hash Results

All 7 protected files verified bit-for-bit via SHA-256 against their canonical definitions:

| File Path | Canonical SHA-256 | Measured SHA-256 | Status |
| :--- | :--- | :--- | :--- |
| `.gitignore` | `a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444` | `a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444` | **MATCH** |
| `src/ocean_sentinel/ingestion/dataset.py` | `f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c` | `f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c` | **MATCH** |
| `src/ocean_sentinel/governance/runner.py` | `dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0` | `dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0` | **MATCH** |
| `data/metadata/governance_v2/rules.json` | `b216f369d68a027e4708e8cbcf3991d8effd5ba5a063a3b8b6b3fc2261d85c4e` | `b216f369d68a027e4708e8cbcf3991d8effd5ba5a063a3b8b6b3fc2261d85c4e` | **MATCH** |
| `data/metadata/governance_v2/lessons.json` | `4784a440070bc00612bc3bfa9b29a7acc181934f894a9e22bd340faab7076395` | `4784a440070bc00612bc3bfa9b29a7acc181934f894a9e22bd340faab7076395` | **MATCH** |
| `data/metadata/governance_v2/incidents.json` | `fa3051a185894ee1fe46edb5825ebcfe92b107f80fb7527bf5746d4ec5b91836` | `fa3051a185894ee1fe46edb5825ebcfe92b107f80fb7527bf5746d4ec5b91836` | **MATCH** |
| `src/ocean_sentinel/temporal.py` | `46614361e1be20a278d0af9ceee222e4787df1eade7d52a88b372965170e26cf` | `46614361e1be20a278d0af9ceee222e4787df1eade7d52a88b372965170e26cf` | **MATCH** |

Protected file count: **7/7 MATCH**.

---

## 11. Worktree Status

A rigorous separation between tracked changes and untracked artifacts is maintained:

1. **Tracked Working Tree (`git diff --name-only`)**:
   Contains strictly pre-existing authorized modifications:
   - `.gitignore` (pre-existing authorized modification)
   - `pyproject.toml` (pre-existing authorized modification)
   - `src/ocean_sentinel/ingestion/dataset.py` (pre-existing authorized modification)
2. **Untracked / In-Scope Phase 9/9A/9B Artifacts**:
   Separately enumerated and verified as within the bounded scope:
   - `src/ocean_sentinel/governance/models.py` (model definitions)
   - `src/ocean_sentinel/governance/control.py` (tracker, rule matrix resolver, and receipt engine)
   - `src/ocean_sentinel/governance/interface.py` (preflight instrumentation)
   - `tests/test_governance_control_effectiveness.py` (test suite)
   - `outputs/receipts/learning_feedback/` (receipt storage directory)
   - `OCEAN_SENTINEL_PHASE9_CONTROL_EFFECTIVENESS_REPORT.md` (this report)
   - `OCEAN_SENTINEL_LEARNING_V3_GAP_AUDIT.md` (Section 14 erratum)
   - `scratch/ocean_sentinel_phase9_control_effectiveness_progress.md` (Phase 9 progress)
   - `scratch/ocean_sentinel_phase9a_control_trace_closure_progress.md` (Phase 9A progress)
   - `scratch/ocean_sentinel_phase9b_rule_applicability_progress.md` (Phase 9B progress)
3. **Diff Integrity (`git diff --check`)**:
   Clean (exit code 0; zero whitespace, CRLF corruption, or merge conflict markers).

**Status**: **NO UNAUTHORIZED CHANGES; PRE-EXISTING/AUTHORIZED MODIFICATIONS PRESERVED**. (Not claiming a literally clean worktree).

---

## 12. Limitations

1. **Lack of Independent Existence Oracle**: The repository lacks an independent oracle to evaluate lesson existence separately from retrieval; `LESSON_EXISTS` is thus bounded to `UNKNOWN`.
2. **Rule-Only Applicability Engine**: The current `ApplicabilityEngine` evaluates rules, not lessons. Lesson applicability is therefore marked `UNKNOWN` rather than fabricated.
3. **Backend Presentation Blindness**: Preflight runs headless in python; it cannot directly detect whether a frontend UI component or IDE prompt displayed the retrieved lesson. `LESSON_PRESENTED` defaults to `UNKNOWN` until a UI presentation event is explicitly reported.
4. **Pre-Execution Prevention Blindness**: Preflight runs before execution. Prevention can only be verified after execution outcome evidence is gathered.
5. **Local Single-Node Receipts**: Receipts are stored as local JSON files with SHA-256 payload checksums. They are integrity-checked against local disk alteration and concurrent overwrite when the recorded digest remains trustworthy, but do not provide cryptographic digital signatures or non-repudiation.

---

## 13. Future Measurement Boundary

In accordance with Section 12 of the execution contract, **no quantitative metric engine was implemented in Phase 9, 9A, or 9B**.

The following capabilities are explicitly deferred to the next bounded phase (**Phase 10: Learning V3 Quantitative Effectiveness Metrics & Trace Analytics**):
- Retrieval recall and precision calculation.
- False-block rate metric aggregation across traces.
- Recurrence rate of known failure classes.
- Lesson staleness and citation frequency scoring.
- UI presentation telemetry callback integration.
- Negative feedback receipt ingestion into offline evaluation batches.

---

## 14. Final Certification

Phase 9 implementation, Phase 9A semantic micro-closure, and Phase 9B rule-applicability micro-closure conform strictly to all permanent governance rules and the execution contract. The separation of the 6-stage control chain is verified by 48 tests, the 149-test governance baseline is preserved without regressions, all 7 protected hashes match bit-for-bit, and canonical governance catalogs remain pristine.

**PHASE 9, PHASE 9A, AND PHASE 9B ARE COMPLETE AND FROZEN.**

---

## 15. Phase 9A Micro-Closure Corrections

In response to the CAO review, Phase 9A executed three targeted micro-corrections:

### 1. LESSON_EXISTS vs LESSON_RETRIEVED Semantic Decoupling
- **Issue**: Phase 9 preflight initially set `LESSON_EXISTS` to `TRUE`/`FALSE` based directly on `len(retrieved_lessons) > 0`, conflating retrieval match with an independent ground-truth existence oracle.
- **Root Cause**: Absence of an explicit anti-fabrication guard separating retrieval success from knowledge existence.
- **Correction**: Selected Option 1. Instrumented preflight to record `LESSON_RETRIEVED = TRUE/FALSE` based on actual retrieval, while recording `LESSON_EXISTS = UNKNOWN` with an explicit reason stating that no independent existence oracle exists in the current architecture. Added an anti-fabrication guard in `ControlEffectivenessTracker.record_stage()` that rejects attempts to set `LESSON_EXISTS` based on retrieval sources.
- **Verification**: Verified via `test_lesson_exists_cannot_be_derived_from_retrieval_alone`, `test_retrieval_miss_does_not_imply_lesson_absence`, and preflight integration tests.

### 2. Receipt Integrity Terminology & Scope Calibration
- **Issue**: Initial phrasing of "tamper-evident receipt" risked overstating cryptographic guarantees without clear disclaimers regarding digital signatures and external identity.
- **Root Cause**: Generic hashing terminology without detailed threat-model boundary specification.
- **Correction**: Replaced terminology with `INTEGRITY_CHECKED_NEGATIVE_FEEDBACK_RECEIPT` and `INTEGRITY-CHECKED LOCAL RECEIPT`. Explicitly documented guarantees (local canonical payload integrity, conflicting overwrite detection) and limitations (no digital signatures, no external identity verification, no non-repudiation, and inability to detect an attacker with full filesystem access rewriting both payload and digest).
- **Verification**: Verified via `test_receipt_integrity_disclaimers_complete` and conflicting overwrite fail-closed tests.

### 3. Worktree Forensic Reporting Precision
- **Issue**: The Phase 9 report summary of `git diff --name-only` could be misread as implying it accounted for untracked workspace files.
- **Root Cause**: Conflation of tracked git diffs with untracked artifact enumeration.
- **Correction**: Restructured Section 11 into distinct subsections for Tracked Working Tree (`git diff --name-only`) and Untracked / In-Scope Phase 9/9A Artifacts, preserving the strict declaration: `NO UNAUTHORIZED CHANGES; PRE-EXISTING/AUTHORIZED MODIFICATIONS PRESERVED`.
- **Verification**: Cross-verified against `git diff --name-only` and `git status --short`.

---

## 16. Phase 9B Micro-Closure — Rule Applicability Trace

In response to CAO review, Phase 9B eliminated the semantic conflation between active catalog rules and task-applicable rules, and between applicable rules and applied rules:

### 1. The 5-Case Rule Applicability Matrix
- **Issue**: Potential ambiguity where `RULE_APPLIED = FALSE` could be derived merely from "active rules exist in the catalog but none triggered", or where `RULE_APPLIED = NOT_APPLICABLE` could be derived merely because no rule was applied.
- **Root Cause**: Preflight logic previously checked `len(active_rules) > 0` where `active_rules` was the variable name returned by `PrecedenceEngine.resolve_rules()`, creating linguistic ambiguity with "active catalog rules" in `store.list_rules()`.
- **Correction**: Implemented `resolve_rule_applied_outcome()` and `ControlEffectivenessTracker.record_rule_applied()` in `src/ocean_sentinel/governance/control.py`. Preflight now explicitly evaluates:
  * **Case 1**: active=0, applicable=0, applied=0 => `NOT_APPLICABLE`
  * **Case 2**: active>0, applicable=0, applied=0 => `NOT_APPLICABLE` (Adversarial counterexample 1: active catalog rules count is NOT an applicability proxy!)
  * **Case 3**: active>=0, applicable>0, applied=0 => `FALSE` (Adversarial counterexample 2: zero applied rules does NOT produce `NOT_APPLICABLE` when rules were applicable!)
  * **Case 4**: applicable>0, applied>0 => `TRUE` (at least one applicable rule contributed to decision)
  * **Case 5**: indeterminate applicability/enforcement => `UNKNOWN`
- **Explicit Active vs Applicable Distinction**:
  * *Active Catalog Rules*: Rules present in the catalog that are enabled/unarchived (`store.list_rules()`).
  * *Applicable Rules*: Rules explicitly determined by `ApplicabilityEngine.evaluate_rule()` to be relevant to the specific proposed `TaskContext`.
- **Explicit Applicable vs Applied Distinction**:
  * *Applicable Rules*: Rules whose scope/triggers encompass the task context.
  * *Applied Rules*: Applicable rules that were actually evaluated by `EnforcementEngine.evaluate_task()` resulting in emitted findings (blockers, warnings, recommendations).
- **Verification**: Verified via 8 new dedicated contract and adversarial tests in `TestRuleApplicabilityMatrix`, confirming that Case 2 strictly produces `NOT_APPLICABLE` and Case 3 strictly produces `FALSE`.

### 2. Receipt Integrity Wording Precision
- **Correction**: Reconciled the receipt integrity note to include the qualification: `"when the recorded digest remains trustworthy"`.
- **Verification**: Verified via `test_receipt_integrity_wording_contains_trustworthy_qualification`.
