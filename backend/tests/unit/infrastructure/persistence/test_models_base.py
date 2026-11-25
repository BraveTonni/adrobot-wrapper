from sqlalchemy.orm import DeclarativeBase

from app.infrastructure.persistence.models.base import Base


def test_storage_base_is_declarative_base() -> None:
    assert issubclass(Base, DeclarativeBase)
