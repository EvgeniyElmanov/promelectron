SHELL := /bin/bash

# Машинно-локальные настройки. Файл в .gitignore и подключается через `-include`:
# на машине, где его нет, всё остальное обязано работать как раньше.
# Здесь живёт только то, что завязано на конкретного разработчика — в первую
# очередь AI_CMD: у одного это claude, у другого kimi. См. ai-launcher/README.md.
-include Makefile.override.mk

# ─── AI-лончер ──────────────────────────────────────────────────────────────
# Команда агента НЕ в репозитории: её задаёт Makefile.override.mk на каждой
# машине своя. Здесь только цель, чтобы кнопка на борде была одна для всех.
#   AI_CMD        — сама команда с флагами (claude … / kimi …)
#   AI_PROMPT_OPT — как этой команде передаётся промпт: пусто = позиционным
#                   аргументом (claude), `-p` = флагом (kimi)
#   AI_NAME_OPT   — флаг имени сессии, если у CLI такой есть; пусто = NAME игнорируется
AI_CMD        ?=
AI_PROMPT_OPT ?=
AI_NAME_OPT   ?=
PROMPT      ?=
NAME        ?=
ARGS        ?=
COMPOSE_BACKEND  := docker compose -f backend/docker-compose.yml -p promelectron
COMPOSE_FRONTEND := docker compose -f frontend/docker-compose.yml -p promelectron
COMPOSE          := docker compose -f backend/docker-compose.yml -f frontend/docker-compose.yml -p promelectron
DOCKER_USER      := --user $(shell id -u):$(shell id -g)
# SEED_SECRET для test-e2e: из .env (worktree или корень main-репо ../../.env),
# с fallback на dev-placeholder из .env.example (backend в non-production его принимает).
# Fail-fast на стороне e2e/global-setup.js, если не задан нигде.
SEED_SECRET ?= $(shell grep -h '^SEED_SECRET=' .env ../../.env .env.example ../../.env.example 2>/dev/null | head -1 | cut -d= -f2-)
export SEED_SECRET
# venv проекта: из корня main-репо — ./venv, из worktree .worktrees/<id>/ — ../../venv.
# Переопределяется через make VENV=...
VENV             ?= $(shell [ -d $(CURDIR)/venv ] && echo $(CURDIR)/venv || echo $(CURDIR)/../../venv)
# Lock-файл для сериализации прогонов backend-тестов (гонка template DB при
# параллельных агентах — LESSONS_LEARNED 2026-08-01). flock ждёт до 30 минут.
TEST_BACKEND_LOCK ?= /tmp/promelectron-test-backend.lock

.PHONY: help dev dev-backend dev-frontend stop logs \
        test test-backend test-onec-mock test-frontend test-e2e test-visual test-full \
        migrate migrate-down migrate-generate migrate-history migrate-check seed \
        lint lint-backend lint-onec-mock lint-frontend format format-backend format-frontend \
        build clean status \
        agent-context agent-status agent-audit \
        ai ai-check

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

test-backend: ## Запустить pytest (поднимает postgres/redis через docker compose; flock сериализует параллельные прогоны)
	flock -w 1800 $(TEST_BACKEND_LOCK) bash -c '\
	  $(COMPOSE_BACKEND) up -d postgres redis && \
	  $(COMPOSE_BACKEND) run --rm --entrypoint "" \
	    $(DOCKER_USER) \
	    -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/promelectron \
	    -e REDIS_URL=redis://redis:6379/0 \
	    -e SECRET_KEY=test-secret-key-32-chars-minimum \
	    api sh -c "pytest tests/ -v --tb=short"'

test-onec-mock: ## Запустить pytest мок-сервера 1С (Docker-PG, схема onec_test, pytest на хосте; тот же flock)
	flock -w 1800 $(TEST_BACKEND_LOCK) bash -c '\
	  $(COMPOSE_BACKEND) up -d postgres && \
	  cd mocks/onec-server && \
	  ONEC_MOCK_SCHEMA=onec_test \
	  DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/promelectron \
	  $(VENV)/bin/pytest'

test-frontend: ## Запустить vitest
	$(COMPOSE_FRONTEND) run --rm $(DOCKER_USER) frontend sh -c "npm install --silent && npm test"

test-e2e: ## Запустить Playwright E2E тесты (требует запущенного стека)
	# frontend-test намеренно НЕ поднимаем: его `npm ci` вайпит примонтированный
	# node_modules и гоняется с dev-server/playwright (LESSONS_LEARNED 2026-08-27).
	$(COMPOSE) up -d postgres redis minio meilisearch api job-worker onec-mock frontend
	@echo "Waiting for frontend dev server to be ready..."
	@$(COMPOSE_FRONTEND) run --rm $(DOCKER_USER) frontend sh -c "until curl -s -o /dev/null http://frontend:5173; do sleep 1; done"
	$(COMPOSE_FRONTEND) run --rm $(DOCKER_USER) -e SEED_SECRET frontend sh -c "npm install --silent && npx playwright test --workers=1"

