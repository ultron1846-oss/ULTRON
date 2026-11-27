"""Tests for read-only verified dataset adapters; fixtures are temporary only."""
import tempfile,unittest
from unittest.mock import patch
from pathlib import Path
from test_dataset_split_manifest import fixture
import ultron_core.dataset_split_manifest as split_module\nfrom ultron_core.dataset_split_manifest import (prepare_dataset_split_manifest, _read_dataset, load_verified_split_rows)
from ultron_core.verified_dataset import (VerifiedMathDataset, build_verified_split_loader, build_verified_split_loaders, collate_verified_math_batch)

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
 def test_split_validation_retains_only_prompt_and_id_metadata(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,contract=self.setup_data(Path(d))
   manifest,rows=_read_dataset(data)
   self.assertEqual(len(rows),manifest["example_count"])
   self.assertTrue(rows)
   self.assertEqual(len(rows[0]),2)
   self.assertIsInstance(rows[0],tuple)
   self.assertIsInstance(rows[0][0],str)
   self.assertIsInstance(rows[0][1],str)
 def test_split_preparation_streams_prompt_groups_without_retaining_row_list(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,_=self.setup_data(Path(d))
   original=split_module._read_dataset
   observed=[]
   def spy(*args,**kwargs):
    self.assertTrue(callable(kwargs.get("row_callback")))
    manifest,rows=original(*args,**kwargs)
    observed.append(len(rows))
    return manifest,rows
   with patch("ultron_core.dataset_split_manifest._read_dataset",side_effect=spy):
    prepare_dataset_split_manifest(data,split,split_seed=4)
   self.assertEqual(observed,[0,0])
 def test_dataset_change_between_verification_and_split_scan_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,_=self.setup_data(Path(d))
   original=split_module.verify_dataset
   def verify_then_mutate(path):
    manifest=original(path)
    with Path(path).open("ab") as stream:
     stream.write(b"\\n")
    return manifest
   with patch("ultron_core.dataset_split_manifest.verify_dataset",side_effect=verify_then_mutate):
    with self.assertRaisesRegex(ValueError,"changed while being read"):
     _read_dataset(data,row_callback=lambda row: None)
 def test_split_manifest_rewrite_after_validation_is_rejected(self):
  import json,hashlib
  with tempfile.TemporaryDirectory() as d:
   data,split,_=self.setup_data(Path(d))
   original=split_module.validate_dataset_split_manifest
   def validate_then_rewrite(*args,**kwargs):
    verified=original(*args,**kwargs)
    payload=json.loads(split.read_text())
    payload["split_ids"]["train"].pop()
    unsigned={key:value for key,value in payload.items() if key!="sha256"}
    payload["sha256"]=hashlib.sha256(split_module._canonical(unsigned)).hexdigest()
    split.write_text(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\\n")
    return verified
   with patch("ultron_core.dataset_split_manifest.validate_dataset_split_manifest",side_effect=validate_then_rewrite):
    with self.assertRaisesRegex(ValueError,"split manifest changed"):
     load_verified_split_rows(data,split,split_name="validation")
 def test_single_split_loader_retains_only_requested_full_records(self):
  import json
  with tempfile.TemporaryDirectory() as d:
   data,split,contract=self.setup_data(Path(d))
   verified,rows=load_verified_split_rows(data,split,split_name="validation")
   payload=json.loads(split.read_text())
   expected=set(payload["split_ids"]["validation"])
   self.assertEqual({row["example_id"] for row in rows},expected)
   self.assertEqual(verified.dataset_sha256,contract.dataset_sha256)
   self.assertTrue(all("exact_answer" in row and "generation_parameters" in row for row in rows))
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
 def test_single_loader_does_not_construct_other_splits(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,contract=self.setup_data(Path(d))
   with patch("ultron_core.verified_dataset.load_verified_split_rows_by_split",side_effect=AssertionError("combined loader path should not be used")):
    loader=build_verified_split_loader(data,split,split_name="validation",batch_size=2,seed=4,max_sequence_length=256)
   self.assertEqual(loader.split_name,"validation")
   self.assertEqual(loader.dataset_manifest_sha256,contract.dataset_sha256)
   self.assertEqual(type(loader.sampler).__name__,"SequentialSampler")
 def test_combined_build_constructs_all_loaders_with_one_shared_digest(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,contract=self.setup_data(Path(d))
   loaders=build_verified_split_loaders(data,split,batch_size=4,seed=0,max_sequence_length=256)
   self.assertEqual(set(loaders),{"train","validation","test"})
   self.assertEqual({loader.dataset_manifest_sha256 for loader in loaders.values()},{contract.dataset_sha256})
   self.assertEqual({loader.split_manifest_sha256 for loader in loaders.values()},{contract.split_manifest_sha256})
   self.assertEqual(type(loaders["validation"].sampler).__name__,"SequentialSampler")
   self.assertEqual(type(loaders["test"].sampler).__name__,"SequentialSampler")
   self.assertEqual(loaders["train"].sampler.state_dict()["next_index"],0)
 def test_oversize_sequence_rejected_without_truncation(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,_=self.setup_data(Path(d))
   ds=VerifiedMathDataset(data,split,split_name="train",max_sequence_length=3)
   with self.assertRaisesRegex(ValueError,"truncation is disabled"): ds[0]
if __name__=="__main__": unittest.main()
