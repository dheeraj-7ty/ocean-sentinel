import json
from pathlib import Path
import os

# Check what kaggle credentials mechanism is available
creds_path = Path('C:/Users/Dheeraj/.kaggle/credentials.json')
kaggle_json_path = Path('C:/Users/Dheeraj/.kaggle/kaggle.json')

print(f"credentials.json exists: {creds_path.exists()}")
print(f"kaggle.json exists: {kaggle_json_path.exists()}")

if creds_path.exists():
    data = json.loads(creds_path.read_text())
    print(f"credentials.json keys: {list(data.keys())}")
    # This file has OAuth tokens from 'kaggle login'

# Check if kaggle CLI auth can use credentials.json
try:
    from kaggle.api.kaggle_api_extended import KaggleApiExtended
    import inspect
    src = inspect.getsource(KaggleApiExtended.authenticate)
    lines = src.split('\n')
    relevant = [l for l in lines if 'credential' in l.lower() or 'kaggle.json' in l.lower() or 'access_token' in l.lower()]
    print("Relevant authenticate source lines:")
    for l in relevant[:15]:
        print(f"  {l.rstrip()}")
except Exception as e:
    print(f"Error: {e}")

# Check if there's an older-style kaggle api module with different auth
print("\nKAGGLE_USERNAME env:", os.environ.get('KAGGLE_USERNAME', 'NOT_SET'))
print("KAGGLE_KEY env:", "SET" if os.environ.get('KAGGLE_KEY') else "NOT_SET")
