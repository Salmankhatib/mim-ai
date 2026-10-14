import pytest

from mim_ai.intents import Intent, IntentRegistry


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
