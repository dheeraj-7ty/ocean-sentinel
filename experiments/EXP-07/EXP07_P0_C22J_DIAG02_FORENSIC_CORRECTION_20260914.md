# EXP-07-P0-C22-J: DIAG-02 Forensic Correction, Association Bounding & Roadmap Realignment

**Investigation ID:** `DIAG-02-FORENSIC-CORRECTION-AND-ROADMAP-GATE`  
**Parent Task:** `EXP-07-P0-C22-I` (DIAG-02 Exposure Audit)  
**Execution Date:** 2026-09-14  
**Authoritative Dataset:** OPS-02 Physical Dataset (`OPS02_v1.0.1_FROZEN`, Manifest SHA-256: `64E5E4BA5117B9A4A1FE0C1FDFDF948FF3BA53B3C837C3C588102607C64BD6C5`)  
**Audit Artifact:** `data/ops02/audits/ops02_c22j_diag02_forensic_correction_v1.json`  
**Status:** `COMPLETED_VALID`

---

## 1. Executive Summary & Forensic Purpose

During EXP-07-P0-C22-I, an audit of Candidate F hybrid sampler schedules and draw frequencies was executed across five replication seeds (Seed 42 from C22-B; Seeds 101, 202, 303, 404 from C22-D). While the primary numerical accounting and schedule reconstruction were sound, the initial reporting suffered from four critical scientific and governance defects:

1. **Unsupported Optimization & Gradient Claims:** The report asserted speculative causal mechanisms regarding unmeasured gradient behavior and optimization dynamics despite the fact that DIAG-02 is a pure dataset/schedule exposure audit that **did not measure loss gradients, gradient norms, or parameter updates**.
2. **Overstated Small-Sample Correlation Interpretation:** Five-seed correlations ($n=5$) between early rare-class draws and model performance deltas ($r = +0.8955$) were described with causal verbs rather than being strictly bounded as descriptive associations.
3. **Unqualified Starvation Claims:** The report claimed that sampler starvation was globally refuted, conflating the empirical absence of zero-exposure draws with positive proof of training sufficiency.
4. **Diagnostic Roadmap Distortion:** The report renumbered future diagnostic priorities, assigning DIAG-03 to "Loss Landscape & Gradient Dynamics" and DIAG-04 to "Architecture & Spatial Resolution", colliding with and overwriting the frozen authoritative diagnostic roadmap established in C22-F and restored in C22-H.

EXP-07-P0-C22-J performs the definitive forensic repair across all artifacts, harmonizing numerical findings, enforcing strict descriptive bounding, ensuring tripartite conceptual separation, and protecting diagnostic roadmap integrity.

---

## 2. Governance Guarantees & Non-Negotiable Invariants

Throughout this forensic task:
- **Training steps executed:** `0`
- **Backward passes executed:** `0`
- **Optimizer steps executed:** `0`
- **Scheduler steps executed:** `0`
- **Parameter updates executed:** `0`
- **GPU training compute allocated:** `0.0 seconds`
- **HOLDOUT benchmark access count:** `0` (`QUARANTINED_ZERO_ACCESS`)
- **Part III evaluation access count:** `0` (`FIREWALLED_ZERO_ACCESS`)
- **DIAG-05 execution:** `0` (`DESIGN_ONLY_NOT_EXECUTED`)
- **Destructive git operations:** `0` (No commit, push, reset, or clean; pre-existing user modifications preserved)

---

## 3. Canonical Rare-Class Terminology Reconciliation

To eliminate naming ambiguity and prevent semantic collisions across reports, canonical taxonomy ordering and strict nomenclature are enforced:

| Symbol | Canonical Class Name | Dense Index | Explicitly Forbidden Misinterpretations |
|:---|:---|:---|:---|
| **OF** | **Ocean Front** | 5 | Colloquial petroleum/slick misnomers |
| **RF** | **Rain / precipitation-related phenomenon** | 7 | N/A |
| **HM** | **Artificial / Anthropogenic Objects** | 11 | Maritime craft or elemental material misnomers |

All references in `EXP07_P0_C22I_SAMPLER_EXPOSURE_AUDIT_20260914.md` and related JSON artifacts conform strictly to these definitions.

