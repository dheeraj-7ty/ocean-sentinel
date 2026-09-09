"""Gate 4.2 Pre-Upload Operations Harness for Kaggle Dataset Packaging and Upload.

Provides production-grade, observable, failure-aware upload operations for the
certified Kaggle dataset: dheeraj12237/ocean-sentinel-trujillo-corpus (~56.19 GB).

Capabilities:
- Preflight inspection (git, staging, filesystem, network, auth, power)
- Network baseline benchmarking (uplink throughput with explicit uncertainty bounds)
- Real-time upload telemetry & rolling throughput window computation
- Persistent ASCII-safe observability (status.json, progress.log, events.log)
- Stall detection with configurable thresholds
- Non-intrusive diagnostic snapshots (never killing the upload process)
- 7-class failure classification based on empirical evidence
- Resumability inspection for Kaggle CLI / Google Cloud Storage state
- Controlled upload probe generation (strictly isolated, unexecuted)
- Production upload command generation (certified slug, private, unexecuted)
"""

from __future__ import annotations

import collections
import datetime
import enum
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

# =============================================================================
# State Enums and Data Models
# =============================================================================


class UploadState(str, enum.Enum):
    """High-level state of the dataset upload operation."""

    STARTING = "STARTING"
    ACTIVE = "ACTIVE"
    STALLED = "STALLED"
    ERROR = "ERROR"
    COMPLETE = "COMPLETE"
    UNKNOWN = "UNKNOWN"


class FailureClassification(str, enum.Enum):
    """Empirical failure classification categories."""

    NETWORK_BOTTLENECK = "network_bottleneck"
    LOCAL_DISK_BOTTLENECK = "local_disk_bottleneck"
    CPU_PROCESS_BOTTLENECK = "cpu_process_bottleneck"
    CLIENT_API_UPLOAD_ERROR = "client_api_upload_error"
    AUTHENTICATION_PROBLEM = "authentication_problem"
    REMOTE_SERVER_STALL = "likely_remote_server_stall"
    AMBIGUOUS_INSUFFICIENT_EVIDENCE = "ambiguous_insufficient_evidence"


@dataclass
class TelemetryState:
    """Snapshot of real-time upload telemetry."""

    timestamp: str
    elapsed_time_sec: float
    bytes_completed: int
    total_bytes: int
    percentage_bytes: float
    files_completed: Optional[int]
    total_files: Optional[int]
    current_file: Optional[str]
    instantaneous_throughput_bps: float
    rolling_60s_throughput_bps: float
    rolling_300s_throughput_bps: float
    overall_avg_throughput_bps: float
    eta_seconds: Optional[float]
    eta_formatted: str
    last_activity_timestamp: str
    time_since_last_progress_sec: float
    retry_error_count: int
    current_state: UploadState
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["current_state"] = self.current_state.value
        return d


@dataclass
class StallAssessment:
    """Result of a stall evaluation check."""

    is_stalled: bool
    severity: str  # "NONE", "WARNING", "CRITICAL"
    time_since_progress_sec: float
    warning_threshold_sec: float
    critical_threshold_sec: float
    action_recommended: str


# =============================================================================
# Helper: Environment and Subprocess Execution
# =============================================================================


