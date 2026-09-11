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

**Первым делом прочитай `.agents/skills/implement/SKILL.md` — там тело сценария, общее для всех агентов проекта. Правится там, а не здесь.** Ниже — только Kimi-специфика.

## Kimi-специфика

### Язык

[Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule. Преамбула для субагентов — раздел **Full subagent prompt block** там же; вставляется в начало и конец промпта каждого субагента. `task.md`, `spec.md`, findings, отчёты и записи в session-log — на русском, когда пользователь русскоязычный.

### Step 1b: Context Size Check

Перед запуском субагентов — [Rule: Agent Commons](../../rules/agent-commons.md) > Context Size Check:

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

Если оценка контекста ≥ 600000 токенов — сначала прочитай `CONTEXT_SUMMARY.md` и работай от него, а не от полной истории.

### Step 1c: Retry Policy

При запуске субагентов — [Rule: Agent Commons](../../rules/agent-commons.md) > Retry Policy: 4 попытки, backoff 2/4/8s.

### Step 1d: Observability — phase-boundary trace

На каждой границе фазы добавляй событие в append-only trace задачи (единый correlation ID на задачу создаётся автоматически при первом событии):

```bash
python3 scripts/agent_state.py trace <task-id> <event> --actor <actor> --data '{"key": "value"}'
```

Обязательные события:

| Момент | event | actor |
|--------|-------|-------|
| task.md создан | `task_created` | orchestrator |
| spec одобрен пользователем | `spec_approved` | orchestrator |
| план создан | `plan_created` | orchestrator |
| план auto-approved | `plan_auto_approved` | orchestrator |
| план одобрен человеком | `plan_human_approved` | human |
| план переработан | `plan_revised` | orchestrator |
| developer(ы) отчитались | `dev_done` | backend-dev / frontend-dev |
| вердикт ревью (каждая итерация) | `review_verdict` | code-reviewer (data: `{"iteration": N, "verdict": "..."}`) |
| QA gate завершён | `qa_done` | qa (data: `{"status": "TESTS_PASSED|TESTS_FAILED"}`) |
| PR открыт | `pr_opened` | orchestrator (data: `{"url": "..."}`) |
| Knowledge capture | `knowledge_captured` | orchestrator (data: `{"rules": N, "skills": N, "docs": N}`) |

Trace никогда не блокирует пайплайн: команда упала — продолжай и упомяни в финальном отчёте.

### Маппинг ролей на субагентов Kimi

- architect → `Agent(subagent_type: plan)` — plan-контекст уже отключает shell и фокусирует на планировании; **не вызывай `EnterPlanMode` повторно**, спеку пиши в plan-файл контекста и завершай `ExitPlanMode`.
- developer (backend-dev / frontend-dev / devops), code-reviewer, qa, e2e-tester → `Agent(subagent_type: coder)`.
- Research fan-out → `AgentSwarm(subagent_type: explore)` — по одному исследователю на ось.
- Mixed review (backend + frontend) → `AgentSwarm(subagent_type: coder)` с items `["backend", "frontend"]`.
- Параллельные разношёрстные developer-роли (backend + frontend) → **два раздельных вызова `Agent`** в одном сообщении (промпты разные, поэтому не один `AgentSwarm` с `{{item}}`).

**После возврата `AgentSwarm` (mixed review):**
1. Прочитай `review/findings-backend.md` и `review/findings-frontend.md`.
2. Смерджи в `review/findings.md`:
   - Overall **Status** = `FIXES_NEEDED`, если хотя бы один sub-report `FIXES_NEEDED`; иначе `APPROVED`.
   - Сохрани номер **Iteration**.
   - Объедини списки findings; перенумеруй так, чтобы ID были уникальны между backend и frontend.
   - Сохрани Human Decisions из обоих отчётов.
3. Временные `findings-backend.md` / `findings-frontend.md` удали или оставь для отладки.

**Rate limits:** при большом fan-out или повторяющихся 429 установи `KIMI_CODE_AGENT_SWARM_MAX_CONCURRENCY=2` (env var, Kimi Code CLI v0.18.0+), чтобы параллельные субагенты не упирались в provider rate limits.

**Вложенность:** субагенты Kimi не могут порождать вложенных субагентов. e2e-tester запускается **только оркестратором** — никогда изнутри qa-субагента.

### Промпты субагентов

Все промпты ниже предваряются комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block) — в начало и конец промпта. Чтение ролей: для ролей с общим файлом — `.agents/agents/<role>.md` (architect, backend-dev, code-reviewer, devops, e2e-tester, frontend-dev, qa, security-reviewer).

