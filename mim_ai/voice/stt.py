# mim_ai/voice/stt.py
"""
STT — talks to any OpenAI-compatible /audio/transcriptions endpoint.
"""
from __future__ import annotations

import io
import wave

import numpy as np

from .._http import transcribe as http_transcribe, APIError
from ..config import STTConfig


class STT:
    def __init__(self, config: STTConfig) -> None:
        self.config = config

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        wav_bytes = _to_wav_bytes(audio, sample_rate)
        try:
            return http_transcribe(self.config, wav_bytes)
        except APIError as e:
            raise STTError(str(e)) from e


class STTError(RuntimeError):
    pass


def _to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Pack a float32 mono buffer into a WAV container."""
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()