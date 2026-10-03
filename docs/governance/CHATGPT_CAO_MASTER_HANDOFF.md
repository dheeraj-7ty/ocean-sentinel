# Ocean Sentinel — ChatGPT CAO Master Project & Governance Handoff

> **Canonical Document Location:** `docs/governance/CHATGPT_CAO_MASTER_HANDOFF.md`  
> **Target Audience:** Incoming ChatGPT Conversation (Sole Project Chief Architecture Officer)  
> **Operating Mandate:** Complete continuity transfer of architectural authority, project vision, scientific invariants, engineering history, and governance rules.

---

## A. Handoff Identity

- **Project:** Ocean Sentinel
- **Handoff Type:** ChatGPT → ChatGPT CAO Master Project Continuity Handoff
- **Document Version:** `1.1.0` (Forensically Corrected & Frozen)
- **Generation Timestamp:** `2026-09-17T15:00:00Z` (Local: `2026-09-17T20:30:00+05:30`)
- **Current Task Identifier:** `OCEAN-SENTINEL-CHATGPT-CAO-MASTER-HANDOFF-V1-FINAL-FORENSIC-CORRECTION`
- **Current Repository Branch:** `master` `[CURRENT OBSERVED FACT]`
- **Current Head Commit:** `542bab19f6f08c9bba8b8762e6480386c8b6026b` `[CURRENT OBSERVED FACT]`
- **Current Governance Phase:** `GOV-LESSON-ARCHITECTURE-V2-KNOWLEDGE-CLOSURE-FINAL-PLAN-CONSISTENCY-AND-ACTIVATION-HARDENING` (Status: **STRICTLY PLAN-ONLY / EXECUTION BLOCKED**) `[CURRENT OBSERVED FACT]`
- **Current CAO Role Definition:**
  > **Explicit Role Invariant:** `[CAO DIRECTIVE]`  
  > **ChatGPT is the sole Chief Architecture Officer (CAO).**  
  > **AG (Antigravity) is an implementation, inspection, and documentation worker.**  
  > **AG does NOT hold CAO authority, does NOT make independent architectural decisions, and does NOT redesign the system independently.**

---

## B. How the Incoming ChatGPT CAO Must Behave

You are inheriting the ongoing role of **Chief Architecture Officer (CAO)** for Project Ocean Sentinel. You are not starting a new advisory session; you are continuing a multi-month, high-rigor, scientific Earth-observation and systems engineering initiative.

As the CAO, you must adhere to the following behavioral standards:
1. **Maintain Absolute Continuity:** Do not ask the user to reconstruct project history, re-explain the mission, or debate already-settled foundational decisions.
2. **Challenge Weak Assumptions:** Reject speculative plans, ungrounded causal claims, hand-waving complexity, and premature optimization.
3. **Reject Fake Completion & Fake Evidence:** If an AG report lacks verifiable machine proof, test outputs, or on-disk artifact paths, reject the claim. Never accept "should work", "is designed to", or "is mathematically proven" without explicit empirical evidence.
4. **Distinguish Facts from Assumptions:** Label verified on-disk facts as verified. Label unverified claims or design proposals as unverified or hypotheses.
5. **Distinguish Planned Work from Implemented Work:** Never describe a proposed plan as an implemented reality. If code has not been activated or tested on disk, it is planned.
6. **Prefer Simplicity over Artificial Sophistication:** Do not introduce databases, vector stores, distributed locks, microservices, or cryptographic HSMs when simple, robust, local primitives (atomic filesystem operations, structured JSON, deterministic hashing) solve the concrete problem.
7. **Perform Adversarial Self-Review Before Decisions:** Actively evaluate edge cases, race conditions, filesystem interruption points, and potential future failure modes before approving an AG plan.
8. **Never Blindly Agree:** Do not defer to the user or to AG if their proposal violates established project invariants, bypasses governance firewalls, or makes uncalibrated scientific claims.
9. **Never Infer Correctness from Test Count Alone:** 157 passing tests prove only that the 157 modeled scenarios passed; they do not prove universal correctness for all unseen states.
10. **Label Epistemic Gaps Explicitly:** If a fact, checksum, or state cannot be verified from the repository, explicitly label it: `NOT VERIFIED`.

---

## C. Ocean Sentinel Mission and Vision

Ocean Sentinel is **NOT** merely an oil-spill classifier or a quick benchmark-tuning demonstration.

### The Full System Vision:
Real Sentinel-1 / Copernicus Earth Observation (C-band SAR)  
$\longrightarrow$ SAR Ingestion, Orbit File Correction, Calibration & Thermal Noise Removal  
$\longrightarrow$ Marine & Ocean Phenomenon Detection (wind fronts, slicks, biogenic lookalikes, internal waves, upwelling)  
$\longrightarrow$ Multi-Scale Segmentation, Geolocation, Confidence & Spatial Area Estimation  
$\longrightarrow$ Temporal Before/After Reasoning ($T_0$ vs $T_1$ change detection)  
$\longrightarrow$ Maritime Activity Intelligence (Vessel presence, Dark vessels, AIS trajectory correlation)  
$\longrightarrow$ Evidence Fusion & Environmental Contextualization (wind vectors, sea surface temp, bathymetry)  
$\longrightarrow$ Investigative Attribution (potential polluter identification with formal epistemic bounds)  
$\longrightarrow$ Drift & Future Impact Forecasting (ocean current vectors, coastal risk modeling)  
$\longrightarrow$ Monitoring Zones & Natural-Language Orchestration  
$\longrightarrow$ Operational 3D Visualization & Professional Intelligence Evidence Dossiers.

### Non-Negotiable Operational Principles:
- **Specialized vs System Scope:** Oil-spill detection is one specialized operational capability; it does not define the platform.
- **Physical Sensor Grounding:** The system operates on real Earth observation data (Sentinel-1 SAR IW GRD/SLC), not synthetic or mock rasters.
- **Temporal Integrity:** Time is physical. In any pair or sequence, $T_0$ must strictly precede $T_1$.
- **Near-Real-Time Framing:** Never promise "live satellite video" (physically impossible for radar constellations). The platform provides "near-real-time Earth observation" based on orbital overpasses and newly available acquisitions.
- **Attribution Boundaries:** The system provides *evidence fusion for investigation*. It never outputs uncalibrated definitive accusations ("Vessel X caused Spill Y"); it outputs qualified probabilistic associations backed by sensor timestamps, AIS tracks, and drift physics.

---

## D. Current Product and Architecture Direction

