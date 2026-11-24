# ULTRON Section D — Benchmark, ablation and statistical protocol

**Status:** protocol and inference-only measurement harness. No empirical performance result is asserted. No training, optimizer step, cloud execution, external AI API or external dataset is used.

## 1. Questions Section D must answer

1. Does sparse expert routing reduce *measured* compute or latency after dispatch overhead?
2. Does predictive refinement improve task quality enough to justify its additional compute?
3. Does fast-weight/episodic memory improve exact recall and transfer without unacceptable latency or memory cost?
4. Are any gains reproducible across seeds, sequence lengths, batch sizes and device classes?
5. Does the complete system improve mathematical task performance at a fixed compute or latency budget?

A lower selected-expert ratio alone is not evidence of lower end-to-end FLOPs, energy, latency or cost.

## 2. Current harness

Run from the repository root:

```bash
python -m ultron_core.benchmark --device cpu --batch 2 --sequence 16 --warmup 10 --iterations 50
python -m ultron_core.benchmark --device cuda --batch 2 --sequence 128 --warmup 20 --iterations 100
python -m ultron_core.benchmark --device cpu --iterations 50 --output benchmark-results/cpu-smoke.json
```

The harness:
- seeds Python-independent Torch input generation and Torch model initialization;
- switches the model to evaluation mode and uses `torch.inference_mode()`;
- performs warm-up separately from timed iterations;
- synchronizes CUDA around each measured call;
- reports every latency sample, median, mean, sample standard deviation, min/max and a seeded percentile-bootstrap 95% interval for the median;
- reports throughput, total/shared/expert parameter counts, CUDA peak allocated memory when applicable, and the exact environment/configuration;
- explicitly records that no training or optimizer step occurred.

The harness uses random token IDs only to exercise tensor shapes. They are not a language corpus, math curriculum or quality-evaluation dataset. CPU and CUDA results must be stored separately and must never be compared as if they were the same hardware.

## 3. Parameter and compute accounting

For (E) experts and top-(k) dispatch, the selected-expert weight fraction per token is:

[
r_{expert} = \frac{k}{E}.
]

The prototype default (k=2,E=8) gives (r_{expert}=0.25) (25%). This is only the fraction of expert subnetworks selected for a token. It is **not** the active fraction of all model parameters.

The harness reports:
- (P_{total}): all unique model parameters;
- (P_{expert}): parameters contained in expert subnetworks;
- (P_{shared}=P_{total}-P_{expert});
- (P_{expert,selected}^{estimate}=P_{expert}\,k/E);
- (P_{active}^{estimate}=P_{shared}+P_{expert,selected}^{estimate}).

The last two are static structural estimates. They are not a profiler-derived count of executed multiply-adds. They do not account for variable refinement depth, memory reads/writes, padding, router work, kernel fusion, dispatch copies, skipped operations, cache behavior or hardware utilization. Report profiler-measured FLOPs and device counters separately when available. Never label the estimate “measured active parameters” or infer energy from it.

## 4. Required ablation matrix

These are **future controlled experiments**, not capabilities exposed by the current Section C model. The model needs explicit, tested switches before these rows can be run. Each row must use the same initialized weights where mathematically meaningful, identical input examples, and the same compute budget.

| ID | Variant | Change isolated | Required control |
|---|---|---|---|
| A0 | Dense expert reference | Evaluate all experts | Same expert weights and aggregation rule |
| A1 | Sparse top-k | Current selected-expert dispatch | Compare against A0 |
| A2 | Sparse top-1 / top-2 / top-4 | Routing sparsity | Hold expert count and width fixed |
| A3 | No fast-weight memory | Remove fast-weight read/write | Keep episodic memory setting fixed |
| A4 | No episodic memory | Remove exact key/value retrieval | Keep fast-weight setting fixed |
| A5 | No memory | Remove both memory paths | Compare A3/A4 and full |
| A6 | Fixed refinement depth | Disable adaptive halt | Match average refinement steps where possible |
| A7 | Adaptive refinement | Current threshold-based halt | Report steps/token and error trajectory |
| A8 | No refinement | Bypass predictive refiner | Same routed representation |
| A9 | Full prototype | All current components | Reference configuration |

Ablation switches must not silently change tensor shapes, parameter initialization, optimizer state, data order or task sampling. For memory ablations, reset state between independent examples and define whether memory is allowed to persist within an example. For routing ablations, report overflow/drop behavior (currently no explicit capacity/drop policy) and token-to-expert assignment histograms. For refinement, report actual iterations per token, not only a batch maximum.

## 5. Benchmark suite and outcome measures

