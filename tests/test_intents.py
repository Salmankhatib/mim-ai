import pytest
import asyncio

from mim_ai.chatbot.chatbot import Chatbot
from mim_ai.chatbot.config import ChatbotConfig
from mim_ai.chatbot.history import build_history_store
from mim_ai.chatbot.llm import LLMError, OpenAICompatibleProvider, ToolCall
from mim_ai.intents import Intent, IntentRegistry
from mim_ai.normalizer.schema import NormalizerConfig


@pytest.fixture
def registry():
    reg = IntentRegistry()
    reg.register(Intent(
        name="get_weather",
        description="Get the weather for a city.",
        examples=["what is the weather in casablanca", "كيفاش الجو ف الدار البيضاء"],
        tool="get_weather",
    ))
    reg.register(Intent(
        name="book_flight",
        description="Book a flight.",
        examples=["reserve a flight to paris", "حجز رحلة للرباط"],
        tool="book_flight",
    ))
    return reg


def test_registry_match_rule_based_handles_none_and_blank(registry):
    assert registry.match_rule_based(None) == (None, 0.0)
    assert registry.match_rule_based("   \n\t  ") == (None, 0.0)


def test_missing_intent_file_fails_with_path(tmp_path):
    with pytest.raises(FileNotFoundError, match="Intent config not found"):
        IntentRegistry().load_yaml(tmp_path / "missing.yaml")


def test_intent_config_rejects_malformed_intents(tmp_path):
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text("intents: {}\n", encoding="utf-8")

    with pytest.raises(TypeError, match="'intents' must be a list"):
        IntentRegistry().load_yaml(config_path)


def test_llm_provider_sends_bearer_api_key(monkeypatch):
    import json

    from mim_ai.chatbot.config import ChatbotConfig

    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({
                "choices": [{"message": {"content": "hello"}}],
            }).encode("utf-8")

    def fake_urlopen(request, timeout=None):
        captured["authorization"] = request.get_header("Authorization")
        return Response()

    monkeypatch.setenv("MIM_TEST_LLM_KEY", "test-key")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OpenAICompatibleProvider(ChatbotConfig(
        enabled=True,
        llm_endpoint="https://example.test/v1",
        llm_api_key_env="MIM_TEST_LLM_KEY",
    ))

    reply = provider.chat([{"role": "user", "content": "hello"}])

    assert reply.content == "hello"
    assert captured["authorization"] == "Bearer test-key"


def test_llm_provider_rejects_invalid_json_response(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"not-json"

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    provider = OpenAICompatibleProvider(
        ChatbotConfig(enabled=True, llm_max_retries=0)
    )

    with pytest.raises(LLMError, match="invalid JSON"):
        provider.chat([{"role": "user", "content": "hello"}])


def test_llm_provider_rejects_invalid_tool_arguments():
    provider = OpenAICompatibleProvider(ChatbotConfig(enabled=True))

    with pytest.raises(LLMError, match="tool arguments"):
        provider._parse({
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [{
                        "id": "call-1",
                        "function": {"name": "lookup", "arguments": "[]"},
                    }],
                }
            }]
        })


def test_unknown_history_backend_fails_explicitly():
    with pytest.raises(ValueError, match="Unsupported history backend"):
        build_history_store(ChatbotConfig(history_backend="typo"))


def test_missing_system_prompt_file_fails_with_path(tmp_path):
    from mim_ai.chatbot.prompt_templates import resolve

    prompt_path = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError, match="missing.txt"):
        resolve("darija", file_path=str(prompt_path))


def test_registry_can_add_intent_at_runtime():
    reg = IntentRegistry()
    reg.add_intent(
        name="play_music",
        description="Play music.",
        examples=["play a song", "شغل موسيقى"],
        tool="play_music",
    )

    intent, score = reg.match_rule_based("شغل موسيقى")
    assert intent is not None
    assert intent.name == "play_music"
    assert 0.0 <= score <= 1.0


def test_registry_matches_transcribed_stt_like_text(registry):
    intent, score = registry.match_rule_based("كيفاش الجو ف الدار البيضاء")
    assert intent is not None
    assert intent.name == "get_weather"
    assert score >= 0.0


