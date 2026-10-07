"""
LLM provider abstraction.

Everything talks OpenAI's /chat/completions schema. This is the de-facto
standard: OpenAI, MNTRA, Ollama (with OLLAMA_OPENAI_COMPAT=1), LM Studio,
vLLM, Together, Groq, Fireworks all speak it. One adapter, many backends.

To add a truly custom provider (e.g. a proprietary SDK), subclass
`LLMProvider` and implement `.chat()`. That's the whole contract.
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Protocol

from .config import ChatbotConfig


# ---------------------------------------------------------------------------
# Neutral response types — what the chatbot consumes.
# ---------------------------------------------------------------------------
@dataclass
class ToolCall:
    id:        str
    name:      str
    arguments: dict


@dataclass
class LLMResponse:
    content:    str | None                  # natural-language reply
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw:        dict | None = None          # provider payload, for logging
    usage:      dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Protocol — the only thing the chatbot depends on.
# ---------------------------------------------------------------------------
class LLMProvider(Protocol):
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse: ...


# ---------------------------------------------------------------------------
# OpenAI-compatible provider (works with the whole ecosystem).
# ---------------------------------------------------------------------------
class OpenAICompatibleProvider:
    """
    Minimal HTTP client for any OpenAI-compatible /chat/completions.

    No `openai` SDK dependency — uses stdlib urllib so the package
    stays dependency-free. If you need streaming, swap in `httpx` or
    the official SDK; the contract (`.chat() -> LLMResponse`) stays
    the same.
    """

    # Preset endpoints for well-known providers. Override via
    # ChatbotConfig.llm_endpoint if yours isn't here.
    PRESETS = {
        "openai": "https://api.openai.com/v1",
        "ollama": "http://localhost:11434/v1",
        "mntra":  "https://api.mntra.ma/v1",
        "lmstudio": "http://localhost:1234/v1",
    }

    def __init__(self, config: ChatbotConfig) -> None:
        self.config = config
        self.endpoint = (
            config.llm_endpoint
            or self.PRESETS.get(config.llm_provider, "")
        ).rstrip("/")
        if not self.endpoint:
            raise ValueError(
                f"No endpoint for provider {config.llm_provider!r}. "
                f"Set ChatbotConfig.llm_endpoint explicitly."
            )
        self.api_key = os.environ.get(config.llm_api_key_env, "")

    # -----------------------------------------------------------------
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        body: dict[str, Any] = {
            "model":       self.config.llm_model,
            "messages":    messages,
            "temperature": self.config.llm_temperature,
            "max_tokens":  self.config.llm_max_tokens,
            **self.config.llm_extra_params,
        }
        if tools and self.config.enable_tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        req = urllib.request.Request(
            url=f"{self.endpoint}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
                **self.config.llm_extra_headers,
            },
        )

        timeout_s = self.config.llm_timeout_ms / 1000
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise LLMError(f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}")
        except urllib.error.URLError as e:
            raise LLMError(f"Network error: {e.reason}")

        return self._parse(payload)

    # -----------------------------------------------------------------
    def _parse(self, payload: dict) -> LLMResponse:
        try:
            choice = payload["choices"][0]
            msg = choice["message"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"Unexpected payload shape: {e}") from e

        tool_calls: list[ToolCall] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(
                id=tc.get("id", ""),
                name=fn.get("name", ""),
                arguments=args,
            ))

        return LLMResponse(
            content=msg.get("content"),
            tool_calls=tool_calls,
            raw=payload,
            usage=payload.get("usage", {}),
        )


class LLMError(RuntimeError):
    """Raised by any provider on failure. Chatbot catches and logs it."""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def build_provider(config: ChatbotConfig) -> LLMProvider:
    """
    Return an LLMProvider for the given config.

    Currently every preset routes through the OpenAI-compatible client.
    Add new classes here when you need a non-HTTP provider (e.g. a
    local llama.cpp binding).
    """
    return OpenAICompatibleProvider(config)