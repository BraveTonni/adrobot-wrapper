import os
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Переменные окружения (.env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        secrets_dir=os.getenv("PYDANTIC_SECRETS_DIR") or None,
    )

    # Keitaro Admin API
    keitaro_url: str = "https://keitaro-for-tests.etolegko.com/admin_api/v1"
    keitaro_api_key: str = ""
    keitaro_admin_url: str = "https://keitaro-for-tests.etolegko.com/admin"
    keitaro_timeout: float = 15.0

    # Local API access: read from API_ACCESS_TOKEN or a secret file.
    api_access_token: str = ""
    cors_allowed_origins: list[str] = []

    # Значения по умолчанию для новых кампаний
    default_domain_id: int = 1813
    default_group_id: int = 10332
    default_source_id: int = 836
    geo_redirect_url: str = "https://google.com"

    # База данных
    database_url: str = "sqlite+aiosqlite:///./adrobot.db"

    # Кэш справочников, секунды
    offers_cache_ttl: float = 300
    reference_cache_ttl: float = 300

    campaign_search_limit: int = 500
    log_level: str = "INFO"
    log_directory: Path = Path("../logs")

    @field_validator("keitaro_url", "keitaro_admin_url")
    @classmethod
    def require_secure_keitaro_urls(cls, value: str) -> str:
        try:
            parsed = urlsplit(value)
            valid = (
                parsed.scheme == "https"
                and parsed.hostname is not None
                and parsed.username is None
                and parsed.password is None
                and not parsed.query
                and not parsed.fragment
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError(
                "Keitaro URLs must use HTTPS and must not contain "
                "credentials, query parameters, or fragments"
            )
        return value


settings = Settings()
