"""Audit and normalizer logging for mim_ai."""

__all__ = [
    "AuditConfig", "NormalizerLogConfig",
    "AuditLogger", "NormalizerLogger",
    "redact", "sha256_hex",
    "verify_chain",
]


def __getattr__(name: str):
    if name in {"AuditConfig", "NormalizerLogConfig"}:
        from .config import AuditConfig, NormalizerLogConfig
        return {"AuditConfig": AuditConfig, "NormalizerLogConfig": NormalizerLogConfig}[name]
    if name in {"AuditLogger", "NormalizerLogger"}:
        from .audit_logger import AuditLogger
        from .normalizer_logger import NormalizerLogger
        return {"AuditLogger": AuditLogger, "NormalizerLogger": NormalizerLogger}[name]
    if name in {"redact", "sha256_hex"}:
        from .redaction import redact, sha256_hex
        return {"redact": redact, "sha256_hex": sha256_hex}[name]
    if name == "verify_chain":
        from .verify import verify_chain
        return verify_chain
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")