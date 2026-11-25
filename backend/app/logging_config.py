"""Настройка логирования: одна запись - один JSON-объект в stdout."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

# Атрибуты самой записи лога; всё остальное в record.__dict__ - это extra.
_STANDARD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
)

# uvicorn настраивает свои логгеры до нашего lifespan.
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_ATTRS
        }
        payload["timestamp"] = datetime.fromtimestamp(
            record.created, UTC
        ).isoformat()
        payload["level"] = record.levelname
        payload["logger"] = record.name
        payload["message"] = record.getMessage()
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str) -> None:
    """Корневой логгер и логгеры uvicorn переводятся в JSON."""
    formatter = JsonFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    for name in _UVICORN_LOGGERS:
        for uvicorn_handler in logging.getLogger(name).handlers:
            uvicorn_handler.setFormatter(formatter)
