from __future__ import annotations


class BasePatternRecognizer:
    """Small compatibility shim for custom recognizer construction."""

    @staticmethod
    def make_recognizer(supported_entity: str, pattern: str, name: str | None = None, score: float = 0.8):
        from presidio_analyzer import PatternRecognizer

        return PatternRecognizer(
            supported_entity=supported_entity,
            name=name or supported_entity,
            patterns=[{"name": name or supported_entity, "regex": pattern, "score": score}],
            version="1.0",
        )


__all__ = ["BasePatternRecognizer"]
