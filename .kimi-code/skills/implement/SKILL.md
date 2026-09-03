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

# /skill:implement — Full Development Cycle

Implement a new feature from idea to tested code using isolated git worktrees, plan-mode architecture, review loops, and E2E tests.

## Language

Follow [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule. All Russian-language requirements and subagent prompt preambles live there.

Also: write `task.md`, `spec.md`, findings, reports, and `SESSION_LOG.md` entries in Russian when the user is Russian.

---

## Step 1: Parse and Setup

Extract from the user request:
- Task description (everything before flags)
- Flags: `--quick`, `--backend-only`, `--frontend-only`, `--serial`, `--qa`

Check GitHub CLI access — backlog automation depends on it:

```bash
gh auth status
gh project view 1 --owner AutonomaCo
```

If either fails — stop and ask the user to run `gh auth login` or grant the `project` scope.

Generate `<task-id>`: short kebab-case slug, e.g. `add-promo-codes`, `fix-cart-stock`.

Record the repo root:

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
```

Paths for the rest of the pipeline:

```text
AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>       (gitignored coordination plane)
WORKTREE  = $PROJECT_ROOT/.worktrees/<task-id>        (per-task code checkout)
BRANCH    = feature/<task-id>
```

Create directories:
```bash
mkdir -p "$PROJECT_ROOT/.agent/runs/<task-id>/review"
mkdir -p "$PROJECT_ROOT/.worktrees"
```

> **Important:** `.agent/runs/<task-id>/` is gitignored. Never write transient pipeline files into the committed `.agent/` planning dir (`BACKLOG.md`, `PLANNING_HANDOFF.md`, `tasks/`, etc.).

Write `$AGENT_DIR/task.md` by the template from [Rule: Task Template](../../rules/task-template.md). Set `github_issue` if the task already has one:
```markdown
# Task: <task-id>

## Description
<full task description>

## Flags
<active flags or "none">

## Date
<YYYY-MM-DD>
```

---

## Step 1b: Context Size Check (Kimi K3)

Follow [Rule: Agent Commons](../../rules/agent-commons.md) > Context Size Check before launching subagents.

---

## Step 1c: Retry Policy

Follow [Rule: Agent Commons](../../rules/agent-commons.md) > Retry Policy when launching subagents.

---

## Step 1d: Observability — phase-boundary trace

At every phase boundary, append an event to the task's append-only trace (a single correlation ID per task is created automatically on the first event):

```bash
python3 scripts/agent_state.py trace <task-id> <event> --actor <actor> --data '{"key": "value"}'
```

Required events:

| Moment | event | actor |
|--------|-------|-------|
| task.md created | `task_created` | orchestrator |
| spec approved by user | `spec_approved` | orchestrator |
| plan created | `plan_created` | orchestrator |
| plan auto-approved | `plan_auto_approved` | orchestrator |
| plan approved by human | `plan_human_approved` | human |
| plan revised | `plan_revised` | orchestrator |
| developer(s) reported done | `dev_done` | backend-dev / frontend-dev |
| review verdict (each iteration) | `review_verdict` | code-reviewer (data: `{"iteration": N, "verdict": "..."}`) |
| QA gate finished | `qa_done` | qa (data: `{"status": "TESTS_PASSED|TESTS_FAILED"}`) |
| PR opened | `pr_opened` | orchestrator (data: `{"url": "..."}`) |
| Knowledge capture | `knowledge_captured` | orchestrator (data: `{"rules": N, "skills": N, "docs": N}`) |

The trace must never block the pipeline: if the command fails — continue and mention it in the final report.

---

## Step 2: Architect Phase (skip if --quick)

You are the `architect`. Read `.kimi-code/skills/architect/SKILL.md` and follow it strictly.

### Research fan-out (parallel, optional)

For non-trivial tasks, launch read-only research subagents in parallel via `AgentSwarm` with `subagent_type: explore` — one per axis (libraries, best-practices, codebase integration) — each writes `$AGENT_DIR/research/<axis>.md`. Skip for small internal changes.

Launch an architect subagent via `Agent` tool with `subagent_type: plan`. Apply the retry policy from Step 1c:

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

You are the architect for Promelectron.
Important: Kimi K3 uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.
Read:
1. .agent/runs/<task-id>/task.md
2. .agent/runs/<task-id>/research/*.md (if present) — synthesize into .agent/runs/<task-id>/research.md
3. PROJECT_CONTEXT.md
4. .agent/BACKLOG.md
5. .agent/BLOCKERS.md
6. .agent/SESSION_LOG.md
7. `.kimi-code/skills/architect/SKILL.md`
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

---

## Step 3: Spec Approval (skip if --quick)

After the user approves the plan, copy the plan file content to `$AGENT_DIR/spec.md`.

If the user rejects or requests revisions, send the architect back to revise the plan.

---

## Step 3.5: Занять пункт на пульте запуска

**До** создания worktree. Пульт `ai-launcher/BOARD.md` — то, чем две сессии (Claude и Kimi)
разводятся между собой, чтобы не взять одну и ту же работу и не переписать одни и те же файлы.

1. Определи **замки** пункта по файлам, которые задача трогает. Таблица — `ai-launcher/CONVENTIONS.md`
   §2. Бери **все** замки, которых касается работа, а не только основной.
2. **Замок уже занят другим пунктом в «🔵 В работе» — остановись** и скажи пользователю. Не
   «аккуратно рядом»: это единственный способ не разгребать конфликты в чужой ветке.
3. Переведи пункт в 🔵, добавь строку в «🔵 В работе» (issue, замки, ветка `feature/<task-id>`),
   пересчитай блок «🔒 Замки».
4. Пульт правится **только в корне репозитория на `main`**, поимённо, никогда не из worktree:
   ```bash
   git -C "$PROJECT_ROOT" add ai-launcher/BOARD.md
   ```
   Перед коммитом прогони проверку формы из `ai-launcher/CONVENTIONS.md` §3.

Задача из свободного текста без issue — пункта на борде нет, шаг пропускается; скажи один раз,
что работа невидима для `/skill:board` и `/skill:sessions`, пока issue не заведён.

---

## Step 4: Worktree Setup

Create the isolated worktree before any agent touches the code:

```bash
git -C "$PROJECT_ROOT" fetch origin
python scripts/implement-pipeline.py create-worktree <task-id>
```

This creates `$WORKTREE` on branch `feature/<task-id>` from `origin/main`. If the worktree already exists, reuse it. `create-worktree` also prepares frontend dependencies automatically (`npm ci` + containerised install + chown; disable with `--skip-frontend-prep`, re-run for an existing worktree with `--prepare-frontend`). Copy gitignored local files needed for the build (`.env`, `backend/.env`, `frontend/.env`, `.worktreeinclude`).

---

## Step 4.5: GitHub Issue Linking (before development)

Per AGENTS.md, ALWAYS link a GitHub Issue before development starts and move the Project board on phase boundaries.

1. Check for an existing `github_issue` in `$AGENT_DIR/task.md`. If present — reuse it; never create a duplicate issue for the same task-id.
2. If missing — draft an issue from the spec/task description, confirm it with the user via `AskUserQuestion`, then run:
   ```bash
   python scripts/implement-pipeline.py create-issue <task-id> --status in-progress
   ```
3. Once the spec is approved, make sure the board status is `In progress`:
   ```bash
   python scripts/implement-pipeline.py set-status <task-id> in-progress
   ```

---

## Step 4.6: Figma design tokens (optional)

If `spec.md` specifies a `figma_file_key` (e.g. `figma_file_key: AbC123dEfG`), use the `figma` MCP server to pull design tokens before frontend development starts:

```text
MCP tools:
- figma/get_design_tokens — aggregated summary (colors, typography, spacing)
- figma/get_file — document tree, if screen structure is needed
- figma/get_components — reusable components
```

Save the extracted tokens as a reference for the frontend-dev agent (briefly in `task.md` or as a separate `$AGENT_DIR/design-tokens.md`).

If the MCP server is unavailable (no `FIGMA_ACCESS_TOKEN`) — continue without it; this is not a blocker. Frontend-dev should then follow the existing UI conventions of the project.

---

## Step 5: Developer Phase — plan → approve → execute

Determine which roles are needed from `Components Affected` in the spec:
- Backend → `backend-dev`
- Frontend → `frontend-dev`
- DevOps → `devops`

Development is split into three phases: **Plan → Approve → Execute**. A developer agent **does not write code without an approved plan**.

Режим запуска (одинаков для фаз Plan и Execute):

- `--backend-only` / `--frontend-only` — запусти только эту одну роль (параллелизм не нужен).
- `--serial` — последовательно: backend → frontend → devops (старое поведение).
- По умолчанию (нужны и backend, и frontend) — запусти `backend-dev` и `frontend-dev` **параллельно**: два раздельных вызова `Agent` в одном сообщении (промпты разношёрстные, поэтому два вызова, а не один `AgentSwarm` с `{{item}}`). `devops`, если нужен, запускай после их завершения.

### Step 5a: Plan — developer writes PLAN.md

Launch the required roles with the task to **only write a plan**, without changing code. Each role creates `$WORKTREE/PLAN.md` (a single shared one if serial; one per side — e.g. `PLAN.backend.md` / `PLAN.frontend.md` — if parallel). If the feature touches both backend and frontend, two independent plans are written.

Use the same prompt as for execution (Step 5c), but prepend:

```text
=== PHASE A: PLAN ONLY — DO NOT WRITE CODE ===

Перед кодированием напиши $WORKTREE/PLAN.md (или $WORKTREE/PLAN.<role>.md при параллельном запуске) по spec. Следуй секции «План перед кодированием (PLAN.md)» своего ролевого SKILL.md.

PLAN.md должен содержать:
1. Goal — одно предложение.
2. Steps — нумерованный список шагов: что меняется, в каком порядке, проверка после каждого шага.
3. Risks / Open questions — что может пойти не так.

Не редактируй production-код, не создавай миграций, не трогай frontend/backend.
После написания PLAN.md остановись и сообщи: «PLAN.md готов».
```

After all roles finish, read `$WORKTREE/PLAN.md` (and the per-side plans, if split).

### Step 5b: Approve — auto or human

The orchestrator evaluates the plan(s) against the **auto-approve** criteria. A plan is auto-approved if **all** conditions hold:

1. Only one side is affected OR backend and frontend have independent plans without cross-dependencies.
2. ≤ 5 Must-haves / Acceptance Criteria in the spec.
3. ≤ 4 major steps in the plan.
4. No auth / payments / PII / uploads / orders / webhooks (extended security scope).
5. No external integrations (1C, YooKassa, CDEK, Telegram, external APIs).
6. All risks are marked LOW or a standard rollback is described.

Log the trace:

```bash
python3 scripts/agent_state.py trace <task-id> plan_created --actor orchestrator
python3 scripts/agent_state.py trace <task-id> plan_auto_approved --actor orchestrator
# or
python3 scripts/agent_state.py trace <task-id> plan_human_approved --actor human --data '{"reason": "..."}'
# on revision
python3 scripts/agent_state.py trace <task-id> plan_revised --actor orchestrator
```

If the plan is auto-approved — proceed to Step 5c.

If **any** criterion fails — show the user a brief summary of PLAN.md (Goal, Steps, Risks) and ask: **«одобрить план / доработать?»**. On revision go back to Step 5a. On approval proceed to Step 5c.

> **Don't skimp on human approval:** if the plan touches money, security, public API, or critical infrastructure — always show it to the user, even if it formally passes auto-approve.

### Step 5c: Execute — implement the approved plan

For each role, launch a developer subagent via `Agent` tool with `subagent_type: coder` (при параллельном режиме — оба вызова `Agent` в одном сообщении). Apply the retry policy from Step 1c:

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

You are <ROLE> for Promelectron.
Important: Kimi K3 uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.

Paths:
- AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>
- WORKTREE = $PROJECT_ROOT/.worktrees/<task-id>
- BRANCH = feature/<task-id>

Read:
1. .agent/runs/<task-id>/task.md
2. .agent/runs/<task-id>/spec.md
3. $WORKTREE/PLAN.md — одобренный план, реализуй строго по нему
4. PROJECT_CONTEXT.md
5. .agent/BACKLOG.md
6. .agent/BLOCKERS.md
7. `.kimi-code/skills/<ROLE>/SKILL.md`
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
3. Update .agent/SESSION_LOG.md from the worktree (при параллельном запуске backend+frontend это делает оркестратор — пропусти).

Report:
- Changed files
- Test results
- Any deviations from PLAN.md (must be re-approved)
- Any blockers

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

При параллельном запуске оба агента работают в **одном** worktree `.worktrees/<task-id>` (общая feature-ветка), но не пересекаются по файлам благодаря scope boundary. `.agent/SESSION_LOG.md` при параллельном режиме обновляет оркестратор после завершения обоих агентов, чтобы избежать конфликта записи.

> **Rate limits:** при большом fan-out или повторяющихся 429 установи `KIMI_CODE_AGENT_SWARM_MAX_CONCURRENCY=2` (env var, см. Kimi Code CLI v0.18.0+), чтобы параллельные субагенты не упирались в provider rate limits.

---

## Step 5.5: API Contract Validation (backend ↔ frontend)

Skip if the feature touches only backend or only frontend. Otherwise — **before launching reviewer subagents** the orchestrator personally verifies that backend and frontend converged on the contract from `$AGENT_DIR/spec.md`:

1. Extract changed/new endpoints from the backend diff:
   ```bash
   git -C "$WORKTREE" --no-pager diff origin/main...HEAD -- 'backend/src/app/api/*.py' | grep -E '^\+.*@(router|.*)\.(get|post|put|patch|delete)'
   ```
2. Extract API calls from the frontend diff:
   ```bash
   git -C "$WORKTREE" --no-pager diff origin/main...HEAD -- 'frontend/src/api/*' | grep -E '^\+.*(get|post|put|patch|delete)\('
   ```
3. Check every endpoint from the spec's `API Changes`:
   - **path** matches, including **trailing slash** (`/items/`, not `/items`)
   - **HTTP method** matches
   - **request fields** (body/params/query) match the Pydantic schema
   - **response fields** the frontend actually reads are present in the response schema
4. On any mismatch — record it in `$AGENT_DIR/review/findings.md` as `[F-xxx] CRITICAL | API Contract` with status `OPEN` and send the respective developer subagent back to fix it **before** Step 6.
5. No mismatches — proceed to Step 6.

This step catches the "backend and frontend diverged on the contract in parallel" class of bugs, which is cheaper to fix before review than after it.

---

## Step 6: Code Review Loop (max 3 iterations)

### Determine review scope

Based on the spec and flags (`--backend-only`, `--frontend-only`):

- **Backend only or frontend only** → run one reviewer subagent.
- **Mixed (backend + frontend)** → run two reviewer subagents in parallel via `AgentSwarm`.
- **Security-sensitive work** (auth, payments, orders) → add `security-reviewer` to the parallel batch.

### Single-component review

Launch one reviewer subagent via `Agent` tool with `subagent_type: coder`. Apply the retry policy from Step 1c:

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

You are the code-reviewer for Promelectron.
Important: Kimi K3 uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.

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
4. `.kimi-code/skills/code-reviewer/SKILL.md`
5. [Rule: Security](../../rules/security.md)

Then follow the workflow of `.kimi-code/skills/code-reviewer/SKILL.md` strictly. Write findings to $AGENT_DIR/review/findings.md.

Do NOT edit source code. Only write findings.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

### Mixed review (backend + frontend in parallel)

Launch reviewer subagents via `AgentSwarm` tool with `subagent_type: coder`. Apply the retry policy from Step 1c:

items: `["backend", "frontend"]`

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

You are the code-reviewer for Promelectron (focus: {{item}}).
Important: Kimi K3 uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.

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
4. `.kimi-code/skills/code-reviewer/SKILL.md`
5. [Rule: Security](../../rules/security.md)

Then follow the workflow of `.kimi-code/skills/code-reviewer/SKILL.md` strictly. Write findings to $AGENT_DIR/review/findings-{{item}}.md.

Do NOT edit source code. Only write findings.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

**After `AgentSwarm` returns:**
1. Read `.agent/runs/<task-id>/review/findings-backend.md` and `.agent/runs/<task-id>/review/findings-frontend.md`.
2. Merge them into `.agent/runs/<task-id>/review/findings.md`:
   - Overall **Status** is `FIXES_NEEDED` if any sub-report is `FIXES_NEEDED`; otherwise `APPROVED`.
   - Preserve **Iteration** number.
   - Combine findings lists; renumber if needed so IDs are unique across backend and frontend.
   - Preserve Human Decisions from both reports.
3. Delete the temporary `findings-backend.md` and `findings-frontend.md` or keep them for debugging.

### Review loop continuation

1. Read `.agent/runs/<task-id>/review/findings.md`.
2. If `APPROVED` → go to Step 7.
3. If `FIXES_NEEDED`:
   - Show the user a summary of findings.
   - For H-items, wait for user decision.
   - Launch the developer subagent again to fix OPEN findings and mark them FIXED.
   - **Before repeating review, re-run the relevant tests** (backend: `make -C "$WORKTREE" test-backend`; frontend: `cd "$WORKTREE/frontend" && npm test`). If tests fail, fix them first.
   - Repeat review. The reviewer verifies FIXED items and marks them `VERIFIED`; if not fixed — reopens as `OPEN` with an explanation.
4. After 3 iterations still `FIXES_NEEDED` → stop and ask the user how to proceed.

---

## Step 7: QA / Test Pyramid

> **Before any `make test-backend` run** (yours or a subagent's): make sure there are no live background pytest processes from developer subagents (`ps aux | grep pytest`); wait for or stop them. Parallel runs break the shared template database — see [Rule: Agent Commons](../../rules/agent-commons.md) > Single Test Run Rule.

After code review passes, launch a `qa` subagent via `Agent` tool with `subagent_type: coder`. Apply the retry policy from Step 1c:

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

You are the qa engineer for Promelectron.
Important: Kimi K3 uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.

Paths:
- AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>
- WORKTREE = $PROJECT_ROOT/.worktrees/<task-id>

Read:
1. .agent/runs/<task-id>/task.md
2. .agent/runs/<task-id>/spec.md
3. .agent/runs/<task-id>/review/findings.md
4. PROJECT_CONTEXT.md
5. .agent/BACKLOG.md
6. .agent/BLOCKERS.md
7. `.kimi-code/skills/qa/SKILL.md`
8. [Rule: Golden Path](../../rules/golden-path.md)

Then:
1. Run backend tests: make -C "$WORKTREE" test-backend
2. Run frontend unit tests: cd "$WORKTREE/frontend" && npm test
3. If the feature touches UI or user flows, note that E2E is required — the orchestrator runs the e2e-tester separately in Step 7.5; do NOT launch it yourself.
4. Verify each Acceptance Criterion from spec.md.
5. Write results to .agent/runs/<task-id>/review/test-findings.md.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

CI already runs E2E on the test environment (`promelectron-test`) after deploy.

---

## Step 7.5: E2E Tester (optional, launched by the orchestrator)

If the feature touches UI/user flows and the unit-test results are OK, launch an `e2e-tester` subagent **from the main agent** via `Agent` tool with `subagent_type: coder`. Subagents cannot spawn nested subagents — never launch the e2e-tester from inside the qa subagent.

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

You are the e2e-tester for Promelectron.

Paths:
- AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>
- WORKTREE = $PROJECT_ROOT/.worktrees/<task-id>

Read:
1. .agent/runs/<task-id>/task.md
2. .agent/runs/<task-id>/spec.md (feature scope + Acceptance Criteria)
3. `.kimi-code/skills/e2e-tester/SKILL.md`
4. [Rule: Golden Path](../../rules/golden-path.md)

Then:
1. Start the dev environment in $WORKTREE (make dev) and verify health checks.
2. Run Playwright for the feature scope: cd "$WORKTREE/frontend" && npx playwright test <feature>.spec.js --workers=1
3. Append E2E results to .agent/runs/<task-id>/review/test-findings.md.

Do NOT edit source code.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

If `test-findings.md` status is `TESTS_FAILED`, show the failures, call the affected developer to fix them, then go back to Step 6 (code changed → re-review). Max 2 QA/E2E iterations, then escalate to the user.

---

## Step 7.6: Dedicated QA Gate (только с флагом `--qa`)

Если передан флаг `--qa`, перед открытием PR обязательно запусти standalone QA gate:

```
/skill:qa-gate <task-id>
```

Он находит coordination plane и worktree задачи и прогоняет полную QA-проверку (pytest + vitest + Playwright) по Acceptance Criteria из spec.md. Если gate падает — исправь найденное и повтори; не открывай PR с красным QA gate.

---

## Step 8: Pull Request

Delegate PR creation to `/skill:ship` — it runs `make pre-push`, pushes `feature/<task-id>`, creates the PR via `gh pr create`, posts open `[H-xxx]` items from `$AGENT_DIR/review/findings.md` as PR comments, and moves the board status to `In review`:

```
/skill:ship <task-id>
```

If ship fails (e.g. pre-push checks are red), stop and report the error — never open a PR with failing checks.

---


### Пульт: вернуть замок

После открытия PR пункт остаётся 🔵 со своим номером PR — именно это держит замок честным.
**После мержа** строка уходит из «🔵 В работе», блок с кнопкой удаляется, блок «🔒 Замки»
пересчитывается. Правится в корне репозитория, не в worktree.

⚠️ Если у пункта есть строка в «⏰ Ждут условия» — **смержено ≠ проверено**: строка остаётся,
пока условие не наступило и проверка реально не проведена. Скажи об этом вслух, а не закрывай
пункт молча: это ровно тот хвост, который теряется.

---

## Step 8.5: Knowledge Capture

Classify the lessons from this task (threshold: only recurring or expensive lessons):

- **doc-worthy** (one-off technical lesson) → append it to `.kimi-code/LESSONS_LEARNED.md` right away (format: Ошибка / Причина / Решение / Профилактика).
- **rule-worthy / skill-worthy** → do NOT edit rules or skills yourself; list them in the final report as "Proposed pipeline improvements".
- **test-worthy** (no test covers this scenario) → the test must already be part of the implementation (Step 5); if not, it is a blocker for merge.

If no lessons were identified, say so.

Log the trace: `python3 scripts/agent_state.py trace <task-id> knowledge_captured --actor orchestrator --data '{"rules": N, "skills": N, "docs": N}'`.

Also apply the AGENTS.md "Обновления после работы" rules:
1. Update `.agent/SESSION_LOG.md`.
2. Update `.agent/BACKLOG.md` if the task is from the sprint.
3. Update `.agent/BLOCKERS.md` if a new blocker appeared.
4. Update `PROJECT_CONTEXT.md` if the architecture changed.

---

## Step 9: Final Report

After all phases:

1. Run `python scripts/implement-pipeline.py record-metrics <task-id>` to collect and save pipeline metrics to `.agent/runs/<task-id>/metrics.json`.
2. Run `python scripts/implement-pipeline.py check-context <task-id>` to capture final estimated tokens.
3. Read `.agent/SESSION_LOG.md` and append a summary including estimated tokens and iteration count.
4. Report to the user:
   - Task ID
   - Worktree path: `.worktrees/<task-id>`
   - Feature branch: `feature/<task-id>`
   - PR URL (if created)
   - Changed files
   - Test results (backend, frontend, e2e)
   - Review status
   - Estimated tokens and iteration count
   - Path to `.agent/runs/<task-id>/metrics.json`
   - Open findings or H-items (if any)
   - Proposed pipeline improvements from Step 8.5 (if any)
5. Ask: **"Merge feature/<task-id> into main and push?"** (do NOT merge or push main without explicit approval).
6. If the merge is done, move the linked GitHub Issue to **Done**:
   ```bash
   python scripts/implement-pipeline.py set-status <task-id> done
   ```

---

## Rules

- NEVER push directly to `main`.
- NEVER merge automatically — a human reviews and merges.
- NEVER delete the worktree until the user approves merge or explicitly asks to clean up.
- ALWAYS link a GitHub Issue before development (Step 4.5) and move the Project board on phase boundaries: spec approved → In progress, PR open → In review, merged → Done.
- Developer marks findings FIXED; reviewer verifies and marks VERIFIED.
- Max 3 review iterations, then escalate to user.
- Max 2 QA iterations, then escalate to user.
- Update `.agent/SESSION_LOG.md` after every significant phase.
- Always write transient pipeline files to `.agent/runs/<task-id>/`, never to the committed `.agent/` planning dir.
- **Idempotency:** never create a duplicate issue for the same `task-id`; reuse `github_issue` from `task.md`.
- **No silent publish:** always ask the user before creating a GitHub Issue.
