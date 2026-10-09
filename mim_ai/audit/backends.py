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
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class LogStorageAdapter:
    """Minimal contract for a database-backed sink.

    App code can inject any object or factory that exposes the same
    interface: `append(row)` and `purge_older_than(days)`.
    """

    def append(self, row: dict[str, Any]) -> None:
        raise NotImplementedError

    def purge_older_than(self, days: int) -> int:
        raise NotImplementedError


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
        self.table = table
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


class MySQLBackend(LogStorageAdapter):
    """Production-ready MySQL adapter."""

    def __init__(self, database_url: str | None, table: str) -> None:
        self.database_url = database_url
        self.table = table
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


class MongoDBBackend(LogStorageAdapter):
    """Production-ready MongoDB adapter."""

    def __init__(self, database_url: str | None, table: str, database_name: str | None = None) -> None:
        self.database_url = database_url
        self.table = table
        self.database_name = database_name or "mim_ai"
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


def create_backend(config: Any, table: str) -> LogStorageAdapter:
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
            dsn=getattr(config, "database_url", None),
            collection=getattr(config, "collection", table),
            driver=backend_name,
            adapter=adapter,
        )

    if backend_name == "sqlite":
        return SQLiteBackend(getattr(config, "db_path", "./audit.db"), table)
    if backend_name == "jsonl":
        directory = getattr(config, "jsonl_path", "./logs/")
        return JSONLBackend(directory, table)
    if backend_name in {"postgres", "postgresql"}:
        return PostgreSQLBackend(getattr(config, "database_url", None), table)
    if backend_name in {"mysql", "mariadb"}:
        return MySQLBackend(getattr(config, "database_url", None), table)
    if backend_name in {"mongo", "mongodb"}:
        return MongoDBBackend(
            getattr(config, "database_url", None),
            table,
            getattr(config, "database_name", None),
        )

    return GenericDatabaseBackend(
        table=table,
        dsn=getattr(config, "database_url", None),
        collection=getattr(config, "collection", table),
        driver=backend_name,
    )


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