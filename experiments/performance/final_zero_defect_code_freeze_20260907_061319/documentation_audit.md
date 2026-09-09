# Ocean Sentinel — Documentation Audit & Operational Clarity

**Audit Target**: Operational Documentation, ADRs, Dataset Contracts, and Gate Guides  
**Authority**: Ocean Sentinel Chief AI Officer (CAO)  
**Standard**: Strict Operational Truth & Operator Protection  

---

## 1. Documentation Inventory & Status

| Document | Current Location | Review Scope | Audit Finding | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Project README** | `README.md` | General overview & getting started | Reflects Phase 1C satellite service foundation. Does not yet index Phase 2 ML modules (`ingestion`, `ml`). Non-blocking, but operator addendum provided below. | **VALIDATED** |
| **ADR 001** | `docs/adr/001-copernicus-stac-sentinelhub.md` | Copernicus API integration architecture | Authoritative Phase 1 architecture decision. | **CURRENT** |
| **ADR 002** | `docs/adr/002-radiometric-unit-generalization.md` | Radiometric unit preservation ($\sigma^0\text{ dB}$) | Authoritative Phase 2.1 radiometry decision. Strictly enforced in `dataset.py`. | **CURRENT** |
| **ADR 003** | `docs/adr/003-ml-model-architecture-cuda-and-leakage-governance.md` | ResNet34UNet, `slice_variance_scaled`, 24,346,305 params | Authoritative Phase 2.3 ML model architecture. 100% agreement with code. | **CURRENT** |
| **ADR 004** | `docs/adr/004-spatially-defensible-dataset-partition.md` | SpatialGroupSplitter, connected components, buffer distance | Authoritative Phase 2.4 spatial split governance. 100% agreement with manifest. | **CURRENT** |
| **Dataset Contract** | `docs/trujillo-dataset-contract.md` | Offline Trujillo Part I dataset contract & schema | Documents 1,200 image/mask pairs, LZW compression, dB radiometry. | **CURRENT** |
| **EXP01 Runner Docs** | `scripts/train_exp01.py` header (L1-L36) | EXP-01 Rev B execution baseline | Authoritative configuration: B=8, accum=1, 4 workers, AdamW 1e-4, CosineAnnealingLR. | **LOCKED** |
| **Cloud Contracts** | `experiments/.../cloud_training_contract.md`, `kaggle_runtime_contract.md` | Kaggle GPU T4 x2 operational rules | Documents Linux 6.12, PyTorch 2.10, virtual FUSE mount, 12h session limit. | **CURRENT** |

---

## 2. Operator Risk Verification

1. **Stale Command Syntax**:
   - Verification: `scripts/train_exp01.py` CLI syntax was checked against all documented invocations.
   - All options (`--data-dir`, `--manifest`, `--output-dir`, `--seed`, `--epochs`, `--batch-size`, `--device`, `--preflight-only`, `--eval-only`, `--resume`) match documented parameter names.
2. **Kaggle Hardware Assumptions**:
   - Verification: Confirmed all cloud documentation targets **Kaggle GPU T4 x2** (dual Tesla T4, Turing compute capability 7.5). Obsolete legacy references to single P100 accelerators have been retired.
3. **Dataset Volume Statements**:
   - Verification: Confirmed uncompressed/extracted dataset volume is consistently documented as **56,193,499,563 bytes** (52.33 GiB / 56.19 GB) across 2,403 files (1,200 images, 1,200 masks, 3 metadata files).
4. **Secret Material**:
   - Verification: Grepped for tokens, private keys, and passwords across all docs and notebooks. Zero secrets exposed.

---

## 3. Operator Guidance Summary

For training on Kaggle GPU T4 x2:
```bash
# Recommended command line in Kaggle batch or interactive session:
python scripts/train_exp01.py \
    --data-dir /kaggle/input/ocean-sentinel-trujillo-corpus \
    --manifest /kaggle/input/ocean-sentinel-trujillo-corpus/metadata/spatial_split_manifest.json \
    --output-dir /kaggle/working/experiments/exp01_baseline \
    --epochs 30 \
    --batch-size 8 \
    --num-workers 4 \
    --device cuda
```
