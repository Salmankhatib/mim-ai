"""
Session history storage.

One protocol, four implementations. Pick via ChatbotConfig.history_backend:

    "memory"    -> InMemoryHistoryStore (default; process-local)
    "sqlite"    -> SQLiteHistoryStore   (single file, zero setup)
    "redis"     -> RedisHistoryStore    (multi-process, fast)
    "postgres"  -> PostgresHistoryStore (durable, queryable)

Every store keeps the last `max_turns` user/assistant pairs. TTL
eviction is enforced where the backend supports it natively
(Redis, Postgres) or via a soft check on read (SQLite, Memory).

All stores serialize a message as a plain dict:
    {"role": "user"|"assistant"|"tool", "content": str, ...}
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Protocol — the only thing the chatbot depends on.
# ---------------------------------------------------------------------------
class HistoryStore:
    """Interface for session history storage."""

    def get(self, session_id: str) -> list[dict]: ...
    def append(self, session_id: str, message: dict) -> None: ...
    def clear(self, session_id: str) -> None: ...


# ---------------------------------------------------------------------------
# 1. In-memory (default)
# ---------------------------------------------------------------------------
class InMemoryHistoryStore:
    def __init__(self, max_turns: int = 20, ttl_seconds: int = 3600) -> None:
        self.max_turns = max_turns
        self.ttl = ttl_seconds
        self._data: dict[str, tuple[float, list[dict]]] = {}

    def _touch(self, sid: str) -> list[dict]:
        now = time.time()
        entry = self._data.get(sid)
        if entry is None or now - entry[0] > self.ttl:
            self._data[sid] = (now, [])
        else:
            self._data[sid] = (now, entry[1])
        return self._data[sid][1]

    def get(self, sid: str) -> list[dict]:
        return list(self._touch(sid))

    def append(self, sid: str, message: dict) -> None:
        hist = self._touch(sid)
        hist.append(message)
        cap = self.max_turns * 2
        if len(hist) > cap:
            del hist[:-cap]

    def clear(self, sid: str) -> None:
        self._data.pop(sid, None)


# ---------------------------------------------------------------------------
# 2. SQLite
# ---------------------------------------------------------------------------
_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS session_messages (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL,
    ts          REAL    NOT NULL,
    payload     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_session ON session_messages(session_id, seq);
"""


class SQLiteHistoryStore:
    """
    SQLite-backed history. One row per message.

    Suitable for single-machine deployments, dev, and small production.
    For multi-process, use Redis; for durable + queryable, use Postgres.
    """

    def __init__(
        self,
        db_path: str = "./sessions/history.db",
        max_turns: int = 20,
        ttl_seconds: int = 3600,
    ) -> None:
        self.max_turns = max_turns
        self.ttl = ttl_seconds
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, isolation_level=None)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SQLITE_SCHEMA)

    def get(self, sid: str) -> list[dict]:
        # TTL check: if the newest message is older than ttl, treat as empty.
        row = self.conn.execute(
            "SELECT MAX(ts) FROM session_messages WHERE session_id = ?", (sid,)
        ).fetchone()
        if row and row[0] and time.time() - row[0] > self.ttl:
            return []
        cur = self.conn.execute(
            "SELECT payload FROM session_messages WHERE session_id = ? "
            "ORDER BY seq DESC LIMIT ?",
            (sid, self.max_turns * 2),
        )
        rows = [json.loads(r[0]) for r in cur.fetchall()]
        rows.reverse()
        return rows

    def append(self, sid: str, message: dict) -> None:
        self.conn.execute(
            "INSERT INTO session_messages (session_id, ts, payload) VALUES (?, ?, ?)",
            (sid, time.time(), json.dumps(message, ensure_ascii=False)),
        )
        # Trim: keep only the newest max_turns*2 rows for this session.
        self.conn.execute(
            "DELETE FROM session_messages WHERE session_id = ? AND seq NOT IN "
            "(SELECT seq FROM session_messages WHERE session_id = ? "
            " ORDER BY seq DESC LIMIT ?)",
            (sid, sid, self.max_turns * 2),
        )

    def clear(self, sid: str) -> None:
        self.conn.execute("DELETE FROM session_messages WHERE session_id = ?", (sid,))