### Systems performance
- End-to-end inference latency: median, p90/p95, and 95% confidence interval.
- Throughput: tokens/s and completed examples/s.
- Peak allocated and reserved device memory; host RAM where measurable.
- Forward FLOPs/MACs from a documented profiler; separate measured from estimated values.
- Expert dispatch time, router time, memory time, refiner time and output-head time.
- Energy per example/token only when measured using a named, calibrated hardware interface; otherwise mark unavailable.
- Compile/cold-start time and steady-state time reported separately.
- Batch sizes 1, 2, 4, 8 and sequence lengths 32, 128, 512, 1024 where device memory permits. Record skipped configurations and OOMs; do not silently drop them.

### Mathematical capability
Use deterministic, versioned splits with no train/test leakage:
- arithmetic and algebraic manipulation;
- equations and inequalities;
- calculus and multivariable calculus;
- linear algebra;
- discrete mathematics and combinatorics;
- probability/statistics;
- real and complex analysis;
- abstract algebra and number theory;
- ODE/PDE and numerical methods;
- proof construction and proof checking.

Report exact-answer accuracy, symbolic equivalence rate, proof-check success, counterexample detection rate, calibration/error rate, and abstention rate. Separate routine exercises, composition/generalization tests, adversarial edge cases and held-out theorem/proof tasks. A proof score counts only if an independent trusted checker accepts the proof under explicit assumptions. Numerical agreement is not proof.

No external generated dataset or AI API may be used to create ULTRON's training data. Benchmark items must be authored or deterministically generated by ULTRON's own approved generator, versioned, and independently reviewed. Public benchmark datasets, if later considered, require a separate explicit data-source decision and leakage review.

## 6. Statistical design

- Use at least 5 independent initialization/data-order seeds for quality experiments; increase this when power analysis indicates insufficient power.
- Pair variants by seed, example, order and hardware; compare per-example paired outcomes.
- Report mean and standard deviation for approximately symmetric metrics; median and IQR for skewed latency; include 95% confidence intervals and raw sample counts.
- For paired continuous outcomes, use paired bootstrap intervals and/or a pre-registered paired test. For binary correctness, report paired discordance and an appropriate paired proportion test.
- Correct for multiple comparisons across ablations (e.g. Holm family-wise correction). Mark exploratory analyses as exploratory.
- Pre-register primary outcomes, exclusion rules, minimum effect of interest and stopping rules before inspecting test results.
- Use a held-out test set only once for final confirmation. Tune thresholds on validation data, never on the final test set.
- Report all seeds, failed runs, OOMs, timeouts, hardware, software versions, power mode, thread counts, precision, batch/sequence shape and command line.
- Do not treat tokens, batches or repeated timings from one initialization as independent training seeds.

A timing run should use at least 10 warm-up iterations and 50 measured iterations for preliminary screening. Final performance claims should use at least 5 independent process launches per configuration, randomized/interleaved configuration order, and enough timed observations to obtain a stable interval. These are minimum protocol defaults, not a substitute for a power analysis.

## 7. Acceptance gates

No architectural component is accepted as an improvement solely because it reduces a proxy metric.

1. **Correctness gate:** no regression in numerical stability, output shape, deterministic replay, memory isolation or checkpoint compatibility.
2. **Quality gate:** the pre-registered primary mathematical metric is non-inferior within a predeclared margin; any claimed improvement has a confidence interval excluding zero after multiplicity correction.
3. **Systems gate:** end-to-end latency or measured FLOPs improve at the target workload; report memory and energy trade-offs. Dispatch overhead must be included.
4. **Robustness gate:** improvement holds across independent seeds and at least two relevant workload shapes; no hidden collapse to a subset of experts.
5. **Reproducibility gate:** a clean rerun reproduces the result within the predeclared tolerance, with full metadata and raw results retained.

The <=2% active-parameter objective remains a research target, not a current achievement. Even if reached, it does not pass the systems or quality gates by itself.

## 8. Current limitations and next engineering prerequisites

The current implementation has no configurable dense-all-expert reference, no public ablation switches, no task-quality benchmark corpus, no energy instrumentation, and no calibrated FLOP accounting. The Section D harness therefore measures only baseline inference behavior on synthetic token IDs. It does not produce ablation comparisons or mathematical-quality results.

Before controlled ablations:
1. Add explicit feature flags for routing, fast-weight memory, episodic memory and predictive refinement, with tests proving each flag bypasses only its named subsystem.
2. Add a dense expert reference path using identical expert weights and a documented aggregation rule.
3. Add hooks/counters for per-token expert assignments, per-token refinement steps, memory reads/writes and component wall time.
4. Define and review the deterministic math-task generator and evaluation split protocol.
5. Add a result schema/version validator and preserve raw per-run JSON.
6. Only after those controls are validated should training or large-scale experiments be proposed. Training still requires separate explicit authorization.

## 9. Interpretation rule

A successful script execution means only that the benchmark harness ran. It does not demonstrate a trained model, a faster model, energy efficiency, university-level mathematics, novel formula discovery or proof capability.
