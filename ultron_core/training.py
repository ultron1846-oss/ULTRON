import math
import time
from dataclasses import dataclass

from .config import NeuroSparseConfig, count_parameters
import torch
from torch.nn import functional as F


def causal_language_model_loss(logits: torch.Tensor, input_ids: torch.Tensor,
        load_balance: torch.Tensor | None = None, prediction_error: torch.Tensor | None = None,
        balance_weight: float = 0.01, prediction_weight: float = 0.01,
        ignore_index: int | None = 0) -> torch.Tensor:
    if logits.ndim != 3 or input_ids.ndim != 2:
        raise ValueError('expected logits [B,T,V] and input_ids [B,T]')
    if logits.shape[:2] != input_ids.shape:
        raise ValueError('logits/input_ids sequence dimensions must match')
    if input_ids.shape[0] == 0 or input_ids.shape[1] < 2:
        raise ValueError('batch must be non-empty and sequence length must be at least 2')
    for name, weight in (("balance_weight", balance_weight), ("prediction_weight", prediction_weight)):
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight < 0:
            raise ValueError(f"{name} must be a finite non-negative number")
    if not logits.is_floating_point():
        raise TypeError("logits must use a floating-point dtype")
    if logits.shape[-1] <= 0:
        raise ValueError("logits vocabulary dimension must be non-empty")
    if input_ids.dtype not in (torch.int32, torch.int64):
        raise TypeError("input_ids must use int32 or int64 token IDs")
    if input_ids.device != logits.device:
        raise ValueError("logits and input_ids must be on the same device")
    if ignore_index is not None and (isinstance(ignore_index, bool) or not isinstance(ignore_index, int)):
        raise TypeError("ignore_index must be an integer or None")
    for name, auxiliary in (("load_balance", load_balance), ("prediction_error", prediction_error)):
        if auxiliary is not None:
            if not isinstance(auxiliary, torch.Tensor) or auxiliary.numel() != 1:
                raise ValueError(f"{name} must be a scalar tensor")
            if not auxiliary.is_floating_point() or auxiliary.device != logits.device:
                raise ValueError(f"{name} must be a floating-point scalar on the logits device")
    targets = input_ids[:, 1:].reshape(-1).long()
    flat_logits = logits[:, :-1].reshape(-1, logits.shape[-1])
    if ignore_index is not None:
        if not bool((targets != ignore_index).any()):
            raise ValueError('all next-token targets are padding; loss is undefined')
        loss = F.cross_entropy(flat_logits, targets, ignore_index=ignore_index)
    else:
        loss = F.cross_entropy(flat_logits, targets)
    if load_balance is not None:
        loss = loss + balance_weight * load_balance
    if prediction_error is not None:
        loss = loss + prediction_weight * prediction_error
    return loss


def make_optimizer(model: torch.nn.Module, learning_rate: float = 3e-4,
                   weight_decay: float = 0.01):
    if (isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float))
            or not math.isfinite(learning_rate) or learning_rate <= 0):
        raise ValueError('learning_rate must be a finite positive number')
    if (isinstance(weight_decay, bool) or not isinstance(weight_decay, (int, float))
            or not math.isfinite(weight_decay) or weight_decay < 0):
        raise ValueError('weight_decay must be a finite non-negative number')
    return torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)



@dataclass(frozen=True)
class TrainingSettings:
    """Bounded per-session settings; these do not authorize training."""
    max_steps: int = 1
    gradient_accumulation_steps: int = 1
    gradient_clip_norm: float = 1.0
    max_seconds: int = 3600
    write_memory: bool = True

    def __post_init__(self):
        if isinstance(self.max_steps, bool) or not isinstance(self.max_steps, int) or not 1 <= self.max_steps <= 1000:
            raise ValueError("max_steps must be an integer in [1, 1000]")
        if (isinstance(self.gradient_accumulation_steps, bool)
                or not isinstance(self.gradient_accumulation_steps, int)
                or not 1 <= self.gradient_accumulation_steps <= 128):
            raise ValueError("gradient_accumulation_steps must be an integer in [1, 128]")
        if (isinstance(self.gradient_clip_norm, bool)
                or not isinstance(self.gradient_clip_norm, (int, float))
                or not math.isfinite(self.gradient_clip_norm) or self.gradient_clip_norm <= 0):
            raise ValueError("gradient_clip_norm must be finite and positive")
        if isinstance(self.max_seconds, bool) or not isinstance(self.max_seconds, int) or not 1 <= self.max_seconds <= 3600:
            raise ValueError("max_seconds must be an integer in [1, 3600]")
        if not isinstance(self.write_memory, bool):
            raise TypeError("write_memory must be boolean")


