# EXPERIMENTAL LESSONS LEARNED & AGENTIC GOVERNANCE MANUAL
**Project:** Ocean Sentinel  
**Authority:** CAIO Scientific Governance  
**Date:** 2026-09-11  
**Status:** FROZEN & DURABLE REFERENCE  

---

## 1. Executive Summary & Purpose

This document establishes permanent operational and scientific lessons derived from the Phase 5A failure analysis and Phase 5B EXP-03 hard-negative baseline training (including the Attempt 001 failure and independent verification stall incidents). 

Future AI agent sessions operating within the Ocean Sentinel project **MUST adhere to the rules, invariants, and failure mitigations codified below**.

---

## 2. Software & Architecture Lessons Learned

### 2.1 Attempt 001 Failure Mode & Validation API Mismatch
* **Observed Incident:** On Phase 5B Attempt 001, after running all 960 Epoch-1 training batches and 180 validation batches (500+ seconds of GPU execution), the script terminated abruptly with:
  ```python
  AttributeError: 'SegmentationMeter' object has no attribute 'summary'
  ```
  This occurred because `scripts/train_exp03.py` called `meter.summary()` instead of `meter.compute()`.
* **Impact:** Zero checkpoints, zero metrics, and zero history entries were persisted for Epoch 1. 100% of the computation was lost.
* **Root Cause:** Incomplete unit testing of the training script's full transaction lifecycle prior to launch. The metric extraction block had never been executed end-to-end against a mock model in preflight.
* **Mandatory Rule:** **Transaction Preflight Rule**. Every new or modified training script must have an automated regression test (e.g., `test_exp03_validation_metric_extraction_regression` and `test_exp03_epoch_transaction_preflight`) that executes the complete transaction chain before any long-running job is launched:
  $$\text{Train Step} \longrightarrow \text{Validation Step} \longrightarrow \text{Meter Compute} \longrightarrow \text{Metric Persistence} \longrightarrow \text{Atomic Checkpoint Serialization} \longrightarrow \text{Reload Verification}$$

### 2.2 Windows Multiprocessing Verifier Failure & The Worker Deadlock
* **Observed Incident:** During independent verification of EXP-03, `scratch/independent_verify_exp03.py` stalled indefinitely at 0 batches completed. PIDs 13996 and 25360 consumed zero GPU and negligible CPU ($<6.5\text{s}$ over hundreds of seconds).
* **Root Cause:**
  1. On Windows, Python uses `spawn` instead of `fork` for multiprocessing. When `DataLoader(num_workers=4)` was initialized without an `if __name__ == '__main__':` entry point guard, child processes repeatedly attempted to import the script, deadlocking the IPC queue.
  2. Even with entry point guards, Windows IPC pipe management for PyTorch DataLoader workers can hang silently when rasterio/GDAL C-extension threads conflict with worker sub-processes.
* **Mandatory Rule:** **Windows Verifier Safety Invariant**.
  1. Every standalone evaluation or verification script on Windows MUST include `if __name__ == '__main__':`.
  2. Standalone evaluation/verification scripts on Windows MUST default to `num_workers=0` (single-process evaluation). Multi-worker data loading is strictly reserved for the main training loop where DataLoader workers are initialized inside a verified runtime context.
  3. Every verifier script MUST emit visible, per-batch or per-interval progress telemetry to stdout (e.g. `[VALIDATION_VERIFY] Batch 20/180 (11.1%)`).
  4. Bounded timeouts or heartbeats must be monitored; silent execution without progress output is classified as a STALL.
  5. Codified in regression test `tests/test_phase_5b_prelaunch_adversarial.py::test_independent_verifier_windows_safety`.

### 2.3 Parameter Count vs. Buffer Count vs. State Dict Entries
* **Observed Incident:** Early Phase 5 reports claimed conflicting parameter counts for `ResNet34UNet`: 24,346,305 vs. 24,365,359.
* **Resolution & Fact:**
  - **Trainable Parameters:** $24,346,305$ (the sum of `p.numel()` for all `p` in `model.parameters()` where `requires_grad=True`).
  - **Non-trainable Buffers:** $19,054$ (BatchNorm `running_mean`, `running_var`, and `num_batches_tracked` across all encoder and decoder layers).
  - **Total State Dict Elements:** $24,346,305 + 19,054 = 24,365,359$.
