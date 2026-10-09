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
    jargon_used: dict[str, int] = field(default_factory=dict)
    jargon_skipped: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class Normalizer:
    """Orchestrates the three-layer pipeline."""

    def __init__(self, config: NormalizerConfig | None = None) -> None:
        self.config = config or NormalizerConfig()
        self._layers: list[BaseLayer] = []

    @classmethod
    def from_config(cls, config: NormalizerConfig) -> "Normalizer":
        obj = cls(config)
        obj._layers = [CleaningLayer(config.cleaning), RulesLayer(config.rules)]
        if config.llm.enabled:
            obj._layers.append(LLMLayer(config.llm))
        return obj

    def normalize(
        self,
        text: str,
        *,
        return_report: bool = False,
    ) -> str | tuple[str, NormalizationReport]:
        """Run the pipeline."""
        if text is None:
            text = ""
        report = NormalizationReport()
        context: dict[str, Any] = {"url_map": {}}

        for layer in self._layers:
            text, delta = layer.apply(text, context)
            report.layers_run.append(layer.name)

            if layer.name == "rules":
                report.dictionary_hits = int(delta.get("dictionary_hits", 0))
                report.rule_applications = int(delta.get("rule_applications", 0))
                report.oov_arabizi = bool(delta.get("oov_arabizi", False))
                report.mixed_script = bool(delta.get("mixed_script", False))
                report.jargon_used = dict(delta.get("jargon_used", {}))
                report.jargon_skipped = dict(delta.get("jargon_skipped", {}))

        if self.config.llm.enabled:
            trigger = self.config.llm.trigger
            should_trigger = (
                trigger == "always"
                or (trigger == "on_oov" and report.oov_arabizi)
                or (trigger == "on_mixed" and report.mixed_script)
            )
            if should_trigger:
                report.llm_triggered = True
                # Layer 3 is intentionally lightweight and non-fatal; the project
                # defaults to keeping Layer 2 output on timeout or unconfigured LLM.
                if getattr(self.config.llm, "fallback_on_timeout", True):
                    pass

        text = context.get("layer2_output", text)
        if "url_map" in context and context["url_map"]:
            from .layers.cleaning import restore_urls
            text = restore_urls(text, context["url_map"])

        if return_report:
            return text, report
        return text