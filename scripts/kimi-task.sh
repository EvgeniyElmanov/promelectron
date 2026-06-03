#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Agent Router — Promelectron
# Автоматически выбирает агента по задаче, собирает контекст,
# формирует готовый промпт для Kimi CLI.
#
# Использование:
#   ./scripts/kimi-task.sh "Создай webhook для ЮKassa"
#   make task MSG="Добавить гостевую корзину на фронтенде"
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

TASK="${1:-}"

if [ -z "$TASK" ]; then
    echo "❌ Ошибка: не указана задача"
    echo ""
    echo "Использование:"
    echo "  ./scripts/kimi-task.sh \"Описание задачи\""
    echo ""
    echo "Примеры:"
    echo '  ./scripts/kimi-task.sh "Создай API гостевой корзины"'
    echo '  ./scripts/kimi-task.sh "Исправь Helm шаблон для worker"'
    echo '  ./scripts/kimi-task.sh "Напиши E2E тест на checkout"'
    exit 1
fi

# ─── Определение роли по ключевым словам ──────────────────────────

detect_role() {
    local task_lower="$(python3 -c "import sys; print(sys.argv[1].lower())" "$TASK")"

    # Hybrid: API integration into frontend (e.g. "Подключи API к форме оплаты")
    if echo "$task_lower" | grep -Eq '(подключи|интегрируй|connect|integrate).*(api|endpoint).*(форм|компонент|страниц|view|ui|vue|frontend|фронт)'; then
        echo "frontend-dev"
        return
    fi

    # Backend keywords
    if echo "$task_lower" | grep -Eq '\b(api|endpoint|backend|бэк\b|бэкенд|model|модель|schema|схема|service|сервис|route|роут|migration|миграция|alembic|sqlalchemy|fastapi|pytest|бд|таблица|table|jwt|oauth.*backend|webhook|payment.*backend|заказ.*backend|order.*backend|корзина.*api|cart.*api|auth.*backend|admin.*api)\b'; then
        echo "backend-dev"
        return
    fi

    # DevOps keywords
    if echo "$task_lower" | grep -Eq '\b(devops|docker|k8s|kubernetes|helm|nginx|ci/cd|deploy|деплой|инфраструктура|infra|ssl|vpn|backup|sentry|monitoring|мониторинг|pod|container|контейнер|harbor|github actions|workflow|\.env|secret|секрет|config|конфиг|server.*config|helm.*template)\b'; then
        echo "devops"
        return
    fi

    # Frontend keywords — склоняемые слова через [аеиоуыюя]?\b
    if echo "$task_lower" | grep -Eq '\b(frontend|фронт|фронтенд|vue|component|компонент|страниц[аеиоуыюя]?|page|view|pinia|store|composable|ui|ux|форма|form|адаптив|responsive|css|html|axios|router|localstorage|корзин[аеиоуыюя]?.*ui|cart.*ui|login.*ui|checkout.*ui|searchbar|productgrid)\b'; then
        echo "frontend-dev"
        return
    fi

    # E2E keywords
    if echo "$task_lower" | grep -Eq '\b(e2e|playwright|тест.*сценарий|test scenario|browser|click|end.to.end|regression|регресс|spec|spec\.js|spec\.ts|page.*test|test.*page|mobile.*test|мобильн.*тест|test.*mobile|тест.*мобильн)'; then
        echo "e2e-tester"
        return
    fi

    # Security keywords
    if echo "$task_lower" | grep -Eq '\b(security|аудит|audit|уязвимост|vulnerability|sql injection|xss|csrf|auth.*check|проверка.*безопасност| penetration|pentest)\b'; then
        echo "security-reviewer"
        return
    fi

    # Review keywords
    if echo "$task_lower" | grep -Eq '\b(review|ревью|code review|проверь.*код[аеиоуыюя]?|findings|quality|качество.*код[аеиоуыюя]?|refactor.*review)\b'; then
        echo "code-reviewer"
        return
    fi

    # Project-manager keywords
    if echo "$task_lower" | grep -Eq '\b(roadmap|план|спринт|sprint|приоритет|prioritize|бэклог|backlog|оцени|estimate|plan|планирование|scope|фаза|phase|milestone|этап)\b'; then
        echo "project-manager"
        return
    fi

    # Default fallback
    echo "backend-dev"
}

ROLE=$(detect_role)

# ─── Сопоставление роли с человекочитаемым названием ──────────────

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

# ─── Чтение контекста ─────────────────────────────────────────────

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Функция для безопасного чтения файла
read_file() {
    if [ -f "$1" ]; then
        cat "$1"
    else
        echo "(файл не найден: $1)"
    fi
}

CONTEXT_PROJECT=$(read_file "PROJECT_CONTEXT.md")
CONTEXT_BACKLOG=$(read_file ".agent/BACKLOG.md" | head -60)
CONTEXT_BLOCKERS=$(read_file ".agent/BLOCKERS.md" | head -40)
CONTEXT_SESSION=$(read_file ".agent/SESSION_LOG.md" | head -30)
CONTEXT_AGENT=$(read_file ".kimi/agents/${ROLE}.md")
CONTEXT_TASK_TEMPLATE=$(read_file ".kimi/rules/task-template.md" | head -40)

GIT_LOG=$(git log --oneline -10 2>/dev/null || echo "(нет git истории)")
GIT_STATUS=$(git status --short 2>/dev/null || echo "(нет git)")

# ─── Формирование промпта ─────────────────────────────────────────

PROMPT="Ты — агент \`${ROLE}\` (${ROLE_NAME}) проекта Promelectron.

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
                      ТВОЯ ЗОНА ОТВЕТСТВЕННОСТИ
══════════════════════════════════════════════════════════════════

${CONTEXT_AGENT}

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

ПЕРЕД НАЧАЛОМ РАБОТЫ:
1. Проанализируй контекст — что уже сделано, что блокирует
2. Найди существующий код, который затрагивается (grep)
3. Если нужно — прочитай конкретные файлы

ПОСЛЕ ВЫПОЛНЕНИЯ:
1. Допиши в \`.agent/SESSION_LOG.md\` кратко: что сделано, файлы, риски
2. Обнови статус задачи в \`.agent/BACKLOG.md\` (если есть)
3. Если новый блокер — добавь в \`.agent/BLOCKERS.md\`
4. Если архитектура изменилась — обнови \`PROJECT_CONTEXT.md\`

Начинай работу."

# ─── Вывод / Копирование ──────────────────────────────────────────

echo "══════════════════════════════════════════════════════════════════"
echo "  Agent Router — Задача распознана"
echo "══════════════════════════════════════════════════════════════════"
echo ""
echo "🎯 Задача: ${TASK}"
echo "🤖 Агент:  ${ROLE} (${ROLE_NAME})"
echo ""
echo "──────────────────────────────────────────────────────────────────"
echo ""

# Пытаемся скопировать в буфер обмена
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
    echo "  1. Открой Kimi CLI"
    echo "  2. Вставь (Ctrl+V / Cmd+V)"
    echo "  3. Нажми Enter — агент начнёт работу"
    echo ""
else
    echo "⚠️  Не удалось скопировать в буфер обмена (установи xclip или wl-copy)"
    echo ""
    echo "Скопируй промпт вручную ниже:"
    echo ""
    echo "══════════════════════════════════════════════════════════════════"
    echo ""
fi

echo "$PROMPT"
