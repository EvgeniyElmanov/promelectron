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

## Step 2: Проверка размера контекста (Kimi K3)

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Context Size Check перед запуском субагентов.

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

Если `ESTIMATED_TOKENS >= 150000`, читай `$AGENT_DIR/CONTEXT_SUMMARY.md` вместо полной истории.

---

## Step 3: Политика повторных попыток

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Retry Policy при запуске субагентов.

---

## Step 3.1: Observability — trace границ фаз

На каждой границе фазы записывай событие в append-only trace задачи (единый correlation ID на задачу создаётся автоматически при первом событии):

```bash
python3 scripts/agent_state.py trace <task-id> <event> --actor <actor> --data '{"key": "value"}'
```

Обязательные события:

| Момент | event | actor |
|--------|-------|-------|
| task.md создан | `task_created` | orchestrator |
| spec одобрен пользователем | `spec_approved` | orchestrator |
| план создан | `plan_created` | orchestrator |
| план auto-одобрен | `plan_auto_approved` | orchestrator |
| план одобрен человеком | `plan_human_approved` | human |
| план доработан | `plan_revised` | orchestrator |
| developer(ы) отчитались о готовности | `dev_done` | backend-dev / frontend-dev |
| вердикт ревью (каждая итерация) | `review_verdict` | code-reviewer (data: `{"iteration": N, "verdict": "..."}`) |
| QA gate завершён | `qa_done` | qa (data: `{"status": "TESTS_PASSED|TESTS_FAILED"}`) |
| PR открыт | `pr_opened` | orchestrator (data: `{"url": "..."}`) |
| Knowledge capture | `knowledge_captured` | orchestrator (data: `{"rules": N, "skills": N, "docs": N}`) |

Trace не должен блокировать пайплайн: если команда падает — продолжай и упомяни в итоговом отчёте.

---

## Step 4: Фаза архитектора (пропустить при --quick)

Спецификацию пишет **агент `architect`** — ты (оркестратор) только управляешь циклом и общаешься с пользователем. Не пиши spec сам.

### 4.1 Research fan-out (параллельно, опционально)

Для нетривиальных задач запускай read-only research субагентов параллельно через инструмент `AgentSwarm` с `subagent_type: explore` — один на ось (libraries, best-practices, codebase integration) — каждый пишет `$AGENT_DIR/research/<axis>.md`. Для мелких внутренних изменений пропусти.

### 4.2 Запуск архитектора

Запусти субагента architect через инструмент `Agent` с `subagent_type: plan`. Применяй политику повторных попыток из Step 3.

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

Ты — архитектор Promelectron.

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

## Step 4.6: Figma design tokens (опционально)

Если в `spec.md` указан `figma_file_key` (например, `figma_file_key: AbC123dEfG`), используй MCP-сервер `figma`, чтобы подтянуть design tokens до старта разработки frontend:

```text
Инструменты MCP:
- figma/get_design_tokens — агрегированный summary (colors, typography, spacing)
- figma/get_file — дерево документа, если нужна структура экранов
- figma/get_components — компоненты, которые можно переиспользовать
```

Извлечённые tokens сохрани как справочник для frontend-dev агента (можно кратко в `task.md` или в отдельный `$AGENT_DIR/design-tokens.md`).

Если MCP-сервер недоступен (нет `FIGMA_ACCESS_TOKEN`) — продолжай без него; это не blocker. Просто frontend-dev должен следовать существующим UI-конвенциям проекта.

---

## Step 5: Разработка — plan → approve → execute

Прочитай `Components Affected` и `Parallelization Plan` из `$AGENT_DIR/spec.md`. Вся работа с кодом ведётся в `WORKTREE`.

Разработку разбиваем на три фазы: **Plan → Approve → Execute**. Developer-агент **не пишет код без одобренного плана**.

---

### Step 5a: Plan — developer пишет PLAN.md

Запусти нужные роли с задачей **только написать план**, не меняя код. Каждая роль создаёт `$WORKTREE/PLAN.md` (один общий, если serial; по одному для backend/frontend, если параллельно). Если фича затрагивает и backend, и frontend — пишутся два независимых плана.

Правила запуска те же:

- **Backend + frontend, независимы, нет `--backend-only`/`--frontend-only`/`--serial`:** параллельно `AgentSwarm` с `items: ["backend-dev", "frontend-dev"]`.
- **`--serial`:** последовательно — сначала backend-dev, затем frontend-dev в том же worktree.
- **Одна сторона / devops:** один вызов `Agent`.

