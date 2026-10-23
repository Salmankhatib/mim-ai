# Audit and logging

## What it does

MIM includes a compliance-oriented audit log and a normalizer log. These are designed for traceability and operational diagnostics.

## Why it matters

Production AI systems need accountability. Audit logs support compliance review and operational debugging.

## Example

```python
from mim_ai import Mim

app = Mim.from_config("config.yaml")
app.chat("salam", session_id="demo")
```

The audit and normalizer loggers are configured through the main config object and can target different backends.

SQLite supports custom table names through `audit.collection` and `logs.collection`. For example, `audit.collection: customer_audit` creates and queries that table instead of requiring `audit_events`.

SQLite hash-chain appends use a write transaction to read the prior hash and append the next row atomically, including when multiple processes share the same local database file. Set `audit.multi_writer: true` to require this atomic-append capability at startup. Other built-in backends and custom adapters do not currently guarantee atomic chained writes; use one writer or provide an adapter with an atomic `append_chained(row, hash_row)` implementation. SQLite WAL is intended for processes on one host/local filesystem, not a shared network filesystem.

Chat, STT and TTS remain synchronous APIs for simple applications. Async alternatives (`achat`, `alisten_and_reply`, `atranscribe`, and `asynthesize`) offload the synchronous calls to worker threads. Configure endpoint retries (`llm_max_retries` / `max_retries` and retry backoff) to handle transient 429, server, and network errors. The standard-library HTTP transport does not provide connection pooling; use a custom chatbot provider if your deployment needs pooled LLM connections.

## Benefits

- compliant by design
- easy to query later
- better support for production review and debugging
