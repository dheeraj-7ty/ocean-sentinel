import json
import os
from pathlib import Path

print("=== HIERARCHICAL CANARY MOUNT REHEARSAL ===")
input_dir = Path("/kaggle/input")
print("Exists /kaggle/input:", input_dir.exists())

all_tree = []
for root, dirs, files in os.walk(input_dir):
    for d in sorted(dirs):
        dp = Path(root) / d
        all_tree.append(f"DIR: {dp.as_posix()}")
    for f in sorted(files):
        fp = Path(root) / f
        all_tree.append(f"FILE: {fp.as_posix()} ({fp.stat().st_size} bytes)")

print("\n".join(all_tree))

# Check for nested paths
image_path = None
mask_path = None
manifest_path = None

for root, dirs, files in os.walk(input_dir):
    for f in files:
        full_path = (Path(root) / f).as_posix()
        if "00000.tif" in full_path and "images" in full_path:
            image_path = full_path
        elif "00000.tif" in full_path and "masks" in full_path:
            mask_path = full_path
        elif "integrity_manifest.json" in full_path:
            manifest_path = full_path

print(f"Found image: {image_path}")
print(f"Found mask: {mask_path}")
print(f"Found manifest: {manifest_path}")

out_file = Path("/kaggle/working/hierarchical_rehearsal_results.json")
out_file.write_text(
    json.dumps(
        {
            "tree": all_tree,
            "image_path": image_path,
            "mask_path": mask_path,
            "manifest_path": manifest_path,
            "hierarchy_preserved": bool(image_path and mask_path and manifest_path),
        },
        indent=2,
    ),
    encoding="utf-8",
)
print("WROTE rehearsal results")
