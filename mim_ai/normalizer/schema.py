"""
Config schema for the normalizer.

Validated at construction so developers get a clear error instead of
a silent no-op. Uses stdlib dataclasses to keep the core dependency-free
— swap for pydantic if you want coercion from YAML/JSON dicts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CleaningConfig:
    """Layer 1 toggles."""
    preserve_urls: bool = True
    strip_tatweel: bool = True
    strip_urls: bool = False

    def __post_init__(self) -> None:
        if self.strip_urls:
            self.preserve_urls = False


@dataclass
class RulesConfig:
    """Layer 2 toggles and dictionary paths."""
    unify_alef: bool = False
    unify_ya: bool = True
    unify_ta_marbuta: bool = False
    remove_diacritics: bool = True  # ⚠️  see arabic_rules.unify_ta_marbuta
    normalize_digits: bool = True

    # Developer-supplied overrides (paths to YAML). Both optional.
    arabizi_dict_path: str | None = None
    skip_words_path: str | None = None


@dataclass
class NormalizerConfig:
    """Top-level normalizer config, nested into mim_ai.config."""
    enabled: bool = True
    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "NormalizerConfig":
        cfg = cls()
        raw = data or {}

        if "enabled" in raw:
            cfg.enabled = bool(raw["enabled"])

        cleaning_cfg = raw.get("cleaning") if isinstance(raw.get("cleaning"), dict) else {}
        if cleaning_cfg:
            for key, value in cleaning_cfg.items():
                if hasattr(cfg.cleaning, key):
                    setattr(cfg.cleaning, key, value)

        if "strip_urls" in raw and "preserve_urls" not in raw:
            cfg.cleaning.strip_urls = bool(raw["strip_urls"])
            cfg.cleaning.preserve_urls = not cfg.cleaning.strip_urls

        if "preserve_urls" in raw:
            cfg.cleaning.preserve_urls = bool(raw["preserve_urls"])
            cfg.cleaning.strip_urls = not cfg.cleaning.preserve_urls

        if "strip_tatweel" in raw:
            cfg.cleaning.strip_tatweel = bool(raw["strip_tatweel"])

        rules_cfg = raw.get("rules") if isinstance(raw.get("rules"), dict) else {}
        if rules_cfg:
            for key, value in rules_cfg.items():
                if hasattr(cfg.rules, key):
                    setattr(cfg.rules, key, value)

        for key in (
            "unify_alef",
            "unify_ya",
            "unify_ta_marbuta",
            "remove_diacritics",
            "normalize_digits",
            "arabizi_dict_path",
            "skip_words_path",
        ):
            if key in raw:
                setattr(cfg.rules, key, raw[key])

        return cfg
