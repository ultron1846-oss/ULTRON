# NeuroSparse Section C — Prototype Implementation

**Status:** experimental code prototype. It is not trained, not benchmarked for competitive performance, and not evidence of mathematical discovery.

## Components

- Configurable PyTorch sequence model and validated configuration.
- Top-k router with per-expert token gather/dispatch and weighted scatter-add. It skips unselected expert token rows, but Python dispatch overhead can erase theoretical FLOP savings.
- Bounded predictive latent refinement using a fixed MSE threshold. This is not a validated free-energy estimator.
- Dual memory experiment: one fast-weight associative matrix plus a bounded content-addressable episodic key/value store. Both are experimental; neither guarantees perfect recall.
- Typed mathematical expression IR with explicit assumption metadata.
- Hand-authored formula-candidate templates and finite-domain counterexample probes. A successful probe is experimental support, never proof or novelty evidence.
- Training loss and optimizer helpers. Importing the package does not start training.
- Atomic checkpoint file replacement with SHA-256 integrity manifest and weights-only loading. Load only trusted local files.
- CPU/GPU forward/backward smoke tool and optional torch.profiler FLOP/memory reporting.

## Honest accounting

The active expert ratio is top_k / num_experts. The default is 2/8 = 25%, not the proposed <=2% research target. It excludes shared embedding, router, refinement, memory and output weights; it is not the full-model active parameter fraction. No speed, energy or quality advantage is claimed.

The current code is not a fixed 3–5M, 40M or 100M parameter model. There is no tokenizer, attention/position mechanism, deterministic training-data generator, curriculum engine, full symbolic algebra, formal proof kernel, literature novelty search, Lean/Coq/Isabelle adapter, or autonomous theorem discovery. The formula templates are seed examples only.

## Checks

Install a PyTorch wheel suitable for the target CPU/GPU, then run from repository root:

    python -m unittest discover -s tests/python -v
    python -m ultron_core.smoke --device cpu --batch 2 --sequence 16
    python -m ultron_core.smoke --device cuda --profile

The smoke tool performs forward and backward propagation only. It performs no optimizer step, training loop, corpus generation, remote job or external AI API call. CUDA requires a CUDA-enabled PyTorch installation and compatible GPU.

## Known limitations

1. The Python expert dispatch and sequential fast-memory writes are reference implementations, not optimized GPU kernels.
2. The predictive halting threshold is fixed and needs calibration and stability analysis.
3. Fast-weight memory is lossy; episodic memory is bounded and overwrites old slots.
4. The finite-domain verifier cannot prove identities or establish mathematical novelty.
5. The checkpoint integrity manifest detects accidental modification but is not a signature or defense against a malicious writer who can replace both files.
6. No training or remote execution was performed for this milestone.
