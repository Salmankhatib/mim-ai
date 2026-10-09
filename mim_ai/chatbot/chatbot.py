"""
Chatbot orchestrator.

Flow per turn:
    normalize user message (if enabled)
    build messages = [system] + history + [user]
    loop:
        call LLM
        if tool calls: execute, append results, repeat (up to max_tool_calls)
        else: break
    append assistant reply to history
    emit audit + normalizer logs (if enabled)
    return reply

Session storage is in-memory by default. Pass `history_store=` to
use Redis/Postgres/whatever — see the HistoryStore protocol.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Protocol

from .config import ChatbotConfig
from .history import build_history_store
from .llm import LLMError, LLMProvider, ToolCall, build_provider
from .prompt_templates import resolve as resolve_prompt
from .tools import ToolRegistry, get_default_registry


# ---------------------------------------------------------------------------
# History storage — pluggable
# ---------------------------------------------------------------------------
class HistoryStore(Protocol):
    def get(self, session_id: str) -> list[dict]: ...
    def append(self, session_id: str, message: dict) -> None: ...
    def clear(self, session_id: str) -> None: ...


class InMemoryHistoryStore:
    """Default store. Evicts on TTL, caps at max_turns per session."""

    def __init__(self, max_turns: int, ttl_seconds: int) -> None:
        self.max_turns = max_turns
        self.ttl = ttl_seconds
        self._data: dict[str, tuple[float, list[dict]]] = {}

    def _touch(self, sid: str) -> list[dict]:
        now = time.time()
        entry = self._data.get(sid)
        if entry is None or now - entry[0] > self.ttl:
            self._data[sid] = (now, [])
        else:
            self._data[sid] = (now, entry[1])
        return self._data[sid][1]

    def get(self, sid: str) -> list[dict]:
        return list(self._touch(sid))

    def append(self, sid: str, message: dict) -> None:
        hist = self._touch(sid)
        hist.append(message)
        # Cap to N user turns (2 messages each: user + assistant)
        cap = self.max_turns * 2
        if len(hist) > cap:
            del hist[:-cap]

    def clear(self, sid: str) -> None:
        self._data.pop(sid, None)


# ---------------------------------------------------------------------------
# Reply container
# ---------------------------------------------------------------------------
@dataclass
class ChatReply:
    text:         str
    tool_calls:   list[dict] = field(default_factory=list)
    trace_id:     str = ""
    duration_ms:  int = 0
    usage:        dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Chatbot
# ---------------------------------------------------------------------------
class Chatbot:
    """
    Construct once at app startup. Reuse across requests.
    """

    def __init__(
        self,
        config: ChatbotConfig,
        provider: LLMProvider | None = None,
        registry: ToolRegistry | None = None,
        history: HistoryStore | None = None,
        normalizer=None,          # mim_ai.normalizer.Normalizer, optional
        audit=None,               # mim_ai.audit.AuditLogger, optional
        normalizer_log=None,      # mim_ai.audit.NormalizerLogger, optional
    ) -> None:
        self.config = config
        self.enabled = config.enabled
        self.provider = provider or build_provider(config)
        self.registry = registry or get_default_registry()
        self.history = history or build_history_store(config)
        self.roles = dict(getattr(config, "roles", {}) or {})
        self.normalizer = normalizer
        self.audit = audit
        self.normalizer_log = normalizer_log
        self.system_prompt = resolve_prompt(
            config.system_prompt,
            config.system_prompt_extra,
            file_path=getattr(config, "system_prompt_file", None),
        )

    # -----------------------------------------------------------------
    @classmethod
    def from_config(cls, config: ChatbotConfig, **kwargs) -> "Chatbot":
        """
        Build a Chatbot, wiring up the normalizer and loggers
        automatically when the corresponding flags are on.

        Optional kwargs:
            normalizer, audit, normalizer_log, provider, registry, history
        Any explicit kwarg overrides auto-wiring.
        """
        if not config.enabled:
            return cls(config)

        # Auto-wire the normalizer if requested and not supplied.
        if config.use_normalizer and kwargs.get("normalizer") is None:
            try:
                from mim_ai.normalizer import Normalizer, NormalizerConfig
                kwargs["normalizer"] = Normalizer.from_config(NormalizerConfig())
            except Exception:            # noqa: BLE001
                pass

        # Auto-wire loggers if requested and not supplied.
        if config.use_audit_log and kwargs.get("audit") is None:
            try:
                from mim_ai.audit import AuditLogger, AuditConfig
                kwargs["audit"] = AuditLogger(AuditConfig(enabled=True))
            except Exception:            # noqa: BLE001
                pass

        if config.use_normalizer_log and kwargs.get("normalizer_log") is None:
            try:
                from mim_ai.audit import NormalizerLogger, NormalizerLogConfig
                kwargs["normalizer_log"] = NormalizerLogger(NormalizerLogConfig(enabled=True))
            except Exception:            # noqa: BLE001
                pass

        return cls(config, **kwargs)

    # -----------------------------------------------------------------
    # The one method a developer calls.
    # -----------------------------------------------------------------
    def chat(
        self,
        message: str,
        *,
        session_id: str = "default",
        user_ref: str | None = None,
    ) -> ChatReply:
        """
        Send a message, return a reply.

        `session_id` groups turns into a conversation. `user_ref` is
        the pseudonymous user ID used by the audit log; never pass
        the raw phone / email here.
        """
        if not self.enabled:
            return ChatReply(text="", trace_id="")

        t0 = time.perf_counter()
        trace_id = f"chat_{uuid.uuid4().hex[:12]}"

        # --- 1. Normalize the user message ---------------------------
        user_text = message
        if self.normalizer is not None:
            user_text, norm_report = self.normalizer.normalize(
                message, return_report=True,
            )
            # Feed the normalizer log if wired.
            if self.normalizer_log is not None:
                self.normalizer_log.emit(
                    trace_id=trace_id, user_ref=user_ref,
                    jargon_used=getattr(norm_report, "jargon_used", {}),
                    jargon_skipped=getattr(norm_report, "jargon_skipped", {}),
                    arabizi_used=getattr(norm_report, "dictionary_hits", 0),
                    arabizi_oov=int(getattr(norm_report, "oov_arabizi", False)),
                    rules_applied=getattr(norm_report, "rule_applications", 0),
                )

        # --- 2. Build the message list -------------------------------
        messages = self._build_messages(session_id, user_text)

        # --- 3. Tool-use loop ----------------------------------------
        tool_calls_made: list[dict] = []
        final_text = ""
        usage: dict = {}

        try:
            for _ in range(self.config.max_tool_calls):
                tool_schemas = (
                    self.registry.specs()
                    if self.config.enable_tools and self.registry
                    else None
                )
                response = self.provider.chat(messages, tools=tool_schemas)
                usage = response.usage or usage

                if not response.tool_calls:
                    final_text = response.content or ""
                    break

                # Append the assistant's tool-call message verbatim.
                messages.append(self._assistant_tool_msg(response.tool_calls))

                # Execute each tool and append its result.
                for call in response.tool_calls:
                    result = self.registry.execute(call.name, call.arguments)
                    tool_calls_made.append({
                        "name": call.name, "args": call.arguments,
                    })
                    messages.append({
                        "role":         "tool",
                        "tool_call_id": call.id,
                        "content":      result,
                    })
            else:
                # Loop exhausted without a final answer.
                final_text = "(tool call limit reached)"

        except LLMError as e:
            final_text = f"(LLM error: {e})"

        # --- 4. Persist history --------------------------------------
        self.history.append(session_id, {"role": "user",      "content": user_text})
        if final_text:
            self.history.append(session_id, {"role": "assistant", "content": final_text})

        duration_ms = int((time.perf_counter() - t0) * 1000)

        # --- 5. Audit log --------------------------------------------
        if self.audit is not None:
            self.audit.emit(
                event="chat",
                trace_id=trace_id,
                user_ref=user_ref,
                input_text=message,
                output_text=final_text,
                duration_ms=duration_ms,
                status="ok" if final_text else "error",
                extra={
                    "session_id":  session_id,
                    "model":       self.config.llm_model,
                    "tool_calls":  [t["name"] for t in tool_calls_made],
                    "usage":       usage,
                },
            )

        return ChatReply(
            text=final_text,
            tool_calls=tool_calls_made,
            trace_id=trace_id,
            duration_ms=duration_ms,
            usage=usage,
        )

    # -----------------------------------------------------------------
    def reset(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        self.history.clear(session_id)

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _build_messages(self, session_id: str, user_text: str) -> list[dict]:
        msgs: list[dict] = [{"role": "system", "content": self.system_prompt}]
        msgs.extend(self.history.get(session_id))
        msgs.append({"role": "user", "content": user_text})
        return msgs

    @staticmethod
    def _assistant_tool_msg(tool_calls: list[ToolCall]) -> dict:
        """
        Build the assistant message that carries tool calls.

        OpenAI's API requires this exact shape before tool results
        can be appended. Some providers want `content: null`, others
        want `content: ""`; null is what the spec says.
        """
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id":   tc.id,
                    "type": "function",
                    "function": {
                        "name":      tc.name,
                        "arguments": _json(tc.arguments),
                    },
                }
                for tc in tool_calls
            ],
        }


def _json(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)