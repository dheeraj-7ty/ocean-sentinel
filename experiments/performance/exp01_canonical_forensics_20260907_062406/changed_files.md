# Changes Made During EXP01 Canonical Forensics

**Session Date**: 2026-09-07  
**Objective**: Establish immutable canonical EXP01 specification, implement regression tests locking EXP01 parameters, and verify baseline integrity.

---

## 1. Production Code Changes

### [NEW] `src/ocean_sentinel/ml/canonical_exp01.py`
- **Purpose**: Defines authoritative, immutable constants and validation logic for EXP-01 baseline experiment.
- **Key Exports**:
  - `CANONICAL_OPTIMIZER_CLASS = "AdamW"`
  - `CANONICAL_LEARNING_RATE = 1e-4`
  - `CANONICAL_WEIGHT_DECAY = 1e-2`
  - `CANONICAL_SCHEDULER_CLASS = "CosineAnnealingLR"`
  - `CANONICAL_SCHEDULER_PARAMS = {"T_max": 30, "eta_min": 1e-6}`
  - `CANONICAL_MAX_EPOCHS = 30`
  - `CANONICAL_PATIENCE = 10`
  - `CANONICAL_LOSS_WEIGHTS = {"bce_weight": 0.5, "dice_weight": 0.5}`
  - `CANONICAL_TOTAL_PARAMS = 24346305`
  - `CANONICAL_TRAINABLE_PARAMS = 24346305`
  - `CANONICAL_BEST_VAL_IOU = 0.71691`
  - `CANONICAL_SELECTED_THRESHOLD = 0.22`
  - `verify_canonical_exp01_config(config: dict) -> Tuple[bool, List[str]]`: Strict validator that fails if `lr == 5e-4` or `scheduler == "CosineAnnealingWarmRestarts"`.
  - `build_canonical_fingerprint_dict() -> dict`: Authoritative generator for machine-readable JSON fingerprints.

### [MODIFY] `src/ocean_sentinel/ml/__init__.py`
- **Purpose**: Exposes canonical EXP01 constants and verification utilities cleanly in the public ML package namespace.

---

## 2. Test Suite Changes

### [NEW] `tests/test_canonical_exp01_fingerprint.py`
- **Purpose**: Comprehensive regression test suite locking EXP01 canonical parameters and certifying baseline artifact adherence.
- **Test Cases (11 total, all passing)**:
  1. `test_canonical_constants_values`: Asserts `CANONICAL_LEARNING_RATE == 1e-4`, `CANONICAL_SCHEDULER_CLASS == "CosineAnnealingLR"`, etc.
  2. `test_fingerprint_builder_schema`: Asserts complete schema adherence and correct metadata.
  3. `test_verify_canonical_exp01_config_valid`: Validates certified `config.json`.
  4. `test_verify_canonical_exp01_config_rejects_5e4_lr`: Explicit negative test rejecting `lr=5e-4`.
  5. `test_verify_canonical_exp01_config_rejects_warm_restarts`: Explicit negative test rejecting `CosineAnnealingWarmRestarts`.
  6. `test_verify_canonical_exp01_config_rejects_epoch_drift`: Explicit negative test rejecting `max_epochs=50`.
  7. `test_verify_canonical_exp01_config_rejects_model_drift`: Explicit negative test rejecting alternative architectures.
  8. `test_certified_baseline_config_integrity`: Asserts certified `config.json` passes validation.
  9. `test_certified_baseline_checkpoints_scheduler_state`: Inspects `best_model.pt` and `latest_checkpoint.pt` to ensure optimizer LR = 0.0001, scheduler = CosineAnnealingLR (`T_max=30, eta_min=1e-6`), and neither `T_0` nor `T_mult` exists.
  10. `test_certified_baseline_history_scheduler_decay`: Numerically verifies smooth cosine decay in `history.json` across epochs 1, 4, and 14, matching theoretical cosine annealing to within $10^{-7}$.
  11. `test_certified_baseline_run_state_and_results`: Asserts metric alignment (Val IoU = 0.71691, threshold = 0.22, test IoU = 0.78434).

---

## 3. Forensic Artifacts Created

Target Directory: `experiments/performance/exp01_canonical_forensics_20260907_062406/`
- `parameter_forensics.json`
- `git_history_evidence.md`
- `conflict_map.md`
- `changed_files.md`
- `closure_audit.md`
- `canonical_fingerprint.json`
- `canonical_fingerprint_test_results.json`
- `run_state.json`
- `commands.log`
- `report.md`
