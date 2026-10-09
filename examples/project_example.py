from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel

from mim_ai import Mim

app = FastAPI(title="MIM Demo API", version="0.1.0")

config_path = os.environ.get("MIM_CONFIG", "mimExemple.yaml")
service = Mim.from_config(config_path)


class NormalizeRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = "demo-session"
    user_ref: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "config": config_path}


@app.post("/normalize")
def normalize(req: NormalizeRequest) -> dict:
    cleaned = service.normalizer.normalize(req.text)
    return {"input": req.text, "output": cleaned}


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    reply = service.chat(req.message, session_id=req.session_id, user_ref=req.user_ref)
    return {"reply": reply.text, "trace_id": reply.trace_id}


@app.post("/voice")
def voice() -> dict:
    if not service.config.voice.enabled:
        return {"status": "disabled", "message": "voice is disabled in config"}
    return {"status": "ready", "message": "voice pipeline configured"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("examples.project_example:app", host="0.0.0.0", port=8000, reload=False)
