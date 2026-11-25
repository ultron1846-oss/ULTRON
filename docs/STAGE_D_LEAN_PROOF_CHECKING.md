# Stage D — local Lean proof-checking adapter

**Status:** local checker adapter and preflight tests only. No Lean toolchain was installed or invoked in CI, and no proof benchmark or proof-search model is claimed.

`ultron_core/formal_proof.py` provides:
- source preflight for a named theorem/lemma;
- nested Lean comment and string removal before rejecting `sorry`/`admit` placeholders;
- an explicit, opt-in call to a local Lean executable with argument-list invocation (no shell) and a bounded timeout;
- separate results for unavailable Lean, timeout, source rejection, compiler failure and successful type-checking.

A successful result means the named source file was accepted by the specified local Lean invocation. It does not prove that the theorem statement accurately represents the original natural-language problem, nor does it search for proofs. Imported modules and the Lean environment are part of the trust boundary. Stage D requires a frozen theorem benchmark, independent statement review, proof validity scoring and a measured baseline before any capability claim.

No training, data generation, external AI API or remote execution is performed.
