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
