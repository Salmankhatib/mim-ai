-- Audit log — law 09-08 + ISO 42001 trail.
-- User text is NEVER stored. Only SHA-256 hashes.
CREATE TABLE IF NOT EXISTS audit_events (
    seq             INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT    NOT NULL,          -- ISO 8601 UTC
    trace_id        TEXT    NOT NULL,
    event           TEXT    NOT NULL,
    user_ref        TEXT,                       -- pseudonym, never raw
    app_version     TEXT    NOT NULL,
    config_hash     TEXT,
    input_hash      TEXT,                       -- SHA-256 of user text
    output_hash     TEXT,
    duration_ms     INTEGER,
    status          TEXT    NOT NULL DEFAULT 'ok',
    payload         TEXT    NOT NULL DEFAULT '{}',  -- JSON blob
    prev_hash       TEXT,                       -- hash of previous line
    line_hash       TEXT    NOT NULL            -- hash of this line
);
CREATE INDEX IF NOT EXISTS idx_audit_ts       ON audit_events(ts);
CREATE INDEX IF NOT EXISTS idx_audit_user     ON audit_events(user_ref);
CREATE INDEX IF NOT EXISTS idx_audit_trace    ON audit_events(trace_id);

-- Normalizer feedback log — dev tool, NOT a compliance trail.
CREATE TABLE IF NOT EXISTS normalizer_events (
    seq             INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT    NOT NULL,
    trace_id        TEXT    NOT NULL,
    user_ref        TEXT,
    lang_detected   TEXT,
    code_switched   INTEGER NOT NULL DEFAULT 0,  -- 0/1
    jargon_used     TEXT    NOT NULL DEFAULT '{}',  -- JSON {key: count}
    jargon_skipped  TEXT    NOT NULL DEFAULT '{}',  -- JSON {token: count}
    arabizi_used    INTEGER NOT NULL DEFAULT 0,
    arabizi_oov     INTEGER NOT NULL DEFAULT 0,
    rules_applied   INTEGER NOT NULL DEFAULT 0,
    urls_protected  INTEGER NOT NULL DEFAULT 0,
    duration_ms     INTEGER
);
CREATE INDEX IF NOT EXISTS idx_norm_ts     ON normalizer_events(ts);
CREATE INDEX IF NOT EXISTS idx_norm_user   ON normalizer_events(user_ref);
CREATE INDEX IF NOT EXISTS idx_norm_trace  ON normalizer_events(trace_id);