* **Mandatory Rule:** Always distinguish parameter counts (`model.parameters()`) from state dict tensor elements (`model.state_dict()`). Never label a discrepancy a bug without auditing model buffers.

### 2.4 Checkpoint & Metric Atomicity
* **Observed Incident:** Direct writing of checkpoints (`torch.save(path)`) or JSON metrics (`json.dump(path)`) can leave corrupt, half-written files if interrupted (e.g. Out of Memory, process termination, power loss).
* **Mandatory Rule:** All persistent artifacts MUST be written to a temporary sibling file (e.g., `path.with_suffix(".tmp.<pid>")`) and atomically moved into place using `os.replace` (`atomic_save_checkpoint`, `atomic_write_json`).

---

## 3. Observability & Agentic Operational Lessons

### 3.1 Stale Agent Status vs. Persisted Run State
* **Observed Incident:** IDE agent status indicators or UI task cards occasionally display stale states (e.g., reporting a command as "running" when it has exited, or failing to display active child process stdout).
* **Mandatory Rule:** **Filesystem Ground Truth Rule**.
  - The agent must NEVER treat IDE UI status as authoritative over disk state.
  - The authoritative state of any long-running job is its persisted `run_state.json` and active operating system process tables (`Get-Process -Id <PID>`).
  - Long-running jobs must continuously update a heartbeat timestamp (`last_heartbeat_iso`) in `run_state.json`.

### 3.2 Git-State Reporting & False "Clean Repository" Claims
* **Observed Incident:** Status reports previously declared `EXP03_GIT_AUDIT = CLEAN_NO_STAGING_NO_UNTRACKED_LEAKAGE` when in reality 20+ untracked experiment reports and modified source files existed in the working tree.
* **Mandatory Rule:** **Zero-Ambiguity Git Classification**.
  - A repository is ONLY clean if `git status --porcelain -uall` returns ZERO lines.
  - Every status report MUST run:
    ```powershell
    git status --short
    git status --porcelain -uall
    git diff --cached --name-status
    git diff --name-status
    ```
  - Every modified (`M`) or untracked (`??`) entry must be explicitly classified in the report.
  - Absolutely NO Git staging (`git add`), commits, or pushes without explicit CAIO instruction.

### 3.3 Prompt-Level Cryptographic Splicing Collisions & Multi-Method Provenance Reconciliation
* **Observed Incident:** During EXP-04 execution, a governance check flagged a discrepancy between the candidate manifest hash stated in the prompt (`3867671E639F020CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`) and the actual digest computed by the script (`3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4`).
* **Root Cause & Forensic Discovery:** Forensic alignment proved that characters 17–64 of the prompt hash were character-for-character identical to the 48-character suffix of the teacher baseline checkpoint hash (`9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`). A clipboard buffer collision during prompt compilation spliced the teacher hash suffix onto the candidate manifest prefix.
* **Mandatory Rule:** When a provenance discrepancy occurs between prompt text and repository code/artifacts:
  1. Do NOT assume it is benign or silently rewrite hashes.
  2. Compute SHA-256 independently using three distinct mechanisms (Python, PowerShell, OS certutil).
  3. Inspect filesystem timestamps and git history to prove whether the file on disk was modified.
  4. Search the entire codebase for historical citations of both hashes.
  5. Perform character-by-character alignment to detect multi-line buffer copy errors.
  6. Document the full forensic reconciliation in a durable audit artifact before declaring validity.

---

## 4. Scientific Lessons Learned from EXP-03

### 4.1 The Hard-Negative Precision/Recall Trade-off
* **Observed Behavior:**
  - Hard-negative mining at 12.5% exposure (2 mined empty tiles per batch of 16, drawn from the 400-tile candidate pool) caused a massive drop in false alarms:
    - Clean-water FAR dropped from $20.09\%$ to $0.33\%$ ($-98.4\%$).
    - Significant FAR dropped from $10.56\%$ to $0.33\%$ ($-96.9\%$).
    - Total FP pixels dropped from $2,327,942$ to $79,742$ ($-96.6\%$).
  - However, this intervention also degraded positive detection performance:
    - Recall dropped from $0.78488$ to $0.77287$ ($-1.53\%$ relative, failing the $\ge 0.80000$ gate).
    - Validation IoU dropped from $0.71691$ to $0.70435$ ($-1.75\%$ relative, failing the $\ge 0.71731$ non-inferiority gate).
    - Precision rose from $0.85138$ to $0.88820$ ($+3.68$ percentage points).
