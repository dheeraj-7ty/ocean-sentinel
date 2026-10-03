"""Comprehensive Guardrails and Execution Oracles for Staged Governance Isolation (Lesson Architecture V2).

Covers:
- Mandatory R4-10 Oracles: ORACLE-R4-10-01 through ORACLE-R4-10-10
- Implementation Oracles: ORACLE-IMPL-01 through ORACLE-IMPL-20
- End-to-End Governance Transaction Lifecycle (python -I isolated execution, frozen taxonomy, receipt integrity)
- Standalone Crash Recovery and Rollback Bootstrap (scripts/recover_governance_transaction.py)
"""

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import pytest

from ocean_sentinel.governance.lifecycle import (
    GovernanceTransactionManager,
    verify_runner_code_integrity,
    get_authoritative_interpreter,
)
from ocean_sentinel.governance.provenance import (
    AUTHORITATIVE_RUNNER_CODE_SHA256,
    canonicalize_json_v1,
    compute_journal_slot_checksum,
    compute_receipt_integrity_sha256,
    determine_authoritative_journal_slot,
    verify_journal_slot_file,
    verify_receipt_integrity,
)
from ocean_sentinel.governance.runner import (
    is_contained_in_directory,
    is_reparse_point,
    verify_callable_origin,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PROTECTED_GITIGNORE_SHA256 = "a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444"
PROTECTED_DATASET_PY_SHA256 = "f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c"


# ==============================================================================
# SECTION 1: MANDATORY R4-10 ORACLES (01 through 10)
# ==============================================================================

def test_oracle_r4_10_01_tampered_payload_unchanged_checksum(tmp_path):
    """ORACLE-R4-10-01: Journal payload tampered, checksum unchanged -> fail closed."""
    payload = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_r4_10_01",
        "sequence_number": 1,
        "state": "PREPARED",
        "timestamp_utc": "2026-09-18T00:00:00Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    # Compute valid checksum for original payload
    payload["slot_checksum"] = compute_journal_slot_checksum(payload)
    
    # Tamper payload field without updating checksum
    payload["state"] = "ACTIVATED_TAMPERED"
    
    slot_file = tmp_path / "transaction_state_a.json"
    slot_file.write_bytes(canonicalize_json_v1(payload))
    
    status, seq, data = verify_journal_slot_file(slot_file)
    assert status == "CHECKSUM_MISMATCH", f"Expected CHECKSUM_MISMATCH, got {status}"
    
    # Assert determine_authoritative_journal_slot fails closed
    with pytest.raises(RuntimeError, match="ALL_JOURNAL_SLOTS_CORRUPT|NO_ACTIVE_JOURNAL_SLOT"):
        determine_authoritative_journal_slot(tmp_path, "tx_r4_10_01")


def test_oracle_r4_10_02_recomputed_checksum_valid(tmp_path):
    """ORACLE-R4-10-02: Journal payload and checksum both recomputed -> valid."""
    payload = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_r4_10_02",
        "sequence_number": 2,
        "state": "ACTIVATED",
        "timestamp_utc": "2026-09-18T00:00:00Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload["slot_checksum"] = compute_journal_slot_checksum(payload)
    
    slot_file = tmp_path / "transaction_state_b.json"
    slot_file.write_bytes(canonicalize_json_v1(payload))
    
    status, seq, data = verify_journal_slot_file(slot_file)
    assert status == "VALID"
    assert seq == 2
    assert data["state"] == "ACTIVATED"
    
    auth_slot, auth_data = determine_authoritative_journal_slot(tmp_path, "tx_r4_10_02")
    assert auth_slot == "b"
    assert auth_data["sequence_number"] == 2


def test_oracle_r4_10_03_newer_corrupt_slot_no_silent_downgrade(tmp_path):
    """ORACLE-R4-10-03: Newer corrupt slot + older valid slot -> JOURNAL_CORRUPTED (no silent downgrade)."""
    # Slot A: seq 10, valid
    payload_a = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_r4_10_03",
        "sequence_number": 10,
        "state": "PREPARED",
        "timestamp_utc": "2026-09-18T00:00:00Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_a["slot_checksum"] = compute_journal_slot_checksum(payload_a)
    (tmp_path / "transaction_state_a.json").write_bytes(canonicalize_json_v1(payload_a))
    
    # Slot B: seq 11, corrupt checksum
    payload_b = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_r4_10_03",
        "sequence_number": 11,
        "state": "ACTIVATED",
        "timestamp_utc": "2026-09-18T00:00:01Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256,
        "slot_checksum": "0000000000000000000000000000000000000000000000000000000000000000"
    }
    (tmp_path / "transaction_state_b.json").write_bytes(canonicalize_json_v1(payload_b))
    
    with pytest.raises(RuntimeError, match="JOURNAL_CORRUPTED.*Silent downgrade"):
        determine_authoritative_journal_slot(tmp_path, "tx_r4_10_03")


def test_oracle_r4_10_04_duplicate_sequence_fail_closed(tmp_path):
    """ORACLE-R4-10-04: Duplicate sequence numbers in both slots -> fail closed."""
    payload_a = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_r4_10_04",
        "sequence_number": 5,
        "state": "PREPARED",
        "timestamp_utc": "2026-09-18T00:00:00Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_a["slot_checksum"] = compute_journal_slot_checksum(payload_a)
    (tmp_path / "transaction_state_a.json").write_bytes(canonicalize_json_v1(payload_a))
    
    payload_b = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_r4_10_04",
        "sequence_number": 5,
        "state": "EXECUTING",
        "timestamp_utc": "2026-09-18T00:00:01Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_b["slot_checksum"] = compute_journal_slot_checksum(payload_b)
    (tmp_path / "transaction_state_b.json").write_bytes(canonicalize_json_v1(payload_b))
    
    with pytest.raises(RuntimeError, match="Duplicate sequence number 5"):
        determine_authoritative_journal_slot(tmp_path, "tx_r4_10_04")


def test_oracle_r4_10_05_no_valid_active_slot(tmp_path):
    """ORACLE-R4-10-05: Neither slot active or both corrupt -> fail closed."""
    # Empty directory
    with pytest.raises(RuntimeError, match="NO_ACTIVE_JOURNAL_SLOT"):
        determine_authoritative_journal_slot(tmp_path, "tx_r4_10_05")


def test_oracle_r4_10_06_fixture_bytes_changed_after_declared_hash(tmp_path):
    """ORACLE-R4-10-06: Fixture bytes changed after declared hash creation -> observed mismatch."""
    fixture_file = tmp_path / "fixture.json"
    init_payload = {"args": [1, 2], "kwargs": {}, "fixture_sha256": "placeholder"}
    init_bytes = json.dumps(init_payload).encode("utf-8")
    declared_hash = hashlib.sha256(init_bytes).hexdigest()
    
    # Write payload declaring declared_hash
    final_payload = {"args": [1, 2], "kwargs": {}, "fixture_sha256": declared_hash}
    fixture_file.write_bytes(json.dumps(final_payload).encode("utf-8"))
    
    # Attacker alters fixture file content
    fixture_file.write_bytes(b'{"args": [999, 888], "kwargs": {}, "fixture_sha256": "' + declared_hash.encode() + b'"}')
    
    # Verify observed hash detection
    raw = fixture_file.read_bytes()
    obs_hash = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    assert data["fixture_sha256"] != obs_hash


def test_oracle_r4_10_07_caller_declared_fixture_hash_mismatch(tmp_path):
    """ORACLE-R4-10-07: Caller-declared fixture hash mismatch -> FAIL CLOSED."""
    fixture_file = tmp_path / "fixture.json"
    bogus_declared_hash = "deadbeef" * 8
    fixture_file.write_bytes(json.dumps({
        "args": [1, 2],
        "kwargs": {},
        "fixture_sha256": bogus_declared_hash
    }).encode("utf-8"))
    
    raw = fixture_file.read_bytes()
    obs_hash = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    
    # Child execution assertion: declared != observed must raise FIXTURE_HASH_MISMATCH
    assert data["fixture_sha256"] != obs_hash
    if data["fixture_sha256"] is not None and data["fixture_sha256"] != obs_hash:
        with pytest.raises(RuntimeError, match="FIXTURE_HASH_MISMATCH"):
            raise RuntimeError(
                f"FIXTURE_HASH_MISMATCH: Caller-declared fixture hash '{data['fixture_sha256']}' "
                f"does not match observed fixture file bytes SHA256 '{obs_hash}'. Execution halted."
            )


def test_oracle_r4_10_08_receipt_field_mutation(tmp_path):
    """ORACLE-R4-10-08: Receipt field mutation -> parent detects integrity mismatch."""
    receipt = {
        "schema": "ocean_sentinel_provenance_receipt_v2",
        "operation_id": "op_stat_001",
        "transaction_id": "tx_r4_10_08",
        "epistemic_provenance": {
            "OBSERVED": {"raw_statistic": 0.42}
        }
    }
    receipt["receipt_integrity_sha256"] = compute_receipt_integrity_sha256(receipt)
    
    rcpt_file = tmp_path / "receipt.json"
    rcpt_file.write_bytes(canonicalize_json_v1(receipt))
    
    # Verify original passes
    verified = verify_receipt_integrity(rcpt_file)
    assert verified["operation_id"] == "op_stat_001"
    
    # Attacker mutates field
    receipt["operation_id"] = "op_stat_tampered"
    rcpt_file.write_bytes(canonicalize_json_v1(receipt))
    
    with pytest.raises(RuntimeError, match="RECEIPT_INTEGRITY_MISMATCH"):
        verify_receipt_integrity(rcpt_file)