Промпт тот же, что и для execution (см. Step 5c), но в начале явно:

```text
=== PHASE A: PLAN ONLY — DO NOT WRITE CODE ===

Перед кодированием напиши $WORKTREE/PLAN.md по spec. Следуй секции «План перед кодированием (PLAN.md)» своего ролевого SKILL.md.

PLAN.md должен содержать:
1. Goal — одно предложение.
2. Steps — нумерованный список шагов: что меняется, в каком порядке, проверка после каждого шага.
3. Risks / Open questions — что может пойти не так.

Не редактируй production-код, не создавай миграций, не трогай frontend/backend.
После написания PLAN.md остановись и сообщи: «PLAN.md готов».
```

После завершения всех ролей прочитай `$WORKTREE/PLAN.md` (и backend/frontend планы, если они разделены).

---

### Step 5b: Approve — auto или human

Оркестратор оценивает план(ы) по критериям **auto-approve**. План auto-одобряется, если **все** условия выполнены:

1. Затронута только одна сторона ИЛИ backend и frontend имеют независимые планы без перекрёстных зависимостей.
2. ≤ 5 Must-haves / Acceptance Criteria в spec.
3. В плане ≤ 4 основных шага.
4. Нет auth / payments / PII / uploads / orders / webhooks (extended security scope).
5. Нет внешних интеграций (1С, YooKassa, CDEK, Telegram, внешние API).
6. Все риски помечены как LOW или описан стандартный rollback.

Логируй trace:

```bash
python3 scripts/agent_state.py trace <task-id> plan_created --actor orchestrator
python3 scripts/agent_state.py trace <task-id> plan_auto_approved --actor orchestrator
# или
python3 scripts/agent_state.py trace <task-id> plan_human_approved --actor human --data '{"reason": "..."}'
# при доработке
python3 scripts/agent_state.py trace <task-id> plan_revised --actor orchestrator
```

Если план auto-одобрен — продолжай к Step 5c.

Если **хотя бы один** критерий не выполнен — покажи PLAN.md пользователю кратко (Goal, Steps, Risks) и спроси: **«одобрить план / доработать?»**. При доработке верни в Step 5a. При одобрении — иди к Step 5c.

> **Не экономь на human-approval:** если план касается денег, безопасности, публичного API или критичной инфраструктуры — всегда показывай пользователю, даже если формально проходит auto-approve.

---

### Step 5c: Execute — реализация по одобренному плану

Запусти те же роли с задачей **реализовать одобренный PLAN.md**. Параллельность / serial / одиночный запуск — та же схема, что в Step 5a.

Промпт (замени `{{item}}` на роль, используется через `AgentSwarm`):

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

Ты — {{item}} для Promelectron.

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. $WORKTREE/PLAN.md — одобренный план, реализуй строго по нему
4. PROJECT_CONTEXT.md
5. .agent/BACKLOG.md
6. .agent/BLOCKERS.md
7. .agent/SESSION_LOG.md
8. `.kimi-code/skills/<role>/SKILL.md` (роль подставляется из `{{item}}` AgentSwarm)
9. [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md)
10. [Rule: Agent Commons](../../rules/agent-commons.md)
11. [Rule: Security](../../rules/security.md) — всегда; lightweight pass для любой задачи, extended для auth/payments/PII/uploads/orders/webhooks

Setup:
1. Работай ТОЛЬКО внутри $WORKTREE (ветка $BRANCH).
2. Используй явные пути: git -C "$WORKTREE" ..., make -C "$WORKTREE" ..., Read/Edit/Write файлов под $WORKTREE.

Implement strictly per the approved PLAN.md and the workflow of {{item}}:
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
- If the approved PLAN.md becomes unworkable mid-flight: stop, report to orchestrator, revise PLAN.md, and get re-approval before continuing.

Before finishing:
1. Run the role-specific tests in $WORKTREE (e.g. make -C "$WORKTREE" test-backend; make -C "$WORKTREE" test-frontend).
2. Run lint (make -C "$WORKTREE" lint-backend / make -C "$WORKTREE" lint-frontend) in $WORKTREE.
3. Update $PROJECT_ROOT/.agent/SESSION_LOG.md (do NOT write session log only inside worktree).

Report:
- Changed files
- Test results
- Any deviations from PLAN.md (must be re-approved)
- Any blockers

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

