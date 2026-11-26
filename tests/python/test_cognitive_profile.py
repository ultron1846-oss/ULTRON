import unittest
import math

from ultron_core.cognitive_profile import CognitiveBehaviorProfile, CognitiveMode


class CognitiveBehaviorProfileTests(unittest.TestCase):
    def test_default_profile_has_valid_balanced_policy(self):
        profile = CognitiveBehaviorProfile.default()
        policy = profile.policy_for()
        self.assertEqual(policy["mode"], "balanced")
        self.assertTrue(policy["require_evidence_for_claims"])
        self.assertTrue(policy["preserve_user_goal"])
        self.assertTrue(policy["avoid_fake_introspection"])

    def test_modes_select_distinct_bounded_policies(self):
        profile = CognitiveBehaviorProfile.default()
        quick = profile.policy_for(CognitiveMode.QUICK)
        deep = profile.policy_for(CognitiveMode.DEEP_REASONING)
        math = profile.policy_for(CognitiveMode.MATHEMATICAL)
        creative = profile.policy_for(CognitiveMode.CREATIVE)
        reflective = profile.policy_for(CognitiveMode.REFLECTIVE)
        self.assertLess(quick["reasoning_effort"], deep["reasoning_effort"])
        self.assertLess(quick["max_planning_steps"], deep["max_planning_steps"])
        self.assertGreaterEqual(deep["critique_passes"], 2)
        self.assertTrue(math["require_formal_verification"])
        self.assertEqual(creative["critique_passes"], 0)
        self.assertTrue(reflective["review_goal_alignment"])

    def test_invalid_policy_values_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "in \[0, 1\]"):
            CognitiveBehaviorProfile(reasoning_effort=1.1)
        with self.assertRaisesRegex(ValueError, "positive"):
            CognitiveBehaviorProfile(planning_steps=0)
        with self.assertRaisesRegex(TypeError, "must be bool"):
            CognitiveBehaviorProfile(preserve_user_goal=1)

    def test_non_finite_weights_are_rejected(self):
        fields = ("factuality_priority", "reasoning_effort", "conversational_naturalness",
                  "creative_flexibility", "self_check_strength", "uncertainty_calibration",
                  "empathy_and_context")
        for field in fields:
            for value in (math.nan, math.inf, -math.inf):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, "finite"):
                    CognitiveBehaviorProfile(**{field: value})

    def test_policy_includes_custom_behavior_weights(self):
        profile = CognitiveBehaviorProfile(factuality_priority=0.12,
            conversational_naturalness=0.23, creative_flexibility=0.45,
            empathy_and_context=0.34)
        policy = profile.policy_for()
        self.assertEqual(policy["factuality_priority"], 0.12)
        self.assertEqual(policy["conversational_naturalness"], 0.23)
        self.assertEqual(policy["creative_flexibility"], 0.45)
        self.assertEqual(policy["empathy_and_context"], 0.34)

    def test_mode_must_be_explicit_enum(self):
        with self.assertRaises(TypeError):
            CognitiveBehaviorProfile.default().policy_for("deep_reasoning")


if __name__ == "__main__":
    unittest.main()