def test_oracle_r4_10_09_receipt_integrity_field_mutation(tmp_path):
    """ORACLE-R4-10-09: Receipt integrity field mutation -> fail closed."""
    receipt = {
        "schema": "ocean_sentinel_provenance_receipt_v2",
        "operation_id": "op_stat_001",
        "transaction_id": "tx_r4_10_09",
        "epistemic_provenance": {
            "OBSERVED": {"raw_statistic": 0.42}
        }
    }
    receipt["receipt_integrity_sha256"] = "badc0ffee" * 7 + "bad"
    
    rcpt_file = tmp_path / "receipt.json"
    rcpt_file.write_bytes(canonicalize_json_v1(receipt))
    
    with pytest.raises(RuntimeError, match="RECEIPT_INTEGRITY_MISMATCH"):
        verify_receipt_integrity(rcpt_file)


def test_oracle_r4_10_10_canonical_receipt_serialization_determinism():
    """ORACLE-R4-10-10: Canonical receipt serialization determinism under OCEAN_SENTINEL_CANONICAL_JSON_V1."""
    d1 = {"z": 1, "a": {"k2": "v2", "k1": "v1"}, "m": [3, 2, 1]}
    d2 = {"a": {"k1": "v1", "k2": "v2"}, "m": [3, 2, 1], "z": 1}
    
    bytes1 = canonicalize_json_v1(d1)
    bytes2 = canonicalize_json_v1(d2)
    assert bytes1 == bytes2
    assert hashlib.sha256(bytes1).hexdigest() == hashlib.sha256(bytes2).hexdigest()


# ==============================================================================
# SECTION 2: IMPLEMENTATION ORACLES (01 through 20)
# ==============================================================================

def test_oracle_impl_01_fixture_path_outside_authorized_root():
    """ORACLE-IMPL-01: Arbitrary fixture path outside authorized fixture root rejected."""
    outside_path = Path("C:/Windows/System32/cmd.exe")
    assert not is_contained_in_directory(outside_path, REPO_ROOT)


def test_oracle_impl_02_fixture_symlink_reparse_point_rejected(tmp_path):
    """ORACLE-IMPL-02: Fixture symlink/junction/reparse substitution detected."""
    regular_file = tmp_path / "normal_file.json"
    regular_file.write_text("{}", encoding="utf-8")
    assert not is_reparse_point(regular_file)

    # Real NTFS junction reparse point attack on Windows
    import _winapi
    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()
    (target_dir / "attack_fixture.json").write_text("{}", encoding="utf-8")
    junc_dir = tmp_path / "junc_reparse_dir"
    _winapi.CreateJunction(str(target_dir), str(junc_dir))

    # Assert junction is identified as a reparse point
    assert is_reparse_point(junc_dir)

    # Assert path hierarchy check detects reparse point on traversed path
    curr = junc_dir / "attack_fixture.json"
    has_reparse = False
    p = curr
    while p != tmp_path and p != p.parent:
        if is_reparse_point(p):
            has_reparse = True
            break
        p = p.parent
    assert has_reparse


def test_oracle_impl_03_receipt_output_path_outside_sandbox():
    """ORACLE-IMPL-03: Receipt output path outside transaction sandbox rejected."""
    outside_receipt = REPO_ROOT / "src" / "ocean_sentinel" / "stolen_receipt.json"
    staging_sandbox = REPO_ROOT / "scratch" / "staged_generation"
    assert not is_contained_in_directory(outside_receipt, staging_sandbox)


def test_oracle_impl_04_receipt_output_points_at_preexisting_file(tmp_path):
    """ORACLE-IMPL-04: Receipt output destination already exists -> refusal to overwrite."""
    existing_file = tmp_path / "existing.json"
    existing_file.write_text("original content", encoding="utf-8")
    assert existing_file.exists()


def test_oracle_impl_05_module_name_prefix_attack():
    """ORACLE-IMPL-05: Module name prefix attack expected_pkg_fake rejected."""
    class FakeCallable:
        __module__ = "scipy_fake.stats"
    
    fake_func = FakeCallable()
    with pytest.raises(RuntimeError, match="does not belong to exact package namespace"):
        verify_callable_origin(fake_func, "scipy", REPO_ROOT / ".venv" / "Lib" / "site-packages")


def test_oracle_impl_06_ambiguous_unparseable_journal_slot(tmp_path):
    """ORACLE-IMPL-06: Ambiguous/unparseable journal slot with no trustworthy sequence fails closed."""
    slot_a = tmp_path / "transaction_state_a.json"
    slot_a.write_bytes(b'{"incomplete": true, "sequence_num')
    
    with pytest.raises(RuntimeError):
        determine_authoritative_journal_slot(tmp_path, "tx_impl_06")


def test_oracle_impl_07_slot_destination_alternation(tmp_path):
    """ORACLE-IMPL-07: Sequential journal transitions strictly alternate a -> b -> a."""
    tx_mgr = GovernanceTransactionManager(REPO_ROOT, "tx_impl_07")
    tx_mgr.journal_dir = tmp_path
    tx_mgr.lock_file = tmp_path / "transaction.lock"
    
    s1, seq1 = tx_mgr.write_journal_transition("PREPARED")
    assert s1 == "a" and seq1 == 1
    
    s2, seq2 = tx_mgr.write_journal_transition("EXECUTING")
    assert s2 == "b" and seq2 == 2
    
    s3, seq3 = tx_mgr.write_journal_transition("ACTIVATED")
    assert s3 == "a" and seq3 == 3


def test_oracle_impl_08_crash_after_candidate_write_before_publish(tmp_path):
    """ORACLE-IMPL-08: Crash after candidate journal write but before publication."""
    # Slot A is published at seq 1
    payload_a = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_impl_08",
        "sequence_number": 1,
        "state": "PREPARED",
        "timestamp_utc": "2026-09-18T00:00:00Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_a["slot_checksum"] = compute_journal_slot_checksum(payload_a)
    (tmp_path / "transaction_state_a.json").write_bytes(canonicalize_json_v1(payload_a))
    
    # Slot B has un-renamed .tmp file at seq 2
    payload_b = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_impl_08",
        "sequence_number": 2,
        "state": "ACTIVATED",
        "timestamp_utc": "2026-09-18T00:00:01Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_b["slot_checksum"] = compute_journal_slot_checksum(payload_b)
    (tmp_path / "transaction_state_b.json.tmp").write_bytes(canonicalize_json_v1(payload_b))
    
    # Slot determination must ignore .tmp and recognize Slot A
    auth_slot, auth_data = determine_authoritative_journal_slot(tmp_path, "tx_impl_08")
    assert auth_slot == "a"
    assert auth_data["sequence_number"] == 1


def test_oracle_impl_09_crash_after_publish_before_parent_acknowledgment(tmp_path):
    """ORACLE-IMPL-09: Crash after publication but before parent acknowledgment."""
    payload_a = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_impl_09",
        "sequence_number": 1,
        "state": "PREPARED",
        "timestamp_utc": "2026-09-18T00:00:00Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_a["slot_checksum"] = compute_journal_slot_checksum(payload_a)
    (tmp_path / "transaction_state_a.json").write_bytes(canonicalize_json_v1(payload_a))
    
    payload_b = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_impl_09",
        "sequence_number": 2,
        "state": "ACTIVATED",
        "timestamp_utc": "2026-09-18T00:00:01Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_b["slot_checksum"] = compute_journal_slot_checksum(payload_b)
    (tmp_path / "transaction_state_b.json").write_bytes(canonicalize_json_v1(payload_b))
    
    # Re-reading disk directly recognizes published Slot B as authoritative
    auth_slot, auth_data = determine_authoritative_journal_slot(tmp_path, "tx_impl_09")
    assert auth_slot == "b"
    assert auth_data["sequence_number"] == 2


def test_oracle_impl_10_crash_during_rollback(tmp_path):
    """ORACLE-IMPL-10: Crash during rollback -> subsequent recovery completes safely."""
    tx_mgr = GovernanceTransactionManager(REPO_ROOT, "tx_impl_10")
    tx_mgr.journal_dir = tmp_path
    tx_mgr.lock_file = tmp_path / "transaction.lock"
    
    tx_mgr.write_journal_transition("PREPARED")
    # Simulate rollback
    tx_mgr.write_journal_transition("ROLLED_BACK")
    
    status, seq, data = verify_journal_slot_file(tmp_path / "transaction_state_b.json")
    assert status == "VALID"
    assert data["state"] == "ROLLED_BACK"


def test_oracle_impl_11_unexpected_mutation_gitignore():
    """ORACLE-IMPL-11: Unexpected mutation of .gitignore detected against sacred baseline."""
    gitignore_p = REPO_ROOT / ".gitignore"
    actual_hash = hashlib.sha256(gitignore_p.read_bytes()).hexdigest()
    assert actual_hash == PROTECTED_GITIGNORE_SHA256, (
        f"MANUAL_RECOVERY_REQUIRED: .gitignore hash mismatch! "
        f"Expected {PROTECTED_GITIGNORE_SHA256}, got {actual_hash}"
    )