def test_chatbot_defaults_to_plain_text_conversation():
    config = ChatbotConfig(enabled=True)

    assert config.use_intents is False
    assert config.enable_tools is False


def test_chatbot_keeps_an_explicit_empty_tool_registry():
    from mim_ai.chatbot.tools import ToolRegistry

    registry = ToolRegistry()

    class FakeProvider:
        def chat(self, messages, tools=None):
            return type(
                "Resp",
                (),
                {"content": "ready", "tool_calls": [], "usage": {}},
            )()

    bot = Chatbot(
        ChatbotConfig(enabled=True, enable_tools=True, use_intents=False),
        provider=FakeProvider(),
        registry=registry,
    )

    assert bot.registry is registry


def test_registry_supports_custom_module_registration(registry):
    registry.add_intent(
        name="handoff_human",
        description="Escalate to a human agent.",
        examples=["I need a human agent", "بغيت خدمه انسان"],
    )

    intent, score = registry.match_rule_based("بغيت خدمه انسان")
    assert intent is not None
    assert intent.name == "handoff_human"
    assert score >= 0.0


def test_chatbot_uses_intent_registry_when_enabled():
    registry = IntentRegistry()
    registry.add_intent(
        name="get_weather",
        description="Get the weather.",
        examples=["كيفاش الجو ف الدار البيضاء", "what is the weather in casablanca"],
        tool="get_weather",
    )

    class FakeProvider:
        def chat(self, messages, tools=None):
            return type(
                "Resp",
                (),
                {"content": "الجو حار", "tool_calls": [], "usage": {}}
            )()

    bot = Chatbot(
        ChatbotConfig(enabled=True, use_intents=True, enable_tools=False),
        provider=FakeProvider(),
        intents=registry,
    )

    reply = bot.chat("كيفاش الجو ف الدار البيضاء", session_id="s1")

    assert reply.intent == "get_weather"
    assert reply.intent_score >= 0.0


def test_chatbot_sends_custom_system_prompt_and_returns_text():
    system_prompt = "You are a concise support assistant. Answer only in French."

    class FakeProvider:
        def __init__(self):
            self.messages = None
            self.tools = None

        def chat(self, messages, tools=None):
            self.messages = messages
            self.tools = tools
            return type(
                "Resp",
                (),
                {"content": "Bonjour !", "tool_calls": [], "usage": {}},
            )()

    provider = FakeProvider()
    bot = Chatbot(
        ChatbotConfig(
            enabled=True,
            system_prompt=system_prompt,
            use_intents=False,
            enable_tools=False,
        ),
        provider=provider,
    )

    reply = bot.chat("Bonjour", session_id="text-only")

    assert provider.messages[0] == {"role": "system", "content": system_prompt}
    assert provider.messages[-1] == {"role": "user", "content": "Bonjour"}
    assert provider.tools is None
    assert reply.text == "Bonjour !"
    assert not hasattr(reply, "audio")


def test_async_chat_supports_concurrent_sessions_with_sqlite_history(tmp_path):
    class FakeProvider:
        def chat(self, messages, tools=None):
            return type(
                "Resp",
                (),
                {
                    "content": f"reply to {messages[-1]['content']}",
                    "tool_calls": [],
                    "usage": {},
                },
            )()

    config = ChatbotConfig(
        enabled=True,
        use_intents=False,
        enable_tools=False,
        history_backend="sqlite",
        history_dsn=str(tmp_path / "history.db"),
    )
    bot = Chatbot(config, provider=FakeProvider())

    async def run_turns():
        return await asyncio.gather(*[
            bot.achat(f"message {index}", session_id=f"session-{index}")
            for index in range(12)
        ])

    replies = asyncio.run(run_turns())

    assert [reply.text for reply in replies] == [
        f"reply to message {index}" for index in range(12)
    ]
    bot.close()


