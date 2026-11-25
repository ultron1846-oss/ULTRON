import unittest
from ultron_core.stage_c_steps import verify_rational_steps

class StageCStepVerifierTests(unittest.TestCase):
 def test_valid_trace_with_backward_references(self):
  r=verify_rational_steps([{"name":"a","expression":"3+5","claimed_value":"8"},{"name":"b","expression":"a/2","claimed_value":"4"},{"name":"c","expression":"b*3","claimed_value":"12"}],"c-2","10")
  self.assertTrue(r["trace_valid"]); self.assertEqual(r["verified_steps"],3); self.assertTrue(r["final_answer_correct"])
  self.assertFalse(r["model_invoked"]); self.assertFalse(r["training_performed"])
 def test_wrong_intermediate_invalidates_trace(self):
  r=verify_rational_steps([{"name":"x","expression":"4*4","claimed_value":"15"},{"name":"y","expression":"x+1","claimed_value":"16"}],"y","16")
  self.assertFalse(r["trace_valid"]); self.assertEqual(r["verified_steps"],0)
 def test_rejects_forward_and_unknown_references(self):
  r=verify_rational_steps([{"name":"x","expression":"later+1","claimed_value":"2"}],"x","2")
  self.assertFalse(r["trace_valid"]); self.assertTrue(any("unknown or forward reference" in x for x in r["issues"]))
 def test_rejects_python_execution_and_unsupported_ast(self):
  r=verify_rational_steps([{"name":"x","expression":"__import__('os').system('echo nope')","claimed_value":"0"}],"0","0")
  self.assertFalse(r["trace_valid"])
 def test_rejects_duplicate_names_and_division_by_zero(self):
  with self.assertRaisesRegex(ValueError,"duplicate step name"):
   verify_rational_steps([{"name":"x","expression":"1","claimed_value":"1"},{"name":"x","expression":"2","claimed_value":"2"}],"x","1")
  r=verify_rational_steps([{"name":"x","expression":"1/0","claimed_value":"0"}],"0","0")
  self.assertFalse(r["trace_valid"])
 def test_final_answer_expression_length_is_checked_before_parsing(self):
  r=verify_rational_steps([],"1"*513,"1")
  self.assertFalse(r["trace_valid"])
  self.assertTrue(any("complexity limit" in x for x in r["issues"]))
 def test_final_answer_must_match_exact_reference(self):
  r=verify_rational_steps([{"name":"x","expression":"1/3+1/3","claimed_value":"2/3"}],"x*3","3")
  self.assertFalse(r["final_answer_correct"]); self.assertFalse(r["trace_valid"])
 def test_rejects_complexity_and_bad_values(self):
  r=verify_rational_steps([{"name":"x","expression":"1+"+"1+"*200+"1","claimed_value":"1"}],"1","1")
  self.assertFalse(r["trace_valid"])
  r=verify_rational_steps([{"name":"x","expression":"1","claimed_value":True}],"1","1")
  self.assertFalse(r["trace_valid"])

if __name__=="__main__": unittest.main()
