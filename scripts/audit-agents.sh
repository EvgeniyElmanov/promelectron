#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Agent System Audit — Promelectron
# Проверка целостности системы агентов после миграции в .kimi-code/
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
    "AGENTS.md"
    ".agent/BACKLOG.md"
    ".agent/BLOCKERS.md"
    ".agent/SESSION_LOG.md"
    ".agent/PLANNING_HANDOFF.md"
    ".kimi-code/mcp.json"
    ".kimi-code/config.example.toml"
    ".kimi-code/skills/promelectron/SKILL.md"
    ".kimi-code/skills/implement/SKILL.md"
    ".kimi-code/skills/fix/SKILL.md"
    ".kimi-code/skills/review/SKILL.md"
    ".kimi-code/skills/deploy/SKILL.md"
    ".kimi-code/skills/context-sync/SKILL.md"
    ".kimi-code/skills/plan-maintainer/SKILL.md"
    ".kimi/agents/dispatcher.md"
    ".kimi/agents/architect.md"
    ".kimi/agents/backend-dev.md"
    ".kimi/agents/frontend-dev.md"
    ".kimi/agents/code-reviewer.md"
    ".kimi/agents/security-reviewer.md"
    ".kimi/agents/e2e-tester.md"
    ".kimi/agents/qa.md"
    ".kimi/agents/devops.md"
    ".kimi/agents/project-manager.md"
    ".kimi/agents/integration-dev.md"
    ".kimi/rules/pre-edit-checklist.md"
    ".kimi/rules/golden-path.md"
    ".kimi/rules/dependency-map.md"
    ".kimi/rules/security.md"
    "scripts/implement-pipeline.py"
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
    ".agent/CURSOR_RULES.md"
    ".agent/START_HERE.md"
    ".agent/DISPATCHER_PROMPT.md"
    ".agent/ORCHESTRATOR_PROMPT.md"
    ".kimi/AGENTS.md"
    ".kimi/CLAUDE.md"
    ".kimi/tester.md"
    ".kimi/settings.json"
    ".kimi/agents/orchestrator.md"
    ".mcp.json"
)

for file in "${obsolete_files[@]}"; do
    if [ -f "$file" ]; then
        error "$file — УСТАРЕЛ, нужно удалить"
    else
        ok "$file — удалён"
    fi
done

if [ -d ".kimi/skills" ]; then
    error ".kimi/skills/ — УСТАРЕЛА, нужно удалить"
else
    ok ".kimi/skills/ — удалена"
fi

# ─── 3. Skills consistency ────────────────────────────────────────

echo ""
echo "🎯 Проверка skills..."

if [ -d ".kimi-code/skills" ]; then
    existing_skills=$(find .kimi-code/skills -maxdepth 1 -mindepth 1 -type d | sort | sed 's|.kimi-code/skills/||' | tr '\n' ' ')
    ok "Skills: $existing_skills"
else
    error ".kimi-code/skills/ — НЕ НАЙДЕНА"
fi

# ─── 4. Консистентность агентов в AGENTS.md ───────────────────────

echo ""
echo "🤖 Проверка реестра агентов..."

for f in .kimi/agents/*.md; do
    agent=$(basename "$f" .md)
    if grep -q "\`$agent\`" AGENTS.md; then
        ok "$agent.md зарегистрирован в AGENTS.md"
    else
        error "$agent.md НЕ зарегистрирован в AGENTS.md"
    fi
done

# ─── 5. Broken links в агентах и skills ───────────────────────────

echo ""
echo "🔗 Проверка broken links в агентах и skills..."

broken_found=0
for f in .kimi/agents/*.md .kimi-code/skills/*/SKILL.md .kimi/rules/*.md; do
    [ -f "$f" ] || continue
    base=$(basename "$f")
    # Ищем markdown-ссылки вида [text](path) и plain-ссылки на .md файлы
    links=$(grep -oP '(?<!`)(\.\/|\.\./)?(?:\.agent|\.kimi|\.kimi-code|backend|frontend|scripts|infra)/[^ )\`]+\.md(?!`)' "$f" 2>/dev/null || true)
    if [ -n "$links" ]; then
        echo "$links" | while read -r link; do
            # Пропускаем шаблонные placeholder'ы вида <task-id>
            if [[ "$link" == *'<'*'>'* ]]; then
                continue
            fi
            # Убираем hash-якори
            clean_link="${link%%#*}"
            if [ ! -f "$clean_link" ]; then
                echo "  ❌ $base → $link (НЕ НАЙДЕН)"
                broken_found=1
            fi
        done
    fi
done

if [ "$broken_found" -eq 0 ]; then
    ok "Broken links не найдены"
else
    error "Найдены broken links (см. выше)"
fi

# ─── 6. YAML frontmatter в агентах ────────────────────────────────

echo ""
echo "📄 Проверка YAML frontmatter в .kimi/agents/*.md..."

for f in .kimi/agents/*.md; do
    agent=$(basename "$f")
    if head -1 "$f" | grep -q '^---$'; then
        error "$agent — содержит legacy YAML frontmatter"
    else
        ok "$agent — чистый markdown"
    fi
done

# ─── 7. Skill frontmatter ─────────────────────────────────────────

echo ""
echo "📄 Проверка frontmatter в .kimi-code/skills/*/SKILL.md..."

