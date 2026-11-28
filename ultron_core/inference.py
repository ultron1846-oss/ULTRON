"""Checkpoint-backed, tool-independent inference for ULTRON."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import hmac
import json
from pathlib import Path
from typing import Any

import torch
from torch import nn

from .checkpoint import (
    _backup,
    _manifest,
    _metadata_path,
    _normalize_saved_config,
    _valid_pair,
    load_checkpoint,
)
from .compress import load_compressed_model_artifact
from .config import NeuroSparseConfig
from .math_tokenizer import MathTokenizer, TokenLimitExceeded
from .model import NeuroSparseModel


def _verified_checkpoint_source(path: str | Path) -> Path:
    target = Path(path)
    if _valid_pair(target, _manifest(target)):
        return target
    backup = _backup(target)
    if _valid_pair(backup, _backup(_manifest(target))):
        return backup
    if not target.is_file() and not backup.is_file():
        raise FileNotFoundError(f"checkpoint and verified backup are missing: {target}")
    raise ValueError("checkpoint and backup integrity verification failed")


def _read_checkpoint_config(path: str | Path) -> tuple[NeuroSparseConfig, Path]:
    target = Path(path)
    source = _verified_checkpoint_source(target)

    # Current checkpoints include a JSON sidecar bound to the checkpoint's
    # SHA-256. Reading that small file avoids deserializing a 60M+ tensor payload
    # merely to discover the model config before load_checkpoint restores it.
    metadata_path = (
        _backup(_metadata_path(target))
        if source == _backup(target)
        else _metadata_path(target)
    )
    manifest_path = _backup(_manifest(target)) if source == _backup(target) else _manifest(target)
    saved_config = None
    saved_format_version = None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        manifest_fields = manifest_path.read_text(encoding="utf-8").split()
        digest = metadata.get("checkpoint_sha256") if isinstance(metadata, dict) else None
        if (
            isinstance(metadata, dict)
            and metadata.get("schema_version") == 1
            and isinstance(digest, str)
            and len(digest) == 64
            and all(character in "0123456789abcdef" for character in digest)
            and manifest_fields
            and hmac.compare_digest(digest, manifest_fields[0])
        ):
            saved_config = metadata.get("config")
            saved_format_version = metadata.get("format_version")
    except (OSError, UnicodeError, json.JSONDecodeError):
        # Legacy/partial metadata falls back to the integrity-verified payload.
        pass

    if saved_config is None:
        try:
            payload = torch.load(source, map_location="cpu", weights_only=True)
        except Exception as exc:
            raise ValueError("verified checkpoint payload is unreadable") from exc
        if not isinstance(payload, dict):
            raise ValueError("checkpoint payload must be a mapping")
        saved_format_version = payload.get("format_version")
        saved_config = payload.get("config")

    if (
        isinstance(saved_format_version, bool)
        or not isinstance(saved_format_version, int)
        or saved_format_version not in (2, 3, 4, 5)
    ):
        raise ValueError("unsupported checkpoint format")
    if not isinstance(saved_config, dict):
        raise ValueError("checkpoint config is malformed")
    try:
        normalized = _normalize_saved_config(saved_config)
        config = NeuroSparseConfig(**normalized)
    except (TypeError, ValueError) as exc:
        raise ValueError("checkpoint model configuration is invalid") from exc
    return config, source


def _validate_tokenizer(tokenizer: Any, config: NeuroSparseConfig) -> None:
    if not callable(getattr(tokenizer, "encode", None)) or not callable(
        getattr(tokenizer, "decode", None)
    ):
        raise TypeError("tokenizer must provide encode() and decode()")
    vocabulary = getattr(tokenizer, "vocabulary", None)
    token_id = getattr(vocabulary, "token_id", None)
    if not callable(token_id):
        raise TypeError("tokenizer.vocabulary must provide token_id()")
    for special in ("<PAD>", "<BOS>", "<EOS>"):
        value = token_id(special)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("tokenizer special-token IDs must be integers")
    compatibility = getattr(tokenizer, "assert_compatible_config", None)
    if not callable(compatibility):
        raise TypeError("tokenizer must provide assert_compatible_config()")
    compatibility(config)


class ULTRONInferenceEngine:
    """Greedy autoregressive inference with deterministic, per-call cleanup.

    The engine never exposes command tools and never updates model parameters.
    It temporarily switches the model to evaluation mode and restores its
    previous mode after each request.
    """

    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any | None = None,
        *,
        load_metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if not isinstance(model, nn.Module):
            raise TypeError("model must be a torch.nn.Module")
        self._model: nn.Module | None = model
        self.tokenizer = tokenizer or MathTokenizer()
        config = getattr(model, "config", None)
        if not isinstance(config, NeuroSparseConfig):
            raise TypeError("model.config must be a NeuroSparseConfig")
        _validate_tokenizer(self.tokenizer, config)
        try:
            next(model.parameters())
        except StopIteration as exc:
            raise ValueError("model must have parameters to determine its device") from exc
        self._config = config
        self._bos_id = self.tokenizer.vocabulary.token_id("<BOS>")
        self._eos_id = self.tokenizer.vocabulary.token_id("<EOS>")
        self.load_metadata = dict(load_metadata or {})
        self._closed = False

    @property
    def model(self) -> nn.Module:
        if self._closed or self._model is None:
            raise RuntimeError("inference engine is closed")
        return self._model

    @property
    def closed(self) -> bool:
        return self._closed

    def generate(self, prompt: str, *, max_new_tokens: int = 64) -> dict:
        """Return a bounded greedy completion and explicit execution metadata."""
        if self._closed or self._model is None:
            raise RuntimeError("inference engine is closed")
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        if (
            isinstance(max_new_tokens, bool)
            or not isinstance(max_new_tokens, int)
            or not 1 <= max_new_tokens <= 256
        ):
            raise ValueError("max_new_tokens must be an integer in [1, 256]")

        try:
            encoded = self.tokenizer.encode(
                prompt,
                add_bos=True,
                max_tokens=self._config.max_sequence_length - 1,
            )
        except TokenLimitExceeded as exc:
            raise ValueError(
                "prompt exceeds max_sequence_length and leaves no room for generation"
            ) from exc
        if not isinstance(encoded, Sequence) or isinstance(encoded, (str, bytes)) or not encoded:
            raise ValueError("tokenizer returned an empty or invalid token sequence")
        if any(
            isinstance(token, bool)
            or not isinstance(token, int)
            or token < 0
            or token >= len(self.tokenizer.vocabulary)
            for token in encoded
        ):
            raise ValueError("tokenizer returned a token ID outside its vocabulary")
        if encoded[0] != self._bos_id:
            raise ValueError("tokenizer did not place BOS at the start")

        available_context = self._config.max_sequence_length - len(encoded)
        if available_context < 1:
            raise ValueError("prompt leaves no room for inference generation")
        token_budget = min(max_new_tokens, available_context)
        finish_reason = (
            "max_new_tokens" if token_budget == max_new_tokens else "max_sequence_length"
        )
        sequence = list(encoded)
        generated: list[int] = []
        model = self._model
        try:
            parameter = next(model.parameters())
        except StopIteration as exc:
            raise ValueError("model has no parameters") from exc
        device = parameter.device
        was_training = model.training
        model.eval()
        reset_memory = getattr(model, "reset_memory", None)
        try:
            if callable(reset_memory):
                reset_memory()
            with torch.inference_mode():
                for _ in range(token_budget):
                    input_ids = torch.tensor([sequence], dtype=torch.long, device=device)
                    output = model(input_ids)
                    if not isinstance(output, Mapping) or "logits" not in output:
                        raise TypeError("model forward must return a mapping containing logits")
                    logits = output["logits"]
                    vocab_size = len(self.tokenizer.vocabulary)
                    if (
                        not isinstance(logits, torch.Tensor)
                        or logits.ndim != 3
                        or logits.shape[0] != 1
                        or logits.shape[1] != len(sequence)
                        or logits.shape[2] != vocab_size
                    ):
                        raise ValueError(
                            "model logits must have shape [1, input_sequence, tokenizer_vocabulary]"
                        )
                    next_logits = logits[0, -1]
                    if not bool(torch.isfinite(next_logits).all()):
                        raise ValueError("model emitted non-finite next-token logits")
                    next_token = int(torch.argmax(next_logits).item())
                    if next_token == self._eos_id:
                        finish_reason = "eos"
                        break
                    generated.append(next_token)
                    sequence.append(next_token)
        finally:
            try:
                if callable(reset_memory):
                    reset_memory()
            finally:
                model.train(was_training)

        text = self.tokenizer.decode(generated)
        if not isinstance(text, str):
            raise TypeError("tokenizer.decode() must return a string")
        return {
            "schema_version": 1,
            "text": text,
            "token_ids": generated,
            "finish_reason": finish_reason,
            "prompt_token_count": len(encoded) - 1,
            "generated_token_count": len(generated),
            "model_invoked": True,
            "tools_available_to_model": False,
            "external_ai_apis_used": False,
            "training_performed": False,
            "trained_model_capability_verified": False,
        }

    def close(self) -> None:
        """Clear mutable runtime memory and release the engine's model reference."""
        if self._closed:
            return
        model = self._model
        self._closed = True
        try:
            reset_memory = getattr(model, "reset_memory", None)
            if callable(reset_memory):
                reset_memory()
        finally:
            self._model = None

    def __enter__(self) -> "ULTRONInferenceEngine":
        if self._closed:
            raise RuntimeError("inference engine is closed")
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


