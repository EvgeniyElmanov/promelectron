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

Implement a new feature from idea to tested code using isolated git worktrees, plan-mode architecture, review loops, E2E tests, and a GitHub Pull Request.

## Language

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule. All Russian-language requirements and subagent prompt preambles live there.

Also: write `task.md`, `spec.md`, findings, reports, and `SESSION_LOG.md` entries in Russian when the user is Russian.

---

## Step 0: Setup — coordination plane and worktree

Record the repo root once:

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
```

### 0.1 Pre-flight checks

Verify GitHub CLI access before starting — backlog automation depends on it:

```bash
gh auth status
gh project view 1 --owner AutonomaCo
```

If either fails, stop and ask the user to run `gh auth login` or grant `project` scope.

Generate `<task-id>`: short kebab-case slug, e.g. `add-promo-codes`, `fix-cart-stock`.

Create the transient coordination plane and the worktree root:

```bash
mkdir -p "$PROJECT_ROOT/.agent/runs/<task-id>/review"
mkdir -p "$PROJECT_ROOT/.worktrees"
```

Paths for the rest of the pipeline:

```text
AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>       (gitignored coordination plane)
WORKTREE  = $PROJECT_ROOT/.worktrees/<task-id>        (per-task code checkout)
BRANCH    = feature/<task-id>
```

> **Important:** `.agent/runs/<task-id>/` is gitignored. Never write transient pipeline files into the committed `.agent/` planning dir (`BACKLOG.md`, `PLANNING_HANDOFF.md`, `tasks/`, etc.).

Write `$AGENT_DIR/task.md`:

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

## Step 1: Create the isolated worktree

Do this **before** any agent touches code, in normal (non-plan) mode — `git worktree add` is a disk mutation plan mode blocks.

```bash
git -C "$PROJECT_ROOT" fetch origin
git -C "$PROJECT_ROOT" worktree add "$WORKTREE" -b "$BRANCH" origin/main
```

- **Always branch from `origin/main`.** Never from the current branch.
- If the worktree already exists (re-run), reuse it — check `git -C "$PROJECT_ROOT" worktree list`.
- A worktree is a fresh checkout: copy gitignored local files the build needs. Honor `.worktreeinclude` if present, else copy `.env` / `backend/.env` / `frontend/.env` when they exist.

You may use the helper script:

```bash
python scripts/implement-pipeline.py setup "<description>" --flags "<flags>"
python scripts/implement-pipeline.py create-worktree <task-id>
```

---

## Step 2: Context Size Check (Kimi K2.7-Code)

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Context Size Check before launching subagents.

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

If `ESTIMATED_TOKENS >= 180000`, read `$AGENT_DIR/CONTEXT_SUMMARY.md` instead of the full history.

---

## Step 3: Retry Policy

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Retry Policy when launching subagents.

---

## Step 4: Architect Phase (skip if --quick)

The spec is written by the **`architect` agent** — you (the orchestrator) only drive the loop and talk to the user. Do not write the spec yourself.

### 4.1 Research fan-out (parallel, optional)

For non-trivial tasks, launch read-only research sub-agents (`coder` with read-only instructions) concurrently in a single message — one per axis that applies (libraries, best-practices, codebase integration) — each writing `$AGENT_DIR/research/<axis>.md`. Skip for small internal changes.

### 4.2 Invoke the architect

Launch an architect subagent via `Agent` tool with `subagent_type: plan`. Apply the retry policy from Step 3.

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

You are the architect for Promelectron.
Important: Kimi K2.7-Code uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.

Read:
1. $AGENT_DIR/task.md
2. $AGENT_DIR/research/*.md (if present) and synthesize into $AGENT_DIR/research.md
3. PROJECT_CONTEXT.md
4. .agent/BACKLOG.md
5. .agent/BLOCKERS.md
6. .agent/SESSION_LOG.md
7. `.kimi-code/skills/architect/SKILL.md`
8. [Rule: Pre-edit Checklist](.kimi-code/rules/pre-edit-checklist.md)

Ты уже запущен как `plan`-субагент — контекст plan уже отключает shell и включает планирование, поэтому НЕ вызывай EnterPlanMode повторно. Пиши спецификацию прямо в plan-файл, предоставленный контекстом plan-субагента, затем вызови ExitPlanMode.

Then:
1. Load as much relevant context as possible in **parallel**: read task files, existing code in $WORKTREE, and external docs/WebSearch results simultaneously.
2. Explore the codebase with Read/Grep/Glob (run multiple reads/searches in parallel) to understand how the feature fits.
3. Use WebSearch/FetchURL if you need external documentation, API docs, or library examples.
4. Ask the user clarifying questions via AskUserQuestion if requirements are unclear.
5. Write a technical specification to the plan file. Include:
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

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

### 4.3 Copy the plan to the coordination plane

After the user approves the plan, copy the plan file content to `$AGENT_DIR/spec.md`.

If the user rejects or requests revisions, send the architect back to revise the plan.

---

## Step 4.5: Publish to GitHub backlog

Every task entering development MUST have a linked GitHub Issue on the Promelectron project board. This step runs **after spec approval** and **before any developer subagent**.

### 4.5.1 Check for existing issue

Read `$AGENT_DIR/task.md`:

- If it already contains `github_issue: #N` (e.g. user invoked `/skill:implement #5`) → skip creation, only ensure the issue status is **In progress**.
- Otherwise → create a new issue.

