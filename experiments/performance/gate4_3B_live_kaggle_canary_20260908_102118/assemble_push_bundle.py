import hashlib, json, os, shutil
from pathlib import Path

GATE_DIR = Path('D:/Projects/ocean-sentinel/experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118')
PUSH_DIR = GATE_DIR / 'kaggle_push_bundle'
PROJECT_ROOT = Path('D:/Projects/ocean-sentinel')
SRC_DIR = PROJECT_ROOT / 'src'

# 1. Copy canary script as the main code file
shutil.copy2(GATE_DIR / 'canary_gate4_3B.py', PUSH_DIR / 'canary_gate4_3B.py')

# 2. Copy src from project root
dst_src = PUSH_DIR / 'src'
if dst_src.exists():
    shutil.rmtree(dst_src)
shutil.copytree(SRC_DIR, dst_src, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

# 3. Verify secret scan (refined patterns only — real credentials, not path strings)
import re
SECRET_PATTERNS = [
    re.compile(r'"key":\s*"[a-f0-9]{32}"', re.IGNORECASE),
    re.compile(r'KAGGLE_KEY\s*=\s*["\'][a-f0-9]{32}["\']', re.IGNORECASE),
    re.compile(r'ghp_[a-zA-Z0-9]{20,}', re.IGNORECASE),
    re.compile(r'AIza[0-9A-Za-z-_]{35}', re.IGNORECASE),
    re.compile(r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----'),
    re.compile(r'"private_key":\s*"-----BEGIN'),
]

violations = []
files_info = []
for p in sorted(PUSH_DIR.rglob('*')):
    if p.is_file():
        rel = p.relative_to(PUSH_DIR).as_posix()
        data = p.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest().upper()
        files_info.append({'relative_path': rel, 'size_bytes': len(data), 'sha256': sha256})
        try:
            text = data.decode('utf-8', errors='ignore')
            for pat in SECRET_PATTERNS:
                m = pat.search(text)
                if m:
                    violations.append({'file': rel, 'pattern': pat.pattern})
        except Exception:
            pass

total_bytes = sum(f['size_bytes'] for f in files_info)
manifest = {
    'gate': 'GATE_4.3B',
    'kernel_id': 'dheeraj12237/ocean-sentinel-gate4-3b-canary',
    'secret_audit': {'passed': len(violations) == 0, 'violations': violations},
    'total_files': len(files_info),
    'total_size_bytes': total_bytes,
    'files': files_info,
}
manifest_out = GATE_DIR / 'bundle_identity.json'
manifest_out.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(f'Bundle files: {len(files_info)}')
print(f'Total bytes:  {total_bytes}')
print(f'Secret violations: {len(violations)}')
print(f'Manifest written: {manifest_out}')
print('BUNDLE_ASSEMBLY:', 'PASS' if not violations else 'FAIL')