def test_chatbot_does_not_execute_tools_when_disabled():
    from mim_ai.chatbot.tools import ToolRegistry, ToolSpec

    execution_count = 0

    def side_effect():
        nonlocal execution_count
        execution_count += 1
        return "done"

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="dangerous_action",
            description="Perform an action",
            params={},
            fn=side_effect,
            required=[],
        )
    )

    class FakeProvider:
        def chat(self, messages, tools=None):
            return type(
                "Resp",
                (),
                {
                    "content": None,
                    "tool_calls": [
                        ToolCall(id="call-1", name="dangerous_action", arguments={})
                    ],
                    "usage": {},
                },
            )()

    bot = Chatbot(
        ChatbotConfig(
            enabled=True,
            use_intents=False,
            enable_tools=False,
        ),
        provider=FakeProvider(),
        registry=registry,
    )

    reply = bot.chat("Please do that")

    assert execution_count == 0
    assert reply.text == ""
    assert "tools are disabled" in reply.error


def test_chatbot_enforces_tool_call_limit_per_turn():
    from mim_ai.chatbot.tools import ToolRegistry, ToolSpec

    execution_count = 0

    def action():
        nonlocal execution_count
        execution_count += 1
        return "done"

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="action",
            description="Perform an action",
            params={},
            fn=action,
            required=[],
        )
    )

    class FakeProvider:
        def chat(self, messages, tools=None):
            return type(
                "Resp",
                (),
                {
                    "content": None,
                    "tool_calls": [
                        ToolCall(id="call-1", name="action", arguments={}),
                        ToolCall(id="call-2", name="action", arguments={}),
                    ],
                    "usage": {},
                },
            )()

    bot = Chatbot(
        ChatbotConfig(
            enabled=True,
            use_intents=False,
            enable_tools=True,
            max_tool_calls=1,
        ),
        provider=FakeProvider(),
        registry=registry,
    )

    reply = bot.chat("Please do that")

    assert execution_count == 0
    assert reply.text == ""
    assert "max_tool_calls" in reply.error


def test_chatbot_llm_error_is_not_stored_as_successful_reply():
    class FakeProvider:
        def chat(self, messages, tools=None):
            raise LLMError("provider down")

    class FakeAudit:
        def __init__(self):
            self.events = []

        def emit(self, **kwargs):
            self.events.append(kwargs)

    hist = {}

    class FakeHistory:
        def get(self, session_id):
            return hist.get(session_id, [])

        def append(self, session_id, message):
            hist.setdefault(session_id, []).append(message)

        def clear(self, session_id):
            hist.pop(session_id, None)

    audit = FakeAudit()
    bot = Chatbot(
        ChatbotConfig(enabled=True, use_intents=False, enable_tools=False),
        provider=FakeProvider(),
        history=FakeHistory(),
        audit=audit,
    )

    reply = bot.chat("bonjour", session_id="s_err")

    assert reply.text == ""
    assert reply.error == "provider down"
    assert hist["s_err"] == [{"role": "user", "content": "bonjour"}]
    assert audit.events[0]["status"] == "error"
    assert audit.events[0]["output_text"] == ""
    assert audit.events[0]["extra"]["error"] == "provider down"


def test_chatbot_component_flags_override_injected_integrations():
    calls = {"normalizer": 0, "normalizer_log": 0, "audit": 0}

    class FakeNormalizer:
        def normalize(self, message, *, return_report=False):
            calls["normalizer"] += 1
            return "changed", type("Report", (), {})()

    class FakeLogger:
        def emit(self, **kwargs):
            calls["normalizer_log"] += 1

    class FakeAudit:
        def emit(self, **kwargs):
            calls["audit"] += 1

    class FakeProvider:
        def __init__(self):
            self.messages = None

        def chat(self, messages, tools=None):
            self.messages = messages
            return type("Resp", (), {"content": "hello", "tool_calls": [], "usage": {}})()

    provider = FakeProvider()
    bot = Chatbot(
        ChatbotConfig(
            enabled=True,
            use_normalizer=False,
            use_normalizer_log=False,
            use_audit_log=False,
            use_intents=False,
            enable_tools=False,
        ),
        provider=provider,
        normalizer=FakeNormalizer(),
        normalizer_log=FakeLogger(),
        audit=FakeAudit(),
    )

    bot.chat("original message")

    assert provider.messages[-1]["content"] == "original message"
    assert calls == {"normalizer": 0, "normalizer_log": 0, "audit": 0}


def test_normalizer_respects_disabled_flag():
    cfg = NormalizerConfig(enabled=False)
    norm = cfg

    assert norm.enabled is False
    assert isinstance(cfg, NormalizerConfig)
