import json
import sys
from pathlib import Path
REPO_ROOT = Path(r"D:\Projects\ocean-sentinel")
sys.path.insert(0, str(REPO_ROOT))
from scripts.train_exp01 import safe_load_checkpoint

best_path = REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt"
chk = safe_load_checkpoint(best_path, map_location="cpu")

print("Config inside checkpoint:")
print(json.dumps(chk.get("config"), indent=2, default=str))

print("Experiment fingerprint inside checkpoint:")
print(json.dumps(chk.get("experiment_fingerprint"), indent=2, default=str))
