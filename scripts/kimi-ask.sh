#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Kimi Ask — Гарантированное переключение роли при каждом запросе
#
# Отличие от kimi-task.sh:
#   - Всегда начинает с Диспетчера (сброс предыдущей роли)
#   - Вставляет инструкции агента прямо в промпт (не требует чтения файлов LLM)
#   - 100% детерминированность роли (определяется bash, не LLM)
#
# Использование:
#   ./scripts/kimi-ask.sh "Сделай страницу checkout"
#   make ask MSG="Добавь API для промокодов"
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

TASK="${1:-}"

if [ -z "$TASK" ]; then
    echo "❌ Ошибка: не указана задача"
    echo ""
    echo "Использование:"
    echo "  ./scripts/kimi-ask.sh \"Описание задачи\""
    echo ""
    echo "Примеры:"
    echo '  ./scripts/kimi-ask.sh "Создай API гостевой корзины"'
    echo '  ./scripts/kimi-ask.sh "Исправь Helm шаблон для worker"'
    echo '  ./scripts/kimi-ask.sh "Напиши E2E тест на checkout"'
    exit 1
fi

# ─── Определение роли (как в kimi-task.sh) ────────────────────────

detect_role() {
    local task_lower="$(python3 -c "import sys; print(sys.argv[1].lower())" "$TASK")"

    # Hybrid: API integration into frontend
    if echo "$task_lower" | grep -Eq '(подключи|интегрируй|connect|integrate).*(api|endpoint).*(форм|компонент|страниц|view|ui|vue|frontend|фронт)'; then
        echo "frontend-dev"
        return
    fi

    # Backend keywords
    if echo "$task_lower" | grep -Eq '\b(api|endpoint|backend|бэк\b|бэкенд|model|модель|schema|схема|service|сервис|route|роут|migration|миграция|alembic|sqlalchemy|fastapi|pytest|бд|таблица|table|jwt|oauth.*backend|webhook|payment.*backend|заказ.*backend|order.*backend|корзина.*api|cart.*api|auth.*backend|admin.*api)'; then
        echo "backend-dev"
        return
    fi

    # DevOps keywords
    if echo "$task_lower" | grep -Eq '\b(devops|docker|k8s|kubernetes|helm|nginx|ci/cd|deploy|деплой|инфраструктура|infra|ssl|vpn|backup|sentry|monitoring|мониторинг|pod|container|контейнер|harbor|github actions|workflow|\.env|secret|секрет|config|конфиг|server.*config|helm.*template)'; then
        echo "devops"
        return
    fi

    # Frontend keywords
    if echo "$task_lower" | grep -Eq '\b(frontend|фронт|фронтенд|vue|component|компонент|страниц[аеиоуыюя]?|page|view|pinia|store|composable|ui|ux|форма|form|адаптив|responsive|css|html|axios|router|localstorage|корзин[аеиоуыюя]?.*ui|cart.*ui|login.*ui|checkout.*ui|searchbar|productgrid)'; then
        echo "frontend-dev"
        return
    fi

    # E2E keywords
    if echo "$task_lower" | grep -Eq '\b(e2e|playwright|тест.*сценарий|test scenario|browser|click|end.to.end|regression|регресс|spec|spec\.js|spec\.ts|page.*test|test.*page|mobile.*test|мобильн.*тест|test.*mobile|тест.*мобильн)'; then
        echo "e2e-tester"
        return
    fi

    # Security keywords
    if echo "$task_lower" | grep -Eq '\b(security|аудит|audit|уязвимост|vulnerability|sql injection|xss|csrf|auth.*check|проверка.*безопасност| penetration|pentest)'; then
        echo "security-reviewer"
        return
    fi

    # Review keywords
    if echo "$task_lower" | grep -Eq '\b(review|ревью|code review|проверь.*код[аеиоуыюя]?|findings|quality|качество.*код[аеиоуыюя]?|refactor.*review)'; then
        echo "code-reviewer"
        return
    fi

    # Project-manager keywords
    if echo "$task_lower" | grep -Eq '\b(roadmap|план|спринт|sprint|приоритет|prioritize|бэклог|backlog|оцени|estimate|plan|планирование|scope|фаза|phase|milestone|этап)'; then
        echo "project-manager"
        return
    fi

    # Default fallback
    echo "backend-dev"
}

ROLE=$(detect_role)

# ─── Сопоставление роли с названием ───────────────────────────────

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

# ─── Чтение файлов ────────────────────────────────────────────────

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

read_file() {
    if [ -f "$1" ]; then
        cat "$1"
    else
        echo "(файл не найден: $1)"
    fi
}

AGENT_CONTENT=$(read_file ".kimi/agents/${ROLE}.md")
CONTEXT_PROJECT=$(read_file "PROJECT_CONTEXT.md")
CONTEXT_BACKLOG=$(read_file ".agent/BACKLOG.md" | head -60)
CONTEXT_BLOCKERS=$(read_file ".agent/BLOCKERS.md" | head -40)
CONTEXT_SESSION=$(read_file ".agent/SESSION_LOG.md" | head -30)
CONTEXT_RULES=$(read_file ".kimi/rules/pre-edit-checklist.md" | head -40)

GIT_LOG=$(git log --oneline -10 2>/dev/null || echo "(нет git истории)")
GIT_STATUS=$(git status --short 2>/dev/null || echo "(нет git)")

# ─── Формирование промпта ─────────────────────────────────────────

PROMPT="══════════════════════════════════════════════════════════════════
                         🚨 ДИСПЕТЧЕР — СБРОС РОЛИ
══════════════════════════════════════════════════════════════════

Ты — Диспетчер Promelectron. Предыдущая роль полностью сброшена.

Роль определена скриптом: ${ROLE} (${ROLE_NAME}).
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
                         GIT СОСТОЯНИЕ
══════════════════════════════════════════════════════════════════

Последние коммиты:
${GIT_LOG}

Незакоммиченные изменения:
${GIT_STATUS}

══════════════════════════════════════════════════════════════════
                        ЗАДАЧА
══════════════════════════════════════════════════════════════════

${TASK}

══════════════════════════════════════════════════════════════════

ПОРЯДОК ДЕЙСТВИЙ:
1. Подтверди: \"Роль принята: ${ROLE}. Предыдущая роль сброшена.\"
2. Проанализируй контекст выше
3. Найди существующий код, который затрагивается (grep)
4. Выполни задачу строго по инструкциям агента ${ROLE}
5. После работы обнови .agent/SESSION_LOG.md

Начинай работу."

# ─── Вывод / Копирование ──────────────────────────────────────────

echo "══════════════════════════════════════════════════════════════════"
echo "  Kimi Ask — Полный промпт с диспетчером"
echo "══════════════════════════════════════════════════════════════════"
echo ""
echo "🎯 Задача: ${TASK}"
echo "🤖 Роль:   ${ROLE} (${ROLE_NAME})"
echo "📦 Размер: $(echo "$PROMPT" | wc -c) байт"
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
    echo "  1. Вставь в Kimi CLI (Ctrl+V / Cmd+V)"
    echo "  2. Нажми Enter"
    echo ""
    echo "💡 Этот промпт можно вставить в ЛЮБУЮ точку сессии —"
    echo "   диспетчер явно сбросит предыдущую роль."
    echo ""
else
    echo "⚠️  Не удалось скопировать в буфер обмена"
    echo ""
    echo "Скопируй промпт вручную ниже:"
    echo ""
    echo "══════════════════════════════════════════════════════════════════"
    echo ""
fi

echo "$PROMPT"
