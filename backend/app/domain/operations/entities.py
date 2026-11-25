"""Сущности истории операций."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class AuditRecord:
    id: int
    created_at: datetime
    action: str
    campaign_id: int | None
    stream_id: int | None
    status: str
    detail: dict[str, Any] | None
    actor: str = "unknown"
    entity_type: str = "operation"
    entity_id: int | None = None
    before_payload: dict[str, Any] | list[Any] | None = None
    after_payload: dict[str, Any] | list[Any] | None = None
    error: str | None = None