> **Rate limits AgentSwarm:** при большом fan-out или повторяющихся 429 установи `KIMI_CODE_AGENT_SWARM_MAX_CONCURRENCY=2` (env var, см. Kimi Code CLI v0.18.0+), чтобы swarm не упирался в provider rate limits.

---

## Step 5.5: Валидация API Contract (backend ↔ frontend)

Пропусти, если фича затрагивает только backend или только frontend. Иначе — **до запуска reviewer-субагентов** сам (оркестратор) сверь, что backend и frontend сошлись в контракте из `$AGENT_DIR/spec.md`:

1. Извлеки изменённые/новые endpoints из backend diff:
   ```bash
   git -C "$WORKTREE" --no-pager diff origin/main...HEAD -- 'backend/src/app/api/*.py' | grep -E '^\+.*@(router|.*)\.(get|post|put|patch|delete)'
   ```
2. Извлеки API calls из frontend diff:
   ```bash
   git -C "$WORKTREE" --no-pager diff origin/main...HEAD -- 'frontend/src/api/*' | grep -E '^\+.*(get|post|put|patch|delete)\('
   ```
3. Сверь по каждому endpoint из spec `API Changes`:
   - **path** совпадает, включая **trailing slash** (`/items/`, не `/items`)
   - **HTTP method** совпадает
   - **request-поля** (body/params/query) совпадают с Pydantic-схемой
   - **response-поля**, которые frontend реально читает, присутствуют в response-схеме
4. Если нашёл расхождение — зафиксируй в `$AGENT_DIR/review/findings.md` как `[F-xxx] CRITICAL | API Contract` со статусом `OPEN` и верни соответствующего developer-субагента на исправление **до** Step 6.
5. Если расхождений нет — переходи к Step 6.

Этот шаг ловит класс ошибок «backend и frontend параллельно разошлись в контракте», который дороже чинить после ревью, чем до него.

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
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

Ты — code-reviewer для Promelectron.

Контекст:
- task-id: <task-id>
- AGENT_DIR: $AGENT_DIR
- WORKTREE: $WORKTREE
- scope: all
- output: $AGENT_DIR/review/findings.md
- iteration: <N>

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. $AGENT_DIR/review/findings.md (если это повторная итерация)
4. `.kimi-code/skills/code-reviewer/SKILL.md`
5. [Rule: Security](../../rules/security.md)
6. [Rule: Agent Commons](../../rules/agent-commons.md)

Затем следуй workflow из `.kimi-code/skills/code-reviewer/SKILL.md` строго. Запиши findings в $AGENT_DIR/review/findings.md.

Do NOT edit source code. Only write findings.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

### Смешанное ревью (backend + frontend параллельно)

Запусти reviewer-субагентов через инструмент `AgentSwarm` с `subagent_type: coder`. Применяй политику повторных попыток из Step 3.

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
- iteration: <N>

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. $AGENT_DIR/review/findings-{{item}}.md (если это повторная итерация)
4. `.kimi-code/skills/code-reviewer/SKILL.md`
5. [Rule: Security](../../rules/security.md)
6. [Rule: Agent Commons](../../rules/agent-commons.md)

Затем следуй workflow из `.kimi-code/skills/code-reviewer/SKILL.md` строго. Запиши findings в $AGENT_DIR/review/findings-{{item}}.md.

Do NOT edit source code. Only write findings.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

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
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

Ты — QA-инженер для Promelectron.

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
3. Если фича затрагивает UI или пользовательские сценарии — запусти E2E: `make -C "$WORKTREE" test-e2e`. Не делегируй E2E другому субагенту; оркестратор запустит `e2e-tester` отдельно при необходимости.
4. Проверь каждый Acceptance Criterion из $AGENT_DIR/spec.md.
5. Запиши результаты в $AGENT_DIR/review/test-findings.md.
6. Обнови $PROJECT_ROOT/.agent/SESSION_LOG.md.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

### Step 7.5: E2E-тестер (опционально, запускается оркестратором)

Если фича затрагивает UI/пользовательские сценарии и требует ручной E2E-автоматизации (новые селекторы, сложный браузерный сценарий), запусти субагента `e2e-tester` **из основного агента** через инструмент `Agent` с `subagent_type: coder`. Не запускай e2e-tester изнутри qa-субагента.

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

Ты — e2e-tester для Promelectron.

