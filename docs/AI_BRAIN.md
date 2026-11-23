# AI Brain Status

## Current state

There is no AI brain or neural model in the repository. The dashboard, arithmetic parser, and fixed practice item are ordinary deterministic application code. No pretrained model, pretrained weights, external AI API, or training dataset is used.

## Proposed future boundaries

Keep these as separate components with explicit interfaces:

1. Input normalization and problem classification.
2. Mathematical operation planner.
3. Deterministic math execution and independent answer verification.
4. Structured knowledge retrieval with source and prerequisite fields.
5. Explanation generation from verified steps.
6. Learner adaptation based on recorded evidence.
7. An original neural model as optional assistance, never as the authority for a verified result.
8. A controller that records which component produced each answer and which checks passed.

These are design directions, not implemented features. A model proposal requires a separate research note and measurable evaluation criteria. Actual training remains disabled absent explicit authorization.
