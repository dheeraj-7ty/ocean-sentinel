import json
import os
from pathlib import Path

print("=== CANARY MOUNT REHEARSAL REVISION 2 ===")
input_dir = Path("/kaggle/input")
print("Exists /kaggle/input:", input_dir.exists())

all_tree = []
for root, dirs, files in os.walk(input_dir):
    for d in dirs:
        dp = Path(root) / d
        all_tree.append(f"DIR: {dp.as_posix()}")
    for f in files:
        fp = Path(root) / f
        all_tree.append(f"FILE: {fp.as_posix()} ({fp.stat().st_size} bytes)")

print("\n".join(all_tree))

canary_found = any("canary" in x.lower() for x in all_tree)
txt_content = ""
for root, dirs, files in os.walk(input_dir):
    for f in files:
        if "canary" in f:
            txt_content = (Path(root) / f).read_text(encoding="utf-8")
            print("FOUND CONTENT:", txt_content[:100])

out_file = Path("/kaggle/working/rehearsal_results.json")
out_file.write_text(
    json.dumps(
        {"tree": all_tree, "canary_found": canary_found, "content_match": "CANARY_TEST_TIMESTAMP" in txt_content},
        indent=2,
    ),
    encoding="utf-8",
)
