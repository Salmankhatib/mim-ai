# MIM — Mim AI

**A config-first toolkit for Moroccan Darija AI.**
Built by a Moroccan dev, for Moroccan devs. Made to sit between the country's new AI models and the applications that need to use them.

---

## The gap

Morocco is building its AI foundation. The MNTRA–Mistral partnership has already released open-source bricks — a Darija language identifier, and Voxtral for speech. The sovereign AI marketplace and Idarati AI are on the roadmap. The models are arriving.

What's missing is the **last mile**.

A developer in Casablanca who wants to build a voice-enabled app today still has to: find the right model, figure out how to run it, handle audio I/O, clean up messy Darija text before it reaches an LLM, and log everything so it survives a compliance review.

That's a week of work before the first feature ships.

MIM is one opinionated answer to that gap.

---

## What MIM is

A small Python SDK that gives Moroccan developers a **drop-in pipeline** for Darija text and voice:

- **Normalizer** — cleans real-world Darija (Arabizi, code-switching, inconsistent orthography) before it hits a model.
- **Chatbot** — wraps any LLM with tools, sessions, and intent classification.
- **Voice** — STT, TTS, and a full listen-and-reply pipeline.
- **Logging** — audit trail aligned with Moroccan law 09-08 and ISO 42001.

One YAML file. Any model. Any endpoint.

---

## What MIM is not

- Not a model. We don't train anything.
- Not a framework. We don't want you to learn us.
- Not the final word. It's a proposition — see below.

---

## Quick start

**1. Install**

```bash
pip install mim-ai

**2. Write mim.yaml**


**3. use it**
from mim_ai import Mim

mim = Mim.from_config("mim.yaml")

# Chat
reply = mim.chat("salam, chkoun nta?")

# Voice
voice = mim.listen_and_reply(session_id="user-42")

# Just transcription
text = mim.transcribe("call.wav")

# Just readout
mim.speak("Salam, kifach nta lyoum?", play_audio=True)

The normalizer — built for production.

Real-time applications don't have 300 ms to spare on text cleaning.

The MIM normalizer runs in under 5 ms on a modern CPU, zero model inference. It's pure Python:

Unicode normalization, a hand-curated Arabizi dictionary, and Arabic-script rules. No neural network, no GPU, no warmup.

For a voice pipeline, that's the difference between a live conversation and a laggy one.

Layers, cheapest first :

Layer	Cost    Does
1 — Universal cleaning	~0 ms	Whitespace, control chars, URL protection
2 — Rule-based Darija	< 5 ms	Alef/Ya unification, Arabizi dict lookup
3 — LLM refinement	200–800 ms	Optional, off by default

Layers 1 and 2 are the default. Layer 3 is opt-in for teams that want the LLM to polish the leftovers.

The dictionary is yours to grow. Ship a base of common Darija, add your app's jargon in a side file. Every skipped token is logged so you can refine from real usage, not guesses.

Made in Morocco, for Morocco
This is a Made in Morocco tool, built in phase with the national AI strategy:

Aligned with AI Made in Morocco 2030 — the 100B MAD GDP target, the 50,000 jobs target, the 200,000 trained talents target.

Built to plug directly into the sovereign AI marketplace and to serve Idarati AI and public-facing services.

Compliant by design with Law 09-08 — audit logs hash user text, honor erasure requests, and expire on schedule.

Written by a Moroccan dev who needed it and couldn't find it.


MIM is not infrastructure. It's the glue between the infrastructure Morocco is building and the applications Morocco's developers want to ship.

What's inside

Text
mim_ai/
├── normalizer/     fast, config-first Darija text normalization
├── chatbot/        LLM wrapper with tools, sessions, intents
├── voice/          STT, TTS, VAD, full listen-and-reply pipeline
├── intents/        English-named, multilingual-matched intent registry
├── audit/          law 09-08 + ISO 42001 aligned logging
└── config.py       one YAML, one loader, one Mim object

Every subsystem is optional. If your config only enables the normalizer, nothing else loads.



