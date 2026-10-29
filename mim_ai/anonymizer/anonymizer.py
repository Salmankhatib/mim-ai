from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
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
    from mim_ai.config import load_config as load_main_config

    try:
        return load_main_config().anonymizer
    except FileNotFoundError:
        return AnonymizerConfig()


def _config_cache_key(config: AnonymizerConfig) -> str:
    patterns = []
    for item in getattr(config, "custom_patterns", []) or []:
        if not isinstance(item, dict):
            patterns.append(item)
            continue
        patterns.append({
            key: item[key]
            for key in ("name", "entity", "pattern", "regex", "score")
            if key in item
        })
    payload = {
        "enabled": bool(getattr(config, "enabled", True)),
        "language": config.language,
        "custom_patterns": patterns,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@lru_cache(maxsize=16)
def _build_analyzer_cached(cache_key: str):
    from presidio_analyzer import AnalyzerEngine

    payload = json.loads(cache_key)
    config = AnonymizerConfig(
        enabled=bool(payload.get("enabled", True)),
        language=payload.get("language", "en"),
        custom_patterns=list(payload.get("custom_patterns", [])),
    )

    analyzer = AnalyzerEngine()
    analyzer.registry.add_recognizer(CINRecognizer())
    analyzer.registry.add_recognizer(MAPhoneRecognizer())

    for recognizer in build_custom_recognizers(getattr(config, "custom_patterns", [])):
        analyzer.registry.add_recognizer(recognizer)

    return analyzer


@lru_cache(maxsize=1)
def _build_anonymizer_cached():
    try:
        from presidio_anonymizer import AnonymizerEngine
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            'Presidio anonymizer is not installed. Install the package with: pip install "mim-ai[anonymizer]"'
        ) from exc
    return AnonymizerEngine()


def _build_analyzer(config: AnonymizerConfig):
    try:
        import presidio_analyzer  # noqa: F401
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            'Presidio analyzer is not installed. Install the package with: pip install "mim-ai[anonymizer]"'
        ) from exc
    return _build_analyzer_cached(_config_cache_key(config))


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

    operators = build_operators(cfg)
    analyzer = _build_analyzer(cfg)
    results = analyzer.analyze(text=str(text), language=cfg.language)

    anonymizer_engine = _build_anonymizer_cached()
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
