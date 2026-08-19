---
name: fix
description: >
  Bug fix workflow for Promelectron. Use when the user reports a bug, error, crash, exception, test failure, or broken functionality
  in backend, frontend, or infrastructure. Creates an isolated worktree, analyzes the bug, determines the correct role,
  reproduces with a minimal test, fixes the root cause (not symptoms), runs code review, tests, and reports results.
type: prompt
whenToUse: When the user reports a bug, crash, failing test, regression, or anything that "does not work". Also triggers on words like fix, bug, broken, error, exception, fail, failing, regression.
arguments: "<bug description> [--backend] [--frontend] [--infra] [--e2e] [--qa]"
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

Сгенерируй `<task-id>`: короткий slug в kebab-case, например `cart-stock-race`, `login-redirect`.

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

## Step 2: Проверка размера контекста (Kimi K3)

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Context Size Check перед запуском субагентов.

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

Если `ESTIMATED_TOKENS` >= 600000, читай `$AGENT_DIR/CONTEXT_SUMMARY.md` вместо полной истории.

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
10. [Rule: Security](../../rules/security.md) — всегда; lightweight pass для любой задачи, extended для auth/payments/PII/uploads/orders/webhooks

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

## Step 6: Исправление причины проблемы — plan → approve → execute

Запуск developer-субагента разбиваем на планирование и исполнение. Без одобренного плана код не пишем.

### Step 6a: Plan — developer пишет PLAN.md

Запусти выбранного developer-субагента через `Agent` с `subagent_type: coder` с задачей **только написать план**:

```text
=== PHASE A: PLAN ONLY — DO NOT WRITE CODE ===

Перед фиксом напиши $WORKTREE/PLAN.md по task.md/spec.md.

PLAN.md должен содержать:
1. Root cause — в чём причина бага (с цитатой из diff или теста).
2. Steps — как исправлять: какие файлы, минимальные изменения, проверка после каждого шага.
3. Regression test — какой тест добавить/обновить, чтобы баг не повторился.
4. Risks / Rollback — что может сломаться и как откатить.

Не редактируй production-код. После написания PLAN.md остановись и сообщи: «PLAN.md готов».
```

### Step 6b: Approve

Оцени план по критериям auto-approve. Auto-одобряется, если **все** условия выполнены:

1. Фикс укладывается в ≤3 файла.
2. Изменения не касаются auth / payments / PII / orders / webhooks.
3. Не требуется изменение API contract.
4. Regression test описан явно.

Если все условия выполнены — trace `plan_auto_approved` и иди к Step 6c.

Если нет — покажи PLAN.md пользователю и спроси: **«одобрить план / доработать?»**. Доработка → верни в Step 6a (trace `plan_revised`). Одобрение → trace `plan_human_approved` и иди к Step 6c.

### Step 6c: Execute — реализация по одобренному плану

Запусти того же developer-субагента с задачей **реализовать одобренный PLAN.md**:

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

Ты — <ROLE> для Promelectron.

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. $WORKTREE/PLAN.md — одобренный план, реализуй строго по нему
4. PROJECT_CONTEXT.md
5. .agent/BACKLOG.md
6. .agent/BLOCKERS.md
7. .agent/SESSION_LOG.md
8. `.kimi-code/skills/<ROLE>/SKILL.md`
9. [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md)
10. [Rule: Agent Commons](../../rules/agent-commons.md)
11. [Rule: Security](../../rules/security.md) — всегда; lightweight pass для любой задачи, extended для auth/payments/PII/uploads/orders/webhooks

Setup:
1. Работай ТОЛЬКО внутри $WORKTREE (ветка $BRANCH).
2. Используй явные пути: git -C "$WORKTREE" ..., make -C "$WORKTREE" ..., Read/Edit/Write файлов под $WORKTREE.

Задача: исправить root cause бага, а не симптом, строго по одобренному PLAN.md.

Rules:
- Do NOT wrap everything in try/except.
- If you change a model → create an Alembic migration.
- If you change an API contract → update the frontend API layer.
- Use trailing slash in FastAPI endpoints.
- Do NOT commit to main. You may commit to $BRANCH in the worktree.
- If PLAN.md becomes unworkable mid-flight: stop, revise PLAN.md with orchestrator, get re-approval.

Before finishing:
1. Write/update a regression test that would have failed before the fix and passes now.
2. Run the role-specific tests in $WORKTREE: make -C "$WORKTREE" test-backend или make -C "$WORKTREE" test-frontend. Тесты — только foreground, дождись результата; NEVER оставляй фоновый прогон после отчёта (Rule: Agent Commons > Single Test Run Rule).
3. Run lint: make -C "$WORKTREE" lint-backend / make -C "$WORKTREE" lint-frontend.
4. If golden path affected → verify the corresponding scenario.
5. Update $PROJECT_ROOT/.agent/SESSION_LOG.md.

Report:
- Root cause
- Fix
- Changed files
- Test results
- Any deviations from PLAN.md (must be re-approved)
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

## Step 9.5: Knowledge Capture — уроки из бага

Баги — лучший источник уроков. Перед итоговым отчётом ответь на три вопроса:

1. **Почему баг дошёл?** Какой слой пайплайна должен был его поймать (unit-тест, ревью, QA, E2E) и почему не поймал.
2. **Повторяем ли паттерн?** Есть ли похожая запись в `.kimi-code/rules/known-pitfalls.md` или `.kimi-code/LESSONS_LEARNED.md`.
3. **Что предотвратило бы повтор?** Действуй по классификации из `/skill:implement` Step 8.5:
   - **doc-worthy** (разовый технический урок) → сразу допиши в `.kimi-code/LESSONS_LEARNED.md` (формат: Ошибка / Причина / Решение / Профилактика).
   - **rule-worthy / skill-worthy** → не правь сам, вынеси в итоговый отчёт списком «Предлагаемые улучшения пайплайна».
   - **test-worthy** (нет теста на этот сценарий) → регрессионный тест должен уже быть частью фикса (Step 6); если нет — это blocker для merge.

Порог тот же: только повторяемые или дорогие уроки. Если уроков нет — напиши «уроков не выявлено».

---

## Step 10: Итоговый отчёт

После всех фаз:

1. Запусти `python scripts/implement-pipeline.py record-metrics <task-id>`, чтобы собрать и сохранить метрики пайплайна в `.agent/runs/<task-id>/metrics.json`.
2. Запусти `python scripts/implement-pipeline.py check-context <task-id>`, чтобы зафиксировать итоговый estimated tokens.
3. Обнови `$PROJECT_ROOT/.agent/SESSION_LOG.md`.
4. Обнови `.agent/BACKLOG.md`, если баг был из спринта.
5. Сообщи пользователю:
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
   - Путь к `.agent/runs/<task-id>/metrics.json`
   - Открытые findings или H-items (если есть)
6. Спроси: **"Влить `$BRANCH` в main?"** — НЕ мержи без явного одобрения.
7. Если merge выполнен, переведи связанный GitHub Issue в **Done**:
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
