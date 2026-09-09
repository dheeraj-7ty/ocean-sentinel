# Ocean Sentinel Test Execution Architecture & Infrastructure

## 1. Overview & Principles

Ocean Sentinel operates under the **CAO (Chief Architecture Officer) Operating Principles**:
- **Repository, filesystem, and live execution results are authoritative.**
- Distinguish strictly between **OBSERVED FACTS**, **INFERENCES**, and **UNVERIFIED**.
- Never collapse test results into generic pass/fail. Explicit statuses include: `PASS`, `PASS WITH WARNINGS`, `FAIL`, `TIMEOUT`, `SKIPPED`, `DESELECTED`, and `INCOMPLETE`.
- Scientific coverage must never be weakened: no mock replacements of real data, no deletion of test cases, and no arbitrary skips.

---

## 2. Test Classification & Pytest Markers

The repository test suite consists of **473 collected tests** across 17 test modules, classified using official pytest markers registered in [`pyproject.toml`](file:///D:/Projects/ocean-sentinel/pyproject.toml):

| Marker | Execution Semantics | Scope / Dependencies | Expected Runtime |
|---|---|---|---|
| `unit` | Fast, isolated in-memory unit tests | Synthetic arrays, mocked HTTP (`respx`), no disk raster reads | < 0.05s per test |
| `integration` | Multi-component subsystem tests | Pipeline integration, telemetry, raster environments | 0.1s – 4.0s per test |
| `real_data` | Tests requiring physical disk artifacts | `data/raw/trujillo_2024/...`, manifests, cached weights | 0.2s – 2.0s per test |
| `slow` | Heavyweight, I/O-intensive real-data tests | Full corpus header reads (1,200 raw GeoTIFFs, 51.13 GB) | ~15-18s (module setup) |

---

## 3. Standard Execution Commands

### A. Default Test Suite (Standard Developer Workflow)
Runs all unit, integration, and fast real-data tests, excluding only the heavyweight 1,200-GeoTIFF spatial tests:
```bash
# Direct pytest command
python -m pytest -m "not slow" -v

# Or using the bounded observability runner
python scripts/run_test_suite.py --suite default
```
- **Tests Collected:** 466 selected, 7 deselected
- **Measured Runtime:** ~34.4 seconds
- **Default Timeout:** 120.0 seconds

### B. Heavyweight Real-Data Suite (Full Ground-Truth Validation)
Intentionally executes the physical dataset validation tests, including full 1,200-image cross-split spatial intersection and geotransform audits:
```bash
# Direct pytest command
python -m pytest -m "slow or real_data" -v

# Or using the bounded observability runner
python scripts/run_test_suite.py --suite heavyweight
```
- **Tests Collected:** 15 selected, 458 deselected
- **Workload:** 1,200 physical GeoTIFFs, 1,200 ground-truth masks, baseline `.pt` checkpoints
- **Measured Runtime:** ~24.0 seconds
- **Default Timeout:** 180.0 seconds

### C. Full Qualification Suite (Complete 473-Test Baseline)
Executes all collected tests across all modules without exclusions:
```bash
# Direct pytest command
python -m pytest -v

# Or using the bounded observability runner
python scripts/run_test_suite.py --suite full
```
- **Tests Collected:** 473 selected, 0 deselected
- **Measured Runtime:** ~46.5 – 48.1 seconds
- **Default Timeout:** 300.0 seconds

### D. Regression Suite (Gate 4.3B Windows Manifest Path Resolution)
Validates cross-platform manifest path parsing under POSIX and Windows path semantics:
```bash
python scripts/run_test_suite.py --suite regression
```
- **Tests Collected:** 3 selected, 470 deselected
- **Measured Runtime:** ~4.5 – 5.4 seconds

---

## 4. Timeout Architecture & Observability

### Why Process-Level Timeouts?
In native scientific ML runtimes containing compiled C/C++ extensions (GDAL, Rasterio, PyTorch LibTorch, CUDA runtime), in-process thread timeouts cannot safely interrupt blocking kernel or filesystem I/O. Abandoned worker threads leave file locks, GPU device allocations, and shared process memory contaminated.

To solve this safely without destabilizing the Python runtime or introducing extra package dependencies, Ocean Sentinel uses the dedicated process-level runner:
[`scripts/run_test_suite.py`](file:///D:/Projects/ocean-sentinel/scripts/run_test_suite.py).

### Timeout Enforcement Rules:
1. **Bounded Subprocess:** Pytest is executed in a dedicated subprocess tree with real-time stdout/stderr streaming.
2. **Deterministic Termination:** If the wall-clock execution exceeds the configured timeout limit, the runner initiates clean process group termination (`SIGTERM` / `terminate()`), followed by `SIGKILL` / `kill()` if unresponsive within 5 seconds.
3. **Failure Capture:** The runner captures the last active test `nodeid` from the line-buffered output stream.
4. **Unambiguous Exit Code:** Returns exit code `124` on timeout, and records status as `TIMEOUT`.

---

## 5. Heavyweight Spatial Test Optimization

### Root Cause Analysis of Previous Stalls
Historically, the full suite stalled at `tests/test_spatial_split.py` because:
1. Two tests (`test_zero_cross_split_spatial_intersection_against_raw_geotiffs` and `test_zero_cross_split_identical_geotransforms`) sequentially opened all 1,200 raw GeoTIFF images from disk **twice** (2,400 file open operations across 51.13 GB of data).
2. On Windows NTFS, reading 1,200 file headers sequentially requires ~15-16 seconds per pass (~32 seconds total).
3. Previous test invocations using quiet mode (`pytest -q`) produced no console output during file I/O, leading agents to assume the process was hung.

### Implemented Optimization (Zero Mocking)
In [`tests/test_spatial_split.py`](file:///D:/Projects/ocean-sentinel/tests/test_spatial_split.py), a shared module-scoped fixture `raw_geotiff_records` opens each of the 1,200 raw GeoTIFF headers **once**, caching the geometry bounding box and geotransform matrix in memory for both tests.
- **Coverage Impact:** 0% reduction (all 1,200 physical files verified; all 719,400 polygon intersections evaluated).
- **Execution Speed:** File setup reduced from 34.09s to 15.73s (a ~54% reduction in disk wait time).
