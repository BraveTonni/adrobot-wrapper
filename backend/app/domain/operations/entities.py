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
