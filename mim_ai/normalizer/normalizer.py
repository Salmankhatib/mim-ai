"""
mim_ai.normalizer.normalizer
============================

Main normalizer orchestrator for Moroccan Darija text.

The normalizer is a **two-layer pipeline**. Each layer is independent,
swappable, and controlled from a single config file. Layers are ordered
from cheapest to most expensive so developers can keep the hot path
fast and predictable.

    ┌──────────────────────────────────────────────────────────────┐
    │ Layer 1 — Universal Text Cleaning              (near 0 ms)   │
    ├──────────────────────────────────────────────────────────────┤
    │ Layer 2 — Rule-Based Darija Normalization      (< 5 ms)      │
    └──────────────────────────────────────────────────────────────┘

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

from .layers import BaseLayer, CleaningLayer, RulesLayer
from .schema import NormalizerConfig


# ---------------------------------------------------------------------------
# Report — returned alongside the normalized text when requested.
# ---------------------------------------------------------------------------

@dataclass
class NormalizationReport:
    """Diagnostics for a single `normalize()` call."""

    layers_run: list[str] = field(default_factory=list)
    oov_arabizi: bool = False
    mixed_script: bool = False
    dictionary_hits: int = 0
    rule_applications: int = 0
    jargon_used: dict[str, int] = field(default_factory=dict)
    jargon_skipped: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class Normalizer:
    """Orchestrates the two-layer pipeline."""

    def __init__(self, config: NormalizerConfig | None = None) -> None:
        self.config = config or NormalizerConfig()
        self._layers: list[BaseLayer] = []
        if self.config.enabled:
            self._layers = [CleaningLayer(self.config.cleaning), RulesLayer(self.config.rules)]

    @classmethod
    def from_config(cls, config: NormalizerConfig) -> "Normalizer":
        obj = cls(config)
        return obj

    def normalize(
        self,
        text: str,
        *,
        return_report: bool = False,
    ) -> str | tuple[str, NormalizationReport]:
        """Run the pipeline."""
        if not self.config.enabled:
            return (text, NormalizationReport()) if return_report else text
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

        text = context.get("layer2_output", text)
        if "url_map" in context and context["url_map"]:
            from .layers.cleaning import restore_urls
            text = restore_urls(text, context["url_map"])

        if return_report:
            return text, report
        return text