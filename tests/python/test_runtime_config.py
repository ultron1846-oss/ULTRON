import json
import unittest
from unittest.mock import patch

import ultron_core.preflight as preflight_module
from ultron_core.preflight import preflight_training_plan_from_runtime_config
from ultron_core.runtime_config import MAX_CONFIG_JSON_BYTES, RuntimeConfig


def valid_payload(**overrides):
    value = RuntimeConfig().to_dict()
    value.update(overrides)
    return value


class RuntimeConfigTests(unittest.TestCase):
    def test_default_runtime_config_is_bounded_and_non_authorizing(self):
        config = RuntimeConfig()
        self.assertEqual(config.memory_budget_gib, 6)
        self.assertEqual(config.batch_size, 1)
        self.assertEqual(config.sequence_length, 256)
        self.assertEqual(config.gradient_accumulation_steps, 1)
        self.assertIs(config.training_authorized, False)
        self.assertIs(config.remote_execution_enabled, False)

    def test_mapping_and_json_round_trip(self):
        config = RuntimeConfig(
            memory_budget_gib=8,
            batch_size=2,
            sequence_length=512,
            gradient_accumulation_steps=4,
        )
        self.assertEqual(RuntimeConfig.from_mapping(config.to_dict()), config)
        self.assertEqual(RuntimeConfig.from_json(config.to_json()), config)
        self.assertEqual(json.loads(config.to_json()), config.to_dict())

    def test_preflight_kwargs_are_exact_and_do_not_include_authorization(self):
        config = RuntimeConfig(
            memory_budget_gib=9,
            batch_size=3,
            sequence_length=1024,
            gradient_accumulation_steps=8,
        )
        self.assertEqual(config.preflight_kwargs(), {
            "memory_budget_gib": 9,
            "batch_size": 3,
            "sequence_length": 1024,
            "gradient_accumulation_steps": 8,
        })
        self.assertNotIn("training_authorized", config.preflight_kwargs())
        self.assertNotIn("remote_execution_enabled", config.preflight_kwargs())

    def test_memory_budget_rejects_invalid_or_out_of_range_values(self):
        for budget in [True, False, 1, 11, 0, -1, 2.5, "6", None]:
            with self.subTest(budget=budget):
                with self.assertRaises((TypeError, ValueError)):
                    RuntimeConfig(memory_budget_gib=budget)

    def test_integer_fields_are_strictly_bounded(self):
        cases = [
            ("schema_version", True), ("schema_version", 2),
            ("batch_size", True), ("batch_size", 0), ("batch_size", 17),
            ("sequence_length", 1), ("sequence_length", 2049),
            ("gradient_accumulation_steps", 0),
            ("gradient_accumulation_steps", 129),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                with self.assertRaises((TypeError, ValueError)):
                    RuntimeConfig(**{field: value})

    def test_config_cannot_enable_training_or_remote_execution(self):
        for field, value in [
            ("training_authorized", True),
            ("remote_execution_enabled", True),
        ]:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "cannot"):
                    RuntimeConfig(**{field: value})

    def test_mapping_rejects_missing_and_unknown_keys(self):
        payload = valid_payload()
        del payload["batch_size"]
        with self.assertRaisesRegex(ValueError, "missing keys"):
            RuntimeConfig.from_mapping(payload)
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            RuntimeConfig.from_mapping(valid_payload(unexpected="not allowed"))

    def test_mapping_rejects_non_mapping_and_non_string_keys(self):
        with self.assertRaises(TypeError):
            RuntimeConfig.from_mapping([])
        payload = valid_payload()
        payload[7] = "invalid key"
        with self.assertRaisesRegex(TypeError, "keys must be strings"):
            RuntimeConfig.from_mapping(payload)

    def test_json_rejects_duplicate_keys(self):
        source = json.dumps(RuntimeConfig().to_dict())
        source = source[:-1] + ', "batch_size": 2}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            RuntimeConfig.from_json(source)

    def test_json_rejects_invalid_or_non_object_roots(self):
        for source in ["", "{", "[]", "null", "42"]:
            with self.subTest(source=source):
                with self.assertRaises((TypeError, ValueError)):
                    RuntimeConfig.from_json(source)

    def test_json_size_limit_is_enforced_before_parsing(self):
        source = " " * (MAX_CONFIG_JSON_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "exceeds"):
            RuntimeConfig.from_json(source)

    def test_json_rejects_authorization_override(self):
        payload = valid_payload(training_authorized=True)
        with self.assertRaisesRegex(ValueError, "cannot authorize"):
            RuntimeConfig.from_json(json.dumps(payload))

    def test_json_rejects_unpaired_unicode_surrogate(self):
        with self.assertRaisesRegex(ValueError, "invalid Unicode"):
            RuntimeConfig.from_json(chr(0xD800))

    def test_preflight_adapter_forwards_only_validated_settings(self):
        captured = {}

        def fake_preflight(model_config, splits, **kwargs):
            captured["model_config"] = model_config
            captured["splits"] = splits
            captured["kwargs"] = kwargs
            return {"status": "PREFLIGHT_ONLY"}

        model_config = object()
        splits = {"train": [], "validation": [], "test": []}
        runtime_config = RuntimeConfig(
            memory_budget_gib=7,
            batch_size=2,
            sequence_length=512,
            gradient_accumulation_steps=3,
        )
        with patch.object(preflight_module, "preflight_training_plan", fake_preflight):
            report = preflight_training_plan_from_runtime_config(
                model_config, splits, runtime_config,
                dataset_manifest_sha256="a" * 64,
            )

        self.assertEqual(report, {"status": "PREFLIGHT_ONLY"})
        self.assertIs(captured["model_config"], model_config)
        self.assertIs(captured["splits"], splits)
        self.assertEqual(captured["kwargs"], {
            "memory_budget_gib": 7,
            "batch_size": 2,
            "sequence_length": 512,
            "gradient_accumulation_steps": 3,
            "dataset_manifest_sha256": "a" * 64,
        })

    def test_preflight_adapter_requires_validated_runtime_config(self):
        with self.assertRaisesRegex(TypeError, "validated RuntimeConfig"):
            preflight_training_plan_from_runtime_config(
                object(), {}, {"memory_budget_gib": 6}
            )


if __name__ == "__main__":
    unittest.main()
