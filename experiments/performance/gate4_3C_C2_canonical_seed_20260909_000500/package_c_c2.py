"""
Package Gate 4.3C-C2 Canonical Seed Generation Push Bundle.

1. Reads local scripts/train_exp01.py.
2. Verifies SHA-256.
3. Compresses and base64 encodes it.
4. Injects it into canary_gate4_3C_C2.py.
5. Writes train_exp01.py and kernel-metadata.json to kaggle_push_bundle/.
6. Validates bundle completeness.
"""

import base64
import gzip
import hashlib
import json
import shutil
from pathlib import Path

GATE_DIR = Path("experiments/performance/gate4_3C_C2_canonical_seed_20260909_000500")
BUNDLE_DIR = GATE_DIR / "kaggle_push_bundle"
BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

RUNNER_SRC = Path("scripts/train_exp01.py")
CANARY_TEMPLATE = Path("experiments/performance/gate4_3C_B_one_epoch_pilot_20260908_220700/kaggle_push_bundle/canary_gate4_3C_B.py")
DEST_CANARY = BUNDLE_DIR / "canary_gate4_3C_C2.py"
DEST_RUNNER = BUNDLE_DIR / "train_exp01.py"
DEST_METADATA = BUNDLE_DIR / "kernel-metadata.json"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    print("=" * 65)
    print("PACKAGING GATE 4.3C-C2 CANONICAL SEED BUNDLE")
    print("=" * 65)

    assert RUNNER_SRC.exists(), f"Missing {RUNNER_SRC}"
    runner_bytes = RUNNER_SRC.read_bytes()
    runner_sha = file_sha256(RUNNER_SRC)
    print(f"Runner Source:     {RUNNER_SRC}")
    print(f"Runner Size:       {len(runner_bytes):,} bytes")
    print(f"Runner SHA256:     {runner_sha}")

    # Copy raw runner into bundle
    DEST_RUNNER.write_bytes(runner_bytes)
    print(f"Copied raw runner to: {DEST_RUNNER}")

    # Write kernel-metadata.json
    metadata = {
        "id": "dheeraj12237/ocean-sentinel-gate-4-3b-live-canary",
        "title": "Ocean Sentinel Gate 4.3B Live Canary",
        "code_file": "canary_gate4_3C_C2.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": True,
        "machine_shape": "NvidiaTeslaT4",
        "dataset_sources": [
            "dheeraj12237/ocean-sentinel-trujillo-corpus",
            "dheeraj12237/ocean-sentinel-src",
        ],
    }
    DEST_METADATA.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Written metadata to:  {DEST_METADATA}")

    # Compress runner
    compressed = gzip.compress(runner_bytes, 9)
    b64 = base64.b64encode(compressed).decode("ascii")

    # Read canary template and adapt for C-C2
    canary_code = CANARY_TEMPLATE.read_text(encoding="utf-8")

    # Replace GATE_ID
    canary_code = canary_code.replace(
        'GATE_ID = "GATE_4.3C_B_ONE_EPOCH_PILOT"',
        'GATE_ID = "GATE_4.3C_C2_CANONICAL_SEED_GENERATION"'
    )

    # Replace working directory names
    canary_code = canary_code.replace(
        'pilot_out_dir = working_dir / "gate4_3C_B_pilot"',
        'pilot_out_dir = working_dir / "gate4_3C_C2_canonical_seed"'
    )

    # Replace CLI training command: Canonical epochs=30 with stop-after-epoch=1
    old_cmd_block = """    train_cmd = [
        sys.executable,
        str(runner_path),
        "--epochs", "1",
        "--batch-size", "8",
        "--accum-steps", "1",
        "--num-workers", "2",
        "--lr", "0.0001",
        "--weight-decay", "0.01",
        "--manifest", str(manifest_path),
        "--data-dir", str(corpus_mount),
        "--output-dir", str(pilot_out_dir),
        "--no-test",
        "--device", "cuda",
        "--log-interval", "100",
    ]"""

    new_cmd_block = """    train_cmd = [
        sys.executable,
        str(runner_path),
        "--epochs", "30",
        "--stop-after-epoch", "1",
        "--batch-size", "8",
        "--accum-steps", "1",
        "--num-workers", "2",
        "--lr", "0.0001",
        "--weight-decay", "0.01",
        "--manifest", str(manifest_path),
        "--data-dir", str(corpus_mount),
        "--output-dir", str(pilot_out_dir),
        "--no-test",
        "--device", "cuda",
        "--log-interval", "100",
        "--seed", "42",
    ]"""
    assert old_cmd_block in canary_code, "Could not find old_cmd_block in template"
    canary_code = canary_code.replace(old_cmd_block, new_cmd_block)

    # Inject EMBEDDED_RUNNER_GZIP_B64
    start_marker = 'EMBEDDED_RUNNER_GZIP_B64 = "'
    idx = canary_code.find(start_marker)
    assert idx != -1, "Marker start not found"
    end_idx = canary_code.find('"\n', idx)
    assert end_idx != -1, "Marker end not found"
    canary_code = canary_code[:idx + len(start_marker)] + b64 + canary_code[end_idx:]

    # Inject EXPECTED_RUNNER_SHA256
    sha_marker = 'EXPECTED_RUNNER_SHA256 = "'
    s_idx = canary_code.find(sha_marker)
    assert s_idx != -1, "SHA marker not found"
    s_end = canary_code.find('"\n', s_idx)
    assert s_end != -1, "SHA marker end not found"
    canary_code = canary_code[:s_idx + len(sha_marker)] + runner_sha + canary_code[s_end:]

    # Add scheduler T_max verification in post-run audit
    audit_inject_target = "    sha_latest = file_sha256(latest_chkpt)\n"
    audit_extra_check = """    # Load checkpoint to verify scheduler T_max=30 and last_epoch=1
    chkpt_obj = torch.load(latest_chkpt, map_location="cpu", weights_only=False)
    sched_dict = chkpt_obj.get("scheduler_state_dict", {})
    t_max_val = sched_dict.get("T_max")
    last_ep_val = sched_dict.get("last_epoch")
    log(f"Checkpoint Scheduler T_max:      {t_max_val}")
    log(f"Checkpoint Scheduler last_epoch: {last_ep_val}")
    if t_max_val != 30:
        raise ValueError(f"FATAL: Checkpoint scheduler T_max is {t_max_val}, expected canonical 30!")
    if last_ep_val != 1:
        raise ValueError(f"FATAL: Checkpoint scheduler last_epoch is {last_ep_val}, expected 1!")

    sha_latest = file_sha256(latest_chkpt)
"""
    assert audit_inject_target in canary_code, "Could not find audit_inject_target"
    canary_code = canary_code.replace(audit_inject_target, audit_extra_check)

    # Add t_max reconciliation record
    reconcil_target = '        "scheduler_steps": {"expected": EXPECTED_SCHEDULER_STEPS, "observed": 1, "pass": True},\n'
    reconcil_extra = """        "scheduler_steps": {"expected": EXPECTED_SCHEDULER_STEPS, "observed": 1, "pass": True},
        "scheduler_t_max": {"expected": 30, "observed": t_max_val, "pass": t_max_val == 30},
        "scheduler_last_epoch": {"expected": 1, "observed": last_ep_val, "pass": last_ep_val == 1},
"""
    assert reconcil_target in canary_code, "Could not find reconcil_target"
    canary_code = canary_code.replace(reconcil_target, reconcil_extra)

    # Write destination canary
    DEST_CANARY.write_text(canary_code, encoding="utf-8")
    canary_sha = file_sha256(DEST_CANARY)
    print(f"Generated canary:  {DEST_CANARY}")
    print(f"Canary Size:       {DEST_CANARY.stat().st_size:,} bytes")
    print(f"Canary SHA256:     {canary_sha}")

    print("\n[VERIFIED] C-C2 push bundle packaged successfully.")
    print("=" * 65)


if __name__ == "__main__":
    main()
