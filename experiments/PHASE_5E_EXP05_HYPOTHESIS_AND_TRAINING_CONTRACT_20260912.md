# PHASE 5E EXP-05 HYPOTHESIS AND TRAINING CONTRACT
**Project:** Ocean Sentinel  
**Authority:** CAIO Scientific Governance  
**Document ID:** PHASE_5E_EXP05_CONTRACT_20260912  
**Date:** 2026-09-12  
**Status:** **PREREGISTERED & FROZEN (TRAINING NOT AUTHORIZED)**  
**Training Authorization:** **NOT GRANTED (SPECIFICATION ONLY)**  

---

## 1. EXP-04 Empirical Findings & Forensic Summary

Phase 5D EXP-04 evaluated a 50% exposure reduction (from $12.5\%$ in EXP-03 to $6.25\%$ in EXP-04) using $15\text{ standard} + 1\text{ mined}$ tiles per 16-tile batch across 10 epochs.

* **Trajectory Metrics at Certified Best Checkpoint (Epoch 9, $\tau = 0.22$):**
  - **Val Loss:** $0.08907$
  - **Validation IoU:** $\mathbf{0.70910}$ (EXP-01: $0.71691$, EXP-03: $0.70435$, Gate: $\ge 0.71731$) $\longrightarrow$ **FAIL** (Missed gate by $-0.00821$)
  - **Validation Dice:** $0.82979$ (EXP-01: $0.83512$, EXP-03: $0.82653$) $\longrightarrow$ ($+0.39\%$ relative gain vs EXP-03)
  - **Validation Precision:** $0.88343$ (EXP-01: $0.85138$, EXP-03: $0.88820$) $\longrightarrow$ ($+3.205\text{ pp}$ above EXP-01 baseline)
  - **Validation Recall:** $\mathbf{0.78230}$ (EXP-01: $0.78488$, EXP-03: $0.77287$, Gate: $\ge 0.78500$) $\longrightarrow$ **FAIL** (Missed gate by $-0.27\text{ pp}$)
  - **Clean-Water FAR:** $\mathbf{0.55\%}$ (EXP-01: $20.09\%$, EXP-03: $0.33\%$, Gate: $< 5.00\%$) $\longrightarrow$ **PASS** ($-97.26\%$ relative reduction vs EXP-01)
  - **Significant FAR:** $\mathbf{0.55\%}$ (EXP-01: $10.56\%$, EXP-03: $0.33\%$, Gate: $< 3.00\%$) $\longrightarrow$ **PASS** ($-94.79\%$ relative reduction vs EXP-01)
  - **Total FP Pixels:** $\mathbf{122,937}$ (EXP-01: $2,327,942$, EXP-03: $79,742$, Gate: $< 350,000$) $\longrightarrow$ **PASS** ($-94.72\%$ relative reduction vs EXP-01)

* **Prediction-Mass Findings:**
  - Total predicted positive mass expanded by $+248,040\text{ pixels}$ ($14,043,861 \to 14,291,901\text{ px}$).
  - Missed false negative mass dropped by $-150,785\text{ pixels}$ ($3,664,417 \to 3,513,632\text{ px}$).
  - **However, positive tile dropout persisted:** $231$ positive tiles dropped in EXP-04 vs. $227$ in EXP-03.

---

## 2. Gate Evaluation & Root-Cause Failure Analysis

| Acceptance Gate Metric | Preregistered Gate Threshold | EXP-04 Observed Value | Status | Scientific Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **Gate 1: Validation Recall** | $\ge 0.78500$ | $0.78230$ | **FAIL** | Narrow gate miss ($-0.00270$ or $-0.27\text{ pp}$) |
| **Gate 2: Validation IoU** | $\ge 0.71731$ | $0.70910$ | **FAIL** | Non-inferiority bound missed by $-0.00821$ |
| **Gate 3: Clean-Water FAR** | $< 5.00\%$ | $0.55\%$ | **PASS** | Vast outperformance ($-97.3\%$ vs baseline) |
| **Gate 4: Significant FAR** | $< 3.00\%$ | $0.55\%$ | **PASS** | Vast outperformance ($-94.8\%$ vs baseline) |
| **Gate 5: Total FP Pixels** | $< 350,000$ | $122,937$ | **PASS** | Vast outperformance ($-94.7\%$ vs baseline) |
| **OVERALL EXP-04 ACCEPTANCE**| **All 5 Gates Pass** | **3 Pass / 2 Fail** | **FAIL** | Acceptance-gate failure |

