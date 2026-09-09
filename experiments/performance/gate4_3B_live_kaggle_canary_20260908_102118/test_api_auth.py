"""
Test Kaggle API kernel push via OAuth access_token.
Uses Kaggle REST API directly (not the kaggle Python package).
"""
import json, os, sys, time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

creds_path = Path('C:/Users/Dheeraj/.kaggle/credentials.json')
creds = json.loads(creds_path.read_text())
access_token = creds.get('access_token', '')
username = creds.get('username', '')
token_len = len(access_token)

print(f"Username: {username}")
print(f"Access token length: {token_len}")
print(f"Token expiration: {creds.get('access_token_expiration', 'N/A')}")

# Try listing kernels via REST API with access token
base_url = "https://www.kaggle.com/api/v1"
headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json',
}

# Test API connectivity
try:
    req = urllib.request.Request(
        f"{base_url}/kernels/list?mine=true&pageSize=5",
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f"API Status: SUCCESS (HTTP 200)")
        if isinstance(data, list):
            print(f"Kernels returned: {len(data)}")
            for k in data[:3]:
                print(f"  - {k.get('ref', 'unknown')}")
        else:
            print(f"Response type: {type(data)}")
            print(f"Response (partial): {str(data)[:200]}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
    body = e.read().decode('utf-8', errors='ignore')
    print(f"Response body: {body[:500]}")
except Exception as e:
    print(f"Error: {e}")
