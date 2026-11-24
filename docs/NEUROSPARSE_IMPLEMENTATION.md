# NeuroSparse Section C — Prototype Implementation

**Status:** experimental code prototype. It is not trained, not benchmarked for competitive performance, and not evidence of mathematical discovery.

## Components

- Configurable PyTorch sequence model and validated configuration.
- Top-k router with per-expert token gather/dispatch and weighted scatter-add. It skips unselected expert token rows, but Python dispatch overhead can erase theoretical FLOP savings.
- Bounded predictive latent refinement using a fixed MSE threshold. This is not a validated free-energy estimator.
- Dual memory experiment: one fast-weight associative matrix plus a bounded content-addressable episodic key/value store. Both are experimental; neither guarantees perfect recall.
- Typed mathematical expression IR with explicit assumption metadata.
- Hand-authored formula-candidate templates and finite-domain counterexample probes. A successful probe is experimental support, never proof or novelty evidence.
- Training loss and optimizer helpers. The next-token loss ignores the configured padding ID by default (pass a different `ignore_index` or `None` explicitly when needed). Importing the package does not start training.
- Atomic checkpoint file replacement with SHA-256 integrity manifest and weights-only loading. Load only trusted local files.
- CPU/GPU forward/backward smoke tool and optional torch.profiler FLOP/memory reporting.

## Honest accounting

The active expert ratio is top_k / num_experts. The default is 2/8 = 25%, not the proposed <=2% research target. It excludes shared embedding, router, refinement, memory and output weights; it is not the full-model active parameter fraction. No speed, energy or quality advantage is claimed.

The current code is not a fixed 3–5M, 40M or 100M parameter model. There is no tokenizer, deterministic training-data generator, curriculum engine, full symbolic algebra, formal proof kernel, literature novelty search, Lean/Coq/Isabelle adapter, or autonomous theorem discovery. Causal self-attention and learned positional embeddings are now implemented in the architecture follow-up described below. The formula templates are seed examples only.

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


## Read-only memory projection optimization

Read-only memory calls now compute only the query projection. Key and value projections are required only for a write performed while the module is in training mode; they are skipped for ordinary inference and for write requests made while the module is in evaluation mode. This removes two hidden-size linear projections from the common read-only path without changing memory state or recall equations. Regression tests use module hooks to verify the skipped projections in both empty-memory and populated-memory read-only cases. Performance gains remain unquantified until measured on target hardware.


## Core validation and reproducibility hardening

Configuration fields now reject booleans/fractional values where integer dimensions or token IDs are required, and reject non-finite threshold/dropout settings. The routing balance helper validates non-empty top-k assignments, integer index dtype, device consistency, index range and duplicate expert assignments. The predictive refiner validates rank and non-empty dimensions. The expression IR validates node kinds, child tuples, integer atoms, rational literals and symbol identifiers before evaluation. Loss/optimizer helpers reject malformed weights and hyperparameters. The inference benchmark isolates its CPU RNG seed and restores the caller's CPU thread count after execution. These checks improve API safety and experiment reproducibility; they do not make the current prototype a context-aware LLM or a theorem prover.


## Checkpoint validation hardening

Checkpoint save/load now validates non-negative integer step values, checks that serialized configuration matches the model configuration, validates manifest syntax and payload structure before loading, and atomically replaces the checksum manifest through a temporary file. Optimizer restoration now fails explicitly if the caller requests an optimizer restore but the checkpoint contains no optimizer state. The SHA-256 sidecar remains an accidental-corruption check, not an authenticity signature; do not load checkpoints from untrusted sources.


## Accelerator synchronization reduction

The model now skips explicit token min/max checks on accelerator inputs and relies on the embedding operation for index validation; CPU inputs retain the explicit friendly range error. The internal load-balancing call accepts a validation switch: external/default calls still validate index range and uniqueness, while the model disables those scalar checks because indices are produced by PyTorch top-k. Predictive refinement retains CPU early exit but avoids a Python boolean conversion of CUDA activity masks, which would synchronize the device on every refinement iteration. Episodic-memory writes read the ring cursor once per forward and update it once after the sequential write loop rather than synchronizing once per token. These changes reduce host/device synchronization; they do not claim measured throughput gains until benchmarked on accelerator hardware.


## Trusted mathematical knowledge gate

