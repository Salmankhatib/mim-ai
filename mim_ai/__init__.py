"""
mim_ai
======

Config-first, model-agnostic toolkit for Moroccan Darija AI.

    from mim_ai import Mim
    mim = Mim.from_config("mim_config.yaml")

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

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from .config import MimConfig, load_config, write_default_config

if TYPE_CHECKING:
    from .chatbot.tools import ToolRegistry

__version__ = "0.1.0"


def __getattr__(name: str):
    if name == "anonymizer":
        import importlib
        return importlib.import_module(".anonymizer", __name__)
    if name == "anonymize":
        from .anonymizer import anonymize
        return anonymize
    if name == "AnonymizationResult":
        from .anonymizer import AnonymizationResult
        return AnonymizationResult
    if name == "VoicePipeline":
        from .voice import VoicePipeline
        return VoicePipeline
    if name == "VoiceReply":
        from .voice import VoiceReply
        return VoiceReply
    if name == "_http":
        import importlib
        return importlib.import_module("._http", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class Mim:
    """
    One object that owns the whole stack.

    Every subsystem is built lazily on first use, so a config that only
    enables the normalizer doesn't import torch, sounddevice, or any
    HTTP client.
    """

    def __init__(
        self, config: MimConfig, *, tool_registry: ToolRegistry | None = None
    ) -> None:
        self.config = config
        self._tool_registry = tool_registry
        self._normalizer = None
        self._intents = None
        self._audit = None
        self._normalizer_log = None
        self._chatbot = None
        self._voice = None

    @classmethod
    def from_config(
        cls, path: str | Path = "mim_config.yaml", *, tool_registry: ToolRegistry | None = None
    ) -> "Mim":
        return cls(load_config(path), tool_registry=tool_registry)

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
                normalizer=self.normalizer if c.use_normalizer else None,
                audit=self.audit if c.use_audit_log else None,
                normalizer_log=self.normalizer_log if c.use_normalizer_log else None,
                intents=self.intents if c.use_intents else None,
                intent_strategy=self.config.intents.strategy,
                intent_prompt=self.config.intents.llm_prompt,
                registry=self._tool_registry,
            )
        return self._chatbot

    @property
    def voice(self):
        if self._voice is None and self.config.voice.enabled:
            from .voice import VoicePipeline
            v = self.config.voice
            self._voice = VoicePipeline(
                v, self.config.stt, self.config.tts,
                chatbot=self.chatbot if v.use_chatbot else None,
                intents=self.intents if v.use_intents else None,
                audit=self.audit if v.use_audit_log else None,
                normalizer=self.normalizer if v.use_normalizer else None,
                normalizer_log=self.normalizer_log if v.use_normalizer else None,
                intent_threshold=self.config.intents.threshold,
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

    async def achat(self, message: str, *, session_id: str = "default",
                    user_ref: str | None = None):
        """One non-blocking chat turn for asyncio applications."""
        if self.chatbot is None:
            raise RuntimeError("chatbot.enabled is false in your config")
        return await self.chatbot.achat(
            message, session_id=session_id, user_ref=user_ref,
        )

    def anonymize(self, text: str):
        """Anonymize text using the anonymizer settings in this Mim config."""
        from .anonymizer import anonymize
        return anonymize(text, config=self.config.anonymizer)

    def listen_and_reply(self, *, session_id: str = "default",
                         user_ref: str | None = None, play_audio: bool = True):
        """One voice turn. Records, transcribes, chats, speaks."""
        if self.voice is None:
            raise RuntimeError("voice.enabled is false in your config")
        return self.voice.listen_and_reply(
            session_id=session_id, user_ref=user_ref, play_audio=play_audio,
        )

    async def alisten_and_reply(self, *, session_id: str = "default",
                                user_ref: str | None = None,
                                play_audio: bool = True):
        """Run the blocking voice pipeline outside an asyncio event loop."""
        if self.voice is None:
            raise RuntimeError("voice.enabled is false in your config")
        return await asyncio.to_thread(
            self.voice.listen_and_reply,
            session_id=session_id,
            user_ref=user_ref,
            play_audio=play_audio,
        )

    def transcribe_file(self, path: str) -> str:
        """Transcribe a WAV file. Standalone — no chatbot needed."""
        if not self.config.stt.enabled:
            raise RuntimeError("stt.enabled is false in your config")
        from .voice.stt import STT
        from .voice.audio import load_wav
        audio, sr = load_wav(path)
        return STT(self.config.stt).transcribe(audio, sr)

    async def atranscribe_file(self, path: str) -> str:
        """Transcribe a WAV file without blocking an asyncio event loop."""
        return await asyncio.to_thread(self.transcribe_file, path)

    def shutdown(self) -> None:
        """Release resources. Idempotent."""
        seen: set[int] = set()
        try:
            for component in (
                self._voice, self._chatbot, self._audit,
                self._normalizer_log, self._intents, self._normalizer,
            ):
                if component is None or id(component) in seen:
                    continue
                seen.add(id(component))
                close = getattr(component, "close", None)
                if callable(close):
                    close()
        finally:
            for attr in ("_voice", "_chatbot", "_audit", "_normalizer_log", "_intents", "_normalizer"):
                setattr(self, attr, None)


__all__ = [
    "Mim",
    "MimConfig",
    "load_config",
    "write_default_config",
    "anonymizer",
    "anonymize",
    "AnonymizationResult",
    "__version__",
]