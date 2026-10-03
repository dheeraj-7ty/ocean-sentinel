"""Statistical and Scientific Method Provenance Validator.
Root Trust Anchor and Canonical Verification Module under Option B Model.
Profile: OCEAN_SENTINEL_CANONICAL_JSON_V1
"""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from ocean_sentinel.governance.models import PreflightIssueV2, SeverityLevel

# Finalized Candidate Bootstrap Root of Trust (Section 7)
# Exact SHA-256 digest of src/ocean_sentinel/governance/runner.py
AUTHORITATIVE_RUNNER_CODE_SHA256: str = "dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0"


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


def compute_receipt_integrity_sha256(receipt_data: Dict[str, Any]) -> str:
    """Computes canonical SHA256 integrity digest over all receipt fields strictly
    excluding receipt_integrity_sha256 using OCEAN_SENTINEL_CANONICAL_JSON_V1.
    Provides integrity and correlation only; NOT authentication or non-repudiation.
    """
    canonical_dict = {k: v for k, v in receipt_data.items() if k != "receipt_integrity_sha256"}
    canonical_bytes = canonicalize_json_v1(canonical_dict)
    return hashlib.sha256(canonical_bytes).hexdigest()


def verify_receipt_integrity(receipt_path: Path) -> Dict[str, Any]:
    """Parent-side mechanical verification of receipt canonical integrity.
    Re-serializes receipt fields using OCEAN_SENTINEL_CANONICAL_JSON_V1 and asserts exact digest match.
    Provides integrity and correlation; promotion authority remains exclusively with parent under transaction.lock.
    """
    if not receipt_path.is_file():
        raise RuntimeError(f"RECEIPT_ABSENT: Receipt file absent on disk: {receipt_path}")
        
    try:
        raw_bytes = receipt_path.read_bytes()
        receipt_data = json.loads(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"RECEIPT_CORRUPTED: Failed to decode receipt JSON: {exc}")
        
    stored_digest = receipt_data.get("receipt_integrity_sha256")
    if not stored_digest or not isinstance(stored_digest, str):
        raise RuntimeError("RECEIPT_INTEGRITY_MISSING: Receipt missing 'receipt_integrity_sha256' field.")
        
    expected_digest = compute_receipt_integrity_sha256(receipt_data)
    
    if stored_digest != expected_digest:
        raise RuntimeError(
            f"RECEIPT_INTEGRITY_MISMATCH: Stored receipt integrity hash '{stored_digest}' "
            f"does not match recomputed canonical hash '{expected_digest}'. Promotion rejected."
        )
        
    return receipt_data


def get_authoritative_interpreter(repo_root: Path) -> Path:
    """Verifies that the canonical .venv python interpreter exists and is strictly contained."""
    canonical_venv = (repo_root / ".venv").resolve()
    pyvenv_cfg = canonical_venv / "pyvenv.cfg"
    if not pyvenv_cfg.is_file():
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


