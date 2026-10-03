"""Standalone Zero-Dependency Governance Recovery and Rollback Bootstrap.
Executes purely using Python standard library and Win32/NT APIs.
Zero dependency on ocean_sentinel.governance or taxonomy.py (resolves F-R4-01 paradox).
Enforces handle-bound Set-2 deletion (F-R4-02), parent-handle continuity (F-R4-20),
reparse-safe traversal (F-R4-12), and zero-share lock arbitration (F-R4-03).
"""

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# NT / Win32 Constants
FILE_READ_DATA = 0x0001
FILE_WRITE_DATA = 0x0002
FILE_READ_ATTRIBUTES = 0x0080
FILE_WRITE_ATTRIBUTES = 0x0100
DELETE = 0x00010000
SYNCHRONIZE = 0x00100000

FILE_SHARE_NONE = 0x00000000
FILE_SHARE_READ = 0x00000001

FILE_OPEN = 0x00000001
FILE_OPEN_IF = 0x00000003

FILE_DIRECTORY_FILE = 0x00000001
FILE_NON_DIRECTORY_FILE = 0x00000040
FILE_OPEN_REPARSE_POINT = 0x00200000
FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020

OBJ_CASE_INSENSITIVE = 0x00000040

STATUS_SUCCESS = 0x00000000
STATUS_SHARING_VIOLATION = 0xC0000043

FileDispositionInfo = 4
FileIdInfo = 18

ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.USHORT),
        ("MaximumLength", wintypes.USHORT),
        ("Buffer", wintypes.LPWSTR),
    ]


class OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.ULONG),
        ("RootDirectory", wintypes.HANDLE),
        ("ObjectName", ctypes.POINTER(UNICODE_STRING)),
        ("Attributes", wintypes.ULONG),
        ("SecurityDescriptor", wintypes.LPVOID),
        ("SecurityQualityOfService", wintypes.LPVOID),
    ]


class IO_STATUS_BLOCK(ctypes.Structure):
    _fields_ = [
        ("Status", wintypes.ULONG),
        ("Information", ctypes.c_size_t),
    ]


class FILE_DISPOSITION_INFO(ctypes.Structure):
    _fields_ = [
        ("DeleteFile", wintypes.BOOLEAN),
    ]


class FILE_ID_128(ctypes.Structure):
    _fields_ = [
        ("Identifier", ctypes.c_ubyte * 16),
    ]


class FILE_ID_INFO(ctypes.Structure):
    _fields_ = [
        ("VolumeSerialNumber", wintypes.ULARGE_INTEGER),
        ("FileId", FILE_ID_128),
    ]


def canonicalize_json_v1(data: Dict[str, Any]) -> bytes:
    """Shared canonicalization profile: OCEAN_SENTINEL_CANONICAL_JSON_V1."""
    return json.dumps(
        data,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=True
    ).encode("utf-8")


def compute_journal_slot_checksum(slot_data: Dict[str, Any]) -> str:
    """Computes SHA256 checksum over all journal slot fields strictly excluding slot_checksum."""
    canonical_dict = {k: v for k, v in slot_data.items() if k != "slot_checksum"}
    canonical_bytes = canonicalize_json_v1(canonical_dict)
    return hashlib.sha256(canonical_bytes).hexdigest()


def is_contained_in_directory(child_path: Path, parent_dir: Path) -> bool:
    """True directory-containment check rejecting sibling-prefix attacks."""
    try:
        resolved_child = child_path.resolve()
        resolved_parent = parent_dir.resolve()
        if os.name == "nt":
            norm_child = Path(os.path.normcase(str(resolved_child)))
            norm_parent = Path(os.path.normcase(str(resolved_parent)))
        else:
            norm_child = resolved_child
            norm_parent = resolved_parent
        norm_child.relative_to(norm_parent)
        return True
    except (ValueError, RuntimeError):
        return False


