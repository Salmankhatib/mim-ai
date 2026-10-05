"""
Arabizi dictionary handling for Layer 2.

Arabizi has no standard orthography, so we treat it as a whole-word
dictionary problem, not a character transliteration problem. This
module loads, merges, and queries the Arabizi dictionary.

Lookup strategy for a Latin-script token:
    1. Normalize key: lowercase, collapse repeated chars, strip
       trailing decorative digits (e.g. "bghit123" -> "bghit").
    2. If in skip-words  -> return None (leave untouched; fr/en).
    3. If in dictionary  -> return canonical Arabic form.
    4. Otherwise         -> return None AND signal OOV to caller.
"""
from __future__ import annotations

from pathlib import Path

from .schema import RulesConfig


class ArabiziDictionary:
    """Whole-word Arabizi -> Arabic-script lookup."""

    def __init__(self) -> None:
        self._table: dict[str, str] = {}
        self._skip: set[str] = set()

    @classmethod
    def from_config(cls, config: RulesConfig) -> "ArabiziDictionary":
        """
        TODO:
            - load package base data via importlib.resources
              (data/arabizi_darija.yaml, data/skip_words.yaml)
            - if config.arabizi_dict_path: merge user overrides on top
            - if config.skip_words_path: merge user skip-words
        """
        raise NotImplementedError

    def lookup(self, token: str) -> str | None:
        """
        Return canonical Arabic form if the token resolves.
        Return None if the token is OOV OR explicitly skipped.
        Callers distinguish the two via `is_skipped()`.
        """
        raise NotImplementedError

    def is_skipped(self, token: str) -> bool:
        """True if the token is on the fr/en whitelist."""
        raise NotImplementedError

    @staticmethod
    def normalize_key(token: str) -> str:
        """
        Canonicalize a Latin token before lookup.
        TODO: lowercase, collapse repeats, strip trailing digits.
        """
        raise NotImplementedError