def run_training_steps(model, batches, optimizer, preflight_report, *, settings,
                       training_authorized=False, scheduler=None,
                       checkpoint_callback=None, cancellation_check=None):
    """Run bounded training only after explicit authorization."""
    if training_authorized is not True:
        raise PermissionError("explicit training authorization is required")
    if not isinstance(settings, TrainingSettings):
        raise TypeError("settings must be TrainingSettings")
    if not isinstance(preflight_report, dict) or preflight_report.get("validated") is not True:
        raise ValueError("a successful preflight report is required")
    count = preflight_report.get("parameter_count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 40_000_000:
        raise ValueError("preflight model must meet the 40M parameter minimum")
    config = getattr(model, "config", None)
    if isinstance(config, NeuroSparseConfig) and count_parameters(config) != count:
        raise ValueError("preflight parameter count does not match model config")
    reset_memory = getattr(model, "reset_memory", None)
    if not callable(reset_memory):
        raise ValueError("model must implement reset_memory() for example isolation")
    if scheduler is not None and not callable(getattr(scheduler, "step", None)):
        raise TypeError("scheduler must provide step()")
    if checkpoint_callback is not None and not callable(checkpoint_callback):
        raise TypeError("checkpoint_callback must be callable")
    if cancellation_check is not None and not callable(cancellation_check):
        raise TypeError("cancellation_check must be callable")

    model.train()
    optimizer.zero_grad(set_to_none=True)
    started = time.monotonic()
    steps, accumulated = 0, 0
    losses = []
    stop_reason = "dataset_exhausted"
    try:
        for batch in batches:
            if cancellation_check is not None and cancellation_check():
                stop_reason = "cancelled"
                break
            if time.monotonic() - started >= settings.max_seconds:
                stop_reason = "time_limit"
                break
            if not isinstance(batch, dict) or not isinstance(batch.get("input_ids"), torch.Tensor):
                raise TypeError("batch must contain tensor input_ids")
            ids, mask = batch["input_ids"], batch.get("attention_mask")
            if ids.ndim != 2 or ids.shape[0] == 0:
                raise ValueError("input_ids must be a non-empty [batch, sequence] tensor")
            if settings.write_memory and ids.shape[0] != 1:
                raise ValueError("memory-writing training requires batch_size=1 for isolation")
            reset_memory()
            output = model(ids, write_memory=settings.write_memory, attention_mask=mask)
            if not isinstance(output, dict) or not isinstance(output.get("logits"), torch.Tensor):
                raise ValueError("model output must contain logits")
            loss = causal_language_model_loss(ids=ids) if False else causal_language_model_loss(
                output["logits"], ids, load_balance=output.get("load_balance_loss"),
                prediction_error=output.get("prediction_error"))
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError("training loss is non-finite")
            (loss / settings.gradient_accumulation_steps).backward()
            accumulated += 1
            losses.append(float(loss.detach().cpu()))
            reset_memory()
            if accumulated == settings.gradient_accumulation_steps:
                parameters = [p for p in model.parameters() if p.grad is not None]
                if parameters:
                    norm = torch.nn.utils.clip_grad_norm_(parameters, settings.gradient_clip_norm)
                    if not bool(torch.isfinite(norm)):
                        raise FloatingPointError("gradient norm is non-finite")
                    if any(not bool(torch.isfinite(p.grad).all()) for p in parameters):
                        raise FloatingPointError("gradient contains non-finite values")
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()
                steps += 1
                optimizer.zero_grad(set_to_none=True)
                accumulated = 0
                if checkpoint_callback is not None:
                    mean_loss = sum(losses[-settings.gradient_accumulation_steps:]) / settings.gradient_accumulation_steps
                    checkpoint_callback(steps, {"mean_loss": mean_loss})
                if steps >= settings.max_steps:
                    stop_reason = "step_limit"
                    break
    finally:
        reset_memory()
        optimizer.zero_grad(set_to_none=True)
    return {"steps_completed": steps, "microbatches_seen": len(losses),
            "discarded_incomplete_microbatches": accumulated, "mean_loss": sum(losses) / len(losses) if losses else None,
            "stop_reason": stop_reason, "training_authorized": True}
