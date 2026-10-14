from __future__ import annotations

from typing import Any

from presidio_analyzer import PatternRecognizer
from presidio_analyzer.pattern_recognizer import Pattern


def build_custom_recognizers(patterns: list[dict[str, Any]] | None) -> list[PatternRecognizer]:
    """Convert developer-provided regex patterns into Presidio PatternRecognizer objects."""
    recognizers: list[PatternRecognizer] = []
    for index, item in enumerate(patterns or []):
        if not isinstance(item, dict):
            continue
        pattern = item.get("pattern") or item.get("regex")
        if not pattern:
            continue
        entity_name = str(item.get("name") or item.get("entity") or f"CUSTOM_{index}")
        recognizers.append(
            PatternRecognizer(
                supported_entity=entity_name,
                name=entity_name,
                patterns=[
                    Pattern(
                        name=entity_name,
                        regex=str(pattern),
                        score=float(item.get("score", 0.8)),
                    )
                ],
                version="1.0",
            )
        )
    return recognizers


__all__ = ["build_custom_recognizers"]
