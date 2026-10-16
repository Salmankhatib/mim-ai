# LinkedIn Launch Post — MIM-AI

> **Post in:** English (primary) with Darija/French phrases for authenticity  
> **Tone:** Professional, proud, technical-but-accessible  
> **Target audience:** Moroccan developers, Arab tech community, AI researchers, government tech officers, startup founders

---

## POST TEXT (Copy-paste ready)

---

🇲🇦 **I just published MIM-AI — the Python SDK that bridges Morocco's new open-source AI models and production applications.**

```
pip install mim-ai
```

Here's why I built it, and why it matters now.

---

**The context:**

Morocco signed a landmark AI convention with Mistral AI in September 2025. Together with the MTNRA, Mistral released open-source Darija tools: a dialect classifier and a Voxtral-based speech recognition model. The Maroc IA 2030 roadmap has real targets — 100B MAD in GDP, 50,000 jobs, 200,000 trained talents.

The models are here. The infrastructure is being built.

**But there's a gap.**

Every developer who tries to build a Darija-native app today hits the same wall: raw models don't handle messy Arabizi, don't redact Moroccan CIN numbers, don't generate Law 09-08 compliant audit trails, and don't wire STT → chatbot → TTS out of the box.

That's a week of boilerplate before the first feature ships.

---

**MIM eliminates that week.**

Five modules, one config file:

🧹 **Normalizer** — Cleans Arabizi and code-switched Darija in under 5ms. Zero GPU, zero model inference. Pure Python.

```python
mim.normalizer.normalize("salam wa7ed 3la ekher")
# → سلام واحد على الآخر
```

🛡️ **Anonymizer** — PII redaction with native Moroccan CIN and phone number patterns.

```python
anonymize("Mon CIN est AB58075")
# → Mon CIN est <CIN_MA>
```

🤖 **Chatbot** — Wraps MNTRA/Mistral (or any OpenAI-compatible endpoint) with sessions, intents, and tool calling.

🎙️ **Voice** — `mim.listen_and_reply()`. One method. Full STT → normalize → chat → TTS pipeline.

📜 **Audit** — Hash-chained, Law 09-08 compliant event log. Ships by default.

---

**This is not just a developer tool.**

Every application built on Morocco's sovereign AI marketplace needs this layer. Every call center, every government chatbot, every startup building on Idarati AI — they all need Darija normalization, PII protection, and compliance logging.

MIM is the glue between the models Morocco is building and the applications Morocco's users will use.

---

**It's open-source. It's MIT licensed. It's made in Morocco 🇲🇦**

GitHub: [link]
PyPI: pip install mim-ai
Docs: [link]

If you're a Moroccan developer, researcher, or startup building with Darija AI — I'd love your feedback, your Arabizi edge cases, and your PRs.

kayn chi haja kat7awwaj? ktab liya. 🙏

---

#MoroccoAI #DarijaAI #AIMaroc #MadeInMorocco #MachineLearning #NLP #Python #OpenSource #MarocIA2030 #MistralAI #MTNRA

---

## POSTING TIPS

- Post on a **Tuesday or Wednesday morning** (Moroccan time, 9–11am) for best reach
- Add the first screenshot of `pip install mim-ai` as an image attachment
- Pin a comment with the GitHub link
- Tag: @Ministry of Digital Transition Morocco, @Mistral AI, @MNTRA if possible
- Engage with every comment in the first 2 hours (LinkedIn algorithm boost)
- Cross-post to relevant LinkedIn groups: Morocco Tech Community, MoroccoAI, Arab Developers
