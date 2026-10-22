# Voice pipeline

## What it does

The voice stack handles transcription, optional normalization, intent detection, conversation, and speech output.

## Quick start

Install voice support and its Python audio dependencies:

```bash
pip install "mim-ai[voice]"
```

Voice uses the default microphone and speaker devices. The host may also need audio system libraries (for example, PortAudio on Linux). Configure reachable STT/TTS endpoints in `config.yaml`, then set the API keys named by `stt.api_key_env` and `tts.api_key_env` in your environment. If the voice pipeline uses chat, also set `chatbot.llm_api_key_env`.

```python
from mim_ai import Mim

app = Mim.from_config("config.yaml")
reply = app.listen_and_reply(session_id="demo")
print(reply.transcript, reply.reply_text)
```

Capture uses RMS energy VAD. `voice.vad.threshold` is a normalized RMS amplitude (default `0.015`); `min_speech_ms` filters short transients, `min_silence_ms` ends an utterance, `pre_roll_ms` keeps its onset, and `start_timeout_ms` returns without calling STT if no speech is detected (`reply.status == "no_speech"`). `max_record_seconds` caps recording length. This is threshold-based, not a speech classifier; raise the threshold in noisy rooms.

If no microphone or speaker is available, audio I/O raises an `AudioError` rather than sending fabricated silence or silently skipping playback.

## Why it matters

Voice is one of the most human ways to interact with an app, especially in call-center or field-service contexts.

## Example

```python
from mim_ai import Mim

app = Mim.from_config("config.yaml")
reply = app.listen_and_reply(session_id="demo")
print(reply.transcript)
print(reply.reply_text)
```

## Config keys

- `voice.enabled`
- `voice.use_normalizer`
- `voice.use_intents`
- `voice.use_audit_log`
- `voice.use_chatbot`
- `voice.max_record_seconds`
- `voice.vad.*`
- `voice.audio.*`
- `stt.*`
- `tts.*`

Set `stt.enabled: false` to make voice transcription fail explicitly before recording. When `tts.enabled: false`, the pipeline returns the text reply without audio. With `voice.use_chatbot: false`, it returns the transcript without generating a reply.

## Benefits

- one voice pipeline for many providers
- easy to plug into IVR or call center flows
- keeps the app coherent through config
