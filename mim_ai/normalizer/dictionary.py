"""
Generic YAML loader and merger used by the Arabizi dictionary and
the Arabic-rules tables. Developer overrides always win on key
collision. Both a missing base file and a malformed override must
raise a clear error at construction time, not silently no-op.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any] | list:
    """Load YAML. Raise FileNotFoundError with a clear message if missing."""
    if not path.exists():
        raise FileNotFoundError(f"YAML file does not exist: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return data
    raise TypeError(f"YAML content must decode to a dict or list: {path}")


def merge_dicts(base: dict, override: dict) -> dict:
    """Shallow merge. `override` wins on key collision."""
    merged = dict(base)
    merged.update(override)
    return merged