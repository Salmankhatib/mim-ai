"""
mim_ai.normalizer
=================

Darija normalizer for Moroccan Arabic (Darija) text.

This package exposes a single public entry point — `Normalizer` — plus
the config and report types a caller needs to drive it. Everything else
(layers, dictionaries, character tables) is internal and imported by
path when a developer needs to customize behavior.

Quick start
-----------
    from mim_ai.normalizer import Normalizer
    from mim_ai.normalizer import NormalizerConfig

    norm = Normalizer.from_config(NormalizerConfig())
    clean = norm.normalize("salam, bghit n3ref wa7ed chi haja")

    # With diagnostics:
    clean, report = norm.normalize(text, return_report=True)
    if report.oov_arabizi:
        ...   # hand off to Layer 3 (LLM)

Package layout
--------------
    normalizer.py     orchestrator + NormalizationReport
    schema.py         config dataclasses (NormalizerConfig, ...)

    darija_rules.py   token-level dispatch (Layer 2 brain)
    arabic_rules.py   character-level Arabic substitutions
    arabizi.py        Latin->Arabic whole-word dictionary
    dictionary.py     YAML loader + merger
    data/             package data (YAML dictionaries)

    layers/           pipeline wrappers for each layer
        base.py       BaseLayer ABC
        cleaning.py   Layer 1 — universal cleaning + URL protection
        rules.py      Layer 2 — wraps darija_rules.normalize_text
        llm.py        Layer 3 — optional LLM normalizer
"""

from .normalizer import Normalizer, NormalizationReport
from .schema import (
    NormalizerConfig,
    CleaningConfig,
    RulesConfig,
    LLMConfig,
)

__all__ = [
    # public API
    "Normalizer",
    "NormalizationReport",
    # config types (for callers building a config programmatically)
    "NormalizerConfig",
    "CleaningConfig",
    "RulesConfig",
    "LLMConfig",
]