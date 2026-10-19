# Normalizer

## What it does

The normalizer cleans user text before it reaches a model. It handles Darija noise such as Arabizi, inconsistent punctuation, spelling variations, and script mixing.

## Why it matters

A model gets better results when the input is controlled. The cleaner the text, the lower the risk of confusion, false intent matching, and poor generation quality.

## How it works

The normalizer is a two-layer pipeline:

1. Cleaning layer
2. Rule-based Darija layer

## Example

```python
from mim_ai import Mim

app = Mim.from_config("config.yaml")
text = "salam wa7ed 3la ekher, bghit n3ref kifach nt3amro app?"
print(app.normalizer.normalize(text))
```

Normalization preserves the input script: Arabizi variants resolve to canonical Arabizi, while Arabic variants resolve to canonical Arabic. It does not translate between scripts.

Normalizer feedback logs record counts for skipped/OOV tokens by default, not the raw tokens. Set `logs.capture_skipped_tokens: true` only when storing those user-provided tokens is acceptable for your application.

## Config keys

In the config, the normalizer can be configured through:

- `normalizer.enabled`
- `normalizer.cleaning`
- `normalizer.rules`

## Benefits

- faster than model-only cleanup
- compatible with Darija-specific text patterns
- easy to tune with custom dictionaries
