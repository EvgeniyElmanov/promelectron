#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Agent System Audit — Promelectron
# Проверка целостности системы агентов
# Запуск: ./scripts/audit-agents.sh
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

ERRORS=0
WARNINGS=0

error() {
    echo "  ❌ $1"
    ((ERRORS++)) || true
}

warn() {
    echo "  ⚠️  $1"
    ((WARNINGS++)) || true
}

ok() {
    echo "  ✅ $1"
}

echo "══════════════════════════════════════════════════════════════════"
echo "  Agent System Audit — Promelectron"
echo "══════════════════════════════════════════════════════════════════"
echo ""

# ─── 1. Обязательные файлы ────────────────────────────────────────

echo "📁 Проверка обязательных файлов..."

required_files=(
    "PROJECT_CONTEXT.md"
    "SESSION_START.md"
    "ROUTER.md"
    ".agent/BACKLOG.md"
    ".agent/BLOCKERS.md"
    ".agent/SESSION_LOG.md"
    ".agent/PLANNING_HANDOFF.md"
    ".agent/DISPATCHER_PROMPT.md"
    ".agent/ORCHESTRATOR_PROMPT.md"
    ".kimi/AGENTS.md"
    ".kimi/settings.json"
    "Makefile"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        ok "$file"
    else
        error "$file — НЕ НАЙДЕН"
    fi
done

# ─── 2. Устаревшие файлы (не должны существовать) ─────────────────

echo ""
echo "🗑️  Проверка устаревших файлов..."

obsolete_files=(
    ".agent/AGENTS.md"
    ".agent/CONTEXT.md"
    ".kimi/agents/qa.md"
)

for file in "${obsolete_files[@]}"; do
    if [ -f "$file" ]; then
        error "$file — УСТАРЕЛ, нужно удалить"
    else
        ok "$file — удалён"
    fi
done

# ─── 3. Broken links в агентах ────────────────────────────────────

echo ""
echo "🔗 Проверка broken links в агентах..."

for f in .kimi/agents/*.md; do
    agent=$(basename "$f")
    # Ищем ссылки на .agent/... .kimi/... review/... без backticks
    links=$(grep -oP '(?<!`)\.(agent|kimi)/[^ ]+\.md(?!`)' "$f" 2>/dev/null || true)
    if [ -n "$links" ]; then
        echo "$links" | while read -r link; do
            if [ ! -f "$link" ]; then
                echo "  ❌ $agent → $link (НЕ НАЙДЕН)"
            fi
        done
    fi
done

# Проверяем review/ папку
if [ -d "review" ]; then
    warn "review/ — папка существует, но агенты больше не должны на неё ссылаться"
else
    ok "review/ — не существует (OK)"
fi

# ─── 4. Skills consistency ────────────────────────────────────────

echo ""
echo "🎯 Проверка skills..."

existing_skills=$(ls -d .kimi/skills/*/ 2>/dev/null | sed 's|/$||' | xargs -n1 basename | sort | tr '\n' ' ')
ok "Skills: $existing_skills"

# ─── 5a. Проверка orchestrator ────────────────────────────────────

echo ""
echo "🤖 Проверка orchestrator..."

if [ -f ".kimi/agents/orchestrator.md" ]; then
    ok "orchestrator.md существует"
else
    warn "orchestrator.md не найден"
fi

if [ -f "scripts/kimi-auto.sh" ]; then
    if [ -x "scripts/kimi-auto.sh" ]; then
        ok "scripts/kimi-auto.sh executable"
    else
        warn "scripts/kimi-auto.sh не executable"
    fi
else
    warn "scripts/kimi-auto.sh не найден"
fi

if grep -q "^auto:" Makefile 2>/dev/null; then
    ok "Makefile target 'auto' существует"
else
    warn "Makefile target 'auto' не найден"
fi

# ─── 5. Rules consistency ─────────────────────────────────────────

echo ""
echo "📋 Проверка rules..."

