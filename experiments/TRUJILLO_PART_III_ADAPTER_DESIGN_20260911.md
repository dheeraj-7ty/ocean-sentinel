# Ocean Sentinel — External Benchmark Adapter Design Specification: Trujillo Part III

**Document Identifier:** `TRUJILLO_PART_III_ADAPTER_DESIGN_20260911`  
**Execution Phase:** Phase 4C (Evaluation Contract + External Benchmark Adapter Design)  
**Dataset Under Specification:** Trujillo Part III (`10.5281/zenodo.13761290`, `02_Test_images_and_ground_truth.7z`)  
**Authority:** Chief Architect Officer (CAO) Mandate  
**Execution Date:** 2026-09-11  
**Baseline Git HEAD:** `542bab19f6f08c9bba8b8762e6480386c8b6026b`  
**Active Git Branch:** `master`  
**ML Forward Passes:** Exactly 0  
**Design Status:** **`FROZEN_PENDING_CAO_APPROVAL`**  

---

## 1. Adapter Philosophy and System Architecture

The Trujillo Part III External Benchmark Adapter is a **strictly read-only, non-destructive, deterministic, versioned, and reproducible** software interface.

### Architectural Invariants:
1. **Zero Source Mutation:** The adapter shall NEVER open canonical source GeoTIFFs in write mode, modify file timestamps, rewrite rasters, resample source files, reproject coordinates on disk, or alter directory structures.
2. **Deterministic Geometry:** Array slicing operations are strictly integer-indexed. Continuous spatial resampling (bilinear, bicubic, nearest-neighbor coordinate warping) is prohibited.
3. **Fail-Closed Unknown Resolution:** Unknown properties identified during Phase 4B-3 qualification (polarization channel ordering, radiometric physical calibration, world-coordinate mask georeferencing) must NEVER be resolved through heuristics or silent defaults. If a required operational policy is unspecified, the adapter must halt immediately with an informative exception.
4. **Isolated Memory / Temporary Structures:** Intermediate tile tensors and manifests exist exclusively in memory or in atomically written, durable temporary scratch structures.

