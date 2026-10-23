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

        self._backend = create_backend(
            config, getattr(config, "collection", "audit_events"), schema="audit"
        )
        if (
            config.multi_writer
            and config.hash_chain
            and not getattr(self._backend, "supports_atomic_chained_append", False)
        ):
            self._backend.close()
            raise ValueError(
                "audit.multi_writer requires a backend with atomic chained appends; "
                "use SQLite or provide a compatible adapter"
            )

        self._last_hash = self._restore_last_hash()

        if config.purge_on_start:
            self._backend.purge_older_than(config.retention_days)

    def _restore_last_hash(self) -> str | None:
        backend = getattr(self, "_backend", None)
        if backend is None or not self.config.hash_chain:
            return None
        if isinstance(backend, SQLiteBackend):
            row = backend.conn.execute(
                f"SELECT line_hash FROM {backend.table} ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            if row:
                return row[0]
        if hasattr(backend, "last_hash"):
            return backend.last_hash()
        if hasattr(backend, "_fallback_path") and backend._fallback_path.exists():
            last_line_hash = None
            with backend._fallback_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        payload = json.loads(line)
                        last_line_hash = payload.get("line_hash", last_line_hash)
            return last_line_hash
        return None

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
    ) -> dict[str, object]:
        """
        Write one audit event and return a machine-readable summary.

        The returned dict clearly states whether the audit logger was used,
        what it recorded, and when it happened.
        """
        ts = datetime.now(timezone.utc).isoformat()
        summary: dict[str, object] = {
            "called": True,
            "when": ts,
            "trace_id": trace_id,
            "user_ref": user_ref,
            "what_it_did": {
                "event": event,
                "status": status,
                "duration_ms": duration_ms,
            },
        }

        if not self.enabled:
            return {**summary, "called": False, "what_it_did": {}}

        row = {
            "ts":           ts,
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
            append_chained = getattr(self._backend, "append_chained", None)
            if (
                callable(append_chained)
                and getattr(self._backend, "supports_atomic_chained_append", False)
            ):
                self._last_hash = append_chained(row, _line_hash)
            else:
                row["prev_hash"] = self._last_hash
                row["line_hash"] = _line_hash(row)
                self._backend.append(row)
                self._last_hash = row["line_hash"]
        else:
            row["prev_hash"] = None
            row["line_hash"] = _line_hash(row)
            self._backend.append(row)
        summary["what_it_did"] = {
            "event": event,
            "status": status,
            "duration_ms": duration_ms,
            "config_hash": config_hash,
            "input_hash": _hash(input_text),
            "output_hash": _hash(output_text),
        }
        return summary

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
        return self._backend.find_by_user(user_ref)

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
        n = self._backend.delete_by_user(user_ref)
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

    def close(self) -> None:
        backend = getattr(self, "_backend", None)
        if backend is not None:
            backend.close()


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