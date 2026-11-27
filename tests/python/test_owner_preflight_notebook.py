"""Static safety contract for the owner preflight notebook scaffold."""
import json
import re
import unittest
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[2] / "notebooks" / "ULTRON_OWNER_PREFLIGHT.ipynb"

class OwnerPreflightNotebookTests(unittest.TestCase):
    def _notebook(self):
        return json.loads(NOTEBOOK.read_text(encoding="utf-8"))

    def test_notebook_json_and_required_cells(self):
        notebook = self._notebook()
        self.assertEqual(notebook["nbformat"], 4)
        code = "\\n".join("".join(cell.get("source", [])) for cell in notebook["cells"] if cell.get("cell_type") == "code")
        for required in ("RuntimeConfig.from_json", "NeuroSparseConfig.foundation()", "count_parameters", "count_total_parameters", "training_authorized is False", "remote_execution_enabled is False"):
            self.assertIn(required, code)

    def test_notebook_does_not_invoke_training_or_data_generation(self):
        code = "\\n".join("".join(cell.get("source", [])) for cell in self._notebook()["cells"] if cell.get("cell_type") == "code")
        forbidden = (r"NeuroSparseModel\\s*\\(", r"make_optimizer\\s*\\(", r"run_training_steps\\s*\\(", r"generate_examples\\s*\\(", r"Level1TrainingDataset\\s*\\(", r"build_level1_training_loader\\s*\\(", r"save_checkpoint\\s*\\(", r"load_checkpoint\\s*\\(")
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, code))

    def test_notebook_has_explicit_stop_point(self):
        markdown = "\\n".join("".join(cell.get("source", [])) for cell in self._notebook()["cells"] if cell.get("cell_type") == "markdown")
        self.assertIn("does not train", markdown.lower())
        self.assertIn("no dataset has been loaded or generated", markdown.lower())
        self.assertIn("not a full dataset preflight", markdown.lower())

if __name__ == "__main__":
    unittest.main()
