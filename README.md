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

Для локального запуска скопируйте `.env.example` в `.env`, укажите
нечувствительные настройки при необходимости, создайте secret-файл и
выполните:

```bash
install -d -m 700 backend/.secrets
read -rsp "Keitaro API key: " KEITARO_API_KEY
printf '\n'
printf '%s' "$KEITARO_API_KEY" > backend/.secrets/keitaro_api_key
unset KEITARO_API_KEY
chmod 444 backend/.secrets/keitaro_api_key
make run
```

Compose сначала применит миграции, затем запустит backend. API доступно только
на `127.0.0.1:8000`. Ключ Keitaro монтируется как Compose secret, а не
передаётся переменной окружения. `.env` и secret-файл нельзя коммитить.

Frontend пока не реализован. Его сервис выключен по умолчанию и подключается
профилем `frontend` после добавления `frontend/Dockerfile`. Подробности
безопасности контейнера и управления секретом описаны в
[руководстве по контейнерам](docs/containers.md).

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
make secret-scan # gitleaks: поиск секретов в коммитах
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

Без make:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

CI (GitHub Actions) гоняет `make check` на каждый push в `main` и на каждый PR.

Есть отдельный workflow `Auto Format`: он запускает `ruff format` и сам коммитит изменения, если они есть.

Есть workflow `Secret Scan` (gitleaks): проверяет коммиты на утечку токенов и API-ключей.

## Лицензия

MIT, см. [LICENSE](LICENSE).