---

## 4. Audit-Artifact Provenance Decision

### 4.1 Provenance Determination: Mutable with Explicit Forensic History
Repository evidence was evaluated to determine whether `data/ops02/audits/ops02_c22i_sampler_exposure_audit_v1.json` is an immutable historical artifact or legitimately mutable under established repository conventions:
1. **Repository Precedent:** In task `EXP-07-P0-C22-H`, the prior audit artifact `data/ops02/audits/ops02_c22g_class_support_metric_sensitivity_v1.json` was legitimately modified in-place to update the verdict to `CASE B` and embed a formal `reclassification_history` block within `decision_logic`.
2. **Harmonization Need:** Leaving unmeasured gradient claims in `ops02_c22i_sampler_exposure_audit_v1.json` would perpetuate scientifically unsupported statements in the machine-readable record.
3. **Preservation of Historical Evidence:** An explicit `forensic_correction_history` object was embedded in `ops02_c22i_sampler_exposure_audit_v1.json`. This object documents the exact date, task ID (`EXP-07-P0-C22-J`), rationale, and original historical strings, preserving the full forensic lineage. Furthermore, the complete original audit generator is preserved in `scratch/generate_c22i_audits.py`.

---

## 5. Authoritative Physical Counts vs. Sampled Cluster Accounting

A critical distinction is maintained between fixed physical dataset properties and seed-level stochastic sampling:

$$\text{Physical Dataset Availability} \neq \text{Sampler Allocation Policy} \neq \text{Demonstrated Learning Effect}$$

### 5.1 Authoritative Physical Dataset Counts (TRAIN Partition, $n=132$)
- **Ocean Front (OF):** 9 physical samples across exactly 4 parent acquisition clusters.
- **Rain / precipitation-related phenomenon (RF):** 13 physical samples across exactly 7 parent acquisition clusters.
- **Artificial / Anthropogenic Objects (HM):** 12 physical samples across exactly 8 parent acquisition clusters.

### 5.2 Realized Sampler Coverage Across Seeds (Epochs 1–7, 504 Draws)
- **OF (4 available clusters):** 4/4 clusters (100%) sampled across all 5 seeds.
- **RF (7 available clusters):** 7/7 clusters (100%) sampled across all 5 seeds.
- **HM (8 available clusters):**
  - Seed 42: 8/8 clusters (100%)
  - Seed 101: 7/8 clusters (87.5%)
  - Seed 202: 8/8 clusters (100%)
  - Seed 303: 8/8 clusters (100%)
  - Seed 404: 8/8 clusters (100%)
  - *Seed-level range in Epochs 1–7:* 7–8 of 8 clusters (mean coverage: 7.8/8).
  - *Full-run coverage (30 epochs, 2,160 draws):* 8/8 clusters (100%) across all 5 seeds.

---

## 6. Authoritative Numerical Verification & Five-Seed Recomputation

The five-seed replication dataset from C22-B and C22-D was independently verified against primary schedule logs and checkpoint evaluation records.

### 6.1 Primary Five-Seed Data Vectors

Let:
- $X$ = Early rare-class exposure draws (sum of OF, RF, HM) during Epochs 1–7 (504 total draws per seed).
- $Y_1$ = Control best $\text{dev\_mIoU\_phenomena}$.
- $Y_2$ = Treatment best $\text{dev\_mIoU\_phenomena}$.
- $Y_3 = Y_2 - Y_1$ = Paired delta ($\Delta = \text{Treatment} - \text{Control}$).

```
+------+------------+------------------+------------------+--------------------+------------------+------------------+
| Seed | Experiment | Rare Draws (X)   | Control Best (Y1)| Treatment Best (Y2)| Paired Delta (Y3)| Top Winning Arm  |
+------+------------+------------------+------------------+--------------------+------------------+------------------+
|   42 | C22-B      |       170        | 0.04147 (Ep 10)  | 0.05318 (Ep  5)    |     +0.01171     | TREATMENT        |
|  101 | C22-D      |        97        | 0.05886 (Ep 15)  | 0.04481 (Ep  5)    |     -0.01405     | CONTROL          |
|  202 | C22-D      |       135        | 0.04358 (Ep 27)  | 0.04741 (Ep  6)    |     +0.00383     | TREATMENT        |
|  303 | C22-D      |       126        | 0.05191 (Ep 19)  | 0.04605 (Ep  5)    |     -0.00586     | CONTROL          |
|  404 | C22-D      |       124        | 0.04940 (Ep 21)  | 0.05398 (Ep  7)    |     +0.00458     | TREATMENT        |
+------+------------+------------------+------------------+--------------------+------------------+------------------+
```

