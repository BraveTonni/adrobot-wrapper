class NotFoundError(Exception):
    """Сущность не найдена."""


class ConflictError(Exception):
    """Действие конфликтует с текущим состоянием."""
