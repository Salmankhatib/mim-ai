"""
mim_ai
======

Config-first, model-agnostic toolkit for Moroccan Darija AI.

    from mim_ai import Mim

    mim = Mim.from_config("mim.yaml")

    # Chat
    reply = mim.chat("salam, chkoun nta?", session_id="u1")

    # Voice
    voice_reply = mim.listen_and_reply(session_id="u1")

    # STT only
    text = mim.transcribe_file("call.wav")

    # Cleanup
    mim.shutdown()
"""
from __future__ import annotations

from .config import load_config, MimConfig


class Mim:
    """
    One object that owns the whole stack.

    Every subsystem is built lazily on first use, so a config that only
    enables the normalizer doesn't import torch, sounddevice, or any
    HTTP client.
    """

    def __init__(self, config: MimConfig) -> None:
        self.config = config
        self._normalizer = None
        self._intents = None
        self._audit = None
        self._normalizer_log = None
        self._logs = None
        self._chatbot = None
        self._voice = None

    @classmethod
    def from_config(cls, path: str = "mimExemple.yaml") -> "Mim":
        return cls(load_config(path))

    # ------------------------------------------------------------------
    # Lazy properties — build on first access, cache forever.
    # ------------------------------------------------------------------
    @property
    def normalizer(self):
        if self._normalizer is None and self.config.normalizer.enabled:
            from .normalizer import Normalizer
            self._normalizer = Normalizer.from_config(self.config.normalizer)
        return self._normalizer

    @property
    def normalizer_log(self):
        if self._normalizer_log is None and self.config.logs.enabled:
            from .audit import NormalizerLogger
            self._normalizer_log = NormalizerLogger(self.config.logs)
        return self._normalizer_log

    @property
    def intents(self):
        if self._intents is None and self.config.intents.enabled:
            from .intents import IntentRegistry
            r = IntentRegistry()
            if self.config.intents.intents_path:
                r.load_yaml(self.config.intents.intents_path)
            self._intents = r
        return self._intents

    @property
    def audit(self):
        if self._audit is None and self.config.audit.enabled:
            from .audit import AuditLogger
            self._audit = AuditLogger(self.config.audit)
        return self._audit

    @property
    def chatbot(self):
        if self._chatbot is None and self.config.chatbot.enabled:
            from .chatbot import Chatbot
            c = self.config.chatbot
            self._chatbot = Chatbot.from_config(
                c,
                normalizer=self.normalizer,
                audit=self.audit,
                normalizer_log=self.normalizer_log,
            )
        return self._chatbot

    @property
    def voice(self):
        if self._voice is None and self.config.voice.enabled:
            from .voice import VoicePipeline
            self._voice = VoicePipeline(
                self.config.voice, self.config.stt, self.config.tts,
                chatbot=self.chatbot, intents=self.intents,
                audit=self.audit, normalizer=self.normalizer,
            )
        return self._voice

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    def chat(self, message: str, *, session_id: str = "default",
             user_ref: str | None = None):
        """One chat turn. Returns a ChatReply."""
        if self.chatbot is None:
            raise RuntimeError("chatbot.enabled is false in your config")
        return self.chatbot.chat(message, session_id=session_id, user_ref=user_ref)

    def listen_and_reply(self, *, session_id: str = "default",
                         user_ref: str | None = None, play_audio: bool = True):
        """One voice turn. Records, transcribes, chats, speaks."""
        if self.voice is None:
            raise RuntimeError("voice.enabled is false in your config")
        return self.voice.listen_and_reply(
            session_id=session_id, user_ref=user_ref, play_audio=play_audio,
        )

    def transcribe_file(self, path: str) -> str:
        """Transcribe a WAV file. Standalone — no chatbot needed."""
        if not self.config.stt.enabled:
            raise RuntimeError("stt.enabled is false in your config")
        from .voice.stt import STT
        from .voice.audio import load_wav
        audio, sr = load_wav(path)
        return STT(self.config.stt).transcribe(audio, sr)

    def shutdown(self) -> None:
        """Release resources. Idempotent."""
        for attr in ("_voice", "_chatbot", "_audit", "_logs", "_normalizer_log", "_intents", "_normalizer"):
            setattr(self, attr, None)


__all__ = ["Mim", "MimConfig", "load_config"]