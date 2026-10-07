"""
Chatbot config. One switch, sane defaults, everything optional.

    cfg = ChatbotConfig(enabled=True)
    bot = Chatbot.from_config(cfg)
    reply = bot.chat("salam, chkoun nta?", session_id="s1", user_ref="u_abc")

Every field has a default. Developers override only what they care about.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChatbotConfig:
    """All chatbot behavior in one place."""

    # --- The switch ----------------------------------------------------
    enabled: bool = False

    # --- System prompt -------------------------------------------------
    # Either a literal string, or the name of a template in
    # prompt_templates.py: "default", "darija", "support", "tutor".
    system_prompt:        str  = "darija"
    system_prompt_extra:  str  = ""      # appended after the template
    language:             str  = "auto"  # "auto" | "ar" | "fr" | "en" | "darija"

    # --- LLM (agnostic — any OpenAI-compatible endpoint works) ---------
    llm_provider:         str  = "openai"          # openai | ollama | mntra | custom
    llm_model:            str  = "mntra/mistral-darija"
    llm_endpoint:         str  = "https://api.mntra.ma/v1"
    llm_api_key_env:      str  = "MNTRA_API_KEY"
    llm_temperature:      float = 0.7
    llm_max_tokens:       int  = 1024
    llm_timeout_ms:       int  = 30000
    llm_extra_headers:    dict = field(default_factory=dict)
    llm_extra_params:     dict = field(default_factory=dict)  # e.g. {"top_p": 0.9}

    # --- Pipeline integration -----------------------------------------
    use_normalizer:       bool = True    # run message through Normalizer first
    use_audit_log:        bool = True    # reuse mim_ai.audit.AuditLogger
    use_normalizer_log:   bool = True    # reuse mim_ai.audit.NormalizerLogger

    # --- Tool use ------------------------------------------------------
    enable_tools:         bool = True
    max_tool_calls:       int  = 5        # safety cap per turn

    # --- Session management --------------------------------------------
    max_history_turns:    int  = 20       # keep last N user+assistant pairs
    session_ttl_seconds:  int  = 3600     # in-memory eviction

    # --- Free-form params passed to the LLM as-is ----------------------
    # e.g. {"response_format": {"type": "json_object"}}
    params:               dict = field(default_factory=dict)