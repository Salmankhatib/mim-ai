"""
Arabizi dictionary handling for Layer 2.

Arabizi has no standard orthography, so we treat it as a whole-word
dictionary problem, not a character transliteration problem. This
module loads, merges, and queries the Arabizi dictionary.
"""
from __future__ import annotations

import re
from pathlib import Path

from .dictionary import load_yaml, merge_dicts
from .schema import RulesConfig


class ArabiziDictionary:
    """Whole-word Arabizi -> Arabic-script lookup."""

    def __init__(self) -> None:
        self._table: dict[str, str] = {}
        self._skip: set[str] = set()

    @classmethod
    def from_config(cls, config: RulesConfig) -> "ArabiziDictionary":
        base_dir = Path(__file__).resolve().parent
        base_dict_path = base_dir / "data" / "arabizi_darija.yaml"
        base_skip_path = base_dir / "data" / "skip_words.yaml"

        base_data = load_yaml(base_dict_path)
        skip_data = load_yaml(base_skip_path)

        if not isinstance(base_data, dict):
            raise TypeError(f"Base Arabizi dictionary must decode to a dict: {base_dict_path}")
        if not isinstance(skip_data, dict):
            raise TypeError(f"Base skip-words file must decode to a dict: {base_skip_path}")

        table = dict(base_data)
        skip_set = {str(k).lower() for k in skip_data.keys()} if isinstance(skip_data, dict) else set()

        if config.arabizi_dict_path:
            override = load_yaml(Path(config.arabizi_dict_path))
            if isinstance(override, dict):
                table = merge_dicts(table, override)

        if config.skip_words_path:
            custom_skip = load_yaml(Path(config.skip_words_path))
            if isinstance(custom_skip, dict):
                skip_set |= {str(k).lower() for k in custom_skip.keys()}
            elif isinstance(custom_skip, list):
                skip_set |= {str(v).lower() for v in custom_skip}

        obj = cls()
        obj._table = {obj.normalize_key(k): v for k, v in table.items()}
        obj._skip = {obj.normalize_key(k) for k in skip_set}
        return obj

    def lookup(self, token: str) -> str | None:
        """Return canonical Arabic form if the token resolves."""
        key = self.normalize_key(token)
        if not key:
            return None
        if self.is_skipped(key):
            return None
        return self._table.get(key)

    def is_skipped(self, token: str) -> bool:
        """True if the token is on the fr/en whitelist."""
        return self.normalize_key(token) in self._skip

    @staticmethod
    def normalize_key(token: str) -> str:
        """Canonicalize a Latin token before lookup."""
        if not token:
            return ""
        value = token.strip().lower()
        value = value.replace("’", "'")
        value = re.sub(r"\d+$", "", value)
        value = re.sub(r"(.)\1{2,}", r"\1\1", value)
        value = re.sub(r"[^a-z]", "", value)
        return value
