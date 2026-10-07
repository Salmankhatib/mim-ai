"""
Tool registry.

A tool is a plain Python function with a decorator that describes its
signature. The registry knows how to convert those decorators into
OpenAI tool schemas, and how to dispatch calls by name.

    from mim_ai.chatbot import tool

    @tool("get_weather", "Return the weather for a city.",
          params={"city": {"type": "string", "description": "City name"}})
    def get_weather(city: str) -> str:
        return f"Sunny in {city}, 24°C"

The function's return value is stringified and sent back to the LLM
as the tool result. Raise an exception to signal a tool error.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolSpec:
    name:        str
    description: str
    params:      dict[str, dict]          # {"arg_name": {"type": ..., ...}}
    fn:          Callable[..., Any]
    required:    list[str]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool {spec.name!r} already registered")
        self._tools[spec.name] = spec

    def specs(self) -> list[dict]:
        """Render to OpenAI's tool schema format."""
        out = []
        for t in self._tools.values():
            out.append({
                "type": "function",
                "function": {
                    "name":        t.name,
                    "description": t.description,
                    "parameters": {
                        "type":       "object",
                        "properties": t.params,
                        "required":   t.required,
                    },
                },
            })
        return out

    def execute(self, name: str, arguments: dict) -> str:
        """Run a tool. Returns a string; raises if the tool is unknown."""
        spec = self._tools.get(name)
        if spec is None:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = spec.fn(**arguments)
        except TypeError as e:
            return json.dumps({"error": f"Bad arguments: {e}"})
        except Exception as e:                     # noqa: BLE001
            return json.dumps({"error": f"{type(e).__name__}: {e}"})
        if not isinstance(result, str):
            result = json.dumps(result, ensure_ascii=False)
        return result

    def __bool__(self) -> bool:
        return bool(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# ---------------------------------------------------------------------------
# The decorator — the only thing a developer needs to touch.
# ---------------------------------------------------------------------------
def tool(
    name: str,
    description: str,
    params: dict[str, dict] | None = None,
    required: list[str] | None = None,
    registry: ToolRegistry | None = None,
):
    """
    Register a function as an LLM tool.

    Usage:
        @tool("get_time", "Return current time in a city.",
              params={"city": {"type": "string"}})
        def get_time(city: str) -> str: ...

    If `registry` is None, the tool attaches to the default registry
    (see `get_default_registry()`), which the Chatbot uses when none
    is passed explicitly. Pass `registry=` to keep tools scoped.
    """
    params = params or {}
    required = required if required is not None else list(params.keys())

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        reg = registry or get_default_registry()
        reg.register(ToolSpec(
            name=name, description=description,
            params=params, fn=fn, required=required,
        ))
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Default registry — one per process, used when no registry is provided.
# ---------------------------------------------------------------------------
_DEFAULT: ToolRegistry | None = None


def get_default_registry() -> ToolRegistry:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = ToolRegistry()
    return _DEFAULT