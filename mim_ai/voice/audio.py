"""Voice/audio helpers for recording and playback.

This module deliberately stays lightweight and provider-agnostic. The STT/TTS
layers abstract transport concerns while this file focuses on local capture and
playback for the voice pipeline.
"""
from __future__ import annotations

import io
import wave
from typing import Any

import numpy as np


class AudioError(RuntimeError):
    pass


def _coerce_audio(audio: np.ndarray | Any) -> np.ndarray:
    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim == 0:
        return arr.reshape(1)
    return arr


def load_wav(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path, "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        dtype = np.dtype("<i2")
        pcm = np.frombuffer(frames, dtype=dtype).astype(np.float32) / 32768.0
        if channels > 1:
            pcm = pcm.reshape(-1, channels).mean(axis=1)
        return pcm, sample_rate


def record_until_silence(audio_cfg: Any, vad_cfg: Any, *, max_seconds: int, silence_timeout_ms: int) -> np.ndarray | None:
    """Placeholder recording function.

    Real production apps should replace this with a microphone backend such as
    sounddevice, pyaudio, or a streaming recorder tied to a queue. The library
    keeps the interface stable and provider-agnostic.
    """
    return None


def play(audio: np.ndarray, sample_rate: int, *, device: str | None = None) -> None:
    """Placeholder playback function.

    Production integrations can swap in sounddevice or any local audio player.
    """
    return None


def audio_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    pcm = _coerce_audio(audio)
    pcm = np.clip(pcm, -1.0, 1.0)
    pcm_i16 = (pcm * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_i16.tobytes())
    return buf.getvalue()
