from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .config import AnonymizerConfig, load_config
from .operators import build_operators
from .recognizers.custom import build_custom_recognizers
from .recognizers.morocco_patterns import CINRecognizer, MAPhoneRecognizer


@dataclass
class AnonymizationResult:
    text: str
    entities_found: list[dict[str, Any]] = field(default_factory=list)
    operators_applied: list[str] = field(default_factory=list)


def _resolve_config(config: Mapping[str, Any] | dict[str, Any] | AnonymizerConfig | None, config_path: str | None) -> AnonymizerConfig:
    if config_path is not None:
        return load_config(config_path)
    if isinstance(config, AnonymizerConfig):
        return config
    if isinstance(config, Mapping):
        return load_config(dict(config))
    try:
        from mim_ai.config import load_config as load_main_config

        return load_main_config().anonymizer
    except Exception:
        return AnonymizerConfig()


def _build_analyzer(config: AnonymizerConfig):
    from presidio_analyzer import AnalyzerEngine

    analyzer = AnalyzerEngine()
    analyzer.registry.add_recognizer(CINRecognizer())
    analyzer.registry.add_recognizer(MAPhoneRecognizer())

    for recognizer in build_custom_recognizers(getattr(config, "custom_patterns", [])):
        analyzer.registry.add_recognizer(recognizer)

    return analyzer


def anonymize(
    text: str,
    *,
    config: dict[str, Any] | AnonymizerConfig | None = None,
    config_path: str | None = None,
) -> AnonymizationResult:
    """Anonymize text using the built-in Presidio engine plus Morocco-specific recognizers."""
    cfg = _resolve_config(config, config_path)
    if text is None:
        text = ""

    if not cfg.enabled:
        return AnonymizationResult(text=str(text), entities_found=[], operators_applied=[])

    analyzer = _build_analyzer(cfg)
    results = analyzer.analyze(text=str(text), language="en")
    operators = build_operators(cfg)

    from presidio_anonymizer import AnonymizerEngine

    anonymizer_engine = AnonymizerEngine()
    anonymized = anonymizer_engine.anonymize(
        text=str(text),
        analyzer_results=results,
        operators=operators,
    )

    result_items = getattr(anonymized, "items", [])
    entities_found = [
        {
            "type": item.entity_type,
            "start": item.start,
            "end": item.end,
            "score": float(getattr(item, "score", 0.0)),
        }
        for item in results
    ]
    operators_applied = list(dict.fromkeys(item.operator for item in result_items))

    return AnonymizationResult(
        text=anonymized.text,
        entities_found=entities_found,
        operators_applied=operators_applied,
    )


__all__ = ["AnonymizationResult", "anonymize"]
