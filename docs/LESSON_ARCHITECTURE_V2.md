# Ocean Sentinel Lesson Architecture v2
## Production-Grade Institutional Learning & Operational Memory Specification

**Document Version:** 2.0.0  
**Effective Date:** 2026-09-17  
**Authoritative Machine Metadata:** `data/metadata/governance_v2/`  
**Engine Implementation:** `src/ocean_sentinel/governance/`  
**Preflight Entrypoint:** `scripts/agent_governance_preflight.py --v2`  
**Standard:** Level 5 Machine-Verifiable Operational Governance + Lesson Architecture v2  

---

## 1. Executive Purpose & Motivation

In previous iterations of the Ocean Sentinel research lifecycle, institutional knowledge was stored primarily as narrative prose records in large JSON registries (`ocean_sentinel_lessons_learned_v1.json`). While comprehensive, this flat representation created structural limitations:
1. **Monolithic Overload:** Agents had to manually review 100+ lessons without fine-grained structured applicability filters.
2. **Entity Conflation:** Principles, failure classes, historical incidents, actionable rules, and verification tests were collapsed into a single dictionary record.
3. **Implicit Assumptions:** Safety-critical assumptions (e.g., support evaluated after validity masking, model running in `eval` mode, statistical method explicitly bound) were silently presumed rather than explicitly tracked.
4. **Precedence Ambiguity:** When rules conflicted, the system lacked a deterministic precedence policy (severity vs scope specificity).

**Lesson Architecture v2** upgrades repository governance into an active, multi-entity, explainable institutional learning system that answers:
- *"What happened before that is relevant to this task?"*
- *"What rule applies?"*
- *"Why does it apply?"*
- *"What must I check before acting?"*
- *"What prevents me from repeating the failure?"*
- *"Has this lesson actually remained reliable across independent future tasks?"*

---

## 2. Target Conceptual Knowledge Model

```
                     ┌──────────────────────────┐
                     │        PRINCIPLE         │
                     │ (Durable Scientific /    │
                     │   Engineering Truth)     │
                     └─────────────┬────────────┘
                                   │
                                   ▼
                     ┌──────────────────────────┐
                     │      FAILURE CLASS       │
                     │ (Controlled Taxonomy of  │
                     │     28 Categories)       │
                     └─────────────┬────────────┘
                                   │
                                   ▼
                     ┌──────────────────────────┐
                     │         INCIDENT         │
                     │ (Concrete Historical     │
                     │  Occurrence & Evidence)  │
                     └─────────────┬────────────┘
                                   │
                                   ▼
                     ┌──────────────────────────┐
                     │          LESSON          │
                     │ (Durable Knowledge       │
                     │   Extracted from Impact) │
                     └─────────────┬────────────┘
                                   │
                                   ▼
                     ┌──────────────────────────┐
                     │           RULE           │
                     │ (Actionable, Enforceable │
                     │   Prevention Directive)  │
                     └─────────────┬────────────┘
                                   │
                                   ▼
                     ┌──────────────────────────┐
                     │      APPLICABILITY       │
                     │ (Structured Predicates   │
                     │    & Scope Matching)     │
                     └─────────────┬────────────┘
                                   │
                                   ▼
                     ┌──────────────────────────┐
                     │VERIFICATION / REGRESSION │
                     │ (Automated Guardrails &  │
                     │     Contract Tests)      │
                     └─────────────┬────────────┘
                                   │
                                   ▼
                     ┌──────────────────────────┐
                     │    VALIDATION HISTORY    │
                     │ (Multi-Task Independent  │
                     │    Evidence Records)     │
                     └──────────────────────────┘
```

---

## 3. Core Knowledge Entities

| Entity | Purpose | Key Attributes | Storage Location |
|---|---|---|---|
| **Principle** | Durable foundational truth | `principle_id`, `title`, `statement`, `rationale`, `scope`, `domain` | `governance_v2/principles.json` |
| **Failure Class** | Controlled taxonomy of error modes | `class_id`, `name`, `description`, `typical_severity`, `prevention_guideline` | `governance_v2/failure_classes.json` |
| **Incident** | Concrete historical occurrence | `incident_id`, `task_id`, `title`, `root_cause`, `impact`, `detection`, `correction` | `governance_v2/incidents.json` |
| **Lesson** | Extracted durable knowledge | `lesson_id`, `title`, `description`, `root_cause`, `correct_rule`, `validation_history` | `governance_v2/lessons.json` |
| **Rule** | Actionable enforcement directive | `rule_id`, `statement`, `scope`, `severity`, `action`, `applies_to`, `prohibited_actions` | `governance_v2/rules.json` |
| **Assumption** | Tracked operational/scientific premises | `assumption_id`, `statement`, `status`, `verification_method`, `associated_rules` | `governance_v2/assumptions.json` |
| **Precedence** | Deterministic conflict resolution rules | `severity_hierarchy`, `scope_hierarchy`, `resolution_rules` | `governance_v2/precedence_policy.json` |

