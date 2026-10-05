"""
Unicode range helpers.

Used by Layer 2's inline per-token script check — this is the
lightweight replacement for the dropped script-detection layer.
Pure Python, no dependencies.
"""
from __future__ import annotations

ARABIC_RANGES: tuple[tuple[int, int], ...] = (
    (0x0600, 0x06FF),   # Arabic
    (0x0750, 0x077F),   # Arabic Supplement
    (0x08A0, 0x08FF),   # Arabic Extended-A
    (0xFB50, 0xFDFF),   # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),   # Arabic Presentation Forms-B
)


def is_arabic_char(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in ARABIC_RANGES)


def is_arabic_script(token: str) -> bool:
    """True if the token contains at least one Arabic-script character."""
    return any(is_arabic_char(c) for c in token)


def is_latin_script(token: str) -> bool:
    """True if the token is ASCII letters only (rough Latin check)."""
    return token.isascii() and token.isalpha()


def script_of(token: str) -> str:
    """Coarse tag: 'arabic' | 'latin' | 'mixed' | 'other'."""
    has_ar = any(is_arabic_char(c) for c in token)
    has_la = any(c.isascii() and c.isalpha() for c in token)
    if has_ar and has_la:
        return "mixed"
    if has_ar:
        return "arabic"
    if has_la:
        return "latin"
    return "other"