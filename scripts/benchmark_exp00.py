"""EXP-00 Hardware & Real-Data Microbenchmark for Ocean Sentinel.

Measures:
1. CPU baseline forward & backward latency.
2. CUDA environment verification & hardware capabilities.
3. Model initialization & parameter counts.
4. Synthetic CUDA forward/backward benchmarks across batch sizes (1, 2, 4, 8) in FP32 and AMP FP16.
5. Peak allocated and reserved VRAM per batch size.
6. Gradient accumulation feasibility (batch 4, accumulation 2).
7. AMP numerical stability validation.
8. Real-data DataLoader throughput on Trujillo tiles (100 batches).
9. Real-data end-to-end training step throughput (DataLoader + Model + AMP + Backward).

Saves machine-readable results to data/metadata/trujillo_2024/exp00_benchmark_results.json.
"""

from __future__ import annotations

import gc
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import torch
from torch.utils.data import DataLoader

# Add src to sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset  # noqa: E402
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName  # noqa: E402
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss  # noqa: E402
from ocean_sentinel.ml.unet_resnet import (  # noqa: E402
    ResNet34UNet,
    VanillaUNet,
    count_parameters,
)


def get_vram_mb() -> Dict[str, float]:
    """Get current allocated and reserved CUDA VRAM in MB."""
    if not torch.cuda.is_available():
        return {"allocated_mb": 0.0, "reserved_mb": 0.0}
    return {
        "allocated_mb": torch.cuda.memory_allocated() / (1024**2),
        "reserved_mb": torch.cuda.memory_reserved() / (1024**2),
        "max_allocated_mb": torch.cuda.max_memory_allocated() / (1024**2),
        "max_reserved_mb": torch.cuda.max_memory_reserved() / (1024**2),
    }


def reset_cuda_memory() -> None:
    """Clear CUDA cache and reset peak statistics."""
    if torch.cuda.is_available():
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()


def benchmark_cpu_baseline() -> Dict[str, Any]:
    """Measure CPU baseline forward and backward latency on a single 512x512 tile."""
    print("\n" + "=" * 60)
    print("1. CPU BASELINE BENCHMARK")
    print("=" * 60)

    model = ResNet34UNet(pretrained=False).cpu()
    criterion = CombinedBCEAndDiceLoss().cpu()

    x = torch.randn(1, 2, 512, 512)
    y = torch.randint(0, 2, (1, 1, 512, 512)).float()

    # Warmup
    out = model(x)
    loss = criterion(out, y)
    loss.backward()

    # Timed runs
    n_iters = 5
    fwd_times: List[float] = []
    bwd_times: List[float] = []

    for _ in range(n_iters):
        model.zero_grad(set_to_none=True)
        t0 = time.perf_counter()
        out = model(x)
        t1 = time.perf_counter()
        loss = criterion(out, y)
        loss.backward()
        t2 = time.perf_counter()
        fwd_times.append(t1 - t0)
        bwd_times.append(t2 - t1)

    mean_fwd = sum(fwd_times) / len(fwd_times)
    mean_bwd = sum(bwd_times) / len(bwd_times)
    fps = 1.0 / (mean_fwd + mean_bwd)

    print(f"  CPU Forward latency:  {mean_fwd * 1000:.2f} ms")
    print(f"  CPU Backward latency: {mean_bwd * 1000:.2f} ms")
    print(f"  CPU Total step time:  {(mean_fwd + mean_bwd) * 1000:.2f} ms ({fps:.2f} samples/sec)")

    return {
        "device": "cpu",
        "batch_size": 1,
        "forward_ms": round(mean_fwd * 1000, 2),
        "backward_ms": round(mean_bwd * 1000, 2),
        "total_step_ms": round((mean_fwd + mean_bwd) * 1000, 2),
        "samples_per_sec": round(fps, 2),
    }


