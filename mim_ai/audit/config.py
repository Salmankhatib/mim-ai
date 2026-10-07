"""
Configuration for the two loggers.

Two switches, both default True:
    AuditConfig.enabled            — law 09-08 + ISO 42001 trail
    NormalizerLogConfig.enabled    — dev feedback loop

Both loggers are no-ops when their switch is False. No file I/O,
no hashing, no DB connection, no overhead.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AuditConfig:
    """
    Audit log config.

    Compliance notes:
        * `hash_chain=True` gives ISO 42001 tamper-evidence: each
          line embeds the SHA-256 of the previous line. Verify with
          `mim_ai.audit.verify.verify_chain()`.
        * `retention_days` gives law 09-08 storage limitation. The
          logger purges files/rows older than this automatically.
        * User text is NEVER stored raw. Only its SHA-256 hash.
        * `user_ref` must already be a pseudonym (e.g. "u_a1b2c3"),
          never the raw ID, phone, email, or CIN.
    """
    enabled:         bool = True
    backend:         str  = "sqlite"          # "sqlite" | "jsonl"
    db_path:         str  = "./audit/audit.db"
    jsonl_path:      str  = "./audit/jsonl/"  # used only when backend="jsonl"
    retention_days:  int  = 90
    hash_chain:      bool = True
    app_version:     str  = "mim-ai 0.1.0"
    purge_on_start:  bool = True              # run retention purge at startup


@dataclass
class NormalizerLogConfig:
    """
    Normalizer feedback-loop log config.

    ⚠️  This log CAN contain user tokens (jargon samples). It is a
    developer tool, not a compliance trail. It defaults to a SHORT
    retention (7 days) and includes sampling controls so you can
    keep PII exposure bounded.

    Set `capture_skipped_tokens=False` to log only COUNTS of OOV
    tokens, not the tokens themselves. Do this in production if
    your users' text is sensitive.
    """
    enabled:                 bool  = True
    backend:                 str   = "sqlite"          # "sqlite" | "jsonl"
    db_path:                 str   = "./logs/normalizer.db"
    jsonl_path:              str   = "./logs/normalizer/"
    retention_days:          int   = 7

    # --- What to capture ---
    capture_jargon_used:     bool  = True   # custom dict keys that matched
    capture_jargon_skipped:  bool  = True   # OOV Latin tokens (PII risk!)
    capture_skipped_tokens:  bool  = True   # False -> counts only, no tokens
    max_tokens_per_event:    int   = 50     # hard cap per event

    # --- Sampling (reduce volume on high-traffic deployments) ---
    sample_rate:             float = 1.0    # 1.0 = every event, 0.1 = 1 in 10

    purge_on_start:          bool  = True