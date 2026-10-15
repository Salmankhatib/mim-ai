# Moroccan App Example

This example app shows how to wire the MIM toolkit into a small FastAPI project for a Moroccan Darija workflow.

## Features

- Normalizer API
- Audit + normalizer logs
- Chatbot integration
- Full voice pipeline entry point
- Audio transcription endpoint
- Text-to-speech read-out endpoint
- Basic bearer-token auth

## Project layout

```text
examples/moroccan_app_example/
├── app/
│   ├── __init__.py
│   ├── auth.py
│   ├── main.py
│   └── services.py
├── templates/
│   └── index.html
├── config.yaml
├── intents.yaml
├── pyproject.toml
└── README.md
```

## Quick start

From this directory:

```bash
python -m pip install -U pip
python -m pip install -e ../..
python -m pip install fastapi uvicorn jinja2 python-multipart pydub
```

Install ffmpeg and make sure it is available on PATH for real `.mp3` uploads and speech synthesis.

Then run:

```bash
export MIM_APP_TOKEN="demo-moroccan-token"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

- http://localhost:8000/
- http://localhost:8000/docs

## Example calls

### Normalize

```bash
curl -X POST http://localhost:8000/api/normalize \
  -H "Authorization: Bearer demo-moroccan-token" \
  -H "Content-Type: application/json" \
  -d '{"text": "salam wa7ed 3la ekher"}'
```

### Chat

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer demo-moroccan-token" \
  -H "Content-Type: application/json" \
  -d '{"message": "salam, bghit n3ref status lorder dyali", "session_id": "demo-session"}'
```

### Transcribe audio

```bash
curl -X POST http://localhost:8000/api/transcribe \
  -H "Authorization: Bearer demo-moroccan-token" \
  -F "audio_file=@demo.wav"
```

### Read aloud

```bash
curl -X POST http://localhost:8000/api/read-out \
  -H "Authorization: Bearer demo-moroccan-token" \
  -H "Content-Type: application/json" \
  -d '{"text": "Salam, service dyalna 3ndek."}' --output audio.wav
```

## Notes

- The example root config is in `config.yaml` and is loaded automatically by the app.
- Chat, STT, and TTS routes are wired to the MIM config and will work when the configured providers are reachable and credentials are valid.
- Local-safe logic like normalization and audit logging works without external provider keys.
