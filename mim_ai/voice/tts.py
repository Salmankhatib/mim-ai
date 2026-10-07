# mim_ai/voice/tts.py
"""
TTS — talks to any OpenAI-compatible /audio/speech endpoint.
"""
from __future__ import annotations

import io
import wave

import numpy as np

from .._http import speak as http_speak, APIError
from ..config import TTSConfig


class TTS:
    def __init__(self, config: TTSConfig) -> None:
        self.config = config

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        try:
            audio_bytes, mime = http_speak(self.config, text)
        except APIError as e:
            raise TTSError(str(e)) from e

        return _decode_audio(audio_bytes, mime, self.config.format)


class TTSError(RuntimeError):
    pass


def _decode_audio(data: bytes, mime: str, fmt: str) -> tuple[np.ndarray, int]:
    """Decode WAV to float32 mono. Non-WAV formats need soundfile (optional)."""
    if fmt == "wav":
        with wave.open(io.BytesIO(data), "rb") as w:
            n = w.getnframes()
            sr = w.getframerate()
            raw = w.readframes(n)
            arr = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
            if w.getnchannels() > 1:
                arr = arr.reshape(-1, w.getnchannels()).mean(axis=1)
            return arr, sr

    # mp3 / opus -> soundfile (optional dependency)
    try:
        import soundfile as sf                       # type: ignore
    except ImportError as e:
        raise ImportError(
            f"Decoding {fmt!r} requires 'soundfile'. "
            f"Install with: pip install mim-ai[voice]"
        ) from e
    arr, sr = sf.read(io.BytesIO(data), dtype="float32")
    if arr.ndim > 1:
        arr = arr.mean(axis=1)
    return arr, sr