The prototype has no formal proof kernel or verifiable proof-receipt type. Consequently, FormulaCandidate.can_enter_trusted_knowledge() now fails closed for every candidate. A caller-supplied FORMALLY_VERIFIED enum value or free-form evidence string is metadata, not a checked proof. Re-enable trusted admission only when a proof backend can return a structured receipt that ULTRON validates independently.


## Causal sequence architecture — 2026-11-24

The prototype now includes pre-normalized multi-head causal self-attention and learned absolute position embeddings.

- Each block applies causal self-attention before sparse expert routing, predictive refinement and memory recall.
- The boolean attention mask blocks keys at positions strictly later than the current query position. The mask is created on the input device and shared across blocks for that forward pass.
- Learned position embeddings make token order explicit. The configurable max_sequence_length bounds the position table; longer inputs fail with a clear error.
- num_attention_heads is configurable and the configuration rejects hidden sizes that are not divisible by the head count.
- Regression tests check both directions of the causal contract: changing an earlier token can affect later logits, while changing future tokens cannot affect earlier logits.
- This is a small reference implementation using PyTorch MultiheadAttention, not a measured high-performance attention kernel. No flash-attention, KV cache, streaming decode, rotary embeddings, relative positions or long-context scaling is claimed.
- The model remains untrained and still lacks a tokenizer, original deterministic mathematical corpus generator, curriculum, full symbolic algebra, formal proof kernel and demonstrated mathematical capability. Causal attention is a necessary language-modeling prerequisite, not evidence of university-level math ability.

Validation remains the CPU Python regression suite and forward/backward smoke check. These checks do not execute an optimizer step or start training.


### Checkpoint compatibility note

The causal-attention and positional-embedding parameters change the model state and configuration schema. Checkpoint format is now version 2. Version 1 checkpoints from the feed-forward-only prototype are rejected rather than partially loaded or silently initialized; no automatic migration is implemented. This is safe for the current untrained prototype, but a future trained release must provide a deliberate, tested migration or a documented fresh-start boundary.


## Checkpoint and verifier boundary hardening — 2026-11-24

- Checkpoint loading now compares the complete saved state-dictionary key set, tensor types, shapes and dtypes against the target model before calling load_state_dict. This prevents a malformed but checksum-consistent payload from partially mutating the target model before a later shape/key error is raised.
- Finite-domain probing now requires an explicit tuple/list of exact rational samples: integers, rational strings or Fraction values. Floats and booleans are rejected to avoid silently treating binary floating-point approximations as exact mathematical domain points.
- Rational samples are normalized before probing and duplicate equivalent values are rejected, so sample counts cannot be inflated by entries such as 1 and "1/1".
- Regression tests verify that malformed checkpoint tensor shapes leave every target parameter unchanged and that finite-probe domains are exact and unambiguous.
- The SHA-256 manifest remains an accidental-corruption check, not an authenticity signature. Do not load untrusted checkpoint files.


- FormulaCandidate now validates its expression type, enum status, identifier, and immutable tuple-of-string metadata fields at construction. This prevents malformed candidate objects from entering evaluator code through annotation-only assumptions.

- Checkpoint preflight also rejects tensor-layout mismatches and safely formats unexpected non-string state keys in validation errors.

- Finite-domain probing enforces a configurable max_samples cap (default 100,000) before evaluating the Cartesian product, preventing accidental unbounded probe workloads.

- Exact exponent evaluation has a configurable absolute-exponent bound (default 1,024); exceeding it raises an explicit evaluation-limit error instead of silently skipping the sample or attempting unbounded integer growth.



## Mathematical tokenization, deterministic examples and padding — 2026-11-24

The initial foundation is implemented in `ultron_core/math_tokenizer.py` and `ultron_core/data_generation.py`.

### Tokenizer contract
- Version 1 is a fixed, deterministic lexical vocabulary. PAD/BOS/EOS occupy IDs 0/1/2. The remaining token list is source-defined and serialized in order.
- The lexer uses longest-match for explicitly listed multi-character operators and otherwise consumes supported Unicode/ASCII symbols. It preserves whitespace and source spelling; it does not normalize mathematical expressions.
- Numeric literals are digit/operator sequences rather than vocabulary entries per distinct number. Exact spelling such as `1/3` is retained; this is a lexical encoding, not an exact-number semantic object.
- `2x`, `2*x`, and `2 × x` remain distinct. Unary minus and subtraction are not parsed or conflated.
- Unknown characters, invalid token IDs, duplicate vocabulary entries, reordered reserved tokens and unsupported vocabulary versions fail explicitly.
- This is not a parser, complete LaTeX tokenizer, semantic analyzer or mathematical evaluator.
- The existing expression IR now supports strict recursive dictionary serialization, canonical structural JSON and SHA-256 structural hashes. The hash is structural, not an algebraic-equivalence hash.

