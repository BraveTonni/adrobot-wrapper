# adrobot-wrapper

Веб-сервис поверх Admin API рекламного трекера Keitaro: создаватор кампаний
и редактор офферов.

Что умеет:

- создаёт кампанию с гео-потоком и потоком оффера, проверяет справочники до
  первой записи и удаляет недоделанную кампанию при сбое;
- защищает от дублей: повтор отправки формы с тем же ключом идемпотентности не
  создаёт вторую кампанию;
- редактирует офферы потока: изменения сразу уходят в Keitaro, доли всегда дают
  в сумме 100%, последний оффер потока удалить нельзя;
- ведёт журнал операций со статусами `ok`, `rolled_back`, `rollback_failed` и
  `unknown` в PostgreSQL или SQLite.

## Требования

- GNU Make
- [uv](https://docs.astral.sh/uv/)
- Python 3.14 (Makefile использует uv для локального окружения backend)
- Docker Compose для запуска всего приложения через `make run`

## Запуск

Для локального запуска backend создайте файл настроек и заполните ключ Keitaro
и токен доступа к API:

```bash
cp backend/.env.example backend/.env
```

В `backend/.env` укажите `KEITARO_API_KEY` и задайте случайный
`API_ACCESS_TOKEN` длиной не менее 32 символов. Токен можно сгенерировать
командой `openssl rand -hex 32`. Без ключа Keitaro backend не стартует.
Не коммитьте файл `.env`.

Затем из корня репозитория выполните:

```bash
make backend-install
make alembic ARGS="upgrade head"
make backend-dev
```

Backend будет доступен на `http://127.0.0.1:8000`. Чтобы запустить полный
интерфейс и backend в Docker Compose, используйте:

```bash
make run
```

Для тестового стенда Keitaro называйте создаваемые кампании с префиксом
`test_<фамилия>_`, например `test_ivanov_geo_us`.

### Миграции базы данных

Команда `make alembic` передаёт аргументы в Alembic и использует настройки из
`backend/.env`. Запускайте её из корня репозитория:

```bash
make alembic ARGS="upgrade head"
make alembic ARGS="current"
make alembic ARGS="downgrade -1"
make alembic ARGS="downgrade -3"
make alembic ARGS="revision --autogenerate -m 'describe change'"
```

`downgrade -N` откатывает базу на `N` ревизий. Для создания ревизии сначала
обновите модели, затем запустите `revision --autogenerate` с кратким описанием
изменения.

## Docker Compose

Стек поднимает PostgreSQL, применяет миграции и запускает backend и frontend.
Локальные настройки и секреты создаёт одна команда:

```bash
make secrets
```

Она копирует `.env.example` в `.env` и генерирует случайные токены и пароли в
`backend/.secrets/`, не перезаписывая существующие файлы. Ключ Keitaro
заполните вручную:

```bash
read -rsp "Keitaro API key: " KEITARO_API_KEY
printf '\n'
printf '%s' "$KEITARO_API_KEY" > backend/.secrets/keitaro_api_key
unset KEITARO_API_KEY
make run
```

Compose:

- поднимет **PostgreSQL 16** и применит **миграции**;
- затем запустит backend и frontend;
- API будет доступно только на `127.0.0.1:8000`;
- интерфейс будет доступен на `http://localhost:3000`;
- для входа используйте логин `admin` и пароль из
  `backend/.secrets/frontend_auth_password`.

При запуске Compose напрямую включите профиль интерфейса:
`docker compose --profile frontend up --build`.

Secrets:

- ключ Keitaro монтируется как Compose secret, а не передаётся переменной
  окружения;
- каталог `backend/.secrets` закрыт правами `700`; не ослабляйте права;
- `.env` и secret-файлы нельзя коммитить;
- `keitaro_api_key` — ключ тестового стенда Keitaro;
- `api_access_token` — отдельный случайный токен для вызовов backend из frontend;
- `frontend_auth_password` задаёт пароль браузерного входа; логин — `admin`;
- `postgres_password` — пароль пользователя базы, `database_url` — строка
  подключения, собранная из него.

### Авторизация во frontend

При открытии `http://localhost:3000` браузер запросит Basic Auth. Логин —
`admin`, пароль — содержимое файла `backend/.secrets/frontend_auth_password`.
Этот secret создаётся при настройке Compose выше и передаётся контейнеру
frontend для проверки входа.

Frontend на Next.js также доступен для разработки командами
`make frontend-install` и `make frontend-dev`. Настройка Compose и архитектура
описаны в
[документации frontend](docs/frontend/architecture.md).

## Проверки

Одной командой:

```bash
make backend-install
make frontend-install
make check
```

`make check` запускает backend lint, typecheck и тесты, строгую сборку
документации, а также frontend lint, typecheck, тесты и production build.
Тесты не обращаются к внешним сервисам: помимо unit-тестов они прогоняют
приёмочные сценарии на собранном приложении с настоящим HTTP-контуром и
Keitaro под моками.

Backend пишет JSON-журналы в `logs/` и stdout. Файлы именуются по времени
создания (`YYYY_MM_DD_HH_MM_SS.log`); HTTP-запросы включают correlation ID.

Отдельно:

```bash
make lint        # ruff check + format --check
make typecheck   # mypy
make test        # pytest
make fmt         # ruff format (автоисправление)
make secret-scan # gitleaks: поиск секретов в коммитах
make frontend-check # frontend lint, typecheck, tests и build
```

## Документация

Исходники документации находятся в [`docs/`](docs/), навигация сайта — в
[`mkdocs.yml`](mkdocs.yml). Быстрый просмотр и сборка:

```bash
make docs-serve
make docs
```

Подготовка, API, архитектура и эксплуатация описаны в
[документации проекта](docs/index.md).
Требования к изменениям и тестам находятся в
[CONTRIBUTING.md](CONTRIBUTING.md).

CI (GitHub Actions) гоняет `make check` на каждый push в `main` и на каждый PR.
Отдельная джоба поднимает PostgreSQL 16, применяет миграции, сверяет их с
моделями (`alembic check`) и запускает сценарии и тесты репозиториев на нём.

Есть отдельный workflow `Auto Format`: он запускает `ruff format` и сам коммитит изменения, если они есть.

Есть workflow `Secret Scan` (gitleaks): проверяет коммиты на утечку токенов и API-ключей.

## Лицензия

MIT, см. [LICENSE](LICENSE).
