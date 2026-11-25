"""Порты - интерфейсы, которые реализует инфраструктура."""

from typing import Protocol


class AuditLog(Protocol):
    """Журнал операций обёртки."""

    async def record(
        self,
        *,
        action: str,
        status: str,
        campaign_id: int | None = None,
        stream_id: int | None = None,
        detail: dict[str, object] | None = None,
    ) -> None: ...
