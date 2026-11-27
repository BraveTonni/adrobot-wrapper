import json
import logging

from app.infrastructure.logging.config import JsonFormatter, setup_logging


def test_json_formatter_includes_standard_and_extra_fields() -> None:
    record = logging.LogRecord(
        "app.test",
        logging.WARNING,
        "test.py",
        12,
        "hello %s",
        ("world",),
        None,
    )
    record.campaign_id = 7
    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "WARNING"
    assert payload["logger"] == "app.test"
    assert payload["message"] == "hello world"
    assert payload["campaign_id"] == 7
    assert payload["timestamp"].endswith("+00:00")


def test_json_formatter_includes_exception() -> None:
    try:
        raise ValueError("broken")
    except ValueError:
        record = logging.getLogger("test").makeRecord(
            "test",
            logging.ERROR,
            "test.py",
            1,
            "failed",
            (),
            __import__("sys").exc_info(),
        )

    payload = json.loads(JsonFormatter().format(record))
    assert "ValueError: broken" in payload["exception"]


def test_setup_logging_configures_root_and_uvicorn_handlers(
    monkeypatch,
) -> None:
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    uvicorn_logger = logging.getLogger("uvicorn")
    original_uvicorn_handlers = uvicorn_logger.handlers[:]
    handler = logging.StreamHandler()
    uvicorn_logger.handlers = [handler]

    try:
        setup_logging("DEBUG")
        assert root.level == logging.DEBUG
        assert isinstance(root.handlers[0].formatter, JsonFormatter)
        assert isinstance(handler.formatter, JsonFormatter)
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)
        uvicorn_logger.handlers = original_uvicorn_handlers


def test_setup_logging_keeps_stdout_when_the_directory_is_not_writable(
    tmp_path, capsys
) -> None:
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("file")

    try:
        setup_logging("INFO", blocker / "logs")

        assert [type(handler) for handler in root.handlers] == [
            logging.StreamHandler
        ]
        # Пред warning уходит в единый консольный handler.
        assert "недоступен" in capsys.readouterr().err
    finally:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
            handler.close()
        root.handlers = original_handlers
        root.setLevel(original_level)
