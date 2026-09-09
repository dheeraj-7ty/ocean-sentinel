"""
Reconcile the 14/15 wrapper warning for Phase C-C4.

Audits and reconciles:
1. Outer wrapper canary checked run_state["cumulative_optimizer_steps"], which was 0 because
   the runner wrote run_state["cumulative_optimizer_updates"]: 3360.
2. Leaves raw downloaded reconciliation_audit.json UNTOUCHED.
3. Examines physical checkpoint latest_checkpoint.pt to confirm that all 150 optimizer
   parameter states are empirically at step 3360.0.
4. Emits reconciliation_reconciled.json documenting the exact diagnostic finding.
"""

import json
import os
import sys
from pathlib import Path

# Ensure Windows path compatibility
if os.name == "nt":
    import pathlib
    try:
        pathlib.PosixPath = pathlib.WindowsPath
    except Exception:
        pass

import torch

REPO_ROOT = Path("D:/Projects/ocean-sentinel")
C_C4_DIR = REPO_ROOT / "experiments/performance/gate4_3C_C4_resume_epoch2_20260909_002000"
KERNEL_OUT = C_C4_DIR / "kernel_output/gate4_3C_C_resume"

RAW_RECONCIL = KERNEL_OUT / "reconciliation_audit.json"
RUN_STATE = KERNEL_OUT / "run_state.json"
LATEST_CHKPT = KERNEL_OUT / "latest_checkpoint.pt"


def main():
    print("=" * 75)
    print("PHASE C-C5/C-C6: RECONCILING 14/15 WRAPPER WARNING")
    print("=" * 75)

    assert RAW_RECONCIL.exists(), f"Missing {RAW_RECONCIL}"
    assert RUN_STATE.exists(), f"Missing {RUN_STATE}"
    assert LATEST_CHKPT.exists(), f"Missing {LATEST_CHKPT}"

    raw_data = json.loads(RAW_RECONCIL.read_text(encoding="utf-8"))
    rs_data = json.loads(RUN_STATE.read_text(encoding="utf-8"))

    # 1. Forensic examination of key names in run_state.json
    print("\n1. RUN_STATE.JSON KEY AUDIT:")
    has_cum_steps = "cumulative_optimizer_steps" in rs_data
    has_cum_updates = "cumulative_optimizer_updates" in rs_data
    print(f"  Key 'cumulative_optimizer_steps' present:   {has_cum_steps}")
    print(f"  Key 'cumulative_optimizer_updates' present: {has_cum_updates}")
    if has_cum_updates:
        print(f"  Value of 'cumulative_optimizer_updates':   {rs_data['cumulative_optimizer_updates']}")

    assert rs_data.get("cumulative_optimizer_updates") == 3360, "Expected 3360 cumulative updates"
    assert rs_data.get("prior_optimizer_steps") == 1680, "Expected 1680 prior steps"
    assert rs_data.get("successful_optimizer_updates") == 1680, "Expected 1680 session updates"

    # 2. Forensic examination of physical checkpoint state dict
    print("\n2. PHYSICAL CHECKPOINT OPTIMIZER STATE AUDIT:")
    chkpt = torch.load(LATEST_CHKPT, map_location="cpu", weights_only=False)
    opt_state = chkpt["optimizer_state_dict"]
    tracked_count = len(opt_state["state"])
    print(f"  Total Tracked Parameters in Optimizer:     {tracked_count}")
    assert tracked_count == 150, f"Expected 150 tracked parameters, got {tracked_count}"

    steps = set()
    for p_id, p_state in opt_state["state"].items():
        step_val = p_state["step"].item()
        steps.add(step_val)

    print(f"  Distinct Step Values Across All Parameters: {steps}")
    assert steps == {3360.0}, f"Expected all parameters at step 3360.0, got {steps}"
    print(f"  [CONFIRMED] All 150 tracked parameters are empirically at step 3360.0.")

    # 3. Build reconciled audit
    reconciled = dict(raw_data)
    reconciled["cumulative_optimizer_steps"] = {
        "expected": 3360,
        "observed": rs_data["cumulative_optimizer_updates"],
        "pass": True,
        "diagnostic_note": (
            "Wrapper looked for key 'cumulative_optimizer_steps', which returned default 0 "
            "because train_exp01.py recorded 'cumulative_optimizer_updates': 3360. "
            "Physical checkpoint confirms 150/150 tracked parameters at step 3360.0."
        ),
    }

    all_passed = all(item["pass"] for item in reconciled.values())
    print(f"\n3. RECONCILED VERDICT: {'CLEAN PASS (15/15)' if all_passed else 'FAIL'}")

    out_file = C_C4_DIR / "reconciliation_reconciled.json"
    out_file.write_text(json.dumps(reconciled, indent=2), encoding="utf-8")
    print(f"Reconciled report written to: {out_file}")
    print("=" * 75)


if __name__ == "__main__":
    main()
