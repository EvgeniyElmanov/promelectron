# ============================================================
# My Shop — Makefile
# ============================================================

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
lint-backend: ## Линт Python (ruff / flake8 если установлен)
	-source venv/bin/activate && python -m py_compile server/app/**/*.py

lint-frontend: ## Линт Vue
	cd client && npm run lint

format-frontend: ## Форматировать Vue
	cd client && npm run format
