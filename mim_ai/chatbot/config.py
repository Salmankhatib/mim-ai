"""
Chatbot config. One switch, sane defaults, everything optional.

    cfg = ChatbotConfig(enabled=True)
    bot = Chatbot.from_config(cfg)
    reply = bot.chat("salam, chkoun nta?", session_id="s1", user_ref="u_abc")

Every field has a default. Developers override only what they care about.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatbotConfig:
    """All chatbot behavior in one place."""

    # --- The switch ----------------------------------------------------
    enabled: bool = False

    # --- System prompt -------------------------------------------------
    system_prompt:        str  = "darija"
    system_prompt_file:   str | None = None
    system_prompt_extra:  str  = ""
    language:             str  = "auto"

    # --- Production options --------------------------------------------
    use_intents:          bool = True

    # --- LLM (agnostic — any OpenAI-compatible endpoint works) ---------
    llm_provider:         str  = "openai"
    llm_model:            str  = "mntra/mistral-darija"
    llm_endpoint:         str  = "https://api.mntra.ma/v1"
    llm_api_key_env:      str  = "MNTRA_API_KEY"
    llm_temperature:      float = 0.7
    llm_max_tokens:       int  = 1024
    llm_timeout_ms:       int  = 30000
    llm_extra_headers:    dict = field(default_factory=dict)
    llm_extra_params:     dict = field(default_factory=dict)

    # --- Pipeline integration -----------------------------------------
    use_normalizer:       bool = True
    use_audit_log:        bool = True
    use_normalizer_log:   bool = True

    # --- Tool use ------------------------------------------------------
    enable_tools:         bool = True
    max_tool_calls:       int  = 5

    # --- Session management --------------------------------------------
    max_history_turns:    int  = 20
    session_ttl_seconds:  int  = 3600
    history_backend:      str = "memory"
    history_dsn:          str | None = None

    # --- Free-form params passed to the LLM as-is ----------------------
    params:               dict = field(default_factory=dict)

    # --- Personalized roles, per-app semantics ------------------------
    roles:                dict = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None, **overrides: Any) -> "ChatbotConfig":
        raw = dict(data or {})
        raw.update(overrides)

        if not raw:
            return cls()

        known = {
            "enabled", "system_prompt", "system_prompt_file", "system_prompt_extra",
            "language", "use_intents", "llm_provider", "llm_model", "llm_endpoint",
            "llm_api_key_env", "llm_temperature", "llm_max_tokens", "llm_timeout_ms",
            "llm_extra_headers", "llm_extra_params", "use_normalizer", "use_audit_log",
            "use_normalizer_log", "enable_tools", "max_tool_calls", "max_history_turns",
            "session_ttl_seconds", "history_backend", "history_dsn", "params", "roles",
        }

        cleaned = {key: value for key, value in raw.items() if key in known}
        return cls(**cleaned)