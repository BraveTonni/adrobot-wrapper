# Локальная разработка и production

Требуются Node.js 22 и npm. Скопируйте `frontend/.env.example` в `frontend/.env.local`, укажите `BACKEND_API_URL` и задайте `API_ACCESS_TOKEN`, совпадающий с backend bearer-токеном (не короче 32 символов). Эти значения используются только серверным процессом Next.js; ключ Keitaro здесь не задаётся.

```bash
make frontend-install
make frontend-dev
```

Проверки: `make frontend-lint`, `make frontend-typecheck`, `make frontend-test`, `make frontend-build`. Production запускается через `cd frontend && npm start` после build. Docker образ собирается командой `make frontend-docker-build`; Compose профиль запускается командой `docker compose --profile frontend up --build`. В Compose frontend читает bearer-токен из того же secret-файла `backend/.secrets/api_access_token`, что и backend. Приложение доступно на `localhost:3000`.