def verify_journal_slot_file(slot_file: Path) -> Tuple[str, Optional[int], Optional[Dict[str, Any]]]:
    """Inspects and validates integrity of a journal slot file."""
    if not slot_file.is_file():
        return "ABSENT", None, None
    try:
        raw_bytes = slot_file.read_bytes()
        data = json.loads(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        seq_guess = None
        try:
            m = re.search(r'"sequence_number"\s*:\s*(\d+)', raw_bytes.decode("utf-8", errors="ignore"))
            if m:
                seq_guess = int(m.group(1))
        except Exception:
            pass
        return "UNPARSEABLE", seq_guess, None

    if not isinstance(data, dict):
        return "UNPARSEABLE", None, None

    seq = data.get("sequence_number")
    if not isinstance(seq, int):
        return "UNPARSEABLE", None, None

    stored_checksum = data.get("slot_checksum")
    if not stored_checksum or not isinstance(stored_checksum, str):
        return "CHECKSUM_MISMATCH", seq, data

    computed_checksum = compute_journal_slot_checksum(data)
    if stored_checksum != computed_checksum:
        return "CHECKSUM_MISMATCH", seq, data

    return "VALID", seq, data


def determine_authoritative_journal_slot(journal_dir: Path, tx_id: str) -> Tuple[str, Dict[str, Any]]:
    """Identifies the authoritative active journal slot with pre-arbitration verification and downgrade prevention."""
    slots_info: Dict[str, Dict[str, Any]] = {}
    
    for slot_name in ("a", "b"):
        slot_file = (journal_dir / f"transaction_state_{slot_name}.json").resolve()
        if not is_contained_in_directory(slot_file, journal_dir):
            continue
            
        status, seq, data = verify_journal_slot_file(slot_file)
        mtime = slot_file.stat().st_mtime if slot_file.is_file() else 0.0
        slots_info[slot_name] = {
            "file": slot_file,
            "status": status,
            "seq": seq,
            "data": data,
            "mtime": mtime
        }
        
    valid_slots = []
    corrupt_slots = []
    
    for slot_name, info in slots_info.items():
        if info["status"] == "VALID":
            data = info["data"]
            if data.get("transaction_id") == tx_id:
                valid_slots.append((slot_name, info["seq"], data, info["mtime"]))
        elif info["status"] in {"CHECKSUM_MISMATCH", "UNPARSEABLE"}:
            corrupt_slots.append((slot_name, info["status"], info["seq"], info["data"], info["mtime"]))

    if not valid_slots:
        if corrupt_slots:
            raise RuntimeError(f"ALL_JOURNAL_SLOTS_CORRUPT: Corrupted journal slot(s) detected for tx_id '{tx_id}'.")
        raise RuntimeError(f"NO_ACTIVE_JOURNAL_SLOT: No valid journal slot found for tx_id '{tx_id}'.")

    if len(valid_slots) == 1 and corrupt_slots:
        valid_name, valid_seq, valid_data, valid_mtime = valid_slots[0]
        for c_name, c_status, c_seq, c_data, c_mtime in corrupt_slots:
            if c_seq is not None and c_seq >= valid_seq:
                raise RuntimeError(
                    f"JOURNAL_CORRUPTED: Newer journal slot '{c_name}' (seq={c_seq}) is corrupt while older slot "
                    f"'{valid_name}' (seq={valid_seq}) is valid. Silent downgrade barred."
                )
            if c_seq is None and c_mtime >= valid_mtime:
                raise RuntimeError(
                    f"JOURNAL_CORRUPTED: Corrupted unparseable slot '{c_name}' appears newer or contemporaneous with "
                    f"'{valid_name}'. Silent downgrade barred."
                )
        return valid_name, valid_data

    if len(valid_slots) == 1:
        return valid_slots[0][0], valid_slots[0][2]

    slot_a, slot_b = valid_slots[0], valid_slots[1]
    if slot_a[1] > slot_b[1]:
        return slot_a[0], slot_a[2]
    elif slot_b[1] > slot_a[1]:
        return slot_b[0], slot_b[2]
    else:
        raise RuntimeError(f"JOURNAL_CORRUPTED: Duplicate sequence number {slot_a[1]} in slots A and B for tx_id '{tx_id}'.")


def acquire_recovery_lock(repo_root: Path) -> wintypes.HANDLE:
    """Acquires exclusive zero-share lock handle on transaction.lock sentinel."""
    journal_dir = (repo_root / "scratch" / "catalog_journal").resolve()
    lock_path = journal_dir / "transaction.lock"
    
    # Persistent sentinel: create if absent
    if not lock_path.is_file():
        journal_dir.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "a") as f:
            pass

    # Use kernel32.CreateFileW with dwShareMode=0
    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    OPEN_EXISTING = 3
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000

    h = kernel32.CreateFileW(
        str(lock_path),
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_NONE,  # Zero-share
        None,
        OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT,
        None
    )

    if h == INVALID_HANDLE_VALUE:
        err = ctypes.get_last_error()
        raise RuntimeError(f"LOCK_ACQUISITION_FAILED: WinError {err} - transaction.lock held by active transaction or competing recovery.")

    return h


