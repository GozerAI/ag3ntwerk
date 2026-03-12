.PHONY: help install dev test lint format typecheck migrate up down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Setup ───────────────────────────────────────────────────────────

install: ## Install production dependencies
	pip install -e .

dev: ## Install all dependencies (dev + distributed) and pre-commit hooks
	pip install -e ".[all]"
	pre-commit install

# ── Testing ─────────────────────────────────────────────────────────

test: ## Run unit tests with coverage
	pytest tests/unit -v --cov=ag3ntwerk --cov-report=term-missing

test-all: ## Run all tests
	pytest -v

test-integration: ## Run integration tests (requires infrastructure)
	pytest tests/integration -v -m integration

# ── Code Quality ────────────────────────────────────────────────────

lint: ## Run ruff linter
	ruff check src/ tests/

format: ## Format code with black and fix lint issues
	black src/ tests/
	ruff check --fix src/ tests/

typecheck: ## Run mypy type checking
	mypy src/ag3ntwerk/ --ignore-missing-imports

check: lint typecheck ## Run all static checks

# ── Database ────────────────────────────────────────────────────────

migrate: ## Run pending Alembic migrations
	alembic upgrade head

migrate-new: ## Create a new migration (usage: make migrate-new MSG="description")
	alembic revision --autogenerate -m "$(MSG)"

# ── Docker ──────────────────────────────────────────────────────────

up: ## Start core services (ag3ntwerk + postgres + redis)
	docker compose up -d

up-all: ## Start all services including federated + monitoring
	docker compose --profile federated --profile monitoring up -d

down: ## Stop all services
	docker compose --profile federated --profile monitoring --profile llm down

build: ## Build all Docker images
	docker compose --profile federated build

# ── Cleanup ─────────────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov/ coverage.xml .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
