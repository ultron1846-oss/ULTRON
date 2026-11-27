"""Static safety contract for the owner preflight notebook scaffold."""
import json
import unittest
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[2] / "notebooks" / "ULTRON_OWNER_PREFLIGHT.ipynb"


class OwnerPreflightNotebookTests(unittest.TestCase):
    def _notebook(self):
        return json.loads(NOTEBOOK.read_text(encoding="utf-8"))

    def test_notebook_json_and_required_cells(self):
        notebook = self._notebook()
        self.assertEqual(notebook["nbformat"], 4)
        code = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        )
        for required in (
            "RuntimeConfig.from_json",
            "NeuroSparseConfig.foundation()",
            "count_parameters",
            "count_total_parameters",
            "training_authorized is False",
            "remote_execution_enabled is False",
        ):
            self.assertIn(required, code)

    def test_notebook_does_not_invoke_training_or_data_generation(self):
        code = "\n".join(
            "".join(cell.get("source", []))
            for cell in self._notebook()["cells"]
            if cell.get("cell_type") == "code"
        )
        forbidden = (
            "NeuroSparseModel(",
            "make_optimizer(",
            "run_training_steps(",
            "generate_examples(",
            "Level1TrainingDataset(",
            "build_level1_training_loader(",
            "save_checkpoint(",
            "load_checkpoint(",
        )
        for call in forbidden:
            with self.subTest(call=call):
                self.assertNotIn(call, code)

    def test_notebook_has_explicit_stop_point(self):
        markdown = "\n".join(
            "".join(cell.get("source", []))
            for cell in self._notebook()["cells"]
            if cell.get("cell_type") == "markdown"
        ).lower()
        self.assertIn("does not train", markdown)
        self.assertIn("no dataset has been loaded or generated", markdown)
        self.assertIn("full dataset preflight", markdown)
        self.assertIn("not** a full dataset preflight", markdown)


if __name__ == "__main__":
    unittest.main()