def delete_set2_target_handle_bound(target_path: Path, repo_root: Path) -> None:
    """Safely deletes a Set-2 target via open handle using parent-handle continuity and FileDispositionInfo."""
    if not target_path.exists():
        return

    parent_dir = target_path.parent.resolve()
    if not is_contained_in_directory(parent_dir, repo_root):
        raise RuntimeError(f"PARENT_DIRECTORY_UNAUTHORIZED: {parent_dir}")

    # Open parent directory handle
    parent_h = kernel32.CreateFileW(
        str(parent_dir),
        FILE_READ_ATTRIBUTES | SYNCHRONIZE,
        FILE_SHARE_READ,
        None,
        3,  # OPEN_EXISTING
        0x02000000 | FILE_OPEN_REPARSE_POINT,  # FILE_FLAG_BACKUP_SEMANTICS
        None
    )
    if parent_h == wintypes.HANDLE(-1).value:
        raise RuntimeError(f"Failed to open verified parent directory: {parent_dir}")

    try:
        # Open child relative to parent handle with DELETE access and FILE_OPEN_REPARSE_POINT
        child_name = target_path.name
        us = UNICODE_STRING()
        us.Buffer = child_name
        us.Length = len(child_name) * 2
        us.MaximumLength = us.Length

        oa = OBJECT_ATTRIBUTES()
        oa.Length = ctypes.sizeof(OBJECT_ATTRIBUTES)
        oa.RootDirectory = parent_h
        oa.ObjectName = ctypes.pointer(us)
        oa.Attributes = OBJ_CASE_INSENSITIVE

        iosb = IO_STATUS_BLOCK()
        child_h = wintypes.HANDLE()

        status = ntdll.NtCreateFile(
            ctypes.byref(child_h),
            DELETE | FILE_READ_ATTRIBUTES | SYNCHRONIZE,
            ctypes.byref(oa),
            ctypes.byref(iosb),
            None,
            0,
            FILE_SHARE_NONE,
            FILE_OPEN,
            FILE_NON_DIRECTORY_FILE | FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT,
            None,
            0
        )

        if status != STATUS_SUCCESS:
            raise RuntimeError(f"NtCreateFile failed on target child '{child_name}' (status=0x{status:08X})")

        try:
            # Set FileDispositionInfo to mark for deletion on close
            disp_info = FILE_DISPOSITION_INFO(True)
            res = kernel32.SetFileInformationByHandle(
                child_h,
                FileDispositionInfo,
                ctypes.byref(disp_info),
                ctypes.sizeof(FILE_DISPOSITION_INFO)
            )
            if not res:
                err = ctypes.get_last_error()
                raise RuntimeError(f"SetFileInformationByHandle(FileDispositionInfo) failed on '{child_name}' (err={err})")
        finally:
            kernel32.CloseHandle(child_h)
    finally:
        kernel32.CloseHandle(parent_h)


