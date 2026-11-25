# Локальная разработка и production

Требуются Node.js 22 и npm. Скопируйте `frontend/.env.example` в `frontend/.env.local`, укажите `BACKEND_API_URL`, задайте `API_ACCESS_TOKEN`, совпадающий с backend bearer-токеном, и `FRONTEND_AUTH_PASSWORD` длиной не менее 32 символов. Используйте случайный пароль. Имя пользователя браузерного входа — `admin`. Эти значения используются только серверным процессом Next.js; ключ Keitaro здесь не задаётся.

```bash
make frontend-install
make frontend-dev
```

Проверки: `make frontend-lint`, `make frontend-typecheck`, `make frontend-test`, `make frontend-build`. После production build запускайте standalone-сервер командой `cd frontend && node .next/standalone/server.js`. Docker образ собирается командой `make frontend-docker-build`; Compose профиль запускается командой `docker compose --profile frontend up --build`. В Compose frontend читает bearer-токен и пароль браузерного входа из отдельных secret-файлов. Приложение доступно на `localhost:3000`.