def benchmark_cuda_synthetic(
    batch_sizes: List[int] = [1, 2, 4, 8],
    warmup: int = 3,
    iterations: int = 10,
) -> List[Dict[str, Any]]:
    """Benchmark synthetic CUDA forward and backward passes across batch sizes."""
    print("\n" + "=" * 60)
    print("2. CUDA SYNTHETIC BATCH-SIZE SWEEP & VRAM PROFILING")
    print("=" * 60)

    if not torch.cuda.is_available():
        print("  CUDA is NOT available. Skipping CUDA benchmarks.")
        return []

    device = torch.device("cuda:0")
    total_vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024**2)
    print(f"  Target Device: {torch.cuda.get_device_name(0)}")
    print(f"  Total VRAM:    {total_vram_mb:.1f} MB")

    results: List[Dict[str, Any]] = []

    for amp_enabled in [False, True]:
        precision_label = "AMP_FP16" if amp_enabled else "FP32"
        print(f"\n  --- Precision: {precision_label} ---")

        for b in batch_sizes:
            reset_cuda_memory()

            try:
                model = ResNet34UNet(pretrained=False).to(device)
                criterion = CombinedBCEAndDiceLoss().to(device)
                optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
                scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled)

                x = torch.randn(b, 2, 512, 512, device=device)
                y = torch.randint(0, 2, (b, 1, 512, 512), device=device).float()

                # Warmup
                for _ in range(warmup):
                    optimizer.zero_grad(set_to_none=True)
                    with torch.amp.autocast("cuda", enabled=amp_enabled, dtype=torch.float16):
                        out = model(x)
                        loss = criterion(out, y)
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()

                torch.cuda.synchronize()
                reset_cuda_memory()

                fwd_times: List[float] = []
                bwd_times: List[float] = []

                for _ in range(iterations):
                    optimizer.zero_grad(set_to_none=True)
                    torch.cuda.synchronize()

                    t0 = time.perf_counter()
                    with torch.amp.autocast("cuda", enabled=amp_enabled, dtype=torch.float16):
                        out = model(x)
                        loss = criterion(out, y)
                    torch.cuda.synchronize()
                    t1 = time.perf_counter()

                    scaler.scale(loss).backward()
                    torch.cuda.synchronize()
                    t2 = time.perf_counter()

                    scaler.step(optimizer)
                    scaler.update()

                    fwd_times.append(t1 - t0)
                    bwd_times.append(t2 - t1)

                vram_peak = get_vram_mb()
                mean_fwd = sum(fwd_times) / len(fwd_times)
                mean_bwd = sum(bwd_times) / len(bwd_times)
                step_time = mean_fwd + mean_bwd
                samples_per_sec = b / step_time
                vram_headroom_mb = total_vram_mb - vram_peak["max_reserved_mb"]

                print(
                    f"    Batch {b:2d} | Fwd: {mean_fwd * 1000:6.1f} ms | "
                    f"Bwd: {mean_bwd * 1000:6.1f} ms | "
                    f"Peak Alloc: {vram_peak['max_allocated_mb']:6.1f} MB | "
                    f"Peak Rsrv: {vram_peak['max_reserved_mb']:6.1f} MB | "
                    f"Headroom: {vram_headroom_mb:6.1f} MB | "
                    f"{samples_per_sec:5.1f} samples/s"
                )

                results.append({
                    "precision": precision_label,
                    "batch_size": b,
                    "forward_ms": round(mean_fwd * 1000, 2),
                    "backward_ms": round(mean_bwd * 1000, 2),
                    "step_ms": round(step_time * 1000, 2),
                    "samples_per_sec": round(samples_per_sec, 2),
                    "max_allocated_mb": round(vram_peak["max_allocated_mb"], 1),
                    "max_reserved_mb": round(vram_peak["max_reserved_mb"], 1),
                    "vram_headroom_mb": round(vram_headroom_mb, 1),
                    "safe": vram_headroom_mb > 500.0,
                })

                del model, criterion, optimizer, scaler, x, y, out, loss
                reset_cuda_memory()

            except torch.cuda.OutOfMemoryError:
                print(f"    Batch {b:2d} | OUT OF MEMORY (OOM)!")
                results.append({
                    "precision": precision_label,
                    "batch_size": b,
                    "error": "CUDA OOM",
                    "safe": False,
                })
                reset_cuda_memory()
                break

    return results