### 4.5.2 Build issue draft from spec

Use `$AGENT_DIR/spec.md` to build a concise issue:

- **Title:** max 120 chars, derived from the task description or spec heading.
- **Body:** Summary, Must-haves, Acceptance Criteria, Out of Scope, plus link to `.agent/runs/<task-id>/spec.md`.

### 4.5.3 Confirm with user

Show the draft title/body via `AskUserQuestion`:

> "Spec approved. I will create/link GitHub Issue and move it to **In progress** on the board. Proceed?"

Wait for explicit approval before publishing.

### 4.5.4 Create/link issue and project item

Use the helper script:

```bash
python scripts/implement-pipeline.py create-issue <task-id> --status in-progress
```

This command:
- Creates or updates the GitHub Issue via `gh issue create` / `gh issue edit`.
- Adds the issue to the GitHub Project board.
- Sets the project status to `In progress`.
- Writes `github_issue` / `issue_url` back to `task.md` and `spec.md`.
- Appends a linked row to `.agent/BACKLOG.md`.

Capture the printed values:

```text
ISSUE_URL=https://github.com/AutonomaCo/promelectron/issues/N
ISSUE_NUMBER=N
STATUS=in-progress
```

### 4.5.5 On failure

If `gh issue create` or project update fails:
- Report the exact error to the user.
- Do NOT start development until the issue is linked.
- Escalate if `gh auth` scope is missing.

---

## Step 5: Development — PARALLEL by default