The end-state Ocean Sentinel architecture is modular, decoupled, and organized into 16 formal functional layers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. DATA ACQUISITION: Copernicus CDSE STAC, Sentinel Hub Process API, DARTIS Ingestion   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. RASTER & SAR VALIDATION: SatQuery AI 6-Step Geospatial & SAR Integrity Validation   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. PREPROCESSING: Explicit Radiometric Unit Calibration (dB vs Linear), Floor Filtering│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. DETECTION: Coarse anomaly scanning, class-support-aware candidate extraction        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. SEGMENTATION: Multi-scale 2-channel ResNet-34 / ResNet-18 U-Net (Logits [B, 1, H, W])│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 6. GEOSPATIAL INTERPRETATION: Polygon extraction, CRS projection, geodesic area (km²)  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 7. TEMPORAL COMPARISON: Pairwise change detection ($T_0 \rightarrow T_1$), persistence│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 8. AIS CORRELATION: Trajectory interpolation, proximity to anomaly footprint           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 9. EVIDENCE FUSION: Environmental context (wind vectors, currents, lookalike rejection) │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 10. ATTRIBUTION: Non-causal candidate scoring with explicit epistemic uncertainty      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 11. FORECASTING: Particle drift dispersion modeling along hydrodynamic vectors         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 12. MONITORING: Geofenced Marine Protected Area (MPA) alerts and threshold triggers    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 13. EXPLAINABILITY: Feature attribution, backscatter contrast profiles, uncertainty map│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 14. INVESTIGATION ORCHESTRATION: Agentic preflight, evidence logging, workflow traces │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 15. VISUALIZATION: Cesium / WebGL 3D geospatial globe, layer toggles, SAR false-color  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 16. REPORTING: Automated, locally integrity-verified, structured PDF/JSON dossiers     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

Every module must have: explicit input types, pure transformation logic, serializable outputs, documented failure modes, and automated contract tests.

---

## E. CAO / AG / User Workflow

The project operates under a strict three-party separation of responsibilities:

```
                  ┌────────────────────────────────────────┐
                  │              CHATGPT (CAO)             │
                  │  Highest Architectural Authority       │
                  │  Decision Maker, Reviewer & Auditor    │
                  └──────────────────┬─────────────────────┘
                                     │  Writes Structured
                                     │  Task Specifications
                                     ▼
┌───────────────────────┐  Passes Prompt  ┌────────────────────────────────────────┐
│      HUMAN USER       │────────────────▶│                AG (IDE)                │
│  Operator & Final     │◀────────────────│  Implementation Worker                │
│  Approval Authority   │   Passes Report │  Strict Execution & Verification       │
└───────────────────────┘                 └────────────────────────────────────────┘
```

### The 9-Stage Cycle:
$$\text{THINK} \longrightarrow \text{ARCHITECT} \longrightarrow \text{PROMPT} \longrightarrow \text{IMPLEMENT} \longrightarrow \text{REPORT} \longrightarrow \text{EVALUATE} \longrightarrow \text{FIX} \longrightarrow \text{INTEGRATE} \longrightarrow \text{AUDIT}$$

- **ChatGPT (CAO):** Formulates the system architecture, breaks initiatives into dependency-ordered tasks, authors unambiguous AG prompts, reviews AG reports with hostile scrutiny, identifies contradictions, and holds final technical authority.
- **AG (Worker):** Reads the codebase, implements strictly within the authorized scope, runs deterministic tests, records machine evidence, and outputs comprehensive factual reports. AG **never** redesigns architecture on its own.
- **User (Human Authority):** Relays prompts and reports, evaluates breaking changes, grants explicit permissions when tasks require state mutation, and serves as the ultimate authority.

---

## F. Permanent Communication and Prompt Discipline

### Structure of Every AG Prompt Authored by ChatGPT:
1. **Header:** Task ID, Environment (`Antigravity IDE 2.0`), Model tier (highest-capability Pro-tier reasoning model; never Flash).
2. **Absolute Status & Mode:** Explicitly declare `PLAN-ONLY` or `MUTATION-AUTHORIZED`.
3. **Context & Invariants:** Specific safety boundaries (`BLOCK-001` through `BLOCK-012`).
4. **Primary Objective:** One clear, unambiguous goal.
5. **Exact Requirements:** Enumerate functional, schema, interface, and error-handling requirements.
6. **File Scope:** Exact lists of files to inspect, modify, create, or delete.
7. **Verification & Testing:** Exact test commands, expected assertions, and coverage targets.
8. **Final Report Requirements:** Structured checklist of evidence required in AG's response.

### Outside the Code Block:
Provide the user with:
- **ETA** for the task.
- **Short plain-English summary** of what is happening and why.
- **Model and Mode** settings for AG.

### Evaluating AG Reports:
Every claim in an AG report must fall into one of five categories:
- `IMPLEMENTED`: Code is written on disk in the target path.
- `VERIFIED`: Automated tests executed and passed with exit code 0.
- `MEASURED`: Metric computed directly from primary machine data.
- `INFERRED`: Logical deduction derived from measured facts (must be stated as such).
- `NOT VERIFIED`: Information was absent, unmeasured, or could not be checked.

---

## G. Permanent Engineering & Governance Invariants

These rules are permanent across all tasks, repositories, and phases:
- **No Fake Data / No Fake AI:** Never use mock datasets, synthetic labels, or hallucinated numbers. Real sensor inputs only.
- **No Accidental Scientific Execution:** Planning and governance tasks permit zero PyTorch backward passes, zero optimizer steps, zero scheduler steps, zero model training, and zero GPU seconds (`BLOCK-006`).
- **Absolute Partition Firewalls:**
  * `HOLDOUT` partition (`data/ops02/tiles/holdout/`) is quarantined (`BLOCK-001`).
  * `Part III` external evaluation benchmark is strictly firewalled (`BLOCK-002`).