### Initial generator contract
- Version 0.1.0 supports integer arithmetic, exact rational arithmetic and one-variable linear equations only.
- Each output is reproducible from generator version, seed, topic configuration and index. Example IDs hash canonical generation inputs.
- Exact answers use `fractions.Fraction`; the validator reparses emitted text with a separate regular-expression path and recomputes the answer exactly.
- Status `semantically_checked` means only that this limited validator agrees with the target. It is not formal verification.
- JSONL rows are canonicalized, and a deterministic manifest records schema/generator version, seed, topics, topic counts, count and SHA-256. A hash detects accidental modification, not authenticity.
- No large corpus is generated as part of tests.

### Padding contract
`NeuroSparseModel.forward(..., attention_mask=...)` accepts a boolean `[batch, sequence]` mask where True denotes a real token. The inverse is passed as PyTorch's key-padding mask alongside the causal mask. Every batch row must contain at least one real token. Masked query attention outputs are zeroed to handle left-padding rows with no causally visible valid key. The same valid-token mask prevents padded positions from being written into episodic memory. Callers must supply the mask for padded batches; omitting it means every input position is treated as valid.

### Remaining limitations
No parser-to-IR conversion, semantic handling of calculus/linear algebra/discrete/proof notation, curriculum scheduler, proof kernel, large generated corpus, or training has been implemented. Lexically recognizing a symbol does not imply its mathematical semantics are implemented. The model remains untrained.



### CI verification — PR #18
- GitHub Actions Python regression suite: 88 tests passed.
- CPU forward/backward smoke: passed on CPU with batch 2 and sequence length 8; workflow output explicitly reports no optimizer step or training run.
- Node.js test workflow: passed.
- Local execution was not claimed because the working environment could not resolve github.com for a repository clone.
- Merged as PR #18 at main commit `38a4b30c28f90998ac5f092fe340df512963fdfc`.



## Mathematical parser and conservative simplifier — 2026-11-24

### Parser
`ultron_core/math_parser.py` implements a recursive-descent parser over the existing `MathTokenizer` tokens and emits the existing `Expr` nodes. It does not call Python `eval` or `exec`.

Supported grammar:
- Integer and finite decimal literals. Decimal values are converted to exact `Fraction` numerator/denominator IR atoms.
- Contiguous identifiers containing letters and trailing digits; simple subscripts such as `x_1` and `x_{12}`.
- Parenthesized expressions, unary signs, `+`, `-`, `*`, `/`, `×`, `·`, `÷`, `^`, Unicode superscript integer powers, implicit multiplication between adjacent factors, and one top-level equality.
- Precedence is conventional: exponentiation binds more tightly than unary minus and is right-associative. Contiguous letters are one identifier, so `velocity` is not silently rewritten as `v*e*l*o*c*i*t*y`.
- Supported lower-case Greek LaTeX aliases map to Unicode symbol names. Unsupported TeX commands fail explicitly.
- Parser defaults are capped at 100,000 source characters, 512 lexer tokens and 128 recursive nesting levels. These are defensive limits, not a throughput benchmark.

The parser deliberately rejects function-call syntax, inequalities, set membership, general LaTeX fractions, matrices, calculus, summation/limit notation and proof syntax. A token recognized by the lexer is not necessarily accepted by the parser.

### Simplifier
`ultron_core/symbolic.py` applies bounded exact constant folding and a small set of local identities:
- flatten associative addition/multiplication nodes and combine exact numeric constants;
- remove additive zero and multiplicative one;
- simplify `x - 0`, `x / 1`, `x ^ 1`, and double negation;
- preserve potentially undefined subexpressions (for example, it does not reduce `0 * (1 / 0)` to zero);
- cap constant-folding exponent magnitude at 64 and leave division-by-zero or over-budget constants explicit.

It does not distribute, factor, reorder symbolic terms, cancel factors, infer domains, or prove equivalence. Test comparisons over finite rational samples are regression checks only.

