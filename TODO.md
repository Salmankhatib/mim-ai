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

C3. Normalizer Layer 3 crashes when opted in
README: "Layer 3 — LLM Refinement: Optional, off by default (opt-in for polishing leftovers)."
mim_ai/normalizer/layers/llm.py::LLMLayer.apply is raise NotImplementedError. Setting normalizer.llm.enabled: true makes normalize() crash. The trigger modes (on_oov, on_mixed) are dead config — the orchestrator runs all layers unconditionally, then the trigger check does nothing (pass). Worse, Normalizer.normalize() ends with:
Python
text = context.get("layer2_output", text)
which would discard the LLM layer's output and revert to Layer 2 output even if the layer were implemented. The whole Layer-3 path is broken three separate ways.
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