test-visual: ## Визуальный smoke (скриншоты)
	$(COMPOSE) up -d postgres redis minio meilisearch api job-worker onec-mock frontend
	@echo "Waiting for frontend dev server to be ready..."
	@$(COMPOSE_FRONTEND) run --rm $(DOCKER_USER) frontend sh -c "until curl -s -o /dev/null http://frontend:5173; do sleep 1; done"
	$(COMPOSE_FRONTEND) run --rm $(DOCKER_USER) frontend npx playwright test --project=visual-smoke --workers=1

test-full: test-backend test-frontend test-e2e ## Полный цикл: unit + e2e

pre-push: lint test-full ## Запустить перед git push: lint + unit + e2e

# ─── Миграции ───────────────────────────────────────────────────────────────

migrate: ## Применить миграции (alembic upgrade head)
	$(COMPOSE_BACKEND) up -d postgres
	$(COMPOSE_BACKEND) run --rm --entrypoint "" $(DOCKER_USER) api alembic upgrade head

migrate-down: ## Откатить последнюю миграцию
	$(COMPOSE_BACKEND) up -d postgres
	$(COMPOSE_BACKEND) run --rm --entrypoint "" $(DOCKER_USER) api alembic downgrade -1

migrate-generate: ## Сгенерировать миграцию: make migrate-generate MSG="add users"
	$(COMPOSE_BACKEND) up -d postgres
	$(COMPOSE_BACKEND) run --rm --entrypoint "" $(DOCKER_USER) api alembic revision --autogenerate -m "$(MSG)"

migrate-history: ## История миграций
	$(COMPOSE_BACKEND) run --rm --entrypoint "" $(DOCKER_USER) api alembic history

migrate-check: ## Проверить drift схемы (alembic check)
	$(COMPOSE_BACKEND) up -d postgres
	$(COMPOSE_BACKEND) run --rm --entrypoint "" $(DOCKER_USER) api alembic check

seed: ## Залить тестовые данные
	$(COMPOSE_BACKEND) up -d postgres redis
	$(COMPOSE_BACKEND) run --rm $(DOCKER_USER) api python seed_data.py

# ─── Линт / Форматирование ──────────────────────────────────────────────────

lint: lint-backend lint-onec-mock lint-frontend ## Линт всего проекта

lint-onec-mock: ## Линт мок-сервера 1С (ruff)
	$(VENV)/bin/ruff check mocks/onec-server/

lint-backend: ## Линт Python (ruff)
	$(COMPOSE_BACKEND) run --rm --entrypoint "" $(DOCKER_USER) api ruff check src/

lint-frontend: ## Линт Vue/JS (oxlint + eslint)
	$(COMPOSE_FRONTEND) run --rm $(DOCKER_USER) frontend-test sh -c "npm ci && npm run lint"

format: format-backend format-frontend ## Форматировать весь проект

format-backend: ## Форматировать Python (ruff)
	$(COMPOSE_BACKEND) run --rm --entrypoint "" $(DOCKER_USER) api ruff format src/

format-frontend: ## Форматировать Vue/JS (prettier)
	$(COMPOSE_FRONTEND) run --rm $(DOCKER_USER) frontend sh -c "npm install --silent && npm run format"

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

review: ## Code review текущих изменений
	@echo "=== Git Diff ===" && git diff --stat
	@echo "" && echo "=== Lint ===" && make lint
	@echo "" && echo "=== Tests ===" && make test

review-security: ## Security audit checklist
	@echo "=== Security Checklist ==="
	@echo "[ ] Auth guards on new endpoints"
	@echo "[ ] No raw SQL with string formatting"
	@echo "[ ] No PII in logs"
	@echo "[ ] Prices calculated server-side"
	@echo "[ ] No hardcoded secrets"
	@git diff --name-only

check: lint test ## Полная проверка: lint + test + security checklist
	@echo "=== Full Check Complete ==="

# ─── Агент-утилиты ────────────────────────────────────────────────────────────

