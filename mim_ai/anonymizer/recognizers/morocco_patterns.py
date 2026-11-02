from __future__ import annotations

from presidio_analyzer import PatternRecognizer
from presidio_analyzer.pattern_recognizer import Pattern

from mim_ai.morocco_patterns import CIN_MA_REGEX, PHONE_MA_REGEX


class CINRecognizer(PatternRecognizer):
    def __init__(self) -> None:
        super().__init__(
            supported_entity="CIN_MA",
            name="CIN_MA",
            patterns=[
                Pattern(
                    name="cin_ma_pattern",
                    regex=CIN_MA_REGEX,
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
                    regex=PHONE_MA_REGEX,
                    score=0.9,
                )
            ],
            version="1.0",
        )


__all__ = ["CINRecognizer", "MAPhoneRecognizer"]
