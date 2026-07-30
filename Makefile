.PHONY: install lint format typecheck test cov run demo up down precommit helm-lint helm-template load

HELM_CHART := deploy/helm/sovereign-rag
BASE_URL ?= http://localhost:8000

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

helm-lint:
	helm lint $(HELM_CHART)

helm-template:
	helm template srag $(HELM_CHART)

load:
	BASE_URL=$(BASE_URL) k6 run load/k6/rag_query.js
