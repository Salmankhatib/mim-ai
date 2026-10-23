"""
Storage backends: SQLite (default), JSONL, and a generic adapter contract.

Every backend implements the same small interface:
    append(row: dict) -> None
    purge_older_than(days: int) -> int

This keeps the logger API stable regardless of whether the app uses
SQLite, a JSONL export, PostgreSQL, MySQL, MongoDB, Cassandra, or a
custom database layer.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_sql_identifier(table: str) -> str:
    if not _IDENTIFIER_RE.fullmatch(table):
        raise ValueError(f"Invalid SQL table name: {table!r}")
    return table


def _database_url(config: Any) -> str | None:
    url = getattr(config, "database_url", None)
    env_name = getattr(config, "database_url_env", None)
    if env_name:
        url = os.environ.get(env_name, url)
        if not url:
            raise ValueError(
                f"Database URL is missing; set environment variable {env_name!r}"
            )
    return url


class LogStorageAdapter:
    """Minimal contract for a database-backed sink.

    App code can inject any object or factory that exposes the same
    interface: `append(row)` and `purge_older_than(days)`.
    """

    def append(self, row: dict[str, Any]) -> None:
        raise NotImplementedError

    def purge_older_than(self, days: int) -> int:
        raise NotImplementedError

    def close(self) -> None:
        return None


# ---------------------------------------------------------------------------
# SQLite
# ---------------------------------------------------------------------------
class SQLiteBackend(LogStorageAdapter):
    """
    One file, SQL queries, zero server.

    The table is created on first use from `schema.sql`. Two separate
    tables (audit_events, normalizer_events) live in separate DB
    files, so deleting normalizer logs never touches audit logs.
    """
    supports_atomic_chained_append = True

    def __init__(self, db_path: str, table: str, schema: str = "audit") -> None:
        self.table = _validate_sql_identifier(table)
        if schema not in {"audit", "normalizer"}:
            raise ValueError(f"Unsupported SQLite log schema: {schema!r}")
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(
            str(path), isolation_level=None, check_same_thread=False,
            timeout=30,
        )
        self._lock = threading.RLock()
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_schema(schema)

    def _ensure_schema(self, schema_kind: str) -> None:
        schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
        default_table = "audit_events" if schema_kind == "audit" else "normalizer_events"
        if self.table != default_table:
            schema = schema.replace(default_table, self.table)
            index_prefix = "idx_audit_" if schema_kind == "audit" else "idx_norm_"
            schema = schema.replace(index_prefix, f"idx_{self.table}_")
        with self._lock:
            self.conn.executescript(schema)

    def _insert(self, row: dict[str, Any]) -> None:
        columns = ", ".join(row)
        placeholders = ", ".join("?" for _ in row)
        self.conn.execute(
            f"INSERT INTO {self.table} ({columns}) VALUES ({placeholders})",
            tuple(row.values()),
        )

    def append(self, row: dict) -> None:
        with self._lock:
            self._insert(row)

    def append_chained(
        self, row: dict[str, Any], hash_row: Callable[[dict[str, Any]], str]
    ) -> str:
        """Atomically link and append a row across threads and processes."""
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                previous = self.conn.execute(
                    f"SELECT line_hash FROM {self.table} "
                    "ORDER BY seq DESC LIMIT 1"
                ).fetchone()
                row["prev_hash"] = previous[0] if previous else None
                row["line_hash"] = hash_row(row)
                self._insert(row)
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise
        return row["line_hash"]

    def purge_older_than(self, days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._lock:
            cur = self.conn.execute(
                f"DELETE FROM {self.table} WHERE ts < ?", (cutoff,)
            )
            return cur.rowcount

    def find_by_user(self, user_ref: str) -> list[dict[str, Any]]:
        with self._lock:
            cur = self.conn.execute(
                f"SELECT * FROM {self.table} WHERE user_ref = ? ORDER BY seq",
                (user_ref,),
            )
            columns = [column[0] for column in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def delete_by_user(self, user_ref: str) -> int:
        with self._lock:
            cur = self.conn.execute(
                f"DELETE FROM {self.table} WHERE user_ref = ?", (user_ref,)
            )
            return cur.rowcount

    def close(self) -> None:
        with self._lock:
            self.conn.close()


# ---------------------------------------------------------------------------
# JSONL
# ---------------------------------------------------------------------------
class JSONLBackend(LogStorageAdapter):
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

    def last_hash(self) -> str | None:
        """Return the latest hash-chain link across this backend's dated files."""
        paths = sorted(
            self.dir.glob(f"{self.prefix}-*.jsonl"),
            key=lambda path: path.name,
            reverse=True,
        )
        for path in paths:
            last_hash = None
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        record = json.loads(line)
                        last_hash = record.get("line_hash", last_hash)
            if last_hash is not None:
                return last_hash
        return None

    def purge_older_than(self, days: int) -> int:
        cutoff = time.time() - days * 86400
        removed = 0
        for path in self.dir.glob(f"{self.prefix}-*.jsonl"):
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        return removed


