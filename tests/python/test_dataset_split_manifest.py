"""Manifest-bound split tests use temporary synthetic fixtures only."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from ultron_core.dataset_split_manifest import prepare_dataset_split_manifest,validate_dataset_split_manifest

_VERSION="0.5.0"
def fixture(path,count=90,duplicate=True):
    seed=31; rows=[]
    for index in range(count+(1 if duplicate else 0)):
        a=1 if duplicate and index==count else index+1; b=2
        prompt=f"{a} + {b}"; answer=str(a+b); params={"a":a,"operator":"+","b":b}
        identity={"generator_version":_VERSION,"seed":seed,"index":index,"topic":"arithmetic","input_text":prompt,"target_text":answer,"generation_parameters":params}
        eid=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        rows.append({"example_id":eid,"generator_version":_VERSION,"topic":"arithmetic","difficulty":1 if max(abs(a),abs(b))<10 else 2,
          "input_text":prompt,"target_text":answer,"exact_answer":answer,"seed":seed,"index":index,"generation_parameters":params,
          "validation_status":"semantically_checked","provenance":"temporary unit-test fixture"})
    content="".join(json.dumps(row,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n" for row in rows).encode()
    path.write_bytes(content)
    manifest={"schema_version":1,"generator_version":_VERSION,"seed":seed,"topics":["arithmetic"],"example_count":len(rows),
              "topic_counts":{"arithmetic":len(rows)},"sha256":hashlib.sha256(content).hexdigest()}
    path.with_suffix(path.suffix+".manifest.json").write_text(json.dumps(manifest,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n")

class DatasetSplitManifestTests(unittest.TestCase):
    def test_prepare_validate_and_duplicate_prompt_collapse(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); dataset=root/"fixture.jsonl"; split=root/"splits.json"; fixture(dataset)
            result=prepare_dataset_split_manifest(dataset,split,split_seed=4,validation_fraction=.1,test_fraction=.1)
            self.assertEqual(result.dataset_example_count,91); self.assertEqual(result.selected_example_count,90)
            self.assertEqual(sum(result.split_counts.values()),90)
            self.assertTrue(all(result.split_counts[n]>0 for n in ("train","validation","test")))
            self.assertEqual(validate_dataset_split_manifest(dataset,split),result)

    def test_tampered_split_digest_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); dataset=root/"d.jsonl"; split=root/"s.json"; fixture(dataset)
            prepare_dataset_split_manifest(dataset,split,split_seed=4)
            data=json.loads(split.read_text()); data["split_ids"]["train"].pop(); split.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"): validate_dataset_split_manifest(dataset,split)

    def test_dataset_mutation_invalidates_binding(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); dataset=root/"d.jsonl"; split=root/"s.json"; fixture(dataset,duplicate=False)
            prepare_dataset_split_manifest(dataset,split,split_seed=4)
            dataset.write_bytes(dataset.read_bytes()+b" ")
            with self.assertRaises(ValueError): validate_dataset_split_manifest(dataset,split)

    def test_output_cannot_overwrite_dataset_or_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            dataset=Path(d)/"d.jsonl"; fixture(dataset,duplicate=False)
            with self.assertRaisesRegex(ValueError,"must not overwrite"): prepare_dataset_split_manifest(dataset,dataset)
            sidecar=dataset.with_suffix(dataset.suffix+".manifest.json")
            with self.assertRaisesRegex(ValueError,"must not overwrite"): prepare_dataset_split_manifest(dataset,sidecar)

if __name__=="__main__": unittest.main()
