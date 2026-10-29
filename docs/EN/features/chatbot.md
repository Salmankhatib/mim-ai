# Chatbot

## What it does

The chatbot wraps an LLM behind a config-driven workflow with history, tool execution, and optional normalizer integration.

## Why it matters

Developers do not want to rebuild the same conversation stack each time. The chatbot centralizes model access, tool use, and session behavior.

## Example

```python
from mim_ai import Mim

app = Mim.from_config("mim_config.yaml")
reply = app.chat("salam, chkoun nta?", session_id="demo")
print(reply.text)
if reply.error:
    print(f"Chat request failed: {reply.error}")
```

The generated config defaults to plain text chat, with tool execution and intent classification disabled. Customize the system prompt inline, or use `system_prompt_file` and `system_prompt_extra` to organize longer instructions:

```yaml
chatbot:
  enabled: true
  enable_tools: false
  use_intents: false
  system_prompt: |
    You are a helpful customer support assistant.
    Answer in the user's language and do not invent policies.
  system_prompt_extra: |
    If you do not know an answer, say so and offer a human handoff.
```

Configure `llm_endpoint`, `llm_model`, and `llm_api_key_env` for the selected OpenAI-compatible service. The environment variable named by `llm_api_key_env` is sent as a Bearer token when set. `app.chat()` returns a `ChatReply`; use `reply.text` for the generated text and check `reply.error` when a provider request fails.

For asyncio web servers, use `await app.achat(...)` so blocking provider and history calls run in a worker thread. Transient rate-limit, server, and network errors are retried according to `llm_max_retries` and `llm_retry_backoff_ms`; set retries to `0` to disable them. Async methods prevent blocking the event loop but do not interrupt an in-flight request if its coroutine is cancelled.

For multiple workers, use a shared history backend instead of the process-local `memory` default. For example:

```yaml
chatbot:
  history_backend: redis
  history_dsn_env: MIM_REDIS_URL
```

Install Redis support with `pip install "mim-ai[redis]"` and set `MIM_REDIS_URL` in the process environment.

## Intent-scoped tools

When tools and intents are enabled together, an intent can declare one or more tool names. The chatbot exposes only those tools to the model for a matching intent and checks the allowlist again before execution. If any intent declares tool permissions, an unmatched intent receives no tools. The legacy singular `tool` field remains supported. Intent matching is routing, not authorization: every tool must independently enforce the caller's permissions.

```yaml
chatbot:
  enabled: true
  enable_tools: true
  use_intents: true
intents:
  enabled: true
  strategy: hybrid
  intents_path: ./intents.yaml
```

In `intents.yaml`, assign only the tools appropriate for each intent. The legacy singular `tool` field remains supported:

```yaml
intents:
  - name: check_order
    description: Read order information.
    examples: ["where is my order", "fin waslat commande"]
    tools: [lookup_order]
  - name: cancel_order
    description: Request an order cancellation.
    examples: ["cancel my order"]
    tools: [request_cancellation]
```

Register only application-owned functions in a per-app registry and pass it to the config-driven facade. The configured intent registry is loaded from `intents_path`:

```python
from mim_ai import Mim
from mim_ai.chatbot import ToolRegistry, tool

tools = ToolRegistry()

@tool(
    "lookup_order",
    "Read an order belonging to the authenticated customer.",
    params={"order_id": {"type": "string"}},
    registry=tools,
)
def lookup_order(order_id: str) -> str:
    row = connection.execute(
        "SELECT status FROM orders WHERE id = ? AND customer_id = ?",
        (order_id, authenticated_customer_id),
    ).fetchone()
    return row["status"] if row else "not found"

app = Mim.from_config("mim_config.yaml", tool_registry=tools)
```

Tool arguments are treated as untrusted input: declared types, required fields, and extra fields are checked before dispatch. The tool function must still enforce user authorization, business rules, and database access controls.

For SQL-backed tools, use bound parameters for values and fixed/allowlisted identifiers; never assemble SQL by interpolating user text or model-generated arguments. The SDK has no generic SQL-execution tool, so it cannot make arbitrary developer-provided tool functions safe; parameter binding and authorization belong in those functions.

## Config keys

Typical configuration values include:

- `chatbot.enabled`
- `chatbot.system_prompt`
- `chatbot.system_prompt_file`
- `chatbot.system_prompt_extra`
- `chatbot.llm_endpoint`
- `chatbot.llm_model`
- `chatbot.llm_api_key_env`
- `chatbot.llm_max_retries`
- `chatbot.llm_retry_backoff_ms`
- `chatbot.history_backend`
- `chatbot.history_dsn_env`
- `chatbot.enable_tools`
- `chatbot.use_intents`
- `intents.*` including per-intent `tool` or `tools` allowlists
- `chatbot.max_history_turns`
- `chatbot.use_normalizer`
- `chatbot.use_audit_log`

## Benefits

- easier LLM integration
- session continuity
- tool-based workflows
- cleaner production operations