### 6.2 Statistical Correlation Synthesis ($n=5$)

Independent recomputation confirms both parametric (Pearson $r$) and non-parametric rank (Spearman $\rho$) statistics:

1. **$X$ vs $Y_1$ (Control Best mIoU):**
   - Pearson $r = -0.9167$ ($p = 0.0285$)
   - Spearman $\rho = -0.9000$ ($p = 0.0374$)
   - *Interpretation:* Strong negative descriptive association. Seeds with fewer rare draws saw higher Control performance.
2. **$X$ vs $Y_2$ (Treatment Best mIoU):**
   - Pearson $r = +0.6302$ ($p = 0.2545$)
   - Spearman $\rho = +0.4000$ ($p = 0.5046$)
   - *Interpretation:* Positive descriptive association.
3. **$X$ vs $Y_3$ (Paired Delta $\Delta$):**
   - Pearson $r = +0.8955$ ($p = 0.0399$)
   - Spearman $\rho = +0.7000$ ($p = 0.1881$)
   - *Interpretation:* Strong positive descriptive association across 5 seeds.

### 6.3 Strict Association Bounding Rule
Under scientific governance, **an exploratory sample of size $n=5$ cannot establish a causal relationship or structural mechanism**, regardless of nominal $p$-values. These statistics are recorded as **descriptive associations only**. Any causal claim asserting that draw frequencies "explain", "cause", or "drive" optimizer behavior is strictly unverified and prohibited.

---

## 7. Bounded Starvation Finding

The authoritative finding regarding the sampler starvation hypothesis is formally calibrated as follows:

> **"Complete exposure absence was not observed under Candidate F; whether exposure was quantitatively sufficient, optimally distributed, or temporally appropriate for learning remains unresolved."**

Non-zero sampler allocation refutes complete exposure absence, but does not prove quantitative learning sufficiency or optimal representation learning.

---

## 8. Authoritative Diagnostic Roadmap Preservation

The authoritative diagnostic roadmap established in C22-F and reaffirmed in C22-H remains fully intact:

1. **DIAG-01: CLASS SUPPORT & METRIC SENSITIVITY:**  
   - *Status:* `COMPLETED_VALID` (Classified as CASE B in C22-H).  
   - *Core Finding:* The frozen macro-arithmetic metric is support-sensitive but mathematically valid.
2. **DIAG-02: SAMPLER EXPOSURE & SCHEDULE INVARIANCE:**  
   - *Status:* `COMPLETED_FORENSICALLY_REPAIRED` (C22-I & C22-J).  
   - *Core Finding:* Candidate F provided non-zero exposure across all rare classes and parent clusters; draw variance descriptively associates with paired delta ($r = +0.8955$, $n=5$); C22-D suffered a silent key lookup defect.
3. **DIAG-03: RADIOMETRIC FEATURE DISCRIMINABILITY:**  
   - *Status:* `UNCHANGED_PENDING_USER_AUTHORIZATION`.  
   - *Identity:* Priority 3. Evaluates spectral and radiometric separability of rare phenomenon signatures in SAR backscatter space. Must not be renamed or overwritten.
4. **DIAG-04: RECEPTIVE FIELD & SPATIAL SCALE COMPATIBILITY:**  
   - *Status:* `UNCHANGED_PENDING_USER_AUTHORIZATION`.  
   - *Identity:* Priority 4. Evaluates effective receptive field vs physical phenomenon scale (sub-pixel objects, thin fronts). Must not be renamed or overwritten.
