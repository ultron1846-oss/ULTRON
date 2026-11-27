"""Static safety contract for the verified owner preflight notebook."""
import json
import unittest
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[2] / "notebooks" / "ULTRON_OWNER_PREFLIGHT.ipynb"


class OwnerPreflightNotebookTests(unittest.TestCase):
    def notebook(self):
        return json.loads(NOTEBOOK.read_text(encoding="utf-8"))

    def code(self):
        return "\n".join(
            "".join(cell.get("source", []))
            for cell in self.notebook()["cells"]
            if cell.get("cell_type") == "code"
        )

    def markdown(self):
        return "\n".join(
            "".join(cell.get("source", []))
            for cell in self.notebook()["cells"]
            if cell.get("cell_type") == "markdown"
        ).lower()

    def test_notebook_json_and_required_preflight_cells(self):
        notebook = self.notebook()
        self.assertEqual(notebook["nbformat"], 4)
        code = self.code()
        for item in (
            "RuntimeConfig.from_json",
            "NeuroSparseConfig.foundation()",
            "count_parameters",
            "count_total_parameters",
            "training_authorized is False",
            "remote_execution_enabled is False",
            "prepare_dataset_split_manifest",
            "build_verified_training_preflight",
            "preflight_report = verified_preflight.report",
            "sampler_seed = 0",
            "initial_data_state = verified_preflight.initial_data_state",
        ):
            with self.subTest(item=item):
                self.assertIn(item, code)

    def test_notebook_does_not_invoke_training_or_corpus_generation(self):
        code = self.code()
        for call in (
            "NeuroSparseModel(",
            "make_optimizer(",
            "run_training_steps(",
            "generate_examples(",
            "Level1TrainingDataset(",
            "build_level1_training_loader(",
            "save_checkpoint(",
            "load_checkpoint(",
            "next(iter(",
            "iter(train_loader)",
            "iter(validation_loader)",
            "iter(test_loader)",
            "optimizer.step(",
            ".backward(",
        ):
            with self.subTest(call=call):
                self.assertNotIn(call, code)

    def test_notebook_uses_preflight_loaders_and_records_seed_binding(self):
        code = self.code()
        for item in (
            "verified_preflight.train_loader",
            "verified_preflight.validation_loader",
            "verified_preflight.test_loader",
            '"sampler_seed": sampler_seed',
            "initial_data_state",
            "loader_contract",
        ):
            with self.subTest(item=item):
                self.assertIn(item, code)

    def test_notebook_has_explicit_non_authorizing_stop_point(self):
        markdown = self.markdown()
        for phrase in (
            "does not train",
            "generates **no dataset examples**",
            "writes split-id metadata only",
            "does not consume batches",
            "no model weights or optimizer are allocated",
            "no checkpoint is restored",
            "no optimizer step",
            "no remote job",
            "memory estimate",
            "must match",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, markdown)


if __name__ == "__main__":
    unittest.main()
