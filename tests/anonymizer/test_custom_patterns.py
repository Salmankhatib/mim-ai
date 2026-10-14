from types import MappingProxyType

from mim_ai.anonymizer import anonymize


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
