"""
Refresh the expired Kaggle OAuth access_token using the refresh_token.
"""
import json, urllib.request, urllib.error, urllib.parse, time
from pathlib import Path

creds_path = Path('C:/Users/Dheeraj/.kaggle/credentials.json')
creds = json.loads(creds_path.read_text())

refresh_token = creds.get('refresh_token', '')
username = creds.get('username', '')

print(f"Username: {username}")
print(f"Refresh token length: {len(refresh_token)}")
print(f"Current access_token expired: {creds.get('access_token_expiration', '') < time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())}")

# Kaggle OAuth token endpoint
# Kaggle uses Google OAuth with client credentials
# The refresh flow requires the Kaggle client_id and client_secret
# These are NOT in the credentials.json file

# Alternative: use the KAGGLE_HUB refresh endpoint
# Try Kaggle's token refresh API
token_endpoints = [
    "https://www.kaggle.com/api/v1/authenticate/token",
    "https://www.kaggle.com/api/oauth2/token",
]

for endpoint in token_endpoints:
    data = urllib.parse.urlencode({
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }).encode('utf-8')
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            print(f"Token refresh at {endpoint}: {result.keys()}")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        print(f"Token refresh at {endpoint}: HTTP {e.code} - {body[:200]}")
    except Exception as e:
        print(f"Token refresh at {endpoint}: {e}")