def benchmark_gradient_accumulation() -> Dict[str, Any]:
    """Test gradient accumulation with physical batch 4, accumulation 2 (effective batch 8)."""
    print("\n" + "=" * 60)
    print("3. GRADIENT ACCUMULATION BENCHMARK (Batch 4, Accum 2 -> Effective Batch 8)")
    print("=" * 60)

    if not torch.cuda.is_available():
        return {"status": "SKIPPED_NO_CUDA"}

    device = torch.device("cuda:0")
    reset_cuda_memory()

    model = ResNet34UNet(pretrained=False).to(device)
    criterion = CombinedBCEAndDiceLoss().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    scaler = torch.amp.GradScaler("cuda", enabled=True)

    phys_batch = 4
    accum_steps = 2
    x1 = torch.randn(phys_batch, 2, 512, 512, device=device)
    y1 = torch.randint(0, 2, (phys_batch, 1, 512, 512), device=device).float()
    x2 = torch.randn(phys_batch, 2, 512, 512, device=device)
    y2 = torch.randint(0, 2, (phys_batch, 1, 512, 512), device=device).float()

    # Step measurement
    torch.cuda.synchronize()
    t0 = time.perf_counter()

    optimizer.zero_grad(set_to_none=True)

    # Microbatch 1
    with torch.amp.autocast("cuda", dtype=torch.float16):
        out1 = model(x1)
        loss1 = criterion(out1, y1) / accum_steps
    scaler.scale(loss1).backward()

    # Microbatch 2
    with torch.amp.autocast("cuda", dtype=torch.float16):
        out2 = model(x2)
        loss2 = criterion(out2, y2) / accum_steps
    scaler.scale(loss2).backward()

    scaler.step(optimizer)
    scaler.update()

    torch.cuda.synchronize()
    t1 = time.perf_counter()

    vram = get_vram_mb()
    total_ms = (t1 - t0) * 1000
    samples_per_sec = (phys_batch * accum_steps) / (t1 - t0)

    # Check finite gradients
    finite_grads = all(
        p.grad is not None and torch.isfinite(p.grad).all()
        for p in model.parameters()
        if p.requires_grad
    )

    print(f"  Effective Batch Size:    {phys_batch * accum_steps}")
    print(f"  Full Step Time:          {total_ms:.1f} ms")
    print(f"  Effective Throughput:    {samples_per_sec:.2f} samples/s")
    print(f"  Peak Allocated VRAM:     {vram['max_allocated_mb']:.1f} MB")
    print(f"  Peak Reserved VRAM:      {vram['max_reserved_mb']:.1f} MB")
    print(f"  All Gradients Finite:    {finite_grads}")

    del model, criterion, optimizer, scaler, x1, y1, x2, y2
    reset_cuda_memory()

    return {
        "physical_batch": phys_batch,
        "accumulation_steps": accum_steps,
        "effective_batch": phys_batch * accum_steps,
        "step_time_ms": round(total_ms, 2),
        "samples_per_sec": round(samples_per_sec, 2),
        "peak_allocated_mb": round(vram["max_allocated_mb"], 1),
        "peak_reserved_mb": round(vram["max_reserved_mb"], 1),
        "all_gradients_finite": finite_grads,
        "feasible": finite_grads and vram["max_reserved_mb"] < 5000.0,
    }


def benchmark_amp_numerical_validation() -> Dict[str, Any]:
    """Test AMP numerical behavior, checking underflow/overflow scaling."""
    print("\n" + "=" * 60)
    print("4. AMP NUMERICAL STABILITY VALIDATION")
    print("=" * 60)

    if not torch.cuda.is_available():
        return {"status": "SKIPPED_NO_CUDA"}

    device = torch.device("cuda:0")
    reset_cuda_memory()

    model = ResNet34UNet(pretrained=False).to(device)
    criterion = CombinedBCEAndDiceLoss().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    scaler = torch.amp.GradScaler("cuda", enabled=True)

    x = torch.randn(4, 2, 512, 512, device=device)
    y = torch.randint(0, 2, (4, 1, 512, 512), device=device).float()

    losses: List[float] = []
    scales: List[float] = []
    gradient_norms: List[float] = []

    for step in range(5):
        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast("cuda", dtype=torch.float16):
            out = model(x)
            loss = criterion(out, y)

        scaler.scale(loss).backward()

        # Unscale before checking norm
        scaler.unscale_(optimizer)
        total_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=10.0)

        scaler.step(optimizer)
        scaler.update()

        losses.append(loss.item())
        scales.append(scaler.get_scale())
        gradient_norms.append(total_norm.item())

    all_finite_loss = all(torch.isfinite(torch.tensor(val)).item() for val in losses)
    all_finite_grads = all(torch.isfinite(torch.tensor(g)).item() for g in gradient_norms)

    print(f"  Step Losses:        {[round(val, 4) for val in losses]}")
    print(f"  Gradient Norms:     {[round(g, 4) for g in gradient_norms]}")
    print(f"  Scaler Scales:      {scales}")
    print(f"  Losses Finite:      {all_finite_loss}")
    print(f"  Gradients Finite:   {all_finite_grads}")

    del model, criterion, optimizer, scaler, x, y
    reset_cuda_memory()

    return {
        "losses": [round(val, 4) for val in losses],
        "gradient_norms": [round(g, 4) for g in gradient_norms],
        "scaler_scales": scales,
        "all_finite_loss": all_finite_loss,
        "all_finite_grads": all_finite_grads,
        "stable": all_finite_loss and all_finite_grads,
    }


