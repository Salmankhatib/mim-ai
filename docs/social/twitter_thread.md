# Twitter / X Launch Thread — MIM-AI

> **Format:** 8-tweet thread  
> **Tone:** Punchy, technical, proud, bilingual-friendly  
> **Best time to post:** Tuesday or Wednesday, 9–11am Morocco time

---

## THREAD (Copy-paste each tweet separately)

---

**Tweet 1 — Hook (Lead tweet)**
```
🇲🇦 Morocco is building its AI stack.

The MTNRA–Mistral convention delivered open-source Darija models.
Maroc IA 2030 targets 100B MAD + 50K jobs.

But there's a gap between those models and shipping real apps.

I built MIM-AI to close it.

pip install mim-ai

🧵 Thread:
```

---

**Tweet 2 — The problem**
```
Every Moroccan dev building a Darija AI app hits the same wall:

❌ Raw models can't handle Arabizi
❌ No Moroccan CIN/phone anonymizer
❌ No Law 09-08 audit trail
❌ No voice pipeline glue

That's a full week before your first feature.

MIM deletes that week.
```

---

**Tweet 3 — Normalizer**
```
🧹 MIM Normalizer:

mim.normalizer.normalize("salam wa7ed 3la ekher")
→ سلام واحد على الآخر

• Under 5ms. Zero GPU. Pure Python.
• Handles Arabizi, code-switching, Arabic-French mix
• Dictionary-driven (no char-level transliteration ambiguity)
• OOV tokens logged for improvement
```

---

**Tweet 4 — Anonymizer**
```
🛡️ MIM Anonymizer:

anonymize("Mon CIN est AB58075 et mon tel est 0612345678")
→ Mon CIN est <CIN_MA> et mon tel est <PHONE_MA>

Native Moroccan patterns: CIN, phone numbers
Built on Microsoft Presidio
Config-driven operators: replace / mask / hash / redact
```

---

**Tweet 5 — Chatbot + Voice**
```
🤖 Chatbot — wraps MNTRA/Mistral (or any OpenAI API):

reply = mim.chat("salam, chkoun nta?", session_id="u1")

🎙️ Voice — full pipeline in one method:

voice = mim.listen_and_reply(session_id="u1")
# records → transcribes → normalizes → chats → speaks

Three methods. One config. Zero boilerplate.
```

---

**Tweet 6 — Compliance**
```
📜 Law 09-08 compliance — out of the box:

audit:
  enabled: true
  hash_chain: true
  retention_days: 90

Every chat turn is logged with a tamper-evident hash chain.
Erasure requests are honored.
Logs auto-expire.

No extra code.
```

---

**Tweet 7 — Strategic fit**
```
This isn't just a dev tool.

It's the missing SDK for:
→ Morocco's Sovereign AI Marketplace
→ Idarati AI citizen services
→ Any startup building on MNTRA models
→ Call centers, public chatbots, voice apps

MIM = the last mile of Morocco's AI stack 🇲🇦
```

---

**Tweet 8 — CTA**
```
Open-source. MIT. Made in Morocco 🇲🇦

pip install mim-ai

GitHub: [link]
Docs: [link]

kayn chi haja kat7awwaj? Reply or DM 🙏

#MoroccoAI #DarijaAI #AIMaroc #Python #NLP #MarocIA2030
```

---

## POSTING TIPS

- Post tweets 1 minute apart (use a thread scheduler like Typefully or Hootsuite)
- Include a code screenshot for tweets 3 and 4 (makes them more shareable)
- Retweet the first tweet from the thread after posting all 8
- Reply to the first tweet with: "TLDR: pip install mim-ai" for people who skip the thread
- @mention @MistralAI and Morocco tech accounts if they exist on X
