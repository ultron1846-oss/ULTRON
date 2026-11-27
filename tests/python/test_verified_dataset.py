"""Tests for read-only verified dataset adapters; fixtures are temporary only."""
import tempfile,unittest
from unittest.mock import patch
from pathlib import Path
from test_dataset_split_manifest import fixture
import ultron_core.dataset_split_manifest as split_module
from ultron_core.dataset_split_manifest import (prepare_dataset_split_manifest, _read_dataset, load_verified_split_rows)
from ultron_core.verified_dataset import (VerifiedMathDataset, IndexedVerifiedMathDataset, build_verified_split_loader, build_verified_split_loaders, close_verified_split_loaders, collate_verified_math_batch)

class VerifiedDatasetTests(unittest.TestCase):
 def setup_data(self,root,count=90):
  data=root/"data.jsonl"; split=root/"splits.json"; fixture(data,count,True); contract=prepare_dataset_split_manifest(data,split,split_seed=4)
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
    raw=Path(path).read_bytes()
    raw=raw.replace(b"temporary unit-test fixture",b"Temporary unit-test fixture",1)
    Path(path).write_bytes(raw)
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
    split.write_text(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\n")
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
 def test_indexed_iterator_streams_stable_verified_records(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,contract=self.setup_data(Path(d))
   loader=build_verified_split_loader(data,split,split_name="validation",batch_size=2,seed=4,max_sequence_length=256)
   store=loader.dataset._store
   streamed=list(store.iter_records("validation"))
   self.assertEqual(len(streamed),contract.split_counts["validation"])
   self.assertEqual([item[0] for item in streamed],sorted(item[0] for item in streamed))
   self.assertEqual(streamed[0],store.get_record("validation",0))
   loader.dataset.close()
 def test_indexed_random_access_is_repeatable_and_missing_index_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,_=self.setup_data(Path(d))
   loader=build_verified_split_loader(data,split,split_name="validation",batch_size=2,seed=4,max_sequence_length=256)
   store=loader.dataset._store
   expected=store.get_record("validation",0)
   self.assertEqual(store.get_record("validation",0),expected)
   store._connection.execute(
    "DELETE FROM ordered_records WHERE split_name=? AND seq=?",
    ("validation",0),
   )
   store._connection.commit()
   with self.assertRaisesRegex(ValueError,"index record is missing"):
    store.get_record("validation",0)
   loader.dataset.close()
 def test_indexed_iterator_rejects_corrupted_snapshot_record(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,_=self.setup_data(Path(d))
   loader=build_verified_split_loader(data,split,split_name="validation",batch_size=2,seed=4,max_sequence_length=256)
   store=loader.dataset._store
   record=store._connection.execute(
    "SELECT byte_offset,byte_length FROM ordered_records WHERE split_name=? AND seq=0",
    ("validation",),
   ).fetchone()
   store._snapshot_path.chmod(0o600)
   with store._snapshot_path.open("r+b") as stream:
    stream.seek(record[0])
    line=stream.read(record[1])
    stream.seek(record[0])
    stream.write(bytes([line[0]^1])+line[1:])
   with self.assertRaisesRegex(ValueError,"record integrity"):
    next(store.iter_records("validation"))
   loader.dataset.close()
 def test_indexed_loader_handles_large_synthetic_fixture_without_row_cache(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,contract=self.setup_data(Path(d),count=2000)
   loader=build_verified_split_loader(data,split,split_name="train",batch_size=8,seed=4,max_sequence_length=256)
   ds=loader.dataset
   self.assertEqual(len(ds),contract.split_counts["train"])
   self.assertFalse(hasattr(ds,"_records"))
   for index in (0,len(ds)//2,len(ds)-1):
    self.assertGreaterEqual(ds[index]["input_ids"].numel(),3)
   self.assertGreater(ds._store._snapshot_path.stat().st_size,0)
   ds.close()
 def test_single_loader_uses_lazy_disk_index_without_full_record_list(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,contract=self.setup_data(Path(d))
   loader=build_verified_split_loader(data,split,split_name="validation",batch_size=3,seed=4,max_sequence_length=256)
   ds=loader.dataset
   self.assertIsInstance(ds,IndexedVerifiedMathDataset)
   self.assertFalse(hasattr(ds,"_records"))
   self.assertEqual(len(ds),contract.split_counts["validation"])
   item=ds[0]
   self.assertEqual(str(item["input_ids"].dtype),"torch.int64")
   self.assertGreaterEqual(item["input_ids"].numel(),3)
   ds.close()
   with self.assertRaisesRegex(RuntimeError,"closed"):
    ds[0]
 def test_lazy_loader_uses_verified_snapshot_after_source_changes(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,_=self.setup_data(Path(d))
   loader=build_verified_split_loader(data,split,split_name="validation",batch_size=2,seed=4,max_sequence_length=256)
   ds=loader.dataset
   data.write_text("tampered source after verified snapshot\n")
   self.assertGreaterEqual(ds[0]["input_ids"].numel(),3)
   ds.close()
 def test_lazy_index_checks_record_digest_on_random_access(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,_=self.setup_data(Path(d))
   loader=build_verified_split_loader(data,split,split_name="validation",batch_size=2,seed=4,max_sequence_length=256)
   ds=loader.dataset
   store=ds._store
   record=store._connection.execute(
    "SELECT byte_offset,byte_length FROM ordered_records WHERE split_name=? AND seq=0",
    ("validation",),
   ).fetchone()
   store._snapshot_path.chmod(0o600)
   with store._snapshot_path.open("r+b") as stream:
    stream.seek(record[0])
    line=stream.read(record[1])
    stream.seek(record[0])
    stream.write(bytes([line[0]^1])+line[1:])
   with self.assertRaisesRegex(ValueError,"record integrity"):
    ds[0]
   ds.close()
 def test_combined_lazy_loaders_share_index_and_can_close(self):
  with tempfile.TemporaryDirectory() as d:
   data,split,contract=self.setup_data(Path(d))
   loaders=build_verified_split_loaders(data,split,batch_size=4,seed=4,max_sequence_length=256)
   stores={id(loader.dataset._store) for loader in loaders.values()}
   self.assertEqual(len(stores),1)
   self.assertTrue(all(isinstance(loader.dataset,IndexedVerifiedMathDataset) for loader in loaders.values()))
   self.assertEqual({loader.dataset.dataset_manifest_sha256 for loader in loaders.values()},{contract.dataset_sha256})
   close_verified_split_loaders(loaders)
   with self.assertRaisesRegex(RuntimeError,"closed"):
    loaders["train"].dataset[0]
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
