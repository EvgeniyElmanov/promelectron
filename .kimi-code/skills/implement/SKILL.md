---
name: implement
description: >
  Full development cycle skill for Promelectron.
  Use for implementing new features, adding pages, creating API endpoints, building Vue components, adding database models, schemas, services, migrations, or any task requiring code changes.
  Runs an architect phase in plan mode, creates a git worktree, develops backend and/or frontend, performs a code review loop (max 3 iterations), an E2E test phase, opens a GitHub PR, and reports results.
  Triggers on: implement, feature, add, create, build, develop, new page, new API, endpoint, component, model, schema, migration, page, view.
type: prompt
whenToUse: When the user asks to implement a new feature, page, API endpoint, component, model, schema, migration, or any multi-step code change that would benefit from architect → developer → reviewer → e2e → PR workflow.
arguments: "<task description> [--quick] [--backend-only] [--frontend-only] [--serial] [--qa]"
disableModelInvocation: false
---

# /skill:implement — Полный цикл разработки

> **ЯЗЫК / LANGUAGE:** Пользователь общается на русском. Все ответы пользователю, отчёты и артефакты (task.md, spec.md, findings, test-findings, SESSION_LOG, комментарии к PR) пиши на русском. Стремись рассуждать на русском, но если внутреннее reasoning уходит на английский — это не ошибка; главное, чтобы финальные ответы и артефакты были на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Реализуй новую фичу от идеи до протестированного кода: изолированный git worktree, архитектура в plan mode, цикл ревью, E2E-тесты и GitHub Pull Request.

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

Проверь доступ к GitHub CLI — автоматизация бэклога зависит от него:

```bash
gh auth status
gh project view 1 --owner AutonomaCo
```

Если что-то не так — остановись и попроси пользователя выполнить `gh auth login` или выдать scope `project`.

Сгенерируй `<task-id>`: короткий slug в kebab-case, например `add-promo-codes`, `fix-cart-stock`.

Создай временную координационную плоскость и корень worktree:

```bash
mkdir -p "$PROJECT_ROOT/.agent/runs/<task-id>/review"
mkdir -p "$PROJECT_ROOT/.worktrees"
```

Пути для остального пайплайна:

```text
AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>       (gitignored coordination plane)
WORKTREE  = $PROJECT_ROOT/.worktrees/<task-id>        (per-task code checkout)
BRANCH    = feature/<task-id>
```

> **Важно:** `.agent/runs/<task-id>/` — в `.gitignore`. Никогда не пиши временные файлы пайплайна в закоммиченную планировочную директорию `.agent/` (`BACKLOG.md`, `PLANNING_HANDOFF.md`, `tasks/` и т.д.).

Напиши `$AGENT_DIR/task.md`:

```markdown
# Task: <task-id>

## Description
<полное описание задачи>

## Flags
<активные флаги или "none">

## Date
<YYYY-MM-DD>
```

---

## Step 1: Создание изолированного worktree

Сделай это **до** того, как любой агент коснётся кода, в обычном (не plan) режиме — `git worktree add` — это изменение на диске, который plan mode блокирует.

```bash
git -C "$PROJECT_ROOT" fetch origin
git -C "$PROJECT_ROOT" worktree add "$WORKTREE" -b "$BRANCH" origin/main
```

- **Всегда ветвись от `origin/main`.** Никогда не от текущей ветки.
- Если worktree уже существует (повторный запуск) — переиспользуй его; проверь `git -C "$PROJECT_ROOT" worktree list`.
- Worktree — свежий checkout: скопируй gitignored локальные файлы, нужные для сборки. Учитывай `.worktreeinclude`, если он есть; иначе копируй `.env` / `backend/.env` / `frontend/.env`, если они существуют.

Можно использовать вспомогательный скрипт:

```bash
python scripts/implement-pipeline.py setup "<описание>" --flags "<флаги>"
python scripts/implement-pipeline.py create-worktree <task-id>
```

---

## Step 2: Проверка размера контекста (Kimi K2.7-Code)

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Context Size Check перед запуском субагентов.

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

Если `ESTIMATED_TOKENS >= 150000`, читай `$AGENT_DIR/CONTEXT_SUMMARY.md` вместо полной истории.

---

## Step 3: Политика повторных попыток

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Retry Policy при запуске субагентов.

---

## Step 4: Фаза архитектора (пропустить при --quick)

Спецификацию пишет **агент `architect`** — ты (оркестратор) только управляешь циклом и общаешься с пользователем. Не пиши spec сам.

