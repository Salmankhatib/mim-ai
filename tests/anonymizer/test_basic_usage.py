import pytest

from mim_ai import anonymizer
from mim_ai.anonymizer import anonymize


@pytest.mark.requires_spacy
def test_module_imports():
    assert anonymizer is not None
    assert callable(anonymize)


@pytest.mark.requires_spacy
def test_basic_anonymize_returns_result_fields():
    result = anonymize("Reach me at hello@example.com")
    assert isinstance(result.text, str)
    assert isinstance(result.entities_found, list)
    assert isinstance(result.operators_applied, list)
