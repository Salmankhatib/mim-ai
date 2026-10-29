import pytest

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


def test_mim_from_config_injects_per_app_tool_registry():
    from mim_ai.chatbot import ToolRegistry

    tools = ToolRegistry()
    app = Mim(
        MimConfig.from_dict({
            "chatbot": {
                "enabled": True,
                "use_normalizer": False,
                "use_intents": False,
                "use_audit_log": False,
                "use_normalizer_log": False,
            }
        }),
        tool_registry=tools,
    )

    assert app.chatbot.registry is tools


def test_mim_loads_intent_scoped_tools_from_config(tmp_path):
    from mim_ai.chatbot import ToolRegistry
    from mim_ai.chatbot.tools import ToolSpec

    intents_path = tmp_path / "intents.yaml"
    intents_path.write_text(
        "intents:\n"
        "  - name: check_order\n"
        "    description: Read order information.\n"
        "    examples: [check order]\n"
        "    tools: [lookup_order]\n",
        encoding="utf-8",
    )
    tools = ToolRegistry()
    app = Mim(
        MimConfig.from_dict({
            "chatbot": {
                "enabled": True,
                "enable_tools": True,
                "use_intents": True,
                "use_normalizer": False,
                "use_audit_log": False,
                "use_normalizer_log": False,
            },
            "intents": {
                "enabled": True,
                "strategy": "rule",
                "intents_path": str(intents_path),
            },
        }),
        tool_registry=tools,
    )

    with pytest.raises(ValueError, match="unregistered tools"):
        _ = app.chatbot

    tools.register(ToolSpec(
        name="lookup_order",
        description="Read order information.",
        params={},
        fn=lambda: "found",
        required=[],
    ))

    assert app.chatbot.intents.all()[0].tool_names == ["lookup_order"]


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


def test_legacy_llm_base_url_is_used_unless_chatbot_endpoint_overrides_it():
    legacy = MimConfig.from_dict({"llm": {"base_url": "https://legacy.example/v1"}})
    preferred = MimConfig.from_dict({
        "llm": {"base_url": "https://legacy.example/v1"},
        "chatbot": {"llm_endpoint": "https://chatbot.example/v1"},
    })

    assert legacy.chatbot.llm_endpoint == "https://legacy.example/v1"
    assert preferred.chatbot.llm_endpoint == "https://chatbot.example/v1"


def test_init_cli_creates_config_and_reports_path(tmp_path, monkeypatch, capsys):
    from mim_ai.__main__ import init_main

    config_path = tmp_path / "config.yaml"
    monkeypatch.setattr("sys.argv", ["mim-init", str(config_path)])

    assert init_main() == 0
    assert config_path.is_file()
    assert f"Config ready at {config_path}" in capsys.readouterr().out


def test_init_cli_defaults_to_canonical_mim_config_name(tmp_path, monkeypatch, capsys):
    from mim_ai.__main__ import init_main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["mim-init"])

    assert init_main() == 0
    assert (tmp_path / "mim_config.yaml").is_file()
    assert "Config ready at mim_config.yaml" in capsys.readouterr().out


def test_generated_default_config_runs_normalizer_outside_repository(
    tmp_path, monkeypatch
):
    from mim_ai.config import write_default_config

    monkeypatch.chdir(tmp_path)
    write_default_config()
    app = Mim.from_config()

    normalized = app.normalizer.normalize("salam wa7ed 3la ekher")

    assert normalized == "salam wa7ed 3la ekher"
    assert (tmp_path / "mim_config.yaml").is_file()
    app.shutdown()


def test_mim_shutdown_does_not_keep_an_unused_logs_attribute():
    app = Mim(MimConfig.from_dict({}))

    assert not hasattr(app, "_logs")
    app.shutdown()
