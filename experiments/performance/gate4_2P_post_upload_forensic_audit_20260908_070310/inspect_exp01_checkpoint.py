import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(r"D:\Projects\ocean-sentinel")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

import torch
from scripts.train_exp01 import safe_load_checkpoint

exp01_dir = REPO_ROOT / "experiments" / "exp01_baseline"
best_path = exp01_dir / "best_model.pt"
latest_path = exp01_dir / "latest_checkpoint.pt"

def get_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

best_sha = get_sha256(best_path)
latest_sha = get_sha256(latest_path)

print(f"best_model.pt SHA256: {best_sha}")
print(f"latest_checkpoint.pt SHA256: {latest_sha}")

best_chk = safe_load_checkpoint(best_path, map_location="cpu")
print("best_model.pt keys:", list(best_chk.keys()))
print(f"best_model epoch: {best_chk.get('epoch')}, val_iou: {best_chk.get('val_iou')}")

model_state = best_chk["model_state_dict"]
conv1_weight = model_state["conv1.weight"]
print(f"conv1.weight shape: {conv1_weight.shape}")
print(f"conv1.weight mean: {conv1_weight.mean().item():.6f}, std: {conv1_weight.std().item():.6f}")

opt_state = best_chk.get("optimizer_state_dict", {})
print("Optimizer param groups:")
for i, pg in enumerate(opt_state.get("param_groups", [])):
    print(f"  group {i}: lr={pg.get('lr')}, initial_lr={pg.get('initial_lr')}, weight_decay={pg.get('weight_decay')}, eps={pg.get('eps')}, betas={pg.get('betas')}")

sched_state = best_chk.get("scheduler_state_dict", {})
print("Scheduler state:")
for k, v in sched_state.items():
    print(f"  {k}: {v}")

total_params = sum(p.numel() for p in model_state.values())
print(f"Total parameters in state dict: {total_params}")

# Inspect latest_checkpoint as well
latest_chk = safe_load_checkpoint(latest_path, map_location="cpu")
print(f"latest_checkpoint epoch: {latest_chk.get('epoch')}")

out_info = {
    "best_model_sha256": best_sha,
    "latest_checkpoint_sha256": latest_sha,
    "epoch": best_chk.get("epoch"),
    "val_iou": best_chk.get("val_iou"),
    "conv1_weight_shape": list(conv1_weight.shape),
    "conv1_weight_mean": conv1_weight.mean().item(),
    "conv1_weight_std": conv1_weight.std().item(),
    "total_params": total_params,
    "optimizer": {
        "lr": opt_state.get("param_groups", [{}])[0].get("lr"),
        "initial_lr": opt_state.get("param_groups", [{}])[0].get("initial_lr"),
        "weight_decay": opt_state.get("param_groups", [{}])[0].get("weight_decay"),
        "betas": opt_state.get("param_groups", [{}])[0].get("betas"),
        "eps": opt_state.get("param_groups", [{}])[0].get("eps"),
    },
    "scheduler": {
        "T_max": sched_state.get("T_max"),
        "eta_min": sched_state.get("eta_min"),
        "base_lrs": sched_state.get("base_lrs"),
        "last_epoch": sched_state.get("last_epoch"),
    },
    "latest_checkpoint": {
        "epoch": latest_chk.get("epoch"),
        "optimizer_lr": latest_chk.get("optimizer_state_dict", {}).get("param_groups", [{}])[0].get("lr"),
        "scheduler_last_epoch": latest_chk.get("scheduler_state_dict", {}).get("last_epoch"),
    }
}

out_json = Path(r"D:\Projects\ocean-sentinel\experiments\performance\gate4_2P_post_upload_forensic_audit_20260908_070310\checkpoint_forensics.json")
out_json.write_text(json.dumps(out_info, indent=2), encoding="utf-8")
print(f"Wrote forensic checkpoint analysis to {out_json}")
