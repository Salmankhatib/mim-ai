import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from mim_ai import MimConfig, load_config
from mim_ai.voice.pipeline import VoicePipeline
from mim_ai.audit import AuditLogger, NormalizerLogger
from mim_ai.audit.backends import (
    MongoDBBackend,
    MySQLBackend,
    PostgreSQLBackend,
    create_backend,
)
from mim_ai.audit.config import AuditConfig, NormalizerLogConfig


class RecordingAdapter:
    instances = []

    def __init__(self, *, table, dsn=None, collection=None, driver=None):
        self.table = table
        self.dsn = dsn
        self.collection = collection
        self.driver = driver
        self.rows = []
        type(self).instances.append(self)

    def append(self, row):
        self.rows.append(dict(row))

    def purge_older_than(self, days):
        return 0


def test_audit_logger_accepts_database_adapter():
    RecordingAdapter.instances = []
    cfg = AuditConfig(
        enabled=True,
        backend="postgresql",
        database_url="postgresql://db.example/app",
        adapter=RecordingAdapter,
        collection="audit_events",
    )

    logger = AuditLogger(cfg)
    logger.emit(event="login", trace_id="t-1", user_ref="u_123", extra={"ok": True})

    assert len(RecordingAdapter.instances) == 1
    assert RecordingAdapter.instances[0].table == "audit_events"
    assert RecordingAdapter.instances[0].rows[0]["event"] == "login"


def test_normalizer_logger_accepts_database_adapter():
    RecordingAdapter.instances = []
    cfg = NormalizerLogConfig(
        enabled=True,
        backend="mongodb",
        database_url="mongodb://localhost:27017/mim",
        adapter=RecordingAdapter,
        collection="normalizer_events",
    )

    logger = NormalizerLogger(cfg)
    result = logger.emit(
        trace_id="t-2",
        user_ref="u-42",
        jargon_used={"wa7ed": 2},
        jargon_skipped={"foo": 1},
        arabizi_used=1,
        arabizi_oov=0,
        rules_applied=3,
        duration_ms=12,
    )

    assert len(RecordingAdapter.instances) == 1
    assert RecordingAdapter.instances[0].table == "normalizer_events"
    assert json.loads(RecordingAdapter.instances[0].rows[0]["jargon_used"]) == {"wa7ed": 2}
    assert result["called"] is True
    assert result["when"]
    assert result["what_it_did"]["dictionary_hits"] == 1
    assert result["what_it_did"]["rules_applied"] == 3


def test_audit_logger_returns_summary_for_called_event():
    cfg = AuditConfig(enabled=True, backend="sqlite", db_path="./tmp/test_audit.db", adapter=RecordingAdapter, collection="audit_events")
    logger = AuditLogger(cfg)
    result = logger.emit(
        event="normalize",
        trace_id="t-3",
        user_ref="u-99",
        input_text="b8it nchouf daaba",
        output_text="bghit nchouf daba",
        duration_ms=7,
        status="ok",
    )

    assert result["called"] is True
    assert result["when"]
    assert result["what_it_did"]["event"] == "normalize"
    assert result["what_it_did"]["status"] == "ok"


def test_database_backend_factory_builds_native_backends():
    postgres_cfg = SimpleNamespace(backend="postgresql", database_url="postgresql://user:pass@localhost:5432/mim")
    mysql_cfg = SimpleNamespace(backend="mysql", database_url="mysql://user:pass@localhost:3306/mim")
    mongo_cfg = SimpleNamespace(backend="mongodb", database_url="mongodb://localhost:27017/mim")

    assert isinstance(create_backend(postgres_cfg, "audit_events"), PostgreSQLBackend)
    assert isinstance(create_backend(mysql_cfg, "audit_events"), MySQLBackend)
    assert isinstance(create_backend(mongo_cfg, "audit_events"), MongoDBBackend)


