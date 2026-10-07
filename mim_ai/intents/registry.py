"""
Intent registry — English-named, multilingual-matched.

An intent is a named capability of your app. The NAME is always
English (enforced), because tools, handlers, and logs must stay
consistent no matter what language the user speaks. Only the
EXAMPLES are multilingual.

    Intent(
        name="get_weather",
        description="Return weather for a city.",
        examples=[
            "chkoun l'weather f Casa",         # arabizi
            "كيفاش الجو فكازا",                # darija
            "quel temps à Casablanca",         # french
            "what's the weather in Casablanca",# english
        ],
        tool="get_weather",   # optional: link to a registered tool
    )

The registry stores intents and offers:
    * match_rule_based(text) -> Intent | None    (fast, deterministic)
    * as_llm_tool()                              (classify_intent schema)
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml


_ASCII_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass
class Intent:
    name:        str
    description: str
    examples:    list[str] = field(default_factory=list)
    tool:        str | None = None

    def __post_init__(self) -> None:
        if not _ASCII_NAME_RE.match(self.name):
            raise ValueError(
                f"Intent name must be lowercase ASCII snake_case, "
                f"got {self.name!r}. Intents are English-internal by "
                f"design so logs and handlers stay portable."
            )


class IntentRegistry:
    def __init__(self) -> None:
        self._intents: dict[str, Intent] = {}

    # -----------------------------------------------------------------
    # Registration
    # -----------------------------------------------------------------
    def register(self, intent: Intent) -> None:
        if intent.name in self._intents:
            raise ValueError(f"Intent {intent.name!r} already registered")
        self._intents[intent.name] = intent

    def load_yaml(self, path: str | Path) -> int:
        """Load intents from a YAML file. Returns count loaded."""
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        count = 0
        for raw in data.get("intents", []):
            self.register(Intent(
                name=raw["name"],
                description=raw["description"],
                examples=raw.get("examples", []),
                tool=raw.get("tool"),
            ))
            count += 1
        return count

    def __len__(self) -> int:
        return len(self._intents)

    def __contains__(self, name: str) -> bool:
        return name in self._intents

    def all(self) -> list[Intent]:
        return list(self._intents.values())

    # -----------------------------------------------------------------
    # Rule-based matching — fast, deterministic, no LLM
    # -----------------------------------------------------------------
    def match_rule_based(
        self,
        text: str,
        threshold: float = 0.55,
    ) -> tuple[Intent | None, float]:
        """
        Return (intent, score). Score in [0, 1].

        Algorithm:
            1. Normalize both sides (lowercase, strip accents, collapse
               whitespace, drop punctuation).
            2. Tokenize on whitespace.
            3. Score = Jaccard similarity of token sets against each
               example; take the max across examples.
            4. Return the highest-scoring intent if >= threshold, else
               (None, best_score).

        Why Jaccard and not embeddings: zero dependencies, ~microseconds
        per call, and good enough for the short phrases users actually
        type. If you outgrow it, swap in a sentence-transformer.
        """
        norm_text = _normalize(text)
        tokens = set(norm_text.split())
        if not tokens:
            return None, 0.0

        best_intent: Intent | None = None
        best_score = 0.0

        for intent in self._intents.values():
            for example in intent.examples:
                ex_tokens = set(_normalize(example).split())
                if not ex_tokens:
                    continue
                inter = len(tokens & ex_tokens)
                union = len(tokens | ex_tokens)
                score = inter / union if union else 0.0
                if score > best_score:
                    best_score = score
                    best_intent = intent

        if best_score >= threshold:
            return best_intent, best_score
        return None, best_score

    # -----------------------------------------------------------------
    # LLM-assisted matching — expose intents as a tool schema
    # -----------------------------------------------------------------
    def as_llm_tool(self) -> dict:
        """
        Return an OpenAI-style tool schema that forces the model to
        pick exactly one registered intent. Add this to your chatbot's
        tool list to get accurate intent classification on any language.
        """
        names = [i.name for i in self._intents.values()]
        return {
            "type": "function",
            "function": {
                "name": "classify_intent",
                "description": (
                    "Classify the user's message into one of the "
                    "registered intents. Always choose exactly one. "
                    "If none fits, use 'unknown'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "enum": names + ["unknown"],
                            "description": "The matched intent name.",
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                    "required": ["intent"],
                },
            },
        }


# ---------------------------------------------------------------------------
# Text normalization for matching
# ---------------------------------------------------------------------------
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Lowercase, strip accents, drop punctuation, collapse whitespace."""
    # Decompose accented Latin letters and drop combining marks.
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text