```
+----------------------------------------------------------------------------------------------------+
|                                    CANONICAL TRUJILLO PART III                                     |
|                                       (Strictly Read-Only)                                         |
|                                                                                                    |
|   Images/Oil/00000.tif (float32, 2x2048x2048)        Mask/Oil/00000_segmentation.tif (uint8, 2048)  |
+----------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+────────────────────────────────────────────────────────────────────────────────────────────────────+
|                                    READ-ONLY BENCHMARK ADAPTER                                     |
|                                                                                                    |
|  [Stage 1]  Discover Sample Manifest (450 items, strictly cataloged)                               |
|  [Stage 2]  Resolve Bijective Pair (Stem + Class directory convention)                             |
|  [Stage 3]  Rasterio Windowed Read (Single 512x512 tile window or full 2048 read)                 |
|  [Stage 4]  Shape & Finite Dtype Validation (2x2048x2048 float32, 2048x2048 uint8, 0 NaNs/Infs)    |
|  [Stage 5]  Explicit Polarization Mapping (MAPPING_A: [0, 1] vs MAPPING_B: [1, 0])                 |
|  [Stage 6]  Radiometric Pass-Through (Direct float32 values; zero unverified physical scaling)     |
|  [Stage 7]  Frozen Z-Score Normalization (Train stats: mu=[-33.23, -19.94], sigma=[6.49, 4.53])   |
|  [Stage 8]  Deterministic Tiling (16 non-overlapping 512x512 chips, row-major order)               |
|  [Stage 9]  Identical Mask Slicing & Dtype Cast (uint8 {0, 1} -> float32 {0.0, 1.0}, shape 1x512)  |
|  [Stage 10] Emit Model-Ready Tensor Batch ((B, 2, 512, 512) + (B, 1, 512, 512))                   |
|  [Stage 11] Emit Immutable Provenance Record (Complete lineage, hashes, tile coordinates)          |
+────────────────────────────────────────────────────────────────────────────────────────────────────+
                                                  │
                                                  ▼
+----------------------------------------------------------------------------------------------------+
|                                      OCEAN SENTINEL PIPELINE                                       |
|                                                                                                    |
|    - Model Input: (B, 2, 512, 512) float32                                                         |
|    - Target Mask: (B, 1, 512, 512) float32                                                         |
|    - Reconstructed Mosaic: (1, 2048, 2048) probability map evaluated at tau = 0.22                  |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Section 6.1 — Adapter Pipeline Stages

The adapter pipeline consists of 11 sequential, modular stages:

### Stage 1: Discover Sample
- **Input:** Extracted root directory `data/raw/external_validation/trujillo_part_iii/extracted/`.
- **Output:** Ordered list of canonical scene identifiers (`class_name`, `stem`).
- **Scientific Assumption:** Exactly 450 scenes exist partitioned across three classes (`Oil`: 150, `No oil`: 150, `Lookalike`: 150) as proven in `scratch/trujillo_part_iii_extracted_inventory.json`.
- **Evidence Source:** Reconciliation R1 audit and extraction inventory.
- **Failure Mode & Handling:** Any count $\neq 450$ or unexpected class name raises `AdapterDiscoveryError` (FAIL CLOSED).

### Stage 2: Resolve Image/Mask Pair
- **Input:** Class name and scene stem (e.g., `Oil`, `00000`).
- **Output:** Absolute paths:
  $$\text{Image: } \texttt{Images/[Class]/[Stem].tif}, \quad \text{Mask: } \texttt{Mask/[Class]/[Stem]\_segmentation.tif}$$
- **Scientific Assumption:** Suffix `_segmentation.tif` uniquely corresponds to `.tif` image stem within the same class folder.
- **Evidence Source:** Reconciliation R2 pairing audit ($450 / 450$ bijective matches).
- **Failure Mode & Handling:** Missing partner file, multiple matching masks, or broken path raises `AdapterPairingError` (FAIL CLOSED).

### Stage 3: Read TIFF Containers
- **Input:** Absolute image and mask paths, target window (or full raster).
- **Output:** In-memory NumPy arrays: raw image array $(2, H, W)$ and raw mask array $(H, W)$.
- **Scientific Assumption:** Containers are valid GeoTIFFs readable via GDAL/Rasterio without data corruption.
- **Evidence Source:** Reconciliation R1 audit ($900 / 900$ containers readable).
- **Failure Mode & Handling:** Corrupt container, I/O error, or unreadable blocks raises `AdapterReadError` (FAIL CLOSED).

### Stage 4: Validate Shape and Finite Dtype
- **Input:** In-memory image and mask arrays.
- **Output:** Verified image array $(2, 2048, 2048)$ `float32`, verified mask array $(2048, 2048)$ `uint8`.
- **Scientific Assumption:** Spatial dimensions are identically $2048 \times 2048$; image has 2 channels; mask has 1 channel; mask values are strictly binary $\{0, 1\}$; all image values are finite real numbers.
- **Evidence Source:** Reconciliations R1, R3, R4.
- **Failure Mode & Handling:** Shape mismatch, non-finite values ($\text{NaN}, +\infty, -\infty$), unexpected channels, or non-binary mask values raises `AdapterValidationError` (FAIL CLOSED).

### Stage 5: Polarization Channel Handling
- **Input:** Validated 2-band image array and explicit `channel_policy` configuration (`MAPPING_A` or `MAPPING_B`).
- **Output:** 2-channel array ordered according to policy:
  - `MAPPING_A`: Channel 0 = Band 1, Channel 1 = Band 2.
  - `MAPPING_B`: Channel 0 = Band 2, Channel 1 = Band 1.
- **Scientific Assumption:** Direct GeoTIFF tags lack band descriptions. Permutation must be explicitly configured and pre-specified before evaluation; the adapter must not guess or tune based on performance.
- **Evidence Source:** Evaluation Contract Section 6.
- **Failure Mode & Handling:** If `channel_policy` is `AUTO` or undefined, raise `AdapterPolicyError` (FAIL CLOSED).

### Stage 6: Radiometric Pass-Through
- **Input:** Channel-ordered `float32` array.
- **Output:** Radiometrically un-altered `float32` array.
- **Scientific Assumption:** In the absence of authoritative container calibration tags, raw floating-point values are preserved directly without pseudo-calibration, uncalibrated decibel transformations, or linear scaling.
- **Evidence Source:** Evaluation Contract Section 7.
- **Failure Mode & Handling:** Attempted conversion to linear units without authoritative calibration tags raises `AdapterRadiometricError` (FAIL CLOSED).

### Stage 7: Frozen Numerical Standardization (Normalization)
- **Input:** Radiometrically preserved array and frozen normalization parameters:
  $$\mu = [-33.233136989478695, -19.941215852796695]$$
  $$\sigma = [6.489985665955077, 4.531345684833188]$$
- **Output:** Standardized `float32` array:
  $$x_{\text{norm}}[c] = \frac{x[c] - \mu_c}{\sigma_c}$$
- **Scientific Assumption:** Normalization constants are frozen from the Part I training split as a numerical model-input compatibility transformation. This does NOT establish physical calibration of Trujillo source data.
- **Evidence Source:** Evaluation Contract Section 7 and `spatial_split_manifest.json`.
- **Failure Mode & Handling:** Attempting to fit parameters on Part III or supplying mismatched parameter vectors raises `AdapterNormalizationError` (FAIL CLOSED).

### Stage 8: Deterministic Tiling
- **Input:** Full normalized scene array $(2, 2048, 2048)$ and grid configuration ($H_{\text{tile}}=512, W_{\text{tile}}=512, \text{stride}=512$).
- **Output:** Ordered list of 16 tile arrays of shape $(2, 512, 512)$.
- **Scientific Assumption:** $2048$ is exactly divisible by $512$ ($2048 = 4 \times 512$). Grid tiling with stride 512 achieves 100% complete coverage with zero overlap and zero pixel dropping.
- **Evidence Source:** Evaluation Contract Section 8.
- **Failure Mode & Handling:** Tile count $\neq 16$ or non-zero residual pixels raises `AdapterTilingError` (FAIL CLOSED).

### Stage 9: Transform Mask Identically
- **Input:** Full scene mask array $(2048, 2048)$ `uint8`.
- **Output:** Ordered list of 16 target mask arrays of shape $(1, 512, 512)$ `float32` with values in $\{0.0, 1.0\}$.
- **Scientific Assumption:** Mask slicing uses identical row/col integer offsets as image tiling in array coordinates. Zero continuous resampling, zero one-pixel shifts, zero transposition.
- **Evidence Source:** Evaluation Contract Section 8.
- **Failure Mode & Handling:** Mask tile shape $\neq (1, 512, 512)$ or non-binary values raises `AdapterMaskError` (FAIL CLOSED).

### Stage 10: Emit Model-Ready Tensors
- **Input:** Image tile arrays and mask tile arrays.
- **Output:** PyTorch tensor pair `(image_tensor, mask_tensor)`:
  - `image_tensor`: `torch.float32`, shape `(2, 512, 512)`.
  - `mask_tensor`: `torch.float32`, shape `(1, 512, 512)`.
- **Scientific Assumption:** Ingestion pipeline requires PyTorch float32 tensors with channel-first ordering.
- **Evidence Source:** Pipeline contract in `src/ocean_sentinel/ingestion/dataset.py`.
- **Failure Mode & Handling:** Non-torch types, incorrect shapes, or memory layout discontinuities raises `AdapterEmissionError` (FAIL CLOSED).

### Stage 11: Emit Provenance Metadata
- **Input:** Execution context, sample identity, tile indices, cryptographic hashes.
- **Output:** Immutable dictionary record attached to each emitted sample/tile.
- **Scientific Assumption:** Every emitted sample must carry complete provenance to ensure end-to-end reproducibility.
- **Evidence Source:** Evaluation Contract Section 13.
- **Failure Mode & Handling:** Missing required provenance fields raises `AdapterProvenanceError` (FAIL CLOSED).

---

## 3. Section 6.2 — Fail-Closed Unknown Handling Policy

The adapter must never make ad-hoc heuristic guesses to resolve unverified properties:

| Unverified Dimension | Permitted Operational Action | Prohibited Operational Action | Failure Enforcement |
|---|---|---|:---:|
| **Polarization Order** | Must be explicitly passed via configuration: `--polarization-mapping MAPPING_A` or `MAPPING_B`. | Guessing based on heuristic; evaluating both and selecting the higher score post-hoc. | If unconfigured, raise `ValueError("Polarization mapping must be explicitly specified.")`. |
| **Radiometric Units** | Preserve raw floating-point values directly as model input. | Inventing a linear conversion, adding arbitrary dB calibration offsets, or fitting scaling constants. | If pseudo-calibration requested, raise `NotImplementedError("Uncalibrated conversion prohibited.")`. |
| **Geospatial Registration** | Operate exclusively in pixel array coordinates $[r, c]$. | Projecting masks or images to mismatched spatial coordinate reference systems. | If CRS warp requested, raise `RuntimeError("World-coordinate warping unauthorized by contract.")`. |
| **Dataset Semantics** | Retain class folder identities (`Oil`, `No oil`, `Lookalike`) in metadata. | Treating 300 empty masks as confirmed absence of oil without qualification disclosure. | If unstratified pooling attempted, raise `ValueError("Stratified reporting required.")`. |

---

## 4. Section 6.3 — Metadata and Provenance Schema

Each emitted tile carries an immutable provenance dictionary adhering to this exact schema:

```json
{
  "adapter_version": "1.0.0",
  "dataset_identity": {
    "dataset_name": "trujillo_part_iii",
    "zenodo_record_id": "13761290",
    "zenodo_doi": "10.5281/zenodo.13761290",
    "archive_filename": "02_Test_images_and_ground_truth.7z"
  },
  "sample_identity": {
    "class_name": "Oil",
    "stem": "00000",
    "image_filename": "00000.tif",
    "mask_filename": "00000_segmentation.tif",
    "image_sha256": "07AEC8CA52459A99FFDA8FECA81D7D38BBD31ECEBD34150B0AB1A7DDB672C469",
    "mask_sha256": "CBBFBA32788FBC789B53E8DD2C5025D2C474D289196B000572E92C2A07530661"
  },
  "geometry": {
    "parent_height": 2048,
    "parent_width": 2048,
    "tile_id": "00000_r00_c00",
    "row_index": 0,
    "col_index": 0,
    "row_offset": 0,
    "col_offset": 0,
    "tile_height": 512,
    "tile_width": 512
  },
  "configuration": {
    "channel_policy": "MAPPING_A",
    "channel_order": [0, 1],
    "normalization_means": [-33.233136989478695, -19.941215852796695],
    "normalization_stds": [6.489985665955077, 4.531345684833188],
    "mask_dtype_cast": "uint8 -> float32",
    "coordinate_mode": "array_indices",
    "threshold_reference": "0.22 (PROBABILITY_DOMAIN_SIGMOID)"
  },
  "statistics": {
    "tile_foreground_pixels": 4128,
    "tile_foreground_ratio": 0.0157470703125,
    "tile_has_oil": true,
    "image_finite": true
  }
}
```

---

## 5. Section 7 — Comprehensive Threat Model & Methodological Attack Review

Before closure, the evaluation methodology and adapter design were actively tested against an exhaustive suite of failure modes and methodological edge cases:

| # | Threat / Edge Case | Expected Safe Behavior | Detection Method | Failure State | Scientific Impact & Block/Pass Condition |
|---|---|---|---|---|:---:|
| **1** | **Wrong Threshold Domain** | Threshold $\tau=0.22$ applied strictly to sigmoid probabilities $p \in [0, 1]$. | Code assertion: verify `is_logits` or probability range before thresholding. | `THRESHOLD_DOMAIN_MISMATCH` | **BLOCK:** Applying 0.22 to raw logits would produce nearly 100% positive mask (collapse). |
| **2** | **Wrong Normalization Order** | Standardization applied strictly after channel selection. | Verify channel association against explicit policy. | `NORMALIZATION_ORDER_ERROR` | **BLOCK:** Inverting order would standardize wrong band with wrong channel parameters. |
| **3** | **Wrong Channel Order** | Enforce explicit `MAPPING_A` or `MAPPING_B`; prohibit automatic swapping. | Check policy argument; fail closed if absent. | `UNSPECIFIED_CHANNEL_POLICY` | **BLOCK:** Silent swapping would corrupt sensitivity analysis. |
| **4** | **Accidental Test-Set Fitting** | Use frozen Part I training stats; never compute mean/std on Part III. | Verify hardcoded stats match `spatial_split_manifest.json`. | `TEST_SET_CONTAMINATION` | **BLOCK:** Adapting to test data violates generalization benchmark. |
| **5** | **Accidental Threshold Tuning** | Threshold fixed to 0.22; zero grid search or ROC optimization. | Verify no grid search loops in evaluation scripts. | `POST_HOC_OPTIMIZATION` | **BLOCK:** Optimizing threshold inflates benchmark scores artificially. |
| **6** | **2048/512 Off-by-One** | Exact row/col offsets $[0, 512, 1024, 1536]$. | Offset boundary assertions ($r_{\text{off}} + 512 \le 2048$). | `GEOMETRIC_OFFSET_ERROR` | **BLOCK:** Index shift would drop edge pixels or truncate tiles. |
| **7** | **Tile Boundary Errors** | Reconstruct mosaic with exact non-overlapping placement. | Verify all $2048 \times 2048$ pixels populated exactly once. | `MOSAIC_RECONSTRUCTION_GAP` | **BLOCK:** Unpopulated pixels corrupt whole-scene metrics. |
| **8** | **Duplicate Tile** | Exactly 16 distinct tiles per scene; unique tile IDs. | Set uniqueness check on `len(set(tile_ids)) == 16`. | `DUPLICATE_TILE_EMISSION` | **BLOCK:** Double-counting inflates micro metrics. |
| **9** | **Missing Tile** | All 16 tiles emitted in row-major order. | Count check `len(tiles) == 16`. | `MISSING_TILE_ERROR` | **BLOCK:** Incomplete scene coverage invalidates whole-scene mosaic. |
| **10** | **Mask One-Pixel Shift** | Identical integer offsets for image and mask. | Spot check array equality between full scene and tiles. | `SPATIAL_REGISTRATION_SHIFT` | **BLOCK:** One-pixel misalignment severely degrades IoU on thin slicks. |
| **11** | **Transpose ($r \leftrightarrow c$)** | Maintain row-major orientation $[y, x]$. | Coordinate orientation checks in structural tests. | `ARRAY_TRANSPOSE_ERROR` | **BLOCK:** Transposing mask destroys IoU completely. |
| **12** | **Horizontal Flip** | Maintain native raster column order $[0 \dots 2047]$. | Compare top-left and top-right feature slices. | `HORIZONTAL_INVERSION_ERROR` | **BLOCK:** Spatial misalignment destroys evaluation validity. |
| **13** | **Vertical Flip** | Maintain native raster row order $[0 \dots 2047]$. | Compare top-left and bottom-left feature slices. | `VERTICAL_INVERSION_ERROR` | **BLOCK:** Inversion destroys evaluation validity. |
| **14** | **Source Mask Inversion** | Foreground strictly $\{1\}$, background $\{0\}$. | Value check on Oil masks: foreground ratio $< 50\%$. | `MASK_INVERSION_ERROR` | **BLOCK:** Inverting mask turns ocean into slick, collapsing metrics. |
| **15** | **Dtype Conversion Error** | Mask cast `uint8` $\{0, 1\} \rightarrow \text{float32}$ $\{0.0, 1.0\}$. | Check unique values in mask tensor remain strictly $\{0.0, 1.0\}$. | `DTYPE_CORRUPTION` | **BLOCK:** Truncation or non-binary float corrupts BCE/Dice loss. |
| **16** | **NaN / Inf Introduction** | All pixels finite real numbers. | `np.all(np.isfinite(img))` assertion on every batch. | `NONFINITE_PIXEL_ERROR` | **BLOCK:** Any NaN propagates through network, invalidating output. |
| **17** | **Empty Mask Handling** | Evaluate empty masks with isolated FAR metrics; no pooling with IoU. | Verify stratified metric dispatch by class. | `METRIC_POOLING_ERROR` | **BLOCK:** 300 empty masks would artificially distort unstratified mean IoU. |
| **18** | **All-Positive Prediction** | Evaluated safely: $FP = \text{Clean pixels}$, IoU drops. | Metrics record full false alarm collapse. | `THRESHOLD_COLLAPSE` | **PASS:** Model failure is captured accurately by metrics. |
| **19** | **All-Negative Prediction** | Evaluated safely: $FN = \text{Foreground pixels}$, $\text{IoU}=0.0$. | Metrics record zero-detection failure. | `DETECTION_COLLAPSE` | **PASS:** Model failure is captured accurately by metrics. |
| **20** | **Undefined Metric Denominator** | Safe divide rules: $0/0 \rightarrow 0.0$ or stratum-isolated metric. | ZeroDivisionError catch and explicit conditional logic. | `UNDEFINED_DIVISION_ERROR` | **BLOCK:** Silent NaN or crash during evaluation. |
| **21** | **Silent Exclusion** | Strictly enforce $N=150$ per stratum; log any technical failure. | Check sample count before and after evaluation. | `SILENT_SAMPLE_REMOVAL` | **BLOCK:** Removing hard samples produces biased benchmark results. |
| **22** | **Duplicate Source Sample** | 450 distinct scenes; unique file stems. | Set uniqueness check on scene stems. | `DATASET_DUPLICATION_ERROR` | **BLOCK:** Duplicate scenes bias population evaluation. |
| **23** | **Benchmark Leakage** | Part III kept isolated; zero exact SHA-256 matches against Part I. | Verify cross-dataset cryptographic leakage audit. | `BENCHMARK_LEAKAGE` | **PASS:** Reconciled in Phase 4B-3 (zero duplicate rasters). |
| **24** | **Checkpoint Drift** | Checkpoint hashes verified before evaluation. | SHA-256 match against certified checkpoint fingerprint. | `CHECKPOINT_MODIFICATION` | **BLOCK:** Running uncertified model checkpoint invalidates benchmark. |
| **25** | **Accidental Model Import / Load** | Adapter script has zero model dependencies or checkpoint loaders. | Static import audit; runtime inspection of loaded modules. | `FIREWALL_BREACH` | **BLOCK:** Phase 4C must remain strictly design and structural validation. |
| **26** | **Accidental Network Access** | Local execution only (`NETWORK_ACCESS = NONE`). | Socket binding audit; air-gapped execution mode. | `NETWORK_FIREWALL_BREACH` | **BLOCK:** External calls violate offline reproducibility contract. |
| **27** | **Partial State after Disconnect** | Atomic durable state updates (`.tmp` + `fsync` + `os.replace`). | State file validation and parsing on resume. | `STATE_CORRUPTION` | **PASS:** Atomic writes ensure corrupted partial state cannot exist. |
| **28** | **Stale Lock / Competing Process** | Single-instance lock with active PID checking. | Test contention rejection and dead PID reclamation. | `CONCURRENCY_CONFLICT` | **PASS:** Verified in `scratch/trujillo_part_iii_adapter_safety_report.json`. |
| **29** | **Report / Artifact Contradiction** | Programmatic self-audit cross-checks numbers across all artifacts. | Automated verification script (`self_audit_phase_4c.py`). | `ARTIFACT_INCONSISTENCY` | **BLOCK:** Contradictions block evaluation authorization. |

---

## 6. Document Status and CAO Handoff

This Adapter Design Specification is complete, exhaustively threat-modeled, and formally **FROZEN**.

**Status:** **`PHASE_4C_DESIGN_READY_FOR_CAO_EVALUATION_AUTHORIZATION`**  
Structural validation passed; zero model forward passes executed.