**Scientific Interpretation:** Halving the batch exposure frequency ($12.5\% \to 6.25\%$) successfully proved the mass-recovery hypothesis, but left positive tile dropout unresolved ($231$ dropped tiles). The persistence of dropout is mechanistically tied to the presence of $45$ extreme outlier tiles in the candidate pool ($\text{fp\_pixels} > 50,000$, up to full-tile $262,144$ errors). When these extreme tiles enter the batch, they impose a whole-feature-map negative gradient penalty that suppresses subtle, low-contrast oil slicks regardless of exposure cadence.

---

## 3. Primary Scientific Hypothesis (H-05)

> **Hypothesis H-05:**  
> Enforcing an upper severity cap of $\le \mathbf{50,000\text{ false positive pixels}}$ on the hard-negative candidate pool while holding the batch exposure frequency strictly constant at $6.25\%$ ($15\text{ standard} + 1\text{ mined}$) will eliminate the catastrophic whole-tile negative gradient shocks that cause positive tile dropout. This intervention will lift validation Recall to $\ge \mathbf{0.78500}$ and validation IoU to $\ge \mathbf{0.71731}$ (achieving non-inferiority against the EXP-01 baseline), while preserving $>90\%$ of the clean-water false-alarm reduction achieved in EXP-04 (Clean-Water FAR $< 5.0\%$, Significant FAR $< 3.0\%$, Total FP Pixels $< 350,000$).

---

## 4. Single-Variable Intervention Specification

* **Primary Intervention:** **Hard-Negative Candidate Severity Capping at $\le 50,000$ False Positive Pixels.**
* **Mechanism:** Filter the frozen $400$-candidate manifest `exp03_hard_negative_manifest.json` such that only candidates satisfying $\text{fp\_pixels} \le 50,000$ are admitted into the active mined sampling pool.
* **Eligible Candidate Pool Size:** Exactly $\mathbf{355\text{ candidates}}$ ($45$ extreme outliers excluded).
* **Mass Purged:** $7,168,600\text{ pixels}$ ($80.35\%$ of total error mass) purged.
* **Geographic Diversity Retained:** $251$ out of $273$ parent scenes retained ($\mathbf{91.94\%}$).
* **Sampling Rate:** Unchanged ($15\text{ standard} + 1\text{ mined} = 16\text{ tiles/batch}$, $6.25\%$ mined exposure).
* **Optimizer Steps:** Unchanged ($896\text{ batches/epoch} \times 10\text{ epochs} = \mathbf{8,960\text{ steps}}$).

---

## 5. Audit Against Hidden Secondary Variables

| Potential Confirmatory Drift | Status | Verification Protocol |
| :--- | :---: | :--- |
| **Standard Training Data Changed?** | **NO** | Standard pool remains strictly the $13,440$ canonical TRAIN tiles. |
| **Batch Size Changed?** | **NO** | Fixed at 16 tiles per batch. |
| **Mined Exposure Ratio Changed?** | **NO** | Fixed at 1 mined tile per batch ($6.25\%$). |
| **Loss Function or Weights Changed?** | **NO** | CombinedBCEAndDiceLoss ($0.5$ BCE, $0.5$ Dice, $\text{smooth}=1.0$). |
| **Optimizer or LR Schedule Changed?** | **NO** | AdamW ($\text{lr}=1\text{e-}4$, $\text{weight\_decay}=1\text{e-}2$), CosineAnnealingLR ($T_{\text{max}}=10$, $\eta_{\text{min}}=1\text{e-}6$). |
| **Epoch Count Changed?** | **NO** | Exactly 10 epochs. |
| **Seed Changed?** | **NO** | Base seed 42. Deterministic sampler seed $42 + 1000 \times \text{epoch}$. |
| **Operating Threshold Changed?** | **NO** | Strictly frozen at $\tau = 0.22$. |
| **Candidate Images or Masks Modified?** | **NO** | Raw GeoTIFFs on disk are read-only. No pixel clipping or reweighting. |

---

## 6. Pre-Registered Acceptance Gates (EXP-05)

The acceptance gates are strictly frozen prior to training authorization:

