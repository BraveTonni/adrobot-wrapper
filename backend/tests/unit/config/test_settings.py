from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_load_environment_and_defaults(monkeypatch) -> None:
    monkeypatch.setenv("KEITARO_API_KEY", "secret")
    monkeypatch.setenv("KEITARO_TIMEOUT", "3.5")
    monkeypatch.setenv("DEFAULT_DOMAIN_ID", "77")

    settings = Settings(_env_file=None)

    assert settings.keitaro_api_key == "secret"
    assert settings.keitaro_timeout == 3.5
    assert settings.default_domain_id == 77
    assert settings.database_url == "sqlite+aiosqlite:///./adrobot.db"


def test_settings_ignore_unknown_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("UNUSED_SETTING", "ignored")

    assert Settings(_env_file=None).log_level == "INFO"


def test_campaign_streams_can_be_configured() -> None:
    settings = Settings(
        _env_file=None,
        campaign_streams=[
            {
                "name": "Geo {geo}",
                "type": "regular",
                "schema": "redirect",
                "position": 1,
            },
            {
                "name": "Landings",
                "type": "default",
                "schema": "landings",
                "position": 2,
                "initial_offer": True,
            },
        ],
    )

    assert [stream.schema_ for stream in settings.campaign_streams] == [
        "redirect",
        "landings",
    ]


def test_settings_read_api_key_from_secrets_directory(tmp_path: Path) -> None:
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "keitaro_api_key").write_text("file-secret\n")

    settings = Settings(_env_file=None, _secrets_dir=secrets_dir)

    assert settings.keitaro_api_key == "file-secret"


@pytest.mark.parametrize(
    "url",
    [
        "http://keitaro.example/admin_api/v1",
        "https://user:password@keitaro.example/admin_api/v1",
        "https://keitaro.example/admin_api/v1?token=secret",
        "not a URL",
    ],
)
def test_settings_reject_insecure_keitaro_urls(url: str) -> None:
    with pytest.raises(ValidationError, match="Keitaro URLs must use HTTPS"):
        Settings(_env_file=None, keitaro_url=url)
