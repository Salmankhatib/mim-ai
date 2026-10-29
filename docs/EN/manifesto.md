# MIM Manifesto
## The Last Mile of Morocco's AI Revolution

---

## Why This Project Exists

On September 12, 2025, Morocco's Minister of Digital Transition, **Amal El Fallah Seghrouchni**, signed a landmark convention with Mistral AI CEO Arthur Mensch in Rabat. The agreement committed both parties to building AI that reflects Morocco's languages and culture — not just importing models designed for someone else.

The Minister said it plainly: **"Morocco wants to build AI, not just use it."**

And Morocco is delivering. The **Maroc IA 2030** roadmap — with targets of 100 billion MAD in GDP contribution, 50,000 new jobs, and 200,000 trained AI talents — is backed by real infrastructure: the JAZARI Institute network, a sovereign AI marketplace, and open-source Darija models released in partnership with Mistral AI.

But a gap remains.

---

## The Gap We Solve

Morocco has models. What Morocco's developers still lack is the **production layer** between those models and working applications.

Today, a developer building a Darija voice app must:

1. Find and run the right model
2. Pre-process messy Arabizi/Darija/French code-switching before it reaches an LLM
3. Anonymize user PII before storing anything
4. Build an audit trail that satisfies Law 09-08
5. Wire together STT → normalization → intent detection → LLM → TTS
6. Handle every failure mode so the app survives production

That's a full week of infrastructure before the first feature ships.

**MIM eliminates that week.**

---

## Principles

**Darija-first, not English-first**  
Every design decision is evaluated against how it handles real Moroccan text — code-switching, Arabizi, French mix-ins, Arabic-script variation.

**Config over code**  
One YAML file controls every subsystem. Change providers, swap models, tune thresholds — without touching application code.

**Provider-agnostic integration**  
MIM works with MNTRA/Mistral endpoints today and any OpenAI-compatible API tomorrow. We don't lock you in.

**Auditability by default**  
Compliance is not an afterthought. Every chat turn is logged with a tamper-evident hash chain. Law 09-08 retention schedules run automatically.

**Low-friction developer experience**  
`pip install mim-ai`. `mim-init`. `Mim.from_config("mim_config.yaml")`. That's the entire setup path.

**Open for the community**  
The Arabizi dictionary is a community asset. Every skipped token is logged so real usage drives the next improvement.

---

## Alignment with Maroc IA 2030

The government's roadmap has three pillars. MIM contributes to all three:

**1. Sovereignty & Trust**  
MIM's anonymizer and audit logger are built for Moroccan legal requirements, not GDPR retrofits. Law 09-08 compliance is the default, not an add-on.

**2. Innovation & Competitiveness**  
MIM is the SDK that turns Morocco's open-source models into shippable products. Every startup building on MNTRA's models can skip the infrastructure week and go straight to features.

**3. Impact, Adoption & Outreach**  
Idarati AI, the Sovereign AI Marketplace, and citizen-facing government services all need Darija-aware production glue. MIM is designed to plug directly into that ecosystem.

---

## The Mission

To give Moroccan developers a lightweight, config-first toolkit that helps them ship Arabic-script, Arabizi-aware, voice-ready, Law 09-08 compliant AI products — without reinventing the stack every time.

Morocco is building the models. We're building the last mile.

**🇲🇦 Made in Morocco. For Morocco. Open to the world.**
