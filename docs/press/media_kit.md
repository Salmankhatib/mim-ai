# MIM-AI Media Kit

*For journalists, bloggers, and content creators covering Moroccan tech and AI*

---

## At a Glance

| | |
|---|---|
| **Product name** | MIM-AI |
| **Tagline** | The last mile of Morocco's AI stack |
| **Category** | Open-source Python SDK / AI Developer Tooling |
| **License** | MIT (completely free, commercial use allowed) |
| **Install** | `pip install mim-ai` |
| **Language** | Python 3.9–3.12 |
| **Released** | October 2026 |
| **Author** | Salman KHATIB (Moroccan developer) |
| **GitHub** | https://github.com/salmankhatib06/mim-ai |

---

## One-Line Summary

**MIM-AI is the open-source Python SDK that bridges Morocco's new Darija AI models and production applications — with built-in text normalization, PII anonymization, voice pipeline, and Law 09-08 audit trail.**

---

## Key Facts for Journalists

### The Numbers
- **< 5 ms** — normalizer latency (no GPU required)
- **92** — automated tests, all passing
- **5** — integrated modules in one package
- **3** — languages handled natively: Arabic, Darija, French (English preserved)
- **0** — external API calls required for core functionality (normalizer + anonymizer work offline)
- **100B MAD** — GDP target of Maroc IA 2030, the national AI roadmap MIM aligns with

### The Strategic Connection
MIM-AI was directly inspired by the **MTNRA–Mistral AI convention** (signed September 12, 2025 in Rabat). That agreement produced open-source Darija AI models. MIM-AI provides the production layer needed to use those models in real applications.

### Why It Matters
Morocco's national AI strategy (Maroc IA 2030) sets ambitious targets. But government models alone don't ship products. MIM-AI is the tool that lets Moroccan developers turn those models into customer-facing applications — call center bots, citizen service assistants, voice-enabled admin tools — without reinventing the infrastructure from scratch.

---

## Module Summary

| Module | What It Does | Key Differentiator |
|--------|-------------|-------------------|
| **Normalizer** | Cleans Arabizi and code-switched Darija text | Under 5ms, offline, no neural network |
| **Anonymizer** | Redacts PII (CIN, phone, names, etc.) | Native Moroccan CIN + phone patterns |
| **Chatbot** | LLM wrapper with sessions + intents | Pre-wired for MNTRA/Mistral API |
| **Voice** | Full STT→TTS pipeline | One method call, one config file |
| **Audit** | Compliance event log | Law 09-08 + ISO 42001 by default |

---

## Quotes (Attribution: Salman KHATIB, Creator of MIM-AI)

> "Morocco's government has built the foundation. The MTNRA–Mistral convention gave us open-source Darija models. Maroc IA 2030 gave us a clear direction. MIM-AI is the bridge between that foundation and the applications Moroccan users will actually use."

> "A developer who wants to build a Darija voice application today still has to solve six infrastructure problems before writing their first line of business logic. MIM eliminates that week."

> "The Arabizi dictionary took weeks to build correctly — because character-level transliteration is fundamentally ambiguous. '3' could be 'ع' or 'غ'. You have to treat it as a vocabulary problem, not a phoneme problem. That's a decision based on how Moroccan developers actually write, not how linguists think they write."

> "Law 09-08 compliance is not optional for any application handling Moroccan user data. We made it the default, not an afterthought. That's what 'production-grade' means in Morocco."

---

## Background: Morocco's AI Moment

| Date | Event |
|------|-------|
| Sept 25, 2024 | Maroc Digital 2030 strategy officially launched |
| July 1–2, 2025 | 1st National AI Conference (Assises Nationales de l'IA), UM6P, Rabat |
| Sept 12, 2025 | MTNRA–Mistral AI convention signed (Seghrouchni × Arthur Mensch) |
| Jan 2026 | Maroc IA 2030 operational roadmap formalized |
| Late Sept 2026 | First Mistral–MNTRA open-source deliverables: Darija LID + Voxtral ASR |
| Oct 2026 | **MIM-AI v0.1.0 released** |

---

## Contact

**Salman KHATIB**  
Email: slamankhatib06@gmail.com  
GitHub: https://github.com/salmankhatib06/mim-ai  

---

## Assets Available on Request

- GitHub repository (full source code)
- Demo video (in production)
- Technical architecture diagram
- Code screenshots for web/print

---

*All materials in this kit may be used freely by press with attribution.*
