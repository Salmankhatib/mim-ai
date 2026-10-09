"""
mim_ai.normalizer.darija_rules
==============================

Token-level Darija normalization. This is the actual "brain" of
Layer 2 — it decides, for each token in the input, which sub-rule
to apply.

Position in the pipeline
------------------------
    Layer 1 (layers/cleaning.py)
        ↓  cleaned text, URLs replaced with <URL_N> placeholders
    Layer 2 (THIS FILE, via layers/rules.py)
        ↓  normalized text, OOV flag emitted
    Layer 3 (layers/llm.py)   — optional
        ↓  LLM-normalized text
    Normalizer.normalize() restores URLs and returns.

This module contains NO character-level tables (they live in
`arabic_rules.py`) and NO pipeline plumbing (it lives in
`layers/rules.py`). It is pure: text + config -> text + report.

Design — the per-token dispatch
-------------------------------
For every whitespace-delimited token we compute its script and
route it through exactly one branch:

    script == "arabic"
        -> arabic_rules.apply_arabic_rules(token, **config_flags)
        Emits rule_applications += 1 if the token changed.

    script == "latin"
        -> 1. arabizi.is_skipped(token)?  -> leave untouched
           2. arabizi.lookup(core)?      -> replace with canonical
           3. otherwise                  -> leave untouched, flag OOV

    script == "mixed"   (Arabic + Latin in one token)
        -> leave untouched, flag mixed_script
           (splitting substrings inside a token is heuristic and
            mis-fires on emoji sequences and digit-suffixed Arabizi)

    script == "other"   (digits, punctuation, emoji, symbols)
        -> leave untouched

The `oov_arabizi` flag is the hand-off to Layer 3: it means "there
was Latin-script text I could not resolve as either French/English
or known Arabizi." The LLM layer uses this as its default trigger.

Report contract
---------------
`normalize_text()` returns `(text, delta)` where `delta` is a plain
dict with keys:
    dictionary_hits     int
    rule_applications   int
    oov_arabizi         bool
    mixed_script        bool

These are merged into the pipeline-wide `NormalizationReport` by
`layers/rules.py`. This file never touches the report object itself.

Usage
-----
    from mim_ai.normalizer.darija_rules import normalize_text
    from mim_ai.normalizer.schema import RulesConfig

    cfg = RulesConfig()
    clean, delta = normalize_text("salam, bghit n3ref wa7ed", cfg)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .layers.arabic_rules import apply_arabic_rules
from .arabizi import ArabiziDictionary
from .schema import RulesConfig
from ..utils.unicode_helpers import script_of


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------
# We split on whitespace boundaries but KEEP the whitespace tokens so
# we can rebuild the string byte-for-byte. `\s+` matches any Unicode
# whitespace, which is what Layer 1 has already collapsed to plain
# spaces — but we stay tolerant in case Layer 1 was disabled.
_SPLIT_WS_RE = re.compile(r"(\s+)")


# ---------------------------------------------------------------------------
# Punctuation peeling (for Arabizi dictionary lookup only)
# ---------------------------------------------------------------------------
# Arabizi writers glue punctuation to words: "bghit," "salam!" "wa7ed?"
# The dictionary stores clean keys, so we strip surrounding punctuation
# before lookup and reattach it after. Only ASCII + common Arabic
# punctuation is peeled — we never peel Arabic letters, digits, or emoji.
#
# Note: this list is intentionally conservative. Adding characters here
# affects the Arabizi lookup behavior for every caller.
_PUNCT_CHARS = frozenset(
    ".,!?;:\"'`()[]{}<>«»…،؛؟"      # ASCII + Arabic punctuation
    "\u2018\u2019\u201c\u201d"        # curly quotes
    "-–—"                             # hyphens / dashes
)


# ---------------------------------------------------------------------------
# Internal report accumulator
# ---------------------------------------------------------------------------
@dataclass
class _Report:
    """Internal-only accumulator for Layer 2."""
    dictionary_hits: int = 0
    rule_applications: int = 0
    oov_arabizi: bool = False
    mixed_script: bool = False
    jargon_used: dict[str, int] = field(default_factory=dict)
    jargon_skipped: dict[str, int] = field(default_factory=dict)

    def to_delta(self) -> dict:
        """Convert to the plain-dict form expected by the pipeline."""
        return {
            "dictionary_hits":   self.dictionary_hits,
            "rule_applications": self.rule_applications,
            "oov_arabizi":       self.oov_arabizi,
            "mixed_script":      self.mixed_script,
            "jargon_used":       dict(self.jargon_used),
            "jargon_skipped":    dict(self.jargon_skipped),
        }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def normalize_text(
    text: str,
    config: RulesConfig,
    arabizi: ArabiziDictionary | None = None,
) -> tuple[str, dict]:
    """
    Normalize a full string of Darija text.

    Parameters
    ----------
    text : str
        Output of Layer 1 (already cleaned, URLs already protected
        behind <URL_N> placeholders — the placeholders are pure ASCII
        and pass through this layer untouched).

    config : RulesConfig
        Layer 2 toggles: unify_alef, unify_ya, unify_ta_marbuta,
        remove_diacritics, normalize_digits, plus dictionary paths.

    arabizi : ArabiziDictionary, optional
        Pre-loaded dictionary. If None, one is built from `config`.
        Pass one in when calling in a hot loop (e.g. a server request
        handler) to avoid rebuilding on every call.

    Returns
    -------
    (normalized_text, report_delta)
        `report_delta` is the plain dict described in the module
        docstring.
    """
    # Defensive: allow None / empty without raising.
    if not text:
        return text or "", _Report().to_delta()

    if arabizi is None:
        arabizi = ArabiziDictionary.from_config(config)

    report = _Report()

    # Split on whitespace while keeping the whitespace tokens, so we
    # can rejoin losslessly.
    parts = _SPLIT_WS_RE.split(text)
    out_parts: list[str] = []

    for part in parts:
        # Whitespace chunks and empty strings pass through verbatim.
        if not part or part.isspace():
            out_parts.append(part)
            continue

        normalized = _normalize_token(part, config, arabizi, report)
        out_parts.append(normalized)

    return "".join(out_parts), report.to_delta()


# ---------------------------------------------------------------------------
# Per-token dispatch
# ---------------------------------------------------------------------------
def _normalize_token(
    token: str,
    config: RulesConfig,
    arabizi: ArabiziDictionary,
    report: _Report,
) -> str:
    """
    Normalize a single whitespace-free token.

    The four branches are ordered from most common to least common
    (Arabic, Latin, mixed, other) — though in practice the script
    check is O(len(token)) regardless, so ordering is about
    readability, not performance.
    """
    script = script_of(token)

    # ---- Arabic script -----------------------------------------------------
    if script == "arabic":
        before = token
        token = apply_arabic_rules(
            token,
            unify_alef_=config.unify_alef,
            unify_ya_=config.unify_ya,
            unify_ta_marbuta_=config.unify_ta_marbuta,
            remove_diacritics=config.remove_diacritics,
            normalize_digits=config.normalize_digits,
        )
        if token != before:
            report.rule_applications += 1
        return token

    # ---- Latin script ------------------------------------------------------
    if script == "latin":
        # Skip-word check runs on the RAW token (before punctuation
        # peel) because the skip list is a whole-token whitelist. A
        # trailing comma should not change the skip decision.
        if arabizi.is_skipped(token):
            return token

        # Peel punctuation, look up the core, reattach.
        core, prefix, suffix = _split_punct(token)

        # If the core is empty (token was all punctuation), nothing
        # to do — return the original.
        if not core:
            return token

        # Skip-word check on the peeled core too, in case the caller
        # populated skip_words with entries that include punctuation.
        if arabizi.is_skipped(core):
            return token

        canonical = arabizi.lookup(core)

        if canonical is not None:
            report.dictionary_hits += 1
            report.jargon_used[core] = report.jargon_used.get(core, 0) + 1
            return f"{prefix}{canonical}{suffix}"

        # OOV: a Latin token that is neither a skip-word nor a known
        # Arabizi form. It might be French, English, a typo, or
        # genuinely ambiguous Arabizi. We leave it alone and flag it
        # so Layer 3 knows there is unresolved Latin-script content.
        report.oov_arabizi = True
        report.jargon_skipped[core] = report.jargon_skipped.get(core, 0) + 1
        return token

    # ---- Mixed script (Arabic + Latin in one token) ------------------------
    if script == "mixed":
        # We do NOT try to split "bghitع" into "bghit" + "ع". Substring
        # boundaries inside a token are heuristic and mis-fire on:
        #   * emoji sequences (👨‍👩‍👧)
        #   * Arabizi with digits ("bghit3")
        #   * technical strings ("iPhone13", "COVID-19a")
        # Leaving mixed tokens untouched is the conservative choice
        # and keeps the normalizer idempotent.
        report.mixed_script = True
        return token

    # ---- Other (digits, punctuation, emoji, symbols) -----------------------
    # Nothing to normalize. Digits stay digits. Punctuation stays.
    # Emoji stay. This branch is reached for "42", "...", "😊", "→".
    return token


# ---------------------------------------------------------------------------
# Punctuation peeling helper
# ---------------------------------------------------------------------------
def _split_punct(token: str) -> tuple[str, str, str]:
    """
    Peel leading and trailing punctuation off a token.

    Returns (core, prefix, suffix) such that:
        prefix + core + suffix == token

    Punctuation is identified by membership in `_PUNCT_CHARS`, which
    contains ASCII and Arabic punctuation plus curly quotes and dashes.

    Examples
    --------
        "bghit,"   -> ("bghit", "", ",")
        "\"salam\"" -> ("salam", "\"", "\"")
        "...salam!" -> ("salam", "...", "!")
        "bghit"    -> ("bghit", "", "")
        "..."      -> ("", "...", "")   # empty core — caller must guard
    """
    i, j = 0, len(token)
    while i < j and token[i] in _PUNCT_CHARS:
        i += 1
    while j > i and token[j - 1] in _PUNCT_CHARS:
        j -= 1
    return token[i:j], token[:i], token[j:]


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------
__all__ = ["normalize_text"]