"""
mim_ai.voice.pipeline
=====================

Full voice pipeline, driven entirely by MimConfig.

    from mim_ai import load_config, VoicePipeline
    cfg = load_config("mim.yaml")
    vp = VoicePipeline(cfg.voice, cfg.stt, cfg.tts,
                       chatbot=bot, intents=intents, audit=audit, normalizer=norm)
    reply = vp.listen_and_reply(session_id="user-42")
"""
from __future__ import annotations

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


class VoicePipeline:
    def __init__(
        self,
        voice_cfg:  VoiceSection,
        stt_cfg:    STTConfig,
        tts_cfg:    TTSConfig,
        chatbot=None, intents=None, audit=None, normalizer=None,
    ) -> None:
        self.cfg = voice_cfg
        self.enabled = voice_cfg.enabled
        self.stt = STT(stt_cfg)
        self.tts = TTS(tts_cfg)
        self.chatbot = chatbot
        self.intents = intents
        self.audit = audit
        self.normalizer = normalizer

    def listen_and_reply(
        self, *, session_id: str = "default",
        user_ref: str | None = None, play_audio: bool = True,
    ) -> VoiceReply:
        if not self.enabled:
            return VoiceReply()

        t0 = time.perf_counter()
        trace_id = f"voice_{uuid.uuid4().hex[:12]}"

        # 1. Record one utterance
        audio_in = record_until_silence(
            self.cfg.audio, self.cfg.vad,
            max_seconds=self.cfg.max_record_seconds,
            silence_timeout_ms=self.cfg.silence_timeout_ms,
        )
        if audio_in is None or len(audio_in) == 0:
            return VoiceReply(trace_id=trace_id)

        # 2. Transcribe
        transcript = self.stt.transcribe(audio_in, self.cfg.audio.sample_rate)
        if not transcript:
            return VoiceReply(trace_id=trace_id)

        # 3. Normalize
        if self.normalizer and self.cfg.use_normalizer:
            transcript, _ = self.normalizer.normalize(transcript, return_report=True)

        # 4. Intent
        intent_name, intent_score = None, 0.0
        if self.intents and self.cfg.use_intents:
            m, s = self.intents.match_rule_based(transcript)
            if m:
                intent_name, intent_score = m.name, s

        # 5. Chat
        reply_text, tools = "", []
        if self.chatbot:
            r = self.chatbot.chat(transcript, session_id=session_id, user_ref=user_ref)
            reply_text, tools = r.text, r.tool_calls
            if r.intent:
                intent_name, intent_score = r.intent, r.intent_score
        if not reply_text:
            reply_text = "سمح ليا، ما فهمتش."

        # 6. Speak
        audio_out, sr = self.tts.synthesize(reply_text)
        if play_audio and audio_out is not None:
            play(audio_out, sr, device=self.cfg.audio.output_device)

        # 7. Audit
        duration_ms = int((time.perf_counter() - t0) * 1000)
        if self.audit and self.cfg.use_audit_log:
            self.audit.emit(
                event="voice_turn", trace_id=trace_id, user_ref=user_ref,
                input_text=transcript, output_text=reply_text,
                duration_ms=duration_ms, status="ok",
                extra={
                    "session_id": session_id, "intent": intent_name,
                    "tool_calls": [t["name"] for t in tools],
                },
            )

        return VoiceReply(
            transcript=transcript, reply_text=reply_text,
            intent=intent_name, intent_score=intent_score,
            audio=audio_out, sample_rate=sr,
            trace_id=trace_id, duration_ms=duration_ms, tool_calls=tools,
        )