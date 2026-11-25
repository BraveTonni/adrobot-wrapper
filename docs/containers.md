# Контейнеры

## Запуск

Создайте локальные настройки Compose и secrets:

```bash
cp .env.example .env
chmod 600 .env
install -d -m 700 backend/.secrets
read -rsp "Keitaro API key: " KEITARO_API_KEY
printf '\n'
printf '%s' "$KEITARO_API_KEY" > backend/.secrets/keitaro_api_key
unset KEITARO_API_KEY
# Internal frontend-to-backend bearer token; this is not the Keitaro API key.
openssl rand -hex 32 > backend/.secrets/api_access_token
printf '%s' 'sqlite+aiosqlite:////data/adrobot.db' > backend/.secrets/database_url
# Browser Basic Auth password; username is admin.
openssl rand -hex 32 > backend/.secrets/frontend_auth_password
```

Запустите сервисы:

```bash
make run
```

`make run` собирает backend и запускает Compose в foreground. Сервис `migrate`
применяет Alembic-миграции перед запуском API. `make up` запускает стек в фоне,
`make down` останавливает контейнеры, `make logs` показывает логи backend.
Команда `make docker-build` собирает образ без Compose и не требует API-key.
JSON-файлы backend доступны на хосте в `logs/`; Compose также продолжает писать
структурированные события в Docker stdout. На Linux проверьте, что каталог
`logs/` доступен на запись пользователю контейнера (UID/GID `10001`).

Основные настройки можно переопределить в локальном `.env`, созданном из
`.env.example`. API-ключ и токен доступа в `.env` не задавайте: Compose получает
их из файлов `backend/.secrets/keitaro_api_key` и
`backend/.secrets/api_access_token`. Keitaro API key монтируется только в
backend, внутренний bearer-токен — в backend и frontend.
Маршруты кампаний, каталога и история операций требуют
`Authorization: Bearer <api_access_token>`.
Compose читает URL базы из `backend/.secrets/database_url`; сервис миграции и
backend используют один и тот же secret. Для PostgreSQL замените содержимое
файла на URL вида `postgresql+asyncpg://user:password@db-host:5432/adrobot?ssl=require`.
Перед миграцией убедитесь, что база доступна из Compose-сети.
Если порт `8000` занят, задайте другой `BACKEND_PORT` в `.env`; публикация
останется привязана к `127.0.0.1`.

Frontend запускается как дополнительный Compose-профиль:

```bash
docker compose --profile frontend up --build
```

Откройте `http://localhost:3000` и войдите с именем `admin` и паролем из
`backend/.secrets/frontend_auth_password`. В production размещайте приложение
за HTTPS reverse proxy. `api_access_token` — внутренний bearer-токен между
frontend и backend; это не ключ Keitaro.

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
  Pydantic Settings читает его через `PYDANTIC_SECRETS_DIR`. URL базы данных
  передаётся таким же file-based secret, чтобы не помещать пароль PostgreSQL в
  переменные окружения контейнера.

## Защита контейнеров

Compose включает read-only root filesystem, удаляет capabilities, запрещает
получать новые привилегии, ограничивает память, CPU и число процессов, а для
временных файлов использует ограниченный `noexec,nosuid,nodev` tmpfs. Для
системного seccomp-профиля Docker оставлено значение по умолчанию. Код не имеет
доступа к Docker socket.

SQLite хранится в отдельном volume `/data`; JSON-журналы пишутся в bind mount
`./logs`. Порт API опубликован только на
`127.0.0.1:8000`. Backend сохраняет исходящий доступ к Keitaro, который нужен
для работы сервиса. Healthcheck обращается к `/api/v1/health`, а Docker-логи
ограничены ротацией.

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
