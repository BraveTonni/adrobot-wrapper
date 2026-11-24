# adrobot-wrapper

Веб-сервис поверх Admin API рекламного трекера Keitaro: создаватор кампаний
и редактор офферов.

## Требования

- [uv](https://docs.astral.sh/uv/)
- Python 3.14 (uv подтянет сам)

## Запуск

```bash
uv sync
uv run main.py
```

## Проверки

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

## Лицензия

MIT, см. [LICENSE](LICENSE).
