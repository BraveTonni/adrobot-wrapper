"""Результаты запросов каталога."""

from dataclasses import dataclass

from app.domain.catalog.entities import Reference


@dataclass(frozen=True, slots=True)
class References:
    domains: list[Reference]
    groups: list[Reference]
    sources: list[Reference]
