🔴 Critical — Breaks Advertised Behavior

C1. mim.voice / mim.listen_and_reply() → ImportError
mim_ai/voice/__init__.py is 0 bytes (git empty-blob SHA), yet Mim.voice does:
Python
from .voice import VoicePipeline
VoicePipeline lives in mim_ai/voice/pipeline.py and is never re-exported, so this import always fails. README advertises: "🎙️ Voice — STT, TTS, and a full listen-and-reply pipeline" and the quick start shows mim.listen_and_reply(...). It cannot run.

C2. Even if C1 is fixed, the voice pipeline is a stub
voice/audio.py::record_until_silence() is a documented placeholder that always returns None → listen_and_reply() silently returns an empty VoiceReply with no error. Mic capture and playback (play()) do nothing.
voice/voice_agent.py is an empty file (dead).
voice/pipeline.py references r.intent / r.intent_score on ChatReply, which does not have those fields → guaranteed AttributeError on any successful chat turn inside the voice path.
VAD config (vad.enabled, threshold, min_silence_ms) is accepted but never consumed anywhere.
TODO.md item #3 confirms this is known unfinished work — but the README presents voice as a shipped feature.

C4. Fresh-install quick-start breaks (relative paths in shipped default config)
default_config.yaml (copied into every user's project by mim-init / load_config) points at:
yaml
rules:
  arabizi_dict_path: ./darija/arabizi.yaml      # ← FileNotFoundError outside the repo
intents:
  intents_path: ./intents.yaml                   # ← FileNotFoundError (file doesn't exist anywhere in the repo)
ArabiziDictionary.from_config calls load_yaml() which raises on a missing override path → first mim.normalizer access crashes for every pip-installed user who didn't manually create ./darija/arabizi.yaml. Similarly mim.intents → r.load_yaml("./intents.yaml") → FileNotFoundError (the repo only ships mim_ai/intents/example_intents.yaml). The README's "Local-safe flow works without external services" is only true if you run from the repo root with the repo's darija/ folder present.
C5. TTS default path is broken against the default provider
_http.py::speak() sends no response_format → OpenAI's tts-1 returns MP3 by default.
TTSConfig.format = "wav" is never sent to the API; it's only used to pick the decoder.
_decode_audio with fmt="wav" calls wave.open() on MP3 bytes → wave.Error (not even wrapped as TTSError).
Additionally, speak() has a double-request bug: _json_request returns a dict ({"raw": ...} on non-JSON), so isinstance(result, (bytes, bytearray)) is never true and the HTTP POST fires twice for every TTS call.



M1. Chatbot never uses intents
README: "🤖 Chatbot — Wraps any LLM with tools, sessions, and intent classification." ChatbotConfig.use_intents exists, IntentRegistry exists with solid Jaccard matching, and VoicePipeline accepts intents= — but nothing in Chatbot.chat() ever calls match_rule_based(), and IntentRegistry.as_llm_tool() is never added to the tool schemas sent to the LLM. Intent classification is advertised but unwired.

M2. Anonymizer builds Presidio engines on every call
anonymize() constructs a fresh AnalyzerEngine() + AnonymizerEngine() per invocation. AnalyzerEngine() init is expensive (NLP engine/registry construction). For a production SDK this is a serious throughput flaw — engines must be built once and cached (the config is hashable; memoize on it). Also: language="en" is hardcoded, so entity NER is weak on exactly the French/Darija text this toolkit targets (pattern recognizers still work). Finally, Presidio's default analyzer requires a spaCy model (en_core_web_*) that is not declared in pyproject.toml dependencies — a fresh pip install mim-ai followed by the README's anonymizer.anonymize(...) will likely raise until the user manually downloads a model. This needs a live-install check.

M3. Config loading crashes on unknown keys
MimConfig.from_dict does AuditConfig(**audit_cfg), NormalizerLogConfig(**logs_cfg), IntentConfig(**intents_cfg) — any typo or extra key in the user's YAML → TypeError with a cryptic message. ChatbotConfig filters unknown keys; the audit/intents configs should do the same.

M4. Dead config options and dead files
rules.arabic_rules_path — parsed, never loaded anywhere. Custom Arabic rule tables are impossible.
data/arabizi_darija.yaml (172 bytes, shipped as package data) — never referenced by any loader.
data/arabic_rules.yaml — also never loaded.
llm.base_url in config → MimConfig.from_dict only applies it if not cfg.chatbot.llm_endpoint — but ChatbotConfig.llm_endpoint defaults to a truthy URL, so llm.base_url is dead config.
Root darija/ duplicates normalizer/data/ concepts; the two skip_words files can drift.
tests/test_router.py — 0 bytes, orphaned (TODO item 5 says the router was dropped; the file wasn't).
_candidate_paths mentions mimExemple.yaml — leftover from an old name.

M5. Normalizer ignores its own enabled flag
Normalizer.from_config() builds layers regardless of config.enabled, and normalize() never checks it. The flag only works as a gate inside Mim.normalizer. Anyone constructing Normalizer(NormalizerConfig(enabled=False)) directly gets a silently-active normalizer — contradicting the "every subsystem is optional" claim at the class level.

M6. Audit hash chain breaks in normal operation
_last_hash is in-memory only. After a process restart, the first new row gets prev_hash=None while old rows remain → verify_chain() reports tampering. Same after retention purge (which runs at every startup by default, purge_on_start=True) and after delete_by_user() (documented, but purge isn't). The ISO 42001 tamper-evidence claim doesn't survive a restart. Fix: persist the last hash (e.g., a meta table) or anchor the chain per-boot with a signed checkpoint.

M7. Silent failure swallowing in Chatbot.from_config
Auto-wiring wraps AuditLogger/NormalizerLogger construction in bare except Exception: pass. For a compliance-oriented product, audit silently not initializing must never be silent — log a warning at minimum.



M6 hash chain: _restore_last_hash() reads the last row's hash at startup — restarts no longer break verification. Caveat: only works for sqlite/generic fallback; the rotating jsonl backend still can't restore (chain resets at midnight rotation and after purge). Fine for v0.1 if documented.

Residuals (minor, didn't claim otherwise)
spaCy model still not declared — presidio-analyzer is a hard dependency but its default analyzer needs an en_core_web_* model that isn't in pyproject.toml. Fresh pip install mim-ai → anonymize(...) likely raises until a manual model download. This is your biggest remaining quick-start risk — make the anonymizer a mim-ai[anonymizer] extra or document the download step prominently.
__pycache__ still committed (both dirs) — git rm -r + gitignore.
arabic_rules_path config option is still parsed but never loaded by any layer; worse, the shipped default points at ./mim_ai/... (CWD-relative, usually nonexistent → silently skipped). Either wire it into RulesLayer or delete the option.
data/arabizi_darija.yaml still dead package data.
STT language still sent as X-Language header — OpenAI-compatible APIs expect a form field, so the ar hint is ignored in practice.
LLM errors still produce non-empty text → audit status="ok" and the error string lands in session history.
README nit: result.entities should be result.entities_found.
langdetect/pydantic still appear unused in the codebase.
None of these contradict the README the way the old ones did.

////////////////////

# MIM-AI Codebase Audit — Final Report

**Scope:** Full static audit of `Salmankhatib/mim-ai` @ `main` (sha `292e68e`) — README, all 5 subsystems (normalizer, anonymizer, chatbot, voice, audit), config layer, packaging, tests, and docs. I could not execute the code (no sandbox network), so this is a read-through audit cross-checked against your own test suite — which turned out to be a useful consistency check.

---

## 1. Architecture Assessment

The architecture is genuinely good — better than most v0.1.0 solo SDKs:

| Decision | Verdict |
|---|---|
| Lazy subsystem loading via `Mim` facade + module-level `__getattr__` | ✅ Clean, tested (`test_optional_subsystems_stay_lazy_loaded`) |
| Layered normalizer (cheap-first, swappable layers, lossless token reassembly) | ✅ The strongest part of the codebase |
| Pluggable audit backends behind a 2-method adapter contract | ✅ SQLite/JSONL/Postgres/MySQL/Mongo + custom adapter — well done |
| Hash-chained audit log + rights of access/erasure helpers | ✅ Right conceptual model for Law 09-08 |
| stdlib-urllib OpenAI-compatible LLM/STT/TTS client (no SDK lock-in) | ✅ Pragmatic; MNTRA preset shows the sovereign-AI intent is real |
| Config-first dataclasses with unknown-key filtering | ✅ Fixed since TODO; robust now |

Module boundaries are respected, docstrings are exceptional, and your test file for the normalizer (`test_normalizer.py`) is a model of "regression guards for text-mangling" thinking — idempotency, French/English pass-through, code-switching, length-never-grows.

---

## 2. Critical Findings (claim ≠ reality)

### 🔴 C1. README quick-start example #1 does not produce the advertised output
README: `normalize("salam wa7ed 3la ekher")` → `سلام واحد على الآخر`.
Reality: `normalizer/data/skip_words.yaml` lists `"salam"`, `"labas"`, `"bghit"`, `"wa7ed"`, `"wahed"`, `"kho"` — the skip check runs **before** the dictionary lookup in `_normalize_token`, so these tokens pass through untouched. Worse, "3la" and "ekher" aren't in the dictionary at all (10 entries total). Your own updated test quietly asserts `"salam" in normalized` — the test was bent to fit the bug, not the other way around. **The flagship demo in the README fails as printed.** Fix: remove Darija words from skip_words (only `merci/bonjour/hello/thanks` belong there), grow the dictionary to cover the example.

### 🔴 C2. README anonymizer example output format is wrong
Default operators are `CIN_MA: replace` → `[CIN_MA]` (brackets, from `_operator_for` fallback) and `PHONE_MA: mask` → `****345678`. README shows `<CIN_MA>` and `<PHONE_MA>`. Detection works (entities_found is populated pre-operator), but the printed output is fiction. Either change defaults to `replace` with `new_value: <ENTITY>` angle-bracket style or fix the README.

### 🔴 C3. `verify_chain()` — the ISO 42001 tamper-evidence verifier — is broken by construction
`AuditLogger.emit()` computes `line_hash` over the row dict **which does not contain `seq`** (SQLite assigns it at insert). `verify_chain()` recomputes over `SELECT *` **which does contain `seq`**. The canonical JSON payloads differ → `verify_chain()` returns `(False, "seq=1 line_hash mismatch")` on a fresh, untouched database. Notably, **no test calls `verify_chain`** — `test_audit_hash_chain_persists_across_restarts` only checks `prev_hash` linkage, which is why this slipped through. This is your most dangerous flaw because compliance tooling that always cries "tampering" is worse than none. Fix: exclude `seq` in `verify_chain`, or include it in `emit`.

### 🔴 C4. Voice "recording" is still a stub — and it's silent about it
`record_until_silence()` records a **fixed** window of `silence_timeout_ms` (1.5 s) via `sd.rec`, with no VAD and no silence detection. `VADConfig.threshold` / `min_silence_ms` are accepted, plumbed, and **never consumed**. Without sounddevice it returns a buffer of **zeros** which is then sent to the paid STT endpoint. `play()` swallows all exceptions. The README sells "records → transcribes → chats → speaks"; the actual UX captures 1.5 s of ambient audio and truncates mid-sentence. TODO.md still flags this as critical — the README should mark voice as preview/beta, or ship a real energy-threshold VAD (it's ~40 lines with the existing numpy dependency).

### 🟠 C5. TTS double-request billing bug
`_http.speak()` fires a second **identical POST** whenever the first response is JSON-shaped (any dict without a `raw` bytes field) — doubling TTS cost for that class of provider responses. The fallback re-request logic should only run when the first response definitively wasn't audio.

### 🟠 C6. Fresh-install anonymizer likely crashes
`AnalyzerEngine()` (Presidio default) requires a spaCy model (`en_core_web_*`) that is **not** in `pyproject.toml` and not documented in the README. `pip install mim-ai && anonymize(...)` → `OSError` until a manual model download. Your own TODO flags this as the biggest quick-start risk. Also: `language="en"` is hardcoded in `analyzer.analyze()`, so NER is weak on exactly the French/Darija text you target (your pattern recognizers still work, so CIN/phone pass). Consider a regex-only fallback mode or a `[anonymizer]` extra with documented `python -m spacy download`.

---

## 3. Moderate / Structural Issues

- **Dependency weight vs "zero bloat" claim:** `presidio-analyzer` drags in **spaCy** (~heavy, model download), while `langdetect` and `pydantic` appear unused in the codebase. The README's "no torch, no sounddevice" is technically true but spacy is the same class of heaviness. Trim or justify.
- **Erasure vs tamper-evidence contradiction:** `delete_by_user()` and startup retention purge delete mid-chain rows → `verify_chain()` can never pass afterward. You log a `deletion` event (good instinct) but the chain still reads as tampered. For a Law 09-08 product this needs a designed answer: per-day chains, signed checkpoints, or a `tombstone` row type that closes a chain segment.
- **Intent "hybrid/llm" strategy is decorative:** `IntentConfig.strategy` documents `rule | llm | hybrid`, but the chatbot only ever calls `match_rule_based`; `IntentRegistry.as_llm_tool()` is never wired into tool schemas; `Intent.tool` is never executed. Either implement or downgrade the docstring to what's real (rule-only).
- **Dead config surface:** `arabic_rules_path` (parsed, never loaded), `strip_mentions`/`strip_hashtags` (parsed, cleaning layer ignores them), `arabizi_darija.yaml` (dead package data), root `darija/*.yaml` duplicates `normalizer/data/` and will drift, `mimExemple.yaml` naming leftover, `Mim._logs` never used. A senior reviewer will clock these.
- **Repo hygiene:** committed `__pycache__/*.pyc` (both `mim_ai/` and `tests/`), stale TODO.md entries (C1/C2/C4/C5 listed as unfixed when the code shows they're partially fixed — the file now contradicts reality in both directions).
- **No CI visible** in the tree (no `.github/workflows`). For a compliance-adjacent tool, CI running `pytest` + a `verify_chain` round-trip is essential.
- Minor: voice pipeline's intent match ignores `config.intents.threshold`; `Normalizer.normalize()` double-reads `layer2_output` redundantly; double normalization in voice→chatbot path (harmless, idempotent, but costs a pass).

---

## 4. What's genuinely strong (worth protecting)

- Normalizer layer design + safety test suite — best-in-repo.
- Audit schema, multi-backend factory, retention, erasure, restart-persistent chain head (`_restore_last_hash`) — the *thinking* here is senior-level; it's the verify implementation that betrayed it.
- Chatbot: correct tool-call loop, OpenAI-spec-compliant assistant message shape, history caps + TTL, normalized-text history (privacy-correct), audit status on error.
- Positioning/docs: bilingual docs, manifesto, architecture doc, press kit — unusually complete go-to-market for a dev tool.

---


## 6. Priority fix list
2. [x] Purge Darija words from `skip_words.yaml`; expand dictionary to cover README example; make README/test/output agree.
3. README anonymizer output format ↔ default operators. *1 hour.*
5. [x] Voice: add real energy-VAD and document plug-and-play setup.

6. [x] `_http.speak` double-POST guard.