def rollback_governance_transaction(repo_root: Path, tx_id: str) -> None:
    """Executes deterministic, handle-bound rollback of transaction tx_id."""
    lock_h = acquire_recovery_lock(repo_root)
    try:
        journal_dir = repo_root / "scratch" / "catalog_journal"
        authoritative_slot, journal_data = determine_authoritative_journal_slot(journal_dir, tx_id)
        if journal_data.get("state") == "COMMITTED":
            print(f"Transaction '{tx_id}' is already durably COMMITTED in slot '{authoritative_slot}'. Rollback skipped to preserve committed state.")
            return

        current_seq = journal_data.get("sequence_number", 0)

        # 1. Restore Set-1 canonical targets from baseline backups if present
        baseline_dir = journal_dir / "baseline"
        if baseline_dir.is_dir():
            for bak_file in baseline_dir.glob("*.bak"):
                rel_name = bak_file.stem
                # Restore to target location
                dest = repo_root / rel_name
                if dest.parent.is_dir():
                    dest.write_bytes(bak_file.read_bytes())

        # 2. Delete candidate targets
        if tx_id == "GOV-LESSON-ARCHITECTURE-V2-FINAL-IMPLEMENTATION-R4-10":
            set2_targets = [
                repo_root / "src" / "ocean_sentinel" / "governance" / "runner.py",
                repo_root / "tests" / "test_staged_governance_isolation.py",
                repo_root / "scripts" / "recover_governance_transaction.py"
            ]
            for t in set2_targets:
                if t.name != "recover_governance_transaction.py" and t.is_file():
                    delete_set2_target_handle_bound(t, repo_root)

        # Clean up transaction-staged outputs
        staging_tx = repo_root / "scratch" / "staged_generation"
        for sub in ["receipts", "fixtures"]:
            tx_sub = staging_tx / sub / tx_id
            if tx_sub.is_dir():
                for f in tx_sub.glob("*"):
                    try:
                        f.unlink()
                    except OSError:
                        pass
                try:
                    tx_sub.rmdir()
                except OSError:
                    pass

        # 3. Write durable ROLLED_BACK state to opposite slot
        inactive_slot = "b" if authoritative_slot == "a" else "a"
        rollback_payload = {
            "schema": "ocean_sentinel_journal_state_v2",
            "transaction_id": tx_id,
            "sequence_number": current_seq + 1,
            "state": "ROLLED_BACK",
            "timestamp_utc": "2026-09-18T00:00:00Z"
        }
        rollback_payload["slot_checksum"] = compute_journal_slot_checksum(rollback_payload)
        
        target_slot_file = journal_dir / f"transaction_state_{inactive_slot}.json"
        tmp_slot_file = journal_dir / f"transaction_state_{inactive_slot}.json.tmp"
        
        with open(tmp_slot_file, "wb") as f:
            f.write(canonicalize_json_v1(rollback_payload))
            f.flush()
            os.fsync(f.fileno())
            
        os.replace(tmp_slot_file, target_slot_file)
        print(f"Transaction '{tx_id}' successfully rolled back. Journal slot '{inactive_slot}' is ROLLED_BACK.")

    finally:
        kernel32.CloseHandle(lock_h)


def main():
    if len(sys.argv) < 2:
        print("Usage: python recover_governance_transaction.py <tx_id> [--repo-root <path>]")
        sys.exit(1)
        
    tx_id = sys.argv[1]
    repo_root = Path(__file__).resolve().parent.parent
    rollback_governance_transaction(repo_root, tx_id)


if __name__ == "__main__":
    main()