agent-context: ## Контекст для агента: спринт, блокеры, последние коммиты
	@echo "══════════════════════════════════════════════════════════════════"
	@echo "                   AGENT CONTEXT — Promelectron"
	@echo "══════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📋 PROJECT_CONTEXT.md:"
	@echo "──────────────────────────────────────────────────────────────────"
	@head -35 PROJECT_CONTEXT.md
	@echo ""
	@echo "🎯 Текущий спринт (BACKLOG.md):"
	@echo "──────────────────────────────────────────────────────────────────"
	@head -40 .agent/BACKLOG.md
	@echo ""
	@echo "⚠️  Активные блокеры (BLOCKERS.md):"
	@echo "──────────────────────────────────────────────────────────────────"
	@head -30 .agent/BLOCKERS.md
	@echo ""
	@echo "📝 Последние сессии (SESSION_LOG.md):"
	@echo "──────────────────────────────────────────────────────────────────"
	@head -20 .agent/SESSION_LOG.md
	@echo ""
	@echo "🔨 Последние коммиты:"
	@echo "──────────────────────────────────────────────────────────────────"
	@git log --oneline -10
	@echo ""
	@echo "📁 Незакоммиченные изменения:"
	@echo "──────────────────────────────────────────────────────────────────"
	@git status --short
	@echo ""
	@echo "══════════════════════════════════════════════════════════════════"

# ─── Агент-аудит ─────────────────────────────────────────────────────────────

agent-audit: ## Проверить целостность системы агентов
	@bash scripts/audit-agents.sh

agent-status: ## Быстрый health-check проекта
	@echo "══════════════════════════════════════════════════════════════════"
	@echo "                   AGENT STATUS — Promelectron"
	@echo "══════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "🧪 Tests:"
	@echo "  Backend:  make test-backend"
	@echo "  Frontend: make test-frontend"
	@echo "  E2E:      make test-e2e"
	@echo ""
	@echo "📊 Git:"
	@git log -1 --oneline | sed 's/^/  Last commit: /'
	@git status --short | wc -l | sed 's/^/  Uncommitted files: /'
	@echo ""
	@echo "🐳 Docker:"
	@$(COMPOSE) ps --format "table {{.Service}}\t{{.Status}}" 2>/dev/null | sed 's/^/  /' || echo "  (not running)"
	@echo ""
	@echo "📦 Active blockers:"
	@grep -c "🔴\|🟡" .agent/BLOCKERS.md 2>/dev/null | sed 's/^/  Count: /' || echo "  N/A"
	@echo ""
	@echo "══════════════════════════════════════════════════════════════════"

# ─── AI-лончер ──────────────────────────────────────────────────────────────

ai: ## Запустить агента по промпту: make ai PROMPT=ai-launcher/prompts/x.prompt.txt NAME="#186 …"
	@set -euo pipefail; \
	if [ -z "$(AI_CMD)" ]; then \
	  echo "AI_CMD не задан. Заведи Makefile.override.mk — см. ai-launcher/README.md" >&2; exit 1; fi; \
	if [ -z "$(PROMPT)" ]; then \
	  echo "PROMPT не задан. make ai PROMPT=ai-launcher/prompts/<файл>.prompt.txt" >&2; exit 1; fi; \
	root="$$(git rev-parse --show-toplevel 2>/dev/null || echo "$(CURDIR)")"; \
	f=""; \
	for c in "$(PROMPT)" "$$root/$(PROMPT)" "$$root/ai-launcher/prompts/$(PROMPT)" \
	         "$$root/ai-launcher/prompts/$$(basename "$(PROMPT)")"; do \
	  if [ -f "$$c" ]; then f="$$c"; break; fi; \
	done; \
	if [ -z "$$f" ]; then \
	  echo "Нет файла промпта: $(PROMPT)" >&2; \
	  echo "Искал относительно текущего каталога, корня репозитория и ai-launcher/prompts/." >&2; \
	  echo "Что есть:" >&2; ls "$$root/ai-launcher/prompts/" >&2; exit 1; fi; \
	cd "$$root"; \
	exec $(AI_CMD) $(if $(AI_NAME_OPT),$(if $(NAME),$(AI_NAME_OPT) "$(NAME)")) $(ARGS) $(AI_PROMPT_OPT) "$$(cat "$$f")"

ai-check: ## Проверить, что лончер настроен на этой машине
	@if [ -z "$(AI_CMD)" ]; then \
	  echo "✗ AI_CMD пуст — Makefile.override.mk отсутствует или не задаёт его."; \
	  echo "  Заведи его по образцу из ai-launcher/README.md."; exit 1; \
	else \
	  echo "✓ AI_CMD  = $(AI_CMD)"; \
	  echo "  AI_PROMPT_OPT = $(if $(AI_PROMPT_OPT),$(AI_PROMPT_OPT),(пусто — промпт позиционным аргументом))"; \
	  echo "  AI_NAME_OPT   = $(if $(AI_NAME_OPT),$(AI_NAME_OPT),(не задан — NAME игнорируется))"; \
	  command -v $(firstword $(AI_CMD)) >/dev/null \
	    && echo "✓ $(firstword $(AI_CMD)) есть в PATH" \
	    || { echo "✗ $(firstword $(AI_CMD)) не найден в PATH"; exit 1; }; \
	fi
