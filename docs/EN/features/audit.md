# Audit and logging

## What it does

MIM includes a compliance-oriented audit log and a normalizer log. These are designed for traceability and operational diagnostics.

## Why it matters

Production AI systems need accountability. Audit logs support compliance review and operational debugging.

## Example

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")
app.chat("salam", session_id="demo")
```

The audit and normalizer loggers are configured through the main config object and can target different backends.

## Benefits

- compliant by design
- easy to query later
- better support for production review and debugging
