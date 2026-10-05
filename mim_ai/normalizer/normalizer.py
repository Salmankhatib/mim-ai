"""
mim_ai.normalizer.normalizer
============================

Main normalizer orchestrator for Moroccan Darija text.

The normalizer is a **three-layer pipeline**. Each layer is independent,
swappable, and controlled from a single config file. Layers are ordered
from cheapest to most expensive so developers can disable expensive
layers to hit their latency budget.

    ┌──────────────────────────────────────────────────────────────┐
    │ Layer 1 — Universal Text Cleaning              (near 0 ms)   │
    ├──────────────────────────────────────────────────────────────┤
    │ Layer 2 — Rule-Based Darija Normalization      (< 5 ms)      │
    ├──────────────────────────────────────────────────────────────┤
    │ Layer 3 — LLM Normalizer (optional)            (200–800 ms)  │
    └──────────────────────────────────────────────────────────────┘

Layer 1 — Universal Text Cleaning
---------------------------------
Language-agnostic, pure Python, zero measurable latency.

Responsibilities:
    * Unicode NFC normalization (guarantees byte-stable comparisons).
    * Collapse runs of whitespace into a single space.
    * Strip control characters (\\x00–\\x1F, \\x7F) except \\n.
    * Strip tatweel (ـ) — it is decorative and inflates token length.
    * Optionally strip URLs, @mentions, #hashtags (config toggles).

This layer NEVER changes the language or script of the text.

Layer 2 — Rule-Based Darija Normalization
-----------------------------------------
Deterministic, dictionary-driven, low latency.

This layer acts as the "script & code-switch detection" we use an inline
per-token script check:

    if token is Arabic script   -> apply Arabic orthography rules
    if token in ARABIZI_DICT    -> replace with canonical Arabic form
    if token in SKIP_WORDS      -> leave untouched (fr / en)
    otherwise                   -> leave untouched (OOV)

Arabic-script rules (safe for BOTH MSA and Darija):
    * Unify Alef forms:      أ إ آ ٱ  ->  ا
    * Unify Ya forms:        ى         ->  ي
    * Unify Ta Marbuta:      ة         ->  ه   (config toggle)
    * Remove tashkeel (diacritics) if config.remove_diacritics.
    * Normalize Arabic-Indic digits  ٠١٢٣٤٥٦٧٨٩ -> 0123456789.

Arabizi handling — as a *dictionary*, not a transliterator:

    Arabizi has no standard orthography, so character-level
    transliteration is fundamentally ambiguous (`3` = ع *or* غ,
    `7` = ح *or* خ, `9` = ق *or* ص). 
    We therefore treat Arabizi as a **whole-word dictionary problem**. The dictionary maps
    variant spellings to a canonical Arabic-script form:

        me3lich / ma3lich / m3lich  ->  معلش
        wa7ed   / wahed             ->  واحد
        kayn    / kayen             ->  كاين

    Base dictionary:       normalizer/data/arabizi_darija.yaml
    Developer overrides:   config.rules.arabizi_dict_path
    Developer jargon always wins on key collision.

Layer 2 also emits a per-call `NormalizationReport` with the
`oov_arabizi` flag set when Latin-script tokens could not be
resolved. Layer 3 uses this flag as its default trigger.

Layer 3 — LLM Normalizer (optional)
-----------------------------------
Off by default. Enabled via `config.normalizer.llm.enabled = True`.

Uses a **single prompt**, no chain-of-thought, no few-shot examples
— every extra token costs latency. Recommended backend is the
MNTRA-Mistral Darija model (dialect-aware out of the box), but any
OpenAI-compatible endpoint works.

Trigger modes (`config.llm.trigger`):
    * "always"    — every call hits the LLM (best quality, slowest)
    * "on_oov"    — only when Layer 2 flagged OOV Arabizi (default)
    * "on_mixed"  — only when the input mixes Arabic + Latin scripts

If the LLM call exceeds `config.llm.timeout_ms`, we fall back to
the Layer 2 output transparently. The caller never sees an error.

Usage
-----
    from mim_ai.normalizer import Normalizer
    from mim_ai.normalizer.schema import NormalizerConfig

    norm = Normalizer(NormalizerConfig())              # defaults
    clean = norm.normalize("salam, bghit n3ref wa7ed")
    clean, report = norm.normalize(text, return_report=True)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .layers import BaseLayer, CleaningLayer, RulesLayer, LLMLayer
from .schema import NormalizerConfig


# ---------------------------------------------------------------------------
# Report — returned alongside the normalized text when requested.
# ---------------------------------------------------------------------------
@dataclass
class NormalizationReport:
    """Diagnostics for a single `normalize()` call."""

    layers_run: list[str] = field(default_factory=list)
    oov_arabizi: bool = False               # set by Layer 2, read by Layer 3
    mixed_script: bool = False              # arabic + latin in same input
    llm_triggered: bool = False
    llm_timed_out: bool = False
    dictionary_hits: int = 0
    rule_applications: int = 0


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class Normalizer:
    """
    Orchestrates the three-layer pipeline.

    The constructor is cheap — all heavy work (dictionary loading,
    LLM client setup) happens in `from_config()` so callers can build
    a normalizer once at app startup and reuse it.

    Note:
        Layers 1 and 2 are ALWAYS built. Layer 3 is only built when
        `config.llm.enabled` is True, so the zero-latency path stays
        dependency-free.
    """

    def __init__(self, config: NormalizerConfig | None = None) -> None:
        self.config = config or NormalizerConfig()
        self._layers: list[BaseLayer] = []

    @classmethod
    def from_config(cls, config: NormalizerConfig) -> "Normalizer":
        """
        Build the pipeline from config.

        TODO:
            - Instantiate CleaningLayer(config.cleaning).
            - Instantiate RulesLayer(config.rules) — this loads the
              base Arabizi dict + the developer override + skip words.
            - If config.llm.enabled: instantiate LLMLayer(config.llm).
            - Validate config via schema; fail loudly on typos.
        """
        raise NotImplementedError

    def normalize(
        self,
        text: str,
        *,
        return_report: bool = False,
    ) -> str | tuple[str, NormalizationReport]:
        """
        Run the pipeline.

        TODO:
            - Run Layer 1 -> Layer 2 unconditionally.
            - Decide whether to fire Layer 3 based on config.llm.trigger
              and the report flags from Layer 2.
            - On LLM timeout: return Layer 2 output, set
              report.llm_timed_out = True, do NOT raise.
            - Return the text, or (text, report) if `return_report`.
        """
        raise NotImplementedError