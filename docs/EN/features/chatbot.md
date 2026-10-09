# Chatbot

## What it does

The chatbot wraps an LLM behind a config-driven workflow with history, tool execution, and optional normalizer integration.

## Why it matters

Developers do not want to rebuild the same conversation stack each time. The chatbot centralizes model access, tool use, and session behavior.

## Example

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")
reply = app.chat("salam, chkoun nta?", session_id="demo")
print(reply.text)
```

## Config keys

Typical configuration values include:

- `chatbot.enabled`
- `chatbot.system_prompt`
- `chatbot.enable_tools`
- `chatbot.max_history_turns`
- `chatbot.use_normalizer`
- `chatbot.use_audit_log`

## Benefits

- easier LLM integration
- session continuity
- tool-based workflows
- cleaner production operations
