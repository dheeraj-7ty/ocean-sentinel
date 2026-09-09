"""Unit and integration tests for Ocean Sentinel Gate 4.2 Upload Operations Harness.

Verifies:
1. Preflight collector field completeness and strict zero-credential exposure.
2. Network baseline benchmarking and uncertainty documentation.
3. Upload telemetry monitor state transitions, rolling throughput windows, and ETA.
4. Kaggle CLI output parsing (tqdm style).
5. Configurable stall detection thresholds and severity levels.
6. Non-secret diagnostic snapshot collection.
7. 7-class empirical failure classification.
8. Persistent observability writer (atomic JSON, ASCII-safe progress/events logs).
9. Resumability inspection and GCS resume token discovery.
10. Controlled upload probe generation (strictly unexecuted).
11. Production upload command generator safety and execution policy.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ocean_sentinel.cloud.upload_harness import (
    ControlledUploadProbe,
    FailureClassification,
    FailureClassifier,
    NetworkBaselineBenchmarker,
    PersistentObservabilityWriter,
    PreflightCollector,
    ProductionCommandGenerator,
    ResumabilityInspector,
    StallDetector,
    TelemetryState,
    UploadState,
    UploadTelemetryMonitor,
)

# =============================================================================
# 1. Preflight Collector Tests
# =============================================================================


class TestPreflightCollector:
    """Verify preflight metrics collection and credential safety."""

    def test_preflight_field_completeness(self, tmp_path: Path):
        collector = PreflightCollector(repo_root=tmp_path, staging_dir=tmp_path / "staging")
        record = collector.collect()

        required_keys = [
            "timestamp",
            "git_branch",
            "git_commit",
            "git_status",
            "git_dirty_files_count",
            "dataset_staging_path",
            "exact_total_byte_count",
            "exact_file_count",
            "image_count",
            "mask_count",
            "manifest_root_sha256",
            "kaggle_dataset_slug",
            "kaggle_cli_version",
            "python_executable",
            "cloud_venv_valid",
            "authentication_state",
            "local_disk_free_space",
            "source_volume_filesystem",
            "active_network_adapter",
            "negotiated_link_speed",
            "current_network_connectivity",
            "upload_benchmark_result",
            "system_power_state",
        ]
        for key in required_keys:
            assert key in record, f"Missing required preflight field: {key}"

    def test_auth_state_strictly_set_or_not_set(self):
        collector = PreflightCollector()
        auth_state = collector._get_auth_state()
        assert auth_state in ("SET", "NOT SET"), f"Invalid auth state representation: {auth_state}"

    def test_no_credentials_exposed_in_preflight_dump(self, monkeypatch):
        # Inject fake secret environment variables
        fake_secret = "SECRET_SUPER_CONFIDENTIAL_KEY_99999"
        monkeypatch.setenv("KAGGLE_KEY", fake_secret)
        monkeypatch.setenv("KAGGLE_USERNAME", "test_user")

        collector = PreflightCollector()
        record = collector.collect()

        dumped = json.dumps(record)
        assert fake_secret not in dumped, (
            "Security violation: Secret credential leaked into preflight dump!"
        )
        assert record["authentication_state"] == "SET"

    def test_staging_metrics_synthetic(self, tmp_path: Path):
        staging = tmp_path / "staging"
        img_dir = staging / "images"
        mask_dir = staging / "masks"
        manifest_dir = staging / "manifest"
        img_dir.mkdir(parents=True)
        mask_dir.mkdir(parents=True)
        manifest_dir.mkdir(parents=True)

        (img_dir / "00000.tif").write_bytes(b"A" * 100)
        (img_dir / "00001.tif").write_bytes(b"B" * 200)
        (mask_dir / "00000.tif").write_bytes(b"C" * 50)
        (manifest_dir / "integrity_manifest.json").write_text(
            json.dumps({"root_sha256": "abcdef123456"}), encoding="utf-8"
        )
        (staging / "dataset-metadata.json").write_text(
            json.dumps({"id": "dheeraj12237/ocean-sentinel-trujillo-corpus", "isPrivate": True}),
            encoding="utf-8",
        )

        collector = PreflightCollector(staging_dir=staging)
        metrics = collector._get_staging_metrics()
        assert metrics["total_file_count"] == 5
        assert metrics["image_count"] == 2
        assert metrics["mask_count"] == 1
        assert metrics["root_sha256"] == "abcdef123456"
        assert metrics["dataset_slug"] == "dheeraj12237/ocean-sentinel-trujillo-corpus"


# =============================================================================
# 2. Network Baseline Benchmarker Tests
# =============================================================================


class TestNetworkBaselineBenchmarker:
    """Verify controlled upload benchmark and uncertainty bounds."""

    def test_benchmark_contains_uncertainty_disclaimer(self):
        benchmarker = NetworkBaselineBenchmarker()
        assert len(benchmarker.UNCERTAINTY_DISCLAIMER) > 50
        assert "Google Cloud Storage" in benchmarker.UNCERTAINTY_DISCLAIMER

    @patch("requests.post")
    def test_benchmark_successful_measurement(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        benchmarker = NetworkBaselineBenchmarker()
        res = benchmarker.measure(endpoint="https://httpbin.org/post", payload_size_bytes=1048576)

        assert res["success"] is True
        assert res["bytes_sent"] == 1048576
        assert res["measured_throughput_mb_s"] >= 0.0
        assert "Google Cloud Storage" in res["limitations_and_uncertainty"]

    @patch("requests.post", side_effect=Exception("Connection refused"))
    def test_benchmark_graceful_failure(self, mock_post):
        benchmarker = NetworkBaselineBenchmarker()
        res = benchmarker.measure(endpoint="https://bad.invalid/post", payload_size_bytes=1024)
        assert res["success"] is False
        assert "Connection refused" in res["error"]
        assert res["measured_throughput_mb_s"] == 0.0


# =============================================================================
# 3. Telemetry Monitor & Rolling Throughput Tests
# =============================================================================


class TestUploadTelemetryMonitor:
    """Verify telemetry state, rolling calculations, and CLI line parsing."""

    def test_initial_state_starting(self):
        monitor = UploadTelemetryMonitor(total_bytes=1000, total_files=10)
        telemetry = monitor.compute_telemetry()
        assert telemetry.current_state == UploadState.STARTING
        assert telemetry.bytes_completed == 0
        assert telemetry.percentage_bytes == 0.0

    def test_progress_advancement_and_completion(self):
        monitor = UploadTelemetryMonitor(total_bytes=1000, total_files=10)
        t1 = monitor.update_bytes(500)
        assert t1.current_state == UploadState.ACTIVE
        assert t1.bytes_completed == 500
        assert t1.percentage_bytes == 50.0

        t2 = monitor.update_bytes(1000)
        assert t2.current_state == UploadState.COMPLETE
        assert t2.percentage_bytes == 100.0

    def test_rolling_windows_calculation(self):
        monitor = UploadTelemetryMonitor(total_bytes=100_000_000)
        # Feed two samples spaced in time
        t_base = time.monotonic()
        monitor.history_samples.append((t_base - 10.0, 0))
        monitor.history_samples.append((t_base, 10_000_000))
        monitor.bytes_completed = 10_000_000

        r60 = monitor._calc_window_rate(t_base, 60.0)
        # 10 MB in 10 s = 1 MB/s = 1,000,000 B/s
        assert pytest.approx(r60, rel=1e-2) == 1_000_000.0

    def test_parse_tqdm_cli_line(self):
        monitor = UploadTelemetryMonitor(total_bytes=56_193_499_563)
        line = " 45%|████▍     | 25.2G/56.2G [06:12<07:35, 68.1MB/s]"
        telemetry = monitor.parse_cli_line(line)
        assert telemetry is not None
        assert telemetry.bytes_completed == int(25.2 * (1024**3))
        assert telemetry.current_state == UploadState.ACTIVE

    def test_parse_cli_line_error_transition(self):
        monitor = UploadTelemetryMonitor(total_bytes=1000)
        monitor.parse_cli_line("Traceback (most recent call last): 401 Unauthorized")
        assert monitor.retry_error_count == 1
        assert monitor.current_state == UploadState.ERROR


# =============================================================================
# 4. Stall Detection Tests
# =============================================================================


class TestStallDetector:
    """Verify configurable stall detection without false positives."""

    def test_no_stall_within_healthy_window(self):
        detector = StallDetector(warning_threshold_sec=60.0, critical_stall_threshold_sec=180.0)
        assessment = detector.evaluate(15.0, UploadState.ACTIVE)
        assert assessment.is_stalled is False
        assert assessment.severity == "NONE"

    def test_warning_stall_threshold(self):
        detector = StallDetector(warning_threshold_sec=60.0, critical_stall_threshold_sec=180.0)
        assessment = detector.evaluate(75.0, UploadState.ACTIVE)
        assert assessment.is_stalled is True
        assert assessment.severity == "WARNING"

    def test_critical_stall_threshold(self):
        detector = StallDetector(warning_threshold_sec=60.0, critical_stall_threshold_sec=180.0)
        assessment = detector.evaluate(195.0, UploadState.ACTIVE)
        assert assessment.is_stalled is True
        assert assessment.severity == "CRITICAL"
        assert "DO_NOT_KILL" in assessment.action_recommended

    def test_completed_upload_never_stalled(self):
        detector = StallDetector(warning_threshold_sec=60.0, critical_stall_threshold_sec=180.0)
        assessment = detector.evaluate(300.0, UploadState.COMPLETE)
        assert assessment.is_stalled is False
        assert assessment.severity == "NONE"


# =============================================================================
# 5. Persistent Observability Writer Tests
# =============================================================================


class TestPersistentObservabilityWriter:
    """Verify atomic writing, log appending, and ASCII safety."""

    def test_atomic_status_write(self, tmp_path: Path):
        writer = PersistentObservabilityWriter(tmp_path)
        telemetry = TelemetryState(
            timestamp="2026-09-07T12:00:00Z",
            elapsed_time_sec=10.0,
            bytes_completed=1024,
            total_bytes=2048,
            percentage_bytes=50.0,
            files_completed=1,
            total_files=2,
            current_file="00000.tif",
            instantaneous_throughput_bps=102.4,
            rolling_60s_throughput_bps=102.4,
            rolling_300s_throughput_bps=102.4,
            overall_avg_throughput_bps=102.4,
            eta_seconds=10.0,
            eta_formatted="00:00:10",
            last_activity_timestamp="2026-09-07T12:00:00Z",
            time_since_last_progress_sec=0.0,
            retry_error_count=0,
            current_state=UploadState.ACTIVE,
        )
        writer.write_status(telemetry)

        assert writer.status_file.exists()
        data = json.loads(writer.status_file.read_text(encoding="utf-8"))
        assert data["bytes_completed"] == 1024
        assert data["current_state"] == "ACTIVE"

    def test_ascii_safe_logging(self, tmp_path: Path):
        writer = PersistentObservabilityWriter(tmp_path)
        # Non-ASCII characters should be safely handled
        unicode_message = "Non-ASCII characters: █ 🚀 警告 tested safely"
        writer.append_event("TEST_EVENT", unicode_message)

        assert writer.events_file.exists()
        raw_bytes = writer.events_file.read_bytes()
        # Verify valid ASCII
        raw_bytes.decode("ascii")


# =============================================================================
# 6. Failure Classifier Tests
# =============================================================================


class TestFailureClassifier:
    """Verify 7-class failure taxonomy."""

    def test_classify_auth_problem(self):
        telemetry = TelemetryState(
            timestamp="",
            elapsed_time_sec=1.0,
            bytes_completed=0,
            total_bytes=100,
            percentage_bytes=0.0,
            files_completed=0,
            total_files=1,
            current_file=None,
            instantaneous_throughput_bps=0.0,
            rolling_60s_throughput_bps=0.0,
            rolling_300s_throughput_bps=0.0,
            overall_avg_throughput_bps=0.0,
            eta_seconds=None,
            eta_formatted="--:--:--",
            last_activity_timestamp="",
            time_since_last_progress_sec=1.0,
            retry_error_count=1,
            current_state=UploadState.ERROR,
        )
        res = FailureClassifier.classify(
            telemetry=telemetry,
            exit_code=1,
            diagnostic_snapshot={},
            log_content="kaggle.rest.ApiException: (401) Unauthorized",
        )
        assert res["classification"] == FailureClassification.AUTHENTICATION_PROBLEM.value

    def test_classify_disk_bottleneck(self):
        telemetry = TelemetryState(
            timestamp="",
            elapsed_time_sec=10.0,
            bytes_completed=0,
            total_bytes=100,
            percentage_bytes=0.0,
            files_completed=0,
            total_files=1,
            current_file=None,
            instantaneous_throughput_bps=0.0,
            rolling_60s_throughput_bps=0.0,
            rolling_300s_throughput_bps=0.0,
            overall_avg_throughput_bps=0.0,
            eta_seconds=None,
            eta_formatted="--:--:--",
            last_activity_timestamp="",
            time_since_last_progress_sec=5.0,
            retry_error_count=0,
            current_state=UploadState.ACTIVE,
        )
        res = FailureClassifier.classify(
            telemetry=telemetry,
            exit_code=None,
            diagnostic_snapshot={"disk_free_c_gb": 2.1},
            log_content="",
        )
        assert res["classification"] == FailureClassification.LOCAL_DISK_BOTTLENECK.value

    def test_classify_remote_server_stall(self):
        telemetry = TelemetryState(
            timestamp="",
            elapsed_time_sec=250.0,
            bytes_completed=500,
            total_bytes=1000,
            percentage_bytes=50.0,
            files_completed=0,
            total_files=1,
            current_file=None,
            instantaneous_throughput_bps=0.0,
            rolling_60s_throughput_bps=0.0,
            rolling_300s_throughput_bps=0.0,
            overall_avg_throughput_bps=2.0,
            eta_seconds=None,
            eta_formatted="--:--:--",
            last_activity_timestamp="",
            time_since_last_progress_sec=190.0,
            retry_error_count=0,
            current_state=UploadState.STALLED,
        )
        res = FailureClassifier.classify(
            telemetry=telemetry,
            exit_code=None,
            diagnostic_snapshot={
                "disk_free_c_gb": 50.0,
                "network_counters": {"dropout": 0, "errout": 0},
            },
            log_content="",
        )
        assert res["classification"] == FailureClassification.REMOTE_SERVER_STALL.value


# =============================================================================
# 7. Resumability Inspector Tests
# =============================================================================


class TestResumabilityInspector:
    """Verify inspection of GCS resumable state tokens."""

    def test_resumability_structure_and_mechanism(self):
        res = ResumabilityInspector.inspect()
        assert res["resumability_supported_by_cli"] is True
        assert "Google Cloud Storage" in res["protocol"]
        assert "Content-Range" in res["recovery_mechanism"]
        assert "-r tar" in res["caveats"]


# =============================================================================
# 8. Probe and Production Command Generator Safety Tests
# =============================================================================


class TestProbeAndProductionGenerators:
    """Verify probe staging and production upload command generation without execution."""

    def test_controlled_upload_probe_prepared_not_executed(self, tmp_path: Path):
        probe_dir = tmp_path / "canary_probe"
        probe = ControlledUploadProbe(probe_dir=probe_dir)
        res = probe.prepare()

        assert res["status"] == "PREPARED_NOT_EXECUTED"
        assert res["is_private"] is True
        assert probe_dir.exists()
        meta = json.loads((probe_dir / "dataset-metadata.json").read_text(encoding="utf-8"))
        assert meta["isPrivate"] is True
        assert "datasets create" in res["command"]

    def test_production_upload_command_generator_safety(self, tmp_path: Path):
        staging = tmp_path / "staging"
        staging.mkdir(parents=True)
        (staging / "dataset-metadata.json").write_text(
            json.dumps({"id": "dheeraj12237/ocean-sentinel-trujillo-corpus", "isPrivate": True}),
            encoding="utf-8",
        )

        gen = ProductionCommandGenerator(staging_dir=staging)
        res = gen.generate()

        assert res["execution_policy"] == "DO_NOT_EXECUTE_AUTOMATICALLY"
        assert res["is_private_enforced"] is True
        assert res["certified_slug"] == "dheeraj12237/ocean-sentinel-trujillo-corpus"
        assert "datasets create" in res["production_upload_command"]
        assert "-r tar" in res["production_upload_command"]
        assert "--quiet" not in res["production_upload_command"]


# =============================================================================
# 9. Adversarial Telemetry Scenarios Tests (Mandatory 13 Cases)
# =============================================================================


class TestAdversarialTelemetryScenarios:
    """Rigorous verification of upload telemetry against 13 adversarial streaming conditions."""

    def test_scenario_01_steady_progress(self, tmp_path: Path):
        writer = PersistentObservabilityWriter(tmp_path)
        monitor = UploadTelemetryMonitor(total_bytes=100_000, writer=writer)

        for i in range(1, 6):
            telemetry = monitor.update_bytes(i * 20_000)
            monitor.tick()
            assert telemetry.current_state in (UploadState.ACTIVE, UploadState.COMPLETE)
            assert telemetry.bytes_completed == i * 20_000

        assert monitor.bytes_completed == 100_000
        assert monitor.current_state == UploadState.COMPLETE

    def test_scenario_02_very_fast_progress(self):
        monitor = UploadTelemetryMonitor(total_bytes=1_000_000_000)
        # 500 MB in single leap
        t1 = monitor.update_bytes(500_000_000)
        assert t1.current_state == UploadState.ACTIVE
        assert t1.percentage_bytes == 50.0
        assert t1.bytes_completed == 500_000_000

    def test_scenario_03_slow_progress(self):
        monitor = UploadTelemetryMonitor(total_bytes=10_000_000)
        # 10 bytes transferred
        t1 = monitor.update_bytes(10)
        assert t1.current_state == UploadState.ACTIVE
        assert t1.bytes_completed == 10
        assert t1.eta_seconds is not None

    def test_scenario_04_temporary_zero_progress(self):
        monitor = UploadTelemetryMonitor(total_bytes=1000)
        monitor.update_bytes(100)
        assert monitor.current_state == UploadState.ACTIVE

        # Advance clock by 15s (healthy window < 60s)
        monitor.last_activity_time = time.monotonic() - 15.0
        telemetry = monitor.tick()
        assert telemetry.current_state == UploadState.ACTIVE
        assert telemetry.time_since_last_progress_sec >= 14.0

    def test_scenario_05_warning_stall(self):
        detector = StallDetector(warning_threshold_sec=60.0, critical_stall_threshold_sec=180.0)
        monitor = UploadTelemetryMonitor(total_bytes=1000, stall_detector=detector)
        monitor.update_bytes(200)

        # Inactive for 75s
        monitor.last_activity_time = time.monotonic() - 75.0
        telemetry = monitor.tick()
        assert telemetry.current_state == UploadState.STALLED

    def test_scenario_06_critical_stall(self):
        detector = StallDetector(warning_threshold_sec=60.0, critical_stall_threshold_sec=180.0)
        monitor = UploadTelemetryMonitor(total_bytes=1000, stall_detector=detector)
        monitor.update_bytes(200)

        # Inactive for 200s
        monitor.last_activity_time = time.monotonic() - 200.0
        telemetry = monitor.tick()
        assert telemetry.current_state == UploadState.STALLED
        assessment = detector.evaluate(200.0, UploadState.STALLED)
        assert assessment.severity == "CRITICAL"
        assert "DO_NOT_KILL" in assessment.action_recommended

    def test_scenario_07_recovery_after_stall(self):
        detector = StallDetector(warning_threshold_sec=60.0, critical_stall_threshold_sec=180.0)
        monitor = UploadTelemetryMonitor(total_bytes=1000, stall_detector=detector)
        monitor.update_bytes(200)

        # Force into stall
        monitor.last_activity_time = time.monotonic() - 100.0
        monitor.tick()
        assert monitor.current_state == UploadState.STALLED

        # Recover with new byte progress
        telemetry = monitor.update_bytes(400)
        assert telemetry.current_state == UploadState.ACTIVE
        assert telemetry.bytes_completed == 400

    def test_scenario_08_repeated_retry_error(self):
        monitor = UploadTelemetryMonitor(total_bytes=1000)
        for i in range(5):
            monitor.parse_cli_line(f"ConnectionResetError: Retrying upload chunk {i+1}...")
        assert monitor.retry_error_count == 5
        assert monitor.current_state == UploadState.ERROR

    def test_scenario_09_malformed_tqdm_line(self):
        monitor = UploadTelemetryMonitor(total_bytes=1000)
        # Random corrupt / partial lines
        bad_lines = [
            "",
            "??? % | garbled bytes ###",
            "12/invalid [00:??<--:--, ??B/s]",
            "Upload: [########] 12% missing brackets",
        ]
        for line in bad_lines:
            res = monitor.parse_cli_line(line)
            assert res is None or isinstance(res, TelemetryState)
        assert monitor.bytes_completed == 0

    def test_scenario_10_missing_progress_output(self):
        detector = StallDetector(warning_threshold_sec=10.0, critical_stall_threshold_sec=30.0)
        monitor = UploadTelemetryMonitor(total_bytes=1000, stall_detector=detector)
        monitor.update_bytes(100)

        # No lines parsed for 15 seconds
        monitor.last_activity_time = time.monotonic() - 15.0
        telemetry = monitor.tick()
        assert telemetry.current_state == UploadState.STALLED

    def test_scenario_11_process_termination_without_full_bytes(self):
        monitor = UploadTelemetryMonitor(total_bytes=1000)
        telemetry = monitor.update_bytes(500)
        # Process exits prematurely
        assert monitor.current_state != UploadState.COMPLETE
        assert monitor.bytes_completed == 500
        assert telemetry.percentage_bytes == 50.0

    def test_scenario_12_clean_completion(self, tmp_path: Path):
        writer = PersistentObservabilityWriter(tmp_path)
        monitor = UploadTelemetryMonitor(total_bytes=1000, writer=writer)
        telemetry = monitor.update_bytes(1000)
        monitor.tick()

        assert telemetry.current_state == UploadState.COMPLETE
        assert telemetry.percentage_bytes == 100.0
        assert telemetry.bytes_completed == 1000
        assert writer.status_file.exists()
        status_data = json.loads(writer.status_file.read_text(encoding="utf-8"))
        assert status_data["current_state"] == "COMPLETE"

    def test_scenario_13_incomplete_process_with_misleading_final_output(self):
        monitor = UploadTelemetryMonitor(total_bytes=50_000_000_000)
        monitor.update_bytes(1_000)
        # Parse output line that might look like completion but bytes incomplete
        monitor.parse_cli_line("Your private Dataset is being created.")
        assert monitor.current_state != UploadState.COMPLETE
        assert monitor.bytes_completed < monitor.total_bytes

    def test_scenario_14_monitor_disappearance_and_restart_independence(self, tmp_path: Path):
        """Phase 10 & 11: Prove MONITOR FAILURE != UPLOAD FAILURE in a synthetic environment."""
        import subprocess
        import sys

        log_file = tmp_path / "synthetic_upload.log"
        out_dir = tmp_path / "telemetry"

        # 1. Start a fake upload process emitting tqdm progress over time to log_file
        uploader_code = (
            "import time, sys\n"
            "with open(sys.argv[1], 'w', buffering=1, encoding='utf-8') as f:\n"
            "    for i in range(1, 11):\n"
            "        mb = i * 10\n"
            "        f.write(f'{i*10}%|████| {mb}.0M/100.0M [00:0{i}<00:0{10-i}, 10.0MB/s]\\n')\n"
            "        time.sleep(0.3)\n"
            "    f.write('Your private Dataset is being created.\\n')\n"
        )
        uploader = subprocess.Popen([sys.executable, "-c", uploader_code, str(log_file)])

        # 2. Wait until log exists and initial progress is written
        time.sleep(0.6)
        assert uploader.poll() is None, "Fake uploader died prematurely"

        # 3. Start telemetry monitor pointing to log file
        monitor_script = Path(__file__).resolve().parents[1] / "scripts" / "gate4_upload_harness.py"
        mon_proc1 = subprocess.Popen(
            [
                sys.executable,
                str(monitor_script),
                "monitor",
                "--log-file",
                str(log_file),
                "--output-dir",
                str(out_dir),
                "--total-bytes",
                str(100 * 1024 * 1024),
                "--exit-on-idle",
                "5.0",
            ]
        )

        time.sleep(1.5)
        # 4. Confirm monitor recorded progress
        status_file = out_dir / "upload_status.json"
        assert status_file.exists(), "Monitor failed to write initial status"
        s1 = json.loads(status_file.read_text(encoding="utf-8"))
        assert s1["bytes_completed"] >= 0

        # 5. Terminate only the monitor
        mon_proc1.kill()
        mon_proc1.wait()

        # 6. Verify fake upload process was NOT terminated by monitor shutdown
        assert uploader.poll() is None, "Violation: Monitor shutdown terminated the uploader!"

        # 7. Restart monitor
        mon_proc2 = subprocess.Popen(
            [
                sys.executable,
                str(monitor_script),
                "monitor",
                "--log-file",
                str(log_file),
                "--output-dir",
                str(out_dir),
                "--total-bytes",
                str(100 * 1024 * 1024),
                "--exit-on-idle",
                "2.0",
            ]
        )

        # 8. Wait for uploader to finish
        uploader.wait(timeout=10.0)
        assert uploader.returncode == 0, "Uploader did not finish cleanly"

        # Wait for monitor to catch up and exit
        mon_proc2.wait(timeout=10.0)

        # 9. Verify persistent state/logs remain usable and uncorrupted
        assert status_file.exists()
        s2 = json.loads(status_file.read_text(encoding="utf-8"))
        assert s2["bytes_completed"] == 100 * 1024 * 1024
        assert s2["percentage_bytes"] == 100.0
        assert s2["current_state"] == "COMPLETE"

        events_file = out_dir / "upload_events.log"
        assert events_file.exists()
        assert len(events_file.read_text(encoding="ascii")) > 0

    def test_scenario_15_credential_sanitization_in_events_and_progress(self, tmp_path: Path):
        """Phase 11: Verify zero credentials can enter logs or status files."""
        writer = PersistentObservabilityWriter(tmp_path)
        secret_key = "SECRET_SUPER_KAGGLE_KEY_99999"

        with patch.dict("os.environ", {"KAGGLE_KEY": secret_key}):
            writer.append_event(
                "TEST_EVENT",
                f"Error with key={secret_key} and Bearer abcdef1234567890",
                {"details": f"secret={secret_key}"},
            )
            monitor = UploadTelemetryMonitor(total_bytes=1000, writer=writer)
            monitor.update_bytes(100)
            monitor.tick()

        events_text = (tmp_path / "upload_events.log").read_text(encoding="utf-8")
        status_text = (tmp_path / "upload_status.json").read_text(encoding="utf-8")
        progress_text = (tmp_path / "upload_progress.log").read_text(encoding="utf-8")

        for text, fname in [
            (events_text, "events.log"),
            (status_text, "status.json"),
            (progress_text, "progress.log"),
        ]:
            assert secret_key not in text, f"Security leak: secret found in {fname}"
            assert "abcdef1234567890" not in text, f"Security leak: token found in {fname}"

    def test_scenario_16_eta_unknown_when_evidence_insufficient(self):
        """Phase 11: Verify ETA becomes UNKNOWN (--:--:--) when evidence is insufficient."""
        monitor = UploadTelemetryMonitor(total_bytes=1000)
        telemetry = monitor.compute_telemetry()
        assert telemetry.eta_formatted == "--:--:--"
        assert telemetry.eta_seconds is None

    def test_scenario_17_gate4_simulation_default_output_path_isolation(self):
        """Verify Gate 4 simulation default output directory isolates to temp/ and not experiments/."""
        import argparse
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "gate4_upload_harness",
            Path(__file__).resolve().parent.parent / "scripts" / "gate4_upload_harness.py",
        )
        assert spec is not None and spec.loader is not None
        gate4_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate4_mod)

        mock_t = MagicMock()
        mock_t.instantaneous_throughput_bps = 10.0 * (1024**2)
        mock_t.percentage_bytes = 40.0
        mock_t.current_state = UploadState.ACTIVE
        mock_t.time_since_last_progress_sec = 2.0
        mock_t.eta_formatted = "00:01:00"

        with patch.object(gate4_mod, "PersistentObservabilityWriter") as mock_writer, \
             patch.object(gate4_mod, "UploadTelemetryMonitor") as mock_monitor, \
             patch.object(gate4_mod.time, "sleep"):
            mock_monitor.return_value.update_bytes.return_value = mock_t
            mock_monitor.return_value.tick.return_value = mock_t
            args = argparse.Namespace(output_dir=None)
            ret = gate4_mod.cmd_simulate(args)
            assert ret == 0
            mock_writer.assert_called_once()
            called_out_dir = mock_writer.call_args[0][0]
            assert isinstance(called_out_dir, Path)
            assert called_out_dir == gate4_mod.REPO_ROOT / "temp" / "synthetic_upload_telemetry_test"
            assert "experiments" not in called_out_dir.parts



