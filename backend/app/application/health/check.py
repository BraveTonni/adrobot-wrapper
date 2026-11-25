"""Проверка доступности критичных зависимостей приложения."""

from app.application.ports import HealthRepository


class HealthCheck:
    def __init__(self, repository: HealthRepository) -> None:
        self._repository = repository

    async def check(self) -> dict[str, str]:
        await self._repository.check_database()
        return {"status": "ok"}
