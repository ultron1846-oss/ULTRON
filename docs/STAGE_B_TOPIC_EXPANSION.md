# Stage B — topic expansion readiness contract

**Status:** preregistration contract only. No Stage B generator, verifier, benchmark dataset, model score or topic mastery is asserted.

Topics: geometry, trigonometry, probability, statistics, linear algebra and number theory. Each topic must be completed independently.

A readiness manifest requires versioned generator/verifier IDs; independent validation flags; a benchmark ID and SHA-256; a split SHA-256; at least 200 held-out examples; and recorded Fable 5.2 baseline results with a hash. The validator checks metadata only. A separate audit must verify that hashes resolve to immutable artifacts, references are mathematically valid, and test examples are leakage-free.

This PR does not generate data, invoke models, train, or call external AI APIs.
