---
name: review
description: >
  Code review workflow for Promelectron. Gathers the diff, determines the task context,
  and delegates the actual review to the `code-reviewer` role skill (and optionally `security-reviewer`).
  Use when the user asks for a code review, audit, findings, quality check,
  or asks "check this code".
type: prompt
whenToUse: When the user asks for a code review, audit, findings, quality check, or asks "check this code".
arguments: "[--security-only] [--quick] [<files>]"
disableModelInvocation: false
---

# /skill:review — Рабочий процесс Code Review

> **ЯЗЫК / LANGUAGE:** Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule / Языковое правило.

Проверь текущие изменения. НЕ редактируй код — только пиши findings.

Фактическая логика ревью живёт в `.kimi-code/skills/code-reviewer/SKILL.md`.

## Language / Язык

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule / Языковое правило. При русскоязычном пользователе пиши findings и reports на русском.

---

## Step 0: Определение контекста

Запиши корень репозитория:

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
```

### 0.1 Определение task-id

Если текущая директория внутри `.agent/runs/<task-id>/`:
- Извлеки `task-id` из пути.
- Установи `AGENT_DIR="$PROJECT_ROOT/.agent/runs/<task-id>"`.
- Установи `WORKTREE="$PROJECT_ROOT/.worktrees/<task-id>"`.
- Прочитай `$AGENT_DIR/task.md` и `$AGENT_DIR/spec.md`, если они есть.

Иначе:
- Сгенерируй короткий `task-id` из сводки diff или спроси пользователя.
- Создай `$PROJECT_ROOT/.agent/runs/<task-id>/review`.
- Установи `WORKTREE` в текущую рабочую директорию (или `$PROJECT_ROOT`, если не в worktree).

### 0.2 Убедись, что директория review существует

```bash
mkdir -p "$AGENT_DIR/review"
```

---

## Step 1: Проверка размера контекста (Kimi K3)

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Context Size Check.

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

Если `ESTIMATED_TOKENS` >= 600000, читай `$AGENT_DIR/CONTEXT_SUMMARY.md` вместо полной истории.

---

## Step 2: Получение diff

```bash
git -C "$WORKTREE" --no-pager diff --no-color origin/main...HEAD
```

Если diff пустой — остановись и сообщи: *"Нет изменений для ревью."*

Если указаны файлы:

```bash
git -C "$WORKTREE" --no-pager diff --no-color origin/main...HEAD -- <files>
```

---

## Step 3: Определение scope ревью

На основе изменённых файлов:

- **Только backend** → запусти одного `code-reviewer` субагента.
- **Только frontend** → запусти одного `code-reviewer` субагента.
- **Смешанный (backend + frontend)** → запусти двух `code-reviewer` субагентов параллельно через `AgentSwarm` с `focus: backend` / `focus: frontend`, затем смержи findings.
- **Security-sensitive работа** (auth, payments, orders, uploads) или `--security-only` → добавь `security-reviewer` в параллельную партию.

Флаг `--quick`: пропустить research/расширенные проверки, сфокусироваться на очевидных багах и регрессиях.

---

## Step 4: Запуск reviewer-субагента(ов)

### Single-component review

Запусти одного `code-reviewer` субагента через инструмент `Agent` с `subagent_type: coder`.

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

Ты — code-reviewer для Promelectron.

Контекст:
- task-id: <task-id>
- AGENT_DIR: $AGENT_DIR
- WORKTREE: $WORKTREE
- scope: all
- output: $AGENT_DIR/review/findings.md
- iteration: 1

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md (если есть)
2. $AGENT_DIR/spec.md (если есть)
3. `.kimi-code/skills/code-reviewer/SKILL.md`
4. [Rule: Security](../../rules/security.md)
5. [Rule: Agent Commons](../../rules/agent-commons.md)

Затем следуй workflow из `.kimi-code/skills/code-reviewer/SKILL.md` строго. Запиши findings в $AGENT_DIR/review/findings.md.

Do NOT edit source code. Only write findings.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

### Смешанное ревью (backend + frontend параллельно)

Используй `AgentSwarm` с `subagent_type: coder`.

items: `["backend", "frontend"]`

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

Ты — code-reviewer для Promelectron.

Контекст:
- task-id: <task-id>
- AGENT_DIR: $AGENT_DIR
- WORKTREE: $WORKTREE
- scope: {{item}}
- output: $AGENT_DIR/review/findings-{{item}}.md
- iteration: 1

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md (если есть)
2. $AGENT_DIR/spec.md (если есть)
3. `.kimi-code/skills/code-reviewer/SKILL.md`
4. [Rule: Security](../../rules/security.md)
5. [Rule: Agent Commons](../../rules/agent-commons.md)

Затем следуй workflow из `.kimi-code/skills/code-reviewer/SKILL.md` строго. Запиши findings в $AGENT_DIR/review/findings-{{item}}.md.

Do NOT edit source code. Only write findings.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

**После возврата `AgentSwarm`:**
1. Прочитай `$AGENT_DIR/review/findings-backend.md` и `$AGENT_DIR/review/findings-frontend.md`.
2. Смержи их в `$AGENT_DIR/review/findings.md`:
   - Общий **Status** — `FIXES_NEEDED`, если хотя бы один sub-report `FIXES_NEEDED`; иначе `APPROVED`.
   - Сохрани номер **Iteration**.
   - Объедини списки findings; при необходимости перенумеруй, чтобы ID были уникальными.
   - Сохрани Human Decisions из обоих отчётов.
3. Удали временные `findings-backend.md` и `findings-frontend.md` или оставь для отладки.

---

## Step 5: Отчёт

Прочитай `$AGENT_DIR/review/findings.md` и отчитайся пользователю:
- Status: APPROVED | FIXES_NEEDED
- Количество проблем по severity
- Пути файлов с findings
- Открытые Human Decisions (если есть)

Запиши trace-событие вердикта (формат — как в `/skill:implement` Step 1d; trace никогда не блокирует пайплайн: при ошибке — продолжай и упомяни в отчёте):

```bash
python3 scripts/agent_state.py trace <task-id> review_verdict --actor code-reviewer --data '{"iteration": N, "verdict": "APPROVED|FIXES_NEEDED"}'
```

---

## Правила

- NEVER редактировать исходный код.
- NEVER отмечать findings как VERIFIED — только reviewer делает это после повторной проверки исправления разработчика.
- Делегировать фактическую логику ревью `code-reviewer`.
- Всегда убедись, что `$AGENT_DIR/review` существует перед запуском субагентов.

---
