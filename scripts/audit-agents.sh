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
    ".kimi-code/AGENTS.md"
    ".kimi-code/BUNDLE.md"
    ".kimi-code/mcp.json"
    ".kimi-code/config.example.toml"
    ".kimi-code/skills/promelectron/SKILL.md"
    ".kimi-code/skills/implement/SKILL.md"
    ".kimi-code/skills/fix/SKILL.md"
    ".kimi-code/skills/review/SKILL.md"
    ".kimi-code/skills/deploy/SKILL.md"
    ".kimi-code/skills/context-sync/SKILL.md"
    ".kimi-code/skills/plan-maintainer/SKILL.md"
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
    ".kimi/"
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

if [ -d ".kimi" ]; then
    error ".kimi/ — УСТАРЕЛА, нужно удалить (содержимое перенесено в .kimi-code/AGENTS.md)"
else
    ok ".kimi/ — удалена"
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

# ─── 4. Консистентность агентов в .kimi-code/AGENTS.md ───────────────────────

echo ""
echo "🤖 Проверка реестра агентов..."

required_agents=(
    "architect"
    "backend-dev"
    "frontend-dev"
    "code-reviewer"
    "security-reviewer"
    "e2e-tester"
    "qa"
    "devops"
    "project-manager"
    "integration-dev"
    "dispatcher"
)

for agent in "${required_agents[@]}"; do
    if grep -qF '| `'$agent'` |' .kimi-code/BUNDLE.md; then
        ok "Role '$agent' найден в .kimi-code/BUNDLE.md"
    else
        error "Role '$agent' НЕ найден в .kimi-code/BUNDLE.md"
    fi
done

# ─── 5. Flat role skills consistency ──────────────────────────────

echo ""
echo "🧩 Проверка flat role skills..."

required_role_skills=(
    "architect"
    "backend-dev"
    "frontend-dev"
    "code-reviewer"
    "security-reviewer"
    "e2e-tester"
    "devops"
    "qa"
    "project-manager"
    "integration-dev"
    "dispatcher"
)

for skill in "${required_role_skills[@]}"; do
    f=".kimi-code/skills/$skill/SKILL.md"
    if [ -f "$f" ]; then
        ok "role skill $skill/SKILL.md"
    else
        error "role skill $skill/SKILL.md — НЕ НАЙДЕН"
    fi
done

required_rules=(
    "agent-commons"
    "pre-edit-checklist"
    "golden-path"
    "dependency-map"
    "security"
    "prompt-format"
    "task-template"
    "planning"
    "known-pitfalls"
)

for rule in "${required_rules[@]}"; do
    f=".kimi-code/rules/$rule.md"
    if [ -f "$f" ]; then
        ok "rule $rule.md"
    else
        error "rule $rule.md — НЕ НАЙДЕН"
    fi
done

# Убедимся, что внутри .kimi-code/skills/promelectron/ нет вложенных skill-директорий
if [ -d ".kimi-code/skills/promelectron" ]; then
    nested_skills=$(find .kimi-code/skills/promelectron -mindepth 2 -name 'SKILL.md' -type f 2>/dev/null || true)
    if [ -n "$nested_skills" ]; then
        error "Найдены вложенные SKILL.md в .kimi-code/skills/promelectron/ — Kimi CLI не загружает их: $nested_skills"
    else
        ok ".kimi-code/skills/promelectron/ — нет вложенных SKILL.md"
    fi
fi

# ─── 6. Broken links в агентах и skills ───────────────────────────

echo ""
echo "🔗 Проверка broken links в агентах и skills..."

