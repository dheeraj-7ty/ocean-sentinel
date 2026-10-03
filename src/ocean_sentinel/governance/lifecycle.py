"""Lifecycle and Validation History Manager for Ocean Sentinel Governance Entities."""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from ocean_sentinel.governance.models import (
    ActionType,
    EvidenceStrength,
    LearningState,
    Lesson,
    Rule,
    RuleChangeClass,
    SeverityLevel,
    ValidationRecord,
)


class LifecycleManager:
    """Enforces evidence-backed state transitions and maintains validation histories."""

    LEGAL_TRANSITIONS = {
        (LearningState.PROPOSED, LearningState.REVIEW_REQUIRED): "Quarantined rule moves to review phase.",
        (LearningState.REVIEW_REQUIRED, LearningState.REGRESSION_PROTECTED): "Requires automated regression test and verified passing control.",
        (LearningState.RECORDED, LearningState.REGRESSION_PROTECTED): "Requires automated regression test.",
        (LearningState.REGRESSION_PROTECTED, LearningState.PROVEN_STABLE): "Requires >= 2 subsequent task validation events with distinct evidence and anti-duplication fingerprints (validation diversity).",
        (LearningState.PROVEN_STABLE, LearningState.REGRESSION_PROTECTED): "Demoted upon detected regression or environment mutation.",
        (LearningState.REGRESSION_PROTECTED, LearningState.RECORDED): "Demoted if regression test is deprecated.",
        (LearningState.RECORDED, LearningState.DEPRECATED): "Deprecated due to obsolete architecture or data.",
        (LearningState.REVIEW_REQUIRED, LearningState.DEPRECATED): "Proposal rejected during review.",
        (LearningState.REGRESSION_PROTECTED, LearningState.SUPERSEDED): "Superseded by a newer, more comprehensive rule.",
        (LearningState.PROVEN_STABLE, LearningState.SUPERSEDED): "Superseded by a newer rule while preserving historical lineage.",
    }

    ILLEGAL_TRANSITIONS = {
        (LearningState.PROPOSED, LearningState.PROVEN_STABLE): "Direct promotion from PROPOSED to PROVEN_STABLE is strictly prohibited.",
        (LearningState.PROPOSED, LearningState.REGRESSION_PROTECTED): "Must pass through REVIEW_REQUIRED before becoming REGRESSION_PROTECTED.",
        (LearningState.REVIEW_REQUIRED, LearningState.PROVEN_STABLE): "Direct promotion from REVIEW_REQUIRED to PROVEN_STABLE is strictly prohibited.",
        (LearningState.RECORDED, LearningState.PROVEN_STABLE): "Direct promotion from RECORDED to PROVEN_STABLE is strictly prohibited; must pass through REGRESSION_PROTECTED.",
        (LearningState.DEPRECATED, LearningState.PROVEN_STABLE): "Cannot promote deprecated entity directly to PROVEN_STABLE.",
    }

    SYNTHETIC_OR_PLACEHOLDER_TASKS: Set[str] = {
        "", "SYNTHETIC", "DRY_RUN", "REPLAY", "UNKNOWN", "TEST", "TEST_TASK", "NONE"
    }

    @staticmethod
    def compute_validation_fingerprint(
        task: str,
        test: str,
        evidence: str = "",
        timestamp: str = "",
        environment: str = "python-3.10",
    ) -> str:
        """Computes a deterministic validation fingerprint to establish anti-duplication identity."""
        payload = f"{task.strip()}|{test.strip()}|{evidence.strip()}|{timestamp.strip()}|{environment.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def can_transition(
        cls,
        current: LearningState,
        target: LearningState,
        has_automated_test: bool = False,
        validation_records: Optional[List[ValidationRecord]] = None,
        origin_task: str = "",
    ) -> Tuple[bool, str]:
        """Evaluates whether a state transition is legal and backed by required evidence (anti-duplication & validation diversity)."""
        if current == target:
            return True, "No state change."

        if (current, target) in cls.ILLEGAL_TRANSITIONS:
            return False, f"Illegal transition: {cls.ILLEGAL_TRANSITIONS[(current, target)]}"

        if (current, target) not in cls.LEGAL_TRANSITIONS:
            return False, f"Undefined transition from {current.value} to {target.value}."

        if target == LearningState.REGRESSION_PROTECTED:
            if not has_automated_test:
                return False, "Cannot transition to REGRESSION_PROTECTED without an automated guardrail or pytest."

        if target == LearningState.PROVEN_STABLE:
            if not has_automated_test:
                return False, "Cannot transition to PROVEN_STABLE without an active automated test."
            val_records = validation_records or []
            passing_records = [v for v in val_records if getattr(v, "result", "") == "PASSED"]
            
            # Filter out synthetic / placeholder / replay tasks
            genuine_records = []
            for v in passing_records:
                task_name = getattr(v, "task", "").strip()
                task_upper = task_name.upper()
                is_synthetic = (
                    task_upper in cls.SYNTHETIC_OR_PLACEHOLDER_TASKS
                    or task_upper.startswith("REPLAY")
                    or task_upper.startswith("SYNTHETIC")
                    or task_upper.startswith("DRY_RUN")
                    or task_upper.startswith("DRYRUN")
                    or task_upper.startswith("TEST-")
                    or task_upper.startswith("AUTO-CHAIN")
                    or task_upper.startswith("AUTO_CHAIN")
                )
                if not is_synthetic:
                    genuine_records.append(v)
                else:
                    return False, f"BLOCK-010-SYNTHETIC_VALIDATION_PROHIBITED: Synthetic, replay, or automated placeholder task '{task_name}' cannot validate PROVEN_STABLE promotion."

            # Reject self-validation by introduction task
            norm_origin = origin_task.strip()
            subsequent_records = []
            for v in genuine_records:
                task_name = getattr(v, "task", "").strip()
                if norm_origin and task_name == norm_origin:
                    continue  # Origin task cannot count as subsequent validation
                subsequent_records.append(v)

            if len(subsequent_records) == 0 and len(genuine_records) > 0 and norm_origin:
                return False, f"BLOCK-010-SELF_VALIDATION_PROHIBITED: Origin task '{origin_task}' cannot self-validate PROVEN_STABLE promotion."

            # Check fingerprint uniqueness across validations (anti-duplication)
            fingerprints = set()
            for v in subsequent_records:
                fp = getattr(v, "fingerprint", "")
                if not fp:
                    fp = cls.compute_validation_fingerprint(
                        task=getattr(v, "task", ""),
                        test=getattr(v, "test", ""),
                        evidence=getattr(v, "evidence", ""),
                        timestamp=getattr(v, "timestamp", ""),
                        environment=getattr(v, "environment", "python-3.10"),
                    )
                if fp in fingerprints:
                    return False, "BLOCK-010-DUPLICATE_VALIDATION: Duplicate validation fingerprint detected; identical validation events cannot be counted multiple times."
                fingerprints.add(fp)

            distinct_tasks = set(getattr(v, "task", "").strip() for v in subsequent_records)
            if len(distinct_tasks) < 2:
                return False, (
                    f"BLOCK-010-UNVERIFIED_PROVEN_STABLE: Requires validation across at least 2 independent tasks "
                    f"(subsequent to origin; found {len(distinct_tasks)}: {distinct_tasks})."
                )

            # Check for duplicate evidence content across distinct validation events (Anti-Duplication / Validation Diversity)
            evidence_hashes = set()
            for v in subsequent_records:
                ev = getattr(v, "evidence", "").strip()
                if ev:
                    norm_ev = " ".join(ev.split()).lower()
                    ev_hash = hashlib.sha256(norm_ev.encode("utf-8")).hexdigest()
                    if ev_hash in evidence_hashes:
                        return False, "BLOCK-010-DUPLICATE_EVIDENCE: Duplicate evidence content detected across subsequent validation records; identical test/fixture evidence cannot be reused to manufacture promotion."
                    evidence_hashes.add(ev_hash)

        return True, f"Legal transition authorized: {cls.LEGAL_TRANSITIONS[(current, target)]}"

    @classmethod
    def record_validation(
        cls,
        entity: Lesson,
        task: str,
        test: str,
        result: str,
        evidence: str = "",
        timestamp: Optional[str] = None,
        environment: str = "python-3.10",
    ) -> ValidationRecord:
        """Appends an immutable validation record to an entity's history with calculated fingerprint."""
        ts = timestamp or datetime.utcnow().isoformat() + "Z"
        fp = cls.compute_validation_fingerprint(
            task=task,
            test=test,
            evidence=evidence,
            timestamp=ts,
            environment=environment,
        )
        record = ValidationRecord(
            task=task,
            timestamp=ts,
            test=test,
            result=result,
            environment=environment,
            scope="regression",
            evidence=evidence,
            fingerprint=fp,
        )
        entity.validation_history.append(record)
        entity.last_validated = ts
        return record

    @classmethod
    def classify_rule_change(cls, old_rule: Rule, new_rule: Rule) -> Tuple[RuleChangeClass, str]:
        """Classifies modifications to a governance rule for monotonic safety."""
        # 1. Check for weakening: severity downgrade, action downgrade, removed non_overridable, or removed checks/prohibitions
        is_weakening = False
        reasons = []
        if new_rule.severity.rank < old_rule.severity.rank:
            is_weakening = True
            reasons.append(f"Severity downgraded from {old_rule.severity.value} to {new_rule.severity.value}")
        if old_rule.action == ActionType.BLOCK and new_rule.action != ActionType.BLOCK:
            is_weakening = True
            reasons.append(f"Action downgraded from BLOCK to {new_rule.action.value}")
        if old_rule.non_overridable and not new_rule.non_overridable:
            is_weakening = True
            reasons.append("non_overridable flag removed")
        removed_prohibitions = set(old_rule.prohibited_actions) - set(new_rule.prohibited_actions)
        if removed_prohibitions:
            is_weakening = True
            reasons.append(f"Prohibited actions removed: {sorted(list(removed_prohibitions))}")
        removed_checks = set(old_rule.required_checks) - set(new_rule.required_checks)
        if removed_checks:
            is_weakening = True
            reasons.append(f"Required checks removed: {sorted(list(removed_checks))}")
        
        if is_weakening:
            return RuleChangeClass.WEAKENING, "; ".join(reasons)

        # 2. Check for strengthening
        is_strengthening = False
        s_reasons = []
        if new_rule.severity.rank > old_rule.severity.rank:
            is_strengthening = True
            s_reasons.append(f"Severity upgraded from {old_rule.severity.value} to {new_rule.severity.value}")
        if old_rule.action != ActionType.BLOCK and new_rule.action == ActionType.BLOCK:
            is_strengthening = True
            s_reasons.append(f"Action upgraded from {old_rule.action.value} to BLOCK")
        if not old_rule.non_overridable and new_rule.non_overridable:
            is_strengthening = True
            s_reasons.append("non_overridable flag added")
        added_prohibitions = set(new_rule.prohibited_actions) - set(old_rule.prohibited_actions)
        if added_prohibitions:
            is_strengthening = True
            s_reasons.append(f"Prohibited actions added: {sorted(list(added_prohibitions))}")

        if is_strengthening:
            return RuleChangeClass.STRENGTHENING, "; ".join(s_reasons)

        # 3. Check scope changes
        if new_rule.scope.rank < old_rule.scope.rank:
            return RuleChangeClass.NARROWING, f"Scope narrowed from {old_rule.scope.value} to {new_rule.scope.value}"
        if new_rule.scope.rank > old_rule.scope.rank:
            return RuleChangeClass.BROADENING, f"Scope broadened from {old_rule.scope.value} to {new_rule.scope.value}"

        return RuleChangeClass.SEMANTIC_CHANGE, "Statement or metadata updated without weakening severity, actions, or scope"

    @classmethod
    def validate_monotonic_safety(cls, old_rule: Rule, new_rule: Rule) -> Tuple[bool, str]:
        """Ensures that rule modifications do not silently weaken protected invariants."""
        change_class, reason = cls.classify_rule_change(old_rule, new_rule)
        
        if change_class != RuleChangeClass.WEAKENING:
            return True, f"Monotonic safety satisfied: change classified as {change_class.value} ({reason})."

        # Check if rule protects a critical invariant
        rule_ident = f"{old_rule.rule_id} {old_rule.title} {old_rule.statement}".lower()
        critical_invariants = [
            "holdout", "part_iii", "part iii", "destructive_git", "git clean", "git reset",
            "unauthorized_training", "model.train", "canonical", "freeze", "protocol_mutation"
        ]
        is_critical_invariant = (
            old_rule.non_overridable
            or old_rule.severity == SeverityLevel.CRITICAL
            or any(inv in rule_ident for inv in critical_invariants)
        )

        if is_critical_invariant:
            return False, (
                f"CRITICAL_SAFETY_WEAKENING_PROHIBITED: Cannot weaken rule '{old_rule.rule_id}' "
                f"protecting critical invariant: {reason}. Fail-closed monotonic safety barrier active."
            )

        return True, (
            f"REASSESSMENT_REQUIRED: Rule '{old_rule.rule_id}' weakened ({reason}). "
            f"Explicit governance review and state reassessment required."
        )

    @classmethod
    def is_quarantined(cls, rule: Rule) -> bool:
        """Determines if a rule is quarantined (PROPOSED or REVIEW_REQUIRED)."""
        return rule.status in (LearningState.PROPOSED, LearningState.REVIEW_REQUIRED)

    @classmethod
    def calculate_rule_impact(cls, rule_id: str, store: Any) -> Dict[str, Any]:
        """Calculates impact graph for a modified or proposed rule."""
        rule = store.get_rule(rule_id)
        if not rule:
            return {"error": f"Rule {rule_id} not found"}
        
        impacted_lessons = [l.lesson_id for l in store.list_lessons() if rule_id in l.rules]
        impacted_incidents = [i.incident_id for i in store.list_incidents() if rule_id in i.rules_created]
        impacted_assumptions = [a.assumption_id for a in store.list_assumptions() if rule_id in a.associated_rules]
        
        return {
            "rule_id": rule_id,
            "principle_id": rule.principle_id,
            "failure_class": rule.failure_class,
            "lifecycle_state": rule.status.value,
            "impacted_lessons": impacted_lessons,
            "impacted_incidents": impacted_incidents,
            "impacted_assumptions": impacted_assumptions,
            "tests": rule.regression_test_ids,
            "reassessment_required": rule.status == LearningState.PROVEN_STABLE,
        }


