# Ocean Sentinel — Gate 4.2R Production Upload Operational Runbook

**Document Version**: 2.0.0 (Gate 4.2R Qualified)  
**Target Dataset**: `dheeraj12237/ocean-sentinel-trujillo-corpus` (~56.19 GB, 2,403 files)  
**Package Staging Directory**: `D:\Projects\ocean-sentinel\experiments\performance\cloud_kaggle_dataset_package_preflight_20260907_022953\staging`  
**Manifest Root SHA-256**: `e6e342d3c47aeed896283b31d7218d220bd465792d4d1f5d83485cc872b5c453`  
**Target Environment**: Verified Dedicated Cloud Tools Environment (`D:\Tools\cloud-tools`)  
**Kaggle CLI Binary**: `D:\Tools\cloud-tools\Scripts\kaggle.exe` (Version: `Kaggle CLI 2.2.4`)  
**Auth Source**: `C:\Users\Dheeraj\.kaggle\credentials.json` (OAuth verified)  

---

## 1. Preflight Verification Checklist

Before launching the production upload, execute the preflight check:

```powershell
"D:\Tools\cloud-tools\Scripts\python.exe" scripts/gate4_upload_harness.py preflight -o experiments/performance/gate4_2_pre_upload_operations_20260907_193000/preflight.json
```

### Required Checklist Items:
- [ ] **Power State**: Must show `AC=Online` (never upload 56 GB on battery power).
- [ ] **Sleep Timeout**: Must show `0x00000000` (disabled while on AC power).
- [ ] **Drive C: Headroom**: Must have `>= 60 GB free` for temporary tarball packaging (`current: > 165 GB`).
- [ ] **Drive D: Free Space**: Must have `>= 50 GB free` (`current: > 388 GB`).
- [ ] **Authentication**: Must show `Authentication State: SET`.
- [ ] **Kaggle CLI Version**: Must show `Kaggle CLI 2.2.4`.
- [ ] **Corpus Root Hash**: Must show `e6e342d3c47aeed896283b31d7218d220bd465792d4d1f5d83485cc872b5c453`.
- [ ] **Network Reachability**: `kaggle.com` and `storage.googleapis.com` must show `UP`.

---

## 2. Baseline Network Benchmark Interpretation

Run the network baseline upload benchmark:

```powershell
"D:\Tools\cloud-tools\Scripts\python.exe" scripts/gate4_upload_harness.py benchmark --payload-mb 2.0
```

- **Uplink Baseline**: Measures general internet uplink bandwidth to httpbin.org.
- **Interpretation Rule**: Baseline speed indicates general interface health. Sustained GCS throughput will differ due to regional edge ingress routing and multi-threaded windowing.

---

## 3. Verified Canary Probe Procedure

The isolated 150-byte canary probe was verified end-to-end during qualification. If the operator wishes to re-test API connectivity independently:

```powershell
"D:\Tools\cloud-tools\Scripts\kaggle.exe" datasets create -p "D:\Projects\ocean-sentinel\experiments\performance\cloud_kaggle_dataset_probe_canary" -r tar
```

Check status:
```powershell
"D:\Tools\cloud-tools\Scripts\kaggle.exe" datasets status dheeraj12237/ocean-sentinel-probe-canary
```
Expected output: `ready`.

---

## 4. Production Upload Command & Invocation

```
================================================================================
UNEXECUTED / HUMAN APPROVAL REQUIRED
================================================================================
```

### Direct Upload Command:
```powershell
"D:\Tools\cloud-tools\Scripts\kaggle.exe" datasets create -p "D:\Projects\ocean-sentinel\experiments\performance\cloud_kaggle_dataset_package_preflight_20260907_022953\staging" -r tar
```

### Recommended Decoupled Pipeline (Zero Risk of Monitor Impact):
```powershell
# Terminal 1 (Uploader - runs independently):
"D:\Tools\cloud-tools\Scripts\kaggle.exe" datasets create -p "D:\Projects\ocean-sentinel\experiments\performance\cloud_kaggle_dataset_package_preflight_20260907_022953\staging" -r tar > upload_raw.log 2>&1

# Terminal 2 (Monitor - can be attached, killed, or restarted anytime):
"D:\Tools\cloud-tools\Scripts\python.exe" scripts/gate4_upload_harness.py monitor --log-file upload_raw.log --out-dir experiments/performance/gate4_2_pre_upload_operations_20260907_193000/telemetry
```

### Alternative Piped Pipeline:
```powershell
"D:\Tools\cloud-tools\Scripts\kaggle.exe" datasets create -p "D:\Projects\ocean-sentinel\experiments\performance\cloud_kaggle_dataset_package_preflight_20260907_022953\staging" -r tar 2>&1 | "D:\Tools\cloud-tools\Scripts\python.exe" scripts/gate4_upload_harness.py monitor --out-dir experiments/performance/gate4_2_pre_upload_operations_20260907_193000/telemetry
```

---

## 5. Live Telemetry & Health States

During upload, the monitor continuously calculates rolling throughput and updates persistent logs.

