# Normalizer

## What it does

The normalizer cleans user text before it reaches a model. It handles Darija noise such as Arabizi, inconsistent punctuation, spelling variations, and script mixing.

## Why it matters

A model gets better results when the input is controlled. The cleaner the text, the lower the risk of confusion, false intent matching, and poor generation quality.

## How it works

The normalizer is a three-layer pipeline:

1. Cleaning layer
2. Rule-based Darija layer
3. Optional LLM refinement layer

## Example

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")
text = "salam wa7ed 3la ekher, bghit n3ref kifach nt3amro app?"
print(app.normalizer.normalize(text))
```

## Config keys

In the config, the normalizer can be configured through:

- `normalizer.enabled`
- `normalizer.cleaning`
- `normalizer.rules`
- `normalizer.llm`

## Benefits

- faster than model-only cleanup
- compatible with Darija-specific text patterns
- easy to tune with custom dictionaries
