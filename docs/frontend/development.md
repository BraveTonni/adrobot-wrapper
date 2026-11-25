# Локальная разработка и production

Требуются Node.js 22 и npm. Скопируйте `frontend/.env.example` в `frontend/.env.local` и при необходимости задайте `BACKEND_API_URL` (по умолчанию `http://127.0.0.1:8000`). Переменная доступна только серверному процессу Next.js; ключ Keitaro здесь не задаётся.

```bash
make frontend-install
make frontend-dev
```

Проверки: `make frontend-lint`, `make frontend-typecheck`, `make frontend-build`. Production запускается через `cd frontend && npm start` после build. Docker образ собирается командой `make frontend-docker-build`; Compose профиль запускается командой `docker compose --profile frontend up --build`. Приложение доступно на `localhost:3000`.
