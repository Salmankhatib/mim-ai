import pytest

from mim_ai.anonymizer import anonymize


@pytest.mark.requires_spacy
def test_cin_detection():
    text = "My national identity card is AB123456 and it is valid."
    result = anonymize(text)
    assert any(item["type"] == "CIN_MA" for item in result.entities_found)
    assert result.text != text


@pytest.mark.requires_spacy
def test_real_world_cin_example_is_detected():
    text = "My CIN is AB58075 and I need to update it."
    result = anonymize(text)
    assert any(item["type"] == "CIN_MA" for item in result.entities_found)
    assert result.text != text