* **Mechanistic Finding (Prediction Mass & Sparsity Analysis):**
  - Validation tiles with predicted positive pixels dropped from $1,361$ to $826$ (out of $1,053$ ground-truth positive tiles).
  - In EXP-03, **227 genuine oil-spill tiles were completely dropped** (predicted 0 positive pixels), whereas the EXP-01 baseline detected oil in every one of them.
  - Total predicted positive pixel mass shrank by $10.4\%$ (from $15.67\text{M}$ to $14.04\text{M}$ pixels).
  - False negative pixels increased by $+866,016$ pixels ($+30.9\%$).
* **Candidate Pool Skew Finding:**
  - The 400-candidate pool exhibits extreme skew: median FP pixels is $2,090$, but the mean is $22,303$.
  - 45 candidates ($11.2\%$) have $\ge 50,000$ FP pixels, and 32 ($8.0\%$) have $\ge 100,000$ FP pixels (up to entire 262,144-pixel tiles).
  - Exposing the model to these full-tile false positive penalties at a 12.5% rate every single batch forced the network weights to strongly suppress low- and medium-confidence activations, causing fine boundaries and subtle oil slicks to collapse into background.

### 4.2 Scientific Integrity: Gate Failure vs. Scientific Failure
* **Critical Principle:**
  - EXP-03 is **NOT** a "bad experiment" or a "scientific failure".
  - It was executed strictly under preregistered protocol, completed 10/10 epochs deterministically, independently reproduced all metrics across all 2,880 validation tiles, and rigorously preserved all firewalls.
  - It represents an **ACCEPTANCE-GATE FAIL**, but a **SCIENTIFIC SUCCESS**: it definitively disproved the hypothesis that $12.5\%$ hard-negative exposure is Pareto-optimal without recall loss.
  - This empirical finding directly guides the precise single-variable formulation of EXP-04.

### 4.3 Scientific Lessons Learned from EXP-04: Exposure Rate vs. Severity Outliers
* **Observed Empirical Behavior:**
  - Halving hard-negative exposure from $12.5\%$ to $6.25\%$ ($15\text{ standard} + 1\text{ mined}$) recovered positive prediction mass ($+248,040\text{ pixels}$) and lifted validation Recall from $0.77287$ to $0.78230$ ($+0.943\text{ pp}$), while retaining $>94\%$ of the false-alarm reduction (Clean-Water FAR remained at $0.55\%$).
  - However, positive tile dropout remained essentially invariant: $231$ positive tiles dropped in EXP-04 vs. $227$ in EXP-03.
* **Mechanistic Discovery:**
  - Adjusting exposure frequency modulates the *quantity* of negative gradients, but does not alter the *nature* of the candidates.
  - The frozen candidate manifest contains $45$ extreme candidates exceeding $50,000$ false positive pixels (including full-tile $262,144$-pixel errors). When an extreme candidate is sampled into a mini-batch, the loss function penalizes the entire spatial receptive field. This periodic whole-feature suppression drives model weights to erase subtle, low-contrast oil slicks.
  - **Conclusion:** Exposure frequency reduction alone is insufficient to resolve positive tile dropout. The intervention must be paired with candidate severity capping.

### 4.4 Candidate Severity Capping as an Orthogonal Controlled Intervention
* **Distributional Grounding:**
  - In the 400-candidate pool, $11.25\%$ of candidates ($45$ tiles $> 50,000$ px) account for **$80.35\%$** of all false positive pixel mass ($7,168,600$ out of $8,921,439$ pixels).
  - Capping the pool at $\le 50,000$ FP pixels purges the destructive extreme tail while retaining **$88.75\%$** of candidate variety ($355$ tiles) and **$91.94\%$** of parent-scene geographic diversity ($251 / 273$ scenes).
  - Because no scene has more than 2 candidates in the post-cap pool, severity capping does not create geographic clustering or scene concentration.
  - This sets the scientific foundation for EXP-05.

