"""GPU Qualification & Decision Boundary Architecture for Ocean Sentinel.

Implements the forensic qualification boundary required by Gate 4.3C-A:
Establishes whether the actual execution environment is qualified to run
the canonical EXP-01 training stack on GPU with zero optimizer steps and
strict prohibition of silent CPU fallback.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import platform
import torch


@dataclass
class GPUQualificationState:
    """State machine container for GPU qualification and training authorization."""

    gpu_present: bool = False
    gpu_name: str = "UNKNOWN"
    gpu_compute_capability: str = "none"
    gpu_count: int = 0
    pytorch_version: str = "UNKNOWN"
    cuda_runtime: str = "UNKNOWN"
    pytorch_cuda_compatible: bool = False
    cuda_tensor_smoke: str = "NOT_VERIFIED"       # PASS, FAIL, NOT_VERIFIED
    model_gpu_smoke: str = "NOT_VERIFIED"         # PASS, FAIL, NOT_VERIFIED
    loss_backward_gpu_smoke: str = "NOT_VERIFIED" # PASS, FAIL, NOT_VERIFIED
    cpu_fallback_detected: bool = False
    optimizer_step_count: int = 0
    training_allowed: bool = False
    gate_decision: str = "NOT_VERIFIED"          # PASS, PASS_WITH_WARNINGS, FAIL, NOT_VERIFIED
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def check_compute_capability_compatibility(
    compute_capability: Tuple[int, int],
    pytorch_version_str: str,
) -> Tuple[bool, str]:
    """Check if compute capability is supported by the installed PyTorch build.

    PyTorch 2.10+cu128 requires minimum sm_70 (Volta/Turing+).
    Older architectures (e.g. Tesla P100, sm_60) trigger fatal execution errors
    or unsupported-architecture warnings and cannot be qualified for GPU training.
    """
    major, minor = compute_capability
    sm_val = major * 10 + minor

    # Minimum compute capability requirement
    # sm_70: Volta (V100)
    # sm_75: Turing (T4)
    # sm_80/sm_86: Ampere (A100, RTX 30xx)
    # sm_89/sm_90: Ada/Hopper (RTX 40xx, H100)
    if major < 7:
        return False, (
            f"GPU compute capability sm_{sm_val} ({major}.{minor}) is below minimum "
            f"required sm_70 for modern PyTorch CUDA builds ({pytorch_version_str})."
        )

    return True, f"GPU compute capability sm_{sm_val} is supported (sm_{sm_val} >= sm_70)."


def probe_gpu_hardware() -> Dict[str, Any]:
    """Inspect local hardware, PyTorch version, and CUDA runtime availability."""
    pt_ver = torch.__version__
    cuda_ver = torch.version.cuda or "none"
    gpu_available = torch.cuda.is_available()
    gpu_count = torch.cuda.device_count() if gpu_available else 0

    info: Dict[str, Any] = {
        "pytorch_version": pt_ver,
        "cuda_runtime": cuda_ver,
        "gpu_available": gpu_available,
        "gpu_count": gpu_count,
        "gpu_name": "none",
        "compute_capability": (0, 0),
        "sm_string": "none",
        "compatible": False,
        "reason": "CUDA is not available.",
    }

    if gpu_available and gpu_count > 0:
        name = torch.cuda.get_device_name(0)
        cap = torch.cuda.get_device_capability(0)
        sm_str = f"sm_{cap[0]}{cap[1]}"
        compat, reason = check_compute_capability_compatibility(cap, pt_ver)

        info.update({
            "gpu_name": name,
            "compute_capability": cap,
            "sm_string": sm_str,
            "compatible": compat,
            "reason": reason,
        })

    return info


def evaluate_gpu_qualification(state: GPUQualificationState) -> GPUQualificationState:
    """Deterministically evaluate whether training is authorized based on qualification evidence.

    TRAINING_ALLOWED = (
        GPU_PRESENT
        AND PYTORCH_CUDA_COMPATIBLE
        AND CUDA_TENSOR_SMOKE == 'PASS'
        AND MODEL_GPU_SMOKE == 'PASS'
        AND LOSS_BACKWARD_GPU_SMOKE == 'PASS'
        AND NOT CPU_FALLBACK_DETECTED
        AND OPTIMIZER_STEP_COUNT == 0
    )
    """
    reasons = []

    if not state.gpu_present:
        reasons.append("GPU is not present or CUDA is unavailable.")
    if not state.pytorch_cuda_compatible:
        reasons.append(f"GPU architecture ({state.gpu_compute_capability}) is incompatible with PyTorch {state.pytorch_version}.")
    if state.cuda_tensor_smoke != "PASS":
        reasons.append(f"CUDA tensor smoke test status is {state.cuda_tensor_smoke} (must be PASS).")
    if state.model_gpu_smoke != "PASS":
        reasons.append(f"Model GPU smoke test status is {state.model_gpu_smoke} (must be PASS).")
    if state.loss_backward_gpu_smoke != "PASS":
        reasons.append(f"Loss backward GPU smoke test status is {state.loss_backward_gpu_smoke} (must be PASS).")
    if state.cpu_fallback_detected:
        reasons.append("CPU fallback was detected; silent CPU fallback is strictly prohibited.")
    if state.optimizer_step_count != 0:
        reasons.append(f"Optimizer step count is {state.optimizer_step_count} (must be strictly 0 during qualification).")

    state.reasons = reasons

    # Decision logic
    if len(reasons) == 0:
        state.training_allowed = True
        if len(state.warnings) > 0:
            state.gate_decision = "PASS WITH WARNINGS"
        else:
            state.gate_decision = "PASS"
    else:
        state.training_allowed = False
        # If any check was attempted and failed
        if any(
            x in ["FAIL"] for x in [
                state.cuda_tensor_smoke,
                state.model_gpu_smoke,
                state.loss_backward_gpu_smoke,
            ]
        ) or (state.gpu_present and not state.pytorch_cuda_compatible) or state.cpu_fallback_detected or state.optimizer_step_count > 0:
            state.gate_decision = "FAIL"
        else:
            state.gate_decision = "NOT VERIFIED"

    return state
