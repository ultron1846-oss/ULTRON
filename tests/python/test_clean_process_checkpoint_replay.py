"""Clean-process checkpoint transfer with RNG and sampler-state replay.

Uses a small synthetic model and dataset; no optimizer exists and no training
or optimizer step is performed.
"""
import hashlib
import json
import os
import random
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


def small_config():
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


def model_fingerprint(model):
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(
            bytes(
                tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).tolist()
            )
        )
    return digest.hexdigest()


class CleanProcessCheckpointReplayTests(unittest.TestCase):
    def test_clean_process_restores_rng_weights_and_exact_sampler_tail(self):
        random.seed(8128)
        torch.manual_seed(2718)
        model = NeuroSparseModel(small_config()).eval()
        dataset = list(range(7))
        sampler = ResumableRandomSampler(
            dataset,
            seed=19,
            dataset_manifest_sha256=DATASET_HASH,
            next_index=3,
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
            "next_sample_index": 3,
            "dataset_manifest_sha256": DATASET_HASH,
            "dataset_size": len(dataset),
            "batch_size": 3,
            "seed": 19,
            "gradient_accumulation_steps": 1,
            "training_settings": settings,
            "sampler_state": sampler.state_dict(),
        }
        expected_fingerprint = model_fingerprint(model)
        expected_permutation = list(
            ResumableRandomSampler(
                dataset, seed=19, dataset_manifest_sha256=DATASET_HASH
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clean-process.pt"
            save_checkpoint(
                path,
                model,
                model.config,
                step=0,
                data_state=cursor,
                dataset_manifest_sha256=DATASET_HASH,
                training_settings=settings,
            )
            saved = torch.load(path, map_location="cpu", weights_only=True)
            isolated_python_rng = random.Random()
            isolated_python_rng.setstate(saved["rng"]["python"])
            expected_python_draw = isolated_python_rng.random()
            isolated_torch_rng = torch.Generator(device="cpu")
            isolated_torch_rng.set_state(saved["rng"]["torch_cpu"])
            expected_torch_draws = torch.rand(5, generator=isolated_torch_rng).tolist()

            script = r'''
import hashlib
import json
import random
import sys
import torch
from ultron_core.checkpoint import load_checkpoint
from ultron_core.config import NeuroSparseConfig
from ultron_core.model import NeuroSparseModel
from ultron_core.resumable_sampler import ResumableRandomSampler

path, expected_fingerprint, dataset_hash = sys.argv[1:]
random.seed(1)
torch.manual_seed(2)
config = NeuroSparseConfig(
    vocab_size=64, hidden_size=32, num_layers=1, num_experts=4,
    top_k=2, expert_multiplier=2, max_refinements=1,
    fast_memory_slots=4, num_attention_heads=4,
    max_sequence_length=8, dropout=0.0,
)
model = NeuroSparseModel(config).eval()
metadata = load_checkpoint(
    path,
    model,
    restore_rng=True,
    expected_dataset_manifest_sha256=dataset_hash,
)
assert metadata["rng_restored"] is True
assert metadata["dataset_hash_verified"] is True
sampler = ResumableRandomSampler(
    list(range(7)), seed=19, dataset_manifest_sha256=dataset_hash
)
sampler.load_state_dict(metadata["data_state"]["sampler_state"])
tail = list(iter(sampler))
digest = hashlib.sha256()
for name, tensor in sorted(model.state_dict().items()):
    digest.update(name.encode("utf-8"))
    digest.update(bytes(tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).tolist()))
assert digest.hexdigest() == expected_fingerprint
result = {
    "python_draw": random.random(),
    "torch_draws": torch.rand(5).tolist(),
    "sampler_tail": tail,
    "step": metadata["step"],
    "rng_restored": metadata["rng_restored"],
}
print(json.dumps(result, sort_keys=True))
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
            child = json.loads(result.stdout.strip().splitlines()[-1])

        self.assertEqual(child["python_draw"], expected_python_draw)
        self.assertEqual(child["torch_draws"], expected_torch_draws)
        self.assertEqual(child["sampler_tail"], expected_permutation[3:])
        self.assertEqual(child["step"], 0)
        self.assertTrue(child["rng_restored"])


if __name__ == "__main__":
    unittest.main()
