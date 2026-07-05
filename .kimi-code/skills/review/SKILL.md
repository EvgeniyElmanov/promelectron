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

> **ЯЗЫК / LANGUAGE:** Пользователь общается на русском. Все ответы пользователю и артефакты (findings, reports, SESSION_LOG) пиши на русском. Стремись рассуждать на русском, но если reasoning уходит на английский — это не ошибка; главное, чтобы финальные ответы и артефакты были на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Проверь текущие изменения. НЕ редактируй код — только пиши findings.

Фактическая логика ревью живёт в `.kimi-code/skills/code-reviewer/SKILL.md`.

## Language / Язык

Следуй [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule / Языковое правило. При русскоязычном пользователе пиши findings и reports на русском.

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

## Step 1: Проверка размера контекста (Kimi K2.7-Code)

Следуй [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Context Size Check.

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

Если `ESTIMATED_TOKENS` >= 150000, читай `$AGENT_DIR/CONTEXT_SUMMARY.md` вместо полной истории.

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

## Step 3: Determine review scope

Based on changed files:

- **Backend only** → run one `code-reviewer` subagent.
- **Frontend only** → run one `code-reviewer` subagent.
- **Mixed (backend + frontend)** → run two `code-reviewer` subagents in parallel via `AgentSwarm` with `focus: backend` / `focus: frontend`, then merge findings.
- **Security-sensitive work** (auth, payments, orders, uploads) or `--security-only` → add `security-reviewer` to the parallel batch.

`--quick` flag: skip research/extensive checks, focus on obvious bugs and regressions.

---

## Step 4: Launch reviewer subagent(s)

### Single-component review

Launch one `code-reviewer` subagent via `Agent` tool with `subagent_type: coder`.

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Ключевые инструкции этой задачи — на русском. Ты — code-reviewer для Promelectron. Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. При multi-step tool calling сохраняй `reasoning_content` из ассистентских сообщений в истории. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Important: Kimi K2.7-Code uses mandatory thinking mode (`thinking={"type":"enabled"}`), with fixed `temperature=1.0`, `top_p=0.95`, `n=1`, `presence_penalty=0.0`, `frequency_penalty=0.0`. `tool_choice` may only be `"auto"` or `"none"`.

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md (если есть)
2. $AGENT_DIR/spec.md (если есть)
3. `.kimi-code/skills/code-reviewer/SKILL.md`
4. [Rule: Security](.kimi-code/rules/security.md)
5. [Rule: Agent Commons](.kimi-code/rules/agent-commons.md)

Затем:
1. Прочитай реализацию в $WORKTREE (используй Read/Grep/Glob параллельно).
2. Получи diff: git -C "$WORKTREE" --no-pager diff --no-color origin/main...HEAD
3. Сравни со спецификацией и Decisions (D-01, D-02, ...), если spec есть.
4. Проверь: логику, безопасность, архитектуру, бизнес-правила, тесты, влияние на golden path.
5. Запиши findings в $AGENT_DIR/review/findings.md в формате:

# Code Review: <task-id>
- **Status:** FIXES_NEEDED | APPROVED
- **Iteration:** <N>

## Findings
### [F001] ❌ CRITICAL | <Category>
- **File:** path/to/file.py:42
- **Problem:** ...
- **Fix:** ...
- **Status:** OPEN

## Human Decisions (if any)
### [H001] ...

Do NOT edit source code. Only write findings.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

### Mixed review (backend + frontend in parallel)

Use `AgentSwarm` with `subagent_type: coder`.

Prompt template:

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Ключевые инструкции этой задачи — на русском. Ты — code-reviewer для Promelectron (фокус: {{item}}). Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. При multi-step tool calling сохраняй `reasoning_content` из ассистентских сообщений в истории. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Important: Kimi K2.7-Code uses mandatory thinking mode (`thinking={"type":"enabled"}`), with fixed `temperature=1.0`, `top_p=0.95`, `n=1`, `presence_penalty=0.0`, `frequency_penalty=0.0`. `tool_choice` may only be `"auto"` or `"none"`.

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md (если есть)
2. $AGENT_DIR/spec.md (если есть)
3. `.kimi-code/skills/code-reviewer/SKILL.md`
4. [Rule: Security](.kimi-code/rules/security.md)
5. [Rule: Agent Commons](.kimi-code/rules/agent-commons.md)

Затем:
1. Читай только {{item}}-файлы реализации в $WORKTREE (используй Read/Grep/Glob параллельно).
2. Получи diff: git -C "$WORKTREE" --no-pager diff --no-color origin/main...HEAD
3. Сравни со спецификацией и Decisions (D-01, D-02, ...), если spec есть.
4. Проверь: логику, безопасность, архитектуру, бизнес-правила, тесты, влияние на golden path для {{item}}.
5. Запиши findings в $AGENT_DIR/review/findings-{{item}}.md в формате:

# Code Review: <task-id> ({{item}})
- **Status:** FIXES_NEEDED | APPROVED
- **Iteration:** <N>
- **Scope:** {{item}}

## Findings
### [F001] ❌ CRITICAL | <Category>
- **File:** path/to/file.py:42
- **Problem:** ...
- **Fix:** ...
- **Status:** OPEN

## Human Decisions (if any)
### [H001] ...

Do NOT edit source code. Only write findings.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

items: `["backend", "frontend"]`

**After `AgentSwarm` returns:**
1. Read `$AGENT_DIR/review/findings-backend.md` and `$AGENT_DIR/review/findings-frontend.md`.
2. Merge them into `$AGENT_DIR/review/findings.md`:
   - Overall **Status** is `FIXES_NEEDED` if any sub-report is `FIXES_NEEDED`; otherwise `APPROVED`.
   - Preserve **Iteration** number.
   - Combine findings lists; renumber if needed so IDs are unique.
   - Preserve Human Decisions from both reports.
3. Delete the temporary `findings-backend.md` and `findings-frontend.md` or keep them for debugging.

---

## Step 5: Report

Read `$AGENT_DIR/review/findings.md` and report to the user:
- Status: APPROVED | FIXES_NEEDED
- Number of issues by severity
- File paths with findings
- Open Human Decisions (if any)

---

## Rules

- NEVER edit source code.
- NEVER mark findings VERIFIED — only the reviewer does after re-checking a developer's fix.
- Delegate the actual review logic to `code-reviewer`.
- Always ensure `$AGENT_DIR/review` exists before launching subagents.

---