def load_inference_engine(
    checkpoint_path: str | Path,
    *,
    tokenizer: Any | None = None,
    device: str | torch.device = "cpu",
) -> ULTRONInferenceEngine:
    """Load a verified model checkpoint without restoring RNG or training state."""
    active_tokenizer = tokenizer or MathTokenizer()
    config, _source = _read_checkpoint_config(checkpoint_path)
    _validate_tokenizer(active_tokenizer, config)
    try:
        target_device = torch.device(device)
    except (TypeError, RuntimeError, ValueError) as exc:
        raise ValueError("device must be a valid torch device") from exc

    # Initialization must not perturb the caller's global CPU RNG stream.
    with torch.random.fork_rng(devices=[]):
        model = NeuroSparseModel(config)
    loaded = load_checkpoint(
        checkpoint_path,
        model,
        map_location="cpu",
        restore_rng=False,
    )
    model.to(target_device)
    model.eval()
    metadata = {
        "checkpoint_sha256": loaded["sha256"],
        "checkpoint_format_version": loaded["format_version"],
        "checkpoint_step": loaded["step"],
        "checkpoint_source": loaded["source_path"],
        "weights_loaded": True,
        "optimizer_loaded": False,
        "rng_restored": False,
        "training_performed": False,
        "trained_model_capability_verified": False,
    }
    return ULTRONInferenceEngine(model, active_tokenizer, load_metadata=metadata)


