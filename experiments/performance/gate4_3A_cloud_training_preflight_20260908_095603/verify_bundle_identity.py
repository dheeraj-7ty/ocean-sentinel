import hashlib, json, os
from pathlib import Path

BUNDLE_DIR = Path('D:/Projects/ocean-sentinel/experiments/performance/gate4_3A_cloud_training_preflight_20260908_095603/bundle')
MANIFEST_PATH = Path('D:/Projects/ocean-sentinel/experiments/performance/gate4_3A_cloud_training_preflight_20260908_095603/cloud_bundle_manifest.json')

# Load manifest
manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
expected_files = {f['relative_path']: f for f in manifest['files']}

# Recompute actual
actual_files = {}
for p in sorted(BUNDLE_DIR.rglob('*')):
    if p.is_file():
        rel = p.relative_to(BUNDLE_DIR).as_posix()
        data = p.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest().upper()
        actual_files[rel] = {'size_bytes': len(data), 'sha256': sha256}

# Compare
mismatches = []
missing = []
extra = []

for rel, exp in expected_files.items():
    if rel not in actual_files:
        missing.append(rel)
    else:
        act = actual_files[rel]
        if act['sha256'] != exp['sha256'] or act['size_bytes'] != exp['size_bytes']:
            mismatches.append({
                'file': rel,
                'expected_sha': exp['sha256'],
                'actual_sha': act['sha256'],
                'expected_size': exp['size_bytes'],
                'actual_size': act['size_bytes']
            })

for rel in actual_files:
    if rel not in expected_files:
        extra.append(rel)

print(f'Expected files: {len(expected_files)}')
print(f'Actual files:   {len(actual_files)}')
print(f'Missing files:  {missing}')
print(f'Extra files:    {extra}')
print(f'Mismatches:     {mismatches}')
total_bytes = sum(f['size_bytes'] for f in actual_files.values())
print(f'Total bytes (actual): {total_bytes}')
print(f'Total bytes (manifest): {manifest["total_size_bytes"]}')
result = 'PASS' if not mismatches and not missing and not extra else 'FAIL'
print(f'BUNDLE_IDENTITY_CHECK: {result}')

# Output per-file identity for audit
print('\nPer-file SHA256 (actual):')
for rel, info in sorted(actual_files.items()):
    match = 'OK' if rel in expected_files and expected_files[rel]['sha256'] == info['sha256'] else 'MISMATCH/NEW'
    print(f'  {match}  {info["sha256"][:16]}...  {info["size_bytes"]:>8}  {rel}')