# ---------------------------------------------------------------------------
# 3. Redis
# ---------------------------------------------------------------------------
class RedisHistoryStore:
    """
    Redis-backed history. One list per session.

    Native TTL (EXPIRE) means idle sessions auto-evict at the storage
    layer — no cron, no sweeper.
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        max_turns: int = 20,
        ttl_seconds: int = 3600,
        key_prefix: str = "mim:hist:",
    ) -> None:
        try:
            import redis                                # type: ignore
        except ImportError as e:
            raise ImportError(
                "RedisHistoryStore requires the 'redis' package. "
                "Install with: pip install mim-ai[redis]"
            ) from e
        self._redis = redis.from_url(url, decode_responses=True)
        self.max_turns = max_turns
        self.ttl = ttl_seconds
        self.prefix = key_prefix

    def _key(self, sid: str) -> str:
        return f"{self.prefix}{sid}"

    def get(self, sid: str) -> list[dict]:
        raw = self._redis.lrange(self._key(sid), -self.max_turns * 2, -1)
        return [json.loads(x) for x in raw]

    def append(self, sid: str, message: dict) -> None:
        key = self._key(sid)
        self._redis.rpush(key, json.dumps(message, ensure_ascii=False))
        # Trim to the newest N entries, then refresh TTL.
        self._redis.ltrim(key, -self.max_turns * 2, -1)
        self._redis.expire(key, self.ttl)

    def clear(self, sid: str) -> None:
        self._redis.delete(self._key(sid))


# ---------------------------------------------------------------------------
# 4. Postgres
# ---------------------------------------------------------------------------
_POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS session_messages (
    seq         BIGSERIAL PRIMARY KEY,
    session_id  TEXT      NOT NULL,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload     JSONB     NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_session ON session_messages(session_id, seq DESC);
"""


class PostgresHistoryStore:
    """
    Postgres-backed history. Durable, queryable, multi-process.

    Uses psycopg (v3). Connection pooling is the caller's job — pass
    a prepared connection factory, or the DSN will open a fresh
    connection per call (fine for low traffic).
    """

    def __init__(
        self,
        dsn: str = "postgresql://localhost/mim",
        max_turns: int = 20,
        ttl_seconds: int = 3600,
    ) -> None:
        try:
            import psycopg                              # type: ignore
        except ImportError as e:
            raise ImportError(
                "PostgresHistoryStore requires the 'psycopg' package. "
                "Install with: pip install mim-ai[postgres]"
            ) from e
        self._psycopg = psycopg
        self.dsn = dsn
        self.max_turns = max_turns
        self.ttl = ttl_seconds
        with self._conn() as c:
            with c.cursor() as cur:
                cur.execute(_POSTGRES_SCHEMA)
            c.commit()

    def _conn(self):
        return self._psycopg.connect(self.dsn)

    def get(self, sid: str) -> list[dict]:
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "SELECT payload, EXTRACT(EPOCH FROM ts) FROM session_messages "
                "WHERE session_id = %s ORDER BY seq DESC LIMIT %s",
                (sid, self.max_turns * 2),
            )
            rows = cur.fetchall()
        if not rows:
            return []
        # TTL check on newest row.
        if time.time() - float(rows[0][1]) > self.ttl:
            return []
        return [r[0] if isinstance(r[0], dict) else json.loads(r[0]) for r in reversed(rows)]

    def append(self, sid: str, message: dict) -> None:
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "INSERT INTO session_messages (session_id, payload) VALUES (%s, %s)",
                (sid, json.dumps(message, ensure_ascii=False)),
            )
            cur.execute(
                "DELETE FROM session_messages WHERE session_id = %s AND seq NOT IN "
                "(SELECT seq FROM session_messages WHERE session_id = %s "
                " ORDER BY seq DESC LIMIT %s)",
                (sid, sid, self.max_turns * 2),
            )
            c.commit()

    def clear(self, sid: str) -> None:
        with self._conn() as c, c.cursor() as cur:
            cur.execute("DELETE FROM session_messages WHERE session_id = %s", (sid,))
            c.commit()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def build_history_store(config) -> HistoryStore:
    """
    Return the HistoryStore indicated by `config.history_backend`.
    Never raises on unknown backend — falls back to memory with a
    printed warning, so a misconfig doesn't crash a running service.
    """
    backend = getattr(config, "history_backend", "memory")
    dsn = getattr(config, "history_dsn", "") or ""
    max_turns = getattr(config, "max_history_turns", 20)
    ttl = getattr(config, "session_ttl_seconds", 3600)

    if backend == "memory":
        return InMemoryHistoryStore(max_turns, ttl)

    if backend == "sqlite":
        path = dsn or "./sessions/history.db"
        return SQLiteHistoryStore(path, max_turns, ttl)

    if backend == "redis":
        return RedisHistoryStore(dsn or "redis://localhost:6379/0", max_turns, ttl)

    if backend == "postgres":
        return PostgresHistoryStore(dsn or "postgresql://localhost/mim", max_turns, ttl)

    print(f"[mim_ai] Unknown history_backend={backend!r}; using memory.")
    return InMemoryHistoryStore(max_turns, ttl)