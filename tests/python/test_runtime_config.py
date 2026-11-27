import json

import pytest

from ultron_core.runtime_config import (
    MAX_CONFIG_JSON_BYTES,
    RuntimeConfig,
)


def valid_payload(**overrides):
    value = RuntimeConfig().to_dict()
    value.update(overrides)
    return value


def test_default_runtime_config_is_bounded_and_non_authorizing():
    config = RuntimeConfig()
    assert config.memory_budget_gib == 6
    assert config.batch_size == 1
    assert config.sequence_length == 256
    assert config.gradient_accumulation_steps == 1
    assert config.training_authorized is False
    assert config.remote_execution_enabled is False


def test_mapping_and_json_round_trip():
    config = RuntimeConfig(
        memory_budget_gib=8,
        batch_size=2,
        sequence_length=512,
        gradient_accumulation_steps=4,
    )
    assert RuntimeConfig.from_mapping(config.to_dict()) == config
    assert RuntimeConfig.from_json(config.to_json()) == config
    assert json.loads(config.to_json()) == config.to_dict()


def test_preflight_kwargs_are_exact_and_do_not_include_authorization():
    config = RuntimeConfig(
        memory_budget_gib=9,
        batch_size=3,
        sequence_length=1024,
        gradient_accumulation_steps=8,
    )
    assert config.preflight_kwargs() == {
        "memory_budget_gib": 9,
        "batch_size": 3,
        "sequence_length": 1024,
        "gradient_accumulation_steps": 8,
    }
    assert "training_authorized" not in config.preflight_kwargs()
    assert "remote_execution_enabled" not in config.preflight_kwargs()


@pytest.mark.parametrize("budget", [True, False, 1, 11, 0, -1, 2.5, "6", None])
def test_memory_budget_rejects_invalid_or_out_of_range_values(budget):
    with pytest.raises((TypeError, ValueError)):
        RuntimeConfig(memory_budget_gib=budget)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("batch_size", True),
        ("batch_size", 0),
        ("batch_size", 17),
        ("sequence_length", 1),
        ("sequence_length", 2049),
        ("gradient_accumulation_steps", 0),
        ("gradient_accumulation_steps", 129),
    ],
)
def test_integer_fields_are_strictly_bounded(field, value):
    with pytest.raises((TypeError, ValueError)):
        RuntimeConfig(**{field: value})


@pytest.mark.parametrize(
    "field,value",
    [("training_authorized", True), ("remote_execution_enabled", True)],
)
def test_config_cannot_enable_training_or_remote_execution(field, value):
    with pytest.raises(ValueError, match="cannot"):
        RuntimeConfig(**{field: value})


def test_mapping_rejects_missing_and_unknown_keys():
    payload = valid_payload()
    del payload["batch_size"]
    with pytest.raises(ValueError, match="missing keys"):
        RuntimeConfig.from_mapping(payload)
    payload = valid_payload(unexpected="ignored?")
    with pytest.raises(ValueError, match="unknown keys"):
        RuntimeConfig.from_mapping(payload)


def test_mapping_rejects_non_mapping():
    with pytest.raises(TypeError):
        RuntimeConfig.from_mapping([])


def test_json_rejects_duplicate_keys():
    payload = RuntimeConfig().to_dict()
    source = json.dumps(payload)
    source = source[:-1] + ', "batch_size": 2}'
    with pytest.raises(ValueError, match="duplicate JSON key"):
        RuntimeConfig.from_json(source)


@pytest.mark.parametrize("source", ["", "{", "[]", "null", "42"])
def test_json_rejects_invalid_or_non_object_root(source):
    with pytest.raises((TypeError, ValueError)):
        RuntimeConfig.from_json(source)


def test_json_size_limit_is_enforced_before_parsing():
    source = " " * (MAX_CONFIG_JSON_BYTES + 1)
    with pytest.raises(ValueError, match="exceeds"):
        RuntimeConfig.from_json(source)


def test_json_rejects_authorization_override():
    payload = valid_payload(training_authorized=True)
    with pytest.raises(ValueError, match="cannot authorize"):
        RuntimeConfig.from_json(json.dumps(payload))
