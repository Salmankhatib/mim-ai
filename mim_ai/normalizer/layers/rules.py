"""
Layer 2 — Rule-Based Darija Normalization.

See `mim_ai.normalizer.normalizer` module docstring for the full spec.
"""
from __future__ import annotations

from typing import Any

from .base import BaseLayer
from ..arabizi import ArabiziDictionary
from ..darija_rules import normalize_text
from ..schema import RulesConfig


class RulesLayer(BaseLayer):
    name = "rules"

    def __init__(self, config: RulesConfig) -> None:
        self.config = config
        self._arabizi = ArabiziDictionary.from_config(config)

    def apply(self, text: str, context: dict[str, Any]) -> tuple[str, dict]:
        normalized_text, delta = normalize_text(text, self.config, arabizi=self._arabizi)
        context["layer2_output"] = normalized_text
        context["jargon_used"] = delta.get("jargon_used", {})
        context["jargon_skipped"] = delta.get("jargon_skipped", {})
        return normalized_text, delta