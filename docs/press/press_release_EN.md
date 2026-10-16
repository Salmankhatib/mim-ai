# PRESS RELEASE

**FOR IMMEDIATE RELEASE**

---

## Moroccan Developer Launches MIM-AI: The Open-Source SDK Bridging Morocco's New Darija AI Models and Production Applications

**First Python toolkit purpose-built for Moroccan Darija development — aligned with the MTNRA–Mistral convention and the Maroc IA 2030 national roadmap**

---

**Casablanca, Morocco — October 2026** — Salman KHATIB, a Moroccan software developer, today announced the public release of **MIM-AI** (pip install mim-ai), an open-source Python SDK that provides the missing production layer between Morocco's newly released Darija AI models and real-world applications.

The release comes in direct response to the landmark **MTNRA–Mistral AI convention** signed in September 2025, which produced two foundational open-source tools — a Moroccan Darija dialect classifier and a Voxtral-based speech recognition model. MIM-AI is built to integrate with both.

---

### The Problem MIM-AI Solves

Morocco's **Maroc IA 2030** national roadmap — targeting 100 billion MAD in GDP contribution, 50,000 new jobs, and 200,000 trained AI talents — has accelerated the availability of Moroccan-language AI models. However, a critical gap has persisted between these foundational models and the production-grade applications that citizens, businesses, and government services need.

"A developer who wants to build a Darija voice application today — a call center bot, a citizen service assistant, a voice-enabled Idarati AI integration — still has to solve five or six infrastructure problems before writing their first line of business logic," said Khatib. "MIM-AI eliminates that gap entirely."

---

### What MIM-AI Delivers

MIM-AI is a configuration-first Python SDK with five integrated modules:

**🧹 Darija Normalizer** — Processes real-world Moroccan text in under 5 milliseconds with no GPU required. Handles Arabizi (romanized Arabic), code-switching between Arabic, Darija, French, and English, and inconsistent orthography. Uses a hand-curated Arabizi dictionary rather than ambiguous character-level transliteration.

**🛡️ PII Anonymizer** — Redacts personally identifiable information using native Moroccan patterns, including CIN (Carte d'Identité Nationale) numbers and Moroccan phone formats. Built on Microsoft Presidio with Morocco-specific recognizers added.

**🤖 Chatbot Module** — Wraps any OpenAI-compatible language model endpoint — including MNTRA/Mistral's Darija API — with session management, intent detection, and tool calling.

**🎙️ Voice Pipeline** — A complete speech-to-text → normalization → chatbot → text-to-speech pipeline in a single method call, configurable for MNTRA's Voxtral model.

**📜 Audit Logger** — A hash-chained event log aligned with Moroccan **Law 09-08** data protection obligations and the **ISO 42001** AI management standard. Compliance ships by default.

---

### Strategic Alignment

MIM-AI is explicitly designed to integrate with Morocco's sovereign AI ecosystem:

- Pre-configured for MNTRA/Mistral API endpoints
- Audit trail implementation satisfies Law 09-08 data protection requirements
- Voice pipeline supports the Voxtral-based ASR model released under the MTNRA–Mistral convention
- Architecture is designed for future integration with the Sovereign AI Marketplace and Idarati AI public services platform

"Morocco's government has correctly identified that sovereign AI requires both foundational models and a local developer ecosystem," Khatib said. "MIM-AI is a contribution to that ecosystem — the glue layer that turns Morocco's open-source models into shipped products."

---

### Availability

MIM-AI v0.1.0 is available now under the MIT license:

- **PyPI:** `pip install mim-ai`
- **GitHub:** https://github.com/salmankhatib06/mim-ai
- **Documentation:** https://github.com/salmankhatib06/mim-ai/tree/main/docs/EN

The package supports Python 3.9 through 3.12 and runs on any platform. Core functionality (normalization and anonymization) works fully offline with no external API required.

---

### About the Developer

Salman KHATIB is a Moroccan software developer focused on production-grade AI tooling. MIM-AI is an open-source project developed independently and released for the benefit of Morocco's developer community.

---

### Media Contact

**Salman KHATIB**  
Email: slamankhatib06@gmail.com  
GitHub: https://github.com/salmankhatib06/mim-ai

---

*Press kit materials including technical fact sheet and project overview are available at:*  
*https://github.com/salmankhatib06/mim-ai/tree/main/docs/press*

---

**###**
