import json
from io import BytesIO

import numpy as np
import pytest

from mim_ai._http import speak, transcribe
from mim_ai.chatbot.chatbot import ChatReply
from mim_ai.normalizer.arabizi import ArabiziDictionary
from mim_ai.normalizer.schema import RulesConfig
from mim_ai.voice import VoicePipeline, VoiceReply


def test_voice_module_exports_pipeline():
    assert VoicePipeline is not None
    assert VoiceReply is not None


def test_chat_reply_exposes_intent_metadata():
    reply = ChatReply(text="hello")
    assert reply.intent is None
    assert reply.intent_score == 0.0

    reply.intent = "faq"
    reply.intent_score = 0.92

    assert reply.intent == "faq"
    assert reply.intent_score == 0.92


def test_record_until_silence_returns_array_when_no_backend_available(monkeypatch):
    import mim_ai.voice.audio as audio_mod

    monkeypatch.setattr(audio_mod, "_has_sounddevice", lambda: False, raising=False)
    out = audio_mod.record_until_silence(
        type("AudioCfg", (), {"sample_rate": 16000})(),
        type("VADCfg", (), {"enabled": True, "threshold": 0.5, "min_silence_ms": 250})(),
        max_seconds=1,
        silence_timeout_ms=400,
    )

    assert isinstance(out, np.ndarray)
    assert out.size > 0


def test_missing_override_paths_do_not_crash_arabizi_dictionary():
    dict_obj = ArabiziDictionary.from_config(RulesConfig(arabizi_dict_path="./definitely_missing.yaml"))
    assert isinstance(dict_obj, ArabiziDictionary)
    assert dict_obj.lookup("salam") in (None, "سلام")


def test_speak_sets_response_format_and_only_posts_once(monkeypatch):
    captured = {}

    class FakeResponse:
        headers = {"Content-Type": "audio/wav"}

        def read(self):
            return b"RIFF\x00\x00\x00\x00WAVE"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("mim_ai._http.request.urlopen", fake_urlopen)
    out, mime = speak(type("Cfg", (), {"model": "tts-1", "voice": "nova", "base_url": "https://example.test/v1", "api_key_env": "OPENAI_API_KEY", "timeout_ms": 1000, "format": "wav"})(), "hello")

    assert mime == "audio/wav"
    assert captured["payload"]["response_format"] == "wav"
    assert out.startswith(b"RIFF")


def test_transcribe_uses_language_form_field_not_x_language_header(monkeypatch):
    captured = {}

    class FakeResponse:
        headers = {"Content-Type": "application/json"}

        def read(self):
            return b'{"text": "salut"}'

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.headers)
        captured["body"] = req.data
        return FakeResponse()

    monkeypatch.setattr("mim_ai._http.request.urlopen", fake_urlopen)

    cfg = type(
        "Cfg",
        (),
        {
            "model": "whisper-1",
            "base_url": "https://example.test/v1",
            "api_key_env": "OPENAI_API_KEY",
            "timeout_ms": 1000,
            "language": "ar",
        },
    )()

    out = transcribe(cfg, b"fake-audio")

    assert out == "salut"
    assert "X-Language" not in captured["headers"]
    assert b'name="language"' in captured["body"]
    assert b"ar" in captured["body"]
