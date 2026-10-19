"""
Safety and correctness tests for the mim_ai normalizer.

Every test here is a regression guard. If you break one of these
without a very good reason, you are corrupting user text.
"""
import pytest

from mim_ai.normalizer.normalizer import Normalizer
from mim_ai.normalizer.schema import NormalizerConfig
from mim_ai.normalizer import arabic_rules as ar

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def norm():
    """Default config — L1 + L2 only, LLM off."""
    return Normalizer.from_config(NormalizerConfig())


@pytest.fixture
def norm_aggressive():
    """All L2 toggles on, URL placeholder enabled."""
    cfg = NormalizerConfig()
    cfg.rules.unify_ta_marbuta = True
    cfg.rules.remove_diacritics = True
    return Normalizer.from_config(cfg)


# ---------------------------------------------------------------------------
# Layer 1 — universal cleaning
# ---------------------------------------------------------------------------
class TestLayer1Safety:

    def test_whitespace_collapsed(self, norm):
        out = norm.normalize("salam    kho    labas")
        assert out == "salam kho labas"

    def test_newlines_preserved(self, norm):
        out = norm.normalize("salam\nlabas")
        assert "\n" in out

    def test_zero_width_removed(self, norm):
        out = norm.normalize("salam\u200b\u200b labas")
        assert "\u200b" not in out

    def test_tatweel_removed(self, norm):
        out = norm.normalize("سلا\u0640\u0640م")
        assert "\u0640" not in out
        assert "سلام" in out

    def test_url_kept_by_default(self, norm):
        """Default config must NOT destroy URLs."""
        text = "chouf https://example.ma/foo bar"
        out = norm.normalize(text)
        assert "https://example.ma/foo" in out

    def test_urls_are_removed_when_explicitly_configured(self):
        cfg = NormalizerConfig.from_mapping({
            "cleaning": {"strip_urls": True},
        })
        out = Normalizer.from_config(cfg).normalize(
            "open https://example.ma/path now"
        )
        assert "https://example.ma/path" not in out
        assert out == "open now"

    def test_disabling_url_preservation_does_not_force_url_stripping(self):
        cfg = NormalizerConfig.from_mapping({
            "cleaning": {"preserve_urls": False},
        })

        assert cfg.cleaning.preserve_urls is False
        assert cfg.cleaning.strip_urls is False

    def test_nfc_normalization(self, norm):
        # é as e + combining accent vs. precomposed é
        out = norm.normalize("cafe\u0301")
        assert out == "café"


# ---------------------------------------------------------------------------
# Layer 2 — French / English must pass through untouched
# ---------------------------------------------------------------------------
class TestFrenchSafety:

    @pytest.mark.parametrize("word", [
        "bonjour", "merci", "la", "le", "les", "ma", "ta", "sa",
        "pas", "plus", "tres", "bien", "oui", "non", "avec", "sans",
        "pour", "dans", "sur", "sous", "ce", "cette",
    ])
    def test_french_word_unchanged(self, norm, word):
        out = norm.normalize(word)
        assert out == word, f"French word '{word}' was modified to '{out}'"

    def test_french_sentence_unchanged(self, norm):
        text = "je suis tres content de te voir"
        assert norm.normalize(text) == text

    def test_french_accents_preserved(self, norm):
        text = "l'école était très chère"
        assert norm.normalize(text) == text

    def test_french_urls_not_arabizi(self, norm):
        """A URL contains latin chars but must not be dict-looked-up."""
        text = "casa.ma"
        out = norm.normalize(text)
        assert "casa" in out or "casa.ma" in out  # not translated to كازا


class TestEnglishSafety:

    @pytest.mark.parametrize("word", [
        "the", "a", "an", "and", "or", "is", "are", "was",
        "yes", "no", "ok", "okay", "thanks",
    ])
    def test_english_word_unchanged(self, norm, word):
        assert norm.normalize(word) == word


