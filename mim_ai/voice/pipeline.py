"""
mim_ai.voice.pipeline
=====================

Full voice pipeline, driven entirely by MimConfig.

    from mim_ai import load_config, VoicePipeline
    cfg = load_config("config.yaml")
    vp = VoicePipeline(cfg.voice, cfg.stt, cfg.tts,
                       chatbot=bot, intents=intents, audit=audit, normalizer=norm)
    reply = vp.listen_and_reply(session_id="user-42")
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field

import numpy as np

from ..config import VoiceSection, STTConfig, TTSConfig
from .stt import STT
from .tts import TTS
from .audio import record_until_silence, play


@dataclass
class VoiceReply:
    transcript:  str = ""
    reply_text:  str = ""
    intent:      str | None = None
    intent_score: float = 0.0
    audio:       np.ndarray | None = None
    sample_rate: int = 0
    trace_id:    str = ""
    duration_ms: int = 0
    tool_calls:  list[dict] = field(default_factory=list)
    status:       str = "ok"
    error:        str | None = None


class VoicePipeline:
    def __init__(
        self,
        voice_cfg:  VoiceSection,
        stt_cfg:    STTConfig,
        tts_cfg:    TTSConfig,
        chatbot=None, intents=None, audit=None, normalizer=None, normalizer_log=None,
        intent_threshold: float = 0.55,
    ) -> None:
        self.cfg = voice_cfg
        self.enabled = voice_cfg.enabled
        self.stt = STT(stt_cfg)
        self.tts = TTS(tts_cfg)
        self.chatbot = chatbot
        self.intents = intents
        self.audit = audit
        self.normalizer = normalizer
        self.normalizer_log = normalizer_log
        self.intent_threshold = intent_threshold

    def listen_and_reply(
        self, *, session_id: str = "default",
        user_ref: str | None = None, play_audio: bool = True,
    ) -> VoiceReply:
        if not self.enabled:
            return VoiceReply()
        if not self.stt.config.enabled:
            raise RuntimeError("stt.enabled is false in your config")

        t0 = time.perf_counter()
        trace_id = f"voice_{uuid.uuid4().hex[:12]}"

        # 1. Record one utterance
        audio_in = record_until_silence(
            self.cfg.audio, self.cfg.vad,
            max_seconds=self.cfg.max_record_seconds,
        )
        if audio_in is None or len(audio_in) == 0:
            return VoiceReply(
                trace_id=trace_id,
                duration_ms=int((time.perf_counter() - t0) * 1000),
                status="no_speech",
            )

        # 2. Transcribe
        transcript = self.stt.transcribe(audio_in, self.cfg.audio.sample_rate)
        if not transcript:
            return VoiceReply(
                trace_id=trace_id,
                duration_ms=int((time.perf_counter() - t0) * 1000),
                status="no_transcript",
            )

        # 3. Normalize
        if self.normalizer and self.cfg.use_normalizer:
            transcript, report = self.normalizer.normalize(transcript, return_report=True)
            if self.normalizer_log is not None:
                self.normalizer_log.emit(
                    trace_id=trace_id,
                    user_ref=user_ref,
                    jargon_used=getattr(report, "jargon_used", {}),
                    jargon_skipped=getattr(report, "jargon_skipped", {}),
                    arabizi_used=getattr(report, "dictionary_hits", 0),
                    arabizi_oov=int(getattr(report, "oov_arabizi", False)),
                    rules_applied=getattr(report, "rule_applications", 0),
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                )

        # 4. Intent
        intent_name, intent_score = None, 0.0
        if self.intents and self.cfg.use_intents:
            m, s = self.intents.match_rule_based(transcript, threshold=self.intent_threshold)
            if m:
                intent_name, intent_score = m.name, s

        # 5. Chat
        reply_text, tools = "", []
        chat_error = None
        if self.cfg.use_chatbot and self.chatbot:
            r = self.chatbot.chat(transcript, session_id=session_id, user_ref=user_ref)
            reply_text, tools = r.text, r.tool_calls
            chat_error = getattr(r, "error", None)
            if chat_error:
                reply_text = ""
            if getattr(r, "intent", None):
                intent_name, intent_score = r.intent, getattr(r, "intent_score", 0.0)
        if self.cfg.use_chatbot and not reply_text and not chat_error:
            reply_text = self.cfg.fallback_response

        # 6. Speak
        audio_out, sr = (None, 0)
        if reply_text and self.tts.config.enabled:
            audio_out, sr = self.tts.synthesize(reply_text)
        if play_audio and audio_out is not None:
            play(audio_out, sr, device=self.cfg.audio.output_device)

        # 7. Audit
        duration_ms = int((time.perf_counter() - t0) * 1000)
        status = "error" if chat_error else ("ok" if reply_text else "transcribed")
        if self.audit and self.cfg.use_audit_log:
            self.audit.emit(
                event="voice_turn", trace_id=trace_id, user_ref=user_ref,
                input_text=transcript, output_text=reply_text,
                duration_ms=duration_ms,
                status=status,
                extra={
                    "session_id": session_id, "intent": intent_name,
                    "tool_calls": [t["name"] for t in tools],
                    **({"error": chat_error} if chat_error else {}),
                },
            )

        return VoiceReply(
            transcript=transcript, reply_text=reply_text,
            intent=intent_name, intent_score=intent_score,
            audio=audio_out, sample_rate=sr,
            trace_id=trace_id, duration_ms=duration_ms, tool_calls=tools,
            status=status,
            error=chat_error,
        )

    async def alisten_and_reply(
        self,
        *,
        session_id: str = "default",
        user_ref: str | None = None,
        play_audio: bool = True,
    ) -> VoiceReply:
        """Run the blocking recording/network pipeline outside asyncio."""
        return await asyncio.to_thread(
            self.listen_and_reply,
            session_id=session_id,
            user_ref=user_ref,
            play_audio=play_audio,
        )