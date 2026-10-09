# MIM Architecture

## Goal

MIM is designed as a config-first Darija app stack. Developers configure one YAML file, then the package builds the components they need.

## Main building blocks

### 1. Config layer

The config object is the root of the app. It holds:

- normalizer settings
- audit and logging settings
- chatbot settings
- intents settings
- voice, STT, and TTS settings

This is loaded by the `MimConfig` class and used by the `Mim` runtime wrapper.

### 2. Normalizer

The normalizer is the lowest-level feature. It cleans real Darija before it reaches a model.

It contains:

- cleaning layer
- rule-based Darija layer
- optional LLM refinement layer

### 3. Chatbot

The chatbot wraps a provider-compatible LLM, handles tool usage, stores session history, and can integrate with the normalizer and audit layers.

### 4. Voice pipeline

The voice stack includes:

- STT transcription
- optional normalizer pass
- intent matching
- chatbot turn
- TTS response

### 5. Audit and logs

The audit and normalizer logs are separate but complementary. The audit log is for compliance and accountability; the normalizer log is more operational and diagnostic.

## Runtime model

The app uses a layered composition model:

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")
```

At runtime, subsystems are created lazily. If a feature is disabled in config, it is not built.

## Why this design works

- simpler onboarding for developers
- safer deployment because behavior is defined in config
- easier to swap providers and storage backends
- clean separation between application logic and infrastructure

## Production deployments

This package is designed to work with:

- SQLite for local/dev
- PostgreSQL, MySQL, or MongoDB for durable deployments
- OpenAI-compatible model endpoints
- local or cloud TTS/STT providers
