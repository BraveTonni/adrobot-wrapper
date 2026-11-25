# adrobot-wrapper

Веб-сервис поверх Admin API рекламного трекера Keitaro: создаватор кампаний
и редактор офферов.

## Требования

- [uv](https://docs.astral.sh/uv/)
- Python 3.14 (uv подтянет сам)

## Запуск

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Или через корневой Makefile:

```bash
make run
```

## Docker Compose

Для локального запуска скопируйте `.env.example` в `.env`, задайте
нечувствительные настройки при необходимости и создайте все Compose secrets:

```bash
cp .env.example .env
chmod 600 .env
install -d -m 700 backend/.secrets
read -rsp "Keitaro API key: " KEITARO_API_KEY
printf '\n'
printf '%s' "$KEITARO_API_KEY" > backend/.secrets/keitaro_api_key
unset KEITARO_API_KEY
openssl rand -hex 32 > backend/.secrets/api_access_token
printf '%s' 'sqlite+aiosqlite:////data/adrobot.db' > backend/.secrets/database_url
openssl rand -hex 32 > backend/.secrets/frontend_auth_password
make run
```

Compose сначала применит миграции, затем запустит backend. API доступно только
на `127.0.0.1:8000`. Ключ Keitaro монтируется как Compose secret, а не
передаётся переменной окружения. `.env` и secret-файл нельзя коммитить.
Каталог secrets закрыт правами `700`; не ослабляйте права каталога.
`keitaro_api_key` — ключ тестового стенда Keitaro. `api_access_token` — отдельный
случайный токен внутреннего вызова backend из frontend. `frontend_auth_password`
задаёт пароль браузерного входа; имя пользователя — `admin`.

Frontend на Next.js доступен локально командами `make frontend-install` и
`make frontend-dev`. Настройка Compose и архитектура описаны в
[документации frontend](docs/frontend/architecture.md).

## Проверки

Одной командой:

```bash
cd backend && uv sync --locked
cd frontend && npm ci
cd ..
make check
```

`make check` запускает backend lint, typecheck и тесты, строгую сборку
документации, а также frontend lint, typecheck, тесты и production build.

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

Без make (backend):

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

Без make (frontend):

```bash
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

CI (GitHub Actions) гоняет `make check` на каждый push в `main` и на каждый PR.

Есть отдельный workflow `Auto Format`: он запускает `ruff format` и сам коммитит изменения, если они есть.

Есть workflow `Secret Scan` (gitleaks): проверяет коммиты на утечку токенов и API-ключей.

## Лицензия

MIT, см. [LICENSE](LICENSE).
