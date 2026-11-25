# Конфигурация

Настройки объявлены в `backend/app/config.py`. Pydantic Settings читает
переменные окружения и `.env` из текущей рабочей директории. При запуске
команд из `Makefile` рабочая директория приложения — `backend/`.

Скопируйте `backend/.env.example` в `backend/.env` и укажите API-ключ Keitaro.
Файл `.env` игнорируется Git.

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `KEITARO_URL` | `https://keitaro-for-tests.etolegko.com/admin_api/v1` | Базовый URL Admin API |
| `KEITARO_API_KEY` | пустая строка | API-ключ, отправляемый в заголовке `Api-Key` |
| `KEITARO_ADMIN_URL` | `https://keitaro-for-tests.etolegko.com/admin` | Базовый URL интерфейса Keitaro для ссылок кампаний |
| `KEITARO_TIMEOUT` | `15.0` | Таймаут HTTP-запроса в секундах |
| `DEFAULT_DOMAIN_ID` | `1813` | Домен кампании, если ID не передан в запросе |
| `DEFAULT_GROUP_ID` | `10332` | Группа кампании по умолчанию |
| `DEFAULT_SOURCE_ID` | `836` | Источник трафика по умолчанию |
| `GEO_REDIRECT_URL` | `https://google.com` | URL действия гео-потока |
| `DATABASE_URL` | `sqlite+aiosqlite:///./adrobot.db` | SQLAlchemy URL базы данных |
| `OFFERS_CACHE_TTL` | `3600` | TTL кэша офферов в секундах |
| `REFERENCE_CACHE_TTL` | `3600` | TTL кэша справочников в секундах |
| `CAMPAIGN_SEARCH_LIMIT` | `500` | Максимальное число кампаний, запрашиваемых для поиска |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

Значения справочников применяются только для пропущенных параметров создания
кампании. Не передавайте API-ключ в документацию, коммиты или логи.
