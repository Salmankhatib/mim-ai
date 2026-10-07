"""Intent config — one switch, one file path."""
from __future__ import annotations

from dataclasses import dataclass


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