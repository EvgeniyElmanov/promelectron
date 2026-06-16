---
name: implement
description: >
  Full development cycle skill for Promelectron.
  Use for implementing new features, adding pages, creating API endpoints, building Vue components, adding database models, schemas, services, migrations, or any task requiring code changes.
  Runs an architect phase in plan mode, creates a git worktree, develops backend and/or frontend, performs a code review loop (max 3 iterations), an E2E test phase, and reports results.
  Triggers on: implement, feature, add, create, build, develop, new page, new API, endpoint, component, model, schema, migration, page, view.
type: prompt
whenToUse: When the user asks to implement a new feature, page, API endpoint, component, model, schema, migration, or any multi-step code change that would benefit from architect → developer → reviewer → e2e workflow.
arguments: "<task description> [--quick] [--backend-only] [--frontend-only]"
disableModelInvocation: false
---

# /implement — Full Development Cycle

Implement a new feature from idea to tested code using isolated git worktrees, plan-mode architecture, review loops, and E2E tests.

---

## Step 1: Parse and Setup

Extract from the user request:
- Task description (everything before flags)
- Flags: `--quick`, `--backend-only`, `--frontend-only`

Generate `<task-id>`: short kebab-case slug, e.g. `add-promo-codes`, `fix-cart-stock`.

Create directories:
```bash
mkdir -p .agent/<task-id>/review
mkdir -p .worktrees
```

Write `.agent/<task-id>/task.md`:
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

## Step 2: Architect Phase (skip if --quick)

You are the `architect`. Read `.kimi/agents/architect.md` and follow it strictly.

Launch an architect subagent via `Agent` tool with `subagent_type: plan`:

```text
You are the architect for Promelectron.
Read:
1. .agent/<task-id>/task.md
2. PROJECT_CONTEXT.md
3. .agent/BACKLOG.md
4. .agent/BLOCKERS.md
5. .agent/SESSION_LOG.md
6. .kimi/agents/architect.md
7. .kimi/rules/pre-edit-checklist.md

Then:
1. Call EnterPlanMode.
2. Explore the codebase with Read/Grep/Glob to understand how the feature fits.
3. Use WebSearch/FetchURL if you need external documentation, API docs, or library examples.
4. Ask the user clarifying questions via AskUserQuestion if requirements are unclear.
5. Write a technical specification to the plan file returned by EnterPlanMode. Include:
   - Task Type
   - Analysis
   - Decisions (D-01, D-02, ...)
   - Components Affected (backend/frontend/infra)
   - Technical Design
   - API Changes
   - Must-haves
   - Acceptance Criteria
   - Out of Scope
6. Call ExitPlanMode.

Do NOT write implementation code, tests, or migrations.
```

After the user approves the plan, copy the plan file content to `.agent/<task-id>/spec.md`.

If the user rejects or requests revisions, send the architect back to revise the plan.

---

## Step 3: Developer Worktree

Determine which roles are needed from `Components Affected` in the spec:
- Backend → `backend-dev`
- Frontend → `frontend-dev`
- DevOps → `devops`

Order: backend → frontend → devops (if multiple).

For each role, launch a developer subagent via `Agent` tool with `subagent_type: coder`:

```text
You are <ROLE> for Promelectron.
Read:
1. .agent/<task-id>/task.md
2. .agent/<task-id>/spec.md
3. PROJECT_CONTEXT.md
4. .agent/BACKLOG.md
5. .agent/BLOCKERS.md
6. .kimi/agents/<ROLE>.md
7. .kimi/rules/pre-edit-checklist.md

Setup:
1. Create an isolated git worktree:
   git worktree add .worktrees/implement-<task-id> -b feature/<task-id>
2. cd .worktrees/implement-<task-id>
3. Work ONLY inside this directory.

Implement strictly per the spec and your role workflow:
- backend-dev: model → schema → service → route handler → tests
- frontend-dev: API service → composable → component → page → route → tests
- devops: Helm/Docker → CI/CD → verify

Rules:
- Business logic belongs in services, NOT route handlers.
- Every new endpoint must have tests.
- Every model change must have an Alembic migration.
- Use trailing slash in FastAPI endpoints.
- Do NOT commit to main. You may commit to feature/<task-id> in the worktree.

Before finishing:
1. Run the role-specific tests (e.g. cd backend && make test-backend; cd frontend && npm test -- --run).
2. Run lint (ruff / npm run lint).
3. Update .agent/SESSION_LOG.md from the worktree.

Report:
- Changed files
- Test results
- Any blockers
```

If both backend and frontend are needed, run backend first, then frontend in the **same** worktree (they share the feature branch).

---

## Step 4: Code Review Loop (max 3 iterations)

### Each iteration:

1. Launch a reviewer subagent via `Agent` tool with `subagent_type: coder`:

```text
You are the code-reviewer for Promelectron.
Read:
1. .agent/<task-id>/task.md
2. .agent/<task-id>/spec.md
3. .kimi/agents/code-reviewer.md
4. .kimi/rules/security.md

Then:
1. Read the implementation in .worktrees/implement-<task-id>/ (use Read/Grep/Glob in parallel).
2. Compare against the spec and Decisions (D-01, D-02, ...).
3. Check: logic, security, architecture, business rules, tests, golden path impact.
4. Write findings to .agent/<task-id>/review/findings.md using this format:

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
```

2. Read `.agent/<task-id>/review/findings.md`.
3. If `APPROVED` → go to Step 5.
4. If `FIXES_NEEDED`:
   - Show the user a summary of findings.
   - For H-items, wait for user decision.
   - Launch the developer subagent again to fix OPEN findings and mark them FIXED.
   - Repeat review.
5. After 3 iterations still `FIXES_NEEDED` → stop and ask the user how to proceed.

---

## Step 5: E2E Tests

If the feature touches UI or user flows, launch an e2e-tester subagent via `Agent` tool with `subagent_type: coder`:

```text
You are the e2e-tester for Promelectron.
Read:
1. .agent/<task-id>/task.md
2. .agent/<task-id>/spec.md
3. .kimi/agents/e2e-tester.md
4. frontend/playwright.config.js
5. frontend/e2e/global-setup.js

Then:
1. Identify user flows affected by this feature.
2. Check that all new UI elements have data-testid attributes. If not, report it as a finding (do NOT add them yourself unless explicitly allowed).
3. Write or update Playwright tests in frontend/e2e/<feature>.spec.js.
4. Run locally: cd frontend && npx playwright test <feature>.spec.js --workers=1
5. Report results.

You are a user, not a developer. Test through the browser like a real person.
```

CI already runs E2E on the test environment (`promelectron-test`) after deploy.

---

## Step 6: Final Report

After all phases:

1. Read `.agent/SESSION_LOG.md` and append a summary.
2. Report to the user:
   - Task ID
   - Worktree path: `.worktrees/implement-<task-id>`
   - Feature branch: `feature/<task-id>`
   - Changed files
   - Test results (backend, frontend, e2e)
   - Review status
   - Open findings or H-items (if any)
3. Ask: **"Merge feature/<task-id> into main?"** (do NOT merge without explicit approval).

---

## Rules

- NEVER push directly to `main`.
- NEVER delete the worktree until the user approves merge or explicitly asks to clean up.
- Developer marks findings FIXED; reviewer verifies and marks VERIFIED.
- Max 3 review iterations, then escalate to user.
- Update `.agent/SESSION_LOG.md` after every significant phase.
