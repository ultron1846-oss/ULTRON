"""Reproducible inference-only benchmark for the ULTRON Section C prototype.

This measures the current implementation; it does not train or update weights.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import math
import platform
import random
import statistics
import time
from typing import Sequence

import torch

from .config import NeuroSparseConfig
from .model import NeuroSparseModel, SparseExpert


def bootstrap_median_ci(
    samples: Sequence[float], *, seed: int = 1729, resamples: int = 2000,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Percentile bootstrap CI for the sample median."""
    if len(samples) < 2:
        raise ValueError("at least two samples are required")
    if any(not math.isfinite(float(sample)) for sample in samples):
        raise ValueError("samples must all be finite")
    if resamples < 100:
        raise ValueError("resamples must be at least 100")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between zero and one")
    rng = random.Random(seed)
    n = len(samples)
    medians = sorted(
        statistics.median(samples[rng.randrange(n)] for _ in range(n))
        for _ in range(resamples)
    )
    tail = (1.0 - confidence) / 2.0
    return percentile(medians, tail), percentile(medians, 1.0 - tail)


def percentile(samples: Sequence[float], q: float) -> float:
    """Linearly interpolated percentile for q in [0, 1]."""
    if not samples:
        raise ValueError("at least one sample is required")
    if any(not math.isfinite(float(sample)) for sample in samples):
        raise ValueError("samples must all be finite")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be between zero and one")
    ordered = sorted(samples)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def parameter_accounting(model: NeuroSparseModel) -> dict[str, int | float]:
    total = sum(parameter.numel() for parameter in model.parameters())
    # SparseExpert owns a Sequential child; include its descendants explicitly.
    expert = sum(
        parameter.numel()
        for module in model.modules()
        if isinstance(module, SparseExpert)
        for parameter in module.parameters()
    )
    shared = total - expert
    selected_ratio = model.config.top_k / model.config.num_experts
    active_expert_estimate = int(expert * selected_ratio)
    return {
        "parameters_total": total,
        "parameters_expert_total": expert,
        "parameters_shared_total": shared,
        "expert_selection_ratio_per_token": selected_ratio,
        "estimated_selected_expert_parameters_per_token": active_expert_estimate,
        "estimated_structurally_active_parameters_per_token": shared + active_expert_estimate,
    }


def _run_benchmark_impl(
    *, device: str = "cpu", batch: int = 2, sequence: int = 16,
    warmup: int = 10, iterations: int = 50, seed: int = 1729,
    num_threads: int | None = None,
) -> dict:
    if batch <= 0 or sequence <= 0:
        raise ValueError("batch and sequence must be positive")
    if warmup < 0:
        raise ValueError("warmup must be non-negative")
    if iterations < 2:
        raise ValueError("iterations must be at least two")
    target = torch.device(device)
    if target.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    if target.type not in ("cpu", "cuda"):
        raise ValueError("device must be cpu or cuda")
    config = NeuroSparseConfig()
    model = NeuroSparseModel(config).to(target).eval()
    generator = torch.Generator(device="cpu").manual_seed(seed)
    input_ids = torch.randint(
        1, config.vocab_size, (batch, sequence), generator=generator
    ).to(target)

    with torch.inference_mode():
        for _ in range(warmup):
            model(input_ids)
        if target.type == "cuda":
            torch.cuda.synchronize(target)
            torch.cuda.reset_peak_memory_stats(target)

        timings: list[float] = []
        for _ in range(iterations):
            if target.type == "cuda":
                torch.cuda.synchronize(target)
            start = time.perf_counter()
            model(input_ids)
            if target.type == "cuda":
                torch.cuda.synchronize(target)
            timings.append(time.perf_counter() - start)

    median = statistics.median(timings)
    ci_low, ci_high = bootstrap_median_ci(timings, seed=seed)
    accounting = parameter_accounting(model)
    return {
        "schema_version": 1,
        "benchmark_kind": "inference_only_synthetic_smoke",
        "training_performed": False,
        "optimizer_steps": 0,
        "external_data_used": False,
        "external_ai_api_used": False,
        "device": str(target),
        "device_name": (
            torch.cuda.get_device_name(target) if target.type == "cuda" else platform.processor() or "CPU"
        ),
        "torch_version": torch.__version__,
        "python_version": platform.python_version(),
        "seed": seed,
        "batch": batch,
        "sequence": sequence,
        "tokens_per_iteration": batch * sequence,
        "warmup_iterations": warmup,
        "measured_iterations": iterations,
        "latency_seconds": {
            "median": median,
            "mean": statistics.mean(timings),
            "stdev": statistics.stdev(timings),
            "p90": percentile(timings, 0.90),
            "p95": percentile(timings, 0.95),
            "min": min(timings),
            "max": max(timings),
            "bootstrap_median_ci_95_percent": [ci_low, ci_high],
            "samples": timings,
        },
        "throughput_tokens_per_second_at_median": (batch * sequence) / median,
        "peak_cuda_memory_bytes": (
            torch.cuda.max_memory_allocated(target) if target.type == "cuda" else None
        ),
        "parameter_accounting": accounting,
        "measurement_limitations": [
            "Synthetic random token IDs are a harness input, not a training or evaluation corpus.",
            "This is one-process inference timing, not a quality benchmark.",
            "Selected expert parameter counts are structural estimates, not measured FLOPs or hardware activity.",
            "The estimate excludes token-dependent refinement work, memory traffic, kernel launch overhead and implementation inefficiency.",
            "No baseline comparison, ablation, energy measurement or mathematical capability claim is produced.",
        ],
    }


@contextmanager
def _preserve_benchmark_runtime(seed: int, num_threads: int | None, target: torch.device):
    """Isolate benchmark RNG/thread settings from the calling application."""
    cpu_rng_state = torch.random.get_rng_state()
    previous_threads = torch.get_num_threads()
    try:
        local_generator = torch.Generator(device="cpu").manual_seed(seed)
        torch.random.set_rng_state(local_generator.get_state())
        if num_threads is not None and num_threads <= 0:
            raise ValueError("num_threads must be positive")
        if num_threads is not None and target.type == "cpu":
            torch.set_num_threads(num_threads)
        yield
    finally:
        torch.random.set_rng_state(cpu_rng_state)
        if torch.get_num_threads() != previous_threads:
            torch.set_num_threads(previous_threads)


def run_benchmark(
    *, device: str = "cpu", batch: int = 2, sequence: int = 16,
    warmup: int = 10, iterations: int = 50, seed: int = 1729,
    num_threads: int | None = None,
) -> dict:
    target = torch.device(device)
    with _preserve_benchmark_runtime(seed, num_threads, target):
        return _run_benchmark_impl(
            device=device, batch=batch, sequence=sequence, warmup=warmup,
            iterations=iterations, seed=seed, num_threads=None,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--sequence", type=int, default=16)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--num-threads", type=int)
    parser.add_argument("--output", help="Optional path for a JSON result; stdout is always emitted.")
    args = parser.parse_args()
    result = run_benchmark(
        device=args.device, batch=args.batch, sequence=args.sequence,
        warmup=args.warmup, iterations=args.iterations, seed=args.seed,
        num_threads=args.num_threads,
    )
    encoded = json.dumps(result, indent=2)
    print(encoded)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(encoded + "\n")


if __name__ == "__main__":
    main()
