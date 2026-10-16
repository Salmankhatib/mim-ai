"""Intent config — one switch, one file path."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class IntentConfig:
    """
    Intent matching config.

    enabled:
        False -> the registry is not consulted; no intent classification.

    strategy:
        "rule"    -> Jaccard matcher only, zero LLM cost
        "llm"     -> rely on the LLM's classify_intent tool
        "hybrid"  -> try rule first; if score < threshold, fall back to LLM

    intents_path:
        YAML file with your intents. If empty, no intents are loaded
        and the registry is empty (matches nothing).

    threshold:
        Minimum Jaccard score to accept a rule-based match.
    """
    enabled:      bool  = True
    strategy:     str   = "hybrid"     # rule | llm | hybrid
    intents_path: str   = ""
    threshold:    float = 0.55

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "IntentConfig":
        raw = dict(data or {})
        known = {"enabled", "strategy", "intents_path", "threshold"}
        return cls(**{key: value for key, value in raw.items() if key in known})