broken_found=0
while IFS= read -r -d '' f; do
    base=$(basename "$f")
    dir=$(dirname "$f")
    # Markdown links: [text](path/to/file.md)
    md_links=$(grep -oP '\[.*?\]\(\K[^) ]+\.md(?=\))' "$f" 2>/dev/null || true)
    # Plain links: paths ending in .md inside known roots, parent-relative paths, or root-level .md files.
    # Start-boundary (whitespace, quote, or backtick) prevents matching a suffix of a Markdown link.
    plain_links=$(grep -oP "(?:(?<=^)|(?<=[\\s'\"\\x60]))(?:(?:\\.agent|\\.kimi-code|backend|frontend|scripts|infra)/|/|\\.\\./)[^ )\\x60]+?\\.md" "$f" 2>/dev/null || true)
    links=$(printf '%s\n%s\n' "$md_links" "$plain_links" | sort -u)
    if [ -n "$links" ]; then
        echo "$links" | while read -r link; do
            # Пропускаем пустые строки и шаблонные placeholder'ы
            if [ -z "$link" ] || [[ "$link" == *'<'*'>'* ]] || [[ "$link" == *'XXX'* ]]; then
                continue
            fi
            # Убираем hash-якори
            clean_link="${link%%#*}"
            # Разрешаем относительно директории файла или проектного корня
            if [[ "$clean_link" == /* ]]; then
                resolved="$PROJECT_ROOT$clean_link"
            elif [[ "$clean_link" == ./* ]] || [[ "$clean_link" == ../* ]]; then
                resolved=$(cd "$dir" && realpath -m "$clean_link" 2>/dev/null || echo "$PROJECT_ROOT/$clean_link")
            elif [[ "$clean_link" == *"/"* ]]; then
                resolved="$PROJECT_ROOT/$clean_link"
            else
                # Bare filename — resolve relative to the file's directory
                resolved=$(cd "$dir" && realpath -m "$clean_link" 2>/dev/null || echo "$PROJECT_ROOT/$clean_link")
            fi
            if [ ! -f "$resolved" ]; then
                echo "  ❌ $f → $link (НЕ НАЙДЕН)"
                broken_found=1
            fi
        done
    fi
done < <(find AGENTS.md .kimi-code/AGENTS.md .kimi-code/BUNDLE.md .kimi-code/rules .kimi-code/skills -type f -name '*.md' -print0)

if [ "$broken_found" -eq 0 ]; then
    ok "Broken links не найдены"
else
    error "Найдены broken links (см. выше)"
fi

# ─── 7. Skill frontmatter ─────────────────────────────────────────

echo ""
echo "📄 Проверка frontmatter в SKILL.md..."

while IFS= read -r -d '' f; do
    skill=$(basename "$(dirname "$f")")
    parent=$(basename "$(dirname "$(dirname "$f")")")
    label="$parent/$skill/SKILL.md"
    if head -5 "$f" | grep -q '^name:' && head -10 "$f" | grep -Eq '^type: (prompt|flow)'; then
        ok "$label — корректный frontmatter"
    else
        error "$label — отсутствует name/type: prompt|flow"
    fi
done < <(find .kimi-code/skills -name 'SKILL.md' -type f -print0)

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

if grep -q "/skill:implement" SESSION_START.md; then
    ok "SESSION_START.md содержит /skill:implement"
else
    error "SESSION_START.md НЕ содержит /skill:implement"
fi

if grep -q "/skill:promelectron" SESSION_START.md; then
    ok "SESSION_START.md содержит /skill:promelectron"
else
    error "SESSION_START.md НЕ содержит /skill:promelectron"
fi

if grep -q "\.kimi-code/skills/" AGENTS.md; then
    ok "AGENTS.md ссылается на .kimi-code/skills/"
else
    error "AGENTS.md НЕ ссылается на .kimi-code/skills/"
fi

if grep -q "\.kimi-code/AGENTS.md" AGENTS.md; then
    ok "AGENTS.md ссылается на .kimi-code/AGENTS.md"
else
    error "AGENTS.md НЕ ссылается на .kimi-code/AGENTS.md"
fi

# ─── 11. .gitignore ───────────────────────────────────────────────

echo ""
echo "🙈 Проверка .gitignore..."

if grep -q '^\.kimi-code/config\.toml$' .gitignore; then
    ok ".gitignore исключает .kimi-code/config.toml (user config lives in ~/.kimi-code/config.toml)"
else
    error ".gitignore НЕ исключает .kimi-code/config.toml (user config lives in ~/.kimi-code/config.toml)"
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
