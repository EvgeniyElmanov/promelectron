#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Router Test — Promelectron
# Проверяет, что роутер правильно определяет роли для типовых задач
# Запуск: ./scripts/test-router.sh
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

ERRORS=0

echo "══════════════════════════════════════════════════════════════════"
echo "  Router Test — Promelectron"
echo "══════════════════════════════════════════════════════════════════"
echo ""

# Функция теста
test_role() {
    local task="$1"
    local expected="$2"
    local description="$3"
    
    echo "🧪 $description"
    echo "   Задача: $task"
    
    output=$(./scripts/kimi-task.sh "$task" 2>&1 || true)
    actual=$(echo "$output" | grep "🤖 Агент:" | head -1 | sed 's/.*🤖 Агент: *//' | awk '{print $1}')
    
    if [ "$actual" = "$expected" ]; then
        echo "   ✅ Определён как: $actual"
    else
        echo "   ❌ Ожидалось: $expected, Получено: ${actual:-'(не определено)'}"
        ((ERRORS++))
    fi
    echo ""
}

# ─── Тесты ────────────────────────────────────────────────────────

echo "📋 Backend-задачи"
test_role "Создай API для промокодов" "backend-dev" "API endpoint"
test_role "Добавь модель OrderItem в БД" "backend-dev" "Модель БД"
test_role "Сделай Alembic миграцию для таблицы payments" "backend-dev" "Миграция"
test_role "Напиши webhook для ЮKassa" "backend-dev" "Webhook"
test_role "Добавь JWT авторизацию" "backend-dev" "Auth backend"

echo "📋 Frontend-задачи"
test_role "Создай компонент корзины на Vue" "frontend-dev" "Vue компонент"
test_role "Добавь Pinia store для заказов" "frontend-dev" "Pinia store"
test_role "Сделай страницу checkout" "frontend-dev" "Страница"
test_role "Добавь адаптив для мобильных" "frontend-dev" "Адаптив"
test_role "Подключи API к форме оплаты" "frontend-dev" "API integration"

echo "📋 DevOps-задачи"
test_role "Исправь Helm шаблон для worker" "devops" "Helm"
test_role "Настрой CI/CD pipeline" "devops" "CI/CD"
test_role "Добавь Docker контейнер для Redis" "devops" "Docker"
test_role "Настрой nginx reverse proxy" "devops" "Nginx"
test_role "Добавь SSL сертификаты" "devops" "SSL"

echo "📋 E2E-задачи"
test_role "Напиши E2E тест на checkout" "e2e-tester" "E2E сценарий"
test_role "Протестируй регистрацию через Playwright" "e2e-tester" "Playwright"
test_role "Добавь тест на мобильную версию" "e2e-tester" "Mobile E2E"

echo "📋 Security-задачи"
test_role "Проверь код на SQL injection" "security-reviewer" "Security audit"
test_role "Аудит авторизации" "security-reviewer" "Auth audit"

echo "📋 Review-задачи"
test_role "Сделай code review последних изменений" "code-reviewer" "Code review"
test_role "Проверь качество кода" "code-reviewer" "Quality review"

echo "📋 Project Manager-задачи"
test_role "Обнови бэклог на следующую неделю" "project-manager" "Backlog update"
test_role "Спланируй спринт" "project-manager" "Sprint planning"
test_role "Оцени приоритеты задач" "project-manager" "Prioritization"

# ─── Итог ─────────────────────────────────────────────────────────

echo "══════════════════════════════════════════════════════════════════"
echo "  РЕЗУЛЬТАТ"
echo "══════════════════════════════════════════════════════════════════"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo "  🎉 Все тесты пройдены! Роутер работает корректно."
else
    echo "  ❌ Ошибок: $ERRORS"
    echo "     Роутер требует доработки!"
fi

echo ""
exit $ERRORS
