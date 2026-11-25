# Path to Fable 5.2 — ULTRON Math Capability Roadmap

**Status:** Stage A is the active target; it is not yet passed.  
**Budget target:** $0 for the initial narrow-topic phase.  
**Training state:** Not authorized or started by this roadmap.  
**Comparison target:** Fable 5.2, evaluated under a documented, reproducible protocol.

## Objective

Build ULTRON's math capability in measurable stages. The goal is to outperform the comparison model on selected, clearly bounded math topics before broadening coverage. A topic is not considered mastered because a command, curriculum card, or verifier exists; it must pass held-out evaluation.

Parameter count is a capacity choice, not an intelligence score. Scale the model only when benchmark results, memory estimates, and available compute justify it.

## Stage A — Win narrow topics (current plan, $0)

**Initial topics:** arithmetic, algebra, and basic calculus, supported by exact or independently checked verification where applicable.

For each topic:

1. Define the task scope and supported input/output format.
2. Create a deterministic or otherwise auditable data generator.
3. Validate generated answers independently; reject invalid examples.
4. Build a held-out benchmark split with prompt-disjoint examples and no training leakage.
5. Compare ULTRON and Fable 5.2 on the same benchmark, prompts, and scoring rules.
6. Report accuracy, attempted coverage, invalid outputs, abstentions, and verifier failure rates separately.

**Gate:** ULTRON must beat Fable 5.2 on the measured score for each topic, with a predeclared statistical decision rule and no material regression in validity or coverage. Publish sample counts, confidence intervals, model/configuration details, and the evaluation date. Do not claim a win from a tiny or contaminated test set.

**Current reality:** The browser Math Agent is a deterministic arithmetic and limited linear-equation prototype. The Python generator and exact evaluators cover only a narrow set of synthetic task families. Basic calculus coverage and an end-to-end neural-model benchmark against Fable 5.2 are not yet established. Stage A remains in progress.

## Stage B — Widen the topics

Add, in measured increments:

- Geometry
- Trigonometry
- Probability
- Statistics
- Linear algebra
- Number theory

Each topic must have its own:

- Explicit capability specification and limits
- Independently tested verifier/checker
- Validated data generator or curated source with provenance
- Train/validation/test separation
- Benchmark and baseline comparison
- Regression tests, including malformed and unsupported inputs

**Gate:** Topic-specific benchmark and verifier pass; report performance and known failure modes before marking the topic available.

## Stage C — Harder reasoning

Progress from multi-step word problems to competition-style problems.

- Add structured problem decomposition and solution planning.
- Use tool-assisted computation only through allow-listed, bounded tools.
- Verify intermediate and final results where possible.
- Test on held-out, difficulty-stratified sets and adversarial variants.
- Consider a model of approximately **1B+ parameters** only when Stage A/B results show that scaling is likely to help and the hardware/resource budget is documented.

**Gate:** Demonstrated improvement on unseen multi-step tasks, not just longer explanations or increased parameter count. No model-size increase is automatic.

## Stage D — Proofs and research-style mathematics

Add a proof assistant/checker such as **Lean** as a formal verification layer.

- Translate supported claims into formal statements.
- Require the checker to accept the proof term before labeling a proof verified.
- Keep informal explanations separate from formal proof status.
- Track translation failures and unsupported mathematics explicitly.
- Build proof benchmarks with independently checked theorem statements and proof validity.

This stage comes last because proof formalization and reliable proof search are substantially more demanding than exact-answer arithmetic or algebra.

**Gate:** The formal checker validates the proof artifact. A natural-language answer, plausible derivation, or model confidence is not a proof.

## Benchmark protocol and fairness

- Use a frozen benchmark version and record the date and exact Fable 5.2 model identifier/settings available at evaluation time.
- Keep test examples private or generated after the model's training cutoff where feasible; prevent benchmark contamination.
- Give both systems equivalent prompts, allowed tools, time limits, and scoring.
- Score correctness, coverage, abstention, and invalid output separately.
- For exact math, normalize equivalent exact forms carefully; do not rely on brittle string matching.
- Use enough examples for meaningful confidence intervals and publish the sample size.
- Re-run a second independent verification pass on benchmark scoring and answer keys.
- Do not describe ULTRON as generally better than Fable 5.2 based on narrow-topic wins.

## Resource and authorization boundaries

- Stage A targets **$0** and uses only resources actually available; free-tier capacity is not guaranteed.
- The >60M foundation configuration is currently a proposed untrained configuration. Larger sizes, including 1B+, require fresh parameter, memory, and compute estimates.
- No external AI inference API, pretrained weights, or borrowed model is permitted for ULTRON's core intelligence.
- This roadmap does not authorize data generation, optimizer steps, model training, or remote jobs. Those remain disabled until separately approved.
- Finish the frontend and required device/browser acceptance before training work.

## Next implementation steps

1. Audit the current arithmetic/algebra task scope and exact evaluator against Stage A requirements.
2. Specify and independently test a basic-calculus task family and verifier before adding it to any benchmark.
3. Establish a frozen, leakage-resistant Stage A benchmark and score ULTRON and Fable 5.2 under matched conditions.
4. Publish baseline results and blockers; only then choose the next model or data improvement.
5. Update this roadmap and the repository README after each meaningful milestone.
