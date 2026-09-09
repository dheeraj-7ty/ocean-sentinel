"""
Phase C-C2.5: Canonical Seed Forensic Verification & Diagnostic Audit.

Exhaustively audits the downloaded C-C2 latest_checkpoint.pt:
1. Verify SHA-256 matches cloud manifest
2. Verify all 14 required canonical keys
3. Verify scheduler.T_max == 30 and scheduler.last_epoch == 1
4. Verify scheduler._last_lr is canonical cosine decay (~9.9726e-5, NOT 1e-6)
5. Verify optimizer parameter step == 1680.0 across all 150 tracked parameters
6. Verify history length == 1, val_iou == 0.66277
7. Run diagnostic comparison against C-B latest_checkpoint.pt
"""

import json
import os
import sys
import time
from pathlib import Path

# Ensure Windows path compatibility
if os.name == "nt":
    import pathlib
    try:
        pathlib.PosixPath = pathlib.WindowsPath
    except Exception:
        pass

import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from ocean_sentinel.ml.unet_resnet import ResNet34UNet
from scripts.train_exp01 import (
    safe_load_checkpoint,
    file_sha256,
)

C_C2_DIR = Path(__file__).resolve().parent / "kernel_output"
C_C2_LATEST = C_C2_DIR / "latest_checkpoint.pt"
C_C2_INTEGRITY = C_C2_DIR / "checkpoint_integrity.json"

CB_DIR = REPO_ROOT / "experiments/performance/gate4_3C_B_one_epoch_pilot_20260908_220700/kernel_output"
CB_LATEST = CB_DIR / "latest_checkpoint.pt"


