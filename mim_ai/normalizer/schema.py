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
    strip_mentions: bool = False
    strip_hashtags: bool = False
    strip_urls: bool = False

    def __post_init__(self) -> None:
        if self.strip_urls:
            self.preserve_urls = False
        else:
            self.preserve_urls = True


@dataclass
class RulesConfig:
    """Layer 2 toggles and dictionary paths."""
    unify_alef: bool = True
    unify_ya: bool = True
    unify_ta_marbuta: bool = False
    remove_diacritics: bool = True  # ⚠️  see arabic_rules.unify_ta_marbuta
    normalize_digits: bool = True

    # Developer-supplied overrides (paths to YAML). Both optional.
    arabizi_dict_path: str | None = None
    skip_words_path: str | None = None
    arabic_rules_path: str | None = None


@dataclass
class LLMConfig:
    """Layer 3 — optional. Off by default."""
    enabled: bool = False
    trigger: str = "on_oov"                       # always | on_oov | on_mixed
    model: str = "mntra/mistral-darija"
    endpoint: str | None = None
    api_key_env: str = "MNTRA_API_KEY"
    timeout_ms: int = 800
    max_tokens: int = 256
    fallback_on_timeout: bool = True


@dataclass
class NormalizerConfig:
    """Top-level normalizer config, nested into mim_ai.config."""
    enabled: bool = True
    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

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

        for key in ("strip_tatweel", "strip_mentions", "strip_hashtags"):
            if key in raw:
                setattr(cfg.cleaning, key, bool(raw[key]))

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
            "arabic_rules_path",
        ):
            if key in raw:
                setattr(cfg.rules, key, raw[key])

        llm_cfg = raw.get("llm") if isinstance(raw.get("llm"), dict) else {}
        if llm_cfg:
            for key, value in llm_cfg.items():
                if hasattr(cfg.llm, key):
                    setattr(cfg.llm, key, value)

        # Only the nested llm block may toggle the optional LLM layer.
        # A top-level `enabled` flag controls the normalizer itself.
        for key in ("trigger", "model", "endpoint", "api_key_env", "timeout_ms", "max_tokens", "fallback_on_timeout"):
            if key in raw and not llm_cfg:
                setattr(cfg.llm, key, raw[key])

        return cfg
