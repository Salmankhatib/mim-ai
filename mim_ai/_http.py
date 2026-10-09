"""HTTP helpers for provider-agnostic OpenAI-compatible APIs.

This keeps the STT and TTS stacks interchangeable: the same code works with
OpenAI, Groq, Mistral-style hosts, or any OpenAI-compatible gateway behind a
custom base URL.
"""
from __future__ import annotations

import json
import mimetypes
import os
from email.generator import BytesGenerator
from io import BytesIO
from typing import Any
from urllib import request
from urllib.parse import urljoin


class APIError(RuntimeError):
    pass


def _api_base_url(config: Any) -> str:
    base = getattr(config, "base_url", None) or "https://api.openai.com/v1"
    return base.rstrip("/")


def _api_key(config: Any) -> str:
    env_name = getattr(config, "api_key_env", "OPENAI_API_KEY")
    return os.getenv(env_name, "")


def _headers(config: Any, *, content_type: str | None = None) -> dict[str, str]:
    headers = {}
    api_key = _api_key(config)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _json_request(url: str, payload: dict[str, Any], config: Any) -> Any:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={**_headers(config, content_type="application/json"), "Accept": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=(getattr(config, "timeout_ms", 20000) / 1000) or 20) as resp:
            raw = resp.read()
    except Exception as exc:  # pragma: no cover - transport dependent
        raise APIError(f"HTTP request failed for {url}: {exc}") from exc
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {"raw": raw}


def _multipart_payload(fields: dict[str, Any], boundary: str) -> bytes:
    buffer = BytesIO()
    for name, value in fields.items():
        buffer.write(f"--{boundary}\r\n".encode("utf-8"))
        if hasattr(value, "read"):
            filename = getattr(value, "name", name)
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            buffer.write(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"))
            buffer.write(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
            buffer.write(value.read())
            buffer.write(b"\r\n")
        else:
            buffer.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            buffer.write(str(value).encode("utf-8"))
            buffer.write(b"\r\n")
    buffer.write(f"--{boundary}--\r\n".encode("utf-8"))
    return buffer.getvalue()


def transcribe(config: Any, wav_bytes: bytes) -> str:
    """Call an OpenAI-compatible transcription endpoint."""
    url = urljoin(_api_base_url(config) + "/", "audio/transcriptions")
    boundary = "----mim-ai-boundary"
    file_like = BytesIO(wav_bytes)
    file_like.name = "audio.wav"
    payload = _multipart_payload({"file": file_like, "model": getattr(config, "model", "whisper-1")}, boundary)
    headers = _headers(config)
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    if getattr(config, "language", None):
        headers["X-Language"] = str(config.language)
    req = request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=(getattr(config, "timeout_ms", 20000) / 1000) or 20) as resp:
            raw = resp.read()
    except Exception as exc:  # pragma: no cover
        raise APIError(f"Transcription request failed: {exc}") from exc
    if not raw:
        return ""
    try:
        obj = json.loads(raw.decode("utf-8"))
        text = obj.get("text")
        if isinstance(text, str):
            return text
    except json.JSONDecodeError:
        pass
    return raw.decode("utf-8", errors="replace").strip()


def speak(config: Any, text: str) -> tuple[bytes, str]:
    """Call an OpenAI-compatible speech endpoint and return raw bytes."""
    url = urljoin(_api_base_url(config) + "/", "audio/speech")
    payload = {
        "model": getattr(config, "model", "tts-1"),
        "input": text,
        "voice": getattr(config, "voice", "nova"),
    }
    result = _json_request(url, payload, config)
    if isinstance(result, (bytes, bytearray)):
        return bytes(result), "audio/wav"

    # Some providers return the audio bytes directly via a raw response body,
    # not a JSON object.
    req = request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={**_headers(config, content_type="application/json"), "Accept": "audio/*"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=(getattr(config, "timeout_ms", 20000) / 1000) or 20) as resp:
            raw = resp.read()
            mime = resp.headers.get_content_type() or "audio/wav"
            return raw, mime
    except Exception as exc:  # pragma: no cover
        raise APIError(f"Speech request failed: {exc}") from exc
