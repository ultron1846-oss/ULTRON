"""Cross-process checkpoint recovery test with no optimizer step."""
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import torch

from ultron_core.checkpoint import save_checkpoint
from ultron_core.config import NeuroSparseConfig
from ultron_core.model import NeuroSparseModel
from ultron_core.resumable_sampler import ResumableRandomSampler


DATASET_HASH = "a" * 64


def config():
    return NeuroSparseConfig(
        vocab_size=64,
        hidden_size=32,
        num_layers=1,
        num_experts=4,
        top_k=2,
        expert_multiplier=2,
        max_refinements=1,
        fast_memory_slots=4,
        num_attention_heads=4,
        max_sequence_length=8,
        dropout=0.0,
    )


def fingerprint(model):
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


class CleanProcessCheckpointResumeTests(unittest.TestCase):
    def test_checkpoint_restores_in_fresh_process_with_sampler_cursor(self):
        torch.manual_seed(911)
        model = NeuroSparseModel(config())
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2)
        dataset = list(range(5))
        sampler = ResumableRandomSampler(
            dataset, seed=19, dataset_manifest_sha256=DATASET_HASH, next_index=2
        )
        settings = {
            "precision": "fp32",
            "seed": 19,
            "gradient_accumulation_steps": 1,
            "deterministic": True,
        }
        cursor = {
            "epoch": 0,
            "next_batch_index": 1,
            "next_sample_index": 2,
            "dataset_manifest_sha256": DATASET_HASH,
            "dataset_size": 5,
            "batch_size": 2,
            "seed": 19,
            "gradient_accumulation_steps": 1,
            "training_settings": settings,
            "sampler_state": sampler.state_dict(),
        }
        expected_fingerprint = fingerprint(model)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clean-process.pt"
            save_checkpoint(
                path,
                model,
                config(),
                optimizer=optimizer,
                scheduler=scheduler,
                step=0,
                data_state=cursor,
                dataset_manifest_sha256=DATASET_HASH,
                training_settings=settings,
            )
            script = r'''
import hashlib
import sys
import torch
from ultron_core.checkpoint import load_checkpoint
from ultron_core.config import NeuroSparseConfig
from ultron_core.model import NeuroSparseModel
from ultron_core.resumable_sampler import ResumableRandomSampler

path, expected_fingerprint, dataset_hash = sys.argv[1:]
config = NeuroSparseConfig(
    vocab_size=64, hidden_size=32, num_layers=1, num_experts=4,
    top_k=2, expert_multiplier=2, max_refinements=1,
    fast_memory_slots=4, num_attention_heads=4,
    max_sequence_length=8, dropout=0.0,
)
model = NeuroSparseModel(config)
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2)
metadata = load_checkpoint(
    path, model, optimizer=optimizer, scheduler=scheduler,
    restore_rng=False, expected_dataset_manifest_sha256=dataset_hash,
)
sampler = ResumableRandomSampler(
    list(range(5)), seed=19, dataset_manifest_sha256=dataset_hash
)
sampler.load_state_dict(metadata["data_state"]["sampler_state"])
assert metadata["optimizer_restored"] is True
assert metadata["scheduler_restored"] is True
assert sampler.state_dict() == metadata["data_state"]["sampler_state"]
digest = hashlib.sha256()
for name, tensor in sorted(model.state_dict().items()):
    digest.update(name.encode("utf-8"))
    digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
assert digest.hexdigest() == expected_fingerprint
with torch.inference_mode():
    output = model(torch.tensor([[1, 2, 3]], dtype=torch.long))
assert torch.isfinite(output["logits"]).all()
assert not optimizer.state, "test must not perform an optimizer step"
print("clean-process-checkpoint-resume-ok")
'''
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    script,
                    str(path),
                    expected_fingerprint,
                    DATASET_HASH,
                ],
                cwd=Path(__file__).resolve().parents[2],
                env=os.environ.copy(),
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertIn("clean-process-checkpoint-resume-ok", result.stdout)
        self.assertFalse(optimizer.state, "parent test must not perform an optimizer step")


if __name__ == "__main__":
    unittest.main()
