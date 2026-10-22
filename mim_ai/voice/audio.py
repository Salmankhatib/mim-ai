"""Voice/audio helpers for recording and playback.

This module deliberately stays lightweight and provider-agnostic. The STT/TTS
layers abstract transport concerns while this file focuses on local capture and
playback for the voice pipeline.
"""
from __future__ import annotations

import io
import wave
from collections import deque
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


def _load_sounddevice():
    try:
        import sounddevice
    except (ImportError, OSError) as exc:
        raise AudioError(
            "Microphone and speaker I/O requires sounddevice. "
            'Install it with: pip install "mim-ai[voice]"'
        ) from exc
    return sounddevice


def record_until_silence(
    audio_cfg: Any,
    vad_cfg: Any,
    *,
    max_seconds: int,
    silence_timeout_ms: int | None = None,
) -> np.ndarray | None:
    """Record one utterance, stopping after speech followed by sustained silence."""
    sample_rate = int(getattr(audio_cfg, "sample_rate", 16000) or 16000)
    max_seconds = float(max_seconds)
    if sample_rate <= 0:
        raise ValueError("audio.sample_rate must be positive")
    if max_seconds <= 0:
        raise ValueError("max_seconds must be positive")

    enabled = bool(getattr(vad_cfg, "enabled", True))
    threshold = float(getattr(vad_cfg, "threshold", 0.015))
    if not 0 < threshold <= 1:
        raise ValueError("vad.threshold must be greater than 0 and at most 1")

    frame_ms = int(getattr(vad_cfg, "frame_ms", 20))
    min_speech_ms = int(getattr(vad_cfg, "min_speech_ms", 100))
    min_silence_ms = int(
        silence_timeout_ms
        if silence_timeout_ms is not None
        else getattr(vad_cfg, "min_silence_ms", 700)
    )
    start_timeout_ms = int(getattr(vad_cfg, "start_timeout_ms", 10000))
    pre_roll_ms = int(getattr(vad_cfg, "pre_roll_ms", 200))
    if frame_ms <= 0 or min_speech_ms <= 0 or min_silence_ms <= 0:
        raise ValueError("VAD frame, speech, and silence durations must be positive")
    if start_timeout_ms <= 0 or pre_roll_ms < 0:
        raise ValueError("VAD start timeout must be positive and pre-roll nonnegative")

    frame_samples = max(1, round(sample_rate * frame_ms / 1000))
    max_samples = max(1, int(max_seconds * sample_rate))
    frame_limit = max(1, int(np.ceil(max_samples / frame_samples)))
    speech_frames_required = max(1, int(np.ceil(min_speech_ms / frame_ms)))
    silence_frames_required = max(1, int(np.ceil(min_silence_ms / frame_ms)))
    start_frames_limit = max(1, int(np.ceil(start_timeout_ms / frame_ms)))
    pre_roll_frames = int(np.ceil(pre_roll_ms / frame_ms))
    onset_buffer: deque[np.ndarray] = deque(
        maxlen=max(1, pre_roll_frames + speech_frames_required)
    )
    captured: list[np.ndarray] = []
    speech_run = silence_run = 0
    speech_started = False

    sd = _load_sounddevice()
    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=frame_samples,
            device=getattr(audio_cfg, "input_device", None),
        ) as stream:
            for frame_index in range(frame_limit):
                if enabled and not speech_started and frame_index >= start_frames_limit:
                    return None
                frame, overflowed = stream.read(frame_samples)
                if overflowed:
                    raise AudioError("Microphone input overflowed while recording")
                samples = np.asarray(frame, dtype=np.float32).reshape(-1)
                if samples.size != frame_samples:
                    raise AudioError("Microphone returned an incomplete audio frame")

                if not enabled:
                    captured.append(samples.copy())
                    continue

                onset_buffer.append(samples.copy())
                rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
                if not speech_started:
                    if rms >= threshold:
                        speech_run += 1
                    else:
                        speech_run = 0
                    if speech_run >= speech_frames_required:
                        captured.extend(onset_buffer)
                        speech_started = True
                        onset_buffer.clear()
                    continue

                captured.append(samples.copy())
                if rms >= threshold:
                    silence_run = 0
                else:
                    silence_run += 1
                    if silence_run >= silence_frames_required:
                        break
    except AudioError:
        raise
    except Exception as exc:
        raise AudioError(f"Microphone capture failed: {exc}") from exc

    if not captured:
        return None
    return np.concatenate(captured)[:max_samples].astype(np.float32, copy=False)


def play(audio: np.ndarray, sample_rate: int, *, device: str | None = None) -> None:
    """Play audio through the configured sound device."""
    if audio is None:
        return
    arr = _coerce_audio(audio)
    if arr.size == 0:
        return
    sd = _load_sounddevice()
    try:
        sd.play(arr.astype(np.float32), sample_rate, device=device)
        sd.wait()
    except Exception as exc:
        raise AudioError(f"Audio playback failed: {exc}") from exc


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
