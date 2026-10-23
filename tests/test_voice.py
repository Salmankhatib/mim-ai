import json
from pathlib import Path

import numpy as np
import pytest

from mim_ai._http import speak, transcribe
from mim_ai.chatbot.chatbot import ChatReply
from mim_ai.config import MimConfig, VADConfig, VoiceSection
from mim_ai.normalizer.arabizi import ArabiziDictionary
from mim_ai.normalizer.schema import RulesConfig
from mim_ai.voice import VoicePipeline, VoiceReply


def test_voice_module_exports_pipeline():
    assert VoicePipeline is not None
    assert VoiceReply is not None


def test_voice_config_exposes_usable_energy_vad_defaults():
    cfg = MimConfig.from_dict({"voice": {"enabled": True}})

    assert cfg.voice.vad.enabled is True
    assert cfg.voice.vad.threshold == 0.015
    assert cfg.voice.vad.min_silence_ms == 700
    assert cfg.voice.vad.start_timeout_ms == 10000


def test_voice_config_validates_vad_and_supports_legacy_silence_timeout():
    cfg = VoiceSection.from_mapping({"silence_timeout_ms": 900})
    assert cfg.vad.min_silence_ms == 900

    configured_vad_wins = VoiceSection.from_mapping(
        {"silence_timeout_ms": 900, "vad": {"min_silence_ms": 400}}
    )
    assert configured_vad_wins.vad.min_silence_ms == 400

    with pytest.raises(ValueError, match="threshold"):
        VADConfig(threshold=0)


def test_chat_reply_exposes_intent_metadata():
    reply = ChatReply(text="hello")
    assert reply.intent is None
    assert reply.intent_score == 0.0

    reply.intent = "faq"
    reply.intent_score = 0.92

    assert reply.intent == "faq"
    assert reply.intent_score == 0.92


def test_record_until_silence_requires_audio_backend(monkeypatch):
    import mim_ai.voice.audio as audio_mod

    def unavailable():
        raise audio_mod.AudioError("sounddevice is missing")

    monkeypatch.setattr(audio_mod, "_load_sounddevice", unavailable)
    with pytest.raises(audio_mod.AudioError, match="sounddevice is missing"):
        audio_mod.record_until_silence(
            type("AudioCfg", (), {"sample_rate": 16000})(),
            type("VADCfg", (), {"enabled": True})(),
            max_seconds=1,
        )


def test_playback_surfaces_device_errors(monkeypatch):
    import mim_ai.voice.audio as audio_mod

    class FakeSoundDevice:
        @staticmethod
        def play(*args, **kwargs):
            raise RuntimeError("speaker unavailable")

    monkeypatch.setattr(audio_mod, "_load_sounddevice", lambda: FakeSoundDevice)
    with pytest.raises(audio_mod.AudioError, match="speaker unavailable"):
        audio_mod.play(np.ones(20, dtype=np.float32), 16000)


def test_energy_vad_records_speech_with_preroll_until_silence(monkeypatch):
    import mim_ai.voice.audio as audio_mod

    blocks = [
        0.001,  # pre-roll
        0.02,
        0.03,   # speech threshold reached
        0.001,
        0.001,  # silence threshold reached
    ]

    class FakeStream:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, frames):
            value = blocks.pop(0)
            return np.full((frames, 1), value, dtype=np.float32), False

    class FakeSoundDevice:
        InputStream = FakeStream

    monkeypatch.setattr(audio_mod, "_load_sounddevice", lambda: FakeSoundDevice)

    result = audio_mod.record_until_silence(
        type("AudioCfg", (), {"sample_rate": 1000, "input_device": None})(),
        type(
            "VADCfg",
            (),
            {
                "enabled": True,
                "threshold": 0.01,
                "frame_ms": 20,
                "min_speech_ms": 40,
                "min_silence_ms": 40,
                "start_timeout_ms": 200,
                "pre_roll_ms": 20,
            },
        )(),
        max_seconds=1,
    )

    assert result is not None
    assert result.shape == (100,)
    assert np.allclose(result[:20], 0.001)
    assert np.allclose(result[20:60], np.repeat([0.02, 0.03], 20))