# ---------------------------------------------------------------------------
# Generic DB adapter
# ---------------------------------------------------------------------------
class PostgreSQLBackend(LogStorageAdapter):
    """Production-ready PostgreSQL adapter.

    Stores each row as a JSONB payload so the log structure stays flexible
    and query-friendly for analytics dashboards and compliance review.
    """

    def __init__(self, database_url: str | None, table: str) -> None:
        self.database_url = database_url
        self.table = _validate_sql_identifier(table)
        self._conn = None

    def _connect(self):
        if self._conn is not None:
            return self._conn
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - environment-specific
            raise RuntimeError(
                "PostgreSQL logging requires the optional dependency 'psycopg[binary]'. "
                "Install it with: pip install "
                "\"psycopg[binary]\""
            ) from exc
        if not self.database_url:
            raise ValueError("database_url is required for PostgreSQL backend")
        self._conn = psycopg.connect(self.database_url)
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.table} (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    payload JSONB NOT NULL
                )
                """
            )
        return self._conn

    def append(self, row: dict[str, Any]) -> None:
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.table} (payload) VALUES (%s)",
                (json.dumps(row, ensure_ascii=False),),
            )
        conn.commit()

    def purge_older_than(self, days: int) -> int:
        conn = self._connect()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self.table} WHERE created_at < %s",
                (cutoff,),
            )
            count = cur.rowcount
        conn.commit()
        return count

    def last_hash(self) -> str | None:
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT payload->>'line_hash' FROM {self.table} "
                "WHERE payload ? 'line_hash' ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
        return row[0] if row else None

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


class MySQLBackend(LogStorageAdapter):
    """Production-ready MySQL adapter."""

    def __init__(self, database_url: str | None, table: str) -> None:
        self.database_url = database_url
        self.table = _validate_sql_identifier(table)
        self._conn = None

    def _connect(self):
        if self._conn is not None:
            return self._conn
        try:
            import pymysql
        except ImportError as exc:  # pragma: no cover - environment-specific
            raise RuntimeError(
                "MySQL logging requires the optional dependency 'PyMySQL'. "
                "Install it with: pip install PyMySQL"
            ) from exc
        if not self.database_url:
            raise ValueError("database_url is required for MySQL backend")

        parsed = urlparse(self.database_url)
        if parsed.scheme not in {"mysql", "mysql+mysqlconnector"}:
            raise ValueError(
                "database_url must look like 'mysql://user:pass@host:3306/dbname'"
            )

        self._conn = pymysql.connect(
            host=parsed.hostname,
            port=parsed.port or 3306,
            user=parsed.username or "",
            password=parsed.password or "",
            database=parsed.path.lstrip("/") or None,
        )
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.table} (
                    id BIGINT NOT NULL AUTO_INCREMENT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    payload JSON,
                    PRIMARY KEY (id)
                )
                """
            )
        return self._conn

    def append(self, row: dict[str, Any]) -> None:
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.table} (payload) VALUES (%s)",
                (json.dumps(row, ensure_ascii=False),),
            )
        conn.commit()

    def purge_older_than(self, days: int) -> int:
        conn = self._connect()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self.table} WHERE created_at < %s",
                (cutoff,),
            )
            count = cur.rowcount
        conn.commit()
        return count

    def last_hash(self) -> str | None:
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT JSON_UNQUOTE(JSON_EXTRACT(payload, '$.line_hash')) "
                f"FROM {self.table} ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
        return row[0] if row and row[0] else None

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


class MongoDBBackend(LogStorageAdapter):
    """Production-ready MongoDB adapter."""

    def __init__(self, database_url: str | None, table: str, database_name: str | None = None) -> None:
        self.database_url = database_url
        self.table = table
        parsed = urlparse(database_url or "")
        self.database_name = database_name or parsed.path.lstrip("/") or "mim_ai"
        self._client = None
        self._collection = None

    def _connect(self):
        if self._collection is not None:
            return self._collection
        try:
            from pymongo import MongoClient
        except ImportError as exc:  # pragma: no cover - environment-specific
            raise RuntimeError(
                "MongoDB logging requires the optional dependency 'pymongo'. "
                "Install it with: pip install pymongo"
            ) from exc
        if not self.database_url:
            raise ValueError("database_url is required for MongoDB backend")
        self._client = MongoClient(self.database_url)
        db = self._client[self.database_name]
        self._collection = db[self.table]
        return self._collection

    def append(self, row: dict[str, Any]) -> None:
        collection = self._connect()
        collection.insert_one(row)

    def purge_older_than(self, days: int) -> int:
        collection = self._connect()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = collection.delete_many({"ts": {"$lt": cutoff}})
        return int(result.deleted_count)

    def last_hash(self) -> str | None:
        collection = self._connect()
        latest = collection.find_one(
            {"line_hash": {"$exists": True}},
            sort=[("_id", -1)],
            projection={"line_hash": 1},
        )
        return latest.get("line_hash") if latest else None

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._collection = None


