# MIM — Mim AI

> **A config-first toolkit for Moroccan Darija AI.**  
> Built by a Moroccan dev, for Moroccan devs. Made to sit between the country's new AI models and the applications that need to use them.

---

## 🇲🇦 The Gap

Morocco is building its AI foundation. The MNTRA–Mistral partnership has already released open-source bricks — a Darija language identifier, and Voxtral for speech. The sovereign AI marketplace and Idarati AI are on the roadmap. The models are arriving.

What's missing is the **last mile**.

A developer in Casablanca who wants to build a voice-enabled app today still has to:
1. Find the right model.
2. Figure out how to run it.
3. Handle audio I/O.
4. Clean up messy Darija text before it reaches an LLM.
5. Log everything so it survives a compliance review.

That's a week of work before the first feature ships. **MIM is an opinionated answer to that gap.**

---

## ✨ What MIM Is

A small Python SDK that gives Moroccan developers a **drop-in pipeline** for Darija text and voice:

- 🧹 **Normalizer** — Cleans real-world Darija (Arabizi, code-switching, inconsistent orthography) before it hits a model.
- 🤖 **Chatbot** — Wraps any LLM with tools, sessions, and intent classification.
- 🎙️ **Voice** — STT, TTS, and a full listen-and-reply pipeline.
- 📜 **Logging** — Audit trail aligned with Moroccan law 09-08 and ISO 42001.

*One YAML file. Any model. Any endpoint.*

---

## 🚫 What MIM Is Not

- **Not a model:** We don't train anything.
- **Not a framework:** We don't want you to learn us.
- **Not the final word:** It's a proposition — open for community contribution.

---

## 🚀 Quick Start

### 1. Install

```bash
pip install mim-ai

```

### 2. Configure (`mim.yaml`)

Define your models, keys, and pipeline settings in a single unified configuration file.

### 3. Use It

```python
from mim_ai import Mim

# Initialize from config
mim = Mim.from_config("mim.yaml")

# Chat
reply = mim.chat("salam, chkoun nta?")

# Voice pipeline
voice = mim.listen_and_reply(session_id="user-42")

# Just transcription
text = mim.transcribe("call.wav")

# Just readout
mim.speak("Salam, kifach nta lyoum?", play_audio=True)

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
| **3 — LLM Refinement** | `200–800 ms` | Optional, off by default (opt-in for polishing leftovers) |

> **Dictionary Customization:** The dictionary is yours to grow. Ship a base of common Darija, add your app's jargon in a side file. Every skipped token is logged so you can refine from real usage, not guesses.

---

## 🇲🇦 Made in Morocco, for Morocco

This is a **Made in Morocco** tool, built in phase with the national AI strategy:

* **Aligned with AI Made in Morocco 2030** — Contributing toward the 100B MAD GDP target, 50,000 jobs target, and 200,000 trained talents target.
* **Ecosystem Integration** — Built to plug directly into the sovereign AI marketplace and to serve Idarati AI and public-facing services.
* **Compliant by Design** — Aligned with **Law 09-08** (audit logs hash user text, honor erasure requests, and expire on schedule) and **ISO 42001**.

*MIM is not infrastructure. It's the glue between the infrastructure Morocco is building and the applications Morocco's developers want to ship.*

---

## 📂 What's Inside

```text
mim_ai/
├── normalizer/   # Fast, config-first Darija text normalization
├── chatbot/      # LLM wrapper with tools, sessions, intents
├── voice/        # STT, TTS, VAD, full listen-and-reply pipeline
├── intents/      # English-named, multilingual-matched intent registry
├── audit/        # Law 09-08 + ISO 42001 aligned logging
└── config.py     # One YAML, one loader, one Mim object

```

> **Note:** Every subsystem is optional. If your configuration only enables the normalizer, nothing else loads. 