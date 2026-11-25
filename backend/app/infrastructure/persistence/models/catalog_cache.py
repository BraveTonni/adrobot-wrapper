from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class CatalogCacheEntry(Base):
    __tablename__ = "catalog_cache"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    payload: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSON, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
