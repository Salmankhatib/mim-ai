from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .audit.config import AuditConfig, NormalizerLogConfig
from .chatbot.config import ChatbotConfig
from .intents.config import IntentConfig
from .normalizer.schema import NormalizerConfig


@dataclass
class AudioConfig:
    """Microphone and playback config for the voice pipeline."""
    input_device: str | None = None
    output_device: str | None = None
    sample_rate: int = 16000
    chunk_ms: int = 32


@dataclass
class VADConfig:
    """Voice activity detection parameters."""
    enabled: bool = True
    threshold: float = 0.5
    min_silence_ms: int = 500


@dataclass
class VoiceSection:
    """Top-level voice pipeline config."""
    enabled: bool = True
    use_normalizer: bool = True
    use_intents: bool = True
    use_audit_log: bool = True
    use_chatbot: bool = True
    vad: VADConfig = field(default_factory=VADConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    max_record_seconds: int = 30
    silence_timeout_ms: int = 1500

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "VoiceSection":
        cfg = cls()
        raw = data or {}
        for key in ("enabled", "use_normalizer", "use_intents", "use_audit_log", "use_chatbot",
                    "max_record_seconds", "silence_timeout_ms"):
            if key in raw:
                setattr(cfg, key, raw[key])
        vad_cfg = raw.get("vad") if isinstance(raw.get("vad"), dict) else {}
        if vad_cfg:
            for key, value in vad_cfg.items():
                if hasattr(cfg.vad, key):
                    setattr(cfg.vad, key, value)
        audio_cfg = raw.get("audio") if isinstance(raw.get("audio"), dict) else {}
        if audio_cfg:
            for key, value in audio_cfg.items():
                if hasattr(cfg.audio, key):
                    setattr(cfg.audio, key, value)
        return cfg


@dataclass
class STTConfig:
    """Speech-to-text provider settings."""
    enabled: bool = True
    provider: str = "openai"
    model: str = "whisper-1"
    base_url: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    language: str = "ar"
    timeout_ms: int = 20000
    temperature: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "STTConfig":
        cfg = cls()
        raw = data or {}
        for key in ("enabled", "provider", "model", "base_url", "api_key_env", "language",
                    "timeout_ms", "temperature"):
            if key in raw:
                setattr(cfg, key, raw[key])
        if "extra" in raw and isinstance(raw["extra"], dict):
            cfg.extra = raw["extra"]
        return cfg


@dataclass
class TTSConfig:
    """Text-to-speech provider settings."""
    enabled: bool = True
    provider: str = "openai"
    model: str = "tts-1"
    voice: str = "nova"
    base_url: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    format: str = "wav"
    timeout_ms: int = 20000
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "TTSConfig":
        cfg = cls()
        raw = data or {}
        for key in ("enabled", "provider", "model", "voice", "base_url", "api_key_env",
                    "format", "timeout_ms"):
            if key in raw:
                setattr(cfg, key, raw[key])
        if "extra" in raw and isinstance(raw["extra"], dict):
            cfg.extra = raw["extra"]
        return cfg


@dataclass
class MimConfig:
    """Top-level application config that binds the optional subsystems."""

    normalizer: NormalizerConfig = field(default_factory=NormalizerConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    logs: NormalizerLogConfig = field(default_factory=NormalizerLogConfig)
    chatbot: ChatbotConfig = field(default_factory=ChatbotConfig)
    intents: IntentConfig = field(default_factory=IntentConfig)
    voice: VoiceSection = field(default_factory=VoiceSection)
    stt: STTConfig = field(default_factory=STTConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "MimConfig":
        data = raw or {}
        cfg = cls()

        normalizer_cfg = data.get("normalizer", {})
        if isinstance(normalizer_cfg, dict):
            cfg.normalizer = NormalizerConfig.from_mapping(normalizer_cfg)

        audit_cfg = data.get("audit", {})
        if isinstance(audit_cfg, dict):
            cfg.audit = AuditConfig(**audit_cfg)

        logs_cfg = data.get("logs") or data.get("normalizer_log") or {}
        if isinstance(logs_cfg, dict):
            cfg.logs = NormalizerLogConfig(**logs_cfg)

        chatbot_cfg = data.get("chatbot", {})
        if isinstance(chatbot_cfg, dict):
            llm_cfg = data.get("llm", {}) if isinstance(data.get("llm", {}), dict) else {}
            merged = dict(llm_cfg)
            merged.update(chatbot_cfg)
            cfg.chatbot = ChatbotConfig.from_mapping(merged)
            if "llm_provider" in llm_cfg:
                cfg.chatbot.llm_provider = llm_cfg["llm_provider"]
            if "base_url" in llm_cfg and not cfg.chatbot.llm_endpoint:
                cfg.chatbot.llm_endpoint = llm_cfg["base_url"]
            if "api_key_env" in llm_cfg:
                cfg.chatbot.llm_api_key_env = llm_cfg["api_key_env"]
            if "model" in llm_cfg:
                cfg.chatbot.llm_model = llm_cfg["model"]
            if "temperature" in llm_cfg:
                cfg.chatbot.llm_temperature = llm_cfg["temperature"]
            if "max_tokens" in llm_cfg:
                cfg.chatbot.llm_max_tokens = llm_cfg["max_tokens"]
            if "timeout_ms" in llm_cfg:
                cfg.chatbot.llm_timeout_ms = llm_cfg["timeout_ms"]
            if "extra" in llm_cfg and isinstance(llm_cfg["extra"], dict):
                cfg.chatbot.llm_extra_params.update(llm_cfg["extra"])

        intents_cfg = data.get("intents", {})
        if isinstance(intents_cfg, dict):
            cfg.intents = IntentConfig(**intents_cfg)

        voice_cfg = data.get("voice", {})
        if isinstance(voice_cfg, dict):
            cfg.voice = VoiceSection.from_mapping(voice_cfg)

        stt_cfg = data.get("stt", {})
        if isinstance(stt_cfg, dict):
            cfg.stt = STTConfig.from_mapping(stt_cfg)

        tts_cfg = data.get("tts", {})
        if isinstance(tts_cfg, dict):
            cfg.tts = TTSConfig.from_mapping(tts_cfg)

        return cfg


def _candidate_paths(path: str | None) -> list[Path]:
    if path:
        return [Path(path)]
    return [
        Path("mimExemple.yaml"),
        Path("mimExemple.yml"),
        Path("config.yaml"),
    ]


def load_config(path: str | None = "mimExemple.yaml") -> MimConfig:
    """Load application config from the example YAML used by developers."""
    for candidate in _candidate_paths(path):
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as fh:
                return MimConfig.from_dict(yaml.safe_load(fh) or {})

    searched = ", ".join(str(p) for p in _candidate_paths(path))
    raise FileNotFoundError(f"No config file found. Looked for: {searched}")


__all__ = ["MimConfig", "load_config"]
