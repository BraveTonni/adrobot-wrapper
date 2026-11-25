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
| `OFFERS_CACHE_TTL` | `300` | TTL кэша офферов в секундах |
| `REFERENCE_CACHE_TTL` | `300` | TTL кэша справочников в секундах |
| `CAMPAIGN_SEARCH_LIMIT` | `500` | Максимальное число кампаний, запрашиваемых для поиска |
| `LOG_LEVEL` | `INFO` | Уровень логирования |
| `LOG_DIRECTORY` | `../logs` | Каталог JSON-логов; путь относительно рабочей директории backend |

Backend пишет по одной JSON-записи на строку одновременно в stdout и в файл
`YYYY_MM_DD_HH_MM_SS.log`. Имя задаёт время создания файла; при смене UTC-даты
открывается следующий файл. HTTP-запросы получают `X-Request-ID`; в журнал
попадают метод, шаблон маршрута, статус и длительность. Заголовки, тела запросов
и ответы внешних сервисов не журналируются; поля с токенами, ключами, паролями и
URL базы данных редактируются. Ограничьте доступ к `logs/` и настройте удаление
старых файлов на уровне хоста или платформы.

`KEITARO_URL` и `KEITARO_ADMIN_URL` обязаны использовать HTTPS. URL с HTTP,
встроенными credentials, query-параметрами или fragment отклоняются при запуске,
чтобы ключ Keitaro не передавался открытым текстом.

Значения справочников применяются только для пропущенных параметров создания
кампании. Не передавайте API-ключ в документацию, коммиты или логи.

Офферы и справочники Keitaro сохраняются в таблице `catalog_cache` на пять минут
(TTL настраивается через `OFFERS_CACHE_TTL` и `REFERENCE_CACHE_TTL`). Кнопка
«Обновить каталог» в форме создания кампании вызывает `POST /api/v1/catalog/refresh`
и принудительно перечитывает оба набора.
