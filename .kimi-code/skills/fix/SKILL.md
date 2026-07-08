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

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule / Языковое правило. Все требования к русскому языку и преамбулы для субагентов живут там.

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

Напиши `$AGENT_DIR/task.md` по шаблону из [Rule: Task Template](../../rules/task-template.md). Укажи `github_issue`, если у бага уже есть issue.

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

## Step 2: Проверка размера контекста (Kimi K2.7-Code)

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Context Size Check перед запуском субагентов.

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

Если `ESTIMATED_TOKENS` >= 150000, читай `$AGENT_DIR/CONTEXT_SUMMARY.md` вместо полной истории.

---

## Step 3: Создание изолированного worktree

Сделай это до того, как любой агент коснётся кода.

```bash
git -C "$PROJECT_ROOT" fetch origin
git -C "$PROJECT_ROOT" worktree add "$WORKTREE" -b "$BRANCH" origin/main
```

Всегда ветвись от `origin/main`. Если worktree уже существует — переиспользуй его. Скопируй gitignored локальные файлы, нужные для сборки (`.env`, `backend/.env`, `frontend/.env`, `.worktreeinclude`).

Можно использовать хелпер:

```bash
python scripts/implement-pipeline.py setup "<bug description>" --flags "<flags>"
python scripts/implement-pipeline.py create-worktree <task-id>
```

---

## Step 4: Воспроизведение и спецификация

### 4.1 Чтение контекста

Прочитай параллельно:
1. `$AGENT_DIR/task.md`
2. `PROJECT_CONTEXT.md`
3. `.agent/BACKLOG.md`
4. `.agent/BLOCKERS.md`
5. `.agent/SESSION_LOG.md`
6. `.kimi-code/skills/<ROLE>/SKILL.md`
7. [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md)
8. [Rule: Golden Path](../../rules/golden-path.md), если баг затрагивает cart, checkout, auth, payment, orders
9. [Rule: Agent Commons](../../rules/agent-commons.md)
10. [Rule: Security](../../rules/security.md), если затрагивает auth/payments/PII

### 4.2 Воспроизведение

Найди баг:
- `git -C "$WORKTREE" log --oneline -20` — что недавно менялось?
- `git -C "$WORKTREE" diff` — есть ли незакоммиченные изменения?
- `grep` по ключевым словам ошибки.

Воспроизведи:
- **Backend:** напиши минимальный тест, который падает из-за бага.
- **Frontend:** опиши шаги воспроизведения или напиши unit-тест.
- **E2E:** запусти конкретный тест: `npx playwright test <spec>`.

Правило: если не можешь воспроизвести — спроси пользователя о деталях. НЕ чини вслепую.

### 4.3 Написание bug spec

Напиши `$AGENT_DIR/spec.md` с:
- **Task Type:** bugfix
- **Analysis:** гипотеза root cause
- **Reproduction:** шаги/тест, который падает
- **Decision:** выбранный подход к исправлению
- **Components Affected:** backend/frontend/infra
- **Fix Plan:** файлы для изменения
- **Must-haves:** regression test + fix
- **Acceptance Criteria:** тест проходит, golden path OK
- **Out of Scope:** несвязанные изменения

---

## Step 5: Связывание GitHub Issue (перед фиксом)

Как в `/skill:implement` Step 4.5:
- Проверь существующий `github_issue` в `$AGENT_DIR/task.md`.
- Если нет — составь черновик из spec, подтверди через `AskUserQuestion`, затем запусти:
  ```bash
  python scripts/implement-pipeline.py create-issue <task-id> --status in-progress
  ```

---

## Step 6: Исправление причины проблемы

Запусти выбранного developer-субагента через `Agent` с `subagent_type: coder`.

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
8. [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md)
9. [Rule: Agent Commons](../../rules/agent-commons.md)
10. [Rule: Security](../../rules/security.md) — если задача касается auth/payments/PII/uploads

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

## Step 7: Ревью кода (максимум 3 итерации)

Как в `/skill:implement` Step 6. Для security-sensitive багов (auth, payments, orders) добавь `security-reviewer` в партию.

Review findings пишутся в `$AGENT_DIR/review/findings.md` со статусами `OPEN` → `FIXED` (developer) → `VERIFIED` (reviewer).

---

## Step 8: QA-проверка

Запускай QA как в `/skill:implement` Step 7, если задан флаг `--qa` или баг затрагивает критические пользовательские потоки.

---

## Step 9: Создание запроса на слияние

Как в `/skill:implement` Step 8, с веткой `bugfix/<task-id>`.

---

## Step 10: Итоговый отчёт

После всех фаз:

1. Запусти `python scripts/implement-pipeline.py check-context <task-id>`, чтобы зафиксировать итоговый estimated tokens.
2. Обнови `$PROJECT_ROOT/.agent/SESSION_LOG.md`.
3. Обнови `.agent/BACKLOG.md`, если баг был из спринта.
4. Сообщи пользователю:
   - Task ID
   - Путь к worktree: `$WORKTREE`
   - Ветка: `$BRANCH`
   - URL PR (если создан)
   - Root cause
   - Fix
   - Изменённые файлы
   - Результаты тестов
   - Статус ревью
   - Estimated tokens и количество итераций
   - Открытые findings или H-items (если есть)
5. Спроси: **"Влить `$BRANCH` в main?"** — НЕ мержи без явного одобрения.
6. Если merge выполнен, переведи связанный GitHub Issue в **Done**:
   ```bash
   python scripts/implement-pipeline.py set-status <task-id> done
   ```

---

## Anti-patterns

- ❌ Чинить симптом вместо причины.
- ❌ Удалять падающий тест вместо исправления кода.
- ❌ Добавлять print/console.log для отладки.
- ❌ Игнорировать flaky test.
- ❌ Коммитить без одобрения пользователя.
- ❌ Пропускать code review для security-sensitive багов.

---
