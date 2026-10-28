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
import math
import re
from collections.abc import Collection
from dataclasses import dataclass
from typing import Any, Callable

_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_JSON_TYPE_CHECKS = {
    "string": lambda value: isinstance(value, str),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "number": lambda value: isinstance(value, (int, float)) and not isinstance(
        value, bool
    ),
    "boolean": lambda value: isinstance(value, bool),
    "object": lambda value: isinstance(value, dict),
    "array": lambda value: isinstance(value, list),
    "null": lambda value: value is None,
}


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
        if not _TOOL_NAME_RE.fullmatch(spec.name):
            raise ValueError(f"Invalid tool name: {spec.name!r}")
        if spec.name in self._tools:
            raise ValueError(f"Tool {spec.name!r} already registered")
        if not callable(spec.fn):
            raise TypeError(f"Tool {spec.name!r} must have a callable function")
        if not isinstance(spec.required, list) or not all(
            isinstance(name, str) for name in spec.required
        ):
            raise TypeError(f"Tool {spec.name!r} required must be a list of names")
        if not isinstance(spec.params, dict) or not all(
            isinstance(key, str) and isinstance(value, dict)
            for key, value in spec.params.items()
        ):
            raise TypeError("Tool params must map argument names to JSON schemas")
        if len(set(spec.required)) != len(spec.required):
            raise ValueError(f"Tool {spec.name!r} has duplicate required arguments")
        unknown_required = set(spec.required) - spec.params.keys()
        if unknown_required:
            raise ValueError(
                f"Tool {spec.name!r} requires undefined arguments: "
                f"{', '.join(sorted(unknown_required))}"
            )
        self._tools[spec.name] = spec

    def specs(
        self, allowed_names: Collection[str] | None = None
    ) -> list[dict]:
        """Render to OpenAI's tool schema format."""
        selected = self._select_tools(allowed_names)
        out = []
        for t in selected:
            out.append({
                "type": "function",
                "function": {
                    "name":        t.name,
                    "description": t.description,
                    "parameters": {
                        "type":       "object",
                        "properties": t.params,
                        "required":   t.required,
                        "additionalProperties": False,
                    },
                },
            })
        return out

    def execute(
        self,
        name: str,
        arguments: dict,
        *,
        allowed_names: Collection[str] | None = None,
    ) -> str:
        """Run a tool. Returns a string; raises if the tool is unknown."""
        spec = self._tools.get(name)
        if spec is None:
            raise ValueError(f"Unknown tool: {name}")
        if allowed_names is not None and name not in allowed_names:
            raise PermissionError(f"Tool {name!r} is not allowed for this intent")
        _validate_arguments(spec, arguments)
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

    def _select_tools(
        self, allowed_names: Collection[str] | None
    ) -> list[ToolSpec]:
        if allowed_names is None:
            return list(self._tools.values())
        unknown = set(allowed_names) - self._tools.keys()
        if unknown:
            raise ValueError(
                f"Unknown tools in intent configuration: {', '.join(sorted(unknown))}"
            )
        return [
            spec for name, spec in self._tools.items() if name in allowed_names
        ]


def _validate_arguments(spec: ToolSpec, arguments: dict) -> None:
    if not isinstance(arguments, dict):
        raise TypeError("Tool arguments must be a JSON object")
    if not all(isinstance(name, str) for name in arguments):
        raise TypeError("Tool argument names must be strings")
    provided = set(arguments)
    declared = set(spec.params)
    missing = set(spec.required) - provided
    extra = provided - declared
    if missing:
        raise ValueError(
            f"Tool {spec.name!r} is missing required arguments: "
            f"{', '.join(sorted(missing))}"
        )
    if extra:
        raise ValueError(
            f"Tool {spec.name!r} received unexpected arguments: "
            f"{', '.join(sorted(extra))}"
        )
    for name, value in arguments.items():
        _validate_value(spec.name, name, value, spec.params[name])


def _validate_value(
    tool_name: str, argument_name: str, value: Any, schema: dict[str, Any]
) -> None:
    if not isinstance(schema, dict):
        raise ValueError(
            f"Tool {tool_name!r} argument {argument_name!r} has an invalid schema"
        )
    expected_type = schema.get("type")
    if expected_type is not None:
        expected_types = (
            expected_type if isinstance(expected_type, list) else [expected_type]
        )
        checks = [_JSON_TYPE_CHECKS.get(item) for item in expected_types]
        if not checks or any(check is None for check in checks):
            raise ValueError(
                f"Tool {tool_name!r} argument {argument_name!r} uses "
                f"unsupported JSON type {expected_type!r}"
            )
        if not any(check(value) for check in checks if check is not None):
            raise TypeError(
                f"Tool {tool_name!r} argument {argument_name!r} "
                f"must be {' or '.join(expected_types)}"
            )
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(
            f"Tool {tool_name!r} argument {argument_name!r} is not an allowed value"
        )
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            raise ValueError(
                f"Tool {tool_name!r} argument {argument_name!r} has an invalid object schema"
            )
        missing = set(required) - value.keys()
        extra = value.keys() - properties.keys()
        if missing or (extra and schema.get("additionalProperties") is False):
            raise ValueError(
                f"Tool {tool_name!r} argument {argument_name!r} has invalid object keys"
            )
        for key, item in value.items():
            if key in properties:
                _validate_value(
                    tool_name, f"{argument_name}.{key}", item, properties[key]
                )
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        if len(value) < schema.get("minItems", 0):
            raise ValueError(
                f"Tool {tool_name!r} argument {argument_name!r} has too few items"
            )
        if len(value) > schema.get("maxItems", float("inf")):
            raise ValueError(
                f"Tool {tool_name!r} argument {argument_name!r} has too many items"
            )
        for index, item in enumerate(value):
            _validate_value(
                tool_name, f"{argument_name}[{index}]", item, schema["items"]
            )
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ValueError(
                f"Tool {tool_name!r} argument {argument_name!r} is too short"
            )
        if len(value) > schema.get("maxLength", float("inf")):
            raise ValueError(
                f"Tool {tool_name!r} argument {argument_name!r} is too long"
            )
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ValueError(
                f"Tool {tool_name!r} argument {argument_name!r} has an invalid format"
            )
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(
                f"Tool {tool_name!r} argument {argument_name!r} must be finite"
            )
        if value < schema.get("minimum", float("-inf")):
            raise ValueError(
                f"Tool {tool_name!r} argument {argument_name!r} is below minimum"
            )
        if value > schema.get("maximum", float("inf")):
            raise ValueError(
                f"Tool {tool_name!r} argument {argument_name!r} is above maximum"
            )


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
        reg = registry if registry is not None else get_default_registry()
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