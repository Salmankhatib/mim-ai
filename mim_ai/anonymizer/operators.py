from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from presidio_anonymizer import OperatorConfig

from .config import AnonymizerConfig


def _operator_for(name: str, *, default_value: str, params: dict[str, Any] | None = None) -> OperatorConfig:
    op_name = str(name or "replace").strip().lower()
    params = dict(params or {})

    if op_name == "mask":
        return OperatorConfig(
            "mask",
            {
                "chars_to_mask": params.get("chars_to_mask", 4),
                "masking_char": params.get("masking_char", "*"),
                "from_end": params.get("from_end", False),
            },
        )
    if op_name == "redact":
        return OperatorConfig("redact", {})
    if op_name == "hash":
        return OperatorConfig("hash", {})
    if op_name == "encrypt":
        key = params.get("key")
        key_env = params.get("key_env")
        if key is not None and key_env is not None:
            raise ValueError("Configure only one of anonymizer encrypt key or key_env")
        if key_env is not None:
            if not isinstance(key_env, str) or not key_env.strip():
                raise ValueError("anonymizer encrypt key_env must be a non-empty environment variable name")
            key = os.environ.get(key_env)
            if key is None:
                raise ValueError(f"Anonymizer encryption key is missing; set environment variable {key_env!r}")
        if isinstance(key, str):
            key_bytes = key.encode("utf-8")
        elif isinstance(key, bytes):
            key_bytes = key
        else:
            raise ValueError(
                "The encrypt operator requires params.key or params.key_env with a 16, 24, or 32-byte key"
            )
        if len(key_bytes) not in {16, 24, 32}:
            raise ValueError("Anonymizer encryption key must be 16, 24, or 32 bytes long")
        return OperatorConfig("encrypt", {"key": key_bytes})
    if op_name == "keep":
        return OperatorConfig("keep", {})

    if op_name == "replace":
        return OperatorConfig("replace", {"new_value": params.get("new_value", default_value)})
    raise ValueError(f"Unsupported anonymizer operator: {name!r}")


def build_operators(config: AnonymizerConfig) -> dict[str, OperatorConfig]:
    """Build the operator map keyed by entity name."""
    operators: dict[str, OperatorConfig] = {}

    for entity_name, operator_spec in (getattr(config, "default_operators", {}) or {}).items():
        fallback = "[REDACTED]" if str(entity_name).upper() == "DEFAULT" else f"[{entity_name}]"
        if isinstance(operator_spec, Mapping):
            operator_name = operator_spec.get("name", operator_spec.get("operator", "replace"))
            params = operator_spec.get("params")
            if not isinstance(params, Mapping):
                params = {}
            else:
                params = dict(params)
        else:
            operator_name = operator_spec
            params = {}
        operators[str(entity_name)] = _operator_for(
            str(operator_name), default_value=fallback, params=params
        )

    for pattern in getattr(config, "custom_patterns", []) or []:
        if not isinstance(pattern, dict):
            raise TypeError("Each custom anonymizer pattern must be a mapping")
        entity_name = str(pattern.get("name") or pattern.get("entity") or "CUSTOM")
        operator_name = str(pattern.get("operator", "replace"))
        raw_params = pattern.get("params")
        params = dict(raw_params) if isinstance(raw_params, Mapping) else {}
        default_value = str(pattern.get("new_value") or f"[{entity_name}]")
        operators[entity_name] = _operator_for(operator_name, default_value=default_value, params=params)

    return operators


__all__ = ["build_operators"]
