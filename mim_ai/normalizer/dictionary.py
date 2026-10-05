"""
Generic YAML loader and merger used by the Arabizi dictionary and
the Arabic-rules tables. Developer overrides always win on key
collision. Both a missing base file and a malformed override must
raise a clear error at construction time, not silently no-op.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def load_yaml(path: Path) -> dict[str, Any] | list:
    """Load YAML. Raise FileNotFoundError with a clear message if missing."""
    raise NotImplementedError


def merge_dicts(base: dict, override: dict) -> dict:
    """Shallow merge. `override` wins on key collision."""
    raise NotImplementedError