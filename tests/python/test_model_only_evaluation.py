import unittest

import torch
from torch import nn

from ultron_core.data_generation import generate_examples
from ultron_core.config import NeuroSparseConfig
from ultron_core.math_tokenizer import MathTokenizer
from ultron_core.model import NeuroSparseModel
from ultron_core.model_only_evaluation import (
    evaluate_prediction_modes,
    run_model_only_evaluation,
)


class _Vocabulary:
    def __len__(self):
        return 5

    def token_id(self, token):
        return {"<PAD>": 0, "<BOS>": 1, "<EOS>": 2, "answer": 3, "prompt": 4}[token]


class _Tokenizer:
    vocabulary = _Vocabulary()

    def __init__(self, answer):
        self.answer = answer

    def assert_compatible_config(self, config):
        if config.tokenizer_version != 1 or config.vocab_size != len(self.vocabulary):
            raise ValueError("model config vocabulary size does not match tokenizer")

    def encode(self, text, *, add_bos=False):
        return [1, 4] if add_bos else [4]

    def decode(self, token_ids):
        return self.answer if token_ids == [3] else ""


class _TinyModel(nn.Module):
    """Mock autoregressive model: answer token then EOS; no tools interface."""

    def __init__(self):
        super().__init__()
        self.anchor = nn.Parameter(torch.zeros(()))
        self.config = type("Config", (), {
            "max_sequence_length": 16, "vocab_size": 5, "tokenizer_version": 1
        })()
        self.reset_count = 0
        self.forward_calls = 0

    def reset_memory(self):
        self.reset_count += 1

    def forward(self, input_ids):
        self.forward_calls += 1
        self.assert_inference = not self.training
        logits = torch.full((1, input_ids.shape[1], 6), -100.0, device=input_ids.device)
        next_id = 3 if input_ids.shape[1] == 2 else 2
        logits[0, -1, next_id] = 100.0
        logits[0, -1, 5] = 200.0  # out-of-vocabulary logit must be masked
        return {"logits": logits}


class ModelOnlyEvaluationTests(unittest.TestCase):
    def test_model_only_runner_calls_model_without_tool_context(self):
        example = generate_examples(101, 1, topics=("arithmetic",))[0]
        model = _TinyModel()
        tokenizer = _Tokenizer(example.exact_answer)
        model.train()

        report = run_model_only_evaluation(model, tokenizer, [example])

        self.assertEqual(report["evaluation_mode"], "model_only")
        self.assertTrue(report["model_invoked"])
        self.assertFalse(report["tools_available_to_model"])
        self.assertEqual(report["tool_calls"], 0)
        self.assertEqual(report["correct"], 1)
        self.assertEqual(model.forward_calls, 2)
        self.assertEqual(model.reset_count, 2)
        self.assertTrue(model.training, "runner should restore the model's original mode")
        self.assertTrue(model.assert_inference)


    def test_model_only_inference_rejects_tokenizer_config_mismatch_before_forward(self):
        example = generate_examples(104, 1, topics=("arithmetic",))[0]
        model = _TinyModel()
        model.config.vocab_size = 6
        tokenizer = _Tokenizer(example.exact_answer)
        with self.assertRaisesRegex(ValueError, "vocabulary size does not match tokenizer"):
            run_model_only_evaluation(model, tokenizer, [example])
        self.assertEqual(model.forward_calls, 0)


    def test_real_small_model_tokenizer_inference_pipeline_is_read_only(self):
        tokenizer = MathTokenizer()
        config = NeuroSparseConfig(
            vocab_size=len(tokenizer.vocabulary),
            hidden_size=32,
            num_layers=1,
            num_experts=4,
            top_k=2,
            expert_multiplier=2,
            max_refinements=1,
            fast_memory_slots=4,
            num_attention_heads=4,
            max_sequence_length=64,
            dropout=0.0,
        )
        torch.manual_seed(303)
        model = NeuroSparseModel(config).eval()
        before = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
        example = generate_examples(105, 1, topics=("arithmetic",))[0]

        report = run_model_only_evaluation(
            model, tokenizer, [example], max_new_tokens=3
        )

        self.assertTrue(report["model_invoked"])
        self.assertFalse(report["tools_available_to_model"])
        self.assertEqual(report["tool_calls"], 0)
        self.assertEqual(set(report["predictions"]), {example.example_id})
        self.assertFalse(report["training_performed"])
        for name, tensor in model.state_dict().items():
            self.assertTrue(torch.equal(tensor, before[name]), name)

    def test_tool_assisted_and_model_only_metrics_are_separate(self):
        example = generate_examples(102, 1, topics=("arithmetic",))[0]
        model_only = {example.example_id: "incorrect"}
        assisted = {example.example_id: example.exact_answer}

        report = evaluate_prediction_modes([example], model_only, assisted)

        self.assertEqual(report["model_only"]["correct"], 0)
        self.assertEqual(report["tool_assisted"]["correct"], 1)
        self.assertEqual(
            report["metric_delta_tool_assisted_minus_model_only"]["exact_accuracy_all"],
            1.0,
        )
        self.assertTrue(report["predictions_are_caller_supplied"])
        self.assertFalse(report["model_invoked"])
        self.assertFalse(report["tools_invoked"])

    def test_rejects_unbounded_generation_request(self):
        example = generate_examples(103, 1, topics=("arithmetic",))[0]
        with self.assertRaisesRegex(ValueError, "max_new_tokens"):
            run_model_only_evaluation(
                _TinyModel(), _Tokenizer(example.exact_answer), [example], max_new_tokens=10000
            )


if __name__ == "__main__":
    unittest.main()