def test_main_config_loads_chatbot_voice_sections():
    cfg = MimConfig.from_dict({
        "chatbot": {"enabled": True, "system_prompt": "darija", "use_normalizer": True},
        "voice": {"enabled": True, "use_audit_log": True},
        "stt": {"enabled": True, "model": "whisper-1"},
        "tts": {"enabled": True, "model": "tts-1"},
        "intents": {"enabled": True, "strategy": "hybrid"},
    })

    assert cfg.chatbot.enabled is True
    assert cfg.voice.enabled is True
    assert cfg.stt.model == "whisper-1"
    assert cfg.tts.model == "tts-1"
    assert cfg.intents.strategy == "hybrid"


def test_chatbot_supports_prompt_file_and_personalized_params(tmp_path):
    prompt_file = tmp_path / "bot_prompt.txt"
    prompt_file.write_text("You are a friendly Moroccan concierge.", encoding="utf-8")

    cfg = MimConfig.from_dict({
        "chatbot": {
            "enabled": True,
            "system_prompt": "darija",
            "system_prompt_file": str(prompt_file),
            "params": {"temperature": 0.2},
            "roles": {"assistant": "concierge"},
        }
    })

    assert cfg.chatbot.system_prompt_file == str(prompt_file)
    assert cfg.chatbot.params["temperature"] == 0.2
    assert cfg.chatbot.roles["assistant"] == "concierge"


def test_load_config_creates_default_yaml_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config("config.yaml")

    assert (tmp_path / "config.yaml").exists()
    assert cfg.chatbot.enabled is True
    assert cfg.voice.enabled is True


def test_config_yaml_takes_priority_over_legacy_alias(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("chatbot:\n  enabled: false\n", encoding="utf-8")
    (tmp_path / "mimExemple.yaml").write_text("chatbot:\n  enabled: true\n", encoding="utf-8")

    cfg = load_config()

    assert cfg.chatbot.enabled is False


def test_voice_pipeline_uses_configured_normalizer_and_audit(monkeypatch):
    cfg = MimConfig.from_dict({
        "voice": {"enabled": True, "use_normalizer": True, "use_audit_log": True},
        "audit": {"enabled": True},
        "logs": {"enabled": True},
    })

    audit_events = []
    norm_events = []
    norm_report = SimpleNamespace(
        jargon_used={"m3nd": 2},
        jargon_skipped={"foo": 1},
        dictionary_hits=1,
        oov_arabizi=0,
        rule_applications=4,
    )

    normalizer = SimpleNamespace(
        normalize=lambda text, return_report=True: ("salam", norm_report),
    )
    normalizer_log = SimpleNamespace(emit=lambda **kwargs: norm_events.append(kwargs))
    audit = SimpleNamespace(emit=lambda **kwargs: audit_events.append(kwargs))

    monkeypatch.setattr("mim_ai.voice.pipeline.record_until_silence", lambda *args, **kwargs: np.array([0.1, 0.2], dtype=np.float32))
    monkeypatch.setattr("mim_ai.voice.pipeline.STT", lambda cfg: SimpleNamespace(transcribe=lambda audio, sr: "salam"))
    monkeypatch.setattr("mim_ai.voice.pipeline.TTS", lambda cfg: SimpleNamespace(synthesize=lambda text: (np.array([0.5, 0.5], dtype=np.float32), 16000)))
    monkeypatch.setattr("mim_ai.voice.pipeline.play", lambda *args, **kwargs: None)

    pipeline = VoicePipeline(
        cfg.voice,
        cfg.stt,
        cfg.tts,
        chatbot=SimpleNamespace(
            chat=lambda message, session_id, user_ref: SimpleNamespace(
                text="reply",
                tool_calls=[],
                intent=None,
                intent_score=0.0,
            )
        ),
        intents=None,
        audit=audit,
        normalizer=normalizer,
        normalizer_log=normalizer_log,
    )

    reply = pipeline.listen_and_reply(session_id="s1", user_ref="u1", play_audio=False)

    assert reply.transcript == "salam"
    assert reply.reply_text == "reply"
    assert norm_events and norm_events[0]["jargon_used"] == {"m3nd": 2}
    assert audit_events and audit_events[0]["event"] == "voice_turn"
