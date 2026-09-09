"""Unit tests for GPU qualification decision boundary logic.

Gate 4.3C-A Phase 10: Regression tests for GPU qualification state machine.
Covers:
1. no GPU -> training denied
2. incompatible GPU (sm < 70) -> training denied
3. CUDA tensor smoke failure -> training denied
4. model GPU smoke failure -> training denied
5. backward failure -> training denied
6. CPU fallback detected -> training denied
7. all prerequisites proven -> training allowed
8. optimizer step count > 0 -> training denied
9. warnings presence -> PASS WITH WARNINGS
10. compute capability evaluation logic
"""

import pytest

from ocean_sentinel.ml.gpu_qualification import (
    GPUQualificationState,
    check_compute_capability_compatibility,
    evaluate_gpu_qualification,
    probe_gpu_hardware,
)


@pytest.mark.unit
def test_no_gpu_denies_training():
    """When GPU is not present, training must be denied and state marked NOT VERIFIED."""
    state = GPUQualificationState(
        gpu_present=False,
        gpu_name="none",
        gpu_compute_capability="none",
        pytorch_version="2.10.0+cu128",
        cuda_runtime="none",
        pytorch_cuda_compatible=False,
    )
    result = evaluate_gpu_qualification(state)

    assert not result.training_allowed
    assert result.gate_decision == "NOT VERIFIED"
    assert any("GPU is not present" in r for r in result.reasons)


@pytest.mark.unit
def test_incompatible_gpu_denies_training():
    """When GPU architecture is incompatible (e.g. sm_60 P100 on cu128), training is FAIL."""
    state = GPUQualificationState(
        gpu_present=True,
        gpu_name="Tesla P100-PCIE-16GB",
        gpu_compute_capability="sm_60",
        pytorch_version="2.10.0+cu128",
        cuda_runtime="12.8",
        pytorch_cuda_compatible=False,  # Incompatible
        cuda_tensor_smoke="NOT_VERIFIED",
    )
    result = evaluate_gpu_qualification(state)

    assert not result.training_allowed
    assert result.gate_decision == "FAIL"
    assert any("incompatible" in r for r in result.reasons)


@pytest.mark.unit
def test_cuda_smoke_failure_denies_training():
    """When CUDA tensor smoke fails, training must be denied with FAIL."""
    state = GPUQualificationState(
        gpu_present=True,
        gpu_name="Tesla T4",
        gpu_compute_capability="sm_75",
        pytorch_version="2.10.0+cu128",
        cuda_runtime="12.8",
        pytorch_cuda_compatible=True,
        cuda_tensor_smoke="FAIL",
        model_gpu_smoke="NOT_VERIFIED",
        loss_backward_gpu_smoke="NOT_VERIFIED",
        cpu_fallback_detected=False,
        optimizer_step_count=0,
    )
    result = evaluate_gpu_qualification(state)

    assert not result.training_allowed
    assert result.gate_decision == "FAIL"
    assert any("CUDA tensor smoke test status is FAIL" in r for r in result.reasons)


@pytest.mark.unit
def test_model_gpu_smoke_failure_denies_training():
    """When Model GPU smoke fails, training must be denied with FAIL."""
    state = GPUQualificationState(
        gpu_present=True,
        gpu_name="Tesla T4",
        gpu_compute_capability="sm_75",
        pytorch_version="2.10.0+cu128",
        cuda_runtime="12.8",
        pytorch_cuda_compatible=True,
        cuda_tensor_smoke="PASS",
        model_gpu_smoke="FAIL",
        loss_backward_gpu_smoke="NOT_VERIFIED",
        cpu_fallback_detected=False,
        optimizer_step_count=0,
    )
    result = evaluate_gpu_qualification(state)

    assert not result.training_allowed
    assert result.gate_decision == "FAIL"
    assert any("Model GPU smoke test status is FAIL" in r for r in result.reasons)


@pytest.mark.unit
def test_loss_backward_smoke_failure_denies_training():
    """When backward pass fails, training must be denied with FAIL."""
    state = GPUQualificationState(
        gpu_present=True,
        gpu_name="Tesla T4",
        gpu_compute_capability="sm_75",
        pytorch_version="2.10.0+cu128",
        cuda_runtime="12.8",
        pytorch_cuda_compatible=True,
        cuda_tensor_smoke="PASS",
        model_gpu_smoke="PASS",
        loss_backward_gpu_smoke="FAIL",
        cpu_fallback_detected=False,
        optimizer_step_count=0,
    )
    result = evaluate_gpu_qualification(state)

    assert not result.training_allowed
    assert result.gate_decision == "FAIL"
    assert any("Loss backward GPU smoke test status is FAIL" in r for r in result.reasons)


