SHELL := /bin/sh
UV ?= uv
COMPOSE ?= docker compose
APP_DIRS := app/ bootstrap/ config/ database/ routes/
TEST_DIR := tests/

.DEFAULT_GOAL := help

.PHONY: help setup sync run test test-unit test-integration coverage \
	lint format format-check typecheck check verify pre-commit \
	migrate seed fresh \
	compose-up compose-down compose-logs compose-ps compose-build compose-restart clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ──── Setup ────

setup: ## Copy .env.example to .env if missing
	@test -f .env || cp .env.example .env

sync: ## Install project dependencies
	$(UV) sync

serve: ## Start Arvel dev server locally
	PYTHONPATH=. $(UV) run arvel serve --host 0.0.0.0 --port 8000

# ──── Testing ────

test: ## Run full test suite
	$(UV) run pytest $(TEST_DIR) -v --tb=short

test-unit: ## Run unit tests only (no Docker required)
	$(UV) run pytest $(TEST_DIR) -v --tb=short -m "not integration"

test-integration: ## Run integration-marked tests only (Docker required)
	$(UV) run pytest $(TEST_DIR) -v --tb=short -m "integration"

coverage: ## Run tests with coverage report
	$(UV) run pytest $(TEST_DIR) -v --cov=$(firstword $(APP_DIRS)) --cov-report=term-missing --cov-report=html --cov-fail-under=80

# ──── Code Quality ────

lint: ## Run linter + format check
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Auto-format source code
	$(UV) run ruff format .

format-check: ## Check formatting without changes
	$(UV) run ruff format --check .

typecheck: ## Run type checker
	$(UV) run ty check $(APP_DIRS) $(TEST_DIR)

check: lint typecheck test ## Run lint + typecheck + tests (alias for verify)

verify: check ## Run lint + typecheck + tests (quick CI gate)

pre-commit: ## Run pre-commit hooks on all files
	$(UV) run pre-commit run --all-files

# ──── Database ────

migrate: ## Run database migrations
	$(UV) run arvel db migrate

seed: ## Seed the database
	$(UV) run arvel db seed

fresh: ## Drop and recreate database + migrate + seed
	@if [ "$$APP_ENV" != "testing" ] && [ "$$APP_ENV" != "development" ] && [ -z "$$APP_ENV" ]; then \
		echo ""; \
		echo "WARNING: APP_ENV is not 'testing' or 'development'."; \
		echo "This will destroy all data. Are you sure? [y/N]"; \
		read -r confirm; \
		if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
			echo "Aborted."; \
			exit 1; \
		fi; \
	fi
	$(UV) run arvel db fresh

# ──── Docker Compose ────

compose-up: setup ## Start app + infra stack in Docker
	$(COMPOSE) up -d --build

compose-down: ## Stop Docker compose stack
	$(COMPOSE) down --remove-orphans --volumes

compose-logs: ## Follow Docker compose logs
	$(COMPOSE) logs -f --tail=200

compose-ps: ## Show Docker service status
	$(COMPOSE) ps

compose-build: ## Rebuild app image
	$(COMPOSE) build app

compose-restart: ## Restart app container
	$(COMPOSE) restart app

clean: compose-down ## Stop services, remove volumes, clean caches
	$(COMPOSE) down -v 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info/
	rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/ .tests/
	rm -rf htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
