.PHONY: check lint typecheck fmt run test secret-scan

check: lint typecheck

lint:
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .

typecheck:
	cd backend && uv run mypy .

fmt:
	cd backend && uv run ruff format .

run:
	cd backend && uv run python -m uvicorn app.main:app --reload

test:
	cd backend && uv run pytest

secret-scan:
	gitleaks detect --source . --config .gitleaks.toml
