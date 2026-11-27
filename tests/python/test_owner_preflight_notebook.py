"""Static safety contract for the owner preflight notebook scaffold."""
import json,unittest
from pathlib import Path
NOTEBOOK=Path(__file__).resolve().parents[2]/"notebooks"/"ULTRON_OWNER_PREFLIGHT.ipynb"
class OwnerPreflightNotebookTests(unittest.TestCase):
 def notebook(self): return json.loads(NOTEBOOK.read_text(encoding="utf-8"))
 def test_notebook_json_and_required_cells(self):
  nb=self.notebook(); self.assertEqual(nb["nbformat"],4)
  code="\n".join("".join(c.get("source",[])) for c in nb["cells"] if c.get("cell_type")=="code")
  for item in ("RuntimeConfig.from_json","NeuroSparseConfig.foundation()","count_parameters","count_total_parameters","training_authorized is False","remote_execution_enabled is False","prepare_dataset_split_manifest","validate_dataset_split_manifest"): self.assertIn(item,code)
 def test_notebook_does_not_invoke_training_or_corpus_generation(self):
  code="\n".join("".join(c.get("source",[])) for c in self.notebook()["cells"] if c.get("cell_type")=="code")
  for call in ("NeuroSparseModel(","make_optimizer(","run_training_steps(","generate_examples(","Level1TrainingDataset(","build_level1_training_loader(","save_checkpoint(","load_checkpoint("):
   with self.subTest(call=call): self.assertNotIn(call,code)
 def test_notebook_has_explicit_stop_point(self):
  md="\n".join("".join(c.get("source",[])) for c in self.notebook()["cells"] if c.get("cell_type")=="markdown").lower()
  self.assertIn("does not train",md); self.assertIn("generates **no dataset examples**",md); self.assertIn("split step writes metadata only",md); self.assertIn("no model weights have been allocated",md)
if __name__=="__main__": unittest.main()