### 4.5 Scientific Lessons Learned from EXP-05: Candidate Severity Capping & Positive Tile Dropout
* **Observed Empirical Behavior:**
  - Restricting the hard-negative pool to candidates with $\text{fp\_pixels} \le 50,000$ ($355$ retained candidates) while keeping mined exposure fixed at $6.25\%$ ($15\text{ standard} + 1\text{ mined}$) broke the positive tile dropout stagnation:
    - Completely dropped positive tiles fell from $231$ (EXP-04) and $227$ (EXP-03) down to **$203$** in EXP-05 (an immediate recovery of **$28$ positive oil-slick tiles**, representing a **$12.12\%$ reduction** in complete dropouts).
    - Detected positive tiles increased from $822$ (EXP-04) to **$850$** (EXP-05).
    - Total predicted positive pixel mass increased to **$14,315,101\text{ pixels}$** ($+23,200\text{ px}$ vs EXP-04, $+271,240\text{ px}$ vs EXP-03).
    - False-alarm suppression remained virtually unaffected: Clean-Water FAR was **$0.49\%$** ($-97.56\%$ vs EXP-01 baseline) and Significant FAR was **$0.49\%$** ($-95.36\%$ vs baseline). Total FP pixels on empty tiles was $129,041$.
  - However, global best validation metrics narrowly missed the preregistered non-inferiority gates:
    - Validation Recall: $0.78227$ (gate $\ge 0.78500$, delta $-0.00273$).
    - Validation IoU: $0.70813$ (gate $\ge 0.71731$, delta $-0.00918$).
* **Mechanistic Finding & Epistemic Boundaries:**
  - The evidence is **consistent with the hypothesis** that extreme-tail candidates ($> 50,000\text{ FP pixels}$) exert disproportionate gradient penalties that drive complete positive tile dropout. Suppressing the extreme tail recovered $28$ previously erased oil slicks without degrading false alarm resistance.
  - **Epistemic Discipline:** We do *not* claim that extreme candidates "proved to be the sole cause of dropout" (correlation $\neq$ causation). Severity capping acts as tail suppression, not guaranteed elimination of gradient domination.
  - In addition, while dropout recovered, overall pixel-level recall and IoU did not surpass EXP-04's global peak ($0.70910$). This indicates that subtle boundary erosion on retained tiles is governed by broader negative exposure dynamics beyond the extreme tail alone.

### 4.6 Universal Governance & Scientific Integrity Invariants
The following twenty governing principles must be upheld across all future phases:
1. **AG UI is not ground truth:** Always query OS process tables and disk files; never trust static UI cards.
2. **Filesystem/process/log evidence is authoritative:** `run_state.json`, `training.log`, and process telemetry take precedence over all else.
3. **Durable run_state is mandatory:** All long-running processes must maintain a persistent, heartbeated `run_state.json`.
4. **Windows verifiers require main guard + num_workers=0 by default:** Standalone verifiers on Windows must run single-process with explicit progress telemetry to prevent IPC worker hangs.
5. **Never trust unverified metric API assumptions:** The exact method names and signatures (`SegmentationMeter.compute()`) must be confirmed against live source code.
6. **Epoch transactions must be tested before long runs:** Automated transaction preflight tests (`test_epoch_transaction_preflight`) must verify forward, backward, optimizer step, metric computation, and serialization end-to-end.
7. **Preserve failed attempts:** Failed runs (e.g. Attempt 001) must have their logs and states preserved under immutable diagnostic records; never delete failure evidence.
8. **Verify hashes from actual files:** Cryptographic hashes must be calculated dynamically via SHA-256 tools on disk, never transcribed from previous markdown reports.
9. **Never manually splice/copy hashes between prompts:** Multi-method provenance verification is required whenever a text-vs-disk hash mismatch appears.
10. **Distinguish trainable parameters from buffers:** Trainable parameters ($24,346,305$), non-trainable buffers ($19,054$), and total state dict elements ($24,365,359$) must be strictly distinguished.
11. **Part III remains closed:** Part III is never development data and must remain strictly firewalled behind cryptographically enforced pre-execution gates.
12. **Recompute arithmetic:** Never copy delta or percentage calculations from previous reports; compute all differentials from authoritative raw values.
13. **One-variable experiments must truly have one changed variable:** When altering a single hyperparameter or loss component, all other 24 experimental parameters must remain strictly frozen.
14. **Do not turn a gate failure into a pass:** A valid scientific experiment that fails a gate remains a valid, informative result. Never manipulate thresholds post-hoc.
15. **Do not overstate causality:** Distinguish observed facts, calculated facts, inferences, and testable hypotheses. Use calibrated terminology ("consistent with", "supports the hypothesis").
16. **Candidate severity capping must not silently change other sampling semantics:** Filtering must maintain uniform replacement sampling probability across the surviving pool with audited coverage.
17. **A reduction in dropout does not necessarily mean a proportional reduction in FN mass:** As demonstrated in Phase 5G, recovering complete tile dropouts shifts tiles into the partial-detection regime, where internal and edge FN mass remains substantial.
18. **Do not optimize validation subgroup definitions or intervention choice through repeated post-hoc searching:** Hypothesis formulation must be derived from population-level mechanistic understanding, not empirical validation overfitting.
19. **Positive failure analysis must separate complete dropout from partial under-segmentation:** Complete dropouts ($< 20\%$ of FN mass) and boundary erosion ($> 80\%$ of FN mass) stem from distinct error dynamics requiring distinct diagnostic framing.
20. **Never confuse 'mechanistically plausible' with 'experimentally proven':** A mechanistic hypothesis remains unproven until validated through a controlled, preregistered, non-inferior intervention.

