"""Static safety contract for the owner preflight notebook scaffold."""
import json
import unittest
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[2] / "notebooks" / "ULTRON_OWNER_PREFLIGHT.ipynb"


class OwnerPreflightNotebookTests(unittest.TestCase):
    def notebook(self):
        return json.loads(NOTEBOOK.read_text(encoding="utf-8"))

    def test_notebook_json_and_required_cells(self):
        nb = self.notebook()
        self.assertEqual(nb["nbformat"], 4)
        code = "\n".join(
            "".join(cell.get("source", []))
            for cell in nb["cells"]
            if cell.get("cell_type") == "code"
        )
        for item in (
            "RuntimeConfig.from_json",
            "NeuroSparseConfig.foundation()",
            "count_parameters",
            "count_total_parameters",
            "training_authorized is False",
            "remote_execution_enabled is False",
            "prepare_dataset_split_manifest",
            "validate_dataset_split_manifest",
            "build_verified_split_loader",
            "initial_data_state",
        ):
            with self.subTest(item=item):
                self.assertIn(item, code)

    def test_notebook_does_not_invoke_training_or_corpus_generation(self):
        code = "\n".join(
            "".join(cell.get("source", []))
            for cell in self.notebook()["cells"]
            if cell.get("cell_type") == "code"
        )
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
        ):
            with self.subTest(call=call):
                self.assertNotIn(call, code)

    def test_notebook_constructs_loaders_without_consuming_batches(self):
        code = "\n".join(
            "".join(cell.get("source", []))
            for cell in self.notebook()["cells"]
            if cell.get("cell_type") == "code"
        )
        for item in (
            'split_name="train"',
            'split_name="validation"',
            'split_name="test"',
            "train_loader.num_workers",
            "train_loader.drop_last",
            "train_sampler.dataset_manifest_sha256",
        ):
            with self.subTest(item=item):
                self.assertIn(item, code)

    def test_notebook_has_explicit_stop_point(self):
        markdown = "\n".join(
            "".join(cell.get("source", []))
            for cell in self.notebook()["cells"]
            if cell.get("cell_type") == "markdown"
        ).lower()
        for phrase in (
            "does not train",
            "generates **no dataset examples**",
            "writes split-id metadata only",
            "constructs read-only split datasets/dataloaders",
            "does not iterate batches",
            "allocate model weights",
            "create an optimizer",
            "perform optimizer steps",
            "dispatch remote jobs",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, markdown)


if __name__ == "__main__":
    unittest.main()
