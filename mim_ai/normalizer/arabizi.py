"""
Arabizi dictionary handling for Layer 2.

Arabizi has no standard orthography, so we treat it as a whole-word
dictionary problem, not a character transliteration problem. Variants
are canonicalized within their original script and never translated.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .dictionary import load_yaml, merge_dicts
from .schema import RulesConfig
from ..utils.unicode_helpers import script_of


class ArabiziDictionary:
    """Whole-word canonicalization that preserves the input script."""

    def __init__(self) -> None:
        self._table: dict[str, str] = {}
        self._skip: set[str] = set()

    @classmethod
    def from_config(cls, config: RulesConfig) -> "ArabiziDictionary":
        base_dir = Path(__file__).resolve().parent
        variant_dict_path = base_dir / "data" / "darija_variants.yaml"
        base_skip_path = base_dir / "data" / "skip_words.yaml"

        variant_data = load_yaml(variant_dict_path)
        skip_data = load_yaml(base_skip_path)

        if not isinstance(skip_data, dict):
            raise TypeError(f"Base skip-words file must decode to a dict: {base_skip_path}")

        table = cls._variant_table_from_data(variant_data)
        skip_set = {str(k).lower() for k in skip_data.keys()} if isinstance(skip_data, dict) else set()

        if config.arabizi_dict_path:
            override_path = Path(config.arabizi_dict_path)
            override = load_yaml(override_path)
            if not isinstance(override, dict):
                raise TypeError(f"Arabizi dictionary must be a mapping: {override_path}")
            table = merge_dicts(table, override)

        if config.skip_words_path:
            skip_path = Path(config.skip_words_path)
            custom_skip = load_yaml(skip_path)
            if isinstance(custom_skip, dict):
                skip_set |= {str(k).lower() for k in custom_skip}
            elif isinstance(custom_skip, list):
                skip_set |= {str(v).lower() for v in custom_skip}
            else:
                raise TypeError(f"Skip-words file must be a mapping or list: {skip_path}")

        obj = cls()
        obj._table = {obj.normalize_key(k): str(v) for k, v in table.items()}
        obj._skip = {obj.normalize_key(k) for k in skip_set}
        return obj

    @staticmethod
    def _variant_table_from_data(data: dict | list) -> dict[str, str]:
        entries: list[dict] = []
        if isinstance(data, list):
            entries = [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            if isinstance(data.get("entries"), list):
                entries = [item for item in data["entries"] if isinstance(item, dict)]
            elif "entries" not in data:
                entries = [data]

        table: dict[str, str] = {}
        for entry in entries:
            canonical_arabizi = entry.get("canonical_arabizi")
            canonical_arabic = entry.get("canonical_arabic")
            variants = entry.get("variants") if isinstance(entry.get("variants"), dict) else {}

            if canonical_arabizi is not None:
                table[str(canonical_arabizi)] = str(canonical_arabizi)
            if canonical_arabic is not None:
                table[str(canonical_arabic)] = str(canonical_arabic)

            for script, variant_group in variants.items():
                if script == "arabizi":
                    canonical = canonical_arabizi
                elif script == "arabic":
                    canonical = canonical_arabic
                else:
                    continue
                if canonical is None:
                    continue
                if isinstance(variant_group, list):
                    for variant in variant_group:
                        if variant is None:
                            continue
                        table[str(variant)] = str(canonical)
                elif variant_group is not None:
                    table[str(variant_group)] = str(canonical)

        return {ArabiziDictionary.normalize_key(k): str(v) for k, v in table.items() if k}

    def lookup(self, token: str) -> str | None:
        """Return the same-script canonical form if the token resolves."""
        key = self.normalize_key(token)
        if not key:
            return None
        if self.is_skipped(token):
            return None
        canonical = self._table.get(key)
        if canonical is not None and script_of(token) != script_of(canonical):
            return None
        return canonical

    def is_skipped(self, token: str) -> bool:
        """Return whether the token should be excluded from dictionary lookup."""
        if re.match(r"^\d", str(token).strip()):
            return False
        return self.normalize_key(token) in self._skip

    @staticmethod
    def normalize_key(token: str) -> str:
        """Canonicalize a token before dictionary lookup."""
        if not token:
            return ""

        value = unicodedata.normalize("NFKC", str(token)).strip()
        value = value.replace("’", "'")
        value = value.replace("‛", "'")
        value = value.replace("\u0640", "")
        value = re.sub(r"[\u200c\u200d\u200b\s]+", "", value)

        if any((0x0600 <= ord(ch) <= 0x06FF) or (0x0750 <= ord(ch) <= 0x077F) for ch in value):
            value = re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]", "", value)
            return value

        value = value.lower()
        value = re.sub(r"\d+$", "", value)
        value = re.sub(r"(.)\1{2,}", r"\1\1", value)
        value = re.sub(r"[^a-z]", "", value)
        return value
