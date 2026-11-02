# Audit and logging

## What it does

MIM includes a compliance-oriented audit log and a normalizer log. These are designed for traceability and operational diagnostics.

## Why it matters

Production AI systems need accountability. Audit logs support compliance review and operational debugging.

## Example

```python
from mim_ai import Mim

app = Mim.from_config("mim_config.yaml")
app.chat("salam", session_id="demo")
```

The audit and normalizer loggers are configured through the main config object and can target different backends.

For PostgreSQL, install the optional driver with `pip install "mim-ai[postgresql]"`, then point both logging sections at the database; no custom adapter is needed. The built-in backend creates JSONB-backed tables (default names `audit_events` and `normalizer_events`):

```yaml
audit:
  backend: postgresql
  database_url_env: MIM_DATABASE_URL
logs:
  backend: postgresql
  database_url_env: MIM_DATABASE_URL
```

Set `MIM_DATABASE_URL` to a PostgreSQL connection URI before starting the application. `Mim.from_config(...)` wires both loggers from these settings. `Chatbot.from_config(config.chatbot, mim_config=config)` does the same for standalone chatbot use. The normalizer log can include user tokens when configured to capture them; review its capture settings before sending it to a shared production database.

SQLite supports custom table names through `audit.collection` and `logs.collection`. For example, `audit.collection: customer_audit` creates and queries that table instead of requiring `audit_events`.

SQLite hash-chain appends use a write transaction to read the prior hash and append the next row atomically, including when multiple processes share the same local database file. Set `audit.multi_writer: true` to require this atomic-append capability at startup. Other built-in backends and custom adapters do not currently guarantee atomic chained writes; use one writer or provide an adapter with an atomic `append_chained(row, hash_row)` implementation. SQLite WAL is intended for processes on one host/local filesystem, not a shared network filesystem.

Chat, STT and TTS remain synchronous APIs for simple applications. Async alternatives (`achat`, `alisten_and_reply`, `atranscribe`, and `asynthesize`) offload the synchronous calls to worker threads. Configure endpoint retries (`llm_max_retries` / `max_retries` and retry backoff) to handle transient 429, server, and network errors. The standard-library HTTP transport does not provide connection pooling; use a custom chatbot provider if your deployment needs pooled LLM connections.

## Benefits

- compliant by design
- easy to query later
- better support for production review and debugging