class GenericDatabaseBackend(LogStorageAdapter):
    """Fallback adapter for DB-agnostic deployments.

    The logger API stays unchanged; the actual database implementation is
    injected via `config.adapter` or by subclassing this adapter. If no
    concrete adapter is provided, we keep a portable JSONL mirror on disk
    so the app can start without a vendor-specific dependency.
    """

    def __init__(
        self,
        *,
        table: str,
        dsn: str | None = None,
        collection: str | None = None,
        driver: str | None = None,
        adapter: Any | None = None,
    ) -> None:
        self.table = table
        self.dsn = dsn
        self.collection = collection or table
        self.driver = driver
        self._adapter = adapter

        if adapter is not None:
            if callable(adapter):
                self._adapter = adapter(table=table, dsn=dsn, collection=collection, driver=driver)
            else:
                self._adapter = adapter
        if self._adapter is not None:
            return

        fallback_dir = Path("./logs") / (driver or "generic")
        fallback_dir.mkdir(parents=True, exist_ok=True)
        self._fallback_path = fallback_dir / f"{table}.jsonl"

    def append(self, row: dict[str, Any]) -> None:
        if self._adapter is not None:
            self._adapter.append(row)
            return
        with self._fallback_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")

    @property
    def supports_atomic_chained_append(self) -> bool:
        return callable(getattr(self._adapter, "append_chained", None))

    def append_chained(
        self, row: dict[str, Any], hash_row: Callable[[dict[str, Any]], str]
    ) -> str:
        append_chained = getattr(self._adapter, "append_chained", None)
        if not callable(append_chained):
            raise NotImplementedError(
                "The configured database adapter must implement "
                "append_chained(row, hash_row) for multi-writer audit chains"
            )
        return append_chained(row, hash_row)

    def purge_older_than(self, days: int) -> int:
        if self._adapter is not None:
            return self._adapter.purge_older_than(days)
        path = getattr(self, "_fallback_path", None)
        if path is None or not path.exists():
            return 0
        cutoff = time.time() - days * 86400
        removed = 0
        for entry in path.parent.glob("*.jsonl"):
            if entry.stat().st_mtime < cutoff:
                entry.unlink()
                removed += 1
        return removed

    def close(self) -> None:
        close = getattr(self._adapter, "close", None)
        if callable(close):
            close()


def create_backend(
    config: Any, table: str, *, schema: str = "audit"
) -> LogStorageAdapter:
    """Factory that resolves a concrete backend from config.

    Built-in production backends: sqlite, jsonl, postgresql, mysql, mongodb.
    Custom adapters are still supported via `config.adapter` and should take
    precedence when provided explicitly by the app.
    """
    backend_name = str(getattr(config, "backend", "sqlite")).lower()
    adapter = getattr(config, "adapter", None)
    if adapter is not None:
        return GenericDatabaseBackend(
            table=table,
            dsn=_database_url(config),
            collection=getattr(config, "collection", table),
            driver=backend_name,
            adapter=adapter,
        )

    if backend_name == "sqlite":
        return SQLiteBackend(
            getattr(config, "db_path", "./audit.db"), table, schema=schema
        )
    if backend_name == "jsonl":
        directory = getattr(config, "jsonl_path", "./logs/")
        return JSONLBackend(directory, table)
    if backend_name in {"postgres", "postgresql"}:
        return PostgreSQLBackend(_database_url(config), table)
    if backend_name in {"mysql", "mariadb"}:
        return MySQLBackend(_database_url(config), table)
    if backend_name in {"mongo", "mongodb"}:
        return MongoDBBackend(
            _database_url(config),
            table,
            getattr(config, "database_name", None),
        )

    raise ValueError(f"Unsupported audit backend: {backend_name!r}")


__all__ = [
    "LogStorageAdapter",
    "SQLiteBackend",
    "JSONLBackend",
    "PostgreSQLBackend",
    "MySQLBackend",
    "MongoDBBackend",
    "GenericDatabaseBackend",
    "create_backend",
]