# Доступ к API

Все маршруты `/api/v1/campaigns` и `/api/v1/operations` требуют
`Authorization: Bearer <API_ACCESS_TOKEN>`. `/health`, `/offers` и `/references`
остаются доступны без токена для healthcheck и получения справочников.

Задайте случайный токен не короче 32 символов. При прямом запуске передайте его
через `API_ACCESS_TOKEN` в `backend/.env`. В Compose используйте файл
`backend/.secrets/api_access_token`; он монтируется как secret и не попадает в
окружение процесса. Пример создания файла приведён в [руководстве по
контейнерам](../containers.md).

Ключ Keitaro и токен доступа — разные секреты. Не используйте ключ Keitaro как
токен для клиентов этого API и не передавайте ни один из них в URL.