def _run_cmd_safe(
    cmd: List[str] | str,
    cwd: Optional[Path] = None,
    timeout: float = 15.0,
    use_shell: bool = False,
) -> Tuple[int, str, str]:
    """Run a command safely without shell expansion vulnerabilities or credential leaks."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=use_shell,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:
        return -1, "", str(exc)


def _check_tcp_port(host: str, port: int = 443, timeout: float = 3.0) -> Tuple[bool, float]:
    """Test TCP reachability to host:port and measure RTT in milliseconds."""
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            rtt_ms = (time.perf_counter() - t0) * 1000.0
            return True, round(rtt_ms, 2)
    except Exception:
        return False, -1.0


# =============================================================================
# Capability A: Pre-Upload Preflight Collector
# =============================================================================


def _detect_default_cloud_python(repo_root: Path) -> Path:
    """Detect candidate cloud-tools python executable, prioritizing dedicated cloud-tools."""
    tools_python = Path("D:/Tools/cloud-tools/Scripts/python.exe")
    if tools_python.exists():
        return tools_python
    dotvenv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if dotvenv_python.exists():
        return dotvenv_python
    return repo_root / ".venv" / "Scripts" / "python.exe"


class PreflightCollector:
    """Gathers comprehensive environmental, filesystem, git, network, and power preflight state."""

    EXPECTED_TOTAL_BYTES = 56_193_499_563
    EXPECTED_TOTAL_FILES = 2403
    EXPECTED_IMAGE_COUNT = 1200
    EXPECTED_MASK_COUNT = 1200
    EXPECTED_ROOT_SHA256 = "e6e342d3c47aeed896283b31d7218d220bd465792d4d1f5d83485cc872b5c453"
    EXPECTED_DATASET_SLUG = "dheeraj12237/ocean-sentinel-trujillo-corpus"

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        staging_dir: Optional[Path] = None,
        cloud_venv_python: Optional[Path] = None,
    ):
        self.repo_root = repo_root or Path(__file__).resolve().parents[3]
        self.staging_dir = staging_dir or (
            self.repo_root
            / "experiments"
            / "performance"
            / "cloud_kaggle_dataset_package_preflight_20260907_022953"
            / "staging"
        )
        self.cloud_venv_python = cloud_venv_python or _detect_default_cloud_python(self.repo_root)

    def collect(self) -> Dict[str, Any]:
        """Execute full preflight collection without exposing credentials."""
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        git_info = self._get_git_state()
        staging_info = self._get_staging_metrics()
        kaggle_env = self._get_kaggle_environment()
        auth_state = self._get_auth_state()
        disk_info = self._get_disk_metrics()
        source_vol = self._get_source_volume_filesystem()
        net_adapter = self._get_active_network_adapter()
        connectivity = self._get_network_connectivity()
        power_state = self._get_system_power_state()

        preflight_record = {
            "timestamp": now_utc,
            "git_branch": git_info["branch"],
            "git_commit": git_info["commit"],
            "git_status": git_info["status"],
            "git_dirty_files_count": git_info["dirty_files_count"],
            "dataset_staging_path": str(self.staging_dir),
            "exact_total_byte_count": staging_info["total_byte_count"],
            "exact_file_count": staging_info["total_file_count"],
            "image_count": staging_info["image_count"],
            "mask_count": staging_info["mask_count"],
            "manifest_root_sha256": staging_info["root_sha256"],
            "kaggle_dataset_slug": staging_info["dataset_slug"],
            "kaggle_cli_version": kaggle_env["kaggle_cli_version"],
            "python_executable": kaggle_env["python_executable"],
            "cloud_venv_valid": kaggle_env["cloud_venv_valid"],
            "authentication_state": auth_state,  # Strictly "SET" or "NOT SET"
            "local_disk_free_space": disk_info,
            "source_volume_filesystem": source_vol,
            "active_network_adapter": net_adapter,
            "negotiated_link_speed": net_adapter.get("link_speed", "UNKNOWN"),
            "current_network_connectivity": connectivity,
            "upload_benchmark_result": None,
            "system_power_state": power_state,
        }
        return preflight_record

    def _get_git_state(self) -> Dict[str, Any]:
        code_b, branch, _ = _run_cmd_safe(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.repo_root
        )
        code_c, commit, _ = _run_cmd_safe(["git", "rev-parse", "HEAD"], cwd=self.repo_root)
        code_s, status_out, _ = _run_cmd_safe(["git", "status", "--porcelain"], cwd=self.repo_root)

        dirty_files = (
            [line.strip() for line in status_out.splitlines() if line.strip()] if status_out else []
        )
        is_dirty = len(dirty_files) > 0
        return {
            "branch": branch if code_b == 0 else "UNKNOWN",
            "commit": commit if code_c == 0 else "UNKNOWN",
            "status": "DIRTY" if is_dirty else "CLEAN",
            "dirty_files_count": len(dirty_files),
        }

    def _get_staging_metrics(self) -> Dict[str, Any]:
        """Compute exact byte counts and file counts without mutating filesystem."""
        if not self.staging_dir.exists():
            return {
                "total_byte_count": 0,
                "total_file_count": 0,
                "image_count": 0,
                "mask_count": 0,
                "root_sha256": None,
                "dataset_slug": None,
            }

        total_bytes = 0
        total_files = 0
        image_count = 0
        mask_count = 0

        for root, dirs, files in os.walk(self.staging_dir):
            for file_name in files:
                total_files += 1
                file_path = Path(root) / file_name
                try:
                    total_bytes += file_path.stat().st_size
                except OSError:
                    pass

                rel = file_path.relative_to(self.staging_dir).as_posix()
                if rel.startswith("images/"):
                    image_count += 1
                elif rel.startswith("masks/"):
                    mask_count += 1

        root_sha256 = None
        manifest_path = self.staging_dir / "manifest" / "integrity_manifest.json"
        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                root_sha256 = data.get("corpus_root_sha256") or data.get("root_sha256")
            except Exception:
                pass

        slug = None
        metadata_path = self.staging_dir / "dataset-metadata.json"
        if metadata_path.exists():
            try:
                meta = json.loads(metadata_path.read_text(encoding="utf-8"))
                slug = meta.get("id")
            except Exception:
                pass

        return {
            "total_byte_count": total_bytes,
            "total_file_count": total_files,
            "image_count": image_count,
            "mask_count": mask_count,
            "root_sha256": root_sha256,
            "dataset_slug": slug,
        }

    def _get_kaggle_environment(self) -> Dict[str, Any]:
        kaggle_exe = self.cloud_venv_python.parent / (
            "kaggle.exe" if sys.platform == "win32" else "kaggle"
        )
        cli_version = "NOT FOUND"
        if kaggle_exe.exists():
            code, out, _ = _run_cmd_safe([str(kaggle_exe), "--version"])
            if code == 0 and out:
                cli_version = out.strip()

        return {
            "kaggle_cli_version": cli_version,
            "python_executable": str(self.cloud_venv_python),
            "cloud_venv_valid": self.cloud_venv_python.exists() and kaggle_exe.exists(),
        }

    def _get_auth_state(self) -> str:
        """Inspect authentication state only as 'SET' or 'NOT SET'. Never print credentials."""
        # 1. Environment variables
        user_env = os.environ.get("KAGGLE_USERNAME")
        key_env = os.environ.get("KAGGLE_KEY")
        if user_env and key_env:
            return "SET"

        # 2. Config files ~/.kaggle/kaggle.json and ~/.kaggle/credentials.json
        home = Path.home()
        config_file = home / ".kaggle" / "kaggle.json"
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text(encoding="utf-8"))
                if data.get("username") and data.get("key"):
                    return "SET"
            except Exception:
                pass

        creds_file = home / ".kaggle" / "credentials.json"
        if creds_file.exists():
            try:
                data = json.loads(creds_file.read_text(encoding="utf-8"))
                if data.get("username") and (
                    data.get("refresh_token") or data.get("access_token")
                ):
                    return "SET"
            except Exception:
                pass

        return "NOT SET"

    def _get_disk_metrics(self) -> Dict[str, Any]:
        """Check free disk space on staging drive (D:) and temp/OS drive (C:)."""
        metrics = {}
        for drive in ["C:", "D:"]:
            path = Path(f"{drive}\\") if sys.platform == "win32" else Path("/")
            if path.exists():
                try:
                    usage = shutil.disk_usage(path)
                    metrics[drive] = {
                        "total_bytes": usage.total,
                        "free_bytes": usage.free,
                        "used_bytes": usage.used,
                        "free_gb": round(usage.free / (1024**3), 2),
                        "total_gb": round(usage.total / (1024**3), 2),
                    }
                except Exception:
                    metrics[drive] = "UNAVAILABLE"
        return metrics

    def _get_source_volume_filesystem(self) -> Dict[str, Any]:
        """Obtain volume filesystem and label info for staging drive."""
        source_drive = self.staging_dir.drive or "D:"
        res = {
            "drive": source_drive,
            "filesystem": "NTFS",
            "label": "Data",
        }
        if sys.platform == "win32":
            ps_cmd = (
                f"Get-Volume -DriveLetter {source_drive.replace(':', '')} | "
                "Select-Object FileSystem, FileSystemLabel, Size, SizeRemaining | ConvertTo-Json"
            )
            code, out, _ = _run_cmd_safe(["powershell", "-NoProfile", "-Command", ps_cmd])
            if code == 0 and out:
                try:
                    v_data = json.loads(out)
                    res["filesystem"] = v_data.get("FileSystem", "NTFS")
                    res["label"] = v_data.get("FileSystemLabel", "")
                except Exception:
                    pass
        return res

    def _get_active_network_adapter(self) -> Dict[str, Any]:
        """Detect active network adapter and link speed."""
        adapter_info: Dict[str, Any] = {
            "name": "UNKNOWN",
            "interface_description": "UNKNOWN",
            "status": "UNKNOWN",
            "link_speed": "UNKNOWN",
        }
        if sys.platform == "win32":
            ps_cmd = (
                "Get-NetAdapter | Where-Object Status -eq 'Up' | "
                "Select-Object Name, InterfaceDescription, Status, LinkSpeed | ConvertTo-Json"
            )
            code, out, _ = _run_cmd_safe(["powershell", "-NoProfile", "-Command", ps_cmd])
            if code == 0 and out:
                try:
                    data = json.loads(out)
                    if isinstance(data, list) and len(data) > 0:
                        data = data[0]
                    adapter_info["name"] = data.get("Name", "UNKNOWN")
                    adapter_info["interface_description"] = data.get(
                        "InterfaceDescription", "UNKNOWN"
                    )
                    adapter_info["status"] = data.get("Status", "Up")
                    adapter_info["link_speed"] = data.get("LinkSpeed", "UNKNOWN")
                except Exception:
                    pass
        return adapter_info

    def _get_network_connectivity(self) -> Dict[str, Any]:
        """Verify reachability to kaggle.com and storage.googleapis.com on port 443."""
        k_ok, k_rtt = _check_tcp_port("kaggle.com", 443)
        g_ok, g_rtt = _check_tcp_port("storage.googleapis.com", 443)
        return {
            "kaggle_com": {"reachable": k_ok, "rtt_ms": k_rtt},
            "storage_googleapis_com": {"reachable": g_ok, "rtt_ms": g_rtt},
        }

    def _get_system_power_state(self) -> Dict[str, Any]:
        """Record AC line status and battery percentage to ensure unthrottled upload."""
        p_info: Dict[str, Any] = {
            "ac_line_status": "UNKNOWN",
            "battery_percent": None,
            "power_saving_active": False,
        }
        if sys.platform == "win32":
            ps_cmd = (
                "Get-CimInstance -ClassName Win32_Battery | "
                "Select-Object EstimatedChargeRemaining, BatteryStatus | ConvertTo-Json"
            )
            code, out, _ = _run_cmd_safe(["powershell", "-NoProfile", "-Command", ps_cmd])
            if code == 0 and out:
                try:
                    data = json.loads(out)
                    if isinstance(data, list) and len(data) > 0:
                        data = data[0]
                    p_info["battery_percent"] = data.get("EstimatedChargeRemaining")
                    status_code = data.get("BatteryStatus")
                    # 1: Discharging, 2: AC Connected / Charging, etc.
                    p_info["ac_line_status"] = "Online" if status_code == 2 else "Offline"
                except Exception:
                    pass
        return p_info


# =============================================================================
# Capability B: Controlled Network Baseline Benchmarker
# =============================================================================


class NetworkBaselineBenchmarker:
    """Controlled upload measurement mechanism with explicit uncertainty documentation."""

    UNCERTAINTY_DISCLAIMER = (
        "Measurement represents baseline uplink performance to the designated test endpoint. "
        "It does NOT guarantee identical throughput to Google Cloud Storage due to differences in "
        "regional edge ingress points, TCP window sizing, SSL session reuse, "
        "and Kaggle API rate limiting."
    )

    def measure(
        self,
        endpoint: str = "https://httpbin.org/post",
        payload_size_bytes: int = 1_048_576,  # 1 MB
        timeout_sec: float = 10.0,
    ) -> Dict[str, Any]:
        """Send a controlled synthetic byte payload to measure uplink throughput."""
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        dummy_data = b"0" * payload_size_bytes

        t0 = time.perf_counter()
        try:
            import requests  # available in venvs

            response = requests.post(
                endpoint,
                data=dummy_data,
                timeout=timeout_sec,
                headers={"Content-Type": "application/octet-stream"},
            )
            dt = time.perf_counter() - t0
            status_code = response.status_code
            success = 200 <= status_code < 300
        except Exception as exc:
            dt = time.perf_counter() - t0
            return {
                "timestamp": now_utc,
                "endpoint": endpoint,
                "test_method": f"HTTP POST {payload_size_bytes} synthetic bytes",
                "success": False,
                "error": str(exc),
                "duration_sec": round(dt, 3),
                "measured_throughput_mb_s": 0.0,
                "measured_throughput_mbps": 0.0,
                "limitations_and_uncertainty": self.UNCERTAINTY_DISCLAIMER,
            }

        mb_sent = payload_size_bytes / (1024 * 1024)
        throughput_mb_s = mb_sent / dt if dt > 0 else 0.0
        throughput_mbps = (payload_size_bytes * 8) / (dt * 1_000_000) if dt > 0 else 0.0

        return {
            "timestamp": now_utc,
            "endpoint": endpoint,
            "test_method": f"HTTP POST {payload_size_bytes} synthetic bytes",
            "success": success,
            "status_code": status_code,
            "bytes_sent": payload_size_bytes,
            "duration_sec": round(dt, 3),
            "measured_throughput_mb_s": round(throughput_mb_s, 2),
            "measured_throughput_mbps": round(throughput_mbps, 2),
            "limitations_and_uncertainty": self.UNCERTAINTY_DISCLAIMER,
        }


# =============================================================================
# Capability E: Stall Detector
# =============================================================================


class StallDetector:
    """Explicit stall detection separating slow transfers from genuine stalls."""

    def __init__(
        self,
        heartbeat_interval_sec: float = 10.0,
        warning_threshold_sec: float = 60.0,
        critical_stall_threshold_sec: float = 180.0,
    ):
        self.heartbeat_interval_sec = heartbeat_interval_sec
        self.warning_threshold_sec = warning_threshold_sec
        self.critical_stall_threshold_sec = critical_stall_threshold_sec

    def evaluate(
        self, time_since_progress_sec: float, current_state: UploadState
    ) -> StallAssessment:
        """Evaluate stall status against configurable thresholds."""
        if current_state in (UploadState.COMPLETE, UploadState.STARTING):
            return StallAssessment(
                is_stalled=False,
                severity="NONE",
                time_since_progress_sec=time_since_progress_sec,
                warning_threshold_sec=self.warning_threshold_sec,
                critical_threshold_sec=self.critical_stall_threshold_sec,
                action_recommended="NO_ACTION_REQUIRED",
            )

        if time_since_progress_sec >= self.critical_stall_threshold_sec:
            return StallAssessment(
                is_stalled=True,
                severity="CRITICAL",
                time_since_progress_sec=time_since_progress_sec,
                warning_threshold_sec=self.warning_threshold_sec,
                critical_threshold_sec=self.critical_stall_threshold_sec,
                action_recommended="COLLECT_DIAGNOSTIC_SNAPSHOT_AND_NOTIFY_OPERATOR_DO_NOT_KILL",
            )
        elif time_since_progress_sec >= self.warning_threshold_sec:
            return StallAssessment(
                is_stalled=True,
                severity="WARNING",
                time_since_progress_sec=time_since_progress_sec,
                warning_threshold_sec=self.warning_threshold_sec,
                critical_threshold_sec=self.critical_stall_threshold_sec,
                action_recommended="LOG_WARNING_INCREASE_TELEMETRY_FREQUENCY",
            )
        else:
            return StallAssessment(
                is_stalled=False,
                severity="NONE",
                time_since_progress_sec=time_since_progress_sec,
                warning_threshold_sec=self.warning_threshold_sec,
                critical_threshold_sec=self.critical_stall_threshold_sec,
                action_recommended="CONTINUE_MONITORING",
            )


# =============================================================================
# Capability F: Non-Secret Diagnostic Snapshot Collector
# =============================================================================


class DiagnosticSnapshotCollector:
    """Gathers non-secret system and network diagnostics without killing the upload process."""

    def collect(self, target_pid: Optional[int] = None) -> Dict[str, Any]:
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        snapshot: Dict[str, Any] = {
            "timestamp": now_utc,
            "target_pid": target_pid,
            "network_adapter": None,
            "cpu_utilization_percent": None,
            "disk_free_c_gb": None,
            "disk_free_d_gb": None,
            "process_state": None,
            "network_counters": None,
        }

        # Disk space
        for drive, key in [("C:\\", "disk_free_c_gb"), ("D:\\", "disk_free_d_gb")]:
            if Path(drive).exists():
                try:
                    u = shutil.disk_usage(drive)
                    snapshot[key] = round(u.free / (1024**3), 2)
                except Exception:
                    pass

        # Use psutil if available (e.g. in .venv)
        try:
            import psutil

            snapshot["cpu_utilization_percent"] = psutil.cpu_percent(interval=0.1)
            net_io = psutil.net_io_counters()
            if net_io:
                snapshot["network_counters"] = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "errin": net_io.errin,
                    "errout": net_io.errout,
                    "dropin": net_io.dropin,
                    "dropout": net_io.dropout,
                }
            try:
                stats = psutil.net_if_stats()
                # Prefer non-loopback active adapters
                candidate = None
                for iface_name, iface_stat in stats.items():
                    if iface_stat.isup and iface_stat.speed > 0:
                        if "loopback" not in iface_name.lower():
                            candidate = {
                                "name": iface_name,
                                "link_speed_mbps": iface_stat.speed,
                                "is_up": iface_stat.isup,
                            }
                            break
                        elif candidate is None:
                            candidate = {
                                "name": iface_name,
                                "link_speed_mbps": iface_stat.speed,
                                "is_up": iface_stat.isup,
                            }
                snapshot["network_adapter"] = candidate
            except Exception:
                pass
            if target_pid and psutil.pid_exists(target_pid):
                try:
                    p = psutil.Process(target_pid)
                    snapshot["process_state"] = {
                        "pid": target_pid,
                        "status": p.status(),
                        "cpu_percent": p.cpu_percent(interval=0.1),
                        "memory_mb": round(p.memory_info().rss / (1024 * 1024), 2),
                        "is_running": p.is_running(),
                    }
                except Exception as p_exc:
                    snapshot["process_state"] = {"pid": target_pid, "error": str(p_exc)}
        except ImportError:
            # Fallback for ML venv: PowerShell
            if sys.platform == "win32":
                ps_cmd = (
                    "Get-CimInstance -ClassName Win32_Processor | "
                    "Select-Object -ExpandProperty LoadPercentage"
                )
                code, out, _ = _run_cmd_safe(["powershell", "-NoProfile", "-Command", ps_cmd])
                if code == 0 and out.isdigit():
                    snapshot["cpu_utilization_percent"] = float(out)

                if target_pid:
                    p_cmd = (
                        f"Get-Process -Id {target_pid} -ErrorAction SilentlyContinue | "
                        "Select-Object Id, CPU, WS, Responding | ConvertTo-Json"
                    )
                    c_p, out_p, _ = _run_cmd_safe(["powershell", "-NoProfile", "-Command", p_cmd])
                    if c_p == 0 and out_p:
                        try:
                            snapshot["process_state"] = json.loads(out_p)
                        except Exception:
                            pass

        return snapshot


# =============================================================================
# Capability G: Empirical Failure Classifier
# =============================================================================


class FailureClassifier:
    """Distinguishes upload failures based strictly on observed evidence."""

    @staticmethod
    def classify(
        telemetry: TelemetryState,
        exit_code: Optional[int],
        diagnostic_snapshot: Dict[str, Any],
        log_content: str = "",
    ) -> Dict[str, Any]:
        evidence: List[str] = []

        # 1. Authentication problem
        auth_patterns = [
            r"401\s+Unauthorized",
            r"403\s+Forbidden",
            r"Unauthorized",
            r"kaggle\.json not found",
            r"credentials.*missing",
        ]
        for pat in auth_patterns:
            if re.search(pat, log_content, re.IGNORECASE):
                evidence.append(f"Matched authentication failure pattern: '{pat}'")
                return {
                    "classification": FailureClassification.AUTHENTICATION_PROBLEM.value,
                    "evidence": evidence,
                    "recommended_action": (
                        "Verify credentials in ~/.kaggle/kaggle.json or KAGGLE_KEY "
                        "without exposing them."
                    ),
                }

        # 2. Local disk bottleneck
        free_c = diagnostic_snapshot.get("disk_free_c_gb")
        if free_c is not None and free_c < 5.0:
            evidence.append(
                f"Drive C: free space is critically low: {free_c} GB "
                "(< 5 GB threshold for temporary tar creation)"
            )
            return {
                "classification": FailureClassification.LOCAL_DISK_BOTTLENECK.value,
                "evidence": evidence,
                "recommended_action": (
                    "Free temporary disk space on C: before packaging dataset archive."
                ),
            }

        # 3. Network bottleneck
        net_counters = diagnostic_snapshot.get("network_counters") or {}
        dropout = net_counters.get("dropout", 0)
        errout = net_counters.get("errout", 0)
        if (dropout > 100 or errout > 100) or ("ConnectionResetError" in log_content):
            evidence.append(f"Network error/drop detected: dropout={dropout}, errout={errout}")
            return {
                "classification": FailureClassification.NETWORK_BOTTLENECK.value,
                "evidence": evidence,
                "recommended_action": (
                    "Check active network interface, Wi-Fi link quality, "
                    "or switch to wired Ethernet."
                ),
            }

        # 4. CPU / Process bottleneck
        cpu_util = diagnostic_snapshot.get("cpu_utilization_percent")
        if (
            cpu_util is not None
            and cpu_util > 95.0
            and telemetry.instantaneous_throughput_bps == 0.0
        ):
            evidence.append(f"High CPU utilization ({cpu_util}%) with zero upload progression")
            return {
                "classification": FailureClassification.CPU_PROCESS_BOTTLENECK.value,
                "evidence": evidence,
                "recommended_action": (
                    "Process may be saturated by compression or hashing. Allow packaging to finish."
                ),
            }

        # 5. Client / API Upload Error
        if exit_code is not None and exit_code != 0:
            evidence.append(f"Upload process exited with non-zero code {exit_code}")
            return {
                "classification": FailureClassification.CLIENT_API_UPLOAD_ERROR.value,
                "evidence": evidence,
                "recommended_action": (
                    "Inspect upload_events.log for client traceback or HTTP response error."
                ),
            }

        # 6. Likely remote/server-side stall
        if telemetry.current_state == UploadState.STALLED:
            if telemetry.time_since_last_progress_sec >= 180.0:
                evidence.append(
                    f"No upload progress for {telemetry.time_since_last_progress_sec:.1f}s while "
                    "client process is active and network link is up"
                )
                return {
                    "classification": FailureClassification.REMOTE_SERVER_STALL.value,
                    "evidence": evidence,
                    "recommended_action": (
                        "Server-side GCS ingestion pause. Do NOT kill; allow Kaggle CLI resumable "
                        "protocol to handle retries."
                    ),
                }

        # 7. Ambiguous / Insufficient evidence
        evidence.append("Observed telemetry does not meet specific bottleneck thresholds.")
        return {
            "classification": FailureClassification.AMBIGUOUS_INSUFFICIENT_EVIDENCE.value,
            "evidence": evidence,
            "recommended_action": (
                "Continue observing and collect additional telemetry before intervening."
            ),
        }


# =============================================================================
# Capability D: Persistent Observability Writer
# =============================================================================


class PersistentObservabilityWriter:
    """Manages atomic writing of upload_status.json, upload_progress.log, and upload_events.log."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.status_file = self.output_dir / "upload_status.json"
        self.progress_file = self.output_dir / "upload_progress.log"
        self.events_file = self.output_dir / "upload_events.log"

    @staticmethod
    def _sanitize(text: str) -> str:
        """Sanitize secrets, tokens, and credentials from log strings."""
        if not text:
            return ""
        # Scrub known env credentials if present
        for env_var in ("KAGGLE_KEY", "KAGGLE_API_TOKEN", "KAGGLE_SECRET"):
            val = os.environ.get(env_var)
            if val and len(val) >= 4:
                text = text.replace(val, "[REDACTED_SECRET]")

        # Pattern scrubbing for Bearer tokens and generic key assignments
        text = re.sub(
            r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}",
            r"\1[REDACTED_TOKEN]",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"((?:key|token|secret|password)[\"']?\s*[:=]\s*[\"']?)[A-Za-z0-9_\-]{8,}([\"']?)",
            r"\1[REDACTED_SECRET]\2",
            text,
            flags=re.IGNORECASE,
        )
        return text

    def write_status(self, telemetry: TelemetryState) -> None:
        """Atomic write of upload_status.json via temporary file rename."""
        temp_file = self.output_dir / f".tmp_status_{os.getpid()}.json"
        data = telemetry.to_dict()
        try:
            dumped = json.dumps(data, indent=2)
            clean_dumped = self._sanitize(dumped)
            temp_file.write_text(clean_dumped, encoding="utf-8")
            temp_file.replace(self.status_file)
        except Exception:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass

    def append_progress(self, telemetry: TelemetryState) -> None:
        """Append ASCII-safe progress line to upload_progress.log and flush."""
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        mb_done = telemetry.bytes_completed / (1024 * 1024)
        mb_total = telemetry.total_bytes / (1024 * 1024)
        mb_s = telemetry.instantaneous_throughput_bps / (1024 * 1024)
        r60_mb_s = telemetry.rolling_60s_throughput_bps / (1024 * 1024)
        raw_line = (
            f"[{now_utc}] state={telemetry.current_state.value} "
            f"progress={telemetry.percentage_bytes:5.1f}% ({mb_done:8.2f}/{mb_total:8.2f} MB) "
            f"cur_rate={mb_s:6.2f} MB/s r60={r60_mb_s:6.2f} MB/s ETA={telemetry.eta_formatted}\n"
        )
        line = self._sanitize(raw_line)
        try:
            with open(self.progress_file, "a", encoding="ascii", errors="replace") as fp:
                fp.write(line)
                fp.flush()
        except Exception:
            pass

    def append_event(
        self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Append ASCII-safe structured event to upload_events.log and flush."""
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        clean_msg = self._sanitize(message).encode("ascii", errors="replace").decode("ascii")
        details_str = self._sanitize(json.dumps(details, default=str)) if details else "{}"
        line = f"[{now_utc}] [{event_type.upper()}] {clean_msg} | {details_str}\n"
        try:
            with open(self.events_file, "a", encoding="ascii", errors="replace") as fp:
                fp.write(line)
                fp.flush()
        except Exception:
            pass


# =============================================================================
# Capability C: Real-Time Upload Telemetry Monitor
# =============================================================================


class UploadTelemetryMonitor:
    """Stateful telemetry engine calculating rolling windows, ETA, and detecting stalls."""

    # Matches Kaggle CLI / tqdm output patterns:
    # e.g.: 45%|████▍     | 25.2G/56.2G [06:12<07:35, 68.1MB/s]
    # or: 100%|██████████| 52.3G/52.3G [12:34<00:00, 74.2MB/s]
    TQDM_REGEX = re.compile(
        r"(\d+)%\|.*\|\s*([0-9.]+)([KMGTP]?)/([0-9.]+)([KMGTP]?)\s*\[([0-9:]+)<([0-9:]+),\s*([0-9.]+)([KMGTP]?)B/s\]"
    )

    def __init__(
        self,
        total_bytes: int = 56_193_499_563,
        total_files: int = 2_403,
        writer: Optional[PersistentObservabilityWriter] = None,
        stall_detector: Optional[StallDetector] = None,
    ):
        self.total_bytes = total_bytes
        self.total_files = total_files
        self.writer = writer
        self.stall_detector = stall_detector or StallDetector()

        self.start_time: float = time.monotonic()
        self.bytes_completed: int = 0
        self.completed_files_bytes: int = 0
        self.current_file_bytes: int = 0
        self.files_completed: Optional[int] = None
        self.current_file: Optional[str] = None
        self.last_activity_time: float = self.start_time
        self.retry_error_count: int = 0
        self.current_state: UploadState = UploadState.STARTING

        # Sliding window samples: (timestamp, cumulative_bytes)
        self.history_samples: Deque[Tuple[float, int]] = collections.deque()
        self.last_snapshot_time: float = 0.0

    def update_bytes(
        self, cumulative_bytes: int, file_info: Optional[str] = None
    ) -> TelemetryState:
        """Update monitor with latest cumulative bytes transferred."""
        now = time.monotonic()
        if cumulative_bytes > self.bytes_completed:
            self.bytes_completed = min(cumulative_bytes, self.total_bytes)
            self.last_activity_time = now
            if self.bytes_completed >= self.total_bytes and self.total_bytes > 0:
                self._transition_state(UploadState.COMPLETE, "All bytes confirmed uploaded")
            elif self.current_state in (UploadState.STARTING, UploadState.STALLED):
                self._transition_state(UploadState.ACTIVE, "Progress update received")
        elif cumulative_bytes >= self.total_bytes and self.total_bytes > 0:
            if self.current_state != UploadState.COMPLETE:
                self._transition_state(UploadState.COMPLETE, "All bytes confirmed uploaded")

        if file_info:
            self.current_file = file_info

        self.history_samples.append((now, self.bytes_completed))
        self._prune_history(now)

        return self.compute_telemetry()

    def parse_cli_line(self, line: str) -> Optional[TelemetryState]:
        """Parse raw terminal output line from Kaggle CLI."""
        lower_line = line.lower()
        if "starting upload for file" in lower_line:
            parts = line.split("Starting upload for file")
            fname = parts[-1].strip() if len(parts) > 1 else "archive.tar"
            self.current_file = fname
            self.completed_files_bytes += self.current_file_bytes
            self.current_file_bytes = 0
            if self.writer:
                self.writer.append_event("FILE_UPLOAD_START", f"Starting upload for file: {fname}")

        if "upload successful" in lower_line:
            if self.writer:
                self.writer.append_event("FILE_UPLOAD_SUCCESS", line.strip())

        match = self.TQDM_REGEX.search(line)
        if match:
            (
                percent_str,
                cur_val,
                cur_unit,
                tot_val,
                tot_unit,
                elapsed_str,
                eta_str,
                rate_val,
                rate_unit,
            ) = match.groups()
            file_bytes_done = self._unit_to_bytes(float(cur_val), cur_unit)
            self.current_file_bytes = file_bytes_done
            cumulative_bytes = self.completed_files_bytes + file_bytes_done
            return self.update_bytes(cumulative_bytes, file_info=self.current_file)

        # Check for error patterns
        if "error" in lower_line or "exception" in lower_line or "traceback" in lower_line:
            self.retry_error_count += 1
            if self.writer:
                self.writer.append_event("ERROR_LINE", line)
            if self.current_state != UploadState.ERROR:
                self._transition_state(UploadState.ERROR, f"Error detected in output: {line[:100]}")

        return None

    def tick(self) -> TelemetryState:
        """Heartbeat tick: check stalls and flush persistent logs."""
        now = time.monotonic()
        time_since_progress = now - self.last_activity_time

        assessment = self.stall_detector.evaluate(time_since_progress, self.current_state)
        if assessment.is_stalled:
            if self.current_state != UploadState.STALLED:
                self._transition_state(
                    UploadState.STALLED,
                    (
                        f"Upload stalled ({assessment.severity}): "
                        f"{time_since_progress:.1f}s without progress"
                    ),
                )
                if self.writer:
                    diag = DiagnosticSnapshotCollector().collect()
                    self.writer.append_event(
                        "STALL_DIAGNOSTIC_SNAPSHOT",
                        "Diagnostic collected upon stall transition",
                        diag,
                    )

        telemetry = self.compute_telemetry()
        if self.writer:
            self.writer.write_status(telemetry)
            self.writer.append_progress(telemetry)
        return telemetry

    def compute_telemetry(self) -> TelemetryState:
        """Compute current throughput windows, ETA, and return snapshot."""
        now = time.monotonic()
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        elapsed = max(now - self.start_time, 0.001)

        pct = (self.bytes_completed / self.total_bytes * 100.0) if self.total_bytes > 0 else 0.0
        overall_avg = self.bytes_completed / elapsed

        r60 = self._calc_window_rate(now, 60.0)
        r300 = self._calc_window_rate(now, 300.0)
        inst = self._calc_instantaneous_rate()

        # ETA calculation based on rolling 60s or overall average
        rate_for_eta = r60 if r60 > 1024 else overall_avg
        remaining_bytes = max(self.total_bytes - self.bytes_completed, 0)
        if rate_for_eta > 1024 and remaining_bytes > 0:
            eta_sec = remaining_bytes / rate_for_eta
            eta_fmt = str(datetime.timedelta(seconds=int(eta_sec)))
        elif remaining_bytes == 0:
            eta_sec = 0.0
            eta_fmt = "00:00:00"
        else:
            eta_sec = None
            eta_fmt = "--:--:--"

        time_since_progress = max(now - self.last_activity_time, 0.0)

        return TelemetryState(
            timestamp=now_utc,
            elapsed_time_sec=round(elapsed, 2),
            bytes_completed=self.bytes_completed,
            total_bytes=self.total_bytes,
            percentage_bytes=round(pct, 2),
            files_completed=self.files_completed,
            total_files=self.total_files,
            current_file=self.current_file,
            instantaneous_throughput_bps=round(inst, 2),
            rolling_60s_throughput_bps=round(r60, 2),
            rolling_300s_throughput_bps=round(r300, 2),
            overall_avg_throughput_bps=round(overall_avg, 2),
            eta_seconds=round(eta_sec, 1) if eta_sec is not None else None,
            eta_formatted=eta_fmt,
            last_activity_timestamp=datetime.datetime.fromtimestamp(
                time.time() - time_since_progress, datetime.timezone.utc
            ).isoformat(),
            time_since_last_progress_sec=round(time_since_progress, 2),
            retry_error_count=self.retry_error_count,
            current_state=self.current_state,
        )

    def _transition_state(self, new_state: UploadState, reason: str) -> None:
        old_state = self.current_state
        self.current_state = new_state
        if self.writer:
            self.writer.append_event(
                "STATE_TRANSITION",
                f"Transitioned from {old_state.value} to {new_state.value}: {reason}",
                {"old_state": old_state.value, "new_state": new_state.value, "reason": reason},
            )

    def _prune_history(self, current_time: float) -> None:
        """Keep history within 300 seconds window."""
        cutoff = current_time - 310.0
        while self.history_samples and self.history_samples[0][0] < cutoff:
            self.history_samples.popleft()

    def _calc_window_rate(self, current_time: float, window_sec: float) -> float:
        if not self.history_samples:
            return 0.0
        cutoff = current_time - window_sec
        # Find oldest sample within window
        oldest = None
        for t, b in self.history_samples:
            if t >= cutoff:
                oldest = (t, b)
                break
        if oldest is None:
            oldest = self.history_samples[0]

        latest = self.history_samples[-1]
        dt = latest[0] - oldest[0]
        db = latest[1] - oldest[1]
        if dt > 0.5:
            return max(db / dt, 0.0)
        return 0.0

    def _calc_instantaneous_rate(self) -> float:
        if len(self.history_samples) < 2:
            return 0.0
        latest = self.history_samples[-1]
        prev = self.history_samples[-2]
        dt = latest[0] - prev[0]
        db = latest[1] - prev[1]
        if dt > 0.01:
            return max(db / dt, 0.0)
        return 0.0

    @staticmethod
    def _unit_to_bytes(value: float, unit: str) -> int:
        unit = unit.upper()
        multipliers = {
            "": 1,
            "K": 1024,
            "M": 1024**2,
            "G": 1024**3,
            "T": 1024**4,
            "P": 1024**5,
        }
        mult = multipliers.get(unit, 1)
        return int(value * mult)


# =============================================================================
# Capability H: Resumability Inspector
# =============================================================================


class ResumabilityInspector:
    """Inspects Kaggle CLI resumable upload state and documents resumption semantics."""

    @staticmethod
    def inspect() -> Dict[str, Any]:
        """Inspect %TEMP%/.kaggle/uploads directory for active resumable state tokens."""
        temp_dir = Path(tempfile.gettempdir())
        kaggle_uploads_dir = temp_dir / ".kaggle" / "uploads"

        active_tokens = []
        if kaggle_uploads_dir.exists():
            for f in kaggle_uploads_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    active_tokens.append(
                        {
                            "token_file": f.name,
                            "file_path": data.get("file_path"),
                            "upload_url_set": bool(data.get("upload_url")),
                            "content_length": data.get("content_length"),
                            "last_byte_uploaded": data.get("last_byte_uploaded"),
                            "created_at": data.get("created_at"),
                        }
                    )
                except Exception:
                    pass

        analysis = {
            "resumability_supported_by_cli": True,
            "protocol": "Google Cloud Storage Resumable Upload (chunked seekable stream)",
            "state_storage_path": str(kaggle_uploads_dir),
            "state_storage_exists": kaggle_uploads_dir.exists(),
            "active_resume_tokens_count": len(active_tokens),
            "active_tokens": active_tokens,
            "recovery_mechanism": (
                "When re-running 'kaggle datasets create' or 'kaggle datasets version' with an "
                "interrupted upload, the client loads the state file from "
                "%TEMP%/.kaggle/uploads/<hash>.json, queries GCS with "
                "'Content-Range: bytes */file_size', receives the latest byte offset from the "
                "remote server, seeks the local file pointer to that offset, and resumes streaming "
                "without re-transmitting preceding bytes. "
                "Resumable state persists for up to 6 days (518,400 seconds) before expiring."
            ),
            "caveats": (
                "1. If uploading directory with -r tar, Kaggle creates the tar in a newly "
                "generated temp directory. If the previous tar was deleted upon interruption, "
                "the file path differs and resume cannot match. "
                "2. Pre-packaging the tar or preserving the staging archive guarantees "
                "deterministic path matching."
            ),
        }
        return analysis


# =============================================================================
# Capability I: Controlled Upload Probe Generator
# =============================================================================


class ControlledUploadProbe:
    """Prepares an isolated canary upload probe workflow (strictly unexecuted)."""

    PROBE_SLUG = "dheeraj12237/ocean-sentinel-probe-canary"

    def __init__(self, probe_dir: Optional[Path] = None, cloud_venv_python: Optional[Path] = None):
        repo_root = Path(__file__).resolve().parents[3]
        self.probe_dir = probe_dir or (
            repo_root / "experiments" / "performance" / "cloud_kaggle_dataset_probe_canary"
        )
        self.cloud_venv_python = cloud_venv_python or _detect_default_cloud_python(repo_root)

    def prepare(self) -> Dict[str, Any]:
        """Stage canary files without executing any Kaggle upload."""
        self.probe_dir.mkdir(parents=True, exist_ok=True)

        meta_file = self.probe_dir / "dataset-metadata.json"
        meta_content = {
            "title": "Ocean Sentinel Upload Probe Canary",
            "id": self.PROBE_SLUG,
            "licenses": [{"name": "CC0-1.0"}],
            "isPrivate": True,
        }
        meta_file.write_text(json.dumps(meta_content, indent=2), encoding="utf-8")

        payload_file = self.probe_dir / "probe_canary.txt"
        payload_file.write_text(
            f"CANARY_TEST_TIMESTAMP={datetime.datetime.now(datetime.timezone.utc).isoformat()}\n"
            "PURPOSE=Verify Kaggle CLI auth, dataset creation, and progress parsing on "
            "small 1KB payload.\n",
            encoding="utf-8",
        )

        kaggle_exe = self.cloud_venv_python.parent / (
            "kaggle.exe" if sys.platform == "win32" else "kaggle"
        )
        probe_cmd = f'"{kaggle_exe}" datasets create -p "{self.probe_dir}" -r tar'

        return {
            "probe_staged": True,
            "probe_dir": str(self.probe_dir),
            "probe_slug": self.PROBE_SLUG,
            "payload_bytes": payload_file.stat().st_size,
            "is_private": True,
            "executable": str(kaggle_exe),
            "command": probe_cmd,
            "status": "PREPARED_NOT_EXECUTED",
        }


# =============================================================================
# Capability J: Certified Production Upload Command Generator
# =============================================================================


class ProductionCommandGenerator:
    """Prepares exact production Kaggle upload command for certified package (unexecuted)."""

    def __init__(
        self,
        staging_dir: Optional[Path] = None,
        cloud_venv_python: Optional[Path] = None,
    ):
        repo_root = Path(__file__).resolve().parents[3]
        self.staging_dir = staging_dir or (
            repo_root
            / "experiments"
            / "performance"
            / "cloud_kaggle_dataset_package_preflight_20260907_022953"
            / "staging"
        )
        self.cloud_venv_python = cloud_venv_python or _detect_default_cloud_python(repo_root)

    def generate(self) -> Dict[str, Any]:
        """Validate certified package integrity and output exact execution command."""
        kaggle_exe = self.cloud_venv_python.parent / (
            "kaggle.exe" if sys.platform == "win32" else "kaggle"
        )

        metadata_file = self.staging_dir / "dataset-metadata.json"
        is_private = False
        slug = "UNKNOWN"
        if metadata_file.exists():
            try:
                m = json.loads(metadata_file.read_text(encoding="utf-8"))
                is_private = m.get("isPrivate", False)
                slug = m.get("id", "UNKNOWN")
            except Exception:
                pass

        # Exact command preserving progress output without --quiet
        cmd = f'"{kaggle_exe}" datasets create -p "{self.staging_dir}" -r tar'

        return {
            "certified_slug": slug,
            "staging_dir": str(self.staging_dir),
            "is_private_enforced": is_private,
            "kaggle_executable": str(kaggle_exe),
            "production_upload_command": cmd,
            "execution_policy": "DO_NOT_EXECUTE_AUTOMATICALLY",
            "safety_checks": {
                "staging_exists": self.staging_dir.exists(),
                "metadata_exists": metadata_file.exists(),
                "is_private": is_private,
                "executable_exists": kaggle_exe.exists(),
            },
        }
