# MIM Tutorial

This guide is for developers who want to install the package, load the config, and build a Darija-first app in a few minutes.

## 1. Install

```bash
pip install mim-ai
```

If you are working from the repository checkout:

```bash
pip install -e .
```

## 2. Start from the shipped config

The package assumes a config-first workflow. The default example file is `mimExemple.yaml`.

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")
```

## 3. Normalize Darija text

```python
text = "salam wa7ed 3la ekher, bghit n3ref kifach nt3amro app?"
clean = app.normalizer.normalize(text)
print(clean)
```

This is useful before sending user text to an LLM or a downstream workflow.

## 4. Use the chatbot

```python
reply = app.chat("salam, chkoun nta?", session_id="demo-user")
print(reply.text)
```

This calls the configured LLM and uses the configured session history backend.

## 5. Use the voice pipeline

```python
voice_reply = app.listen_and_reply(session_id="demo-user")
print(voice_reply.transcript)
print(voice_reply.reply_text)
```

This requires a real microphone input and a working STT/TTS provider config.

## 6. Best practice

Keep a single config file and change provider values there instead of changing code. This makes environment-specific deployments easy.

## 7. Minimal app idea

A small app can be built with:

- normalizer for Arabic/Arabizi cleanup
- chatbot for business conversations
- audit logger for regulatory traceability
- voice pipeline for call-center or IVR workflows

---

## Example project flow

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")

raw = "salam, 3ndna 9a9a"
clean = app.normalizer.normalize(raw)
reply = app.chat(clean, session_id="demo")
print(reply.text)
```
