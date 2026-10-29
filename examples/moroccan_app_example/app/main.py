from __future__ import annotations

import io
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

from .auth import require_api_key
from .services import MimService

PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="Moroccan App Example", version="0.1.0")
service = MimService(PROJECT_ROOT / "mim_config.yaml")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))


class NormalizeRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = "demo-session"


class ReadOutRequest(BaseModel):
    text: str


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "voice_enabled": service.mim.config.voice.enabled,
        "chatbot_enabled": service.mim.config.chatbot.enabled,
        "normalizer_enabled": service.mim.config.normalizer.enabled,
    }


@app.post("/api/normalize")
async def normalize(payload: NormalizeRequest, _: str = Depends(require_api_key)) -> dict:
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    return service.normalize_text(payload.text)


@app.post("/api/chat")
async def chat(payload: ChatRequest, _: str = Depends(require_api_key)) -> dict:
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message is required")
    return service.chat(payload.message, session_id=payload.session_id)


@app.get("/api/audit")
async def audit_status(_: str = Depends(require_api_key)) -> dict:
    return {
        "enabled": service.mim.config.audit.enabled,
        "db_path": str(service.mim.config.audit.db_path),
        "logs_enabled": service.mim.config.logs.enabled,
    }


@app.post("/api/transcribe")
async def transcribe(
    audio_file: UploadFile = File(...),
    _: str = Depends(require_api_key),
) -> dict:
    if not audio_file.filename:
        raise HTTPException(status_code=400, detail="audio file is required")
    payload = await audio_file.read()
    return service.transcribe_audio_bytes(audio_file.filename, payload)


@app.post("/api/voice")
async def voice_turn(
    audio_file: UploadFile = File(...),
    _: str = Depends(require_api_key),
) -> dict:
    payload = await audio_file.read()
    return service.voice_turn_from_audio(audio_file.filename, payload)


@app.post("/api/read-out")
async def read_out(payload: ReadOutRequest, _: str = Depends(require_api_key)) -> StreamingResponse:
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    wav_bytes = service.read_out(payload.text)
    return StreamingResponse(
        io.BytesIO(wav_bytes),
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=read_out.wav"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