#### Architect (`Agent`, subagent_type: plan)

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

You are the architect for Promelectron.
Read:
1. .agent/runs/<task-id>/task.md
2. .agent/runs/<task-id>/research/*.md (if present) — synthesize into .agent/runs/<task-id>/research.md
3. PROJECT_CONTEXT.md
4. docs/backlog.md
5. docs/blockers.md
6. docs/journal/session-log.md
7. `.agents/agents/architect.md`
8. [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md)

Then:
1. You are already running as a `plan` subagent — the plan context already disables shell access and focuses on planning, so do NOT call `EnterPlanMode` again. Write the specification directly to the plan file provided by the plan subagent context, and call `ExitPlanMode` at the end.
2. Load as much relevant context as possible in **parallel**: read task files, existing code, and external docs/WebSearch results simultaneously.
3. Explore the codebase with Read/Grep/Glob (run multiple reads/searches in parallel) to understand how the feature fits.
4. Use WebSearch/FetchURL if you need external documentation, API docs, or library examples.
5. Ask the user clarifying questions via AskUserQuestion if requirements are unclear.
6. Write a technical specification to the plan file. Include:
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
7. Call ExitPlanMode.

Do NOT write implementation code, tests, or migrations.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

После одобрения плана пользователем скопируй содержимое plan-файла в `$AGENT_DIR/spec.md`. Если пользователь отклонил или попросил доработку — отправь architect на переработку.

#### Developer, фаза Plan (`Agent`, subagent_type: coder)

Тот же промпт, что для Execute (ниже), но с префиксом:

```text
=== PHASE A: PLAN ONLY — DO NOT WRITE CODE ===

Перед кодированием напиши $WORKTREE/PLAN.md (или $WORKTREE/PLAN.<role>.md при параллельном запуске) по spec. Следуй секции «План перед кодированием (PLAN.md)» своего ролевого файла.

PLAN.md должен содержать:
1. Goal — одно предложение.
2. Steps — нумерованный список шагов: что меняется, в каком порядке, проверка после каждого шага.
3. Risks / Open questions — что может пойти не так.

Не редактируй production-код, не создавай миграций, не трогай frontend/backend.
После написания PLAN.md остановись и сообщи: «PLAN.md готов».
```

#### Developer, фаза Execute (`Agent`, subagent_type: coder; при параллельном режиме — оба вызова в одном сообщении)

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

You are <ROLE> for Promelectron.

Paths:
- AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>
- WORKTREE = $PROJECT_ROOT/.worktrees/<task-id>
- BRANCH = feature/<task-id>

Read:
1. .agent/runs/<task-id>/task.md
2. .agent/runs/<task-id>/spec.md
3. $WORKTREE/PLAN.md — одобренный план, реализуй строго по нему
4. PROJECT_CONTEXT.md
5. docs/backlog.md
6. docs/blockers.md
7. `.agents/agents/<ROLE>.md`
8. [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md)

Setup:
1. Work ONLY inside $WORKTREE (branch feature/<task-id>).
2. Use explicit paths: git -C "$WORKTREE" ..., make -C "$WORKTREE" ..., Read/Edit/Write files under $WORKTREE.
3. Scope boundary (обязательно при параллельном запуске): backend-dev изменяет файлы только внутри `backend/` (код, alembic-миграции, backend-тесты), frontend-dev — только внутри `frontend/`. Файлы вне своего scope не трогай.

Implement strictly per the approved PLAN.md and your role workflow:
- backend-dev: model → schema → service → route handler → tests
- frontend-dev: API service → composable → component → page → route → tests
- devops: Helm/Docker → CI/CD → verify

Rules:
- Business logic belongs in services, NOT route handlers.
- Every new endpoint must have tests.
- Every model change must have an Alembic migration.
- Use trailing slash in FastAPI endpoints.
- Do NOT commit to main. You may commit to feature/<task-id> in the worktree.
- For OPEN findings from a previous review: fix them and set their status to FIXED in $AGENT_DIR/review/findings.md.
- If the approved PLAN.md becomes unworkable mid-flight: stop, report to the orchestrator, revise PLAN.md, and get re-approval before continuing.

Before finishing:
1. Run the role-specific tests (e.g. make -C "$WORKTREE" test-backend; cd "$WORKTREE/frontend" && npm test). Тесты — только foreground, дождись результата; NEVER оставляй фоновый прогон после отчёта (Rule: Agent Commons > Single Test Run Rule).
2. Run lint (ruff / npm run lint).
3. Update docs/journal/session-log.md from the worktree (при параллельном запуске backend+frontend это делает оркестратор — пропусти).

Report:
- Changed files
- Test results
- Any deviations from PLAN.md (must be re-approved)
- Any blockers

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

При параллельном запуске оба агента работают в **одном** worktree `.worktrees/<task-id>` (общая feature-ветка), но не пересекаются по файлам благодаря scope boundary. `docs/journal/session-log.md` при параллельном режиме обновляет оркестратор после завершения обоих агентов, чтобы избежать конфликта записи.

#### Code-reviewer, single scope (`Agent`, subagent_type: coder)

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

You are the code-reviewer for Promelectron.

Context:
- task-id: <task-id>
- AGENT_DIR: $AGENT_DIR
- WORKTREE: $WORKTREE
- scope: all
- output: $AGENT_DIR/review/findings.md
- iteration: <N>

Read:
1. .agent/runs/<task-id>/task.md
2. .agent/runs/<task-id>/spec.md
3. .agent/runs/<task-id>/review/findings.md (if this is a re-review)
4. `.agents/agents/code-reviewer.md`
5. [Rule: Security](../../rules/security.md)

Then follow the workflow of `.agents/agents/code-reviewer.md` strictly. Write findings to $AGENT_DIR/review/findings.md.

Do NOT edit source code. Only write findings.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

#### Code-reviewer, mixed (`AgentSwarm`, subagent_type: coder)

items: `["backend", "frontend"]`

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

You are the code-reviewer for Promelectron (focus: {{item}}).

Context:
- task-id: <task-id>
- AGENT_DIR: $AGENT_DIR
- WORKTREE: $WORKTREE
- scope: {{item}}
- output: $AGENT_DIR/review/findings-{{item}}.md
- iteration: <N>

Read:
1. .agent/runs/<task-id>/task.md
2. .agent/runs/<task-id>/spec.md
3. .agent/runs/<task-id>/review/findings-{{item}}.md (if this is a re-review)
4. `.agents/agents/code-reviewer.md`
5. [Rule: Security](../../rules/security.md)

Then follow the workflow of `.agents/agents/code-reviewer.md` strictly. Write findings to $AGENT_DIR/review/findings-{{item}}.md.

Do NOT edit source code. Only write findings.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

#### QA (`Agent`, subagent_type: coder)

> **Перед любым запуском `make test-backend`** (твоим или субагентом): убедись, что нет живых фоновых pytest-процессов от developer-субагентов (`ps aux | grep pytest`); дождись или останови их. Параллельные прогоны ломают общую template database — Rule: Agent Commons > Single Test Run Rule.

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

You are the qa engineer for Promelectron.

Paths:
- AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>
- WORKTREE = $PROJECT_ROOT/.worktrees/<task-id>

Read:
1. .agent/runs/<task-id>/task.md
2. .agent/runs/<task-id>/spec.md
3. .agent/runs/<task-id>/review/findings.md
4. PROJECT_CONTEXT.md
5. docs/backlog.md
6. docs/blockers.md
7. `.agents/agents/qa.md`
8. [Rule: Golden Path](../../rules/golden-path.md)

Then:
1. Run backend tests: make -C "$WORKTREE" test-backend
2. Run frontend unit tests: cd "$WORKTREE/frontend" && npm test
3. If the feature touches UI or user flows, note that E2E is required — the orchestrator runs the e2e-tester separately; do NOT launch it yourself.
4. Verify each Acceptance Criterion from spec.md.
5. Write results to .agent/runs/<task-id>/review/test-findings.md.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

CI уже прогоняет E2E на тестовом окружении (`promelectron-test`) после деплоя.

#### E2E-tester (только от оркестратора; `Agent`, subagent_type: coder)

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

You are the e2e-tester for Promelectron.

Paths:
- AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>
- WORKTREE = $PROJECT_ROOT/.worktrees/<task-id>

Read:
1. .agent/runs/<task-id>/task.md
2. .agent/runs/<task-id>/spec.md (feature scope + Acceptance Criteria)
3. `.agents/agents/e2e-tester.md`
4. [Rule: Golden Path](../../rules/golden-path.md)

Then:
1. Start the dev environment in $WORKTREE (make dev) and verify health checks.
2. Run Playwright for the feature scope: cd "$WORKTREE/frontend" && npx playwright test <feature>.spec.js --workers=1
3. Append E2E results to .agent/runs/<task-id>/review/test-findings.md.

Do NOT edit source code.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

### Step 4.6: Figma design tokens (optional)

MCP-сервер `figma` подключён у Kimi (`.kimi-code/mcp.json`). Если в `spec.md` указан `figma_file_key` (например `figma_file_key: AbC123dEfG`), вытяни design tokens до старта frontend-разработки:

```text
MCP tools:
- figma/get_design_tokens — aggregated summary (colors, typography, spacing)
- figma/get_file — document tree, if screen structure is needed
- figma/get_components — reusable components
```

Сохрани токены как референс для frontend-dev (кратко в `task.md` или отдельным `$AGENT_DIR/design-tokens.md`). Если MCP-сервер недоступен (нет `FIGMA_ACCESS_TOKEN`) — продолжай без него; это не блокер, frontend-dev следует существующим UI-конвенциям проекта.

### Worktree setup

Точная команда создания worktree (в общем файле описано нейтрально):

```bash
git -C "$PROJECT_ROOT" fetch origin
python scripts/implement-pipeline.py create-worktree <task-id>
```

Создаёт `$WORKTREE` на ветке `feature/<task-id>` от `origin/main`; существующий worktree переиспользуется. `create-worktree` также готовит frontend-зависимости автоматически (`npm ci` + контейнерная установка + chown; отключить — `--skip-frontend-prep`, догнать для существующего worktree — `--prepare-frontend`). Скопируй gitignored локальные файлы для сборки (`.env`, `backend/.env`, `frontend/.env`, `.worktreeinclude`).

### Команды общего файла у Kimi

Команды в общем файле названы нейтрально; у Kimi они вызываются как `/skill:<имя>`:
- делегирование PR в ship → `/skill:ship <task-id>`
- dedicated QA gate по флагу `--qa` → `/skill:qa-gate <task-id>`

### Knowledge Capture

Классифицируй уроки задачи (порог: только повторяющиеся или дорогие уроки):

- **doc-worthy** (разовый технический урок) → сразу допиши в `.kimi-code/LESSONS_LEARNED.md` (формат: Ошибка / Причина / Решение / Профилактика).
- **rule-worthy / skill-worthy** → НЕ правь rules/skills сам; перечисли в финальном отчёте как «Proposed pipeline improvements».
- **test-worthy** (сценарий не покрыт тестом) → тест уже должен быть частью реализации; если нет — это блокер для merge.

Если уроков нет — скажи об этом. Trace: `knowledge_captured` (см. таблицу выше).

Также применяй правила AGENTS.md «Обновления после работы»: session-log, backlog, blockers, PROJECT_CONTEXT, пульт.

### Финальный отчёт

1. `python scripts/implement-pipeline.py record-metrics <task-id>` — метрики пайплайна в `.agent/runs/<task-id>/metrics.json`.
2. `python scripts/implement-pipeline.py check-context <task-id>` — финальная оценка токенов.
3. Допиши сводку в `docs/journal/session-log.md` (оценка токенов, число итераций).
4. Отчёт пользователю: Task ID, worktree, ветка, PR URL, изменённые файлы, результаты тестов (backend/frontend/e2e), статус ревью, оценка токенов и итераций, путь к metrics.json, открытые findings/H-items, предложенные улучшения пайплайна.
5. Спроси: **"Merge feature/<task-id> into main and push?"** — без явного одобрения не мержить и не пушить main.
6. После мержа переведи связанный GitHub Issue в Done: `python scripts/implement-pipeline.py set-status <task-id> done`.