# ==============================================================================
# Transaction & Provenance Lifecycle Management (Lesson Architecture V2 R4-10)
# ==============================================================================

import ctypes
from ctypes import wintypes
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from ocean_sentinel.governance.provenance import (
    AUTHORITATIVE_RUNNER_CODE_SHA256,
    canonicalize_json_v1,
    compute_journal_slot_checksum,
    determine_authoritative_journal_slot,
    is_contained_in_directory,
    verify_journal_slot_file,
    verify_receipt_integrity,
)

ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Win32 Constants
FILE_SHARE_NONE = 0x00000000
FILE_SHARE_READ = 0x00000001
FILE_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
OPEN_EXISTING = 3
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000


def _check_test_fault_injection(point_name: str) -> None:
    """Test-only fault injection seam. Inactive unless explicitly set in environment.
    Emulates abrupt process termination without normal exception handling or cleanup.
    """
    target_point = os.environ.get("OCEAN_SENTINEL_FAULT_INJECTION_POINT")
    if target_point and target_point == point_name:
        exit_code = int(os.environ.get("OCEAN_SENTINEL_FAULT_INJECTION_EXIT_CODE", "77"))
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(exit_code)

EXPECTED_TAXONOMY_SOURCE_SHA256 = "680f9bd6460e02a7cfea0e92a1b528becedf80d9467d6c03e25adb1896b2bbbb"


