# Архитектура frontend

Приложение использует Next.js App Router, React и TypeScript strict. Структура разделяет маршруты, общие компоненты, функции кампаний и транспорт API:

```text
src/
  app/                         # Next.js маршруты, layout, глобальные стили
  app/styles/                  # глобальные правила и светлые/тёмные токены
  components/layout/           # шапка, боковая панель, подвал, переключатель темы
  features/campaigns/          # сценарии кампаний, формы и редактор
  lib/                         # типы API и единый HTTP-клиент
```

`app/page.tsx` собирает экран из feature-компонента. `CampaignWorkspace` связывает состояние сценария с отображением. `useCampaignWorkspace` управляет загрузкой и изменением данных. Компоненты форм и редактора отображают состояние и вызывают переданные обработчики. API-запросы находятся в одном типизированном клиенте.

Все страницы и API-запросы frontend защищены HTTP Basic Auth: имя пользователя
`admin`, пароль хранится в Compose secret `frontend_auth_password`. Для локальной
разработки задайте `FRONTEND_AUTH_PASSWORD` длиной не менее 32 символов.

## Интеграция с backend

Браузер вызывает внутренний Next.js route handler `/api/backend/*`. Обработчик передаёт запрос backend, адрес которого берётся из серверной переменной `BACKEND_API_URL`, и добавляет Bearer-токен из серверной переменной `API_ACCESS_TOKEN` либо файла `API_ACCESS_TOKEN_FILE`. В Compose токен доступен frontend как secret-файл. Значение токена не передаётся браузеру. Проксируются `GET /api/v1/references`, `GET /offers`, `GET /campaigns?search=`, `GET /campaigns/{id}`, `POST /campaigns` и POST/DELETE для офферов потоков. Форматы соответствуют Pydantic-схемам backend. Ошибки API централизованно преобразуются в сообщения для пользователя.

Proxy принимает только same-origin POST/DELETE, ограничивает тело 64 KiB и не
передаёт browser credentials backend. В production публикуйте frontend только
за HTTPS reverse proxy.

Создание кампании также отправляет уникальный `Idempotency-Key`. При повторной отправке неизменённой формы используется тот же ключ, чтобы backend не создал дубль после сетевого сбоя.

Переменная `BACKEND_API_URL` читается Next.js на сервере. Keitaro API key остаётся исключительно в backend и не передаётся браузеру.

Структура следует референсу MilkCord: маршруты собирают страницы, сценарии сгруппированы по feature, повторно используемый UI отделён, запросы и типы контрактов централизованы. Реализация адаптирована под App Router.
