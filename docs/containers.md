# Контейнеры

## Запуск

Создайте локальные настройки Compose и секреты одной командой:

```bash
make secrets
```

Она копирует `.env.example` в `.env`, генерирует случайные токены и пароли в
`backend/.secrets/` и собирает URL базы. Существующие файлы команда не
перезаписывает, поэтому её безопасно повторять. Ключ Keitaro сервис получить не
может: заполните его вручную.

```bash
read -rsp "Keitaro API key: " KEITARO_API_KEY
printf '\n'
printf '%s' "$KEITARO_API_KEY" > backend/.secrets/keitaro_api_key
unset KEITARO_API_KEY
```

Запустите сервисы:

```bash
make run
```

`make run` собирает backend и frontend и запускает Compose в foreground.
Сервис `migrate` применяет Alembic-миграции, как только база проходит
healthcheck, и только затем запускается API. `make up` запускает стек в фоне,
`make down` останавливает контейнеры, `make logs` показывает логи backend.
Команда `make docker-build` собирает образ без Compose и не требует API-key.
JSON-файлы backend доступны на хосте в `logs/`; Compose также продолжает писать
структурированные события в Docker stdout. Если каталог `logs/` недоступен на
запись пользователю контейнера (UID/GID `10001`), backend продолжает работу с
выводом в stdout.

Основные настройки можно переопределить в локальном `.env`, созданном из
`.env.example`. API-ключ и токен доступа в `.env` не задавайте: Compose получает
их из файлов `backend/.secrets/keitaro_api_key` и
`backend/.secrets/api_access_token`. Keitaro API key монтируется только в
backend, внутренний bearer-токен — в backend и frontend.
Маршруты кампаний, каталога и история операций требуют
`Authorization: Bearer <api_access_token>`.
Если порт `8000` занят, задайте другой `BACKEND_PORT` в `.env`; публикация
останется привязана к `127.0.0.1`.

Команды `make run` и `make up` включают frontend-профиль. Для запуска Compose
вручную укажите этот профиль:

```bash
docker compose --profile frontend up --build
```

Откройте `http://localhost:3000` и войдите с именем `admin` и паролем из
`backend/.secrets/frontend_auth_password`. В production размещайте приложение
за HTTPS reverse proxy. `api_access_token` — внутренний bearer-токен между
frontend и backend; это не ключ Keitaro.

## База данных

По умолчанию стек использует PostgreSQL 16: сервис `db` хранит данные в volume
`postgres_data`, пароль читается из секрета `postgres_password`, а backend и
миграции подключаются по URL из секрета `database_url`:

```text
postgresql+asyncpg://adrobot:<postgres_password>@db:5432/adrobot
```

Порт PostgreSQL наружу не публикуется. Чтобы подключиться к базе для
диагностики, выполните `docker compose exec db psql -U adrobot -d adrobot`.

SQLite остаётся вариантом для локального запуска: задайте URL вида
`sqlite+aiosqlite:////data/adrobot.db` в том же секрете — сервис `db` при этом
просто не используется. Для внешней PostgreSQL задайте URL вида
`postgresql+asyncpg://user:password@db-host:5432/adrobot?ssl=require` и
подключайте migrate и backend своим Compose-файлом: условия `depends_on` в
`compose.yaml` относятся к локальному сервису `db`.

## Защита образа

- Dockerfile использует отдельные стадии сборки и запуска. В runtime копируются
  только production-зависимости, код приложения и миграции; `uv`, dev-пакеты и
  тесты в него не попадают.
- Python и uv закреплены по multi-platform digest. Runtime-пакеты обновляются
  из датированного Debian snapshot; обновляйте digest и snapshot согласованно,
  чтобы получать исправления безопасности с воспроизводимым составом образа.
- Frontend использует конкретные версии Node.js и Alpine; Trivy регулярно
  сканирует его зависимости и runtime-образ.
- Runtime запускается от UID/GID `10001`; код и виртуальное окружение принадлежат
  root и доступны приложению только для чтения.
- API-ключ не попадает в build context, слои образа или переменные окружения
  процесса. Секрет монтируется Compose в `/run/secrets/keitaro_api_key`;
  Pydantic Settings читает его через `PYDANTIC_SECRETS_DIR`. URL базы данных и
  пароль PostgreSQL передаются такими же file-based secret, чтобы не помещать
  их в переменные окружения контейнера.

## Защита контейнеров

Compose включает read-only root filesystem, удаляет capabilities, запрещает
получать новые привилегии, ограничивает память, CPU и число процессов, а для
временных файлов использует ограниченный `noexec,nosuid,nodev` tmpfs. Для
системного seccomp-профиля Docker оставлено значение по умолчанию. Код не имеет
доступа к Docker socket.

У сервиса `db` после `cap_drop: ALL` возвращены только те capabilities, которые
официальному образу PostgreSQL нужны, чтобы подготовить каталог данных и
снизить права до пользователя `postgres`: `CHOWN`, `DAC_OVERRIDE`, `FOWNER`,
`SETGID` и `SETUID`. Сокеты и временные файлы базы лежат в tmpfs.

Порт API опубликован только на `127.0.0.1:8000`, порт интерфейса — на
`127.0.0.1:3000`; порт базы не публикуется. Backend сохраняет исходящий доступ к
Keitaro, который нужен для работы сервиса. Healthcheck обращается к
`/api/v1/health`, а Docker-логи ограничены ротацией.

Compose задаёт защиту контейнера, но не переводит сам Docker daemon в rootless
режим. Для production рассмотрите rootless Docker или user namespace remapping
на уровне хоста и ограничьте доступ к Docker socket.

## Хранение секретов

Папка `backend/.secrets/` исключена из Git и имеет права `700`; храните её на
доверенном локальном диске и не ослабляйте права каталога. Compose монтирует
файлы секретов read-only. Локальный Compose использует bind mount; `uid`, `gid`
и `mode` из Compose не могут изменить права файла. Не делайте файлы доступными
через общие каталоги хоста. Каталог `700` закрывает их от других пользователей
хоста, а Compose подключает каждый файл только сервисам из его `secrets:`.

Локальные Compose secrets не шифруются в хранилище Docker. Не помещайте туда
ключ, который не разрешено хранить на локальной машине. В production используйте
secret manager платформы или внешние Docker secrets. См. документацию Docker о
[Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/) и
[ограничениях file-based secrets](https://docs.docker.com/reference/compose-file/container-spec/).

`docker compose down` сохраняет volume базы данных. Для удаления локальной базы
используйте `docker compose down --volumes` только если данные больше не нужны.
