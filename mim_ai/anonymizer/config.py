from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AnonymizerConfig:
    enabled: bool = True
    default_operators: dict[str, str] = field(
        default_factory=lambda: {
            "DEFAULT": "replace",
            "CIN_MA": "replace",
            "PHONE_MA": "mask",
        }
    )
    custom_patterns: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | dict[str, Any] | None) -> "AnonymizerConfig":
        cfg = cls()
        raw = dict(data or {})

        if "enabled" in raw:
            cfg.enabled = bool(raw["enabled"])

        default_operators = raw.get("default_operators")
        if isinstance(default_operators, dict):
            cfg.default_operators = {
                str(k): str(v) for k, v in default_operators.items()
            }

        custom_patterns = raw.get("custom_patterns")
        if isinstance(custom_patterns, list):
            cfg.custom_patterns = list(custom_patterns)

        return cfg


def load_config(path_or_dict: str | Path | dict[str, Any] | None) -> AnonymizerConfig:
    """Load config from a YAML/JSON file path or from an inline dict."""
    if path_or_dict is None:
        return AnonymizerConfig()

    if isinstance(path_or_dict, dict):
        return AnonymizerConfig.from_mapping(path_or_dict)

    path = Path(path_or_dict)
    if not path.exists():
        raise FileNotFoundError(f"Anonymizer config not found: {path}")

    raw_text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".json"}:
        payload = json.loads(raw_text)
    else:
        payload = yaml.safe_load(raw_text) or {}

    if not isinstance(payload, dict):
        raise ValueError("Anonymizer config root must be a mapping/object.")

    return AnonymizerConfig.from_mapping(payload)


__all__ = ["AnonymizerConfig", "load_config"]
