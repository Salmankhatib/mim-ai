# Voice pipeline

## What it does

The voice stack handles transcription, optional normalization, intent detection, conversation, and speech output.

## Why it matters

Voice is one of the most human ways to interact with an app, especially in call-center or field-service contexts.

## Example

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")
reply = app.listen_and_reply(session_id="demo")
print(reply.transcript)
print(reply.reply_text)
```

## Config keys

- `voice.enabled`
- `voice.use_normalizer`
- `voice.use_intents`
- `voice.use_audit_log`
- `stt.*`
- `tts.*`

## Benefits

- one voice pipeline for many providers
- easy to plug into IVR or call center flows
- keeps the app coherent through config