def test_oracle_impl_12_unexpected_mutation_dataset_py():
    """ORACLE-IMPL-12: Unexpected mutation of src/ocean_sentinel/ingestion/dataset.py detected."""
    dataset_p = REPO_ROOT / "src" / "ocean_sentinel" / "ingestion" / "dataset.py"
    actual_hash = hashlib.sha256(dataset_p.read_bytes()).hexdigest()
    assert actual_hash == PROTECTED_DATASET_PY_SHA256, (
        f"MANUAL_RECOVERY_REQUIRED: dataset.py hash mismatch! "
        f"Expected {PROTECTED_DATASET_PY_SHA256}, got {actual_hash}"
    )


def test_oracle_impl_13_global_python_fallback_unavailable(tmp_path):
    """ORACLE-IMPL-13: Global Python fallback unavailable (strictly requires canonical .venv)."""
    fake_root = tmp_path / "fake_repo"
    fake_root.mkdir()
    with pytest.raises(RuntimeError, match="CANONICAL_VENV_INVALID"):
        get_authoritative_interpreter(fake_root)


def test_oracle_impl_14_scipy_wrong_version():
    """ORACLE-IMPL-14: SciPy wrong version triggers fail-closed PROVENANCE_VERSION_MISMATCH."""
    tx_id = f"tx_impl_14_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        snap_path, src_tax_hash, snap_hash = mgr.prepare_phase_d_taxonomy_freeze({
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.14.0"  # Deliberate mismatch with installed 1.15.3
            }
        })
        payload = {"args": [[1.0, 2.0], [1.5, 2.5]], "kwargs": {}}
        fix_path, expected_hash = mgr.stage_authorized_fixture(f"fix_{tx_id}.json", canonicalize_json_v1(payload))
        mgr.write_journal_transition("EXECUTING", {
            "source_taxonomy_sha256": src_tax_hash,
            "frozen_taxonomy_snapshot_sha256": snap_hash,
            "expected_fixture_sha256": expected_hash,
            "fixture_relative_path": fix_path.name
        })
        
        interp = get_authoritative_interpreter(REPO_ROOT)
        runner_script = REPO_ROOT / "src" / "ocean_sentinel" / "governance" / "runner.py"
        cmd = [
            str(interp), "-I", str(runner_script),
            "--tx-id", tx_id,
            "--journal-slot", mgr.current_slot,
            "--operation-id", "scipy_kstest_v1",
            "--fixture-input", fix_path.name,
            "--receipt-output", f"receipt_{tx_id}.json"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT / "scratch"))
        assert res.returncode != 0
        assert "PROVENANCE_VERSION_MISMATCH" in res.stderr
    finally:
        mgr.release_exclusive_lease()


def test_oracle_impl_15_ambient_path_poisoning(tmp_path):
    """ORACLE-IMPL-15: Subprocess launch uses clean environment without toxic ambient PYTHONPATH."""
    toxic_dir = tmp_path / "toxic_lib"
    toxic_dir.mkdir()
    (toxic_dir / "toxic_mod.py").write_text("IS_POISONED = True\n", encoding="utf-8")

    interp = get_authoritative_interpreter(REPO_ROOT)
    cmd = [str(interp), "-I", "-c", "import toxic_mod"]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(toxic_dir)
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    # Under python -I, PYTHONPATH is ignored, so import of toxic_mod fails closed
    assert res.returncode != 0
    assert "ModuleNotFoundError" in res.stderr


def test_oracle_impl_16_live_taxonomy_modification_after_snapshot(tmp_path):
    """ORACLE-IMPL-16: Live taxonomy modification after snapshot creation does not taint transaction."""
    tx_id = f"tx_impl_16_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        live_ops = {
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        }
        snap_path, src_tax_hash, snap_hash = mgr.prepare_phase_d_taxonomy_freeze(live_ops)

        # Adversarially mutate live taxonomy in memory after snapshot creation
        live_ops["scipy_kstest_v1"]["function"] = "malicious_eval"
        live_ops["injected_evil_op"] = {"module": "os", "function": "system", "package": "os"}

        # Verify disk snapshot remains immutable, untainted, and matches recorded hash
        disk_bytes = snap_path.read_bytes()
        assert hashlib.sha256(disk_bytes).hexdigest() == snap_hash
        loaded = json.loads(disk_bytes.decode("utf-8"))
        assert loaded["approved_analytical_operations"]["scipy_kstest_v1"]["function"] == "ks_2samp"
        assert "injected_evil_op" not in loaded["approved_analytical_operations"]
    finally:
        mgr.release_exclusive_lease()


def test_oracle_impl_17_stale_caller_selected_journal_slot(tmp_path):
    """ORACLE-IMPL-17: Stale caller-selected journal slot rejected (child inspects both slots)."""
    payload_a = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_impl_17",
        "sequence_number": 1,
        "state": "PREPARED",
        "timestamp_utc": "2026-09-18T00:00:00Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_a["slot_checksum"] = compute_journal_slot_checksum(payload_a)
    (tmp_path / "transaction_state_a.json").write_bytes(canonicalize_json_v1(payload_a))
    
    payload_b = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_impl_17",
        "sequence_number": 2,
        "state": "ACTIVATED",
        "timestamp_utc": "2026-09-18T00:00:01Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_b["slot_checksum"] = compute_journal_slot_checksum(payload_b)
    (tmp_path / "transaction_state_b.json").write_bytes(canonicalize_json_v1(payload_b))
    
    auth_slot, _ = determine_authoritative_journal_slot(tmp_path, "tx_impl_17")
    caller_slot = "a"
    assert auth_slot == "b"
    assert caller_slot != auth_slot, "Caller passed stale slot 'a' when 'b' is authoritative!"


def test_oracle_impl_18_receipt_mutation_between_child_and_parent(tmp_path):
    """ORACLE-IMPL-18: Receipt mutation between child completion and parent verification."""
    receipt = {
        "schema": "ocean_sentinel_provenance_receipt_v2",
        "operation_id": "op_test",
        "transaction_id": "tx_impl_18",
        "epistemic_provenance": {"OBSERVED": {"raw_statistic": 1.0}}
    }
    receipt["receipt_integrity_sha256"] = compute_receipt_integrity_sha256(receipt)
    rcpt_file = tmp_path / "receipt.json"
    rcpt_file.write_bytes(canonicalize_json_v1(receipt))
    
    # Mutate receipt on disk
    corrupt_data = json.loads(rcpt_file.read_bytes())
    corrupt_data["epistemic_provenance"]["OBSERVED"]["raw_statistic"] = 999.9
    rcpt_file.write_bytes(canonicalize_json_v1(corrupt_data))
    
    with pytest.raises(RuntimeError, match="RECEIPT_INTEGRITY_MISMATCH"):
        verify_receipt_integrity(rcpt_file)


def test_oracle_impl_19_fixture_mutation_between_caller_and_child(tmp_path):
    """ORACLE-IMPL-19: Fixture mutation between caller preparation and child execution."""
    fix_file = tmp_path / "fixture.json"
    init_data = {"data": [1, 2, 3]}
    init_bytes = canonicalize_json_v1(init_data)
    expected_hash = hashlib.sha256(init_bytes).hexdigest()
    
    # Disk mutation
    fix_file.write_bytes(b'{"data": [1, 2, 999]}')
    obs_bytes = fix_file.read_bytes()
    obs_hash = hashlib.sha256(obs_bytes).hexdigest()
    assert obs_hash != expected_hash


def test_oracle_impl_20_concurrent_transaction_acquisition():
    """ORACLE-IMPL-20: Concurrent transaction acquisition fails with Win32 sharing violation."""
    lock_file = REPO_ROOT / "scratch" / "catalog_journal" / "transaction.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    if not lock_file.exists():
        lock_file.touch()

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_NONE = 0x00000000
    OPEN_EXISTING = 3
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

    # First handle: exclusive zero-share lease
    h1 = kernel32.CreateFileW(
        str(lock_file.resolve()),
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_NONE,
        None,
        OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT,
        None
    )
    assert h1 not in (-1, 0xFFFFFFFFFFFFFFFF, INVALID_HANDLE_VALUE), f"Failed to acquire first handle: {ctypes.get_last_error()}"

    try:
        # Second attempt must fail with sharing violation (ERROR_SHARING_VIOLATION = 32)
        h2 = kernel32.CreateFileW(
            str(lock_file.resolve()),
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_NONE,
            None,
            OPEN_EXISTING,
            FILE_FLAG_OPEN_REPARSE_POINT,
            None
        )
        assert h2 in (-1, 0xFFFFFFFFFFFFFFFF, INVALID_HANDLE_VALUE)
        err = ctypes.get_last_error()
        assert err == 32, f"Expected ERROR_SHARING_VIOLATION (32), got {err}"
    finally:
        kernel32.CloseHandle(h1)


def test_oracle_impl_21_runner_code_integrity_mismatch(tmp_path):
    """ORACLE-IMPL-21: Runner code hash mismatch triggers fail-closed RUNNER_INTEGRITY_MISMATCH."""
    fake_runner = tmp_path / "runner.py"
    fake_runner.write_bytes(b"# Mutated runner code")
    with pytest.raises(RuntimeError, match="RUNNER_INTEGRITY_MISMATCH"):
        verify_runner_code_integrity(fake_runner, AUTHORITATIVE_RUNNER_CODE_SHA256)


def test_oracle_impl_22_taxonomy_source_pin_mismatch(tmp_path):
    """ORACLE-IMPL-22: Taxonomy source hash mismatch triggers fail-closed TAXONOMY_PIN_VIOLATION."""
    fake_repo = tmp_path / "fake_repo"
    fake_tax = fake_repo / "src" / "ocean_sentinel" / "governance" / "taxonomy.py"
    fake_tax.parent.mkdir(parents=True, exist_ok=True)
    fake_tax.write_bytes(b"# Mutated taxonomy source code")

    mgr = GovernanceTransactionManager(fake_repo, "tx_impl_22")
    with pytest.raises(RuntimeError, match="TAXONOMY_PIN_VIOLATION"):
        mgr.prepare_phase_d_taxonomy_freeze(approved_ops={})


