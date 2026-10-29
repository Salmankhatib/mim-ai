from types import MappingProxyType

import pytest

from mim_ai.anonymizer import anonymize
from mim_ai.anonymizer.config import AnonymizerConfig
from mim_ai.anonymizer.operators import build_operators
from mim_ai.anonymizer.recognizers.custom import build_custom_recognizers


def test_custom_patterns_are_supported():
    text = "Please check ORDER-123456 in the system."
    result = anonymize(
        text,
        config={
            "custom_patterns": [
                {
                    "name": "ORDER_ID",
                    "pattern": r"ORDER-[0-9]{6}",
                    "operator": "replace",
                    "params": {"new_value": "[ORDER]"},
                }
            ]
        },
    )
    assert any(item["type"] == "ORDER_ID" for item in result.entities_found)
    assert "[ORDER]" in result.text


def test_custom_patterns_accept_dynamic_mapping_payloads():
    payload = MappingProxyType(
        {
            "enabled": True,
            "custom_patterns": [
                {
                    "name": "ORDER_ID",
                    "pattern": r"ORDER-[0-9]{6}",
                    "operator": "replace",
                    "params": {"new_value": "[ORDER]"},
                }
            ],
        }
    )

    result = anonymize("Reference ORDER-123456 is in the ticket.", config=payload)

    assert any(item["type"] == "ORDER_ID" for item in result.entities_found)
    assert "[ORDER]" in result.text


def test_unknown_operator_does_not_fall_back_to_replace():
    with pytest.raises(ValueError, match="Unsupported anonymizer operator"):
        build_operators(AnonymizerConfig(
            default_operators={"DEFAULT": "replce"},
        ))


def test_encrypt_operator_requires_a_valid_key():
    with pytest.raises(ValueError, match="requires params.key or params.key_env"):
        build_operators(AnonymizerConfig(default_operators={"DEFAULT": "encrypt"}))

    with pytest.raises(ValueError, match="16, 24, or 32 bytes"):
        build_operators(AnonymizerConfig(
            default_operators={
                "DEFAULT": {
                    "name": "encrypt",
                    "params": {"key": "too-short"},
                }
            }
        ))


def test_encrypt_operator_resolves_environment_key(monkeypatch):
    monkeypatch.setenv("MIM_TEST_ANONYMIZER_KEY", "0123456789abcdef")
    operators = build_operators(AnonymizerConfig(
        default_operators={
            "DEFAULT": {
                "name": "encrypt",
                "params": {"key_env": "MIM_TEST_ANONYMIZER_KEY"},
            }
        }
    ))

    assert operators["DEFAULT"].params["key"] == b"0123456789abcdef"


def test_custom_pattern_without_regex_fails_explicitly():
    with pytest.raises(ValueError, match="missing 'pattern'"):
        build_custom_recognizers([{"name": "MISSING"}])