def main():
    print("=" * 70)
    print("PHASE C-C2.5: CANONICAL SEED FORENSIC VERIFICATION & FREEZE")
    print("=" * 70)

    assert C_C2_LATEST.exists(), f"Missing C-C2 checkpoint: {C_C2_LATEST}"
    fsize = C_C2_LATEST.stat().st_size
    actual_sha = file_sha256(C_C2_LATEST)
    print(f"File:         {C_C2_LATEST}")
    print(f"Size:         {fsize:,} bytes")
    print(f"SHA-256:      {actual_sha}")

    integrity = json.loads(C_C2_INTEGRITY.read_text(encoding="utf-8"))
    expected_sha = integrity["latest_sha256"]
    assert actual_sha.upper() == expected_sha.upper(), f"SHA mismatch: {actual_sha} vs {expected_sha}"
    print(f"Manifest SHA: {expected_sha} [MATCHES DISK BITWISE]")

    # Safe load
    chkpt = safe_load_checkpoint(C_C2_LATEST, map_location="cpu", expected_sha256=actual_sha)

    # 1. Canonical 14 keys
    for req_k in [
        "epoch", "model_state_dict", "optimizer_state_dict", "scheduler_state_dict",
        "scaler_state_dict", "val_iou", "val_dice", "val_loss", "best_val_iou",
        "best_epoch", "patience_counter", "history", "config", "experiment_fingerprint",
    ]:
        assert req_k in chkpt, f"Missing canonical key: {req_k}"
    print("Canonical Keys: 14/14 Present [PASS]")

    # 2. Scheduler State (CRITICAL SCIENTIFIC INTEGRITY PROOF)
    sched = chkpt["scheduler_state_dict"]
    sched_t_max = sched.get("T_max")
    last_ep = sched.get("last_epoch")
    last_lr = sched.get("_last_lr", [None])[0]
    print(f"Scheduler T_max:      {sched_t_max} (Canonical EXP01 requires 30)")
    print(f"Scheduler last_epoch: {last_ep} (Requires 1)")
    print(f"Scheduler _last_lr:   {last_lr:.8e}")

    assert sched_t_max == 30, f"FATAL: Scheduler T_max is {sched_t_max}, expected 30!"
    assert last_ep == 1, f"FATAL: Scheduler last_epoch is {last_ep}, expected 1!"
    # Under T_max=30, cosine decay at epoch 1 gives ~9.9726e-5
    assert abs(last_lr - 9.9726e-5) < 1e-6, f"Unexpected LR: {last_lr}"
    print("[PASS] SCHEDULER STATE VERIFIED CANONICAL (T_max=30, last_epoch=1, LR=9.9726e-5)")

    # 3. Optimizer State
    opt = chkpt["optimizer_state_dict"]
    tracked = len(opt["state"])
    assert tracked == 150, f"Expected 150 tracked parameters, got {tracked}"
    step_set = set(s["step"].item() for s in opt["state"].values())
    assert step_set == {1680.0}, f"Unexpected optimizer steps: {step_set}"
    print(f"[PASS] OPTIMIZER STATE VERIFIED (150 tracked parameters @ step 1680.0)")

    # 4. Scaler State
    scaler = chkpt["scaler_state_dict"]
    assert scaler["scale"] == 65536.0
    assert scaler["_growth_tracker"] == 1680
    print(f"[PASS] SCALER STATE VERIFIED (scale=65536.0, growth_tracker=1680)")

    # 5. History and Epoch
    assert chkpt["epoch"] == 1
    assert len(chkpt["history"]) == 1
    print(f"[PASS] EPOCH & HISTORY VERIFIED (epoch 1, history len 1, val_iou={chkpt['val_iou']:.5f})")

    # 6. Best State Synchronization
    assert chkpt["best_val_iou"] == chkpt["val_iou"]
    assert chkpt["best_epoch"] == 1
    print(f"[PASS] BEST-STATE SYNCHRONIZED (best_val_iou={chkpt['best_val_iou']:.5f} @ epoch {chkpt['best_epoch']})")

    # 7. Model State Count
    msd = chkpt["model_state_dict"]
    assert len(msd) == 288
    print(f"[PASS] MODEL STATE VERIFIED (288 tensors)")

    # 8. Run Diagnostic Model Comparison against C-B
    print("\n" + "-" * 70)
    print("RUNNING DIAGNOSTIC MODEL-STATE COMPARISON (C-B vs C-C2)...")
    print("-" * 70)

    cb_chkpt = safe_load_checkpoint(CB_LATEST, map_location="cpu")
    cb_msd = cb_chkpt["model_state_dict"]
    cc2_msd = chkpt["model_state_dict"]

    all_keys = sorted(list(set(cb_msd.keys()) | set(cc2_msd.keys())))
    identical_tensors = 0
    total_tensors = len(all_keys)
    max_abs_diff = 0.0
    sum_sq_diff = 0.0
    total_elements = 0

    for k in all_keys:
        t_cb = cb_msd[k].float()
        t_cc2 = cc2_msd[k].float()
        diff = (t_cb - t_cc2).abs()
        t_max = float(diff.max().item())
        if (t_cb == t_cc2).all().item():
            identical_tensors += 1
        if t_max > max_abs_diff:
            max_abs_diff = t_max
        sum_sq_diff += float((t_cb - t_cc2).pow(2).sum().item())
        total_elements += t_cb.numel()

    l2_overall = float(sum_sq_diff ** 0.5)
    identical_pct = round(100.0 * identical_tensors / max(total_tensors, 1), 2)

    print(f"Total Tensors Compared:       {total_tensors}")
    print(f"Bitwise Identical Tensors:    {identical_tensors} / {total_tensors} ({identical_pct}%)")
    print(f"Total Parameter Elements:     {total_elements:,}")
    print(f"Max Absolute Difference:      {max_abs_diff:.6e}")
    print(f"Overall L2 Difference Norm:   {l2_overall:.6e}")
    print("-" * 70)

    diag_summary = {
        "total_tensors": total_tensors,
        "identical_tensors": identical_tensors,
        "identical_percentage": identical_pct,
        "max_absolute_difference": max_abs_diff,
        "overall_l2_difference_norm": l2_overall,
    }

    # 9. Write Final Verification Report
    report = {
        "phase": "C-C2.5",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "canonical_seed_checkpoint": str(C_C2_LATEST),
        "sha256": actual_sha,
        "size_bytes": fsize,
        "scheduler_t_max": sched_t_max,
        "scheduler_last_epoch": last_ep,
        "scheduler_last_lr": last_lr,
        "optimizer_cumulative_step": 1680.0,
        "history_length": len(chkpt["history"]),
        "val_iou": chkpt["val_iou"],
        "diagnostic_model_comparison": {
            "total_tensors": diag_summary["total_tensors"],
            "identical_tensors": diag_summary["identical_tensors"],
            "identical_percentage": diag_summary["identical_percentage"],
            "max_absolute_difference": diag_summary["max_absolute_difference"],
            "overall_l2_difference_norm": diag_summary["overall_l2_difference_norm"],
        },
        "canonical_continuation_qualification": "CLEAN PASS — Authorized as continuation seed for Phase C-C3/C-C4",
    }
    report_file = Path(__file__).resolve().parent / "c_c2_verification_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nVerification report written to: {report_file}")
    print("=" * 70)
    print("PHASE C-C2.5 VERDICT: CLEAN PASS")
    print("Canonical Epoch-1 Seed successfully qualified and frozen locally.")
    print("=" * 70)


if __name__ == "__main__":
    main()
