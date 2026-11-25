"""Чтение истории операций через порт репозитория."""

from app.application.ports import AuditRepository
from app.domain.operations.entities import AuditRecord


class OperationHistory:
    def __init__(self, repository: AuditRepository) -> None:
        self._repository = repository

    async def recent(self, limit: int = 50) -> list[AuditRecord]:
        return await self._repository.recent(limit)
