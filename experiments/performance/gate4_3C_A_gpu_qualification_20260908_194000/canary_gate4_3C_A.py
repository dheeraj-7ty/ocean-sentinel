#!/usr/bin/env python3
"""
Ocean Sentinel — Gate 4.3C-A Cloud GPU Qualification Canary Script

PURPOSE:
Establish whether the ACTUAL Kaggle execution environment currently available
to Ocean Sentinel is qualified to run the canonical EXP01 training stack on GPU.

INFRASTRUCTURE QUALIFICATION GATE:
- ZERO optimizer steps permitted (OPTIMIZER_STEP_COUNT = 0).
- NO silent CPU fallback: if GPU is unsupported, unavailable, or unverified,
  hard-abort immediately before any forward/loss execution.
- Canonical model: ResNet34UNet (2 in, 1 out, 24,346,305 trainable parameters).
- Pretrained checkpoint SHA256: B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F.
- Adaptation method: slice_variance_scaled.
- Loss: 0.5 BCE + 0.5 SoftDice (smooth=1.0).
- Real data sample passed through real ingestion path.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# CANONICAL CONSTANTS
# ============================================================
GATE_ID = "GATE_4.3C_A_GPU_QUALIFICATION"
EXPECTED_WEIGHT_FILENAME = "resnet34-b627a593.pth"
EXPECTED_WEIGHT_SHA256 = "B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F"
EXPECTED_WEIGHT_SIZE_BYTES = 87_319_819
EXPECTED_PARAM_COUNT = 24_346_305
EXPECTED_ADAPTATION_METHOD = "slice_variance_scaled"
CANONICAL_NORM_MEANS = [-33.233136989478695, -19.941215852796695]
CANONICAL_NORM_STDS = [6.489985665955077, 4.531345684833188]
EXPECTED_TOTAL_TILES = 19200
EXPECTED_TRAIN_TILES = 13440
EXPECTED_VAL_TILES = 2880
EXPECTED_TEST_TILES = 2880

# State accumulator
START_UTC = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

QUALIFICATION_RESULT: Dict[str, Any] = {
    "gpu_present": False,
    "gpu_name": "none",
    "gpu_compute_capability": "none",
    "pytorch_version": "UNKNOWN",
    "cuda_runtime": "none",
    "pytorch_cuda_compatible": False,
    "cuda_tensor_smoke": "NOT_VERIFIED",
    "model_gpu_smoke": "NOT_VERIFIED",
    "loss_backward_gpu_smoke": "NOT_VERIFIED",
    "cpu_fallback_detected": False,
    "optimizer_step_count": 0,
    "training_allowed": False,
    "gate_decision": "NOT_VERIFIED",
    "reasons": [],
    "warnings": [],
}

EXECUTION_LOG: List[Dict[str, Any]] = []


def utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(msg: str) -> None:
    ts = utcnow()
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    EXECUTION_LOG.append({"timestamp": ts, "message": msg})


def phase_start(name: str) -> None:
    log(f"PHASE START: {name}")


def phase_complete(name: str) -> None:
    log(f"PHASE COMPLETE: {name}")


def phase_failed(name: str, error: str) -> None:
    log(f"PHASE FAILED: {name} - Error: {error}")


def get_output_dir() -> Path:
    if Path("/kaggle/working").exists():
        out = Path("/kaggle/working/gate4_3C_A_gpu_qualification")
    else:
        out = Path("./cloud_output_gate4_3C_A")
    out.mkdir(parents=True, exist_ok=True)
    return out


def setup_import_path() -> Path | None:
    """Resolve ocean_sentinel package path in Kaggle environment."""
    _script_dir = Path(__file__).resolve().parent
    _src_mount = Path("/kaggle/input/ocean-sentinel-src")
    _candidates = [
        _src_mount,
        _script_dir / "src",
        _script_dir,
        Path("/kaggle/working/src"),
    ]
    for _cand in _candidates:
        if (_cand / "ocean_sentinel" / "__init__.py").exists():
            if str(_cand) not in sys.path:
                sys.path.insert(0, str(_cand))
            log(f"  Import path resolved (nested): {_cand}")
            return _cand
        elif _cand.exists() and (_cand / "__init__.py").exists():
            # Flat extraction: symlink into working
            _working = Path("/kaggle/working")
            _symlink = _working / "ocean_sentinel"
            if not _symlink.exists():
                os.symlink(str(_cand), str(_symlink))
                log(f"  Created symlink: {_symlink} -> {_cand}")
            if str(_working) not in sys.path:
                sys.path.insert(0, str(_working))
            log(f"  Import path resolved (flat symlink): {_working}")
            return _working
    log("  WARNING: ocean_sentinel package directory not found in standard paths.")
    return None


# ============================================================
# PHASE 0: BOOT & ENVIRONMENT INSPECTION
# ============================================================
def phase0_boot() -> Dict[str, Any]:
    phase_start("BOOT_ENVIRONMENT")
    import torch
    import torchvision

    cuda_avail = torch.cuda.is_available()
    gpu_count = torch.cuda.device_count() if cuda_avail else 0
    gpu_names = [torch.cuda.get_device_name(i) for i in range(gpu_count)]
    cuda_ver = torch.version.cuda or "none"
    cudnn_ver = str(torch.backends.cudnn.version()) if cuda_avail else "none"

    env_info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "cwd": str(Path.cwd()),
        "torch_version": torch.__version__,
        "torchvision_version": torchvision.__version__,
        "cuda_available": cuda_avail,
        "cuda_version": cuda_ver,
        "cudnn_version": cudnn_ver,
        "gpu_count": gpu_count,
        "gpu_names": gpu_names,
    }

    QUALIFICATION_RESULT["pytorch_version"] = torch.__version__
    QUALIFICATION_RESULT["cuda_runtime"] = cuda_ver

    log(f"  OS / Platform:    {env_info['platform']}")
    log(f"  Python:           {env_info['python_version']}")
    log(f"  PyTorch:          {env_info['torch_version']}")
    log(f"  CUDA Runtime:     {env_info['cuda_version']}")
    log(f"  cuDNN:            {env_info['cudnn_version']}")
    log(f"  GPU Count:        {gpu_count}")
    for i, name in enumerate(gpu_names):
        log(f"  GPU {i}:           {name}")

    phase_complete("BOOT_ENVIRONMENT")
    return env_info


# ============================================================
# PHASE 1: HARD GPU COMPATIBILITY GATE
# ============================================================
def phase1_gpu_compatibility(env_info: Dict[str, Any]) -> bool:
    phase_start("GPU_COMPATIBILITY_GATE")
    import torch

    cuda_avail = torch.cuda.is_available()
    gpu_count = torch.cuda.device_count() if cuda_avail else 0

    if not cuda_avail or gpu_count == 0:
        QUALIFICATION_RESULT["gpu_present"] = False
        QUALIFICATION_RESULT["pytorch_cuda_compatible"] = False
        QUALIFICATION_RESULT["reasons"].append("GPU is not present or CUDA is unavailable.")
        phase_failed("GPU_COMPATIBILITY_GATE", "No GPU / CUDA available")
        return False

    QUALIFICATION_RESULT["gpu_present"] = True
    gpu_name = torch.cuda.get_device_name(0)
    cap = torch.cuda.get_device_capability(0)
    sm_str = f"sm_{cap[0]}{cap[1]}"

    QUALIFICATION_RESULT["gpu_name"] = gpu_name
    QUALIFICATION_RESULT["gpu_compute_capability"] = sm_str

    log(f"  Primary GPU:                {gpu_name}")
    log(f"  Compute Capability:         {sm_str} ({cap[0]}.{cap[1]})")

    # Hard architectural gate: PyTorch 2.10+cu128 requires sm_70+ (Volta/Turing+)
    # P100 is sm_60 (Pascal) -> strictly INCOMPATIBLE
    if cap[0] < 7:
        reason = (
            f"GPU compute capability {sm_str} ({cap[0]}.{cap[1]}) is below minimum "
            f"required sm_70 for modern PyTorch CUDA builds ({torch.__version__}). "
            f"Hardware architecture {gpu_name} cannot be qualified."
        )
        QUALIFICATION_RESULT["pytorch_cuda_compatible"] = False
        QUALIFICATION_RESULT["reasons"].append(reason)
        log(f"  CRITICAL FAILURE: {reason}")
        log("  HARD ABORT: Silent CPU fallback is strictly prohibited by Rule 7.")
        phase_failed("GPU_COMPATIBILITY_GATE", reason)
        return False

    QUALIFICATION_RESULT["pytorch_cuda_compatible"] = True
    log(f"  Architectural Compatibility: PASS ({sm_str} >= sm_70)")
    phase_complete("GPU_COMPATIBILITY_GATE")
    return True


# ============================================================
# PHASE 2: CUDA TENSOR SMOKE
# ============================================================
def phase2_cuda_tensor_smoke() -> bool:
    phase_start("CUDA_TENSOR_SMOKE")
    import torch

    try:
        device = torch.device("cuda:0")
        t_a = torch.randn(64, 64, device=device, dtype=torch.float32)
        t_b = torch.randn(64, 64, device=device, dtype=torch.float32)

        # Matrix multiply on GPU
        t_c = torch.matmul(t_a, t_b)
        torch.cuda.synchronize()

        # Strict device verification
        if not t_c.is_cuda or t_c.device.type != "cuda":
            QUALIFICATION_RESULT["cpu_fallback_detected"] = True
            QUALIFICATION_RESULT["cuda_tensor_smoke"] = "FAIL"
            QUALIFICATION_RESULT["reasons"].append("CUDA tensor smoke result did not reside on CUDA device.")
            phase_failed("CUDA_TENSOR_SMOKE", "Result not on CUDA")
            return False

        if not torch.isfinite(t_c).all().item():
            QUALIFICATION_RESULT["cuda_tensor_smoke"] = "FAIL"
            QUALIFICATION_RESULT["reasons"].append("CUDA tensor smoke output contains non-finite values.")
            phase_failed("CUDA_TENSOR_SMOKE", "Non-finite values in output")
            return False

        QUALIFICATION_RESULT["cuda_tensor_smoke"] = "PASS"
        log("  CUDA basic tensor allocation and GEMM execution: PASS (device=cuda:0, finite=True)")
        phase_complete("CUDA_TENSOR_SMOKE")
        return True

    except Exception as e:
        QUALIFICATION_RESULT["cuda_tensor_smoke"] = "FAIL"
        QUALIFICATION_RESULT["reasons"].append(f"CUDA tensor smoke failed with exception: {e}")
        phase_failed("CUDA_TENSOR_SMOKE", f"{e}\n{traceback.format_exc()}")
        return False


# ============================================================
# PHASE 3: REAL DATASET MOUNT & MANIFEST VERIFICATION
# ============================================================
def locate_corpus_root() -> Optional[Path]:
    candidates = [
        Path("/kaggle/input/datasets/dheeraj12237/ocean-sentinel-trujillo-corpus"),
        Path("/kaggle/input/ocean-sentinel-trujillo-corpus"),
    ]
    for c in candidates:
        if c.exists() and (c / "images" / "Oil").exists():
            return c.resolve()
    ki = Path("/kaggle/input")
    if ki.exists():
        for root, dirs, _ in os.walk(ki):
            if "images" in dirs and "masks" in dirs:
                cand = Path(root)
                if (cand / "images" / "Oil").exists():
                    return cand.resolve()
    return None


def phase3_dataset_and_manifest() -> Tuple[Optional[Path], Optional[Dict[str, Any]]]:
    phase_start("DATASET_AND_MANIFEST")
    corpus_root = locate_corpus_root()
    if corpus_root is None:
        err = "Could not locate Trujillo corpus under /kaggle/input"
        QUALIFICATION_RESULT["reasons"].append(err)
        phase_failed("DATASET_AND_MANIFEST", err)
        return None, None

    log(f"  Corpus root identified: {corpus_root}")

    # Locate spatial split manifest
    manifest_candidates = [
        corpus_root / "manifest" / "spatial_split_manifest.json",
        corpus_root / "metadata" / "spatial_split_manifest.json",
    ]
    manifest_path = None
    for m in manifest_candidates:
        if m.exists():
            manifest_path = m
            break

    if manifest_path is None:
        err = "Spatial split manifest not found in corpus"
        QUALIFICATION_RESULT["reasons"].append(err)
        phase_failed("DATASET_AND_MANIFEST", err)
        return corpus_root, None

    raw_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(raw_bytes).hexdigest().upper()
    manifest_data = json.loads(raw_bytes.decode("utf-8"))

    tiles = manifest_data.get("tiles", [])
    train_tiles = [t for t in tiles if t.get("split") == "train"]
    val_tiles = [t for t in tiles if t.get("split") == "val"]
    test_tiles = [t for t in tiles if t.get("split") == "test"]

    norm_stats = manifest_data.get("normalization_stats", {})
    actual_means = norm_stats.get("channel_means", [])
    actual_stds = norm_stats.get("channel_stds", [])

    means_ok = (
        len(actual_means) == 2
        and abs(actual_means[0] - CANONICAL_NORM_MEANS[0]) < 1e-6
        and abs(actual_means[1] - CANONICAL_NORM_MEANS[1]) < 1e-6
    )
    stds_ok = (
        len(actual_stds) == 2
        and abs(actual_stds[0] - CANONICAL_NORM_STDS[0]) < 1e-6
        and abs(actual_stds[1] - CANONICAL_NORM_STDS[1]) < 1e-6
    )

    counts_ok = (
        len(train_tiles) == EXPECTED_TRAIN_TILES
        and len(val_tiles) == EXPECTED_VAL_TILES
        and len(test_tiles) == EXPECTED_TEST_TILES
    )

    log(f"  Manifest SHA256:       {manifest_sha256}")
    log(f"  Tile counts:           train={len(train_tiles)}, val={len(val_tiles)}, test={len(test_tiles)} (match={counts_ok})")
    log(f"  Canonical Norm Means:  {actual_means} (match={means_ok})")
    log(f"  Canonical Norm Stds:   {actual_stds} (match={stds_ok})")

    if not (counts_ok and means_ok and stds_ok):
        err = "Manifest counts or normalization statistics mismatch canonical specification"
        QUALIFICATION_RESULT["reasons"].append(err)
        phase_failed("DATASET_AND_MANIFEST", err)
        return corpus_root, None

    phase_complete("DATASET_AND_MANIFEST")
    return corpus_root, manifest_data


# ============================================================
# PHASE 4: PRETRAINED CHECKPOINT PROVENANCE AUDIT
# ============================================================
def phase4_checkpoint_audit() -> bool:
    phase_start("CHECKPOINT_AUDIT")
    hub_cache = Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
    weight_file = hub_cache / EXPECTED_WEIGHT_FILENAME

    # Check external mounts first
    ki = Path("/kaggle/input")
    if ki.exists():
        for p in ki.rglob(EXPECTED_WEIGHT_FILENAME):
            if p.is_file() and p.stat().st_size == EXPECTED_WEIGHT_SIZE_BYTES:
                sha = hashlib.sha256(p.read_bytes()).hexdigest().upper()
                if sha == EXPECTED_WEIGHT_SHA256:
                    hub_cache.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(p, weight_file)
                    log(f"  Staged pre-cached weights from {p} to {weight_file}")
                    break

    # Trigger torchvision load/download
    try:
        from torchvision.models import resnet34, ResNet34_Weights
        _ = resnet34(weights=ResNet34_Weights.DEFAULT)

        if not weight_file.exists():
            err = f"Weight file {weight_file} not found after torchvision load"
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("CHECKPOINT_AUDIT", err)
            return False

        sz = weight_file.stat().st_size
        sha = hashlib.sha256(weight_file.read_bytes()).hexdigest().upper()

        size_ok = (sz == EXPECTED_WEIGHT_SIZE_BYTES)
        hash_ok = (sha == EXPECTED_WEIGHT_SHA256)

        log(f"  Checkpoint Path:    {weight_file}")
        log(f"  Size:               {sz} bytes (expected {EXPECTED_WEIGHT_SIZE_BYTES}) [match={size_ok}]")
        log(f"  SHA256:             {sha}")
        log(f"  Expected SHA256:    {EXPECTED_WEIGHT_SHA256} [match={hash_ok}]")

        if not (size_ok and hash_ok):
            err = f"Checkpoint verification failed: size_ok={size_ok}, hash_ok={hash_ok}"
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("CHECKPOINT_AUDIT", err)
            return False

        phase_complete("CHECKPOINT_AUDIT")
        return True

    except Exception as e:
        err = f"Checkpoint provenance audit exception: {e}"
        QUALIFICATION_RESULT["reasons"].append(err)
        phase_failed("CHECKPOINT_AUDIT", f"{err}\n{traceback.format_exc()}")
        return False


# ============================================================
# PHASE 5: REAL DATA PATH SAMPLE VALIDATION
# ============================================================
def phase5_real_data_sample(corpus_root: Path) -> Tuple[Optional[Any], Optional[Any]]:
    phase_start("REAL_DATA_SAMPLE")
    import torch
    from torch.utils.data import DataLoader

    try:
        from ocean_sentinel.ingestion.split import DatasetManifest, SplitName
        from ocean_sentinel.ingestion.dataset import TrujilloTileDataset

        manifest_path = corpus_root / "manifest" / "spatial_split_manifest.json"
        if not manifest_path.exists():
            manifest_path = corpus_root / "metadata" / "spatial_split_manifest.json"

        manifest_obj = DatasetManifest.load(manifest_path)
        ds_train = TrujilloTileDataset(
            manifest=manifest_obj,
            split=SplitName.TRAIN,
            normalize=True,
            data_root=corpus_root,
        )

        log(f"  TrujilloTileDataset initialized with {len(ds_train)} train tiles.")

        loader = DataLoader(ds_train, batch_size=2, shuffle=False, num_workers=0)
        batch_images, batch_masks = next(iter(loader))

        img_shape = list(batch_images.shape)
        mask_shape = list(batch_masks.shape)
        img_finite = bool(torch.isfinite(batch_images).all().item())
        mask_finite = bool(torch.isfinite(batch_masks).all().item())

        log(f"  Sample Batch Images Shape: {img_shape} (expected [2, 2, 512, 512])")
        log(f"  Sample Batch Masks Shape:  {mask_shape} (expected [2, 1, 512, 512])")
        log(f"  Values finite: images={img_finite}, masks={mask_finite}")

        shape_ok = (img_shape == [2, 2, 512, 512] and mask_shape == [2, 1, 512, 512])
        if not (shape_ok and img_finite and mask_finite):
            err = f"Real data batch contract failure: shape_ok={shape_ok}, finite={img_finite and mask_finite}"
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("REAL_DATA_SAMPLE", err)
            return None, None

        phase_complete("REAL_DATA_SAMPLE")
        return batch_images, batch_masks

    except Exception as e:
        err = f"Real data sample loading failed with exception: {e}"
        QUALIFICATION_RESULT["reasons"].append(err)
        phase_failed("REAL_DATA_SAMPLE", f"{err}\n{traceback.format_exc()}")
        return None, None


# ============================================================
# PHASE 6: EXACT CANONICAL MODEL GPU SMOKE
# ============================================================
def phase6_model_gpu_smoke(batch_images: Any) -> Tuple[bool, Optional[Any], Optional[Any]]:
    phase_start("MODEL_GPU_SMOKE")
    import torch

    try:
        from ocean_sentinel.ml.unet_resnet import ResNet34UNet, count_parameters

        # Instantiate exact canonical architecture
        model = ResNet34UNet(
            in_channels=2,
            num_classes=1,
            pretrained=True,
            adaptation_method=EXPECTED_ADAPTATION_METHOD,
        )

        param_counts = count_parameters(model)
        total_p = param_counts["total"]
        trainable_p = param_counts["trainable"]

        param_ok = (total_p == EXPECTED_PARAM_COUNT and trainable_p == EXPECTED_PARAM_COUNT)
        adaptation_ok = (model.adaptation_method == EXPECTED_ADAPTATION_METHOD)

        log(f"  Architecture:         ResNet34UNet")
        log(f"  Total Parameters:     {total_p:,} (expected {EXPECTED_PARAM_COUNT:,}) [match={param_ok}]")
        log(f"  Adaptation Method:    {model.adaptation_method} [match={adaptation_ok}]")

        if not (param_ok and adaptation_ok):
            err = f"Canonical model architecture verification mismatch: param_ok={param_ok}, adapt_ok={adaptation_ok}"
            QUALIFICATION_RESULT["model_gpu_smoke"] = "FAIL"
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("MODEL_GPU_SMOKE", err)
            return False, None, None

        # STRICT GPU ALLOCATION: target cuda:0
        target_device = torch.device("cuda:0")
        model = model.to(target_device)

        # Verify all parameters reside on CUDA
        non_cuda_params = [name for name, p in model.named_parameters() if p.device.type != "cuda"]
        if non_cuda_params:
            QUALIFICATION_RESULT["cpu_fallback_detected"] = True
            QUALIFICATION_RESULT["model_gpu_smoke"] = "FAIL"
            err = f"Silent CPU fallback detected! Parameters not on CUDA: {non_cuda_params[:5]}"
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("MODEL_GPU_SMOKE", err)
            return False, None, None

        # Transfer real input to GPU
        inputs = batch_images.to(target_device)
        if inputs.device.type != "cuda":
            QUALIFICATION_RESULT["cpu_fallback_detected"] = True
            QUALIFICATION_RESULT["model_gpu_smoke"] = "FAIL"
            err = "Inputs failed to allocate to CUDA device."
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("MODEL_GPU_SMOKE", err)
            return False, None, None

        # Execute forward pass
        model.train()  # Keep in train mode to test trainable gradient graph
        logits = model(inputs)
        torch.cuda.synchronize()

        # Verify output properties
        if logits.device.type != "cuda":
            QUALIFICATION_RESULT["cpu_fallback_detected"] = True
            QUALIFICATION_RESULT["model_gpu_smoke"] = "FAIL"
            err = "Model forward pass output tensor does not reside on CUDA."
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("MODEL_GPU_SMOKE", err)
            return False, None, None

        out_shape = list(logits.shape)
        out_finite = bool(torch.isfinite(logits).all().item())
        shape_ok = (out_shape == [2, 1, 512, 512])

        log(f"  Forward Pass Device:  {logits.device} (is_cuda={logits.is_cuda})")
        log(f"  Forward Output Shape: {out_shape} [match={shape_ok}]")
        log(f"  Forward Output Finite:{out_finite}")

        if not (shape_ok and out_finite):
            err = f"Model forward pass contract failure: shape_ok={shape_ok}, finite={out_finite}"
            QUALIFICATION_RESULT["model_gpu_smoke"] = "FAIL"
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("MODEL_GPU_SMOKE", err)
            return False, None, None

        QUALIFICATION_RESULT["model_gpu_smoke"] = "PASS"
        phase_complete("MODEL_GPU_SMOKE")
        return True, model, logits

    except Exception as e:
        QUALIFICATION_RESULT["model_gpu_smoke"] = "FAIL"
        err = f"Model GPU smoke failed with exception: {e}"
        QUALIFICATION_RESULT["reasons"].append(err)
        phase_failed("MODEL_GPU_SMOKE", f"{err}\n{traceback.format_exc()}")
        return False, None, None


# ============================================================
# PHASE 7: EXACT LOSS + BACKWARD GPU SMOKE
# ============================================================
def phase7_loss_backward_gpu_smoke(
    model: Any,
    logits: Any,
    batch_masks: Any,
) -> bool:
    phase_start("LOSS_BACKWARD_GPU_SMOKE")
    import torch

    try:
        from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss

        target_device = torch.device("cuda:0")
        targets = batch_masks.to(target_device)

        if targets.device.type != "cuda":
            QUALIFICATION_RESULT["cpu_fallback_detected"] = True
            QUALIFICATION_RESULT["loss_backward_gpu_smoke"] = "FAIL"
            err = "Targets failed to allocate to CUDA device."
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("LOSS_BACKWARD_GPU_SMOKE", err)
            return False

        # Canonical loss formulation: 0.5 * BCE + 0.5 * SoftDice (smooth=1.0)
        criterion = CombinedBCEAndDiceLoss(
            bce_weight=0.5,
            dice_weight=0.5,
            smooth=1.0,
        )

        loss = criterion(logits, targets)

        if loss.device.type != "cuda":
            QUALIFICATION_RESULT["cpu_fallback_detected"] = True
            QUALIFICATION_RESULT["loss_backward_gpu_smoke"] = "FAIL"
            err = f"Loss tensor device is {loss.device}, expected CUDA."
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("LOSS_BACKWARD_GPU_SMOKE", err)
            return False

        loss_val = loss.item()
        loss_finite = bool(torch.isfinite(loss).item())
        log(f"  Loss Value:           {loss_val:.6f} (finite={loss_finite}, device={loss.device})")

        if not loss_finite:
            QUALIFICATION_RESULT["loss_backward_gpu_smoke"] = "FAIL"
            err = "Loss value is NaN or Infinite."
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("LOSS_BACKWARD_GPU_SMOKE", err)
            return False

        # Backward pass on GPU
        loss.backward()
        torch.cuda.synchronize()

        # Verify gradient tensors
        # Inspect representative parameters: first layer, middle encoder, decoder head
        grad_verified = 0
        non_cuda_grads = []
        nan_grads = []

        for name, p in model.named_parameters():
            if p.requires_grad:
                if p.grad is None:
                    continue
                grad_verified += 1
                if p.grad.device.type != "cuda":
                    non_cuda_grads.append(name)
                if not torch.isfinite(p.grad).all().item():
                    nan_grads.append(name)

        log(f"  Trainable Parameters with Verified Gradients: {grad_verified}")
        log(f"  Non-CUDA Gradients Count:                     {len(non_cuda_grads)}")
        log(f"  Non-Finite Gradients Count:                   {len(nan_grads)}")

        if grad_verified == 0:
            QUALIFICATION_RESULT["loss_backward_gpu_smoke"] = "FAIL"
            err = "Zero parameters received gradients after backward pass."
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("LOSS_BACKWARD_GPU_SMOKE", err)
            return False

        if non_cuda_grads:
            QUALIFICATION_RESULT["cpu_fallback_detected"] = True
            QUALIFICATION_RESULT["loss_backward_gpu_smoke"] = "FAIL"
            err = f"Gradients found on CPU instead of CUDA: {non_cuda_grads[:5]}"
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("LOSS_BACKWARD_GPU_SMOKE", err)
            return False

        if nan_grads:
            QUALIFICATION_RESULT["loss_backward_gpu_smoke"] = "FAIL"
            err = f"NaN/Inf gradients detected: {nan_grads[:5]}"
            QUALIFICATION_RESULT["reasons"].append(err)
            phase_failed("LOSS_BACKWARD_GPU_SMOKE", err)
            return False

        # CRITICAL HARD REQUIREMENT: ZERO OPTIMIZER STEPS
        QUALIFICATION_RESULT["optimizer_step_count"] = 0
        log(f"  OPTIMIZER_STEP_COUNT = {QUALIFICATION_RESULT['optimizer_step_count']} (STRICT ZERO)")

        QUALIFICATION_RESULT["loss_backward_gpu_smoke"] = "PASS"
        phase_complete("LOSS_BACKWARD_GPU_SMOKE")
        return True

    except Exception as e:
        QUALIFICATION_RESULT["loss_backward_gpu_smoke"] = "FAIL"
        err = f"Loss backward GPU smoke failed with exception: {e}"
        QUALIFICATION_RESULT["reasons"].append(err)
        phase_failed("LOSS_BACKWARD_GPU_SMOKE", f"{err}\n{traceback.format_exc()}")
        return False


# ============================================================
# EVALUATION & ARTIFACT GENERATION
# ============================================================
def evaluate_final_decision() -> None:
    # Try importing evaluate_gpu_qualification from ocean_sentinel
    try:
        from ocean_sentinel.ml.gpu_qualification import (
            GPUQualificationState,
            evaluate_gpu_qualification,
        )
        state = GPUQualificationState(
            gpu_present=QUALIFICATION_RESULT["gpu_present"],
            gpu_name=QUALIFICATION_RESULT["gpu_name"],
            gpu_compute_capability=QUALIFICATION_RESULT["gpu_compute_capability"],
            pytorch_version=QUALIFICATION_RESULT["pytorch_version"],
            cuda_runtime=QUALIFICATION_RESULT["cuda_runtime"],
            pytorch_cuda_compatible=QUALIFICATION_RESULT["pytorch_cuda_compatible"],
            cuda_tensor_smoke=QUALIFICATION_RESULT["cuda_tensor_smoke"],
            model_gpu_smoke=QUALIFICATION_RESULT["model_gpu_smoke"],
            loss_backward_gpu_smoke=QUALIFICATION_RESULT["loss_backward_gpu_smoke"],
            cpu_fallback_detected=QUALIFICATION_RESULT["cpu_fallback_detected"],
            optimizer_step_count=QUALIFICATION_RESULT["optimizer_step_count"],
            warnings=QUALIFICATION_RESULT["warnings"],
        )
        evaluated = evaluate_gpu_qualification(state)
        QUALIFICATION_RESULT["training_allowed"] = evaluated.training_allowed
        QUALIFICATION_RESULT["gate_decision"] = evaluated.gate_decision
        QUALIFICATION_RESULT["reasons"] = evaluated.reasons
    except Exception as e:
        # Fallback inline evaluation
        reasons = []
        if not QUALIFICATION_RESULT["gpu_present"]:
            reasons.append("GPU is not present or CUDA is unavailable.")
        if not QUALIFICATION_RESULT["pytorch_cuda_compatible"]:
            reasons.append(f"GPU architecture ({QUALIFICATION_RESULT['gpu_compute_capability']}) is incompatible.")
        if QUALIFICATION_RESULT["cuda_tensor_smoke"] != "PASS":
            reasons.append(f"CUDA tensor smoke is {QUALIFICATION_RESULT['cuda_tensor_smoke']}")
        if QUALIFICATION_RESULT["model_gpu_smoke"] != "PASS":
            reasons.append(f"Model GPU smoke is {QUALIFICATION_RESULT['model_gpu_smoke']}")
        if QUALIFICATION_RESULT["loss_backward_gpu_smoke"] != "PASS":
            reasons.append(f"Loss backward smoke is {QUALIFICATION_RESULT['loss_backward_gpu_smoke']}")
        if QUALIFICATION_RESULT["cpu_fallback_detected"]:
            reasons.append("CPU fallback detected.")
        if QUALIFICATION_RESULT["optimizer_step_count"] != 0:
            reasons.append(f"Optimizer steps = {QUALIFICATION_RESULT['optimizer_step_count']}")

        QUALIFICATION_RESULT["reasons"] = reasons
        if len(reasons) == 0:
            QUALIFICATION_RESULT["training_allowed"] = True
            QUALIFICATION_RESULT["gate_decision"] = "PASS WITH WARNINGS" if QUALIFICATION_RESULT["warnings"] else "PASS"
        else:
            QUALIFICATION_RESULT["training_allowed"] = False
            QUALIFICATION_RESULT["gate_decision"] = "FAIL"


def write_evidence_artifacts(out_dir: Path, env_info: Dict[str, Any]) -> None:
    # 1. qualification.json
    qual_path = out_dir / "qualification.json"
    qual_path.write_text(json.dumps(QUALIFICATION_RESULT, indent=2), encoding="utf-8")
    log(f"Artifact written: {qual_path}")

    # 2. environment.txt
    env_path = out_dir / "environment.txt"
    env_lines = [f"{k}: {v}" for k, v in sorted(env_info.items())]
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    log(f"Artifact written: {env_path}")

    # 3. gpu.txt
    gpu_path = out_dir / "gpu.txt"
    gpu_lines = [
        f"GPU_PRESENT={QUALIFICATION_RESULT['gpu_present']}",
        f"GPU_NAME={QUALIFICATION_RESULT['gpu_name']}",
        f"COMPUTE_CAPABILITY={QUALIFICATION_RESULT['gpu_compute_capability']}",
        f"PYTORCH_VERSION={QUALIFICATION_RESULT['pytorch_version']}",
        f"CUDA_RUNTIME={QUALIFICATION_RESULT['cuda_runtime']}",
        f"PYTORCH_CUDA_COMPATIBLE={QUALIFICATION_RESULT['pytorch_cuda_compatible']}",
        f"CUDA_TENSOR_SMOKE={QUALIFICATION_RESULT['cuda_tensor_smoke']}",
        f"MODEL_GPU_SMOKE={QUALIFICATION_RESULT['model_gpu_smoke']}",
        f"LOSS_BACKWARD_GPU_SMOKE={QUALIFICATION_RESULT['loss_backward_gpu_smoke']}",
        f"CPU_FALLBACK_DETECTED={QUALIFICATION_RESULT['cpu_fallback_detected']}",
        f"OPTIMIZER_STEP_COUNT={QUALIFICATION_RESULT['optimizer_step_count']}",
        f"TRAINING_ALLOWED={QUALIFICATION_RESULT['training_allowed']}",
        f"GATE_DECISION={QUALIFICATION_RESULT['gate_decision']}",
    ]
    gpu_path.write_text("\n".join(gpu_lines) + "\n", encoding="utf-8")
    log(f"Artifact written: {gpu_path}")

    # 4. run_state.json
    run_state_path = out_dir / "run_state.json"
    run_state = {
        "gate_id": GATE_ID,
        "start_utc": START_UTC,
        "end_utc": utcnow(),
        "qualification": QUALIFICATION_RESULT,
        "execution_log": EXECUTION_LOG,
    }
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")
    log(f"Artifact written: {run_state_path}")


# ============================================================
# MAIN ENTRYPOINT
# ============================================================
def main() -> int:
    log(f"============================================================")
    log(f"STARTING {GATE_ID} - ACTUAL CLOUD GPU QUALIFICATION")
    log(f"============================================================")

    out_dir = get_output_dir()
    log(f"Output directory: {out_dir}")

    # Setup import path for ocean_sentinel package
    setup_import_path()

    # Phase 0: Boot & System Environment
    env_info = phase0_boot()

    # Phase 1: Hard GPU Compatibility Gate
    compat = phase1_gpu_compatibility(env_info)
    if not compat:
        log("Hard GPU compatibility gate failed. Terminating before any tensor/model execution.")
        evaluate_final_decision()
        write_evidence_artifacts(out_dir, env_info)
        log(f"FINAL DECISION: GATE_DECISION={QUALIFICATION_RESULT['gate_decision']}, TRAINING_ALLOWED={QUALIFICATION_RESULT['training_allowed']}")
        return 1

    # Phase 2: CUDA Tensor Smoke
    cuda_smoke_ok = phase2_cuda_tensor_smoke()
    if not cuda_smoke_ok:
        evaluate_final_decision()
        write_evidence_artifacts(out_dir, env_info)
        return 1

    # Phase 3: Dataset & Manifest Mount
    corpus_root, manifest_data = phase3_dataset_and_manifest()
    if corpus_root is None or manifest_data is None:
        evaluate_final_decision()
        write_evidence_artifacts(out_dir, env_info)
        return 1

    # Phase 4: Pretrained Checkpoint Provenance Audit
    chkpt_ok = phase4_checkpoint_audit()
    if not chkpt_ok:
        evaluate_final_decision()
        write_evidence_artifacts(out_dir, env_info)
        return 1

    # Phase 5: Real Data Sample Validation
    batch_images, batch_masks = phase5_real_data_sample(corpus_root)
    if batch_images is None or batch_masks is None:
        evaluate_final_decision()
        write_evidence_artifacts(out_dir, env_info)
        return 1

    # Phase 6: Canonical Model GPU Smoke
    model_ok, model, logits = phase6_model_gpu_smoke(batch_images)
    if not model_ok or model is None or logits is None:
        evaluate_final_decision()
        write_evidence_artifacts(out_dir, env_info)
        return 1

    # Phase 7: Canonical Loss + Backward GPU Smoke
    loss_ok = phase7_loss_backward_gpu_smoke(model, logits, batch_masks)
    if not loss_ok:
        evaluate_final_decision()
        write_evidence_artifacts(out_dir, env_info)
        return 1

    # Final Evaluation & Artifacts
    evaluate_final_decision()
    write_evidence_artifacts(out_dir, env_info)

    log(f"============================================================")
    log(f"QUALIFICATION COMPLETE")
    log(f"  GATE_DECISION:        {QUALIFICATION_RESULT['gate_decision']}")
    log(f"  TRAINING_ALLOWED:     {QUALIFICATION_RESULT['training_allowed']}")
    log(f"  OPTIMIZER_STEP_COUNT: {QUALIFICATION_RESULT['optimizer_step_count']}")
    log(f"============================================================")

    return 0 if QUALIFICATION_RESULT["training_allowed"] else 1


if __name__ == "__main__":
    sys.exit(main())
