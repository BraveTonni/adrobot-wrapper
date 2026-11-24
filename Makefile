.PHONY: check lint typecheck fmt run

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