Read `Components Affected` and `Parallelization Plan` from `$AGENT_DIR/spec.md`. All code work targets `WORKTREE` (use `git -C`, `make -C`, explicit paths — a sub-agent's `cd` does not persist).

**If both backend and frontend are affected, independent, and neither `--backend-only`/`--frontend-only`/`--serial` is set:**
Launch `backend-dev` and `frontend-dev` **in the same message** so they run concurrently. They edit disjoint trees (`backend/` vs `frontend/`) and both build against the spec's **API Contract**.

**If `--serial` is set:** run backend first, then frontend in the same worktree.

**If only one side is affected or flags restrict it:** run only the relevant developer(s).

Prompt for each developer:

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

You are <ROLE> for Promelectron.
Important: Kimi K2.7-Code uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.

Read:
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. PROJECT_CONTEXT.md
4. .agent/BACKLOG.md
5. .agent/BLOCKERS.md
6. .agent/SESSION_LOG.md
7. `.kimi-code/skills/<ROLE>/SKILL.md`
8. [Rule: Pre-edit Checklist](.kimi-code/rules/pre-edit-checklist.md)

Setup:
1. Work ONLY inside $WORKTREE (branch $BRANCH).
2. Use explicit paths: git -C "$WORKTREE" ..., make -C "$WORKTREE" ..., Read/Edit/Write files under $WORKTREE.

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

Before finishing:
1. Run the role-specific tests in $WORKTREE (e.g. make -C "$WORKTREE" test-backend; make -C "$WORKTREE" test-frontend).
2. Run lint (make -C "$WORKTREE" lint-backend / make -C "$WORKTREE" lint-frontend) in $WORKTREE.
3. Update $WORKTREE/.agent/SESSION_LOG.md.

Report:
- Changed files
- Test results
- Any blockers

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

---

## Step 6: Code Review Loop (max 3 iterations)

### Determine review scope

Based on the spec and flags (`--backend-only`, `--frontend-only`):

- **Backend only or frontend only** → run one reviewer subagent.
- **Mixed (backend + frontend)** → run two reviewer subagents in parallel via `AgentSwarm`.
- **Security-sensitive work** (auth, payments, orders) → add `security-reviewer` to the parallel batch.

### Single-component review

Launch one reviewer subagent via `Agent` tool with `subagent_type: coder`. Apply the retry policy from Step 3.

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

You are the code-reviewer for Promelectron.
Important: Kimi K2.7-Code uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.

Read:
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. `.kimi-code/skills/code-reviewer/SKILL.md`
4. [Rule: Security](.kimi-code/rules/security.md)

Then:
1. Read the implementation in $WORKTREE (use Read/Grep/Glob in parallel).
2. Obtain the diff: git -C "$WORKTREE" diff origin/main...HEAD
3. Compare against the spec and Decisions (D-01, D-02, ...).
4. Check: logic, security, architecture, business rules, tests, golden path impact.
5. Write findings to $AGENT_DIR/review/findings.md using this format:

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

Launch reviewer subagents via `AgentSwarm` tool with `subagent_type: coder`. Apply the retry policy from Step 3.

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

You are the code-reviewer for Promelectron (focus: {{item}}).
Important: Kimi K2.7-Code uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.

Read:
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. `.kimi-code/skills/code-reviewer/SKILL.md`
4. [Rule: Security](.kimi-code/rules/security.md)

Then:
1. Read only {{item}} implementation files in $WORKTREE (use Read/Grep/Glob in parallel).
2. Obtain the diff: git -C "$WORKTREE" diff origin/main...HEAD
3. Compare against the spec and Decisions (D-01, D-02, ...).
4. Check: logic, security, architecture, business rules, tests, golden path impact for {{item}}.
5. Write findings to $AGENT_DIR/review/findings-{{item}}.md using this format:

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
   - Combine findings lists; renumber if needed so IDs are unique across backend and frontend.
   - Preserve Human Decisions from both reports.
3. Delete the temporary `findings-backend.md` and `findings-frontend.md` or keep them for debugging.

### Review loop continuation

1. Read `$AGENT_DIR/review/findings.md`.
2. If `APPROVED` → go to Step 7.
3. If `FIXES_NEEDED`:
   - Show the user a summary of findings.
   - For H-items, wait for user decision.
   - Launch the developer subagent again to fix OPEN findings and mark them FIXED.
   - **Before repeating review, re-run the relevant tests** in `$WORKTREE` (backend: `make -C "$WORKTREE" test-backend`; frontend: `make -C "$WORKTREE" test-frontend`). If tests fail, fix them first.
   - Repeat review.
4. After 3 iterations still `FIXES_NEEDED` → stop and ask the user how to proceed.

---

## Step 7: QA / Test Pyramid

### Light QA (default)

If `--qa` is **not** set, rely on the developers' own test runs and skip the dedicated QA gate.

### Full QA gate (run if --qa)

After code review passes, launch a `qa` subagent via `Agent` tool with `subagent_type: coder`. Apply the retry policy from Step 3.

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

You are the qa engineer for Promelectron.
Important: Kimi K2.7-Code uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.

Read:
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md
3. $AGENT_DIR/review/findings.md
4. PROJECT_CONTEXT.md
5. .agent/BACKLOG.md
6. .agent/BLOCKERS.md
7. `.kimi-code/skills/qa/SKILL.md`
8. [Rule: Golden Path](.kimi-code/rules/golden-path.md)

Then:
1. Run backend tests: make -C "$WORKTREE" test-backend
2. Run frontend unit tests: make -C "$WORKTREE" test-frontend
3. If the feature touches UI or user flows, run E2E tests. You may delegate the E2E-specific work to an e2e-tester subagent; if you do, pass the feature scope and spec explicitly.
4. Verify each Acceptance Criterion from $AGENT_DIR/spec.md.
5. Write results to $AGENT_DIR/review/test-findings.md.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

The `qa` subagent may launch an `e2e-tester` subagent for the browser-automation part if needed.

If `test-findings.md` status is `TESTS_FAILED`, show failures, invoke the affected developer(s) to fix, then return to Step 6 (code changed → re-review). Max 2 QA iterations, then escalate to the user.

CI already runs E2E on the test environment (`promelectron-test`) after deploy.

---

## Step 8: Create the Pull Request

All git ops target the worktree.

1. Push the branch:
   ```bash
   git -C "$WORKTREE" push -u origin "$BRANCH"
   ```
2. Create the PR:
   ```bash
   gh pr create --base main --head "$BRANCH" \
     --title "<concise description>" \
     --body "$(cat <<'EOF'
   ## Summary
   <what was done>

   ## Spec
   .agent/runs/<task-id>/spec.md — chosen approach + API contract

   ## Changes
   <changed files/components>

   ## Test Results
   - Backend: pytest X/Y · Frontend: vitest X/Y

   ## Acceptance Criteria
   <checked list from test-findings.md>
   EOF
   )"
   ```
3. Post open Human-Decision items as PR comments:
   ```bash
   gh pr comment "$BRANCH" --body "[H-xxx] <the open human-decision item>"
   ```
4. Move the linked GitHub Issue to **In review**:
   ```bash
   python scripts/implement-pipeline.py set-status <task-id> in-review
   ```
5. Capture the PR URL for the report.

---

## Step 9: Final Report

After all phases:

1. Run `python scripts/implement-pipeline.py check-context <task-id>` to capture final estimated tokens.
2. Read `.agent/SESSION_LOG.md` and append a summary including estimated tokens and iteration count.
3. Report to the user:
   - Task ID
   - Worktree path: `$WORKTREE`
   - Feature branch: `$BRANCH`
   - PR URL (if created)
   - Changed files
   - Test results (backend, frontend, e2e)
   - Review status
   - Estimated tokens and iteration count
   - Open findings or H-items (if any)
4. Ask: **"Merge `$BRANCH` into main?"** (do NOT merge or push main without explicit approval).
5. If the user approves merge and the merge completes, move the linked GitHub Issue to **Done**:
   ```bash
   python scripts/implement-pipeline.py set-status <task-id> done
   ```

---

## Rules

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
