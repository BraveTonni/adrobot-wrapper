from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Operation(Base):
    """Запись audit log."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Время всегда приходит с таймзоной: PostgreSQL принимает его только в
    # колонку WITH TIME ZONE.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    action: Mapped[str] = mapped_column(String(50))
    actor: Mapped[str] = mapped_column(String(150), default="unknown")
    entity_type: Mapped[str] = mapped_column(String(40), default="operation")
    entity_id: Mapped[int | None]
    campaign_id: Mapped[int | None]
    stream_id: Mapped[int | None]
    status: Mapped[str] = mapped_column(String(20))
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    before_payload: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON
    )
    after_payload: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON
    )
    error: Mapped[str | None] = mapped_column(Text)
