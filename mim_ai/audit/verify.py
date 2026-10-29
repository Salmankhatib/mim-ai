"""
Hash-chain verifier for supported audit storage backends.

Reads stored records in append order, recomputes each row hash, and confirms
that adjacent `prev_hash` links match.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .backends import create_backend


def _sqlite_records(db_path: str, table: str) -> list[dict[str, Any]]:
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        cur = conn.execute(f"SELECT * FROM {table} ORDER BY seq")
        columns = [column[0] for column in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def verify_chain(
    db_path: str | None = None,
    table: str | None = None,
    *,
    config: Any | None = None,
) -> tuple[bool, str]:
    """
    Verify the audit hash chain from a SQLite path or an AuditConfig.

    Custom database adapters must implement ``iter_chain_records()``.
    Returns ``(False, message)`` for a detected integrity mismatch; backend
    and configuration errors are raised rather than reported as success.
    """
    backend_name = str(getattr(config, "backend", "sqlite")).lower()
    selected_table = table or getattr(config, "collection", "audit_events")
    if (
        (config is None or backend_name == "sqlite")
        and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", selected_table)
    ):
        raise ValueError(f"Invalid SQL table name: {selected_table!r}")

    if config is None or backend_name == "sqlite":
        selected_path = db_path or getattr(config, "db_path", None)
        if not selected_path:
            raise ValueError("db_path or an AuditConfig with db_path is required")
        records = _sqlite_records(selected_path, selected_table)
    elif backend_name == "jsonl":
        directory = Path(getattr(config, "jsonl_path", "./logs/"))
        if not directory.is_dir():
            raise FileNotFoundError(f"Audit JSONL directory not found: {directory}")
        paths = sorted(
            path for path in directory.iterdir()
            if path.is_file()
            and path.name.startswith(f"{selected_table}-")
            and path.suffix == ".jsonl"
        )
        records = []
        for path in paths:
            with path.open("r", encoding="utf-8") as fh:
                for line_number, line in enumerate(fh, start=1):
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise ValueError(f"Expected an object in {path} line {line_number}")
                    records.append(record)
    else:
        backend = create_backend(config, selected_table, schema="audit")
        try:
            records = backend.iter_chain_records()
        finally:
            backend.close()

    previous_hash = None
    for index, record in enumerate(records, start=1):
        location = record.get("seq", index)
        line_hash = record.get("line_hash")
        if not isinstance(line_hash, str):
            return False, f"record={location} missing line_hash"
        body = {key: value for key, value in record.items() if key not in {"line_hash", "seq"}}
        payload = json.dumps(body, sort_keys=True, ensure_ascii=False)
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if expected != line_hash:
            return False, f"record={location} line_hash mismatch (row edited?)"
        if previous_hash is not None and record.get("prev_hash") != previous_hash:
            return False, f"record={location} prev_hash mismatch (row deleted?)"
        previous_hash = line_hash

    return True, "chain intact"