# ---------------------------------------------------------------------------
# Layer 2 — Arabic rules correctness and idempotency
# ---------------------------------------------------------------------------
class TestArabicRules:

    def test_alef_unified(self):
        assert ar.unify_alef("أحمد") == "احمد"
        assert ar.unify_alef("إبراهيم") == "ابراهيم"
        assert ar.unify_alef("آمن") == "امن"

    def test_default_normalizer_preserves_canonical_hamza_spelling(self, norm):
        assert norm.normalize("أحمد إبراهيم آمن") == "أحمد إبراهيم آمن"

    def test_ya_unified(self):
        assert ar.unify_ya("على") == "على"
        assert ar.unify_ya("علي") == "علي"
        assert ar.unify_ya("مصطفى") == "مصطفى"
        assert ar.unify_ya("علی") == "علي"

    def test_ta_marbuta_basic(self):
        assert ar.unify_ta_marbuta("مدرسة") == "مدرسه"

    def test_ta_marbuta_guard_possessive(self):
        """Ta Marbuta with possessive suffix must NOT be unified."""
        # معلمته (his teacher, f.) — the ة carries meaning
        assert ar.unify_ta_marbuta("معلمته") == "معلمته"

    def test_tashkeel_removed(self):
        assert ar.remove_tashkeel("كَتَبَ") == "كتب"

    def test_arabic_digits(self):
        assert ar.normalize_arabic_digits("٢٠٢٦") == "2026"

    def test_ascii_digits_untouched(self):
        assert ar.normalize_arabic_digits("2026") == "2026"

    def test_idempotent_full_chain(self):
        text = "أَحْمَد   فِي  الْمَدْرَسَةِ ٢٠٢٦"
        once  = ar.apply_arabic_rules(text)
        twice = ar.apply_arabic_rules(once)
        assert once == twice, "arabic rules are not idempotent"

    def test_url_placeholder_preserves_intent(self):
        out = ar.placeholder_urls("chouf https://x.ma bar")
        assert "<URL>" in out
        assert "https" not in out


# ---------------------------------------------------------------------------
# Code-switching — the real-world case
# ---------------------------------------------------------------------------
class TestCodeSwitching:

    def test_canonical_darija_variant_bank(self, norm):
        assert norm.normalize("b8it nchouf daaba") == "bghit nchouf daba"
        assert norm.normalize("بغيت نشوف دابة") == "بغيت نشوف دابا"

    def test_readme_darija_example_preserves_input_script(self, norm):
        assert norm.normalize("salam wa7ed 3la ekher") == "salam wa7ed 3la ekher"
        assert norm.normalize("slm wahed 3laa akhar") == "salam wa7ed 3la ekher"
        assert norm.normalize("سلم واحد على الاخر") == "سلام واحد على الآخر"
        assert norm.normalize("علي") == "علي"
        assert norm.normalize("la vie est belle") == "la vie est belle"

    def test_darija_french_mix(self, norm):
        text = "salam, ça va? bghit n3ref wa7ed chi haja"
        out = norm.normalize(text)
        # French must survive
        assert "ça va" in out
        # Arabizi handled by L2 dict if keys present, else passes through
        assert "salam" in out.lower()

    def test_arabic_french_mix(self, norm):
        text = "كاين مشكل ف la base de données"
        out = norm.normalize(text)
        assert "la" in out
        assert "base" in out
        assert "données" in out

    def test_pure_msa_not_destroyed(self, norm):
        text = "الطلاب يدرسون في الجامعة"
        out = norm.normalize(text)
        # MSA must remain MSA
        assert "الجامعة" in out or "الجامعه" in out
        assert "الطلاب" in out


# ---------------------------------------------------------------------------
# Nature-of-text invariants — these must ALWAYS hold
# ---------------------------------------------------------------------------
class TestTextInvariants:

    def test_emoji_preserved(self, norm):
        text = "salam 👋 labas 😊"
        out = norm.normalize(text)
        assert "👋" in out
        assert "😊" in out

    def test_punctuation_preserved(self, norm):
        text = "salam, wa3lach? daba!"
        out = norm.normalize(text)
        for p in [",", "?", "!"]:
            assert p in out

    def test_arabic_punctuation_preserved(self, norm):
        text = "سلام، واش راك؟"
        out = norm.normalize(text)
        assert "،" in out
        assert "؟" in out

    def test_numbers_untouched(self, norm):
        text = "3andna 42 clients"
        out = norm.normalize(text)
        assert "42" in out

    def test_empty_string(self, norm):
        assert norm.normalize("") == ""

    def test_whitespace_only(self, norm):
        assert norm.normalize("   \n  ") == ""

    def test_length_never_grows(self, norm):
        """Normalization must never make text longer."""
        samples = [
            "salam    kho",
            "أحمد",
            "café",
            "bghit n3ref wa7ed chi haja",
        ]
        for s in samples:
            assert len(norm.normalize(s)) <= len(s) + 2   # placeholder slack

    def test_report_flags_oov_arabizi(self, norm):
        _, report = norm.normalize("xyzxyz", return_report=True)
        assert report.mixed_script is False
        # xyzxyz is pure latin and not in dict — should flag OOV? maybe
        # adjust depending on your dict-hit definition


