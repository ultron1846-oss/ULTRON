# AI Brain Status

## Current state

ULTRON contains an **experimental untrained neural sequence-model prototype** in `ultron_core/model.py`, alongside deterministic mathematical parsing, exact arithmetic, symbolic/algebraic utilities, a narrow deterministic data generator, and finite-domain candidate probing.

This is not a trained AI brain. The model has not demonstrated university-level mathematical reasoning, theorem proving, formula discovery, or general intelligence. Deterministic verified outputs and model-generated guesses must remain clearly separated.

## Required system boundaries

1. Input normalization and problem classification.
2. Mathematical operation planner.
3. Deterministic math execution and independent answer verification.
4. Structured knowledge retrieval with source and prerequisite fields.
5. Explanation generation from verified steps.
6. Learner adaptation based on recorded evidence.
7. Original neural model as optional assistance, never the authority for verified results.
8. Controller recording which component produced each answer and which checks passed.

Actual training remains disabled absent separate explicit authorization.