### Evaluator boundary
The existing exact evaluator now rejects `0^0` as undefined, as well as division by zero and non-integer exponents. It remains a scalar evaluator, not an equation solver, CAS, proof kernel or calculus engine. FormulaCandidate trusted-knowledge admission remains fail-closed.

No training, optimizer step, corpus generation, external AI API, pretrained weight, cloud job, remote execution or website change was performed for this stage.



### Parser milestone CI verification
- GitHub Actions Python regression suite: 104 tests passed.
- CPU forward/backward smoke: passed on CPU; workflow output confirms no optimizer step or training run.
- Node.js test workflow: passed.
- Verification was executed against implementation commit `e5fe00a6cc1afc2f3a9345f9469ba951009d6b53`; a subsequent README/notes-only update is included in the current PR and must pass its own required checks before merge.
- No local execution, training, dataset generation, external API, pretrained weights or remote execution is claimed.


## Typed comparison and function-call IR — 2026-11-24

The expression IR and parser now represent one top-level comparison using distinct node kinds for equality, inequality, and ordered comparisons. ASCII `!=`, `<=`, `>=` and Unicode `≠`, `≤`, `≥` map to explicit typed nodes. Chained comparisons are rejected rather than assigned an implicit associativity.

A bounded unary-call grammar recognizes `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `exp`, `ln`, `log`, `sqrt`, and `abs`. Calls are stored as `CALL` nodes with a validated function name and one argument. This is syntax and IR support only: the exact rational evaluator deliberately rejects all function calls because transcendental values and their domains/branches need a separate semantic design. No numerical approximation or domain assumption is silently introduced.

The exact evaluator can evaluate comparisons only when both operands are exact scalar rational expressions. Comparisons nested inside comparisons are rejected. Finite-domain candidate probing remains equality-only and therefore does not treat inequalities as proof candidates. The symbolic simplifier preserves comparison and function-call nodes without rewriting them.

Tests cover ASCII and Unicode comparisons, chained-comparison rejection, function-name allowlisting, nested function-call parsing, and explicit evaluator rejection. This stage does not add trigonometric simplification, numerical function evaluation, domain inference, equation solving, or formal proof.


## Exact sparse-polynomial foundation — 2026-11-24

ultron_core/polynomial.py adds bounded exact sparse-polynomial algebra over Fraction coefficients. It converts the existing Expr IR and does not introduce a second parser or expression tree.

- A monomial is a lexicographically sorted tuple of (symbol, positive integer exponent) pairs. A polynomial is an immutable sorted tuple of unique monomials with non-zero exact rational coefficients.
- Addition collects like terms and removes zero coefficients. Multiplication merges monomial exponents and collects cancellations. Non-negative integer powers use exponentiation by squaring.
- Constant rational division is supported only when the denominator reduces to a non-zero constant polynomial. Variable-polynomial denominators, zero denominators, negative/fractional/non-literal powers, function calls, comparisons and assumption-bearing expressions are rejected.
- Exact evaluation accepts integer/Fraction environments only. to_expr() exports deterministic structural IR; polynomial equality is exact canonical representation equality.
- PolynomialLimits bounds total degree, term count and individual exponent. Defaults are degree 64, 4,096 terms and exponent 64. Absolute hard ceilings (including direct object construction) are degree 256, 16,384 terms and exponent 256. Operations check budgets while constructing intermediate products and raise PolynomialError rather than silently truncating.

This is a polynomial ring over rational coefficients and finitely many named variables. It is not a rational-function engine, algebraic-number system, general CAS, equation solver or proof kernel. Non-constant denominators are rejected so denominator-domain restrictions are not silently discarded. Canonical equality applies only after both expressions are soundly converted into this supported polynomial domain.

The parser's stale inline comment about function-call syntax was corrected: supported calls are represented as typed CALL nodes, but the exact evaluator still refuses to evaluate them. No training, optimizer step, corpus generation, external API, pretrained weights, cloud job, remote execution, website, Supabase or authentication change was performed.


## Domain-preserving exact rational expressions — 2026-11-24

`ultron_core/rational.py` adds a rational-function representation over the existing exact sparse-polynomial ring.

- State is an exact polynomial numerator, a non-zero exact polynomial denominator, and a canonical tuple of polynomials required to be non-zero.
- Construction adds each nonconstant normalized denominator to the restriction set; non-zero constant denominators are omitted because they can never vanish. Division adds the divisor's numerator, because the divisor must be non-zero wherever it is evaluated. Integer exponent zero adds the base numerator as a restriction; negative powers swap numerator/denominator and preserve the same non-zero condition.
- Addition and multiplication use cross-products without cancellation. This may grow expressions, but avoids losing excluded points. All polynomial products inherit configured degree/term/exponent budgets; the restriction set has a hard cap of 256.
- Denominator scalar normalization and scalar-normalized restriction deduplication provide deterministic structural representation. This is not a complete canonical form for rational functions; no polynomial GCD or factorization is claimed.
- Exact evaluation checks every preserved restriction before dividing. Violations raise RationalDomainError rather than returning a value from an enlarged domain.
- The converter accepts integer/rational/symbol atoms, arithmetic, division and integer powers. Function calls, comparisons and assumptions fail closed.

Important semantics: (x/x) is represented with the condition (x\ne0), and ((x^2-1)/(x-1)) retains (x\ne1); neither is simplified by cancelling factors. (1/(1/x)) also retains the inner condition (x\ne0). This design preserves partial-function domains under nested operations.

Limitations: no polynomial GCD, cancellation, multivariate division, equation solving, calculus, algebraic-number semantics, or proof kernel. It is not a general CAS. No training or optimizer step is performed by these operations.


## Exact univariate polynomial division and GCD — 2026-11-24

The Polynomial API now provides bounded univariate Euclidean division over exact Fraction coefficients.

- divide_univariate(divisor) returns (quotient, remainder), satisfying the reconstruction identity (A=QB+R), and the strict degree bound on a nonzero remainder.
- exact_divide_univariate raises PolynomialError unless the remainder is zero.
- gcd_univariate implements the Euclidean algorithm and normalizes the result to monic form over the rational field.
- Only one variable is allowed across both operands. Multivariate monomials, mixed variables, zero divisors, mismatched requested variables and budget violations fail explicitly.
- The implementation uses exact Fraction coefficient division; it does not use floating point.

RationalFunction factor cancellation is intentionally not included in this change. The next stage can use the univariate GCD to reduce numerator/denominator while retaining every original non-zero domain constraint. Multivariate GCD and multivariate polynomial division remain unsupported.


## Domain-safe univariate rational reduction — 2026-11-24

RationalFunction.cancel_common_univariate_factors() now uses Polynomial.gcd_univariate() and exact_divide_univariate() to cancel a common univariate factor from numerator and denominator.

The returned RationalFunction retains every original non-zero domain constraint, including factors that disappeared from the reduced denominator. Examples:
- (x/x) reduces to (1), but the stored (x\ne0) condition still rejects (x=0).
- ((x^2-1)/(x-1)) reduces to (x+1), but the stored (x\ne1) condition still rejects (x=1).
- ((x(x-1))/(x(x+1))) reduces to ((x-1)/(x+1)), while retaining both original excluded points (x=0) and (x=-1).

The operation rejects multivariate numerator/denominator terms. It is idempotent for the tested canonical representations. It does not establish arbitrary symbolic equivalence, prove identities, or add multivariate factorization.


## Exact real-root counting with Sturm sequences — 2026-11-24

Polynomial now exposes:
- derivative_univariate(variable=..., limits=...): exact formal derivative for one named variable.
- sturm_sequence_univariate(variable=..., limits=...): exact signed remainder sequence over (mathbb{Q}).
- real_root_count_univariate(lower, upper, variable=..., limits=...): exact count of distinct real roots in the open rational interval ((lower, upper)).

The root-count operation requires integer/Fraction endpoints in strictly increasing order and rejects intervals whose endpoints are roots. Sign variations omit zero-valued sequence members at an endpoint, as in Sturm's theorem. Repeated roots are counted once. A nonzero constant has zero roots; the zero polynomial is rejected because its zero set is not finite.

This does not numerically approximate roots or return isolating intervals. Multivariate root counting, algebraic-number objects, minimal-polynomial arithmetic and formal proof receipts are not implemented. The algorithm's correctness is covered by regression examples, but the implementation is not independently machine-checked by a proof kernel.


## Exact real-root isolation — 2026-11-24

Polynomial.isolate_real_roots_univariate(lower, upper, max_width=Fraction(1, 1000), max_depth=64, max_intervals=4096) returns a sorted tuple of disjoint rational intervals isolating every distinct real root in the requested open interval.

Algorithm:
1. Validate exact rational bounds and require non-root endpoints.
2. Compute the exact derivative and polynomial GCD to obtain a square-free polynomial, so repeated roots are isolated once.
3. Count roots with the exact Sturm sequence.
4. Bisect using rational midpoints. If a midpoint is an exact root, emit the degenerate interval (r, r), divide out (x-r), and continue on the remaining left/right intervals.
5. Stop only when a non-degenerate interval contains exactly one root and its width is at most max_width.

The implementation has explicit depth and processed-interval budgets and uses Fraction arithmetic only. It rejects multivariate inputs, the zero polynomial, inexact float bounds, root endpoints and exhausted budgets. It returns isolating intervals, not decimal root approximations or algebraic-number objects. It is not a formal proof-kernel receipt.


### Root-isolation endpoint regression hardening

A review found a boundary case when a rational root is detected exactly at a split point and a nearby distinct root remains in the adjacent interval. The reduced square-free polynomial no longer vanishes at that split point, but the original polynomial still does. Before returning a non-degenerate interval, the isolator now moves any such endpoint inward using exact rational candidates and Sturm counts, without crossing the remaining root. If the configured depth budget cannot establish a non-root endpoint, isolation fails closed. A regression test covers two closely spaced rational roots with a deliberately wide requested interval.


## Exact real algebraic number representation — 2026-11-24

ULTRON now exposes `RealAlgebraicNumber`, a bounded exact representation of one real root of a univariate rational-coefficient polynomial.

- A non-degenerate rational interval must have non-root endpoints and contain exactly one distinct real root, verified with the exact Sturm counter.
- Exact rational roots can be represented as degenerate intervals `(r, r)`.
- `refine()` bisects with rational arithmetic and detects an exact rational midpoint.
- `same_value_as()` decides equality using exact rational evaluation or the polynomial GCD over the overlap of isolating intervals.
- `compare_to()` orders distinct represented roots by exact interval refinement, with a caller-controlled refinement budget.

The defining polynomial is **not asserted to be minimal or irreducible**. The representation supports exact affine transforms and bounded arithmetic via resultants. It does not provide minimal-polynomial computation, multivariate algebraic numbers, or formal proof receipts. Comparisons currently require both values to use the same variable name. No floating-point arithmetic is used.


A further regression covers an exact rational root encountered during the inward endpoint-adjustment search itself. The isolator now emits that root as a degenerate rational interval instead of passing a root endpoint into the Sturm counter.


## Exact algebraic arithmetic via resultants — 2026-11-24

The algebraic-number layer now exposes exact addition, subtraction, multiplication, division and reciprocal operations. For addition and subtraction it forms a Sylvester resultant from P(x) and Q(z-x). For multiplication it uses P(x) and x^n Q(z/x). Division first constructs the reciprocal algebraic value using x^n Q(1/x), after certifying that the selected denominator root is nonzero, and then invokes multiplication.

The resultant may retain repeated factors and extraneous factors; the implementation does not assert minimality or irreducibility. It computes a rational interval enclosure of the intended result and uses the exact Sturm counter to require exactly one distinct real root in that interval. If the interval is too broad or has a root endpoint, operand intervals are refined with exact rational bisection. If certification cannot complete within the configured budget, the operation fails closed.

The Sylvester determinant uses a subset dynamic program with O(n 2^n) state transitions and is capped at matrix dimension 10. Sparse polynomial degree, exponent and term limits remain active. All coefficient and interval arithmetic is over Q; no floating-point approximation is used.

Public API:
- RealAlgebraicNumber.add(other, max_refinements=4096, limits=...)
- RealAlgebraicNumber.subtract(...)
- RealAlgebraicNumber.multiply(...)
- RealAlgebraicNumber.divide(...)
- RealAlgebraicNumber.reciprocal(...)
- Operators +, -, *, / accept another RealAlgebraicNumber.

The implementation intentionally does not claim a minimal polynomial, irreducibility, general multivariate algebraic-number support, a complete computer algebra system, or a formally verified proof kernel. Regression tests include conjugate multiplicities, positive-root selection, reciprocal and quotient cases, rational operands, cancellation, zero division and resource exhaustion.
