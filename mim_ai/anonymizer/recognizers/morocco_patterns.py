from __future__ import annotations

from presidio_analyzer import PatternRecognizer
from presidio_analyzer.pattern_recognizer import Pattern


class CINRecognizer(PatternRecognizer):
    def __init__(self) -> None:
        super().__init__(
            supported_entity="CIN_MA",
            name="CIN_MA",
            patterns=[
                Pattern(
                    name="cin_ma_pattern",
                    regex=r"\b[A-Z]{1,2}\d{5,6}\b",
                    score=0.85,
                )
            ],
            version="1.0",
        )


class MAPhoneRecognizer(PatternRecognizer):
    def __init__(self) -> None:
        super().__init__(
            supported_entity="PHONE_MA",
            name="PHONE_MA",
            patterns=[
                Pattern(
                    name="moroccan_phone_pattern",
                    regex=r"(?<!\d)(?:\+212|0)[2567]\d{8}(?!\d)",
                    score=0.9,
                )
            ],
            version="1.0",
        )


__all__ = ["CINRecognizer", "MAPhoneRecognizer"]
