# ============================================================
# My Shop — Makefile
# ============================================================

SHELL := /bin/bash

.PHONY: help dev stop test test-backend test-frontend test-e2e migrate seed lint format

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# --- Dev окружение ---
dev: ## Запустить backend + frontend
	bash scripts/run_dev.sh

stop: ## Остановить backend + frontend
	bash scripts/stop_dev.sh

# --- Тесты ---
test: test-backend test-frontend ## Запустить все тесты

test-backend: ## Запустить backend тесты (pytest)
	source venv/bin/activate && pytest tests/ -v --tb=short

test-frontend: ## Запустить frontend тесты (vitest)
	cd client && npx vitest run

test-e2e: ## Запустить E2E тесты (playwright)
	npx playwright test --project=e2e

test-visual: ## Визуальная проверка — скриншоты всех ключевых страниц
	npx playwright test --project=visual-smoke

test-full: test-backend test-frontend test-e2e test-visual ## Полный цикл: unit + e2e + visual smoke

# --- База данных ---
migrate: ## Применить Alembic миграции
	source venv/bin/activate && alembic upgrade head

migrate-generate: ## Сгенерировать новую Alembic миграцию (make migrate-generate MSG="add users table")
	source venv/bin/activate && alembic revision --autogenerate -m "$(MSG)"

seed: ## Заполнить БД тестовыми данными
	source venv/bin/activate && python seed_data.py

# --- Docker ---
db-up: ## Запустить PostgreSQL в Docker
	docker compose up -d postgres

db-down: ## Остановить PostgreSQL
	docker compose down

# --- Линтинг и форматирование ---
lint: lint-backend lint-frontend ## Линт всего проекта

lint-backend: ## Линт Python (ruff)
	source venv/bin/activate && ruff check server/app

lint-frontend: ## Линт Vue
	cd client && npm run lint 2>/dev/null || npx oxlint src/ 2>/dev/null || echo "Frontend linter not configured"

format: format-backend format-frontend ## Форматировать весь проект

format-backend: ## Форматировать Python (ruff)
	source venv/bin/activate && ruff format server/app

format-frontend: ## Форматировать Vue
	cd client && npm run format 2>/dev/null || echo "Frontend formatter not configured"

# --- Code Review & Security ---
review: ## Code review текущих изменений
	bash scripts/review.sh

review-security: ## Security audit
	bash scripts/security-check.sh

check: lint test review ## Полная проверка: линт + тесты + ревью

# --- Миграции ---
migrate-down: ## Откатить последнюю Alembic миграцию
	source venv/bin/activate && alembic downgrade -1

migrate-history: ## История миграций
	source venv/bin/activate && alembic history

# --- Утилиты ---
clean: ## Очистить кэш и артефакты
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -prune -o -type d -name .vite -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf test-results/ playwright-report/ 2>/dev/null || true

status: ## Статус проекта: git + тесты + линт
	@echo "=== Git Status ==="
	@git status --short
	@echo ""
	@echo "=== Last Commit ==="
	@git log -1 --oneline
	@echo ""
	@echo "=== Branch ==="
	@git branch --show-current
	@echo ""
	@echo "=== Unpushed Commits ==="
	@git log --oneline --graph --left-right @{u}...HEAD 2>/dev/null || echo "No upstream branch"
	@echo ""
	@echo "=== Test Summary ==="
	@source venv/bin/activate && pytest tests/ -q --tb=no 2>&1 | tail -3 || true
	@echo ""
	@echo "=== Frontend Tests ==="
	@cd client && npx vitest run --reporter=dot 2>&1 | tail -3 || true
