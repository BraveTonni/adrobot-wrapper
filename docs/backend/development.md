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

Заполните `KEITARO_API_KEY` и `API_ACCESS_TOKEN` (случайный секрет не короче
32 символов), а при необходимости URL/ID справочников в `.env`. Без
`KEITARO_API_KEY` backend не стартует.
Подробности приведены в [конфигурации](configuration.md).

## Запуск без контейнера

```bash
cd backend
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Локальный адрес по умолчанию — `http://127.0.0.1:8000`. Интерактивная схема
FastAPI доступна по `/docs`, OpenAPI JSON — по `/openapi.json`.

Команда `make run` из корня запускает backend и frontend через Docker Compose.
Настройку
контейнеров, секретов и миграций см. в [общем руководстве по контейнерам](../containers.md).

## Проверки

```bash
make fmt         # сортировка импортов и форматирование Python-файлов
make check       # Ruff, mypy, pytest, документация и проверки frontend
make test        # pytest
make docs        # строгая сборка документации
make docs-serve  # локальный сервер документации с автообновлением
```

`make test` запускает три набора тестов, ни один из них не обращается к
внешним сервисам:

- unit-тесты слоёв: сценарии создания и редактора, распределение долей,
  клиент Keitaro под моками `respx`, SQL-репозитории на SQLite, обработчики
  ошибок;
- `tests/acceptance` — сценарии на собранном приложении: настоящий HTTP-контур
  с аутентификацией и обработчиками ошибок, база, поднятая настоящими
  миграциями, и Keitaro под моками;
- репозитории и миграции на PostgreSQL (`tests/integration/postgres`) — только
  с переменной `TEST_DATABASE_URL`, в CI их запускает отдельная джоба.

Общий сторож `respx` в `conftest.py` валит любой незамоканный HTTP-запрос.
Интеграционные тесты настоящего Keitaro помечены `integration` и не входят в
`make test` по умолчанию.

GitHub Actions собирает backend-образ и запускает Trivy. Сборка падает при
исправляемых уязвимостях уровня HIGH или CRITICAL; проверка запускается для
pull request, push в `main` и еженедельно.

## Тесты на PostgreSQL

Джоба `postgres` в CI поднимает PostgreSQL 16, применяет миграции, сверяет их
с моделями командой `alembic check` и запускает приёмочные сценарии и тесты
репозиториев. Локально нужен любой доступный PostgreSQL 16:

```bash
docker run -d --name adrobot-pg -e POSTGRES_USER=adrobot \
  -e POSTGRES_PASSWORD=adrobot -e POSTGRES_DB=adrobot -p 5432:5432 postgres:16-alpine
cd backend
export TEST_DATABASE_URL=postgresql+asyncpg://adrobot:adrobot@127.0.0.1:5432/adrobot
export ACCEPTANCE_DATABASE_URL="$TEST_DATABASE_URL"
uv run pytest tests/acceptance
uv run pytest -m integration tests/integration/postgres
```

Оба набора сами применяют миграции и откатывают базу до пустой схемы.

## Тесты настоящего Keitaro

Интеграционные тесты Keitaro по умолчанию исключены из быстрого набора,
чтобы обычный запуск не обращался к внешнему API. Задайте `KEITARO_API_KEY`
в `backend/.env` и запускайте тесты из `backend/`.

```bash
uv run pytest tests/integration/infrastructure/keitaro/test_client.py -m integration
```

Этот тест выполняет только чтение списка офферов.

Сквозной тест создания кампании и редактирования оффера дополнительно требует
переменную `KEITARO_TEST_CAMPAIGN_PREFIX` с префиксом `test_<фамилия>_`. Он
создаёт временную кампанию с этим префиксом и удаляет её после проверки.
Запустить оба интеграционных теста можно командой:

```bash
KEITARO_TEST_CAMPAIGN_PREFIX='test_<фамилия>_' uv run pytest -m integration
```

## Изменение схемы

После изменения ORM-моделей создайте и примените миграцию из `backend/`,
затем убедитесь, что модель и миграция не разошлись:

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
uv run alembic check
```

Миграции должны работать и на SQLite, и на PostgreSQL: для изменения типов и
ограничений используйте `op.batch_alter_table`.

## Как менять документацию

Общие Markdown-файлы лежат в `docs/`, backend-документация — в `docs/backend/`,
структура сайта описана в `mkdocs.yml`.
При добавлении страницы обновите `nav` в `mkdocs.yml` и проверьте ссылки:

```bash
make docs
```

CI запускает строгую сборку документации, поэтому предупреждения о битых
ссылках или некорректной навигации нужно исправить до слияния.
