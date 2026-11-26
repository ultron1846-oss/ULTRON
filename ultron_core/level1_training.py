"""Lazy, verified Level 1 training source.

This module only creates examples when a caller explicitly constructs the
source with training_authorized=True. It never runs an optimizer or training.
The fixed held-out benchmark is not imported or consumed here.
"""
from __future__ import annotations

import random
import hashlib
import json

import torch
from torch.utils.data import DataLoader, Dataset, SequentialSampler

from .math_tokenizer import MathTokenizer, MathVocabulary
from .resumable_sampler import ResumableRandomSampler
from tools.level1_math.ultron_level1 import DIFFICULTIES, generate_problem, verify


TARGET_SOURCE = "ultron_level1.generate_problem"
TARGET_TYPE = "generator_worked_solution"
VERIFIER_ROLE = "independent_exact_validation_only"


def _serialize_generator_problem(problem: dict) -> str:
    """Serialize only allowlisted generator fields into the supervised sequence.

    Unknown fields (including any accidental tool_output/tool_answer field) are
    intentionally ignored and never become model targets.
    """
    if not isinstance(problem, dict):
        raise TypeError("generator problem must be a dictionary")
    prompt, answer = problem.get("prompt"), problem.get("answer")
    steps = problem.get("steps")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("generator problem prompt must be non-empty text")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("generator problem answer must be non-empty text")
    if (not isinstance(steps, list) or not steps
            or any(not isinstance(step, str) or not step.strip() for step in steps)):
        raise ValueError("generator problem must contain non-empty worked steps")
    return ("Question: " + prompt + "\\nWorking:\\n"
            + "\\n".join(steps) + "\\nAnswer: " + answer)


class Level1TrainingDataset(Dataset):
    """Create verified arithmetic/linear examples for a future training run.

    Construction requires the same explicit authorization boundary used by the
    training controller. This prevents accidental generation during preflight.
    """
    def __init__(self, *, count: int, seed: int, training_authorized: bool = False,
                 tokenizer: MathTokenizer | None = None):
        if training_authorized is not True:
            raise PermissionError("explicit training authorization is required to generate Level 1 training examples")
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 100_000:
            raise ValueError("count must be an integer in [1, 100000]")
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
            raise ValueError("seed must be an integer in [0, 2**63)")
        self.tokenizer = tokenizer or MathTokenizer(MathVocabulary.default())
        rng = random.Random(seed)
        examples = []
        for index in range(count):
            difficulty = DIFFICULTIES[index % len(DIFFICULTIES)]
            problem = generate_problem(rng, difficulty)
            if not verify(problem, problem["answer"]):
                raise RuntimeError(f"Level 1 verifier rejected generated example at index {index}")
            text = ("Question: " + problem["prompt"] + "\nWorking:\n"
                    + "\n".join(problem["steps"]) + "\nAnswer: "
                    + problem["answer"])
            token_ids = self.tokenizer.encode(text, add_bos=True, add_eos=True)
            if len(token_ids) < 3:
                raise RuntimeError("generated training sequence is too short")
            examples.append({"input_ids": torch.tensor(token_ids, dtype=torch.long),
                             "example_index": index,
                             "topic": problem["kind"],
                             "difficulty": problem["difficulty"],
                             "target_source": TARGET_SOURCE,
                             "target_type": TARGET_TYPE,
                             "verifier_role": VERIFIER_ROLE})
        self.examples = tuple(examples)
        self.seed = seed
        vocab_sha256 = hashlib.sha256(self.tokenizer.vocabulary.to_json().encode("utf-8")).hexdigest()
        manifest_payload = {
            "schema_version": 1,
            "generator": "ultron-level1",
            "generator_version": "0.1.0",
            "seed": seed,
            "count": count,
            "vocabulary_sha256": vocab_sha256,
            "target_contract": {
                "source": TARGET_SOURCE,
                "target_type": TARGET_TYPE,
                "verifier_role": VERIFIER_ROLE,
                "tool_outputs_in_targets": False,
            },
            "examples": [item["input_ids"].tolist() for item in self.examples],
        }
        canonical = json.dumps(manifest_payload, sort_keys=True, separators=(",", ":"))
        self.dataset_manifest_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, index):
        item = self.examples[index]
        return {"input_ids": item["input_ids"].clone()}


def collate_level1_batch(items: list[dict], *, pad_token_id: int = 0) -> dict[str, torch.Tensor]:
    """Right-pad generated sequences into the training controller's batch shape."""
    if not items:
        raise ValueError("cannot collate an empty batch")
    if isinstance(pad_token_id, bool) or not isinstance(pad_token_id, int) or pad_token_id != 0:
        raise ValueError("canonical ULTRON padding token ID must be 0")
    sequences = [item.get("input_ids") for item in items]
    if any(not isinstance(seq, torch.Tensor) or seq.ndim != 1 or seq.dtype != torch.long
           or seq.numel() < 2 for seq in sequences):
        raise ValueError("each item must contain a 1D int64 input_ids sequence")
    max_length = max(seq.numel() for seq in sequences)
    batch = torch.full((len(sequences), max_length), pad_token_id, dtype=torch.long)
    for row, seq in enumerate(sequences):
        batch[row, :seq.numel()] = seq
    return {"input_ids": batch, "attention_mask": batch.ne(pad_token_id)}


def build_level1_training_loader(*, count: int, seed: int, batch_size: int,
                                 training_authorized: bool = False,
                                 tokenizer: MathTokenizer | None = None,
                                 shuffle: bool = True) -> DataLoader:
    """Build the Level 1 training DataLoader at the authorized training boundary."""
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not 1 <= batch_size <= 1024:
        raise ValueError("batch_size must be an integer in [1, 1024]")
    if not isinstance(shuffle, bool):
        raise TypeError("shuffle must be boolean")
    dataset = Level1TrainingDataset(count=count, seed=seed,
                                   training_authorized=training_authorized,
                                   tokenizer=tokenizer)
    if shuffle:
        sampler = ResumableRandomSampler(
            dataset, seed=seed,
            dataset_manifest_sha256=dataset.dataset_manifest_sha256,
        )
    else:
        sampler = SequentialSampler(dataset)
    loader = DataLoader(dataset, batch_size=batch_size, sampler=sampler,
                        num_workers=0, drop_last=False,
                        collate_fn=collate_level1_batch)
    # Caller passes loader.sampler to run_training_steps and binds this hash
    # into validated preflight/checkpoint metadata.
    loader.dataset_manifest_sha256 = dataset.dataset_manifest_sha256
    return loader
