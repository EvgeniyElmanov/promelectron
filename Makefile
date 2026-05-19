# ============================================================
# My Shop — Infrastructure & CI/CD Makefile
# ============================================================

SHELL := /bin/bash

.PHONY: help lint review review-security check status clean

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# --- Code Review & Security ---
review: ## Code review текущих изменений
	bash scripts/review.sh

review-security: ## Security audit
	bash scripts/security-check.sh

# --- Validation ---
lint: ## Линт Python (ruff)
	. venv/bin/activate && ruff check . 2>/dev/null || echo "ruff not available"

check: review review-security ## Полная проверка: ревью + секьюрити

# --- CI/CD ---
ci-validate: ## Валидация Helm чартов
	helm lint ./infra/helm

# --- Утилиты ---
clean: ## Очистить кэш и артефакты
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf test-results/ playwright-report/ 2>/dev/null || true

status: ## Статус проекта: git + lint
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