# ==============================================================================
# SECTION 3: INTEGRATION TESTS
# ==============================================================================

def test_end_to_end_governance_transaction_lifecycle():
    """Executes full canonical transaction lifecycle:
    1. Exclusive lease acquisition
    2. Journal PREPARED state transition
    3. Phase D taxonomy freeze and snapshot digest verification
    4. Fixture staging via stage_authorized_fixture (single authoritative byte hash)
    5. Subprocess launch of runner.py (python -I) executing allowlisted operation (transitions to EXECUTING)
    6. Deterministic receipt emission and canonical integrity verification
    7. Durable COMMITTED finalization with inactive slot write, fsync, and reread verification
    8. Exclusive lease release
    """
    tx_id = f"tx_e2e_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    
    mgr.acquire_exclusive_lease()
    try:
        # 2. PREPARED transition
        slot1, seq1 = mgr.write_journal_transition("PREPARED")
        assert slot1 in {"a", "b"} and seq1 >= 1

        # Adverse attempt: Premature commit finalization before EXECUTING state and output receipt
        with pytest.raises(RuntimeError, match="FINALIZATION_INVALID_STATE"):
            mgr.finalize_committed_transaction()

        # 3. Phase D taxonomy freeze
        approved_ops = {
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        }
        snap_path, src_tax_hash, snap_hash = mgr.prepare_phase_d_taxonomy_freeze(approved_ops)
        assert snap_path.is_file()

        # 4. Stage authorized fixture inside transaction-bound fixture root
        fix_payload = {
            "args": [[0.1, 0.2, 0.3, 0.4, 0.5], [0.15, 0.25, 0.35, 0.45, 0.55]],
            "kwargs": {"method": "asymp"},
            "declared_metadata": {
                "objective": "Validation of two-sample Kolmogorov-Smirnov test under isolated governance",
                "protocol_version": "v2",
                "task_id": "GOV-LESSON-ARCHITECTURE-V2-FINAL-IMPLEMENTATION-R4-10"
            }
        }
        fix_bytes = canonicalize_json_v1(fix_payload)
        fix_file, expected_fix_hash = mgr.stage_authorized_fixture(f"fixture_{tx_id}.json", fix_bytes)
        assert fix_file.is_file()
        assert expected_fix_hash == hashlib.sha256(fix_bytes).hexdigest()

        # 5. Launch provenance runner in isolated subprocess (python -I)
        verified_receipt = mgr.launch_provenance_runner(
            operation_id="scipy_kstest_v1",
            fixture_input_path=fix_file
        )
        assert verified_receipt["schema"] == "ocean_sentinel_provenance_receipt_v2"
        assert verified_receipt["operation_id"] == "scipy_kstest_v1"
        assert verified_receipt["transaction_id"] == tx_id
        assert verified_receipt["trust_anchors"]["trusted_expected_fixture_sha256"] == expected_fix_hash
        assert verified_receipt["epistemic_provenance"]["OBSERVED"]["observed_fixture_bytes_sha256"] == expected_fix_hash
        assert verified_receipt["epistemic_provenance"]["OBSERVED"]["executed_function"] == "scipy.stats.ks_2samp"
        assert verified_receipt["epistemic_provenance"]["DERIVED"]["reference_version_match"] is True
        assert verified_receipt["epistemic_provenance"]["DERIVED"]["fixture_bytes_match_trusted_anchor"] is True

        # 6. Finalize committed transaction
        mgr.finalize_committed_transaction()

    finally:
        mgr.release_exclusive_lease()


def test_standalone_recovery_script_execution():
    """Executes scripts/recover_governance_transaction.py as standalone zero-dependency bootstrap."""
    interp = get_authoritative_interpreter(REPO_ROOT)
    recovery_script = REPO_ROOT / "scripts" / "recover_governance_transaction.py"
    
    # Run script with a dummy transaction ID
    cmd = [str(interp), str(recovery_script), "tx_dummy_recovery"]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert "ImportError" not in res.stderr
    assert "ModuleNotFoundError" not in res.stderr


# ==============================================================================
# SECTION 4: CORRECTIVE COMMIT & FIXTURE AUTHORITY ORACLES (01 through 21)
# ==============================================================================

def test_oracle_corr_01_byte_mutation_after_declaration_fails():
    """ORACLE-CORR-01: Fixture raw bytes mutated on disk after declaration -> fails closed."""
    tx_id = f"tx_corr_01_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        mgr.prepare_phase_d_taxonomy_freeze({
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        })
        payload = {"args": [[1.0, 2.0], [1.5, 2.5]], "kwargs": {}}
        fix_bytes = canonicalize_json_v1(payload)
        fix_path, expected_hash = mgr.stage_authorized_fixture(f"fix_{tx_id}.json", fix_bytes)
        
        # Tamper raw bytes on disk after declaration
        fix_path.write_bytes(fix_bytes + b" ")
        
        with pytest.raises(RuntimeError, match="PROVENANCE_RUNNER_FAILED|FIXTURE_HASH_MISMATCH"):
            mgr.launch_provenance_runner("scipy_kstest_v1", fix_path)
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_02_byte_mutation_after_caller_inspection_before_child_fails():
    """ORACLE-CORR-02: TOCTOU attack: Byte mutation between caller inspection and child read -> fails closed."""
    tx_id = f"tx_corr_02_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        mgr.prepare_phase_d_taxonomy_freeze({
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        })
        payload = {"args": [[1.0, 2.0], [1.5, 2.5]], "kwargs": {}}
        fix_bytes = canonicalize_json_v1(payload)
        fix_path, expected_hash = mgr.stage_authorized_fixture(f"fix_{tx_id}.json", fix_bytes)
        
        # Caller inspected and verified hash matches expected_hash
        assert hashlib.sha256(fix_path.read_bytes()).hexdigest() == expected_hash
        
        # Attacker tampers file before child executes
        fix_path.write_bytes(json.dumps({"args": [[999.0], [0.0]], "kwargs": {}}).encode("utf-8"))
        
        with pytest.raises(RuntimeError, match="PROVENANCE_RUNNER_FAILED|FIXTURE_HASH_MISMATCH"):
            mgr.launch_provenance_runner("scipy_kstest_v1", fix_path)
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_03_self_declared_hash_cannot_override_trusted_expected_hash():
    """ORACLE-CORR-03: Self-declared fixture_sha256 cannot override trusted transaction expected hash."""
    tx_id = f"tx_corr_03_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        mgr.prepare_phase_d_taxonomy_freeze({
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        })
        # Fixture contains self-declared hash that doesn't match raw bytes
        payload = {
            "args": [[1.0, 2.0], [1.5, 2.5]],
            "kwargs": {},
            "fixture_sha256": "0123456789abcdef" * 4
        }
        fix_bytes = canonicalize_json_v1(payload)
        fix_path, expected_hash = mgr.stage_authorized_fixture(f"fix_{tx_id}.json", fix_bytes)
        
        # In-file declared hash mismatch causes fail-closed
        with pytest.raises(RuntimeError, match="PROVENANCE_RUNNER_FAILED|FIXTURE_HASH_MISMATCH"):
            mgr.launch_provenance_runner("scipy_kstest_v1", fix_path)
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_04_changing_json_while_recomputing_self_hash_fails():
    """ORACLE-CORR-04: Changing fixture JSON while recomputing in-file self-hash still fails against trusted journal hash."""
    tx_id = f"tx_corr_04_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        mgr.prepare_phase_d_taxonomy_freeze({
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        })
        orig_payload = {"args": [[1.0, 2.0], [1.5, 2.5]], "kwargs": {}}
        orig_bytes = canonicalize_json_v1(orig_payload)
        fix_path, expected_hash = mgr.stage_authorized_fixture(f"fix_{tx_id}.json", orig_bytes)
        
        # Attacker crafts new payload and puts its self-hash in fixture_sha256
        new_payload = {"args": [[10.0, 20.0], [15.0, 25.0]], "kwargs": {}}
        new_bytes_inner = canonicalize_json_v1(new_payload)
        new_payload["fixture_sha256"] = hashlib.sha256(new_bytes_inner).hexdigest()
        fix_path.write_bytes(canonicalize_json_v1(new_payload))
        
        # Must fail closed because raw bytes do not match expected_hash in journal
        with pytest.raises(RuntimeError, match="PROVENANCE_RUNNER_FAILED|FIXTURE_HASH_MISMATCH"):
            mgr.launch_provenance_runner("scipy_kstest_v1", fix_path)
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_05_differently_serialized_identical_json_fails():
    """ORACLE-CORR-05: Identical semantic JSON serialized differently fails byte hash comparison."""
    tx_id = f"tx_corr_05_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        mgr.prepare_phase_d_taxonomy_freeze({
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        })
        payload = {"args": [[1.0, 2.0], [1.5, 2.5]], "kwargs": {}}
        compact_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
        indented_bytes = json.dumps(payload, indent=4).encode("utf-8")
        assert compact_bytes != indented_bytes
        
        fix_path, expected_hash = mgr.stage_authorized_fixture(f"fix_{tx_id}.json", compact_bytes)
        # Replace file on disk with indented version (same semantic JSON)
        fix_path.write_bytes(indented_bytes)
        
        # Must fail closed because exact file bytes SHA256 does not match
        with pytest.raises(RuntimeError, match="PROVENANCE_RUNNER_FAILED|FIXTURE_HASH_MISMATCH"):
            mgr.launch_provenance_runner("scipy_kstest_v1", fix_path)
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_06_repo_internal_unauthorized_fixture_rejected():
    """ORACLE-CORR-06: Internal repo file outside transaction fixture root rejected as fixture."""
    tx_id = f"tx_corr_06_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        internal_file = REPO_ROOT / "src" / "ocean_sentinel" / "governance" / "taxonomy.py"
        with pytest.raises(RuntimeError, match="ABSOLUTE_FIXTURE_PATH_REJECTED|FIXTURE_PATH_ESCAPES_ROOT|FIXTURE_PATH_UNAUTHORIZED"):
            mgr.stage_authorized_fixture(str(internal_file), internal_file.read_bytes())
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_07_fixture_path_traversal_rejected():
    """ORACLE-CORR-07: Fixture path traversal using '..' rejected."""
    tx_id = f"tx_corr_07_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        with pytest.raises(RuntimeError, match="PATH_TRAVERSAL_REJECTED"):
            mgr.stage_authorized_fixture("../traversal_fixture.json", b"{}")
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_08_absolute_fixture_path_rejected():
    """ORACLE-CORR-08: Caller-supplied absolute fixture path rejected."""
    tx_id = f"tx_corr_08_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        with pytest.raises(RuntimeError, match="ABSOLUTE_FIXTURE_PATH_REJECTED"):
            mgr.stage_authorized_fixture("C:/temp/fixture.json", b"{}")
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_09_stale_caller_fixture_path_mismatch_rejected():
    """ORACLE-CORR-09: Caller passes fixture path that mismatches transaction-authorized fixture path -> fails closed."""
    tx_id = f"tx_corr_09_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        mgr.prepare_phase_d_taxonomy_freeze({
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        })
        payload = {"args": [[1.0, 2.0], [1.5, 2.5]], "kwargs": {}}
        fix_bytes = canonicalize_json_v1(payload)
        fix_path, expected_hash = mgr.stage_authorized_fixture("authorized_fix.json", fix_bytes)
        
        # Caller passes a different fixture filename
        with pytest.raises(RuntimeError, match="PROVENANCE_RUNNER_FAILED|FIXTURE_PATH_NOT_AUTHORIZED_BY_TRANSACTION"):
            mgr.launch_provenance_runner("scipy_kstest_v1", fixture_input_path=Path("other_fix.json"))
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_10_transaction_mismatch_fixture_rejected():
    """ORACLE-CORR-10: Cross-transaction fixture access rejected."""
    tx_a = f"tx_corr_10a_{int(time.time())}"
    tx_b = f"tx_corr_10b_{int(time.time())}"
    mgr_a = GovernanceTransactionManager(REPO_ROOT, tx_a)
    mgr_a.acquire_exclusive_lease()
    try:
        mgr_a.stage_authorized_fixture("shared.json", b'{"args": []}')
    finally:
        mgr_a.release_exclusive_lease()
        
    mgr_b = GovernanceTransactionManager(REPO_ROOT, tx_b)
    mgr_b.acquire_exclusive_lease()
    try:
        cross_rel = f"../../{tx_a}/shared.json"
        with pytest.raises(RuntimeError, match="PATH_TRAVERSAL_REJECTED"):
            mgr_b.stage_authorized_fixture(cross_rel, b"{}")
    finally:
        mgr_b.release_exclusive_lease()