---

## 4. Scope and Precedence Policy

### Scope Hierarchy
1. `GLOBAL`: Universal repository invariants (e.g. firewalls, destructive git prohibition).
2. `DOMAIN`: Domain-specific policies (e.g. statistics, autograd, data preprocessing).
3. `PROJECT`: Ocean Sentinel project-wide contracts (e.g. canonical 12-class taxonomy).
4. `EXPERIMENT`: Experiment-specific protocol invariants (e.g. EXP-07).
5. `DIAGNOSTIC`: Diagnostic investigation boundaries (e.g. DIAG-05).
6. `TASK`: Specific execution task envelope.

### Severity Hierarchy
1. `CRITICAL` (Weight 100): Immediate system block.
2. `HIGH` (Weight 75): Block unless an explicit approved exception applies.
3. `MEDIUM` (Weight 50): Advisory warning.
4. `LOW` (Weight 25): Informational notice.

### Precedence Resolution Engine
- **Non-Overridability:** A `CRITICAL` global rule declared with `non_overridable=True` (such as the HOLDOUT partition quarantine) **can never be overridden** by a more specific task or diagnostic rule.
- **Severity Trumps Specificity:** When two rules target the same action, the rule with higher severity governs.
- **Specificity as Tiebreaker:** Within the same severity tier, the more specific scope governs unless the broader rule is non-overridable.
- **Explicit Supersession:** If Rule A metadata declares `supersedes: ["Rule B"]`, Rule B is retired deterministically.
- **Conflict Detection:** If two rules have identical effective priority and opposing directives (e.g. BLOCK vs ALLOW), the engine flags an explicit `BLOCK-CONFLICT-001` requiring human/agent review. **Never last record wins.**

---

## 5. Controlled Failure Class Taxonomy (28 Classes)

1. `DATA-INTEGRITY`: Corrupted rasters, invalid headers, or missing manifest records.
2. `POPULATION-CONSTRUCTION`: Evaluating support before validity masking or cropping (`GOV-RULE-129`).
3. `OBSERVATION-UNIT-MISMATCH`: Conflating tiles, patches, or pixels with physical units.
4. `INFERENCE-UNIT-MISMATCH`: Treating non-independent tiles as independent degrees of freedom (`GOV-RULE-116`).
5. `INDEPENDENCE-ASSUMPTION`: Assuming sample independence despite scene clustering (`GOV-RULE-124`).
6. `TAXONOMY-DRIFT`: Mutating dense class IDs or source labels across phases.
7. `MATHEMATICAL-DEFINITION`: Altering loss functions or estimators from registered spec.
8. `DENOMINATOR-DRIFT`: Substituting subset normalizations for full-batch denominators (`GOV-RULE-127`).
9. `IMPLEMENTATION-MISMATCH`: Discrepancy between mathematical spec and runtime code.
10. `MODEL-STATE-MISMATCH`: Running diagnostics in `model.train()` or mutating BatchNorm (`GOV-RULE-128`).
11. `AUTOGRAD-SEMANTICS`: Graph retention, in-place tensor mutations, or unzeroed gradients.
12. `OPTIMIZATION-SEMANTICS`: Unauthorized optimizer steps or scheduler updates in diagnostics.
13. `STATISTICAL-PROVENANCE`: Discrepancy between executed routine and declared metadata (`GOV-RULE-130`).
14. `STATISTICAL-INFERENCE`: Applying invalid parametric tests or unadjusted p-values.
15. `P-VALUE-OVERINTERPRETATION`: Interpreting $p > 0.05$ as proof of zero effect or stability (`GOV-RULE-131`).
16. `CAUSAL-OVERCLAIM`: Using causal verbs on descriptive observational data (`BLOCK-004`).
17. `STATIC-VS-DYNAMIC-CONFLATION`: Extrapolating training dynamics from Step-0 evaluations (`GOV-RULE-131`).
18. `ARTIFACT-INTEGRITY`: In-place mutation of closed historical artifacts.
19. `ARTIFACT-REPORT-MISMATCH`: Numbers in reports differing from machine JSON (`GOV-RULE-100`).
20. `EXECUTION-SAFETY`: Destructive git operations or unconstrained execution loops (`BLOCK-007`).
21. `AUTHORIZATION`: Executing unapproved phases (e.g. unauthorized Tier-2 / H3).
22. `TELEMETRY`: Analysis tasks claiming `execution_authorized=true` (`BLOCK-012`).
23. `PSEUDOREPLICATION`: Treating $N > 10^6$ pixels as independent replicates (`BLOCK-009`).
24. `POST-HOC-ANALYSIS`: Presenting exploratory subgroupings as registered hypotheses.
25. `REPRODUCIBILITY`: Unseeded random generators or non-deterministic execution.
26. `TERMINOLOGY-DRIFT`: Using deprecated synonyms (calling OF an "oil spill") (`BLOCK-008`).
27. `DOCUMENTATION-INTEGRITY`: Narrative transcription errors or stale specifications.
28. `GOVERNANCE`: Preflight bypass or unverified `PROVEN_STABLE` claims (`BLOCK-010`, `BLOCK-011`).

