"""Tests for read-only verified dataset adapters; fixtures are temporary only."""
import tempfile,unittest
from pathlib import Path
from test_dataset_split_manifest import fixture
from ultron_core.dataset_split_manifest import prepare_dataset_split_manifest
from ultron_core.verified_dataset import VerifiedMathDataset,build_verified_split_loader,collate_verified_math_batch

class VerifiedDatasetTests(unittest.TestCase):
 def setup_data(self,root):
  data=root/"data.jsonl"; split=root/"splits.json"; fixture(data,90,True); contract=prepare_dataset_split_manifest(data,split,split_seed=4)
  return data,split,contract
 def test_dataset_only_reads_selected_split_and_binds_digest(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,contract=self.setup_data(Path(d))
   ds=VerifiedMathDataset(data,split,split_name="train",max_sequence_length=256)
   self.assertEqual(ds.dataset_manifest_sha256,contract.dataset_sha256)
   self.assertEqual(ds.split_manifest_sha256,contract.split_manifest_sha256)
   item=ds[0]; self.assertEqual(str(item["input_ids"].dtype),"torch.int64"); self.assertGreaterEqual(item["input_ids"].numel(),3)
   item["input_ids"][0]=0
   self.assertEqual(int(ds[0]["input_ids"][0]),1)
 def test_train_loader_has_resumable_sampler_without_consuming_batches(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,contract=self.setup_data(Path(d))
   loader=build_verified_split_loader(data,split,split_name="train",batch_size=4,seed=4,max_sequence_length=256)
   self.assertEqual(loader.num_workers,0); self.assertFalse(loader.drop_last)
   self.assertEqual(loader.dataset_manifest_sha256,contract.dataset_sha256)
   state=loader.sampler.state_dict(); self.assertEqual(state["next_index"],0); self.assertEqual(state["dataset_manifest_sha256"],contract.dataset_sha256)
 def test_eval_loader_is_sequential_and_cannot_shuffle(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,_=self.setup_data(Path(d))
   loader=build_verified_split_loader(data,split,split_name="validation",batch_size=3,seed=2,max_sequence_length=256)
   self.assertEqual(type(loader.sampler).__name__,"SequentialSampler")
   with self.assertRaisesRegex(ValueError,"must not shuffle"): build_verified_split_loader(data,split,split_name="test",batch_size=3,seed=2,shuffle=True)
 def test_collator_pads_and_masks(self):
  import torch
  batch=collate_verified_math_batch([{"input_ids":torch.tensor([1,4,2])},{"input_ids":torch.tensor([1,5,6,2])}])
  self.assertEqual(tuple(batch["input_ids"].shape),(2,4)); self.assertEqual(batch["attention_mask"][0].tolist(),[True,True,True,False])
 def test_oversize_sequence_rejected_without_truncation(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,_=self.setup_data(Path(d))
   ds=VerifiedMathDataset(data,split,split_name="train",max_sequence_length=3)
   with self.assertRaisesRegex(ValueError,"truncation is disabled"): ds[0]
if __name__=="__main__": unittest.main()