def benchmark_real_dataloader_throughput(
    manifest_path: Path,
    n_batches: int = 100,
    batch_size: int = 4,
) -> Dict[str, Any]:
    """Benchmark DataLoader throughput on real Trujillo tiles."""
    print("\n" + "=" * 60)
    print(f"5. REAL-DATA DATALOADER BENCHMARK ({n_batches} Batches, Batch Size {batch_size})")
    print("=" * 60)

    if not manifest_path.exists():
        print(f"  Manifest not found at {manifest_path}. Skipping.")
        return {"status": "MANIFEST_NOT_FOUND"}

    manifest = DatasetManifest.load(manifest_path)
    dataset = TrujilloTileDataset(
        manifest=manifest,
        split=SplitName.TRAIN,
        normalize=True,
    )

    results: Dict[str, Any] = {}

    for num_workers in [0]:
        print(f"\n  Testing num_workers={num_workers}...")
        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=torch.cuda.is_available(),
        )

        batch_times: List[float] = []
        t_start = time.perf_counter()
        t_prev = t_start
        first_batch_time: float = 0.0

        for i, (images, masks) in enumerate(loader):
            t_now = time.perf_counter()
            dt = t_now - t_prev
            t_prev = t_now

            if i == 0:
                first_batch_time = dt
            else:
                batch_times.append(dt)

            if i + 1 >= n_batches:
                break

        t_end = time.perf_counter()
        total_time = t_end - t_start
        total_samples = min(n_batches, len(dataset) // batch_size) * batch_size

        steady_mean_batch_ms = (
            (sum(batch_times) / len(batch_times)) * 1000 if batch_times else 0.0
        )
        steady_samples_per_sec = (
            (batch_size / (steady_mean_batch_ms / 1000)) if steady_mean_batch_ms > 0 else 0.0
        )
        overall_samples_per_sec = total_samples / total_time

        print(f"    First Batch Latency:         {first_batch_time * 1000:.1f} ms")
        print(f"    Steady-state Mean Batch:     {steady_mean_batch_ms:.1f} ms")
        print(f"    Steady-state Throughput:     {steady_samples_per_sec:.2f} samples/sec")
        print(
            f"    Overall Elapsed ({n_batches} batches): {total_time:.2f} s "
            f"({overall_samples_per_sec:.2f} samples/sec)"
        )

        results[f"workers_{num_workers}"] = {
            "num_workers": num_workers,
            "batch_size": batch_size,
            "n_batches_measured": n_batches,
            "first_batch_ms": round(first_batch_time * 1000, 2),
            "steady_mean_batch_ms": round(steady_mean_batch_ms, 2),
            "steady_samples_per_sec": round(steady_samples_per_sec, 2),
            "overall_samples_per_sec": round(overall_samples_per_sec, 2),
            "total_time_s": round(total_time, 2),
        }

    return results


def benchmark_real_training_loop_throughput(
    manifest_path: Path,
    n_batches: int = 25,
    batch_size: int = 4,
) -> Dict[str, Any]:
    """Benchmark training loop (Loader + GPU Transfer + AMP Forward + Backward + Step)."""
    print("\n" + "=" * 60)
    print(f"6. REAL-DATA TRAINING LOOP ({n_batches} Batches, Batch Size {batch_size})")
    print("=" * 60)

    if not torch.cuda.is_available() or not manifest_path.exists():
        return {"status": "SKIPPED"}

    device = torch.device("cuda:0")
    reset_cuda_memory()

    manifest = DatasetManifest.load(manifest_path)
    dataset = TrujilloTileDataset(
        manifest=manifest,
        split=SplitName.TRAIN,
        normalize=True,
    )
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=True,
    )

    model = ResNet34UNet(pretrained=False).to(device)
    criterion = CombinedBCEAndDiceLoss().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    scaler = torch.amp.GradScaler("cuda", enabled=True)

    batch_times: List[float] = []
    t_start = time.perf_counter()
    first_step_ms: float = 0.0

    for i, (images, masks) in enumerate(loader):
        t0 = time.perf_counter()

        images = images.to(device, non_blocking=True)
        masks = masks.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast("cuda", dtype=torch.float16):
            logits = model(images)
            loss = criterion(logits, masks)

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        torch.cuda.synchronize()
        t1 = time.perf_counter()
        dt = t1 - t0

        if i == 0:
            first_step_ms = dt * 1000
        else:
            batch_times.append(dt)

        if i + 1 >= n_batches:
            break

    t_end = time.perf_counter()
    total_s = t_end - t_start
    total_samples = n_batches * batch_size

    steady_mean_ms = (sum(batch_times) / len(batch_times)) * 1000 if batch_times else 0.0
    steady_samples_per_sec = (batch_size / (steady_mean_ms / 1000)) if steady_mean_ms > 0 else 0.0
    overall_samples_per_sec = total_samples / total_s
    vram = get_vram_mb()

    # Calculate full epoch estimate for 13,440 tiles
    epoch_seconds = 13440 / steady_samples_per_sec if steady_samples_per_sec > 0 else 0.0
    epoch_minutes = epoch_seconds / 60.0

    print(f"  First Step Latency:         {first_step_ms:.1f} ms")
    print(f"  Steady-state Step Latency:  {steady_mean_ms:.1f} ms")
    print(f"  Steady-state Throughput:    {steady_samples_per_sec:.2f} samples/sec")
    print(f"  Overall Throughput:         {overall_samples_per_sec:.2f} samples/sec")
    print(
        f"  Peak VRAM (Alloc / Rsrv):   {vram['max_allocated_mb']:.1f} MB / "
        f"{vram['max_reserved_mb']:.1f} MB"
    )
    print(
        f"  Estimated Epoch Time (13,440 tiles): {epoch_minutes:.1f} minutes "
        f"({epoch_seconds:.1f} s)"
    )

    del model, criterion, optimizer, scaler
    reset_cuda_memory()

    return {
        "batch_size": batch_size,
        "n_batches": n_batches,
        "first_step_ms": round(first_step_ms, 2),
        "steady_step_ms": round(steady_mean_ms, 2),
        "steady_samples_per_sec": round(steady_samples_per_sec, 2),
        "overall_samples_per_sec": round(overall_samples_per_sec, 2),
        "peak_allocated_mb": round(vram["max_allocated_mb"], 1),
        "peak_reserved_mb": round(vram["max_reserved_mb"], 1),
        "estimated_epoch_minutes": round(epoch_minutes, 2),
    }