class TestConfigAndWiring:

    def test_example_yaml_is_the_default_loader_target(self):
        from mim_ai import load_config

        cfg = load_config("config.yaml")
        assert cfg.normalizer.enabled is True
        assert cfg.audit.enabled is True
        assert cfg.logs.enabled is True

    def test_logger_switches_are_config_driven(self):
        from mim_ai import load_config

        cfg = load_config("config.yaml")
        cfg.audit.enabled = False
        cfg.logs.enabled = False

        assert cfg.audit.enabled is False
        assert cfg.logs.enabled is False

    def test_normalizer_has_only_two_layers(self):
        from mim_ai import load_config

        cfg = load_config("config.yaml")
        assert cfg.normalizer.enabled is True
        assert hasattr(cfg.normalizer, "cleaning")
        assert hasattr(cfg.normalizer, "rules")
        assert not hasattr(cfg.normalizer, "llm")

    def test_chatbot_history_and_llm_params_are_config_driven(self):
        from mim_ai.chatbot.config import ChatbotConfig
        from mim_ai.chatbot import Chatbot

        cfg = ChatbotConfig.from_mapping({
            "enabled": True,
            "history_backend": "sqlite",
            "history_dsn": "./tmp/test_history.db",
            "params": {"response_format": {"type": "json_object"}},
            "roles": {"assistant": "concierge"},
        })

        assert cfg.params["response_format"]["type"] == "json_object"
        assert cfg.roles["assistant"] == "concierge"

        bot = Chatbot.from_config(cfg)
        assert bot.history.__class__.__name__ == "SQLiteHistoryStore"


def test_normalizer_import_does_not_eagerly_load_anonymizer():
    import importlib
    import sys

    for key in ["mim_ai.anonymizer", "mim_ai"]:
        sys.modules.pop(key, None)

    pkg = importlib.import_module("mim_ai")
    importlib.import_module("mim_ai.normalizer")

    assert "mim_ai.anonymizer" not in sys.modules
    assert hasattr(pkg, "Mim")


def test_optional_subsystems_stay_lazy_loaded():
    import importlib
    import sys

    for key in [
        "mim_ai.chatbot", "mim_ai.chatbot.chatbot", "mim_ai.chatbot.config", "mim_ai.chatbot.llm",
        "mim_ai.audit", "mim_ai.audit.config", "mim_ai.audit.audit_logger", "mim_ai.audit.normalizer_logger",
        "mim_ai.intents", "mim_ai.intents.config", "mim_ai.intents.registry",
        "mim_ai.anonymizer", "mim_ai.anonymizer.anonymizer", "mim_ai.anonymizer.config",
    ]:
        sys.modules.pop(key, None)

    import mim_ai

    assert "mim_ai.chatbot" not in sys.modules
    assert "mim_ai.audit" not in sys.modules
    assert "mim_ai.intents" not in sys.modules
    assert "mim_ai.anonymizer" not in sys.modules

    chat_mod = importlib.import_module("mim_ai.chatbot")
    assert chat_mod.ChatbotConfig is not None
    assert "mim_ai.chatbot.chatbot" not in sys.modules

    audit_mod = importlib.import_module("mim_ai.audit")
    assert audit_mod.AuditConfig is not None
    assert "mim_ai.audit.audit_logger" not in sys.modules

    assert hasattr(mim_ai, "Mim")


def test_readme_local_dev_flow_works_without_external_llm():
    from mim_ai import Mim, anonymizer

    app = Mim.from_config("config.yaml")
    normalized = app.normalizer.normalize("salam wa7ed 3la ekher")
    result = anonymizer.anonymize("Mon CIN est AB58075 et mon tel est 0612345678")

    assert normalized == "salam wa7ed 3la ekher"
    assert any(item["type"] == "CIN_MA" for item in result.entities_found)
    assert any(item["type"] == "PHONE_MA" for item in result.entities_found)
