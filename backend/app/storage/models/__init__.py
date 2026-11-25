"""ORM-модели приложения."""

from app.storage.models.base import Base
from app.storage.models.operation import Operation

__all__ = ["Base", "Operation"]