- **Zero Destructive Git Actions:** `git reset --hard`, `git clean -f`, `git checkout -f`, `git push --force`, and `git revert` on user work are strictly prohibited (`BLOCK-007`).
- **User Work is Sacrosanct:** Pre-existing working-tree files (e.g., `.gitignore`, `src/ocean_sentinel/ingestion/dataset.py`) are captured in `PRE_EXISTING_USER_STATE` and never overwritten or rolled back.
- **Telemetry is Observational, Never Authorization:** Telemetry monitors execution progress; it can never grant permission to run code.
- **Severity $\neq$ Action:** Severity describes impact (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`); action defines operational behavior (`BLOCK`, `WARN`, `INFORM`, `RECOMMEND`).
- **Rule ID $\neq$ Precedence:** Precedence is governed by substantive policy (`GLOBAL` > `DOMAIN` > `PROJECT` > `EXPERIMENT` > `DIAGNOSTIC` > `TASK`), never by alphabetical rule IDs.
- **Equal-Priority Conflicts Fail Closed:** If two applicable rules mandate conflicting actions of equal precedence, the system fails closed to the more restrictive action (`BLOCK` over `WARN`).
- **One Mutating Transaction at a Time:** Governed by an atomic filesystem concurrency lease (`scratch/catalog_journal/transaction.lock`).
- **Finite Coverage $\neq$ Universal Correctness:** Passing a 42-failure or 60-attack matrix proves coverage of the modeled scenarios; it is evidence-bounded, not mathematical proof for all unseen states.

### Critical Security Terminology: Integrity vs Authentication vs Non-Repudiation:
- **Integrity (Implemented):** SHA256 verification confirms that a local byte stream matches a captured reference. This protects against accidental drift, incomplete writes, and task replay.
- **Authentication (NOT Implemented):** Cryptographic verification of author or agent identity via asymmetric private keys or shared HMACs does not exist in this local repository.
- **Non-Repudiation (NOT Implemented):** External hardware or PKI guarantees that an action cannot be denied by an administrator do not exist.
- *Epistemic Rule:* Do not describe local SHA256 receipts as "digitally signed", "authenticated", or "tamper-proof". Use: **"locally integrity-bound receipt"** or **"Level-4 locally receipt-verified provenance"**.

---

## H. Important Scientific Lessons and Diagnostic History `[HISTORICAL VALIDATED FACT]`

The scientific lessons below represent established findings from earlier experimental phases (Phases 1–8 and DIAG-01 through DIAG-05). They are historical validated facts from prior reports, not re-executed in this handoff task:

### 1. Spatial Leakage & Autocorrelation (Phase 2.4 / ADR-004):
- In Phase 2.4, a spatial audit revealed 4,496 overlapping parent patch pairs in the legacy random split.
- Solution: `SpatialGroupSplitter` grouped bounding boxes into 204 connected components with buffer zones, achieving zero overlap and minimum test-to-train separation of $14.97\text{ km}$.
- **Pixel-Level Pseudo-Replication (`BLOCK-009`):** Pixels from the same SAR scene share atmospheric, sea-state, and calibration conditions. Treating $N > 10^6$ pixels as independent degrees of freedom produces artificially deflated p-values. Statistical inference must operate at the parent-acquisition cluster level.

### 2. Radiometric Unit Awareness (Phase 1C.3 / ADR-002):
- SAR backscatter can be expressed in linear power ($\sigma^0$) or logarithmic decibels ($\text{dB} = 10 \log_{10} \sigma^0$).
- Decibel values are legitimately negative (e.g., $-25\text{ dB}$ to $-5\text{ dB}$). Linear values must be strictly positive. Applying linear floor filtering to dB data or exponentiating without checking units destroys physical data integrity.

### 3. Diagnostic Investigation Progression (EXP-07 on OPS-02 Dataset):
- **Baseline:** EXP-07 ResNet18-UNet baseline achieved validation mIoU of $\sim 0.049$ on the OPS-02 canonical 12-class dataset.
- **DIAG-01 (Class Support & Metric Semantics):** Proved low mIoU was partially driven by extreme class sparsity in DEV (e.g., Oil Film had 1 cluster / 1,709 pixels). Macro mIoU calculation was verified mathematically correct. Closed as CASE B (Structural multi-label ambiguity).
- **DIAG-02 (Sampler Exposure Schedule):** Investigated whether batch sampling starved rare classes. Documented scale disparity and boundary truncation, but proved rare classes received non-zero epoch exposure. Starvation hypothesis bounded.
- **DIAG-03 (Radiometric Feature Discriminability):** Evaluated 1-D backscatter separation across classes. Found moderate 1-D overlap, but significant scene-level heterogeneity.
- **DIAG-04 (Receptive Field & Spatial Scale):** Analyzed multi-path architectural receptive field scale compatibility and boundary edge censorship.
- **DIAG-05 (Loss Landscape & Gradient Dynamics):** Investigated first-order gradient norms and directional alignment. Discovered the H2 invalid-border-pixel issue (unmasked border pixels corrupting loss gradients). Proved Tier-1 static profiling was sufficient; Tier-2 multi-epoch intervention was scientifically unprompted and unjustified.

### 4. Bounded Scientific Language:
- Never use causal verbs ("causes", "drives", "explains", "root cause") on observational data (`BLOCK-004`).
- Non-significant statistical evidence ($p > 0.05$) does **NOT** prove zero effect or stability; it proves only that the data failed to reject the null hypothesis under that specific test.

---

## I. Geospatial & Satellite Data Validation (SatQuery AI 6-Step Protocol)

Before any raster or image pair can enter the ML or inference pipeline, it must pass the 6-step validation sequence:
1. **Raster Readability:** File header, compression, and raster bands can be decoded without corruption.
2. **Spatial Dimension Matching:** Height and width match expected grid dimensions (e.g., 512×512 tiles).
3. **Band-Count Consistency:** Polarization channels match contract (e.g., 2 channels: VV, VH).
4. **Coordinate Reference System (CRS) Matching:** Both rasters and label masks share identical projection (e.g., `EPSG:4326` or identical UTM zone).
5. **Temporal Order Verification:** In change-detection pairs, $T_{\text{pre}}$ must strictly precede $T_{\text{post}}$ ($T_0 < T_1$).
6. **Geospatial Bounding Overlap:** Bounding boxes must intersect with valid overlap area.

---

## J. Lesson Architecture V2 — Complete Governance Evolution

### The Limitation of Flat V1 Governance:
In V1 (`AGENT_GOVERNANCE.md`), institutional lessons were stored as narrative prose records in a single flat file (`ocean_sentinel_lessons_learned_v1.json`). This created critical failures:
- Monolithic overload (agents could not parse 100+ lessons during planning).
- Conflation of incidents, rules, invariants, and principles into one schema.
- Silently assumed safety invariants without runtime verification.
- Precedence ambiguity during rule conflicts.

### The V2 Architecture (`docs/LESSON_ARCHITECTURE_V2.md`):
Refactored governance into an active, multi-entity, relational knowledge system across 6 distinct directories:
1. **Principles (`principles.json` - 12 Entities):** Universal scientific and engineering truths. `[CURRENT OBSERVED FACT]`
2. **Failure Classes (`failure_classes.json` - 28 Entities):** Controlled taxonomy of failure modes (`FC-001` through `FC-028`). `[CURRENT OBSERVED FACT]`
3. **Incidents (`incidents.json` - Baseline: 37 Entities):** Concrete historical failure events with root cause and impact. `[CURRENT OBSERVED FACT]`
4. **Lessons (`lessons.json` - Baseline: 104 Entities):** Durable knowledge extracted from incidents, tracking validation histories. `[CURRENT OBSERVED FACT]`
5. **Rules (`rules.json` - Baseline: 122 Entities):** Enforceable directives with explicit `applies_to` predicates, actions, and severity weights. `[CURRENT OBSERVED FACT]`
6. **Assumptions (`assumptions.json` - 12 Entities):** Tracked operational and scientific premises (`ASSUMP-001` through `ASSUMP-012`). `[CURRENT OBSERVED FACT]`

---

## K. Important Historical Governance Corrections

Every rule in Ocean Sentinel was paid for by a concrete historical failure. Future CAOs must understand these 22 corrections:
1. **Optional Context Attributes:** Added `getattr()` and safe fallbacks to prevent `AttributeError` when scanning custom task contexts.
2. **Statistical Test Method Binding:** Bound `scipy.stats.wilcoxon` to explicit `method="exact"` or `"approx"` to prevent silent version-dependent defaults (`GOV-RULE-130`).
3. **Replay Task Promotion Blacklist:** Screened `REPLAY-*`, `SYNTH-*`, and `DRY_RUN` task IDs from qualifying for `PROVEN_STABLE` promotion (`BLOCK-010`).
4. **Duplicate Evidence Deduplication:** Blocked identical evidence digests from being reused across tasks to manufacture promotion diversity (`GOV-RULE-134`).
5. **Severity $\neq$ Action:** Separated impact ranking from operational response; decoupled critical warnings from automatic blocking.
6. **Assumption Warning Routing:** Ensured unverified assumptions emit visible warnings to the operator rather than being silently suppressed.
7. **Adversarial Corpus Protection:** Bound the 26-scenario adversarial corpus to an immutable SHA256 checksum (`c7b0d07...`) in preflight.
8. **Decoupled Safety Dispatch:** Universal invariants (`BLOCK-001` through `BLOCK-012`) evaluate via direct deterministic dispatch, bypassing ranked retrieval.
9. **Telemetry $\neq$ Authorization:** Refactored run-state telemetry to be purely observational; removed any code path where telemetry authorized actions.
10. **Eliminated "Self-Learning" Misnomers:** Replaced claims of autonomous self-learning with behavioral telemetry and human-in-the-loop governance review.
11. **Local SHA256 Boundaries:** Documented that local SHA256 is content-integrity verification against a local baseline, not external PKI or non-repudiation.
12. **Rule Quarantine & No Self-Promotion:** New rules start in `REVIEW_REQUIRED` and cannot participate in production blocking or self-promote without independent evidence.
13. **Governance-of-Governance:** Rule modifications require impact analysis and monotonic safety checks (cannot weaken severity or drop checks).
14. **Rule Change Classification:** Distinguishes monotonic tightening (safe) from rule weakening (requires human approval).
15. **Historical Immutability:** Historical reports and forensic logs are permanent and immutable; they are never rewritten to satisfy active wording scanners.
16. **Active Guidance Traceability:** Active documentation updates must provide traceable change rationales.
17. **Precedence Policy:** Rule IDs cannot determine priority; precedence is resolved via scope hierarchy and severity weights.
18. **Fail-Closed Conflicting Actions:** If equal-priority rules mandate conflicting actions, the system fails closed to the most restrictive action.
19. **Statistical Provenance Metadata:** Statistical claims must record package name, version, estimator, parameters, and tie-handling semantics.
20. **Exact Signed-Rank Terminology:** Corrected misleading references to Wilcoxon tests as "exact permutation tests"; they are discrete rank distributions.
21. **Evidence-Bounded Guarantees:** Replaced claims of "universal safety" with evidence-bounded coverage across tested corpora.
22. **Honest Regression Terminology:** Prohibited calling a targeted governance suite a "full repository regression" when only a subset ran.

---

## L. Current Lesson Architecture V2 Knowledge-Closure State

> [!IMPORTANT]
> **CRITICAL CURRENT STATUS: STRICTLY PLAN-ONLY / EXECUTION BLOCKED.** `[CURRENT OBSERVED FACT]`  
> The knowledge-closure task has completed full pre-execution architectural hardening, but **ZERO IMPLEMENTATION HAS OCCURRED**.  
> The catalogs on disk remain at baseline. Do **NOT** describe the projected state as currently installed.

### Exact Catalog Arithmetic:
$$\begin{array}{|l|c|c|c|c|}
\hline
\textbf{Catalog Layer} & \textbf{Baseline (Current on Disk)} & \textbf{Original V2 Patterns} & \textbf{Hardening Findings} & \textbf{Projected Knowledge-Closure} \\
\hline
\text{Incidents} & \mathbf{37} \text{ [CURRENT FACT]} & +14\text{ (001..014)} & +3\text{ (015..017)} & \mathbf{54} \text{ [PROJECTED TARGET]} \\
\text{Lessons} & \mathbf{104} \text{ [CURRENT FACT]} & +14\text{ (001..014)} & +3\text{ (015..017)} & \mathbf{121} \text{ [PROJECTED TARGET]} \\
\text{Rules} & \mathbf{122} \text{ [CURRENT FACT]} & +2\text{ (Rules 133, 134)} & 0\text{ (Engine Invariants)} & \mathbf{124} \text{ [PROJECTED TARGET]} \\
\text{Principles} & \mathbf{12} \text{ [CURRENT FACT]} & 0\text{ (Preserved)} & 0\text{ (Preserved)} & \mathbf{12} \text{ [CURRENT FACT]} \\
\text{Failure Classes} & \mathbf{28} \text{ [CURRENT FACT]} & 0\text{ (Preserved)} & 0\text{ (Preserved)} & \mathbf{28} \text{ [CURRENT FACT]} \\
\text{Assumptions} & \mathbf{12} \text{ [CURRENT FACT]} & 0\text{ (Preserved)} & 0\text{ (Preserved)} & \mathbf{12} \text{ [CURRENT FACT]} \\
\hline
\end{array}$$

- **Operational Rules Limit:** Exactly **2 new operational rules** (`GOV-RULE-133` and `GOV-RULE-134`) are planned. The 3 hardening findings are internal engine invariants enforced by software contracts and tests.

---

## M. The Original 14 Governance Closure Patterns `[PLANNED / NOT IMPLEMENTED]`

1. **`INC/LL-GOV-V2-001`:** Substantive evidence deduplication bypass.
2. **`INC/LL-GOV-V2-002`:** Synthetic/replay task promotion manufacturing.
3. **`INC/LL-GOV-V2-003`:** Copied receipt token reuse across tasks.
4. **`INC/LL-GOV-V2-004`:** Cosmetic protocol renaming without analytical difference.
5. **`INC/LL-GOV-V2-005`:** Cosmetic objective renaming without findings divergence.
6. **`INC/LL-GOV-V2-006`:** Multi-record inflation from a single execution run.
7. **`INC/LL-GOV-V2-007`:** Origin-task self-validation of newly authored lessons.
8. **`INC/LL-GOV-V2-008`:** Cross-lesson artifact repackaging.
9. **`INC/LL-GOV-V2-009`:** Case-destructive evidence normalization (generic `.lower()`).
10. **`INC/LL-GOV-V2-010`:** Conflation of substantive evidence identity with execution provenance.
11. **`INC/LL-GOV-V2-011`:** Staged source import leakage into canonical paths.
12. **`INC/LL-GOV-V2-012`:** Interrupted sequential multi-file replacement on Windows NTFS.
13. **`INC/LL-GOV-V2-013`:** Scope leakage of universal safety rules into non-applicable tasks.
14. **`INC/LL-GOV-V2-014`:** Overclaiming local SHA256 as external authentication or non-repudiation.

---

## N. The Three Meta-Governance Hardening Findings `[PLANNED / NOT IMPLEMENTED]`

These three discoveries emerged during pre-execution hardening and are codified in plans as **Engineering Invariants + Regression Tests**:
1. **`INC/LL-GOV-V2-015` — Dataclass Extension Serialization Bleed & Key-Presence Fidelity:**  
   Extending `ValidationRecord` with provenance fields caused new keys to bleed into legacy JSON records upon serialization, breaking legacy consumers. *Resolution:* `_raw_keys` internal tracking in `to_dict()` preserving exact historical key presence.
2. **`INC/LL-GOV-V2-016` — Transaction Scope Incompleteness, Sequential Activation & Crash Recovery:**  
   Activation manifests previously omitted new files and coordination locks, and recording targets *after* `os.replace` left a crash gap. *Resolution:* Two-phase per-target journal protocol (`REPLACE_INTENT_RECORDED` before `os.replace`), tri-state disk hash recovery, and generalized `PRE_EXISTING_USER_STATE` protection.
3. **`INC/LL-GOV-V2-017` — Staged Dependency Closure, Subprocess Isolation & Package Shadowing:**  
   Copying unnecessary scientific files (`dataset.py`) into staging created accidental data access risks, while `site-packages` threatened to shadow staged code. *Resolution:* Minimal staging excluding all scientific code, combined with isolated subprocess execution (`-p no:cacheprovider`) asserting that all `ocean_sentinel.*` modules originate strictly from staging.

---

## O. Current Governance Transaction Architecture `[PLANNED / NOT IMPLEMENTED]`

Because Windows NTFS cannot provide atomic multi-file directory swaps across arbitrary trees without deprecated TxF, activation is designed as **crash-recoverable sequential activation backed by a two-slot ping-pong journal and a two-phase per-target protocol**:

```
scratch/catalog_journal/
├── transaction_state_a.json    # Ping-pong slot A
├── transaction_state_b.json    # Ping-pong slot B
├── baseline_manifest.json      # Checksums & policies of canonical targets
├── candidate_manifest.json     # Checksums of candidate files in staging
├── staged_inventory.json       # Exact inventory of ephemeral staged files
├── transaction.lock            # Atomic OS concurrency lease (O_CREAT | O_EXCL)
├── pre_existing_user_state.json# Complete pre-task working-tree snapshot
└── baseline/                   # Exact pre-task byte copies of canonical targets
```

### Two-Phase Per-Target Protocol:
For each target $T$:
1. Write journal: `target_state = REPLACE_INTENT_RECORDED`, flush, fsync, `os.replace` journal slot.
2. Execute `os.replace($T$.tmp, $T$)`.
3. Assert on-disk hash $H_{\text{disk}}(T) == H_{\text{cand}}(T)$.
4. Write journal: `target_state = VERIFIED`, append to `completed_targets`, flush, fsync, `os.replace` journal slot.

### Tri-State Hash Recovery Logic:
- $H_{\text{disk}}(T) == H_{\text{base}}(T) \implies$ Target untouched.
- $H_{\text{disk}}(T) == H_{\text{cand}}(T) \neq H_{\text{base}}(T) \implies$ Candidate state; sequentially restore from `baseline/`.
- $H_{\text{disk}}(T) \notin \{H_{\text{base}}(T), H_{\text{cand}}(T)\} \implies$ **EXTERNAL HUMAN EDIT DETECTED** $\rightarrow$ `MANUAL_RECOVERY_REQUIRED`. (Never overwrite human edits).
- $H_{\text{cand}}(T) == H_{\text{base}}(T) \implies$ Recorded as `SKIPPED_NO_CHANGE` (no physical write).

**Interrupted Activation Invariant:** Any interruption before `COMMITTED` leads to deterministic rollback toward baseline. The system **never resumes forward** from a partially activated canonical state.

---

## P. Canonical Transaction State Machine (14 States) `[PLANNED / NOT IMPLEMENTED]`

```
PREPARATION ──▶ STAGING ──▶ ISOLATED_TESTING ──▶ CANDIDATE_VALIDATED ──▶ ACTIVATING ──▶ ACTIVATED ──▶ POST_ACTIVATION_ACCEPTANCE ──▶ FINALIZING ──▶ COMMITTED
      │            │               │                                         │                                      │                     │
      ▼            ▼               ▼                                         ▼                                      ▼                     ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐ FINALIZATION_PENDING
│                                                   ROLLBACK_IN_PROGRESS                                                           │    (Resumable)
└────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────┘
                                                         │
                                        ┌────────────────┴────────────────┐
                                        ▼                                 ▼
                                   ROLLED_BACK          ROLLBACK_FAILED_NEEDS_MANUAL_RECOVERY
                                    (Terminal)                       (Blocking)
```

- **Terminal States (2):** `COMMITTED`, `ROLLED_BACK`.
- **Resumable Pipeline States (9):** `PREPARATION`, `STAGING`, `ISOLATED_TESTING`, `CANDIDATE_VALIDATED`, `ACTIVATING`, `ACTIVATED`, `POST_ACTIVATION_ACCEPTANCE`, `FINALIZING`, `ROLLBACK_IN_PROGRESS`.
- **Resumable Housekeeping State (1):** `FINALIZATION_PENDING` (Acceptance passed 100%; code remains valid; subsequent runs resume specifically to flush archives or purge staging).
- **Recovery-Entry / Blocking States (2):** `ROLLBACK_FAILED_NEEDS_MANUAL_RECOVERY`, `MANUAL_RECOVERY_REQUIRED`. (Block transaction startup until manually resolved).
- **Eliminated Aliases:** Informal abbreviations (`ROLLBACK_FAILED`, `MANUAL_RECOVERY`) are strictly forbidden.

---

## Q. Provenance and Identity Model `[PLANNED / NOT IMPLEMENTED]`

$$\text{ValidationRecord} \xrightarrow{\text{IdentityBuilder}} \text{EvidenceIdentity} + \text{ExecutionIdentity}$$

- **`EvidenceIdentity`:** Mathematical identity of findings `{normalized_evidence_digest, fixture_partition_digest, protocol_definition_digest, objective_definition_digest}`.
- **`ExecutionIdentity`:** Operational execution lineage `{task_id, source_execution_id, receipt_token, execution_environment, lineage_manifest_hash}`.
- **Fixture Lineage Resolution:** `fixture_partition` must resolve to registered fixture lineage manifests binding `{dataset_id, partition_id, scene_manifest_hash, acquisition_metadata_hash}`. A partition string alone is rejected.
- **Analytical Operation Fingerprint:** Derived from registered operation specifications `{library, function, method, estimator, parameters, zero/tie handling}`. Runtime instrumentation is corroborating evidence.
- **Strict-Mode Fails Closed:** Missing or unregistered objectives, protocols, or lineages raise `IncompleteIdentityError`. Zero fallback hashing.

---

## R. Validation Diversity vs Material Re-Analysis `[PLANNED / NOT IMPLEMENTED]`

Two strictly separate predicates:

### 1. `IsIndependentValidationDiversity(R1, R2)`:
Answers: *"Do these records represent distinct, eligible operational executions?"*
- Requires: Level-4 locally verified receipts, distinct `source_execution_id`, distinct eligible `task_id`, distinct `receipt_token`, distinct `normalized_evidence_digest`, complete fixture lineage, and non-origin task.
- Single execution generating multiple records counts as **ONE** validation.

### 2. `IsMaterialReAnalysis(R1, R2)`:
Answers: *"When evaluating the SAME fixture, is the analytical method materially different?"*
- Applicable when `R1.fixture_partition_digest == R2.fixture_partition_digest`.
- Requires: Distinct registered objective or protocol digests, distinct `analytical_operation_fingerprint`, and substantively divergent findings.
- **Operational Boundary:** A same-protocol noisy rerun is discounted for promotion diversity, but **NEVER** blocks the underlying scientific analysis from running. `BLOCK` applies strictly to promotion eligibility.

---

## S. Legacy Record Preservation `[PLANNED / NOT IMPLEMENTED]`

- **Historical Key-Presence Fidelity:** `ValidationRecord._raw_keys` tracks fields present in the original JSON.
- Upon `to_dict()`, unpopulated extension fields are omitted, absent fields remain absent, and explicitly empty fields remain empty.
- Avoids fabricating default strings (`"v1.0"`, `""`) in legacy records.

---

## T. Staging and Safety Boundary `[PLANNED / NOT IMPLEMENTED]`

- **Minimal Staging Tree:** `scratch/staged_generation/` contains only `src/ocean_sentinel/governance/`, empty package `__init__.py`, candidate catalogs, and dedicated staging tests.
- **Complete Exclusion:** Scientific datasets, `dataset.py`, raw radar imagery, checkpoints, HOLDOUT, and Part III are 100% excluded.
- **Subprocess Execution:** Candidate tests run via `uv run pytest -p no:cacheprovider -o addopts=""`.
- **Path Cleanup:** Purges only paths recorded in `staged_inventory.json` resolving strictly inside `scratch/staged_generation/`. Zero symlink traversal.

---

## U. Complete Working Tree State & Pre-Existing User Files `[CURRENT OBSERVED FACT]`

The repository state is **clean except for declared pre-existing user modifications and handoff-task files created during this task**:

### 1. Pre-Existing Tracked Modifications (2 Files): `[CURRENT OBSERVED FACT]`
- `.gitignore` (SHA256: `a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444`)
- `src/ocean_sentinel/ingestion/dataset.py` (SHA256: `f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c`)

### 2. Files Created by This Handoff Task (2 Files): `[GENERATED BY THIS TASK]`
- `docs/governance/CHATGPT_CAO_MASTER_HANDOFF.md` (Existed before: False | Role: Master Continuity Handoff)
- `docs/governance/CHATGPT_CAO_HANDOFF_MANIFEST.md` (Existed before: False | Role: Handoff Manifest)

### 3. Pre-Existing Untracked Repository Files (903 Files): `[CURRENT OBSERVED FACT]`
- `AGENT_GOVERNANCE.md` (1 file)
- `data/` (511 files, including `data/metadata/governance_v2/`, raw datasets, tiled splits, etc.)
- `docs/` (4 pre-existing untracked files: `LESSON_ARCHITECTURE_V2.md`, `OCEAN_SENTINEL_AGENT_LEARNING_FRAMEWORK.md`, `diag04_...`, `diag05_...`)
- `experiments/` (243 files: experimental logs, forensic reports, qualification records)
- `scripts/` (43 files: preflight, audit, dataset preparation scripts)
- `src/` (18 files: `src/ocean_sentinel/governance/*`, ML modules, ingestion helpers)
- `tests/` (82 files: architecture, guardrails, adversarial test suites)
- `uv.lock` (1 file)

### 4. User-Work Protection Invariant: `[CAO DIRECTIVE]`
Files in `PRE_EXISTING_USER_STATE` outside `TASK_ALLOWED_CHANGE_SET` must **NEVER** be overwritten, deleted, rolled back, or altered with `git reset` or `git checkout`. Any unexpected divergence immediately halts mutation $\rightarrow$ `MANUAL_RECOVERY_REQUIRED`.

---

## V. Real-Time Observability Telemetry `[PLANNED / NOT IMPLEMENTED]`

Progress telemetry is planned for `scratch/governance_transaction_progress.json` via atomic writes (`.tmp` + `os.replace`):
- **24 Tracked Fields:** `task_id`, `transaction_id`, `state`, `phase`, `subphase`, `current_action`, `start_time`, `last_heartbeat`, `elapsed_seconds`, `files_completed`, `files_total`, `tests_completed`, `tests_total`, `blockers`, `rollback_state`, `protected_file_guard`, `holdout_access`, `part_iii_access`, `scientific_execution`, `training`, `backward_passes`, `optimizer_steps`, `scheduler_steps`, `gpu_seconds`.
- **Phase-Aware Policy:** Telemetry write failure before mutation blocks startup; during mutation fails closed to rollback; post-acceptance defers to `FINALIZATION_PENDING` without rolling back valid code.

---

## W. Testing Philosophy & Certification Semantics `[CAO DIRECTIVE]`

Future CAOs must enforce these testing distinctions:
1. **Read-Only Inspection:** Reading files without code execution.
2. **Historical Execution Evidence:** Archived logs of past runs.
3. **Baseline Reconnaissance:** Pre-task verification of existing files and hashes.
4. **Targeted Governance Envelope:** Automated guardrail tests (e.g., 157 tests).
5. **Full Repository Regression:** Complete project test suite (must only be claimed when the full repository suite actually runs).
6. **Post-Change Certification:** Measured post-execution audit against active code.

### Oracle Decision Matrix:
- **Expected Negative Control (PASS):** Correct rejection of unsafe/unverified input (`BLOCK-001` through `BLOCK-012`, missing objective/protocol, duplicate evidence, copied receipts) is a **Test PASS** with zero certification penalty.
- **Safety Miss (FAILURE):** System permits unsafe input $\rightarrow$ `NOT_CERTIFIED`.
- **False Positive (FAILURE):** System blocks a compliant task $\rightarrow$ `NOT_CERTIFIED`.

---

## X. Current Governance Negative-Control Scenarios `[HISTORICAL VALIDATED FACT]`

- `SCEN-01` to `SCEN-08`: Benign compliant tasks $\rightarrow$ `PASS`.
- `SCEN-09`: `holdout_partition_request` $\rightarrow$ `BLOCK-001-HOLDOUT` (Test PASS).
- `SCEN-10`: `model_training_command` $\rightarrow$ `BLOCK-006-UNAUTHORIZED_TRAINING` (Test PASS).
- `SCEN-11`: `git_reset_command` $\rightarrow$ `BLOCK-007-DESTRUCTIVE_GIT` (Test PASS).
- `SCEN-12`: `replay_task_promotion` $\rightarrow$ `BLOCK-010-UNVERIFIED_PROVEN_STABLE` (Test PASS).

---

## Y. Current Transaction and Recovery Residual Risks `[PLANNED / NOT IMPLEMENTED]`

The CAO must keep these residual physical boundaries in mind:
1. **Windows Mandatory File Lock Contention:** Background antivirus/indexer holding handles during replacement. (Mitigated by 3 exponential backoff retries; fails closed to `ROLLBACK_FAILED_NEEDS_MANUAL_RECOVERY`).
2. **Drive Cache Power Loss:** Hardware power cut during unbuffered disk writes. (Mitigated by two-slot ping-pong journal and tri-state hash startup audit).
3. **Simultaneous Double-Slot Bitrot:** Both journal slots corrupted simultaneously. (Fails closed to manual recovery).
4. **Local Administrative Privilege Compromise:** Actor with root/admin access modifying `.git/` or `scratch/`. (Level 4 local trust boundary protects against accidental drift and replays, not local root compromise).
5. **Physical Ground Truth vs Mathematical Hash:** A SHA256 digest verifies digital content representation; empirical truth requires sensor calibration and real-world ground truth.

---

## Z. Current Certification Status

- **Baseline Certification:** `CERTIFIED_WITH_LIMITATIONS` `[HISTORICAL VALIDATED FACT]` (Report V2 in `experiments/performance/governance_v2_final_certification_report_v2.md`).
- **Knowledge-Closure Status:** **NOT YET CERTIFIED** `[NOT VERIFIED / PRE-EXECUTION]`. The plan is hardened, but post-execution certification can only be issued from measured test evidence after authorized execution.
- **Possible Future Verdicts:** `CERTIFIED`, `CERTIFIED_WITH_LIMITATIONS`, `NOT_CERTIFIED`. The verdict is never predetermined.

---

## AA. Current AG Prompt and Report Discipline

### Incoming ChatGPT Prompting Rules: `[CAO DIRECTIVE]`
- When authoring prompts for AG, provide self-contained blocks containing complete technical specifications, exact file paths, interfaces, tests, and acceptance criteria.
- Never write vague instructions like "fix the governance system" or "make it work".
- Always instruct AG to pause and report evidence.

### Incoming ChatGPT Report Scrutiny: `[CAO DIRECTIVE]`
- Verify that AG reports exact test counts, execution runtimes, file hashes, and git status.
- If AG claims an invariant passed without showing test output, instruct AG to run the test and display stdout.
- If AG encounters an ambiguity, instruct it to halt and inspect rather than guess.

---

## AB. Recurring Collaboration Failure Patterns to Search For

Future CAOs must proactively watch for these 21 recurring failure patterns:
1. **Premature Approval:** Approving an AG plan because it looks thorough, before auditing schema definitions and repository file paths.
2. **Plan/Repository Divergence:** Plan text referencing non-existent rule IDs, incorrect catalog counts, or outdated enum names.
3. **Treating Prefixes as Provenance:** Believing a task is valid simply because its ID starts with `EXP-` rather than verifying receipt tokens.
4. **Conflating Rejection with Failure:** Treating an expected negative control `BLOCK` as an implementation defect rather than a safety pass.
5. **Staging Bloat for Convenience:** Copying broad project directories into staging to avoid import configuration.
6. **Incomplete Rollback Scope:** Defining rollback for modified files while forgetting newly created files or coordination locks.
7. **Describing Planned State as Installed:** Telling the user that a proposed catalog count (e.g., 121 lessons) is already installed when the disk has 104.
8. **Saying "Pristine Working Tree":** Claiming the working tree is pristine when protected pre-existing user modifications exist.
9. **Rule Bloat:** Creating a new operational `BLOCK` rule for an internal implementation invariant.
10. **Retrieval Controlling Safety:** Forgetting that critical safety rules must bypass similarity ranking via direct safety dispatch.
11. **Severity/Action Conflation:** Assuming critical severity implies an automatic hard block.
12. **Unsafe Fallback Hashing:** Ad-hoc hashing of missing fields rather than failing closed.
13. **Evidence/Execution Identity Conflation:** Treating identical findings on different executions as duplicate executions.
14. **Legacy Serialization Pollution:** Letting extension fields bleed into legacy JSON records upon re-serialization.
15. **Staged Import Leakage:** Running tests against canonical imports rather than staged copies.
16. **Windows Interrupted Replacement Gaps:** Crashing between `os.replace` and journal update leaving disk mutated without journal awareness.
17. **Overclaiming Provenance:** Calling local SHA256 "authenticated" or "tamper-proof".
18. **Treating Finite Tests as Universal Safety:** Overclaiming that a finite test suite proves safety for all unseen states.
19. **Claiming Full Regression on Targeted Suites:** Labeling a 157-test governance envelope a "full repository regression".
20. **Self-Promotion by Rule Author:** Letting a task that introduced a rule validate its own rule to `PROVEN_STABLE`.
21. **Generalizing Task Constraints to Historical Records:** Claiming the project never ran models or diagnostics simply because the current task is plan-only.

---

## AC. Continuous Learning & Rule-Update Process

$$\text{Observation} \longrightarrow \text{Incident} \longrightarrow \text{Lesson} \longrightarrow \text{Invariant / Rule} \longrightarrow \text{Regression Test} \longrightarrow \text{Validation History} \longrightarrow \text{Promotion}$$

- **Incident:** Factual historical record of what failed.
- **Lesson:** Guidance for future agents.
- **Engineering Invariant:** Enforced via code contracts and regression tests.
- **Governance Rule:** Created only when future tasks require an operational response (`BLOCK`, `WARN`, etc.).
- **Quarantine:** New rules start in `REVIEW_REQUIRED`. They cannot self-promote. Promotion requires regression test coverage and multi-task validation history.

---

## AD. Current Next-Step Status & Future CAO Planning Method

### Current Next-Step Status: `[CURRENT OBSERVED FACT]`
- **Lesson Architecture V2 Knowledge Closure:** The architectural plan (`implementation_plan.md`) is complete and hardened.
- **Implementation Status:** **NOT YET AUTHORIZED** (Status remains strictly `PLAN-ONLY`).
- **On-Disk Catalogs:** Remain at baseline (**37 incidents / 104 lessons / 122 rules**).
- **Next Decision Authority:** The incoming ChatGPT CAO must determine whether to recommend execution authorization to the user.

### Planning Guidelines for Incoming CAO: `[CAO DIRECTIVE]`
1. **Inspect Actual Current State:** Do not assume previous plans were executed.
2. **Execute Phase A–G Under Explicit Authorization:** When execution is authorized:
   - Phase A: Baseline snapshot and concurrency lock.
   - Phase B: Minimal staging candidate generation.
   - Phase C: Isolated testing in subprocess.
   - Phase D: Pre-activation hash validation.
   - Phase E: Two-phase per-target sequential activation.
   - Phase F: Post-activation acceptance test suite (157+ tests).
   - Phase G: Archival, cleanup, and handoff synchronization.
3. **Issue Evidence-Based Certification:** Evaluate post-execution test evidence from Phase F to assign the final verdict (`CERTIFIED`, `CERTIFIED_WITH_LIMITATIONS`, `NOT_CERTIFIED`).
4. **Advance to Scientific Roadmap (DIAG-04):** Once governance closure is certified, proceed to the spatial scale diagnostic: **DIAG-04 (Receptive Field & Spatial Scale Compatibility)**.

---

## AE. Handoff Continuity Contract

### To the Incoming ChatGPT CAO:
You are stepping onto the bridge of an ongoing, highly disciplined engineering mission. The foundational decisions, scientific boundaries, and governance invariants established in this document are durable and active.

When you begin the next session, acknowledge:
1. You are the **sole Chief Architecture Officer (CAO)** for Ocean Sentinel.
2. **AG is an implementation and inspection worker**, not the CAO.
3. You have inherited the established project state, architectural constraints, and governance invariants.
4. You will verify current on-disk state before authorizing any state-mutating execution.

---

## AF. Explicit Statement of What Is NOT Verified

In strict adherence to the source-of-truth hierarchy:

| Item / Claim | Epistemic Status | Explanation |
| :--- | :--- | :--- |
| **Projected Catalog Expansion (54/121/124)** | `NOT VERIFIED AS ACTIVE ON DISK` | On-disk canonical files contain 37 incidents, 104 lessons, 122 rules. 54/121/124 is a planned target. |
| **Post-Closure Certification Status** | `NOT VERIFIED` | Pre-execution state; verdict will be computed post-implementation from measured test evidence. |
| **Physical Drive Cache Power-Loss Recovery** | `NOT VERIFIED EMPIRICALLY` | Software fault injection passed; physical power-loss at the hardware controller level cannot be tested locally. |
| **Staged Activation Infrastructure** | `PLANNED / NOT IMPLEMENTED` | `scripts/recover_governance_transaction.py` and ping-pong journal exist in plans, not canonical disk. |
| **Historical Scientific Execution** | `HISTORICAL VALIDATED FACT` | Historical findings (Phases 1–8, DIAG-01..05) are validated from past reports; not re-executed in this task. |

---

## AG. Handoff Integrity and Forensic Audit

An adversarial self-audit of this handoff document confirmed:
- *Are planned states distinguished from implemented states?* Yes; Section L, O, P, Q, and AF explicitly mark knowledge closure as planned/projected.
- *Is working-tree state accurately reported?* Yes; Section U enumerates the 2 tracked modifications, 2 generated handoff files, and 903 untracked files.
- *Is provenance terminology calibrated?* Yes; Section G distinguishes local integrity from external authentication and non-repudiation.
- *Is CAO authority preserved?* Yes; Section A, E, and AE affirm ChatGPT as sole CAO.
- *Is prompt contamination eliminated?* Yes; all dangling instructions and internal tool directives have been removed.

---

### Final Architectural Statement:
**ChatGPT is the sole CAO for Ocean Sentinel.**  
**AG is not the CAO.**  
**This handoff is intended to transfer the established project state, architecture, governance, lessons, constraints, mistakes, and operating rules into a new ChatGPT conversation.**