Paths:
- AGENT_DIR = $AGENT_DIR
- WORKTREE = $WORKTREE

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. $AGENT_DIR/review/findings.md
4. $AGENT_DIR/review/test-findings.md (если есть)
5. `.kimi-code/skills/e2e-tester/SKILL.md`
6. [Rule: Golden Path](../../rules/golden-path.md)
7. [Rule: Agent Commons](../../rules/agent-commons.md)

Затем:
1. Работай только внутри $WORKTREE.
2. Сопоставь Acceptance Criteria из spec.md с E2E-сценариями.
3. Добавь/обнови E2E-тесты в $WORKTREE/frontend/e2e/.
4. Запусти `npx playwright test` для новых/изменённых спек.
5. Запиши краткий результат в $AGENT_DIR/review/test-findings.md (добавь секцию E2E, не перезаписывай результаты qa).

Do NOT edit source code, кроме `data-testid` и E2E-спек.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

Если статус `test-findings.md` — `TESTS_FAILED`, покажи ошибки, вызови затронутого разработчика для исправления, затем вернись к Step 6 (изменён код → повторное ревью). Максимум 2 QA/E2E-итерации, затем эскалация пользователю.

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

## Step 8.5: Knowledge Capture — уроки из прогона

Перед итоговым отчётом извлеки уроки из этого run. Это фаза самоулучшения пайплайна: то, что стоило нам итераций, не должно повториться.

**Что анализировать:**

1. `review/findings.md` — какие категории findings повторялись между итерациями (одна и та же ошибка дважды = системная проблема процесса, а не кода).
2. `review/test-findings.md` — падения QA, которые не были пойманы на ревью.
3. Ошибки субагентов и retry (см. trace.jsonl, если есть).
4. Правки, которые вносил человек вручную (спроси пользователя, если заметил их в diff).

**Классификация каждого урока:**

| Класс | Критерий | Куда попадает |
|-------|----------|---------------|
| **rule-worthy** | Инвариант, который должны соблюдать все задачи | Предложение добавить в `.kimi-code/rules/` (pre-edit-checklist / known-pitfalls / business / security) |
| **skill-worthy** | Улучшение процедуры конкретной роли | Предложение правки `.kimi-code/skills/<role>/SKILL.md` |
| **doc-worthy** | Разовый технический урок (окружение, инструменты, flaky) | Сразу записать в `.kimi-code/LESSONS_LEARNED.md` |

**Порог срабатывания** — пишем урок только если он:

- **повторяемый** — встретился ≥2 раз в этом run или уже есть похожий в `known-pitfalls.md`; или
- **дорогой** — стоил итерацию ревью, падение QA или вмешательство человека.

Не плоди шум: «опечатка в одном файле» — не урок.

**Действия:**

- **doc-worthy** — допиши в `.kimi-code/LESSONS_LEARNED.md` по существующему формату: номер, заголовок, **Ошибка** / **Причина** / **Решение** / **Профилактика**.
- **rule-worthy / skill-worthy** — НЕ правь правила и скиллы сам. Вынеси в итоговый отчёт отдельным списком «Предлагаемые улучшения пайплайна» с конкретным текстом правки; пользователь одобряет.
- Запиши trace: `python3 scripts/agent_state.py trace <task-id> knowledge_captured --actor orchestrator --data '{"rules": N, "skills": N, "docs": N}'`.

Если уроков нет — так и напиши в отчёте: «уроков не выявлено». Не выдумывай.

---

## Step 9: Итоговый отчёт

После завершения всех фаз:

1. Запусти `python scripts/implement-pipeline.py record-metrics <task-id>`, чтобы собрать и сохранить метрики пайплайна в `.agent/runs/<task-id>/metrics.json`.
2. Запусти `python scripts/implement-pipeline.py check-context <task-id>`, чтобы зафиксировать итоговый размер контекста.
3. Прочитай `.agent/SESSION_LOG.md` и допиши сводку: estimated tokens, количество итераций ревью, результат QA.
4. Сообщи пользователю на русском:
   - Task ID
   - Путь к worktree: `$WORKTREE`
   - Feature branch: `$BRANCH`
   - URL PR (если создан)
   - Изменённые файлы
   - Результаты тестов (backend, frontend, e2e)
   - Статус ревью
   - Estimated tokens и количество итераций
   - Путь к `.agent/runs/<task-id>/metrics.json`
   - Открытые findings или H-items (если есть)
5. Спроси: **"Влить `$BRANCH` в main?"** — НЕ мержи и НЕ пушь в main без явного одобрения.
6. Если пользователь одобрил merge и merge выполнен, переведи связанный GitHub Issue в **Done**:
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