def main() -> None:
    print("=" * 60)
    print("OCEAN SENTINEL — PHASE 2.3 EXP-00 MICROBENCHMARK")
    print("=" * 60)

    # 1. Environment metadata
    env_info = {
        "platform": platform.platform(),
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
    }

    if torch.cuda.is_available():
        env_info.update({
            "device_name": torch.cuda.get_device_name(0),
            "compute_capability": torch.cuda.get_device_capability(0),
            "device_count": torch.cuda.device_count(),
            "cuda_runtime_version": torch.version.cuda,
            "cudnn_version": torch.backends.cudnn.version(),
            "total_vram_mb": round(torch.cuda.get_device_properties(0).total_memory / (1024**2), 1),
        })

    print(json.dumps(env_info, indent=2))

    # 2. Model Parameter Audit
    model_params = {
        "resnet34_unet": count_parameters(ResNet34UNet(pretrained=False)),
        "vanilla_unet": count_parameters(VanillaUNet()),
    }
    print("\nModel Parameter Audit:")
    for mname, counts in model_params.items():
        print(f"  {mname}: {counts['trainable']:,} trainable parameters (total: {counts['total']:,})")

    # 3. CPU Baseline
    cpu_results = benchmark_cpu_baseline()

    # 4. CUDA Synthetic Sweep
    cuda_sweep = benchmark_cuda_synthetic(batch_sizes=[1, 2, 4, 8])

    # 5. Gradient Accumulation
    grad_accum = benchmark_gradient_accumulation()

    # 6. AMP Validation
    amp_validation = benchmark_amp_numerical_validation()

    # 7. Real DataLoader
    manifest_path = repo_root / "data" / "metadata" / "trujillo_2024" / "split_manifest.json"
    dataloader_results = benchmark_real_dataloader_throughput(
        manifest_path=manifest_path,
        n_batches=100,
        batch_size=4,
    )

    # 8. Real End-to-End Training Step
    training_step_results = benchmark_real_training_loop_throughput(
        manifest_path=manifest_path,
        n_batches=25,
        batch_size=4,
    )

    # Combine into comprehensive report
    benchmark_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "environment": env_info,
        "model_parameters": model_params,
        "cpu_baseline": cpu_results,
        "cuda_synthetic_sweep": cuda_sweep,
        "gradient_accumulation": grad_accum,
        "amp_validation": amp_validation,
        "real_dataloader_throughput": dataloader_results,
        "real_training_throughput": training_step_results,
    }

    out_path = repo_root / "data" / "metadata" / "trujillo_2024" / "exp00_benchmark_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_report, f, indent=2)

    print("\n" + "=" * 60)
    print(f"BENCHMARK COMPLETE. Results saved to: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