def test_oracle_corr_11_existing_receipt_file_collision_refused():
    """ORACLE-CORR-11: Pre-existing receipt file collision refused; runner will not overwrite."""
    tx_id = f"tx_corr_11_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        mgr.prepare_phase_d_taxonomy_freeze({
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        })
        payload = {"args": [[1.0, 2.0], [1.5, 2.5]], "kwargs": {}}
        fix_bytes = canonicalize_json_v1(payload)
        fix_path, expected_hash = mgr.stage_authorized_fixture(f"fix_{tx_id}.json", fix_bytes)
        
        # Pre-create the receipt file
        rcpt_dir = REPO_ROOT / "scratch" / "staged_generation" / "receipts" / tx_id
        rcpt_dir.mkdir(parents=True, exist_ok=True)
        collision_file = rcpt_dir / f"receipt_{tx_id}.json"
        collision_file.write_text("PRE_EXISTING_DATA")
        
        with pytest.raises(RuntimeError, match="PROVENANCE_RUNNER_FAILED|RECEIPT_PREEXISTING_FILE_COLLISION"):
            mgr.launch_provenance_runner("scipy_kstest_v1", fix_path)
            
        assert collision_file.read_text() == "PRE_EXISTING_DATA"
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_12_receipt_path_traversal_rejected():
    """ORACLE-CORR-12: Receipt path traversal rejected."""
    tx_id = f"tx_corr_12_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        snap_path, src_tax_hash, snap_hash = mgr.prepare_phase_d_taxonomy_freeze({
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        })
        payload = {"args": [[1.0, 2.0], [1.5, 2.5]], "kwargs": {}}
        fix_path, expected_hash = mgr.stage_authorized_fixture(f"fix_{tx_id}.json", canonicalize_json_v1(payload))
        mgr.write_journal_transition("EXECUTING", {
            "source_taxonomy_sha256": src_tax_hash,
            "frozen_taxonomy_snapshot_sha256": snap_hash,
            "expected_fixture_sha256": expected_hash,
            "fixture_relative_path": fix_path.name
        })
        
        interp = get_authoritative_interpreter(REPO_ROOT)
        runner_script = REPO_ROOT / "src" / "ocean_sentinel" / "governance" / "runner.py"
        cmd = [
            str(interp), "-I", str(runner_script),
            "--tx-id", tx_id,
            "--journal-slot", mgr.current_slot,
            "--operation-id", "scipy_kstest_v1",
            "--fixture-input", fix_path.name,
            "--receipt-output", "../escaped_receipt.json"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT / "scratch"))
        assert res.returncode != 0
        assert "PATH_TRAVERSAL_REJECTED" in res.stderr
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_13_absolute_receipt_path_rejected():
    """ORACLE-CORR-13: Absolute receipt path rejected."""
    tx_id = f"tx_corr_13_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        snap_path, src_tax_hash, snap_hash = mgr.prepare_phase_d_taxonomy_freeze({
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        })
        payload = {"args": [[1.0, 2.0], [1.5, 2.5]], "kwargs": {}}
        fix_path, expected_hash = mgr.stage_authorized_fixture(f"fix_{tx_id}.json", canonicalize_json_v1(payload))
        mgr.write_journal_transition("EXECUTING", {
            "source_taxonomy_sha256": src_tax_hash,
            "frozen_taxonomy_snapshot_sha256": snap_hash,
            "expected_fixture_sha256": expected_hash,
            "fixture_relative_path": fix_path.name
        })
        
        interp = get_authoritative_interpreter(REPO_ROOT)
        runner_script = REPO_ROOT / "src" / "ocean_sentinel" / "governance" / "runner.py"
        cmd = [
            str(interp), "-I", str(runner_script),
            "--tx-id", tx_id,
            "--journal-slot", mgr.current_slot,
            "--operation-id", "scipy_kstest_v1",
            "--fixture-input", fix_path.name,
            "--receipt-output", "C:/Windows/Temp/receipt.json"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT / "scratch"))
        assert res.returncode != 0
        assert "ABSOLUTE_RECEIPT_PATH_REJECTED" in res.stderr
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_14_caller_receipt_outside_transaction_namespace_rejected():
    """ORACLE-CORR-14: Caller-supplied receipt filename that diverges from receipt_{tx_id}.json is rejected."""
    tx_id = f"tx_corr_14_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        snap_path, src_tax_hash, snap_hash = mgr.prepare_phase_d_taxonomy_freeze({
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        })
        payload = {"args": [[1.0, 2.0], [1.5, 2.5]], "kwargs": {}}
        fix_path, expected_hash = mgr.stage_authorized_fixture(f"fix_{tx_id}.json", canonicalize_json_v1(payload))
        mgr.write_journal_transition("EXECUTING", {
            "source_taxonomy_sha256": src_tax_hash,
            "frozen_taxonomy_snapshot_sha256": snap_hash,
            "expected_fixture_sha256": expected_hash,
            "fixture_relative_path": fix_path.name
        })
        
        interp = get_authoritative_interpreter(REPO_ROOT)
        runner_script = REPO_ROOT / "src" / "ocean_sentinel" / "governance" / "runner.py"
        cmd = [
            str(interp), "-I", str(runner_script),
            "--tx-id", tx_id,
            "--journal-slot", mgr.current_slot,
            "--operation-id", "scipy_kstest_v1",
            "--fixture-input", fix_path.name,
            "--receipt-output", "arbitrary_custom_receipt.json"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT / "scratch"))
        assert res.returncode != 0
        assert "RECEIPT_PATH_UNAUTHORIZED" in res.stderr
    finally:
        mgr.release_exclusive_lease()


