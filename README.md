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

Одной командой:

```bash
make check
```

Отдельно:

```bash
make lint        # ruff check + format --check
make typecheck   # mypy
make fmt         # ruff format (автоисправление)
```

Без make:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

CI (GitHub Actions) гоняет `make check` на каждый push в `main` и на каждый PR.

Есть отдельный workflow `Auto Format`: он запускает `ruff format` и сам коммитит изменения, если они есть.

## Лицензия

MIT, см. [LICENSE](LICENSE).
