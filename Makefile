.PHONY: check lint typecheck fmt run secret-scan

check: lint typecheck

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy .

fmt:
	uv run ruff format .

run:
	uv run main.py

secret-scan:
	gitleaks detect --source . --config .gitleaks.toml
