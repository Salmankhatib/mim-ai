"""Reusable English-named intent registry."""

__all__ = ["IntentConfig", "Intent", "IntentRegistry"]


def __getattr__(name: str):
    if name == "IntentConfig":
        from .config import IntentConfig
        return IntentConfig
    if name in {"Intent", "IntentRegistry"}:
        from .registry import Intent, IntentRegistry
        return {"Intent": Intent, "IntentRegistry": IntentRegistry}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")