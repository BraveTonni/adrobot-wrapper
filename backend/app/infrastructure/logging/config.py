"""Structured application logging to stdout and timestamped JSON files."""

import contextvars
import json
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)

_STANDARD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
)
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")
_SENSITIVE_KEYS = (
    "authorization",
    "password",
    "secret",
    "token",
    "api_key",
    "database_url",
)
_SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[=:]\s*)[^\r\n,;]+"),
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/-]+=*"),
    re.compile(
        r"(?i)(password|token|secret|api[_-]?key)(\s*[=:]\s*)([^\s,;&]+)"
    ),
    re.compile(r"(?i)(://[^:/\s]+:)[^@/\s]+@"),
)


def _redact_text(value: str) -> str:
    value = _SENSITIVE_TEXT_PATTERNS[0].sub(r"\1[REDACTED]", value)
    value = _SENSITIVE_TEXT_PATTERNS[1].sub(r"\1[REDACTED]", value)
    value = _SENSITIVE_TEXT_PATTERNS[2].sub(r"\1\2[REDACTED]", value)
    return _SENSITIVE_TEXT_PATTERNS[3].sub(r"\1[REDACTED]@", value)


def _redact(value: Any, key: str = "") -> Any:
    normalized_key = key.casefold().replace("-", "_")
    if any(sensitive in normalized_key for sensitive in _SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {
            str(item_key): _redact(item, str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class JsonFormatter(logging.Formatter):
    """Render one safe, searchable JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            key: _redact(value, key)
            for key, value in record.__dict__.items()
            if key not in _STANDARD_ATTRS
        }
        payload["timestamp"] = datetime.fromtimestamp(
            record.created, UTC
        ).isoformat()
        payload["level"] = record.levelname
        payload["logger"] = record.name
        payload["message"] = _redact_text(record.getMessage())
        payload["request_id"] = request_id_context.get()
        if record.exc_info:
            payload["exception"] = _redact_text(
                self.formatException(record.exc_info)
            )
        return json.dumps(payload, ensure_ascii=False, default=str)


class TimestampedJsonFileHandler(logging.Handler):
    """Write append-only JSON logs, opening a new timestamped file each day."""

    def __init__(self, directory: Path, formatter: logging.Formatter) -> None:
        super().__init__()
        self.directory = directory
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.formatter = formatter
        self._file_date = ""
        self._stream: Any = None
        self._open_file()

    def _open_file(self) -> None:
        now = datetime.now(UTC)
        self._file_date = now.strftime("%Y_%m_%d")
        filename = now.strftime("%Y_%m_%d_%H_%M_%S.log")
        self._stream = (self.directory / filename).open("a", encoding="utf-8")
        try:
            os.chmod(self._stream.name, 0o600)
        except OSError:
            # On platforms without POSIX modes, retain the platform defaults.
            pass

    def emit(self, record: logging.LogRecord) -> None:
        try:
            current_date = datetime.now(UTC).strftime("%Y_%m_%d")
            if current_date != self._file_date:
                self._stream.close()
                self._open_file()
            self._stream.write(self.format(record) + "\n")
            self._stream.flush()
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        self.acquire()
        try:
            if self._stream is not None:
                self._stream.close()
                self._stream = None
        finally:
            self.release()
            super().close()


def setup_logging(level: str, directory: Path = Path("logs")) -> None:
    """Configure JSON stdout and private timestamped file logging."""
    formatter = JsonFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    root.addHandler(console_handler)
    root.setLevel(level.upper())
    try:
        root.addHandler(TimestampedJsonFileHandler(directory, formatter))
    except OSError as exc:
        # Например, bind mount в контейнере закрыт на запись: сервис
        # остаётся доступен, а те же события уходят в stdout.
        logging.getLogger(__name__).warning(
            "запись журнала в файл отключена: каталог %s недоступен (%s)",
            directory,
            exc,
        )

    for name in _UVICORN_LOGGERS:
        logger = logging.getLogger(name)
        for handler in logger.handlers:
            handler.setFormatter(formatter)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.NOTSET)
    # Uvicorn's access message includes raw paths and query strings. The HTTP
    # middleware records route templates instead, avoiding accidental PII logs.
    logging.getLogger("uvicorn.access").disabled = True
