"""Parse and display canary v4 execution log."""
import json, re
from pathlib import Path

log_path = Path('experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118/cloud_execution_v4.log')
raw = log_path.read_text(encoding='utf-8', errors='replace').strip()
if raw.startswith('['): raw = raw[1:]
if raw.endswith(']'): raw = raw[:-1]

lines = []
for piece in re.split(r'\n,', raw):
    piece = piece.strip().lstrip(',')
    if piece:
        try:
            lines.append(json.loads(piece))
        except Exception:
            pass

print(f"=== CANARY V4 LOG ({len(lines)} events) ===")
for obj in lines:
    stream = obj.get('stream_name', '')
    data = obj.get('data', '').rstrip('\n')
    t = obj.get('time', 0)
    safe = data.encode('ascii', errors='replace').decode('ascii')
    prefix = 'OUT' if stream == 'stdout' else 'ERR'
    if safe.strip():
        print(f'[{t:7.2f}s][{prefix}] {safe}')
