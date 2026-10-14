__all__ = [
    "AnonymizationResult",
    "anonymize",
    "AnonymizerConfig",
    "load_config",
]


def __getattr__(name: str):
    if name in {"AnonymizationResult", "anonymize"}:
        from .anonymizer import AnonymizationResult, anonymize
        return {"AnonymizationResult": AnonymizationResult, "anonymize": anonymize}[name]
    if name in {"AnonymizerConfig", "load_config"}:
        from .config import AnonymizerConfig, load_config
        return {"AnonymizerConfig": AnonymizerConfig, "load_config": load_config}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
