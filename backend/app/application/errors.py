class NotFoundError(Exception):
    """Сущность не найдена."""


class ConflictError(Exception):
    """Действие конфликтует с текущим состоянием."""


class ValidationError(Exception):
    """Входные данные не прошли прикладную валидацию."""


class RepositoryNotFoundError(Exception):
    """Запрошенная запись отсутствует во внешнем хранилище."""


class ExternalServiceError(Exception):
    """Внешний сервис не смог выполнить запрос."""
