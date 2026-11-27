"""Runtime process-memory guard for bounded local training.

The monitor samples process RSS and CUDA allocator-reserved memory at safe
controller boundaries. It cannot interrupt a single tensor/kernel operation.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Callable, Mapping

import torch


@dataclass(frozen=True)
class MemoryUsage:
    process_rss_bytes: int
    cuda_reserved_bytes: int = 0

    def __post_init__(self):
        for name, value in (
            ("process_rss_bytes", self.process_rss_bytes),
            ("cuda_reserved_bytes", self.cuda_reserved_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")

    @property
    def total_bytes(self) -> int:
        # CUDA reserved memory is not included in process RSS on typical
        # runtimes, so add it to approximate the process's combined footprint.
        return self.process_rss_bytes + self.cuda_reserved_bytes

    def as_dict(self) -> dict[str, int]:
        return {
            "process_rss_bytes": self.process_rss_bytes,
            "cuda_reserved_bytes": self.cuda_reserved_bytes,
            "total_bytes": self.total_bytes,
        }


def _current_process_rss_bytes() -> int:
    """Return current resident-set size using native sources where available."""
    try:
        import psutil  # optional; used when installed by the runtime
        return int(psutil.Process(os.getpid()).memory_info().rss)
    except ImportError:
        pass

    # Linux /proc reports resident pages in statm; this is current RSS rather
    # than the process lifetime high-water mark.
    try:
        with open("/proc/self/statm", "r", encoding="ascii") as statm:
            fields = statm.read().split()
        if len(fields) < 2:
            raise RuntimeError("unexpected /proc/self/statm format")
        resident_pages = int(fields[1])
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        if resident_pages < 0 or page_size <= 0:
            raise RuntimeError("invalid resident page count or page size")
        return resident_pages * page_size
    except (OSError, ValueError, IndexError):
        pass

    # Portable Unix fallback. This is a peak RSS high-water mark, not current
    # RSS; the monitor reports the source limitation explicitly.
    try:
        import resource
        peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return peak if sys.platform == "darwin" else peak * 1024
    except (ImportError, AttributeError, OSError, ValueError):
        raise RuntimeError(
            "cannot sample process RSS on this runtime; install psutil or use "
            "a platform with /proc/self/statm or resource.getrusage"
        ) from None


def sample_memory_usage(device=None) -> MemoryUsage:
    """Sample process RSS and CUDA allocator-reserved memory."""
    rss = _current_process_rss_bytes()
    cuda_reserved = 0
    if torch.cuda.is_available():
        if device is not None and getattr(device, "type", None) == "cuda":
            cuda_reserved = int(torch.cuda.memory_reserved(device))
        else:
            # Before the first batch, include reservations on every visible
            # CUDA device instead of silently treating device memory as zero.
            cuda_reserved = sum(
                int(torch.cuda.memory_reserved(index))
                for index in range(torch.cuda.device_count())
            )
    return MemoryUsage(rss, cuda_reserved)


class RuntimeMemoryMonitor:
    """Enforce a combined RSS + CUDA-reserved memory budget.

    An injectable provider supports deterministic unit tests and platform
    adapters. The provider receives the active device (or None before batches)
    and returns MemoryUsage or a mapping with the two byte-count fields.
    """

    def __init__(
        self,
        budget_bytes: int,
        *,
        usage_provider: Callable[[object | None], MemoryUsage | Mapping[str, int]] | None = None,
    ):
        if isinstance(budget_bytes, bool) or not isinstance(budget_bytes, int) or budget_bytes <= 0:
            raise ValueError("budget_bytes must be a positive integer")
        if usage_provider is not None and not callable(usage_provider):
            raise TypeError("usage_provider must be callable or None")
        self.budget_bytes = budget_bytes
        self.usage_provider = usage_provider or sample_memory_usage
        self.samples = 0
        self.peak_bytes = 0
        self.last_usage: MemoryUsage | None = None
        self.last_stage: str | None = None

    def check(self, stage: str, *, device=None) -> MemoryUsage:
        if not isinstance(stage, str) or not stage.strip():
            raise ValueError("stage must be a non-empty string")
        sampled = self.usage_provider(device)
        if isinstance(sampled, MemoryUsage):
            usage = sampled
        elif isinstance(sampled, Mapping):
            usage = MemoryUsage(
                sampled.get("process_rss_bytes"),
                sampled.get("cuda_reserved_bytes", 0),
            )
        else:
            raise TypeError("usage_provider must return MemoryUsage or a mapping")

        self.samples += 1
        self.last_usage = usage
        self.last_stage = stage
        self.peak_bytes = max(self.peak_bytes, usage.total_bytes)
        if usage.total_bytes > self.budget_bytes:
            raise MemoryError(
                "runtime memory budget exceeded at "
                f"{stage}: sampled {usage.total_bytes:,} bytes "
                f"(RSS {usage.process_rss_bytes:,} + CUDA reserved "
                f"{usage.cuda_reserved_bytes:,}) exceeds "
                f"{self.budget_bytes:,} byte budget"
            )
        return usage

    def summary(self) -> dict[str, object]:
        return {
            "budget_bytes": self.budget_bytes,
            "peak_sampled_bytes": self.peak_bytes,
            "samples": self.samples,
            "last_stage": self.last_stage,
            "last_usage": None if self.last_usage is None else self.last_usage.as_dict(),
            "measurement": "process RSS + CUDA allocator-reserved memory",
            "limitation": (
                "sampled only at controller boundaries; cannot interrupt an "
                "individual tensor operation; RSS fallback may be a lifetime "
                "high-water mark on platforms without a current-RSS source"
            ),
        }
