import json, urllib.request, urllib.error, time
from pathlib import Path

creds = json.loads(Path('C:/Users/Dheeraj/.kaggle/credentials.json').read_text())
access_token = creds['access_token']
username = creds['username']
expiry = creds.get('access_token_expiration', '')
now_utc = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

print(f'Username: {username}')
print(f'Token expiry: {expiry}')
print(f'Current UTC: {now_utc}')
print(f'Token expired: {expiry < now_utc}')

base_url = 'https://www.kaggle.com/api/v1'

# Test 1: List kernels (mine=true)
try:
    req = urllib.request.Request(
        f'{base_url}/kernels',
        headers={'Authorization': f'Bearer {access_token}'},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        print('GET /kernels OK:', str(data)[:200])
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='ignore')
    print(f'GET /kernels: HTTP {e.code}: {body[:300]}')
except Exception as e:
    print(f'GET /kernels error: {e}')

# Test 2: List kernels for user
try:
    req = urllib.request.Request(
        f'{base_url}/kernels/list?userNames={username}',
        headers={'Authorization': f'Bearer {access_token}'},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        print(f'GET /kernels/list OK: {len(data) if isinstance(data, list) else data}')
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='ignore')
    print(f'GET /kernels/list: HTTP {e.code}: {body[:300]}')
except Exception as e:
    print(f'GET /kernels/list error: {e}')
