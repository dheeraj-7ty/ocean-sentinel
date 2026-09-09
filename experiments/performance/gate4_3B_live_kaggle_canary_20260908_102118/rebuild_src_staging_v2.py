"""Rebuild src_dataset_staging_v2 with ocean_sentinel/ properly nested."""
import shutil, json, re
from pathlib import Path

GATE_DIR = Path('experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118')
SRC_DIR = Path('src/ocean_sentinel')
STAGING_V2 = GATE_DIR / 'src_dataset_staging_v2'

if STAGING_V2.exists():
    shutil.rmtree(STAGING_V2)
STAGING_V2.mkdir(parents=True)

dest = STAGING_V2 / 'ocean_sentinel'
shutil.copytree(SRC_DIR, dest)

for pc in list(dest.rglob('__pycache__')):
    shutil.rmtree(pc)

metadata = {
    'title': 'Ocean Sentinel Source Code',
    'id': 'dheeraj12237/ocean-sentinel-src',
    'licenses': [{'name': 'other'}]
}
(STAGING_V2 / 'dataset-metadata.json').write_text(json.dumps(metadata, indent=2))

py_files = list(dest.rglob('*.py'))
init_exists = (dest / '__init__.py').exists()
print(f'Python files: {len(py_files)}')
print(f'ocean_sentinel/__init__.py exists: {init_exists}')
print(f'Expected Kaggle mount after extraction:')
print(f'  /kaggle/input/ocean-sentinel-src/ocean_sentinel/__init__.py')
print(f'  sys.path entry: /kaggle/input/ocean-sentinel-src/')
print(f'Staging v2 dir: {STAGING_V2}')

SECRET_PATTERNS = [
    re.compile(r'Bearer\s+[A-Za-z0-9\-.]{20,}'),
    re.compile(r'api[_-]?key\s*[=:]\s*[A-Za-z0-9]{16,}', re.IGNORECASE),
]
violations = 0
for pyfile in dest.rglob('*.py'):
    content = pyfile.read_text(encoding='utf-8', errors='ignore')
    for pat in SECRET_PATTERNS:
        if pat.search(content):
            print(f'  SECRET VIOLATION: {pyfile}')
            violations += 1
print(f'Secret violations: {violations}')
print('STAGING_V2: READY' if violations == 0 else 'STAGING_V2: FAIL')
