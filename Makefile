.DEFAULT_GOAL := help

.PHONY: help check lint typecheck fmt secrets run up down logs docker-build migrate backend-install backend-dev alembic test docs docs-serve secret-scan frontend-install frontend-dev frontend-lint frontend-typecheck frontend-test frontend-build frontend-check frontend-docker-build

help:
	@echo "Доступные команды:"
	@echo "  make secrets      Создать локальные .env и секреты Compose"
	@echo "  make run          Собрать и запустить приложение через Docker Compose"
	@echo "  make up           Запустить Compose в фоне"
	@echo "  make down         Остановить Compose и удалить контейнеры/сеть"
	@echo "  make logs         Показать логи backend"
	@echo "  make docker-build Собрать backend-образ без запуска Compose"
	@echo "  make migrate      Выполнить миграции базы данных"
	@echo "  make backend-install Установить зависимости backend для локальной разработки"
	@echo "  make backend-dev     Запустить backend локально"
	@echo "  make alembic ARGS=... Выполнить команду Alembic локально"
	@echo "  make check        Проверить backend, frontend, тесты и документацию"
	@echo "  make lint         Запустить Ruff"
	@echo "  make typecheck    Запустить mypy"
	@echo "  make test         Запустить pytest"
	@echo "  make fmt          Отсортировать импорты и отформатировать Python"
	@echo "  make docs         Собрать документацию"
	@echo "  make docs-serve   Запустить локальный сервер документации"
	@echo "  make secret-scan  Проверить репозиторий через gitleaks"
	@echo "  make frontend-install Установить зависимости frontend"
	@echo "  make frontend-dev     Запустить frontend в режиме разработки"
	@echo "  make frontend-check   Проверить frontend lint/typecheck/tests/build"

check: lint typecheck test docs frontend-check

lint:
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .

typecheck:
	cd backend && uv run mypy .

fmt:
	cd backend && uv run ruff check --select I --fix .
	cd backend && uv run ruff format .

secrets:
	./scripts/create-local-secrets.sh

run:
	docker compose --profile frontend up --build

up:
	docker compose --profile frontend up --build -d

down:
	docker compose down

logs:
	docker compose logs -f backend

docker-build:
	docker build -f backend/Dockerfile -t adrobot-wrapper-backend:local backend

migrate:
	docker compose run --rm migrate

backend-install:
	cd backend && uv sync

backend-dev:
	cd backend && uv run uvicorn app.main:app --reload

alembic:
	cd backend && uv run alembic $(ARGS)

test:
	cd backend && uv run pytest

docs:
	cd backend && uv run mkdocs build --strict -f ../mkdocs.yml

docs-serve:
	cd backend && uv run mkdocs serve -f ../mkdocs.yml

secret-scan:
	gitleaks detect --source . --config .gitleaks.toml

frontend-install:
	cd frontend && npm ci

frontend-dev:
	cd frontend && npm run dev

frontend-lint:
	cd frontend && npm run lint

frontend-typecheck:
	cd frontend && npm run typecheck

frontend-test:
	cd frontend && npm test

frontend-build:
	cd frontend && npm run build

frontend-check: frontend-lint frontend-typecheck frontend-test frontend-build

frontend-docker-build:
	docker build -f frontend/Dockerfile -t adrobot-wrapper-frontend:local frontend
