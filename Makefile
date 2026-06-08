.PHONY: install lint format typecheck test cov run demo up down precommit

install:
	uv sync --extra dev || uv pip install -e ".[dev]"

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

typecheck:
	uv run mypy

test:
	uv run pytest

cov:
	uv run pytest --cov-report=html

run:
	uv run uvicorn sovereign_rag.api.app:app --reload --port 8000

demo:
	uv run python scripts/demo.py

up:
	docker compose up --build

down:
	docker compose down -v

precommit:
	uv run pre-commit run --all-files
