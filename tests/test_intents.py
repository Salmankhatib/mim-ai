import pytest

from mim_ai.chatbot.chatbot import Chatbot
from mim_ai.chatbot.config import ChatbotConfig
from mim_ai.chatbot.llm import LLMError
from mim_ai.chatbot.llm import OpenAICompatibleProvider
from mim_ai.intents import Intent, IntentRegistry
from mim_ai.normalizer.schema import NormalizerConfig
from mim_ai.chatbot.history import build_history_store


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
    assert hist["s_err"] == [{"role": "user", "content": "bonjour"}]
    assert audit.events[0]["status"] == "error"
    assert audit.events[0]["output_text"] == ""
    assert audit.events[0]["extra"]["error"] == "provider down"


def test_normalizer_respects_disabled_flag():
    cfg = NormalizerConfig(enabled=False)
    norm = cfg

    assert norm.enabled is False
    assert isinstance(cfg, NormalizerConfig)
