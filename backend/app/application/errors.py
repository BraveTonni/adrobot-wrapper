class NotFoundError(Exception):
    """Сущность не найдена."""


class ConflictError(Exception):
    """Действие конфликтует с текущим состоянием."""


class RepositoryNotFoundError(Exception):
    """Запрошенная запись отсутствует во внешнем хранилище."""


class ExternalServiceError(Exception):
    """Внешний сервис не смог выполнить запрос."""
