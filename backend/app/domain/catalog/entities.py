"""Сущности каталога и справочных данных."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Offer:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class Reference:
    id: int
    name: str
