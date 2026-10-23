# Chatbot

## What it does

The chatbot wraps an LLM behind a config-driven workflow with history, tool execution, and optional normalizer integration.

## Why it matters

Developers do not want to rebuild the same conversation stack each time. The chatbot centralizes model access, tool use, and session behavior.

## Example

```python
from mim_ai import Mim

app = Mim.from_config("config.yaml")
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

## Config keys

Typical configuration values include:

- `chatbot.enabled`
- `chatbot.system_prompt`
- `chatbot.system_prompt_file`
- `chatbot.system_prompt_extra`
- `chatbot.llm_endpoint`
- `chatbot.llm_model`
- `chatbot.llm_api_key_env`
- `chatbot.enable_tools`
- `chatbot.use_intents`
- `chatbot.max_history_turns`
- `chatbot.use_normalizer`
- `chatbot.use_audit_log`

## Benefits

- easier LLM integration
- session continuity
- tool-based workflows
- cleaner production operations
