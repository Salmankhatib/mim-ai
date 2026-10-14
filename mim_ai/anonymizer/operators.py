from __future__ import annotations

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
        return OperatorConfig("encrypt", {})
    if op_name == "keep":
        return OperatorConfig("keep", {})

    return OperatorConfig("replace", {"new_value": params.get("new_value", default_value)})


def build_operators(config: AnonymizerConfig) -> dict[str, OperatorConfig]:
    """Build the operator map keyed by entity name."""
    operators: dict[str, OperatorConfig] = {}

    for entity_name, operator_name in (getattr(config, "default_operators", {}) or {}).items():
        fallback = "[REDACTED]" if str(entity_name).upper() == "DEFAULT" else f"[{entity_name}]"
        operators[str(entity_name)] = _operator_for(operator_name, default_value=fallback)

    for pattern in getattr(config, "custom_patterns", []) or []:
        if not isinstance(pattern, dict):
            continue
        entity_name = str(pattern.get("name") or pattern.get("entity") or "CUSTOM")
        operator_name = str(pattern.get("operator", "replace"))
        params = pattern.get("params") if isinstance(pattern.get("params"), dict) else {}
        default_value = str(pattern.get("new_value") or f"[{entity_name}]")
        operators[entity_name] = _operator_for(operator_name, default_value=default_value, params=params)

    return operators


__all__ = ["build_operators"]
