"""Chatbot for mim_ai — config-first, LLM-agnostic, tool-enabled."""

__all__ = [
    "ChatbotConfig",
    "Chatbot", "ChatReply", "HistoryStore", "InMemoryHistoryStore",
    "LLMProvider", "LLMResponse", "ToolCall", "LLMError",
    "ToolRegistry", "tool", "get_default_registry", "IntentConfig",
]


def __getattr__(name: str):
    if name == "ChatbotConfig":
        from .config import ChatbotConfig
        return ChatbotConfig
    if name in {"Chatbot", "ChatReply", "HistoryStore", "InMemoryHistoryStore"}:
        from .chatbot import Chatbot, ChatReply, HistoryStore, InMemoryHistoryStore
        return {
            "Chatbot": Chatbot,
            "ChatReply": ChatReply,
            "HistoryStore": HistoryStore,
            "InMemoryHistoryStore": InMemoryHistoryStore,
        }[name]
    if name in {"LLMProvider", "LLMResponse", "ToolCall", "LLMError"}:
        from .llm import LLMProvider, LLMResponse, ToolCall, LLMError
        return {
            "LLMProvider": LLMProvider,
            "LLMResponse": LLMResponse,
            "ToolCall": ToolCall,
            "LLMError": LLMError,
        }[name]
    if name in {"ToolRegistry", "tool", "get_default_registry"}:
        from .tools import ToolRegistry, tool, get_default_registry
        return {
            "ToolRegistry": ToolRegistry,
            "tool": tool,
            "get_default_registry": get_default_registry,
        }[name]
    if name == "IntentConfig":
        from ..intents import IntentConfig
        return IntentConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")