SHELL := /bin/bash
COMPOSE_BACKEND  := docker compose -f backend/docker-compose.yml -p promelectron
COMPOSE_FRONTEND := docker compose -f frontend/docker-compose.yml -p promelectron
COMPOSE          := docker compose -f backend/docker-compose.yml -f frontend/docker-compose.yml -p promelectron

.PHONY: help dev dev-backend dev-frontend stop logs \
        test test-backend test-frontend test-e2e test-visual test-full \
        migrate migrate-down migrate-generate migrate-history seed \
        lint lint-backend lint-frontend format format-backend format-frontend \
        build clean status

# ─── Справка ───────────────────────────────────────────────────────────────

help: ## Показать все команды
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ─── Dev-окружение ──────────────────────────────────────────────────────────

dev: ## Запустить весь стек (API + PostgreSQL + Redis + Frontend)
	$(COMPOSE) up -d

dev-backend: ## Запустить только бэкенд (API + PostgreSQL + Redis)
	$(COMPOSE_BACKEND) up -d

dev-frontend: ## Запустить только фронтенд
	$(COMPOSE_FRONTEND) up -d

stop: ## Остановить все сервисы
	$(COMPOSE) down

logs: ## Показать логи всех сервисов
	$(COMPOSE) logs -f

logs-api: ## Показать логи API
	$(COMPOSE_BACKEND) logs -f api

logs-frontend: ## Показать логи фронтенда
	$(COMPOSE_FRONTEND) logs -f frontend

# ─── Тесты ──────────────────────────────────────────────────────────────────

test: test-backend test-frontend ## Запустить все unit-тесты

test-backend: ## Запустить pytest (поднимает postgres/redis через docker compose)
	$(COMPOSE_BACKEND) up -d postgres redis
	$(COMPOSE_BACKEND) run --rm --entrypoint "" \
	  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/promelectron \
	  -e REDIS_URL=redis://redis:6379/0 \
	  -e SECRET_KEY=test-secret-key-32-chars-minimum \
	  api sh -c "pip install -q -r requirements-dev.txt && pytest tests/ -v --tb=short"

test-frontend: ## Запустить vitest
	$(COMPOSE_FRONTEND) run --rm frontend sh -c "npm install --silent && npm test"

test-e2e: ## Запустить Playwright E2E тесты (требует запущенного стека)
	$(COMPOSE) up -d
	$(COMPOSE_FRONTEND) run --rm frontend sh -c "npm install --silent && npx playwright install chromium && npm run e2e"

test-visual: ## Визуальный smoke (скриншоты)
	$(COMPOSE_FRONTEND) run --rm frontend sh -c "npm install --silent && npx playwright install chromium && npx playwright test --project=visual-smoke"

test-full: test-backend test-frontend test-e2e ## Полный цикл: unit + e2e

# ─── Миграции ───────────────────────────────────────────────────────────────

migrate: ## Применить миграции (alembic upgrade head)
	$(COMPOSE_BACKEND) up -d postgres
	$(COMPOSE_BACKEND) run --rm --entrypoint "" api alembic upgrade head

migrate-down: ## Откатить последнюю миграцию
	$(COMPOSE_BACKEND) up -d postgres
	$(COMPOSE_BACKEND) run --rm --entrypoint "" api alembic downgrade -1

migrate-generate: ## Сгенерировать миграцию: make migrate-generate MSG="add users"
	$(COMPOSE_BACKEND) up -d postgres
	$(COMPOSE_BACKEND) run --rm --entrypoint "" api alembic revision --autogenerate -m "$(MSG)"

migrate-history: ## История миграций
	$(COMPOSE_BACKEND) run --rm --entrypoint "" api alembic history

seed: ## Залить тестовые данные
	$(COMPOSE_BACKEND) up -d postgres redis
	$(COMPOSE_BACKEND) run --rm api python seed_data.py

# ─── Линт / Форматирование ──────────────────────────────────────────────────

lint: lint-backend lint-frontend ## Линт всего проекта

lint-backend: ## Линт Python (ruff)
	$(COMPOSE_BACKEND) run --rm api ruff check src/

lint-frontend: ## Линт Vue/JS (oxlint + eslint)
	$(COMPOSE_FRONTEND) run --rm frontend sh -c "npm install --silent && npm run lint"

format: format-backend format-frontend ## Форматировать весь проект

format-backend: ## Форматировать Python (ruff)
	$(COMPOSE_BACKEND) run --rm api ruff format src/

format-frontend: ## Форматировать Vue/JS (prettier)
	$(COMPOSE_FRONTEND) run --rm frontend sh -c "npm install --silent && npm run format"

# ─── Сборка образов ─────────────────────────────────────────────────────────

build: ## Пересобрать образы без кэша
	$(COMPOSE) build --no-cache

build-api: ## Пересобрать только API образ
	$(COMPOSE_BACKEND) build --no-cache api

build-frontend: ## Пересобрать только frontend образ
	$(COMPOSE_FRONTEND) build --no-cache frontend

# ─── Утилиты ────────────────────────────────────────────────────────────────

clean: ## Удалить кэш, артефакты
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/playwright-report/ frontend/test-results/ 2>/dev/null || true

status: ## Статус: git + запущенные сервисы
	@echo "=== Git Status ===" && git status --short
	@echo "" && echo "=== Last Commit ===" && git log -1 --oneline
	@echo "" && echo "=== Running Services ===" && $(COMPOSE) ps 2>/dev/null || true