### State Definitions:
- **GREEN (Healthy Upload)**:
  - `current_state: ACTIVE`
  - `time_since_last_progress_sec < 60.0`
  - Instantaneous throughput > 0, rolling 60s > 0, rolling 5m > 0.
  - Action: Do nothing; allow upload to stream.
- **YELLOW (Warning Stall)**:
  - `current_state: STALLED`
  - `60.0 <= time_since_last_progress_sec < 180.0`
  - Action: **DO NOT KILL PROCESS**. Diagnostic snapshot is automatically logged. Check if local tar packaging is active or if GCS is retrying a chunk.
- **RED (Critical Stall / Error)**:
  - `time_since_last_progress_sec >= 180.0` or `current_state: ERROR`
  - Action: Run manual diagnostic snapshot. Inspect failure classification in `upload_events.log`.

---

## 6. Real-Time Forensic Diagnostics

If the upload appears stalled, execute the diagnostic snapshot collector in a separate terminal:

```powershell
"D:\Tools\cloud-tools\Scripts\python.exe" scripts/gate4_upload_harness.py diagnose
```

This non-intrusively captures:
- Active network adapter link speed and socket error/drop counters
- CPU utilization (to distinguish tar packaging from genuine stalls)
- Disk free space on Drive C: and D:

---

## 7. Resumability & Interruption Mechanics

- **In-Process Resumption**: If a transient network glitch occurs during streaming, GCS resumable upload internally handles socket retries without restarting.
- **Command-Level Interruption**: If the upload process is killed (`Ctrl+C`, power loss, or terminal crash), restarting `kaggle datasets create` will archive into a new randomized temporary folder (`tempfile.mkdtemp()`). This will start a fresh upload.
- **Operational Rule**: Never kill the upload process during temporary rate fluctuations. Only terminate if an unrecoverable fatal authentication or remote API error is confirmed in `upload_events.log`.

---

## 8. Speed Optimization Decision Tree

```
1. Ethernet Connection:
   - Observable Signal: Active adapter is Wi-Fi (Link speed fluctuating 288-468 Mbps).
   - Safe Action: Connect wired Gigabit Ethernet cable. Disable Wi-Fi once Ethernet shows 'Up'.
   - Unsafe Action: Disabling network adapter during an active transfer.

2. Power & Thermal Management:
   - Observable Signal: AC plugged in, CPU throttles if laptop lid is closed.
   - Safe Action: Keep laptop lid open on AC power with adequate ventilation.

3. Antivirus Real-Time Scanning:
   - Observable Signal: High CPU load by Defender/McAfee during initial tar packaging.
   - Safe Action: Add temporary folder scan exclusions for:
     * D:\Projects\ocean-sentinel
     * C:\Users\Dheeraj\AppData\Local\Temp
   - Unsafe Action: Disabling antivirus or firewall globally.

4. Competing Network Transfers:
   - Observable Signal: Other video streams, downloads, or backup syncs on LAN.
   - Safe Action: Pause large concurrent downloads or cloud backups during upload.
```

---

## 9. Production Checkpoint Plan (U0 to U12)

| Checkpoint | Event | What is Checked | Normal Behavior | Action on Anomaly |
| :--- | :--- | :--- | :--- | :--- |
| **U0** | Ready | Preflight fields complete | 23 fields green | Abort if C: < 60 GB or AC offline |
| **U1** | Canary Pass | Isolated 150B canary | Remote `ready`, `isPrivate` | Do not start U2 if U1 fails |
| **U2** | Prod Start | Kaggle CLI launched | Staging read begins | Verify backslash path passed |
| **U3** | 1 GB | First progress update | Rolling 60s throughput > 0 | Verify tar packaging finished |
| **U4** | 10% | ~5.6 GB uploaded | Steady streaming | Check socket drop counters |
| **U5** | 25% | ~14.0 GB uploaded | ETA stabilizes | Verify AC power plugged in |
| **U6** | 50% | ~28.1 GB uploaded | Consistent rolling 5m | Monitor Wi-Fi renegotiation |
| **U7** | 75% | ~42.1 GB uploaded | No unexpected stalls | Observe persistent logs |
| **U8** | 100% | All bytes transferred | `100.0% [COMPLETE]` | Await remote Kaggle ingestion |
| **U9** | Remote Ready | `kaggle datasets status` | Status transitions to `ready` | Check web UI if stuck in processing |
| **U10**| Mount Verify | Remote container mount | Dataset visible in `/kaggle/input/` | Verify directory hierarchy |
| **U11**| Integrity | Manifest check | Root SHA-256 matches | Verify sample GeoTIFF read |
| **U12**| Dataloader | Smoke test batch | Batch load succeeds in < 1s | EXP01 training ready |

---

## 10. Explicit Hard-Stop Conditions

Halt and investigate immediately if:
1. **Authentication Error**: `401 Unauthorized` or token expired in `upload_events.log`.
2. **Drive C: Exhaustion**: Drive C: free space drops below `5.0 GB`.
3. **Visibility Leak**: Command lacks private enforcement or metadata shows `isPrivate: false`.
4. **Source Package Mutation**: Any file in `staging` changes hash or size.
5. **Critical Sustained Stall**: Time since last progress exceeds `300.0 s` while network is confirmed down.