for f in .kimi-code/skills/*/SKILL.md; do
    skill=$(basename "$(dirname "$f")")
    if head -5 "$f" | grep -q '^name:' && head -10 "$f" | grep -q '^type: prompt'; then
        ok "$skill/SKILL.md — корректный frontmatter"
    else
        error "$skill/SKILL.md — отсутствует name/type: prompt"
    fi
done

# ─── 8. Makefile targets ──────────────────────────────────────────

echo ""
echo "🔨 Проверка Makefile targets..."

required_targets=("dev" "test" "lint" "agent-context" "agent-status" "agent-audit")
for target in "${required_targets[@]}"; do
    if grep -q "^${target}:" Makefile; then
        ok "make $target"
    else
        error "make $target — ОТСУТСТВУЕТ"
    fi
done

# ─── 9. Legacy Makefile targets и scripts ─────────────────────────

echo ""
echo "🕸️  Проверка legacy Makefile targets и scripts..."

legacy_targets=("task" "ask" "auto" "task-compact")
for target in "${legacy_targets[@]}"; do
    if grep -q "^${target}:" Makefile; then
        error "make $target — legacy target всё ещё существует"
    else
        ok "make $target — удалён"
    fi
done

if [ -f "scripts/kimi.py" ]; then
    error "scripts/kimi.py — legacy script, нужно удалить"
else
    ok "scripts/kimi.py — удалён"
fi

if [ -f ".vscode/tasks.json" ] && grep -q "scripts/kimi.py" .vscode/tasks.json; then
    error ".vscode/tasks.json ссылается на scripts/kimi.py"
else
    ok ".vscode/tasks.json не ссылается на scripts/kimi.py"
fi

# ─── 10. SESSION_START.md и AGENTS.md ─────────────────────────────

echo ""
echo "🚀 Проверка документации..."

if grep -q "/implement" SESSION_START.md; then
    ok "SESSION_START.md содержит /implement"
else
    error "SESSION_START.md НЕ содержит /implement"
fi

if grep -q "/promelectron" SESSION_START.md; then
    ok "SESSION_START.md содержит /promelectron"
else
    error "SESSION_START.md НЕ содержит /promelectron"
fi

if grep -q "\.kimi-code/skills/" AGENTS.md; then
    ok "AGENTS.md ссылается на .kimi-code/skills/"
else
    error "AGENTS.md НЕ ссылается на .kimi-code/skills/"
fi

# ─── 11. .gitignore ───────────────────────────────────────────────

echo ""
echo "🙈 Проверка .gitignore..."

if grep -q '^\.kimi-code/config\.toml$' .gitignore; then
    ok ".gitignore исключает .kimi-code/config.toml"
else
    error ".gitignore НЕ исключает .kimi-code/config.toml"
fi

if grep -q '^\.worktrees/' .gitignore; then
    ok ".gitignore исключает .worktrees/"
else
    error ".gitignore НЕ исключает .worktrees/"
fi

# ─── 12. scripts/implement-pipeline.py ────────────────────────────

echo ""
echo "🐍 Проверка scripts/implement-pipeline.py..."

if python3 -m py_compile scripts/implement-pipeline.py 2>/dev/null; then
    ok "scripts/implement-pipeline.py синтаксически корректен"
else
    error "scripts/implement-pipeline.py имеет синтаксические ошибки"
fi

if cd backend && ruff check ../scripts/implement-pipeline.py 2>/dev/null; then
    ok "ruff check scripts/implement-pipeline.py — чисто"
else
    error "ruff check scripts/implement-pipeline.py — есть ошибки"
fi
cd "$PROJECT_ROOT"

# ─── 13. JSON/TOML валидация ──────────────────────────────────────

echo ""
echo "📋 Проверка JSON/TOML..."

if python3 -m json.tool .kimi-code/mcp.json > /dev/null 2>&1; then
    ok ".kimi-code/mcp.json — валидный JSON"
else
    error ".kimi-code/mcp.json — НЕ валидный JSON"
fi

if python3 -c "import tomllib; tomllib.load(open('.kimi-code/config.example.toml','rb'))" 2>/dev/null; then
    ok ".kimi-code/config.example.toml — валидный TOML"
else
    error ".kimi-code/config.example.toml — НЕ валидный TOML"
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
