"""Opt-in counters for expert dispatches in a ULTRON model.""" 
from __future__ import annotations

from threading import Lock
from typing import Any


class ExpertUsageCounter:
    """Count token rows processed by each expert using forward pre-hooks.

    Attach explicitly before an inference/analysis pass. Each expert receives
    the token rows routed to it, so counting its input rows measures dispatch
    assignments (not optimizer activity or expert quality). The counter never
    changes model parameters and can be removed with :meth:\`close\`.
    """

    def __init__(self, model: Any):
        blocks = getattr(model, "blocks", None)
        if blocks is None or not hasattr(blocks, "__iter__"):
            raise TypeError("model must expose iterable blocks")
        self._counts: list[list[int]] = []
        self._handles = []
        self._closed = False
        self._lock = Lock()

        expert_layers = []
        for layer_index, block in enumerate(blocks):
            experts = getattr(block, "experts", None)
            if experts is None or not hasattr(experts, "__iter__") or len(experts) == 0:
                raise TypeError(f"model block {layer_index} must expose a non-empty experts sequence")
            expert_layers.append(tuple(experts))
        if not expert_layers:
            raise ValueError("model must contain at least one expert layer")
        if any(not callable(getattr(expert, "register_forward_pre_hook", None))
               for experts in expert_layers for expert in experts):
            raise TypeError("every expert must be a torch module supporting forward pre-hooks")

        # Validate the complete layout before registering any hook. This avoids
        # leaving partial instrumentation behind if a later layer is malformed.
        for layer_index, experts in enumerate(expert_layers):
            self._counts.append([0 for _ in experts])
            for expert_index, expert in enumerate(experts):
                self._handles.append(
                    expert.register_forward_pre_hook(
                        self._make_hook(layer_index, expert_index)
                    )
                )

    def _make_hook(self, layer_index: int, expert_index: int):
        def count_input(_module, inputs):
            if not inputs:
                raise ValueError("expert forward did not receive an input tensor")
            tensor = inputs[0]
            if not hasattr(tensor, "shape") or len(tensor.shape) < 2:
                raise ValueError("expert input must have shape [tokens, hidden_size]")
            token_rows = int(tensor.shape[0])
            with self._lock:
                if not self._closed:
                    self._counts[layer_index][expert_index] += token_rows
        return count_input

    def snapshot(self) -> dict[str, Any]:
        """Return a detached, JSON-compatible count snapshot."""
        with self._lock:
            layers = {str(i): list(values) for i, values in enumerate(self._counts)}
        totals = [
            sum(layers[str(layer)][expert] for layer in layers)
            for expert in range(len(self._counts[0]))
        ]
        return {
            "layers": layers,
            "totals_by_expert": totals,
            "total_assignments": sum(totals),
            "layer_count": len(self._counts),
            "expert_count": len(self._counts[0]),
            "measurement": "expert_forward_input_token_rows",
        }

    def reset(self) -> None:
        """Reset collected counters without changing model state."""
        with self._lock:
            for layer in self._counts:
                for index in range(len(layer)):
                    layer[index] = 0

    def close(self) -> None:
        """Remove all hooks. Safe to call more than once."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            handles, self._handles = self._handles, []
        for handle in handles:
            handle.remove()

    def __enter__(self) -> "ExpertUsageCounter":
        if self._closed:
            raise RuntimeError("counter is closed")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