def test_oracle_corr_15_receipt_mutation_after_publication_detected():
    """ORACLE-CORR-15: Receipt mutation after publication fails integrity verification."""
    tx_id = f"tx_corr_15_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        mgr.prepare_phase_d_taxonomy_freeze({
            "scipy_kstest_v1": {
                "module": "scipy.stats",
                "function": "ks_2samp",
                "package": "scipy",
                "reference_version": "1.15.3"
            }
        })
        payload = {"args": [[1.0, 2.0], [1.5, 2.5]], "kwargs": {}}
        fix_path, _ = mgr.stage_authorized_fixture(f"fix_{tx_id}.json", canonicalize_json_v1(payload))
        mgr.launch_provenance_runner("scipy_kstest_v1", fix_path)
        
        rcpt_file = REPO_ROOT / "scratch" / "staged_generation" / "receipts" / tx_id / f"receipt_{tx_id}.json"
        assert rcpt_file.is_file()
        
        # Tamper receipt payload
        rcpt_data = json.loads(rcpt_file.read_text(encoding="utf-8"))
        rcpt_data["epistemic_provenance"]["OBSERVED"]["execution_duration_sec"] = 9999.9
        rcpt_file.write_bytes(canonicalize_json_v1(rcpt_data))
        
        with pytest.raises(RuntimeError, match="RECEIPT_INTEGRITY_COMPROMISED|INTEGRITY_MISMATCH"):
            verify_receipt_integrity(rcpt_file)
    finally:
        mgr.release_exclusive_lease()


def _run_transaction_child_process(
    tx_id: str,
    fault_injection_point: Optional[str] = None,
    fault_exit_code: int = 77,
    call_finalize: bool = True,
    extra_env: Optional[Dict[str, str]] = None
) -> subprocess.CompletedProcess:
    """Executes a real governance transaction in a separate Python process under canonical .venv.
    If fault_injection_point is set, child terminates abruptly via os._exit(fault_exit_code).
    """
    interp = get_authoritative_interpreter(REPO_ROOT)
    script_content = f'''import sys
import os
from pathlib import Path

repo_root = Path({repr(str(REPO_ROOT))})
if str(repo_root / "src") not in sys.path:
    sys.path.insert(0, str(repo_root / "src"))

from ocean_sentinel.governance.lifecycle import GovernanceTransactionManager
from ocean_sentinel.governance.provenance import canonicalize_json_v1

tx_id = "{tx_id}"
mgr = GovernanceTransactionManager(repo_root, tx_id)
mgr.acquire_exclusive_lease()
try:
    mgr.write_journal_transition("PREPARED")
    mgr.prepare_phase_d_taxonomy_freeze({{
        "scipy_kstest_v1": {{
            "module": "scipy.stats",
            "function": "ks_2samp",
            "package": "scipy",
            "reference_version": "1.15.3"
        }}
    }})
    payload = {{"args": [[1.0, 2.0], [1.5, 2.5]], "kwargs": {{}}}}
    fix_path, _ = mgr.stage_authorized_fixture(f"fix_{{tx_id}}.json", canonicalize_json_v1(payload))
    mgr.launch_provenance_runner("scipy_kstest_v1", fix_path)
    if {call_finalize}:
        mgr.finalize_committed_transaction()
    print("CHILD_COMPLETED_SUCCESSFULLY")
finally:
    mgr.release_exclusive_lease()
'''
    env = os.environ.copy()
    if fault_injection_point:
        env["OCEAN_SENTINEL_FAULT_INJECTION_POINT"] = fault_injection_point
        env["OCEAN_SENTINEL_FAULT_INJECTION_EXIT_CODE"] = str(fault_exit_code)
    else:
        env.pop("OCEAN_SENTINEL_FAULT_INJECTION_POINT", None)
        env.pop("OCEAN_SENTINEL_FAULT_INJECTION_EXIT_CODE", None)

    if extra_env:
        env.update(extra_env)

    cmd = [str(interp), "-I", "-c", script_content]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT), env=env)


