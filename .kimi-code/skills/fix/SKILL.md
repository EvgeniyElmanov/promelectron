---
name: fix
description: >
  Bug fix workflow for Promelectron. Use when the user reports a bug, error, crash, exception, test failure, or broken functionality
  in backend, frontend, or infrastructure. Creates an isolated worktree, analyzes the bug, determines the correct role,
  reproduces with a minimal test, fixes the root cause (not symptoms), runs code review, tests, and reports results.
type: prompt
whenToUse: When the user reports a bug, crash, failing test, regression, or anything that "does not work". Also triggers on words like fix, bug, broken, error, exception, fail, failing, regression.
arguments: "<bug description> [--backend] [--frontend] [--infra] [--e2e]"
disableModelInvocation: false
---

# /skill:fix — Рабочий процесс исправления багов

> **ЯЗЫК / LANGUAGE:** Пользователь общается на русском. Все ответы пользователю, отчёты и артефакты (task.md, spec.md, findings, test-findings, SESSION_LOG) пиши на русском. Стремись рассуждать на русском, но если reasoning уходит на английский — это не ошибка; главное, чтобы финальные ответы и артефакты были на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Исправь баг системно: анализ → воспроизведение → исправление → ревью → тесты → верификация.

## Language / Язык

Следуй [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule / Языковое правило. Все требования к русскому языку и преамбулы для субагентов живут там.

При русскоязычном пользователе пиши `task.md`, `spec.md`, findings, reports и записи `SESSION_LOG.md` на русском.

---

## Step 0: Подготовка — координационная плоскость и worktree

Запиши корень репозитория:

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
```

### 0.1 Предварительные проверки

Проверь доступ к GitHub CLI перед началом:

```bash
gh auth status
gh project view 1 --owner AutonomaCo
```

Если что-то не так — остановись и попроси пользователя выполнить `gh auth login` или выдать scope `project`.

Сгенерируй `<task-id>`: короткий slug в kebab-case с префиксом `bugfix-`, например `bugfix-cart-stock-race`, `bugfix-login-redirect`.

Создай временную координационную плоскость и корень worktree:

```bash
mkdir -p "$PROJECT_ROOT/.agent/runs/<task-id>/review"
mkdir -p "$PROJECT_ROOT/.worktrees"
```

Пути для остального пайплайна:

```text
AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>       (gitignored coordination plane)
WORKTREE  = $PROJECT_ROOT/.worktrees/<task-id>        (per-task code checkout)
BRANCH    = bugfix/<task-id>
```

Напиши `$AGENT_DIR/task.md` по шаблону из [Rule: Task Template](.kimi-code/rules/task-template.md). Укажи `github_issue`, если у бага уже есть issue.

---

## Step 1: Анализ и маршрутизация

Определи роль по типу бага (можно переопределить флагами `--backend`, `--frontend`, `--infra`, `--e2e`):

| Тип бага | Роль |
|----------|------|
| Ошибка API, 500, БД, миграция, race condition | `backend-dev` |
| Сломан UI, CSS, router, форма, frontend-валидация | `frontend-dev` |
| Docker, Helm, CI/CD, деплой, секреты, nginx | `devops` |
| Падает Playwright, отсутствует селектор | `e2e-tester` |

Если не уверен — спроси пользователя.

---

## Step 2: Context Size Check (Kimi K2.7-Code)

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Context Size Check before launching subagents.

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

If `ESTIMATED_TOKENS` >= 150000, read `$AGENT_DIR/CONTEXT_SUMMARY.md` instead of the full history.

---

## Step 3: Create the isolated worktree

Do this before any agent touches code.

```bash
git -C "$PROJECT_ROOT" fetch origin
git -C "$PROJECT_ROOT" worktree add "$WORKTREE" -b "$BRANCH" origin/main
```

Always branch from `origin/main`. If the worktree already exists, reuse it. Copy gitignored local files the build needs (`.env`, `backend/.env`, `frontend/.env`, `.worktreeinclude`).

Or use the helper:

```bash
python scripts/implement-pipeline.py setup "<bug description>" --flags "<flags>"
python scripts/implement-pipeline.py create-worktree <task-id>
```

---

## Step 4: Reproduce and Spec

### 4.1 Read context

Read in parallel:
1. `$AGENT_DIR/task.md`
2. `PROJECT_CONTEXT.md`
3. `.agent/BACKLOG.md`
4. `.agent/BLOCKERS.md`
5. `.agent/SESSION_LOG.md`
6. `.kimi-code/skills/<ROLE>/SKILL.md`
7. [Rule: Pre-edit Checklist](.kimi-code/rules/pre-edit-checklist.md)
8. [Rule: Golden Path](.kimi-code/rules/golden-path.md) if the bug touches cart, checkout, auth, payment, orders
9. [Rule: Agent Commons](.kimi-code/rules/agent-commons.md)
10. [Rule: Security](.kimi-code/rules/security.md) if auth/payments/PII affected

### 4.2 Reproduce

Find the bug:
- `git -C "$WORKTREE" log --oneline -20` — what changed recently?
- `git -C "$WORKTREE" diff` — any uncommitted changes?
- `grep` for error keywords.

Reproduce:
- **Backend:** write a minimal test that fails because of the bug.
- **Frontend:** describe reproduction steps or write a unit test.
- **E2E:** run the specific test: `npx playwright test <spec>`.

Rule: if you cannot reproduce, ask the user for details. Do NOT fix blindly.

### 4.3 Write bug spec

Write `$AGENT_DIR/spec.md` with:
- **Task Type:** bugfix
- **Analysis:** root cause hypothesis
- **Reproduction:** steps/test that fails
- **Decision:** chosen fix approach
- **Components Affected:** backend/frontend/infra
- **Fix Plan:** files to change
- **Must-haves:** regression test + fix
- **Acceptance Criteria:** test passes, golden path OK
- **Out of Scope:** unrelated changes

---

## Step 5: Link GitHub Issue (before fix)

Same as `/skill:implement` Step 4.5:
- Check existing `github_issue` in `$AGENT_DIR/task.md`.
- If none, build draft from spec, confirm via `AskUserQuestion`, then run:
  ```bash
  python scripts/implement-pipeline.py create-issue <task-id> --status in-progress
  ```

---

## Step 6: Fix Root Cause

Launch the selected developer subagent via `Agent` with `subagent_type: coder`.

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Ключевые инструкции этой задачи — на русском. Ты — <ROLE> для Promelectron. Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. При multi-step tool calling сохраняй `reasoning_content` из ассистентских сообщений в истории. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Important: Kimi K2.7-Code uses mandatory thinking mode (`thinking={"type":"enabled"}`), with fixed `temperature=1.0`, `top_p=0.95`, `n=1`, `presence_penalty=0.0`, `frequency_penalty=0.0`. `tool_choice` may only be `"auto"` or `"none"`.

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. PROJECT_CONTEXT.md
4. .agent/BACKLOG.md
5. .agent/BLOCKERS.md
6. .agent/SESSION_LOG.md
7. `.kimi-code/skills/<ROLE>/SKILL.md`
8. [Rule: Pre-edit Checklist](.kimi-code/rules/pre-edit-checklist.md)
9. [Rule: Agent Commons](.kimi-code/rules/agent-commons.md)
10. [Rule: Security](.kimi-code/rules/security.md) — если задача касается auth/payments/PII/uploads

Setup:
1. Работай ТОЛЬКО внутри $WORKTREE (ветка $BRANCH).
2. Используй явные пути: git -C "$WORKTREE" ..., make -C "$WORKTREE" ..., Read/Edit/Write файлов под $WORKTREE.

Задача: исправить root cause бага, а не симптом.

Rules:
- Do NOT wrap everything in try/except.
- If you change a model → create an Alembic migration.
- If you change an API contract → update the frontend API layer.
- Use trailing slash in FastAPI endpoints.
- Do NOT commit to main. You may commit to $BRANCH in the worktree.

Before finishing:
1. Write/update a regression test that would have failed before the fix and passes now.
2. Run the role-specific tests in $WORKTREE: make -C "$WORKTREE" test-backend или make -C "$WORKTREE" test-frontend.
3. Run lint: make -C "$WORKTREE" lint-backend / make -C "$WORKTREE" lint-frontend.
4. If golden path affected → verify the corresponding scenario.
5. Update $PROJECT_ROOT/.agent/SESSION_LOG.md.

Report:
- Root cause
- Fix
- Changed files
- Test results
- Any blockers

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

---

## Step 7: Code Review (max 3 iterations)

Same as `/skill:implement` Step 6. For security-sensitive bugs (auth, payments, orders), add `security-reviewer` to the batch.

Review findings go to `$AGENT_DIR/review/findings.md` with statuses `OPEN` → `FIXED` (developer) → `VERIFIED` (reviewer).

---

## Step 8: QA Gate

Run QA same as `/skill:implement` Step 7 if `--qa` flag is set or the bug touches critical user flows.

---

## Step 9: Create Pull Request

Same as `/skill:implement` Step 8, with branch `bugfix/<task-id>`.

---

## Step 10: Final Report

After all phases:

1. Run `python scripts/implement-pipeline.py check-context <task-id>` to capture final estimated tokens.
2. Update `$PROJECT_ROOT/.agent/SESSION_LOG.md`.
3. Update `.agent/BACKLOG.md` if the bug was from the sprint.
4. Report to the user:
   - Task ID
   - Worktree path: `$WORKTREE`
   - Branch: `$BRANCH`
   - PR URL (if created)
   - Root cause
   - Fix
   - Changed files
   - Test results
   - Review status
   - Estimated tokens and iteration count
   - Open findings or H-items (if any)
5. Ask: **"Merge `$BRANCH` into main?"** (do NOT merge without explicit approval).
6. If merged, move the linked GitHub Issue to **Done**:
   ```bash
   python scripts/implement-pipeline.py set-status <task-id> done
   ```

---

## Anti-Patterns

- ❌ Fix the symptom instead of the cause.
- ❌ Remove a failing test instead of fixing the code.
- ❌ Add print/console.log for debugging.
- ❌ Ignore a flaky test.
- ❌ Commit without user approval.
- ❌ Skip code review for security-sensitive bugs.

---
