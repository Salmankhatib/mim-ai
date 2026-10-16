# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-10-15

### 🎉 Initial Release — "Last Mile"

MIM is the production bridge between Morocco's open-source Darija AI models and the applications that need to use them.

This release covers the full pipeline: text normalization → PII anonymization → LLM chatbot → voice pipeline → Law 09-08 audit trail.

### Added

#### 🧹 Normalizer
- Three-layer Darija text normalization pipeline (cleaning → rule-based → optional LLM)
- Arabizi dictionary lookup (whole-word, not character-level transliteration)
- Arabic-script rules: Alef/Ya unification, tashkeel removal, Arabic-Indic digit normalization
- URL, @mention, and #hashtag preservation with config toggles
- `NormalizationReport` diagnostics: OOV flags, dictionary hits, jargon tracking
- **Under 5 ms** on modern CPU — zero model inference by default
- Optional Layer 3: LLM refinement (on_oov / on_mixed / always trigger modes)
- Built-in support for MNTRA/Mistral Darija endpoint

#### 🛡️ Anonymizer
- Config-first PII redaction powered by Microsoft Presidio
- Morocco-specific recognizers: **CIN** (national identity card) and **Moroccan phone numbers**
- Per-entity operator mapping (replace, mask, hash, redact)
- Custom pattern injection via YAML or runtime dict
- `AnonymizationResult` with redacted text + entity spans

#### 🤖 Chatbot
- OpenAI-compatible LLM wrapper (works with MNTRA/Mistral, OpenAI, any local endpoint)
- Session history with configurable TTL (memory, SQLite, PostgreSQL, MySQL, MongoDB)
- Intent classification integration
- Tool calling with configurable max iterations
- Normalizer pre-processing and audit logging built-in

#### 🎙️ Voice Pipeline
- STT → Normalizer → Intent → Chatbot → TTS full pipeline
- Standalone `listen()`, `speak()`, and `listen_and_reply()` methods
- Voice Activity Detection (VAD) with configurable threshold
- Configurable audio device, sample rate, and silence timeout
- Supports any OpenAI-compatible STT/TTS endpoint (Whisper, MNTRA Voxtral, etc.)

#### 📜 Audit & Logging
- **AuditLogger** — hash-chained event log aligned with **Law 09-08** and **ISO 42001**
- Configurable retention (default 90 days), erasure support
- **NormalizerLogger** — per-call normalizer telemetry for OOV tracking and dictionary improvement
- Backends: SQLite (default), PostgreSQL, MySQL, MongoDB, JSONL file

#### ⚙️ Config System
- Single `config.yaml` controls every subsystem
- `Mim.from_config("config.yaml")` — one line to start
- `mim-init` CLI command generates the default config in your project
- All subsystems are **lazily loaded** — unused modules are never imported

### Notes
- Python 3.9–3.12 supported
- Zero mandatory cloud dependency — normalizer and anonymizer work fully offline
- Chatbot and voice require a reachable provider endpoint

[0.1.0]: https://github.com/salmankhatib06/mim-ai/releases/tag/v0.1.0
