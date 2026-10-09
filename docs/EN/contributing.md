# Contributing to MIM

Thanks for helping improve MIM.

## 1. Setup

```bash
python -m venv .venv
. .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
pip install pytest
```

## 2. Run tests

```bash
pytest -q
```

## 3. Contribution rules

- keep changes small and focused
- keep config-driven design intact
- prefer optional behavior over hard-coded assumptions
- document new configuration fields
- test behavior with real use cases, not only mocks

## 4. Pull request expectations

- explain the problem and solution clearly
- mention config changes
- include examples when behavior changes
- validate with relevant tests

## 5. Feature design guidelines

Features should remain:

- provider-agnostic
- config-driven
- easy to disable
- safe for production use

Thank you for contributing to a Darija-first AI stack for Moroccan developers.
