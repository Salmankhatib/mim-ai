"""
Audit logger — law 09-08 + ISO 42001 compliant.

Guarantees:
    * Never stores user text. Only SHA-256 hashes.
    * Append-only. Never rewrites a line.
    * Hash-chained when config.hash_chain is True (ISO 42001 §A.7.4).
    * Auto-purges events older than config.retention_days
      (law 09-08 storage limitation).
    * `find_by_user()` supports law 09-08 rights of access & erasure.

When config.enabled is False, every method returns immediately.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .backends import SQLiteBackend, create_backend
from .config import AuditConfig


class AuditLogger:
    def __init__(self, config: AuditConfig) -> None:
        self.config = config
        self.enabled = config.enabled
        self._last_hash: str | None = None

        if not self.enabled:
            return

        self._backend = create_backend(config, getattr(config, "collection", "audit_events"))

        if config.purge_on_start:
            self._backend.purge_older_than(config.retention_days)

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def emit(
        self,
        *,
        event: str,
        trace_id: str,
        user_ref: str | None = None,
        input_text: str | None = None,
        output_text: str | None = None,
        duration_ms: int | None = None,
        status: str = "ok",
        config_hash: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """
        Write one audit event.

        `input_text` / `output_text` are hashed here — the raw strings
        are NEVER written to the log. Pass them as kwargs for
        convenience; the logger takes care of the rest.
        """
        if not self.enabled:
            return

        row = {
            "ts":           datetime.now(timezone.utc).isoformat(),
            "trace_id":     trace_id,
            "event":        event,
            "user_ref":     user_ref,
            "app_version":  self.config.app_version,
            "config_hash":  config_hash,
            "input_hash":   _hash(input_text),
            "output_hash":  _hash(output_text),
            "duration_ms":  duration_ms,
            "status":       status,
            "payload":      json.dumps(extra or {}, ensure_ascii=False),
        }

        # --- ISO 42001 tamper-evidence ---
        if self.config.hash_chain:
            row["prev_hash"] = self._last_hash
            row["line_hash"] = _line_hash(row)
            self._last_hash = row["line_hash"]
        else:
            row["prev_hash"] = None
            row["line_hash"] = _line_hash(row)

        self._backend.append(row)

    # -----------------------------------------------------------------
    # Law 09-08 helpers — rights of access and erasure
    # -----------------------------------------------------------------
    def find_by_user(self, user_ref: str) -> list[dict]:
        """
        Return all audit rows for a user. Satisfies the law 09-08
        right of access and the retention/erasure workflows.

        Only works with the SQLite backend. For JSONL, read the
        files yourself or use the CLI tool.
        """
        if not self.enabled:
            return []
        if not isinstance(self._backend, SQLiteBackend):
            raise NotImplementedError(
                "find_by_user() requires backend='sqlite'"
            )
        cur = self._backend.conn.execute(
            "SELECT * FROM audit_events WHERE user_ref = ? ORDER BY seq",
            (user_ref,),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def delete_by_user(self, user_ref: str) -> int:
        """
        Delete all audit rows for a user. Satisfies law 09-08 right
        to erasure. Returns rows deleted.

        ⚠️  Breaks the hash chain. Log a `deletion` event immediately
        after so the gap is explained.
        """
        if not self.enabled:
            return 0
        if not isinstance(self._backend, SQLiteBackend):
            raise NotImplementedError(
                "delete_by_user() requires backend='sqlite'"
            )
        cur = self._backend.conn.execute(
            "DELETE FROM audit_events WHERE user_ref = ?", (user_ref,)
        )
        n = cur.rowcount
        self.emit(
            event="deletion",
            trace_id="system",
            user_ref=user_ref,
            extra={"deleted_rows": n, "reason": "user_erasure_request"},
        )
        return n

    def purge_expired(self) -> int:
        """Run retention purge on demand. Also runs at startup."""
        if not self.enabled:
            return 0
        return self._backend.purge_older_than(self.config.retention_days)


# ---------------------------------------------------------------------------
def _hash(text: str | None) -> str | None:
    if text is None:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _line_hash(row: dict) -> str:
    """Hash the row's canonical form, ignoring line_hash itself."""
    body = {k: v for k, v in row.items() if k != "line_hash"}
    payload = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()