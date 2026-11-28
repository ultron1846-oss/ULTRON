"""Reproducible Phase 1 CPU microbenchmarks (fixture-only, inference-only)."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import torch

from ultron_core.checkpoint import load_checkpoint, save_checkpoint
from ultron_core.config import NeuroSparseConfig
from ultron_core.dataset_split_manifest import prepare_dataset_split_manifest
from ultron_core.inference import ULTRONInferenceEngine
from ultron_core.math_tokenizer import MathTokenizer
from ultron_core.model import NeuroSparseModel, _causal_attention_with_mha_weights
from tools.benchmark_verified_dataset import benchmark_indexed_dataset


SEED = 20261128
WARMUP = 3
REPETITIONS = 12
TOKENIZER_INPUTS = (
    "12345 + 67890 = 80235",
    r"\frac{1}{2} + \frac{1}{3} = \frac{5}{6}",
    "∀x∈ℝ: x²≥0",
    "∫₀¹ x² dx = 1/3",
    r"\lim_{x\to0}\frac{x^2}{x}=0",
)
FRONTEND_ASSETS = (
    "index.html", "styles.css", "app.js", "preferences.js", "graph-tool.js",
    "math-engine.js", "math-tools.js", "memory-store.js", "provider-directory.js",
    "runtime-config.js", "runtime-status.js", "supabase-integration.js", "word-problems.js",
)


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def measure(function, *, warmup: int = WARMUP, repetitions: int = REPETITIONS) -> dict:
    for _ in range(warmup):
        function()
    samples = []
    for _ in range(repetitions):
        start = time.perf_counter()
        function()
        samples.append(time.perf_counter() - start)
    median = statistics.median(samples)
    return {
        "warmup_iterations": warmup,
        "measured_iterations": repetitions,
        "samples_seconds": samples,
        "median_seconds": median,
        "mean_seconds": statistics.mean(samples),
        "p95_seconds": percentile(samples, 0.95),
    }


def reference_scan(tokenizer: MathTokenizer, source: str) -> list[int]:
    """Reproduce the earlier full-vocabulary longest-match scan."""
    candidates = sorted(
        tokenizer.vocabulary.tokens[3:],
        key=lambda value: (-len(value), value),
    )
    ids = []
    offset = 0
    while offset < len(source):
        match = next(
            (value for value in candidates if source.startswith(value, offset)),
            None,
        )
        if match is None:
            raise ValueError(f"unsupported character at offset {offset}")
        ids.append(tokenizer.vocabulary.token_id(match))
        offset += len(match)
    return ids


def tokenizer_report() -> dict:
    tokenizer = MathTokenizer()
    expected = {
        source: reference_scan(tokenizer, source) for source in TOKENIZER_INPUTS
    }
    actual = {
        source: tokenizer.encode(source) for source in TOKENIZER_INPUTS
    }
    if actual != expected:
        raise AssertionError("trie tokenizer differs from reference longest-match scan")
    token_count = sum(len(value) for value in actual.values())
    old = measure(
        lambda: [reference_scan(tokenizer, source) for source in TOKENIZER_INPUTS]
    )
    new = measure(
        lambda: [tokenizer.encode(source) for source in TOKENIZER_INPUTS]
    )
    for report in (old, new):
        report["tokens_per_iteration"] = token_count
        report["tokens_per_second_at_median"] = token_count / report["median_seconds"]
    return {
        "input_count": len(TOKENIZER_INPUTS),
        "characters_per_iteration": sum(len(value) for value in TOKENIZER_INPUTS),
        "tokens_per_iteration": token_count,
        "reference_full_vocabulary_scan": old,
        "current_trie_tokenizer": new,
        "token_ids_equivalent": True,
        "median_speedup_ratio_reference_over_trie": (
            old["median_seconds"] / new["median_seconds"]
        ),
    }


def tiny_config() -> NeuroSparseConfig:
    return NeuroSparseConfig(
        vocab_size=len(MathTokenizer().vocabulary),
        hidden_size=32,
        num_layers=1,
        num_experts=4,
        top_k=2,
        expert_multiplier=2,
        max_refinements=1,
        fast_memory_slots=4,
        num_attention_heads=4,
        max_sequence_length=64,
        dropout=0.0,
    )


def model_report() -> tuple[dict, NeuroSparseModel, NeuroSparseConfig]:
    torch.manual_seed(SEED)
    config = tiny_config()
    model = NeuroSparseModel(config).cpu().eval()
    generator = torch.Generator(device="cpu").manual_seed(SEED)
    forward = {}
    with torch.inference_mode():
        for sequence in (16, 32, 64):
            input_ids = torch.randint(
                1, config.vocab_size, (2, sequence), generator=generator
            )
            forward[str(sequence)] = measure(lambda x=input_ids: model(x))

        hidden = torch.randn((2, 32, config.hidden_size), generator=generator)
        block = model.blocks[0]
        normalized = block.attention_norm(hidden)
        attention = measure(
            lambda: _causal_attention_with_mha_weights(
                block.attention, normalized
            )
        )
        router = measure(lambda: block.router(normalized))
    return {
        "configuration": config.to_dict(),
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "batch_size": 2,
        "forward_latency_by_sequence_length": forward,
        "attention_component_latency": attention,
        "topk_router_component_latency": router,
        "model_is_random_initialized": True,
        "optimizer_created": False,
        "optimizer_steps": 0,
    }, model, config


def checkpoint_report(model: NeuroSparseModel, config: NeuroSparseConfig) -> dict:
    saves, loads = [], []
    with tempfile.TemporaryDirectory(prefix="ultron-phase1-checkpoint-") as directory:
        path = Path(directory) / "tiny-inference-only.pt"
        loaded_step = None
        for index in range(3):
            started = time.perf_counter()
            save_checkpoint(path, model, config, step=index)
            saves.append(time.perf_counter() - started)
            destination = NeuroSparseModel(config).eval()
            started = time.perf_counter()
            result = load_checkpoint(
                path, destination, map_location="cpu", restore_rng=False
            )
            loads.append(time.perf_counter() - started)
            loaded_step = result["step"]
        return {
            "save_seconds": saves,
            "save_median_seconds": statistics.median(saves),
            "load_seconds": loads,
            "load_median_seconds": statistics.median(loads),
            "checkpoint_bytes": path.stat().st_size,
            "last_loaded_step_metadata": loaded_step,
            "optimizer_state_present": False,
            "rng_restored": False,
            "training_performed": False,
        }


def inference_report(model: NeuroSparseModel) -> dict:
    engine = ULTRONInferenceEngine(model, MathTokenizer())
    results = {}
    try:
        for nominal_tokens in (8, 24, 48):
            prompt = "x+" * (nominal_tokens // 2)
            last = {}
            latency = measure(
                lambda: last.update(engine.generate(prompt, max_new_tokens=2)),
                warmup=2,
                repetitions=8,
            )
            results[str(nominal_tokens)] = {
                "prompt_characters": len(prompt),
                "prompt_tokens": last.get("prompt_token_count"),
                "generated_tokens": last.get("generated_token_count"),
                "latency": latency,
            }
    finally:
        engine.close()
    return {
        "latency_by_nominal_prompt_size": results,
        "random_initialized_model": True,
        "quality_claim": False,
        "training_performed": False,
    }


def write_fixture(path: Path, rows: int = 3500) -> None:
    version = "0.5.0"
    encoded_rows = []
    for index in range(rows):
        a, b = index + 1, 2
        prompt, answer = f"{a} + {b}", str(a + b)
        parameters = {"a": a, "operator": "+", "b": b}
        identity = {
            "generator_version": version, "seed": 37, "index": index,
            "topic": "arithmetic", "input_text": prompt, "target_text": answer,
            "generation_parameters": parameters,
        }
        example_id = hashlib.sha256(json.dumps(
            identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        row = {
            "example_id": example_id, "generator_version": version,
            "topic": "arithmetic", "difficulty": 1 if a < 10 else 2,
            "input_text": prompt, "target_text": answer, "exact_answer": answer,
            "seed": 37, "index": index, "generation_parameters": parameters,
            "validation_status": "semantically_checked",
            "provenance": "temporary Phase 1 synthetic benchmark fixture",
        }
        encoded_rows.append(
            json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        )
    payload = "".join(encoded_rows).encode("utf-8")
    path.write_bytes(payload)
    manifest = {
        "schema_version": 1, "generator_version": version, "seed": 37,
        "topics": ["arithmetic"], "example_count": rows,
        "topic_counts": {"arithmetic": rows},
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    path.with_suffix(path.suffix + ".manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def dataset_report() -> dict:
    with tempfile.TemporaryDirectory(prefix="ultron-phase1-dataset-") as directory:
        root = Path(directory)
        dataset, split = root / "fixture.jsonl", root / "fixture.splits.json"
        write_fixture(dataset)
        prepared = prepare_dataset_split_manifest(dataset, split, split_seed=SEED)
        report = benchmark_indexed_dataset(
            dataset, split, random_access_samples=100, seed=SEED
        )
        return {
            "fixture_rows": 3500,
            "selected_split_counts": dict(prepared.split_counts),
            "indexed_loader_benchmark": report,
            "production_dataset_used": False,
            "temporary_files_retained": False,
        }


def frontend_report(root: Path) -> dict:
    assets, raw_total, gzip_total = [], 0, 0
    for name in FRONTEND_ASSETS:
        path = root / name
        if not path.is_file():
            continue
        data = path.read_bytes()
        zipped = gzip.compress(data, compresslevel=9, mtime=0)
        assets.append({
            "path": name,
            "raw_bytes": len(data),
            "gzip_bytes": len(zipped),
        })
        raw_total += len(data)
        gzip_total += len(zipped)
    return {
        "assets": assets,
        "raw_total_bytes": raw_total,
        "gzip_total_bytes": gzip_total,
        "browser_load_time_measured": False,
        "limitation": "Transfer-size proxy only; not a browser/network load-time measurement.",
    }


def system_report() -> dict:
    node_version = None
    try:
        node_version = subprocess.run(
            ["node", "--version"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    cpu = platform.processor() or "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            if line.lower().startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    try:
        import resource
        peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if platform.system() != "Darwin":
            peak_rss *= 1024
    except (ImportError, OSError):
        peak_rss = None
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "node": node_version,
        "cpu_model": cpu,
        "logical_cpu_count": os.cpu_count(),
        "torch_cpu_threads": torch.get_num_threads(),
        "cuda_available": torch.cuda.is_available(),
        "peak_rss_bytes_process_high_water": peak_rss,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    original_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        model, model_instance, config = model_report()
        report = {
            "schema_version": 1,
            "benchmark": "ULTRON Phase 1 microbenchmarks",
            "system": system_report(),
            "conditions": {
                "seed": SEED, "warmup_iterations": WARMUP,
                "repetitions": REPETITIONS, "device": "CPU",
                "model_batch_size": 2, "model_sequence_lengths": [16, 32, 64],
                "model": "small random-initialized smoke configuration",
            },
            "tokenizer": tokenizer_report(),
            "dataset": dataset_report(),
            "model": model,
            "checkpoint": checkpoint_report(model_instance, config),
            "inference": inference_report(model_instance),
            "frontend_transfer_size": frontend_report(Path(__file__).resolve().parents[1]),
            "measurement_gaps": [
                "No 60M+ model allocation or target-device profile was performed.",
                "The dataset is synthetic and temporary, not a production corpus.",
                "Peak RSS is a process high-water mark, not a per-component measurement.",
                "Tracemalloc excludes native SQLite and PyTorch allocator memory.",
                "Frontend bytes are transfer-size proxies; no browser page-load timing was measured.",
                "Random initialized model timings are not quality or learned-capability measurements.",
                "No CUDA benchmark was performed in this CPU-only workflow.",
            ],
            "safety": {
                "production_corpus_generated": False,
                "external_data_downloaded": False,
                "external_ai_api_used": False,
                "training_performed": False,
                "optimizer_created": False,
                "optimizer_steps": 0,
                "model_weights_updated": False,
                "remote_jobs_dispatched": False,
            },
        }
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
    finally:
        if torch.get_num_threads() != original_threads:
            torch.set_num_threads(original_threads)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