@pytest.mark.unit
def test_cpu_fallback_denies_training():
    """When silent CPU fallback is detected, training must be denied with FAIL."""
    state = GPUQualificationState(
        gpu_present=True,
        gpu_name="Tesla T4",
        gpu_compute_capability="sm_75",
        pytorch_version="2.10.0+cu128",
        cuda_runtime="12.8",
        pytorch_cuda_compatible=True,
        cuda_tensor_smoke="PASS",
        model_gpu_smoke="PASS",
        loss_backward_gpu_smoke="PASS",
        cpu_fallback_detected=True,  # Fallback occurred!
        optimizer_step_count=0,
    )
    result = evaluate_gpu_qualification(state)

    assert not result.training_allowed
    assert result.gate_decision == "FAIL"
    assert any("CPU fallback was detected" in r for r in result.reasons)


@pytest.mark.unit
def test_optimizer_step_violation_denies_training():
    """If an optimizer step occurs during qualification, training must be denied with FAIL."""
    state = GPUQualificationState(
        gpu_present=True,
        gpu_name="Tesla T4",
        gpu_compute_capability="sm_75",
        pytorch_version="2.10.0+cu128",
        cuda_runtime="12.8",
        pytorch_cuda_compatible=True,
        cuda_tensor_smoke="PASS",
        model_gpu_smoke="PASS",
        loss_backward_gpu_smoke="PASS",
        cpu_fallback_detected=False,
        optimizer_step_count=1,  # Violation!
    )
    result = evaluate_gpu_qualification(state)

    assert not result.training_allowed
    assert result.gate_decision == "FAIL"
    assert any("Optimizer step count is 1" in r for r in result.reasons)


@pytest.mark.unit
def test_all_prerequisites_proven_allows_training():
    """When all prerequisites pass with 0 optimizer steps and 0 fallback, training is PASS."""
    state = GPUQualificationState(
        gpu_present=True,
        gpu_name="Tesla T4",
        gpu_compute_capability="sm_75",
        gpu_count=1,
        pytorch_version="2.10.0+cu128",
        cuda_runtime="12.8",
        pytorch_cuda_compatible=True,
        cuda_tensor_smoke="PASS",
        model_gpu_smoke="PASS",
        loss_backward_gpu_smoke="PASS",
        cpu_fallback_detected=False,
        optimizer_step_count=0,
    )
    result = evaluate_gpu_qualification(state)

    assert result.training_allowed
    assert result.gate_decision == "PASS"
    assert len(result.reasons) == 0


@pytest.mark.unit
def test_all_proven_with_warnings_allows_training():
    """When all prerequisites pass but non-fatal warnings exist, decision is PASS WITH WARNINGS."""
    state = GPUQualificationState(
        gpu_present=True,
        gpu_name="Tesla T4",
        gpu_compute_capability="sm_75",
        gpu_count=1,
        pytorch_version="2.10.0+cu128",
        cuda_runtime="12.8",
        pytorch_cuda_compatible=True,
        cuda_tensor_smoke="PASS",
        model_gpu_smoke="PASS",
        loss_backward_gpu_smoke="PASS",
        cpu_fallback_detected=False,
        optimizer_step_count=0,
        warnings=["DataLoader num_workers warning: set to 2 for cloud container"],
    )
    result = evaluate_gpu_qualification(state)

    assert result.training_allowed
    assert result.gate_decision == "PASS WITH WARNINGS"
    assert len(result.reasons) == 0


@pytest.mark.unit
def test_compute_capability_thresholds():
    """Test compute capability compatibility thresholds."""
    # P100: sm_60 -> Incompatible
    compat, reason = check_compute_capability_compatibility((6, 0), "2.10.0+cu128")
    assert not compat
    assert "below minimum required sm_70" in reason

    # V100: sm_70 -> Compatible
    compat, reason = check_compute_capability_compatibility((7, 0), "2.10.0+cu128")
    assert compat
    assert "sm_70 >= sm_70" in reason

    # T4: sm_75 -> Compatible
    compat, reason = check_compute_capability_compatibility((7, 5), "2.10.0+cu128")
    assert compat
    assert "sm_75 >= sm_70" in reason

    # A100: sm_80 -> Compatible
    compat, reason = check_compute_capability_compatibility((8, 0), "2.10.0+cu128")
    assert compat
    assert "sm_80 >= sm_70" in reason


@pytest.mark.unit
def test_probe_gpu_hardware_structure():
    """Test probe_gpu_hardware returns expected dictionary schema."""
    info = probe_gpu_hardware()
    assert "pytorch_version" in info
    assert "cuda_runtime" in info
    assert "gpu_available" in info
    assert "gpu_count" in info
    assert "compatible" in info
