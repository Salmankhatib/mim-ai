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
    llm_prompt:   str = (
        "Classify the user's message into one of the listed intents. "
        "Return only JSON with the keys intent and confidence. "
        "Use intent \"unknown\" when none fit.\n\n"
        "Registered intents:\n{intents}"
    )

    def __post_init__(self) -> None:
        if self.strategy not in {"rule", "llm", "hybrid"}:
            raise ValueError("intents.strategy must be 'rule', 'llm', or 'hybrid'")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("intents.threshold must be between 0 and 1")
        if not isinstance(self.llm_prompt, str) or not self.llm_prompt.strip():
            raise ValueError("intents.llm_prompt must be a non-empty string")

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "IntentConfig":
        raw = dict(data or {})
        known = {"enabled", "strategy", "intents_path", "threshold", "llm_prompt"}
        return cls(**{key: value for key, value in raw.items() if key in known})