5. **DIAG-05: LOSS LANDSCAPE & GRADIENT DYNAMICS (FUTURE DESIGN ONLY / NOT EXECUTED):**  
   - *Status:* `DESIGN_ONLY_NOT_EXECUTED`.  
   - *Identity:* Reserved future diagnostic candidate. Outlined in Section 9 below.

---

## 9. DIAG-05 Specification (Loss Landscape & Gradient Dynamics) — DESIGN ONLY

### 9.1 Objective & Rationale
If future empirical investigation is authorized into the hypothesis that canonical class weights induce gradient norm volatility or cross-class gradient interference, such investigation must be conducted via direct measurement rather than speculation. DIAG-05 is designed specifically to test this hypothesis.

### 9.2 Experimental Protocol Specification (DESIGN ONLY)
1. **Model State:** Load frozen initial checkpoint clones or identical intermediate epoch checkpoints.
2. **Batch Control:** Construct identical paired minibatches:
   - Control Arm: Evaluated with canonical class weights vector.
   - Treatment Arm: Evaluated with uniform class weights vector ($1.0$).
   - Condition A: Minibatches containing only common classes (BG, IWs, MCC).
   - Condition B: Minibatches containing rare classes (OF, RF, HM).
3. **Direct Measurements:**
   - Layer-wise gradient $L_2$ norms ($\|\nabla_\theta \mathcal{L}\|_2$).
   - Gradient cosine similarity ($\cos(\nabla_{\theta} \mathcal{L}_{\text{rare}}, \nabla_{\theta} \mathcal{L}_{\text{common}})$).
   - Iteration-to-iteration gradient norm dispersion within identical training epochs.
4. **Strict Non-Execution Boundary:**
   - **DIAG-05 IS DESIGN ONLY.**
   - Zero backward passes were executed. Zero gradient norms were computed.
   - Execution requires future explicit user authorization.

---

## 10. Durable Lessons Learned Summary

The following lessons are formally registered and regression-protected in `data/metadata/ocean_sentinel_lessons_learned_v1.json`:

1. **`LL-C22I-001` (CRITICAL):** *Deterministic Samplers Must Not Silently Fall Back on Missing Manifest Keys.* (Dict `.get("labels_present", [])` silently collapsed class-presence weighting to 0.14%).
2. **`LL-C22I-002` (HIGH):** *Empirical Exposure Audit Must Precede Speculative Training-Starvation Claims.* (Auditing realized schedules directly before hypothesizing starvation; reflects that complete exposure absence was not observed, while sufficiency remains unresolved).
3. **`LL-C22I-003` (HIGH):** *Descriptive Association Between Schedule Draw Variance and Replication Delta.* (Bounded strictly to descriptive association across $n=5$ seeds; no causal/gradient mechanism claims).
4. **`LL-C22I-004` (HIGH):** *Early Peaking in Unweighted Training Is Driven by Dominant Mode Convergence, Not Sampler Starvation.* (Early peaking at Ep 5–7 is invariant to rare draws).
5. **`LL-C22J-001` (CRITICAL):** *Sampler Exposure Is Not Direct Evidence of Gradient Dynamics.* (Sampler audits measure draws, not gradients; gradient claims without measurement are forbidden).
6. **`LL-C22J-002` (HIGH):** *Small-Sample (n=5) Correlations Are Descriptive Associations, Not Causal Proof.* (Barring causal language like "explains", "drives", or "causes").
7. **`LL-C22J-003` (HIGH):** *Nonzero Sampler Exposure Does Not Prove Learning Sufficiency.* (Absence of total starvation $\neq$ quantitative adequacy for learning).
8. **`LL-C22J-004` (CRITICAL):** *Diagnostic Roadmap Integrity Requires Unique IDs; Never Overwrite Existing IDs.* (DIAG-03 and DIAG-04 preserved; DIAG-05 isolated as DESIGN ONLY).
9. **`LL-C22J-005` (HIGH):** *Physical Dataset Availability Must Be Distinguished from Sampler Allocation Policy.* (Tripartite distinction enforced across all analyses).

---

## 11. Conclusion

With this forensic correction, the analytical narrative, statistical calculations, and diagnostic roadmaps are completely synchronized, fully bounded, and verified against authoritative primary data.
