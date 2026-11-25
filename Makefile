.PHONY: check lint typecheck fmt run test docs docs-serve secret-scan

check: lint typecheck docs

lint:
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .

typecheck:
	cd backend && uv run mypy .

fmt:
	cd backend && uv run ruff check --select I --fix .
	cd backend && uv run ruff format .

run:
	cd backend && uv run python -m uvicorn app.main:app --reload

test:
	cd backend && uv run pytest

docs:
	cd backend && uv run mkdocs build --strict -f ../mkdocs.yml

docs-serve:
	cd backend && uv run mkdocs serve -f ../mkdocs.yml

secret-scan:
	gitleaks detect --source . --config .gitleaks.toml
