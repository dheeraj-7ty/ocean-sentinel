"""Fetch C-C2 kernel logs and output files from Kaggle with UTF-8 encoding."""
import os
import subprocess
from pathlib import Path

GATE_DIR = Path("D:/Projects/ocean-sentinel/experiments/performance/gate4_3C_C2_canonical_seed_20260909_000500")
LOGS_DIR = GATE_DIR / "logs"
OUTPUT_DIR = GATE_DIR / "kernel_output"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUTF8"] = "1"

# Fetch logs
cmd_logs = [
    r"D:\Tools\cloud-tools\Scripts\kaggle.exe",
    "kernels", "logs",
    "dheeraj12237/ocean-sentinel-gate-4-3b-live-canary"
]
print("Fetching kernel logs...")
res_logs = subprocess.run(
    cmd_logs,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    env=env
)

log_file = LOGS_DIR / "cloud_execution.log"
log_file.write_text(res_logs.stdout, encoding="utf-8")
print(f"Logs written to {log_file} ({len(res_logs.stdout)} chars)")
if res_logs.stderr:
    err_file = LOGS_DIR / "cloud_execution_err.log"
    err_file.write_text(res_logs.stderr, encoding="utf-8")
    print(f"Stderr written to {err_file}")

# Fetch outputs
cmd_output = [
    r"D:\Tools\cloud-tools\Scripts\kaggle.exe",
    "kernels", "output",
    "dheeraj12237/ocean-sentinel-gate-4-3b-live-canary",
    "-p", str(OUTPUT_DIR),
    "--force"
]
print("Fetching kernel output files...")
res_output = subprocess.run(
    cmd_output,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace"
)
print("Output STDOUT:\n", res_output.stdout)
print("Output STDERR:\n", res_output.stderr)
