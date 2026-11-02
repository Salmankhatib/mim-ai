"""
Minimal PII redaction for strings that are about to hit a log.

Best practice is to NEVER log user text at all. This module exists
for the few places where you must log a derived string (e.g. an
exception message) and want a last line of defense.
"""
from __future__ import annotations

import hashlib
import re

from ..morocco_patterns import CIN_MA_REGEX, PHONE_MA_REGEX

# Conservative patterns. Order matters: run email before phone so
# "a@b.ma" isn't partly eaten by the phone regex.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email",   re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("phone",   re.compile(PHONE_MA_REGEX)),
    ("cin",     re.compile(CIN_MA_REGEX)),
    ("iban",    re.compile(r"\bMA\d{2}[\s\d]{20,}\b")),
    ("url",     re.compile(r"\b(?:https?://|www\.)\S+")),
]


def redact(text: str) -> str:
    """Replace every detected PII pattern with '<REDACTED:kind>'."""
    for kind, pattern in _PATTERNS:
        text = pattern.sub(f"<REDACTED:{kind}>", text)
    return text


def sha256_hex(text: str) -> str:
    """Stable hash for input/output fields. Never log the input itself."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()