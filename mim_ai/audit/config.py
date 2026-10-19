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
from typing import Any


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

    `backend` is intentionally storage-agnostic. Values like
    `postgresql`, `mysql`, `mongodb`, and `cassandra` are accepted as
    long as an `adapter` factory is provided. That lets the app plug in
    its own connection layer without changing the logger API.
    """
    enabled:         bool = True
    backend:         str  = "sqlite"          # sqlite | jsonl | postgresql | mysql | mongodb | cassandra | ...
    db_path:         str  = "./audit/audit.db"
    jsonl_path:      str  = "./audit/jsonl/"  # used only when backend="jsonl"
    database_url:    str | None = None
    collection:      str = "audit_events"
    adapter:         Any | None = None
    retention_days:  int = 90
    hash_chain:      bool = True
    app_version:     str  = "mim-ai 0.1.0"
    purge_on_start:  bool = True              # run retention purge at startup

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "AuditConfig":
        raw = dict(data or {})
        known = {
            "enabled", "backend", "db_path", "jsonl_path", "database_url",
            "collection", "adapter", "retention_days", "hash_chain",
            "app_version", "purge_on_start",
        }
        return cls(**{key: value for key, value in raw.items() if key in known})


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

    `adapter` can be a factory or instance implementing the same
    `append(row)` / `purge_older_than(days)` contract as the SQLite and
    JSONL backends. This keeps the logger usable with PostgreSQL,
    MySQL, MongoDB, Cassandra, or any internal application DB.
    """
    enabled:                 bool  = True
    backend:                 str   = "sqlite"          # sqlite | jsonl | postgresql | mysql | mongodb | cassandra | ...
    db_path:                 str   = "./logs/normalizer.db"
    jsonl_path:              str   = "./logs/normalizer/"
    database_url:            str | None = None
    collection:              str   = "normalizer_events"
    adapter:                 Any | None = None
    retention_days:          int   = 7

    # --- What to capture ---
    capture_jargon_used:     bool  = True   # custom dict keys that matched
    capture_jargon_skipped:  bool  = True   # OOV Latin tokens (PII risk!)
    capture_skipped_tokens:  bool  = False  # True -> store raw OOV tokens
    max_tokens_per_event:    int   = 50     # hard cap per event

    # --- Sampling (reduce volume on high-traffic deployments) ---
    sample_rate:             float = 1.0    # 1.0 = every event, 0.1 = 1 in 10

    purge_on_start:          bool  = True

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "NormalizerLogConfig":
        raw = dict(data or {})
        known = {
            "enabled", "backend", "db_path", "jsonl_path", "database_url",
            "collection", "adapter", "retention_days", "capture_jargon_used",
            "capture_jargon_skipped", "capture_skipped_tokens", "max_tokens_per_event",
            "sample_rate", "purge_on_start",
        }
        return cls(**{key: value for key, value in raw.items() if key in known})