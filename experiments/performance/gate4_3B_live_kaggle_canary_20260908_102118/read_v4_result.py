"""Extract exact failure evidence from canary v4 result JSON."""
import json
from pathlib import Path

result_path = Path('D:/Projects/ocean-sentinel/experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118/kernel_output_v4/gate4_3B_canary/canary_result.json')
result = json.loads(result_path.read_text(encoding='utf-8', errors='replace'))

print("=== CANARY V4 RESULT ===")
print(f"Overall: {result.get('result', 'N/A')}")
print(f"Passed:  {result.get('passed', [])}")
print(f"Failed:  {result.get('failed', [])}")
print()

for check_name in ['dataloader_contract', 'model_contract']:
    check = result.get('checks', {}).get(check_name, {})
    print(f"{'='*60}")
    print(f"CHECK: {check_name}")
    print(f"Status: {check.get('status', 'N/A')}")
    ev = check.get('evidence', {})
    # Print all evidence keys
    for k, v in ev.items():
        if k == 'traceback':
            print(f"traceback:")
            for line in str(v).splitlines():
                print(f"  {line}")
        else:
            print(f"{k}: {v}")
    print()