existing_rules=$(ls .kimi/rules/*.md 2>/dev/null | xargs -n1 basename | sort | tr '\n' ' ')
ok "Rules: $existing_rules"

# ─── 6. Консистентность дат ───────────────────────────────────────

echo ""
echo "📅 Проверка консистентности дат..."

backlog_date=$(head -5 .agent/BACKLOG.md | grep -oP '\d{4}-\d{2}-\d{2}' | head -1)
blockers_date=$(head -5 .agent/BLOCKERS.md | grep -oP '\d{4}-\d{2}-\d{2}' | head -1)
log_date=$(grep -oP '\d{4}-\d{2}-\d{2}' .agent/SESSION_LOG.md | head -1)
today=$(date +%Y-%m-%d)

if [ "$backlog_date" = "$today" ] || [ "$blockers_date" = "$today" ] || [ "$log_date" = "$today" ]; then
    ok "Даты актуальны (сегодня $today)"
else
    warn "BACKLOG.md: $backlog_date, BLOCKERS.md: $blockers_date, SESSION_LOG.md: $log_date — возможно устарели"
fi

# ─── 7. YAML frontmatter в PROJECT_CONTEXT.md ─────────────────────

echo ""
echo "📊 Проверка PROJECT_CONTEXT.md..."

if head -1 PROJECT_CONTEXT.md | grep -q '^---$'; then
    ok "YAML frontmatter присутствует"
    
    # Проверяем ключевые поля
    for key in sprint last_update backend_tests frontend_tests e2e_tests; do
        if grep -q "^${key}:" PROJECT_CONTEXT.md; then
            ok "frontmatter.$key"
        else
            warn "frontmatter.$key отсутствует"
        fi
    done
else
    error "YAML frontmatter ОТСУТСТВУЕТ в PROJECT_CONTEXT.md"
fi

# Проверяем, что нет дублирования дат
if grep -q "^\*\*Последнее обновление:\*\*" PROJECT_CONTEXT.md; then
    warn "Дублирование даты в markdown (есть в YAML frontmatter)"
else
    ok "Дублирование дат отсутствует"
fi

# ─── 8. Git hooks ─────────────────────────────────────────────────

echo ""
echo "🪝 Проверка git hooks..."

if [ -f ".git/hooks/pre-push" ]; then
    if [ -x ".git/hooks/pre-push" ]; then
        ok "pre-push hook существует и executable"
    else
        warn "pre-push hook не executable (chmod +x)"
    fi
else
    warn "pre-push hook ОТСУТСТВУЕТ"
fi

# ─── 9. Makefile targets ──────────────────────────────────────────

echo ""
echo "🔨 Проверка Makefile targets..."

required_targets=("dev" "test" "lint" "task" "task-compact" "ask" "agent-context" "agent-status")
for target in "${required_targets[@]}"; do
    if grep -q "^${target}:" Makefile; then
        ok "make $target"
    else
        error "make $target — ОТСУТСТВУЕТ"
    fi
done

# ─── 10. SESSION_START.md ─────────────────────────────────────────

echo ""
echo "🚀 Проверка SESSION_START.md..."

if grep -q "DISPATCHER_PROMPT.md" SESSION_START.md; then
    ok "Диспетчер (DISPATCHER_PROMPT.md) присутствует в SESSION_START.md"
else
    error "Диспетчер ОТСУТСТВУЕТ в SESSION_START.md"
fi

if grep -q "Замени \`<ROLE>\`" SESSION_START.md; then
    error "Устаревшая инструкция '<ROLE>' всё ещё присутствует"
else
    ok "Устаревшая инструкция '<ROLE>' удалена"
fi

# ─── Итог ─────────────────────────────────────────────────────────

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "  РЕЗУЛЬТАТ"
echo "══════════════════════════════════════════════════════════════════"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "  🎉 Система агентов в порядке!"
elif [ $ERRORS -eq 0 ]; then
    echo "  ⚠️  Предупреждений: $WARNINGS"
    echo "     Ошибок: $ERRORS"
    echo "     Система работает, но есть нюансы."
else
    echo "  ❌ Ошибок: $ERRORS"
    echo "  ⚠️  Предупреждений: $WARNINGS"
    echo "     Нужно исправить ошибки!"
fi

echo ""
exit $ERRORS
