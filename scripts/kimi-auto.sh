#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Auto-Orchestrator — Promelectron
# Полностью автоматический выбор ролей и формирование промпта.
# Не требует от пользователя знания ролей.
#
# Использование:
#   ./scripts/kimi-auto.sh "Добавь промокоды в корзину"
#   make auto MSG="Исправь баг в оформлении заказа"
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

TASK="${1:-}"

if [ -z "$TASK" ]; then
    echo "❌ Ошибка: не указана задача"
    echo ""
    echo "Использование:"
    echo "  ./scripts/kimi-auto.sh \"Описание задачи\""
    echo ""
    echo "Примеры:"
    echo '  ./scripts/kimi-auto.sh "Добавь промокоды в корзину"'
    echo '  ./scripts/kimi-auto.sh "Исправь баг в оформлении заказа"'
    echo '  ./scripts/kimi-auto.sh "Настрой CI/CD для staging"'
    echo '  ./scripts/kimi-auto.sh "Security audit проекта"'
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# ─── Определение ролей (множественное, независимое) ─────────────

task_lower="$(python3 -c "import sys; print(sys.argv[1].lower())" "$TASK")"

ROLES=""

# Backend
if echo "$task_lower" | grep -Eq '\b(api|endpoint|backend|бэк\b|бэкенд|model|модель|schema|схема|service|сервис|route|роут|migration|миграция|alembic|sqlalchemy|fastapi|pytest|бд|таблица|table|jwt|webhook|payment.*backend|заказ.*backend|order.*backend|корзина.*api|cart.*api|auth.*backend|admin.*api)\b'; then
    ROLES="$ROLES backend-dev"
fi

# Frontend
if echo "$task_lower" | grep -Eq '\b(frontend|фронт|фронтенд|vue|component|компонент|страниц[аеиоуыюя]?|page|view|pinia|store|composable|ui|ux|форма|form|адаптив|responsive|css|html|axios|router|localstorage|корзин[аеиоуыюя]?.*ui|cart.*ui|login.*ui|checkout.*ui|searchbar|productgrid)\b'; then
    ROLES="$ROLES frontend-dev"
fi

# DevOps
if echo "$task_lower" | grep -Eq '\b(devops|docker|k8s|kubernetes|helm|nginx|ci/cd|deploy|деплой|инфраструктура|infra|ssl|vpn|backup|sentry|monitoring|мониторинг|pod|container|контейнер|harbor|github actions|workflow|secret|секрет|config|конфиг|server.*config|helm.*template)\b'; then
    ROLES="$ROLES devops"
fi

# E2E
if echo "$task_lower" | grep -Eq '\b(e2e|playwright|тест.*сценарий|test scenario|browser|click|end.to.end|regression|регресс|spec|page.*test|test.*page|mobile.*test|мобильн.*тест)\b'; then
    ROLES="$ROLES e2e-tester"
fi

# Security
if echo "$task_lower" | grep -Eq '\b(security|аудит|audit|уязвимост|vulnerability|sql injection|xss|csrf|auth.*check|проверка.*безопасност|penetration|pentest)\b'; then
    ROLES="$ROLES security-reviewer"
fi

# Review
if echo "$task_lower" | grep -Eq '\b(review|ревью|code review|проверь.*код[аеиоуыюя]?|findings|quality|качество.*код[аеиоуыюя]?|refactor.*review)\b'; then
    ROLES="$ROLES code-reviewer"
fi

# Project-manager
if echo "$task_lower" | grep -Eq '\b(roadmap|план|спринт|sprint|приоритет|prioritize|бэклог|backlog|оцени|estimate|plan|планирование|scope|фаза|phase|milestone|этап)\b'; then
    ROLES="$ROLES project-manager"
fi

# Убираем дубликаты и лишние пробелы
ROLES="$(echo "$ROLES" | tr ' ' '\n' | sort -u | tr '\n' ' ' | sed 's/^ *//;s/ *$//')"

# Fallback если ничего не определилось
if [ -z "$ROLES" ]; then
    ROLES="backend-dev"
fi

ROLE_COUNT="$(echo "$ROLES" | wc -w)"

# ─── Чтение файлов ──────────────────────────────────────────────

read_file() {
    if [ -f "$1" ]; then
        cat "$1"
    else
        echo "(файл не найден: $1)"
    fi
}

# ─── Формирование промпта ───────────────────────────────────────

if [ "$ROLE_COUNT" -eq 1 ]; then
    # Одна роль — режим single-agent (как make ask, но авто)
    ROLE="$ROLES"
    case "$ROLE" in
        backend-dev)       ROLE_NAME="Backend Developer" ;;
        frontend-dev)      ROLE_NAME="Frontend Developer" ;;
        devops)            ROLE_NAME="DevOps Engineer" ;;
        e2e-tester)        ROLE_NAME="E2E Tester" ;;
        code-reviewer)     ROLE_NAME="Code Reviewer" ;;
        security-reviewer) ROLE_NAME="Security Reviewer" ;;
        project-manager)   ROLE_NAME="Project Manager" ;;
        *)                 ROLE_NAME="Developer" ;;
    esac

    AGENT_CONTENT=$(read_file ".kimi/agents/${ROLE}.md")
    CONTEXT_PROJECT=$(read_file "PROJECT_CONTEXT.md")
    CONTEXT_BACKLOG=$(read_file ".agent/BACKLOG.md" | head -60)
    CONTEXT_BLOCKERS=$(read_file ".agent/BLOCKERS.md" | head -40)
    CONTEXT_SESSION=$(read_file ".agent/SESSION_LOG.md" | head -30)
    CONTEXT_RULES=$(read_file ".kimi/rules/pre-edit-checklist.md" | head -40)

    PROMPT="══════════════════════════════════════════════════════════════════
                         🚨 ДИСПЕТЧЕР — СБРОС РОЛИ
