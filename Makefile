SHELL := /bin/sh
UV ?= uv
COMPOSE ?= docker compose

.PHONY: help setup sync run test lint format typecheck check compose-up compose-down compose-logs compose-ps compose-build compose-restart

help:
	@echo "Targets:"
	@echo "  setup           Copy .env.example to .env if missing"
	@echo "  sync            Install project dependencies"
	@echo "  run             Start Arvel dev server locally"
	@echo "  test            Run pytest suite"
	@echo "  lint            Run Ruff lint checks"
	@echo "  format          Run Ruff formatter"
	@echo "  typecheck       Run ty type checker"
	@echo "  check           Run lint + typecheck + tests"
	@echo "  compose-up      Start app + infra stack in Docker"
	@echo "  compose-down    Stop docker compose stack"
	@echo "  compose-logs    Follow compose logs"
	@echo "  compose-ps      Show compose service status"
	@echo "  compose-build   Rebuild app image"
	@echo "  compose-restart Restart app container"

setup:
	@test -f .env || cp .env.example .env

sync:
	$(UV) sync

run:
	PYTHONPATH=. $(UV) run arvel serve --host 0.0.0.0 --port 8000

test:
	$(UV) run pytest -q

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .

typecheck:
	$(UV) run ty check app/ bootstrap/ config/ database/ routes/ tests/

check: lint typecheck test

pre-commit:
	$(UV) run pre-commit run --all-files

compose-up: setup
	$(COMPOSE) up -d --build

compose-down:
	$(COMPOSE) down --remove-orphans --volumes

compose-logs:
	$(COMPOSE) logs -f --tail=200

compose-ps:
	$(COMPOSE) ps

compose-build:
	$(COMPOSE) build app

compose-restart:
	$(COMPOSE) restart app

clean: compose-down
	rm -rf dist/ build/ *.egg-info/
	rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/ .temp/
	rm -rf htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