### 4.7 Scientific Lessons Learned from Phase 5G: The Dual Structure of Positive Detection Failures
* **Empirical Population Decomposition:**
  - Forensic evaluation across all $1,053$ GT-positive validation tiles revealed that **False Negative pixels dominate total error by $2.08:1$ over False Positives** ($3,514,098\text{ FN px}$ vs. $1,689,666\text{ FP px}$ in EXP-05).
  - Crucially, False Negative mass is divided into two structurally distinct categories:
    1. **Complete Tile Dropouts (19.1% of FN mass):** $203$ tiles ($671,336\text{ FN px}$). These are primarily small oil slicks ($< 2,712$ px) whose prediction probabilities are deeply suppressed ($< 0.10$).
    2. **Partial Detection & Boundary Under-Segmentation (80.9% of FN mass):** $850$ detected tiles account for **$2,842,762\text{ FN pixels}$**.
  - Slicks with area $> 19,367\text{ pixels}$ account for **$66.2\%$ of all FN pixels in the entire validation set ($2,327,503\text{ px}$)**, despite suffering only $7$ complete dropouts. The model reliably finds large spills but truncates diffuse margins and fine filaments due to background negative gradient dominance.
* **Non-Clustering Probability Distribution:**
  - Positive pixel probabilities are strictly bimodal: complete dropouts have near-zero probabilities ($< 0.05$), while detected spills have confident foreground activations ($> 0.70$ on cores, trailing off sharply at edges). Only $27$ out of $1,053$ tiles have mean probability in the $[0.10, 0.35]$ transition zone.
  - Therefore, adjusting decision threshold $\tau$ alone cannot bridge the recall gap without destabilizing false alarm rates.
* **Design Directive for EXP-06:**
  - Because hard-negative mining has already reduced Clean-Water FAR to $0.49\%$ ($-97.6\%$ vs baseline, well within the $< 5.00\%$ gate), the primary scientific opportunity is **rebalancing positive vs. negative gradients** during training.