def test_energy_vad_returns_none_when_no_speech(monkeypatch):
    import mim_ai.voice.audio as audio_mod

    class FakeStream:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, frames):
            return np.zeros((frames, 1), dtype=np.float32), False

    class FakeSoundDevice:
        InputStream = FakeStream

    monkeypatch.setattr(audio_mod, "_load_sounddevice", lambda: FakeSoundDevice)
    result = audio_mod.record_until_silence(
        type("AudioCfg", (), {"sample_rate": 1000})(),
        type(
            "VADCfg",
            (),
            {
                "enabled": True,
                "threshold": 0.01,
                "frame_ms": 20,
                "min_speech_ms": 40,
                "min_silence_ms": 40,
                "start_timeout_ms": 60,
                "pre_roll_ms": 20,
            },
        )(),
        max_seconds=1,
    )

    assert result is None


def test_pipeline_reports_no_speech_without_calling_stt(monkeypatch):
    import importlib

    from mim_ai.config import STTConfig, TTSConfig, VoiceSection
    from mim_ai.voice.pipeline import VoicePipeline

    pipeline_module = importlib.import_module("mim_ai.voice.pipeline")
    monkeypatch.setattr(pipeline_module, "record_until_silence", lambda *args, **kwargs: None)

    class NeverTranscribe:
        def __init__(self, config):
            self.config = config

        def transcribe(self, audio, sample_rate):
            pytest.fail("STT must not run when VAD detects no speech")

    monkeypatch.setattr(pipeline_module, "STT", NeverTranscribe)

    result = VoicePipeline(VoiceSection(), STTConfig(), TTSConfig()).listen_and_reply(
        play_audio=False
    )

    assert result.status == "no_speech"
    assert result.transcript == ""
    assert result.trace_id


def test_missing_dictionary_override_path_is_reported():
    with pytest.raises(FileNotFoundError, match="YAML file does not exist"):
        ArabiziDictionary.from_config(
            RulesConfig(arabizi_dict_path="./definitely_missing.yaml")
        )


def test_default_and_custom_skip_lists_keep_darija_mappable():
    dict_obj = ArabiziDictionary.from_config(
        RulesConfig(
            skip_words_path=str(
                Path(__file__).resolve().parents[1] / "darija" / "skip_words.yaml"
            )
        )
    )

    assert dict_obj.lookup("salam") == "salam"
    assert dict_obj.lookup("bghit") == "bghit"
    assert dict_obj.lookup("3la") == "3la"
    assert dict_obj.lookup("la") is None
    assert dict_obj.is_skipped("bonjour")
    assert dict_obj.lookup("سلم") == "سلام"


def test_speak_sets_response_format_and_only_posts_once(monkeypatch):
    captured = {"requests": 0}

    class FakeResponse:
        headers = {"Content-Type": "application/octet-stream"}

        def read(self):
            return b"RIFF\x00\x00\x00\x00WAVE"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req, timeout=None):
        captured["requests"] += 1
        captured["url"] = req.full_url
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("mim_ai._http.request.urlopen", fake_urlopen)
    out, mime = speak(type("Cfg", (), {"model": "tts-1", "voice": "nova", "base_url": "https://example.test/v1", "api_key_env": "OPENAI_API_KEY", "timeout_ms": 1000, "format": "wav"})(), "hello")

    assert mime == "audio/wav"
    assert captured["requests"] == 1
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


def test_http_helpers_send_bearer_api_key(monkeypatch):
    from mim_ai._http import _headers

    monkeypatch.setenv("MIM_TEST_API_KEY", "secret-test-key")
    cfg = type("Cfg", (), {"api_key_env": "MIM_TEST_API_KEY"})()

    assert _headers(cfg)["Authorization"] == "Bearer secret-test-key"