def get_authoritative_interpreter(repo_root: Path) -> Path:
    """Resolves and verifies the authoritative project virtual-environment Python interpreter.
    Strictly fails closed if the canonical .venv interpreter does not exist or fails verification.
    Zero fallback to global sys.executable or ambient PATH.
    """
    canonical_venv = (repo_root / ".venv").resolve()
    if not canonical_venv.is_dir() or not (canonical_venv / "pyvenv.cfg").is_file():
        raise RuntimeError(f"CANONICAL_VENV_INVALID: Virtual environment invalid or absent: {canonical_venv}")
        
    venv_python = (canonical_venv / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")).resolve()
    if not venv_python.is_file():
        raise RuntimeError(f"CANONICAL_INTERPRETER_ABSENT: Interpreter executable absent: {venv_python}")
        
    if not is_contained_in_directory(venv_python, canonical_venv):
        raise RuntimeError(f"INTERPRETER_ESCAPES_VENV: Python interpreter escapes canonical venv: {venv_python}")
        
    return venv_python


def verify_runner_code_integrity(runner_script: Path, expected_hash: str) -> None:
    """Verifies that runner.py matches the cryptographically pinned code hash."""
    if not runner_script.is_file():
        raise RuntimeError(f"RUNNER_SCRIPT_ABSENT: Governance runner script absent: {runner_script}")
    content = runner_script.read_bytes()
    actual_hash = hashlib.sha256(content).hexdigest()
    if actual_hash != expected_hash:
        raise RuntimeError(
            f"RUNNER_INTEGRITY_MISMATCH: Runner code hash mismatch! (expected={expected_hash}, actual={actual_hash})"
        )


class GovernanceTransactionManager:
    """Durable transaction coordinator for Lesson Architecture V2.
    Enforces Win32 zero-share kernel lease (dwShareMode=0), dual-slot ping-pong journaling,
    frozen taxonomy snapshots, and COMMITTED-before-release finalization.
    """

    def __init__(self, repo_root: Path, tx_id: str):
        self.repo_root = repo_root.resolve()
        self.tx_id = tx_id
        self.journal_dir = (self.repo_root / "scratch" / "catalog_journal").resolve()
        self.staging_dir = (self.repo_root / "scratch" / "staged_generation").resolve()
        self.lock_file = (self.journal_dir / "transaction.lock").resolve()
        
        self.lock_handle: Optional[wintypes.HANDLE] = None
        self.current_slot: Optional[str] = None
        self.sequence_number: int = 0
        
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

    def acquire_exclusive_lease(self) -> None:
        """Acquires an exclusive Win32 zero-share lease on transaction.lock sentinel."""
        if not self.lock_file.is_file():
            with open(self.lock_file, "a") as f:
                pass

        h = kernel32.CreateFileW(
            str(self.lock_file),
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_NONE,  # dwShareMode=0
            None,
            OPEN_EXISTING,
            FILE_FLAG_OPEN_REPARSE_POINT,
            None
        )

        if h in (-1, 0xFFFFFFFFFFFFFFFF, wintypes.HANDLE(-1).value):
            err = ctypes.get_last_error()
            raise RuntimeError(
                f"TRANSACTION_LEASE_DENIED: WinError {err} - transaction.lock held with exclusive access by another transaction."
            )

        self.lock_handle = h

    def release_exclusive_lease(self) -> None:
        """Releases the kernel transaction authority by closing handle. Sentinel is NEVER unlinked."""
        if self.lock_handle is not None and self.lock_handle not in (-1, 0xFFFFFFFFFFFFFFFF, wintypes.HANDLE(-1).value):
            kernel32.CloseHandle(self.lock_handle)
            self.lock_handle = None

    def write_journal_transition(
        self,
        new_state: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, int]:
        """Writes next journal generation with explicit slot destination semantics.
        1. Identifies active slot and opposite/inactive slot.
        2. Increments sequence number monotonically.
        3. Serializes via OCEAN_SENTINEL_CANONICAL_JSON_V1 and computes slot_checksum.
        4. Atomic rename via temporary file with fsync flush.
        5. Verifies new state on disk before returning.
        """
        # Explicit slot destination tracking
        if self.current_slot is None:
            # First write in transaction: determine initial destination
            try:
                auth_slot, auth_data = determine_authoritative_journal_slot(self.journal_dir, self.tx_id)
                self.current_slot = auth_slot
                self.sequence_number = auth_data.get("sequence_number", 0)
                target_slot = "b" if self.current_slot == "a" else "a"
            except RuntimeError:
                # Fresh transaction starting in slot A
                self.current_slot = "b"
                target_slot = "a"
                self.sequence_number = 0
        else:
            target_slot = "b" if self.current_slot == "a" else "a"

        candidate_sequence = self.sequence_number + 1

        payload = {
            "schema": "ocean_sentinel_journal_state_v2",
            "transaction_id": self.tx_id,
            "sequence_number": candidate_sequence,
            "state": new_state,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "authoritative_runner_sha256": AUTHORITATIVE_RUNNER_CODE_SHA256
        }
        if extra_data:
            payload.update(extra_data)

        # Compute canonical slot checksum excluding slot_checksum
        payload["slot_checksum"] = compute_journal_slot_checksum(payload)

        tmp_file = self.journal_dir / f"transaction_state_{target_slot}.json.tmp"
        dest_file = self.journal_dir / f"transaction_state_{target_slot}.json"

        canonical_bytes = canonicalize_json_v1(payload)
        with open(tmp_file, "wb") as f:
            f.write(canonical_bytes)
            f.flush()
            _check_test_fault_injection("BEFORE_JOURNAL_FSYNC")
            _check_test_fault_injection(f"BEFORE_JOURNAL_FSYNC_{new_state}")
            os.fsync(f.fileno())

        _check_test_fault_injection("BEFORE_JOURNAL_REPLACE")
        _check_test_fault_injection(f"BEFORE_JOURNAL_REPLACE_{new_state}")

        os.replace(tmp_file, dest_file)

        _check_test_fault_injection("AFTER_JOURNAL_REPLACE_BEFORE_VERIFICATION")
        _check_test_fault_injection(f"AFTER_JOURNAL_REPLACE_BEFORE_VERIFICATION_{new_state}")

        # Verify disk write
        status, seq, verified_data = verify_journal_slot_file(dest_file)
        if status != "VALID" or seq != candidate_sequence or verified_data.get("state") != new_state:
            raise RuntimeError(f"JOURNAL_WRITE_VERIFICATION_FAILED: Destination slot '{target_slot}' invalid on disk!")

        _check_test_fault_injection("AFTER_JOURNAL_FSYNC_BEFORE_ACK")
        _check_test_fault_injection("AFTER_JOURNAL_VERIFICATION_BEFORE_ACK")
        _check_test_fault_injection(f"AFTER_JOURNAL_VERIFICATION_BEFORE_ACK_{new_state}")

        self.current_slot = target_slot
        self.sequence_number = candidate_sequence
        return self.current_slot, self.sequence_number

    def prepare_phase_d_taxonomy_freeze(
        self,
        approved_ops: Dict[str, Any]
    ) -> Tuple[Path, str, str]:
        """Phase D: Validates taxonomy.py digest, creates frozen snapshot, and returns (path, src_hash, snap_hash)."""
        tax_file = (self.repo_root / "src" / "ocean_sentinel" / "governance" / "taxonomy.py").resolve()
        if not tax_file.is_file():
            raise RuntimeError(f"TAXONOMY_ABSENT: {tax_file}")

        tax_bytes = tax_file.read_bytes()
        actual_src_tax_sha256 = hashlib.sha256(tax_bytes).hexdigest()
        if actual_src_tax_sha256 != EXPECTED_TAXONOMY_SOURCE_SHA256:
            raise RuntimeError(
                f"TAXONOMY_PIN_VIOLATION: taxonomy.py SHA256 mismatch! "
                f"(expected={EXPECTED_TAXONOMY_SOURCE_SHA256}, actual={actual_src_tax_sha256})"
            )

        snapshot_payload = {
            "snapshot_schema": "ocean_sentinel_frozen_taxonomy_v2",
            "transaction_id": self.tx_id,
            "source_taxonomy_sha256": actual_src_tax_sha256,
            "approved_analytical_operations": approved_ops
        }
        snap_bytes = canonicalize_json_v1(snapshot_payload)
        snap_sha256 = hashlib.sha256(snap_bytes).hexdigest()

        snap_path = self.journal_dir / f"frozen_taxonomy_{self.tx_id}.json"
        with open(snap_path, "wb") as f:
            f.write(snap_bytes)
            f.flush()
            os.fsync(f.fileno())

        self.source_taxonomy_sha256 = actual_src_tax_sha256
        self.frozen_taxonomy_snapshot_sha256 = snap_sha256
        return snap_path, actual_src_tax_sha256, snap_sha256

    def stage_authorized_fixture(
        self,
        fixture_relative_path: str,
        fixture_bytes: bytes
    ) -> Tuple[Path, str]:
        """Stages an authorized fixture inside the transaction-bound fixture root and computes exact byte hash."""
        raw_fix = str(fixture_relative_path).replace("\\", "/")
        if raw_fix.startswith("/") or (len(raw_fix) > 1 and raw_fix[1] == ":"):
            raise RuntimeError(f"ABSOLUTE_FIXTURE_PATH_REJECTED: {fixture_relative_path}")
        if ".." in Path(raw_fix).parts or raw_fix.startswith(".."):
            raise RuntimeError(f"PATH_TRAVERSAL_REJECTED: {fixture_relative_path}")
            
        fixture_root = (self.staging_dir / "fixtures" / self.tx_id).resolve()
        target_path = (fixture_root / fixture_relative_path).resolve()
        if not is_contained_in_directory(target_path, fixture_root):
            raise RuntimeError(f"FIXTURE_PATH_ESCAPES_ROOT: {target_path}")
            
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(fixture_bytes)
        
        expected_sha256 = hashlib.sha256(fixture_bytes).hexdigest()
        self.authorized_fixture_rel_path = fixture_relative_path
        self.authorized_fixture_sha256 = expected_sha256
        return target_path, expected_sha256

    def launch_provenance_runner(
        self,
        operation_id: str,
        fixture_input_path: Optional[Path] = None,
        receipt_output_path: Optional[Path] = None,
        declared_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Launches the authoritative isolated provenance runner and verifies receipt integrity."""
        interpreter = get_authoritative_interpreter(self.repo_root)
        runner_script = (self.repo_root / "src" / "ocean_sentinel" / "governance" / "runner.py").resolve()

        # Pre-execution verification of runner code
        verify_runner_code_integrity(runner_script, AUTHORITATIVE_RUNNER_CODE_SHA256)

        sandbox_cwd = (self.staging_dir / "runner_sandbox").resolve()
        sandbox_cwd.mkdir(parents=True, exist_ok=True)

        sys_root = os.environ.get("SYSTEMROOT", r"C:\Windows")
        clean_env = {
            "SYSTEMROOT": sys_root,
            "WINDIR": os.environ.get("WINDIR", sys_root),
            "COMSPEC": os.environ.get("COMSPEC", rf"{sys_root}\system32\cmd.exe"),
            "PATH": rf"{sys_root}\system32;{sys_root};{sys_root}\System32\Wbem",
            "TEMP": str(sandbox_cwd),
            "TMP": str(sandbox_cwd),
        }

        # Resolve relative fixture and receipt parameters
        fix_rel = getattr(self, "authorized_fixture_rel_path", None)
        if fixture_input_path:
            if not os.path.isabs(str(fixture_input_path)):
                fix_rel = str(fixture_input_path)
            else:
                fix_rel = Path(fixture_input_path).name

        # Ensure state transition to EXECUTING with fixture metadata
        exec_extra = {}
        if hasattr(self, "authorized_fixture_sha256") and self.authorized_fixture_sha256:
            exec_extra["expected_fixture_sha256"] = self.authorized_fixture_sha256
            exec_extra["fixture_relative_path"] = self.authorized_fixture_rel_path
        elif fixture_input_path:
            fixture_root = (self.staging_dir / "fixtures" / self.tx_id).resolve()
            p = (fixture_root / Path(fixture_input_path).name).resolve()
            if p.is_file():
                fix_bytes = p.read_bytes()
                exec_extra["expected_fixture_sha256"] = hashlib.sha256(fix_bytes).hexdigest()
                exec_extra["fixture_relative_path"] = p.name
                self.authorized_fixture_sha256 = exec_extra["expected_fixture_sha256"]
                self.authorized_fixture_rel_path = p.name

        if hasattr(self, "source_taxonomy_sha256") and self.source_taxonomy_sha256:
            exec_extra["source_taxonomy_sha256"] = self.source_taxonomy_sha256
        if hasattr(self, "frozen_taxonomy_snapshot_sha256") and self.frozen_taxonomy_snapshot_sha256:
            exec_extra["frozen_taxonomy_snapshot_sha256"] = self.frozen_taxonomy_snapshot_sha256

        # Check snapshot file on disk if not already set
        snap_file = self.journal_dir / f"frozen_taxonomy_{self.tx_id}.json"
        if snap_file.is_file():
            snap_bytes = snap_file.read_bytes()
            exec_extra.setdefault("frozen_taxonomy_snapshot_sha256", hashlib.sha256(snap_bytes).hexdigest())
            try:
                snap_json = json.loads(snap_bytes.decode("utf-8"))
                if "source_taxonomy_sha256" in snap_json:
                    exec_extra.setdefault("source_taxonomy_sha256", snap_json["source_taxonomy_sha256"])
            except Exception:
                pass

        if self.current_slot:
            try:
                curr_file = self.journal_dir / f"transaction_state_{self.current_slot}.json"
                if curr_file.is_file():
                    _, _, curr_data = verify_journal_slot_file(curr_file)
                    if curr_data:
                        for k in ("source_taxonomy_sha256", "frozen_taxonomy_snapshot_sha256"):
                            if k in curr_data and k not in exec_extra:
                                exec_extra[k] = curr_data[k]
            except Exception:
                pass

        self.write_journal_transition("EXECUTING", exec_extra)

        cmd = [
            str(interpreter),
            "-I",
            str(runner_script),
            "--tx-id", self.tx_id,
            "--journal-slot", self.current_slot,
            "--operation-id", operation_id,
        ]
        if fix_rel:
            cmd.extend(["--fixture-input", fix_rel])
        cmd.extend(["--receipt-output", f"receipt_{self.tx_id}.json"])

        _check_test_fault_injection("BEFORE_RUNNER_LAUNCH")

        proc = subprocess.run(
            cmd,
            cwd=str(sandbox_cwd),
            env=clean_env,
            capture_output=True,
            text=True,
            timeout=60
        )

        expected_receipt_path = (self.staging_dir / "receipts" / self.tx_id / f"receipt_{self.tx_id}.json").resolve()
        if proc.returncode != 0:
            if "RECEIPT_PREEXISTING_FILE_COLLISION" not in proc.stderr and expected_receipt_path.exists():
                try:
                    expected_receipt_path.unlink()
                except OSError:
                    pass
            raise RuntimeError(f"PROVENANCE_RUNNER_FAILED (code {proc.returncode}): {proc.stderr}")

        # Parent verifies receipt integrity mechanically
        verified_receipt = verify_receipt_integrity(expected_receipt_path)
        return verified_receipt

    def finalize_committed_transaction(self, expected_receipt_path: Optional[Path] = None) -> None:
        """Executes strict finalization ordering:
        1. Verify prerequisites: transaction must be in active state (ACTIVATED/EXECUTING)
        2. Verify outputs & filesystem state (receipt exists on disk and passes integrity)
        3. Execute and flush housekeeping (history manifest)
        4. Write durable COMMITTED state to inactive slot (with fsync)
        5. Independently reread and verify COMMITTED slot from disk
        6. Release exclusive kernel lock handle
        """
        if self.current_slot is None or self.lock_handle is None:
            raise RuntimeError("FINALIZATION_PRECONDITION_FAILED: Transaction not held under lock or missing slot.")
            
        auth_slot, auth_data = determine_authoritative_journal_slot(self.journal_dir, self.tx_id)
        if auth_data.get("state") not in {"ACTIVATED", "EXECUTING"}:
            raise RuntimeError(f"FINALIZATION_INVALID_STATE: Current state is {auth_data.get('state')}, expected ACTIVATED or EXECUTING.")

        # Verify outputs & filesystem state
        receipt_to_verify = expected_receipt_path
        if receipt_to_verify is None:
            receipt_to_verify = (self.staging_dir / "receipts" / self.tx_id / f"receipt_{self.tx_id}.json").resolve()
            
        if not receipt_to_verify.is_file():
            raise RuntimeError(f"FINALIZATION_OUTPUT_MISSING: Expected receipt file missing: {receipt_to_verify}")
            
        verify_receipt_integrity(receipt_to_verify)

        # 3. Housekeeping: archive transaction history
        history_dir = self.journal_dir / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        history_file = history_dir / f"{self.tx_id}_manifest.json"
        hist_tmp = history_dir / f"{self.tx_id}_manifest.json.tmp"
        with open(hist_tmp, "w", encoding="utf-8") as f:
            json.dump({
                "transaction_id": self.tx_id,
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": "COMMITTED",
                "final_sequence": self.sequence_number + 1
            }, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(hist_tmp, history_file)

        # Fault injection: candidate receipt is verified, housekeeping is done, but COMMITTED not yet written
        _check_test_fault_injection("AFTER_CANDIDATE_PUBLISH_BEFORE_COMMITTED")

        # 4. Write durable COMMITTED state to inactive slot
        committed_slot, committed_seq = self.write_journal_transition("COMMITTED")

        # 5. Independently reread and verify COMMITTED slot from disk
        verified_slot, verified_data = determine_authoritative_journal_slot(self.journal_dir, self.tx_id)
        if verified_slot != committed_slot or verified_data.get("state") != "COMMITTED" or verified_data.get("sequence_number") != committed_seq:
            raise RuntimeError("COMMITTED_SLOT_VERIFICATION_FAILED: Failed to independently verify COMMITTED state on disk.")

        # Fault injection: COMMITTED is durably on disk and independently verified, but lock not yet released
        _check_test_fault_injection("AFTER_COMMITTED_DURABILITY_BEFORE_LOCK_RELEASE")

        # 6. Only then release exclusive kernel lock handle
        self.release_exclusive_lease()

        # Fault injection: normal finalization completed and lock released
        _check_test_fault_injection("AFTER_LOCK_RELEASE")

    def rollback_transaction(self) -> None:
        """Executes handle-bound rollback and marks ROLLED_BACK in durable journal."""
        try:
            # 1. Restore Set-1 baselines if present in baseline backup
            baseline_dir = self.journal_dir / "baseline"
            if baseline_dir.is_dir():
                for bak in baseline_dir.glob("*.bak"):
                    dest = self.repo_root / bak.stem
                    if dest.parent.is_dir():
                        dest.write_bytes(bak.read_bytes())

            # 2. Delete Set-2 candidate targets if rolling back bootstrap transaction
            if self.tx_id == "GOV-LESSON-ARCHITECTURE-V2-FINAL-IMPLEMENTATION-R4-10":
                for set2 in [
                    self.repo_root / "src" / "ocean_sentinel" / "governance" / "runner.py",
                    self.repo_root / "tests" / "test_staged_governance_isolation.py",
                    self.repo_root / "scripts" / "recover_governance_transaction.py"
                ]:
                    if set2.is_file():
                        try:
                            set2.unlink()
                        except OSError:
                            pass

            # Clean up transaction-staged outputs
            for sub in ["receipts", "fixtures"]:
                tx_sub = self.staging_dir / sub / self.tx_id
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

            # 3. Record ROLLED_BACK state
            self.write_journal_transition("ROLLED_BACK")
        finally:
            self.release_exclusive_lease()


