# Gate 4.3A — Test Execution and Verification Results

**Gate Reference**: `GATE_4.3A_REPOSITORY_HYGIENE_AND_CLOUD_PREFLIGHT`  
**Execution Timestamp**: `2026-09-08T09:56:45+05:30` to `2026-09-08T09:58:52+05:30`  
**Environment**: Python 3.10.9, PyTorch 2.14.0+cu126, CUDA 12.6, Windows 11  
**Targeted Change**: `tests/test_ml_components.py:42` updated to `spatial_split_manifest.json`  
**Overall Test Decision**: **100% PASS (139 / 139 TESTS PASSED)**  

---

## 1. Primary Targeted Test Suites

### A. `tests/test_ml_components.py`
- **Command**: `pytest tests/test_ml_components.py -v`
- **Execution Time**: 11.53s
- **Outcome**: **32 / 32 PASSED**
- **Key Validations**:
  - `TestResNet34UNet`: Architecture, parameter counts (24,346,305), forward/backward, gradient flow, CUDA FP16, and all 4 channel adaptation methods.
  - `TestVanillaUNet`: Classic 4-stage baseline forward pass.
  - `TestLosses`: `CombinedBCEAndDiceLoss`, `SoftDiceLoss` (empty mask conventions, worst prediction), and `FocalTverskyLoss`.
  - `TestMetrics`: `SegmentationMeter` streaming confusion matrix accumulation.
  - `TestThresholdOptimization`: Grid search across validation data.
  - `TestSARAugmentation`: Spatial consistency, binary mask preservation, deterministic seeding, and identity transform.
  - `TestRealDataPipelineIntegration` (**Directly affected by Line 42 fix**):
    - `test_real_dataset_sample_dimensions_and_types`: Loaded real tile from `spatial_split_manifest.json` (13,440 train tiles) — shape `(2, 512, 512)` float32, mask `(1, 512, 512)` float32 binary. **PASSED**.
    - `test_real_batch_through_model_and_loss`: Batch size 2 through `ResNet34UNet` and `CombinedBCEAndDiceLoss` — finite loss, finite IoU. **PASSED**.
  - `TestSpatialLeakageAudit`: Overlap calculations and haversine distances.

---

### B. `tests/test_canonical_exp01_fingerprint.py`
- **Command**: `pytest tests/test_canonical_exp01_fingerprint.py -v`
- **Execution Time**: 4.23s
- **Outcome**: **11 / 11 PASSED**
- **Key Validations**:
  - `TestCanonicalConstantsLock`: Hyperparameters, scheduler, batch size, parameter count locks.
  - `TestDiscrepancyRejection`: Explicit negative testing against hallucinated lr (5e-4), WarmRestarts scheduler, max epochs drift, and architectural deviations.
  - `TestCertifiedBaselineArtifacts`: Optimizer param group initial lr (0.0001), scheduler state (`T_max=30, eta_min=1e-6`), and smooth monotonic cosine decay in `history.json` without restarts.
  - `TestFingerprintGenerator`: Programmatic fingerprint dictionary integrity.

---

### C. `tests/test_exp01_eval.py`
- **Command**: `pytest tests/test_canonical_exp01_fingerprint.py tests/test_exp01_eval.py -v`
- **Execution Time**: 7.07s
- **Outcome**: **14 / 14 PASSED** (25/25 combined)
- **Key Validations**:
  - `TestSafeCheckpointLoading`: Safe loading under allowlisted globals, epoch 4 state dict integrity, and SHA-256 match.
  - `TestProcessLivenessAndLock`: Process liveness, stale lock recovery, and duplicate execution lock conflict prevention.
  - `TestLifecycleAndResults`: Atomic run state writing, `--eval-only` non-training guarantee, and terminal failure states.
  - `TestAuthoritativeArtifactImmutability`: Byte-for-byte SHA-256 verification of `best_model.pt` and `history.json`.

---

### D. `tests/test_spatial_split.py`
- **Command**: `pytest tests/test_spatial_split.py -v`
- **Execution Time**: 36.99s
- **Outcome**: **10 / 10 PASSED**
- **Key Validations**:
  - `TestSyntheticSpatialSplitter`: Overlap graph construction, connected component partitioning, and component indivisibility.
  - `TestRealSpatialSplitManifest`:
    - Patch counts: 840 train (70%), 180 val (15%), 180 test (15%) = 1,200.
    - Tile counts: 13,440 train, 2,880 val, 2,880 test = 19,200.
    - Normalization statistics provenance from train split only.
    - Raw GeoTIFF bounding box intersection: 0 cross-split positive spatial overlaps across 1,200 image headers.
    - Geotransform analysis: 0 cross-split identical geotransforms.
    - Spatial split audit certification: `CERTIFIED_LEAKAGE_FREE`.
    - `TrujilloTileDataset` loader integration.

---

## 2. Broader Regression Suite

To ensure the manifest reference update in `tests/test_ml_components.py` caused zero regressions across dataset parsing, tiling, and ingestion, the full ingestion and pipeline test suites were executed:

### A. `tests/test_dataset_pipeline.py` & `tests/test_trujillo_ingestion.py`
- **Command**: `pytest tests/test_dataset_pipeline.py tests/test_trujillo_ingestion.py -v`
- **Execution Time**: 9.52s
- **Outcome**: **72 / 72 PASSED** (52 expected GDAL/rasterio Affine deprecation warnings safely caught)
- **Key Validations**:
  - Manifest generation and patch/mask pairing.
  - Split determinism across random seeds.
  - Spatial group leakage prevention.
  - Normalization contract: computed strictly from train split.
  - `TrujilloTileDataset`: Lazy sample loading, tensor shapes, float32 conversion, binary mask contract.
  - Error taxonomy: `DatasetError` hierarchy.
  - Real Trujillo mask validation: 1,200 mask files exist and conform to contract.

---

## 3. Pretrained Weight Access Offline Verification

- **Command**: Python script validating offline loading using local cache and `TORCH_HOME` override.
- **Outcome**: **SUCCESS**
- **Observed Evidence**:
  - Source weights: `C:\Users\Dheeraj\.cache\torch\hub\checkpoints\resnet34-b627a593.pth` (87,319,819 bytes, SHA-256: `b627a593bcbe140c234610266fe4f8ae95ea42fc881d091c9b6052e6b1d0590f`).
  - Isolated temporary directory populated with `hub/checkpoints/resnet34-b627a593.pth`.
  - Initialized `ResNet34UNet(in_channels=2, num_classes=1, pretrained=True)` with `TORCH_HOME` pointing to isolated directory.
  - Successfully instantiated and adapted model offline with zero network calls.

---

## 4. Test Summary Table

| Test Suite File | Tests | Passed | Failed | Skipped | Duration | Status |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| `tests/test_ml_components.py` | 32 | 32 | 0 | 0 | 11.53s | **PASS** |
| `tests/test_canonical_exp01_fingerprint.py` | 11 | 11 | 0 | 0 | 4.23s | **PASS** |
| `tests/test_exp01_eval.py` | 14 | 14 | 0 | 0 | 7.07s | **PASS** |
| `tests/test_spatial_split.py` | 10 | 10 | 0 | 0 | 36.99s | **PASS** |
| `tests/test_dataset_pipeline.py` | 40 | 40 | 0 | 0 | 5.81s | **PASS** |
| `tests/test_trujillo_ingestion.py` | 32 | 32 | 0 | 0 | 3.71s | **PASS** |
| **Total Test Regressions** | **139** | **139** | **0** | **0** | **69.34s** | **100% PASS** |
