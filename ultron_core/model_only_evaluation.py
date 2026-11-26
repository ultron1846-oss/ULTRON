"""Tool-independent autoregressive evaluation for ULTRON's math model.

This runner performs inference only. It never imports or invokes command tools,
and it keeps any optional tool-assisted prediction set separate.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

import torch

from .data_generation import MathExample
from .evaluation import evaluate_predictions


def run_model_only_evaluation(
    model: torch.nn.Module,
    tokenizer,
    examples: Iterable[MathExample],
    *,
    max_new_tokens: int = 64,
) -> dict:
    """Run greedy next-token inference without command-tool access.

    The model receives only a tensor of token IDs. No tool registry, callable,
    command output, or tool-assisted answer is passed to its forward method.
    Predictions are scored by the existing independent exact-answer evaluator.
    """
    if not isinstance(model, torch.nn.Module):
        raise TypeError("model must be a torch.nn.Module")
    if not callable(getattr(tokenizer, "encode", None)) or not callable(
        getattr(tokenizer, "decode", None)
    ):
        raise TypeError("tokenizer must provide encode() and decode()")
    if (
        isinstance(max_new_tokens, bool)
        or not isinstance(max_new_tokens, int)
        or not 1 <= max_new_tokens <= 256
    ):
        raise ValueError("max_new_tokens must be an integer in [1, 256]")

    items = tuple(examples)
    if not items or any(not isinstance(item, MathExample) for item in items):
        raise ValueError("examples must contain at least one MathExample")
    if len({item.example_id for item in items}) != len(items):
        raise ValueError("evaluation examples contain duplicate IDs")

    vocabulary = getattr(tokenizer, "vocabulary", None)
    token_id = getattr(vocabulary, "token_id", None)
    if not callable(token_id):
        raise TypeError("tokenizer.vocabulary must provide token_id()")
    bos_id, eos_id = token_id("<BOS>"), token_id("<EOS>")
    vocabulary_size = len(vocabulary)

    try:
        parameter = next(model.parameters())
    except StopIteration as exc:
        raise ValueError("model must have at least one parameter to determine its device") from exc
    device = parameter.device
    configured_max = getattr(getattr(model, "config", None), "max_sequence_length", None)
    if configured_max is not None and (
        isinstance(configured_max, bool) or not isinstance(configured_max, int) or configured_max < 2
    ):
        raise ValueError("model config max_sequence_length is invalid")

    was_training = model.training
    predictions: dict[str, str | None] = {}
    model.eval()
    try:
        with torch.inference_mode():
            for item in items:
                reset_memory = getattr(model, "reset_memory", None)
                if callable(reset_memory):
                    reset_memory()
                try:
                    encoded = tokenizer.encode(item.input_text + "\n", add_bos=True)
                    if not isinstance(encoded, list) or not encoded:
                        raise ValueError("tokenizer returned an empty or invalid token sequence")
                    if any(
                        isinstance(value, bool) or not isinstance(value, int)
                        or value < 0 or value >= vocabulary_size
                        for value in encoded
                    ):
                        raise ValueError("tokenizer returned an ID outside its vocabulary")
                    if encoded[0] != bos_id:
                        raise ValueError("tokenizer did not place BOS at the start")
                    if configured_max is not None and len(encoded) >= configured_max:
                        raise ValueError("prompt leaves no room for model-only generation")

                    generated: list[int] = []
                    sequence = list(encoded)
                    for _ in range(max_new_tokens):
                        if configured_max is not None and len(sequence) >= configured_max:
                            break
                        input_ids = torch.tensor([sequence], dtype=torch.long, device=device)
                        output = model(input_ids)
                        if not isinstance(output, Mapping) or "logits" not in output:
                            raise TypeError("model forward must return a mapping containing logits")
                        logits = output["logits"]
                        if not isinstance(logits, torch.Tensor) or logits.ndim != 3:
                            raise ValueError("model logits must have shape [batch, sequence, vocabulary]")
                        if logits.shape[0] != 1 or logits.shape[1] != len(sequence):
                            raise ValueError("model logits do not match the input sequence")
                        if logits.shape[2] < vocabulary_size:
                            raise ValueError("model output vocabulary is smaller than tokenizer vocabulary")
                        # The default CPU smoke config has extra unused logits
                        # beyond the canonical math vocabulary. Mask them so the
                        # model cannot emit unsupported token IDs.
                        next_logits = logits[0, -1, :vocabulary_size]
                        if not bool(torch.isfinite(next_logits).all()):
                            raise ValueError("model emitted non-finite next-token logits")
                        next_token = int(torch.argmax(next_logits).item())
                        if not 0 <= next_token < vocabulary_size:
                            raise ValueError("model emitted a token outside its vocabulary")
                        if next_token == eos_id:
                            break
                        generated.append(next_token)
                        sequence.append(next_token)

                    prediction = tokenizer.decode(generated)
                    if not isinstance(prediction, str):
                        raise TypeError("tokenizer.decode() must return a string")
                    predictions[item.example_id] = prediction if prediction.strip() else None
                finally:
                    if callable(reset_memory):
                        reset_memory()
    finally:
        model.train(was_training)

    report = evaluate_predictions(items, predictions)
    report.update({
        "evaluation_mode": "model_only",
        "model_invoked": True,
        "tools_available_to_model": False,
        "tool_calls": 0,
        "predictions": predictions,
        "max_new_tokens": max_new_tokens,
        "training_performed": False,
        "data_generated": False,
    })
    return report


def evaluate_prediction_modes(
    examples: Iterable[MathExample],
    model_only_predictions: Mapping[str, str | None],
    tool_assisted_predictions: Mapping[str, str | None],
) -> dict:
    """Report model-only and optional tool-assisted scores as separate metrics.

    Both prediction maps are caller-supplied; this function does not call a
    model or any tools. Tool-assisted results must never be used as training
    targets or mislabeled as model-only performance.
    """
    items = tuple(examples)
    model_only = evaluate_predictions(items, model_only_predictions)
    tool_assisted = evaluate_predictions(items, tool_assisted_predictions)
    return {
        "schema_version": 1,
        "evaluation_kind": "separate_model_only_and_tool_assisted",
        "model_only": model_only,
        "tool_assisted": tool_assisted,
        "metric_delta_tool_assisted_minus_model_only": {
            "exact_accuracy_all": (
                tool_assisted["exact_accuracy_all"] - model_only["exact_accuracy_all"]
            ),
            "coverage": tool_assisted["coverage"] - model_only["coverage"],
            "valid_answer_rate": (
                tool_assisted["valid_answer_rate"] - model_only["valid_answer_rate"]
            ),
        },
        "predictions_are_caller_supplied": True,
        "model_invoked": False,
        "tools_invoked": False,
        "training_performed": False,
        "data_generated": False,
        "limitations": [
            "This report compares supplied prediction maps; it does not invoke a tool-assisted workflow.",
            "The tool-assisted score is descriptive and must not be presented as model-only capability.",
            "Neither score validates natural-language derivations or formal proofs.",
        ],
    }
