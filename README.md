# MIM — Mim AI

[![PyPI version](https://img.shields.io/pypi/v/mim-ai.svg?color=brightgreen)](https://pypi.org/project/mim-ai/)
[![Python versions](https://img.shields.io/pypi/pyversions/mim-ai.svg)](https://pypi.org/project/mim-ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-92%20passed-brightgreen)](./tests/)
[![Made in Morocco](https://img.shields.io/badge/Made%20in-Morocco%20🇲🇦-cc0000)](https://github.com/salmankhatib06/mim-ai)

> **A config-first Python SDK for Moroccan Darija AI.**  
> Built by a Moroccan developer, for Moroccan developers.  
> The last-mile bridge between Morocco's open-source AI models and the apps that use them.

---

## 🇲🇦 The Gap

Morocco is building its AI foundation fast. The **MTNRA–Mistral AI convention** (signed September 2025) has already delivered open-source bricks: a Darija language-identification classifier and a Voxtral-based speech recognition model. The **Sovereign AI Marketplace** and **Idarati AI** are rolling out. The **Maroc IA 2030** roadmap targets 100 billion MAD in GDP contribution and 50,000 new jobs.

**The models are arriving. What's missing is the last mile.**

A developer who wants to build a voice-enabled Darija app today still has to:

1. Find the right model.
2. Figure out how to run it.
3. Handle audio I/O.
4. Clean up messy Darija/Arabizi text before it reaches an LLM.
5. Anonymize PII before logging.
6. Log everything so it survives a Law 09-08 compliance review.

That's a week of work before the first feature ships. **MIM is an opinionated answer to that gap.**

---

## ✨ What MIM Is

A small Python SDK that gives Moroccan developers a **drop-in pipeline** for Darija text and voice:

- 🧹 **Normalizer** — Cleans real-world Darija (Arabizi, code-switching, inconsistent orthography) before it hits a model. Runs in **under 5 ms**, zero GPU.
- 🛡️ **Anonymizer** — Config-first PII redaction using Presidio, with Morocco-specific CIN and phone patterns.
- 🤖 **Chatbot** — Wraps any LLM with tools, sessions, and intent classification. Pre-wired for MNTRA/Mistral endpoints.
- 🎙️ **Voice** — STT → Normalizer → Chatbot → TTS full pipeline. Three methods, one config, zero bloat.
- 📜 **Audit** — Hash-chained audit trail aligned with **Law 09-08** and **ISO 42001**. Out-of-the-box compliance.

*One YAML file. Any model. Any endpoint.*

---

## 🚫 What MIM Is Not

- **Not a model:** We don't train anything.
- **Not a framework:** We don't want you to learn a new abstraction.
- **Not the final word:** It's a proposition — open for community contribution.

---

## 🚀 Quick Start

### 1. Install

```bash
pip install mim-ai
```

Microphone and speaker support are included in the standard install. Install the optional `voice` extra only if you also need decoding for non-WAV speech formats:

```bash
pip install "mim-ai[voice]"
```

### 2. Generate Your Config

```bash
mim-init
```

This creates a `config.yaml` in your project directory with all subsystems pre-configured and commented.

### 3. Use It

```python
import os
from mim_ai import Mim

# Initialize from config
mim = Mim.from_config("config.yaml")

# Local-safe flow: normalization + anonymization work without external services.
normalized = mim.normalizer.normalize("salam wa7ed 3la ekher")
print(normalized)  # سلام واحد على الآخر

from mim_ai import anonymize
redacted = anonymize("Mon CIN est AB58075 et mon tel est 0612345678")
print(redacted.text)  # Mon CIN est <CIN_MA> et mon tel est <PHONE_MA>

# Chat and voice require configured provider credentials and a reachable endpoint.
if mim.config.chatbot.enabled and os.getenv(mim.config.chatbot.llm_api_key_env):
    reply = mim.chat("salam, chkoun nta?", session_id="user-42")
    print(reply.text)

# Voice records from the default microphone until speech ends, then replies aloud.
# Set the STT/TTS API credentials from config.yaml before enabling this call.
# voice_reply = mim.listen_and_reply(session_id="user-42")
```

---

## ⚡ The Normalizer — Built for Production

Real-time applications don't have 300 ms to spare on text cleaning.

The MIM normalizer runs in **under 5 ms on a modern CPU** with **zero model inference**. It is pure Python: Unicode normalization, a hand-curated Arabizi dictionary, and Arabic-script rules. No neural network, no GPU, no warmup.

For a voice pipeline, that's the difference between a live conversation and a laggy one.

### Pipeline Layers (Cheapest First)

| Layer | Speed / Cost | What it does |
| --- | --- | --- |
| **1 — Universal Cleaning** | `~0 ms` | Whitespace, control characters, URL protection |
| **2 — Rule-based Darija** | `< 5 ms` | Alef/Ya unification, Arabizi dictionary lookup *(Default)* |

> **Dictionary Customization:** The dictionary is yours to grow. Ship a base of common Darija, add your app's jargon in a side file. Every skipped token is logged so you can refine from real usage, not guesses.

---

## 🛡️ Anonymizer — Morocco-Specific PII Redaction

```python
from mim_ai import anonymize

result = anonymize("Mon CIN est AB58075 et mon tel est 0612345678")
print(result.text)    # Mon CIN est <CIN_MA> et mon tel est <PHONE_MA>
print(result.entities_found)  # [EntityResult(type='CIN_MA', ...), ...]
```

Built on top of Microsoft Presidio with native Moroccan recognizers:
- **CIN patterns** (Carte d'Identité Nationale) — `AB123456`, `A123456`, etc.
- **Moroccan phone numbers** — all mobile and fixed-line formats
- Fully configurable per-entity operators: `replace`, `mask`, `hash`, `redact`

Presidio requires the English spaCy model. Install it after `mim-ai` and before using the anonymizer:

```bash
python -m spacy download en_core_web_lg
```

There is no automatic regex-only fallback. See the [anonymizer setup guide](docs/anonymizer/README.md) for details.

---

## 📜 Compliance — Law 09-08 & ISO 42001

MIM ships compliance by default:

```yaml
audit:
  enabled: true
  backend: sqlite
  hash_chain: true        # tamper-evident chain
  retention_days: 90      # auto-purge on schedule
```

Every chat turn is logged with a hash chain. Erasure requests are honored. Logs expire automatically. No extra code required.

---

## 🇲🇦 Made in Morocco, for Morocco

This is a **Made in Morocco** tool, built in step with the national AI strategy:

* **Aligned with Maroc IA 2030** — Contributing toward the 100B MAD GDP target, 50,000 jobs, and 200,000 trained talents.

* **MTNRA–Mistral Partnership** — Pre-configured for the MNTRA/Mistral Darija API endpoint. When Morocco's sovereign models ship, MIM is already wired for them.

* **Ecosystem Integration** — Built to plug directly into the Sovereign AI Marketplace and to serve Idarati AI and public-facing government services.

* **Compliant by Design** — Aligned with **Law 09-08** (audit logs hash user text, honor erasure requests, and expire on schedule) and **ISO 42001**.

*MIM is not infrastructure. It's the glue between the infrastructure Morocco is building and the applications Morocco's developers want to ship.*

---

## 📂 What's Inside

```text
mim_ai/
├── anonymizer/   # Config-first PII redaction with Presidio + Morocco-specific rules
├── normalizer/   # Fast, config-first Darija text normalization (< 5 ms, zero GPU)
├── chatbot/      # LLM wrapper with tools, sessions, intents
├── voice/        # STT, TTS, VAD, full listen-and-reply pipeline
├── intents/      # English-named, multilingual-matched intent registry
├── audit/        # Law 09-08 + ISO 42001 aligned logging
└── config.py     # One YAML, one loader, one Mim object
```

> **Note:** Every subsystem is optional. If your configuration only enables the normalizer, nothing else loads. No torch, no sounddevice, no HTTP client.

---

## 📚 Documentation

- English: [docs/EN/tutorial.md](docs/EN/tutorial.md)
- Français: [docs/FR/tutorial.md](docs/FR/tutorial.md)
- Architecture: [docs/EN/architecture.md](docs/EN/architecture.md) / [docs/FR/architecture.md](docs/FR/architecture.md)
- Manifesto: [docs/EN/manifesto.md](docs/EN/manifesto.md) / [docs/FR/manifesto.md](docs/FR/manifesto.md)
- Feature guides: [Normalizer](docs/EN/features/normalizer.md) · [Chatbot](docs/EN/features/chatbot.md) · [Voice](docs/EN/features/voice.md) · [Audit](docs/EN/features/audit.md)
- Contributing: [docs/EN/contributing.md](docs/EN/contributing.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)

---

## 🧪 Minimal Project Example

A FastAPI example is included in [examples/project_example.py](examples/project_example.py). It demonstrates how to expose MIM through a simple HTTP service.

---

## 🔖 PyPI Release

Before publishing a release candidate:

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

Upload to TestPyPI first:

```bash
python -m twine upload --repository testpypi dist/*
```

Then to PyPI:

```bash
python -m twine upload dist/*
```
