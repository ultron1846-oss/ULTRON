import unittest
from ultron_core.stage_b_contract import STAGE_B_TOPICS,validate_stage_b_manifest

def fixture():
 return {"schema_version":1,"topics":[{"topic":t,"generator_id":t+"-gen-v1","verifier_id":t+"-verify-v1","benchmark_id":t+"-heldout-v1","benchmark_sha256":"a"*64,"split_sha256":"b"*64,"held_out_examples":200,"generator_independently_validated":True,"verifier_independently_tested":True,"baseline_model":"Fable 5.2","baseline_results_sha256":"c"*64} for t in STAGE_B_TOPICS]}

class StageBContractTests(unittest.TestCase):
 def test_complete_manifest_ready_without_execution(self):
  r=validate_stage_b_manifest(fixture()); self.assertTrue(r["ready"]); self.assertEqual(r["provided_topic_count"],6)
  self.assertFalse(r["data_generated"]); self.assertFalse(r["model_invoked"]); self.assertFalse(r["training_performed"])
 def test_missing_and_duplicate_topics_block(self):
  m=fixture(); m["topics"].pop(); self.assertFalse(validate_stage_b_manifest(m)["ready"])
  m=fixture(); m["topics"].append(dict(m["topics"][0])); self.assertTrue(any("duplicate topic" in x for x in validate_stage_b_manifest(m)["blockers"]))
 def test_hash_sample_and_validation_flags_block(self):
  m=fixture(); m["topics"][0]["benchmark_sha256"]="bad"; m["topics"][0]["held_out_examples"]=199
  m["topics"][0]["verifier_independently_tested"]=False
  row=validate_stage_b_manifest(m)["per_topic"]["geometry"]; self.assertFalse(row["ready"])
  self.assertIn("benchmark_sha256 must be a lowercase SHA-256",row["blockers"])
  self.assertIn("held_out_examples must be at least 200",row["blockers"])
 def test_schema_and_type_validation(self):
  with self.assertRaises(TypeError): validate_stage_b_manifest([])
  with self.assertRaisesRegex(ValueError,"schema_version"): validate_stage_b_manifest({"schema_version":2,"topics":[]})

if __name__=="__main__": unittest.main()