---

## 6. Explicit Assumption Registry

Rather than treating operational premises as implicit facts, v2 maintains an active assumption ledger:

| Assumption ID | Statement | Epistemic Status | Verification Invariant |
|---|---|---|---|
| `ASSUMP-001` | Tile maps one-to-one to parent acquisition scene. | `VERIFIED` | Audited across all 132 TRAIN tiles. |
| `ASSUMP-002` | Sample support thresholds ($M_c \ge K$) evaluated post-validity masking. | `VERIFIED` | Enforced via `GOV-RULE-129`. |
| `ASSUMP-003` | Statistical routines explicitly bind method parameter in code and metadata. | `VERIFIED` | Enforced via `GOV-RULE-130`. |
| `ASSUMP-004` | Model is in explicit `model.eval()` mode with BatchNorm frozen in diagnostics. | `VERIFIED` | Enforced via `GOV-RULE-128`. |
| `ASSUMP-005` | Artifact p-values are derived directly from executed routine. | `VERIFIED` | Enforced via `GOV-RULE-100`. |
| `ASSUMP-006` | Minibatch size $B_{\text{phys}}=4$ guarantees scene independence. | `CONTRADICTED` | Clustered scenes co-occur in minibatches. |
| `ASSUMP-007` | Step-0 non-significance proves dynamic training stability. | `CONTRADICTED` | Static Step-0 does not bound trajectory. |
| `ASSUMP-008` | Opposing gradient alignment is an intrinsic structural architecture property. | `CONTRADICTED` | Observed only on Step-0 OPS-02 initialization. |
| `ASSUMP-009` | HOLDOUT partition is completely quarantined and inaccessible. | `VERIFIED` | Enforced via `BLOCK-001-HOLDOUT`. |
| `ASSUMP-010` | Part III external benchmark is strictly firewalled. | `VERIFIED` | Enforced via `BLOCK-002-PART_III`. |
| `ASSUMP-011` | Canonical checkpoint weights match SHA256 `67181C4C...`. | `VERIFIED` | Audited bit-for-bit. |
| `ASSUMP-012` | Analysis-only tasks permit strictly zero backward passes. | `VERIFIED` | Enforced via `BLOCK-006-UNAUTHORIZED_TRAINING`. |

---

## 7. Hybrid Retrieval Engine

Future agents query repository institutional memory using hybrid scoring:
1. **Exact Identifiers (Score 1.0):** Immediate lookup by rule ID, lesson ID, or historical alias.
2. **Trigger Patterns (Score 0.95–0.98):** Scans proposed commands and plan text for prohibited keywords or regex patterns.
3. **Structured Scope Match (Score 0.85):** Filters by task type, experiment, diagnostic, or domain.
4. **Operation Match (Score 0.85):** Matches declared operations (e.g. `sample_eligibility_census`).
5. **Failure Class Match (Score 0.75):** Matches declared risk classes.
6. **Lexical Keyword Match (Score 0.30–0.70):** Tokenized overlap across lesson titles, descriptions, and prevention rules.

Every retrieval result outputs a human-readable **`relevance_reason`** explaining why the lesson was surfaced.

---

## 8. Novelty Detection Engine

When an incoming task declares new operations, assumptions, or failure classes, the novelty detector classifies the surface:
- `NOVEL`: Unrecognized operation or uncatalogued failure class. Emits guidance to establish invariants.
- `POTENTIALLY_NOVEL`: Active assumption that is `UNVERIFIED` and lacks a backing rule.
- `KNOWN_BUT_UNPROTECTED`: Applicable rule is in `RECORDED` state without an automated regression test.
- `KNOWN`: Fully covered by active, regression-protected governance rules.

---

## 9. Scientific & Statistical Method Provenance Chain

To prevent discrepancies between scientific intent, code execution, and narrative reporting, the architecture validates the complete provenance chain:

$$\text{Question} \longrightarrow \text{Estimand} \longrightarrow \text{Data} \longrightarrow \text{Population} \longrightarrow \text{Observations} \longrightarrow \text{Method Config} \longrightarrow \text{Executed Result} \longrightarrow \text{Artifact} \longrightarrow \text{Report}$$

### Provenance Invariants:
1. **No Fake Degrees of Freedom:** Prohibits declaring degrees of freedom for non-parametric rank tests (`Wilcoxon`, `Mann-Whitney`).
2. **Explicit Distribution Metadata:** Metadata must declare whether p-values derive from exact permutation distributions or asymptotic normal approximations.
3. **Unit Separation:** Observation units ($N_{\text{obs}}$, physical tiles) and inferential units ($K_{\text{clusters}}$, parent scenes) must be explicitly reported.
4. **Machine Truth Derivation:** All reported metrics must derive directly from machine JSON artifacts (`GOV-RULE-100`).

---

## 10. DIAG-05 Adversarial Replay Suite Results

The architecture was validated by replaying all 12 failure modes discovered during DIAG-05 against the preflight and enforcement engine:

| Adversarial Case | Replayed Failure Condition | Expected Action | Actual v2 Behavior | Result |
|---|---|---|---|---|
| **Case 1** | Raw disk mask support $\ge K$, post-validity support $=0$. | `BLOCK` | Blocked via `GOV-RULE-129-POPULATION_CONSTRUCTION` | **PASSED** |
| **Case 2** | `scipy.stats.wilcoxon` called without explicit `method`. | `BLOCK` | Blocked via `GOV-RULE-130-UNBOUND_METHOD` | **PASSED** |
| **Case 3** | Metadata claims asymptotic while calculation is exact. | `WARN` | Warned via `GOV-RULE-130-METADATA_MISMATCH` | **PASSED** |
| **Case 4** | $p > 0.05$ described as "proves no effect" or "guarantees stability". | `BLOCK` | Blocked via `GOV-RULE-131-OVERCLAIM_NO_EFFECT` | **PASSED** |
| **Case 5** | Step-0 alignment described as "intrinsic structural characteristic". | `BLOCK` | Blocked via `GOV-RULE-131-OVERCLAIM_INTRINSIC` | **PASSED** |
| **Case 6** | Tile-level $n$ treated as inferential $N$ for clustered scenes. | `BLOCK` | Blocked via `GOV-RULE-116-INFERENCE_UNIT_MISMATCH` | **PASSED** |
| **Case 7** | $B=8$ assumed to provide parent-cluster independence. | `WARN/BLOCK` | Flagged via `GOV-RULE-124-MINIBATCH_INDEPENDENCE` | **PASSED** |
| **Case 8** | Subset-normalized gradient substituted for full-batch denominator. | `BLOCK` | Blocked via `GOV-RULE-127-DENOMINATOR_DRIFT` | **PASSED** |
| **Case 9** | `model.train()` invoked during diagnostic static profiling. | `BLOCK` | Blocked via `BLOCK-006-UNAUTHORIZED_TRAINING` | **PASSED** |
| **Case 10** | Negative cosine described as "destructive interference" without spec. | `WARN` | Warned via `GOV-RULE-131-UNREGISTERED_INTERFERENCE` | **PASSED** |
| **Case 11** | Analysis-only task leaves `execution_authorized=true` in telemetry. | `BLOCK` | Blocked via `BLOCK-012-TELEMETRY_AUTHORIZATION_AMBIGUITY` | **PASSED** |
| **Case 12** | Report claims status "VALID" while population construction is defective. | `BLOCK` | Blocked via `GOV-RULE-100-AMBIGUOUS_VALID_STATUS` | **PASSED** |

*All compliant counterexamples passed with zero false-positive blocks.*

---

## 11. Performance Benchmarks

- **V2 Preflight Evaluation Latency:** **0.0046 seconds** (Target: $< 5.0$ seconds).
- **Hybrid Retrieval Latency:** **0.0012 seconds** across 104 lessons and 121 rules.
- **Combined Test Suite Runtime:** **6.65 seconds** across 142 tests.

---

## 12. Migration and Backward Compatibility

- **100% Information Preservation:** All 104 historical lessons in `ocean_sentinel_lessons_learned_v1.json` were migrated to `governance_v2/lessons.json` with historical validation histories, aliases, and categories intact.
- **Legacy Preflight Preserved:** `scripts/agent_governance_preflight.py` retains 100% backward compatibility for existing `--task-type <type>` CLI options and test suites, while introducing `--v2`, `--query-lessons`, and `--context-json`.
