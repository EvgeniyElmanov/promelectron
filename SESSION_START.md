# SESSION_START — Working with Promelectron agents

> Everything runs through **Kimi Code CLI skills** in `.kimi-code/skills/`.

## Language

When the user communicates in Russian, the main agent and all subagents must perform reasoning, thinking, and internal monologue in Russian. The parent agent must explicitly tell subagents that the original user communicates in Russian. Final replies to the user must be in Russian. Keep code, commands, identifiers, file paths, and technical terms in their original form.

## Contents

1. [Quick start (first time)](#quick-start-first-time)
2. [Daily workflow](#daily-workflow)
3. [Workflow modes](#workflow-modes)
4. [Task format (5 elements)](#task-format-5-elements)
5. [Roles and example tasks](#roles-and-example-tasks)
6. [After a task](#after-a-task)
7. [If something goes wrong](#if-something-goes-wrong)
8. [Useful files](#useful-files)

## Quick start (first time)

### Step 1: Choose a mode

| If you... | Use |
|-----------|-----|
| Don't know the role | [Workflow `/skill:implement`](#mode-a-full-feature-cycle-implement) |
| Need a bug fixed | [Workflow `/skill:fix`](#mode-b-bug-fix-fix) |
| Know the exact role | [Fixed role](#mode-c-fixed-role) |
| Need planning/roadmap | [Project manager](#mode-d-project-manager) |

### Step 2: Load the skill

For any task when you don't know the role:
```
/skill:promelectron
Task: Add promo codes to cart
```

For a full feature cycle:
```
/skill:implement "Add promo codes to cart"
```

For a bug:
```
/skill:fix "Race condition when adding to cart"
```

### Step 3: Follow the subagent

The skill spawns subagents (architect → developer → reviewer → QA). Approve the spec when asked, then let the pipeline run.

## Daily workflow

After loading a workflow skill, just describe tasks:

```
/skill:implement "Add a discount field to orders"
```

```
/skill:fix "Checkout button is disabled on mobile"
```

```
/skill:review
```

The skill routes to the correct subagent automatically.

## Workflow modes

### Mode A: Full feature cycle `/skill:implement`

> For tasks that need design, development, review, and QA.

```
/skill:implement "Add promo codes to cart"
```

How it works:
1. **Architect** — analysis, questions, `spec.md` (plan mode; requires approval)
2. **Git worktree** — `.worktrees/implement-<task-id>` on branch `feature/<task-id>`
3. **Backend dev** — model → schema → service → route → tests
4. **Frontend dev** — API → composable → component → page → tests
5. **Code review** — max 3 iterations
6. **QA / E2E** — pytest + vitest + Playwright
7. **Report** — merge only with explicit approval

Flags:
- `--quick` — skip architect/spec phase
- `--backend-only` — backend only
- `--frontend-only` — frontend only

### Mode B: Bug fix `/skill:fix`

> For bugs: analyze → reproduce → fix → test.

```
/skill:fix "Race condition in cart add"
```

How it works:
1. Determines role from description
2. Reads context and recent git log
3. Reproduces the bug (writes a minimal test)
4. Fixes the cause, not the symptom
5. Runs tests
6. Checks golden path if touched

Flags:
- `--backend` — explicitly backend bug
- `--frontend` — explicitly frontend bug
- `--infra` — infrastructure bug

### Mode C: Fixed role

> If you work in one role all day.

```
Role: backend-dev. Task: add email validation to registration.

Read PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md, SESSION_LOG.md.
Load `/skill:backend-dev` or read `.kimi-code/skills/backend-dev/SKILL.md` and `.kimi-code/rules/pre-edit-checklist.md`.
After work update SESSION_LOG.md.
```

### Mode D: Project manager

> For planning, priorities, and roadmap.

```
Role: project-manager. Task: prioritize backlog for next sprint.
```

## Working through the terminal

Useful `make` commands:

```bash
make check       # lint + test
make status      # git + services
make dev         # start the stack
make stop        # stop the stack
make test-backend
make test-frontend
make test-e2e
```

## Task format (5 elements)

The more specific the task, the better the result.

```
[ROLE] Task: [one sentence]
File: [specific file or zone]
Related: [related files that will also change]
Do not break: [boundaries]
Verify: [how to confirm it works]
```

### Examples

**Backend:**
```
[backend-dev] Task: add promo_code field to Order model
File: backend/src/app/models/order.py
Related: backend/src/app/schemas/order.py, backend/src/app/services/order_service.py
Do not break: existing migrations, payments table
Verify: pytest tests/test_orders.py && ruff check backend/src/app/models/order.py
```

**Frontend:**
```
[frontend-dev] Task: add promo code input to Cart.vue
File: frontend/src/views/Cart.vue
Related: frontend/src/services/cart.js, frontend/src/stores/cart.js
Do not break: existing total calculation, mobile layout
Verify: npm run test:unit Cart && check responsiveness (375px)
```

More details in `.kimi-code/rules/prompt-format.md`.

## Roles and example tasks

| Role | Keywords | Typical task | Example |
|------|----------|--------------|---------|
| `backend-dev` | API, model, migration, service, endpoint, FastAPI, SQLAlchemy, pytest | Backend models, schemas, services, routes, tests | "Add POST /promo/apply endpoint" |
| `frontend-dev` | Vue, component, page, form, Pinia, UI, CSS | Components, stores, composables, tests | "Add promo input in Cart.vue" |
| `devops` | Docker, Helm, K8s, CI/CD, deploy, nginx, secret | Helm, Docker, CI/CD | "Add migration check to deploy.yml" |
| `e2e-tester` | E2E, Playwright, test scenario, browser, click | Playwright tests | "Write checkout test with test card" |
| `code-reviewer` | review, code review, findings, quality | Code review | "Review PR #42" |
| `security-reviewer` | security, audit, vulnerability, SQL injection | Security audit | "Audit API for SQL injection" |
| `project-manager` | plan, sprint, prioritize, backlog, estimate | Planning, priorities, roadmap | "Estimate YooKassa integration timeline" |
| `architect` | design, architecture, spec, technical task, trade-off | Feature design | "Design delivery integration" |
| `qa` | test, acceptance criteria, full check, qa | Full verification | "Check feature/X branch before merge" |

## After a task

Agents update:

1. `.agent/SESSION_LOG.md` — what was done, files changed, risks
2. `.agent/BACKLOG.md` — task status (if from sprint)
3. `.agent/BLOCKERS.md` — new blockers (if any)
4. `PROJECT_CONTEXT.md` — if architecture changed

Before reporting:
- [ ] Tests pass (`make test`)
- [ ] Lint is clean (`make lint`)
- [ ] Critical paths from `.kimi-code/rules/golden-path.md` are not broken

## If something goes wrong

### The agent is not following the expected role

1. Reload the workflow skill: `/skill:implement ...` or `/skill:fix ...`
2. Start a new Kimi CLI session
3. Explicitly specify the role: `Role: frontend-dev. Task: ...`

### You want two independent tasks at once

Don't write: "Create API and fix Helm"

Write two messages:
```
Task: create API for X
```
```
Task: fix Helm template for Y
```

## Useful files

| File | When to read |
|------|--------------|
| `.kimi-code/rules/prompt-format.md` | Before formulating a task |
| `.kimi-code/rules/pre-edit-checklist.md` | Before editing code |
| `.kimi-code/rules/dependency-map.md` | Before changing a file |
| `.kimi-code/rules/golden-path.md` | Before finishing |
| `.kimi-code/rules/task-template.md` | When creating a new backlog item |
| `.kimi-code/skills/<role>/SKILL.md` | When working in a fixed role |
| `.kimi-code/AGENTS.md` | Active index of project invariants and agent system overview |
| `ROUTER.md` | Routing documentation |
| `PROJECT_CONTEXT.md` | At session start — stack, status, blockers |
| `.agent/BACKLOG.md` | At session start — current sprint |
| `.agent/BLOCKERS.md` | At session start — active blockers |