def test_http_helper_retries_429_and_respects_retry_after(monkeypatch):
    import urllib.error
    import urllib.request
    from io import BytesIO

    from mim_ai._http import open_with_retries

    attempts = []
    delays = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req, timeout=None):
        attempts.append(timeout)
        if len(attempts) == 1:
            raise urllib.error.HTTPError(
                req.full_url, 429, "rate limited", {"Retry-After": "0"}, BytesIO()
            )
        return FakeResponse()

    monkeypatch.setattr("mim_ai._http.request.urlopen", fake_urlopen)
    monkeypatch.setattr("mim_ai._http.time.sleep", delays.append)

    with open_with_retries(
        urllib.request.Request("https://example.test"),
        timeout=1,
        max_retries=1,
        backoff_ms=100,
    ):
        pass

    assert attempts == [1, 1]
    assert delays == [0.0]


def test_voice_pipeline_honors_component_flags(monkeypatch):
    import mim_ai.voice.pipeline as pipeline_module
    from mim_ai.config import STTConfig, TTSConfig, VoiceSection

    monkeypatch.setattr(
        pipeline_module, "record_until_silence",
        lambda *args, **kwargs: np.ones(20, dtype=np.float32),
    )

    class FakeSTT:
        def __init__(self, config):
            self.config = config

        def transcribe(self, audio, sample_rate):
            return "salam"

    class FakeTTS:
        def __init__(self, config):
            self.config = config

        def synthesize(self, text):
            pytest.fail("TTS must not run when disabled")

    class NeverChat:
        def chat(self, *args, **kwargs):
            pytest.fail("chatbot must not run when voice.use_chatbot is false")

    monkeypatch.setattr(pipeline_module, "STT", FakeSTT)
    monkeypatch.setattr(pipeline_module, "TTS", FakeTTS)
    pipeline = VoicePipeline(
        VoiceSection(use_chatbot=False),
        STTConfig(enabled=True),
        TTSConfig(enabled=False),
        chatbot=NeverChat(),
    )

    result = pipeline.listen_and_reply(play_audio=False)

    assert result.transcript == "salam"
    assert result.reply_text == ""
    assert result.audio is None
    assert result.status == "transcribed"


def test_voice_pipeline_returns_text_without_tts_when_tts_disabled(monkeypatch):
    import mim_ai.voice.pipeline as pipeline_module
    from mim_ai.config import STTConfig, TTSConfig, VoiceSection

    monkeypatch.setattr(
        pipeline_module, "record_until_silence",
        lambda *args, **kwargs: np.ones(20, dtype=np.float32),
    )
    monkeypatch.setattr(
        pipeline_module, "STT",
        lambda cfg: type(
            "FakeSTT", (), {
                "config": cfg,
                "transcribe": lambda self, audio, sample_rate: "salam",
            },
        )(),
    )

    class FakeTTS:
        def __init__(self, config):
            self.config = config

        def synthesize(self, text):
            pytest.fail("TTS must not run when disabled")

    monkeypatch.setattr(pipeline_module, "TTS", FakeTTS)
    pipeline = VoicePipeline(
        VoiceSection(),
        STTConfig(),
        TTSConfig(enabled=False),
        chatbot=type(
            "FakeChatbot", (), {
                "chat": lambda self, *args, **kwargs: ChatReply(
                    text="reply", tool_calls=[],
                ),
            },
        )(),
    )

    result = pipeline.listen_and_reply(play_audio=False)

    assert result.reply_text == "reply"
    assert result.audio is None


def test_voice_pipeline_fails_before_recording_when_stt_disabled(monkeypatch):
    import mim_ai.voice.pipeline as pipeline_module
    from mim_ai.config import STTConfig, TTSConfig, VoiceSection

    monkeypatch.setattr(
        pipeline_module, "record_until_silence",
        lambda *args, **kwargs: pytest.fail("must not record when STT is disabled"),
    )

    pipeline = VoicePipeline(VoiceSection(), STTConfig(enabled=False), TTSConfig())

    with pytest.raises(RuntimeError, match="stt.enabled is false"):
        pipeline.listen_and_reply()
