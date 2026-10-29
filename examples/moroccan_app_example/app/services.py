from __future__ import annotations

import io
import uuid
import wave
from pathlib import Path

import numpy as np
from pydub import AudioSegment

from mim_ai import Mim, load_config
from mim_ai.voice.stt import STT
from mim_ai.voice.tts import TTS


class MimService:
    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path).resolve()
        self.project_root = self.config_path.parent
        config = load_config(self.config_path)
        path_values = [
            (config.normalizer.rules, "arabizi_dict_path"),
            (config.normalizer.rules, "skip_words_path"),
            (config.intents, "intents_path"),
            (config.chatbot, "system_prompt_file"),
            (config.audit, "db_path"),
            (config.audit, "jsonl_path"),
            (config.logs, "db_path"),
            (config.logs, "jsonl_path"),
        ]
        if config.chatbot.history_backend == "sqlite":
            path_values.append((config.chatbot, "history_dsn"))
        for section, key in path_values:
            value = getattr(section, key, None)
            if value:
                path = Path(value)
                if not path.is_absolute():
                    setattr(section, key, str(self.project_root / path))
        self.mim = Mim(config)

    def normalize_text(self, text: str) -> dict:
        if not self.mim.config.normalizer.enabled:
            raise RuntimeError("Normalizer is disabled in the config file.")

        cleaned, report = self.mim.normalizer.normalize(text, return_report=True)
        trace_id = f"norm_{uuid.uuid4().hex[:12]}"
        if self.mim.normalizer_log is not None:
            self.mim.normalizer_log.emit(
                trace_id=trace_id,
                user_ref="demo-user",
                jargon_used=getattr(report, "jargon_used", {}),
                jargon_skipped=getattr(report, "jargon_skipped", {}),
                arabizi_used=getattr(report, "dictionary_hits", 0),
                arabizi_oov=int(getattr(report, "oov_arabizi", False)),
                rules_applied=getattr(report, "rule_applications", 0),
            )
        if self.mim.audit is not None:
            self.mim.audit.emit(
                event="normalize",
                trace_id=trace_id,
                user_ref="demo-user",
                input_text=text,
                output_text=cleaned,
                duration_ms=0,
                status="ok",
                extra={"module": "moroccan_app_example"},
            )
        return {
            "input": text,
            "normalized": cleaned,
            "report": {
                "dictionary_hits": getattr(report, "dictionary_hits", 0),
                "oov_arabizi": bool(getattr(report, "oov_arabizi", False)),
                "rule_applications": getattr(report, "rule_applications", 0),
            },
        }

    def chat(self, message: str, session_id: str = "demo-session") -> dict:
        if not self.mim.config.chatbot.enabled:
            raise RuntimeError("Chatbot is disabled in the config file.")

        reply = self.mim.chat(message, session_id=session_id, user_ref="demo-user")
        if self.mim.audit is not None:
            self.mim.audit.emit(
                event="chat",
                trace_id=f"chat_{uuid.uuid4().hex[:12]}",
                user_ref="demo-user",
                input_text=message,
                output_text=reply.text,
                duration_ms=0,
                status="ok",
                extra={"session_id": session_id},
            )
        return {"message": message, "reply": reply.text, "intent": reply.intent}

    def transcribe_audio_bytes(self, file_name: str, file_bytes: bytes) -> dict:
        if not self.mim.config.stt.enabled:
            raise RuntimeError("Speech-to-text is disabled in the config file.")

        audio = self._read_audio_bytes(file_name=file_name, file_bytes=file_bytes)
        transcript = STT(self.mim.config.stt).transcribe(audio, 16000)
        normalized = self.mim.normalizer.normalize(transcript) if self.mim.config.normalizer.enabled else transcript
        return {
            "source": file_name,
            "transcript": transcript,
            "normalized": normalized,
        }

    def voice_turn_from_audio(self, file_name: str, file_bytes: bytes, session_id: str = "voice-session") -> dict:
        t = self.transcribe_audio_bytes(file_name, file_bytes)
        reply = self.mim.chat(t["normalized"], session_id=session_id, user_ref="demo-user")
        if self.mim.audit is not None:
            self.mim.audit.emit(
                event="voice_turn",
                trace_id=f"voice_{uuid.uuid4().hex[:12]}",
                user_ref="demo-user",
                input_text=t["transcript"],
                output_text=reply.text,
                duration_ms=0,
                status="ok",
                extra={"session_id": session_id},
            )
        return {
            "transcript": t["transcript"],
            "normalized": t["normalized"],
            "reply": reply.text,
            "intent": reply.intent,
        }

    def read_out(self, text: str) -> bytes:
        if not self.mim.config.tts.enabled:
            raise RuntimeError("Text-to-speech is disabled in the config file.")
        audio, sr = TTS(self.mim.config.tts).synthesize(text)
        return self._numpy_to_wav(audio, sr)

    @staticmethod
    def _read_audio_bytes(*, file_name: str, file_bytes: bytes) -> np.ndarray:
        suffix = Path(file_name).suffix.lower()
        buffer = io.BytesIO(file_bytes)
        if suffix == ".wav":
            with wave.open(buffer, "rb") as wav:
                channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                nframes = wav.getnframes()
                raw = wav.readframes(nframes)
            pcm = np.frombuffer(raw, dtype=f"<{sample_width == 2 and 'i2' or 'u1'}")
            if channels > 1:
                pcm = pcm.reshape(-1, channels)
                pcm = pcm.mean(axis=1)
            if sample_width == 2:
                pcm = pcm.astype(np.float32) / 32768.0
            else:
                pcm = pcm.astype(np.float32) / 255.0
            return np.clip(pcm, -1.0, 1.0)

        audio = AudioSegment.from_file(buffer, format=suffix.lstrip("."))
        audio = audio.set_channels(1).set_frame_rate(16000)
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        return np.clip(samples / 32768.0, -1.0, 1.0)

    @staticmethod
    def _numpy_to_wav(audio: np.ndarray, sample_rate: int) -> bytes:
        pcm = np.clip(audio, -1.0, 1.0)
        pcm_i16 = (pcm * 32767).astype("<i2")
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm_i16.tobytes())
        return buffer.getvalue()
