"""Read and display canary v5 result."""
import json
from pathlib import Path

result = json.loads(
    Path('experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118/kernel_output_v5/gate4_3B_canary/canary_result.json')
    .read_bytes().decode('utf-8', errors='replace')
)

print('=== CANARY V5 RESULT ===')
overall = result.get('result', result.get('canary_result', 'N/A'))
print('Overall result:', overall)

checks = result.get('checks', {})
passed = [k for k, v in checks.items() if v.get('status') == 'PASS']
failed = [k for k, v in checks.items() if v.get('status') == 'FAIL']
warned = [k for k, v in checks.items() if v.get('status') == 'WARN']
print(f'PASSED ({len(passed)}): {passed}')
print(f'FAILED ({len(failed)}): {failed}')
print(f'WARNED ({len(warned)}): {warned}')
print()

for name, check in checks.items():
    status = check.get('status', 'N/A')
    ev = check.get('evidence', {})
    icon = 'PASS' if status == 'PASS' else 'FAIL' if status == 'FAIL' else status
    print(f'  [{icon}] {name}')
    if status != 'PASS':
        err = ev.get('error', '')
        tb = ev.get('traceback', '')
        if err:
            print(f'    error: {err[:300]}')
        if tb:
            for line in tb.strip().splitlines()[:15]:
                print(f'    {line}')
    else:
        # Print key evidence fields
        for k, v in ev.items():
            if k not in ('traceback',) and not isinstance(v, dict):
                print(f'    {k}: {v}')
