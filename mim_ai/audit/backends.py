"""
Storage backends: SQLite (default) and JSONL.

Both implement the same two methods:
    append(row: dict) -> None
    purge_older_than(days: int) -> int

SQLite gives you SQL queries out of the box. JSONL gives you grep
and `jq`. Pick one per logger via `config.backend`.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# SQLite
# ---------------------------------------------------------------------------
class SQLiteBackend:
    """
    One file, SQL queries, zero server.

    The table is created on first use from `schema.sql`. Two separate
    tables (audit_events, normalizer_events) live in separate DB
    files, so deleting normalizer logs never touches audit logs.
    """

    def __init__(self, db_path: str, table: str) -> None:
        self.table = table
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), isolation_level=None)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
        self.conn.executescript(schema)

    def append(self, row: dict) -> None:
        cols = ", ".join(row.keys())
        placeholders = ", ".join("?" for _ in row)
        self.conn.execute(
            f"INSERT INTO {self.table} ({cols}) VALUES ({placeholders})",
            tuple(row.values()),
        )

    def purge_older_than(self, days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cur = self.conn.execute(
            f"DELETE FROM {self.table} WHERE ts < ?", (cutoff,)
        )
        return cur.rowcount


# ---------------------------------------------------------------------------
# JSONL
# ---------------------------------------------------------------------------
class JSONLBackend:
    """
    One file per day: audit-YYYY-MM-DD.jsonl, normalizer-YYYY-MM-DD.jsonl.

    Append-only. Each line is a self-contained JSON object. Query
    with `jq` or pandas.
    """

    def __init__(self, directory: str, prefix: str) -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.prefix = prefix

    def _path_for_today(self) -> Path:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.dir / f"{self.prefix}-{day}.jsonl"

    def append(self, row: dict) -> None:
        path = self._path_for_today()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")

    def purge_older_than(self, days: int) -> int:
        cutoff = time.time() - days * 86400
        removed = 0
        for path in self.dir.glob(f"{self.prefix}-*.jsonl"):
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        return removed