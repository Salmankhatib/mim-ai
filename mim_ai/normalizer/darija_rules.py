"""
mim_ai.normalizer.arabic_rules
==============================

Arabic-script orthographic rules for Layer 2.

Design principles
-----------------
* Every rule here is **safe for BOTH MSA and Darija**. We never apply
  a rule that would corrupt MSA, because Layer 2 cannot tell them apart
  (and does not need to — both benefit from the same unification).

* Rules are **idempotent**. Running the normalizer twice on the same
  text must produce the same output as running it once. This matters
  because Layer 3 (LLM) may round-trip through Layer 2 again.

* Rules are **character-level substitutions or regex rewrites**, never
  contextual decisions. Contextual logic belongs in `darija_rules.py`.

* Every rule is exposed as a named function so developers can compose
  their own rule chains in `darija_rules.py` without touching this file.

What lives here
---------------
    unify_alef            أ إ آ ٱ  -> ا
    unify_ya              ى         -> ي
    unify_ta_marbuta      ة         -> ه
    remove_tashkeel       strip Arabic diacritics
    normalize_arabic_digits   ٠١٢٣ -> 0123
    strip_tatweel         remove ـ (kashida)
    strip_control_chars   remove \x00-\x1F except \n
    collapse_whitespace   runs of space -> single space

What does NOT live here
-----------------------
    * Arabizi transliteration (see `arabizi.py`)
    * Token splitting / script detection (see `layers/rules.py`)
    * Language-specific greetings / fillers (see `darija_rules.py`)
    * Any rule that depends on surrounding tokens
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable


# ---------------------------------------------------------------------------
# Character tables
# ---------------------------------------------------------------------------
# These are the DEFAULTS. Developers can override any table via
# `config.rules.arabic_rules_path` (see `dictionary.py` for the loader).

ALEF_FORMS: dict[str, str] = {
    "\u0623": "\u0627",   # أ  -> ا
    "\u0625": "\u0627",   # إ  -> ا
    "\u0622": "\u0627",   # آ  -> ا
    "\u0671": "\u0627",   # ٱ  -> ا
    "\u0672": "\u0627",   # ٲ  -> ا
    "\u0673": "\u0627",   # ٳ  -> ا
}

YA_FORMS: dict[str, str] = {
    "\u0649": "\u064A",   # ى  -> ي   (Alef Maksura -> Ya)
    "\u06CC": "\u064A",   # ی  -> ي   (Persian Yeh)
}

TA_MARBUTA_FORMS: dict[str, str] = {
    "\u0629": "\u0647",   # ة  -> ه
}

ARABIC_INDIC_DIGITS: dict[str, str] = {
    "\u0660": "0",   # ٠
    "\u0661": "1",   # ١
    "\u0662": "2",   # ٢
    "\u0663": "3",   # ٣
    "\u0664": "4",   # ٤
    "\u0665": "5",   # ٥
    "\u0666": "6",   # ٦
    "\u0667": "7",   # ٧
    "\u0668": "8",   # ٨
    "\u0669": "9",   # ٩
    "\u06F0": "0",   # ۰  (Extended Arabic-Indic, Persian)
    "\u06F1": "1",   # ۱
    "\u06F2": "2",   # ۲
    "\u06F3": "3",   # ۳
    "\u06F4": "4",   # ۴
    "\u06F5": "5",   # ۵
    "\u06F6": "6",   # ۶
    "\u06F7": "7",   # ۷
    "\u06F8": "8",   # ۸
    "\u06F9": "9",   # ۹
}


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
# Tashkeel + Quranic marks. Kept as one character class so we do a single
# pass instead of chaining multiple `.sub()` calls (measurably faster).
TASHKEEL_RE = re.compile(
    "["
    "\u0610-\u061A"   # Arabic signs (Quranic)
    "\u064B-\u065F"   # Standard tashkeel (fatha, damma, kasra, sukun…)
    "\u0670"          # Superscript Alef
    "\u06D6-\u06DC"   # Quranic annotation signs
    "\u06DF-\u06E4"
    "\u06E7\u06E8"
    "\u06EA-\u06ED"
    "]"
)

TATWEEL_RE = re.compile("\u0640+")

# Control characters EXCEPT \n (kept for paragraph structure) and \t
# (converted to space by whitespace collapse below).
CONTROL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

WHITESPACE_RE = re.compile(r"[ \t\u00A0\u2000-\u200A\u202F\u205F\u3000]+")

# Non-printable formatting marks often pasted from web pages.
ZERO_WIDTH_RE = re.compile("[\u200B-\u200F\u202A-\u202E\uFEFF]")


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------
def unify_alef(token: str) -> str:
    """
    Collapse all Alef variants to bare Alef (ا).

    Rationale: Moroccan writers use أ/إ/آ/ا interchangeably, and MSA
    readers treat them as the same letter in practice. Unifying them
    cuts vocabulary sparsity dramatically for downstream models.
    """
    return _translate(token, ALEF_FORMS)


def unify_ya(token: str) -> str:
    """
    Collapse Alef Maksura (ى) and Persian Yeh (ی) to standard Ya (ي).

    Note: we do NOT touch the final-ya vs. middle-ya distinction in
    Egyptian/Levantine orthography — that is not a Darija concern.
    """
    return _translate(token, YA_FORMS)


def unify_ta_marbuta(token: str) -> str:
    """
    Collapse Ta Marbuta (ة) to Ha (ه).

    This is config-toggleable because some downstream tasks (e.g. MSA
    parsing) prefer to keep ة intact. For Darija it is almost always
    the right normalization — Darija rarely uses ة at all.
    """
    return _translate(token, TA_MARBUTA_FORMS)


def remove_tashkeel(token: str) -> str:
    """
    Strip all Arabic diacritics (fatha, damma, kasra, sukun, shadda…).

    Darija is almost never written with diacritics; when they appear
    they are usually noise from a copy-paste out of a Quranic text or
    an MSA article. Stripping them is safe.
    """
    return TASHKEEL_RE.sub("", token)


def normalize_arabic_digits(token: str) -> str:
    """
    Convert Arabic-Indic digits (٠١٢٣…) and their Extended variants
    (۰۱۲۳…) to ASCII digits (0123…).

    Rationale: ASCII digits are what every downstream tokenizer,
    regex, and model was trained on. Arabic-Indic digits are rare
    enough in Moroccan text that unifying them costs nothing.
    """
    return _translate(token, ARABIC_INDIC_DIGITS)


def strip_tatweel(token: str) -> str:
    """
    Remove the tatweel / kashida character (ـ).

    It is purely decorative — writers insert it to stretch words for
    justification. It inflates token length without adding meaning and
    will wreck any subword tokenizer that has not seen it.
    """
    return TATWEEL_RE.sub("", token)


def strip_control_chars(token: str) -> str:
    """Remove non-printable control characters, preserving \\n."""
    return CONTROL_RE.sub("", token)


def strip_zero_width(token: str) -> str:
    """
    Remove zero-width and bidi-control characters.

    These are the #1 cause of "why doesn't my string match?" bugs when
    copy-pasting from web pages, PDFs, or WhatsApp.
    """
    return ZERO_WIDTH_RE.sub("", token)


def collapse_whitespace(token: str) -> str:
    """Collapse any run of whitespace characters to a single space."""
    return WHITESPACE_RE.sub(" ", token)


# ---------------------------------------------------------------------------
# Composite rule chains — the ones Layer 2 actually calls
# ---------------------------------------------------------------------------
def apply_arabic_rules(
    token: str,
    *,
    unify_alef_: bool = True,
    unify_ya_: bool = True,
    unify_ta_marbuta_: bool = True,
    remove_diacritics: bool = True,
    normalize_digits: bool = True,
) -> str:
    """
    Apply the standard Layer 2 rule chain to a single Arabic-script token.

    Order matters: we strip diacritics and tatweel *before* unifying
    characters, so the unifiers see clean input. This is faster and
    avoids edge cases like a shadda sitting between a Ta Marbuta and
    the following letter.

    Every step is gated by a keyword flag so callers can build custom
    chains without duplicating logic. Defaults match the "recommended
    Darija normalization" profile.
    """
    if remove_diacritics:
        token = remove_tashkeel(token)
    token = strip_tatweel(token)
    token = strip_zero_width(token)
    token = strip_control_chars(token)

    if unify_alef_:
        token = unify_alef(token)
    if unify_ya_:
        token = unify_ya(token)
    if unify_ta_marbuta_:
        token = unify_ta_marbuta(token)
    if normalize_digits:
        token = normalize_arabic_digits(token)

    return token


def apply_universal_clean(text: str) -> str:
    """
    Layer 1 entry point. Called once on the whole text before tokenizing.

    Order:
        1. Unicode NFC — must be first, so subsequent comparisons are
           byte-stable.
        2. Strip zero-width / bidi controls (they hide inside "spaces").
        3. Strip other control chars (except \\n).
        4. Collapse whitespace runs.
    """
    text = unicodedata.normalize("NFC", text)
    text = strip_zero_width(text)
    text = strip_control_chars(text)
    text = collapse_whitespace(text)
    return text.strip()


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _translate(token: str, table: dict[str, str]) -> str:
    """
    Fast per-character translation.

    `str.translate` with a pre-built table is ~3x faster than a Python
    loop for short strings and avoids allocating intermediate lists.
    We use a plain dict as input because callers may override tables.
    """
    if not any(c in table for c in token):
        return token          # fast path: nothing to do
    return token.translate(str.maketrans(table))


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------
__all__ = [
    # tables (overridable)
    "ALEF_FORMS",
    "YA_FORMS",
    "TA_MARBUTA_FORMS",
    "ARABIC_INDIC_DIGITS",
    # individual rules
    "unify_alef",
    "unify_ya",
    "unify_ta_marbuta",
    "remove_tashkeel",
    "normalize_arabic_digits",
    "strip_tatweel",
    "strip_control_chars",
    "strip_zero_width",
    "collapse_whitespace",
    # composite chains
    "apply_arabic_rules",
    "apply_universal_clean",
]