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

import asyncio
import threading
import time
import uuid
import warnings
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
    intent:       str | None = None
    intent_score: float = 0.0
    error:        str | None = None


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
        intents=None,
        intent_strategy: str = "rule",
        intent_prompt: str | None = None,
    ) -> None:
        self.config = config
        self.enabled = config.enabled
        self.registry = registry if registry is not None else get_default_registry()
        self.intents = intents
        if self.config.enable_tools and self.intents is not None:
            if self.intents.has_tool_restrictions:
                configured_tools = {
                    name
                    for intent in self.intents.all()
                    for name in (intent.tool_names or [])
                }
                unknown_tools = configured_tools - {
                    spec["function"]["name"] for spec in self.registry.specs()
                }
                if unknown_tools:
                    raise ValueError(
                        "Intent configuration references unregistered tools: "
                        + ", ".join(sorted(unknown_tools))
                    )

        self.provider = provider if provider is not None else build_provider(config)
        self.history = history if history is not None else build_history_store(config)
        self.roles = dict(getattr(config, "roles", {}) or {})
        self.normalizer = normalizer
        self.audit = audit
        self.normalizer_log = normalizer_log
        self.intent_threshold = getattr(config, "intent_threshold", 0.55)
        self.intent_strategy = intent_strategy
        self.intent_prompt = intent_prompt or (
            "Classify the user's message into one of the listed intents. "
            "Return only JSON with the keys intent and confidence. "
            "Use intent \"unknown\" when none fit.\n\n"
            "Registered intents:\n{intents}"
        )
        self.system_prompt = resolve_prompt(
            config.system_prompt,
            config.system_prompt_extra,
            file_path=getattr(config, "system_prompt_file", None),
        )
        self._session_locks = [threading.RLock() for _ in range(64)]

    # -----------------------------------------------------------------
    @classmethod
    def from_config(cls, config: ChatbotConfig, **kwargs) -> "Chatbot":
        """
        Build a Chatbot, wiring up the normalizer, intents, and loggers
        automatically when the corresponding flags are on.

        Optional kwargs:
            normalizer, audit, normalizer_log, provider, registry, history, intents
        Any explicit kwarg overrides auto-wiring.
        """
        if not config.enabled:
            return cls(config, **kwargs)

        # Auto-wire the normalizer if requested and not supplied.
        if config.use_normalizer and "normalizer" not in kwargs:
            try:
                from mim_ai.normalizer import Normalizer, NormalizerConfig
                kwargs["normalizer"] = Normalizer.from_config(NormalizerConfig())
            except Exception as exc:            # noqa: BLE001
                warnings.warn(f"Failed to initialize chatbot normalizer: {exc}", UserWarning)

        # Auto-wire intents if requested and not supplied.
        if config.use_intents and "intents" not in kwargs:
            try:
                from mim_ai.intents import IntentRegistry
                registry = IntentRegistry()
                intent_path = getattr(config, "intent_path", None)
                if intent_path:
                    registry.load_yaml(intent_path)
                kwargs["intents"] = registry
            except Exception as exc:            # noqa: BLE001
                warnings.warn(f"Failed to initialize chatbot intents: {exc}", UserWarning)

        # Auto-wire loggers if requested and not supplied.
        if config.use_audit_log and "audit" not in kwargs:
            try:
                from mim_ai.audit import AuditLogger, AuditConfig
                kwargs["audit"] = AuditLogger(AuditConfig(enabled=True))
            except Exception as exc:            # noqa: BLE001
                warnings.warn(f"Failed to initialize audit logger: {exc}", UserWarning)

        if config.use_normalizer_log and "normalizer_log" not in kwargs:
            try:
                from mim_ai.audit import NormalizerLogger, NormalizerLogConfig
                kwargs["normalizer_log"] = NormalizerLogger(NormalizerLogConfig(enabled=True))
            except Exception as exc:            # noqa: BLE001
                warnings.warn(f"Failed to initialize normalizer logger: {exc}", UserWarning)

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
        lock = self._session_locks[hash(session_id) % len(self._session_locks)]
        with lock:
            return self._chat_turn(message, session_id=session_id, user_ref=user_ref)

    async def achat(
        self,
        message: str,
        *,
        session_id: str = "default",
        user_ref: str | None = None,
    ) -> ChatReply:
        """Run a blocking chat turn without blocking the asyncio event loop."""
        return await asyncio.to_thread(
            self.chat, message, session_id=session_id, user_ref=user_ref,
        )

    def _chat_turn(
        self,
        message: str,
        *,
        session_id: str,
        user_ref: str | None,
    ) -> ChatReply:
        if not self.enabled:
            return ChatReply(text="", trace_id="")

        t0 = time.perf_counter()
        trace_id = f"chat_{uuid.uuid4().hex[:12]}"

        # --- 1. Normalize the user message ---------------------------
        user_text = message
        if self.config.use_normalizer and self.normalizer is not None:
            user_text, norm_report = self.normalizer.normalize(
                message, return_report=True,
            )
            # Feed the normalizer log if wired.
            if self.config.use_normalizer_log and self.normalizer_log is not None:
                self.normalizer_log.emit(
                    trace_id=trace_id, user_ref=user_ref,
                    jargon_used=getattr(norm_report, "jargon_used", {}),
                    jargon_skipped=getattr(norm_report, "jargon_skipped", {}),
                    arabizi_used=getattr(norm_report, "dictionary_hits", 0),
                    arabizi_oov=int(getattr(norm_report, "oov_arabizi", False)),
                    rules_applied=getattr(norm_report, "rule_applications", 0),
                )

        intent_name = None
        intent_score = 0.0
        matched_intent = None
        messages = self._build_messages(session_id, user_text)

        tool_calls_made: list[dict] = []
        final_text = ""
        usage: dict = {}
        error_message: str | None = None

        try:
            if self.config.use_intents and self.intents is not None:
                match, score = self.intents.match_rule_based(
                    user_text, threshold=self.intent_threshold
                )
                if self.intent_strategy == "llm":
                    match, score = self.intents.match_llm(
                        user_text, self.provider, self.intent_prompt
                    )
                elif self.intent_strategy == "hybrid" and match is None:
                    match, score = self.intents.match_llm(
                        user_text, self.provider, self.intent_prompt
                    )
                if match is not None:
                    matched_intent = match
                    intent_name, intent_score = match.name, float(score)

            allowed_tool_names = None
            if (
                self.config.use_intents
                and self.intents is not None
                and self.intents.has_tool_restrictions
            ):
                allowed_tool_names = set(
                    matched_intent.tool_names or []
                ) if matched_intent is not None else set()

            while True:
                remaining_tool_calls = (
                    self.config.max_tool_calls - len(tool_calls_made)
                )
                tool_schemas = (
                    self.registry.specs(allowed_tool_names)
                    if (
                        self.config.enable_tools
                        and self.registry
                        and allowed_tool_names != set()
                        and remaining_tool_calls > 0
                    )
                    else None
                )
                response = self.provider.chat(messages, tools=tool_schemas)
                usage = response.usage or usage

                if not response.tool_calls:
                    final_text = response.content or ""
                    if not final_text.strip():
                        raise LLMError("LLM returned an empty text response")
                    break

                if not self.config.enable_tools or not self.registry:
                    raise LLMError(
                        "LLM requested tools, but chatbot tools are disabled "
                        "or no tools are registered"
                    )
                if (
                    len(tool_calls_made) + len(response.tool_calls)
                    > self.config.max_tool_calls
                ):
                    raise LLMError(
                        "LLM requested more tool calls than "
                        "chatbot.max_tool_calls allows"
                    )

                for call in response.tool_calls:
                    if call.name not in self.registry:
                        raise LLMError(f"LLM requested unregistered tool {call.name!r}")
                    if (
                        allowed_tool_names is not None
                        and call.name not in allowed_tool_names
                    ):
                        raise LLMError(
                            f"Tool {call.name!r} is not allowed for intent "
                            f"{intent_name or 'unknown'}"
                        )

                # Append the assistant's tool-call message verbatim.
                messages.append(self._assistant_tool_msg(response.tool_calls))

                # Execute each tool and append its result.
                for call in response.tool_calls:
                    try:
                        result = self.registry.execute(
                            call.name,
                            call.arguments,
                            allowed_names=allowed_tool_names,
                        )
                    except (TypeError, ValueError, PermissionError) as exc:
                        raise LLMError(f"Invalid tool call: {exc}") from exc
                    tool_calls_made.append({
                        "name": call.name, "args": call.arguments,
                    })
                    messages.append({
                        "role":         "tool",
                        "tool_call_id": call.id,
                        "content":      result,
                    })
        except LLMError as e:
            error_message = str(e)
            final_text = ""

        # --- 5. Persist history --------------------------------------
        if final_text:
            self.history.append(session_id, {"role": "user", "content": user_text})
            self.history.append(session_id, {"role": "assistant", "content": final_text})

        duration_ms = int((time.perf_counter() - t0) * 1000)

        # --- 5. Audit log --------------------------------------------
        if self.config.use_audit_log and self.audit is not None:
            status = "ok" if final_text else "error"
            extra = {
                "session_id":  session_id,
                "model":       self.config.llm_model,
                "intent":      intent_name,
                "intent_score": intent_score,
                "tool_calls":  [t["name"] for t in tool_calls_made],
                "usage":       usage,
            }
            if error_message is not None:
                extra["error"] = error_message
            self.audit.emit(
                event="chat",
                trace_id=trace_id,
                user_ref=user_ref,
                input_text=message,
                output_text=final_text,
                duration_ms=duration_ms,
                status=status,
                extra=extra,
            )

        return ChatReply(
            text=final_text,
            tool_calls=tool_calls_made,
            trace_id=trace_id,
            duration_ms=duration_ms,
            usage=usage,
            intent=intent_name,
            intent_score=intent_score,
            error=error_message,
        )

    def close(self) -> None:
        close = getattr(self.history, "close", None)
        if callable(close):
            close()

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