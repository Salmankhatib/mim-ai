"""
Layer 3 — LLM Normalizer (optional).

See `mim_ai.normalizer.normalizer` module docstring for the full spec.

    TODO:
        - build a single-prompt payload (see PROMPT below)
        - POST to config.endpoint with config.model
        - enforce config.timeout_ms with a hard cutoff
        - on any failure/timeout: return context["layer2_output"]
          unchanged, set report delta {"llm_timed_out": True}
"""

PROMPT = """\
You are a Moroccan Darija normalizer. Normalize the following text:
- Unify Arabic orthography (Alef, Ya, Ta Marbuta)
- Convert Arabizi (Latin-script Darija) to Arabic script
- Preserve French and English or other language words exactly
- Preserve punctuation and code-switching structure
- Output ONLY the normalized text, nothing else
- Preserve <URL_N> placeholders exactly as they appear

Text: {text}
"""


from __future__ import annotations

from typing import Any

from .base import BaseLayer
from ..schema import LLMConfig


class LLMLayer(BaseLayer):
    name = "llm"

    def __init__(self, config: LLMConfig, client: Any | None = None) -> None:
        self.config = config
        self.client = client   # inject an OpenAI-compatible client

    def apply(self, text: str, context: dict[str, Any]) -> tuple[str, dict]:
        raise NotImplementedError