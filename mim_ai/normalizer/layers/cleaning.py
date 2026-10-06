"""
Layer 1 — Universal Text Cleaning.

Language-agnostic, pure Python, near-zero latency. Runs once on the
whole text before any tokenization.

Order of operations matters and is documented inline. The key trick:
URLs are protected FIRST, before anything else can touch them, using
a placeholder that survives every later layer. The original URL is
stored in `context["url_map"]` and restored by the orchestrator at
the very end of the pipeline.

Config toggles:
    preserve_urls  (default True)  — protect scheme:// and www. URLs
    strip_tatweel  (default True)  — remove the Arabic kashida char
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from .base import BaseLayer
from ..schema import CleaningConfig


# ---------------------------------------------------------------------------
# URL detection
# ---------------------------------------------------------------------------
# Strict: only matches strings that clearly START with a scheme or `www.`.
# Deliberately does NOT try to catch bare domains like "example.ma" or
# "casa.ma" — those collide with Arabizi tokens and filenames, and the
# false-positive rate is not worth the coverage.
#
# \S+ greedily consumes everything non-whitespace after the prefix, which
# is what we want: URLs rarely contain spaces in chat text.
URL_RE = re.compile(
    r"(?:https?|wss?|ftp)://\S+"        # scheme://...
    r"|www\.\S+",                        # www....
    re.IGNORECASE,
)

# Placeholder format: <URL_N>. Only ASCII, no dots, no underscores beyond
# the fixed prefix — safe against every rule in Layer 2 and against most
# LLM paraphrasing (bracketed tokens are usually preserved verbatim).
_PLACEHOLDER_RE = re.compile(r"<URL_(\d+)>")


class CleaningLayer(BaseLayer):
    name = "cleaning"

    def __init__(self, config: CleaningConfig) -> None:
        self.config = config

    def apply(self, text: str, context: dict[str, Any]) -> tuple[str, dict]:
        url_map: dict[str, str] = {}

        # 1. Unicode NFC. Must be first so every later comparison is
        #    byte-stable (é as one codepoint, not two).
        text = unicodedata.normalize("NFC", text)

        # 2. Protect URLs BEFORE any other step. From here on, the URL
        #    text is not in `text` — only a short placeholder is. Any
        #    later rule that would have damaged the URL now operates on
        #    a harmless ASCII token instead.
        if self.config.preserve_urls:
            text = self._protect_urls(text, url_map)

        # 3. Zero-width and bidi-control characters. These hide inside
        #    "spaces" pasted from web pages and are the #1 cause of
        #    "why doesn't my string match?" bugs.
        text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]", "", text)

        # 4. Other control characters. \n is kept so paragraph structure
        #    survives for the LLM layer.
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # 5. Tatweel / kashida. Decorative only; inflates token length
        #    without adding meaning.
        if self.config.strip_tatweel:
            text = text.replace("\u0640", "")

        # 6. Collapse whitespace. Runs last so the placeholders we
        #    inserted above are cleanly separated by single spaces.
        text = re.sub(
            r"[ \t\u00a0\u2000-\u200a\u202f\u205f\u3000]+",
            " ",
            text,
        )
        text = text.strip()

        # Hand the URL map to the orchestrator so it can restore at the
        # very end of the pipeline (after Layer 3, not before).
        context["url_map"] = url_map
        return text, {"urls_protected": len(url_map)}

    # -----------------------------------------------------------------------
    def _protect_urls(self, text: str, url_map: dict[str, str]) -> str:
        """
        Replace every URL with `<URL_N>` and remember the original.

        N is the index into `url_map`, so restoration is a flat dict
        lookup — O(1) per URL, no regex scanning of the URL body at
        restore time.
        """
        def repl(match: re.Match) -> str:
            token = f"<URL_{len(url_map)}>"
            url_map[token] = match.group(0)
            return token

        return URL_RE.sub(repl, text)


# ---------------------------------------------------------------------------
# Restoration helper — called by the orchestrator, not by this layer.
# ---------------------------------------------------------------------------
def restore_urls(text: str, url_map: dict[str, str]) -> str:
    """
    Put the original URLs back into the text.

    Called by `Normalizer.normalize()` AFTER Layer 3 (LLM) has run, so
    the model never sees the real URL. The LLM may still decide to drop
    or paraphrase the placeholder — see the prompt template in
    `layers/llm.py` for the instruction that prevents it.
    """
    if not url_map:
        return text
    return _PLACEHOLDER_RE.sub(
        lambda m: url_map.get(m.group(0), m.group(0)),
        text,
    )