class MethodProvenanceValidator:
    """Validates full scientific provenance chain:
    Question -> Estimand -> Data -> Population -> Observation -> Method Config -> Executed Result -> Artifact -> Report.
    """

    @staticmethod
    def validate_statistical_payload(payload: Dict[str, Any]) -> List[PreflightIssueV2]:
        """Audits a statistical artifact or evaluation payload for method provenance and integrity."""
        issues: List[PreflightIssueV2] = []

        test_name = payload.get("test_name", payload.get("test", "")).lower()

        # 1. Verify explicit method parameter binding (GOV-RULE-130)
        method = payload.get("method") or payload.get("method_argument") or payload.get("distribution")
        if not method:
            issues.append(PreflightIssueV2(
                severity=SeverityLevel.CRITICAL,
                code="PROV-001-UNBOUND_METHOD",
                rule_id="GOV-RULE-130",
                message=f"Statistical call for '{test_name}' did not explicitly bind method/distribution parameter.",
                remediation="Explicitly pass method='asymptotic' or method='exact' in code and record it in artifact metadata."
            ))

        # 2. Check for fake degrees of freedom on non-parametric tests
        if "wilcoxon" in test_name or "mannwhitney" in test_name:
            if "degrees_of_freedom" in payload or "df" in payload:
                issues.append(PreflightIssueV2(
                    severity=SeverityLevel.HIGH,
                    code="PROV-002-INVALID_DF_NONPARAMETRIC",
                    rule_id="GOV-RULE-130",
                    message=f"Non-parametric test '{test_name}' contains invalid 'degrees_of_freedom' field.",
                    remediation="Remove degrees of freedom from Wilcoxon/Mann-Whitney test artifacts; report sample size N_paired instead."
                ))

        # 3. Check for observation unit vs inference unit separation
        has_obs_n = any(k in payload for k in ("n_observations", "n_tiles", "n_pixels", "n_samples"))
        has_inf_n = any(k in payload for k in ("n_paired", "n_clusters", "n_effective", "n_scenes"))
        if not has_inf_n and not has_obs_n:
            issues.append(PreflightIssueV2(
                severity=SeverityLevel.HIGH,
                code="PROV-003-MISSING_SAMPLE_SIZE",
                rule_id="GOV-RULE-116",
                message="Statistical artifact lacks explicit sample size (observation n or inferential n).",
                remediation="Explicitly record both observation unit count and inferential cluster count."
            ))

        # 4. Check numerical validity of statistic and p-value
        if "p_value" in payload:
            pval = payload["p_value"]
            if not isinstance(pval, (int, float)) or pval < 0.0 or pval > 1.0:
                issues.append(PreflightIssueV2(
                    severity=SeverityLevel.CRITICAL,
                    code="PROV-004-INVALID_P_VALUE",
                    rule_id="GOV-RULE-100",
                    message=f"Invalid p-value: {pval} (must be float between 0.0 and 1.0).",
                    remediation="Verify statistical computation output."
                ))

        # 5. Check tie and zero handling declaration
        if "wilcoxon" in test_name:
            if "zero_method" not in payload and "zero_handling" not in payload:
                issues.append(PreflightIssueV2(
                    severity=SeverityLevel.MEDIUM,
                    code="PROV-005-UNDECLARED_ZERO_METHOD",
                    rule_id="GOV-RULE-130",
                    message="Wilcoxon test payload does not document zero_method ('wilcox', 'pratt', or 'zsplit').",
                    remediation="Document explicit zero_method in artifact metadata."
                ))

            # 5b. Audit ties and zeros under requested method="exact"
            has_ties = payload.get("has_ties", payload.get("ties_present", False))
            has_zeros = payload.get("has_zeros", payload.get("zeros_present", False))
            method_arg = str(payload.get("method", payload.get("method_argument", ""))).lower()
            exact_semantics = payload.get("exact_p_value_semantics", payload.get("p_value_semantics", ""))

            if method_arg == "exact":
                if has_ties or has_zeros:
                    # In SciPy 1.15.3, ties or zeros alter the null distribution; method="exact" no longer calculates an exact p-value
                    if exact_semantics != "NOT_EXACT_UNDER_DOCUMENTED_ASSUMPTIONS":
                        issues.append(PreflightIssueV2(
                            severity=SeverityLevel.HIGH,
                            code="PROV-010-EXACT_ASSUMPTION_VIOLATION",
                            rule_id="GOV-RULE-132",
                            message="SciPy wilcoxon method='exact' with ties or zeros does not produce a mathematically exact p-value; exact_p_value_semantics must be declared as 'NOT_EXACT_UNDER_DOCUMENTED_ASSUMPTIONS'.",
                            remediation="Set exact_p_value_semantics='NOT_EXACT_UNDER_DOCUMENTED_ASSUMPTIONS' or execute an alternative verified procedure such as PermutationMethod."
                        ))

            # 5c. Audit PermutationMethod configuration and executed procedure
            if "permutationmethod" in str(type(payload.get("method"))).lower() or "permutation" in method_arg:
                executed_algo = payload.get("executed_algorithm", "").lower()
                n_resamples = payload.get("n_resamples", payload.get("resamples"))
                if not executed_algo or "permutation" not in executed_algo:
                    issues.append(PreflightIssueV2(
                        severity=SeverityLevel.HIGH,
                        code="PROV-011-UNVERIFIED_PERMUTATION_CONFIGURATION",
                        rule_id="GOV-RULE-132",
                        message="Payload requested PermutationMethod but executed_algorithm does not verify that permutation testing actually occurred.",
                        remediation="Verify and record executed_algorithm='permutation_test' with verified n_resamples in provenance payload."
                    ))

        # 6. Check library version and algorithm semantics (GOV-RULE-132)
        lib = payload.get("library", "").lower()
        ver = payload.get("version", "")
        if lib == "scipy":
            if ver and not str(ver).startswith("1.15."):
                issues.append(PreflightIssueV2(
                    severity=SeverityLevel.HIGH,
                    code="METHOD_SEMANTICS_REVIEW_REQUIRED",
                    rule_id="GOV-RULE-132",
                    message=f"SciPy version '{ver}' differs from verified reference version (1.15.3); statistical method semantics must be reviewed.",
                    remediation="Re-verify algorithm semantics against the newly installed SciPy documentation."
                ))
            
            executed_algo = payload.get("executed_algorithm", "").lower()
            method_arg = str(payload.get("method", payload.get("method_argument", ""))).lower()
            if "wilcoxon" in test_name and method_arg == "exact":
                if "permutation" in executed_algo or "randomization" in executed_algo:
                    issues.append(PreflightIssueV2(
                        severity=SeverityLevel.HIGH,
                        code="PROV-007-STATISTICAL_CONFLATION",
                        rule_id="GOV-RULE-132",
                        message="SciPy wilcoxon method='exact' executes the exact discrete signed-rank distribution, not a permutation test.",
                        remediation="Declare executed_algorithm as 'exact discrete signed-rank distribution' or use PermutationMethod."
                    ))

        # 7. Check full provenance record completeness
        required_prov = ["library", "function", "method_argument", "executed_algorithm", "assumptions", "zero_handling", "tie_handling", "verification_source"]
        missing_prov = [f for f in required_prov if f not in payload]
        if missing_prov and payload.get("formal_artifact", False):
            issues.append(PreflightIssueV2(
                severity=SeverityLevel.MEDIUM,
                code="PROV-008-INCOMPLETE_PROVENANCE",
                rule_id="GOV-RULE-132",
                message=f"Statistical artifact missing provenance fields: {missing_prov}",
                remediation=f"Record full provenance: {required_prov}."
            ))

        return issues

    @staticmethod
    def audit_report_consistency(
        artifact_metrics: Dict[str, Any], report_text: str
    ) -> List[PreflightIssueV2]:
        """Verifies that numerical claims and method descriptions in report match machine artifact values (GOV-RULE-100, GOV-RULE-132)."""
        issues: List[PreflightIssueV2] = []
        report_lower = report_text.lower()

        # 1. Search for p-values in report
        if "p_value" in artifact_metrics:
            pval = artifact_metrics["p_value"]
            pval_str_3 = f"{pval:.3f}"
            pval_str_4 = f"{pval:.4f}"
            if "p = " in report_lower or "p-value" in report_lower or "p=" in report_lower:
                if pval_str_3 not in report_text and pval_str_4 not in report_text:
                    issues.append(PreflightIssueV2(
                        severity=SeverityLevel.HIGH,
                        code="PROV-006-REPORT_METRIC_DISCREPANCY",
                        rule_id="GOV-RULE-100",
                        message=f"Report text does not contain machine p-value ({pval_str_4}).",
                        remediation="Derive narrative p-values directly from machine JSON artifacts."
                    ))

        # 2. Check method mismatch
        method_declared = str(artifact_metrics.get("method") or artifact_metrics.get("method_argument") or "").lower()
        if "asymptotic" in method_declared and "exact" in report_lower and "asymptotic" not in report_lower:
            issues.append(PreflightIssueV2(
                severity=SeverityLevel.HIGH,
                code="PROV-009-METHOD_MISMATCH",
                rule_id="GOV-RULE-100",
                message="Report claims exact inference while artifact used asymptotic approximation.",
                remediation="Align narrative description with executed method in machine artifact."
            ))
        elif "exact" in method_declared and "asymptotic" in report_lower and "exact" not in report_lower:
            issues.append(PreflightIssueV2(
                severity=SeverityLevel.HIGH,
                code="PROV-009-METHOD_MISMATCH",
                rule_id="GOV-RULE-100",
                message="Report claims asymptotic inference while artifact executed exact method.",
                remediation="Align narrative description with executed method in machine artifact."
            ))

        # 3. Check for statistical method conflation in report text (GOV-RULE-132)
        if ("wilcoxon" in report_lower and "exact permutation" in report_lower) or "conflating exact signed-rank" in report_lower:
            issues.append(PreflightIssueV2(
                severity=SeverityLevel.HIGH,
                code="GOV-RULE-132-STATISTICAL_CONFLATION",
                rule_id="GOV-RULE-132",
                message="Report conflates SciPy method='exact' with permutation testing.",
                remediation="Describe SciPy exact Wilcoxon as 'exact discrete signed-rank distribution'."
            ))

        # 4. Check for unconditional exact p-value claim with ties or zeros
        has_ties = artifact_metrics.get("has_ties", artifact_metrics.get("ties_present", False))
        has_zeros = artifact_metrics.get("has_zeros", artifact_metrics.get("zeros_present", False))
        if "wilcoxon" in str(artifact_metrics.get("test_name", artifact_metrics.get("test", ""))).lower():
            if (has_ties or has_zeros) and "exact p-value" in report_lower and "not exact under documented assumptions" not in report_lower and "stated assumptions" not in report_lower:
                issues.append(PreflightIssueV2(
                    severity=SeverityLevel.HIGH,
                    code="PROV-010-EXACT_ASSUMPTION_VIOLATION",
                    rule_id="GOV-RULE-132",
                    message="Report claims unconditional exact p-value for Wilcoxon test despite presence of ties or zeros.",
                    remediation="Document that method='exact' p-value is NOT_EXACT_UNDER_DOCUMENTED_ASSUMPTIONS due to ties or zeros."
                ))

        return issues
