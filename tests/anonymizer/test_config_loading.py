import yaml

from mim_ai.anonymizer.config import AnonymizerConfig, load_config


def test_yaml_and_dict_config_loading(tmp_path):
    config_path = tmp_path / "anon.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "enabled": True,
                "default_operators": {"DEFAULT": "replace", "CIN_MA": "replace"},
                "custom_patterns": [{"name": "ORDER_ID", "pattern": "ORDER-[0-9]{6}", "operator": "replace"}],
            }
        ),
        encoding="utf-8",
    )

    loaded_from_file = load_config(str(config_path))
    assert isinstance(loaded_from_file, AnonymizerConfig)
    assert loaded_from_file.enabled is True
    assert loaded_from_file.language == "en"
    assert loaded_from_file.default_operators["CIN_MA"] == "replace"

    loaded_from_dict = load_config({"enabled": False, "custom_patterns": [{"name": "X", "pattern": "abc"}]})
    assert loaded_from_dict.enabled is False
    assert loaded_from_dict.custom_patterns[0]["name"] == "X"


def test_unsupported_anonymizer_language_fails_explicitly():
    import pytest

    with pytest.raises(ValueError, match="only language='en'"):
        AnonymizerConfig.from_mapping({"language": "fr"})


def test_full_application_yaml_loads_nested_anonymizer_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({
            "anonymizer": {
                "enabled": False,
                "default_operators": {"DEFAULT": "redact"},
                "custom_patterns": [{"name": "ORDER_ID", "pattern": "ORDER-[0-9]+"}],
            },
            "voice": {"enabled": True},
        }),
        encoding="utf-8",
    )

    loaded = load_config(config_path)

    assert loaded.enabled is False
    assert loaded.default_operators == {"DEFAULT": "redact"}
    assert loaded.custom_patterns[0]["name"] == "ORDER_ID"
