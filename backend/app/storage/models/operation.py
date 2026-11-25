from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.models.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Operation(Base):
    """Запись журнала операций."""

    __tablename__ = "operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        default=utcnow, server_default=func.now()
    )
    action: Mapped[str] = mapped_column(String(50))
    campaign_id: Mapped[int | None]
    stream_id: Mapped[int | None]
    status: Mapped[str] = mapped_column(String(20))
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON)
