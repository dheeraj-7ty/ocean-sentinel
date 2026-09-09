"""EXP-01 Performance Benchmark: batch-size, accumulation, DataLoader worker search.

Measures training-step throughput with REAL Trujillo data, real model, real loss,
real CUDA AMP FP16. Produces a structured JSON benchmark report.

Usage:
    python scripts/benchmark_exp01_perf.py [--manifest PATH] [--report PATH]
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset  # noqa: E402
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName  # noqa: E402
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss  # noqa: E402
from ocean_sentinel.ml.unet_resnet import ResNet34UNet  # noqa: E402

DEFAULT_MANIFEST = (
    REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def reset_cuda() -> None:
    if DEVICE.type == "cuda":
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        gc.collect()


def get_peak_vram_mb() -> float:
    if DEVICE.type != "cuda":
        return 0.0
    torch.cuda.synchronize()
    return round(torch.cuda.max_memory_allocated() / 1e6, 1)


def benchmark_training_step(
    batch_size: int,
    accum_steps: int,
    dataset: "TrujilloTileDataset",
    num_warmup_batches: int = 3,
    num_measure_batches: int = 12,
) -> dict:
    """Full training-step benchmark for one (batch_size, accum_steps) config."""
    result: dict = {
        "batch_size": batch_size,
        "accum_steps": accum_steps,
        "nominal_effective_batch": batch_size * accum_steps,
        "status": "UNKNOWN",
    }
    reset_cuda()
    if DEVICE.type == "cuda":
        torch.cuda.reset_peak_memory_stats()

    try:
        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0,
            pin_memory=(DEVICE.type == "cuda"),
            drop_last=True,
        )
        need = num_warmup_batches + num_measure_batches
        if len(loader) < need:
            result["status"] = "INSUFFICIENT_BATCHES"
            result["error"] = f"Need {need}, have {len(loader)}"
            return result

        model = ResNet34UNet(
            in_channels=2, num_classes=1, pretrained=False,
            adaptation_method="slice_variance_scaled",
        ).to(DEVICE)
        criterion = CombinedBCEAndDiceLoss(
            bce_weight=0.5, dice_weight=0.5, smooth=1.0
        ).to(DEVICE)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)
        scaler = torch.amp.GradScaler(DEVICE.type, enabled=True)

        model.train()
        loader_iter = iter(loader)

        # Warmup (not measured)
        optimizer.zero_grad(set_to_none=True)
        for _ in range(num_warmup_batches):
            imgs, masks = next(loader_iter)
            imgs = imgs.to(DEVICE, non_blocking=True)
            masks = masks.to(DEVICE, non_blocking=True)
            with torch.amp.autocast(device_type=DEVICE.type, enabled=True):
                loss = criterion(model(imgs), masks) / accum_steps
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad(set_to_none=True)

        if DEVICE.type == "cuda":
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()

        fwd_times: list[float] = []
        bwd_times: list[float] = []
        opt_times: list[float] = []
        io_times: list[float] = []
        total_samples = 0
        optimizer.zero_grad(set_to_none=True)
        overall_start = time.perf_counter()

        for step in range(num_measure_batches):
            io_t0 = time.perf_counter()
            imgs, masks = next(loader_iter)
            imgs = imgs.to(DEVICE, non_blocking=True)
            masks = masks.to(DEVICE, non_blocking=True)
            if DEVICE.type == "cuda":
                torch.cuda.synchronize()
            io_times.append(time.perf_counter() - io_t0)

            fwd_t0 = time.perf_counter()
            with torch.amp.autocast(device_type=DEVICE.type, enabled=True):
                logits = model(imgs)
                loss = criterion(logits, masks) / accum_steps
            if DEVICE.type == "cuda":
                torch.cuda.synchronize()
            fwd_times.append(time.perf_counter() - fwd_t0)

            bwd_t0 = time.perf_counter()
            scaler.scale(loss).backward()
            if DEVICE.type == "cuda":
                torch.cuda.synchronize()
            bwd_times.append(time.perf_counter() - bwd_t0)

            opt_t0 = time.perf_counter()
            is_step = ((step + 1) % accum_steps == 0) or (step == num_measure_batches - 1)
            if is_step:
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
            if DEVICE.type == "cuda":
                torch.cuda.synchronize()
            opt_times.append(time.perf_counter() - opt_t0)
            total_samples += imgs.shape[0]

        elapsed = time.perf_counter() - overall_start

        def ms(vals: list[float]) -> float:
            return round(1000 * sum(vals) / max(len(vals), 1), 2)

        result.update({
            "status": "OK",
            "samples_per_sec": round(total_samples / elapsed, 1),
            "mean_batch_time_ms": round(1000 * elapsed / num_measure_batches, 1),
            "mean_io_ms": ms(io_times),
            "mean_fwd_ms": ms(fwd_times),
            "mean_bwd_ms": ms(bwd_times),
            "mean_opt_ms": ms(opt_times),
            "peak_vram_allocated_mb": get_peak_vram_mb(),
        })

    except torch.cuda.OutOfMemoryError as e:
        reset_cuda()
        result["status"] = "OOM"
        result["error"] = str(e)[:300]
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)[:300]
    finally:
        try:
            del model, criterion, optimizer, scaler, loader, loader_iter
        except Exception:
            pass
        reset_cuda()

    return result


def benchmark_workers(
    dataset: "TrujilloTileDataset",
    batch_size: int,
    worker_counts: list[int],
    num_batches: int = 15,
) -> list[dict]:
    results = []
    for nw in worker_counts:
        reset_cuda()
        r: dict = {"num_workers": nw, "batch_size": batch_size}
        try:
            ldr = DataLoader(
                dataset,
                batch_size=batch_size,
                shuffle=False,
                num_workers=nw,
                pin_memory=(DEVICE.type == "cuda"),
                persistent_workers=(nw > 0),
                prefetch_factor=(2 if nw > 0 else None),
                drop_last=False,
            )
            it = iter(ldr)
            times: list[float] = []
            n_batches = min(num_batches, len(ldr))
            for _ in range(n_batches):
                t0 = time.perf_counter()
                imgs, _ = next(it)
                imgs.to(DEVICE, non_blocking=True)
                if DEVICE.type == "cuda":
                    torch.cuda.synchronize()
                times.append(time.perf_counter() - t0)
            del ldr
            r["status"] = "OK"
            r["mean_batch_load_ms"] = round(1000 * sum(times) / len(times), 2)
            r["samples_per_sec"] = round((batch_size * len(times)) / sum(times), 1)
        except Exception as e:
            r["status"] = "ERROR"
            r["error"] = str(e)[:200]
        results.append(r)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="EXP-01 Performance Benchmark")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--report",
        type=Path,
        default=REPO_ROOT / "experiments" / "exp01_baseline" / "benchmark_report.json",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("EXP-01 PERFORMANCE BENCHMARK")
    print("=" * 70)
    gpu_name = torch.cuda.get_device_name(0) if DEVICE.type == "cuda" else "CPU"
    vram_total_mb = (
        torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
        if DEVICE.type == "cuda"
        else 0
    )
    print(f"Device: {DEVICE} ({gpu_name}), VRAM: {vram_total_mb} MB")

    manifest = DatasetManifest.load(args.manifest)
    dataset = TrujilloTileDataset(manifest, SplitName.TRAIN, normalize=True)
    print(f"Train tiles: {len(dataset)}")

    report: dict = {
        "device": str(DEVICE),
        "gpu": gpu_name,
        "vram_total_mb": vram_total_mb,
        "torch_version": torch.__version__,
        "manifest": str(args.manifest),
        "train_tiles": len(dataset),
        "batch_results": [],
        "worker_results": [],
    }

    # --- Batch size + accumulation benchmark ---
    candidates = [
        (4, 2),
        (8, 1),
        (8, 2),
        (12, 1),
        (16, 1),
    ]
    print("\n--- BATCH SIZE / ACCUMULATION SEARCH ---")
    hdr = f"{'BS':>4} {'Ac':>3} {'NEB':>5} {'Status':>8}  {'samp/s':>8}  {'VRAM MB':>8}  "
    hdr += f"{'io ms':>7} {'fwd ms':>7} {'bwd ms':>7} {'opt ms':>7}"
    print(hdr)
    print("-" * 75)

    for bs, acc in candidates:
        r = benchmark_training_step(bs, acc, dataset)
        report["batch_results"].append(r)
        if r["status"] == "OK":
            print(
                f"{bs:>4} {acc:>3} {bs*acc:>5} {'OK':>8}  "
                f"{r['samples_per_sec']:>8.1f}  "
                f"{r['peak_vram_allocated_mb']:>8.1f}  "
                f"{r['mean_io_ms']:>7.1f} {r['mean_fwd_ms']:>7.1f} "
                f"{r['mean_bwd_ms']:>7.1f} {r['mean_opt_ms']:>7.1f}"
            )
        else:
            print(f"{bs:>4} {acc:>3} {bs*acc:>5} {r['status']:>8}  {'---':>8}  {'---':>8}")

    # --- DataLoader worker benchmark ---
    best_viable_bs = 8
    for r in report["batch_results"]:
        if r["status"] == "OK" and r["batch_size"] >= 8 and r["accum_steps"] == 1:
            best_viable_bs = r["batch_size"]
            break

    print(f"\n--- DATALOADER WORKER SEARCH (bs={best_viable_bs}) ---")
    print(f"{'Workers':>8}  {'Status':>8}  {'load ms':>9}  {'samp/s':>9}")
    print("-" * 45)

    wresults = benchmark_workers(dataset, best_viable_bs, [0, 1, 2, 4])
    for r in wresults:
        report["worker_results"].append(r)
        if r["status"] == "OK":
            print(
                f"{r['num_workers']:>8}  {'OK':>8}  "
                f"{r['mean_batch_load_ms']:>9.1f}  "
                f"{r['samples_per_sec']:>9.1f}"
            )
        else:
            print(f"{r['num_workers']:>8}  {r['status']:>8}  {'---':>9}  {'---':>9}")

    # --- Selection summary ---
    ok = [r for r in report["batch_results"] if r["status"] == "OK"]
    baseline = next((r for r in ok if r["batch_size"] == 4 and r["accum_steps"] == 2), None)
    best = max(ok, key=lambda r: r["samples_per_sec"]) if ok else None

    print("\n--- SELECTION SUMMARY ---")
    if baseline and best:
        speedup = best["samples_per_sec"] / baseline["samples_per_sec"]
        report["baseline_config"] = baseline
        report["recommended_config"] = best
        report["speedup_vs_baseline"] = round(speedup, 3)
        print(
            f"Baseline  B{baseline['batch_size']} acc{baseline['accum_steps']}: "
            f"{baseline['samples_per_sec']:.1f} samp/s, "
            f"{baseline['peak_vram_allocated_mb']:.0f} MB VRAM"
        )
        print(
            f"Best      B{best['batch_size']} acc{best['accum_steps']}: "
            f"{best['samples_per_sec']:.1f} samp/s, "
            f"{best['peak_vram_allocated_mb']:.0f} MB VRAM"
        )
        print(f"Speedup:  {speedup:.2f}x")

        steps_epoch = len(dataset) // best["batch_size"]
        epoch_s = steps_epoch * best["mean_batch_time_ms"] / 1000
        report["estimated_epoch_time_s"] = round(epoch_s, 1)
        report["estimated_30epoch_time_min"] = round(epoch_s * 30 / 60, 1)
        print(f"Est. epoch time (best): {epoch_s/60:.1f} min")
        print(f"Est. 30-epoch total:    {epoch_s*30/60:.1f} min")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with open(args.report, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nBenchmark report saved: {args.report}")
    print("=" * 70)


if __name__ == "__main__":
    main()
