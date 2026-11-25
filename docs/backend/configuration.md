# Конфигурация

Настройки объявлены в `backend/app/config/settings.py`. Pydantic Settings читает
переменные окружения и `.env` из текущей рабочей директории. В Docker Compose
API-ключ и URL базы читаются из secret-файлов в `/run/secrets`.

Маршруты кампаний, каталога и `/operations` требуют `API_ACCESS_TOKEN`. Для Compose
сгенерируйте токен и сохраните его в `backend/.secrets/api_access_token`;
локальный запуск может читать `API_ACCESS_TOKEN` из `backend/.env`.

Скопируйте `backend/.env.example` в `backend/.env` и укажите API-ключ Keitaro.
Файл `.env` игнорируется Git.

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `KEITARO_URL` | `https://keitaro-for-tests.etolegko.com/admin_api/v1` | Базовый URL Admin API |
| `KEITARO_API_KEY` | пустая строка | API-ключ, отправляемый в заголовке `Api-Key` |
| `KEITARO_ADMIN_URL` | `https://keitaro-for-tests.etolegko.com/admin` | Базовый URL интерфейса Keitaro для ссылок кампаний |
| `KEITARO_TIMEOUT` | `15.0` | Таймаут HTTP-запроса в секундах |
| `API_ACCESS_TOKEN` | пустая строка | Bearer-токен для маршрутов кампаний, каталога и истории; в Compose читается из secret-файла |
| `CORS_ALLOWED_ORIGINS` | `[]` | JSON-массив разрешённых браузерных origin; wildcard запрещён |
| `DEFAULT_DOMAIN_ID` | `1813` | Домен кампании, если ID не передан в запросе |
| `DEFAULT_GROUP_ID` | `10332` | Группа кампании по умолчанию |
| `DEFAULT_SOURCE_ID` | `836` | Источник трафика по умолчанию |
| `GEO_REDIRECT_URL` | `https://google.com` | URL действия гео-потока |
| `DATABASE_URL` | `sqlite+aiosqlite:///./adrobot.db` | SQLAlchemy URL базы данных; поддерживаются SQLite и PostgreSQL через `asyncpg` |
| `OFFERS_CACHE_TTL` | `3600` | TTL кэша офферов в секундах |
| `REFERENCE_CACHE_TTL` | `3600` | TTL кэша справочников в секундах |
| `CAMPAIGN_SEARCH_LIMIT` | `500` | Максимальное число кампаний, запрашиваемых для поиска |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

Значения справочников применяются только для пропущенных параметров создания
кампании. Не передавайте API-ключ в документацию, коммиты или логи.