### 4.1 Research fan-out (параллельно, опционально)

Для нетривиальных задач запускай read-only research субагентов (`coder` с read-only инструкциями) параллельно в одном сообщении — один на ось (libraries, best-practices, codebase integration) — каждый пишет `$AGENT_DIR/research/<axis>.md`. Для мелких внутренних изменений пропусти.

### 4.2 Запуск архитектора

Запусти субагента architect через инструмент `Agent` с `subagent_type: plan`. Применяй политику повторных попыток из Step 3.

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Ключевые инструкции этой задачи — на русском. Ты — архитектор Promelectron. Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. При multi-step tool calling сохраняй `reasoning_content` из ассистентских сообщений в истории. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Important: Kimi K2.7-Code uses mandatory thinking mode (`thinking={"type":"enabled"}`), with fixed `temperature=1.0`, `top_p=0.95`, `n=1`, `presence_penalty=0.0`, `frequency_penalty=0.0`. `tool_choice` may only be `"auto"` or `"none"`.

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md
2. $AGENT_DIR/research/*.md (если есть) и синтезируй в $AGENT_DIR/research.md
3. PROJECT_CONTEXT.md
4. .agent/BACKLOG.md
5. .agent/BLOCKERS.md
6. .agent/SESSION_LOG.md
7. `.kimi-code/skills/architect/SKILL.md`
8. [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md)
9. [Rule: Agent Commons](../../rules/agent-commons.md) — язык, retry policy, API constraints

Ты уже запущен как `plan`-субагент — контекст plan уже отключает shell и включает планирование, поэтому НЕ вызывай EnterPlanMode повторно. Пиши спецификацию прямо в plan-файл, предоставленный контекстом plan-субагента, затем вызови ExitPlanMode.

Затем:
1. Загрузи как можно больше релевантного контекста **параллельно**: читай task-файлы, существующий код в $WORKTREE, внешнюю документацию/WebSearch.
2. Исследуй кодовую базу через Read/Grep/Glob (запускай несколько чтений/поисков параллельно), чтобы понять, как фича вписывается.
3. Используй WebSearch/FetchURL, если нужна внешняя документация, API docs или примеры библиотек.
4. Задай уточняющие вопросы пользователю через AskUserQuestion, если требования неясны.
5. Напиши техническую спецификацию в plan-файл. Включи:
   - Task Type
   - Analysis
   - Decisions (D-01, D-02, ...)
   - Components Affected (backend/frontend/infra)
   - Parallelization Plan
   - Technical Design
   - API Changes
   - Must-haves
   - Acceptance Criteria
   - Out of Scope
6. Вызови ExitPlanMode.

Do NOT write implementation code, tests, or migrations.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

### 4.3 Копирование плана в координационную плоскость

После одобрения плана пользователем скопируй содержимое plan-файла в `$AGENT_DIR/spec.md`.

Если пользователь отклонил или попросил доработки — отправь архитектора на доработку.

---

## Step 4.5: Публикация в GitHub backlog

Каждая задача, выходящая на разработку, ДОЛЖНА иметь связанный GitHub Issue на проектной доске Promelectron. Этот шаг выполняется **после одобрения spec** и **до запуска любого developer-субагента**.

### 4.5.1 Проверка существующего issue

Прочитай `$AGENT_DIR/task.md`:

- Если там уже есть `github_issue: #N` (например, пользователь вызвал `/skill:implement #5`) — пропусти создание, только убедись, что статус issue — **In progress**.
- Иначе — создай новый issue.

### 4.5.2 Формирование черновика issue из spec

Используй `$AGENT_DIR/spec.md`, чтобы составить краткий issue:

- **Title:** не более 120 символов, из описания задачи или заголовка spec.
- **Body:** Summary, Must-haves, Acceptance Criteria, Out of Scope, plus link to `.agent/runs/<task-id>/spec.md`.

### 4.5.3 Подтверждение у пользователя

Покажи черновик title/body через `AskUserQuestion`:

> "Спецификация одобрена. Я создам/свяжу GitHub Issue и переведу его в **In progress** на доске. Продолжить?"

Дождись явного одобрения перед публикацией.

### 4.5.4 Создание/связывание issue и project item

Используй вспомогательный скрипт:

```bash
python scripts/implement-pipeline.py create-issue <task-id> --status in-progress
```

Эта команда:
- Создаёт или обновляет GitHub Issue через `gh issue create` / `gh issue edit`.
- Добавляет issue на GitHub Project board.
- Устанавливает статус проекта `In progress`.
- Пишет `github_issue` / `issue_url` обратно в `task.md` и `spec.md`.
- Добавляет связанную строку в `.agent/BACKLOG.md`.

Захвати выведенные значения:

```text
ISSUE_URL=https://github.com/AutonomaCo/promelectron/issues/N
ISSUE_NUMBER=N
STATUS=in-progress
```

### 4.5.5 При ошибке

Если `gh issue create` или обновление проекта не удалось:
- Сообщи пользователю точную ошибку.
- НЕ начинай разработку, пока issue не связан.
- Эскалируй, если не хватает scope `gh auth`.

---

## Step 5: Разработка — по умолчанию параллельно

Прочитай `Components Affected` и `Parallelization Plan` из `$AGENT_DIR/spec.md`. Вся работа с кодом ведётся в `WORKTREE` (используй `git -C`, `make -C`, явные пути — `cd` субагента не сохраняется).

**Если затронуты и backend, и frontend, они независимы, и не заданы `--backend-only`/`--frontend-only`/`--serial`:**
Запусти `backend-dev` и `frontend-dev` **в одном сообщении**, чтобы они работали параллельно. Они редактируют непересекающиеся деревья (`backend/` и `frontend/`) и оба ориентируются на **API Contract** из spec.

**Если задан `--serial`:** сначала backend, затем frontend в том же worktree.

**Если затронута только одна сторона или флаги ограничивают область:** запускай только нужных разработчиков.

Промпт для каждого разработчика:

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

Implement strictly per the spec and your role workflow:
- backend-dev: model → schema → service → route handler → tests
- frontend-dev: API service → composable → component → page → route → tests
- devops: Helm/Docker → CI/CD → verify

Rules:
- Business logic belongs in services, NOT route handlers.
- Every new endpoint must have tests.
- Every model change must have an Alembic migration.
- Use trailing slash in FastAPI endpoints.
- Do NOT commit to main. You may commit to $BRANCH in the worktree.
- For OPEN findings from previous review: fix them and update the finding status to FIXED in $AGENT_DIR/review/findings.md.

Before finishing:
1. Run the role-specific tests in $WORKTREE (e.g. make -C "$WORKTREE" test-backend; make -C "$WORKTREE" test-frontend).
2. Run lint (make -C "$WORKTREE" lint-backend / make -C "$WORKTREE" lint-frontend) in $WORKTREE.
3. Update $PROJECT_ROOT/.agent/SESSION_LOG.md (do NOT write session log only inside worktree).

Report:
- Changed files
- Test results
- Any blockers

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

---

## Step 6: Цикл ревью кода (максимум 3 итерации)

### Определение scope ревью

На основе spec и флагов (`--backend-only`, `--frontend-only`):

- **Только backend или только frontend** → запусти одного reviewer-субагента.
- **Смешанный (backend + frontend)** → запусти двух reviewer-субагентов параллельно через `AgentSwarm`.
- **Security-sensitive работа** (auth, payments, orders) → добавь `security-reviewer` в параллельную партию.

### Single-component review

Запусти одного reviewer-субагента через `Agent` с `subagent_type: coder`. Применяй политику повторных попыток из Step 3.

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Ключевые инструкции этой задачи — на русском. Ты — code-reviewer для Promelectron. Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. При multi-step tool calling сохраняй `reasoning_content` из ассистентских сообщений в истории. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Important: Kimi K2.7-Code uses mandatory thinking mode (`thinking={"type":"enabled"}`), with fixed `temperature=1.0`, `top_p=0.95`, `n=1`, `presence_penalty=0.0`, `frequency_penalty=0.0`. `tool_choice` may only be `"auto"` or `"none"`.

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. `.kimi-code/skills/code-reviewer/SKILL.md`
4. [Rule: Security](../../rules/security.md)
5. [Rule: Agent Commons](../../rules/agent-commons.md)

Затем:
1. Прочитай реализацию в $WORKTREE (используй Read/Grep/Glob параллельно).
2. Получи diff: git -C "$WORKTREE" --no-pager diff --no-color origin/main...HEAD
3. Сравни со спецификацией и Decisions (D-01, D-02, ...).
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
- **Status:** OPEN | FIXED | VERIFIED

## Human Decisions (if any)
### [H001] ...

Жизненный цикл finding'а:
- `OPEN` — найден ревьюером, требует исправления разработчиком.
- `FIXED` — разработчик исправил и обновил статус (не ревьюер).
- `VERIFIED` — ревьюер на повторной проверке подтвердил исправление.

Do NOT edit source code. Only write findings.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

### Смешанное ревью (backend + frontend параллельно)

Запусти reviewer-субагентов через инструмент `AgentSwarm` с `subagent_type: coder`. Применяй политику повторных попыток из Step 3.

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Ключевые инструкции этой задачи — на русском. Ты — code-reviewer для Promelectron (фокус: {{item}}). Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. При multi-step tool calling сохраняй `reasoning_content` из ассистентских сообщений в истории. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Important: Kimi K2.7-Code uses mandatory thinking mode (`thinking={"type":"enabled"}`), with fixed `temperature=1.0`, `top_p=0.95`, `n=1`, `presence_penalty=0.0`, `frequency_penalty=0.0`. `tool_choice` may only be `"auto"` or `"none"`.

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. `.kimi-code/skills/code-reviewer/SKILL.md`
4. [Rule: Security](../../rules/security.md)
5. [Rule: Agent Commons](../../rules/agent-commons.md)

Затем:
1. Читай только {{item}}-файлы реализации в $WORKTREE (используй Read/Grep/Glob параллельно).
2. Получи diff: git -C "$WORKTREE" --no-pager diff --no-color origin/main...HEAD
3. Сравни со спецификацией и Decisions (D-01, D-02, ...).
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
- **Status:** OPEN | FIXED | VERIFIED

## Human Decisions (if any)
### [H001] ...

Do NOT edit source code. Only write findings.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

items: `["backend", "frontend"]`

**После возврата `AgentSwarm`:**
1. Прочитай `$AGENT_DIR/review/findings-backend.md` и `$AGENT_DIR/review/findings-frontend.md`.
2. Смержи их в `$AGENT_DIR/review/findings.md`:
   - Общий **Status** — `FIXES_NEEDED`, если хотя бы один sub-report `FIXES_NEEDED`; иначе `APPROVED`.
   - Сохрани номер **Iteration**.
   - Объедини списки findings; при необходимости перенумеруй, чтобы ID были уникальными across backend и frontend.
   - Сохрани Human Decisions из обоих отчётов.
3. Удали временные `findings-backend.md` и `findings-frontend.md` или оставь для отладки.

### Продолжение цикла ревью

1. Прочитай `$AGENT_DIR/review/findings.md`.
2. Если `APPROVED` → переходи к Step 7.
3. Если `FIXES_NEEDED`:
   - Покажи пользователю сводку findings.
   - Для H-items дождись решения пользователя.
   - Запусти developer-субагента повторно для исправления OPEN findings.
   - Разработчик **должен** отредактировать `$AGENT_DIR/review/findings.md` и изменить статус исправленных пунктов с `OPEN` на `FIXED` (с краткой заметкой, что изменено).
   - **Перед повторным ревью перезапусти релевантные тесты** в `$WORKTREE` (backend: `make -C "$WORKTREE" test-backend`; frontend: `make -C "$WORKTREE" test-frontend`). Если тесты падают — сначала исправь их.
   - Запусти reviewer повторно. Reviewer проверяет FIXED и меняет статус на `VERIFIED`; если не исправлено — переоткрывает как `OPEN` с пояснением.
   - Повторяй ревью.
4. После 3 итераций, если всё ещё `FIXES_NEEDED` — остановись и спроси пользователя, как поступить.

---

## Step 7: QA / Пирамида тестирования

### Лёгкая QA (по умолчанию)

Если `--qa` **не** задан, полагайся на тесты, запущенные разработчиками, и пропусти выделенный QA gate.

### Полный QA gate (запускать при --qa)

После прохождения code review запусти субагента `qa` через `Agent` с `subagent_type: coder`. Применяй политику повторных попыток из Step 3.

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Ключевые инструкции этой задачи — на русском. Ты — QA-инженер для Promelectron. Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. При multi-step tool calling сохраняй `reasoning_content` из ассистентских сообщений в истории. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Important: Kimi K2.7-Code uses mandatory thinking mode (`thinking={"type":"enabled"}`), with fixed `temperature=1.0`, `top_p=0.95`, `n=1`, `presence_penalty=0.0`, `frequency_penalty=0.0`. `tool_choice` may only be `"auto"` or `"none"`.

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. $AGENT_DIR/review/findings.md
4. PROJECT_CONTEXT.md
5. .agent/BACKLOG.md
6. .agent/BLOCKERS.md
7. `.kimi-code/skills/qa/SKILL.md`
8. [Rule: Golden Path](../../rules/golden-path.md)
9. [Rule: Agent Commons](../../rules/agent-commons.md)

Затем:
1. Запусти backend-тесты: make -C "$WORKTREE" test-backend
2. Запусти frontend unit-тесты: make -C "$WORKTREE" test-frontend
3. Если фича затрагивает UI или пользовательские сценарии — запусти E2E: make -C "$WORKTREE" test-e2e. При необходимости делегируй E2E-специфичную часть e2e-tester субагенту, передав scope, spec и пути $AGENT_DIR / $WORKTREE.
4. Проверь каждый Acceptance Criterion из $AGENT_DIR/spec.md.
5. Запиши результаты в $AGENT_DIR/review/test-findings.md.
6. Обнови $PROJECT_ROOT/.agent/SESSION_LOG.md.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

Субагент `qa` может запустить субагента `e2e-tester` для браузерной автоматизации, если нужно.

Если статус `test-findings.md` — `TESTS_FAILED`, покажи ошибки, вызови затронутого разработчика для исправления, затем вернись к Step 6 (изменён код → повторное ревью). Максимум 2 QA-итерации, затем эскалация пользователю.

E2E в CI уже запускается на test-окружении (`promelectron-test`) после деплоя.

---

## Step 8: Создание запроса на слияние

Все git-операции — в worktree.

1. Запушь ветку:
   ```bash
   git -C "$WORKTREE" push -u origin "$BRANCH"
   ```
2. Создай PR:
   ```bash
   gh pr create --base main --head "$BRANCH" \
     --title "<краткое описание>" \
     --body "$(cat <<'EOF'
   ## Summary
   <что сделано>

   ## Spec
   .agent/runs/<task-id>/spec.md — выбранный подход + API contract

   ## Changes
   <изменённые файлы/компоненты>

   ## Test Results
   - Backend: pytest X/Y · Frontend: vitest X/Y

   ## Acceptance Criteria
   <checked list из test-findings.md>
   EOF
   )"
   ```
3. Опубликуй открытые Human-Decision пункты как комментарии к PR:
   ```bash
   gh pr comment "$BRANCH" --body "[H-xxx] <открытый human-decision пункт>"
   ```
4. Переведи связанный GitHub Issue в **In review**:
   ```bash
   python scripts/implement-pipeline.py set-status <task-id> in-review
   ```
5. Захвати URL PR для отчёта.

---

## Step 9: Итоговый отчёт

После завершения всех фаз:

1. Запусти `python scripts/implement-pipeline.py check-context <task-id>`, чтобы зафиксировать итоговый размер контекста.
2. Прочитай `.agent/SESSION_LOG.md` и допиши сводку: estimated tokens, количество итераций ревью, результат QA.
3. Сообщи пользователю на русском:
   - Task ID
   - Путь к worktree: `$WORKTREE`
   - Feature branch: `$BRANCH`
   - URL PR (если создан)
   - Изменённые файлы
   - Результаты тестов (backend, frontend, e2e)
   - Статус ревью
   - Estimated tokens и количество итераций
   - Открытые findings или H-items (если есть)
4. Спроси: **"Влить `$BRANCH` в main?"** — НЕ мержи и НЕ пушь в main без явного одобрения.
5. Если пользователь одобрил merge и merge выполнен, переведи связанный GitHub Issue в **Done**:
   ```bash
   python scripts/implement-pipeline.py set-status <task-id> done
   ```

---

## Rules / Правила

- NEVER push directly to `main`.
- NEVER merge automatically — a human reviews and merges.
- NEVER delete the worktree until the user approves merge or explicitly asks to clean up.
- Developer marks findings FIXED; reviewer verifies and marks VERIFIED.
- Max 3 review iterations, then escalate to user.
- Max 2 QA iterations, then escalate to user.
- Update `.agent/SESSION_LOG.md` after every significant phase.
- Always write transient pipeline files to `.agent/runs/<task-id>/`, never to the committed `.agent/` planning dir.
- **Backlog automation:** every task entering development MUST have a linked GitHub Issue before Step 5.
- **Status transitions:** In progress → In review → Done are updated automatically at phase boundaries.
- **Idempotency:** never create a duplicate issue for the same `task-id`; reuse `github_issue` from `task.md`.
- **No silent publish:** always ask the user before creating a GitHub Issue.
