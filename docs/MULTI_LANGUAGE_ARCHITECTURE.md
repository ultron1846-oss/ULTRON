# ULTRON Hybrid Language Architecture

## Principle

Use each language where it has a clear engineering advantage. Do not rewrite working components merely to increase the number of languages. The primary architecture remains original and self-contained: no external AI inference APIs, pretrained weights, or opaque model dependencies.

## Language responsibilities

| Language | ULTRON role | Adoption plan |
|---|---|---|
| Python | Model definition, training/inference research, evaluation, data validation, experiment orchestration | Primary AI development language. PyTorch remains the reference implementation and correctness baseline. |
| C++ (and CUDA where available) | Profiling-proven low-level kernels, custom tensor operations, memory/layout-sensitive bottlenecks | Add only after profiling identifies a stable hot path. Keep a Python fallback and parity tests. |
| Rust | Optional lightweight inference/runtime service, safe checkpoint or job-control components, device/edge runtime | Consider after the inference API and deployment requirements stabilize. Do not add a Rust service just to wrap Python without measured benefit. |
| JavaScript / TypeScript | GitHub Pages website, interactive Math Agent, browser-side UI, typed API contracts and validation | Keep the web frontend in JS initially; introduce TypeScript incrementally for new modules if the build/test pipeline supports it. Browser code is not responsible for large-model training. |
| Java / C# | Optional integrations with enterprise systems, Android or Unity clients, if a concrete product requirement appears | Not part of the current core runtime. Avoid maintaining duplicate model implementations. |
| Julia / R | Optional research notebooks, statistical analysis, independent experiment plots and data audits | Research-only tools; results should be reproducible and exported in documented formats. Not required for deployment. |

## Interoperability boundaries

1. Python owns the canonical model behavior, checkpoint format, and reference tests.
2. Native C++/CUDA code must expose a narrow, documented interface and preserve output/gradient parity with the Python reference. Unsupported devices fall back to the reference path.
3. Rust services, if introduced, communicate through versioned local IPC or a documented HTTP API; they must not introduce external AI providers or silently trigger jobs.
4. The website communicates only with explicitly approved ULTRON endpoints. Public pages remain non-executing; training and remote execution stay disabled until separately authorized.
5. Java/C# and Julia/R are optional adapters/research environments, not competing sources of model truth.

## Performance decision gate

Before adopting a lower-level implementation, record:
- baseline hardware, software versions, model configuration and input shape;
- median and p95 latency, throughput, and peak memory;
- correctness parity and numerical tolerance;
- maintenance cost and fallback behavior.

A language change is accepted only when measured benefit or a concrete integration requirement justifies the added build and maintenance burden. Parameter count alone is not a performance or memory guarantee.

## Current status

- Python/PyTorch: active model and benchmark implementation.
- JavaScript: active GitHub Pages frontend and deterministic Math Agent.
- C++/CUDA: targeted optimization option; no new custom kernel is authorized by this architecture note.
- Rust, Java, C#, Julia and R: planned optional tools, not currently integrated.
- No training, dataset generation, cloud execution or remote job is started by this document.