### 4.8 Scientific Lessons Learned from Phase 5H (EXP-06): Successful Recovery via Positive-Class BCE Reweighting
* **Empirical Confirmation of the Phase 5G Hypothesis:**
  - Setting positive-class BCE weight to $\text{pos\_weight} = 2.0$ (while freezing all other 24 experimental parameters) successfully resolved the positive under-segmentation deficit identified in Phase 5G.
  - Validation Recall rose from $0.78227$ (EXP-05) to **$0.81153$** (+2.926 pp / +3.74% relative gain), comfortably clearing the $\ge 0.78500$ acceptance gate.
  - Validation IoU reached **$0.72168$** (+1.355 pp / +1.91% relative gain over EXP-05's $0.70813$), surpassing the preregistered non-inferiority gate ($\ge 0.71731$, margin $+0.00437$) and matching the canonical EXP-01 baseline operating point ($0.72231$ at $\tau=0.22$, $\Delta = -0.00063$ / $-0.063\text{ pp}$).
  - **All five preregistered acceptance gates passed simultaneously** at the global best checkpoint (Epoch 9) for the first time in the Phase 5 series.
* **Mechanistic Forensic Validation:**
  - Total False Negative pixels dropped by **$472,351\text{ px}$ ($-13.44\%$)**, from $3,514,098$ in EXP-05 to $3,041,747$ in EXP-06.
  - **Partial Detection FN Mass:** Reduced from $2,842,762\text{ px}$ to $2,572,918\text{ px}$ ($-269,844\text{ px}$, $-9.49\%$), providing empirical evidence consistent with the Phase 5G hypothesis that doubling positive BCE gradient pressure counteracts background negative pressure along slick boundaries and restores eroded slick margins.
  - **Complete Tile Dropouts:** Reduced from $203$ tiles in EXP-05 to **$174$ tiles** in EXP-06 (an additional $29$ positive tiles recovered; $-14.29\%$). Dropout FN mass dropped from $671,336\text{ px}$ to $468,829\text{ px}$ ($-202,507\text{ px}$, $-30.16\%$).
* **Preservation of False-Alarm Suppression:**
  - Crucially, the positive reweighting did *not* cause an uncontrolled false-alarm rebound. Clean-Water FAR remained at **$0.55\%$** (vs $0.49\%$ in EXP-05 and $20.09\%$ in EXP-01 baseline, maintaining a **$97.3\%$ reduction in clean-water false alarms**).
  - Significant FAR remained at **$0.55\%$** (vs $10.56\%$ in baseline, a **$94.8\%$ reduction**).
  - Clean-Water FP pixels on empty validation tiles dropped to **$113,187\text{ px}$** (lower than EXP-05's $129,041\text{ px}$, and $-75.71\%$ vs baseline's $465,950\text{ px}$; global validation FP also dropped from $2,328,613\text{ px}$ to $2,009,530\text{ px}$, a $-13.70\%$ reduction).
* **Loss Balance Invariant:**
  - The audited BCE-to-Dice loss ratio evolved from $0.054$ (Epoch 1) to $0.271$ (Epoch 9) and $0.276$ (Epoch 10). The BCE term never numerically dominated the Dice term, preserving topological segmentation stability.

### 4.9 Definitive Acceptance-Contract, Metric Semantics, and Audit Lessons
1. **Acceptance-gate names must exactly match mathematical definitions:** Shorthand names like "Total FP Pixels" for a metric computed solely over empty tiles creates severe ambiguity when contrasted with the global validation confusion matrix FP ($2,009,530\text{ px}$). Canonical documents must explicitly use "Clean-Water FP Pixels (Empty Tiles)" ($113,187\text{ px}$) to align with the original preregistered contract.
2. **Total validation FP and clean-water FP are distinct quantities:** Total validation FP ($2,009,530\text{ px}$) spans all $2,880$ validation tiles (including true slick boundary dilation of $1,896,343\text{ px}$), whereas clean-water FP ($113,187\text{ px}$) spans exclusively the $1,827$ empty ocean tiles. The mathematical partition $\text{Clean FP} + \text{Positive FP} == \text{Total FP}$ ($113,187 + 1,896,343 = 2,009,530$) must be formally maintained.
3. **Every gate must be traceable back to the original preregistration:** Audits must establish an unbroken five-stage trace: `ORIGINAL CONTRACT` $\rightarrow$ `IMPLEMENTATION` $\rightarrow$ `TRAINING ARTIFACT` $\rightarrow$ `INDEPENDENT VERIFIER` $\rightarrow$ `FINAL REPORT`. A gate is unverified until all five stages agree.
4. **Narrative PASS statements cannot substitute for contract verification:** A report claiming "5/5 PASS" is invalid until every underlying gate quantity is traced to its original preregistered formula and recomputed from authoritative raw integers.
5. **Equality of two metric values does not imply equality of definitions:** Clean-Water FAR and Significant FAR both equaled $0.55\%$ in EXP-06, but their definitions are distinct ($\ge 1\text{ px}$ vs $\ge 100\text{ px}$). The equality was purely incidental to model convergence (all 10 false alarm tiles happened to have $\ge 100\text{ px}$), whereas early epochs demonstrated expected divergence (e.g. 13.52% vs 9.63% in Epoch 1).
6. **Generate hashes programmatically:** Never copy or transcribe SHA-256 strings manually. Programmatic on-disk calculation is mandatory, and the earlier index-28 typo (`E` vs `B`) stands as a permanent cautionary example.
7. **Distinguish execution lifecycle states:** Differentiate `LAUNCHED`, `RUNNING`, `COMPLETED`, and `INDEPENDENTLY VERIFIED`. Interim status notes ("is running") must never contaminate permanent verification records.
8. **Scope scientific claims to the evidence actually audited:** Use calibrated, evidence-grounded scientific language ("provides strong evidence consistent with the Phase 5G hypothesis") rather than claims of unproven direct causation.

### 4.10 Scientific & Governance Lesson: Metric Scope Is Part of Scientific Correctness
- **Core Principle:** A valid numerical metric can still be scientifically misleading if its evaluation population and scope are not explicitly declared. Metric scope is an essential component of scientific correctness.
- **Incident Analysis (Phase 6 External Benchmark):**
  1. **Stratum vs. Global Segmentation Scope:** On the Trujillo Part III external benchmark, the frozen EXP-06 model achieved an Oil-stratum macro mean IoU of `0.74486` ($74.49\%$). Presenting this value as an unqualified "overall external benchmark IoU" or "global Part III IoU" is scientifically misleading because the metric evaluates only the 150 scenes in the `Oil` stratum, omitting the $130,502,095$ false-positive pixels generated over the `Lookalike` stratum. When evaluated over the full benchmark population ($N=450$ scenes), the true global pixel IoU is `25.21%`.
  2. **Scene FAR vs. Pixel Specificity:** Describing the clean-water Primary Scene FAR of `4.67%` ($7/150$ scenes with $FP>0$) or clean scene rejection rate of `95.33%` ($143/150$ scenes with $FP=0$) as "specificity" or "95.33% true negative rate" conflates a scene-level binomial rate with a pixel-level metric ($TN / (TN + FP) = 99.985\%$).
  3. **Evidence-Bounded vs. Speculative Causal Claims:** Causal assertions regarding lookalike discrimination (e.g. claiming single-pass 2D SAR cannot discriminate lookalikes without multi-temporal coherence or meteorological data) or polarization mechanics (claiming the model requires Channel 0 to correspond to lower backscatter) exceed empirical observation. Benchmark reporting must state observations strictly: "The frozen single-pass 2D SAR configuration showed substantial vulnerability to the benchmark Lookalike class" and "The frozen model exhibited strong sensitivity to the tested channel ordering".
- **Permanent Mandatory Rules:**
  1. **Mandatory Scope Labeling:** Every segmentation metric must explicitly declare its stratum scope (e.g., "Oil-stratum macro mean IoU" vs "Whole-benchmark global pixel IoU").
  2. **Scene FAR vs Specificity Firewall:** Scene FAR ($\mathbb{I}(FP > 0)$) and pixel-level specificity ($TN / (TN + FP)$) must never be interchanged or labeled synonymously.
  3. **Evidence-Bounded Causal Bounds:** Reports must state findings strictly bounded by empirical evidence under the fixed protocol, avoiding unsubstantiated claims of physical causation or unproven necessity.
  4. **Signed Delta vs. Absolute Gap:** Directional comparisons between experimental conditions or channel mappings (e.g. Mapping A vs Mapping B) must be labeled explicitly as 'Signed Delta (A − B)' rather than 'Gap' or '|A − B|' when signed directional differences are displayed.

### 4.11 Scientific & Governance Lesson: Permanent Protection of External Test Benchmarks (Rule 38)
- **Core Principle (Rule 38):** **External test benchmarks are permanently protected from model-selection feedback once officially evaluated.**
- **Rationale & Incident Analysis:**
  Following the official completion of Phase 6 on the Trujillo Part III external benchmark, the evaluation established both strong morphological transfer on true slicks (Oil-stratum macro mean IoU $74.49\%$) and severe vulnerability to natural lookalikes (Lookalike Primary Scene FAR $90.67\%$). The immediate temptation in post-evaluation machine learning is to tune thresholds, adjust loss weights, or select model architectures specifically to drive down the external lookalike score. Doing so would destroy the external validity of Trujillo Part III and convert it into a contaminated test set.
- **Mandatory Operating Rules:**
  1. **Strict Read-Only Quarantine:** All raw Part III images, masks, and Phase 6 prediction outputs are strictly quarantined from future training, validation, checkpoint selection, threshold calibration, and candidate filtering.
  2. **No Direct Optimization Against External Errors:** No candidate model or intervention may be accepted or rejected based on performance on Trujillo Part III.
### 4.12 Scientific & Data Governance Lessons: Phase 7A Data Protocol Foundation
- **Core Principle:** Development environments must enforce absolute quarantine of external benchmarks, strict parent-scene contamination firewalls, empirical baseline coupling, and precise separation between source descriptions, physical interpretations, and authorized training roles.
- **Key Lessons Codified:**
  1. **Documented Training-Distribution Deficiency vs. Unproven Causal Claims:** Never claim "root cause is proven to be data absence" or "architecture is not the bottleneck" without controlled empirical evidence. The exact evidence establishes: *"A major directly observed training-distribution deficiency is the absence of dedicated Lookalike and Clean-Water scenes from the Part-I development corpus."* Furthermore, *"There is currently insufficient evidence to justify architectural intervention before addressing the documented training-distribution deficiency."*
  2. **Three-Tier Dataset Semantic Firewall:** For every candidate proxy sample, explicitly distinguish:
     - **(A) Source-Provided Label / Description:** What the dataset authors actually documented.
     - **(B) Physical Interpretation:** What physical phenomenon the signature represents.
     - **(C) Training Role:** How the sample is authorized to be used (`CONFIRMED_NEGATIVE`, `DEVELOPMENT_ONLY`, `AMBIGUOUS_EXCLUDE`, `REJECTED`).
     Never silently convert (A) into (B), and never silently convert (B) into (C). Only `CONFIRMED_NEGATIVE` may enter ordinary negative training.
  3. **Parent-Scene Level Contamination Firewall:** Bounding-box or patch-level exclusion alone is insufficient. If any candidate patch from a multi-patch parent scene intersects a quarantined benchmark scene (such as Trujillo Part III), the **entire parent scene** must be marked `REJECTED` and excluded at the scene level to eliminate co-scene radiometric and contextual leakage.
  4. **Empirical Baseline Coupling for Acceptance Floors:** Acceptance thresholds must never be chosen arbitrarily (e.g. asserting "IoU >= 0.7200" in a vacuum). All candidate acceptance floors must be derived directly from the newly frozen DEV baseline, defining explicit effect sizes, regression tolerances, and non-regression constraints on the exact evaluation population.
  5. **Unit and Denominator Integrity:** Never mix parent scenes, tiles, and candidate regions. An evaluation unit must be explicitly matched to its denominator: Tile FAR uses the total tile denominator ($N=1,827$ empty tiles), whereas Scene FAR uses the total parent scene denominator.
  6. **Mandatory Split Freeze Sequence:** Splits must be constructed, verified for zero spatial connected component leakage, written to manifest, hashed with SHA-256, and frozen **BEFORE** baseline evaluation. The manifest must never be adjusted after observing baseline results.
  7. **Governance Rule 39 (Prerequisite Audit Gate):** *"No downstream artifact may be generated from an upstream protocol artifact whose required prerequisite audits are incomplete."* Downstream manifests or baseline runs must not be created or executed until upstream source-data, contamination, leakage, and clustering audits are certified complete with durable, machine-readable records.
  8. **Governance Rule 40 (Sequential State-Mutating Process Constraint):** *"One active state-mutating experiment or audit process per AG task is the default. Parallel execution requires explicit authorization and demonstrated non-conflicting write scopes."* Asynchronous background job overlap during protocol setup introduces process-integrity risks; all auditing and freezing stages must be executed serially with verified completion gates.

---

## 5. Summary Checklist for Future Experiments

Before launching any future experiment:
- [ ] Automated preflight tests pass (`pytest tests/`).
- [ ] End-to-end epoch transaction simulated and verified on CPU.
- [ ] Independent verifier adheres to Windows safety invariants (`num_workers=0`, `if __name__ == '__main__':`).
- [ ] Checkpoint directory isolated and clean.
- [ ] Candidate manifests, teacher checkpoints, and data splits verified by SHA-256.
- [ ] Part III firewall rigorously asserted (zero Part III tiles in training or validation).
- [ ] Real-time telemetry (`run_state.json`) with heartbeats and batch progress enabled.
- [ ] Candidate pool sampling audits verify deterministic replacement coverage.
- [ ] FN decomposition verifies balance between complete dropout and boundary erosion.


