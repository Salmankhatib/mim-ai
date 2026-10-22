# Anonymizer

The anonymizer module gives the project a config-first PII redaction layer built on Microsoft Presidio.

## Install the spaCy model

The anonymizer is an optional extra. Presidio's built-in recognizers also require the English spaCy model. Install both before the first anonymization call:

```bash
pip install "mim-ai[anonymizer]"
python -m spacy download en_core_web_lg
```

There is no automatic regex-only fallback when the model is missing. Moroccan CIN and phone recognizers are included, but the configured Presidio analyzer still needs its model to initialize.

## Quick start

```python
from mim_ai import anonymizer

result = anonymizer.anonymize("Call me at 0612345678 or hello@example.com")
print(result.text)
print(result.entities_found)
```

## Default behavior

The package includes:

- Presidio built-in recognizers for common PII such as email addresses and phone numbers.
- Morocco-specific recognizers for:
  - CIN (Carte d'Identité Nationale): `AB123456`
  - Moroccan phone numbers: `0612345678`, `+212612345678`
- A developer-configurable custom pattern list.

## YAML config example

```yaml
anonymizer:
  enabled: true
  default_operators:
    DEFAULT: replace
    CIN_MA: replace
    PHONE_MA: mask
  custom_patterns:
    - name: ORDER_ID
      pattern: "ORDER-[0-9]{6}"
      operator: replace
      params:
        new_value: "[ORDER]"
```

## Runtime config

```python
from mim_ai.anonymizer import anonymize

result = anonymize(
    "My card is AB123456 and ref ORDER-123456",
    config={
        "custom_patterns": [{
            "name": "ORDER_ID",
            "pattern": r"ORDER-[0-9]{6}",
            "operator": "replace",
            "params": {"new_value": "[ORDER]"},
        }]
    },
)
```

## Notes

- If the anonymizer block is absent from the config, safe defaults are used.
- The module is importable as both `from mim_ai import anonymizer` and `from mim_ai.anonymizer import anonymize`.
