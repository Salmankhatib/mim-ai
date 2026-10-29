from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from examples.moroccan_app_example.app import auth


def test_example_auth_fails_closed_when_token_is_not_configured(monkeypatch):
    monkeypatch.delenv("MIM_APP_TOKEN", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        auth.require_api_key(None)

    assert exc_info.value.status_code == 503


def test_example_auth_fails_closed_for_blank_token(monkeypatch):
    monkeypatch.setenv("MIM_APP_TOKEN", "   ")

    with pytest.raises(HTTPException) as exc_info:
        auth.require_api_key(None)

    assert exc_info.value.status_code == 503


def test_example_auth_uses_constant_time_token_comparison(monkeypatch):
    monkeypatch.setenv("MIM_APP_TOKEN", "test-token")
    calls = []
    compare_digest = auth.hmac.compare_digest

    def compare_digest_spy(candidate, expected):
        calls.append((candidate, expected))
        return compare_digest(candidate, expected)

    monkeypatch.setattr(auth.hmac, "compare_digest", compare_digest_spy)
    credentials = SimpleNamespace(credentials="test-token")

    assert auth.require_api_key(credentials) == "test-token"
    assert calls == [("test-token", "test-token")]


def test_example_service_does_not_change_process_working_directory():
    from pathlib import Path

    from examples.moroccan_app_example.app.services import MimService

    current_directory = Path.cwd()
    config_path = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "moroccan_app_example"
        / "mim_config.yaml"
    )

    service = MimService(config_path)

    assert Path.cwd() == current_directory
    assert Path(service.mim.config.audit.db_path).parent == config_path.parent / "audit"
