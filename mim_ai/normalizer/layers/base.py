"""
Abstract base for normalizer layers.

Contract: `apply(text, context) -> (new_text, report_delta)`.
`context` carries pipeline state that later layers may need.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLayer(ABC):
    """Every normalizer layer implements this contract."""

    name: str = "base"

    @abstractmethod
    def apply(self, text: str, context: dict[str, Any]) -> tuple[str, dict]:
        """Return (transformed_text, report_delta)."""
        raise NotImplementedError