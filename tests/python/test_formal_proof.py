import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from ultron_core.formal_proof import preflight_lean_source,verify_lean_file

class LeanProofCheckerTests(unittest.TestCase):
 def test_preflight_requires_named_theorem(self):
  self.assertTrue(preflight_lean_source("theorem add_zero (n : Nat) : n + 0 = n := by simp","add_zero")["preflight_passed"])
  self.assertFalse(preflight_lean_source("theorem other : True := by trivial","my_result")["preflight_passed"])
 def test_ignores_sorry_in_comments_and_strings(self):
  source='/- sorry nested /- admit -/ comment -/\n-- sorry\ndef msg := "sorry admit"\ntheorem safe : True := by trivial'
  self.assertTrue(preflight_lean_source(source,"safe")["preflight_passed"])
 def test_rejects_sorry_and_admit_tokens(self):
  for word in ("sorry","admit"):
   with self.subTest(word=word):
    r=preflight_lean_source(f"theorem t : True := by {word}","t")
    self.assertFalse(r["preflight_passed"])
 def test_rejects_bad_comment_string_and_identifier(self):
  with self.assertRaisesRegex(ValueError,"unterminated"):
   preflight_lean_source("/- not closed","t")
  with self.assertRaisesRegex(ValueError,"identifier"):
   preflight_lean_source("theorem t : True := by trivial","bad name")
 def test_lean_success_is_reported_only_after_explicit_invocation(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"proof.lean"; p.write_text("theorem t : True := by trivial",encoding="utf-8")
   with patch("ultron_core.formal_proof.subprocess.run",return_value=SimpleNamespace(returncode=0,stdout="Lean 4",stderr="")) as run:
    r=verify_lean_file(p,"t")
   self.assertTrue(r["verified"]); self.assertTrue(r["lean_invoked"])
   self.assertEqual(run.call_args.args[0],["lean",str(p)])
   self.assertFalse(run.call_args.kwargs["shell"])
 def test_missing_lean_and_timeout_do_not_pass(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"proof.lean"; p.write_text("theorem t : True := by trivial",encoding="utf-8")
   with patch("ultron_core.formal_proof.subprocess.run",side_effect=FileNotFoundError):
    self.assertEqual(verify_lean_file(p,"t")["status"],"lean_unavailable")
   import subprocess
   with patch("ultron_core.formal_proof.subprocess.run",side_effect=subprocess.TimeoutExpired("lean",2)):
    self.assertEqual(verify_lean_file(p,"t")["status"],"timeout")
 def test_nonzero_exit_and_sorry_warning_never_pass(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"proof.lean"; p.write_text("theorem t : True := by trivial",encoding="utf-8")
   with patch("ultron_core.formal_proof.subprocess.run",return_value=SimpleNamespace(returncode=1,stdout="",stderr="error")):
    self.assertFalse(verify_lean_file(p,"t")["verified"])
   with patch("ultron_core.formal_proof.subprocess.run",return_value=SimpleNamespace(returncode=0,stdout="",stderr="declaration uses 'sorry'")):
    self.assertEqual(verify_lean_file(p,"t")["status"],"rejected_sorry_warning")
 def test_file_extension_and_timeout_are_bounded(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"proof.txt"; p.write_text("x",encoding="utf-8")
   with self.assertRaisesRegex(ValueError,".lean"):
    verify_lean_file(p,"t")
   p=Path(d)/"proof.lean"; p.write_text("theorem t : True := by trivial",encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"at most 120"):
    verify_lean_file(p,"t",timeout_seconds=121)

if __name__=="__main__": unittest.main()
