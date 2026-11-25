# Доступ к API

Все маршруты `/api/v1/campaigns`, `/api/v1/offers`, `/api/v1/references` и
`/api/v1/operations` требуют `Authorization: Bearer <API_ACCESS_TOKEN>`.
`/api/v1/health` остаётся доступен без токена для Docker healthcheck и возвращает
только общий статус `ok` либо ошибку сервиса.

Задайте случайный токен не короче 32 символов. При прямом запуске передайте его
через `API_ACCESS_TOKEN` в `backend/.env`. В Compose используйте файл
`backend/.secrets/api_access_token`; он монтируется как secret и не попадает в
окружение процесса. Пример создания файла приведён в [руководстве по
контейнерам](../containers.md).

Ключ Keitaro и токен доступа — разные секреты. Не используйте ключ Keitaro как
токен для клиентов этого API и не передавайте ни один из них в URL.

Защищённые маршруты ограничивают неверные попытки авторизации: после восьми
неудачных попыток с одного адреса в течение минуты API временно отвечает `429`
и задаёт `Retry-After`. Счётчик хранится в памяти процесса, поэтому в много-
worker или нескольких экземплярах дополнительно настройте общий rate limit на
reverse proxy/API gateway.

CORS закрыт по умолчанию. Если браузерный клиент размещён на другом origin,
задайте `CORS_ALLOWED_ORIGINS` как JSON-массив точных origin, например
`["https://app.example.com"]`; wildcard `*` запрещён. API также добавляет
`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
`Permissions-Policy` и CSP для ответов, кроме интерактивных `/docs` и `/redoc`.
