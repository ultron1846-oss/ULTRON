import unittest
import hashlib
import json
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import Mock, patch
from tools.hf_seed_data.importer import (
    contains_program_or_tool_output, load_config, mathinstruct_license,
    normalize_row, split_for_question,
)

class HuggingFaceSeedDataTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()

    def test_requested_sources_and_counts(self):
        sources = {item["id"]: item for item in self.config["sources"]}
        self.assertEqual(sources["metamathqa"]["expected_rows"], 395000)
        self.assertEqual(sources["mathinstruct"]["expected_rows"], 262039)
        self.assertEqual(sources["metamathqa"]["repo_id"], "meta-math/MetaMathQA")
        self.assertEqual(sources["mathinstruct"]["repo_id"], "TIGER-Lab/MathInstruct")

    def test_allowlist_and_denials(self):
        self.assertEqual(mathinstruct_license("data/CoT/aqua_rat.json", self.config), "Apache-2.0")
        self.assertEqual(mathinstruct_license("data/CoT/gsm8k.json", self.config), "MIT")
        self.assertEqual(mathinstruct_license("data/CoT/math.json", self.config), "MIT")
        for source in ("data/CoT/gsm8k_rft.json", "data/CoT/camel_math.json",
                       "data/PoT/aqua_rat_filtered.json", "unknown.json"):
            self.assertIsNone(mathinstruct_license(source, self.config))

    def test_rejects_code_and_tool_targets(self):
        self.assertTrue(contains_program_or_tool_output("import sympy\nprint(answer)"))
        self.assertTrue(contains_program_or_tool_output("The tool returned 42."))
        self.assertFalse(contains_program_or_tool_output("First simplify the fraction, then compare."))

    def test_basic_arithmetic_source_is_registered_and_train_only(self):
        source = next(item for item in self.config["sources"] if item["id"] == "basic_arithmetic")
        self.assertEqual(source["repo_id"], "ChrisMcCormick/basic-arithmetic")
        self.assertEqual(source["split"], "train")
        self.assertEqual(source["dataset_license"], "MIT")
        self.assertEqual(source["expected_rows"], 10000)

    def test_basic_arithmetic_accepts_only_exact_verified_operations(self):
        cases = [
            ({"question": "What is 12 + 5?", "answer": 17.0, "op": "+", "a": 12, "b": 5}, "17"),
            ({"question": "What is 7 - 12?", "answer": -5.0, "op": "-", "a": 7, "b": 12}, "-5"),
            ({"question": "What is 6 * 7?", "answer": 42.0, "op": "*", "a": 6, "b": 7}, "42"),
            ({"question": "What is 12 / 3?", "answer": 4.0, "op": "/", "a": 12, "b": 3}, "4"),
        ]
        for row, expected in cases:
            record = normalize_row("basic_arithmetic", row, 0, "c" * 40, self.config)
            self.assertIsNotNone(record)
            self.assertEqual(record["reasoning_answer"], expected)
            self.assertEqual(record["target_kind"], "answer_only")
            self.assertEqual(record["dataset_repo"], "ChrisMcCormick/basic-arithmetic")
            self.assertEqual(record["source_license"], "MIT")

    def test_basic_arithmetic_rejects_bad_answers_and_unsafe_or_nonbasic_rows(self):
        invalid_rows = [
            {"question": "bad answer", "answer": 99, "op": "+", "a": 2, "b": 3},
            {"question": "fractional division", "answer": 1.5, "op": "/", "a": 3, "b": 2},
            {"question": "zero divisor", "answer": 0, "op": "/", "a": 3, "b": 0},
            {"question": "too large", "answer": 20001, "op": "+", "a": 20000, "b": 1},
            {"question": "unsupported operation", "answer": 2, "op": "^", "a": 1, "b": 2},
            {"question": "bool operand", "answer": 2, "op": "+", "a": True, "b": 1},
        ]
        for row in invalid_rows:
            self.assertIsNone(normalize_row("basic_arithmetic", row, 0, "d" * 40, self.config))

    def test_metamath_row_provenance(self):
        row = {"query":" Solve 2 + 2 ", "response":" Add the numbers. Answer: 4 ", "type":"GSM_Rephrased"}
        normalized = normalize_row("metamathqa", row, 0, "a" * 40, self.config)
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized["question"], "Solve 2 + 2")
        self.assertEqual(normalized["source_license"], "MIT")
        self.assertEqual(normalized["dataset_revision"], "a" * 40)

    def test_mathinstruct_rejects_unreviewed_source(self):
        row = {"instruction":"Q", "output":"A", "source":"data/CoT/camel_math.json"}
        self.assertIsNone(normalize_row("mathinstruct", row, 1, "b" * 40, self.config))

    def test_mocked_streaming_import_pins_revision_deduplicates_and_writes_manifest(self):
        from tools.hf_seed_data import importer

        revision = "a" * 40
        api = Mock()
        api.dataset_info.return_value.sha = revision
        rows_meta = [
            {"query": "What is 2 + 2?", "response": "Add 2 and 2 to get 4.", "type": "GSM_Rephrased"},
            {"query": " what is 2 + 2? ", "response": "Duplicate prompt.", "type": "GSM_Rephrased"},
            {"query": "Write code", "response": "import sympy\nprint(2 + 2)", "type": "GSM_Rephrased"},
        ]
        rows_math = [
            {"instruction": "What is 3 + 3?", "output": "Add 3 and 3 to get 6.", "source": "data/CoT/aqua_rat.json"}
        ]
        dataset_module = types.ModuleType("datasets")
        dataset_module.load_dataset = Mock(side_effect=[iter(rows_meta), iter(rows_math)])
        hub_module = types.ModuleType("huggingface_hub")
        hub_module.HfApi = Mock(return_value=api)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "curated"
            with patch.dict(sys.modules, {"datasets": dataset_module, "huggingface_hub": hub_module}):
                with patch.object(importer, "CONFIG_PATH", Path(__file__).resolve().parents[2] / "tools/hf_seed_data/config.json"):
                    manifest = importer.import_sources(output)
            self.assertEqual(manifest["unique_accepted_rows"], 2)
            self.assertEqual(manifest["rejected_counts"]["duplicate"], 1)
            self.assertEqual(manifest["rejected_counts"]["license_or_program_filter"], 1)
            self.assertFalse(manifest["data_is_training_authorized"])
            self.assertEqual(api.dataset_info.call_count, 2)
            for call in dataset_module.load_dataset.call_args_list:
                self.assertEqual(call.kwargs["revision"], revision)
                self.assertTrue(call.kwargs["streaming"])
            rows = []
            for name in ("train.jsonl", "validation.jsonl", "test.jsonl"):
                rows.extend(json.loads(line) for line in (output / name).read_text().splitlines())
                self.assertEqual(manifest["files_sha256"][name], hashlib.sha256((output / name).read_bytes()).hexdigest())
            self.assertEqual(len(rows), 2)
            self.assertTrue((output / "manifest.json").exists())

    def test_failed_stream_does_not_publish_partial_files(self):
        from tools.hf_seed_data import importer

        revision = "b" * 40
        api = Mock()
        api.dataset_info.return_value.sha = revision

        def broken_stream():
            yield {"query": "A question", "response": "A reasoned answer", "type": "GSM_Rephrased"}
            raise RuntimeError("simulated stream failure")

        dataset_module = types.ModuleType("datasets")
        dataset_module.load_dataset = Mock(return_value=broken_stream())
        hub_module = types.ModuleType("huggingface_hub")
        hub_module.HfApi = Mock(return_value=api)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "curated"
            with patch.dict(sys.modules, {"datasets": dataset_module, "huggingface_hub": hub_module}):
                with patch.object(importer, "CONFIG_PATH", Path(__file__).resolve().parents[2] / "tools/hf_seed_data/config.json"):
                    with self.assertRaisesRegex(RuntimeError, "simulated stream failure"):
                        importer.import_sources(output)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(temp).glob(".ultron-seed-stage-*")), [])

    def test_import_workflow_is_manual_and_disabled_by_default(self):
        workflow_path = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "import-hf-seed-data.yml"
        workflow = workflow_path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertIn("inputs.confirm_download == true", workflow)
        self.assertIn("vars.ULTRON_SEED_IMPORT_ENABLED == 'true'", workflow)

    def test_hash_split_is_deterministic_and_has_all_buckets(self):
        splits = {split_for_question(f"{i:02x}" + "0" * 62, self.config) for i in range(256)}
        self.assertEqual(splits, {"train", "validation", "test"})
        self.assertEqual(split_for_question("ab" * 32, self.config), split_for_question("ab" * 32, self.config))

if __name__ == "__main__":
    unittest.main()
