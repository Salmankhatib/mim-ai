"""
Layer 1 — Universal Text Cleaning.

See `mim_ai.normalizer.normalizer` module docstring for the full spec.
Pure Python, no models, no dependencies beyond `unicodedata`.

    TODO:
        - unicodedata.normalize("NFC", text)
        - re.sub(r"\\s+", " ", text).strip()
        - remove control chars except \\n
        - remove tatweel if config.strip_tatweel
        - strip URLs/mentions/hashtags if config toggles are on
"""
from __future__ import annotations

from typing import Any

from .base import BaseLayer
from ..schema import CleaningConfig


class CleaningLayer(BaseLayer):
    name = "cleaning"

    def __init__(self, config: CleaningConfig) -> None:
        self.config = config

    def apply(self, text: str, context: dict[str, Any]) -> tuple[str, dict]:
        raise NotImplementedError