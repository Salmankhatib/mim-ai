"""
Hash-chain verifier for the audit log (ISO 42001 tamper-evidence).

Walks the SQLite audit_events table in `seq` order, recomputes each
line's hash, and confirms prev_hash matches the previous line's
line_hash. Any mismatch means the log was edited out-of-band.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3


def verify_chain(db_path: str) -> tuple[bool, str]:
    """
    Returns (ok, message).
    `ok=False` means the chain is broken at some seq; message says where.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT * FROM audit_events ORDER BY seq")
    cols = [c[0] for c in cur.description]

    prev = None
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        # Recompute hash of this row, ignoring line_hash.
        body = {k: v for k, v in r.items() if k != "line_hash"}
        payload = json.dumps(body, sort_keys=True, ensure_ascii=False)
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        if expected != r["line_hash"]:
            return False, f"seq={r['seq']} line_hash mismatch (row edited?)"
        if prev is not None and r["prev_hash"] != prev:
            return False, f"seq={r['seq']} prev_hash mismatch (row deleted?)"
        prev = r["line_hash"]

    return True, "chain intact"