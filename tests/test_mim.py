from mim_ai import Mim, MimConfig


def test_mim_anonymize_uses_loaded_config():
    app = Mim(MimConfig.from_dict({"anonymizer": {"enabled": False}}))

    result = app.anonymize("AB123456")

    assert result.text == "AB123456"
    assert result.entities_found == []


def test_mim_chatbot_does_not_construct_disabled_integrations():
    config = MimConfig.from_dict(
        {
            "normalizer": {"enabled": True},
            "intents": {"enabled": True},
            "audit": {"enabled": True},
            "logs": {"enabled": True},
            "chatbot": {
                "enabled": True,
                "use_normalizer": False,
                "use_intents": False,
                "use_audit_log": False,
                "use_normalizer_log": False,
            },
        }
    )
    app = Mim(config)

    assert app.chatbot is not None

    assert app._normalizer is None
    assert app._intents is None
    assert app._audit is None
    assert app._normalizer_log is None


def test_chatbot_does_not_fallback_to_normalizer_when_globally_disabled():
    config = MimConfig.from_dict(
        {
            "normalizer": {"enabled": False},
            "chatbot": {
                "enabled": True,
                "use_normalizer": True,
                "use_intents": False,
                "use_audit_log": False,
                "use_normalizer_log": False,
            },
        }
    )
    app = Mim(config)

    assert app.chatbot is not None

    assert app._normalizer is None


def test_voice_does_not_construct_disabled_integrations():
    config = MimConfig.from_dict(
        {
            "normalizer": {"enabled": True},
            "intents": {"enabled": True},
            "audit": {"enabled": True},
            "logs": {"enabled": True},
            "voice": {
                "enabled": True,
                "use_normalizer": False,
                "use_intents": False,
                "use_audit_log": False,
                "use_chatbot": False,
            },
        }
    )
    app = Mim(config)

    assert app.voice is not None

    assert app._normalizer is None
    assert app._intents is None
    assert app._audit is None
    assert app._normalizer_log is None
    assert app._chatbot is None


def test_global_intent_threshold_is_used_unless_chatbot_overrides_it():
    defaulted = MimConfig.from_dict({"intents": {"threshold": 0.8}})
    overridden = MimConfig.from_dict(
        {
            "intents": {"threshold": 0.8},
            "chatbot": {"intent_threshold": 0.4},
        }
    )

    assert defaulted.chatbot.intent_threshold == 0.8
    assert overridden.chatbot.intent_threshold == 0.4


def test_init_cli_creates_config_and_reports_path(tmp_path, monkeypatch, capsys):
    from mim_ai.__main__ import init_main

    config_path = tmp_path / "config.yaml"
    monkeypatch.setattr("sys.argv", ["mim-init", str(config_path)])

    assert init_main() == 0
    assert config_path.is_file()
    assert f"Config ready at {config_path}" in capsys.readouterr().out