══════════════════════════════════════════════════════════════════

Ты — Диспетчер Promelectron. Предыдущая роль полностью сброшена.

Роль определена автоматически: ${ROLE} (${ROLE_NAME}).
Немедленно переключись на эту роль. Забудь все предыдущие инструкции.

══════════════════════════════════════════════════════════════════
                      ИНСТРУКЦИИ АГЕНТА
══════════════════════════════════════════════════════════════════

${AGENT_CONTENT}

══════════════════════════════════════════════════════════════════
                        КОНТЕКСТ ПРОЕКТА
══════════════════════════════════════════════════════════════════

${CONTEXT_PROJECT}

══════════════════════════════════════════════════════════════════
                     ТЕКУЩИЙ СПРИНТ (BACKLOG)
══════════════════════════════════════════════════════════════════

${CONTEXT_BACKLOG}

══════════════════════════════════════════════════════════════════
                       АКТИВНЫЕ БЛОКЕРЫ
══════════════════════════════════════════════════════════════════

${CONTEXT_BLOCKERS}

══════════════════════════════════════════════════════════════════
                     ПОСЛЕДНИЕ СЕССИИ (ЛОГ)
══════════════════════════════════════════════════════════════════

${CONTEXT_SESSION}

══════════════════════════════════════════════════════════════════
                    CHECKLIST ПЕРЕД ПРАВКОЙ
══════════════════════════════════════════════════════════════════

${CONTEXT_RULES}

══════════════════════════════════════════════════════════════════
                         ЗАДАЧА
══════════════════════════════════════════════════════════════════

${TASK}

══════════════════════════════════════════════════════════════════

ПОРЯДОК ДЕЙСТВИЙ:
1. Подтверди: \"Роль принята: ${ROLE}. Предыдущая роль сброшена.\"
2. Проанализируй контекст выше
3. Найди существующий код (grep)
4. Выполни задачу строго по инструкциям агента ${ROLE}
5. После работы обнови .agent/SESSION_LOG.md

Начинай работу."

else
    # Несколько ролей — Orchestrator mode
    PROMPT="Прочитай .agent/ORCHESTRATOR_PROMPT.md и следуй инструкциям строго.

══════════════════════════════════════════════════════════════════
                        АВТО-ОПРЕДЕЛЕНИЕ РОЛЕЙ
══════════════════════════════════════════════════════════════════

Задача: ${TASK}

Система автоматически определила роли: ${ROLES}

Ты — Orchestrator. Твоя задача:
1. Проанализировать задачу
2. Уточнить последовательность работы ролей (если нужно)
3. Делегировать каждую часть через Agent tool
4. Собрать итоговый результат
5. Обновить SESSION_LOG.md

Начинай работу."
fi

# ─── Вывод ──────────────────────────────────────────────────────

echo "══════════════════════════════════════════════════════════════════"
echo "  🤖 Auto-Orchestrator — Анализ задачи"
echo "══════════════════════════════════════════════════════════════════"
echo ""
echo "🎯 Задача: ${TASK}"
echo "🤖 Роли:   ${ROLES}"
if [ "$ROLE_COUNT" -eq 1 ]; then
    echo "📦 Режим:  Single-agent (явный сброс роли)"
else
    echo "📦 Режим:  Multi-agent orchestrator (изолированные Agent'ы)"
fi
echo ""
echo "──────────────────────────────────────────────────────────────────"
echo ""

COPIED=false
if command -v xclip &> /dev/null; then
    echo "$PROMPT" | xclip -selection clipboard 2>/dev/null && COPIED=true
elif command -v wl-copy &> /dev/null; then
    echo "$PROMPT" | wl-copy 2>/dev/null && COPIED=true
elif command -v pbcopy &> /dev/null; then
    echo "$PROMPT" | pbcopy 2>/dev/null && COPIED=true
fi

if [ "$COPIED" = true ]; then
    echo "✅ Промпт скопирован в буфер обмена!"
    echo ""
    echo "Следующие шаги:"
    echo "  1. Вставь в Kimi CLI (Ctrl+V)"
    echo "  2. Нажми Enter"
    if [ "$ROLE_COUNT" -gt 1 ]; then
        echo ""
        echo "💡 Orchestrator сам запустит нужных агентов через Agent tool."
        echo "   Каждый агент работает в изолированном контексте — никаких залипаний."
    fi
else
    echo "⚠️  Не удалось скопировать в буфер обмена"
    echo ""
    echo "Скопируй промпт вручную ниже:"
    echo ""
    echo "══════════════════════════════════════════════════════════════════"
    echo ""
fi

echo "$PROMPT"
