"""
Config schema for the normalizer.

Validated at construction so developers get a clear error instead of
a silent no-op. Uses stdlib dataclasses to keep the core dependency-free
— swap for pydantic if you want coercion from YAML/JSON dicts.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import true

from mim_ai.audit.config import AuditConfig, NormalizerLogConfig


@dataclass
class CleaningConfig:
    """Layer 1 toggles."""
    strip_urls: bool = true
    strip_tatweel: bool = true
    strip_mentions: bool = False
    strip_hashtags: bool = False



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
    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)


@dataclass
class NormalizerConfig:
    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    rules:    RulesConfig    = field(default_factory=RulesConfig)
    llm:      LLMConfig      = field(default_factory=LLMConfig)
    audit:      AuditConfig         = field(default_factory=AuditConfig)
    normalizer: NormalizerLogConfig = field(default_factory=NormalizerLogConfig)