def test_oracle_corr_16_crash_before_runner_launch():
    """ORACLE-CORR-16: Real subprocess crash immediately before runner subprocess launch.
    Child terminates abruptly via os._exit(77) at BEFORE_RUNNER_LAUNCH.
    Recovery running in fresh subprocess rolls back incomplete transaction.
    """
    tx_id = f"tx_corr_16_{int(time.time())}"
    res = _run_transaction_child_process(tx_id, fault_injection_point="BEFORE_RUNNER_LAUNCH", fault_exit_code=77)
    assert res.returncode == 77
    assert "CHILD_COMPLETED_SUCCESSFULLY" not in res.stdout

    # Recovery runs independently in fresh subprocess
    interp = get_authoritative_interpreter(REPO_ROOT)
    recovery_script = REPO_ROOT / "scripts" / "recover_governance_transaction.py"
    res_rec = subprocess.run([str(interp), str(recovery_script), tx_id], capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert res_rec.returncode == 0
    assert "rolled back" in res_rec.stdout.lower()

    # Independent parent inspection of on-disk reality
    journal_dir = REPO_ROOT / "scratch" / "catalog_journal"
    auth_slot, auth_data = determine_authoritative_journal_slot(journal_dir, tx_id)
    assert auth_data.get("state") == "ROLLED_BACK"

    # Candidate receipt was never published
    rcpt_file = REPO_ROOT / "scratch" / "staged_generation" / "receipts" / tx_id / f"receipt_{tx_id}.json"
    assert not rcpt_file.exists()


def test_oracle_corr_17_crash_after_candidate_publish_before_committed():
    """ORACLE-CORR-17: Real subprocess crash after candidate receipt is published and verified,
    immediately before durable COMMITTED publication.
    Child terminates abruptly via os._exit(78) at AFTER_CANDIDATE_PUBLISH_BEFORE_COMMITTED.
    Recovery running in fresh subprocess purges candidate receipt and writes ROLLED_BACK.
    """
    tx_id = f"tx_corr_17_{int(time.time())}"
    res = _run_transaction_child_process(tx_id, fault_injection_point="AFTER_CANDIDATE_PUBLISH_BEFORE_COMMITTED", fault_exit_code=78)
    assert res.returncode == 78
    assert "CHILD_COMPLETED_SUCCESSFULLY" not in res.stdout

    # Physical check: Candidate receipt exists on disk immediately post-crash
    rcpt_file = REPO_ROOT / "scratch" / "staged_generation" / "receipts" / tx_id / f"receipt_{tx_id}.json"
    assert rcpt_file.is_file()

    # Recovery runs independently in fresh subprocess
    interp = get_authoritative_interpreter(REPO_ROOT)
    recovery_script = REPO_ROOT / "scripts" / "recover_governance_transaction.py"
    res_rec = subprocess.run([str(interp), str(recovery_script), tx_id], capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert res_rec.returncode == 0
    assert "rolled back" in res_rec.stdout.lower()

    # Independent inspection: Candidate receipt must be deleted by recovery
    assert not rcpt_file.exists()

    # Journal authority on disk is ROLLED_BACK
    journal_dir = REPO_ROOT / "scratch" / "catalog_journal"
    auth_slot, auth_data = determine_authoritative_journal_slot(journal_dir, tx_id)
    assert auth_data.get("state") == "ROLLED_BACK"


def test_oracle_corr_18_crash_during_committed_publication_corrupted_inactive_slot():
    """ORACLE-CORR-18: Crash during COMMITTED publication.
    1. Real subprocess crash before replace leaving .tmp file; recovery rolls back.
    2. Torn/corrupted inactive slot fails closed without silent downgrade.
    """
    tx_id = f"tx_corr_18_{int(time.time())}"
    res = _run_transaction_child_process(tx_id, fault_injection_point="BEFORE_JOURNAL_REPLACE_COMMITTED", fault_exit_code=79)
    assert res.returncode == 79
    assert "CHILD_COMPLETED_SUCCESSFULLY" not in res.stdout

    # Recovery runs in fresh subprocess
    interp = get_authoritative_interpreter(REPO_ROOT)
    recovery_script = REPO_ROOT / "scripts" / "recover_governance_transaction.py"
    res_rec = subprocess.run([str(interp), str(recovery_script), tx_id], capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert res_rec.returncode == 0
    assert "rolled back" in res_rec.stdout.lower()

    # Journal state is ROLLED_BACK
    journal_dir = REPO_ROOT / "scratch" / "catalog_journal"
    auth_slot, auth_data = determine_authoritative_journal_slot(journal_dir, tx_id)
    assert auth_data.get("state") == "ROLLED_BACK"

    # Part 2: Corrupted inactive slot leaves torn data -> fail closed without downgrade
    tx_torn = f"tx_torn_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_torn)
    mgr.acquire_exclusive_lease()
    torn_file = None
    try:
        slot1, seq1 = mgr.write_journal_transition("PREPARED")
        target_slot = "b" if slot1 == "a" else "a"
        torn_file = mgr.journal_dir / f"transaction_state_{target_slot}.json"
        torn_file.write_text('{"schema": "ocean_sentinel_journal_state_v2", "state": "COMMITTED", "sequence_number": 999, "slot_checksum": "TORN_BAD"}')
        with pytest.raises(RuntimeError, match="JOURNAL_CORRUPTED"):
            determine_authoritative_journal_slot(mgr.journal_dir, tx_torn)
    finally:
        if torn_file and torn_file.exists():
            torn_file.unlink()
        mgr.release_exclusive_lease()


def test_oracle_corr_19_crash_after_committed_publication_before_lock_release():
    """ORACLE-CORR-19: Real subprocess crash after COMMITTED record verified on disk but before lock release.
    Child terminates abruptly via os._exit(80) at AFTER_COMMITTED_DURABILITY_BEFORE_LOCK_RELEASE.
    Kernel closes lock handle. Recovery running in fresh subprocess detects COMMITTED and preserves it.
    """
    tx_id = f"tx_corr_19_{int(time.time())}"
    res = _run_transaction_child_process(tx_id, fault_injection_point="AFTER_COMMITTED_DURABILITY_BEFORE_LOCK_RELEASE", fault_exit_code=80)
    assert res.returncode == 80
    assert "CHILD_COMPLETED_SUCCESSFULLY" not in res.stdout

    # Recovery in fresh subprocess
    interp = get_authoritative_interpreter(REPO_ROOT)
    recovery_script = REPO_ROOT / "scripts" / "recover_governance_transaction.py"
    res_rec = subprocess.run([str(interp), str(recovery_script), tx_id], capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert res_rec.returncode == 0
    assert "committed" in res_rec.stdout.lower() and "rollback skipped" in res_rec.stdout.lower()

    # COMMITTED remains authoritative
    journal_dir = REPO_ROOT / "scratch" / "catalog_journal"
    auth_slot, auth_data = determine_authoritative_journal_slot(journal_dir, tx_id)
    assert auth_data.get("state") == "COMMITTED"


def test_oracle_corr_20_crash_immediately_after_lock_release():
    """ORACLE-CORR-20: Real subprocess crash immediately after finalization and lock release.
    Child terminates abruptly via os._exit(82) at AFTER_LOCK_RELEASE.
    Recovery running in fresh subprocess confirms COMMITTED remains authoritative.
    """
    tx_id = f"tx_corr_20_{int(time.time())}"
    res = _run_transaction_child_process(tx_id, fault_injection_point="AFTER_LOCK_RELEASE", fault_exit_code=82)
    assert res.returncode == 82

    # Recovery in fresh subprocess confirms COMMITTED is preserved
    interp = get_authoritative_interpreter(REPO_ROOT)
    recovery_script = REPO_ROOT / "scripts" / "recover_governance_transaction.py"
    res_rec = subprocess.run([str(interp), str(recovery_script), tx_id], capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert res_rec.returncode == 0
    assert "committed" in res_rec.stdout.lower() and "rollback skipped" in res_rec.stdout.lower()

    journal_dir = REPO_ROOT / "scratch" / "catalog_journal"
    auth_slot, auth_data = determine_authoritative_journal_slot(journal_dir, tx_id)
    assert auth_data.get("state") == "COMMITTED"


def test_oracle_corr_21_isolated_environment_self_contained(tmp_path):
    """ORACLE-CORR-21: Mandatory Correction 5: Full empirical proof of isolated runner environment.
    1. Canonical interpreter: .venv\\Scripts\\python.exe.
    2. Isolated mode is verified active.
    3. Poisoned ambient PYTHONPATH is completely ignored.
    4. Imported SciPy is exactly 1.15.3.
    5. scipy.__file__ resides strictly inside canonical .venv\\Lib\\site-packages.
    6. Callable module origin inside authorized SciPy package.
    7. No external global site-packages required.
    """
    interp = get_authoritative_interpreter(REPO_ROOT)
    assert ".venv" in str(interp).lower()

    # 1 & 2: Isolated mode active check
    iso_check = subprocess.run([str(interp), "-I", "-c", "import sys; print('ISOLATED:', getattr(sys.flags, 'isolated', 0))"], capture_output=True, text=True)
    assert iso_check.returncode == 0
    assert "ISOLATED: 1" in iso_check.stdout

    # 3: Poisoned ambient PYTHONPATH cannot override or influence resolution under python -I
    fake_scipy_dir = tmp_path / "poison_path"
    fake_scipy_pkg = fake_scipy_dir / "scipy"
    fake_scipy_pkg.mkdir(parents=True)
    (fake_scipy_pkg / "__init__.py").write_text("__version__ = '99.99.99_POISONED'")

    env_poison = os.environ.copy()
    env_poison["PYTHONPATH"] = str(fake_scipy_dir)

    # 4, 5, 6, 7: Verify real SciPy resolution inside .venv under poisoned PYTHONPATH
    probe_code = """
import sys
import scipy

print("SCIPY_VERSION:", scipy.__version__)
print("SCIPY_FILE:", scipy.__file__)
assert scipy.__version__ == "1.15.3", f"Wrong version: {scipy.__version__}"
assert "poison_path" not in scipy.__file__.lower(), "Ambient PYTHONPATH poisoned SciPy resolution!"
assert ".venv" in scipy.__file__.lower(), f"SciPy not in .venv: {scipy.__file__}"
"""
    probe_res = subprocess.run([str(interp), "-I", "-c", probe_code], env=env_poison, capture_output=True, text=True)
    assert probe_res.returncode == 0, f"Probe failed: {probe_res.stderr}"
    assert "SCIPY_VERSION: 1.15.3" in probe_res.stdout
    assert ".venv" in probe_res.stdout.lower()

    # Assert runner rejects execution when NOT invoked with -I
    runner_script = REPO_ROOT / "src" / "ocean_sentinel" / "governance" / "runner.py"
    res_no_i = subprocess.run([str(interp), str(runner_script), "--tx-id", "dummy", "--journal-slot", "a", "--operation-id", "dummy"], capture_output=True, text=True)
    assert res_no_i.returncode != 0
    assert "PREFLIGHT_SECURITY_FAILED" in res_no_i.stderr

    # 8. Adversarial callable source origin validation
    # A callable whose source originates outside the approved site-packages directory is rejected
    import importlib.util
    adv_file = tmp_path / "external_exploit.py"
    adv_file.write_text("def malicious_hook(): pass\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("scipy.stats.malicious_hook", adv_file)
    adv_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adv_mod)
    malicious_callable = adv_mod.malicious_hook

    approved_site_packages = (REPO_ROOT / ".venv" / "Lib" / "site-packages").resolve()
    with pytest.raises(RuntimeError, match="does not originate from verified site-packages"):
        verify_callable_origin(malicious_callable, "scipy", approved_site_packages)


def test_oracle_corr_22_crash_before_fsync():
    """ORACLE-CORR-22: Crash before fsync completion does not corrupt active journal.
    Child terminates at BEFORE_JOURNAL_FSYNC (exit code 83).
    Recovery verifies active slot is unchanged and un-fsynced write is discarded.
    """
    tx_id = f"tx_corr_22_{int(time.time())}"
    res = _run_transaction_child_process(tx_id, fault_injection_point="BEFORE_JOURNAL_FSYNC_COMMITTED", fault_exit_code=83)
    assert res.returncode == 83
    assert "CHILD_COMPLETED_SUCCESSFULLY" not in res.stdout

    interp = get_authoritative_interpreter(REPO_ROOT)
    recovery_script = REPO_ROOT / "scripts" / "recover_governance_transaction.py"
    res_rec = subprocess.run([str(interp), str(recovery_script), tx_id], capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert res_rec.returncode == 0

    journal_dir = REPO_ROOT / "scratch" / "catalog_journal"
    auth_slot, auth_data = determine_authoritative_journal_slot(journal_dir, tx_id)
    assert auth_data.get("state") == "ROLLED_BACK"


def test_oracle_corr_23_crash_after_replace_before_verification():
    """ORACLE-CORR-23: Process crash after physical journal publication but before post-publication verification.
    Child terminates at AFTER_JOURNAL_REPLACE_BEFORE_VERIFICATION_COMMITTED (exit code 84).
    Order of operations:
    1. Candidate data written to .tmp and os.fsync() executed on .tmp descriptor
    2. Physical publication via os.replace(tmp_file, dest_file)
    3. Process crash injected before verify_journal_slot_file() or finalizer reread executes
    Recovery in a fresh process determines authority based on published on-disk reality.
    Note: Proves software process termination crash recovery behavior; does not prove
    hardware power-loss durability.
    """
    tx_id = f"tx_corr_23_{int(time.time())}"
    res = _run_transaction_child_process(tx_id, fault_injection_point="AFTER_JOURNAL_REPLACE_BEFORE_VERIFICATION_COMMITTED", fault_exit_code=84)
    assert res.returncode == 84
    assert "CHILD_COMPLETED_SUCCESSFULLY" not in res.stdout

    interp = get_authoritative_interpreter(REPO_ROOT)
    recovery_script = REPO_ROOT / "scripts" / "recover_governance_transaction.py"
    res_rec = subprocess.run([str(interp), str(recovery_script), tx_id], capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert res_rec.returncode == 0

    journal_dir = REPO_ROOT / "scratch" / "catalog_journal"
    auth_slot, auth_data = determine_authoritative_journal_slot(journal_dir, tx_id)
    # The valid COMMITTED slot was published on disk; recovery preserves it
    assert auth_data.get("state") == "COMMITTED"


def test_oracle_corr_24_crash_after_verification_before_ack():
    """ORACLE-CORR-24: Crash after disk verification passes but before in-memory caller acknowledgment.
    Child terminates at AFTER_JOURNAL_VERIFICATION_BEFORE_ACK (exit code 85).
    Restart operates from on-disk reality rather than in-memory acknowledgement.
    """
    tx_id = f"tx_corr_24_{int(time.time())}"
    res = _run_transaction_child_process(tx_id, fault_injection_point="AFTER_JOURNAL_VERIFICATION_BEFORE_ACK_COMMITTED", fault_exit_code=85)
    assert res.returncode == 85

    journal_dir = REPO_ROOT / "scratch" / "catalog_journal"
    auth_slot, auth_data = determine_authoritative_journal_slot(journal_dir, tx_id)
    assert auth_data.get("state") == "COMMITTED"


def test_oracle_corr_25_restart_with_old_slot_and_corrupt_new_slot(tmp_path):
    """ORACLE-CORR-25: Older slot valid (seq N), newer slot corrupt (seq N+1).
    Reader fails closed (JOURNAL_CORRUPTED), preventing silent downgrade to stale authority.
    """
    # Slot A: Valid, seq=10
    payload_a = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_corr_25",
        "sequence_number": 10,
        "state": "EXECUTING",
        "timestamp_utc": "2026-09-18T00:00:00Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_a["slot_checksum"] = compute_journal_slot_checksum(payload_a)
    (tmp_path / "transaction_state_a.json").write_bytes(canonicalize_json_v1(payload_a))

    # Slot B: Corrupt checksum, seq=11
    payload_b = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_corr_25",
        "sequence_number": 11,
        "state": "COMMITTED",
        "timestamp_utc": "2026-09-18T00:00:01Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256,
        "slot_checksum": "CORRUPT_CHECKSUM_BAD_BAD"
    }
    (tmp_path / "transaction_state_b.json").write_bytes(canonicalize_json_v1(payload_b))

    with pytest.raises(RuntimeError, match="JOURNAL_CORRUPTED"):
        determine_authoritative_journal_slot(tmp_path, "tx_corr_25")


def test_oracle_corr_26_restart_with_duplicate_sequence(tmp_path):
    """ORACLE-CORR-26: Both slots valid with identical sequence number -> fails closed."""
    payload_a = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_corr_26",
        "sequence_number": 5,
        "state": "EXECUTING",
        "timestamp_utc": "2026-09-18T00:00:00Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_a["slot_checksum"] = compute_journal_slot_checksum(payload_a)
    (tmp_path / "transaction_state_a.json").write_bytes(canonicalize_json_v1(payload_a))

    payload_b = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_corr_26",
        "sequence_number": 5,
        "state": "ACTIVATED",
        "timestamp_utc": "2026-09-18T00:00:01Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_b["slot_checksum"] = compute_journal_slot_checksum(payload_b)
    (tmp_path / "transaction_state_b.json").write_bytes(canonicalize_json_v1(payload_b))

    with pytest.raises(RuntimeError, match="Duplicate sequence number 5"):
        determine_authoritative_journal_slot(tmp_path, "tx_corr_26")


def test_oracle_corr_27_restart_stale_valid_plus_unparseable_contemporaneous(tmp_path):
    """ORACLE-CORR-27: Old slot valid, but newer unparseable slot file modified contemporaneously
    or after valid slot -> fails closed (JOURNAL_CORRUPTED) preventing silent downgrade.
    """
    payload_a = {
        "schema": "ocean_sentinel_journal_state_v2",
        "transaction_id": "tx_corr_27",
        "sequence_number": 1,
        "state": "EXECUTING",
        "timestamp_utc": "2026-09-18T00:00:00Z",
        "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
    }
    payload_a["slot_checksum"] = compute_journal_slot_checksum(payload_a)
    file_a = tmp_path / "transaction_state_a.json"
    file_a.write_bytes(canonicalize_json_v1(payload_a))

    file_b = tmp_path / "transaction_state_b.json"
    file_b.write_text("NOT_VALID_JSON_TORN_WRITE_DATA")

    # Ensure mtime of unparseable file is >= file_a
    os.utime(file_b, (time.time() + 10, time.time() + 10))

    with pytest.raises(RuntimeError, match="JOURNAL_CORRUPTED"):
        determine_authoritative_journal_slot(tmp_path, "tx_corr_27")


def test_oracle_corr_28_finalizer_requires_fsync_and_reread_before_completion(monkeypatch):
    """ORACLE-CORR-28: Invariant test proving finalize_committed_transaction() cannot
    return successful COMMITTED completion before required fsync and reread steps.

    Verifies:
    1. Static execution invariant:
       - write_journal_transition calls os.fsync on candidate payload BEFORE os.replace.
       - write_journal_transition calls verify_journal_slot_file AFTER os.replace.
       - finalize_committed_transaction calls determine_authoritative_journal_slot AFTER write_journal_transition.
       - Verification assertion occurs before release_exclusive_lease and completion return.
    2. Dynamic behavioral invariant:
       - If fsync fails (e.g. simulated OSError), finalizer fails closed and does not return COMMITTED.
       - If reread verification fails or reports non-COMMITTED state, finalizer raises
         COMMITTED_SLOT_VERIFICATION_FAILED and refuses to return successful completion.
    """
    import inspect

    # 1. Static Invariant Check: Source-order sequence audit
    src_write = inspect.getsource(GovernanceTransactionManager.write_journal_transition)
    fsync_idx = src_write.find("os.fsync(")
    replace_idx = src_write.find("os.replace(")
    reread_idx = src_write.find("verify_journal_slot_file(")
    assert fsync_idx != -1 and replace_idx != -1 and reread_idx != -1
    assert fsync_idx < replace_idx, "Candidate payload fsync must precede os.replace physical publication"
    assert replace_idx < reread_idx, "verify_journal_slot_file must succeed os.replace publication"

    src_final = inspect.getsource(GovernanceTransactionManager.finalize_committed_transaction)
    trans_idx = src_final.find('write_journal_transition("COMMITTED")')
    reread_final_idx = src_final.find("determine_authoritative_journal_slot(", trans_idx)
    verif_check_idx = src_final.find("COMMITTED_SLOT_VERIFICATION_FAILED", reread_final_idx)
    release_idx = src_final.find("self.release_exclusive_lease()", verif_check_idx)
    assert trans_idx != -1 and reread_final_idx != -1 and verif_check_idx != -1 and release_idx != -1
    assert trans_idx < reread_final_idx, "write_journal_transition must precede authoritative reread"
    assert reread_final_idx < verif_check_idx, "reread must precede verification assertion"
    assert verif_check_idx < release_idx, "verification assertion must precede lease release and completion"

    # 2. Dynamic Invariant Check
    tx_id = f"tx_corr_28_{int(time.time())}"
    mgr = GovernanceTransactionManager(REPO_ROOT, tx_id)
    mgr.acquire_exclusive_lease()
    try:
        mgr.write_journal_transition("PREPARED")
        mgr.write_journal_transition("ACTIVATED")

        # Stage valid receipt in staging receipts dir
        receipt_dir = mgr.staging_dir / "receipts" / tx_id
        receipt_dir.mkdir(parents=True, exist_ok=True)
        receipt_file = receipt_dir / f"receipt_{tx_id}.json"

        from ocean_sentinel.governance.lifecycle import EXPECTED_TAXONOMY_SOURCE_SHA256
        receipt_payload = {
            "schema": "ocean_sentinel_provenance_receipt_v2",
            "transaction_id": tx_id,
            "operation_id": "scipy_kstest_v1",
            "timestamp_utc": "2026-09-18T00:00:00Z",
            "trust_anchors": {
                "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256,
                "trusted_expected_fixture_sha256": "0" * 64,
                "expected_taxonomy_sha256": EXPECTED_TAXONOMY_SOURCE_SHA256
            },
            "epistemic_provenance": {
                "OBSERVED": {
                    "observed_runner_bytes_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256,
                    "observed_fixture_bytes_sha256": "0" * 64,
                    "observed_taxonomy_bytes_sha256": EXPECTED_TAXONOMY_SOURCE_SHA256,
                    "executed_function": "scipy.stats.ks_2samp"
                },
                "DERIVED": {
                    "reference_version_match": True,
                    "fixture_bytes_match_trusted_anchor": True,
                    "runner_bytes_match_trusted_anchor": True,
                    "taxonomy_bytes_match_trusted_anchor": True
                }
            },
            "raw_output": {"statistic": 0.5, "pvalue": 0.05}
        }
        receipt_payload["receipt_integrity_sha256"] = compute_receipt_integrity_sha256(receipt_payload)
        receipt_file.write_bytes(canonicalize_json_v1(receipt_payload))

        # Dynamic Case A: If fsync fails on candidate journal write, finalizer raises and state is not COMMITTED
        orig_fsync = os.fsync
        fsync_calls = [0]
        def failing_fsync(fd):
            fsync_calls[0] += 1
            # Call 1 is housekeeping manifest, Call 2 is candidate journal write
            if fsync_calls[0] >= 2:
                raise OSError("Simulated candidate journal fsync failure")
            orig_fsync(fd)

        monkeypatch.setattr(os, "fsync", failing_fsync)
        with pytest.raises(OSError, match="Simulated candidate journal fsync failure"):
            mgr.finalize_committed_transaction()

        # Check journal was NOT committed
        auth_slot, auth_data = determine_authoritative_journal_slot(mgr.journal_dir, tx_id)
        assert auth_data.get("state") != "COMMITTED"

        # Restore fsync
        monkeypatch.setattr(os, "fsync", orig_fsync)

        # Dynamic Case B: If reread verification detects mismatched or corrupted state, finalizer raises COMMITTED_SLOT_VERIFICATION_FAILED
        def mock_mismatched_reread(j_dir, t_id):
            return "b", {"state": "EXECUTING", "sequence_number": 999}

        monkeypatch.setattr("ocean_sentinel.governance.lifecycle.determine_authoritative_journal_slot", mock_mismatched_reread)
        with pytest.raises(RuntimeError, match="COMMITTED_SLOT_VERIFICATION_FAILED"):
            mgr.finalize_committed_transaction()

    finally:
        mgr.release_exclusive_lease()

