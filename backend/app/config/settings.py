import os

from pydantic import Field
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
    api_access_token: str = Field(default="", min_length=32)

    # Значения по умолчанию для новых кампаний
    default_domain_id: int = 1813
    default_group_id: int = 10332
    default_source_id: int = 836
    geo_redirect_url: str = "https://google.com"

    # База данных
    database_url: str = "sqlite+aiosqlite:///./adrobot.db"

    # Кэш справочников, секунды
    offers_cache_ttl: float = 3600
    reference_cache_ttl: float = 3600

    campaign_search_limit: int = 500
    log_level: str = "INFO"


settings = Settings()