| Gate Identifier | Metric | Gate Condition | Primary Baseline Target (EXP-01) | EXP-04 Control (Observed) | Scientific Disposition |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **Gate 1** | **Validation Recall** | $\ge \mathbf{0.78500}$ | $0.78488$ | $0.78230$ | Non-inferiority bound vs EXP-01 |
| **Gate 2** | **Validation IoU** | $\ge \mathbf{0.71731}$ | $0.71691$ | $0.70910$ | Non-inferiority bound vs EXP-01 |
| **Gate 3** | **Clean-Water FAR** | $< \mathbf{5.00\%}$ | $20.09\%$ | $0.55\%$ | Operational false alarm ceiling |
| **Gate 4** | **Significant FAR** | $< \mathbf{3.00\%}$ | $10.56\%$ | $0.55\%$ | Multi-pixel false alarm ceiling |
| **Gate 5** | **Total FP Pixels** | $< \mathbf{350,000}$ | $2,327,942$ | $122,937$ | Structural false positive mass bound |

**Overall Acceptance Condition:** All 5 gates must PASS simultaneously at the certified best validation IoU checkpoint at $\tau = 0.22$.

---

## 7. Observability & Durable Telemetry Protocol

For future authorized EXP-05 execution, telemetry must be recorded to:
`experiments/performance/exp05_candidate_severity_cap/run_state.json`

The JSON payload must maintain:
- `experiment_id`: `"EXP-05_CANDIDATE_SEVERITY_CAP"`
- `attempt_id`: `"EXP05_ATTEMPT_001"`
- `pid`, `command_line`, `git_branch`, `git_commit_sha`
- `start_time_utc`, `heartbeat_utc`, `status`, `phase`
- `epoch`, `batch`, `completed_batches`, `percent_complete`
- `eta_seconds`, `current_train_loss`, `best_val_iou`, `best_epoch`
- `checkpoint_status`, `gpu_vram_allocated_mb`
- Mandatory real-time output line:
  `PHASE: <phase> | PROGRESS: <pct>% (Batch B/896, Epoch E/10) | STATUS: <status> | ETA: <eta> | HEARTBEAT: <timestamp>`
- Cadence: Updated every 20 batches and at every epoch boundary.

---

## 8. Windows Multiprocessing Safety Protocol

All verification and training scripts MUST strictly adhere to:
1. Entry point protected by `if __name__ == "__main__":`.
2. Explicit `num_workers=0` for all validation and independent verification loaders to prevent Windows process spawn deadlocks.
3. Explicit terminal telemetry reporting on batch progress.
4. Independent execution from project virtual environment (`venv\Scripts\python`).

---

## 9. Scientific Firewall Against External Trujillo Part III

* External Part III test data remains strictly quarantined.
* Zero Part III paths or identifiers may be read, loaded, evaluated, or referenced.
* Verified enforced by `ocean_sentinel.ingestion.firewall.assert_no_part_iii_leakage`.

---

## 10. Explicit Rejection Criteria for the Design

The design itself must be rejected immediately if:
1. Filtering by $\text{fp\_pixels} \le 50,000$ reduces parent-scene retention below $85\%$. (Observed retention: $91.94\%$, PASS).
2. Any single parent scene accounts for $> 5\%$ of the active candidate pool. (Observed max: $2$ candidates = $0.56\%$, PASS).
3. Any candidate in the retained pool has non-zero ground-truth pixels (`gt_pixels > 0`). (Observed: 100% negative purity, PASS).
4. The number of optimizer steps deviates from $8,960$. (Observed: exactly $8,960$, PASS).

---

## 11. Final Declarations

```text
EXP05_FORENSIC_ANALYSIS = PASS
EXP05_DESIGN = PASS
EXP05_ONE_VARIABLE_CONTRACT = PASS
EXP05_PREFLIGHT = PASS
PART_III_FIREWALL = PASS
DATA_LEAKAGE_CONTROLS = PASS
REPRODUCIBILITY_CONTROLS = PASS
OBSERVABILITY_DESIGN = PASS
WINDOWS_SAFETY = PASS
TRAINING_EXECUTED = NO
CAIO_AUTHORIZATION_FOR_TRAINING = NOT_GRANTED
```

**Final Status:**  
$$\mathbf{FROZEN\_BEFORE\_TRAINING\ /\ AWAITING\_CAIO\_AUTHORIZATION}$$
