import os
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StreamFilterSettings(BaseModel):
    name: str
    mode: str
    payload: Any = None


class CampaignStreamSettings(BaseModel):
    name: str
    type: Literal["regular", "forced", "default"]
    schema_: Literal["redirect", "landings", "action"] = Field(alias="schema")
    position: int = Field(gt=0)
    action_type: str = "http"
    action_payload: str | None = None
    filters: list[StreamFilterSettings] = Field(default_factory=list)
    initial_offer: bool = False


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
    campaign_streams: list[CampaignStreamSettings] = Field(
        default_factory=lambda: [
            CampaignStreamSettings(
                name="Geo {geo}",
                type="regular",
                schema="redirect",
                position=1,
                action_payload="{geo_redirect_url}",
                filters=[
                    StreamFilterSettings(
                        name="country", mode="accept", payload=["{geo}"]
                    )
                ],
            ),
            CampaignStreamSettings(
                name="Offers",
                type="default",
                schema="landings",
                position=2,
                initial_offer=True,
            ),
        ]
    )

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
