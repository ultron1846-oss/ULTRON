# Lean 4 proof-checking integration plan

**Status: design and interface stub only (2026-11-26).** No Lean toolchain was installed, no proof was run, and no candidate was admitted to trusted knowledge by this work.

## Purpose and scope

Lean 4 is the planned proof-kernel boundary for proof-level university mathematics, including Math 55-style proof exercises. ULTRON's exact polynomial/rational checkers currently emit EXACT_CHECKED; they are not formal proof systems. FORMALLY_VERIFIED is reserved for a future validated Lean kernel receipt.

This plan does not claim coverage of Math 55, theorem translation, proof search, or autonomous proof construction.

## Proposed call flow

1. ULTRON creates a proof candidate tied to the original task and a reviewed formal statement.
2. A local checker adapter receives a source file, theorem identifier, and pinned environment digest.
3. The adapter validates the file path and theorem name, rejects sorry/admit placeholders, and invokes a pinned Lean 4 executable using an argument list (never a shell), a temporary isolated workspace, bounded timeout, and captured diagnostics.
4. The checker returns a typed result: TYPECHECKED, REJECTED, UNAVAILABLE, TIMEOUT, or INVALID_INPUT. A successful type-check is only a result about the named declaration in that exact environment.
5. A future receipt validator binds the result to the candidate ID, formal statement hash, source hash, Lean version, imported environment/mathlib commit hash, checker configuration, and successful kernel result. It must reject missing or mismatched fields.
6. Only a validated proof-kernel receipt may eventually produce FORMALLY_VERIFIED. Candidate status, exact-check certificates, a fake checker, or a free-form string must never admit knowledge.

The existing ultron_core/formal_proof.py is an opt-in local file-checking prototype with preflight and bounded subprocess handling. It is not yet integrated with a receipt validator or the candidate trust policy. ultron_core/lean_interface.py defines only the abstract boundary; it does not launch Lean.

## Result shape

The stub's ProofCheckResult records:
- status and theorem name;
- SHA-256 of the submitted source;
- checker version;
- optional environment SHA-256;
- optional receipt SHA-256;
- diagnostic messages.

A future implementation must also identify the exact Lean toolchain and imported package revisions in the validated receipt. TYPECHECKED from the interface alone is not a trust decision.

## Candidate / receipt integration

The intended receipt should be immutable and versioned. It should include candidate_id, task/statement hash, source hash, theorem name, Lean version, environment digest, checker configuration digest, and kernel exit/result metadata. The receipt validator should recompute hashes, verify the trusted environment identifier, and reject stale or mismatched receipts.

The current FormulaCandidate.can_enter_trusted_knowledge() deliberately returns false. This remains fail-closed until receipt validation is implemented and independently reviewed. The fake checker test exercises only the interface contract and explicitly does not create a receipt.

## Tokenizer and vocabulary readiness

The current math tokenizer is a fixed versioned lexical vocabulary; recognizing a character or token does not mean ULTRON parses or reasons about it. Lean source requires a separate, versioned vocabulary extension rather than silently changing the existing token IDs.

Likely additions include:
- declaration and scope syntax: theorem, lemma, def, example, namespace, section, end, import, open, by;
- binders and type syntax: fun, ∀, ∃, →, ↔, :, :=, =>, ⟨, ⟩, Type, Prop;
- common types and structures: Nat, Int, Rat, Real, Set, Fin, List, Vector;
- university symbols and notation: ℕ, ℤ, ℚ, ℝ, ∈, ∉, ⊆, ∩, ∪, ∅, ≤, ≠, Σ, ∏, ∫, λ, α, β.

The tokenizer extension must be versioned, deterministic, round-trip tested, and compatible with saved checkpoints. Vocabulary growth does not itself implement Lean parsing or theorem semantics.

## Explicitly unsupported

- Natural-language-to-Lean statement translation and proof search.
- General Math 55 coverage or a Math 55 capability claim.
- Trusting unpinned imports, arbitrary environment changes, or network-resolved dependencies.
- Treating sorry warnings, fake checker results, successful process exit without statement review, or an unvalidated receipt as proof.
- Automatically launching Lean from the website or training pipeline.
- Installing Lean, running proofs, or adding a concrete subprocess adapter in this design-only PR.

## Acceptance gates for a future implementation

- Pin Lean 4 and every imported package/mathlib revision.
- Establish a reviewed benchmark of formal statements with expected accepted/rejected results.
- Validate source/theorem binding, timeout and failure paths, and receipt tampering.
- Independently review whether each formal statement matches the intended problem.
- Keep trusted-knowledge admission closed until the receipt validator is implemented and tested.
