class KeitaroError(Exception):
    """Ошибка ответа или недоступности Admin API."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status