def load_compressed_inference_engine(
    artifact_path: str | Path,
    parent_checkpoint_path: str | Path,
    *,
    parent_checkpoint_id: str,
    tokenizer: Any | None = None,
    device: str | torch.device = "cpu",
) -> ULTRONInferenceEngine:
    """Load a compressed artifact by rebuilding it from its verified parent model."""
    if not isinstance(parent_checkpoint_id, str) or not parent_checkpoint_id.strip():
        raise ValueError("parent_checkpoint_id must be a non-empty stable identifier")
    try:
        target_device = torch.device(device)
    except (TypeError, RuntimeError, ValueError) as exc:
        raise ValueError("device must be a valid torch device") from exc
    parent_engine = load_inference_engine(
        parent_checkpoint_path,
        tokenizer=tokenizer,
        device="cpu",
    )
    parent_model = parent_engine.model
    parent_metadata = dict(parent_engine.load_metadata)
    active_tokenizer = parent_engine.tokenizer
    try:
        compressed_model, compression_report = load_compressed_model_artifact(
            artifact_path,
            parent_model,
            parent_checkpoint_id=parent_checkpoint_id,
        )
    finally:
        parent_engine.close()
    compressed_model.to(target_device)
    compressed_model.eval()
    metadata = {
        "checkpoint": parent_metadata,
        "compressed_artifact_loaded": True,
        "parent_checkpoint_id": parent_checkpoint_id,
        "compression": compression_report,
        "training_performed": False,
        "trained_model_capability_verified": False,
    }
    return ULTRONInferenceEngine(
        compressed_model,
        active_tokenizer,
        load_metadata=metadata,
    )
