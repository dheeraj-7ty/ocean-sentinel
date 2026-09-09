"""
Parse canary v3 execution log and display clean output.
Also downloads kernel output files.
"""
import json, re, subprocess
from pathlib import Path

GATE_DIR = Path('D:/Projects/ocean-sentinel/experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118')
LOG_PATH = GATE_DIR / 'cloud_execution_v3.log'

if not LOG_PATH.exists():
    print("Log v3 not yet downloaded")
    exit(1)

raw = LOG_PATH.read_text(encoding='utf-8', errors='replace').strip()
if raw.startswith('['): raw = raw[1:]
if raw.endswith(']'): raw = raw[:-1]

lines = []
for piece in re.split(r'\n,', raw):
    piece = piece.strip().lstrip(',')
    if piece:
        try:
            lines.append(json.loads(piece))
        except: pass

print(f"=== CANARY V3 EXECUTION LOG ({len(lines)} events) ===\n")
for obj in lines:
    stream = obj.get('stream_name', '')
    data = obj.get('data', '').rstrip('\n')
    t = obj.get('time', 0)
    safe = data.encode('ascii', errors='replace').decode('ascii')
    if safe.strip():
        prefix = 'OUT' if stream == 'stdout' else 'ERR'
        print(f'[{t:7.2f}s][{prefix}] {safe}')
