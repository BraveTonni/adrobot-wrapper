# Разработка и локальный запуск

## Требования

- Python 3.14 (устанавливается через `uv` при необходимости).
- `uv`.
- Доступный Keitaro Admin API и API-ключ для работы с интеграцией.

## Подготовка

```bash
cd backend
uv sync
cp .env.example .env
```

Заполните `KEITARO_API_KEY` и при необходимости URL/ID справочников в `.env`.
Подробности приведены в [конфигурации](configuration.md).

## Запуск без контейнера

```bash
cd backend
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Локальный адрес по умолчанию — `http://127.0.0.1:8000`. Интерактивная схема
FastAPI доступна по `/docs`, OpenAPI JSON — по `/openapi.json`.

Команда `make run` из корня запускает приложение через Docker Compose. Настройку
контейнеров, секретов и миграций см. в [общем руководстве по контейнерам](../containers.md).

## Проверки

```bash
make check       # Ruff и mypy
make test        # pytest
make fmt         # форматирование Python-файлов
make docs        # строгая сборка документации
make docs-serve  # локальный сервер документации с автообновлением
```

GitHub Actions собирает backend-образ и запускает Trivy. Сборка падает при
исправляемых уязвимостях уровня HIGH или CRITICAL; проверка запускается для
pull request, push в `main` и еженедельно.

Интеграционный тест Keitaro-клиента по умолчанию исключён из быстрого набора,
чтобы обычный запуск не обращался к внешнему API. Для отдельного запуска
задайте `KEITARO_API_KEY` в `backend/.env` и выполните из `backend/`:

```bash
uv run pytest -m integration
```

Тест выполняет только чтение списка офферов.

После изменения схемы ORM создайте и примените миграцию из `backend/`:

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

## Как менять документацию

Общие Markdown-файлы лежат в `docs/`, backend-документация — в `docs/backend/`,
структура сайта описана в `mkdocs.yml`.
При добавлении страницы обновите `nav` в `mkdocs.yml` и проверьте ссылки:

```bash
make docs
```

CI запускает строгую сборку документации, поэтому предупреждения о битых
ссылках или некорректной навигации нужно исправить до слияния.
