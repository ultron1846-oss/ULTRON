# Stage C — bounded multi-step trace verification

**Status:** a deterministic exact-rational trace verifier, not a general multi-step reasoning model or benchmark result.

The verifier in `ultron_core/stage_c_steps.py` accepts a sequence of named arithmetic steps. Each step's expression may reference only earlier, successfully verified values. It checks the claimed intermediate result and the final expression against an independently supplied exact answer.

The evaluator uses a restricted Python AST whitelist for integer/decimal literals, names, unary signs and the four rational arithmetic operators. It does not use `eval`, execute arbitrary code, call a model, or create data. It applies expression-length and AST-node limits.

This is a narrow benchmark component for arithmetic chains. It does not solve natural-language word problems, validate semantic decomposition, prove algebraic transformations outside the supported arithmetic, or establish competition-math ability. Stage C remains unpassed until frozen, held-out multi-step tasks and matched baseline results demonstrate improvement.
