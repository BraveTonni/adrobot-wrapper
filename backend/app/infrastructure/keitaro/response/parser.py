"""Разбор обёрток ответов Admin API Keitaro."""

from typing import Any

from app.infrastructure.keitaro.errors import KeitaroError


def parse_list(data: Any) -> list[dict[str, Any]]:
    """Извлекает список объектов из поддерживаемых форматов ответа."""
    if isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            return data
        raise KeitaroError("Keitaro вернул список с некорректными элементами")

    if isinstance(data, dict):
        for key in ("data", "items", "results"):
            items = data.get(key)
            if isinstance(items, list):
                return parse_list(items)

    raise KeitaroError("Keitaro вернул ответ неожиданного формата для списка")


def parse_one(data: Any, entity: str) -> dict[str, Any]:
    """Извлекает один объект и проверяет наличие его ID."""
    if isinstance(data, list) and data:
        data = data[0]

    if not isinstance(data, dict) or data.get("id") is None:
        raise KeitaroError(f"Keitaro не вернул ID {entity}")

    return data
