"""
Parse the Kaggle kernel logs JSON stream and extract structured information.
Saves a clean execution log and extracts error details.
"""
import json, re
from pathlib import Path

log_path = Path('D:/Projects/ocean-sentinel/experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118/cloud_execution.log')
evidence_dir = Path('D:/Projects/ocean-sentinel/experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118')

raw = log_path.read_text(encoding='utf-8', errors='replace')

# Strip leading/trailing brackets if wrapped in array
raw = raw.strip()
if raw.startswith('['):
    raw = raw[1:]
if raw.endswith(']'):
    raw = raw[:-1]

# Split on JSON objects
lines = []
for piece in re.split(r'\n,', raw):
    piece = piece.strip().lstrip(',')
    if piece:
        try:
            obj = json.loads(piece)
            lines.append(obj)
        except Exception:
            pass

# Build clean text log
clean_lines = []
for obj in lines:
    stream = obj.get('stream_name', 'stdout')
    t = obj.get('time', 0)
    data = obj.get('data', '')
    prefix = 'OUT' if stream == 'stdout' else 'ERR'
    clean_lines.append(f"[t={t:8.3f}s] [{prefix}] {data}")

clean_log = ''.join(clean_lines)
clean_log_path = evidence_dir / 'cloud_execution_clean.log'
clean_log_path.write_text(clean_log, encoding='utf-8')
print(f"Clean log written: {len(clean_lines)} lines -> {clean_log_path}")

# Extract error lines (dataloader_contract and model_contract failures)
error_context = []
for i, obj in enumerate(lines):
    data = obj.get('data', '')
    if 'FAIL' in data or 'Error' in data or 'error' in data or 'Traceback' in data or 'Exception' in data:
        # Get context window
        start = max(0, i-3)
        end = min(len(lines), i+10)
        for j in range(start, end):
            error_context.append(f"[{lines[j].get('stream_name')}] {lines[j].get('data','')}")
        error_context.append('---')

print("\nError context:")
for l in error_context[:100]:
    print(l, end='')
