import json
import unittest

from ultron_core.data_generation import generate_examples
from ultron_core.problem import (
    CoreExactVerifier,
    Problem,
    ProblemVerifier,
    ReplayGeneratorVerifier,
)
from ultron_core.task_schema import MathTaskRecord, VerificationReceipt


def _worked_problem():
    source_record = {
        "problem": "Calculate 2 + 2.",
        "answer": "4",
        "topic": "arithmetic",
        "seed": 17,
        "difficulty": 1,
        "steps": ["Identify the two addends.", "Add 2 and 2 to obtain 4."],
        "ingredients": {"operands": [2, 2], "operator": "+"},
    }
    problem = Problem.from_generator(source_record, source="test.fixture")
    verifier = ReplayGeneratorVerifier(
        source_record, lambda record: record["answer"] == "4", source="test.fixture"
    )
    return problem, verifier


class MathTaskSerializationTests(unittest.TestCase):
    def test_canonical_json_round_trip_and_task_identity(self):
        problem, verifier = _worked_problem()
        task = MathTaskRecord.from_verifier(
            problem, verifier,
            verifier_id="test.replay_verifier",
            verifier_version="1",
        )

        encoded = task.to_json()
        restored = MathTaskRecord.from_json(encoded)

        self.assertEqual(restored.to_dict(), task.to_dict())
        self.assertEqual(restored.task_id, task.task_id)
        self.assertEqual(restored.to_json(), encoded)
        self.assertTrue(restored.training_eligible)

    def test_training_target_contains_only_problem_derivation_and_answer(self):
        problem, verifier = _worked_problem()
        task = MathTaskRecord.from_verifier(
            problem, verifier,
            verifier_id="test.replay_verifier",
            verifier_version="1",
        )

        target = task.to_training_target_dict()
        self.assertEqual(set(target), {"problem", "derivation", "answer"})
        self.assertEqual(target["problem"], problem.prompt)
        self.assertEqual(target["derivation"], list(problem.steps))
        self.assertEqual(target["answer"], problem.answer)
        self.assertNotIn("verification", target)
        self.assertNotIn("verifier_id", task.to_training_target_json())

    def test_answer_only_verifier_does_not_authorize_derivation_target(self):
        example = generate_examples(seed=99, count=1)[0]
        problem = example.to_problem()
        task = MathTaskRecord.from_verifier(
            problem, CoreExactVerifier(),
            verifier_id="ultron_core.CoreExactVerifier",
            verifier_version="1",
        )

        self.assertEqual(task.verification.verified_fields, ("problem", "answer"))
        self.assertFalse(task.training_eligible)
        with self.assertRaisesRegex(ValueError, "verified problem, derivation, and answer"):
            task.to_training_target_dict()

    def test_rejected_verifier_result_cannot_be_exported(self):
        class RejectingVerifier(ProblemVerifier):
            def verify(self, problem):
                return False

        problem, _ = _worked_problem()
        task = MathTaskRecord.from_verifier(
            problem, RejectingVerifier(),
            verifier_id="test.rejecting_verifier",
            verifier_version="1",
        )

        self.assertEqual(task.verification.outcome, "rejected")
        self.assertFalse(task.training_eligible)
        with self.assertRaisesRegex(ValueError, "verified problem, derivation, and answer"):
            task.to_training_target_json()

    def test_verifier_must_return_an_actual_boolean(self):
        class AmbiguousVerifier(ProblemVerifier):
            def verify(self, problem):
                return "true"

        problem, _ = _worked_problem()
        with self.assertRaisesRegex(TypeError, "must return a boolean"):
            MathTaskRecord.from_verifier(
                problem, AmbiguousVerifier(),
                verifier_id="test.ambiguous_verifier",
                verifier_version="1",
            )

    def test_receipt_is_bound_to_full_problem_contents(self):
        problem, verifier = _worked_problem()
        task = MathTaskRecord.from_verifier(
            problem, verifier,
            verifier_id="test.replay_verifier",
            verifier_version="1",
        )
        payload = task.to_dict()
        payload["problem"]["answer"] = "5"

        with self.assertRaisesRegex(ValueError, "verification receipt does not match"):
            MathTaskRecord.from_dict(payload)

    def test_task_id_detects_document_tampering(self):
        problem, verifier = _worked_problem()
        task = MathTaskRecord.from_verifier(
            problem, verifier,
            verifier_id="test.replay_verifier",
            verifier_version="1",
        )
        payload = task.to_dict()
        payload["task_id"] = "0" * 64

        with self.assertRaisesRegex(ValueError, "task_id does not match"):
            MathTaskRecord.from_dict(payload)

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            MathTaskRecord.from_json('{"task_id":"first","task_id":"second"}')

    def test_unknown_task_and_problem_fields_are_rejected(self):
        problem, verifier = _worked_problem()
        task = MathTaskRecord.from_verifier(
            problem, verifier,
            verifier_id="test.replay_verifier",
            verifier_version="1",
        )
        task_payload = task.to_dict()
        task_payload["untrusted_extra"] = "ignored?"
        with self.assertRaisesRegex(ValueError, "math task fields"):
            MathTaskRecord.from_dict(task_payload)

        problem_payload = problem.to_dict()
        problem_payload["untrusted_extra"] = "ignored?"
        with self.assertRaisesRegex(ValueError, "problem document fields"):
            Problem.from_dict(problem_payload)

    def test_invalid_derivation_rows_fail_closed(self):
        record = {
            "problem": "Calculate 2 + 2.",
            "answer": "4",
            "topic": "arithmetic",
            "seed": 17,
            "difficulty": 1,
            "steps": ["valid step", 7],
        }
        with self.assertRaisesRegex(ValueError, "steps must be a sequence"):
            Problem.from_generator(record, source="test.fixture")

    def test_verification_receipt_json_has_explicit_scope(self):
        problem, verifier = _worked_problem()
        task = MathTaskRecord.from_verifier(
            problem, verifier,
            verifier_id="test.replay_verifier",
            verifier_version="1",
        )
        payload = json.loads(task.to_json())

        self.assertEqual(
            payload["verification"]["verified_fields"],
            ["problem", "derivation", "answer"],
        )
        self.assertRegex(payload["verification"]["subject_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
