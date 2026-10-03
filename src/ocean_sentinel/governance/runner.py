"""Authoritative Isolated Governance Analytical Runner.
Executes inside an isolated subprocess (python -I) to emit verified execution receipts.
Trust anchors are derived directly from the locked transaction journal slot, rejecting caller CLI tampering.
Profile: OCEAN_SENTINEL_CANONICAL_JSON_V1
"""

import argparse
import hashlib
import importlib
import inspect
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


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


def is_reparse_point(path: Path) -> bool:
    """Checks if a path is a symbolic link or NTFS reparse point."""
    try:
        p_str = str(path)
        if os.path.islink(p_str):
            return True
        st = os.lstat(p_str)
        if hasattr(st, "st_file_attributes") and (st.st_file_attributes & 0x0400):
            return True
        return False
    except OSError:
        return False


def canonicalize_json_v1(data: Dict[str, Any]) -> bytes:
    """Shared canonicalization profile: OCEAN_SENTINEL_CANONICAL_JSON_V1.
    - Keys sorted recursively (sort_keys=True)
    - Compact delimiters with zero whitespace (separators=(',', ':'))
    - ASCII-safe character escaping (ensure_ascii=True)
    - UTF-8 byte encoding
    NOTE: Provides deterministic byte representation; does not claim full RFC 8785 compliance.
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=True
    ).encode("utf-8")


def compute_journal_slot_checksum(slot_data: Dict[str, Any]) -> str:
    """Computes SHA256 checksum over all journal slot fields strictly excluding slot_checksum.
    Self-contained integrity detection (detecting torn writes or bitrot); not cryptographic authentication.
    """
    canonical_dict = {k: v for k, v in slot_data.items() if k != "slot_checksum"}
    canonical_bytes = canonicalize_json_v1(canonical_dict)
    return hashlib.sha256(canonical_bytes).hexdigest()


def verify_journal_slot_file(slot_file: Path) -> Tuple[str, Optional[int], Optional[Dict[str, Any]]]:
    """Inspects and validates integrity of a journal slot file.
    Returns (status, sequence_number, data):
      status: "VALID" | "CHECKSUM_MISMATCH" | "UNPARSEABLE" | "ABSENT"
    """
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
    """Deterministically identifies the authoritative active journal slot for tx_id.
    
    CRITICAL INVARIANTS:
    1. Integrity Verification Precedes Authority: All slots undergo checksum integrity
       evaluation BEFORE any sequence arbitration or authority selection.
    2. Silent Downgrade Prohibition: If a newer or contemporaneous slot is corrupt,
       the system FAILS CLOSED. It NEVER silently downgrades to a stale valid slot.
    3. Trust Boundary: Plain self-contained checksum detects bitrot and torn writes
       within the local-administrator security boundary; it is not cryptographic authentication.
    """
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
            if data.get("transaction_id") == tx_id and data.get("state") in {"PREPARED", "EXECUTING", "ACTIVATED", "COMMITTED", "ROLLED_BACK"}:
                valid_slots.append((slot_name, info["seq"], data, info["mtime"]))
        elif info["status"] in {"CHECKSUM_MISMATCH", "UNPARSEABLE"}:
            corrupt_slots.append((slot_name, info["status"], info["seq"], info["data"], info["mtime"]))

    # Case 1: Neither slot has valid checksum for tx_id -> fail closed
    if not valid_slots:
        if corrupt_slots:
            raise RuntimeError(
                f"ALL_JOURNAL_SLOTS_CORRUPT: Corrupted journal slot(s) detected with zero valid slots for tx_id '{tx_id}'. "
                f"Details: {[(c[0], c[1]) for c in corrupt_slots]}"
            )
        raise RuntimeError(f"NO_ACTIVE_JOURNAL_SLOT: No valid active journal slot found for tx_id '{tx_id}'.")

    # Case 2: One slot valid, but another slot is corrupt -> evaluate downgrade risk
    if len(valid_slots) == 1 and corrupt_slots:
        valid_name, valid_seq, valid_data, valid_mtime = valid_slots[0]
        for c_name, c_status, c_seq, c_data, c_mtime in corrupt_slots:
            if c_seq is not None and c_seq >= valid_seq:
                raise RuntimeError(
                    f"JOURNAL_CORRUPTED: Newer journal slot '{c_name}' (seq={c_seq}, status={c_status}) has failed "
                    f"integrity validation while older slot '{valid_name}' (seq={valid_seq}) is valid. "
                    f"Silent downgrade to stale authority is strictly barred."
                )
            if c_seq is None and c_mtime >= valid_mtime:
                raise RuntimeError(
                    f"JOURNAL_CORRUPTED: Corrupted unparseable journal slot '{c_name}' was modified contemporaneously "
                    f"or after valid slot '{valid_name}' (mtime {c_mtime} >= {valid_mtime}). "
                    f"Silent downgrade to stale authority is strictly barred."
                )
        return valid_name, valid_data

    # Case 3: Exactly one valid slot and no corrupt slots
    if len(valid_slots) == 1:
        return valid_slots[0][0], valid_slots[0][2]

    # Case 4: Both slots are valid and active for tx_id -> sequence arbitration
    slot_a, slot_b = valid_slots[0], valid_slots[1]
    if slot_a[1] > slot_b[1]:
        return slot_a[0], slot_a[2]
    elif slot_b[1] > slot_a[1]:
        return slot_b[0], slot_b[2]
    else:
        raise RuntimeError(
            f"JOURNAL_CORRUPTED: Duplicate sequence number {slot_a[1]} detected in slots '{slot_a[0]}' and '{slot_b[0]}' for tx_id '{tx_id}'."
        )


def child_derive_and_verify_paths() -> Tuple[Path, Path, Path]:
    """Independently derives and verifies venv_site_packages, project_src, and repo_root inside child.
    Never trusts caller-supplied paths across CLI.
    """
    running_interpreter = Path(sys.executable).resolve()
    if not getattr(sys.flags, "isolated", 0):
        raise RuntimeError("PREFLIGHT_SECURITY_FAILED: Runner must be invoked with isolated interpreter flag 'python -I'.")

    venv_root = running_interpreter.parent.parent
    if not (venv_root / "pyvenv.cfg").is_file():
        raise RuntimeError("Child interpreter is not inside a verified virtual environment.")
        
    site_pkg = (venv_root / "Lib" / "site-packages" if os.name == "nt" else venv_root / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages").resolve()
    if not site_pkg.is_dir() or not is_contained_in_directory(site_pkg, venv_root):
        raise RuntimeError(f"Derived site-packages invalid or escapes venv root: {site_pkg}")

    runner_file = Path(__file__).resolve()
    project_src = (runner_file.parent.parent.parent).resolve()
    repo_root = project_src.parent.resolve()
    if not (project_src / "ocean_sentinel" / "governance").is_dir():
        raise RuntimeError(f"Derived project src invalid: {project_src}")

    # Check for accidental external .pth path injection outside venv and project
    for pth_file in site_pkg.glob("*.pth"):
        try:
            for line in pth_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("import "):
                    pth_target = (site_pkg / line).resolve()
                    if not is_contained_in_directory(pth_target, venv_root) and not is_contained_in_directory(pth_target, repo_root):
                        raise RuntimeError(f"PREFLIGHT_SECURITY_FAILED: Uncontrolled .pth file '{pth_file.name}' references external path: {pth_target}")
        except Exception as err:
            if isinstance(err, RuntimeError):
                raise

    # Check that sys.path does not contain external global site-packages
    for p in sys.path:
        if "site-packages" in p.lower():
            resolved_p = Path(p).resolve()
            if not is_contained_in_directory(resolved_p, venv_root):
                raise RuntimeError(f"PREFLIGHT_SECURITY_FAILED: Accidental global site-packages detected in sys.path: {p}")
        
    return site_pkg, project_src, repo_root


def reconstruct_controlled_sys_path(venv_site_packages: Path, project_src: Path) -> None:
    """Reconstructs controlled sys.path with strict anti-shadowing order:
    1. Python standard library.
    2. Verified virtual-environment site-packages.
    3. Project source location (src/).
    Excludes current directory, ambient PYTHONPATH, and user site.
    """
    stdlib_paths = []
    for p in list(sys.path):
        if not p:
            continue
        norm_p = os.path.normcase(os.path.realpath(p))
        if is_contained_in_directory(Path(p), Path(sys.base_prefix)) and "site-packages" not in norm_p:
            stdlib_paths.append(os.path.realpath(p))
            
    norm_site_pkg = os.path.realpath(str(venv_site_packages))
    norm_src = os.path.realpath(str(project_src))
    
    controlled_path = []
    for entry in stdlib_paths + [norm_site_pkg, norm_src]:
        if entry not in controlled_path and os.path.isdir(entry):
            controlled_path.append(entry)
            
    sys.path.clear()
    sys.path.extend(controlled_path)


def child_load_and_verify_trust_anchors(
    tx_id: str,
    declared_journal_slot: str,
    repo_root: Path
) -> Tuple[str, str, str, Path, Optional[str], Optional[str]]:
    """Loads authoritative runner hash, snapshot digest, expected fixture hash, and fixture relative path
    directly from the verified active journal slot.
    Deterministically evaluates slots via sequence arbitration and asserts declared_journal_slot matches authoritative slot.
    """
    journal_dir = (repo_root / "scratch" / "catalog_journal").resolve()
    authoritative_slot, journal_data = determine_authoritative_journal_slot(journal_dir, tx_id)
    
    if declared_journal_slot != authoritative_slot:
        raise RuntimeError(
            f"DECLARED_SLOT_NOT_AUTHORITATIVE: Caller supplied slot '{declared_journal_slot}', "
            f"but authoritative active slot is '{authoritative_slot}'."
        )
        
    authoritative_runner_sha256 = journal_data.get("authoritative_runner_sha256")
    source_taxonomy_sha256 = journal_data.get("source_taxonomy_sha256")
    frozen_taxonomy_snapshot_sha256 = journal_data.get("frozen_taxonomy_snapshot_sha256")
    expected_fixture_sha256 = journal_data.get("expected_fixture_sha256")
    fixture_relative_path = journal_data.get("fixture_relative_path")
    
    if not authoritative_runner_sha256 or not frozen_taxonomy_snapshot_sha256 or not source_taxonomy_sha256:
        raise RuntimeError("Journal slot missing authoritative trust-anchor digests!")
        
    snapshot_path = (journal_dir / f"frozen_taxonomy_{tx_id}.json").resolve()
    if not is_contained_in_directory(snapshot_path, journal_dir):
        raise RuntimeError(f"Snapshot path escapes journal directory: {snapshot_path}")
    if not snapshot_path.is_file():
        raise RuntimeError(f"Snapshot file absent on disk: {snapshot_path}")
        
    return (
        authoritative_runner_sha256,
        source_taxonomy_sha256,
        frozen_taxonomy_snapshot_sha256,
        snapshot_path,
        expected_fixture_sha256,
        fixture_relative_path
    )


def verify_callable_origin(func: Any, expected_pkg: str, venv_site_packages: Path) -> str:
    """Verifies that the callable and its root package originate strictly from the verified site-packages.
    Enforces exact namespace semantics (preventing expected_pkg_fake prefix bypass).
    """
    # 1. Exact package namespace validation
    mod_name = getattr(func, "__module__", "")
    if mod_name != expected_pkg and not mod_name.startswith(expected_pkg + "."):
        raise RuntimeError(f"Callable module '{mod_name}' does not belong to exact package namespace '{expected_pkg}'.")

    # 2. Verify root package location
    root_pkg = importlib.import_module(expected_pkg)
    pkg_file = getattr(root_pkg, "__file__", None)
    if not pkg_file:
        raise RuntimeError(f"Package '{expected_pkg}' lacks __file__ attribute.")
    if not is_contained_in_directory(Path(pkg_file), venv_site_packages):
        raise RuntimeError(f"Package '{expected_pkg}' resolved from unapproved location: {pkg_file}")
        
    # 3. Verify callable source origin
    unwrapped = inspect.unwrap(func)
    src_file = inspect.getsourcefile(unwrapped) or inspect.getfile(unwrapped)
    if not src_file:
        raise RuntimeError(f"Cannot determine source file for callable {func}.")
    if not is_contained_in_directory(Path(src_file), venv_site_packages):
        raise RuntimeError(f"Callable source '{src_file}' does not originate from verified site-packages: {venv_site_packages}")
        
    return os.path.realpath(src_file)


def compute_receipt_integrity_sha256(receipt_data: Dict[str, Any]) -> str:
    """Computes canonical SHA256 integrity digest over all receipt fields strictly
    excluding receipt_integrity_sha256 using OCEAN_SENTINEL_CANONICAL_JSON_V1.
    Provides integrity and correlation only; NOT authentication or non-repudiation.
    """
    canonical_dict = {k: v for k, v in receipt_data.items() if k != "receipt_integrity_sha256"}
    canonical_bytes = canonicalize_json_v1(canonical_dict)
    return hashlib.sha256(canonical_bytes).hexdigest()


def execute_allowlisted_operation(
    tx_id: str,
    journal_slot: str,
    operation_id: str,
    fixture_input_path: Optional[str] = None,
    receipt_output_path: Optional[str] = None
) -> None:
    """Executes the allowlisted operation in the controlled environment and writes an execution receipt.
    Derives trust anchors directly from the locked journal slot; zero caller CLI hash trust.
    Single authoritative fixture digest: SHA256(EXACT_BYTES_READ_FROM_THE_AUTHORIZED_FIXTURE_FILE).
    """
    # Step 1: Independently derive and verify paths (rejecting caller path trust)
    derived_site_pkg, derived_src, derived_repo_root = child_derive_and_verify_paths()
    reconstruct_controlled_sys_path(derived_site_pkg, derived_src)

    # Step 2: Load authoritative trust anchors directly from verified active journal slot
    (
        expected_runner_sha256,
        expected_src_tax_sha256,
        expected_snapshot_sha256,
        snapshot_path,
        expected_fixture_sha256,
        journal_fixture_rel_path
    ) = child_load_and_verify_trust_anchors(tx_id, journal_slot, derived_repo_root)

    # Step 3: Self-verify runner code integrity against journal trust anchor
    runner_code = Path(__file__).resolve().read_bytes()
    actual_runner_sha256 = hashlib.sha256(runner_code).hexdigest()
    if actual_runner_sha256 != expected_runner_sha256:
        raise RuntimeError(
            f"Child self-check failed: runner.py code hash mismatch! "
            f"(expected={expected_runner_sha256}, actual={actual_runner_sha256})"
        )

    # Step 4: Load and verify frozen transaction snapshot against journal digest (NEVER import live taxonomy.py)
    spec_bytes = snapshot_path.read_bytes()
    actual_snapshot_sha256 = hashlib.sha256(spec_bytes).hexdigest()
    if actual_snapshot_sha256 != expected_snapshot_sha256:
        raise RuntimeError(
            f"Frozen taxonomy snapshot integrity mismatch! "
            f"(expected={expected_snapshot_sha256}, actual={actual_snapshot_sha256})"
        )
        
    frozen_taxonomy = json.loads(spec_bytes.decode("utf-8"))
    if frozen_taxonomy.get("transaction_id") != tx_id:
        raise RuntimeError(f"Snapshot transaction_id mismatch! (expected={tx_id}, actual={frozen_taxonomy.get('transaction_id')})")
    if frozen_taxonomy.get("source_taxonomy_sha256") != expected_src_tax_sha256:
        raise RuntimeError("Snapshot source_taxonomy_sha256 does not match locked journal anchor!")

    approved_ops = frozen_taxonomy.get("approved_analytical_operations", {})
    if operation_id not in approved_ops:
        raise ValueError(f"Operation ID '{operation_id}' is not in the frozen analytical operations allowlist.")
        
    op_spec = approved_ops[operation_id]
    
    # Step 5: Import module and resolve callable
    mod = importlib.import_module(op_spec["module"])
    func = getattr(mod, op_spec["function"])
    
    # Step 6: Verify module and file origin against verified venv site-packages with exact namespace checks
    verified_src_file = verify_callable_origin(func, op_spec["package"], derived_site_pkg)
    
    # Step 7: Dynamically query package version and enforce exact version pin (FAIL CLOSED)
    root_pkg = importlib.import_module(op_spec["package"])
    runtime_version = getattr(root_pkg, "__version__", None)
    if runtime_version != op_spec["reference_version"]:
        raise RuntimeError(
            f"PROVENANCE_VERSION_MISMATCH: Runtime version '{runtime_version}' does not match exact pinned "
            f"reference version '{op_spec['reference_version']}'. Promotion rejected."
        )

    # Step 8: Transaction-bound fixture authorization & TOCTOU-safe byte read
    authorized_fixture_root = (derived_repo_root / "scratch" / "staged_generation" / "fixtures" / tx_id).resolve()
    
    # 8.1 Caller path validation: reject absolute paths and path traversal
    if fixture_input_path:
        norm_fix_str = str(fixture_input_path).replace("\\", "/")
        if norm_fix_str.startswith("/") or (len(norm_fix_str) > 1 and norm_fix_str[1] == ":"):
            raise RuntimeError(f"ABSOLUTE_FIXTURE_PATH_REJECTED: Caller-supplied absolute fixture paths are strictly barred: {fixture_input_path}")
        if ".." in Path(norm_fix_str).parts or norm_fix_str.startswith(".."):
            raise RuntimeError(f"PATH_TRAVERSAL_REJECTED: Path traversal in fixture path is strictly barred: {fixture_input_path}")

    # 8.2 Derive authorized relative path from transaction-controlled state
    effective_fixture_rel = journal_fixture_rel_path or (Path(fixture_input_path).name if fixture_input_path else "fixture.json")
    if journal_fixture_rel_path and fixture_input_path:
        norm_journal = Path(journal_fixture_rel_path).name
        norm_caller = Path(fixture_input_path).name
        if norm_journal != norm_caller:
            raise RuntimeError(
                f"FIXTURE_PATH_NOT_AUTHORIZED_BY_TRANSACTION: Caller fixture path '{fixture_input_path}' "
                f"does not match transaction-authorized fixture path '{journal_fixture_rel_path}'."
            )

    final_fixture_path = (authorized_fixture_root / effective_fixture_rel).resolve()
    
    # 8.3 Strict containment check inside the transaction-owned root
    if not is_contained_in_directory(final_fixture_path, authorized_fixture_root):
        raise RuntimeError(f"FIXTURE_PATH_UNAUTHORIZED: Fixture path '{final_fixture_path}' escapes authorized transaction root '{authorized_fixture_root}'.")

    # 8.4 Reparse point / symlink check across entire path hierarchy
    curr_fix_check = final_fixture_path
    while curr_fix_check != derived_repo_root and curr_fix_check != curr_fix_check.parent:
        if curr_fix_check.exists() and is_reparse_point(curr_fix_check):
            raise RuntimeError(f"FIXTURE_REPARSE_POINT_DISALLOWED: Reparse point detected in fixture path hierarchy at '{curr_fix_check}'.")
        curr_fix_check = curr_fix_check.parent

    if not final_fixture_path.is_file():
        raise RuntimeError(f"FIXTURE_FILE_ABSENT: Authorized fixture file absent on disk: {final_fixture_path}")
        
    # 8.5 Read exact raw bytes once (Single Authoritative Definition: SHA256(EXACT_BYTES_READ_FROM_THE_AUTHORIZED_FIXTURE_FILE))
    fixture_bytes = final_fixture_path.read_bytes()
    observed_fixture_bytes_sha256 = hashlib.sha256(fixture_bytes).hexdigest()

    # 8.6 Compare observed byte hash against trusted expected hash from journal
    if not expected_fixture_sha256:
        raise RuntimeError(
            "MISSING_TRUSTED_FIXTURE_HASH: Expected fixture SHA256 must be supplied by the trusted journal boundary."
        )
    if observed_fixture_bytes_sha256 != expected_fixture_sha256:
        raise RuntimeError(
            f"FIXTURE_HASH_MISMATCH: Observed fixture bytes SHA256 '{observed_fixture_bytes_sha256}' "
            f"does not match trusted transaction expected hash '{expected_fixture_sha256}'. Execution halted."
        )

    try:
        payload = json.loads(fixture_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Fixture JSON decode failure: {exc}")
        
    call_args = payload.get("args", [])
    call_kwargs = payload.get("kwargs", {})
    declared_metadata = payload.get("declared_metadata", {})
    caller_declared_fixture_sha256 = payload.get("fixture_sha256")
    
    # 8.7 Non-authoritative metadata check: in-file fixture_sha256 CANNOT override security authority
    if caller_declared_fixture_sha256 is not None:
        if caller_declared_fixture_sha256 != observed_fixture_bytes_sha256:
            raise RuntimeError(
                f"FIXTURE_HASH_MISMATCH: In-file declared fixture hash '{caller_declared_fixture_sha256}' "
                f"does not match observed fixture file bytes SHA256 '{observed_fixture_bytes_sha256}'. Execution halted."
            )
    
    # Step 9: Execute the verified callable and capture observed facts
    start_time = time.perf_counter()
    result = func(*call_args, **call_kwargs)
    duration = time.perf_counter() - start_time
    
    # Step 10: Build and serialize execution receipt
    receipt = {
        "schema": "ocean_sentinel_provenance_receipt_v2",
        "operation_id": operation_id,
        "transaction_id": tx_id,
        "trust_anchors": {
            "authoritative_runner_sha256": expected_runner_sha256,
            "source_taxonomy_sha256": expected_src_tax_sha256,
            "frozen_taxonomy_snapshot_sha256": expected_snapshot_sha256,
            "trusted_expected_fixture_sha256": expected_fixture_sha256
        },
        "epistemic_provenance": {
            "DECLARED": {
                "caller_objective": declared_metadata.get("objective"),
                "caller_protocol_version": declared_metadata.get("protocol_version"),
                "caller_task_id": declared_metadata.get("task_id"),
                "caller_declared_fixture_sha256": caller_declared_fixture_sha256
            },
            "OBSERVED": {
                "interpreter_path": sys.executable,
                "process_pid": os.getpid(),
                "executed_function": f"{op_spec['module']}.{op_spec['function']}",
                "callable_source_file": verified_src_file,
                "invocation_kwargs": {k: str(v) for k, v in call_kwargs.items()},
                "execution_duration_sec": duration,
                "raw_statistic": float(getattr(result, "statistic", 0.0)),
                "raw_p_value": float(getattr(result, "pvalue", 0.0)),
                "observed_fixture_bytes_sha256": observed_fixture_bytes_sha256,
                "fixture_input_sha256": observed_fixture_bytes_sha256
            },
            "DERIVED": {
                "runtime_package_version": runtime_version,
                "reference_version_match": True,
                "fixture_bytes_match_trusted_anchor": (observed_fixture_bytes_sha256 == expected_fixture_sha256) if expected_fixture_sha256 else True
            }
        }
    }
    
    # Compute deterministic canonical receipt integrity digest
    receipt["receipt_integrity_sha256"] = compute_receipt_integrity_sha256(receipt)
    
    # Step 11: Transaction-bound receipt output authorization
    authorized_receipt_root = (derived_repo_root / "scratch" / "staged_generation" / "receipts" / tx_id).resolve()
    deterministic_receipt_name = f"receipt_{tx_id}.json"
    final_receipt_path = (authorized_receipt_root / deterministic_receipt_name).resolve()

    if receipt_output_path:
        norm_rcpt_str = str(receipt_output_path).replace("\\", "/")
        if norm_rcpt_str.startswith("/") or (len(norm_rcpt_str) > 1 and norm_rcpt_str[1] == ":"):
            raise RuntimeError(f"ABSOLUTE_RECEIPT_PATH_REJECTED: Caller-supplied absolute receipt paths are strictly barred: {receipt_output_path}")
        if ".." in Path(norm_rcpt_str).parts or norm_rcpt_str.startswith(".."):
            raise RuntimeError(f"PATH_TRAVERSAL_REJECTED: Path traversal in receipt path is strictly barred: {receipt_output_path}")
        if Path(norm_rcpt_str).name != deterministic_receipt_name:
            raise RuntimeError(
                f"RECEIPT_PATH_UNAUTHORIZED: Caller receipt path '{receipt_output_path}' does not match "
                f"transaction-derived deterministic filename '{deterministic_receipt_name}'."
            )

    if not is_contained_in_directory(final_receipt_path, authorized_receipt_root):
        raise RuntimeError(f"RECEIPT_PATH_UNAUTHORIZED: Receipt destination '{final_receipt_path}' escapes authorized transaction receipt root.")

    # Reparse point check on receipt path hierarchy
    curr_rcpt_check = authorized_receipt_root
    while curr_rcpt_check != derived_repo_root and curr_rcpt_check != curr_rcpt_check.parent:
        if curr_rcpt_check.exists() and is_reparse_point(curr_rcpt_check):
            raise RuntimeError(f"RECEIPT_REPARSE_POINT_DISALLOWED: Reparse point detected in receipt directory hierarchy at '{curr_rcpt_check}'.")
        curr_rcpt_check = curr_rcpt_check.parent

    # Refuse overwrite of pre-existing file
    if final_receipt_path.exists():
        raise RuntimeError(f"RECEIPT_PREEXISTING_FILE_COLLISION: Receipt destination '{final_receipt_path}' already exists on disk. Refusing to overwrite.")

    authorized_receipt_root.mkdir(parents=True, exist_ok=True)
    tmp_out = authorized_receipt_root / f"$T$.tx_{tx_id}_rcpt_{os.getpid()}.tmp"
    with open(tmp_out, "wb") as f:
        f.write(canonicalize_json_v1(receipt))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_out, final_receipt_path)


def main():
    """Main CLI entrypoint for child runner.
    Takes transaction coordinates and execution parameters. ZERO expected hashes are accepted on CLI.
    """
    parser = argparse.ArgumentParser(description="Authoritative Isolated Governance Analytical Runner")
    parser.add_argument("--tx-id", required=True, help="Active transaction identifier")
    parser.add_argument("--journal-slot", required=True, choices=["a", "b"], help="Active journal slot identifier")
    parser.add_argument("--operation-id", required=True, help="Allowlisted analytical operation ID")
    parser.add_argument("--fixture-input", required=False, default=None, help="Relative path to authorized fixture JSON within transaction root")
    parser.add_argument("--receipt-output", required=False, default=None, help="Relative path to write execution receipt JSON within transaction root")
    
    args = parser.parse_args()
    execute_allowlisted_operation(
        tx_id=args.tx_id,
        journal_slot=args.journal_slot,
        operation_id=args.operation_id,
        fixture_input_path=args.fixture_input,
        receipt_output_path=args.receipt_output
    )


if __name__ == "__main__":
    main()
