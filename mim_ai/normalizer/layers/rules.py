"""
Layer 2 — Rule-Based Darija Normalization.

See `mim_ai.normalizer.normalizer` module docstring for the full spec.

    TODO:
        - Tokenize on whitespace + punctuation (keep punctuation).
        - Per token: script_of(token) via utils.unicode_helpers.
            * "arabic" -> apply arabic_rules transformations.
            * "latin"  -> ArabiziDictionary.lookup(token) or skip-word check.
            * "mixed"  -> split on script boundary, recurse.
        - Accumulate report: dictionary_hits, rule_applications.
        - Set report["oov_arabizi"] = True if any latin token missed
          both the Arabizi dict and the skip-word list.
        - Set report["mixed_script"] = True if both scripts present.
"""
from __future__ import annotations

from typing import Any

from .base import BaseLayer
from ..arabizi import ArabiziDictionary
from ..schema import RulesConfig


class RulesLayer(BaseLayer):
    name = "rules"

    def __init__(self, config: RulesConfig) -> None:
        self.config = config
        self._arabizi = ArabiziDictionary.from_config(config)
        # TODO: load skip-words and arabic-rules overrides here too.

    def apply(self, text: str, context: dict[str, Any]) -> tuple[str, dict]:
        raise NotImplementedError